"""Diagnostique et corrige les menus orphelins (sans parent)"""
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

# ── Centrale : hierarchie complete ───────────────────────────────────────────
print("[1] Hierarchie dans la centrale...")
c = conn("OptiBoard_SaaS")
cur_c = c.cursor()
cur_c.execute("""
    SELECT m.code, m.nom, m.type, p.code as parent_code, p.nom as parent_nom
    FROM APP_Menus m
    LEFT JOIN APP_Menus p ON p.id = m.parent_id
    ORDER BY p.nom, m.ordre
""")
central_map = {}   # code -> parent_code
for row in cur_c.fetchall():
    central_map[row[0]] = {'nom': row[1], 'type': row[2],
                           'parent_code': row[3], 'parent_nom': row[4]}
c.close()

# ── Client : trouver les orphelins non-custom ─────────────────────────────────
print("\n[2] Orphelins dans client KA...")
client = conn("OptiBoard_cltKA")
client.autocommit = False
cur = client.cursor()

cur.execute("""
    SELECT id, nom, code, type, parent_code, is_custom
    FROM APP_Menus
    WHERE parent_id IS NULL
      AND ISNULL(is_custom,0) = 0
    ORDER BY nom
""")
orphelins = cur.fetchall()
print(f"    {len(orphelins)} menus sans parent (non-custom) :")

fixes = []
for o in orphelins:
    mid, nom, code, mtype, pcode, custom = o
    # Est-ce un dossier racine legitime ?
    in_central = central_map.get(code, {})
    is_root = in_central.get('parent_code') is None
    if is_root:
        print(f"    [OK ROOT] {nom} ({code})")
    else:
        expected_parent = in_central.get('parent_code', '???')
        print(f"    [ORPHELIN] {nom} | code={code} | parent_attendu={expected_parent}")
        if expected_parent and expected_parent != '???':
            fixes.append((mid, expected_parent, nom))

# ── Corriger les orphelins ────────────────────────────────────────────────────
if fixes:
    print(f"\n[3] Correction de {len(fixes)} orphelins...")
    for mid, parent_code, nom in fixes:
        cur.execute("SELECT id FROM APP_Menus WHERE code = ?", (parent_code,))
        parent_row = cur.fetchone()
        if parent_row:
            cur.execute("UPDATE APP_Menus SET parent_id = ?, parent_code = ? WHERE id = ?",
                        (parent_row[0], parent_code, mid))
            print(f"    OK : '{nom}' -> parent id={parent_row[0]} (code={parent_code})")
        else:
            print(f"    MANQUANT : parent '{parent_code}' absent du client pour '{nom}'")

# ── Supprimer doublon Fiche Client (garder MENU_FICHE_CLIENT seulement) ───────
print("\n[4] Suppression doublon 'Fiche Client'...")
cur.execute("""
    WITH CTE AS (
        SELECT id, ROW_NUMBER() OVER (PARTITION BY nom ORDER BY id ASC) AS rn
        FROM APP_Menus WHERE nom = 'Fiche Client'
    )
    DELETE FROM CTE WHERE rn > 1
""")
print(f"    {cur.rowcount} doublon(s) Fiche Client supprime(s)")

client.commit()

cur.execute("SELECT COUNT(*) FROM APP_Menus WHERE parent_id IS NULL AND ISNULL(is_custom,0)=0")
print(f"\n=== Reste a la racine (non-custom) : {cur.fetchone()[0]} dossiers ===")
cur.execute("SELECT nom FROM APP_Menus WHERE parent_id IS NULL ORDER BY nom")
for r in cur.fetchall():
    print(f"    - {r[0]}")

client.close()
print("\nF5 dans le navigateur !")
