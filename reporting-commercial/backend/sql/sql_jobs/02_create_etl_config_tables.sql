-- =====================================================================
-- 02_create_etl_config_tables.sql
-- Tables de configuration et suivi ETL
-- Architecture 3 bases : OptiBoard_xxxx + DWH_yyyy + Sage 1..N
-- =====================================================================
-- PARTIE A : ETL_Tables_Config    -> dans OptiBoard_xxxx (config centrale)
-- PARTIE B : SyncControl, ETL_Sources, ETL_Sync_Log, ETL_Alerts -> dans DWH_yyyy
-- =====================================================================
-- VARIABLES A REMPLACER :
--   {OPTIBOARD_DB}  -> nom de votre base OptiBoard (ex: OptiBoard_SaaS)
--   {DWH_NAME}      -> nom de votre base DWH (ex: DWH_Alboughaze)
-- =====================================================================
-- NOTE: Chaque batch inclut son propre USE pour garantir le contexte DB
--       meme si pyodbc ne propage pas le USE entre cursor.execute() calls.
-- =====================================================================

SET NOCOUNT ON;
GO

-- ═══════════════════════════════════════════════════════════════
-- PARTIE A : DANS OPTIBOARD (CONFIG CENTRALE)
-- ═══════════════════════════════════════════════════════════════

-- Batch 1 : DROP ancien ETL_Tables_Config si existe
USE [{OPTIBOARD_DB}];
PRINT '══════════════════════════════════════════════════════════════';
PRINT ' PARTIE A : TABLES CONFIG DANS {OPTIBOARD_DB}';
PRINT '══════════════════════════════════════════════════════════════';
IF EXISTS (SELECT * FROM sys.tables WHERE name = 'ETL_Tables_Config')
BEGIN
    DROP TABLE ETL_Tables_Config;
    PRINT '  -> Ancien ETL_Tables_Config supprime (sera recree)';
END
GO

-- Batch 2 : CREATE TABLE ETL_Tables_Config (schema v2)
USE [{OPTIBOARD_DB}];
CREATE TABLE ETL_Tables_Config (
    config_id            INT IDENTITY(1,1) PRIMARY KEY,
    table_name           NVARCHAR(100) NOT NULL,          -- Nom logique (ex: Collaborateurs)
    source_query         NVARCHAR(MAX) NULL,              -- Requete SELECT brute (sans prefixe DB)
    target_table         NVARCHAR(100) NOT NULL,          -- Table cible DWH
    join_column          NVARCHAR(200) NULL,              -- Colonne PK pour MERGE ON (-> @JoinColumn)
    filter_column        NVARCHAR(100) DEFAULT 'DB',      -- Colonne multi-source (-> @FilterColumn)
    sync_type            NVARCHAR(20) DEFAULT 'full',     -- 'incremental' ou 'full'
    timestamp_column     NVARCHAR(100) NULL,              -- Colonne pour sync incremental (ex: cbModification)
    priority             NVARCHAR(20) DEFAULT 'normal',   -- 'high','normal','low'
    sort_order           INT DEFAULT 0,                   -- Ordre d'execution
    delete_orphans       BIT DEFAULT 0,                   -- Activer detection suppressions
    is_active            BIT DEFAULT 1,
    created_at           DATETIME2 DEFAULT GETDATE(),
    updated_at           DATETIME2 DEFAULT GETDATE(),
    CONSTRAINT UQ_ETL_Tables_Config_Name UNIQUE (table_name)
);
CREATE INDEX IX_ETL_Tables_Config_Active ON ETL_Tables_Config (is_active, sort_order);
PRINT '  V Table ETL_Tables_Config creee dans {OPTIBOARD_DB}';
GO

-- ═══════════════════════════════════════════════════════════════
-- PARTIE B : DANS DWH (BASE CIBLE)
-- ═══════════════════════════════════════════════════════════════

-- Batch 3 : ETL_Sources
USE [{DWH_NAME}];
PRINT '';
PRINT '══════════════════════════════════════════════════════════════';
PRINT ' PARTIE B : TABLES ETL DANS {DWH_NAME}';
PRINT '══════════════════════════════════════════════════════════════';
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'ETL_Sources')
BEGIN
    CREATE TABLE ETL_Sources (
        source_id          INT IDENTITY(1,1) PRIMARY KEY,
        source_code        VARCHAR(50) NOT NULL,             -- Ex: CASHPLUS_2026, BIJOU
        source_caption     NVARCHAR(200) NOT NULL,           -- Ex: GROUPE CASHPLUS
        db_id              INT NOT NULL,                     -- Identifiant numerique unique
        server_name        VARCHAR(200) NOT NULL,            -- Nom/IP du serveur Sage
        database_name      VARCHAR(100) NOT NULL,            -- Nom base Sage
        is_linked_server   BIT DEFAULT 0,                    -- 0=meme serveur, 1=Linked Server
        linked_server_name VARCHAR(200) NULL,                -- Nom du Linked Server (scenario B)
        is_active          BIT DEFAULT 1,
        created_at         DATETIME2 DEFAULT GETDATE(),
        updated_at         DATETIME2 DEFAULT GETDATE(),
        CONSTRAINT UQ_ETL_Sources_Code UNIQUE (source_code)
    );
    CREATE INDEX IX_ETL_Sources_Active ON ETL_Sources (is_active);
    PRINT '  V Table ETL_Sources creee';
END
ELSE
    PRINT '  -> Table ETL_Sources existe deja';
GO

-- Batch 4 : SyncControl
USE [{DWH_NAME}];
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'SyncControl')
BEGIN
    CREATE TABLE SyncControl (
        TableName          NVARCHAR(200) NOT NULL,           -- Ex: CASHPLUS_2026_Collaborateurs
        LastSyncDate       DATETIME NULL,                     -- Watermark pour sync incremental
        TotalInserted      BIGINT DEFAULT 0,
        TotalUpdated       BIGINT DEFAULT 0,
        TotalDeleted       BIGINT DEFAULT 0,
        LastStatus         NVARCHAR(20) NULL,                 -- Success / Error
        LastError          NVARCHAR(MAX) NULL,
        LastSyncDuration   INT NULL,                          -- Duree en secondes
        CONSTRAINT PK_SyncControl PRIMARY KEY (TableName)
    );
    PRINT '  V Table SyncControl creee';
END
ELSE
    PRINT '  -> Table SyncControl existe deja';
GO

-- Batch 5 : ETL_Sync_Log
USE [{DWH_NAME}];
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'ETL_Sync_Log')
BEGIN
    CREATE TABLE ETL_Sync_Log (
        id                BIGINT IDENTITY(1,1) PRIMARY KEY,
        sync_control_name NVARCHAR(200) NOT NULL,            -- Ref vers SyncControl.TableName
        source_code       VARCHAR(50) NULL,                   -- Pour le reporting
        table_name        NVARCHAR(100) NULL,                 -- Pour le reporting
        sync_type         NVARCHAR(20) NULL,                  -- 'full' ou 'incremental'
        started_at        DATETIME2 DEFAULT GETDATE(),
        completed_at      DATETIME2 NULL,
        status            NVARCHAR(20) DEFAULT 'running',     -- running/success/failed
        rows_extracted    INT DEFAULT 0,
        rows_inserted     INT DEFAULT 0,
        rows_updated      INT DEFAULT 0,
        rows_deleted      INT DEFAULT 0,
        duration_seconds  AS DATEDIFF(SECOND, started_at, completed_at),
        error_message     NVARCHAR(MAX) NULL,
        watermark_before  NVARCHAR(100) NULL,
        watermark_after   NVARCHAR(100) NULL
    );
    CREATE INDEX IX_ETL_Sync_Log_SyncControl ON ETL_Sync_Log (sync_control_name, started_at DESC);
    CREATE INDEX IX_ETL_Sync_Log_Status ON ETL_Sync_Log (status);
    CREATE INDEX IX_ETL_Sync_Log_Date ON ETL_Sync_Log (started_at DESC);
    PRINT '  V Table ETL_Sync_Log creee';
END
ELSE
    PRINT '  -> Table ETL_Sync_Log existe deja';
GO

-- Batch 6 : ETL_Alerts
USE [{DWH_NAME}];
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'ETL_Alerts')
BEGIN
    CREATE TABLE ETL_Alerts (
        alert_id          BIGINT IDENTITY(1,1) PRIMARY KEY,
        alert_time        DATETIME2 DEFAULT GETDATE(),
        alert_type        NVARCHAR(50) NOT NULL,              -- SYNC_FAILURE, TIMEOUT, etc.
        severity          NVARCHAR(20) NOT NULL,              -- LOW/MEDIUM/HIGH/CRITICAL
        source_code       VARCHAR(50) NULL,
        table_name        NVARCHAR(100) NULL,
        sync_control_name NVARCHAR(200) NULL,
        message           NVARCHAR(MAX) NOT NULL,
        is_acknowledged   BIT DEFAULT 0,
        acknowledged_at   DATETIME2 NULL,
        acknowledged_by   NVARCHAR(100) NULL
    );
    CREATE INDEX IX_ETL_Alerts_Time ON ETL_Alerts (alert_time DESC);
    CREATE INDEX IX_ETL_Alerts_Unacked ON ETL_Alerts (is_acknowledged) WHERE is_acknowledged = 0;
    PRINT '  V Table ETL_Alerts creee';
END
ELSE
    PRINT '  -> Table ETL_Alerts existe deja';
GO

-- Resume final
USE [{DWH_NAME}];
PRINT '';
PRINT '══════════════════════════════════════════════════════════════';
PRINT ' TABLES DE CONFIGURATION ETL CREEES AVEC SUCCES';
PRINT '══════════════════════════════════════════════════════════════';
PRINT '';
PRINT ' OptiBoard ({OPTIBOARD_DB}) :';
PRINT '   - ETL_Tables_Config  (35 configs tables)';
PRINT '';
PRINT ' DWH ({DWH_NAME}) :';
PRINT '   - ETL_Sources        (registre sources Sage)';
PRINT '   - SyncControl        (watermarks + compteurs)';
PRINT '   - ETL_Sync_Log       (historique syncs)';
PRINT '   - ETL_Alerts         (alertes automatiques)';
PRINT '══════════════════════════════════════════════════════════════';
GO
