"""Vérifier ce qui existe déjà pour Performance Commerciale."""
import sys, os, warnings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings('ignore')
from app.database_unified import execute_central

# Datasources existantes liées aux commerciaux
print("=== DATASOURCES COMMERCIAL/PERFORMANCE ===")
ds = execute_central("""
    SELECT code, nom FROM APP_DataSources_Templates
    WHERE code LIKE '%COMMERCIAL%' OR code LIKE '%PERF%' OR code LIKE '%OBJECTIF%'
       OR nom LIKE '%commercial%' OR nom LIKE '%performance%' OR nom LIKE '%objectif%'
    ORDER BY code
""")
for r in ds:
    print(f"  {r['code']}  =>  {r['nom']}")

# Gridviews existants liés aux commerciaux
print("\n=== GRIDVIEWS COMMERCIAL/PERFORMANCE ===")
gv = execute_central("""
    SELECT id, nom, data_source_code FROM APP_GridViews
    WHERE nom LIKE '%commercial%' OR nom LIKE '%Commercial%'
       OR nom LIKE '%performance%' OR nom LIKE '%Performance%'
       OR nom LIKE '%objectif%' OR nom LIKE '%Objectif%'
       OR nom LIKE '%repr%senta%' OR nom LIKE '%Repr%senta%'
    ORDER BY nom
""")
for r in gv:
    print(f"  [id={r['id']}] {r['nom']}  (source: {r['data_source_code']})")

# Pivots existants
print("\n=== PIVOTS COMMERCIAL/PERFORMANCE ===")
try:
    pv = execute_central("""
        SELECT id, nom FROM APP_Pivots_V2
        WHERE nom LIKE '%commercial%' OR nom LIKE '%Commercial%'
           OR nom LIKE '%performance%' OR nom LIKE '%Performance%'
        ORDER BY nom
    """)
    for r in pv:
        print(f"  [id={r['id']}] {r['nom']}")
except Exception as e:
    print(f"  (erreur: {e})")

# Menus liés section Performance Commerciale
print("\n=== MENUS SECTION PERFORMANCE ===")
menus = execute_central("""
    SELECT id, label, target_type, target_id, section
    FROM APP_Menus
    WHERE section LIKE '%perf%' OR section LIKE '%Performance%'
       OR label LIKE '%commercial%' OR label LIKE '%Commercial%'
       OR label LIKE '%performance%' OR label LIKE '%Performance%'
    ORDER BY section, label
""")
for r in menus:
    print(f"  [{r['section']}] {r['label']}  type={r['target_type']} id={r['target_id']}")
