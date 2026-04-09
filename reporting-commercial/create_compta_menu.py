import requests, json, re, hashlib, time

BASE = "http://localhost:8084/api"
H = {"Content-Type": "application/json", "X-DWH-Code": "FO"}

PARENT_ID = 4  # Comptabilite folder ID

def make_code(nom):
    slug = re.sub(r'[^a-z0-9]+', '_', nom.lower().strip())[:30].strip('_')
    suffix = hashlib.md5(f"{nom}{time.time()}".encode()).hexdigest()[:4]
    return f"MN_{slug}_{suffix}"

def post_menu(nom, icon, parent_id, ordre, type_, target_id=None):
    data = {
        "nom": nom,
        "code": make_code(nom),
        "icon": icon,
        "parent_id": parent_id,
        "ordre": ordre,
        "type": type_,
        "target_id": target_id,
        "actif": True,
        "is_public": True,
    }
    r = requests.post(f"{BASE}/menus/", json=data, headers=H)
    resp = r.json()
    if resp.get("success") or resp.get("id"):
        mid = resp.get("id") or resp.get("data", {}).get("id", "?")
        print(f"  ok [{type_}] {nom} (id={mid}, target={target_id})")
        return mid
    else:
        print(f"  ERREUR [{type_}] {nom} -> {resp}")
        return None

# ─── Sous-dossier 1: Tableaux de Bord ───────────────────────────────
print("\n=== Sous-dossier: Tableaux de Bord Comptabilite ===")
folder_db = post_menu("Tableaux de Bord", "LayoutDashboard", PARENT_ID, 1, "folder")

if folder_db:
    post_menu("Tableau de Bord Comptabilite", "BookOpen",   folder_db, 1, "dashboard", 175)
    post_menu("Tableau de Bord Tresorerie",   "Landmark",   folder_db, 2, "dashboard", 176)

# ─── Sous-dossier 2: Analyses (Pivots) ──────────────────────────────
print("\n=== Sous-dossier: Analyses Comptables ===")
folder_pv = post_menu("Analyses Comptables", "BarChart2", PARENT_ID, 2, "folder")

if folder_pv:
    post_menu("Resultat par Nature de Compte", "TrendingUp",  folder_pv, 1, "pivot-v2", 111)
    post_menu("Balance par Journal",           "BookOpen",    folder_pv, 2, "pivot-v2", 112)
    post_menu("Balance par Classe Comptable",  "Layers",      folder_pv, 3, "pivot-v2", 113)
    post_menu("Tresorerie par Banque",         "Landmark",    folder_pv, 4, "pivot-v2", 114)
    post_menu("Soldes Clients par Periode",    "Users",       folder_pv, 5, "pivot-v2", 115)
    post_menu("Soldes Fournisseurs par Periode","Truck",      folder_pv, 6, "pivot-v2", 116)

# ─── Sous-dossier 3: Registres (Grids) ──────────────────────────────
print("\n=== Sous-dossier: Registres Comptables ===")
folder_gv = post_menu("Registres Comptables", "Table", PARENT_ID, 3, "folder")

if folder_gv:
    post_menu("Grand Livre General",     "BookOpen",    folder_gv, 1, "gridview", 331)
    post_menu("Balance Generale",        "Scale",       folder_gv, 2, "gridview", 332)
    post_menu("Journal des Ecritures",   "ScrollText",  folder_gv, 3, "gridview", 333)
    post_menu("Balance Tiers",           "Users",       folder_gv, 4, "gridview", 334)
    post_menu("Echeancier Clients",      "CalendarClock",folder_gv, 5, "gridview", 335)
    post_menu("Echeancier Fournisseurs", "CalendarClock",folder_gv, 6, "gridview", 336)
    post_menu("Detail des Charges",      "Receipt",     folder_gv, 7, "gridview", 337)

print("\nDone!")
