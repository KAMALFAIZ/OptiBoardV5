"""
Module Master Export
====================
Expose le catalogue maître (menus, dashboards, gridviews, pivots, datasources)
pour qu'un client distant puisse le tirer via HTTP.

Routes :
    GET  /api/master/info          → ping + version + nb d'entités exposées
    GET  /api/master/menus         → catalogue des menus
    GET  /api/master/dashboards    → catalogue des dashboards
    GET  /api/master/gridviews     → catalogue des gridviews
    GET  /api/master/pivots        → catalogue des pivots V2
    GET  /api/master/datasources   → catalogue des sources de données
    GET  /api/master/all           → tout en un seul appel

Auth :
    Header obligatoire : X-Master-Api-Key
    La clé est lue depuis .env (MASTER_API_KEY).
    Si MASTER_API_KEY est vide, toutes les routes renvoient 503 (module désactivé).

Source des données :
    Lecture directe sur la base centrale OptiBoard_SaaS (tables APP_*).
    Cette base joue le rôle de "catalogue maître" sur le serveur central.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Header, HTTPException

from ..config import get_settings
from ..database_unified import execute_central

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/master", tags=["Master Catalog"])


# ============================================================
# Helpers
# ============================================================

def _check_api_key(api_key: Optional[str]) -> None:
    """
    Vérifie la clé API. Lève 503 si module désactivé, 401/403 si clé invalide.
    """
    settings = get_settings()
    expected = (getattr(settings, "MASTER_API_KEY", "") or "").strip()

    if not expected:
        # Module désactivé sur ce serveur (cas client : ne doit pas servir de master)
        raise HTTPException(
            status_code=503,
            detail="Master catalog désactivé sur ce serveur (MASTER_API_KEY non configuré)"
        )
    if not api_key:
        raise HTTPException(status_code=401, detail="Header X-Master-Api-Key requis")
    if api_key.strip() != expected:
        raise HTTPException(status_code=403, detail="Clé API maître invalide")


def _safe_select(sql: str, label: str) -> list:
    """SELECT sur la base centrale, retourne [] si table absente."""
    try:
        rows = execute_central(sql, use_cache=False)
        return rows or []
    except Exception as e:
        logger.warning(f"master_export {label}: {e}")
        return []


# ============================================================
# GET /api/master/info
# ============================================================

@router.get("/info")
async def master_info(
    x_master_api_key: Optional[str] = Header(None, alias="X-Master-Api-Key"),
):
    """Ping + comptage des entités exposées par le catalogue maître."""
    _check_api_key(x_master_api_key)

    counts = {
        "menus":       len(_safe_select("SELECT 1 FROM APP_Menus WHERE actif=1",       "menus_count")),
        "dashboards":  len(_safe_select("SELECT 1 FROM APP_Dashboards WHERE actif=1",  "dashboards_count")),
        "gridviews":   len(_safe_select("SELECT 1 FROM APP_GridViews WHERE actif=1",   "gridviews_count")),
        "pivots":      len(_safe_select("SELECT 1 FROM APP_Pivots_V2 WHERE actif=1",   "pivots_count")),
        "datasources": len(_safe_select("SELECT 1 FROM APP_DataSources",               "datasources_count")),
    }
    return {
        "success": True,
        "version": "1.0",
        "counts":  counts,
        "total":   sum(counts.values()),
    }


# ============================================================
# GET /api/master/menus
# ============================================================

@router.get("/menus")
async def master_menus(
    x_master_api_key: Optional[str] = Header(None, alias="X-Master-Api-Key"),
):
    """Liste complète des menus actifs (template maître)."""
    _check_api_key(x_master_api_key)
    rows = _safe_select(
        "SELECT code, nom, parent_code, ordre, page_code, icone, actif "
        "FROM APP_Menus WHERE actif=1 ORDER BY parent_code, ordre",
        "menus"
    )
    return {"success": True, "count": len(rows), "items": rows}


# ============================================================
# GET /api/master/dashboards
# ============================================================

@router.get("/dashboards")
async def master_dashboards(
    x_master_api_key: Optional[str] = Header(None, alias="X-Master-Api-Key"),
):
    """Liste complète des dashboards actifs (template maître)."""
    _check_api_key(x_master_api_key)
    rows = _safe_select(
        "SELECT code, nom, description, config, widgets, is_public "
        "FROM APP_Dashboards WHERE actif=1 ORDER BY nom",
        "dashboards"
    )
    return {"success": True, "count": len(rows), "items": rows}


# ============================================================
# GET /api/master/gridviews
# ============================================================

@router.get("/gridviews")
async def master_gridviews(
    x_master_api_key: Optional[str] = Header(None, alias="X-Master-Api-Key"),
):
    """Liste complète des gridviews actifs (template maître)."""
    _check_api_key(x_master_api_key)
    rows = _safe_select(
        "SELECT code, nom, description, query_template, columns_config, "
        "       parameters, features "
        "FROM APP_GridViews WHERE actif=1 ORDER BY nom",
        "gridviews"
    )
    return {"success": True, "count": len(rows), "items": rows}


# ============================================================
# GET /api/master/pivots
# ============================================================

@router.get("/pivots")
async def master_pivots(
    x_master_api_key: Optional[str] = Header(None, alias="X-Master-Api-Key"),
):
    """Liste complète des pivots V2 actifs (template maître)."""
    _check_api_key(x_master_api_key)
    rows = _safe_select(
        "SELECT code, nom, description, datasource_code, pivot_config, "
        "       filters_config, display_config "
        "FROM APP_Pivots_V2 WHERE actif=1 ORDER BY nom",
        "pivots"
    )
    return {"success": True, "count": len(rows), "items": rows}


# ============================================================
# GET /api/master/datasources
# ============================================================

@router.get("/datasources")
async def master_datasources(
    x_master_api_key: Optional[str] = Header(None, alias="X-Master-Api-Key"),
):
    """Liste complète des sources de données (template maître)."""
    _check_api_key(x_master_api_key)
    rows = _safe_select(
        "SELECT code, nom, type, query_template, parameters, description "
        "FROM APP_DataSources ORDER BY nom",
        "datasources"
    )
    return {"success": True, "count": len(rows), "items": rows}


# ============================================================
# GET /api/master/all
# Tout en un seul appel pour réduire le nombre de requêtes HTTP
# ============================================================

@router.get("/all")
async def master_all(
    x_master_api_key: Optional[str] = Header(None, alias="X-Master-Api-Key"),
):
    """Renvoie l'intégralité du catalogue maître en un seul payload."""
    _check_api_key(x_master_api_key)

    catalog = {
        "menus":       _safe_select(
            "SELECT code, nom, parent_code, ordre, page_code, icone, actif "
            "FROM APP_Menus WHERE actif=1 ORDER BY parent_code, ordre", "menus"),
        "dashboards":  _safe_select(
            "SELECT code, nom, description, config, widgets, is_public "
            "FROM APP_Dashboards WHERE actif=1 ORDER BY nom", "dashboards"),
        "gridviews":   _safe_select(
            "SELECT code, nom, description, query_template, columns_config, parameters, features "
            "FROM APP_GridViews WHERE actif=1 ORDER BY nom", "gridviews"),
        "pivots":      _safe_select(
            "SELECT code, nom, description, datasource_code, pivot_config, filters_config, display_config "
            "FROM APP_Pivots_V2 WHERE actif=1 ORDER BY nom", "pivots"),
        "datasources": _safe_select(
            "SELECT code, nom, type, query_template, parameters, description "
            "FROM APP_DataSources ORDER BY nom", "datasources"),
    }
    return {
        "success": True,
        "version": "1.0",
        "counts":  {k: len(v) for k, v in catalog.items()},
        "catalog": catalog,
    }
