"""
FIX : Supprime les doublons dans APP_ETL_Tables_Published pour le DWH KA.
Le DWH KA a deux entrées pour Imputation factures des achats :
  - code='Imputation factures des achats' (avec espaces, invalide - SUPPRIMER)
  - code='Imputation_Factures_Achats' (avec underscore, valide - GARDER)
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database_unified import get_central_connection
import pyodbc

conn_c = get_central_connection()
cur_c  = conn_c.cursor()

print("=" * 70)
print("FIX - Doublons APP_ETL_Tables_Published (DWH KA)")
print("=" * 70)

# Récupérer les infos du DWH KA
cur_c.execute("""
    SELECT d.code, ISNULL(c.db_name, d.base_dwh) AS db_name,
           d.serveur_dwh, d.user_dwh, d.password_dwh
    FROM APP_DWH d
    LEFT JOIN APP_ClientDB c ON c.dwh_code = d.code
    WHERE d.code = 'KA' AND d.actif = 1
""")
dwh = cur_c.fetchone()
conn_c.close()

db_server = os.getenv('DB_SERVER', 'kasoft.selfip.net')
db_user   = os.getenv('DB_USER', 'sa')
db_pwd    = os.getenv('DB_PASSWORD', '')

if not dwh:
    print("  DWH KA non trouvé. Rien à faire.")
else:
    dwh_code, db_name, serveur, user_dwh, pwd_dwh = dwh
    srv = serveur or db_server
    usr = user_dwh or db_user
    pwd = pwd_dwh  or db_pwd
    db  = db_name  or f"OptiBoard_{dwh_code}"

    print(f"\nConnexion: {srv}/{db}")
    try:
        cs = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={srv};DATABASE={db};"
            f"UID={usr};PWD={pwd};TrustServerCertificate=yes;"
        )
        conn_d = pyodbc.connect(cs, autocommit=True)
        cur_d  = conn_d.cursor()

        # Lister les doublons actuels
        print("\n[Avant] Entrées 'imputation' dans APP_ETL_Tables_Published:")
        cur_d.execute("""
            SELECT code, table_name, target_table, is_enabled
            FROM APP_ETL_Tables_Published
            WHERE LOWER(code) LIKE '%imputation%'
               OR LOWER(table_name) LIKE '%imputation%'
            ORDER BY code
        """)
        rows = cur_d.fetchall()
        for r in rows:
            print(f"  code={repr(r[0])}, enabled={r[3]}")

        # Supprimer les entrées avec espaces (invalides)
        invalid_codes = [
            'Imputation factures des achats',
            'Imputation les factures des ventes',
        ]

        deleted = 0
        for bad_code in invalid_codes:
            cur_d.execute(
                "DELETE FROM APP_ETL_Tables_Published WHERE code = ?",
                (bad_code,)
            )
            if cur_d.rowcount > 0:
                deleted += cur_d.rowcount
                print(f"\n  ✓ Supprimé: code='{bad_code}' ({cur_d.rowcount} ligne)")
            else:
                print(f"\n  - Pas trouvé: code='{bad_code}'")

        print(f"\n  Total supprimé: {deleted} ligne(s)")

        # Vérification finale
        print("\n[Après] Entrées 'imputation' dans APP_ETL_Tables_Published:")
        cur_d.execute("""
            SELECT code, table_name, target_table, is_enabled
            FROM APP_ETL_Tables_Published
            WHERE LOWER(code) LIKE '%imputation%'
               OR LOWER(table_name) LIKE '%imputation%'
            ORDER BY code
        """)
        rows = cur_d.fetchall()
        for r in rows:
            print(f"  code={repr(r[0])}, enabled={r[3]}")

        conn_d.close()
    except Exception as e:
        print(f"  ERREUR: {e}")

print("\n" + "=" * 70)
print("FIN")
print("=" * 70)
