"""
Corrige la hierarchie dans la CENTRALE (OptiBoard_SaaS)
ET dans le CLIENT KA en meme temps.

- CA par Client     -> sous Ventes
- CA par Commercial -> sous Ventes
"""
import pyodbc
from pathlib import Path

env = {}
for line in (Path(__file__).parent / ".env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()

def conn(db):
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={env['DB_SERVER']};DATABASE={db};"
        f"UID={env['DB_USER']};PWD={env['DB_PASSWORD']};TrustServerCertificate=yes;", timeout=15)

# Mapping : code du menu -> code du dossier parent voulu
MOVES = {
    'GV_CA_CLIENT_DRILL':      'MENU_VENTES',   # CA par Client -> Ventes
    'GV_CA_COMMERCIAL_DRILL':  'MENU_VENTES',   # CA par Commercial -> Ventes
}

print("\n=== Correction hierarchie centrale + client KA ===\n")

for db_name, label in [("OptiBoard_SaaS", "CENTRALE"), ("OptiBoard_cltKA", "CLIENT KA")]:
    print(f"[{label}] {db_name}")
    c = conn(db_name)
    c.autocommit = False
    cur = c.cursor()

    for child_code, parent_code in MOVES.items():
        # Trouver le parent
        cur.execute("SELECT id FROM APP_Menus WHERE code = ?", (parent_code,))
        p = cur.fetchone()
        if not p:
            print(f"    PARENT MANQUANT : {parent_code}")
            continue
        parent_id = p[0]

        # Mettre a jour l'enfant
        # parent_code n'existe que dans les bases client, pas dans la centrale
        has_parent_code = False
        try:
            cur.execute("SELECT TOP 1 parent_code FROM APP_Menus")
            has_parent_code = True
        except Exception:
            pass

        if has_parent_code:
            cur.execute("""
                UPDATE APP_Menus
                SET parent_id = ?, parent_code = ?
                WHERE code = ?
            """, (parent_id, parent_code, child_code))
        else:
            cur.execute("""
                UPDATE APP_Menus SET parent_id = ? WHERE code = ?
            """, (parent_id, child_code))

        if cur.rowcount > 0:
            print(f"    OK : '{child_code}' -> sous '{parent_code}' (id={parent_id})")
        else:
            print(f"    NON TROUVE : '{child_code}' absent de {db_name}")

    c.commit()

    # Afficher la racine resultante
    cur.execute("""
        SELECT nom FROM APP_Menus
        WHERE parent_id IS NULL
        ORDER BY ordre, nom
    """)
    roots = [r[0] for r in cur.fetchall()]
    print(f"    Racine ({len(roots)}) : {', '.join(roots)}")
    c.close()
    print()

print("=== Termine - F5 dans le navigateur ! ===")
