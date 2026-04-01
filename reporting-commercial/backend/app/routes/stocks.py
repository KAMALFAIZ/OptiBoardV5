"""Stocks API routes"""
from fastapi import APIRouter, Query, HTTPException
from datetime import date
from typing import Optional
import time

from ..database_unified import execute_app as execute_query
from ..sql.query_templates import (
    STOCK_PAR_ARTICLE,
    STOCK_DORMANT,
    ROTATION_STOCK,
    MOUVEMENTS_PAR_ARTICLE
)
from ..services.calculs import get_periode_dates, calculer_couverture_stock, calculer_rotation_stock
from ..services.query_logger import query_logger

router = APIRouter(prefix="/api/stocks", tags=["Stocks"])


@router.get("")
async def get_stocks(
    date_debut: Optional[date] = Query(None),
    date_fin: Optional[date] = Query(None),
    periode: Optional[str] = Query("annee_courante"),
    gamme: Optional[str] = Query(None)
):
    """
    Récupère l'état global des stocks.
    """
    try:
        if not date_debut or not date_fin:
            date_debut_str, date_fin_str = get_periode_dates(periode)
        else:
            date_debut_str = date_debut.strftime("%Y-%m-%d")
            date_fin_str = date_fin.strftime("%Y-%m-%d")

        # Stock par article
        start_time = time.time()
        stock_articles = execute_query(STOCK_PAR_ARTICLE)
        query_logger.log_query(
            "stock_articles", "Stock par Article",
            STOCK_PAR_ARTICLE, time.time() - start_time, len(stock_articles)
        )

        # Stock dormant
        start_time = time.time()
        stock_dormant = execute_query(STOCK_DORMANT)
        query_logger.log_query(
            "stock_dormant", "Stock Dormant",
            STOCK_DORMANT, time.time() - start_time, len(stock_dormant)
        )

        # Rotation par gamme
        start_time = time.time()
        rotation = execute_query(ROTATION_STOCK, (date_debut_str, date_fin_str))
        query_logger.log_query(
            "rotation_stock", "Rotation Stock",
            ROTATION_STOCK, time.time() - start_time, len(rotation)
        )

        # Calculs globaux
        valeur_totale = sum(
            (row.get('Stock_Actuel', 0) or 0) * (row.get('CMUP_Moyen', 0) or 0)
            for row in stock_articles
        )
        nb_articles = len(stock_articles)

        valeur_dormant = sum(row.get('Valeur_Stock', 0) or 0 for row in stock_dormant)
        nb_dormant = len(stock_dormant)

        # Filtrer par gamme si spécifié
        if gamme:
            stock_articles = [s for s in stock_articles if s.get('Gamme') == gamme]
            stock_dormant = [s for s in stock_dormant if s.get('Gamme') == gamme]

        return {
            "success": True,
            "valeur_totale_stock": round(valeur_totale, 2),
            "nb_articles": nb_articles,
            "stock_dormant_valeur": round(valeur_dormant, 2),
            "stock_dormant_nb_articles": nb_dormant,
            "taux_dormant": round(valeur_dormant / valeur_totale * 100, 2) if valeur_totale > 0 else 0,
            "par_article": [
                {
                    "code_article": row.get('Code article', ''),
                    "designation": row.get('Désignation', ''),
                    "gamme": row.get('Gamme'),
                    "entrees": row.get('Entrees', 0) or 0,
                    "sorties": row.get('Sorties', 0) or 0,
                    "stock_actuel": row.get('Stock_Actuel', 0) or 0,
                    "cmup_moyen": row.get('CMUP_Moyen', 0) or 0,
                    "valeur_stock": round(
                        (row.get('Stock_Actuel', 0) or 0) * (row.get('CMUP_Moyen', 0) or 0), 2
                    ),
                    "dernier_mouvement": row.get('Dernier_Mouvement')
                }
                for row in stock_articles[:100]  # Limiter à 100 articles
            ],
            "articles_dormants": [
                {
                    "code_article": row.get('Code article', ''),
                    "designation": row.get('Désignation', ''),
                    "gamme": row.get('Gamme'),
                    "dernier_mouvement": row.get('Dernier_Mouvement'),
                    "jours_sans_mouvement": row.get('Jours_Sans_Mouvement', 0) or 0,
                    "stock_actuel": row.get('Stock_Actuel', 0) or 0,
                    "valeur_stock": row.get('Valeur_Stock', 0) or 0
                }
                for row in stock_dormant
            ],
            "rotation_par_gamme": [
                {
                    "gamme": row.get('Gamme', 'Non défini'),
                    "sorties_valeur": row.get('Sorties_Valeur', 0) or 0,
                    "stock_moyen_valeur": row.get('Stock_Moyen_Valeur', 0) or 0,
                    "rotation": row.get('Rotation', 0) or 0
                }
                for row in rotation
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dormant")
async def get_stock_dormant(
    jours_min: int = Query(180, description="Nombre minimum de jours sans mouvement"),
    gamme: Optional[str] = Query(None)
):
    """
    Récupère la liste des articles dormants.
    """
    try:
        # Modifier la requête pour le seuil de jours
        query = STOCK_DORMANT.replace("> 180", f"> {jours_min}")
        data = execute_query(query)

        if gamme:
            data = [d for d in data if d.get('Gamme') == gamme]

        valeur_totale = sum(row.get('Valeur_Stock', 0) or 0 for row in data)

        result = []
        for row in data:
            result.append({
                "code_article": row.get('Code article', ''),
                "designation": row.get('Désignation', ''),
                "gamme": row.get('Gamme'),
                "dernier_mouvement": row.get('Dernier_Mouvement'),
                "jours_sans_mouvement": row.get('Jours_Sans_Mouvement', 0) or 0,
                "stock_actuel": row.get('Stock_Actuel', 0) or 0,
                "valeur_stock": row.get('Valeur_Stock', 0) or 0
            })

        return {
            "success": True,
            "data": result,
            "valeur_totale": round(valeur_totale, 2),
            "nb_articles": len(result)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rotation")
async def get_rotation_stock(
    date_debut: Optional[date] = Query(None),
    date_fin: Optional[date] = Query(None),
    periode: Optional[str] = Query("annee_courante")
):
    """
    Récupère les indicateurs de rotation des stocks.
    """
    try:
        if not date_debut or not date_fin:
            date_debut_str, date_fin_str = get_periode_dates(periode)
        else:
            date_debut_str = date_debut.strftime("%Y-%m-%d")
            date_fin_str = date_fin.strftime("%Y-%m-%d")

        data = execute_query(ROTATION_STOCK, (date_debut_str, date_fin_str))

        result = []
        for row in data:
            rotation = row.get('Rotation', 0) or 0
            stock_moyen = row.get('Stock_Moyen_Valeur', 0) or 0
            sorties = row.get('Sorties_Valeur', 0) or 0

            # Calculer la couverture en jours
            couverture = round(365 / rotation, 1) if rotation > 0 else 0

            result.append({
                "gamme": row.get('Gamme', 'Non défini'),
                "sorties_valeur": round(sorties, 2),
                "stock_moyen_valeur": round(stock_moyen, 2),
                "rotation": round(rotation, 2),
                "couverture_jours": couverture
            })

        # Rotation globale
        total_sorties = sum(r['sorties_valeur'] for r in result)
        total_stock = sum(r['stock_moyen_valeur'] for r in result)
        rotation_globale = round(total_sorties / total_stock, 2) if total_stock > 0 else 0

        return {
            "success": True,
            "data": result,
            "rotation_globale": rotation_globale,
            "couverture_globale_jours": round(365 / rotation_globale, 1) if rotation_globale > 0 else 0
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/article/{code_article}")
async def get_mouvements_article(
    code_article: str,
    limit: int = Query(100, ge=1, le=1000)
):
    """
    Récupère l'historique des mouvements d'un article.
    """
    try:
        data = execute_query(MOUVEMENTS_PAR_ARTICLE, (code_article,))

        result = []
        for row in data[:limit]:
            result.append({
                "date_mouvement": row.get('Date Mouvement'),
                "type_mouvement": row.get('Type Mouvement', ''),
                "numero_piece": row.get('N° Pièce'),
                "quantite": row.get('Quantité', 0) or 0,
                "sens_mouvement": row.get('Sens de mouvement', ''),
                "cmup": row.get('CMUP', 0) or 0,
                "montant_stock": row.get('Montant Stock', 0) or 0,
                "client": row.get('Intitulé client'),
                "commercial": row.get('Représentant')
            })

        # Calculer le stock actuel
        entrees = sum(
            r['quantite'] for r in result
            if r['sens_mouvement'] == 'E'
        )
        sorties = sum(
            r['quantite'] for r in result
            if r['sens_mouvement'] == 'S'
        )

        return {
            "success": True,
            "code_article": code_article,
            "mouvements": result,
            "total_entrees": entrees,
            "total_sorties": sorties,
            "stock_actuel": entrees - sorties,
            "nb_mouvements": len(result)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/par-gamme")
async def get_stocks_par_gamme():
    """
    Récupère les stocks agrégés par gamme.
    """
    try:
        data = execute_query(STOCK_PAR_ARTICLE)

        # Agréger par gamme
        gammes = {}
        for row in data:
            gamme = row.get('Gamme', 'Non défini') or 'Non défini'
            if gamme not in gammes:
                gammes[gamme] = {
                    "gamme": gamme,
                    "nb_articles": 0,
                    "stock_total": 0,
                    "valeur_totale": 0
                }
            gammes[gamme]["nb_articles"] += 1
            gammes[gamme]["stock_total"] += row.get('Stock_Actuel', 0) or 0
            gammes[gamme]["valeur_totale"] += (
                (row.get('Stock_Actuel', 0) or 0) * (row.get('CMUP_Moyen', 0) or 0)
            )

        result = list(gammes.values())
        for r in result:
            r["valeur_totale"] = round(r["valeur_totale"], 2)

        return {
            "success": True,
            "data": sorted(result, key=lambda x: x['valeur_totale'], reverse=True)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
