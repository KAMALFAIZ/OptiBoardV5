# -*- coding: utf-8 -*-
"""Fix stock report queries with proper accented column names"""
import pyodbc

conn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019;TrustServerCertificate=yes')
cursor = conn.cursor()

SOC_ES = "(@societe IS NULL OR es.societe = @societe)"
SOC_MV = "(@societe IS NULL OR mv.societe = @societe)"

queries = {}

queries["DS_STK_MOUVEMENTS"] = """SELECT
    mv.[Date Mouvement] AS [Date], mv.[Type Mouvement] AS [Type Mouvement], mv.[Domaine mouvement] AS [Domaine],
    mv.[Sens de mouvement] AS [Sens], mv.[Code article] AS [Code article], mv.[D\u00e9signation] AS [Designation],
    mv.[Code famille] AS [Code famille], mv.[Intitul\u00e9 famille] AS [Famille],
    mv.[Code D\u00e9p\u00f4t] AS [Code Depot], mv.[D\u00e9p\u00f4t] AS [Depot],
    mv.[Quantit\u00e9] AS [Quantite], mv.CMUP AS [CMUP], mv.[Montant Stock] AS [Montant Stock],
    mv.[N\u00b0 Pi\u00e8ce] AS [Num Piece], mv.[Code tiers] AS [Code tiers], mv.[Intitul\u00e9 tiers] AS [Tiers],
    mv.[Prix unitaire] AS [Prix unitaire], mv.[Prix de revient] AS [Prix de revient], mv.[DPA-P\u00e9riode] AS [DPA Periode],
    mv.[DPA-Vente] AS [DPA Vente], mv.[Co\u00fbt standard] AS [Cout standard], mv.[DPR-Vente] AS [DPR Vente],
    mv.[N\u00b0 S\u00e9rie / Lot] AS [Num Serie Lot], mv.[Suivi Stock] AS [Suivi Stock], mv.[Gamme 1] AS [Gamme 1], mv.[Gamme 2] AS [Gamme 2],
    mv.[Date P\u00e9remption] AS [Date Peremption], mv.[Date Fabrication] AS [Date Fabrication],
    mv.[Catalogue 1] AS [Catalogue 1], mv.[Catalogue 2] AS [Catalogue 2], mv.[Catalogue 3] AS [Catalogue 3], mv.[Catalogue 4] AS [Catalogue 4],
    mv.societe AS [Societe]
FROM Mouvement_stock mv
WHERE mv.[Date Mouvement] BETWEEN @dateDebut AND @dateFin
  AND """ + SOC_MV + """
ORDER BY mv.[Date Mouvement] DESC"""

queries["DS_STK_ENTREES"] = """SELECT
    mv.[Date Mouvement] AS [Date], mv.[Type Mouvement],
    mv.[Code article], mv.[D\u00e9signation] AS [Designation],
    mv.[Code famille], mv.[Intitul\u00e9 famille] AS [Famille],
    mv.[Code D\u00e9p\u00f4t], mv.[D\u00e9p\u00f4t] AS [Depot],
    mv.[Quantit\u00e9], mv.CMUP, mv.[Montant Stock],
    mv.[N\u00b0 Pi\u00e8ce] AS [Num Piece], mv.[Code tiers], mv.[Intitul\u00e9 tiers] AS [Tiers],
    mv.societe AS [Societe]
FROM Mouvement_stock mv
WHERE mv.[Sens de mouvement] = 'Entr\u00e9e'
  AND mv.[Date Mouvement] BETWEEN @dateDebut AND @dateFin
  AND """ + SOC_MV + """
ORDER BY mv.[Date Mouvement] DESC"""

queries["DS_STK_SORTIES"] = """SELECT
    mv.[Date Mouvement] AS [Date], mv.[Type Mouvement],
    mv.[Code article], mv.[D\u00e9signation] AS [Designation],
    mv.[Code famille], mv.[Intitul\u00e9 famille] AS [Famille],
    mv.[Code D\u00e9p\u00f4t], mv.[D\u00e9p\u00f4t] AS [Depot],
    mv.[Quantit\u00e9], mv.CMUP, mv.[Montant Stock],
    mv.[N\u00b0 Pi\u00e8ce] AS [Num Piece], mv.[Code tiers], mv.[Intitul\u00e9 tiers] AS [Tiers],
    mv.societe AS [Societe]
FROM Mouvement_stock mv
WHERE mv.[Sens de mouvement] = 'Sortie'
  AND mv.[Date Mouvement] BETWEEN @dateDebut AND @dateFin
  AND """ + SOC_MV + """
ORDER BY mv.[Date Mouvement] DESC"""

queries["DS_STK_ETAT_ACTUEL"] = """SELECT
    es.[Code article], es.[D\u00e9signation article] AS [Designation],
    es.[Code famille], es.[Intitule] AS [Famille],
    es.[Catalogue 1] AS [Catalogue], es.[Unit\u00e9] AS [Unite],
    es.[Code d\u00e9p\u00f4t], es.[DE_Intitule] AS [Depot],
    es.[Quantit\u00e9 en stock] AS [Qte Stock],
    es.[Valeur du stock (montant)] AS [Valeur Stock],
    es.[Quantit\u00e9 minimale] AS [Qte Min],
    es.[Quantit\u00e9 maximale] AS [Qte Max],
    es.[Quntitt\u00e9 r\u00e9serv\u00e9e] AS [Qte Reservee],
    es.[Quantit\u00e9 command\u00e9e] AS [Qte Commandee],
    es.[Stock mouvement\u00e9] AS [Mouvemente],
    es.[D\u00e9p\u00f4t principale] AS [Depot Principal],
    es.societe AS [Societe]
FROM Etat_Stock es
WHERE """ + SOC_ES + """
ORDER BY es.[Valeur du stock (montant)] DESC"""

queries["DS_STK_PAR_DEPOT"] = """SELECT
    es.[Code d\u00e9p\u00f4t], es.[DE_Intitule] AS [Depot],
    COUNT(DISTINCT es.[Code article]) AS [Nb Articles],
    SUM(es.[Quantit\u00e9 en stock]) AS [Qte Totale],
    SUM(es.[Valeur du stock (montant)]) AS [Valeur Stock],
    SUM(CASE WHEN es.[Quantit\u00e9 en stock] <= 0 THEN 1 ELSE 0 END) AS [Articles Rupture],
    SUM(CASE WHEN es.[Quantit\u00e9 en stock] > es.[Quantit\u00e9 maximale] AND es.[Quantit\u00e9 maximale] > 0 THEN 1 ELSE 0 END) AS [Articles Surstock],
    es.societe AS [Societe]
FROM Etat_Stock es
WHERE """ + SOC_ES + """
GROUP BY es.[Code d\u00e9p\u00f4t], es.[DE_Intitule], es.societe
ORDER BY SUM(es.[Valeur du stock (montant)]) DESC"""

queries["DS_STK_RUPTURE"] = """SELECT
    es.[Code article], es.[D\u00e9signation article] AS [Designation],
    es.[Code famille], es.[Intitule] AS [Famille], es.[Catalogue 1] AS [Catalogue],
    es.[Code d\u00e9p\u00f4t], es.[DE_Intitule] AS [Depot],
    es.[Quantit\u00e9 en stock] AS [Qte Stock], es.[Quantit\u00e9 minimale] AS [Qte Min],
    es.[Quantit\u00e9 command\u00e9e] AS [Qte Commandee], es.[Stock mouvement\u00e9] AS [Mouvemente],
    es.societe AS [Societe]
FROM Etat_Stock es
WHERE es.[Quantit\u00e9 en stock] <= 0 AND es.[Stock mouvement\u00e9] = 'Oui' AND """ + SOC_ES + """
ORDER BY es.[Code famille], es.[D\u00e9signation article]"""

queries["DS_STK_SURSTOCK"] = """SELECT
    es.[Code article], es.[D\u00e9signation article] AS [Designation],
    es.[Code famille], es.[Intitule] AS [Famille], es.[Catalogue 1] AS [Catalogue],
    es.[Code d\u00e9p\u00f4t], es.[DE_Intitule] AS [Depot],
    es.[Quantit\u00e9 en stock] AS [Qte Stock], es.[Quantit\u00e9 maximale] AS [Qte Max],
    es.[Quantit\u00e9 en stock] - es.[Quantit\u00e9 maximale] AS [Excedent],
    es.[Valeur du stock (montant)] AS [Valeur Stock], es.societe AS [Societe]
FROM Etat_Stock es
WHERE es.[Quantit\u00e9 maximale] > 0 AND es.[Quantit\u00e9 en stock] > es.[Quantit\u00e9 maximale] AND """ + SOC_ES + """
ORDER BY es.[Quantit\u00e9 en stock] - es.[Quantit\u00e9 maximale] DESC"""

queries["DS_STK_VALORISATION"] = """SELECT
    es.[Code famille], es.[Intitule] AS [Famille], es.[Catalogue 1] AS [Catalogue],
    es.[Code d\u00e9p\u00f4t], es.[DE_Intitule] AS [Depot],
    COUNT(DISTINCT es.[Code article]) AS [Nb Articles],
    SUM(es.[Quantit\u00e9 en stock]) AS [Qte Stock],
    SUM(es.[Valeur du stock (montant)]) AS [Valeur Stock],
    AVG(CASE WHEN es.[Quantit\u00e9 en stock] > 0 THEN es.[Valeur du stock (montant)] / es.[Quantit\u00e9 en stock] END) AS [CU Moyen],
    es.societe AS [Societe]
FROM Etat_Stock es WHERE """ + SOC_ES + """
GROUP BY es.[Code famille], es.[Intitule], es.[Catalogue 1], es.[Code d\u00e9p\u00f4t], es.[DE_Intitule], es.societe
ORDER BY SUM(es.[Valeur du stock (montant)]) DESC"""

queries["DS_STK_ROTATION"] = """SELECT
    es.[Code article], es.[D\u00e9signation article] AS [Designation],
    es.[Code famille], es.[Intitule] AS [Famille],
    es.[Quantit\u00e9 en stock] AS [Qte Stock], es.[Valeur du stock (montant)] AS [Valeur Stock],
    ISNULL(sortie.qte_sortie, 0) AS [Qte Sortie Periode],
    CASE WHEN ISNULL(sortie.qte_sortie, 0) > 0 AND es.[Quantit\u00e9 en stock] > 0
         THEN ROUND(ISNULL(sortie.qte_sortie, 0) / es.[Quantit\u00e9 en stock], 2) ELSE 0 END AS [Taux Rotation],
    CASE WHEN ISNULL(sortie.qte_sortie, 0) > 0
         THEN ROUND(es.[Quantit\u00e9 en stock] / (ISNULL(sortie.qte_sortie, 0) / 365.0), 0) ELSE 999 END AS [Jours Couverture],
    es.societe AS [Societe]
FROM Etat_Stock es
LEFT JOIN (SELECT mv.[Code article], mv.societe, SUM(mv.[Quantit\u00e9]) AS qte_sortie FROM Mouvement_stock mv WHERE mv.[Sens de mouvement] = 'Sortie' AND mv.[Date Mouvement] BETWEEN @dateDebut AND @dateFin GROUP BY mv.[Code article], mv.societe) sortie ON es.[Code article] = sortie.[Code article] AND es.societe = sortie.societe
WHERE es.[Quantit\u00e9 en stock] > 0 AND """ + SOC_ES

queries["DS_STK_EVOLUTION_MENSUELLE"] = """SELECT
    YEAR(mv.[Date Mouvement]) AS [Annee], MONTH(mv.[Date Mouvement]) AS [Mois],
    CAST(YEAR(mv.[Date Mouvement]) AS VARCHAR) + '-' + RIGHT('0' + CAST(MONTH(mv.[Date Mouvement]) AS VARCHAR), 2) AS [Periode],
    SUM(CASE WHEN mv.[Sens de mouvement] = 'Entr\u00e9e' THEN mv.[Quantit\u00e9] ELSE 0 END) AS [Entrees Qte],
    SUM(CASE WHEN mv.[Sens de mouvement] = 'Sortie' THEN mv.[Quantit\u00e9] ELSE 0 END) AS [Sorties Qte],
    SUM(CASE WHEN mv.[Sens de mouvement] = 'Entr\u00e9e' THEN mv.[Montant Stock] ELSE 0 END) AS [Entrees Valeur],
    SUM(CASE WHEN mv.[Sens de mouvement] = 'Sortie' THEN mv.[Montant Stock] ELSE 0 END) AS [Sorties Valeur],
    COUNT(DISTINCT mv.[Code article]) AS [Nb Articles], mv.societe AS [Societe]
FROM Mouvement_stock mv
WHERE mv.[Date Mouvement] BETWEEN @dateDebut AND @dateFin AND """ + SOC_MV + """
GROUP BY YEAR(mv.[Date Mouvement]), MONTH(mv.[Date Mouvement]), mv.societe
ORDER BY YEAR(mv.[Date Mouvement]), MONTH(mv.[Date Mouvement])"""

queries["DS_STK_DORMANT"] = """SELECT
    es.[Code article], es.[D\u00e9signation article] AS [Designation],
    es.[Code famille], es.[Intitule] AS [Famille], es.[Catalogue 1] AS [Catalogue],
    es.[Code d\u00e9p\u00f4t], es.[DE_Intitule] AS [Depot],
    es.[Quantit\u00e9 en stock] AS [Qte Stock], es.[Valeur du stock (montant)] AS [Valeur Stock],
    es.societe AS [Societe]
FROM Etat_Stock es
WHERE es.[Quantit\u00e9 en stock] > 0 AND es.[Stock mouvement\u00e9] = 'Non' AND """ + SOC_ES + """
ORDER BY es.[Valeur du stock (montant)] DESC"""

queries["DS_STK_ABC"] = """SELECT
    es.[Code article], es.[D\u00e9signation article] AS [Designation],
    es.[Code famille], es.[Intitule] AS [Famille],
    es.[Quantit\u00e9 en stock] AS [Qte Stock], es.[Valeur du stock (montant)] AS [Valeur Stock],
    SUM(es.[Valeur du stock (montant)]) OVER (ORDER BY es.[Valeur du stock (montant)] DESC) AS [Cumul Valeur],
    ROUND(100.0 * SUM(es.[Valeur du stock (montant)]) OVER (ORDER BY es.[Valeur du stock (montant)] DESC) / NULLIF(SUM(es.[Valeur du stock (montant)]) OVER (), 0), 2) AS [Cumul Pct],
    CASE WHEN 100.0 * SUM(es.[Valeur du stock (montant)]) OVER (ORDER BY es.[Valeur du stock (montant)] DESC) / NULLIF(SUM(es.[Valeur du stock (montant)]) OVER (), 0) <= 80 THEN 'A'
         WHEN 100.0 * SUM(es.[Valeur du stock (montant)]) OVER (ORDER BY es.[Valeur du stock (montant)] DESC) / NULLIF(SUM(es.[Valeur du stock (montant)]) OVER (), 0) <= 95 THEN 'B' ELSE 'C' END AS [Classe ABC],
    es.societe AS [Societe]
FROM Etat_Stock es
WHERE es.[Quantit\u00e9 en stock] > 0 AND """ + SOC_ES + """
ORDER BY es.[Valeur du stock (montant)] DESC"""

queries["DS_STK_COUVERTURE"] = """SELECT
    es.[Code famille], es.[Intitule] AS [Famille],
    COUNT(DISTINCT es.[Code article]) AS [Nb Articles],
    SUM(es.[Quantit\u00e9 en stock]) AS [Qte Stock], SUM(es.[Valeur du stock (montant)]) AS [Valeur Stock],
    ISNULL(SUM(sortie.qte_mois), 0) AS [Consommation Mensuelle],
    CASE WHEN ISNULL(SUM(sortie.qte_mois), 0) > 0 THEN ROUND(SUM(es.[Quantit\u00e9 en stock]) / SUM(sortie.qte_mois), 1) ELSE 999 END AS [Mois Couverture],
    es.societe AS [Societe]
FROM Etat_Stock es
LEFT JOIN (SELECT mv.[Code famille], mv.societe, SUM(mv.[Quantit\u00e9]) / NULLIF(DATEDIFF(month, @dateDebut, @dateFin) + 1, 0) AS qte_mois FROM Mouvement_stock mv WHERE mv.[Sens de mouvement] = 'Sortie' AND mv.[Date Mouvement] BETWEEN @dateDebut AND @dateFin GROUP BY mv.[Code famille], mv.societe) sortie ON es.[Code famille] = sortie.[Code famille] AND es.societe = sortie.societe
WHERE es.[Quantit\u00e9 en stock] > 0 AND """ + SOC_ES + """
GROUP BY es.[Code famille], es.[Intitule], es.societe"""

queries["DS_STK_INVENTAIRE_COMPARATIF"] = """SELECT
    es.[Code d\u00e9p\u00f4t], es.[DE_Intitule] AS [Depot], es.[Code famille], es.[Intitule] AS [Famille],
    COUNT(DISTINCT es.[Code article]) AS [Nb References], SUM(es.[Quantit\u00e9 en stock]) AS [Qte Stock],
    SUM(es.[Valeur du stock (montant)]) AS [Valeur Stock],
    SUM(CASE WHEN es.[Quantit\u00e9 en stock] > 0 THEN 1 ELSE 0 END) AS [Ref En Stock],
    SUM(CASE WHEN es.[Quantit\u00e9 en stock] <= 0 THEN 1 ELSE 0 END) AS [Ref Rupture],
    ROUND(100.0 * SUM(CASE WHEN es.[Quantit\u00e9 en stock] > 0 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1) AS [Taux Dispo Pct],
    es.societe AS [Societe]
FROM Etat_Stock es WHERE """ + SOC_ES + """
GROUP BY es.[Code d\u00e9p\u00f4t], es.[DE_Intitule], es.[Code famille], es.[Intitule], es.societe
ORDER BY es.[Code d\u00e9p\u00f4t], SUM(es.[Valeur du stock (montant)]) DESC"""

queries["DS_STK_TRANSFERTS"] = u"""SELECT
    mv.[Date Mouvement] AS [Date], mv.[Code D\u00e9p\u00f4t], mv.[D\u00e9p\u00f4t] AS [Depot],
    mv.[Code article], mv.[D\u00e9signation] AS [Designation],
    mv.[Code famille], mv.[Intitul\u00e9 famille] AS [Famille],
    mv.[Sens de mouvement] AS [Sens], mv.[Quantit\u00e9], mv.[Montant Stock],
    mv.[N\u00b0 Pi\u00e8ce] AS [Num Piece], mv.societe AS [Societe]
FROM Mouvement_stock mv
WHERE mv.[Type Mouvement] = 'Virement de d\u00e9p\u00f4t \u00e0 d\u00e9p\u00f4t'
  AND mv.[Date Mouvement] BETWEEN @dateDebut AND @dateFin AND """ + SOC_MV + """
ORDER BY mv.[Date Mouvement] DESC"""

queries["DS_STK_ABC_XYZ"] = """SELECT
    es.[Code article], es.[D\u00e9signation article] AS [Designation],
    es.[Code famille], es.[Intitule] AS [Famille],
    es.[Quantit\u00e9 en stock] AS [Qte Stock], es.[Valeur du stock (montant)] AS [Valeur Stock],
    CASE WHEN 100.0 * SUM(es.[Valeur du stock (montant)]) OVER (ORDER BY es.[Valeur du stock (montant)] DESC) / NULLIF(SUM(es.[Valeur du stock (montant)]) OVER (), 0) <= 80 THEN 'A'
         WHEN 100.0 * SUM(es.[Valeur du stock (montant)]) OVER (ORDER BY es.[Valeur du stock (montant)] DESC) / NULLIF(SUM(es.[Valeur du stock (montant)]) OVER (), 0) <= 95 THEN 'B' ELSE 'C' END AS [Classe ABC],
    CASE WHEN es.[Stock mouvement\u00e9] = 'Oui' THEN 'X-Regulier' ELSE 'Z-Dormant' END AS [Classe XYZ],
    es.societe AS [Societe]
FROM Etat_Stock es
WHERE es.[Quantit\u00e9 en stock] > 0 AND """ + SOC_ES + """
ORDER BY es.[Valeur du stock (montant)] DESC"""

queries["DS_STK_PREVISION_RUPTURE"] = """SELECT
    es.[Code article], es.[D\u00e9signation article] AS [Designation],
    es.[Code famille], es.[Intitule] AS [Famille],
    es.[Code d\u00e9p\u00f4t], es.[DE_Intitule] AS [Depot],
    es.[Quantit\u00e9 en stock] AS [Qte Stock], es.[Quantit\u00e9 minimale] AS [Seuil Min],
    ISNULL(sortie.qte_jour, 0) AS [Conso Journaliere],
    CASE WHEN ISNULL(sortie.qte_jour, 0) > 0 THEN ROUND(es.[Quantit\u00e9 en stock] / sortie.qte_jour, 0) ELSE 999 END AS [Jours Restants],
    CASE WHEN ISNULL(sortie.qte_jour, 0) > 0 AND es.[Quantit\u00e9 en stock] / sortie.qte_jour <= 7 THEN 'CRITIQUE'
         WHEN ISNULL(sortie.qte_jour, 0) > 0 AND es.[Quantit\u00e9 en stock] / sortie.qte_jour <= 30 THEN 'ALERTE' ELSE 'OK' END AS [Statut],
    es.societe AS [Societe]
FROM Etat_Stock es
LEFT JOIN (SELECT mv.[Code article], mv.societe, SUM(mv.[Quantit\u00e9]) / NULLIF(DATEDIFF(day, @dateDebut, @dateFin) + 1, 0) AS qte_jour FROM Mouvement_stock mv WHERE mv.[Sens de mouvement] = 'Sortie' AND mv.[Date Mouvement] BETWEEN @dateDebut AND @dateFin GROUP BY mv.[Code article], mv.societe) sortie ON es.[Code article] = sortie.[Code article] AND es.societe = sortie.societe
WHERE es.[Quantit\u00e9 en stock] > 0 AND """ + SOC_ES

queries["DS_STK_COUT_POSSESSION"] = """SELECT
    es.[Code famille], es.[Intitule] AS [Famille], es.[Catalogue 1] AS [Catalogue],
    COUNT(DISTINCT es.[Code article]) AS [Nb Articles], SUM(es.[Quantit\u00e9 en stock]) AS [Qte Stock],
    SUM(es.[Valeur du stock (montant)]) AS [Valeur Stock],
    ROUND(SUM(es.[Valeur du stock (montant)]) * 0.15, 2) AS [Cout Possession Annuel],
    ROUND(100.0 * SUM(es.[Valeur du stock (montant)]) / NULLIF(SUM(SUM(es.[Valeur du stock (montant)])) OVER (), 0), 2) AS [Part Valeur Pct],
    es.societe AS [Societe]
FROM Etat_Stock es
WHERE es.[Quantit\u00e9 en stock] > 0 AND """ + SOC_ES + """
GROUP BY es.[Code famille], es.[Intitule], es.[Catalogue 1], es.societe
ORDER BY SUM(es.[Valeur du stock (montant)]) DESC"""

queries["DS_STK_OBSOLESCENCE"] = """SELECT
    es.[Code famille], es.[Intitule] AS [Famille], COUNT(*) AS [Nb Total Ref],
    SUM(CASE WHEN es.[Stock mouvement\u00e9] = 'Non' AND es.[Quantit\u00e9 en stock] > 0 THEN 1 ELSE 0 END) AS [Ref Dormantes],
    SUM(CASE WHEN es.[Stock mouvement\u00e9] = 'Non' AND es.[Quantit\u00e9 en stock] > 0 THEN es.[Valeur du stock (montant)] ELSE 0 END) AS [Valeur Dormante],
    ROUND(100.0 * SUM(CASE WHEN es.[Stock mouvement\u00e9] = 'Non' AND es.[Quantit\u00e9 en stock] > 0 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1) AS [Taux Obsolescence Pct],
    SUM(es.[Valeur du stock (montant)]) AS [Valeur Totale], es.societe AS [Societe]
FROM Etat_Stock es WHERE """ + SOC_ES + """
GROUP BY es.[Code famille], es.[Intitule], es.societe"""

queries["DS_STK_MIN_COMMANDE"] = """SELECT
    es.[Code article], es.[D\u00e9signation article] AS [Designation],
    es.[Code famille], es.[Intitule] AS [Famille],
    es.[Code d\u00e9p\u00f4t], es.[DE_Intitule] AS [Depot],
    es.[Quantit\u00e9 en stock] AS [Qte Stock], es.[Quantit\u00e9 minimale] AS [Stock Min],
    es.[Quantit\u00e9 maximale] AS [Stock Max], es.[Quantit\u00e9 command\u00e9e] AS [Qte Commandee],
    CASE WHEN es.[Quantit\u00e9 en stock] <= es.[Quantit\u00e9 minimale] THEN 'A COMMANDER'
         WHEN es.[Quantit\u00e9 en stock] <= es.[Quantit\u00e9 minimale] * 1.5 THEN 'SURVEILLER' ELSE 'OK' END AS [Statut],
    es.[Quantit\u00e9 maximale] - es.[Quantit\u00e9 en stock] AS [Qte a Commander],
    es.societe AS [Societe]
FROM Etat_Stock es
WHERE es.[Quantit\u00e9 minimale] > 0 AND """ + SOC_ES

queries["DS_STK_ECARTS_INVENTAIRE"] = """SELECT
    es.[Code d\u00e9p\u00f4t], es.[DE_Intitule] AS [Depot], es.[Code famille], es.[Intitule] AS [Famille],
    COUNT(DISTINCT es.[Code article]) AS [Nb Articles], SUM(es.[Quantit\u00e9 en stock]) AS [Qte Stock],
    SUM(es.[Valeur du stock (montant)]) AS [Valeur Stock],
    SUM(CASE WHEN es.[Quantit\u00e9 de contr\u00f4le] <> 0 THEN 1 ELSE 0 END) AS [Avec Ecart],
    SUM(es.[Quantit\u00e9 de contr\u00f4le]) AS [Ecart Total Qte],
    ROUND(100.0 * SUM(CASE WHEN es.[Quantit\u00e9 de contr\u00f4le] <> 0 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1) AS [Taux Ecart Pct],
    es.societe AS [Societe]
FROM Etat_Stock es WHERE """ + SOC_ES + """
GROUP BY es.[Code d\u00e9p\u00f4t], es.[DE_Intitule], es.[Code famille], es.[Intitule], es.societe"""

queries["DS_STK_FLUX_DEPOT"] = """SELECT
    mv.[Code D\u00e9p\u00f4t], mv.[D\u00e9p\u00f4t] AS [Depot],
    CAST(YEAR(mv.[Date Mouvement]) AS VARCHAR) + '-' + RIGHT('0' + CAST(MONTH(mv.[Date Mouvement]) AS VARCHAR), 2) AS [Periode],
    SUM(CASE WHEN mv.[Sens de mouvement] = 'Entr\u00e9e' THEN mv.[Quantit\u00e9] ELSE 0 END) AS [Entrees],
    SUM(CASE WHEN mv.[Sens de mouvement] = 'Sortie' THEN mv.[Quantit\u00e9] ELSE 0 END) AS [Sorties],
    SUM(CASE WHEN mv.[Sens de mouvement] = 'Entr\u00e9e' THEN mv.[Montant Stock] ELSE 0 END) AS [Valeur Entrees],
    SUM(CASE WHEN mv.[Sens de mouvement] = 'Sortie' THEN mv.[Montant Stock] ELSE 0 END) AS [Valeur Sorties],
    COUNT(DISTINCT mv.[Code article]) AS [Nb Articles], mv.societe AS [Societe]
FROM Mouvement_stock mv
WHERE mv.[Date Mouvement] BETWEEN @dateDebut AND @dateFin AND """ + SOC_MV + """
GROUP BY mv.[Code D\u00e9p\u00f4t], mv.[D\u00e9p\u00f4t], YEAR(mv.[Date Mouvement]), MONTH(mv.[Date Mouvement]), mv.societe
ORDER BY mv.[Code D\u00e9p\u00f4t], YEAR(mv.[Date Mouvement]), MONTH(mv.[Date Mouvement])"""

queries["DS_STK_LEAD_TIME"] = """SELECT
    es.[Code famille], es.[Intitule] AS [Famille],
    COUNT(DISTINCT es.[Code article]) AS [Nb Articles], SUM(es.[Quantit\u00e9 en stock]) AS [Qte Stock],
    SUM(es.[Quantit\u00e9 minimale]) AS [Stock Securite Total],
    SUM(es.[Valeur du stock (montant)]) AS [Valeur Stock],
    ROUND(AVG(CASE WHEN es.[Quantit\u00e9 minimale] > 0 THEN es.[Quantit\u00e9 en stock] / es.[Quantit\u00e9 minimale] END), 2) AS [Ratio Stock Securite],
    SUM(CASE WHEN es.[Quantit\u00e9 en stock] < es.[Quantit\u00e9 minimale] THEN 1 ELSE 0 END) AS [Sous Seuil],
    es.societe AS [Societe]
FROM Etat_Stock es
WHERE es.[Quantit\u00e9 minimale] > 0 AND """ + SOC_ES + """
GROUP BY es.[Code famille], es.[Intitule], es.societe"""

queries["DS_STK_VALORISATION_MULTI"] = """SELECT
    es.[Code famille], es.[Intitule] AS [Famille], es.[Catalogue 1] AS [Catalogue],
    COUNT(DISTINCT es.[Code article]) AS [Nb Articles], SUM(es.[Quantit\u00e9 en stock]) AS [Qte Stock],
    SUM(es.[Valeur du stock (montant)]) AS [Valeur CMUP],
    ROUND(100.0 * SUM(es.[Valeur du stock (montant)]) / NULLIF(SUM(SUM(es.[Valeur du stock (montant)])) OVER (), 0), 2) AS [Part Pct],
    es.societe AS [Societe]
FROM Etat_Stock es
WHERE es.[Quantit\u00e9 en stock] > 0 AND """ + SOC_ES + """
GROUP BY es.[Code famille], es.[Intitule], es.[Catalogue 1], es.societe
ORDER BY SUM(es.[Valeur du stock (montant)]) DESC"""

queries["DS_STK_PRODUCTIVITE"] = """SELECT
    mv.[Code D\u00e9p\u00f4t], mv.[D\u00e9p\u00f4t] AS [Depot],
    COUNT(*) AS [Nb Mouvements], COUNT(DISTINCT mv.[Code article]) AS [Nb Articles Geres],
    SUM(mv.[Quantit\u00e9]) AS [Qte Totale Mvt], SUM(mv.[Montant Stock]) AS [Valeur Totale Mvt],
    COUNT(DISTINCT mv.[N\u00b0 Pi\u00e8ce]) AS [Nb Pieces],
    SUM(CASE WHEN mv.[Sens de mouvement] = 'Entr\u00e9e' THEN 1 ELSE 0 END) AS [Nb Entrees],
    SUM(CASE WHEN mv.[Sens de mouvement] = 'Sortie' THEN 1 ELSE 0 END) AS [Nb Sorties],
    mv.societe AS [Societe]
FROM Mouvement_stock mv
WHERE mv.[Date Mouvement] BETWEEN @dateDebut AND @dateFin AND """ + SOC_MV + """
GROUP BY mv.[Code D\u00e9p\u00f4t], mv.[D\u00e9p\u00f4t], mv.societe
ORDER BY COUNT(*) DESC"""

# Update all templates
updated = 0
for code, query in queries.items():
    cursor.execute("UPDATE APP_DataSources_Templates SET query_template=? WHERE code=?", query, code)
    updated += cursor.rowcount

conn.commit()
print(f"Updated {updated} templates with proper accented column names")
conn.close()
