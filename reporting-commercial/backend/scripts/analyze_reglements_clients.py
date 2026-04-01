# -*- coding: utf-8 -*-
import pyodbc

conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=kasoft.selfip.net;"
    "DATABASE=DWH_ESSAIDI26;"
    "UID=sa;PWD=SQL@2019;"
    "TrustServerCertificate=yes"
)
cursor = conn.cursor()

# Find the exact table name
cursor.execute("""
    SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_NAME LIKE '%glement%Client%' OR TABLE_NAME LIKE '%R%glement%'
    ORDER BY TABLE_NAME
""")
print("Tables matching:")
for r in cursor.fetchall():
    tname = r[0]
    hex_repr = ' '.join(f'{ord(c):04x}' for c in tname)
    print(f"  {tname} => {hex_repr}")

# Try exact name from user query
tbl = "R\u00e8glements_Clients"
print(f"\nUsing table: {tbl}")

cursor.execute(f"SELECT COUNT(*) FROM [{tbl}]")
total = cursor.fetchone()[0]
print(f"Total rows: {total}")

cursor.execute(f"SELECT societe, COUNT(*) FROM [{tbl}] GROUP BY societe")
for r in cursor.fetchall():
    print(f"  Societe {r[0]}: {r[1]} rows")

# Column details with hex
cursor.execute(f"""
    SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = '{tbl}'
    ORDER BY ORDINAL_POSITION
""")
print("\nColumns:")
for r in cursor.fetchall():
    col = r[0]
    hex_repr = ' '.join(f'{ord(c):04x}' for c in col)
    print(f"  {col} | {r[1]} | maxlen={r[2]} | hex={hex_repr}")

# Sample data
print("\n--- Sample data (top 3) ---")
cursor.execute(f"SELECT TOP 3 * FROM [{tbl}]")
cols = [desc[0] for desc in cursor.description]
for row in cursor.fetchall():
    print("ROW:")
    for i, val in enumerate(row):
        print(f"  {cols[i]} = {val}")
    print()

# Key stats
print("--- Key stats ---")
cursor.execute(f"SELECT MIN([Date]), MAX([Date]) FROM [{tbl}]")
r = cursor.fetchone()
print(f"Date range: {r[0]} to {r[1]}")

cursor.execute(f"SELECT COUNT(DISTINCT [Code client]) FROM [{tbl}]")
print(f"Distinct clients: {cursor.fetchone()[0]}")

cursor.execute(f"SELECT TOP 10 [Mode de r\u00e8glement], COUNT(*) as cnt FROM [{tbl}] GROUP BY [Mode de r\u00e8glement] ORDER BY cnt DESC")
print("\nMode reglement:")
for r in cursor.fetchall():
    print(f"  {r[0]}: {r[1]}")

cursor.execute(f"SELECT TOP 10 [Code journal], [Journal], COUNT(*) as cnt FROM [{tbl}] GROUP BY [Code journal], [Journal] ORDER BY cnt DESC")
print("\nJournal:")
for r in cursor.fetchall():
    print(f"  {r[0]} ({r[1]}): {r[2]}")

cursor.execute(f"SELECT [Valide], COUNT(*) as cnt FROM [{tbl}] GROUP BY [Valide]")
print("\nValide:")
for r in cursor.fetchall():
    print(f"  {r[0]}: {r[1]}")

cursor.execute(f"SELECT [Impute], COUNT(*) as cnt FROM [{tbl}] GROUP BY [Impute]")
print("\nImpute:")
for r in cursor.fetchall():
    print(f"  {r[0]}: {r[1]}")

cursor.execute(f"SELECT [Comptabilis\u00e9], COUNT(*) as cnt FROM [{tbl}] GROUP BY [Comptabilis\u00e9]")
print("\nComptabilise:")
for r in cursor.fetchall():
    print(f"  {r[0]}: {r[1]}")

cursor.execute(f"SELECT [Devise], COUNT(*) as cnt FROM [{tbl}] GROUP BY [Devise]")
print("\nDevise:")
for r in cursor.fetchall():
    print(f"  {r[0]}: {r[1]}")

cursor.execute(f"SELECT TOP 5 [Portfeuille], COUNT(*) as cnt FROM [{tbl}] GROUP BY [Portfeuille] ORDER BY cnt DESC")
print("\nPortfeuille:")
for r in cursor.fetchall():
    print(f"  {r[0]}: {r[1]}")

cursor.execute(f"SELECT SUM([Montant]), AVG([Montant]), MIN([Montant]), MAX([Montant]) FROM [{tbl}]")
r = cursor.fetchone()
print(f"\nMontant: sum={r[0]}, avg={r[1]}, min={r[2]}, max={r[3]}")

cursor.execute(f"SELECT SUM([solde]), AVG([solde]) FROM [{tbl}]")
r = cursor.fetchone()
print(f"Solde: sum={r[0]}, avg={r[1]}")

conn.close()
print("\nDone!")
