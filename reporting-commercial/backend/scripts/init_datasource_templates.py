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
                [societe] AS [Societe],
                SUM([Montant HT Net]) AS [CA HT],
                SUM([Montant TTC Net]) AS [CA TTC],
                SUM([Montant HT Net] - [Prix de revient] * [Quantité]) AS [Marge],
                CASE WHEN SUM([Montant HT Net]) > 0
                    THEN ROUND(SUM([Montant HT Net] - [Prix de revient] * [Quantité]) * 100.0 / SUM([Montant HT Net]), 2)
                    ELSE 0 END AS [Taux Marge %],
                COUNT(DISTINCT [Code client]) AS [Nb Clients],
                COUNT(DISTINCT [N° Pièce]) AS [Nb Documents],
                SUM([Quantité]) AS [Qte Totale],
                COUNT(*) AS [Nb Lignes]
            FROM [Lignes_des_ventes]
            WHERE [Valorise CA] = 'Oui'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
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
                YEAR([Date]) AS [Annee],
                MONTH([Date]) AS [Mois],
                FORMAT([Date], 'yyyy-MM') AS [Periode],
                [societe] AS [Societe],
                SUM([Montant HT Net]) AS [CA HT],
                SUM([Montant TTC Net]) AS [CA TTC],
                SUM([Montant HT Net] - [Prix de revient] * [Quantité]) AS [Marge],
                CASE WHEN SUM([Montant HT Net]) > 0
                    THEN ROUND(SUM([Montant HT Net] - [Prix de revient] * [Quantité]) * 100.0 / SUM([Montant HT Net]), 2)
                    ELSE 0 END AS [Taux Marge %],
                COUNT(DISTINCT [Code client]) AS [Nb Clients],
                SUM([Quantité]) AS [Qte Totale]
            FROM [Lignes_des_ventes]
            WHERE [Valorise CA] = 'Oui'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
            GROUP BY YEAR([Date]), MONTH([Date]), FORMAT([Date], 'yyyy-MM'), [societe]
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
                [societe] AS [Societe],
                SUM([Montant HT Net]) AS [CA HT],
                SUM([Montant TTC Net]) AS [CA TTC],
                SUM([Montant HT Net] - [Prix de revient] * [Quantité]) AS [Marge],
                CASE WHEN SUM([Montant HT Net]) > 0
                    THEN ROUND(SUM([Montant HT Net] - [Prix de revient] * [Quantité]) * 100.0 / SUM([Montant HT Net]), 2)
                    ELSE 0 END AS [Taux Marge %],
                COUNT(DISTINCT [N° Pièce]) AS [Nb Factures],
                SUM([Quantité]) AS [Qte Totale],
                MIN([Date]) AS [Premiere Vente],
                MAX([Date]) AS [Derniere Vente]
            FROM [Lignes_des_ventes]
            WHERE [Valorise CA] = 'Oui'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
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
                SUM([Montant HT Net] - [Prix de revient] * [Quantité]) AS [Marge],
                CASE WHEN SUM([Montant HT Net]) > 0
                    THEN ROUND(SUM([Montant HT Net] - [Prix de revient] * [Quantité]) * 100.0 / SUM([Montant HT Net]), 2)
                    ELSE 0 END AS [Taux Marge %],
                CASE WHEN SUM([Quantité]) > 0
                    THEN ROUND(SUM([Montant HT Net]) / SUM([Quantité]), 2)
                    ELSE 0 END AS [Prix Moyen],
                AVG([Prix de revient]) AS [Cout Moyen],
                COUNT(DISTINCT [Code client]) AS [Nb Clients]
            FROM [Lignes_des_ventes]
            WHERE [Valorise CA] = 'Oui'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
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
                [Catalogue 1] AS [Catalogue],
                [Catalogue 2] AS [Sous Catalogue],
                COUNT(DISTINCT [Code article]) AS [Nb Articles],
                SUM([Quantité]) AS [Qte Vendue],
                SUM([Montant HT Net]) AS [CA HT],
                SUM([Montant HT Net] - [Prix de revient] * [Quantité]) AS [Marge],
                CASE WHEN SUM([Montant HT Net]) > 0
                    THEN ROUND(SUM([Montant HT Net] - [Prix de revient] * [Quantité]) * 100.0 / SUM([Montant HT Net]), 2)
                    ELSE 0 END AS [Taux Marge %],
                COUNT(DISTINCT [Code client]) AS [Nb Clients]
            FROM [Lignes_des_ventes]
            WHERE [Valorise CA] = 'Oui'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date] BETWEEN @dateDebut AND @dateFin
              AND [Catalogue 1] IS NOT NULL
            GROUP BY [Catalogue 1], [Catalogue 2]
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
                [societe] AS [Societe],
                SUM([Montant HT Net]) AS [CA HT],
                SUM([Montant HT Net] - [Prix de revient] * [Quantité]) AS [Marge],
                SUM([Quantité]) AS [Qte Vendue],
                COUNT(DISTINCT [Code article]) AS [Nb Articles],
                COUNT(DISTINCT [Code client]) AS [Nb Clients],
                COUNT(DISTINCT [N° Pièce]) AS [Nb Documents]
            FROM [Lignes_des_ventes]
            WHERE [Valorise CA] = 'Oui'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
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
                [societe] AS [Societe],
                COUNT(DISTINCT [N° Pièce]) AS [Nb Documents],
                COUNT(*) AS [Nb Lignes],
                SUM([Quantité]) AS [Qte Totale],
                SUM([Montant HT Net]) AS [Montant HT],
                SUM([Montant TTC Net]) AS [Montant TTC],
                COUNT(DISTINCT [Code client]) AS [Nb Clients],
                COUNT(DISTINCT [Code article]) AS [Nb Articles]
            FROM [Lignes_des_ventes]
            WHERE [Date] BETWEEN @dateDebut AND @dateFin
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
                [societe] AS [Societe],
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
                [Prix de revient] AS [Cout],
                [Montant HT Net] - [Prix de revient] * [Quantité] AS [Marge],
                [Référence] AS [Reference Client],
                [Code d'affaire] AS [Code Affaire],
                [Intitulé affaire] AS [Affaire]
            FROM [Lignes_des_ventes]
            WHERE [Type Document] IN ('Facture', 'Facture comptabilisée')
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
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
                [societe] AS [Societe],
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
              AND [Date] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
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
                [societe] AS [Societe],
                [N° Pièce] AS [Num BC],
                [Date BC],
                [Code client] AS [Code Client],
                [Intitulé client] AS [Client],
                [Code article] AS [Code Article],
                [Désignation ligne] AS [Designation],
                [Quantité BC] AS [Qte Commandee],
                [Quantité BL] AS [Qte Livree],
                [Quantité BC] - ISNULL([Quantité BL], 0) AS [Reste A Livrer],
                [Prix unitaire] AS [PU HT],
                [Montant HT Net] AS [Montant HT],
                [Date Livraison] AS [Date Livraison Prevue],
                [Référence] AS [Reference Client],
                [Code d'affaire] AS [Code Affaire]
            FROM [Lignes_des_ventes]
            WHERE [Type Document] = 'Bon de commande'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
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
                [societe] AS [Societe],
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
              AND [Date] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
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
                [societe] AS [Societe],
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
              AND [Date] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
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
                [societe] AS [Societe],
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
              AND [Date] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
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
                [societe] AS [Societe],
                [Type Document],
                [N° Pièce] AS [Num Piece],
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
                [Prix de revient] AS [Cout],
                [CMUP],
                [Coût standard],
                [Montant HT Net] - [Prix de revient] * [Quantité] AS [Marge],
                [Code dépôt] AS [Code Depot],
                [Intitulé dépôt] AS [Depot],
                [N° Série/Lot] AS [Num Serie Lot],
                [Poids net], [Poids brut], [Colisage],
                [Code d'affaire] AS [Code Affaire],
                [Intitulé affaire] AS [Affaire],
                [Référence] AS [Reference Client],
                [Valorise CA]
            FROM [Lignes_des_ventes]
            WHERE [Date] BETWEEN @dateDebut AND @dateFin
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
                [societe] AS [Societe],
                SUM([Montant HT Net]) AS [CA HT],
                SUM([Montant HT Net] - [Prix de revient] * [Quantité]) AS [Marge],
                CASE WHEN SUM([Montant HT Net]) > 0
                    THEN ROUND(SUM([Montant HT Net] - [Prix de revient] * [Quantité]) * 100.0 / SUM([Montant HT Net]), 2)
                    ELSE 0 END AS [Taux Marge %],
                COUNT(DISTINCT [N° Pièce]) AS [Nb Documents],
                MIN([Date]) AS [Date Debut],
                MAX([Date]) AS [Date Fin]
            FROM [Lignes_des_ventes]
            WHERE [Valorise CA] = 'Oui'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Code d'affaire] IS NOT NULL
              AND [Code d'affaire] <> ''
              AND [Date] BETWEEN @dateDebut AND @dateFin
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
                [societe] AS [Societe],
                [N° Pièce] AS [Num BC],
                [Date BC],
                [Code client] AS [Code Client],
                [Intitulé client] AS [Client],
                [Code article] AS [Code Article],
                [Désignation ligne] AS [Designation],
                [Quantité BC] AS [Qte Commandee],
                ISNULL([Quantité BL], 0) AS [Qte Livree],
                [Quantité BC] - ISNULL([Quantité BL], 0) AS [Reste A Livrer],
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
                SUM([Montant HT Net] - [Prix de revient] * [Quantité]) AS [Marge],
                CASE WHEN SUM([Montant HT Net]) > 0
                    THEN ROUND(SUM([Montant HT Net] - [Prix de revient] * [Quantité]) * 100.0 / SUM([Montant HT Net]), 2)
                    ELSE 0 END AS [Taux Marge %],
                COUNT(DISTINCT [Code client]) AS [Nb Clients],
                COUNT(DISTINCT [N° Pièce]) AS [Nb Ventes]
            FROM [Lignes_des_ventes]
            WHERE [Valorise CA] = 'Oui'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
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
                [societe] AS [Societe],
                SUM([Montant HT Net]) AS [CA HT],
                SUM([Montant HT Net] - [Prix de revient] * [Quantité]) AS [Marge],
                CASE WHEN SUM([Montant HT Net]) > 0
                    THEN ROUND(SUM([Montant HT Net] - [Prix de revient] * [Quantité]) * 100.0 / SUM([Montant HT Net]), 2)
                    ELSE 0 END AS [Taux Marge %],
                COUNT(DISTINCT [N° Pièce]) AS [Nb Factures],
                COUNT(DISTINCT [Code article]) AS [Nb Articles],
                MIN([Date]) AS [Premiere Vente],
                MAX([Date]) AS [Derniere Vente]
            FROM [Lignes_des_ventes]
            WHERE [Valorise CA] = 'Oui'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
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
                e.[Code commercial] AS [Code Commercial],
                e.[Nom commercial] AS [Commercial],
                l.[societe] AS [Societe],
                COUNT(DISTINCT l.[Code client]) AS [Nb Clients],
                COUNT(DISTINCT l.[N° Pièce]) AS [Nb Factures],
                SUM(l.[Montant HT Net]) AS [CA HT],
                SUM(l.[Montant HT Net] - l.[Prix de revient] * l.[Quantité]) AS [Marge],
                CASE WHEN SUM(l.[Montant HT Net]) > 0
                    THEN ROUND(SUM(l.[Montant HT Net] - l.[Prix de revient] * l.[Quantité]) * 100.0 / SUM(l.[Montant HT Net]), 2)
                    ELSE 0 END AS [Taux Marge %]
            FROM [Lignes_des_ventes] l
            INNER JOIN [Entête_des_ventes] e
                ON l.[DB] = e.[DB_Id]
                AND l.[Type Document] = e.[Type Document]
                AND l.[N° Pièce] = e.[N° pièce]
            WHERE l.[Valorise CA] = 'Oui'
              AND (@societe IS NULL OR l.[societe] = @societe)
              AND l.[Date] BETWEEN @dateDebut AND @dateFin
            GROUP BY e.[Code commercial], e.[Nom commercial], l.[societe]
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
                c.[Zone géographique] AS [Zone],
                c.[Canal de vente] AS [Canal],
                l.[societe] AS [Societe],
                COUNT(DISTINCT l.[Code client]) AS [Nb Clients],
                SUM(l.[Montant HT Net]) AS [CA HT],
                SUM(l.[Montant HT Net] - l.[Prix de revient] * l.[Quantité]) AS [Marge],
                CASE WHEN SUM(l.[Montant HT Net]) > 0
                    THEN ROUND(SUM(l.[Montant HT Net] - l.[Prix de revient] * l.[Quantité]) * 100.0 / SUM(l.[Montant HT Net]), 2)
                    ELSE 0 END AS [Taux Marge %]
            FROM [Lignes_des_ventes] l
            INNER JOIN [Clients] c
                ON l.[DB] = c.[DB_Id]
                AND l.[Code client] = c.[Code client]
            WHERE l.[Valorise CA] = 'Oui'
              AND (@societe IS NULL OR l.[societe] = @societe)
              AND l.[Date] BETWEEN @dateDebut AND @dateFin
              AND c.[Zone géographique] IS NOT NULL
            GROUP BY c.[Zone géographique], c.[Canal de vente], l.[societe]
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
                l.[Désignation Article] AS [Désignation Ligne],
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
                l.[Prix de revient],
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
                -- Marge calculée avec Prix de revient
                l.[Montant HT Net] - l.Quantité * ISNULL(l.[Prix de revient], 0) AS [Marge PR],
                -- Marge calculée avec CMUP
                l.[Montant HT Net] - l.Quantité * ISNULL(l.CMUP, 0) AS [Marge CMUP],
                -- Marge calculée avec DPA-Vente
                l.[Montant HT Net] - l.Quantité * ISNULL(ms.[DPA-Vente], 0) AS [Marge DPA-Vente],
                -- Marge calculée avec DPA-Période
                l.[Montant HT Net] - l.Quantité * ISNULL(ms.[DPA-Période], 0) AS [Marge DPA-Période],
                -- Marge calculée avec DPR-Vente
                l.[Montant HT Net] - l.Quantité * ISNULL(ms.[DPR-Vente], 0) AS [Marge DPR-Vente],
                -- Coût marchandise Prix de revient
                l.Quantité * ISNULL(l.[Prix de revient], 0) AS [Coût PR],
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
            WHERE e.Date BETWEEN @dateDebut AND @dateFin
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
        "description": "CA et marge avec choix de valorisation (CMUP, Prix de revient, DPA-Vente, DPA-Période, DPR-Vente) et valorisation CA (HT/TTC)",
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
                l.[Prix de revient],
                ISNULL(ms.[DPA-Période], 0) AS [DPA-Période],
                ISNULL(ms.[DPA-Vente], 0) AS [DPA-Vente],
                ISNULL(ms.[DPR-Vente], 0) AS [DPR-Vente],
                -- Marge dynamique selon valorisation choisie
                (CASE WHEN @ValorisationCA = 'TTC' THEN l.[Montant TTC Net] ELSE l.[Montant HT Net] END) -
                l.Quantité * ISNULL(
                    CASE @Valorisation
                        WHEN 'CMUP' THEN l.CMUP
                        WHEN 'Prix de revient' THEN l.[Prix de revient]
                        WHEN 'DPA-Vente' THEN ms.[DPA-Vente]
                        WHEN 'DPA-Période' THEN ms.[DPA-Période]
                        WHEN 'DPR-Vente' THEN ms.[DPR-Vente]
                        ELSE 0
                    END, 0) AS [Marge],
                -- Coût marchandise dynamique
                ISNULL(
                    CASE @Valorisation
                        WHEN 'CMUP' THEN l.CMUP
                        WHEN 'Prix de revient' THEN l.[Prix de revient]
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
            WHERE e.Date BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR e.societe = @societe)
              AND l.[Valorise CA] = 'Oui'
            ORDER BY e.Date DESC, e.[N° pièce]
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global", "required": true, "label": "Date début"}, {"name": "dateFin", "type": "date", "source": "global", "required": true, "label": "Date fin"}, {"name": "societe", "type": "string", "source": "global", "required": false, "label": "Société"}, {"name": "Valorisation", "type": "select", "source": "fixed", "required": true, "label": "Méthode de valorisation", "default": "Prix de revient", "options": ["CMUP", "Prix de revient", "DPA-Vente", "DPA-Période", "DPR-Vente"]}, {"name": "ValorisationCA", "type": "select", "source": "fixed", "required": true, "label": "Valorisation CA", "default": "HT", "options": ["HT", "TTC"]}]'
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
                            WHEN 'Prix de revient' THEN l.[Prix de revient]
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
                                    WHEN 'Prix de revient' THEN l.[Prix de revient]
                                    WHEN 'DPA-Vente' THEN ms.[DPA-Vente]
                                    WHEN 'DPA-Période' THEN ms.[DPA-Période]
                                    WHEN 'DPR-Vente' THEN ms.[DPR-Vente]
                                    ELSE 0
                                END, 0)
                        ) * 100.0 / SUM(CASE WHEN @ValorisationCA = 'TTC' THEN l.[Montant TTC Net] ELSE l.[Montant HT Net] END), 2)
                    ELSE 0 END AS [Taux Marge %],
                SUM(
                    ISNULL(
                        CASE @Valorisation
                            WHEN 'CMUP' THEN l.CMUP
                            WHEN 'Prix de revient' THEN l.[Prix de revient]
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
            WHERE e.Date BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR e.societe = @societe)
              AND l.[Valorise CA] = 'Oui'
            GROUP BY e.societe, e.[Code client], e.[Intitulé client], c.Ville, c.Région, c.[Catégorie tarifaire]
            ORDER BY [CA] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global", "required": true, "label": "Date début"}, {"name": "dateFin", "type": "date", "source": "global", "required": true, "label": "Date fin"}, {"name": "societe", "type": "string", "source": "global", "required": false, "label": "Société"}, {"name": "Valorisation", "type": "select", "source": "fixed", "required": true, "label": "Méthode de valorisation", "default": "Prix de revient", "options": ["CMUP", "Prix de revient", "DPA-Vente", "DPA-Période", "DPR-Vente"]}, {"name": "ValorisationCA", "type": "select", "source": "fixed", "required": true, "label": "Valorisation CA", "default": "HT", "options": ["HT", "TTC"]}]'
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
                            WHEN 'Prix de revient' THEN l.[Prix de revient]
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
                                    WHEN 'Prix de revient' THEN l.[Prix de revient]
                                    WHEN 'DPA-Vente' THEN ms.[DPA-Vente]
                                    WHEN 'DPA-Période' THEN ms.[DPA-Période]
                                    WHEN 'DPR-Vente' THEN ms.[DPR-Vente]
                                    ELSE 0
                                END, 0)
                        ) * 100.0 / SUM(CASE WHEN @ValorisationCA = 'TTC' THEN l.[Montant TTC Net] ELSE l.[Montant HT Net] END), 2)
                    ELSE 0 END AS [Taux Marge %],
                AVG(l.[Prix unitaire]) AS [Prix Moyen Vente],
                AVG(
                    CASE @Valorisation
                        WHEN 'CMUP' THEN l.CMUP
                        WHEN 'Prix de revient' THEN l.[Prix de revient]
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
            WHERE e.Date BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR e.societe = @societe)
              AND l.[Valorise CA] = 'Oui'
            GROUP BY e.societe, l.[Code article], a.[Désignation Article], a.[Code Famille], a.[Intitulé famille], a.[Catalogue 1], a.[Catalogue 2]
            ORDER BY [CA] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global", "required": true, "label": "Date début"}, {"name": "dateFin", "type": "date", "source": "global", "required": true, "label": "Date fin"}, {"name": "societe", "type": "string", "source": "global", "required": false, "label": "Société"}, {"name": "Valorisation", "type": "select", "source": "fixed", "required": true, "label": "Méthode de valorisation", "default": "Prix de revient", "options": ["CMUP", "Prix de revient", "DPA-Vente", "DPA-Période", "DPR-Vente"]}, {"name": "ValorisationCA", "type": "select", "source": "fixed", "required": true, "label": "Valorisation CA", "default": "HT", "options": ["HT", "TTC"]}]'
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
                            WHEN 'Prix de revient' THEN l.[Prix de revient]
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
                                    WHEN 'Prix de revient' THEN l.[Prix de revient]
                                    WHEN 'DPA-Vente' THEN ms.[DPA-Vente]
                                    WHEN 'DPA-Période' THEN ms.[DPA-Période]
                                    WHEN 'DPR-Vente' THEN ms.[DPR-Vente]
                                    ELSE 0
                                END, 0)
                        ) * 100.0 / SUM(CASE WHEN @ValorisationCA = 'TTC' THEN l.[Montant TTC Net] ELSE l.[Montant HT Net] END), 2)
                    ELSE 0 END AS [Taux Marge %]
            FROM Entête_des_ventes AS e
            INNER JOIN Clients AS c
                ON e.[Code client] = c.[Code client] AND e.societe = c.societe
            INNER JOIN Lignes_des_ventes AS l
                ON e.societe = l.societe AND e.[Type Document] = l.[Type Document] AND e.[N° pièce] = l.[N° Pièce]
            INNER JOIN Articles AS a
                ON l.societe = a.societe AND l.[Code article] = a.[Code Article]
            LEFT JOIN Mouvement_stock AS ms
                ON l.societe = ms.societe AND l.[N° interne] = ms.[N° interne]
            WHERE e.Date BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR e.societe = @societe)
              AND l.[Valorise CA] = 'Oui'
            GROUP BY e.societe, a.[Catalogue 1], a.[Catalogue 2], a.[Code Famille], a.[Intitulé famille]
            ORDER BY [CA] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global", "required": true, "label": "Date début"}, {"name": "dateFin", "type": "date", "source": "global", "required": true, "label": "Date fin"}, {"name": "societe", "type": "string", "source": "global", "required": false, "label": "Société"}, {"name": "Valorisation", "type": "select", "source": "fixed", "required": true, "label": "Méthode de valorisation", "default": "Prix de revient", "options": ["CMUP", "Prix de revient", "DPA-Vente", "DPA-Période", "DPR-Vente"]}, {"name": "ValorisationCA", "type": "select", "source": "fixed", "required": true, "label": "Valorisation CA", "default": "HT", "options": ["HT", "TTC"]}]'
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
                            WHEN 'Prix de revient' THEN l.[Prix de revient]
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
                                    WHEN 'Prix de revient' THEN l.[Prix de revient]
                                    WHEN 'DPA-Vente' THEN ms.[DPA-Vente]
                                    WHEN 'DPA-Période' THEN ms.[DPA-Période]
                                    WHEN 'DPR-Vente' THEN ms.[DPR-Vente]
                                    ELSE 0
                                END, 0)
                        ) * 100.0 / SUM(CASE WHEN @ValorisationCA = 'TTC' THEN l.[Montant TTC Net] ELSE l.[Montant HT Net] END), 2)
                    ELSE 0 END AS [Taux Marge %]
            FROM Entête_des_ventes AS e
            INNER JOIN Clients AS c
                ON e.[Code client] = c.[Code client] AND e.societe = c.societe
            INNER JOIN Lignes_des_ventes AS l
                ON e.societe = l.societe AND e.[Type Document] = l.[Type Document] AND e.[N° pièce] = l.[N° Pièce]
            INNER JOIN Articles AS a
                ON l.societe = a.societe AND l.[Code article] = a.[Code Article]
            LEFT JOIN Mouvement_stock AS ms
                ON l.societe = ms.societe AND l.[N° interne] = ms.[N° interne]
            WHERE e.Date BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR e.societe = @societe)
              AND l.[Valorise CA] = 'Oui'
            GROUP BY e.societe, e.[Nom représentant]
            ORDER BY [CA] DESC
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global", "required": true, "label": "Date début"}, {"name": "dateFin", "type": "date", "source": "global", "required": true, "label": "Date fin"}, {"name": "societe", "type": "string", "source": "global", "required": false, "label": "Société"}, {"name": "Valorisation", "type": "select", "source": "fixed", "required": true, "label": "Méthode de valorisation", "default": "Prix de revient", "options": ["CMUP", "Prix de revient", "DPA-Vente", "DPA-Période", "DPR-Vente"]}, {"name": "ValorisationCA", "type": "select", "source": "fixed", "required": true, "label": "Valorisation CA", "default": "HT", "options": ["HT", "TTC"]}]'
    },
    {
        "code": "DS_CA_PAR_MOIS_DYNAMIQUE",
        "nom": "CA Mensuel avec Marge Dynamique",
        "category": "Ventes",
        "description": "Evolution mensuelle du CA et marge avec choix de valorisation",
        "query_template": """
            SELECT
                e.societe AS [Société],
                YEAR(e.Date) AS [Année],
                MONTH(e.Date) AS [Mois],
                FORMAT(e.Date, 'yyyy-MM') AS [Période],
                COUNT(DISTINCT e.[Code client]) AS [Nb Clients],
                COUNT(DISTINCT e.[N° pièce]) AS [Nb Documents],
                SUM(l.Quantité) AS [Qte Vendue],
                SUM(CASE WHEN @ValorisationCA = 'TTC' THEN l.[Montant TTC Net] ELSE l.[Montant HT Net] END) AS [CA],
                SUM(
                    (CASE WHEN @ValorisationCA = 'TTC' THEN l.[Montant TTC Net] ELSE l.[Montant HT Net] END) -
                    l.Quantité * ISNULL(
                        CASE @Valorisation
                            WHEN 'CMUP' THEN l.CMUP
                            WHEN 'Prix de revient' THEN l.[Prix de revient]
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
                                    WHEN 'Prix de revient' THEN l.[Prix de revient]
                                    WHEN 'DPA-Vente' THEN ms.[DPA-Vente]
                                    WHEN 'DPA-Période' THEN ms.[DPA-Période]
                                    WHEN 'DPR-Vente' THEN ms.[DPR-Vente]
                                    ELSE 0
                                END, 0)
                        ) * 100.0 / SUM(CASE WHEN @ValorisationCA = 'TTC' THEN l.[Montant TTC Net] ELSE l.[Montant HT Net] END), 2)
                    ELSE 0 END AS [Taux Marge %]
            FROM Entête_des_ventes AS e
            INNER JOIN Clients AS c
                ON e.[Code client] = c.[Code client] AND e.societe = c.societe
            INNER JOIN Lignes_des_ventes AS l
                ON e.societe = l.societe AND e.[Type Document] = l.[Type Document] AND e.[N° pièce] = l.[N° Pièce]
            INNER JOIN Articles AS a
                ON l.societe = a.societe AND l.[Code article] = a.[Code Article]
            LEFT JOIN Mouvement_stock AS ms
                ON l.societe = ms.societe AND l.[N° interne] = ms.[N° interne]
            WHERE e.Date BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR e.societe = @societe)
              AND l.[Valorise CA] = 'Oui'
            GROUP BY e.societe, YEAR(e.Date), MONTH(e.Date), FORMAT(e.Date, 'yyyy-MM')
            ORDER BY [Année], [Mois]
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global", "required": true, "label": "Date début"}, {"name": "dateFin", "type": "date", "source": "global", "required": true, "label": "Date fin"}, {"name": "societe", "type": "string", "source": "global", "required": false, "label": "Société"}, {"name": "Valorisation", "type": "select", "source": "fixed", "required": true, "label": "Méthode de valorisation", "default": "Prix de revient", "options": ["CMUP", "Prix de revient", "DPA-Vente", "DPA-Période", "DPR-Vente"]}, {"name": "ValorisationCA", "type": "select", "source": "fixed", "required": true, "label": "Valorisation CA", "default": "HT", "options": ["HT", "TTC"]}]'
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
                l.[societe] AS [Societe],
                SUM(l.[Montant HT Net]) AS [Achats HT],
                SUM(l.[Montant TTC Net]) AS [Achats TTC],
                COUNT(DISTINCT l.[Code fournisseur]) AS [Nb Fournisseurs],
                COUNT(DISTINCT l.[N° Pièce]) AS [Nb Documents],
                SUM(l.[Quantité]) AS [Qte Totale],
                COUNT(*) AS [Nb Lignes]
            FROM [Lignes_des_achats] l
            WHERE l.[Type Document] IN ('Facture', 'Facture comptabilisée')
              AND (@societe IS NULL OR l.[societe] = @societe)
              AND l.[Date] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR l.[societe] = @societe)
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
                FORMAT(l.[Date], 'yyyy-MM') AS [Mois],
                l.[societe] AS [Societe],
                SUM(l.[Montant HT Net]) AS [Achats HT],
                SUM(l.[Montant TTC Net]) AS [Achats TTC],
                COUNT(DISTINCT l.[Code fournisseur]) AS [Nb Fournisseurs],
                COUNT(DISTINCT l.[N° Pièce]) AS [Nb Documents],
                SUM(l.[Quantité]) AS [Qte Totale]
            FROM [Lignes_des_achats] l
            WHERE l.[Type Document] IN ('Facture', 'Facture comptabilisée')
              AND (@societe IS NULL OR l.[societe] = @societe)
              AND l.[Date] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR l.[societe] = @societe)
            GROUP BY FORMAT(l.[Date], 'yyyy-MM'), l.[societe]
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
                l.[societe] AS [Societe],
                SUM(l.[Montant HT Net]) AS [Achats HT],
                SUM(l.[Montant TTC Net]) AS [Achats TTC],
                COUNT(DISTINCT l.[N° Pièce]) AS [Nb Documents],
                SUM(l.[Quantité]) AS [Qte Totale],
                COUNT(DISTINCT l.[Code article]) AS [Nb Articles]
            FROM [Lignes_des_achats] l
            INNER JOIN [Fournisseurs] f ON l.[DB_Id] = f.[DB_Id] AND l.[Code fournisseur] = f.[Code fournisseur]
            WHERE l.[Type Document] IN ('Facture', 'Facture comptabilisée')
              AND (@societe IS NULL OR l.[societe] = @societe)
              AND l.[Date] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR l.[societe] = @societe)
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
                l.[societe] AS [Societe],
                SUM(l.[Quantité]) AS [Qte Achetee],
                SUM(l.[Montant HT Net]) AS [Achats HT],
                AVG(l.[Prix unitaire]) AS [Prix Moyen],
                AVG(l.[CMUP]) AS [CMUP Moyen],
                COUNT(DISTINCT l.[Code fournisseur]) AS [Nb Fournisseurs],
                COUNT(DISTINCT l.[N° Pièce]) AS [Nb Documents]
            FROM [Lignes_des_achats] l
            INNER JOIN [Articles] a ON l.[DB_Id] = a.[DB_Id] AND l.[Code article] = a.[Code Article]
            WHERE l.[Type Document] IN ('Facture', 'Facture comptabilisée')
              AND (@societe IS NULL OR l.[societe] = @societe)
              AND l.[Date] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR l.[societe] = @societe)
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
                l.[societe] AS [Societe],
                SUM(l.[Quantité]) AS [Qte Achetee],
                SUM(l.[Montant HT Net]) AS [Achats HT],
                SUM(l.[Montant TTC Net]) AS [Achats TTC],
                COUNT(DISTINCT l.[Code article]) AS [Nb Articles],
                COUNT(DISTINCT l.[Code fournisseur]) AS [Nb Fournisseurs]
            FROM [Lignes_des_achats] l
            INNER JOIN [Articles] a ON l.[DB_Id] = a.[DB_Id] AND l.[Code article] = a.[Code Article]
            WHERE l.[Type Document] IN ('Facture', 'Facture comptabilisée')
              AND (@societe IS NULL OR l.[societe] = @societe)
              AND l.[Date] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR l.[societe] = @societe)
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
                l.[societe] AS [Societe],
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
                l.[Désignation Article] AS [Designation],
                l.[Quantité] AS [Quantite],
                l.[Prix unitaire] AS [Prix Unitaire],
                l.[Montant HT Net] AS [Montant HT],
                l.[Montant TTC Net] AS [Montant TTC],
                l.[CMUP],
                l.[Frais d'approche] AS [Frais Approche],
                l.[societe] AS [Societe]
            FROM [Lignes_des_achats] l
            WHERE l.[Type Document] IN ('Facture', 'Facture comptabilisée')
              AND (@societe IS NULL OR l.[societe] = @societe)
              AND l.[Date] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR l.[societe] = @societe)
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
                l.[Désignation Article] AS [Designation],
                l.[Quantité] AS [Quantite],
                l.[Prix unitaire] AS [Prix Unitaire],
                l.[Montant HT Net] AS [Montant HT],
                l.[N° Pièce BC] AS [N BC],
                l.[Date BC],
                l.[societe] AS [Societe]
            FROM [Lignes_des_achats] l
            WHERE l.[Type Document] = 'Bon de Réception'
              AND (@societe IS NULL OR l.[societe] = @societe)
              AND l.[Date] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR l.[societe] = @societe)
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
                l.[Désignation Article] AS [Designation],
                l.[Quantité] AS [Quantite],
                l.[Prix unitaire] AS [Prix Unitaire],
                l.[Montant HT Net] AS [Montant HT],
                l.[Date Livraison] AS [Date Livraison Prevue],
                e.[Statut],
                e.[Document clôturé] AS [Cloture],
                l.[societe] AS [Societe]
            FROM [Lignes_des_achats] l
            INNER JOIN [Entête_des_achats] e ON l.[DB_Id] = e.[DB_Id] AND l.[Type Document] = e.[Type Document] AND l.[N° Pièce] = e.[N° Pièce]
            WHERE l.[Type Document] = 'Bon de commande'
              AND (@societe IS NULL OR l.[societe] = @societe)
              AND l.[Date] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR l.[societe] = @societe)
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
                l.[Désignation Article] AS [Designation],
                l.[Quantité] AS [Quantite],
                l.[Montant HT Net] AS [Montant HT],
                l.[Montant TTC Net] AS [Montant TTC],
                l.[societe] AS [Societe]
            FROM [Lignes_des_achats] l
            WHERE l.[Type Document] IN ('Bon avoir', 'Bon de retour')
              AND (@societe IS NULL OR l.[societe] = @societe)
              AND l.[Date] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR l.[societe] = @societe)
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
                l.[societe] AS [Societe],
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
                l.[Désignation Article] AS [Designation],
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
                l.[Prix de revient] AS [Prix Revient],
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
                l.[Désignation Article] AS [Designation],
                l.[Quantité] AS [Qte Commandee],
                l.[Prix unitaire] AS [Prix Unitaire],
                l.[Montant HT Net] AS [Montant HT],
                l.[Date Livraison] AS [Date Livraison Prevue],
                e.[Statut],
                e.[Encours],
                DATEDIFF(DAY, l.[Date], GETDATE()) AS [Age Jours],
                l.[societe] AS [Societe]
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
                l.[societe] AS [Societe],
                SUM(l.[Montant HT Net]) AS [Achats HT],
                COUNT(DISTINCT l.[N° Pièce]) AS [Nb Factures],
                COUNT(DISTINCT l.[Code article]) AS [Nb Articles],
                SUM(l.[Quantité]) AS [Qte Totale]
            FROM [Lignes_des_achats] l
            INNER JOIN [Fournisseurs] f ON l.[DB_Id] = f.[DB_Id] AND l.[Code fournisseur] = f.[Code fournisseur]
            WHERE l.[Type Document] IN ('Facture', 'Facture comptabilisée')
              AND (@societe IS NULL OR l.[societe] = @societe)
              AND l.[Date] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR l.[societe] = @societe)
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
                l.[societe] AS [Societe],
                SUM(l.[Quantité]) AS [Qte Achetee],
                SUM(l.[Montant HT Net]) AS [Achats HT],
                AVG(l.[Prix unitaire]) AS [Prix Moyen],
                COUNT(DISTINCT l.[Code fournisseur]) AS [Nb Fournisseurs]
            FROM [Lignes_des_achats] l
            INNER JOIN [Articles] a ON l.[DB_Id] = a.[DB_Id] AND l.[Code article] = a.[Code Article]
            WHERE l.[Type Document] IN ('Facture', 'Facture comptabilisée')
              AND (@societe IS NULL OR l.[societe] = @societe)
              AND l.[Date] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR l.[societe] = @societe)
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
                l.[societe] AS [Societe],
                SUM(l.[Montant HT Net]) AS [Achats HT],
                SUM(l.[Montant TTC Net]) AS [Achats TTC],
                COUNT(DISTINCT l.[Code fournisseur]) AS [Nb Fournisseurs],
                COUNT(DISTINCT l.[Code article]) AS [Nb Articles],
                COUNT(DISTINCT l.[N° Pièce]) AS [Nb Documents]
            FROM [Lignes_des_achats] l
            WHERE l.[Code d'affaire] IS NOT NULL AND l.[Code d'affaire] <> ''
              AND (@societe IS NULL OR l.[societe] = @societe)
              AND l.[Type Document] IN ('Facture', 'Facture comptabilisée')
              AND l.[Date] BETWEEN @dateDebut AND @dateFin
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
                l.[societe] AS [Societe],
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
              AND l.[Date] BETWEEN @dateDebut AND @dateFin
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
                FORMAT(l.[Date], 'yyyy-MM') AS [Mois],
                l.[societe] AS [Societe],
                AVG(l.[Prix unitaire]) AS [Prix Moyen],
                MIN(l.[Prix unitaire]) AS [Prix Min],
                MAX(l.[Prix unitaire]) AS [Prix Max],
                SUM(l.[Quantité]) AS [Qte Achetee],
                COUNT(DISTINCT l.[Code fournisseur]) AS [Nb Fournisseurs]
            FROM [Lignes_des_achats] l
            INNER JOIN [Articles] a ON l.[DB_Id] = a.[DB_Id] AND l.[Code article] = a.[Code Article]
            WHERE l.[Type Document] IN ('Facture', 'Facture comptabilisée')
              AND (@societe IS NULL OR l.[societe] = @societe)
              AND l.[Date] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR l.[societe] = @societe)
            GROUP BY l.[Code article], a.[Désignation Article], FORMAT(l.[Date], 'yyyy-MM'), l.[societe]
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
                l.[societe] AS [Societe],
                SUM(l.[Montant HT Net]) AS [Achats HT],
                SUM(l.[Quantité]) AS [Qte Achetee],
                COUNT(DISTINCT l.[Code article]) AS [Nb Articles],
                COUNT(DISTINCT l.[Code fournisseur]) AS [Nb Fournisseurs]
            FROM [Lignes_des_achats] l
            INNER JOIN [Articles] a ON l.[DB_Id] = a.[DB_Id] AND l.[Code article] = a.[Code Article]
            WHERE a.[Catalogue 1] IS NOT NULL AND a.[Catalogue 1] <> ''
              AND (@societe IS NULL OR l.[societe] = @societe)
              AND l.[Type Document] IN ('Facture', 'Facture comptabilisée')
              AND l.[Date] BETWEEN @dateDebut AND @dateFin
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
                l.[societe] AS [Societe],
                AVG(l.[Prix unitaire]) AS [Prix Moyen],
                MIN(l.[Prix unitaire]) AS [Prix Min],
                MAX(l.[Prix unitaire]) AS [Prix Max],
                SUM(l.[Quantité]) AS [Qte Achetee],
                COUNT(DISTINCT l.[N° Pièce]) AS [Nb Commandes],
                MAX(l.[Date]) AS [Dernier Achat]
            FROM [Lignes_des_achats] l
            INNER JOIN [Articles] a ON l.[DB_Id] = a.[DB_Id] AND l.[Code article] = a.[Code Article]
            WHERE l.[Type Document] IN ('Facture', 'Facture comptabilisée')
              AND (@societe IS NULL OR l.[societe] = @societe)
              AND l.[Date] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR l.[societe] = @societe)
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
                [societe] AS [Societe],
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
                [societe] AS [Societe],
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
                [societe] AS [Societe],
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
                [societe] AS [Societe],
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
                [societe] AS [Societe],
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
                [societe] AS [Societe],
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
                [societe] AS [Societe]
            FROM [Mouvement_stock]
            WHERE [Sens de mouvement] = 'Entrée'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date Mouvement] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
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
                [societe] AS [Societe]
            FROM [Mouvement_stock]
            WHERE [Sens de mouvement] = 'Sortie'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date Mouvement] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
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
                [societe] AS [Societe],
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
                [societe] AS [Societe],
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
                [societe] AS [Societe],
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
                [Prix de revient] AS [Prix Revient],
                [Montant Stock] AS [Valeur Stock],
                ([Prix unitaire] - [Prix de revient]) * [Quantité] AS [Marge],
                [societe] AS [Societe]
            FROM [Mouvement_stock]
            WHERE [Domaine mouvement] = 'Vente'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Type Mouvement] IN ('Facture', 'Facture comptabilisée', 'Bon de livraison')
              AND [Date Mouvement] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
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
                [societe] AS [Societe]
            FROM [Mouvement_stock]
            WHERE [Domaine mouvement] = 'Achat'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date Mouvement] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
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
                [societe] AS [Societe]
            FROM [Mouvement_stock]
            WHERE [Domaine mouvement] IN ('Stock', 'Document interne')
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date Mouvement] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
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
                s.[societe] AS [Societe],
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
                [societe] AS [Societe],
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
                [Prix de revient] AS [Prix Revient],
                [Montant Stock] AS [Valeur Stock],
                [N° Série / Lot] AS [Lot Serie],
                [Gamme 1],
                [Gamme 2],
                [Catalogue 1],
                [Catalogue 2],
                [societe] AS [Societe]
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
                [societe] AS [Societe],
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
              AND (@societe IS NULL OR [societe] = @societe)
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
                [societe] AS [Societe],
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
                [societe] AS [Societe],
                COUNT(*) AS [Nb Mouvements],
                SUM(CASE WHEN [Sens de mouvement] = 'Entrée' THEN [Quantité] ELSE 0 END) AS [Qte Entrees],
                SUM(CASE WHEN [Sens de mouvement] = 'Sortie' THEN [Quantité] ELSE 0 END) AS [Qte Sorties],
                SUM(CASE WHEN [Sens de mouvement] = 'Sortie' THEN [Montant Stock] ELSE 0 END) AS [Valeur Sorties],
                COUNT(DISTINCT [Code article]) AS [Nb Articles]
            FROM [Mouvement_stock]
            WHERE [Catalogue 1] IS NOT NULL AND [Catalogue 1] <> ''
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date Mouvement] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
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
                [societe] AS [Societe],
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
                [societe] AS [Societe],
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
                [societe] AS [Societe],
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
                [societe] AS [Societe],
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
                [societe] AS [Societe],
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
                [Mode de réglement] AS [Mode Reglement],
                [Lettrage],
                [Lettre],
                [societe] AS [Societe]
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
                [societe] AS [Societe]
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
                [societe] AS [Societe],
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
                [societe] AS [Societe],
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
                [societe] AS [Societe],
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
                [societe] AS [Societe],
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
                [societe] AS [Societe],
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
                [societe] AS [Societe],
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
                [societe] AS [Societe],
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
                [societe] AS [Societe],
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
                [societe] AS [Societe],
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
                [societe] AS [Societe],
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
                [societe] AS [Societe],
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
                [societe] AS [Societe],
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
                [societe] AS [Societe],
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
                [societe] AS [Societe],
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
                a.[societe] AS [Societe]
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
                [societe] AS [Societe],
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
                [societe] AS [Societe],
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
                [Mode de réglement] AS [Mode Reglement],
                [Lettrage],
                [Type tiers],
                [societe] AS [Societe],
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
                [societe] AS [Societe],
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
                e.[Nom collaborateur] + ' ' + e.[Prénom collaborateur] AS [Commercial],
                e.[Charge Recouvr] AS [Charge Recouvrement],
                e.[societe] AS [Societe],
                SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'échéance], GETDATE()) <= 0
                    THEN e.[Montant échéance] - ISNULL(e.[Régler], 0) ELSE 0 END) AS [Non Echu],
                SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'échéance], GETDATE()) BETWEEN 1 AND 30
                    THEN e.[Montant échéance] - ISNULL(e.[Régler], 0) ELSE 0 END) AS [0-30j],
                SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'échéance], GETDATE()) BETWEEN 31 AND 60
                    THEN e.[Montant échéance] - ISNULL(e.[Régler], 0) ELSE 0 END) AS [31-60j],
                SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'échéance], GETDATE()) BETWEEN 61 AND 90
                    THEN e.[Montant échéance] - ISNULL(e.[Régler], 0) ELSE 0 END) AS [61-90j],
                SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'échéance], GETDATE()) BETWEEN 91 AND 120
                    THEN e.[Montant échéance] - ISNULL(e.[Régler], 0) ELSE 0 END) AS [91-120j],
                SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'échéance], GETDATE()) > 120
                    THEN e.[Montant échéance] - ISNULL(e.[Régler], 0) ELSE 0 END) AS [+120j],
                SUM(e.[Montant échéance] - ISNULL(e.[Régler], 0)) AS [Total Creance],
                SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'échéance], GETDATE()) > 0
                    THEN e.[Montant échéance] - ISNULL(e.[Régler], 0) ELSE 0 END) AS [Total Echu],
                COUNT(*) AS [Nb Echeances],
                MAX(DATEDIFF(DAY, e.[Date d'échéance], GETDATE())) AS [Max Retard Jours]
            FROM [Echéances_Ventes] e
            WHERE e.[Montant échéance] > ISNULL(e.[Régler], 0)
              AND (@societe IS NULL OR e.[societe] = @societe)
            GROUP BY e.[Code client], e.[Intitulé client],
                     e.[Nom collaborateur], e.[Prénom collaborateur],
                     e.[Charge Recouvr], e.[societe]
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
                    SUM([Montant échéance] - ISNULL([Régler], 0)) AS Total_Encours
                FROM [Echéances_Ventes]
                WHERE [Montant échéance] > ISNULL([Régler], 0)
              AND (@societe IS NULL OR [societe] = @societe)
                GROUP BY [Code client], [Intitulé client], [societe]
            ),
            Reglements AS (
                SELECT
                    [Code client],
                    SUM([Montant réglement]) AS Total_Regle_12M,
                    AVG(DATEDIFF(DAY, [Date document], [Date réglement])) AS Delai_Moyen_Paiement,
                    COUNT(DISTINCT [id Réglement]) AS Nb_Reglements
                FROM [Imputation_Factures_Ventes]
                WHERE [Date réglement] >= DATEADD(YEAR, -1, GETDATE())
                  AND [Date réglement] IS NOT NULL
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
                enc.[societe] AS [Societe],
                enc.Total_Encours AS [Encours],
                ISNULL(ca.CA_12M, 0) AS [CA 12 Mois],
                ISNULL(reg.Total_Regle_12M, 0) AS [Regle 12 Mois],
                ISNULL(reg.Delai_Moyen_Paiement, 0) AS [Delai Moyen Paiement],
                ISNULL(reg.Nb_Reglements, 0) AS [Nb Reglements],
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
                e.[Nom collaborateur] + ' ' + e.[Prénom collaborateur] AS [Commercial],
                e.[Charge Recouvr] AS [Charge Recouvrement],
                e.[societe] AS [Societe],
                SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'échéance], GETDATE()) > 120
                    THEN e.[Montant échéance] - ISNULL(e.[Régler], 0) ELSE 0 END) AS [Montant +120j],
                SUM(e.[Montant échéance] - ISNULL(e.[Régler], 0)) AS [Total Creance],
                CASE
                    WHEN SUM(e.[Montant échéance] - ISNULL(e.[Régler], 0)) > 0
                    THEN ROUND(SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'échéance], GETDATE()) > 120
                        THEN e.[Montant échéance] - ISNULL(e.[Régler], 0) ELSE 0 END) * 100.0
                        / SUM(e.[Montant échéance] - ISNULL(e.[Régler], 0)), 2)
                    ELSE 0
                END AS [% Douteux],
                COUNT(CASE WHEN DATEDIFF(DAY, e.[Date d'échéance], GETDATE()) > 120 THEN 1 END) AS [Nb Echeances +120j],
                MAX(DATEDIFF(DAY, e.[Date d'échéance], GETDATE())) AS [Max Retard Jours]
            FROM [Echéances_Ventes] e
            WHERE e.[Montant échéance] > ISNULL(e.[Régler], 0)
              AND (@societe IS NULL OR e.[societe] = @societe)
            GROUP BY e.[Code client], e.[Intitulé client],
                     e.[Nom collaborateur], e.[Prénom collaborateur],
                     e.[Charge Recouvr], e.[societe]
            HAVING SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'échéance], GETDATE()) > 120
                THEN e.[Montant échéance] - ISNULL(e.[Régler], 0) ELSE 0 END) > 0
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
                [societe] AS [Societe],
                [Code client] AS [Code Client],
                [Intitulé client] AS [Client],
                [Code tier payeur] AS [Code Tier Payeur],
                [Inititulé tier payeur] AS [Tier Payeur],
                [Type Document],
                [N° pièce] AS [Num Piece],
                [Date document] AS [Date Document],
                [Date d'échéance] AS [Date Echeance],
                [Montant échéance] AS [Montant Echeance],
                [Montant TTC],
                [Régler] AS [Montant Regle],
                [Montant échéance] - ISNULL([Régler], 0) AS [Reste A Regler],
                [Mode de réglement] AS [Mode Reglement],
                [Code collaborateur] AS [Code Commercial],
                [Nom collaborateur] + ' ' + [Prénom collaborateur] AS [Commercial],
                [Charge Recouvr] AS [Charge Recouvrement],
                DATEDIFF(DAY, [Date d'échéance], GETDATE()) AS [Jours Retard],
                CASE
                    WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) <= 0 THEN 'A echoir'
                    WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) <= 30 THEN '0-30 jours'
                    WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) <= 60 THEN '31-60 jours'
                    WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) <= 90 THEN '61-90 jours'
                    WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) <= 120 THEN '91-120 jours'
                    ELSE '+120 jours'
                END AS [Tranche Age]
            FROM [Echéances_Ventes]
            WHERE [Montant échéance] > ISNULL([Régler], 0)
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
                [societe] AS [Societe],
                COUNT(*) AS [Nb Echeances],
                SUM([Montant échéance]) AS [Total Echeances],
                SUM(ISNULL([Régler], 0)) AS [Total Regle],
                SUM([Montant échéance] - ISNULL([Régler], 0)) AS [Reste A Regler],
                SUM(CASE WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) <= 0 THEN [Montant échéance] - ISNULL([Régler], 0) ELSE 0 END) AS [A Echoir],
                SUM(CASE WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) BETWEEN 1 AND 30 THEN [Montant échéance] - ISNULL([Régler], 0) ELSE 0 END) AS [0-30j],
                SUM(CASE WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) BETWEEN 31 AND 60 THEN [Montant échéance] - ISNULL([Régler], 0) ELSE 0 END) AS [31-60j],
                SUM(CASE WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) BETWEEN 61 AND 90 THEN [Montant échéance] - ISNULL([Régler], 0) ELSE 0 END) AS [61-90j],
                SUM(CASE WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) BETWEEN 91 AND 120 THEN [Montant échéance] - ISNULL([Régler], 0) ELSE 0 END) AS [91-120j],
                SUM(CASE WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) > 120 THEN [Montant échéance] - ISNULL([Régler], 0) ELSE 0 END) AS [+120j],
                MAX([Date d'échéance]) AS [Derniere Echeance],
                MAX(DATEDIFF(DAY, [Date d'échéance], GETDATE())) AS [Max Jours Retard]
            FROM [Echéances_Ventes]
            WHERE [Montant échéance] > ISNULL([Régler], 0)
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
                [Code collaborateur] AS [Code Commercial],
                [Nom collaborateur] + ' ' + [Prénom collaborateur] AS [Commercial],
                [Charge Recouvr] AS [Charge Recouvrement],
                COUNT(DISTINCT [Code client]) AS [Nb Clients],
                COUNT(*) AS [Nb Echeances],
                SUM([Montant échéance] - ISNULL([Régler], 0)) AS [Encours Total],
                SUM(CASE WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) <= 0 THEN [Montant échéance] - ISNULL([Régler], 0) ELSE 0 END) AS [A Echoir],
                SUM(CASE WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) BETWEEN 1 AND 30 THEN [Montant échéance] - ISNULL([Régler], 0) ELSE 0 END) AS [0-30j],
                SUM(CASE WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) BETWEEN 31 AND 60 THEN [Montant échéance] - ISNULL([Régler], 0) ELSE 0 END) AS [31-60j],
                SUM(CASE WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) BETWEEN 61 AND 90 THEN [Montant échéance] - ISNULL([Régler], 0) ELSE 0 END) AS [61-90j],
                SUM(CASE WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) BETWEEN 91 AND 120 THEN [Montant échéance] - ISNULL([Régler], 0) ELSE 0 END) AS [91-120j],
                SUM(CASE WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) > 120 THEN [Montant échéance] - ISNULL([Régler], 0) ELSE 0 END) AS [+120j]
            FROM [Echéances_Ventes]
            WHERE [Montant échéance] > ISNULL([Régler], 0)
              AND (@societe IS NULL OR [societe] = @societe)
            GROUP BY [Code collaborateur], [Nom collaborateur], [Prénom collaborateur], [Charge Recouvr]
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
                [Mode de réglement] AS [Mode Reglement],
                [Code mode règlement] AS [Code Mode],
                COUNT(*) AS [Nb Echeances],
                SUM([Montant échéance]) AS [Total Echeances],
                SUM([Montant échéance] - ISNULL([Régler], 0)) AS [Reste A Regler],
                AVG(DATEDIFF(DAY, [Date d'échéance], GETDATE())) AS [Retard Moyen Jours]
            FROM [Echéances_Ventes]
            WHERE [Montant échéance] > ISNULL([Régler], 0)
              AND (@societe IS NULL OR [societe] = @societe)
            GROUP BY [Mode de réglement], [Code mode règlement]
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
                [societe] AS [Societe],
                [Code client] AS [Code Client],
                [Intitulé client] AS [Client],
                [N° pièce] AS [Num Piece],
                [Date document] AS [Date Document],
                [Date d'échéance] AS [Date Echeance],
                [Montant échéance] - ISNULL([Régler], 0) AS [Montant A Regler],
                [Mode de réglement] AS [Mode Reglement],
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
              AND [Montant échéance] > ISNULL([Régler], 0)
            ORDER BY [Date d'échéance] ASC
        """,
        "parameters": '[{"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # ==================== REGLEMENTS / IMPUTATIONS ====================
    {
        "code": "DS_REGLEMENTS_PAR_PERIODE",
        "nom": "Reglements par Periode",
        "category": "Recouvrement",
        "description": "Evolution mensuelle des encaissements",
        "query_template": """
            SELECT
                YEAR([Date réglement]) AS [Annee],
                MONTH([Date réglement]) AS [Mois],
                FORMAT([Date réglement], 'yyyy-MM') AS [Periode],
                COUNT(DISTINCT [id Réglement]) AS [Nb Reglements],
                SUM([Montant réglement]) AS [Total Reglements],
                COUNT(DISTINCT [Code client]) AS [Nb Clients],
                AVG(DATEDIFF(DAY, [Date document], [Date réglement])) AS [Delai Moyen Jours]
            FROM [Imputation_Factures_Ventes]
            WHERE [Date réglement] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
            GROUP BY YEAR([Date réglement]), MONTH([Date réglement]), FORMAT([Date réglement], 'yyyy-MM')
            ORDER BY [Annee], [Mois]
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_REGLEMENTS_PAR_CLIENT",
        "nom": "Reglements par Client",
        "category": "Recouvrement",
        "description": "Historique des reglements avec delai moyen de paiement",
        "query_template": """
            SELECT
                [Code client] AS [Code Client],
                [Intitulé client] AS [Client],
                [societe] AS [Societe],
                COUNT(DISTINCT [id Réglement]) AS [Nb Reglements],
                SUM([Montant réglement]) AS [Total Regle],
                MIN([Date réglement]) AS [Premier Reglement],
                MAX([Date réglement]) AS [Dernier Reglement],
                AVG(DATEDIFF(DAY, [Date document], [Date réglement])) AS [Delai Moyen Jours]
            FROM [Imputation_Factures_Ventes]
            WHERE [Date réglement] IS NOT NULL
              AND (@societe IS NULL OR [societe] = @societe)
            GROUP BY [Code client], [Intitulé client], [societe]
            ORDER BY [Total Regle] DESC
        """,
        "parameters": '[{"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },
    {
        "code": "DS_REGLEMENTS_PAR_MODE",
        "nom": "Reglements par Mode",
        "category": "Recouvrement",
        "description": "Repartition des encaissements par mode de reglement",
        "query_template": """
            SELECT
                [Mode de réglement] AS [Mode Reglement],
                COUNT(DISTINCT [id Réglement]) AS [Nb Reglements],
                SUM([Montant réglement]) AS [Total Regle],
                COUNT(DISTINCT [Code client]) AS [Nb Clients],
                AVG(DATEDIFF(DAY, [Date document], [Date réglement])) AS [Delai Moyen Jours]
            FROM [Imputation_Factures_Ventes]
            WHERE [Date réglement] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
            GROUP BY [Mode de réglement]
            ORDER BY [Total Regle] DESC
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
                [societe] AS [Societe],
                [Code client] AS [Code Client],
                [Intitulé client] AS [Client],
                [Type Document],
                [N° pièce] AS [Num Piece],
                [Date document] AS [Date Document],
                [Montant facture TTC] AS [Montant TTC],
                ISNULL([Montant régler], 0) AS [Montant Regle],
                [Montant facture TTC] - ISNULL([Montant régler], 0) AS [Reste A Regler],
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
                (SELECT SUM([Montant échéance] - ISNULL([Régler], 0))
                 FROM [Echéances_Ventes]
                 WHERE [Montant échéance] > ISNULL([Régler], 0)) AS [Encours Total],

                (SELECT SUM([Montant échéance] - ISNULL([Régler], 0))
                 FROM [Echéances_Ventes]
                 WHERE [Date d'échéance] >= GETDATE()
              AND (@societe IS NULL OR [societe] = @societe)
                   AND [Montant échéance] > ISNULL([Régler], 0)) AS [A Echoir],

                (SELECT SUM([Montant échéance] - ISNULL([Régler], 0))
                 FROM [Echéances_Ventes]
                 WHERE [Date d'échéance] < GETDATE()
                   AND [Montant échéance] > ISNULL([Régler], 0)) AS [Echu],

                (SELECT COUNT(*)
                 FROM [Echéances_Ventes]
                 WHERE [Date d'échéance] < GETDATE()
                   AND [Montant échéance] > ISNULL([Régler], 0)) AS [Nb Echeances Retard],

                (SELECT COUNT(DISTINCT [Code client])
                 FROM [Echéances_Ventes]
                 WHERE [Date d'échéance] < GETDATE()
                   AND [Montant échéance] > ISNULL([Régler], 0)) AS [Nb Clients Retard],

                (SELECT ISNULL(SUM([Montant réglement]), 0)
                 FROM [Imputation_Factures_Ventes]
                 WHERE MONTH([Date réglement]) = MONTH(GETDATE())
                   AND YEAR([Date réglement]) = YEAR(GETDATE())) AS [Reglements Mois],

                (SELECT AVG(DATEDIFF(DAY, [Date d'échéance], GETDATE()))
                 FROM [Echéances_Ventes]
                 WHERE [Date d'échéance] < GETDATE()
                   AND [Montant échéance] > ISNULL([Régler], 0)) AS [Retard Moyen Jours]
        """,
        "parameters": '[{"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
    },

    # ==================== TABLEAU DE BORD ====================
    # IMPORTANT: Toutes les requetes de CA utilisent le filtre e.[Valorise CA]='Oui' sur Entête_des_ventes
    {
        "code": "DS_KPI_RESUME",
        "nom": "KPIs Resume",
        "category": "dashboard",
        "description": "Indicateurs cles pour le tableau de bord",
        "query_template": """
            SELECT
                (SELECT SUM(l.[Montant HT])
                 FROM Entête_des_ventes AS e
                 INNER JOIN Lignes_des_ventes AS l ON e.DB_Id = l.DB_Id AND e.[Type Document] = l.[Type Document] AND e.[N° pièce] = l.[N° Pièce]
                 WHERE e.[Date pièce] BETWEEN @dateDebut AND @dateFin AND e.[Valorise CA] = 'Oui' AND @societe_filter) as CA,
                (SELECT SUM(l.[Montant HT] - l.[Prix de revient] * l.[Quantité])
                 FROM Entête_des_ventes AS e
                 INNER JOIN Lignes_des_ventes AS l ON e.DB_Id = l.DB_Id AND e.[Type Document] = l.[Type Document] AND e.[N° pièce] = l.[N° Pièce]
                 WHERE e.[Date pièce] BETWEEN @dateDebut AND @dateFin AND e.[Valorise CA] = 'Oui' AND @societe_filter) as Marge,
                (SELECT SUM(valeur_stock) FROM Stock WHERE @societe_filter) as ValeurStock,
                (SELECT SUM(total_creance) FROM BalanceAgee WHERE @societe_filter) as Encours,
                (SELECT SUM(tranche_plus_120) FROM BalanceAgee WHERE @societe_filter) as CreancesDouteuses,
                (SELECT COUNT(DISTINCT e.[Code client])
                 FROM Entête_des_ventes AS e
                 WHERE e.[Date pièce] BETWEEN @dateDebut AND @dateFin AND e.[Valorise CA] = 'Oui' AND @societe_filter) as NbClientsActifs
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
                e.[Code client] as [Code],
                c.[Nom] as [Client],
                SUM(l.[Montant HT]) as CA,
                SUM(l.[Montant HT] - l.[Prix de revient] * l.[Quantité]) as Marge
            FROM Entête_des_ventes AS e
            INNER JOIN Clients AS c ON e.[Code client] = c.[Code client] AND e.DB_Id = c.DB_Id
            INNER JOIN Lignes_des_ventes AS l ON e.DB_Id = l.DB_Id AND e.[Type Document] = l.[Type Document] AND e.[N° pièce] = l.[N° Pièce]
            WHERE e.[Valorise CA] = 'Oui'
            AND e.[Date pièce] BETWEEN @dateDebut AND @dateFin
            AND @societe_filter
            GROUP BY e.[Code client], c.[Nom]
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
                l.[Code article] as [Code],
                a.[Désignation] as [Article],
                SUM(l.[Quantité]) as [Qte],
                SUM(l.[Montant HT]) as CA
            FROM Entête_des_ventes AS e
            INNER JOIN Lignes_des_ventes AS l ON e.DB_Id = l.DB_Id AND e.[Type Document] = l.[Type Document] AND e.[N° pièce] = l.[N° Pièce]
            INNER JOIN Articles AS a ON l.DB_Id = a.DB_Id AND l.[Code article] = a.[Code Article]
            WHERE e.[Valorise CA] = 'Oui'
            AND e.[Date pièce] BETWEEN @dateDebut AND @dateFin
            AND @societe_filter
            GROUP BY l.[Code article], a.[Désignation]
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
                YEAR([Date]) AS [Annee],
                MONTH([Date]) AS [Mois],
                FORMAT([Date], 'yyyy-MM') AS [Periode],
                [Code client] AS [Code Client],
                [Intitulé client] AS [Client],
                [societe] AS [Societe],
                SUM([Montant HT Net]) AS [CA HT],
                SUM([Montant TTC Net]) AS [CA TTC],
                SUM([Montant HT Net] - [Prix de revient] * [Quantité]) AS [Marge],
                CASE WHEN SUM([Montant HT Net]) > 0
                    THEN ROUND(SUM([Montant HT Net] - [Prix de revient] * [Quantité]) * 100.0 / SUM([Montant HT Net]), 2)
                    ELSE 0 END AS [Taux Marge %],
                COUNT(DISTINCT [N° Pièce]) AS [Nb Factures],
                SUM([Quantité]) AS [Qte Totale]
            FROM [Lignes_des_ventes]
            WHERE [Valorise CA] = 'Oui'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date] BETWEEN @dateDebut AND @dateFin
            GROUP BY YEAR([Date]), MONTH([Date]), FORMAT([Date], 'yyyy-MM'),
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
                YEAR([Date]) AS [Annee],
                MONTH([Date]) AS [Mois],
                FORMAT([Date], 'yyyy-MM') AS [Periode],
                [Code article] AS [Code Article],
                [Désignation ligne] AS [Article],
                [Catalogue 1] AS [Catalogue],
                SUM([Quantité]) AS [Qte Vendue],
                SUM([Montant HT Net]) AS [CA HT],
                SUM([Montant HT Net] - [Prix de revient] * [Quantité]) AS [Marge],
                CASE WHEN SUM([Montant HT Net]) > 0
                    THEN ROUND(SUM([Montant HT Net] - [Prix de revient] * [Quantité]) * 100.0 / SUM([Montant HT Net]), 2)
                    ELSE 0 END AS [Taux Marge %]
            FROM [Lignes_des_ventes]
            WHERE [Valorise CA] = 'Oui'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date] BETWEEN @dateDebut AND @dateFin
            GROUP BY YEAR([Date]), MONTH([Date]), FORMAT([Date], 'yyyy-MM'),
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
                YEAR(l.[Date]) AS [Annee],
                MONTH(l.[Date]) AS [Mois],
                FORMAT(l.[Date], 'yyyy-MM') AS [Periode],
                e.[Code commercial] AS [Code Commercial],
                e.[Nom commercial] AS [Commercial],
                l.[societe] AS [Societe],
                COUNT(DISTINCT l.[Code client]) AS [Nb Clients],
                SUM(l.[Montant HT Net]) AS [CA HT],
                SUM(l.[Montant HT Net] - l.[Prix de revient] * l.[Quantité]) AS [Marge],
                CASE WHEN SUM(l.[Montant HT Net]) > 0
                    THEN ROUND(SUM(l.[Montant HT Net] - l.[Prix de revient] * l.[Quantité]) * 100.0 / SUM(l.[Montant HT Net]), 2)
                    ELSE 0 END AS [Taux Marge %]
            FROM [Lignes_des_ventes] l
            INNER JOIN [Entête_des_ventes] e
                ON l.[DB] = e.[DB_Id]
                AND l.[Type Document] = e.[Type Document]
                AND l.[N° Pièce] = e.[N° pièce]
            WHERE l.[Valorise CA] = 'Oui'
              AND (@societe IS NULL OR l.[societe] = @societe)
              AND l.[Date] BETWEEN @dateDebut AND @dateFin
            GROUP BY YEAR(l.[Date]), MONTH(l.[Date]), FORMAT(l.[Date], 'yyyy-MM'),
                     e.[Code commercial], e.[Nom commercial], l.[societe]
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
                YEAR([Date]) AS [Annee],
                MONTH([Date]) AS [Mois],
                FORMAT([Date], 'yyyy-MM') AS [Periode],
                [Catalogue 1] AS [Catalogue],
                [Catalogue 2] AS [Sous Catalogue],
                COUNT(DISTINCT [Code article]) AS [Nb Articles],
                SUM([Quantité]) AS [Qte Vendue],
                SUM([Montant HT Net]) AS [CA HT],
                SUM([Montant HT Net] - [Prix de revient] * [Quantité]) AS [Marge],
                CASE WHEN SUM([Montant HT Net]) > 0
                    THEN ROUND(SUM([Montant HT Net] - [Prix de revient] * [Quantité]) * 100.0 / SUM([Montant HT Net]), 2)
                    ELSE 0 END AS [Taux Marge %]
            FROM [Lignes_des_ventes]
            WHERE [Valorise CA] = 'Oui'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date] BETWEEN @dateDebut AND @dateFin
              AND [Catalogue 1] IS NOT NULL
            GROUP BY YEAR([Date]), MONTH([Date]), FORMAT([Date], 'yyyy-MM'),
                     [Catalogue 1], [Catalogue 2]
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
                [societe] AS [Societe],
                [Type Document],
                [N° Pièce] AS [Num Piece],
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
                [Prix de revient] AS [Prix Revient],
                [CMUP],
                [Coût standard] AS [Cout Standard],
                [Montant HT Net] - [Prix de revient] * [Quantité] AS [Marge],
                CASE WHEN [Montant HT Net] <> 0
                    THEN ROUND(([Montant HT Net] - [Prix de revient] * [Quantité]) * 100.0 / [Montant HT Net], 2)
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
                [societe] AS [Societe],
                [Type Document],
                [N° Pièce] AS [Num Piece],
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
                [Prix de revient] AS [Prix Revient],
                [Montant HT Net] - [Prix de revient] * [Quantité] AS [Marge],
                CASE WHEN [Montant HT Net] <> 0
                    THEN ROUND(([Montant HT Net] - [Prix de revient] * [Quantité]) * 100.0 / [Montant HT Net], 2)
                    ELSE 0 END AS [Taux Marge]

            FROM [Lignes_des_ventes]
            WHERE [Valorise CA] = 'Oui'
              AND [Date] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
              AND (@typeDocument IS NULL OR [Type Document] = @typeDocument)
            ORDER BY [Date] DESC, [Num Piece]
        """,
        "parameters": '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}, {"name": "typeDocument", "type": "select", "source": "static", "options": [{"value": "Facture", "label": "Facture"}, {"value": "Facture comptabilisée", "label": "Facture comptabilisée"}, {"value": "Bon de livraison", "label": "Bon de livraison"}], "required": false, "allow_null": true, "null_label": "(Tous)"}]'
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
