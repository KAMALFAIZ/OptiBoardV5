# -*- coding: utf-8 -*-
"""
Creation des 25 rapports du cycle CREANCES & RECOUVREMENT CLIENT pour OptiBoard
11 GRID + 6 PIVOT + 9 DASHBOARD
Tables sources: Échéances_Ventes + Imputation_Factures_Ventes + Clients + Règlements_Clients + Lignes_des_ventes (DWH)
"""
import pyodbc, json, re

CONN_STR = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019;TrustServerCertificate=yes"

# ======================================================================
# PARAMETRES COMMUNS
# ======================================================================
PARAMS_DATE_SOCIETE = json.dumps([
    {"name": "dateDebut", "type": "date", "label": "Date début", "required": True, "default": "FIRST_DAY_YEAR"},
    {"name": "dateFin", "type": "date", "label": "Date fin", "required": True, "default": "TODAY"},
    {"name": "societe", "type": "select", "label": "Société", "required": False,
     "source": "query", "query": "SELECT code as value, nom + ' (' + code + ')' as label FROM APP_DWH WHERE actif = 1 ORDER BY nom",
     "allow_null": True, "null_label": "(Toutes)"}
])

PARAMS_SOCIETE_ONLY = json.dumps([
    {"name": "societe", "type": "select", "label": "Société", "required": False,
     "source": "query", "query": "SELECT code as value, nom + ' (' + code + ')' as label FROM APP_DWH WHERE actif = 1 ORDER BY nom",
     "allow_null": True, "null_label": "(Toutes)"}
])

# Societe filters
SOC_EV = "(@societe IS NULL OR ev.societe = @societe)"
SOC_IMP = "(@societe IS NULL OR imp.societe = @societe)"

# Table name with accent
TBL_EV = "[Echéances_Ventes]"

# ======================================================================
# SOUS-REQUETE REUTILISABLE : Montant réglé agrégé depuis Imputation_Factures_Ventes
# Remplace ev.[Montant du règlement] qui donne des résultats erronés
# ======================================================================
REG_SUBQUERY = (
    "LEFT JOIN (SELECT [Id échéance], societe, "
    "SUM([Montant régler]) AS MontantRegle "
    "FROM Imputation_Factures_Ventes "
    "GROUP BY [Id échéance], societe) reg "
    "ON ev.[N° interne] = reg.[Id échéance] AND ev.societe = reg.societe "
)

# Même sous-requête avec filtre date pour rapports avec @dateFin
REG_SUBQUERY_DATE = (
    "LEFT JOIN (SELECT [Id échéance], societe, "
    "SUM([Montant régler]) AS MontantRegle "
    "FROM Imputation_Factures_Ventes "
    "WHERE [Date règlement] <= @dateFin "
    "GROUP BY [Id échéance], societe) reg "
    "ON ev.[N° interne] = reg.[Id échéance] AND ev.societe = reg.societe "
)

# ======================================================================
# 26 DATASOURCE TEMPLATES
# ======================================================================
DS_TEMPLATES = [
    # --- 1. GRID: Echeances Clients Detail (avec imputations + Clients) ---
    {
        "code": "DS_REC_ECHEANCES_DETAIL",
        "nom": "Échéances Clients Détail",
        "query": "SELECT "
            + "ev.[N° interne], ev.societe AS [Societe], "
            + "ev.[Code client], ev.[Intitulé client] AS [Client], "
            + "ev.[Code tiers payeur], ev.[Intitulé Tiers payeur] AS [Tiers Payeur], "
            + "ev.[N° Pièce] AS [Num Piece], ev.[Date document], "
            + "ev.[Date d'échéance] AS [Date Echeance], "
            + "ev.[Mode de règlement] AS [Mode Reglement], "
            + "ev.[Montant échéance] AS [Montant Echeance], "
            + "ev.[Type Document], "
            + "ISNULL(reg.MontantRegle, 0) AS [Montant Regler], "
            + "cl.[Encours de l'autorisation] AS [Caution], "
            + "ev.[Montant échéance] - ISNULL(reg.MontantRegle, 0) AS [Reste A Payer], "
            + "cl.[Catégorie tarifaire], cl.[Catégorie comptable], "
            + "cl.Représentant, cl.Ville, cl.Région "
            + "FROM " + TBL_EV + " ev "
            + REG_SUBQUERY_DATE
            + "LEFT JOIN Clients cl "
            + "ON ev.[Code client] = cl.[Code client] AND ev.societe = cl.societe "
            + "WHERE ev.[Type Document] LIKE '%facture%' "
            + "AND ev.[Type Document] <> 'Facture d''accompte' "
            + "AND ev.[Type de règlement] <> 'Acompte' "
            + "AND ev.[Date document] BETWEEN @dateDebut AND @dateFin AND " + SOC_EV + " "
            + "ORDER BY ev.[Date d'échéance] DESC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "recouvrement"
    },
    # --- 2. GRID: Creances Impayees (solde > 0) ---
    {
        "code": "DS_REC_IMPAYES",
        "nom": "Créances Impayées",
        "query": "SELECT "
            + "ev.[Code client], ev.[Intitulé client] AS [Client], "
            + "ev.[Code tiers payeur], ev.[Intitulé Tiers payeur] AS [Tiers Payeur], "
            + "ev.[Type Document], ev.[N° Pièce] AS [Num Piece], "
            + "ev.[Date document], ev.[Date d'échéance] AS [Date Echeance], "
            + "ev.[Montant échéance] AS [Montant Echeance], "
            + "ISNULL(reg.MontantRegle, 0) AS [Montant Regle], "
            + "ev.[Montant échéance] - ISNULL(reg.MontantRegle, 0) AS [Reste A Payer], "
            + "DATEDIFF(day, ev.[Date d'échéance], GETDATE()) AS [Jours Retard], "
            + "CASE WHEN DATEDIFF(day, ev.[Date d'échéance], GETDATE()) <= 0 THEN 'A Jour' "
            + "WHEN DATEDIFF(day, ev.[Date d'échéance], GETDATE()) <= 30 THEN '1-30j' "
            + "WHEN DATEDIFF(day, ev.[Date d'échéance], GETDATE()) <= 60 THEN '31-60j' "
            + "WHEN DATEDIFF(day, ev.[Date d'échéance], GETDATE()) <= 90 THEN '61-90j' "
            + "ELSE '+90j' END AS [Tranche Retard], "
            + "ev.[Mode de règlement] AS [Mode Reglement], "
            + "ev.societe AS [Societe] "
            + "FROM " + TBL_EV + " ev "
            + REG_SUBQUERY
            + "WHERE ev.[Montant échéance] - ISNULL(reg.MontantRegle, 0) > 0.01 "
            + "AND ev.[Type Document] LIKE '%facture%' "
            + "AND " + SOC_EV + " "
            + "ORDER BY DATEDIFF(day, ev.[Date d'échéance], GETDATE()) DESC",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "recouvrement"
    },
    # --- 3. GRID: Reglements Recus ---
    {
        "code": "DS_REC_REGLEMENTS",
        "nom": "Règlements Reçus",
        "query": "SELECT "
            + "imp.[Code client], imp.[Intitulé client] AS [Client], "
            + "imp.[Code tier payeur], imp.[Intitulé tier payeur] AS [Tiers Payeur], "
            + "imp.[Type Document], imp.[N° pièce] AS [Num Piece], "
            + "imp.[Date document], imp.[Date règlement] AS [Date Reglement], "
            + "imp.[Montant facture TTC] AS [Montant Facture], "
            + "imp.[Montant régler] AS [Montant A Regler], "
            + "imp.[Montant réglement] AS [Montant Reglement], "
            + "imp.[Mode de réglement] AS [Mode Reglement], "
            + "imp.[Référence] AS [Reference], "
            + "imp.societe AS [Societe] "
            + "FROM Imputation_Factures_Ventes imp "
            + "WHERE imp.[Date règlement] BETWEEN @dateDebut AND @dateFin AND " + SOC_IMP + " "
            + "ORDER BY imp.[Date règlement] DESC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "recouvrement"
    },
    # --- 4. GRID: Balance Agee Clients (avec 4 colonnes supplementaires) ---
    {
        "code": "DS_REC_BALANCE_AGEE",
        "nom": "Balance Âgée Clients",
        "query": "SELECT "
            + "ev.[Code client], ev.[Intitulé client] AS [Client], "
            + "SUM(ev.[Montant échéance] - ISNULL(reg.MontantRegle, 0)) AS [Solde Total], "
            + "SUM(CASE WHEN DATEDIFF(day, ev.[Date d'échéance], GETDATE()) <= 0 THEN ev.[Montant échéance] - ISNULL(reg.MontantRegle, 0) ELSE 0 END) AS [Non Echu], "
            + "SUM(CASE WHEN DATEDIFF(day, ev.[Date d'échéance], GETDATE()) BETWEEN 1 AND 30 THEN ev.[Montant échéance] - ISNULL(reg.MontantRegle, 0) ELSE 0 END) AS [1-30j], "
            + "SUM(CASE WHEN DATEDIFF(day, ev.[Date d'échéance], GETDATE()) BETWEEN 31 AND 60 THEN ev.[Montant échéance] - ISNULL(reg.MontantRegle, 0) ELSE 0 END) AS [31-60j], "
            + "SUM(CASE WHEN DATEDIFF(day, ev.[Date d'échéance], GETDATE()) BETWEEN 61 AND 90 THEN ev.[Montant échéance] - ISNULL(reg.MontantRegle, 0) ELSE 0 END) AS [61-90j], "
            + "SUM(CASE WHEN DATEDIFF(day, ev.[Date d'échéance], GETDATE()) > 90 THEN ev.[Montant échéance] - ISNULL(reg.MontantRegle, 0) ELSE 0 END) AS [Plus 90j], "
            + "COUNT(*) AS [Nb Echeances], "
            + "ISNULL(MAX(rne.ReglementsNonEchus), 0) AS [Reglements NonEchus], "
            + "ISNULL(MAX(blnf.BL_NonFactures), 0) AS [BL NonFacture], "
            + "ISNULL(MAX(imp_i.Impaye), 0) AS [Impayes], "
            + "ISNULL(MAX(rni.ReglementNonImpute), 0) AS [Reglements NonImputes], "
            + "ev.societe AS [Societe] "
            + "FROM " + TBL_EV + " ev "
            + REG_SUBQUERY
            + "LEFT JOIN (SELECT societe, [Code client], SUM([Montant régler]) AS ReglementsNonEchus "
            + "FROM Imputation_Factures_Ventes WHERE [Date d'échéance] > GETDATE() "
            + "GROUP BY societe, [Code client]) rne "
            + "ON ev.[Code client] = rne.[Code client] AND ev.societe = rne.societe "
            + "LEFT JOIN (SELECT societe, [Code client], SUM([Montant TTC Net]) AS BL_NonFactures "
            + "FROM Lignes_des_ventes WHERE [Type Document] = 'Bon de livraison' "
            + "GROUP BY societe, [Code client]) blnf "
            + "ON ev.[Code client] = blnf.[Code client] AND ev.societe = blnf.societe "
            + "LEFT JOIN (SELECT societe, [Code client], -SUM(Montant) AS Impaye "
            + "FROM [Règlements_Clients] WHERE [Mode de règlement] = 'Impayé' "
            + "GROUP BY societe, [Code client]) imp_i "
            + "ON ev.[Code client] = imp_i.[Code client] AND ev.societe = imp_i.societe "
            + "LEFT JOIN (SELECT r.societe, r.[Code client], "
            + "r.TotalReglements - ISNULL(i.TotalImpute, 0) AS ReglementNonImpute "
            + "FROM (SELECT societe, [Code client], SUM(Montant) AS TotalReglements "
            + "FROM [Règlements_Clients] GROUP BY societe, [Code client]) r "
            + "LEFT JOIN (SELECT societe, [Code client], SUM([Montant régler]) AS TotalImpute "
            + "FROM Imputation_Factures_Ventes GROUP BY societe, [Code client]) i "
            + "ON r.societe = i.societe AND r.[Code client] = i.[Code client]) rni "
            + "ON ev.[Code client] = rni.[Code client] AND ev.societe = rni.societe "
            + "WHERE ev.[Montant échéance] - ISNULL(reg.MontantRegle, 0) > 0.01 "
            + "AND ev.[Type Document] LIKE '%facture%' "
            + "AND " + SOC_EV + " "
            + "GROUP BY ev.[Code client], ev.[Intitulé client], ev.societe "
            + "ORDER BY SUM(ev.[Montant échéance] - ISNULL(reg.MontantRegle, 0)) DESC",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "recouvrement"
    },
    # --- 5. GRID: Echeances avec Imputations (JOIN) ---
    {
        "code": "DS_REC_ECHEANCES_IMPUTATIONS",
        "nom": "Échéances avec Imputations",
        "query": "SELECT "
            + "ev.[Code client], ev.[Intitulé client] AS [Client], "
            + "ev.[Type Document], ev.[N° Pièce] AS [Num Piece], "
            + "ev.[Date document], ev.[Date d'échéance] AS [Date Echeance], "
            + "ev.[Montant TTC Net], ev.[Montant échéance] AS [Montant Echeance], "
            + "imp.[Montant régler] AS [Montant A Regler], "
            + "imp.[Mode de réglement] AS [Mode Reglement Imp], "
            + "imp.[Intitulé tier payeur] AS [Tiers Payeur Imp], "
            + "imp.[Date règlement] AS [Date Reglement], "
            + "imp.[Montant réglement] AS [Montant Reglement], "
            + "ev.societe AS [Societe] "
            + "FROM " + TBL_EV + " ev "
            + "LEFT JOIN Imputation_Factures_Ventes imp "
            + "ON imp.[Id échéance] = ev.[N° interne] AND imp.societe = ev.societe "
            + "WHERE ev.[Date document] BETWEEN @dateDebut AND @dateFin AND " + SOC_EV + " "
            + "ORDER BY ev.[Date document] DESC, ev.[N° Pièce]",
        "params": PARAMS_DATE_SOCIETE,
        "category": "recouvrement"
    },
    # --- 6. GRID: Factures Echues Non Reglees ---
    {
        "code": "DS_REC_ECHUES_NON_REGLEES",
        "nom": "Factures Échues Non Réglées",
        "query": "SELECT "
            + "ev.[Code client], ev.[Intitulé client] AS [Client], "
            + "ev.[Type Document], ev.[N° Pièce] AS [Num Piece], "
            + "ev.[Date document], ev.[Date d'échéance] AS [Date Echeance], "
            + "ev.[Montant échéance] AS [Montant Echeance], "
            + "ISNULL(reg.MontantRegle, 0) AS [Montant Regle], "
            + "ev.[Montant échéance] - ISNULL(reg.MontantRegle, 0) AS [Reste A Payer], "
            + "DATEDIFF(day, ev.[Date d'échéance], GETDATE()) AS [Jours Retard], "
            + "ev.[Mode de règlement] AS [Mode Reglement], "
            + "ev.societe AS [Societe] "
            + "FROM " + TBL_EV + " ev "
            + REG_SUBQUERY
            + "WHERE ev.[Date d'échéance] < GETDATE() "
            + "AND ev.[Montant échéance] - ISNULL(reg.MontantRegle, 0) > 0.01 "
            + "AND ev.[Type Document] LIKE '%facture%' "
            + "AND " + SOC_EV + " "
            + "ORDER BY DATEDIFF(day, ev.[Date d'échéance], GETDATE()) DESC",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "recouvrement"
    },
    # --- 7. GRID: Clients a Risque (>90j retard) ---
    {
        "code": "DS_REC_CLIENTS_RISQUE",
        "nom": "Clients à Risque",
        "query": "SELECT "
            + "ev.[Code client], ev.[Intitulé client] AS [Client], "
            + "COUNT(*) AS [Nb Factures Impayees], "
            + "SUM(ev.[Montant échéance] - ISNULL(reg.MontantRegle, 0)) AS [Montant Impaye], "
            + "MAX(DATEDIFF(day, ev.[Date d'échéance], GETDATE())) AS [Max Jours Retard], "
            + "AVG(DATEDIFF(day, ev.[Date d'échéance], GETDATE())) AS [Moy Jours Retard], "
            + "MIN(ev.[Date d'échéance]) AS [Plus Ancienne Echeance], "
            + "CASE WHEN MAX(DATEDIFF(day, ev.[Date d'échéance], GETDATE())) > 180 THEN 'CRITIQUE' "
            + "WHEN MAX(DATEDIFF(day, ev.[Date d'échéance], GETDATE())) > 90 THEN 'ELEVE' "
            + "WHEN MAX(DATEDIFF(day, ev.[Date d'échéance], GETDATE())) > 30 THEN 'MOYEN' "
            + "ELSE 'FAIBLE' END AS [Niveau Risque], "
            + "ev.societe AS [Societe] "
            + "FROM " + TBL_EV + " ev "
            + REG_SUBQUERY
            + "WHERE ev.[Montant échéance] - ISNULL(reg.MontantRegle, 0) > 0.01 "
            + "AND ev.[Date d'échéance] < GETDATE() "
            + "AND ev.[Type Document] LIKE '%facture%' "
            + "AND " + SOC_EV + " "
            + "GROUP BY ev.[Code client], ev.[Intitulé client], ev.societe "
            + "ORDER BY SUM(ev.[Montant échéance] - ISNULL(reg.MontantRegle, 0)) DESC",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "recouvrement"
    },
    # --- 8. GRID: Historique Reglements par Client ---
    {
        "code": "DS_REC_HISTORIQUE_CLIENT",
        "nom": "Historique Règlements par Client",
        "query": "SELECT "
            + "imp.[Code client], imp.[Intitulé client] AS [Client], "
            + "imp.[Type Document], imp.[N° pièce] AS [Num Piece], "
            + "imp.[Date document], imp.[Date règlement] AS [Date Reglement], "
            + "imp.[Montant facture TTC] AS [Montant Facture], "
            + "imp.[Montant régler] AS [Montant A Regler], "
            + "imp.[Montant réglement] AS [Montant Reglement], "
            + "imp.[Mode de réglement] AS [Mode Reglement], "
            + "DATEDIFF(day, imp.[Date document], imp.[Date règlement]) AS [Delai Reglement Jours], "
            + "imp.societe AS [Societe] "
            + "FROM Imputation_Factures_Ventes imp "
            + "WHERE imp.[Date règlement] IS NOT NULL "
            + "AND imp.[Date règlement] BETWEEN @dateDebut AND @dateFin AND " + SOC_IMP + " "
            + "ORDER BY imp.[Code client], imp.[Date règlement] DESC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "recouvrement"
    },
    # --- 9. GRID: Echeances a Venir ---
    {
        "code": "DS_REC_ECHEANCES_A_VENIR",
        "nom": "Échéances à Venir",
        "query": "SELECT "
            + "ev.[Code client], ev.[Intitulé client] AS [Client], "
            + "ev.[Type Document], ev.[N° Pièce] AS [Num Piece], "
            + "ev.[Date document], ev.[Date d'échéance] AS [Date Echeance], "
            + "ev.[Montant échéance] AS [Montant Echeance], "
            + "ISNULL(reg.MontantRegle, 0) AS [Montant Regle], "
            + "ev.[Montant échéance] - ISNULL(reg.MontantRegle, 0) AS [Reste A Payer], "
            + "DATEDIFF(day, GETDATE(), ev.[Date d'échéance]) AS [Jours Restants], "
            + "ev.[Mode de règlement] AS [Mode Reglement], "
            + "ev.societe AS [Societe] "
            + "FROM " + TBL_EV + " ev "
            + REG_SUBQUERY
            + "WHERE ev.[Date d'échéance] >= GETDATE() "
            + "AND ev.[Montant échéance] - ISNULL(reg.MontantRegle, 0) > 0.01 "
            + "AND ev.[Type Document] LIKE '%facture%' "
            + "AND " + SOC_EV + " "
            + "ORDER BY ev.[Date d'échéance] ASC",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "recouvrement"
    },
    # --- 10. GRID: Delai Moyen de Paiement par Client ---
    {
        "code": "DS_REC_DELAI_PAIEMENT",
        "nom": "Délai Moyen de Paiement",
        "query": "SELECT "
            + "imp.[Code client], imp.[Intitulé client] AS [Client], "
            + "COUNT(*) AS [Nb Reglements], "
            + "SUM(imp.[Montant réglement]) AS [Total Regle], "
            + "AVG(DATEDIFF(day, imp.[Date document], imp.[Date règlement])) AS [Delai Moyen Jours], "
            + "MIN(DATEDIFF(day, imp.[Date document], imp.[Date règlement])) AS [Delai Min], "
            + "MAX(DATEDIFF(day, imp.[Date document], imp.[Date règlement])) AS [Delai Max], "
            + "imp.societe AS [Societe] "
            + "FROM Imputation_Factures_Ventes imp "
            + "WHERE imp.[Date règlement] IS NOT NULL "
            + "AND imp.[Date règlement] BETWEEN @dateDebut AND @dateFin AND " + SOC_IMP + " "
            + "GROUP BY imp.[Code client], imp.[Intitulé client], imp.societe "
            + "ORDER BY AVG(DATEDIFF(day, imp.[Date document], imp.[Date règlement])) DESC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "recouvrement"
    },
    # --- 11. GRID: Suivi Echeances Clients (agrege par client) ---
    {
        "code": "DS_REC_SUIVI_ECHEANCES",
        "nom": "Suivi Échéances Clients",
        "query": "SELECT "
            + "ev.[Code client], ev.[Intitulé client] AS [Client], "
            + "COUNT(*) AS [Nb Echeances], "
            + "SUM(ev.[Montant échéance]) AS [Total Echeances], "
            + "SUM(ISNULL(imp.[Montant régler], 0)) AS [Total Regle], "
            + "SUM(ev.[Montant échéance]) - SUM(ISNULL(imp.[Montant régler], 0)) AS [Reste A Payer], "
            + "MIN(ev.[Date d'échéance]) AS [Echeance Plus Ancienne], "
            + "MAX(ev.[Date d'échéance]) AS [Echeance Plus Recente], "
            + "MAX(CASE WHEN ev.[Date d'échéance] < GETDATE() "
            + "THEN DATEDIFF(day, ev.[Date d'échéance], GETDATE()) ELSE 0 END) AS [Max Jours Retard], "
            + "ev.societe AS [Societe] "
            + "FROM " + TBL_EV + " ev "
            + "LEFT OUTER JOIN Imputation_Factures_Ventes imp "
            + "ON ev.[N° interne] = imp.[Id échéance] AND ev.societe = imp.societe "
            + "WHERE ev.[Date document] BETWEEN @dateDebut AND @dateFin AND " + SOC_EV + " "
            + "GROUP BY ev.[Code client], ev.[Intitulé client], ev.societe "
            + "ORDER BY SUM(ev.[Montant échéance]) - SUM(ISNULL(imp.[Montant régler], 0)) DESC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "recouvrement"
    },
    # --- 12. PIVOT: Creances par Tranche d'Age ---
    {
        "code": "DS_REC_PIVOT_BALANCE_AGEE",
        "nom": "Créances par Tranche d'Age",
        "query": "SELECT "
            + "ev.[Code client], ev.[Intitulé client] AS [Client], "
            + "CASE WHEN DATEDIFF(day, ev.[Date d'échéance], GETDATE()) <= 0 THEN 'Non Echu' "
            + "WHEN DATEDIFF(day, ev.[Date d'échéance], GETDATE()) <= 30 THEN '1-30j' "
            + "WHEN DATEDIFF(day, ev.[Date d'échéance], GETDATE()) <= 60 THEN '31-60j' "
            + "WHEN DATEDIFF(day, ev.[Date d'échéance], GETDATE()) <= 90 THEN '61-90j' "
            + "ELSE '+90j' END AS [Tranche], "
            + "SUM(ev.[Montant échéance] - ISNULL(reg.MontantRegle, 0)) AS [Montant Impaye], "
            + "COUNT(*) AS [Nb Echeances], "
            + "ev.societe AS [Societe] "
            + "FROM " + TBL_EV + " ev "
            + REG_SUBQUERY
            + "WHERE ev.[Montant échéance] - ISNULL(reg.MontantRegle, 0) > 0.01 "
            + "AND ev.[Type Document] LIKE '%facture%' "
            + "AND " + SOC_EV + " "
            + "GROUP BY ev.[Code client], ev.[Intitulé client], "
            + "CASE WHEN DATEDIFF(day, ev.[Date d'échéance], GETDATE()) <= 0 THEN 'Non Echu' "
            + "WHEN DATEDIFF(day, ev.[Date d'échéance], GETDATE()) <= 30 THEN '1-30j' "
            + "WHEN DATEDIFF(day, ev.[Date d'échéance], GETDATE()) <= 60 THEN '31-60j' "
            + "WHEN DATEDIFF(day, ev.[Date d'échéance], GETDATE()) <= 90 THEN '61-90j' "
            + "ELSE '+90j' END, ev.societe",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "recouvrement"
    },
    # --- 13. PIVOT: Reglements par Mode ---
    {
        "code": "DS_REC_PIVOT_MODE_REGLEMENT",
        "nom": "Règlements par Mode",
        "query": "SELECT "
            + "imp.[Mode de réglement] AS [Mode Reglement], "
            + "YEAR(imp.[Date règlement]) AS [Annee], "
            + "MONTH(imp.[Date règlement]) AS [Mois], "
            + "SUM(imp.[Montant réglement]) AS [Montant Reglement], "
            + "COUNT(*) AS [Nb Reglements], "
            + "imp.societe AS [Societe] "
            + "FROM Imputation_Factures_Ventes imp "
            + "WHERE imp.[Date règlement] BETWEEN @dateDebut AND @dateFin AND " + SOC_IMP + " "
            + "GROUP BY imp.[Mode de réglement], YEAR(imp.[Date règlement]), MONTH(imp.[Date règlement]), imp.societe",
        "params": PARAMS_DATE_SOCIETE,
        "category": "recouvrement"
    },
    # --- 14. PIVOT: Creances par Type Document ---
    {
        "code": "DS_REC_PIVOT_TYPE_DOC",
        "nom": "Créances par Type Document",
        "query": "SELECT "
            + "ev.[Type Document], "
            + "ev.[Code client], ev.[Intitulé client] AS [Client], "
            + "SUM(ev.[Montant échéance]) AS [Total Echeance], "
            + "SUM(ISNULL(reg.MontantRegle, 0)) AS [Total Regle], "
            + "SUM(ev.[Montant échéance] - ISNULL(reg.MontantRegle, 0)) AS [Reste A Payer], "
            + "COUNT(*) AS [Nb Echeances], "
            + "ev.societe AS [Societe] "
            + "FROM " + TBL_EV + " ev "
            + REG_SUBQUERY
            + "WHERE ev.[Date document] BETWEEN @dateDebut AND @dateFin AND " + SOC_EV + " "
            + "GROUP BY ev.[Type Document], ev.[Code client], ev.[Intitulé client], ev.societe",
        "params": PARAMS_DATE_SOCIETE,
        "category": "recouvrement"
    },
    # --- 15. PIVOT: Evolution Mensuelle Creances ---
    {
        "code": "DS_REC_PIVOT_EVOLUTION",
        "nom": "Evolution Mensuelle Créances",
        "query": "SELECT "
            + "YEAR(ev.[Date document]) AS [Annee], MONTH(ev.[Date document]) AS [Mois], "
            + "CAST(YEAR(ev.[Date document]) AS VARCHAR) + '-' + RIGHT('0' + CAST(MONTH(ev.[Date document]) AS VARCHAR), 2) AS [Periode], "
            + "SUM(ev.[Montant échéance]) AS [Total Echeances], "
            + "SUM(ISNULL(reg.MontantRegle, 0)) AS [Total Regle], "
            + "SUM(ev.[Montant échéance] - ISNULL(reg.MontantRegle, 0)) AS [Reste A Payer], "
            + "COUNT(*) AS [Nb Echeances], "
            + "COUNT(DISTINCT ev.[Code client]) AS [Nb Clients], "
            + "ev.societe AS [Societe] "
            + "FROM " + TBL_EV + " ev "
            + REG_SUBQUERY
            + "WHERE ev.[Type Document] LIKE '%facture%' "
            + "AND ev.[Date document] BETWEEN @dateDebut AND @dateFin AND " + SOC_EV + " "
            + "GROUP BY YEAR(ev.[Date document]), MONTH(ev.[Date document]), ev.societe "
            + "ORDER BY YEAR(ev.[Date document]), MONTH(ev.[Date document])",
        "params": PARAMS_DATE_SOCIETE,
        "category": "recouvrement"
    },
    # --- 16. PIVOT: Taux de Recouvrement par Client ---
    {
        "code": "DS_REC_PIVOT_TAUX_CLIENT",
        "nom": "Taux de Recouvrement par Client",
        "query": "SELECT "
            + "ev.[Code client], ev.[Intitulé client] AS [Client], "
            + "SUM(ev.[Montant échéance]) AS [Total Echeance], "
            + "SUM(ISNULL(reg.MontantRegle, 0)) AS [Total Regle], "
            + "SUM(ev.[Montant échéance] - ISNULL(reg.MontantRegle, 0)) AS [Reste A Payer], "
            + "CASE WHEN SUM(ev.[Montant échéance]) > 0 "
            + "THEN ROUND(100.0 * SUM(ISNULL(reg.MontantRegle, 0)) / SUM(ev.[Montant échéance]), 2) ELSE 0 END AS [Taux Recouvrement], "
            + "COUNT(*) AS [Nb Echeances], "
            + "ev.societe AS [Societe] "
            + "FROM " + TBL_EV + " ev "
            + REG_SUBQUERY
            + "WHERE ev.[Type Document] LIKE '%facture%' "
            + "AND ev.[Date document] BETWEEN @dateDebut AND @dateFin AND " + SOC_EV + " "
            + "GROUP BY ev.[Code client], ev.[Intitulé client], ev.societe "
            + "ORDER BY SUM(ev.[Montant échéance] - ISNULL(reg.MontantRegle, 0)) DESC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "recouvrement"
    },
    # --- 17. PIVOT: Reglements par Tiers Payeur ---
    {
        "code": "DS_REC_PIVOT_TIERS_PAYEUR",
        "nom": "Règlements par Tiers Payeur",
        "query": "SELECT "
            + "ev.[Code tiers payeur], ev.[Intitulé Tiers payeur] AS [Tiers Payeur], "
            + "SUM(ev.[Montant échéance]) AS [Total Echeance], "
            + "SUM(ISNULL(reg.MontantRegle, 0)) AS [Total Regle], "
            + "SUM(ev.[Montant échéance] - ISNULL(reg.MontantRegle, 0)) AS [Reste A Payer], "
            + "COUNT(*) AS [Nb Echeances], "
            + "COUNT(DISTINCT ev.[Code client]) AS [Nb Clients], "
            + "ev.societe AS [Societe] "
            + "FROM " + TBL_EV + " ev "
            + REG_SUBQUERY
            + "WHERE ev.[Type Document] LIKE '%facture%' "
            + "AND ev.[Date document] BETWEEN @dateDebut AND @dateFin AND " + SOC_EV + " "
            + "GROUP BY ev.[Code tiers payeur], ev.[Intitulé Tiers payeur], ev.societe "
            + "ORDER BY SUM(ev.[Montant échéance]) DESC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "recouvrement"
    },
    # --- 18. DASHBOARD: KPI Recouvrement Global ---
    {
        "code": "DS_REC_KPI_GLOBAL",
        "nom": "KPI Recouvrement Global",
        "query": "SELECT "
            + "SUM(ev.[Montant échéance]) AS [Total Creances], "
            + "SUM(ISNULL(reg.MontantRegle, 0)) AS [Total Recouvre], "
            + "SUM(ev.[Montant échéance] - ISNULL(reg.MontantRegle, 0)) AS [Reste A Recouvrer], "
            + "CASE WHEN SUM(ev.[Montant échéance]) > 0 "
            + "THEN ROUND(100.0 * SUM(ISNULL(reg.MontantRegle, 0)) / SUM(ev.[Montant échéance]), 2) ELSE 0 END AS [Taux Recouvrement], "
            + "COUNT(*) AS [Nb Echeances], "
            + "COUNT(DISTINCT ev.[Code client]) AS [Nb Clients], "
            + "SUM(CASE WHEN ev.[Date d'échéance] < GETDATE() AND ev.[Montant échéance] - ISNULL(reg.MontantRegle, 0) > 0.01 THEN 1 ELSE 0 END) AS [Nb Echues Impayees], "
            + "SUM(CASE WHEN ev.[Date d'échéance] < GETDATE() AND ev.[Montant échéance] - ISNULL(reg.MontantRegle, 0) > 0.01 THEN ev.[Montant échéance] - ISNULL(reg.MontantRegle, 0) ELSE 0 END) AS [Montant Echues Impayees], "
            + "ev.societe AS [Societe] "
            + "FROM " + TBL_EV + " ev "
            + REG_SUBQUERY
            + "WHERE ev.[Type Document] LIKE '%facture%' "
            + "AND ev.[Date document] BETWEEN @dateDebut AND @dateFin AND " + SOC_EV + " "
            + "GROUP BY ev.societe",
        "params": PARAMS_DATE_SOCIETE,
        "category": "recouvrement"
    },
    # --- 19. DASHBOARD: Evolution Mensuelle Recouvrement ---
    {
        "code": "DS_REC_EVOLUTION_MENSUELLE",
        "nom": "Evolution Mensuelle Recouvrement",
        "query": "SELECT "
            + "YEAR(ev.[Date document]) AS [Annee], MONTH(ev.[Date document]) AS [Mois], "
            + "CAST(YEAR(ev.[Date document]) AS VARCHAR) + '-' + RIGHT('0' + CAST(MONTH(ev.[Date document]) AS VARCHAR), 2) AS [Periode], "
            + "SUM(ev.[Montant échéance]) AS [Creances], "
            + "SUM(ISNULL(reg.MontantRegle, 0)) AS [Recouvre], "
            + "SUM(ev.[Montant échéance] - ISNULL(reg.MontantRegle, 0)) AS [Impaye], "
            + "ev.societe AS [Societe] "
            + "FROM " + TBL_EV + " ev "
            + REG_SUBQUERY
            + "WHERE ev.[Type Document] LIKE '%facture%' "
            + "AND ev.[Date document] BETWEEN @dateDebut AND @dateFin AND " + SOC_EV + " "
            + "GROUP BY YEAR(ev.[Date document]), MONTH(ev.[Date document]), ev.societe "
            + "ORDER BY YEAR(ev.[Date document]), MONTH(ev.[Date document])",
        "params": PARAMS_DATE_SOCIETE,
        "category": "recouvrement"
    },
    # --- 20. DASHBOARD: Repartition Balance Agee (Pie) ---
    {
        "code": "DS_REC_REPARTITION_AGEE",
        "nom": "Répartition Balance Âgée",
        "query": "SELECT "
            + "CASE WHEN DATEDIFF(day, ev.[Date d'échéance], GETDATE()) <= 0 THEN 'Non Echu' "
            + "WHEN DATEDIFF(day, ev.[Date d'échéance], GETDATE()) <= 30 THEN '1-30 jours' "
            + "WHEN DATEDIFF(day, ev.[Date d'échéance], GETDATE()) <= 60 THEN '31-60 jours' "
            + "WHEN DATEDIFF(day, ev.[Date d'échéance], GETDATE()) <= 90 THEN '61-90 jours' "
            + "ELSE 'Plus de 90 jours' END AS [Tranche], "
            + "SUM(ev.[Montant échéance] - ISNULL(reg.MontantRegle, 0)) AS [Montant Impaye], "
            + "COUNT(*) AS [Nb Echeances], "
            + "COUNT(DISTINCT ev.[Code client]) AS [Nb Clients], "
            + "ev.societe AS [Societe] "
            + "FROM " + TBL_EV + " ev "
            + REG_SUBQUERY
            + "WHERE ev.[Montant échéance] - ISNULL(reg.MontantRegle, 0) > 0.01 "
            + "AND ev.[Type Document] LIKE '%facture%' "
            + "AND " + SOC_EV + " "
            + "GROUP BY CASE WHEN DATEDIFF(day, ev.[Date d'échéance], GETDATE()) <= 0 THEN 'Non Echu' "
            + "WHEN DATEDIFF(day, ev.[Date d'échéance], GETDATE()) <= 30 THEN '1-30 jours' "
            + "WHEN DATEDIFF(day, ev.[Date d'échéance], GETDATE()) <= 60 THEN '31-60 jours' "
            + "WHEN DATEDIFF(day, ev.[Date d'échéance], GETDATE()) <= 90 THEN '61-90 jours' "
            + "ELSE 'Plus de 90 jours' END, ev.societe",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "recouvrement"
    },
    # --- 21. DASHBOARD: Top 20 Debiteurs ---
    {
        "code": "DS_REC_TOP_DEBITEURS",
        "nom": "Top 20 Débiteurs",
        "query": "SELECT TOP 20 "
            + "ev.[Code client], ev.[Intitulé client] AS [Client], "
            + "SUM(ev.[Montant échéance] - ISNULL(reg.MontantRegle, 0)) AS [Montant Impaye], "
            + "COUNT(*) AS [Nb Echeances], "
            + "MAX(DATEDIFF(day, ev.[Date d'échéance], GETDATE())) AS [Max Retard Jours], "
            + "ev.societe AS [Societe] "
            + "FROM " + TBL_EV + " ev "
            + REG_SUBQUERY
            + "WHERE ev.[Montant échéance] - ISNULL(reg.MontantRegle, 0) > 0.01 "
            + "AND ev.[Type Document] LIKE '%facture%' "
            + "AND " + SOC_EV + " "
            + "GROUP BY ev.[Code client], ev.[Intitulé client], ev.societe "
            + "ORDER BY SUM(ev.[Montant échéance] - ISNULL(reg.MontantRegle, 0)) DESC",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "recouvrement"
    },
    # --- 22. DASHBOARD: Repartition par Mode Reglement ---
    {
        "code": "DS_REC_REPARTITION_MODE",
        "nom": "Répartition par Mode Règlement",
        "query": "SELECT "
            + "ev.[Mode de règlement] AS [Mode Reglement], "
            + "SUM(ev.[Montant échéance]) AS [Total Echeances], "
            + "SUM(ISNULL(reg.MontantRegle, 0)) AS [Total Regle], "
            + "SUM(ev.[Montant échéance] - ISNULL(reg.MontantRegle, 0)) AS [Reste A Payer], "
            + "COUNT(*) AS [Nb Echeances], "
            + "ev.societe AS [Societe] "
            + "FROM " + TBL_EV + " ev "
            + REG_SUBQUERY
            + "WHERE ev.[Type Document] LIKE '%facture%' "
            + "AND ev.[Date document] BETWEEN @dateDebut AND @dateFin AND " + SOC_EV + " "
            + "GROUP BY ev.[Mode de règlement], ev.societe "
            + "ORDER BY SUM(ev.[Montant échéance]) DESC",
        "params": PARAMS_DATE_SOCIETE,
        "category": "recouvrement"
    },
    # --- 23. DASHBOARD: Taux Recouvrement Mensuel ---
    {
        "code": "DS_REC_TAUX_MENSUEL",
        "nom": "Taux Recouvrement Mensuel",
        "query": "SELECT "
            + "YEAR(ev.[Date document]) AS [Annee], MONTH(ev.[Date document]) AS [Mois], "
            + "CAST(YEAR(ev.[Date document]) AS VARCHAR) + '-' + RIGHT('0' + CAST(MONTH(ev.[Date document]) AS VARCHAR), 2) AS [Periode], "
            + "CASE WHEN SUM(ev.[Montant échéance]) > 0 "
            + "THEN ROUND(100.0 * SUM(ISNULL(reg.MontantRegle, 0)) / SUM(ev.[Montant échéance]), 2) ELSE 0 END AS [Taux Recouvrement], "
            + "SUM(ev.[Montant échéance]) AS [Creances], "
            + "SUM(ISNULL(reg.MontantRegle, 0)) AS [Recouvre], "
            + "ev.societe AS [Societe] "
            + "FROM " + TBL_EV + " ev "
            + REG_SUBQUERY
            + "WHERE ev.[Type Document] LIKE '%facture%' "
            + "AND ev.[Date document] BETWEEN @dateDebut AND @dateFin AND " + SOC_EV + " "
            + "GROUP BY YEAR(ev.[Date document]), MONTH(ev.[Date document]), ev.societe "
            + "ORDER BY YEAR(ev.[Date document]), MONTH(ev.[Date document])",
        "params": PARAMS_DATE_SOCIETE,
        "category": "recouvrement"
    },
    # --- 24. DASHBOARD: Niveau de Risque Clients ---
    {
        "code": "DS_REC_NIVEAU_RISQUE",
        "nom": "Niveau de Risque Clients",
        "query": "SELECT sub.[Niveau Risque], "
            + "COUNT(*) AS [Nb Clients], "
            + "SUM(sub.[Montant Impaye]) AS [Montant Impaye], "
            + "sub.societe AS [Societe] "
            + "FROM ("
            + "SELECT ev.[Code client], "
            + "SUM(ev.[Montant échéance] - ISNULL(reg.MontantRegle, 0)) AS [Montant Impaye], "
            + "CASE WHEN MAX(DATEDIFF(day, ev.[Date d'échéance], GETDATE())) > 180 THEN 'CRITIQUE' "
            + "WHEN MAX(DATEDIFF(day, ev.[Date d'échéance], GETDATE())) > 90 THEN 'ELEVE' "
            + "WHEN MAX(DATEDIFF(day, ev.[Date d'échéance], GETDATE())) > 30 THEN 'MOYEN' "
            + "ELSE 'FAIBLE' END AS [Niveau Risque], "
            + "ev.societe "
            + "FROM " + TBL_EV + " ev "
            + REG_SUBQUERY
            + "WHERE ev.[Montant échéance] - ISNULL(reg.MontantRegle, 0) > 0.01 "
            + "AND ev.[Date d'échéance] < GETDATE() "
            + "AND ev.[Type Document] LIKE '%facture%' "
            + "AND " + SOC_EV + " "
            + "GROUP BY ev.[Code client], ev.societe"
            + ") sub "
            + "GROUP BY sub.[Niveau Risque], sub.societe "
            + "ORDER BY CASE sub.[Niveau Risque] WHEN 'CRITIQUE' THEN 1 WHEN 'ELEVE' THEN 2 WHEN 'MOYEN' THEN 3 ELSE 4 END",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "recouvrement"
    },
    # --- 25. DASHBOARD: Encaissements Mensuels ---
    {
        "code": "DS_REC_ENCAISSEMENTS_MENS",
        "nom": "Encaissements Mensuels",
        "query": "SELECT "
            + "YEAR(imp.[Date règlement]) AS [Annee], MONTH(imp.[Date règlement]) AS [Mois], "
            + "CAST(YEAR(imp.[Date règlement]) AS VARCHAR) + '-' + RIGHT('0' + CAST(MONTH(imp.[Date règlement]) AS VARCHAR), 2) AS [Periode], "
            + "SUM(imp.[Montant réglement]) AS [Total Encaisse], "
            + "COUNT(*) AS [Nb Reglements], "
            + "COUNT(DISTINCT imp.[Code client]) AS [Nb Clients], "
            + "imp.societe AS [Societe] "
            + "FROM Imputation_Factures_Ventes imp "
            + "WHERE imp.[Date règlement] BETWEEN @dateDebut AND @dateFin AND " + SOC_IMP + " "
            + "GROUP BY YEAR(imp.[Date règlement]), MONTH(imp.[Date règlement]), imp.societe "
            + "ORDER BY YEAR(imp.[Date règlement]), MONTH(imp.[Date règlement])",
        "params": PARAMS_DATE_SOCIETE,
        "category": "recouvrement"
    },
    # --- 26. DASHBOARD: Synthese Annuelle Recouvrement ---
    {
        "code": "DS_REC_SYNTHESE_ANNUELLE",
        "nom": "Synthèse Annuelle Recouvrement",
        "query": "SELECT "
            + "YEAR(ev.[Date document]) AS [Exercice], "
            + "SUM(ev.[Montant échéance]) AS [Total Creances], "
            + "SUM(ISNULL(reg.MontantRegle, 0)) AS [Total Recouvre], "
            + "SUM(ev.[Montant échéance] - ISNULL(reg.MontantRegle, 0)) AS [Reste A Recouvrer], "
            + "CASE WHEN SUM(ev.[Montant échéance]) > 0 "
            + "THEN ROUND(100.0 * SUM(ISNULL(reg.MontantRegle, 0)) / SUM(ev.[Montant échéance]), 2) ELSE 0 END AS [Taux Recouvrement], "
            + "COUNT(*) AS [Nb Echeances], "
            + "COUNT(DISTINCT ev.[Code client]) AS [Nb Clients], "
            + "ev.societe AS [Societe] "
            + "FROM " + TBL_EV + " ev "
            + REG_SUBQUERY
            + "WHERE ev.[Type Document] LIKE '%facture%' "
            + "AND " + SOC_EV + " "
            + "GROUP BY YEAR(ev.[Date document]), ev.societe "
            + "ORDER BY YEAR(ev.[Date document])",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "recouvrement"
    },
]

# ======================================================================
# 11 GRIDVIEWS
# ======================================================================
GRIDVIEWS = [
    ("DS_REC_ECHEANCES_DETAIL",      "Échéances Clients Détail"),
    ("DS_REC_IMPAYES",               "Créances Impayées"),
    ("DS_REC_REGLEMENTS",            "Règlements Reçus"),
    ("DS_REC_BALANCE_AGEE",          "Balance Âgée Clients"),
    ("DS_REC_ECHEANCES_IMPUTATIONS", "Échéances avec Imputations"),
    ("DS_REC_ECHUES_NON_REGLEES",    "Factures Échues Non Réglées"),
    ("DS_REC_CLIENTS_RISQUE",        "Clients à Risque"),
    ("DS_REC_HISTORIQUE_CLIENT",     "Historique Règlements"),
    ("DS_REC_ECHEANCES_A_VENIR",     "Échéances à Venir"),
    ("DS_REC_DELAI_PAIEMENT",       "Délai Moyen de Paiement"),
    ("DS_REC_SUIVI_ECHEANCES",      "Suivi Échéances Clients"),
]

# ======================================================================
# 6 PIVOTS
# ======================================================================
PIVOTS = [
    ("DS_REC_PIVOT_BALANCE_AGEE", "Créances par Tranche d'Age",
     [{"field": "Client"}],
     [{"field": "Montant Impaye", "aggregation": "sum"}, {"field": "Nb Echeances", "aggregation": "sum"}],
     [{"field": "Societe"}, {"field": "Tranche"}]),

    ("DS_REC_PIVOT_MODE_REGLEMENT", "Règlements par Mode",
     [{"field": "Mode Reglement"}],
     [{"field": "Montant Reglement", "aggregation": "sum"}, {"field": "Nb Reglements", "aggregation": "sum"}],
     [{"field": "Societe"}]),

    ("DS_REC_PIVOT_TYPE_DOC", "Créances par Type Document",
     [{"field": "Type Document"}],
     [{"field": "Total Echeance", "aggregation": "sum"}, {"field": "Total Regle", "aggregation": "sum"}, {"field": "Reste A Payer", "aggregation": "sum"}],
     [{"field": "Societe"}]),

    ("DS_REC_PIVOT_EVOLUTION", "Evolution Mensuelle Créances",
     [{"field": "Periode"}],
     [{"field": "Total Echeances", "aggregation": "sum"}, {"field": "Total Regle", "aggregation": "sum"}, {"field": "Reste A Payer", "aggregation": "sum"}],
     [{"field": "Societe"}]),

    ("DS_REC_PIVOT_TAUX_CLIENT", "Taux Recouvrement par Client",
     [{"field": "Client"}],
     [{"field": "Total Echeance", "aggregation": "sum"}, {"field": "Total Regle", "aggregation": "sum"}, {"field": "Taux Recouvrement", "aggregation": "avg"}],
     [{"field": "Societe"}]),

    ("DS_REC_PIVOT_TIERS_PAYEUR", "Règlements par Tiers Payeur",
     [{"field": "Tiers Payeur"}],
     [{"field": "Total Echeance", "aggregation": "sum"}, {"field": "Total Regle", "aggregation": "sum"}, {"field": "Reste A Payer", "aggregation": "sum"}],
     [{"field": "Societe"}]),
]

# ======================================================================
# 9 DASHBOARDS
# ======================================================================
DASHBOARDS = [
    ("DS_REC_KPI_GLOBAL", "TB Recouvrement Global", [
        {"id": "w1", "type": "kpi", "title": "Total Créances", "x": 0, "y": 0, "w": 3, "h": 3,
         "config": {"dataSourceCode": "DS_REC_KPI_GLOBAL", "dataSourceOrigin": "template",
                    "value_field": "Total Creances", "format": "currency", "suffix": " DH"}},
        {"id": "w2", "type": "kpi", "title": "Total Recouvré", "x": 3, "y": 0, "w": 3, "h": 3,
         "config": {"dataSourceCode": "DS_REC_KPI_GLOBAL", "dataSourceOrigin": "template",
                    "value_field": "Total Recouvre", "format": "currency", "suffix": " DH"}},
        {"id": "w3", "type": "kpi", "title": "Reste à Recouvrer", "x": 6, "y": 0, "w": 3, "h": 3,
         "config": {"dataSourceCode": "DS_REC_KPI_GLOBAL", "dataSourceOrigin": "template",
                    "value_field": "Reste A Recouvrer", "format": "currency", "suffix": " DH",
                    "conditional_color": [{"operator": ">", "value": 0, "color": "#ef4444"}]}},
        {"id": "w4", "type": "kpi", "title": "Taux Recouvrement", "x": 9, "y": 0, "w": 3, "h": 3,
         "config": {"dataSourceCode": "DS_REC_KPI_GLOBAL", "dataSourceOrigin": "template",
                    "value_field": "Taux Recouvrement", "format": "percent", "suffix": "%",
                    "conditional_color": [{"operator": ">=", "value": 80, "color": "#10b981"}, {"operator": "<", "value": 80, "color": "#f59e0b"}]}},
        {"id": "w5", "type": "kpi", "title": "Nb Clients", "x": 0, "y": 3, "w": 3, "h": 3,
         "config": {"dataSourceCode": "DS_REC_KPI_GLOBAL", "dataSourceOrigin": "template",
                    "value_field": "Nb Clients", "format": "number"}},
        {"id": "w6", "type": "kpi", "title": "Nb Échéances", "x": 3, "y": 3, "w": 3, "h": 3,
         "config": {"dataSourceCode": "DS_REC_KPI_GLOBAL", "dataSourceOrigin": "template",
                    "value_field": "Nb Echeances", "format": "number"}},
        {"id": "w7", "type": "kpi", "title": "Échées Impayées", "x": 6, "y": 3, "w": 3, "h": 3,
         "config": {"dataSourceCode": "DS_REC_KPI_GLOBAL", "dataSourceOrigin": "template",
                    "value_field": "Nb Echues Impayees", "format": "number"}},
        {"id": "w8", "type": "kpi", "title": "Montant Échées Impayées", "x": 9, "y": 3, "w": 3, "h": 3,
         "config": {"dataSourceCode": "DS_REC_KPI_GLOBAL", "dataSourceOrigin": "template",
                    "value_field": "Montant Echues Impayees", "format": "currency", "suffix": " DH"}},
    ]),
    ("DS_REC_EVOLUTION_MENSUELLE", "Evolution Mensuelle Recouvrement", [
        {"id": "w1", "type": "bar", "title": "Créances vs Recouvrement", "x": 0, "y": 0, "w": 12, "h": 8,
         "config": {"dataSourceCode": "DS_REC_EVOLUTION_MENSUELLE", "dataSourceOrigin": "template",
                    "category_field": "Periode", "value_fields": ["Creances", "Recouvre"],
                    "colors": ["#3b82f6", "#10b981"]}},
        {"id": "w2", "type": "line", "title": "Impayés Mensuels", "x": 0, "y": 8, "w": 12, "h": 6,
         "config": {"dataSourceCode": "DS_REC_EVOLUTION_MENSUELLE", "dataSourceOrigin": "template",
                    "category_field": "Periode", "value_fields": ["Impaye"],
                    "colors": ["#ef4444"]}},
    ]),
    ("DS_REC_REPARTITION_AGEE", "Répartition Balance Âgée", [
        {"id": "w1", "type": "pie", "title": "Montant par Tranche d'Age", "x": 0, "y": 0, "w": 6, "h": 8,
         "config": {"dataSourceCode": "DS_REC_REPARTITION_AGEE", "dataSourceOrigin": "template",
                    "category_field": "Tranche", "value_field": "Montant Impaye"}},
        {"id": "w2", "type": "bar", "title": "Nb Clients par Tranche", "x": 6, "y": 0, "w": 6, "h": 8,
         "config": {"dataSourceCode": "DS_REC_REPARTITION_AGEE", "dataSourceOrigin": "template",
                    "category_field": "Tranche", "value_fields": ["Nb Clients"],
                    "colors": ["#f59e0b"]}},
        {"id": "w3", "type": "table", "title": "Détail par Tranche", "x": 0, "y": 8, "w": 12, "h": 6,
         "config": {"dataSourceCode": "DS_REC_REPARTITION_AGEE", "dataSourceOrigin": "template",
                    "columns": ["Tranche", "Montant Impaye", "Nb Echeances", "Nb Clients"]}},
    ]),
    ("DS_REC_TOP_DEBITEURS", "Top 20 Débiteurs", [
        {"id": "w1", "type": "bar", "title": "Top 20 Débiteurs", "x": 0, "y": 0, "w": 12, "h": 8,
         "config": {"dataSourceCode": "DS_REC_TOP_DEBITEURS", "dataSourceOrigin": "template",
                    "category_field": "Client", "value_fields": ["Montant Impaye"],
                    "colors": ["#ef4444"]}},
        {"id": "w2", "type": "table", "title": "Détail Top Débiteurs", "x": 0, "y": 8, "w": 12, "h": 6,
         "config": {"dataSourceCode": "DS_REC_TOP_DEBITEURS", "dataSourceOrigin": "template",
                    "columns": ["Code client", "Client", "Montant Impaye", "Nb Echeances", "Max Retard Jours"]}},
    ]),
    ("DS_REC_REPARTITION_MODE", "Répartition par Mode Règlement", [
        {"id": "w1", "type": "pie", "title": "Par Mode Règlement", "x": 0, "y": 0, "w": 6, "h": 8,
         "config": {"dataSourceCode": "DS_REC_REPARTITION_MODE", "dataSourceOrigin": "template",
                    "category_field": "Mode Reglement", "value_field": "Total Echeances"}},
        {"id": "w2", "type": "bar", "title": "Réglé vs Reste par Mode", "x": 6, "y": 0, "w": 6, "h": 8,
         "config": {"dataSourceCode": "DS_REC_REPARTITION_MODE", "dataSourceOrigin": "template",
                    "category_field": "Mode Reglement", "value_fields": ["Total Regle", "Reste A Payer"],
                    "colors": ["#10b981", "#ef4444"]}},
    ]),
    ("DS_REC_TAUX_MENSUEL", "Taux Recouvrement Mensuel", [
        {"id": "w1", "type": "line", "title": "Evolution Taux de Recouvrement", "x": 0, "y": 0, "w": 12, "h": 8,
         "config": {"dataSourceCode": "DS_REC_TAUX_MENSUEL", "dataSourceOrigin": "template",
                    "category_field": "Periode", "value_fields": ["Taux Recouvrement"],
                    "colors": ["#8b5cf6"]}},
        {"id": "w2", "type": "bar", "title": "Créances vs Recouvrement", "x": 0, "y": 8, "w": 12, "h": 6,
         "config": {"dataSourceCode": "DS_REC_TAUX_MENSUEL", "dataSourceOrigin": "template",
                    "category_field": "Periode", "value_fields": ["Creances", "Recouvre"],
                    "colors": ["#3b82f6", "#10b981"]}},
    ]),
    ("DS_REC_NIVEAU_RISQUE", "Niveau de Risque Clients", [
        {"id": "w1", "type": "pie", "title": "Clients par Niveau de Risque", "x": 0, "y": 0, "w": 6, "h": 8,
         "config": {"dataSourceCode": "DS_REC_NIVEAU_RISQUE", "dataSourceOrigin": "template",
                    "category_field": "Niveau Risque", "value_field": "Nb Clients"}},
        {"id": "w2", "type": "bar", "title": "Montant Impayé par Risque", "x": 6, "y": 0, "w": 6, "h": 8,
         "config": {"dataSourceCode": "DS_REC_NIVEAU_RISQUE", "dataSourceOrigin": "template",
                    "category_field": "Niveau Risque", "value_fields": ["Montant Impaye"],
                    "colors": ["#ef4444"]}},
    ]),
    ("DS_REC_ENCAISSEMENTS_MENS", "Encaissements Mensuels", [
        {"id": "w1", "type": "bar", "title": "Encaissements par Mois", "x": 0, "y": 0, "w": 12, "h": 8,
         "config": {"dataSourceCode": "DS_REC_ENCAISSEMENTS_MENS", "dataSourceOrigin": "template",
                    "category_field": "Periode", "value_fields": ["Total Encaisse"],
                    "colors": ["#10b981"]}},
        {"id": "w2", "type": "line", "title": "Nb Règlements par Mois", "x": 0, "y": 8, "w": 12, "h": 6,
         "config": {"dataSourceCode": "DS_REC_ENCAISSEMENTS_MENS", "dataSourceOrigin": "template",
                    "category_field": "Periode", "value_fields": ["Nb Reglements"],
                    "colors": ["#3b82f6"]}},
    ]),
    ("DS_REC_SYNTHESE_ANNUELLE", "Synthèse Annuelle Recouvrement", [
        {"id": "w1", "type": "bar", "title": "Créances vs Recouvrement par Année", "x": 0, "y": 0, "w": 8, "h": 8,
         "config": {"dataSourceCode": "DS_REC_SYNTHESE_ANNUELLE", "dataSourceOrigin": "template",
                    "category_field": "Exercice", "value_fields": ["Total Creances", "Total Recouvre"],
                    "colors": ["#3b82f6", "#10b981"]}},
        {"id": "w2", "type": "line", "title": "Taux de Recouvrement", "x": 8, "y": 0, "w": 4, "h": 8,
         "config": {"dataSourceCode": "DS_REC_SYNTHESE_ANNUELLE", "dataSourceOrigin": "template",
                    "category_field": "Exercice", "value_fields": ["Taux Recouvrement"],
                    "colors": ["#8b5cf6"]}},
        {"id": "w3", "type": "table", "title": "Détail par Année", "x": 0, "y": 8, "w": 12, "h": 6,
         "config": {"dataSourceCode": "DS_REC_SYNTHESE_ANNUELLE", "dataSourceOrigin": "template",
                    "columns": ["Exercice", "Total Creances", "Total Recouvre", "Reste A Recouvrer", "Taux Recouvrement", "Nb Echeances", "Nb Clients"]}},
    ]),
]

# ======================================================================
# Menu icons
# ======================================================================
MENU_ICONS = {
    "Échéances Clients Détail": "FileText",
    "Créances Impayées": "AlertTriangle",
    "Règlements Reçus": "CheckCircle",
    "Balance Âgée Clients": "Scale",
    "Échéances avec Imputations": "Link",
    "Factures Échues Non Réglées": "XCircle",
    "Clients à Risque": "ShieldAlert",
    "Historique Règlements": "History",
    "Échéances à Venir": "CalendarClock",
    "Délai Moyen de Paiement": "Timer",
    "Suivi Échéances Clients": "ClipboardList",
    "Créances par Tranche d'Age": "Layers",
    "Règlements par Mode": "CreditCard",
    "Créances par Type Document": "FolderOpen",
    "Evolution Mensuelle Créances": "TrendingUp",
    "Taux Recouvrement par Client": "Target",
    "Règlements par Tiers Payeur": "Users",
    "TB Recouvrement Global": "LayoutGrid",
    "Evolution Mensuelle Recouvrement": "TrendingUp",
    "Répartition Balance Âgée": "PieChart",
    "Top 20 Débiteurs": "Award",
    "Répartition par Mode Règlement": "PieChart",
    "Taux Recouvrement Mensuel": "Target",
    "Niveau de Risque Clients": "ShieldAlert",
    "Encaissements Mensuels": "Banknote",
    "Synthèse Annuelle Recouvrement": "CalendarDays",
}


# ======================================================================
# MAIN
# ======================================================================
def main():
    import sys
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()

    # --- 0. Suppression si --reset ---
    if "--reset" in sys.argv:
        print("=" * 60)
        print("  SUPPRESSION DES RAPPORTS RECOUVREMENT EXISTANTS")
        print("=" * 60)

        # Codes DS recouvrement
        ds_codes = [ds["code"] for ds in DS_TEMPLATES]
        placeholders = ",".join(["?" for _ in ds_codes])

        # Supprimer menus liés aux gridviews, pivots, dashboards recouvrement
        cursor.execute("SELECT id FROM APP_Menus WHERE nom = 'Recouvrement' AND parent_id IS NULL")
        root = cursor.fetchone()
        if not root:
            cursor.execute("SELECT id FROM APP_Menus WHERE nom LIKE '%ecouvrement%' AND parent_id IS NULL")
            root = cursor.fetchone()
        if root:
            root_id = root[0]
            # Supprimer items de menus (sous-dossiers + items)
            cursor.execute("SELECT id FROM APP_Menus WHERE parent_id = ?", root_id)
            subfolder_ids = [r[0] for r in cursor.fetchall()]
            for sf_id in subfolder_ids:
                cursor.execute("DELETE FROM APP_Menus WHERE parent_id = ?", sf_id)
            cursor.execute("DELETE FROM APP_Menus WHERE parent_id = ?", root_id)
            print(f"  Menus items supprimes (racine id={root_id})")

        # Supprimer GridViews recouvrement
        cursor.execute(f"DELETE FROM APP_GridViews WHERE data_source_code IN ({placeholders})", *ds_codes)
        print(f"  GridViews supprimees ({cursor.rowcount} lignes)")

        # Supprimer Pivots V2 recouvrement
        cursor.execute(f"DELETE FROM APP_Pivots_V2 WHERE data_source_code IN ({placeholders})", *ds_codes)
        print(f"  Pivots V2 supprimes ({cursor.rowcount} lignes)")

        # Supprimer Dashboards recouvrement
        db_noms = [d[1] for d in DASHBOARDS]
        db_ph = ",".join(["?" for _ in db_noms])
        cursor.execute(f"DELETE FROM APP_Dashboards WHERE nom IN ({db_ph})", *db_noms)
        print(f"  Dashboards supprimes ({cursor.rowcount} lignes)")

        # Supprimer DataSource Templates recouvrement
        cursor.execute(f"DELETE FROM APP_DataSources_Templates WHERE code IN ({placeholders})", *ds_codes)
        print(f"  DataSource Templates supprimes ({cursor.rowcount} lignes)")

        conn.commit()
        print("  => Suppression terminee\n")

    print("=" * 60)
    print("  CREATION DES 25 RAPPORTS CREANCES & RECOUVREMENT")
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
            aliases = re.findall(r'ev\.\[([^\]]+)\]', query)

        columns = []
        for alias in aliases:
            if alias.lower() in ('societe',):
                continue
            fmt = "text"
            low = alias.lower()
            if any(k in low for k in ("montant", "solde", "reste", "total", "impaye", "regle", "encaiss", "creance", "recouvr", "caution", "bl ")):
                fmt = "currency"
            elif any(k in low for k in ("nb ", "nombre", "jours", "delai", "retard", "taux")):
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
            nom, f"Rapport Recouvrement - {nom}", ds_code, columns_json, total_cols_json, features_json)
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
            nom, f"Pivot Recouvrement - {nom}", ds_code,
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
            nom, f"Dashboard Recouvrement - {nom}", json.dumps(widgets))
        cursor.execute("SELECT @@IDENTITY")
        db_id = int(cursor.fetchone()[0])
        db_ids[ds_code] = db_id
        print(f"  + NEW Dashboard {nom} (id={db_id})")
    conn.commit()

    # --- 5. Menus ---
    print("\n[5/5] Creation des Menus...")

    # Menu racine
    cursor.execute("SELECT id FROM APP_Menus WHERE nom = 'Recouvrement' AND parent_id IS NULL")
    root = cursor.fetchone()
    if not root:
        cursor.execute("SELECT id FROM APP_Menus WHERE nom LIKE '%ecouvrement%' AND parent_id IS NULL")
        root = cursor.fetchone()
    if root:
        root_id = root[0]
        print(f"  OK EXISTS racine 'Recouvrement' (id={root_id})")
    else:
        cursor.execute("""INSERT INTO APP_Menus (nom, icon, type, parent_id, ordre, actif)
            VALUES ('Recouvrement', 'Receipt', 'folder', NULL, 40, 1)""")
        cursor.execute("SELECT @@IDENTITY")
        root_id = int(cursor.fetchone()[0])
        print(f"  + NEW racine 'Recouvrement' (id={root_id})")

    # Sous-dossiers
    subfolders = [
        ("Suivi des Créances", "FileText", 1),
        ("Analyses Recouvrement", "BarChart3", 2),
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
        # Suivi des Creances (11 gridviews)
        ("Suivi des Créances", "Échéances Clients Détail", "gridview", gv_ids.get("DS_REC_ECHEANCES_DETAIL"), 1),
        ("Suivi des Créances", "Créances Impayées", "gridview", gv_ids.get("DS_REC_IMPAYES"), 2),
        ("Suivi des Créances", "Règlements Reçus", "gridview", gv_ids.get("DS_REC_REGLEMENTS"), 3),
        ("Suivi des Créances", "Balance Âgée Clients", "gridview", gv_ids.get("DS_REC_BALANCE_AGEE"), 4),
        ("Suivi des Créances", "Échéances avec Imputations", "gridview", gv_ids.get("DS_REC_ECHEANCES_IMPUTATIONS"), 5),
        ("Suivi des Créances", "Factures Échues Non Réglées", "gridview", gv_ids.get("DS_REC_ECHUES_NON_REGLEES"), 6),
        ("Suivi des Créances", "Clients à Risque", "gridview", gv_ids.get("DS_REC_CLIENTS_RISQUE"), 7),
        ("Suivi des Créances", "Historique Règlements", "gridview", gv_ids.get("DS_REC_HISTORIQUE_CLIENT"), 8),
        ("Suivi des Créances", "Échéances à Venir", "gridview", gv_ids.get("DS_REC_ECHEANCES_A_VENIR"), 9),
        ("Suivi des Créances", "Délai Moyen de Paiement", "gridview", gv_ids.get("DS_REC_DELAI_PAIEMENT"), 10),
        ("Suivi des Créances", "Suivi Échéances Clients", "gridview", gv_ids.get("DS_REC_SUIVI_ECHEANCES"), 11),
        # Analyses Recouvrement (6 pivots)
        ("Analyses Recouvrement", "Créances par Tranche d'Age", "pivot-v2", pv_ids.get("DS_REC_PIVOT_BALANCE_AGEE"), 1),
        ("Analyses Recouvrement", "Règlements par Mode", "pivot-v2", pv_ids.get("DS_REC_PIVOT_MODE_REGLEMENT"), 2),
        ("Analyses Recouvrement", "Créances par Type Document", "pivot-v2", pv_ids.get("DS_REC_PIVOT_TYPE_DOC"), 3),
        ("Analyses Recouvrement", "Evolution Mensuelle Créances", "pivot-v2", pv_ids.get("DS_REC_PIVOT_EVOLUTION"), 4),
        ("Analyses Recouvrement", "Taux Recouvrement par Client", "pivot-v2", pv_ids.get("DS_REC_PIVOT_TAUX_CLIENT"), 5),
        ("Analyses Recouvrement", "Règlements par Tiers Payeur", "pivot-v2", pv_ids.get("DS_REC_PIVOT_TIERS_PAYEUR"), 6),
        # Tableaux de Bord (9 dashboards)
        ("Tableaux de Bord", "TB Recouvrement Global", "dashboard", db_ids.get("DS_REC_KPI_GLOBAL"), 1),
        ("Tableaux de Bord", "Evolution Mensuelle Recouvrement", "dashboard", db_ids.get("DS_REC_EVOLUTION_MENSUELLE"), 2),
        ("Tableaux de Bord", "Répartition Balance Âgée", "dashboard", db_ids.get("DS_REC_REPARTITION_AGEE"), 3),
        ("Tableaux de Bord", "Top 20 Débiteurs", "dashboard", db_ids.get("DS_REC_TOP_DEBITEURS"), 4),
        ("Tableaux de Bord", "Répartition par Mode Règlement", "dashboard", db_ids.get("DS_REC_REPARTITION_MODE"), 5),
        ("Tableaux de Bord", "Taux Recouvrement Mensuel", "dashboard", db_ids.get("DS_REC_TAUX_MENSUEL"), 6),
        ("Tableaux de Bord", "Niveau de Risque Clients", "dashboard", db_ids.get("DS_REC_NIVEAU_RISQUE"), 7),
        ("Tableaux de Bord", "Encaissements Mensuels", "dashboard", db_ids.get("DS_REC_ENCAISSEMENTS_MENS"), 8),
        ("Tableaux de Bord", "Synthèse Annuelle Recouvrement", "dashboard", db_ids.get("DS_REC_SYNTHESE_ANNUELLE"), 9),
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
