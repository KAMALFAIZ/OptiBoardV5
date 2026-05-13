# -*- coding: utf-8 -*-
import sys, os, warnings, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings('ignore')
from app.database_unified import execute_central

# Full widget config of a working dashboard
for did, name in [(168, 'TB Commercial'), (169, 'TB Resp Commercial'), (170, 'TB DG')]:
    db = execute_central(f"SELECT widgets FROM APP_Dashboards WHERE id={did}")
    if not db or not db[0]['widgets']:
        print(f"[{did}] {name} : pas de widgets"); continue
    ws = json.loads(db[0]['widgets'])
    print(f"\n=== [{did}] {name} ({len(ws)} widgets) ===")
    for w in ws:
        cfg = w.get('config', {}) or {}
        print(f"  [{w.get('id')}] {w.get('type'):20} '{w.get('title')}'")
        # Afficher toutes les cles config
        for k, v in cfg.items():
            if k != 'columns':  # skip long lists
                print(f"    {k} = {str(v)[:80]}")

# DS_KPI_RESUME champs complets
print("\n=== DS_KPI_RESUME : query complete ===")
ds = execute_central("SELECT query_template FROM APP_DataSources_Templates WHERE code='DS_KPI_RESUME'")
if ds:
    print(ds[0]['query_template'])
