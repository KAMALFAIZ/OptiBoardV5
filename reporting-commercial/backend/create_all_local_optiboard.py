"""
CREATION LOCALE - OptiBoard pour tous les DWH avec serveur local
Tourne sur la machine de l'utilisateur => localhost = machine locale
"""
import pyodbc, sys

# Connexion centrale (pour lire APP_DWH)
CENTRAL = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019;TrustServerCertificate=yes;"

# Connexion locale (pour créer les bases)
LOCAL_SA_USER = "sa"
LOCAL_SA_PWD  = "SQL@2019"

LOCAL_SERVERS = {'.', 'localhost', '127.0.0.1', '(local)'}

def is_local(srv):
    if not srv: return True   # NULL = local par défaut
    s = srv.strip().lower()
    return s in LOCAL_SERVERS or s.startswith('.\\') or s.startswith('localhost\\')

def local_conn(db="master"):
    return f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER=.;DATABASE={db};UID={LOCAL_SA_USER};PWD={LOCAL_SA_PWD};TrustServerCertificate=yes;"

# Tables essentielles
TABLES_SQL = [
"""IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Users' AND xtype='U')
CREATE TABLE APP_Users (
    id INT IDENTITY(1,1) PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255), nom NVARCHAR(100), prenom NVARCHAR(100),
    email VARCHAR(200), role_dwh VARCHAR(50) DEFAULT 'user',
    actif BIT DEFAULT 1, date_creation DATETIME DEFAULT GETDATE())""",

"""IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_UserPages' AND xtype='U')
CREATE TABLE APP_UserPages (
    id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NOT NULL, page_code VARCHAR(50) NOT NULL)""",

"""IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_UserMenus' AND xtype='U')
CREATE TABLE APP_UserMenus (
    id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NOT NULL, menu_id INT NOT NULL,
    can_view BIT DEFAULT 1, can_export BIT DEFAULT 1)""",

"""IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Dashboards' AND xtype='U')
CREATE TABLE APP_Dashboards (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nom NVARCHAR(200) NOT NULL, code VARCHAR(100),
    description NVARCHAR(500), config NVARCHAR(MAX), widgets NVARCHAR(MAX),
    is_public BIT DEFAULT 0, is_custom BIT DEFAULT 0, is_customized BIT DEFAULT 0,
    actif BIT DEFAULT 1, date_creation DATETIME DEFAULT GETDATE(),
    date_modification DATETIME DEFAULT GETDATE())""",

"""IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_DataSources' AND xtype='U')
CREATE TABLE APP_DataSources (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nom NVARCHAR(200) NOT NULL, code VARCHAR(100),
    type VARCHAR(50) DEFAULT 'query', query_template NVARCHAR(MAX),
    parameters NVARCHAR(MAX), description NVARCHAR(500),
    is_custom BIT DEFAULT 0, is_customized BIT DEFAULT 0,
    date_creation DATETIME DEFAULT GETDATE())""",

"""IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_GridViews' AND xtype='U')
CREATE TABLE APP_GridViews (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nom NVARCHAR(200) NOT NULL, code VARCHAR(100),
    description NVARCHAR(500), query_template NVARCHAR(MAX),
    columns_config NVARCHAR(MAX), parameters NVARCHAR(MAX), features NVARCHAR(MAX),
    is_custom BIT DEFAULT 0, is_customized BIT DEFAULT 0,
    actif BIT DEFAULT 1, date_creation DATETIME DEFAULT GETDATE(),
    date_modification DATETIME DEFAULT GETDATE())""",

"""IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Pivots_V2' AND xtype='U')
CREATE TABLE APP_Pivots_V2 (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nom NVARCHAR(200) NOT NULL, code VARCHAR(100),
    data_source_code VARCHAR(100), rows_config NVARCHAR(MAX),
    columns_config NVARCHAR(MAX), filters_config NVARCHAR(MAX),
    values_config NVARCHAR(MAX), formatting_rules NVARCHAR(MAX),
    is_custom BIT DEFAULT 0, is_customized BIT DEFAULT 0,
    actif BIT DEFAULT 1, date_creation DATETIME DEFAULT GETDATE(),
    date_modification DATETIME DEFAULT GETDATE())""",

"""IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Pivots_Templates' AND xtype='U')
CREATE TABLE APP_Pivots_Templates (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nom NVARCHAR(200) NOT NULL, code VARCHAR(100),
    type VARCHAR(50) DEFAULT 'pivot',
    data_source_code VARCHAR(100), config NVARCHAR(MAX),
    is_custom BIT DEFAULT 0, is_customized BIT DEFAULT 0,
    actif BIT DEFAULT 1, date_creation DATETIME DEFAULT GETDATE(),
    date_modification DATETIME DEFAULT GETDATE())""",

"""IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Menus' AND xtype='U')
CREATE TABLE APP_Menus (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nom NVARCHAR(100) NOT NULL, code VARCHAR(100), icon VARCHAR(50),
    url VARCHAR(200), parent_id INT, parent_code VARCHAR(100),
    ordre INT DEFAULT 0, type VARCHAR(20) DEFAULT 'link',
    actif BIT DEFAULT 1, is_custom BIT DEFAULT 0, is_customized BIT DEFAULT 0,
    roles NVARCHAR(200), date_creation DATETIME DEFAULT GETDATE())""",

"""IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Settings' AND xtype='U')
CREATE TABLE APP_Settings (
    id INT IDENTITY(1,1) PRIMARY KEY,
    setting_key VARCHAR(100) NOT NULL, setting_value NVARCHAR(MAX),
    setting_type VARCHAR(20) DEFAULT 'string',
    description NVARCHAR(500), date_modification DATETIME DEFAULT GETDATE())""",

"""IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_EmailConfig' AND xtype='U')
CREATE TABLE APP_EmailConfig (
    id INT IDENTITY(1,1) PRIMARY KEY,
    smtp_server VARCHAR(200), smtp_port INT DEFAULT 587,
    smtp_username VARCHAR(200), smtp_password VARCHAR(200),
    from_email VARCHAR(200), from_name NVARCHAR(100),
    use_ssl BIT DEFAULT 0, use_tls BIT DEFAULT 1,
    actif BIT DEFAULT 1, date_modification DATETIME DEFAULT GETDATE())""",
]

def create_db_and_tables(code, db_name):
    print(f"\n{'─'*50}")
    print(f"  DWH: {code}  →  {db_name}  sur localhost")
    print(f"{'─'*50}")

    # 1. Créer la base
    try:
        c = pyodbc.connect(local_conn("master"), timeout=10, autocommit=True)
        cur = c.cursor()
        cur.execute(f"SELECT COUNT(*) FROM sys.databases WHERE name='{db_name}'")
        exists = cur.fetchone()[0] > 0
        if exists:
            print(f"  [OK]  {db_name} existe déjà")
        else:
            cur.execute(f"CREATE DATABASE [{db_name}]")
            print(f"  [OK]  {db_name} CREEE")
        c.close()
    except Exception as e:
        print(f"  [ERR] Création base : {e}")
        return False

    # 2. Créer les tables
    try:
        c = pyodbc.connect(local_conn(db_name), timeout=30, autocommit=True)
        cur = c.cursor()
        ok = 0
        for sql in TABLES_SQL:
            try:
                cur.execute(sql)
                ok += 1
            except Exception as e2:
                print(f"  [WARN] Table: {e2}")
        print(f"  [OK]  {ok}/{len(TABLES_SQL)} tables initialisées")
        c.close()
    except Exception as e:
        print(f"  [ERR] Tables : {e}")
        return False

    return True

def update_central(code, db_name):
    """Met à jour APP_DWH avec les infos optiboard locales"""
    try:
        c = pyodbc.connect(CENTRAL, timeout=15, autocommit=False)
        cur = c.cursor()
        cur.execute("""
            UPDATE APP_DWH SET
                serveur_optiboard  = '.',
                base_optiboard     = ?,
                user_optiboard     = 'sa',
                password_optiboard = 'SQL@2019'
            WHERE code = ?
        """, (db_name, code))
        c.commit()
        print(f"  [OK]  APP_DWH mis à jour (optiboard=. / {db_name})")
        c.close()
    except Exception as e:
        print(f"  [WARN] APP_DWH update : {e}")

# ── MAIN ──────────────────────────────────────────────────────────────────────
print("\n" + "="*55)
print("  CREATION LOCALE OptiBoard - Machine utilisateur")
print("="*55)

# 1. Lire tous les DWH locaux depuis la centrale
print("\nLecture de APP_DWH...")
try:
    c = pyodbc.connect(CENTRAL, timeout=15)
    cur = c.cursor()
    cur.execute("""
        SELECT code, nom, serveur_dwh, serveur_optiboard, base_optiboard,
               user_dwh, password_dwh
        FROM APP_DWH ORDER BY code
    """)
    dwhs = cur.fetchall()
    c.close()
except Exception as e:
    print(f"Impossible de lire APP_DWH : {e}")
    sys.exit(1)

# 2. Filtrer les DWH à serveur local
local_dwhs = []
for r in dwhs:
    code, nom, srv_dwh, srv_opti, base_opti = r[0], r[1], r[2], r[3], r[4]
    effective_srv = srv_opti or srv_dwh
    if is_local(effective_srv):
        db_name = base_opti or f"OptiBoard_clt{code}"
        local_dwhs.append((code, nom, db_name))

if not local_dwhs:
    print("Aucun DWH avec serveur local trouvé.")
    sys.exit(0)

print(f"\nDWH avec serveur local ({len(local_dwhs)}) :")
for code, nom, db in local_dwhs:
    print(f"  {code} ({nom}) → {db}")

# 3. Test connexion locale
print("\nTest connexion SQL Server local...")
try:
    c = pyodbc.connect(local_conn("master"), timeout=10, autocommit=True)
    c.close()
    print("  [OK]  Connexion locale réussie (sa@localhost)")
except Exception as e:
    print(f"  [ERR] Impossible de se connecter au SQL Server local : {e}")
    sys.exit(1)

# 4. Créer chaque base
results = []
for code, nom, db_name in local_dwhs:
    ok = create_db_and_tables(code, db_name)
    if ok:
        update_central(code, db_name)
    results.append((code, db_name, ok))

# 5. Résumé final
print(f"\n{'='*55}")
print("  RÉSUMÉ")
print(f"{'='*55}")
for code, db, ok in results:
    status = "✅ OK" if ok else "❌ ERREUR"
    print(f"  {status}  {code} → {db}")

# 6. Vérification sur SQL Server local
print("\nBases OptiBoard sur localhost :")
try:
    c = pyodbc.connect(local_conn("master"), timeout=10, autocommit=True)
    cur = c.cursor()
    cur.execute("SELECT name FROM sys.databases WHERE name LIKE 'OptiBoard%' ORDER BY name")
    for r in cur.fetchall():
        print(f"  ✅  {r[0]}")
    c.close()
except Exception as e:
    print(f"Vérification : {e}")

print("\nTerminé.")
