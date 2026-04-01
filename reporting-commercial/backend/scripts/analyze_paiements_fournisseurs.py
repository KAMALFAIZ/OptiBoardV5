# -*- coding: utf-8 -*-
import pyodbc
import json

conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=kasoft.selfip.net;"
    "DATABASE=DWH_ESSAIDI26;"
    "UID=sa;PWD=SQL@2019;"
    "TrustServerCertificate=yes"
)
cursor = conn.cursor()

# Count rows
cursor.execute("SELECT COUNT(*) FROM Paiements_Fournisseurs")
total = cursor.fetchone()[0]
print(f"Total rows: {total}")

# Societes
cursor.execute("SELECT societe, COUNT(*) FROM Paiements_Fournisseurs GROUP BY societe")
for r in cursor.fetchall():
    print(f"  Societe {r[0]}: {r[1]} rows")

# Column details
cursor.execute("""
    SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'Paiements_Fournisseurs'
    ORDER BY ORDINAL_POSITION
""")
print("\nColumns:")
for r in cursor.fetchall():
    col_name = r[0]
    # Show hex for accented chars
    hex_repr = ' '.join(f'{ord(c):04x}' for c in col_name)
    print(f"  {col_name} | {r[1]} | maxlen={r[2]} | nullable={r[3]} | hex={hex_repr}")

# Sample data
print("\n--- Sample data (top 5) ---")
cursor.execute("SELECT TOP 5 * FROM Paiements_Fournisseurs")
cols = [desc[0] for desc in cursor.description]
for row in cursor.fetchall():
    print("ROW:")
    for i, val in enumerate(row):
        print(f"  {cols[i]} = {val}")
    print()

# Key stats
print("--- Key stats ---")
cursor.execute("SELECT MIN([Date]), MAX([Date]) FROM Paiements_Fournisseurs")
r = cursor.fetchone()
print(f"Date range: {r[0]} to {r[1]}")

cursor.execute("SELECT COUNT(DISTINCT [Code fournisseur]) FROM Paiements_Fournisseurs")
print(f"Distinct fournisseurs: {cursor.fetchone()[0]}")

cursor.execute("SELECT TOP 10 [Mode r\u00e9glement], COUNT(*) as cnt FROM Paiements_Fournisseurs GROUP BY [Mode r\u00e9glement] ORDER BY cnt DESC")
print("\nMode reglement distribution:")
for r in cursor.fetchall():
    print(f"  {r[0]}: {r[1]}")

cursor.execute("SELECT TOP 10 [Code journal], [Journal], COUNT(*) as cnt FROM Paiements_Fournisseurs GROUP BY [Code journal], [Journal] ORDER BY cnt DESC")
print("\nJournal distribution:")
for r in cursor.fetchall():
    print(f"  {r[0]} ({r[1]}): {r[2]}")

cursor.execute("SELECT TOP 5 [Devise], COUNT(*) as cnt FROM Paiements_Fournisseurs GROUP BY [Devise] ORDER BY cnt DESC")
print("\nDevise distribution:")
for r in cursor.fetchall():
    print(f"  {r[0]}: {r[1]}")

cursor.execute("SELECT [Valide], COUNT(*) as cnt FROM Paiements_Fournisseurs GROUP BY [Valide] ORDER BY cnt DESC")
print("\nValide distribution:")
for r in cursor.fetchall():
    print(f"  {r[0]}: {r[1]}")

cursor.execute("SELECT [Impute], COUNT(*) as cnt FROM Paiements_Fournisseurs GROUP BY [Impute] ORDER BY cnt DESC")
print("\nImpute distribution:")
for r in cursor.fetchall():
    print(f"  {r[0]}: {r[1]}")

cursor.execute("""SELECT [Comptabilis\u00e9], COUNT(*) as cnt FROM Paiements_Fournisseurs GROUP BY [Comptabilis\u00e9] ORDER BY cnt DESC""")
print("\nComptabilise distribution:")
for r in cursor.fetchall():
    print(f"  {r[0]}: {r[1]}")

cursor.execute("SELECT SUM([Montant]), AVG([Montant]), MIN([Montant]), MAX([Montant]) FROM Paiements_Fournisseurs")
r = cursor.fetchone()
print(f"\nMontant: sum={r[0]}, avg={r[1]}, min={r[2]}, max={r[3]}")

cursor.execute("SELECT SUM([solde]), AVG([solde]) FROM Paiements_Fournisseurs")
r = cursor.fetchone()
print(f"Solde: sum={r[0]}, avg={r[1]}")

conn.close()
print("\nDone!")
