"""Fix ordre collisions apres reorganisation."""
import sys, os, warnings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings('ignore')
from app.database_unified import execute_central

# Fix Documents Commerciaux : Taux Transformation Devis ordre=7->8, Commandes=6
execute_central("UPDATE APP_Menus SET ordre=6 WHERE id=1224")
execute_central("UPDATE APP_Menus SET ordre=7 WHERE id=1225")
print("Documents Commerciaux (1196):")
rows = execute_central("SELECT id, nom, ordre FROM APP_Menus WHERE parent_id=1196 ORDER BY ordre")
for r in rows: print(f"  [id={r['id']}] ordre={r['ordre']} | {r['nom']}")

# Fix CA : CA Commercial/Mois ordre=13->11
execute_central("UPDATE APP_Menus SET ordre=11 WHERE id=1223")
print("\nCA (1185):")
rows = execute_central("SELECT id, nom, ordre FROM APP_Menus WHERE parent_id=1185 ORDER BY ordre")
for r in rows: print(f"  [id={r['id']}] ordre={r['ordre']} | {r['nom']}")
