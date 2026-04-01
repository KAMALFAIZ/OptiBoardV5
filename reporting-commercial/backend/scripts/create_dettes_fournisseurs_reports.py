# -*- coding: utf-8 -*-
"""
Creation des 25 rapports du cycle DETTES FOURNISSEURS pour OptiBoard
10 GRID + 6 PIVOT + 9 DASHBOARD
Tables sources: Echeances_Achats + Imputation_Factures_Achats (DWH)
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

# Unicode column name references:
# Echeances_Achats (ea):
#   Date d'\u00e9ch\u00e9ance, N\u00b0 pi\u00e8ce, Montant \u00e9ch\u00e9ance devise,
#   R\u00e9gler, Mode de r\u00e9glement, Intitul\u00e9 fournisseur,
#   Montant \u00e9ch\u00e9ance, N\u00b0 interne, Date cr\u00e9ation
#
# Imputation_Factures_Achats (ifa):
#   R\u00e9f\u00e9rence, Libell\u00e9, id R\u00e9glement, Date r\u00e9glement,
#   Date d'\u00e9chance (NOT \u00e9ch\u00e9ance - single accent!),
#   Id \u00e9cheance (NOT \u00e9ch\u00e9ance - single accent!),
#   N\u00b0 pi\u00e8ce, Montant r\u00e9gler, Mode de r\u00e9glement,
#   Intitul\u00e9 fournisseur, Intitul\u00e9 tier encaisseur,
#   Montant r\u00e9glement, Date cr\u00e9ation

SOC_EA = "(@societe IS NULL OR ea.societe = @societe)"
SOC_IFA = "(@societe IS NULL OR ifa.societe = @societe)"

# ======================================================================
# 25 DATASOURCE TEMPLATES
# ======================================================================
DS_TEMPLATES = [
    # --- 1. GRID: Echeances Fournisseurs Detail ---
    {
        "code": "DS_DET_ECHEANCES_DETAIL",
        "nom": "Ech\u00e9ances Fournisseurs D\u00e9tail",
        "query": "SELECT "
            + "ea.[Code fournisseur], ea.[Intitul\u00e9 fournisseur] AS [Fournisseur], "
            + "ea.[Code tier payeur], ea.[Tier payeur] AS [Tiers Payeur], "
            + "ea.[Type Document], ea.[N\u00b0 pi\u00e8ce] AS [Num Piece], "
            + "ea.[Date document], ea.[Date d'\u00e9ch\u00e9ance] AS [Date Echeance], "
            + "ea.[Montant TTC], ea.[Montant \u00e9ch\u00e9ance] AS [Montant Echeance], "
            + "ea.[Mode de r\u00e9glement] AS [Mode Reglement], "
            + "ea.[R\u00e9gler] AS [Statut Reglement], "
            + "ea.societe AS [Societe] "
            + "FROM Echeances_Achats ea "
            + "WHERE ea.[Date document] BETWEEN @dateDebut AND @dateFin AND " + SOC_EA + " "
            + "ORDER BY ea.[Date d'\u00e9ch\u00e9ance] DESC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "dettes_fournisseurs"
    },
    # --- 2. GRID: Dettes Impayees ---
    {
        "code": "DS_DET_IMPAYES",
        "nom": "Dettes Impay\u00e9es",
        "query": "SELECT "
            + "ea.[Code fournisseur], ea.[Intitul\u00e9 fournisseur] AS [Fournisseur], "
            + "ea.[Code tier payeur], ea.[Tier payeur] AS [Tiers Payeur], "
            + "ea.[Type Document], ea.[N\u00b0 pi\u00e8ce] AS [Num Piece], "
            + "ea.[Date document], ea.[Date d'\u00e9ch\u00e9ance] AS [Date Echeance], "
            + "ea.[Montant \u00e9ch\u00e9ance] AS [Montant Echeance], "
            + "ea.[Mode de r\u00e9glement] AS [Mode Reglement], "
            + "DATEDIFF(day, ea.[Date d'\u00e9ch\u00e9ance], GETDATE()) AS [Jours Retard], "
            + "CASE WHEN DATEDIFF(day, ea.[Date d'\u00e9ch\u00e9ance], GETDATE()) <= 0 THEN 'A Jour' "
            + "WHEN DATEDIFF(day, ea.[Date d'\u00e9ch\u00e9ance], GETDATE()) <= 30 THEN '1-30j' "
            + "WHEN DATEDIFF(day, ea.[Date d'\u00e9ch\u00e9ance], GETDATE()) <= 60 THEN '31-60j' "
            + "WHEN DATEDIFF(day, ea.[Date d'\u00e9ch\u00e9ance], GETDATE()) <= 90 THEN '61-90j' "
            + "ELSE '+90j' END AS [Tranche Retard], "
            + "ea.societe AS [Societe] "
            + "FROM Echeances_Achats ea "
            + "WHERE ea.[R\u00e9gler] = 'Non' "
            + "AND ea.[Type Document] LIKE '%Facture%' "
            + "AND ea.[Montant \u00e9ch\u00e9ance] > 0 "
            + "AND " + SOC_EA + " "
            + "ORDER BY DATEDIFF(day, ea.[Date d'\u00e9ch\u00e9ance], GETDATE()) DESC",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "dettes_fournisseurs"
    },
    # --- 3. GRID: Reglements Effectues ---
    {
        "code": "DS_DET_REGLEMENTS",
        "nom": "R\u00e8glements Effectu\u00e9s",
        "query": "SELECT "
            + "ifa.[Code fournisseur], ifa.[Intitul\u00e9 fournisseur] AS [Fournisseur], "
            + "ifa.[Code tier encaisseur], ifa.[Intitul\u00e9 tier encaisseur] AS [Tier Encaisseur], "
            + "ifa.[Type Document], ifa.[N\u00b0 pi\u00e8ce] AS [Num Piece], "
            + "ifa.[Date document], ifa.[Date r\u00e9glement] AS [Date Reglement], "
            + "ifa.[Montant facture TTC] AS [Montant Facture], "
            + "ifa.[Montant r\u00e9gler] AS [Montant A Regler], "
            + "ifa.[Montant r\u00e9glement] AS [Montant Reglement], "
            + "ifa.[Mode de r\u00e9glement] AS [Mode Reglement], "
            + "ifa.[R\u00e9f\u00e9rence] AS [Reference], "
            + "ifa.societe AS [Societe] "
            + "FROM Imputation_Factures_Achats ifa "
            + "WHERE ifa.[Date r\u00e9glement] BETWEEN @dateDebut AND @dateFin AND " + SOC_IFA + " "
            + "ORDER BY ifa.[Date r\u00e9glement] DESC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "dettes_fournisseurs"
    },
    # --- 4. GRID: Balance Agee Fournisseurs ---
    {
        "code": "DS_DET_BALANCE_AGEE",
        "nom": "Balance Ag\u00e9e Fournisseurs",
        "query": "SELECT "
            + "ea.[Code fournisseur], ea.[Intitul\u00e9 fournisseur] AS [Fournisseur], "
            + "SUM(ea.[Montant \u00e9ch\u00e9ance]) AS [Solde Total], "
            + "SUM(CASE WHEN DATEDIFF(day, ea.[Date d'\u00e9ch\u00e9ance], GETDATE()) <= 0 THEN ea.[Montant \u00e9ch\u00e9ance] ELSE 0 END) AS [Non Echu], "
            + "SUM(CASE WHEN DATEDIFF(day, ea.[Date d'\u00e9ch\u00e9ance], GETDATE()) BETWEEN 1 AND 30 THEN ea.[Montant \u00e9ch\u00e9ance] ELSE 0 END) AS [1-30j], "
            + "SUM(CASE WHEN DATEDIFF(day, ea.[Date d'\u00e9ch\u00e9ance], GETDATE()) BETWEEN 31 AND 60 THEN ea.[Montant \u00e9ch\u00e9ance] ELSE 0 END) AS [31-60j], "
            + "SUM(CASE WHEN DATEDIFF(day, ea.[Date d'\u00e9ch\u00e9ance], GETDATE()) BETWEEN 61 AND 90 THEN ea.[Montant \u00e9ch\u00e9ance] ELSE 0 END) AS [61-90j], "
            + "SUM(CASE WHEN DATEDIFF(day, ea.[Date d'\u00e9ch\u00e9ance], GETDATE()) > 90 THEN ea.[Montant \u00e9ch\u00e9ance] ELSE 0 END) AS [Plus 90j], "
            + "COUNT(*) AS [Nb Echeances], "
            + "ea.societe AS [Societe] "
            + "FROM Echeances_Achats ea "
            + "WHERE ea.[R\u00e9gler] = 'Non' AND ea.[Montant \u00e9ch\u00e9ance] > 0 "
            + "AND ea.[Type Document] LIKE '%Facture%' "
            + "AND " + SOC_EA + " "
            + "GROUP BY ea.[Code fournisseur], ea.[Intitul\u00e9 fournisseur], ea.societe "
            + "ORDER BY SUM(ea.[Montant \u00e9ch\u00e9ance]) DESC",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "dettes_fournisseurs"
    },
    # --- 5. GRID: Echeances avec Imputations (JOIN) ---
    {
        "code": "DS_DET_ECHEANCES_IMPUTATIONS",
        "nom": "Ech\u00e9ances avec Imputations",
        "query": "SELECT "
            + "ea.[Code fournisseur], ea.[Intitul\u00e9 fournisseur] AS [Fournisseur], "
            + "ea.[Type Document], ea.[N\u00b0 pi\u00e8ce] AS [Num Piece], "
            + "ea.[Date document], ea.[Date d'\u00e9ch\u00e9ance] AS [Date Echeance], "
            + "ea.[Montant TTC], ea.[Montant \u00e9ch\u00e9ance] AS [Montant Echeance], "
            + "ea.[R\u00e9gler] AS [Statut], "
            + "ifa.[Montant r\u00e9gler] AS [Montant A Regler], "
            + "ifa.[Mode de r\u00e9glement] AS [Mode Reglement Imp], "
            + "ifa.[Date r\u00e9glement] AS [Date Reglement], "
            + "ifa.[Montant r\u00e9glement] AS [Montant Reglement], "
            + "ea.societe AS [Societe] "
            + "FROM Echeances_Achats ea "
            + "LEFT JOIN Imputation_Factures_Achats ifa "
            + "ON ifa.[Id \u00e9cheance] = ea.[N\u00b0 interne] AND ifa.societe = ea.societe "
            + "WHERE ea.[Date document] BETWEEN @dateDebut AND @dateFin AND " + SOC_EA + " "
            + "ORDER BY ea.[Date document] DESC, ea.[N\u00b0 pi\u00e8ce]",
        "params": PARAMS_DATE_SOCIETE,
        "category": "dettes_fournisseurs"
    },
    # --- 6. GRID: Factures Echues Non Reglees ---
    {
        "code": "DS_DET_ECHUES_NON_REGLEES",
        "nom": "Factures Ech\u00e9es Non R\u00e9gl\u00e9es",
        "query": "SELECT "
            + "ea.[Code fournisseur], ea.[Intitul\u00e9 fournisseur] AS [Fournisseur], "
            + "ea.[Type Document], ea.[N\u00b0 pi\u00e8ce] AS [Num Piece], "
            + "ea.[Date document], ea.[Date d'\u00e9ch\u00e9ance] AS [Date Echeance], "
            + "ea.[Montant \u00e9ch\u00e9ance] AS [Montant Echeance], "
            + "DATEDIFF(day, ea.[Date d'\u00e9ch\u00e9ance], GETDATE()) AS [Jours Retard], "
            + "ea.[Mode de r\u00e9glement] AS [Mode Reglement], "
            + "ea.societe AS [Societe] "
            + "FROM Echeances_Achats ea "
            + "WHERE ea.[Date d'\u00e9ch\u00e9ance] < GETDATE() "
            + "AND ea.[R\u00e9gler] = 'Non' AND ea.[Montant \u00e9ch\u00e9ance] > 0 "
            + "AND ea.[Type Document] LIKE '%Facture%' "
            + "AND " + SOC_EA + " "
            + "ORDER BY DATEDIFF(day, ea.[Date d'\u00e9ch\u00e9ance], GETDATE()) DESC",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "dettes_fournisseurs"
    },
    # --- 7. GRID: Fournisseurs Critiques ---
    {
        "code": "DS_DET_FOURNISSEURS_CRITIQUES",
        "nom": "Fournisseurs Critiques",
        "query": "SELECT "
            + "ea.[Code fournisseur], ea.[Intitul\u00e9 fournisseur] AS [Fournisseur], "
            + "COUNT(*) AS [Nb Factures Impayees], "
            + "SUM(ea.[Montant \u00e9ch\u00e9ance]) AS [Montant Impaye], "
            + "MAX(DATEDIFF(day, ea.[Date d'\u00e9ch\u00e9ance], GETDATE())) AS [Max Jours Retard], "
            + "AVG(DATEDIFF(day, ea.[Date d'\u00e9ch\u00e9ance], GETDATE())) AS [Moy Jours Retard], "
            + "MIN(ea.[Date d'\u00e9ch\u00e9ance]) AS [Plus Ancienne Echeance], "
            + "CASE WHEN MAX(DATEDIFF(day, ea.[Date d'\u00e9ch\u00e9ance], GETDATE())) > 180 THEN 'CRITIQUE' "
            + "WHEN MAX(DATEDIFF(day, ea.[Date d'\u00e9ch\u00e9ance], GETDATE())) > 90 THEN 'ELEVE' "
            + "WHEN MAX(DATEDIFF(day, ea.[Date d'\u00e9ch\u00e9ance], GETDATE())) > 30 THEN 'MOYEN' "
            + "ELSE 'FAIBLE' END AS [Urgence], "
            + "ea.societe AS [Societe] "
            + "FROM Echeances_Achats ea "
            + "WHERE ea.[R\u00e9gler] = 'Non' AND ea.[Montant \u00e9ch\u00e9ance] > 0 "
            + "AND ea.[Date d'\u00e9ch\u00e9ance] < GETDATE() "
            + "AND ea.[Type Document] LIKE '%Facture%' "
            + "AND " + SOC_EA + " "
            + "GROUP BY ea.[Code fournisseur], ea.[Intitul\u00e9 fournisseur], ea.societe "
            + "ORDER BY SUM(ea.[Montant \u00e9ch\u00e9ance]) DESC",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "dettes_fournisseurs"
    },
    # --- 8. GRID: Historique Paiements Fournisseurs ---
    {
        "code": "DS_DET_HISTORIQUE_PAIEMENTS",
        "nom": "Historique Paiements Fournisseurs",
        "query": "SELECT "
            + "ifa.[Code fournisseur], ifa.[Intitul\u00e9 fournisseur] AS [Fournisseur], "
            + "ifa.[Type Document], ifa.[N\u00b0 pi\u00e8ce] AS [Num Piece], "
            + "ifa.[Date document], ifa.[Date r\u00e9glement] AS [Date Reglement], "
            + "ifa.[Montant facture TTC] AS [Montant Facture], "
            + "ifa.[Montant r\u00e9gler] AS [Montant A Regler], "
            + "ifa.[Montant r\u00e9glement] AS [Montant Reglement], "
            + "ifa.[Mode de r\u00e9glement] AS [Mode Reglement], "
            + "DATEDIFF(day, ifa.[Date document], ifa.[Date r\u00e9glement]) AS [Delai Paiement Jours], "
            + "ifa.societe AS [Societe] "
            + "FROM Imputation_Factures_Achats ifa "
            + "WHERE ifa.[Date r\u00e9glement] BETWEEN @dateDebut AND @dateFin AND " + SOC_IFA + " "
            + "ORDER BY ifa.[Code fournisseur], ifa.[Date r\u00e9glement] DESC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "dettes_fournisseurs"
    },
    # --- 9. GRID: Echeances a Venir ---
    {
        "code": "DS_DET_ECHEANCES_A_VENIR",
        "nom": "Ech\u00e9ances \u00e0 Venir",
        "query": "SELECT "
            + "ea.[Code fournisseur], ea.[Intitul\u00e9 fournisseur] AS [Fournisseur], "
            + "ea.[Type Document], ea.[N\u00b0 pi\u00e8ce] AS [Num Piece], "
            + "ea.[Date document], ea.[Date d'\u00e9ch\u00e9ance] AS [Date Echeance], "
            + "ea.[Montant \u00e9ch\u00e9ance] AS [Montant Echeance], "
            + "DATEDIFF(day, GETDATE(), ea.[Date d'\u00e9ch\u00e9ance]) AS [Jours Restants], "
            + "ea.[Mode de r\u00e9glement] AS [Mode Reglement], "
            + "ea.societe AS [Societe] "
            + "FROM Echeances_Achats ea "
            + "WHERE ea.[Date d'\u00e9ch\u00e9ance] >= GETDATE() "
            + "AND ea.[R\u00e9gler] = 'Non' AND ea.[Montant \u00e9ch\u00e9ance] > 0 "
            + "AND ea.[Type Document] LIKE '%Facture%' "
            + "AND " + SOC_EA + " "
            + "ORDER BY ea.[Date d'\u00e9ch\u00e9ance] ASC",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "dettes_fournisseurs"
    },
    # --- 10. GRID: Delai Moyen Paiement Fournisseurs ---
    {
        "code": "DS_DET_DELAI_PAIEMENT",
        "nom": "D\u00e9lai Moyen de Paiement",
        "query": "SELECT "
            + "ifa.[Code fournisseur], ifa.[Intitul\u00e9 fournisseur] AS [Fournisseur], "
            + "COUNT(*) AS [Nb Reglements], "
            + "SUM(ifa.[Montant r\u00e9glement]) AS [Total Paye], "
            + "AVG(DATEDIFF(day, ifa.[Date document], ifa.[Date r\u00e9glement])) AS [Delai Moyen Jours], "
            + "MIN(DATEDIFF(day, ifa.[Date document], ifa.[Date r\u00e9glement])) AS [Delai Min], "
            + "MAX(DATEDIFF(day, ifa.[Date document], ifa.[Date r\u00e9glement])) AS [Delai Max], "
            + "ifa.societe AS [Societe] "
            + "FROM Imputation_Factures_Achats ifa "
            + "WHERE ifa.[Date r\u00e9glement] IS NOT NULL "
            + "AND ifa.[Date r\u00e9glement] BETWEEN @dateDebut AND @dateFin AND " + SOC_IFA + " "
            + "GROUP BY ifa.[Code fournisseur], ifa.[Intitul\u00e9 fournisseur], ifa.societe "
            + "ORDER BY AVG(DATEDIFF(day, ifa.[Date document], ifa.[Date r\u00e9glement])) DESC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "dettes_fournisseurs"
    },
    # --- 11. PIVOT: Dettes par Tranche d'Age ---
    {
        "code": "DS_DET_PIVOT_BALANCE_AGEE",
        "nom": "Dettes par Tranche d'Age",
        "query": "SELECT "
            + "ea.[Code fournisseur], ea.[Intitul\u00e9 fournisseur] AS [Fournisseur], "
            + "CASE WHEN DATEDIFF(day, ea.[Date d'\u00e9ch\u00e9ance], GETDATE()) <= 0 THEN 'Non Echu' "
            + "WHEN DATEDIFF(day, ea.[Date d'\u00e9ch\u00e9ance], GETDATE()) <= 30 THEN '1-30j' "
            + "WHEN DATEDIFF(day, ea.[Date d'\u00e9ch\u00e9ance], GETDATE()) <= 60 THEN '31-60j' "
            + "WHEN DATEDIFF(day, ea.[Date d'\u00e9ch\u00e9ance], GETDATE()) <= 90 THEN '61-90j' "
            + "ELSE '+90j' END AS [Tranche], "
            + "SUM(ea.[Montant \u00e9ch\u00e9ance]) AS [Montant Impaye], "
            + "COUNT(*) AS [Nb Echeances], "
            + "ea.societe AS [Societe] "
            + "FROM Echeances_Achats ea "
            + "WHERE ea.[R\u00e9gler] = 'Non' AND ea.[Montant \u00e9ch\u00e9ance] > 0 "
            + "AND ea.[Type Document] LIKE '%Facture%' "
            + "AND " + SOC_EA + " "
            + "GROUP BY ea.[Code fournisseur], ea.[Intitul\u00e9 fournisseur], "
            + "CASE WHEN DATEDIFF(day, ea.[Date d'\u00e9ch\u00e9ance], GETDATE()) <= 0 THEN 'Non Echu' "
            + "WHEN DATEDIFF(day, ea.[Date d'\u00e9ch\u00e9ance], GETDATE()) <= 30 THEN '1-30j' "
            + "WHEN DATEDIFF(day, ea.[Date d'\u00e9ch\u00e9ance], GETDATE()) <= 60 THEN '31-60j' "
            + "WHEN DATEDIFF(day, ea.[Date d'\u00e9ch\u00e9ance], GETDATE()) <= 90 THEN '61-90j' "
            + "ELSE '+90j' END, ea.societe",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "dettes_fournisseurs"
    },
    # --- 12. PIVOT: Paiements par Mode ---
    {
        "code": "DS_DET_PIVOT_MODE_REGLEMENT",
        "nom": "Paiements par Mode",
        "query": "SELECT "
            + "ifa.[Mode de r\u00e9glement] AS [Mode Reglement], "
            + "YEAR(ifa.[Date r\u00e9glement]) AS [Annee], "
            + "MONTH(ifa.[Date r\u00e9glement]) AS [Mois], "
            + "SUM(ifa.[Montant r\u00e9glement]) AS [Montant Paye], "
            + "COUNT(*) AS [Nb Paiements], "
            + "ifa.societe AS [Societe] "
            + "FROM Imputation_Factures_Achats ifa "
            + "WHERE ifa.[Date r\u00e9glement] BETWEEN @dateDebut AND @dateFin AND " + SOC_IFA + " "
            + "GROUP BY ifa.[Mode de r\u00e9glement], YEAR(ifa.[Date r\u00e9glement]), MONTH(ifa.[Date r\u00e9glement]), ifa.societe",
        "params": PARAMS_DATE_SOCIETE,
        "category": "dettes_fournisseurs"
    },
    # --- 13. PIVOT: Dettes par Type Document ---
    {
        "code": "DS_DET_PIVOT_TYPE_DOC",
        "nom": "Dettes par Type Document",
        "query": "SELECT "
            + "ea.[Type Document], "
            + "ea.[Code fournisseur], ea.[Intitul\u00e9 fournisseur] AS [Fournisseur], "
            + "SUM(ea.[Montant \u00e9ch\u00e9ance]) AS [Total Echeance], "
            + "SUM(CASE WHEN ea.[R\u00e9gler] = 'Oui' THEN ea.[Montant \u00e9ch\u00e9ance] ELSE 0 END) AS [Total Regle], "
            + "SUM(CASE WHEN ea.[R\u00e9gler] = 'Non' THEN ea.[Montant \u00e9ch\u00e9ance] ELSE 0 END) AS [Reste A Payer], "
            + "COUNT(*) AS [Nb Echeances], "
            + "ea.societe AS [Societe] "
            + "FROM Echeances_Achats ea "
            + "WHERE ea.[Date document] BETWEEN @dateDebut AND @dateFin AND " + SOC_EA + " "
            + "GROUP BY ea.[Type Document], ea.[Code fournisseur], ea.[Intitul\u00e9 fournisseur], ea.societe",
        "params": PARAMS_DATE_SOCIETE,
        "category": "dettes_fournisseurs"
    },
    # --- 14. PIVOT: Evolution Mensuelle Dettes ---
    {
        "code": "DS_DET_PIVOT_EVOLUTION",
        "nom": "Evolution Mensuelle Dettes",
        "query": "SELECT "
            + "YEAR(ea.[Date document]) AS [Annee], MONTH(ea.[Date document]) AS [Mois], "
            + "CAST(YEAR(ea.[Date document]) AS VARCHAR) + '-' + RIGHT('0' + CAST(MONTH(ea.[Date document]) AS VARCHAR), 2) AS [Periode], "
            + "SUM(ea.[Montant \u00e9ch\u00e9ance]) AS [Total Echeances], "
            + "SUM(CASE WHEN ea.[R\u00e9gler] = 'Oui' THEN ea.[Montant \u00e9ch\u00e9ance] ELSE 0 END) AS [Total Regle], "
            + "SUM(CASE WHEN ea.[R\u00e9gler] = 'Non' THEN ea.[Montant \u00e9ch\u00e9ance] ELSE 0 END) AS [Reste A Payer], "
            + "COUNT(*) AS [Nb Echeances], "
            + "COUNT(DISTINCT ea.[Code fournisseur]) AS [Nb Fournisseurs], "
            + "ea.societe AS [Societe] "
            + "FROM Echeances_Achats ea "
            + "WHERE ea.[Type Document] LIKE '%Facture%' "
            + "AND ea.[Date document] BETWEEN @dateDebut AND @dateFin AND " + SOC_EA + " "
            + "GROUP BY YEAR(ea.[Date document]), MONTH(ea.[Date document]), ea.societe "
            + "ORDER BY YEAR(ea.[Date document]), MONTH(ea.[Date document])",
        "params": PARAMS_DATE_SOCIETE,
        "category": "dettes_fournisseurs"
    },
    # --- 15. PIVOT: Taux Paiement par Fournisseur ---
    {
        "code": "DS_DET_PIVOT_TAUX_FOURN",
        "nom": "Taux de Paiement par Fournisseur",
        "query": "SELECT "
            + "ea.[Code fournisseur], ea.[Intitul\u00e9 fournisseur] AS [Fournisseur], "
            + "SUM(ea.[Montant \u00e9ch\u00e9ance]) AS [Total Echeance], "
            + "SUM(CASE WHEN ea.[R\u00e9gler] = 'Oui' THEN ea.[Montant \u00e9ch\u00e9ance] ELSE 0 END) AS [Total Regle], "
            + "SUM(CASE WHEN ea.[R\u00e9gler] = 'Non' THEN ea.[Montant \u00e9ch\u00e9ance] ELSE 0 END) AS [Reste A Payer], "
            + "CASE WHEN SUM(ea.[Montant \u00e9ch\u00e9ance]) > 0 "
            + "THEN ROUND(100.0 * SUM(CASE WHEN ea.[R\u00e9gler] = 'Oui' THEN ea.[Montant \u00e9ch\u00e9ance] ELSE 0 END) / SUM(ea.[Montant \u00e9ch\u00e9ance]), 2) ELSE 0 END AS [Taux Paiement], "
            + "COUNT(*) AS [Nb Echeances], "
            + "ea.societe AS [Societe] "
            + "FROM Echeances_Achats ea "
            + "WHERE ea.[Type Document] LIKE '%Facture%' "
            + "AND ea.[Date document] BETWEEN @dateDebut AND @dateFin AND " + SOC_EA + " "
            + "GROUP BY ea.[Code fournisseur], ea.[Intitul\u00e9 fournisseur], ea.societe "
            + "ORDER BY SUM(CASE WHEN ea.[R\u00e9gler] = 'Non' THEN ea.[Montant \u00e9ch\u00e9ance] ELSE 0 END) DESC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "dettes_fournisseurs"
    },
    # --- 16. PIVOT: Paiements par Tier Encaisseur ---
    {
        "code": "DS_DET_PIVOT_TIER_ENCAISSEUR",
        "nom": "Paiements par Tier Encaisseur",
        "query": "SELECT "
            + "ea.[Code tier payeur], ea.[Tier payeur] AS [Tier Encaisseur], "
            + "SUM(ea.[Montant \u00e9ch\u00e9ance]) AS [Total Echeance], "
            + "SUM(CASE WHEN ea.[R\u00e9gler] = 'Oui' THEN ea.[Montant \u00e9ch\u00e9ance] ELSE 0 END) AS [Total Regle], "
            + "SUM(CASE WHEN ea.[R\u00e9gler] = 'Non' THEN ea.[Montant \u00e9ch\u00e9ance] ELSE 0 END) AS [Reste A Payer], "
            + "COUNT(*) AS [Nb Echeances], "
            + "COUNT(DISTINCT ea.[Code fournisseur]) AS [Nb Fournisseurs], "
            + "ea.societe AS [Societe] "
            + "FROM Echeances_Achats ea "
            + "WHERE ea.[Type Document] LIKE '%Facture%' "
            + "AND ea.[Date document] BETWEEN @dateDebut AND @dateFin AND " + SOC_EA + " "
            + "GROUP BY ea.[Code tier payeur], ea.[Tier payeur], ea.societe "
            + "ORDER BY SUM(ea.[Montant \u00e9ch\u00e9ance]) DESC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "dettes_fournisseurs"
    },
    # --- 17. DASHBOARD: KPI Dettes Global ---
    {
        "code": "DS_DET_KPI_GLOBAL",
        "nom": "KPI Dettes Fournisseurs",
        "query": "SELECT "
            + "SUM(ea.[Montant \u00e9ch\u00e9ance]) AS [Total Dettes], "
            + "SUM(CASE WHEN ea.[R\u00e9gler] = 'Oui' THEN ea.[Montant \u00e9ch\u00e9ance] ELSE 0 END) AS [Total Paye], "
            + "SUM(CASE WHEN ea.[R\u00e9gler] = 'Non' THEN ea.[Montant \u00e9ch\u00e9ance] ELSE 0 END) AS [Reste A Payer], "
            + "CASE WHEN SUM(ea.[Montant \u00e9ch\u00e9ance]) > 0 "
            + "THEN ROUND(100.0 * SUM(CASE WHEN ea.[R\u00e9gler] = 'Oui' THEN ea.[Montant \u00e9ch\u00e9ance] ELSE 0 END) / SUM(ea.[Montant \u00e9ch\u00e9ance]), 2) ELSE 0 END AS [Taux Paiement], "
            + "COUNT(*) AS [Nb Echeances], "
            + "COUNT(DISTINCT ea.[Code fournisseur]) AS [Nb Fournisseurs], "
            + "SUM(CASE WHEN ea.[Date d'\u00e9ch\u00e9ance] < GETDATE() AND ea.[R\u00e9gler] = 'Non' THEN 1 ELSE 0 END) AS [Nb Echues Impayees], "
            + "SUM(CASE WHEN ea.[Date d'\u00e9ch\u00e9ance] < GETDATE() AND ea.[R\u00e9gler] = 'Non' THEN ea.[Montant \u00e9ch\u00e9ance] ELSE 0 END) AS [Montant Echues Impayees], "
            + "ea.societe AS [Societe] "
            + "FROM Echeances_Achats ea "
            + "WHERE ea.[Type Document] LIKE '%Facture%' "
            + "AND ea.[Date document] BETWEEN @dateDebut AND @dateFin AND " + SOC_EA + " "
            + "GROUP BY ea.societe",
        "params": PARAMS_DATE_SOCIETE,
        "category": "dettes_fournisseurs"
    },
    # --- 18. DASHBOARD: Evolution Mensuelle Dettes ---
    {
        "code": "DS_DET_EVOLUTION_MENSUELLE",
        "nom": "Evolution Mensuelle Dettes",
        "query": "SELECT "
            + "YEAR(ea.[Date document]) AS [Annee], MONTH(ea.[Date document]) AS [Mois], "
            + "CAST(YEAR(ea.[Date document]) AS VARCHAR) + '-' + RIGHT('0' + CAST(MONTH(ea.[Date document]) AS VARCHAR), 2) AS [Periode], "
            + "SUM(ea.[Montant \u00e9ch\u00e9ance]) AS [Dettes], "
            + "SUM(CASE WHEN ea.[R\u00e9gler] = 'Oui' THEN ea.[Montant \u00e9ch\u00e9ance] ELSE 0 END) AS [Paye], "
            + "SUM(CASE WHEN ea.[R\u00e9gler] = 'Non' THEN ea.[Montant \u00e9ch\u00e9ance] ELSE 0 END) AS [Impaye], "
            + "ea.societe AS [Societe] "
            + "FROM Echeances_Achats ea "
            + "WHERE ea.[Type Document] LIKE '%Facture%' "
            + "AND ea.[Date document] BETWEEN @dateDebut AND @dateFin AND " + SOC_EA + " "
            + "GROUP BY YEAR(ea.[Date document]), MONTH(ea.[Date document]), ea.societe "
            + "ORDER BY YEAR(ea.[Date document]), MONTH(ea.[Date document])",
        "params": PARAMS_DATE_SOCIETE,
        "category": "dettes_fournisseurs"
    },
    # --- 19. DASHBOARD: Repartition Balance Agee ---
    {
        "code": "DS_DET_REPARTITION_AGEE",
        "nom": "R\u00e9partition Balance Ag\u00e9e Fournisseurs",
        "query": "SELECT "
            + "CASE WHEN DATEDIFF(day, ea.[Date d'\u00e9ch\u00e9ance], GETDATE()) <= 0 THEN 'Non Echu' "
            + "WHEN DATEDIFF(day, ea.[Date d'\u00e9ch\u00e9ance], GETDATE()) <= 30 THEN '1-30 jours' "
            + "WHEN DATEDIFF(day, ea.[Date d'\u00e9ch\u00e9ance], GETDATE()) <= 60 THEN '31-60 jours' "
            + "WHEN DATEDIFF(day, ea.[Date d'\u00e9ch\u00e9ance], GETDATE()) <= 90 THEN '61-90 jours' "
            + "ELSE 'Plus de 90 jours' END AS [Tranche], "
            + "SUM(ea.[Montant \u00e9ch\u00e9ance]) AS [Montant Impaye], "
            + "COUNT(*) AS [Nb Echeances], "
            + "COUNT(DISTINCT ea.[Code fournisseur]) AS [Nb Fournisseurs], "
            + "ea.societe AS [Societe] "
            + "FROM Echeances_Achats ea "
            + "WHERE ea.[R\u00e9gler] = 'Non' AND ea.[Montant \u00e9ch\u00e9ance] > 0 "
            + "AND ea.[Type Document] LIKE '%Facture%' "
            + "AND " + SOC_EA + " "
            + "GROUP BY CASE WHEN DATEDIFF(day, ea.[Date d'\u00e9ch\u00e9ance], GETDATE()) <= 0 THEN 'Non Echu' "
            + "WHEN DATEDIFF(day, ea.[Date d'\u00e9ch\u00e9ance], GETDATE()) <= 30 THEN '1-30 jours' "
            + "WHEN DATEDIFF(day, ea.[Date d'\u00e9ch\u00e9ance], GETDATE()) <= 60 THEN '31-60 jours' "
            + "WHEN DATEDIFF(day, ea.[Date d'\u00e9ch\u00e9ance], GETDATE()) <= 90 THEN '61-90 jours' "
            + "ELSE 'Plus de 90 jours' END, ea.societe",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "dettes_fournisseurs"
    },
    # --- 20. DASHBOARD: Top 20 Creanciers ---
    {
        "code": "DS_DET_TOP_CREANCIERS",
        "nom": "Top 20 Cr\u00e9anciers",
        "query": "SELECT TOP 20 "
            + "ea.[Code fournisseur], ea.[Intitul\u00e9 fournisseur] AS [Fournisseur], "
            + "SUM(ea.[Montant \u00e9ch\u00e9ance]) AS [Montant Impaye], "
            + "COUNT(*) AS [Nb Echeances], "
            + "MAX(DATEDIFF(day, ea.[Date d'\u00e9ch\u00e9ance], GETDATE())) AS [Max Retard Jours], "
            + "ea.societe AS [Societe] "
            + "FROM Echeances_Achats ea "
            + "WHERE ea.[R\u00e9gler] = 'Non' AND ea.[Montant \u00e9ch\u00e9ance] > 0 "
            + "AND ea.[Type Document] LIKE '%Facture%' "
            + "AND " + SOC_EA + " "
            + "GROUP BY ea.[Code fournisseur], ea.[Intitul\u00e9 fournisseur], ea.societe "
            + "ORDER BY SUM(ea.[Montant \u00e9ch\u00e9ance]) DESC",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "dettes_fournisseurs"
    },
    # --- 21. DASHBOARD: Repartition par Mode Reglement ---
    {
        "code": "DS_DET_REPARTITION_MODE",
        "nom": "R\u00e9partition par Mode R\u00e8glement",
        "query": "SELECT "
            + "ea.[Mode de r\u00e9glement] AS [Mode Reglement], "
            + "SUM(ea.[Montant \u00e9ch\u00e9ance]) AS [Total Echeances], "
            + "SUM(CASE WHEN ea.[R\u00e9gler] = 'Oui' THEN ea.[Montant \u00e9ch\u00e9ance] ELSE 0 END) AS [Total Regle], "
            + "SUM(CASE WHEN ea.[R\u00e9gler] = 'Non' THEN ea.[Montant \u00e9ch\u00e9ance] ELSE 0 END) AS [Reste A Payer], "
            + "COUNT(*) AS [Nb Echeances], "
            + "ea.societe AS [Societe] "
            + "FROM Echeances_Achats ea "
            + "WHERE ea.[Type Document] LIKE '%Facture%' "
            + "AND ea.[Date document] BETWEEN @dateDebut AND @dateFin AND " + SOC_EA + " "
            + "GROUP BY ea.[Mode de r\u00e9glement], ea.societe "
            + "ORDER BY SUM(ea.[Montant \u00e9ch\u00e9ance]) DESC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "dettes_fournisseurs"
    },
    # --- 22. DASHBOARD: Taux Paiement Mensuel ---
    {
        "code": "DS_DET_TAUX_MENSUEL",
        "nom": "Taux Paiement Mensuel",
        "query": "SELECT "
            + "YEAR(ea.[Date document]) AS [Annee], MONTH(ea.[Date document]) AS [Mois], "
            + "CAST(YEAR(ea.[Date document]) AS VARCHAR) + '-' + RIGHT('0' + CAST(MONTH(ea.[Date document]) AS VARCHAR), 2) AS [Periode], "
            + "CASE WHEN SUM(ea.[Montant \u00e9ch\u00e9ance]) > 0 "
            + "THEN ROUND(100.0 * SUM(CASE WHEN ea.[R\u00e9gler] = 'Oui' THEN ea.[Montant \u00e9ch\u00e9ance] ELSE 0 END) / SUM(ea.[Montant \u00e9ch\u00e9ance]), 2) ELSE 0 END AS [Taux Paiement], "
            + "SUM(ea.[Montant \u00e9ch\u00e9ance]) AS [Dettes], "
            + "SUM(CASE WHEN ea.[R\u00e9gler] = 'Oui' THEN ea.[Montant \u00e9ch\u00e9ance] ELSE 0 END) AS [Paye], "
            + "ea.societe AS [Societe] "
            + "FROM Echeances_Achats ea "
            + "WHERE ea.[Type Document] LIKE '%Facture%' "
            + "AND ea.[Date document] BETWEEN @dateDebut AND @dateFin AND " + SOC_EA + " "
            + "GROUP BY YEAR(ea.[Date document]), MONTH(ea.[Date document]), ea.societe "
            + "ORDER BY YEAR(ea.[Date document]), MONTH(ea.[Date document])",
        "params": PARAMS_DATE_SOCIETE,
        "category": "dettes_fournisseurs"
    },
    # --- 23. DASHBOARD: Niveau Urgence Fournisseurs ---
    {
        "code": "DS_DET_NIVEAU_URGENCE",
        "nom": "Niveau Urgence Fournisseurs",
        "query": "SELECT sub.[Urgence], "
            + "COUNT(*) AS [Nb Fournisseurs], "
            + "SUM(sub.[Montant Impaye]) AS [Montant Impaye], "
            + "sub.societe AS [Societe] "
            + "FROM ("
            + "SELECT ea.[Code fournisseur], "
            + "SUM(ea.[Montant \u00e9ch\u00e9ance]) AS [Montant Impaye], "
            + "CASE WHEN MAX(DATEDIFF(day, ea.[Date d'\u00e9ch\u00e9ance], GETDATE())) > 180 THEN 'CRITIQUE' "
            + "WHEN MAX(DATEDIFF(day, ea.[Date d'\u00e9ch\u00e9ance], GETDATE())) > 90 THEN 'ELEVE' "
            + "WHEN MAX(DATEDIFF(day, ea.[Date d'\u00e9ch\u00e9ance], GETDATE())) > 30 THEN 'MOYEN' "
            + "ELSE 'FAIBLE' END AS [Urgence], "
            + "ea.societe "
            + "FROM Echeances_Achats ea "
            + "WHERE ea.[R\u00e9gler] = 'Non' AND ea.[Montant \u00e9ch\u00e9ance] > 0 "
            + "AND ea.[Date d'\u00e9ch\u00e9ance] < GETDATE() "
            + "AND ea.[Type Document] LIKE '%Facture%' "
            + "AND " + SOC_EA + " "
            + "GROUP BY ea.[Code fournisseur], ea.societe"
            + ") sub "
            + "GROUP BY sub.[Urgence], sub.societe "
            + "ORDER BY CASE sub.[Urgence] WHEN 'CRITIQUE' THEN 1 WHEN 'ELEVE' THEN 2 WHEN 'MOYEN' THEN 3 ELSE 4 END",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "dettes_fournisseurs"
    },
    # --- 24. DASHBOARD: Decaissements Mensuels ---
    {
        "code": "DS_DET_DECAISSEMENTS_MENS",
        "nom": "D\u00e9caissements Mensuels",
        "query": "SELECT "
            + "YEAR(ifa.[Date r\u00e9glement]) AS [Annee], MONTH(ifa.[Date r\u00e9glement]) AS [Mois], "
            + "CAST(YEAR(ifa.[Date r\u00e9glement]) AS VARCHAR) + '-' + RIGHT('0' + CAST(MONTH(ifa.[Date r\u00e9glement]) AS VARCHAR), 2) AS [Periode], "
            + "SUM(ifa.[Montant r\u00e9glement]) AS [Total Decaisse], "
            + "COUNT(*) AS [Nb Paiements], "
            + "COUNT(DISTINCT ifa.[Code fournisseur]) AS [Nb Fournisseurs], "
            + "ifa.societe AS [Societe] "
            + "FROM Imputation_Factures_Achats ifa "
            + "WHERE ifa.[Date r\u00e9glement] BETWEEN @dateDebut AND @dateFin AND " + SOC_IFA + " "
            + "GROUP BY YEAR(ifa.[Date r\u00e9glement]), MONTH(ifa.[Date r\u00e9glement]), ifa.societe "
            + "ORDER BY YEAR(ifa.[Date r\u00e9glement]), MONTH(ifa.[Date r\u00e9glement])",
        "params": PARAMS_DATE_SOCIETE,
        "category": "dettes_fournisseurs"
    },
    # --- 25. DASHBOARD: Synthese Annuelle Dettes ---
    {
        "code": "DS_DET_SYNTHESE_ANNUELLE",
        "nom": "Synth\u00e8se Annuelle Dettes Fournisseurs",
        "query": "SELECT "
            + "YEAR(ea.[Date document]) AS [Exercice], "
            + "SUM(ea.[Montant \u00e9ch\u00e9ance]) AS [Total Dettes], "
            + "SUM(CASE WHEN ea.[R\u00e9gler] = 'Oui' THEN ea.[Montant \u00e9ch\u00e9ance] ELSE 0 END) AS [Total Paye], "
            + "SUM(CASE WHEN ea.[R\u00e9gler] = 'Non' THEN ea.[Montant \u00e9ch\u00e9ance] ELSE 0 END) AS [Reste A Payer], "
            + "CASE WHEN SUM(ea.[Montant \u00e9ch\u00e9ance]) > 0 "
            + "THEN ROUND(100.0 * SUM(CASE WHEN ea.[R\u00e9gler] = 'Oui' THEN ea.[Montant \u00e9ch\u00e9ance] ELSE 0 END) / SUM(ea.[Montant \u00e9ch\u00e9ance]), 2) ELSE 0 END AS [Taux Paiement], "
            + "COUNT(*) AS [Nb Echeances], "
            + "COUNT(DISTINCT ea.[Code fournisseur]) AS [Nb Fournisseurs], "
            + "ea.societe AS [Societe] "
            + "FROM Echeances_Achats ea "
            + "WHERE ea.[Type Document] LIKE '%Facture%' "
            + "AND " + SOC_EA + " "
            + "GROUP BY YEAR(ea.[Date document]), ea.societe "
            + "ORDER BY YEAR(ea.[Date document])",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "dettes_fournisseurs"
    },
]

# ======================================================================
# 10 GRIDVIEWS
# ======================================================================
GRIDVIEWS = [
    ("DS_DET_ECHEANCES_DETAIL",       "Ech\u00e9ances Fournisseurs D\u00e9tail"),
    ("DS_DET_IMPAYES",                "Dettes Impay\u00e9es"),
    ("DS_DET_REGLEMENTS",             "R\u00e8glements Effectu\u00e9s"),
    ("DS_DET_BALANCE_AGEE",           "Balance Ag\u00e9e Fournisseurs"),
    ("DS_DET_ECHEANCES_IMPUTATIONS",  "Ech\u00e9ances avec Imputations"),
    ("DS_DET_ECHUES_NON_REGLEES",     "Factures Ech\u00e9es Non R\u00e9gl\u00e9es"),
    ("DS_DET_FOURNISSEURS_CRITIQUES", "Fournisseurs Critiques"),
    ("DS_DET_HISTORIQUE_PAIEMENTS",   "Historique Paiements"),
    ("DS_DET_ECHEANCES_A_VENIR",      "Ech\u00e9ances \u00e0 Venir"),
    ("DS_DET_DELAI_PAIEMENT",         "D\u00e9lai Moyen de Paiement"),
]

# ======================================================================
# 6 PIVOTS
# ======================================================================
PIVOTS = [
    ("DS_DET_PIVOT_BALANCE_AGEE", "Dettes par Tranche d'Age",
     [{"field": "Fournisseur"}],
     [{"field": "Montant Impaye", "aggregation": "sum"}, {"field": "Nb Echeances", "aggregation": "sum"}],
     [{"field": "Societe"}, {"field": "Tranche"}]),
    ("DS_DET_PIVOT_MODE_REGLEMENT", "Paiements par Mode",
     [{"field": "Mode Reglement"}],
     [{"field": "Montant Paye", "aggregation": "sum"}, {"field": "Nb Paiements", "aggregation": "sum"}],
     [{"field": "Societe"}]),
    ("DS_DET_PIVOT_TYPE_DOC", "Dettes par Type Document",
     [{"field": "Type Document"}],
     [{"field": "Total Echeance", "aggregation": "sum"}, {"field": "Total Regle", "aggregation": "sum"}, {"field": "Reste A Payer", "aggregation": "sum"}],
     [{"field": "Societe"}]),
    ("DS_DET_PIVOT_EVOLUTION", "Evolution Mensuelle Dettes",
     [{"field": "Periode"}],
     [{"field": "Total Echeances", "aggregation": "sum"}, {"field": "Total Regle", "aggregation": "sum"}, {"field": "Reste A Payer", "aggregation": "sum"}],
     [{"field": "Societe"}]),
    ("DS_DET_PIVOT_TAUX_FOURN", "Taux Paiement par Fournisseur",
     [{"field": "Fournisseur"}],
     [{"field": "Total Echeance", "aggregation": "sum"}, {"field": "Total Regle", "aggregation": "sum"}, {"field": "Taux Paiement", "aggregation": "avg"}],
     [{"field": "Societe"}]),
    ("DS_DET_PIVOT_TIER_ENCAISSEUR", "Paiements par Tier Encaisseur",
     [{"field": "Tier Encaisseur"}],
     [{"field": "Total Echeance", "aggregation": "sum"}, {"field": "Total Regle", "aggregation": "sum"}, {"field": "Reste A Payer", "aggregation": "sum"}],
     [{"field": "Societe"}]),
]

# ======================================================================
# 9 DASHBOARDS
# ======================================================================
DASHBOARDS = [
    ("DS_DET_KPI_GLOBAL", "TB Dettes Fournisseurs", [
        {"id": "w1", "type": "kpi", "title": "Total Dettes", "x": 0, "y": 0, "w": 3, "h": 3,
         "config": {"dataSourceCode": "DS_DET_KPI_GLOBAL", "dataSourceOrigin": "template", "value_field": "Total Dettes", "format": "currency", "suffix": " DH"}},
        {"id": "w2", "type": "kpi", "title": "Total Pay\u00e9", "x": 3, "y": 0, "w": 3, "h": 3,
         "config": {"dataSourceCode": "DS_DET_KPI_GLOBAL", "dataSourceOrigin": "template", "value_field": "Total Paye", "format": "currency", "suffix": " DH"}},
        {"id": "w3", "type": "kpi", "title": "Reste \u00e0 Payer", "x": 6, "y": 0, "w": 3, "h": 3,
         "config": {"dataSourceCode": "DS_DET_KPI_GLOBAL", "dataSourceOrigin": "template", "value_field": "Reste A Payer", "format": "currency", "suffix": " DH",
                    "conditional_color": [{"operator": ">", "value": 0, "color": "#ef4444"}]}},
        {"id": "w4", "type": "kpi", "title": "Taux Paiement", "x": 9, "y": 0, "w": 3, "h": 3,
         "config": {"dataSourceCode": "DS_DET_KPI_GLOBAL", "dataSourceOrigin": "template", "value_field": "Taux Paiement", "format": "percent", "suffix": "%"}},
        {"id": "w5", "type": "kpi", "title": "Nb Fournisseurs", "x": 0, "y": 3, "w": 3, "h": 3,
         "config": {"dataSourceCode": "DS_DET_KPI_GLOBAL", "dataSourceOrigin": "template", "value_field": "Nb Fournisseurs", "format": "number"}},
        {"id": "w6", "type": "kpi", "title": "Nb Ech\u00e9ances", "x": 3, "y": 3, "w": 3, "h": 3,
         "config": {"dataSourceCode": "DS_DET_KPI_GLOBAL", "dataSourceOrigin": "template", "value_field": "Nb Echeances", "format": "number"}},
        {"id": "w7", "type": "kpi", "title": "Ech\u00e9es Impay\u00e9es", "x": 6, "y": 3, "w": 3, "h": 3,
         "config": {"dataSourceCode": "DS_DET_KPI_GLOBAL", "dataSourceOrigin": "template", "value_field": "Nb Echues Impayees", "format": "number"}},
        {"id": "w8", "type": "kpi", "title": "Montant Ech\u00e9es", "x": 9, "y": 3, "w": 3, "h": 3,
         "config": {"dataSourceCode": "DS_DET_KPI_GLOBAL", "dataSourceOrigin": "template", "value_field": "Montant Echues Impayees", "format": "currency", "suffix": " DH"}},
    ]),
    ("DS_DET_EVOLUTION_MENSUELLE", "Evolution Mensuelle Dettes Fourn.", [
        {"id": "w1", "type": "bar", "title": "Dettes vs Paiements", "x": 0, "y": 0, "w": 12, "h": 8,
         "config": {"dataSourceCode": "DS_DET_EVOLUTION_MENSUELLE", "dataSourceOrigin": "template", "category_field": "Periode", "value_fields": ["Dettes", "Paye"], "colors": ["#ef4444", "#10b981"]}},
        {"id": "w2", "type": "line", "title": "Impay\u00e9s Mensuels", "x": 0, "y": 8, "w": 12, "h": 6,
         "config": {"dataSourceCode": "DS_DET_EVOLUTION_MENSUELLE", "dataSourceOrigin": "template", "category_field": "Periode", "value_fields": ["Impaye"], "colors": ["#ef4444"]}},
    ]),
    ("DS_DET_REPARTITION_AGEE", "R\u00e9partition Balance Ag\u00e9e Fourn.", [
        {"id": "w1", "type": "pie", "title": "Montant par Tranche", "x": 0, "y": 0, "w": 6, "h": 8,
         "config": {"dataSourceCode": "DS_DET_REPARTITION_AGEE", "dataSourceOrigin": "template", "category_field": "Tranche", "value_field": "Montant Impaye"}},
        {"id": "w2", "type": "bar", "title": "Nb Fournisseurs par Tranche", "x": 6, "y": 0, "w": 6, "h": 8,
         "config": {"dataSourceCode": "DS_DET_REPARTITION_AGEE", "dataSourceOrigin": "template", "category_field": "Tranche", "value_fields": ["Nb Fournisseurs"], "colors": ["#f59e0b"]}},
        {"id": "w3", "type": "table", "title": "D\u00e9tail par Tranche", "x": 0, "y": 8, "w": 12, "h": 6,
         "config": {"dataSourceCode": "DS_DET_REPARTITION_AGEE", "dataSourceOrigin": "template", "columns": ["Tranche", "Montant Impaye", "Nb Echeances", "Nb Fournisseurs"]}},
    ]),
    ("DS_DET_TOP_CREANCIERS", "Top 20 Cr\u00e9anciers", [
        {"id": "w1", "type": "bar", "title": "Top 20 Cr\u00e9anciers", "x": 0, "y": 0, "w": 12, "h": 8,
         "config": {"dataSourceCode": "DS_DET_TOP_CREANCIERS", "dataSourceOrigin": "template", "category_field": "Fournisseur", "value_fields": ["Montant Impaye"], "colors": ["#ef4444"]}},
        {"id": "w2", "type": "table", "title": "D\u00e9tail Top Cr\u00e9anciers", "x": 0, "y": 8, "w": 12, "h": 6,
         "config": {"dataSourceCode": "DS_DET_TOP_CREANCIERS", "dataSourceOrigin": "template", "columns": ["Code fournisseur", "Fournisseur", "Montant Impaye", "Nb Echeances", "Max Retard Jours"]}},
    ]),
    ("DS_DET_REPARTITION_MODE", "R\u00e9partition par Mode Paiement", [
        {"id": "w1", "type": "pie", "title": "Par Mode R\u00e8glement", "x": 0, "y": 0, "w": 6, "h": 8,
         "config": {"dataSourceCode": "DS_DET_REPARTITION_MODE", "dataSourceOrigin": "template", "category_field": "Mode Reglement", "value_field": "Total Echeances"}},
        {"id": "w2", "type": "bar", "title": "Pay\u00e9 vs Reste par Mode", "x": 6, "y": 0, "w": 6, "h": 8,
         "config": {"dataSourceCode": "DS_DET_REPARTITION_MODE", "dataSourceOrigin": "template", "category_field": "Mode Reglement", "value_fields": ["Total Regle", "Reste A Payer"], "colors": ["#10b981", "#ef4444"]}},
    ]),
    ("DS_DET_TAUX_MENSUEL", "Taux Paiement Mensuel Fourn.", [
        {"id": "w1", "type": "line", "title": "Evolution Taux de Paiement", "x": 0, "y": 0, "w": 12, "h": 8,
         "config": {"dataSourceCode": "DS_DET_TAUX_MENSUEL", "dataSourceOrigin": "template", "category_field": "Periode", "value_fields": ["Taux Paiement"], "colors": ["#8b5cf6"]}},
        {"id": "w2", "type": "bar", "title": "Dettes vs Paiements", "x": 0, "y": 8, "w": 12, "h": 6,
         "config": {"dataSourceCode": "DS_DET_TAUX_MENSUEL", "dataSourceOrigin": "template", "category_field": "Periode", "value_fields": ["Dettes", "Paye"], "colors": ["#ef4444", "#10b981"]}},
    ]),
    ("DS_DET_NIVEAU_URGENCE", "Niveau Urgence Fournisseurs", [
        {"id": "w1", "type": "pie", "title": "Fournisseurs par Urgence", "x": 0, "y": 0, "w": 6, "h": 8,
         "config": {"dataSourceCode": "DS_DET_NIVEAU_URGENCE", "dataSourceOrigin": "template", "category_field": "Urgence", "value_field": "Nb Fournisseurs"}},
        {"id": "w2", "type": "bar", "title": "Montant par Urgence", "x": 6, "y": 0, "w": 6, "h": 8,
         "config": {"dataSourceCode": "DS_DET_NIVEAU_URGENCE", "dataSourceOrigin": "template", "category_field": "Urgence", "value_fields": ["Montant Impaye"], "colors": ["#ef4444"]}},
    ]),
    ("DS_DET_DECAISSEMENTS_MENS", "D\u00e9caissements Mensuels", [
        {"id": "w1", "type": "bar", "title": "D\u00e9caissements par Mois", "x": 0, "y": 0, "w": 12, "h": 8,
         "config": {"dataSourceCode": "DS_DET_DECAISSEMENTS_MENS", "dataSourceOrigin": "template", "category_field": "Periode", "value_fields": ["Total Decaisse"], "colors": ["#ef4444"]}},
        {"id": "w2", "type": "line", "title": "Nb Paiements par Mois", "x": 0, "y": 8, "w": 12, "h": 6,
         "config": {"dataSourceCode": "DS_DET_DECAISSEMENTS_MENS", "dataSourceOrigin": "template", "category_field": "Periode", "value_fields": ["Nb Paiements"], "colors": ["#3b82f6"]}},
    ]),
    ("DS_DET_SYNTHESE_ANNUELLE", "Synth\u00e8se Annuelle Dettes Fourn.", [
        {"id": "w1", "type": "bar", "title": "Dettes vs Paiements par Ann\u00e9e", "x": 0, "y": 0, "w": 8, "h": 8,
         "config": {"dataSourceCode": "DS_DET_SYNTHESE_ANNUELLE", "dataSourceOrigin": "template", "category_field": "Exercice", "value_fields": ["Total Dettes", "Total Paye"], "colors": ["#ef4444", "#10b981"]}},
        {"id": "w2", "type": "line", "title": "Taux de Paiement", "x": 8, "y": 0, "w": 4, "h": 8,
         "config": {"dataSourceCode": "DS_DET_SYNTHESE_ANNUELLE", "dataSourceOrigin": "template", "category_field": "Exercice", "value_fields": ["Taux Paiement"], "colors": ["#8b5cf6"]}},
        {"id": "w3", "type": "table", "title": "D\u00e9tail par Ann\u00e9e", "x": 0, "y": 8, "w": 12, "h": 6,
         "config": {"dataSourceCode": "DS_DET_SYNTHESE_ANNUELLE", "dataSourceOrigin": "template", "columns": ["Exercice", "Total Dettes", "Total Paye", "Reste A Payer", "Taux Paiement", "Nb Echeances", "Nb Fournisseurs"]}},
    ]),
]

# ======================================================================
MENU_ICONS = {
    "Ech\u00e9ances Fournisseurs D\u00e9tail": "FileText",
    "Dettes Impay\u00e9es": "AlertTriangle",
    "R\u00e8glements Effectu\u00e9s": "CheckCircle",
    "Balance Ag\u00e9e Fournisseurs": "Scale",
    "Ech\u00e9ances avec Imputations": "Link",
    "Factures Ech\u00e9es Non R\u00e9gl\u00e9es": "XCircle",
    "Fournisseurs Critiques": "ShieldAlert",
    "Historique Paiements": "History",
    "Ech\u00e9ances \u00e0 Venir": "CalendarClock",
    "D\u00e9lai Moyen de Paiement": "Timer",
    "Dettes par Tranche d'Age": "Layers",
    "Paiements par Mode": "CreditCard",
    "Dettes par Type Document": "FolderOpen",
    "Evolution Mensuelle Dettes": "TrendingUp",
    "Taux Paiement par Fournisseur": "Target",
    "Paiements par Tier Encaisseur": "Users",
    "TB Dettes Fournisseurs": "LayoutGrid",
    "Evolution Mensuelle Dettes Fourn.": "TrendingDown",
    "R\u00e9partition Balance Ag\u00e9e Fourn.": "PieChart",
    "Top 20 Cr\u00e9anciers": "Award",
    "R\u00e9partition par Mode Paiement": "PieChart",
    "Taux Paiement Mensuel Fourn.": "Target",
    "Niveau Urgence Fournisseurs": "ShieldAlert",
    "D\u00e9caissements Mensuels": "Banknote",
    "Synth\u00e8se Annuelle Dettes Fourn.": "CalendarDays",
}

# ======================================================================
# MAIN
# ======================================================================
def main():
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()
    print("=" * 60)
    print("  CREATION DES 25 RAPPORTS DETTES FOURNISSEURS")
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
            if any(k in low for k in ("montant", "solde", "reste", "total", "impaye", "regle", "paye", "decaiss", "dette", "echeance")):
                fmt = "currency"
            elif any(k in low for k in ("nb ", "nombre", "jours", "delai", "retard", "taux", "pourcentage")):
                fmt = "number"
            elif "date" in low: fmt = "date"
            columns.append({"field": alias, "header": alias, "format": fmt, "sortable": True, "filterable": True, "width": 150})
        total_cols = [c["field"] for c in columns if c["format"] in ("currency", "number") and "nb " not in c["field"].lower()]
        features_json = json.dumps({"show_search": True, "show_column_filters": True, "show_grouping": True, "show_column_toggle": True, "show_export": True, "show_pagination": True, "allow_sorting": True})
        cursor.execute("INSERT INTO APP_GridViews (nom, description, data_source_code, columns_config, page_size, show_totals, total_columns, features, actif) VALUES (?, ?, ?, ?, 25, 1, ?, ?, 1)",
            nom, f"Rapport Dettes Fourn. - {nom}", ds_code, json.dumps(columns), json.dumps(total_cols[:5]), features_json)
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
            nom, f"Pivot Dettes Fourn. - {nom}", ds_code, json.dumps(rows_cfg), json.dumps(vals_cfg), json.dumps(filters_cfg))
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
            nom, f"Dashboard Dettes Fourn. - {nom}", json.dumps(widgets))
        cursor.execute("SELECT @@IDENTITY")
        db_id = int(cursor.fetchone()[0])
        db_ids[ds_code] = db_id
        print(f"  + NEW Dashboard {nom} (id={db_id})")
    conn.commit()

    # --- 5. Menus ---
    print("\n[5/5] Creation des Menus...")
    cursor.execute("SELECT id FROM APP_Menus WHERE nom LIKE '%Dettes%' AND parent_id IS NULL")
    root = cursor.fetchone()
    if root:
        root_id = root[0]
        print(f"  OK EXISTS racine (id={root_id})")
    else:
        cursor.execute("INSERT INTO APP_Menus (nom, icon, type, parent_id, ordre, actif) VALUES ('Dettes Fournisseurs', 'HandCoins', 'folder', NULL, 50, 1)")
        cursor.execute("SELECT @@IDENTITY")
        root_id = int(cursor.fetchone()[0])
        print(f"  + NEW racine 'Dettes Fournisseurs' (id={root_id})")

    subfolders = [("Suivi des Dettes", "FileText", 1), ("Analyses Dettes", "BarChart3", 2), ("Tableaux de Bord", "LayoutGrid", 3)]
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
        ("Suivi des Dettes", "Ech\u00e9ances Fournisseurs D\u00e9tail", "gridview", gv_ids.get("DS_DET_ECHEANCES_DETAIL"), 1),
        ("Suivi des Dettes", "Dettes Impay\u00e9es", "gridview", gv_ids.get("DS_DET_IMPAYES"), 2),
        ("Suivi des Dettes", "R\u00e8glements Effectu\u00e9s", "gridview", gv_ids.get("DS_DET_REGLEMENTS"), 3),
        ("Suivi des Dettes", "Balance Ag\u00e9e Fournisseurs", "gridview", gv_ids.get("DS_DET_BALANCE_AGEE"), 4),
        ("Suivi des Dettes", "Ech\u00e9ances avec Imputations", "gridview", gv_ids.get("DS_DET_ECHEANCES_IMPUTATIONS"), 5),
        ("Suivi des Dettes", "Factures Ech\u00e9es Non R\u00e9gl\u00e9es", "gridview", gv_ids.get("DS_DET_ECHUES_NON_REGLEES"), 6),
        ("Suivi des Dettes", "Fournisseurs Critiques", "gridview", gv_ids.get("DS_DET_FOURNISSEURS_CRITIQUES"), 7),
        ("Suivi des Dettes", "Historique Paiements", "gridview", gv_ids.get("DS_DET_HISTORIQUE_PAIEMENTS"), 8),
        ("Suivi des Dettes", "Ech\u00e9ances \u00e0 Venir", "gridview", gv_ids.get("DS_DET_ECHEANCES_A_VENIR"), 9),
        ("Suivi des Dettes", "D\u00e9lai Moyen de Paiement", "gridview", gv_ids.get("DS_DET_DELAI_PAIEMENT"), 10),
        ("Analyses Dettes", "Dettes par Tranche d'Age", "pivot-v2", pv_ids.get("DS_DET_PIVOT_BALANCE_AGEE"), 1),
        ("Analyses Dettes", "Paiements par Mode", "pivot-v2", pv_ids.get("DS_DET_PIVOT_MODE_REGLEMENT"), 2),
        ("Analyses Dettes", "Dettes par Type Document", "pivot-v2", pv_ids.get("DS_DET_PIVOT_TYPE_DOC"), 3),
        ("Analyses Dettes", "Evolution Mensuelle Dettes", "pivot-v2", pv_ids.get("DS_DET_PIVOT_EVOLUTION"), 4),
        ("Analyses Dettes", "Taux Paiement par Fournisseur", "pivot-v2", pv_ids.get("DS_DET_PIVOT_TAUX_FOURN"), 5),
        ("Analyses Dettes", "Paiements par Tier Encaisseur", "pivot-v2", pv_ids.get("DS_DET_PIVOT_TIER_ENCAISSEUR"), 6),
        ("Tableaux de Bord", "TB Dettes Fournisseurs", "dashboard", db_ids.get("DS_DET_KPI_GLOBAL"), 1),
        ("Tableaux de Bord", "Evolution Mensuelle Dettes Fourn.", "dashboard", db_ids.get("DS_DET_EVOLUTION_MENSUELLE"), 2),
        ("Tableaux de Bord", "R\u00e9partition Balance Ag\u00e9e Fourn.", "dashboard", db_ids.get("DS_DET_REPARTITION_AGEE"), 3),
        ("Tableaux de Bord", "Top 20 Cr\u00e9anciers", "dashboard", db_ids.get("DS_DET_TOP_CREANCIERS"), 4),
        ("Tableaux de Bord", "R\u00e9partition par Mode Paiement", "dashboard", db_ids.get("DS_DET_REPARTITION_MODE"), 5),
        ("Tableaux de Bord", "Taux Paiement Mensuel Fourn.", "dashboard", db_ids.get("DS_DET_TAUX_MENSUEL"), 6),
        ("Tableaux de Bord", "Niveau Urgence Fournisseurs", "dashboard", db_ids.get("DS_DET_NIVEAU_URGENCE"), 7),
        ("Tableaux de Bord", "D\u00e9caissements Mensuels", "dashboard", db_ids.get("DS_DET_DECAISSEMENTS_MENS"), 8),
        ("Tableaux de Bord", "Synth\u00e8se Annuelle Dettes Fourn.", "dashboard", db_ids.get("DS_DET_SYNTHESE_ANNUELLE"), 9),
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
