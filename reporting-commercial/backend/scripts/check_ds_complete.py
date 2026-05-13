"""Voir la query complete de DS_COM_PERF_COMMERCIAL et structure tables."""
import sys, os, warnings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings('ignore')
from app.database_unified import execute_central

# DS_COM_PERF_COMMERCIAL
print("=== DS_COM_PERF_COMMERCIAL ===")
ds = execute_central("SELECT code, nom, query_template FROM APP_DataSources_Templates WHERE code='DS_COM_PERF_COMMERCIAL'")
if ds:
    d = ds[0]
    print(f"nom: {d['nom']}")
    print(f"query:\n{d['query_template']}")
    pass
else:
    print("INTROUVABLE")

# Voir si table objectifs existe dans base centrale
print("\n=== Tables Objectifs dans base centrale ===")
obj_tables = execute_central("""
    SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_NAME LIKE '%objectif%' OR TABLE_NAME LIKE '%Objectif%'
       OR TABLE_NAME LIKE '%target%' OR TABLE_NAME LIKE '%budget%'
""")
for t in obj_tables:
    print(f"  {t['TABLE_NAME']}")
if not obj_tables:
    print("  Aucune table objectifs trouvee")

# Config complete dashboard 168
print("\n=== WIDGETS DASHBOARD 168 ===")
db = execute_central("SELECT widgets FROM APP_Dashboards WHERE id=168")
if db:
    import json
    try:
        ws = json.loads(db[0]['widgets'] or '[]')
        for w in ws:
            print(f"  [{w.get('type')}] {w.get('title')} (ds={w.get('config',{}).get('dataSourceCode','')})")
    except:
        print(db[0]['widgets'][:500])

# Config complete dashboard 169
print("\n=== WIDGETS DASHBOARD 169 ===")
db = execute_central("SELECT widgets FROM APP_Dashboards WHERE id=169")
if db:
    try:
        ws = json.loads(db[0]['widgets'] or '[]')
        for w in ws:
            print(f"  [{w.get('type')}] {w.get('title')} (ds={w.get('config',{}).get('dataSourceCode','')})")
    except:
        print(db[0]['widgets'][:500])

# DS_COM_CA_PAR_COMMERCIAL
print("\n=== DS_COM_CA_PAR_COMMERCIAL ===")
ds = execute_central("SELECT query_template FROM APP_DataSources_Templates WHERE code='DS_COM_CA_PAR_COMMERCIAL'")
if ds:
    print(ds[0]['query_template'])
