"""
DIAGNOSTIC COMPLET - Imputation_Factures_Achats
Vérifie la query stockée, les PKs, et tente d'exécuter la query contre Sage.
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database_unified import get_central_connection
from dotenv import load_dotenv

# Charger .env
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

conn_c = get_central_connection()
cur_c  = conn_c.cursor()

print("=" * 80)
print("DIAGNOSTIC COMPLET - Imputation_Factures_Achats")
print("=" * 80)

# 1. Récupérer la config complète depuis APP_ETL_Tables_Config
print("\n[1] APP_ETL_Tables_Config pour Imputation_Factures_Achats:")
cur_c.execute("""
    SELECT code, table_name, target_table, actif,
           primary_key_columns, sync_type, timestamp_column,
           LEN(ISNULL(source_query,'')) AS sq_len,
           source_query
    FROM APP_ETL_Tables_Config
    WHERE code = 'Imputation_Factures_Achats'
""")
row = cur_c.fetchone()
if row:
    print(f"  code              = {repr(row[0])}")
    print(f"  table_name        = {repr(row[1])}")
    print(f"  target_table      = {repr(row[2])}")
    print(f"  actif             = {row[3]}")
    print(f"  primary_key       = {repr(row[4])}")
    print(f"  sync_type         = {repr(row[5])}")
    print(f"  timestamp_column  = {repr(row[6])}")
    print(f"  source_query len  = {row[7]}")
    print(f"\n  === SOURCE QUERY ===")
    print(row[8])
else:
    print("  NON TROUVÉ!")

# 2. Comparer avec Ecritures_Comptables (qui fonctionne)
print("\n[2] APP_ETL_Tables_Config pour Ecritures_Comptables (comparaison):")
cur_c.execute("""
    SELECT code, primary_key_columns, sync_type, timestamp_column,
           LEN(ISNULL(source_query,'')) AS sq_len,
           LEFT(source_query, 200) AS sq_preview
    FROM APP_ETL_Tables_Config
    WHERE code = 'Ecritures_Comptables'
""")
row = cur_c.fetchone()
if row:
    print(f"  primary_key = {repr(row[1])}")
    print(f"  sync_type   = {repr(row[2])}")
    print(f"  timestamp   = {repr(row[3])}")
    print(f"  sq_len      = {row[4]}")
    print(f"  sq_preview  = {repr(row[5])}")

# 3. Vérifier la table cible dans le DWH AMM
print("\n[3] Tables dans DWH AMM contenant 'imputation':")
cur_c.execute("""
    SELECT d.code, ISNULL(c.db_name, d.base_dwh) AS db_name,
           d.serveur_dwh, d.user_dwh, d.password_dwh
    FROM APP_DWH d
    LEFT JOIN APP_ClientDB c ON c.dwh_code = d.code
    WHERE d.code = 'AMM' AND d.actif = 1
""")
dwh = cur_c.fetchone()
conn_c.close()

if not dwh:
    print("  DWH AMM non trouvé!")
else:
    dwh_code, db_name, serveur, user_dwh, pwd_dwh = dwh

    import pyodbc
    server_c = os.getenv('DB_SERVER', 'kasoft.selfip.net')
    user_c   = os.getenv('DB_USER', 'sa')
    pwd_c    = os.getenv('DB_PASSWORD', '')

    srv = serveur or server_c
    usr = user_dwh or user_c
    pwd = pwd_dwh or pwd_c
    db  = db_name or f"OptiBoard_{dwh_code}"

    print(f"  Connexion: {srv}/{db}")
    try:
        cs = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={srv};DATABASE={db};"
            f"UID={usr};PWD={pwd};TrustServerCertificate=yes;"
        )
        conn_d = pyodbc.connect(cs, autocommit=True)
        cur_d  = conn_d.cursor()

        cur_d.execute("""
            SELECT name FROM sys.tables
            WHERE LOWER(name) LIKE '%imputation%'
        """)
        tables = cur_d.fetchall()
        if tables:
            for t in tables:
                print(f"  Table DWH trouvée: {t[0]}")
                # Count rows
                try:
                    cur_d.execute(f"SELECT COUNT(*) FROM [{t[0]}]")
                    cnt = cur_d.fetchone()[0]
                    print(f"    → {cnt} lignes")
                except Exception as e:
                    print(f"    → Erreur count: {e}")
        else:
            print("  Aucune table *imputation* dans le DWH AMM")

        conn_d.close()
    except Exception as e:
        print(f"  ERREUR connexion DWH: {e}")

# 4. Tenter d'exécuter la query contre Sage AMM
print("\n[4] Test d'exécution de la query contre Sage AMM:")
conn_c2 = get_central_connection()
cur_c2  = conn_c2.cursor()

# Récupérer source Sage pour AMM
cur_c2.execute("""
    SELECT s.sage_server, s.sage_database, s.sage_username, s.sage_password
    FROM APP_DWH_Sources s
    WHERE s.dwh_code = 'AMM' AND s.actif = 1
""")
sage_row = cur_c2.fetchone()

# Récupérer la query
cur_c2.execute("SELECT source_query FROM APP_ETL_Tables_Config WHERE code = 'Imputation_Factures_Achats'")
q_row = cur_c2.fetchone()
conn_c2.close()

if not sage_row:
    print("  Source Sage AMM non trouvée dans APP_DWH_Sources")
elif not q_row:
    print("  Query non trouvée dans APP_ETL_Tables_Config")
else:
    sage_server, sage_db, sage_user, sage_pwd = sage_row
    query = q_row[0]

    print(f"  Sage: {sage_server}/{sage_db}")
    try:
        import pyodbc
        cs_sage = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={sage_server};DATABASE={sage_db};"
            f"UID={sage_user};PWD={sage_pwd};TrustServerCertificate=yes;"
        )
        conn_sage = pyodbc.connect(cs_sage, autocommit=True)
        cur_sage  = conn_sage.cursor()

        # Test avec TOP 5
        test_query = f"SELECT TOP 5 * FROM ({query}) AS sq"
        print(f"  Exécution TOP 5...")
        try:
            cur_sage.execute(test_query)
            rows = cur_sage.fetchall()
            print(f"  → {len(rows)} lignes retournées (OK!)")
            if rows:
                cols = [d[0] for d in cur_sage.description]
                print(f"  → Colonnes: {cols[:10]}")
        except Exception as e:
            print(f"  → ERREUR SQL: {e}")
            # Essayer la query simple F_DOCREGL
            print("\n  Tentative avec query simple F_DOCREGL:")
            simple_q = """SELECT TOP 5 DR_No, DO_Domaine, DO_Type, DO_Piece, DR_TypeRegl,
DR_Date, DR_Libelle, DR_Pourcent, DR_Montant, DR_MontantDev,
N_Reglement, DR_Regle, cbCreation, cbModification
FROM F_DOCREGL WHERE DO_Domaine = 1 AND DO_Type = 3"""
            try:
                cur_sage.execute(simple_q)
                rows2 = cur_sage.fetchall()
                print(f"  → {len(rows2)} lignes (OK!)")
                if rows2:
                    cols2 = [d[0] for d in cur_sage.description]
                    print(f"  → Colonnes: {cols2}")
            except Exception as e2:
                print(f"  → Erreur query simple: {e2}")

        conn_sage.close()
    except Exception as e:
        print(f"  ERREUR connexion Sage: {e}")

print("\n" + "=" * 80)
print("FIN DIAGNOSTIC")
print("=" * 80)
