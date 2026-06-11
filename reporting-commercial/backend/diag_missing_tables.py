"""
DIAGNOSTIC : Vérifie quelles tables cibles sont absentes dans les DWH.
Une table absente = sync a toujours échoué.
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database_unified import get_central_connection
import pyodbc

conn_c = get_central_connection()
cur_c  = conn_c.cursor()

cur_c.execute("""
    SELECT code, target_table
    FROM APP_ETL_Tables_Config
    WHERE actif = 1
    ORDER BY code
""")
config_tables = {r[0]: r[1] for r in cur_c.fetchall()}

cur_c.execute("""
    SELECT d.code, d.nom, ISNULL(c.db_name, d.base_dwh) AS db_name,
           d.serveur_dwh, d.user_dwh, d.password_dwh
    FROM APP_DWH d
    LEFT JOIN APP_ClientDB c ON c.dwh_code = d.code
    WHERE d.actif = 1
    ORDER BY d.code
""")
dwh_list = cur_c.fetchall()
conn_c.close()

srv_c = os.getenv('DB_SERVER', 'kasoft.selfip.net')
usr_c = os.getenv('DB_USER', 'sa')
pwd_c = os.getenv('DB_PASSWORD', '')

print("=" * 80)
print("TABLES ABSENTES DANS LES DWH (sync jamais réussi)")
print("=" * 80)

for row in dwh_list:
    dwh_code, nom, db_name, serveur, user_dwh, pwd_dwh = row
    srv = serveur or srv_c
    usr = user_dwh or usr_c
    pwd = pwd_dwh  or pwd_c
    db  = db_name  or f"OptiBoard_{dwh_code}"

    print(f"\n[{dwh_code}] {nom} → {db}")
    try:
        cs = (f"DRIVER={{ODBC Driver 17 for SQL Server}};"
              f"SERVER={srv};DATABASE={db};"
              f"UID={usr};PWD={pwd};TrustServerCertificate=yes;")
        conn_d = pyodbc.connect(cs, autocommit=True)
        cur_d  = conn_d.cursor()

        # Lister toutes les tables existantes dans ce DWH
        cur_d.execute("SELECT name FROM sys.tables ORDER BY name")
        existing_tables = set(r[0] for r in cur_d.fetchall())

        missing = []
        present = []
        for code, target in config_tables.items():
            if target not in existing_tables:
                missing.append((code, target))
            else:
                cur_d.execute(f"SELECT COUNT(*) FROM [{target}]")
                cnt = cur_d.fetchone()[0]
                present.append((code, target, cnt))

        if missing:
            print(f"  ✗ TABLES ABSENTES ({len(missing)}):")
            for code, target in missing:
                print(f"      [{code}] → {target}")
        else:
            print(f"  ✓ Toutes les tables présentes ({len(present)})")

        if present:
            print(f"  ✓ Tables présentes ({len(present)}):")
            for code, target, cnt in present:
                print(f"      {target} : {cnt} lignes")

        conn_d.close()
    except Exception as e:
        print(f"  ERREUR: {e}")

print("\n" + "=" * 80)
print("FIN DIAGNOSTIC")
print("=" * 80)
