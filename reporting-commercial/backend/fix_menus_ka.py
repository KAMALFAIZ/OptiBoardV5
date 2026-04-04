"""
Fix complet menus client KA
1. Verifie la hierarchie dans la base centrale
2. Supprime les doublons par NOM (garde le plus ancien = id MIN)
3. Reconstruit la hierarchie depuis la base centrale
"""
import pyodbc, sys
from pathlib import Path

env = {}
for line in (Path(__file__).parent / ".env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()

SRV  = env['DB_SERVER']
USR  = env['DB_USER']
PWD  = env['DB_PASSWORD']

def conn(db):
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SRV};DATABASE={db};"
        f"UID={USR};PWD={PWD};TrustServerCertificate=yes;", timeout=15)

print("\n=== Fix menus client KA ===\n")

# ── Verifier hierarchie centrale ─────────────────────────────────────────────
print("[1/5] Verification hierarchie centrale (OptiBoard_SaaS)...")
c_central = conn("OptiBoard_SaaS")
cur_c = c_central.cursor()

cur_c.execute("""
    SELECT COUNT(*) FROM APP_Menus
    WHERE parent_id IS NOT NULL
""")
has_hierarchy = cur_c.fetchone()[0]
print(f"      Menus avec parent_id dans centrale : {has_hierarchy}")

# Lire tous les menus du central avec leur parent_code calcule
cur_c.execute("""
    SELECT m.id, m.nom, m.code, m.parent_id,
           p.code as parent_code,
           m.ordre, m.type, m.icon, m.actif
    FROM APP_Menus m
    LEFT JOIN APP_Menus p ON p.id = m.parent_id
    ORDER BY m.ordre, m.id
""")
central_menus = cur_c.fetchall()
print(f"      Total menus dans centrale : {len(central_menus)}")
c_central.close()

# Construire map nom -> (code, parent_code, ordre, type, icon, actif)
# Pour reconstruire proprement le client
central_by_nom = {}
for m in central_menus:
    central_by_nom[m[1]] = {
        'code':        m[2],
        'parent_code': m[4],
        'ordre':       m[5],
        'type':        m[6],
        'icon':        m[7],
        'actif':       m[8],
    }

# ── Connexion client KA ───────────────────────────────────────────────────────
print("\n[2/5] Connexion client KA (OptiBoard_cltKA)...")
c_client = conn("OptiBoard_cltKA")
c_client.autocommit = False
cur = c_client.cursor()

cur.execute("SELECT COUNT(*) FROM APP_Menus")
total_avant = cur.fetchone()[0]
print(f"      Menus avant : {total_avant}")

# ── Supprimer doublons par NOM (garder MIN id = le plus ancien) ───────────────
print("\n[3/5] Suppression des doublons par NOM...")
cur.execute("""
    WITH CTE AS (
        SELECT id,
               ROW_NUMBER() OVER (
                   PARTITION BY nom
                   ORDER BY id ASC        -- garder le plus ancien (id MIN)
               ) AS rn
        FROM APP_Menus
        WHERE ISNULL(is_custom, 0) = 0   -- seulement les menus master
    )
    DELETE FROM CTE WHERE rn > 1
""")
suppr = cur.rowcount
print(f"      Doublons supprimes : {suppr}")

# ── Mettre a jour parent_code depuis la centrale (par correspondance nom) ──────
print("\n[4/5] Mise a jour parent_code depuis la centrale...")
updated = 0
not_found = 0
for m in central_menus:
    nom         = m[1]
    code        = m[2]
    parent_code = m[4]   # code du parent dans la centrale

    # Mettre a jour le menu client qui a ce nom
    # On met aussi a jour le code pour le normaliser
    cur.execute("""
        UPDATE APP_Menus
        SET    parent_code  = ?,
               code         = ?,
               ordre        = ?,
               actif        = ?
        WHERE  nom = ?
          AND  ISNULL(is_custom, 0) = 0
    """, (parent_code, code, m[5], m[8], nom))
    if cur.rowcount > 0:
        updated += 1
    else:
        not_found += 1

print(f"      Mis a jour  : {updated}")
print(f"      Non trouves : {not_found}")

# ── Reconstruire parent_id depuis parent_code ─────────────────────────────────
print("\n[5/5] Reconstruction de la hierarchie (parent_id)...")

# Reset parent_id pour les menus master uniquement
cur.execute("UPDATE APP_Menus SET parent_id = NULL WHERE ISNULL(is_custom, 0) = 0")

# Self-join : parent_id = id du menu dont code = parent_code
cur.execute("""
    UPDATE child
    SET    child.parent_id = parent.id
    FROM   APP_Menus child
    JOIN   APP_Menus parent ON parent.code = child.parent_code
    WHERE  child.parent_code IS NOT NULL
      AND  child.parent_code != ''
""")
remapped = cur.rowcount
print(f"      Hierarchie reconstruite : {remapped} menus")

# Verifier les orphelins
cur.execute("""
    SELECT COUNT(*) FROM APP_Menus
    WHERE ISNULL(is_custom, 0) = 0
      AND parent_code IS NOT NULL AND parent_code != ''
      AND parent_id IS NULL
""")
orphelins = cur.fetchone()[0]
if orphelins > 0:
    print(f"      ATTENTION : {orphelins} menus avec parent_code non resolu")

c_client.commit()

cur.execute("SELECT COUNT(*) FROM APP_Menus")
total_apres = cur.fetchone()[0]
c_client.close()

print(f"\n=== Termine ===")
print(f"Avant : {total_avant}  ->  Apres : {total_apres}")
print(f"Supprimes : {total_avant - total_apres}")
print(f"\nRafraichissez le navigateur (F5)")
