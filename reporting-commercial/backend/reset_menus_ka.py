"""
RESET COMPLET menus client KA
1. Sauvegarde les menus custom (is_custom=1)
2. Supprime TOUS les menus master (is_custom=0)
3. Reinsere depuis la centrale avec hierarchie correcte
4. Restaure les menus custom
"""
import pyodbc
from pathlib import Path

env = {}
for line in (Path(__file__).parent / ".env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()

SRV = env['DB_SERVER']
USR = env['DB_USER']
PWD = env['DB_PASSWORD']

def conn(db):
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SRV};DATABASE={db};"
        f"UID={USR};PWD={PWD};TrustServerCertificate=yes;", timeout=15)

print("\n" + "="*55)
print("  RESET COMPLET menus client KA")
print("="*55 + "\n")

# ─── 1. Lire tous les menus depuis la CENTRALE avec hierarchie ───────────────
print("[1/5] Lecture menus depuis OptiBoard_SaaS...")
central = conn("OptiBoard_SaaS")
cur_c = central.cursor()
cur_c.execute("""
    SELECT m.nom, m.code, m.icon, m.url,
           p.code  AS parent_code,
           m.ordre, m.type,
           m.target_id, m.actif
    FROM   APP_Menus m
    LEFT   JOIN APP_Menus p ON p.id = m.parent_id
    WHERE  m.code IS NOT NULL AND m.code != ''
    ORDER  BY m.ordre, m.id
""")
master_menus = cur_c.fetchall()
central.close()
print(f"      {len(master_menus)} menus lus depuis la centrale")

# ─── 2. Connexion client KA ──────────────────────────────────────────────────
print("\n[2/5] Connexion OptiBoard_cltKA...")
client = conn("OptiBoard_cltKA")
client.autocommit = False
cur = client.cursor()

cur.execute("SELECT COUNT(*) FROM APP_Menus")
print(f"      Menus avant reset : {cur.fetchone()[0]}")

# ─── 3. Sauvegarder menus custom (is_custom=1) ───────────────────────────────
print("\n[3/5] Sauvegarde menus personnalises (is_custom=1)...")
cur.execute("""
    SELECT nom, code, icon, url, parent_code, ordre, type,
           target_id, actif, is_custom, is_customized
    FROM   APP_Menus
    WHERE  ISNULL(is_custom, 0) = 1
""")
custom_menus = cur.fetchall()
print(f"      {len(custom_menus)} menus custom sauvegardes")
for m in custom_menus:
    print(f"        -> nom='{m[0]}' code='{m[1]}'")

# ─── 4. Supprimer TOUS les menus master ──────────────────────────────────────
print("\n[4/5] Suppression de tous les menus master (is_custom=0)...")
cur.execute("DELETE FROM APP_Menus WHERE ISNULL(is_custom, 0) = 0")
deleted = cur.rowcount
print(f"      {deleted} menus supprimes")

# ─── 5. Reinsertion propre depuis la centrale ─────────────────────────────────
print("\n[5/5] Reinsertion depuis la centrale...")

insert_sql = """
    INSERT INTO APP_Menus
        (nom, code, icon, url, parent_code, ordre, type,
         target_id, actif, is_custom, is_customized)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
"""

inserted = 0
for m in master_menus:
    nom, code, icon, url, parent_code, ordre, mtype, target_id, actif = m
    try:
        cur.execute(insert_sql, (nom, code, icon, url, parent_code,
                                  ordre, mtype, target_id, actif))
        inserted += 1
    except Exception as e:
        print(f"        ERREUR insert '{nom}': {e}")

print(f"      {inserted} menus inseres")

# ─── 6. Reconstruire parent_id ───────────────────────────────────────────────
cur.execute("""
    UPDATE child
    SET    child.parent_id = parent.id
    FROM   APP_Menus child
    JOIN   APP_Menus parent ON parent.code = child.parent_code
    WHERE  child.parent_code IS NOT NULL AND child.parent_code != ''
""")
remapped = cur.rowcount
print(f"      Hierarchie reconstruite : {remapped} menus")

# ─── 7. Restaurer menus custom ───────────────────────────────────────────────
if custom_menus:
    print(f"\n      Restauration {len(custom_menus)} menus custom...")
    for m in custom_menus:
        # Eviter le doublon Fiche Client si deja present (meme code)
        cur.execute("SELECT COUNT(*) FROM APP_Menus WHERE code = ?", (m[1],))
        if cur.fetchone()[0] == 0:
            cur.execute("""
                INSERT INTO APP_Menus
                    (nom, code, icon, url, parent_code, ordre, type,
                     target_id, actif, is_custom, is_customized)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, m)
            print(f"        + Restaure '{m[0]}'")
        else:
            print(f"        ~ Ignore '{m[0]}' (code deja present)")

# ─── Commit final ─────────────────────────────────────────────────────────────
client.commit()

cur.execute("SELECT COUNT(*) FROM APP_Menus")
total_apres = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM APP_Menus WHERE parent_id IS NULL")
a_racine = cur.fetchone()[0]

client.close()

print(f"\n{'='*55}")
print(f"  RESET TERMINE !")
print(f"  Menus total    : {total_apres}")
print(f"  A la racine    : {a_racine} (dossiers principaux)")
print(f"  Avec parent    : {total_apres - a_racine}")
print(f"{'='*55}")
print("\nAppuyez sur F5 dans le navigateur pour voir le resultat.")
