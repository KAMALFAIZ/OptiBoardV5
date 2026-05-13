# -*- coding: utf-8 -*-
import pyodbc

DWH_KA = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=DWH_KA;UID=sa;PWD=SQL@2019'
conn = pyodbc.connect(DWH_KA, timeout=30)
c = conn.cursor()

query = """
DECLARE @dateDebut DATE = '2025-01-01'
DECLARE @dateFin DATE = '2025-12-31'
DECLARE @societe NVARCHAR(50) = NULL

;WITH
Ventes AS (
    SELECT
        FORMAT([Date BL], 'yyyy-MM') AS [Periode],
        SUM([Montant HT Net]) AS [CA_HT],
        SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) AS [Marge_HT]
    FROM Lignes_des_ventes
    WHERE [Valorise CA] = 'Oui'
      AND [Date BL] BETWEEN @dateDebut AND @dateFin
      AND (@societe IS NULL OR [societe] = @societe)
    GROUP BY FORMAT([Date BL], 'yyyy-MM')
),
Ventes_N1 AS (
    SELECT
        FORMAT(DATEADD(YEAR, 1, [Date BL]), 'yyyy-MM') AS [Periode],
        SUM([Montant HT Net]) AS [CA_HT_N1]
    FROM Lignes_des_ventes
    WHERE [Valorise CA] = 'Oui'
      AND DATEADD(YEAR, 1, [Date BL]) BETWEEN @dateDebut AND @dateFin
      AND (@societe IS NULL OR [societe] = @societe)
    GROUP BY FORMAT(DATEADD(YEAR, 1, [Date BL]), 'yyyy-MM')
),
Achats AS (
    SELECT
        FORMAT([Date], 'yyyy-MM') AS [Periode],
        SUM([Montant HT Net]) AS [Achats_HT],
        COUNT(DISTINCT [N° Pièce]) AS [Nb_Cmds]
    FROM Lignes_des_achats
    WHERE [Valorise CA] = 'Oui'
      AND [Date] BETWEEN @dateDebut AND @dateFin
      AND (@societe IS NULL OR [societe] = @societe)
    GROUP BY FORMAT([Date], 'yyyy-MM')
)
SELECT
    v.[Periode],
    ROUND(v.[CA_HT], 0) AS [CA HT Mois],
    ROUND(ISNULL(n.[CA_HT_N1], 0), 0) AS [CA HT N-1],
    ROUND(v.[CA_HT] - ISNULL(n.[CA_HT_N1], 0), 0) AS [Ecart CA vs N-1],
    CASE WHEN ISNULL(n.[CA_HT_N1], 0) > 0 THEN ROUND((v.[CA_HT] - n.[CA_HT_N1]) * 100.0 / n.[CA_HT_N1], 1) ELSE 0 END AS [Evol%],
    ROUND(v.[Marge_HT], 0) AS [Marge],
    CASE WHEN v.[CA_HT] > 0 THEN ROUND(v.[Marge_HT] * 100.0 / v.[CA_HT], 1) ELSE 0 END AS [Taux%],
    ROUND(ISNULL(a.[Achats_HT], 0), 0) AS [Achats],
    ISNULL(a.[Nb_Cmds], 0) AS [Nb Cmds]
FROM Ventes v
LEFT JOIN Ventes_N1 n ON v.[Periode] = n.[Periode]
LEFT JOIN Achats a ON v.[Periode] = a.[Periode]
ORDER BY v.[Periode]
"""

try:
    c.execute(query)
    rows = c.fetchall()
    headers = [desc[0] for desc in c.description]
    print(f"{'Periode':<10} {'CA HT Mois':>14} {'CA HT N-1':>14} {'Ecart':>12} {'Evol%':>7} {'Marge':>14} {'Tx%':>6} {'Achats':>14} {'Cmds':>5}")
    print("-"*110)
    for r in rows:
        print(f"{str(r[0]):<10} {r[1]:>14,.0f} {r[2]:>14,.0f} {r[3]:>12,.0f} {r[4]:>6.1f}% {r[5]:>14,.0f} {r[6]:>5.1f}% {r[7]:>14,.0f} {r[8]:>5}")
    print(f"\n{len(rows)} mois retournés")
except Exception as e:
    print(f"ERREUR: {e}")

conn.close()
