# -*- coding: utf-8 -*-
import pyodbc
conn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=DWH_KA;UID=sa;PWD=SQL@2019', timeout=15)
cursor = conn.cursor()

# Test the exact query from the datasource
print("=== Test exact query ===")
cursor.execute("""
SELECT
    FORMAT([Date Mouvement], 'yyyy-MM') AS [Mois],
    DATENAME(MONTH, [Date Mouvement]) + ' ' + CAST(YEAR([Date Mouvement]) AS VARCHAR) AS [Libellé Mois],
    SUM(CASE WHEN [Sens de mouvement] = N'Entrée' THEN ABS([Quantité]) ELSE 0 END) AS [Entrées],
    SUM(CASE WHEN [Sens de mouvement] = 'Sortie' THEN ABS([Quantité]) ELSE 0 END) AS [Sorties],
    SUM(CASE WHEN [Sens de mouvement] = N'Entrée' THEN ABS([Montant Stock]) ELSE 0 END) AS [Valeur Entrées],
    SUM(CASE WHEN [Sens de mouvement] = 'Sortie' THEN ABS([Montant Stock]) ELSE 0 END) AS [Valeur Sorties]
FROM [Mouvement_stock]
WHERE [Date Mouvement] BETWEEN '2025-01-01' AND '2025-12-31'
GROUP BY FORMAT([Date Mouvement], 'yyyy-MM'), DATENAME(MONTH, [Date Mouvement]) + ' ' + CAST(YEAR([Date Mouvement]) AS VARCHAR)
ORDER BY [Mois]
""")
rows = cursor.fetchall()
print(f"  Rows returned: {len(rows)}")
for r in rows[:3]:
    print(f"  {r[0]} | {r[1]} | E={r[2]} S={r[3]} | VE={r[4]} VS={r[5]}")

# Also check what the actual stored query looks like
print("\n=== Stored query in DB ===")
cursor2 = conn.cursor()
conn2 = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019', timeout=15)
c2 = conn2.cursor()
c2.execute("SELECT query_template FROM APP_DataSources_Templates WHERE code='DS_TB_MVT_STOCK_MENSUEL'")
r = c2.fetchone()
if r:
    print(f"  Length: {len(r[0])}")
    print(f"  Contains 'Entrée': {'Entrée' in r[0]}")
    print(f"  Contains 'Sens de mouvement': {'Sens de mouvement' in r[0]}")
    # Check if é is stored correctly
    for i, ch in enumerate(r[0]):
        if ord(ch) > 127:
            print(f"  Char at {i}: '{ch}' (U+{ord(ch):04X})")
            if i > 5:
                break
conn2.close()
conn.close()
