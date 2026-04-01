"""
Script de migration Multi-Tenant
=================================
Migre de l'architecture mono-base (OptiBoard_SaaS) vers multi-base:
  - OptiBoard_SaaS (MASTER) = auth, routage, templates
  - OptiBoard_XXX (CLIENT) = config par client

Usage:
    python -m scripts.migrate_to_multitenant
"""

import pyodbc
import sys
import os
from pathlib import Path

# Ajouter le repertoire parent au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def get_master_connection_string():
    """Lit la config depuis .env pour se connecter a la base MASTER"""
    env_path = Path(__file__).parent.parent / ".env"
    config = {}
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()

    server = config.get('CENTRAL_DB_SERVER', config.get('DB_SERVER', ''))
    database = config.get('CENTRAL_DB_NAME', config.get('DB_NAME', ''))
    user = config.get('CENTRAL_DB_USER', config.get('DB_USER', ''))
    password = config.get('CENTRAL_DB_PASSWORD', config.get('DB_PASSWORD', ''))
    driver = config.get('CENTRAL_DB_DRIVER', config.get('DB_DRIVER', '{ODBC Driver 17 for SQL Server}'))

    return (
        f"DRIVER={driver};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
        f"TrustServerCertificate=yes"
    ), server, user, password, driver


# Tables a creer dans chaque base client OptiBoard_XXX
CLIENT_TABLES_SQL = """
-- =====================================================
-- Tables client OptiBoard_XXX
-- =====================================================

-- Permissions pages par utilisateur
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_UserPages' AND xtype='U')
CREATE TABLE APP_UserPages (
    id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NOT NULL,
    page_code VARCHAR(50) NOT NULL
);

-- Permissions menus par utilisateur
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_UserMenus' AND xtype='U')
CREATE TABLE APP_UserMenus (
    id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NOT NULL,
    menu_id INT NOT NULL,
    can_view BIT DEFAULT 1,
    can_export BIT DEFAULT 1
);

-- Dashboards
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Dashboards' AND xtype='U')
CREATE TABLE APP_Dashboards (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nom NVARCHAR(200) NOT NULL,
    description NVARCHAR(500),
    config NVARCHAR(MAX),
    widgets NVARCHAR(MAX),
    is_public BIT DEFAULT 0,
    created_by INT NULL,
    actif BIT DEFAULT 1,
    date_creation DATETIME DEFAULT GETDATE(),
    date_modification DATETIME DEFAULT GETDATE()
);

-- DataSources custom
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_DataSources' AND xtype='U')
CREATE TABLE APP_DataSources (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nom NVARCHAR(200) NOT NULL,
    type VARCHAR(50) NOT NULL DEFAULT 'query',
    query_template NVARCHAR(MAX),
    parameters NVARCHAR(MAX),
    description NVARCHAR(500),
    date_creation DATETIME DEFAULT GETDATE()
);

-- GridViews
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_GridViews' AND xtype='U')
CREATE TABLE APP_GridViews (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nom NVARCHAR(200) NOT NULL,
    description NVARCHAR(500),
    query_template NVARCHAR(MAX),
    columns_config NVARCHAR(MAX),
    parameters NVARCHAR(MAX),
    features NVARCHAR(MAX),
    actif BIT DEFAULT 1,
    date_creation DATETIME DEFAULT GETDATE(),
    date_modification DATETIME DEFAULT GETDATE()
);

-- GridView User Prefs
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_GridView_User_Prefs' AND xtype='U')
CREATE TABLE APP_GridView_User_Prefs (
    id INT IDENTITY(1,1) PRIMARY KEY,
    gridview_id INT NOT NULL,
    user_id INT NOT NULL,
    columns_config NVARCHAR(MAX),
    date_modification DATETIME DEFAULT GETDATE(),
    CONSTRAINT UQ_GridView_User UNIQUE (gridview_id, user_id)
);

-- Pivots (legacy)
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Pivots' AND xtype='U')
CREATE TABLE APP_Pivots (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nom NVARCHAR(200) NOT NULL,
    description NVARCHAR(500),
    query_template NVARCHAR(MAX),
    pivot_config NVARCHAR(MAX),
    parameters NVARCHAR(MAX),
    actif BIT DEFAULT 1,
    date_creation DATETIME DEFAULT GETDATE(),
    date_modification DATETIME DEFAULT GETDATE()
);

-- Pivots V2
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Pivots_V2' AND xtype='U')
CREATE TABLE APP_Pivots_V2 (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nom NVARCHAR(200) NOT NULL,
    description NVARCHAR(500),
    data_source_id INT NULL,
    data_source_code VARCHAR(100),
    rows_config NVARCHAR(MAX),
    columns_config NVARCHAR(MAX),
    filters_config NVARCHAR(MAX),
    values_config NVARCHAR(MAX),
    show_grand_totals BIT DEFAULT 1,
    show_subtotals BIT DEFAULT 0,
    show_row_percent BIT DEFAULT 0,
    show_col_percent BIT DEFAULT 0,
    show_total_percent BIT DEFAULT 0,
    comparison_mode NVARCHAR(50),
    formatting_rules NVARCHAR(MAX),
    source_params NVARCHAR(MAX),
    is_public BIT DEFAULT 0,
    created_by INT NULL,
    created_at DATETIME DEFAULT GETDATE(),
    updated_at DATETIME DEFAULT GETDATE(),
    grand_total_position NVARCHAR(20) DEFAULT 'bottom',
    subtotal_position NVARCHAR(20) DEFAULT 'bottom',
    show_summary_row BIT DEFAULT 0,
    summary_functions NVARCHAR(MAX),
    window_calculations NVARCHAR(MAX)
);

-- Pivot User Prefs
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Pivot_User_Prefs' AND xtype='U')
CREATE TABLE APP_Pivot_User_Prefs (
    id INT IDENTITY(1,1) PRIMARY KEY,
    pivot_id INT NOT NULL,
    user_id INT NOT NULL,
    custom_config NVARCHAR(MAX),
    date_modification DATETIME DEFAULT GETDATE(),
    CONSTRAINT UQ_Pivot_User UNIQUE (pivot_id, user_id)
);

-- Menus
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Menus' AND xtype='U')
CREATE TABLE APP_Menus (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nom NVARCHAR(100) NOT NULL,
    code VARCHAR(100),
    icon VARCHAR(50),
    url VARCHAR(200),
    parent_id INT NULL,
    ordre INT DEFAULT 0,
    type VARCHAR(20) DEFAULT 'link',
    target_id INT NULL,
    actif BIT DEFAULT 1,
    roles NVARCHAR(200),
    date_creation DATETIME DEFAULT GETDATE()
);

-- Email Config
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

-- Settings
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Settings' AND xtype='U')
CREATE TABLE APP_Settings (
    id INT IDENTITY(1,1) PRIMARY KEY,
    setting_key VARCHAR(100) NOT NULL,
    setting_value NVARCHAR(MAX),
    setting_type VARCHAR(20) DEFAULT 'string',
    description NVARCHAR(500),
    date_modification DATETIME DEFAULT GETDATE()
);

-- Report Schedules
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ReportSchedules' AND xtype='U')
CREATE TABLE APP_ReportSchedules (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nom NVARCHAR(255) NOT NULL,
    description NVARCHAR(MAX),
    report_type NVARCHAR(50) NOT NULL,
    report_id INT,
    export_format NVARCHAR(20) DEFAULT 'excel',
    frequency NVARCHAR(20) NOT NULL,
    schedule_time NVARCHAR(10) DEFAULT '08:00',
    schedule_day INT,
    recipients NVARCHAR(MAX) NOT NULL,
    cc_recipients NVARCHAR(MAX),
    filters NVARCHAR(MAX),
    is_active BIT DEFAULT 1,
    last_run DATETIME,
    next_run DATETIME,
    created_by INT,
    created_at DATETIME DEFAULT GETDATE(),
    updated_at DATETIME DEFAULT GETDATE()
);

-- Report History
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ReportHistory' AND xtype='U')
CREATE TABLE APP_ReportHistory (
    id INT IDENTITY(1,1) PRIMARY KEY,
    schedule_id INT,
    report_name NVARCHAR(255),
    recipients NVARCHAR(MAX),
    status NVARCHAR(20) NOT NULL,
    error_message NVARCHAR(MAX),
    file_path NVARCHAR(500),
    file_size INT,
    sent_at DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (schedule_id) REFERENCES APP_ReportSchedules(id) ON DELETE SET NULL
);

-- Audit Log
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_AuditLog' AND xtype='U')
CREATE TABLE APP_AuditLog (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NULL,
    action VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50),
    entity_id INT NULL,
    details NVARCHAR(MAX),
    ip_address VARCHAR(50),
    user_agent NVARCHAR(500),
    date_action DATETIME DEFAULT GETDATE()
);

-- Index
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_CLIENT_AuditLog_date')
    CREATE INDEX IX_CLIENT_AuditLog_date ON APP_AuditLog(date_action);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_CLIENT_UserPages_user')
    CREATE INDEX IX_CLIENT_UserPages_user ON APP_UserPages(user_id);
"""


def migrate():
    """Execute la migration multi-tenant"""
    print("=" * 60)
    print("  Migration Multi-Tenant OptiBoard")
    print("=" * 60)

    # Connexion a MASTER
    conn_str, server, db_user, db_password, driver = get_master_connection_string()
    print(f"\n[1/5] Connexion a MASTER...")

    try:
        master_conn = pyodbc.connect(conn_str)
        master_cursor = master_conn.cursor()
        print("  OK - Connecte a MASTER")
    except Exception as e:
        print(f"  ERREUR: {e}")
        return False

    # Creer la table APP_ClientDB si elle n'existe pas
    print(f"\n[2/5] Creation de APP_ClientDB dans MASTER...")
    try:
        master_cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ClientDB' AND xtype='U')
            CREATE TABLE APP_ClientDB (
                id INT IDENTITY(1,1) PRIMARY KEY,
                dwh_code VARCHAR(50) UNIQUE NOT NULL,
                db_name NVARCHAR(100) NOT NULL,
                db_server NVARCHAR(200) NULL,
                db_user NVARCHAR(100) NULL,
                db_password NVARCHAR(200) NULL,
                actif BIT DEFAULT 1,
                date_creation DATETIME DEFAULT GETDATE()
            )
        """)
        master_conn.commit()
        print("  OK - Table APP_ClientDB prete")
    except Exception as e:
        print(f"  ERREUR: {e}")
        master_conn.rollback()

    # Lister les clients (DWH)
    print(f"\n[3/5] Lecture des clients DWH...")
    master_cursor.execute("SELECT code, nom FROM APP_DWH WHERE actif = 1 ORDER BY nom")
    clients = master_cursor.fetchall()

    if not clients:
        print("  Aucun client DWH trouve. Rien a migrer.")
        master_cursor.close()
        master_conn.close()
        return True

    print(f"  {len(clients)} client(s) trouve(s):")
    for c in clients:
        print(f"    - {c[0]} ({c[1]})")

    # Pour chaque client, creer la base OptiBoard_XXX
    print(f"\n[4/5] Creation des bases client...")
    server_conn_str = (
        f"DRIVER={driver};"
        f"SERVER={server};"
        f"UID={db_user};"
        f"PWD={db_password};"
        f"TrustServerCertificate=yes"
    )

    for dwh_code, dwh_nom in clients:
        # Determiner le nom de la base client
        # Transformer le code DWH en nom de base: DWH_ESSAIDI -> OptiBoard_ESSAIDI
        client_suffix = dwh_code.replace('DWH_', '').replace('dwh_', '')
        db_name = f"OptiBoard_{client_suffix}"

        print(f"\n  --- Client: {dwh_nom} ({dwh_code}) -> {db_name} ---")

        # Verifier si deja enregistre dans APP_ClientDB
        master_cursor.execute(
            "SELECT COUNT(*) FROM APP_ClientDB WHERE dwh_code = ?",
            (dwh_code,)
        )
        if master_cursor.fetchone()[0] > 0:
            print(f"    Deja enregistre dans APP_ClientDB")
        else:
            # Enregistrer dans APP_ClientDB (NULL = meme serveur/credentials)
            master_cursor.execute(
                "INSERT INTO APP_ClientDB (dwh_code, db_name) VALUES (?, ?)",
                (dwh_code, db_name)
            )
            master_conn.commit()
            print(f"    Enregistre dans APP_ClientDB")

        # Creer la base si elle n'existe pas
        try:
            server_conn = pyodbc.connect(server_conn_str, autocommit=True)
            server_cursor = server_conn.cursor()

            server_cursor.execute(
                "SELECT COUNT(*) FROM sys.databases WHERE name = ?",
                (db_name,)
            )
            if server_cursor.fetchone()[0] == 0:
                server_cursor.execute(f"CREATE DATABASE [{db_name}]")
                print(f"    Base {db_name} creee")
            else:
                print(f"    Base {db_name} existe deja")

            server_cursor.close()
            server_conn.close()
        except Exception as e:
            print(f"    ERREUR creation base: {e}")
            continue

        # Creer les tables dans la base client
        try:
            client_conn_str = (
                f"DRIVER={driver};"
                f"SERVER={server};"
                f"DATABASE={db_name};"
                f"UID={db_user};"
                f"PWD={db_password};"
                f"TrustServerCertificate=yes"
            )
            client_conn = pyodbc.connect(client_conn_str, autocommit=True)
            client_cursor = client_conn.cursor()

            # Executer chaque CREATE TABLE separement avec autocommit
            tables_ok = 0
            for statement in CLIENT_TABLES_SQL.split(';'):
                # Supprimer les lignes de commentaires au debut
                lines = statement.strip().split('\n')
                clean_lines = []
                for line in lines:
                    stripped = line.strip()
                    if stripped and not stripped.startswith('--'):
                        clean_lines.append(line)
                statement = '\n'.join(clean_lines).strip()
                if not statement:
                    continue
                try:
                    client_cursor.execute(statement)
                    if 'CREATE TABLE' in statement.upper():
                        tables_ok += 1
                except Exception as e:
                    if 'already exists' not in str(e).lower():
                        print(f"    Warning: {str(e)[:80]}")

            print(f"    {tables_ok} tables creees dans {db_name}")

            # Migrer les donnees depuis MASTER
            migrate_client_data(master_conn, client_conn, dwh_code, db_name)

            client_cursor.close()
            client_conn.close()
        except Exception as e:
            print(f"    ERREUR tables: {e}")

    # Resume
    print(f"\n[5/5] Migration terminee!")
    print("=" * 60)
    print("  IMPORTANT:")
    print("  - Les bases client OptiBoard_XXX ont ete creees")
    print("  - Les donnees ont ete copiees depuis MASTER")
    print("  - Les tables dans MASTER restent intactes (backup)")
    print("  - Redemarrez le backend pour prendre en compte les changements")
    print("=" * 60)

    master_cursor.close()
    master_conn.close()
    return True


def migrate_client_data(master_conn, client_conn, dwh_code, db_name):
    """Migre les donnees d'un client depuis MASTER vers sa base"""
    master_cursor = master_conn.cursor()
    client_cursor = client_conn.cursor()

    # Trouver les user_ids lies a ce DWH
    master_cursor.execute(
        "SELECT user_id FROM APP_UserDWH WHERE dwh_code = ?",
        (dwh_code,)
    )
    user_ids = [row[0] for row in master_cursor.fetchall()]

    if not user_ids:
        print(f"    Aucun utilisateur lie a {dwh_code}")
        return

    print(f"    {len(user_ids)} utilisateur(s) a migrer")
    placeholders = ','.join(['?' for _ in user_ids])

    # Migrer APP_UserPages
    try:
        master_cursor.execute(
            f"SELECT user_id, page_code FROM APP_UserPages WHERE user_id IN ({placeholders})",
            user_ids
        )
        rows = master_cursor.fetchall()
        for row in rows:
            try:
                client_cursor.execute(
                    "INSERT INTO APP_UserPages (user_id, page_code) VALUES (?, ?)",
                    (row[0], row[1])
                )
            except:
                pass
        client_conn.commit()
        print(f"    APP_UserPages: {len(rows)} entrees")
    except Exception as e:
        print(f"    APP_UserPages ERREUR: {str(e)[:60]}")
        client_conn.rollback()

    # Migrer APP_UserMenus
    try:
        master_cursor.execute(
            f"SELECT user_id, menu_id, can_view, can_export FROM APP_UserMenus WHERE user_id IN ({placeholders})",
            user_ids
        )
        rows = master_cursor.fetchall()
        for row in rows:
            try:
                client_cursor.execute(
                    "INSERT INTO APP_UserMenus (user_id, menu_id, can_view, can_export) VALUES (?, ?, ?, ?)",
                    (row[0], row[1], row[2], row[3])
                )
            except:
                pass
        client_conn.commit()
        print(f"    APP_UserMenus: {len(rows)} entrees")
    except Exception as e:
        print(f"    APP_UserMenus ERREUR: {str(e)[:60]}")
        client_conn.rollback()

    # Migrer APP_Dashboards (crees par les utilisateurs de ce client)
    try:
        master_cursor.execute(
            f"SELECT nom, description, config, widgets, is_public, created_by, actif, date_creation, date_modification FROM APP_Dashboards WHERE created_by IN ({placeholders}) OR created_by IS NULL",
            user_ids
        )
        rows = master_cursor.fetchall()
        for row in rows:
            try:
                client_cursor.execute(
                    "INSERT INTO APP_Dashboards (nom, description, config, widgets, is_public, created_by, actif, date_creation, date_modification) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    row
                )
            except:
                pass
        client_conn.commit()
        print(f"    APP_Dashboards: {len(rows)} entrees")
    except Exception as e:
        print(f"    APP_Dashboards ERREUR: {str(e)[:60]}")
        client_conn.rollback()

    # Migrer APP_GridViews
    try:
        master_cursor.execute(
            "SELECT nom, description, query_template, columns_config, parameters, features, actif, date_creation, date_modification FROM APP_GridViews"
        )
        rows = master_cursor.fetchall()
        for row in rows:
            try:
                client_cursor.execute(
                    "INSERT INTO APP_GridViews (nom, description, query_template, columns_config, parameters, features, actif, date_creation, date_modification) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    row
                )
            except:
                pass
        client_conn.commit()
        print(f"    APP_GridViews: {len(rows)} entrees")
    except Exception as e:
        print(f"    APP_GridViews ERREUR: {str(e)[:60]}")
        client_conn.rollback()

    # Migrer APP_Menus
    try:
        master_cursor.execute(
            "SELECT nom, code, icon, url, parent_id, ordre, type, target_id, actif, roles, date_creation FROM APP_Menus"
        )
        rows = master_cursor.fetchall()
        for row in rows:
            try:
                client_cursor.execute(
                    "INSERT INTO APP_Menus (nom, code, icon, url, parent_id, ordre, type, target_id, actif, roles, date_creation) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    row
                )
            except:
                pass
        client_conn.commit()
        print(f"    APP_Menus: {len(rows)} entrees")
    except Exception as e:
        print(f"    APP_Menus ERREUR: {str(e)[:60]}")
        client_conn.rollback()

    # Migrer APP_Pivots_V2
    try:
        master_cursor.execute(
            "SELECT nom, description, data_source_code, pivot_config, columns_config, values_config, filters_config, chart_config, features, created_by, actif, date_creation, date_modification FROM APP_Pivots_V2"
        )
        rows = master_cursor.fetchall()
        for row in rows:
            try:
                client_cursor.execute(
                    "INSERT INTO APP_Pivots_V2 (nom, description, data_source_code, pivot_config, columns_config, values_config, filters_config, chart_config, features, created_by, actif, date_creation, date_modification) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    row
                )
            except:
                pass
        client_conn.commit()
        print(f"    APP_Pivots_V2: {len(rows)} entrees")
    except Exception as e:
        print(f"    APP_Pivots_V2 ERREUR: {str(e)[:60]}")
        client_conn.rollback()

    # Migrer APP_EmailConfig pour ce DWH
    try:
        master_cursor.execute(
            "SELECT smtp_server, smtp_port, smtp_username, smtp_password, from_email, from_name, use_ssl, use_tls, actif FROM APP_EmailConfig WHERE dwh_code = ? OR dwh_code IS NULL",
            (dwh_code,)
        )
        rows = master_cursor.fetchall()
        for row in rows:
            try:
                client_cursor.execute(
                    "INSERT INTO APP_EmailConfig (smtp_server, smtp_port, smtp_username, smtp_password, from_email, from_name, use_ssl, use_tls, actif) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    row
                )
            except:
                pass
        client_conn.commit()
        print(f"    APP_EmailConfig: {len(rows)} entrees")
    except Exception as e:
        print(f"    APP_EmailConfig ERREUR: {str(e)[:60]}")
        client_conn.rollback()

    # Migrer APP_Settings pour ce DWH
    try:
        master_cursor.execute(
            "SELECT setting_key, setting_value, setting_type, description FROM APP_Settings WHERE dwh_code = ?",
            (dwh_code,)
        )
        rows = master_cursor.fetchall()
        for row in rows:
            try:
                client_cursor.execute(
                    "INSERT INTO APP_Settings (setting_key, setting_value, setting_type, description) VALUES (?, ?, ?, ?)",
                    row
                )
            except:
                pass
        client_conn.commit()
        print(f"    APP_Settings: {len(rows)} entrees")
    except Exception as e:
        print(f"    APP_Settings ERREUR: {str(e)[:60]}")
        client_conn.rollback()

    # Migrer APP_ReportSchedules
    try:
        master_cursor.execute(
            "SELECT nom, description, report_type, report_id, export_format, frequency, schedule_time, schedule_day, recipients, cc_recipients, filters, is_active, last_run, next_run, created_by, created_at, updated_at FROM APP_ReportSchedules"
        )
        rows = master_cursor.fetchall()
        for row in rows:
            try:
                client_cursor.execute(
                    "INSERT INTO APP_ReportSchedules (nom, description, report_type, report_id, export_format, frequency, schedule_time, schedule_day, recipients, cc_recipients, filters, is_active, last_run, next_run, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    row
                )
            except:
                pass
        client_conn.commit()
        print(f"    APP_ReportSchedules: {len(rows)} entrees")
    except Exception as e:
        print(f"    APP_ReportSchedules ERREUR: {str(e)[:60]}")
        client_conn.rollback()


if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
