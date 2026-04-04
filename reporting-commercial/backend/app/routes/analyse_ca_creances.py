"""Analyse CA et Creances Clients API"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional
import time

from ..database_unified import execute_app as execute_query
from ..services.query_logger import query_logger

router = APIRouter(prefix="/api/analyse-ca-creances", tags=["Analyse CA Creances"])

# Tables sources
TABLE_CA = "[dbo].[Chiffre_Affaires_Groupe_Bis]"
TABLE_CREANCES = "[dbo].[Balance_Agee_Clients_Groupe]"


@router.get("/kpis")
async def get_kpis(
    societe: Optional[str] = Query(None, description="Filtre par societe"),
    representant: Optional[str] = Query(None, description="Filtre par representant"),
    region: Optional[str] = Query(None, description="Filtre par region"),
    groupe: Optional[str] = Query(None, description="Filtre par groupe client"),
    annee: int = Query(2025, description="Annee pour le CA")
):
    """
    Recupere les KPIs globaux pour le dashboard CA et Creances.
    """
    try:
        # Filtres CA - construction differente selon presence du groupe
        ca_params = [annee]

        if groupe:
            # Avec jointure - utiliser alias ca.
            ca_filters = ["YEAR(ca.[Date BL]) = ?"]
            if societe:
                ca_filters.append("ca.[Société] = ?")
                ca_params.append(societe)
            if representant:
                ca_filters.append("ca.[Représentant] = ?")
                ca_params.append(representant)
            if region:
                ca_filters.append("ca.[Région] = ?")
                ca_params.append(region)
            ca_filters.append("bal.[Groupe] = ?")
            ca_params.append(groupe)

            ca_where = " AND ".join(ca_filters)
            ca_query = f"""
            SELECT
                COUNT(DISTINCT ca.[Code client]) AS Nb_Clients,
                COUNT(DISTINCT ca.[N° Pièce]) AS Nb_Factures,
                SUM(ca.[Quantité]) AS Quantite_Totale,
                SUM(ca.[Montant HT Net]) AS CA_HT,
                SUM(ca.[Montant TTC Net]) AS CA_TTC,
                SUM(ca.[Coût]) AS Cout_Total,
                SUM(ca.[Montant HT Net]) - SUM(ca.[Coût]) AS Marge_Brute
            FROM {TABLE_CA} ca
            INNER JOIN (SELECT DISTINCT Client, [Groupe] FROM {TABLE_CREANCES}) bal
                ON ca.[Intitulé client] = bal.Client
            WHERE {ca_where}
            """
        else:
            # Sans jointure - pas d'alias
            ca_filters = ["YEAR([Date BL]) = ?"]
            if societe:
                ca_filters.append("[Société] = ?")
                ca_params.append(societe)
            if representant:
                ca_filters.append("[Représentant] = ?")
                ca_params.append(representant)
            if region:
                ca_filters.append("[Région] = ?")
                ca_params.append(region)

            ca_where = " AND ".join(ca_filters)
            ca_query = f"""
            SELECT
                COUNT(DISTINCT [Code client]) AS Nb_Clients,
                COUNT(DISTINCT [N° Pièce]) AS Nb_Factures,
                SUM([Quantité]) AS Quantite_Totale,
                SUM([Montant HT Net]) AS CA_HT,
                SUM([Montant TTC Net]) AS CA_TTC,
                SUM([Coût]) AS Cout_Total,
                SUM([Montant HT Net]) - SUM([Coût]) AS Marge_Brute
            FROM {TABLE_CA}
            WHERE {ca_where}
            """

        start_time = time.time()
        ca_result = execute_query(ca_query, tuple(ca_params))
        ca_time = time.time() - start_time

        ca_data = ca_result[0] if ca_result else {}

        # Filtres Creances
        creance_filters = []
        creance_params = []
        if societe:
            creance_filters.append("Societe = ?")
            creance_params.append(societe)
        if representant:
            creance_filters.append("Representant = ?")
            creance_params.append(representant)
        if region:
            creance_filters.append("[Région] = ?")
            creance_params.append(region)
        if groupe:
            creance_filters.append("[Groupe] = ?")
            creance_params.append(groupe)

        creance_where = " WHERE " + " AND ".join(creance_filters) if creance_filters else ""

        # KPIs Creances
        creance_query = f"""
        SELECT
            COUNT(*) AS Nb_Clients_Creances,
            SUM(Solde_Cloture) AS Total_Solde,
            SUM(Impayes) AS Total_Impayes,
            SUM(Dec_25) AS Total_Dec,
            SUM(Nov_25) AS Total_Nov,
            SUM(Oct_25) AS Total_Oct,
            SUM(Sept_25) AS Total_Sept,
            SUM(Aout_25) AS Total_Aout,
            SUM(Juil_25) AS Total_Juil,
            SUM(Juin_25) AS Total_Juin,
            SUM(Mai_25) AS Total_Mai,
            SUM(Avr_25) AS Total_Avr,
            SUM(Mars_25) AS Total_Mars,
            SUM(Fevr_25) AS Total_Fevr,
            SUM(Janv_25) AS Total_Janv
        FROM {TABLE_CREANCES}
        {creance_where}
        """

        start_time = time.time()
        creance_result = execute_query(creance_query, tuple(creance_params) if creance_params else None)
        creance_time = time.time() - start_time

        creance_data = creance_result[0] if creance_result else {}

        # Calculer le taux de recouvrement
        ca_ht = float(ca_data.get('CA_HT', 0) or 0)
        total_solde = float(creance_data.get('Total_Solde', 0) or 0)
        taux_recouvrement = ((ca_ht - total_solde) / ca_ht * 100) if ca_ht > 0 else 0

        # Calculer le DSO (Days Sales Outstanding)
        dso = (total_solde / (ca_ht / 365)) if ca_ht > 0 else 0

        return {
            "success": True,
            "kpis": {
                "ca": {
                    "nb_clients": ca_data.get('Nb_Clients', 0) or 0,
                    "nb_factures": ca_data.get('Nb_Factures', 0) or 0,
                    "quantite_totale": ca_data.get('Quantite_Totale', 0) or 0,
                    "ca_ht": ca_ht,
                    "ca_ttc": float(ca_data.get('CA_TTC', 0) or 0),
                    "cout_total": float(ca_data.get('Cout_Total', 0) or 0),
                    "marge_brute": float(ca_data.get('Marge_Brute', 0) or 0),
                    "taux_marge": round((float(ca_data.get('Marge_Brute', 0) or 0) / ca_ht * 100) if ca_ht > 0 else 0, 2)
                },
                "creances": {
                    "nb_clients": creance_data.get('Nb_Clients_Creances', 0) or 0,
                    "total_solde": total_solde,
                    "total_impayes": float(creance_data.get('Total_Impayes', 0) or 0),
                    "taux_recouvrement": round(taux_recouvrement, 2),
                    "dso": round(dso, 0)
                },
                "mensuel": {
                    "dec_25": float(creance_data.get('Total_Dec', 0) or 0),
                    "nov_25": float(creance_data.get('Total_Nov', 0) or 0),
                    "oct_25": float(creance_data.get('Total_Oct', 0) or 0),
                    "sept_25": float(creance_data.get('Total_Sept', 0) or 0),
                    "aout_25": float(creance_data.get('Total_Aout', 0) or 0),
                    "juil_25": float(creance_data.get('Total_Juil', 0) or 0),
                    "juin_25": float(creance_data.get('Total_Juin', 0) or 0),
                    "mai_25": float(creance_data.get('Total_Mai', 0) or 0),
                    "avr_25": float(creance_data.get('Total_Avr', 0) or 0),
                    "mars_25": float(creance_data.get('Total_Mars', 0) or 0),
                    "fevr_25": float(creance_data.get('Total_Fevr', 0) or 0),
                    "janv_25": float(creance_data.get('Total_Janv', 0) or 0)
                }
            },
            "annee": annee,
            "query_time_ms": round((ca_time + creance_time) * 1000, 2)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top-clients-ca")
async def get_top_clients_ca(
    societe: Optional[str] = Query(None),
    representant: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    groupe: Optional[str] = Query(None),
    annee: int = Query(2025),
    limit: int = Query(10, ge=5, le=50)
):
    """Top clients par CA"""
    try:
        params = [annee]

        if groupe:
            # Avec jointure
            filters = ["YEAR(ca.[Date BL]) = ?"]
            if societe:
                filters.append("ca.[Société] = ?")
                params.append(societe)
            if representant:
                filters.append("ca.[Représentant] = ?")
                params.append(representant)
            if region:
                filters.append("ca.[Région] = ?")
                params.append(region)
            filters.append("bal.[Groupe] = ?")
            params.append(groupe)

            where_clause = " AND ".join(filters)
            query = f"""
            SELECT TOP {limit}
                ca.[Intitulé client] AS Client,
                COUNT(DISTINCT ca.[N° Pièce]) AS Nb_Factures,
                SUM(ca.[Quantité]) AS Quantite,
                SUM(ca.[Montant HT Net]) AS CA_HT,
                SUM(ca.[Montant TTC Net]) AS CA_TTC,
                SUM(ca.[Montant HT Net]) - SUM(ca.[Coût]) AS Marge
            FROM {TABLE_CA} ca
            INNER JOIN (SELECT DISTINCT Client, [Groupe] FROM {TABLE_CREANCES}) bal
                ON ca.[Intitulé client] = bal.Client
            WHERE {where_clause}
            GROUP BY ca.[Intitulé client]
            ORDER BY CA_HT DESC
            """
        else:
            # Sans jointure
            filters = ["YEAR([Date BL]) = ?"]
            if societe:
                filters.append("[Société] = ?")
                params.append(societe)
            if representant:
                filters.append("[Représentant] = ?")
                params.append(representant)
            if region:
                filters.append("[Région] = ?")
                params.append(region)

            where_clause = " AND ".join(filters)
            query = f"""
            SELECT TOP {limit}
                [Intitulé client] AS Client,
                COUNT(DISTINCT [N° Pièce]) AS Nb_Factures,
                SUM([Quantité]) AS Quantite,
                SUM([Montant HT Net]) AS CA_HT,
                SUM([Montant TTC Net]) AS CA_TTC,
                SUM([Montant HT Net]) - SUM([Coût]) AS Marge
            FROM {TABLE_CA}
            WHERE {where_clause}
            GROUP BY [Intitulé client]
            ORDER BY CA_HT DESC
            """

        data = execute_query(query, tuple(params))

        result = []
        for row in data:
            ca_ht = float(row.get('CA_HT', 0) or 0)
            marge = float(row.get('Marge', 0) or 0)
            result.append({
                "client": row.get('Client', ''),
                "nb_factures": row.get('Nb_Factures', 0) or 0,
                "quantite": row.get('Quantite', 0) or 0,
                "ca_ht": ca_ht,
                "ca_ttc": float(row.get('CA_TTC', 0) or 0),
                "marge": marge,
                "taux_marge": round((marge / ca_ht * 100) if ca_ht > 0 else 0, 2)
            })

        return {"success": True, "data": result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top-clients-creances")
async def get_top_clients_creances(
    societe: Optional[str] = Query(None),
    representant: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    groupe: Optional[str] = Query(None),
    limit: int = Query(10, ge=5, le=50)
):
    """Top clients par creances (solde)"""
    try:
        filters = []
        params = []
        if societe:
            filters.append("Societe = ?")
            params.append(societe)
        if representant:
            filters.append("Representant = ?")
            params.append(representant)
        if region:
            filters.append("[Région] = ?")
            params.append(region)
        if groupe:
            filters.append("[Groupe] = ?")
            params.append(groupe)

        where_clause = " WHERE " + " AND ".join(filters) if filters else ""

        query = f"""
        SELECT TOP {limit}
            Client,
            MAX(Representant) AS Representant,
            MAX(Societe) AS Societe,
            SUM(Solde_Cloture) AS Solde_Cloture,
            SUM(Impayes) AS Impayes
        FROM {TABLE_CREANCES}
        {where_clause}
        GROUP BY Client
        ORDER BY Solde_Cloture DESC
        """

        data = execute_query(query, tuple(params) if params else None)

        result = []
        for row in data:
            result.append({
                "client": row.get('Client', ''),
                "representant": row.get('Representant', ''),
                "societe": row.get('Societe', ''),
                "solde_cloture": float(row.get('Solde_Cloture', 0) or 0),
                "impayes": float(row.get('Impayes', 0) or 0)
            })

        return {"success": True, "data": result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ca-par-mois")
async def get_ca_par_mois(
    societe: Optional[str] = Query(None),
    representant: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    groupe: Optional[str] = Query(None),
    annee: int = Query(2025)
):
    """CA par mois pour graphique"""
    try:
        params = [annee]

        if groupe:
            # Avec jointure
            filters = ["YEAR(ca.[Date BL]) = ?"]
            if societe:
                filters.append("ca.[Société] = ?")
                params.append(societe)
            if representant:
                filters.append("ca.[Représentant] = ?")
                params.append(representant)
            if region:
                filters.append("ca.[Région] = ?")
                params.append(region)
            filters.append("bal.[Groupe] = ?")
            params.append(groupe)

            where_clause = " AND ".join(filters)
            query = f"""
            SELECT
                MONTH(ca.[Date BL]) AS Mois,
                SUM(ca.[Montant HT Net]) AS CA_HT,
                SUM(ca.[Montant TTC Net]) AS CA_TTC,
                SUM(ca.[Montant HT Net]) - SUM(ca.[Coût]) AS Marge,
                COUNT(DISTINCT ca.[Code client]) AS Nb_Clients,
                COUNT(DISTINCT ca.[N° Pièce]) AS Nb_Factures
            FROM {TABLE_CA} ca
            INNER JOIN (SELECT DISTINCT Client, [Groupe] FROM {TABLE_CREANCES}) bal
                ON ca.[Intitulé client] = bal.Client
            WHERE {where_clause}
            GROUP BY MONTH(ca.[Date BL])
            ORDER BY Mois
            """
        else:
            # Sans jointure
            filters = ["YEAR([Date BL]) = ?"]
            if societe:
                filters.append("[Société] = ?")
                params.append(societe)
            if representant:
                filters.append("[Représentant] = ?")
                params.append(representant)
            if region:
                filters.append("[Région] = ?")
                params.append(region)

            where_clause = " AND ".join(filters)
            query = f"""
            SELECT
                MONTH([Date BL]) AS Mois,
                SUM([Montant HT Net]) AS CA_HT,
                SUM([Montant TTC Net]) AS CA_TTC,
                SUM([Montant HT Net]) - SUM([Coût]) AS Marge,
                COUNT(DISTINCT [Code client]) AS Nb_Clients,
                COUNT(DISTINCT [N° Pièce]) AS Nb_Factures
            FROM {TABLE_CA}
            WHERE {where_clause}
            GROUP BY MONTH([Date BL])
            ORDER BY Mois
            """

        data = execute_query(query, tuple(params))

        # Noms des mois
        mois_noms = ['', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
                     'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']

        result = []
        for row in data:
            mois = row.get('Mois', 0) or 0
            result.append({
                "mois": mois,
                "mois_nom": mois_noms[mois] if 1 <= mois <= 12 else '',
                "ca_ht": float(row.get('CA_HT', 0) or 0),
                "ca_ttc": float(row.get('CA_TTC', 0) or 0),
                "marge": float(row.get('Marge', 0) or 0),
                "nb_clients": row.get('Nb_Clients', 0) or 0,
                "nb_factures": row.get('Nb_Factures', 0) or 0
            })

        return {"success": True, "data": result, "annee": annee}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ca-par-commercial")
async def get_ca_par_commercial(
    societe: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    groupe: Optional[str] = Query(None),
    annee: int = Query(2025)
):
    """CA par commercial"""
    try:
        params = [annee]

        if groupe:
            # Avec jointure
            filters = ["YEAR(ca.[Date BL]) = ?", "ca.[Représentant] IS NOT NULL"]
            if societe:
                filters.append("ca.[Société] = ?")
                params.append(societe)
            if region:
                filters.append("ca.[Région] = ?")
                params.append(region)
            filters.append("bal.[Groupe] = ?")
            params.append(groupe)

            where_clause = " AND ".join(filters)
            query = f"""
            SELECT
                ca.[Représentant] AS Commercial,
                COUNT(DISTINCT ca.[Code client]) AS Nb_Clients,
                COUNT(DISTINCT ca.[N° Pièce]) AS Nb_Factures,
                SUM(ca.[Montant HT Net]) AS CA_HT,
                SUM(ca.[Montant HT Net]) - SUM(ca.[Coût]) AS Marge
            FROM {TABLE_CA} ca
            INNER JOIN (SELECT DISTINCT Client, [Groupe] FROM {TABLE_CREANCES}) bal
                ON ca.[Intitulé client] = bal.Client
            WHERE {where_clause}
            GROUP BY ca.[Représentant]
            ORDER BY CA_HT DESC
            """
        else:
            # Sans jointure
            filters = ["YEAR([Date BL]) = ?", "[Représentant] IS NOT NULL"]
            if societe:
                filters.append("[Société] = ?")
                params.append(societe)
            if region:
                filters.append("[Région] = ?")
                params.append(region)

            where_clause = " AND ".join(filters)
            query = f"""
            SELECT
                [Représentant] AS Commercial,
                COUNT(DISTINCT [Code client]) AS Nb_Clients,
                COUNT(DISTINCT [N° Pièce]) AS Nb_Factures,
                SUM([Montant HT Net]) AS CA_HT,
                SUM([Montant HT Net]) - SUM([Coût]) AS Marge
            FROM {TABLE_CA}
            WHERE {where_clause}
            GROUP BY [Représentant]
            ORDER BY CA_HT DESC
            """

        data = execute_query(query, tuple(params))

        result = []
        for row in data:
            ca_ht = float(row.get('CA_HT', 0) or 0)
            marge = float(row.get('Marge', 0) or 0)
            result.append({
                "commercial": row.get('Commercial', ''),
                "nb_clients": row.get('Nb_Clients', 0) or 0,
                "nb_factures": row.get('Nb_Factures', 0) or 0,
                "ca_ht": ca_ht,
                "marge": marge,
                "taux_marge": round((marge / ca_ht * 100) if ca_ht > 0 else 0, 2)
            })

        return {"success": True, "data": result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/balance-agee-tranche")
async def get_balance_agee_tranche(
    societe: Optional[str] = Query(None),
    representant: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    groupe: Optional[str] = Query(None)
):
    """
    Balance agee par tranche d'anciennete.
    Calcule les creances par tranche basee sur les colonnes mensuelles.
    Tranches: 0-30j (Dec), 30-60j (Nov), 60-90j (Oct), 90-180j (Sept+Aout+Juil), >180j (reste)
    """
    try:
        filters = []
        params = []
        if societe:
            filters.append("Societe = ?")
            params.append(societe)
        if representant:
            filters.append("Representant = ?")
            params.append(representant)
        if region:
            filters.append("[Région] = ?")
            params.append(region)
        if groupe:
            filters.append("[Groupe] = ?")
            params.append(groupe)

        where_clause = " WHERE " + " AND ".join(filters) if filters else ""

        query = f"""
        SELECT
            COUNT(*) AS Nb_Clients,
            SUM(Solde_Cloture) AS Total_Solde,
            SUM(Impayes) AS Total_Impayes,
            SUM(ISNULL(Dec_25, 0)) AS Tranche_0_30,
            SUM(ISNULL(Nov_25, 0)) AS Tranche_30_60,
            SUM(ISNULL(Oct_25, 0)) AS Tranche_60_90,
            SUM(ISNULL(Sept_25, 0) + ISNULL(Aout_25, 0) + ISNULL(Juil_25, 0)) AS Tranche_90_180,
            SUM(ISNULL(Juin_25, 0) + ISNULL(Mai_25, 0) + ISNULL(Avr_25, 0) + ISNULL(Mars_25, 0) + ISNULL(Fevr_25, 0) + ISNULL(Janv_25, 0)) AS Tranche_Plus_180
        FROM {TABLE_CREANCES}
        {where_clause}
        """

        data = execute_query(query, tuple(params) if params else None)
        result = data[0] if data else {}

        total_solde = float(result.get('Total_Solde', 0) or 0)

        # Construire les tranches avec pourcentages
        tranches = [
            {
                "tranche": "0-30 jours",
                "label": "Courant",
                "montant": float(result.get('Tranche_0_30', 0) or 0),
                "pourcentage": round((float(result.get('Tranche_0_30', 0) or 0) / total_solde * 100) if total_solde > 0 else 0, 2),
                "color": "green"
            },
            {
                "tranche": "30-60 jours",
                "label": "1 mois",
                "montant": float(result.get('Tranche_30_60', 0) or 0),
                "pourcentage": round((float(result.get('Tranche_30_60', 0) or 0) / total_solde * 100) if total_solde > 0 else 0, 2),
                "color": "yellow"
            },
            {
                "tranche": "60-90 jours",
                "label": "2 mois",
                "montant": float(result.get('Tranche_60_90', 0) or 0),
                "pourcentage": round((float(result.get('Tranche_60_90', 0) or 0) / total_solde * 100) if total_solde > 0 else 0, 2),
                "color": "orange"
            },
            {
                "tranche": "90-180 jours",
                "label": "3-6 mois",
                "montant": float(result.get('Tranche_90_180', 0) or 0),
                "pourcentage": round((float(result.get('Tranche_90_180', 0) or 0) / total_solde * 100) if total_solde > 0 else 0, 2),
                "color": "red"
            },
            {
                "tranche": ">180 jours",
                "label": "+6 mois",
                "montant": float(result.get('Tranche_Plus_180', 0) or 0),
                "pourcentage": round((float(result.get('Tranche_Plus_180', 0) or 0) / total_solde * 100) if total_solde > 0 else 0, 2),
                "color": "darkred"
            }
        ]

        return {
            "success": True,
            "data": {
                "nb_clients": result.get('Nb_Clients', 0) or 0,
                "total_solde": total_solde,
                "total_impayes": float(result.get('Total_Impayes', 0) or 0),
                "tranches": tranches
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/balance-agee-detail")
async def get_balance_agee_detail(
    societe: Optional[str] = Query(None),
    representant: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    groupe: Optional[str] = Query(None),
    limit: int = Query(100, ge=10, le=500)
):
    """
    Balance agee detaillee par client avec colonnes par tranche.
    Retourne chaque client avec ses montants par tranche d'anciennete.
    """
    try:
        filters = []
        params = []
        if societe:
            filters.append("Societe = ?")
            params.append(societe)
        if representant:
            filters.append("Representant = ?")
            params.append(representant)
        if region:
            filters.append("[Région] = ?")
            params.append(region)
        if groupe:
            filters.append("[Groupe] = ?")
            params.append(groupe)

        where_clause = " WHERE " + " AND ".join(filters) if filters else ""

        query = f"""
        SELECT TOP {limit}
            Client,
            MAX(Representant) AS Representant,
            MAX(Societe) AS Societe,
            SUM(Solde_Cloture) AS Solde_Cloture,
            SUM(Impayes) AS Impayes,
            SUM(ISNULL(Dec_25, 0)) AS Tranche_0_30,
            SUM(ISNULL(Nov_25, 0)) AS Tranche_30_60,
            SUM(ISNULL(Oct_25, 0)) AS Tranche_60_90,
            SUM(ISNULL(Sept_25, 0) + ISNULL(Aout_25, 0) + ISNULL(Juil_25, 0)) AS Tranche_90_180,
            SUM(ISNULL(Juin_25, 0) + ISNULL(Mai_25, 0) + ISNULL(Avr_25, 0) + ISNULL(Mars_25, 0) + ISNULL(Fevr_25, 0) + ISNULL(Janv_25, 0)) AS Tranche_Plus_180
        FROM {TABLE_CREANCES}
        {where_clause}
        GROUP BY Client
        ORDER BY Solde_Cloture DESC
        """

        data = execute_query(query, tuple(params) if params else None)

        result = []
        for row in data:
            solde = float(row.get('Solde_Cloture', 0) or 0)
            t_0_30 = float(row.get('Tranche_0_30', 0) or 0)
            t_30_60 = float(row.get('Tranche_30_60', 0) or 0)
            t_60_90 = float(row.get('Tranche_60_90', 0) or 0)
            t_90_180 = float(row.get('Tranche_90_180', 0) or 0)
            t_plus_180 = float(row.get('Tranche_Plus_180', 0) or 0)

            # Calculer DSO pondere (age moyen des creances en jours)
            # 0-30j = 15j, 30-60j = 45j, 60-90j = 75j, 90-180j = 135j, >180j = 270j
            total_creances = t_0_30 + t_30_60 + t_60_90 + t_90_180 + t_plus_180
            if total_creances > 0:
                dso = (t_0_30 * 15 + t_30_60 * 45 + t_60_90 * 75 + t_90_180 * 135 + t_plus_180 * 270) / total_creances
            else:
                dso = 0

            result.append({
                "client": row.get('Client', ''),
                "representant": row.get('Representant', ''),
                "societe": row.get('Societe', ''),
                "solde_cloture": solde,
                "impayes": float(row.get('Impayes', 0) or 0),
                "dso": round(dso, 0),
                "tranche_0_30": t_0_30,
                "tranche_30_60": t_30_60,
                "tranche_60_90": t_60_90,
                "tranche_90_180": t_90_180,
                "tranche_plus_180": t_plus_180
            })

        return {"success": True, "data": result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/filtres")
async def get_filtres():
    """Recupere les filtres disponibles"""
    try:
        # Societes depuis CA
        societes_query = f"""
        SELECT DISTINCT [Société] AS Societe
        FROM {TABLE_CA}
        WHERE [Société] IS NOT NULL AND YEAR([Date BL]) = 2025
        ORDER BY [Société]
        """
        societes = execute_query(societes_query)

        # Representants depuis CA
        representants_query = f"""
        SELECT DISTINCT [Représentant] AS Representant
        FROM {TABLE_CA}
        WHERE [Représentant] IS NOT NULL AND YEAR([Date BL]) = 2025
        ORDER BY [Représentant]
        """
        representants = execute_query(representants_query)

        # Regions depuis CA
        regions_query = f"""
        SELECT DISTINCT [Région] AS Region
        FROM {TABLE_CA}
        WHERE [Région] IS NOT NULL AND YEAR([Date BL]) = 2025
        ORDER BY [Région]
        """
        regions = execute_query(regions_query)

        # Groupes depuis Balance_Agee_Clients_Groupe
        groupes_query = f"""
        SELECT DISTINCT [Groupe]
        FROM {TABLE_CREANCES}
        WHERE [Groupe] IS NOT NULL AND [Groupe] <> ''
        ORDER BY [Groupe]
        """
        groupes = execute_query(groupes_query)

        return {
            "success": True,
            "societes": [r['Societe'] for r in societes if r.get('Societe')],
            "representants": [r['Representant'] for r in representants if r.get('Representant')],
            "regions": [r['Region'] for r in regions if r.get('Region')],
            "groupes": [r['Groupe'] for r in groupes if r.get('Groupe')]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
