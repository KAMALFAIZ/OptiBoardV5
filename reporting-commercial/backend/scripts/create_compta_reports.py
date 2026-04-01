# -*- coding: utf-8 -*-
"""
Creation des 25 rapports du cycle COMPTABILITE pour OptiBoard
10 GRID + 6 PIVOT + 9 DASHBOARD
Table source: Ecritures_Comptables (DWH)
"""
import pyodbc, json, re, sys

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

# Unicode column name references (accented columns from Ecritures_Comptables)
# \u00e9 = e-acute, \u00e8 = e-grave, \u00e0 = a-grave, \u00b0 = degree sign (N°)
# Date d'\u00e9criture, N\u00b0 Compte G\u00e9n\u00e9ral, Intitul\u00e9 compte g\u00e9n\u00e9ral
# Intitul\u00e9 tiers, N\u00b0 Pi\u00e8ce, N\u00b0 facture, N\u00b0 Pi\u00e8ce de tr\u00e9so
# Libell\u00e9, D\u00e9bit, Cr\u00e9dit, Report \u00e0 Nouveau
# Saisie Ech\u00e9ance, Saisie Quantit\u00e9, Cl\u00e9 Comptabilit\u00e9
# N\u00b0 interne, N\u00b0 interne de lien, Date d'\u00e9ch\u00e9ance
# R\u00e9vision, Parit\u00e9, Quantit\u00e9, Mode de r\u00e8glement -> actually r\u00e9glement
# Type \u00e0 Nouveau, R\u00e9f\u00e9rence, N\u00b0 Dossier Recouvrement
# Libell\u00e9 Journal, Ann\u00e9e

# Societe filter aliases
SOC = "(@societe IS NULL OR ec.societe = @societe)"

# ======================================================================
# 25 DATASOURCE TEMPLATES
# ======================================================================
DS_TEMPLATES = [
    # --- 1. GRID: Grand Livre General ---
    {
        "code": "DS_CPT_GRAND_LIVRE",
        "nom": "Grand Livre G\u00e9n\u00e9ral",
        "query": "SELECT "
            + "ec.[Date d'\u00e9criture] AS [Date], "
            + "ec.[N\u00b0 Compte G\u00e9n\u00e9ral] AS [Compte], "
            + "ec.[Intitul\u00e9 compte g\u00e9n\u00e9ral] AS [Intitule Compte], "
            + "ec.[Compte Tiers], ec.[Intitul\u00e9 tiers] AS [Tiers], "
            + "ec.[N\u00b0 Pi\u00e8ce] AS [Num Piece], "
            + "ec.[Code Journal], ec.[Libell\u00e9 Journal] AS [Journal], "
            + "ec.[Libell\u00e9] AS [Libelle], "
            + "ec.[D\u00e9bit], ec.[Cr\u00e9dit], "
            + "ec.[D\u00e9bit] - ec.[Cr\u00e9dit] AS [Solde], "
            + "ec.[Nature Compte], ec.[Exercice], ec.societe AS [Societe] "
            + "FROM Ecritures_Comptables ec "
            + "WHERE ec.[Date d'\u00e9criture] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "ORDER BY ec.[N\u00b0 Compte G\u00e9n\u00e9ral], ec.[Date d'\u00e9criture]",
        "params": PARAMS_DATE_SOCIETE,
        "category": "comptabilite"
    },
    # --- 2. GRID: Balance Generale ---
    {
        "code": "DS_CPT_BALANCE",
        "nom": "Balance G\u00e9n\u00e9rale",
        "query": "SELECT "
            + "ec.[N\u00b0 Compte G\u00e9n\u00e9ral] AS [Compte], "
            + "ec.[Intitul\u00e9 compte g\u00e9n\u00e9ral] AS [Intitule Compte], "
            + "ec.[Nature Compte], "
            + "SUM(ec.[D\u00e9bit]) AS [Total Debit], "
            + "SUM(ec.[Cr\u00e9dit]) AS [Total Credit], "
            + "SUM(ec.[D\u00e9bit]) - SUM(ec.[Cr\u00e9dit]) AS [Solde], "
            + "COUNT(*) AS [Nb Ecritures], "
            + "ec.societe AS [Societe] "
            + "FROM Ecritures_Comptables ec "
            + "WHERE ec.[Date d'\u00e9criture] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY ec.[N\u00b0 Compte G\u00e9n\u00e9ral], ec.[Intitul\u00e9 compte g\u00e9n\u00e9ral], ec.[Nature Compte], ec.societe "
            + "ORDER BY ec.[N\u00b0 Compte G\u00e9n\u00e9ral]",
        "params": PARAMS_DATE_SOCIETE,
        "category": "comptabilite"
    },
    # --- 3. GRID: Journal des Ecritures ---
    {
        "code": "DS_CPT_JOURNAL",
        "nom": "Journal des Ecritures",
        "query": "SELECT "
            + "ec.[Date d'\u00e9criture] AS [Date], "
            + "ec.[Code Journal], ec.[Libell\u00e9 Journal] AS [Journal], "
            + "ec.[N\u00b0 Pi\u00e8ce] AS [Num Piece], "
            + "ec.[N\u00b0 Compte G\u00e9n\u00e9ral] AS [Compte], "
            + "ec.[Intitul\u00e9 compte g\u00e9n\u00e9ral] AS [Intitule Compte], "
            + "ec.[Compte Tiers], ec.[Intitul\u00e9 tiers] AS [Tiers], "
            + "ec.[Libell\u00e9] AS [Libelle], "
            + "ec.[D\u00e9bit], ec.[Cr\u00e9dit], "
            + "ec.[Type Ecriture], ec.[Exercice], ec.societe AS [Societe] "
            + "FROM Ecritures_Comptables ec "
            + "WHERE ec.[Date d'\u00e9criture] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "ORDER BY ec.[Date d'\u00e9criture] DESC, ec.[N\u00b0 Pi\u00e8ce]",
        "params": PARAMS_DATE_SOCIETE,
        "category": "comptabilite"
    },
    # --- 4. GRID: Balance Tiers (Clients + Fournisseurs) ---
    {
        "code": "DS_CPT_BALANCE_TIERS",
        "nom": "Balance Tiers",
        "query": "SELECT "
            + "ec.[Compte Tiers], ec.[Intitul\u00e9 tiers] AS [Tiers], "
            + "ec.[Type tiers], ec.[Nature Compte], "
            + "SUM(ec.[D\u00e9bit]) AS [Total Debit], "
            + "SUM(ec.[Cr\u00e9dit]) AS [Total Credit], "
            + "SUM(ec.[D\u00e9bit]) - SUM(ec.[Cr\u00e9dit]) AS [Solde], "
            + "COUNT(*) AS [Nb Ecritures], "
            + "ec.societe AS [Societe] "
            + "FROM Ecritures_Comptables ec "
            + "WHERE ec.[Compte Tiers] IS NOT NULL AND ec.[Compte Tiers] <> '' "
            + "AND ec.[Date d'\u00e9criture] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY ec.[Compte Tiers], ec.[Intitul\u00e9 tiers], ec.[Type tiers], ec.[Nature Compte], ec.societe "
            + "ORDER BY ABS(SUM(ec.[D\u00e9bit]) - SUM(ec.[Cr\u00e9dit])) DESC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "comptabilite"
    },
    # --- 5. GRID: Ecritures de Tresorerie ---
    {
        "code": "DS_CPT_TRESORERIE",
        "nom": "Ecritures de Tr\u00e9sorerie",
        "query": "SELECT "
            + "ec.[Date d'\u00e9criture] AS [Date], "
            + "ec.[Code Journal], ec.[Libell\u00e9 Journal] AS [Journal], "
            + "ec.[N\u00b0 Pi\u00e8ce] AS [Num Piece], "
            + "ec.[N\u00b0 Compte G\u00e9n\u00e9ral] AS [Compte], "
            + "ec.[Intitul\u00e9 compte g\u00e9n\u00e9ral] AS [Intitule Compte], "
            + "ec.[Compte Tiers], ec.[Intitul\u00e9 tiers] AS [Tiers], "
            + "ec.[Libell\u00e9] AS [Libelle], "
            + "ec.[D\u00e9bit], ec.[Cr\u00e9dit], "
            + "ec.[Mode de r\u00e9glement] AS [Mode Reglement], "
            + "ec.[N\u00b0 Pi\u00e8ce de tr\u00e9so] AS [Num Piece Treso], "
            + "ec.societe AS [Societe] "
            + "FROM Ecritures_Comptables ec "
            + "WHERE ec.[Type Code Journal] = 'Tr\u00e9sorerie' "
            + "AND ec.[Date d'\u00e9criture] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "ORDER BY ec.[Date d'\u00e9criture] DESC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "comptabilite"
    },
    # --- 6. GRID: Charges par Compte ---
    {
        "code": "DS_CPT_CHARGES",
        "nom": "D\u00e9tail des Charges",
        "query": "SELECT "
            + "ec.[N\u00b0 Compte G\u00e9n\u00e9ral] AS [Compte], "
            + "ec.[Intitul\u00e9 compte g\u00e9n\u00e9ral] AS [Intitule Compte], "
            + "SUM(ec.[D\u00e9bit]) AS [Total Debit], "
            + "SUM(ec.[Cr\u00e9dit]) AS [Total Credit], "
            + "SUM(ec.[D\u00e9bit]) - SUM(ec.[Cr\u00e9dit]) AS [Montant Charge], "
            + "COUNT(*) AS [Nb Ecritures], "
            + "ec.societe AS [Societe] "
            + "FROM Ecritures_Comptables ec "
            + "WHERE ec.[Nature Compte] = 'Charge' "
            + "AND ec.[Date d'\u00e9criture] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY ec.[N\u00b0 Compte G\u00e9n\u00e9ral], ec.[Intitul\u00e9 compte g\u00e9n\u00e9ral], ec.societe "
            + "ORDER BY SUM(ec.[D\u00e9bit]) - SUM(ec.[Cr\u00e9dit]) DESC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "comptabilite"
    },
    # --- 7. GRID: Produits par Compte ---
    {
        "code": "DS_CPT_PRODUITS",
        "nom": "D\u00e9tail des Produits",
        "query": "SELECT "
            + "ec.[N\u00b0 Compte G\u00e9n\u00e9ral] AS [Compte], "
            + "ec.[Intitul\u00e9 compte g\u00e9n\u00e9ral] AS [Intitule Compte], "
            + "SUM(ec.[D\u00e9bit]) AS [Total Debit], "
            + "SUM(ec.[Cr\u00e9dit]) AS [Total Credit], "
            + "SUM(ec.[Cr\u00e9dit]) - SUM(ec.[D\u00e9bit]) AS [Montant Produit], "
            + "COUNT(*) AS [Nb Ecritures], "
            + "ec.societe AS [Societe] "
            + "FROM Ecritures_Comptables ec "
            + "WHERE ec.[Nature Compte] = 'Produit' "
            + "AND ec.[Date d'\u00e9criture] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY ec.[N\u00b0 Compte G\u00e9n\u00e9ral], ec.[Intitul\u00e9 compte g\u00e9n\u00e9ral], ec.societe "
            + "ORDER BY SUM(ec.[Cr\u00e9dit]) - SUM(ec.[D\u00e9bit]) DESC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "comptabilite"
    },
    # --- 8. GRID: Echeances Clients ---
    {
        "code": "DS_CPT_ECHEANCES_CLIENTS",
        "nom": "Ech\u00e9ances Clients",
        "query": "SELECT "
            + "ec.[Compte Tiers], ec.[Intitul\u00e9 tiers] AS [Client], "
            + "ec.[Date d'\u00e9ch\u00e9ance] AS [Date Echeance], "
            + "ec.[Date d'\u00e9criture] AS [Date Ecriture], "
            + "ec.[N\u00b0 Pi\u00e8ce] AS [Num Piece], "
            + "ec.[N\u00b0 facture] AS [Num Facture], "
            + "ec.[Libell\u00e9] AS [Libelle], "
            + "ec.[D\u00e9bit], ec.[Cr\u00e9dit], "
            + "ec.[D\u00e9bit] - ec.[Cr\u00e9dit] AS [Solde], "
            + "ec.[Lettrage], ec.[Lettre], "
            + "ec.[Mode de r\u00e9glement] AS [Mode Reglement], "
            + "ec.societe AS [Societe] "
            + "FROM Ecritures_Comptables ec "
            + "WHERE ec.[Type tiers] = 'Client' "
            + "AND ec.[Date d'\u00e9criture] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "ORDER BY ec.[Date d'\u00e9ch\u00e9ance] DESC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "comptabilite"
    },
    # --- 9. GRID: Echeances Fournisseurs ---
    {
        "code": "DS_CPT_ECHEANCES_FOURN",
        "nom": "Ech\u00e9ances Fournisseurs",
        "query": "SELECT "
            + "ec.[Compte Tiers], ec.[Intitul\u00e9 tiers] AS [Fournisseur], "
            + "ec.[Date d'\u00e9ch\u00e9ance] AS [Date Echeance], "
            + "ec.[Date d'\u00e9criture] AS [Date Ecriture], "
            + "ec.[N\u00b0 Pi\u00e8ce] AS [Num Piece], "
            + "ec.[N\u00b0 facture] AS [Num Facture], "
            + "ec.[Libell\u00e9] AS [Libelle], "
            + "ec.[D\u00e9bit], ec.[Cr\u00e9dit], "
            + "ec.[Cr\u00e9dit] - ec.[D\u00e9bit] AS [Solde], "
            + "ec.[Lettrage], ec.[Lettre], "
            + "ec.[Mode de r\u00e9glement] AS [Mode Reglement], "
            + "ec.societe AS [Societe] "
            + "FROM Ecritures_Comptables ec "
            + "WHERE ec.[Type tiers] = 'Fournisseur' "
            + "AND ec.[Date d'\u00e9criture] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "ORDER BY ec.[Date d'\u00e9ch\u00e9ance] DESC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "comptabilite"
    },
    # --- 10. GRID: Lettrage et Rapprochement ---
    {
        "code": "DS_CPT_LETTRAGE",
        "nom": "Lettrage et Rapprochement",
        "query": "SELECT "
            + "ec.[Compte Tiers], ec.[Intitul\u00e9 tiers] AS [Tiers], "
            + "ec.[Type tiers], "
            + "SUM(ec.[D\u00e9bit]) AS [Total Debit], "
            + "SUM(ec.[Cr\u00e9dit]) AS [Total Credit], "
            + "SUM(ec.[D\u00e9bit]) - SUM(ec.[Cr\u00e9dit]) AS [Solde], "
            + "SUM(CASE WHEN ec.[Lettrage] = 'OUI' THEN ec.[D\u00e9bit] - ec.[Cr\u00e9dit] ELSE 0 END) AS [Lettre], "
            + "SUM(CASE WHEN ec.[Lettrage] = 'NON' OR ec.[Lettrage] IS NULL THEN ec.[D\u00e9bit] - ec.[Cr\u00e9dit] ELSE 0 END) AS [Non Lettre], "
            + "COUNT(*) AS [Nb Ecritures], "
            + "ec.societe AS [Societe] "
            + "FROM Ecritures_Comptables ec "
            + "WHERE ec.[Compte Tiers] IS NOT NULL AND ec.[Compte Tiers] <> '' "
            + "AND ec.[Date d'\u00e9criture] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY ec.[Compte Tiers], ec.[Intitul\u00e9 tiers], ec.[Type tiers], ec.societe "
            + "ORDER BY ABS(SUM(CASE WHEN ec.[Lettrage] = 'NON' OR ec.[Lettrage] IS NULL THEN ec.[D\u00e9bit] - ec.[Cr\u00e9dit] ELSE 0 END)) DESC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "comptabilite"
    },
    # --- 11. PIVOT: Charges vs Produits par Nature ---
    {
        "code": "DS_CPT_RESULTAT_NATURE",
        "nom": "R\u00e9sultat par Nature",
        "query": "SELECT "
            + "ec.[Nature Compte], "
            + "LEFT(ec.[N\u00b0 Compte G\u00e9n\u00e9ral], 2) AS [Classe], "
            + "ec.[Mois], ec.[Ann\u00e9e] AS [Annee], "
            + "SUM(ec.[D\u00e9bit]) AS [Debit], "
            + "SUM(ec.[Cr\u00e9dit]) AS [Credit], "
            + "SUM(ec.[D\u00e9bit]) - SUM(ec.[Cr\u00e9dit]) AS [Solde], "
            + "ec.societe AS [Societe] "
            + "FROM Ecritures_Comptables ec "
            + "WHERE ec.[Nature Compte] IN ('Charge', 'Produit') "
            + "AND ec.[Date d'\u00e9criture] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY ec.[Nature Compte], LEFT(ec.[N\u00b0 Compte G\u00e9n\u00e9ral], 2), ec.[Mois], ec.[Ann\u00e9e], ec.societe",
        "params": PARAMS_DATE_SOCIETE,
        "category": "comptabilite"
    },
    # --- 12. PIVOT: Balance par Journal ---
    {
        "code": "DS_CPT_BALANCE_JOURNAL",
        "nom": "Balance par Journal",
        "query": "SELECT "
            + "ec.[Code Journal], ec.[Libell\u00e9 Journal] AS [Journal], "
            + "ec.[Type Code Journal] AS [Type Journal], "
            + "ec.[Mois], ec.[Ann\u00e9e] AS [Annee], "
            + "SUM(ec.[D\u00e9bit]) AS [Debit], "
            + "SUM(ec.[Cr\u00e9dit]) AS [Credit], "
            + "SUM(ec.[D\u00e9bit]) - SUM(ec.[Cr\u00e9dit]) AS [Solde], "
            + "COUNT(*) AS [Nb Ecritures], "
            + "ec.societe AS [Societe] "
            + "FROM Ecritures_Comptables ec "
            + "WHERE ec.[Date d'\u00e9criture] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY ec.[Code Journal], ec.[Libell\u00e9 Journal], ec.[Type Code Journal], ec.[Mois], ec.[Ann\u00e9e], ec.societe",
        "params": PARAMS_DATE_SOCIETE,
        "category": "comptabilite"
    },
    # --- 13. PIVOT: Balance par Classe Comptable ---
    {
        "code": "DS_CPT_BALANCE_CLASSE",
        "nom": "Balance par Classe Comptable",
        "query": "SELECT "
            + "LEFT(ec.[N\u00b0 Compte G\u00e9n\u00e9ral], 1) AS [Classe], "
            + "CASE LEFT(ec.[N\u00b0 Compte G\u00e9n\u00e9ral], 1) "
            + "WHEN '1' THEN 'Capitaux' WHEN '2' THEN 'Immobilisations' "
            + "WHEN '3' THEN 'Stocks' WHEN '4' THEN 'Tiers' "
            + "WHEN '5' THEN 'Tresorerie' WHEN '6' THEN 'Charges' "
            + "WHEN '7' THEN 'Produits' ELSE 'Autres' END AS [Libelle Classe], "
            + "ec.[Mois], ec.[Ann\u00e9e] AS [Annee], "
            + "SUM(ec.[D\u00e9bit]) AS [Debit], "
            + "SUM(ec.[Cr\u00e9dit]) AS [Credit], "
            + "SUM(ec.[D\u00e9bit]) - SUM(ec.[Cr\u00e9dit]) AS [Solde], "
            + "COUNT(*) AS [Nb Ecritures], "
            + "ec.societe AS [Societe] "
            + "FROM Ecritures_Comptables ec "
            + "WHERE ec.[Date d'\u00e9criture] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY LEFT(ec.[N\u00b0 Compte G\u00e9n\u00e9ral], 1), ec.[Mois], ec.[Ann\u00e9e], ec.societe",
        "params": PARAMS_DATE_SOCIETE,
        "category": "comptabilite"
    },
    # --- 14. PIVOT: Tresorerie par Banque ---
    {
        "code": "DS_CPT_TRESO_BANQUE",
        "nom": "Tr\u00e9sorerie par Banque",
        "query": "SELECT "
            + "ec.[Code Journal], ec.[Libell\u00e9 Journal] AS [Banque], "
            + "ec.[Mois], ec.[Ann\u00e9e] AS [Annee], "
            + "SUM(ec.[D\u00e9bit]) AS [Encaissements], "
            + "SUM(ec.[Cr\u00e9dit]) AS [Decaissements], "
            + "SUM(ec.[D\u00e9bit]) - SUM(ec.[Cr\u00e9dit]) AS [Solde], "
            + "COUNT(*) AS [Nb Operations], "
            + "ec.societe AS [Societe] "
            + "FROM Ecritures_Comptables ec "
            + "WHERE ec.[Type Code Journal] = 'Tr\u00e9sorerie' "
            + "AND ec.[Date d'\u00e9criture] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY ec.[Code Journal], ec.[Libell\u00e9 Journal], ec.[Mois], ec.[Ann\u00e9e], ec.societe",
        "params": PARAMS_DATE_SOCIETE,
        "category": "comptabilite"
    },
    # --- 15. PIVOT: Soldes Clients ---
    {
        "code": "DS_CPT_SOLDES_CLIENTS",
        "nom": "Soldes Clients",
        "query": "SELECT "
            + "ec.[Compte Tiers], ec.[Intitul\u00e9 tiers] AS [Client], "
            + "ec.[Mois], ec.[Ann\u00e9e] AS [Annee], "
            + "SUM(ec.[D\u00e9bit]) AS [Debit], "
            + "SUM(ec.[Cr\u00e9dit]) AS [Credit], "
            + "SUM(ec.[D\u00e9bit]) - SUM(ec.[Cr\u00e9dit]) AS [Solde], "
            + "COUNT(*) AS [Nb Ecritures], "
            + "ec.societe AS [Societe] "
            + "FROM Ecritures_Comptables ec "
            + "WHERE ec.[Type tiers] = 'Client' "
            + "AND ec.[Date d'\u00e9criture] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY ec.[Compte Tiers], ec.[Intitul\u00e9 tiers], ec.[Mois], ec.[Ann\u00e9e], ec.societe",
        "params": PARAMS_DATE_SOCIETE,
        "category": "comptabilite"
    },
    # --- 16. PIVOT: Soldes Fournisseurs ---
    {
        "code": "DS_CPT_SOLDES_FOURN",
        "nom": "Soldes Fournisseurs",
        "query": "SELECT "
            + "ec.[Compte Tiers], ec.[Intitul\u00e9 tiers] AS [Fournisseur], "
            + "ec.[Mois], ec.[Ann\u00e9e] AS [Annee], "
            + "SUM(ec.[D\u00e9bit]) AS [Debit], "
            + "SUM(ec.[Cr\u00e9dit]) AS [Credit], "
            + "SUM(ec.[Cr\u00e9dit]) - SUM(ec.[D\u00e9bit]) AS [Solde], "
            + "COUNT(*) AS [Nb Ecritures], "
            + "ec.societe AS [Societe] "
            + "FROM Ecritures_Comptables ec "
            + "WHERE ec.[Type tiers] = 'Fournisseur' "
            + "AND ec.[Date d'\u00e9criture] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY ec.[Compte Tiers], ec.[Intitul\u00e9 tiers], ec.[Mois], ec.[Ann\u00e9e], ec.societe",
        "params": PARAMS_DATE_SOCIETE,
        "category": "comptabilite"
    },
    # --- 17. DASHBOARD: KPI Comptabilite Globale ---
    {
        "code": "DS_CPT_KPI_GLOBAL",
        "nom": "KPI Comptabilit\u00e9 Globale",
        "query": "SELECT "
            + "SUM(ec.[D\u00e9bit]) AS [Total Debit], "
            + "SUM(ec.[Cr\u00e9dit]) AS [Total Credit], "
            + "COUNT(*) AS [Nb Ecritures], "
            + "COUNT(DISTINCT ec.[N\u00b0 Compte G\u00e9n\u00e9ral]) AS [Nb Comptes], "
            + "COUNT(DISTINCT ec.[Code Journal]) AS [Nb Journaux], "
            + "SUM(CASE WHEN ec.[Nature Compte] = 'Charge' THEN ec.[D\u00e9bit] - ec.[Cr\u00e9dit] ELSE 0 END) AS [Total Charges], "
            + "SUM(CASE WHEN ec.[Nature Compte] = 'Produit' THEN ec.[Cr\u00e9dit] - ec.[D\u00e9bit] ELSE 0 END) AS [Total Produits], "
            + "SUM(CASE WHEN ec.[Nature Compte] = 'Produit' THEN ec.[Cr\u00e9dit] - ec.[D\u00e9bit] ELSE 0 END) - "
            + "SUM(CASE WHEN ec.[Nature Compte] = 'Charge' THEN ec.[D\u00e9bit] - ec.[Cr\u00e9dit] ELSE 0 END) AS [Resultat], "
            + "ec.societe AS [Societe] "
            + "FROM Ecritures_Comptables ec "
            + "WHERE ec.[Date d'\u00e9criture] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY ec.societe",
        "params": PARAMS_DATE_SOCIETE,
        "category": "comptabilite"
    },
    # --- 18. DASHBOARD: Evolution Mensuelle Debit/Credit ---
    {
        "code": "DS_CPT_EVOLUTION_MENSUELLE",
        "nom": "Evolution Mensuelle Comptable",
        "query": "SELECT "
            + "ec.[Ann\u00e9e] AS [Annee], ec.[Mois], "
            + "CAST(ec.[Ann\u00e9e] AS VARCHAR) + '-' + RIGHT('0' + CAST(ec.[Mois] AS VARCHAR), 2) AS [Periode], "
            + "SUM(ec.[D\u00e9bit]) AS [Total Debit], "
            + "SUM(ec.[Cr\u00e9dit]) AS [Total Credit], "
            + "SUM(ec.[D\u00e9bit]) - SUM(ec.[Cr\u00e9dit]) AS [Solde Net], "
            + "COUNT(*) AS [Nb Ecritures], "
            + "COUNT(DISTINCT ec.[N\u00b0 Compte G\u00e9n\u00e9ral]) AS [Nb Comptes], "
            + "ec.societe AS [Societe] "
            + "FROM Ecritures_Comptables ec "
            + "WHERE ec.[Date d'\u00e9criture] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY ec.[Ann\u00e9e], ec.[Mois], ec.societe "
            + "ORDER BY ec.[Ann\u00e9e], ec.[Mois]",
        "params": PARAMS_DATE_SOCIETE,
        "category": "comptabilite"
    },
    # --- 19. DASHBOARD: Charges vs Produits Mensuel ---
    {
        "code": "DS_CPT_CHARGES_PRODUITS_MENS",
        "nom": "Charges vs Produits Mensuel",
        "query": "SELECT "
            + "ec.[Ann\u00e9e] AS [Annee], ec.[Mois], "
            + "CAST(ec.[Ann\u00e9e] AS VARCHAR) + '-' + RIGHT('0' + CAST(ec.[Mois] AS VARCHAR), 2) AS [Periode], "
            + "SUM(CASE WHEN ec.[Nature Compte] = 'Charge' THEN ec.[D\u00e9bit] - ec.[Cr\u00e9dit] ELSE 0 END) AS [Charges], "
            + "SUM(CASE WHEN ec.[Nature Compte] = 'Produit' THEN ec.[Cr\u00e9dit] - ec.[D\u00e9bit] ELSE 0 END) AS [Produits], "
            + "SUM(CASE WHEN ec.[Nature Compte] = 'Produit' THEN ec.[Cr\u00e9dit] - ec.[D\u00e9bit] ELSE 0 END) - "
            + "SUM(CASE WHEN ec.[Nature Compte] = 'Charge' THEN ec.[D\u00e9bit] - ec.[Cr\u00e9dit] ELSE 0 END) AS [Resultat], "
            + "ec.societe AS [Societe] "
            + "FROM Ecritures_Comptables ec "
            + "WHERE ec.[Nature Compte] IN ('Charge', 'Produit') "
            + "AND ec.[Date d'\u00e9criture] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY ec.[Ann\u00e9e], ec.[Mois], ec.societe "
            + "ORDER BY ec.[Ann\u00e9e], ec.[Mois]",
        "params": PARAMS_DATE_SOCIETE,
        "category": "comptabilite"
    },
    # --- 20. DASHBOARD: Repartition par Nature ---
    {
        "code": "DS_CPT_REPARTITION_NATURE",
        "nom": "R\u00e9partition par Nature Compte",
        "query": "SELECT "
            + "ec.[Nature Compte], "
            + "SUM(ec.[D\u00e9bit]) AS [Debit], "
            + "SUM(ec.[Cr\u00e9dit]) AS [Credit], "
            + "ABS(SUM(ec.[D\u00e9bit]) - SUM(ec.[Cr\u00e9dit])) AS [Solde Abs], "
            + "COUNT(*) AS [Nb Ecritures], "
            + "COUNT(DISTINCT ec.[N\u00b0 Compte G\u00e9n\u00e9ral]) AS [Nb Comptes], "
            + "ec.societe AS [Societe] "
            + "FROM Ecritures_Comptables ec "
            + "WHERE ec.[Date d'\u00e9criture] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY ec.[Nature Compte], ec.societe "
            + "ORDER BY ABS(SUM(ec.[D\u00e9bit]) - SUM(ec.[Cr\u00e9dit])) DESC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "comptabilite"
    },
    # --- 21. DASHBOARD: Flux Tresorerie ---
    {
        "code": "DS_CPT_FLUX_TRESORERIE",
        "nom": "Flux de Tr\u00e9sorerie",
        "query": "SELECT "
            + "ec.[Ann\u00e9e] AS [Annee], ec.[Mois], "
            + "CAST(ec.[Ann\u00e9e] AS VARCHAR) + '-' + RIGHT('0' + CAST(ec.[Mois] AS VARCHAR), 2) AS [Periode], "
            + "SUM(CASE WHEN ec.[Nature Compte] = 'Banque' THEN ec.[D\u00e9bit] ELSE 0 END) AS [Encaissements], "
            + "SUM(CASE WHEN ec.[Nature Compte] = 'Banque' THEN ec.[Cr\u00e9dit] ELSE 0 END) AS [Decaissements], "
            + "SUM(CASE WHEN ec.[Nature Compte] = 'Banque' THEN ec.[D\u00e9bit] - ec.[Cr\u00e9dit] ELSE 0 END) AS [Flux Net], "
            + "SUM(CASE WHEN ec.[Nature Compte] = 'Caisse' THEN ec.[D\u00e9bit] - ec.[Cr\u00e9dit] ELSE 0 END) AS [Flux Caisse], "
            + "ec.societe AS [Societe] "
            + "FROM Ecritures_Comptables ec "
            + "WHERE ec.[Nature Compte] IN ('Banque', 'Caisse') "
            + "AND ec.[Date d'\u00e9criture] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY ec.[Ann\u00e9e], ec.[Mois], ec.societe "
            + "ORDER BY ec.[Ann\u00e9e], ec.[Mois]",
        "params": PARAMS_DATE_SOCIETE,
        "category": "comptabilite"
    },
    # --- 22. DASHBOARD: Top 20 Clients par Solde ---
    {
        "code": "DS_CPT_TOP_CLIENTS",
        "nom": "Top Clients par Solde",
        "query": "SELECT TOP 20 "
            + "ec.[Compte Tiers], ec.[Intitul\u00e9 tiers] AS [Client], "
            + "SUM(ec.[D\u00e9bit]) AS [Total Debit], "
            + "SUM(ec.[Cr\u00e9dit]) AS [Total Credit], "
            + "SUM(ec.[D\u00e9bit]) - SUM(ec.[Cr\u00e9dit]) AS [Solde], "
            + "COUNT(*) AS [Nb Ecritures], "
            + "ec.societe AS [Societe] "
            + "FROM Ecritures_Comptables ec "
            + "WHERE ec.[Type tiers] = 'Client' "
            + "AND ec.[Date d'\u00e9criture] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY ec.[Compte Tiers], ec.[Intitul\u00e9 tiers], ec.societe "
            + "HAVING SUM(ec.[D\u00e9bit]) - SUM(ec.[Cr\u00e9dit]) > 0 "
            + "ORDER BY SUM(ec.[D\u00e9bit]) - SUM(ec.[Cr\u00e9dit]) DESC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "comptabilite"
    },
    # --- 23. DASHBOARD: Top 20 Fournisseurs par Solde ---
    {
        "code": "DS_CPT_TOP_FOURNISSEURS",
        "nom": "Top Fournisseurs par Solde",
        "query": "SELECT TOP 20 "
            + "ec.[Compte Tiers], ec.[Intitul\u00e9 tiers] AS [Fournisseur], "
            + "SUM(ec.[D\u00e9bit]) AS [Total Debit], "
            + "SUM(ec.[Cr\u00e9dit]) AS [Total Credit], "
            + "SUM(ec.[Cr\u00e9dit]) - SUM(ec.[D\u00e9bit]) AS [Solde], "
            + "COUNT(*) AS [Nb Ecritures], "
            + "ec.societe AS [Societe] "
            + "FROM Ecritures_Comptables ec "
            + "WHERE ec.[Type tiers] = 'Fournisseur' "
            + "AND ec.[Date d'\u00e9criture] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY ec.[Compte Tiers], ec.[Intitul\u00e9 tiers], ec.societe "
            + "HAVING SUM(ec.[Cr\u00e9dit]) - SUM(ec.[D\u00e9bit]) > 0 "
            + "ORDER BY SUM(ec.[Cr\u00e9dit]) - SUM(ec.[D\u00e9bit]) DESC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "comptabilite"
    },
    # --- 24. DASHBOARD: Repartition par Type Journal ---
    {
        "code": "DS_CPT_REPARTITION_JOURNAL",
        "nom": "R\u00e9partition par Type Journal",
        "query": "SELECT "
            + "ec.[Type Code Journal] AS [Type Journal], "
            + "SUM(ec.[D\u00e9bit]) AS [Debit], "
            + "SUM(ec.[Cr\u00e9dit]) AS [Credit], "
            + "COUNT(*) AS [Nb Ecritures], "
            + "COUNT(DISTINCT ec.[Code Journal]) AS [Nb Journaux], "
            + "ec.societe AS [Societe] "
            + "FROM Ecritures_Comptables ec "
            + "WHERE ec.[Date d'\u00e9criture] BETWEEN @dateDebut AND @dateFin AND " + SOC + " "
            + "GROUP BY ec.[Type Code Journal], ec.societe "
            + "ORDER BY SUM(ec.[D\u00e9bit]) DESC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "comptabilite"
    },
    # --- 25. DASHBOARD: Synthese Annuelle ---
    {
        "code": "DS_CPT_SYNTHESE_ANNUELLE",
        "nom": "Synth\u00e8se Annuelle Comptable",
        "query": "SELECT "
            + "ec.[Exercice], "
            + "SUM(ec.[D\u00e9bit]) AS [Total Debit], "
            + "SUM(ec.[Cr\u00e9dit]) AS [Total Credit], "
            + "COUNT(*) AS [Nb Ecritures], "
            + "COUNT(DISTINCT ec.[N\u00b0 Compte G\u00e9n\u00e9ral]) AS [Nb Comptes], "
            + "COUNT(DISTINCT ec.[Code Journal]) AS [Nb Journaux], "
            + "SUM(CASE WHEN ec.[Nature Compte] = 'Charge' THEN ec.[D\u00e9bit] - ec.[Cr\u00e9dit] ELSE 0 END) AS [Total Charges], "
            + "SUM(CASE WHEN ec.[Nature Compte] = 'Produit' THEN ec.[Cr\u00e9dit] - ec.[D\u00e9bit] ELSE 0 END) AS [Total Produits], "
            + "SUM(CASE WHEN ec.[Nature Compte] = 'Produit' THEN ec.[Cr\u00e9dit] - ec.[D\u00e9bit] ELSE 0 END) - "
            + "SUM(CASE WHEN ec.[Nature Compte] = 'Charge' THEN ec.[D\u00e9bit] - ec.[Cr\u00e9dit] ELSE 0 END) AS [Resultat], "
            + "SUM(CASE WHEN ec.[Nature Compte] = 'Banque' THEN ec.[D\u00e9bit] - ec.[Cr\u00e9dit] ELSE 0 END) AS [Solde Banques], "
            + "ec.societe AS [Societe] "
            + "FROM Ecritures_Comptables ec "
            + "WHERE " + SOC + " "
            + "GROUP BY ec.[Exercice], ec.societe "
            + "ORDER BY ec.[Exercice]",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "comptabilite"
    },
]

# ======================================================================
# 10 GRIDVIEWS
# ======================================================================
GRIDVIEWS = [
    ("DS_CPT_GRAND_LIVRE",        "Grand Livre G\u00e9n\u00e9ral"),
    ("DS_CPT_BALANCE",            "Balance G\u00e9n\u00e9rale"),
    ("DS_CPT_JOURNAL",            "Journal des Ecritures"),
    ("DS_CPT_BALANCE_TIERS",      "Balance Tiers"),
    ("DS_CPT_TRESORERIE",         "Ecritures de Tr\u00e9sorerie"),
    ("DS_CPT_CHARGES",            "D\u00e9tail des Charges"),
    ("DS_CPT_PRODUITS",           "D\u00e9tail des Produits"),
    ("DS_CPT_ECHEANCES_CLIENTS",  "Ech\u00e9ances Clients"),
    ("DS_CPT_ECHEANCES_FOURN",    "Ech\u00e9ances Fournisseurs"),
    ("DS_CPT_LETTRAGE",           "Lettrage et Rapprochement"),
]

# ======================================================================
# 6 PIVOTS
# ======================================================================
PIVOTS = [
    ("DS_CPT_RESULTAT_NATURE", "R\u00e9sultat par Nature",
     [{"field": "Nature Compte"}, {"field": "Classe"}],
     [{"field": "Debit", "aggregation": "sum"}, {"field": "Credit", "aggregation": "sum"}, {"field": "Solde", "aggregation": "sum"}],
     [{"field": "Societe"}, {"field": "Annee"}]),

    ("DS_CPT_BALANCE_JOURNAL", "Balance par Journal",
     [{"field": "Code Journal"}, {"field": "Journal"}],
     [{"field": "Debit", "aggregation": "sum"}, {"field": "Credit", "aggregation": "sum"}, {"field": "Solde", "aggregation": "sum"}],
     [{"field": "Societe"}, {"field": "Type Journal"}]),

    ("DS_CPT_BALANCE_CLASSE", "Balance par Classe",
     [{"field": "Classe"}, {"field": "Libelle Classe"}],
     [{"field": "Debit", "aggregation": "sum"}, {"field": "Credit", "aggregation": "sum"}, {"field": "Solde", "aggregation": "sum"}, {"field": "Nb Ecritures", "aggregation": "sum"}],
     [{"field": "Societe"}, {"field": "Annee"}]),

    ("DS_CPT_TRESO_BANQUE", "Tr\u00e9sorerie par Banque",
     [{"field": "Code Journal"}, {"field": "Banque"}],
     [{"field": "Encaissements", "aggregation": "sum"}, {"field": "Decaissements", "aggregation": "sum"}, {"field": "Solde", "aggregation": "sum"}],
     [{"field": "Societe"}]),

    ("DS_CPT_SOLDES_CLIENTS", "Soldes Clients",
     [{"field": "Compte Tiers"}, {"field": "Client"}],
     [{"field": "Debit", "aggregation": "sum"}, {"field": "Credit", "aggregation": "sum"}, {"field": "Solde", "aggregation": "sum"}],
     [{"field": "Societe"}]),

    ("DS_CPT_SOLDES_FOURN", "Soldes Fournisseurs",
     [{"field": "Compte Tiers"}, {"field": "Fournisseur"}],
     [{"field": "Debit", "aggregation": "sum"}, {"field": "Credit", "aggregation": "sum"}, {"field": "Solde", "aggregation": "sum"}],
     [{"field": "Societe"}]),
]

# ======================================================================
# 9 DASHBOARDS
# ======================================================================
DASHBOARDS = [
    ("DS_CPT_KPI_GLOBAL", "TB Comptabilit\u00e9 Globale", [
        {"id": "w1", "type": "kpi", "title": "Total D\u00e9bit", "x": 0, "y": 0, "w": 3, "h": 3,
         "config": {"dataSourceCode": "DS_CPT_KPI_GLOBAL", "dataSourceOrigin": "template",
                    "value_field": "Total Debit", "format": "currency", "prefix": "", "suffix": " DH"}},
        {"id": "w2", "type": "kpi", "title": "Total Cr\u00e9dit", "x": 3, "y": 0, "w": 3, "h": 3,
         "config": {"dataSourceCode": "DS_CPT_KPI_GLOBAL", "dataSourceOrigin": "template",
                    "value_field": "Total Credit", "format": "currency", "prefix": "", "suffix": " DH"}},
        {"id": "w3", "type": "kpi", "title": "R\u00e9sultat", "x": 6, "y": 0, "w": 3, "h": 3,
         "config": {"dataSourceCode": "DS_CPT_KPI_GLOBAL", "dataSourceOrigin": "template",
                    "value_field": "Resultat", "format": "currency", "prefix": "", "suffix": " DH",
                    "conditional_color": [{"operator": ">=", "value": 0, "color": "#10b981"}, {"operator": "<", "value": 0, "color": "#ef4444"}]}},
        {"id": "w4", "type": "kpi", "title": "Nb Ecritures", "x": 9, "y": 0, "w": 3, "h": 3,
         "config": {"dataSourceCode": "DS_CPT_KPI_GLOBAL", "dataSourceOrigin": "template",
                    "value_field": "Nb Ecritures", "format": "number"}},
        {"id": "w5", "type": "kpi", "title": "Total Charges", "x": 0, "y": 3, "w": 4, "h": 3,
         "config": {"dataSourceCode": "DS_CPT_KPI_GLOBAL", "dataSourceOrigin": "template",
                    "value_field": "Total Charges", "format": "currency", "suffix": " DH"}},
        {"id": "w6", "type": "kpi", "title": "Total Produits", "x": 4, "y": 3, "w": 4, "h": 3,
         "config": {"dataSourceCode": "DS_CPT_KPI_GLOBAL", "dataSourceOrigin": "template",
                    "value_field": "Total Produits", "format": "currency", "suffix": " DH"}},
        {"id": "w7", "type": "kpi", "title": "Nb Comptes", "x": 8, "y": 3, "w": 2, "h": 3,
         "config": {"dataSourceCode": "DS_CPT_KPI_GLOBAL", "dataSourceOrigin": "template",
                    "value_field": "Nb Comptes", "format": "number"}},
        {"id": "w8", "type": "kpi", "title": "Nb Journaux", "x": 10, "y": 3, "w": 2, "h": 3,
         "config": {"dataSourceCode": "DS_CPT_KPI_GLOBAL", "dataSourceOrigin": "template",
                    "value_field": "Nb Journaux", "format": "number"}},
    ]),
    ("DS_CPT_EVOLUTION_MENSUELLE", "Evolution Mensuelle Comptable", [
        {"id": "w1", "type": "bar", "title": "D\u00e9bit / Cr\u00e9dit par Mois", "x": 0, "y": 0, "w": 12, "h": 8,
         "config": {"dataSourceCode": "DS_CPT_EVOLUTION_MENSUELLE", "dataSourceOrigin": "template",
                    "category_field": "Periode", "value_fields": ["Total Debit", "Total Credit"],
                    "colors": ["#3b82f6", "#ef4444"]}},
        {"id": "w2", "type": "line", "title": "Solde Net Mensuel", "x": 0, "y": 8, "w": 12, "h": 6,
         "config": {"dataSourceCode": "DS_CPT_EVOLUTION_MENSUELLE", "dataSourceOrigin": "template",
                    "category_field": "Periode", "value_fields": ["Solde Net"],
                    "colors": ["#10b981"]}},
    ]),
    ("DS_CPT_CHARGES_PRODUITS_MENS", "Charges vs Produits", [
        {"id": "w1", "type": "bar", "title": "Charges vs Produits par Mois", "x": 0, "y": 0, "w": 12, "h": 8,
         "config": {"dataSourceCode": "DS_CPT_CHARGES_PRODUITS_MENS", "dataSourceOrigin": "template",
                    "category_field": "Periode", "value_fields": ["Charges", "Produits"],
                    "colors": ["#ef4444", "#10b981"]}},
        {"id": "w2", "type": "line", "title": "R\u00e9sultat Mensuel", "x": 0, "y": 8, "w": 12, "h": 6,
         "config": {"dataSourceCode": "DS_CPT_CHARGES_PRODUITS_MENS", "dataSourceOrigin": "template",
                    "category_field": "Periode", "value_fields": ["Resultat"],
                    "colors": ["#8b5cf6"]}},
    ]),
    ("DS_CPT_REPARTITION_NATURE", "R\u00e9partition par Nature Compte", [
        {"id": "w1", "type": "pie", "title": "R\u00e9partition par Nature (Volume)", "x": 0, "y": 0, "w": 6, "h": 8,
         "config": {"dataSourceCode": "DS_CPT_REPARTITION_NATURE", "dataSourceOrigin": "template",
                    "category_field": "Nature Compte", "value_field": "Nb Ecritures"}},
        {"id": "w2", "type": "pie", "title": "R\u00e9partition par Nature (Montant)", "x": 6, "y": 0, "w": 6, "h": 8,
         "config": {"dataSourceCode": "DS_CPT_REPARTITION_NATURE", "dataSourceOrigin": "template",
                    "category_field": "Nature Compte", "value_field": "Solde Abs"}},
        {"id": "w3", "type": "table", "title": "D\u00e9tail par Nature", "x": 0, "y": 8, "w": 12, "h": 6,
         "config": {"dataSourceCode": "DS_CPT_REPARTITION_NATURE", "dataSourceOrigin": "template",
                    "columns": ["Nature Compte", "Debit", "Credit", "Solde Abs", "Nb Ecritures", "Nb Comptes"]}},
    ]),
    ("DS_CPT_FLUX_TRESORERIE", "Flux de Tr\u00e9sorerie", [
        {"id": "w1", "type": "bar", "title": "Encaissements vs D\u00e9caissements", "x": 0, "y": 0, "w": 12, "h": 8,
         "config": {"dataSourceCode": "DS_CPT_FLUX_TRESORERIE", "dataSourceOrigin": "template",
                    "category_field": "Periode", "value_fields": ["Encaissements", "Decaissements"],
                    "colors": ["#10b981", "#ef4444"]}},
        {"id": "w2", "type": "line", "title": "Flux Net Bancaire", "x": 0, "y": 8, "w": 8, "h": 6,
         "config": {"dataSourceCode": "DS_CPT_FLUX_TRESORERIE", "dataSourceOrigin": "template",
                    "category_field": "Periode", "value_fields": ["Flux Net"],
                    "colors": ["#3b82f6"]}},
        {"id": "w3", "type": "line", "title": "Flux Caisse", "x": 8, "y": 8, "w": 4, "h": 6,
         "config": {"dataSourceCode": "DS_CPT_FLUX_TRESORERIE", "dataSourceOrigin": "template",
                    "category_field": "Periode", "value_fields": ["Flux Caisse"],
                    "colors": ["#f59e0b"]}},
    ]),
    ("DS_CPT_TOP_CLIENTS", "Top 20 Clients Comptable", [
        {"id": "w1", "type": "bar", "title": "Top 20 Clients par Solde", "x": 0, "y": 0, "w": 12, "h": 8,
         "config": {"dataSourceCode": "DS_CPT_TOP_CLIENTS", "dataSourceOrigin": "template",
                    "category_field": "Client", "value_fields": ["Solde"],
                    "colors": ["#3b82f6"]}},
        {"id": "w2", "type": "table", "title": "D\u00e9tail Top Clients", "x": 0, "y": 8, "w": 12, "h": 6,
         "config": {"dataSourceCode": "DS_CPT_TOP_CLIENTS", "dataSourceOrigin": "template",
                    "columns": ["Compte Tiers", "Client", "Total Debit", "Total Credit", "Solde", "Nb Ecritures"]}},
    ]),
    ("DS_CPT_TOP_FOURNISSEURS", "Top 20 Fournisseurs Comptable", [
        {"id": "w1", "type": "bar", "title": "Top 20 Fournisseurs par Solde", "x": 0, "y": 0, "w": 12, "h": 8,
         "config": {"dataSourceCode": "DS_CPT_TOP_FOURNISSEURS", "dataSourceOrigin": "template",
                    "category_field": "Fournisseur", "value_fields": ["Solde"],
                    "colors": ["#ef4444"]}},
        {"id": "w2", "type": "table", "title": "D\u00e9tail Top Fournisseurs", "x": 0, "y": 8, "w": 12, "h": 6,
         "config": {"dataSourceCode": "DS_CPT_TOP_FOURNISSEURS", "dataSourceOrigin": "template",
                    "columns": ["Compte Tiers", "Fournisseur", "Total Debit", "Total Credit", "Solde", "Nb Ecritures"]}},
    ]),
    ("DS_CPT_REPARTITION_JOURNAL", "R\u00e9partition par Type Journal", [
        {"id": "w1", "type": "pie", "title": "Volume par Type Journal", "x": 0, "y": 0, "w": 6, "h": 8,
         "config": {"dataSourceCode": "DS_CPT_REPARTITION_JOURNAL", "dataSourceOrigin": "template",
                    "category_field": "Type Journal", "value_field": "Nb Ecritures"}},
        {"id": "w2", "type": "bar", "title": "Montants par Type Journal", "x": 6, "y": 0, "w": 6, "h": 8,
         "config": {"dataSourceCode": "DS_CPT_REPARTITION_JOURNAL", "dataSourceOrigin": "template",
                    "category_field": "Type Journal", "value_fields": ["Debit", "Credit"],
                    "colors": ["#3b82f6", "#ef4444"]}},
    ]),
    ("DS_CPT_SYNTHESE_ANNUELLE", "Synth\u00e8se Annuelle Comptable", [
        {"id": "w1", "type": "bar", "title": "D\u00e9bit / Cr\u00e9dit par Exercice", "x": 0, "y": 0, "w": 8, "h": 8,
         "config": {"dataSourceCode": "DS_CPT_SYNTHESE_ANNUELLE", "dataSourceOrigin": "template",
                    "category_field": "Exercice", "value_fields": ["Total Debit", "Total Credit"],
                    "colors": ["#3b82f6", "#ef4444"]}},
        {"id": "w2", "type": "line", "title": "R\u00e9sultat par Exercice", "x": 8, "y": 0, "w": 4, "h": 8,
         "config": {"dataSourceCode": "DS_CPT_SYNTHESE_ANNUELLE", "dataSourceOrigin": "template",
                    "category_field": "Exercice", "value_fields": ["Resultat"],
                    "colors": ["#10b981"]}},
        {"id": "w3", "type": "bar", "title": "Charges vs Produits par Exercice", "x": 0, "y": 8, "w": 8, "h": 6,
         "config": {"dataSourceCode": "DS_CPT_SYNTHESE_ANNUELLE", "dataSourceOrigin": "template",
                    "category_field": "Exercice", "value_fields": ["Total Charges", "Total Produits"],
                    "colors": ["#ef4444", "#10b981"]}},
        {"id": "w4", "type": "kpi", "title": "Solde Banques", "x": 8, "y": 8, "w": 4, "h": 6,
         "config": {"dataSourceCode": "DS_CPT_SYNTHESE_ANNUELLE", "dataSourceOrigin": "template",
                    "value_field": "Solde Banques", "format": "currency", "suffix": " DH"}},
    ]),
]

# ======================================================================
# Menu icons
# ======================================================================
MENU_ICONS = {
    "Grand Livre G\u00e9n\u00e9ral": "BookOpen",
    "Balance G\u00e9n\u00e9rale": "Scale",
    "Journal des Ecritures": "FileText",
    "Balance Tiers": "Users",
    "Ecritures de Tr\u00e9sorerie": "Landmark",
    "D\u00e9tail des Charges": "TrendingDown",
    "D\u00e9tail des Produits": "TrendingUp",
    "Ech\u00e9ances Clients": "Clock",
    "Ech\u00e9ances Fournisseurs": "Timer",
    "Lettrage et Rapprochement": "Link",
    "R\u00e9sultat par Nature": "PieChart",
    "Balance par Journal": "BookOpen",
    "Balance par Classe": "Layers",
    "Tr\u00e9sorerie par Banque": "Landmark",
    "Soldes Clients": "UserCheck",
    "Soldes Fournisseurs": "Truck",
    "TB Comptabilit\u00e9 Globale": "LayoutGrid",
    "Evolution Mensuelle Comptable": "TrendingUp",
    "Charges vs Produits": "GitCompare",
    "R\u00e9partition par Nature Compte": "PieChart",
    "Flux de Tr\u00e9sorerie": "Waves",
    "Top 20 Clients Comptable": "Award",
    "Top 20 Fournisseurs Comptable": "Award",
    "R\u00e9partition par Type Journal": "PieChart",
    "Synth\u00e8se Annuelle Comptable": "CalendarDays",
}


# ======================================================================
# MAIN
# ======================================================================
def main():
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()

    print("=" * 60)
    print("  CREATION DES 25 RAPPORTS COMPTABILITE")
    print("=" * 60)

    # --- 1. DataSource Templates ---
    print("\n[1/5] Creation des DataSource Templates...")
    ds_ids = {}
    for ds in DS_TEMPLATES:
        cursor.execute("SELECT id FROM APP_DataSources_Templates WHERE code = ?", ds["code"])
        existing = cursor.fetchone()
        if existing:
            cursor.execute("""UPDATE APP_DataSources_Templates
                SET nom=?, query_template=?, parameters=?, category=?, actif=1
                WHERE code=?""", ds["nom"], ds["query"], ds["params"], ds["category"], ds["code"])
            ds_ids[ds["code"]] = existing[0]
            print(f"  OK MAJ {ds['code']} (id={existing[0]})")
        else:
            cursor.execute("""INSERT INTO APP_DataSources_Templates
                (code, nom, description, query_template, parameters, category, actif)
                VALUES (?, ?, ?, ?, ?, ?, 1)""",
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
        if not row:
            print(f"  XX SKIP {nom} - template {ds_code} not found")
            continue

        query = row[0]
        aliases = re.findall(r'AS\s+\[([^\]]+)\]', query, re.IGNORECASE)
        if not aliases:
            aliases = re.findall(r'ec\.\[([^\]]+)\]', query)

        columns = []
        for alias in aliases:
            if alias.lower() in ('societe',):
                continue
            fmt = "text"
            low = alias.lower()
            if any(k in low for k in ("debit", "credit", "solde", "montant", "valeur", "charge", "produit", "total", "lettre", "non lettre")):
                fmt = "currency"
            elif any(k in low for k in ("nb ", "nombre")):
                fmt = "number"
            elif "date" in low:
                fmt = "date"
            columns.append({"field": alias, "header": alias, "format": fmt, "sortable": True, "filterable": True, "width": 150})

        total_cols = [c["field"] for c in columns if c["format"] in ("currency", "number") and "nb " not in c["field"].lower()]

        columns_json = json.dumps(columns)
        total_cols_json = json.dumps(total_cols[:5])
        features_json = json.dumps({"show_search": True, "show_column_filters": True, "show_grouping": True,
                                     "show_column_toggle": True, "show_export": True, "show_pagination": True, "allow_sorting": True})

        cursor.execute("""INSERT INTO APP_GridViews
            (nom, description, data_source_code, columns_config, page_size, show_totals, total_columns, features, actif)
            VALUES (?, ?, ?, ?, 25, 1, ?, ?, 1)""",
            nom, f"Rapport Comptabilite - {nom}", ds_code, columns_json, total_cols_json, features_json)
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

        cursor.execute("""INSERT INTO APP_Pivots_V2
            (nom, description, data_source_code, rows_config, columns_config, values_config, filters_config, show_grand_totals, show_subtotals)
            VALUES (?, ?, ?, ?, '[]', ?, ?, 1, 1)""",
            nom, f"Pivot Comptabilite - {nom}", ds_code,
            json.dumps(rows_cfg), json.dumps(vals_cfg), json.dumps(filters_cfg))
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

        cursor.execute("""INSERT INTO APP_Dashboards
            (nom, description, widgets, actif)
            VALUES (?, ?, ?, 1)""",
            nom, f"Dashboard Comptabilite - {nom}", json.dumps(widgets))
        cursor.execute("SELECT @@IDENTITY")
        db_id = int(cursor.fetchone()[0])
        db_ids[ds_code] = db_id
        print(f"  + NEW Dashboard {nom} (id={db_id})")
    conn.commit()

    # --- 5. Menus ---
    print("\n[5/5] Creation des Menus...")

    # Menu racine Comptabilite
    cursor.execute("SELECT id FROM APP_Menus WHERE nom = 'Comptabilit\u00e9' AND parent_id IS NULL")
    root = cursor.fetchone()
    if not root:
        cursor.execute("SELECT id FROM APP_Menus WHERE nom = 'Comptabilite' AND parent_id IS NULL")
        root = cursor.fetchone()
    if root:
        root_id = root[0]
        print(f"  OK EXISTS racine 'Comptabilite' (id={root_id})")
    else:
        cursor.execute("""INSERT INTO APP_Menus (nom, icon, type, parent_id, ordre, actif)
            VALUES ('Comptabilit\u00e9', 'Calculator', 'folder', NULL, 30, 1)""")
        cursor.execute("SELECT @@IDENTITY")
        root_id = int(cursor.fetchone()[0])
        print(f"  + NEW racine 'Comptabilite' (id={root_id})")

    # Sous-dossiers
    subfolders = [
        ("Documents Comptables", "FileText", 1),
        ("Analyses Comptables", "BarChart3", 2),
        ("Tableaux de Bord", "LayoutGrid", 3),
    ]
    sf_ids = {}
    for sf_label, sf_icon, sf_ordre in subfolders:
        cursor.execute("SELECT id FROM APP_Menus WHERE nom = ? AND parent_id = ?", sf_label, root_id)
        existing = cursor.fetchone()
        if existing:
            sf_ids[sf_label] = existing[0]
            print(f"  OK EXISTS dossier '{sf_label}' (id={existing[0]})")
        else:
            cursor.execute("""INSERT INTO APP_Menus (nom, icon, type, parent_id, ordre, actif)
                VALUES (?, ?, 'folder', ?, ?, 1)""", sf_label, sf_icon, root_id, sf_ordre)
            cursor.execute("SELECT @@IDENTITY")
            sf_ids[sf_label] = int(cursor.fetchone()[0])
            print(f"  + NEW dossier '{sf_label}' (id={sf_ids[sf_label]})")

    # Menu items
    menu_items = [
        # Documents Comptables (10 gridviews)
        ("Documents Comptables", "Grand Livre G\u00e9n\u00e9ral", "gridview", gv_ids.get("DS_CPT_GRAND_LIVRE"), 1),
        ("Documents Comptables", "Balance G\u00e9n\u00e9rale", "gridview", gv_ids.get("DS_CPT_BALANCE"), 2),
        ("Documents Comptables", "Journal des Ecritures", "gridview", gv_ids.get("DS_CPT_JOURNAL"), 3),
        ("Documents Comptables", "Balance Tiers", "gridview", gv_ids.get("DS_CPT_BALANCE_TIERS"), 4),
        ("Documents Comptables", "Ecritures de Tr\u00e9sorerie", "gridview", gv_ids.get("DS_CPT_TRESORERIE"), 5),
        ("Documents Comptables", "D\u00e9tail des Charges", "gridview", gv_ids.get("DS_CPT_CHARGES"), 6),
        ("Documents Comptables", "D\u00e9tail des Produits", "gridview", gv_ids.get("DS_CPT_PRODUITS"), 7),
        ("Documents Comptables", "Ech\u00e9ances Clients", "gridview", gv_ids.get("DS_CPT_ECHEANCES_CLIENTS"), 8),
        ("Documents Comptables", "Ech\u00e9ances Fournisseurs", "gridview", gv_ids.get("DS_CPT_ECHEANCES_FOURN"), 9),
        ("Documents Comptables", "Lettrage et Rapprochement", "gridview", gv_ids.get("DS_CPT_LETTRAGE"), 10),
        # Analyses Comptables (6 pivots)
        ("Analyses Comptables", "R\u00e9sultat par Nature", "pivot-v2", pv_ids.get("DS_CPT_RESULTAT_NATURE"), 1),
        ("Analyses Comptables", "Balance par Journal", "pivot-v2", pv_ids.get("DS_CPT_BALANCE_JOURNAL"), 2),
        ("Analyses Comptables", "Balance par Classe", "pivot-v2", pv_ids.get("DS_CPT_BALANCE_CLASSE"), 3),
        ("Analyses Comptables", "Tr\u00e9sorerie par Banque", "pivot-v2", pv_ids.get("DS_CPT_TRESO_BANQUE"), 4),
        ("Analyses Comptables", "Soldes Clients", "pivot-v2", pv_ids.get("DS_CPT_SOLDES_CLIENTS"), 5),
        ("Analyses Comptables", "Soldes Fournisseurs", "pivot-v2", pv_ids.get("DS_CPT_SOLDES_FOURN"), 6),
        # Tableaux de Bord (9 dashboards)
        ("Tableaux de Bord", "TB Comptabilit\u00e9 Globale", "dashboard", db_ids.get("DS_CPT_KPI_GLOBAL"), 1),
        ("Tableaux de Bord", "Evolution Mensuelle Comptable", "dashboard", db_ids.get("DS_CPT_EVOLUTION_MENSUELLE"), 2),
        ("Tableaux de Bord", "Charges vs Produits", "dashboard", db_ids.get("DS_CPT_CHARGES_PRODUITS_MENS"), 3),
        ("Tableaux de Bord", "R\u00e9partition par Nature Compte", "dashboard", db_ids.get("DS_CPT_REPARTITION_NATURE"), 4),
        ("Tableaux de Bord", "Flux de Tr\u00e9sorerie", "dashboard", db_ids.get("DS_CPT_FLUX_TRESORERIE"), 5),
        ("Tableaux de Bord", "Top 20 Clients Comptable", "dashboard", db_ids.get("DS_CPT_TOP_CLIENTS"), 6),
        ("Tableaux de Bord", "Top 20 Fournisseurs Comptable", "dashboard", db_ids.get("DS_CPT_TOP_FOURNISSEURS"), 7),
        ("Tableaux de Bord", "R\u00e9partition par Type Journal", "dashboard", db_ids.get("DS_CPT_REPARTITION_JOURNAL"), 8),
        ("Tableaux de Bord", "Synth\u00e8se Annuelle Comptable", "dashboard", db_ids.get("DS_CPT_SYNTHESE_ANNUELLE"), 9),
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
            cursor.execute("""UPDATE APP_Menus SET icon=?, type=?, target_id=?, ordre=?, actif=1
                WHERE id=?""", icon, menu_type, target_id, ordre, existing[0])
            print(f"  OK MAJ '{label}' ({menu_type} -> id {target_id})")
        else:
            cursor.execute("""INSERT INTO APP_Menus (nom, icon, type, target_id, parent_id, ordre, actif)
                VALUES (?, ?, ?, ?, ?, ?, 1)""", label, icon, menu_type, target_id, parent_id, ordre)
            print(f"  + NEW '{label}' ({menu_type} -> id {target_id})")
        menu_count += 1

    conn.commit()

    # --- Resume ---
    print("\n" + "=" * 60)
    print("  RESUME")
    print("=" * 60)
    print(f"  DataSource Templates : {len(DS_TEMPLATES)}")
    print(f"  GridViews            : {len(GRIDVIEWS)}")
    print(f"  Pivots V2            : {len(PIVOTS)}")
    print(f"  Dashboards           : {len(DASHBOARDS)}")
    print(f"  Menus                : {menu_count} items + 1 racine + {len(subfolders)} dossiers")
    print(f"  TOTAL                : {len(DS_TEMPLATES)} DS + {len(GRIDVIEWS)} GV + {len(PIVOTS)} PV + {len(DASHBOARDS)} DB")
    print("=" * 60)

    conn.close()
    print("\n[OK] Done!")

if __name__ == "__main__":
    main()
