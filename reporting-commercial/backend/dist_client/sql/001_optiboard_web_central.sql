-- =====================================================
-- Script d'initialisation - BASE CENTRALE
-- Base: OptiBoard_SaaS
-- Architecture: Multi-tenant SaaS
-- =====================================================

USE master;
GO

-- Creer la base si elle n'existe pas
IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'OptiBoard_SaaS')
BEGIN
    CREATE DATABASE OptiBoard_SaaS;
    PRINT 'Base OptiBoard_SaaS creee avec succes';
END
GO

USE OptiBoard_SaaS;
GO

-- =====================================================
-- SECTION 1: GESTION DES CLIENTS (DWH)
-- =====================================================

-- ===================== APP_DWH (Clients) =====================
-- Table principale des clients/tenants
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_DWH' AND xtype='U')
CREATE TABLE APP_DWH (
    id INT IDENTITY(1,1) PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,              -- Ex: DWH_ALBOUGHAZE
    nom NVARCHAR(200) NOT NULL,                    -- Ex: Groupe Alboughaze
    raison_sociale NVARCHAR(300),                  -- Raison sociale complete
    adresse NVARCHAR(500),                         -- Adresse du client
    ville NVARCHAR(100),
    pays NVARCHAR(100) DEFAULT 'Maroc',
    telephone VARCHAR(50),
    email VARCHAR(200),
    logo_url NVARCHAR(500),                        -- URL du logo client
    -- Connexion a la base DWH du client
    serveur_dwh VARCHAR(200) NOT NULL,             -- Ex: sql.client1.com
    base_dwh VARCHAR(100) NOT NULL,                -- Ex: DWH_Alboughaze
    user_dwh VARCHAR(100) NOT NULL,
    password_dwh VARCHAR(200) NOT NULL,
    -- Parametres
    actif BIT DEFAULT 1,
    date_creation DATETIME DEFAULT GETDATE(),
    date_modification DATETIME DEFAULT GETDATE(),
    created_by INT NULL
);
GO

-- ===================== APP_DWH_Sources (Bases Sage par DWH) =====================
-- Chaque client DWH peut avoir plusieurs bases Sage
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_DWH_Sources' AND xtype='U')
CREATE TABLE APP_DWH_Sources (
    id INT IDENTITY(1,1) PRIMARY KEY,
    dwh_code VARCHAR(50) NOT NULL,                 -- FK vers APP_DWH
    code_societe VARCHAR(50) NOT NULL,             -- Ex: BIJOU, DIAMOND
    nom_societe NVARCHAR(200) NOT NULL,            -- Ex: Bijou Sanitaire
    -- Connexion a la base Sage source
    serveur_sage VARCHAR(200) NOT NULL,
    base_sage VARCHAR(100) NOT NULL,
    user_sage VARCHAR(100) NOT NULL,
    password_sage VARCHAR(200) NOT NULL,
    -- ETL Config
    etl_enabled BIT DEFAULT 1,
    etl_mode VARCHAR(20) DEFAULT 'incremental',    -- incremental, full
    etl_schedule VARCHAR(50) DEFAULT '*/15 * * * *', -- Cron expression
    last_sync DATETIME NULL,
    last_sync_status VARCHAR(20) NULL,             -- success, error, running
    last_sync_message NVARCHAR(MAX) NULL,
    -- Parametres
    actif BIT DEFAULT 1,
    date_creation DATETIME DEFAULT GETDATE(),
    CONSTRAINT FK_DWH_Sources_DWH FOREIGN KEY (dwh_code) REFERENCES APP_DWH(code) ON DELETE CASCADE,
    CONSTRAINT UQ_DWH_Source UNIQUE (dwh_code, code_societe)
);
GO

-- =====================================================
-- SECTION 2: GESTION DES UTILISATEURS
-- =====================================================

-- ===================== APP_Users =====================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Users' AND xtype='U')
CREATE TABLE APP_Users (
    id INT IDENTITY(1,1) PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(64) NOT NULL,
    nom NVARCHAR(100) NOT NULL,
    prenom NVARCHAR(100) NOT NULL,
    email VARCHAR(200),
    telephone VARCHAR(50),
    fonction NVARCHAR(100),                        -- Ex: Directeur Commercial
    role_global VARCHAR(20) DEFAULT 'user',        -- superadmin, admin, user
    actif BIT DEFAULT 1,
    date_creation DATETIME DEFAULT GETDATE(),
    derniere_connexion DATETIME,
    avatar_url NVARCHAR(500)
);
GO

-- ===================== APP_UserDWH (Niveau 1: Acces DWH) =====================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_UserDWH' AND xtype='U')
CREATE TABLE APP_UserDWH (
    id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NOT NULL,
    dwh_code VARCHAR(50) NOT NULL,
    role_dwh VARCHAR(30) DEFAULT 'user',           -- admin_client, manager, user, viewer
    is_default BIT DEFAULT 0,                      -- DWH par defaut a la connexion
    date_creation DATETIME DEFAULT GETDATE(),
    CONSTRAINT FK_UserDWH_User FOREIGN KEY (user_id) REFERENCES APP_Users(id) ON DELETE CASCADE,
    CONSTRAINT FK_UserDWH_DWH FOREIGN KEY (dwh_code) REFERENCES APP_DWH(code) ON DELETE CASCADE,
    CONSTRAINT UQ_UserDWH UNIQUE (user_id, dwh_code)
);
GO

-- ===================== APP_UserSocietes (Niveau 2: Acces Societes Sage) =====================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_UserSocietes' AND xtype='U')
CREATE TABLE APP_UserSocietes (
    id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NOT NULL,
    dwh_code VARCHAR(50) NOT NULL,
    societe_code VARCHAR(50) NOT NULL,
    -- Permissions granulaires
    can_view BIT DEFAULT 1,
    can_export BIT DEFAULT 1,
    can_edit BIT DEFAULT 0,
    date_creation DATETIME DEFAULT GETDATE(),
    CONSTRAINT FK_UserSocietes_User FOREIGN KEY (user_id) REFERENCES APP_Users(id) ON DELETE CASCADE,
    CONSTRAINT UQ_UserSociete UNIQUE (user_id, dwh_code, societe_code)
);
GO

-- ===================== APP_UserPages =====================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_UserPages' AND xtype='U')
CREATE TABLE APP_UserPages (
    id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NOT NULL,
    page_code VARCHAR(50) NOT NULL,
    CONSTRAINT FK_UserPages_User FOREIGN KEY (user_id) REFERENCES APP_Users(id) ON DELETE CASCADE
);
GO

-- ===================== APP_UserMenus =====================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_UserMenus' AND xtype='U')
CREATE TABLE APP_UserMenus (
    id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NOT NULL,
    menu_id INT NOT NULL,
    can_view BIT DEFAULT 1,
    can_export BIT DEFAULT 1,
    CONSTRAINT FK_UserMenus_User FOREIGN KEY (user_id) REFERENCES APP_Users(id) ON DELETE CASCADE
);
GO

-- =====================================================
-- SECTION 3: TEMPLATES GLOBAUX (Plateforme)
-- =====================================================

-- ===================== APP_DataSources_Templates =====================
-- Templates de sources de donnees reutilisables par tous les DWH
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_DataSources_Templates' AND xtype='U')
CREATE TABLE APP_DataSources_Templates (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nom NVARCHAR(200) NOT NULL,
    code VARCHAR(100) UNIQUE NOT NULL,             -- Ex: DS_VENTES_PAR_CLIENT
    type VARCHAR(50) NOT NULL DEFAULT 'query',     -- query, stored_procedure
    category VARCHAR(50),                          -- ventes, stocks, recouvrement, rh
    description NVARCHAR(500),
    query_template NVARCHAR(MAX),                  -- SQL avec placeholders @param
    parameters NVARCHAR(MAX),                      -- JSON definition des parametres
    is_system BIT DEFAULT 1,                       -- Non modifiable par clients
    actif BIT DEFAULT 1,
    date_creation DATETIME DEFAULT GETDATE(),
    date_modification DATETIME DEFAULT GETDATE()
);
GO

-- ===================== APP_Dashboards_Templates =====================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Dashboards_Templates' AND xtype='U')
CREATE TABLE APP_Dashboards_Templates (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nom NVARCHAR(200) NOT NULL,
    code VARCHAR(100) UNIQUE NOT NULL,
    description NVARCHAR(500),
    config NVARCHAR(MAX),
    widgets NVARCHAR(MAX),                         -- JSON des widgets
    category VARCHAR(50),
    preview_image NVARCHAR(500),
    is_system BIT DEFAULT 1,
    actif BIT DEFAULT 1,
    date_creation DATETIME DEFAULT GETDATE()
);
GO

-- ===================== APP_Menus_Templates =====================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Menus_Templates' AND xtype='U')
CREATE TABLE APP_Menus_Templates (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nom NVARCHAR(100) NOT NULL,
    code VARCHAR(100) NOT NULL,
    icon VARCHAR(50),
    url VARCHAR(200),
    parent_code VARCHAR(100) NULL,
    ordre INT DEFAULT 0,
    type VARCHAR(20) DEFAULT 'link',               -- link, folder, dashboard, gridview, pivot
    target_type VARCHAR(50) NULL,                  -- dashboard, gridview, pivot
    target_code VARCHAR(100) NULL,
    is_system BIT DEFAULT 1,
    actif BIT DEFAULT 1,
    date_creation DATETIME DEFAULT GETDATE()
);
GO

-- ===================== APP_GridViews_Templates =====================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_GridViews_Templates' AND xtype='U')
CREATE TABLE APP_GridViews_Templates (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nom NVARCHAR(200) NOT NULL,
    code VARCHAR(100) UNIQUE NOT NULL,
    description NVARCHAR(500),
    datasource_code VARCHAR(100),                  -- Reference vers APP_DataSources_Templates
    columns_config NVARCHAR(MAX),
    features NVARCHAR(MAX),
    is_system BIT DEFAULT 1,
    actif BIT DEFAULT 1,
    date_creation DATETIME DEFAULT GETDATE()
);
GO

-- ===================== APP_Pivots_Templates =====================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Pivots_Templates' AND xtype='U')
CREATE TABLE APP_Pivots_Templates (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nom NVARCHAR(200) NOT NULL,
    code VARCHAR(100) UNIQUE NOT NULL,
    description NVARCHAR(500),
    datasource_code VARCHAR(100),
    pivot_config NVARCHAR(MAX),
    is_system BIT DEFAULT 1,
    actif BIT DEFAULT 1,
    date_creation DATETIME DEFAULT GETDATE()
);
GO

-- ===================== APP_WidgetTemplates =====================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_WidgetTemplates' AND xtype='U')
CREATE TABLE APP_WidgetTemplates (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nom NVARCHAR(200) NOT NULL,
    code VARCHAR(100) UNIQUE NOT NULL,
    type VARCHAR(50) NOT NULL,                     -- kpi, chart, table, gauge
    config NVARCHAR(MAX),
    preview_image NVARCHAR(500),
    description NVARCHAR(500),
    category VARCHAR(50),
    is_system BIT DEFAULT 1,
    actif BIT DEFAULT 1,
    date_creation DATETIME DEFAULT GETDATE()
);
GO

-- =====================================================
-- SECTION 4: CONFIGURATION GLOBALE
-- =====================================================

-- ===================== APP_EmailConfig =====================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_EmailConfig' AND xtype='U')
CREATE TABLE APP_EmailConfig (
    id INT IDENTITY(1,1) PRIMARY KEY,
    dwh_code VARCHAR(50) NULL,                     -- NULL = config globale
    smtp_server VARCHAR(200),
    smtp_port INT DEFAULT 587,
    smtp_username VARCHAR(200),
    smtp_password VARCHAR(200),
    from_email VARCHAR(200),
    from_name NVARCHAR(100),
    use_tls BIT DEFAULT 1,
    actif BIT DEFAULT 1,
    date_modification DATETIME DEFAULT GETDATE(),
    CONSTRAINT FK_EmailConfig_DWH FOREIGN KEY (dwh_code) REFERENCES APP_DWH(code) ON DELETE CASCADE
);
GO

-- ===================== APP_Settings =====================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Settings' AND xtype='U')
CREATE TABLE APP_Settings (
    id INT IDENTITY(1,1) PRIMARY KEY,
    dwh_code VARCHAR(50) NULL,                     -- NULL = setting global
    setting_key VARCHAR(100) NOT NULL,
    setting_value NVARCHAR(MAX),
    setting_type VARCHAR(20) DEFAULT 'string',     -- string, int, bool, json
    description NVARCHAR(500),
    date_modification DATETIME DEFAULT GETDATE(),
    CONSTRAINT FK_Settings_DWH FOREIGN KEY (dwh_code) REFERENCES APP_DWH(code) ON DELETE CASCADE
);
GO

-- =====================================================
-- SECTION 5: AUDIT & LOGS
-- =====================================================

-- ===================== APP_AuditLog =====================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_AuditLog' AND xtype='U')
CREATE TABLE APP_AuditLog (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NULL,
    dwh_code VARCHAR(50) NULL,
    action VARCHAR(50) NOT NULL,                   -- login, logout, view, export, edit, delete
    entity_type VARCHAR(50),                       -- user, dashboard, report, etc.
    entity_id INT NULL,
    details NVARCHAR(MAX),                         -- JSON details
    ip_address VARCHAR(50),
    user_agent NVARCHAR(500),
    date_action DATETIME DEFAULT GETDATE()
);
GO

-- =====================================================
-- SECTION 6: INDEX POUR OPTIMISATION
-- =====================================================

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_APP_DWH_code')
    CREATE INDEX IX_APP_DWH_code ON APP_DWH(code);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_APP_DWH_actif')
    CREATE INDEX IX_APP_DWH_actif ON APP_DWH(actif);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_APP_DWH_Sources_dwh_code')
    CREATE INDEX IX_APP_DWH_Sources_dwh_code ON APP_DWH_Sources(dwh_code);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_APP_UserDWH_user_id')
    CREATE INDEX IX_APP_UserDWH_user_id ON APP_UserDWH(user_id);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_APP_UserDWH_dwh_code')
    CREATE INDEX IX_APP_UserDWH_dwh_code ON APP_UserDWH(dwh_code);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_APP_UserSocietes_user_id')
    CREATE INDEX IX_APP_UserSocietes_user_id ON APP_UserSocietes(user_id);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_APP_UserSocietes_dwh_code')
    CREATE INDEX IX_APP_UserSocietes_dwh_code ON APP_UserSocietes(dwh_code);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_APP_UserPages_user_id')
    CREATE INDEX IX_APP_UserPages_user_id ON APP_UserPages(user_id);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_APP_AuditLog_user_id')
    CREATE INDEX IX_APP_AuditLog_user_id ON APP_AuditLog(user_id);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_APP_AuditLog_dwh_code')
    CREATE INDEX IX_APP_AuditLog_dwh_code ON APP_AuditLog(dwh_code);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_APP_AuditLog_date')
    CREATE INDEX IX_APP_AuditLog_date ON APP_AuditLog(date_action);
GO

-- =====================================================
-- SECTION 7: DONNEES INITIALES
-- =====================================================

-- Utilisateur SuperAdmin
IF NOT EXISTS (SELECT * FROM APP_Users WHERE username = 'superadmin')
BEGIN
    INSERT INTO APP_Users (username, password_hash, nom, prenom, email, role_global, actif)
    VALUES ('superadmin', '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918', 'Super', 'Admin', 'superadmin@optiboard.local', 'superadmin', 1);

    DECLARE @superadmin_id INT = SCOPE_IDENTITY();

    -- Acces a toutes les pages
    INSERT INTO APP_UserPages (user_id, page_code) VALUES (@superadmin_id, 'dashboard');
    INSERT INTO APP_UserPages (user_id, page_code) VALUES (@superadmin_id, 'ventes');
    INSERT INTO APP_UserPages (user_id, page_code) VALUES (@superadmin_id, 'stocks');
    INSERT INTO APP_UserPages (user_id, page_code) VALUES (@superadmin_id, 'recouvrement');
    INSERT INTO APP_UserPages (user_id, page_code) VALUES (@superadmin_id, 'admin');
    INSERT INTO APP_UserPages (user_id, page_code) VALUES (@superadmin_id, 'users');
    INSERT INTO APP_UserPages (user_id, page_code) VALUES (@superadmin_id, 'dwh_management');
    INSERT INTO APP_UserPages (user_id, page_code) VALUES (@superadmin_id, 'etl_admin');
END
GO

-- Settings par defaut
IF NOT EXISTS (SELECT * FROM APP_Settings WHERE setting_key = 'app_name' AND dwh_code IS NULL)
BEGIN
    INSERT INTO APP_Settings (dwh_code, setting_key, setting_value, setting_type, description)
    VALUES (NULL, 'app_name', 'OptiBoard', 'string', 'Nom de l''application');

    INSERT INTO APP_Settings (dwh_code, setting_key, setting_value, setting_type, description)
    VALUES (NULL, 'cache_ttl', '300', 'int', 'Duree du cache en secondes');

    INSERT INTO APP_Settings (dwh_code, setting_key, setting_value, setting_type, description)
    VALUES (NULL, 'max_rows', '10000', 'int', 'Nombre max de lignes par requete');

    INSERT INTO APP_Settings (dwh_code, setting_key, setting_value, setting_type, description)
    VALUES (NULL, 'query_timeout', '30', 'int', 'Timeout des requetes en secondes');
END
GO

PRINT '=====================================================';
PRINT 'Base OptiBoard_SaaS initialisee avec succes!';
PRINT 'Tables creees: APP_DWH, APP_DWH_Sources, APP_Users,';
PRINT '               APP_UserDWH, APP_UserSocietes, etc.';
PRINT 'SuperAdmin cree (mot de passe: admin)';
PRINT '=====================================================';
