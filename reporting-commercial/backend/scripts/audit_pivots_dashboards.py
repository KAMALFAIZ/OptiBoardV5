# -*- coding: utf-8 -*-
"""Lister tous les Pivots et Dashboards existants."""
import sys, os, warnings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings('ignore')
from app.database_unified import execute_central

print("=== TOUS LES PIVOTS (APP_Pivots_V2) ===")
pvs = execute_central("SELECT id, nom, code, data_source_code FROM APP_Pivots_V2 ORDER BY id")
for p in pvs:
    print(f"  [{p['id']:3}] {p['nom']:50} ds={p['data_source_code']}")

print(f"\nTotal : {len(pvs)} pivots")

print("\n=== TOUS LES DASHBOARDS (APP_Dashboards) ===")
dbs = execute_central("SELECT id, nom, code, actif FROM APP_Dashboards ORDER BY id")
for d in dbs:
    print(f"  [{d['id']:3}] {d['nom']:50} actif={d['actif']} code={d['code']}")

print(f"\nTotal : {len(dbs)} dashboards")

# Pivots deja dans un menu
print("\n=== PIVOTS DEJA DANS UN MENU ===")
pv_in_menu = execute_central("SELECT target_id, nom FROM APP_Menus WHERE type='pivot'")
used_pv = {r['target_id'] for r in pv_in_menu}
print(f"  IDs utilises : {sorted(used_pv)}")

# Pivots PAS encore dans un menu
print("\n=== PIVOTS NON ENCORE DANS UN MENU ===")
for p in pvs:
    if p['id'] not in used_pv:
        print(f"  [{p['id']:3}] {p['nom']} (ds={p['data_source_code']})")

# Dashboards deja dans un menu
print("\n=== DASHBOARDS DEJA DANS UN MENU ===")
db_in_menu = execute_central("SELECT target_id, nom FROM APP_Menus WHERE type='dashboard'")
used_db = {r['target_id'] for r in db_in_menu}
print(f"  IDs utilises : {sorted(used_db)}")

# Dashboards PAS encore dans un menu
print("\n=== DASHBOARDS NON ENCORE DANS UN MENU ===")
for d in dbs:
    if d['id'] not in used_db:
        print(f"  [{d['id']:3}] actif={d['actif']} | {d['nom']} (code={d['code']})")
