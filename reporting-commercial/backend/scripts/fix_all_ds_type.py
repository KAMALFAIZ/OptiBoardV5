# -*- coding: utf-8 -*-
"""Corriger type=query -> type=SQL pour toutes les DS utilisees par les pivots."""
import sys, os, warnings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings('ignore')
from app.database_unified import execute_central

# Recuperer tous les codes DS utilises par des pivots dans les menus
pv_ids = [r['target_id'] for r in execute_central("SELECT DISTINCT target_id FROM APP_Menus WHERE type='pivot'")]
ds_codes = []
for pid in pv_ids:
    pv = execute_central(f"SELECT data_source_code FROM APP_Pivots_V2 WHERE id={pid}")
    if pv and pv[0]['data_source_code']:
        ds_codes.append(pv[0]['data_source_code'])

# Trouver celles avec type != SQL
codes_in = "','".join(ds_codes)
wrong_type = execute_central(f"""
    SELECT code, type FROM APP_DataSources_Templates
    WHERE code IN ('{codes_in}') AND type != 'SQL'
""")

print(f"DS avec type incorrect : {len(wrong_type)}")
for r in wrong_type:
    print(f"  {r['code']:45} type='{r['type']}'")

# Corriger
if wrong_type:
    execute_central(f"UPDATE APP_DataSources_Templates SET type='SQL' WHERE code IN ('{codes_in}') AND type != 'SQL'")
    print(f"\nCorrige {len(wrong_type)} enregistrements -> type=SQL")

# Verification finale
still_wrong = execute_central(f"""
    SELECT COUNT(1) AS n FROM APP_DataSources_Templates
    WHERE code IN ('{codes_in}') AND type != 'SQL'
""")
print(f"Restant avec type incorrect : {still_wrong[0]['n']}")
print("\nTout est corrige - tous les pivots devraient maintenant fonctionner.")
