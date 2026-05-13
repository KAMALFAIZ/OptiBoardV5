"""Vérifier les menus et sections existants."""
import sys, os, warnings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings('ignore')
from app.database_unified import execute_central

# Sections principales (sans parent)
print("=== SECTIONS MENU (racine) ===")
parents = execute_central(
    "SELECT id, nom, code, ordre FROM APP_Menus WHERE parent_id IS NULL ORDER BY ordre"
)
for p in parents:
    print(f"  [id={p['id']}] ordre={p['ordre']} | {p['nom']} (code={p['code']})")

# Menus performance/commercial
print("\n=== MENUS PERFORMANCE / COMMERCIAL ===")
menus = execute_central("""
    SELECT id, nom, code, type, target_id, parent_id
    FROM APP_Menus
    WHERE nom LIKE '%commercial%' OR nom LIKE '%Commercial%'
       OR nom LIKE '%performance%' OR nom LIKE '%Performance%'
       OR nom LIKE '%objectif%' OR nom LIKE '%Objectif%'
    ORDER BY parent_id, nom
""")
for r in menus:
    print(f"  [id={r['id']}] parent={r['parent_id']} | {r['nom']} | type={r['type']} | target={r['target_id']}")
