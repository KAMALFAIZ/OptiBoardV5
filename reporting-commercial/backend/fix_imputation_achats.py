"""
FIX : Remplace la query complexe d'Imputation_Factures_Achats
par une query simple et fiable (F_DOCREGL).

Corrige aussi :
- primary_key_columns : DR_No (plain CSV, pas JSON)
- APP_ETL_Agent_Tables : met à jour les agents avec la query chiffrée
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database_unified import get_central_connection
from app.services.query_crypto import enc_query as encrypt_query

# Query simple et fiable - F_DOCREGL pour les achats (DO_Domaine=1)
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
WHERE DO_Domaine = 1 AND DO_Type = 3"""

PK_COLUMNS  = 'DR_No'
SYNC_TYPE   = 'incremental'
TIMESTAMP   = 'cbModification'
CODE        = 'Imputation_Factures_Achats'
TABLE_NAME  = 'Imputation factures des achats'

print("=" * 70)
print("FIX - Imputation_Factures_Achats")
print("=" * 70)

conn = get_central_connection()
cur  = conn.cursor()

# 1. Mettre à jour APP_ETL_Tables_Config
print(f"\n[1] Mise à jour APP_ETL_Tables_Config pour code='{CODE}'")
cur.execute("""
    UPDATE APP_ETL_Tables_Config
    SET source_query         = ?,
        primary_key_columns  = ?,
        sync_type            = ?,
        timestamp_column     = ?,
        date_modification    = GETDATE()
    WHERE code = ?
""", (SIMPLE_QUERY, PK_COLUMNS, SYNC_TYPE, TIMESTAMP, CODE))

if cur.rowcount > 0:
    print(f"  ✓ APP_ETL_Tables_Config mis à jour ({cur.rowcount} ligne)")
else:
    print(f"  ✗ CODE '{CODE}' non trouvé dans APP_ETL_Tables_Config!")
    # Afficher les codes disponibles
    cur.execute("SELECT code FROM APP_ETL_Tables_Config ORDER BY code")
    print("  Codes disponibles:", [r[0] for r in cur.fetchall()])

conn.commit()

# 2. Chiffrer la query pour les agents
print(f"\n[2] Chiffrement de la query...")
try:
    enc_query = encrypt_query(SIMPLE_QUERY)
    print(f"  ✓ Query chiffrée (len={len(enc_query)})")
except Exception as e:
    print(f"  ✗ Erreur chiffrement: {e}")
    enc_query = None

# 3. Mettre à jour APP_ETL_Agent_Tables
print(f"\n[3] Mise à jour APP_ETL_Agent_Tables (table_name='{TABLE_NAME}')")
cur.execute("""
    SELECT COUNT(*) FROM APP_ETL_Agent_Tables
    WHERE table_name = ? OR table_name = ?
""", (TABLE_NAME, CODE))
total = cur.fetchone()[0]
print(f"  {total} entrée(s) trouvée(s)")

if total > 0 and enc_query:
    cur.execute("""
        UPDATE APP_ETL_Agent_Tables
        SET source_query         = ?,
            primary_key_columns  = ?,
            sync_type            = ?,
            timestamp_column     = ?
        WHERE table_name = ? OR table_name = ?
    """, (enc_query, PK_COLUMNS, SYNC_TYPE, TIMESTAMP, TABLE_NAME, CODE))
    print(f"  ✓ {cur.rowcount} entrée(s) mises à jour dans APP_ETL_Agent_Tables")
    conn.commit()
elif total > 0 and not enc_query:
    print(f"  ✗ Chiffrement échoué, APP_ETL_Agent_Tables non mis à jour")

# 4. Vérification finale
print(f"\n[4] Vérification finale:")
cur.execute("""
    SELECT code, table_name, primary_key_columns, sync_type, timestamp_column,
           LEN(ISNULL(source_query,'')) AS sq_len,
           LEFT(source_query, 100) AS sq_preview
    FROM APP_ETL_Tables_Config
    WHERE code = ?
""", (CODE,))
row = cur.fetchone()
if row:
    print(f"  code              = {repr(row[0])}")
    print(f"  table_name        = {repr(row[1])}")
    print(f"  primary_key       = {repr(row[2])}")
    print(f"  sync_type         = {repr(row[3])}")
    print(f"  timestamp         = {repr(row[4])}")
    print(f"  sq_len            = {row[5]}")
    print(f"  sq_preview        = {repr(row[6])}")

# 5. Vérifier les agents
print(f"\n[5] Agents avec table '{TABLE_NAME}':")
cur.execute("""
    SELECT agent_id, table_name, primary_key_columns, sync_type,
           LEN(ISNULL(source_query,'')) AS sq_len
    FROM APP_ETL_Agent_Tables
    WHERE table_name = ? OR table_name = ?
""", (TABLE_NAME, CODE))
agents = cur.fetchall()
if agents:
    for a in agents:
        print(f"  agent={a[0][:16]}... | pk={repr(a[2])} | sync={a[3]} | sq_len={a[4]}")
else:
    print("  Aucun agent trouvé")

conn.close()

print("\n" + "=" * 70)
print("FIX TERMINÉ")
print("=" * 70)
print("""
ACTION SUIVANTE:
  Redémarrez l'agent ETL ATLASMULTIMATERIAL pour déclencher
  une synchronisation complète de Imputation_Factures_Achats.
  La table sera créée automatiquement dans le DWH lors du premier sync.
""")
