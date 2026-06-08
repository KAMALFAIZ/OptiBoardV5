"""Dettes Fournisseurs API routes — miroir de recouvrement.py pour les achats"""
from fastapi import APIRouter, Query, HTTPException
from datetime import date
from typing import Optional

from ..database_unified import execute_app as execute_query
from ..sql.query_templates import (
    BALANCE_AGEE_FOURNISSEURS,
    ECHEANCES_FOURNISSEURS_NON_REGLEES,
    ECHEANCES_FOURNISSEURS,
    ECHEANCES_FOURNISSEURS_PAR_FOURNISSEUR,
    KPIS_ECHEANCES_FOURNISSEURS,
)

router = APIRouter(prefix="/api/dettes-fournisseurs", tags=["Dettes Fournisseurs"])


def _date_ref(date_ref: Optional[date]) -> str:
    if date_ref:
        return date_ref.strftime("%Y-%m-%d")
    return date.today().strftime("%Y-%m-%d")


def _get_balance_data(societe: Optional[str], d: str):
    """Balance âgée fournisseurs avec filtres optionnels."""
    params = [d, d, d, d, d, d, d]
    query = BALANCE_AGEE_FOURNISSEURS
    if societe:
        query = query.rstrip() + "\n  AND [DB] = ?"
        params.append(societe)
    return execute_query(query, tuple(params))


@router.get("")
async def get_dettes_fournisseurs(
    societe: Optional[str] = Query(None),
    date_ref: Optional[date] = Query(None),
):
    """Vue d'ensemble des dettes fournisseurs : KPIs, tranches, top 10."""
    try:
        d = _date_ref(date_ref)
        data = _get_balance_data(societe, d)

        total_dettes = sum(r.get("Reste_A_Payer", 0) or 0 for r in data)
        total_0_30 = sum(r.get("Tranche_0_30", 0) or 0 for r in data)
        total_31_60 = sum(r.get("Tranche_31_60", 0) or 0 for r in data)
        total_61_90 = sum(r.get("Tranche_61_90", 0) or 0 for r in data)
        total_91_120 = sum(r.get("Tranche_91_120", 0) or 0 for r in data)
        total_plus_120 = sum(r.get("Tranche_Plus_120", 0) or 0 for r in data)

        top_10 = sorted(data, key=lambda x: x.get("Reste_A_Payer", 0), reverse=True)[:10]

        dettes_critiques = [
            r for r in data if (r.get("Tranche_Plus_120", 0) or 0) > 0
        ]
        dettes_critiques = sorted(dettes_critiques, key=lambda x: x.get("Tranche_Plus_120", 0), reverse=True)

        taux_critiques = round(total_plus_120 / total_dettes * 100, 2) if total_dettes > 0 else 0

        def pct(v):
            return round(v / total_dettes * 100, 2) if total_dettes > 0 else 0

        return {
            "success": True,
            "date_reference": d,
            "dettes_total": round(total_dettes, 2),
            "nb_fournisseurs": len(data),
            "dettes_critiques_montant": round(total_plus_120, 2),
            "taux_dettes_critiques": taux_critiques,
            "repartition_tranches": {
                "0_30": round(total_0_30, 2),
                "31_60": round(total_31_60, 2),
                "61_90": round(total_61_90, 2),
                "91_120": round(total_91_120, 2),
                "plus_120": round(total_plus_120, 2),
            },
            "repartition_pct": {
                "0_30": pct(total_0_30),
                "31_60": pct(total_31_60),
                "61_90": pct(total_61_90),
                "91_120": pct(total_91_120),
                "plus_120": pct(total_plus_120),
            },
            "top_dettes": [
                {
                    "fournisseur": r.get("Nom_Fournisseur", ""),
                    "code": r.get("Code_Fournisseur", ""),
                    "societe": r.get("Societe"),
                    "dettes": r.get("Reste_A_Payer", 0),
                    "tranche_0_30": r.get("Tranche_0_30", 0),
                    "tranche_31_60": r.get("Tranche_31_60", 0),
                    "tranche_61_90": r.get("Tranche_61_90", 0),
                    "tranche_91_120": r.get("Tranche_91_120", 0),
                    "tranche_plus_120": r.get("Tranche_Plus_120", 0),
                }
                for r in top_10
            ],
            "dettes_critiques": [
                {
                    "fournisseur": r.get("Nom_Fournisseur", ""),
                    "code": r.get("Code_Fournisseur", ""),
                    "societe": r.get("Societe"),
                    "dettes_plus_120": r.get("Tranche_Plus_120", 0),
                    "dettes_total": r.get("Reste_A_Payer", 0),
                }
                for r in dettes_critiques[:20]
            ],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/balance-agee")
async def get_balance_agee_fournisseurs(
    societe: Optional[str] = Query(None),
    date_ref: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """Balance âgée détaillée par fournisseur."""
    try:
        d = _date_ref(date_ref)
        data = _get_balance_data(societe, d)

        total = len(data)
        start = (page - 1) * page_size
        paginated = data[start:start + page_size]

        return {
            "success": True,
            "date_reference": d,
            "data": paginated,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fournisseur/{code_fournisseur}")
async def get_fournisseur_detail(code_fournisseur: str):
    """Détail d'un fournisseur (répartition par tranche)."""
    try:
        d = _date_ref(None)
        data = _get_balance_data(None, d)
        rows = [r for r in data if r.get("Code_Fournisseur", "").strip() == code_fournisseur.strip()]

        if not rows:
            raise HTTPException(status_code=404, detail="Fournisseur non trouvé")

        r = rows[0]
        return {
            "success": True,
            "fournisseur": r.get("Nom_Fournisseur", ""),
            "code": r.get("Code_Fournisseur", ""),
            "societe": r.get("Societe"),
            "dettes_total": r.get("Reste_A_Payer", 0),
            "repartition": {
                "0_30": r.get("Tranche_0_30", 0),
                "31_60": r.get("Tranche_31_60", 0),
                "61_90": r.get("Tranche_61_90", 0),
                "91_120": r.get("Tranche_91_120", 0),
                "plus_120": r.get("Tranche_Plus_120", 0),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/echeances")
async def get_echeances_fournisseurs(
    societe: Optional[str] = Query(None),
    fournisseur: Optional[str] = Query(None),
    tranche: Optional[str] = Query(None),
    date_ref: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """Échéances fournisseurs non réglées avec détail et tranches."""
    try:
        d = _date_ref(date_ref)
        # 6 paramètres date pour les DATEDIFF/CASE
        params = [d, d, d, d, d, d]
        query = ECHEANCES_FOURNISSEURS_NON_REGLEES
        conditions = []
        extra = []

        if societe:
            conditions.append("[DB] = ?")
            extra.append(societe)
        if fournisseur:
            conditions.append("[Code fournisseur] = ?")
            extra.append(fournisseur)

        if conditions:
            query = query.rstrip() + "\n  AND " + " AND ".join(conditions)

        query += "\nORDER BY [Date d'échéance] ASC"
        data = execute_query(query, tuple(params + extra))

        if tranche:
            tranche_map = {
                "a_echoir": "A échoir",
                "0-30": "0-30 jours",
                "31-60": "31-60 jours",
                "61-90": "61-90 jours",
                "91-120": "91-120 jours",
                "+120": "+120 jours",
                "plus120": "+120 jours",
            }
            label = tranche_map.get(tranche)
            if label:
                data = [r for r in data if r.get("Tranche_Age") == label]

        total_reste = sum(r.get("Reste_A_Payer", 0) or 0 for r in data)
        total = len(data)
        paginated = data[(page - 1) * page_size:(page - 1) * page_size + page_size]

        return {
            "success": True,
            "data": paginated,
            "total": total,
            "total_reste_a_payer": round(total_reste, 2),
            "date_reference": d,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tranche/{tranche}")
async def get_fournisseurs_par_tranche(
    tranche: str,
    societe: Optional[str] = Query(None),
    date_ref: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    """Fournisseurs filtrés par tranche d'âge."""
    try:
        d = _date_ref(date_ref)
        data = _get_balance_data(societe, d)

        tranche_map = {
            "0-30": "Tranche_0_30",
            "31-60": "Tranche_31_60",
            "61-90": "Tranche_61_90",
            "91-120": "Tranche_91_120",
            "+120": "Tranche_Plus_120",
            "plus120": "Tranche_Plus_120",
        }
        col = tranche_map.get(tranche)
        if not col:
            raise HTTPException(status_code=400, detail="Tranche invalide")

        filtered = [
            {
                "fournisseur": r.get("Nom_Fournisseur", ""),
                "code": r.get("Code_Fournisseur", ""),
                "societe": r.get("Societe"),
                "montant_tranche": r.get(col, 0),
                "dettes_total": r.get("Reste_A_Payer", 0),
            }
            for r in data
            if (r.get(col, 0) or 0) > 0
        ]
        filtered = sorted(filtered, key=lambda x: x["montant_tranche"], reverse=True)

        total = len(filtered)
        paginated = filtered[(page - 1) * page_size:(page - 1) * page_size + page_size]

        return {
            "success": True,
            "tranche": tranche,
            "data": paginated,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
            "total_montant": sum(r["montant_tranche"] for r in filtered),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
