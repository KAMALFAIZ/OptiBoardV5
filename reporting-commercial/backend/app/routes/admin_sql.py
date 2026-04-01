"""Admin SQL API routes - Visualisation des requêtes"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional
import time
import re

from ..database_unified import execute_app as execute_query, execute_central
from ..sql.query_templates import (
    CHIFFRE_AFFAIRES_GLOBAL,
    CHIFFRE_AFFAIRES_PAR_PERIODE,
    CHIFFRE_AFFAIRES_PAR_GAMME,
    CHIFFRE_AFFAIRES_PAR_CANAL,
    CHIFFRE_AFFAIRES_PAR_ZONE,
    CHIFFRE_AFFAIRES_PAR_COMMERCIAL,
    TOP_CLIENTS,
    TOP_PRODUITS,
    MOUVEMENTS_STOCK,
    STOCK_PAR_ARTICLE,
    STOCK_DORMANT,
    ROTATION_STOCK,
    BALANCE_AGEE,
    BALANCE_AGEE_PAR_COMMERCIAL,
    TOP_ENCOURS_CLIENTS,
    CREANCES_DOUTEUSES,
    DSO_GLOBAL,
    QUERIES_METADATA
)
from ..services.query_logger import query_logger
from ..config import get_settings

settings = get_settings()
router = APIRouter(prefix="/api/admin", tags=["Admin SQL"])

# Dictionnaire des requêtes disponibles
AVAILABLE_QUERIES = {
    "chiffre_affaires_global": {
        "id": "chiffre_affaires_global",
        "name": "Chiffre d'Affaires Global",
        "description": "Récupère toutes les données de chiffre d'affaires du groupe",
        "sql": CHIFFRE_AFFAIRES_GLOBAL,
        "table": "Chiffre_Affaires_Groupe_Bis",
        "category": "Ventes",
        "params": []
    },
    "chiffre_affaires_par_periode": {
        "id": "chiffre_affaires_par_periode",
        "name": "CA par Période",
        "description": "Analyse du chiffre d'affaires agrégé par mois et année",
        "sql": CHIFFRE_AFFAIRES_PAR_PERIODE,
        "table": "Chiffre_Affaires_Groupe_Bis",
        "category": "Ventes",
        "params": ["date_debut", "date_fin"]
    },
    "chiffre_affaires_par_gamme": {
        "id": "chiffre_affaires_par_gamme",
        "name": "CA par Gamme de Produits",
        "description": "Répartition du CA par gamme (Catalogue 1) avec calcul de marge",
        "sql": CHIFFRE_AFFAIRES_PAR_GAMME,
        "table": "Chiffre_Affaires_Groupe_Bis",
        "category": "Ventes",
        "params": ["date_debut", "date_fin"]
    },
    "chiffre_affaires_par_canal": {
        "id": "chiffre_affaires_par_canal",
        "name": "CA par Canal de Distribution",
        "description": "Répartition du CA par canal (Catégorie_)",
        "sql": CHIFFRE_AFFAIRES_PAR_CANAL,
        "table": "Chiffre_Affaires_Groupe_Bis",
        "category": "Ventes",
        "params": ["date_debut", "date_fin"]
    },
    "chiffre_affaires_par_zone": {
        "id": "chiffre_affaires_par_zone",
        "name": "CA par Zone Géographique",
        "description": "Répartition du CA par zone (Souche)",
        "sql": CHIFFRE_AFFAIRES_PAR_ZONE,
        "table": "Chiffre_Affaires_Groupe_Bis",
        "category": "Ventes",
        "params": ["date_debut", "date_fin"]
    },
    "chiffre_affaires_par_commercial": {
        "id": "chiffre_affaires_par_commercial",
        "name": "CA par Commercial",
        "description": "Performance de chaque commercial (Représentant)",
        "sql": CHIFFRE_AFFAIRES_PAR_COMMERCIAL,
        "table": "Chiffre_Affaires_Groupe_Bis",
        "category": "Ventes",
        "params": ["date_debut", "date_fin"]
    },
    "top_clients": {
        "id": "top_clients",
        "name": "Top 10 Clients",
        "description": "Les 10 meilleurs clients par CA",
        "sql": TOP_CLIENTS,
        "table": "Chiffre_Affaires_Groupe_Bis",
        "category": "Ventes",
        "params": ["date_debut", "date_fin"]
    },
    "top_produits": {
        "id": "top_produits",
        "name": "Top 10 Produits",
        "description": "Les 10 meilleurs produits par CA",
        "sql": TOP_PRODUITS,
        "table": "Chiffre_Affaires_Groupe_Bis",
        "category": "Ventes",
        "params": ["date_debut", "date_fin"]
    },
    "mouvements_stock": {
        "id": "mouvements_stock",
        "name": "Mouvements de Stock",
        "description": "Tous les mouvements de stock (entrées/sorties)",
        "sql": MOUVEMENTS_STOCK,
        "table": "Mouvement_stock",
        "category": "Stocks",
        "params": []
    },
    "stock_par_article": {
        "id": "stock_par_article",
        "name": "Stock par Article",
        "description": "État du stock agrégé par article avec CMUP",
        "sql": STOCK_PAR_ARTICLE,
        "table": "Mouvement_stock",
        "category": "Stocks",
        "params": []
    },
    "stock_dormant": {
        "id": "stock_dormant",
        "name": "Stock Dormant",
        "description": "Articles sans mouvement depuis plus de 180 jours",
        "sql": STOCK_DORMANT,
        "table": "Mouvement_stock",
        "category": "Stocks",
        "params": []
    },
    "rotation_stock": {
        "id": "rotation_stock",
        "name": "Rotation des Stocks",
        "description": "Indicateurs de rotation par gamme de produits",
        "sql": ROTATION_STOCK,
        "table": "Mouvement_stock",
        "category": "Stocks",
        "params": ["date_debut", "date_fin"]
    },
    "balance_agee": {
        "id": "balance_agee",
        "name": "Balance Âgée",
        "description": "Encours clients par tranche d'ancienneté",
        "sql": BALANCE_AGEE,
        "table": "BalanceAgee",
        "category": "Recouvrement",
        "params": []
    },
    "balance_agee_par_commercial": {
        "id": "balance_agee_par_commercial",
        "name": "Balance Âgée par Commercial",
        "description": "Encours agrégé par commercial",
        "sql": BALANCE_AGEE_PAR_COMMERCIAL,
        "table": "BalanceAgee",
        "category": "Recouvrement",
        "params": []
    },
    "top_encours_clients": {
        "id": "top_encours_clients",
        "name": "Top 10 Encours Clients",
        "description": "Les 10 plus gros encours clients",
        "sql": TOP_ENCOURS_CLIENTS,
        "table": "BalanceAgee",
        "category": "Recouvrement",
        "params": []
    },
    "creances_douteuses": {
        "id": "creances_douteuses",
        "name": "Créances Douteuses",
        "description": "Clients avec créances +120 jours ou impayés",
        "sql": CREANCES_DOUTEUSES,
        "table": "BalanceAgee",
        "category": "Recouvrement",
        "params": []
    }
}


@router.get("/queries")
async def get_queries(
    category: Optional[str] = Query(None, description="Filtrer par catégorie")
):
    """
    Liste toutes les requêtes SQL configurées.
    """
    queries = list(AVAILABLE_QUERIES.values())

    if category:
        queries = [q for q in queries if q["category"].lower() == category.lower()]

    # Ajouter les stats de performance
    stats = query_logger.get_stats()
    for q in queries:
        q_stats = stats.get(q["id"], {})
        q["avg_time"] = round(q_stats.get("avg_time", 0), 3)
        q["total_executions"] = q_stats.get("total_executions", 0)
        q["last_execution"] = q_stats.get("last_execution")

    return {
        "success": True,
        "queries": queries,
        "categories": list(set(q["category"] for q in AVAILABLE_QUERIES.values()))
    }


@router.get("/queries/{query_id}")
async def get_query_detail(query_id: str):
    """
    Récupère le détail d'une requête.
    """
    if query_id not in AVAILABLE_QUERIES:
        raise HTTPException(status_code=404, detail="Requête non trouvée")

    query = AVAILABLE_QUERIES[query_id].copy()

    # Ajouter les stats
    stats = query_logger.get_stats(query_id)
    query.update({
        "avg_time": round(stats.get("avg_time", 0), 3),
        "min_time": round(stats.get("min_time", float('inf')) if stats.get("min_time") != float('inf') else 0, 3),
        "max_time": round(stats.get("max_time", 0), 3),
        "total_executions": stats.get("total_executions", 0),
        "total_rows": stats.get("total_rows", 0),
        "errors": stats.get("errors", 0),
        "last_execution": stats.get("last_execution")
    })

    return {"success": True, "query": query}


@router.post("/queries/execute")
async def execute_custom_query(
    query: str = Query(..., description="Requête SQL à exécuter"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre max de lignes")
):
    """
    Exécute une requête SQL personnalisée (lecture seule).
    """
    # Validation: uniquement SELECT
    query_upper = query.strip().upper()
    if not query_upper.startswith("SELECT"):
        raise HTTPException(
            status_code=400,
            detail="Seules les requêtes SELECT sont autorisées"
        )

    # Vérifier les mots-clés dangereux
    forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", "EXEC", "EXECUTE"]
    for word in forbidden:
        if re.search(rf'\b{word}\b', query_upper):
            raise HTTPException(
                status_code=400,
                detail=f"Mot-clé interdit détecté: {word}"
            )

    try:
        # Ajouter TOP si non présent
        if "TOP" not in query_upper:
            query = query.replace("SELECT", f"SELECT TOP {limit}", 1)

        start_time = time.time()
        # Essayer d'abord la base client, puis fallback vers la base centrale
        # (nécessaire pour les tables comme APP_DWH, APP_Users qui sont en central)
        try:
            data = execute_query(query)
        except Exception:
            data = execute_central(query)
        execution_time = time.time() - start_time

        # Log
        query_logger.log_query(
            "custom_query", "Requête Personnalisée",
            query[:200], execution_time, len(data)
        )

        columns = list(data[0].keys()) if data else []

        return {
            "success": True,
            "data": data[:limit],
            "columns": columns,
            "row_count": len(data),
            "execution_time": round(execution_time, 4)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/queries/history")
async def get_query_history(
    limit: int = Query(100, ge=1, le=500),
    query_id: Optional[str] = Query(None)
):
    """
    Récupère l'historique d'exécution des requêtes.
    """
    history = query_logger.get_history(limit, query_id)

    return {
        "success": True,
        "history": history,
        "total": len(history)
    }


@router.get("/queries/stats")
async def get_query_stats():
    """
    Récupère les statistiques globales des requêtes.
    """
    stats = query_logger.get_stats()
    slowest = query_logger.get_slowest_queries(10)

    total_executions = sum(s.get("total_executions", 0) for s in stats.values())
    total_time = sum(s.get("total_time", 0) for s in stats.values())
    avg_time = total_time / total_executions if total_executions > 0 else 0

    return {
        "success": True,
        "summary": {
            "total_executions": total_executions,
            "avg_execution_time": round(avg_time, 4),
            "total_queries": len(stats)
        },
        "by_query": [
            {
                "query_id": k,
                "query_name": AVAILABLE_QUERIES.get(k, {}).get("name", k),
                **v
            }
            for k, v in stats.items()
        ],
        "slowest_queries": slowest
    }


@router.post("/queries/preview/{query_id}")
async def preview_query(
    query_id: str,
    date_debut: Optional[str] = Query("2025-01-01"),
    date_fin: Optional[str] = Query("2025-12-31"),
    limit: int = Query(10, ge=1, le=100)
):
    """
    Prévisualise les résultats d'une requête prédéfinie.
    """
    if query_id not in AVAILABLE_QUERIES:
        raise HTTPException(status_code=404, detail="Requête non trouvée")

    query_info = AVAILABLE_QUERIES[query_id]
    query = query_info["sql"]

    # Ajouter LIMIT si nécessaire
    if "TOP" not in query.upper():
        query = query.replace("SELECT", f"SELECT TOP {limit}", 1)

    try:
        params = None
        if query_info["params"]:
            if "date_debut" in query_info["params"]:
                params = (date_debut, date_fin)

        start_time = time.time()
        if params:
            data = execute_query(query, params)
        else:
            data = execute_query(query)
        execution_time = time.time() - start_time

        columns = list(data[0].keys()) if data else []

        return {
            "success": True,
            "query_id": query_id,
            "query_name": query_info["name"],
            "data": data[:limit],
            "columns": columns,
            "row_count": len(data),
            "execution_time": round(execution_time, 4)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/queries/history")
async def clear_history():
    """
    Efface l'historique des requêtes.
    """
    query_logger.clear_history()
    return {"success": True, "message": "Historique effacé"}


@router.delete("/queries/stats")
async def clear_stats():
    """
    Réinitialise les statistiques des requêtes.
    """
    query_logger.clear_stats()
    return {"success": True, "message": "Statistiques réinitialisées"}
