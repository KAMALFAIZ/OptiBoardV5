# -*- coding: utf-8 -*-
"""Verifier quelles datasources sont manquantes pour les pivots dans les menus."""
import sys, os, warnings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings('ignore')
from app.database_unified import execute_central

# Tous les pivots dans un menu
pv_in_menu = execute_central("SELECT DISTINCT target_id FROM APP_Menus WHERE type='pivot'")
pv_ids = [r['target_id'] for r in pv_in_menu]

print(f"Pivots dans les menus : {sorted(pv_ids)}")
print()

# Pour chaque pivot, verifier si sa DS existe
print(f"{'Pivot ID':<10} {'Pivot nom':<45} {'DS code':<45} {'Existe?'}")
print("-"*140)

missing = []
for pid in sorted(pv_ids):
    pv = execute_central(f"SELECT id, nom, data_source_code FROM APP_Pivots_V2 WHERE id={pid}")
    if not pv:
        print(f"{pid:<10} PIVOT INTROUVABLE")
        continue
    p = pv[0]
    ds_code = p['data_source_code'] or ''
    if not ds_code:
        print(f"{pid:<10} {p['nom']:<45} (pas de DS)")
        continue
    exists = execute_central(f"SELECT COUNT(1) AS n FROM APP_DataSources_Templates WHERE code='{ds_code}'")[0]['n']
    status = "OK" if exists else "MANQUANTE"
    print(f"{pid:<10} {p['nom']:<45} {ds_code:<45} {status}")
    if not exists:
        missing.append((pid, p['nom'], ds_code))

print(f"\n{'='*70}")
print(f"DATASOURCES MANQUANTES : {len(missing)}")
print(f"{'='*70}")
for pid, nom, code in missing:
    print(f"  Pivot {pid:3} '{nom}' -> DS '{code}'")

# Aussi verifier les datasources utilisees par les DS qui existent avec des codes COM_
print("\n=== DS avec prefix DS_COM_ existantes ===")
com_ds = execute_central("SELECT code, nom FROM APP_DataSources_Templates WHERE code LIKE 'DS_COM_%' ORDER BY code")
for d in com_ds:
    print(f"  {d['code']:45} | {d['nom']}")
