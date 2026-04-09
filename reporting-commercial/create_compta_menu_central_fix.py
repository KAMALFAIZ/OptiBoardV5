"""
Crée les menus Comptabilité directement dans la DB CENTRALE (OptiBoard_SaaS)
en utilisant execute_central pour les écritures.
Parent Comptabilité en central = id=266 (code='MN_comptabilit_c3da').
"""
import sys, os, re, hashlib, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
os.chdir(os.path.join(os.path.dirname(__file__), 'backend'))

from app.database_unified import execute_central

def make_code(nom):
    slug = re.sub(r'[^a-z0-9]+', '_', nom.lower().strip())[:30].strip('_')
    suffix = hashlib.md5(f"{nom}central".encode()).hexdigest()[:4]
    return f"MN_{slug}_{suffix}"

def insert_central(nom, icon, parent_id, ordre, type_, target_id=None):
    code = make_code(nom)
    try:
        rows = execute_central(
            """INSERT INTO APP_Menus (nom, code, icon, parent_id, ordre, type, target_id, actif, is_custom)
               OUTPUT INSERTED.id
               VALUES (?, ?, ?, ?, ?, ?, ?, 1, 0)""",
            (nom, code, icon, parent_id, ordre, type_, target_id),
            use_cache=False
        )
        if rows:
            mid = rows[0]['id']
            print(f"  ok [{type_}] {nom} (id={mid}, parent={parent_id})")
            return mid
        else:
            print(f"  ERREUR [{type_}] {nom} -> pas d'id retourné")
            return None
    except Exception as e:
        print(f"  ERREUR [{type_}] {nom} -> {e}")
        return None

# Check: does Comptabilite already have children in central?
existing = execute_central(
    "SELECT id, nom FROM APP_Menus WHERE parent_id = 266",
    use_cache=False
)
if existing:
    print(f"Comptabilité (id=266) a déjà {len(existing)} enfant(s) en central:")
    for r in existing:
        print(f"  id={r['id']} nom={r['nom']}")
    print("Annulation pour éviter les doublons. Supprimez d'abord ces menus si besoin.")
    sys.exit(0)

PARENT_ID = 266  # Comptabilite in CENTRAL (OptiBoard_SaaS)

# ─── Sous-dossier 1: Tableaux de Bord ───────────────────────────────
print("\n=== Sous-dossier: Tableaux de Bord Comptabilite (CENTRAL OptiBoard_SaaS) ===")
folder_db = insert_central("Tableaux de Bord", "LayoutDashboard", PARENT_ID, 1, "folder")

if folder_db:
    insert_central("Tableau de Bord Comptabilite", "BookOpen",  folder_db, 1, "dashboard", 175)
    insert_central("Tableau de Bord Tresorerie",   "Landmark",  folder_db, 2, "dashboard", 176)

# ─── Sous-dossier 2: Analyses (Pivots) ──────────────────────────────
print("\n=== Sous-dossier: Analyses Comptables (CENTRAL OptiBoard_SaaS) ===")
folder_pv = insert_central("Analyses Comptables", "BarChart2", PARENT_ID, 2, "folder")

if folder_pv:
    insert_central("Resultat par Nature de Compte", "TrendingUp",  folder_pv, 1, "pivot-v2", 111)
    insert_central("Balance par Journal",           "BookOpen",    folder_pv, 2, "pivot-v2", 112)
    insert_central("Balance par Classe Comptable",  "Layers",      folder_pv, 3, "pivot-v2", 113)
    insert_central("Tresorerie par Banque",         "Landmark",    folder_pv, 4, "pivot-v2", 114)
    insert_central("Soldes Clients par Periode",    "Users",       folder_pv, 5, "pivot-v2", 115)
    insert_central("Soldes Fournisseurs par Periode","Truck",      folder_pv, 6, "pivot-v2", 116)

# ─── Sous-dossier 3: Registres (Grids) ──────────────────────────────
print("\n=== Sous-dossier: Registres Comptables (CENTRAL OptiBoard_SaaS) ===")
folder_gv = insert_central("Registres Comptables", "Table", PARENT_ID, 3, "folder")

if folder_gv:
    insert_central("Grand Livre General",     "BookOpen",     folder_gv, 1, "gridview", 331)
    insert_central("Balance Generale",        "Scale",        folder_gv, 2, "gridview", 332)
    insert_central("Journal des Ecritures",   "ScrollText",   folder_gv, 3, "gridview", 333)
    insert_central("Balance Tiers",           "Users",        folder_gv, 4, "gridview", 334)
    insert_central("Echeancier Clients",      "CalendarClock",folder_gv, 5, "gridview", 335)
    insert_central("Echeancier Fournisseurs", "CalendarClock",folder_gv, 6, "gridview", 336)
    insert_central("Detail des Charges",      "Receipt",      folder_gv, 7, "gridview", 337)

print("\nDone! Central menus (OptiBoard_SaaS) created.")

# Verify
count = execute_central("SELECT COUNT(*) as cnt FROM APP_Menus WHERE parent_id IN (SELECT id FROM APP_Menus WHERE parent_id = 266)", use_cache=False)
print(f"Verification: {count[0]['cnt']} menus feuilles créés sous Comptabilité.")
