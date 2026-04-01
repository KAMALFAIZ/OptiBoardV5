"""
Routes API pour le module IA OptiBoard.
Les requetes SQL generees par l'IA sont executees sur la base DWH du client
via execute_dwh_query (connexion directe, sans prefixe de base de donnees).
"""
from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Tuple
import time
import json
import logging
import re
import decimal
import datetime

from ..config import get_settings, reload_settings  # force reload on every AI call
from ..database_unified import execute_central as execute_query  # pour APP_UserDWH lookup uniquement (CENTRAL)
from ..database_unified import execute_dwh_query  # shim compatibilite (dwh_code, query, ...)
from ..services.ai_provider import get_ai_provider, AIMessage, AIProviderError
from ..services.ai_schema import get_schema_for_ai, get_business_context, get_sql_examples, get_dynamic_examples
from ..services.ai_query_library import add_to_library as _lib_add
from ..services.ai_prompt_manager import get_prompt
from ..services.ai_sql_validator import validate_ai_sql
from ..services.ai_conversation import conversation_manager
from ..services.query_logger import query_logger
from ..middleware.license_guard import get_effective_row_limit, get_license_restriction_info

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["IA Assistant"])


def _json_serial(obj):
    """Serialiseur JSON custom pour les types Python non serialisables par defaut."""
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _safe_json_dumps(data) -> str:
    """json.dumps avec gestion des types SQL Server (Decimal, date...)."""
    return json.dumps(data, default=_json_serial)


# =====================================================
# MODELES PYDANTIC
# =====================================================

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    mode: str = "chat"  # "chat" | "sql" | "help"
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    success: bool
    response: str
    session_id: str
    sql_query: Optional[str] = None
    sql_results: Optional[List[Dict]] = None
    sql_columns: Optional[List[str]] = None
    provider: str
    duration_ms: int
    license_restriction: Optional[Dict] = None  # Ex: {"limited": True, "row_limit": 100, "reason": "..."}


class AIStatusResponse(BaseModel):
    enabled: bool
    provider: str
    model: str
    configured: bool


class SQLValidateRequest(BaseModel):
    query: str


class SQLExecuteRequest(BaseModel):
    query: str


# =====================================================
# HELPERS INTERNES
# =====================================================

def _resolve_dwh_code(x_dwh_code: Optional[str], user_id: int) -> Tuple[Optional[str], Optional[List[Dict]]]:
    """
    Resout le code DWH a utiliser pour les requetes IA.
    Retourne (dwh_code, None) si resolu, ou (None, dwh_list) si selection requise.
    """
    if x_dwh_code:
        return x_dwh_code, None

    # Pas de header DWH → chercher les DWH accessibles par l'utilisateur
    try:
        if user_id > 0:
            dwh_list = execute_query(
                """SELECT d.code, d.nom
                   FROM APP_DWH d
                   INNER JOIN APP_UserDWH ud ON d.code = ud.dwh_code
                   WHERE ud.user_id = ? AND d.actif = 1
                   ORDER BY ud.is_default DESC, d.nom""",
                (user_id,),
                use_cache=False
            )
            if dwh_list and len(dwh_list) == 1:
                return dwh_list[0]['code'], None
            if dwh_list and len(dwh_list) > 1:
                return None, [{"code": d["code"], "nom": d["nom"]} for d in dwh_list]
    except Exception as e:
        logger.warning(f"APP_UserDWH lookup failed for user {user_id}: {e}")

    # Fallback : premier DWH actif
    try:
        fallback = execute_query(
            "SELECT TOP 1 code, nom FROM APP_DWH WHERE actif = 1 ORDER BY id",
            use_cache=True
        )
        if fallback:
            return fallback[0]['code'], None
    except Exception as e:
        logger.warning(f"Fallback DWH lookup failed: {e}")

    return None, None


def _build_system_prompt(mode: str, dwh_code: Optional[str], context: dict = None, question: str = "") -> str:
    """Construit le prompt systeme selon le mode d'interaction. Utilise les prompts DB si disponibles."""
    # Sections personnalisables depuis DB (fallback hardcodé automatique)
    business_ctx = get_prompt("business_context")
    sql_rules = get_prompt("sql_rules")
    custom_instructions = get_prompt("custom_instructions")

    try:
        if dwh_code:
            schema = get_schema_for_ai(dwh_code)
        else:
            schema = "(Schema non disponible: aucun DWH selectionne)"
    except Exception as e:
        logger.warning(f"Schema introspection failed: {e}")
        schema = "(Schema non disponible)"

    # Exemples dynamiques depuis la Query Library (RAG) — injectés en priorité
    dynamic_examples = get_dynamic_examples(question, dwh_code) if question else ""

    # Exemples SQL eprouves pour guider le LLM
    sql_examples = get_sql_examples()

    base_system = f"{business_ctx}\n\n{schema}\n\n{dynamic_examples}{sql_examples}\n\n{sql_rules}\n"

    # Instructions personnalisées (si définies)
    if custom_instructions.strip():
        base_system += f"\n=== INSTRUCTIONS SPECIFIQUES ===\n{custom_instructions}\n"

    if mode == "sql":
        return base_system + "\n" + get_prompt("mode_sql")
    elif mode == "help":
        return base_system + "\n" + get_prompt("mode_help")
    else:
        return base_system + "\n" + get_prompt("mode_chat")


def _extract_sql_from_response(response: str) -> Optional[str]:
    """Extrait la requete SQL du texte de la reponse LLM."""
    pattern = re.compile(r'```sql\s*(.*?)\s*```', re.DOTALL | re.IGNORECASE)
    matches = pattern.findall(response)
    return matches[0].strip() if matches else None


def _get_user_role(user_id: int) -> str:
    """Retourne le role_global de l'utilisateur, ou '' si inconnu."""
    if not user_id:
        return ""
    try:
        row = execute_query(
            "SELECT role_global FROM APP_Users WHERE id = ?",
            (user_id,),
            use_cache=False
        )
        return row[0].get("role_global", "") if row else ""
    except Exception:
        return ""


# Rate limiting simple en memoire
_rate_limit_store: Dict[str, List[float]] = {}


def _check_rate_limit(user_key: str, max_per_minute: int) -> bool:
    """Verifie le rate limit par utilisateur. Retourne False si limite depassee."""
    now = time.time()
    window_start = now - 60.0

    if user_key not in _rate_limit_store:
        _rate_limit_store[user_key] = []

    _rate_limit_store[user_key] = [
        t for t in _rate_limit_store[user_key] if t > window_start
    ]

    if len(_rate_limit_store[user_key]) >= max_per_minute:
        return False

    _rate_limit_store[user_key].append(now)
    return True


async def _retry_failed_sql(
    provider, messages: List, original_sql: str, error_msg: str,
    dwh_code: str, max_rows: int, session
) -> Optional[Dict]:
    """
    Tente de corriger un SQL qui a echoue en renvoyant l'erreur au LLM.
    Retourne un dict {sql_query, sql_results, sql_columns, retried} ou None si echec.
    """
    try:
        correction_prompt = (
            f"La requete SQL suivante a echoue avec une erreur:\n\n"
            f"```sql\n{original_sql}\n```\n\n"
            f"Erreur: {error_msg}\n\n"
            f"Corrige la requete SQL pour resoudre cette erreur. "
            f"Verifie les noms de colonnes et la syntaxe T-SQL. "
            f"Retourne UNIQUEMENT la requete corrigee dans un bloc ```sql."
        )

        retry_messages = messages + [AIMessage("user", correction_prompt)]
        retry_response = await provider.chat(retry_messages)

        # Extraire le nouveau SQL
        new_sql = _extract_sql_from_response(retry_response)
        if not new_sql:
            return None

        # Valider le nouveau SQL
        is_valid, safe_sql, val_error = validate_ai_sql(new_sql, max_rows=max_rows)
        if not is_valid:
            logger.warning(f"Retry SQL also invalid: {val_error}")
            return None

        # Executer le nouveau SQL
        results = execute_dwh_query(dwh_code, safe_sql, use_cache=True, cache_ttl=300)
        columns = list(results[0].keys()) if results else []

        # Sauvegarder la correction dans l'historique
        session.add_message("assistant", retry_response)

        logger.info(f"SQL auto-retry succeeded. Original error: {error_msg[:100]}")
        return {
            "sql_query": safe_sql,
            "sql_results": results[:max_rows],
            "sql_columns": columns,
            "retried": True
        }

    except Exception as e:
        logger.warning(f"SQL auto-retry also failed: {e}")
        return None


# =====================================================
# ENDPOINTS
# =====================================================

@router.get("/status", response_model=AIStatusResponse)
async def get_ai_status():
    """Retourne le statut et la configuration du module IA."""
    current_settings = reload_settings()  # Toujours relire le .env pour avoir la config a jour

    if current_settings.AI_PROVIDER == "ollama":
        configured = bool(
            current_settings.AI_ENABLED
            and current_settings.AI_OLLAMA_URL
            and current_settings.AI_MODEL
        )
    else:
        configured = bool(
            current_settings.AI_ENABLED
            and current_settings.AI_API_KEY
            and current_settings.AI_MODEL
            and current_settings.AI_PROVIDER
        )

    return AIStatusResponse(
        enabled=current_settings.AI_ENABLED,
        provider=current_settings.AI_PROVIDER or "non configure",
        model=current_settings.AI_MODEL or "non configure",
        configured=configured
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    x_dwh_code: Optional[str] = Header(None, alias="X-DWH-Code"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """Point d'entree principal du chatbot IA."""
    start_time = time.time()
    user_id = int(x_user_id) if x_user_id and x_user_id.isdigit() else 0
    is_superadmin = _get_user_role(user_id) == "superadmin"

    # Resoudre le DWH
    dwh_code, dwh_list = _resolve_dwh_code(x_dwh_code, user_id)

    # Rate limiting (bypasse pour superadmin)
    current_settings = get_settings()
    if not is_superadmin:
        rate_key = f"ai:{user_id}:{dwh_code or 'none'}"
        if not _check_rate_limit(rate_key, current_settings.AI_RATE_LIMIT_PER_MINUTE):
            raise HTTPException(
                status_code=429,
                detail="Trop de requetes IA. Veuillez patienter une minute."
            )

    # Sélection DWH requise
    if dwh_list:
        # Retourner une reponse demandant la selection
        return ChatResponse(
            success=True,
            response=f"Plusieurs datasources DWH sont disponibles: {', '.join(d['nom'] for d in dwh_list)}. Veuillez selectionner celui a interroger.",
            session_id=request.session_id or "pending",
            provider="system",
            duration_ms=0
        )

    # Session
    session = conversation_manager.get_or_create_session(
        request.session_id, user_id, dwh_code or "default"
    )

    try:
        provider = get_ai_provider()
        if not provider:
            raise HTTPException(
                status_code=503,
                detail="Module IA non configure. Activez un fournisseur dans Parametres > Intelligence Artificielle."
            )

        # Construire les messages
        system_prompt = _build_system_prompt(request.mode, dwh_code, request.context, request.message)
        history = session.get_recent_messages(
            max_messages=current_settings.AI_HISTORY_MAX_MESSAGES
        )

        messages = [AIMessage("system", system_prompt)]
        for msg in history:
            messages.append(AIMessage(msg["role"], msg["content"]))
        messages.append(AIMessage("user", request.message))

        # Appel LLM
        ai_response = await provider.chat(messages)

        # Sauvegarder dans l'historique
        session.add_message("user", request.message)
        session.add_message("assistant", ai_response)

        # Extraction et execution SQL si present
        sql_query = None
        sql_results = None
        sql_columns = None

        # Limite de lignes selon licence (superadmin → accès total)
        if is_superadmin:
            effective_max_rows = getattr(current_settings, "AI_SQL_MAX_ROWS", 500) or 500
            license_restriction = None
        else:
            effective_max_rows = get_effective_row_limit()
            license_restriction = get_license_restriction_info()

        extracted_sql = _extract_sql_from_response(ai_response)
        if extracted_sql and dwh_code:
            is_valid, safe_sql, error = validate_ai_sql(
                extracted_sql, max_rows=effective_max_rows
            )
            if is_valid:
                sql_query = safe_sql
                try:
                    sql_data = execute_dwh_query(
                        dwh_code, safe_sql, use_cache=True, cache_ttl=300
                    )
                    sql_results = sql_data[:effective_max_rows]
                    sql_columns = list(sql_data[0].keys()) if sql_data else []
                    query_logger.log_query(
                        "ai_generated", "IA Generated SQL",
                        safe_sql[:200], time.time() - start_time, len(sql_data)
                    )
                    # Auto-save to library (pending validation) pour apprentissage
                    try:
                        _lib_add(
                            question_text=request.message[:1000],
                            sql_query=safe_sql,
                            dwh_code=dwh_code,
                            validated_by=None,
                            is_validated=False
                        )
                    except Exception:
                        pass
                except Exception as e:
                    logger.warning(f"AI SQL execution failed (DWH: {dwh_code}): {e}")
                    # Auto-retry: tenter de corriger le SQL
                    retry_result = await _retry_failed_sql(
                        provider, messages, safe_sql, str(e)[:500],
                        dwh_code, effective_max_rows, session
                    )
                    if retry_result:
                        sql_query = retry_result["sql_query"]
                        sql_results = retry_result["sql_results"]
                        sql_columns = retry_result["sql_columns"]
                    else:
                        sql_results = None
                        session.add_message(
                            "system",
                            f"Note: La requete SQL a echoue: {str(e)[:200]}"
                        )

        duration_ms = int((time.time() - start_time) * 1000)

        return ChatResponse(
            success=True,
            response=ai_response,
            session_id=session.session_id,
            sql_query=sql_query,
            sql_results=sql_results,
            sql_columns=sql_columns,
            provider=provider.get_provider_name(),
            duration_ms=duration_ms,
            license_restriction=license_restriction
        )

    except AIProviderError as e:
        logger.error(f"AI provider error: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    x_dwh_code: Optional[str] = Header(None, alias="X-DWH-Code"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """Version streaming du chat IA (Server-Sent Events)."""
    user_id = int(x_user_id) if x_user_id and x_user_id.isdigit() else 0
    is_superadmin = _get_user_role(user_id) == "superadmin"

    # Resoudre le DWH
    dwh_code, dwh_list = _resolve_dwh_code(x_dwh_code, user_id)

    # Si plusieurs DWH → demander la selection via SSE
    if dwh_list:
        async def dwh_selection_stream():
            payload = {
                "dwh_selection_required": True,
                "dwh_list": dwh_list
            }
            yield f"data: {_safe_json_dumps(payload)}\n\n"
        return StreamingResponse(
            dwh_selection_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
        )

    session = conversation_manager.get_or_create_session(
        request.session_id, user_id, dwh_code or "default"
    )

    try:
        provider = get_ai_provider()
        if not provider:
            raise HTTPException(status_code=503, detail="Module IA non configure. Activez un fournisseur dans Parametres > Intelligence Artificielle.")

        current_settings = get_settings()
        system_prompt = _build_system_prompt(request.mode, dwh_code, request.context, request.message)
        history = session.get_recent_messages()
        messages = [AIMessage("system", system_prompt)]
        for msg in history:
            messages.append(AIMessage(msg["role"], msg["content"]))
        messages.append(AIMessage("user", request.message))

        session.add_message("user", request.message)
        full_response_parts = []

        async def generate():
            try:
                async for token in provider.chat_stream(messages):
                    full_response_parts.append(token)
                    yield f"data: {_safe_json_dumps({'token': token})}\n\n"

                full_response = "".join(full_response_parts)
                session.add_message("assistant", full_response)

                # Extraction et execution SQL post-stream
                extracted_sql = _extract_sql_from_response(full_response)
                sql_data = None
                # Limite de lignes selon licence (superadmin → accès total)
                if is_superadmin:
                    stream_max_rows = getattr(current_settings, "AI_SQL_MAX_ROWS", 500) or 500
                    license_restriction = None
                else:
                    stream_max_rows = get_effective_row_limit()
                    license_restriction = get_license_restriction_info()
                if extracted_sql and dwh_code:
                    is_valid, safe_sql, _ = validate_ai_sql(
                        extracted_sql, max_rows=stream_max_rows
                    )
                    if is_valid:
                        try:
                            results = execute_dwh_query(
                                dwh_code, safe_sql, use_cache=True, cache_ttl=300
                            )
                            columns = list(results[0].keys()) if results else []
                            sql_data = {
                                "sql_query": safe_sql,
                                "sql_results": results[:stream_max_rows],
                                "sql_columns": columns
                            }
                        except Exception as e:
                            logger.warning(f"AI stream SQL execution failed (DWH: {dwh_code}): {e}")
                            # Auto-retry: tenter de corriger le SQL
                            yield f"data: {_safe_json_dumps({'retry': True, 'message': 'Correction du SQL en cours...'})}\n\n"
                            retry_result = await _retry_failed_sql(
                                provider, messages, safe_sql, str(e)[:500],
                                dwh_code, stream_max_rows, session
                            )
                            if retry_result:
                                sql_data = retry_result
                            else:
                                sql_data = {
                                    "sql_query": safe_sql,
                                    "sql_results": None,
                                    "sql_columns": None,
                                    "sql_error": str(e)[:200]
                                }
                    else:
                        sql_data = {"sql_query": extracted_sql, "sql_results": None, "sql_columns": None}
                elif extracted_sql and not dwh_code:
                    # SQL genere mais pas de DWH → indiquer l'erreur
                    sql_data = {
                        "sql_query": extracted_sql,
                        "sql_results": None,
                        "sql_columns": None,
                        "sql_error": "Aucun DWH selectionne pour executer la requete"
                    }

                done_payload = {"done": True, "session_id": session.session_id}
                if sql_data:
                    done_payload.update(sql_data)
                if license_restriction:
                    done_payload["license_restriction"] = license_restriction
                yield f"data: {_safe_json_dumps(done_payload)}\n\n"

            except Exception as e:
                logger.error(f"Stream generation error: {e}")
                yield f"data: {_safe_json_dumps({'error': str(e)})}\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no"
            }
        )

    except AIProviderError as e:
        logger.error(f"AI provider error in stream: {e}")
        async def error_stream_provider():
            yield f"data: {_safe_json_dumps({'error': str(e)})}\n\n"
        return StreamingResponse(
            error_stream_provider(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
        )
    except HTTPException as e:
        async def error_stream_http():
            yield f"data: {_safe_json_dumps({'error': e.detail})}\n\n"
        return StreamingResponse(
            error_stream_http(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
        )
    except Exception as e:
        logger.error(f"AI stream error: {e}", exc_info=True)
        async def error_stream_generic():
            yield f"data: {_safe_json_dumps({'error': str(e)})}\n\n"
        return StreamingResponse(
            error_stream_generic(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
        )


@router.get("/schema")
async def get_schema(
    x_dwh_code: Optional[str] = Header(None, alias="X-DWH-Code"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """Retourne le schema disponible pour le contexte IA."""
    user_id = int(x_user_id) if x_user_id and x_user_id.isdigit() else 0
    dwh_code, _ = _resolve_dwh_code(x_dwh_code, user_id)
    try:
        if not dwh_code:
            return {"success": False, "error": "Aucun DWH disponible", "schema": ""}
        schema = get_schema_for_ai(dwh_code)
        return {"success": True, "schema": schema, "dwh_code": dwh_code}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sql/validate")
async def validate_sql(request: SQLValidateRequest):
    """Valide une requete SQL generee par l'IA sans l'executer."""
    current_settings = get_settings()
    is_valid, safe_sql, error = validate_ai_sql(
        request.query, current_settings.AI_SQL_MAX_ROWS
    )
    return {
        "success": True,
        "valid": is_valid,
        "sanitized_query": safe_sql if is_valid else None,
        "error": error if not is_valid else None
    }


@router.post("/sql/execute")
async def execute_ai_sql(
    request: SQLExecuteRequest,
    x_dwh_code: Optional[str] = Header(None, alias="X-DWH-Code"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """Execute une requete SQL validee sur le DWH du client.
    Reservee aux utilisateurs superadmin uniquement.
    """
    user_id = int(x_user_id) if x_user_id and x_user_id.isdigit() else 0

    # ── Verification role superadmin ──────────────────────────────────────────
    if user_id:
        try:
            user_row = execute_query(
                "SELECT role_global FROM APP_Users WHERE id = ?",
                (user_id,),
                use_cache=False
            )
            role = user_row[0].get("role_global", "") if user_row else ""
        except Exception:
            role = ""
    else:
        role = ""

    if role != "superadmin":
        raise HTTPException(
            status_code=403,
            detail="Acces refuse : l'execution SQL est reservee aux super-administrateurs."
        )
    # ─────────────────────────────────────────────────────────────────────────

    dwh_code, dwh_list = _resolve_dwh_code(x_dwh_code, user_id)

    if dwh_list:
        raise HTTPException(
            status_code=400,
            detail=f"Plusieurs DWH disponibles. Specifiez le DWH via le header X-DWH-Code: {', '.join(d['code'] for d in dwh_list)}"
        )
    if not dwh_code:
        raise HTTPException(status_code=400, detail="Aucun DWH disponible pour executer la requete")

    current_settings = get_settings()
    is_valid, safe_sql, error = validate_ai_sql(
        request.query, current_settings.AI_SQL_MAX_ROWS
    )
    if not is_valid:
        raise HTTPException(
            status_code=400, detail=f"Requete SQL invalide: {error}"
        )

    try:
        start_time = time.time()
        data = execute_dwh_query(dwh_code, safe_sql, use_cache=True, cache_ttl=300)
        execution_time = time.time() - start_time
        columns = list(data[0].keys()) if data else []

        # Serialiser avec le convertisseur custom puis re-parser pour retourner un dict propre
        serialized = _safe_json_dumps({
            "success": True,
            "data": data[:current_settings.AI_SQL_MAX_ROWS],
            "columns": columns,
            "row_count": len(data),
            "execution_time_ms": round(execution_time * 1000),
            "dwh_code": dwh_code
        })
        return json.loads(serialized)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """Efface l'historique d'une session de conversation."""
    conversation_manager.clear_session(session_id)
    return {"success": True, "message": "Session effacee"}


@router.post("/test-provider")
async def test_provider():
    """Teste la connexion au fournisseur IA configure."""
    try:
        provider = get_ai_provider()
        if not provider:
            return {"success": False, "error": "Aucun fournisseur configure"}

        test_messages = [
            AIMessage("system", "Tu es un assistant de test."),
            AIMessage("user", "Reponds uniquement 'OK' en un seul mot.")
        ]
        response = await provider.chat(test_messages)
        return {
            "success": True,
            "provider": provider.get_provider_name(),
            "response": response[:100]
        }
    except AIProviderError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": str(e)}
