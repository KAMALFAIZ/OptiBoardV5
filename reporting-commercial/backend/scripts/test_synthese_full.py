# -*- coding: utf-8 -*-
"""Test la query complète DS_DIR_SYNTHESE_MENSUELLE depuis la base"""
import pyodbc

SAAS = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019'
DWH_KA = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=DWH_KA;UID=sa;PWD=SQL@2019'

# Read template from DB
conn = pyodbc.connect(SAAS, timeout=15)
c = conn.cursor()
c.execute("SELECT query_template FROM APP_DataSources_Templates WHERE code = 'DS_DIR_SYNTHESE_MENSUELLE'")
template = c.fetchone()[0]
conn.close()

# Execute on DWH_KA
query = template.replace('@dateDebut', "'2025-01-01'").replace('@dateFin', "'2025-12-31'").replace('@societe', 'NULL')

print("=== Synthèse Mensuelle Direction - DWH_KA 2025 ===\n")
conn2 = pyodbc.connect(DWH_KA, timeout=30)
c2 = conn2.cursor()
try:
    c2.execute(query)
    rows = c2.fetchall()
    headers = [desc[0] for desc in c2.description]
    print(f"Colonnes retournées: {headers}\n")
    for r in rows:
        d = dict(zip(headers, r))
        print(f"{d.get('Période','?')}: CA={d.get('CA HT Mois',0):>12,.0f} | N-1={d.get('CA HT N-1',0):>12,.0f} | Marge={d.get('Marge Brute Mois',0):>12,.0f} | Achats={d.get('Achats HT Mois',0):>12,.0f} | Cmds={d.get('Nb Commandes Achats',0):>3} | Stock={d.get('Valeur Stock',0):>12,.0f} | Rupt={d.get('Nb Ruptures',0)}")
    print(f"\n{len(rows)} lignes OK")
except Exception as e:
    print(f"ERREUR: {e}")
conn2.close()
