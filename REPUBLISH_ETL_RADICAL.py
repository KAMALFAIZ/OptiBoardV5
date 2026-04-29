"""
SOLUTION RADICALE — Republie le catalogue ETL central vers tous les agents
ET vers toutes les bases clients actives.

Pour chaque agent actif (KA, FO, AMM, GB) :
1. WIPE APP_ETL_Agent_Tables (central) pour cet agent
2. INSERT toutes les tables depuis ETL_Tables_Config (24 tables)

Pour chaque base client active :
3. WIPE APP_ETL_Tables_Published (client DB)
4. INSERT toutes les tables depuis ETL_Tables_Config

Les agents actifs sont identifies via APP_ETL_Agents_Monitoring.
"""
import pyodbc
from datetime import datetime

CENTRAL_CONN = 'DRIVER={SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019'

def get_central_conn():
    return pyodbc.connect(CENTRAL_CONN, autocommit=False)

def get_client_conn(server, db, user='sa', pwd='SQL@2019'):
    return pyodbc.connect(f'DRIVER={{SQL Server}};SERVER={server};DATABASE={db};UID={user};PWD={pwd}', autocommit=False)

def get_master_tables(cursor):
    cursor.execute("""
        SELECT table_name, source_query, target_table, primary_key, sync_type,
               timestamp_column, interval_minutes, priority, COALESCE(enabled, is_active, 1) as is_enabled,
               COALESCE(delete_detection, 0) as delete_detection, description, batch_size
        FROM ETL_Tables_Config
        WHERE COALESCE(is_active, 1) = 1
        ORDER BY priority, table_name
    """)
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]

def republish_agent(central_cur, agent_id, agent_name, dwh_code, master_tables):
    print(f"  -> Agent {agent_name} ({dwh_code}) [{agent_id}]")
    central_cur.execute("DELETE FROM APP_ETL_Agent_Tables WHERE agent_id = ?", (agent_id,))
    deleted = central_cur.rowcount
    print(f"     Supprime: {deleted} anciennes lignes")
    inserted = 0
    for t in master_tables:
        central_cur.execute("""
            INSERT INTO APP_ETL_Agent_Tables
            (agent_id, table_name, source_query, target_table, societe_code, primary_key_columns,
             sync_type, timestamp_column, interval_minutes, priority, is_enabled, delete_detection,
             description, is_inherited, is_customized, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0, GETDATE(), GETDATE())
        """, (
            agent_id, t['table_name'], t['source_query'], t['target_table'], dwh_code,
            t['primary_key'], t['sync_type'], t['timestamp_column'], t['interval_minutes'],
            t['priority'], 1 if t['is_enabled'] else 0, 1 if t['delete_detection'] else 0,
            t['description']
        ))
        inserted += 1
    print(f"     Insere: {inserted} tables")
    return inserted

def ensure_published_schema(client_cur):
    """Cree la table APP_ETL_Tables_Published si absente, ajoute colonnes manquantes."""
    client_cur.execute("""
        IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name='APP_ETL_Tables_Published')
        CREATE TABLE APP_ETL_Tables_Published (
            id INT IDENTITY(1,1) PRIMARY KEY,
            table_name NVARCHAR(255) NOT NULL UNIQUE,
            source_query NVARCHAR(MAX),
            target_table NVARCHAR(255),
            primary_key NVARCHAR(255),
            sync_type NVARCHAR(50),
            timestamp_column NVARCHAR(255),
            interval_minutes INT,
            priority INT,
            is_enabled BIT DEFAULT 1,
            delete_detection BIT DEFAULT 0,
            description NVARCHAR(MAX),
            batch_size INT,
            version_centrale NVARCHAR(20),
            date_publication DATETIME,
            date_modification DATETIME
        )
    """)
    # ALTER columns if missing
    for col, ddl in [
        ('version_centrale', 'NVARCHAR(20) NULL'),
        ('date_publication', 'DATETIME NULL'),
        ('date_modification', 'DATETIME NULL'),
        ('batch_size', 'INT NULL'),
        ('description', 'NVARCHAR(MAX) NULL'),
    ]:
        client_cur.execute(f"""
            IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_ETL_Tables_Published') AND name='{col}')
            ALTER TABLE APP_ETL_Tables_Published ADD {col} {ddl}
        """)

def republish_client(server, db, master_tables):
    print(f"  -> Client DB {db} @ {server}")
    try:
        conn = get_client_conn(server, db)
    except Exception as e:
        print(f"     ECHEC connexion: {e}")
        return 0
    cur = conn.cursor()
    try:
        ensure_published_schema(cur)
        # Detect schema columns
        cur.execute("SELECT name FROM sys.columns WHERE object_id=OBJECT_ID('APP_ETL_Tables_Published')")
        existing = {r[0] for r in cur.fetchall()}
        pk_col = 'primary_key_columns' if 'primary_key_columns' in existing else 'primary_key'
        has_code = 'code' in existing
        has_version = 'version' in existing

        cur.execute("DELETE FROM APP_ETL_Tables_Published")
        deleted = cur.rowcount
        print(f"     Supprime: {deleted} anciennes lignes (pk_col={pk_col}, has_code={has_code})")
        inserted = 0
        for t in master_tables:
            cols = ['table_name', 'source_query', 'target_table', pk_col, 'sync_type',
                    'timestamp_column', 'interval_minutes', 'priority', 'is_enabled',
                    'delete_detection', 'description',
                    'version_centrale', 'date_publication', 'date_modification']
            vals = [t['table_name'], t['source_query'], t['target_table'], t['primary_key'],
                    t['sync_type'], t['timestamp_column'], t['interval_minutes'], t['priority'],
                    1 if t['is_enabled'] else 0, 1 if t['delete_detection'] else 0,
                    t['description'], 1]
            placeholders = ['?'] * len(vals) + ['GETDATE()', 'GETDATE()']
            if has_code:
                cols.insert(0, 'code')
                vals.insert(0, t['table_name'])
                placeholders.insert(0, '?')
            if has_version:
                cols.append('version')
                vals.append('1.0')
                placeholders.append('?')
            sql = f"INSERT INTO APP_ETL_Tables_Published ({','.join(cols)}) VALUES ({','.join(placeholders)})"
            cur.execute(sql, vals)
            inserted += 1
        conn.commit()
        print(f"     Insere: {inserted} tables")
        return inserted
    except Exception as e:
        conn.rollback()
        print(f"     ERREUR: {e}")
        return 0
    finally:
        conn.close()

def main():
    print("=" * 70)
    print("REPUBLISH ETL RADICAL — Catalogue central vers tous les agents/clients")
    print("=" * 70)
    print(f"Demarre: {datetime.now()}")
    print()

    central = get_central_conn()
    cur = central.cursor()

    master_tables = get_master_tables(cur)
    print(f"Tables maitres dans ETL_Tables_Config: {len(master_tables)}")
    print()

    # 1) Agents centraux
    print("[1] APP_ETL_Agent_Tables (central)")
    print("-" * 70)
    cur.execute("""
        SELECT agent_id, nom, dwh_code FROM APP_ETL_Agents_Monitoring
        ORDER BY nom
    """)
    agents = [(r[0], r[1], r[2]) for r in cur.fetchall()]
    total_agent = 0
    for agent_id, nom, dwh in agents:
        total_agent += republish_agent(cur, agent_id, nom, dwh, master_tables)
    central.commit()
    print(f"\nTotal central: {total_agent} lignes inserees pour {len(agents)} agents")
    print()

    # 2) Clients
    print("[2] APP_ETL_Tables_Published (par client)")
    print("-" * 70)
    cur.execute("""
        SELECT DISTINCT c.dwh_code, c.db_name, c.db_server
        FROM APP_ClientDB c
        INNER JOIN APP_ETL_Agents_Monitoring a ON a.dwh_code = c.dwh_code
        WHERE c.db_server IS NOT NULL AND c.db_server <> ''
    """)
    clients = cur.fetchall()
    total_client = 0
    for dwh, db, server in clients:
        total_client += republish_client(server, db, master_tables)
    print(f"\nTotal clients: {total_client} lignes inserees pour {len(clients)} bases")
    print()

    central.close()
    print("=" * 70)
    print(f"TERMINE: {datetime.now()}")
    print(f"Central: {total_agent} | Clients: {total_client}")
    print("=" * 70)

if __name__ == '__main__':
    main()
