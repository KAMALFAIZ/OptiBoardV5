# -*- coding: utf-8 -*-
"""Verification finale : tous les pivots dans les menus ont leur DS."""
import sys, os, warnings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings('ignore')
from app.database_unified import execute_central

pv_ids = [r['target_id'] for r in execute_central("SELECT DISTINCT target_id FROM APP_Menus WHERE type='pivot'")]
db_ids = [r['target_id'] for r in execute_central("SELECT DISTINCT target_id FROM APP_Menus WHERE type='dashboard'")]

# Check pivots
print("=== PIVOTS (tous dans les menus) ===")
pv_ok = pv_ko = 0
for pid in sorted(pv_ids):
    pv = execute_central(f"SELECT nom, data_source_code FROM APP_Pivots_V2 WHERE id={pid}")
    if not pv: print(f"  [!!] Pivot {pid} INTROUVABLE"); pv_ko += 1; continue
    dsc = pv[0]['data_source_code'] or ''
    if not dsc: print(f"  [--] Pivot {pid} '{pv[0]['nom']}' sans DS"); continue
    ex = execute_central(f"SELECT type FROM APP_DataSources_Templates WHERE code='{dsc}'")
    if ex:
        t = ex[0]['type']
        status = "OK" if t == 'SQL' else f"type={t}!"
        print(f"  [{status}] PV{pid:3} '{pv[0]['nom'][:35]}' -> {dsc}")
        if 'OK' in status: pv_ok += 1
        else: pv_ko += 1
    else:
        print(f"  [!!] PV{pid:3} '{pv[0]['nom'][:35]}' -> {dsc} MANQUANTE")
        pv_ko += 1

print(f"\nPivots : {pv_ok} OK / {pv_ko} problemes")

# Check dashboards (juste existence)
print(f"\n=== DASHBOARDS ({len(db_ids)} dans les menus) ===")
db_ok = db_ko = 0
for did in sorted(db_ids):
    db = execute_central(f"SELECT nom, actif FROM APP_Dashboards WHERE id={did}")
    if db and db[0]['actif']:
        db_ok += 1
    else:
        print(f"  [!!] Dashboard {did} : {'INTROUVABLE' if not db else 'INACTIF'}")
        db_ko += 1

print(f"Dashboards : {db_ok} OK / {db_ko} problemes")
print(f"\nRESUME : {pv_ok+db_ok} OK / {pv_ko+db_ko} problemes")
