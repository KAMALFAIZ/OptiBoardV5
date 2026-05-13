"""Inspecter APP_Objectifs et les sources pivot manquantes."""
import sys, os, warnings, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings('ignore')
from app.database_unified import execute_central

# Structure APP_Objectifs
print("=== COLONNES APP_Objectifs ===")
meta = execute_central("""
    SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME='APP_Objectifs'
    ORDER BY ORDINAL_POSITION
""")
for c in meta:
    print(f"  {c['COLUMN_NAME']:30} {c['DATA_TYPE']}")

# Echantillon data
print("\n=== DONNEES APP_Objectifs (10 premieres) ===")
try:
    rows = execute_central("SELECT TOP 10 * FROM APP_Objectifs ORDER BY 1")
    for r in rows:
        print(f"  {r}")
except Exception as e:
    print(f"  Erreur: {e}")

# Chercher la datasource qui alimente GV 387
print("\n=== TOUTES LES DATASOURCES (codes) ===")
all_ds = execute_central("SELECT code, nom FROM APP_DataSources_Templates ORDER BY code")
for d in all_ds:
    print(f"  {d['code']:45} | {d['nom']}")

# Datasource ID=6 (utilise par dashboards)
print("\n=== GRIDVIEW ID=6 ou Datasource ID=6 ===")
try:
    gv6 = execute_central("SELECT id, nom, data_source_code FROM APP_GridViews WHERE id=6")
    for r in gv6:
        print(f"  GV6: {r['nom']} ds={r['data_source_code']}")
except: pass
try:
    ds6 = execute_central("SELECT id, nom FROM APP_DataSources WHERE id=6")
    for r in ds6:
        print(f"  DS6 (APP_DataSources): {r['nom']}")
except: pass
