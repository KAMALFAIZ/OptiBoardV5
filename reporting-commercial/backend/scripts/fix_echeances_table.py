# -*- coding: utf-8 -*-
"""Fix table name [Échéances_Ventes] -> [Echéances_Ventes] in all datasources"""
import pyodbc

SAAS = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019'
DWH_KA = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=DWH_KA;UID=sa;PWD=SQL@2019'

# First: find exact table name in DWH
print("=== Tables Echéances dans DWH_KA ===")
conn_dwh = pyodbc.connect(DWH_KA, timeout=15)
c_dwh = conn_dwh.cursor()
c_dwh.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME LIKE '%ch%ances%' OR TABLE_NAME LIKE '%ch%ance%'")
for r in c_dwh.fetchall():
    print(f"  '{r[0]}' (hex first 3: {r[0][:3].encode('utf-8').hex()})")
conn_dwh.close()

# Fix in APP_DataSources_Templates
print("\n=== Correction dans OptiBoard_SaaS ===")
conn = pyodbc.connect(SAAS, timeout=15)
c = conn.cursor()

# Find all datasources with É (capital E accent) in Échéances
c.execute("SELECT id, code, query_template FROM APP_DataSources_Templates WHERE query_template LIKE N'%ch%ances_Ventes%' AND actif = 1")
rows = c.fetchall()

fixed = 0
for ds_id, code, query in rows:
    if not query:
        continue
    # Replace [Échéances_Ventes] -> [Echéances_Ventes]
    # The accented É vs E issue
    new_query = query.replace('Échéances_Ventes', 'Echéances_Ventes')
    # Also try without brackets
    new_query = new_query.replace('Échéances_Achats', 'Echéances_Achats')
    if new_query != query:
        c.execute("UPDATE APP_DataSources_Templates SET query_template = ? WHERE id = ?", (new_query, ds_id))
        print(f"  Fixed {code} (id={ds_id})")
        fixed += 1

conn.commit()
print(f"\nTotal: {fixed} datasources corrigées")

# Verify DS_KPI_RESUME
c.execute("SELECT query_template FROM APP_DataSources_Templates WHERE code = 'DS_KPI_RESUME'")
row = c.fetchone()
if row:
    q = row[0]
    if 'Echéances_Ventes' in q and 'Échéances_Ventes' not in q:
        print("DS_KPI_RESUME: OK - utilise Echéances_Ventes (sans É)")
    elif 'Échéances_Ventes' in q:
        print("DS_KPI_RESUME: STILL HAS É - not fixed!")
    else:
        print("DS_KPI_RESUME: No Echéances reference found")

conn.close()
