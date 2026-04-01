"""Routes pour la gestion des favoris et rapports récents utilisateur"""
from fastapi import APIRouter, Header
from pydantic import BaseModel
from typing import Optional
import json

from ..database_unified import execute_central as execute_query, central_cursor as get_db_cursor, execute_client

router = APIRouter(prefix="/api/favorites", tags=["favorites"])

VALID_TYPES = {"gridview", "dashboard", "pivot"}
ROUTE_MAP = {"gridview": "/grid", "dashboard": "/view", "pivot": "/pivot-v2"}


# ==================== SCHEMAS ====================

class FavoriteCreate(BaseModel):
    report_type: str
    report_id: int
    nom: str


class RecentVisit(BaseModel):
    report_type: str
    report_id: int
    nom: str


# ==================== INIT TABLES ====================

def init_favorites_tables():
    """Crée les tables favoris et récents si elles n'existent pas."""
    sql_favorites = """
    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'APP_UserFavorites')
    CREATE TABLE APP_UserFavorites (
        id          INT IDENTITY(1,1) PRIMARY KEY,
        user_id     INT          NOT NULL,
        report_type NVARCHAR(50) NOT NULL,
        report_id   INT          NOT NULL,
        nom         NVARCHAR(255) NOT NULL,
        pinned_order INT          DEFAULT 0,
        created_at  DATETIME     DEFAULT GETDATE(),
        CONSTRAINT UQ_UserFav UNIQUE (user_id, report_type, report_id)
    )
    """
    sql_recents = """
    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'APP_UserRecents')
    CREATE TABLE APP_UserRecents (
        id          INT IDENTITY(1,1) PRIMARY KEY,
        user_id     INT          NOT NULL,
        report_type NVARCHAR(50) NOT NULL,
        report_id   INT          NOT NULL,
        nom         NVARCHAR(255) NOT NULL,
        visited_at  DATETIME     DEFAULT GETDATE(),
        CONSTRAINT UQ_UserRecent UNIQUE (user_id, report_type, report_id)
    )
    """
    try:
        with get_db_cursor() as cur:
            cur.execute(sql_favorites)
            cur.execute(sql_recents)
        return True
    except Exception as e:
        print(f"[FAVORITES] Erreur init tables: {e}")
        return False


# ==================== FAVORITES CRUD ====================

@router.get("")
async def get_favorites(user_id: int):
    """Retourne les favoris de l'utilisateur, triés par pinned_order."""
    try:
        init_favorites_tables()
        rows = execute_query(
            "SELECT * FROM APP_UserFavorites WHERE user_id = ? ORDER BY pinned_order, created_at",
            (user_id,), use_cache=False
        )
        for r in rows:
            r["url"] = f"{ROUTE_MAP.get(r['report_type'], '/grid')}/{r['report_id']}"
        return {"success": True, "data": rows}
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}


@router.get("/check")
async def check_favorite(user_id: int, report_type: str, report_id: int):
    """Vérifie si un rapport est en favori."""
    try:
        init_favorites_tables()
        rows = execute_query(
            "SELECT id FROM APP_UserFavorites WHERE user_id = ? AND report_type = ? AND report_id = ?",
            (user_id, report_type, report_id), use_cache=False
        )
        return {"success": True, "is_favorite": len(rows) > 0}
    except Exception as e:
        return {"success": False, "error": str(e), "is_favorite": False}


@router.post("")
async def add_favorite(fav: FavoriteCreate, user_id: int):
    """Ajoute un rapport aux favoris."""
    if fav.report_type not in VALID_TYPES:
        return {"success": False, "error": "Type de rapport invalide"}
    try:
        init_favorites_tables()
        # Vérifier si déjà en favori
        exists = execute_query(
            "SELECT id FROM APP_UserFavorites WHERE user_id = ? AND report_type = ? AND report_id = ?",
            (user_id, fav.report_type, fav.report_id), use_cache=False
        )
        if exists:
            return {"success": True, "message": "Déjà en favori", "already_exists": True}

        with get_db_cursor() as cur:
            cur.execute(
                "INSERT INTO APP_UserFavorites (user_id, report_type, report_id, nom) VALUES (?, ?, ?, ?)",
                (user_id, fav.report_type, fav.report_id, fav.nom)
            )
        return {"success": True, "message": "Ajouté aux favoris"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.delete("")
async def remove_favorite(user_id: int, report_type: str, report_id: int):
    """Retire un rapport des favoris."""
    try:
        with get_db_cursor() as cur:
            cur.execute(
                "DELETE FROM APP_UserFavorites WHERE user_id = ? AND report_type = ? AND report_id = ?",
                (user_id, report_type, report_id)
            )
        return {"success": True, "message": "Retiré des favoris"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.put("/reorder")
async def reorder_favorites(user_id: int, ordered_ids: list[int]):
    """Met à jour l'ordre des favoris."""
    try:
        with get_db_cursor() as cur:
            for i, fav_id in enumerate(ordered_ids):
                cur.execute(
                    "UPDATE APP_UserFavorites SET pinned_order = ? WHERE id = ? AND user_id = ?",
                    (i, fav_id, user_id)
                )
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== RECENTS ====================


@router.get("/recents")
async def get_recents(user_id: int, limit: int = 8):
    """Retourne les derniers rapports visités."""
    try:
        init_favorites_tables()
        rows = execute_query(
            "SELECT TOP (?) * FROM APP_UserRecents WHERE user_id = ? ORDER BY visited_at DESC",
            (limit, user_id), use_cache=False
        )
        for r in rows:
            r["url"] = f"{ROUTE_MAP.get(r['report_type'], '/grid')}/{r['report_id']}"
        return {"success": True, "data": rows}
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}


@router.post("/recents")
async def track_recent(visit: RecentVisit, user_id: int):
    """Enregistre ou met à jour la visite d'un rapport."""
    if visit.report_type not in VALID_TYPES:
        return {"success": False, "error": "Type invalide"}
    try:
        init_favorites_tables()
        # UPSERT : mettre à jour si existe, sinon insérer
        exists = execute_query(
            "SELECT id FROM APP_UserRecents WHERE user_id = ? AND report_type = ? AND report_id = ?",
            (user_id, visit.report_type, visit.report_id), use_cache=False
        )
        with get_db_cursor() as cur:
            if exists:
                cur.execute(
                    "UPDATE APP_UserRecents SET visited_at = GETDATE(), nom = ? WHERE user_id = ? AND report_type = ? AND report_id = ?",
                    (visit.nom, user_id, visit.report_type, visit.report_id)
                )
            else:
                # Limiter à 20 recents : supprimer le plus ancien si dépassé
                count = execute_query(
                    "SELECT COUNT(*) AS cnt FROM APP_UserRecents WHERE user_id = ?",
                    (user_id,), use_cache=False
                )
                if count and count[0].get("cnt", 0) >= 20:
                    cur.execute(
                        "DELETE FROM APP_UserRecents WHERE id = (SELECT TOP 1 id FROM APP_UserRecents WHERE user_id = ? ORDER BY visited_at ASC)",
                        (user_id,)
                    )
                cur.execute(
                    "INSERT INTO APP_UserRecents (user_id, report_type, report_id, nom) VALUES (?, ?, ?, ?)",
                    (user_id, visit.report_type, visit.report_id, visit.nom)
                )
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== ROLE REPORTS ====================

@router.get("/role-reports")
async def get_role_reports(user_id: int, x_dwh_code: Optional[str] = Header(None)):
    """Retourne les rapports assignés au(x) rôle(s) de l'utilisateur."""
    try:
        if not x_dwh_code:
            return {"success": True, "data": []}

        # Vérifier si superadmin plateforme (APP_Users.role_global)
        user_rows = execute_query(
            "SELECT role_global FROM APP_Users WHERE id = ?",
            (user_id,), use_cache=False,
        )
        is_superadmin = bool(user_rows and user_rows[0].get("role_global") in ("superadmin", "admin"))

        # Récupérer les rôles actifs de l'utilisateur (base client)
        roles = execute_client(
            """
            SELECT r.id, r.is_admin
            FROM APP_User_Roles ur
            JOIN APP_Roles r ON r.id = ur.role_id
            WHERE ur.user_id = ? AND r.actif = 1
            """,
            (user_id,),
            dwh_code=x_dwh_code,
            use_cache=False,
        )

        is_role_admin = bool(roles and any(bool(r["is_admin"]) for r in roles))

        # Superadmin ou rôle admin → tous les dashboards publics
        if is_superadmin or is_role_admin or not roles:
            pub = execute_query(
                "SELECT id, nom FROM APP_Dashboards WHERE is_public = 1 AND actif = 1 ORDER BY id",
                use_cache=False,
            )
            return {
                "success": True,
                "is_admin": True,
                "data": [
                    {"report_type": "dashboard", "report_id": r["id"],
                     "nom": r["nom"], "url": f"/view/{r['id']}"}
                    for r in (pub or [])
                ],
            }

        role_ids = [r["id"] for r in roles]
        placeholders = ",".join("?" * len(role_ids))

        # Récupérer les rapports avec can_view=1 (base client)
        report_rows = execute_client(
            f"""
            SELECT DISTINCT report_type, report_id
            FROM APP_Role_Reports
            WHERE role_id IN ({placeholders}) AND can_view = 1
            """,
            tuple(role_ids),
            dwh_code=x_dwh_code,
            use_cache=False,
        )
        if not report_rows:
            return {"success": True, "data": []}

        # Regrouper par type
        by_type = {"dashboard": [], "gridview": [], "pivot": []}
        for row in report_rows:
            rtype = row["report_type"]
            if rtype in by_type:
                by_type[rtype].append(row["report_id"])

        results = []

        # Récupérer les noms depuis la base centrale
        if by_type["dashboard"]:
            ph = ",".join("?" * len(by_type["dashboard"]))
            rows = execute_query(
                f"SELECT id, nom FROM APP_Dashboards WHERE id IN ({ph})",
                tuple(by_type["dashboard"]), use_cache=False,
            )
            for r in rows:
                results.append({
                    "report_type": "dashboard",
                    "report_id": r["id"],
                    "nom": r["nom"],
                    "url": f"/view/{r['id']}",
                })

        if by_type["gridview"]:
            ph = ",".join("?" * len(by_type["gridview"]))
            rows = execute_query(
                f"SELECT id, nom FROM APP_GridViews WHERE id IN ({ph})",
                tuple(by_type["gridview"]), use_cache=False,
            )
            for r in rows:
                results.append({
                    "report_type": "gridview",
                    "report_id": r["id"],
                    "nom": r["nom"],
                    "url": f"/grid/{r['id']}",
                })

        if by_type["pivot"]:
            ph = ",".join("?" * len(by_type["pivot"]))
            rows = execute_query(
                f"SELECT id, nom FROM APP_Pivots_V2 WHERE id IN ({ph})",
                tuple(by_type["pivot"]), use_cache=False,
            )
            for r in rows:
                results.append({
                    "report_type": "pivot",
                    "report_id": r["id"],
                    "nom": r["nom"],
                    "url": f"/pivot-v2/{r['id']}",
                })

        return {"success": True, "data": results}
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}
