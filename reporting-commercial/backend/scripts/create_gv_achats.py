"""Script pour creer les GridViews des rapports Achats et mettre a jour les menus"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import execute_query, get_db_cursor

# ==============================================================================
# DEFINITIONS DES GRIDVIEWS ACHATS
# ==============================================================================

GRIDVIEWS = [
    # --- Synthese Achats ---
    {
        "nom": "Achats Global",
        "description": "Synthese globale des achats par societe",
        "data_source_code": "DS_ACHATS_GLOBAL",
        "menu_code": "DS_ACHATS_GLOBAL",
        "columns": [
            {"field": "Societe", "header": "Societe", "width": 150, "sortable": True, "visible": True},
            {"field": "Achats HT", "header": "Achats HT", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Achats TTC", "header": "Achats TTC", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Fournisseurs", "header": "Nb Fournisseurs", "width": 120, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Documents", "header": "Nb Documents", "width": 120, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Qte Totale", "header": "Qte Totale", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Lignes", "header": "Nb Lignes", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Achats HT", "direction": "desc"},
        "total_columns": ["Achats HT", "Achats TTC", "Qte Totale", "Nb Lignes"],
        "page_size": 50,
    },
    {
        "nom": "Achats par Mois",
        "description": "Achats ventiles par mois",
        "data_source_code": "DS_ACHATS_PAR_MOIS",
        "menu_code": "DS_ACHATS_PAR_MOIS",
        "columns": [
            {"field": "Mois", "header": "Mois", "width": 100, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 150, "sortable": True, "visible": True},
            {"field": "Achats HT", "header": "Achats HT", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Achats TTC", "header": "Achats TTC", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Fournisseurs", "header": "Nb Fournisseurs", "width": 120, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Documents", "header": "Nb Documents", "width": 120, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Qte Totale", "header": "Qte Totale", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Mois", "direction": "desc"},
        "total_columns": ["Achats HT", "Achats TTC", "Qte Totale"],
        "page_size": 50,
    },
    {
        "nom": "Achats par Fournisseur",
        "description": "Achats ventiles par fournisseur",
        "data_source_code": "DS_ACHATS_PAR_FOURNISSEUR",
        "menu_code": "DS_ACHATS_PAR_FOURNISSEUR",
        "columns": [
            {"field": "Code Fournisseur", "header": "Code Fournisseur", "width": 130, "sortable": True, "visible": True},
            {"field": "Fournisseur", "header": "Fournisseur", "width": 200, "sortable": True, "visible": True},
            {"field": "Qualite", "header": "Qualite", "width": 100, "sortable": True, "visible": True},
            {"field": "Categorie Tarifaire", "header": "Cat. Tarifaire", "width": 120, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 120, "sortable": True, "visible": True},
            {"field": "Achats HT", "header": "Achats HT", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Achats TTC", "header": "Achats TTC", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Documents", "header": "Nb Documents", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Qte Totale", "header": "Qte Totale", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Articles", "header": "Nb Articles", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Achats HT", "direction": "desc"},
        "total_columns": ["Achats HT", "Achats TTC", "Qte Totale"],
        "page_size": 50,
    },
    {
        "nom": "Achats par Article",
        "description": "Achats ventiles par article",
        "data_source_code": "DS_ACHATS_PAR_ARTICLE",
        "menu_code": "DS_ACHATS_PAR_ARTICLE",
        "columns": [
            {"field": "Code Article", "header": "Code Article", "width": 130, "sortable": True, "visible": True},
            {"field": "Designation", "header": "Designation", "width": 200, "sortable": True, "visible": True},
            {"field": "Famille", "header": "Famille", "width": 120, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 120, "sortable": True, "visible": True},
            {"field": "Qte Achetee", "header": "Qte Achetee", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Achats HT", "header": "Achats HT", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Prix Moyen", "header": "Prix Moyen", "width": 110, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "CMUP Moyen", "header": "CMUP Moyen", "width": 110, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Fournisseurs", "header": "Nb Fourn.", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Documents", "header": "Nb Documents", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Achats HT", "direction": "desc"},
        "total_columns": ["Achats HT", "Qte Achetee"],
        "page_size": 50,
    },
    {
        "nom": "Achats par Famille",
        "description": "Achats ventiles par famille d'articles",
        "data_source_code": "DS_ACHATS_PAR_FAMILLE",
        "menu_code": "DS_ACHATS_PAR_FAMILLE",
        "columns": [
            {"field": "Famille", "header": "Famille", "width": 200, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 120, "sortable": True, "visible": True},
            {"field": "Qte Achetee", "header": "Qte Achetee", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Achats HT", "header": "Achats HT", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Achats TTC", "header": "Achats TTC", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Articles", "header": "Nb Articles", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Fournisseurs", "header": "Nb Fourn.", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Achats HT", "direction": "desc"},
        "total_columns": ["Achats HT", "Achats TTC", "Qte Achetee"],
        "page_size": 50,
    },
    {
        "nom": "Achats par Catalogue",
        "description": "Achats ventiles par catalogue",
        "data_source_code": "DS_ACHATS_PAR_CATALOGUE",
        "menu_code": "DS_ACHATS_PAR_CATALOGUE",
        "columns": [
            {"field": "Catalogue", "header": "Catalogue", "width": 200, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 120, "sortable": True, "visible": True},
            {"field": "Achats HT", "header": "Achats HT", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Qte Achetee", "header": "Qte Achetee", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Articles", "header": "Nb Articles", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Fournisseurs", "header": "Nb Fourn.", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Achats HT", "direction": "desc"},
        "total_columns": ["Achats HT", "Qte Achetee"],
        "page_size": 50,
    },
    {
        "nom": "Achats par Type Document",
        "description": "Achats ventiles par type de document",
        "data_source_code": "DS_ACHATS_PAR_TYPE_DOC",
        "menu_code": "DS_ACHATS_PAR_TYPE_DOC",
        "columns": [
            {"field": "Type Document", "header": "Type Document", "width": 180, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 120, "sortable": True, "visible": True},
            {"field": "Nb Documents", "header": "Nb Documents", "width": 120, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Qte Totale", "header": "Qte Totale", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Montant HT", "header": "Montant HT", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Montant TTC", "header": "Montant TTC", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Fournisseurs", "header": "Nb Fourn.", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Articles", "header": "Nb Articles", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Montant HT", "direction": "desc"},
        "total_columns": ["Montant HT", "Montant TTC", "Qte Totale"],
        "page_size": 50,
    },
    {
        "nom": "Achats par Affaire",
        "description": "Achats ventiles par code affaire",
        "data_source_code": "DS_ACHATS_PAR_AFFAIRE",
        "menu_code": "DS_ACHATS_PAR_AFFAIRE",
        "columns": [
            {"field": "Code Affaire", "header": "Code Affaire", "width": 120, "sortable": True, "visible": True},
            {"field": "Affaire", "header": "Affaire", "width": 200, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 120, "sortable": True, "visible": True},
            {"field": "Achats HT", "header": "Achats HT", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Achats TTC", "header": "Achats TTC", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Fournisseurs", "header": "Nb Fourn.", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Articles", "header": "Nb Articles", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Documents", "header": "Nb Documents", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Achats HT", "direction": "desc"},
        "total_columns": ["Achats HT", "Achats TTC"],
        "page_size": 50,
    },
    {
        "nom": "Achats par Acheteur",
        "description": "Achats ventiles par acheteur",
        "data_source_code": "DS_ACHATS_PAR_ACHETEUR",
        "menu_code": "DS_ACHATS_PAR_ACHETEUR",
        "columns": [
            {"field": "Acheteur", "header": "Acheteur", "width": 200, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 120, "sortable": True, "visible": True},
            {"field": "Achats HT", "header": "Achats HT", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Achats TTC", "header": "Achats TTC", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Fournisseurs", "header": "Nb Fourn.", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Documents", "header": "Nb Documents", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Articles", "header": "Nb Articles", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Achats HT", "direction": "desc"},
        "total_columns": ["Achats HT", "Achats TTC"],
        "page_size": 50,
    },
    # --- Documents Achats ---
    {
        "nom": "Factures Achats",
        "description": "Detail des factures d'achats",
        "data_source_code": "DS_FACTURES_ACHATS",
        "menu_code": "DS_FACTURES_ACHATS",
        "columns": [
            {"field": "Societe", "header": "Societe", "width": 100, "sortable": True, "visible": True},
            {"field": "N Piece", "header": "N Piece", "width": 120, "sortable": True, "visible": True},
            {"field": "Date", "header": "Date", "width": 100, "format": "date", "sortable": True, "visible": True},
            {"field": "Code Fournisseur", "header": "Code Fourn.", "width": 110, "sortable": True, "visible": True},
            {"field": "Fournisseur", "header": "Fournisseur", "width": 200, "sortable": True, "visible": True},
            {"field": "Code Article", "header": "Code Article", "width": 120, "sortable": True, "visible": True},
            {"field": "Designation", "header": "Designation", "width": 200, "sortable": True, "visible": True},
            {"field": "Quantite", "header": "Qte", "width": 80, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Prix Unitaire", "header": "PU HT", "width": 100, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Montant HT", "header": "Montant HT", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Montant TTC", "header": "Montant TTC", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Frais Approche", "header": "Frais Approche", "width": 110, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "CMUP", "header": "CMUP", "width": 100, "format": "currency", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Date", "direction": "desc"},
        "total_columns": ["Montant HT", "Montant TTC", "Quantite"],
        "page_size": 50,
    },
    {
        "nom": "Bons de Reception",
        "description": "Detail des bons de reception",
        "data_source_code": "DS_BONS_RECEPTION",
        "menu_code": "DS_BONS_RECEPTION",
        "columns": [
            {"field": "Societe", "header": "Societe", "width": 100, "sortable": True, "visible": True},
            {"field": "N Piece", "header": "N Piece", "width": 120, "sortable": True, "visible": True},
            {"field": "Date", "header": "Date", "width": 100, "format": "date", "sortable": True, "visible": True},
            {"field": "Code Fournisseur", "header": "Code Fourn.", "width": 110, "sortable": True, "visible": True},
            {"field": "Fournisseur", "header": "Fournisseur", "width": 200, "sortable": True, "visible": True},
            {"field": "Code Article", "header": "Code Article", "width": 120, "sortable": True, "visible": True},
            {"field": "Designation", "header": "Designation", "width": 200, "sortable": True, "visible": True},
            {"field": "Quantite", "header": "Qte", "width": 80, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Prix Unitaire", "header": "PU HT", "width": 100, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Montant HT", "header": "Montant HT", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "N BC", "header": "N BC", "width": 120, "sortable": True, "visible": True},
            {"field": "Date BC", "header": "Date BC", "width": 100, "format": "date", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Date", "direction": "desc"},
        "total_columns": ["Montant HT", "Quantite"],
        "page_size": 50,
    },
    {
        "nom": "Commandes Achats",
        "description": "Detail des bons de commande achats",
        "data_source_code": "DS_COMMANDES_ACHATS",
        "menu_code": "DS_COMMANDES_ACHATS",
        "columns": [
            {"field": "Societe", "header": "Societe", "width": 100, "sortable": True, "visible": True},
            {"field": "N Piece", "header": "N Piece", "width": 120, "sortable": True, "visible": True},
            {"field": "Date", "header": "Date", "width": 100, "format": "date", "sortable": True, "visible": True},
            {"field": "Code Fournisseur", "header": "Code Fourn.", "width": 110, "sortable": True, "visible": True},
            {"field": "Fournisseur", "header": "Fournisseur", "width": 200, "sortable": True, "visible": True},
            {"field": "Code Article", "header": "Code Article", "width": 120, "sortable": True, "visible": True},
            {"field": "Designation", "header": "Designation", "width": 200, "sortable": True, "visible": True},
            {"field": "Quantite", "header": "Qte", "width": 80, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Prix Unitaire", "header": "PU HT", "width": 100, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Montant HT", "header": "Montant HT", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Date Livraison Prevue", "header": "Date Livraison", "width": 120, "format": "date", "sortable": True, "visible": True},
            {"field": "Cloture", "header": "Cloture", "width": 80, "sortable": True, "visible": True},
            {"field": "Statut", "header": "Statut", "width": 100, "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Date", "direction": "desc"},
        "total_columns": ["Montant HT", "Quantite"],
        "page_size": 50,
    },
    {
        "nom": "Avoirs Achats",
        "description": "Detail des avoirs achats",
        "data_source_code": "DS_AVOIRS_ACHATS",
        "menu_code": "DS_AVOIRS_ACHATS",
        "columns": [
            {"field": "Societe", "header": "Societe", "width": 100, "sortable": True, "visible": True},
            {"field": "N Piece", "header": "N Piece", "width": 120, "sortable": True, "visible": True},
            {"field": "Date", "header": "Date", "width": 100, "format": "date", "sortable": True, "visible": True},
            {"field": "Code Fournisseur", "header": "Code Fourn.", "width": 110, "sortable": True, "visible": True},
            {"field": "Fournisseur", "header": "Fournisseur", "width": 200, "sortable": True, "visible": True},
            {"field": "Code Article", "header": "Code Article", "width": 120, "sortable": True, "visible": True},
            {"field": "Designation", "header": "Designation", "width": 200, "sortable": True, "visible": True},
            {"field": "Quantite", "header": "Qte", "width": 80, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Montant HT", "header": "Montant HT", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Montant TTC", "header": "Montant TTC", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Date", "direction": "desc"},
        "total_columns": ["Montant HT", "Montant TTC", "Quantite"],
        "page_size": 50,
    },
    {
        "nom": "Achats Detail Complet",
        "description": "Detail complet de toutes les lignes d'achats",
        "data_source_code": "DS_ACHATS_DETAIL",
        "menu_code": "DS_ACHATS_DETAIL",
        "columns": [
            {"field": "Societe", "header": "Societe", "width": 100, "sortable": True, "visible": True},
            {"field": "Code Fournisseur", "header": "Code Fourn.", "width": 110, "sortable": True, "visible": True},
            {"field": "Fournisseur", "header": "Fournisseur", "width": 180, "sortable": True, "visible": True},
            {"field": "N Piece", "header": "N Piece", "width": 120, "sortable": True, "visible": True},
            {"field": "Reference", "header": "Reference", "width": 120, "sortable": True, "visible": True},
            {"field": "Code Affaire", "header": "Code Affaire", "width": 100, "sortable": True, "visible": True},
            {"field": "Affaire", "header": "Affaire", "width": 150, "sortable": True, "visible": True},
            {"field": "Code Article", "header": "Code Article", "width": 120, "sortable": True, "visible": True},
            {"field": "Designation", "header": "Designation", "width": 200, "sortable": True, "visible": True},
            {"field": "Quantite", "header": "Qte", "width": 80, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Prix Unitaire", "header": "PU HT", "width": 100, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Prix TTC", "header": "PU TTC", "width": 100, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Montant HT", "header": "Montant HT", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Montant TTC", "header": "Montant TTC", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Prix Revient", "header": "Prix Revient", "width": 100, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Frais Approche", "header": "Frais Approche", "width": 110, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "N BL", "header": "N BL", "width": 100, "sortable": True, "visible": False},
            {"field": "N BC", "header": "N BC", "width": 100, "sortable": True, "visible": False},
            {"field": "N PL", "header": "N PL", "width": 100, "sortable": True, "visible": False},
            {"field": "Lot Serie", "header": "Lot/Serie", "width": 100, "sortable": True, "visible": False},
            {"field": "Poids Brut", "header": "Poids Brut", "width": 90, "format": "number", "align": "right", "sortable": True, "visible": False},
            {"field": "Poids Net", "header": "Poids Net", "width": 90, "format": "number", "align": "right", "sortable": True, "visible": False},
            {"field": "Qualite Fournisseur", "header": "Qualite", "width": 100, "sortable": True, "visible": False},
            {"field": "Cloture", "header": "Cloture", "width": 80, "sortable": True, "visible": False},
            {"field": "Montant Regle", "header": "Montant Regle", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": False},
        ],
        "default_sort": {"field": "N Piece", "direction": "desc"},
        "total_columns": ["Montant HT", "Montant TTC", "Quantite"],
        "page_size": 50,
    },
    # --- Analyses Achats ---
    {
        "nom": "Commandes Achats en Cours",
        "description": "Commandes achats non soldees",
        "data_source_code": "DS_COMMANDES_ACHATS_EN_COURS",
        "menu_code": "DS_COMMANDES_ACHATS_EN_COURS",
        "columns": [
            {"field": "Societe", "header": "Societe", "width": 100, "sortable": True, "visible": True},
            {"field": "N Piece", "header": "N Piece", "width": 120, "sortable": True, "visible": True},
            {"field": "Code Fournisseur", "header": "Code Fourn.", "width": 110, "sortable": True, "visible": True},
            {"field": "Fournisseur", "header": "Fournisseur", "width": 200, "sortable": True, "visible": True},
            {"field": "Code Article", "header": "Code Article", "width": 120, "sortable": True, "visible": True},
            {"field": "Designation", "header": "Designation", "width": 200, "sortable": True, "visible": True},
            {"field": "Qte Commandee", "header": "Qte Cmd", "width": 90, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Prix Unitaire", "header": "PU HT", "width": 100, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Montant HT", "header": "Montant HT", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Date Livraison Prevue", "header": "Date Livraison", "width": 120, "format": "date", "sortable": True, "visible": True},
            {"field": "Age Jours", "header": "Age (j)", "width": 80, "format": "number", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Age Jours", "direction": "desc"},
        "total_columns": ["Montant HT", "Qte Commandee"],
        "page_size": 50,
    },
    {
        "nom": "Top Fournisseurs",
        "description": "Classement des fournisseurs par volume d'achats",
        "data_source_code": "DS_TOP_FOURNISSEURS",
        "menu_code": "DS_TOP_FOURNISSEURS",
        "columns": [
            {"field": "Code Fournisseur", "header": "Code Fourn.", "width": 110, "sortable": True, "visible": True},
            {"field": "Fournisseur", "header": "Fournisseur", "width": 200, "sortable": True, "visible": True},
            {"field": "Qualite", "header": "Qualite", "width": 100, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 120, "sortable": True, "visible": True},
            {"field": "Achats HT", "header": "Achats HT", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Factures", "header": "Nb Factures", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Articles", "header": "Nb Articles", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Qte Totale", "header": "Qte Totale", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Achats HT", "direction": "desc"},
        "total_columns": ["Achats HT", "Qte Totale"],
        "page_size": 50,
    },
    {
        "nom": "Top Articles Achetes",
        "description": "Classement des articles par volume d'achats",
        "data_source_code": "DS_TOP_ARTICLES_ACHATS",
        "menu_code": "DS_TOP_ARTICLES_ACHATS",
        "columns": [
            {"field": "Code Article", "header": "Code Article", "width": 130, "sortable": True, "visible": True},
            {"field": "Designation", "header": "Designation", "width": 200, "sortable": True, "visible": True},
            {"field": "Famille", "header": "Famille", "width": 120, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 120, "sortable": True, "visible": True},
            {"field": "Qte Achetee", "header": "Qte Achetee", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Achats HT", "header": "Achats HT", "width": 130, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Prix Moyen", "header": "Prix Moyen", "width": 110, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Fournisseurs", "header": "Nb Fourn.", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Achats HT", "direction": "desc"},
        "total_columns": ["Achats HT", "Qte Achetee"],
        "page_size": 50,
    },
    {
        "nom": "Evolution Prix Achats",
        "description": "Evolution des prix d'achat par article et par mois",
        "data_source_code": "DS_EVOLUTION_PRIX_ACHATS",
        "menu_code": "DS_EVOLUTION_PRIX_ACHATS",
        "columns": [
            {"field": "Code Article", "header": "Code Article", "width": 130, "sortable": True, "visible": True},
            {"field": "Designation", "header": "Designation", "width": 200, "sortable": True, "visible": True},
            {"field": "Mois", "header": "Mois", "width": 100, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 120, "sortable": True, "visible": True},
            {"field": "Prix Moyen", "header": "Prix Moyen", "width": 110, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Prix Min", "header": "Prix Min", "width": 100, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Prix Max", "header": "Prix Max", "width": 100, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Qte Achetee", "header": "Qte Achetee", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Fournisseurs", "header": "Nb Fourn.", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Mois", "direction": "desc"},
        "total_columns": ["Qte Achetee"],
        "page_size": 50,
    },
    {
        "nom": "Comparaison Fournisseurs",
        "description": "Comparaison des prix entre fournisseurs par article",
        "data_source_code": "DS_COMPARAISON_FOURNISSEURS",
        "menu_code": "DS_COMPARAISON_FOURNISSEURS",
        "columns": [
            {"field": "Code Article", "header": "Code Article", "width": 130, "sortable": True, "visible": True},
            {"field": "Designation", "header": "Designation", "width": 200, "sortable": True, "visible": True},
            {"field": "Code Fournisseur", "header": "Code Fourn.", "width": 110, "sortable": True, "visible": True},
            {"field": "Fournisseur", "header": "Fournisseur", "width": 200, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 120, "sortable": True, "visible": True},
            {"field": "Prix Moyen", "header": "Prix Moyen", "width": 110, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Prix Min", "header": "Prix Min", "width": 100, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Prix Max", "header": "Prix Max", "width": 100, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Qte Achetee", "header": "Qte Achetee", "width": 110, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Commandes", "header": "Nb Cmd", "width": 90, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Dernier Achat", "header": "Dernier Achat", "width": 120, "format": "date", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Code Article", "direction": "asc"},
        "total_columns": ["Qte Achetee"],
        "page_size": 50,
    },
]


def create_gridviews():
    """Cree les GridViews et met a jour les menus"""
    results = []

    with get_db_cursor() as cursor:
        for gv in GRIDVIEWS:
            columns_json = json.dumps(gv["columns"], ensure_ascii=False)
            default_sort_json = json.dumps(gv["default_sort"])
            total_columns_json = json.dumps(gv["total_columns"])
            features_json = json.dumps({
                "show_search": True,
                "show_column_filters": True,
                "show_grouping": True,
                "show_column_toggle": True,
                "show_export": True,
                "show_pagination": True,
                "show_page_size": True,
                "allow_sorting": True,
            })

            cursor.execute("""
                INSERT INTO APP_GridViews
                    (nom, description, columns_config, features, actif, data_source_code,
                     default_sort, page_size, show_totals, total_columns, is_public, created_by)
                VALUES (?, ?, ?, ?, 1, ?, ?, ?, 1, ?, 1, 1)
            """, (
                gv["nom"],
                gv["description"],
                columns_json,
                features_json,
                gv["data_source_code"],
                default_sort_json,
                gv["page_size"],
                total_columns_json,
            ))

            cursor.execute("SELECT @@IDENTITY AS id")
            new_id = cursor.fetchone()[0]
            new_id = int(new_id)

            # Update the menu target_id
            cursor.execute(
                "UPDATE APP_Menus SET target_id = ? WHERE code = ? AND type = 'gridview'",
                (new_id, gv["menu_code"])
            )
            menu_updated = cursor.rowcount

            results.append({
                "nom": gv["nom"],
                "gridview_id": new_id,
                "menu_code": gv["menu_code"],
                "menu_updated": menu_updated,
            })
            print(f"  OK: {gv['nom']} (GV ID={new_id}, menu_updated={menu_updated})")

    return results


if __name__ == "__main__":
    print(f"Creation de {len(GRIDVIEWS)} GridViews Achats...")
    print()
    results = create_gridviews()
    print()
    print(f"Termine: {len(results)} GridViews creees")
    print()

    # Verification
    ok = sum(1 for r in results if r["menu_updated"] > 0)
    fail = sum(1 for r in results if r["menu_updated"] == 0)
    print(f"Menus mis a jour: {ok}/{len(results)}")
    if fail > 0:
        print(f"ATTENTION: {fail} menus non trouves:")
        for r in results:
            if r["menu_updated"] == 0:
                print(f"  - {r['menu_code']}")
