# -*- coding: utf-8 -*-
import pyodbc, json

SAAS = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019'
DWH_KA = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=DWH_KA;UID=sa;PWD=SQL@2019'

conn = pyodbc.connect(SAAS, timeout=15)
c = conn.cursor()

# Trouver le dashboard 166 et sa structure widgets
print("=== APP_Dashboards colonnes ===")
c.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'APP_Dashboards' ORDER BY ORDINAL_POSITION")
print([r[0] for r in c.fetchall()])

print("\n=== Dashboard 166 ===")
c.execute("SELECT * FROM APP_Dashboards WHERE id = 166")
row = c.fetchone()
if row:
    headers = [desc[0] for desc in c.description]
    d = dict(zip(headers, row))
    print(f"nom: {d.get('nom', d.get('name', '?'))}")
    # Show widgets config
    for k in headers:
        if 'widget' in k.lower() or 'layout' in k.lower() or 'config' in k.lower():
            if d.get(k):
                try:
                    parsed = json.loads(d[k])
                    print(f"\n{k} (parsed):")
                    if isinstance(parsed, list):
                        for item in parsed[:3]:
                            print(f"  {item}")
                    else:
                        print(f"  {str(parsed)[:500]}")
                except:
                    print(f"\n{k}: {str(d[k])[:300]}")
else:
    print("Dashboard 166 non trouvé")
    c.execute("SELECT id, nom FROM APP_Dashboards ORDER BY id DESC")
    for r in c.fetchall()[:10]:
        print(f"  id={r[0]}, nom={r[1]}")

conn.close()
