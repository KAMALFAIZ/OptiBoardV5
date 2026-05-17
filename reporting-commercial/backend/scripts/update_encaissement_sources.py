# -*- coding: utf-8 -*-
"""
Remplace les requêtes encaissement dans APP_DataSources_Templates :
  - 7 sources pures : Imputation_Factures_Ventes → Réglements_Clients
  - 1 hybride     : DS_TB_ENCAISSEMENTS_MOIS garde Échéances_Ventes + RC
  - 1 partielle   : DS_KPI_RECOUVREMENT — sous-requête Reglements Mois → RC
  - 2 inchangées  : DS_TB_SYNTHESE_RECOUVREMENT, DS_REC_KPI_GLOBAL (calculs d'encours)
"""
import sys
import pyodbc

CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=kasoft.selfip.net;"
    "DATABASE=OptiBoard_SaaS;"
    "UID=sa;PWD=SQL@2019;"
    "TrustServerCertificate=yes"
)

# ---------------------------------------------------------------------------
# Nouvelles requêtes
# ---------------------------------------------------------------------------

Q_TB_ENCAISSEMENTS_MOIS = """\
WITH
Enc AS (
    SELECT
        FORMAT([Date], 'yyyy-MM') AS [Mois],
        SUM([Montant]) AS [Encaisse]
    FROM [Réglements_Clients]
    WHERE [Date] BETWEEN @dateDebut AND @dateFin
      AND (@societe IS NULL OR [societe] = @societe)
      AND [Valide] = 'Oui'
    GROUP BY FORMAT([Date], 'yyyy-MM')
),
Ech AS (
    SELECT
        FORMAT([Date d'échéance], 'yyyy-MM') AS [Mois],
        SUM([Montant échéance]) AS [Echeances]
    FROM [Échéances_Ventes]
    WHERE [Date d'échéance] BETWEEN @dateDebut AND @dateFin
      AND (@societe IS NULL OR [societe] = @societe)
    GROUP BY FORMAT([Date d'échéance], 'yyyy-MM')
)
SELECT
    COALESCE(h.[Mois], e.[Mois]) AS [Mois],
    DATENAME(MONTH, CAST(COALESCE(h.[Mois], e.[Mois]) + '-01' AS DATE))
        + ' ' + CAST(YEAR(CAST(COALESCE(h.[Mois], e.[Mois]) + '-01' AS DATE)) AS VARCHAR) AS [Periode],
    ISNULL(h.[Echeances], 0) AS [Echeances],
    ISNULL(e.[Encaisse], 0) AS [Encaisse],
    ISNULL(h.[Echeances], 0) - ISNULL(e.[Encaisse], 0) AS [Reste]
FROM Ech h
FULL OUTER JOIN Enc e ON h.[Mois] = e.[Mois]
ORDER BY [Mois]"""

Q_REC_ENCAISSEMENTS_MENS = """\
SELECT
    YEAR(r.[Date]) AS [Annee],
    MONTH(r.[Date]) AS [Mois],
    CAST(YEAR(r.[Date]) AS VARCHAR) + '-' + RIGHT('0' + CAST(MONTH(r.[Date]) AS VARCHAR), 2) AS [Periode],
    SUM(r.[Montant]) AS [Total Encaisse],
    COUNT(DISTINCT r.[N° pièce]) AS [Nb Règlements],
    COUNT(DISTINCT r.[Code client]) AS [Nb Clients],
    r.[societe] AS [Société]
FROM [Réglements_Clients] r
WHERE r.[Date] BETWEEN @dateDebut AND @dateFin
  AND (@societe IS NULL OR r.[societe] = @societe)
  AND r.[Valide] = 'Oui'
GROUP BY YEAR(r.[Date]), MONTH(r.[Date]), r.[societe]
ORDER BY YEAR(r.[Date]), MONTH(r.[Date])"""

Q_REGLEMENTS_PAR_PERIODE = """\
SELECT
    YEAR([Date]) AS [Annee],
    MONTH([Date]) AS [Mois],
    FORMAT([Date], 'yyyy-MM') AS [Periode],
    COUNT(DISTINCT [N° pièce]) AS [Nb Règlements],
    SUM([Montant]) AS [Total Règlements],
    COUNT(DISTINCT [Code client]) AS [Nb Clients]
FROM [Réglements_Clients]
WHERE [Date] BETWEEN @dateDebut AND @dateFin
  AND (@societe IS NULL OR [societe] = @societe)
  AND [Valide] = 'Oui'
GROUP BY YEAR([Date]), MONTH([Date]), FORMAT([Date], 'yyyy-MM')
ORDER BY [Annee], [Mois]"""

Q_REGLEMENTS_PAR_CLIENT = """\
SELECT
    [Code client] AS [Code Client],
    [Intitulé] AS [Client],
    [societe] AS [Société],
    COUNT(DISTINCT [N° pièce]) AS [Nb Règlements],
    SUM([Montant]) AS [Total Réglé],
    MIN([Date]) AS [Premier Règlement],
    MAX([Date]) AS [Dernier Règlement]
FROM [Réglements_Clients]
WHERE [Date] IS NOT NULL
  AND (@societe IS NULL OR [societe] = @societe)
  AND [Valide] = 'Oui'
GROUP BY [Code client], [Intitulé], [societe]
ORDER BY SUM([Montant]) DESC"""

Q_REGLEMENTS_PAR_MODE = """\
SELECT
    [Mode de règlement] AS [Mode de Règlement],
    COUNT(DISTINCT [N° pièce]) AS [Nb Règlements],
    SUM([Montant]) AS [Total Réglé],
    COUNT(DISTINCT [Code client]) AS [Nb Clients]
FROM [Réglements_Clients]
WHERE [Date] BETWEEN @dateDebut AND @dateFin
  AND (@societe IS NULL OR [societe] = @societe)
  AND [Valide] = 'Oui'
GROUP BY [Mode de règlement]
ORDER BY SUM([Montant]) DESC"""

Q_REC_REGLEMENTS = """\
SELECT
    r.[Code client],
    r.[Intitulé] AS [Client],
    r.[N° pièce] AS [Numéro Pièce],
    r.[Date] AS [Date Règlement],
    r.[Montant] AS [Montant Règlement],
    r.[Mode de règlement] AS [Mode de Règlement],
    r.[Date d'échéance] AS [Date Echéance],
    r.[societe] AS [Société]
FROM [Réglements_Clients] r
WHERE r.[Date] BETWEEN @dateDebut AND @dateFin
  AND (@societe IS NULL OR r.[societe] = @societe)
  AND r.[Valide] = 'Oui'
ORDER BY r.[Date] DESC"""

Q_REC_HISTORIQUE_CLIENT = """\
SELECT
    r.[Code client],
    r.[Intitulé] AS [Client],
    r.[N° pièce] AS [Numéro Pièce],
    r.[Date] AS [Date Règlement],
    r.[Montant] AS [Montant Règlement],
    r.[Mode de règlement] AS [Mode de Règlement],
    r.[Date d'échéance] AS [Date Echéance],
    DATEDIFF(day, r.[Date d'échéance], r.[Date]) AS [Délai Règlement Jours],
    r.[societe] AS [Société]
FROM [Réglements_Clients] r
WHERE r.[Date] IS NOT NULL
  AND r.[Date] BETWEEN @dateDebut AND @dateFin
  AND (@societe IS NULL OR r.[societe] = @societe)
  AND r.[Valide] = 'Oui'
ORDER BY r.[Code client], r.[Date] DESC"""

# DS_KPI_RECOUVREMENT : on garde les sous-requêtes encours (EV + IFV),
# on remplace uniquement le bloc "Reglements Mois" par Réglements_Clients
Q_KPI_RECOUVREMENT = """\
SELECT
    (SELECT SUM(e.[Montant échéance] - ISNULL(ifv.Total_Regle, 0))
     FROM [Échéances_Ventes] e
     LEFT JOIN (
         SELECT [N° pièce], [Code client], [DB_Id], SUM([Montant régler]) AS Total_Regle
         FROM [Imputation_Factures_Ventes]
         WHERE [Date règlement] <= @dateFin
         GROUP BY [N° pièce], [Code client], [DB_Id]
     ) ifv ON e.[N° pièce] = ifv.[N° pièce] AND e.[Code client] = ifv.[Code client] AND e.[DB_Id] = ifv.[DB_Id]
     WHERE e.[Date document] <= @dateFin
       AND e.[Montant échéance] - ISNULL(ifv.Total_Regle, 0) > 0
       AND (@societe IS NULL OR e.[societe] = @societe)) AS [Encours Total],

    (SELECT SUM(e.[Montant échéance] - ISNULL(ifv.Total_Regle, 0))
     FROM [Échéances_Ventes] e
     LEFT JOIN (
         SELECT [N° pièce], [Code client], [DB_Id], SUM([Montant régler]) AS Total_Regle
         FROM [Imputation_Factures_Ventes]
         WHERE [Date règlement] <= @dateFin
         GROUP BY [N° pièce], [Code client], [DB_Id]
     ) ifv ON e.[N° pièce] = ifv.[N° pièce] AND e.[Code client] = ifv.[Code client] AND e.[DB_Id] = ifv.[DB_Id]
     WHERE e.[Date document] <= @dateFin
       AND e.[Date d'échéance] >= @dateFin
       AND e.[Montant échéance] - ISNULL(ifv.Total_Regle, 0) > 0
       AND (@societe IS NULL OR e.[societe] = @societe)) AS [A Echoir],

    (SELECT SUM(e.[Montant échéance] - ISNULL(ifv.Total_Regle, 0))
     FROM [Échéances_Ventes] e
     LEFT JOIN (
         SELECT [N° pièce], [Code client], [DB_Id], SUM([Montant régler]) AS Total_Regle
         FROM [Imputation_Factures_Ventes]
         WHERE [Date règlement] <= @dateFin
         GROUP BY [N° pièce], [Code client], [DB_Id]
     ) ifv ON e.[N° pièce] = ifv.[N° pièce] AND e.[Code client] = ifv.[Code client] AND e.[DB_Id] = ifv.[DB_Id]
     WHERE e.[Date document] <= @dateFin
       AND e.[Date d'échéance] < @dateFin
       AND e.[Montant échéance] - ISNULL(ifv.Total_Regle, 0) > 0
       AND (@societe IS NULL OR e.[societe] = @societe)) AS [Echu],

    (SELECT COUNT(*)
     FROM [Échéances_Ventes] e
     LEFT JOIN (
         SELECT [N° pièce], [Code client], [DB_Id], SUM([Montant régler]) AS Total_Regle
         FROM [Imputation_Factures_Ventes]
         WHERE [Date règlement] <= @dateFin
         GROUP BY [N° pièce], [Code client], [DB_Id]
     ) ifv ON e.[N° pièce] = ifv.[N° pièce] AND e.[Code client] = ifv.[Code client] AND e.[DB_Id] = ifv.[DB_Id]
     WHERE e.[Date document] <= @dateFin
       AND e.[Date d'échéance] < @dateFin
       AND e.[Montant échéance] - ISNULL(ifv.Total_Regle, 0) > 0
       AND (@societe IS NULL OR e.[societe] = @societe)) AS [Nb Echeances Retard],

    (SELECT COUNT(DISTINCT e.[Code client])
     FROM [Échéances_Ventes] e
     LEFT JOIN (
         SELECT [N° pièce], [Code client], [DB_Id], SUM([Montant régler]) AS Total_Regle
         FROM [Imputation_Factures_Ventes]
         WHERE [Date règlement] <= @dateFin
         GROUP BY [N° pièce], [Code client], [DB_Id]
     ) ifv ON e.[N° pièce] = ifv.[N° pièce] AND e.[Code client] = ifv.[Code client] AND e.[DB_Id] = ifv.[DB_Id]
     WHERE e.[Date document] <= @dateFin
       AND e.[Date d'échéance] < @dateFin
       AND e.[Montant échéance] - ISNULL(ifv.Total_Regle, 0) > 0
       AND (@societe IS NULL OR e.[societe] = @societe)) AS [Nb Clients Retard],

    (SELECT ISNULL(SUM([Montant]), 0)
     FROM [Réglements_Clients]
     WHERE [Date] BETWEEN DATEADD(MONTH, DATEDIFF(MONTH, 0, @dateFin), 0) AND @dateFin
       AND (@societe IS NULL OR [societe] = @societe)
       AND [Valide] = 'Oui') AS [Reglements Mois],

    (SELECT AVG(DATEDIFF(DAY, e.[Date d'échéance], @dateFin))
     FROM [Échéances_Ventes] e
     LEFT JOIN (
         SELECT [N° pièce], [Code client], [DB_Id], SUM([Montant régler]) AS Total_Regle
         FROM [Imputation_Factures_Ventes]
         WHERE [Date règlement] <= @dateFin
         GROUP BY [N° pièce], [Code client], [DB_Id]
     ) ifv ON e.[N° pièce] = ifv.[N° pièce] AND e.[Code client] = ifv.[Code client] AND e.[DB_Id] = ifv.[DB_Id]
     WHERE e.[Date document] <= @dateFin
       AND e.[Date d'échéance] < @dateFin
       AND e.[Montant échéance] - ISNULL(ifv.Total_Regle, 0) > 0
       AND (@societe IS NULL OR e.[societe] = @societe)) AS [Retard Moyen Jours]"""

UPDATES = {
    "DS_TB_ENCAISSEMENTS_MOIS":  Q_TB_ENCAISSEMENTS_MOIS,
    "DS_REC_ENCAISSEMENTS_MENS": Q_REC_ENCAISSEMENTS_MENS,
    "DS_REGLEMENTS_PAR_PERIODE": Q_REGLEMENTS_PAR_PERIODE,
    "DS_REGLEMENTS_PAR_CLIENT":  Q_REGLEMENTS_PAR_CLIENT,
    "DS_REGLEMENTS_PAR_MODE":    Q_REGLEMENTS_PAR_MODE,
    "DS_REC_REGLEMENTS":         Q_REC_REGLEMENTS,
    "DS_REC_HISTORIQUE_CLIENT":  Q_REC_HISTORIQUE_CLIENT,
    "DS_KPI_RECOUVREMENT":       Q_KPI_RECOUVREMENT,
}

SKIP = {
    "DS_TB_SYNTHESE_RECOUVREMENT": "calcul d'encours (EV + IFV) — inchangé",
    "DS_REC_KPI_GLOBAL":           "calcul d'encours (EV + IFV) — inchangé",
}


def run(conn_str=CONN_STR):
    print(f"Connexion à {conn_str.split(';')[1]}...")
    conn = pyodbc.connect(conn_str)
    cur = conn.cursor()

    for code, reason in SKIP.items():
        print(f"  SKIP  {code} ({reason})")

    updated = 0
    for code, query in UPDATES.items():
        cur.execute(
            "SELECT id, nom FROM APP_DataSources_Templates WHERE code = ?", code
        )
        row = cur.fetchone()
        if not row:
            print(f"  WARN  {code} introuvable — ignoré")
            continue
        ds_id, nom = row
        cur.execute(
            "UPDATE APP_DataSources_Templates SET query_template = ? WHERE code = ?",
            query, code
        )
        print(f"  OK    [{ds_id}] {code} — {nom}")
        updated += 1

    conn.commit()
    conn.close()
    print(f"\nTerminé : {updated} source(s) mise(s) à jour.")


if __name__ == "__main__":
    conn_str = sys.argv[1] if len(sys.argv) > 1 else CONN_STR
    run(conn_str)
