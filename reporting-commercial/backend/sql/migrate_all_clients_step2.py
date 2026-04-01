"""
Step 2 pour TOUS les clients : créer APP_ETL_Agents et tables associées
dans chaque base OptiBoard_XXX qui ne les a pas encore.
"""
import pyodbc, sys, os

C_SERVER = "kasoft.selfip.net"
C_USER   = "sa"
C_PASS   = "SQL@2019"

DRY_RUN  = "--dry-run" in sys.argv

def conn(server, db, user=C_USER, pwd=C_PASS):
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={server};DATABASE={db};UID={user};PWD={pwd};"
        f"TrustServerCertificate=yes;Connection Timeout=15;",
        timeout=15
    )

# ── SQL de création des tables client (idempotent) ────────────────────────────
CREATE_SQL = """
IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME='APP_ETL_Agents')
BEGIN
    CREATE TABLE APP_ETL_Agents (
        id                          INT IDENTITY(1,1) PRIMARY KEY,
        agent_id                    VARCHAR(36)   NOT NULL UNIQUE,
        nom                         NVARCHAR(100) NOT NULL,
        description                 NVARCHAR(500),
        sage_server                 VARCHAR(200),
        sage_database               VARCHAR(200),
        sage_username               VARCHAR(100),
        sage_password               NVARCHAR(200),
        sync_interval_secondes      INT  DEFAULT 300,
        heartbeat_interval_secondes INT  DEFAULT 60,
        batch_size                  INT  DEFAULT 5000,
        max_retry_count             INT  DEFAULT 3,
        is_active                   BIT  DEFAULT 1,
        auto_start                  BIT  DEFAULT 1,
        statut                      VARCHAR(20)   DEFAULT 'inactif',
        last_heartbeat              DATETIME,
        last_sync                   DATETIME,
        last_sync_statut            VARCHAR(20),
        last_error                  NVARCHAR(MAX),
        consecutive_failures        INT  DEFAULT 0,
        total_syncs                 INT  DEFAULT 0,
        total_lignes_sync           BIGINT DEFAULT 0,
        hostname                    VARCHAR(200),
        ip_address                  VARCHAR(50),
        os_info                     NVARCHAR(200),
        agent_version               VARCHAR(50),
        api_key_hash                VARCHAR(64)   NOT NULL,
        api_key_prefix              VARCHAR(20),
        created_at                  DATETIME      DEFAULT GETDATE(),
        updated_at                  DATETIME      DEFAULT GETDATE()
    );
    PRINT 'APP_ETL_Agents cree'
END
ELSE
    PRINT 'APP_ETL_Agents existe deja'

IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME='APP_ETL_Agent_Societes')
BEGIN
    CREATE TABLE APP_ETL_Agent_Societes (
        id              INT IDENTITY(1,1) PRIMARY KEY,
        agent_id        VARCHAR(36)   NOT NULL,
        code_societe    VARCHAR(50)   NOT NULL,
        nom_societe     NVARCHAR(200),
        sage_server     VARCHAR(200),
        sage_database   VARCHAR(200),
        sage_username   VARCHAR(100),
        sage_password   NVARCHAR(200),
        actif           BIT DEFAULT 1,
        date_ajout      DATETIME DEFAULT GETDATE(),
        UNIQUE (agent_id, code_societe)
    );
    PRINT 'APP_ETL_Agent_Societes cree'
END
ELSE
    PRINT 'APP_ETL_Agent_Societes existe deja'

IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME='APP_ETL_Agent_Tables')
BEGIN
    CREATE TABLE APP_ETL_Agent_Tables (
        id              INT IDENTITY(1,1) PRIMARY KEY,
        agent_id        VARCHAR(36)   NOT NULL,
        code_societe    VARCHAR(50)   NOT NULL,
        table_code      VARCHAR(100)  NOT NULL,
        actif           BIT DEFAULT 1,
        date_ajout      DATETIME DEFAULT GETDATE(),
        UNIQUE (agent_id, code_societe, table_code)
    );
    PRINT 'APP_ETL_Agent_Tables cree'
END
ELSE
    PRINT 'APP_ETL_Agent_Tables existe deja'

IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME='APP_ETL_Agent_Sync_Log')
BEGIN
    CREATE TABLE APP_ETL_Agent_Sync_Log (
        id              INT IDENTITY(1,1) PRIMARY KEY,
        agent_id        VARCHAR(36),
        code_societe    VARCHAR(50),
        table_code      VARCHAR(100),
        statut          VARCHAR(20),
        lignes_sync     INT DEFAULT 0,
        debut_sync      DATETIME,
        fin_sync        DATETIME,
        message         NVARCHAR(MAX),
        date_log        DATETIME DEFAULT GETDATE()
    );
    PRINT 'APP_ETL_Agent_Sync_Log cree'
END
ELSE
    PRINT 'APP_ETL_Agent_Sync_Log existe deja'

IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME='APP_Update_History')
BEGIN
    CREATE TABLE APP_Update_History (
        id              INT IDENTITY(1,1) PRIMARY KEY,
        type_maj        VARCHAR(50)   NOT NULL,
        code_element    VARCHAR(100),
        nom_element     NVARCHAR(200),
        version_avant   VARCHAR(50),
        version_apres   VARCHAR(50),
        statut          VARCHAR(20)   DEFAULT 'succes',
        details         NVARCHAR(MAX),
        date_maj        DATETIME      DEFAULT GETDATE()
    );
    PRINT 'APP_Update_History cree'
END
ELSE
    PRINT 'APP_Update_History existe deja'
"""

# ── Récupérer tous les clients ────────────────────────────────────────────────
print("=" * 60)
print(f"Step 2 : Initialisation tables ETL sur toutes les bases clients")
if DRY_RUN:
    print("[DRY-RUN] Aucune écriture")
print("=" * 60)

try:
    cn_central = conn(C_SERVER, "OptiBoard_SaaS")
    cur = cn_central.cursor()
    cur.execute("SELECT dwh_code, db_name, db_server, db_user, db_password FROM APP_ClientDB WHERE actif=1")
    clients = [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]
    cn_central.close()
except Exception as e:
    print(f"ERREUR lecture APP_ClientDB: {e}")
    sys.exit(1)

print(f"\n{len(clients)} client(s) à traiter\n")

ok = 0; skipped = 0; errors = 0

for c in clients:
    code    = c['dwh_code']
    db_name = c['db_name'] or f"OptiBoard_{code}"
    srv     = c['db_server'] or C_SERVER
    usr     = c['db_user']   or C_USER
    pwd_db  = c['db_password'] or C_PASS

    print(f"--- Client: {code} -> {db_name} sur {srv} ---")

    try:
        cn2 = conn(srv, db_name, usr, pwd_db)
        cur2 = cn2.cursor()

        # Vérifier si les tables existent déjà
        cur2.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME='APP_ETL_Agents'")
        already = cur2.fetchone()[0]

        if already:
            print(f"  [SKIP] APP_ETL_Agents déjà présent")
            skipped += 1
            cn2.close()
            continue

        if DRY_RUN:
            print(f"  [DRY-RUN] Créerait APP_ETL_Agents + 4 tables")
            cn2.close()
            continue

        # Exécuter la création
        for stmt in CREATE_SQL.split('\n\n'):
            stmt = stmt.strip()
            if stmt:
                try:
                    cur2.execute(stmt)
                except Exception as e2:
                    if 'There is already an object' in str(e2):
                        pass  # table déjà créée dans le même batch
                    else:
                        raise

        cn2.commit()
        cn2.close()
        print(f"  [OK] Tables créées")
        ok += 1

    except pyodbc.Error as e:
        err = str(e)
        if '4060' in err or 'Cannot open database' in err:
            print(f"  [SKIP] Base {db_name} inexistante sur {srv}")
            skipped += 1
        elif '18456' in err or 'Login failed' in err:
            print(f"  [SKIP] Accès refusé à {db_name}")
            skipped += 1
        else:
            print(f"  [ERREUR] {e}")
            errors += 1

print()
print("=" * 60)
print(f"Résultat : {ok} OK | {skipped} skippés | {errors} erreurs")
if DRY_RUN:
    print("(DRY-RUN - rien écrit)")
print("=" * 60)
