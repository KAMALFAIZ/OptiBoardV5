"""
FIX AUTOMATIQUE : Echéances_Ventes absente de APP_ETL_Tables_Config
1. Lit la source_query depuis le YAML (sync_tables.yaml)
2. Insère dans APP_ETL_Tables_Config (centrale)
3. Propage vers APP_ETL_Agent_Tables (tous agents)
4. Propage vers APP_ETL_Tables_Published (toutes bases DWH clientes)
"""
import sys, os, json, yaml
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database_unified import get_central_connection

YAML_PATH = os.path.join(os.path.dirname(__file__), 'etl', 'config', 'sync_tables.yaml')
CODE           = 'Echeances_Ventes'
TABLE_NAME     = 'Echéances ventes'
TARGET_TABLE   = 'Echéances_Ventes'
PK_COLUMNS     = 'N° interne'
SYNC_TYPE      = 'incremental'
TIMESTAMP_COL  = 'cbModification'
INTERVAL_MIN   = 5
PRIORITY       = 'normal'
DELETE_DET     = 0
DESCRIPTION    = 'Échéances de ventes (F_DOCREGL) avec calcul montant échu'
VERSION        = 1

def get_conn_to(server, db, user, password):
    import pyodbc
    cs = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={server};DATABASE={db};"
        f"UID={user};PWD={password};TrustServerCertificate=yes;"
    )
    return pyodbc.connect(cs, autocommit=False)

# ─────────────────────────────────────────────────────────────
# 1. Lire la source_query depuis le YAML
# ─────────────────────────────────────────────────────────────
print("=" * 70)
print("ÉTAPE 1 — Lecture source_query depuis YAML")
print("=" * 70)

with open(YAML_PATH, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

import unicodedata
def _norm(s):
    n = unicodedata.normalize('NFD', s.lower())
    return ''.join(c for c in n if unicodedata.category(c) != 'Mn')

# Le YAML est un dict avec clé 'tables', ou directement une liste
tables_yaml = config.get('tables', config) if isinstance(config, dict) else config

source_query = None
for t in tables_yaml:
    if not isinstance(t, dict):
        continue
    name_norm = _norm(t.get('name', ''))
    if 'echeance' in name_norm and 'vente' in name_norm:
        src = t.get('source', {})
        source_query = src.get('query', '') if isinstance(src, dict) else ''
        print(f"  Trouvé dans YAML : name={repr(t['name'])}")
        print(f"  source_query : {len(source_query)} caractères")
        break

if not source_query:
    print("  ERREUR : source_query non trouvée dans le YAML")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────
# 2. Insérer dans APP_ETL_Tables_Config (centrale)
# ─────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("ÉTAPE 2 — APP_ETL_Tables_Config (centrale)")
print("=" * 70)

conn_c = get_central_connection()
cur_c  = conn_c.cursor()

cur_c.execute("SELECT id, code, target_table FROM APP_ETL_Tables_Config WHERE code = ?", (CODE,))
existing = cur_c.fetchone()

if existing:
    print(f"  Déjà présent (id={existing[0]}, target_table={repr(existing[2])}) → mise à jour")
    cur_c.execute("""
        UPDATE APP_ETL_Tables_Config
        SET table_name=?, target_table=?, source_query=?,
            primary_key_columns=?, sync_type=?, timestamp_column=?,
            interval_minutes=?, priority=?, delete_detection=?,
            description=?, version=?, actif=1,
            date_modification=GETDATE()
        WHERE code=?
    """, (TABLE_NAME, TARGET_TABLE, source_query, PK_COLUMNS, SYNC_TYPE,
          TIMESTAMP_COL, INTERVAL_MIN, PRIORITY, DELETE_DET,
          DESCRIPTION, VERSION, CODE))
else:
    print(f"  Absent → insertion")
    cur_c.execute("""
        INSERT INTO APP_ETL_Tables_Config
            (code, table_name, target_table, source_query, primary_key_columns,
             sync_type, timestamp_column, interval_minutes, priority,
             delete_detection, description, version, actif)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,1)
    """, (CODE, TABLE_NAME, TARGET_TABLE, source_query, PK_COLUMNS,
          SYNC_TYPE, TIMESTAMP_COL, INTERVAL_MIN, PRIORITY,
          DELETE_DET, DESCRIPTION, VERSION))

conn_c.commit()
print(f"  ✓ APP_ETL_Tables_Config OK")

# ─────────────────────────────────────────────────────────────
# 3. Propager vers APP_ETL_Agent_Tables (tous agents, centrale)
# ─────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("ÉTAPE 3 — APP_ETL_Agent_Tables (tous agents)")
print("=" * 70)

cur_c.execute("SELECT agent_id FROM APP_ETL_Agent_Tables GROUP BY agent_id")
agent_ids = [r[0] for r in cur_c.fetchall()]

# Lire aussi depuis APP_ETL_Agents si accessible
try:
    conn_c2 = get_central_connection()
    cur2 = conn_c2.cursor()
    # APP_ETL_Agents est dans chaque base cliente, pas centrale
    # On lit les agent_id depuis APP_ETL_Agent_Tables directement
    conn_c2.close()
except:
    pass

updated_agents = 0
inserted_agents = 0
for agent_id in agent_ids:
    cur_c.execute(
        "SELECT id FROM APP_ETL_Agent_Tables WHERE agent_id=? AND table_name=?",
        (agent_id, TABLE_NAME)
    )
    if cur_c.fetchone():
        cur_c.execute("""
            UPDATE APP_ETL_Agent_Tables
            SET target_table=?, source_query=?, primary_key_columns=?,
                sync_type=?, timestamp_column=?, interval_minutes=?,
                priority=?, delete_detection=?, is_enabled=1
            WHERE agent_id=? AND table_name=?
        """, (TARGET_TABLE, source_query, PK_COLUMNS, SYNC_TYPE,
              TIMESTAMP_COL, INTERVAL_MIN, PRIORITY, DELETE_DET,
              agent_id, TABLE_NAME))
        updated_agents += 1
    else:
        cur_c.execute("""
            INSERT INTO APP_ETL_Agent_Tables
                (agent_id, table_name, target_table, source_query,
                 primary_key_columns, sync_type, timestamp_column,
                 interval_minutes, priority, delete_detection, is_enabled)
            VALUES (?,?,?,?,?,?,?,?,?,?,1)
        """, (agent_id, TABLE_NAME, TARGET_TABLE, source_query,
              PK_COLUMNS, SYNC_TYPE, TIMESTAMP_COL, INTERVAL_MIN,
              PRIORITY, DELETE_DET))
        inserted_agents += 1

conn_c.commit()
print(f"  ✓ {len(agent_ids)} agent(s) : {inserted_agents} insérés, {updated_agents} mis à jour")

# Récupérer la liste des DWH
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

# ─────────────────────────────────────────────────────────────
# 4. Propager vers APP_ETL_Tables_Published (chaque DWH cliente)
# ─────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("ÉTAPE 4 — APP_ETL_Tables_Published (toutes bases DWH)")
print("=" * 70)

import os
server_central = os.getenv('DB_SERVER', 'kasoft.selfip.net')
user_central   = os.getenv('DB_USER',   'sa')
pwd_central    = os.getenv('DB_PASSWORD', '')

errors = []
for row in dwh_list:
    code_dwh, nom, base_dwh, db_name, serveur, user_dwh, pwd_dwh = row
    db  = db_name or base_dwh
    srv = serveur or server_central
    usr = user_dwh or user_central
    pwd = pwd_dwh  or pwd_central

    print(f"\n  [{code_dwh}] {nom}  →  {srv}/{db}")
    try:
        conn_d = get_conn_to(srv, db, usr, pwd)
        cur_d  = conn_d.cursor()

        cur_d.execute(
            "SELECT id FROM APP_ETL_Tables_Published WHERE code=?",
            (CODE,)
        )
        if cur_d.fetchone():
            cur_d.execute("""
                UPDATE APP_ETL_Tables_Published
                SET table_name=?, target_table=?, sync_type=?,
                    timestamp_column=?, interval_minutes=?,
                    priority=?, delete_detection=?,
                    description=?, version_centrale=?, is_enabled=1,
                    date_publication=GETDATE()
                WHERE code=?
            """, (TABLE_NAME, TARGET_TABLE, SYNC_TYPE, TIMESTAMP_COL,
                  INTERVAL_MIN, PRIORITY, DELETE_DET,
                  DESCRIPTION, VERSION, CODE))
            print(f"    ✓ APP_ETL_Tables_Published : mise à jour")
        else:
            cur_d.execute("""
                INSERT INTO APP_ETL_Tables_Published
                    (code, table_name, target_table, sync_type,
                     timestamp_column, interval_minutes, priority,
                     delete_detection, description, version_centrale,
                     is_enabled, date_publication)
                VALUES (?,?,?,?,?,?,?,?,?,?,1,GETDATE())
            """, (CODE, TABLE_NAME, TARGET_TABLE, SYNC_TYPE, TIMESTAMP_COL,
                  INTERVAL_MIN, PRIORITY, DELETE_DET, DESCRIPTION, VERSION))
            print(f"    ✓ APP_ETL_Tables_Published : insertion")

        conn_d.commit()
        conn_d.close()
    except Exception as e:
        msg = f"    ✗ Erreur [{code_dwh}] {db} : {e}"
        print(msg)
        errors.append(msg)

# ─────────────────────────────────────────────────────────────
# Résumé
# ─────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
if errors:
    print(f"TERMINÉ AVEC {len(errors)} ERREUR(S) :")
    for e in errors:
        print(e)
else:
    print("TERMINÉ SANS ERREUR")
    print(f"  → Echéances_Ventes ajoutée dans APP_ETL_Tables_Config")
    print(f"  → Propagée vers {len(agent_ids)} agent(s) et {len(dwh_list)} base(s) DWH")
print("=" * 70)
print("\nAction suivante : relancer l'agent ETL chez le client AMM")
print("La 1ère sync créera automatiquement la table [Echéances_Ventes]")
