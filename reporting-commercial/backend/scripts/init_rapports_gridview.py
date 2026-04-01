"""
Script d'initialisation des Rapports GridView basés sur les DataSources Templates
==================================================================================
Ce script crée des grilles prêtes à l'emploi pour chaque template de DataSource Ventes
"""

import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import execute_query, get_db_cursor


def get_template_by_code(code):
    """Récupère un template par son code"""
    results = execute_query(
        "SELECT id, code, nom, query_template FROM APP_DataSources_Templates WHERE code = ?",
        (code,),
        use_cache=False
    )
    return results[0] if results else None


def create_gridview(config):
    """Crée ou met à jour une GridView"""
    # Vérifier si la grille existe déjà
    existing = execute_query(
        "SELECT id FROM APP_GridViews WHERE nom = ?",
        (config['nom'],),
        use_cache=False
    )

    if existing:
        print(f"  [UPDATE] GridView '{config['nom']}' existe déjà (id={existing[0]['id']})")
        # Mettre à jour
        with get_db_cursor() as cursor:
            cursor.execute("""
                UPDATE APP_GridViews
                SET description = ?,
                    data_source_code = ?,
                    columns_config = ?,
                    default_sort = ?,
                    page_size = ?,
                    show_totals = ?,
                    total_columns = ?,
                    features = ?,
                    is_public = 1,
                    updated_at = GETDATE()
                WHERE id = ?
            """, (
                config.get('description', ''),
                config['data_source_code'],
                json.dumps(config.get('columns', [])),
                json.dumps(config.get('default_sort')),
                config.get('page_size', 25),
                1 if config.get('show_totals') else 0,
                json.dumps(config.get('total_columns', [])),
                json.dumps(config.get('features', {})),
                existing[0]['id']
            ))
        return existing[0]['id']
    else:
        print(f"  [CREATE] GridView '{config['nom']}'")
        with get_db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO APP_GridViews
                (nom, description, data_source_code, columns_config, default_sort,
                 page_size, show_totals, total_columns, features, is_public, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1)
            """, (
                config['nom'],
                config.get('description', ''),
                config['data_source_code'],
                json.dumps(config.get('columns', [])),
                json.dumps(config.get('default_sort')),
                config.get('page_size', 25),
                1 if config.get('show_totals') else 0,
                json.dumps(config.get('total_columns', [])),
                json.dumps(config.get('features', {}))
            ))
            cursor.execute("SELECT @@IDENTITY AS id")
            result = cursor.fetchone()
            return result[0] if result else None


# =============================================================================
# CONFIGURATIONS DES GRIDVIEWS VENTES
# =============================================================================

GRIDVIEW_CONFIGS = [
    # 1. CA Global
    {
        "nom": "CA Global",
        "description": "Vue globale du chiffre d'affaires et marge par société",
        "data_source_code": "DS_VENTES_GLOBAL",
        "columns": [
            {"field": "Societe", "header": "Société", "width": 150, "sortable": True, "filterable": True, "align": "left"},
            {"field": "CA HT", "header": "CA HT", "width": 130, "sortable": True, "filterable": True, "format": "currency", "align": "right"},
            {"field": "CA TTC", "header": "CA TTC", "width": 130, "sortable": True, "filterable": True, "format": "currency", "align": "right"},
            {"field": "Marge", "header": "Marge", "width": 130, "sortable": True, "filterable": True, "format": "currency", "align": "right"},
            {"field": "Taux Marge %", "header": "Tx Marge %", "width": 100, "sortable": True, "filterable": True, "format": "percent", "align": "right"},
            {"field": "Nb Clients", "header": "Nb Clients", "width": 100, "sortable": True, "filterable": True, "format": "number", "align": "right"},
            {"field": "Nb Documents", "header": "Nb Docs", "width": 100, "sortable": True, "filterable": True, "format": "number", "align": "right"},
            {"field": "Qte Totale", "header": "Qté Totale", "width": 100, "sortable": True, "filterable": True, "format": "number", "align": "right"},
            {"field": "Nb Lignes", "header": "Nb Lignes", "width": 100, "sortable": True, "filterable": True, "format": "number", "align": "right"}
        ],
        "default_sort": {"field": "CA HT", "direction": "desc"},
        "page_size": 25,
        "show_totals": True,
        "total_columns": ["CA HT", "CA TTC", "Marge", "Nb Clients", "Nb Documents", "Qte Totale", "Nb Lignes"],
        "features": {
            "show_search": True,
            "show_column_filters": True,
            "show_grouping": True,
            "show_column_toggle": True,
            "show_export": True,
            "show_pagination": True,
            "show_page_size": True,
            "allow_sorting": True
        }
    },

    # 2. CA par Mois
    {
        "nom": "CA par Mois",
        "description": "Evolution mensuelle du chiffre d'affaires",
        "data_source_code": "DS_VENTES_PAR_MOIS",
        "columns": [
            {"field": "Periode", "header": "Période", "width": 100, "sortable": True, "filterable": True, "align": "center"},
            {"field": "Annee", "header": "Année", "width": 80, "sortable": True, "filterable": True, "format": "number", "align": "center"},
            {"field": "Mois", "header": "Mois", "width": 60, "sortable": True, "filterable": True, "format": "number", "align": "center"},
            {"field": "Societe", "header": "Société", "width": 150, "sortable": True, "filterable": True, "align": "left"},
            {"field": "CA HT", "header": "CA HT", "width": 130, "sortable": True, "filterable": True, "format": "currency", "align": "right"},
            {"field": "CA TTC", "header": "CA TTC", "width": 130, "sortable": True, "filterable": True, "format": "currency", "align": "right"},
            {"field": "Marge", "header": "Marge", "width": 130, "sortable": True, "filterable": True, "format": "currency", "align": "right"},
            {"field": "Taux Marge %", "header": "Tx Marge %", "width": 100, "sortable": True, "filterable": True, "format": "percent", "align": "right"},
            {"field": "Nb Clients", "header": "Nb Clients", "width": 100, "sortable": True, "filterable": True, "format": "number", "align": "right"},
            {"field": "Qte Totale", "header": "Qté Totale", "width": 100, "sortable": True, "filterable": True, "format": "number", "align": "right"}
        ],
        "default_sort": {"field": "Periode", "direction": "asc"},
        "page_size": 50,
        "show_totals": True,
        "total_columns": ["CA HT", "CA TTC", "Marge", "Nb Clients", "Qte Totale"],
        "features": {
            "show_search": True,
            "show_column_filters": True,
            "show_grouping": True,
            "show_column_toggle": True,
            "show_export": True,
            "show_pagination": True,
            "show_page_size": True,
            "allow_sorting": True
        }
    },

    # 3. CA par Client
    {
        "nom": "CA par Client",
        "description": "Chiffre d'affaires et marge par client",
        "data_source_code": "DS_VENTES_PAR_CLIENT",
        "columns": [
            {"field": "Code Client", "header": "Code", "width": 100, "sortable": True, "filterable": True, "align": "left"},
            {"field": "Client", "header": "Client", "width": 200, "sortable": True, "filterable": True, "align": "left"},
            {"field": "Societe", "header": "Société", "width": 120, "sortable": True, "filterable": True, "align": "left"},
            {"field": "CA HT", "header": "CA HT", "width": 130, "sortable": True, "filterable": True, "format": "currency", "align": "right"},
            {"field": "CA TTC", "header": "CA TTC", "width": 130, "sortable": True, "filterable": True, "format": "currency", "align": "right"},
            {"field": "Marge", "header": "Marge", "width": 120, "sortable": True, "filterable": True, "format": "currency", "align": "right"},
            {"field": "Taux Marge %", "header": "Tx Marge %", "width": 100, "sortable": True, "filterable": True, "format": "percent", "align": "right"},
            {"field": "Nb Factures", "header": "Nb Fact.", "width": 90, "sortable": True, "filterable": True, "format": "number", "align": "right"},
            {"field": "Qte Totale", "header": "Qté", "width": 90, "sortable": True, "filterable": True, "format": "number", "align": "right"},
            {"field": "Premiere Vente", "header": "1ère Vente", "width": 100, "sortable": True, "filterable": True, "format": "date", "align": "center"},
            {"field": "Derniere Vente", "header": "Dern. Vente", "width": 100, "sortable": True, "filterable": True, "format": "date", "align": "center"}
        ],
        "default_sort": {"field": "CA HT", "direction": "desc"},
        "page_size": 50,
        "show_totals": True,
        "total_columns": ["CA HT", "CA TTC", "Marge", "Nb Factures", "Qte Totale"],
        "features": {
            "show_search": True,
            "show_column_filters": True,
            "show_grouping": True,
            "show_column_toggle": True,
            "show_export": True,
            "show_pagination": True,
            "show_page_size": True,
            "allow_sorting": True
        }
    },

    # 4. CA par Article
    {
        "nom": "CA par Article",
        "description": "Chiffre d'affaires et marge par article",
        "data_source_code": "DS_VENTES_PAR_ARTICLE",
        "columns": [
            {"field": "Code Article", "header": "Code", "width": 120, "sortable": True, "filterable": True, "align": "left"},
            {"field": "Designation", "header": "Désignation", "width": 220, "sortable": True, "filterable": True, "align": "left"},
            {"field": "Catalogue1", "header": "Catalogue", "width": 120, "sortable": True, "filterable": True, "align": "left"},
            {"field": "Catalogue2", "header": "Sous-Cat.", "width": 100, "sortable": True, "filterable": True, "align": "left"},
            {"field": "Qte Vendue", "header": "Qté", "width": 80, "sortable": True, "filterable": True, "format": "number", "align": "right"},
            {"field": "CA HT", "header": "CA HT", "width": 120, "sortable": True, "filterable": True, "format": "currency", "align": "right"},
            {"field": "Marge", "header": "Marge", "width": 110, "sortable": True, "filterable": True, "format": "currency", "align": "right"},
            {"field": "Taux Marge %", "header": "Tx Marge %", "width": 90, "sortable": True, "filterable": True, "format": "percent", "align": "right"},
            {"field": "Prix Moyen", "header": "PU Moyen", "width": 100, "sortable": True, "filterable": True, "format": "currency", "align": "right"},
            {"field": "Cout Moyen", "header": "Coût Moy.", "width": 100, "sortable": True, "filterable": True, "format": "currency", "align": "right"},
            {"field": "Nb Clients", "header": "Nb Cli.", "width": 80, "sortable": True, "filterable": True, "format": "number", "align": "right"}
        ],
        "default_sort": {"field": "CA HT", "direction": "desc"},
        "page_size": 50,
        "show_totals": True,
        "total_columns": ["Qte Vendue", "CA HT", "Marge", "Nb Clients"],
        "features": {
            "show_search": True,
            "show_column_filters": True,
            "show_grouping": True,
            "show_column_toggle": True,
            "show_export": True,
            "show_pagination": True,
            "show_page_size": True,
            "allow_sorting": True
        }
    },

    # 5. CA par Catalogue
    {
        "nom": "CA par Catalogue",
        "description": "Chiffre d'affaires par famille de produits",
        "data_source_code": "DS_VENTES_PAR_CATALOGUE",
        "columns": [
            {"field": "Catalogue", "header": "Catalogue", "width": 180, "sortable": True, "filterable": True, "align": "left"},
            {"field": "Sous Catalogue", "header": "Sous-Catalogue", "width": 150, "sortable": True, "filterable": True, "align": "left"},
            {"field": "Nb Articles", "header": "Nb Art.", "width": 80, "sortable": True, "filterable": True, "format": "number", "align": "right"},
            {"field": "Qte Vendue", "header": "Qté", "width": 90, "sortable": True, "filterable": True, "format": "number", "align": "right"},
            {"field": "CA HT", "header": "CA HT", "width": 130, "sortable": True, "filterable": True, "format": "currency", "align": "right"},
            {"field": "Marge", "header": "Marge", "width": 120, "sortable": True, "filterable": True, "format": "currency", "align": "right"},
            {"field": "Taux Marge %", "header": "Tx Marge %", "width": 100, "sortable": True, "filterable": True, "format": "percent", "align": "right"},
            {"field": "Nb Clients", "header": "Nb Clients", "width": 100, "sortable": True, "filterable": True, "format": "number", "align": "right"}
        ],
        "default_sort": {"field": "CA HT", "direction": "desc"},
        "page_size": 50,
        "show_totals": True,
        "total_columns": ["Nb Articles", "Qte Vendue", "CA HT", "Marge", "Nb Clients"],
        "features": {
            "show_search": True,
            "show_column_filters": True,
            "show_grouping": True,
            "show_column_toggle": True,
            "show_export": True,
            "show_pagination": True,
            "show_page_size": True,
            "allow_sorting": True
        }
    },

    # 6. CA par Depot
    {
        "nom": "CA par Depot",
        "description": "Chiffre d'affaires par dépôt/entrepôt",
        "data_source_code": "DS_VENTES_PAR_DEPOT",
        "columns": [
            {"field": "Code Depot", "header": "Code", "width": 100, "sortable": True, "filterable": True, "align": "left"},
            {"field": "Depot", "header": "Dépôt", "width": 180, "sortable": True, "filterable": True, "align": "left"},
            {"field": "Societe", "header": "Société", "width": 120, "sortable": True, "filterable": True, "align": "left"},
            {"field": "CA HT", "header": "CA HT", "width": 130, "sortable": True, "filterable": True, "format": "currency", "align": "right"},
            {"field": "Marge", "header": "Marge", "width": 120, "sortable": True, "filterable": True, "format": "currency", "align": "right"},
            {"field": "Qte Vendue", "header": "Qté", "width": 90, "sortable": True, "filterable": True, "format": "number", "align": "right"},
            {"field": "Nb Articles", "header": "Nb Art.", "width": 90, "sortable": True, "filterable": True, "format": "number", "align": "right"},
            {"field": "Nb Clients", "header": "Nb Cli.", "width": 90, "sortable": True, "filterable": True, "format": "number", "align": "right"},
            {"field": "Nb Documents", "header": "Nb Docs", "width": 90, "sortable": True, "filterable": True, "format": "number", "align": "right"}
        ],
        "default_sort": {"field": "CA HT", "direction": "desc"},
        "page_size": 50,
        "show_totals": True,
        "total_columns": ["CA HT", "Marge", "Qte Vendue", "Nb Articles", "Nb Clients", "Nb Documents"],
        "features": {
            "show_search": True,
            "show_column_filters": True,
            "show_grouping": True,
            "show_column_toggle": True,
            "show_export": True,
            "show_pagination": True,
            "show_page_size": True,
            "allow_sorting": True
        }
    },

    # 7. CA par Commercial
    {
        "nom": "CA par Commercial",
        "description": "Performance commerciale par représentant",
        "data_source_code": "DS_VENTES_PAR_COMMERCIAL",
        "columns": [
            {"field": "Code Commercial", "header": "Code", "width": 100, "sortable": True, "filterable": True, "align": "left"},
            {"field": "Commercial", "header": "Commercial", "width": 180, "sortable": True, "filterable": True, "align": "left"},
            {"field": "Societe", "header": "Société", "width": 120, "sortable": True, "filterable": True, "align": "left"},
            {"field": "Nb Clients", "header": "Nb Cli.", "width": 90, "sortable": True, "filterable": True, "format": "number", "align": "right"},
            {"field": "Nb Factures", "header": "Nb Fact.", "width": 90, "sortable": True, "filterable": True, "format": "number", "align": "right"},
            {"field": "CA HT", "header": "CA HT", "width": 130, "sortable": True, "filterable": True, "format": "currency", "align": "right"},
            {"field": "Marge", "header": "Marge", "width": 120, "sortable": True, "filterable": True, "format": "currency", "align": "right"},
            {"field": "Taux Marge %", "header": "Tx Marge %", "width": 100, "sortable": True, "filterable": True, "format": "percent", "align": "right"}
        ],
        "default_sort": {"field": "CA HT", "direction": "desc"},
        "page_size": 50,
        "show_totals": True,
        "total_columns": ["Nb Clients", "Nb Factures", "CA HT", "Marge"],
        "features": {
            "show_search": True,
            "show_column_filters": True,
            "show_grouping": True,
            "show_column_toggle": True,
            "show_export": True,
            "show_pagination": True,
            "show_page_size": True,
            "allow_sorting": True
        }
    },

    # 8. CA par Zone Geo
    {
        "nom": "CA par Zone Geo",
        "description": "Répartition géographique des ventes",
        "data_source_code": "DS_VENTES_PAR_ZONE",
        "columns": [
            {"field": "Zone", "header": "Zone", "width": 150, "sortable": True, "filterable": True, "align": "left"},
            {"field": "Canal", "header": "Canal", "width": 120, "sortable": True, "filterable": True, "align": "left"},
            {"field": "Societe", "header": "Société", "width": 120, "sortable": True, "filterable": True, "align": "left"},
            {"field": "Nb Clients", "header": "Nb Clients", "width": 100, "sortable": True, "filterable": True, "format": "number", "align": "right"},
            {"field": "CA HT", "header": "CA HT", "width": 130, "sortable": True, "filterable": True, "format": "currency", "align": "right"},
            {"field": "Marge", "header": "Marge", "width": 120, "sortable": True, "filterable": True, "format": "currency", "align": "right"},
            {"field": "Taux Marge %", "header": "Tx Marge %", "width": 100, "sortable": True, "filterable": True, "format": "percent", "align": "right"}
        ],
        "default_sort": {"field": "CA HT", "direction": "desc"},
        "page_size": 50,
        "show_totals": True,
        "total_columns": ["Nb Clients", "CA HT", "Marge"],
        "features": {
            "show_search": True,
            "show_column_filters": True,
            "show_grouping": True,
            "show_column_toggle": True,
            "show_export": True,
            "show_pagination": True,
            "show_page_size": True,
            "allow_sorting": True
        }
    },

    # 9. CA par Affaire
    {
        "nom": "CA par Affaire",
        "description": "Chiffre d'affaires par affaire/projet",
        "data_source_code": "DS_VENTES_PAR_AFFAIRE",
        "columns": [
            {"field": "Code Affaire", "header": "Code", "width": 120, "sortable": True, "filterable": True, "align": "left"},
            {"field": "Affaire", "header": "Affaire", "width": 200, "sortable": True, "filterable": True, "align": "left"},
            {"field": "Code Client", "header": "Code Cli.", "width": 100, "sortable": True, "filterable": True, "align": "left"},
            {"field": "Client", "header": "Client", "width": 150, "sortable": True, "filterable": True, "align": "left"},
            {"field": "Societe", "header": "Société", "width": 100, "sortable": True, "filterable": True, "align": "left"},
            {"field": "CA HT", "header": "CA HT", "width": 130, "sortable": True, "filterable": True, "format": "currency", "align": "right"},
            {"field": "Marge", "header": "Marge", "width": 120, "sortable": True, "filterable": True, "format": "currency", "align": "right"},
            {"field": "Taux Marge %", "header": "Tx Marge %", "width": 100, "sortable": True, "filterable": True, "format": "percent", "align": "right"},
            {"field": "Nb Documents", "header": "Nb Docs", "width": 90, "sortable": True, "filterable": True, "format": "number", "align": "right"},
            {"field": "Date Debut", "header": "Début", "width": 100, "sortable": True, "filterable": True, "format": "date", "align": "center"},
            {"field": "Date Fin", "header": "Fin", "width": 100, "sortable": True, "filterable": True, "format": "date", "align": "center"}
        ],
        "default_sort": {"field": "CA HT", "direction": "desc"},
        "page_size": 50,
        "show_totals": True,
        "total_columns": ["CA HT", "Marge", "Nb Documents"],
        "features": {
            "show_search": True,
            "show_column_filters": True,
            "show_grouping": True,
            "show_column_toggle": True,
            "show_export": True,
            "show_pagination": True,
            "show_page_size": True,
            "allow_sorting": True
        }
    }
]


def init_gridviews():
    """Initialise toutes les GridViews"""
    print("\n" + "="*70)
    print("INITIALISATION DES RAPPORTS GRIDVIEW - VENTES")
    print("="*70 + "\n")

    created = 0
    updated = 0
    errors = 0

    for config in GRIDVIEW_CONFIGS:
        try:
            # Vérifier que le template existe
            template = get_template_by_code(config['data_source_code'])
            if not template:
                print(f"  [WARN] Template '{config['data_source_code']}' non trouve - Grille ignoree")
                continue

            # Créer la grille
            existing = execute_query(
                "SELECT id FROM APP_GridViews WHERE nom = ?",
                (config['nom'],),
                use_cache=False
            )

            result_id = create_gridview(config)

            if existing:
                updated += 1
            else:
                created += 1

            print(f"  -> ID: {result_id}")

        except Exception as e:
            print(f"  [ERROR] {config['nom']}: {e}")
            errors += 1

    print("\n" + "-"*70)
    print(f"RESUME: {created} creees, {updated} mises a jour, {errors} erreurs")
    print("-"*70 + "\n")

    return created, updated, errors


if __name__ == "__main__":
    init_gridviews()
