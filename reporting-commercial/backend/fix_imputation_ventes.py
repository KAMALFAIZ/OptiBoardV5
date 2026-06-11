"""
FIX : Remplace la query complexe d'Imputation_Factures_Ventes
par une query simple et fiable (F_DOCREGL, DO_Domaine=0).
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database_unified import get_central_connection
from app.services.query_crypto import enc_query as encrypt_query

SIMPLE_QUERY = """SELECT
    DR_No,
    DO_Domaine,
    DO_Type,
    DO_Piece,
    DR_TypeRegl,
    DR_Date,
    DR_Libelle,
    DR_Pourcent,
    DR_Montant,
    DR_MontantDev,
    N_Reglement,
    DR_Regle,
    cbCreation,
    cbModification
FROM F_DOCREGL
WHERE DO_Domaine = 0 AND DO_Type = 3"""

PK_COLUMNS = 'DR_No'
SYNC_TYPE  = 'incremental'
TIMESTAMP  = 'cbModification'
CODE       = 'Imputation_Factures_Ventes'
TABLE_NAME = 'Imputation les factures des ventes'

print("=" * 70)
print("FIX - Imputation_Factures_Ventes")
print("=" * 70)

conn = get_central_connection()
cur  = conn.cursor()

# Afficher l'état actuel
cur.execute("""
    SELECT code, primary_key_columns, sync_type,
           LEN(ISNULL(source_query,'')) AS sq_len,
           LEFT(ISNULL(source_query,''), 120) AS sq_preview
    FROM APP_ETL_Tables_Config WHERE code = ?
""", (CODE,))
row = cur.fetchone()
if row:
    print(f"\n[AVANT]")
    print(f"  primary_key = {repr(row[1])}")
    print(f"  sync_type   = {repr(row[2])}")
    print(f"  sq_len      = {row[3]}")
    print(f"  sq_preview  = {repr(row[4])}")

# 1. Mettre à jour APP_ETL_Tables_Config
print(f"\n[1] Mise à jour APP_ETL_Tables_Config...")
cur.execute("""
    UPDATE APP_ETL_Tables_Config
    SET source_query        = ?,
        primary_key_columns = ?,
        sync_type           = ?,
        timestamp_column    = ?,
        date_modification   = GETDATE()
    WHERE code = ?
""", (SIMPLE_QUERY, PK_COLUMNS, SYNC_TYPE, TIMESTAMP, CODE))

if cur.rowcount > 0:
    print(f"  ✓ Mis à jour ({cur.rowcount} ligne)")
else:
    print(f"  ✗ Code '{CODE}' non trouvé!")
conn.commit()

# 2. Chiffrer et mettre à jour APP_ETL_Agent_Tables
print(f"\n[2] Chiffrement...")
enc_query = encrypt_query(SIMPLE_QUERY)
print(f"  ✓ Query chiffrée (len={len(enc_query)})")

print(f"\n[3] Mise à jour APP_ETL_Agent_Tables...")
cur.execute("""
    SELECT COUNT(*) FROM APP_ETL_Agent_Tables
    WHERE table_name = ? OR table_name = ?
""", (TABLE_NAME, CODE))
total = cur.fetchone()[0]
print(f"  {total} agent(s) trouvé(s)")

if total > 0:
    cur.execute("""
        UPDATE APP_ETL_Agent_Tables
        SET source_query        = ?,
            primary_key_columns = ?,
            sync_type           = ?,
            timestamp_column    = ?
        WHERE table_name = ? OR table_name = ?
    """, (enc_query, PK_COLUMNS, SYNC_TYPE, TIMESTAMP, TABLE_NAME, CODE))
    print(f"  ✓ {cur.rowcount} entrée(s) mises à jour")
    conn.commit()

# 3. Vérification finale
print(f"\n[4] Vérification finale APP_ETL_Tables_Config:")
cur.execute("""
    SELECT primary_key_columns, sync_type, timestamp_column,
           LEN(ISNULL(source_query,'')) AS sq_len,
           LEFT(source_query, 120) AS sq_preview
    FROM APP_ETL_Tables_Config WHERE code = ?
""", (CODE,))
row = cur.fetchone()
if row:
    print(f"  primary_key = {repr(row[0])}")
    print(f"  sync_type   = {repr(row[1])}")
    print(f"  timestamp   = {repr(row[2])}")
    print(f"  sq_len      = {row[3]}")
    print(f"  sq_preview  = {repr(row[4])}")

# 4. Vérifier si la table cible existe dans les DWH
print(f"\n[5] Table cible '{CODE}' dans les DWH:")
cur.execute("""
    SELECT d.code, d.nom, ISNULL(c.db_name, d.base_dwh) AS db_name,
           d.serveur_dwh, d.user_dwh, d.password_dwh
    FROM APP_DWH d
    LEFT JOIN APP_ClientDB c ON c.dwh_code = d.code
    WHERE d.actif = 1
""")
dwh_list = cur.fetchall()
conn.close()

import pyodbc
srv_c = os.getenv('DB_SERVER', 'kasoft.selfip.net')
usr_c = os.getenv('DB_USER', 'sa')
pwd_c = os.getenv('DB_PASSWORD', '')

for row in dwh_list:
    dwh_code, nom, db_name, serveur, user_dwh, pwd_dwh = row
    srv = serveur or srv_c
    usr = user_dwh or usr_c
    pwd = pwd_dwh  or pwd_c
    db  = db_name  or f"OptiBoard_{dwh_code}"
    try:
        cs = (f"DRIVER={{ODBC Driver 17 for SQL Server}};"
              f"SERVER={srv};DATABASE={db};"
              f"UID={usr};PWD={pwd};TrustServerCertificate=yes;")
        conn_d = pyodbc.connect(cs, autocommit=True)
        cur_d  = conn_d.cursor()
        cur_d.execute("SELECT COUNT(*) FROM sys.tables WHERE name = ?", (CODE,))
        exists = cur_d.fetchone()[0]
        if exists:
            cur_d.execute(f"SELECT COUNT(*) FROM [{CODE}]")
            cnt = cur_d.fetchone()[0]
            print(f"  [{dwh_code}] ✓ Table existe → {cnt} lignes")
        else:
            print(f"  [{dwh_code}] ✗ Table ABSENTE (sera créée au premier sync)")
        conn_d.close()
    except Exception as e:
        print(f"  [{dwh_code}] ERREUR: {e}")

print("\n" + "=" * 70)
print("FIX TERMINÉ — Redémarrez l'agent ETL pour synchroniser.")
print("=" * 70)
