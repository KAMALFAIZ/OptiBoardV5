"""
Gestion des Roles & Permissions — OptiBoard
============================================
Systeme de roles granulaire pour controler l'acces aux DWH, rapports et colonnes.
Toutes les donnees sont stockees dans la base client (OptiBoard_cltXX).

Tables gerees :
  APP_Roles          — definition des roles
  APP_Role_DWH       — DWH autorises par role
  APP_Role_Reports   — rapports autorises par role
  APP_Role_Columns   — colonnes masquees par role
  APP_User_Roles     — affectation users <-> roles
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from ..database_unified import execute_client, write_client, client_cursor, ClientDBNotFoundError, client_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Roles & Permissions"])

# ============================================================
# Cache d'initialisation (evite de recrer les tables a chaque appel)
# ============================================================
_init_done: set = set()


# ============================================================
# Schemas Pydantic
# ============================================================

class RoleCreate(BaseModel):
    nom: str
    description: Optional[str] = None
    couleur: Optional[str] = "#6366f1"
    is_admin: Optional[bool] = False


class RoleUpdate(BaseModel):
    nom: Optional[str] = None
    description: Optional[str] = None
    couleur: Optional[str] = None
    is_admin: Optional[bool] = None
    actif: Optional[bool] = None


class DWHSet(BaseModel):
    dwh_codes: List[str]


class ReportPermission(BaseModel):
    report_type: str           # 'dashboard' | 'gridview' | 'pivot'
    report_id: int
    can_view: Optional[bool] = True
    can_export: Optional[bool] = False
    can_schedule: Optional[bool] = False


class ColumnsSet(BaseModel):
    report_type: str
    report_id: int
    hidden_columns: List[str]


class UserRoleAssign(BaseModel):
    role_id: int


class FeatureSet(BaseModel):
    feature_codes: List[str]


# ============================================================
# Initialisation des tables
# ============================================================

_STANDARD_ROLES = [
    {"nom": "Administrateur",        "description": "Accès complet à toutes les fonctionnalités", "couleur": "#8B5CF6", "is_admin": True},
    {"nom": "Utilisateur",           "description": "Accès standard aux rapports et tableaux de bord", "couleur": "#3B82F6", "is_admin": False},
    {"nom": "Lecture seule",         "description": "Consultation uniquement, sans export ni modification", "couleur": "#6B7280", "is_admin": False},
    {"nom": "Commercial",            "description": "Accès aux ventes et au reporting commercial", "couleur": "#10B981", "is_admin": False},
    {"nom": "Responsable Commercial","description": "Supervision de l'équipe commerciale, KPIs et objectifs", "couleur": "#059669", "is_admin": False},
    {"nom": "Direction Générale",    "description": "Vue consolidée : CA, marges, recouvrement et tableaux de bord exécutifs", "couleur": "#1D4ED8", "is_admin": False},
    {"nom": "Finance",               "description": "Accès aux données financières et au recouvrement", "couleur": "#F59E0B", "is_admin": False},
    {"nom": "Comptabilité",          "description": "Facturation, règlements, balance âgée et clôtures", "couleur": "#D97706", "is_admin": False},
    {"nom": "Logistique",            "description": "Stocks, bons de livraison et prévisions de rupture", "couleur": "#0891B2", "is_admin": False},
    {"nom": "Achat",                 "description": "Commandes fournisseurs, délais et coûts d'approvisionnement", "couleur": "#7C3AED", "is_admin": False},
]

# DDL sans FK vers APP_Users pour eviter les cycles de cascade SQL Server
_DDL_TABLES = [
    # APP_Roles
    """IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME='APP_Roles')
    CREATE TABLE APP_Roles (
        id            INT IDENTITY(1,1) PRIMARY KEY,
        nom           NVARCHAR(100) NOT NULL,
        description   NVARCHAR(500) NULL,
        couleur       VARCHAR(20) DEFAULT '#6366f1',
        is_admin      BIT DEFAULT 0,
        actif         BIT DEFAULT 1,
        date_creation DATETIME DEFAULT GETDATE()
    )""",
    # APP_Role_DWH
    """IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME='APP_Role_DWH')
    CREATE TABLE APP_Role_DWH (
        id       INT IDENTITY(1,1) PRIMARY KEY,
        role_id  INT NOT NULL,
        dwh_code VARCHAR(50) NOT NULL,
        CONSTRAINT UQ_Role_DWH UNIQUE (role_id, dwh_code)
    )""",
    # APP_Role_Reports
    """IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME='APP_Role_Reports')
    CREATE TABLE APP_Role_Reports (
        id           INT IDENTITY(1,1) PRIMARY KEY,
        role_id      INT NOT NULL,
        report_type  VARCHAR(20) NOT NULL,
        report_id    INT NOT NULL,
        can_view     BIT DEFAULT 1,
        can_export   BIT DEFAULT 0,
        can_schedule BIT DEFAULT 0,
        CONSTRAINT UQ_Role_Report UNIQUE (role_id, report_type, report_id)
    )""",
    # APP_Role_Columns
    """IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME='APP_Role_Columns')
    CREATE TABLE APP_Role_Columns (
        id          INT IDENTITY(1,1) PRIMARY KEY,
        role_id     INT NOT NULL,
        report_type VARCHAR(20) NOT NULL,
        report_id   INT NOT NULL,
        column_name VARCHAR(200) NOT NULL,
        is_hidden   BIT DEFAULT 1,
        CONSTRAINT UQ_Role_Column UNIQUE (role_id, report_type, report_id, column_name)
    )""",
    # APP_User_Roles — sans FK vers APP_Users pour eviter les cycles de cascade
    """IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME='APP_User_Roles')
    CREATE TABLE APP_User_Roles (
        id               INT IDENTITY(1,1) PRIMARY KEY,
        user_id          INT NOT NULL,
        role_id          INT NOT NULL,
        date_attribution DATETIME DEFAULT GETDATE(),
        CONSTRAINT UQ_User_Role UNIQUE (user_id, role_id)
    )""",
    # APP_Role_Features — fonctionnalites OptiBoard autorisees par role
    """IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME='APP_Role_Features')
    CREATE TABLE APP_Role_Features (
        id           INT IDENTITY(1,1) PRIMARY KEY,
        role_id      INT NOT NULL,
        feature_code VARCHAR(100) NOT NULL,
        CONSTRAINT UQ_Role_Feature UNIQUE (role_id, feature_code)
    )""",
]


def init_roles_tables(dwh_code: str) -> None:
    """Cree les 5 tables de gestion des roles + roles standard si absents."""
    if dwh_code in _init_done:
        return

    failed: list = []
    for ddl in _DDL_TABLES:
        try:
            with client_cursor(dwh_code) as cursor:
                cursor.execute(ddl)
        except Exception as exc:
            failed.append(str(exc))
            logger.warning("init_roles_tables DDL skipped dwh=%s : %s", dwh_code, exc)

    # Marquer done seulement si au moins les tables principales ont ete creees
    tables_ok = len(failed) < len(_DDL_TABLES)
    if not tables_ok:
        raise Exception("; ".join(failed))

    # Creer les roles standard si APP_Roles est vide
    try:
        existing = execute_client(
            "SELECT COUNT(*) AS n FROM APP_Roles",
            dwh_code=dwh_code,
            use_cache=False,
        )
        if (existing[0]["n"] if existing else 0) == 0:
            for r in _STANDARD_ROLES:
                try:
                    write_client(
                        "INSERT INTO APP_Roles (nom, description, couleur, is_admin, actif, date_creation) VALUES (?,?,?,?,1,GETDATE())",
                        (r["nom"], r["description"], r["couleur"], 1 if r["is_admin"] else 0),
                        dwh_code=dwh_code,
                    )
                except Exception as exc:
                    logger.warning("Erreur creation role standard '%s': %s", r["nom"], exc)
            logger.info("Roles standard crees pour dwh=%s", dwh_code)
    except Exception as exc:
        logger.warning("Impossible de verifier/creer les roles standard: %s", exc)

    _init_done.add(dwh_code)
    logger.info("Tables roles initialisees pour dwh_code=%s", dwh_code)


def _ensure_init(dwh_code: str) -> bool:
    """Appele en debut de chaque endpoint pour garantir l'existence des tables."""
    if not dwh_code or dwh_code == "default":
        raise HTTPException(status_code=400, detail="Aucun DWH sélectionné (header X-DWH-Code manquant)")
    # DWH sans base client (ex: DEMO_*) → pas de tables de roles, ignorer silencieusement
    if not client_manager.has_client_db(dwh_code):
        return False
    try:
        init_roles_tables(dwh_code)
    except ClientDBNotFoundError:
        raise HTTPException(status_code=404, detail=f"Base client introuvable pour DWH '{dwh_code}'")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erreur initialisation tables roles : {exc}")
    return True


# ============================================================
# Helper permissions effectives (usage interne / middleware)
# ============================================================

def get_user_effective_permissions(user_id: int, dwh_code: str) -> dict:
    """
    Retourne les permissions fusionnees de tous les roles de l'utilisateur.

    Si un role est admin -> acces total (is_admin=True, listes vides = tout autorise).

    Retourne:
    {
        "is_admin": bool,
        "allowed_dwh": ["DWH1", "DWH2"],
        "allowed_reports": {
            "dashboard": {1: {"can_view": True, "can_export": False, "can_schedule": False}},
            "gridview":  {...},
            "pivot":     {...}
        },
        "hidden_columns": {
            "dashboard": {1: ["COL_PRIX", "COL_MARGE"]},
            "gridview":  {...}
        }
    }
    """
    try:
        if not _ensure_init(dwh_code): return {"success": True, "data": []}
    except HTTPException:
        pass  # Si les tables n'existent pas encore, renvoyer un profil vide

    result: dict = {
        "is_admin": False,
        "allowed_dwh": [],
        "allowed_reports": {"dashboard": {}, "gridview": {}, "pivot": {}},
        "hidden_columns": {"dashboard": {}, "gridview": {}, "pivot": {}},
    }

    try:
        # Recuperer tous les roles actifs de l'user
        roles = execute_client(
            """
            SELECT r.id, r.is_admin
            FROM APP_User_Roles ur
            JOIN APP_Roles r ON r.id = ur.role_id
            WHERE ur.user_id = ? AND r.actif = 1
            """,
            (user_id,),
            dwh_code=dwh_code,
            use_cache=False,
        )
    except Exception:
        return result

    if not roles:
        return result

    role_ids = [r["id"] for r in roles]
    is_admin = any(bool(r["is_admin"]) for r in roles)
    result["is_admin"] = is_admin

    if is_admin:
        # Admin -> tout autorise, listes vides signifient "acces total"
        return result

    # --- DWH autorises ---
    placeholders = ",".join("?" * len(role_ids))
    try:
        dwh_rows = execute_client(
            f"SELECT DISTINCT dwh_code FROM APP_Role_DWH WHERE role_id IN ({placeholders})",
            tuple(role_ids),
            dwh_code=dwh_code,
            use_cache=False,
        )
        result["allowed_dwh"] = [r["dwh_code"] for r in (dwh_rows or [])]
    except Exception:
        pass

    # --- Rapports autorises (fusion OR sur les permissions) ---
    try:
        report_rows = execute_client(
            f"""
            SELECT report_type, report_id,
                   MAX(CAST(can_view AS INT))     AS can_view,
                   MAX(CAST(can_export AS INT))   AS can_export,
                   MAX(CAST(can_schedule AS INT)) AS can_schedule
            FROM APP_Role_Reports
            WHERE role_id IN ({placeholders})
            GROUP BY report_type, report_id
            """,
            tuple(role_ids),
            dwh_code=dwh_code,
            use_cache=False,
        )
        for row in (report_rows or []):
            rtype = row["report_type"]
            rid = row["report_id"]
            if rtype not in result["allowed_reports"]:
                result["allowed_reports"][rtype] = {}
            result["allowed_reports"][rtype][rid] = {
                "can_view": bool(row["can_view"]),
                "can_export": bool(row["can_export"]),
                "can_schedule": bool(row["can_schedule"]),
            }
    except Exception:
        pass

    # --- Colonnes masquees (intersection : masquee seulement si masquee dans TOUS les roles) ---
    try:
        col_rows = execute_client(
            f"""
            SELECT report_type, report_id, column_name,
                   MIN(CAST(is_hidden AS INT)) AS is_hidden
            FROM APP_Role_Columns
            WHERE role_id IN ({placeholders})
            GROUP BY report_type, report_id, column_name
            """,
            tuple(role_ids),
            dwh_code=dwh_code,
            use_cache=False,
        )
        for row in (col_rows or []):
            if not bool(row["is_hidden"]):
                continue
            rtype = row["report_type"]
            rid = row["report_id"]
            if rtype not in result["hidden_columns"]:
                result["hidden_columns"][rtype] = {}
            if rid not in result["hidden_columns"][rtype]:
                result["hidden_columns"][rtype][rid] = []
            result["hidden_columns"][rtype][rid].append(row["column_name"])
    except Exception:
        pass

    return result


# ============================================================
# Routes — Roles CRUD
# ============================================================

@router.post("/roles/init")
async def route_init_tables(x_dwh_code: Optional[str] = Header(None, alias="X-DWH-Code")):
    """Initialise les tables de gestion des roles dans la base client."""
    dwh_code = x_dwh_code or "default"
    _init_done.discard(dwh_code)   # Force la recreation
    try:
        init_roles_tables(dwh_code)
        return {"success": True, "message": "Tables roles initialisees avec succes"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/roles")
async def list_roles(x_dwh_code: Optional[str] = Header(None, alias="X-DWH-Code")):
    """Liste tous les roles avec le nombre d'utilisateurs affectes."""
    dwh_code = x_dwh_code or "default"
    if not _ensure_init(dwh_code): return {"success": True, "data": []}
    try:
        rows = execute_client(
            """
            SELECT r.id, r.nom, r.description, r.couleur, r.is_admin, r.actif,
                   r.date_creation,
                   COUNT(ur.user_id) AS nb_users
            FROM APP_Roles r
            LEFT JOIN APP_User_Roles ur ON ur.role_id = r.id
            WHERE r.actif = 1
            GROUP BY r.id, r.nom, r.description, r.couleur, r.is_admin, r.actif, r.date_creation
            ORDER BY r.nom
            """,
            dwh_code=dwh_code,
            use_cache=False,
        )
        return {"success": True, "data": rows or []}
    except Exception as exc:
        # Fallback si APP_User_Roles n'existe pas encore (init partielle)
        if "invalid object name" in str(exc).lower() or "APP_User_Roles" in str(exc):
            try:
                rows = execute_client(
                    """SELECT id, nom, description, couleur, is_admin, actif,
                              date_creation, 0 AS nb_users
                       FROM APP_Roles WHERE actif = 1 ORDER BY nom""",
                    dwh_code=dwh_code,
                    use_cache=False,
                )
                return {"success": True, "data": rows or []}
            except Exception as exc2:
                raise HTTPException(status_code=500, detail=str(exc2))
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/roles/seed-standard")
async def seed_standard_roles(x_dwh_code: Optional[str] = Header(None, alias="X-DWH-Code")):
    """Insère les rôles standard manquants (ignore ceux qui existent déjà par nom)."""
    dwh_code = x_dwh_code or "default"
    if not _ensure_init(dwh_code): return {"success": True, "data": []}
    try:
        existing = execute_client(
            "SELECT nom FROM APP_Roles",
            dwh_code=dwh_code,
            use_cache=False,
        )
        existing_names = {r["nom"].lower() for r in (existing or [])}
        created = []
        skipped = []
        to_create = [r for r in _STANDARD_ROLES if r["nom"].lower() not in existing_names]
        for r in _STANDARD_ROLES:
            if r["nom"].lower() in existing_names:
                skipped.append(r["nom"])
        try:
            with client_cursor(dwh_code) as cur:
                for r in to_create:
                    cur.execute(
                        "INSERT INTO APP_Roles (nom, description, couleur, is_admin, actif, date_creation) VALUES (?,?,?,?,1,GETDATE())",
                        (r["nom"], r["description"], r["couleur"], 1 if r["is_admin"] else 0),
                    )
                    created.append(r["nom"])
        except Exception as exc:
            logger.warning("Erreur création rôles standard: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc))
        return {
            "success": True,
            "created": created,
            "skipped": skipped,
            "message": f"{len(created)} rôle(s) créé(s), {len(skipped)} déjà existant(s)",
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/roles")
async def create_role(body: RoleCreate, x_dwh_code: Optional[str] = Header(None)):
    """Cree un nouveau role."""
    dwh_code = x_dwh_code or "default"
    if not _ensure_init(dwh_code): return {"success": True, "data": []}
    try:
        write_client(
            """
            INSERT INTO APP_Roles (nom, description, couleur, is_admin, actif, date_creation)
            VALUES (?, ?, ?, ?, 1, GETDATE())
            """,
            (body.nom, body.description, body.couleur or "#6366f1", 1 if body.is_admin else 0),
            dwh_code=dwh_code,
        )
        rows = execute_client(
            "SELECT TOP 1 id FROM APP_Roles WHERE nom = ? ORDER BY id DESC",
            (body.nom,),
            dwh_code=dwh_code,
            use_cache=False,
        )
        new_id = rows[0]["id"] if rows else None
        return {"success": True, "message": f"Role '{body.nom}' cree", "id": new_id}
    except Exception as exc:
        if "unique" in str(exc).lower() or "duplicate" in str(exc).lower():
            raise HTTPException(status_code=409, detail=f"Un role nomme '{body.nom}' existe deja")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/roles/{role_id}")
async def get_role(role_id: int, x_dwh_code: Optional[str] = Header(None)):
    """Retourne le detail d'un role."""
    dwh_code = x_dwh_code or "default"
    if not _ensure_init(dwh_code): return {"success": True, "data": []}
    try:
        rows = execute_client(
            "SELECT id, nom, description, couleur, is_admin, actif, date_creation FROM APP_Roles WHERE id = ?",
            (role_id,),
            dwh_code=dwh_code,
            use_cache=False,
        )
        if not rows:
            raise HTTPException(status_code=404, detail=f"Role {role_id} introuvable")
        return {"success": True, "data": rows[0]}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.put("/roles/{role_id}")
async def update_role(role_id: int, body: RoleUpdate, x_dwh_code: Optional[str] = Header(None)):
    """Modifie un role existant."""
    dwh_code = x_dwh_code or "default"
    if not _ensure_init(dwh_code): return {"success": True, "data": []}
    try:
        fields, params = [], []
        if body.nom is not None:
            fields.append("nom = ?"); params.append(body.nom)
        if body.description is not None:
            fields.append("description = ?"); params.append(body.description)
        if body.couleur is not None:
            fields.append("couleur = ?"); params.append(body.couleur)
        if body.is_admin is not None:
            fields.append("is_admin = ?"); params.append(1 if body.is_admin else 0)
        if body.actif is not None:
            fields.append("actif = ?"); params.append(1 if body.actif else 0)
        if not fields:
            raise HTTPException(status_code=400, detail="Aucun champ a mettre a jour")
        params.append(role_id)
        write_client(
            f"UPDATE APP_Roles SET {', '.join(fields)} WHERE id = ?",
            tuple(params),
            dwh_code=dwh_code,
        )
        return {"success": True, "message": "Role mis a jour"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/roles/{role_id}")
async def delete_role(role_id: int, x_dwh_code: Optional[str] = Header(None)):
    """Desactive un role (actif=0)."""
    dwh_code = x_dwh_code or "default"
    if not _ensure_init(dwh_code): return {"success": True, "data": []}
    try:
        write_client(
            "UPDATE APP_Roles SET actif = 0 WHERE id = ?",
            (role_id,),
            dwh_code=dwh_code,
        )
        return {"success": True, "message": f"Role {role_id} desactive"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================
# Routes — Permissions DWH
# ============================================================

@router.get("/roles/{role_id}/dwh")
async def get_role_dwh(role_id: int, x_dwh_code: Optional[str] = Header(None)):
    """Liste les DWH autorises pour ce role."""
    dwh_code = x_dwh_code or "default"
    if not _ensure_init(dwh_code): return {"success": True, "data": []}
    try:
        rows = execute_client(
            "SELECT id, dwh_code FROM APP_Role_DWH WHERE role_id = ? ORDER BY dwh_code",
            (role_id,),
            dwh_code=dwh_code,
            use_cache=False,
        )
        return {"success": True, "data": rows or []}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/roles/{role_id}/dwh")
async def set_role_dwh(role_id: int, body: DWHSet, x_dwh_code: Optional[str] = Header(None)):
    """
    Remplace completement la liste des DWH autorises pour ce role.
    body: { dwh_codes: ["DWH1", "DWH2"] }
    """
    dwh_code = x_dwh_code or "default"
    if not _ensure_init(dwh_code): return {"success": True, "data": []}
    try:
        with client_cursor(dwh_code) as cursor:
            cursor.execute("DELETE FROM APP_Role_DWH WHERE role_id = ?", (role_id,))
            for code in body.dwh_codes:
                cursor.execute(
                    "INSERT INTO APP_Role_DWH (role_id, dwh_code) VALUES (?, ?)",
                    (role_id, code),
                )
        return {"success": True, "message": f"{len(body.dwh_codes)} DWH definis pour le role {role_id}"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================
# Routes — Permissions Rapports
# ============================================================

@router.get("/roles/{role_id}/reports")
async def get_role_reports(role_id: int, x_dwh_code: Optional[str] = Header(None)):
    """Liste les rapports autorises pour ce role."""
    dwh_code = x_dwh_code or "default"
    if not _ensure_init(dwh_code): return {"success": True, "data": []}
    try:
        rows = execute_client(
            """
            SELECT id, report_type, report_id, can_view, can_export, can_schedule
            FROM APP_Role_Reports
            WHERE role_id = ?
            ORDER BY report_type, report_id
            """,
            (role_id,),
            dwh_code=dwh_code,
            use_cache=False,
        )
        return {"success": True, "data": rows or []}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/roles/{role_id}/reports")
async def upsert_role_report(
    role_id: int,
    body: ReportPermission,
    x_dwh_code: Optional[str] = Header(None),
):
    """Ajoute ou modifie la permission d'acces a un rapport pour ce role."""
    dwh_code = x_dwh_code or "default"
    if not _ensure_init(dwh_code): return {"success": True, "data": []}
    try:
        with client_cursor(dwh_code) as cursor:
            cursor.execute(
                "SELECT id FROM APP_Role_Reports WHERE role_id = ? AND report_type = ? AND report_id = ?",
                (role_id, body.report_type, body.report_id),
            )
            existing = cursor.fetchone()
            if existing:
                cursor.execute(
                    """
                    UPDATE APP_Role_Reports
                    SET can_view = ?, can_export = ?, can_schedule = ?
                    WHERE role_id = ? AND report_type = ? AND report_id = ?
                    """,
                    (
                        1 if body.can_view else 0,
                        1 if body.can_export else 0,
                        1 if body.can_schedule else 0,
                        role_id, body.report_type, body.report_id,
                    ),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO APP_Role_Reports
                        (role_id, report_type, report_id, can_view, can_export, can_schedule)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        role_id, body.report_type, body.report_id,
                        1 if body.can_view else 0,
                        1 if body.can_export else 0,
                        1 if body.can_schedule else 0,
                    ),
                )
        return {"success": True, "message": "Permission rapport mise a jour"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/roles/{role_id}/reports/{report_type}/{report_id}")
async def delete_role_report(
    role_id: int,
    report_type: str,
    report_id: int,
    x_dwh_code: Optional[str] = Header(None),
):
    """Retire l'acces a un rapport pour ce role."""
    dwh_code = x_dwh_code or "default"
    if not _ensure_init(dwh_code): return {"success": True, "data": []}
    try:
        write_client(
            "DELETE FROM APP_Role_Reports WHERE role_id = ? AND report_type = ? AND report_id = ?",
            (role_id, report_type, report_id),
            dwh_code=dwh_code,
        )
        return {"success": True, "message": "Rapport retire du role"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================
# Routes — Colonnes masquees
# ============================================================

@router.get("/roles/{role_id}/columns")
async def get_role_columns(role_id: int, x_dwh_code: Optional[str] = Header(None)):
    """Liste les masques de colonnes definis pour ce role."""
    dwh_code = x_dwh_code or "default"
    if not _ensure_init(dwh_code): return {"success": True, "data": []}
    try:
        rows = execute_client(
            """
            SELECT id, report_type, report_id, column_name, is_hidden
            FROM APP_Role_Columns
            WHERE role_id = ?
            ORDER BY report_type, report_id, column_name
            """,
            (role_id,),
            dwh_code=dwh_code,
            use_cache=False,
        )
        return {"success": True, "data": rows or []}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/roles/{role_id}/columns")
async def set_role_columns(
    role_id: int,
    body: ColumnsSet,
    x_dwh_code: Optional[str] = Header(None),
):
    """
    Remplace completement les colonnes masquees pour un rapport donne.
    body: { report_type, report_id, hidden_columns: ["COL1", "COL2"] }
    """
    dwh_code = x_dwh_code or "default"
    if not _ensure_init(dwh_code): return {"success": True, "data": []}
    try:
        with client_cursor(dwh_code) as cursor:
            cursor.execute(
                "DELETE FROM APP_Role_Columns WHERE role_id = ? AND report_type = ? AND report_id = ?",
                (role_id, body.report_type, body.report_id),
            )
            for col in body.hidden_columns:
                cursor.execute(
                    """
                    INSERT INTO APP_Role_Columns
                        (role_id, report_type, report_id, column_name, is_hidden)
                    VALUES (?, ?, ?, ?, 1)
                    """,
                    (role_id, body.report_type, body.report_id, col),
                )
        return {
            "success": True,
            "message": f"{len(body.hidden_columns)} colonne(s) masquee(s) definies pour le rapport {body.report_type}/{body.report_id}",
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================
# Routes — Affectation Utilisateurs <-> Roles
# ============================================================

@router.get("/roles/{role_id}/users")
async def get_role_users(role_id: int, x_dwh_code: Optional[str] = Header(None)):
    """Liste les utilisateurs ayant ce role."""
    dwh_code = x_dwh_code or "default"
    if not _ensure_init(dwh_code): return {"success": True, "data": []}
    try:
        rows = execute_client(
            """
            SELECT u.id, u.username, u.nom, u.prenom, u.email, ur.date_attribution
            FROM APP_User_Roles ur
            JOIN APP_Users u ON u.id = ur.user_id
            WHERE ur.role_id = ?
            ORDER BY u.nom
            """,
            (role_id,),
            dwh_code=dwh_code,
            use_cache=False,
        )
        return {"success": True, "data": rows or []}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/users/{user_id}/roles")
async def get_user_roles(user_id: int, x_dwh_code: Optional[str] = Header(None)):
    """Liste tous les roles d'un utilisateur."""
    dwh_code = x_dwh_code or "default"
    if not _ensure_init(dwh_code): return {"success": True, "data": []}
    try:
        rows = execute_client(
            """
            SELECT r.id, r.nom, r.description, r.couleur, r.is_admin, ur.date_attribution
            FROM APP_User_Roles ur
            JOIN APP_Roles r ON r.id = ur.role_id
            WHERE ur.user_id = ? AND r.actif = 1
            ORDER BY r.nom
            """,
            (user_id,),
            dwh_code=dwh_code,
            use_cache=False,
        )
        return {"success": True, "data": rows or []}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/users/{user_id}/roles")
async def assign_role_to_user(
    user_id: int,
    body: UserRoleAssign,
    x_dwh_code: Optional[str] = Header(None),
):
    """Assigne un role a un utilisateur."""
    dwh_code = x_dwh_code or "default"
    if not _ensure_init(dwh_code): return {"success": True, "data": []}
    try:
        write_client(
            """
            INSERT INTO APP_User_Roles (user_id, role_id, date_attribution)
            VALUES (?, ?, GETDATE())
            """,
            (user_id, body.role_id),
            dwh_code=dwh_code,
        )
        return {"success": True, "message": f"Role {body.role_id} attribue a l'utilisateur {user_id}"}
    except Exception as exc:
        if "unique" in str(exc).lower() or "duplicate" in str(exc).lower() or "violation" in str(exc).lower():
            raise HTTPException(status_code=409, detail="Ce role est deja attribue a cet utilisateur")
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/users/{user_id}/roles/{role_id}")
async def remove_role_from_user(
    user_id: int,
    role_id: int,
    x_dwh_code: Optional[str] = Header(None),
):
    """Retire un role d'un utilisateur."""
    dwh_code = x_dwh_code or "default"
    if not _ensure_init(dwh_code): return {"success": True, "data": []}
    try:
        write_client(
            "DELETE FROM APP_User_Roles WHERE user_id = ? AND role_id = ?",
            (user_id, role_id),
            dwh_code=dwh_code,
        )
        return {"success": True, "message": f"Role {role_id} retire de l'utilisateur {user_id}"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================
# Routes — Permissions effectives
# ============================================================

@router.get("/users/{user_id}/effective-permissions")
async def get_effective_permissions(user_id: int, x_dwh_code: Optional[str] = Header(None)):
    """
    Retourne les permissions effectives fusionnees de tous les roles de l'utilisateur.
    Si un role est admin, is_admin=True et les listes sont vides (acces total).
    """
    dwh_code = x_dwh_code or "default"
    try:
        perms = get_user_effective_permissions(user_id, dwh_code)
        return {"success": True, "data": perms}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================
# Routes — Fonctionnalités OptiBoard par rôle
# ============================================================

@router.get("/roles/{role_id}/features")
async def get_role_features(role_id: int, x_dwh_code: Optional[str] = Header(None)):
    """Retourne les codes de fonctionnalites autorisees pour ce role."""
    dwh_code = x_dwh_code or "default"
    if not _ensure_init(dwh_code): return {"success": True, "data": []}
    try:
        rows = execute_client(
            "SELECT feature_code FROM APP_Role_Features WHERE role_id = ? ORDER BY feature_code",
            (role_id,), dwh_code=dwh_code, use_cache=False,
        )
        return {"success": True, "data": [r["feature_code"] for r in (rows or [])]}
    except Exception as exc:
        if "invalid object name" in str(exc).lower():
            return {"success": True, "data": []}
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/roles/{role_id}/features")
async def set_role_features(
    role_id: int,
    body: FeatureSet,
    x_dwh_code: Optional[str] = Header(None),
):
    """Remplace completement la liste des fonctionnalites autorisees pour ce role."""
    dwh_code = x_dwh_code or "default"
    if not _ensure_init(dwh_code): return {"success": True, "data": []}
    try:
        with client_cursor(dwh_code) as cursor:
            cursor.execute("DELETE FROM APP_Role_Features WHERE role_id = ?", (role_id,))
            for code in body.feature_codes:
                cursor.execute(
                    "INSERT INTO APP_Role_Features (role_id, feature_code) VALUES (?, ?)",
                    (role_id, code),
                )
        return {"success": True, "message": f"{len(body.feature_codes)} fonctionnalite(s) enregistree(s)"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
