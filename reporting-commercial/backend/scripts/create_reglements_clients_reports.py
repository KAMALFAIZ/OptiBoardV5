# -*- coding: utf-8 -*-
"""
Creation des 25 rapports du cycle REGLEMENTS CLIENTS pour OptiBoard
10 GRID + 6 PIVOT + 9 DASHBOARD
Table source: R\u00e8glements_Clients (DWH)
"""
import pyodbc, json, re

CONN_STR = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019;TrustServerCertificate=yes"

# ======================================================================
# PARAMETRES COMMUNS
# ======================================================================
PARAMS_DATE_SOCIETE = json.dumps([
    {"name": "dateDebut", "type": "date", "label": "Date d\u00e9but", "required": True, "default": "FIRST_DAY_YEAR"},
    {"name": "dateFin", "type": "date", "label": "Date fin", "required": True, "default": "TODAY"},
    {"name": "societe", "type": "select", "label": "Soci\u00e9t\u00e9", "required": False,
     "source": "query", "query": "SELECT code as value, nom + ' (' + code + ')' as label FROM APP_DWH WHERE actif = 1 ORDER BY nom",
     "allow_null": True, "null_label": "(Toutes)"}
])

PARAMS_SOCIETE_ONLY = json.dumps([
    {"name": "societe", "type": "select", "label": "Soci\u00e9t\u00e9", "required": False,
     "source": "query", "query": "SELECT code as value, nom + ' (' + code + ')' as label FROM APP_DWH WHERE actif = 1 ORDER BY nom",
     "allow_null": True, "null_label": "(Toutes)"}
])

# Unicode column names for R\u00e8glements_Clients (rc):
#   Table: [R\u00e8glements_Clients]  (\u00e8 = e-grave in table name AND Mode de r\u00e8glement, Code r\u00e8glement)
#   Intitul\u00e9, Intitul\u00e9 original, Date d'\u00e9ch\u00e9ance, R\u00e9f\u00e9rence, Libell\u00e9
#   Comptabilis\u00e9, Compte g\u00e9n\u00e9rale, N\u00b0 pi\u00e9ce, N\u00b0 interne
#   Mode de r\u00e8glement (\u00e8 !), Code r\u00e8glement (\u00e8 !), Date cr\u00e9ation
#   Valide = 'Oui'/'Non', Impute = 'Oui'/'Non', Comptabilis\u00e9 = 'Oui'/'Non'

TBL = "[R\u00e8glements_Clients]"
SOC = "(@societe IS NULL OR rc.societe = @societe)"

# ======================================================================
# 25 DATASOURCE TEMPLATES
# ======================================================================
DS_TEMPLATES = [
    # --- 1. GRID: Detail Reglements Clients ---
    {
        "code": "DS_RGC_DETAIL_REGLEMENTS",
        "nom": "D\u00e9tail R\u00e8glements Clients",
        "query": "SELECT "
            + "rc.[Code client], rc.[Intitul\u00e9] AS [Client], "
            + "rc.[Code client original], rc.[Intitul\u00e9 original] AS [Client Original], "
            + "rc.[Date], rc.[Date d'\u00e9ch\u00e9ance] AS [Date Echeance], "
            + "rc.[R\u00e9f\u00e9rence] AS [Reference], rc.[Libell\u00e9] AS [Libelle], "
            + "rc.[Code journal], rc.[Journal], "
            + "rc.[Compte g\u00e9n\u00e9rale] AS [Compte General], "
            + "rc.[N\u00b0 pi\u00e9ce] AS [Num Piece], "
            + "rc.[Mode de r\u00e8glement] AS [Mode Reglement], "
            + "rc.[Montant], rc.[solde] AS [Solde], "
            + "rc.[Devise], rc.[Valide], rc.[Impute], "
            + "rc.societe AS [Societe] "
            + "FROM " + TBL + " rc "
            + "WHERE rc.[Date] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "ORDER BY rc.[Date] DESC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "reglements_clients"
    },
    # --- 2. GRID: Reglements Non Imputes ---
    {
        "code": "DS_RGC_NON_IMPUTES",
        "nom": "R\u00e8glements Non Imput\u00e9s",
        "query": "SELECT "
            + "rc.[Code client], rc.[Intitul\u00e9] AS [Client], "
            + "rc.[Date], rc.[Date d'\u00e9ch\u00e9ance] AS [Date Echeance], "
            + "rc.[R\u00e9f\u00e9rence] AS [Reference], rc.[Libell\u00e9] AS [Libelle], "
            + "rc.[Journal], rc.[N\u00b0 pi\u00e9ce] AS [Num Piece], "
            + "rc.[Mode de r\u00e8glement] AS [Mode Reglement], "
            + "rc.[Montant], rc.[solde] AS [Solde], "
            + "DATEDIFF(day, rc.[Date], GETDATE()) AS [Jours Depuis Reglement], "
            + "rc.societe AS [Societe] "
            + "FROM " + TBL + " rc "
            + "WHERE rc.[Impute] = 'Non' "
            + "AND " + SOC + " "
            + "ORDER BY rc.[Montant] DESC",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "reglements_clients"
    },
    # --- 3. GRID: Reglements avec Solde Non Nul ---
    {
        "code": "DS_RGC_SOLDE_NON_NUL",
        "nom": "R\u00e8glements avec Solde Non Nul",
        "query": "SELECT "
            + "rc.[Code client], rc.[Intitul\u00e9] AS [Client], "
            + "rc.[Date], rc.[Date d'\u00e9ch\u00e9ance] AS [Date Echeance], "
            + "rc.[R\u00e9f\u00e9rence] AS [Reference], rc.[Libell\u00e9] AS [Libelle], "
            + "rc.[Journal], rc.[N\u00b0 pi\u00e9ce] AS [Num Piece], "
            + "rc.[Mode de r\u00e8glement] AS [Mode Reglement], "
            + "rc.[Montant], rc.[solde] AS [Solde], "
            + "rc.[Montant] - rc.[solde] AS [Montant Impute], "
            + "rc.societe AS [Societe] "
            + "FROM " + TBL + " rc "
            + "WHERE ABS(rc.[solde]) > 0.01 "
            + "AND " + SOC + " "
            + "ORDER BY ABS(rc.[solde]) DESC",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "reglements_clients"
    },
    # --- 4. GRID: Encaissements par Client ---
    {
        "code": "DS_RGC_PAR_CLIENT",
        "nom": "Encaissements par Client",
        "query": "SELECT "
            + "rc.[Code client], rc.[Intitul\u00e9] AS [Client], "
            + "COUNT(*) AS [Nb Reglements], "
            + "SUM(rc.[Montant]) AS [Total Encaisse], "
            + "SUM(rc.[solde]) AS [Total Solde], "
            + "AVG(rc.[Montant]) AS [Montant Moyen], "
            + "MIN(rc.[Date]) AS [Premier Reglement], "
            + "MAX(rc.[Date]) AS [Dernier Reglement], "
            + "rc.societe AS [Societe] "
            + "FROM " + TBL + " rc "
            + "WHERE rc.[Date] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY rc.[Code client], rc.[Intitul\u00e9], rc.societe "
            + "ORDER BY SUM(rc.[Montant]) DESC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "reglements_clients"
    },
    # --- 5. GRID: Echeances Reglements Clients ---
    {
        "code": "DS_RGC_ECHEANCES",
        "nom": "Ech\u00e9ances R\u00e8glements Clients",
        "query": "SELECT "
            + "rc.[Code client], rc.[Intitul\u00e9] AS [Client], "
            + "rc.[Date], rc.[Date d'\u00e9ch\u00e9ance] AS [Date Echeance], "
            + "rc.[R\u00e9f\u00e9rence] AS [Reference], rc.[Libell\u00e9] AS [Libelle], "
            + "rc.[Mode de r\u00e8glement] AS [Mode Reglement], "
            + "rc.[Montant], rc.[solde] AS [Solde], "
            + "CASE WHEN rc.[Date d'\u00e9ch\u00e9ance] < GETDATE() AND ABS(rc.[solde]) > 0.01 THEN 'Echu Non Encaisse' "
            + "WHEN rc.[Date d'\u00e9ch\u00e9ance] < GETDATE() THEN 'Echu Encaisse' "
            + "WHEN rc.[Date d'\u00e9ch\u00e9ance] >= GETDATE() THEN 'Non Echu' "
            + "ELSE 'Sans Echeance' END AS [Statut Echeance], "
            + "rc.societe AS [Societe] "
            + "FROM " + TBL + " rc "
            + "WHERE rc.[Date d'\u00e9ch\u00e9ance] IS NOT NULL "
            + "AND rc.[Date] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "ORDER BY rc.[Date d'\u00e9ch\u00e9ance] ASC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "reglements_clients"
    },
    # --- 6. GRID: Reglements par Journal ---
    {
        "code": "DS_RGC_PAR_JOURNAL",
        "nom": "R\u00e8glements par Journal",
        "query": "SELECT "
            + "rc.[Code journal], rc.[Journal], "
            + "COUNT(*) AS [Nb Reglements], "
            + "SUM(rc.[Montant]) AS [Total Encaisse], "
            + "SUM(rc.[solde]) AS [Total Solde], "
            + "AVG(rc.[Montant]) AS [Montant Moyen], "
            + "COUNT(DISTINCT rc.[Code client]) AS [Nb Clients], "
            + "rc.societe AS [Societe] "
            + "FROM " + TBL + " rc "
            + "WHERE rc.[Date] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY rc.[Code journal], rc.[Journal], rc.societe "
            + "ORDER BY SUM(rc.[Montant]) DESC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "reglements_clients"
    },
    # --- 7. GRID: Top 20 Clients Encaissements ---
    {
        "code": "DS_RGC_TOP_CLIENTS",
        "nom": "Top 20 Clients Encaissements",
        "query": "SELECT TOP 20 "
            + "rc.[Code client], rc.[Intitul\u00e9] AS [Client], "
            + "COUNT(*) AS [Nb Reglements], "
            + "SUM(rc.[Montant]) AS [Total Encaisse], "
            + "SUM(rc.[solde]) AS [Total Solde], "
            + "AVG(rc.[Montant]) AS [Montant Moyen], "
            + "MAX(rc.[Date]) AS [Dernier Reglement], "
            + "rc.societe AS [Societe] "
            + "FROM " + TBL + " rc "
            + "WHERE rc.[Date] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY rc.[Code client], rc.[Intitul\u00e9], rc.societe "
            + "ORDER BY SUM(rc.[Montant]) DESC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "reglements_clients"
    },
    # --- 8. GRID: Reglements par Compte General ---
    {
        "code": "DS_RGC_PAR_COMPTE",
        "nom": "R\u00e8glements par Compte G\u00e9n\u00e9ral",
        "query": "SELECT "
            + "rc.[Compte g\u00e9n\u00e9rale] AS [Compte General], "
            + "COUNT(*) AS [Nb Reglements], "
            + "SUM(rc.[Montant]) AS [Total Encaisse], "
            + "SUM(rc.[solde]) AS [Total Solde], "
            + "COUNT(DISTINCT rc.[Code client]) AS [Nb Clients], "
            + "rc.societe AS [Societe] "
            + "FROM " + TBL + " rc "
            + "WHERE rc.[Date] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY rc.[Compte g\u00e9n\u00e9rale], rc.societe "
            + "ORDER BY SUM(rc.[Montant]) DESC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "reglements_clients"
    },
    # --- 9. GRID: Reglements Non Valides ---
    {
        "code": "DS_RGC_NON_VALIDES",
        "nom": "R\u00e8glements Non Valid\u00e9s",
        "query": "SELECT "
            + "rc.[Code client], rc.[Intitul\u00e9] AS [Client], "
            + "rc.[Date], rc.[R\u00e9f\u00e9rence] AS [Reference], "
            + "rc.[Libell\u00e9] AS [Libelle], "
            + "rc.[Journal], rc.[N\u00b0 pi\u00e9ce] AS [Num Piece], "
            + "rc.[Mode de r\u00e8glement] AS [Mode Reglement], "
            + "rc.[Montant], rc.[solde] AS [Solde], "
            + "rc.[Valide], rc.[Impute], "
            + "rc.societe AS [Societe] "
            + "FROM " + TBL + " rc "
            + "WHERE rc.[Valide] = 'Non' "
            + "AND " + SOC + " "
            + "ORDER BY rc.[Date] DESC",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "reglements_clients"
    },
    # --- 10. GRID: Reglements par Portfeuille ---
    {
        "code": "DS_RGC_PAR_PORTEFEUILLE",
        "nom": "R\u00e8glements par Portefeuille",
        "query": "SELECT "
            + "ISNULL(rc.[Portfeuille], 'Non d\u00e9fini') AS [Portefeuille], "
            + "COUNT(*) AS [Nb Reglements], "
            + "SUM(rc.[Montant]) AS [Total Encaisse], "
            + "SUM(rc.[solde]) AS [Total Solde], "
            + "AVG(rc.[Montant]) AS [Montant Moyen], "
            + "COUNT(DISTINCT rc.[Code client]) AS [Nb Clients], "
            + "rc.societe AS [Societe] "
            + "FROM " + TBL + " rc "
            + "WHERE rc.[Date] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY ISNULL(rc.[Portfeuille], 'Non d\u00e9fini'), rc.societe "
            + "ORDER BY SUM(rc.[Montant]) DESC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "reglements_clients"
    },
    # --- 11. PIVOT: Encaissements par Mode Reglement ---
    {
        "code": "DS_RGC_PIVOT_MODE",
        "nom": "Encaissements par Mode R\u00e8glement",
        "query": "SELECT "
            + "ISNULL(rc.[Mode de r\u00e8glement], 'Non d\u00e9fini') AS [Mode Reglement], "
            + "COUNT(*) AS [Nb Reglements], "
            + "SUM(rc.[Montant]) AS [Total Encaisse], "
            + "AVG(rc.[Montant]) AS [Montant Moyen], "
            + "COUNT(DISTINCT rc.[Code client]) AS [Nb Clients], "
            + "rc.societe AS [Societe] "
            + "FROM " + TBL + " rc "
            + "WHERE rc.[Date] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY ISNULL(rc.[Mode de r\u00e8glement], 'Non d\u00e9fini'), rc.societe",
        "params": PARAMS_DATE_SOCIETE,
        "category": "reglements_clients"
    },
    # --- 12. PIVOT: Encaissements par Journal ---
    {
        "code": "DS_RGC_PIVOT_JOURNAL",
        "nom": "Encaissements par Journal",
        "query": "SELECT "
            + "rc.[Code journal], rc.[Journal], "
            + "COUNT(*) AS [Nb Reglements], "
            + "SUM(rc.[Montant]) AS [Total Encaisse], "
            + "SUM(rc.[solde]) AS [Total Solde], "
            + "COUNT(DISTINCT rc.[Code client]) AS [Nb Clients], "
            + "rc.societe AS [Societe] "
            + "FROM " + TBL + " rc "
            + "WHERE rc.[Date] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY rc.[Code journal], rc.[Journal], rc.societe",
        "params": PARAMS_DATE_SOCIETE,
        "category": "reglements_clients"
    },
    # --- 13. PIVOT: Encaissements Mensuels ---
    {
        "code": "DS_RGC_PIVOT_MENSUEL",
        "nom": "Encaissements Mensuels",
        "query": "SELECT "
            + "CAST(YEAR(rc.[Date]) AS VARCHAR) + '-' + RIGHT('0' + CAST(MONTH(rc.[Date]) AS VARCHAR), 2) AS [Periode], "
            + "COUNT(*) AS [Nb Reglements], "
            + "SUM(rc.[Montant]) AS [Total Encaisse], "
            + "SUM(rc.[solde]) AS [Total Solde], "
            + "COUNT(DISTINCT rc.[Code client]) AS [Nb Clients], "
            + "rc.societe AS [Societe] "
            + "FROM " + TBL + " rc "
            + "WHERE rc.[Date] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY CAST(YEAR(rc.[Date]) AS VARCHAR) + '-' + RIGHT('0' + CAST(MONTH(rc.[Date]) AS VARCHAR), 2), rc.societe "
            + "ORDER BY CAST(YEAR(rc.[Date]) AS VARCHAR) + '-' + RIGHT('0' + CAST(MONTH(rc.[Date]) AS VARCHAR), 2)",
        "params": PARAMS_DATE_SOCIETE,
        "category": "reglements_clients"
    },
    # --- 14. PIVOT: Encaissements par Client et Mode ---
    {
        "code": "DS_RGC_PIVOT_CLIENT_MODE",
        "nom": "Encaissements par Client et Mode",
        "query": "SELECT "
            + "rc.[Code client], rc.[Intitul\u00e9] AS [Client], "
            + "ISNULL(rc.[Mode de r\u00e8glement], 'Non d\u00e9fini') AS [Mode Reglement], "
            + "COUNT(*) AS [Nb Reglements], "
            + "SUM(rc.[Montant]) AS [Total Encaisse], "
            + "rc.societe AS [Societe] "
            + "FROM " + TBL + " rc "
            + "WHERE rc.[Date] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY rc.[Code client], rc.[Intitul\u00e9], ISNULL(rc.[Mode de r\u00e8glement], 'Non d\u00e9fini'), rc.societe",
        "params": PARAMS_DATE_SOCIETE,
        "category": "reglements_clients"
    },
    # --- 15. PIVOT: Evolution Annuelle Encaissements ---
    {
        "code": "DS_RGC_PIVOT_ANNUEL",
        "nom": "Evolution Annuelle Encaissements",
        "query": "SELECT "
            + "CAST(YEAR(rc.[Date]) AS VARCHAR) AS [Exercice], "
            + "COUNT(*) AS [Nb Reglements], "
            + "SUM(rc.[Montant]) AS [Total Encaisse], "
            + "SUM(rc.[solde]) AS [Total Solde], "
            + "AVG(rc.[Montant]) AS [Montant Moyen], "
            + "COUNT(DISTINCT rc.[Code client]) AS [Nb Clients], "
            + "rc.societe AS [Societe] "
            + "FROM " + TBL + " rc "
            + "WHERE " + SOC + " "
            + "GROUP BY CAST(YEAR(rc.[Date]) AS VARCHAR), rc.societe "
            + "ORDER BY CAST(YEAR(rc.[Date]) AS VARCHAR)",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "reglements_clients"
    },
    # --- 16. PIVOT: Statut Imputation Reglements ---
    {
        "code": "DS_RGC_PIVOT_IMPUTATION",
        "nom": "Statut Imputation R\u00e8glements",
        "query": "SELECT "
            + "rc.[Impute] AS [Statut Imputation], "
            + "COUNT(*) AS [Nb Reglements], "
            + "SUM(rc.[Montant]) AS [Total Encaisse], "
            + "SUM(rc.[solde]) AS [Total Solde], "
            + "COUNT(DISTINCT rc.[Code client]) AS [Nb Clients], "
            + "rc.societe AS [Societe] "
            + "FROM " + TBL + " rc "
            + "WHERE rc.[Date] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY rc.[Impute], rc.societe",
        "params": PARAMS_DATE_SOCIETE,
        "category": "reglements_clients"
    },
    # --- 17. DASHBOARD: KPIs Globaux Encaissements ---
    {
        "code": "DS_RGC_KPI_GLOBAL",
        "nom": "KPIs Encaissements Clients",
        "query": "SELECT "
            + "COUNT(*) AS [Nb Reglements], "
            + "SUM(rc.[Montant]) AS [Total Encaisse], "
            + "SUM(rc.[solde]) AS [Total Solde], "
            + "SUM(rc.[Montant]) - SUM(rc.[solde]) AS [Total Impute], "
            + "CASE WHEN SUM(rc.[Montant]) > 0 THEN ROUND((SUM(rc.[Montant]) - SUM(rc.[solde])) * 100.0 / SUM(rc.[Montant]), 2) ELSE 0 END AS [Taux Imputation], "
            + "COUNT(DISTINCT rc.[Code client]) AS [Nb Clients], "
            + "AVG(rc.[Montant]) AS [Montant Moyen], "
            + "SUM(CASE WHEN rc.[Impute] = 'Non' THEN 1 ELSE 0 END) AS [Nb Non Imputes], "
            + "rc.societe AS [Societe] "
            + "FROM " + TBL + " rc "
            + "WHERE rc.[Date] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY rc.societe",
        "params": PARAMS_DATE_SOCIETE,
        "category": "reglements_clients"
    },
    # --- 18. DASHBOARD: Evolution Mensuelle Encaissements ---
    {
        "code": "DS_RGC_EVOLUTION_MENSUELLE",
        "nom": "Evolution Mensuelle Encaissements",
        "query": "SELECT "
            + "CAST(YEAR(rc.[Date]) AS VARCHAR) + '-' + RIGHT('0' + CAST(MONTH(rc.[Date]) AS VARCHAR), 2) AS [Periode], "
            + "SUM(rc.[Montant]) AS [Total Encaisse], "
            + "SUM(rc.[solde]) AS [Total Solde], "
            + "COUNT(*) AS [Nb Reglements], "
            + "COUNT(DISTINCT rc.[Code client]) AS [Nb Clients], "
            + "rc.societe AS [Societe] "
            + "FROM " + TBL + " rc "
            + "WHERE rc.[Date] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY CAST(YEAR(rc.[Date]) AS VARCHAR) + '-' + RIGHT('0' + CAST(MONTH(rc.[Date]) AS VARCHAR), 2), rc.societe "
            + "ORDER BY CAST(YEAR(rc.[Date]) AS VARCHAR) + '-' + RIGHT('0' + CAST(MONTH(rc.[Date]) AS VARCHAR), 2)",
        "params": PARAMS_DATE_SOCIETE,
        "category": "reglements_clients"
    },
    # --- 19. DASHBOARD: Repartition par Mode Encaissement ---
    {
        "code": "DS_RGC_REPARTITION_MODE",
        "nom": "R\u00e9partition par Mode Encaissement",
        "query": "SELECT "
            + "ISNULL(rc.[Mode de r\u00e8glement], 'Non d\u00e9fini') AS [Mode Reglement], "
            + "COUNT(*) AS [Nb Reglements], "
            + "SUM(rc.[Montant]) AS [Total Encaisse], "
            + "AVG(rc.[Montant]) AS [Montant Moyen], "
            + "COUNT(DISTINCT rc.[Code client]) AS [Nb Clients], "
            + "rc.societe AS [Societe] "
            + "FROM " + TBL + " rc "
            + "WHERE rc.[Date] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY ISNULL(rc.[Mode de r\u00e8glement], 'Non d\u00e9fini'), rc.societe "
            + "ORDER BY SUM(rc.[Montant]) DESC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "reglements_clients"
    },
    # --- 20. DASHBOARD: Repartition par Journal ---
    {
        "code": "DS_RGC_REPARTITION_JOURNAL",
        "nom": "R\u00e9partition par Journal",
        "query": "SELECT "
            + "rc.[Code journal], rc.[Journal], "
            + "COUNT(*) AS [Nb Reglements], "
            + "SUM(rc.[Montant]) AS [Total Encaisse], "
            + "SUM(rc.[solde]) AS [Total Solde], "
            + "rc.societe AS [Societe] "
            + "FROM " + TBL + " rc "
            + "WHERE rc.[Date] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY rc.[Code journal], rc.[Journal], rc.societe "
            + "ORDER BY SUM(rc.[Montant]) DESC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "reglements_clients"
    },
    # --- 21. DASHBOARD: Top Clients Encaissements (chart) ---
    {
        "code": "DS_RGC_TOP_CLIENTS_CHART",
        "nom": "Top 15 Clients Encaissements",
        "query": "SELECT TOP 15 "
            + "rc.[Intitul\u00e9] AS [Client], "
            + "SUM(rc.[Montant]) AS [Total Encaisse], "
            + "COUNT(*) AS [Nb Reglements], "
            + "rc.societe AS [Societe] "
            + "FROM " + TBL + " rc "
            + "WHERE rc.[Date] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY rc.[Intitul\u00e9], rc.societe "
            + "ORDER BY SUM(rc.[Montant]) DESC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "reglements_clients"
    },
    # --- 22. DASHBOARD: Statut Imputation ---
    {
        "code": "DS_RGC_STATUT_IMPUTATION",
        "nom": "Statut Imputation R\u00e8glements",
        "query": "SELECT "
            + "rc.[Impute] AS [Statut], "
            + "COUNT(*) AS [Nb Reglements], "
            + "SUM(rc.[Montant]) AS [Total Encaisse], "
            + "SUM(rc.[solde]) AS [Total Solde], "
            + "rc.societe AS [Societe] "
            + "FROM " + TBL + " rc "
            + "WHERE rc.[Date] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY rc.[Impute], rc.societe",
        "params": PARAMS_DATE_SOCIETE,
        "category": "reglements_clients"
    },
    # --- 23. DASHBOARD: Encaissements par Tranche Montant ---
    {
        "code": "DS_RGC_TRANCHE_MONTANT",
        "nom": "Encaissements par Tranche de Montant",
        "query": "SELECT "
            + "CASE WHEN rc.[Montant] < 1000 THEN '< 1K' "
            + "WHEN rc.[Montant] < 10000 THEN '1K - 10K' "
            + "WHEN rc.[Montant] < 50000 THEN '10K - 50K' "
            + "WHEN rc.[Montant] < 100000 THEN '50K - 100K' "
            + "WHEN rc.[Montant] < 500000 THEN '100K - 500K' "
            + "ELSE '> 500K' END AS [Tranche Montant], "
            + "COUNT(*) AS [Nb Reglements], "
            + "SUM(rc.[Montant]) AS [Total Encaisse], "
            + "rc.societe AS [Societe] "
            + "FROM " + TBL + " rc "
            + "WHERE rc.[Date] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY CASE WHEN rc.[Montant] < 1000 THEN '< 1K' "
            + "WHEN rc.[Montant] < 10000 THEN '1K - 10K' "
            + "WHEN rc.[Montant] < 50000 THEN '10K - 50K' "
            + "WHEN rc.[Montant] < 100000 THEN '50K - 100K' "
            + "WHEN rc.[Montant] < 500000 THEN '100K - 500K' "
            + "ELSE '> 500K' END, rc.societe "
            + "ORDER BY MIN(rc.[Montant])",
        "params": PARAMS_DATE_SOCIETE,
        "category": "reglements_clients"
    },
    # --- 24. DASHBOARD: Encaissements Mensuels (chart) ---
    {
        "code": "DS_RGC_ENCAISSEMENTS_MENS",
        "nom": "Encaissements Mensuels",
        "query": "SELECT "
            + "CAST(YEAR(rc.[Date]) AS VARCHAR) + '-' + RIGHT('0' + CAST(MONTH(rc.[Date]) AS VARCHAR), 2) AS [Periode], "
            + "SUM(rc.[Montant]) AS [Total Encaisse], "
            + "COUNT(*) AS [Nb Reglements], "
            + "COUNT(DISTINCT rc.[Code client]) AS [Nb Clients], "
            + "AVG(rc.[Montant]) AS [Montant Moyen], "
            + "rc.societe AS [Societe] "
            + "FROM " + TBL + " rc "
            + "WHERE rc.[Date] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY CAST(YEAR(rc.[Date]) AS VARCHAR) + '-' + RIGHT('0' + CAST(MONTH(rc.[Date]) AS VARCHAR), 2), rc.societe "
            + "ORDER BY CAST(YEAR(rc.[Date]) AS VARCHAR) + '-' + RIGHT('0' + CAST(MONTH(rc.[Date]) AS VARCHAR), 2)",
        "params": PARAMS_DATE_SOCIETE,
        "category": "reglements_clients"
    },
    # --- 25. DASHBOARD: Synthese Annuelle Encaissements ---
    {
        "code": "DS_RGC_SYNTHESE_ANNUELLE",
        "nom": "Synth\u00e8se Annuelle Encaissements",
        "query": "SELECT "
            + "CAST(YEAR(rc.[Date]) AS VARCHAR) AS [Exercice], "
            + "COUNT(*) AS [Nb Reglements], "
            + "SUM(rc.[Montant]) AS [Total Encaisse], "
            + "SUM(rc.[solde]) AS [Total Solde], "
            + "AVG(rc.[Montant]) AS [Montant Moyen], "
            + "COUNT(DISTINCT rc.[Code client]) AS [Nb Clients], "
            + "SUM(CASE WHEN rc.[Impute] = 'Oui' THEN rc.[Montant] ELSE 0 END) AS [Total Impute], "
            + "SUM(CASE WHEN rc.[Impute] = 'Non' THEN rc.[Montant] ELSE 0 END) AS [Total Non Impute], "
            + "rc.societe AS [Societe] "
            + "FROM " + TBL + " rc "
            + "WHERE " + SOC + " "
            + "GROUP BY CAST(YEAR(rc.[Date]) AS VARCHAR), rc.societe "
            + "ORDER BY CAST(YEAR(rc.[Date]) AS VARCHAR)",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "reglements_clients"
    },
]

# ======================================================================
# 10 GRIDVIEWS
# ======================================================================
GRIDVIEWS = [
    ("DS_RGC_DETAIL_REGLEMENTS",  "D\u00e9tail R\u00e8glements Clients"),
    ("DS_RGC_NON_IMPUTES",        "R\u00e8glements Non Imput\u00e9s"),
    ("DS_RGC_SOLDE_NON_NUL",      "R\u00e8glements avec Solde Non Nul"),
    ("DS_RGC_PAR_CLIENT",         "Encaissements par Client"),
    ("DS_RGC_ECHEANCES",          "Ech\u00e9ances R\u00e8glements Clients"),
    ("DS_RGC_PAR_JOURNAL",        "R\u00e8glements par Journal"),
    ("DS_RGC_TOP_CLIENTS",        "Top 20 Clients Encaissements"),
    ("DS_RGC_PAR_COMPTE",         "R\u00e8glements par Compte G\u00e9n\u00e9ral"),
    ("DS_RGC_NON_VALIDES",        "R\u00e8glements Non Valid\u00e9s"),
    ("DS_RGC_PAR_PORTEFEUILLE",   "R\u00e8glements par Portefeuille"),
]

# ======================================================================
# 6 PIVOTS
# ======================================================================
PIVOTS = [
    ("DS_RGC_PIVOT_MODE", "Encaissements par Mode R\u00e8glement",
     [{"field": "Mode Reglement"}],
     [{"field": "Total Encaisse", "aggregation": "sum"}, {"field": "Nb Reglements", "aggregation": "sum"}],
     [{"field": "Societe"}]),
    ("DS_RGC_PIVOT_JOURNAL", "Encaissements par Journal",
     [{"field": "Journal"}],
     [{"field": "Total Encaisse", "aggregation": "sum"}, {"field": "Total Solde", "aggregation": "sum"}, {"field": "Nb Reglements", "aggregation": "sum"}],
     [{"field": "Societe"}]),
    ("DS_RGC_PIVOT_MENSUEL", "Encaissements Mensuels",
     [{"field": "Periode"}],
     [{"field": "Total Encaisse", "aggregation": "sum"}, {"field": "Nb Reglements", "aggregation": "sum"}, {"field": "Nb Clients", "aggregation": "sum"}],
     [{"field": "Societe"}]),
    ("DS_RGC_PIVOT_CLIENT_MODE", "Encaissements par Client et Mode",
     [{"field": "Client"}, {"field": "Mode Reglement"}],
     [{"field": "Total Encaisse", "aggregation": "sum"}, {"field": "Nb Reglements", "aggregation": "sum"}],
     [{"field": "Societe"}]),
    ("DS_RGC_PIVOT_ANNUEL", "Evolution Annuelle Encaissements",
     [{"field": "Exercice"}],
     [{"field": "Total Encaisse", "aggregation": "sum"}, {"field": "Total Solde", "aggregation": "sum"}, {"field": "Nb Clients", "aggregation": "sum"}],
     [{"field": "Societe"}]),
    ("DS_RGC_PIVOT_IMPUTATION", "Statut Imputation R\u00e8glements",
     [{"field": "Statut Imputation"}],
     [{"field": "Total Encaisse", "aggregation": "sum"}, {"field": "Nb Reglements", "aggregation": "sum"}, {"field": "Nb Clients", "aggregation": "sum"}],
     [{"field": "Societe"}]),
]

# ======================================================================
# 9 DASHBOARDS
# ======================================================================
DASHBOARDS = [
    ("DS_RGC_KPI_GLOBAL", "TB Encaissements Clients", [
        {"id": "w1", "type": "kpi", "title": "Total Encaiss\u00e9", "x": 0, "y": 0, "w": 3, "h": 3,
         "config": {"dataSourceCode": "DS_RGC_KPI_GLOBAL", "dataSourceOrigin": "template", "value_field": "Total Encaisse", "format": "currency", "suffix": " DH"}},
        {"id": "w2", "type": "kpi", "title": "Total Solde", "x": 3, "y": 0, "w": 3, "h": 3,
         "config": {"dataSourceCode": "DS_RGC_KPI_GLOBAL", "dataSourceOrigin": "template", "value_field": "Total Solde", "format": "currency", "suffix": " DH",
                    "conditional_color": [{"operator": ">", "value": 0, "color": "#f59e0b"}]}},
        {"id": "w3", "type": "kpi", "title": "Total Imput\u00e9", "x": 6, "y": 0, "w": 3, "h": 3,
         "config": {"dataSourceCode": "DS_RGC_KPI_GLOBAL", "dataSourceOrigin": "template", "value_field": "Total Impute", "format": "currency", "suffix": " DH"}},
        {"id": "w4", "type": "kpi", "title": "Taux Imputation", "x": 9, "y": 0, "w": 3, "h": 3,
         "config": {"dataSourceCode": "DS_RGC_KPI_GLOBAL", "dataSourceOrigin": "template", "value_field": "Taux Imputation", "format": "percent", "suffix": "%"}},
        {"id": "w5", "type": "kpi", "title": "Nb R\u00e8glements", "x": 0, "y": 3, "w": 3, "h": 3,
         "config": {"dataSourceCode": "DS_RGC_KPI_GLOBAL", "dataSourceOrigin": "template", "value_field": "Nb Reglements", "format": "number"}},
        {"id": "w6", "type": "kpi", "title": "Nb Clients", "x": 3, "y": 3, "w": 3, "h": 3,
         "config": {"dataSourceCode": "DS_RGC_KPI_GLOBAL", "dataSourceOrigin": "template", "value_field": "Nb Clients", "format": "number"}},
        {"id": "w7", "type": "kpi", "title": "Montant Moyen", "x": 6, "y": 3, "w": 3, "h": 3,
         "config": {"dataSourceCode": "DS_RGC_KPI_GLOBAL", "dataSourceOrigin": "template", "value_field": "Montant Moyen", "format": "currency", "suffix": " DH"}},
        {"id": "w8", "type": "kpi", "title": "Non Imput\u00e9s", "x": 9, "y": 3, "w": 3, "h": 3,
         "config": {"dataSourceCode": "DS_RGC_KPI_GLOBAL", "dataSourceOrigin": "template", "value_field": "Nb Non Imputes", "format": "number",
                    "conditional_color": [{"operator": ">", "value": 0, "color": "#f59e0b"}]}},
    ]),
    ("DS_RGC_EVOLUTION_MENSUELLE", "Evolution Mensuelle Encaissements", [
        {"id": "w1", "type": "bar", "title": "Encaissements Mensuels", "x": 0, "y": 0, "w": 12, "h": 8,
         "config": {"dataSourceCode": "DS_RGC_EVOLUTION_MENSUELLE", "dataSourceOrigin": "template", "category_field": "Periode", "value_fields": ["Total Encaisse"], "colors": ["#10b981"]}},
        {"id": "w2", "type": "line", "title": "Nb R\u00e8glements par Mois", "x": 0, "y": 8, "w": 12, "h": 6,
         "config": {"dataSourceCode": "DS_RGC_EVOLUTION_MENSUELLE", "dataSourceOrigin": "template", "category_field": "Periode", "value_fields": ["Nb Reglements"], "colors": ["#3b82f6"]}},
    ]),
    ("DS_RGC_REPARTITION_MODE", "R\u00e9partition Modes Encaissement", [
        {"id": "w1", "type": "pie", "title": "Par Mode R\u00e8glement", "x": 0, "y": 0, "w": 6, "h": 8,
         "config": {"dataSourceCode": "DS_RGC_REPARTITION_MODE", "dataSourceOrigin": "template", "category_field": "Mode Reglement", "value_field": "Total Encaisse"}},
        {"id": "w2", "type": "bar", "title": "Montant par Mode", "x": 6, "y": 0, "w": 6, "h": 8,
         "config": {"dataSourceCode": "DS_RGC_REPARTITION_MODE", "dataSourceOrigin": "template", "category_field": "Mode Reglement", "value_fields": ["Total Encaisse"], "colors": ["#10b981"]}},
    ]),
    ("DS_RGC_REPARTITION_JOURNAL", "R\u00e9partition par Journal Encaissements", [
        {"id": "w1", "type": "pie", "title": "Par Journal", "x": 0, "y": 0, "w": 6, "h": 8,
         "config": {"dataSourceCode": "DS_RGC_REPARTITION_JOURNAL", "dataSourceOrigin": "template", "category_field": "Journal", "value_field": "Total Encaisse"}},
        {"id": "w2", "type": "bar", "title": "Total par Journal", "x": 6, "y": 0, "w": 6, "h": 8,
         "config": {"dataSourceCode": "DS_RGC_REPARTITION_JOURNAL", "dataSourceOrigin": "template", "category_field": "Journal", "value_fields": ["Total Encaisse", "Total Solde"], "colors": ["#10b981", "#f59e0b"]}},
    ]),
    ("DS_RGC_TOP_CLIENTS_CHART", "Top Clients Encaissements", [
        {"id": "w1", "type": "bar", "title": "Top 15 Clients", "x": 0, "y": 0, "w": 12, "h": 8,
         "config": {"dataSourceCode": "DS_RGC_TOP_CLIENTS_CHART", "dataSourceOrigin": "template", "category_field": "Client", "value_fields": ["Total Encaisse"], "colors": ["#10b981"]}},
        {"id": "w2", "type": "table", "title": "D\u00e9tail Top Clients", "x": 0, "y": 8, "w": 12, "h": 6,
         "config": {"dataSourceCode": "DS_RGC_TOP_CLIENTS_CHART", "dataSourceOrigin": "template", "columns": ["Client", "Total Encaisse", "Nb Reglements"]}},
    ]),
    ("DS_RGC_STATUT_IMPUTATION", "Statut Imputation Encaissements", [
        {"id": "w1", "type": "pie", "title": "Imput\u00e9 vs Non Imput\u00e9", "x": 0, "y": 0, "w": 6, "h": 8,
         "config": {"dataSourceCode": "DS_RGC_STATUT_IMPUTATION", "dataSourceOrigin": "template", "category_field": "Statut", "value_field": "Total Encaisse"}},
        {"id": "w2", "type": "bar", "title": "Montant par Statut", "x": 6, "y": 0, "w": 6, "h": 8,
         "config": {"dataSourceCode": "DS_RGC_STATUT_IMPUTATION", "dataSourceOrigin": "template", "category_field": "Statut", "value_fields": ["Total Encaisse", "Total Solde"], "colors": ["#10b981", "#f59e0b"]}},
    ]),
    ("DS_RGC_TRANCHE_MONTANT", "Encaissements par Tranche Montant", [
        {"id": "w1", "type": "pie", "title": "Nb par Tranche", "x": 0, "y": 0, "w": 6, "h": 8,
         "config": {"dataSourceCode": "DS_RGC_TRANCHE_MONTANT", "dataSourceOrigin": "template", "category_field": "Tranche Montant", "value_field": "Nb Reglements"}},
        {"id": "w2", "type": "bar", "title": "Montant par Tranche", "x": 6, "y": 0, "w": 6, "h": 8,
         "config": {"dataSourceCode": "DS_RGC_TRANCHE_MONTANT", "dataSourceOrigin": "template", "category_field": "Tranche Montant", "value_fields": ["Total Encaisse"], "colors": ["#8b5cf6"]}},
    ]),
    ("DS_RGC_ENCAISSEMENTS_MENS", "Encaissements Mensuels Clients", [
        {"id": "w1", "type": "bar", "title": "Encaissements par Mois", "x": 0, "y": 0, "w": 12, "h": 8,
         "config": {"dataSourceCode": "DS_RGC_ENCAISSEMENTS_MENS", "dataSourceOrigin": "template", "category_field": "Periode", "value_fields": ["Total Encaisse"], "colors": ["#10b981"]}},
        {"id": "w2", "type": "line", "title": "Montant Moyen par Mois", "x": 0, "y": 8, "w": 12, "h": 6,
         "config": {"dataSourceCode": "DS_RGC_ENCAISSEMENTS_MENS", "dataSourceOrigin": "template", "category_field": "Periode", "value_fields": ["Montant Moyen"], "colors": ["#f59e0b"]}},
    ]),
    ("DS_RGC_SYNTHESE_ANNUELLE", "Synth\u00e8se Annuelle Encaissements", [
        {"id": "w1", "type": "bar", "title": "Encaissements par Ann\u00e9e", "x": 0, "y": 0, "w": 8, "h": 8,
         "config": {"dataSourceCode": "DS_RGC_SYNTHESE_ANNUELLE", "dataSourceOrigin": "template", "category_field": "Exercice", "value_fields": ["Total Encaisse", "Total Impute", "Total Non Impute"], "colors": ["#10b981", "#3b82f6", "#f59e0b"]}},
        {"id": "w2", "type": "line", "title": "Nb Clients", "x": 8, "y": 0, "w": 4, "h": 8,
         "config": {"dataSourceCode": "DS_RGC_SYNTHESE_ANNUELLE", "dataSourceOrigin": "template", "category_field": "Exercice", "value_fields": ["Nb Clients"], "colors": ["#8b5cf6"]}},
        {"id": "w3", "type": "table", "title": "D\u00e9tail par Ann\u00e9e", "x": 0, "y": 8, "w": 12, "h": 6,
         "config": {"dataSourceCode": "DS_RGC_SYNTHESE_ANNUELLE", "dataSourceOrigin": "template", "columns": ["Exercice", "Total Encaisse", "Total Solde", "Total Impute", "Total Non Impute", "Nb Reglements", "Nb Clients"]}},
    ]),
]

# ======================================================================
MENU_ICONS = {
    "D\u00e9tail R\u00e8glements Clients": "FileText",
    "R\u00e8glements Non Imput\u00e9s": "AlertTriangle",
    "R\u00e8glements avec Solde Non Nul": "Scale",
    "Encaissements par Client": "Users",
    "Ech\u00e9ances R\u00e8glements Clients": "CalendarClock",
    "R\u00e8glements par Journal": "BookOpen",
    "Top 20 Clients Encaissements": "Award",
    "R\u00e8glements par Compte G\u00e9n\u00e9ral": "Calculator",
    "R\u00e8glements Non Valid\u00e9s": "XCircle",
    "R\u00e8glements par Portefeuille": "Briefcase",
    "Encaissements par Mode R\u00e8glement": "CreditCard",
    "Encaissements par Journal": "BookOpen",
    "Encaissements Mensuels (Pivot)": "Calendar",
    "Encaissements par Client et Mode": "Layers",
    "Evolution Annuelle Encaissements": "TrendingUp",
    "Statut Imputation R\u00e8glements": "CheckCircle",
    "TB Encaissements Clients": "LayoutGrid",
    "Evolution Mensuelle Encaissements": "TrendingUp",
    "R\u00e9partition Modes Encaissement": "PieChart",
    "R\u00e9partition par Journal Encaissements": "PieChart",
    "Top Clients Encaissements": "Award",
    "Statut Imputation Encaissements": "CheckCircle",
    "Encaissements par Tranche Montant": "BarChart3",
    "Encaissements Mensuels Clients": "Banknote",
    "Synth\u00e8se Annuelle Encaissements": "CalendarDays",
}

# ======================================================================
# MAIN
# ======================================================================
def main():
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()
    print("=" * 60)
    print("  CREATION DES 25 RAPPORTS REGLEMENTS CLIENTS")
    print("=" * 60)

    # --- 1. DataSource Templates ---
    print("\n[1/5] Creation des DataSource Templates...")
    ds_ids = {}
    for ds in DS_TEMPLATES:
        cursor.execute("SELECT id FROM APP_DataSources_Templates WHERE code = ?", ds["code"])
        existing = cursor.fetchone()
        if existing:
            cursor.execute("UPDATE APP_DataSources_Templates SET nom=?, query_template=?, parameters=?, category=?, actif=1 WHERE code=?",
                ds["nom"], ds["query"], ds["params"], ds["category"], ds["code"])
            ds_ids[ds["code"]] = existing[0]
            print(f"  OK MAJ {ds['code']} (id={existing[0]})")
        else:
            cursor.execute("INSERT INTO APP_DataSources_Templates (code, nom, description, query_template, parameters, category, actif) VALUES (?, ?, ?, ?, ?, ?, 1)",
                ds["code"], ds["nom"], ds["nom"], ds["query"], ds["params"], ds["category"])
            cursor.execute("SELECT @@IDENTITY")
            new_id = int(cursor.fetchone()[0])
            ds_ids[ds["code"]] = new_id
            print(f"  + NEW {ds['code']} (id={new_id})")
    conn.commit()
    print(f"  => {len(DS_TEMPLATES)} templates traites")

    # --- 2. GridViews ---
    print("\n[2/5] Creation des GridViews...")
    gv_ids = {}
    for ds_code, nom in GRIDVIEWS:
        cursor.execute("SELECT id FROM APP_GridViews WHERE data_source_code = ?", ds_code)
        existing = cursor.fetchone()
        if existing:
            gv_ids[ds_code] = existing[0]
            print(f"  OK EXISTS {nom} (id={existing[0]})")
            continue
        cursor.execute("SELECT query_template FROM APP_DataSources_Templates WHERE code = ?", ds_code)
        row = cursor.fetchone()
        if not row: continue
        query = row[0]
        aliases = re.findall(r'AS\s+\[([^\]]+)\]', query, re.IGNORECASE)
        columns = []
        for alias in aliases:
            if alias.lower() in ('societe',): continue
            fmt = "text"
            low = alias.lower()
            if any(k in low for k in ("montant", "solde", "reste", "total", "impute", "encaiss", "moyen")):
                fmt = "currency"
            elif any(k in low for k in ("nb ", "nombre", "jours", "delai", "retard", "taux", "part")):
                fmt = "number"
            elif "date" in low: fmt = "date"
            columns.append({"field": alias, "header": alias, "format": fmt, "sortable": True, "filterable": True, "width": 150})
        total_cols = [c["field"] for c in columns if c["format"] in ("currency", "number") and "nb " not in c["field"].lower()]
        features_json = json.dumps({"show_search": True, "show_column_filters": True, "show_grouping": True, "show_column_toggle": True, "show_export": True, "show_pagination": True, "allow_sorting": True})
        cursor.execute("INSERT INTO APP_GridViews (nom, description, data_source_code, columns_config, page_size, show_totals, total_columns, features, actif) VALUES (?, ?, ?, ?, 25, 1, ?, ?, 1)",
            nom, f"Rapport Encaissements - {nom}", ds_code, json.dumps(columns), json.dumps(total_cols[:5]), features_json)
        cursor.execute("SELECT @@IDENTITY")
        gv_id = int(cursor.fetchone()[0])
        gv_ids[ds_code] = gv_id
        print(f"  + NEW GridView {nom} (id={gv_id}, {len(columns)} cols)")
    conn.commit()

    # --- 3. Pivots ---
    print("\n[3/5] Creation des Pivots V2...")
    pv_ids = {}
    for ds_code, nom, rows_cfg, vals_cfg, filters_cfg in PIVOTS:
        cursor.execute("SELECT id FROM APP_Pivots_V2 WHERE data_source_code = ?", ds_code)
        existing = cursor.fetchone()
        if existing:
            pv_ids[ds_code] = existing[0]
            print(f"  OK EXISTS {nom} (id={existing[0]})")
            continue
        cursor.execute("INSERT INTO APP_Pivots_V2 (nom, description, data_source_code, rows_config, columns_config, values_config, filters_config, show_grand_totals, show_subtotals) VALUES (?, ?, ?, ?, '[]', ?, ?, 1, 1)",
            nom, f"Pivot Encaissements - {nom}", ds_code, json.dumps(rows_cfg), json.dumps(vals_cfg), json.dumps(filters_cfg))
        cursor.execute("SELECT @@IDENTITY")
        pv_id = int(cursor.fetchone()[0])
        pv_ids[ds_code] = pv_id
        print(f"  + NEW Pivot {nom} (id={pv_id})")
    conn.commit()

    # --- 4. Dashboards ---
    print("\n[4/5] Creation des Dashboards...")
    db_ids = {}
    for ds_code, nom, widgets in DASHBOARDS:
        cursor.execute("SELECT id FROM APP_Dashboards WHERE nom = ?", nom)
        existing = cursor.fetchone()
        if existing:
            db_ids[ds_code] = existing[0]
            print(f"  OK EXISTS {nom} (id={existing[0]})")
            continue
        cursor.execute("INSERT INTO APP_Dashboards (nom, description, widgets, actif) VALUES (?, ?, ?, 1)",
            nom, f"Dashboard Encaissements - {nom}", json.dumps(widgets))
        cursor.execute("SELECT @@IDENTITY")
        db_id = int(cursor.fetchone()[0])
        db_ids[ds_code] = db_id
        print(f"  + NEW Dashboard {nom} (id={db_id})")
    conn.commit()

    # --- 5. Menus ---
    print("\n[5/5] Creation des Menus...")
    cursor.execute("SELECT id FROM APP_Menus WHERE nom = 'R\u00e8glements Clients' AND parent_id IS NULL")
    root = cursor.fetchone()
    if root:
        root_id = root[0]
        print(f"  OK EXISTS racine (id={root_id})")
    else:
        cursor.execute("INSERT INTO APP_Menus (nom, icon, type, parent_id, ordre, actif) VALUES ('R\u00e8glements Clients', 'Receipt', 'folder', NULL, 60, 1)")
        cursor.execute("SELECT @@IDENTITY")
        root_id = int(cursor.fetchone()[0])
        print(f"  + NEW racine 'R\u00e8glements Clients' (id={root_id})")

    subfolders = [("Suivi des Encaissements", "FileText", 1), ("Analyses Encaissements", "BarChart3", 2), ("Tableaux de Bord", "LayoutGrid", 3)]
    sf_ids = {}
    for sf_label, sf_icon, sf_ordre in subfolders:
        cursor.execute("SELECT id FROM APP_Menus WHERE nom = ? AND parent_id = ?", sf_label, root_id)
        existing = cursor.fetchone()
        if existing:
            sf_ids[sf_label] = existing[0]
        else:
            cursor.execute("INSERT INTO APP_Menus (nom, icon, type, parent_id, ordre, actif) VALUES (?, ?, 'folder', ?, ?, 1)", sf_label, sf_icon, root_id, sf_ordre)
            cursor.execute("SELECT @@IDENTITY")
            sf_ids[sf_label] = int(cursor.fetchone()[0])
            print(f"  + NEW dossier '{sf_label}' (id={sf_ids[sf_label]})")

    menu_items = [
        ("Suivi des Encaissements", "D\u00e9tail R\u00e8glements Clients", "gridview", gv_ids.get("DS_RGC_DETAIL_REGLEMENTS"), 1),
        ("Suivi des Encaissements", "R\u00e8glements Non Imput\u00e9s", "gridview", gv_ids.get("DS_RGC_NON_IMPUTES"), 2),
        ("Suivi des Encaissements", "R\u00e8glements avec Solde Non Nul", "gridview", gv_ids.get("DS_RGC_SOLDE_NON_NUL"), 3),
        ("Suivi des Encaissements", "Encaissements par Client", "gridview", gv_ids.get("DS_RGC_PAR_CLIENT"), 4),
        ("Suivi des Encaissements", "Ech\u00e9ances R\u00e8glements Clients", "gridview", gv_ids.get("DS_RGC_ECHEANCES"), 5),
        ("Suivi des Encaissements", "R\u00e8glements par Journal", "gridview", gv_ids.get("DS_RGC_PAR_JOURNAL"), 6),
        ("Suivi des Encaissements", "Top 20 Clients Encaissements", "gridview", gv_ids.get("DS_RGC_TOP_CLIENTS"), 7),
        ("Suivi des Encaissements", "R\u00e8glements par Compte G\u00e9n\u00e9ral", "gridview", gv_ids.get("DS_RGC_PAR_COMPTE"), 8),
        ("Suivi des Encaissements", "R\u00e8glements Non Valid\u00e9s", "gridview", gv_ids.get("DS_RGC_NON_VALIDES"), 9),
        ("Suivi des Encaissements", "R\u00e8glements par Portefeuille", "gridview", gv_ids.get("DS_RGC_PAR_PORTEFEUILLE"), 10),
        ("Analyses Encaissements", "Encaissements par Mode R\u00e8glement", "pivot-v2", pv_ids.get("DS_RGC_PIVOT_MODE"), 1),
        ("Analyses Encaissements", "Encaissements par Journal", "pivot-v2", pv_ids.get("DS_RGC_PIVOT_JOURNAL"), 2),
        ("Analyses Encaissements", "Encaissements Mensuels (Pivot)", "pivot-v2", pv_ids.get("DS_RGC_PIVOT_MENSUEL"), 3),
        ("Analyses Encaissements", "Encaissements par Client et Mode", "pivot-v2", pv_ids.get("DS_RGC_PIVOT_CLIENT_MODE"), 4),
        ("Analyses Encaissements", "Evolution Annuelle Encaissements", "pivot-v2", pv_ids.get("DS_RGC_PIVOT_ANNUEL"), 5),
        ("Analyses Encaissements", "Statut Imputation R\u00e8glements", "pivot-v2", pv_ids.get("DS_RGC_PIVOT_IMPUTATION"), 6),
        ("Tableaux de Bord", "TB Encaissements Clients", "dashboard", db_ids.get("DS_RGC_KPI_GLOBAL"), 1),
        ("Tableaux de Bord", "Evolution Mensuelle Encaissements", "dashboard", db_ids.get("DS_RGC_EVOLUTION_MENSUELLE"), 2),
        ("Tableaux de Bord", "R\u00e9partition Modes Encaissement", "dashboard", db_ids.get("DS_RGC_REPARTITION_MODE"), 3),
        ("Tableaux de Bord", "R\u00e9partition par Journal Encaissements", "dashboard", db_ids.get("DS_RGC_REPARTITION_JOURNAL"), 4),
        ("Tableaux de Bord", "Top Clients Encaissements", "dashboard", db_ids.get("DS_RGC_TOP_CLIENTS_CHART"), 5),
        ("Tableaux de Bord", "Statut Imputation Encaissements", "dashboard", db_ids.get("DS_RGC_STATUT_IMPUTATION"), 6),
        ("Tableaux de Bord", "Encaissements par Tranche Montant", "dashboard", db_ids.get("DS_RGC_TRANCHE_MONTANT"), 7),
        ("Tableaux de Bord", "Encaissements Mensuels Clients", "dashboard", db_ids.get("DS_RGC_ENCAISSEMENTS_MENS"), 8),
        ("Tableaux de Bord", "Synth\u00e8se Annuelle Encaissements", "dashboard", db_ids.get("DS_RGC_SYNTHESE_ANNUELLE"), 9),
    ]

    menu_count = 0
    for sf_label, label, menu_type, target_id, ordre in menu_items:
        if target_id is None:
            print(f"  XX SKIP menu '{label}' - target_id manquant")
            continue
        parent_id = sf_ids[sf_label]
        icon = MENU_ICONS.get(label, "FileText")
        cursor.execute("SELECT id FROM APP_Menus WHERE nom = ? AND parent_id = ?", label, parent_id)
        existing = cursor.fetchone()
        if existing:
            cursor.execute("UPDATE APP_Menus SET icon=?, type=?, target_id=?, ordre=?, actif=1 WHERE id=?", icon, menu_type, target_id, ordre, existing[0])
        else:
            cursor.execute("INSERT INTO APP_Menus (nom, icon, type, target_id, parent_id, ordre, actif) VALUES (?, ?, ?, ?, ?, ?, 1)", label, icon, menu_type, target_id, parent_id, ordre)
            print(f"  + NEW '{label}' ({menu_type} -> id {target_id})")
        menu_count += 1
    conn.commit()

    print("\n" + "=" * 60)
    print("  RESUME")
    print("=" * 60)
    print(f"  DataSource Templates : {len(DS_TEMPLATES)}")
    print(f"  GridViews            : {len(GRIDVIEWS)}")
    print(f"  Pivots V2            : {len(PIVOTS)}")
    print(f"  Dashboards           : {len(DASHBOARDS)}")
    print(f"  Menus                : {menu_count} items + 1 racine + {len(subfolders)} dossiers")
    print("=" * 60)
    conn.close()
    print("\n[OK] Done!")

if __name__ == "__main__":
    main()
