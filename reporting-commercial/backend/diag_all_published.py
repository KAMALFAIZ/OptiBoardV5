"""
DIAGNOSTIC : Vérifie toutes les entrées APP_ETL_Tables_Published dans tous les DWH.
Détecte les codes avec espaces (invalides car ils ne matchent pas APP_ETL_Tables_Config).
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database_unified import get_central_connection
import pyodbc

conn_c = get_central_connection()
cur_c  = conn_c.cursor()

# Lire tous les codes valides depuis APP_ETL_Tables_Config
cur_c.execute("SELECT code FROM APP_ETL_Tables_Config WHERE actif = 1")
valid_codes = set(r[0] for r in cur_c.fetchall())
print(f"Codes valides dans APP_ETL_Tables_Config: {len(valid_codes)}")

# Lire les DWH
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

db_server = os.getenv('DB_SERVER', 'kasoft.selfip.net')
db_user   = os.getenv('DB_USER', 'sa')
db_pwd    = os.getenv('DB_PASSWORD', '')

print("\n" + "=" * 80)
print("ÉTAT DES APP_ETL_Tables_Published PAR DWH")
print("=" * 80)

for row in dwh_list:
    dwh_code, nom, db_name, serveur, user_dwh, pwd_dwh = row
    srv = serveur or db_server
    usr = user_dwh or db_user
    pwd = pwd_dwh  or db_pwd
    db  = db_name  or f"OptiBoard_{dwh_code}"

    print(f"\n[{dwh_code}] {nom} → {db}")
    try:
        cs = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={srv};DATABASE={db};"
            f"UID={usr};PWD={pwd};TrustServerCertificate=yes;"
        )
        conn_d = pyodbc.connect(cs, autocommit=True)
        cur_d  = conn_d.cursor()

        cur_d.execute("""
            SELECT code, is_enabled
            FROM APP_ETL_Tables_Published
            ORDER BY code
        """)
        pub_rows = cur_d.fetchall()
        conn_d.close()

        invalid = []
        for r in pub_rows:
            code = r[0]
            if code not in valid_codes:
                invalid.append((code, r[1]))

        if invalid:
            print(f"  ✗ {len(invalid)} CODE(S) INVALIDE(S) (sans correspondance dans APP_ETL_Tables_Config):")
            for code, enabled in invalid:
                print(f"      code={repr(code)}, enabled={enabled}")
        else:
            print(f"  ✓ {len(pub_rows)} tables publiées, tous les codes valides")

    except Exception as e:
        print(f"  ERREUR connexion: {e}")

print("\n" + "=" * 80)
print("FIN DIAGNOSTIC")
print("=" * 80)
