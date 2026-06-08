"""Module Comptabilité Analytique — Phase 4
Expose les données analytiques (centres de coûts, P&L, budget vs réalisé).
"""
from fastapi import APIRouter, Query
from datetime import date
from app.database_unified import execute_client
from app.sql.query_templates import (
    ANALYTIQUE_PAR_CENTRE,
    ANALYTIQUE_EVOLUTION_MENSUELLE,
    ANALYTIQUE_BUDGET_VS_REALISE,
    ANALYTIQUE_PL_ACTIVITE,
    LISTE_CENTRES_ANALYTIQUES,
)
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analytique", tags=["analytique"])


def _run(sql: str, params: tuple, dwh_code: str) -> list:
    try:
        return execute_client(sql, params=params, dwh_code=dwh_code) or []
    except Exception as e:
        logger.error(f"[analytique] Erreur requête : {e}")
        return []


@router.get("/centres")
async def get_centres(
    dwh_code: str = Query(...),
    date_debut: date = Query(...),
    date_fin: date = Query(...),
):
    """Charges/produits par centre analytique sur la période."""
    data = _run(ANALYTIQUE_PAR_CENTRE, (str(date_debut), str(date_fin)), dwh_code)
    return {"success": True, "data": data, "count": len(data)}


@router.get("/evolution")
async def get_evolution(
    dwh_code: str = Query(...),
    date_debut: date = Query(...),
    date_fin: date = Query(...),
):
    """Évolution mensuelle par centre analytique."""
    data = _run(ANALYTIQUE_EVOLUTION_MENSUELLE, (str(date_debut), str(date_fin)), dwh_code)
    return {"success": True, "data": data, "count": len(data)}


@router.get("/pl-activite")
async def get_pl_activite(
    dwh_code: str = Query(...),
    date_debut: date = Query(...),
    date_fin: date = Query(...),
):
    """Résultat analytique (Produits − Charges) par centre."""
    data = _run(ANALYTIQUE_PL_ACTIVITE, (str(date_debut), str(date_fin)), dwh_code)
    return {"success": True, "data": data, "count": len(data)}


@router.get("/budget-vs-realise")
async def get_budget_vs_realise(
    dwh_code: str = Query(...),
    date_debut: date = Query(...),
    date_fin: date = Query(...),
    exercice: int = Query(...),
):
    """Comparatif budget analytique vs réalisé par centre."""
    data = _run(
        ANALYTIQUE_BUDGET_VS_REALISE,
        (str(date_debut), str(date_fin), exercice),
        dwh_code,
    )
    return {"success": True, "data": data, "count": len(data)}


@router.get("/liste-centres")
async def get_liste_centres(dwh_code: str = Query(...)):
    """Liste des centres analytiques disponibles."""
    data = _run(LISTE_CENTRES_ANALYTIQUES, (), dwh_code)
    return {"success": True, "data": data}
