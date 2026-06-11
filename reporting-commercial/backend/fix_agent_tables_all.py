"""
FIX COMPLET : Synchronise toutes les queries dans APP_ETL_Agent_Tables
avec celles de APP_ETL_Tables_Config (qui viennent d'être mises à jour).

Pour chaque table dans APP_ETL_Agent_Tables, trouve le code correspondant
dans APP_ETL_Tables_Config et met à jour la query chiffrée.
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database_unified import get_central_connection
from app.services.query_crypto import enc_query as encrypt_query, dec_query

conn = get_central_connection()
cur  = conn.cursor()

print("=" * 70)
print("SYNC APP_ETL_Agent_Tables depuis APP_ETL_Tables_Config")
print("=" * 70)

# 1. Récupérer la config centrale avec target_table et query
cur.execute("""
    SELECT code, table_name, target_table, source_query,
           primary_key_columns, sync_type, timestamp_column
    FROM APP_ETL_Tables_Config
    WHERE actif = 1 AND source_query IS NOT NULL
      AND LEN(source_query) > 20
""")
central = {}
for r in cur.fetchall():
    # Index par code, target_table ET table_name pour matcher les agents
    central[r[0]] = {  # par code
        'code': r[0], 'table_name': r[1], 'target_table': r[2],
        'query': r[3], 'pk': r[4], 'sync': r[5], 'ts': r[6]
    }
    central[r[1]] = central[r[0]]  # par table_name
    central[r[2]] = central[r[0]]  # par target_table

print(f"\n{len(set(v['code'] for v in central.values()))} tables dans APP_ETL_Tables_Config")

# 2. Lire toutes les entrées de APP_ETL_Agent_Tables
cur.execute("""
    SELECT id, agent_id, table_name, target_table,
           primary_key_columns, sync_type, timestamp_column,
           LEN(ISNULL(source_query,'')) AS sq_len
    FROM APP_ETL_Agent_Tables
    ORDER BY table_name, agent_id
""")
agent_rows = cur.fetchall()
print(f"\n{len(agent_rows)} entrées dans APP_ETL_Agent_Tables")

# 3. Matcher et mettre à jour
updated = 0
not_found = []
already_ok = []

for row in agent_rows:
    rid, agent_id, tname, ttable, pk, sync, ts, sq_len = row

    # Chercher le match dans la config centrale
    cfg = central.get(tname) or central.get(ttable)
    if not cfg:
        not_found.append(tname)
        continue

    # Chiffrer la nouvelle query
    new_enc = encrypt_query(cfg['query'])
    new_len = len(new_enc)

    # Mettre à jour
    cur.execute("""
        UPDATE APP_ETL_Agent_Tables
        SET source_query        = ?,
            primary_key_columns = ?,
            sync_type           = ?,
            timestamp_column    = ?
        WHERE id = ?
    """, (new_enc, cfg['pk'] or '', cfg['sync'] or 'full', cfg['ts'] or 'cbModification', rid))

    if cur.rowcount > 0:
        updated += 1
        print(f"  ✓ [{agent_id[:12]}...] {tname} → pk={cfg['pk']}, sq_len={sq_len}→{new_len}")
    else:
        print(f"  ✗ Échec UPDATE pour id={rid}")

conn.commit()

# 4. Rapport des tables non matchées
if not_found:
    unique_nf = sorted(set(not_found))
    print(f"\n  Tables sans correspondance dans APP_ETL_Tables_Config ({len(unique_nf)}):")
    for n in unique_nf:
        print(f"    - {repr(n)}")

print(f"\n{'='*70}")
print(f"RÉSULTAT: {updated} entrées mises à jour, {len(set(not_found))} sans correspondance")
print(f"{'='*70}")

conn.close()
