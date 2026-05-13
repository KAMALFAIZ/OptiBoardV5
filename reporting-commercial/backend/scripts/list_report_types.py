"""Liste les rapports groupés par type/application/catégorie."""
import sys, os, warnings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings('ignore')
from app.database_unified import execute_central

# Voir les colonnes disponibles pour la catégorisation
grids = execute_central(
    "SELECT id, nom, data_source_code, application, sage_application, actif "
    "FROM APP_GridViews WHERE actif=1 ORDER BY application, nom"
)

# Grouper par application
from collections import defaultdict
by_app = defaultdict(list)
for g in grids:
    app = g.get('application') or g.get('sage_application') or '(non défini)'
    by_app[app].append(g['nom'])

print(f"=== RAPPORTS PAR TYPE/APPLICATION ({len(grids)} total) ===\n")
for app in sorted(by_app.keys()):
    rapports = by_app[app]
    print(f"[{app}] — {len(rapports)} rapport(s)")
    for r in sorted(rapports):
        print(f"   • {r}")
    print()
