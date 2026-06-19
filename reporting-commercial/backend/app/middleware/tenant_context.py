"""
Middleware de Contexte Tenant (async-safe)
==========================================
Remplace client_context.py.
Utilise contextvars.ContextVar au lieu de threading.local().

Extrait les headers X-DWH-Code, X-User-Id, X-Societe-Code
et les injecte dans le contexte de la coroutine courante.
"""

import os
import logging
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..database_unified import (
    set_tenant_context,
    reset_tenant_context,
    current_dwh_code,
    current_user_id,
    current_societe,
    validate_session,
    client_manager
)

logger = logging.getLogger(__name__)

# Routes qui n'ont pas besoin de contexte tenant (et pas de plancher d'auth)
EXEMPT_PREFIXES = (
    "/api/setup",
    "/api/license",
    "/api/console",   # monitoring console KASOFT (auth par X-Console-Token dans la route)
    "/api/auth/login",
    "/api/health",
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json",
    "/api/cache",
    "/api/info",
    "/api/scheduler/status",
)

# Routes /api/* qui ONT besoin du contexte tenant mais PAS d'une session
# utilisateur — elles s'authentifient autrement (clé API agent, token démo,
# signature Meta, clé maître) ou sont des étapes pré-session du login.
# Toute autre route /api/* exige désormais une session valide (plancher d'auth).
SESSION_OPTIONAL_PREFIXES = (
    # Étapes du login antérieures à l'obtention de la session
    "/api/auth/client-info",
    "/api/auth/dwh-list",
    "/api/auth/societes-list",
    "/api/auth/set-first-password",
    "/api/auth/2fa",
    # Agent ETL C# (auth par X-Api-Key, verify_agent)
    "/api/agents/",
    # Puller de catalogue (tire depuis le maître configuré par l'admin)
    "/api/updates",
    # Serveur central : catalogue maître exposé (auth par X-Master-Api-Key)
    "/api/master",
    # Portail démo : inscription publique + agent (auth par X-Demo-Token)
    "/api/demo",
    # Webhook WhatsApp (auth par signature Meta)
    "/api/whatsapp/webhook",
)

# ── Routage SaaS par sous-domaine ────────────────────────────────────────────
# xxxx.optiboard.kasoft.ma  →  DWH "XXXX". Domaine de base configurable via
# l'env BASE_DOMAIN. Les sous-domaines réservés ne sont pas des tenants.
_BASE_DOMAIN = (os.environ.get("BASE_DOMAIN", "optiboard.kasoft.ma") or "").lower()
_RESERVED_SUBDOMAINS = {"www", "app", "api", "portal", "admin", "static", "cdn", "mail"}


def _subdomain_dwh_code(host: str):
    """Extrait le code DWH du sous-domaine de l'en-tête Host, ou None."""
    if not host or not _BASE_DOMAIN:
        return None
    host = host.split(":")[0].strip().lower()  # retirer le port éventuel
    if host == "localhost" or host.endswith(".localhost"):
        return None
    suffix = "." + _BASE_DOMAIN
    if not host.endswith(suffix):
        return None
    left = host[: -len(suffix)]          # tout ce qui précède le domaine de base
    if not left:
        return None
    sub = left.split(".")[0]             # premier label uniquement
    if not sub or sub in _RESERVED_SUBDOMAINS:
        return None
    return sub.upper()


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware qui injecte le contexte tenant dans les ContextVars.

    Apres ce middleware, les routes peuvent acceder a:
    - request.state.dwh_code : le code DWH actif
    - request.state.user_id : l'ID utilisateur
    - request.state.has_client_db : True si une base client est configuree
    - Via contextvars: current_dwh_code.get(), current_user_id.get(), etc.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Routes exemptees - pas de contexte tenant
        if path == "/" or any(path.startswith(prefix) for prefix in EXEMPT_PREFIXES):
            request.state.dwh_code = None
            request.state.user_id = None
            request.state.has_client_db = False
            tokens = set_tenant_context(dwh_code=None, user_id=None, societe=None)
            try:
                return await call_next(request)
            finally:
                reset_tenant_context(tokens)

        # Extraire les headers
        dwh_code = request.headers.get("x-dwh-code") or None
        user_id_str = request.headers.get("x-user-id")
        societe_code = request.headers.get("x-societe-code") or None
        data_source = request.headers.get("x-data-source") or None  # "dwh" | "sage"
        session_token = request.headers.get("x-session-token") or None

        # Routage SaaS par sous-domaine : si le client n'a pas envoyé
        # X-DWH-Code, déduire le tenant de l'hôte (xxxx.optiboard.kasoft.ma).
        # Précédence : header explicite > sous-domaine > session > .env.
        if dwh_code is None:
            dwh_code = _subdomain_dwh_code(request.headers.get("host", ""))

        # Validation du session token (si présent)
        session_valid = False
        session_dwh_code = None
        session_user_id = None
        if session_token:
            try:
                session = validate_session(session_token)
                if session is None:
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "Session expirée ou invalide — veuillez vous reconnecter"},
                    )
                session_valid = True
                session_user_id = session.get("user_id")
                session_dwh_code = session.get("dwh_code")
                # Priorité au session token sur les headers manuels
                if not user_id_str:
                    user_id_str = str(session["user_id"])
                if not dwh_code:
                    dwh_code = session_dwh_code
            except Exception as e:
                logger.warning(f"validate_session error: {e}")

        # ── Plancher d'authentification (fail-closed) ─────────────────────────
        # Toute route /api/* qui n'est ni exemptée (ci-dessus, return anticipé)
        # ni « session optionnelle » exige une session VALIDE. On ne fait jamais
        # confiance au seul header X-User-Id (falsifiable) : seule une session
        # validée via validate_session autorise l'accès.
        if path.startswith("/api/") and not any(
            path.startswith(p) for p in SESSION_OPTIONAL_PREFIXES
        ):
            if not session_valid:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Authentification requise — veuillez vous reconnecter"},
                )

        # Fallback : utiliser DWH_CODE depuis .env si défini (standalone ou démo)
        if dwh_code is None:
            from ..config import get_settings
            s = get_settings()
            if s.DWH_CODE:
                dwh_code = s.DWH_CODE

        # ── Isolation tenant : anti-rejeu cross-tenant ───────────────────────
        # Le dwh_code prouvé au login (session_dwh_code) fait autorité. Un
        # dwh_code DIFFÉRENT (header X-DWH-Code ou sous-domaine) n'est légitime
        # que pour une session CENTRALE (superadmin / user multi-DWH) : pour un
        # user lié à un tenant, son user_id n'a de sens que dans SA base client,
        # donc on le fige sur ce tenant (sinon rejeu du token vers un autre DWH).
        if session_valid and dwh_code and session_dwh_code != dwh_code:
            allowed = False
            if session_dwh_code is None and session_user_id is not None:
                try:
                    from ..security import user_can_access_dwh
                    allowed = user_can_access_dwh(session_user_id, dwh_code)
                except Exception as e:
                    logger.warning(f"user_can_access_dwh error: {e}")
                    allowed = False
            if not allowed:
                logger.warning(
                    f"[TENANT] Accès cross-tenant refusé user={session_user_id} "
                    f"session_dwh={session_dwh_code} demandé={dwh_code} path={path}"
                )
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Accès à ce client non autorisé"},
                )

        # Parser user_id
        user_id = None
        if user_id_str:
            try:
                user_id = int(user_id_str)
            except (ValueError, TypeError):
                logger.warning(f"X-User-Id invalide: '{user_id_str}'")

        # Verifier si la base client existe
        has_client_db = False
        if dwh_code:
            try:
                has_client_db = client_manager.has_client_db(dwh_code)
            except Exception as e:
                logger.warning(f"Erreur verification base client pour '{dwh_code}': {e}")

        # Injecter dans request.state
        request.state.dwh_code = dwh_code
        request.state.user_id = user_id
        request.state.has_client_db = has_client_db
        request.state.data_source = data_source

        # Injecter dans contextvars (async-safe)
        tokens = set_tenant_context(
            dwh_code=dwh_code,
            user_id=user_id,
            societe=societe_code,
            data_source=data_source
        )

        try:
            return await call_next(request)
        finally:
            # Reset le contexte apres la requete
            reset_tenant_context(tokens)
