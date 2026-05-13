# -*- coding: utf-8 -*-
"""Verification finale de la section Performance Commerciale."""
import sys, os, warnings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings('ignore')
from app.database_unified import execute_central

print("="*70)
print("PERFORMANCE COMMERCIALE - VERIFICATION FINALE")
print("="*70)

# Menu final
print("\n[1] STRUCTURE MENU (parent_id=1221)")
items = execute_central(
    "SELECT id, nom, type, target_id, ordre FROM APP_Menus WHERE parent_id=1221 ORDER BY ordre"
)
icons = {'gridview': 'GV', 'pivot': 'PV', 'dashboard': 'DB', 'folder': 'FL'}
for r in items:
    icon = icons.get(r['type'], '??')
    print(f"  {r['ordre']:2}. [{icon}] {r['nom']} (target={r['target_id']})")

# Verifier que chaque target existe
print("\n[2] VERIFICATION DES CIBLES")
for r in items:
    if r['type'] == 'gridview':
        ex = execute_central(f"SELECT nom, actif FROM APP_GridViews WHERE id={r['target_id']}")
        status = "OK" if (ex and ex[0]['actif']) else "MANQUANT/INACTIF"
        nom = ex[0]['nom'] if ex else "?"
        print(f"  GV {r['target_id']:4}: {status:15} | {nom}")
    elif r['type'] == 'pivot':
        ex = execute_central(f"SELECT nom FROM APP_Pivots_V2 WHERE id={r['target_id']}")
        status = "OK" if ex else "MANQUANT"
        nom = ex[0]['nom'] if ex else "?"
        print(f"  PV {r['target_id']:4}: {status:15} | {nom}")
    elif r['type'] == 'dashboard':
        ex = execute_central(f"SELECT nom, actif FROM APP_Dashboards WHERE id={r['target_id']}")
        status = "OK" if (ex and ex[0]['actif']) else "MANQUANT/INACTIF"
        nom = ex[0]['nom'] if ex else "?"
        print(f"  DB {r['target_id']:4}: {status:15} | {nom}")

# Datasources des nouveaux rapports
print("\n[3] NOUVELLES DATASOURCES")
for code in ['DS_OBJECTIFS_VS_REALISE', 'DS_REMISE_PAR_COMMERCIAL']:
    r = execute_central(f"SELECT nom, LEN(query_template) AS qlen FROM APP_DataSources_Templates WHERE code='{code}'")
    if r:
        print(f"  {code}: OK ({r[0]['qlen']} chars) | {r[0]['nom']}")
    else:
        print(f"  {code}: MANQUANTE")

# CA et Documents Commerciaux
print("\n[4] CA (1185) - Nouveaux items")
ca_new = execute_central("SELECT id, nom, ordre FROM APP_Menus WHERE parent_id=1185 AND ordre > 10 ORDER BY ordre")
for r in ca_new:
    print(f"  ordre={r['ordre']} id={r['id']} | {r['nom']}")

print("\n[5] Documents Commerciaux (1196) - Nouveaux items")
doc_new = execute_central("SELECT id, nom, ordre FROM APP_Menus WHERE parent_id=1196 AND ordre > 5 ORDER BY ordre")
for r in doc_new:
    print(f"  ordre={r['ordre']} id={r['id']} | {r['nom']}")

print("\n" + "="*70)
print(f"Total Performance Commerciale : {len(items)} rapports")
print("="*70)
