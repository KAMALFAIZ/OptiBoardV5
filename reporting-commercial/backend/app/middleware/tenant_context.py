"""
Middleware de Contexte Tenant (async-safe)
==========================================
Remplace client_context.py.
Utilise contextvars.ContextVar au lieu de threading.local().

Extrait les headers X-DWH-Code, X-User-Id, X-Societe-Code
et les injecte dans le contexte de la coroutine courante.
"""

import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ..database_unified import (
    set_tenant_context,
    reset_tenant_context,
    current_dwh_code,
    current_user_id,
    current_societe,
    client_manager
)

logger = logging.getLogger(__name__)

# Routes qui n'ont pas besoin de contexte tenant
EXEMPT_PREFIXES = (
    "/api/setup",
    "/api/license",
    "/api/auth/login",
    "/api/health",
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json",
    "/api/cache",
    "/api/info",
    "/api/scheduler/status",
)


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

        # Fallback : utiliser DWH_CODE depuis .env si défini (standalone ou démo)
        if dwh_code is None:
            from ..config import get_settings
            s = get_settings()
            if s.DWH_CODE:
                dwh_code = s.DWH_CODE

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

        # Injecter dans contextvars (async-safe)
        tokens = set_tenant_context(
            dwh_code=dwh_code,
            user_id=user_id,
            societe=societe_code
        )

        try:
            return await call_next(request)
        finally:
            # Reset le contexte apres la requete
            reset_tenant_context(tokens)
