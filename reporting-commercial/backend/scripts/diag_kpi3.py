# -*- coding: utf-8 -*-
import pyodbc, json

SAAS = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019'
DWH_KA = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=DWH_KA;UID=sa;PWD=SQL@2019'

conn = pyodbc.connect(SAAS, timeout=15)
c = conn.cursor()

# Colonnes de APP_Pivots_V2
print("=== Colonnes APP_Pivots_V2 ===")
c.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'APP_Pivots_V2' ORDER BY ORDINAL_POSITION")
cols = [r[0] for r in c.fetchall()]
print(cols)

# Chercher les pivots du dashboard 166
print("\n=== Pivots du dashboard 166 ===")
c.execute("SELECT TOP 1 * FROM APP_Pivots_V2 WHERE id = 1")
row = c.fetchone()
if row:
    print([desc[0] for desc in c.description])

# Chercher dashboard_id colonne alternative
dash_col = None
for col in cols:
    if 'dashboard' in col.lower() or 'dash' in col.lower():
        dash_col = col
        break
print(f"\nColonne dashboard: {dash_col}")

if dash_col:
    c.execute(f"SELECT TOP 20 * FROM APP_Pivots_V2 WHERE [{dash_col}] = 166")
    rows = c.fetchall()
    headers = [desc[0] for desc in c.description]
    print(f"Headers: {headers}")
    for row in rows:
        d = dict(zip(headers, row))
        print(f"\nid={d.get('id')}, titre/name={d.get('titre', d.get('name', d.get('libelle', '?')))}")
        print(f"  datasource={d.get('datasource_code', d.get('datasource', d.get('source_code', '?')))}")
        print(f"  type={d.get('type_affichage', d.get('widget_type', d.get('type', '?')))}")
        # Config
        for k in headers:
            if 'config' in k.lower() and d.get(k):
                try:
                    cfg = json.loads(d[k])
                    kpi_related = {ck: cv for ck, cv in cfg.items() if any(x in ck.lower() for x in ['field', 'metric', 'kpi', 'value', 'column'])}
                    if kpi_related:
                        print(f"  config fields: {kpi_related}")
                except:
                    pass

conn.close()
