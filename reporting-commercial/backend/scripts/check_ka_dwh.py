import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import warnings; warnings.filterwarnings('ignore')
from app.database_unified import execute_central

rows = execute_central("SELECT * FROM APP_DWH WHERE code = 'KA'")
for r in rows:
    for k, v in r.items():
        print(f"  {k}: {v}")

print("\n--- APP_ClientDB for KA ---")
rows2 = execute_central("SELECT * FROM APP_ClientDB WHERE dwh_code = 'KA'")
for r in rows2:
    for k, v in r.items():
        print(f"  {k}: {v}")
