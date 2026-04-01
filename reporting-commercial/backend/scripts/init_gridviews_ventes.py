"""
Script pour creer les GridViews manquants pour les rapports de ventes
====================================================================
Les menus existent deja mais pointent vers des GridViews inexistants.
Ce script cree les GridViews et met a jour les target_id des menus.

Execution: python scripts/init_gridviews_ventes.py
"""

import sys
import os
import json

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import execute_query, get_db_cursor


# =============================================================================
# DEFINITION DES GRIDVIEWS A CREER
# =============================================================================

GRIDVIEWS = [
    # === Documents des Ventes ===
    {
        "nom": "Factures",
        "description": "Liste des factures de vente",
        "data_source_code": "DS_FACTURES",
        "menu_code": "DS_FACTURES",
        "columns": [
            {"field": "Societe", "header": "Societe", "width": 100, "sortable": True, "visible": True},
            {"field": "Num Facture", "header": "N Facture", "width": 120, "sortable": True, "visible": True},
            {"field": "Date Facture", "header": "Date", "width": 100, "format": "date", "sortable": True, "visible": True},
            {"field": "Code Client", "header": "Code Client", "width": 100, "sortable": True, "visible": True},
            {"field": "Client", "header": "Client", "width": 200, "sortable": True, "visible": True},
            {"field": "Code Article", "header": "Code Article", "width": 120, "sortable": True, "visible": True},
            {"field": "Designation", "header": "Designation", "width": 200, "sortable": True, "visible": True},
            {"field": "Qte", "header": "Qte", "width": 80, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "PU HT", "header": "PU HT", "width": 100, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Montant HT", "header": "Montant HT", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Montant TTC", "header": "Montant TTC", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Marge", "header": "Marge", "width": 100, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Code Affaire", "header": "Code Affaire", "width": 100, "sortable": True, "visible": False},
            {"field": "Affaire", "header": "Affaire", "width": 150, "sortable": True, "visible": False},
        ],
        "default_sort": {"field": "Date Facture", "direction": "desc"},
        "page_size": 50,
        "show_totals": True,
        "total_columns": ["Montant HT", "Montant TTC", "Marge", "Qte"],
    },
    {
        "nom": "Bons de Livraison",
        "description": "Liste des bons de livraison",
        "data_source_code": "DS_BONS_LIVRAISON",
        "menu_code": "DS_BONS_LIVRAISON",
        "columns": [
            {"field": "Societe", "header": "Societe", "width": 100, "sortable": True, "visible": True},
            {"field": "Num BL", "header": "N BL", "width": 120, "sortable": True, "visible": True},
            {"field": "Date BL", "header": "Date BL", "width": 100, "format": "date", "sortable": True, "visible": True},
            {"field": "Num BC", "header": "N BC", "width": 120, "sortable": True, "visible": True},
            {"field": "Date BC", "header": "Date BC", "width": 100, "format": "date", "sortable": True, "visible": True},
            {"field": "Code Client", "header": "Code Client", "width": 100, "sortable": True, "visible": True},
            {"field": "Client", "header": "Client", "width": 200, "sortable": True, "visible": True},
            {"field": "Code Article", "header": "Code Article", "width": 120, "sortable": True, "visible": True},
            {"field": "Designation", "header": "Designation", "width": 200, "sortable": True, "visible": True},
            {"field": "Qte BL", "header": "Qte BL", "width": 80, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Montant HT", "header": "Montant HT", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Code Depot", "header": "Code Depot", "width": 100, "sortable": True, "visible": True},
            {"field": "Depot", "header": "Depot", "width": 150, "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Date BL", "direction": "desc"},
        "page_size": 50,
        "show_totals": True,
        "total_columns": ["Montant HT", "Qte BL"],
    },
    {
        "nom": "Bons de Commande",
        "description": "Liste des bons de commande clients",
        "data_source_code": "DS_BONS_COMMANDE",
        "menu_code": "DS_BONS_COMMANDE",
        "columns": [
            {"field": "Societe", "header": "Societe", "width": 100, "sortable": True, "visible": True},
            {"field": "Num BC", "header": "N BC", "width": 120, "sortable": True, "visible": True},
            {"field": "Date BC", "header": "Date BC", "width": 100, "format": "date", "sortable": True, "visible": True},
            {"field": "Code Client", "header": "Code Client", "width": 100, "sortable": True, "visible": True},
            {"field": "Client", "header": "Client", "width": 200, "sortable": True, "visible": True},
            {"field": "Code Article", "header": "Code Article", "width": 120, "sortable": True, "visible": True},
            {"field": "Designation", "header": "Designation", "width": 200, "sortable": True, "visible": True},
            {"field": "Qte Commandee", "header": "Qte Cmd", "width": 80, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Qte Livree", "header": "Qte Livree", "width": 80, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Reste A Livrer", "header": "Reste", "width": 80, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "PU HT", "header": "PU HT", "width": 100, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Montant HT", "header": "Montant HT", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Date Livraison Prevue", "header": "Livraison Prevue", "width": 120, "format": "date", "sortable": True, "visible": True},
            {"field": "Code Affaire", "header": "Code Affaire", "width": 100, "sortable": True, "visible": False},
        ],
        "default_sort": {"field": "Date BC", "direction": "desc"},
        "page_size": 50,
        "show_totals": True,
        "total_columns": ["Montant HT", "Qte Commandee", "Qte Livree", "Reste A Livrer"],
    },
    {
        "nom": "Devis",
        "description": "Liste des devis",
        "data_source_code": "DS_DEVIS",
        "menu_code": "DS_DEVIS",
        "columns": [
            {"field": "Societe", "header": "Societe", "width": 100, "sortable": True, "visible": True},
            {"field": "Num Devis", "header": "N Devis", "width": 120, "sortable": True, "visible": True},
            {"field": "Date Devis", "header": "Date", "width": 100, "format": "date", "sortable": True, "visible": True},
            {"field": "Code Client", "header": "Code Client", "width": 100, "sortable": True, "visible": True},
            {"field": "Client", "header": "Client", "width": 200, "sortable": True, "visible": True},
            {"field": "Code Article", "header": "Code Article", "width": 120, "sortable": True, "visible": True},
            {"field": "Designation", "header": "Designation", "width": 200, "sortable": True, "visible": True},
            {"field": "Qte", "header": "Qte", "width": 80, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "PU HT", "header": "PU HT", "width": 100, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Montant HT", "header": "Montant HT", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Montant TTC", "header": "Montant TTC", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Code Affaire", "header": "Code Affaire", "width": 100, "sortable": True, "visible": False},
            {"field": "Affaire", "header": "Affaire", "width": 150, "sortable": True, "visible": False},
        ],
        "default_sort": {"field": "Date Devis", "direction": "desc"},
        "page_size": 50,
        "show_totals": True,
        "total_columns": ["Montant HT", "Montant TTC", "Qte"],
    },
    {
        "nom": "Avoirs",
        "description": "Liste des avoirs",
        "data_source_code": "DS_AVOIRS",
        "menu_code": "DS_AVOIRS",
        "columns": [
            {"field": "Societe", "header": "Societe", "width": 100, "sortable": True, "visible": True},
            {"field": "Type Document", "header": "Type", "width": 100, "sortable": True, "visible": True},
            {"field": "Num Avoir", "header": "N Avoir", "width": 120, "sortable": True, "visible": True},
            {"field": "Date Avoir", "header": "Date", "width": 100, "format": "date", "sortable": True, "visible": True},
            {"field": "Code Client", "header": "Code Client", "width": 100, "sortable": True, "visible": True},
            {"field": "Client", "header": "Client", "width": 200, "sortable": True, "visible": True},
            {"field": "Code Article", "header": "Code Article", "width": 120, "sortable": True, "visible": True},
            {"field": "Designation", "header": "Designation", "width": 200, "sortable": True, "visible": True},
            {"field": "Qte", "header": "Qte", "width": 80, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "PU HT", "header": "PU HT", "width": 100, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Montant HT", "header": "Montant HT", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Montant TTC", "header": "Montant TTC", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Code Depot", "header": "Code Depot", "width": 100, "sortable": True, "visible": False},
        ],
        "default_sort": {"field": "Date Avoir", "direction": "desc"},
        "page_size": 50,
        "show_totals": True,
        "total_columns": ["Montant HT", "Montant TTC", "Qte"],
    },
    {
        "nom": "Preparations Livraison",
        "description": "Liste des preparations de livraison",
        "data_source_code": "DS_PREPARATIONS_LIVRAISON",
        "menu_code": "DS_PREPARATIONS_LIVRAISON",
        "columns": [
            {"field": "Societe", "header": "Societe", "width": 100, "sortable": True, "visible": True},
            {"field": "Num PL", "header": "N PL", "width": 120, "sortable": True, "visible": True},
            {"field": "Date PL", "header": "Date PL", "width": 100, "format": "date", "sortable": True, "visible": True},
            {"field": "Num BC", "header": "N BC", "width": 120, "sortable": True, "visible": True},
            {"field": "Code Client", "header": "Code Client", "width": 100, "sortable": True, "visible": True},
            {"field": "Client", "header": "Client", "width": 200, "sortable": True, "visible": True},
            {"field": "Code Article", "header": "Code Article", "width": 120, "sortable": True, "visible": True},
            {"field": "Designation", "header": "Designation", "width": 200, "sortable": True, "visible": True},
            {"field": "Qte PL", "header": "Qte PL", "width": 80, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "PU HT", "header": "PU HT", "width": 100, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Montant HT", "header": "Montant HT", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Code Depot", "header": "Code Depot", "width": 100, "sortable": True, "visible": True},
            {"field": "Depot", "header": "Depot", "width": 150, "sortable": True, "visible": True},
            {"field": "Date Livraison Prevue", "header": "Livraison Prevue", "width": 120, "format": "date", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Date PL", "direction": "desc"},
        "page_size": 50,
        "show_totals": True,
        "total_columns": ["Montant HT", "Qte PL"],
    },
    {
        "nom": "Ventes par Type Document",
        "description": "Synthese des ventes par type de document",
        "data_source_code": "DS_VENTES_PAR_TYPE_DOC",
        "menu_code": "DS_VENTES_PAR_TYPE_DOC",
        "columns": [
            {"field": "Type Document", "header": "Type Document", "width": 150, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 100, "sortable": True, "visible": True},
            {"field": "Nb Documents", "header": "Nb Docs", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Lignes", "header": "Nb Lignes", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Qte Totale", "header": "Qte Totale", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Montant HT", "header": "Montant HT", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Montant TTC", "header": "Montant TTC", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Clients", "header": "Nb Clients", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Articles", "header": "Nb Articles", "width": 100, "format": "number", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Montant HT", "direction": "desc"},
        "page_size": 25,
        "show_totals": True,
        "total_columns": ["Montant HT", "Montant TTC", "Nb Documents", "Nb Lignes"],
    },
    {
        "nom": "Ventes Detail Complet",
        "description": "Detail complet de toutes les ventes",
        "data_source_code": "DS_VENTES_DETAIL",
        "menu_code": "DS_VENTES_DETAIL",
        "columns": [
            {"field": "Societe", "header": "Societe", "width": 100, "sortable": True, "visible": True},
            {"field": "Type Document", "header": "Type", "width": 100, "sortable": True, "visible": True},
            {"field": "Num Piece", "header": "N Piece", "width": 120, "sortable": True, "visible": True},
            {"field": "Date", "header": "Date", "width": 100, "format": "date", "sortable": True, "visible": True},
            {"field": "Code Client", "header": "Code Client", "width": 100, "sortable": True, "visible": True},
            {"field": "Client", "header": "Client", "width": 180, "sortable": True, "visible": True},
            {"field": "Code Article", "header": "Code Article", "width": 120, "sortable": True, "visible": True},
            {"field": "Designation", "header": "Designation", "width": 200, "sortable": True, "visible": True},
            {"field": "Qte", "header": "Qte", "width": 70, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "PU HT", "header": "PU HT", "width": 90, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Montant HT", "header": "MT HT", "width": 110, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Montant TTC", "header": "MT TTC", "width": 110, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Marge", "header": "Marge", "width": 100, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Code Depot", "header": "Depot", "width": 80, "sortable": True, "visible": False},
            {"field": "Code Affaire", "header": "Affaire", "width": 100, "sortable": True, "visible": False},
        ],
        "default_sort": {"field": "Date", "direction": "desc"},
        "page_size": 100,
        "show_totals": True,
        "total_columns": ["Montant HT", "Montant TTC", "Marge", "Qte"],
    },

    # === Analyses des Ventes ===
    {
        "nom": "Top Clients",
        "description": "Classement des meilleurs clients par CA",
        "data_source_code": "DS_TOP_CLIENTS",
        "menu_code": "DS_TOP_CLIENTS",
        "columns": [
            {"field": "Code Client", "header": "Code", "width": 100, "sortable": True, "visible": True},
            {"field": "Client", "header": "Client", "width": 200, "sortable": True, "visible": True},
            {"field": "Societe", "header": "Societe", "width": 100, "sortable": True, "visible": True},
            {"field": "CA HT", "header": "CA HT", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Marge", "header": "Marge", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Taux Marge %", "header": "Taux Marge", "width": 100, "format": "percent", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Factures", "header": "Nb Fact.", "width": 90, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Articles", "header": "Nb Art.", "width": 90, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Premiere Vente", "header": "1ere Vente", "width": 100, "format": "date", "sortable": True, "visible": True},
            {"field": "Derniere Vente", "header": "Derniere Vente", "width": 110, "format": "date", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "CA HT", "direction": "desc"},
        "page_size": 50,
        "show_totals": True,
        "total_columns": ["CA HT", "Marge"],
    },
    {
        "nom": "Top Articles",
        "description": "Classement des articles les plus vendus",
        "data_source_code": "DS_TOP_ARTICLES",
        "menu_code": "DS_TOP_ARTICLES",
        "columns": [
            {"field": "Code Article", "header": "Code", "width": 120, "sortable": True, "visible": True},
            {"field": "Designation", "header": "Designation", "width": 250, "sortable": True, "visible": True},
            {"field": "Catalogue", "header": "Catalogue", "width": 120, "sortable": True, "visible": True},
            {"field": "Qte Vendue", "header": "Qte", "width": 80, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "CA HT", "header": "CA HT", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Marge", "header": "Marge", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Taux Marge %", "header": "Taux Marge", "width": 100, "format": "percent", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Clients", "header": "Nb Clients", "width": 90, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Nb Ventes", "header": "Nb Ventes", "width": 90, "format": "number", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "CA HT", "direction": "desc"},
        "page_size": 50,
        "show_totals": True,
        "total_columns": ["CA HT", "Marge", "Qte Vendue"],
    },
    {
        "nom": "Commandes en Cours",
        "description": "Commandes clients non entierement livrees",
        "data_source_code": "DS_COMMANDES_EN_COURS",
        "menu_code": "DS_COMMANDES_EN_COURS",
        "columns": [
            {"field": "Societe", "header": "Societe", "width": 100, "sortable": True, "visible": True},
            {"field": "Num BC", "header": "N BC", "width": 120, "sortable": True, "visible": True},
            {"field": "Date BC", "header": "Date BC", "width": 100, "format": "date", "sortable": True, "visible": True},
            {"field": "Code Client", "header": "Code Client", "width": 100, "sortable": True, "visible": True},
            {"field": "Client", "header": "Client", "width": 200, "sortable": True, "visible": True},
            {"field": "Code Article", "header": "Code Article", "width": 120, "sortable": True, "visible": True},
            {"field": "Designation", "header": "Designation", "width": 200, "sortable": True, "visible": True},
            {"field": "Qte Commandee", "header": "Qte Cmd", "width": 80, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Qte Livree", "header": "Qte Livree", "width": 80, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Reste A Livrer", "header": "Reste", "width": 80, "format": "number", "align": "right", "sortable": True, "visible": True},
            {"field": "Montant Reste", "header": "MT Reste", "width": 120, "format": "currency", "align": "right", "sortable": True, "visible": True},
            {"field": "Date Livraison Prevue", "header": "Livraison Prevue", "width": 120, "format": "date", "sortable": True, "visible": True},
            {"field": "Age Commande Jours", "header": "Age (j)", "width": 80, "format": "number", "align": "right", "sortable": True, "visible": True},
        ],
        "default_sort": {"field": "Age Commande Jours", "direction": "desc"},
        "page_size": 50,
        "show_totals": True,
        "total_columns": ["Montant Reste", "Qte Commandee", "Reste A Livrer"],
    },
]

FEATURES = {
    "show_search": True,
    "show_column_filters": True,
    "show_grouping": True,
    "show_column_toggle": True,
    "show_export": True,
    "show_pagination": True,
    "show_page_size": True,
    "allow_sorting": True,
}


def main():
    print("=" * 60)
    print("  CREATION DES GRIDVIEWS VENTES & ANALYSES")
    print("=" * 60)

    created = 0
    updated_menus = 0

    with get_db_cursor() as cursor:
        for gv in GRIDVIEWS:
            menu_code = gv.pop("menu_code")

            # Verifier si un gridview avec ce data_source_code existe deja
            existing = execute_query(
                "SELECT id FROM APP_GridViews WHERE data_source_code = ?",
                (gv["data_source_code"],),
                use_cache=False
            )

            if existing:
                grid_id = existing[0]["id"]
                print(f"  [existe] {gv['nom']} (ID={grid_id})")
            else:
                # Creer le gridview
                cursor.execute(
                    """INSERT INTO APP_GridViews
                       (nom, description, data_source_code, columns_config, default_sort, page_size, show_totals, total_columns, row_styles, features, is_public, created_by)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1)""",
                    (
                        gv["nom"],
                        gv["description"],
                        gv["data_source_code"],
                        json.dumps(gv["columns"]),
                        json.dumps(gv["default_sort"]),
                        gv["page_size"],
                        gv["show_totals"],
                        json.dumps(gv["total_columns"]),
                        json.dumps([]),
                        json.dumps(FEATURES),
                    )
                )
                cursor.execute("SELECT @@IDENTITY AS id")
                grid_id = int(cursor.fetchone()[0])
                created += 1
                print(f"  [cree]   {gv['nom']} (ID={grid_id})")

            # Mettre a jour le menu qui reference ce code
            cursor.execute(
                "UPDATE APP_Menus SET target_id = ? WHERE code = ? AND type = 'gridview'",
                (grid_id, menu_code)
            )
            if cursor.rowcount > 0:
                updated_menus += cursor.rowcount
                print(f"           -> Menu '{menu_code}' mis a jour (target_id={grid_id})")

    print()
    print(f"Resultat: {created} GridViews crees, {updated_menus} menus mis a jour")
    print("=" * 60)


if __name__ == "__main__":
    main()
