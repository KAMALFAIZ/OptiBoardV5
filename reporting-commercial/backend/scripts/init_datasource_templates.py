"""
Script d'initialisation des Templates de DataSources
=====================================================
Execute ce script pour creer les templates de sources de donnees dans la base centrale
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Utiliser la base de donnees standard (DB_* dans .env)
from app.database import execute_query as execute_central_query, get_db_cursor

def execute_central_write(query, params=None):
    with get_db_cursor() as cursor:
        cursor.execute(query, params or ())
        return cursor.rowcount

# =============================================================================
# TEMPLATES DE DATASOURCES
# =============================================================================

DATASOURCE_TEMPLATES = [
    # ==================== VENTES - Base Lignes_des_ventes ====================
    # Source principale: Lignes_des_ventes avec tous les types de documents
    # Types: Facture, Facture comptabilisee, Bon de livraison, Bon de commande,
    #        Devis, Bon avoir, Facture avoir, Bon de retour, Preparation de livraison

    # --- CA et Marges (Valorise CA = Oui) ---
    {
        "code": "DS_VENTES_GLOBAL",
        "nom": "CA Global",
        "category": "Ventes",
        "description": "Chiffre d'affaires et marge globaux depuis Lignes_des_ventes",
        "query_template": """
            SELECT
                [societe] AS [Société],
                SUM([Montant HT Net]) AS [CA HT],
                SUM([Montant TTC Net]) AS [CA TTC],
                SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) AS [Marge],
                CASE WHEN SUM([Montant HT Net]) > 0
                    THEN ROUND(SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) * 100.0 / SUM([Montant HT Net]), 2)
                    ELSE 0 END AS [Marge %],
                COUNT(DISTINCT [Code client]) AS [Nb Clients],
                COUNT(DISTINCT [N° Pièce]) AS [Nb Documents],
                SUM([Quantité]) AS [Qte Totale],
                COUNT(*) AS [Nb Lignes],
                CASE WHEN COUNT(DISTINCT [Code client]) > 0
                    THEN ROUND(SUM([Montant HT Net]) / COUNT(DISTINCT [Code client]), 2)
                    ELSE 0 END AS [CA Moyen par Client],
                CASE WHEN COUNT(DISTINCT [N° Pièce]) > 0
                    THEN ROUND(SUM([Montant HT Net]) / COUNT(DISTINCT [N° Pièce]), 2)
                    ELSE 0 END AS [Panier Moyen]
            FROM [Lignes_des_ventes]
            WHERE [Valorise CA] = 'Oui'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date BL] BETWEEN @dateDebut AND @dateFin
            GROUP BY [societe]
            ORDER BY [CA HT] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_VENTES_PAR_MOIS",
        "nom": "CA par Mois",
        "category": "Ventes",
        "description": "Evolution mensuelle du CA et de la marge",
        "query_template": """
            SELECT
                YEAR([Date BL]) AS [Annee],
                MONTH([Date BL]) AS [Mois],
                FORMAT([Date BL], 'yyyy-MM') AS [Periode],
                [societe] AS [Société],
                SUM([Montant HT Net]) AS [CA HT],
                SUM([Montant TTC Net]) AS [CA TTC],
                SUM(ISNULL([CMUP], 0) * [Quantité]) AS [Cout Revient],
                SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) AS [Marge],
                CASE WHEN SUM([Montant HT Net]) > 0
                    THEN ROUND(SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) * 100.0 / SUM([Montant HT Net]), 2)
                    ELSE 0 END AS [Marge %],
                COUNT(DISTINCT [Code client]) AS [Nb Clients],
                COUNT(DISTINCT [N° Pièce]) AS [Nb Documents],
                COUNT(DISTINCT [Code article]) AS [Nb Articles],
                SUM([Quantité]) AS [Qte Totale]
            FROM [Lignes_des_ventes]
            WHERE [Valorise CA] = 'Oui'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date BL] BETWEEN @dateDebut AND @dateFin
            GROUP BY YEAR([Date BL]), MONTH([Date BL]), FORMAT([Date BL], 'yyyy-MM'), [societe]
            ORDER BY [Annee], [Mois]
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_VENTES_PAR_CLIENT",
        "nom": "CA par Client",
        "category": "Ventes",
        "description": "Chiffre d'affaires et marge par client",
        "query_template": """
            SELECT
                [Code client] AS [Code Client],
                [Intitulé client] AS [Client],
                [societe] AS [Société],
                SUM([Montant HT Net]) AS [CA HT],
                SUM([Montant TTC Net]) AS [CA TTC],
                SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) AS [Marge],
                CASE WHEN SUM([Montant HT Net]) > 0
                    THEN ROUND(SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) * 100.0 / SUM([Montant HT Net]), 2)
                    ELSE 0 END AS [Marge %],
                COUNT(DISTINCT [N° Pièce]) AS [Nb Factures],
                SUM([Quantité]) AS [Qte Totale],
                CASE WHEN COUNT(DISTINCT [N° Pièce]) > 0
                    THEN ROUND(SUM([Montant HT Net]) / COUNT(DISTINCT [N° Pièce]), 2)
                    ELSE 0 END AS [Panier Moyen],
                MIN([Date BL]) AS [Premiere Vente],
                MAX([Date BL]) AS [Derniere Vente]
            FROM [Lignes_des_ventes]
            WHERE [Valorise CA] = 'Oui'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date BL] BETWEEN @dateDebut AND @dateFin
            GROUP BY [Code client], [Intitulé client], [societe]
            ORDER BY [CA HT] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_VENTES_PAR_ARTICLE",
        "nom": "CA par Article",
        "category": "Ventes",
        "description": "Chiffre d'affaires et marge par article avec catalogues",
        "query_template": """
            SELECT
                [Code article] AS [Code Article],
                [Désignation ligne] AS [Designation],
                [Catalogue 1] AS [Catalogue1],
                [Catalogue 2] AS [Catalogue2],
                [Gamme 1] AS [Gamme1],
                [Gamme 2] AS [Gamme2],
                SUM([Quantité]) AS [Qte Vendue],
                SUM([Montant HT Net]) AS [CA HT],
                SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) AS [Marge],
                CASE WHEN SUM([Montant HT Net]) > 0
                    THEN ROUND(SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) * 100.0 / SUM([Montant HT Net]), 2)
                    ELSE 0 END AS [Marge %],
                CASE WHEN SUM([Quantité]) > 0
                    THEN ROUND(SUM([Montant HT Net]) / SUM([Quantité]), 2)
                    ELSE 0 END AS [Prix Moyen],
                AVG([CMUP]) AS [Cout Moyen],
                COUNT(DISTINCT [Code client]) AS [Nb Clients]
            FROM [Lignes_des_ventes]
            WHERE [Valorise CA] = 'Oui'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date BL] BETWEEN @dateDebut AND @dateFin
            GROUP BY [Code article], [Désignation ligne], [Catalogue 1], [Catalogue 2], [Gamme 1], [Gamme 2]
            ORDER BY [CA HT] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_VENTES_PAR_CATALOGUE",
        "nom": "CA par Catalogue",
        "category": "Ventes",
        "description": "Chiffre d'affaires par catalogue/famille de produits",
        "query_template": """
            SELECT
                ISNULL([Catalogue 1], '(Non classé)') AS [Catalogue],
                ISNULL([Catalogue 2], '(Non classé)') AS [Sous Catalogue],
                COUNT(DISTINCT [Code article]) AS [Nb Articles],
                SUM([Quantité]) AS [Qte Vendue],
                SUM([Montant HT Net]) AS [CA HT],
                SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) AS [Marge],
                CASE WHEN SUM([Montant HT Net]) > 0
                    THEN ROUND(SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) * 100.0 / SUM([Montant HT Net]), 2)
                    ELSE 0 END AS [Marge %],
                COUNT(DISTINCT [Code client]) AS [Nb Clients],
                CASE WHEN COUNT(DISTINCT [Code article]) > 0
                    THEN ROUND(SUM([Montant HT Net]) / COUNT(DISTINCT [Code article]), 2)
                    ELSE 0 END AS [CA Moyen par Article]
            FROM [Lignes_des_ventes]
            WHERE [Valorise CA] = 'Oui'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date BL] BETWEEN @dateDebut AND @dateFin
            GROUP BY ISNULL([Catalogue 1], '(Non classé)'), ISNULL([Catalogue 2], '(Non classé)')
            ORDER BY [CA HT] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_VENTES_PAR_DEPOT",
        "nom": "CA par Depot",
        "category": "Ventes",
        "description": "Chiffre d'affaires par depot/entrepot",
        "query_template": """
            SELECT
                [Code dépôt] AS [Code Depot],
                [Intitulé dépôt] AS [Depot],
                [societe] AS [Société],
                SUM([Montant HT Net]) AS [CA HT],
                SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) AS [Marge],
                CASE WHEN SUM([Montant HT Net]) > 0
                    THEN ROUND(SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) * 100.0 / SUM([Montant HT Net]), 2)
                    ELSE 0 END AS [Marge %],
                SUM([Quantité]) AS [Qte Vendue],
                COUNT(DISTINCT [Code article]) AS [Nb Articles],
                COUNT(DISTINCT [Code client]) AS [Nb Clients],
                COUNT(DISTINCT [N° Pièce]) AS [Nb Documents],
                CASE WHEN COUNT(DISTINCT [Code client]) > 0
                    THEN ROUND(SUM([Montant HT Net]) / COUNT(DISTINCT [Code client]), 2)
                    ELSE 0 END AS [CA Moyen par Client]
            FROM [Lignes_des_ventes]
            WHERE [Valorise CA] = 'Oui'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date BL] BETWEEN @dateDebut AND @dateFin
            GROUP BY [Code dépôt], [Intitulé dépôt], [societe]
            ORDER BY [CA HT] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- Analyse par Type de Document ---
    {
        "code": "DS_VENTES_PAR_TYPE_DOC",
        "nom": "Ventes par Type Document",
        "category": "Ventes",
        "description": "Analyse des ventes par type de document (Facture, BL, BC, Devis, Avoir...)",
        "query_template": """
            SELECT
                [Type Document],
                [societe] AS [Société],
                COUNT(DISTINCT [N° Pièce]) AS [Nb Documents],
                COUNT(*) AS [Nb Lignes],
                SUM([Quantité]) AS [Qte Totale],
                SUM([Montant HT Net]) AS [Montant HT],
                SUM([Montant TTC Net]) AS [Montant TTC],
                COUNT(DISTINCT [Code client]) AS [Nb Clients],
                COUNT(DISTINCT [Code article]) AS [Nb Articles]
            FROM [Lignes_des_ventes]
            WHERE [Date document] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
            GROUP BY [Type Document], [societe]
            ORDER BY [Montant HT] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_FACTURES",
        "nom": "Factures",
        "category": "Ventes",
        "description": "Detail des factures (Facture et Facture comptabilisee)",
        "query_template": """
            SELECT
                [societe] AS [Société],
                [N° Pièce] AS [Num Facture],
                [Date document] AS [Date Facture],
                [Code client] AS [Code Client],
                [Intitulé client] AS [Client],
                [Code article] AS [Code Article],
                [Désignation ligne] AS [Designation],
                [Quantité] AS [Qte],
                [Prix unitaire] AS [PU HT],
                [Montant HT Net] AS [Montant HT],
                [Montant TTC Net] AS [Montant TTC],
                [CMUP] AS [Cout],
                [Montant HT Net] - ISNULL([CMUP], 0) * [Quantité] AS [Marge],
                CASE WHEN [Montant HT Net] <> 0
                    THEN ROUND(([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) * 100.0 / [Montant HT Net], 2)
                    ELSE 0 END AS [Taux Marge %],
                [Référence] AS [Reference Client],
                [Code d'affaire] AS [Code Affaire],
                [Intitulé affaire] AS [Affaire]
            FROM [Lignes_des_ventes]
            WHERE [Type Document] IN ('Facture', 'Facture comptabilisée')
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date document] BETWEEN @dateDebut AND @dateFin
            ORDER BY [Date document] DESC, [N° Pièce]
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_BONS_LIVRAISON",
        "nom": "Bons de Livraison",
        "category": "Ventes",
        "description": "Detail des bons de livraison",
        "query_template": """
            SELECT
                [societe] AS [Société],
                [N° Pièce] AS [Num BL],
                [Date BL],
                [N° Pièce BC] AS [Num BC],
                [Date BC],
                [Code client] AS [Code Client],
                [Intitulé client] AS [Client],
                [Code article] AS [Code Article],
                [Désignation ligne] AS [Designation],
                [Quantité BL] AS [Qte BL],
                [Quantité BC] AS [Qte BC],
                [Montant HT Net] AS [Montant HT],
                [Code dépôt] AS [Code Depot],
                [Intitulé dépôt] AS [Depot],
                [Date Livraison],
                [N° Série/Lot] AS [Num Serie Lot]
            FROM [Lignes_des_ventes]
            WHERE [Type Document] = 'Bon de livraison'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date document] BETWEEN @dateDebut AND @dateFin
            ORDER BY [Date BL] DESC, [N° Pièce]
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_BONS_COMMANDE",
        "nom": "Bons de Commande",
        "category": "Ventes",
        "description": "Detail des bons de commande clients",
        "query_template": """
            SELECT
                [societe] AS [Société],
                [N° Pièce] AS [Num BC],
                [Date BC],
                [Code client] AS [Code Client],
                [Intitulé client] AS [Client],
                [Code article] AS [Code Article],
                [Désignation ligne] AS [Designation],
                [Quantité BC] AS [Qte Commandee],
                [Quantité BL] AS [Qte Livree],
                [Quantité BC] - ISNULL([Quantité BL], 0) AS [Reste A Livrer],
                CASE WHEN [Quantité BC] > 0
                    THEN ROUND(ISNULL([Quantité BL], 0) * 100.0 / [Quantité BC], 2)
                    ELSE 0 END AS [Taux Livraison %],
                [Prix unitaire] AS [PU HT],
                [Montant HT Net] AS [Montant HT],
                [Date Livraison] AS [Date Livraison Prevue],
                [Référence] AS [Reference Client],
                [Code d'affaire] AS [Code Affaire]
            FROM [Lignes_des_ventes]
            WHERE [Type Document] = 'Bon de commande'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date document] BETWEEN @dateDebut AND @dateFin
            ORDER BY [Date BC] DESC, [N° Pièce]
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_DEVIS",
        "nom": "Devis",
        "category": "Ventes",
        "description": "Detail des devis clients",
        "query_template": """
            SELECT
                [societe] AS [Société],
                [N° Pièce] AS [Num Devis],
                [Date document] AS [Date Devis],
                [Code client] AS [Code Client],
                [Intitulé client] AS [Client],
                [Code article] AS [Code Article],
                [Désignation ligne] AS [Designation],
                [Quantité devis] AS [Qte],
                [Prix unitaire] AS [PU HT],
                [Montant HT Net] AS [Montant HT],
                [Montant TTC Net] AS [Montant TTC],
                [Référence] AS [Reference],
                [Code d'affaire] AS [Code Affaire],
                [Intitulé affaire] AS [Affaire]
            FROM [Lignes_des_ventes]
            WHERE [Type Document] = 'Devis'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date document] BETWEEN @dateDebut AND @dateFin
            ORDER BY [Date document] DESC, [N° Pièce]
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_AVOIRS",
        "nom": "Avoirs",
        "category": "Ventes",
        "description": "Detail des avoirs et retours (Facture avoir, Bon avoir, Bon de retour)",
        "query_template": """
            SELECT
                [societe] AS [Société],
                [Type Document],
                [N° Pièce] AS [Num Avoir],
                [Date document] AS [Date Avoir],
                [Code client] AS [Code Client],
                [Intitulé client] AS [Client],
                [Code article] AS [Code Article],
                [Désignation ligne] AS [Designation],
                [Quantité] AS [Qte],
                [Prix unitaire] AS [PU HT],
                [Montant HT Net] AS [Montant HT],
                [Montant TTC Net] AS [Montant TTC],
                [Référence] AS [Reference],
                [Code dépôt] AS [Code Depot]
            FROM [Lignes_des_ventes]
            WHERE [Type Document] IN ('Facture avoir', 'Facture avoir comptabilisée', 'Bon avoir financier', 'Bon de retour', 'Facture de retour', 'Facture de retour comptabilisée')
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date document] BETWEEN @dateDebut AND @dateFin
            ORDER BY [Date document] DESC, [N° Pièce]
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_PREPARATIONS_LIVRAISON",
        "nom": "Preparations Livraison",
        "category": "Ventes",
        "description": "Detail des preparations de livraison en cours",
        "query_template": """
            SELECT
                [societe] AS [Société],
                [N° pièce PL] AS [Num PL],
                [Date PL],
                [N° Pièce BC] AS [Num BC],
                [Code client] AS [Code Client],
                [Intitulé client] AS [Client],
                [Code article] AS [Code Article],
                [Désignation ligne] AS [Designation],
                [Quantité PL] AS [Qte PL],
                [Quantité BC] AS [Qte BC],
                [Prix unitaire] AS [PU HT],
                [Montant HT Net] AS [Montant HT],
                [Code dépôt] AS [Code Depot],
                [Intitulé dépôt] AS [Depot],
                [Date Livraison] AS [Date Livraison Prevue]
            FROM [Lignes_des_ventes]
            WHERE [Type Document] = 'Préparation de livraison'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date document] BETWEEN @dateDebut AND @dateFin
            ORDER BY [Date PL] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- Analyses detaillees ---
    {
        "code": "DS_VENTES_DETAIL",
        "nom": "Ventes Detail Complet",
        "category": "Ventes",
        "description": "Detail complet de toutes les lignes de ventes avec tous les champs",
        "query_template": """
            SELECT
                [societe] AS [Société],
                [Type Document],
                [N° Pièce] AS [Numéro Pièce],
                [Date document] AS [Date],
                [Code client] AS [Code Client],
                [Intitulé client] AS [Client],
                [Code article] AS [Code Article],
                [Désignation ligne] AS [Designation],
                [Catalogue 1], [Catalogue 2], [Catalogue 3], [Catalogue 4],
                [Gamme 1], [Gamme 2],
                [Quantité] AS [Qte],
                [Prix unitaire] AS [PU HT],
                [Prix unitaire TTC] AS [PU TTC],
                [Remise 1], [Remise 2],
                [Montant HT Net] AS [Montant HT],
                [Montant TTC Net] AS [Montant TTC],
                [CMUP] AS [Cout],
                [CMUP],
                [Coût standard],
                [Montant HT Net] - ISNULL([CMUP], 0) * [Quantité] AS [Marge],
                CASE WHEN [Montant HT Net] <> 0
                    THEN ROUND(([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) * 100.0 / [Montant HT Net], 2)
                    ELSE 0 END AS [Taux Marge %],
                [Code dépôt] AS [Code Depot],
                [Intitulé dépôt] AS [Depot],
                [N° Série/Lot] AS [Num Serie Lot],
                [Poids net], [Poids brut], [Colisage],
                [Code d'affaire] AS [Code Affaire],
                [Intitulé affaire] AS [Affaire],
                [Référence] AS [Reference Client],
                [Valorise CA]
            FROM [Lignes_des_ventes]
            WHERE [Date document] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
            ORDER BY [Date document] DESC, [N° Pièce]
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_VENTES_PAR_AFFAIRE",
        "nom": "CA par Affaire",
        "category": "Ventes",
        "description": "Chiffre d'affaires par affaire/projet",
        "query_template": """
            SELECT
                [Code d'affaire] AS [Code Affaire],
                [Intitulé affaire] AS [Affaire],
                [Code client] AS [Code Client],
                [Intitulé client] AS [Client],
                [societe] AS [Société],
                SUM([Montant HT Net]) AS [CA HT],
                SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) AS [Marge],
                CASE WHEN SUM([Montant HT Net]) > 0
                    THEN ROUND(SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) * 100.0 / SUM([Montant HT Net]), 2)
                    ELSE 0 END AS [Marge %],
                COUNT(DISTINCT [N° Pièce]) AS [Nb Documents],
                MIN([Date BL]) AS [Date Debut],
                MAX([Date BL]) AS [Date Fin]
            FROM [Lignes_des_ventes]
            WHERE [Valorise CA] = 'Oui'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Code d'affaire] IS NOT NULL
              AND [Code d'affaire] <> ''
              AND [Date BL] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
            GROUP BY [Code d'affaire], [Intitulé affaire], [Code client], [Intitulé client], [societe]
            ORDER BY [CA HT] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_COMMANDES_EN_COURS",
        "nom": "Commandes en Cours",
        "category": "Ventes",
        "description": "Commandes non entierement livrees (carnet de commandes)",
        "query_template": """
            SELECT
                [societe] AS [Société],
                [N° Pièce] AS [Num BC],
                [Date BC],
                [Code client] AS [Code Client],
                [Intitulé client] AS [Client],
                [Code article] AS [Code Article],
                [Désignation ligne] AS [Designation],
                [Quantité BC] AS [Qte Commandee],
                ISNULL([Quantité BL], 0) AS [Qte Livree],
                [Quantité BC] - ISNULL([Quantité BL], 0) AS [Reste A Livrer],
                CASE WHEN [Quantité BC] > 0
                    THEN ROUND(ISNULL([Quantité BL], 0) * 100.0 / [Quantité BC], 2)
                    ELSE 0 END AS [Taux Livraison %],
                [Prix unitaire] AS [PU HT],
                ([Quantité BC] - ISNULL([Quantité BL], 0)) * [Prix unitaire] AS [Montant Reste],
                [Date Livraison] AS [Date Livraison Prevue],
                DATEDIFF(DAY, [Date BC], GETDATE()) AS [Age Commande Jours]
            FROM [Lignes_des_ventes]
            WHERE [Type Document] = 'Bon de commande'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Quantité BC] > ISNULL([Quantité BL], 0)
            ORDER BY [Date Livraison], [Date BC]
        """,
        "parameters": '[{"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_TOP_ARTICLES",
        "nom": "Top Articles",
        "category": "Ventes",
        "description": "Classement des meilleurs articles par CA",
        "query_template": """
            SELECT TOP 100
                [Code article] AS [Code Article],
                [Désignation ligne] AS [Designation],
                [Catalogue 1] AS [Catalogue],
                SUM([Quantité]) AS [Qte Vendue],
                SUM([Montant HT Net]) AS [CA HT],
                SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) AS [Marge],
                CASE WHEN SUM([Montant HT Net]) > 0
                    THEN ROUND(SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) * 100.0 / SUM([Montant HT Net]), 2)
                    ELSE 0 END AS [Marge %],
                COUNT(DISTINCT [Code client]) AS [Nb Clients],
                COUNT(DISTINCT [N° Pièce]) AS [Nb Ventes]
            FROM [Lignes_des_ventes]
            WHERE [Valorise CA] = 'Oui'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date BL] BETWEEN @dateDebut AND @dateFin
            GROUP BY [Code article], [Désignation ligne], [Catalogue 1]
            ORDER BY [CA HT] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_TOP_CLIENTS",
        "nom": "Top Clients",
        "category": "Ventes",
        "description": "Classement des meilleurs clients par CA",
        "query_template": """
            SELECT TOP 100
                [Code client] AS [Code Client],
                [Intitulé client] AS [Client],
                [societe] AS [Société],
                SUM([Montant HT Net]) AS [CA HT],
                SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) AS [Marge],
                CASE WHEN SUM([Montant HT Net]) > 0
                    THEN ROUND(SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) * 100.0 / SUM([Montant HT Net]), 2)
                    ELSE 0 END AS [Marge %],
                COUNT(DISTINCT [N° Pièce]) AS [Nb Factures],
                COUNT(DISTINCT [Code article]) AS [Nb Articles],
                CASE WHEN COUNT(DISTINCT [N° Pièce]) > 0
                    THEN ROUND(SUM([Montant HT Net]) / COUNT(DISTINCT [N° Pièce]), 2)
                    ELSE 0 END AS [Panier Moyen],
                MIN([Date BL]) AS [Premiere Vente],
                MAX([Date BL]) AS [Derniere Vente]
            FROM [Lignes_des_ventes]
            WHERE [Valorise CA] = 'Oui'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date BL] BETWEEN @dateDebut AND @dateFin
            GROUP BY [Code client], [Intitulé client], [societe]
            ORDER BY [CA HT] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_VENTES_PAR_COMMERCIAL",
        "nom": "CA par Commercial",
        "category": "Ventes",
        "description": "Performance commerciale (necessite jointure avec Entete)",
        "query_template": """
            SELECT
                e.[Code représentant] AS [Code Commercial],
                e.[Nom représentant] AS [Commercial],
                l.[societe] AS [Société],
                COUNT(DISTINCT l.[Code client]) AS [Nb Clients],
                COUNT(DISTINCT l.[N° Pièce]) AS [Nb Factures],
                SUM(l.[Montant HT Net]) AS [CA HT],
                SUM(l.[Montant HT Net] - ISNULL(l.[CMUP], 0) * l.[Quantité]) AS [Marge],
                CASE WHEN SUM(l.[Montant HT Net]) > 0
                    THEN ROUND(SUM(l.[Montant HT Net] - ISNULL(l.[CMUP], 0) * l.[Quantité]) * 100.0 / SUM(l.[Montant HT Net]), 2)
                    ELSE 0 END AS [Marge %],
                CASE WHEN COUNT(DISTINCT l.[Code client]) > 0
                    THEN ROUND(SUM(l.[Montant HT Net]) / COUNT(DISTINCT l.[Code client]), 2)
                    ELSE 0 END AS [CA Moyen par Client],
                CASE WHEN COUNT(DISTINCT l.[N° Pièce]) > 0
                    THEN ROUND(SUM(l.[Montant HT Net]) / COUNT(DISTINCT l.[N° Pièce]), 2)
                    ELSE 0 END AS [Panier Moyen]
            FROM [Lignes_des_ventes] l
            INNER JOIN [Entête_des_ventes] e
                ON l.[DB_Id] = e.[DB_Id]
                AND l.[Type Document] = e.[Type Document]
                AND l.[N° Pièce] = e.[N° pièce]
            WHERE l.[Valorise CA] = 'Oui'
              AND (@societe IS NULL OR l.[societe] = @societe)
              AND l.[Date BL] BETWEEN @dateDebut AND @dateFin
            GROUP BY e.[Code représentant], e.[Nom représentant], l.[societe]
            ORDER BY [CA HT] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_VENTES_PAR_ZONE",
        "nom": "CA par Zone Geographique",
        "category": "Ventes",
        "description": "Repartition geographique des ventes (necessite jointure avec Clients)",
        "query_template": """
            SELECT
                c.[Région] AS [Zone],
                c.[Catégorie tarifaire] AS [Canal],
                l.[societe] AS [Société],
                COUNT(DISTINCT l.[Code client]) AS [Nb Clients],
                SUM(l.[Montant HT Net]) AS [CA HT],
                SUM(l.[Montant HT Net] - ISNULL(l.[CMUP], 0) * l.[Quantité]) AS [Marge],
                CASE WHEN SUM(l.[Montant HT Net]) > 0
                    THEN ROUND(SUM(l.[Montant HT Net] - ISNULL(l.[CMUP], 0) * l.[Quantité]) * 100.0 / SUM(l.[Montant HT Net]), 2)
                    ELSE 0 END AS [Marge %]
            FROM [Lignes_des_ventes] l
            INNER JOIN [Clients] c
                ON l.[DB_Id] = c.[DB_Id]
                AND l.[Code client] = c.[Code client]
            WHERE l.[Valorise CA] = 'Oui'
              AND (@societe IS NULL OR l.[societe] = @societe)
              AND l.[Date BL] BETWEEN @dateDebut AND @dateFin
              AND c.[Région] IS NOT NULL
            GROUP BY c.[Région], c.[Catégorie tarifaire], l.[societe]
            ORDER BY [CA HT] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- CA Détaillé avec jointures complètes (Entête, Lignes, Clients, Articles, Mouvement_stock) ---
    {
        "code": "DS_CA_DETAIL_COMPLET",
        "nom": "CA Détail Complet avec Marges",
        "category": "Ventes",
        "description": "Détail complet du CA avec toutes les jointures: Entête, Lignes, Clients, Articles, Mouvement_stock. Inclut marges dynamiques.",
        "query_template": """
            SELECT
                e.[Type Document],
                e.societe AS [Société entête],
                e.Souche,
                e.Statut,
                e.[Intitulé client],
                e.[Code client],
                e.[Nom représentant],
                e.Date,
                e.[N° pièce],
                e.Etat,
                e.[Intitulé tiers payeur],
                e.[N° Compte Payeur],
                e.[Code d'affaire],
                e.[Intitulé affaire],
                e.[Catégorie Comptable],
                e.Cours,
                e.Référence,
                e.[Montant réglé],
                e.[Montant net à payer],
                e.[Entête 1],
                e.[Entête 2],
                e.[Entête 3],
                e.[Entête 4],
                e.Devise,
                e.[Type frais],
                e.[Valeur frais],
                e.[Montant TTC] AS [Montant TTC Entete],
                e.[Montant HT] AS [Montant HT Entete],
                l.[Valorise CA],
                l.[N° Pièce BL],
                l.[Date BL],
                l.[N° Pièce BC],
                l.[Date BC],
                l.[N° pièce PL],
                l.[Date PL],
                l.[Désignation ligne] AS [Désignation Ligne],
                l.Colisage,
                l.[N° Série/Lot],
                l.Taxe1,
                l.[Type taux taxe 1],
                l.[Remise 1],
                l.[Frais d'approche],
                l.CMUP,
                l.[Prix unitaire],
                l.[Prix unitaire TTC],
                l.Quantité,
                l.[Montant HT Net],
                l.[Montant TTC Net],
                c.Ville,
                c.Région,
                a.[Code Famille],
                a.[Intitulé famille],
                a.[Désignation Article],
                a.[Libellé Gamme 1],
                a.[Libellé Gamme 2],
                a.[Catalogue 1],
                a.[Catalogue 2],
                a.[Catalogue 3],
                a.[Catalogue 4],
                a.[Unité Vente],
                l.[PU Devise],
                l.[CMUP],
                e.Dépôt,
                l.[Gamme 1],
                l.[Gamme 2],
                l.[Poids brut],
                l.[Poids net],
                l.[Montant HT Net] AS [Montant],
                a.[Prix d'achat],
                c.[Catégorie tarifaire],
                ISNULL(ms.[DPA-Période], 0) AS [DPA-Période],
                ISNULL(ms.[DPA-Vente], 0) AS [DPA-Vente],
                ISNULL(ms.[DPR-Vente], 0) AS [DPR-Vente],
                -- Marge calculée avec CMUP
                l.[Montant HT Net] - l.Quantité * ISNULL(l.[CMUP], 0) AS [Marge PR],
                -- Marge calculée avec CMUP
                l.[Montant HT Net] - l.Quantité * ISNULL(l.CMUP, 0) AS [Marge CMUP],
                -- Marge calculée avec DPA-Vente
                l.[Montant HT Net] - l.Quantité * ISNULL(ms.[DPA-Vente], 0) AS [Marge DPA-Vente],
                -- Marge calculée avec DPA-Période
                l.[Montant HT Net] - l.Quantité * ISNULL(ms.[DPA-Période], 0) AS [Marge DPA-Période],
                -- Marge calculée avec DPR-Vente
                l.[Montant HT Net] - l.Quantité * ISNULL(ms.[DPR-Vente], 0) AS [Marge DPR-Vente],
                -- Coût marchandise CMUP
                l.Quantité * ISNULL(l.[CMUP], 0) AS [Coût PR],
                -- Coût marchandise CMUP
                l.Quantité * ISNULL(l.CMUP, 0) AS [Coût CMUP]
            FROM Entête_des_ventes AS e
            INNER JOIN Clients AS c
                ON e.[Code client] = c.[Code client] AND e.societe = c.societe
            INNER JOIN Lignes_des_ventes AS l
                ON e.societe = l.societe AND e.[Type Document] = l.[Type Document] AND e.[N° pièce] = l.[N° Pièce]
            INNER JOIN Articles AS a
                ON l.societe = a.societe AND l.[Code article] = a.[Code Article]
            LEFT JOIN Mouvement_stock AS ms
                ON l.societe = ms.societe AND l.[N° interne] = ms.[N° interne]
            WHERE l.[Date BL] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR e.societe = @societe)
              AND l.[Valorise CA] = 'Oui'
            ORDER BY e.Date DESC, e.[N° pièce]
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global", "required": true, "label": "Date début"}, {"name": "dateFin", "type": "date", "source": "global", "required": true, "label": "Date fin"}, {"name": "societe", "type": "string", "source": "global", "required": false, "label": "Société"}]'
    },
    {
        "code": "DS_CA_MARGE_DYNAMIQUE",
        "nom": "CA avec Marge Dynamique",
        "category": "Ventes",
        "description": "CA et marge avec choix de valorisation (CMUP, CMUP, DPA-Vente, DPA-Période, DPR-Vente) et valorisation CA (HT/TTC)",
        "query_template": """
            SELECT
                e.[Type Document],
                e.societe AS [Société],
                e.[Code client],
                e.[Intitulé client],
                e.[Nom représentant],
                e.Date,
                e.[N° pièce],
                e.[Code d'affaire],
                e.[Intitulé affaire],
                e.Dépôt,
                l.[Code article],
                a.[Désignation Article],
                a.[Code Famille],
                a.[Intitulé famille],
                a.[Catalogue 1],
                a.[Catalogue 2],
                l.[Gamme 1],
                l.[Gamme 2],
                c.Ville,
                c.Région,
                c.[Catégorie tarifaire],
                l.Quantité,
                l.[Prix unitaire],
                l.[Prix unitaire TTC],
                l.[Montant HT Net],
                l.[Montant TTC Net],
                -- Montant selon valorisation CA choisie
                CASE WHEN @ValorisationCA = 'TTC' THEN l.[Montant TTC Net] ELSE l.[Montant HT Net] END AS [Montant],
                -- Valeurs de coût disponibles
                l.CMUP,
                l.[CMUP],
                ISNULL(ms.[DPA-Période], 0) AS [DPA-Période],
                ISNULL(ms.[DPA-Vente], 0) AS [DPA-Vente],
                ISNULL(ms.[DPR-Vente], 0) AS [DPR-Vente],
                -- Marge dynamique selon valorisation choisie
                (CASE WHEN @ValorisationCA = 'TTC' THEN l.[Montant TTC Net] ELSE l.[Montant HT Net] END) -
                l.Quantité * ISNULL(
                    CASE @Valorisation
                        WHEN 'CMUP' THEN l.CMUP
                        WHEN 'CMUP' THEN l.[CMUP]
                        WHEN 'DPA-Vente' THEN ms.[DPA-Vente]
                        WHEN 'DPA-Période' THEN ms.[DPA-Période]
                        WHEN 'DPR-Vente' THEN ms.[DPR-Vente]
                        ELSE 0
                    END, 0) AS [Marge],
                -- Coût marchandise dynamique
                ISNULL(
                    CASE @Valorisation
                        WHEN 'CMUP' THEN l.CMUP
                        WHEN 'CMUP' THEN l.[CMUP]
                        WHEN 'DPA-Vente' THEN ms.[DPA-Vente]
                        WHEN 'DPA-Période' THEN ms.[DPA-Période]
                        WHEN 'DPR-Vente' THEN ms.[DPR-Vente]
                        ELSE 0
                    END, 0) * l.Quantité AS [Coût marchandise],
                @Valorisation AS [Type Valorisation]
            FROM Entête_des_ventes AS e
            INNER JOIN Clients AS c
                ON e.[Code client] = c.[Code client] AND e.societe = c.societe
            INNER JOIN Lignes_des_ventes AS l
                ON e.societe = l.societe AND e.[Type Document] = l.[Type Document] AND e.[N° pièce] = l.[N° Pièce]
            INNER JOIN Articles AS a
                ON l.societe = a.societe AND l.[Code article] = a.[Code Article]
            LEFT JOIN Mouvement_stock AS ms
                ON l.societe = ms.societe AND l.[N° interne] = ms.[N° interne]
            WHERE l.[Date BL] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR e.societe = @societe)
              AND l.[Valorise CA] = 'Oui'
            ORDER BY e.Date DESC, e.[N° pièce]
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global", "required": true, "label": "Date début"}, {"name": "dateFin", "type": "date", "source": "global", "required": true, "label": "Date fin"}, {"name": "societe", "type": "string", "source": "global", "required": false, "label": "Société"}, {"name": "Valorisation", "type": "select", "source": "fixed", "required": true, "label": "Méthode de valorisation", "default": "CMUP", "options": ["CMUP", "CMUP", "DPA-Vente", "DPA-Période", "DPR-Vente"]}, {"name": "ValorisationCA", "type": "select", "source": "fixed", "required": true, "label": "Valorisation CA", "default": "HT", "options": ["HT", "TTC"]}]'
    },
    {
        "code": "DS_CA_AGREGE_CLIENT",
        "nom": "CA Agrégé par Client avec Marge Dynamique",
        "category": "Ventes",
        "description": "CA et marge agrégés par client avec choix de valorisation",
        "query_template": """
            SELECT
                e.societe AS [Société],
                e.[Code client],
                e.[Intitulé client],
                c.Ville,
                c.Région,
                c.[Catégorie tarifaire],
                COUNT(DISTINCT e.[N° pièce]) AS [Nb Documents],
                SUM(l.Quantité) AS [Qte Totale],
                SUM(CASE WHEN @ValorisationCA = 'TTC' THEN l.[Montant TTC Net] ELSE l.[Montant HT Net] END) AS [CA],
                SUM(
                    (CASE WHEN @ValorisationCA = 'TTC' THEN l.[Montant TTC Net] ELSE l.[Montant HT Net] END) -
                    l.Quantité * ISNULL(
                        CASE @Valorisation
                            WHEN 'CMUP' THEN l.CMUP
                            WHEN 'CMUP' THEN l.[CMUP]
                            WHEN 'DPA-Vente' THEN ms.[DPA-Vente]
                            WHEN 'DPA-Période' THEN ms.[DPA-Période]
                            WHEN 'DPR-Vente' THEN ms.[DPR-Vente]
                            ELSE 0
                        END, 0)
                ) AS [Marge],
                CASE WHEN SUM(CASE WHEN @ValorisationCA = 'TTC' THEN l.[Montant TTC Net] ELSE l.[Montant HT Net] END) > 0
                    THEN ROUND(
                        SUM(
                            (CASE WHEN @ValorisationCA = 'TTC' THEN l.[Montant TTC Net] ELSE l.[Montant HT Net] END) -
                            l.Quantité * ISNULL(
                                CASE @Valorisation
                                    WHEN 'CMUP' THEN l.CMUP
                                    WHEN 'CMUP' THEN l.[CMUP]
                                    WHEN 'DPA-Vente' THEN ms.[DPA-Vente]
                                    WHEN 'DPA-Période' THEN ms.[DPA-Période]
                                    WHEN 'DPR-Vente' THEN ms.[DPR-Vente]
                                    ELSE 0
                                END, 0)
                        ) * 100.0 / SUM(CASE WHEN @ValorisationCA = 'TTC' THEN l.[Montant TTC Net] ELSE l.[Montant HT Net] END), 2)
                    ELSE 0 END AS [Marge %],
                SUM(
                    ISNULL(
                        CASE @Valorisation
                            WHEN 'CMUP' THEN l.CMUP
                            WHEN 'CMUP' THEN l.[CMUP]
                            WHEN 'DPA-Vente' THEN ms.[DPA-Vente]
                            WHEN 'DPA-Période' THEN ms.[DPA-Période]
                            WHEN 'DPR-Vente' THEN ms.[DPR-Vente]
                            ELSE 0
                        END, 0) * l.Quantité
                ) AS [Coût marchandise]
            FROM Entête_des_ventes AS e
            INNER JOIN Clients AS c
                ON e.[Code client] = c.[Code client] AND e.societe = c.societe
            INNER JOIN Lignes_des_ventes AS l
                ON e.societe = l.societe AND e.[Type Document] = l.[Type Document] AND e.[N° pièce] = l.[N° Pièce]
            INNER JOIN Articles AS a
                ON l.societe = a.societe AND l.[Code article] = a.[Code Article]
            LEFT JOIN Mouvement_stock AS ms
                ON l.societe = ms.societe AND l.[N° interne] = ms.[N° interne]
            WHERE l.[Date BL] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR e.societe = @societe)
              AND l.[Valorise CA] = 'Oui'
            GROUP BY e.societe, e.[Code client], e.[Intitulé client], c.Ville, c.Région, c.[Catégorie tarifaire]
            ORDER BY [CA] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global", "required": true, "label": "Date début"}, {"name": "dateFin", "type": "date", "source": "global", "required": true, "label": "Date fin"}, {"name": "societe", "type": "string", "source": "global", "required": false, "label": "Société"}, {"name": "Valorisation", "type": "select", "source": "fixed", "required": true, "label": "Méthode de valorisation", "default": "CMUP", "options": ["CMUP", "CMUP", "DPA-Vente", "DPA-Période", "DPR-Vente"]}, {"name": "ValorisationCA", "type": "select", "source": "fixed", "required": true, "label": "Valorisation CA", "default": "HT", "options": ["HT", "TTC"]}]'
    },
    {
        "code": "DS_CA_AGREGE_ARTICLE",
        "nom": "CA Agrégé par Article avec Marge Dynamique",
        "category": "Ventes",
        "description": "CA et marge agrégés par article avec choix de valorisation",
        "query_template": """
            SELECT
                e.societe AS [Société],
                l.[Code article],
                a.[Désignation Article],
                a.[Code Famille],
                a.[Intitulé famille],
                a.[Catalogue 1],
                a.[Catalogue 2],
                COUNT(DISTINCT e.[Code client]) AS [Nb Clients],
                COUNT(DISTINCT e.[N° pièce]) AS [Nb Documents],
                SUM(l.Quantité) AS [Qte Vendue],
                SUM(CASE WHEN @ValorisationCA = 'TTC' THEN l.[Montant TTC Net] ELSE l.[Montant HT Net] END) AS [CA],
                SUM(
                    (CASE WHEN @ValorisationCA = 'TTC' THEN l.[Montant TTC Net] ELSE l.[Montant HT Net] END) -
                    l.Quantité * ISNULL(
                        CASE @Valorisation
                            WHEN 'CMUP' THEN l.CMUP
                            WHEN 'CMUP' THEN l.[CMUP]
                            WHEN 'DPA-Vente' THEN ms.[DPA-Vente]
                            WHEN 'DPA-Période' THEN ms.[DPA-Période]
                            WHEN 'DPR-Vente' THEN ms.[DPR-Vente]
                            ELSE 0
                        END, 0)
                ) AS [Marge],
                CASE WHEN SUM(CASE WHEN @ValorisationCA = 'TTC' THEN l.[Montant TTC Net] ELSE l.[Montant HT Net] END) > 0
                    THEN ROUND(
                        SUM(
                            (CASE WHEN @ValorisationCA = 'TTC' THEN l.[Montant TTC Net] ELSE l.[Montant HT Net] END) -
                            l.Quantité * ISNULL(
                                CASE @Valorisation
                                    WHEN 'CMUP' THEN l.CMUP
                                    WHEN 'CMUP' THEN l.[CMUP]
                                    WHEN 'DPA-Vente' THEN ms.[DPA-Vente]
                                    WHEN 'DPA-Période' THEN ms.[DPA-Période]
                                    WHEN 'DPR-Vente' THEN ms.[DPR-Vente]
                                    ELSE 0
                                END, 0)
                        ) * 100.0 / SUM(CASE WHEN @ValorisationCA = 'TTC' THEN l.[Montant TTC Net] ELSE l.[Montant HT Net] END), 2)
                    ELSE 0 END AS [Marge %],
                AVG(l.[Prix unitaire]) AS [Prix Moyen Vente],
                AVG(
                    CASE @Valorisation
                        WHEN 'CMUP' THEN l.CMUP
                        WHEN 'CMUP' THEN l.[CMUP]
                        WHEN 'DPA-Vente' THEN ms.[DPA-Vente]
                        WHEN 'DPA-Période' THEN ms.[DPA-Période]
                        WHEN 'DPR-Vente' THEN ms.[DPR-Vente]
                        ELSE 0
                    END
                ) AS [Coût Moyen]
            FROM Entête_des_ventes AS e
            INNER JOIN Clients AS c
                ON e.[Code client] = c.[Code client] AND e.societe = c.societe
            INNER JOIN Lignes_des_ventes AS l
                ON e.societe = l.societe AND e.[Type Document] = l.[Type Document] AND e.[N° pièce] = l.[N° Pièce]
            INNER JOIN Articles AS a
                ON l.societe = a.societe AND l.[Code article] = a.[Code Article]
            LEFT JOIN Mouvement_stock AS ms
                ON l.societe = ms.societe AND l.[N° interne] = ms.[N° interne]
            WHERE l.[Date BL] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR e.societe = @societe)
              AND l.[Valorise CA] = 'Oui'
            GROUP BY e.societe, l.[Code article], a.[Désignation Article], a.[Code Famille], a.[Intitulé famille], a.[Catalogue 1], a.[Catalogue 2]
            ORDER BY [CA] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global", "required": true, "label": "Date début"}, {"name": "dateFin", "type": "date", "source": "global", "required": true, "label": "Date fin"}, {"name": "societe", "type": "string", "source": "global", "required": false, "label": "Société"}, {"name": "Valorisation", "type": "select", "source": "fixed", "required": true, "label": "Méthode de valorisation", "default": "CMUP", "options": ["CMUP", "CMUP", "DPA-Vente", "DPA-Période", "DPR-Vente"]}, {"name": "ValorisationCA", "type": "select", "source": "fixed", "required": true, "label": "Valorisation CA", "default": "HT", "options": ["HT", "TTC"]}]'
    },
    {
        "code": "DS_CA_AGREGE_CATALOGUE",
        "nom": "CA Agrégé par Catalogue avec Marge Dynamique",
        "category": "Ventes",
        "description": "CA et marge agrégés par catalogue/famille avec choix de valorisation",
        "query_template": """
            SELECT
                e.societe AS [Société],
                a.[Catalogue 1],
                a.[Catalogue 2],
                a.[Code Famille],
                a.[Intitulé famille],
                COUNT(DISTINCT l.[Code article]) AS [Nb Articles],
                COUNT(DISTINCT e.[Code client]) AS [Nb Clients],
                SUM(l.Quantité) AS [Qte Vendue],
                SUM(CASE WHEN @ValorisationCA = 'TTC' THEN l.[Montant TTC Net] ELSE l.[Montant HT Net] END) AS [CA],
                SUM(
                    (CASE WHEN @ValorisationCA = 'TTC' THEN l.[Montant TTC Net] ELSE l.[Montant HT Net] END) -
                    l.Quantité * ISNULL(
                        CASE @Valorisation
                            WHEN 'CMUP' THEN l.CMUP
                            WHEN 'CMUP' THEN l.[CMUP]
                            WHEN 'DPA-Vente' THEN ms.[DPA-Vente]
                            WHEN 'DPA-Période' THEN ms.[DPA-Période]
                            WHEN 'DPR-Vente' THEN ms.[DPR-Vente]
                            ELSE 0
                        END, 0)
                ) AS [Marge],
                CASE WHEN SUM(CASE WHEN @ValorisationCA = 'TTC' THEN l.[Montant TTC Net] ELSE l.[Montant HT Net] END) > 0
                    THEN ROUND(
                        SUM(
                            (CASE WHEN @ValorisationCA = 'TTC' THEN l.[Montant TTC Net] ELSE l.[Montant HT Net] END) -
                            l.Quantité * ISNULL(
                                CASE @Valorisation
                                    WHEN 'CMUP' THEN l.CMUP
                                    WHEN 'CMUP' THEN l.[CMUP]
                                    WHEN 'DPA-Vente' THEN ms.[DPA-Vente]
                                    WHEN 'DPA-Période' THEN ms.[DPA-Période]
                                    WHEN 'DPR-Vente' THEN ms.[DPR-Vente]
                                    ELSE 0
                                END, 0)
                        ) * 100.0 / SUM(CASE WHEN @ValorisationCA = 'TTC' THEN l.[Montant TTC Net] ELSE l.[Montant HT Net] END), 2)
                    ELSE 0 END AS [Marge %]
            FROM Entête_des_ventes AS e
            INNER JOIN Clients AS c
                ON e.[Code client] = c.[Code client] AND e.societe = c.societe
            INNER JOIN Lignes_des_ventes AS l
                ON e.societe = l.societe AND e.[Type Document] = l.[Type Document] AND e.[N° pièce] = l.[N° Pièce]
            INNER JOIN Articles AS a
                ON l.societe = a.societe AND l.[Code article] = a.[Code Article]
            LEFT JOIN Mouvement_stock AS ms
                ON l.societe = ms.societe AND l.[N° interne] = ms.[N° interne]
            WHERE l.[Date BL] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR e.societe = @societe)
              AND l.[Valorise CA] = 'Oui'
            GROUP BY e.societe, a.[Catalogue 1], a.[Catalogue 2], a.[Code Famille], a.[Intitulé famille]
            ORDER BY [CA] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global", "required": true, "label": "Date début"}, {"name": "dateFin", "type": "date", "source": "global", "required": true, "label": "Date fin"}, {"name": "societe", "type": "string", "source": "global", "required": false, "label": "Société"}, {"name": "Valorisation", "type": "select", "source": "fixed", "required": true, "label": "Méthode de valorisation", "default": "CMUP", "options": ["CMUP", "CMUP", "DPA-Vente", "DPA-Période", "DPR-Vente"]}, {"name": "ValorisationCA", "type": "select", "source": "fixed", "required": true, "label": "Valorisation CA", "default": "HT", "options": ["HT", "TTC"]}]'
    },
    {
        "code": "DS_CA_AGREGE_REPRESENTANT",
        "nom": "CA Agrégé par Représentant avec Marge Dynamique",
        "category": "Ventes",
        "description": "CA et marge agrégés par représentant/commercial avec choix de valorisation",
        "query_template": """
            SELECT
                e.societe AS [Société],
                e.[Nom représentant] AS [Représentant],
                COUNT(DISTINCT e.[Code client]) AS [Nb Clients],
                COUNT(DISTINCT e.[N° pièce]) AS [Nb Documents],
                SUM(l.Quantité) AS [Qte Vendue],
                SUM(CASE WHEN @ValorisationCA = 'TTC' THEN l.[Montant TTC Net] ELSE l.[Montant HT Net] END) AS [CA],
                SUM(
                    (CASE WHEN @ValorisationCA = 'TTC' THEN l.[Montant TTC Net] ELSE l.[Montant HT Net] END) -
                    l.Quantité * ISNULL(
                        CASE @Valorisation
                            WHEN 'CMUP' THEN l.CMUP
                            WHEN 'CMUP' THEN l.[CMUP]
                            WHEN 'DPA-Vente' THEN ms.[DPA-Vente]
                            WHEN 'DPA-Période' THEN ms.[DPA-Période]
                            WHEN 'DPR-Vente' THEN ms.[DPR-Vente]
                            ELSE 0
                        END, 0)
                ) AS [Marge],
                CASE WHEN SUM(CASE WHEN @ValorisationCA = 'TTC' THEN l.[Montant TTC Net] ELSE l.[Montant HT Net] END) > 0
                    THEN ROUND(
                        SUM(
                            (CASE WHEN @ValorisationCA = 'TTC' THEN l.[Montant TTC Net] ELSE l.[Montant HT Net] END) -
                            l.Quantité * ISNULL(
                                CASE @Valorisation
                                    WHEN 'CMUP' THEN l.CMUP
                                    WHEN 'CMUP' THEN l.[CMUP]
                                    WHEN 'DPA-Vente' THEN ms.[DPA-Vente]
                                    WHEN 'DPA-Période' THEN ms.[DPA-Période]
                                    WHEN 'DPR-Vente' THEN ms.[DPR-Vente]
                                    ELSE 0
                                END, 0)
                        ) * 100.0 / SUM(CASE WHEN @ValorisationCA = 'TTC' THEN l.[Montant TTC Net] ELSE l.[Montant HT Net] END), 2)
                    ELSE 0 END AS [Marge %]
            FROM Entête_des_ventes AS e
            INNER JOIN Clients AS c
                ON e.[Code client] = c.[Code client] AND e.societe = c.societe
            INNER JOIN Lignes_des_ventes AS l
                ON e.societe = l.societe AND e.[Type Document] = l.[Type Document] AND e.[N° pièce] = l.[N° Pièce]
            INNER JOIN Articles AS a
                ON l.societe = a.societe AND l.[Code article] = a.[Code Article]
            LEFT JOIN Mouvement_stock AS ms
                ON l.societe = ms.societe AND l.[N° interne] = ms.[N° interne]
            WHERE l.[Date BL] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR e.societe = @societe)
              AND l.[Valorise CA] = 'Oui'
            GROUP BY e.societe, e.[Nom représentant]
            ORDER BY [CA] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global", "required": true, "label": "Date début"}, {"name": "dateFin", "type": "date", "source": "global", "required": true, "label": "Date fin"}, {"name": "societe", "type": "string", "source": "global", "required": false, "label": "Société"}, {"name": "Valorisation", "type": "select", "source": "fixed", "required": true, "label": "Méthode de valorisation", "default": "CMUP", "options": ["CMUP", "CMUP", "DPA-Vente", "DPA-Période", "DPR-Vente"]}, {"name": "ValorisationCA", "type": "select", "source": "fixed", "required": true, "label": "Valorisation CA", "default": "HT", "options": ["HT", "TTC"]}]'
    },
    {
        "code": "DS_CA_PAR_MOIS_DYNAMIQUE",
        "nom": "CA Mensuel avec Marge Dynamique",
        "category": "Ventes",
        "description": "Evolution mensuelle du CA et marge avec choix de valorisation",
        "query_template": """
            SELECT
                e.societe AS [Société],
                YEAR(l.[Date BL]) AS [Année],
                MONTH(l.[Date BL]) AS [Mois],
                FORMAT(l.[Date BL], 'yyyy-MM') AS [Période],
                COUNT(DISTINCT e.[Code client]) AS [Nb Clients],
                COUNT(DISTINCT e.[N° pièce]) AS [Nb Documents],
                SUM(l.Quantité) AS [Qte Vendue],
                SUM(CASE WHEN @ValorisationCA = 'TTC' THEN l.[Montant TTC Net] ELSE l.[Montant HT Net] END) AS [CA],
                SUM(
                    (CASE WHEN @ValorisationCA = 'TTC' THEN l.[Montant TTC Net] ELSE l.[Montant HT Net] END) -
                    l.Quantité * ISNULL(
                        CASE @Valorisation
                            WHEN 'CMUP' THEN l.CMUP
                            WHEN 'CMUP' THEN l.[CMUP]
                            WHEN 'DPA-Vente' THEN ms.[DPA-Vente]
                            WHEN 'DPA-Période' THEN ms.[DPA-Période]
                            WHEN 'DPR-Vente' THEN ms.[DPR-Vente]
                            ELSE 0
                        END, 0)
                ) AS [Marge],
                CASE WHEN SUM(CASE WHEN @ValorisationCA = 'TTC' THEN l.[Montant TTC Net] ELSE l.[Montant HT Net] END) > 0
                    THEN ROUND(
                        SUM(
                            (CASE WHEN @ValorisationCA = 'TTC' THEN l.[Montant TTC Net] ELSE l.[Montant HT Net] END) -
                            l.Quantité * ISNULL(
                                CASE @Valorisation
                                    WHEN 'CMUP' THEN l.CMUP
                                    WHEN 'CMUP' THEN l.[CMUP]
                                    WHEN 'DPA-Vente' THEN ms.[DPA-Vente]
                                    WHEN 'DPA-Période' THEN ms.[DPA-Période]
                                    WHEN 'DPR-Vente' THEN ms.[DPR-Vente]
                                    ELSE 0
                                END, 0)
                        ) * 100.0 / SUM(CASE WHEN @ValorisationCA = 'TTC' THEN l.[Montant TTC Net] ELSE l.[Montant HT Net] END), 2)
                    ELSE 0 END AS [Marge %]
            FROM Entête_des_ventes AS e
            INNER JOIN Clients AS c
                ON e.[Code client] = c.[Code client] AND e.societe = c.societe
            INNER JOIN Lignes_des_ventes AS l
                ON e.societe = l.societe AND e.[Type Document] = l.[Type Document] AND e.[N° pièce] = l.[N° Pièce]
            INNER JOIN Articles AS a
                ON l.societe = a.societe AND l.[Code article] = a.[Code Article]
            LEFT JOIN Mouvement_stock AS ms
                ON l.societe = ms.societe AND l.[N° interne] = ms.[N° interne]
            WHERE l.[Date BL] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR e.societe = @societe)
              AND l.[Valorise CA] = 'Oui'
            GROUP BY e.societe, YEAR(l.[Date BL]), MONTH(l.[Date BL]), FORMAT(l.[Date BL], 'yyyy-MM')
            ORDER BY [Année], [Mois]
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global", "required": true, "label": "Date début"}, {"name": "dateFin", "type": "date", "source": "global", "required": true, "label": "Date fin"}, {"name": "societe", "type": "string", "source": "global", "required": false, "label": "Société"}, {"name": "Valorisation", "type": "select", "source": "fixed", "required": true, "label": "Méthode de valorisation", "default": "CMUP", "options": ["CMUP", "CMUP", "DPA-Vente", "DPA-Période", "DPR-Vente"]}, {"name": "ValorisationCA", "type": "select", "source": "fixed", "required": true, "label": "Valorisation CA", "default": "HT", "options": ["HT", "TTC"]}]'
    },

    # ==================== PIVOT VENTES LIGNES (datasource riche pour pivot builder) ====================
    # Datasource ligne-par-ligne avec toutes les dimensions et mesures brutes.
    # Idéal pour le pivot builder : ~50 champs disponibles, agrégation dynamique.
    {
        "code": "DS_PIVOT_VENTES_LIGNES",
        "nom": "Ventes – Lignes Détail (Pivot)",
        "category": "Ventes",
        "description": "Datasource ligne-par-ligne pour pivot builder : toutes les dimensions (Client, Commercial, Article, Famille, Dépôt, Région, Période…) et mesures brutes (CA HT, TTC, Marge, Quantité, Poids…). ~50 champs disponibles.",
        "query_template": """
            SELECT
                -- SOCIÉTÉ
                li.[societe]                                                AS [Société],

                -- DIMENSIONS TEMPORELLES
                li.[Date BL]                                                AS [Date BL],
                li.[Date document]                                          AS [Date Document],
                YEAR(li.[Date BL])                                          AS [Année],
                MONTH(li.[Date BL])                                         AS [Mois Num],
                FORMAT(li.[Date BL], 'MMMM', 'fr-FR')                      AS [Mois],
                DATEPART(QUARTER, li.[Date BL])                             AS [Trimestre Num],
                'T' + CAST(DATEPART(QUARTER, li.[Date BL]) AS VARCHAR)     AS [Trimestre],
                FORMAT(li.[Date BL], 'yyyy-MM')                             AS [Période],
                FORMAT(li.[Date BL], 'yyyy') + ' T'
                    + CAST(DATEPART(QUARTER, li.[Date BL]) AS VARCHAR)      AS [Trim Année],
                FORMAT(li.[Date BL], 'yyyy')
                    + CASE WHEN MONTH(li.[Date BL]) <= 6 THEN ' S1' ELSE ' S2' END
                                                                            AS [Semestre],

                -- DIMENSIONS CLIENT
                li.[Code client]                                            AS [Code Client],
                li.[Intitulé client]                                        AS [Client],
                ISNULL(cl.[Région], '')                                     AS [Région],
                ISNULL(cl.[Ville], '')                                      AS [Ville],
                ISNULL(cl.[Pays], '')                                       AS [Pays],
                ISNULL(cl.[Classement], '')                                 AS [Classement Client],
                ISNULL(cl.[Catégorie tarifaire], '')                        AS [Catégorie Tarifaire],

                -- DIMENSIONS COMMERCIAL
                ISNULL(CAST(en.[Code représentant] AS VARCHAR), '')         AS [Code Commercial],
                ISNULL(en.[Nom représentant], 'Non affecté')               AS [Commercial],

                -- DIMENSIONS ARTICLE
                li.[Code article]                                            AS [Code Article],
                li.[Désignation ligne]                                       AS [Désignation],
                ISNULL(li.[Catalogue 1], '')                                 AS [Famille],
                ISNULL(li.[Catalogue 2], '')                                 AS [Sous Famille],
                ISNULL(li.[Catalogue 3], '')                                 AS [Catalogue 3],
                ISNULL(li.[Catalogue 4], '')                                 AS [Catalogue 4],
                ISNULL(li.[Gamme 1], '')                                     AS [Gamme 1],
                ISNULL(li.[Gamme 2], '')                                     AS [Gamme 2],

                -- DIMENSIONS DOCUMENT
                li.[Type Document],
                li.[N° Pièce]                                                AS [Num Pièce],
                ISNULL(en.[Statut], '')                                      AS [Statut Document],
                ISNULL(en.[Souche], '')                                      AS [Souche],
                ISNULL(en.[Catégorie Comptable], '')                         AS [Catégorie Comptable],
                ISNULL(en.[Intitulé tiers payeur], '')                       AS [Tiers Payeur],
                ISNULL(en.[Expédition], '')                                  AS [Expédition],

                -- DIMENSIONS DÉPÔT
                ISNULL(CAST(li.[Code dépôt] AS VARCHAR), '')                 AS [Code Dépôt],
                ISNULL(li.[Intitulé dépôt], '')                              AS [Dépôt],

                -- DIMENSIONS AFFAIRE / LOT
                ISNULL(li.[Code d'affaire], '')                              AS [Code Affaire],
                ISNULL(li.[Intitulé affaire], '')                            AS [Affaire],
                ISNULL(li.[N° Série/Lot], '')                                AS [Lot Série],

                -- MESURES BRUTES
                li.[Montant HT Net]                                          AS [CA HT],
                li.[Montant TTC Net]                                         AS [CA TTC],
                li.[Quantité]                                                AS [Quantité],
                li.[Prix unitaire]                                           AS [Prix Unitaire HT],
                ISNULL(li.[CMUP], 0)                                         AS [Coût Revient Unit],
                li.[Quantité] * ISNULL(li.[CMUP], 0)                        AS [Coût Revient],
                li.[Montant HT Net] - li.[Quantité] * ISNULL(li.[CMUP], 0)  AS [Marge],
                ISNULL(li.[Poids net], 0)                                    AS [Poids Net],
                ISNULL(li.[Poids brut], 0)                                   AS [Poids Brut],
                ISNULL(li.[Remise 1], 0)                                     AS [Remise 1 %],
                ISNULL(li.[Frais d'approche], 0)                             AS [Frais Approche],
                1                                                            AS [Nb Lignes]

            FROM [Lignes_des_ventes] li
            INNER JOIN [Entête_des_ventes] en
                ON li.[DB_Id]        = en.[DB_Id]
               AND li.[Type Document] = en.[Type Document]
               AND li.[N° Pièce]     = en.[N° pièce]
            LEFT JOIN [Clients] cl
                ON li.[DB_Id]      = cl.[DB_Id]
               AND li.[Code client] = cl.[Code client]
            WHERE li.[Valorise CA] = 'Oui'
              AND (@societe IS NULL OR li.[societe] = @societe)
              AND li.[Date BL] BETWEEN @dateDebut AND @dateFin
              AND (@commercial IS NULL OR en.[Nom représentant] = @commercial)
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}, {"name": "commercial", "type": "select", "source": "query", "query": "SELECT DISTINCT [Nom représentant] AS value, [Nom représentant] AS label FROM [Entête_des_ventes] WHERE [Nom représentant] IS NOT NULL AND [Nom représentant] <> \\'\\' ORDER BY [Nom représentant]", "required": false, "allow_null": true, "null_label": "(Tous)"}]'
    },

    # ==================== ACHATS ====================
    # Basé sur les tables Entête_des_achats, Lignes_des_achats, Fournisseurs, Articles
    # Types Documents: Préparation de commande, Bon de commande, Bon de Réception,
    #                  Bon de retour, Bon avoir, Facture, Facture comptabilisée

    # --- Achats Globaux ---
    {
        "code": "DS_ACHATS_GLOBAL",
        "nom": "Achats Global",
        "category": "Achats",
        "description": "Synthese globale des achats",
        "query_template": """
            SELECT
                l.[societe] AS [Société],
                SUM(l.[Montant HT Net]) AS [Achats HT],
                SUM(l.[Montant TTC Net]) AS [Achats TTC],
                COUNT(DISTINCT l.[Code fournisseur]) AS [Nb Fournisseurs],
                COUNT(DISTINCT l.[N° Pièce]) AS [Nb Documents],
                SUM(l.[Quantité]) AS [Qte Totale],
                COUNT(*) AS [Nb Lignes],
                CASE WHEN COUNT(DISTINCT l.[Code fournisseur]) > 0
                    THEN ROUND(SUM(l.[Montant HT Net]) / COUNT(DISTINCT l.[Code fournisseur]), 2)
                    ELSE 0 END AS [Achat Moyen par Fournisseur],
                CASE WHEN COUNT(DISTINCT l.[N° Pièce]) > 0
                    THEN ROUND(SUM(l.[Montant HT Net]) / COUNT(DISTINCT l.[N° Pièce]), 2)
                    ELSE 0 END AS [Achat Moyen par Document]
            FROM [Lignes_des_achats] l
            WHERE l.[Type Document] IN ('Facture', 'Facture comptabilisée')
              AND l.[Valorise CA] = 'Oui'
              AND (@societe IS NULL OR l.[societe] = @societe)
              AND l.[Date BL] BETWEEN @dateDebut AND @dateFin
            GROUP BY l.[societe]
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_ACHATS_PAR_MOIS",
        "nom": "Achats par Mois",
        "category": "Achats",
        "description": "Evolution mensuelle des achats",
        "query_template": """
            SELECT
                FORMAT(l.[Date BL], 'yyyy-MM') AS [Mois],
                l.[societe] AS [Société],
                SUM(l.[Montant HT Net]) AS [Achats HT],
                SUM(l.[Montant TTC Net]) AS [Achats TTC],
                COUNT(DISTINCT l.[Code fournisseur]) AS [Nb Fournisseurs],
                COUNT(DISTINCT l.[N° Pièce]) AS [Nb Documents],
                SUM(l.[Quantité]) AS [Qte Totale]
            FROM [Lignes_des_achats] l
            WHERE l.[Type Document] IN ('Facture', 'Facture comptabilisée')
              AND l.[Valorise CA] = 'Oui'
              AND (@societe IS NULL OR l.[societe] = @societe)
              AND l.[Date BL] BETWEEN @dateDebut AND @dateFin
            GROUP BY FORMAT(l.[Date BL], 'yyyy-MM'), l.[societe]
            ORDER BY [Mois] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_ACHATS_PAR_FOURNISSEUR",
        "nom": "Achats par Fournisseur",
        "category": "Achats",
        "description": "Achats agreges par fournisseur",
        "query_template": """
            SELECT
                l.[Code fournisseur] AS [Code Fournisseur],
                l.[Intitulé fournisseur] AS [Fournisseur],
                f.[Qualité] AS [Qualite],
                f.[Acheteur],
                f.[Catégorie tarifaire] AS [Categorie Tarifaire],
                l.[societe] AS [Société],
                SUM(l.[Montant HT Net]) AS [Achats HT],
                SUM(l.[Montant TTC Net]) AS [Achats TTC],
                COUNT(DISTINCT l.[N° Pièce]) AS [Nb Documents],
                SUM(l.[Quantité]) AS [Qte Totale],
                COUNT(DISTINCT l.[Code article]) AS [Nb Articles],
                CASE WHEN COUNT(DISTINCT l.[N° Pièce]) > 0
                    THEN ROUND(SUM(l.[Montant HT Net]) / COUNT(DISTINCT l.[N° Pièce]), 2)
                    ELSE 0 END AS [Achat Moyen par Document],
                CASE WHEN SUM(l.[Quantité]) > 0
                    THEN ROUND(SUM(l.[Montant HT Net]) / SUM(l.[Quantité]), 2)
                    ELSE 0 END AS [Prix Moyen Unitaire]
            FROM [Lignes_des_achats] l
            INNER JOIN [Fournisseurs] f ON l.[DB_Id] = f.[DB_Id] AND l.[Code fournisseur] = f.[Code fournisseur]
            WHERE l.[Type Document] IN ('Facture', 'Facture comptabilisée')
              AND l.[Valorise CA] = 'Oui'
              AND (@societe IS NULL OR l.[societe] = @societe)
              AND l.[Date BL] BETWEEN @dateDebut AND @dateFin
            GROUP BY l.[Code fournisseur], l.[Intitulé fournisseur], f.[Qualité], f.[Acheteur], f.[Catégorie tarifaire], l.[societe]
            ORDER BY [Achats HT] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_ACHATS_PAR_ARTICLE",
        "nom": "Achats par Article",
        "category": "Achats",
        "description": "Achats agreges par article",
        "query_template": """
            SELECT
                l.[Code article] AS [Code Article],
                a.[Désignation Article] AS [Designation],
                a.[Code Famille],
                a.[Intitulé famille] AS [Famille],
                a.[Catalogue 1],
                l.[societe] AS [Société],
                SUM(l.[Quantité]) AS [Qte Achetee],
                SUM(l.[Montant HT Net]) AS [Achats HT],
                AVG(l.[Prix unitaire]) AS [Prix Moyen],
                AVG(l.[CMUP]) AS [CMUP Moyen],
                COUNT(DISTINCT l.[Code fournisseur]) AS [Nb Fournisseurs],
                COUNT(DISTINCT l.[N° Pièce]) AS [Nb Documents]
            FROM [Lignes_des_achats] l
            INNER JOIN [Articles] a ON l.[DB_Id] = a.[DB_Id] AND l.[Code article] = a.[Code Article]
            WHERE l.[Type Document] IN ('Facture', 'Facture comptabilisée')
              AND l.[Valorise CA] = 'Oui'
              AND (@societe IS NULL OR l.[societe] = @societe)
              AND l.[Date BL] BETWEEN @dateDebut AND @dateFin
            GROUP BY l.[Code article], a.[Désignation Article], a.[Code Famille], a.[Intitulé famille], a.[Catalogue 1], l.[societe]
            ORDER BY [Achats HT] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_ACHATS_PAR_FAMILLE",
        "nom": "Achats par Famille",
        "category": "Achats",
        "description": "Achats agreges par famille d'articles",
        "query_template": """
            SELECT
                a.[Code Famille],
                a.[Intitulé famille] AS [Famille],
                l.[societe] AS [Société],
                SUM(l.[Quantité]) AS [Qte Achetee],
                SUM(l.[Montant HT Net]) AS [Achats HT],
                SUM(l.[Montant TTC Net]) AS [Achats TTC],
                COUNT(DISTINCT l.[Code article]) AS [Nb Articles],
                COUNT(DISTINCT l.[Code fournisseur]) AS [Nb Fournisseurs],
                CASE WHEN COUNT(DISTINCT l.[Code article]) > 0
                    THEN ROUND(SUM(l.[Montant HT Net]) / COUNT(DISTINCT l.[Code article]), 2)
                    ELSE 0 END AS [Achat Moyen par Article]
            FROM [Lignes_des_achats] l
            INNER JOIN [Articles] a ON l.[DB_Id] = a.[DB_Id] AND l.[Code article] = a.[Code Article]
            WHERE l.[Type Document] IN ('Facture', 'Facture comptabilisée')
              AND l.[Valorise CA] = 'Oui'
              AND (@societe IS NULL OR l.[societe] = @societe)
              AND l.[Date BL] BETWEEN @dateDebut AND @dateFin
            GROUP BY a.[Code Famille], a.[Intitulé famille], l.[societe]
            ORDER BY [Achats HT] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_ACHATS_PAR_TYPE_DOC",
        "nom": "Achats par Type Document",
        "category": "Achats",
        "description": "Achats par type de document",
        "query_template": """
            SELECT
                l.[Type Document],
                l.[societe] AS [Société],
                COUNT(DISTINCT l.[N° Pièce]) AS [Nb Documents],
                SUM(l.[Quantité]) AS [Qte Totale],
                SUM(l.[Montant HT Net]) AS [Montant HT],
                SUM(l.[Montant TTC Net]) AS [Montant TTC],
                COUNT(DISTINCT l.[Code fournisseur]) AS [Nb Fournisseurs],
                COUNT(DISTINCT l.[Code article]) AS [Nb Articles]
            FROM [Lignes_des_achats] l
            WHERE l.[Date] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR l.[societe] = @societe)
            GROUP BY l.[Type Document], l.[societe]
            ORDER BY [Montant HT] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- Documents Achats specifiques ---
    {
        "code": "DS_FACTURES_ACHATS",
        "nom": "Factures Achats",
        "category": "Achats",
        "description": "Liste des factures fournisseurs",
        "query_template": """
            SELECT
                l.[Date],
                l.[N° Pièce] AS [N Piece],
                l.[Code fournisseur] AS [Code Fournisseur],
                l.[Intitulé fournisseur] AS [Fournisseur],
                l.[Code article] AS [Code Article],
                l.[Désignation] AS [Designation],
                l.[Quantité] AS [Quantite],
                l.[Prix unitaire] AS [Prix Unitaire],
                l.[Montant HT Net] AS [Montant HT],
                l.[Montant TTC Net] AS [Montant TTC],
                l.[CMUP],
                l.[Frais d'approche] AS [Frais Approche],
                l.[societe] AS [Société]
            FROM [Lignes_des_achats] l
            WHERE l.[Type Document] IN ('Facture', 'Facture comptabilisée')
              AND (@societe IS NULL OR l.[societe] = @societe)
              AND l.[Date] BETWEEN @dateDebut AND @dateFin
            ORDER BY l.[Date] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_BONS_RECEPTION",
        "nom": "Bons de Reception",
        "category": "Achats",
        "description": "Liste des bons de reception",
        "query_template": """
            SELECT
                l.[Date],
                l.[N° Pièce] AS [N Piece],
                l.[Code fournisseur] AS [Code Fournisseur],
                l.[Intitulé fournisseur] AS [Fournisseur],
                l.[Code article] AS [Code Article],
                l.[Désignation] AS [Designation],
                l.[Quantité] AS [Quantite],
                l.[Prix unitaire] AS [Prix Unitaire],
                l.[Montant HT Net] AS [Montant HT],
                l.[N° Pièce BC] AS [N BC],
                l.[Date BC],
                l.[societe] AS [Société]
            FROM [Lignes_des_achats] l
            WHERE l.[Type Document] = 'Bon de Réception'
              AND (@societe IS NULL OR l.[societe] = @societe)
              AND l.[Date] BETWEEN @dateDebut AND @dateFin
            ORDER BY l.[Date] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_COMMANDES_ACHATS",
        "nom": "Bons de Commande Achats",
        "category": "Achats",
        "description": "Liste des commandes fournisseurs",
        "query_template": """
            SELECT
                l.[Date],
                l.[N° Pièce] AS [N Piece],
                l.[Code fournisseur] AS [Code Fournisseur],
                l.[Intitulé fournisseur] AS [Fournisseur],
                l.[Code article] AS [Code Article],
                l.[Désignation] AS [Designation],
                l.[Quantité] AS [Quantite],
                l.[Prix unitaire] AS [Prix Unitaire],
                l.[Montant HT Net] AS [Montant HT],
                l.[Date Livraison] AS [Date Livraison Prevue],
                e.[Statut],
                e.[Document clôturé] AS [Cloture],
                l.[societe] AS [Société]
            FROM [Lignes_des_achats] l
            INNER JOIN [Entête_des_achats] e ON l.[DB_Id] = e.[DB_Id] AND l.[Type Document] = e.[Type Document] AND l.[N° Pièce] = e.[N° Pièce]
            WHERE l.[Type Document] = 'Bon de commande'
              AND (@societe IS NULL OR l.[societe] = @societe)
              AND l.[Date] BETWEEN @dateDebut AND @dateFin
            ORDER BY l.[Date] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_AVOIRS_ACHATS",
        "nom": "Avoirs Achats",
        "category": "Achats",
        "description": "Liste des avoirs fournisseurs",
        "query_template": """
            SELECT
                l.[Date],
                l.[N° Pièce] AS [N Piece],
                l.[Type Document],
                l.[Code fournisseur] AS [Code Fournisseur],
                l.[Intitulé fournisseur] AS [Fournisseur],
                l.[Code article] AS [Code Article],
                l.[Désignation] AS [Designation],
                l.[Quantité] AS [Quantite],
                l.[Montant HT Net] AS [Montant HT],
                l.[Montant TTC Net] AS [Montant TTC],
                l.[societe] AS [Société]
            FROM [Lignes_des_achats] l
            WHERE l.[Type Document] IN ('Bon avoir', 'Bon de retour')
              AND (@societe IS NULL OR l.[societe] = @societe)
              AND l.[Date] BETWEEN @dateDebut AND @dateFin
            ORDER BY l.[Date] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- Achats Detail Complet ---
    {
        "code": "DS_ACHATS_DETAIL",
        "nom": "Achats Detail Complet",
        "category": "Achats",
        "description": "Detail complet des achats avec toutes les informations",
        "query_template": """
            SELECT
                l.[societe] AS [Société],
                l.[Type Document],
                l.[Valorise CA],
                l.[Code fournisseur] AS [Code Fournisseur],
                l.[Intitulé fournisseur] AS [Fournisseur],
                l.[N° Pièce] AS [N Piece],
                l.[Référence] AS [Reference],
                l.[Intitulé affaire] AS [Affaire],
                l.[Code d'affaire] AS [Code Affaire],
                l.[Date],
                l.[N° Pièce BL] AS [N BL],
                l.[Date BL],
                l.[N° Pièce BC] AS [N BC],
                l.[Date BC],
                l.[N° pièce PL] AS [N PL],
                l.[Date PL],
                l.[Date Livraison],
                l.[Code article] AS [Code Article],
                l.[Désignation] AS [Designation],
                l.[Gamme 1],
                l.[Gamme 2],
                l.[Poids brut] AS [Poids Brut],
                l.[Poids net] AS [Poids Net],
                l.[N° Série/Lot] AS [Lot Serie],
                l.[Frais d'approche] AS [Frais Approche],
                l.[PU Devise] AS [Prix Devise],
                l.[CMUP],
                l.[Prix unitaire] AS [Prix Unitaire],
                l.[Prix unitaire TTC] AS [Prix TTC],
                l.[Quantité] AS [Quantite],
                l.[Montant HT Net] AS [Montant HT],
                l.[Montant TTC Net] AS [Montant TTC],
                l.[CMUP] AS [Prix Revient],
                a.[Code Famille],
                a.[Intitulé famille] AS [Famille],
                a.[Catalogue 1],
                a.[Catalogue 2],
                a.[Unité Vente] AS [Unite],
                f.[Qualité] AS [Qualite Fournisseur],
                f.[Acheteur],
                f.[Catégorie tarifaire] AS [Categorie Tarifaire],
                e.[Encours],
                e.[Statut],
                e.[Document clôturé] AS [Cloture],
                e.[Devise],
                e.[Montant réglé] AS [Montant Regle]
            FROM [Lignes_des_achats] l
            INNER JOIN [Entête_des_achats] e ON l.[DB_Id] = e.[DB_Id] AND l.[Type Document] = e.[Type Document] AND l.[N° Pièce] = e.[N° Pièce]
            INNER JOIN [Fournisseurs] f ON l.[DB_Id] = f.[DB_Id] AND l.[Code fournisseur] = f.[Code fournisseur]
            INNER JOIN [Articles] a ON l.[DB_Id] = a.[DB_Id] AND l.[Code article] = a.[Code Article]
            WHERE l.[Date] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR l.[societe] = @societe)
            ORDER BY l.[Date] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- Commandes en cours ---
    {
        "code": "DS_COMMANDES_ACHATS_EN_COURS",
        "nom": "Commandes Achats en Cours",
        "category": "Achats",
        "description": "Commandes fournisseurs non cloturees",
        "query_template": """
            SELECT
                l.[Date],
                l.[N° Pièce] AS [N Piece],
                l.[Code fournisseur] AS [Code Fournisseur],
                l.[Intitulé fournisseur] AS [Fournisseur],
                l.[Code article] AS [Code Article],
                l.[Désignation] AS [Designation],
                l.[Quantité] AS [Qte Commandee],
                l.[Prix unitaire] AS [Prix Unitaire],
                l.[Montant HT Net] AS [Montant HT],
                l.[Date Livraison] AS [Date Livraison Prevue],
                e.[Statut],
                e.[Encours],
                DATEDIFF(DAY, l.[Date], GETDATE()) AS [Age Jours],
                l.[societe] AS [Société]
            FROM [Lignes_des_achats] l
            INNER JOIN [Entête_des_achats] e ON l.[DB_Id] = e.[DB_Id] AND l.[Type Document] = e.[Type Document] AND l.[N° Pièce] = e.[N° Pièce]
            WHERE l.[Type Document] = 'Bon de commande'
              AND (@societe IS NULL OR l.[societe] = @societe)
              AND (e.[Document clôturé] IS NULL OR e.[Document clôturé] = 'Non')
            ORDER BY l.[Date Livraison]
        """,
        "parameters": '[{"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- Top Fournisseurs et Articles ---
    {
        "code": "DS_TOP_FOURNISSEURS",
        "nom": "Top Fournisseurs",
        "category": "Achats",
        "description": "Top fournisseurs par volume d'achats",
        "query_template": """
            SELECT TOP 50
                l.[Code fournisseur] AS [Code Fournisseur],
                l.[Intitulé fournisseur] AS [Fournisseur],
                f.[Qualité] AS [Qualite],
                f.[Acheteur],
                l.[societe] AS [Société],
                SUM(l.[Montant HT Net]) AS [Achats HT],
                COUNT(DISTINCT l.[N° Pièce]) AS [Nb Factures],
                COUNT(DISTINCT l.[Code article]) AS [Nb Articles],
                SUM(l.[Quantité]) AS [Qte Totale]
            FROM [Lignes_des_achats] l
            INNER JOIN [Fournisseurs] f ON l.[DB_Id] = f.[DB_Id] AND l.[Code fournisseur] = f.[Code fournisseur]
            WHERE l.[Type Document] IN ('Facture', 'Facture comptabilisée')
              AND l.[Valorise CA] = 'Oui'
              AND (@societe IS NULL OR l.[societe] = @societe)
              AND l.[Date BL] BETWEEN @dateDebut AND @dateFin
            GROUP BY l.[Code fournisseur], l.[Intitulé fournisseur], f.[Qualité], f.[Acheteur], l.[societe]
            ORDER BY [Achats HT] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_TOP_ARTICLES_ACHATS",
        "nom": "Top Articles Achetes",
        "category": "Achats",
        "description": "Articles les plus achetes",
        "query_template": """
            SELECT TOP 50
                l.[Code article] AS [Code Article],
                a.[Désignation Article] AS [Designation],
                a.[Intitulé famille] AS [Famille],
                l.[societe] AS [Société],
                SUM(l.[Quantité]) AS [Qte Achetee],
                SUM(l.[Montant HT Net]) AS [Achats HT],
                AVG(l.[Prix unitaire]) AS [Prix Moyen],
                COUNT(DISTINCT l.[Code fournisseur]) AS [Nb Fournisseurs]
            FROM [Lignes_des_achats] l
            INNER JOIN [Articles] a ON l.[DB_Id] = a.[DB_Id] AND l.[Code article] = a.[Code Article]
            WHERE l.[Type Document] IN ('Facture', 'Facture comptabilisée')
              AND l.[Valorise CA] = 'Oui'
              AND (@societe IS NULL OR l.[societe] = @societe)
              AND l.[Date BL] BETWEEN @dateDebut AND @dateFin
            GROUP BY l.[Code article], a.[Désignation Article], a.[Intitulé famille], l.[societe]
            ORDER BY [Achats HT] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- Achats par Affaire ---
    {
        "code": "DS_ACHATS_PAR_AFFAIRE",
        "nom": "Achats par Affaire",
        "category": "Achats",
        "description": "Achats agreges par affaire/projet",
        "query_template": """
            SELECT
                l.[Code d'affaire] AS [Code Affaire],
                l.[Intitulé affaire] AS [Affaire],
                l.[societe] AS [Société],
                SUM(l.[Montant HT Net]) AS [Achats HT],
                SUM(l.[Montant TTC Net]) AS [Achats TTC],
                COUNT(DISTINCT l.[Code fournisseur]) AS [Nb Fournisseurs],
                COUNT(DISTINCT l.[Code article]) AS [Nb Articles],
                COUNT(DISTINCT l.[N° Pièce]) AS [Nb Documents]
            FROM [Lignes_des_achats] l
            WHERE l.[Code d'affaire] IS NOT NULL AND l.[Code d'affaire] <> ''
              AND (@societe IS NULL OR l.[societe] = @societe)
              AND l.[Type Document] IN ('Facture', 'Facture comptabilisée')
              AND l.[Valorise CA] = 'Oui'
              AND l.[Date BL] BETWEEN @dateDebut AND @dateFin
            GROUP BY l.[Code d'affaire], l.[Intitulé affaire], l.[societe]
            ORDER BY [Achats HT] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- Achats par Acheteur ---
    {
        "code": "DS_ACHATS_PAR_ACHETEUR",
        "nom": "Achats par Acheteur",
        "category": "Achats",
        "description": "Achats agreges par acheteur",
        "query_template": """
            SELECT
                f.[Acheteur],
                l.[societe] AS [Société],
                SUM(l.[Montant HT Net]) AS [Achats HT],
                SUM(l.[Montant TTC Net]) AS [Achats TTC],
                COUNT(DISTINCT l.[Code fournisseur]) AS [Nb Fournisseurs],
                COUNT(DISTINCT l.[N° Pièce]) AS [Nb Documents],
                COUNT(DISTINCT l.[Code article]) AS [Nb Articles]
            FROM [Lignes_des_achats] l
            INNER JOIN [Fournisseurs] f ON l.[DB_Id] = f.[DB_Id] AND l.[Code fournisseur] = f.[Code fournisseur]
            WHERE f.[Acheteur] IS NOT NULL AND f.[Acheteur] <> ''
              AND (@societe IS NULL OR l.[societe] = @societe)
              AND l.[Type Document] IN ('Facture', 'Facture comptabilisée')
              AND l.[Valorise CA] = 'Oui'
              AND l.[Date BL] BETWEEN @dateDebut AND @dateFin
            GROUP BY f.[Acheteur], l.[societe]
            ORDER BY [Achats HT] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- Evolution Prix Achats ---
    {
        "code": "DS_EVOLUTION_PRIX_ACHATS",
        "nom": "Evolution Prix Achats",
        "category": "Achats",
        "description": "Evolution des prix d'achat par article",
        "query_template": """
            SELECT
                l.[Code article] AS [Code Article],
                a.[Désignation Article] AS [Designation],
                FORMAT(l.[Date BL], 'yyyy-MM') AS [Mois],
                l.[societe] AS [Société],
                AVG(l.[Prix unitaire]) AS [Prix Moyen],
                MIN(l.[Prix unitaire]) AS [Prix Min],
                MAX(l.[Prix unitaire]) AS [Prix Max],
                SUM(l.[Quantité]) AS [Qte Achetee],
                COUNT(DISTINCT l.[Code fournisseur]) AS [Nb Fournisseurs]
            FROM [Lignes_des_achats] l
            INNER JOIN [Articles] a ON l.[DB_Id] = a.[DB_Id] AND l.[Code article] = a.[Code Article]
            WHERE l.[Type Document] IN ('Facture', 'Facture comptabilisée')
              AND l.[Valorise CA] = 'Oui'
              AND (@societe IS NULL OR l.[societe] = @societe)
              AND l.[Date BL] BETWEEN @dateDebut AND @dateFin
            GROUP BY l.[Code article], a.[Désignation Article], FORMAT(l.[Date BL], 'yyyy-MM'), l.[societe]
            ORDER BY l.[Code article], [Mois]
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- Achats par Catalogue ---
    {
        "code": "DS_ACHATS_PAR_CATALOGUE",
        "nom": "Achats par Catalogue",
        "category": "Achats",
        "description": "Achats agreges par catalogue produit",
        "query_template": """
            SELECT
                a.[Catalogue 1] AS [Catalogue],
                l.[societe] AS [Société],
                SUM(l.[Montant HT Net]) AS [Achats HT],
                SUM(l.[Quantité]) AS [Qte Achetee],
                COUNT(DISTINCT l.[Code article]) AS [Nb Articles],
                COUNT(DISTINCT l.[Code fournisseur]) AS [Nb Fournisseurs]
            FROM [Lignes_des_achats] l
            INNER JOIN [Articles] a ON l.[DB_Id] = a.[DB_Id] AND l.[Code article] = a.[Code Article]
            WHERE a.[Catalogue 1] IS NOT NULL AND a.[Catalogue 1] <> ''
              AND (@societe IS NULL OR l.[societe] = @societe)
              AND l.[Type Document] IN ('Facture', 'Facture comptabilisée')
              AND l.[Valorise CA] = 'Oui'
              AND l.[Date BL] BETWEEN @dateDebut AND @dateFin
            GROUP BY a.[Catalogue 1], l.[societe]
            ORDER BY [Achats HT] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- Comparaison Fournisseurs par Article ---
    {
        "code": "DS_COMPARAISON_FOURNISSEURS",
        "nom": "Comparaison Fournisseurs",
        "category": "Achats",
        "description": "Comparaison des prix par fournisseur pour chaque article",
        "query_template": """
            SELECT
                l.[Code article] AS [Code Article],
                a.[Désignation Article] AS [Designation],
                l.[Code fournisseur] AS [Code Fournisseur],
                l.[Intitulé fournisseur] AS [Fournisseur],
                l.[societe] AS [Société],
                AVG(l.[Prix unitaire]) AS [Prix Moyen],
                MIN(l.[Prix unitaire]) AS [Prix Min],
                MAX(l.[Prix unitaire]) AS [Prix Max],
                SUM(l.[Quantité]) AS [Qte Achetee],
                COUNT(DISTINCT l.[N° Pièce]) AS [Nb Commandes],
                MAX(l.[Date]) AS [Dernier Achat]
            FROM [Lignes_des_achats] l
            INNER JOIN [Articles] a ON l.[DB_Id] = a.[DB_Id] AND l.[Code article] = a.[Code Article]
            WHERE l.[Type Document] IN ('Facture', 'Facture comptabilisée')
              AND l.[Valorise CA] = 'Oui'
              AND (@societe IS NULL OR l.[societe] = @societe)
              AND l.[Date BL] BETWEEN @dateDebut AND @dateFin
            GROUP BY l.[Code article], a.[Désignation Article], l.[Code fournisseur], l.[Intitulé fournisseur], l.[societe]
            ORDER BY l.[Code article], [Prix Moyen]
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # ==================== STOCKS / MOUVEMENTS ====================
    # Basé sur la table Mouvement_stock
    {
        "code": "DS_MVT_STOCK_GLOBAL",
        "nom": "Mouvements Stock Global",
        "category": "Stocks",
        "description": "Synthese globale des mouvements de stock",
        "query_template": """
            SELECT
                [societe] AS [Société],
                COUNT(*) AS [Nb Mouvements],
                SUM(CASE WHEN [Sens de mouvement] = 'Entrée' THEN [Quantité] ELSE 0 END) AS [Qte Entrees],
                SUM(CASE WHEN [Sens de mouvement] = 'Sortie' THEN [Quantité] ELSE 0 END) AS [Qte Sorties],
                SUM(CASE WHEN [Sens de mouvement] = 'Entrée' THEN [Montant Stock] ELSE 0 END) AS [Valeur Entrees],
                SUM(CASE WHEN [Sens de mouvement] = 'Sortie' THEN [Montant Stock] ELSE 0 END) AS [Valeur Sorties],
                SUM(CASE WHEN [Sens de mouvement] = 'Entrée' THEN [Quantité] ELSE -[Quantité] END) AS [Solde Qte],
                SUM(CASE WHEN [Sens de mouvement] = 'Entrée' THEN [Montant Stock] ELSE -[Montant Stock] END) AS [Solde Valeur]
            FROM [Mouvement_stock]
            WHERE [Date Mouvement] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
            GROUP BY [societe]
            ORDER BY [Nb Mouvements] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_MVT_PAR_DEPOT",
        "nom": "Mouvements par Depot",
        "category": "Stocks",
        "description": "Mouvements de stock par depot",
        "query_template": """
            SELECT
                [Code Dépôt] AS [Code Depot],
                [Dépôt] AS [Depot],
                [societe] AS [Société],
                COUNT(*) AS [Nb Mouvements],
                SUM(CASE WHEN [Sens de mouvement] = 'Entrée' THEN [Quantité] ELSE 0 END) AS [Qte Entrees],
                SUM(CASE WHEN [Sens de mouvement] = 'Sortie' THEN [Quantité] ELSE 0 END) AS [Qte Sorties],
                SUM(CASE WHEN [Sens de mouvement] = 'Entrée' THEN [Montant Stock] ELSE 0 END) AS [Valeur Entrees],
                SUM(CASE WHEN [Sens de mouvement] = 'Sortie' THEN [Montant Stock] ELSE 0 END) AS [Valeur Sorties],
                COUNT(DISTINCT [Code article]) AS [Nb Articles]
            FROM [Mouvement_stock]
            WHERE [Date Mouvement] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
            GROUP BY [Code Dépôt], [Dépôt], [societe]
            ORDER BY [Nb Mouvements] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_MVT_PAR_FAMILLE",
        "nom": "Mouvements par Famille",
        "category": "Stocks",
        "description": "Mouvements de stock par famille d'articles",
        "query_template": """
            SELECT
                [Code famille] AS [Code Famille],
                [Intitulé famille] AS [Famille],
                [societe] AS [Société],
                COUNT(*) AS [Nb Mouvements],
                SUM(CASE WHEN [Sens de mouvement] = 'Entrée' THEN [Quantité] ELSE 0 END) AS [Qte Entrees],
                SUM(CASE WHEN [Sens de mouvement] = 'Sortie' THEN [Quantité] ELSE 0 END) AS [Qte Sorties],
                SUM(CASE WHEN [Sens de mouvement] = 'Entrée' THEN [Montant Stock] ELSE 0 END) AS [Valeur Entrees],
                SUM(CASE WHEN [Sens de mouvement] = 'Sortie' THEN [Montant Stock] ELSE 0 END) AS [Valeur Sorties],
                COUNT(DISTINCT [Code article]) AS [Nb Articles]
            FROM [Mouvement_stock]
            WHERE [Date Mouvement] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
            GROUP BY [Code famille], [Intitulé famille], [societe]
            ORDER BY [Valeur Sorties] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_MVT_PAR_ARTICLE",
        "nom": "Mouvements par Article",
        "category": "Stocks",
        "description": "Detail des mouvements par article",
        "query_template": """
            SELECT
                [Code article] AS [Code Article],
                [Référence] AS [Reference],
                [Désignation] AS [Designation],
                [Intitulé famille] AS [Famille],
                [societe] AS [Société],
                SUM(CASE WHEN [Sens de mouvement] = 'Entrée' THEN [Quantité] ELSE 0 END) AS [Qte Entrees],
                SUM(CASE WHEN [Sens de mouvement] = 'Sortie' THEN [Quantité] ELSE 0 END) AS [Qte Sorties],
                SUM(CASE WHEN [Sens de mouvement] = 'Entrée' THEN [Quantité] ELSE -[Quantité] END) AS [Solde Qte],
                AVG([CMUP]) AS [CMUP Moyen],
                SUM([Montant Stock]) AS [Valeur Mvt Total]
            FROM [Mouvement_stock]
            WHERE [Date Mouvement] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
            GROUP BY [Code article], [Référence], [Désignation], [Intitulé famille], [societe]
            ORDER BY [Valeur Mvt Total] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_MVT_PAR_DOMAINE",
        "nom": "Mouvements par Domaine",
        "category": "Stocks",
        "description": "Mouvements par domaine (Vente, Achat, Stock, Document interne)",
        "query_template": """
            SELECT
                [Domaine mouvement] AS [Domaine],
                [societe] AS [Société],
                COUNT(*) AS [Nb Mouvements],
                SUM(CASE WHEN [Sens de mouvement] = 'Entrée' THEN [Quantité] ELSE 0 END) AS [Qte Entrees],
                SUM(CASE WHEN [Sens de mouvement] = 'Sortie' THEN [Quantité] ELSE 0 END) AS [Qte Sorties],
                SUM(CASE WHEN [Sens de mouvement] = 'Entrée' THEN [Montant Stock] ELSE 0 END) AS [Valeur Entrees],
                SUM(CASE WHEN [Sens de mouvement] = 'Sortie' THEN [Montant Stock] ELSE 0 END) AS [Valeur Sorties],
                COUNT(DISTINCT [Code article]) AS [Nb Articles]
            FROM [Mouvement_stock]
            WHERE [Date Mouvement] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
            GROUP BY [Domaine mouvement], [societe]
            ORDER BY [Nb Mouvements] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_MVT_PAR_TYPE",
        "nom": "Mouvements par Type Document",
        "category": "Stocks",
        "description": "Mouvements par type de document (Facture, BL, BC, etc.)",
        "query_template": """
            SELECT
                [Type Mouvement] AS [Type Document],
                [Domaine mouvement] AS [Domaine],
                [societe] AS [Société],
                COUNT(*) AS [Nb Mouvements],
                SUM([Quantité]) AS [Qte Totale],
                SUM([Montant Stock]) AS [Valeur Totale],
                COUNT(DISTINCT [N° Pièce]) AS [Nb Pieces],
                COUNT(DISTINCT [Code article]) AS [Nb Articles]
            FROM [Mouvement_stock]
            WHERE [Date Mouvement] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
            GROUP BY [Type Mouvement], [Domaine mouvement], [societe]
            ORDER BY [Nb Mouvements] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_MVT_ENTREES",
        "nom": "Entrees Stock",
        "category": "Stocks",
        "description": "Detail des entrees de stock",
        "query_template": """
            SELECT
                [Date Mouvement] AS [Date],
                [Type Mouvement] AS [Type],
                [Domaine mouvement] AS [Domaine],
                [N° Pièce] AS [N Piece],
                [Code article] AS [Code Article],
                [Désignation] AS [Designation],
                [Code Dépôt] AS [Code Depot],
                [Dépôt] AS [Depot],
                [Quantité] AS [Quantite],
                [CMUP],
                [Prix unitaire] AS [Prix Unitaire],
                [Montant Stock] AS [Valeur],
                [N° Série / Lot] AS [Lot Serie],
                [societe] AS [Société]
            FROM [Mouvement_stock]
            WHERE [Sens de mouvement] = 'Entrée'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date Mouvement] BETWEEN @dateDebut AND @dateFin
            ORDER BY [Date Mouvement] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_MVT_SORTIES",
        "nom": "Sorties Stock",
        "category": "Stocks",
        "description": "Detail des sorties de stock",
        "query_template": """
            SELECT
                [Date Mouvement] AS [Date],
                [Type Mouvement] AS [Type],
                [Domaine mouvement] AS [Domaine],
                [N° Pièce] AS [N Piece],
                [Code article] AS [Code Article],
                [Désignation] AS [Designation],
                [Code Dépôt] AS [Code Depot],
                [Dépôt] AS [Depot],
                [Quantité] AS [Quantite],
                [CMUP],
                [Prix unitaire] AS [Prix Unitaire],
                [Montant Stock] AS [Valeur],
                [N° Série / Lot] AS [Lot Serie],
                [societe] AS [Société]
            FROM [Mouvement_stock]
            WHERE [Sens de mouvement] = 'Sortie'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date Mouvement] BETWEEN @dateDebut AND @dateFin
            ORDER BY [Date Mouvement] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_STOCK_ACTUEL",
        "nom": "Stock Actuel par Article",
        "category": "Stocks",
        "description": "Stock actuel calcule depuis les mouvements cumules",
        "query_template": """
            SELECT
                [Code article] AS [Code Article],
                [Référence] AS [Reference],
                [Désignation] AS [Designation],
                [Intitulé famille] AS [Famille],
                [Code Dépôt] AS [Code Depot],
                [Dépôt] AS [Depot],
                [societe] AS [Société],
                SUM(CASE WHEN [Sens de mouvement] = 'Entrée' THEN [Quantité] ELSE -[Quantité] END) AS [Stock Actuel],
                MAX([CMUP]) AS [Dernier CMUP],
                SUM(CASE WHEN [Sens de mouvement] = 'Entrée' THEN [Quantité] ELSE -[Quantité] END) * MAX([CMUP]) AS [Valeur Stock],
                MAX([Date Mouvement]) AS [Dernier Mouvement]
            FROM [Mouvement_stock]
            WHERE (@societe IS NULL OR [societe] = @societe)
            GROUP BY [Code article], [Référence], [Désignation], [Intitulé famille],
                     [Code Dépôt], [Dépôt], [societe]
            HAVING SUM(CASE WHEN [Sens de mouvement] = 'Entrée' THEN [Quantité] ELSE -[Quantité] END) <> 0
            ORDER BY [Valeur Stock] DESC
        """,
        "parameters": '[{"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_STOCK_PAR_DEPOT",
        "nom": "Stock Actuel par Depot",
        "category": "Stocks",
        "description": "Stock actuel agrege par depot",
        "query_template": """
            SELECT
                [Code Dépôt] AS [Code Depot],
                [Dépôt] AS [Depot],
                [societe] AS [Société],
                COUNT(DISTINCT [Code article]) AS [Nb Articles],
                SUM(CASE WHEN [Sens de mouvement] = 'Entrée' THEN [Quantité] ELSE -[Quantité] END) AS [Stock Total Qte],
                SUM((CASE WHEN [Sens de mouvement] = 'Entrée' THEN [Quantité] ELSE -[Quantité] END) * [CMUP]) AS [Valeur Stock]
            FROM [Mouvement_stock]
            WHERE (@societe IS NULL OR [societe] = @societe)
            GROUP BY [Code Dépôt], [Dépôt], [societe]
            ORDER BY [Valeur Stock] DESC
        """,
        "parameters": '[{"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_MVT_PAR_MOIS",
        "nom": "Mouvements par Mois",
        "category": "Stocks",
        "description": "Evolution mensuelle des mouvements de stock",
        "query_template": """
            SELECT
                FORMAT([Date Mouvement], 'yyyy-MM') AS [Mois],
                [societe] AS [Société],
                COUNT(*) AS [Nb Mouvements],
                SUM(CASE WHEN [Sens de mouvement] = 'Entrée' THEN [Quantité] ELSE 0 END) AS [Qte Entrees],
                SUM(CASE WHEN [Sens de mouvement] = 'Sortie' THEN [Quantité] ELSE 0 END) AS [Qte Sorties],
                SUM(CASE WHEN [Sens de mouvement] = 'Entrée' THEN [Montant Stock] ELSE 0 END) AS [Valeur Entrees],
                SUM(CASE WHEN [Sens de mouvement] = 'Sortie' THEN [Montant Stock] ELSE 0 END) AS [Valeur Sorties],
                COUNT(DISTINCT [Code article]) AS [Nb Articles]
            FROM [Mouvement_stock]
            WHERE [Date Mouvement] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
            GROUP BY FORMAT([Date Mouvement], 'yyyy-MM'), [societe]
            ORDER BY [Mois] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_MVT_VENTES",
        "nom": "Mouvements Ventes",
        "category": "Stocks",
        "description": "Mouvements de stock lies aux ventes (BL, Factures)",
        "query_template": """
            SELECT
                [Date Mouvement] AS [Date],
                [Type Mouvement] AS [Type],
                [N° Pièce] AS [N Piece],
                [Code article] AS [Code Article],
                [Désignation] AS [Designation],
                [Code Dépôt] AS [Code Depot],
                [Quantité] AS [Quantite],
                [Prix unitaire] AS [Prix Vente],
                [CMUP] AS [Prix Revient],
                [Montant Stock] AS [Valeur Stock],
                ([Prix unitaire] - [CMUP]) * [Quantité] AS [Marge],
                [societe] AS [Société]
            FROM [Mouvement_stock]
            WHERE [Domaine mouvement] = 'Vente'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Type Mouvement] IN ('Facture', 'Facture comptabilisée', 'Bon de livraison')
              AND [Date Mouvement] BETWEEN @dateDebut AND @dateFin
            ORDER BY [Date Mouvement] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_MVT_ACHATS",
        "nom": "Mouvements Achats",
        "category": "Stocks",
        "description": "Mouvements de stock lies aux achats (BR, Factures)",
        "query_template": """
            SELECT
                [Date Mouvement] AS [Date],
                [Type Mouvement] AS [Type],
                [N° Pièce] AS [N Piece],
                [Code article] AS [Code Article],
                [Désignation] AS [Designation],
                [Code Dépôt] AS [Code Depot],
                [Quantité] AS [Quantite],
                [Prix unitaire] AS [Prix Achat],
                [CMUP],
                [Montant Stock] AS [Valeur Stock],
                [societe] AS [Société]
            FROM [Mouvement_stock]
            WHERE [Domaine mouvement] = 'Achat'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date Mouvement] BETWEEN @dateDebut AND @dateFin
            ORDER BY [Date Mouvement] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_MVT_INTERNES",
        "nom": "Mouvements Internes Stock",
        "category": "Stocks",
        "description": "Mouvements internes (virements, inventaires, regularisations)",
        "query_template": """
            SELECT
                [Date Mouvement] AS [Date],
                [Type Mouvement] AS [Type],
                [N° Pièce] AS [N Piece],
                [Code article] AS [Code Article],
                [Désignation] AS [Designation],
                [Code Dépôt] AS [Code Depot],
                [Dépôt] AS [Depot],
                [Sens de mouvement] AS [Sens],
                [Quantité] AS [Quantite],
                [CMUP],
                [Montant Stock] AS [Valeur],
                [societe] AS [Société]
            FROM [Mouvement_stock]
            WHERE [Domaine mouvement] IN ('Stock', 'Document interne')
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date Mouvement] BETWEEN @dateDebut AND @dateFin
            ORDER BY [Date Mouvement] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_STOCK_ROTATION",
        "nom": "Rotation des Stocks",
        "category": "Stocks",
        "description": "Analyse de la rotation des stocks basee sur les mouvements",
        "query_template": """
            WITH StockActuel AS (
                SELECT
                    [Code article],
                    [Référence],
                    [Désignation],
                    [Intitulé famille],
                    [societe],
                    SUM(CASE WHEN [Sens de mouvement] = 'Entrée' THEN [Quantité] ELSE -[Quantité] END) AS stock_qte,
                    MAX([CMUP]) AS cmup
                FROM [Mouvement_stock]
            WHERE (@societe IS NULL OR [societe] = @societe)
                GROUP BY [Code article], [Référence], [Désignation], [Intitulé famille], [societe]
            ),
            Sorties12M AS (
                SELECT
                    [Code article],
                    [societe],
                    SUM([Quantité]) AS qte_sortie_12m
                FROM [Mouvement_stock]
                WHERE [Sens de mouvement] = 'Sortie'
              AND (@societe IS NULL OR [societe] = @societe)
                  AND [Date Mouvement] >= DATEADD(MONTH, -12, GETDATE())
                GROUP BY [Code article], [societe]
            )
            SELECT
                s.[Code article] AS [Code Article],
                s.[Référence] AS [Reference],
                s.[Désignation] AS [Designation],
                s.[Intitulé famille] AS [Famille],
                s.[societe] AS [Société],
                s.stock_qte AS [Stock Actuel],
                s.cmup AS [CMUP],
                s.stock_qte * s.cmup AS [Valeur Stock],
                ISNULL(v.qte_sortie_12m, 0) AS [Sorties 12M],
                CASE
                    WHEN ISNULL(v.qte_sortie_12m, 0) > 0
                    THEN ROUND(s.stock_qte * 365.0 / v.qte_sortie_12m, 0)
                    ELSE 9999
                END AS [Couverture Jours],
                CASE
                    WHEN ISNULL(v.qte_sortie_12m, 0) > 0
                    THEN ROUND(v.qte_sortie_12m / NULLIF(s.stock_qte, 0), 2)
                    ELSE 0
                END AS [Taux Rotation]
            FROM StockActuel s
            LEFT JOIN Sorties12M v ON s.[Code article] = v.[Code article] AND s.[societe] = v.[societe]
            WHERE s.stock_qte > 0
              AND (@societe IS NULL OR s.[societe] = @societe)
            ORDER BY [Couverture Jours] DESC
        """,
        "parameters": '[{"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_STOCK_DORMANT",
        "nom": "Stock Dormant",
        "category": "Stocks",
        "description": "Articles sans mouvement depuis plus de 180 jours",
        "query_template": """
            WITH DernierMvt AS (
                SELECT
                    [Code article],
                    [Référence],
                    [Désignation],
                    [Intitulé famille],
                    [societe],
                    MAX([Date Mouvement]) AS dernier_mvt,
                    SUM(CASE WHEN [Sens de mouvement] = 'Entrée' THEN [Quantité] ELSE -[Quantité] END) AS stock_qte,
                    MAX([CMUP]) AS cmup
                FROM [Mouvement_stock]
            WHERE (@societe IS NULL OR [societe] = @societe)
                GROUP BY [Code article], [Référence], [Désignation], [Intitulé famille], [societe]
            )
            SELECT
                [Code article] AS [Code Article],
                [Référence] AS [Reference],
                [Désignation] AS [Designation],
                [Intitulé famille] AS [Famille],
                [societe] AS [Société],
                stock_qte AS [Stock Qte],
                cmup AS [CMUP],
                stock_qte * cmup AS [Valeur Stock],
                dernier_mvt AS [Dernier Mouvement],
                DATEDIFF(DAY, dernier_mvt, GETDATE()) AS [Jours Sans Mvt]
            FROM DernierMvt
            WHERE stock_qte > 0
              AND (@societe IS NULL OR [societe] = @societe)
              AND DATEDIFF(DAY, dernier_mvt, GETDATE()) > 180
            ORDER BY [Valeur Stock] DESC
        """,
        "parameters": '[{"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_MVT_DETAIL",
        "nom": "Detail Complet Mouvements",
        "category": "Stocks",
        "description": "Liste complete des mouvements avec tous les details",
        "query_template": """
            SELECT
                [Date Mouvement] AS [Date],
                [Type Mouvement] AS [Type],
                [Domaine mouvement] AS [Domaine],
                [Sens de mouvement] AS [Sens],
                [N° Pièce] AS [N Piece],
                [Code article] AS [Code Article],
                [Référence] AS [Reference],
                [Désignation] AS [Designation],
                [Intitulé famille] AS [Famille],
                [Code Dépôt] AS [Code Depot],
                [Dépôt] AS [Depot],
                [Quantité] AS [Quantite],
                [CMUP],
                [Prix unitaire] AS [Prix Unitaire],
                [CMUP] AS [Prix Revient],
                [Montant Stock] AS [Valeur Stock],
                [N° Série / Lot] AS [Lot Serie],
                [Gamme 1],
                [Gamme 2],
                [Catalogue 1],
                [Catalogue 2],
                [societe] AS [Société]
            FROM [Mouvement_stock]
            WHERE [Date Mouvement] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
            ORDER BY [Date Mouvement] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_MVT_PAR_LOT",
        "nom": "Mouvements par Lot/Serie",
        "category": "Stocks",
        "description": "Tracabilite des mouvements par numero de lot ou serie",
        "query_template": """
            SELECT
                [N° Série / Lot] AS [Lot Serie],
                [Code article] AS [Code Article],
                [Désignation] AS [Designation],
                [societe] AS [Société],
                COUNT(*) AS [Nb Mouvements],
                SUM(CASE WHEN [Sens de mouvement] = 'Entrée' THEN [Quantité] ELSE 0 END) AS [Qte Entrees],
                SUM(CASE WHEN [Sens de mouvement] = 'Sortie' THEN [Quantité] ELSE 0 END) AS [Qte Sorties],
                SUM(CASE WHEN [Sens de mouvement] = 'Entrée' THEN [Quantité] ELSE -[Quantité] END) AS [Solde Qte],
                MIN([Date Mouvement]) AS [Premier Mvt],
                MAX([Date Mouvement]) AS [Dernier Mvt]
            FROM [Mouvement_stock]
            WHERE [N° Série / Lot] IS NOT NULL AND [N° Série / Lot] <> ''
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date Mouvement] BETWEEN @dateDebut AND @dateFin
            GROUP BY [N° Série / Lot], [Code article], [Désignation], [societe]
            ORDER BY [Dernier Mvt] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_TOP_ARTICLES_MVT",
        "nom": "Top Articles Mouvementes",
        "category": "Stocks",
        "description": "Articles avec le plus de mouvements",
        "query_template": """
            SELECT TOP 50
                [Code article] AS [Code Article],
                [Référence] AS [Reference],
                [Désignation] AS [Designation],
                [Intitulé famille] AS [Famille],
                [societe] AS [Société],
                COUNT(*) AS [Nb Mouvements],
                SUM(CASE WHEN [Sens de mouvement] = 'Sortie' THEN [Quantité] ELSE 0 END) AS [Qte Sorties],
                SUM(CASE WHEN [Sens de mouvement] = 'Sortie' THEN [Montant Stock] ELSE 0 END) AS [Valeur Sorties],
                SUM(CASE WHEN [Sens de mouvement] = 'Entrée' THEN [Quantité] ELSE 0 END) AS [Qte Entrees],
                COUNT(DISTINCT [N° Pièce]) AS [Nb Pieces]
            FROM [Mouvement_stock]
            WHERE [Date Mouvement] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
            GROUP BY [Code article], [Référence], [Désignation], [Intitulé famille], [societe]
            ORDER BY [Nb Mouvements] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_MVT_CATALOGUE",
        "nom": "Mouvements par Catalogue",
        "category": "Stocks",
        "description": "Mouvements de stock par catalogue produit",
        "query_template": """
            SELECT
                [Catalogue 1] AS [Catalogue],
                [societe] AS [Société],
                COUNT(*) AS [Nb Mouvements],
                SUM(CASE WHEN [Sens de mouvement] = 'Entrée' THEN [Quantité] ELSE 0 END) AS [Qte Entrees],
                SUM(CASE WHEN [Sens de mouvement] = 'Sortie' THEN [Quantité] ELSE 0 END) AS [Qte Sorties],
                SUM(CASE WHEN [Sens de mouvement] = 'Sortie' THEN [Montant Stock] ELSE 0 END) AS [Valeur Sorties],
                COUNT(DISTINCT [Code article]) AS [Nb Articles]
            FROM [Mouvement_stock]
            WHERE [Catalogue 1] IS NOT NULL AND [Catalogue 1] <> ''
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date Mouvement] BETWEEN @dateDebut AND @dateFin
            GROUP BY [Catalogue 1], [societe]
            ORDER BY [Valeur Sorties] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # ==================== COMPTABILITE ====================
    # Basé sur les tables Ecritures_Comptables et Ecritures_Analytiques

    # --- ECRITURES COMPTABLES GENERALES ---
    {
        "code": "DS_ECRITURES_GLOBAL",
        "nom": "Ecritures Comptables Global",
        "category": "Comptabilite",
        "description": "Synthese globale des ecritures comptables par periode",
        "query_template": """
            SELECT
                [societe] AS [Société],
                [Exercice],
                COUNT(*) AS [Nb Ecritures],
                SUM([Débit]) AS [Total Debit],
                SUM([Crédit]) AS [Total Credit],
                SUM([Débit]) - SUM([Crédit]) AS [Solde],
                COUNT(DISTINCT [N° Compte Général]) AS [Nb Comptes],
                COUNT(DISTINCT [Code Journal]) AS [Nb Journaux]
            FROM [Ecritures_Comptables]
            WHERE [Date d'écriture] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
            GROUP BY [societe], [Exercice]
            ORDER BY [Exercice] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_ECRITURES_PAR_JOURNAL",
        "nom": "Ecritures par Journal",
        "category": "Comptabilite",
        "description": "Ecritures comptables agregees par journal",
        "query_template": """
            SELECT
                [Code Journal],
                [Libellé Journal] AS [Journal],
                [Type Code Journal] AS [Type Journal],
                [societe] AS [Société],
                COUNT(*) AS [Nb Ecritures],
                SUM([Débit]) AS [Total Debit],
                SUM([Crédit]) AS [Total Credit],
                COUNT(DISTINCT [N° Pièce]) AS [Nb Pieces]
            FROM [Ecritures_Comptables]
            WHERE [Date d'écriture] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
            GROUP BY [Code Journal], [Libellé Journal], [Type Code Journal], [societe]
            ORDER BY [Total Debit] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_ECRITURES_PAR_COMPTE",
        "nom": "Ecritures par Compte",
        "category": "Comptabilite",
        "description": "Mouvements par compte general",
        "query_template": """
            SELECT
                [N° Compte Général] AS [Compte],
                [Intitulé compte général] AS [Intitule],
                [Masse],
                [Rubrique],
                [Poste],
                [societe] AS [Société],
                SUM([Débit]) AS [Total Debit],
                SUM([Crédit]) AS [Total Credit],
                SUM([Débit]) - SUM([Crédit]) AS [Solde],
                COUNT(*) AS [Nb Ecritures]
            FROM [Ecritures_Comptables]
            WHERE [Date d'écriture] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
            GROUP BY [N° Compte Général], [Intitulé compte général], [Masse], [Rubrique], [Poste], [societe]
            ORDER BY [Compte]
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_ECRITURES_PAR_TIERS",
        "nom": "Ecritures par Tiers",
        "category": "Comptabilite",
        "description": "Mouvements par compte tiers (clients/fournisseurs)",
        "query_template": """
            SELECT
                [Compte Tiers] AS [Code Tiers],
                [Intitulé tiers] AS [Tiers],
                [Type tiers] AS [Type],
                [societe] AS [Société],
                SUM([Débit]) AS [Total Debit],
                SUM([Crédit]) AS [Total Credit],
                SUM([Débit]) - SUM([Crédit]) AS [Solde],
                COUNT(*) AS [Nb Ecritures],
                COUNT(DISTINCT [N° Pièce]) AS [Nb Pieces]
            FROM [Ecritures_Comptables]
            WHERE [Compte Tiers] IS NOT NULL AND [Compte Tiers] <> ''
              AND [Date d'écriture] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
            GROUP BY [Compte Tiers], [Intitulé tiers], [Type tiers], [societe]
            ORDER BY ABS([Solde]) DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_ECRITURES_PAR_MOIS",
        "nom": "Ecritures par Mois",
        "category": "Comptabilite",
        "description": "Evolution mensuelle des ecritures comptables",
        "query_template": """
            SELECT
                [Année] AS [Annee],
                [Mois],
                [societe] AS [Société],
                COUNT(*) AS [Nb Ecritures],
                SUM([Débit]) AS [Total Debit],
                SUM([Crédit]) AS [Total Credit],
                COUNT(DISTINCT [N° Compte Général]) AS [Nb Comptes],
                COUNT(DISTINCT [N° Pièce]) AS [Nb Pieces]
            FROM [Ecritures_Comptables]
            WHERE [Date d'écriture] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
            GROUP BY [Année], [Mois], [societe]
            ORDER BY [Annee] DESC, [Mois] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_ECRITURES_DETAIL",
        "nom": "Detail Ecritures Comptables",
        "category": "Comptabilite",
        "description": "Liste detaillee des ecritures comptables",
        "query_template": """
            SELECT
                [Date d'écriture] AS [Date],
                [Code Journal],
                [Libellé Journal] AS [Journal],
                [N° Pièce] AS [Piece],
                [N° Compte Général] AS [Compte],
                [Intitulé compte général] AS [Intitule Compte],
                [Compte Tiers],
                [Intitulé tiers] AS [Tiers],
                [Libellé] AS [Libelle],
                [Débit],
                [Crédit],
                [Sens],
                [Référence],
                [Date d'échéance] AS [Echeance],
                [Mode de règlement] AS [Mode de Règlement],
                [Lettrage],
                [Lettre],
                [societe] AS [Société]
            FROM [Ecritures_Comptables]
            WHERE [Date d'écriture] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
            ORDER BY [Date d'écriture] DESC, [N° Pièce]
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_GRAND_LIVRE",
        "nom": "Grand Livre",
        "category": "Comptabilite",
        "description": "Grand livre comptable par compte",
        "query_template": """
            SELECT
                [N° Compte Général] AS [Compte],
                [Intitulé compte général] AS [Intitule],
                [Date d'écriture] AS [Date],
                [Code Journal],
                [N° Pièce] AS [Piece],
                [Libellé] AS [Libelle],
                [Débit],
                [Crédit],
                [Compte Tiers],
                [Intitulé tiers] AS [Tiers],
                [Lettrage],
                [societe] AS [Société]
            FROM [Ecritures_Comptables]
            WHERE [Date d'écriture] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
            ORDER BY [N° Compte Général], [Date d'écriture]
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_BALANCE_GENERALE",
        "nom": "Balance Generale",
        "category": "Comptabilite",
        "description": "Balance generale des comptes avec soldes",
        "query_template": """
            SELECT
                [N° Compte Général] AS [Compte],
                [Intitulé compte général] AS [Intitule],
                [Masse],
                [Rubrique],
                [Poste],
                [Nature Compte] AS [Nature],
                [societe] AS [Société],
                SUM(CASE WHEN [Report à Nouveau] = 'Oui' THEN [Débit] - [Crédit] ELSE 0 END) AS [A Nouveau],
                SUM(CASE WHEN [Report à Nouveau] <> 'Oui' THEN [Débit] ELSE 0 END) AS [Mvt Debit],
                SUM(CASE WHEN [Report à Nouveau] <> 'Oui' THEN [Crédit] ELSE 0 END) AS [Mvt Credit],
                SUM([Débit]) AS [Total Debit],
                SUM([Crédit]) AS [Total Credit],
                SUM([Débit]) - SUM([Crédit]) AS [Solde],
                CASE WHEN SUM([Débit]) > SUM([Crédit]) THEN SUM([Débit]) - SUM([Crédit]) ELSE 0 END AS [Solde Debiteur],
                CASE WHEN SUM([Crédit]) > SUM([Débit]) THEN SUM([Crédit]) - SUM([Débit]) ELSE 0 END AS [Solde Crediteur]
            FROM [Ecritures_Comptables]
            WHERE [Exercice] = YEAR(@dateFin)
              AND (@societe IS NULL OR [societe] = @societe)
            GROUP BY [N° Compte Général], [Intitulé compte général], [Masse], [Rubrique], [Poste], [Nature Compte], [societe]
            HAVING SUM([Débit]) <> 0 OR SUM([Crédit]) <> 0
            ORDER BY [Compte]
        """,
        "parameters": '[{"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- BILAN : ACTIF ---
    {
        "code": "DS_BILAN_ACTIF",
        "nom": "Bilan Actif",
        "category": "Comptabilite",
        "description": "Actif du bilan - Comptes classes 2, 3, 4 (debiteurs), 5",
        "query_template": """
            SELECT
                [Masse],
                [Rubrique],
                [Poste],
                [societe] AS [Société],
                SUM([Débit]) - SUM([Crédit]) AS [Montant],
                COUNT(DISTINCT [N° Compte Général]) AS [Nb Comptes]
            FROM [Ecritures_Comptables]
            WHERE [Exercice] = YEAR(@dateFin)
              AND (@societe IS NULL OR [societe] = @societe)
              AND (
                  [N° Compte Général] LIKE '2%'  -- Immobilisations
                  OR [N° Compte Général] LIKE '3%'  -- Stocks
                  OR ([N° Compte Général] LIKE '4%' AND [Nature Compte] = 'Débiteur')  -- Créances
                  OR [N° Compte Général] LIKE '5%'  -- Trésorerie
              )
            GROUP BY [Masse], [Rubrique], [Poste], [societe]
            HAVING SUM([Débit]) - SUM([Crédit]) <> 0
            ORDER BY [Masse], [Rubrique], [Poste]
        """,
        "parameters": '[{"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_ACTIF_IMMOBILISE",
        "nom": "Actif Immobilise",
        "category": "Comptabilite",
        "description": "Detail de l'actif immobilise (classe 2)",
        "query_template": """
            SELECT
                LEFT([N° Compte Général], 2) AS [Classe],
                [Rubrique],
                [Poste],
                [societe] AS [Société],
                SUM(CASE WHEN [N° Compte Général] NOT LIKE '28%' AND [N° Compte Général] NOT LIKE '29%'
                    THEN [Débit] - [Crédit] ELSE 0 END) AS [Valeur Brute],
                SUM(CASE WHEN [N° Compte Général] LIKE '28%' OR [N° Compte Général] LIKE '29%'
                    THEN [Crédit] - [Débit] ELSE 0 END) AS [Amortissements],
                SUM([Débit]) - SUM([Crédit]) AS [Valeur Nette]
            FROM [Ecritures_Comptables]
            WHERE [Exercice] = YEAR(@dateFin)
              AND (@societe IS NULL OR [societe] = @societe)
              AND [N° Compte Général] LIKE '2%'
            GROUP BY LEFT([N° Compte Général], 2), [Rubrique], [Poste], [societe]
            ORDER BY [Classe]
        """,
        "parameters": '[{"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_ACTIF_CIRCULANT",
        "nom": "Actif Circulant",
        "category": "Comptabilite",
        "description": "Detail de l'actif circulant (classes 3, 4, 5)",
        "query_template": """
            SELECT
                CASE
                    WHEN [N° Compte Général] LIKE '3%' THEN 'Stocks'
                    WHEN [N° Compte Général] LIKE '4%' THEN 'Creances'
                    WHEN [N° Compte Général] LIKE '5%' THEN 'Tresorerie'
                END AS [Categorie],
                [Rubrique],
                [Poste],
                [societe] AS [Société],
                SUM([Débit]) - SUM([Crédit]) AS [Montant]
            FROM [Ecritures_Comptables]
            WHERE [Exercice] = YEAR(@dateFin)
              AND (@societe IS NULL OR [societe] = @societe)
              AND (
                  [N° Compte Général] LIKE '3%'
                  OR ([N° Compte Général] LIKE '4%' AND [Nature Compte] = 'Débiteur')
                  OR [N° Compte Général] LIKE '5%'
              )
            GROUP BY
                CASE
                    WHEN [N° Compte Général] LIKE '3%' THEN 'Stocks'
                    WHEN [N° Compte Général] LIKE '4%' THEN 'Creances'
                    WHEN [N° Compte Général] LIKE '5%' THEN 'Tresorerie'
                END,
                [Rubrique], [Poste], [societe]
            HAVING SUM([Débit]) - SUM([Crédit]) <> 0
            ORDER BY [Categorie], [Rubrique]
        """,
        "parameters": '[{"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- BILAN : PASSIF ---
    {
        "code": "DS_BILAN_PASSIF",
        "nom": "Bilan Passif",
        "category": "Comptabilite",
        "description": "Passif du bilan - Comptes classes 1, 4 (crediteurs)",
        "query_template": """
            SELECT
                [Masse],
                [Rubrique],
                [Poste],
                [societe] AS [Société],
                SUM([Crédit]) - SUM([Débit]) AS [Montant],
                COUNT(DISTINCT [N° Compte Général]) AS [Nb Comptes]
            FROM [Ecritures_Comptables]
            WHERE [Exercice] = YEAR(@dateFin)
              AND (@societe IS NULL OR [societe] = @societe)
              AND (
                  [N° Compte Général] LIKE '1%'  -- Capitaux propres
                  OR ([N° Compte Général] LIKE '4%' AND [Nature Compte] = 'Créditeur')  -- Dettes
              )
            GROUP BY [Masse], [Rubrique], [Poste], [societe]
            HAVING SUM([Crédit]) - SUM([Débit]) <> 0
            ORDER BY [Masse], [Rubrique], [Poste]
        """,
        "parameters": '[{"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_CAPITAUX_PROPRES",
        "nom": "Capitaux Propres",
        "category": "Comptabilite",
        "description": "Detail des capitaux propres (classe 1)",
        "query_template": """
            SELECT
                [Rubrique],
                [Poste],
                [N° Compte Général] AS [Compte],
                [Intitulé compte général] AS [Intitule],
                [societe] AS [Société],
                SUM([Crédit]) - SUM([Débit]) AS [Montant]
            FROM [Ecritures_Comptables]
            WHERE [Exercice] = YEAR(@dateFin)
              AND (@societe IS NULL OR [societe] = @societe)
              AND [N° Compte Général] LIKE '1%'
            GROUP BY [Rubrique], [Poste], [N° Compte Général], [Intitulé compte général], [societe]
            HAVING SUM([Crédit]) - SUM([Débit]) <> 0
            ORDER BY [N° Compte Général]
        """,
        "parameters": '[{"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_DETTES",
        "nom": "Dettes",
        "category": "Comptabilite",
        "description": "Detail des dettes (classe 4 crediteur)",
        "query_template": """
            SELECT
                [Rubrique],
                [Poste],
                [Compte Tiers],
                [Intitulé tiers] AS [Fournisseur],
                [societe] AS [Société],
                SUM([Crédit]) - SUM([Débit]) AS [Montant],
                COUNT(*) AS [Nb Ecritures]
            FROM [Ecritures_Comptables]
            WHERE [Exercice] = YEAR(@dateFin)
              AND (@societe IS NULL OR [societe] = @societe)
              AND [N° Compte Général] LIKE '4%'
              AND [Nature Compte] = 'Créditeur'
            GROUP BY [Rubrique], [Poste], [Compte Tiers], [Intitulé tiers], [societe]
            HAVING SUM([Crédit]) - SUM([Débit]) > 0
            ORDER BY [Montant] DESC
        """,
        "parameters": '[{"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- COMPTE DE PRODUITS ET CHARGES (CPC) ---
    {
        "code": "DS_CPC_GLOBAL",
        "nom": "CPC Global",
        "category": "Comptabilite",
        "description": "Compte de Produits et Charges - Vue synthetique",
        "query_template": """
            SELECT
                [societe] AS [Société],
                -- Produits d'exploitation (classe 7)
                SUM(CASE WHEN [N° Compte Général] LIKE '71%' THEN [Crédit] - [Débit] ELSE 0 END) AS [Ventes Marchandises],
                SUM(CASE WHEN [N° Compte Général] LIKE '72%' THEN [Crédit] - [Débit] ELSE 0 END) AS [Ventes Biens Services],
                SUM(CASE WHEN [N° Compte Général] LIKE '73%' THEN [Crédit] - [Débit] ELSE 0 END) AS [Variation Stocks Produits],
                SUM(CASE WHEN [N° Compte Général] LIKE '74%' THEN [Crédit] - [Débit] ELSE 0 END) AS [Immob Produites],
                SUM(CASE WHEN [N° Compte Général] LIKE '75%' THEN [Crédit] - [Débit] ELSE 0 END) AS [Subventions Exploitation],
                SUM(CASE WHEN [N° Compte Général] LIKE '7%' THEN [Crédit] - [Débit] ELSE 0 END) AS [Total Produits Exploitation],
                -- Charges d'exploitation (classe 6)
                SUM(CASE WHEN [N° Compte Général] LIKE '61%' THEN [Débit] - [Crédit] ELSE 0 END) AS [Achats Marchandises],
                SUM(CASE WHEN [N° Compte Général] LIKE '612%' THEN [Débit] - [Crédit] ELSE 0 END) AS [Achats Matieres],
                SUM(CASE WHEN [N° Compte Général] LIKE '613%' OR [N° Compte Général] LIKE '614%' THEN [Débit] - [Crédit] ELSE 0 END) AS [Autres Charges Externes],
                SUM(CASE WHEN [N° Compte Général] LIKE '617%' THEN [Débit] - [Crédit] ELSE 0 END) AS [Charges Personnel],
                SUM(CASE WHEN [N° Compte Général] LIKE '619%' THEN [Débit] - [Crédit] ELSE 0 END) AS [Dotations Amortissements],
                SUM(CASE WHEN [N° Compte Général] LIKE '6%' THEN [Débit] - [Crédit] ELSE 0 END) AS [Total Charges Exploitation],
                -- Resultat exploitation
                SUM(CASE WHEN [N° Compte Général] LIKE '7%' THEN [Crédit] - [Débit]
                         WHEN [N° Compte Général] LIKE '6%' THEN [Crédit] - [Débit] ELSE 0 END) AS [Resultat Exploitation],
                -- Produits financiers (classe 73)
                SUM(CASE WHEN [N° Compte Général] LIKE '73%' THEN [Crédit] - [Débit] ELSE 0 END) AS [Produits Financiers],
                -- Charges financières (classe 63)
                SUM(CASE WHEN [N° Compte Général] LIKE '63%' THEN [Débit] - [Crédit] ELSE 0 END) AS [Charges Financieres],
                -- Resultat net
                SUM([Crédit]) - SUM([Débit]) AS [Resultat Net]
            FROM [Ecritures_Comptables]
            WHERE [Exercice] = YEAR(@dateFin)
              AND (@societe IS NULL OR [societe] = @societe)
              AND ([N° Compte Général] LIKE '6%' OR [N° Compte Général] LIKE '7%')
            GROUP BY [societe]
        """,
        "parameters": '[{"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_CPC_PRODUITS",
        "nom": "CPC Produits",
        "category": "Comptabilite",
        "description": "Detail des produits (classe 7)",
        "query_template": """
            SELECT
                LEFT([N° Compte Général], 2) AS [Classe],
                [Rubrique],
                [Poste],
                [societe] AS [Société],
                SUM([Crédit]) - SUM([Débit]) AS [Montant],
                COUNT(DISTINCT [N° Compte Général]) AS [Nb Comptes]
            FROM [Ecritures_Comptables]
            WHERE [Exercice] = YEAR(@dateFin)
              AND (@societe IS NULL OR [societe] = @societe)
              AND [N° Compte Général] LIKE '7%'
            GROUP BY LEFT([N° Compte Général], 2), [Rubrique], [Poste], [societe]
            HAVING SUM([Crédit]) - SUM([Débit]) <> 0
            ORDER BY [Classe], [Rubrique]
        """,
        "parameters": '[{"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_CPC_CHARGES",
        "nom": "CPC Charges",
        "category": "Comptabilite",
        "description": "Detail des charges (classe 6)",
        "query_template": """
            SELECT
                LEFT([N° Compte Général], 2) AS [Classe],
                [Rubrique],
                [Poste],
                [societe] AS [Société],
                SUM([Débit]) - SUM([Crédit]) AS [Montant],
                COUNT(DISTINCT [N° Compte Général]) AS [Nb Comptes]
            FROM [Ecritures_Comptables]
            WHERE [Exercice] = YEAR(@dateFin)
              AND (@societe IS NULL OR [societe] = @societe)
              AND [N° Compte Général] LIKE '6%'
            GROUP BY LEFT([N° Compte Général], 2), [Rubrique], [Poste], [societe]
            HAVING SUM([Débit]) - SUM([Crédit]) <> 0
            ORDER BY [Classe], [Rubrique]
        """,
        "parameters": '[{"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_CPC_PAR_MOIS",
        "nom": "CPC par Mois",
        "category": "Comptabilite",
        "description": "Evolution mensuelle du CPC",
        "query_template": """
            SELECT
                [Année] AS [Annee],
                [Mois],
                [societe] AS [Société],
                SUM(CASE WHEN [N° Compte Général] LIKE '7%' THEN [Crédit] - [Débit] ELSE 0 END) AS [Produits],
                SUM(CASE WHEN [N° Compte Général] LIKE '6%' THEN [Débit] - [Crédit] ELSE 0 END) AS [Charges],
                SUM(CASE WHEN [N° Compte Général] LIKE '7%' THEN [Crédit] - [Débit]
                         WHEN [N° Compte Général] LIKE '6%' THEN [Crédit] - [Débit] ELSE 0 END) AS [Resultat]
            FROM [Ecritures_Comptables]
            WHERE [Date d'écriture] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
              AND ([N° Compte Général] LIKE '6%' OR [N° Compte Général] LIKE '7%')
            GROUP BY [Année], [Mois], [societe]
            ORDER BY [Annee], [Mois]
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- BILAN COMPLET ---
    {
        "code": "DS_BILAN_SYNTHETIQUE",
        "nom": "Bilan Synthetique",
        "category": "Comptabilite",
        "description": "Vue synthetique du bilan Actif/Passif",
        "query_template": """
            SELECT
                [societe] AS [Société],
                -- ACTIF
                SUM(CASE WHEN [N° Compte Général] LIKE '2%' AND [N° Compte Général] NOT LIKE '28%' AND [N° Compte Général] NOT LIKE '29%'
                    THEN [Débit] - [Crédit] ELSE 0 END) AS [Immob Brut],
                SUM(CASE WHEN [N° Compte Général] LIKE '28%' OR [N° Compte Général] LIKE '29%'
                    THEN [Crédit] - [Débit] ELSE 0 END) AS [Amortissements],
                SUM(CASE WHEN [N° Compte Général] LIKE '2%'
                    THEN [Débit] - [Crédit] ELSE 0 END) AS [Actif Immobilise Net],
                SUM(CASE WHEN [N° Compte Général] LIKE '3%'
                    THEN [Débit] - [Crédit] ELSE 0 END) AS [Stocks],
                SUM(CASE WHEN [N° Compte Général] LIKE '4%' AND [Nature Compte] = 'Débiteur'
                    THEN [Débit] - [Crédit] ELSE 0 END) AS [Creances],
                SUM(CASE WHEN [N° Compte Général] LIKE '5%'
                    THEN [Débit] - [Crédit] ELSE 0 END) AS [Tresorerie Actif],
                -- PASSIF
                SUM(CASE WHEN [N° Compte Général] LIKE '1%'
                    THEN [Crédit] - [Débit] ELSE 0 END) AS [Capitaux Propres],
                SUM(CASE WHEN [N° Compte Général] LIKE '4%' AND [Nature Compte] = 'Créditeur'
                    THEN [Crédit] - [Débit] ELSE 0 END) AS [Dettes],
                -- TOTAUX
                SUM(CASE WHEN [N° Compte Général] LIKE '2%' OR [N° Compte Général] LIKE '3%'
                             OR ([N° Compte Général] LIKE '4%' AND [Nature Compte] = 'Débiteur')
                             OR [N° Compte Général] LIKE '5%'
                    THEN [Débit] - [Crédit] ELSE 0 END) AS [Total Actif],
                SUM(CASE WHEN [N° Compte Général] LIKE '1%'
                             OR ([N° Compte Général] LIKE '4%' AND [Nature Compte] = 'Créditeur')
                    THEN [Crédit] - [Débit] ELSE 0 END) AS [Total Passif]
            FROM [Ecritures_Comptables]
            WHERE [Exercice] = YEAR(@dateFin)
              AND (@societe IS NULL OR [societe] = @societe)
            GROUP BY [societe]
        """,
        "parameters": '[{"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- ANALYTIQUE ---
    {
        "code": "DS_ANALYTIQUE_GLOBAL",
        "nom": "Analytique Global",
        "category": "Comptabilite",
        "description": "Synthese des ecritures analytiques",
        "query_template": """
            SELECT
                [Plan analytique] AS [Plan],
                [Compte analytique] AS [Compte],
                [Intitulé] AS [Intitule],
                [societe] AS [Société],
                SUM([Montant analytique]) AS [Montant],
                SUM([Quantité]) AS [Quantite],
                COUNT(*) AS [Nb Ecritures]
            FROM [Ecritures_Analytiques]
            WHERE (@societe IS NULL OR [societe] = @societe)
            GROUP BY [Plan analytique], [Compte analytique], [Intitulé], [societe]
            ORDER BY [Plan], ABS([Montant]) DESC
        """,
        "parameters": '[{"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_ANALYTIQUE_PAR_PLAN",
        "nom": "Analytique par Plan",
        "category": "Comptabilite",
        "description": "Ecritures analytiques agregees par plan",
        "query_template": """
            SELECT
                [Plan analytique] AS [Plan],
                [societe] AS [Société],
                SUM([Montant analytique]) AS [Total Montant],
                SUM([Quantité]) AS [Total Quantite],
                COUNT(*) AS [Nb Ecritures],
                COUNT(DISTINCT [Compte analytique]) AS [Nb Comptes]
            FROM [Ecritures_Analytiques]
            WHERE (@societe IS NULL OR [societe] = @societe)
            GROUP BY [Plan analytique], [societe]
            ORDER BY [Total Montant] DESC
        """,
        "parameters": '[{"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_ANALYTIQUE_DETAIL",
        "nom": "Detail Analytique",
        "category": "Comptabilite",
        "description": "Detail des ecritures analytiques",
        "query_template": """
            SELECT
                a.[N° interne],
                a.[Ligne],
                a.[Plan analytique] AS [Plan],
                a.[Compte analytique] AS [Compte Analytique],
                a.[Intitulé] AS [Intitule],
                a.[Montant analytique] AS [Montant],
                a.[Quantité] AS [Quantite],
                a.[societe] AS [Société]
            FROM [Ecritures_Analytiques] a
            WHERE (@societe IS NULL OR a.[societe] = @societe)
            ORDER BY a.[N° interne], a.[Ligne]
        """,
        "parameters": '[{"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- TRESORERIE ---
    {
        "code": "DS_TRESORERIE",
        "nom": "Tresorerie",
        "category": "Comptabilite",
        "description": "Situation de la tresorerie (classe 5)",
        "query_template": """
            SELECT
                [N° Compte Général] AS [Compte],
                [Intitulé compte général] AS [Intitule],
                [societe] AS [Société],
                SUM(CASE WHEN [Report à Nouveau] = 'Oui' THEN [Débit] - [Crédit] ELSE 0 END) AS [Solde Initial],
                SUM(CASE WHEN [Report à Nouveau] <> 'Oui' THEN [Débit] ELSE 0 END) AS [Encaissements],
                SUM(CASE WHEN [Report à Nouveau] <> 'Oui' THEN [Crédit] ELSE 0 END) AS [Decaissements],
                SUM([Débit]) - SUM([Crédit]) AS [Solde Final]
            FROM [Ecritures_Comptables]
            WHERE [Exercice] = YEAR(@dateFin)
              AND (@societe IS NULL OR [societe] = @societe)
              AND [N° Compte Général] LIKE '5%'
            GROUP BY [N° Compte Général], [Intitulé compte général], [societe]
            ORDER BY [Compte]
        """,
        "parameters": '[{"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_TRESORERIE_PAR_MOIS",
        "nom": "Tresorerie par Mois",
        "category": "Comptabilite",
        "description": "Evolution mensuelle de la tresorerie",
        "query_template": """
            SELECT
                [Année] AS [Annee],
                [Mois],
                [societe] AS [Société],
                SUM([Débit]) AS [Encaissements],
                SUM([Crédit]) AS [Decaissements],
                SUM([Débit]) - SUM([Crédit]) AS [Flux Net]
            FROM [Ecritures_Comptables]
            WHERE [N° Compte Général] LIKE '5%'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date d'écriture] BETWEEN @dateDebut AND @dateFin
            GROUP BY [Année], [Mois], [societe]
            ORDER BY [Annee], [Mois]
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- ECHEANCES COMPTABLES ---
    {
        "code": "DS_ECHEANCES_COMPTABLES",
        "nom": "Echeances Comptables",
        "category": "Comptabilite",
        "description": "Ecritures avec echeances",
        "query_template": """
            SELECT
                [Date d'échéance] AS [Echeance],
                [N° Compte Général] AS [Compte],
                [Compte Tiers],
                [Intitulé tiers] AS [Tiers],
                [N° Pièce] AS [Piece],
                [Libellé] AS [Libelle],
                [Débit],
                [Crédit],
                [Mode de règlement] AS [Mode de Règlement],
                [Lettrage],
                [Type tiers],
                [societe] AS [Société],
                DATEDIFF(DAY, GETDATE(), [Date d'échéance]) AS [Jours Avant Echeance]
            FROM [Ecritures_Comptables]
            WHERE [Date d'échéance] IS NOT NULL
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date d'échéance] BETWEEN @dateDebut AND @dateFin
              AND [Lettrage] IS NULL
            ORDER BY [Date d'échéance]
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_LETTRAGE",
        "nom": "Analyse Lettrage",
        "category": "Comptabilite",
        "description": "Analyse des ecritures lettrees et non lettrees",
        "query_template": """
            SELECT
                [N° Compte Général] AS [Compte],
                [Intitulé compte général] AS [Intitule],
                [societe] AS [Société],
                SUM(CASE WHEN [Lettrage] IS NOT NULL THEN 1 ELSE 0 END) AS [Nb Lettrees],
                SUM(CASE WHEN [Lettrage] IS NULL THEN 1 ELSE 0 END) AS [Nb Non Lettrees],
                SUM(CASE WHEN [Lettrage] IS NULL THEN [Débit] - [Crédit] ELSE 0 END) AS [Solde Non Lettre]
            FROM [Ecritures_Comptables]
            WHERE [Exercice] = YEAR(@dateFin)
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Saisie Echéance] = 'Oui'
            GROUP BY [N° Compte Général], [Intitulé compte général], [societe]
            HAVING SUM(CASE WHEN [Lettrage] IS NULL THEN 1 ELSE 0 END) > 0
            ORDER BY ABS([Solde Non Lettre]) DESC
        """,
        "parameters": '[{"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # ==================== RECOUVREMENT ====================
    # Balance Agee calculee dynamiquement a partir des echeances reelles
    {
        "code": "DS_BALANCE_AGEE",
        "nom": "Balance Agee",
        "category": "Recouvrement",
        "description": "Balance agee des creances clients calculee depuis Echeances_Ventes",
        "query_template": """
            SELECT
                e.[Code client] AS [Code Client],
                e.[Intitulé client] AS [Client],
                e.[societe] AS [Société],
                SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'échéance], GETDATE()) <= 0
                    THEN e.[Montant échéance] - ISNULL(e.[Montant du règlement], 0) ELSE 0 END) AS [Non Échu],
                SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'échéance], GETDATE()) BETWEEN 1 AND 30
                    THEN e.[Montant échéance] - ISNULL(e.[Montant du règlement], 0) ELSE 0 END) AS [0-30j],
                SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'échéance], GETDATE()) BETWEEN 31 AND 60
                    THEN e.[Montant échéance] - ISNULL(e.[Montant du règlement], 0) ELSE 0 END) AS [31-60j],
                SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'échéance], GETDATE()) BETWEEN 61 AND 90
                    THEN e.[Montant échéance] - ISNULL(e.[Montant du règlement], 0) ELSE 0 END) AS [61-90j],
                SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'échéance], GETDATE()) BETWEEN 91 AND 120
                    THEN e.[Montant échéance] - ISNULL(e.[Montant du règlement], 0) ELSE 0 END) AS [91-120j],
                SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'échéance], GETDATE()) > 120
                    THEN e.[Montant échéance] - ISNULL(e.[Montant du règlement], 0) ELSE 0 END) AS [+120j],
                SUM(e.[Montant échéance] - ISNULL(e.[Montant du règlement], 0)) AS [Total Créance],
                SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'échéance], GETDATE()) > 0
                    THEN e.[Montant échéance] - ISNULL(e.[Montant du règlement], 0) ELSE 0 END) AS [Total Echu],
                COUNT(*) AS [Nb Échéances],
                MAX(DATEDIFF(DAY, e.[Date d'échéance], GETDATE())) AS [Max Retard Jours]
            FROM [Echéances_Ventes] e
            WHERE e.[Montant échéance] > ISNULL(e.[Montant du règlement], 0)
              AND (@societe IS NULL OR e.[societe] = @societe)
            GROUP BY e.[Code client], e.[Intitulé client], e.[societe]
            ORDER BY [Total Creance] DESC
        """,
        "parameters": '[{"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    # DSO calcule a partir des reglements reels (Imputation_Factures_Ventes)
    {
        "code": "DS_DSO",
        "nom": "DSO par Client",
        "category": "Recouvrement",
        "description": "Delai moyen de paiement par client calcule depuis Imputation_Factures_Ventes",
        "query_template": """
            WITH Encours AS (
                SELECT
                    [Code client],
                    [Intitulé client],
                    [societe],
                    SUM([Montant échéance] - ISNULL([Montant du règlement], 0)) AS Total_Encours
                FROM [Echéances_Ventes]
                WHERE [Montant échéance] > ISNULL([Montant du règlement], 0)
              AND (@societe IS NULL OR [societe] = @societe)
                GROUP BY [Code client], [Intitulé client], [societe]
            ),
            Reglements AS (
                SELECT
                    [Code client],
                    SUM([Montant réglement]) AS Total_Regle_12M,
                    AVG(DATEDIFF(DAY, [Date document], [Date règlement])) AS Delai_Moyen_Paiement,
                    COUNT(DISTINCT [id Règlement]) AS Nb_Reglements
                FROM [Imputation_Factures_Ventes]
                WHERE [Date règlement] >= DATEADD(YEAR, -1, GETDATE())
                  AND [Date règlement] IS NOT NULL
                GROUP BY [Code client]
            ),
            CA AS (
                SELECT
                    [Code client],
                    SUM([Montant facture TTC]) AS CA_12M
                FROM [Imputation_Factures_Ventes]
                WHERE [Date document] >= DATEADD(YEAR, -1, GETDATE())
                GROUP BY [Code client]
            )
            SELECT
                enc.[Code client] AS [Code Client],
                enc.[Intitulé client] AS [Client],
                enc.[societe] AS [Société],
                enc.Total_Encours AS [Encours],
                ISNULL(ca.CA_12M, 0) AS [CA 12 Mois],
                ISNULL(reg.Total_Regle_12M, 0) AS [Regle 12 Mois],
                ISNULL(reg.Delai_Moyen_Paiement, 0) AS [Délai Moyen Paiement],
                ISNULL(reg.Nb_Reglements, 0) AS [Nb Règlements],
                CASE
                    WHEN ISNULL(ca.CA_12M, 0) > 0
                    THEN ROUND(enc.Total_Encours * 365.0 / ca.CA_12M, 1)
                    ELSE 0
                END AS [DSO Jours]
            FROM Encours enc
            LEFT JOIN Reglements reg ON enc.[Code client] = reg.[Code client]
            LEFT JOIN CA ca ON enc.[Code client] = ca.[Code client]
            ORDER BY [DSO Jours] DESC
        """,
        "parameters": '[{"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    # Creances douteuses calculees depuis les echeances reelles
    {
        "code": "DS_CREANCES_DOUTEUSES",
        "nom": "Creances Douteuses",
        "category": "Recouvrement",
        "description": "Creances de plus de 120 jours calculees depuis Echeances_Ventes",
        "query_template": """
            SELECT
                e.[Code client] AS [Code Client],
                e.[Intitulé client] AS [Client],
                e.[societe] AS [Société],
                SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'échéance], GETDATE()) > 120
                    THEN e.[Montant échéance] - ISNULL(e.[Montant du règlement], 0) ELSE 0 END) AS [Montant +120j],
                SUM(e.[Montant échéance] - ISNULL(e.[Montant du règlement], 0)) AS [Total Créance],
                CASE
                    WHEN SUM(e.[Montant échéance] - ISNULL(e.[Montant du règlement], 0)) > 0
                    THEN ROUND(SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'échéance], GETDATE()) > 120
                        THEN e.[Montant échéance] - ISNULL(e.[Montant du règlement], 0) ELSE 0 END) * 100.0
                        / SUM(e.[Montant échéance] - ISNULL(e.[Montant du règlement], 0)), 2)
                    ELSE 0
                END AS [% Douteux],
                COUNT(CASE WHEN DATEDIFF(DAY, e.[Date d'échéance], GETDATE()) > 120 THEN 1 END) AS [Nb Echeances +120j],
                MAX(DATEDIFF(DAY, e.[Date d'échéance], GETDATE())) AS [Max Retard Jours]
            FROM [Echéances_Ventes] e
            WHERE e.[Montant échéance] > ISNULL(e.[Montant du règlement], 0)
              AND (@societe IS NULL OR e.[societe] = @societe)
            GROUP BY e.[Code client], e.[Intitulé client], e.[societe]
            HAVING SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'échéance], GETDATE()) > 120
                THEN e.[Montant échéance] - ISNULL(e.[Montant du règlement], 0) ELSE 0 END) > 0
            ORDER BY [Montant +120j] DESC
        """,
        "parameters": '[{"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # ==================== ECHEANCES VENTES ====================
    {
        "code": "DS_ECHEANCES_NON_REGLEES",
        "nom": "Echeances Non Reglees",
        "category": "Recouvrement",
        "description": "Detail des echeances en attente de reglement avec calcul du retard",
        "query_template": """
            SELECT
                [societe] AS [Société],
                [Code client] AS [Code Client],
                [Intitulé client] AS [Client],
                [Code tiers payeur] AS [Code Tier Payeur],
                [Intitulé Tiers payeur] AS [Tier Payeur],
                [Type Document],
                [N° pièce] AS [Numéro Pièce],
                [Date document] AS [Date Document],
                [Date d'échéance] AS [Date Échéance],
                [Montant échéance] AS [Montant Échéance],
                [Montant TTC Net] AS [Montant TTC],
                [Montant du règlement] AS [Montant Regle],
                [Montant échéance] - ISNULL([Montant du règlement], 0) AS [Reste à Régler],
                [Mode de règlement] AS [Mode de Règlement],
                DATEDIFF(DAY, [Date d'échéance], GETDATE()) AS [Jours de Retard],
                CASE
                    WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) <= 0 THEN 'A echoir'
                    WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) <= 30 THEN '0-30 jours'
                    WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) <= 60 THEN '31-60 jours'
                    WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) <= 90 THEN '61-90 jours'
                    WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) <= 120 THEN '91-120 jours'
                    ELSE '+120 jours'
                END AS [Tranche Age]
            FROM [Echéances_Ventes]
            WHERE [Montant échéance] > ISNULL([Montant du règlement], 0)
              AND (@societe IS NULL OR [societe] = @societe)
            ORDER BY [Reste A Regler] DESC
        """,
        "parameters": '[{"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_ECHEANCES_PAR_CLIENT",
        "nom": "Echeances par Client",
        "category": "Recouvrement",
        "description": "Balance agee dynamique calculee a partir des echeances reelles",
        "query_template": """
            SELECT
                [Code client] AS [Code Client],
                [Intitulé client] AS [Client],
                [societe] AS [Société],
                COUNT(*) AS [Nb Échéances],
                SUM([Montant échéance]) AS [Total Échéances],
                SUM(ISNULL([Montant du règlement], 0)) AS [Total Réglé],
                SUM([Montant échéance] - ISNULL([Montant du règlement], 0)) AS [Reste à Régler],
                SUM(CASE WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) <= 0 THEN [Montant échéance] - ISNULL([Montant du règlement], 0) ELSE 0 END) AS [A Echoir],
                SUM(CASE WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) BETWEEN 1 AND 30 THEN [Montant échéance] - ISNULL([Montant du règlement], 0) ELSE 0 END) AS [0-30j],
                SUM(CASE WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) BETWEEN 31 AND 60 THEN [Montant échéance] - ISNULL([Montant du règlement], 0) ELSE 0 END) AS [31-60j],
                SUM(CASE WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) BETWEEN 61 AND 90 THEN [Montant échéance] - ISNULL([Montant du règlement], 0) ELSE 0 END) AS [61-90j],
                SUM(CASE WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) BETWEEN 91 AND 120 THEN [Montant échéance] - ISNULL([Montant du règlement], 0) ELSE 0 END) AS [91-120j],
                SUM(CASE WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) > 120 THEN [Montant échéance] - ISNULL([Montant du règlement], 0) ELSE 0 END) AS [+120j],
                CASE WHEN SUM([Montant échéance]) > 0
                    THEN ROUND(SUM(ISNULL([Montant du règlement], 0)) * 100.0 / SUM([Montant échéance]), 2)
                    ELSE 0 END AS [Taux Recouvrement %],
                MAX([Date d'échéance]) AS [Derniere Echeance],
                MAX(DATEDIFF(DAY, [Date d'échéance], GETDATE())) AS [Max Jours Retard]
            FROM [Echéances_Ventes]
            WHERE [Montant échéance] > ISNULL([Montant du règlement], 0)
              AND (@societe IS NULL OR [societe] = @societe)
            GROUP BY [Code client], [Intitulé client], [societe]
            ORDER BY [Reste A Regler] DESC
        """,
        "parameters": '[{"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_ECHEANCES_PAR_COMMERCIAL",
        "nom": "Echeances par Commercial",
        "category": "Recouvrement",
        "description": "Encours et retards par commercial ou charge de recouvrement",
        "query_template": """
            SELECT
                ISNULL(CAST(ev.[Code représentant] AS NVARCHAR(50)), 'N/A') AS [Code Commercial],
                ISNULL(ev.[Nom représentant], 'Non assigné') AS [Commercial],
                COUNT(DISTINCT e.[Code client]) AS [Nb Clients],
                COUNT(*) AS [Nb Échéances],
                SUM(e.[Montant échéance] - ISNULL(e.[Montant du règlement], 0)) AS [Encours Total],
                SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'échéance], GETDATE()) <= 0 THEN e.[Montant échéance] - ISNULL(e.[Montant du règlement], 0) ELSE 0 END) AS [A Echoir],
                SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'échéance], GETDATE()) BETWEEN 1 AND 30 THEN e.[Montant échéance] - ISNULL(e.[Montant du règlement], 0) ELSE 0 END) AS [0-30j],
                SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'échéance], GETDATE()) BETWEEN 31 AND 60 THEN e.[Montant échéance] - ISNULL(e.[Montant du règlement], 0) ELSE 0 END) AS [31-60j],
                SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'échéance], GETDATE()) BETWEEN 61 AND 90 THEN e.[Montant échéance] - ISNULL(e.[Montant du règlement], 0) ELSE 0 END) AS [61-90j],
                SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'échéance], GETDATE()) BETWEEN 91 AND 120 THEN e.[Montant échéance] - ISNULL(e.[Montant du règlement], 0) ELSE 0 END) AS [91-120j],
                SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'échéance], GETDATE()) > 120 THEN e.[Montant échéance] - ISNULL(e.[Montant du règlement], 0) ELSE 0 END) AS [+120j]
            FROM [Echéances_Ventes] e
            LEFT JOIN [Entête_des_ventes] ev ON e.[N° Pièce] = ev.[N° pièce]
                AND e.[Type Document] = ev.[Type Document]
                AND e.societe = ev.societe
            WHERE e.[Montant échéance] > ISNULL(e.[Montant du règlement], 0)
              AND (@societe IS NULL OR e.societe = @societe)
            GROUP BY ev.[Code représentant], ev.[Nom représentant]
            ORDER BY [Encours Total] DESC
        """,
        "parameters": '[{"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_ECHEANCES_PAR_MODE",
        "nom": "Echeances par Mode Reglement",
        "category": "Recouvrement",
        "description": "Repartition des echeances par mode de reglement",
        "query_template": """
            SELECT
                [Mode de règlement] AS [Mode de Règlement],
                [Code mode règlement] AS [Code Mode],
                COUNT(*) AS [Nb Échéances],
                SUM([Montant échéance]) AS [Total Échéances],
                SUM([Montant échéance] - ISNULL([Montant du règlement], 0)) AS [Reste à Régler],
                CASE WHEN SUM([Montant échéance]) > 0
                    THEN ROUND(SUM(ISNULL([Montant du règlement], 0)) * 100.0 / SUM([Montant échéance]), 2)
                    ELSE 0 END AS [Taux Recouvrement %],
                AVG(DATEDIFF(DAY, [Date d'échéance], GETDATE())) AS [Retard Moyen Jours]
            FROM [Echéances_Ventes]
            WHERE [Montant échéance] > ISNULL([Montant du règlement], 0)
              AND (@societe IS NULL OR [societe] = @societe)
            GROUP BY [Mode de règlement], [Code mode règlement]
            ORDER BY [Reste A Regler] DESC
        """,
        "parameters": '[{"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_ECHEANCES_A_ECHOIR",
        "nom": "Echeances a Echoir",
        "category": "Recouvrement",
        "description": "Echeances futures avec niveau d'urgence",
        "query_template": """
            SELECT
                [societe] AS [Société],
                [Code client] AS [Code Client],
                [Intitulé client] AS [Client],
                [N° pièce] AS [Numéro Pièce],
                [Date document] AS [Date Document],
                [Date d'échéance] AS [Date Échéance],
                [Montant échéance] - ISNULL([Montant du règlement], 0) AS [Montant à Régler],
                [Mode de règlement] AS [Mode de Règlement],
                [Nom collaborateur] + ' ' + [Prénom collaborateur] AS [Commercial],
                DATEDIFF(DAY, GETDATE(), [Date d'échéance]) AS [Jours Avant Echeance],
                CASE
                    WHEN DATEDIFF(DAY, GETDATE(), [Date d'échéance]) <= 7 THEN 'Cette semaine'
                    WHEN DATEDIFF(DAY, GETDATE(), [Date d'échéance]) <= 15 THEN 'Sous 15 jours'
                    WHEN DATEDIFF(DAY, GETDATE(), [Date d'échéance]) <= 30 THEN 'Sous 30 jours'
                    ELSE 'Plus de 30 jours'
                END AS [Urgence]
            FROM [Echéances_Ventes]
            WHERE [Date d'échéance] >= GETDATE()
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Montant échéance] > ISNULL([Montant du règlement], 0)
            ORDER BY [Date d'échéance] ASC
        """,
        "parameters": '[{"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # ==================== REGLEMENTS / IMPUTATIONS ====================
    {
        "code": "DS_REGLEMENTS_PAR_PERIODE",
        "nom": "Règlements par Période",
        "category": "Recouvrement",
        "description": "Évolution mensuelle des encaissements",
        "query_template": """
            SELECT
                YEAR([Date règlement]) AS [Annee],
                MONTH([Date règlement]) AS [Mois],
                FORMAT([Date règlement], 'yyyy-MM') AS [Periode],
                COUNT(DISTINCT [id Règlement]) AS [Nb Règlements],
                SUM([Montant réglement]) AS [Total Règlements],
                COUNT(DISTINCT [Code client]) AS [Nb Clients],
                AVG(DATEDIFF(DAY, [Date document], [Date règlement])) AS [Délai Moyen Jours]
            FROM [Imputation_Factures_Ventes]
            WHERE [Date règlement] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
            GROUP BY YEAR([Date règlement]), MONTH([Date règlement]), FORMAT([Date règlement], 'yyyy-MM')
            ORDER BY [Annee], [Mois]
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_REGLEMENTS_PAR_CLIENT",
        "nom": "Règlements par Client",
        "category": "Recouvrement",
        "description": "Historique des règlements avec délai moyen de paiement",
        "query_template": """
            SELECT
                [Code client] AS [Code Client],
                [Intitulé client] AS [Client],
                [societe] AS [Société],
                COUNT(DISTINCT [id Règlement]) AS [Nb Règlements],
                SUM([Montant réglement]) AS [Total Réglé],
                MIN([Date règlement]) AS [Premier Règlement],
                MAX([Date règlement]) AS [Dernier Règlement],
                AVG(DATEDIFF(DAY, [Date document], [Date règlement])) AS [Délai Moyen Jours]
            FROM [Imputation_Factures_Ventes]
            WHERE [Date règlement] IS NOT NULL
              AND (@societe IS NULL OR [societe] = @societe)
            GROUP BY [Code client], [Intitulé client], [societe]
            ORDER BY [Total Regle] DESC
        """,
        "parameters": '[{"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_REGLEMENTS_PAR_MODE",
        "nom": "Règlements par Mode",
        "category": "Recouvrement",
        "description": "Répartition des encaissements par mode de règlement",
        "query_template": """
            SELECT
                [Mode de réglement] AS [Mode de Règlement],
                COUNT(DISTINCT [id Règlement]) AS [Nb Règlements],
                SUM([Montant réglement]) AS [Total Réglé],
                COUNT(DISTINCT [Code client]) AS [Nb Clients],
                AVG(DATEDIFF(DAY, [Date document], [Date règlement])) AS [Délai Moyen Jours]
            FROM [Imputation_Factures_Ventes]
            WHERE [Date règlement] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
            GROUP BY [Mode de réglement]
            ORDER BY [Total Réglé] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_FACTURES_NON_REGLEES",
        "nom": "Factures Non Reglees",
        "category": "Recouvrement",
        "description": "Liste des factures en attente de reglement complet",
        "query_template": """
            SELECT
                [societe] AS [Société],
                [Code client] AS [Code Client],
                [Intitulé client] AS [Client],
                [Type Document],
                [N° pièce] AS [Numéro Pièce],
                [Date document] AS [Date Document],
                [Montant facture TTC] AS [Montant TTC],
                ISNULL([Montant régler], 0) AS [Montant Regle],
                [Montant facture TTC] - ISNULL([Montant régler], 0) AS [Reste à Régler],
                DATEDIFF(DAY, [Date document], GETDATE()) AS [Age Jours]
            FROM [Imputation_Factures_Ventes]
            WHERE [Montant facture TTC] > ISNULL([Montant régler], 0)
              AND (@societe IS NULL OR [societe] = @societe)
            GROUP BY [societe], [Code client], [Intitulé client], [Type Document],
                     [N° pièce], [Date document], [Montant facture TTC], [Montant régler]
            ORDER BY [Reste A Regler] DESC
        """,
        "parameters": '[{"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_KPI_RECOUVREMENT",
        "nom": "KPIs Recouvrement",
        "category": "Recouvrement",
        "description": "Indicateurs cles du recouvrement: encours, echu, a echoir, retard moyen",
        "query_template": """
            SELECT
                (SELECT SUM([Montant échéance] - ISNULL([Montant du règlement], 0))
                 FROM [Echéances_Ventes]
                 WHERE [Montant échéance] > ISNULL([Montant du règlement], 0)) AS [Encours Total],

                (SELECT SUM([Montant échéance] - ISNULL([Montant du règlement], 0))
                 FROM [Echéances_Ventes]
                 WHERE [Date d'échéance] >= GETDATE()
              AND (@societe IS NULL OR [societe] = @societe)
                   AND [Montant échéance] > ISNULL([Montant du règlement], 0)) AS [A Echoir],

                (SELECT SUM([Montant échéance] - ISNULL([Montant du règlement], 0))
                 FROM [Echéances_Ventes]
                 WHERE [Date d'échéance] < GETDATE()
                   AND [Montant échéance] > ISNULL([Montant du règlement], 0)) AS [Echu],

                (SELECT COUNT(*)
                 FROM [Echéances_Ventes]
                 WHERE [Date d'échéance] < GETDATE()
                   AND [Montant échéance] > ISNULL([Montant du règlement], 0)) AS [Nb Echeances Retard],

                (SELECT COUNT(DISTINCT [Code client])
                 FROM [Echéances_Ventes]
                 WHERE [Date d'échéance] < GETDATE()
                   AND [Montant échéance] > ISNULL([Montant du règlement], 0)) AS [Nb Clients Retard],

                (SELECT ISNULL(SUM([Montant règlement]), 0)
                 FROM [Imputation_Factures_Ventes]
                 WHERE MONTH([Date règlement]) = MONTH(GETDATE())
                   AND YEAR([Date règlement]) = YEAR(GETDATE())) AS [Reglements Mois],

                (SELECT AVG(DATEDIFF(DAY, [Date d'échéance], GETDATE()))
                 FROM [Echéances_Ventes]
                 WHERE [Date d'échéance] < GETDATE()
                   AND [Montant échéance] > ISNULL([Montant du règlement], 0)) AS [Retard Moyen Jours]
        """,
        "parameters": '[{"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # ==================== TABLEAU DE BORD ====================
    {
        "code": "DS_KPI_RESUME",
        "nom": "KPIs Resume",
        "category": "dashboard",
        "description": "Indicateurs cles pour le tableau de bord",
        "query_template": """
            SELECT
                (SELECT ISNULL(SUM([Montant HT Net]), 0)
                 FROM [Lignes_des_ventes]
                 WHERE [Valorise CA] = 'Oui'
                   AND [Date BL] BETWEEN @dateDebut AND @dateFin
                   AND (@societe IS NULL OR [societe] = @societe)) AS CA,

                (SELECT ISNULL(SUM([Montant HT Net] - [CMUP] * [Quantité]), 0)
                 FROM [Lignes_des_ventes]
                 WHERE [Valorise CA] = 'Oui'
                   AND [Date BL] BETWEEN @dateDebut AND @dateFin
                   AND (@societe IS NULL OR [societe] = @societe)) AS Marge,

                (SELECT ISNULL(SUM([Valeur du stock (montant)]), 0)
                 FROM [Etat_Stock]
                 WHERE (@societe IS NULL OR [societe] = @societe)) AS ValeurStock,

                (SELECT ISNULL(SUM([Montant échéance] - ISNULL([Montant du règlement], 0)), 0)
                 FROM [Echéances_Ventes]
                 WHERE [Montant échéance] > ISNULL([Montant du règlement], 0)
                   AND (@societe IS NULL OR [societe] = @societe)) AS Encours,

                (SELECT ISNULL(SUM([Montant échéance] - ISNULL([Montant du règlement], 0)), 0)
                 FROM [Echéances_Ventes]
                 WHERE [Montant échéance] > ISNULL([Montant du règlement], 0)
                   AND DATEDIFF(DAY, [Date d'échéance], GETDATE()) > 120
                   AND (@societe IS NULL OR [societe] = @societe)) AS CreancesDouteuses,

                (SELECT COUNT(DISTINCT [Code client])
                 FROM [Lignes_des_ventes]
                 WHERE [Valorise CA] = 'Oui'
                   AND [Date BL] BETWEEN @dateDebut AND @dateFin
                   AND (@societe IS NULL OR [societe] = @societe)) AS NbClientsActifs
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_TOP10_CLIENTS",
        "nom": "Top 10 Clients",
        "category": "dashboard",
        "description": "Les 10 meilleurs clients par CA",
        "query_template": """
            SELECT TOP 10
                [Code client] AS [Code],
                [Intitulé client] AS [Client],
                SUM([Montant HT Net]) AS CA,
                SUM([Montant HT Net] - [CMUP] * [Quantité]) AS Marge
            FROM [Lignes_des_ventes]
            WHERE [Valorise CA] = 'Oui'
              AND [Date BL] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
            GROUP BY [Code client], [Intitulé client]
            ORDER BY CA DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_TOP10_ARTICLES",
        "nom": "Top 10 Articles",
        "category": "dashboard",
        "description": "Les 10 articles les plus vendus",
        "query_template": """
            SELECT TOP 10
                [Code article] AS [Code],
                [Désignation ligne] AS [Article],
                SUM([Quantité]) AS [Qte],
                SUM([Montant HT Net]) AS CA
            FROM [Lignes_des_ventes]
            WHERE [Valorise CA] = 'Oui'
              AND [Date BL] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
            GROUP BY [Code article], [Désignation ligne]
            ORDER BY CA DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # ==================== VENTES - Variantes mensuelles pour TCD ====================
    # Ces templates ajoutent Annee, Mois, Periode aux groupements pour permettre
    # des tableaux croises dynamiques avec colonnes = Periode (yyyy-MM)

    {
        "code": "DS_VENTES_CLIENT_MOIS",
        "nom": "CA Client par Mois",
        "category": "Ventes",
        "description": "CA et marge par client ventiles par mois (pour TCD)",
        "query_template": """
            SELECT
                YEAR([Date BL]) AS [Annee],
                MONTH([Date BL]) AS [Mois],
                FORMAT([Date BL], 'yyyy-MM') AS [Periode],
                [Code client] AS [Code Client],
                [Intitulé client] AS [Client],
                [societe] AS [Société],
                SUM([Montant HT Net]) AS [CA HT],
                SUM([Montant TTC Net]) AS [CA TTC],
                SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) AS [Marge],
                CASE WHEN SUM([Montant HT Net]) > 0
                    THEN ROUND(SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) * 100.0 / SUM([Montant HT Net]), 2)
                    ELSE 0 END AS [Marge %],
                COUNT(DISTINCT [N° Pièce]) AS [Nb Factures],
                SUM([Quantité]) AS [Qte Totale]
            FROM [Lignes_des_ventes]
            WHERE [Valorise CA] = 'Oui'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date BL] BETWEEN @dateDebut AND @dateFin
            GROUP BY YEAR([Date BL]), MONTH([Date BL]), FORMAT([Date BL], 'yyyy-MM'),
                     [Code client], [Intitulé client], [societe]
            ORDER BY [Client], [Annee], [Mois]
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_VENTES_ARTICLE_MOIS",
        "nom": "CA Article par Mois",
        "category": "Ventes",
        "description": "CA et marge par article ventiles par mois (pour TCD)",
        "query_template": """
            SELECT
                YEAR([Date BL]) AS [Annee],
                MONTH([Date BL]) AS [Mois],
                FORMAT([Date BL], 'yyyy-MM') AS [Periode],
                [Code article] AS [Code Article],
                [Désignation ligne] AS [Article],
                [Catalogue 1] AS [Catalogue],
                SUM([Quantité]) AS [Qte Vendue],
                SUM([Montant HT Net]) AS [CA HT],
                SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) AS [Marge],
                CASE WHEN SUM([Montant HT Net]) > 0
                    THEN ROUND(SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) * 100.0 / SUM([Montant HT Net]), 2)
                    ELSE 0 END AS [Marge %]
            FROM [Lignes_des_ventes]
            WHERE [Valorise CA] = 'Oui'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date BL] BETWEEN @dateDebut AND @dateFin
            GROUP BY YEAR([Date BL]), MONTH([Date BL]), FORMAT([Date BL], 'yyyy-MM'),
                     [Code article], [Désignation ligne], [Catalogue 1]
            ORDER BY [Article], [Annee], [Mois]
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_VENTES_COMMERCIAL_MOIS",
        "nom": "CA Commercial par Mois",
        "category": "Ventes",
        "description": "Performance commerciale ventilee par mois (pour TCD)",
        "query_template": """
            SELECT
                YEAR(l.[Date BL]) AS [Annee],
                MONTH(l.[Date BL]) AS [Mois],
                FORMAT(l.[Date BL], 'yyyy-MM') AS [Periode],
                e.[Code représentant] AS [Code Commercial],
                e.[Nom représentant] AS [Commercial],
                l.[societe] AS [Société],
                COUNT(DISTINCT l.[Code client]) AS [Nb Clients],
                SUM(l.[Montant HT Net]) AS [CA HT],
                SUM(l.[Montant HT Net] - ISNULL(l.[CMUP], 0) * l.[Quantité]) AS [Marge],
                CASE WHEN SUM(l.[Montant HT Net]) > 0
                    THEN ROUND(SUM(l.[Montant HT Net] - ISNULL(l.[CMUP], 0) * l.[Quantité]) * 100.0 / SUM(l.[Montant HT Net]), 2)
                    ELSE 0 END AS [Marge %]
            FROM [Lignes_des_ventes] l
            INNER JOIN [Entête_des_ventes] e
                ON l.[DB_Id] = e.[DB_Id]
                AND l.[Type Document] = e.[Type Document]
                AND l.[N° Pièce] = e.[N° pièce]
            WHERE l.[Valorise CA] = 'Oui'
              AND (@societe IS NULL OR l.[societe] = @societe)
              AND l.[Date BL] BETWEEN @dateDebut AND @dateFin
            GROUP BY YEAR(l.[Date BL]), MONTH(l.[Date BL]), FORMAT(l.[Date BL], 'yyyy-MM'),
                     e.[Code représentant], e.[Nom représentant], l.[societe]
            ORDER BY [Commercial], [Annee], [Mois]
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_VENTES_CATALOGUE_MOIS",
        "nom": "CA Catalogue par Mois",
        "category": "Ventes",
        "description": "CA par catalogue ventile par mois (pour TCD)",
        "query_template": """
            SELECT
                YEAR([Date BL]) AS [Annee],
                MONTH([Date BL]) AS [Mois],
                FORMAT([Date BL], 'yyyy-MM') AS [Periode],
                ISNULL([Catalogue 1], '(Non classé)') AS [Catalogue],
                ISNULL([Catalogue 2], '(Non classé)') AS [Sous Catalogue],
                COUNT(DISTINCT [Code article]) AS [Nb Articles],
                SUM([Quantité]) AS [Qte Vendue],
                SUM([Montant HT Net]) AS [CA HT],
                SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) AS [Marge],
                CASE WHEN SUM([Montant HT Net]) > 0
                    THEN ROUND(SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) * 100.0 / SUM([Montant HT Net]), 2)
                    ELSE 0 END AS [Marge %]
            FROM [Lignes_des_ventes]
            WHERE [Valorise CA] = 'Oui'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date BL] BETWEEN @dateDebut AND @dateFin
            GROUP BY YEAR([Date BL]), MONTH([Date BL]), FORMAT([Date BL], 'yyyy-MM'),
                     ISNULL([Catalogue 1], '(Non classé)'), ISNULL([Catalogue 2], '(Non classé)')
            ORDER BY [Catalogue], [Annee], [Mois]
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # ==================== PIVOT V2 - Sources brutes pour Pivot Builder ====================
    # Ces templates exposent les donnees brutes (sans agregation)
    # L'agregation est geree par le moteur pivot V2 cote backend

    {
        "code": "DS_PIVOT_LIGNES_VENTES",
        "nom": "Pivot - Lignes des Ventes (Complet)",
        "category": "Pivot V2",
        "description": "Toutes les colonnes de Lignes_des_ventes pour analyse pivot. Dimensions: client, article, catalogue, gamme, depot, commercial, affaire, type document. Mesures: montants HT/TTC, quantites, prix, couts, marge.",
        "query_template": """
            SELECT
                -- Dimensions temporelles
                [Date],
                YEAR([Date]) AS [Annee],
                MONTH([Date]) AS [Mois],
                FORMAT([Date], 'yyyy-MM') AS [Periode],
                DATENAME(QUARTER, [Date]) AS [Trimestre],
                DATENAME(WEEKDAY, [Date]) AS [Jour Semaine],
                [Date document],
                [Date BL],
                [Date BC],
                [Date Livraison],

                -- Dimensions document
                [societe] AS [Société],
                [Type Document],
                [N° Pièce] AS [Numéro Pièce],
                [Valorise CA],

                -- Dimensions client
                [Code client] AS [Code Client],
                [Intitulé client] AS [Client],

                -- Dimensions article
                [Code article] AS [Code Article],
                [Désignation ligne] AS [Designation],
                [Référence] AS [Reference],

                -- Dimensions classification
                [Catalogue 1],
                [Catalogue 2],
                [Gamme 1],
                [Gamme 2],

                -- Dimensions logistique
                [Code dépôt] AS [Code Depot],
                [Intitulé dépôt] AS [Depot],
                [N° Série/Lot] AS [Num Serie Lot],

                -- Dimensions affaire
                [Code d'affaire] AS [Code Affaire],
                [Intitulé affaire] AS [Affaire],

                -- Mesures montants
                [Montant HT Net] AS [Montant HT],
                [Montant TTC Net] AS [Montant TTC],
                [Prix unitaire] AS [PU HT],
                [Prix unitaire TTC] AS [PU TTC],

                -- Mesures quantites
                [Quantité] AS [Qte],
                [Quantité BL] AS [Qte BL],
                [Quantité BC] AS [Qte BC],

                -- Mesures couts et marge
                [CMUP] AS [Prix Revient],
                [CMUP],
                [Coût standard] AS [Cout Standard],
                [Montant HT Net] - ISNULL([CMUP], 0) * [Quantité] AS [Marge],
                CASE WHEN [Montant HT Net] <> 0
                    THEN ROUND(([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) * 100.0 / [Montant HT Net], 2)
                    ELSE 0 END AS [Taux Marge],

                -- Mesures poids
                [Poids net],
                [Poids brut],
                [Colisage],

                -- Remises
                [Remise 1],
                [Remise 2]

            FROM [Lignes_des_ventes]
            WHERE [Date] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
              AND (@typeDocument IS NULL OR [Type Document] = @typeDocument)
              AND (@valoriseCA IS NULL OR [Valorise CA] = @valoriseCA)
            ORDER BY [Date] DESC, [Num Piece]
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}, {"name": "typeDocument", "type": "select", "source": "static", "options": [{"value": "Facture", "label": "Facture"}, {"value": "Facture comptabilisée", "label": "Facture comptabilisée"}, {"value": "Bon de livraison", "label": "Bon de livraison"}, {"value": "Bon de commande", "label": "Bon de commande"}, {"value": "Devis", "label": "Devis"}, {"value": "Bon avoir", "label": "Bon avoir"}, {"value": "Facture avoir", "label": "Facture avoir"}, {"value": "Bon de retour", "label": "Bon de retour"}], "required": false, "allow_null": true, "null_label": "(Tous)"}, {"name": "valoriseCA", "type": "select", "source": "static", "options": [{"value": "Oui", "label": "Oui"}, {"value": "Non", "label": "Non"}], "required": false, "allow_null": true, "null_label": "(Tous)"}]'
    },
    {
        "code": "DS_PIVOT_VENTES_CA",
        "nom": "Pivot - Ventes CA (Valorise CA = Oui)",
        "category": "Pivot V2",
        "description": "Lignes de ventes valorisees CA uniquement pour analyse pivot. Pre-filtre sur Valorise CA = Oui. Ideal pour analyses CA, marge, rentabilite.",
        "query_template": """
            SELECT
                -- Dimensions temporelles
                [Date],
                YEAR([Date]) AS [Annee],
                MONTH([Date]) AS [Mois],
                FORMAT([Date], 'yyyy-MM') AS [Periode],
                DATENAME(QUARTER, [Date]) AS [Trimestre],

                -- Dimensions
                [societe] AS [Société],
                [Type Document],
                [N° Pièce] AS [Numéro Pièce],
                [Code client] AS [Code Client],
                [Intitulé client] AS [Client],
                [Code article] AS [Code Article],
                [Désignation ligne] AS [Designation],
                [Catalogue 1],
                [Catalogue 2],
                [Gamme 1],
                [Gamme 2],
                [Code dépôt] AS [Code Depot],
                [Intitulé dépôt] AS [Depot],
                [Code d'affaire] AS [Code Affaire],
                [Intitulé affaire] AS [Affaire],

                -- Mesures
                [Montant HT Net] AS [Montant HT],
                [Montant TTC Net] AS [Montant TTC],
                [Quantité] AS [Qte],
                [Prix unitaire] AS [PU HT],
                [CMUP] AS [Prix Revient],
                ISNULL([CMUP], 0) * [Quantité] AS [Cout Revient],
                [Montant HT Net] - ISNULL([CMUP], 0) * [Quantité] AS [Marge Brute],
                CASE WHEN [Montant HT Net] <> 0
                    THEN ROUND(([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) * 100.0 / [Montant HT Net], 2)
                    ELSE 0 END AS [Taux Marge %]

            FROM [Lignes_des_ventes]
            WHERE [Valorise CA] = 'Oui'
              AND [Date BL] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
              AND (@typeDocument IS NULL OR [Type Document] = @typeDocument)
            ORDER BY [Date BL] DESC, [Num Piece]
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}, {"name": "typeDocument", "type": "select", "source": "static", "options": [{"value": "Facture", "label": "Facture"}, {"value": "Facture comptabilisée", "label": "Facture comptabilisée"}, {"value": "Bon de livraison", "label": "Bon de livraison"}], "required": false, "allow_null": true, "null_label": "(Tous)"}]'
    },

    # =============================================================================
    # NOUVEAUX TEMPLATES — Architecture 11 sections
    # =============================================================================

    # --- Comparatif Annuel N/N-1 ---
    {
        "code": "DS_COMPARATIF_ANNUEL",
        "nom": "Comparatif Annuel N/N-1",
        "category": "Tableau de Bord",
        "description": "Comparaison du CA, marge, volume, ticket moyen et remise entre l'annee en cours et l'annee precedente (2 lignes)",
        "query_template": """
            SELECT
                YEAR([Date]) AS [Annee],
                SUM([Montant HT Net]) AS [CA HT],
                SUM([Montant TTC Net]) AS [CA TTC],
                SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) AS [Marge],
                CASE WHEN SUM([Montant HT Net]) > 0
                    THEN ROUND(SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) * 100.0 / SUM([Montant HT Net]), 2)
                    ELSE 0 END AS [Marge %],
                COUNT(DISTINCT [Code client]) AS [Nb Clients],
                COUNT(DISTINCT [N° Pièce]) AS [Nb Documents],
                COUNT(*) AS [Nb Lignes],
                SUM([Quantité]) AS [Qte Totale],
                ROUND(SUM(ISNULL([Poids net], 0)), 2) AS [Poids Net Total],
                CASE WHEN COUNT(DISTINCT [N° Pièce]) > 0
                    THEN ROUND(SUM([Montant HT Net]) / COUNT(DISTINCT [N° Pièce]), 2)
                    ELSE 0 END AS [Ticket Moyen HT],
                CASE WHEN COUNT(DISTINCT [Code client]) > 0
                    THEN ROUND(SUM([Montant HT Net]) / COUNT(DISTINCT [Code client]), 2)
                    ELSE 0 END AS [CA Moy par Client],
                ROUND(CAST(COUNT(*) AS FLOAT) / NULLIF(COUNT(DISTINCT [N° Pièce]), 0), 1) AS [Lignes Moy par Doc],
                ROUND(SUM([Prix unitaire] * [Quantité]) - SUM([Montant HT Net]), 2) AS [Remise HT],
                CASE WHEN SUM([Prix unitaire] * [Quantité]) > 0
                    THEN ROUND((SUM([Prix unitaire] * [Quantité]) - SUM([Montant HT Net])) * 100.0 / SUM([Prix unitaire] * [Quantité]), 2)
                    ELSE 0 END AS [Taux Remise %]
            FROM [Lignes_des_ventes]
            WHERE [Valorise CA] = 'Oui'
              AND (@societe IS NULL OR [societe] = @societe)
              AND YEAR([Date]) IN (YEAR(@dateFin), YEAR(@dateFin) - 1)
            GROUP BY YEAR([Date])
            ORDER BY [Annee]
        """,
        "parameters": '[{"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- Comparatif Annuel N/N-1 — Pivot (1 ligne) ---
    {
        "code": "DS_COMPARATIF_ANNUEL_PIVOT",
        "nom": "Comparatif Annuel Pivot N/N-1",
        "category": "Tableau de Bord",
        "description": "Tous les KPIs N vs N-1 sur une seule ligne avec ecarts et evolutions : CA, marge, clients, documents, ticket moyen, remise",
        "query_template": """
            WITH Base AS (
                SELECT
                    YEAR([Date]) AS annee,
                    SUM([Montant HT Net])                                    AS ca_ht,
                    SUM([Montant TTC Net])                                   AS ca_ttc,
                    SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité])  AS marge,
                    COUNT(DISTINCT [Code client])                             AS nb_clients,
                    COUNT(DISTINCT [N° Pièce])                               AS nb_docs,
                    COUNT(*)                                                  AS nb_lignes,
                    SUM([Quantité])                                           AS qte_totale,
                    SUM([Prix unitaire] * [Quantité])                        AS ca_brut,
                    ROUND(SUM(ISNULL([Poids net], 0)), 2)                    AS poids_net
                FROM [Lignes_des_ventes]
                WHERE [Valorise CA] = 'Oui'
                  AND (@societe IS NULL OR [societe] = @societe)
                  AND YEAR([Date]) IN (YEAR(@dateFin), YEAR(@dateFin) - 1)
                GROUP BY YEAR([Date])
            ),
            N  AS (SELECT * FROM Base WHERE annee = YEAR(@dateFin)),
            N1 AS (SELECT * FROM Base WHERE annee = YEAR(@dateFin) - 1)
            SELECT
                YEAR(@dateFin)     AS [Annee N],
                YEAR(@dateFin) - 1 AS [Annee N-1],
                -- CA HT
                ISNULL(n.ca_ht, 0)                                                          AS [CA HT N],
                ISNULL(n1.ca_ht, 0)                                                         AS [CA HT N-1],
                ROUND(ISNULL(n.ca_ht, 0) - ISNULL(n1.ca_ht, 0), 2)                         AS [Ecart CA HT],
                CASE WHEN ISNULL(n1.ca_ht, 0) > 0
                     THEN ROUND((ISNULL(n.ca_ht, 0) - ISNULL(n1.ca_ht, 0)) * 100.0 / ISNULL(n1.ca_ht, 0), 2)
                     ELSE NULL END                                                           AS [Evol CA %],
                -- CA TTC
                ISNULL(n.ca_ttc, 0)                                                         AS [CA TTC N],
                ISNULL(n1.ca_ttc, 0)                                                        AS [CA TTC N-1],
                -- Marge
                ISNULL(n.marge, 0)                                                          AS [Marge N],
                ISNULL(n1.marge, 0)                                                         AS [Marge N-1],
                ROUND(ISNULL(n.marge, 0) - ISNULL(n1.marge, 0), 2)                         AS [Ecart Marge],
                CASE WHEN ISNULL(n1.marge, 0) <> 0
                     THEN ROUND((ISNULL(n.marge, 0) - ISNULL(n1.marge, 0)) * 100.0 / ABS(ISNULL(n1.marge, 0)), 2)
                     ELSE NULL END                                                           AS [Evol Marge %],
                -- Taux de marge
                CASE WHEN ISNULL(n.ca_ht, 0)  > 0 THEN ROUND(ISNULL(n.marge, 0)  * 100.0 / n.ca_ht,  2) ELSE 0 END AS [Marge % N],
                CASE WHEN ISNULL(n1.ca_ht, 0) > 0 THEN ROUND(ISNULL(n1.marge, 0) * 100.0 / n1.ca_ht, 2) ELSE 0 END AS [Marge % N-1],
                CASE WHEN ISNULL(n.ca_ht, 0)  > 0 THEN ROUND(ISNULL(n.marge, 0)  * 100.0 / n.ca_ht,  2) ELSE 0 END
                  - CASE WHEN ISNULL(n1.ca_ht, 0) > 0 THEN ROUND(ISNULL(n1.marge, 0) * 100.0 / n1.ca_ht, 2) ELSE 0 END AS [Ecart Marge %],
                -- Clients
                ISNULL(n.nb_clients, 0)                                                     AS [Nb Clients N],
                ISNULL(n1.nb_clients, 0)                                                    AS [Nb Clients N-1],
                ISNULL(n.nb_clients, 0) - ISNULL(n1.nb_clients, 0)                         AS [Ecart Clients],
                CASE WHEN ISNULL(n1.nb_clients, 0) > 0
                     THEN ROUND(CAST(ISNULL(n.nb_clients, 0) - ISNULL(n1.nb_clients, 0) AS FLOAT) * 100.0 / ISNULL(n1.nb_clients, 0), 2)
                     ELSE NULL END                                                           AS [Evol Clients %],
                -- Documents
                ISNULL(n.nb_docs, 0)                                                        AS [Nb Documents N],
                ISNULL(n1.nb_docs, 0)                                                       AS [Nb Documents N-1],
                ISNULL(n.nb_docs, 0) - ISNULL(n1.nb_docs, 0)                               AS [Ecart Documents],
                -- Lignes
                ISNULL(n.nb_lignes, 0)                                                      AS [Nb Lignes N],
                ISNULL(n1.nb_lignes, 0)                                                     AS [Nb Lignes N-1],
                -- Quantités
                ISNULL(n.qte_totale, 0)                                                     AS [Qte Totale N],
                ISNULL(n1.qte_totale, 0)                                                    AS [Qte Totale N-1],
                ROUND(ISNULL(n.qte_totale, 0) - ISNULL(n1.qte_totale, 0), 2)               AS [Ecart Qte],
                -- Ticket moyen
                CASE WHEN ISNULL(n.nb_docs, 0)  > 0 THEN ROUND(ISNULL(n.ca_ht, 0)  / n.nb_docs,  2) ELSE 0 END  AS [Ticket Moyen N],
                CASE WHEN ISNULL(n1.nb_docs, 0) > 0 THEN ROUND(ISNULL(n1.ca_ht, 0) / n1.nb_docs, 2) ELSE 0 END  AS [Ticket Moyen N-1],
                -- CA moyen par client
                CASE WHEN ISNULL(n.nb_clients, 0)  > 0 THEN ROUND(ISNULL(n.ca_ht, 0)  / n.nb_clients,  2) ELSE 0 END AS [CA Moy Client N],
                CASE WHEN ISNULL(n1.nb_clients, 0) > 0 THEN ROUND(ISNULL(n1.ca_ht, 0) / n1.nb_clients, 2) ELSE 0 END AS [CA Moy Client N-1],
                -- Remise
                ROUND(ISNULL(n.ca_brut, 0)  - ISNULL(n.ca_ht, 0),  2)                     AS [Remise HT N],
                ROUND(ISNULL(n1.ca_brut, 0) - ISNULL(n1.ca_ht, 0), 2)                     AS [Remise HT N-1],
                CASE WHEN ISNULL(n.ca_brut, 0)  > 0
                     THEN ROUND((ISNULL(n.ca_brut, 0)  - ISNULL(n.ca_ht, 0))  * 100.0 / ISNULL(n.ca_brut, 0),  2) ELSE 0 END AS [Taux Remise % N],
                CASE WHEN ISNULL(n1.ca_brut, 0) > 0
                     THEN ROUND((ISNULL(n1.ca_brut, 0) - ISNULL(n1.ca_ht, 0)) * 100.0 / ISNULL(n1.ca_brut, 0), 2) ELSE 0 END AS [Taux Remise % N-1],
                -- Poids
                ISNULL(n.poids_net,  0) AS [Poids Net N],
                ISNULL(n1.poids_net, 0) AS [Poids Net N-1]
            FROM (SELECT 1 AS dummy) d
            LEFT JOIN N  ON 1 = 1
            LEFT JOIN N1 ON 1 = 1
        """,
        "parameters": '[{"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- Comparatif Mensuel N/N-1 ---
    {
        "code": "DS_COMPARATIF_MENSUEL",
        "nom": "Comparatif Mensuel N/N-1",
        "category": "Tableau de Bord",
        "description": "Comparaison mois par mois N vs N-1 : CA, marge, clients, documents, ticket moyen, ecarts et evolutions",
        "query_template": """
            WITH Mois AS (
                SELECT
                    MONTH([Date]) AS mois_num,
                    CASE MONTH([Date])
                        WHEN 1  THEN 'Janvier'   WHEN 2  THEN 'Fevrier'
                        WHEN 3  THEN 'Mars'       WHEN 4  THEN 'Avril'
                        WHEN 5  THEN 'Mai'        WHEN 6  THEN 'Juin'
                        WHEN 7  THEN 'Juillet'    WHEN 8  THEN 'Aout'
                        WHEN 9  THEN 'Septembre'  WHEN 10 THEN 'Octobre'
                        WHEN 11 THEN 'Novembre'   WHEN 12 THEN 'Decembre'
                    END AS mois_label,
                    SUM(CASE WHEN YEAR([Date]) = YEAR(@dateFin)     THEN [Montant HT Net] ELSE 0 END) AS ca_n,
                    SUM(CASE WHEN YEAR([Date]) = YEAR(@dateFin) - 1 THEN [Montant HT Net] ELSE 0 END) AS ca_n1,
                    SUM(CASE WHEN YEAR([Date]) = YEAR(@dateFin)
                        THEN [Montant HT Net] - ISNULL([CMUP], 0) * [Quantité] ELSE 0 END) AS marge_n,
                    SUM(CASE WHEN YEAR([Date]) = YEAR(@dateFin) - 1
                        THEN [Montant HT Net] - ISNULL([CMUP], 0) * [Quantité] ELSE 0 END) AS marge_n1,
                    COUNT(DISTINCT CASE WHEN YEAR([Date]) = YEAR(@dateFin)     THEN [Code client] END) AS nb_clients_n,
                    COUNT(DISTINCT CASE WHEN YEAR([Date]) = YEAR(@dateFin) - 1 THEN [Code client] END) AS nb_clients_n1,
                    COUNT(DISTINCT CASE WHEN YEAR([Date]) = YEAR(@dateFin)     THEN [N° Pièce] END)    AS nb_docs_n,
                    COUNT(DISTINCT CASE WHEN YEAR([Date]) = YEAR(@dateFin) - 1 THEN [N° Pièce] END)    AS nb_docs_n1,
                    SUM(CASE WHEN YEAR([Date]) = YEAR(@dateFin)     THEN [Quantité] ELSE 0 END) AS qte_n,
                    SUM(CASE WHEN YEAR([Date]) = YEAR(@dateFin) - 1 THEN [Quantité] ELSE 0 END) AS qte_n1
                FROM [Lignes_des_ventes]
                WHERE [Valorise CA] = 'Oui'
                  AND (@societe IS NULL OR [societe] = @societe)
                  AND YEAR([Date]) IN (YEAR(@dateFin), YEAR(@dateFin) - 1)
                GROUP BY MONTH([Date])
            )
            SELECT
                mois_num                                                                          AS [Mois],
                mois_label                                                                        AS [Mois Label],
                YEAR(@dateFin)                                                                    AS [Annee N],
                YEAR(@dateFin) - 1                                                                AS [Annee N-1],
                ca_n                                                                              AS [CA HT N],
                ca_n1                                                                             AS [CA HT N-1],
                ROUND(ca_n - ca_n1, 2)                                                            AS [Ecart CA],
                CASE WHEN ca_n1 > 0 THEN ROUND((ca_n - ca_n1) * 100.0 / ca_n1, 2) ELSE NULL END  AS [Evol CA %],
                marge_n                                                                           AS [Marge N],
                marge_n1                                                                          AS [Marge N-1],
                ROUND(marge_n - marge_n1, 2)                                                      AS [Ecart Marge],
                CASE WHEN ca_n  > 0 THEN ROUND(marge_n  * 100.0 / ca_n,  2) ELSE 0 END           AS [Marge % N],
                CASE WHEN ca_n1 > 0 THEN ROUND(marge_n1 * 100.0 / ca_n1, 2) ELSE 0 END           AS [Marge % N-1],
                nb_clients_n                                                                      AS [Nb Clients N],
                nb_clients_n1                                                                     AS [Nb Clients N-1],
                nb_clients_n - nb_clients_n1                                                      AS [Ecart Clients],
                nb_docs_n                                                                         AS [Nb Documents N],
                nb_docs_n1                                                                        AS [Nb Documents N-1],
                nb_docs_n - nb_docs_n1                                                            AS [Ecart Documents],
                qte_n                                                                             AS [Qte N],
                qte_n1                                                                            AS [Qte N-1],
                ROUND(qte_n - qte_n1, 2)                                                          AS [Ecart Qte],
                CASE WHEN nb_docs_n  > 0 THEN ROUND(ca_n  / nb_docs_n,  2) ELSE 0 END            AS [Ticket Moyen N],
                CASE WHEN nb_docs_n1 > 0 THEN ROUND(ca_n1 / nb_docs_n1, 2) ELSE 0 END            AS [Ticket Moyen N-1],
                CASE WHEN nb_clients_n  > 0 THEN ROUND(ca_n  / nb_clients_n,  2) ELSE 0 END      AS [CA Moy Client N],
                CASE WHEN nb_clients_n1 > 0 THEN ROUND(ca_n1 / nb_clients_n1, 2) ELSE 0 END      AS [CA Moy Client N-1]
            FROM Mois
            ORDER BY mois_num
        """,
        "parameters": '[{"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- CA par Canal (Categorie tarifaire) ---
    {
        "code": "DS_VENTES_PAR_CANAL",
        "nom": "CA par Canal de Vente",
        "category": "Chiffre d Affaires",
        "description": "Repartition du CA par canal de vente (Categorie tarifaire depuis Entete des ventes)",
        "query_template": """
            SELECT
                e.[Catégorie tarifaire] AS [Canal de Vente],
                l.[societe] AS [Société],
                COUNT(DISTINCT l.[Code client]) AS [Nb Clients],
                COUNT(DISTINCT l.[N° Pièce]) AS [Nb Documents],
                SUM(l.[Quantité]) AS [Qte Vendue],
                SUM(l.[Montant HT Net]) AS [CA HT],
                SUM(l.[Montant TTC Net]) AS [CA TTC],
                SUM(l.[Montant HT Net] - ISNULL(l.[CMUP], 0) * l.[Quantité]) AS [Marge],
                CASE WHEN SUM(l.[Montant HT Net]) > 0
                    THEN ROUND(SUM(l.[Montant HT Net] - ISNULL(l.[CMUP], 0) * l.[Quantité]) * 100.0 / SUM(l.[Montant HT Net]), 2)
                    ELSE 0 END AS [Marge %]
            FROM [Lignes_des_ventes] l
            INNER JOIN [Entête_des_ventes] e
                ON l.[DB_Id] = e.[DB_Id]
                AND l.[Type Document] = e.[Type Document]
                AND l.[N° Pièce] = e.[N° pièce]
            WHERE l.[Valorise CA] = 'Oui'
              AND (@societe IS NULL OR l.[societe] = @societe)
              AND l.[Date BL] BETWEEN @dateDebut AND @dateFin
            GROUP BY e.[Catégorie tarifaire], l.[societe]
            ORDER BY [CA HT] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- Panier Moyen Client ---
    {
        "code": "DS_PANIER_MOYEN_CLIENT",
        "nom": "Panier Moyen par Client",
        "category": "Analyse Clients",
        "description": "Panier moyen par client: CA moyen par facture, frequence d'achat",
        "query_template": """
            SELECT
                [Code client] AS [Code Client],
                [Intitulé client] AS [Client],
                [societe] AS [Société],
                COUNT(DISTINCT [N° Pièce]) AS [Nb Factures],
                SUM([Montant HT Net]) AS [CA HT Total],
                CASE WHEN COUNT(DISTINCT [N° Pièce]) > 0
                    THEN ROUND(SUM([Montant HT Net]) / COUNT(DISTINCT [N° Pièce]), 2)
                    ELSE 0 END AS [Panier Moyen HT],
                COUNT(DISTINCT [Code article]) AS [Nb Articles Distincts],
                CASE WHEN COUNT(DISTINCT [N° Pièce]) > 0
                    THEN ROUND(CAST(COUNT(*) AS FLOAT) / COUNT(DISTINCT [N° Pièce]), 1)
                    ELSE 0 END AS [Lignes Moy par Facture],
                MIN([Date BL]) AS [Premiere Vente],
                MAX([Date BL]) AS [Derniere Vente],
                DATEDIFF(DAY, MIN([Date BL]), MAX([Date BL])) AS [Anciennete Jours]
            FROM [Lignes_des_ventes]
            WHERE [Valorise CA] = 'Oui'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date BL] BETWEEN @dateDebut AND @dateFin
            GROUP BY [Code client], [Intitulé client], [societe]
            ORDER BY [Panier Moyen HT] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- Clients Nouveaux ---
    {
        "code": "DS_CLIENTS_NOUVEAUX",
        "nom": "Clients Nouveaux",
        "category": "Analyse Clients",
        "description": "Clients dont la premiere vente se situe dans la periode selectionnee",
        "query_template": """
            WITH PremierAchat AS (
                SELECT
                    [Code client],
                    MIN([Date BL]) AS [Date Premier Achat]
                FROM [Lignes_des_ventes]
                WHERE [Valorise CA] = 'Oui'
                  AND (@societe IS NULL OR [societe] = @societe)
                GROUP BY [Code client]
            )
            SELECT
                l.[Code client] AS [Code Client],
                l.[Intitulé client] AS [Client],
                l.[societe] AS [Société],
                p.[Date Premier Achat],
                SUM(l.[Montant HT Net]) AS [CA HT Periode],
                COUNT(DISTINCT l.[N° Pièce]) AS [Nb Factures],
                COUNT(DISTINCT l.[Code article]) AS [Nb Articles]
            FROM [Lignes_des_ventes] l
            INNER JOIN PremierAchat p ON l.[Code client] = p.[Code client]
            WHERE l.[Valorise CA] = 'Oui'
              AND (@societe IS NULL OR l.[societe] = @societe)
              AND l.[Date BL] BETWEEN @dateDebut AND @dateFin
              AND p.[Date Premier Achat] BETWEEN @dateDebut AND @dateFin
            GROUP BY l.[Code client], l.[Intitulé client], l.[societe], p.[Date Premier Achat]
            ORDER BY [CA HT Periode] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- Clients Perdus ---
    {
        "code": "DS_CLIENTS_PERDUS",
        "nom": "Clients Perdus",
        "category": "Analyse Clients",
        "description": "Clients actifs l'annee precedente mais sans achat sur la periode en cours",
        "query_template": """
            WITH ClientsAnneePrecedente AS (
                SELECT DISTINCT [Code client]
                FROM [Lignes_des_ventes]
                WHERE [Valorise CA] = 'Oui'
                  AND (@societe IS NULL OR [societe] = @societe)
                  AND [Date BL] BETWEEN DATEADD(YEAR, -1, @dateDebut) AND DATEADD(YEAR, -1, @dateFin)
            ),
            ClientsPeriode AS (
                SELECT DISTINCT [Code client]
                FROM [Lignes_des_ventes]
                WHERE [Valorise CA] = 'Oui'
                  AND (@societe IS NULL OR [societe] = @societe)
                  AND [Date BL] BETWEEN @dateDebut AND @dateFin
            )
            SELECT
                l.[Code client] AS [Code Client],
                l.[Intitulé client] AS [Client],
                l.[societe] AS [Société],
                MAX(l.[Date]) AS [Derniere Vente],
                DATEDIFF(DAY, MAX(l.[Date]), @dateFin) AS [Jours Sans Achat],
                SUM(l.[Montant HT Net]) AS [CA HT Annee Precedente],
                COUNT(DISTINCT l.[N° Pièce]) AS [Nb Factures Annee Precedente]
            FROM [Lignes_des_ventes] l
            INNER JOIN ClientsAnneePrecedente cap ON l.[Code client] = cap.[Code client]
            LEFT JOIN ClientsPeriode cp ON l.[Code client] = cp.[Code client]
            WHERE cp.[Code client] IS NULL
              AND l.[Valorise CA] = 'Oui'
              AND (@societe IS NULL OR l.[societe] = @societe)
              AND l.[Date BL] BETWEEN DATEADD(YEAR, -1, @dateDebut) AND DATEADD(YEAR, -1, @dateFin)
            GROUP BY l.[Code client], l.[Intitulé client], l.[societe]
            ORDER BY [CA HT Annee Precedente] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- Segmentation ABC Clients ---
    {
        "code": "DS_SEGMENTATION_ABC",
        "nom": "Segmentation ABC Clients",
        "category": "Analyse Clients",
        "description": "Classification ABC des clients par CA cumule (A=80%, B=15%, C=5%)",
        "query_template": """
            WITH CA_Client AS (
                SELECT
                    [Code client],
                    [Intitulé client],
                    [societe],
                    SUM([Montant HT Net]) AS [CA HT]
                FROM [Lignes_des_ventes]
                WHERE [Valorise CA] = 'Oui'
                  AND (@societe IS NULL OR [societe] = @societe)
                  AND [Date BL] BETWEEN @dateDebut AND @dateFin
                GROUP BY [Code client], [Intitulé client], [societe]
            ),
            CA_Ranked AS (
                SELECT *,
                    SUM([CA HT]) OVER (ORDER BY [CA HT] DESC) AS [CA Cumule],
                    SUM([CA HT]) OVER () AS [CA Total],
                    ROW_NUMBER() OVER (ORDER BY [CA HT] DESC) AS [Rang]
                FROM CA_Client
            )
            SELECT
                [Code client] AS [Code Client],
                [Intitulé client] AS [Client],
                [societe] AS [Société],
                [CA HT],
                [Rang],
                ROUND([CA Cumule] * 100.0 / NULLIF([CA Total], 0), 2) AS [% Cumule],
                CASE
                    WHEN [CA Cumule] * 100.0 / NULLIF([CA Total], 0) <= 80 THEN 'A'
                    WHEN [CA Cumule] * 100.0 / NULLIF([CA Total], 0) <= 95 THEN 'B'
                    ELSE 'C'
                END AS [Segment]
            FROM CA_Ranked
            ORDER BY [Rang]
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- Taux de Transformation Devis ---
    {
        "code": "DS_TAUX_TRANSFORMATION",
        "nom": "Taux Transformation Devis",
        "category": "Performance Commerciale",
        "description": "Taux de conversion des devis en commandes/factures par periode et commercial",
        "query_template": """
            WITH Devis AS (
                SELECT
                    YEAR([Date]) AS [Annee],
                    MONTH([Date]) AS [Mois],
                    FORMAT([Date], 'yyyy-MM') AS [Periode],
                    [societe] AS [Société],
                    COUNT(DISTINCT [N° Pièce]) AS [Nb Devis],
                    SUM([Montant HT Net]) AS [Montant Devis HT]
                FROM [Lignes_des_ventes]
                WHERE [Type Document] = 'Devis'
                  AND (@societe IS NULL OR [societe] = @societe)
                  AND [Date document] BETWEEN @dateDebut AND @dateFin
                GROUP BY YEAR([Date]), MONTH([Date]), FORMAT([Date], 'yyyy-MM'), [societe]
            ),
            Commandes AS (
                SELECT
                    YEAR([Date]) AS [Annee],
                    MONTH([Date]) AS [Mois],
                    [societe] AS [Société],
                    COUNT(DISTINCT [N° Pièce]) AS [Nb Commandes],
                    SUM([Montant HT Net]) AS [Montant Commandes HT]
                FROM [Lignes_des_ventes]
                WHERE [Type Document] = 'Bon de commande'
                  AND (@societe IS NULL OR [societe] = @societe)
                  AND [Date document] BETWEEN @dateDebut AND @dateFin
                GROUP BY YEAR([Date]), MONTH([Date]), [societe]
            )
            SELECT
                d.[Periode],
                d.[Societe],
                d.[Nb Devis],
                d.[Montant Devis HT],
                ISNULL(c.[Nb Commandes], 0) AS [Nb Commandes],
                ISNULL(c.[Montant Commandes HT], 0) AS [Montant Commandes HT],
                CASE WHEN d.[Nb Devis] > 0
                    THEN ROUND(CAST(ISNULL(c.[Nb Commandes], 0) AS FLOAT) * 100.0 / d.[Nb Devis], 1)
                    ELSE 0 END AS [Taux Transformation %],
                CASE WHEN d.[Montant Devis HT] > 0
                    THEN ROUND(ISNULL(c.[Montant Commandes HT], 0) * 100.0 / d.[Montant Devis HT], 1)
                    ELSE 0 END AS [Taux Transformation Montant %]
            FROM Devis d
            LEFT JOIN Commandes c ON d.[Annee] = c.[Annee] AND d.[Mois] = c.[Mois] AND d.[Societe] = c.[Societe]
            ORDER BY d.[Annee], d.[Mois]
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- Echeances Achats (Fournisseurs) ---
    {
        "code": "DS_ECHEANCES_ACHATS",
        "nom": "Échéances Achats Fournisseurs",
        "category": "Achats",
        "description": "Échéances fournisseurs non réglées avec calcul de retard",
        "query_template": """
            SELECT
                [societe] AS [Société],
                [Code fournisseur] AS [Code Fournisseur],
                [Intitulé fournisseur] AS [Fournisseur],
                [Type Document],
                [N° pièce] AS [Numéro Pièce],
                [Date document] AS [Date Document],
                [Date d'échéance] AS [Date Échéance],
                [Montant échéance] AS [Montant Échéance],
                ISNULL(TRY_CAST([Régler] AS DECIMAL(18,2)), 0) AS [Montant Réglé],
                [Montant échéance] - ISNULL(TRY_CAST([Régler] AS DECIMAL(18,2)), 0) AS [Reste à Payer],
                [Mode de réglement] AS [Mode de Règlement],
                DATEDIFF(DAY, [Date d'échéance], GETDATE()) AS [Jours de Retard],
                CASE
                    WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) <= 0 THEN 'À échoir'
                    WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) <= 30 THEN '0-30 jours'
                    WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) <= 60 THEN '31-60 jours'
                    WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) <= 90 THEN '61-90 jours'
                    ELSE '+90 jours'
                END AS [Tranche d'Âge]
            FROM [Echeances_Achats]
            WHERE [Montant échéance] > ISNULL(TRY_CAST([Régler] AS DECIMAL(18,2)), 0)
              AND (@societe IS NULL OR [societe] = @societe)
            ORDER BY [Date d'échéance] ASC
        """,
        "parameters": '[{"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- BL Non Factures ---
    {
        "code": "DS_BL_NON_FACTURES",
        "nom": "BL Non Factures",
        "category": "Logistique",
        "description": "Bons de livraison sans facture associee",
        "query_template": """
            SELECT
                bl.[societe] AS [Société],
                bl.[N° Pièce] AS [Num BL],
                bl.[Date BL],
                bl.[Code client] AS [Code Client],
                bl.[Intitulé client] AS [Client],
                bl.[Code article] AS [Code Article],
                bl.[Désignation ligne] AS [Designation],
                bl.[Quantité BL] AS [Qte BL],
                bl.[Montant HT Net] AS [Montant HT],
                bl.[Code dépôt] AS [Code Depot],
                bl.[Intitulé dépôt] AS [Depot],
                DATEDIFF(DAY, bl.[Date BL], GETDATE()) AS [Age BL Jours]
            FROM [Lignes_des_ventes] bl
            WHERE bl.[Type Document] = 'Bon de livraison'
              AND (@societe IS NULL OR bl.[societe] = @societe)
              AND bl.[Date] BETWEEN @dateDebut AND @dateFin
              AND NOT EXISTS (
                  SELECT 1 FROM [Lignes_des_ventes] f
                  WHERE f.[Type Document] IN ('Facture', 'Facture comptabilisée')
                    AND f.[N° Pièce BL] = bl.[N° Pièce]
                    AND f.[Code article] = bl.[Code article]
                    AND f.[DB_Id] = bl.[DB_Id]
              )
            ORDER BY bl.[Date BL], bl.[N° Pièce]
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # ==========================================================================
    # ENRICHISSEMENTS V2 — Nouveaux datasources (Gammes, Pipeline, Alertes, Stock+)
    # ==========================================================================

    # --- CA par Gamme (angle mort : Gamme1/Gamme2 remontees mais jamais exploitees) ---
    {
        "code": "DS_VENTES_PAR_GAMME",
        "nom": "CA par Gamme",
        "category": "Ventes",
        "description": "Chiffre d'affaires et marge par gamme de produits (Gamme 1 / Gamme 2)",
        "query_template": """
            SELECT
                ISNULL(NULLIF([Gamme 1], ''), '(Non classé)') AS [Gamme],
                ISNULL(NULLIF([Gamme 2], ''), '(Non classé)') AS [Sous Gamme],
                [societe] AS [Société],
                COUNT(DISTINCT [Code article]) AS [Nb Articles],
                SUM([Quantité]) AS [Qte Vendue],
                SUM([Montant HT Net]) AS [CA HT],
                SUM([Montant TTC Net]) AS [CA TTC],
                SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) AS [Marge],
                CASE WHEN SUM([Montant HT Net]) > 0
                    THEN ROUND(SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) * 100.0 / SUM([Montant HT Net]), 2)
                    ELSE 0 END AS [Marge %],
                COUNT(DISTINCT [Code client]) AS [Nb Clients],
                COUNT(DISTINCT [N° Pièce]) AS [Nb Documents]
            FROM [Lignes_des_ventes]
            WHERE [Valorise CA] = 'Oui'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date BL] BETWEEN @dateDebut AND @dateFin
            GROUP BY ISNULL(NULLIF([Gamme 1], ''), '(Non classé)'), ISNULL(NULLIF([Gamme 2], ''), '(Non classé)'), [societe]
            ORDER BY [CA HT] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- CA par Categorie Tarifaire ---
    {
        "code": "DS_VENTES_PAR_CATEGORIE_TARIF",
        "nom": "CA par Categorie Tarifaire",
        "category": "Ventes",
        "description": "Chiffre d'affaires par categorie tarifaire client",
        "query_template": """
            SELECT
                c.[Catégorie tarifaire] AS [Categorie Tarifaire],
                l.[societe] AS [Société],
                COUNT(DISTINCT l.[Code client]) AS [Nb Clients],
                SUM(l.[Quantité]) AS [Qte Vendue],
                SUM(l.[Montant HT Net]) AS [CA HT],
                SUM(l.[Montant HT Net] - ISNULL(l.[CMUP], 0) * l.[Quantité]) AS [Marge],
                CASE WHEN SUM(l.[Montant HT Net]) > 0
                    THEN ROUND(SUM(l.[Montant HT Net] - ISNULL(l.[CMUP], 0) * l.[Quantité]) * 100.0 / SUM(l.[Montant HT Net]), 2)
                    ELSE 0 END AS [Marge %],
                CASE WHEN COUNT(DISTINCT l.[Code client]) > 0
                    THEN ROUND(SUM(l.[Montant HT Net]) / COUNT(DISTINCT l.[Code client]), 2)
                    ELSE 0 END AS [CA Moyen par Client],
                COUNT(DISTINCT l.[N° Pièce]) AS [Nb Documents]
            FROM [Lignes_des_ventes] l
            INNER JOIN [Clients] c ON l.[Code client] = c.[Code client] AND l.[societe] = c.[societe]
            WHERE l.[Valorise CA] = 'Oui'
              AND (@societe IS NULL OR l.[societe] = @societe)
              AND l.[Date BL] BETWEEN @dateDebut AND @dateFin
            GROUP BY c.[Catégorie tarifaire], l.[societe]
            ORDER BY [CA HT] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- Contribution Marginale (Pareto cumule) ---
    {
        "code": "DS_CONTRIBUTION_MARGINALE",
        "nom": "Contribution Marginale",
        "category": "Ventes",
        "description": "Analyse Pareto : contribution de chaque client au CA total (% cumule)",
        "query_template": """
            WITH CA_Client AS (
                SELECT
                    [Code client],
                    [Intitulé client],
                    [societe],
                    SUM([Montant HT Net]) AS [CA HT],
                    SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) AS [Marge]
                FROM [Lignes_des_ventes]
                WHERE [Valorise CA] = 'Oui'
                  AND (@societe IS NULL OR [societe] = @societe)
                  AND [Date BL] BETWEEN @dateDebut AND @dateFin
                GROUP BY [Code client], [Intitulé client], [societe]
            ),
            Ranked AS (
                SELECT *,
                    ROW_NUMBER() OVER (ORDER BY [CA HT] DESC) AS [Rang],
                    SUM([CA HT]) OVER (ORDER BY [CA HT] DESC) AS [CA Cumule],
                    SUM([CA HT]) OVER () AS [CA Total],
                    SUM([Marge]) OVER () AS [Marge Totale]
                FROM CA_Client
            )
            SELECT
                [Code client] AS [Code Client],
                [Intitulé client] AS [Client],
                [societe] AS [Société],
                [Rang],
                [CA HT],
                [Marge],
                ROUND([CA HT] * 100.0 / NULLIF([CA Total], 0), 2) AS [% CA],
                ROUND([CA Cumule] * 100.0 / NULLIF([CA Total], 0), 2) AS [% CA Cumule],
                ROUND([Marge] * 100.0 / NULLIF([Marge Totale], 0), 2) AS [% Marge]
            FROM Ranked
            ORDER BY [Rang]
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- Marge par Gamme ---
    {
        "code": "DS_MARGE_PAR_GAMME",
        "nom": "Marge par Gamme",
        "category": "Marges",
        "description": "Analyse des marges par gamme de produits",
        "query_template": """
            SELECT
                ISNULL(NULLIF([Gamme 1], ''), '(Non classé)') AS [Gamme],
                ISNULL(NULLIF([Gamme 2], ''), '(Non classé)') AS [Sous Gamme],
                [societe] AS [Société],
                SUM([Montant HT Net]) AS [CA HT],
                SUM(ISNULL([CMUP], 0) * [Quantité]) AS [Cout Revient],
                SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) AS [Marge],
                CASE WHEN SUM([Montant HT Net]) > 0
                    THEN ROUND(SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) * 100.0 / SUM([Montant HT Net]), 2)
                    ELSE 0 END AS [Marge %],
                SUM([Quantité]) AS [Qte Vendue],
                COUNT(DISTINCT [Code article]) AS [Nb Articles]
            FROM [Lignes_des_ventes]
            WHERE [Valorise CA] = 'Oui'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date BL] BETWEEN @dateDebut AND @dateFin
            GROUP BY ISNULL(NULLIF([Gamme 1], ''), '(Non classé)'), ISNULL(NULLIF([Gamme 2], ''), '(Non classé)'), [societe]
            ORDER BY [Marge] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- Alerte Marge Negative ---
    {
        "code": "DS_MARGE_NEGATIVE",
        "nom": "Alertes Marge Negative",
        "category": "Marges",
        "description": "Lignes de vente avec marge negative (alerte direction)",
        "query_template": """
            SELECT
                [societe] AS [Société],
                [Date BL] AS [Date],
                [N° Pièce] AS [Num Piece],
                [Code client] AS [Code Client],
                [Intitulé client] AS [Client],
                [Code article] AS [Code Article],
                [Désignation ligne] AS [Designation],
                [Catalogue 1] AS [Catalogue],
                [Gamme 1] AS [Gamme],
                [Quantité] AS [Qte],
                [Prix unitaire] AS [PU HT],
                [CMUP] AS [Cout Revient],
                [Montant HT Net] AS [CA HT],
                [Montant HT Net] - ISNULL([CMUP], 0) * [Quantité] AS [Marge],
                CASE WHEN [Montant HT Net] <> 0
                    THEN ROUND(([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) * 100.0 / [Montant HT Net], 2)
                    ELSE 0 END AS [Marge %],
                [Code représentant] AS [Code Commercial],
                [Nom représentant] AS [Commercial]
            FROM [Lignes_des_ventes]
            WHERE [Valorise CA] = 'Oui'
              AND ([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) < 0
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date BL] BETWEEN @dateDebut AND @dateFin
            ORDER BY ([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) ASC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- Pipeline Commercial (Devis -> BC -> BL -> Facture) ---
    {
        "code": "DS_PIPELINE_COMMERCIAL",
        "nom": "Pipeline Commercial",
        "category": "Performance Commerciale",
        "description": "Funnel commercial : volume et montant par etape (Devis, BC, BL, Facture)",
        "query_template": """
            SELECT
                [Type Document] AS [Etape],
                [societe] AS [Société],
                COUNT(DISTINCT [N° Pièce]) AS [Nb Documents],
                COUNT(*) AS [Nb Lignes],
                SUM([Montant HT Net]) AS [Montant HT],
                SUM([Montant TTC Net]) AS [Montant TTC],
                COUNT(DISTINCT [Code client]) AS [Nb Clients],
                COUNT(DISTINCT [Code article]) AS [Nb Articles],
                SUM([Quantité]) AS [Qte Totale]
            FROM [Lignes_des_ventes]
            WHERE [Type Document] IN ('Devis', 'Bon de commande', 'Bon de livraison', 'Facture', 'Facture comptabilisée')
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date document] BETWEEN @dateDebut AND @dateFin
            GROUP BY [Type Document], [societe]
            ORDER BY CASE [Type Document]
                WHEN 'Devis' THEN 1
                WHEN 'Bon de commande' THEN 2
                WHEN 'Bon de livraison' THEN 3
                WHEN 'Facture' THEN 4
                WHEN 'Facture comptabilisée' THEN 5
                ELSE 6 END
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- Delai Moyen par Etape (BC->BL, BL->Facture) ---
    {
        "code": "DS_DELAIS_ETAPES",
        "nom": "Delais par Etape",
        "category": "Performance Commerciale",
        "description": "Delai moyen entre etapes du cycle commercial (BC->BL, BL->Facture)",
        "query_template": """
            SELECT
                [societe] AS [Société],
                FORMAT([Date BL], 'yyyy-MM') AS [Periode],
                COUNT(DISTINCT [N° Pièce]) AS [Nb Documents],
                AVG(CASE WHEN [Date BC] IS NOT NULL AND [Date BL] IS NOT NULL
                    THEN DATEDIFF(DAY, [Date BC], [Date BL]) END) AS [Delai BC vers BL (j)],
                AVG(CASE WHEN [Date BL] IS NOT NULL AND [Date document] IS NOT NULL
                    AND [Type Document] IN ('Facture', 'Facture comptabilisée')
                    THEN DATEDIFF(DAY, [Date BL], [Date document]) END) AS [Delai BL vers Facture (j)],
                AVG(CASE WHEN [Date BC] IS NOT NULL AND [Date document] IS NOT NULL
                    AND [Type Document] IN ('Facture', 'Facture comptabilisée')
                    THEN DATEDIFF(DAY, [Date BC], [Date document]) END) AS [Delai Total BC vers Facture (j)],
                MIN(CASE WHEN [Date BC] IS NOT NULL AND [Date BL] IS NOT NULL
                    THEN DATEDIFF(DAY, [Date BC], [Date BL]) END) AS [Min Delai BC-BL],
                MAX(CASE WHEN [Date BC] IS NOT NULL AND [Date BL] IS NOT NULL
                    THEN DATEDIFF(DAY, [Date BC], [Date BL]) END) AS [Max Delai BC-BL]
            FROM [Lignes_des_ventes]
            WHERE [Valorise CA] = 'Oui'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date BL] BETWEEN @dateDebut AND @dateFin
            GROUP BY [societe], FORMAT([Date BL], 'yyyy-MM')
            ORDER BY [Periode]
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- Documents en Anomalie ---
    {
        "code": "DS_DOCUMENTS_ANOMALIE",
        "nom": "Documents en Anomalie",
        "category": "Documents",
        "description": "BL sans facture >30j, BC sans BL >60j — detection des blocages",
        "query_template": """
            WITH BL_Sans_Facture AS (
                SELECT
                    bl.[societe],
                    'BL sans Facture' AS [Type Anomalie],
                    bl.[N° Pièce] AS [Num Piece],
                    bl.[Date BL] AS [Date Document],
                    bl.[Code client],
                    bl.[Intitulé client] AS [Client],
                    SUM(bl.[Montant HT Net]) AS [Montant HT],
                    DATEDIFF(DAY, bl.[Date BL], GETDATE()) AS [Age Jours]
                FROM [Lignes_des_ventes] bl
                WHERE bl.[Type Document] = 'Bon de livraison'
                  AND (@societe IS NULL OR bl.[societe] = @societe)
                  AND bl.[Date BL] BETWEEN @dateDebut AND @dateFin
                  AND NOT EXISTS (
                      SELECT 1 FROM [Lignes_des_ventes] f
                      WHERE f.[Type Document] IN ('Facture', 'Facture comptabilisée')
                        AND f.[N° Pièce BL] = bl.[N° Pièce]
                        AND f.[societe] = bl.[societe]
                  )
                  AND DATEDIFF(DAY, bl.[Date BL], GETDATE()) > 30
                GROUP BY bl.[societe], bl.[N° Pièce], bl.[Date BL], bl.[Code client], bl.[Intitulé client]
            ),
            BC_Sans_BL AS (
                SELECT
                    bc.[societe],
                    'BC sans BL' AS [Type Anomalie],
                    bc.[N° Pièce] AS [Num Piece],
                    bc.[Date BC] AS [Date Document],
                    bc.[Code client],
                    bc.[Intitulé client] AS [Client],
                    SUM(bc.[Montant HT Net]) AS [Montant HT],
                    DATEDIFF(DAY, bc.[Date BC], GETDATE()) AS [Age Jours]
                FROM [Lignes_des_ventes] bc
                WHERE bc.[Type Document] = 'Bon de commande'
                  AND (@societe IS NULL OR bc.[societe] = @societe)
                  AND bc.[Date BC] BETWEEN @dateDebut AND @dateFin
                  AND NOT EXISTS (
                      SELECT 1 FROM [Lignes_des_ventes] bl
                      WHERE bl.[Type Document] = 'Bon de livraison'
                        AND bl.[N° Pièce BC] = bc.[N° Pièce]
                        AND bl.[societe] = bc.[societe]
                  )
                  AND DATEDIFF(DAY, bc.[Date BC], GETDATE()) > 60
                GROUP BY bc.[societe], bc.[N° Pièce], bc.[Date BC], bc.[Code client], bc.[Intitulé client]
            )
            SELECT * FROM BL_Sans_Facture
            UNION ALL
            SELECT * FROM BC_Sans_BL
            ORDER BY [Age Jours] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- Concentration Risque Client ---
    {
        "code": "DS_CONCENTRATION_RISQUE",
        "nom": "Concentration Risque Client",
        "category": "Analyse Clients",
        "description": "Dependance au top clients : alerte si un client depasse 30% du CA",
        "query_template": """
            WITH CA_Client AS (
                SELECT
                    [Code client],
                    [Intitulé client],
                    [societe],
                    SUM([Montant HT Net]) AS [CA HT]
                FROM [Lignes_des_ventes]
                WHERE [Valorise CA] = 'Oui'
                  AND (@societe IS NULL OR [societe] = @societe)
                  AND [Date BL] BETWEEN @dateDebut AND @dateFin
                GROUP BY [Code client], [Intitulé client], [societe]
            ),
            Totaux AS (
                SELECT [societe], SUM([CA HT]) AS [CA Total] FROM CA_Client GROUP BY [societe]
            )
            SELECT TOP 20
                c.[Code client] AS [Code Client],
                c.[Intitulé client] AS [Client],
                c.[societe] AS [Société],
                c.[CA HT],
                t.[CA Total],
                ROUND(c.[CA HT] * 100.0 / NULLIF(t.[CA Total], 0), 2) AS [% du CA Total],
                CASE
                    WHEN c.[CA HT] * 100.0 / NULLIF(t.[CA Total], 0) >= 30 THEN 'CRITIQUE'
                    WHEN c.[CA HT] * 100.0 / NULLIF(t.[CA Total], 0) >= 20 THEN 'ELEVE'
                    WHEN c.[CA HT] * 100.0 / NULLIF(t.[CA Total], 0) >= 10 THEN 'MOYEN'
                    ELSE 'FAIBLE'
                END AS [Niveau Risque]
            FROM CA_Client c
            INNER JOIN Totaux t ON c.[societe] = t.[societe]
            ORDER BY c.[CA HT] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- Evolution ABC Clients (mouvement entre segments) ---
    {
        "code": "DS_EVOLUTION_ABC",
        "nom": "Evolution ABC Clients",
        "category": "Analyse Clients",
        "description": "Mouvement des clients entre segments ABC d'une annee a l'autre",
        "query_template": """
            WITH ABC_N AS (
                SELECT
                    [Code client], [Intitulé client], [societe],
                    SUM([Montant HT Net]) AS [CA N],
                    CASE
                        WHEN SUM([Montant HT Net]) * 100.0 / NULLIF(SUM(SUM([Montant HT Net])) OVER(), 0) <= 80 THEN 'A'
                        WHEN SUM([Montant HT Net]) * 100.0 / NULLIF(SUM(SUM([Montant HT Net])) OVER(), 0) <= 95 THEN 'B'
                        ELSE 'C' END AS [Segment N]
                FROM [Lignes_des_ventes]
                WHERE [Valorise CA] = 'Oui'
                  AND (@societe IS NULL OR [societe] = @societe)
                  AND [Date BL] BETWEEN @dateDebut AND @dateFin
                GROUP BY [Code client], [Intitulé client], [societe]
            ),
            ABC_N1 AS (
                SELECT
                    [Code client], [societe],
                    SUM([Montant HT Net]) AS [CA N-1],
                    CASE
                        WHEN SUM([Montant HT Net]) * 100.0 / NULLIF(SUM(SUM([Montant HT Net])) OVER(), 0) <= 80 THEN 'A'
                        WHEN SUM([Montant HT Net]) * 100.0 / NULLIF(SUM(SUM([Montant HT Net])) OVER(), 0) <= 95 THEN 'B'
                        ELSE 'C' END AS [Segment N-1]
                FROM [Lignes_des_ventes]
                WHERE [Valorise CA] = 'Oui'
                  AND (@societe IS NULL OR [societe] = @societe)
                  AND [Date BL] BETWEEN DATEADD(YEAR, -1, @dateDebut) AND DATEADD(YEAR, -1, @dateFin)
                GROUP BY [Code client], [societe]
            )
            SELECT
                n.[Code client] AS [Code Client],
                n.[Intitulé client] AS [Client],
                n.[societe] AS [Société],
                ISNULL(n1.[Segment N-1], 'Nouveau') AS [Segment N-1],
                n.[Segment N],
                ISNULL(n1.[CA N-1], 0) AS [CA N-1],
                n.[CA N],
                n.[CA N] - ISNULL(n1.[CA N-1], 0) AS [Evolution CA],
                CASE
                    WHEN n.[Segment N] = ISNULL(n1.[Segment N-1], '') THEN 'Stable'
                    WHEN n.[Segment N] < ISNULL(n1.[Segment N-1], 'D') THEN 'Promotion'
                    ELSE 'Regression'
                END AS [Mouvement]
            FROM ABC_N n
            LEFT JOIN ABC_N1 n1 ON n.[Code client] = n1.[Code client] AND n.[societe] = n1.[societe]
            ORDER BY n.[CA N] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- Matrice Client x Article (cross-sell) ---
    {
        "code": "DS_MATRICE_CLIENT_ARTICLE",
        "nom": "Matrice Client x Article",
        "category": "Analyse Clients",
        "description": "Quel client achete quel article — detection opportunites de cross-sell",
        "query_template": """
            SELECT
                [Code client] AS [Code Client],
                [Intitulé client] AS [Client],
                [Code article] AS [Code Article],
                [Désignation ligne] AS [Article],
                [Catalogue 1] AS [Catalogue],
                [Gamme 1] AS [Gamme],
                [societe] AS [Société],
                SUM([Quantité]) AS [Qte Totale],
                SUM([Montant HT Net]) AS [CA HT],
                COUNT(DISTINCT [N° Pièce]) AS [Nb Commandes],
                MIN([Date BL]) AS [Premier Achat],
                MAX([Date BL]) AS [Dernier Achat]
            FROM [Lignes_des_ventes]
            WHERE [Valorise CA] = 'Oui'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date BL] BETWEEN @dateDebut AND @dateFin
            GROUP BY [Code client], [Intitulé client], [Code article], [Désignation ligne],
                     [Catalogue 1], [Gamme 1], [societe]
            ORDER BY [CA HT] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- Portefeuille Commercial x Client ---
    {
        "code": "DS_PORTEFEUILLE_COMMERCIAL",
        "nom": "Portefeuille Commercial",
        "category": "Performance Commerciale",
        "description": "Repartition du portefeuille clients par commercial",
        "query_template": """
            SELECT
                [Code représentant] AS [Code Commercial],
                [Nom représentant] AS [Commercial],
                [Code client] AS [Code Client],
                [Intitulé client] AS [Client],
                [societe] AS [Société],
                SUM([Montant HT Net]) AS [CA HT],
                SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) AS [Marge],
                COUNT(DISTINCT [N° Pièce]) AS [Nb Documents],
                MIN([Date BL]) AS [Premier Achat],
                MAX([Date BL]) AS [Dernier Achat],
                DATEDIFF(DAY, MAX([Date BL]), GETDATE()) AS [Jours Sans Achat]
            FROM [Lignes_des_ventes]
            WHERE [Valorise CA] = 'Oui'
              AND [Code représentant] IS NOT NULL AND [Code représentant] <> ''
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date BL] BETWEEN @dateDebut AND @dateFin
            GROUP BY [Code représentant], [Nom représentant], [Code client], [Intitulé client], [societe]
            ORDER BY [Commercial], [CA HT] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- Stock Valorisation Multi-methodes ---
    {
        "code": "DS_STOCK_VALORISATION",
        "nom": "Valorisation Stock Multi-methodes",
        "category": "Stocks",
        "description": "Valorisation du stock selon differentes methodes comptables (CMUP, Prix revient, DPA)",
        "query_template": """
            WITH StockActuel AS (
                SELECT
                    [Code article],
                    [Référence],
                    [Désignation],
                    [Intitulé famille],
                    [societe],
                    SUM(CASE WHEN [Sens de mouvement] = 'Entrée' THEN [Quantité] ELSE -[Quantité] END) AS stock_qte,
                    MAX([CMUP]) AS cmup,
                    MAX([CMUP]) AS prix_revient,
                    MAX([DPA-Période]) AS dpa_periode,
                    MAX([DPA-Vente]) AS dpa_vente,
                    MAX([Coût standard]) AS cout_standard
                FROM [Mouvement_stock]
                WHERE (@societe IS NULL OR [societe] = @societe)
                GROUP BY [Code article], [Référence], [Désignation], [Intitulé famille], [societe]
                HAVING SUM(CASE WHEN [Sens de mouvement] = 'Entrée' THEN [Quantité] ELSE -[Quantité] END) > 0
            )
            SELECT
                [Code article] AS [Code Article],
                [Référence] AS [Reference],
                [Désignation] AS [Designation],
                [Intitulé famille] AS [Famille],
                [societe] AS [Société],
                stock_qte AS [Stock Qte],
                cmup AS [CMUP],
                stock_qte * cmup AS [Valeur CMUP],
                prix_revient AS [Prix Revient],
                stock_qte * ISNULL(prix_revient, 0) AS [Valeur Prix Revient],
                dpa_periode AS [DPA Periode],
                stock_qte * ISNULL(dpa_periode, 0) AS [Valeur DPA],
                cout_standard AS [Cout Standard],
                stock_qte * ISNULL(cout_standard, 0) AS [Valeur Cout Standard],
                stock_qte * cmup - stock_qte * ISNULL(prix_revient, 0) AS [Ecart CMUP vs Revient]
            FROM StockActuel
            ORDER BY [Valeur CMUP] DESC
        """,
        "parameters": '[{"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- Stock vs Ventes (couverture) ---
    {
        "code": "DS_STOCK_COUVERTURE",
        "nom": "Couverture Stock vs Ventes",
        "category": "Stocks",
        "description": "Stock actuel rapporte aux ventes mensuelles moyennes = couverture en mois",
        "query_template": """
            WITH StockActuel AS (
                SELECT
                    [Code article],
                    [Référence],
                    [Désignation],
                    [Intitulé famille],
                    [societe],
                    SUM(CASE WHEN [Sens de mouvement] = 'Entrée' THEN [Quantité] ELSE -[Quantité] END) AS stock_qte,
                    MAX([CMUP]) AS cmup
                FROM [Mouvement_stock]
                WHERE (@societe IS NULL OR [societe] = @societe)
                GROUP BY [Code article], [Référence], [Désignation], [Intitulé famille], [societe]
                HAVING SUM(CASE WHEN [Sens de mouvement] = 'Entrée' THEN [Quantité] ELSE -[Quantité] END) > 0
            ),
            VentesMensuelles AS (
                SELECT
                    [Code article],
                    [societe],
                    SUM([Quantité]) / NULLIF(DATEDIFF(MONTH,
                        MIN([Date BL]),
                        MAX([Date BL])) + 1, 0) AS qte_mensuelle_moy
                FROM [Lignes_des_ventes]
                WHERE [Valorise CA] = 'Oui'
                  AND (@societe IS NULL OR [societe] = @societe)
                  AND [Date BL] >= DATEADD(MONTH, -12, GETDATE())
                GROUP BY [Code article], [societe]
            )
            SELECT
                s.[Code article] AS [Code Article],
                s.[Référence] AS [Reference],
                s.[Désignation] AS [Designation],
                s.[Intitulé famille] AS [Famille],
                s.[societe] AS [Société],
                s.stock_qte AS [Stock Actuel],
                s.cmup AS [CMUP],
                s.stock_qte * s.cmup AS [Valeur Stock],
                ROUND(ISNULL(v.qte_mensuelle_moy, 0), 2) AS [Vente Moy/Mois],
                CASE WHEN ISNULL(v.qte_mensuelle_moy, 0) > 0
                    THEN ROUND(s.stock_qte / v.qte_mensuelle_moy, 1)
                    ELSE 9999 END AS [Couverture Mois],
                CASE
                    WHEN ISNULL(v.qte_mensuelle_moy, 0) = 0 THEN 'Sans vente'
                    WHEN s.stock_qte / v.qte_mensuelle_moy < 1 THEN 'CRITIQUE (<1 mois)'
                    WHEN s.stock_qte / v.qte_mensuelle_moy < 2 THEN 'FAIBLE (1-2 mois)'
                    WHEN s.stock_qte / v.qte_mensuelle_moy < 6 THEN 'NORMAL (2-6 mois)'
                    ELSE 'SURSTOCK (>6 mois)'
                END AS [Alerte]
            FROM StockActuel s
            LEFT JOIN VentesMensuelles v ON s.[Code article] = v.[Code article] AND s.[societe] = v.[societe]
            ORDER BY [Couverture Mois] ASC
        """,
        "parameters": '[{"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- Articles proches peremption ---
    {
        "code": "DS_STOCK_PEREMPTION",
        "nom": "Articles Proches Peremption",
        "category": "Stocks",
        "description": "Stock avec dates de peremption proches ou depassees",
        "query_template": """
            SELECT
                [Code article] AS [Code Article],
                [Référence] AS [Reference],
                [Désignation] AS [Designation],
                [Intitulé famille] AS [Famille],
                [N° Série / Lot] AS [Lot],
                [Code Dépôt] AS [Code Depot],
                [Dépôt] AS [Depot],
                [Date Péremption] AS [Date Peremption],
                [Date Fabrication] AS [Date Fabrication],
                [societe] AS [Société],
                SUM(CASE WHEN [Sens de mouvement] = 'Entrée' THEN [Quantité] ELSE -[Quantité] END) AS [Stock Qte],
                MAX([CMUP]) AS [CMUP],
                SUM(CASE WHEN [Sens de mouvement] = 'Entrée' THEN [Quantité] ELSE -[Quantité] END) * MAX([CMUP]) AS [Valeur Stock],
                DATEDIFF(DAY, GETDATE(), [Date Péremption]) AS [Jours Restants],
                CASE
                    WHEN [Date Péremption] < GETDATE() THEN 'PERIME'
                    WHEN DATEDIFF(DAY, GETDATE(), [Date Péremption]) <= 30 THEN 'CRITIQUE (<30j)'
                    WHEN DATEDIFF(DAY, GETDATE(), [Date Péremption]) <= 90 THEN 'ALERTE (<90j)'
                    WHEN DATEDIFF(DAY, GETDATE(), [Date Péremption]) <= 180 THEN 'ATTENTION (<6 mois)'
                    ELSE 'OK'
                END AS [Statut]
            FROM [Mouvement_stock]
            WHERE [Date Péremption] IS NOT NULL
              AND (@societe IS NULL OR [societe] = @societe)
            GROUP BY [Code article], [Référence], [Désignation], [Intitulé famille],
                     [N° Série / Lot], [Code Dépôt], [Dépôt], [Date Péremption], [Date Fabrication], [societe]
            HAVING SUM(CASE WHEN [Sens de mouvement] = 'Entrée' THEN [Quantité] ELSE -[Quantité] END) > 0
               AND DATEDIFF(DAY, GETDATE(), [Date Péremption]) <= 180
            ORDER BY [Jours Restants] ASC
        """,
        "parameters": '[{"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- Mouvements Inter-Depots ---
    {
        "code": "DS_MVT_INTER_DEPOTS",
        "nom": "Mouvements Inter-Depots",
        "category": "Stocks",
        "description": "Transferts de stock entre depots (virements internes)",
        "query_template": """
            SELECT
                [Date Mouvement] AS [Date],
                [N° Pièce] AS [N Piece],
                [Code article] AS [Code Article],
                [Désignation] AS [Designation],
                [Intitulé famille] AS [Famille],
                [Code Dépôt] AS [Code Depot],
                [Dépôt] AS [Depot],
                [Sens de mouvement] AS [Sens],
                [Quantité] AS [Quantite],
                [CMUP],
                [Quantité] * [CMUP] AS [Valeur],
                [societe] AS [Société]
            FROM [Mouvement_stock]
            WHERE [Type Mouvement] IN ('Virement de dépôt à dépôt', 'Transfert')
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date Mouvement] BETWEEN @dateDebut AND @dateFin
            ORDER BY [Date Mouvement] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- Articles Composes ---
    {
        "code": "DS_ARTICLES_COMPOSES",
        "nom": "Articles Composes",
        "category": "Stocks",
        "description": "Mouvements des articles composes (nomenclatures)",
        "query_template": """
            SELECT
                [Code article] AS [Code Article],
                [Référence] AS [Reference],
                [Désignation] AS [Designation],
                [Intitulé famille] AS [Famille],
                [Article composé] AS [Article Compose],
                [societe] AS [Société],
                COUNT(*) AS [Nb Mouvements],
                SUM(CASE WHEN [Sens de mouvement] = 'Entrée' THEN [Quantité] ELSE 0 END) AS [Qte Entrees],
                SUM(CASE WHEN [Sens de mouvement] = 'Sortie' THEN [Quantité] ELSE 0 END) AS [Qte Sorties],
                SUM(CASE WHEN [Sens de mouvement] = 'Entrée' THEN [Quantité] ELSE -[Quantité] END) AS [Solde Qte],
                MAX([CMUP]) AS [CMUP],
                SUM(CASE WHEN [Sens de mouvement] = 'Entrée' THEN [Quantité] ELSE -[Quantité] END) * MAX([CMUP]) AS [Valeur Stock]
            FROM [Mouvement_stock]
            WHERE [Article composé] IS NOT NULL AND [Article composé] <> ''
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date Mouvement] BETWEEN @dateDebut AND @dateFin
            GROUP BY [Code article], [Référence], [Désignation], [Intitulé famille],
                     [Article composé], [societe]
            ORDER BY [Nb Mouvements] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- Comparaison Prix Achat vs Prix Vente ---
    {
        "code": "DS_ACHATS_VS_VENTES",
        "nom": "Comparaison Prix Achat vs Vente",
        "category": "Achats",
        "description": "Marge brute par article : prix d'achat moyen vs prix de vente moyen",
        "query_template": """
            WITH PrixAchat AS (
                SELECT
                    [Code article],
                    [societe],
                    AVG([Prix unitaire]) AS [Prix Achat Moy],
                    SUM([Quantité]) AS [Qte Achetee],
                    SUM([Montant HT Net]) AS [Total Achats HT]
                FROM [Lignes_des_achats]
                WHERE [Type Document] IN ('Facture', 'Facture comptabilisée')
                  AND [Valorise CA] = 'Oui'
                  AND (@societe IS NULL OR [societe] = @societe)
                  AND [Date BL] BETWEEN @dateDebut AND @dateFin
                GROUP BY [Code article], [societe]
            ),
            PrixVente AS (
                SELECT
                    [Code article],
                    [societe],
                    AVG([Prix unitaire]) AS [Prix Vente Moy],
                    SUM([Quantité]) AS [Qte Vendue],
                    SUM([Montant HT Net]) AS [Total Ventes HT]
                FROM [Lignes_des_ventes]
                WHERE [Valorise CA] = 'Oui'
                  AND (@societe IS NULL OR [societe] = @societe)
                  AND [Date BL] BETWEEN @dateDebut AND @dateFin
                GROUP BY [Code article], [societe]
            )
            SELECT
                ISNULL(a.[Code article], v.[Code article]) AS [Code Article],
                ISNULL(a.[societe], v.[societe]) AS [Société],
                ISNULL(a.[Prix Achat Moy], 0) AS [Prix Achat Moy],
                ISNULL(v.[Prix Vente Moy], 0) AS [Prix Vente Moy],
                ISNULL(v.[Prix Vente Moy], 0) - ISNULL(a.[Prix Achat Moy], 0) AS [Ecart],
                CASE WHEN ISNULL(v.[Prix Vente Moy], 0) > 0
                    THEN ROUND((ISNULL(v.[Prix Vente Moy], 0) - ISNULL(a.[Prix Achat Moy], 0)) * 100.0 / v.[Prix Vente Moy], 2)
                    ELSE 0 END AS [Marge Brute %],
                ISNULL(a.[Qte Achetee], 0) AS [Qte Achetee],
                ISNULL(v.[Qte Vendue], 0) AS [Qte Vendue],
                ISNULL(a.[Total Achats HT], 0) AS [Total Achats HT],
                ISNULL(v.[Total Ventes HT], 0) AS [Total Ventes HT]
            FROM PrixAchat a
            FULL OUTER JOIN PrixVente v ON a.[Code article] = v.[Code article] AND a.[societe] = v.[societe]
            ORDER BY [Marge Brute %] ASC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- Historique Prix Fournisseur ---
    {
        "code": "DS_HISTORIQUE_PRIX_FOURNISSEUR",
        "nom": "Historique Prix Fournisseur",
        "category": "Achats",
        "description": "Evolution du prix unitaire d'achat par article et fournisseur sur 12-24 mois",
        "query_template": """
            SELECT
                FORMAT([Date BL], 'yyyy-MM') AS [Periode],
                [Code fournisseur] AS [Code Fournisseur],
                [Intitulé fournisseur] AS [Fournisseur],
                [Code article] AS [Code Article],
                [Désignation ligne] AS [Article],
                [societe] AS [Société],
                AVG([Prix unitaire]) AS [Prix Moyen],
                MIN([Prix unitaire]) AS [Prix Min],
                MAX([Prix unitaire]) AS [Prix Max],
                SUM([Quantité]) AS [Qte],
                SUM([Montant HT Net]) AS [Montant HT]
            FROM [Lignes_des_achats]
            WHERE [Type Document] IN ('Facture', 'Facture comptabilisée')
              AND [Valorise CA] = 'Oui'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date BL] BETWEEN @dateDebut AND @dateFin
            GROUP BY FORMAT([Date BL], 'yyyy-MM'), [Code fournisseur], [Intitulé fournisseur],
                     [Code article], [Désignation ligne], [societe]
            ORDER BY [Code Article], [Periode]
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- Prevision Encaissements ---
    {
        "code": "DS_PREVISION_ENCAISSEMENTS",
        "nom": "Prevision Encaissements",
        "category": "Recouvrement",
        "description": "Echeances a venir par semaine/mois — projection de tresorerie",
        "query_template": """
            SELECT
                FORMAT([Date d'échéance], 'yyyy-MM') AS [Periode],
                DATEPART(WEEK, [Date d'échéance]) AS [Semaine],
                [societe] AS [Société],
                COUNT(*) AS [Nb Echeances],
                COUNT(DISTINCT [Code client]) AS [Nb Clients],
                SUM([Montant échéance]) AS [Montant Total],
                SUM(ISNULL([Montant du règlement], 0)) AS [Deja Regle],
                SUM([Montant échéance] - ISNULL([Montant du règlement], 0)) AS [Reste a Encaisser],
                SUM(CASE WHEN [Date d'échéance] < GETDATE()
                    THEN [Montant échéance] - ISNULL([Montant du règlement], 0) ELSE 0 END) AS [Retard],
                SUM(CASE WHEN [Date d'échéance] >= GETDATE()
                    THEN [Montant échéance] - ISNULL([Montant du règlement], 0) ELSE 0 END) AS [A Venir]
            FROM [Echéances_Ventes]
            WHERE [Montant échéance] > ISNULL([Montant du règlement], 0)
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date d'échéance] BETWEEN DATEADD(MONTH, -3, GETDATE()) AND DATEADD(MONTH, 6, GETDATE())
            GROUP BY FORMAT([Date d'échéance], 'yyyy-MM'), DATEPART(WEEK, [Date d'échéance]), [societe]
            ORDER BY [Periode], [Semaine]
        """,
        "parameters": '[{"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- Comportement de Paiement Client ---
    {
        "code": "DS_COMPORTEMENT_PAIEMENT",
        "nom": "Comportement de Paiement",
        "category": "Recouvrement",
        "description": "Delai moyen de paiement par client sur 12 mois — tendance amelioration/degradation",
        "query_template": """
            WITH Paiements AS (
                SELECT
                    e.[Code client],
                    e.[Intitulé client],
                    e.[societe],
                    FORMAT(e.[Date document], 'yyyy-MM') AS [Periode],
                    AVG(DATEDIFF(DAY, e.[Date d'échéance],
                        ISNULL(i.[Date règlement], GETDATE()))) AS [Delai Moyen],
                    COUNT(*) AS [Nb Echeances],
                    SUM(e.[Montant échéance]) AS [Montant Total]
                FROM [Echéances_Ventes] e
                LEFT JOIN [Imputation_Factures_Ventes] i
                    ON e.[societe] = i.[societe]
                    AND e.[Type Document] = i.[Type Document]
                    AND e.[N° Pièce] = i.[N° pièce]
                WHERE (@societe IS NULL OR e.[societe] = @societe)
                  AND e.[Date document] >= DATEADD(MONTH, -12, GETDATE())
                GROUP BY e.[Code client], e.[Intitulé client], e.[societe],
                         FORMAT(e.[Date document], 'yyyy-MM')
            )
            SELECT
                [Code client] AS [Code Client],
                [Intitulé client] AS [Client],
                [societe] AS [Société],
                [Periode],
                [Delai Moyen] AS [Delai Moyen Jours],
                [Nb Echeances],
                [Montant Total],
                CASE
                    WHEN [Delai Moyen] <= 0 THEN 'Anticipe'
                    WHEN [Delai Moyen] <= 15 THEN 'Bon payeur'
                    WHEN [Delai Moyen] <= 30 THEN 'Normal'
                    WHEN [Delai Moyen] <= 60 THEN 'Lent'
                    ELSE 'Mauvais payeur'
                END AS [Profil Paiement]
            FROM Paiements
            ORDER BY [Code Client], [Periode]
        """,
        "parameters": '[{"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- CA par Gamme et Mois (pour pivot) ---
    {
        "code": "DS_VENTES_GAMME_MOIS",
        "nom": "CA par Gamme et Mois",
        "category": "Ventes",
        "description": "CA et marge par gamme avec ventilation mensuelle pour pivot",
        "query_template": """
            SELECT
                ISNULL(NULLIF([Gamme 1], ''), '(Non classé)') AS [Gamme],
                FORMAT([Date BL], 'yyyy-MM') AS [Periode],
                [societe] AS [Société],
                SUM([Montant HT Net]) AS [CA HT],
                SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) AS [Marge],
                SUM([Quantité]) AS [Qte Vendue],
                COUNT(DISTINCT [Code client]) AS [Nb Clients]
            FROM [Lignes_des_ventes]
            WHERE [Valorise CA] = 'Oui'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date BL] BETWEEN @dateDebut AND @dateFin
            GROUP BY ISNULL(NULLIF([Gamme 1], ''), '(Non classé)'), FORMAT([Date BL], 'yyyy-MM'), [societe]
            ORDER BY [Gamme], [Periode]
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # --- CA par Famille et Mois ---
    {
        "code": "DS_VENTES_FAMILLE_MOIS",
        "nom": "CA par Famille et Mois",
        "category": "Ventes",
        "description": "CA par famille d'articles avec ventilation mensuelle",
        "query_template": """
            SELECT
                ISNULL(NULLIF(a.[Intitulé famille], ''), '(Non classé)') AS [Famille],
                FORMAT(l.[Date BL], 'yyyy-MM') AS [Periode],
                l.[societe] AS [Société],
                SUM(l.[Montant HT Net]) AS [CA HT],
                SUM(l.[Montant HT Net] - ISNULL(l.[CMUP], 0) * l.[Quantité]) AS [Marge],
                SUM(l.[Quantité]) AS [Qte Vendue],
                COUNT(DISTINCT l.[Code article]) AS [Nb Articles]
            FROM [Lignes_des_ventes] l
            LEFT JOIN [Articles] a ON l.[Code article] = a.[Code Article] AND l.[societe] = a.[societe]
            WHERE l.[Valorise CA] = 'Oui'
              AND (@societe IS NULL OR l.[societe] = @societe)
              AND l.[Date BL] BETWEEN @dateDebut AND @dateFin
            GROUP BY ISNULL(NULLIF(a.[Intitulé famille], ''), '(Non classé)'), FORMAT(l.[Date BL], 'yyyy-MM'), l.[societe]
            ORDER BY [Famille], [Periode]
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
]


def init_templates():
    """Initialise les templates de DataSources dans la base centrale"""
    print("=" * 60)
    print("Initialisation des Templates de DataSources")
    print("=" * 60)

    # Verifier si la table existe
    try:
        existing = execute_central_query(
            "SELECT COUNT(*) as cnt FROM APP_DataSources_Templates",
            use_cache=False
        )
        print(f"Templates existants: {existing[0]['cnt']}")
    except Exception as e:
        print(f"Erreur: La table APP_DataSources_Templates n'existe pas")
        print(f"Executez d'abord le script SQL 001_optiboard_web_central.sql")
        return False

    created = 0
    updated = 0

    for ds in DATASOURCE_TEMPLATES:
        try:
            # Verifier si existe
            existing = execute_central_query(
                "SELECT id FROM APP_DataSources_Templates WHERE code = ?",
                (ds["code"],),
                use_cache=False
            )

            if existing:
                # Mettre a jour
                execute_central_write("""
                    UPDATE APP_DataSources_Templates
                    SET nom = ?, category = ?, description = ?,
                        query_template = ?, parameters = ?
                    WHERE code = ?
                """, (
                    ds["nom"],
                    ds["category"],
                    ds["description"],
                    ds["query_template"].strip(),
                    ds["parameters"],
                    ds["code"]
                ))
                updated += 1
                print(f"  [UPDATE] {ds['code']}")
            else:
                # Creer
                execute_central_write("""
                    INSERT INTO APP_DataSources_Templates
                    (code, nom, type, category, description, query_template, parameters, is_system, actif)
                    VALUES (?, ?, 'query', ?, ?, ?, ?, 1, 1)
                """, (
                    ds["code"],
                    ds["nom"],
                    ds["category"],
                    ds["description"],
                    ds["query_template"].strip(),
                    ds["parameters"]
                ))
                created += 1
                print(f"  [CREATE] {ds['code']}")

        except Exception as e:
            print(f"  [ERROR] {ds['code']}: {e}")

    print("-" * 60)
    print(f"Termine: {created} crees, {updated} mis a jour")
    print("=" * 60)

    return True


def list_templates():
    """Affiche la liste des templates existants"""
    print("\n" + "=" * 60)
    print("Templates de DataSources existants")
    print("=" * 60)

    try:
        templates = execute_central_query("""
            SELECT code, nom, category, is_system, actif
            FROM APP_DataSources_Templates
            ORDER BY category, nom
        """, use_cache=False)

        current_cat = None
        for t in templates:
            if t["category"] != current_cat:
                current_cat = t["category"]
                print(f"\n[{current_cat.upper()}]")

            status = "systeme" if t["is_system"] else "custom"
            active = "actif" if t["actif"] else "inactif"
            print(f"  - {t['code']}: {t['nom']} ({status}, {active})")

        print(f"\nTotal: {len(templates)} templates")

    except Exception as e:
        print(f"Erreur: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Gestion des templates de DataSources")
    parser.add_argument("--list", action="store_true", help="Lister les templates existants")
    parser.add_argument("--init", action="store_true", help="Initialiser/mettre a jour les templates")

    args = parser.parse_args()

    if args.list:
        list_templates()
    elif args.init:
        init_templates()
    else:
        print("Usage:")
        print("  python init_datasource_templates.py --init   # Initialiser les templates")
        print("  python init_datasource_templates.py --list   # Lister les templates")
