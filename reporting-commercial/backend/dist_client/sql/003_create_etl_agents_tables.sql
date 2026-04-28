-- =====================================================
-- Script de creation des tables ETL Agents
-- Base: OptiBoard_SaaS (Base Centrale)
-- Tables pour la gestion des agents ETL distribues
-- =====================================================

USE OptiBoard_SaaS;
GO

-- =====================================================
-- TABLE: APP_ETL_Agents
-- Registre des agents ETL distants
-- =====================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Agents' AND xtype='U')
CREATE TABLE APP_ETL_Agents (
    agent_id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    dwh_code VARCHAR(50) NOT NULL,                    -- FK vers APP_DWH
    name NVARCHAR(200) NOT NULL,                      -- Nom descriptif de l'agent
    description NVARCHAR(500),                        -- Description
    api_key_hash VARCHAR(64) NOT NULL,                -- Hash SHA256 de la cle API
    -- Informations machine
    hostname NVARCHAR(200),                           -- Nom de la machine
    ip_address VARCHAR(50),                           -- Adresse IP
    os_info NVARCHAR(200),                            -- Info systeme
    agent_version VARCHAR(50),                        -- Version de l'agent
    -- Etat
    status VARCHAR(20) DEFAULT 'inactive',            -- inactive/active/syncing/error/paused
    last_heartbeat DATETIME NULL,                     -- Dernier signe de vie
    last_sync DATETIME NULL,                          -- Derniere synchronisation
    last_sync_status VARCHAR(20) NULL,                -- success/error
    last_error NVARCHAR(MAX) NULL,                    -- Derniere erreur
    consecutive_failures INT DEFAULT 0,               -- Echecs consecutifs
    -- Configuration
    sync_interval_seconds INT DEFAULT 300,            -- Intervalle sync (5 min par defaut)
    heartbeat_interval_seconds INT DEFAULT 30,        -- Intervalle heartbeat
    max_retry_count INT DEFAULT 3,                    -- Nombre max de tentatives
    batch_size INT DEFAULT 10000,                     -- Taille batch
    -- Metriques
    total_syncs BIGINT DEFAULT 0,                     -- Total syncs reussies
    total_rows_synced BIGINT DEFAULT 0,               -- Total lignes synchronisees
    -- Parametres
    is_active BIT DEFAULT 1,                          -- Actif/Inactif
    auto_start BIT DEFAULT 1,                         -- Demarrage automatique
    created_at DATETIME DEFAULT GETDATE(),
    updated_at DATETIME DEFAULT GETDATE(),
    created_by INT NULL,
    CONSTRAINT FK_ETL_Agents_DWH FOREIGN KEY (dwh_code) REFERENCES APP_DWH(code) ON DELETE CASCADE
);
GO

-- Index
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_ETL_Agents_dwh_code')
    CREATE INDEX IX_ETL_Agents_dwh_code ON APP_ETL_Agents(dwh_code);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_ETL_Agents_status')
    CREATE INDEX IX_ETL_Agents_status ON APP_ETL_Agents(status);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_ETL_Agents_active')
    CREATE INDEX IX_ETL_Agents_active ON APP_ETL_Agents(is_active);
GO

PRINT 'Table APP_ETL_Agents creee';
GO


-- =====================================================
-- TABLE: APP_ETL_Agent_Tables
-- Configuration des tables a synchroniser par agent
-- =====================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Agent_Tables' AND xtype='U')
CREATE TABLE APP_ETL_Agent_Tables (
    id INT IDENTITY(1,1) PRIMARY KEY,
    agent_id UNIQUEIDENTIFIER NOT NULL,               -- FK vers APP_ETL_Agents
    table_name NVARCHAR(100) NOT NULL,                -- Nom logique de la table
    -- Source (Sage 100)
    source_query NVARCHAR(MAX) NOT NULL,              -- Requete SQL source
    societe_code VARCHAR(50) NOT NULL,                -- Code societe Sage
    -- Cible (DWH)
    target_table NVARCHAR(100) NOT NULL,              -- Table cible dans le DWH
    primary_key_columns NVARCHAR(500) NOT NULL,       -- Colonnes PK (JSON array)
    -- Synchronisation
    sync_type VARCHAR(20) DEFAULT 'incremental',      -- incremental/full
    timestamp_column NVARCHAR(100) DEFAULT 'cbModification',
    last_sync_timestamp NVARCHAR(50) NULL,            -- Dernier timestamp sync
    -- Etat
    is_enabled BIT DEFAULT 1,
    priority VARCHAR(20) DEFAULT 'normal',            -- high/normal/low
    last_sync DATETIME NULL,
    last_sync_status VARCHAR(20) NULL,
    last_sync_rows INT DEFAULT 0,
    last_error NVARCHAR(MAX) NULL,
    -- Parametres
    created_at DATETIME DEFAULT GETDATE(),
    updated_at DATETIME DEFAULT GETDATE(),
    CONSTRAINT FK_ETL_Agent_Tables_Agent FOREIGN KEY (agent_id) REFERENCES APP_ETL_Agents(agent_id) ON DELETE CASCADE,
    CONSTRAINT UQ_ETL_Agent_Table UNIQUE (agent_id, table_name, societe_code)
);
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_ETL_Agent_Tables_agent_id')
    CREATE INDEX IX_ETL_Agent_Tables_agent_id ON APP_ETL_Agent_Tables(agent_id);
GO

PRINT 'Table APP_ETL_Agent_Tables creee';
GO


-- =====================================================
-- TABLE: APP_ETL_Agent_Sync_Log
-- Journaux de synchronisation
-- =====================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Agent_Sync_Log' AND xtype='U')
CREATE TABLE APP_ETL_Agent_Sync_Log (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    agent_id UNIQUEIDENTIFIER NOT NULL,
    table_name NVARCHAR(100) NOT NULL,
    societe_code VARCHAR(50) NOT NULL,
    batch_id NVARCHAR(50) NULL,                       -- ID batch pour regrouper
    -- Temps
    started_at DATETIME DEFAULT GETDATE(),
    completed_at DATETIME NULL,
    duration_seconds FLOAT NULL,
    -- Resultats
    status VARCHAR(20) DEFAULT 'pending',             -- pending/running/success/error
    rows_extracted INT DEFAULT 0,
    rows_inserted INT DEFAULT 0,
    rows_updated INT DEFAULT 0,
    rows_failed INT DEFAULT 0,
    -- Metriques
    sync_timestamp_start NVARCHAR(50) NULL,           -- Timestamp debut sync
    sync_timestamp_end NVARCHAR(50) NULL,             -- Timestamp fin sync
    execution_time_ms INT NULL,
    network_latency_ms INT NULL,
    -- Erreurs
    error_message NVARCHAR(MAX) NULL,
    error_details NVARCHAR(MAX) NULL,
    CONSTRAINT FK_ETL_Sync_Log_Agent FOREIGN KEY (agent_id) REFERENCES APP_ETL_Agents(agent_id) ON DELETE CASCADE
);
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_ETL_Sync_Log_agent_id')
    CREATE INDEX IX_ETL_Sync_Log_agent_id ON APP_ETL_Agent_Sync_Log(agent_id);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_ETL_Sync_Log_started_at')
    CREATE INDEX IX_ETL_Sync_Log_started_at ON APP_ETL_Agent_Sync_Log(started_at DESC);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_ETL_Sync_Log_status')
    CREATE INDEX IX_ETL_Sync_Log_status ON APP_ETL_Agent_Sync_Log(status);
GO

PRINT 'Table APP_ETL_Agent_Sync_Log creee';
GO


-- =====================================================
-- TABLE: APP_ETL_Agent_Commands
-- File de commandes pour les agents (modele Pull)
-- =====================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Agent_Commands' AND xtype='U')
CREATE TABLE APP_ETL_Agent_Commands (
    id INT IDENTITY(1,1) PRIMARY KEY,
    agent_id UNIQUEIDENTIFIER NOT NULL,
    command_type VARCHAR(50) NOT NULL,                -- sync_now/pause/resume/update_config/sync_table
    command_data NVARCHAR(MAX) NULL,                  -- Donnees JSON de la commande
    priority INT DEFAULT 5,                           -- 1=urgent, 5=normal, 10=low
    -- Etat
    status VARCHAR(20) DEFAULT 'pending',             -- pending/acknowledged/completed/expired/failed
    created_at DATETIME DEFAULT GETDATE(),
    acknowledged_at DATETIME NULL,
    completed_at DATETIME NULL,
    expires_at DATETIME NULL,                         -- Expiration (optionnel)
    -- Resultat
    result NVARCHAR(MAX) NULL,                        -- Resultat JSON
    error_message NVARCHAR(MAX) NULL,
    CONSTRAINT FK_ETL_Commands_Agent FOREIGN KEY (agent_id) REFERENCES APP_ETL_Agents(agent_id) ON DELETE CASCADE
);
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_ETL_Commands_agent_id')
    CREATE INDEX IX_ETL_Commands_agent_id ON APP_ETL_Agent_Commands(agent_id);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_ETL_Commands_status')
    CREATE INDEX IX_ETL_Commands_status ON APP_ETL_Agent_Commands(status, priority);
GO

PRINT 'Table APP_ETL_Agent_Commands creee';
GO


-- =====================================================
-- TABLE: APP_ETL_Agent_Heartbeats
-- Historique des heartbeats (monitoring)
-- =====================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Agent_Heartbeats' AND xtype='U')
CREATE TABLE APP_ETL_Agent_Heartbeats (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    agent_id UNIQUEIDENTIFIER NOT NULL,
    heartbeat_time DATETIME DEFAULT GETDATE(),
    -- Etat agent
    status VARCHAR(20) NOT NULL,                      -- idle/syncing/error
    current_task NVARCHAR(200) NULL,                  -- Tache en cours
    -- Metriques systeme
    cpu_usage FLOAT NULL,
    memory_usage FLOAT NULL,
    disk_usage FLOAT NULL,
    queue_size INT NULL,                              -- Taille file d'attente
    -- Info supplementaire
    agent_uptime_seconds BIGINT NULL,
    additional_info NVARCHAR(MAX) NULL,               -- JSON
    CONSTRAINT FK_ETL_Heartbeats_Agent FOREIGN KEY (agent_id) REFERENCES APP_ETL_Agents(agent_id) ON DELETE CASCADE
);
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_ETL_Heartbeats_agent_id')
    CREATE INDEX IX_ETL_Heartbeats_agent_id ON APP_ETL_Agent_Heartbeats(agent_id, heartbeat_time DESC);
GO

PRINT 'Table APP_ETL_Agent_Heartbeats creee';
GO


-- =====================================================
-- TABLE: APP_ETL_Audit_Log
-- Audit des actions sur les agents
-- =====================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Audit_Log' AND xtype='U')
CREATE TABLE APP_ETL_Audit_Log (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    agent_id UNIQUEIDENTIFIER NULL,
    user_id INT NULL,
    action VARCHAR(100) NOT NULL,                     -- create_agent/delete_agent/push_data/etc
    entity_type VARCHAR(50) NULL,                     -- agent/table/command
    entity_id NVARCHAR(100) NULL,
    details NVARCHAR(MAX) NULL,                       -- JSON
    ip_address VARCHAR(50) NULL,
    created_at DATETIME DEFAULT GETDATE()
);
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_ETL_Audit_agent_id')
    CREATE INDEX IX_ETL_Audit_agent_id ON APP_ETL_Audit_Log(agent_id);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_ETL_Audit_created_at')
    CREATE INDEX IX_ETL_Audit_created_at ON APP_ETL_Audit_Log(created_at DESC);
GO

PRINT 'Table APP_ETL_Audit_Log creee';
GO


-- =====================================================
-- VUES UTILES
-- =====================================================

-- Vue: Statut de tous les agents
IF EXISTS (SELECT * FROM sys.views WHERE name = 'VW_ETL_Agents_Status')
    DROP VIEW VW_ETL_Agents_Status;
GO

CREATE VIEW VW_ETL_Agents_Status AS
SELECT
    a.agent_id,
    a.name,
    a.dwh_code,
    d.nom AS dwh_name,
    a.status,
    a.hostname,
    a.ip_address,
    a.last_heartbeat,
    a.last_sync,
    a.last_sync_status,
    a.consecutive_failures,
    a.total_syncs,
    a.total_rows_synced,
    a.is_active,
    a.sync_interval_seconds,
    CASE
        WHEN a.is_active = 0 THEN 'Desactive'
        WHEN a.last_heartbeat IS NULL THEN 'Jamais connecte'
        WHEN DATEDIFF(SECOND, a.last_heartbeat, GETDATE()) > a.heartbeat_interval_seconds * 3 THEN 'Hors ligne'
        WHEN a.status = 'error' THEN 'Erreur'
        WHEN a.status = 'syncing' THEN 'Synchronisation'
        ELSE 'En ligne'
    END AS health_status,
    DATEDIFF(SECOND, a.last_heartbeat, GETDATE()) AS seconds_since_heartbeat,
    (SELECT COUNT(*) FROM APP_ETL_Agent_Tables t WHERE t.agent_id = a.agent_id AND t.is_enabled = 1) AS tables_count,
    (SELECT COUNT(*) FROM APP_ETL_Agent_Commands c WHERE c.agent_id = a.agent_id AND c.status = 'pending') AS pending_commands
FROM APP_ETL_Agents a
LEFT JOIN APP_DWH d ON a.dwh_code = d.code;
GO

PRINT 'Vue VW_ETL_Agents_Status creee';
GO


-- Vue: Derniers logs par agent
IF EXISTS (SELECT * FROM sys.views WHERE name = 'VW_ETL_Agent_Latest_Syncs')
    DROP VIEW VW_ETL_Agent_Latest_Syncs;
GO

CREATE VIEW VW_ETL_Agent_Latest_Syncs AS
SELECT
    l.agent_id,
    a.name AS agent_name,
    l.table_name,
    l.societe_code,
    l.status,
    l.started_at,
    l.completed_at,
    l.duration_seconds,
    l.rows_extracted,
    l.rows_inserted,
    l.rows_updated,
    l.rows_failed,
    l.error_message
FROM APP_ETL_Agent_Sync_Log l
INNER JOIN APP_ETL_Agents a ON l.agent_id = a.agent_id
WHERE l.id IN (
    SELECT MAX(id)
    FROM APP_ETL_Agent_Sync_Log
    GROUP BY agent_id, table_name, societe_code
);
GO

PRINT 'Vue VW_ETL_Agent_Latest_Syncs creee';
GO


-- =====================================================
-- PROCEDURES STOCKEES
-- =====================================================

-- Procedure: Enregistrer un heartbeat
IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'SP_ETL_Agent_Heartbeat')
    DROP PROCEDURE SP_ETL_Agent_Heartbeat;
GO

CREATE PROCEDURE SP_ETL_Agent_Heartbeat
    @agent_id UNIQUEIDENTIFIER,
    @status VARCHAR(20),
    @current_task NVARCHAR(200) = NULL,
    @cpu_usage FLOAT = NULL,
    @memory_usage FLOAT = NULL,
    @disk_usage FLOAT = NULL,
    @queue_size INT = NULL
AS
BEGIN
    SET NOCOUNT ON;

    -- Mettre a jour l'agent
    UPDATE APP_ETL_Agents
    SET
        last_heartbeat = GETDATE(),
        status = CASE WHEN @status = 'error' THEN 'error' ELSE @status END,
        hostname = ISNULL(hostname, HOST_NAME()),
        updated_at = GETDATE()
    WHERE agent_id = @agent_id;

    -- Inserer le heartbeat
    INSERT INTO APP_ETL_Agent_Heartbeats (
        agent_id, status, current_task,
        cpu_usage, memory_usage, disk_usage, queue_size
    )
    VALUES (
        @agent_id, @status, @current_task,
        @cpu_usage, @memory_usage, @disk_usage, @queue_size
    );

    -- Retourner les commandes en attente
    SELECT id, command_type, command_data, priority
    FROM APP_ETL_Agent_Commands
    WHERE agent_id = @agent_id
      AND status = 'pending'
      AND (expires_at IS NULL OR expires_at > GETDATE())
    ORDER BY priority ASC, created_at ASC;
END
GO

PRINT 'Procedure SP_ETL_Agent_Heartbeat creee';
GO


-- Procedure: Nettoyer les anciens heartbeats
IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'SP_ETL_Cleanup_Heartbeats')
    DROP PROCEDURE SP_ETL_Cleanup_Heartbeats;
GO

CREATE PROCEDURE SP_ETL_Cleanup_Heartbeats
    @retention_hours INT = 24
AS
BEGIN
    SET NOCOUNT ON;

    DELETE FROM APP_ETL_Agent_Heartbeats
    WHERE heartbeat_time < DATEADD(HOUR, -@retention_hours, GETDATE());

    PRINT CONCAT('Heartbeats nettoyes: ', @@ROWCOUNT, ' lignes supprimees');
END
GO

PRINT 'Procedure SP_ETL_Cleanup_Heartbeats creee';
GO


-- Procedure: Nettoyer les anciens logs
IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'SP_ETL_Cleanup_Sync_Logs')
    DROP PROCEDURE SP_ETL_Cleanup_Sync_Logs;
GO

CREATE PROCEDURE SP_ETL_Cleanup_Sync_Logs
    @retention_days INT = 30
AS
BEGIN
    SET NOCOUNT ON;

    DELETE FROM APP_ETL_Agent_Sync_Log
    WHERE started_at < DATEADD(DAY, -@retention_days, GETDATE());

    DELETE FROM APP_ETL_Audit_Log
    WHERE created_at < DATEADD(DAY, -@retention_days, GETDATE());

    PRINT CONCAT('Logs nettoyes: retention ', @retention_days, ' jours');
END
GO

PRINT 'Procedure SP_ETL_Cleanup_Sync_Logs creee';
GO


PRINT '';
PRINT '=====================================================';
PRINT ' TABLES ETL AGENTS CREEES AVEC SUCCES';
PRINT '=====================================================';
PRINT ' - APP_ETL_Agents (Registre agents)';
PRINT ' - APP_ETL_Agent_Tables (Config tables)';
PRINT ' - APP_ETL_Agent_Sync_Log (Journaux sync)';
PRINT ' - APP_ETL_Agent_Commands (File commandes)';
PRINT ' - APP_ETL_Agent_Heartbeats (Monitoring)';
PRINT ' - APP_ETL_Audit_Log (Audit)';
PRINT '=====================================================';
GO
