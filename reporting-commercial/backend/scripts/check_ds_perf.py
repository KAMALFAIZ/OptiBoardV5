"""Inspecter les datasources et configs des GV de performance existants."""
import sys, os, warnings, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings('ignore')
from app.database_unified import execute_central

# GV cibles : 387 (Performance par Commercial), 454 (Ranking), 440 (CA par Commercial), 469 (Echeances)
target_gvs = [387, 454, 440, 469]

print("=== GRIDVIEWS DE PERFORMANCE ===\n")
for gid in target_gvs:
    gvs = execute_central(f"SELECT id, nom, data_source_code, columns_config FROM APP_GridViews WHERE id={gid}")
    if not gvs:
        print(f"[GV {gid}] INTROUVABLE")
        continue
    g = gvs[0]
    print(f"[GV {gid}] {g['nom']}")
    print(f"  data_source_code = {g['data_source_code']}")
    try:
        cols = json.loads(g['columns_config'] or '[]')
        for c in cols[:8]:
            print(f"    col: {c.get('field','?'):30} type={c.get('type','?')}")
    except:
        print(f"  columns_config = {str(g['columns_config'])[:200]}")
    print()

# Voir les datasources associees
codes = []
for gid in target_gvs:
    r = execute_central(f"SELECT data_source_code FROM APP_GridViews WHERE id={gid}")
    if r and r[0]['data_source_code']:
        codes.append(r[0]['data_source_code'])

print("=== DATASOURCES ASSOCIEES ===\n")
for code in set(codes):
    ds = execute_central(f"SELECT code, nom, query_template FROM APP_DataSources_Templates WHERE code='{code}'")
    if ds:
        d = ds[0]
        print(f"[{d['code']}] {d['nom']}")
        q = d['query_template'] or ''
        print(f"  Query (200c): {q[:200]}")
        print()

# Voir aussi les datasources PERF/COMMERCIAL/OBJECTIF
print("=== DATASOURCES PERF/COMMERCIAL/OBJECTIF ===\n")
dss = execute_central("""
    SELECT code, nom, query_template FROM APP_DataSources_Templates
    WHERE code LIKE '%PERF%' OR code LIKE '%COMMERCIAL%' OR code LIKE '%OBJECTIF%'
       OR code LIKE '%REMISE%' OR code LIKE '%RANKING%'
    ORDER BY code
""")
for d in dss:
    print(f"[{d['code']}] {d['nom']}")
    q = d['query_template'] or ''
    print(f"  Query (300c): {q[:300]}")
    print()

# Voir les pivots 128, 140, 118
print("=== PIVOTS DE PERFORMANCE ===\n")
for pid in [128, 140, 118]:
    pvs = execute_central(f"SELECT id, nom, data_source_code FROM APP_Pivots_V2 WHERE id={pid}")
    if pvs:
        p = pvs[0]
        print(f"[Pivot {pid}] {p['nom']} (ds={p['data_source_code']})")

# Voir les dashboards 168, 169
print("\n=== DASHBOARDS ===\n")
for did in [168, 169]:
    dbs = execute_central(f"SELECT id, nom FROM APP_Dashboards WHERE id={did}")
    if dbs:
        print(f"[Dashboard {did}] {dbs[0]['nom']}")
