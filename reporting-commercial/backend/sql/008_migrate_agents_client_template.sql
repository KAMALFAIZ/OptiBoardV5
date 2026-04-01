-- ============================================================
-- MIGRATION STEP 2 : BASE CLIENT (OptiBoard_cltXXX)
-- ============================================================
-- Remplacer XXX par le code client avant execution
-- Ex: USE OptiBoard_cltALBG;
--
-- Objectif : creer dans la base client toutes les tables
--            necessaires a la gestion autonome des agents ETL.
--
-- Ce script est un TEMPLATE.
-- Le script Python migrate_agents.py l execute automatiquement
-- sur chaque base client avec les bonnes valeurs.
--
-- Tables creees :
--   APP_ETL_Agents         — config complete (credentials Sage inclus)
--   APP_ETL_Agent_Tables   — tables a synchroniser par agent
--   APP_ETL_Agent_Sync_Log — logs locaux de synchronisation
--   APP_ETL_Agent_Societes — societes Sage associees a chaque agent
-- ============================================================

-- REMPLACER XXX par le code client
USE OptiBoard_cltXXX;
GO

PRINT '============================================================';
PRINT ' MIGRATION AGENTS ETL — STEP 2 (BASE CLIENT)';
PRINT ' ' + CONVERT(VARCHAR, GETDATE(), 120);
PRINT '============================================================';
GO

-- ============================================================
-- 1. APP_ETL_Agents — config complete (propriete du client)
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Agents' AND xtype='U')
BEGIN
    CREATE TABLE APP_ETL_Agents (
        id                          INT IDENTITY(1,1) PRIMARY KEY,
        agent_id                    VARCHAR(100) UNIQUE NOT NULL,
        nom                         NVARCHAR(200) NOT NULL,
        description                 NVARCHAR(500),
        -- Connexion Sage (credentials stockes cote client UNIQUEMENT)
        sage_server                 VARCHAR(200) NOT NULL,
        sage_database               VARCHAR(100) NOT NULL,
        sage_username               VARCHAR(100),
        sage_password               VARCHAR(200),
        -- Configuration synchronisation
        sync_interval_secondes      INT DEFAULT 300,
        heartbeat_interval_secondes INT DEFAULT 30,
        batch_size                  INT DEFAULT 10000,
        max_retry_count             INT DEFAULT 3,
        -- Options
        is_active                   BIT DEFAULT 1,
        auto_start                  BIT DEFAULT 1,
        -- Statut local (mis a jour par l agent via heartbeat)
        statut                      VARCHAR(20) DEFAULT 'inactif'
                                    CHECK (statut IN ('actif','inactif','erreur','inactif')),
        last_heartbeat              DATETIME,
        last_sync                   DATETIME,
        last_sync_statut            VARCHAR(20),
        last_error                  NVARCHAR(MAX),
        consecutive_failures        INT DEFAULT 0,
        total_syncs                 INT DEFAULT 0,
        total_lignes_sync           BIGINT DEFAULT 0,
        -- Infos machine
        hostname                    VARCHAR(200),
        ip_address                  VARCHAR(50),
        os_info                     VARCHAR(200),
        agent_version               VARCHAR(50),
        -- Auth portail local
        api_key_hash                VARCHAR(64),
        api_key_prefix              VARCHAR(20),
        created_at                  DATETIME DEFAULT GETDATE(),
        updated_at                  DATETIME DEFAULT GETDATE()
    );
    CREATE INDEX IX_ETL_Agents_statut   ON APP_ETL_Agents(statut);
    CREATE INDEX IX_ETL_Agents_active   ON APP_ETL_Agents(is_active);
    PRINT '[OK] APP_ETL_Agents creee';
END
ELSE
    PRINT '[SKIP] APP_ETL_Agents existe deja';
GO

-- ============================================================
-- 2. APP_ETL_Agent_Societes — societes Sage par agent
--    Un agent = 1 serveur Sage = N societes
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Agent_Societes' AND xtype='U')
BEGIN
    CREATE TABLE APP_ETL_Agent_Societes (
        id              INT IDENTITY(1,1) PRIMARY KEY,
        agent_id        VARCHAR(100) NOT NULL REFERENCES APP_ETL_Agents(agent_id) ON DELETE CASCADE,
        societe_code    VARCHAR(50)  NOT NULL,
        societe_nom     NVARCHAR(200),
        base_sage       VARCHAR(100),   -- si differente de la base principale de l agent
        actif           BIT DEFAULT 1,
        date_ajout      DATETIME DEFAULT GETDATE(),
        UNIQUE(agent_id, societe_code)
    );
    PRINT '[OK] APP_ETL_Agent_Societes creee';
END
ELSE
    PRINT '[SKIP] APP_ETL_Agent_Societes existe deja';
GO

-- ============================================================
-- 3. APP_ETL_Agent_Tables — tables a synchroniser par agent
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Agent_Tables' AND xtype='U')
BEGIN
    CREATE TABLE APP_ETL_Agent_Tables (
        id                  INT IDENTITY(1,1) PRIMARY KEY,
        agent_id            VARCHAR(100) NOT NULL REFERENCES APP_ETL_Agents(agent_id) ON DELETE CASCADE,
        table_name          NVARCHAR(100) NOT NULL,
        -- Source Sage
        source_query        NVARCHAR(MAX) NOT NULL,
        societe_code        VARCHAR(50)   NOT NULL DEFAULT '',
        -- Cible DWH
        target_table        NVARCHAR(100) NOT NULL,
        primary_key_columns NVARCHAR(500) NOT NULL,
        -- Synchronisation
        sync_type           VARCHAR(20)   DEFAULT 'incremental',
        timestamp_column    NVARCHAR(100) DEFAULT 'cbModification',
        interval_minutes    INT           DEFAULT 5,
        priority            VARCHAR(20)   DEFAULT 'normal',
        delete_detection    BIT           DEFAULT 0,
        description         NVARCHAR(500),
        -- Heritage depuis catalogue central
        --   is_inherited=1 : vient du catalogue (APP_ETL_Tables_Config central)
        --   is_customized=1: le client a modifie une table heritee
        --   is_inherited=0 : table propre au client (jamais touchee par les syncs)
        is_inherited        BIT DEFAULT 0,
        is_customized       BIT DEFAULT 0,
        -- Statut
        is_enabled          BIT DEFAULT 1,
        last_sync           DATETIME,
        last_sync_status    VARCHAR(20),
        last_sync_rows      INT DEFAULT 0,
        last_error          NVARCHAR(MAX),
        created_at          DATETIME DEFAULT GETDATE(),
        updated_at          DATETIME DEFAULT GETDATE(),
        CONSTRAINT UQ_Agent_Table UNIQUE (agent_id, table_name, societe_code)
    );
    CREATE INDEX IX_AgentTables_agent   ON APP_ETL_Agent_Tables(agent_id);
    CREATE INDEX IX_AgentTables_enabled ON APP_ETL_Agent_Tables(agent_id, is_enabled);
    PRINT '[OK] APP_ETL_Agent_Tables creee';
END
ELSE
BEGIN
    -- Migration colonnes manquantes si table existe deja
    IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_ETL_Agent_Tables') AND name='is_inherited')
        ALTER TABLE APP_ETL_Agent_Tables ADD is_inherited BIT NOT NULL DEFAULT 0;
    IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_ETL_Agent_Tables') AND name='is_customized')
        ALTER TABLE APP_ETL_Agent_Tables ADD is_customized BIT NOT NULL DEFAULT 0;
    IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_ETL_Agent_Tables') AND name='interval_minutes')
        ALTER TABLE APP_ETL_Agent_Tables ADD interval_minutes INT DEFAULT 5;
    IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_ETL_Agent_Tables') AND name='delete_detection')
        ALTER TABLE APP_ETL_Agent_Tables ADD delete_detection BIT DEFAULT 0;
    IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_ETL_Agent_Tables') AND name='description')
        ALTER TABLE APP_ETL_Agent_Tables ADD description NVARCHAR(500);
    PRINT '[SKIP] APP_ETL_Agent_Tables existe — colonnes heritage verifiees';
END
GO

-- ============================================================
-- 4. APP_ETL_Agent_Sync_Log — logs locaux (propres au client)
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Agent_Sync_Log' AND xtype='U')
BEGIN
    CREATE TABLE APP_ETL_Agent_Sync_Log (
        id                  BIGINT IDENTITY(1,1) PRIMARY KEY,
        agent_id            VARCHAR(100) NOT NULL,
        table_name          NVARCHAR(100) NOT NULL,
        societe_code        VARCHAR(50),
        batch_id            NVARCHAR(50),
        -- Temps
        started_at          DATETIME DEFAULT GETDATE(),
        completed_at        DATETIME,
        duration_seconds    FLOAT,
        -- Resultats
        status              VARCHAR(20) DEFAULT 'pending',
        rows_extracted      INT DEFAULT 0,
        rows_inserted       INT DEFAULT 0,
        rows_updated        INT DEFAULT 0,
        rows_failed         INT DEFAULT 0,
        -- Timestamps Sage
        sync_timestamp_start NVARCHAR(50),
        sync_timestamp_end   NVARCHAR(50),
        -- Erreurs
        error_message        NVARCHAR(MAX)
    );
    CREATE INDEX IX_SyncLog_agent     ON APP_ETL_Agent_Sync_Log(agent_id);
    CREATE INDEX IX_SyncLog_started   ON APP_ETL_Agent_Sync_Log(started_at DESC);
    CREATE INDEX IX_SyncLog_status    ON APP_ETL_Agent_Sync_Log(status);
    PRINT '[OK] APP_ETL_Agent_Sync_Log creee';
END
ELSE
    PRINT '[SKIP] APP_ETL_Agent_Sync_Log existe deja';
GO

-- ============================================================
-- 5. RESUME
-- ============================================================
PRINT '';
PRINT '============================================================';
PRINT ' STEP 2 TERMINE — BASE CLIENT';
PRINT '------------------------------------------------------------';
PRINT ' Tables creees / verifiees :';
PRINT '   APP_ETL_Agents         (config complete + credentials)';
PRINT '   APP_ETL_Agent_Societes (societes Sage par agent)';
PRINT '   APP_ETL_Agent_Tables   (tables a synchroniser)';
PRINT '   APP_ETL_Agent_Sync_Log (logs locaux)';
PRINT ' Etape suivante :';
PRINT '   Lancer : python migrate_agents.py';
PRINT '   (deplace les donnees centrale → bases clients)';
PRINT '============================================================';
GO
