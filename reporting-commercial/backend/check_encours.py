import sys, os, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.database_unified import get_central_connection

conn = get_central_connection()
cur = conn.cursor()

# Chercher tous les dashboards avec "Encours" dans les widgets
cur.execute("SELECT nom, widgets FROM APP_Dashboards WHERE widgets IS NOT NULL AND widgets LIKE '%ncours%'")
for r in cur.fetchall():
    print("DASH:", r[0])
    try:
        widgets = json.loads(r[1])
        for w in widgets:
            title = w.get('title', '')
            if 'ncours' in title.lower() or 'ncours' in json.dumps(w.get('config', {})).lower():
                cfg = w.get('config', {})
                print(f"  Widget: {title}")
                print(f"  dataSourceCode: {cfg.get('dataSourceCode')}")
                print(f"  drilldownDsCode: {cfg.get('drilldownDsCode')}")
                print(f"  dataSourceOrigin: {cfg.get('dataSourceOrigin')}")
    except: pass
    print()

# Chercher aussi dans les datasources
print("=== DS avec 'encours' ===")
cur.execute("SELECT code, nom FROM APP_DataSources_Templates WHERE code LIKE '%ENCOURS%' OR nom LIKE '%ncours%'")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")

conn.close()
