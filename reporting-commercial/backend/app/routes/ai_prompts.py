"""
Routes API pour la gestion des prompts IA personnalisés.
"""
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
import logging

from ..database_unified import execute_central
from ..services.ai_prompt_manager import (
    get_all_prompts, save_prompt, reset_prompt, get_prompt
)
from ..services.ai_schema import get_schema_for_ai, get_sql_examples
from ..services.ai_query_library import find_similar_queries

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ai/prompts", tags=["IA Prompts"])


def _get_user_role(user_id: int) -> str:
    if not user_id:
        return ""
    try:
        rows = execute_central(
            "SELECT role_global FROM APP_Users WHERE id = ?",
            (user_id,), use_cache=False
        )
        return rows[0].get("role_global", "") if rows else ""
    except Exception:
        return ""


class PromptSaveRequest(BaseModel):
    contenu: str


@router.get("/")
async def list_prompts(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """Retourne toutes les sections de prompts (superadmin)."""
    user_id = int(x_user_id) if x_user_id and x_user_id.isdigit() else 0
    if _get_user_role(user_id) != "superadmin":
        raise HTTPException(status_code=403, detail="Accès réservé aux super-administrateurs")
    return {"success": True, "prompts": get_all_prompts()}


@router.put("/{code}")
async def update_prompt(
    code: str,
    request: PromptSaveRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """Sauvegarde un prompt personnalisé (superadmin)."""
    user_id = int(x_user_id) if x_user_id and x_user_id.isdigit() else 0
    if _get_user_role(user_id) != "superadmin":
        raise HTTPException(status_code=403, detail="Accès réservé aux super-administrateurs")
    success = save_prompt(code, request.contenu, updated_by=f"user_{user_id}")
    if not success:
        raise HTTPException(status_code=500, detail="Erreur lors de la sauvegarde")
    return {"success": True, "message": "Prompt sauvegardé"}


@router.delete("/{code}/reset")
async def reset_prompt_route(
    code: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """Remet un prompt à sa valeur par défaut (superadmin)."""
    user_id = int(x_user_id) if x_user_id and x_user_id.isdigit() else 0
    if _get_user_role(user_id) != "superadmin":
        raise HTTPException(status_code=403, detail="Accès réservé aux super-administrateurs")
    success = reset_prompt(code)
    return {"success": success, "message": "Prompt réinitialisé au défaut"}


@router.get("/preview")
async def preview_full_prompt(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_dwh_code: Optional[str] = Header(None, alias="X-DWH-Code")
):
    """Retourne un aperçu du prompt complet assemblé avec le vrai schéma DWH (superadmin)."""
    user_id = int(x_user_id) if x_user_id and x_user_id.isdigit() else 0
    if _get_user_role(user_id) != "superadmin":
        raise HTTPException(status_code=403, detail="Accès réservé aux super-administrateurs")

    business_ctx  = get_prompt("business_context")
    sql_rules     = get_prompt("sql_rules")
    custom        = get_prompt("custom_instructions")
    mode_chat     = get_prompt("mode_chat")
    mode_sql      = get_prompt("mode_sql")
    mode_help     = get_prompt("mode_help")

    # ── Schéma DWH réel ──────────────────────────────────────────────────────
    if x_dwh_code:
        try:
            schema = get_schema_for_ai(x_dwh_code)
            schema_section = f"=== SCHEMA DWH ({x_dwh_code}) ===\n{schema}"
        except Exception as e:
            schema_section = f"[SCHEMA DWH — erreur: {e}]"
    else:
        schema_section = "[SCHEMA DWH — sélectionnez un DWH via l'en-tête X-DWH-Code pour voir le schéma réel]"

    # ── Exemples Query Library ────────────────────────────────────────────────
    try:
        lib_entries = find_similar_queries("", dwh_code=x_dwh_code, top_k=5, min_score=0.0)
        if lib_entries:
            lib_lines = ["=== BASE DE CONNAISSANCE VALIDEE (top 5) ==="]
            for i, e in enumerate(lib_entries, 1):
                lib_lines.append(f"\n--- Exemple {i} (utilisé {e['success_count']}x) ---")
                lib_lines.append(f"Question: \"{e['question_text']}\"")
                lib_lines.append(f"SQL:\n{e['sql_query']}")
            library_section = "\n".join(lib_lines)
        else:
            library_section = "[EXEMPLES QUERY LIBRARY — aucun exemple validé (cliquez Init Exemples)]"
    except Exception as e:
        library_section = f"[EXEMPLES QUERY LIBRARY — erreur: {e}]"

    # ── Exemples SQL statiques ────────────────────────────────────────────────
    sql_examples_section = get_sql_examples()

    # ── Assemblage final ──────────────────────────────────────────────────────
    sections = [
        ("CONTEXTE METIER", business_ctx),
        ("SCHEMA DWH", schema_section),
        ("BASE DE CONNAISSANCE (RAG)", library_section),
        ("EXEMPLES SQL STATIQUES", sql_examples_section),
        ("REGLES SQL", sql_rules),
    ]

    preview = ""
    for title, content in sections:
        preview += f"{'═'*60}\n▶ {title}\n{'═'*60}\n{content}\n\n"

    if custom.strip():
        preview += f"{'═'*60}\n▶ INSTRUCTIONS PERSONNALISEES\n{'═'*60}\n{custom}\n\n"

    preview += (
        f"{'═'*60}\n▶ MODE ACTIF\n{'═'*60}\n"
        f"[Chat/Analyse]\n{mode_chat}\n\n"
        f"[SQL]\n{mode_sql}\n\n"
        f"[Aide]\n{mode_help}"
    )

    return {
        "success": True,
        "preview": preview,
        "char_count": len(preview),
        "token_estimate": len(preview) // 4,
        "dwh_code": x_dwh_code or "non sélectionné",
        "sections": {
            "schema_loaded": bool(x_dwh_code),
            "library_entries": len(lib_entries) if 'lib_entries' in dir() else 0,
        }
    }
