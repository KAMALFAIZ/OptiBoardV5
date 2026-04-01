"""
Solution radicale : creer OptiBoard_cltKASOFT sur le serveur local
et mettre a jour APP_DWH avec les bonnes infos optiboard.
"""
import sys
import pyodbc

# ── Connexion centrale (pour lire/ecrire APP_DWH) ─────────────────────────────
CENTRAL_SERVER   = "kasoft.selfip.net"
CENTRAL_DB       = "OptiBoard_SaaS"
CENTRAL_USER     = "sa"
CENTRAL_PASSWORD = "SQL@2019"

# ── Serveur local (pour creer OptiBoard_cltKASOFT) ───────────────────────────
LOCAL_SERVER = "."          # Serveur SQL local
CLIENT_DB    = "OptiBoard_cltKASOFT"
DWH_CODE     = "KASOFT"

def conn_str_central():
    return (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={CENTRAL_SERVER};DATABASE={CENTRAL_DB};"
        f"UID={CENTRAL_USER};PWD={CENTRAL_PASSWORD};TrustServerCertificate=yes;"
    )

LOCAL_USER     = "sa"
LOCAL_PASSWORD = "SQL@2019"   # mot de passe sa local (meme serveur)

def conn_str_local(db="master"):
    # Essayer d'abord Windows Auth, puis SQL Auth
    return (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={LOCAL_SERVER};DATABASE={db};"
        f"UID={LOCAL_USER};PWD={LOCAL_PASSWORD};TrustServerCertificate=yes;"
    )

# ── Tables a creer dans OptiBoard_cltKASOFT ───────────────────────────────────
# (version simplifiee - tables essentielles pour la publication)
CLIENT_TABLES_SQL = """
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Users' AND xtype='U')
CREATE TABLE APP_Users (
    id INT IDENTITY(1,1) PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    nom NVARCHAR(100),
    prenom NVARCHAR(100),
    email VARCHAR(200),
    role_dwh VARCHAR(50) DEFAULT 'user',
    actif BIT DEFAULT 1,
    date_creation DATETIME DEFAULT GETDATE()
);

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_UserPages' AND xtype='U')
CREATE TABLE APP_UserPages (
    id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NOT NULL,
    page_code VARCHAR(50) NOT NULL
);

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_UserMenus' AND xtype='U')
CREATE TABLE APP_UserMenus (
    id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NOT NULL,
    menu_id INT NOT NULL,
    can_view BIT DEFAULT 1,
    can_export BIT DEFAULT 1
);

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Dashboards' AND xtype='U')
CREATE TABLE APP_Dashboards (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nom NVARCHAR(200) NOT NULL,
    code VARCHAR(100) NULL,
    description NVARCHAR(500),
    config NVARCHAR(MAX),
    widgets NVARCHAR(MAX),
    is_public BIT DEFAULT 0,
    is_custom BIT DEFAULT 0,
    is_customized BIT DEFAULT 0,
    created_by INT NULL,
    actif BIT DEFAULT 1,
    date_creation DATETIME DEFAULT GETDATE(),
    date_modification DATETIME DEFAULT GETDATE()
);

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_DataSources' AND xtype='U')
CREATE TABLE APP_DataSources (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nom NVARCHAR(200) NOT NULL,
    code VARCHAR(100) NULL,
    type VARCHAR(50) NOT NULL DEFAULT 'query',
    query_template NVARCHAR(MAX),
    parameters NVARCHAR(MAX),
    description NVARCHAR(500),
    is_custom BIT DEFAULT 0,
    is_customized BIT DEFAULT 0,
    date_creation DATETIME DEFAULT GETDATE()
);

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_GridViews' AND xtype='U')
CREATE TABLE APP_GridViews (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nom NVARCHAR(200) NOT NULL,
    code VARCHAR(100) NULL,
    description NVARCHAR(500),
    query_template NVARCHAR(MAX),
    columns_config NVARCHAR(MAX),
    parameters NVARCHAR(MAX),
    features NVARCHAR(MAX),
    is_custom BIT DEFAULT 0,
    is_customized BIT DEFAULT 0,
    actif BIT DEFAULT 1,
    date_creation DATETIME DEFAULT GETDATE(),
    date_modification DATETIME DEFAULT GETDATE()
);

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Pivots_V2' AND xtype='U')
CREATE TABLE APP_Pivots_V2 (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nom NVARCHAR(200) NOT NULL,
    code VARCHAR(100) NULL,
    description NVARCHAR(500),
    data_source_id INT NULL,
    data_source_code VARCHAR(100),
    rows_config NVARCHAR(MAX),
    columns_config NVARCHAR(MAX),
    filters_config NVARCHAR(MAX),
    values_config NVARCHAR(MAX),
    formatting_rules NVARCHAR(MAX),
    source_params NVARCHAR(MAX),
    is_custom BIT DEFAULT 0,
    is_customized BIT DEFAULT 0,
    actif BIT DEFAULT 1,
    date_creation DATETIME DEFAULT GETDATE(),
    date_modification DATETIME DEFAULT GETDATE()
);

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Menus' AND xtype='U')
CREATE TABLE APP_Menus (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nom NVARCHAR(100) NOT NULL,
    code VARCHAR(100),
    icon VARCHAR(50),
    url VARCHAR(200),
    parent_id INT NULL,
    parent_code VARCHAR(100),
    ordre INT DEFAULT 0,
    type VARCHAR(20) DEFAULT 'link',
    target_id INT NULL,
    actif BIT DEFAULT 1,
    is_custom BIT DEFAULT 0,
    is_customized BIT DEFAULT 0,
    roles NVARCHAR(200),
    date_creation DATETIME DEFAULT GETDATE()
);

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Settings' AND xtype='U')
CREATE TABLE APP_Settings (
    id INT IDENTITY(1,1) PRIMARY KEY,
    setting_key VARCHAR(100) NOT NULL,
    setting_value NVARCHAR(MAX),
    setting_type VARCHAR(20) DEFAULT 'string',
    description NVARCHAR(500),
    date_modification DATETIME DEFAULT GETDATE()
);

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_EmailConfig' AND xtype='U')
CREATE TABLE APP_EmailConfig (
    id INT IDENTITY(1,1) PRIMARY KEY,
    smtp_server VARCHAR(200),
    smtp_port INT DEFAULT 587,
    smtp_username VARCHAR(200),
    smtp_password VARCHAR(200),
    from_email VARCHAR(200),
    from_name NVARCHAR(100),
    use_ssl BIT DEFAULT 0,
    use_tls BIT DEFAULT 1,
    actif BIT DEFAULT 1,
    date_modification DATETIME DEFAULT GETDATE()
);
"""

def ok(msg):  print(f"[OK]  {msg}")
def err(msg): print(f"[ERR] {msg}", file=sys.stderr)

def main():
    # ── ETAPE 1 : Tester connexion locale ────────────────────────────────────
    print(f"\n=== ETAPE 1 : Test connexion locale ({LOCAL_SERVER}) ===")
    try:
        c = pyodbc.connect(conn_str_local("master"), timeout=10)
        c.close()
        ok(f"Connexion Windows Auth sur {LOCAL_SERVER} reussie")
    except Exception as e:
        err(f"Impossible de se connecter a {LOCAL_SERVER} : {e}")
        err("Verifiez que SQL Server est bien installe localement et que l'auth Windows est activee.")
        sys.exit(1)

    # ── ETAPE 2 : Creer la base ───────────────────────────────────────────────
    print(f"\n=== ETAPE 2 : Creation de {CLIENT_DB} ===")
    try:
        c = pyodbc.connect(conn_str_local("master"), timeout=10)
        c.autocommit = True
        cur = c.cursor()
        cur.execute(f"SELECT COUNT(*) FROM sys.databases WHERE name = '{CLIENT_DB}'")
        exists = cur.fetchone()[0] > 0
        if exists:
            ok(f"{CLIENT_DB} existe deja")
        else:
            cur.execute(f"CREATE DATABASE [{CLIENT_DB}]")
            ok(f"{CLIENT_DB} creee avec succes")
        c.close()
    except Exception as e:
        err(f"Erreur creation base : {e}")
        sys.exit(1)

    # ── ETAPE 3 : Creer les tables ────────────────────────────────────────────
    print(f"\n=== ETAPE 3 : Creation des tables dans {CLIENT_DB} ===")
    try:
        c = pyodbc.connect(conn_str_local(CLIENT_DB), timeout=30)
        c.autocommit = True
        cur = c.cursor()
        tables_ok = 0
        for stmt in CLIENT_TABLES_SQL.split(";"):
            lines = [l for l in stmt.strip().split("\n")
                     if l.strip() and not l.strip().startswith("--")]
            clean = "\n".join(lines).strip()
            if len(clean) < 10:
                continue
            try:
                cur.execute(clean)
                tables_ok += 1
            except Exception as e2:
                err(f"Table: {e2}")
        ok(f"{tables_ok} statements executes")
        c.close()
    except Exception as e:
        err(f"Erreur creation tables : {e}")
        sys.exit(1)

    # ── ETAPE 4 : Verifier les tables cles ───────────────────────────────────
    print(f"\n=== ETAPE 4 : Verification des tables ===")
    tables_check = ["APP_DataSources","APP_GridViews","APP_Pivots_V2",
                    "APP_Dashboards","APP_Menus","APP_Users"]
    try:
        c = pyodbc.connect(conn_str_local(CLIENT_DB), timeout=10)
        cur = c.cursor()
        for t in tables_check:
            cur.execute(f"SELECT COUNT(*) FROM sysobjects WHERE name='{t}' AND xtype='U'")
            exists = cur.fetchone()[0] == 1
            print(f"  {'[OK]' if exists else '[MISSING]'}  {t}")
        c.close()
    except Exception as e:
        err(f"Verification: {e}")

    # ── ETAPE 5 : Mettre a jour APP_DWH avec infos optiboard ─────────────────
    print(f"\n=== ETAPE 5 : Mise a jour APP_DWH (colonnes optiboard) ===")
    try:
        c = pyodbc.connect(conn_str_central(), timeout=15)
        c.autocommit = False
        cur = c.cursor()
        cur.execute("""
            UPDATE APP_DWH
            SET serveur_optiboard  = '.',
                base_optiboard     = 'OptiBoard_cltKASOFT',
                user_optiboard     = '',
                password_optiboard = '',
                actif = 1
            WHERE code = 'KASOFT'
        """)
        rows = cur.rowcount
        c.commit()
        ok(f"APP_DWH KASOFT mis a jour ({rows} ligne(s))")
        c.close()
    except Exception as e:
        err(f"Mise a jour APP_DWH : {e}")

    # ── ETAPE 6 : Mettre a jour APP_ClientDB ─────────────────────────────────
    print(f"\n=== ETAPE 6 : Mise a jour APP_ClientDB ===")
    try:
        c = pyodbc.connect(conn_str_central(), timeout=15)
        c.autocommit = False
        cur = c.cursor()
        # Verifier si la ligne existe
        cur.execute("SELECT COUNT(*) FROM APP_ClientDB WHERE dwh_code='KASOFT'")
        exists = cur.fetchone()[0] > 0
        if exists:
            cur.execute("""
                UPDATE APP_ClientDB
                SET db_name='OptiBoard_cltKASOFT', db_server='.', db_user=NULL, db_password=NULL
                WHERE dwh_code='KASOFT'
            """)
        else:
            cur.execute("""
                INSERT INTO APP_ClientDB (dwh_code, db_name, db_server)
                VALUES ('KASOFT', 'OptiBoard_cltKASOFT', '.')
            """)
        c.commit()
        ok(f"APP_ClientDB KASOFT {'mis a jour' if exists else 'insere'}")
        c.close()
    except Exception as e:
        err(f"APP_ClientDB : {e}")

    # ── ETAPE 7 : Test connexion finale ───────────────────────────────────────
    print(f"\n=== ETAPE 7 : Test connexion finale (comme master_publish) ===")
    try:
        c = pyodbc.connect(conn_str_local(CLIENT_DB), timeout=10)
        c.close()
        ok(f"Connexion a {CLIENT_DB} sur {LOCAL_SERVER} : SUCCES")
        print("\n=> La publication vers Kasoft devrait maintenant fonctionner.")
    except Exception as e:
        err(f"Test final echoue : {e}")

if __name__ == "__main__":
    main()
