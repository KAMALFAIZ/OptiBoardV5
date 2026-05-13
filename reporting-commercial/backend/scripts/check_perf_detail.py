"""Détail complet section Performance Commerciale."""
import sys, os, warnings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings('ignore')
from app.database_unified import execute_central

# Sous-menus de Performance Commerciale (id=1221)
print("=== SOUS-MENUS PERFORMANCE COMMERCIALE ===")
items = execute_central(
    "SELECT id, nom, code, type, target_id, ordre FROM APP_Menus WHERE parent_id=1221 ORDER BY ordre"
)
for r in items:
    print(f"  [id={r['id']}] ordre={r['ordre']} | {r['nom']} | type={r['type']} | target={r['target_id']}")

# GridViews liés performance
print("\n=== GRIDVIEWS PERFORMANCE (existants) ===")
gvs = execute_central(
    "SELECT id, nom, data_source_code, actif FROM APP_GridViews WHERE id IN (387,440,454,466,469)"
)
for r in gvs:
    print(f"  [id={r['id']}] actif={r['actif']} | {r['nom']} (source={r['data_source_code']})")

# Pivots
print("\n=== PIVOTS EXISTANTS ===")
pv = execute_central("SELECT id, nom FROM APP_Pivots_V2 ORDER BY nom")
for r in pv:
    print(f"  [id={r['id']}] {r['nom']}")

# Dashboards
print("\n=== DASHBOARDS EXISTANTS ===")
dbs = execute_central("SELECT id, nom FROM APP_Dashboards ORDER BY nom")
for r in dbs:
    print(f"  [id={r['id']}] {r['nom']}")
