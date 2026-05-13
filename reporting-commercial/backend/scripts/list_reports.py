"""Liste tous les gridviews avec colonnes et types."""
import sys, os, json, warnings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings('ignore')
from app.database_unified import execute_central

grids = execute_central(
    "SELECT id, nom, data_source_code, columns_config FROM APP_GridViews WHERE actif=1 ORDER BY nom"
)
print(f"=== GRIDVIEWS ACTIFS ({len(grids)} total) ===\n")
for g in grids:
    cfg = g['columns_config'] or '[]'
    try:
        cols = json.loads(cfg)
    except:
        cols = []
    src = g['data_source_code'] or '(query direct)'
    print(f"[id={g['id']:3d}] {g['nom']}")
    print(f"       source: {src}")
    if cols:
        for c in cols:
            t   = c.get('type',   '?')
            fmt = c.get('format', '')
            f   = c.get('field',  c.get('header', '?'))
            print(f"       - {f:35s}  type={t:8s}  format={fmt}")
    else:
        print("       (auto-generees)")
    print()
