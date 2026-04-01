"""SQL Query Templates for Reporting Commercial"""

# Chiffre d'Affaires Queries
CHIFFRE_AFFAIRES_GLOBAL = """
SELECT * FROM [GROUPE_ALBOUGHAZE].[dbo].[DashBoard_CA]
"""

CHIFFRE_AFFAIRES_PAR_PERIODE = """
SELECT
    YEAR([Date BL]) AS Annee,
    MONTH([Date BL]) AS Mois,
    SUM([Montant HT Net]) AS CA_HT,
    SUM([Montant TTC Net]) AS CA_TTC,
    SUM([Coût]) AS Cout_Total,
    COUNT(DISTINCT [Code client]) AS Nb_Clients,
    COUNT(*) AS Nb_Transactions
FROM [GROUPE_ALBOUGHAZE].[dbo].[DashBoard_CA]
WHERE [Date BL] BETWEEN ? AND ?
GROUP BY YEAR([Date BL]), MONTH([Date BL])
ORDER BY Annee, Mois
"""

CHIFFRE_AFFAIRES_PAR_GAMME = """
SELECT
    [Catalogue 1] AS Gamme,
    SUM([Montant HT Net]) AS CA_HT,
    SUM([Montant TTC Net]) AS CA_TTC,
    SUM([Coût]) AS Cout_Total,
    SUM([Montant HT Net]) - SUM([Coût]) AS Marge_Brute,
    CASE
        WHEN SUM([Montant HT Net]) > 0
        THEN (SUM([Montant HT Net]) - SUM([Coût])) / SUM([Montant HT Net]) * 100
        ELSE 0
    END AS Taux_Marge,
    COUNT(*) AS Nb_Ventes
FROM [GROUPE_ALBOUGHAZE].[dbo].[DashBoard_CA]
WHERE [Date BL] BETWEEN ? AND ?
GROUP BY [Catalogue 1]
ORDER BY CA_HT DESC
"""

CHIFFRE_AFFAIRES_PAR_CANAL = """
SELECT
    [Catégorie_] AS Canal,
    SUM([Montant HT Net]) AS CA_HT,
    SUM([Montant TTC Net]) AS CA_TTC,
    SUM([Coût]) AS Cout_Total,
    COUNT(DISTINCT [Code client]) AS Nb_Clients
FROM [GROUPE_ALBOUGHAZE].[dbo].[DashBoard_CA]
WHERE [Date BL] BETWEEN ? AND ?
GROUP BY [Catégorie_]
ORDER BY CA_HT DESC
"""

CHIFFRE_AFFAIRES_PAR_ZONE = """
SELECT
    [Souche] AS Zone,
    SUM([Montant HT Net]) AS CA_HT,
    SUM([Montant TTC Net]) AS CA_TTC,
    COUNT(DISTINCT [Code client]) AS Nb_Clients
FROM [GROUPE_ALBOUGHAZE].[dbo].[DashBoard_CA]
WHERE [Date BL] BETWEEN ? AND ?
GROUP BY [Souche]
ORDER BY CA_HT DESC
"""

CHIFFRE_AFFAIRES_PAR_COMMERCIAL = """
SELECT
    [Représentant] AS Commercial,
    SUM([Montant HT Net]) AS CA_HT,
    SUM([Montant TTC Net]) AS CA_TTC,
    SUM([Coût]) AS Cout_Total,
    SUM([Montant HT Net]) - SUM([Coût]) AS Marge_Brute,
    COUNT(DISTINCT [Code client]) AS Nb_Clients,
    COUNT(*) AS Nb_Ventes
FROM [GROUPE_ALBOUGHAZE].[dbo].[DashBoard_CA]
WHERE [Date BL] BETWEEN ? AND ?
GROUP BY [Représentant]
ORDER BY CA_HT DESC
"""

TOP_CLIENTS = """
SELECT TOP 10
    [Code client] AS Code_Client,
    [Intitulé client] AS Nom_Client,
    [Représentant] AS Commercial,
    SUM([Montant HT Net]) AS CA_HT,
    SUM([Montant TTC Net]) AS CA_TTC,
    COUNT(*) AS Nb_Transactions
FROM [GROUPE_ALBOUGHAZE].[dbo].[DashBoard_CA]
WHERE [Date BL] BETWEEN ? AND ?
GROUP BY [Code client], [Intitulé client], [Représentant]
ORDER BY CA_HT DESC
"""

TOP_PRODUITS = """
SELECT TOP 10
    [Code article] AS Code_Article,
    [Désignation] AS Designation,
    [Catalogue 1] AS Gamme,
    SUM([Quantité]) AS Quantite_Vendue,
    SUM([Montant HT Net]) AS CA_HT,
    SUM([Coût]) AS Cout_Total
FROM [GROUPE_ALBOUGHAZE].[dbo].[DashBoard_CA]
WHERE [Date BL] BETWEEN ? AND ?
GROUP BY [Code article], [Désignation], [Catalogue 1]
ORDER BY CA_HT DESC
"""

# Mouvements Stock Queries
MOUVEMENTS_STOCK = """
SELECT
    [DB],
    [Code article],
    [Désignation],
    [Type Mouvement],
    [Date Mouvement],
    [N° Pièce],
    [CMUP],
    [Prix unitaire],
    [Prix de revient],
    [Quantité],
    [Sens de mouvement],
    [Montant Stock],
    [Code coloboratore],
    [Représentant],
    [Catalogue 1],
    [Intitulé tiers],
    [Code tiers],
    [Intitulé client]
FROM [GROUPE_ALBOUGHAZE].[dbo].[Mouvement_stock]
"""

STOCK_PAR_ARTICLE = """
SELECT
    [Code article],
    [Désignation],
    [Catalogue 1] AS Gamme,
    SUM(CASE WHEN [Sens de mouvement] = 'E' THEN [Quantité] ELSE 0 END) AS Entrees,
    SUM(CASE WHEN [Sens de mouvement] = 'S' THEN [Quantité] ELSE 0 END) AS Sorties,
    SUM(CASE WHEN [Sens de mouvement] = 'E' THEN [Quantité] ELSE -[Quantité] END) AS Stock_Actuel,
    AVG([CMUP]) AS CMUP_Moyen,
    MAX([Date Mouvement]) AS Dernier_Mouvement
FROM [GROUPE_ALBOUGHAZE].[dbo].[Mouvement_stock]
GROUP BY [Code article], [Désignation], [Catalogue 1]
ORDER BY Stock_Actuel DESC
"""

STOCK_DORMANT = """
SELECT
    [Code article],
    [Désignation],
    [Catalogue 1] AS Gamme,
    MAX([Date Mouvement]) AS Dernier_Mouvement,
    DATEDIFF(DAY, MAX([Date Mouvement]), GETDATE()) AS Jours_Sans_Mouvement,
    SUM(CASE WHEN [Sens de mouvement] = 'E' THEN [Quantité] ELSE -[Quantité] END) AS Stock_Actuel,
    SUM(CASE WHEN [Sens de mouvement] = 'E' THEN [Quantité] ELSE -[Quantité] END) * AVG([CMUP]) AS Valeur_Stock
FROM [GROUPE_ALBOUGHAZE].[dbo].[Mouvement_stock]
GROUP BY [Code article], [Désignation], [Catalogue 1]
HAVING DATEDIFF(DAY, MAX([Date Mouvement]), GETDATE()) > 180
ORDER BY Valeur_Stock DESC
"""

ROTATION_STOCK = """
WITH StockData AS (
    SELECT
        [Catalogue 1] AS Gamme,
        SUM(CASE WHEN [Sens de mouvement] = 'S' THEN [Quantité] * [CMUP] ELSE 0 END) AS Sorties_Valeur,
        AVG(CASE WHEN [Sens de mouvement] = 'E' THEN [Quantité] * [CMUP] ELSE NULL END) AS Stock_Moyen_Valeur
    FROM [GROUPE_ALBOUGHAZE].[dbo].[Mouvement_stock]
    WHERE [Date Mouvement] BETWEEN ? AND ?
    GROUP BY [Catalogue 1]
)
SELECT
    Gamme,
    Sorties_Valeur,
    Stock_Moyen_Valeur,
    CASE
        WHEN Stock_Moyen_Valeur > 0
        THEN Sorties_Valeur / Stock_Moyen_Valeur
        ELSE 0
    END AS Rotation
FROM StockData
ORDER BY Rotation DESC
"""

MOUVEMENTS_PAR_ARTICLE = """
SELECT
    [Date Mouvement],
    [Type Mouvement],
    [N° Pièce],
    [Quantité],
    [Sens de mouvement],
    [CMUP],
    [Montant Stock],
    [Intitulé client],
    [Représentant]
FROM [GROUPE_ALBOUGHAZE].[dbo].[Mouvement_stock]
WHERE [Code article] = ?
ORDER BY [Date Mouvement] DESC
"""

# Balance Âgée Queries
BALANCE_AGEE = """
SELECT
    [CLIENTS ] AS CLIENTS,
    [Représenant] AS Representant,
    [SOCIETE],
    [Solde Clôture] AS Solde_Cloture,
    [Impayés] AS Impayes,
    [0-30],
    [31-60],
    [61-90],
    [91-120],
    [+120]
FROM [GROUPE_ALBOUGHAZE].[dbo].[BalanceAgee]
"""

BALANCE_AGEE_PAR_COMMERCIAL = """
SELECT
    [Représenant] AS Commercial,
    COUNT(DISTINCT [CLIENTS ]) AS Nb_Clients,
    SUM([Solde Clôture]) AS Encours_Total,
    SUM([0-30]) AS Tranche_0_30,
    SUM([31-60]) AS Tranche_31_60,
    SUM([61-90]) AS Tranche_61_90,
    SUM([91-120]) AS Tranche_91_120,
    SUM([+120]) AS Tranche_Plus_120,
    SUM([Impayés]) AS Total_Impayes
FROM [GROUPE_ALBOUGHAZE].[dbo].[BalanceAgee]
GROUP BY [Représenant]
ORDER BY Encours_Total DESC
"""

TOP_ENCOURS_CLIENTS = """
SELECT TOP 10
    [CLIENTS ] AS Client,
    [Représenant] AS Commercial,
    [SOCIETE] AS Societe,
    [Solde Clôture] AS Encours,
    [0-30] AS Tranche_0_30,
    [31-60] AS Tranche_31_60,
    [61-90] AS Tranche_61_90,
    [91-120] AS Tranche_91_120,
    [+120] AS Tranche_Plus_120,
    [Impayés] AS Impayes
FROM [GROUPE_ALBOUGHAZE].[dbo].[BalanceAgee]
ORDER BY [Solde Clôture] DESC
"""

CREANCES_DOUTEUSES = """
SELECT
    [CLIENTS ] AS Client,
    [Représenant] AS Commercial,
    [SOCIETE] AS Societe,
    [+120] AS Creances_Plus_120,
    [Impayés] AS Impayes,
    [Solde Clôture] AS Encours_Total
FROM [GROUPE_ALBOUGHAZE].[dbo].[BalanceAgee]
WHERE [+120] > 0 OR [Impayés] > 0
ORDER BY [+120] DESC
"""

# =====================================================
# ECHEANCES VENTES - Détail des échéances clients
# =====================================================

ECHEANCES_VENTES = """
SELECT
    [DB_Caption],
    [DB_Id],
    [Code tier payeur],
    [Code client],
    [Intitulé client],
    [Tier payeur],
    [Inititulé tier payeur],
    [Type Document],
    [N° pièce],
    [N° interne],
    [Date document],
    [Date d'échéance],
    [Montant échéance],
    [Montant échéance devise],
    [Montant TTC],
    [Montant TTC Net],
    [Régler],
    [Mode de réglement],
    [Code mode règlement],
    [Pourcentage],
    [Devise],
    [Cours de la devise],
    [Code collaborateur],
    [Nom collaborateur],
    [Prénom collaborateur],
    [Charge Recouvr],
    [Sens],
    [Mois],
    [Année],
    [Jours],
    [Semaine],
    [Libellé de l'échéance],
    [Type],
    [Etape en cours],
    [Dernière étape comptable]
FROM [Echéances_Ventes]
"""

ECHEANCES_VENTES_NON_REGLEES = """
SELECT
    [DB_Caption] AS Societe,
    [Code client],
    [Intitulé client],
    [Code tier payeur],
    [Inititulé tier payeur] AS Intitule_Tier_Payeur,
    [Type Document],
    [N° pièce] AS Num_Piece,
    [Date document],
    [Date d'échéance] AS Date_Echeance,
    [Montant échéance] AS Montant_Echeance,
    [Montant TTC],
    [Régler] AS Montant_Regle,
    [Montant échéance] - ISNULL([Régler], 0) AS Reste_A_Regler,
    [Mode de réglement] AS Mode_Reglement,
    [Code collaborateur],
    [Nom collaborateur] + ' ' + [Prénom collaborateur] AS Commercial,
    [Charge Recouvr] AS Charge_Recouvrement,
    DATEDIFF(DAY, [Date d'échéance], GETDATE()) AS Jours_Retard,
    CASE
        WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) <= 0 THEN 'A échoir'
        WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) <= 30 THEN '0-30 jours'
        WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) <= 60 THEN '31-60 jours'
        WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) <= 90 THEN '61-90 jours'
        WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) <= 120 THEN '91-120 jours'
        ELSE '+120 jours'
    END AS Tranche_Age
FROM [Echéances_Ventes]
WHERE [Montant échéance] > ISNULL([Régler], 0)
"""

ECHEANCES_PAR_CLIENT = """
SELECT
    [Code client],
    [Intitulé client],
    [DB_Caption] AS Societe,
    COUNT(*) AS Nb_Echeances,
    SUM([Montant échéance]) AS Total_Echeances,
    SUM(ISNULL([Régler], 0)) AS Total_Regle,
    SUM([Montant échéance] - ISNULL([Régler], 0)) AS Reste_A_Regler,
    SUM(CASE WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) <= 0 THEN [Montant échéance] - ISNULL([Régler], 0) ELSE 0 END) AS A_Echoir,
    SUM(CASE WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) BETWEEN 1 AND 30 THEN [Montant échéance] - ISNULL([Régler], 0) ELSE 0 END) AS Tranche_0_30,
    SUM(CASE WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) BETWEEN 31 AND 60 THEN [Montant échéance] - ISNULL([Régler], 0) ELSE 0 END) AS Tranche_31_60,
    SUM(CASE WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) BETWEEN 61 AND 90 THEN [Montant échéance] - ISNULL([Régler], 0) ELSE 0 END) AS Tranche_61_90,
    SUM(CASE WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) BETWEEN 91 AND 120 THEN [Montant échéance] - ISNULL([Régler], 0) ELSE 0 END) AS Tranche_91_120,
    SUM(CASE WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) > 120 THEN [Montant échéance] - ISNULL([Régler], 0) ELSE 0 END) AS Tranche_Plus_120,
    MAX([Date d'échéance]) AS Derniere_Echeance,
    MAX(DATEDIFF(DAY, [Date d'échéance], GETDATE())) AS Max_Jours_Retard
FROM [Echéances_Ventes]
WHERE [Montant échéance] > ISNULL([Régler], 0)
GROUP BY [Code client], [Intitulé client], [DB_Caption]
ORDER BY Reste_A_Regler DESC
"""

ECHEANCES_PAR_COMMERCIAL = """
SELECT
    [Code collaborateur],
    [Nom collaborateur] + ' ' + [Prénom collaborateur] AS Commercial,
    [Charge Recouvr] AS Charge_Recouvrement,
    COUNT(DISTINCT [Code client]) AS Nb_Clients,
    COUNT(*) AS Nb_Echeances,
    SUM([Montant échéance] - ISNULL([Régler], 0)) AS Encours_Total,
    SUM(CASE WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) <= 0 THEN [Montant échéance] - ISNULL([Régler], 0) ELSE 0 END) AS A_Echoir,
    SUM(CASE WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) BETWEEN 1 AND 30 THEN [Montant échéance] - ISNULL([Régler], 0) ELSE 0 END) AS Tranche_0_30,
    SUM(CASE WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) BETWEEN 31 AND 60 THEN [Montant échéance] - ISNULL([Régler], 0) ELSE 0 END) AS Tranche_31_60,
    SUM(CASE WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) BETWEEN 61 AND 90 THEN [Montant échéance] - ISNULL([Régler], 0) ELSE 0 END) AS Tranche_61_90,
    SUM(CASE WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) BETWEEN 91 AND 120 THEN [Montant échéance] - ISNULL([Régler], 0) ELSE 0 END) AS Tranche_91_120,
    SUM(CASE WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) > 120 THEN [Montant échéance] - ISNULL([Régler], 0) ELSE 0 END) AS Tranche_Plus_120
FROM [Echéances_Ventes]
WHERE [Montant échéance] > ISNULL([Régler], 0)
GROUP BY [Code collaborateur], [Nom collaborateur], [Prénom collaborateur], [Charge Recouvr]
ORDER BY Encours_Total DESC
"""

ECHEANCES_PAR_MODE_REGLEMENT = """
SELECT
    [Mode de réglement] AS Mode_Reglement,
    [Code mode règlement] AS Code_Mode,
    COUNT(*) AS Nb_Echeances,
    SUM([Montant échéance]) AS Total_Echeances,
    SUM([Montant échéance] - ISNULL([Régler], 0)) AS Reste_A_Regler,
    AVG(DATEDIFF(DAY, [Date d'échéance], GETDATE())) AS Retard_Moyen_Jours
FROM [Echéances_Ventes]
WHERE [Montant échéance] > ISNULL([Régler], 0)
GROUP BY [Mode de réglement], [Code mode règlement]
ORDER BY Reste_A_Regler DESC
"""

ECHEANCES_A_ECHOIR = """
SELECT
    [DB_Caption] AS Societe,
    [Code client],
    [Intitulé client],
    [N° pièce] AS Num_Piece,
    [Date document],
    [Date d'échéance] AS Date_Echeance,
    [Montant échéance] - ISNULL([Régler], 0) AS Montant_A_Regler,
    [Mode de réglement] AS Mode_Reglement,
    [Nom collaborateur] + ' ' + [Prénom collaborateur] AS Commercial,
    DATEDIFF(DAY, GETDATE(), [Date d'échéance]) AS Jours_Avant_Echeance,
    CASE
        WHEN DATEDIFF(DAY, GETDATE(), [Date d'échéance]) <= 7 THEN 'Cette semaine'
        WHEN DATEDIFF(DAY, GETDATE(), [Date d'échéance]) <= 15 THEN 'Sous 15 jours'
        WHEN DATEDIFF(DAY, GETDATE(), [Date d'échéance]) <= 30 THEN 'Sous 30 jours'
        ELSE 'Plus de 30 jours'
    END AS Urgence
FROM [Echéances_Ventes]
WHERE [Date d'échéance] >= GETDATE()
  AND [Montant échéance] > ISNULL([Régler], 0)
ORDER BY [Date d'échéance] ASC
"""

# =====================================================
# IMPUTATION FACTURES - Règlements et imputations
# =====================================================

IMPUTATIONS_FACTURES = """
SELECT
    [DB],
    [DB_Caption],
    [Référence],
    [Libellé],
    [id Réglement],
    [Date réglement],
    [Date d'échance] AS Date_Echeance,
    [Id écheance],
    [Type Document],
    [N° pièce] AS Num_Piece,
    [Montant facture TTC],
    [Montant régler] AS Montant_Regle,
    [Date document],
    [Mode de réglement] AS Mode_Reglement,
    [Code client],
    [Intitulé client],
    [Code tier payeur],
    [Intitulé tier payeur],
    [Montant réglement],
    [N° interne],
    [Valorise CA]
FROM [Imputation_Factures_Ventes]
"""

REGLEMENTS_PAR_PERIODE = """
SELECT
    YEAR([Date réglement]) AS Annee,
    MONTH([Date réglement]) AS Mois,
    COUNT(DISTINCT [id Réglement]) AS Nb_Reglements,
    SUM([Montant réglement]) AS Total_Reglements,
    COUNT(DISTINCT [Code client]) AS Nb_Clients,
    AVG(DATEDIFF(DAY, [Date document], [Date réglement])) AS Delai_Moyen_Reglement
FROM [Imputation_Factures_Ventes]
WHERE [Date réglement] BETWEEN ? AND ?
GROUP BY YEAR([Date réglement]), MONTH([Date réglement])
ORDER BY Annee, Mois
"""

REGLEMENTS_PAR_CLIENT = """
SELECT
    [Code client],
    [Intitulé client],
    [DB_Caption] AS Societe,
    COUNT(DISTINCT [id Réglement]) AS Nb_Reglements,
    SUM([Montant réglement]) AS Total_Regle,
    MIN([Date réglement]) AS Premier_Reglement,
    MAX([Date réglement]) AS Dernier_Reglement,
    AVG(DATEDIFF(DAY, [Date document], [Date réglement])) AS Delai_Moyen_Jours
FROM [Imputation_Factures_Ventes]
WHERE [Date réglement] IS NOT NULL
GROUP BY [Code client], [Intitulé client], [DB_Caption]
ORDER BY Total_Regle DESC
"""

REGLEMENTS_PAR_MODE = """
SELECT
    [Mode de réglement] AS Mode_Reglement,
    COUNT(DISTINCT [id Réglement]) AS Nb_Reglements,
    SUM([Montant réglement]) AS Total_Regle,
    COUNT(DISTINCT [Code client]) AS Nb_Clients,
    AVG(DATEDIFF(DAY, [Date document], [Date réglement])) AS Delai_Moyen_Jours
FROM [Imputation_Factures_Ventes]
WHERE [Date réglement] BETWEEN ? AND ?
GROUP BY [Mode de réglement]
ORDER BY Total_Regle DESC
"""

FACTURES_NON_REGLEES = """
SELECT
    [DB_Caption] AS Societe,
    [Code client],
    [Intitulé client],
    [Type Document],
    [N° pièce] AS Num_Piece,
    [Date document],
    [Montant facture TTC],
    ISNULL([Montant régler], 0) AS Montant_Regle,
    [Montant facture TTC] - ISNULL([Montant régler], 0) AS Reste_A_Regler,
    DATEDIFF(DAY, [Date document], GETDATE()) AS Age_Jours
FROM [Imputation_Factures_Ventes]
WHERE [Montant facture TTC] > ISNULL([Montant régler], 0)
GROUP BY [DB_Caption], [Code client], [Intitulé client], [Type Document],
         [N° pièce], [Date document], [Montant facture TTC], [Montant régler]
ORDER BY Reste_A_Regler DESC
"""

HISTORIQUE_REGLEMENTS_CLIENT = """
SELECT TOP 100
    [Date réglement],
    [N° pièce] AS Num_Piece,
    [Type Document],
    [Date document],
    [Montant facture TTC],
    [Montant réglement],
    [Mode de réglement] AS Mode_Reglement,
    DATEDIFF(DAY, [Date document], [Date réglement]) AS Delai_Reglement_Jours
FROM [GROUPE_ALBOUGHAZE].[dbo].[Echéances_Ventes]
WHERE [Intitulé client] = ?
  AND [Date réglement] IS NOT NULL
ORDER BY [Date réglement] DESC
"""

# =====================================================
# KPIs RECOUVREMENT ENRICHIS
# =====================================================

KPIS_RECOUVREMENT = """
SELECT
    -- Encours total
    (SELECT SUM([Montant échéance] - ISNULL([Régler], 0))
     FROM [Echéances_Ventes]
     WHERE [Montant échéance] > ISNULL([Régler], 0)) AS Encours_Total,

    -- Montant à échoir (non encore échu)
    (SELECT SUM([Montant échéance] - ISNULL([Régler], 0))
     FROM [Echéances_Ventes]
     WHERE [Date d'échéance] >= GETDATE()
       AND [Montant échéance] > ISNULL([Régler], 0)) AS A_Echoir,

    -- Montant échu (en retard)
    (SELECT SUM([Montant échéance] - ISNULL([Régler], 0))
     FROM [Echéances_Ventes]
     WHERE [Date d'échéance] < GETDATE()
       AND [Montant échéance] > ISNULL([Régler], 0)) AS Echu,

    -- Nombre d'échéances en retard
    (SELECT COUNT(*)
     FROM [Echéances_Ventes]
     WHERE [Date d'échéance] < GETDATE()
       AND [Montant échéance] > ISNULL([Régler], 0)) AS Nb_Echeances_Retard,

    -- Nombre de clients avec retard
    (SELECT COUNT(DISTINCT [Code client])
     FROM [Echéances_Ventes]
     WHERE [Date d'échéance] < GETDATE()
       AND [Montant échéance] > ISNULL([Régler], 0)) AS Nb_Clients_Retard,

    -- Règlements du mois en cours
    (SELECT ISNULL(SUM([Montant réglement]), 0)
     FROM [Imputation_Factures_Ventes]
     WHERE MONTH([Date réglement]) = MONTH(GETDATE())
       AND YEAR([Date réglement]) = YEAR(GETDATE())) AS Reglements_Mois,

    -- Retard moyen en jours
    (SELECT AVG(DATEDIFF(DAY, [Date d'échéance], GETDATE()))
     FROM [Echéances_Ventes]
     WHERE [Date d'échéance] < GETDATE()
       AND [Montant échéance] > ISNULL([Régler], 0)) AS Retard_Moyen_Jours
"""

EVOLUTION_RECOUVREMENT = """
SELECT
    YEAR([Date réglement]) AS Annee,
    MONTH([Date réglement]) AS Mois,
    SUM([Montant réglement]) AS Reglements,
    COUNT(DISTINCT [Code client]) AS Nb_Clients_Payants
FROM [Imputation_Factures_Ventes]
WHERE [Date réglement] BETWEEN ? AND ?
GROUP BY YEAR([Date réglement]), MONTH([Date réglement])
ORDER BY Annee, Mois
"""

# =====================================================
# FICHE CLIENT - Requêtes spécifiques à un client
# =====================================================

LISTE_CLIENTS_BALANCE = """
SELECT DISTINCT
    [CLIENTS ] AS Code_Client,
    [CLIENTS ] AS Nom_Client,
    [Représenant] AS Commercial,
    [SOCIETE] AS Societe,
    [Solde Clôture] AS Encours,
    [Impayés] AS Impayes
FROM [GROUPE_ALBOUGHAZE].[dbo].[BalanceAgee]
ORDER BY [CLIENTS ]
"""

CA_EVOLUTION_CLIENT = """
SELECT
    YEAR([Date BL]) AS Annee,
    MONTH([Date BL]) AS Mois,
    SUM([Montant HT Net]) AS CA_HT,
    SUM([Montant TTC Net]) AS CA_TTC,
    COUNT(*) AS Nb_Transactions
FROM [GROUPE_ALBOUGHAZE].[dbo].[DashBoard_CA]
WHERE [Intitulé client] = ?
  AND [Date BL] BETWEEN ? AND ?
GROUP BY YEAR([Date BL]), MONTH([Date BL])
ORDER BY Annee, Mois
"""

CA_TOTAL_CLIENT = """
SELECT
    [Code client] AS Code_Client,
    [Intitulé client] AS Nom_Client,
    [Représentant] AS Commercial,
    SUM([Montant HT Net]) AS CA_HT,
    SUM([Montant TTC Net]) AS CA_TTC,
    COUNT(*) AS Nb_Transactions,
    COUNT(DISTINCT [Code article]) AS Nb_Produits_Distincts
FROM [GROUPE_ALBOUGHAZE].[dbo].[DashBoard_CA]
WHERE [Intitulé client] = ?
  AND [Date BL] BETWEEN ? AND ?
GROUP BY [Code client], [Intitulé client], [Représentant]
"""

TOP_PRODUITS_CLIENT = """
SELECT TOP 10
    [Code article] AS Code_Article,
    [Désignation] AS Designation,
    [Catalogue 1] AS Gamme,
    SUM([Quantité]) AS Quantite_Vendue,
    SUM([Montant HT Net]) AS CA_HT,
    COUNT(*) AS Nb_Lignes
FROM [GROUPE_ALBOUGHAZE].[dbo].[DashBoard_CA]
WHERE [Intitulé client] = ?
  AND [Date BL] BETWEEN ? AND ?
GROUP BY [Code article], [Désignation], [Catalogue 1]
ORDER BY CA_HT DESC
"""

ECHEANCES_NON_REGLEES_CLIENT = """
SELECT
    [DB_Caption] AS Societe,
    [Type Document],
    [N° pièce] AS Num_Piece,
    [Date document],
    [Date d'échéance] AS Date_Echeance,
    [Montant échéance] AS Montant_Echeance,
    [Montant TTC],
    [Régler] AS Montant_Regle,
    [Montant échéance] - ISNULL([Régler], 0) AS Reste_A_Regler,
    [Mode de réglement] AS Mode_Reglement,
    DATEDIFF(DAY, [Date d'échéance], GETDATE()) AS Jours_Retard,
    CASE
        WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) <= 0 THEN 'A echoir'
        WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) <= 30 THEN '0-30 jours'
        WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) <= 60 THEN '31-60 jours'
        WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) <= 90 THEN '61-90 jours'
        WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) <= 120 THEN '91-120 jours'
        ELSE '+120 jours'
    END AS Tranche_Age
FROM [GROUPE_ALBOUGHAZE].[dbo].[Echéances_Ventes]
WHERE [Intitulé client] = ?
  AND [Montant échéance] > ISNULL([Régler], 0)
ORDER BY [Date d'échéance] ASC
"""

INFO_CLIENT = """
SELECT TOP 1
    [Code client],
    [Intitulé],
    [Représentant],
    [Risque client],
    [Encours de l'autorisation] AS Plafond_Autorisation,
    [Assurance],
    [Téléphone],
    [Email],
    [Adresse],
    [Ville],
    [ICE_] AS ICE,
    [RC_] AS RC,
    [Capital_] AS Capital,
    [Forme juridique_] AS Forme_Juridique,
    [Date de création] AS Date_Creation
FROM [GROUPE_ALBOUGHAZE].[dbo].[Clients]
WHERE [Intitulé] = ?
"""

DOCUMENTS_VENTES_CLIENT = """
SELECT
    [DB_Caption] AS Societe,
    [Type Document],
    [Souche],
    [N° pièce] AS Num_Piece,
    [Date],
    [Montant HT] AS Montant_HT,
    [Montant TTC],
    [Montant réglé] AS Montant_Regle,
    [Montant TTC] - ISNULL([Montant réglé], 0) AS Reste_A_Regler,
    [Statut],
    [Etat],
    [Code représentant] AS Code_Commercial,
    [Nom représentant] AS Commercial
FROM [GROUPE_ALBOUGHAZE].[dbo].[Entête_des_ventes]
WHERE [Intitulé client] = ?
  AND [Date] BETWEEN ? AND ?
ORDER BY [Date] DESC
"""

# =====================================================
# FICHE FOURNISSEUR — Queries
# =====================================================

LISTE_FOURNISSEURS = """
SELECT
    [DB] AS Societe,
    [Code fournisseur],
    [Intitulé fournisseur] AS Nom_Fournisseur,
    [Acheteur],
    SUM([Montant TTC Net]) AS Total_Achats,
    SUM([Total réglement]) AS Total_Regle,
    SUM([Solde]) AS Solde
FROM [GROUPE_ALBOUGHAZE].[dbo].[Situation_Fournisseurs]
GROUP BY [DB], [Code fournisseur], [Intitulé fournisseur], [Acheteur]
ORDER BY SUM([Solde]) DESC
"""

INFO_FOURNISSEUR = """
SELECT TOP 1
    [Code fournisseur],
    [Intitulé],
    [Acheteur],
    [Téléphone],
    [Télécopie] AS Fax,
    [Email],
    [Adresse],
    [Ville],
    [ICE_] AS ICE,
    [RC_] AS RC,
    [Capital_] AS Capital,
    [Forme juridique_] AS Forme_Juridique,
    [Risque fournisseur] AS Risque_Fournisseur,
    [Encours de l'autorisation] AS Plafond_Autorisation,
    [Assurance],
    [Date de création] AS Date_Creation
FROM [GROUPE_ALBOUGHAZE].[dbo].[Fournisseurs]
WHERE [Intitulé] = ?
"""

DOCUMENTS_ACHATS_FOURNISSEUR = """
SELECT
    [DB_Caption] AS Societe,
    [Type Document],
    [Souche],
    [N° Pièce] AS Num_Piece,
    [Date],
    [Montant HT] AS Montant_HT,
    [Montant TTC],
    [Montant réglé] AS Montant_Regle,
    [Montant TTC] - ISNULL([Montant réglé], 0) AS Reste_A_Regler,
    [Statut],
    [Etat],
    [Nom acheteur] AS Acheteur
FROM [GROUPE_ALBOUGHAZE].[dbo].[Entête_des_achats]
WHERE [Intitulé Fournisseur] = ?
  AND [Date] BETWEEN ? AND ?
ORDER BY [Date] DESC
"""

ECHEANCES_NON_REGLEES_FOURNISSEUR = """
SELECT
    [DB_Caption] AS Societe,
    [Type Document],
    [N° pièce] AS Num_Piece,
    [Date document],
    [Date d'échéance] AS Date_Echeance,
    [Montant échéance] AS Montant_Echeance,
    [Régler] AS Montant_Regle,
    [Montant échéance] - ISNULL([Régler], 0) AS Reste_A_Regler,
    [Mode de règlement] AS Mode_Reglement,
    DATEDIFF(DAY, [Date d'échéance], GETDATE()) AS Jours_Retard,
    CASE
        WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) <= 0 THEN 'A echoir'
        WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) <= 30 THEN '0-30 jours'
        WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) <= 60 THEN '31-60 jours'
        WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) <= 90 THEN '61-90 jours'
        WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) <= 120 THEN '91-120 jours'
        ELSE '+120 jours'
    END AS Tranche_Age
FROM [GROUPE_ALBOUGHAZE].[dbo].[Echeances_Achats]
WHERE [Intitulé fournisseur] = ?
  AND [Montant échéance] > ISNULL([Régler], 0)
ORDER BY [Date d'échéance] ASC
"""

HISTORIQUE_PAIEMENTS_FOURNISSEUR = """
SELECT TOP 100
    [Date] AS Date_Paiement,
    [N° pièce] AS Num_Piece,
    [Mode règlement] AS Mode_Reglement,
    [Montant] AS Montant_Paiement,
    [Date d'échéance] AS Date_Echeance
FROM [GROUPE_ALBOUGHAZE].[dbo].[Paiements_Fournisseurs]
WHERE [Intitulé] = ?
ORDER BY [Date] DESC
"""

ACHATS_EVOLUTION_FOURNISSEUR = """
SELECT
    YEAR([Date]) AS Annee,
    MONTH([Date]) AS Mois,
    SUM([Montant HT]) AS Montant_HT,
    SUM([Montant TTC]) AS Montant_TTC,
    COUNT(*) AS Nb_Documents
FROM [GROUPE_ALBOUGHAZE].[dbo].[Entête_des_achats]
WHERE [Intitulé Fournisseur] = ?
  AND [Date] BETWEEN ? AND ?
  AND [Type Document] IN ('Facture', 'Avoir fournisseur')
GROUP BY YEAR([Date]), MONTH([Date])
ORDER BY Annee, Mois
"""

ACHATS_TOTAL_FOURNISSEUR = """
SELECT
    SUM([Montant HT]) AS Total_HT,
    SUM([Montant TTC]) AS Total_TTC,
    COUNT(*) AS Nb_Documents,
    COUNT(DISTINCT [Type Document]) AS Nb_Types
FROM [GROUPE_ALBOUGHAZE].[dbo].[Entête_des_achats]
WHERE [Intitulé Fournisseur] = ?
  AND [Date] BETWEEN ? AND ?
"""

# DSO Calculation Query
DSO_GLOBAL = """
WITH CA_Data AS (
    SELECT SUM([Montant TTC Net]) AS CA_TTC
    FROM [GROUPE_ALBOUGHAZE].[dbo].[DashBoard_CA]
    WHERE [Date BL] BETWEEN ? AND ?
),
Encours_Data AS (
    SELECT SUM([Solde Clôture]) AS Encours_Total
    FROM [GROUPE_ALBOUGHAZE].[dbo].[BalanceAgee]
)
SELECT
    Encours_Total,
    CA_TTC,
    CASE
        WHEN CA_TTC > 0
        THEN (Encours_Total / CA_TTC) * 365
        ELSE 0
    END AS DSO
FROM CA_Data, Encours_Data
"""

# KPIs Dashboard
KPIS_DASHBOARD = """
SELECT
    (SELECT ISNULL(SUM([Montant HT Net]), 0) FROM [GROUPE_ALBOUGHAZE].[dbo].[DashBoard_CA]
     WHERE [Date BL] BETWEEN ? AND ?) AS CA_HT,
    (SELECT ISNULL(SUM([Montant HT Net]) - SUM([Coût]), 0) FROM [GROUPE_ALBOUGHAZE].[dbo].[DashBoard_CA]
     WHERE [Date BL] BETWEEN ? AND ?) AS Marge_Brute,
    (SELECT ISNULL(SUM([Solde Clôture]), 0) FROM [GROUPE_ALBOUGHAZE].[dbo].[BalanceAgee]) AS Encours_Clients,
    (SELECT ISNULL(SUM([+120]), 0) FROM [GROUPE_ALBOUGHAZE].[dbo].[BalanceAgee]) AS Creances_Douteuses,
    (SELECT COUNT(DISTINCT [Code client]) FROM [GROUPE_ALBOUGHAZE].[dbo].[DashBoard_CA]
     WHERE [Date BL] BETWEEN ? AND ?) AS Nb_Clients_Actifs
"""

# Comparatif N/N-1
COMPARATIF_ANNUEL = """
SELECT
    YEAR([Date BL]) AS Annee,
    SUM([Montant HT Net]) AS CA_HT,
    SUM([Montant TTC Net]) AS CA_TTC,
    SUM([Coût]) AS Cout_Total,
    SUM([Montant HT Net]) - SUM([Coût]) AS Marge_Brute,
    COUNT(DISTINCT [Code client]) AS Nb_Clients
FROM [GROUPE_ALBOUGHAZE].[dbo].[DashBoard_CA]
WHERE YEAR([Date BL]) IN (?, ?)
GROUP BY YEAR([Date BL])
ORDER BY Annee
"""

# Query metadata for admin interface
QUERIES_METADATA = {
    "chiffre_affaires_global": {
        "name": "Chiffre d'Affaires Global",
        "description": "Récupère toutes les données de chiffre d'affaires du groupe",
        "table": "DashBoard_CA",
        "category": "Ventes"
    },
    "chiffre_affaires_par_periode": {
        "name": "CA par Période",
        "description": "Analyse du chiffre d'affaires par mois/année",
        "table": "DashBoard_CA",
        "category": "Ventes"
    },
    "chiffre_affaires_par_gamme": {
        "name": "CA par Gamme de Produits",
        "description": "Répartition du CA par gamme (Catalogue 1)",
        "table": "DashBoard_CA",
        "category": "Ventes"
    },
    "mouvements_stock": {
        "name": "Mouvements de Stock",
        "description": "Tous les mouvements de stock (entrées/sorties)",
        "table": "Mouvement_stock",
        "category": "Stocks"
    },
    "stock_dormant": {
        "name": "Stock Dormant",
        "description": "Articles sans mouvement depuis plus de 180 jours",
        "table": "Mouvement_stock",
        "category": "Stocks"
    },
    "balance_agee": {
        "name": "Balance Âgée",
        "description": "Encours clients par tranche d'ancienneté",
        "table": "BalanceAgee",
        "category": "Recouvrement"
    },
    "dso_global": {
        "name": "DSO Global",
        "description": "Calcul du Days Sales Outstanding",
        "table": "Multiple",
        "category": "Recouvrement"
    },
    # Nouvelles sources de données - Échéances
    "echeances_ventes": {
        "name": "Échéances Ventes",
        "description": "Détail complet des échéances clients avec dates, montants et statuts",
        "table": "Echéances_Ventes",
        "category": "Recouvrement"
    },
    "echeances_non_reglees": {
        "name": "Échéances Non Réglées",
        "description": "Échéances en attente de règlement avec calcul du retard",
        "table": "Echéances_Ventes",
        "category": "Recouvrement"
    },
    "echeances_par_client": {
        "name": "Échéances par Client",
        "description": "Balance âgée dynamique calculée à partir des échéances réelles",
        "table": "Echéances_Ventes",
        "category": "Recouvrement"
    },
    "echeances_par_commercial": {
        "name": "Échéances par Commercial",
        "description": "Encours et retards par commercial/chargé de recouvrement",
        "table": "Echéances_Ventes",
        "category": "Recouvrement"
    },
    "echeances_par_mode_reglement": {
        "name": "Échéances par Mode Règlement",
        "description": "Répartition des échéances par mode de règlement",
        "table": "Echéances_Ventes",
        "category": "Recouvrement"
    },
    "echeances_a_echoir": {
        "name": "Échéances à Échoir",
        "description": "Échéances futures avec niveau d'urgence",
        "table": "Echéances_Ventes",
        "category": "Recouvrement"
    },
    # Nouvelles sources de données - Règlements
    "imputations_factures": {
        "name": "Imputations Factures",
        "description": "Détail des règlements et leur imputation sur les factures",
        "table": "Imputation_Factures_Ventes",
        "category": "Recouvrement"
    },
    "reglements_par_periode": {
        "name": "Règlements par Période",
        "description": "Évolution mensuelle des encaissements",
        "table": "Imputation_Factures_Ventes",
        "category": "Recouvrement"
    },
    "reglements_par_client": {
        "name": "Règlements par Client",
        "description": "Historique des règlements avec délai moyen de paiement",
        "table": "Imputation_Factures_Ventes",
        "category": "Recouvrement"
    },
    "reglements_par_mode": {
        "name": "Règlements par Mode",
        "description": "Répartition des encaissements par mode de règlement",
        "table": "Imputation_Factures_Ventes",
        "category": "Recouvrement"
    },
    "factures_non_reglees": {
        "name": "Factures Non Réglées",
        "description": "Liste des factures en attente de règlement complet",
        "table": "Imputation_Factures_Ventes",
        "category": "Recouvrement"
    },
    "historique_reglements_client": {
        "name": "Historique Règlements Client",
        "description": "Historique complet des paiements d'un client",
        "table": "Imputation_Factures_Ventes",
        "category": "Recouvrement"
    },
    "kpis_recouvrement": {
        "name": "KPIs Recouvrement",
        "description": "Indicateurs clés: encours, échu, à échoir, retard moyen",
        "table": "Multiple",
        "category": "Recouvrement"
    },
    "evolution_recouvrement": {
        "name": "Évolution Recouvrement",
        "description": "Suivi mensuel des encaissements",
        "table": "Imputation_Factures_Ventes",
        "category": "Recouvrement"
    }
}
