# -*- coding: utf-8 -*-
"""
Creation des 25 rapports du cycle PAIEMENTS FOURNISSEURS pour OptiBoard
10 GRID + 6 PIVOT + 9 DASHBOARD
Table source: Paiements_Fournisseurs (DWH)
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

# Unicode column names for Paiements_Fournisseurs (pf):
#   Intitul\u00e9, Date d'\u00e9ch\u00e9ance, R\u00e9f\u00e9rence, Libell\u00e9
#   Comptabilis\u00e9, Compte g\u00e9n\u00e9rale, N\u00b0 pi\u00e9ce
#   Mode r\u00e9glement, N\u00b0 interne, Code r\u00e9glement, Date cr\u00e9ation
#   Valide = 'Ou'/'Non', Impute = 'Oui'/'Non'

SOC = "(@societe IS NULL OR pf.societe = @societe)"

# ======================================================================
# 25 DATASOURCE TEMPLATES
# ======================================================================
DS_TEMPLATES = [
    # --- 1. GRID: Detail Paiements Fournisseurs ---
    {
        "code": "DS_PAF_DETAIL_PAIEMENTS",
        "nom": "D\u00e9tail Paiements Fournisseurs",
        "query": "SELECT "
            + "pf.[Code fournisseur], pf.[Intitul\u00e9] AS [Fournisseur], "
            + "pf.[Date], pf.[Date d'\u00e9ch\u00e9ance] AS [Date Echeance], "
            + "pf.[R\u00e9f\u00e9rence] AS [Reference], pf.[Libell\u00e9] AS [Libelle], "
            + "pf.[Code journal], pf.[Journal], "
            + "pf.[Compte g\u00e9n\u00e9rale] AS [Compte General], "
            + "pf.[N\u00b0 pi\u00e9ce] AS [Num Piece], "
            + "pf.[Mode r\u00e9glement] AS [Mode Reglement], "
            + "pf.[Montant], pf.[solde] AS [Solde], "
            + "pf.[Devise], pf.[Valide], pf.[Impute], "
            + "pf.societe AS [Societe] "
            + "FROM Paiements_Fournisseurs pf "
            + "WHERE pf.[Date] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "ORDER BY pf.[Date] DESC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "paiements_fournisseurs"
    },
    # --- 2. GRID: Paiements Non Imputes ---
    {
        "code": "DS_PAF_NON_IMPUTES",
        "nom": "Paiements Non Imput\u00e9s",
        "query": "SELECT "
            + "pf.[Code fournisseur], pf.[Intitul\u00e9] AS [Fournisseur], "
            + "pf.[Date], pf.[Date d'\u00e9ch\u00e9ance] AS [Date Echeance], "
            + "pf.[R\u00e9f\u00e9rence] AS [Reference], pf.[Libell\u00e9] AS [Libelle], "
            + "pf.[Journal], pf.[N\u00b0 pi\u00e9ce] AS [Num Piece], "
            + "pf.[Mode r\u00e9glement] AS [Mode Reglement], "
            + "pf.[Montant], pf.[solde] AS [Solde], "
            + "DATEDIFF(day, pf.[Date], GETDATE()) AS [Jours Depuis Paiement], "
            + "pf.societe AS [Societe] "
            + "FROM Paiements_Fournisseurs pf "
            + "WHERE pf.[Impute] = 'Non' "
            + "AND " + SOC + " "
            + "ORDER BY pf.[Montant] DESC",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "paiements_fournisseurs"
    },
    # --- 3. GRID: Paiements avec Solde Non Nul ---
    {
        "code": "DS_PAF_SOLDE_NON_NUL",
        "nom": "Paiements avec Solde Non Nul",
        "query": "SELECT "
            + "pf.[Code fournisseur], pf.[Intitul\u00e9] AS [Fournisseur], "
            + "pf.[Date], pf.[Date d'\u00e9ch\u00e9ance] AS [Date Echeance], "
            + "pf.[R\u00e9f\u00e9rence] AS [Reference], pf.[Libell\u00e9] AS [Libelle], "
            + "pf.[Journal], pf.[N\u00b0 pi\u00e9ce] AS [Num Piece], "
            + "pf.[Mode r\u00e9glement] AS [Mode Reglement], "
            + "pf.[Montant], pf.[solde] AS [Solde], "
            + "pf.[Montant] - pf.[solde] AS [Montant Impute], "
            + "pf.societe AS [Societe] "
            + "FROM Paiements_Fournisseurs pf "
            + "WHERE ABS(pf.[solde]) > 0.01 "
            + "AND " + SOC + " "
            + "ORDER BY ABS(pf.[solde]) DESC",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "paiements_fournisseurs"
    },
    # --- 4. GRID: Paiements par Fournisseur (Synthese) ---
    {
        "code": "DS_PAF_PAR_FOURNISSEUR",
        "nom": "Paiements par Fournisseur",
        "query": "SELECT "
            + "pf.[Code fournisseur], pf.[Intitul\u00e9] AS [Fournisseur], "
            + "COUNT(*) AS [Nb Paiements], "
            + "SUM(pf.[Montant]) AS [Total Paye], "
            + "SUM(pf.[solde]) AS [Total Solde], "
            + "AVG(pf.[Montant]) AS [Montant Moyen], "
            + "MIN(pf.[Date]) AS [Premier Paiement], "
            + "MAX(pf.[Date]) AS [Dernier Paiement], "
            + "pf.societe AS [Societe] "
            + "FROM Paiements_Fournisseurs pf "
            + "WHERE pf.[Date] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY pf.[Code fournisseur], pf.[Intitul\u00e9], pf.societe "
            + "ORDER BY SUM(pf.[Montant]) DESC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "paiements_fournisseurs"
    },
    # --- 5. GRID: Echeances Fournisseurs ---
    {
        "code": "DS_PAF_ECHEANCES",
        "nom": "Ech\u00e9ances Paiements Fournisseurs",
        "query": "SELECT "
            + "pf.[Code fournisseur], pf.[Intitul\u00e9] AS [Fournisseur], "
            + "pf.[Date], pf.[Date d'\u00e9ch\u00e9ance] AS [Date Echeance], "
            + "pf.[R\u00e9f\u00e9rence] AS [Reference], pf.[Libell\u00e9] AS [Libelle], "
            + "pf.[Mode r\u00e9glement] AS [Mode Reglement], "
            + "pf.[Montant], pf.[solde] AS [Solde], "
            + "CASE WHEN pf.[Date d'\u00e9ch\u00e9ance] < GETDATE() AND ABS(pf.[solde]) > 0.01 THEN 'Echu Impaye' "
            + "WHEN pf.[Date d'\u00e9ch\u00e9ance] < GETDATE() THEN 'Echu Paye' "
            + "WHEN pf.[Date d'\u00e9ch\u00e9ance] >= GETDATE() THEN 'Non Echu' "
            + "ELSE 'Sans Echeance' END AS [Statut Echeance], "
            + "pf.societe AS [Societe] "
            + "FROM Paiements_Fournisseurs pf "
            + "WHERE pf.[Date d'\u00e9ch\u00e9ance] IS NOT NULL "
            + "AND pf.[Date] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "ORDER BY pf.[Date d'\u00e9ch\u00e9ance] ASC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "paiements_fournisseurs"
    },
    # --- 6. GRID: Paiements par Journal ---
    {
        "code": "DS_PAF_PAR_JOURNAL",
        "nom": "Paiements par Journal",
        "query": "SELECT "
            + "pf.[Code journal], pf.[Journal], "
            + "COUNT(*) AS [Nb Paiements], "
            + "SUM(pf.[Montant]) AS [Total Paye], "
            + "SUM(pf.[solde]) AS [Total Solde], "
            + "AVG(pf.[Montant]) AS [Montant Moyen], "
            + "COUNT(DISTINCT pf.[Code fournisseur]) AS [Nb Fournisseurs], "
            + "pf.societe AS [Societe] "
            + "FROM Paiements_Fournisseurs pf "
            + "WHERE pf.[Date] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY pf.[Code journal], pf.[Journal], pf.societe "
            + "ORDER BY SUM(pf.[Montant]) DESC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "paiements_fournisseurs"
    },
    # --- 7. GRID: Paiements par Compte General ---
    {
        "code": "DS_PAF_PAR_COMPTE",
        "nom": "Paiements par Compte G\u00e9n\u00e9ral",
        "query": "SELECT "
            + "pf.[Compte g\u00e9n\u00e9rale] AS [Compte General], "
            + "COUNT(*) AS [Nb Paiements], "
            + "SUM(pf.[Montant]) AS [Total Paye], "
            + "SUM(pf.[solde]) AS [Total Solde], "
            + "COUNT(DISTINCT pf.[Code fournisseur]) AS [Nb Fournisseurs], "
            + "pf.societe AS [Societe] "
            + "FROM Paiements_Fournisseurs pf "
            + "WHERE pf.[Date] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY pf.[Compte g\u00e9n\u00e9rale], pf.societe "
            + "ORDER BY SUM(pf.[Montant]) DESC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "paiements_fournisseurs"
    },
    # --- 8. GRID: Top 20 Fournisseurs Payes ---
    {
        "code": "DS_PAF_TOP_FOURNISSEURS",
        "nom": "Top 20 Fournisseurs Pay\u00e9s",
        "query": "SELECT TOP 20 "
            + "pf.[Code fournisseur], pf.[Intitul\u00e9] AS [Fournisseur], "
            + "COUNT(*) AS [Nb Paiements], "
            + "SUM(pf.[Montant]) AS [Total Paye], "
            + "SUM(pf.[solde]) AS [Total Solde], "
            + "AVG(pf.[Montant]) AS [Montant Moyen], "
            + "MAX(pf.[Date]) AS [Dernier Paiement], "
            + "pf.societe AS [Societe] "
            + "FROM Paiements_Fournisseurs pf "
            + "WHERE pf.[Date] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY pf.[Code fournisseur], pf.[Intitul\u00e9], pf.societe "
            + "ORDER BY SUM(pf.[Montant]) DESC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "paiements_fournisseurs"
    },
    # --- 9. GRID: Paiements Non Valides ---
    {
        "code": "DS_PAF_NON_VALIDES",
        "nom": "Paiements Non Valid\u00e9s",
        "query": "SELECT "
            + "pf.[Code fournisseur], pf.[Intitul\u00e9] AS [Fournisseur], "
            + "pf.[Date], pf.[R\u00e9f\u00e9rence] AS [Reference], "
            + "pf.[Libell\u00e9] AS [Libelle], "
            + "pf.[Journal], pf.[N\u00b0 pi\u00e9ce] AS [Num Piece], "
            + "pf.[Mode r\u00e9glement] AS [Mode Reglement], "
            + "pf.[Montant], pf.[solde] AS [Solde], "
            + "pf.[Valide], pf.[Impute], "
            + "pf.societe AS [Societe] "
            + "FROM Paiements_Fournisseurs pf "
            + "WHERE pf.[Valide] = 'Non' "
            + "AND " + SOC + " "
            + "ORDER BY pf.[Date] DESC",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "paiements_fournisseurs"
    },
    # --- 10. GRID: Delai Moyen Paiement ---
    {
        "code": "DS_PAF_DELAI_PAIEMENT",
        "nom": "D\u00e9lai Moyen de Paiement",
        "query": "SELECT "
            + "pf.[Code fournisseur], pf.[Intitul\u00e9] AS [Fournisseur], "
            + "COUNT(*) AS [Nb Paiements], "
            + "SUM(pf.[Montant]) AS [Total Paye], "
            + "AVG(DATEDIFF(day, pf.[Date], pf.[Date d'\u00e9ch\u00e9ance])) AS [Delai Moyen Jours], "
            + "MIN(DATEDIFF(day, pf.[Date], pf.[Date d'\u00e9ch\u00e9ance])) AS [Delai Min], "
            + "MAX(DATEDIFF(day, pf.[Date], pf.[Date d'\u00e9ch\u00e9ance])) AS [Delai Max], "
            + "pf.societe AS [Societe] "
            + "FROM Paiements_Fournisseurs pf "
            + "WHERE pf.[Date d'\u00e9ch\u00e9ance] IS NOT NULL "
            + "AND pf.[Date] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY pf.[Code fournisseur], pf.[Intitul\u00e9], pf.societe "
            + "ORDER BY AVG(DATEDIFF(day, pf.[Date], pf.[Date d'\u00e9ch\u00e9ance])) DESC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "paiements_fournisseurs"
    },
    # --- 11. PIVOT: Paiements par Mode Reglement ---
    {
        "code": "DS_PAF_PIVOT_MODE",
        "nom": "Paiements par Mode R\u00e8glement",
        "query": "SELECT "
            + "ISNULL(pf.[Mode r\u00e9glement], 'Non d\u00e9fini') AS [Mode Reglement], "
            + "COUNT(*) AS [Nb Paiements], "
            + "SUM(pf.[Montant]) AS [Total Paye], "
            + "AVG(pf.[Montant]) AS [Montant Moyen], "
            + "COUNT(DISTINCT pf.[Code fournisseur]) AS [Nb Fournisseurs], "
            + "pf.societe AS [Societe] "
            + "FROM Paiements_Fournisseurs pf "
            + "WHERE pf.[Date] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY ISNULL(pf.[Mode r\u00e9glement], 'Non d\u00e9fini'), pf.societe",
        "params": PARAMS_DATE_SOCIETE,
        "category": "paiements_fournisseurs"
    },
    # --- 12. PIVOT: Paiements par Journal ---
    {
        "code": "DS_PAF_PIVOT_JOURNAL",
        "nom": "Paiements par Journal",
        "query": "SELECT "
            + "pf.[Code journal], pf.[Journal], "
            + "COUNT(*) AS [Nb Paiements], "
            + "SUM(pf.[Montant]) AS [Total Paye], "
            + "SUM(pf.[solde]) AS [Total Solde], "
            + "COUNT(DISTINCT pf.[Code fournisseur]) AS [Nb Fournisseurs], "
            + "pf.societe AS [Societe] "
            + "FROM Paiements_Fournisseurs pf "
            + "WHERE pf.[Date] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY pf.[Code journal], pf.[Journal], pf.societe",
        "params": PARAMS_DATE_SOCIETE,
        "category": "paiements_fournisseurs"
    },
    # --- 13. PIVOT: Paiements Mensuels ---
    {
        "code": "DS_PAF_PIVOT_MENSUEL",
        "nom": "Paiements Mensuels",
        "query": "SELECT "
            + "CAST(YEAR(pf.[Date]) AS VARCHAR) + '-' + RIGHT('0' + CAST(MONTH(pf.[Date]) AS VARCHAR), 2) AS [Periode], "
            + "COUNT(*) AS [Nb Paiements], "
            + "SUM(pf.[Montant]) AS [Total Paye], "
            + "SUM(pf.[solde]) AS [Total Solde], "
            + "COUNT(DISTINCT pf.[Code fournisseur]) AS [Nb Fournisseurs], "
            + "pf.societe AS [Societe] "
            + "FROM Paiements_Fournisseurs pf "
            + "WHERE pf.[Date] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY CAST(YEAR(pf.[Date]) AS VARCHAR) + '-' + RIGHT('0' + CAST(MONTH(pf.[Date]) AS VARCHAR), 2), pf.societe "
            + "ORDER BY CAST(YEAR(pf.[Date]) AS VARCHAR) + '-' + RIGHT('0' + CAST(MONTH(pf.[Date]) AS VARCHAR), 2)",
        "params": PARAMS_DATE_SOCIETE,
        "category": "paiements_fournisseurs"
    },
    # --- 14. PIVOT: Paiements par Fournisseur et Mode ---
    {
        "code": "DS_PAF_PIVOT_FOURN_MODE",
        "nom": "Paiements par Fournisseur et Mode",
        "query": "SELECT "
            + "pf.[Code fournisseur], pf.[Intitul\u00e9] AS [Fournisseur], "
            + "ISNULL(pf.[Mode r\u00e9glement], 'Non d\u00e9fini') AS [Mode Reglement], "
            + "COUNT(*) AS [Nb Paiements], "
            + "SUM(pf.[Montant]) AS [Total Paye], "
            + "pf.societe AS [Societe] "
            + "FROM Paiements_Fournisseurs pf "
            + "WHERE pf.[Date] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY pf.[Code fournisseur], pf.[Intitul\u00e9], ISNULL(pf.[Mode r\u00e9glement], 'Non d\u00e9fini'), pf.societe",
        "params": PARAMS_DATE_SOCIETE,
        "category": "paiements_fournisseurs"
    },
    # --- 15. PIVOT: Evolution Annuelle Paiements ---
    {
        "code": "DS_PAF_PIVOT_ANNUEL",
        "nom": "Evolution Annuelle Paiements",
        "query": "SELECT "
            + "CAST(YEAR(pf.[Date]) AS VARCHAR) AS [Exercice], "
            + "COUNT(*) AS [Nb Paiements], "
            + "SUM(pf.[Montant]) AS [Total Paye], "
            + "SUM(pf.[solde]) AS [Total Solde], "
            + "AVG(pf.[Montant]) AS [Montant Moyen], "
            + "COUNT(DISTINCT pf.[Code fournisseur]) AS [Nb Fournisseurs], "
            + "pf.societe AS [Societe] "
            + "FROM Paiements_Fournisseurs pf "
            + "WHERE " + SOC + " "
            + "GROUP BY CAST(YEAR(pf.[Date]) AS VARCHAR), pf.societe "
            + "ORDER BY CAST(YEAR(pf.[Date]) AS VARCHAR)",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "paiements_fournisseurs"
    },
    # --- 16. PIVOT: Impute vs Non Impute ---
    {
        "code": "DS_PAF_PIVOT_IMPUTATION",
        "nom": "Statut Imputation Paiements",
        "query": "SELECT "
            + "pf.[Impute] AS [Statut Imputation], "
            + "COUNT(*) AS [Nb Paiements], "
            + "SUM(pf.[Montant]) AS [Total Paye], "
            + "SUM(pf.[solde]) AS [Total Solde], "
            + "COUNT(DISTINCT pf.[Code fournisseur]) AS [Nb Fournisseurs], "
            + "pf.societe AS [Societe] "
            + "FROM Paiements_Fournisseurs pf "
            + "WHERE pf.[Date] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY pf.[Impute], pf.societe",
        "params": PARAMS_DATE_SOCIETE,
        "category": "paiements_fournisseurs"
    },
    # --- 17. DASHBOARD: KPIs Globaux Paiements ---
    {
        "code": "DS_PAF_KPI_GLOBAL",
        "nom": "KPIs Paiements Fournisseurs",
        "query": "SELECT "
            + "COUNT(*) AS [Nb Paiements], "
            + "SUM(pf.[Montant]) AS [Total Paye], "
            + "SUM(pf.[solde]) AS [Total Solde], "
            + "SUM(pf.[Montant]) - SUM(pf.[solde]) AS [Total Impute], "
            + "CASE WHEN SUM(pf.[Montant]) > 0 THEN ROUND((SUM(pf.[Montant]) - SUM(pf.[solde])) * 100.0 / SUM(pf.[Montant]), 2) ELSE 0 END AS [Taux Imputation], "
            + "COUNT(DISTINCT pf.[Code fournisseur]) AS [Nb Fournisseurs], "
            + "AVG(pf.[Montant]) AS [Montant Moyen], "
            + "SUM(CASE WHEN pf.[Impute] = 'Non' THEN 1 ELSE 0 END) AS [Nb Non Imputes], "
            + "pf.societe AS [Societe] "
            + "FROM Paiements_Fournisseurs pf "
            + "WHERE pf.[Date] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY pf.societe",
        "params": PARAMS_DATE_SOCIETE,
        "category": "paiements_fournisseurs"
    },
    # --- 18. DASHBOARD: Evolution Mensuelle ---
    {
        "code": "DS_PAF_EVOLUTION_MENSUELLE",
        "nom": "Evolution Mensuelle Paiements",
        "query": "SELECT "
            + "CAST(YEAR(pf.[Date]) AS VARCHAR) + '-' + RIGHT('0' + CAST(MONTH(pf.[Date]) AS VARCHAR), 2) AS [Periode], "
            + "SUM(pf.[Montant]) AS [Total Paye], "
            + "SUM(pf.[solde]) AS [Total Solde], "
            + "COUNT(*) AS [Nb Paiements], "
            + "COUNT(DISTINCT pf.[Code fournisseur]) AS [Nb Fournisseurs], "
            + "pf.societe AS [Societe] "
            + "FROM Paiements_Fournisseurs pf "
            + "WHERE pf.[Date] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY CAST(YEAR(pf.[Date]) AS VARCHAR) + '-' + RIGHT('0' + CAST(MONTH(pf.[Date]) AS VARCHAR), 2), pf.societe "
            + "ORDER BY CAST(YEAR(pf.[Date]) AS VARCHAR) + '-' + RIGHT('0' + CAST(MONTH(pf.[Date]) AS VARCHAR), 2)",
        "params": PARAMS_DATE_SOCIETE,
        "category": "paiements_fournisseurs"
    },
    # --- 19. DASHBOARD: Repartition par Mode ---
    {
        "code": "DS_PAF_REPARTITION_MODE",
        "nom": "R\u00e9partition par Mode Paiement",
        "query": "SELECT "
            + "ISNULL(pf.[Mode r\u00e9glement], 'Non d\u00e9fini') AS [Mode Reglement], "
            + "COUNT(*) AS [Nb Paiements], "
            + "SUM(pf.[Montant]) AS [Total Paye], "
            + "ROUND(SUM(pf.[Montant]) * 100.0 / NULLIF((SELECT SUM(p2.[Montant]) FROM Paiements_Fournisseurs p2 WHERE p2.[Date] BETWEEN @dateDebut AND @dateFin AND " + SOC.replace("pf.", "p2.") + "), 0), 2) AS [Part Pct], "
            + "pf.societe AS [Societe] "
            + "FROM Paiements_Fournisseurs pf "
            + "WHERE pf.[Date] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY ISNULL(pf.[Mode r\u00e9glement], 'Non d\u00e9fini'), pf.societe "
            + "ORDER BY SUM(pf.[Montant]) DESC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "paiements_fournisseurs"
    },
    # --- 20. DASHBOARD: Repartition par Journal ---
    {
        "code": "DS_PAF_REPARTITION_JOURNAL",
        "nom": "R\u00e9partition par Journal",
        "query": "SELECT "
            + "pf.[Code journal], pf.[Journal], "
            + "COUNT(*) AS [Nb Paiements], "
            + "SUM(pf.[Montant]) AS [Total Paye], "
            + "SUM(pf.[solde]) AS [Total Solde], "
            + "pf.societe AS [Societe] "
            + "FROM Paiements_Fournisseurs pf "
            + "WHERE pf.[Date] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY pf.[Code journal], pf.[Journal], pf.societe "
            + "ORDER BY SUM(pf.[Montant]) DESC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "paiements_fournisseurs"
    },
    # --- 21. DASHBOARD: Top Fournisseurs Payes (chart) ---
    {
        "code": "DS_PAF_TOP_FOURN_CHART",
        "nom": "Top 15 Fournisseurs Pay\u00e9s",
        "query": "SELECT TOP 15 "
            + "pf.[Intitul\u00e9] AS [Fournisseur], "
            + "SUM(pf.[Montant]) AS [Total Paye], "
            + "COUNT(*) AS [Nb Paiements], "
            + "pf.societe AS [Societe] "
            + "FROM Paiements_Fournisseurs pf "
            + "WHERE pf.[Date] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY pf.[Intitul\u00e9], pf.societe "
            + "ORDER BY SUM(pf.[Montant]) DESC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "paiements_fournisseurs"
    },
    # --- 22. DASHBOARD: Statut Imputation Paiements ---
    {
        "code": "DS_PAF_STATUT_IMPUTATION",
        "nom": "Statut Imputation Paiements",
        "query": "SELECT "
            + "pf.[Impute] AS [Statut], "
            + "COUNT(*) AS [Nb Paiements], "
            + "SUM(pf.[Montant]) AS [Total Paye], "
            + "SUM(pf.[solde]) AS [Total Solde], "
            + "pf.societe AS [Societe] "
            + "FROM Paiements_Fournisseurs pf "
            + "WHERE pf.[Date] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY pf.[Impute], pf.societe",
        "params": PARAMS_DATE_SOCIETE,
        "category": "paiements_fournisseurs"
    },
    # --- 23. DASHBOARD: Paiements par Tranche Montant ---
    {
        "code": "DS_PAF_TRANCHE_MONTANT",
        "nom": "Paiements par Tranche de Montant",
        "query": "SELECT "
            + "CASE WHEN pf.[Montant] < 1000 THEN '< 1K' "
            + "WHEN pf.[Montant] < 10000 THEN '1K - 10K' "
            + "WHEN pf.[Montant] < 50000 THEN '10K - 50K' "
            + "WHEN pf.[Montant] < 100000 THEN '50K - 100K' "
            + "WHEN pf.[Montant] < 500000 THEN '100K - 500K' "
            + "ELSE '> 500K' END AS [Tranche Montant], "
            + "COUNT(*) AS [Nb Paiements], "
            + "SUM(pf.[Montant]) AS [Total Paye], "
            + "pf.societe AS [Societe] "
            + "FROM Paiements_Fournisseurs pf "
            + "WHERE pf.[Date] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY CASE WHEN pf.[Montant] < 1000 THEN '< 1K' "
            + "WHEN pf.[Montant] < 10000 THEN '1K - 10K' "
            + "WHEN pf.[Montant] < 50000 THEN '10K - 50K' "
            + "WHEN pf.[Montant] < 100000 THEN '50K - 100K' "
            + "WHEN pf.[Montant] < 500000 THEN '100K - 500K' "
            + "ELSE '> 500K' END, pf.societe "
            + "ORDER BY MIN(pf.[Montant])",
        "params": PARAMS_DATE_SOCIETE,
        "category": "paiements_fournisseurs"
    },
    # --- 24. DASHBOARD: Decaissements Mensuels ---
    {
        "code": "DS_PAF_DECAISSEMENTS_MENS",
        "nom": "D\u00e9caissements Mensuels",
        "query": "SELECT "
            + "CAST(YEAR(pf.[Date]) AS VARCHAR) + '-' + RIGHT('0' + CAST(MONTH(pf.[Date]) AS VARCHAR), 2) AS [Periode], "
            + "SUM(pf.[Montant]) AS [Total Decaisse], "
            + "COUNT(*) AS [Nb Paiements], "
            + "COUNT(DISTINCT pf.[Code fournisseur]) AS [Nb Fournisseurs], "
            + "AVG(pf.[Montant]) AS [Montant Moyen], "
            + "pf.societe AS [Societe] "
            + "FROM Paiements_Fournisseurs pf "
            + "WHERE pf.[Date] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY CAST(YEAR(pf.[Date]) AS VARCHAR) + '-' + RIGHT('0' + CAST(MONTH(pf.[Date]) AS VARCHAR), 2), pf.societe "
            + "ORDER BY CAST(YEAR(pf.[Date]) AS VARCHAR) + '-' + RIGHT('0' + CAST(MONTH(pf.[Date]) AS VARCHAR), 2)",
        "params": PARAMS_DATE_SOCIETE,
        "category": "paiements_fournisseurs"
    },
    # --- 25. DASHBOARD: Synthese Annuelle Paiements ---
    {
        "code": "DS_PAF_SYNTHESE_ANNUELLE",
        "nom": "Synth\u00e8se Annuelle Paiements Fourn.",
        "query": "SELECT "
            + "CAST(YEAR(pf.[Date]) AS VARCHAR) AS [Exercice], "
            + "COUNT(*) AS [Nb Paiements], "
            + "SUM(pf.[Montant]) AS [Total Paye], "
            + "SUM(pf.[solde]) AS [Total Solde], "
            + "AVG(pf.[Montant]) AS [Montant Moyen], "
            + "COUNT(DISTINCT pf.[Code fournisseur]) AS [Nb Fournisseurs], "
            + "SUM(CASE WHEN pf.[Impute] = 'Oui' THEN pf.[Montant] ELSE 0 END) AS [Total Impute], "
            + "SUM(CASE WHEN pf.[Impute] = 'Non' THEN pf.[Montant] ELSE 0 END) AS [Total Non Impute], "
            + "pf.societe AS [Societe] "
            + "FROM Paiements_Fournisseurs pf "
            + "WHERE " + SOC + " "
            + "GROUP BY CAST(YEAR(pf.[Date]) AS VARCHAR), pf.societe "
            + "ORDER BY CAST(YEAR(pf.[Date]) AS VARCHAR)",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "paiements_fournisseurs"
    },
]

# ======================================================================
# 10 GRIDVIEWS
# ======================================================================
GRIDVIEWS = [
    ("DS_PAF_DETAIL_PAIEMENTS",  "D\u00e9tail Paiements Fournisseurs"),
    ("DS_PAF_NON_IMPUTES",       "Paiements Non Imput\u00e9s"),
    ("DS_PAF_SOLDE_NON_NUL",     "Paiements avec Solde Non Nul"),
    ("DS_PAF_PAR_FOURNISSEUR",   "Paiements par Fournisseur"),
    ("DS_PAF_ECHEANCES",         "Ech\u00e9ances Paiements Fournisseurs"),
    ("DS_PAF_PAR_JOURNAL",       "Paiements par Journal"),
    ("DS_PAF_PAR_COMPTE",        "Paiements par Compte G\u00e9n\u00e9ral"),
    ("DS_PAF_TOP_FOURNISSEURS",  "Top 20 Fournisseurs Pay\u00e9s"),
    ("DS_PAF_NON_VALIDES",       "Paiements Non Valid\u00e9s"),
    ("DS_PAF_DELAI_PAIEMENT",    "D\u00e9lai Moyen de Paiement"),
]

# ======================================================================
# 6 PIVOTS
# ======================================================================
PIVOTS = [
    ("DS_PAF_PIVOT_MODE", "Paiements par Mode R\u00e8glement",
     [{"field": "Mode Reglement"}],
     [{"field": "Total Paye", "aggregation": "sum"}, {"field": "Nb Paiements", "aggregation": "sum"}],
     [{"field": "Societe"}]),
    ("DS_PAF_PIVOT_JOURNAL", "Paiements par Journal",
     [{"field": "Journal"}],
     [{"field": "Total Paye", "aggregation": "sum"}, {"field": "Total Solde", "aggregation": "sum"}, {"field": "Nb Paiements", "aggregation": "sum"}],
     [{"field": "Societe"}]),
    ("DS_PAF_PIVOT_MENSUEL", "Paiements Mensuels",
     [{"field": "Periode"}],
     [{"field": "Total Paye", "aggregation": "sum"}, {"field": "Nb Paiements", "aggregation": "sum"}, {"field": "Nb Fournisseurs", "aggregation": "sum"}],
     [{"field": "Societe"}]),
    ("DS_PAF_PIVOT_FOURN_MODE", "Paiements par Fournisseur et Mode",
     [{"field": "Fournisseur"}, {"field": "Mode Reglement"}],
     [{"field": "Total Paye", "aggregation": "sum"}, {"field": "Nb Paiements", "aggregation": "sum"}],
     [{"field": "Societe"}]),
    ("DS_PAF_PIVOT_ANNUEL", "Evolution Annuelle Paiements",
     [{"field": "Exercice"}],
     [{"field": "Total Paye", "aggregation": "sum"}, {"field": "Total Solde", "aggregation": "sum"}, {"field": "Nb Fournisseurs", "aggregation": "sum"}],
     [{"field": "Societe"}]),
    ("DS_PAF_PIVOT_IMPUTATION", "Statut Imputation Paiements",
     [{"field": "Statut Imputation"}],
     [{"field": "Total Paye", "aggregation": "sum"}, {"field": "Nb Paiements", "aggregation": "sum"}, {"field": "Nb Fournisseurs", "aggregation": "sum"}],
     [{"field": "Societe"}]),
]

# ======================================================================
# 9 DASHBOARDS
# ======================================================================
DASHBOARDS = [
    ("DS_PAF_KPI_GLOBAL", "TB Paiements Fournisseurs", [
        {"id": "w1", "type": "kpi", "title": "Total Pay\u00e9", "x": 0, "y": 0, "w": 3, "h": 3,
         "config": {"dataSourceCode": "DS_PAF_KPI_GLOBAL", "dataSourceOrigin": "template", "value_field": "Total Paye", "format": "currency", "suffix": " DH"}},
        {"id": "w2", "type": "kpi", "title": "Total Solde", "x": 3, "y": 0, "w": 3, "h": 3,
         "config": {"dataSourceCode": "DS_PAF_KPI_GLOBAL", "dataSourceOrigin": "template", "value_field": "Total Solde", "format": "currency", "suffix": " DH",
                    "conditional_color": [{"operator": ">", "value": 0, "color": "#ef4444"}]}},
        {"id": "w3", "type": "kpi", "title": "Total Imput\u00e9", "x": 6, "y": 0, "w": 3, "h": 3,
         "config": {"dataSourceCode": "DS_PAF_KPI_GLOBAL", "dataSourceOrigin": "template", "value_field": "Total Impute", "format": "currency", "suffix": " DH"}},
        {"id": "w4", "type": "kpi", "title": "Taux Imputation", "x": 9, "y": 0, "w": 3, "h": 3,
         "config": {"dataSourceCode": "DS_PAF_KPI_GLOBAL", "dataSourceOrigin": "template", "value_field": "Taux Imputation", "format": "percent", "suffix": "%"}},
        {"id": "w5", "type": "kpi", "title": "Nb Paiements", "x": 0, "y": 3, "w": 3, "h": 3,
         "config": {"dataSourceCode": "DS_PAF_KPI_GLOBAL", "dataSourceOrigin": "template", "value_field": "Nb Paiements", "format": "number"}},
        {"id": "w6", "type": "kpi", "title": "Nb Fournisseurs", "x": 3, "y": 3, "w": 3, "h": 3,
         "config": {"dataSourceCode": "DS_PAF_KPI_GLOBAL", "dataSourceOrigin": "template", "value_field": "Nb Fournisseurs", "format": "number"}},
        {"id": "w7", "type": "kpi", "title": "Montant Moyen", "x": 6, "y": 3, "w": 3, "h": 3,
         "config": {"dataSourceCode": "DS_PAF_KPI_GLOBAL", "dataSourceOrigin": "template", "value_field": "Montant Moyen", "format": "currency", "suffix": " DH"}},
        {"id": "w8", "type": "kpi", "title": "Non Imput\u00e9s", "x": 9, "y": 3, "w": 3, "h": 3,
         "config": {"dataSourceCode": "DS_PAF_KPI_GLOBAL", "dataSourceOrigin": "template", "value_field": "Nb Non Imputes", "format": "number",
                    "conditional_color": [{"operator": ">", "value": 0, "color": "#f59e0b"}]}},
    ]),
    ("DS_PAF_EVOLUTION_MENSUELLE", "Evolution Mensuelle Paiements Fourn.", [
        {"id": "w1", "type": "bar", "title": "Paiements Mensuels", "x": 0, "y": 0, "w": 12, "h": 8,
         "config": {"dataSourceCode": "DS_PAF_EVOLUTION_MENSUELLE", "dataSourceOrigin": "template", "category_field": "Periode", "value_fields": ["Total Paye"], "colors": ["#3b82f6"]}},
        {"id": "w2", "type": "line", "title": "Nb Paiements par Mois", "x": 0, "y": 8, "w": 12, "h": 6,
         "config": {"dataSourceCode": "DS_PAF_EVOLUTION_MENSUELLE", "dataSourceOrigin": "template", "category_field": "Periode", "value_fields": ["Nb Paiements"], "colors": ["#10b981"]}},
    ]),
    ("DS_PAF_REPARTITION_MODE", "R\u00e9partition Modes Paiement Fourn.", [
        {"id": "w1", "type": "pie", "title": "Par Mode R\u00e8glement", "x": 0, "y": 0, "w": 6, "h": 8,
         "config": {"dataSourceCode": "DS_PAF_REPARTITION_MODE", "dataSourceOrigin": "template", "category_field": "Mode Reglement", "value_field": "Total Paye"}},
        {"id": "w2", "type": "bar", "title": "Montant par Mode", "x": 6, "y": 0, "w": 6, "h": 8,
         "config": {"dataSourceCode": "DS_PAF_REPARTITION_MODE", "dataSourceOrigin": "template", "category_field": "Mode Reglement", "value_fields": ["Total Paye", "Nb Paiements"], "colors": ["#3b82f6", "#f59e0b"]}},
    ]),
    ("DS_PAF_REPARTITION_JOURNAL", "R\u00e9partition par Journal Fourn.", [
        {"id": "w1", "type": "pie", "title": "Par Journal", "x": 0, "y": 0, "w": 6, "h": 8,
         "config": {"dataSourceCode": "DS_PAF_REPARTITION_JOURNAL", "dataSourceOrigin": "template", "category_field": "Journal", "value_field": "Total Paye"}},
        {"id": "w2", "type": "bar", "title": "Total par Journal", "x": 6, "y": 0, "w": 6, "h": 8,
         "config": {"dataSourceCode": "DS_PAF_REPARTITION_JOURNAL", "dataSourceOrigin": "template", "category_field": "Journal", "value_fields": ["Total Paye", "Total Solde"], "colors": ["#3b82f6", "#ef4444"]}},
    ]),
    ("DS_PAF_TOP_FOURN_CHART", "Top Fournisseurs Pay\u00e9s", [
        {"id": "w1", "type": "bar", "title": "Top 15 Fournisseurs", "x": 0, "y": 0, "w": 12, "h": 8,
         "config": {"dataSourceCode": "DS_PAF_TOP_FOURN_CHART", "dataSourceOrigin": "template", "category_field": "Fournisseur", "value_fields": ["Total Paye"], "colors": ["#3b82f6"]}},
        {"id": "w2", "type": "table", "title": "D\u00e9tail Top Fournisseurs", "x": 0, "y": 8, "w": 12, "h": 6,
         "config": {"dataSourceCode": "DS_PAF_TOP_FOURN_CHART", "dataSourceOrigin": "template", "columns": ["Fournisseur", "Total Paye", "Nb Paiements"]}},
    ]),
    ("DS_PAF_STATUT_IMPUTATION", "Statut Imputation Paiements Fourn.", [
        {"id": "w1", "type": "pie", "title": "Imput\u00e9 vs Non Imput\u00e9", "x": 0, "y": 0, "w": 6, "h": 8,
         "config": {"dataSourceCode": "DS_PAF_STATUT_IMPUTATION", "dataSourceOrigin": "template", "category_field": "Statut", "value_field": "Total Paye"}},
        {"id": "w2", "type": "bar", "title": "Montant par Statut", "x": 6, "y": 0, "w": 6, "h": 8,
         "config": {"dataSourceCode": "DS_PAF_STATUT_IMPUTATION", "dataSourceOrigin": "template", "category_field": "Statut", "value_fields": ["Total Paye", "Total Solde"], "colors": ["#10b981", "#ef4444"]}},
    ]),
    ("DS_PAF_TRANCHE_MONTANT", "Paiements par Tranche Montant", [
        {"id": "w1", "type": "pie", "title": "Nb par Tranche", "x": 0, "y": 0, "w": 6, "h": 8,
         "config": {"dataSourceCode": "DS_PAF_TRANCHE_MONTANT", "dataSourceOrigin": "template", "category_field": "Tranche Montant", "value_field": "Nb Paiements"}},
        {"id": "w2", "type": "bar", "title": "Montant par Tranche", "x": 6, "y": 0, "w": 6, "h": 8,
         "config": {"dataSourceCode": "DS_PAF_TRANCHE_MONTANT", "dataSourceOrigin": "template", "category_field": "Tranche Montant", "value_fields": ["Total Paye"], "colors": ["#8b5cf6"]}},
    ]),
    ("DS_PAF_DECAISSEMENTS_MENS", "D\u00e9caissements Mensuels Fourn.", [
        {"id": "w1", "type": "bar", "title": "D\u00e9caissements par Mois", "x": 0, "y": 0, "w": 12, "h": 8,
         "config": {"dataSourceCode": "DS_PAF_DECAISSEMENTS_MENS", "dataSourceOrigin": "template", "category_field": "Periode", "value_fields": ["Total Decaisse"], "colors": ["#ef4444"]}},
        {"id": "w2", "type": "line", "title": "Montant Moyen par Mois", "x": 0, "y": 8, "w": 12, "h": 6,
         "config": {"dataSourceCode": "DS_PAF_DECAISSEMENTS_MENS", "dataSourceOrigin": "template", "category_field": "Periode", "value_fields": ["Montant Moyen"], "colors": ["#f59e0b"]}},
    ]),
    ("DS_PAF_SYNTHESE_ANNUELLE", "Synth\u00e8se Annuelle Paiements Fourn.", [
        {"id": "w1", "type": "bar", "title": "Paiements par Ann\u00e9e", "x": 0, "y": 0, "w": 8, "h": 8,
         "config": {"dataSourceCode": "DS_PAF_SYNTHESE_ANNUELLE", "dataSourceOrigin": "template", "category_field": "Exercice", "value_fields": ["Total Paye", "Total Impute", "Total Non Impute"], "colors": ["#3b82f6", "#10b981", "#ef4444"]}},
        {"id": "w2", "type": "line", "title": "Nb Fournisseurs", "x": 8, "y": 0, "w": 4, "h": 8,
         "config": {"dataSourceCode": "DS_PAF_SYNTHESE_ANNUELLE", "dataSourceOrigin": "template", "category_field": "Exercice", "value_fields": ["Nb Fournisseurs"], "colors": ["#8b5cf6"]}},
        {"id": "w3", "type": "table", "title": "D\u00e9tail par Ann\u00e9e", "x": 0, "y": 8, "w": 12, "h": 6,
         "config": {"dataSourceCode": "DS_PAF_SYNTHESE_ANNUELLE", "dataSourceOrigin": "template", "columns": ["Exercice", "Total Paye", "Total Solde", "Total Impute", "Total Non Impute", "Nb Paiements", "Nb Fournisseurs"]}},
    ]),
]

# ======================================================================
MENU_ICONS = {
    "D\u00e9tail Paiements Fournisseurs": "FileText",
    "Paiements Non Imput\u00e9s": "AlertTriangle",
    "Paiements avec Solde Non Nul": "Scale",
    "Paiements par Fournisseur": "Users",
    "Ech\u00e9ances Paiements Fournisseurs": "CalendarClock",
    "Paiements par Journal": "BookOpen",
    "Paiements par Compte G\u00e9n\u00e9ral": "Calculator",
    "Top 20 Fournisseurs Pay\u00e9s": "Award",
    "Paiements Non Valid\u00e9s": "XCircle",
    "D\u00e9lai Moyen de Paiement": "Timer",
    "Paiements par Mode R\u00e8glement": "CreditCard",
    "Paiements par Journal (Pivot)": "BookOpen",
    "Paiements Mensuels": "Calendar",
    "Paiements par Fournisseur et Mode": "Layers",
    "Evolution Annuelle Paiements": "TrendingUp",
    "Statut Imputation Paiements": "CheckCircle",
    "TB Paiements Fournisseurs": "LayoutGrid",
    "Evolution Mensuelle Paiements Fourn.": "TrendingUp",
    "R\u00e9partition Modes Paiement Fourn.": "PieChart",
    "R\u00e9partition par Journal Fourn.": "PieChart",
    "Top Fournisseurs Pay\u00e9s": "Award",
    "Statut Imputation Paiements Fourn.": "CheckCircle",
    "Paiements par Tranche Montant": "BarChart3",
    "D\u00e9caissements Mensuels Fourn.": "Banknote",
    "Synth\u00e8se Annuelle Paiements Fourn.": "CalendarDays",
}

# ======================================================================
# MAIN
# ======================================================================
def main():
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()
    print("=" * 60)
    print("  CREATION DES 25 RAPPORTS PAIEMENTS FOURNISSEURS")
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
            if any(k in low for k in ("montant", "solde", "reste", "total", "impute", "paye", "decaiss", "moyen")):
                fmt = "currency"
            elif any(k in low for k in ("nb ", "nombre", "jours", "delai", "retard", "taux", "part")):
                fmt = "number"
            elif "date" in low: fmt = "date"
            columns.append({"field": alias, "header": alias, "format": fmt, "sortable": True, "filterable": True, "width": 150})
        total_cols = [c["field"] for c in columns if c["format"] in ("currency", "number") and "nb " not in c["field"].lower()]
        features_json = json.dumps({"show_search": True, "show_column_filters": True, "show_grouping": True, "show_column_toggle": True, "show_export": True, "show_pagination": True, "allow_sorting": True})
        cursor.execute("INSERT INTO APP_GridViews (nom, description, data_source_code, columns_config, page_size, show_totals, total_columns, features, actif) VALUES (?, ?, ?, ?, 25, 1, ?, ?, 1)",
            nom, f"Rapport Paiements Fourn. - {nom}", ds_code, json.dumps(columns), json.dumps(total_cols[:5]), features_json)
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
            nom, f"Pivot Paiements Fourn. - {nom}", ds_code, json.dumps(rows_cfg), json.dumps(vals_cfg), json.dumps(filters_cfg))
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
            nom, f"Dashboard Paiements Fourn. - {nom}", json.dumps(widgets))
        cursor.execute("SELECT @@IDENTITY")
        db_id = int(cursor.fetchone()[0])
        db_ids[ds_code] = db_id
        print(f"  + NEW Dashboard {nom} (id={db_id})")
    conn.commit()

    # --- 5. Menus ---
    print("\n[5/5] Creation des Menus...")
    cursor.execute("SELECT id FROM APP_Menus WHERE nom = 'Paiements Fournisseurs' AND parent_id IS NULL")
    root = cursor.fetchone()
    if root:
        root_id = root[0]
        print(f"  OK EXISTS racine (id={root_id})")
    else:
        cursor.execute("INSERT INTO APP_Menus (nom, icon, type, parent_id, ordre, actif) VALUES ('Paiements Fournisseurs', 'Banknote', 'folder', NULL, 55, 1)")
        cursor.execute("SELECT @@IDENTITY")
        root_id = int(cursor.fetchone()[0])
        print(f"  + NEW racine 'Paiements Fournisseurs' (id={root_id})")

    subfolders = [("Suivi des Paiements", "FileText", 1), ("Analyses Paiements", "BarChart3", 2), ("Tableaux de Bord", "LayoutGrid", 3)]
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
        ("Suivi des Paiements", "D\u00e9tail Paiements Fournisseurs", "gridview", gv_ids.get("DS_PAF_DETAIL_PAIEMENTS"), 1),
        ("Suivi des Paiements", "Paiements Non Imput\u00e9s", "gridview", gv_ids.get("DS_PAF_NON_IMPUTES"), 2),
        ("Suivi des Paiements", "Paiements avec Solde Non Nul", "gridview", gv_ids.get("DS_PAF_SOLDE_NON_NUL"), 3),
        ("Suivi des Paiements", "Paiements par Fournisseur", "gridview", gv_ids.get("DS_PAF_PAR_FOURNISSEUR"), 4),
        ("Suivi des Paiements", "Ech\u00e9ances Paiements Fournisseurs", "gridview", gv_ids.get("DS_PAF_ECHEANCES"), 5),
        ("Suivi des Paiements", "Paiements par Journal", "gridview", gv_ids.get("DS_PAF_PAR_JOURNAL"), 6),
        ("Suivi des Paiements", "Paiements par Compte G\u00e9n\u00e9ral", "gridview", gv_ids.get("DS_PAF_PAR_COMPTE"), 7),
        ("Suivi des Paiements", "Top 20 Fournisseurs Pay\u00e9s", "gridview", gv_ids.get("DS_PAF_TOP_FOURNISSEURS"), 8),
        ("Suivi des Paiements", "Paiements Non Valid\u00e9s", "gridview", gv_ids.get("DS_PAF_NON_VALIDES"), 9),
        ("Suivi des Paiements", "D\u00e9lai Moyen de Paiement", "gridview", gv_ids.get("DS_PAF_DELAI_PAIEMENT"), 10),
        ("Analyses Paiements", "Paiements par Mode R\u00e8glement", "pivot-v2", pv_ids.get("DS_PAF_PIVOT_MODE"), 1),
        ("Analyses Paiements", "Paiements par Journal (Pivot)", "pivot-v2", pv_ids.get("DS_PAF_PIVOT_JOURNAL"), 2),
        ("Analyses Paiements", "Paiements Mensuels", "pivot-v2", pv_ids.get("DS_PAF_PIVOT_MENSUEL"), 3),
        ("Analyses Paiements", "Paiements par Fournisseur et Mode", "pivot-v2", pv_ids.get("DS_PAF_PIVOT_FOURN_MODE"), 4),
        ("Analyses Paiements", "Evolution Annuelle Paiements", "pivot-v2", pv_ids.get("DS_PAF_PIVOT_ANNUEL"), 5),
        ("Analyses Paiements", "Statut Imputation Paiements", "pivot-v2", pv_ids.get("DS_PAF_PIVOT_IMPUTATION"), 6),
        ("Tableaux de Bord", "TB Paiements Fournisseurs", "dashboard", db_ids.get("DS_PAF_KPI_GLOBAL"), 1),
        ("Tableaux de Bord", "Evolution Mensuelle Paiements Fourn.", "dashboard", db_ids.get("DS_PAF_EVOLUTION_MENSUELLE"), 2),
        ("Tableaux de Bord", "R\u00e9partition Modes Paiement Fourn.", "dashboard", db_ids.get("DS_PAF_REPARTITION_MODE"), 3),
        ("Tableaux de Bord", "R\u00e9partition par Journal Fourn.", "dashboard", db_ids.get("DS_PAF_REPARTITION_JOURNAL"), 4),
        ("Tableaux de Bord", "Top Fournisseurs Pay\u00e9s", "dashboard", db_ids.get("DS_PAF_TOP_FOURN_CHART"), 5),
        ("Tableaux de Bord", "Statut Imputation Paiements Fourn.", "dashboard", db_ids.get("DS_PAF_STATUT_IMPUTATION"), 6),
        ("Tableaux de Bord", "Paiements par Tranche Montant", "dashboard", db_ids.get("DS_PAF_TRANCHE_MONTANT"), 7),
        ("Tableaux de Bord", "D\u00e9caissements Mensuels Fourn.", "dashboard", db_ids.get("DS_PAF_DECAISSEMENTS_MENS"), 8),
        ("Tableaux de Bord", "Synth\u00e8se Annuelle Paiements Fourn.", "dashboard", db_ids.get("DS_PAF_SYNTHESE_ANNUELLE"), 9),
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
