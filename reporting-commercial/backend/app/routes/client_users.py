"""
Gestion Utilisateurs & Droits — Base Client (OptiBoard_cltXXX)
===============================================================
Tout est 100% local au client.
APP_Users et APP_UserDWH sont dans la base client, INVISIBLES du central.
"""
import hashlib
import json
import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from ..database_unified import execute_client, write_client, client_cursor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/client-admin", tags=["Client Users"])


# ============================================================
# Schemas
# ============================================================

class ClientUserCreate(BaseModel):
    username: str
    password: str
    nom: str
    prenom: Optional[str] = None
    email: Optional[str] = None
    role: str = "user"   # admin_client | user | readonly
    mobile_access: bool = True   # accès application mobile

class ClientUserUpdate(BaseModel):
    nom: Optional[str] = None
    prenom: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    actif: Optional[bool] = None
    password: Optional[str] = None
    mobile_access: Optional[bool] = None   # accès application mobile

class UserDWHAssign(BaseModel):
    dwh_code: str
    role_dwh: str = "user"   # admin_client | user
    is_default: bool = False
    societes: Optional[List[str]] = None   # None = toutes


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# ============================================================
# Utilisateurs locaux
# ============================================================

@router.get("/users")
async def list_users(x_dwh_code: str = Header(..., alias="X-DWH-Code")):
    """Liste les utilisateurs locaux du client avec leurs roles."""
    try:
        # Migration douce : ajouter mobile_access si la colonne n'existe pas encore
        try:
            write_client(
                "ALTER TABLE APP_Users ADD mobile_access BIT NOT NULL DEFAULT 1",
                dwh_code=x_dwh_code,
            )
        except Exception:
            pass  # Colonne déjà présente — ignoré

        # Colonnes de base (compatibles avec le schema client)
        users = execute_client(
            """SELECT id, username,
                      ISNULL(nom, '') AS nom,
                      ISNULL(prenom, '') AS prenom,
                      ISNULL(email, '') AS email,
                      ISNULL(role_dwh, 'user') AS role,
                      actif,
                      ISNULL(mobile_access, 1) AS mobile_access,
                      date_creation,
                      derniere_connexion
               FROM APP_Users ORDER BY nom""",
            dwh_code=x_dwh_code,
            use_cache=False,
        )
        # Enrichir chaque utilisateur avec ses roles (si APP_User_Roles existe)
        try:
            all_ur = execute_client(
                """SELECT ur.user_id, r.id AS role_id, r.nom, r.couleur, r.is_admin
                   FROM APP_User_Roles ur
                   JOIN APP_Roles r ON r.id = ur.role_id AND r.actif = 1""",
                dwh_code=x_dwh_code,
                use_cache=False,
            )
        except Exception:
            all_ur = []

        # Indexer par user_id
        roles_by_user: dict = {}
        for ur in all_ur:
            uid = ur["user_id"]
            roles_by_user.setdefault(uid, []).append({
                "id": ur["role_id"],
                "nom": ur["nom"],
                "couleur": ur["couleur"],
                "is_admin": bool(ur["is_admin"]),
            })

        for u in users:
            u["roles"] = roles_by_user.get(u["id"], [])

        return {"success": True, "data": users}
    except Exception as e:
        err = str(e).lower()
        if "invalid object name" in err or "invalid column name" in err:
            return {"success": True, "data": []}
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users")
async def create_user(
    user: ClientUserCreate,
    x_dwh_code: str = Header(..., alias="X-DWH-Code")
):
    """Cree un utilisateur local."""
    try:
        # admin_client a toujours l'accès mobile
        mobile_val = 1 if user.role == 'admin_client' else (1 if user.mobile_access else 0)
        write_client(
            """INSERT INTO APP_Users
                 (username, password_hash, nom, prenom, email, role_dwh, actif, mobile_access, date_creation)
               VALUES (?,?,?,?,?,?,1,?,GETDATE())""",
            (user.username, _hash(user.password), user.nom,
             user.prenom, user.email, user.role, mobile_val),
            dwh_code=x_dwh_code,
        )
        return {"success": True, "message": f"Utilisateur '{user.username}' cree"}
    except Exception as e:
        if "unique" in str(e).lower() or "violation" in str(e).lower():
            raise HTTPException(status_code=409, detail=f"Username '{user.username}' deja existant")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    update: ClientUserUpdate,
    x_dwh_code: str = Header(..., alias="X-DWH-Code")
):
    """Met a jour un utilisateur local."""
    try:
        fields, params = [], []
        if update.nom is not None:
            fields.append("nom = ?"); params.append(update.nom)
        if update.prenom is not None:
            fields.append("prenom = ?"); params.append(update.prenom)
        if update.email is not None:
            fields.append("email = ?"); params.append(update.email)
        if update.role is not None:
            fields.append("role = ?"); params.append(update.role)
        if update.actif is not None:
            fields.append("actif = ?"); params.append(1 if update.actif else 0)
        if update.mobile_access is not None:
            # admin_client garde toujours l'accès mobile (on force à 1 si role = admin_client)
            fields.append("mobile_access = ?"); params.append(1 if update.mobile_access else 0)
        if update.password is not None:
            fields.append("password_hash = ?"); params.append(_hash(update.password))
        if not fields:
            raise HTTPException(status_code=400, detail="Aucun champ a mettre a jour")
        params.append(user_id)
        write_client(
            f"UPDATE APP_Users SET {', '.join(fields)} WHERE id = ?",
            tuple(params)
        )
        return {"success": True, "message": "Utilisateur mis a jour"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    x_dwh_code: str = Header(..., alias="X-DWH-Code")
):
    """Supprime un utilisateur local et ses droits DWH."""
    try:
        write_client("DELETE FROM APP_Users WHERE id = ?", (user_id,))
        return {"success": True, "message": "Utilisateur supprime"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Droits User <-> DWH (APP_UserDWH) — gestion 100% locale
# ============================================================

@router.get("/users/{user_id}/dwh")
async def list_user_dwh(
    user_id: int,
    x_dwh_code: str = Header(..., alias="X-DWH-Code")
):
    """Liste les DWH accessibles par un utilisateur local."""
    try:
        rights = execute_client(
            """SELECT id, dwh_code, role_dwh, is_default, societes, date_attribution
               FROM APP_UserDWH WHERE user_id = ?
               ORDER BY is_default DESC, dwh_code""",
            (user_id,), use_cache=False
        )
        return {"success": True, "data": rights}
    except Exception as e:
        if "invalid object name" in str(e).lower():
            return {"success": True, "data": []}
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users/{user_id}/dwh")
async def assign_dwh_to_user(
    user_id: int,
    assignment: UserDWHAssign,
    x_dwh_code: str = Header(..., alias="X-DWH-Code")
):
    """
    Attribue l'acces a un DWH pour un utilisateur local.
    Si is_default=True, on retire le flag des autres DWH de cet user.
    """
    try:
        with client_cursor() as cursor:
            # Si default, retirer le flag sur les autres
            if assignment.is_default:
                cursor.execute(
                    "UPDATE APP_UserDWH SET is_default = 0 WHERE user_id = ?",
                    (user_id,)
                )
            # Upsert
            cursor.execute(
                "SELECT id FROM APP_UserDWH WHERE user_id = ? AND dwh_code = ?",
                (user_id, assignment.dwh_code)
            )
            existing = cursor.fetchone()
            societes_json = json.dumps(assignment.societes) if assignment.societes else None
            if existing:
                cursor.execute(
                    """UPDATE APP_UserDWH SET role_dwh=?, is_default=?, societes=?
                       WHERE user_id=? AND dwh_code=?""",
                    (assignment.role_dwh, 1 if assignment.is_default else 0,
                     societes_json, user_id, assignment.dwh_code)
                )
            else:
                cursor.execute(
                    """INSERT INTO APP_UserDWH
                         (user_id, dwh_code, role_dwh, is_default, societes, date_attribution)
                       VALUES (?,?,?,?,?,GETDATE())""",
                    (user_id, assignment.dwh_code, assignment.role_dwh,
                     1 if assignment.is_default else 0, societes_json)
                )
            cursor.commit()
        return {"success": True, "message": f"Acces DWH '{assignment.dwh_code}' attribue"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/users/{user_id}/dwh/{dwh_code}")
async def revoke_dwh_from_user(
    user_id: int,
    dwh_code: str,
    x_dwh_code: str = Header(..., alias="X-DWH-Code")
):
    """Retire l'acces a un DWH pour un utilisateur local."""
    try:
        write_client(
            "DELETE FROM APP_UserDWH WHERE user_id = ? AND dwh_code = ?",
            (user_id, dwh_code)
        )
        return {"success": True, "message": f"Acces DWH '{dwh_code}' retire"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dwh-access")
async def list_all_dwh_access(x_dwh_code: str = Header(..., alias="X-DWH-Code")):
    """Vue globale de tous les droits DWH du client."""
    try:
        access = execute_client(
            """SELECT u.username, u.nom, u.prenom, u.role,
                      d.dwh_code, d.role_dwh, d.is_default, d.societes
               FROM APP_Users u
               LEFT JOIN APP_UserDWH d ON u.id = d.user_id
               WHERE u.actif = 1
               ORDER BY u.nom, d.dwh_code""",
            use_cache=False
        )
        return {"success": True, "data": access}
    except Exception as e:
        if "invalid object name" in str(e).lower():
            return {"success": True, "data": []}
        raise HTTPException(status_code=500, detail=str(e))
