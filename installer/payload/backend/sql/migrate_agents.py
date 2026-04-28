"""
migrate_agents.py — Migration agents ETL : centrale → bases clients
====================================================================
Objectif :
  Lire tous les agents depuis APP_ETL_Agents_OLD (centrale)
  et les copier dans les bases clients correspondantes :
    - APP_ETL_Agents        (config complete + credentials)
    - APP_ETL_Agent_Tables  (tables configurees par agent)
    - APP_ETL_Agent_Sync_Log (derniers logs, configurable)

Puis mettre a jour APP_ETL_Agents_Monitoring (centrale)
avec les metriques de chaque agent.

Prerequis :
  1. Avoir execute 008_migrate_agents_central_step1.sql sur OptiBoard_SaaS
  2. Avoir execute 008_migrate_agents_client_template.sql sur chaque base client

Usage :
  python migrate_agents.py
  python migrate_agents.py --dry-run      (simulation sans ecriture)
  python migrate_agents.py --client ALBG  (migrer un seul client)
  python migrate_agents.py --logs-days 7  (migrer les logs des 7 derniers jours)

Configuration :
  Lire depuis .env ou variables d environnement :
    CENTRAL_DB_SERVER, CENTRAL_DB_NAME, CENTRAL_DB_USER, CENTRAL_DB_PASSWORD
    DB_DRIVER (defaut: {ODBC Driver 17 for SQL Server})
"""

import sys
import os
import argparse
import pyodbc
from datetime import datetime
from pathlib import Path

# ────────────────────────────────────────────────────────────
# Configuration (depuis .env ou env vars)
# ────────────────────────────────────────────────────────────
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"'))

DRIVER   = os.getenv("DB_DRIVER", "{ODBC Driver 17 for SQL Server}")
C_SERVER = os.getenv("CENTRAL_DB_SERVER") or os.getenv("DB_SERVER", "")
C_NAME   = os.getenv("CENTRAL_DB_NAME",   "OptiBoard_SaaS")
C_USER   = os.getenv("CENTRAL_DB_USER")   or os.getenv("DB_USER", "")
C_PASS   = os.getenv("CENTRAL_DB_PASSWORD") or os.getenv("DB_PASSWORD", "")


# ────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────

def conn_str(server: str, db: str, user: str, pwd: str) -> str:
    return (
        f"DRIVER={DRIVER};SERVER={server};DATABASE={db};"
        f"UID={user};PWD={pwd};TrustServerCertificate=yes;"
    )

def connect_central():
    return pyodbc.connect(conn_str(C_SERVER, C_NAME, C_USER, C_PASS), timeout=15)

def connect_client(info: dict):
    # client_db_server = serveur de la base OptiBoard_cltXXX
    # Si null -> meme serveur que la centrale (C_SERVER)
    # NE PAS utiliser serveur_dwh qui est le serveur Sage du client
    server = info.get("client_db_server") or C_SERVER
    db     = info.get("client_db_name")   or f"OptiBoard_{info['code']}"
    user   = info.get("client_db_user")   or C_USER
    pwd    = info.get("client_db_password") or C_PASS
    return pyodbc.connect(conn_str(server, db, user, pwd), timeout=15), db

def fetch(cursor, query, params=None):
    cursor.execute(query, params or ())
    cols = [c[0] for c in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]

def log(msg: str, level: str = "INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {msg}")


# ────────────────────────────────────────────────────────────
# Lecture des donnees depuis la centrale (OLD tables)
# ────────────────────────────────────────────────────────────

def get_clients(cursor, filter_code=None):
    q = """
        SELECT d.code, d.nom,
               d.serveur_dwh, d.user_dwh, d.password_dwh,
               c.db_server AS client_db_server,
               c.db_name   AS client_db_name,
               c.db_user   AS client_db_user,
               c.db_password AS client_db_password
        FROM APP_DWH d
        LEFT JOIN APP_ClientDB c ON d.code = c.dwh_code
        WHERE d.actif = 1
    """
    params = ()
    if filter_code:
        q += " AND d.code = ?"
        params = (filter_code,)
    q += " ORDER BY d.nom"
    return fetch(cursor, q, params)


def get_agents_for_client(cursor, dwh_code: str):
    """Lit les agents depuis APP_ETL_Agents_OLD (backup centrale)."""
    try:
        return fetch(cursor,
            "SELECT * FROM APP_ETL_Agents_OLD WHERE dwh_code = ?",
            (dwh_code,)
        )
    except Exception:
        log("APP_ETL_Agents_OLD absente — tentative sur APP_ETL_Agents", "WARN")
        try:
            return fetch(cursor,
                "SELECT * FROM APP_ETL_Agents WHERE dwh_code = ?",
                (dwh_code,)
            )
        except Exception:
            return []


def get_agent_tables(cursor, agent_id: str):
    """Lit les tables depuis APP_ETL_Agent_Tables_OLD."""
    try:
        return fetch(cursor,
            "SELECT * FROM APP_ETL_Agent_Tables_OLD WHERE agent_id = ?",
            (agent_id,)
        )
    except Exception:
        try:
            return fetch(cursor,
                "SELECT * FROM APP_ETL_Agent_Tables WHERE agent_id = ?",
                (agent_id,)
            )
        except Exception:
            return []


def get_agent_logs(cursor, agent_id: str, days: int):
    """Lit les N derniers jours de logs depuis APP_ETL_Agent_Sync_Log_OLD."""
    try:
        return fetch(cursor,
            """SELECT * FROM APP_ETL_Agent_Sync_Log_OLD
               WHERE agent_id = ?
                 AND started_at >= DATEADD(DAY, ?, GETDATE())
               ORDER BY started_at DESC""",
            (agent_id, -days)
        )
    except Exception:
        return []


# ────────────────────────────────────────────────────────────
# Ecriture dans la base CLIENT
# ────────────────────────────────────────────────────────────

def migrate_agent_to_client(ccursor, agent: dict, dry_run: bool) -> bool:
    """Insere ou met a jour un agent dans la base client."""
    agent_id = str(agent.get("agent_id", ""))
    nom      = agent.get("name") or agent.get("nom") or f"Agent {agent_id[:8]}"

    # Verifier si l agent existe deja
    ccursor.execute("SELECT agent_id FROM APP_ETL_Agents WHERE agent_id = ?", (agent_id,))
    exists = ccursor.fetchone()

    if exists:
        log(f"  Agent '{nom}' ({agent_id[:8]}...) deja present — skipped", "SKIP")
        return False

    if dry_run:
        log(f"  [DRY-RUN] Insererait agent '{nom}' ({agent_id[:8]}...)")
        return True

    ccursor.execute("""
        INSERT INTO APP_ETL_Agents (
            agent_id, nom, description,
            sage_server, sage_database, sage_username, sage_password,
            sync_interval_secondes, heartbeat_interval_secondes, batch_size,
            is_active, auto_start,
            statut, last_heartbeat, last_sync, last_sync_statut,
            consecutive_failures, total_syncs, total_lignes_sync,
            hostname, ip_address, os_info, agent_version,
            api_key_hash, api_key_prefix,
            created_at, updated_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        agent_id,
        nom,
        agent.get("description"),
        agent.get("sage_server"),
        agent.get("sage_database"),
        agent.get("sage_username"),
        agent.get("sage_password"),
        agent.get("sync_interval_seconds", 300),
        agent.get("heartbeat_interval_seconds", 30),
        agent.get("batch_size", 10000),
        1 if agent.get("is_active", True) else 0,
        1 if agent.get("auto_start", True) else 0,
        "inactif",
        agent.get("last_heartbeat"),
        agent.get("last_sync"),
        agent.get("last_sync_status"),
        agent.get("consecutive_failures", 0),
        agent.get("total_syncs", 0),
        agent.get("total_rows_synced", 0),
        agent.get("hostname"),
        agent.get("ip_address"),
        agent.get("os_info"),
        agent.get("agent_version"),
        agent.get("api_key_hash"),
        agent.get("api_key_prefix"),
        agent.get("created_at") or datetime.now(),
        agent.get("updated_at") or datetime.now(),
    ))
    log(f"  [OK] Agent '{nom}' migre")
    return True


def migrate_tables_to_client(ccursor, tables: list, agent_id: str, dry_run: bool) -> int:
    """Insere les tables configurees pour cet agent dans la base client."""
    count = 0
    for t in tables:
        table_name   = t.get("table_name", "")
        societe_code = t.get("societe_code", "")

        ccursor.execute(
            "SELECT id FROM APP_ETL_Agent_Tables WHERE agent_id=? AND table_name=? AND societe_code=?",
            (agent_id, table_name, societe_code)
        )
        if ccursor.fetchone():
            continue

        if dry_run:
            log(f"    [DRY-RUN] Insererait table '{table_name}' ({societe_code})")
            count += 1
            continue

        try:
            ccursor.execute("""
                INSERT INTO APP_ETL_Agent_Tables (
                    agent_id, table_name, source_query, societe_code,
                    target_table, primary_key_columns,
                    sync_type, timestamp_column, interval_minutes,
                    priority, delete_detection, description,
                    is_inherited, is_customized, is_enabled,
                    last_sync, last_sync_status, last_sync_rows,
                    created_at, updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                agent_id,
                table_name,
                t.get("source_query", ""),
                societe_code,
                t.get("target_table", ""),
                t.get("primary_key_columns", "[]"),
                t.get("sync_type", "incremental"),
                t.get("timestamp_column", "cbModification"),
                t.get("interval_minutes", 5),
                t.get("priority", "normal"),
                1 if t.get("delete_detection") else 0,
                t.get("description"),
                1 if t.get("is_inherited") else 0,
                1 if t.get("is_customized") else 0,
                1 if t.get("is_enabled", True) else 0,
                t.get("last_sync"),
                t.get("last_sync_status"),
                t.get("last_sync_rows", 0),
                t.get("created_at") or datetime.now(),
                t.get("updated_at") or datetime.now(),
            ))
            count += 1
        except Exception as e:
            log(f"    [WARN] Table '{table_name}': {e}", "WARN")
    return count


def migrate_logs_to_client(ccursor, logs: list, dry_run: bool) -> int:
    """Insere les logs recents dans la base client."""
    if not logs or dry_run:
        return len(logs) if dry_run else 0
    count = 0
    for lg in logs:
        try:
            ccursor.execute("""
                INSERT INTO APP_ETL_Agent_Sync_Log (
                    agent_id, table_name, societe_code, batch_id,
                    started_at, completed_at, duration_seconds, status,
                    rows_extracted, rows_inserted, rows_updated, rows_failed,
                    sync_timestamp_start, sync_timestamp_end, error_message
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                str(lg.get("agent_id", "")),
                lg.get("table_name", ""),
                lg.get("societe_code", ""),
                lg.get("batch_id"),
                lg.get("started_at"),
                lg.get("completed_at"),
                lg.get("duration_seconds"),
                lg.get("status", "success"),
                lg.get("rows_extracted", 0),
                lg.get("rows_inserted", 0),
                lg.get("rows_updated", 0),
                lg.get("rows_failed", 0),
                lg.get("sync_timestamp_start"),
                lg.get("sync_timestamp_end"),
                lg.get("error_message"),
            ))
            count += 1
        except Exception:
            pass
    return count


def update_central_monitoring(central_conn, agent: dict, dry_run: bool):
    """Met a jour APP_ETL_Agents_Monitoring dans la centrale."""
    if dry_run:
        return
    agent_id = str(agent.get("agent_id", ""))
    try:
        c = central_conn.cursor()
        c.execute(
            "SELECT agent_id FROM APP_ETL_Agents_Monitoring WHERE agent_id = ?",
            (agent_id,)
        )
        if c.fetchone():
            c.execute("""
                UPDATE APP_ETL_Agents_Monitoring SET
                    hostname=?, ip_address=?, os_info=?, agent_version=?,
                    last_heartbeat=?, last_sync=?, consecutive_failures=?,
                    total_syncs=?, total_lignes_sync=?, date_modification=GETDATE()
                WHERE agent_id=?
            """, (
                agent.get("hostname"), agent.get("ip_address"),
                agent.get("os_info"), agent.get("agent_version"),
                agent.get("last_heartbeat"), agent.get("last_sync"),
                agent.get("consecutive_failures", 0),
                agent.get("total_syncs", 0), agent.get("total_rows_synced", 0),
                agent_id
            ))
        central_conn.commit()
    except Exception as e:
        log(f"  [WARN] Monitoring central non mis a jour: {e}", "WARN")


# ────────────────────────────────────────────────────────────
# ORCHESTRATION PRINCIPALE
# ────────────────────────────────────────────────────────────

def run(dry_run: bool, filter_client: str, logs_days: int):
    log("=" * 60)
    log("MIGRATION AGENTS ETL : CENTRALE -> BASES CLIENTS")
    if dry_run:
        log("MODE DRY-RUN : aucune ecriture ne sera effectuee", "WARN")
    log("=" * 60)

    central = connect_central()
    cc = central.cursor()

    clients = get_clients(cc, filter_client)
    log(f"{len(clients)} client(s) a traiter")

    total_agents = total_tables = total_logs = 0

    for client in clients:
        code = client["code"]
        nom  = client["nom"]
        log(f"\n--- Client : {nom} ({code}) ---")

        # Lire agents depuis centrale (OLD)
        agents = get_agents_for_client(cc, code)
        if not agents:
            log("  Aucun agent dans la centrale pour ce client", "INFO")
            continue

        log(f"  {len(agents)} agent(s) trouve(s)")

        # Connexion base client
        try:
            client_conn, db_name = connect_client(client)
            client_conn.autocommit = False
            ccursor = client_conn.cursor()
            log(f"  Connecte a {db_name}")
        except Exception as e:
            log(f"  [ERREUR] Connexion impossible : {e}", "ERR")
            continue

        for agent in agents:
            agent_id  = str(agent.get("agent_id", ""))
            agent_nom = agent.get("name") or agent.get("nom") or agent_id[:8]

            # 1. Migrer l agent
            migrated = migrate_agent_to_client(ccursor, agent, dry_run)
            if migrated:
                total_agents += 1

            # 2. Migrer ses tables
            tables = get_agent_tables(cc, agent_id)
            n_tables = migrate_tables_to_client(ccursor, tables, agent_id, dry_run)
            total_tables += n_tables
            if n_tables:
                log(f"    {n_tables} table(s) migree(s) pour {agent_nom}")

            # 3. Migrer les logs recents
            if logs_days > 0:
                logs = get_agent_logs(cc, agent_id, logs_days)
                n_logs = migrate_logs_to_client(ccursor, logs, dry_run)
                total_logs += n_logs
                if n_logs:
                    log(f"    {n_logs} log(s) migre(s) pour {agent_nom}")

            # 4. Mettre a jour monitoring central
            update_central_monitoring(central, agent, dry_run)

        if not dry_run:
            client_conn.commit()
        client_conn.close()

    central.close()

    log("\n" + "=" * 60)
    log("MIGRATION TERMINEE")
    log(f"  Agents migres  : {total_agents}")
    log(f"  Tables migrees : {total_tables}")
    log(f"  Logs migres    : {total_logs}")
    if dry_run:
        log("  (DRY-RUN : rien n a ete ecrit)", "WARN")
    log("=" * 60)
    log("ETAPE SUIVANTE : verifier les bases clients,")
    log("puis supprimer les tables _OLD si tout est correct :")
    log("  DROP TABLE OptiBoard_SaaS.dbo.APP_ETL_Agents_OLD")
    log("  DROP TABLE OptiBoard_SaaS.dbo.APP_ETL_Agent_Tables_OLD")
    log("  DROP TABLE OptiBoard_SaaS.dbo.APP_ETL_Agent_Sync_Log_OLD")


# ────────────────────────────────────────────────────────────
# ENTRYPOINT
# ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migration agents ETL centrale → clients")
    parser.add_argument("--dry-run",    action="store_true", help="Simulation sans ecriture")
    parser.add_argument("--client",     type=str, default=None, help="Migrer un seul client (code DWH)")
    parser.add_argument("--logs-days",  type=int, default=7,    help="Nb de jours de logs a migrer (0=aucun)")
    args = parser.parse_args()

    if not C_SERVER:
        print("[ERREUR] CENTRAL_DB_SERVER non configure dans .env")
        sys.exit(1)

    run(
        dry_run=args.dry_run,
        filter_client=args.client,
        logs_days=args.logs_days
    )
