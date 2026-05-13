"""
Réorganisation section Performance Commerciale (parent_id=1221).

ÉTAPE 0 : Vérifier les types utilisés dans APP_Menus pour pivot/dashboard
ÉTAPE 1 : Déplacer 5 items mal placés vers bonnes sections
ÉTAPE 2 : Ajouter 6 assets existants au menu Performance Commerciale
"""
import sys, os, warnings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings('ignore')
from app.database_unified import execute_central

# ── ÉTAPE 0 : Voir les valeurs de type utilisées ───────────────────────────
print("=== ÉTAPE 0 — Valeurs de TYPE utilisées dans APP_Menus ===")
types = execute_central(
    "SELECT DISTINCT type FROM APP_Menus WHERE type IS NOT NULL ORDER BY type"
)
for r in types:
    print(f"  type = '{r['type']}'")

print("\n=== Exemples d'entrées pivot/dashboard existantes ===")
samples = execute_central("""
    SELECT TOP 10 id, nom, type, target_id, parent_id
    FROM APP_Menus
    WHERE type IN ('pivot','dashboard','gridview','Pivot','Dashboard','GridView')
       OR type LIKE '%pivot%' OR type LIKE '%dashboard%'
    ORDER BY type, id
""")
for r in samples:
    print(f"  [id={r['id']}] parent={r['parent_id']} type='{r['type']}' target={r['target_id']} | {r['nom']}")

# ── ÉTAPE 0b : Vérifier les sections cibles ────────────────────────────────
print("\n=== ÉTAPE 0b — Sections principales (pour vérifier parent_id) ===")
sections = execute_central(
    "SELECT id, nom, ordre FROM APP_Menus WHERE parent_id IS NULL ORDER BY ordre"
)
for r in sections:
    print(f"  [id={r['id']}] ordre={r['ordre']} | {r['nom']}")

# ── ÉTAPE 0c : Voir l'état actuel de Performance Commerciale ───────────────
print("\n=== ÉTAPE 0c — Sous-menus actuels Performance Commerciale (id=1221) ===")
items = execute_central(
    "SELECT id, nom, type, target_id, ordre FROM APP_Menus WHERE parent_id=1221 ORDER BY ordre"
)
for r in items:
    print(f"  [id={r['id']}] ordre={r['ordre']} | type='{r['type']}' target={r['target_id']} | {r['nom']}")

# ── ÉTAPE 0d : Vérifier les assets qu'on veut ajouter ─────────────────────
print("\n=== ÉTAPE 0d — Assets existants à ajouter ===")
# GridView 387
gv = execute_central("SELECT id, nom, actif FROM APP_GridViews WHERE id=387")
for r in gv: print(f"  GridView {r['id']}: {r['nom']} (actif={r['actif']})")

# Pivots 128, 140, 118
pvs = execute_central("SELECT id, nom FROM APP_Pivots_V2 WHERE id IN (128, 140, 118)")
for r in pvs: print(f"  Pivot {r['id']}: {r['nom']}")

# Dashboards 168, 169
dbs = execute_central("SELECT id, nom FROM APP_Dashboards WHERE id IN (168, 169)")
for r in dbs: print(f"  Dashboard {r['id']}: {r['nom']}")

# ── ÉTAPE 0e : Vérifier les sections CA et Documents Commerciaux ───────────
print("\n=== ÉTAPE 0e — Sous-menus CA (1185) et Documents Commerciaux (1196) ===")
ca_items = execute_central(
    "SELECT id, nom, type, target_id, ordre FROM APP_Menus WHERE parent_id=1185 ORDER BY ordre"
)
print("CA (1185):")
for r in ca_items:
    print(f"  [id={r['id']}] ordre={r['ordre']} | {r['nom']}")

doc_items = execute_central(
    "SELECT id, nom, type, target_id, ordre FROM APP_Menus WHERE parent_id=1196 ORDER BY ordre"
)
print("Documents Commerciaux (1196):")
for r in doc_items:
    print(f"  [id={r['id']}] ordre={r['ordre']} | {r['nom']}")
