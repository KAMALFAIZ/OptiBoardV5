import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import warnings; warnings.filterwarnings('ignore')
from app.database_unified import execute_client

try:
    rows = execute_client("SELECT id, username, role_global, actif FROM APP_Users", dwh_code='KA')
    print(f"Users in OptiBoard_KA: {len(rows)}")
    for r in rows:
        print(f"  id={r['id']} username={r['username']} role={r['role_global']} actif={r['actif']}")
except Exception as e:
    print(f"Error: {e}")
