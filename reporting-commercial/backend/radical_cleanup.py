"""
NETTOYAGE RADICAL - kasoft.selfip.net
======================================
1. Liste toutes les bases OptiBoard_* sur kasoft.selfip.net
2. Identifie lesquelles sont legitimes (enregistrees dans APP_DWH avec serveur=kasoft.selfip.net)
3. Supprime TOUTES les autres
"""
import pyodbc, sys

CENTRAL = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=master;UID=sa;PWD=SQL@2019;TrustServerCertificate=yes;"

def connect():
    return pyodbc.connect(CENTRAL, timeout=15, autocommit=True)

# ── 1. Lister toutes les bases OptiBoard_* ────────────────────────────────────
print("\n=== BASES OptiBoard_* sur kasoft.selfip.net ===")
conn = connect()
cur = conn.cursor()
cur.execute("SELECT name FROM sys.databases WHERE name LIKE 'OptiBoard%' ORDER BY name")
all_optiboard = [r[0] for r in cur.fetchall()]
print(f"Trouvees : {len(all_optiboard)}")
for db in all_optiboard:
    print(f"  - {db}")

# ── 2. Bases legitimes = DWH enregistres avec serveur kasoft ─────────────────
print("\n=== BASES LEGITIMES (enregistrees dans APP_DWH) ===")
cur.execute("USE OptiBoard_SaaS")
cur.execute("""
    SELECT code, base_optiboard, serveur_optiboard, serveur_dwh
    FROM APP_DWH
    WHERE actif = 1 OR actif = 0
""")
rows = cur.fetchall()

legitimate = set()
for r in rows:
    code, base_optiboard, srv_opti, srv_dwh = r
    effective_srv = srv_opti or srv_dwh or ''
    effective_base = base_optiboard or f"OptiBoard_clt{code}"
    # Legitime sur kasoft si le serveur est kasoft (pas localhost)
    is_kasoft = effective_srv not in ('.', 'localhost', '127.0.0.1', '(local)', '')
    if is_kasoft:
        legitimate.add(effective_base)
        print(f"  GARDE  : {effective_base} (DWH={code}, srv={effective_srv})")

# ── 3. Bases a supprimer ──────────────────────────────────────────────────────
# Ne JAMAIS supprimer ces bases systeme
PROTECTED = {'OptiBoard_SaaS', 'OptiBoard_Licenses'}
to_drop = [db for db in all_optiboard if db not in legitimate and db not in PROTECTED]
print(f"\n=== BASES A SUPPRIMER ({len(to_drop)}) ===")
for db in to_drop:
    print(f"  DROP   : {db}")

if not to_drop:
    print("Rien a supprimer.")
    conn.close()
    sys.exit(0)

# ── 4. Confirmation ───────────────────────────────────────────────────────────
print(f"\n{'='*55}")
print(f"  ATTENTION : {len(to_drop)} base(s) vont etre supprimees")
print(f"  sur kasoft.selfip.net de facon IRREVERSIBLE !")
print(f"{'='*55}")
rep = input("\nTaper OUI pour confirmer : ").strip()
if rep != "OUI":
    print("Annule.")
    conn.close()
    sys.exit(0)

# ── 5. Suppression ────────────────────────────────────────────────────────────
print("\n=== SUPPRESSION ===")
for db in to_drop:
    try:
        cur.execute(f"ALTER DATABASE [{db}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE")
        cur.execute(f"DROP DATABASE [{db}]")
        print(f"  [OK]  {db} supprimee")
    except Exception as e:
        print(f"  [ERR] {db} : {e}")

conn.close()

# ── 6. Verification finale ────────────────────────────────────────────────────
print("\n=== VERIFICATION FINALE ===")
conn2 = connect()
cur2 = conn2.cursor()
cur2.execute("SELECT name FROM sys.databases WHERE name LIKE 'OptiBoard%' ORDER BY name")
remaining = [r[0] for r in cur2.fetchall()]
print(f"Bases restantes ({len(remaining)}) :")
for db in remaining:
    print(f"  - {db}")
conn2.close()
print("\nNettoyage termine.")
