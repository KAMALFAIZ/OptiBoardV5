"""Corrige 'Liste des articles' : trouve le rapport et relie le menu"""
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

print("\n=== Fix 'Liste des articles' ===\n")

client = conn("OptiBoard_cltKA")
client.autocommit = False
cur = client.cursor()

# Chercher dans GridViews
print("[1] Recherche dans APP_GridViews...")
cur.execute("SELECT id, nom, code FROM APP_GridViews WHERE nom LIKE '%article%' OR nom LIKE '%Article%'")
gv_rows = cur.fetchall()
for r in gv_rows:
    print(f"    id={r[0]} | nom='{r[1]}' | code='{r[2]}'")

# Chercher dans Pivots V2
print("\n[2] Recherche dans APP_Pivots_V2...")
cur.execute("SELECT id, nom, code FROM APP_Pivots_V2 WHERE nom LIKE '%article%' OR nom LIKE '%Article%'")
pv_rows = cur.fetchall()
for r in pv_rows:
    print(f"    id={r[0]} | nom='{r[1]}' | code='{r[2]}'")

# Chercher dans Pivots anciens
print("\n[3] Recherche dans APP_Pivots...")
try:
    cur.execute("SELECT id, nom FROM APP_Pivots WHERE nom LIKE '%article%' OR nom LIKE '%Article%'")
    for r in cur.fetchall():
        print(f"    id={r[0]} | nom='{r[1]}'")
except Exception:
    print("    (table absente)")

# Appliquer la correction
best_id   = None
best_type = None
best_nom  = None

if gv_rows:
    best_id   = gv_rows[0][0]
    best_type = 'gridview'
    best_nom  = gv_rows[0][1]
elif pv_rows:
    best_id   = pv_rows[0][0]
    best_type = 'pivot-v2'
    best_nom  = pv_rows[0][1]

if best_id:
    print(f"\n[4] Correction du menu -> type={best_type}, target_id={best_id} ('{best_nom}')")
    cur.execute("""
        UPDATE APP_Menus
        SET type      = ?,
            target_id = ?
        WHERE nom LIKE '%Liste%article%'
    """, (best_type, best_id))
    print(f"    {cur.rowcount} menu(s) mis a jour")

    # Meme correction dans la CENTRALE
    client.commit()
    client.close()

    print(f"\n[5] Correction dans la CENTRALE (OptiBoard_SaaS)...")
    central = conn("OptiBoard_SaaS")
    central.autocommit = False
    cur_c = central.cursor()

    # Chercher le rapport dans la centrale par nom
    if best_type == 'gridview':
        cur_c.execute("SELECT id FROM APP_GridViews WHERE nom LIKE '%article%'")
    else:
        cur_c.execute("SELECT id FROM APP_Pivots_V2 WHERE nom LIKE '%article%'")
    r_central = cur_c.fetchone()
    if r_central:
        cur_c.execute("""
            UPDATE APP_Menus SET type = ?, target_id = ?
            WHERE nom LIKE '%Liste%article%'
        """, (best_type, r_central[0]))
        print(f"    Centrale : target_id={r_central[0]}, type={best_type}")
    else:
        # Juste corriger le type (target_id reste a lier manuellement)
        cur_c.execute("""
            UPDATE APP_Menus SET type = ? WHERE nom LIKE '%Liste%article%'
        """, (best_type,))
        print(f"    Centrale : type corrige en {best_type} (rapport a publier)")
    central.commit()
    central.close()

else:
    print("\n[!] Aucun rapport 'articles' trouve dans le client KA.")
    print("    Allez dans Admin -> Gestion Menus et editez manuellement 'Liste des articles'")
    print("    pour choisir le rapport GridView ou Pivot correspondant.")
    client.close()

print("\n=== Termine — F5 dans le navigateur ===")
