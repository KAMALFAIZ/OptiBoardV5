"""
Script pour initialiser la structure complete des menus
basee sur la nouvelle architecture 11 sections (109 rapports)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import execute_query, get_db_cursor

# =============================================================================
# STRUCTURE DES MENUS — 11 SECTIONS / 109 RAPPORTS
# =============================================================================
# Chaque item a un "code" unique pour le menu et un "ds_code" pour le lien
# vers le template de datasource. Quand un meme DS apparait dans plusieurs
# sections, le code menu est prefixe pour garantir l'unicite.

MENU_STRUCTURE = [
    # ==================== 1. TABLEAU DE BORD GENERAL (4) ====================
    # type "dashboard" -> /view/{id} (widgets KPI/graphiques)
    # type "pivot-v2"  -> /pivot-v2/{id} (tableau croise dynamique)
    # type "gridview"  -> /grid/{id} (grille AG Grid tabulaire)
    {
        "nom": "Tableau de Bord",
        "code": "dashboard",
        "icon": "LayoutDashboard",
        "ordre": 1,
        "children": [
            {"nom": "KPIs Globaux", "code": "tb-kpi-resume", "ds_code": "DS_KPI_RESUME", "type": "dashboard", "icon": "Gauge", "ordre": 1},
            {"nom": "Comparatif Annuel", "code": "tb-comparatif-annuel", "ds_code": "DS_COMPARATIF_ANNUEL", "type": "dashboard", "icon": "ArrowLeftRight", "ordre": 2},
            {"nom": "Comparatif Annuel Pivot", "code": "tb-comparatif-pivot", "ds_code": "DS_COMPARATIF_ANNUEL_PIVOT", "type": "dashboard", "icon": "ArrowLeftRight", "ordre": 3},
            {"nom": "Comparatif Mensuel", "code": "tb-comparatif-mensuel", "ds_code": "DS_COMPARATIF_MENSUEL", "type": "dashboard", "icon": "CalendarDays", "ordre": 4},
            {"nom": "Top 10 Clients", "code": "tb-top10-clients", "ds_code": "DS_TOP10_CLIENTS", "type": "dashboard", "icon": "Trophy", "ordre": 5},
            {"nom": "Top 10 Articles", "code": "tb-top10-articles", "ds_code": "DS_TOP10_ARTICLES", "type": "dashboard", "icon": "Star", "ordre": 6},
        ]
    },

    # ==================== 2. CHIFFRE D'AFFAIRES (13) ====================
    {
        "nom": "Chiffre d'Affaires",
        "code": "ca",
        "icon": "TrendingUp",
        "ordre": 2,
        "children": [
            {"nom": "CA Global", "code": "ca-global", "ds_code": "DS_VENTES_GLOBAL", "type": "pivot-v2", "icon": "Sigma", "ordre": 1},
            {"nom": "CA par Période", "code": "ca-periode", "ds_code": "DS_VENTES_PAR_MOIS", "type": "pivot-v2", "icon": "Sigma", "ordre": 2},
            {"nom": "CA par Catalogue", "code": "ca-gamme", "ds_code": "DS_VENTES_PAR_CATALOGUE", "type": "pivot-v2", "icon": "Sigma", "ordre": 3},
            {"nom": "CA par Canal", "code": "ca-canal", "ds_code": "DS_VENTES_PAR_CANAL", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 4},
            {"nom": "CA par Zone Géo", "code": "ca-zone", "ds_code": "DS_VENTES_PAR_ZONE", "type": "pivot-v2", "icon": "Sigma", "ordre": 5},
            {"nom": "CA par Commercial", "code": "ca-commercial", "ds_code": "DS_VENTES_PAR_COMMERCIAL", "type": "pivot-v2", "icon": "Sigma", "ordre": 6},
            {"nom": "CA par Client", "code": "ca-client", "ds_code": "DS_VENTES_PAR_CLIENT", "type": "pivot-v2", "icon": "Sigma", "ordre": 7},
            {"nom": "CA par Article", "code": "ca-article", "ds_code": "DS_VENTES_PAR_ARTICLE", "type": "pivot-v2", "icon": "Sigma", "ordre": 8},
            {"nom": "CA par Affaire", "code": "ca-affaire", "ds_code": "DS_VENTES_PAR_AFFAIRE", "type": "pivot-v2", "icon": "Sigma", "ordre": 9},
            {"nom": "CA par Dépôt", "code": "ca-depot", "ds_code": "DS_VENTES_PAR_DEPOT", "type": "pivot-v2", "icon": "Sigma", "ordre": 10},
            {"nom": "CA par Gamme", "code": "ca-gamme-detail", "ds_code": "DS_VENTES_PAR_GAMME", "type": "pivot-v2", "icon": "Sigma", "ordre": 11},
            {"nom": "CA par Catégorie Tarifaire", "code": "ca-cat-tarif", "ds_code": "DS_VENTES_PAR_CATEGORIE_TARIF", "type": "pivot-v2", "icon": "Sigma", "ordre": 12},
            {"nom": "Contribution Marginale (Pareto)", "code": "ca-pareto", "ds_code": "DS_CONTRIBUTION_MARGINALE", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 13},
        ]
    },

    # ==================== 3. DOCUMENTS COMMERCIAUX (8) ====================
    {
        "nom": "Documents Commerciaux",
        "code": "documents",
        "icon": "FileText",
        "ordre": 3,
        "children": [
            {"nom": "Factures", "code": "doc-factures", "ds_code": "DS_FACTURES", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 1},
            {"nom": "Bons de Livraison", "code": "doc-bl", "ds_code": "DS_BONS_LIVRAISON", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 2},
            {"nom": "Bons de Commande", "code": "doc-bc", "ds_code": "DS_BONS_COMMANDE", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 3},
            {"nom": "Devis", "code": "doc-devis", "ds_code": "DS_DEVIS", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 4},
            {"nom": "Avoirs", "code": "doc-avoirs", "ds_code": "DS_AVOIRS", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 5},
            {"nom": "Pipeline Commercial", "code": "doc-pipeline", "ds_code": "DS_PIPELINE_COMMERCIAL", "type": "pivot-v2", "icon": "Sigma", "ordre": 6},
            {"nom": "Délais par Étape", "code": "doc-delais", "ds_code": "DS_DELAIS_ETAPES", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 7},
            {"nom": "Documents en Anomalie", "code": "doc-anomalies", "ds_code": "DS_DOCUMENTS_ANOMALIE", "type": "gridview", "icon": "AlertTriangle", "ordre": 8},
        ]
    },

    # ==================== 4. MARGES & RENTABILITE (9) ====================
    {
        "nom": "Marges & Rentabilité",
        "code": "marges",
        "icon": "PiggyBank",
        "ordre": 4,
        "children": [
            {"nom": "Marge Globale", "code": "marge-globale", "ds_code": "DS_CA_MARGE_DYNAMIQUE", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 1},
            {"nom": "Marge par Client", "code": "marge-client", "ds_code": "DS_CA_AGREGE_CLIENT", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 2},
            {"nom": "Marge par Article", "code": "marge-article", "ds_code": "DS_CA_AGREGE_ARTICLE", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 3},
            {"nom": "Marge par Catalogue", "code": "marge-catalogue", "ds_code": "DS_CA_AGREGE_CATALOGUE", "type": "pivot-v2", "icon": "Sigma", "ordre": 4},
            {"nom": "Marge par Commercial", "code": "marge-commercial", "ds_code": "DS_CA_AGREGE_REPRESENTANT", "type": "pivot-v2", "icon": "Sigma", "ordre": 5},
            {"nom": "Evolution Mensuelle Marge", "code": "marge-evolution", "ds_code": "DS_CA_PAR_MOIS_DYNAMIQUE", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 6},
            {"nom": "Detail Complet CA/Marge", "code": "marge-detail", "ds_code": "DS_CA_DETAIL_COMPLET", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 7},
            {"nom": "Marge par Gamme", "code": "marge-gamme", "ds_code": "DS_MARGE_PAR_GAMME", "type": "pivot-v2", "icon": "Sigma", "ordre": 8},
            {"nom": "Alertes Marge Negative", "code": "marge-negative", "ds_code": "DS_MARGE_NEGATIVE", "type": "gridview", "icon": "AlertTriangle", "ordre": 9},
        ]
    },

    # ==================== 5. ANALYSE CLIENTS (13) ====================
    {
        "nom": "Analyse Clients",
        "code": "clients",
        "icon": "Users",
        "ordre": 5,
        "children": [
            {"nom": "Top Clients CA", "code": "cli-top", "ds_code": "DS_TOP_CLIENTS", "type": "pivot-v2", "icon": "Sigma", "ordre": 1},
            {"nom": "Top 10 Clients", "code": "cli-top10", "ds_code": "DS_TOP10_CLIENTS", "type": "dashboard", "icon": "Trophy", "ordre": 2},
            {"nom": "CA par Client/Mois", "code": "cli-ca-mois", "ds_code": "DS_VENTES_CLIENT_MOIS", "type": "pivot-v2", "icon": "Sigma", "ordre": 3},
            {"nom": "Panier Moyen Client", "code": "cli-panier", "ds_code": "DS_PANIER_MOYEN_CLIENT", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 4},
            {"nom": "Clients Nouveaux", "code": "cli-nouveaux", "ds_code": "DS_CLIENTS_NOUVEAUX", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 5},
            {"nom": "Clients Perdus", "code": "cli-perdus", "ds_code": "DS_CLIENTS_PERDUS", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 6},
            {"nom": "Segmentation ABC", "code": "cli-abc", "ds_code": "DS_SEGMENTATION_ABC", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 7},
            {"nom": "Encours Clients", "code": "cli-encours", "ds_code": "DS_BALANCE_AGEE", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 8},
            {"nom": "Historique Reglements", "code": "cli-reglements", "ds_code": "DS_REGLEMENTS_PAR_CLIENT", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 9},
            {"nom": "Detail Ventes Complet", "code": "cli-detail", "ds_code": "DS_VENTES_DETAIL", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 10},
            {"nom": "Concentration Risque", "code": "cli-concentration", "ds_code": "DS_CONCENTRATION_RISQUE", "type": "gridview", "icon": "AlertTriangle", "ordre": 11},
            {"nom": "Evolution ABC", "code": "cli-evolution-abc", "ds_code": "DS_EVOLUTION_ABC", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 12},
            {"nom": "Matrice Client x Article", "code": "cli-matrice", "ds_code": "DS_MATRICE_CLIENT_ARTICLE", "type": "pivot-v2", "icon": "Sigma", "ordre": 13},
        ]
    },

    # ==================== 6. PERFORMANCE COMMERCIALE (11) ====================
    {
        "nom": "Performance Commerciale",
        "code": "performance",
        "icon": "Award",
        "ordre": 6,
        "children": [
            {"nom": "CA par Commercial", "code": "perf-commercial", "ds_code": "DS_VENTES_PAR_COMMERCIAL", "type": "pivot-v2", "icon": "Sigma", "ordre": 1},
            {"nom": "CA Commercial/Mois", "code": "perf-commercial-mois", "ds_code": "DS_VENTES_COMMERCIAL_MOIS", "type": "pivot-v2", "icon": "Sigma", "ordre": 2},
            {"nom": "Commandes en Cours", "code": "perf-commandes", "ds_code": "DS_COMMANDES_EN_COURS", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 3},
            {"nom": "Taux Transformation Devis", "code": "perf-transformation", "ds_code": "DS_TAUX_TRANSFORMATION", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 4},
            {"nom": "CA par Zone Géo", "code": "perf-zone", "ds_code": "DS_VENTES_PAR_ZONE", "type": "pivot-v2", "icon": "Sigma", "ordre": 5},
            {"nom": "CA par Canal", "code": "perf-canal", "ds_code": "DS_VENTES_PAR_CANAL", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 6},
            {"nom": "Échéances par Commercial", "code": "perf-echeances", "ds_code": "DS_ECHEANCES_PAR_COMMERCIAL", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 7},
            {"nom": "Ranking Commerciaux", "code": "perf-ranking", "ds_code": "DS_CA_AGREGE_REPRESENTANT", "type": "pivot-v2", "icon": "Sigma", "ordre": 8},
            {"nom": "Pipeline Commercial", "code": "perf-pipeline", "ds_code": "DS_PIPELINE_COMMERCIAL", "type": "pivot-v2", "icon": "Sigma", "ordre": 9},
            {"nom": "Délais par Étape", "code": "perf-delais", "ds_code": "DS_DELAIS_ETAPES", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 10},
            {"nom": "Portefeuille Clients", "code": "perf-portefeuille", "ds_code": "DS_PORTEFEUILLE_COMMERCIAL", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 11},
        ]
    },

    # ==================== 7. TENDANCES & SAISONNALITE (8) ====================
    {
        "nom": "Tendances & Saisonnalité",
        "code": "tendances",
        "icon": "LineChart",
        "ordre": 7,
        "children": [
            {"nom": "Evolution CA Mensuel", "code": "tend-ca-mensuel", "ds_code": "DS_VENTES_PAR_MOIS", "type": "pivot-v2", "icon": "Sigma", "ordre": 1},
            {"nom": "Comparatif Annuel", "code": "tend-comparatif", "ds_code": "DS_COMPARATIF_ANNUEL", "type": "dashboard", "icon": "ArrowLeftRight", "ordre": 2},
            {"nom": "Comparatif Mensuel N/N-1", "code": "tend-comparatif-mensuel", "ds_code": "DS_COMPARATIF_MENSUEL", "type": "dashboard", "icon": "CalendarDays", "ordre": 3},
            {"nom": "CA par Article/Mois", "code": "tend-article-mois", "ds_code": "DS_VENTES_ARTICLE_MOIS", "type": "pivot-v2", "icon": "Sigma", "ordre": 4},
            {"nom": "CA par Catalogue/Mois", "code": "tend-catalogue-mois", "ds_code": "DS_VENTES_CATALOGUE_MOIS", "type": "pivot-v2", "icon": "Sigma", "ordre": 5},
            {"nom": "Evolution Prix Achats", "code": "tend-prix-achats", "ds_code": "DS_EVOLUTION_PRIX_ACHATS", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 6},
            {"nom": "Pivot Ventes CA", "code": "tend-pivot", "ds_code": "DS_PIVOT_VENTES_CA", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 7},
            {"nom": "CA par Gamme/Mois", "code": "tend-gamme-mois", "ds_code": "DS_VENTES_GAMME_MOIS", "type": "pivot-v2", "icon": "Sigma", "ordre": 8},
            {"nom": "CA par Famille/Mois", "code": "tend-famille-mois", "ds_code": "DS_VENTES_FAMILLE_MOIS", "type": "pivot-v2", "icon": "Sigma", "ordre": 9},
        ]
    },

    # ==================== 8. RECOUVREMENT & TRESORERIE (10) ====================
    {
        "nom": "Recouvrement & Trésorerie",
        "code": "recouvrement",
        "icon": "Wallet",
        "ordre": 8,
        "children": [
            {"nom": "Balance Âgée", "code": "rec-balance-agee", "ds_code": "DS_BALANCE_AGEE", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 1},
            {"nom": "DSO par Client", "code": "rec-dso", "ds_code": "DS_DSO", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 2},
            {"nom": "Créances Douteuses", "code": "rec-creances", "ds_code": "DS_CREANCES_DOUTEUSES", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 3},
            {"nom": "Échéances Non Réglées", "code": "rec-echeances-nr", "ds_code": "DS_ECHEANCES_NON_REGLEES", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 4},
            {"nom": "Échéances par Commercial", "code": "rec-echeances-comm", "ds_code": "DS_ECHEANCES_PAR_COMMERCIAL", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 5},
            {"nom": "Règlements par Période", "code": "rec-reglements-per", "ds_code": "DS_REGLEMENTS_PAR_PERIODE", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 6},
            {"nom": "Règlements par Mode", "code": "rec-reglements-mode", "ds_code": "DS_REGLEMENTS_PAR_MODE", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 7},
            {"nom": "Factures Non Réglées", "code": "rec-factures-nr", "ds_code": "DS_FACTURES_NON_REGLEES", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 8},
            {"nom": "Prévision Encaissements", "code": "rec-previsions", "ds_code": "DS_PREVISION_ENCAISSEMENTS", "type": "pivot-v2", "icon": "Sigma", "ordre": 9},
            {"nom": "Comportement Paiement", "code": "rec-comportement", "ds_code": "DS_COMPORTEMENT_PAIEMENT", "type": "pivot-v2", "icon": "Sigma", "ordre": 10},
        ]
    },

    # ==================== 9. STOCK & APPROVISIONNEMENT (15) ====================
    {
        "nom": "Stock & Approvisionnement",
        "code": "stocks",
        "icon": "Package",
        "ordre": 9,
        "children": [
            {"nom": "Stock Actuel", "code": "stk-actuel", "ds_code": "DS_STOCK_ACTUEL", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 1},
            {"nom": "Mouvements Globaux", "code": "stk-mvt-global", "ds_code": "DS_MVT_STOCK_GLOBAL", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 2},
            {"nom": "Entrees Stock", "code": "stk-entrees", "ds_code": "DS_MVT_ENTREES", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 3},
            {"nom": "Sorties Stock", "code": "stk-sorties", "ds_code": "DS_MVT_SORTIES", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 4},
            {"nom": "Stock par Dépôt", "code": "stk-depot", "ds_code": "DS_STOCK_PAR_DEPOT", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 5},
            {"nom": "Rotation des Stocks", "code": "stk-rotation", "ds_code": "DS_STOCK_ROTATION", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 6},
            {"nom": "Stock Dormant", "code": "stk-dormant", "ds_code": "DS_STOCK_DORMANT", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 7},
            {"nom": "Mouvements par Article", "code": "stk-mvt-article", "ds_code": "DS_MVT_PAR_ARTICLE", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 8},
            {"nom": "Top Articles Mouvementes", "code": "stk-top-mvt", "ds_code": "DS_TOP_ARTICLES_MVT", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 9},
            {"nom": "Detail Mouvements", "code": "stk-mvt-detail", "ds_code": "DS_MVT_DETAIL", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 10},
            {"nom": "Valorisation Multi-méthodes", "code": "stk-valorisation", "ds_code": "DS_STOCK_VALORISATION", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 11},
            {"nom": "Couverture Stock vs Ventes", "code": "stk-couverture", "ds_code": "DS_STOCK_COUVERTURE", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 12},
            {"nom": "Articles Proches Péremption", "code": "stk-peremption", "ds_code": "DS_STOCK_PEREMPTION", "type": "gridview", "icon": "AlertTriangle", "ordre": 13},
            {"nom": "Transferts Inter-Dépôts", "code": "stk-inter-depots", "ds_code": "DS_MVT_INTER_DEPOTS", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 14},
            {"nom": "Articles Composes", "code": "stk-composes", "ds_code": "DS_ARTICLES_COMPOSES", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 15},
        ]
    },

    # ==================== 10. ACHATS & FOURNISSEURS (12) ====================
    {
        "nom": "Achats & Fournisseurs",
        "code": "achats",
        "icon": "ShoppingBag",
        "ordre": 10,
        "children": [
            {"nom": "Achats Global", "code": "ach-global", "ds_code": "DS_ACHATS_GLOBAL", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 1},
            {"nom": "Achats par Fournisseur", "code": "ach-fournisseur", "ds_code": "DS_ACHATS_PAR_FOURNISSEUR", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 2},
            {"nom": "Achats par Article", "code": "ach-article", "ds_code": "DS_ACHATS_PAR_ARTICLE", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 3},
            {"nom": "Achats par Famille", "code": "ach-famille", "ds_code": "DS_ACHATS_PAR_FAMILLE", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 4},
            {"nom": "Factures Achats", "code": "ach-factures", "ds_code": "DS_FACTURES_ACHATS", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 5},
            {"nom": "Commandes Achats", "code": "ach-commandes", "ds_code": "DS_COMMANDES_ACHATS", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 6},
            {"nom": "Commandes en Cours", "code": "ach-cmd-encours", "ds_code": "DS_COMMANDES_ACHATS_EN_COURS", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 7},
            {"nom": "Top Fournisseurs", "code": "ach-top-fourn", "ds_code": "DS_TOP_FOURNISSEURS", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 8},
            {"nom": "Échéances Achats", "code": "ach-echeances", "ds_code": "DS_ECHEANCES_ACHATS", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 9},
            {"nom": "Comparaison Fournisseurs", "code": "ach-comparaison", "ds_code": "DS_COMPARAISON_FOURNISSEURS", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 10},
            {"nom": "Comparaison Prix Achat/Vente", "code": "ach-vs-ventes", "ds_code": "DS_ACHATS_VS_VENTES", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 11},
            {"nom": "Historique Prix Fournisseur", "code": "ach-historique-prix", "ds_code": "DS_HISTORIQUE_PRIX_FOURNISSEUR", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 12},
        ]
    },

    # ==================== 11. SERVICE & LOGISTIQUE (4) ====================
    {
        "nom": "Service & Logistique",
        "code": "logistique",
        "icon": "Truck",
        "ordre": 11,
        "children": [
            {"nom": "Préparations Livraison", "code": "log-preparations", "ds_code": "DS_PREPARATIONS_LIVRAISON", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 1},
            {"nom": "Bons de Reception", "code": "log-reception", "ds_code": "DS_BONS_RECEPTION", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 2},
            {"nom": "BL Non Facturés", "code": "log-bl-non-fact", "ds_code": "DS_BL_NON_FACTURES", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 3},
            {"nom": "Retours & Avoirs", "code": "log-retours", "ds_code": "DS_AVOIRS", "type": "gridview", "icon": "FileSpreadsheet", "ordre": 4},
        ]
    },
]


def get_datasource_template_id(code):
    """Recupere l'ID d'un template de datasource par son code"""
    try:
        result = execute_query(
            "SELECT id FROM APP_DataSources_Templates WHERE code = ?",
            (code,),
            use_cache=False
        )
        if result:
            return result[0]['id']
        return None
    except Exception as e:
        print(f"  Erreur recherche template {code}: {e}")
        return None


def get_or_create_gridview(ds_code, nom):
    """Recupere ou cree un GridView lie a un datasource template code."""
    try:
        existing = execute_query(
            "SELECT id FROM APP_GridViews WHERE data_source_code = ?",
            (ds_code,),
            use_cache=False
        )
        if existing:
            return existing[0]['id']

        with get_db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO APP_GridViews
                (nom, description, data_source_code, columns_config, page_size, actif, is_public, show_totals)
                VALUES (?, ?, ?, '[]', 50, 1, 1, 1)
            """, (nom, f"Auto-genere depuis {ds_code}", ds_code))
            cursor.execute("SELECT @@IDENTITY AS id")
            gv_id = cursor.fetchone()[0]
            print(f"    [GV] GridView cree id={gv_id} -> {ds_code}")
            return gv_id
    except Exception as e:
        print(f"    [GV ERROR] {ds_code}: {e}")
        return None


def get_or_create_pivot(ds_code, nom):
    """Recupere un Pivot V2 existant par data_source_code, ou en cree un minimal."""
    try:
        existing = execute_query(
            "SELECT id FROM APP_Pivots_V2 WHERE data_source_code = ?",
            (ds_code,),
            use_cache=False
        )
        if existing:
            return existing[0]['id']

        with get_db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO APP_Pivots_V2
                (nom, description, data_source_code, rows_config, columns_config,
                 values_config, filters_config, is_public)
                VALUES (?, ?, ?, '[]', '[]', '[]', '[]', 1)
            """, (nom, f"Auto-genere depuis {ds_code}", ds_code))
            cursor.execute("SELECT @@IDENTITY AS id")
            pv_id = cursor.fetchone()[0]
            print(f"    [PV] Pivot V2 cree id={pv_id} -> {ds_code}")
            return pv_id
    except Exception as e:
        print(f"    [PV ERROR] {ds_code}: {e}")
        return None


def get_or_create_dashboard(ds_code, nom):
    """Recupere ou cree un Dashboard avec un widget KPI auto-genere."""
    try:
        existing = execute_query(
            "SELECT id FROM APP_Dashboards WHERE code = ?",
            (ds_code,),
            use_cache=False
        )
        if existing:
            return existing[0]['id']

        import json
        widgets = json.dumps([{
            "id": "w1",
            "type": "table",
            "title": nom,
            "data_source_code": ds_code,
            "layout": {"x": 0, "y": 0, "w": 12, "h": 6}
        }])

        with get_db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO APP_Dashboards
                (nom, code, description, widgets, is_public, actif)
                VALUES (?, ?, ?, ?, 1, 1)
            """, (nom, ds_code, f"Dashboard auto-genere depuis {ds_code}", widgets))
            cursor.execute("SELECT @@IDENTITY AS id")
            db_id = cursor.fetchone()[0]
            print(f"    [DB] Dashboard cree id={db_id} -> {ds_code}")
            return db_id
    except Exception as e:
        print(f"    [DB ERROR] {ds_code}: {e}")
        return None


def resolve_target(menu_type, ds_code, nom):
    """Resout le target_id selon le type de menu."""
    if menu_type == 'gridview':
        return get_or_create_gridview(ds_code, nom)
    elif menu_type == 'pivot-v2':
        return get_or_create_pivot(ds_code, nom)
    elif menu_type == 'dashboard':
        return get_or_create_dashboard(ds_code, nom)
    return None


def create_menu(menu, parent_id=None):
    """Cree un menu de facon recursive"""
    try:
        existing = execute_query(
            "SELECT id FROM APP_Menus WHERE code = ?",
            (menu['code'],),
            use_cache=False
        )

        if existing:
            menu_id = existing[0]['id']
            print(f"  Menu '{menu['nom']}' existe deja (id={menu_id})")
        else:
            menu_type = menu.get('type', 'folder')
            target_id = None

            if menu_type in ('gridview', 'pivot-v2', 'dashboard'):
                ds_code = menu.get('ds_code', menu['code'])
                target_id = resolve_target(menu_type, ds_code, menu['nom'])
                if not target_id:
                    print(f"  WARN: {menu_type} pour '{ds_code}' non cree")
                    return None

            with get_db_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO APP_Menus (parent_id, nom, code, icon, type, target_id, ordre, actif)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                """, (
                    parent_id,
                    menu['nom'],
                    menu['code'],
                    menu.get('icon', 'Folder'),
                    menu_type,
                    target_id,
                    menu.get('ordre', 1)
                ))
                cursor.execute("SELECT @@IDENTITY AS id")
                menu_id = cursor.fetchone()[0]
                print(f"  Menu '{menu['nom']}' cree (id={menu_id}) [type={menu_type}]")

        if 'children' in menu:
            for child in menu['children']:
                create_menu(child, menu_id)

        return menu_id

    except Exception as e:
        print(f"  ERREUR menu '{menu['nom']}': {e}")
        return None


def delete_old_menus():
    """Supprime les anciens menus pour recreer proprement"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as cnt FROM APP_Menus")
            count = cursor.fetchone()[0]

            if count > 0:
                print(f"  Suppression de {count} menus existants...")
                cursor.execute("DELETE FROM APP_Menus")
                print("  Menus supprimes")
            else:
                print("  Aucun menu existant")

    except Exception as e:
        print(f"  Erreur suppression menus: {e}")


def main():
    print("=" * 60)
    print("INITIALISATION DE LA STRUCTURE DES MENUS")
    print("Architecture 11 sections / 109 rapports")
    print("=" * 60)

    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--reset':
        print("\n[0/2] Suppression des anciens menus...")
        delete_old_menus()

    print("\n[1/2] Verification des templates de datasources...")
    templates = execute_query(
        "SELECT COUNT(*) as cnt FROM APP_DataSources_Templates",
        use_cache=False
    )
    print(f"  {templates[0]['cnt']} templates disponibles")

    print("\n[2/2] Creation des menus...")
    for menu in MENU_STRUCTURE:
        create_menu(menu)

    print("\n" + "=" * 60)
    print("TERMINE!")
    menus_count = execute_query(
        "SELECT COUNT(*) as cnt FROM APP_Menus",
        use_cache=False
    )
    print(f"  {menus_count[0]['cnt']} menus dans la base")

    sections = execute_query(
        "SELECT nom, (SELECT COUNT(*) FROM APP_Menus c WHERE c.parent_id = p.id) as nb_enfants FROM APP_Menus p WHERE parent_id IS NULL ORDER BY ordre",
        use_cache=False
    )
    for s in sections:
        print(f"  {s['nom']}: {s['nb_enfants']} rapports")
    print("=" * 60)


if __name__ == "__main__":
    main()
