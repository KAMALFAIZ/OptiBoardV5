# -*- coding: utf-8 -*-
"""
Réécrire DS_DIR_COMPARATIF_3ANS pour produire les colonnes correctes:
Mois | CA HT N | CA HT N-1 | CA HT N-2 | Ecart CA N/N-1 | Evolution CA %
     | Achats HT N | Achats HT N-1 | Marge N | Marge N-1
     | Nb Clients N | Nb Clients N-1
"""
import sys, os, pyodbc
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;'
    'UID=sa;PWD=SQL@2019;TrustServerCertificate=yes'
)
conn.autocommit = True
cur = conn.cursor()

NEW_QUERY = """\
WITH VentesParMois AS (
    SELECT
        MONTH(li.[Date BL]) AS mois_num,
        SUM(CASE WHEN YEAR(li.[Date BL]) = YEAR(@dateFin)     THEN li.[Montant HT Net] ELSE 0 END) AS ca_n,
        SUM(CASE WHEN YEAR(li.[Date BL]) = YEAR(@dateFin) - 1 THEN li.[Montant HT Net] ELSE 0 END) AS ca_n1,
        SUM(CASE WHEN YEAR(li.[Date BL]) = YEAR(@dateFin) - 2 THEN li.[Montant HT Net] ELSE 0 END) AS ca_n2,
        SUM(CASE WHEN YEAR(li.[Date BL]) = YEAR(@dateFin)
            THEN li.[Montant HT Net] - li.[Quantit\xe9] * ISNULL(li.[CMUP], 0) ELSE 0 END) AS marge_n,
        SUM(CASE WHEN YEAR(li.[Date BL]) = YEAR(@dateFin) - 1
            THEN li.[Montant HT Net] - li.[Quantit\xe9] * ISNULL(li.[CMUP], 0) ELSE 0 END) AS marge_n1,
        COUNT(DISTINCT CASE WHEN YEAR(li.[Date BL]) = YEAR(@dateFin)     THEN li.[Code client] END) AS nb_clients_n,
        COUNT(DISTINCT CASE WHEN YEAR(li.[Date BL]) = YEAR(@dateFin) - 1 THEN li.[Code client] END) AS nb_clients_n1
    FROM [Lignes_des_ventes] li
    WHERE li.[Valorise CA] = 'Oui'
      AND YEAR(li.[Date BL]) BETWEEN YEAR(@dateFin) - 2 AND YEAR(@dateFin)
      AND (@societe IS NULL OR li.[societe] = @societe)
    GROUP BY MONTH(li.[Date BL])
),
AchatsParMois AS (
    SELECT
        MONTH(l.[Date]) AS mois_num,
        SUM(CASE WHEN YEAR(l.[Date]) = YEAR(@dateFin)     THEN l.[Montant HT Net] ELSE 0 END) AS ach_n,
        SUM(CASE WHEN YEAR(l.[Date]) = YEAR(@dateFin) - 1 THEN l.[Montant HT Net] ELSE 0 END) AS ach_n1
    FROM [Lignes_des_achats] l
    WHERE l.[Type Document] IN ('Facture', 'Facture comptabilis\xe9e')
      AND YEAR(l.[Date]) BETWEEN YEAR(@dateFin) - 1 AND YEAR(@dateFin)
      AND (@societe IS NULL OR l.[societe] = @societe)
    GROUP BY MONTH(l.[Date])
)
SELECT
    v.mois_num AS [Mois],
    v.ca_n  AS [CA HT N],
    v.ca_n1 AS [CA HT N-1],
    v.ca_n2 AS [CA HT N-2],
    v.ca_n - v.ca_n1 AS [Ecart CA N/N-1],
    CASE WHEN v.ca_n1 > 0
         THEN ROUND(100.0 * (v.ca_n - v.ca_n1) / v.ca_n1, 2)
         ELSE 0 END AS [Evolution CA %],
    ISNULL(a.ach_n,  0) AS [Achats HT N],
    ISNULL(a.ach_n1, 0) AS [Achats HT N-1],
    v.marge_n  AS [Marge N],
    v.marge_n1 AS [Marge N-1],
    v.nb_clients_n  AS [Nb Clients N],
    v.nb_clients_n1 AS [Nb Clients N-1]
FROM VentesParMois v
LEFT JOIN AchatsParMois a ON a.mois_num = v.mois_num
ORDER BY [Mois]"""

print("Mise à jour de DS_DIR_COMPARATIF_3ANS...")
cur.execute("UPDATE APP_DataSources_Templates SET query_template=? WHERE code='DS_DIR_COMPARATIF_3ANS'", (NEW_QUERY,))
print(f"Lignes affectées: {cur.rowcount}")

# Vérification
cur.execute("SELECT LEFT(query_template,120) FROM APP_DataSources_Templates WHERE code='DS_DIR_COMPARATIF_3ANS'")
r = cur.fetchone()
print(f"\nApercu:\n{r[0]}")
conn.close()
print("\nOK")
