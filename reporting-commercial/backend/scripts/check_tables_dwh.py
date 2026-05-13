# -*- coding: utf-8 -*-
import pyodbc

DWH_KA = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=DWH_KA;UID=sa;PWD=SQL@2019'
conn = pyodbc.connect(DWH_KA, timeout=15)
c = conn.cursor()

print("=== Toutes les tables DWH_KA ===")
c.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE' ORDER BY TABLE_NAME")
for r in c.fetchall():
    print(f"  {r[0]}")

print("\n=== Colonnes Etat_Stock ===")
c.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='Etat_Stock' ORDER BY ORDINAL_POSITION")
for r in c.fetchall():
    print(f"  {r[0]}")

print("\n=== Colonnes Lignes_des_achats ===")
c.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='Lignes_des_achats' ORDER BY ORDINAL_POSITION")
for r in c.fetchall():
    print(f"  {r[0]}")

print("\n=== Check Trésorerie tables ===")
c.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME LIKE '%tresor%' OR TABLE_NAME LIKE '%trésor%' OR TABLE_NAME LIKE '%banque%' OR TABLE_NAME LIKE '%caisse%'")
for r in c.fetchall():
    print(f"  {r[0]}")

print("\n=== Colonnes Entête_des_achats ===")
c.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME LIKE '%t%te_des_achats%' ORDER BY ORDINAL_POSITION")
for r in c.fetchall():
    print(f"  {r[0]}")

# Check dates disponibles achats
print("\n=== Plage dates Lignes_des_achats ===")
try:
    c.execute("SELECT MIN([Date]), MAX([Date]), COUNT(*) FROM Lignes_des_achats WHERE [Valorise CA] = 'Oui'")
    r = c.fetchone()
    print(f"  Min={r[0]}, Max={r[1]}, Count={r[2]}")
except Exception as e:
    print(f"  {e}")
    try:
        c.execute("SELECT TOP 3 * FROM Lignes_des_achats")
        headers = [desc[0] for desc in c.description]
        print(f"  Colonnes: {headers[:10]}")
    except Exception as e2:
        print(f"  {e2}")

conn.close()
