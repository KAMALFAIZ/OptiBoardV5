"""
Création des 25 rapports du cycle ACHATS pour OptiBoard
8 GRID + 8 PIVOT + 9 DASHBOARD
Selon le catalogue RAPPORTS_OPTIBOARD.md
"""
import pyodbc, json, sys

CONN_STR = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019;TrustServerCertificate=yes"

# ═══════════════════════════════════════════════════════════════
# PARAMÈTRES COMMUNS
# ═══════════════════════════════════════════════════════════════
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

# Filtre societe commun
SOC_FILTER = """(@societe IS NULL OR li.societe = @societe)"""

# ═══════════════════════════════════════════════════════════════
# 25 DATASOURCE TEMPLATES
# ═══════════════════════════════════════════════════════════════
DS_TEMPLATES = [
    # ─── 2.1 Documents Achats (6 GRID) ───
    {
        "code": "DS_ACH_FACTURES",
        "nom": "Factures Fournisseurs",
        "query": f"""SELECT
    li.[N° Pièce], li.[Date], li.[Code fournisseur], li.[Intitulé fournisseur],
    li.[Code article], li.[Désignation], li.[Catalogue 1] AS [Famille],
    li.[Quantité], li.[Prix unitaire], li.[Montant HT Net], li.[Montant TTC Net],
    li.[Remise 1], li.[Frais d'approche], li.CMUP, li.[Prix de revient],
    li.[Code dépôt], li.[Intitulé dépôt], en.Souche, en.Statut,
    en.[Catégorie Comptable], li.societe
FROM Lignes_des_achats li
INNER JOIN [Entête_des_achats] en ON li.societe = en.societe AND li.[Type Document] = en.[Type Document] AND li.[N° Pièce] = en.[N° pièce]
WHERE li.[Type Document] IN ('Facture', 'Facture comptabilisée')
  AND li.[Date] BETWEEN @dateDebut AND @dateFin
  AND {SOC_FILTER}
ORDER BY li.[Date] DESC, li.[N° Pièce]""",
        "params": PARAMS_DATE_SOCIETE,
        "category": "achats"
    },
    {
        "code": "DS_ACH_BL",
        "nom": "Bons de Réception",
        "query": f"""SELECT
    li.[N° Pièce], li.[Date], li.[Code fournisseur], li.[Intitulé fournisseur],
    li.[Code article], li.[Désignation], li.[Catalogue 1] AS [Famille],
    li.[Quantité], li.[Prix unitaire], li.[Montant HT Net], li.[Montant TTC Net],
    li.[Code dépôt], li.[Intitulé dépôt], li.[N° Pièce BC] AS [N° BC],
    en.Souche, en.Statut, li.societe
FROM Lignes_des_achats li
INNER JOIN [Entête_des_achats] en ON li.societe = en.societe AND li.[Type Document] = en.[Type Document] AND li.[N° Pièce] = en.[N° pièce]
WHERE li.[Type Document] = 'Bon de livraison'
  AND li.[Date] BETWEEN @dateDebut AND @dateFin
  AND {SOC_FILTER}
ORDER BY li.[Date] DESC""",
        "params": PARAMS_DATE_SOCIETE,
        "category": "achats"
    },
    {
        "code": "DS_ACH_BC",
        "nom": "Bons de Commande Fournisseurs",
        "query": f"""SELECT
    li.[N° Pièce], li.[Date], li.[Code fournisseur], li.[Intitulé fournisseur],
    li.[Code article], li.[Désignation], li.[Catalogue 1] AS [Famille],
    li.[Quantité], li.[Prix unitaire], li.[Montant HT Net], li.[Montant TTC Net],
    li.[Date Livraison] AS [Date Livraison Prévue],
    li.[Code dépôt], li.[Intitulé dépôt], en.Souche, en.Statut, li.societe
FROM Lignes_des_achats li
INNER JOIN [Entête_des_achats] en ON li.societe = en.societe AND li.[Type Document] = en.[Type Document] AND li.[N° Pièce] = en.[N° pièce]
WHERE li.[Type Document] = 'Bon de commande'
  AND li.[Date] BETWEEN @dateDebut AND @dateFin
  AND {SOC_FILTER}
ORDER BY li.[Date] DESC""",
        "params": PARAMS_DATE_SOCIETE,
        "category": "achats"
    },
    {
        "code": "DS_ACH_DA",
        "nom": "Demandes d'Achat",
        "query": f"""SELECT
    li.[N° Pièce], li.[Date], li.[Code fournisseur], li.[Intitulé fournisseur],
    li.[Code article], li.[Désignation], li.[Catalogue 1] AS [Famille],
    li.[Quantité], li.[Prix unitaire], li.[Montant HT Net],
    en.Souche, en.Statut, li.societe
FROM Lignes_des_achats li
INNER JOIN [Entête_des_achats] en ON li.societe = en.societe AND li.[Type Document] = en.[Type Document] AND li.[N° Pièce] = en.[N° pièce]
WHERE li.[Type Document] = 'Demande d''achat'
  AND li.[Date] BETWEEN @dateDebut AND @dateFin
  AND {SOC_FILTER}
ORDER BY li.[Date] DESC""",
        "params": PARAMS_DATE_SOCIETE,
        "category": "achats"
    },
    {
        "code": "DS_ACH_AVOIRS",
        "nom": "Avoirs Fournisseurs",
        "query": f"""SELECT
    li.[N° Pièce], li.[Date], li.[Code fournisseur], li.[Intitulé fournisseur],
    li.[Code article], li.[Désignation], li.[Quantité], li.[Prix unitaire],
    li.[Montant HT Net], li.[Montant TTC Net], en.Souche, en.Statut, li.societe
FROM Lignes_des_achats li
INNER JOIN [Entête_des_achats] en ON li.societe = en.societe AND li.[Type Document] = en.[Type Document] AND li.[N° Pièce] = en.[N° pièce]
WHERE li.[Type Document] IN ('Facture avoir', 'Facture avoir comptabilisée')
  AND li.[Date] BETWEEN @dateDebut AND @dateFin
  AND {SOC_FILTER}
ORDER BY li.[Date] DESC""",
        "params": PARAMS_DATE_SOCIETE,
        "category": "achats"
    },
    {
        "code": "DS_ACH_RETOURS",
        "nom": "Bons de Retour Fournisseurs",
        "query": f"""SELECT
    li.[N° Pièce], li.[Date], li.[Code fournisseur], li.[Intitulé fournisseur],
    li.[Code article], li.[Désignation], li.[Quantité], li.[Prix unitaire],
    li.[Montant HT Net], li.[Montant TTC Net], li.[Code dépôt], en.Statut, li.societe
FROM Lignes_des_achats li
INNER JOIN [Entête_des_achats] en ON li.societe = en.societe AND li.[Type Document] = en.[Type Document] AND li.[N° Pièce] = en.[N° pièce]
WHERE li.[Type Document] IN ('Bon de retour', 'Facture de retour', 'Facture de retour comptabilisée')
  AND li.[Date] BETWEEN @dateDebut AND @dateFin
  AND {SOC_FILTER}
ORDER BY li.[Date] DESC""",
        "params": PARAMS_DATE_SOCIETE,
        "category": "achats"
    },

    # ─── 2.2 Analyses Achats ───
    {
        "code": "DS_ACH_PAR_FOURNISSEUR",
        "nom": "Achats par Fournisseur",
        "query": f"""SELECT
    li.[Code fournisseur], li.[Intitulé fournisseur],
    COUNT(DISTINCT li.[N° Pièce]) AS [Nb Documents],
    COUNT(DISTINCT li.[Code article]) AS [Nb Articles],
    SUM(li.[Quantité]) AS [Quantité],
    SUM(li.[Montant HT Net]) AS [Montant HT],
    SUM(li.[Montant TTC Net]) AS [Montant TTC],
    li.societe AS [Société]
FROM Lignes_des_achats li
WHERE li.[Type Document] IN ('Facture', 'Facture comptabilisée')
  AND li.[Date] BETWEEN @dateDebut AND @dateFin
  AND {SOC_FILTER}
GROUP BY li.[Code fournisseur], li.[Intitulé fournisseur], li.societe
ORDER BY SUM(li.[Montant HT Net]) DESC""",
        "params": PARAMS_DATE_SOCIETE,
        "category": "achats"
    },
    {
        "code": "DS_ACH_PAR_ARTICLE",
        "nom": "Achats par Article",
        "query": f"""SELECT
    li.[Code article], li.[Désignation], li.[Catalogue 1] AS [Famille],
    li.[Catalogue 2] AS [Sous-Famille], li.[Gamme 1] AS [Gamme],
    COUNT(DISTINCT li.[Code fournisseur]) AS [Nb Fournisseurs],
    SUM(li.[Quantité]) AS [Quantité],
    SUM(li.[Montant HT Net]) AS [Montant HT],
    AVG(li.[Prix unitaire]) AS [Prix Moyen],
    li.societe AS [Société]
FROM Lignes_des_achats li
WHERE li.[Type Document] IN ('Facture', 'Facture comptabilisée')
  AND li.[Date] BETWEEN @dateDebut AND @dateFin
  AND {SOC_FILTER}
GROUP BY li.[Code article], li.[Désignation], li.[Catalogue 1], li.[Catalogue 2], li.[Gamme 1], li.societe
ORDER BY SUM(li.[Montant HT Net]) DESC""",
        "params": PARAMS_DATE_SOCIETE,
        "category": "achats"
    },
    {
        "code": "DS_ACH_PAR_FAMILLE",
        "nom": "Achats par Famille Article",
        "query": f"""SELECT
    li.[Catalogue 1] AS [Famille], li.[Catalogue 2] AS [Sous-Famille],
    COUNT(DISTINCT li.[Code article]) AS [Nb Articles],
    COUNT(DISTINCT li.[Code fournisseur]) AS [Nb Fournisseurs],
    SUM(li.[Quantité]) AS [Quantité],
    SUM(li.[Montant HT Net]) AS [Montant HT],
    SUM(li.[Montant TTC Net]) AS [Montant TTC],
    li.societe AS [Société]
FROM Lignes_des_achats li
WHERE li.[Type Document] IN ('Facture', 'Facture comptabilisée')
  AND li.[Date] BETWEEN @dateDebut AND @dateFin
  AND {SOC_FILTER}
GROUP BY li.[Catalogue 1], li.[Catalogue 2], li.societe
ORDER BY SUM(li.[Montant HT Net]) DESC""",
        "params": PARAMS_DATE_SOCIETE,
        "category": "achats"
    },
    {
        "code": "DS_ACH_EVOLUTION_MENSUELLE",
        "nom": "Evolution Achats Mensuelle",
        "query": f"""SELECT
    YEAR(li.[Date]) AS [Année], MONTH(li.[Date]) AS [Mois],
    FORMAT(li.[Date], 'yyyy-MM') AS [Période],
    COUNT(DISTINCT li.[Code fournisseur]) AS [Nb Fournisseurs],
    COUNT(DISTINCT li.[N° Pièce]) AS [Nb Documents],
    SUM(li.[Quantité]) AS [Quantité],
    SUM(li.[Montant HT Net]) AS [Montant HT],
    SUM(li.[Montant TTC Net]) AS [Montant TTC],
    li.societe AS [Société]
FROM Lignes_des_achats li
WHERE li.[Type Document] IN ('Facture', 'Facture comptabilisée')
  AND li.[Date] BETWEEN @dateDebut AND @dateFin
  AND {SOC_FILTER}
GROUP BY YEAR(li.[Date]), MONTH(li.[Date]), FORMAT(li.[Date], 'yyyy-MM'), li.societe
ORDER BY YEAR(li.[Date]) DESC, MONTH(li.[Date]) DESC""",
        "params": PARAMS_DATE_SOCIETE,
        "category": "achats"
    },
    {
        "code": "DS_ACH_TOP20_FOURNISSEURS",
        "nom": "Top 20 Fournisseurs",
        "query": f"""SELECT TOP 20
    li.[Code fournisseur], li.[Intitulé fournisseur],
    COUNT(DISTINCT li.[N° Pièce]) AS [Nb Factures],
    SUM(li.[Quantité]) AS [Quantité],
    SUM(li.[Montant HT Net]) AS [Montant HT],
    SUM(li.[Montant TTC Net]) AS [Montant TTC],
    ROUND(100.0 * SUM(li.[Montant HT Net]) / NULLIF((SELECT SUM(l2.[Montant HT Net]) FROM Lignes_des_achats l2 WHERE l2.[Type Document] IN ('Facture','Facture comptabilisée') AND l2.[Date] BETWEEN @dateDebut AND @dateFin AND (@societe IS NULL OR l2.societe = @societe)), 0), 2) AS [% du Total]
FROM Lignes_des_achats li
WHERE li.[Type Document] IN ('Facture', 'Facture comptabilisée')
  AND li.[Date] BETWEEN @dateDebut AND @dateFin
  AND {SOC_FILTER}
GROUP BY li.[Code fournisseur], li.[Intitulé fournisseur]
ORDER BY SUM(li.[Montant HT Net]) DESC""",
        "params": PARAMS_DATE_SOCIETE,
        "category": "achats"
    },
    {
        "code": "DS_ACH_COMPARATIF_PRIX",
        "nom": "Comparatif Prix d'Achat",
        "query": f"""SELECT
    li.[Code article], li.[Désignation], li.[Code fournisseur], li.[Intitulé fournisseur],
    MIN(li.[Prix unitaire]) AS [Prix Min], MAX(li.[Prix unitaire]) AS [Prix Max],
    AVG(li.[Prix unitaire]) AS [Prix Moyen],
    MAX(li.[Prix unitaire]) - MIN(li.[Prix unitaire]) AS [Ecart Prix],
    SUM(li.[Quantité]) AS [Quantité Totale],
    SUM(li.[Montant HT Net]) AS [Montant HT],
    li.societe AS [Société]
FROM Lignes_des_achats li
WHERE li.[Type Document] IN ('Facture', 'Facture comptabilisée')
  AND li.[Date] BETWEEN @dateDebut AND @dateFin
  AND {SOC_FILTER}
GROUP BY li.[Code article], li.[Désignation], li.[Code fournisseur], li.[Intitulé fournisseur], li.societe
ORDER BY li.[Code article], SUM(li.[Montant HT Net]) DESC""",
        "params": PARAMS_DATE_SOCIETE,
        "category": "achats"
    },
    {
        "code": "DS_ACH_COMMANDES_EN_COURS",
        "nom": "Commandes en Cours Fournisseurs",
        "query": f"""SELECT
    li.[N° Pièce], li.[Date], li.[Code fournisseur], li.[Intitulé fournisseur],
    li.[Code article], li.[Désignation], li.[Quantité] AS [Qté Commandée],
    ISNULL(li.[Quantité PL], 0) AS [Qté Reçue],
    li.[Quantité] - ISNULL(li.[Quantité PL], 0) AS [Qté Restante],
    li.[Prix unitaire], li.[Montant HT Net],
    CASE WHEN ISDATE(li.[Date Livraison]) = 1 AND CAST(li.[Date Livraison] AS DATE) < CAST(GETDATE() AS DATE) THEN 'En retard' ELSE 'A temps' END AS [Statut Livraison],
    en.Statut, li.societe AS [Societe]
FROM Lignes_des_achats li
INNER JOIN [Entête_des_achats] en ON li.societe = en.societe AND li.[Type Document] = en.[Type Document] AND li.[N° Pièce] = en.[N° pièce]
WHERE li.[Type Document] = 'Bon de commande'
  AND li.[Quantité] > ISNULL(li.[Quantité PL], 0)
  AND {SOC_FILTER}
ORDER BY li.[Date] DESC""",
        "params": PARAMS_SOCIETE_ONLY,
        "category": "achats"
    },
    {
        "code": "DS_ACH_DELAI_LIVRAISON",
        "nom": "Analyse Délais Livraison Fournisseurs",
        "query": f"""SELECT
    li.[Code fournisseur], li.[Intitulé fournisseur],
    COUNT(DISTINCT li.[N° Pièce]) AS [Nb Réceptions],
    AVG(DATEDIFF(day, li.[Date BC], li.[Date])) AS [Délai Moyen (j)],
    MIN(DATEDIFF(day, li.[Date BC], li.[Date])) AS [Délai Min (j)],
    MAX(DATEDIFF(day, li.[Date BC], li.[Date])) AS [Délai Max (j)],
    SUM(CASE WHEN li.[Date] > li.[Date Livraison] THEN 1 ELSE 0 END) AS [Nb Retards],
    ROUND(100.0 * SUM(CASE WHEN li.[Date] > li.[Date Livraison] THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1) AS [% Retard],
    li.societe AS [Société]
FROM Lignes_des_achats li
WHERE li.[Type Document] = 'Bon de livraison'
  AND li.[Date BC] IS NOT NULL
  AND li.[Date] BETWEEN @dateDebut AND @dateFin
  AND {SOC_FILTER}
GROUP BY li.[Code fournisseur], li.[Intitulé fournisseur], li.societe
ORDER BY AVG(DATEDIFF(day, li.[Date BC], li.[Date])) DESC""",
        "params": PARAMS_DATE_SOCIETE,
        "category": "achats"
    },
    {
        "code": "DS_ACH_PAR_DEPOT",
        "nom": "Achats par Dépôt",
        "query": f"""SELECT
    li.[Code dépôt], li.[Intitulé dépôt],
    COUNT(DISTINCT li.[Code fournisseur]) AS [Nb Fournisseurs],
    COUNT(DISTINCT li.[N° Pièce]) AS [Nb Documents],
    COUNT(DISTINCT li.[Code article]) AS [Nb Articles],
    SUM(li.[Quantité]) AS [Quantité],
    SUM(li.[Montant HT Net]) AS [Montant HT],
    li.societe AS [Société]
FROM Lignes_des_achats li
WHERE li.[Type Document] IN ('Facture', 'Facture comptabilisée')
  AND li.[Date] BETWEEN @dateDebut AND @dateFin
  AND {SOC_FILTER}
GROUP BY li.[Code dépôt], li.[Intitulé dépôt], li.societe
ORDER BY SUM(li.[Montant HT Net]) DESC""",
        "params": PARAMS_DATE_SOCIETE,
        "category": "achats"
    },

    # ─── 2.3 Rapports Avancés ───
    {
        "code": "DS_ACH_SCORING_FOURNISSEURS",
        "nom": "Scoring Fournisseurs",
        "query": f"""SELECT
    li.[Code fournisseur], li.[Intitulé fournisseur],
    COUNT(DISTINCT li.[N° Pièce]) AS [Nb Commandes],
    SUM(li.[Montant HT Net]) AS [Volume Achats HT],
    AVG(DATEDIFF(day, li.[Date BC], li.[Date BL])) AS [Délai Moyen Livr (j)],
    SUM(CASE WHEN li.[Date BL] > li.[Date Livraison] THEN 1 ELSE 0 END) AS [Nb Retards],
    ROUND(100.0 - 100.0 * SUM(CASE WHEN li.[Date BL] > li.[Date Livraison] THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1) AS [Taux Ponctualité %],
    COUNT(DISTINCT li.[Code article]) AS [Nb Articles Fournis],
    li.societe AS [Société]
FROM Lignes_des_achats li
WHERE li.[Type Document] IN ('Facture', 'Facture comptabilisée')
  AND li.[Date] BETWEEN @dateDebut AND @dateFin
  AND {SOC_FILTER}
GROUP BY li.[Code fournisseur], li.[Intitulé fournisseur], li.societe
ORDER BY SUM(li.[Montant HT Net]) DESC""",
        "params": PARAMS_DATE_SOCIETE,
        "category": "achats"
    },
    {
        "code": "DS_ACH_ECARTS_PRIX",
        "nom": "Analyse des Ecarts de Prix",
        "query": f"""SELECT
    li.[Code article], li.[Désignation],
    COUNT(DISTINCT li.[Code fournisseur]) AS [Nb Fournisseurs],
    MIN(li.[Prix unitaire]) AS [Prix Min],
    MAX(li.[Prix unitaire]) AS [Prix Max],
    AVG(li.[Prix unitaire]) AS [Prix Moyen],
    MAX(li.[Prix unitaire]) - MIN(li.[Prix unitaire]) AS [Ecart Abs],
    CASE WHEN AVG(li.[Prix unitaire]) > 0
        THEN ROUND(100.0 * (MAX(li.[Prix unitaire]) - MIN(li.[Prix unitaire])) / AVG(li.[Prix unitaire]), 1)
        ELSE 0 END AS [Ecart %],
    SUM(li.[Quantité]) AS [Qté Totale],
    SUM(li.[Montant HT Net]) AS [Montant HT],
    li.societe AS [Société]
FROM Lignes_des_achats li
WHERE li.[Type Document] IN ('Facture', 'Facture comptabilisée')
  AND li.[Date] BETWEEN @dateDebut AND @dateFin
  AND {SOC_FILTER}
GROUP BY li.[Code article], li.[Désignation], li.societe
HAVING COUNT(DISTINCT li.[Code fournisseur]) > 1
ORDER BY (MAX(li.[Prix unitaire]) - MIN(li.[Prix unitaire])) DESC""",
        "params": PARAMS_DATE_SOCIETE,
        "category": "achats"
    },
    {
        "code": "DS_ACH_DEPENDANCE_FOURNISSEUR",
        "nom": "Dépendance Fournisseur",
        "query": f"""SELECT
    li.[Code fournisseur], li.[Intitulé fournisseur],
    SUM(li.[Montant HT Net]) AS [Montant HT],
    ROUND(100.0 * SUM(li.[Montant HT Net]) / NULLIF((SELECT SUM(l2.[Montant HT Net]) FROM Lignes_des_achats l2 WHERE l2.[Type Document] IN ('Facture','Facture comptabilisée') AND l2.[Date] BETWEEN @dateDebut AND @dateFin AND (@societe IS NULL OR l2.societe = @societe)), 0), 2) AS [Part Achats %],
    COUNT(DISTINCT li.[Code article]) AS [Nb Articles Exclusifs],
    COUNT(DISTINCT li.[N° Pièce]) AS [Nb Documents],
    li.societe AS [Société]
FROM Lignes_des_achats li
WHERE li.[Type Document] IN ('Facture', 'Facture comptabilisée')
  AND li.[Date] BETWEEN @dateDebut AND @dateFin
  AND {SOC_FILTER}
GROUP BY li.[Code fournisseur], li.[Intitulé fournisseur], li.societe
ORDER BY SUM(li.[Montant HT Net]) DESC""",
        "params": PARAMS_DATE_SOCIETE,
        "category": "achats"
    },
    {
        "code": "DS_ACH_DELAI_MOYEN",
        "nom": "Délai Moyen de Livraison",
        "query": f"""SELECT
    FORMAT(li.[Date BL], 'yyyy-MM') AS [Période],
    li.[Code fournisseur], li.[Intitulé fournisseur],
    COUNT(*) AS [Nb Lignes],
    AVG(DATEDIFF(day, li.[Date BC], li.[Date BL])) AS [Délai Moyen (j)],
    MIN(DATEDIFF(day, li.[Date BC], li.[Date BL])) AS [Délai Min (j)],
    MAX(DATEDIFF(day, li.[Date BC], li.[Date BL])) AS [Délai Max (j)],
    li.societe AS [Société]
FROM Lignes_des_achats li
WHERE li.[Type Document] = 'Bon de livraison'
  AND li.[Date BC] IS NOT NULL AND li.[Date BL] IS NOT NULL
  AND li.[Date BL] BETWEEN @dateDebut AND @dateFin
  AND {SOC_FILTER}
GROUP BY FORMAT(li.[Date BL], 'yyyy-MM'), li.[Code fournisseur], li.[Intitulé fournisseur], li.societe
ORDER BY FORMAT(li.[Date BL], 'yyyy-MM') DESC""",
        "params": PARAMS_DATE_SOCIETE,
        "category": "achats"
    },
    {
        "code": "DS_ACH_CONFORMITE",
        "nom": "Taux de Conformité Réception",
        "query": f"""SELECT
    li.[Code fournisseur], li.[Intitulé fournisseur],
    COUNT(*) AS [Nb Réceptions],
    SUM(CASE WHEN ABS(li.[Quantité] - ISNULL(li.[Quantité PL], li.[Quantité])) < 0.01 THEN 1 ELSE 0 END) AS [Conformes],
    SUM(CASE WHEN ABS(li.[Quantité] - ISNULL(li.[Quantité PL], li.[Quantité])) >= 0.01 THEN 1 ELSE 0 END) AS [Non Conformes],
    ROUND(100.0 * SUM(CASE WHEN ABS(li.[Quantité] - ISNULL(li.[Quantité PL], li.[Quantité])) < 0.01 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1) AS [Taux Conformité %],
    li.societe AS [Société]
FROM Lignes_des_achats li
WHERE li.[Type Document] = 'Bon de livraison'
  AND li.[Date] BETWEEN @dateDebut AND @dateFin
  AND {SOC_FILTER}
GROUP BY li.[Code fournisseur], li.[Intitulé fournisseur], li.societe
ORDER BY ROUND(100.0 * SUM(CASE WHEN ABS(li.[Quantité] - ISNULL(li.[Quantité PL], li.[Quantité])) < 0.01 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1)""",
        "params": PARAMS_DATE_SOCIETE,
        "category": "achats"
    },
    {
        "code": "DS_ACH_PREVISION",
        "nom": "Prévision des Achats",
        "query": f"""SELECT
    YEAR(li.[Date]) AS [Année], MONTH(li.[Date]) AS [Mois],
    FORMAT(li.[Date], 'yyyy-MM') AS [Période],
    li.[Catalogue 1] AS [Famille],
    SUM(li.[Montant HT Net]) AS [Montant HT],
    SUM(li.[Quantité]) AS [Quantité],
    COUNT(DISTINCT li.[Code fournisseur]) AS [Nb Fournisseurs],
    li.societe AS [Société]
FROM Lignes_des_achats li
WHERE li.[Type Document] IN ('Facture', 'Facture comptabilisée')
  AND li.[Date] BETWEEN @dateDebut AND @dateFin
  AND {SOC_FILTER}
GROUP BY YEAR(li.[Date]), MONTH(li.[Date]), FORMAT(li.[Date], 'yyyy-MM'), li.[Catalogue 1], li.societe
ORDER BY YEAR(li.[Date]), MONTH(li.[Date])""",
        "params": PARAMS_DATE_SOCIETE,
        "category": "achats"
    },
    {
        "code": "DS_ACH_VS_BUDGET",
        "nom": "Achats vs Budget",
        "query": f"""SELECT
    FORMAT(li.[Date], 'yyyy-MM') AS [Période],
    li.[Catalogue 1] AS [Famille],
    SUM(li.[Montant HT Net]) AS [Réalisé HT],
    SUM(li.[Quantité]) AS [Quantité],
    COUNT(DISTINCT li.[N° Pièce]) AS [Nb Documents],
    COUNT(DISTINCT li.[Code fournisseur]) AS [Nb Fournisseurs],
    li.societe AS [Société]
FROM Lignes_des_achats li
WHERE li.[Type Document] IN ('Facture', 'Facture comptabilisée')
  AND li.[Date] BETWEEN @dateDebut AND @dateFin
  AND {SOC_FILTER}
GROUP BY FORMAT(li.[Date], 'yyyy-MM'), li.[Catalogue 1], li.societe
ORDER BY FORMAT(li.[Date], 'yyyy-MM')""",
        "params": PARAMS_DATE_SOCIETE,
        "category": "achats"
    },
    {
        "code": "DS_ACH_LITIGES",
        "nom": "Analyse des Litiges Fournisseurs",
        "query": f"""SELECT
    li.[N° Pièce], li.[Date], li.[Type Document],
    li.[Code fournisseur], li.[Intitulé fournisseur],
    li.[Code article], li.[Désignation],
    li.[Quantité], li.[Montant HT Net], li.[Montant TTC Net],
    en.Statut, en.[Entête 1] AS [Motif],
    li.societe
FROM Lignes_des_achats li
INNER JOIN [Entête_des_achats] en ON li.societe = en.societe AND li.[Type Document] = en.[Type Document] AND li.[N° Pièce] = en.[N° pièce]
WHERE li.[Type Document] IN ('Facture avoir', 'Facture avoir comptabilisée', 'Bon de retour', 'Facture de retour', 'Facture de retour comptabilisée')
  AND li.[Date] BETWEEN @dateDebut AND @dateFin
  AND {SOC_FILTER}
ORDER BY li.[Date] DESC""",
        "params": PARAMS_DATE_SOCIETE,
        "category": "achats"
    },
    {
        "code": "DS_ACH_COUT_ACQUISITION",
        "nom": "Coût Total d'Acquisition",
        "query": f"""SELECT
    li.[Code article], li.[Désignation], li.[Catalogue 1] AS [Famille],
    SUM(li.[Quantité]) AS [Quantité],
    SUM(li.[Montant HT Net]) AS [Montant HT Achat],
    SUM(li.[Frais d'approche] * li.[Quantité]) AS [Frais Approche],
    SUM(li.[Montant HT Net]) + SUM(ISNULL(li.[Frais d'approche], 0) * li.[Quantité]) AS [Coût Total],
    CASE WHEN SUM(li.[Quantité]) > 0
        THEN (SUM(li.[Montant HT Net]) + SUM(ISNULL(li.[Frais d'approche], 0) * li.[Quantité])) / SUM(li.[Quantité])
        ELSE 0 END AS [Coût Unitaire Moyen],
    li.societe AS [Société]
FROM Lignes_des_achats li
WHERE li.[Type Document] IN ('Facture', 'Facture comptabilisée')
  AND li.[Date] BETWEEN @dateDebut AND @dateFin
  AND {SOC_FILTER}
GROUP BY li.[Code article], li.[Désignation], li.[Catalogue 1], li.societe
ORDER BY SUM(li.[Montant HT Net]) DESC""",
        "params": PARAMS_DATE_SOCIETE,
        "category": "achats"
    },
    {
        "code": "DS_ACH_MULTI_FOURNISSEURS",
        "nom": "Articles Multi-Fournisseurs",
        "query": f"""SELECT
    li.[Code article], li.[Désignation], li.[Catalogue 1] AS [Famille],
    COUNT(DISTINCT li.[Code fournisseur]) AS [Nb Fournisseurs],
    STRING_AGG(DISTINCT li.[Intitulé fournisseur], ', ') AS [Fournisseurs],
    MIN(li.[Prix unitaire]) AS [Prix Min],
    MAX(li.[Prix unitaire]) AS [Prix Max],
    AVG(li.[Prix unitaire]) AS [Prix Moyen],
    SUM(li.[Quantité]) AS [Quantité Totale],
    SUM(li.[Montant HT Net]) AS [Montant HT],
    li.societe AS [Société]
FROM Lignes_des_achats li
WHERE li.[Type Document] IN ('Facture', 'Facture comptabilisée')
  AND li.[Date] BETWEEN @dateDebut AND @dateFin
  AND {SOC_FILTER}
GROUP BY li.[Code article], li.[Désignation], li.[Catalogue 1], li.societe
HAVING COUNT(DISTINCT li.[Code fournisseur]) > 1
ORDER BY COUNT(DISTINCT li.[Code fournisseur]) DESC""",
        "params": PARAMS_DATE_SOCIETE,
        "category": "achats"
    },
]

# ═══════════════════════════════════════════════════════════════
# REPORTS DEFINITION: type, DS code, nom
# ═══════════════════════════════════════════════════════════════
# 8 GRID
GRIDVIEWS = [
    ("DS_ACH_FACTURES",  "Factures Fournisseurs"),
    ("DS_ACH_BL",        "Bons de Réception"),
    ("DS_ACH_BC",        "Bons de Commande Fournisseurs"),
    ("DS_ACH_DA",        "Demandes d'Achat"),
    ("DS_ACH_AVOIRS",    "Avoirs Fournisseurs"),
    ("DS_ACH_RETOURS",   "Bons de Retour Fournisseurs"),
    ("DS_ACH_COMMANDES_EN_COURS", "Commandes en Cours Fournisseurs"),
    ("DS_ACH_LITIGES",   "Analyse des Litiges Fournisseurs"),
]

# 8 PIVOT
PIVOTS = [
    ("DS_ACH_PAR_FOURNISSEUR", "Achats par Fournisseur",
     [{"field":"Code fournisseur","label":"Fournisseur","type":"text"},{"field":"Intitulé fournisseur","label":"Nom Fournisseur","type":"text"}],
     [{"field":"Montant HT","label":"Montant HT","aggregation":"SUM","format":"currency","decimals":2},{"field":"Quantité","label":"Quantité","aggregation":"SUM","format":"number","decimals":0}],
     [{"field":"Société","label":"Société","type":"select"}]),
    ("DS_ACH_PAR_ARTICLE", "Achats par Article",
     [{"field":"Code article","label":"Article","type":"text"},{"field":"Désignation","label":"Désignation","type":"text"},{"field":"Famille","label":"Famille","type":"text"}],
     [{"field":"Montant HT","label":"Montant HT","aggregation":"SUM","format":"currency","decimals":2},{"field":"Quantité","label":"Quantité","aggregation":"SUM","format":"number","decimals":0},{"field":"Prix Moyen","label":"Prix Moyen","aggregation":"AVG","format":"currency","decimals":2}],
     [{"field":"Famille","label":"Famille","type":"select"}]),
    ("DS_ACH_PAR_FAMILLE", "Achats par Famille Article",
     [{"field":"Famille","label":"Famille","type":"text"},{"field":"Sous-Famille","label":"Sous-Famille","type":"text"}],
     [{"field":"Montant HT","label":"Montant HT","aggregation":"SUM","format":"currency","decimals":2},{"field":"Quantité","label":"Quantité","aggregation":"SUM","format":"number","decimals":0},{"field":"Nb Articles","label":"Nb Articles","aggregation":"SUM","format":"number","decimals":0}],
     [{"field":"Société","label":"Société","type":"select"}]),
    ("DS_ACH_COMPARATIF_PRIX", "Comparatif Prix d'Achat",
     [{"field":"Code article","label":"Article","type":"text"},{"field":"Code fournisseur","label":"Fournisseur","type":"text"}],
     [{"field":"Prix Moyen","label":"Prix Moyen","aggregation":"AVG","format":"currency","decimals":2},{"field":"Ecart Prix","label":"Ecart Prix","aggregation":"SUM","format":"currency","decimals":2},{"field":"Montant HT","label":"Montant HT","aggregation":"SUM","format":"currency","decimals":2}],
     [{"field":"Société","label":"Société","type":"select"}]),
    ("DS_ACH_PAR_DEPOT", "Achats par Dépôt",
     [{"field":"Code dépôt","label":"Dépôt","type":"text"},{"field":"Intitulé dépôt","label":"Nom Dépôt","type":"text"}],
     [{"field":"Montant HT","label":"Montant HT","aggregation":"SUM","format":"currency","decimals":2},{"field":"Quantité","label":"Quantité","aggregation":"SUM","format":"number","decimals":0},{"field":"Nb Fournisseurs","label":"Nb Fournisseurs","aggregation":"SUM","format":"number","decimals":0}],
     [{"field":"Société","label":"Société","type":"select"}]),
    ("DS_ACH_ECARTS_PRIX", "Analyse des Ecarts de Prix",
     [{"field":"Code article","label":"Article","type":"text"},{"field":"Désignation","label":"Désignation","type":"text"}],
     [{"field":"Prix Min","label":"Prix Min","aggregation":"MIN","format":"currency","decimals":2},{"field":"Prix Max","label":"Prix Max","aggregation":"MAX","format":"currency","decimals":2},{"field":"Ecart %","label":"Ecart %","aggregation":"AVG","format":"number","decimals":1},{"field":"Montant HT","label":"Montant HT","aggregation":"SUM","format":"currency","decimals":2}],
     [{"field":"Société","label":"Société","type":"select"}]),
    ("DS_ACH_COUT_ACQUISITION", "Coût Total d'Acquisition",
     [{"field":"Code article","label":"Article","type":"text"},{"field":"Famille","label":"Famille","type":"text"}],
     [{"field":"Montant HT Achat","label":"Montant HT","aggregation":"SUM","format":"currency","decimals":2},{"field":"Frais Approche","label":"Frais Approche","aggregation":"SUM","format":"currency","decimals":2},{"field":"Coût Total","label":"Coût Total","aggregation":"SUM","format":"currency","decimals":2},{"field":"Coût Unitaire Moyen","label":"CU Moyen","aggregation":"AVG","format":"currency","decimals":2}],
     [{"field":"Famille","label":"Famille","type":"select"}]),
    ("DS_ACH_MULTI_FOURNISSEURS", "Articles Multi-Fournisseurs",
     [{"field":"Code article","label":"Article","type":"text"},{"field":"Désignation","label":"Désignation","type":"text"},{"field":"Famille","label":"Famille","type":"text"}],
     [{"field":"Nb Fournisseurs","label":"Nb Fourn.","aggregation":"SUM","format":"number","decimals":0},{"field":"Prix Min","label":"Prix Min","aggregation":"MIN","format":"currency","decimals":2},{"field":"Prix Max","label":"Prix Max","aggregation":"MAX","format":"currency","decimals":2},{"field":"Montant HT","label":"Montant HT","aggregation":"SUM","format":"currency","decimals":2}],
     [{"field":"Famille","label":"Famille","type":"select"}]),
]

# 9 DASHBOARD
DASHBOARDS = [
    ("DS_ACH_EVOLUTION_MENSUELLE", "Evolution Achats Mensuelle", [
        {"id":"w_ach_evol_kpi_mt","type":"kpi","title":"Total Achats HT","x":0,"y":0,"w":3,"h":3,"config":{"dataSourceCode":"DS_ACH_EVOLUTION_MENSUELLE","dataSourceOrigin":"template","value_field":"Montant HT","aggregation":"SUM","suffix":" DH","kpi_color":"#ef4444","subtitle":"Montant HT Total"}},
        {"id":"w_ach_evol_kpi_doc","type":"kpi","title":"Nb Documents","x":3,"y":0,"w":3,"h":3,"config":{"dataSourceCode":"DS_ACH_EVOLUTION_MENSUELLE","dataSourceOrigin":"template","value_field":"Nb Documents","aggregation":"SUM","kpi_color":"#f59e0b","subtitle":"Total Documents"}},
        {"id":"w_ach_evol_bar","type":"chart_bar","title":"Achats Mensuels","x":0,"y":3,"w":8,"h":5,"config":{"dataSourceCode":"DS_ACH_EVOLUTION_MENSUELLE","dataSourceOrigin":"template","x_field":"Période","y_field":"Montant HT","color":"#ef4444","show_grid":True,"show_legend":True}},
        {"id":"w_ach_evol_line","type":"chart_line","title":"Evolution Nb Fournisseurs","x":8,"y":3,"w":4,"h":5,"config":{"dataSourceCode":"DS_ACH_EVOLUTION_MENSUELLE","dataSourceOrigin":"template","x_field":"Période","y_field":"Nb Fournisseurs","color":"#8b5cf6","show_grid":True}},
    ]),
    ("DS_ACH_TOP20_FOURNISSEURS", "Top 20 Fournisseurs", [
        {"id":"w_ach_top_kpi","type":"kpi","title":"Montant Total HT","x":0,"y":0,"w":4,"h":3,"config":{"dataSourceCode":"DS_ACH_TOP20_FOURNISSEURS","dataSourceOrigin":"template","value_field":"Montant HT","aggregation":"SUM","suffix":" DH","kpi_color":"#ef4444"}},
        {"id":"w_ach_top_bar","type":"chart_bar","title":"Top 20 par Montant HT","x":0,"y":3,"w":8,"h":6,"config":{"dataSourceCode":"DS_ACH_TOP20_FOURNISSEURS","dataSourceOrigin":"template","x_field":"Intitulé fournisseur","y_field":"Montant HT","color":"#ef4444","horizontal":True,"show_labels":True}},
        {"id":"w_ach_top_pie","type":"chart_pie","title":"Répartition Achats","x":8,"y":3,"w":4,"h":6,"config":{"dataSourceCode":"DS_ACH_TOP20_FOURNISSEURS","dataSourceOrigin":"template","label_field":"Intitulé fournisseur","value_field":"Montant HT","donut":True,"show_legend":False}},
        {"id":"w_ach_top_table","type":"table","title":"Détail Fournisseurs","x":0,"y":9,"w":12,"h":5,"config":{"dataSourceCode":"DS_ACH_TOP20_FOURNISSEURS","dataSourceOrigin":"template","visible_columns":["Code fournisseur","Intitulé fournisseur","Nb Factures","Montant HT","% du Total"]}},
    ]),
    ("DS_ACH_DELAI_LIVRAISON", "Analyse Délais Livraison Fournisseurs", [
        {"id":"w_ach_del_kpi_moy","type":"kpi","title":"Délai Moyen Global","x":0,"y":0,"w":3,"h":3,"config":{"dataSourceCode":"DS_ACH_DELAI_LIVRAISON","dataSourceOrigin":"template","value_field":"Délai Moyen (j)","aggregation":"AVG","suffix":" j","kpi_color":"#f59e0b"}},
        {"id":"w_ach_del_kpi_ret","type":"kpi","title":"Taux de Retard","x":3,"y":0,"w":3,"h":3,"config":{"dataSourceCode":"DS_ACH_DELAI_LIVRAISON","dataSourceOrigin":"template","value_field":"% Retard","aggregation":"AVG","suffix":" %","kpi_color":"#ef4444"}},
        {"id":"w_ach_del_bar","type":"chart_bar","title":"Délai Moyen par Fournisseur","x":0,"y":3,"w":12,"h":5,"config":{"dataSourceCode":"DS_ACH_DELAI_LIVRAISON","dataSourceOrigin":"template","x_field":"Intitulé fournisseur","y_field":"Délai Moyen (j)","color":"#f59e0b","show_grid":True,"sort_field":"Délai Moyen (j)","sort_direction":"desc","limit_rows":15}},
        {"id":"w_ach_del_table","type":"table","title":"Détail Délais","x":0,"y":8,"w":12,"h":5,"config":{"dataSourceCode":"DS_ACH_DELAI_LIVRAISON","dataSourceOrigin":"template"}},
    ]),
    ("DS_ACH_SCORING_FOURNISSEURS", "Scoring Fournisseurs", [
        {"id":"w_ach_scr_kpi_nb","type":"kpi","title":"Nb Fournisseurs","x":0,"y":0,"w":3,"h":3,"config":{"dataSourceCode":"DS_ACH_SCORING_FOURNISSEURS","dataSourceOrigin":"template","value_field":"Nb Commandes","aggregation":"COUNT","kpi_color":"#3b82f6"}},
        {"id":"w_ach_scr_kpi_vol","type":"kpi","title":"Volume Total Achats","x":3,"y":0,"w":3,"h":3,"config":{"dataSourceCode":"DS_ACH_SCORING_FOURNISSEURS","dataSourceOrigin":"template","value_field":"Volume Achats HT","aggregation":"SUM","suffix":" DH","kpi_color":"#ef4444"}},
        {"id":"w_ach_scr_bar","type":"chart_bar","title":"Volume Achats par Fournisseur","x":0,"y":3,"w":8,"h":5,"config":{"dataSourceCode":"DS_ACH_SCORING_FOURNISSEURS","dataSourceOrigin":"template","x_field":"Intitulé fournisseur","y_field":"Volume Achats HT","color":"#ef4444","sort_field":"Volume Achats HT","sort_direction":"desc","limit_rows":15}},
        {"id":"w_ach_scr_ponc","type":"chart_bar","title":"Taux Ponctualité","x":8,"y":3,"w":4,"h":5,"config":{"dataSourceCode":"DS_ACH_SCORING_FOURNISSEURS","dataSourceOrigin":"template","x_field":"Intitulé fournisseur","y_field":"Taux Ponctualité %","color":"#10b981","sort_field":"Taux Ponctualité %","sort_direction":"asc","limit_rows":15}},
        {"id":"w_ach_scr_table","type":"table","title":"Détail Scoring","x":0,"y":8,"w":12,"h":5,"config":{"dataSourceCode":"DS_ACH_SCORING_FOURNISSEURS","dataSourceOrigin":"template"}},
    ]),
    ("DS_ACH_DEPENDANCE_FOURNISSEUR", "Dépendance Fournisseur", [
        {"id":"w_ach_dep_pie","type":"chart_pie","title":"Part des Achats par Fournisseur","x":0,"y":0,"w":6,"h":6,"config":{"dataSourceCode":"DS_ACH_DEPENDANCE_FOURNISSEUR","dataSourceOrigin":"template","label_field":"Intitulé fournisseur","value_field":"Montant HT","donut":True,"show_legend":True,"limit_rows":10}},
        {"id":"w_ach_dep_bar","type":"chart_bar","title":"Part Achats % Top Fournisseurs","x":6,"y":0,"w":6,"h":6,"config":{"dataSourceCode":"DS_ACH_DEPENDANCE_FOURNISSEUR","dataSourceOrigin":"template","x_field":"Intitulé fournisseur","y_field":"Part Achats %","color":"#f59e0b","horizontal":True,"show_labels":True,"limit_rows":10}},
        {"id":"w_ach_dep_table","type":"table","title":"Détail Dépendance","x":0,"y":6,"w":12,"h":5,"config":{"dataSourceCode":"DS_ACH_DEPENDANCE_FOURNISSEUR","dataSourceOrigin":"template"}},
    ]),
    ("DS_ACH_DELAI_MOYEN", "Délai Moyen de Livraison", [
        {"id":"w_ach_dmo_kpi","type":"kpi","title":"Délai Moyen Global","x":0,"y":0,"w":4,"h":3,"config":{"dataSourceCode":"DS_ACH_DELAI_MOYEN","dataSourceOrigin":"template","value_field":"Délai Moyen (j)","aggregation":"AVG","suffix":" jours","kpi_color":"#f59e0b"}},
        {"id":"w_ach_dmo_line","type":"chart_line","title":"Evolution Délai Moyen","x":0,"y":3,"w":12,"h":5,"config":{"dataSourceCode":"DS_ACH_DELAI_MOYEN","dataSourceOrigin":"template","x_field":"Période","y_field":"Délai Moyen (j)","color":"#f59e0b","show_grid":True}},
        {"id":"w_ach_dmo_table","type":"table","title":"Détail par Fournisseur","x":0,"y":8,"w":12,"h":5,"config":{"dataSourceCode":"DS_ACH_DELAI_MOYEN","dataSourceOrigin":"template"}},
    ]),
    ("DS_ACH_CONFORMITE", "Taux de Conformité Réception", [
        {"id":"w_ach_conf_kpi","type":"kpi","title":"Taux Conformité Global","x":0,"y":0,"w":4,"h":3,"config":{"dataSourceCode":"DS_ACH_CONFORMITE","dataSourceOrigin":"template","value_field":"Taux Conformité %","aggregation":"AVG","suffix":" %","kpi_color":"#10b981"}},
        {"id":"w_ach_conf_kpi2","type":"kpi","title":"Réceptions Non Conformes","x":4,"y":0,"w":4,"h":3,"config":{"dataSourceCode":"DS_ACH_CONFORMITE","dataSourceOrigin":"template","value_field":"Non Conformes","aggregation":"SUM","kpi_color":"#ef4444"}},
        {"id":"w_ach_conf_bar","type":"chart_bar","title":"Taux Conformité par Fournisseur","x":0,"y":3,"w":12,"h":5,"config":{"dataSourceCode":"DS_ACH_CONFORMITE","dataSourceOrigin":"template","x_field":"Intitulé fournisseur","y_field":"Taux Conformité %","color":"#10b981","show_grid":True,"sort_field":"Taux Conformité %","sort_direction":"asc","limit_rows":15}},
        {"id":"w_ach_conf_table","type":"table","title":"Détail Conformité","x":0,"y":8,"w":12,"h":5,"config":{"dataSourceCode":"DS_ACH_CONFORMITE","dataSourceOrigin":"template"}},
    ]),
    ("DS_ACH_PREVISION", "Prévision des Achats", [
        {"id":"w_ach_prev_kpi","type":"kpi","title":"Total Achats HT","x":0,"y":0,"w":4,"h":3,"config":{"dataSourceCode":"DS_ACH_PREVISION","dataSourceOrigin":"template","value_field":"Montant HT","aggregation":"SUM","suffix":" DH","kpi_color":"#8b5cf6"}},
        {"id":"w_ach_prev_area","type":"chart_area","title":"Tendance Achats par Famille","x":0,"y":3,"w":12,"h":5,"config":{"dataSourceCode":"DS_ACH_PREVISION","dataSourceOrigin":"template","x_field":"Période","y_field":"Montant HT","color":"#8b5cf6","show_grid":True,"stacked":False}},
        {"id":"w_ach_prev_table","type":"table","title":"Détail par Période/Famille","x":0,"y":8,"w":12,"h":5,"config":{"dataSourceCode":"DS_ACH_PREVISION","dataSourceOrigin":"template"}},
    ]),
    ("DS_ACH_VS_BUDGET", "Achats vs Budget", [
        {"id":"w_ach_bud_kpi","type":"kpi","title":"Réalisé Total HT","x":0,"y":0,"w":4,"h":3,"config":{"dataSourceCode":"DS_ACH_VS_BUDGET","dataSourceOrigin":"template","value_field":"Réalisé HT","aggregation":"SUM","suffix":" DH","kpi_color":"#3b82f6"}},
        {"id":"w_ach_bud_bar","type":"chart_bar","title":"Réalisé par Période","x":0,"y":3,"w":8,"h":5,"config":{"dataSourceCode":"DS_ACH_VS_BUDGET","dataSourceOrigin":"template","x_field":"Période","y_field":"Réalisé HT","color":"#3b82f6","show_grid":True}},
        {"id":"w_ach_bud_pie","type":"chart_pie","title":"Répartition par Famille","x":8,"y":3,"w":4,"h":5,"config":{"dataSourceCode":"DS_ACH_VS_BUDGET","dataSourceOrigin":"template","label_field":"Famille","value_field":"Réalisé HT","donut":True}},
        {"id":"w_ach_bud_table","type":"table","title":"Détail Budget vs Réalisé","x":0,"y":8,"w":12,"h":5,"config":{"dataSourceCode":"DS_ACH_VS_BUDGET","dataSourceOrigin":"template"}},
    ]),
]

# ═══════════════════════════════════════════════════════════════
# MENU ICONS
# ═══════════════════════════════════════════════════════════════
MENU_ICONS = {
    "Factures Fournisseurs": "Receipt",
    "Bons de Réception": "PackageCheck",
    "Bons de Commande Fournisseurs": "ClipboardList",
    "Demandes d'Achat": "FileQuestion",
    "Avoirs Fournisseurs": "RotateCcw",
    "Bons de Retour Fournisseurs": "Repeat",
    "Achats par Fournisseur": "Users",
    "Achats par Article": "Package",
    "Achats par Famille Article": "Boxes",
    "Evolution Achats Mensuelle": "TrendingUp",
    "Top 20 Fournisseurs": "Award",
    "Comparatif Prix d'Achat": "Scale",
    "Commandes en Cours Fournisseurs": "Clock",
    "Analyse Délais Livraison Fournisseurs": "Truck",
    "Achats par Dépôt": "MapPin",
    "Scoring Fournisseurs": "Star",
    "Analyse des Ecarts de Prix": "ArrowUpDown",
    "Dépendance Fournisseur": "AlertTriangle",
    "Délai Moyen de Livraison": "Gauge",
    "Taux de Conformité Réception": "UserCheck",
    "Prévision des Achats": "LineChart",
    "Achats vs Budget": "Target",
    "Analyse des Litiges Fournisseurs": "Zap",
    "Coût Total d'Acquisition": "DollarSign",
    "Articles Multi-Fournisseurs": "GitCompare",
}


def main():
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()

    print("=" * 60)
    print("  CREATION DES 25 RAPPORTS ACHATS")
    print("=" * 60)

    # ─── 1. Insérer les DataSource Templates ───
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

    # ─── 2. Créer les GridViews ───
    print("\n[2/5] Creation des GridViews...")
    gv_ids = {}
    for ds_code, nom in GRIDVIEWS:
        # Vérifier si existe déjà
        cursor.execute("SELECT id FROM APP_GridViews WHERE data_source_code = ?", ds_code)
        existing = cursor.fetchone()
        if existing:
            gv_ids[ds_code] = existing[0]
            print(f"  OK EXISTS {nom} (id={existing[0]})")
            continue

        # Construire les colonnes depuis le template
        cursor.execute("SELECT query_template FROM APP_DataSources_Templates WHERE code = ?", ds_code)
        row = cursor.fetchone()
        if not row:
            print(f"  XX SKIP {nom} - template {ds_code} not found")
            continue

        # Extraire les alias des colonnes depuis le SQL
        import re
        query = row[0]
        # Match patterns like: AS [Column Name] or AS Column
        aliases = re.findall(r'AS\s+\[([^\]]+)\]', query, re.IGNORECASE)
        if not aliases:
            aliases = re.findall(r'AS\s+(\w+)', query, re.IGNORECASE)

        columns = []
        for i, alias in enumerate(aliases[:25]):  # Max 25 colonnes
            col_format = "text"
            align = "left"
            if any(kw in alias.lower() for kw in ["montant", "prix", "marge", "ca ", "coût", "frais"]):
                col_format = "currency"
                align = "right"
            elif any(kw in alias.lower() for kw in ["quantit", "nb ", "nombre"]):
                col_format = "number"
                align = "right"
            elif any(kw in alias.lower() for kw in ["%", "taux", "part "]):
                col_format = "number"
                align = "right"
            elif "date" in alias.lower():
                col_format = "date"

            columns.append({
                "field": alias,
                "header": alias,
                "format": col_format,
                "align": align,
                "sortable": True,
                "filterable": True,
                "visible": True,
                "width": 150
            })

        total_cols = [c["field"] for c in columns if c["format"] in ("currency", "number") and "nb " not in c["field"].lower() and "%" not in c["field"]]

        columns_json = json.dumps(columns)
        total_cols_json = json.dumps(total_cols[:5])
        features_json = json.dumps({"show_search":True,"show_column_filters":True,"show_grouping":True,"show_column_toggle":True,"show_export":True,"show_pagination":True,"allow_sorting":True})

        cursor.execute("""INSERT INTO APP_GridViews
            (nom, description, data_source_code, columns_config, page_size, show_totals, total_columns, features, actif)
            VALUES (?, ?, ?, ?, 25, 1, ?, ?, 1)""",
            nom, f"Rapport Achats - {nom}", ds_code, columns_json, total_cols_json, features_json)
        cursor.execute("SELECT @@IDENTITY")
        gv_id = int(cursor.fetchone()[0])
        gv_ids[ds_code] = gv_id
        print(f"  + NEW GridView {nom} (id={gv_id}, {len(columns)} cols)")
    conn.commit()

    # ─── 3. Créer les Pivots ───
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
            nom, f"Pivot Achats - {nom}", ds_code,
            json.dumps(rows_cfg), json.dumps(vals_cfg), json.dumps(filters_cfg))
        cursor.execute("SELECT @@IDENTITY")
        pv_id = int(cursor.fetchone()[0])
        pv_ids[ds_code] = pv_id
        print(f"  + NEW Pivot {nom} (id={pv_id})")
    conn.commit()

    # ─── 4. Créer les Dashboards ───
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
            nom, f"Dashboard Achats - {nom}", json.dumps(widgets))
        cursor.execute("SELECT @@IDENTITY")
        db_id = int(cursor.fetchone()[0])
        db_ids[ds_code] = db_id
        print(f"  + NEW Dashboard {nom} (id={db_id})")
    conn.commit()

    # ─── 5. Créer les Menus ───
    print("\n[5/5] Creation des Menus...")

    # Menu racine Achats
    cursor.execute("SELECT id FROM APP_Menus WHERE nom = 'Achats' AND parent_id IS NULL")
    root = cursor.fetchone()
    if root:
        root_id = root[0]
        print(f"  OK EXISTS racine 'Achats' (id={root_id})")
    else:
        cursor.execute("""INSERT INTO APP_Menus (nom, icon, type, parent_id, ordre, actif)
            VALUES ('Achats', 'ShoppingCart', 'folder', NULL, 20, 1)""")
        cursor.execute("SELECT @@IDENTITY")
        root_id = int(cursor.fetchone()[0])
        print(f"  + NEW racine 'Achats' (id={root_id})")

    # Sous-dossiers
    subfolders = [
        ("Documents Achats", "FileText", 1),
        ("Analyses Achats", "BarChart3", 2),
        ("Rapports Avancés Achats", "Activity", 3),
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

    # Menu items - regroupés par sous-dossier
    menu_items = [
        # Documents Achats
        ("Documents Achats", "Factures Fournisseurs", "gridview", gv_ids.get("DS_ACH_FACTURES"), 1),
        ("Documents Achats", "Bons de Réception", "gridview", gv_ids.get("DS_ACH_BL"), 2),
        ("Documents Achats", "Bons de Commande Fournisseurs", "gridview", gv_ids.get("DS_ACH_BC"), 3),
        ("Documents Achats", "Demandes d'Achat", "gridview", gv_ids.get("DS_ACH_DA"), 4),
        ("Documents Achats", "Avoirs Fournisseurs", "gridview", gv_ids.get("DS_ACH_AVOIRS"), 5),
        ("Documents Achats", "Bons de Retour Fournisseurs", "gridview", gv_ids.get("DS_ACH_RETOURS"), 6),
        # Analyses Achats
        ("Analyses Achats", "Achats par Fournisseur", "pivot-v2", pv_ids.get("DS_ACH_PAR_FOURNISSEUR"), 1),
        ("Analyses Achats", "Achats par Article", "pivot-v2", pv_ids.get("DS_ACH_PAR_ARTICLE"), 2),
        ("Analyses Achats", "Achats par Famille Article", "pivot-v2", pv_ids.get("DS_ACH_PAR_FAMILLE"), 3),
        ("Analyses Achats", "Evolution Achats Mensuelle", "dashboard", db_ids.get("DS_ACH_EVOLUTION_MENSUELLE"), 4),
        ("Analyses Achats", "Top 20 Fournisseurs", "dashboard", db_ids.get("DS_ACH_TOP20_FOURNISSEURS"), 5),
        ("Analyses Achats", "Comparatif Prix d'Achat", "pivot-v2", pv_ids.get("DS_ACH_COMPARATIF_PRIX"), 6),
        ("Analyses Achats", "Commandes en Cours Fournisseurs", "gridview", gv_ids.get("DS_ACH_COMMANDES_EN_COURS"), 7),
        ("Analyses Achats", "Analyse Délais Livraison Fournisseurs", "dashboard", db_ids.get("DS_ACH_DELAI_LIVRAISON"), 8),
        ("Analyses Achats", "Achats par Dépôt", "pivot-v2", pv_ids.get("DS_ACH_PAR_DEPOT"), 9),
        # Rapports Avancés
        ("Rapports Avancés Achats", "Scoring Fournisseurs", "dashboard", db_ids.get("DS_ACH_SCORING_FOURNISSEURS"), 1),
        ("Rapports Avancés Achats", "Analyse des Ecarts de Prix", "pivot-v2", pv_ids.get("DS_ACH_ECARTS_PRIX"), 2),
        ("Rapports Avancés Achats", "Dépendance Fournisseur", "dashboard", db_ids.get("DS_ACH_DEPENDANCE_FOURNISSEUR"), 3),
        ("Rapports Avancés Achats", "Délai Moyen de Livraison", "dashboard", db_ids.get("DS_ACH_DELAI_MOYEN"), 4),
        ("Rapports Avancés Achats", "Taux de Conformité Réception", "dashboard", db_ids.get("DS_ACH_CONFORMITE"), 5),
        ("Rapports Avancés Achats", "Prévision des Achats", "dashboard", db_ids.get("DS_ACH_PREVISION"), 6),
        ("Rapports Avancés Achats", "Achats vs Budget", "dashboard", db_ids.get("DS_ACH_VS_BUDGET"), 7),
        ("Rapports Avancés Achats", "Analyse des Litiges Fournisseurs", "gridview", gv_ids.get("DS_ACH_LITIGES"), 8),
        ("Rapports Avancés Achats", "Coût Total d'Acquisition", "pivot-v2", pv_ids.get("DS_ACH_COUT_ACQUISITION"), 9),
        ("Rapports Avancés Achats", "Articles Multi-Fournisseurs", "pivot-v2", pv_ids.get("DS_ACH_MULTI_FOURNISSEURS"), 10),
    ]

    menu_count = 0
    for sf_label, label, menu_type, target_id, ordre in menu_items:
        if target_id is None:
            print(f"  XX SKIP menu '{label}' - target_id manquant")
            continue

        parent_id = sf_ids[sf_label]
        icon = MENU_ICONS.get(label, "FileText")

        # Verifier si existe
        cursor.execute("SELECT id FROM APP_Menus WHERE nom = ? AND parent_id = ?", label, parent_id)
        existing = cursor.fetchone()
        if existing:
            # Mettre a jour avec target_id (pas url)
            cursor.execute("""UPDATE APP_Menus SET icon=?, type=?, target_id=?, ordre=?, actif=1
                WHERE id=?""", icon, menu_type, target_id, ordre, existing[0])
            print(f"  OK MAJ '{label}' ({menu_type} -> id {target_id})")
        else:
            cursor.execute("""INSERT INTO APP_Menus (nom, icon, type, target_id, parent_id, ordre, actif)
                VALUES (?, ?, ?, ?, ?, ?, 1)""", label, icon, menu_type, target_id, parent_id, ordre)
            print(f"  + NEW '{label}' ({menu_type} -> id {target_id})")
        menu_count += 1

    conn.commit()

    # ─── Résumé ───
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
