"""
Script d'initialisation des Rapports Pivot bases sur les DataSources Templates
================================================================================
Ce script cree des pivots prets a l'emploi pour chaque template de DataSource Ventes.
Utilise le pattern UPSERT (create or update) par nom de pivot.

Execution: python backend/scripts/init_rapports_pivot.py
"""

import sys
import os
import json

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import execute_query, get_db_cursor


def get_template_by_code(code):
    """Recupere un template par son code"""
    results = execute_query(
        "SELECT id, code, nom, query_template FROM APP_DataSources_Templates WHERE code = ?",
        (code,),
        use_cache=False
    )
    return results[0] if results else None


def create_pivot(config):
    """Cree ou met a jour un Pivot"""
    # Verifier si le pivot existe deja
    existing = execute_query(
        "SELECT id FROM APP_Pivots WHERE nom = ?",
        (config['nom'],),
        use_cache=False
    )

    if existing:
        print(f"  [UPDATE] Pivot '{config['nom']}' existe deja (id={existing[0]['id']})")
        with get_db_cursor() as cursor:
            cursor.execute("""
                UPDATE APP_Pivots
                SET description = ?,
                    data_source_code = ?,
                    rows_config = ?,
                    columns_config = ?,
                    values_config = ?,
                    filters_config = ?,
                    is_public = 1,
                    updated_at = GETDATE()
                WHERE id = ?
            """, (
                config.get('description', ''),
                config['data_source_code'],
                json.dumps(config.get('rows', []), ensure_ascii=False),
                json.dumps(config.get('columns', []), ensure_ascii=False),
                json.dumps(config.get('values', []), ensure_ascii=False),
                json.dumps(config.get('filters', []), ensure_ascii=False),
                existing[0]['id']
            ))
        return existing[0]['id']
    else:
        print(f"  [CREATE] Pivot '{config['nom']}'")
        with get_db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO APP_Pivots
                (nom, description, data_source_code, rows_config, columns_config,
                 values_config, filters_config, is_public, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1)
            """, (
                config['nom'],
                config.get('description', ''),
                config['data_source_code'],
                json.dumps(config.get('rows', []), ensure_ascii=False),
                json.dumps(config.get('columns', []), ensure_ascii=False),
                json.dumps(config.get('values', []), ensure_ascii=False),
                json.dumps(config.get('filters', []), ensure_ascii=False)
            ))
            cursor.execute("SELECT @@IDENTITY AS id")
            result = cursor.fetchone()
            return result[0] if result else None


# =============================================================================
# CONFIGURATIONS DES PIVOTS VENTES
# =============================================================================

PIVOT_CONFIGS = [
    # 1. Pivot CA Global par Societe
    {
        "nom": "Pivot CA Global",
        "description": "Analyse globale du chiffre d'affaires par societe avec marge et nombre de clients",
        "data_source_code": "DS_VENTES_GLOBAL",
        "rows": ["Societe"],
        "columns": [],
        "values": [
            {"field": "CA HT", "aggregation": "SUM", "alias": "SUM_CA_HT"},
            {"field": "Marge", "aggregation": "SUM", "alias": "SUM_Marge"},
            {"field": "Nb Clients", "aggregation": "SUM", "alias": "SUM_Nb_Clients"},
            {"field": "Nb Documents", "aggregation": "SUM", "alias": "SUM_Nb_Docs"}
        ],
        "filters": []
    },

    # 2. Pivot CA par Client
    {
        "nom": "Pivot CA par Client",
        "description": "Chiffre d'affaires et marge par client avec nombre de factures",
        "data_source_code": "DS_VENTES_PAR_CLIENT",
        "rows": ["Code Client", "Client"],
        "columns": [],
        "values": [
            {"field": "CA HT", "aggregation": "SUM", "alias": "SUM_CA_HT"},
            {"field": "Marge", "aggregation": "SUM", "alias": "SUM_Marge"},
            {"field": "Nb Factures", "aggregation": "SUM", "alias": "SUM_Nb_Factures"}
        ],
        "filters": []
    },

    # 3. Pivot CA par Article et Catalogue
    {
        "nom": "Pivot CA par Article",
        "description": "Analyse des ventes par article avec regroupement par catalogue",
        "data_source_code": "DS_VENTES_PAR_ARTICLE",
        "rows": ["Catalogue1", "Designation"],
        "columns": [],
        "values": [
            {"field": "CA HT", "aggregation": "SUM", "alias": "SUM_CA_HT"},
            {"field": "Qte Vendue", "aggregation": "SUM", "alias": "SUM_Qte"},
            {"field": "Marge", "aggregation": "SUM", "alias": "SUM_Marge"}
        ],
        "filters": []
    },

    # 4. Pivot CA par Catalogue
    {
        "nom": "Pivot CA par Catalogue",
        "description": "Ventilation du CA par catalogue et sous-catalogue de produits",
        "data_source_code": "DS_VENTES_PAR_CATALOGUE",
        "rows": ["Catalogue", "Sous Catalogue"],
        "columns": [],
        "values": [
            {"field": "CA HT", "aggregation": "SUM", "alias": "SUM_CA_HT"},
            {"field": "Marge", "aggregation": "SUM", "alias": "SUM_Marge"},
            {"field": "Nb Articles", "aggregation": "SUM", "alias": "SUM_Nb_Articles"}
        ],
        "filters": []
    },

    # 5. Pivot CA par Commercial
    {
        "nom": "Pivot CA par Commercial",
        "description": "Performance de l'equipe commerciale : CA, marge, clients et factures",
        "data_source_code": "DS_VENTES_PAR_COMMERCIAL",
        "rows": ["Commercial"],
        "columns": [],
        "values": [
            {"field": "CA HT", "aggregation": "SUM", "alias": "SUM_CA_HT"},
            {"field": "Marge", "aggregation": "SUM", "alias": "SUM_Marge"},
            {"field": "Nb Clients", "aggregation": "SUM", "alias": "SUM_Nb_Clients"},
            {"field": "Nb Factures", "aggregation": "SUM", "alias": "SUM_Nb_Factures"}
        ],
        "filters": []
    },

    # 6. Pivot CA par Zone Geographique
    {
        "nom": "Pivot CA par Zone",
        "description": "Repartition geographique des ventes par zone et canal de distribution",
        "data_source_code": "DS_VENTES_PAR_ZONE",
        "rows": ["Zone", "Canal"],
        "columns": [],
        "values": [
            {"field": "CA HT", "aggregation": "SUM", "alias": "SUM_CA_HT"},
            {"field": "Marge", "aggregation": "SUM", "alias": "SUM_Marge"},
            {"field": "Nb Clients", "aggregation": "SUM", "alias": "SUM_Nb_Clients"}
        ],
        "filters": []
    },

    # 7. Pivot CA par Depot
    {
        "nom": "Pivot CA par Depot",
        "description": "Analyse des ventes par depot/entrepot",
        "data_source_code": "DS_VENTES_PAR_DEPOT",
        "rows": ["Depot"],
        "columns": [],
        "values": [
            {"field": "CA HT", "aggregation": "SUM", "alias": "SUM_CA_HT"},
            {"field": "Marge", "aggregation": "SUM", "alias": "SUM_Marge"},
            {"field": "Qte Vendue", "aggregation": "SUM", "alias": "SUM_Qte"}
        ],
        "filters": []
    },

    # 8. Pivot CA par Affaire
    {
        "nom": "Pivot CA par Affaire",
        "description": "Suivi du chiffre d'affaires par affaire/projet avec detail par client",
        "data_source_code": "DS_VENTES_PAR_AFFAIRE",
        "rows": ["Affaire", "Client"],
        "columns": [],
        "values": [
            {"field": "CA HT", "aggregation": "SUM", "alias": "SUM_CA_HT"},
            {"field": "Marge", "aggregation": "SUM", "alias": "SUM_Marge"},
            {"field": "Nb Documents", "aggregation": "SUM", "alias": "SUM_Nb_Docs"}
        ],
        "filters": []
    },

    # 9. Pivot Evolution Mensuelle (avec colonnes dynamiques)
    {
        "nom": "Pivot Evolution Mensuelle",
        "description": "Evolution du CA et de la marge par societe, ventilee par periode mensuelle",
        "data_source_code": "DS_VENTES_PAR_MOIS",
        "rows": ["Societe"],
        "columns": ["Periode"],
        "values": [
            {"field": "CA HT", "aggregation": "SUM", "alias": "SUM_CA_HT"},
            {"field": "Marge", "aggregation": "SUM", "alias": "SUM_Marge"}
        ],
        "filters": []
    },

    # 10. Pivot Marge par Catalogue
    {
        "nom": "Pivot Marge par Catalogue",
        "description": "Analyse de la rentabilite par catalogue : CA, marge et taux de marge moyen",
        "data_source_code": "DS_VENTES_PAR_CATALOGUE",
        "rows": ["Catalogue"],
        "columns": [],
        "values": [
            {"field": "CA HT", "aggregation": "SUM", "alias": "SUM_CA_HT"},
            {"field": "Marge", "aggregation": "SUM", "alias": "SUM_Marge"},
            {"field": "Taux Marge %", "aggregation": "AVG", "alias": "AVG_Taux_Marge"}
        ],
        "filters": []
    },

    # 11. Pivot Performance Commerciale detaillee
    {
        "nom": "Pivot Performance Commerciale",
        "description": "Performance detaillee par commercial et societe : CA, marge et portefeuille clients",
        "data_source_code": "DS_VENTES_PAR_COMMERCIAL",
        "rows": ["Commercial", "Societe"],
        "columns": [],
        "values": [
            {"field": "CA HT", "aggregation": "SUM", "alias": "SUM_CA_HT"},
            {"field": "Marge", "aggregation": "SUM", "alias": "SUM_Marge"},
            {"field": "Nb Clients", "aggregation": "SUM", "alias": "SUM_Nb_Clients"}
        ],
        "filters": []
    },

    # 12. Pivot CA Top Clients
    {
        "nom": "Pivot CA Top Clients",
        "description": "Classement des clients par CA avec detail HT, TTC et marge par societe",
        "data_source_code": "DS_VENTES_PAR_CLIENT",
        "rows": ["Code Client", "Client", "Societe"],
        "columns": [],
        "values": [
            {"field": "CA HT", "aggregation": "SUM", "alias": "SUM_CA_HT"},
            {"field": "CA TTC", "aggregation": "SUM", "alias": "SUM_CA_TTC"},
            {"field": "Marge", "aggregation": "SUM", "alias": "SUM_Marge"}
        ],
        "filters": []
    },

    # ==================== PIVOTS AVEC COLONNES MOIS (TCD) ====================

    # 13. Pivot CA Client par Mois
    {
        "nom": "Pivot CA Client par Mois",
        "description": "Evolution mensuelle du CA par client - tableau croise avec mois en colonnes",
        "data_source_code": "DS_VENTES_CLIENT_MOIS",
        "rows": ["Client"],
        "columns": ["Periode"],
        "values": [
            {"field": "CA HT", "aggregation": "SUM", "alias": "SUM_CA_HT"},
            {"field": "Marge", "aggregation": "SUM", "alias": "SUM_Marge"}
        ],
        "filters": []
    },

    # 14. Pivot CA Article par Mois
    {
        "nom": "Pivot CA Article par Mois",
        "description": "Evolution mensuelle du CA par article - tableau croise avec mois en colonnes",
        "data_source_code": "DS_VENTES_ARTICLE_MOIS",
        "rows": ["Article"],
        "columns": ["Periode"],
        "values": [
            {"field": "CA HT", "aggregation": "SUM", "alias": "SUM_CA_HT"},
            {"field": "Marge", "aggregation": "SUM", "alias": "SUM_Marge"}
        ],
        "filters": []
    },

    # 15. Pivot CA Commercial par Mois
    {
        "nom": "Pivot CA Commercial par Mois",
        "description": "Evolution mensuelle du CA par commercial - tableau croise avec mois en colonnes",
        "data_source_code": "DS_VENTES_COMMERCIAL_MOIS",
        "rows": ["Commercial"],
        "columns": ["Periode"],
        "values": [
            {"field": "CA HT", "aggregation": "SUM", "alias": "SUM_CA_HT"},
            {"field": "Marge", "aggregation": "SUM", "alias": "SUM_Marge"}
        ],
        "filters": []
    },

    # 16. Pivot CA Catalogue par Mois
    {
        "nom": "Pivot CA Catalogue par Mois",
        "description": "Evolution mensuelle du CA par catalogue - tableau croise avec mois en colonnes",
        "data_source_code": "DS_VENTES_CATALOGUE_MOIS",
        "rows": ["Catalogue"],
        "columns": ["Periode"],
        "values": [
            {"field": "CA HT", "aggregation": "SUM", "alias": "SUM_CA_HT"},
            {"field": "Marge", "aggregation": "SUM", "alias": "SUM_Marge"}
        ],
        "filters": []
    }
]


def init_pivots():
    """Initialise tous les Pivots"""
    print("\n" + "=" * 70)
    print("INITIALISATION DES RAPPORTS PIVOT - VENTES")
    print("=" * 70 + "\n")

    # S'assurer que la table existe
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Pivots' AND xtype='U')
                CREATE TABLE APP_Pivots (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    nom NVARCHAR(200) NOT NULL,
                    description NVARCHAR(500),
                    data_source_id INT,
                    data_source_code VARCHAR(100),
                    rows_config NVARCHAR(MAX),
                    columns_config NVARCHAR(MAX),
                    values_config NVARCHAR(MAX),
                    filters_config NVARCHAR(MAX),
                    is_public BIT DEFAULT 0,
                    created_by INT,
                    created_at DATETIME DEFAULT GETDATE(),
                    updated_at DATETIME DEFAULT GETDATE()
                )
            """)
            # Ajouter data_source_code si elle n'existe pas
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('APP_Pivots') AND name = 'data_source_code')
                ALTER TABLE APP_Pivots ADD data_source_code VARCHAR(100)
            """)
        print("Table APP_Pivots verifiee/creee\n")
    except Exception as e:
        print(f"  [WARN] Verification table: {e}\n")

    created = 0
    updated = 0
    errors = 0

    for config in PIVOT_CONFIGS:
        try:
            # Verifier que le template DataSource existe
            template = get_template_by_code(config['data_source_code'])
            if not template:
                print(f"  [WARN] Template '{config['data_source_code']}' non trouve - Pivot ignore")
                errors += 1
                continue

            # Creer/mettre a jour le pivot
            existing = execute_query(
                "SELECT id FROM APP_Pivots WHERE nom = ?",
                (config['nom'],),
                use_cache=False
            )

            result_id = create_pivot(config)

            if existing:
                updated += 1
            else:
                created += 1

            print(f"  -> ID: {result_id} (template: {config['data_source_code']})")

        except Exception as e:
            print(f"  [ERROR] {config['nom']}: {e}")
            errors += 1

    print("\n" + "-" * 70)
    print(f"RESUME: {created} crees, {updated} mis a jour, {errors} erreurs")
    print("-" * 70)

    # Afficher un recapitulatif
    all_pivots = execute_query("SELECT id, nom, data_source_code FROM APP_Pivots ORDER BY id", use_cache=False)
    print(f"\nTotal pivots en base: {len(all_pivots)}")
    for p in all_pivots:
        code = p.get('data_source_code', '-')
        print(f"  [{p['id']}] {p['nom']} -> {code}")

    print()
    return created, updated, errors


if __name__ == "__main__":
    init_pivots()
