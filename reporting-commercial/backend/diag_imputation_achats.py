"""
DIAGNOSTIC : Vérifie la configuration d'Imputation factures des achats dans toutes les tables ETL.
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database_unified import get_central_connection

conn_c = get_central_connection()
cur_c  = conn_c.cursor()

print("=" * 80)
print("DIAGNOSTIC - Imputation factures des achats")
print("=" * 80)

# 1. APP_ETL_Tables_Config - recherche large
print("\n[1] APP_ETL_Tables_Config (centrale) - recherche 'imputation' et 'achat':")
cur_c.execute("""
    SELECT code, table_name, target_table, actif,
           LEN(ISNULL(source_query,'')) AS sq_len,
           LEFT(ISNULL(source_query,''), 100) AS sq_preview
    FROM APP_ETL_Tables_Config
    WHERE LOWER(code) LIKE '%imputation%'
       OR LOWER(table_name) LIKE '%imputation%'
       OR LOWER(target_table) LIKE '%imputation%'
    ORDER BY code
""")
rows = cur_c.fetchall()
if rows:
    for r in rows:
        print(f"  code         = {repr(r[0])}")
        print(f"  table_name   = {repr(r[1])}")
        print(f"  target_table = {repr(r[2])}")
        print(f"  actif        = {r[3]}")
        print(f"  sq_len       = {r[4]}")
        print(f"  sq_preview   = {repr(r[5])}")
        print()
else:
    print("  AUCUNE LIGNE TROUVÉE")

# 2. APP_ETL_Tables_Config - TOUTES les tables pour voir les codes exacts
print("\n[2] APP_ETL_Tables_Config - TOUTES les tables (code + sq_len):")
cur_c.execute("""
    SELECT code, table_name, target_table, actif,
           LEN(ISNULL(source_query,'')) AS sq_len
    FROM APP_ETL_Tables_Config
    ORDER BY code
""")
rows = cur_c.fetchall()
if rows:
    for r in rows:
        sq_status = "OK" if r[4] > 50 else ("VIDE" if r[4] == 0 else "COURT")
        marker = "!!!" if sq_status != "OK" else "   "
        print(f"  {marker} {sq_status:5} len={r[4]:5}  code={repr(r[0])}")
else:
    print("  AUCUNE LIGNE")

# 3. APP_ETL_Agent_Tables - recherche imputation
print("\n[3] APP_ETL_Agent_Tables - recherche 'imputation' et 'achat':")
cur_c.execute("""
    SELECT agent_id, table_name, target_table, is_enabled,
           LEN(ISNULL(source_query,'')) AS sq_len,
           LEFT(ISNULL(source_query,''), 150) AS sq_preview
    FROM APP_ETL_Agent_Tables
    WHERE LOWER(table_name) LIKE '%imputation%'
       OR LOWER(target_table) LIKE '%imputation%'
    ORDER BY table_name
""")
rows = cur_c.fetchall()
if rows:
    for r in rows:
        print(f"  agent_id     = {r[0][:16]}...")
        print(f"  table_name   = {repr(r[1])}")
        print(f"  target_table = {repr(r[2])}")
        print(f"  is_enabled   = {r[3]}")
        print(f"  sq_len       = {r[4]}")
        print(f"  sq_preview   = {repr(r[5])}")
        print()
else:
    print("  AUCUNE LIGNE TROUVÉE")

# 4. APP_ETL_Tables_Published dans les DWH
print("\n[4] APP_ETL_Tables_Published dans les DWH - recherche 'imputation':")
cur_c.execute("""
    SELECT d.code AS dwh_code, d.nom,
           ISNULL(c.db_name, d.base_dwh) AS db_name,
           d.serveur_dwh, d.user_dwh, d.password_dwh
    FROM APP_DWH d
    LEFT JOIN APP_ClientDB c ON c.dwh_code = d.code
    WHERE d.actif = 1
    ORDER BY d.code
""")
dwh_list = cur_c.fetchall()
conn_c.close()

import pyodbc
import os
server_central = os.getenv('DB_SERVER', 'kasoft.selfip.net')
user_central   = os.getenv('DB_USER',   'sa')
pwd_central    = os.getenv('DB_PASSWORD', '')

for row in dwh_list:
    dwh_code, nom, db_name, serveur, user_dwh, pwd_dwh = row
    db  = db_name or f"OptiBoard_{dwh_code}"
    srv = serveur or server_central
    usr = user_dwh or user_central
    pwd = pwd_dwh  or pwd_central

    print(f"\n  DWH [{dwh_code}] {nom} → {srv}/{db}")
    try:
        cs = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={srv};DATABASE={db};"
            f"UID={usr};PWD={pwd};TrustServerCertificate=yes;"
        )
        conn_d = pyodbc.connect(cs, autocommit=True)
        cur_d  = conn_d.cursor()

        cur_d.execute("""
            SELECT code, table_name, target_table, is_enabled
            FROM APP_ETL_Tables_Published
            WHERE LOWER(code) LIKE '%imputation%'
               OR LOWER(target_table) LIKE '%imputation%'
               OR LOWER(table_name) LIKE '%imputation%'
        """)
        rows = cur_d.fetchall()
        if rows:
            for r in rows:
                print(f"    code={repr(r[0])}, table_name={repr(r[1])}, target={repr(r[2])}, enabled={r[3]}")
        else:
            print("    AUCUNE ligne imputation dans APP_ETL_Tables_Published")
        conn_d.close()
    except Exception as e:
        print(f"    ERREUR: {e}")

print("\n" + "=" * 80)
print("FIN DIAGNOSTIC")
print("=" * 80)
