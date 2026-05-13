# -*- coding: utf-8 -*-
"""Diagnostic DS_KPI_RESUME - pourquoi les KPIs sont à 0"""
import pyodbc

SAAS = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019'
DWH_KA = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=DWH_KA;UID=sa;PWD=SQL@2019'

# 1. Voir la query actuelle de DS_KPI_RESUME
print("=== DS_KPI_RESUME query actuelle ===")
conn = pyodbc.connect(SAAS, timeout=15)
c = conn.cursor()
c.execute("SELECT query_template FROM APP_DataSources_Templates WHERE code = 'DS_KPI_RESUME'")
row = c.fetchone()
if row:
    print(row[0])
conn.close()

# 2. Tester la query directement sur DWH_KA avec dates 2025
print("\n\n=== Test direct sur DWH_KA (2025) ===")
try:
    conn2 = pyodbc.connect(DWH_KA, timeout=15)
    c2 = conn2.cursor()
    c2.execute("""
    SELECT
        (SELECT ISNULL(SUM([Montant HT Net]), 0)
         FROM [Lignes_des_ventes]
         WHERE [Valorise CA] = 'Oui'
           AND [Date BL] BETWEEN '2025-01-01' AND '2025-12-31') AS CA,
        (SELECT ISNULL(SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]), 0)
         FROM [Lignes_des_ventes]
         WHERE [Valorise CA] = 'Oui'
           AND [Date BL] BETWEEN '2025-01-01' AND '2025-12-31') AS Marge,
        (SELECT COUNT(DISTINCT [Code article])
         FROM [Lignes_des_ventes]
         WHERE [Valorise CA] = 'Oui'
           AND [Date BL] BETWEEN '2025-01-01' AND '2025-12-31') AS NbArticles
    """)
    r = c2.fetchone()
    print(f"CA={r[0]}, Marge={r[1]}, NbArticles={r[2]}")

    # 3. Checker les dates disponibles dans Lignes_des_ventes
    print("\n=== Plage de dates dans Lignes_des_ventes ===")
    c2.execute("""
    SELECT MIN([Date BL]), MAX([Date BL]), COUNT(*) as total,
           SUM(CASE WHEN [Valorise CA] = 'Oui' THEN 1 ELSE 0 END) as ca_oui
    FROM [Lignes_des_ventes]
    """)
    r = c2.fetchone()
    print(f"Min [Date BL]: {r[0]}, Max [Date BL]: {r[1]}, Total: {r[2]}, [Valorise CA]='Oui': {r[3]}")

    # 4. Checker si [Date BL] est NULL souvent
    c2.execute("""
    SELECT TOP 5 [Date BL], [Montant HT Net], [Valorise CA]
    FROM [Lignes_des_ventes]
    WHERE [Valorise CA] = 'Oui'
    ORDER BY [Date BL] DESC
    """)
    print("\n=== TOP 5 lignes CA=Oui (Date BL DESC) ===")
    for r in c2.fetchall():
        print(f"  DateBL={r[0]}, MontantHT={r[1]}, ValoriseCA={r[2]}")

    conn2.close()
except Exception as e:
    print(f"ERREUR: {e}")
