"""Routes pour la configuration des liens drill-through inter-rapports"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List
import json

from ..database_unified import execute_central, central_cursor, execute_client

router = APIRouter(prefix="/api/drillthrough", tags=["drillthrough"])

# Types de rapports supportés comme source et cible
REPORT_TYPES = ["gridview", "dashboard", "pivot"]


# ==================== SCHEMAS ====================

class DrillThroughRule(BaseModel):
    nom: str
    # Source
    source_type: str   # gridview | dashboard | pivot
    source_id: int
    source_column: str  # nom de la colonne / champ source (pour gridview)
    # Cible
    target_type: str   # gridview | dashboard | pivot
    target_id: int
    target_filter_field: str  # champ sur lequel filtrer dans la cible
    # UI
    label: Optional[str] = None   # libellé affiché dans le menu contextuel
    is_active: bool = True


class DrillThroughRuleUpdate(BaseModel):
    nom: Optional[str] = None
    source_column: Optional[str] = None
    target_type: Optional[str] = None
    target_id: Optional[int] = None
    target_filter_field: Optional[str] = None
    label: Optional[str] = None
    is_active: Optional[bool] = None


# ==================== INIT TABLE ====================

def init_drillthrough_tables():
    """Crée la table de configuration drill-through si elle n'existe pas."""
    sql = """
    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'APP_DrillThrough')
    CREATE TABLE APP_DrillThrough (
        id                  INT IDENTITY(1,1) PRIMARY KEY,
        nom                 NVARCHAR(255)   NOT NULL,
        source_type         NVARCHAR(50)    NOT NULL,
        source_id           INT             NOT NULL,
        source_column       NVARCHAR(255)   NOT NULL,
        target_type         NVARCHAR(50)    NOT NULL,
        target_id           INT             NOT NULL,
        target_filter_field NVARCHAR(255)   NOT NULL,
        label               NVARCHAR(255),
        is_active           BIT             NOT NULL DEFAULT 1,
        created_at          DATETIME        DEFAULT GETDATE(),
        updated_at          DATETIME        DEFAULT GETDATE()
    )
    """
    try:
        with central_cursor() as cur:
            cur.execute(sql)
        return True
    except Exception as e:
        print(f"[DRILLTHROUGH] Erreur init table: {e}")
        return False


# ==================== HELPERS ====================

def _get_report_name(report_type: str, report_id: int) -> str:
    """Récupère le nom d'un rapport depuis la base."""
    table_map = {
        "gridview":  "APP_GridViews",
        "dashboard": "APP_Dashboards",
        "pivot":     "APP_Pivots",
    }
    table = table_map.get(report_type)
    if not table:
        return "Inconnu"
    try:
        rows = execute_central(f"SELECT nom FROM {table} WHERE id = ?", (report_id,), use_cache=False)
        return rows[0]["nom"] if rows else "Inconnu"
    except Exception:
        return "Inconnu"


# ==================== CRUD ====================

@router.get("/rules")
async def get_rules(source_type: Optional[str] = None, source_id: Optional[int] = None):
    """Retourne les règles drill-through, filtrables par source."""
    try:
        init_drillthrough_tables()

        query = "SELECT * FROM APP_DrillThrough WHERE 1=1"
        params = []
        if source_type:
            query += " AND source_type = ?"
            params.append(source_type)
        if source_id:
            query += " AND source_id = ?"
            params.append(source_id)
        query += " ORDER BY source_type, source_id, source_column"

        rows = execute_central(query, tuple(params) if params else None, use_cache=False)

        # Enrichir avec les noms des rapports
        for r in rows:
            r["source_name"] = _get_report_name(r["source_type"], r["source_id"])
            r["target_name"] = _get_report_name(r["target_type"], r["target_id"])
            r["target_url"] = _build_target_url(r["target_type"], r["target_id"])

        return {"success": True, "data": rows}
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}


@router.get("/rules/by-source")
async def get_rules_by_source(source_type: str, source_id: int):
    """Retourne les règles actives pour une source donnée, groupées par colonne."""
    try:
        init_drillthrough_tables()
        rows = execute_central("""
            SELECT * FROM APP_DrillThrough
            WHERE source_type = ? AND source_id = ? AND is_active = 1
            ORDER BY source_column
        """, (source_type, source_id), use_cache=False)

        for r in rows:
            r["target_name"] = _get_report_name(r["target_type"], r["target_id"])
            r["target_url"] = _build_target_url(r["target_type"], r["target_id"])

        # Grouper par colonne source
        by_column: dict = {}
        for r in rows:
            col = r["source_column"]
            if col not in by_column:
                by_column[col] = []
            by_column[col].append(r)

        return {"success": True, "data": rows, "by_column": by_column}
    except Exception as e:
        return {"success": False, "error": str(e), "data": [], "by_column": {}}


@router.post("/rules")
async def create_rule(rule: DrillThroughRule):
    """Crée une nouvelle règle drill-through."""
    try:
        init_drillthrough_tables()
        with central_cursor() as cur:
            cur.execute("""
                INSERT INTO APP_DrillThrough
                    (nom, source_type, source_id, source_column,
                     target_type, target_id, target_filter_field, label, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rule.nom, rule.source_type, rule.source_id, rule.source_column,
                rule.target_type, rule.target_id, rule.target_filter_field,
                rule.label or rule.nom, rule.is_active
            ))
            cur.execute("SELECT @@IDENTITY AS id")
            new_id = cur.fetchone()[0]
        return {"success": True, "id": new_id, "message": "Règle drill-through créée"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.put("/rules/{rule_id}")
async def update_rule(rule_id: int, rule: DrillThroughRuleUpdate):
    """Met à jour une règle."""
    try:
        updates, params = [], []
        field_map = {
            "nom": rule.nom, "source_column": rule.source_column,
            "target_type": rule.target_type, "target_id": rule.target_id,
            "target_filter_field": rule.target_filter_field,
            "label": rule.label, "is_active": rule.is_active,
        }
        for col, val in field_map.items():
            if val is not None:
                updates.append(f"{col} = ?")
                params.append(val)

        if not updates:
            return {"success": False, "error": "Aucune modification"}

        updates.append("updated_at = GETDATE()")
        params.append(rule_id)

        with central_cursor() as cur:
            cur.execute(f"UPDATE APP_DrillThrough SET {', '.join(updates)} WHERE id = ?", params)

        return {"success": True, "message": "Règle mise à jour"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: int):
    """Supprime une règle."""
    try:
        with central_cursor() as cur:
            cur.execute("DELETE FROM APP_DrillThrough WHERE id = ?", (rule_id,))
        return {"success": True, "message": "Règle supprimée"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/rules/{rule_id}/toggle")
async def toggle_rule(rule_id: int):
    """Active/désactive une règle."""
    try:
        with central_cursor() as cur:
            cur.execute("""
                UPDATE APP_DrillThrough
                SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END,
                    updated_at = GETDATE()
                WHERE id = ?
            """, (rule_id,))
        rows = execute_central("SELECT is_active FROM APP_DrillThrough WHERE id = ?", (rule_id,), use_cache=False)
        return {"success": True, "is_active": rows[0]["is_active"] if rows else None}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== RAPPORTS DISPONIBLES ====================

@router.get("/available-reports")
async def get_available_reports():
    """Liste tous les rapports disponibles comme source ou cible."""
    try:
        gridviews = execute_central("SELECT id, nom FROM APP_GridViews ORDER BY nom", use_cache=False)
        dashboards = execute_central("SELECT id, nom FROM APP_Dashboards ORDER BY nom", use_cache=False)
        pivots = execute_central("SELECT id, nom FROM APP_Pivots ORDER BY nom", use_cache=False)

        return {
            "success": True,
            "data": {
                "gridview":  [{"id": r["id"], "nom": r["nom"]} for r in gridviews],
                "dashboard": [{"id": r["id"], "nom": r["nom"]} for r in dashboards],
                "pivot":     [{"id": r["id"], "nom": r["nom"]} for r in pivots],
            }
        }
    except Exception as e:
        import traceback
        print(f"[DRILLTHROUGH] available-reports error: {traceback.format_exc()}")
        return {"success": False, "error": str(e), "data": {}}


@router.get("/columns/{report_id}")
async def get_gridview_columns(report_id: int):
    """Retourne les colonnes d'un GridView (pour la sélection de la colonne source)."""
    try:
        rows = execute_central("SELECT columns_config FROM APP_GridViews WHERE id = ?", (report_id,), use_cache=False)
        if not rows or not rows[0].get("columns_config"):
            return {"success": True, "data": []}
        cols = json.loads(rows[0]["columns_config"])
        result = [{"field": c.get("field", ""), "header": c.get("header", c.get("field", ""))} for c in cols]
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}


# ==================== HELPER URL ====================

def _build_target_url(target_type: str, target_id: int) -> str:
    route_map = {"gridview": "grid", "dashboard": "view", "pivot": "pivot-v2"}
    route = route_map.get(target_type, "grid")
    return f"/{route}/{target_id}"
