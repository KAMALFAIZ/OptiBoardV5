# -*- coding: utf-8 -*-
"""Test DS_KPI_RESUME query depuis la base (template réel)"""
import pyodbc

SAAS = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019'
DWH_KA = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=DWH_KA;UID=sa;PWD=SQL@2019'

# Read the actual template from DB
conn = pyodbc.connect(SAAS, timeout=15)
c = conn.cursor()
c.execute("SELECT query_template FROM APP_DataSources_Templates WHERE code = 'DS_KPI_RESUME'")
row = c.fetchone()
template = row[0]
conn.close()

print("=== Template actuel DS_KPI_RESUME (extrait lignes Echéances) ===")
for line in template.split('\n'):
    if 'ch' in line.lower() and 'ance' in line.lower():
        print(f"  {line.strip()}")

# Replace params and execute on DWH_KA
print("\n=== Exécution sur DWH_KA ===")
query = template.replace('@dateDebut', "'2025-01-01'")
query = query.replace('@dateFin', "'2025-12-31'")
query = query.replace('@societe', 'NULL')

try:
    conn2 = pyodbc.connect(DWH_KA, timeout=30)
    c2 = conn2.cursor()
    c2.execute(query)
    r = c2.fetchone()
    if r:
        headers = [desc[0] for desc in c2.description]
        for h, v in zip(headers, r):
            print(f"  {h} = {v}")
    else:
        print("  NO RESULT")
    conn2.close()
except Exception as e:
    print(f"  ERREUR: {e}")
