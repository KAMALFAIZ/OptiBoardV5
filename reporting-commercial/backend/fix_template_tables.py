"""
Migration : Creer les tables Templates manquantes dans OptiBoard_SaaS
====================================================================
Cree APP_Pivots_Templates, APP_GridViews_Templates, APP_Dashboards_Templates,
APP_DataSources_Templates et APP_Menus_Templates si elles n'existent pas.
"""

import pyodbc
import sys

# ── Connexion ──────────────────────────────────────────────────────────────────
SERVER   = "kasoft.selfip.net"
DATABASE = "OptiBoard_SaaS"
USER     = "sa"
PASSWORD = "SQL@2019"
DRIVER   = "{ODBC Driver 17 for SQL Server}"

conn_str = (
    f"DRIVER={DRIVER};SERVER={SERVER};DATABASE={DATABASE};"
    f"UID={USER};PWD={PASSWORD};TrustServerCertificate=yes;"
)

# ── DDL ────────────────────────────────────────────────────────────────────────
STATEMENTS = [

    # ── APP_Dashboards_Templates ───────────────────────────────────────────────
    """IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Dashboards_Templates' AND xtype='U')
CREATE TABLE APP_Dashboards_Templates (
    id                INT IDENTITY(1,1) PRIMARY KEY,
    code              VARCHAR(100) UNIQUE NOT NULL,
    nom               NVARCHAR(200) NOT NULL,
    description       NVARCHAR(500),
    config            NVARCHAR(MAX),
    widgets           NVARCHAR(MAX),
    is_public         BIT DEFAULT 1,
    actif             BIT DEFAULT 1,
    date_creation     DATETIME DEFAULT GETDATE(),
    date_modification DATETIME DEFAULT GETDATE()
)""",

    # ── APP_GridViews_Templates ────────────────────────────────────────────────
    """IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_GridViews_Templates' AND xtype='U')
CREATE TABLE APP_GridViews_Templates (
    id                INT IDENTITY(1,1) PRIMARY KEY,
    code              VARCHAR(100) UNIQUE NOT NULL,
    nom               NVARCHAR(200) NOT NULL,
    description       NVARCHAR(500),
    query_template    NVARCHAR(MAX),
    columns_config    NVARCHAR(MAX),
    parameters        NVARCHAR(MAX),
    features          NVARCHAR(MAX),
    actif             BIT DEFAULT 1,
    date_creation     DATETIME DEFAULT GETDATE(),
    date_modification DATETIME DEFAULT GETDATE()
)""",

    # ── APP_Pivots_Templates ───────────────────────────────────────────────────
    """IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Pivots_Templates' AND xtype='U')
CREATE TABLE APP_Pivots_Templates (
    id                INT IDENTITY(1,1) PRIMARY KEY,
    code              VARCHAR(100) UNIQUE NOT NULL,
    nom               NVARCHAR(200) NOT NULL,
    description       NVARCHAR(500),
    data_source_code  VARCHAR(100),
    rows_config       NVARCHAR(MAX),
    columns_config    NVARCHAR(MAX),
    filters_config    NVARCHAR(MAX),
    values_config     NVARCHAR(MAX),
    formatting_rules  NVARCHAR(MAX),
    source_params     NVARCHAR(MAX),
    actif             BIT DEFAULT 1,
    date_creation     DATETIME DEFAULT GETDATE(),
    date_modification DATETIME DEFAULT GETDATE()
)""",

    # ── APP_Menus_Templates ────────────────────────────────────────────────────
    """IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Menus_Templates' AND xtype='U')
CREATE TABLE APP_Menus_Templates (
    id            INT IDENTITY(1,1) PRIMARY KEY,
    code          VARCHAR(100) UNIQUE NOT NULL,
    nom           NVARCHAR(200) NOT NULL,
    icon          VARCHAR(100),
    url           VARCHAR(500),
    parent_code   VARCHAR(100),
    ordre         INT DEFAULT 0,
    type          VARCHAR(50),
    target_id     INT,
    roles         NVARCHAR(MAX),
    actif         BIT DEFAULT 1,
    date_creation DATETIME DEFAULT GETDATE()
)""",

    # ── APP_DataSources_Templates ──────────────────────────────────────────────
    """IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_DataSources_Templates' AND xtype='U')
CREATE TABLE APP_DataSources_Templates (
    id             INT IDENTITY(1,1) PRIMARY KEY,
    code           VARCHAR(100) UNIQUE NOT NULL,
    nom            NVARCHAR(200) NOT NULL,
    type           VARCHAR(50),
    query_template NVARCHAR(MAX),
    parameters     NVARCHAR(MAX),
    description    NVARCHAR(500),
    date_creation  DATETIME DEFAULT GETDATE()
)""",

    # ── Ajouter is_customized dans les tables client si manquant ───────────────
    # (ces colonnes sont utilisees dans master_publish.py)
]

# Colonnes is_customized a ajouter dans les tables client (ici dans le central
# ce n'est pas necessaire, mais on verifie APP_GridViews / APP_Pivots_V2)
ADD_COLUMNS = [
    ("APP_GridViews",  "is_customized", "BIT DEFAULT 0"),
    ("APP_Pivots_V2",  "is_customized", "BIT DEFAULT 0"),
    ("APP_Dashboards", "is_customized", "BIT DEFAULT 0"),
    ("APP_DataSources","is_customized", "BIT DEFAULT 0"),
    ("APP_Menus",      "is_customized", "BIT DEFAULT 0"),
]

# ── Execution ──────────────────────────────────────────────────────────────────
def main():
    print(f"Connexion a {SERVER}/{DATABASE}...")
    try:
        conn = pyodbc.connect(conn_str, timeout=15)
        conn.autocommit = True
        cursor = conn.cursor()
        print("OK Connecte\n")
    except Exception as e:
        print(f"ERREUR Connexion echouee : {e}", file=sys.stderr)
        sys.exit(1)

    created = 0
    for stmt in STATEMENTS:
        table_name = stmt.split("'")[1] if "'" in stmt else "?"
        try:
            cursor.execute(stmt)
            print(f"[OK] {table_name} — OK")
            created += 1
        except Exception as e:
            print(f"[ERR] {table_name} — ERREUR : {e}")

    # Verifier quelles tables existent maintenant
    print("\n-- Tables templates presentes dans OptiBoard_SaaS --")
    templates = [
        "APP_Pivots_Templates",
        "APP_GridViews_Templates",
        "APP_Dashboards_Templates",
        "APP_DataSources_Templates",
        "APP_Menus_Templates",
    ]
    for t in templates:
        cursor.execute("SELECT COUNT(*) FROM sysobjects WHERE name=? AND xtype='U'", (t,))
        exists = cursor.fetchone()[0] == 1
        status = "[OK] EXISTS" if exists else "[ERR] MISSING"
        cursor.execute(f"SELECT COUNT(*) FROM {t}") if exists else None
        count = cursor.fetchone()[0] if exists else 0
        print(f"  {status}  {t}  ({count} lignes)")

    conn.close()
    print(f"\nTermine : {created} table(s) creee(s) / verifiee(s).")


if __name__ == "__main__":
    main()
