"""Fix APP_ClientDB for KA: db_name should be OptiBoard_cltKA not OptiBoard_KA."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import warnings; warnings.filterwarnings('ignore')
from app.database_unified import execute_central, central_cursor

# Fix the db_name
with central_cursor() as c:
    c.execute(
        "UPDATE APP_ClientDB SET db_name = 'OptiBoard_cltKA' WHERE dwh_code = 'KA'"
    )
print("APP_ClientDB updated: KA -> OptiBoard_cltKA")

# Also fix APP_DWH
with central_cursor() as c:
    c.execute(
        "UPDATE APP_DWH SET base_optiboard = 'OptiBoard_cltKA' WHERE code = 'KA'"
    )
print("APP_DWH updated: base_optiboard = OptiBoard_cltKA")

# Verify
rows = execute_central("SELECT dwh_code, db_name, db_server FROM APP_ClientDB WHERE dwh_code = 'KA'")
for r in rows:
    print(f"  Verified: {r['dwh_code']} -> {r['db_name']} @ {r['db_server']}")
