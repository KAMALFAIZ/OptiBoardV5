"""
DIAGNOSTIC : Affiche les vraies valeurs de target_table pour Echéances_Ventes
dans toutes les tables de configuration ETL.
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database_unified import get_central_connection

def get_conn_to(server, db, user, password):
    import pyodbc
    cs = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={server};DATABASE={db};"
        f"UID={user};PWD={password};TrustServerCertificate=yes;"
    )
    return pyodbc.connect(cs, autocommit=True)

conn_c = get_central_connection()
cur_c  = conn_c.cursor()

# 1. APP_ETL_Tables_Config — valeurs réelles
print("=" * 70)
print("APP_ETL_Tables_Config (centrale)")
print("=" * 70)
cur_c.execute("""
    SELECT code, table_name, target_table, actif
    FROM APP_ETL_Tables_Config
    WHERE LOWER(code) LIKE '%cheance%'
       OR LOWER(target_table) LIKE '%cheance%'
       OR LOWER(table_name)   LIKE '%cheance%'
""")
rows = cur_c.fetchall()
if rows:
    for r in rows:
        code, tname, ttable, actif = r
        print(f"  code         = {repr(code)}")
        print(f"  table_name   = {repr(tname)}")
        print(f"  target_table = {repr(ttable)}")
        print(f"  actif        = {actif}")
        print()
else:
    print("  AUCUNE LIGNE TROUVÉE dans APP_ETL_Tables_Config")

# 2. APP_ETL_Agent_Tables — valeurs réelles
print("=" * 70)
print("APP_ETL_Agent_Tables (centrale)")
print("=" * 70)
cur_c.execute("""
    SELECT agent_id, table_name, target_table, is_enabled
    FROM APP_ETL_Agent_Tables
    WHERE LOWER(table_name)   LIKE '%cheance%'
       OR LOWER(target_table) LIKE '%cheance%'
""")
rows = cur_c.fetchall()
if rows:
    for r in rows:
        print(f"  agent_id     = {r[0]}")
        print(f"  table_name   = {repr(r[1])}")
        print(f"  target_table = {repr(r[2])}")
        print(f"  is_enabled   = {r[3]}")
        print()
else:
    print("  AUCUNE LIGNE TROUVÉE dans APP_ETL_Agent_Tables")

# 3. Pour chaque base DWH — APP_ETL_Tables_Published
cur_c.execute("""
    SELECT d.code, d.nom, d.base_dwh,
           ISNULL(c.db_name, d.base_dwh) AS db_name,
           d.serveur_dwh, d.user_dwh, d.password_dwh
    FROM APP_DWH d
    LEFT JOIN APP_ClientDB c ON c.dwh_code = d.code
    WHERE d.actif = 1
    ORDER BY d.code
""")
dwh_list = cur_c.fetchall()
conn_c.close()

import os
server_central = os.getenv('DB_SERVER', 'kasoft.selfip.net')
user_central   = os.getenv('DB_USER',   'sa')
pwd_central    = os.getenv('DB_PASSWORD', '')

for row in dwh_list:
    code, nom, base_dwh, db_name, serveur, user_dwh, pwd_dwh = row
    db  = db_name or base_dwh
    srv = serveur or server_central
    usr = user_dwh or user_central
    pwd = pwd_dwh  or pwd_central

    print("=" * 70)
    print(f"APP_ETL_Tables_Published — [{code}] {nom}  ({srv}/{db})")
    print("=" * 70)
    try:
        conn_d = get_conn_to(srv, db, usr, pwd)
        cur_d  = conn_d.cursor()

        cur_d.execute("""
            SELECT code, table_name, target_table, is_enabled
            FROM APP_ETL_Tables_Published
            WHERE LOWER(code)         LIKE '%cheance%'
               OR LOWER(target_table) LIKE '%cheance%'
               OR LOWER(table_name)   LIKE '%cheance%'
        """)
        rows = cur_d.fetchall()
        if rows:
            for r in rows:
                print(f"  code         = {repr(r[0])}")
                print(f"  table_name   = {repr(r[1])}")
                print(f"  target_table = {repr(r[2])}")
                print(f"  is_enabled   = {r[3]}")
                print()
        else:
            print("  AUCUNE LIGNE TROUVÉE dans APP_ETL_Tables_Published")

        # Vérifier aussi les tables DWH existantes
        cur_d.execute("""
            SELECT name FROM sys.tables
            WHERE LOWER(name) LIKE '%cheance%'
        """)
        tables = cur_d.fetchall()
        if tables:
            print(f"  Tables DWH existantes : {[r[0] for r in tables]}")
        else:
            print("  Aucune table *cheance* dans cette base")
        conn_d.close()
    except Exception as e:
        print(f"  ERREUR connexion : {e}")
