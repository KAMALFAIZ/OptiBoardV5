"""
FIX : Echeances_Ventes - remplace la query YAML complexe par la query simple.
Le code dans la DB est 'Echeances_Ventes' (sans accent sur E),
mais fix_queries.py cherchait 'Echéances_Ventes' (avec accent) → NON TROUVE.
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database_unified import get_central_connection
from app.services.query_crypto import enc_query as encrypt_query

SIMPLE_QUERY = """SELECT ECH_No, ENT_No, CT_Num, ECH_Piece, ECH_RefPiece,
ECH_Montant, ECH_DateEch, ECH_Libelle, ECH_Type, ECH_Sens,
ECH_ModePaie, N_Devise, ECH_MontantDev, ECH_Etape,
ECH_DateCreat, cbModification, cbCreation
FROM F_ECHEANCES WHERE ECH_Sens = 0"""

PK       = 'ECH_No'
SYNC     = 'incremental'
TS       = 'cbModification'

conn = get_central_connection()
cur  = conn.cursor()

print("=" * 60)
print("FIX - Echeances_Ventes (tous les codes possibles)")
print("=" * 60)

# Chercher tous les codes qui contiennent 'cheance' et 'vente'
cur.execute("""
    SELECT code, table_name, LEN(ISNULL(source_query,'')) AS sq_len
    FROM APP_ETL_Tables_Config
    WHERE LOWER(code) LIKE '%cheance%'
      AND (LOWER(code) LIKE '%vent%' OR LOWER(table_name) LIKE '%vent%')
""")
rows = cur.fetchall()
print(f"\nCodes correspondants:")
for r in rows:
    print(f"  code={repr(r[0])}, table_name={repr(r[1])}, sq_len={r[2]}")

# Mettre à jour tous les codes trouvés
updated_total = 0
for r in rows:
    code = r[0]
    cur.execute("""
        UPDATE APP_ETL_Tables_Config
        SET source_query        = ?,
            primary_key_columns = ?,
            sync_type           = ?,
            timestamp_column    = ?,
            date_modification   = GETDATE()
        WHERE code = ?
    """, (SIMPLE_QUERY, PK, SYNC, TS, code))
    if cur.rowcount > 0:
        updated_total += 1
        print(f"\n  ✓ Mis à jour: {repr(code)}")

conn.commit()

# Mettre à jour APP_ETL_Agent_Tables
print(f"\n[2] Mise à jour APP_ETL_Agent_Tables...")
enc_q = encrypt_query(SIMPLE_QUERY)

cur.execute("""
    SELECT DISTINCT table_name FROM APP_ETL_Agent_Tables
    WHERE LOWER(table_name) LIKE '%cheance%'
      AND (LOWER(table_name) LIKE '%vent%')
""")
agent_table_names = [r[0] for r in cur.fetchall()]
print(f"  Noms trouvés: {agent_table_names}")

for tname in agent_table_names:
    cur.execute("""
        UPDATE APP_ETL_Agent_Tables
        SET source_query = ?, primary_key_columns = ?, sync_type = ?, timestamp_column = ?
        WHERE table_name = ?
    """, (enc_q, PK, SYNC, TS, tname))
    if cur.rowcount > 0:
        print(f"  ✓ {cur.rowcount} agent(s) mis à jour pour '{tname}'")

conn.commit()

# Vérification
print(f"\n[3] Vérification finale:")
cur.execute("""
    SELECT code, primary_key_columns, sync_type,
           LEN(ISNULL(source_query,'')) AS sq_len,
           LEFT(source_query, 80) AS sq_preview
    FROM APP_ETL_Tables_Config
    WHERE LOWER(code) LIKE '%cheance%'
    ORDER BY code
""")
for r in cur.fetchall():
    print(f"  {repr(r[0])}: pk={repr(r[1])}, sync={r[2]}, sq_len={r[3]}")
    print(f"    preview: {repr(r[4])}")

conn.close()
print("\nFIX TERMINÉ")
