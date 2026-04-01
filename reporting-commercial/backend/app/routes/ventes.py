"""Ventes API routes"""
from fastapi import APIRouter, Query, HTTPException
from datetime import date
from typing import Optional
import time

from ..database_unified import execute_app as execute_query
from ..sql.query_templates import (
    CHIFFRE_AFFAIRES_PAR_PERIODE,
    CHIFFRE_AFFAIRES_PAR_GAMME,
    CHIFFRE_AFFAIRES_PAR_CANAL,
    CHIFFRE_AFFAIRES_PAR_ZONE,
    CHIFFRE_AFFAIRES_PAR_COMMERCIAL,
    TOP_CLIENTS,
    TOP_PRODUITS
)
from ..services.calculs import get_periode_dates, calculer_evolution
from ..services.query_logger import query_logger

router = APIRouter(prefix="/api/ventes", tags=["Ventes"])


def add_societe_filter(query: str, societe: Optional[str]) -> tuple:
    """Ajoute le filtre société à une requête SQL si nécessaire."""
    if not societe:
        return query, False
    # Ajouter AND [Société] = ? avant GROUP BY ou ORDER BY
    if "GROUP BY" in query:
        modified = query.replace("GROUP BY", f"AND [Société] = ? GROUP BY")
    elif "ORDER BY" in query:
        modified = query.replace("ORDER BY", f"AND [Société] = ? ORDER BY")
    else:
        modified = query + f" AND [Société] = ?"
    return modified, True


def build_params(date_debut: str, date_fin: str, societe: Optional[str], has_societe: bool) -> tuple:
    """Construit les paramètres de requête."""
    if has_societe:
        return (date_debut, date_fin, societe)
    return (date_debut, date_fin)


@router.get("")
async def get_ventes(
    date_debut: Optional[date] = Query(None),
    date_fin: Optional[date] = Query(None),
    periode: Optional[str] = Query("annee_courante"),
    societe: Optional[str] = Query(None, description="Filtre par société"),
    gamme: Optional[str] = Query(None),
    canal: Optional[str] = Query(None),
    zone: Optional[str] = Query(None),
    commercial: Optional[str] = Query(None)
):
    """
    Récupère les données de ventes avec filtres.
    """
    try:
        if not date_debut or not date_fin:
            date_debut_str, date_fin_str = get_periode_dates(periode)
        else:
            date_debut_str = date_debut.strftime("%Y-%m-%d")
            date_fin_str = date_fin.strftime("%Y-%m-%d")

        # Préparer les requêtes avec filtre société
        q_periode, has_soc = add_societe_filter(CHIFFRE_AFFAIRES_PAR_PERIODE, societe)
        q_gamme, _ = add_societe_filter(CHIFFRE_AFFAIRES_PAR_GAMME, societe)
        q_canal, _ = add_societe_filter(CHIFFRE_AFFAIRES_PAR_CANAL, societe)
        q_zone, _ = add_societe_filter(CHIFFRE_AFFAIRES_PAR_ZONE, societe)
        q_commercial, _ = add_societe_filter(CHIFFRE_AFFAIRES_PAR_COMMERCIAL, societe)
        q_clients, _ = add_societe_filter(TOP_CLIENTS, societe)
        q_produits, _ = add_societe_filter(TOP_PRODUITS, societe)
        params = build_params(date_debut_str, date_fin_str, societe, has_soc)

        # CA par période
        start_time = time.time()
        par_periode = execute_query(q_periode, params)
        query_logger.log_query("ca_periode", "CA par Période", CHIFFRE_AFFAIRES_PAR_PERIODE, time.time() - start_time, len(par_periode))

        # CA par gamme
        start_time = time.time()
        par_gamme = execute_query(q_gamme, params)
        query_logger.log_query("ca_gamme", "CA par Gamme", CHIFFRE_AFFAIRES_PAR_GAMME, time.time() - start_time, len(par_gamme))

        # CA par canal
        start_time = time.time()
        par_canal = execute_query(q_canal, params)
        query_logger.log_query("ca_canal", "CA par Canal", CHIFFRE_AFFAIRES_PAR_CANAL, time.time() - start_time, len(par_canal))

        # CA par zone
        start_time = time.time()
        par_zone = execute_query(q_zone, params)
        query_logger.log_query("ca_zone", "CA par Zone", CHIFFRE_AFFAIRES_PAR_ZONE, time.time() - start_time, len(par_zone))

        # CA par commercial
        start_time = time.time()
        par_commercial = execute_query(q_commercial, params)
        query_logger.log_query("ca_commercial", "CA par Commercial", CHIFFRE_AFFAIRES_PAR_COMMERCIAL, time.time() - start_time, len(par_commercial))

        # Top clients
        start_time = time.time()
        top_clients = execute_query(q_clients, params)
        query_logger.log_query("top_clients", "Top Clients", TOP_CLIENTS, time.time() - start_time, len(top_clients))

        # Top produits
        start_time = time.time()
        top_produits = execute_query(q_produits, params)
        query_logger.log_query("top_produits", "Top Produits", TOP_PRODUITS, time.time() - start_time, len(top_produits))

        # Calculs totaux
        ca_total_ht = sum(row.get('CA_HT', 0) or 0 for row in par_periode)
        ca_total_ttc = sum(row.get('CA_TTC', 0) or 0 for row in par_periode)

        # Ajouter pourcentage CA pour chaque gamme
        for row in par_gamme:
            row['pourcentage_ca'] = round((row.get('CA_HT', 0) or 0) / ca_total_ht * 100, 2) if ca_total_ht > 0 else 0

        return {
            "success": True,
            "ca_total_ht": ca_total_ht,
            "ca_total_ttc": ca_total_ttc,
            "par_periode": [
                {
                    "annee": row['Annee'],
                    "mois": row['Mois'],
                    "periode": f"{row['Annee']}-{str(row['Mois']).zfill(2)}",
                    "ca_ht": row.get('CA_HT', 0) or 0,
                    "ca_ttc": row.get('CA_TTC', 0) or 0,
                    "cout_total": row.get('Cout_Total', 0) or 0,
                    "marge_brute": (row.get('CA_HT', 0) or 0) - (row.get('Cout_Total', 0) or 0),
                    "nb_clients": row.get('Nb_Clients', 0) or 0,
                    "nb_transactions": row.get('Nb_Transactions', 0) or 0
                }
                for row in par_periode
            ],
            "par_gamme": [
                {
                    "gamme": row.get('Gamme', 'Non défini'),
                    "ca_ht": row.get('CA_HT', 0) or 0,
                    "ca_ttc": row.get('CA_TTC', 0) or 0,
                    "cout_total": row.get('Cout_Total', 0) or 0,
                    "marge_brute": row.get('Marge_Brute', 0) or 0,
                    "taux_marge": row.get('Taux_Marge', 0) or 0,
                    "nb_ventes": row.get('Nb_Ventes', 0) or 0,
                    "pourcentage_ca": row.get('pourcentage_ca', 0)
                }
                for row in par_gamme
            ],
            "par_canal": [
                {
                    "canal": row.get('Canal', 'Non défini'),
                    "ca_ht": row.get('CA_HT', 0) or 0,
                    "ca_ttc": row.get('CA_TTC', 0) or 0,
                    "cout_total": row.get('Cout_Total', 0) or 0,
                    "nb_clients": row.get('Nb_Clients', 0) or 0
                }
                for row in par_canal
            ],
            "par_zone": [
                {
                    "zone": row.get('Zone', 'Non défini'),
                    "ca_ht": row.get('CA_HT', 0) or 0,
                    "ca_ttc": row.get('CA_TTC', 0) or 0,
                    "nb_clients": row.get('Nb_Clients', 0) or 0
                }
                for row in par_zone
            ],
            "par_commercial": [
                {
                    "commercial": row.get('Commercial', 'Non défini'),
                    "ca_ht": row.get('CA_HT', 0) or 0,
                    "ca_ttc": row.get('CA_TTC', 0) or 0,
                    "cout_total": row.get('Cout_Total', 0) or 0,
                    "marge_brute": row.get('Marge_Brute', 0) or 0,
                    "nb_clients": row.get('Nb_Clients', 0) or 0,
                    "nb_ventes": row.get('Nb_Ventes', 0) or 0
                }
                for row in par_commercial
            ],
            "top_clients": [
                {
                    "code_client": row.get('Code_Client', ''),
                    "nom_client": row.get('Nom_Client', ''),
                    "commercial": row.get('Commercial'),
                    "ca_ht": row.get('CA_HT', 0) or 0,
                    "ca_ttc": row.get('CA_TTC', 0) or 0,
                    "nb_transactions": row.get('Nb_Transactions', 0) or 0
                }
                for row in top_clients
            ],
            "top_produits": [
                {
                    "code_article": row.get('Code_Article', ''),
                    "designation": row.get('Designation', ''),
                    "gamme": row.get('Gamme'),
                    "quantite_vendue": row.get('Quantite_Vendue', 0) or 0,
                    "ca_ht": row.get('CA_HT', 0) or 0,
                    "cout_total": row.get('Cout_Total', 0) or 0
                }
                for row in top_produits
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/par-gamme")
async def get_ventes_par_gamme(
    date_debut: Optional[date] = Query(None),
    date_fin: Optional[date] = Query(None),
    periode: Optional[str] = Query("annee_courante"),
    societe: Optional[str] = Query(None, description="Filtre par société")
):
    """Récupère les ventes par gamme de produits."""
    try:
        if not date_debut or not date_fin:
            date_debut_str, date_fin_str = get_periode_dates(periode)
        else:
            date_debut_str = date_debut.strftime("%Y-%m-%d")
            date_fin_str = date_fin.strftime("%Y-%m-%d")

        query, has_soc = add_societe_filter(CHIFFRE_AFFAIRES_PAR_GAMME, societe)
        params = build_params(date_debut_str, date_fin_str, societe, has_soc)
        data = execute_query(query, params)

        ca_total = sum(row.get('CA_HT', 0) or 0 for row in data)

        result = []
        for row in data:
            ca_ht = row.get('CA_HT', 0) or 0
            result.append({
                "gamme": row.get('Gamme', 'Non défini'),
                "ca_ht": ca_ht,
                "ca_ttc": row.get('CA_TTC', 0) or 0,
                "marge_brute": row.get('Marge_Brute', 0) or 0,
                "taux_marge": row.get('Taux_Marge', 0) or 0,
                "nb_ventes": row.get('Nb_Ventes', 0) or 0,
                "pourcentage_ca": round(ca_ht / ca_total * 100, 2) if ca_total > 0 else 0
            })

        return {"success": True, "data": result, "ca_total": ca_total}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/par-commercial")
async def get_ventes_par_commercial(
    date_debut: Optional[date] = Query(None),
    date_fin: Optional[date] = Query(None),
    periode: Optional[str] = Query("annee_courante"),
    societe: Optional[str] = Query(None, description="Filtre par société")
):
    """Récupère les ventes par commercial."""
    try:
        if not date_debut or not date_fin:
            date_debut_str, date_fin_str = get_periode_dates(periode)
        else:
            date_debut_str = date_debut.strftime("%Y-%m-%d")
            date_fin_str = date_fin.strftime("%Y-%m-%d")

        query, has_soc = add_societe_filter(CHIFFRE_AFFAIRES_PAR_COMMERCIAL, societe)
        params = build_params(date_debut_str, date_fin_str, societe, has_soc)
        data = execute_query(query, params)

        result = []
        for row in data:
            result.append({
                "commercial": row.get('Commercial', 'Non défini'),
                "ca_ht": row.get('CA_HT', 0) or 0,
                "ca_ttc": row.get('CA_TTC', 0) or 0,
                "marge_brute": row.get('Marge_Brute', 0) or 0,
                "nb_clients": row.get('Nb_Clients', 0) or 0,
                "nb_ventes": row.get('Nb_Ventes', 0) or 0
            })

        return {"success": True, "data": result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top-clients")
async def get_top_clients(
    date_debut: Optional[date] = Query(None),
    date_fin: Optional[date] = Query(None),
    periode: Optional[str] = Query("annee_courante"),
    societe: Optional[str] = Query(None, description="Filtre par société"),
    limit: int = Query(10, ge=1, le=100)
):
    """Récupère le top des clients par CA."""
    try:
        if not date_debut or not date_fin:
            date_debut_str, date_fin_str = get_periode_dates(periode)
        else:
            date_debut_str = date_debut.strftime("%Y-%m-%d")
            date_fin_str = date_fin.strftime("%Y-%m-%d")

        # Modifier la requête pour le limit
        query = TOP_CLIENTS.replace("TOP 10", f"TOP {limit}")
        query, has_soc = add_societe_filter(query, societe)
        params = build_params(date_debut_str, date_fin_str, societe, has_soc)
        data = execute_query(query, params)

        result = []
        for row in data:
            result.append({
                "code_client": row.get('Code_Client', ''),
                "nom_client": row.get('Nom_Client', ''),
                "commercial": row.get('Commercial'),
                "ca_ht": row.get('CA_HT', 0) or 0,
                "ca_ttc": row.get('CA_TTC', 0) or 0,
                "nb_transactions": row.get('Nb_Transactions', 0) or 0
            })

        return {"success": True, "data": result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top-produits")
async def get_top_produits(
    date_debut: Optional[date] = Query(None),
    date_fin: Optional[date] = Query(None),
    periode: Optional[str] = Query("annee_courante"),
    societe: Optional[str] = Query(None, description="Filtre par société"),
    limit: int = Query(10, ge=1, le=100)
):
    """Récupère le top des produits par CA."""
    try:
        if not date_debut or not date_fin:
            date_debut_str, date_fin_str = get_periode_dates(periode)
        else:
            date_debut_str = date_debut.strftime("%Y-%m-%d")
            date_fin_str = date_fin.strftime("%Y-%m-%d")

        query = TOP_PRODUITS.replace("TOP 10", f"TOP {limit}")
        query, has_soc = add_societe_filter(query, societe)
        params = build_params(date_debut_str, date_fin_str, societe, has_soc)
        data = execute_query(query, params)

        result = []
        for row in data:
            result.append({
                "code_article": row.get('Code_Article', ''),
                "designation": row.get('Designation', ''),
                "gamme": row.get('Gamme'),
                "quantite_vendue": row.get('Quantite_Vendue', 0) or 0,
                "ca_ht": row.get('CA_HT', 0) or 0,
                "cout_total": row.get('Cout_Total', 0) or 0
            })

        return {"success": True, "data": result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
