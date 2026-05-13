# -*- coding: utf-8 -*-
"""Vérifie les colonnes de Echéances_Ventes et la cohérence des données Marge"""
import pyodbc

DWH_KA = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=DWH_KA;UID=sa;PWD=SQL@2019'

conn = pyodbc.connect(DWH_KA, timeout=15)
c = conn.cursor()

print("=== Colonnes Echéances_Ventes ===")
c.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME LIKE '%ch%ance%' AND TABLE_NAME LIKE '%Vente%' ORDER BY ORDINAL_POSITION")
for r in c.fetchall():
    print(f"  {r[0]}")

print("\n=== TOP 5 lignes ventes avec CMUP ===")
c.execute("""
SELECT TOP 5 [Code article], [Montant HT Net], [CMUP], [Quantité],
    [CMUP] * [Quantité] AS CoutTotal,
    [Montant HT Net] - ISNULL([CMUP], 0) * [Quantité] AS Marge
FROM Lignes_des_ventes
WHERE [Valorise CA] = 'Oui' AND [CMUP] > 0 AND [Date BL] >= '2025-01-01'
ORDER BY [Montant HT Net] DESC
""")
for r in c.fetchall():
    print(f"  Art={r[0]}, CA={r[1]:.2f}, PdR={r[2]:.4f}, Qte={r[3]:.2f}, CoutTotal={r[4]:.2f}, Marge={r[5]:.2f}")

print("\n=== Stats CMUP ===")
c.execute("""
SELECT
    COUNT(*) total,
    SUM(CASE WHEN [CMUP] IS NULL THEN 1 ELSE 0 END) nb_null,
    SUM(CASE WHEN [CMUP] = 0 THEN 1 ELSE 0 END) nb_zero,
    SUM(CASE WHEN [CMUP] > 0 THEN 1 ELSE 0 END) nb_pos,
    MIN(CASE WHEN [CMUP] > 0 THEN [CMUP] END) min_pdr,
    MAX([CMUP]) max_pdr,
    AVG(CASE WHEN [CMUP] > 0 THEN [CMUP] END) avg_pdr,
    AVG([Montant HT Net]) avg_ca,
    AVG([Quantité]) avg_qte
FROM Lignes_des_ventes
WHERE [Valorise CA] = 'Oui' AND [Date BL] >= '2025-01-01'
""")
r = c.fetchone()
print(f"  Total={r[0]}, Null={r[1]}, Zero={r[2]}, Positif={r[3]}")
print(f"  Min PdR={r[4]}, Max PdR={r[5]:.2f}, Avg PdR={r[6]:.2f}")
print(f"  Avg Montant HT={r[7]:.2f}, Avg Qte={r[8]:.2f}")

conn.close()
