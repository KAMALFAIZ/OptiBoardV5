"""
Routes d'Authentification Multi-Tenant
=======================================
Règle 2 (architecture) : chaque base client OptiBoard_cltxx possède sa propre
table APP_Users. Le login tente d'abord la base client si dwh_code est fourni,
puis se replie sur la base centrale (superadmin / backward compat).

Flux de login :
  1. Si dwh_code fourni → chercher user dans OptiBoard_{dwh_code}.APP_Users
  2. Si trouvé → authentifier, mettre à jour derniere_connexion dans client DB
  3. Si non trouvé → chercher dans OptiBoard_SaaS.APP_Users (superadmin / fallback)
  4. Retourner le contexte complet
"""

import hashlib
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import pyodbc
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

from ..database_unified import (
    execute_central,
    execute_client,
    write_central,
    write_client,
    create_user_context,
    get_user_dwh_list,
    get_user_societes,
    get_all_dwh_societes,
    client_manager,
    UserContext,
)

logger = logging.getLogger("AuthMultitenant")

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# DWH réservés à la démonstration (superadmin uniquement, accès client interdit)
_DEMO_DWH_CODES = {"KA"}


# =============================================================================
# SCHEMAS
# =============================================================================

class LoginRequest(BaseModel):
    username: str
    password: str
    dwh_code: Optional[str] = None
    hostname: Optional[str] = None   # Nom du poste client (optionnel, envoyé par l'app desktop/mobile)


class LoginResponse(BaseModel):
    success: bool
    message: str
    user: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None
    must_change_password: bool = False
    first_login_user_id: Optional[int] = None


class SwitchDWHRequest(BaseModel):
    dwh_code: str


class SwitchSocieteRequest(BaseModel):
    societe_code: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


# =============================================================================
# UTILITAIRES
# =============================================================================

def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _verify_password(password: str, password_hash: str) -> bool:
    return _hash_password(password) == password_hash


def _query_client_user(dwh_code: str, username: str) -> Optional[Dict[str, Any]]:
    """
    Cherche un utilisateur dans la base client OptiBoard_{dwh_code}.APP_Users.
    Retourne None si la base n'existe pas ou si l'utilisateur est absent.
    """
    if not client_manager.has_client_db(dwh_code):
        return None
    try:
        from ..database_unified import execute_client
        rows = execute_client(
            "SELECT id, username, password_hash, nom, prenom, email, role_dwh, actif, ISNULL(must_change_password,0) AS must_change_password FROM APP_Users WHERE username = ?",
            (username,),
            dwh_code=dwh_code,
            use_cache=False,
        )
        return rows[0] if rows else None
    except Exception as e:
        logger.debug(f"_query_client_user({dwh_code}, {username}): {e}")
        return None


def _update_last_login_client(dwh_code: str, user_id: int) -> None:
    """Met à jour derniere_connexion dans la base client."""
    try:
        write_client(
            "UPDATE APP_Users SET derniere_connexion = GETDATE() WHERE id = ?",
            (user_id,),
            dwh_code=dwh_code,
        )
    except Exception as e:
        logger.debug(f"_update_last_login_client: {e}")


def _get_user_restrictions(dwh_code: str, user_id: int) -> Dict[str, Any]:
    """Récupère les restrictions d'accès d'un utilisateur client (colonnes optionnelles)."""
    try:
        rows = execute_client(
            "SELECT ip_autorises, pc_autorises, heure_debut, heure_fin, jours_autorises FROM APP_Users WHERE id = ?",
            (user_id,), dwh_code=dwh_code, use_cache=False,
        )
        return rows[0] if rows else {}
    except Exception:
        return {}  # Colonnes pas encore créées — aucune restriction


def _check_access_restrictions(
    restrictions: Dict[str, Any],
    hostname: Optional[str],
    client_ip: str,
) -> None:
    """
    Vérifie les restrictions IP / poste / plage horaire / jours.
    Lève HTTPException 403 si une restriction est violée.
    """
    # ── IP ──────────────────────────────────────────────────────────────────
    ip_autorises = (restrictions.get("ip_autorises") or "").strip()
    if ip_autorises:
        allowed = [ip.strip() for ip in ip_autorises.split(",") if ip.strip()]
        if allowed and not any(client_ip == ip or client_ip.startswith(ip) for ip in allowed):
            raise HTTPException(status_code=403, detail="Connexion refusée — adresse IP non autorisée")

    # ── Poste (hostname) ─────────────────────────────────────────────────────
    pc_autorises = (restrictions.get("pc_autorises") or "").strip()
    if pc_autorises and hostname:
        allowed_pcs = [pc.strip().lower() for pc in pc_autorises.split(",") if pc.strip()]
        if allowed_pcs and hostname.lower() not in allowed_pcs:
            raise HTTPException(status_code=403, detail="Connexion refusée — poste non autorisé")

    # ── Plage horaire ────────────────────────────────────────────────────────
    heure_debut = restrictions.get("heure_debut")
    heure_fin   = restrictions.get("heure_fin")
    if heure_debut is not None and heure_fin is not None:
        h = datetime.now().hour
        if heure_debut <= heure_fin:
            ok = heure_debut <= h < heure_fin
        else:           # passe minuit
            ok = h >= heure_debut or h < heure_fin
        if not ok:
            raise HTTPException(
                status_code=403,
                detail=f"Connexion refusée — hors de la plage autorisée ({heure_debut:02d}h–{heure_fin:02d}h)",
            )

    # ── Jours autorisés ──────────────────────────────────────────────────────
    jours_autorises = (restrictions.get("jours_autorises") or "").strip()
    if jours_autorises:
        allowed_days = [int(d) for d in jours_autorises.split(",") if d.strip().isdigit()]
        if allowed_days:
            # weekday() : 0=Lun … 6=Dim → +1 pour avoir 1=Lun … 7=Dim
            current_day = datetime.now().weekday() + 1
            if current_day not in allowed_days:
                raise HTTPException(status_code=403, detail="Connexion refusée — jour non autorisé")


# =============================================================================
# ROUTE — LOGIN
# =============================================================================

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, http_request: Request):
    """
    Authentification multi-tenant.

    Si dwh_code fourni :
      → tente la base client (Règle 2)
      → repli sur la base centrale si absent (superadmin / backward compat)

    Si dwh_code absent :
      → base centrale uniquement
    """
    user = None
    from_client_db = False

    # ── Étape 0 : refuser accès DWH démo aux utilisateurs clients ──────────
    if request.dwh_code and request.dwh_code.upper() in _DEMO_DWH_CODES:
        raise HTTPException(status_code=403, detail="Ce client est réservé à la démonstration — accès non autorisé")

    # ── Étape 1 : chercher dans la base client si dwh_code fourni ──────────
    if request.dwh_code:
        client_user = _query_client_user(request.dwh_code, request.username)
        if client_user:
            if not client_user.get("actif"):
                raise HTTPException(status_code=401, detail="Compte désactivé")
            # Premier login : password_hash NULL → forcer création du mot de passe
            if client_user.get("password_hash") is None:
                return LoginResponse(
                    success=True,
                    message="Premier login — création du mot de passe requise",
                    must_change_password=True,
                    first_login_user_id=client_user["id"],
                )
            if not _verify_password(request.password, client_user["password_hash"]):
                raise HTTPException(status_code=401, detail="Identifiants invalides")
            # Vérifier les restrictions avancées (IP / poste / plage horaire / jours)
            client_ip = (
                http_request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
                or (http_request.client.host if http_request.client else "")
            )
            restrictions = _get_user_restrictions(request.dwh_code, client_user["id"])
            _check_access_restrictions(restrictions, request.hostname, client_ip)
            user = client_user
            from_client_db = True
            _update_last_login_client(request.dwh_code, user["id"])
            logger.info(f"Login client '{request.username}' sur {request.dwh_code}")

    # ── Étape 2 : base centrale (superadmin uniquement, sans dwh_code) ─────
    if user is None:
        if request.dwh_code:
            # dwh_code fourni mais user absent/invalide dans la base client
            # → accès refusé, pas de repli sur OptiBoard_SaaS (isolation tenant)
            raise HTTPException(status_code=401, detail="Identifiants invalides")
        central_users = execute_central(
            "SELECT id, username, password_hash, nom, prenom, email, role_global, actif FROM APP_Users WHERE username = ?",
            (request.username,),
            use_cache=False,
        )
        if not central_users:
            raise HTTPException(status_code=401, detail="Identifiants invalides")
        central_user = central_users[0]

        if not central_user.get("actif"):
            raise HTTPException(status_code=401, detail="Compte désactivé")
        if not _verify_password(request.password, central_user["password_hash"]):
            raise HTTPException(status_code=401, detail="Identifiants invalides")

        user = central_user
        write_central(
            "UPDATE APP_Users SET derniere_connexion = GETDATE() WHERE id = ?",
            (user["id"],),
        )

    # ── Étape 3 : construire le contexte ────────────────────────────────────
    # Pour un user client DB : on adapte le format pour create_user_context
    if from_client_db:
        user_for_context = {
            "id": user["id"],
            "username": user["username"],
            "nom":    user.get("nom")    or "",
            "prenom": user.get("prenom") or "",
            "email":  user.get("email")  or "",
            "role_global": user.get("role_dwh", "user"),  # rôle DWH utilisé comme global
        }
    else:
        user_for_context = user

    try:
        context = create_user_context(user_for_context, request.dwh_code)
    except Exception as e:
        logger.warning(f"create_user_context error: {e}")
        context = UserContext(
            user_id=user["id"],
            username=user["username"],
            nom=    user.get("nom")    or "",
            prenom= user.get("prenom") or "",
            email=  user.get("email")  or "",
            role_global=user.get("role_global") or user.get("role_dwh", "user"),
            dwh_accessibles=[],
            societes_accessibles=[],
            pages_accessibles=[],
        )

    # ── has_client_db & current_dwh ─────────────────────────────────────────
    # Pour un user CLIENT (from_client_db=True) : il vient d'une base qui EXISTE
    # → pas besoin de chercher dans context (qui est vide pour les users client)
    # → forcer current_dwh = dwh_code du login, has_client_db = True
    if from_client_db and request.dwh_code:
        has_client_db   = True
        effective_dwh   = {"code": request.dwh_code, "nom": request.dwh_code}
        effective_role  = user.get("role_dwh", "user")
    else:
        has_client_db  = client_manager.has_client_db(context.current_dwh_code) if context.current_dwh_code else False
        effective_dwh  = {"code": context.current_dwh_code, "nom": context.current_dwh_nom} if context.current_dwh_code else None
        effective_role = context.role_dwh

    return LoginResponse(
        success=True,
        message="Connexion réussie",
        user={
            "id": user["id"],
            "username": user["username"],
            "nom":    user.get("nom")    or "",
            "prenom": user.get("prenom") or "",
            "email":  user.get("email")  or "",
            "role_global": user.get("role_global") or user.get("role_dwh", "user"),
            "from_client_db": from_client_db,
        },
        context={
            "current_dwh": effective_dwh,
            "role_dwh":    effective_role,
            "dwh_accessibles":    context.dwh_accessibles,
            "societes_accessibles": context.societes_accessibles,
            "pages_accessibles":  context.pages_accessibles,
            "has_client_db": has_client_db,
        },
    )


# =============================================================================
# ROUTE — CLIENT INFO (publique, sans authentification)
# =============================================================================

@router.get("/client-info")
async def get_client_info(code: str):
    """
    Retourne le nom et logo d'un client DWH à partir de son code.
    Route publique — utilisée par la page de login pour afficher le branding.
    """
    results = execute_central(
        "SELECT nom, raison_sociale, logo_url, ISNULL(is_demo,0) AS is_demo FROM APP_DWH WHERE code = ? AND actif = 1",
        (code.upper(),), use_cache=False,
    )
    if not results:
        raise HTTPException(status_code=404, detail="Client non trouvé")
    # DWH démo : inaccessible aux clients via URL directe
    is_demo = bool(results[0].get("is_demo")) or code.upper() in _DEMO_DWH_CODES
    if is_demo:
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    row = results[0]
    return {
        "success": True,
        "nom": row.get("raison_sociale") or row.get("nom"),
        "logo_url": row.get("logo_url"),
        "code": code.upper(),
    }


# =============================================================================
# ROUTES — SWITCH DWH / SOCIÉTÉ
# =============================================================================

@router.post("/switch-dwh")
async def switch_dwh(
    request: SwitchDWHRequest,
    user_id: int = Header(..., alias="X-User-Id"),
):
    """Change le DWH actif. Vérifie les droits d'accès."""
    # Vérifier l'accès (base centrale ou rôle admin)
    access = execute_central(
        """SELECT ud.dwh_code, ud.role_dwh, d.nom
           FROM APP_UserDWH ud
           INNER JOIN APP_DWH d ON ud.dwh_code = d.code
           WHERE ud.user_id = ? AND ud.dwh_code = ? AND d.actif = 1""",
        (user_id, request.dwh_code),
        use_cache=False,
    )
    if not access:
        user = execute_central("SELECT role_global FROM APP_Users WHERE id = ?", (user_id,), use_cache=False)
        if not user or user[0].get("role_global") != "superadmin":
            # Vérifier dans la base client (Règle 2 : admin_client)
            try:
                from ..database_unified import execute_client
                client_user = execute_client(
                    "SELECT role_dwh FROM APP_Users WHERE id = ?",
                    (user_id,),
                    dwh_code=request.dwh_code,
                    use_cache=False,
                )
                if not client_user or client_user[0].get("role_dwh") not in ("admin_client",):
                    raise HTTPException(status_code=403, detail="Accès non autorisé à ce DWH")
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(status_code=403, detail="Accès non autorisé à ce DWH")

    user_data = execute_central(
        "SELECT id, username, nom, prenom, email, role_global FROM APP_Users WHERE id = ?",
        (user_id,), use_cache=False,
    )
    if not user_data:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    context = create_user_context(user_data[0], request.dwh_code)
    return {
        "success": True,
        "current_dwh": {"code": context.current_dwh_code, "nom": context.current_dwh_nom},
        "role_dwh": context.role_dwh,
        "societes_accessibles": context.societes_accessibles,
    }


@router.post("/switch-societe")
async def switch_societe(
    request: SwitchSocieteRequest,
    user_id: int = Header(..., alias="X-User-Id"),
    dwh_code: str = Header(..., alias="X-DWH-Code"),
):
    """Change la société active (filtre les données)."""
    if request.societe_code:
        access = execute_central(
            "SELECT societe_code FROM APP_UserSocietes WHERE user_id=? AND dwh_code=? AND societe_code=?",
            (user_id, dwh_code, request.societe_code),
            use_cache=False,
        )
        if not access:
            user = execute_central(
                "SELECT u.role_global, ud.role_dwh FROM APP_Users u LEFT JOIN APP_UserDWH ud ON u.id=ud.user_id AND ud.dwh_code=? WHERE u.id=?",
                (dwh_code, user_id), use_cache=False,
            )
            if user:
                is_admin = (
                    user[0].get("role_global") == "superadmin"
                    or user[0].get("role_dwh") == "admin_client"
                )
                if not is_admin:
                    raise HTTPException(status_code=403, detail="Accès non autorisé à cette société")

    return {"success": True, "societe_active": request.societe_code, "message": f"Filtre société: {request.societe_code or 'Toutes'}"}


# =============================================================================
# ROUTES — CONTEXTE / LISTE DWH / LISTE SOCIÉTÉS
# =============================================================================

@router.get("/context")
async def get_user_context(
    user_id: int = Header(..., alias="X-User-Id"),
    dwh_code: Optional[str] = Header(None, alias="X-DWH-Code"),
):
    """Récupère le contexte complet de l'utilisateur."""
    user_data = execute_central(
        "SELECT id, username, nom, prenom, email, role_global FROM APP_Users WHERE id = ?",
        (user_id,), use_cache=False,
    )
    if not user_data:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    context = create_user_context(user_data[0], dwh_code)
    return {
        "user": {"id": context.user_id, "username": context.username, "nom": context.nom, "prenom": context.prenom, "email": context.email, "role_global": context.role_global},
        "current_dwh": {"code": context.current_dwh_code, "nom": context.current_dwh_nom} if context.current_dwh_code else None,
        "role_dwh": context.role_dwh,
        "dwh_accessibles": context.dwh_accessibles,
        "societes_accessibles": context.societes_accessibles,
        "pages_accessibles": context.pages_accessibles,
        "is_admin": context.is_admin(),
    }


@router.get("/dwh-list")
async def get_dwh_list(user_id: int = Header(..., alias="X-User-Id")):
    """Liste les DWH accessibles par l'utilisateur."""
    user = execute_central("SELECT role_global FROM APP_Users WHERE id = ?", (user_id,), use_cache=False)
    if user and user[0].get("role_global") == "superadmin":
        return execute_central("SELECT code, nom, raison_sociale, logo_url, 0 AS is_default FROM APP_DWH WHERE actif=1 ORDER BY nom", use_cache=False)
    return get_user_dwh_list(user_id)


@router.get("/societes-list")
async def get_societes_list(
    user_id: int = Header(..., alias="X-User-Id"),
    dwh_code: str = Header(..., alias="X-DWH-Code"),
):
    """Liste les sociétés accessibles dans le DWH actif."""
    user = execute_central(
        "SELECT u.role_global, ud.role_dwh FROM APP_Users u LEFT JOIN APP_UserDWH ud ON u.id=ud.user_id AND ud.dwh_code=? WHERE u.id=?",
        (dwh_code, user_id), use_cache=False,
    )
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    is_admin = (
        user[0].get("role_global") == "superadmin"
        or user[0].get("role_dwh") == "admin_client"
    )
    return get_all_dwh_societes(dwh_code) if is_admin else get_user_societes(user_id, dwh_code)


# =============================================================================
# ROUTES — MOT DE PASSE
# =============================================================================

@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    user_id: int = Header(..., alias="X-User-Id"),
    dwh_code: Optional[str] = Header(None, alias="X-DWH-Code"),
):
    """Change le mot de passe (base client en priorité, puis centrale)."""
    # Chercher dans la base client si disponible (Règle 2)
    if dwh_code and client_manager.has_client_db(dwh_code):
        try:
            from ..database_unified import execute_client
            rows = execute_client("SELECT password_hash FROM APP_Users WHERE id=?", (user_id,), dwh_code=dwh_code, use_cache=False)
            if rows:
                if not _verify_password(request.current_password, rows[0]["password_hash"]):
                    raise HTTPException(status_code=401, detail="Mot de passe actuel incorrect")
                write_client("UPDATE APP_Users SET password_hash=? WHERE id=?", (_hash_password(request.new_password), user_id), dwh_code=dwh_code)
                return {"success": True, "message": "Mot de passe modifié"}
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"change_password client DB: {e}")

    # Repli sur centrale
    user = execute_central("SELECT password_hash FROM APP_Users WHERE id=?", (user_id,), use_cache=False)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    if not _verify_password(request.current_password, user[0]["password_hash"]):
        raise HTTPException(status_code=401, detail="Mot de passe actuel incorrect")
    write_central("UPDATE APP_Users SET password_hash=? WHERE id=?", (_hash_password(request.new_password), user_id))
    return {"success": True, "message": "Mot de passe modifié"}


# =============================================================================
# ROUTE — PREMIER LOGIN : définir le mot de passe
# =============================================================================

class SetFirstPasswordRequest(BaseModel):
    user_id: int
    dwh_code: str
    new_password: str


@router.post("/set-first-password")
async def set_first_password(request: SetFirstPasswordRequest):
    """
    Définit le mot de passe d'un utilisateur lors de son premier login.
    Requiert que must_change_password=1 et password_hash IS NULL.
    """
    if len(request.new_password) < 6:
        raise HTTPException(status_code=400, detail="Le mot de passe doit contenir au moins 6 caractères")

    if not client_manager.has_client_db(request.dwh_code):
        raise HTTPException(status_code=404, detail="Base client introuvable")

    try:
        from ..database_unified import execute_client, write_client as _write_client
        rows = execute_client(
            "SELECT id, must_change_password, password_hash FROM APP_Users WHERE id=? AND actif=1",
            (request.user_id,),
            dwh_code=request.dwh_code,
            use_cache=False,
        )
        if not rows:
            raise HTTPException(status_code=404, detail="Utilisateur introuvable")
        row = rows[0]
        if row.get("password_hash") is not None and not row.get("must_change_password"):
            raise HTTPException(status_code=403, detail="Ce compte a déjà un mot de passe défini")

        _write_client(
            "UPDATE APP_Users SET password_hash=?, must_change_password=0 WHERE id=?",
            (_hash_password(request.new_password), request.user_id),
            dwh_code=request.dwh_code,
        )
        return {"success": True, "message": "Mot de passe défini avec succès"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"set_first_password error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ROUTE — AUDIT LOG
# =============================================================================

@router.post("/log-action")
async def log_action(
    action: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    details: Optional[str] = None,
    user_id: int = Header(..., alias="X-User-Id"),
    dwh_code: Optional[str] = Header(None, alias="X-DWH-Code"),
):
    """Enregistre une action dans le log d'audit (base client si disponible)."""
    if dwh_code and client_manager.has_client_db(dwh_code):
        write_client(
            "INSERT INTO APP_AuditLog (user_id, action, entity_type, entity_id, details, date_action) VALUES (?,?,?,?,?,GETDATE())",
            (user_id, action, entity_type, entity_id, details),
            dwh_code=dwh_code,
        )
    else:
        write_central(
            "INSERT INTO APP_AuditLog (user_id, dwh_code, action, entity_type, entity_id, details, date_action) VALUES (?,?,?,?,?,?,GETDATE())",
            (user_id, dwh_code, action, entity_type, entity_id, details),
        )
    return {"success": True}


# =============================================================================
# ROUTES — GESTION UTILISATEURS CLIENT (admin_client)
# =============================================================================

class ClientUserCreate(BaseModel):
    username: str
    password: str
    nom: str
    prenom: str
    email: Optional[str] = ""
    role_dwh: str = "user"
    mobile_access: bool = True
    ip_autorises: Optional[str] = None      # IPs séparées par virgule
    pc_autorises: Optional[str] = None      # Noms de postes séparés par virgule
    heure_debut: Optional[int] = None       # 0-23
    heure_fin: Optional[int] = None         # 0-23
    jours_autorises: Optional[str] = None   # ex: "1,2,3,4,5"


class ClientUserUpdate(BaseModel):
    nom: Optional[str] = None
    prenom: Optional[str] = None
    email: Optional[str] = None
    role_dwh: Optional[str] = None
    actif: Optional[bool] = None
    mobile_access: Optional[bool] = None
    ip_autorises: Optional[str] = None
    pc_autorises: Optional[str] = None
    heure_debut: Optional[int] = None
    heure_fin: Optional[int] = None
    jours_autorises: Optional[str] = None


@router.get("/client-users")
async def get_client_users(dwh_code: Optional[str] = Header(None, alias="X-DWH-Code")):
    """Liste les utilisateurs de la base client."""
    if not dwh_code:
        raise HTTPException(status_code=400, detail="X-DWH-Code header requis")
    # Migrations douces — ajouter les colonnes avancées si absentes
    for col_sql in [
        "ALTER TABLE APP_Users ADD mobile_access BIT NOT NULL DEFAULT 1",
        "ALTER TABLE APP_Users ADD ip_autorises NVARCHAR(500) NULL",
        "ALTER TABLE APP_Users ADD pc_autorises NVARCHAR(500) NULL",
        "ALTER TABLE APP_Users ADD heure_debut TINYINT NULL",
        "ALTER TABLE APP_Users ADD heure_fin TINYINT NULL",
        "ALTER TABLE APP_Users ADD jours_autorises NVARCHAR(20) NULL",
    ]:
        try:
            write_client(col_sql, dwh_code=dwh_code)
        except Exception:
            pass  # Colonne déjà présente
    try:
        users = execute_client(
            """SELECT id, username, nom, prenom, email, role_dwh, actif,
                      ISNULL(mobile_access, 1) AS mobile_access,
                      ip_autorises, pc_autorises, heure_debut, heure_fin, jours_autorises
               FROM APP_Users ORDER BY nom, prenom""",
            dwh_code=dwh_code,
            use_cache=False,
        )
        return {"success": True, "data": users}
    except Exception as e:
        logger.warning(f"[client-users] {dwh_code}: {e}")
        return {"success": True, "data": [], "warning": "Base client non encore initialisée"}


@router.post("/client-users")
async def create_client_user(data: ClientUserCreate, dwh_code: Optional[str] = Header(None, alias="X-DWH-Code")):
    """Crée un utilisateur dans la base client."""
    if not dwh_code:
        raise HTTPException(status_code=400, detail="X-DWH-Code header requis")
    try:
        existing = execute_client(
            "SELECT id FROM APP_Users WHERE username = ?",
            (data.username,), dwh_code=dwh_code,
        )
        if existing:
            raise HTTPException(status_code=409, detail=f"L'identifiant '{data.username}' est déjà utilisé")
        password_hash = hashlib.sha256(data.password.encode()).hexdigest()
        mobile_val = 1 if data.role_dwh == "admin_client" else (1 if data.mobile_access else 0)
        write_client(
            """INSERT INTO APP_Users
                 (username, password_hash, nom, prenom, email, role_dwh, actif,
                  mobile_access, ip_autorises, pc_autorises, heure_debut, heure_fin, jours_autorises)
               VALUES (?,?,?,?,?,?,1,?,?,?,?,?,?)""",
            (data.username, password_hash, data.nom, data.prenom, data.email or "", data.role_dwh,
             mobile_val, data.ip_autorises or None, data.pc_autorises or None,
             data.heure_debut, data.heure_fin, data.jours_autorises or None),
            dwh_code=dwh_code,
        )
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/client-users/{user_id}")
async def update_client_user(
    user_id: int,
    data: ClientUserUpdate,
    dwh_code: Optional[str] = Header(None, alias="X-DWH-Code"),
):
    """Met à jour un utilisateur de la base client."""
    if not dwh_code:
        raise HTTPException(status_code=400, detail="X-DWH-Code header requis")
    try:
        updates, params = [], []
        if data.nom is not None:           updates.append("nom=?");           params.append(data.nom)
        if data.prenom is not None:        updates.append("prenom=?");        params.append(data.prenom)
        if data.email is not None:         updates.append("email=?");         params.append(data.email)
        if data.role_dwh is not None:      updates.append("role_dwh=?");      params.append(data.role_dwh)
        if data.actif is not None:         updates.append("actif=?");         params.append(1 if data.actif else 0)
        if data.mobile_access is not None: updates.append("mobile_access=?"); params.append(1 if data.mobile_access else 0)
        if data.ip_autorises is not None:  updates.append("ip_autorises=?");  params.append(data.ip_autorises or None)
        if data.pc_autorises is not None:  updates.append("pc_autorises=?");  params.append(data.pc_autorises or None)
        if data.heure_debut is not None:   updates.append("heure_debut=?");   params.append(data.heure_debut)
        if data.heure_fin is not None:     updates.append("heure_fin=?");     params.append(data.heure_fin)
        if data.jours_autorises is not None: updates.append("jours_autorises=?"); params.append(data.jours_autorises or None)
        if not updates:
            return {"success": True}
        params.append(user_id)
        write_client(f"UPDATE APP_Users SET {', '.join(updates)} WHERE id=?", tuple(params), dwh_code=dwh_code)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/client-users/{user_id}")
async def delete_client_user(user_id: int, dwh_code: Optional[str] = Header(None, alias="X-DWH-Code")):
    """Supprime un utilisateur de la base client."""
    if not dwh_code:
        raise HTTPException(status_code=400, detail="X-DWH-Code header requis")
    try:
        # Nettoyer d'abord les tables FK NO ACTION avant de supprimer l'utilisateur
        try:
            write_client("DELETE FROM APP_User_Roles WHERE user_id=?", (user_id,), dwh_code=dwh_code)
        except Exception:
            pass  # Table inexistante ou déjà vide
        write_client("DELETE FROM APP_Users WHERE id=?", (user_id,), dwh_code=dwh_code)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/client-users/{user_id}/reset-password")
async def reset_client_user_password(user_id: int, dwh_code: Optional[str] = Header(None, alias="X-DWH-Code")):
    """Réinitialise le mot de passe d'un utilisateur client à son identifiant."""
    if not dwh_code:
        raise HTTPException(status_code=400, detail="X-DWH-Code header requis")
    try:
        rows = execute_client("SELECT username FROM APP_Users WHERE id=?", (user_id,), dwh_code=dwh_code)
        if not rows:
            raise HTTPException(status_code=404, detail="Utilisateur introuvable")
        username = rows[0]["username"]
        new_hash = hashlib.sha256(username.encode()).hexdigest()
        write_client("UPDATE APP_Users SET password_hash=? WHERE id=?", (new_hash, user_id), dwh_code=dwh_code)
        return {"success": True, "message": f"Mot de passe réinitialisé à '{username}'"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
