"""Dashboard API routes"""
from fastapi import APIRouter, Query, HTTPException
from datetime import datetime, date
from typing import Optional
import time

from ..database_unified import execute_app as execute_query
from ..sql.query_templates import (
    CHIFFRE_AFFAIRES_PAR_PERIODE,
    BALANCE_AGEE,
    COMPARATIF_ANNUEL
)
from ..services.calculs import (
    calculer_dso,
    calculer_evolution,
    identifier_alertes,
    formater_montant,
    get_periode_dates,
    parse_number,
    safe_sum
)
from ..services.query_logger import query_logger
from ..models.schemas import DashboardResponse, KPIData, DashboardKPIs, AlerteData

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


def build_ca_query_with_societe(base_query: str, societe: Optional[str]) -> tuple:
    """Ajoute le filtre société à une requête CA."""
    if societe:
        # Insérer le filtre société avant le GROUP BY
        modified = base_query.replace(
            "GROUP BY YEAR([Date BL]), MONTH([Date BL])",
            f"AND [Société] = ? GROUP BY YEAR([Date BL]), MONTH([Date BL])"
        )
        return modified, True
    return base_query, False


def build_balance_query_with_societe(base_query: str, societe: Optional[str]) -> tuple:
    """Ajoute le filtre société à la requête Balance Âgée."""
    if societe:
        # La colonne société dans BalanceAgee s'appelle SOCIETE
        if "WHERE" in base_query:
            modified = base_query + f" AND [SOCIETE] = ?"
        else:
            modified = base_query + f" WHERE [SOCIETE] = ?"
        return modified, True
    return base_query, False


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    date_debut: Optional[date] = Query(None, description="Date de début"),
    date_fin: Optional[date] = Query(None, description="Date de fin"),
    periode: Optional[str] = Query("annee_courante", description="Période prédéfinie"),
    societe: Optional[str] = Query(None, description="Filtre par société")
):
    """
    Récupère les KPIs principaux du dashboard.
    """
    try:
        # Déterminer les dates
        if not date_debut or not date_fin:
            date_debut_str, date_fin_str = get_periode_dates(periode)
        else:
            date_debut_str = date_debut.strftime("%Y-%m-%d")
            date_fin_str = date_fin.strftime("%Y-%m-%d")

        # Dates N-1 pour comparaison
        annee_courante = int(date_debut_str[:4])
        date_debut_n1 = date_debut_str.replace(str(annee_courante), str(annee_courante - 1))
        date_fin_n1 = date_fin_str.replace(str(annee_courante), str(annee_courante - 1))

        # Préparer requête avec filtre société si nécessaire
        query, has_societe = build_ca_query_with_societe(CHIFFRE_AFFAIRES_PAR_PERIODE, societe)
        params = (date_debut_str, date_fin_str, societe) if has_societe else (date_debut_str, date_fin_str)

        # Requête CA période courante
        start_time = time.time()
        ca_data = execute_query(query, params)
        query_logger.log_query(
            "ca_periode", "CA par Période",
            CHIFFRE_AFFAIRES_PAR_PERIODE,
            time.time() - start_time,
            len(ca_data)
        )

        # Calcul CA total
        ca_ht_total = sum(row.get('CA_HT', 0) or 0 for row in ca_data)
        ca_ttc_total = sum(row.get('CA_TTC', 0) or 0 for row in ca_data)
        cout_total = sum(row.get('Cout_Total', 0) or 0 for row in ca_data)
        marge_brute = ca_ht_total - cout_total
        nb_clients = sum(row.get('Nb_Clients', 0) or 0 for row in ca_data)

        # Requête CA N-1 pour évolution
        params_n1 = (date_debut_n1, date_fin_n1, societe) if has_societe else (date_debut_n1, date_fin_n1)
        start_time = time.time()
        ca_data_n1 = execute_query(query, params_n1)
        query_logger.log_query(
            "ca_periode_n1", "CA par Période N-1",
            CHIFFRE_AFFAIRES_PAR_PERIODE,
            time.time() - start_time,
            len(ca_data_n1)
        )
        ca_ht_n1 = sum(row.get('CA_HT', 0) or 0 for row in ca_data_n1)
        marge_n1 = sum((row.get('CA_HT', 0) or 0) - (row.get('Cout_Total', 0) or 0) for row in ca_data_n1)

        # Requête Balance Âgée (avec filtre société si nécessaire)
        balance_query, has_balance_societe = build_balance_query_with_societe(BALANCE_AGEE, societe)
        balance_params = (societe,) if has_balance_societe else None
        start_time = time.time()
        balance_data = execute_query(balance_query, balance_params)
        query_logger.log_query(
            "balance_agee", "Balance Âgée",
            BALANCE_AGEE,
            time.time() - start_time,
            len(balance_data)
        )

        # Calculs recouvrement (avec parse_number pour gérer les valeurs formatées)
        encours_total = safe_sum(balance_data, 'Solde_Cloture')
        creances_douteuses = safe_sum(balance_data, '+120')

        # Calcul DSO
        dso = calculer_dso(encours_total, ca_ttc_total)

        # Évolutions
        evolution_ca = calculer_evolution(ca_ht_total, ca_ht_n1)
        evolution_marge = calculer_evolution(marge_brute, marge_n1)

        # Construire les KPIs
        kpis = DashboardKPIs(
            ca_ht=KPIData(
                label="Chiffre d'Affaires HT",
                value=ca_ht_total,
                formatted_value=formater_montant(ca_ht_total),
                evolution=evolution_ca["evolution_pct"],
                tendance=evolution_ca["tendance"],
                unite="MAD"
            ),
            marge_brute=KPIData(
                label="Marge Brute",
                value=marge_brute,
                formatted_value=formater_montant(marge_brute),
                evolution=evolution_marge["evolution_pct"],
                tendance=evolution_marge["tendance"],
                unite="MAD"
            ),
            dso=KPIData(
                label="DSO",
                value=dso,
                formatted_value=f"{dso} jours",
                unite="jours"
            ),
            encours_clients=KPIData(
                label="Encours Clients",
                value=encours_total,
                formatted_value=formater_montant(encours_total),
                unite="MAD"
            ),
            nb_clients_actifs=KPIData(
                label="Clients Actifs",
                value=nb_clients,
                formatted_value=str(nb_clients),
                unite=""
            ),
            creances_douteuses=KPIData(
                label="Créances Douteuses (+120j)",
                value=creances_douteuses,
                formatted_value=formater_montant(creances_douteuses),
                unite="MAD"
            )
        )

        # Identifier les alertes
        alertes_data = identifier_alertes({
            "dso": dso,
            "taux_creances_douteuses": (creances_douteuses / encours_total * 100) if encours_total > 0 else 0
        })
        alertes = [AlerteData(**a) for a in alertes_data]

        return DashboardResponse(
            success=True,
            kpis=kpis,
            alertes=alertes,
            date_mise_a_jour=datetime.now()
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/evolution-mensuelle")
async def get_evolution_mensuelle(
    date_debut: Optional[date] = Query(None),
    date_fin: Optional[date] = Query(None),
    periode: Optional[str] = Query("annee_courante"),
    societe: Optional[str] = Query(None, description="Filtre par société")
):
    """
    Récupère l'évolution mensuelle du CA pour les graphiques.
    """
    try:
        if not date_debut or not date_fin:
            date_debut_str, date_fin_str = get_periode_dates(periode)
        else:
            date_debut_str = date_debut.strftime("%Y-%m-%d")
            date_fin_str = date_fin.strftime("%Y-%m-%d")

        query, has_societe = build_ca_query_with_societe(CHIFFRE_AFFAIRES_PAR_PERIODE, societe)
        params = (date_debut_str, date_fin_str, societe) if has_societe else (date_debut_str, date_fin_str)
        data = execute_query(query, params)

        # Formater pour les graphiques
        result = []
        for row in data:
            result.append({
                "periode": f"{row['Annee']}-{str(row['Mois']).zfill(2)}",
                "mois": row['Mois'],
                "annee": row['Annee'],
                "ca_ht": row.get('CA_HT', 0) or 0,
                "ca_ttc": row.get('CA_TTC', 0) or 0,
                "marge_brute": (row.get('CA_HT', 0) or 0) - (row.get('Cout_Total', 0) or 0),
                "nb_clients": row.get('Nb_Clients', 0) or 0,
                "nb_transactions": row.get('Nb_Transactions', 0) or 0
            })

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/comparatif-annuel")
async def get_comparatif_annuel(
    annee: int = Query(default=2025, description="Année de référence")
):
    """
    Récupère le comparatif N/N-1.
    """
    try:
        data = execute_query(COMPARATIF_ANNUEL, (annee - 1, annee))

        result = []
        for row in data:
            result.append({
                "annee": row['Annee'],
                "ca_ht": row.get('CA_HT', 0) or 0,
                "ca_ttc": row.get('CA_TTC', 0) or 0,
                "marge_brute": row.get('Marge_Brute', 0) or 0,
                "nb_clients": row.get('Nb_Clients', 0) or 0
            })

        # Calcul évolution si 2 années présentes
        evolution = None
        if len(result) == 2:
            ca_n = result[1]["ca_ht"] if result[1]["annee"] == annee else result[0]["ca_ht"]
            ca_n1 = result[0]["ca_ht"] if result[0]["annee"] == annee - 1 else result[1]["ca_ht"]
            if ca_n1 > 0:
                evolution = round(((ca_n - ca_n1) / ca_n1) * 100, 2)

        return {
            "success": True,
            "data": result,
            "evolution_pct": evolution
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
