"""
Source de vérité unique : sync_tables.yaml
Applique les requêtes vers les 3 tables en un seul passage :
  1. ETL_Tables_Config          — lu par le service C# SageETLAgent
  2. APP_ETL_Tables_Config       — lu par l'UI "Gestion Tables ETL"
  3. APP_ETL_Agent_Tables        — lu par chaque agent DWH (bases clients)

Usage: python apply_etl_queries.py
"""
import yaml
import json
import re
import os
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
YAML_PATH  = os.path.join(SCRIPT_DIR, '..', 'etl', 'config', 'sync_tables.yaml')
ENV_PATH   = os.path.join(SCRIPT_DIR, '..', '.env')


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def load_env():
    env = {}
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    k, v = line.split('=', 1)
                    env[k.strip()] = v.strip()
    return env


def get_connection(env, db_override=None):
    import pyodbc
    server = env.get('DB_SERVER', 'localhost')
    db     = db_override or env.get('CENTRAL_DB_NAME') or env.get('DB_NAME', 'OptiBoard_SaaS')
    user   = env.get('DB_USER', 'sa')
    pwd    = env.get('DB_PASSWORD', '')
    port   = env.get('DB_PORT', '1433')
    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={server},{port};DATABASE={db};"
        f"UID={user};PWD={pwd};TrustServerCertificate=yes"
    )
    return pyodbc.connect(conn_str, autocommit=True)


def normalize_query(q):
    """Supprime \r\n et espaces multiples, retire le ; final."""
    q = q.replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')
    q = re.sub(r'\s+', ' ', q).strip().rstrip(';').strip()
    return q


def load_yaml_tables():
    """
    Retourne une liste de dicts :
      name, query_raw, query_norm, target_table, primary_key,
      sync_type, timestamp_column, interval_minutes, priority,
      delete_detection
    """
    with open(YAML_PATH, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    tables = []
    for t in config.get('tables', []):
        name   = t.get('name', '')
        source = t.get('source', {})
        target = t.get('target', {})
        query_raw = source.get('query', '') or ''
        if not name or not query_raw:
            continue
        pk = target.get('primary_key', [])
        if isinstance(pk, str):
            pk = [pk]
        tables.append({
            'name':             name,
            'query_raw':        query_raw,
            'query_norm':       normalize_query(query_raw),
            'target_table':     target.get('table', name),
            'primary_key':      pk,
            'sync_type':        t.get('sync_type', 'incremental'),
            'timestamp_column': t.get('timestamp_column', 'cbModification'),
            'interval_minutes': int(t.get('interval_minutes', 5)),
            'priority':         t.get('priority', 'normal'),
            'delete_detection': 1 if t.get('delete_detection', False) else 0,
        })
    return tables


def get_dwh_databases(cursor):
    """Retourne la liste des db_name depuis APP_ClientDB."""
    try:
        cursor.execute("SELECT DISTINCT db_name FROM APP_ClientDB WHERE db_name IS NOT NULL")
        return [r[0] for r in cursor.fetchall()]
    except Exception:
        return []


# ──────────────────────────────────────────────────────────────
# Étape 1 — ETL_Tables_Config  (service C#)
# ──────────────────────────────────────────────────────────────

def sync_etl_tables_config(cursor, yaml_by_name):
    """Met à jour ETL_Tables_Config depuis le YAML (correspondance par name)."""
    try:
        cursor.execute(
            "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_NAME = 'ETL_Tables_Config' ORDER BY ORDINAL_POSITION"
        )
        cols = [r[0] for r in cursor.fetchall()]
    except Exception as e:
        print(f"  [ETL_Tables_Config] Table absente ou erreur : {e}")
        return

    name_col = 'name' if 'name' in cols else 'table_name'
    cursor.execute(f"SELECT [{name_col}] FROM ETL_Tables_Config")
    db_names = [r[0] for r in cursor.fetchall()]

    updated = 0
    for db_name in db_names:
        entry = yaml_by_name.get(db_name)
        if entry:
            cursor.execute(
                f"UPDATE ETL_Tables_Config SET source_query = ? WHERE [{name_col}] = ?",
                (entry['query_norm'], db_name)
            )
            updated += cursor.rowcount
    print(f"  [ETL_Tables_Config]        {updated}/{len(db_names)} mise(s) à jour")


# ──────────────────────────────────────────────────────────────
# Étape 2 — APP_ETL_Tables_Config  (UI centrale)
# ──────────────────────────────────────────────────────────────

def sync_app_etl_tables_config(cursor, yaml_by_target, yaml_by_name):
    """Met à jour APP_ETL_Tables_Config depuis le YAML.
    Correspondance : target_table en priorité, puis table_name."""
    try:
        cursor.execute(
            "SELECT code, table_name, target_table FROM APP_ETL_Tables_Config"
        )
        rows = cursor.fetchall()
    except Exception as e:
        print(f"  [APP_ETL_Tables_Config]    Table absente ou erreur : {e}")
        return

    updated = 0
    for code, tname, ttable in rows:
        entry = yaml_by_target.get(ttable) or yaml_by_name.get(tname)
        if entry:
            cursor.execute(
                """UPDATE APP_ETL_Tables_Config
                   SET source_query = ?,
                       version = version + 1,
                       date_modification = GETDATE()
                   WHERE code = ?""",
                (entry['query_raw'], code)
            )
            updated += cursor.rowcount
    print(f"  [APP_ETL_Tables_Config]    {updated}/{len(rows)} mise(s) à jour")


# ──────────────────────────────────────────────────────────────
# Étape 3 — APP_ETL_Agent_Tables  (agents DWH, bases clients)
# ──────────────────────────────────────────────────────────────

def sync_agent_tables(env, yaml_by_target, yaml_by_name, central_cursor):
    """Met à jour APP_ETL_Agent_Tables dans chaque base DWH cliente."""
    import pyodbc

    dbs = get_dwh_databases(central_cursor)
    if not dbs:
        print("  [APP_ETL_Agent_Tables]     Aucune base DWH trouvée")
        return

    total_updated = 0
    total_dbs     = 0

    for db in dbs:
        try:
            conn = get_connection(env, db_override=db)
            cur  = conn.cursor()

            # Vérifier que la table existe
            cur.execute(
                "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES "
                "WHERE TABLE_NAME = 'APP_ETL_Agent_Tables'"
            )
            if cur.fetchone()[0] == 0:
                conn.close()
                continue

            cur.execute(
                "SELECT id, table_name, target_table FROM APP_ETL_Agent_Tables"
            )
            rows = cur.fetchall()
            db_updated = 0
            for rid, tname, ttable in rows:
                entry = yaml_by_target.get(ttable) or yaml_by_name.get(tname)
                if entry:
                    cur.execute(
                        """UPDATE APP_ETL_Agent_Tables
                           SET source_query = ?,
                               is_inherited  = 1,
                               is_customized = 0,
                               updated_at    = GETDATE()
                           WHERE id = ?""",
                        (entry['query_raw'], rid)
                    )
                    db_updated += cur.rowcount

            conn.close()
            if db_updated:
                total_updated += db_updated
                total_dbs     += 1
                print(f"    {db}: {db_updated} ligne(s)")

        except Exception:
            pass  # base inaccessible (autre serveur) — ignorée silencieusement

    print(f"  [APP_ETL_Agent_Tables]     {total_updated} mise(s) à jour dans {total_dbs} base(s)")


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("sync_tables.yaml  →  3 tables SQL")
    print("=" * 60)

    env = load_env()
    print(f"\nChargement YAML ({YAML_PATH})...")
    tables = load_yaml_tables()
    print(f"  {len(tables)} tables chargées")

    # Index par nom d'affichage et par table cible
    yaml_by_name   = {t['name']:         t for t in tables}
    yaml_by_target = {t['target_table']: t for t in tables}

    print(f"\nConnexion centrale...")
    conn   = get_connection(env)
    cursor = conn.cursor()

    print()
    sync_etl_tables_config(cursor, yaml_by_name)
    sync_app_etl_tables_config(cursor, yaml_by_target, yaml_by_name)
    sync_agent_tables(env, yaml_by_target, yaml_by_name, cursor)

    conn.close()
    print(f"\n{'=' * 60}")
    print("Done — YAML est la source de vérité unique.")
    print("=" * 60)


if __name__ == '__main__':
    main()
