"""
FIX Echeances_Achats / Echeances_Ventes pour AMM :
1. Vérifie si F_ECHEANCES existe dans Sage AMM
2. Si absent → désactive ces tables dans APP_ETL_Tables_Published pour AMM
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database_unified import get_central_connection
import pyodbc

conn = get_central_connection()
cur  = conn.cursor()

# Colonnes correctes : serveur_sage, base_sage, user_sage, password_sage
cur.execute("""
    SELECT d.code, d.nom, s.serveur_sage, s.base_sage, s.user_sage, s.password_sage
    FROM APP_DWH d
    JOIN APP_DWH_Sources s ON s.dwh_code = d.code
    WHERE d.actif = 1 AND s.actif = 1
    ORDER BY d.code
""")
sage_sources = cur.fetchall()
conn.close()

print("=" * 60)
print("Vérification F_ECHEANCES dans les bases Sage")
print("=" * 60)

dwh_no_echeances = []

for row in sage_sources:
    dwh_code, nom, sage_srv, sage_db, sage_usr, sage_pwd = row
    print(f"\n[{dwh_code}] {nom} → {sage_srv}/{sage_db}")
    try:
        cs = (f"DRIVER={{ODBC Driver 17 for SQL Server}};"
              f"SERVER={sage_srv};DATABASE={sage_db};"
              f"UID={sage_usr};PWD={sage_pwd};TrustServerCertificate=yes;")
        conn_sage = pyodbc.connect(cs, autocommit=True)
        cur_sage  = conn_sage.cursor()

        cur_sage.execute("SELECT COUNT(*) FROM sys.tables WHERE LOWER(name)='f_echeances'")
        exists = cur_sage.fetchone()[0]
        if exists:
            cur_sage.execute("SELECT COUNT(*) FROM F_ECHEANCES")
            cnt = cur_sage.fetchone()[0]
            print(f"  ✓ F_ECHEANCES existe ({cnt} lignes)")
        else:
            print(f"  ✗ F_ECHEANCES ABSENTE → sera désactivée")
            dwh_no_echeances.append(dwh_code)
            # Chercher des tables similaires
            cur_sage.execute("""
                SELECT name FROM sys.tables
                WHERE LOWER(name) LIKE '%ech%' ORDER BY name
            """)
            alts = [r[0] for r in cur_sage.fetchall()]
            if alts:
                print(f"  Tables similaires: {alts[:5]}")

        conn_sage.close()
    except Exception as e:
        print(f"  ERREUR connexion Sage: {e}")
        dwh_no_echeances.append(dwh_code)

print(f"\n\nDWH sans F_ECHEANCES : {dwh_no_echeances}")

# Désactiver Echeances dans APP_ETL_Tables_Published pour ces DWH
if dwh_no_echeances:
    srv_c = os.getenv('DB_SERVER', 'kasoft.selfip.net')
    usr_c = os.getenv('DB_USER', 'sa')
    pwd_c = os.getenv('DB_PASSWORD', '')

    conn2 = get_central_connection()
    cur2  = conn2.cursor()
    cur2.execute("""
        SELECT d.code, ISNULL(c.db_name, d.base_dwh) AS db_name,
               d.serveur_dwh, d.user_dwh, d.password_dwh
        FROM APP_DWH d LEFT JOIN APP_ClientDB c ON c.dwh_code = d.code
        WHERE d.actif = 1
    """)
    dwh_list = {r[0]: r for r in cur2.fetchall()}
    conn2.close()

    print("\n" + "=" * 60)
    print("Désactivation dans APP_ETL_Tables_Published")
    print("=" * 60)

    for dwh_code in dwh_no_echeances:
        if dwh_code not in dwh_list:
            continue
        row = dwh_list[dwh_code]
        _, db_name, serveur, user_dwh, pwd_dwh = row
        srv = serveur or srv_c
        usr = user_dwh or usr_c
        pwd = pwd_dwh  or pwd_c
        db  = db_name  or f"OptiBoard_{dwh_code}"

        print(f"\n  [{dwh_code}] → {db}")
        try:
            cs = (f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                  f"SERVER={srv};DATABASE={db};"
                  f"UID={usr};PWD={pwd};TrustServerCertificate=yes;")
            conn_d = pyodbc.connect(cs, autocommit=True)
            cur_d  = conn_d.cursor()
            for code in ['Echeances_Achats', 'Echeances_Ventes']:
                cur_d.execute("UPDATE APP_ETL_Tables_Published SET is_enabled=0 WHERE code=?", (code,))
                if cur_d.rowcount > 0:
                    print(f"    ✓ {code} désactivé")
                else:
                    print(f"    - {code} non trouvé")
            conn_d.close()
        except Exception as e:
            print(f"    ERREUR: {e}")
else:
    print("\nTous les DWH ont F_ECHEANCES → aucune désactivation nécessaire")

print("\nFIX TERMINÉ")
