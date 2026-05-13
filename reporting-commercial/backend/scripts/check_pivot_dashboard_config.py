"""Inspecter la config d'un pivot et d'un dashboard existants."""
import sys, os, warnings, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings('ignore')
from app.database_unified import execute_central

# Structure colonnes APP_Pivots_V2
print("=== COLONNES APP_Pivots_V2 ===")
cols_pv = execute_central("SELECT TOP 0 * FROM APP_Pivots_V2")
# Pour voir les colonnes, on utilise une requete differente
meta = execute_central("""
    SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME='APP_Pivots_V2'
    ORDER BY ORDINAL_POSITION
""")
for c in meta:
    print(f"  {c['COLUMN_NAME']:30} {c['DATA_TYPE']}({c['CHARACTER_MAXIMUM_LENGTH'] or ''})")

# Un pivot exemple
print("\n=== EXEMPLE PIVOT 128 (CA par Commercial) ===")
pv = execute_central("SELECT * FROM APP_Pivots_V2 WHERE id=128")
if pv:
    p = pv[0]
    for k, v in p.items():
        val = str(v)[:200] if v else 'NULL'
        print(f"  {k:30} = {val}")

print("\n=== EXEMPLE PIVOT 140 (Performance Commercial) ===")
pv = execute_central("SELECT * FROM APP_Pivots_V2 WHERE id=140")
if pv:
    p = pv[0]
    for k, v in p.items():
        val = str(v)[:200] if v else 'NULL'
        print(f"  {k:30} = {val}")

# Structure colonnes APP_Dashboards
print("\n=== COLONNES APP_Dashboards ===")
meta = execute_central("""
    SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME='APP_Dashboards'
    ORDER BY ORDINAL_POSITION
""")
for c in meta:
    print(f"  {c['COLUMN_NAME']:30} {c['DATA_TYPE']}({c['CHARACTER_MAXIMUM_LENGTH'] or ''})")

# Un dashboard exemple
print("\n=== EXEMPLE DASHBOARD 168 (TB Commercial) ===")
db = execute_central("SELECT * FROM APP_Dashboards WHERE id=168")
if db:
    d = db[0]
    for k, v in d.items():
        val = str(v)[:300] if v else 'NULL'
        print(f"  {k:30} = {val}")

# Query complète DS_VTE_REMISES
print("\n=== QUERY DS_VTE_REMISES (complete) ===")
ds = execute_central("SELECT query_template FROM APP_DataSources_Templates WHERE code='DS_VTE_REMISES'")
if ds:
    print(ds[0]['query_template'])

# Query complète DS_COM_PERF_COMMERCIAL
print("\n=== QUERY DS_COM_PERF_COMMERCIAL (complete) ===")
ds = execute_central("SELECT query_template FROM APP_DataSources_Templates WHERE code='DS_COM_PERF_COMMERCIAL'")
if ds:
    print(ds[0]['query_template'])
