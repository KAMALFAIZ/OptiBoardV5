"""
Creation des 25 rapports du cycle STOCKS pour OptiBoard
Tables: Etat_Stock (15,689 lignes) + Mouvement_stock (1,764,745 lignes)
"""
import pyodbc, json

CONN_STR = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019;TrustServerCertificate=yes"

# ===============================================================
# PARAMETRES COMMUNS
# ===============================================================
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

SOC_FILTER = "(@societe IS NULL OR es.societe = @societe)"
SOC_FILTER_MV = "(@societe IS NULL OR mv.societe = @societe)"

# ===============================================================
# 25 DATASOURCE TEMPLATES
# ===============================================================
DS_TEMPLATES = [
    # --- 3.1 Mouvements et Situation (7 GRID) ---
    {
        "code": "DS_STK_MOUVEMENTS",
        "nom": "Mouvements de Stock",
        "query": f"""SELECT
    mv.[Date Mouvement] AS [Date], mv.[Type Mouvement] AS [Type Mouvement], mv.[Domaine mouvement] AS [Domaine],
    mv.[Sens de mouvement] AS [Sens], mv.[Code article] AS [Code article], mv.[Désignation] AS [Designation],
    mv.[Code famille] AS [Code famille], mv.[Intitulé famille] AS [Famille],
    mv.[Code Dépôt] AS [Code Depot], mv.[Dépôt] AS [Depot],
    mv.[Quantité] AS [Quantite], mv.CMUP AS [CMUP], mv.[Montant Stock] AS [Montant Stock],
    mv.[N° Pièce] AS [Num Piece], mv.[Code tiers] AS [Code tiers], mv.[Intitulé tiers] AS [Tiers],
    mv.[Prix unitaire] AS [Prix unitaire], mv.[Prix de revient] AS [Prix de revient], mv.[DPA-Période] AS [DPA Periode],
    mv.[DPA-Vente] AS [DPA Vente], mv.[Coût standard] AS [Cout standard], mv.[DPR-Vente] AS [DPR Vente],
    mv.[N° Série / Lot] AS [Num Serie Lot], mv.[Suivi Stock] AS [Suivi Stock], mv.[Gamme 1] AS [Gamme 1], mv.[Gamme 2] AS [Gamme 2],
    mv.[Date Péremption] AS [Date Peremption], mv.[Date Fabrication] AS [Date Fabrication],
    mv.[Catalogue 1] AS [Catalogue 1], mv.[Catalogue 2] AS [Catalogue 2], mv.[Catalogue 3] AS [Catalogue 3], mv.[Catalogue 4] AS [Catalogue 4],
    mv.societe AS [Societe]
FROM Mouvement_stock mv
WHERE mv.[Date Mouvement] BETWEEN @dateDebut AND @dateFin
  AND {SOC_FILTER_MV}
ORDER BY mv.[Date Mouvement] DESC""",
        "params": PARAMS_DATE_SOCIETE,
        "category": "stocks"
    },
    {
        "code": "DS_STK_ENTREES",
        "nom": "Entrées de Stock",
        "query": f"""SELECT
    mv.[Date Mouvement] AS [Date], mv.[Type Mouvement],
    mv.[Code article], mv.[Désignation] AS [Designation],
    mv.[Code famille], mv.[Intitulé famille] AS [Famille],
    mv.[Code Dépôt] AS [Code Depot], mv.[Dépôt] AS [Depot],
    mv.[Quantité] AS [Quantite], mv.CMUP, mv.[Montant Stock],
    mv.[N° Pièce] AS [Num Piece], mv.[Code tiers], mv.[Intitulé tiers] AS [Tiers],
    mv.societe AS [Societe]
FROM Mouvement_stock mv
WHERE mv.[Sens de mouvement] = N'Entrée'
  AND mv.[Date Mouvement] BETWEEN @dateDebut AND @dateFin
  AND {SOC_FILTER_MV}
ORDER BY mv.[Date Mouvement] DESC""",
        "params": PARAMS_DATE_SOCIETE,
        "category": "stocks"
    },
    {
        "code": "DS_STK_SORTIES",
        "nom": "Sorties de Stock",
        "query": f"""SELECT
    mv.[Date Mouvement] AS [Date], mv.[Type Mouvement],
    mv.[Code article], mv.[Désignation] AS [Designation],
    mv.[Code famille], mv.[Intitulé famille] AS [Famille],
    mv.[Code Dépôt] AS [Code Depot], mv.[Dépôt] AS [Depot],
    mv.[Quantité] AS [Quantite], mv.CMUP, mv.[Montant Stock],
    mv.[N° Pièce] AS [Num Piece], mv.[Code tiers], mv.[Intitulé tiers] AS [Tiers],
    mv.societe AS [Societe]
FROM Mouvement_stock mv
WHERE mv.[Sens de mouvement] = 'Sortie'
  AND mv.[Date Mouvement] BETWEEN @dateDebut AND @dateFin
  AND {SOC_FILTER_MV}
ORDER BY mv.[Date Mouvement] DESC""",
        "params": PARAMS_DATE_SOCIETE,
        "category": "stocks"
    },
    {
        "code": "DS_STK_ETAT_ACTUEL",
        "nom": "État du Stock Actuel",
        "query": f"""SELECT
    es.[Code article], es.[Désignation article] AS [Designation],
    es.[Code famille], es.[Intitule] AS [Famille],
    es.[Catalogue 1] AS [Catalogue], es.[Unité] AS [Unite],
    es.[Code dépôt], es.[DE_Intitule] AS [Depot],
    es.[Quantité en stock] AS [Qte Stock],
    es.[Valeur du stock (montant)] AS [Valeur Stock],
    es.[Quantité minimale] AS [Qte Min],
    es.[Quantité maximale] AS [Qte Max],
    es.[Quntitté réservée] AS [Qte Reservee],
    es.[Quantité commandée] AS [Qte Commandee],
    es.[Stock mouvementé] AS [Mouvemente],
    es.[Dépôt principale] AS [Depot Principal],
    es.societe AS [Societe]
FROM Etat_Stock es
WHERE {SOC_FILTER}
ORDER BY es.[Valeur du stock (montant)] DESC""",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "stocks"
    },
    {
        "code": "DS_STK_PAR_DEPOT",
        "nom": "Stock par Dépôt",
        "query": f"""SELECT
    es.[Code dépôt], es.[DE_Intitule] AS [Depot],
    COUNT(DISTINCT es.[Code article]) AS [Nb Articles],
    SUM(es.[Quantité en stock]) AS [Qte Totale],
    SUM(es.[Valeur du stock (montant)]) AS [Valeur Stock],
    SUM(CASE WHEN es.[Quantité en stock] <= 0 THEN 1 ELSE 0 END) AS [Articles Rupture],
    SUM(CASE WHEN es.[Quantité en stock] > es.[Quantité maximale] AND es.[Quantité maximale] > 0 THEN 1 ELSE 0 END) AS [Articles Surstock],
    es.societe AS [Societe]
FROM Etat_Stock es
WHERE {SOC_FILTER}
GROUP BY es.[Code dépôt], es.[DE_Intitule], es.societe
ORDER BY SUM(es.[Valeur du stock (montant)]) DESC""",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "stocks"
    },
    {
        "code": "DS_STK_RUPTURE",
        "nom": "Articles en Rupture",
        "query": f"""SELECT
    es.[Code article], es.[Désignation article] AS [Designation],
    es.[Code famille], es.[Intitule] AS [Famille],
    es.[Catalogue 1] AS [Catalogue],
    es.[Code dépôt], es.[DE_Intitule] AS [Depot],
    es.[Quantité en stock] AS [Qte Stock],
    es.[Quantité minimale] AS [Qte Min],
    es.[Quantité commandée] AS [Qte Commandee],
    es.[Stock mouvementé] AS [Mouvemente],
    es.societe AS [Societe]
FROM Etat_Stock es
WHERE es.[Quantité en stock] <= 0
  AND es.[Stock mouvementé] = 'Oui'
  AND {SOC_FILTER}
ORDER BY es.[Code famille], es.[Désignation article]""",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "stocks"
    },
    {
        "code": "DS_STK_SURSTOCK",
        "nom": "Articles en Surstock",
        "query": f"""SELECT
    es.[Code article], es.[Désignation article] AS [Designation],
    es.[Code famille], es.[Intitule] AS [Famille],
    es.[Catalogue 1] AS [Catalogue],
    es.[Code dépôt], es.[DE_Intitule] AS [Depot],
    es.[Quantité en stock] AS [Qte Stock],
    es.[Quantité maximale] AS [Qte Max],
    es.[Quantité en stock] - es.[Quantité maximale] AS [Excedent],
    es.[Valeur du stock (montant)] AS [Valeur Stock],
    es.societe AS [Societe]
FROM Etat_Stock es
WHERE es.[Quantité maximale] > 0
  AND es.[Quantité en stock] > es.[Quantité maximale]
  AND {SOC_FILTER}
ORDER BY es.[Quantité en stock] - es.[Quantité maximale] DESC""",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "stocks"
    },

    # --- 3.2 Analyses Stocks ---
    {
        "code": "DS_STK_VALORISATION",
        "nom": "Valorisation du Stock",
        "query": f"""SELECT
    es.[Code famille], es.[Intitule] AS [Famille],
    es.[Catalogue 1] AS [Catalogue],
    es.[Code dépôt], es.[DE_Intitule] AS [Depot],
    COUNT(DISTINCT es.[Code article]) AS [Nb Articles],
    SUM(es.[Quantité en stock]) AS [Qte Stock],
    SUM(es.[Valeur du stock (montant)]) AS [Valeur Stock],
    AVG(CASE WHEN es.[Quantité en stock] > 0 THEN es.[Valeur du stock (montant)] / es.[Quantité en stock] END) AS [CU Moyen],
    es.societe AS [Societe]
FROM Etat_Stock es
WHERE {SOC_FILTER}
GROUP BY es.[Code famille], es.[Intitule], es.[Catalogue 1], es.[Code dépôt], es.[DE_Intitule], es.societe
ORDER BY SUM(es.[Valeur du stock (montant)]) DESC""",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "stocks"
    },
    {
        "code": "DS_STK_ROTATION",
        "nom": "Rotation des Stocks",
        "query": f"""SELECT
    es.[Code article], es.[Désignation article] AS [Designation],
    es.[Code famille], es.[Intitule] AS [Famille],
    es.[Quantité en stock] AS [Qte Stock],
    es.[Valeur du stock (montant)] AS [Valeur Stock],
    ISNULL(sortie.qte_sortie, 0) AS [Qte Sortie Periode],
    CASE WHEN ISNULL(sortie.qte_sortie, 0) > 0 AND es.[Quantité en stock] > 0
         THEN ROUND(ISNULL(sortie.qte_sortie, 0) / es.[Quantité en stock], 2)
         ELSE 0 END AS [Taux Rotation],
    CASE WHEN ISNULL(sortie.qte_sortie, 0) > 0
         THEN ROUND(es.[Quantité en stock] / (ISNULL(sortie.qte_sortie, 0) / 365.0), 0)
         ELSE 999 END AS [Jours Couverture],
    es.societe AS [Societe]
FROM Etat_Stock es
LEFT JOIN (
    SELECT mv.[Code article], mv.societe, SUM(mv.[Quantité]) AS qte_sortie
    FROM Mouvement_stock mv
    WHERE mv.[Sens de mouvement] = 'Sortie'
      AND mv.[Date Mouvement] BETWEEN @dateDebut AND @dateFin
    GROUP BY mv.[Code article], mv.societe
) sortie ON es.[Code article] = sortie.[Code article] AND es.societe = sortie.societe
WHERE es.[Quantité en stock] > 0
  AND {SOC_FILTER}
ORDER BY CASE WHEN ISNULL(sortie.qte_sortie, 0) > 0 AND es.[Quantité en stock] > 0
         THEN ISNULL(sortie.qte_sortie, 0) / es.[Quantité en stock]
         ELSE 0 END""",
        "params": PARAMS_DATE_SOCIETE,
        "category": "stocks"
    },
    {
        "code": "DS_STK_EVOLUTION_MENSUELLE",
        "nom": "Évolution Stock Mensuelle",
        "query": f"""SELECT
    YEAR(mv.[Date Mouvement]) AS [Annee],
    MONTH(mv.[Date Mouvement]) AS [Mois],
    CAST(YEAR(mv.[Date Mouvement]) AS VARCHAR) + '-' + RIGHT('0' + CAST(MONTH(mv.[Date Mouvement]) AS VARCHAR), 2) AS [Periode],
    SUM(CASE WHEN mv.[Sens de mouvement] = N'Entrée' THEN mv.[Quantité] ELSE 0 END) AS [Entrees Qte],
    SUM(CASE WHEN mv.[Sens de mouvement] = 'Sortie' THEN mv.[Quantité] ELSE 0 END) AS [Sorties Qte],
    SUM(CASE WHEN mv.[Sens de mouvement] = N'Entrée' THEN mv.[Montant Stock] ELSE 0 END) AS [Entrees Valeur],
    SUM(CASE WHEN mv.[Sens de mouvement] = 'Sortie' THEN mv.[Montant Stock] ELSE 0 END) AS [Sorties Valeur],
    COUNT(DISTINCT mv.[Code article]) AS [Nb Articles],
    mv.societe AS [Societe]
FROM Mouvement_stock mv
WHERE mv.[Date Mouvement] BETWEEN @dateDebut AND @dateFin
  AND {SOC_FILTER_MV}
GROUP BY YEAR(mv.[Date Mouvement]), MONTH(mv.[Date Mouvement]), mv.societe
ORDER BY YEAR(mv.[Date Mouvement]), MONTH(mv.[Date Mouvement])""",
        "params": PARAMS_DATE_SOCIETE,
        "category": "stocks"
    },
    {
        "code": "DS_STK_DORMANT",
        "nom": "Stock Dormant",
        "query": f"""SELECT
    es.[Code article], es.[Désignation article] AS [Designation],
    es.[Code famille], es.[Intitule] AS [Famille],
    es.[Catalogue 1] AS [Catalogue],
    es.[Code dépôt], es.[DE_Intitule] AS [Depot],
    es.[Quantité en stock] AS [Qte Stock],
    es.[Valeur du stock (montant)] AS [Valeur Stock],
    es.societe AS [Societe]
FROM Etat_Stock es
WHERE es.[Quantité en stock] > 0
  AND es.[Stock mouvementé] = 'Non'
  AND {SOC_FILTER}
ORDER BY es.[Valeur du stock (montant)] DESC""",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "stocks"
    },
    {
        "code": "DS_STK_ABC",
        "nom": "Analyse ABC Stock",
        "query": f"""SELECT
    es.[Code article], es.[Désignation article] AS [Designation],
    es.[Code famille], es.[Intitule] AS [Famille],
    es.[Quantité en stock] AS [Qte Stock],
    es.[Valeur du stock (montant)] AS [Valeur Stock],
    SUM(es.[Valeur du stock (montant)]) OVER (ORDER BY es.[Valeur du stock (montant)] DESC) AS [Cumul Valeur],
    ROUND(100.0 * SUM(es.[Valeur du stock (montant)]) OVER (ORDER BY es.[Valeur du stock (montant)] DESC)
        / NULLIF(SUM(es.[Valeur du stock (montant)]) OVER (), 0), 2) AS [Cumul %],
    CASE
        WHEN 100.0 * SUM(es.[Valeur du stock (montant)]) OVER (ORDER BY es.[Valeur du stock (montant)] DESC)
            / NULLIF(SUM(es.[Valeur du stock (montant)]) OVER (), 0) <= 80 THEN 'A'
        WHEN 100.0 * SUM(es.[Valeur du stock (montant)]) OVER (ORDER BY es.[Valeur du stock (montant)] DESC)
            / NULLIF(SUM(es.[Valeur du stock (montant)]) OVER (), 0) <= 95 THEN 'B'
        ELSE 'C'
    END AS [Classe ABC],
    es.societe AS [Societe]
FROM Etat_Stock es
WHERE es.[Quantité en stock] > 0
  AND {SOC_FILTER}
ORDER BY es.[Valeur du stock (montant)] DESC""",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "stocks"
    },
    {
        "code": "DS_STK_COUVERTURE",
        "nom": "Couverture de Stock",
        "query": f"""SELECT
    es.[Code famille], es.[Intitule] AS [Famille],
    COUNT(DISTINCT es.[Code article]) AS [Nb Articles],
    SUM(es.[Quantité en stock]) AS [Qte Stock],
    SUM(es.[Valeur du stock (montant)]) AS [Valeur Stock],
    ISNULL(SUM(sortie.qte_mois), 0) AS [Consommation Mensuelle],
    CASE WHEN ISNULL(SUM(sortie.qte_mois), 0) > 0
         THEN ROUND(SUM(es.[Quantité en stock]) / SUM(sortie.qte_mois), 1)
         ELSE 999 END AS [Mois Couverture],
    es.societe AS [Societe]
FROM Etat_Stock es
LEFT JOIN (
    SELECT mv.[Code famille], mv.societe, SUM(mv.[Quantité]) / NULLIF(DATEDIFF(month, @dateDebut, @dateFin) + 1, 0) AS qte_mois
    FROM Mouvement_stock mv
    WHERE mv.[Sens de mouvement] = 'Sortie'
      AND mv.[Date Mouvement] BETWEEN @dateDebut AND @dateFin
    GROUP BY mv.[Code famille], mv.societe
) sortie ON es.[Code famille] = sortie.[Code famille] AND es.societe = sortie.societe
WHERE es.[Quantité en stock] > 0
  AND {SOC_FILTER}
GROUP BY es.[Code famille], es.[Intitule], es.societe
ORDER BY CASE WHEN ISNULL(SUM(sortie.qte_mois), 0) > 0
         THEN SUM(es.[Quantité en stock]) / SUM(sortie.qte_mois)
         ELSE 999 END""",
        "params": PARAMS_DATE_SOCIETE,
        "category": "stocks"
    },
    {
        "code": "DS_STK_INVENTAIRE_COMPARATIF",
        "nom": "Inventaire Comparatif",
        "query": f"""SELECT
    es.[Code dépôt], es.[DE_Intitule] AS [Depot],
    es.[Code famille], es.[Intitule] AS [Famille],
    COUNT(DISTINCT es.[Code article]) AS [Nb References],
    SUM(es.[Quantité en stock]) AS [Qte Stock],
    SUM(es.[Valeur du stock (montant)]) AS [Valeur Stock],
    SUM(CASE WHEN es.[Quantité en stock] > 0 THEN 1 ELSE 0 END) AS [Ref En Stock],
    SUM(CASE WHEN es.[Quantité en stock] <= 0 THEN 1 ELSE 0 END) AS [Ref Rupture],
    ROUND(100.0 * SUM(CASE WHEN es.[Quantité en stock] > 0 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1) AS [Taux Dispo %],
    es.societe AS [Societe]
FROM Etat_Stock es
WHERE {SOC_FILTER}
GROUP BY es.[Code dépôt], es.[DE_Intitule], es.[Code famille], es.[Intitule], es.societe
ORDER BY es.[Code dépôt], SUM(es.[Valeur du stock (montant)]) DESC""",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "stocks"
    },
    {
        "code": "DS_STK_TRANSFERTS",
        "nom": "Transferts Inter-Dépôts",
        "query": f"""SELECT
    mv.[Date Mouvement] AS [Date],
    mv.[Code Dépôt] AS [Code Depot], mv.[Dépôt] AS [Depot],
    mv.[Code article], mv.[Désignation] AS [Designation],
    mv.[Code famille], mv.[Intitulé famille] AS [Famille],
    mv.[Sens de mouvement] AS [Sens],
    mv.[Quantité] AS [Quantite], mv.[Montant Stock],
    mv.[N° Pièce] AS [Num Piece],
    mv.societe AS [Societe]
FROM Mouvement_stock mv
WHERE mv.[Type Mouvement] = N'Virement de dépôt à dépôt'
  AND mv.[Date Mouvement] BETWEEN @dateDebut AND @dateFin
  AND {SOC_FILTER_MV}
ORDER BY mv.[Date Mouvement] DESC""",
        "params": PARAMS_DATE_SOCIETE,
        "category": "stocks"
    },

    # --- 3.3 Rapports Avancés ---
    {
        "code": "DS_STK_ABC_XYZ",
        "nom": "Classification ABC/XYZ",
        "query": f"""SELECT
    es.[Code article], es.[Désignation article] AS [Designation],
    es.[Code famille], es.[Intitule] AS [Famille],
    es.[Quantité en stock] AS [Qte Stock],
    es.[Valeur du stock (montant)] AS [Valeur Stock],
    CASE
        WHEN 100.0 * SUM(es.[Valeur du stock (montant)]) OVER (ORDER BY es.[Valeur du stock (montant)] DESC)
            / NULLIF(SUM(es.[Valeur du stock (montant)]) OVER (), 0) <= 80 THEN 'A'
        WHEN 100.0 * SUM(es.[Valeur du stock (montant)]) OVER (ORDER BY es.[Valeur du stock (montant)] DESC)
            / NULLIF(SUM(es.[Valeur du stock (montant)]) OVER (), 0) <= 95 THEN 'B'
        ELSE 'C'
    END AS [Classe ABC],
    CASE WHEN es.[Stock mouvementé] = 'Oui' THEN 'X-Regulier' ELSE 'Z-Dormant' END AS [Classe XYZ],
    es.societe AS [Societe]
FROM Etat_Stock es
WHERE es.[Quantité en stock] > 0
  AND {SOC_FILTER}
ORDER BY es.[Valeur du stock (montant)] DESC""",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "stocks"
    },
    {
        "code": "DS_STK_PREVISION_RUPTURE",
        "nom": "Prévision de Rupture",
        "query": f"""SELECT
    es.[Code article], es.[Désignation article] AS [Designation],
    es.[Code famille], es.[Intitule] AS [Famille],
    es.[Code dépôt], es.[DE_Intitule] AS [Depot],
    es.[Quantité en stock] AS [Qte Stock],
    es.[Quantité minimale] AS [Seuil Min],
    ISNULL(sortie.qte_jour, 0) AS [Conso Journaliere],
    CASE WHEN ISNULL(sortie.qte_jour, 0) > 0
         THEN ROUND(es.[Quantité en stock] / sortie.qte_jour, 0)
         ELSE 999 END AS [Jours Restants],
    CASE WHEN ISNULL(sortie.qte_jour, 0) > 0 AND es.[Quantité en stock] / sortie.qte_jour <= 7 THEN 'CRITIQUE'
         WHEN ISNULL(sortie.qte_jour, 0) > 0 AND es.[Quantité en stock] / sortie.qte_jour <= 30 THEN 'ALERTE'
         ELSE 'OK' END AS [Statut],
    es.societe AS [Societe]
FROM Etat_Stock es
LEFT JOIN (
    SELECT mv.[Code article], mv.societe,
        SUM(mv.[Quantité]) / NULLIF(DATEDIFF(day, @dateDebut, @dateFin) + 1, 0) AS qte_jour
    FROM Mouvement_stock mv
    WHERE mv.[Sens de mouvement] = 'Sortie'
      AND mv.[Date Mouvement] BETWEEN @dateDebut AND @dateFin
    GROUP BY mv.[Code article], mv.societe
) sortie ON es.[Code article] = sortie.[Code article] AND es.societe = sortie.societe
WHERE es.[Quantité en stock] > 0
  AND {SOC_FILTER}
ORDER BY CASE WHEN ISNULL(sortie.qte_jour, 0) > 0
         THEN es.[Quantité en stock] / sortie.qte_jour ELSE 999 END""",
        "params": PARAMS_DATE_SOCIETE,
        "category": "stocks"
    },
    {
        "code": "DS_STK_COUT_POSSESSION",
        "nom": "Coût de Possession du Stock",
        "query": f"""SELECT
    es.[Code famille], es.[Intitule] AS [Famille],
    es.[Catalogue 1] AS [Catalogue],
    COUNT(DISTINCT es.[Code article]) AS [Nb Articles],
    SUM(es.[Quantité en stock]) AS [Qte Stock],
    SUM(es.[Valeur du stock (montant)]) AS [Valeur Stock],
    ROUND(SUM(es.[Valeur du stock (montant)]) * 0.15, 2) AS [Cout Possession Annuel],
    ROUND(100.0 * SUM(es.[Valeur du stock (montant)]) / NULLIF(SUM(SUM(es.[Valeur du stock (montant)])) OVER (), 0), 2) AS [Part Valeur %],
    es.societe AS [Societe]
FROM Etat_Stock es
WHERE es.[Quantité en stock] > 0
  AND {SOC_FILTER}
GROUP BY es.[Code famille], es.[Intitule], es.[Catalogue 1], es.societe
ORDER BY SUM(es.[Valeur du stock (montant)]) DESC""",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "stocks"
    },
    {
        "code": "DS_STK_OBSOLESCENCE",
        "nom": "Taux de Péremption / Obsolescence",
        "query": f"""SELECT
    es.[Code famille], es.[Intitule] AS [Famille],
    COUNT(*) AS [Nb Total Ref],
    SUM(CASE WHEN es.[Stock mouvementé] = 'Non' AND es.[Quantité en stock] > 0 THEN 1 ELSE 0 END) AS [Ref Dormantes],
    SUM(CASE WHEN es.[Stock mouvementé] = 'Non' AND es.[Quantité en stock] > 0 THEN es.[Valeur du stock (montant)] ELSE 0 END) AS [Valeur Dormante],
    ROUND(100.0 * SUM(CASE WHEN es.[Stock mouvementé] = 'Non' AND es.[Quantité en stock] > 0 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1) AS [Taux Obsolescence %],
    SUM(es.[Valeur du stock (montant)]) AS [Valeur Totale],
    es.societe AS [Societe]
FROM Etat_Stock es
WHERE {SOC_FILTER}
GROUP BY es.[Code famille], es.[Intitule], es.societe
ORDER BY SUM(CASE WHEN es.[Stock mouvementé] = 'Non' AND es.[Quantité en stock] > 0 THEN es.[Valeur du stock (montant)] ELSE 0 END) DESC""",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "stocks"
    },
    {
        "code": "DS_STK_MIN_COMMANDE",
        "nom": "Stock Minimum / Point de Commande",
        "query": f"""SELECT
    es.[Code article], es.[Désignation article] AS [Designation],
    es.[Code famille], es.[Intitule] AS [Famille],
    es.[Code dépôt], es.[DE_Intitule] AS [Depot],
    es.[Quantité en stock] AS [Qte Stock],
    es.[Quantité minimale] AS [Stock Min],
    es.[Quantité maximale] AS [Stock Max],
    es.[Quantité commandée] AS [Qte Commandee],
    CASE WHEN es.[Quantité en stock] <= es.[Quantité minimale] THEN 'A COMMANDER'
         WHEN es.[Quantité en stock] <= es.[Quantité minimale] * 1.5 THEN 'SURVEILLER'
         ELSE 'OK' END AS [Statut],
    es.[Quantité maximale] - es.[Quantité en stock] AS [Qte a Commander],
    es.societe AS [Societe]
FROM Etat_Stock es
WHERE es.[Quantité minimale] > 0
  AND {SOC_FILTER}
ORDER BY CASE WHEN es.[Quantité en stock] <= es.[Quantité minimale] THEN 0
              WHEN es.[Quantité en stock] <= es.[Quantité minimale] * 1.5 THEN 1
              ELSE 2 END,
         es.[Quantité en stock] / NULLIF(es.[Quantité minimale], 0)""",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "stocks"
    },
    {
        "code": "DS_STK_ECARTS_INVENTAIRE",
        "nom": "Analyse des Écarts d'Inventaire",
        "query": f"""SELECT
    es.[Code dépôt], es.[DE_Intitule] AS [Depot],
    es.[Code famille], es.[Intitule] AS [Famille],
    COUNT(DISTINCT es.[Code article]) AS [Nb Articles],
    SUM(es.[Quantité en stock]) AS [Qte Stock],
    SUM(es.[Valeur du stock (montant)]) AS [Valeur Stock],
    SUM(CASE WHEN es.[Quantité de contrôle] <> 0 THEN 1 ELSE 0 END) AS [Avec Ecart],
    SUM(es.[Quantité de contrôle]) AS [Ecart Total Qte],
    ROUND(100.0 * SUM(CASE WHEN es.[Quantité de contrôle] <> 0 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1) AS [Taux Ecart %],
    es.societe AS [Societe]
FROM Etat_Stock es
WHERE {SOC_FILTER}
GROUP BY es.[Code dépôt], es.[DE_Intitule], es.[Code famille], es.[Intitule], es.societe
ORDER BY SUM(CASE WHEN es.[Quantité de contrôle] <> 0 THEN 1 ELSE 0 END) DESC""",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "stocks"
    },
    {
        "code": "DS_STK_FLUX_DEPOT",
        "nom": "Flux de Stock par Dépôt",
        "query": f"""SELECT
    mv.[Code Dépôt] AS [Code Depot], mv.[Dépôt] AS [Depot],
    CAST(YEAR(mv.[Date Mouvement]) AS VARCHAR) + '-' + RIGHT('0' + CAST(MONTH(mv.[Date Mouvement]) AS VARCHAR), 2) AS [Periode],
    SUM(CASE WHEN mv.[Sens de mouvement] = N'Entrée' THEN mv.[Quantité] ELSE 0 END) AS [Entrees],
    SUM(CASE WHEN mv.[Sens de mouvement] = 'Sortie' THEN mv.[Quantité] ELSE 0 END) AS [Sorties],
    SUM(CASE WHEN mv.[Sens de mouvement] = N'Entrée' THEN mv.[Montant Stock] ELSE 0 END) AS [Valeur Entrees],
    SUM(CASE WHEN mv.[Sens de mouvement] = 'Sortie' THEN mv.[Montant Stock] ELSE 0 END) AS [Valeur Sorties],
    COUNT(DISTINCT mv.[Code article]) AS [Nb Articles],
    mv.societe AS [Societe]
FROM Mouvement_stock mv
WHERE mv.[Date Mouvement] BETWEEN @dateDebut AND @dateFin
  AND {SOC_FILTER_MV}
GROUP BY mv.[Code Dépôt], mv.[Dépôt], YEAR(mv.[Date Mouvement]), MONTH(mv.[Date Mouvement]), mv.societe
ORDER BY mv.[Code Dépôt], YEAR(mv.[Date Mouvement]), MONTH(mv.[Date Mouvement])""",
        "params": PARAMS_DATE_SOCIETE,
        "category": "stocks"
    },
    {
        "code": "DS_STK_LEAD_TIME",
        "nom": "Lead Time vs Stock Sécurité",
        "query": f"""SELECT
    es.[Code famille], es.[Intitule] AS [Famille],
    COUNT(DISTINCT es.[Code article]) AS [Nb Articles],
    SUM(es.[Quantité en stock]) AS [Qte Stock],
    SUM(es.[Quantité minimale]) AS [Stock Securite Total],
    SUM(es.[Valeur du stock (montant)]) AS [Valeur Stock],
    ROUND(AVG(CASE WHEN es.[Quantité minimale] > 0 THEN es.[Quantité en stock] / es.[Quantité minimale] END), 2) AS [Ratio Stock/Securite],
    SUM(CASE WHEN es.[Quantité en stock] < es.[Quantité minimale] THEN 1 ELSE 0 END) AS [Sous Seuil],
    es.societe AS [Societe]
FROM Etat_Stock es
WHERE es.[Quantité minimale] > 0
  AND {SOC_FILTER}
GROUP BY es.[Code famille], es.[Intitule], es.societe
ORDER BY SUM(CASE WHEN es.[Quantité en stock] < es.[Quantité minimale] THEN 1 ELSE 0 END) DESC""",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "stocks"
    },
    {
        "code": "DS_STK_VALORISATION_MULTI",
        "nom": "Valorisation Multi-Méthodes",
        "query": f"""SELECT
    es.[Code famille], es.[Intitule] AS [Famille],
    es.[Catalogue 1] AS [Catalogue],
    COUNT(DISTINCT es.[Code article]) AS [Nb Articles],
    SUM(es.[Quantité en stock]) AS [Qte Stock],
    SUM(es.[Valeur du stock (montant)]) AS [Valeur CMUP],
    ROUND(100.0 * SUM(es.[Valeur du stock (montant)]) / NULLIF(SUM(SUM(es.[Valeur du stock (montant)])) OVER (), 0), 2) AS [Part %],
    es.societe AS [Societe]
FROM Etat_Stock es
WHERE es.[Quantité en stock] > 0
  AND {SOC_FILTER}
GROUP BY es.[Code famille], es.[Intitule], es.[Catalogue 1], es.societe
ORDER BY SUM(es.[Valeur du stock (montant)]) DESC""",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "stocks"
    },
    {
        "code": "DS_STK_PRODUCTIVITE",
        "nom": "Productivité Logistique",
        "query": f"""SELECT
    mv.[Code Dépôt] AS [Code Depot], mv.[Dépôt] AS [Depot],
    COUNT(*) AS [Nb Mouvements],
    COUNT(DISTINCT mv.[Code article]) AS [Nb Articles Geres],
    SUM(mv.[Quantité]) AS [Qte Totale Mvt],
    SUM(mv.[Montant Stock]) AS [Valeur Totale Mvt],
    COUNT(DISTINCT mv.[N° Pièce]) AS [Nb Pieces],
    SUM(CASE WHEN mv.[Sens de mouvement] = N'Entrée' THEN 1 ELSE 0 END) AS [Nb Entrees],
    SUM(CASE WHEN mv.[Sens de mouvement] = 'Sortie' THEN 1 ELSE 0 END) AS [Nb Sorties],
    mv.societe AS [Societe]
FROM Mouvement_stock mv
WHERE mv.[Date Mouvement] BETWEEN @dateDebut AND @dateFin
  AND {SOC_FILTER_MV}
GROUP BY mv.[Code Dépôt], mv.[Dépôt], mv.societe
ORDER BY COUNT(*) DESC""",
        "params": PARAMS_DATE_SOCIETE,
        "category": "stocks"
    },
]

# ===============================================================
# 10 GRIDVIEWS
# ===============================================================
GRIDVIEWS = [
    ("DS_STK_MOUVEMENTS",    "Mouvements de Stock"),
    ("DS_STK_ENTREES",       "Entrées de Stock"),
    ("DS_STK_SORTIES",       "Sorties de Stock"),
    ("DS_STK_ETAT_ACTUEL",   "État du Stock Actuel"),
    ("DS_STK_PAR_DEPOT",     "Stock par Dépôt"),
    ("DS_STK_RUPTURE",       "Articles en Rupture"),
    ("DS_STK_SURSTOCK",      "Articles en Surstock"),
    ("DS_STK_DORMANT",       "Stock Dormant"),
    ("DS_STK_TRANSFERTS",    "Transferts Inter-Dépôts"),
    ("DS_STK_MIN_COMMANDE",  "Stock Minimum / Point de Commande"),
]

# ===============================================================
# 4 PIVOTS
# ===============================================================
PIVOTS = [
    ("DS_STK_VALORISATION", "Valorisation du Stock",
     [{"field":"Code famille","label":"Famille","type":"text"},{"field":"Famille","label":"Nom Famille","type":"text"},{"field":"Depot","label":"Dépôt","type":"text"}],
     [{"field":"Valeur Stock","label":"Valeur Stock","aggregation":"SUM","format":"currency","decimals":2},{"field":"Qte Stock","label":"Qte Stock","aggregation":"SUM","format":"number","decimals":0},{"field":"Nb Articles","label":"Nb Articles","aggregation":"SUM","format":"number","decimals":0}],
     [{"field":"Catalogue","label":"Catalogue","type":"select"},{"field":"Societe","label":"Société","type":"select"}]),
    ("DS_STK_INVENTAIRE_COMPARATIF", "Inventaire Comparatif",
     [{"field":"Depot","label":"Dépôt","type":"text"},{"field":"Famille","label":"Famille","type":"text"}],
     [{"field":"Nb References","label":"Nb Ref","aggregation":"SUM","format":"number","decimals":0},{"field":"Valeur Stock","label":"Valeur","aggregation":"SUM","format":"currency","decimals":2},{"field":"Taux Dispo %","label":"Taux Dispo","aggregation":"AVG","format":"number","decimals":1}],
     [{"field":"Societe","label":"Société","type":"select"}]),
    ("DS_STK_ECARTS_INVENTAIRE", "Analyse des Écarts d'Inventaire",
     [{"field":"Depot","label":"Dépôt","type":"text"},{"field":"Famille","label":"Famille","type":"text"}],
     [{"field":"Nb Articles","label":"Nb Articles","aggregation":"SUM","format":"number","decimals":0},{"field":"Avec Ecart","label":"Avec Écart","aggregation":"SUM","format":"number","decimals":0},{"field":"Taux Ecart %","label":"Taux Écart","aggregation":"AVG","format":"number","decimals":1}],
     [{"field":"Societe","label":"Société","type":"select"}]),
    ("DS_STK_VALORISATION_MULTI", "Valorisation Multi-Méthodes",
     [{"field":"Code famille","label":"Famille","type":"text"},{"field":"Catalogue","label":"Catalogue","type":"text"}],
     [{"field":"Valeur CMUP","label":"Valeur CMUP","aggregation":"SUM","format":"currency","decimals":2},{"field":"Qte Stock","label":"Qte Stock","aggregation":"SUM","format":"number","decimals":0},{"field":"Part %","label":"Part %","aggregation":"AVG","format":"number","decimals":2}],
     [{"field":"Societe","label":"Société","type":"select"}]),
]

# ===============================================================
# 11 DASHBOARDS
# ===============================================================
DASHBOARDS = [
    ("DS_STK_ROTATION", "Rotation des Stocks", [
        {"id":"w_rot_kpi_nb","type":"kpi","title":"Articles en Stock","x":0,"y":0,"w":3,"h":3,"config":{"dataSourceCode":"DS_STK_ROTATION","dataSourceOrigin":"template","value_field":"Qte Stock","aggregation":"COUNT","kpi_color":"#3b82f6"}},
        {"id":"w_rot_kpi_val","type":"kpi","title":"Valeur Totale Stock","x":3,"y":0,"w":3,"h":3,"config":{"dataSourceCode":"DS_STK_ROTATION","dataSourceOrigin":"template","value_field":"Valeur Stock","aggregation":"SUM","suffix":" DH","kpi_color":"#ef4444"}},
        {"id":"w_rot_kpi_couv","type":"kpi","title":"Couverture Moyenne","x":6,"y":0,"w":3,"h":3,"config":{"dataSourceCode":"DS_STK_ROTATION","dataSourceOrigin":"template","value_field":"Jours Couverture","aggregation":"AVG","suffix":" jours","kpi_color":"#f59e0b"}},
        {"id":"w_rot_bar","type":"chart_bar","title":"Taux de Rotation par Article","x":0,"y":3,"w":8,"h":5,"config":{"dataSourceCode":"DS_STK_ROTATION","dataSourceOrigin":"template","x_field":"Designation","y_field":"Taux Rotation","color":"#3b82f6","sort_field":"Taux Rotation","sort_direction":"desc","limit_rows":15}},
        {"id":"w_rot_table","type":"table","title":"Détail Rotation","x":0,"y":8,"w":12,"h":5,"config":{"dataSourceCode":"DS_STK_ROTATION","dataSourceOrigin":"template"}},
    ]),
    ("DS_STK_EVOLUTION_MENSUELLE", "Évolution Stock Mensuelle", [
        {"id":"w_evol_kpi_ent","type":"kpi","title":"Total Entrées","x":0,"y":0,"w":3,"h":3,"config":{"dataSourceCode":"DS_STK_EVOLUTION_MENSUELLE","dataSourceOrigin":"template","value_field":"Entrees Valeur","aggregation":"SUM","suffix":" DH","kpi_color":"#10b981"}},
        {"id":"w_evol_kpi_sor","type":"kpi","title":"Total Sorties","x":3,"y":0,"w":3,"h":3,"config":{"dataSourceCode":"DS_STK_EVOLUTION_MENSUELLE","dataSourceOrigin":"template","value_field":"Sorties Valeur","aggregation":"SUM","suffix":" DH","kpi_color":"#ef4444"}},
        {"id":"w_evol_line","type":"chart_line","title":"Évolution Entrées/Sorties","x":0,"y":3,"w":12,"h":5,"config":{"dataSourceCode":"DS_STK_EVOLUTION_MENSUELLE","dataSourceOrigin":"template","x_field":"Periode","y_field":"Entrees Valeur","color":"#10b981","show_grid":True}},
        {"id":"w_evol_table","type":"table","title":"Détail Mensuel","x":0,"y":8,"w":12,"h":5,"config":{"dataSourceCode":"DS_STK_EVOLUTION_MENSUELLE","dataSourceOrigin":"template"}},
    ]),
    ("DS_STK_ABC", "Analyse ABC Stock", [
        {"id":"w_abc_pie","type":"chart_pie","title":"Répartition ABC","x":0,"y":0,"w":5,"h":6,"config":{"dataSourceCode":"DS_STK_ABC","dataSourceOrigin":"template","label_field":"Classe ABC","value_field":"Valeur Stock","donut":True,"show_legend":True}},
        {"id":"w_abc_bar","type":"chart_bar","title":"Valeur par Classe ABC","x":5,"y":0,"w":7,"h":6,"config":{"dataSourceCode":"DS_STK_ABC","dataSourceOrigin":"template","x_field":"Classe ABC","y_field":"Valeur Stock","color":"#8b5cf6","show_labels":True}},
        {"id":"w_abc_table","type":"table","title":"Détail ABC","x":0,"y":6,"w":12,"h":5,"config":{"dataSourceCode":"DS_STK_ABC","dataSourceOrigin":"template"}},
    ]),
    ("DS_STK_COUVERTURE", "Couverture de Stock", [
        {"id":"w_couv_kpi","type":"kpi","title":"Couverture Moyenne","x":0,"y":0,"w":4,"h":3,"config":{"dataSourceCode":"DS_STK_COUVERTURE","dataSourceOrigin":"template","value_field":"Mois Couverture","aggregation":"AVG","suffix":" mois","kpi_color":"#f59e0b"}},
        {"id":"w_couv_bar","type":"chart_bar","title":"Couverture par Famille","x":0,"y":3,"w":8,"h":5,"config":{"dataSourceCode":"DS_STK_COUVERTURE","dataSourceOrigin":"template","x_field":"Famille","y_field":"Mois Couverture","color":"#f59e0b","sort_field":"Mois Couverture","sort_direction":"asc","limit_rows":15}},
        {"id":"w_couv_pie","type":"chart_pie","title":"Valeur Stock par Famille","x":8,"y":3,"w":4,"h":5,"config":{"dataSourceCode":"DS_STK_COUVERTURE","dataSourceOrigin":"template","label_field":"Famille","value_field":"Valeur Stock","donut":True}},
        {"id":"w_couv_table","type":"table","title":"Détail Couverture","x":0,"y":8,"w":12,"h":5,"config":{"dataSourceCode":"DS_STK_COUVERTURE","dataSourceOrigin":"template"}},
    ]),
    ("DS_STK_ABC_XYZ", "Classification ABC/XYZ", [
        {"id":"w_abcxyz_pie","type":"chart_pie","title":"Répartition ABC","x":0,"y":0,"w":4,"h":5,"config":{"dataSourceCode":"DS_STK_ABC_XYZ","dataSourceOrigin":"template","label_field":"Classe ABC","value_field":"Valeur Stock","donut":True}},
        {"id":"w_abcxyz_pie2","type":"chart_pie","title":"Répartition XYZ","x":4,"y":0,"w":4,"h":5,"config":{"dataSourceCode":"DS_STK_ABC_XYZ","dataSourceOrigin":"template","label_field":"Classe XYZ","value_field":"Qte Stock","donut":True}},
        {"id":"w_abcxyz_bar","type":"chart_bar","title":"Valeur par Classe","x":8,"y":0,"w":4,"h":5,"config":{"dataSourceCode":"DS_STK_ABC_XYZ","dataSourceOrigin":"template","x_field":"Classe ABC","y_field":"Valeur Stock","color":"#6366f1"}},
        {"id":"w_abcxyz_table","type":"table","title":"Détail Classification","x":0,"y":5,"w":12,"h":6,"config":{"dataSourceCode":"DS_STK_ABC_XYZ","dataSourceOrigin":"template"}},
    ]),
    ("DS_STK_PREVISION_RUPTURE", "Prévision de Rupture", [
        {"id":"w_prev_kpi_crit","type":"kpi","title":"Articles Critiques","x":0,"y":0,"w":3,"h":3,"config":{"dataSourceCode":"DS_STK_PREVISION_RUPTURE","dataSourceOrigin":"template","value_field":"Statut","aggregation":"COUNT","kpi_color":"#ef4444","subtitle":"< 7 jours"}},
        {"id":"w_prev_kpi_alert","type":"kpi","title":"Articles en Alerte","x":3,"y":0,"w":3,"h":3,"config":{"dataSourceCode":"DS_STK_PREVISION_RUPTURE","dataSourceOrigin":"template","value_field":"Jours Restants","aggregation":"AVG","suffix":" jours","kpi_color":"#f59e0b"}},
        {"id":"w_prev_bar","type":"chart_bar","title":"Jours Restants par Article","x":0,"y":3,"w":12,"h":5,"config":{"dataSourceCode":"DS_STK_PREVISION_RUPTURE","dataSourceOrigin":"template","x_field":"Designation","y_field":"Jours Restants","color":"#ef4444","sort_field":"Jours Restants","sort_direction":"asc","limit_rows":20}},
        {"id":"w_prev_table","type":"table","title":"Détail Prévision","x":0,"y":8,"w":12,"h":5,"config":{"dataSourceCode":"DS_STK_PREVISION_RUPTURE","dataSourceOrigin":"template"}},
    ]),
    ("DS_STK_COUT_POSSESSION", "Coût de Possession du Stock", [
        {"id":"w_cout_kpi","type":"kpi","title":"Coût Possession Annuel","x":0,"y":0,"w":4,"h":3,"config":{"dataSourceCode":"DS_STK_COUT_POSSESSION","dataSourceOrigin":"template","value_field":"Cout Possession Annuel","aggregation":"SUM","suffix":" DH","kpi_color":"#ef4444"}},
        {"id":"w_cout_kpi2","type":"kpi","title":"Valeur Stock Total","x":4,"y":0,"w":4,"h":3,"config":{"dataSourceCode":"DS_STK_COUT_POSSESSION","dataSourceOrigin":"template","value_field":"Valeur Stock","aggregation":"SUM","suffix":" DH","kpi_color":"#3b82f6"}},
        {"id":"w_cout_bar","type":"chart_bar","title":"Coût par Famille","x":0,"y":3,"w":8,"h":5,"config":{"dataSourceCode":"DS_STK_COUT_POSSESSION","dataSourceOrigin":"template","x_field":"Famille","y_field":"Cout Possession Annuel","color":"#ef4444","horizontal":True,"limit_rows":15}},
        {"id":"w_cout_pie","type":"chart_pie","title":"Part Valeur","x":8,"y":3,"w":4,"h":5,"config":{"dataSourceCode":"DS_STK_COUT_POSSESSION","dataSourceOrigin":"template","label_field":"Famille","value_field":"Part Valeur %","donut":True}},
        {"id":"w_cout_table","type":"table","title":"Détail Coûts","x":0,"y":8,"w":12,"h":5,"config":{"dataSourceCode":"DS_STK_COUT_POSSESSION","dataSourceOrigin":"template"}},
    ]),
    ("DS_STK_OBSOLESCENCE", "Taux de Péremption / Obsolescence", [
        {"id":"w_obs_kpi","type":"kpi","title":"Valeur Dormante","x":0,"y":0,"w":4,"h":3,"config":{"dataSourceCode":"DS_STK_OBSOLESCENCE","dataSourceOrigin":"template","value_field":"Valeur Dormante","aggregation":"SUM","suffix":" DH","kpi_color":"#ef4444"}},
        {"id":"w_obs_kpi2","type":"kpi","title":"Taux Obsolescence Moyen","x":4,"y":0,"w":4,"h":3,"config":{"dataSourceCode":"DS_STK_OBSOLESCENCE","dataSourceOrigin":"template","value_field":"Taux Obsolescence %","aggregation":"AVG","suffix":" %","kpi_color":"#f59e0b"}},
        {"id":"w_obs_bar","type":"chart_bar","title":"Obsolescence par Famille","x":0,"y":3,"w":8,"h":5,"config":{"dataSourceCode":"DS_STK_OBSOLESCENCE","dataSourceOrigin":"template","x_field":"Famille","y_field":"Taux Obsolescence %","color":"#f59e0b","sort_field":"Taux Obsolescence %","sort_direction":"desc","limit_rows":15}},
        {"id":"w_obs_table","type":"table","title":"Détail Obsolescence","x":0,"y":8,"w":12,"h":5,"config":{"dataSourceCode":"DS_STK_OBSOLESCENCE","dataSourceOrigin":"template"}},
    ]),
    ("DS_STK_FLUX_DEPOT", "Flux de Stock par Dépôt", [
        {"id":"w_flux_kpi","type":"kpi","title":"Nb Mouvements","x":0,"y":0,"w":4,"h":3,"config":{"dataSourceCode":"DS_STK_FLUX_DEPOT","dataSourceOrigin":"template","value_field":"Entrees","aggregation":"SUM","kpi_color":"#3b82f6"}},
        {"id":"w_flux_bar","type":"chart_bar","title":"Flux par Dépôt","x":0,"y":3,"w":8,"h":5,"config":{"dataSourceCode":"DS_STK_FLUX_DEPOT","dataSourceOrigin":"template","x_field":"Depot","y_field":"Valeur Entrees","color":"#10b981","show_grid":True,"limit_rows":10}},
        {"id":"w_flux_line","type":"chart_line","title":"Évolution par Période","x":8,"y":3,"w":4,"h":5,"config":{"dataSourceCode":"DS_STK_FLUX_DEPOT","dataSourceOrigin":"template","x_field":"Periode","y_field":"Entrees","color":"#3b82f6"}},
        {"id":"w_flux_table","type":"table","title":"Détail Flux","x":0,"y":8,"w":12,"h":5,"config":{"dataSourceCode":"DS_STK_FLUX_DEPOT","dataSourceOrigin":"template"}},
    ]),
    ("DS_STK_LEAD_TIME", "Lead Time vs Stock Sécurité", [
        {"id":"w_lead_kpi","type":"kpi","title":"Familles Sous Seuil","x":0,"y":0,"w":4,"h":3,"config":{"dataSourceCode":"DS_STK_LEAD_TIME","dataSourceOrigin":"template","value_field":"Sous Seuil","aggregation":"SUM","kpi_color":"#ef4444"}},
        {"id":"w_lead_bar","type":"chart_bar","title":"Ratio Stock/Sécurité par Famille","x":0,"y":3,"w":12,"h":5,"config":{"dataSourceCode":"DS_STK_LEAD_TIME","dataSourceOrigin":"template","x_field":"Famille","y_field":"Ratio Stock/Securite","color":"#6366f1","sort_field":"Ratio Stock/Securite","sort_direction":"asc","limit_rows":15}},
        {"id":"w_lead_table","type":"table","title":"Détail Lead Time","x":0,"y":8,"w":12,"h":5,"config":{"dataSourceCode":"DS_STK_LEAD_TIME","dataSourceOrigin":"template"}},
    ]),
    ("DS_STK_PRODUCTIVITE", "Productivité Logistique", [
        {"id":"w_prod_kpi","type":"kpi","title":"Total Mouvements","x":0,"y":0,"w":3,"h":3,"config":{"dataSourceCode":"DS_STK_PRODUCTIVITE","dataSourceOrigin":"template","value_field":"Nb Mouvements","aggregation":"SUM","kpi_color":"#3b82f6"}},
        {"id":"w_prod_kpi2","type":"kpi","title":"Valeur Totale","x":3,"y":0,"w":3,"h":3,"config":{"dataSourceCode":"DS_STK_PRODUCTIVITE","dataSourceOrigin":"template","value_field":"Valeur Totale Mvt","aggregation":"SUM","suffix":" DH","kpi_color":"#10b981"}},
        {"id":"w_prod_bar","type":"chart_bar","title":"Mouvements par Dépôt","x":0,"y":3,"w":8,"h":5,"config":{"dataSourceCode":"DS_STK_PRODUCTIVITE","dataSourceOrigin":"template","x_field":"Depot","y_field":"Nb Mouvements","color":"#3b82f6","horizontal":True}},
        {"id":"w_prod_pie","type":"chart_pie","title":"Entrées vs Sorties","x":8,"y":3,"w":4,"h":5,"config":{"dataSourceCode":"DS_STK_PRODUCTIVITE","dataSourceOrigin":"template","label_field":"Depot","value_field":"Nb Entrees","donut":True}},
        {"id":"w_prod_table","type":"table","title":"Détail Productivité","x":0,"y":8,"w":12,"h":5,"config":{"dataSourceCode":"DS_STK_PRODUCTIVITE","dataSourceOrigin":"template"}},
    ]),
]

# ===============================================================
# MENU ICONS
# ===============================================================
MENU_ICONS = {
    "Mouvements de Stock": "ArrowLeftRight",
    "Entrées de Stock": "ArrowDownToLine",
    "Sorties de Stock": "ArrowUpFromLine",
    "État du Stock Actuel": "ClipboardList",
    "Stock par Dépôt": "Warehouse",
    "Articles en Rupture": "AlertTriangle",
    "Articles en Surstock": "PackagePlus",
    "Valorisation du Stock": "BadgeDollarSign",
    "Rotation des Stocks": "RefreshCw",
    "Évolution Stock Mensuelle": "TrendingUp",
    "Stock Dormant": "Moon",
    "Analyse ABC Stock": "BarChart3",
    "Couverture de Stock": "Shield",
    "Inventaire Comparatif": "Scale",
    "Transferts Inter-Dépôts": "Repeat",
    "Classification ABC/XYZ": "LayoutGrid",
    "Prévision de Rupture": "AlertCircle",
    "Coût de Possession du Stock": "Coins",
    "Taux de Péremption / Obsolescence": "Timer",
    "Stock Minimum / Point de Commande": "ArrowDown",
    "Analyse des Écarts d'Inventaire": "GitCompare",
    "Flux de Stock par Dépôt": "Activity",
    "Lead Time vs Stock Sécurité": "Clock",
    "Valorisation Multi-Méthodes": "Calculator",
    "Productivité Logistique": "Gauge",
}


def main():
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()

    print("=" * 60)
    print("  CREATION DES 25 RAPPORTS STOCKS")
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
    print(f"  => {len(DS_TEMPLATES)} templates")

    # --- 2. GridViews ---
    print("\n[2/5] Creation des GridViews...")
    import re
    gv_ids = {}
    for ds_code, nom in GRIDVIEWS:
        cursor.execute("SELECT query_template FROM APP_DataSources_Templates WHERE code = ?", ds_code)
        row = cursor.fetchone()
        if not row:
            print(f"  XX SKIP {nom}")
            continue

        query = row[0]
        aliases = re.findall(r'AS\s+\[([^\]]+)\]', query, re.IGNORECASE)
        if not aliases:
            aliases = re.findall(r'AS\s+(\w+)', query, re.IGNORECASE)

        columns = []
        for alias in aliases[:40]:
            col_format = "text"
            align = "left"
            if any(kw in alias.lower() for kw in ["montant", "valeur", "prix", "cout", "cmup", "cu ", "dpa", "dpr"]):
                col_format = "currency"; align = "right"
            elif any(kw in alias.lower() for kw in ["qte", "quantit", "nb ", "nombre", "entrees", "sorties"]):
                col_format = "number"; align = "right"
            elif any(kw in alias.lower() for kw in ["%", "taux", "part ", "ratio", "cumul"]):
                col_format = "number"; align = "right"
            elif "date" in alias.lower():
                col_format = "date"
            columns.append({"field": alias, "header": alias, "format": col_format, "align": align, "sortable": True, "filterable": True, "visible": True, "width": 150})

        total_cols = [c["field"] for c in columns if c["format"] in ("currency", "number") and "%" not in c["field"]]
        columns_json = json.dumps(columns)
        total_cols_json = json.dumps(total_cols[:5])
        features_json = json.dumps({"show_search":True,"show_column_filters":True,"show_grouping":True,"show_column_toggle":True,"show_export":True,"show_pagination":True,"allow_sorting":True})

        cursor.execute("SELECT id FROM APP_GridViews WHERE data_source_code = ?", ds_code)
        existing = cursor.fetchone()
        if existing:
            gv_ids[ds_code] = existing[0]
            cursor.execute("""UPDATE APP_GridViews
                SET columns_config=?, total_columns=?
                WHERE id=?""", columns_json, total_cols_json, existing[0])
            print(f"  OK MAJ {nom} (id={existing[0]}, {len(columns)} cols)")
        else:
            cursor.execute("""INSERT INTO APP_GridViews
                (nom, description, data_source_code, columns_config, page_size, show_totals, total_columns, features, actif)
                VALUES (?, ?, ?, ?, 25, 1, ?, ?, 1)""",
                nom, f"Rapport Stocks - {nom}", ds_code, columns_json, total_cols_json, features_json)
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
            nom, f"Pivot Stocks - {nom}", ds_code,
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
            nom, f"Dashboard Stocks - {nom}", json.dumps(widgets))
        cursor.execute("SELECT @@IDENTITY")
        db_id = int(cursor.fetchone()[0])
        db_ids[ds_code] = db_id
        print(f"  + NEW Dashboard {nom} (id={db_id})")
    conn.commit()

    # --- 5. Menus ---
    print("\n[5/5] Creation des Menus...")
    cursor.execute("SELECT id FROM APP_Menus WHERE nom = 'Stocks' AND parent_id IS NULL")
    root = cursor.fetchone()
    if root:
        root_id = root[0]
        print(f"  OK EXISTS racine 'Stocks' (id={root_id})")
    else:
        cursor.execute("""INSERT INTO APP_Menus (nom, icon, type, parent_id, ordre, actif)
            VALUES ('Stocks', 'Package', 'folder', NULL, 30, 1)""")
        cursor.execute("SELECT @@IDENTITY")
        root_id = int(cursor.fetchone()[0])
        print(f"  + NEW racine 'Stocks' (id={root_id})")

    subfolders = [
        ("Mouvements et Situation", "ArrowLeftRight", 1),
        ("Analyses Stocks", "BarChart3", 2),
        ("Rapports Avancés Stocks", "Activity", 3),
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

    menu_items = [
        # 3.1 Mouvements et Situation
        ("Mouvements et Situation", "Mouvements de Stock", "gridview", gv_ids.get("DS_STK_MOUVEMENTS"), 1),
        ("Mouvements et Situation", "Entrées de Stock", "gridview", gv_ids.get("DS_STK_ENTREES"), 2),
        ("Mouvements et Situation", "Sorties de Stock", "gridview", gv_ids.get("DS_STK_SORTIES"), 3),
        ("Mouvements et Situation", "État du Stock Actuel", "gridview", gv_ids.get("DS_STK_ETAT_ACTUEL"), 4),
        ("Mouvements et Situation", "Stock par Dépôt", "gridview", gv_ids.get("DS_STK_PAR_DEPOT"), 5),
        ("Mouvements et Situation", "Articles en Rupture", "gridview", gv_ids.get("DS_STK_RUPTURE"), 6),
        ("Mouvements et Situation", "Articles en Surstock", "gridview", gv_ids.get("DS_STK_SURSTOCK"), 7),
        # 3.2 Analyses Stocks
        ("Analyses Stocks", "Valorisation du Stock", "pivot-v2", pv_ids.get("DS_STK_VALORISATION"), 1),
        ("Analyses Stocks", "Rotation des Stocks", "dashboard", db_ids.get("DS_STK_ROTATION"), 2),
        ("Analyses Stocks", "Évolution Stock Mensuelle", "dashboard", db_ids.get("DS_STK_EVOLUTION_MENSUELLE"), 3),
        ("Analyses Stocks", "Stock Dormant", "gridview", gv_ids.get("DS_STK_DORMANT"), 4),
        ("Analyses Stocks", "Analyse ABC Stock", "dashboard", db_ids.get("DS_STK_ABC"), 5),
        ("Analyses Stocks", "Couverture de Stock", "dashboard", db_ids.get("DS_STK_COUVERTURE"), 6),
        ("Analyses Stocks", "Inventaire Comparatif", "pivot-v2", pv_ids.get("DS_STK_INVENTAIRE_COMPARATIF"), 7),
        ("Analyses Stocks", "Transferts Inter-Dépôts", "gridview", gv_ids.get("DS_STK_TRANSFERTS"), 8),
        # 3.3 Rapports Avances
        ("Rapports Avancés Stocks", "Classification ABC/XYZ", "dashboard", db_ids.get("DS_STK_ABC_XYZ"), 1),
        ("Rapports Avancés Stocks", "Prévision de Rupture", "dashboard", db_ids.get("DS_STK_PREVISION_RUPTURE"), 2),
        ("Rapports Avancés Stocks", "Coût de Possession du Stock", "dashboard", db_ids.get("DS_STK_COUT_POSSESSION"), 3),
        ("Rapports Avancés Stocks", "Taux de Péremption / Obsolescence", "dashboard", db_ids.get("DS_STK_OBSOLESCENCE"), 4),
        ("Rapports Avancés Stocks", "Stock Minimum / Point de Commande", "gridview", gv_ids.get("DS_STK_MIN_COMMANDE"), 5),
        ("Rapports Avancés Stocks", "Analyse des Écarts d'Inventaire", "pivot-v2", pv_ids.get("DS_STK_ECARTS_INVENTAIRE"), 6),
        ("Rapports Avancés Stocks", "Flux de Stock par Dépôt", "dashboard", db_ids.get("DS_STK_FLUX_DEPOT"), 7),
        ("Rapports Avancés Stocks", "Lead Time vs Stock Sécurité", "dashboard", db_ids.get("DS_STK_LEAD_TIME"), 8),
        ("Rapports Avancés Stocks", "Valorisation Multi-Méthodes", "pivot-v2", pv_ids.get("DS_STK_VALORISATION_MULTI"), 9),
        ("Rapports Avancés Stocks", "Productivité Logistique", "dashboard", db_ids.get("DS_STK_PRODUCTIVITE"), 10),
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
