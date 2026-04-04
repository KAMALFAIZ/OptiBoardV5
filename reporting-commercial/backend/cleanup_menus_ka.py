"""
Nettoyage direct des menus en double - Client KA
Connexion directe SQL Server, pas besoin du backend
"""
import pyodbc
import sys
from pathlib import Path

# Lire le .env
env = {}
env_path = Path(__file__).parent / ".env"
for line in env_path.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()

CENTRAL_SERVER = env.get("DB_SERVER", "kasoft.selfip.net")
CENTRAL_DB     = env.get("DB_NAME",   "OptiBoard_SaaS")
USER           = env.get("DB_USER",   "sa")
PASSWORD       = env.get("DB_PASSWORD", "")

def get_conn(server, database):
    cs = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={server};DATABASE={database};"
        f"UID={USER};PWD={PASSWORD};"
        f"TrustServerCertificate=yes;"
    )
    return pyodbc.connect(cs, timeout=15)

print("=" * 55)
print("  Nettoyage menus client KA")
print("=" * 55)

# 1. Trouver la base client KA depuis la table centrale
print(f"\n[1/4] Connexion a {CENTRAL_SERVER}/{CENTRAL_DB}...")
try:
    central = get_conn(CENTRAL_SERVER, CENTRAL_DB)
    cursor  = central.cursor()
    print("      OK")
except Exception as e:
    print(f"      ERREUR : {e}")
    sys.exit(1)

print("\n[2/4] Recherche config client KA...")
cursor.execute("""
    SELECT d.code, d.nom,
           ISNULL(d.serveur_optiboard, d.serveur_dwh) as server,
           ISNULL(d.base_optiboard,    'OptiBoard_cltKA') as db_name,
           ISNULL(d.user_optiboard,    d.user_dwh)    as db_user,
           ISNULL(d.password_optiboard, d.password_dwh) as db_pass
    FROM APP_DWH d
    WHERE d.code = 'KA' AND d.actif = 1
""")
row = cursor.fetchone()
if not row:
    print("      Client KA introuvable dans APP_DWH !")
    # Essayer avec le meme serveur
    client_server = CENTRAL_SERVER
    client_db     = "OptiBoard_cltKA"
    client_user   = USER
    client_pass   = PASSWORD
else:
    client_server = row[2] or CENTRAL_SERVER
    client_db     = row[3]
    client_user   = row[4] or USER
    client_pass   = row[5] or PASSWORD
    print(f"      {row[1]} -> {client_server}/{client_db}")

central.close()

# 2. Connexion base client
print(f"\n[3/4] Connexion a {client_server}/{client_db}...")
try:
    client = get_conn(client_server, client_db)
    client.autocommit = False
    cur = client.cursor()
    print("      OK")
except Exception as e:
    print(f"      ERREUR : {e}")
    sys.exit(1)

# 3. Compter avant
cur.execute("SELECT COUNT(*) FROM APP_Menus")
total_avant = cur.fetchone()[0]
print(f"\n      Menus avant nettoyage : {total_avant}")

# Afficher les doublons
cur.execute("""
    SELECT code, COUNT(*) as nb
    FROM APP_Menus
    WHERE code IS NOT NULL AND code != ''
    GROUP BY code HAVING COUNT(*) > 1
    ORDER BY nb DESC
""")
doublons = cur.fetchall()
if doublons:
    print(f"\n      Doublons detectes ({len(doublons)} codes) :")
    for d in doublons[:10]:
        print(f"        code={d[0]}  x{d[1]}")
else:
    print("      Aucun doublon par code detecte")

# 4. Nettoyer
print(f"\n[4/4] Nettoyage...")

# Supprimer doublons par code (garder MAX id)
cur.execute("""
    WITH CTE AS (
        SELECT id,
               ROW_NUMBER() OVER (
                   PARTITION BY code
                   ORDER BY id DESC
               ) AS rn
        FROM APP_Menus
        WHERE code IS NOT NULL AND code != ''
    )
    DELETE FROM CTE WHERE rn > 1
""")
suppr_doublons = cur.rowcount
print(f"      Doublons supprimes  : {suppr_doublons}")

# Supprimer menus master sans code (is_custom=0)
cur.execute("""
    DELETE FROM APP_Menus
    WHERE ISNULL(is_custom, 0) = 0
      AND (code IS NULL OR code = '')
""")
suppr_vides = cur.rowcount
print(f"      Orphelins supprimes : {suppr_vides}")

# Reconstruire parent_id depuis parent_code
cur.execute("""
    UPDATE APP_Menus SET parent_id = NULL
    WHERE ISNULL(is_custom, 0) = 0
""")
print(f"      parent_id reinitialise pour menus master")

cur.execute("""
    UPDATE child
    SET    child.parent_id = parent.id
    FROM   APP_Menus child
    JOIN   APP_Menus parent ON parent.code = child.parent_code
    WHERE  child.parent_code IS NOT NULL AND child.parent_code != ''
""")
remapped = cur.rowcount
print(f"      Hierarchie reconstruite : {remapped} menus")

client.commit()

cur.execute("SELECT COUNT(*) FROM APP_Menus")
total_apres = cur.fetchone()[0]

client.close()

print(f"\n{'=' * 55}")
print(f"  Nettoyage termine !")
print(f"  Avant : {total_avant}  →  Apres : {total_apres}")
print(f"  Supprimes : {total_avant - total_apres}")
print(f"{'=' * 55}")
print("\nRelancez le frontend pour voir le menu corrige.")
