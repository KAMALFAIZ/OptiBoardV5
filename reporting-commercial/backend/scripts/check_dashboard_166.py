# -*- coding: utf-8 -*-
import sys, os, warnings, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings('ignore')
from app.database_unified import execute_central

db = execute_central("SELECT nom, description, widgets FROM APP_Dashboards WHERE id=166")[0]
print(f"Dashboard 166 : {db['nom']}")
print(f"Description   : {db['description']}")
print()

widgets = json.loads(db['widgets'] or '[]')
print(f"=== {len(widgets)} WIDGETS ===")
for w in widgets:
    wid  = w.get('id','?')
    wtyp = w.get('type','?')
    wtit = w.get('title','?')
    cfg  = w.get('config', {}) or {}

    ds_code   = cfg.get('dataSourceCode','')
    ds_id     = cfg.get('dataSourceId','') or cfg.get('ds','')
    ds_origin = cfg.get('dataSourceOrigin','')
    vfield    = cfg.get('value_field','') or cfg.get('y_field','') or cfg.get('valueField','')

    print(f"  [{wid}] {wtyp:10} '{wtit}'")
    print(f"          ds_code={ds_code!r}  ds_id={ds_id!r}  origin={ds_origin!r}  field={vfield!r}")

    # Verifier si la DS existe
    if ds_code:
        ex = execute_central(f"SELECT COUNT(1) AS n FROM APP_DataSources_Templates WHERE code='{ds_code}'")
        print(f"          -> DS existe : {ex[0]['n'] > 0}")
    elif ds_id:
        ex = execute_central(f"SELECT COUNT(1) AS n FROM APP_DataSources WHERE id={ds_id}") if str(ds_id).isdigit() else [{'n':0}]
        print(f"          -> DS (id={ds_id}) existe : {ex[0]['n'] > 0}")
    else:
        print(f"          -> PAS DE SOURCE CONFIGUREE")
    print()
