"""
Script d'initialisation des rapports de Ventes et Chiffre d'Affaires
=====================================================================
Ce script supprime les anciens rapports et cree les 29 nouveaux rapports
avec la structure de menus correspondante.

Execution: python scripts/init_rapports_ventes.py
"""

import sys
import os

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import execute_query, get_db_cursor
import json

# =============================================================================
# CONFIGURATION - Source de données principale
# =============================================================================

DATASOURCE_VENTES_QUERY = """
SELECT *
FROM VW_Ventes_CA
WHERE [Date_BL] BETWEEN @dateDebut AND @dateFin
  AND (@societe IS NULL OR [Societe] = @societe)
"""

DATASOURCE_PARAMS = [
    # Paramètres de date
    {"name": "dateDebut", "type": "date", "label": "Du", "required": True, "source": "global", "global_key": "dateDebut"},
    {"name": "dateFin", "type": "date", "label": "Au", "required": True, "source": "global", "global_key": "dateFin"},
    # Filtre Société - Liste déroulante simple
    {
        "name": "societe",
        "type": "select",
        "label": "Société",
        "required": False,
        "source": "query",
        "query": "SELECT DISTINCT [Société entête] as value, [Société entête] as label FROM Entête_des_ventes WHERE [Société entête] IS NOT NULL ORDER BY [Société entête]",
        "allow_null": True,
        "null_label": "(Toutes)"
    }
]

# =============================================================================
# DÉFINITION DES RAPPORTS
# =============================================================================

# Catégorie 1: Rapports Synthétiques (Dashboard)
DASHBOARDS = [
    {
        "id": 1,
        "nom": "Tableau de Bord CA Global",
        "description": "Vue instantanée des KPIs clés: CA, Marge, Clients actifs, Évolution N/N-1",
        "widgets": [
            {"id": "kpi-ca", "type": "kpi", "title": "Chiffre d'Affaires", "x": 0, "y": 0, "w": 4, "h": 2,
             "config": {"value_field": "Montant", "aggregation": "SUM", "format": "currency", "color": "blue", "icon": "TrendingUp"}},
            {"id": "kpi-marge", "type": "kpi", "title": "Marge Brute", "x": 4, "y": 0, "w": 4, "h": 2,
             "config": {"value_field": "Marge", "aggregation": "SUM", "format": "currency", "color": "green", "icon": "DollarSign"}},
            {"id": "kpi-taux-marge", "type": "kpi", "title": "Taux de Marge", "x": 8, "y": 0, "w": 4, "h": 2,
             "config": {"value_field": "Marge", "value_field_2": "Montant", "aggregation": "RATIO", "format": "percent", "color": "purple", "icon": "Percent"}},
            {"id": "kpi-clients", "type": "kpi", "title": "Clients Actifs", "x": 0, "y": 2, "w": 4, "h": 2,
             "config": {"value_field": "Code_Client", "aggregation": "COUNT_DISTINCT", "format": "number", "color": "orange", "icon": "Users"}},
            {"id": "kpi-transactions", "type": "kpi", "title": "Transactions", "x": 4, "y": 2, "w": 4, "h": 2,
             "config": {"value_field": "Numero_BL", "aggregation": "COUNT_DISTINCT", "format": "number", "color": "cyan", "icon": "FileText"}},
            {"id": "kpi-panier", "type": "kpi", "title": "Panier Moyen", "x": 8, "y": 2, "w": 4, "h": 2,
             "config": {"value_field": "Montant", "value_field_2": "Numero_BL", "aggregation": "AVG_PER", "format": "currency", "color": "pink", "icon": "ShoppingCart"}},
            {"id": "chart-evolution", "type": "chart_line", "title": "Évolution Mensuelle du CA", "x": 0, "y": 4, "w": 8, "h": 4,
             "config": {"x_field": "Mois", "y_field": "Montant", "aggregation": "SUM", "group_by": "Annee", "color": "#3b82f6"}},
            {"id": "chart-gamme", "type": "chart_pie", "title": "Répartition par Gamme", "x": 8, "y": 4, "w": 4, "h": 4,
             "config": {"label_field": "Catalogue1", "value_field": "Montant", "aggregation": "SUM"}}
        ]
    },
    {
        "id": 2,
        "nom": "Synthèse Mensuelle CA",
        "description": "Bilan mensuel avec comparatifs et objectifs",
        "widgets": [
            {"id": "kpi-ca-mois", "type": "kpi_compare", "title": "CA du Mois", "x": 0, "y": 0, "w": 4, "h": 2,
             "config": {"value_field": "Montant", "compare_period": "M-1", "format": "currency"}},
            {"id": "kpi-evol-m", "type": "kpi", "title": "Évolution vs M-1", "x": 4, "y": 0, "w": 4, "h": 2,
             "config": {"calculation": "evolution_m1", "format": "percent", "color": "green"}},
            {"id": "kpi-evol-n", "type": "kpi", "title": "Évolution vs N-1", "x": 8, "y": 0, "w": 4, "h": 2,
             "config": {"calculation": "evolution_n1", "format": "percent", "color": "blue"}},
            {"id": "chart-mensuel", "type": "chart_bar", "title": "CA par Mois", "x": 0, "y": 2, "w": 12, "h": 4,
             "config": {"x_field": "Mois", "y_field": "Montant", "aggregation": "SUM", "color": "#3b82f6"}},
            {"id": "table-detail", "type": "table", "title": "Détail Mensuel", "x": 0, "y": 6, "w": 12, "h": 4,
             "config": {"columns": ["Mois", "CA", "Marge", "Taux_Marge", "Nb_Clients", "Nb_BL"], "pageSize": 12}}
        ]
    },
    {
        "id": 3,
        "nom": "Rapport Annuel CA",
        "description": "Bilan complet de l'exercice fiscal",
        "widgets": [
            {"id": "kpi-ca-annuel", "type": "kpi", "title": "CA Annuel", "x": 0, "y": 0, "w": 3, "h": 2,
             "config": {"value_field": "Montant", "aggregation": "SUM", "format": "currency", "color": "blue"}},
            {"id": "kpi-marge-annuel", "type": "kpi", "title": "Marge Annuelle", "x": 3, "y": 0, "w": 3, "h": 2,
             "config": {"value_field": "Marge", "aggregation": "SUM", "format": "currency", "color": "green"}},
            {"id": "kpi-clients-annuel", "type": "kpi", "title": "Clients", "x": 6, "y": 0, "w": 3, "h": 2,
             "config": {"value_field": "Code_Client", "aggregation": "COUNT_DISTINCT", "format": "number"}},
            {"id": "kpi-evol-annuel", "type": "kpi_compare", "title": "Évolution N/N-1", "x": 9, "y": 0, "w": 3, "h": 2,
             "config": {"calculation": "evolution_n1", "format": "percent"}},
            {"id": "chart-evol-annuel", "type": "chart_line", "title": "Évolution Mensuelle", "x": 0, "y": 2, "w": 8, "h": 4,
             "config": {"x_field": "Mois", "y_field": "Montant", "aggregation": "SUM"}},
            {"id": "chart-top-gamme", "type": "chart_bar", "title": "Top Gammes", "x": 8, "y": 2, "w": 4, "h": 4,
             "config": {"x_field": "Catalogue1", "y_field": "Montant", "aggregation": "SUM", "limit": 5}}
        ]
    },
    {
        "id": 14,
        "nom": "Évolution Mensuelle CA",
        "description": "Visualisation de la tendance du CA mois par mois",
        "widgets": [
            {"id": "chart-evol-principal", "type": "chart_line", "title": "Évolution du CA", "x": 0, "y": 0, "w": 12, "h": 5,
             "config": {"x_field": "Mois", "y_field": "Montant", "aggregation": "SUM", "group_by": "Annee", "show_legend": True}},
            {"id": "table-evol", "type": "table", "title": "Données Mensuelles", "x": 0, "y": 5, "w": 12, "h": 4,
             "config": {"columns": ["Annee", "Mois", "CA", "Marge", "Nb_Clients", "Evol_M1"], "pageSize": 12}}
        ]
    },
    {
        "id": 26,
        "nom": "Bilan CA Annuel",
        "description": "Synthèse complète de l'exercice pour clôture",
        "widgets": [
            {"id": "kpi-resume-1", "type": "kpi", "title": "CA Total", "x": 0, "y": 0, "w": 2, "h": 2,
             "config": {"value_field": "Montant", "aggregation": "SUM", "format": "currency"}},
            {"id": "kpi-resume-2", "type": "kpi", "title": "Marge Totale", "x": 2, "y": 0, "w": 2, "h": 2,
             "config": {"value_field": "Marge", "aggregation": "SUM", "format": "currency"}},
            {"id": "kpi-resume-3", "type": "kpi", "title": "Taux Marge", "x": 4, "y": 0, "w": 2, "h": 2,
             "config": {"calculation": "taux_marge", "format": "percent"}},
            {"id": "kpi-resume-4", "type": "kpi", "title": "Clients", "x": 6, "y": 0, "w": 2, "h": 2,
             "config": {"value_field": "Code_Client", "aggregation": "COUNT_DISTINCT"}},
            {"id": "kpi-resume-5", "type": "kpi", "title": "Transactions", "x": 8, "y": 0, "w": 2, "h": 2,
             "config": {"value_field": "Numero_BL", "aggregation": "COUNT_DISTINCT"}},
            {"id": "kpi-resume-6", "type": "kpi_compare", "title": "Évol. N-1", "x": 10, "y": 0, "w": 2, "h": 2,
             "config": {"calculation": "evolution_n1", "format": "percent"}},
            {"id": "chart-bilan-mensuel", "type": "chart_bar", "title": "CA Mensuel", "x": 0, "y": 2, "w": 6, "h": 4,
             "config": {"x_field": "Mois", "y_field": "Montant", "aggregation": "SUM"}},
            {"id": "chart-bilan-gamme", "type": "chart_pie", "title": "Par Gamme", "x": 6, "y": 2, "w": 3, "h": 4,
             "config": {"label_field": "Catalogue1", "value_field": "Montant"}},
            {"id": "chart-bilan-commercial", "type": "chart_pie", "title": "Par Commercial", "x": 9, "y": 2, "w": 3, "h": 4,
             "config": {"label_field": "Commercial", "value_field": "Montant"}}
        ]
    },
    {
        "id": 29,
        "nom": "Rapport de Performance Globale",
        "description": "Consolidation toutes dimensions pour la direction",
        "widgets": [
            {"id": "kpi-perf-ca", "type": "kpi", "title": "CA Global", "x": 0, "y": 0, "w": 4, "h": 2,
             "config": {"value_field": "Montant", "aggregation": "SUM", "format": "currency", "color": "blue"}},
            {"id": "kpi-perf-marge", "type": "kpi", "title": "Marge Globale", "x": 4, "y": 0, "w": 4, "h": 2,
             "config": {"value_field": "Marge", "aggregation": "SUM", "format": "currency", "color": "green"}},
            {"id": "kpi-perf-evol", "type": "kpi_compare", "title": "Évolution", "x": 8, "y": 0, "w": 4, "h": 2,
             "config": {"calculation": "evolution_n1", "format": "percent"}},
            {"id": "table-perf-societe", "type": "table", "title": "Performance par Société", "x": 0, "y": 2, "w": 6, "h": 3,
             "config": {"group_by": "Societe", "columns": ["Societe", "CA", "Marge", "Pct_CA"]}},
            {"id": "table-perf-gamme", "type": "table", "title": "Performance par Gamme", "x": 6, "y": 2, "w": 6, "h": 3,
             "config": {"group_by": "Catalogue1", "columns": ["Catalogue1", "CA", "Marge", "Pct_CA"]}},
            {"id": "chart-perf-evol", "type": "chart_line", "title": "Évolution Mensuelle", "x": 0, "y": 5, "w": 12, "h": 4,
             "config": {"x_field": "Mois", "y_field": "Montant", "group_by": "Annee"}}
        ]
    }
]

# Catégorie 2-3: Rapports Pivot
PIVOTS = [
    # Cat 2: Par Dimension
    {"id": 4, "nom": "CA par Gamme de Produits", "description": "Analyse du CA par ligne de produits (Catalogue 1)",
     "rows": ["Catalogue1"], "columns": [], "values": [
         {"field": "Montant", "aggregation": "SUM", "alias": "CA"},
         {"field": "Marge", "aggregation": "SUM", "alias": "Marge"},
         {"field": "Quantite", "aggregation": "SUM", "alias": "Qte"},
         {"field": "Code_Client", "aggregation": "COUNT_DISTINCT", "alias": "Nb_Clients"}
     ]},
    {"id": 5, "nom": "CA par Canal de Distribution", "description": "Analyse par catégorie client",
     "rows": ["Categorie_Client"], "columns": [], "values": [
         {"field": "Montant", "aggregation": "SUM", "alias": "CA"},
         {"field": "Marge", "aggregation": "SUM", "alias": "Marge"},
         {"field": "Code_Client", "aggregation": "COUNT_DISTINCT", "alias": "Nb_Clients"}
     ]},
    {"id": 6, "nom": "CA par Zone Géographique", "description": "Performance par région",
     "rows": ["Region"], "columns": [], "values": [
         {"field": "Montant", "aggregation": "SUM", "alias": "CA"},
         {"field": "Marge", "aggregation": "SUM", "alias": "Marge"},
         {"field": "Code_Client", "aggregation": "COUNT_DISTINCT", "alias": "Nb_Clients"}
     ]},
    {"id": 7, "nom": "CA par Commercial", "description": "Performance de l'équipe commerciale",
     "rows": ["Commercial"], "columns": [], "values": [
         {"field": "Montant", "aggregation": "SUM", "alias": "CA"},
         {"field": "Marge", "aggregation": "SUM", "alias": "Marge"},
         {"field": "Code_Client", "aggregation": "COUNT_DISTINCT", "alias": "Nb_Clients"},
         {"field": "Numero_BL", "aggregation": "COUNT_DISTINCT", "alias": "Nb_BL"}
     ]},
    {"id": 8, "nom": "CA par Société", "description": "Consolidation par entité du groupe",
     "rows": ["Societe"], "columns": ["Mois"], "values": [
         {"field": "Montant", "aggregation": "SUM", "alias": "CA"},
         {"field": "Marge", "aggregation": "SUM", "alias": "Marge"}
     ]},

    # Cat 4: Évolution & Tendances
    {"id": 15, "nom": "Comparatif N/N-1", "description": "Comparaison année courante vs précédente",
     "rows": ["Mois"], "columns": ["Annee"], "values": [
         {"field": "Montant", "aggregation": "SUM", "alias": "CA"},
         {"field": "Marge", "aggregation": "SUM", "alias": "Marge"}
     ]},
    {"id": 16, "nom": "Saisonnalité des Ventes", "description": "Analyse des patterns saisonniers",
     "rows": ["Mois"], "columns": ["Annee"], "values": [
         {"field": "Montant", "aggregation": "SUM", "alias": "CA"},
         {"field": "Montant", "aggregation": "AVG", "alias": "CA_Moyen"}
     ]},
    {"id": 17, "nom": "Tendance par Gamme", "description": "Évolution du mix produit dans le temps",
     "rows": ["Annee", "Mois"], "columns": ["Catalogue1"], "values": [
         {"field": "Montant", "aggregation": "SUM", "alias": "CA"}
     ]},

    # Cat 6: Marges & Rentabilité
    {"id": 22, "nom": "Analyse des Marges par Gamme", "description": "Rentabilité par ligne de produits",
     "rows": ["Catalogue1"], "columns": [], "values": [
         {"field": "Montant", "aggregation": "SUM", "alias": "CA"},
         {"field": "Cout_Marchandise", "aggregation": "SUM", "alias": "Cout"},
         {"field": "Marge", "aggregation": "SUM", "alias": "Marge"}
     ]},
    {"id": 23, "nom": "Marges par Commercial", "description": "Rentabilité par vendeur",
     "rows": ["Commercial"], "columns": [], "values": [
         {"field": "Montant", "aggregation": "SUM", "alias": "CA"},
         {"field": "Marge", "aggregation": "SUM", "alias": "Marge"},
         {"field": "Code_Client", "aggregation": "COUNT_DISTINCT", "alias": "Nb_Clients"}
     ]},

    # Cat 7: Fin d'Année
    {"id": 27, "nom": "Comparatif Multi-Années", "description": "Tendance sur plusieurs années",
     "rows": ["Annee"], "columns": [], "values": [
         {"field": "Montant", "aggregation": "SUM", "alias": "CA"},
         {"field": "Marge", "aggregation": "SUM", "alias": "Marge"},
         {"field": "Code_Client", "aggregation": "COUNT_DISTINCT", "alias": "Nb_Clients"}
     ]},
    {"id": 28, "nom": "Analyse Pareto (80/20)", "description": "Clients/Produits générant 80% du CA",
     "rows": ["Code_Client", "Nom_Client"], "columns": [], "values": [
         {"field": "Montant", "aggregation": "SUM", "alias": "CA"},
         {"field": "Marge", "aggregation": "SUM", "alias": "Marge"}
     ]}
]

# Catégorie 3, 5, 6: Rapports GridView
GRIDVIEWS = [
    # Cat 3: Top / Classements
    {"id": 9, "nom": "Top Clients par CA", "description": "Classement des meilleurs clients",
     "columns": [
         {"field": "Code_Client", "header": "Code", "width": 100, "sortable": True, "visible": True},
         {"field": "Nom_Client", "header": "Client", "width": 200, "sortable": True, "visible": True},
         {"field": "Commercial", "header": "Commercial", "width": 150, "sortable": True, "visible": True},
         {"field": "Region", "header": "Région", "width": 120, "sortable": True, "visible": True},
         {"field": "CA", "header": "CA", "width": 120, "format": "currency", "align": "right", "visible": True},
         {"field": "Marge", "header": "Marge", "width": 120, "format": "currency", "align": "right", "visible": True},
         {"field": "Taux_Marge", "header": "Taux", "width": 80, "format": "percent", "align": "right", "visible": True},
         {"field": "Nb_BL", "header": "Nb BL", "width": 80, "align": "right", "visible": True}
     ],
     "default_sort": {"field": "CA", "direction": "desc"}, "page_size": 50, "show_totals": True, "total_columns": ["CA", "Marge"]},

    {"id": 10, "nom": "Top Produits par CA", "description": "Produits les plus vendus en valeur",
     "columns": [
         {"field": "Code_Article", "header": "Code", "width": 120, "sortable": True, "visible": True},
         {"field": "Designation", "header": "Désignation", "width": 250, "sortable": True, "visible": True},
         {"field": "Famille", "header": "Famille", "width": 150, "sortable": True, "visible": True},
         {"field": "Catalogue1", "header": "Gamme", "width": 120, "sortable": True, "visible": True},
         {"field": "CA", "header": "CA", "width": 120, "format": "currency", "align": "right", "visible": True},
         {"field": "Quantite", "header": "Qté", "width": 80, "format": "number", "align": "right", "visible": True},
         {"field": "Marge", "header": "Marge", "width": 120, "format": "currency", "align": "right", "visible": True},
         {"field": "Nb_Clients", "header": "Clients", "width": 80, "align": "right", "visible": True}
     ],
     "default_sort": {"field": "CA", "direction": "desc"}, "page_size": 50, "show_totals": True, "total_columns": ["CA", "Marge", "Quantite"]},

    {"id": 11, "nom": "Top Produits par Quantité", "description": "Produits les plus vendus en volume",
     "columns": [
         {"field": "Code_Article", "header": "Code", "width": 120, "visible": True},
         {"field": "Designation", "header": "Désignation", "width": 250, "visible": True},
         {"field": "Catalogue1", "header": "Gamme", "width": 120, "visible": True},
         {"field": "Quantite", "header": "Quantité", "width": 100, "format": "number", "align": "right", "visible": True},
         {"field": "CA", "header": "CA", "width": 120, "format": "currency", "align": "right", "visible": True},
         {"field": "Prix_Moyen", "header": "Prix Moy.", "width": 100, "format": "currency", "align": "right", "visible": True}
     ],
     "default_sort": {"field": "Quantite", "direction": "desc"}, "page_size": 50},

    {"id": 12, "nom": "Clients en Croissance", "description": "Clients avec meilleure progression N/N-1",
     "columns": [
         {"field": "Code_Client", "header": "Code", "width": 100, "visible": True},
         {"field": "Nom_Client", "header": "Client", "width": 200, "visible": True},
         {"field": "Commercial", "header": "Commercial", "width": 150, "visible": True},
         {"field": "CA_N", "header": "CA N", "width": 120, "format": "currency", "align": "right", "visible": True},
         {"field": "CA_N1", "header": "CA N-1", "width": 120, "format": "currency", "align": "right", "visible": True},
         {"field": "Progression", "header": "Progression", "width": 120, "format": "currency", "align": "right", "visible": True},
         {"field": "Evolution", "header": "Évolution %", "width": 100, "format": "percent", "align": "right", "visible": True}
     ],
     "default_sort": {"field": "Evolution", "direction": "desc"}, "page_size": 50},

    {"id": 13, "nom": "Clients en Déclin", "description": "Clients avec baisse significative",
     "columns": [
         {"field": "Code_Client", "header": "Code", "width": 100, "visible": True},
         {"field": "Nom_Client", "header": "Client", "width": 200, "visible": True},
         {"field": "Commercial", "header": "Commercial", "width": 150, "visible": True},
         {"field": "CA_N", "header": "CA N", "width": 120, "format": "currency", "align": "right", "visible": True},
         {"field": "CA_N1", "header": "CA N-1", "width": 120, "format": "currency", "align": "right", "visible": True},
         {"field": "Perte", "header": "Perte", "width": 120, "format": "currency", "align": "right", "visible": True},
         {"field": "Declin", "header": "Déclin %", "width": 100, "format": "percent", "align": "right", "visible": True}
     ],
     "default_sort": {"field": "Declin", "direction": "asc"}, "page_size": 50},

    # Cat 5: Détaillés
    {"id": 18, "nom": "Détail Ventes par Mois", "description": "Liste exhaustive des transactions",
     "columns": [
         {"field": "Date_BL", "header": "Date", "width": 100, "format": "date", "visible": True},
         {"field": "Numero_BL", "header": "N° BL", "width": 100, "visible": True},
         {"field": "Societe", "header": "Société", "width": 100, "visible": True},
         {"field": "Code_Client", "header": "Code Clt", "width": 100, "visible": True},
         {"field": "Nom_Client", "header": "Client", "width": 180, "visible": True},
         {"field": "Code_Article", "header": "Code Art", "width": 100, "visible": True},
         {"field": "Designation", "header": "Article", "width": 200, "visible": True},
         {"field": "Catalogue1", "header": "Gamme", "width": 100, "visible": True},
         {"field": "Commercial", "header": "Commercial", "width": 120, "visible": True},
         {"field": "Quantite", "header": "Qté", "width": 70, "format": "number", "align": "right", "visible": True},
         {"field": "Prix_Unitaire", "header": "PU", "width": 90, "format": "currency", "align": "right", "visible": True},
         {"field": "Montant_HT", "header": "MT HT", "width": 100, "format": "currency", "align": "right", "visible": True},
         {"field": "Montant_TTC", "header": "MT TTC", "width": 100, "format": "currency", "align": "right", "visible": True},
         {"field": "Marge", "header": "Marge", "width": 100, "format": "currency", "align": "right", "visible": True}
     ],
     "default_sort": {"field": "Date_BL", "direction": "desc"}, "page_size": 100, "show_totals": True,
     "total_columns": ["Montant_HT", "Montant_TTC", "Marge", "Quantite"]},

    {"id": 19, "nom": "Fiche Client Détaillée", "description": "Historique complet d'un client",
     "columns": [
         {"field": "Date_BL", "header": "Date", "width": 100, "format": "date", "visible": True},
         {"field": "Numero_BL", "header": "N° BL", "width": 100, "visible": True},
         {"field": "Code_Article", "header": "Code", "width": 100, "visible": True},
         {"field": "Designation", "header": "Article", "width": 200, "visible": True},
         {"field": "Catalogue1", "header": "Gamme", "width": 120, "visible": True},
         {"field": "Quantite", "header": "Qté", "width": 70, "format": "number", "align": "right", "visible": True},
         {"field": "Montant", "header": "Montant", "width": 110, "format": "currency", "align": "right", "visible": True},
         {"field": "Marge", "header": "Marge", "width": 100, "format": "currency", "align": "right", "visible": True}
     ],
     "default_sort": {"field": "Date_BL", "direction": "desc"}, "page_size": 50, "show_totals": True,
     "total_columns": ["Montant", "Marge", "Quantite"]},

    {"id": 20, "nom": "Fiche Produit Détaillée", "description": "Historique des ventes d'un article",
     "columns": [
         {"field": "Date_BL", "header": "Date", "width": 100, "format": "date", "visible": True},
         {"field": "Numero_BL", "header": "N° BL", "width": 100, "visible": True},
         {"field": "Code_Client", "header": "Code Clt", "width": 100, "visible": True},
         {"field": "Nom_Client", "header": "Client", "width": 180, "visible": True},
         {"field": "Commercial", "header": "Commercial", "width": 120, "visible": True},
         {"field": "Quantite", "header": "Qté", "width": 70, "format": "number", "align": "right", "visible": True},
         {"field": "Prix_Unitaire", "header": "PU", "width": 90, "format": "currency", "align": "right", "visible": True},
         {"field": "Montant", "header": "Montant", "width": 110, "format": "currency", "align": "right", "visible": True},
         {"field": "Cout_Marchandise", "header": "Coût", "width": 100, "format": "currency", "align": "right", "visible": True},
         {"field": "Marge", "header": "Marge", "width": 100, "format": "currency", "align": "right", "visible": True}
     ],
     "default_sort": {"field": "Date_BL", "direction": "desc"}, "page_size": 50, "show_totals": True,
     "total_columns": ["Montant", "Marge", "Quantite", "Cout_Marchandise"]},

    {"id": 21, "nom": "Performance Commercial Détaillée", "description": "Détail complet d'un commercial",
     "columns": [
         {"field": "Code_Client", "header": "Code Clt", "width": 100, "visible": True},
         {"field": "Nom_Client", "header": "Client", "width": 180, "visible": True},
         {"field": "Region", "header": "Région", "width": 100, "visible": True},
         {"field": "CA", "header": "CA", "width": 120, "format": "currency", "align": "right", "visible": True},
         {"field": "Marge", "header": "Marge", "width": 110, "format": "currency", "align": "right", "visible": True},
         {"field": "Taux_Marge", "header": "Taux", "width": 80, "format": "percent", "align": "right", "visible": True},
         {"field": "Nb_BL", "header": "Nb BL", "width": 70, "align": "right", "visible": True}
     ],
     "default_sort": {"field": "CA", "direction": "desc"}, "page_size": 50, "show_totals": True,
     "total_columns": ["CA", "Marge"]},

    # Cat 6: Marges
    {"id": 24, "nom": "Produits à Faible Marge", "description": "Articles sous un seuil de rentabilité",
     "columns": [
         {"field": "Code_Article", "header": "Code", "width": 100, "visible": True},
         {"field": "Designation", "header": "Désignation", "width": 220, "visible": True},
         {"field": "Catalogue1", "header": "Gamme", "width": 120, "visible": True},
         {"field": "CA", "header": "CA", "width": 110, "format": "currency", "align": "right", "visible": True},
         {"field": "Cout", "header": "Coût", "width": 110, "format": "currency", "align": "right", "visible": True},
         {"field": "Marge", "header": "Marge", "width": 110, "format": "currency", "align": "right", "visible": True},
         {"field": "Taux_Marge", "header": "Taux Marge", "width": 90, "format": "percent", "align": "right", "visible": True},
         {"field": "Quantite", "header": "Qté", "width": 70, "format": "number", "align": "right", "visible": True}
     ],
     "default_sort": {"field": "Taux_Marge", "direction": "asc"}, "page_size": 50},

    {"id": 25, "nom": "Clients les Plus Rentables", "description": "Classement par marge générée",
     "columns": [
         {"field": "Code_Client", "header": "Code", "width": 100, "visible": True},
         {"field": "Nom_Client", "header": "Client", "width": 200, "visible": True},
         {"field": "Commercial", "header": "Commercial", "width": 130, "visible": True},
         {"field": "CA", "header": "CA", "width": 110, "format": "currency", "align": "right", "visible": True},
         {"field": "Marge", "header": "Marge", "width": 110, "format": "currency", "align": "right", "visible": True},
         {"field": "Taux_Marge", "header": "Taux", "width": 80, "format": "percent", "align": "right", "visible": True},
         {"field": "Pct_Marge_Total", "header": "% Marge Tot.", "width": 100, "format": "percent", "align": "right", "visible": True}
     ],
     "default_sort": {"field": "Marge", "direction": "desc"}, "page_size": 50, "show_totals": True,
     "total_columns": ["CA", "Marge"]}
]

# Structure des menus
MENUS = [
    # Racines
    {"parent_id": None, "nom": "Ventes & CA", "code": "ventes-ca", "icon": "TrendingUp", "type": "folder", "ordre": 1},

    # Sous-menus de Ventes & CA (seront créés avec parent_id dynamique)
    {"parent_code": "ventes-ca", "nom": "Tableaux de Bord", "code": "ventes-dashboards", "icon": "LayoutDashboard", "type": "folder", "ordre": 1},
    {"parent_code": "ventes-ca", "nom": "Analyses par Dimension", "code": "ventes-dimensions", "icon": "PieChart", "type": "folder", "ordre": 2},
    {"parent_code": "ventes-ca", "nom": "Classements & Top", "code": "ventes-tops", "icon": "Award", "type": "folder", "ordre": 3},
    {"parent_code": "ventes-ca", "nom": "Évolution & Tendances", "code": "ventes-evolution", "icon": "LineChart", "type": "folder", "ordre": 4},
    {"parent_code": "ventes-ca", "nom": "Détails & Fiches", "code": "ventes-details", "icon": "FileText", "type": "folder", "ordre": 5},
    {"parent_code": "ventes-ca", "nom": "Marges & Rentabilité", "code": "ventes-marges", "icon": "DollarSign", "type": "folder", "ordre": 6},
    {"parent_code": "ventes-ca", "nom": "Rapports Fin d'Année", "code": "ventes-fin-annee", "icon": "Calendar", "type": "folder", "ordre": 7},
]

# Mapping rapports -> menus
RAPPORT_MENU_MAPPING = [
    # Tableaux de Bord
    {"parent_code": "ventes-dashboards", "type": "dashboard", "rapport_id": 1, "ordre": 1},
    {"parent_code": "ventes-dashboards", "type": "dashboard", "rapport_id": 2, "ordre": 2},
    {"parent_code": "ventes-dashboards", "type": "dashboard", "rapport_id": 3, "ordre": 3},

    # Analyses par Dimension (Pivots)
    {"parent_code": "ventes-dimensions", "type": "pivot", "rapport_id": 4, "ordre": 1},
    {"parent_code": "ventes-dimensions", "type": "pivot", "rapport_id": 5, "ordre": 2},
    {"parent_code": "ventes-dimensions", "type": "pivot", "rapport_id": 6, "ordre": 3},
    {"parent_code": "ventes-dimensions", "type": "pivot", "rapport_id": 7, "ordre": 4},
    {"parent_code": "ventes-dimensions", "type": "pivot", "rapport_id": 8, "ordre": 5},

    # Classements & Top (GridViews)
    {"parent_code": "ventes-tops", "type": "gridview", "rapport_id": 9, "ordre": 1},
    {"parent_code": "ventes-tops", "type": "gridview", "rapport_id": 10, "ordre": 2},
    {"parent_code": "ventes-tops", "type": "gridview", "rapport_id": 11, "ordre": 3},
    {"parent_code": "ventes-tops", "type": "gridview", "rapport_id": 12, "ordre": 4},
    {"parent_code": "ventes-tops", "type": "gridview", "rapport_id": 13, "ordre": 5},

    # Évolution & Tendances
    {"parent_code": "ventes-evolution", "type": "dashboard", "rapport_id": 14, "ordre": 1},
    {"parent_code": "ventes-evolution", "type": "pivot", "rapport_id": 15, "ordre": 2},
    {"parent_code": "ventes-evolution", "type": "pivot", "rapport_id": 16, "ordre": 3},
    {"parent_code": "ventes-evolution", "type": "pivot", "rapport_id": 17, "ordre": 4},

    # Détails & Fiches (GridViews)
    {"parent_code": "ventes-details", "type": "gridview", "rapport_id": 18, "ordre": 1},
    {"parent_code": "ventes-details", "type": "gridview", "rapport_id": 19, "ordre": 2},
    {"parent_code": "ventes-details", "type": "gridview", "rapport_id": 20, "ordre": 3},
    {"parent_code": "ventes-details", "type": "gridview", "rapport_id": 21, "ordre": 4},

    # Marges & Rentabilité
    {"parent_code": "ventes-marges", "type": "pivot", "rapport_id": 22, "ordre": 1},
    {"parent_code": "ventes-marges", "type": "pivot", "rapport_id": 23, "ordre": 2},
    {"parent_code": "ventes-marges", "type": "gridview", "rapport_id": 24, "ordre": 3},
    {"parent_code": "ventes-marges", "type": "gridview", "rapport_id": 25, "ordre": 4},

    # Rapports Fin d'Année
    {"parent_code": "ventes-fin-annee", "type": "dashboard", "rapport_id": 26, "ordre": 1},
    {"parent_code": "ventes-fin-annee", "type": "pivot", "rapport_id": 27, "ordre": 2},
    {"parent_code": "ventes-fin-annee", "type": "pivot", "rapport_id": 28, "ordre": 3},
    {"parent_code": "ventes-fin-annee", "type": "dashboard", "rapport_id": 29, "ordre": 4},
]


# =============================================================================
# FONCTIONS D'EXÉCUTION
# =============================================================================

def create_sql_view():
    """Cree une vue SQL pour les ventes dans la base de donnees"""
    print("\n📋 Creation de la vue SQL VW_Ventes_CA...")

    drop_view = "IF OBJECT_ID('VW_Ventes_CA', 'V') IS NOT NULL DROP VIEW VW_Ventes_CA"

    create_view = """
    CREATE VIEW VW_Ventes_CA AS
    SELECT
        e.[Type Document],
        e.[Société entête] AS [Societe],
        e.Souche,
        e.Statut,
        e.[Intitulé client] AS [Nom_Client],
        e.[Code client] AS [Code_Client],
        e.[Nom représentant] AS [Commercial],
        e.Date AS [Date_Document],
        e.[N° pièce] AS [Numero_Piece],
        e.Etat,
        e.[Code d'affaire] AS [Code_Affaire],
        e.[Intitulé affaire] AS [Nom_Affaire],
        e.Dépôt AS [Depot],
        e.Devise,
        l.[N° Pièce BL] AS [Numero_BL],
        l.[Date BL] AS [Date_BL],
        l.[N° Pièce BC] AS [Numero_BC],
        l.[Date BC] AS [Date_BC],
        a.[Code Article] AS [Code_Article],
        a.[Désignation Article] AS [Designation],
        a.[Code Famille] AS [Code_Famille],
        a.[Intitulé famille] AS [Famille],
        a.[Libellé Gamme 1] AS [Gamme1],
        a.[Libellé Gamme 2] AS [Gamme2],
        a.[Catalogue 1] AS [Catalogue1],
        a.[Catalogue 2] AS [Catalogue2],
        a.[Catalogue 3] AS [Catalogue3],
        a.[Catalogue 4] AS [Catalogue4],
        a.[Unité Vente] AS [Unite_Vente],
        c.Ville,
        c.Région AS [Region],
        c.[Catégorie tarifaire] AS [Categorie_Client],
        l.Quantité AS [Quantite],
        l.[Prix unitaire] AS [Prix_Unitaire],
        l.[Prix unitaire TTC] AS [Prix_Unitaire_TTC],
        l.[Montant HT Net] AS [Montant_HT],
        l.[Montant TTC Net] AS [Montant_TTC],
        l.CMUP,
        l.[Prix de revient] AS [Prix_Revient],
        ISNULL(ms.[DPA-Période], 0) AS [DPA_Periode],
        ISNULL(ms.[DPA-Vente], 0) AS [DPA_Vente],
        ISNULL(ms.[DPR-Vente], 0) AS [DPR_Vente],
        l.[Montant HT Net] AS [Montant],
        l.CMUP * l.Quantité AS [Cout_Marchandise],
        l.[Montant HT Net] - (l.CMUP * l.Quantité) AS [Marge],
        YEAR(l.[Date BL]) AS [Annee],
        MONTH(l.[Date BL]) AS [Mois],
        DATEPART(QUARTER, l.[Date BL]) AS [Trimestre]
    FROM Entête_des_ventes AS e
    INNER JOIN Clients AS c ON e.[Code client] = c.[Code client] AND e.DB_Id = c.DB_Id
    INNER JOIN Lignes_des_ventes AS l ON e.DB_Id = l.DB_Id AND e.[Type Document] = l.[Type Document] AND e.[N° pièce] = l.[N° Pièce]
    INNER JOIN Articles AS a ON l.DB_Id = a.DB_Id AND l.[Code article] = a.[Code Article]
    INNER JOIN Mouvement_stock AS ms ON l.id = ms.id
    WHERE l.[Valorise CA] = 'oui'
    """

    try:
        with get_db_cursor() as cursor:
            cursor.execute(drop_view)
            cursor.execute(create_view)
        print("✅ Vue VW_Ventes_CA creee avec succes")
        return True
    except Exception as e:
        print(f"⚠️  Erreur creation vue: {e}")
        return False


def clear_old_reports():
    """Supprime tous les anciens rapports et menus"""
    print("🗑️  Suppression des anciens rapports...")

    with get_db_cursor() as cursor:
        # Supprimer les droits utilisateurs sur les menus
        cursor.execute("DELETE FROM APP_UserMenus")
        print("   - Droits utilisateurs supprimés")

        # Supprimer les menus
        cursor.execute("DELETE FROM APP_Menus")
        print("   - Menus supprimés")

        # Supprimer les dashboards
        cursor.execute("DELETE FROM APP_Dashboards")
        print("   - Dashboards supprimés")

        # Supprimer les pivots
        cursor.execute("DELETE FROM APP_Pivots")
        print("   - Pivots supprimés")

        # Supprimer les gridviews
        cursor.execute("DELETE FROM APP_GridViews")
        print("   - GridViews supprimés")

        # Supprimer les sources de données (sauf système)
        cursor.execute("DELETE FROM APP_DataSources")
        print("   - Sources de données supprimées")

    print("✅ Anciens rapports supprimés")


def create_datasource():
    """Crée la source de données principale pour les ventes"""
    print("\n📊 Création de la source de données Ventes...")

    with get_db_cursor() as cursor:
        cursor.execute(
            """INSERT INTO APP_DataSources (nom, type, description, query_template, parameters)
               VALUES (?, ?, ?, ?, ?)""",
            (
                "Ventes - Chiffre d'Affaires",
                "query",
                "Source principale pour l'analyse des ventes et du CA. Inclut les données de lignes de ventes avec calcul de marge selon valorisation choisie.",
                DATASOURCE_VENTES_QUERY,
                json.dumps(DATASOURCE_PARAMS)
            )
        )
        cursor.execute("SELECT @@IDENTITY AS id")
        datasource_id = cursor.fetchone()[0]

    print(f"✅ Source de données créée (ID: {datasource_id})")
    return datasource_id


def create_dashboards(datasource_id):
    """Crée les rapports de type Dashboard"""
    print("\n📊 Création des Dashboards...")

    dashboard_ids = {}
    with get_db_cursor() as cursor:
        for dash in DASHBOARDS:
            cursor.execute(
                """INSERT INTO APP_Dashboards (nom, description, widgets, is_public, created_by)
                   VALUES (?, ?, ?, 1, 1)""",
                (dash['nom'], dash['description'], json.dumps(dash['widgets']))
            )
            cursor.execute("SELECT @@IDENTITY AS id")
            new_id = cursor.fetchone()[0]
            dashboard_ids[dash['id']] = new_id
            print(f"   - {dash['nom']} (ID: {new_id})")

    print(f"✅ {len(DASHBOARDS)} Dashboards créés")
    return dashboard_ids


def create_pivots(datasource_id):
    """Crée les rapports de type Pivot"""
    print("\n🔄 Création des Pivots...")

    pivot_ids = {}
    with get_db_cursor() as cursor:
        for pivot in PIVOTS:
            cursor.execute(
                """INSERT INTO APP_Pivots (nom, description, data_source_id, rows_config, columns_config, values_config, filters_config, is_public, created_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1)""",
                (
                    pivot['nom'],
                    pivot['description'],
                    datasource_id,
                    json.dumps(pivot['rows']),
                    json.dumps(pivot['columns']),
                    json.dumps(pivot['values']),
                    json.dumps([])
                )
            )
            cursor.execute("SELECT @@IDENTITY AS id")
            new_id = cursor.fetchone()[0]
            pivot_ids[pivot['id']] = new_id
            print(f"   - {pivot['nom']} (ID: {new_id})")

    print(f"✅ {len(PIVOTS)} Pivots créés")
    return pivot_ids


def create_gridviews(datasource_id):
    """Crée les rapports de type GridView"""
    print("\n📋 Création des GridViews...")

    gridview_ids = {}
    with get_db_cursor() as cursor:
        for grid in GRIDVIEWS:
            features = {
                "show_search": True,
                "show_column_filters": True,
                "show_grouping": True,
                "show_column_toggle": True,
                "show_export": True,
                "show_pagination": True,
                "show_page_size": True,
                "allow_sorting": True
            }

            cursor.execute(
                """INSERT INTO APP_GridViews (nom, description, data_source_id, columns_config, default_sort, page_size, show_totals, total_columns, row_styles, features, is_public, created_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1)""",
                (
                    grid['nom'],
                    grid['description'],
                    datasource_id,
                    json.dumps(grid['columns']),
                    json.dumps(grid.get('default_sort')),
                    grid.get('page_size', 25),
                    grid.get('show_totals', False),
                    json.dumps(grid.get('total_columns', [])),
                    json.dumps([]),
                    json.dumps(features)
                )
            )
            cursor.execute("SELECT @@IDENTITY AS id")
            new_id = cursor.fetchone()[0]
            gridview_ids[grid['id']] = new_id
            print(f"   - {grid['nom']} (ID: {new_id})")

    print(f"✅ {len(GRIDVIEWS)} GridViews créés")
    return gridview_ids


def create_menus(dashboard_ids, pivot_ids, gridview_ids):
    """Crée la structure des menus"""
    print("\n📁 Création des menus...")

    menu_code_to_id = {}

    with get_db_cursor() as cursor:
        # 1. Créer les menus racines et dossiers
        for menu in MENUS:
            parent_id = None
            if 'parent_code' in menu and menu['parent_code'] in menu_code_to_id:
                parent_id = menu_code_to_id[menu['parent_code']]

            cursor.execute(
                """INSERT INTO APP_Menus (parent_id, nom, code, icon, type, target_id, url, ordre, is_active)
                   VALUES (?, ?, ?, ?, ?, NULL, NULL, ?, 1)""",
                (parent_id, menu['nom'], menu['code'], menu['icon'], menu['type'], menu['ordre'])
            )
            cursor.execute("SELECT @@IDENTITY AS id")
            new_id = cursor.fetchone()[0]
            menu_code_to_id[menu['code']] = new_id
            print(f"   - 📁 {menu['nom']}")

        # 2. Créer les menus pour les rapports
        for mapping in RAPPORT_MENU_MAPPING:
            parent_id = menu_code_to_id.get(mapping['parent_code'])
            if not parent_id:
                continue

            rapport_type = mapping['type']
            rapport_id = mapping['rapport_id']

            # Récupérer les infos du rapport
            if rapport_type == 'dashboard':
                target_id = dashboard_ids.get(rapport_id)
                rapport_info = next((d for d in DASHBOARDS if d['id'] == rapport_id), None)
            elif rapport_type == 'pivot':
                target_id = pivot_ids.get(rapport_id)
                rapport_info = next((p for p in PIVOTS if p['id'] == rapport_id), None)
            elif rapport_type == 'gridview':
                target_id = gridview_ids.get(rapport_id)
                rapport_info = next((g for g in GRIDVIEWS if g['id'] == rapport_id), None)
            else:
                continue

            if not target_id or not rapport_info:
                continue

            # Icône selon type
            icon = "LayoutDashboard" if rapport_type == 'dashboard' else ("RotateCw" if rapport_type == 'pivot' else "Table")

            cursor.execute(
                """INSERT INTO APP_Menus (parent_id, nom, code, icon, type, target_id, url, ordre, is_active)
                   VALUES (?, ?, ?, ?, ?, ?, NULL, ?, 1)""",
                (
                    parent_id,
                    rapport_info['nom'],
                    f"rapport-{rapport_type}-{rapport_id}",
                    icon,
                    rapport_type,
                    target_id,
                    mapping['ordre']
                )
            )
            type_icon = "📊" if rapport_type == 'dashboard' else ("🔄" if rapport_type == 'pivot' else "📋")
            print(f"      {type_icon} {rapport_info['nom']}")

    print(f"✅ Menus créés")


def grant_admin_access():
    """Donne accès à tous les menus pour les admins"""
    print("\n🔐 Attribution des droits admin...")

    with get_db_cursor() as cursor:
        # Récupérer les utilisateurs admin
        admins = execute_query("SELECT id FROM APP_Users WHERE role = 'admin'", use_cache=False)

        # Récupérer tous les menus
        menus = execute_query("SELECT id FROM APP_Menus", use_cache=False)

        for admin in admins:
            for menu in menus:
                cursor.execute(
                    """INSERT INTO APP_UserMenus (user_id, menu_id, can_view, can_export)
                       VALUES (?, ?, 1, 1)""",
                    (admin['id'], menu['id'])
                )

        print(f"✅ Droits attribués à {len(admins)} admin(s)")


def main():
    """Fonction principale"""
    print("=" * 60)
    print("🚀 INITIALISATION DES RAPPORTS VENTES & CHIFFRE D'AFFAIRES")
    print("=" * 60)

    try:
        # 0. Creer la vue SQL dans la base de donnees
        create_sql_view()

        # 1. Supprimer les anciens rapports
        clear_old_reports()

        # 2. Créer la source de données
        datasource_id = create_datasource()

        # 3. Créer les rapports
        dashboard_ids = create_dashboards(datasource_id)
        pivot_ids = create_pivots(datasource_id)
        gridview_ids = create_gridviews(datasource_id)

        # 4. Créer les menus
        create_menus(dashboard_ids, pivot_ids, gridview_ids)

        # 5. Attribuer les droits admin
        grant_admin_access()

        print("\n" + "=" * 60)
        print("✅ INITIALISATION TERMINÉE AVEC SUCCÈS!")
        print("=" * 60)
        print(f"""
📊 Récapitulatif:
   - 1 Source de données créée
   - {len(DASHBOARDS)} Dashboards créés
   - {len(PIVOTS)} Pivots créés
   - {len(GRIDVIEWS)} GridViews créés
   - Structure de menus créée
   - Droits admin attribués
        """)

    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
