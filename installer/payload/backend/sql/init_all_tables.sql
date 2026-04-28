-- =====================================================
-- Script d'initialisation de toutes les tables APP
-- Base: OptiBoard_SaaS (OptiBoard_Essaidi)
-- =====================================================

-- ===================== APP_Societes =====================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Societes' AND xtype='U')
CREATE TABLE APP_Societes (
    id INT IDENTITY(1,1) PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    nom NVARCHAR(200) NOT NULL,
    base_donnees VARCHAR(100) NOT NULL,
    serveur VARCHAR(100),
    actif BIT DEFAULT 1,
    date_creation DATETIME DEFAULT GETDATE()
);
GO

-- ===================== APP_Users =====================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Users' AND xtype='U')
CREATE TABLE APP_Users (
    id INT IDENTITY(1,1) PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(64) NOT NULL,
    nom NVARCHAR(100) NOT NULL,
    prenom NVARCHAR(100) NOT NULL,
    email VARCHAR(200),
    role VARCHAR(20) DEFAULT 'user',
    actif BIT DEFAULT 1,
    date_creation DATETIME DEFAULT GETDATE(),
    derniere_connexion DATETIME
);
GO

-- ===================== APP_UserSocietes =====================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_UserSocietes' AND xtype='U')
CREATE TABLE APP_UserSocietes (
    id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NOT NULL,
    societe_code VARCHAR(50) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES APP_Users(id) ON DELETE CASCADE
);
GO

-- ===================== APP_UserPages =====================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_UserPages' AND xtype='U')
CREATE TABLE APP_UserPages (
    id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NOT NULL,
    page_code VARCHAR(50) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES APP_Users(id) ON DELETE CASCADE
);
GO

-- ===================== APP_DWH =====================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_DWH' AND xtype='U')
CREATE TABLE APP_DWH (
    id INT IDENTITY(1,1) PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    nom NVARCHAR(200) NOT NULL,
    serveur VARCHAR(200) NOT NULL,
    base_donnees VARCHAR(100) NOT NULL,
    username VARCHAR(100) NOT NULL,
    password VARCHAR(200) NOT NULL,
    description NVARCHAR(500),
    actif BIT DEFAULT 1,
    date_creation DATETIME DEFAULT GETDATE()
);
GO

-- ===================== APP_UserDWH =====================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_UserDWH' AND xtype='U')
CREATE TABLE APP_UserDWH (
    id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NOT NULL,
    dwh_code VARCHAR(50) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES APP_Users(id) ON DELETE CASCADE
);
GO

-- ===================== APP_Dashboards =====================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Dashboards' AND xtype='U')
CREATE TABLE APP_Dashboards (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nom NVARCHAR(200) NOT NULL,
    description NVARCHAR(500),
    config NVARCHAR(MAX),
    widgets NVARCHAR(MAX),
    actif BIT DEFAULT 1,
    date_creation DATETIME DEFAULT GETDATE(),
    date_modification DATETIME DEFAULT GETDATE()
);
GO

-- ===================== APP_DataSources =====================
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
GO

-- ===================== APP_GridViews =====================
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
GO

-- ===================== APP_Pivots =====================
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
GO

-- ===================== APP_Menus =====================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Menus' AND xtype='U')
CREATE TABLE APP_Menus (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nom NVARCHAR(100) NOT NULL,
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
GO

-- ===================== APP_ReportHistory =====================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ReportHistory' AND xtype='U')
CREATE TABLE APP_ReportHistory (
    id INT IDENTITY(1,1) PRIMARY KEY,
    report_name NVARCHAR(200) NOT NULL,
    report_type VARCHAR(50),
    parameters NVARCHAR(MAX),
    file_path NVARCHAR(500),
    status VARCHAR(20) DEFAULT 'pending',
    error_message NVARCHAR(MAX),
    created_by INT,
    date_creation DATETIME DEFAULT GETDATE(),
    date_completion DATETIME
);
GO

-- ===================== APP_ReportSchedules =====================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ReportSchedules' AND xtype='U')
CREATE TABLE APP_ReportSchedules (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nom NVARCHAR(200) NOT NULL,
    description NVARCHAR(500),
    report_type VARCHAR(50) NOT NULL,
    report_config NVARCHAR(MAX),
    schedule_type VARCHAR(20) NOT NULL,
    schedule_config NVARCHAR(MAX),
    email_recipients NVARCHAR(MAX),
    email_subject NVARCHAR(200),
    email_body NVARCHAR(MAX),
    actif BIT DEFAULT 1,
    last_run DATETIME,
    next_run DATETIME,
    created_by INT,
    date_creation DATETIME DEFAULT GETDATE()
);
GO

-- ===================== APP_EmailConfig =====================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_EmailConfig' AND xtype='U')
CREATE TABLE APP_EmailConfig (
    id INT IDENTITY(1,1) PRIMARY KEY,
    smtp_server VARCHAR(200),
    smtp_port INT DEFAULT 587,
    smtp_username VARCHAR(200),
    smtp_password VARCHAR(200),
    from_email VARCHAR(200),
    from_name NVARCHAR(100),
    use_tls BIT DEFAULT 1,
    actif BIT DEFAULT 1,
    date_modification DATETIME DEFAULT GETDATE()
);
GO

-- ===================== APP_WidgetTemplates =====================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_WidgetTemplates' AND xtype='U')
CREATE TABLE APP_WidgetTemplates (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nom NVARCHAR(200) NOT NULL,
    type VARCHAR(50) NOT NULL,
    config NVARCHAR(MAX),
    preview_image NVARCHAR(500),
    description NVARCHAR(500),
    actif BIT DEFAULT 1,
    date_creation DATETIME DEFAULT GETDATE()
);
GO

-- =====================================================
-- INDEX POUR OPTIMISATION
-- =====================================================
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_APP_UserSocietes_user_id')
    CREATE INDEX IX_APP_UserSocietes_user_id ON APP_UserSocietes(user_id);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_APP_UserPages_user_id')
    CREATE INDEX IX_APP_UserPages_user_id ON APP_UserPages(user_id);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_APP_UserDWH_user_id')
    CREATE INDEX IX_APP_UserDWH_user_id ON APP_UserDWH(user_id);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_APP_UserDWH_dwh_code')
    CREATE INDEX IX_APP_UserDWH_dwh_code ON APP_UserDWH(dwh_code);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_APP_DWH_code')
    CREATE INDEX IX_APP_DWH_code ON APP_DWH(code);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_APP_Menus_parent_id')
    CREATE INDEX IX_APP_Menus_parent_id ON APP_Menus(parent_id);
GO

-- =====================================================
-- UTILISATEUR ADMIN PAR DEFAUT
-- Password: admin (SHA256 hash)
-- =====================================================
IF NOT EXISTS (SELECT * FROM APP_Users WHERE username = 'admin')
BEGIN
    INSERT INTO APP_Users (username, password_hash, nom, prenom, email, role, actif)
    VALUES ('admin', '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918', 'Administrateur', 'System', 'admin@optiboard.local', 'admin', 1);

    DECLARE @admin_id INT = SCOPE_IDENTITY();

    -- Donner acces a toutes les pages
    INSERT INTO APP_UserPages (user_id, page_code) VALUES (@admin_id, 'dashboard');
    INSERT INTO APP_UserPages (user_id, page_code) VALUES (@admin_id, 'ventes');
    INSERT INTO APP_UserPages (user_id, page_code) VALUES (@admin_id, 'stocks');
    INSERT INTO APP_UserPages (user_id, page_code) VALUES (@admin_id, 'recouvrement');
    INSERT INTO APP_UserPages (user_id, page_code) VALUES (@admin_id, 'admin');
    INSERT INTO APP_UserPages (user_id, page_code) VALUES (@admin_id, 'users');
END
GO

PRINT '=====================================================';
PRINT 'Toutes les tables APP ont ete creees avec succes!';
PRINT 'Utilisateur admin cree (mot de passe: admin)';
PRINT '=====================================================';
