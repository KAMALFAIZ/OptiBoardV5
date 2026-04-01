"""Script pour creer les GridViews des rapports Stocks et mettre a jour les menus"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import execute_query, get_db_cursor

GRIDVIEWS = [
    # === Mouvements ===
    {
        "nom": "Mouvements Global",
        "description": "Synthese globale des mouvements de stock",
        "data_source_code": "DS_MVT_STOCK_GLOBAL",
        "menu_code": "DS_MVT_STOCK_GLOBAL",
        "columns": [
            {"field": "Societe", "header": "Societe", "width": 150, "sortable": True, "visible": True},
            {"field": "Nb Mouvements", "header": "Nb Mvt", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Qte Entrees", "header": "Qte Entrees", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Qte Sorties", "header": "Qte Sorties", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Valeur Entrees", "header": "Valeur Entrees", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Valeur Sorties", "header": "Valeur Sorties", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Solde Qte", "header": "Solde Qte", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Solde Valeur", "header": "Solde Valeur", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Solde Valeur", "direction": "desc"},
        "total_columns": ["Qte Entrees", "Qte Sorties", "Valeur Entrees", "Valeur Sorties", "Solde Qte", "Solde Valeur"],
    },
    {
        "nom": "Mouvements par Mois",
        "description": "Mouvements de stock ventiles par mois",
        "data_source_code": "DS_MVT_PAR_MOIS",
        "menu_code": "DS_MVT_PAR_MOIS",
        "columns": [
            {"field": "Mois", "header": "Mois", "width": 100, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 120, "sortable": True, "visible": True},
            {"field": "Nb Mouvements", "header": "Nb Mvt", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Qte Entrees", "header": "Qte Entrees", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Qte Sorties", "header": "Qte Sorties", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Valeur Entrees", "header": "Valeur Entrees", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Valeur Sorties", "header": "Valeur Sorties", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Articles", "header": "Nb Articles", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Mois", "direction": "desc"},
        "total_columns": ["Qte Entrees", "Qte Sorties", "Valeur Entrees", "Valeur Sorties"],
    },
    {
        "nom": "Mouvements par Depot",
        "description": "Mouvements de stock ventiles par depot",
        "data_source_code": "DS_MVT_PAR_DEPOT",
        "menu_code": "DS_MVT_PAR_DEPOT",
        "columns": [
            {"field": "Code Depot", "header": "Code Depot", "width": 100, "sortable": True, "visible": True},
            {"field": "Depot", "header": "Depot", "width": 200, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 120, "sortable": True, "visible": True},
            {"field": "Nb Mouvements", "header": "Nb Mvt", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Qte Entrees", "header": "Qte Entrees", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Qte Sorties", "header": "Qte Sorties", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Valeur Entrees", "header": "Valeur Entrees", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Valeur Sorties", "header": "Valeur Sorties", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Articles", "header": "Nb Articles", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Valeur Sorties", "direction": "desc"},
        "total_columns": ["Qte Entrees", "Qte Sorties", "Valeur Entrees", "Valeur Sorties"],
    },
    {
        "nom": "Mouvements par Famille",
        "description": "Mouvements de stock ventiles par famille d'articles",
        "data_source_code": "DS_MVT_PAR_FAMILLE",
        "menu_code": "DS_MVT_PAR_FAMILLE",
        "columns": [
            {"field": "Code Famille", "header": "Code Famille", "width": 110, "sortable": True, "visible": True},
            {"field": "Famille", "header": "Famille", "width": 200, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 120, "sortable": True, "visible": True},
            {"field": "Nb Mouvements", "header": "Nb Mvt", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Qte Entrees", "header": "Qte Entrees", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Qte Sorties", "header": "Qte Sorties", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Valeur Entrees", "header": "Valeur Entrees", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Valeur Sorties", "header": "Valeur Sorties", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Articles", "header": "Nb Articles", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Valeur Sorties", "direction": "desc"},
        "total_columns": ["Qte Entrees", "Qte Sorties", "Valeur Entrees", "Valeur Sorties"],
    },
    {
        "nom": "Mouvements par Article",
        "description": "Mouvements de stock ventiles par article",
        "data_source_code": "DS_MVT_PAR_ARTICLE",
        "menu_code": "DS_MVT_PAR_ARTICLE",
        "columns": [
            {"field": "Code Article", "header": "Code Article", "width": 130, "sortable": True, "visible": True},
            {"field": "Reference", "header": "Reference", "width": 120, "sortable": True, "visible": True},
            {"field": "Designation", "header": "Designation", "width": 200, "sortable": True, "visible": True},
            {"field": "Famille", "header": "Famille", "width": 120, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 120, "sortable": True, "visible": True},
            {"field": "Qte Entrees", "header": "Qte Entrees", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Qte Sorties", "header": "Qte Sorties", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Solde Qte", "header": "Solde Qte", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "CMUP Moyen", "header": "CMUP Moyen", "width": 110, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Valeur Mvt Total", "header": "Valeur Mvt", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Valeur Mvt Total", "direction": "desc"},
        "total_columns": ["Qte Entrees", "Qte Sorties", "Solde Qte", "Valeur Mvt Total"],
    },
    {
        "nom": "Mouvements par Domaine",
        "description": "Mouvements ventiles par domaine (Ventes, Achats, Stock)",
        "data_source_code": "DS_MVT_PAR_DOMAINE",
        "menu_code": "DS_MVT_PAR_DOMAINE",
        "columns": [
            {"field": "Domaine", "header": "Domaine", "width": 150, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 120, "sortable": True, "visible": True},
            {"field": "Nb Mouvements", "header": "Nb Mvt", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Qte Entrees", "header": "Qte Entrees", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Qte Sorties", "header": "Qte Sorties", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Valeur Entrees", "header": "Valeur Entrees", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Valeur Sorties", "header": "Valeur Sorties", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Articles", "header": "Nb Articles", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Valeur Sorties", "direction": "desc"},
        "total_columns": ["Qte Entrees", "Qte Sorties", "Valeur Entrees", "Valeur Sorties"],
    },
    {
        "nom": "Mouvements par Type Document",
        "description": "Mouvements ventiles par type de document",
        "data_source_code": "DS_MVT_PAR_TYPE",
        "menu_code": "DS_MVT_PAR_TYPE",
        "columns": [
            {"field": "Type Document", "header": "Type Document", "width": 180, "sortable": True, "visible": True},
            {"field": "Domaine", "header": "Domaine", "width": 120, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 120, "sortable": True, "visible": True},
            {"field": "Nb Mouvements", "header": "Nb Mvt", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Qte Totale", "header": "Qte Totale", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Valeur Totale", "header": "Valeur Totale", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Pieces", "header": "Nb Pieces", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Articles", "header": "Nb Articles", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Valeur Totale", "direction": "desc"},
        "total_columns": ["Qte Totale", "Valeur Totale"],
    },
    {
        "nom": "Mouvements par Catalogue",
        "description": "Mouvements ventiles par catalogue",
        "data_source_code": "DS_MVT_CATALOGUE",
        "menu_code": "DS_MVT_CATALOGUE",
        "columns": [
            {"field": "Catalogue", "header": "Catalogue", "width": 200, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 120, "sortable": True, "visible": True},
            {"field": "Nb Mouvements", "header": "Nb Mvt", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Qte Entrees", "header": "Qte Entrees", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Qte Sorties", "header": "Qte Sorties", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Valeur Sorties", "header": "Valeur Sorties", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Articles", "header": "Nb Articles", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Valeur Sorties", "direction": "desc"},
        "total_columns": ["Qte Entrees", "Qte Sorties", "Valeur Sorties"],
    },
    {
        "nom": "Mouvements par Lot/Serie",
        "description": "Mouvements ventiles par lot ou numero de serie",
        "data_source_code": "DS_MVT_PAR_LOT",
        "menu_code": "DS_MVT_PAR_LOT",
        "columns": [
            {"field": "Lot Serie", "header": "Lot/Serie", "width": 130, "sortable": True, "visible": True},
            {"field": "Code Article", "header": "Code Article", "width": 130, "sortable": True, "visible": True},
            {"field": "Designation", "header": "Designation", "width": 200, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 120, "sortable": True, "visible": True},
            {"field": "Nb Mouvements", "header": "Nb Mvt", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Qte Entrees", "header": "Qte Entrees", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Qte Sorties", "header": "Qte Sorties", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Solde Qte", "header": "Solde Qte", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Premier Mvt", "header": "Premier Mvt", "width": 110, "format": "date", "sortable": True, "visible": True},
            {"field": "Dernier Mvt", "header": "Dernier Mvt", "width": 110, "format": "date", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Dernier Mvt", "direction": "desc"},
        "total_columns": ["Qte Entrees", "Qte Sorties", "Solde Qte"],
    },
    {
        "nom": "Detail Complet Mouvements",
        "description": "Detail complet de tous les mouvements de stock",
        "data_source_code": "DS_MVT_DETAIL",
        "menu_code": "DS_MVT_DETAIL",
        "columns": [
            {"field": "Date", "header": "Date", "width": 100, "format": "date", "sortable": True, "visible": True},
            {"field": "Type", "header": "Type Document", "width": 150, "sortable": True, "visible": True},
            {"field": "Domaine", "header": "Domaine", "width": 100, "sortable": True, "visible": True},
            {"field": "Sens", "header": "Sens", "width": 70, "sortable": True, "visible": True},
            {"field": "N Piece", "header": "N Piece", "width": 120, "sortable": True, "visible": True},
            {"field": "Code Article", "header": "Code Article", "width": 130, "sortable": True, "visible": True},
            {"field": "Reference", "header": "Reference", "width": 100, "sortable": True, "visible": True},
            {"field": "Designation", "header": "Designation", "width": 200, "sortable": True, "visible": True},
            {"field": "Famille", "header": "Famille", "width": 120, "sortable": True, "visible": True},
            {"field": "Code Depot", "header": "Code Depot", "width": 80, "sortable": True, "visible": True},
            {"field": "Depot", "header": "Depot", "width": 150, "sortable": True, "visible": True},
            {"field": "Quantite", "header": "Qte", "width": 80, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Prix Unitaire", "header": "PU", "width": 100, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Prix Revient", "header": "Prix Revient", "width": 100, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Valeur Stock", "header": "Valeur", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Lot Serie", "header": "Lot/Serie", "width": 100, "sortable": True, "visible": False},
            {"field": "Societe", "header": "Societe", "width": 100, "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Date", "direction": "desc"},
        "total_columns": ["Quantite", "Valeur Stock"],
    },
    # === Entrees / Sorties ===
    {
        "nom": "Entrees Stock",
        "description": "Detail des entrees en stock",
        "data_source_code": "DS_MVT_ENTREES",
        "menu_code": "DS_MVT_ENTREES",
        "columns": [
            {"field": "Date", "header": "Date", "width": 100, "format": "date", "sortable": True, "visible": True},
            {"field": "Type", "header": "Type Document", "width": 150, "sortable": True, "visible": True},
            {"field": "Domaine", "header": "Domaine", "width": 100, "sortable": True, "visible": True},
            {"field": "N Piece", "header": "N Piece", "width": 120, "sortable": True, "visible": True},
            {"field": "Code Article", "header": "Code Article", "width": 130, "sortable": True, "visible": True},
            {"field": "Designation", "header": "Designation", "width": 200, "sortable": True, "visible": True},
            {"field": "Code Depot", "header": "Code Depot", "width": 80, "sortable": True, "visible": True},
            {"field": "Depot", "header": "Depot", "width": 150, "sortable": True, "visible": True},
            {"field": "Quantite", "header": "Qte", "width": 80, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Prix Unitaire", "header": "PU", "width": 100, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Valeur", "header": "Valeur", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Lot Serie", "header": "Lot/Serie", "width": 100, "sortable": True, "visible": False},
            {"field": "Societe", "header": "Societe", "width": 100, "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Date", "direction": "desc"},
        "total_columns": ["Quantite", "Valeur"],
    },
    {
        "nom": "Sorties Stock",
        "description": "Detail des sorties de stock",
        "data_source_code": "DS_MVT_SORTIES",
        "menu_code": "DS_MVT_SORTIES",
        "columns": [
            {"field": "Date", "header": "Date", "width": 100, "format": "date", "sortable": True, "visible": True},
            {"field": "Type", "header": "Type Document", "width": 150, "sortable": True, "visible": True},
            {"field": "Domaine", "header": "Domaine", "width": 100, "sortable": True, "visible": True},
            {"field": "N Piece", "header": "N Piece", "width": 120, "sortable": True, "visible": True},
            {"field": "Code Article", "header": "Code Article", "width": 130, "sortable": True, "visible": True},
            {"field": "Designation", "header": "Designation", "width": 200, "sortable": True, "visible": True},
            {"field": "Code Depot", "header": "Code Depot", "width": 80, "sortable": True, "visible": True},
            {"field": "Depot", "header": "Depot", "width": 150, "sortable": True, "visible": True},
            {"field": "Quantite", "header": "Qte", "width": 80, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Prix Unitaire", "header": "PU", "width": 100, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Valeur", "header": "Valeur", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Lot Serie", "header": "Lot/Serie", "width": 100, "sortable": True, "visible": False},
            {"field": "Societe", "header": "Societe", "width": 100, "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Date", "direction": "desc"},
        "total_columns": ["Quantite", "Valeur"],
    },
    {
        "nom": "Mouvements Ventes",
        "description": "Mouvements de stock lies aux ventes",
        "data_source_code": "DS_MVT_VENTES",
        "menu_code": "DS_MVT_VENTES",
        "columns": [
            {"field": "Date", "header": "Date", "width": 100, "format": "date", "sortable": True, "visible": True},
            {"field": "Type", "header": "Type Document", "width": 150, "sortable": True, "visible": True},
            {"field": "N Piece", "header": "N Piece", "width": 120, "sortable": True, "visible": True},
            {"field": "Code Article", "header": "Code Article", "width": 130, "sortable": True, "visible": True},
            {"field": "Designation", "header": "Designation", "width": 200, "sortable": True, "visible": True},
            {"field": "Code Depot", "header": "Code Depot", "width": 80, "sortable": True, "visible": True},
            {"field": "Quantite", "header": "Qte", "width": 80, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Prix Vente", "header": "Prix Vente", "width": 110, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Prix Revient", "header": "Prix Revient", "width": 110, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Valeur Stock", "header": "Valeur Stock", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Marge", "header": "Marge", "width": 110, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 100, "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Date", "direction": "desc"},
        "total_columns": ["Quantite", "Valeur Stock", "Marge"],
    },
    {
        "nom": "Mouvements Achats",
        "description": "Mouvements de stock lies aux achats",
        "data_source_code": "DS_MVT_ACHATS",
        "menu_code": "DS_MVT_ACHATS",
        "columns": [
            {"field": "Date", "header": "Date", "width": 100, "format": "date", "sortable": True, "visible": True},
            {"field": "Type", "header": "Type Document", "width": 150, "sortable": True, "visible": True},
            {"field": "N Piece", "header": "N Piece", "width": 120, "sortable": True, "visible": True},
            {"field": "Code Article", "header": "Code Article", "width": 130, "sortable": True, "visible": True},
            {"field": "Designation", "header": "Designation", "width": 200, "sortable": True, "visible": True},
            {"field": "Code Depot", "header": "Code Depot", "width": 80, "sortable": True, "visible": True},
            {"field": "Quantite", "header": "Qte", "width": 80, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Prix Achat", "header": "Prix Achat", "width": 110, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Valeur Stock", "header": "Valeur Stock", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 100, "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Date", "direction": "desc"},
        "total_columns": ["Quantite", "Valeur Stock"],
    },
    {
        "nom": "Mouvements Internes",
        "description": "Mouvements de stock internes (transferts, inventaires)",
        "data_source_code": "DS_MVT_INTERNES",
        "menu_code": "DS_MVT_INTERNES",
        "columns": [
            {"field": "Date", "header": "Date", "width": 100, "format": "date", "sortable": True, "visible": True},
            {"field": "Type", "header": "Type Document", "width": 150, "sortable": True, "visible": True},
            {"field": "N Piece", "header": "N Piece", "width": 120, "sortable": True, "visible": True},
            {"field": "Code Article", "header": "Code Article", "width": 130, "sortable": True, "visible": True},
            {"field": "Designation", "header": "Designation", "width": 200, "sortable": True, "visible": True},
            {"field": "Code Depot", "header": "Code Depot", "width": 80, "sortable": True, "visible": True},
            {"field": "Depot", "header": "Depot", "width": 150, "sortable": True, "visible": True},
            {"field": "Sens", "header": "Sens", "width": 70, "sortable": True, "visible": True},
            {"field": "Quantite", "header": "Qte", "width": 80, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Valeur", "header": "Valeur", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 100, "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Date", "direction": "desc"},
        "total_columns": ["Quantite", "Valeur"],
    },
    # === Situation Stock ===
    {
        "nom": "Stock Actuel par Article",
        "description": "Stock actuel par article et par depot",
        "data_source_code": "DS_STOCK_ACTUEL",
        "menu_code": "DS_STOCK_ACTUEL",
        "columns": [
            {"field": "Code Article", "header": "Code Article", "width": 130, "sortable": True, "visible": True},
            {"field": "Reference", "header": "Reference", "width": 120, "sortable": True, "visible": True},
            {"field": "Designation", "header": "Designation", "width": 200, "sortable": True, "visible": True},
            {"field": "Famille", "header": "Famille", "width": 120, "sortable": True, "visible": True},
            {"field": "Code Depot", "header": "Code Depot", "width": 80, "sortable": True, "visible": True},
            {"field": "Depot", "header": "Depot", "width": 150, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 100, "sortable": True, "visible": True},
            {"field": "Stock Actuel", "header": "Stock Actuel", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Dernier CMUP", "header": "CMUP", "width": 100, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Valeur Stock", "header": "Valeur Stock", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Dernier Mouvement", "header": "Dernier Mvt", "width": 110, "format": "date", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Valeur Stock", "direction": "desc"},
        "total_columns": ["Stock Actuel", "Valeur Stock"],
    },
    {
        "nom": "Stock par Depot",
        "description": "Synthese du stock par depot",
        "data_source_code": "DS_STOCK_PAR_DEPOT",
        "menu_code": "DS_STOCK_PAR_DEPOT",
        "columns": [
            {"field": "Code Depot", "header": "Code Depot", "width": 100, "sortable": True, "visible": True},
            {"field": "Depot", "header": "Depot", "width": 200, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 120, "sortable": True, "visible": True},
            {"field": "Nb Articles", "header": "Nb Articles", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Stock Total Qte", "header": "Stock Total Qte", "width": 130, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Valeur Stock", "header": "Valeur Stock", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Valeur Stock", "direction": "desc"},
        "total_columns": ["Stock Total Qte", "Valeur Stock"],
    },
    {
        "nom": "Top Articles Mouvementes",
        "description": "Classement des articles les plus mouvementes",
        "data_source_code": "DS_TOP_ARTICLES_MVT",
        "menu_code": "DS_TOP_ARTICLES_MVT",
        "columns": [
            {"field": "Code Article", "header": "Code Article", "width": 130, "sortable": True, "visible": True},
            {"field": "Reference", "header": "Reference", "width": 120, "sortable": True, "visible": True},
            {"field": "Designation", "header": "Designation", "width": 200, "sortable": True, "visible": True},
            {"field": "Famille", "header": "Famille", "width": 120, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 100, "sortable": True, "visible": True},
            {"field": "Nb Mouvements", "header": "Nb Mvt", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Qte Sorties", "header": "Qte Sorties", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Valeur Sorties", "header": "Valeur Sorties", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Qte Entrees", "header": "Qte Entrees", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Pieces", "header": "Nb Pieces", "width": 90, "format": "number", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Nb Mouvements", "direction": "desc"},
        "total_columns": ["Qte Sorties", "Valeur Sorties", "Qte Entrees"],
    },
    # === Analyses Stock ===
    {
        "nom": "Rotation des Stocks",
        "description": "Analyse de la rotation des stocks (couverture et taux)",
        "data_source_code": "DS_STOCK_ROTATION",
        "menu_code": "DS_STOCK_ROTATION",
        "columns": [
            {"field": "Code Article", "header": "Code Article", "width": 130, "sortable": True, "visible": True},
            {"field": "Reference", "header": "Reference", "width": 120, "sortable": True, "visible": True},
            {"field": "Designation", "header": "Designation", "width": 200, "sortable": True, "visible": True},
            {"field": "Famille", "header": "Famille", "width": 120, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 100, "sortable": True, "visible": True},
            {"field": "Stock Actuel", "header": "Stock Actuel", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "CMUP", "header": "CMUP", "width": 100, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Valeur Stock", "header": "Valeur Stock", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Sorties 12M", "header": "Sorties 12M", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Couverture Jours", "header": "Couverture (j)", "width": 120, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Taux Rotation", "header": "Taux Rotation", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Valeur Stock", "direction": "desc"},
        "total_columns": ["Stock Actuel", "Valeur Stock", "Sorties 12M"],
    },
    {
        "nom": "Stock Dormant",
        "description": "Articles en stock sans mouvement recent",
        "data_source_code": "DS_STOCK_DORMANT",
        "menu_code": "DS_STOCK_DORMANT",
        "columns": [
            {"field": "Code Article", "header": "Code Article", "width": 130, "sortable": True, "visible": True},
            {"field": "Reference", "header": "Reference", "width": 120, "sortable": True, "visible": True},
            {"field": "Designation", "header": "Designation", "width": 200, "sortable": True, "visible": True},
            {"field": "Famille", "header": "Famille", "width": 120, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 100, "sortable": True, "visible": True},
            {"field": "Stock Qte", "header": "Stock Qte", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "CMUP", "header": "CMUP", "width": 100, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Valeur Stock", "header": "Valeur Stock", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Dernier Mouvement", "header": "Dernier Mvt", "width": 110, "format": "date", "sortable": True, "visible": True},
            {"field": "Jours Sans Mvt", "header": "Jours Sans Mvt", "width": 120, "format": "number", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Jours Sans Mvt", "direction": "desc"},
        "total_columns": ["Stock Qte", "Valeur Stock"],
    },
]


def create_gridviews():
    results = []
    with get_db_cursor() as cursor:
        for gv in GRIDVIEWS:
            columns_json = json.dumps(gv["columns"], ensure_ascii=False)
            default_sort_json = json.dumps(gv["default_sort"])
            total_columns_json = json.dumps(gv["total_columns"])
            features_json = json.dumps({
                "show_search": True, "show_column_filters": True,
                "show_grouping": True, "show_column_toggle": True,
                "show_export": True, "show_pagination": True,
                "show_page_size": True, "allow_sorting": True,
            })

            cursor.execute("""
                INSERT INTO APP_GridViews
                    (nom, description, columns_config, features, actif, data_source_code,
                     default_sort, page_size, show_totals, total_columns, is_public, created_by)
                VALUES (?, ?, ?, ?, 1, ?, ?, ?, 1, ?, 1, 1)
            """, (
                gv["nom"], gv["description"], columns_json, features_json,
                gv["data_source_code"], default_sort_json,
                gv.get("page_size", 50), total_columns_json,
            ))

            cursor.execute("SELECT @@IDENTITY AS id")
            new_id = int(cursor.fetchone()[0])

            cursor.execute(
                "UPDATE APP_Menus SET target_id = ? WHERE code = ? AND type = 'gridview'",
                (new_id, gv["menu_code"])
            )
            menu_updated = cursor.rowcount

            results.append({"nom": gv["nom"], "id": new_id, "menu_code": gv["menu_code"], "menu_ok": menu_updated})
            print(f"  OK: {gv['nom']} (GV ID={new_id}, menu={menu_updated})")
    return results


if __name__ == "__main__":
    print(f"Creation de {len(GRIDVIEWS)} GridViews Stocks...")
    print()
    results = create_gridviews()
    print()
    ok = sum(1 for r in results if r["menu_ok"] > 0)
    print(f"Termine: {len(results)} GridViews, {ok}/{len(results)} menus OK")
    if ok < len(results):
        for r in results:
            if r["menu_ok"] == 0:
                print(f"  ATTENTION menu non trouve: {r['menu_code']}")
