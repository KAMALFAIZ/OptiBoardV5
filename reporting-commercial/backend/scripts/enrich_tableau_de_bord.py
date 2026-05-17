# -*- coding: utf-8 -*-
"""
Enrichit le menu "Tableau de Bord" avec un maximum d'indicateurs :
KPIs, graphiques, tops, analyses.
"""
import sys, os, json, uuid
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import get_db_cursor


# ─── Helper : short unique code ──────────────────────────────────────
def ucode(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:6]}"


# ─── DATASOURCES à créer ─────────────────────────────────────────────
NEW_DATASOURCES = [
    # ── Synthèse Ventes ──
    {
        "code": "DS_TB_SYNTHESE_VENTES",
        "nom": "TB Synthèse Ventes",
        "description": "KPIs principaux ventes : CA, Marge, Nb Clients, Nb Documents, Panier Moyen, Taux Marge",
        "query": """
SELECT
    ISNULL(SUM([Montant HT Net]), 0) AS [CA HT],
    ISNULL(SUM([Montant TTC Net]), 0) AS [CA TTC],
    ISNULL(SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]), 0) AS [Marge],
    CASE WHEN SUM([Montant HT Net]) > 0
        THEN ROUND(SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) * 100.0 / SUM([Montant HT Net]), 2)
        ELSE 0 END AS [Taux Marge %],
    COUNT(DISTINCT [Code client]) AS [Nb Clients],
    COUNT(DISTINCT [N° Pièce]) AS [Nb Documents],
    ISNULL(SUM([Quantité]), 0) AS [Qte Totale],
    CASE WHEN COUNT(DISTINCT [N° Pièce]) > 0
        THEN ROUND(SUM([Montant HT Net]) * 1.0 / COUNT(DISTINCT [N° Pièce]), 2)
        ELSE 0 END AS [Panier Moyen],
    CASE WHEN COUNT(DISTINCT [Code client]) > 0
        THEN ROUND(SUM([Montant HT Net]) * 1.0 / COUNT(DISTINCT [Code client]), 2)
        ELSE 0 END AS [CA Moyen par Client]
FROM [Lignes_des_ventes]
WHERE [Valorise CA] = 'Oui'
  AND [Date BL] BETWEEN @dateDebut AND @dateFin
  AND (@societe IS NULL OR [societe] = @societe)
""",
    },

    # ── Evolution CA Mensuel ──
    {
        "code": "DS_TB_CA_MENSUEL",
        "nom": "TB Evolution CA Mensuel",
        "description": "CA HT et Marge par mois pour graphique ligne/barre",
        "query": """
SELECT
    FORMAT([Date BL], 'yyyy-MM') AS [Mois],
    DATENAME(MONTH, [Date BL]) + ' ' + CAST(YEAR([Date BL]) AS VARCHAR) AS [Periode],
    SUM([Montant HT Net]) AS [CA HT],
    SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) AS [Marge],
    COUNT(DISTINCT [Code client]) AS [Nb Clients],
    COUNT(DISTINCT [N° Pièce]) AS [Nb Documents]
FROM [Lignes_des_ventes]
WHERE [Valorise CA] = 'Oui'
  AND [Date BL] BETWEEN @dateDebut AND @dateFin
  AND (@societe IS NULL OR [societe] = @societe)
GROUP BY FORMAT([Date BL], 'yyyy-MM'), DATENAME(MONTH, [Date BL]) + ' ' + CAST(YEAR([Date BL]) AS VARCHAR)
ORDER BY [Mois]
""",
    },

    # ── Top 10 Commerciaux ──
    {
        "code": "DS_TB_TOP_COMMERCIAUX",
        "nom": "TB Top 10 Commerciaux",
        "description": "Top 10 commerciaux par CA",
        "query": """
SELECT TOP 10
    e.[Nom représentant] AS [Commercial],
    SUM(l.[Montant HT Net]) AS [CA HT],
    SUM(l.[Montant HT Net] - ISNULL(l.[CMUP], 0) * l.[Quantité]) AS [Marge],
    COUNT(DISTINCT l.[Code client]) AS [Nb Clients],
    COUNT(DISTINCT l.[N° Pièce]) AS [Nb Documents]
FROM [Lignes_des_ventes] l
INNER JOIN [Entête_des_ventes] e ON l.[N° Pièce] = e.[N° pièce] AND l.[societe] = e.[societe]
WHERE l.[Valorise CA] = 'Oui'
  AND l.[Date BL] BETWEEN @dateDebut AND @dateFin
  AND (@societe IS NULL OR l.[societe] = @societe)
  AND e.[Nom représentant] IS NOT NULL AND e.[Nom représentant] <> ''
GROUP BY e.[Nom représentant]
ORDER BY [CA HT] DESC
""",
    },

    # ── Répartition CA par Catalogue/Gamme ──
    {
        "code": "DS_TB_CA_PAR_CATALOGUE",
        "nom": "TB CA par Catalogue",
        "description": "Répartition CA par catalogue pour pie chart",
        "query": """
SELECT TOP 15
    ISNULL([Catalogue 1], 'Non classé') AS [Catalogue],
    SUM([Montant HT Net]) AS [CA HT],
    SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) AS [Marge],
    COUNT(DISTINCT [Code article]) AS [Nb Articles]
FROM [Lignes_des_ventes]
WHERE [Valorise CA] = 'Oui'
  AND [Date BL] BETWEEN @dateDebut AND @dateFin
  AND (@societe IS NULL OR [societe] = @societe)
GROUP BY ISNULL([Catalogue 1], 'Non classé')
ORDER BY [CA HT] DESC
""",
    },

    # ── Top 10 Familles ──
    {
        "code": "DS_TB_TOP_FAMILLES",
        "nom": "TB Top 10 Familles",
        "description": "Top 10 familles d'articles par CA",
        "query": """
SELECT TOP 10
    ISNULL([Catalogue 1], 'Non classé') AS [Famille],
    SUM([Montant HT Net]) AS [CA HT],
    SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) AS [Marge],
    COUNT(DISTINCT [Code article]) AS [Nb Articles],
    SUM([Quantité]) AS [Qte Vendue]
FROM [Lignes_des_ventes]
WHERE [Valorise CA] = 'Oui'
  AND [Date BL] BETWEEN @dateDebut AND @dateFin
  AND (@societe IS NULL OR [societe] = @societe)
GROUP BY ISNULL([Catalogue 1], 'Non classé')
ORDER BY [CA HT] DESC
""",
    },

    # ── Synthèse Recouvrement ──
    {
        "code": "DS_TB_SYNTHESE_RECOUVREMENT",
        "nom": "TB Synthèse Recouvrement",
        "description": "KPIs recouvrement : encours, échéances, créances douteuses",
        "query": """
SELECT
    ISNULL(SUM(e.[Montant échéance]), 0) AS [Total Echeances],
    ISNULL(SUM(ISNULL(ifv.Total_Regle, 0)), 0) AS [Total Regle],
    ISNULL(SUM(e.[Montant échéance] - ISNULL(ifv.Total_Regle, 0)), 0) AS [Encours Total],
    CASE WHEN SUM(e.[Montant échéance]) > 0
        THEN ROUND(SUM(ISNULL(ifv.Total_Regle, 0)) * 100.0 / SUM(e.[Montant échéance]), 2)
        ELSE 0 END AS [Taux Recouvrement],
    SUM(CASE WHEN e.[Montant échéance] > ISNULL(ifv.Total_Regle, 0)
             AND DATEDIFF(DAY, e.[Date d'échéance], CAST(GETDATE() AS DATE)) > 0 THEN 1 ELSE 0 END) AS [Nb Echues],
    SUM(CASE WHEN e.[Montant échéance] > ISNULL(ifv.Total_Regle, 0)
             AND DATEDIFF(DAY, e.[Date d'échéance], CAST(GETDATE() AS DATE)) > 120
        THEN e.[Montant échéance] - ISNULL(ifv.Total_Regle, 0) ELSE 0 END) AS [Creances Douteuses 120j],
    COUNT(DISTINCT e.[Code client]) AS [Nb Clients Debiteurs]
FROM [Echéances_Ventes] e
LEFT JOIN (
    SELECT [N° pièce], [Code client], [DB_Id], SUM([Montant régler]) AS Total_Regle
    FROM [Imputation_Factures_Ventes]
    WHERE [Date règlement] <= @dateFin
    GROUP BY [N° pièce], [Code client], [DB_Id]
) ifv ON e.[N° pièce] = ifv.[N° pièce] AND e.[Code client] = ifv.[Code client] AND e.[DB_Id] = ifv.[DB_Id]
WHERE e.[Date document] BETWEEN @dateDebut AND @dateFin
  AND e.[Montant échéance] - ISNULL(ifv.Total_Regle, 0) > 0
  AND (@societe IS NULL OR e.[societe] = @societe)
""",
    },

    # ── Balance Âgée Synthèse (tranches) ──
    {
        "code": "DS_TB_BALANCE_AGEE_SYNTH",
        "nom": "TB Balance Âgée Synthèse",
        "description": "Répartition encours par tranche d'âge (format long : Tranche + Montant) — âge calculé à aujourd'hui",
        "query": """
WITH Encours AS (
    SELECT
        e.[Date d'échéance],
        e.[Montant échéance] - ISNULL(ifv.Total_Regle, 0) AS [Solde],
        DATEDIFF(DAY, e.[Date d'échéance], CAST(GETDATE() AS DATE)) AS [Age]
    FROM [Echéances_Ventes] e
    LEFT JOIN (
        SELECT [N° pièce], [Code client], [DB_Id], SUM([Montant régler]) AS Total_Regle
        FROM [Imputation_Factures_Ventes]
        WHERE [Date règlement] <= CAST(GETDATE() AS DATE)
        GROUP BY [N° pièce], [Code client], [DB_Id]
    ) ifv ON e.[N° pièce] = ifv.[N° pièce] AND e.[Code client] = ifv.[Code client] AND e.[DB_Id] = ifv.[DB_Id]
    WHERE e.[Date document] <= CAST(GETDATE() AS DATE)
      AND e.[Montant échéance] - ISNULL(ifv.Total_Regle, 0) > 0
      AND (@societe IS NULL OR e.[societe] = @societe)
)
SELECT [Tranche], ROUND(SUM([Solde]), 2) AS [Montant], [Ordre]
FROM (
    SELECT 'A Echoir'  AS [Tranche], [Solde], 0 AS [Ordre] FROM Encours WHERE [Age] < 0
    UNION ALL
    SELECT '0-30j',    [Solde], 1 FROM Encours WHERE [Age] BETWEEN 0  AND 30
    UNION ALL
    SELECT '31-60j',   [Solde], 2 FROM Encours WHERE [Age] BETWEEN 31 AND 60
    UNION ALL
    SELECT '61-90j',   [Solde], 3 FROM Encours WHERE [Age] BETWEEN 61 AND 90
    UNION ALL
    SELECT '91-120j',  [Solde], 4 FROM Encours WHERE [Age] BETWEEN 91 AND 120
    UNION ALL
    SELECT '+120j',    [Solde], 5 FROM Encours WHERE [Age] > 120
) t
GROUP BY [Tranche], [Ordre]
HAVING SUM([Solde]) > 0
ORDER BY [Ordre]
""",
    },

    # ── Top 10 Débiteurs ──
    {
        "code": "DS_TB_TOP_DEBITEURS",
        "nom": "TB Top 10 Débiteurs",
        "description": "Top 10 clients avec le plus gros encours",
        "query": """
SELECT TOP 10
    e.[Code client] AS [Code],
    e.[Intitulé client] AS [Client],
    SUM(e.[Montant échéance] - ISNULL(ifv.Total_Regle, 0)) AS [Encours],
    SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'échéance], @dateFin) > 0
        THEN e.[Montant échéance] - ISNULL(ifv.Total_Regle, 0) ELSE 0 END) AS [Echu],
    COUNT(*) AS [Nb Echeances]
FROM [Echéances_Ventes] e
LEFT JOIN (
    SELECT [N° pièce], [Code client], [DB_Id], SUM([Montant régler]) AS Total_Regle
    FROM [Imputation_Factures_Ventes]
    WHERE [Date règlement] <= @dateFin
    GROUP BY [N° pièce], [Code client], [DB_Id]
) ifv ON e.[N° pièce] = ifv.[N° pièce] AND e.[Code client] = ifv.[Code client] AND e.[DB_Id] = ifv.[DB_Id]
WHERE e.[Date document] <= @dateFin
  AND e.[Montant échéance] - ISNULL(ifv.Total_Regle, 0) > 0
  AND (@societe IS NULL OR e.[societe] = @societe)
GROUP BY e.[Code client], e.[Intitulé client]
ORDER BY [Encours] DESC
""",
    },

    # ── Synthèse Stock ──
    {
        "code": "DS_TB_SYNTHESE_STOCK",
        "nom": "TB Synthèse Stock",
        "description": "KPIs stock : valeur à @dateMax, nb articles, articles en rupture",
        "params": '[{"name": "dateFin", "type": "date", "source": "global", "required": true}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]',
        "query": """
WITH StockParArticle AS (
    SELECT
        [Code article],
        [societe],
        SUM(CASE WHEN [Sens de mouvement] LIKE N'%ntr%'
                 THEN ABS([Quantité]) ELSE -ABS([Quantité]) END) AS [Qte],
        SUM(CASE WHEN [Sens de mouvement] LIKE N'%ntr%'
                 THEN ABS([Montant Stock]) ELSE -ABS([Montant Stock]) END) AS [Valeur]
    FROM [Mouvement_stock]
    WHERE [Date Mouvement] <= @dateFin
      AND (@societe IS NULL OR [societe] = @societe)
    GROUP BY [Code article], [societe]
)
SELECT
    ISNULL(SUM(CASE WHEN [Qte] > 0 THEN [Valeur] ELSE 0 END), 0) AS [Valeur Stock Total],
    COUNT(DISTINCT CASE WHEN [Qte] > 0 THEN [Code article] END)   AS [Nb Articles en Stock],
    COUNT(DISTINCT CASE WHEN [Qte] <= 0 THEN [Code article] END)  AS [Articles en Rupture],
    COUNT(DISTINCT [Code article])                                  AS [Articles Disponibles]
FROM StockParArticle
""",
    },

    # ── Stock par Dépôt ──
    {
        "code": "DS_TB_STOCK_PAR_DEPOT",
        "nom": "TB Stock par Dépôt",
        "description": "Valeur stock par dépôt pour pie chart — calculée depuis mouvements jusqu'à @dateFin",
        "params": '[{"name": "dateFin", "type": "date", "source": "global", "required": true}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]',
        "query": """
WITH StockParDepotArticle AS (
    SELECT
        ISNULL([Dépôt], 'Non defini') AS [Depot],
        [Code article],
        SUM(CASE WHEN [Sens de mouvement] LIKE N'%ntr%'
                 THEN ABS([Quantité]) ELSE -ABS([Quantité]) END) AS [Qte],
        SUM(CASE WHEN [Sens de mouvement] LIKE N'%ntr%'
                 THEN ABS([Montant Stock]) ELSE -ABS([Montant Stock]) END) AS [Valeur]
    FROM [Mouvement_stock]
    WHERE [Date Mouvement] <= @dateFin
      AND (@societe IS NULL OR [societe] = @societe)
    GROUP BY ISNULL([Dépôt], 'Non defini'), [Code article]
)
SELECT
    [Depot],
    ISNULL(SUM(CASE WHEN [Qte] > 0 THEN [Valeur] ELSE 0 END), 0) AS [Valeur Stock],
    COUNT(DISTINCT CASE WHEN [Qte] > 0 THEN [Code article] END)   AS [Nb Articles],
    ISNULL(SUM(CASE WHEN [Qte] > 0 THEN [Qte] ELSE 0 END), 0)    AS [Qte en Stock]
FROM StockParDepotArticle
GROUP BY [Depot]
HAVING SUM(CASE WHEN [Qte] > 0 THEN [Valeur] ELSE 0 END) > 0
ORDER BY [Valeur Stock] DESC
""",
    },

    # ── Synthèse Achats ──
    {
        "code": "DS_TB_SYNTHESE_ACHATS",
        "nom": "TB Synthèse Achats",
        "description": "KPIs achats : montant, nb fournisseurs, nb documents",
        "query": """
SELECT
    ISNULL(SUM([Montant HT Net]), 0) AS [Achats HT],
    ISNULL(SUM([Montant TTC Net]), 0) AS [Achats TTC],
    COUNT(DISTINCT [Code fournisseur]) AS [Nb Fournisseurs],
    COUNT(DISTINCT [N° Pièce]) AS [Nb Documents],
    ISNULL(SUM([Quantité]), 0) AS [Qte Totale]
FROM [Lignes_des_achats]
WHERE [Date] BETWEEN @dateDebut AND @dateFin
  AND (@societe IS NULL OR [societe] = @societe)
""",
    },

    # ── Top 10 Fournisseurs (TB) ──
    {
        "code": "DS_TB_TOP_FOURNISSEURS",
        "nom": "TB Top 10 Fournisseurs",
        "description": "Top 10 fournisseurs par montant d'achats",
        "query": """
SELECT TOP 10
    [Code fournisseur] AS [Code],
    [Intitulé fournisseur] AS [Fournisseur],
    SUM([Montant HT Net]) AS [Achats HT],
    COUNT(DISTINCT [N° Pièce]) AS [Nb Documents],
    SUM([Quantité]) AS [Qte Achetee]
FROM [Lignes_des_achats]
WHERE [Date] BETWEEN @dateDebut AND @dateFin
  AND (@societe IS NULL OR [societe] = @societe)
GROUP BY [Code fournisseur], [Intitulé fournisseur]
ORDER BY [Achats HT] DESC
""",
    },

    # ── Evolution Achats Mensuel ──
    {
        "code": "DS_TB_ACHATS_MENSUEL",
        "nom": "TB Evolution Achats Mensuel",
        "description": "Achats par mois pour graphique",
        "query": """
SELECT
    FORMAT([Date], 'yyyy-MM') AS [Mois],
    DATENAME(MONTH, [Date]) + ' ' + CAST(YEAR([Date]) AS VARCHAR) AS [Periode],
    SUM([Montant HT Net]) AS [Achats HT],
    COUNT(DISTINCT [Code fournisseur]) AS [Nb Fournisseurs],
    COUNT(DISTINCT [N° Pièce]) AS [Nb Documents]
FROM [Lignes_des_achats]
WHERE [Date] BETWEEN @dateDebut AND @dateFin
  AND (@societe IS NULL OR [societe] = @societe)
GROUP BY FORMAT([Date], 'yyyy-MM'), DATENAME(MONTH, [Date]) + ' ' + CAST(YEAR([Date]) AS VARCHAR)
ORDER BY [Mois]
""",
    },

    # ── CA par Commercial (bar chart) ──
    {
        "code": "DS_TB_CA_COMMERCIAL",
        "nom": "TB CA par Commercial",
        "description": "CA et Marge par commercial pour bar chart",
        "query": """
SELECT
    ISNULL(e.[Nom représentant], 'Non affecté') AS [Commercial],
    SUM(l.[Montant HT Net]) AS [CA HT],
    SUM(l.[Montant HT Net] - ISNULL(l.[CMUP], 0) * l.[Quantité]) AS [Marge],
    COUNT(DISTINCT l.[Code client]) AS [Nb Clients]
FROM [Lignes_des_ventes] l
INNER JOIN [Entête_des_ventes] e ON l.[N° Pièce] = e.[N° pièce] AND l.[societe] = e.[societe]
WHERE l.[Valorise CA] = 'Oui'
  AND l.[Date BL] BETWEEN @dateDebut AND @dateFin
  AND (@societe IS NULL OR l.[societe] = @societe)
GROUP BY ISNULL(e.[Nom représentant], 'Non affecté')
ORDER BY [CA HT] DESC
""",
    },

    # ── Marge par Catalogue ──
    {
        "code": "DS_TB_MARGE_CATALOGUE",
        "nom": "TB Marge par Catalogue",
        "description": "Marge par catalogue pour analyse rentabilité",
        "query": """
SELECT TOP 15
    ISNULL([Catalogue 1], N'Non classé') AS [Catalogue],
    SUM([Montant HT Net]) AS [CA HT],
    SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) AS [Marge],
    CASE WHEN SUM([Montant HT Net]) > 0
        THEN ROUND(SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) * 100.0 / SUM([Montant HT Net]), 2)
        ELSE 0 END AS [Taux Marge]
FROM [Lignes_des_ventes]
WHERE [Valorise CA] = 'Oui'
  AND [Date BL] BETWEEN @dateDebut AND @dateFin
  AND (@societe IS NULL OR [societe] = @societe)
GROUP BY ISNULL([Catalogue 1], N'Non classé')
ORDER BY [CA HT] DESC
""",
    },

    # ── Dettes Fournisseurs Synthèse ──
    {
        "code": "DS_TB_SYNTHESE_DETTES",
        "nom": "TB Synthèse Dettes Fournisseurs",
        "description": "KPIs dettes fournisseurs : total dû, réglé, reste",
        "query": """
SELECT
    ISNULL(SUM([Montant échéance]), 0) AS [Total Du],
    ISNULL(SUM(CASE WHEN [Régler] = 'Oui' THEN [Montant échéance] ELSE 0 END), 0) AS [Total Regle],
    ISNULL(SUM(CASE WHEN [Régler] = 'Non' THEN [Montant échéance] ELSE 0 END), 0) AS [Reste a Payer],
    CASE WHEN SUM([Montant échéance]) > 0
        THEN ROUND(SUM(CASE WHEN [Régler] = 'Oui' THEN [Montant échéance] ELSE 0 END) * 100.0 / SUM([Montant échéance]), 2)
        ELSE 0 END AS [Taux Paiement %],
    COUNT(DISTINCT [Code fournisseur]) AS [Nb Fournisseurs],
    SUM(CASE WHEN [Régler] = 'Non'
             AND DATEDIFF(DAY, [Date d'échéance], GETDATE()) > 0 THEN 1 ELSE 0 END) AS [Nb Echues]
FROM [Echeances_Achats]
WHERE (@societe IS NULL OR [societe] = @societe)
""",
    },

    # ── Mouvements Stock Mensuel ──
    {
        "code": "DS_TB_MVT_STOCK_MENSUEL",
        "nom": "TB Mouvements Stock Mensuel",
        "description": "Entrées et sorties stock par mois",
        "query": """
SELECT
    FORMAT([Date Mouvement], 'yyyy-MM') AS [Mois],
    DATENAME(MONTH, [Date Mouvement]) + ' ' + CAST(YEAR([Date Mouvement]) AS VARCHAR) AS [Periode],
    SUM(CASE WHEN [Sens de mouvement] = N'Entrée' THEN ABS([Quantité]) ELSE 0 END) AS [Qte Entrees],
    SUM(CASE WHEN [Sens de mouvement] = N'Sortie' THEN ABS([Quantité]) ELSE 0 END) AS [Qte Sorties],
    SUM(CASE WHEN [Sens de mouvement] = N'Entrée' THEN ABS([Montant Stock]) ELSE 0 END) AS [Valeur Entrees],
    SUM(CASE WHEN [Sens de mouvement] = N'Sortie' THEN ABS([Montant Stock]) ELSE 0 END) AS [Valeur Sorties]
FROM [Mouvement_stock]
WHERE [Date Mouvement] BETWEEN @dateDebut AND @dateFin
  AND (@societe IS NULL OR [societe] = @societe)
GROUP BY FORMAT([Date Mouvement], 'yyyy-MM'), DATENAME(MONTH, [Date Mouvement]) + ' ' + CAST(YEAR([Date Mouvement]) AS VARCHAR)
ORDER BY [Mois]
""",
    },

    # ── Répartition CA par Région/Ville ──
    {
        "code": "DS_TB_CA_PAR_REGION",
        "nom": "TB CA par Région",
        "description": "Répartition CA par ville/région pour pie chart",
        "query": """
SELECT TOP 15
    ISNULL(c.[Ville], 'Non renseigné') AS [Ville],
    SUM(l.[Montant HT Net]) AS [CA HT],
    COUNT(DISTINCT l.[Code client]) AS [Nb Clients]
FROM [Lignes_des_ventes] l
LEFT JOIN [Clients] c ON l.[societe] = c.[societe] AND l.[Code client] = c.[Code client]
WHERE l.[Valorise CA] = 'Oui'
  AND l.[Date BL] BETWEEN @dateDebut AND @dateFin
  AND (@societe IS NULL OR l.[societe] = @societe)
GROUP BY ISNULL(c.[Ville], 'Non renseigné')
ORDER BY [CA HT] DESC
""",
    },

    # ── Comparatif CA N vs N-1 par Mois ──
    {
        "code": "DS_TB_CA_NvsN1_MOIS",
        "nom": "TB Comparatif CA N vs N-1 par Mois",
        "description": "CA, Marge, Clients, Documents mensuel N vs N-1",
        "query": """
SELECT
    MONTH([Date BL]) AS [Mois],
    DATENAME(MONTH, DATEFROMPARTS(2000, MONTH([Date BL]), 1)) AS [Mois Label],
    SUM(CASE WHEN YEAR([Date BL]) = YEAR(@dateFin)     THEN [Montant HT Net] ELSE 0 END) AS [CA Annee N],
    SUM(CASE WHEN YEAR([Date BL]) = YEAR(@dateFin) - 1 THEN [Montant HT Net] ELSE 0 END) AS [CA Annee N-1],
    ROUND(
        SUM(CASE WHEN YEAR([Date BL]) = YEAR(@dateFin)     THEN [Montant HT Net] ELSE 0 END)
      - SUM(CASE WHEN YEAR([Date BL]) = YEAR(@dateFin) - 1 THEN [Montant HT Net] ELSE 0 END), 2
    ) AS [Ecart CA],
    CASE WHEN SUM(CASE WHEN YEAR([Date BL]) = YEAR(@dateFin) - 1 THEN [Montant HT Net] ELSE 0 END) > 0
         THEN ROUND(
             (SUM(CASE WHEN YEAR([Date BL]) = YEAR(@dateFin) THEN [Montant HT Net] ELSE 0 END)
            - SUM(CASE WHEN YEAR([Date BL]) = YEAR(@dateFin) - 1 THEN [Montant HT Net] ELSE 0 END))
            * 100.0
            / SUM(CASE WHEN YEAR([Date BL]) = YEAR(@dateFin) - 1 THEN [Montant HT Net] ELSE 0 END), 2)
         ELSE NULL END AS [Evol CA %],
    SUM(CASE WHEN YEAR([Date BL]) = YEAR(@dateFin)
        THEN [Montant HT Net] - ISNULL([CMUP], 0) * [Quantité] ELSE 0 END) AS [Marge N],
    SUM(CASE WHEN YEAR([Date BL]) = YEAR(@dateFin) - 1
        THEN [Montant HT Net] - ISNULL([CMUP], 0) * [Quantité] ELSE 0 END) AS [Marge N-1],
    CASE WHEN SUM(CASE WHEN YEAR([Date BL]) = YEAR(@dateFin) THEN [Montant HT Net] ELSE 0 END) > 0
         THEN ROUND(
             SUM(CASE WHEN YEAR([Date BL]) = YEAR(@dateFin)
                 THEN [Montant HT Net] - ISNULL([CMUP], 0) * [Quantité] ELSE 0 END) * 100.0
           / SUM(CASE WHEN YEAR([Date BL]) = YEAR(@dateFin) THEN [Montant HT Net] ELSE 0 END), 2)
         ELSE 0 END AS [Marge % N],
    CASE WHEN SUM(CASE WHEN YEAR([Date BL]) = YEAR(@dateFin) - 1 THEN [Montant HT Net] ELSE 0 END) > 0
         THEN ROUND(
             SUM(CASE WHEN YEAR([Date BL]) = YEAR(@dateFin) - 1
                 THEN [Montant HT Net] - ISNULL([CMUP], 0) * [Quantité] ELSE 0 END) * 100.0
           / SUM(CASE WHEN YEAR([Date BL]) = YEAR(@dateFin) - 1 THEN [Montant HT Net] ELSE 0 END), 2)
         ELSE 0 END AS [Marge % N-1],
    COUNT(DISTINCT CASE WHEN YEAR([Date BL]) = YEAR(@dateFin)     THEN [Code client] END) AS [Nb Clients N],
    COUNT(DISTINCT CASE WHEN YEAR([Date BL]) = YEAR(@dateFin) - 1 THEN [Code client] END) AS [Nb Clients N-1],
    COUNT(DISTINCT CASE WHEN YEAR([Date BL]) = YEAR(@dateFin)     THEN [N° Pièce] END) AS [Nb Docs N],
    COUNT(DISTINCT CASE WHEN YEAR([Date BL]) = YEAR(@dateFin) - 1 THEN [N° Pièce] END) AS [Nb Docs N-1]
FROM [Lignes_des_ventes]
WHERE [Valorise CA] = 'Oui'
  AND YEAR([Date BL]) IN (YEAR(@dateFin), YEAR(@dateFin) - 1)
  AND MONTH([Date BL]) BETWEEN MONTH(@dateDebut) AND MONTH(@dateFin)
  AND (@societe IS NULL OR [societe] = @societe)
GROUP BY MONTH([Date BL]), DATENAME(MONTH, DATEFROMPARTS(2000, MONTH([Date BL]), 1))
ORDER BY [Mois]
""",
    },

    # ── Marge Mensuelle (pour combo chart) ──
    {
        "code": "DS_TB_MARGE_MENSUEL",
        "nom": "TB Marge Mensuelle",
        "description": "CA, Marge et Taux Marge par mois pour combo chart",
        "query": """
SELECT
    FORMAT([Date BL], 'yyyy-MM') AS [Mois],
    DATENAME(MONTH, [Date BL]) + ' ' + CAST(YEAR([Date BL]) AS VARCHAR) AS [Periode],
    SUM([Montant HT Net]) AS [CA HT],
    SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) AS [Marge],
    CASE WHEN SUM([Montant HT Net]) > 0
        THEN ROUND(SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) * 100.0 / SUM([Montant HT Net]), 2)
        ELSE 0 END AS [Taux Marge]
FROM [Lignes_des_ventes]
WHERE [Valorise CA] = 'Oui'
  AND [Date BL] BETWEEN @dateDebut AND @dateFin
  AND (@societe IS NULL OR [societe] = @societe)
GROUP BY FORMAT([Date BL], 'yyyy-MM'), DATENAME(MONTH, [Date BL]) + ' ' + CAST(YEAR([Date BL]) AS VARCHAR)
ORDER BY [Mois]
""",
    },

    # ── Encaissements Mensuels ──
    {
        "code": "DS_TB_ENCAISSEMENTS_MOIS",
        "nom": "TB Encaissements Mensuels",
        "description": "Encaissements réels vs échéances par mois (axe X = date échéance)",
        "query": """
SELECT
    FORMAT(e.[Date d'échéance], 'yyyy-MM') AS [Mois],
    DATENAME(MONTH, e.[Date d'échéance]) + ' ' + CAST(YEAR(e.[Date d'échéance]) AS VARCHAR) AS [Periode],
    SUM(e.[Montant échéance]) AS [Echeances],
    SUM(ISNULL(ifv.Total_Regle, 0)) AS [Encaisse],
    SUM(e.[Montant échéance] - ISNULL(ifv.Total_Regle, 0)) AS [Reste]
FROM [Echéances_Ventes] e
LEFT JOIN (
    SELECT [N° pièce], [Code client], [DB_Id], SUM([Montant régler]) AS Total_Regle
    FROM [Imputation_Factures_Ventes]
    WHERE [Date règlement] BETWEEN @dateDebut AND @dateFin
    GROUP BY [N° pièce], [Code client], [DB_Id]
) ifv ON e.[N° pièce] = ifv.[N° pièce]
      AND e.[Code client] = ifv.[Code client]
      AND e.[DB_Id] = ifv.[DB_Id]
WHERE e.[Date d'échéance] BETWEEN @dateDebut AND @dateFin
  AND (@societe IS NULL OR e.[societe] = @societe)
GROUP BY FORMAT(e.[Date d'échéance], 'yyyy-MM'),
         DATENAME(MONTH, e.[Date d'échéance]) + ' ' + CAST(YEAR(e.[Date d'échéance]) AS VARCHAR)
ORDER BY [Mois]
""",
    },

    # ── Répartition par Type Document ──
    {
        "code": "DS_TB_REPARTITION_TYPE_DOC",
        "nom": "TB Répartition par Type Document",
        "description": "Nb documents et montant par type (Facture, BL, BC, Devis, Avoir)",
        "query": """
SELECT
    [Type document] AS [Type],
    COUNT(DISTINCT [N° Pièce]) AS [Nb Documents],
    SUM([Montant HT Net]) AS [Montant HT],
    SUM([Quantité]) AS [Qte Totale]
FROM [Lignes_des_ventes]
WHERE [Date BL] BETWEEN @dateDebut AND @dateFin
  AND (@societe IS NULL OR [societe] = @societe)
  AND [Type document] IS NOT NULL
GROUP BY [Type document]
ORDER BY [Montant HT] DESC
""",
    },
]


# ─── Helper: widget avec format correct (x,y,w,h aplatis + dataSourceCode dans config)
def W(wid, wtype, title, ds_code, x, y, w, h, **cfg):
    return {"id": wid, "type": wtype, "title": title,
            "x": x, "y": y, "w": w, "h": h,
            "config": {"dataSourceCode": ds_code, "dataSourceOrigin": "template", **cfg}}


# ─── DASHBOARDS à créer (avec widgets) ──────────────────────────────
NEW_DASHBOARDS = [
    # ─── 1. SYNTHÈSE GLOBALE ───
    {
        "nom": "Synthèse Globale",
        "code": "DB_TB_SYNTHESE_GLOBALE",
        "menu_nom": "Synthèse Globale",
        "menu_icon": "Activity",
        "widgets": [
            W("k1", "kpi", "Chiffre d'Affaires HT", "DS_TB_SYNTHESE_VENTES", 0, 0, 2, 2, value_field="CA HT", aggregation="FIRST", suffix=" DH", kpi_color="#2563eb"),
            W("k2", "kpi", "Marge Brute", "DS_TB_SYNTHESE_VENTES", 2, 0, 2, 2, value_field="Marge", aggregation="FIRST", suffix=" DH", kpi_color="#16a34a"),
            W("k3", "kpi", "Taux Marge", "DS_TB_SYNTHESE_VENTES", 4, 0, 2, 2, value_field="Taux Marge %", aggregation="FIRST", suffix=" %", kpi_color="#9333ea"),
            W("k4", "kpi", "Clients Actifs", "DS_TB_SYNTHESE_VENTES", 6, 0, 2, 2, value_field="Nb Clients", aggregation="FIRST", kpi_color="#ea580c"),
            W("k5", "kpi", "Panier Moyen", "DS_TB_SYNTHESE_VENTES", 8, 0, 2, 2, value_field="Panier Moyen", aggregation="FIRST", suffix=" DH", kpi_color="#0891b2"),
            W("k6", "kpi", "Encours Clients", "DS_TB_SYNTHESE_RECOUVREMENT", 10, 0, 2, 2, value_field="Encours Total", aggregation="FIRST", suffix=" DH", kpi_color="#dc2626"),
            W("c1", "chart_combo", "Évolution CA & Marge Mensuel", "DS_TB_CA_MENSUEL", 0, 2, 8, 4,
              x_field="Periode", y_field="CA HT", y_field_2="Marge", y_label="CA HT", y_label_2="Marge",
              color="#2563eb", color_2="#16a34a", show_grid=True, show_legend=True),
            W("p1", "chart_pie", "CA par Catalogue", "DS_TB_CA_PAR_CATALOGUE", 8, 2, 4, 4,
              label_field="Catalogue", value_field="CA HT", donut=True, show_legend=True),
            W("t1", "table", "Top 10 Clients", "DS_TOP10_CLIENTS", 0, 6, 6, 4, max_rows=10),
            W("t2", "table", "Top 10 Articles", "DS_TOP10_ARTICLES", 6, 6, 6, 4, max_rows=10),
        ],
    },

    # ─── 2. PERFORMANCE COMMERCIALE ───
    {
        "nom": "Performance Commerciale",
        "code": "DB_TB_PERF_COMMERCIALE",
        "menu_nom": "Performance Commerciale",
        "menu_icon": "TrendingUp",
        "widgets": [
            W("k1", "kpi", "CA HT", "DS_TB_SYNTHESE_VENTES", 0, 0, 3, 2, value_field="CA HT", aggregation="FIRST", suffix=" DH", kpi_color="#2563eb"),
            W("k2", "kpi", "Nb Documents", "DS_TB_SYNTHESE_VENTES", 3, 0, 3, 2, value_field="Nb Documents", aggregation="FIRST", kpi_color="#ea580c"),
            W("k3", "kpi", "CA Moyen / Client", "DS_TB_SYNTHESE_VENTES", 6, 0, 3, 2, value_field="CA Moyen par Client", aggregation="FIRST", suffix=" DH", kpi_color="#0891b2"),
            W("k4", "kpi", "Qte Vendue", "DS_TB_SYNTHESE_VENTES", 9, 0, 3, 2, value_field="Qte Totale", aggregation="FIRST", kpi_color="#9333ea"),
            W("b1", "chart_bar", "CA par Commercial", "DS_TB_CA_COMMERCIAL", 0, 2, 6, 5,
              x_field="Commercial", y_field="CA HT", color="#2563eb", horizontal=True, show_labels=True),
            W("b2", "chart_stacked_bar", "CA & Marge par Commercial", "DS_TB_TOP_COMMERCIAUX", 6, 2, 6, 5,
              x_field="Commercial", y_field="CA HT", y_field_2="Marge", y_label="CA HT", y_label_2="Marge",
              color="#2563eb", color_2="#16a34a", stack_mode="grouped", show_legend=True),
            W("l1", "chart_line", "Comparatif CA N vs N-1 par Mois", "DS_TB_CA_NvsN1_MOIS", 0, 7, 8, 4,
              x_field="Mois Label", y_field="CA Annee N", y_field_2="CA Annee N-1",
              y_label="N", y_label_2="N-1",
              color="#2563eb", color_2="#94a3b8", show_grid=True, show_legend=True,
              drilldownDsCode="DS_CA_DETAIL_COMPLET", drilldownDsOrigin="template"),
            W("b1b", "chart_bar", "Évolution CA % par Mois (N/N-1)", "DS_TB_CA_NvsN1_MOIS", 8, 7, 4, 4,
              x_field="Mois Label", y_field="Evol CA %", y_label="Évol CA %",
              color="#10b981", show_grid=True, show_legend=False),
            W("l2", "chart_line", "Comparatif Marge N vs N-1 par Mois", "DS_TB_CA_NvsN1_MOIS", 0, 11, 8, 4,
              x_field="Mois Label", y_field="Marge N", y_field_2="Marge N-1",
              y_label="Marge N", y_label_2="Marge N-1",
              color="#f59e0b", color_2="#d1d5db", show_grid=True, show_legend=True),
            W("l3", "chart_line", "Taux de Marge % — N vs N-1", "DS_TB_CA_NvsN1_MOIS", 8, 11, 4, 4,
              x_field="Mois Label", y_field="Marge % N", y_field_2="Marge % N-1",
              y_label="Marge % N", y_label_2="Marge % N-1",
              color="#8b5cf6", color_2="#c4b5fd", show_grid=True, show_legend=True),
            W("l4", "chart_line", "Clients Actifs par Mois — N vs N-1", "DS_TB_CA_NvsN1_MOIS", 0, 15, 6, 4,
              x_field="Mois Label", y_field="Nb Clients N", y_field_2="Nb Clients N-1",
              y_label="Clients N", y_label_2="Clients N-1",
              color="#0ea5e9", color_2="#bae6fd", show_grid=True, show_legend=True),
            W("l5", "chart_line", "Nb Documents par Mois — N vs N-1", "DS_TB_CA_NvsN1_MOIS", 6, 15, 6, 4,
              x_field="Mois Label", y_field="Nb Docs N", y_field_2="Nb Docs N-1",
              y_label="Docs N", y_label_2="Docs N-1",
              color="#ef4444", color_2="#fca5a5", show_grid=True, show_legend=True),
        ],
    },

    # ─── 3. MARGE & RENTABILITÉ ───
    {
        "nom": "Analyse Marge & Rentabilité",
        "code": "DB_TB_MARGE_RENTABILITE",
        "menu_nom": "Marge & Rentabilité",
        "menu_icon": "PieChart",
        "widgets": [
            W("k1", "kpi", "Marge Totale", "DS_TB_SYNTHESE_VENTES", 0, 0, 4, 2, value_field="Marge", aggregation="FIRST", suffix=" DH", kpi_color="#16a34a"),
            W("k2", "kpi", "Taux Marge", "DS_TB_SYNTHESE_VENTES", 4, 0, 4, 2, value_field="Taux Marge %", aggregation="FIRST", suffix=" %", kpi_color="#9333ea"),
            W("k3", "kpi", "CA HT", "DS_TB_SYNTHESE_VENTES", 8, 0, 4, 2, value_field="CA HT", aggregation="FIRST", suffix=" DH", kpi_color="#2563eb"),
            W("c1", "chart_combo", "CA, Marge & Taux Marge Mensuel", "DS_TB_MARGE_MENSUEL", 0, 2, 8, 4,
              x_field="Periode", y_field="CA HT", y_field_2="Marge", y_field_3="Taux Marge",
              y_label="CA HT", y_label_2="Marge", y_label_3="Taux %",
              color="#2563eb", color_2="#16a34a", color_3="#f59e0b", show_grid=True, show_legend=True),
            W("p1", "chart_pie", "Marge par Catalogue", "DS_TB_MARGE_CATALOGUE", 8, 2, 4, 4,
              label_field="Catalogue", value_field="Marge", donut=True, show_legend=True),
            W("t1", "table", "Détail Marge par Catalogue", "DS_TB_MARGE_CATALOGUE", 0, 6, 12, 4),
        ],
    },

    # ─── 4. RECOUVREMENT ───
    {
        "nom": "TB Recouvrement",
        "code": "DB_TB_RECOUVREMENT",
        "menu_nom": "Recouvrement",
        "menu_icon": "Wallet",
        "widgets": [
            W("k1", "kpi", "Encours Total", "DS_TB_SYNTHESE_RECOUVREMENT", 0, 0, 3, 2, value_field="Encours Total", aggregation="FIRST", suffix=" DH", kpi_color="#dc2626"),
            W("k2", "kpi", "Taux Recouvrement", "DS_TB_SYNTHESE_RECOUVREMENT", 3, 0, 3, 2, value_field="Taux Recouvrement", aggregation="FIRST", suffix=" %", kpi_color="#16a34a"),
            W("k3", "kpi", "Créances +120j", "DS_TB_SYNTHESE_RECOUVREMENT", 6, 0, 3, 2, value_field="Creances Douteuses 120j", aggregation="FIRST", suffix=" DH", kpi_color="#991b1b"),
            W("k4", "kpi", "Clients Débiteurs", "DS_TB_SYNTHESE_RECOUVREMENT", 9, 0, 3, 2, value_field="Nb Clients Debiteurs", aggregation="FIRST", kpi_color="#ea580c"),
            W("c1", "chart_combo", "Encaissements Mensuels", "DS_TB_ENCAISSEMENTS_MOIS", 0, 2, 7, 4,
              x_field="Periode", y_field="Echeances", y_field_2="Encaisse",
              y_label="Echeances", y_label_2="Encaisse",
              color="#94a3b8", color_2="#16a34a", show_grid=True, show_legend=True),
            W("p1", "chart_pie", "Répartition Balance Âgée", "DS_TB_BALANCE_AGEE_SYNTH", 7, 2, 5, 4,
              label_field="Tranche", value_field="Montant", donut=True, show_legend=True),
            W("t1", "table", "Top 10 Débiteurs", "DS_TB_TOP_DEBITEURS", 0, 6, 12, 4, max_rows=10),
        ],
    },

    # ─── 5. STOCK ───
    {
        "nom": "TB Stock",
        "code": "DB_TB_STOCK",
        "menu_nom": "Stock",
        "menu_icon": "Package",
        "widgets": [
            W("k1", "kpi", "Valeur Stock", "DS_TB_SYNTHESE_STOCK", 0, 0, 3, 2, value_field="Valeur Stock Total", aggregation="FIRST", suffix=" DH", kpi_color="#2563eb"),
            W("k2", "kpi", "Articles en Stock", "DS_TB_SYNTHESE_STOCK", 3, 0, 3, 2, value_field="Nb Articles en Stock", aggregation="FIRST", kpi_color="#16a34a"),
            W("k3", "kpi", "En Rupture", "DS_TB_SYNTHESE_STOCK", 6, 0, 3, 2, value_field="Articles en Rupture", aggregation="FIRST", kpi_color="#dc2626"),
            W("k4", "kpi", "Sous Seuil Min.", "DS_TB_SYNTHESE_STOCK", 9, 0, 3, 2, value_field="Articles Sous Seuil", aggregation="FIRST", kpi_color="#f59e0b"),
            W("p1", "chart_pie", "Valeur Stock par Dépôt", "DS_TB_STOCK_PAR_DEPOT", 0, 2, 5, 4,
              label_field="Depot", value_field="Valeur Stock", donut=True, show_legend=True),
            W("c1", "chart_combo", "Mouvements Stock Mensuels", "DS_TB_MVT_STOCK_MENSUEL", 5, 2, 7, 4,
              x_field="Periode", y_field="Valeur Entrees", y_field_2="Valeur Sorties",
              y_label="Entrees", y_label_2="Sorties",
              color="#16a34a", color_2="#dc2626", show_grid=True, show_legend=True),
            W("t1", "table", "Stock par Dépôt", "DS_TB_STOCK_PAR_DEPOT", 0, 6, 12, 3),
        ],
    },

    # ─── 6. ACHATS ───
    {
        "nom": "TB Achats",
        "code": "DB_TB_ACHATS",
        "menu_nom": "Achats",
        "menu_icon": "ShoppingCart",
        "widgets": [
            W("k1", "kpi", "Achats HT", "DS_TB_SYNTHESE_ACHATS", 0, 0, 3, 2, value_field="Achats HT", aggregation="FIRST", suffix=" DH", kpi_color="#7c3aed"),
            W("k2", "kpi", "Nb Fournisseurs", "DS_TB_SYNTHESE_ACHATS", 3, 0, 3, 2, value_field="Nb Fournisseurs", aggregation="FIRST", kpi_color="#0891b2"),
            W("k3", "kpi", "Nb Documents", "DS_TB_SYNTHESE_ACHATS", 6, 0, 3, 2, value_field="Nb Documents", aggregation="FIRST", kpi_color="#ea580c"),
            W("k4", "kpi", "Reste à Payer", "DS_TB_SYNTHESE_DETTES", 9, 0, 3, 2, value_field="Reste a Payer", aggregation="FIRST", suffix=" DH", kpi_color="#dc2626"),
            W("c1", "chart_combo", "Évolution Achats Mensuel", "DS_TB_ACHATS_MENSUEL", 0, 2, 7, 4,
              x_field="Periode", y_field="Achats HT", y_field_2="Nb Documents",
              y_label="Achats HT", y_label_2="Nb Documents",
              color="#7c3aed", color_2="#f59e0b", show_grid=True, show_legend=True),
            W("b1", "chart_bar", "Top 10 Fournisseurs", "DS_TB_TOP_FOURNISSEURS", 7, 2, 5, 4,
              x_field="Fournisseur", y_field="Achats HT", color="#7c3aed", horizontal=True, show_labels=True),
            W("t1", "table", "Détail Top Fournisseurs", "DS_TB_TOP_FOURNISSEURS", 0, 6, 12, 4),
        ],
    },

    # ─── 7. ANALYSE CLIENTS ───
    {
        "nom": "Analyse Clients",
        "code": "DB_TB_ANALYSE_CLIENTS",
        "menu_nom": "Analyse Clients",
        "menu_icon": "Users",
        "widgets": [
            W("k1", "kpi", "Clients Actifs", "DS_TB_SYNTHESE_VENTES", 0, 0, 4, 2, value_field="Nb Clients", aggregation="FIRST", kpi_color="#2563eb"),
            W("k2", "kpi", "CA Moyen / Client", "DS_TB_SYNTHESE_VENTES", 4, 0, 4, 2, value_field="CA Moyen par Client", aggregation="FIRST", suffix=" DH", kpi_color="#16a34a"),
            W("k3", "kpi", "Panier Moyen", "DS_TB_SYNTHESE_VENTES", 8, 0, 4, 2, value_field="Panier Moyen", aggregation="FIRST", suffix=" DH", kpi_color="#0891b2"),
            W("p1", "chart_pie", "CA par Ville / Région", "DS_TB_CA_PAR_REGION", 0, 2, 5, 4,
              label_field="Ville", value_field="CA HT", donut=True, show_legend=True),
            W("b1", "chart_bar", "Top Familles Articles", "DS_TB_TOP_FAMILLES", 5, 2, 7, 4,
              x_field="Famille", y_field="CA HT", color="#2563eb", horizontal=True, show_labels=True),
            W("t1", "table", "Top 10 Clients", "DS_TOP10_CLIENTS", 0, 6, 6, 4, max_rows=10),
            W("p2", "chart_pie", "Par Type Document", "DS_TB_REPARTITION_TYPE_DOC", 6, 6, 6, 4,
              label_field="Type", value_field="Montant HT", donut=True, show_legend=True),
        ],
    },
]


def main():
    print("=" * 70)
    print("ENRICHISSEMENT TABLEAU DE BORD")
    print("=" * 70)

    # ─── Étape 1 : Créer les datasource templates ────────────────────
    print("\n--- DATASOURCES ---")
    with get_db_cursor() as cursor:
        for ds in NEW_DATASOURCES:
            cursor.execute("SELECT id FROM APP_DataSources_Templates WHERE code = ?", (ds["code"],))
            existing = cursor.fetchone()
            params_json = ds.get("params", '["dateDebut","dateFin","societe"]')
            if existing:
                cursor.execute("""
                    UPDATE APP_DataSources_Templates
                    SET nom = ?, description = ?, query_template = ?, parameters = ?, actif = 1
                    WHERE code = ?
                """, (ds["nom"], ds["description"], ds["query"].strip(), params_json, ds["code"]))
                print(f"  [MAJ] {ds['code']}")
            else:
                cursor.execute("""
                    INSERT INTO APP_DataSources_Templates (code, nom, description, query_template, type, actif, parameters)
                    VALUES (?, ?, ?, ?, 'query', 1, ?)
                """, (ds["code"], ds["nom"], ds["description"], ds["query"].strip(), params_json))
                print(f"  [NEW] {ds['code']}")

    # ─── Étape 2 : Créer les dashboards ──────────────────────────────
    print("\n--- DASHBOARDS ---")
    dashboard_ids = {}
    with get_db_cursor() as cursor:
        for db in NEW_DASHBOARDS:
            cursor.execute("SELECT id FROM APP_Dashboards WHERE code = ?", (db["code"],))
            existing = cursor.fetchone()

            widgets_json = json.dumps(db["widgets"], ensure_ascii=False)

            if existing:
                cursor.execute("""
                    UPDATE APP_Dashboards
                    SET nom = ?, widgets = ?, actif = 1
                    WHERE code = ?
                """, (db["nom"], widgets_json, db["code"]))
                dashboard_ids[db["code"]] = existing[0]
                print(f"  [MAJ] {db['code']} (id={existing[0]})")
            else:
                cursor.execute("""
                    INSERT INTO APP_Dashboards (nom, description, config, widgets, is_public, actif, code, sage_application, application)
                    VALUES (?, ?, '{}', ?, 1, 1, ?, 'commercial', 'reporting')
                """, (db["nom"], db["nom"], widgets_json, db["code"]))
                cursor.execute("SELECT @@IDENTITY")
                new_id = int(cursor.fetchone()[0])
                dashboard_ids[db["code"]] = new_id
                print(f"  [NEW] {db['code']} (id={new_id})")

    # ─── Étape 3 : Trouver le menu parent "Tableau de Bord" ─────────
    print("\n--- MENUS ---")
    with get_db_cursor() as cursor:
        cursor.execute("SELECT id FROM APP_Menus WHERE actif=1 AND nom LIKE '%Tableau de Bord%' AND parent_id IS NULL")
        parent = cursor.fetchone()
        if not parent:
            cursor.execute("SELECT id FROM APP_Menus WHERE actif=1 AND code='dashboard' AND parent_id IS NULL")
            parent = cursor.fetchone()

        if not parent:
            print("  [ERREUR] Menu parent 'Tableau de Bord' introuvable!")
            return

        parent_id = parent[0]
        print(f"  Parent: id={parent_id}")

        # Récupérer le max ordre existant
        cursor.execute("SELECT ISNULL(MAX(ordre), 0) FROM APP_Menus WHERE parent_id = ?", (parent_id,))
        max_ordre = cursor.fetchone()[0]

        ordre = max_ordre + 1
        for db in NEW_DASHBOARDS:
            db_id = dashboard_ids.get(db["code"])
            if not db_id:
                continue

            menu_code = f"tb-{db['code'].replace('DB_TB_', '').lower().replace('_', '-')}"

            cursor.execute("SELECT id FROM APP_Menus WHERE code = ? AND parent_id = ?", (menu_code, parent_id))
            existing = cursor.fetchone()

            if existing:
                cursor.execute("""
                    UPDATE APP_Menus SET nom = ?, icon = ?, target_id = ?, actif = 1 WHERE id = ?
                """, (db["menu_nom"], db["menu_icon"], db_id, existing[0]))
                print(f"  [MAJ] {db['menu_nom']} (menu id={existing[0]})")
            else:
                cursor.execute("""
                    INSERT INTO APP_Menus (nom, code, icon, parent_id, ordre, type, target_id, actif, roles)
                    VALUES (?, ?, ?, ?, ?, 'dashboard', ?, 1, '["admin","user","viewer"]')
                """, (db["menu_nom"], menu_code, db["menu_icon"], parent_id, ordre, db_id))
                print(f"  [NEW] {db['menu_nom']} (ordre={ordre})")
                ordre += 1

    print(f"\n{'=' * 70}")
    print(f"TERMINE: {len(NEW_DATASOURCES)} datasources, {len(NEW_DASHBOARDS)} dashboards, {len(NEW_DASHBOARDS)} menus")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
