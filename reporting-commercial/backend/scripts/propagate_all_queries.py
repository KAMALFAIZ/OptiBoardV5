"""
Propage toutes les requêtes de APP_ETL_Tables_Config (UI = source de vérité)
vers ETL_Tables_Config, APP_ETL_Agent_Tables, et sync_tables.yaml.
Usage: python scripts/propagate_all_queries.py
"""
import sys, os, re, json, pyodbc, threading
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH   = os.path.join(SCRIPT_DIR, '..', '.env')
YAML_PATH  = os.path.abspath(os.path.join(SCRIPT_DIR, '..', 'etl', 'config', 'sync_tables.yaml'))

sys.path.insert(0, os.path.join(SCRIPT_DIR, '..'))
from app.services.query_crypto import enc_query


def load_env():
    env = {}
    with open(ENV_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip()
    return env


def central_conn(env):
    s = env.get('DB_SERVER','localhost')
    p = env.get('DB_PORT','1433')
    d = env.get('DB_NAME','OptiBoard_SaaS')
    u = env.get('DB_USER','sa')
    pw = env.get('DB_PASSWORD','')
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={s},{p};DATABASE={d};"
        f"UID={u};PWD={pw};TrustServerCertificate=yes", autocommit=True)


def client_conn(env, db):
    s = env.get('DB_SERVER','localhost')
    p = env.get('DB_PORT','1433')
    u = env.get('DB_USER','sa')
    pw = env.get('DB_PASSWORD','')
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={s},{p};DATABASE={db};"
        f"UID={u};PWD={pw};TrustServerCertificate=yes", autocommit=True)


def main():
    env = load_env()
    cc  = central_conn(env)
    cur = cc.cursor()

    # 1. Lire toutes les entrées de APP_ETL_Tables_Config (source de vérité UI)
    cur.execute("SELECT code, table_name, target_table, source_query FROM APP_ETL_Tables_Config WHERE actif=1 AND source_query IS NOT NULL")
    rows = cur.fetchall()
    print(f"APP_ETL_Tables_Config : {len(rows)} entrées actives\n")

    # Index par target_table et par table_name
    by_target = {r[2]: {'code': r[0], 'name': r[1], 'target': r[2], 'query': r[3]} for r in rows}
    by_name   = {r[1]: by_target[r[2]] for r in rows if r[2] in by_target}

    # ── 2. ETL_Tables_Config (C# service) ──────────────────────────────
    print("── ETL_Tables_Config ──")
    try:
        cur.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='ETL_Tables_Config'")
        cols = [r[0] for r in cur.fetchall()]
        name_col   = 'name' if 'name' in cols else 'table_name'
        target_col = 'target_table' if 'target_table' in cols else None
        cur.execute(f"SELECT [{name_col}]{', target_table' if target_col else ''} FROM ETL_Tables_Config")
        etl_rows = cur.fetchall()
        updated = 0
        for row in etl_rows:
            tname  = row[0]
            ttable = row[1] if target_col else tname
            entry  = by_target.get(ttable) or by_name.get(tname)
            if entry:
                cur.execute(
                    f"UPDATE ETL_Tables_Config SET source_query=? WHERE [{name_col}]=?",
                    (entry['query'], tname)
                )
                updated += cur.rowcount
        print(f"  {updated}/{len(etl_rows)} mise(s) à jour\n")
    except Exception as e:
        print(f"  ERREUR : {e}\n")

    # ── 3. APP_ETL_Agent_Tables (agents DWH) ────────────────────────────
    print("── APP_ETL_Agent_Tables ──")
    cur.execute("SELECT DISTINCT db_name FROM APP_ClientDB WHERE db_name IS NOT NULL")
    dbs = [r[0] for r in cur.fetchall()]
    total_agent = 0
    for db in dbs:
        try:
            c2  = client_conn(env, db)
            c2c = c2.cursor()
            c2c.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME='APP_ETL_Agent_Tables'")
            if c2c.fetchone()[0] == 0:
                c2.close(); continue
            c2c.execute("SELECT id, table_name, target_table FROM APP_ETL_Agent_Tables")
            agent_rows = c2c.fetchall()
            db_upd = 0
            for rid, tname, ttable in agent_rows:
                entry = by_target.get(ttable) or by_name.get(tname)
                if entry:
                    c2c.execute(
                        "UPDATE APP_ETL_Agent_Tables SET source_query=?, is_inherited=1, is_customized=0, updated_at=GETDATE() WHERE id=?",
                        (enc_query(entry['query']), rid)
                    )
                    db_upd += c2c.rowcount
            c2.close()
            if db_upd:
                print(f"  {db}: {db_upd} ligne(s)")
                total_agent += db_upd
        except Exception:
            pass
    print(f"  Total agents : {total_agent}\n")

    # ── 4. sync_tables.yaml ─────────────────────────────────────────────
    print("── sync_tables.yaml ──")
    try:
        import yaml
        with open(YAML_PATH, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        yaml_upd = 0
        for t in data.get('tables', []):
            tgt = t.get('target', {})
            if not isinstance(tgt, dict): continue
            ttable = tgt.get('table', '')
            entry  = by_target.get(ttable)
            if entry and entry['query']:
                t['source']['query'] = entry['query']
                yaml_upd += 1
        with open(YAML_PATH, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False,
                      sort_keys=False, width=10000)
        print(f"  {yaml_upd} entrées mises à jour dans {YAML_PATH}\n")
    except Exception as e:
        print(f"  ERREUR : {e}\n")

    cc.close()
    print("Done — APP_ETL_Tables_Config est la source de vérité.")


if __name__ == '__main__':
    main()
