"""
Dépendances FastAPI d'autorisation par rôle.
================================================
Ferme la faille « toute session authentifiée peut atteindre les routes
d'administration » (créer un DWH, éditer le .env, publier le catalogue, etc.).

Principe :
  - L'identité fait autorité UNIQUEMENT via un X-Session-Token validé
    (validate_session) — on ne fait pas confiance au header X-User-Id seul,
    qui est falsifiable.
  - Le rôle est résolu selon la même précédence que le login (Règle 2) :
    si l'utilisateur existe dans la base client OptiBoard_<DWH>.APP_Users → rôle
    client (role_dwh) ; sinon → rôle central (role_global).

Dépendances exposées :
  - require_admin       : superadmin (central) OU admin_client (base client).
  - require_superadmin  : superadmin central uniquement.

Fail-closed : toute ambiguïté ou erreur de résolution refuse l'accès (403/401).
"""
import logging
import time
import threading
from typing import Optional, Tuple

from fastapi import Request, HTTPException

from .database_unified import (
    validate_session,
    execute_central,
    execute_client,
    client_manager,
)

logger = logging.getLogger("Security")

_SUPERADMIN_ROLES = {"superadmin"}
_CENTRAL_ADMIN_ROLES = {"superadmin", "admin"}
_CLIENT_ADMIN_ROLES = {"admin_client"}

# Cache (positif) des accès DWH pour les sessions centrales — évite une requête
# SQL par appel API quand un superadmin navigue intensément dans un client.
_DWH_ACCESS_TTL = 120  # secondes
_dwh_access_cache: dict = {}
_dwh_access_lock = threading.Lock()


def user_can_access_dwh(user_id: int, dwh_code: str) -> bool:
    """L'utilisateur CENTRAL peut-il accéder à ce DWH ?

    À n'appeler QUE pour une session centrale (session.dwh_code is None) : dans
    ce cas user_id est l'ID de la base CENTRALE, donc APP_UserDWH/role_global
    sont fiables (pas de collision d'ID avec une base client). Pour une session
    déjà liée à un tenant, seul ce tenant est autorisé (cf. middleware).

    Autorise : superadmin central, ou association explicite APP_UserDWH sur un
    DWH actif. Résultat positif mis en cache (TTL court).
    """
    if not user_id or not dwh_code:
        return False
    now = time.time()
    key = (int(user_id), str(dwh_code))
    with _dwh_access_lock:
        hit = _dwh_access_cache.get(key)
        if hit and hit > now:
            return True
    allowed = False
    try:
        u = execute_central(
            "SELECT role_global FROM APP_Users WHERE id=?", (user_id,), use_cache=False
        )
        if u and (u[0].get("role_global") or "").strip().lower() in _SUPERADMIN_ROLES:
            allowed = True
    except Exception as e:  # pragma: no cover
        logger.warning(f"[SECURITY] role_global lookup ({user_id}): {e}")
    if not allowed:
        try:
            rows = execute_central(
                """SELECT 1 FROM APP_UserDWH ud
                   INNER JOIN APP_DWH d ON ud.dwh_code = d.code
                   WHERE ud.user_id = ? AND ud.dwh_code = ? AND d.actif = 1""",
                (user_id, dwh_code), use_cache=False,
            )
            if rows:
                allowed = True
        except Exception as e:  # pragma: no cover
            logger.warning(f"[SECURITY] APP_UserDWH lookup ({user_id},{dwh_code}): {e}")
    if allowed:
        with _dwh_access_lock:
            _dwh_access_cache[key] = now + _DWH_ACCESS_TTL
    return allowed


def _authenticated_identity(request: Request) -> Tuple[Optional[int], Optional[str]]:
    """Identité fiable, dérivée d'une session validée (pas du header brut)."""
    token = request.headers.get("x-session-token")
    if not token:
        return None, None
    try:
        session = validate_session(token)
    except Exception as e:  # pragma: no cover
        logger.warning(f"[SECURITY] validate_session error: {e}")
        return None, None
    if not session:
        return None, None
    try:
        uid = int(session["user_id"])
    except (KeyError, ValueError, TypeError):
        return None, None
    return uid, session.get("dwh_code")


def _resolve_role(user_id: int, dwh_code: Optional[str]) -> Tuple[str, Optional[str]]:
    """
    Retourne (realm, role) où realm ∈ {'client','central'}.
    Précédence identique au login : base client d'abord, puis centrale.
    """
    if dwh_code:
        try:
            if client_manager.has_client_db(dwh_code):
                rows = execute_client(
                    "SELECT role_dwh FROM APP_Users WHERE id=?",
                    (user_id,), dwh_code=dwh_code, use_cache=False,
                )
                if rows:
                    return "client", (rows[0].get("role_dwh") or "").strip().lower()
        except Exception as e:
            logger.warning(f"[SECURITY] lookup role_dwh ({dwh_code}): {e}")
    try:
        rows = execute_central(
            "SELECT role_global FROM APP_Users WHERE id=?",
            (user_id,), use_cache=False,
        )
        if rows:
            return "central", (rows[0].get("role_global") or "").strip().lower()
    except Exception as e:
        logger.warning(f"[SECURITY] lookup role_global: {e}")
    return "central", None


def _require(request: Request, *, superadmin_only: bool) -> dict:
    user_id, dwh_code = _authenticated_identity(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Session requise — veuillez vous reconnecter")

    realm, role = _resolve_role(user_id, dwh_code)

    if superadmin_only:
        allowed = (realm == "central" and role in _SUPERADMIN_ROLES)
    else:
        allowed = (
            (realm == "central" and role in _CENTRAL_ADMIN_ROLES)
            or (realm == "client" and role in _CLIENT_ADMIN_ROLES)
        )

    if not allowed:
        logger.warning(
            f"[SECURITY] Accès refusé user={user_id} dwh={dwh_code} realm={realm} "
            f"role={role} (superadmin_only={superadmin_only}) path={request.url.path}"
        )
        raise HTTPException(status_code=403, detail="Privilèges administrateur requis")

    return {"user_id": user_id, "dwh_code": dwh_code, "realm": realm, "role": role}


async def require_admin(request: Request) -> dict:
    """Autorise superadmin (central) ou admin_client (base client)."""
    return _require(request, superadmin_only=False)


async def require_superadmin(request: Request) -> dict:
    """Autorise uniquement le superadmin central."""
    return _require(request, superadmin_only=True)
