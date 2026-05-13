# -*- coding: utf-8 -*-
import pyodbc, json

SAAS = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019'
DWH_KA = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=DWH_KA;UID=sa;PWD=SQL@2019'

conn = pyodbc.connect(SAAS, timeout=15)
c = conn.cursor()

print("=== Pivot 121 ===")
c.execute("SELECT * FROM APP_Pivots_V2 WHERE id = 121")
row = c.fetchone()
if row:
    headers = [desc[0] for desc in c.description]
    d = dict(zip(headers, row))
    for k, v in d.items():
        if v and str(v).strip():
            if k in ('rows_config','columns_config','values_config','filters_config','source_params','summary_functions','window_calculations','formatting_rules'):
                try:
                    print(f"\n{k}:")
                    print(json.dumps(json.loads(v), ensure_ascii=False, indent=2)[:800])
                except:
                    print(f"{k}: {str(v)[:300]}")
            else:
                print(f"{k}: {v}")

print("\n=== Datasource lié ===")
ds_code = d.get('data_source_code')
if ds_code:
    c.execute("SELECT id, code, query_template FROM APP_DataSources_Templates WHERE code = ?", (ds_code,))
    r = c.fetchone()
    if r:
        print(f"id={r[0]}, code={r[1]}")
        print(f"\nQuery:\n{r[2]}")
    else:
        print(f"DS '{ds_code}' NOT FOUND in templates!")

conn.close()
