"""Module Budget vs Réalisé — Phase 5
Saisie, consultation et comparatif budgétaire.
"""
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.database_unified import execute_client, write_client
from app.sql.query_templates import (
    BUDGET_VS_REALISE_CA,
    BUDGET_VS_REALISE_CHARGES,
    BUDGET_GLOBAL_ANNUEL,
    MASSE_SALARIALE_MENSUELLE,
    RATIO_MASSE_SALARIALE_CA,
)
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/budget", tags=["budget"])


class BudgetItem(BaseModel):
    exercice: int
    mois: int
    axe: str           # 'CA', 'CHARGES', 'MARGE', 'PAIE'
    code_poste: Optional[str] = None
    libelle_poste: Optional[str] = None
    montant_budget: float


def _run(sql: str, params: tuple, dwh_code: str) -> list:
    try:
        return execute_client(sql, params=params, dwh_code=dwh_code) or []
    except Exception as e:
        logger.error(f"[budget] Erreur requête : {e}")
        return []


@router.get("/vs-realise/ca")
async def budget_vs_realise_ca(
    dwh_code: str = Query(...),
    exercice: int = Query(...),
):
    data = _run(BUDGET_VS_REALISE_CA, (exercice,), dwh_code)
    return {"success": True, "data": data}


@router.get("/vs-realise/charges")
async def budget_vs_realise_charges(
    dwh_code: str = Query(...),
    exercice: int = Query(...),
):
    data = _run(BUDGET_VS_REALISE_CHARGES, (exercice,), dwh_code)
    return {"success": True, "data": data}


@router.get("/global")
async def budget_global(
    dwh_code: str = Query(...),
    exercice: int = Query(...),
):
    data = _run(BUDGET_GLOBAL_ANNUEL, (exercice,), dwh_code)
    return {"success": True, "data": data}


@router.get("/masse-salariale")
async def masse_salariale(
    dwh_code: str = Query(...),
    date_debut: str = Query(...),
    date_fin: str = Query(...),
):
    data = _run(MASSE_SALARIALE_MENSUELLE, (date_debut, date_fin), dwh_code)
    return {"success": True, "data": data}


@router.get("/ratio-ms-ca")
async def ratio_ms_ca(
    dwh_code: str = Query(...),
    date_debut: str = Query(...),
    date_fin: str = Query(...),
):
    data = _run(RATIO_MASSE_SALARIALE_CA, (date_debut, date_fin), dwh_code)
    return {"success": True, "data": data}


@router.get("/saisie")
async def get_saisie(
    dwh_code: str = Query(...),
    exercice: int = Query(...),
    axe: Optional[str] = Query(None),
):
    """Récupère les lignes de budget saisies."""
    sql = "SELECT * FROM [dbo].[APP_Budgets] WHERE exercice = ?"
    params = [exercice]
    if axe:
        sql += " AND axe = ?"
        params.append(axe)
    sql += " ORDER BY mois, axe, code_poste"
    data = _run(sql, tuple(params), dwh_code)
    return {"success": True, "data": data}


@router.post("/saisie")
async def upsert_budget(item: BudgetItem, dwh_code: str = Query(...)):
    """Insère ou met à jour une ligne de budget (UPSERT)."""
    try:
        write_client(
            """
            MERGE [dbo].[APP_Budgets] AS target
            USING (SELECT ? AS exercice, ? AS mois, ? AS axe, ? AS code_poste) AS src
            ON target.exercice=src.exercice AND target.mois=src.mois
               AND target.axe=src.axe AND target.code_poste=src.code_poste
            WHEN MATCHED THEN
                UPDATE SET montant_budget=?, libelle_poste=?
            WHEN NOT MATCHED THEN
                INSERT (exercice,mois,axe,code_poste,libelle_poste,montant_budget)
                VALUES (?,?,?,?,?,?);
            """,
            params=(
                item.exercice, item.mois, item.axe, item.code_poste,
                item.montant_budget, item.libelle_poste,
                item.exercice, item.mois, item.axe, item.code_poste,
                item.libelle_poste, item.montant_budget,
            ),
            dwh_code=dwh_code,
        )
        return {"success": True, "message": "Budget enregistré"}
    except Exception as e:
        logger.error(f"[budget] Erreur upsert : {e}")
        raise HTTPException(status_code=500, detail=str(e))
