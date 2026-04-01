-- =====================================================================
-- Migration 007 — Règle 1 : colonne is_customized + Règle 2 : APP_Users
-- À exécuter sur chaque base client OptiBoard_XXX existante
-- =====================================================================
-- Usage :
--   Exécuter sur chaque OptiBoard_XXX (remplacer {CLIENT_DB} par le nom)
--   Ou utiliser le endpoint POST /api/dwh-admin/{code}/sync-data
--   qui applique automatiquement les migrations via CLIENT_OPTIBOARD_TABLES_SQL
-- =====================================================================

-- RÈGLE 1 : Ajouter is_customized sur toutes les tables de config
-- is_customized = 0 : ligne synchronisée depuis Master (sera mise à jour)
-- is_customized = 1 : ligne personnalisée par le client (protégée des syncs)

IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_GridViews') AND name='is_customized')
BEGIN
    ALTER TABLE APP_GridViews ADD is_customized BIT NOT NULL DEFAULT 0;
    PRINT 'APP_GridViews : colonne is_customized ajoutée';
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_Pivots_V2') AND name='is_customized')
BEGIN
    ALTER TABLE APP_Pivots_V2 ADD is_customized BIT NOT NULL DEFAULT 0;
    PRINT 'APP_Pivots_V2 : colonne is_customized ajoutée';
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_Dashboards') AND name='is_customized')
BEGIN
    ALTER TABLE APP_Dashboards ADD is_customized BIT NOT NULL DEFAULT 0;
    PRINT 'APP_Dashboards : colonne is_customized ajoutée';
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_DataSources') AND name='is_customized')
BEGIN
    ALTER TABLE APP_DataSources ADD is_customized BIT NOT NULL DEFAULT 0;
    PRINT 'APP_DataSources : colonne is_customized ajoutée';
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_Menus') AND name='is_customized')
BEGIN
    ALTER TABLE APP_Menus ADD is_customized BIT NOT NULL DEFAULT 0;
    PRINT 'APP_Menus : colonne is_customized ajoutée';
END
GO

-- Colonne `code` si manquante (nécessaire pour l'UPSERT)
IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_GridViews') AND name='code')
BEGIN
    ALTER TABLE APP_GridViews ADD code VARCHAR(100) NULL;
    PRINT 'APP_GridViews : colonne code ajoutée';
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_Pivots_V2') AND name='code')
BEGIN
    ALTER TABLE APP_Pivots_V2 ADD code VARCHAR(100) NULL;
    PRINT 'APP_Pivots_V2 : colonne code ajoutée';
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_Dashboards') AND name='code')
BEGIN
    ALTER TABLE APP_Dashboards ADD code VARCHAR(100) NULL;
    PRINT 'APP_Dashboards : colonne code ajoutée';
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_DataSources') AND name='code')
BEGIN
    ALTER TABLE APP_DataSources ADD code VARCHAR(100) NULL;
    PRINT 'APP_DataSources : colonne code ajoutée';
END
GO

-- =====================================================================
-- RÈGLE 2 : Table APP_Users dans chaque base client
-- Les utilisateurs du client sont directement dans OptiBoard_XXX
-- =====================================================================

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Users' AND xtype='U')
BEGIN
    CREATE TABLE APP_Users (
        id                  INT IDENTITY(1,1) PRIMARY KEY,
        username            VARCHAR(100) UNIQUE NOT NULL,
        password_hash       VARCHAR(200) NOT NULL,
        nom                 NVARCHAR(200),
        prenom              NVARCHAR(100),
        email               VARCHAR(200),
        role_dwh            VARCHAR(50) DEFAULT 'user',  -- admin_client | user | viewer
        actif               BIT DEFAULT 1,
        derniere_connexion  DATETIME NULL,
        date_creation       DATETIME DEFAULT GETDATE()
    );
    CREATE INDEX IX_CLIENT_Users_username ON APP_Users(username);
    PRINT 'APP_Users créée dans la base client';
END
GO

-- =====================================================================
-- RÈGLE 3 : Vérification d'isolation (pour diagnostic)
-- Aucun impact structurel — juste un check de cohérence
-- =====================================================================

DECLARE @db_name NVARCHAR(128) = DB_NAME();
DECLARE @tables_count INT;
DECLARE @users_count INT;
DECLARE @customized_count INT;

SELECT @tables_count = COUNT(*) FROM sys.tables WHERE is_ms_shipped = 0;
SELECT @users_count = COUNT(*) FROM APP_Users;
SELECT @customized_count =
    (SELECT COUNT(*) FROM APP_GridViews WHERE is_customized = 1) +
    (SELECT COUNT(*) FROM APP_Dashboards WHERE is_customized = 1) +
    (SELECT COUNT(*) FROM APP_Pivots_V2 WHERE is_customized = 1) +
    (SELECT COUNT(*) FROM APP_Menus WHERE is_customized = 1) +
    (SELECT COUNT(*) FROM APP_DataSources WHERE is_customized = 1);

PRINT '=====================================================================';
PRINT 'Migration 007 terminée sur : ' + @db_name;
PRINT '  Tables totales        : ' + CAST(@tables_count AS VARCHAR);
PRINT '  Utilisateurs (Règle 2): ' + CAST(@users_count AS VARCHAR);
PRINT '  Lignes personnalisées : ' + CAST(@customized_count AS VARCHAR);
PRINT '=====================================================================';
GO
