"""
FIX :
1. Mouvement_stock : enlever les alias avec espaces → utiliser noms natifs F_ARTSTOCK
2. Echeances_Achats / Echeances_Ventes : F_ECHEANCES absente chez AMM
   → désactiver dans APP_ETL_Tables_Published pour AMM
   → vérifier aussi GO et KA
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database_unified import get_central_connection
from app.services.query_crypto import enc_query as encrypt_query
import pyodbc

conn = get_central_connection()
cur  = conn.cursor()

# ─────────────────────────────────────────────────────────
# 1. FIX Mouvement_stock : noms natifs sans alias avec espaces
# ─────────────────────────────────────────────────────────
print("=" * 60)
print("[1] FIX Mouvement_stock - noms de colonnes natifs")
print("=" * 60)

# Query avec noms natifs Sage (sans alias avec espaces)
MOUVEMENT_QUERY = """SELECT
    AR_Ref,
    DE_No,
    AS_QteSto,
    AS_QteRes,
    AS_QteCom,
    AS_QtePrepa,
    AS_MontSto,
    AS_QteMini,
    AS_QteMaxi,
    cbModification,
    cbCreation
FROM F_ARTSTOCK"""

# Mettre à jour APP_ETL_Tables_Config
cur.execute("""
    UPDATE APP_ETL_Tables_Config
    SET source_query        = ?,
        primary_key_columns = 'AR_Ref,DE_No',
        sync_type           = 'full',
        timestamp_column    = 'cbModification',
        date_modification   = GETDATE()
    WHERE code = 'Mouvement_stock'
""", (MOUVEMENT_QUERY,))
print(f"  APP_ETL_Tables_Config: {cur.rowcount} ligne(s) mise(s) à jour")

# Mettre à jour APP_ETL_Agent_Tables
enc_mv = encrypt_query(MOUVEMENT_QUERY)
cur.execute("""
    UPDATE APP_ETL_Agent_Tables
    SET source_query        = ?,
        primary_key_columns = 'AR_Ref,DE_No',
        sync_type           = 'full',
        timestamp_column    = 'cbModification'
    WHERE table_name IN ('Mouvement stock', 'Mouvement_stock')
""", (enc_mv,))
print(f"  APP_ETL_Agent_Tables: {cur.rowcount} agent(s) mis à jour")
conn.commit()

# ─────────────────────────────────────────────────────────
# 2. FIX Echeances : vérifier quels DWH ont F_ECHEANCES dans Sage
# ─────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("[2] Echeances_Achats / Echeances_Ventes - F_ECHEANCES absent")
print("=" * 60)

# Récupérer les sources Sage par DWH
cur.execute("""
    SELECT d.code AS dwh_code, d.nom,
           s.sage_server, s.sage_database, s.sage_user, s.sage_password
    FROM APP_DWH d
    JOIN APP_DWH_Sources s ON s.dwh_code = d.code
    WHERE d.actif = 1 AND s.actif = 1
    ORDER BY d.code
""")
sage_sources = cur.fetchall()

# Si la requête échoue à cause de noms de colonnes différents, essayer une autre
if not sage_sources:
    print("  Tentative avec noms de colonnes alternatifs...")
    cur.execute("""
        SELECT d.code AS dwh_code, d.nom,
               s.host AS sage_server, s.database_name AS sage_database,
               s.username AS sage_user, s.password AS sage_password
        FROM APP_DWH d
        JOIN APP_DWH_Sources s ON s.dwh_code = d.code
        WHERE d.actif = 1 AND s.actif = 1
    """)
    sage_sources = cur.fetchall()

dwh_no_echeances = []  # DWH sans F_ECHEANCES

if sage_sources:
    for row in sage_sources:
        dwh_code, nom = row[0], row[1]
        sage_srv, sage_db, sage_usr, sage_pwd = row[2], row[3], row[4], row[5]

        print(f"\n  [{dwh_code}] {nom} → Sage: {sage_srv}/{sage_db}")
        try:
            cs = (f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                  f"SERVER={sage_srv};DATABASE={sage_db};"
                  f"UID={sage_usr};PWD={sage_pwd};TrustServerCertificate=yes;")
            conn_sage = pyodbc.connect(cs, autocommit=True)
            cur_sage  = conn_sage.cursor()

            # Vérifier si F_ECHEANCES existe
            cur_sage.execute("SELECT COUNT(*) FROM sys.tables WHERE LOWER(name) = 'f_echeances'")
            exists = cur_sage.fetchone()[0]

            if exists:
                cur_sage.execute("SELECT COUNT(*) FROM F_ECHEANCES")
                cnt = cur_sage.fetchone()[0]
                print(f"    ✓ F_ECHEANCES existe ({cnt} lignes)")
            else:
                print(f"    ✗ F_ECHEANCES ABSENTE")
                dwh_no_echeances.append(dwh_code)

                # Chercher des tables alternatives
                cur_sage.execute("""
                    SELECT name FROM sys.tables
                    WHERE LOWER(name) LIKE '%ech%' OR LOWER(name) LIKE '%echeance%'
                    ORDER BY name
                """)
                alts = [r[0] for r in cur_sage.fetchall()]
                if alts:
                    print(f"    Tables similaires: {alts}")

            conn_sage.close()
        except Exception as e:
            print(f"    ERREUR connexion Sage: {e}")
            dwh_no_echeances.append(dwh_code)
else:
    print("  Impossible de récupérer les sources Sage (structure APP_DWH_Sources inconnue)")
    print("  Désactivation manuelle dans APP_ETL_Tables_Published pour AMM...")
    dwh_no_echeances = ['AMM']  # On sait qu'AMM n'a pas F_ECHEANCES

# ─────────────────────────────────────────────────────────
# 3. Désactiver Echeances pour les DWH sans F_ECHEANCES
# ─────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("[3] Désactivation Echeances dans APP_ETL_Tables_Published")
print("    pour les DWH sans F_ECHEANCES:", dwh_no_echeances)
print("=" * 60)

# Récupérer les connexions DWH
cur.execute("""
    SELECT d.code, ISNULL(c.db_name, d.base_dwh) AS db_name,
           d.serveur_dwh, d.user_dwh, d.password_dwh
    FROM APP_DWH d
    LEFT JOIN APP_ClientDB c ON c.dwh_code = d.code
    WHERE d.actif = 1
""")
dwh_list = {r[0]: r for r in cur.fetchall()}
conn.close()

srv_c = os.getenv('DB_SERVER', 'kasoft.selfip.net')
usr_c = os.getenv('DB_USER', 'sa')
pwd_c = os.getenv('DB_PASSWORD', '')

for dwh_code in dwh_no_echeances:
    if dwh_code not in dwh_list:
        print(f"\n  [{dwh_code}] Non trouvé dans APP_DWH")
        continue

    row = dwh_list[dwh_code]
    _, db_name, serveur, user_dwh, pwd_dwh = row
    srv = serveur or srv_c
    usr = user_dwh or usr_c
    pwd = pwd_dwh  or pwd_c
    db  = db_name  or f"OptiBoard_{dwh_code}"

    print(f"\n  [{dwh_code}] → {srv}/{db}")
    try:
        cs = (f"DRIVER={{ODBC Driver 17 for SQL Server}};"
              f"SERVER={srv};DATABASE={db};"
              f"UID={usr};PWD={pwd};TrustServerCertificate=yes;")
        conn_d = pyodbc.connect(cs, autocommit=True)
        cur_d  = conn_d.cursor()

        for code in ['Echeances_Achats', 'Echeances_Ventes']:
            cur_d.execute("""
                UPDATE APP_ETL_Tables_Published
                SET is_enabled = 0
                WHERE code = ?
            """, (code,))
            if cur_d.rowcount > 0:
                print(f"    ✓ {code} désactivé (is_enabled=0)")
            else:
                print(f"    - {code} non trouvé (déjà absent?)")

        conn_d.close()
    except Exception as e:
        print(f"    ERREUR: {e}")

print("\n" + "=" * 60)
print("FIX TERMINÉ")
print("=" * 60)
print("""
RÉSUMÉ :
  - Mouvement_stock : query corrigée (noms natifs AS_QteSto, AS_QteRes...)
  - Echeances_Achats/Ventes : désactivées pour les DWH sans F_ECHEANCES

NOTE Echeances :
  Si ATLASMULTIMATERIAL utilise un module Sage avec les échéances,
  vérifiez quel est le vrai nom de la table (F_ECHEANCES peut être
  F_CREGLEMENT, F_REGLECH, ou autre selon la version Sage).
""")
