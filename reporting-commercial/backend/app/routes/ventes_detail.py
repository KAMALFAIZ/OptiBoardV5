"""Ventes Drill-Down API routes"""
from fastapi import APIRouter, Query, HTTPException
from datetime import date
from typing import Optional
import time

from ..database_unified import execute_app as execute_query
from ..services.calculs import get_periode_dates
from ..services.query_logger import query_logger

router = APIRouter(prefix="/api/ventes/detail", tags=["Ventes - Détails"])


@router.get("/gamme/{gamme}")
async def get_detail_gamme(
    gamme: str,
    date_debut: Optional[date] = Query(None),
    date_fin: Optional[date] = Query(None),
    periode: Optional[str] = Query("annee_courante"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100)
):
    """
    Récupère le détail des ventes pour une gamme de produits.
    """
    try:
        if not date_debut or not date_fin:
            date_debut_str, date_fin_str = get_periode_dates(periode)
        else:
            date_debut_str = date_debut.strftime("%Y-%m-%d")
            date_fin_str = date_fin.strftime("%Y-%m-%d")

        query = """
        SELECT
            [Code article] AS Code_Article,
            [Désignation] AS Designation,
            SUM([Quantité]) AS Quantite_Vendue,
            SUM([Montant HT Net]) AS CA_HT,
            SUM([Coût]) AS Cout_Total,
            COUNT(*) AS Nb_Ventes,
            COUNT(DISTINCT [Code client]) AS Nb_Clients
        FROM [dbo].[DashBoard_CA]
        WHERE [Catalogue 1] = ?
          AND [Date BL] BETWEEN ? AND ?
        GROUP BY [Code article], [Désignation]
        ORDER BY CA_HT DESC
        """

        start_time = time.time()
        data = execute_query(query, (gamme, date_debut_str, date_fin_str))
        query_logger.log_query(
            "detail_gamme", f"Détail Gamme {gamme}",
            query, time.time() - start_time, len(data)
        )

        # Pagination
        total = len(data)
        start = (page - 1) * page_size
        end = start + page_size
        paginated = data[start:end]

        ca_total = sum(row.get('CA_HT', 0) or 0 for row in data)

        result = []
        for row in paginated:
            ca_ht = row.get('CA_HT', 0) or 0
            result.append({
                "code_article": row.get('Code_Article', ''),
                "designation": row.get('Designation', ''),
                "quantite_vendue": row.get('Quantite_Vendue', 0) or 0,
                "ca_ht": ca_ht,
                "cout_total": row.get('Cout_Total', 0) or 0,
                "marge_brute": ca_ht - (row.get('Cout_Total', 0) or 0),
                "nb_ventes": row.get('Nb_Ventes', 0) or 0,
                "nb_clients": row.get('Nb_Clients', 0) or 0,
                "pourcentage_ca": round(ca_ht / ca_total * 100, 2) if ca_total > 0 else 0
            })

        return {
            "success": True,
            "gamme": gamme,
            "data": result,
            "ca_total_gamme": round(ca_total, 2),
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/client/{code_client}")
async def get_detail_client(
    code_client: str,
    date_debut: Optional[date] = Query(None),
    date_fin: Optional[date] = Query(None),
    periode: Optional[str] = Query("annee_courante"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100)
):
    """
    Récupère l'historique des achats d'un client.
    """
    try:
        if not date_debut or not date_fin:
            date_debut_str, date_fin_str = get_periode_dates(periode)
        else:
            date_debut_str = date_debut.strftime("%Y-%m-%d")
            date_fin_str = date_fin.strftime("%Y-%m-%d")

        # Informations client
        query_client = """
        SELECT TOP 1
            [Code client] AS Code_Client,
            [Intitulé client] AS Nom_Client,
            [Représentant] AS Commercial,
            [Catégorie_] AS Canal
        FROM [dbo].[DashBoard_CA]
        WHERE [Code client] = ?
        """

        client_info = execute_query(query_client, (code_client,))
        if not client_info:
            raise HTTPException(status_code=404, detail="Client non trouvé")

        # Détail des achats
        query_achats = """
        SELECT
            [Date BL] AS Date_BL,
            [N° Pièce] AS Numero_Piece,
            [Code article] AS Code_Article,
            [Désignation] AS Designation,
            [Catalogue 1] AS Gamme,
            [Quantité] AS Quantite,
            [Montant HT Net] AS Montant_HT,
            [Montant TTC Net] AS Montant_TTC
        FROM [dbo].[DashBoard_CA]
        WHERE [Code client] = ?
          AND [Date BL] BETWEEN ? AND ?
        ORDER BY [Date BL] DESC
        """

        start_time = time.time()
        achats = execute_query(query_achats, (code_client, date_debut_str, date_fin_str))
        query_logger.log_query(
            "detail_client", f"Détail Client {code_client}",
            query_achats, time.time() - start_time, len(achats)
        )

        # Stats
        ca_total = sum(row.get('Montant_HT', 0) or 0 for row in achats)
        nb_transactions = len(achats)

        # Pagination
        total = len(achats)
        start = (page - 1) * page_size
        end = start + page_size
        paginated = achats[start:end]

        return {
            "success": True,
            "client": {
                "code": client_info[0].get('Code_Client', ''),
                "nom": client_info[0].get('Nom_Client', ''),
                "commercial": client_info[0].get('Commercial'),
                "canal": client_info[0].get('Canal')
            },
            "ca_total": round(ca_total, 2),
            "nb_transactions": nb_transactions,
            "achats": [
                {
                    "date": row.get('Date_BL'),
                    "numero_piece": row.get('Numero_Piece'),
                    "code_article": row.get('Code_Article', ''),
                    "designation": row.get('Designation', ''),
                    "gamme": row.get('Gamme'),
                    "quantite": row.get('Quantite', 0) or 0,
                    "montant_ht": row.get('Montant_HT', 0) or 0,
                    "montant_ttc": row.get('Montant_TTC', 0) or 0
                }
                for row in paginated
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/produit/{code_article}")
async def get_detail_produit(
    code_article: str,
    date_debut: Optional[date] = Query(None),
    date_fin: Optional[date] = Query(None),
    periode: Optional[str] = Query("annee_courante"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100)
):
    """
    Récupère l'historique des ventes d'un produit.
    """
    try:
        if not date_debut or not date_fin:
            date_debut_str, date_fin_str = get_periode_dates(periode)
        else:
            date_debut_str = date_debut.strftime("%Y-%m-%d")
            date_fin_str = date_fin.strftime("%Y-%m-%d")

        # Informations produit
        query_produit = """
        SELECT TOP 1
            [Code article] AS Code_Article,
            [Désignation] AS Designation,
            [Catalogue 1] AS Gamme
        FROM [dbo].[DashBoard_CA]
        WHERE [Code article] = ?
        """

        produit_info = execute_query(query_produit, (code_article,))
        if not produit_info:
            raise HTTPException(status_code=404, detail="Produit non trouvé")

        # Ventes du produit
        query_ventes = """
        SELECT
            [Date BL] AS Date_BL,
            [N° Pièce] AS Numero_Piece,
            [Code client] AS Code_Client,
            [Intitulé client] AS Nom_Client,
            [Représentant] AS Commercial,
            [Quantité] AS Quantite,
            [Montant HT Net] AS Montant_HT,
            [Coût] AS Cout
        FROM [dbo].[DashBoard_CA]
        WHERE [Code article] = ?
          AND [Date BL] BETWEEN ? AND ?
        ORDER BY [Date BL] DESC
        """

        start_time = time.time()
        ventes = execute_query(query_ventes, (code_article, date_debut_str, date_fin_str))
        query_logger.log_query(
            "detail_produit", f"Détail Produit {code_article}",
            query_ventes, time.time() - start_time, len(ventes)
        )

        # Stats
        ca_total = sum(row.get('Montant_HT', 0) or 0 for row in ventes)
        qte_totale = sum(row.get('Quantite', 0) or 0 for row in ventes)
        nb_clients = len(set(row.get('Code_Client', '') for row in ventes))

        # Pagination
        total = len(ventes)
        start = (page - 1) * page_size
        end = start + page_size
        paginated = ventes[start:end]

        return {
            "success": True,
            "produit": {
                "code": produit_info[0].get('Code_Article', ''),
                "designation": produit_info[0].get('Designation', ''),
                "gamme": produit_info[0].get('Gamme')
            },
            "ca_total": round(ca_total, 2),
            "quantite_totale": qte_totale,
            "nb_clients": nb_clients,
            "ventes": [
                {
                    "date": row.get('Date_BL'),
                    "numero_piece": row.get('Numero_Piece'),
                    "code_client": row.get('Code_Client', ''),
                    "nom_client": row.get('Nom_Client', ''),
                    "commercial": row.get('Commercial'),
                    "quantite": row.get('Quantite', 0) or 0,
                    "montant_ht": row.get('Montant_HT', 0) or 0,
                    "cout": row.get('Cout', 0) or 0
                }
                for row in paginated
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/commercial/{commercial}")
async def get_detail_commercial(
    commercial: str,
    date_debut: Optional[date] = Query(None),
    date_fin: Optional[date] = Query(None),
    periode: Optional[str] = Query("annee_courante")
):
    """
    Récupère le détail des performances d'un commercial.
    """
    try:
        if not date_debut or not date_fin:
            date_debut_str, date_fin_str = get_periode_dates(periode)
        else:
            date_debut_str = date_debut.strftime("%Y-%m-%d")
            date_fin_str = date_fin.strftime("%Y-%m-%d")

        # Stats globales
        query_stats = """
        SELECT
            SUM([Montant HT Net]) AS CA_HT,
            SUM([Montant TTC Net]) AS CA_TTC,
            SUM([Coût]) AS Cout_Total,
            COUNT(DISTINCT [Code client]) AS Nb_Clients,
            COUNT(*) AS Nb_Transactions
        FROM [dbo].[DashBoard_CA]
        WHERE [Représentant] = ?
          AND [Date BL] BETWEEN ? AND ?
        """

        stats = execute_query(query_stats, (commercial, date_debut_str, date_fin_str))

        # Top clients du commercial
        query_clients = """
        SELECT TOP 10
            [Code client] AS Code_Client,
            [Intitulé client] AS Nom_Client,
            SUM([Montant HT Net]) AS CA_HT,
            COUNT(*) AS Nb_Transactions
        FROM [dbo].[DashBoard_CA]
        WHERE [Représentant] = ?
          AND [Date BL] BETWEEN ? AND ?
        GROUP BY [Code client], [Intitulé client]
        ORDER BY CA_HT DESC
        """

        top_clients = execute_query(query_clients, (commercial, date_debut_str, date_fin_str))

        # Ventes par gamme
        query_gammes = """
        SELECT
            [Catalogue 1] AS Gamme,
            SUM([Montant HT Net]) AS CA_HT,
            COUNT(*) AS Nb_Ventes
        FROM [dbo].[DashBoard_CA]
        WHERE [Représentant] = ?
          AND [Date BL] BETWEEN ? AND ?
        GROUP BY [Catalogue 1]
        ORDER BY CA_HT DESC
        """

        par_gamme = execute_query(query_gammes, (commercial, date_debut_str, date_fin_str))

        # Evolution mensuelle
        query_mensuel = """
        SELECT
            YEAR([Date BL]) AS Annee,
            MONTH([Date BL]) AS Mois,
            SUM([Montant HT Net]) AS CA_HT
        FROM [dbo].[DashBoard_CA]
        WHERE [Représentant] = ?
          AND [Date BL] BETWEEN ? AND ?
        GROUP BY YEAR([Date BL]), MONTH([Date BL])
        ORDER BY Annee, Mois
        """

        evolution = execute_query(query_mensuel, (commercial, date_debut_str, date_fin_str))

        stat = stats[0] if stats else {}
        ca_ht = stat.get('CA_HT', 0) or 0
        cout = stat.get('Cout_Total', 0) or 0

        return {
            "success": True,
            "commercial": commercial,
            "stats": {
                "ca_ht": round(ca_ht, 2),
                "ca_ttc": round(stat.get('CA_TTC', 0) or 0, 2),
                "marge_brute": round(ca_ht - cout, 2),
                "taux_marge": round((ca_ht - cout) / ca_ht * 100, 2) if ca_ht > 0 else 0,
                "nb_clients": stat.get('Nb_Clients', 0) or 0,
                "nb_transactions": stat.get('Nb_Transactions', 0) or 0
            },
            "top_clients": [
                {
                    "code_client": row.get('Code_Client', ''),
                    "nom_client": row.get('Nom_Client', ''),
                    "ca_ht": row.get('CA_HT', 0) or 0,
                    "nb_transactions": row.get('Nb_Transactions', 0) or 0
                }
                for row in top_clients
            ],
            "par_gamme": [
                {
                    "gamme": row.get('Gamme', 'Non défini'),
                    "ca_ht": row.get('CA_HT', 0) or 0,
                    "nb_ventes": row.get('Nb_Ventes', 0) or 0
                }
                for row in par_gamme
            ],
            "evolution_mensuelle": [
                {
                    "periode": f"{row['Annee']}-{str(row['Mois']).zfill(2)}",
                    "ca_ht": row.get('CA_HT', 0) or 0
                }
                for row in evolution
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mois/{annee}/{mois}")
async def get_detail_mois(
    annee: int,
    mois: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100)
):
    """
    Récupère le détail des ventes d'un mois spécifique.
    """
    try:
        query = """
        SELECT
            [Date BL] AS Date_BL,
            [N° Pièce] AS Numero_Piece,
            [Code client] AS Code_Client,
            [Intitulé client] AS Nom_Client,
            [Code article] AS Code_Article,
            [Désignation] AS Designation,
            [Catalogue 1] AS Gamme,
            [Représentant] AS Commercial,
            [Quantité] AS Quantite,
            [Montant HT Net] AS Montant_HT,
            [Montant TTC Net] AS Montant_TTC
        FROM [dbo].[DashBoard_CA]
        WHERE YEAR([Date BL]) = ? AND MONTH([Date BL]) = ?
        ORDER BY [Date BL] DESC
        """

        start_time = time.time()
        data = execute_query(query, (annee, mois))
        query_logger.log_query(
            "detail_mois", f"Détail Mois {annee}-{mois}",
            query, time.time() - start_time, len(data)
        )

        # Stats
        ca_total = sum(row.get('Montant_HT', 0) or 0 for row in data)
        nb_clients = len(set(row.get('Code_Client', '') for row in data))

        # Pagination
        total = len(data)
        start = (page - 1) * page_size
        end = start + page_size
        paginated = data[start:end]

        return {
            "success": True,
            "periode": f"{annee}-{str(mois).zfill(2)}",
            "ca_total": round(ca_total, 2),
            "nb_transactions": total,
            "nb_clients": nb_clients,
            "ventes": [
                {
                    "date": row.get('Date_BL'),
                    "numero_piece": row.get('Numero_Piece'),
                    "code_client": row.get('Code_Client', ''),
                    "nom_client": row.get('Nom_Client', ''),
                    "code_article": row.get('Code_Article', ''),
                    "designation": row.get('Designation', ''),
                    "gamme": row.get('Gamme'),
                    "commercial": row.get('Commercial'),
                    "quantite": row.get('Quantite', 0) or 0,
                    "montant_ht": row.get('Montant_HT', 0) or 0,
                    "montant_ttc": row.get('Montant_TTC', 0) or 0
                }
                for row in paginated
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
