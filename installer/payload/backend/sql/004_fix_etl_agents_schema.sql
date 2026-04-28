-- =====================================================
-- Script de correction du schema APP_ETL_Agents
-- Ajoute les colonnes manquantes pour compatibilite backend
-- =====================================================

USE OptiBoard_SaaS;
GO

-- Supprimer et recreer la table APP_ETL_Agents avec le bon schema
-- ATTENTION: Cela supprime les donnees existantes

PRINT 'Suppression des anciennes tables si elles existent...';

-- Supprimer les contraintes et tables dans l'ordre
IF EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK_ETL_Agent_Tables_Agent')
    ALTER TABLE APP_ETL_Agent_Tables DROP CONSTRAINT FK_ETL_Agent_Tables_Agent;

IF EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK_ETL_Agent_Heartbeats_Agent')
    ALTER TABLE APP_ETL_Agent_Heartbeats DROP CONSTRAINT FK_ETL_Agent_Heartbeats_Agent;

IF EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK_ETL_Agent_Sync_Log_Agent')
    ALTER TABLE APP_ETL_Agent_Sync_Log DROP CONSTRAINT FK_ETL_Agent_Sync_Log_Agent;

IF EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK_ETL_Agent_Commands_Agent')
    ALTER TABLE APP_ETL_Agent_Commands DROP CONSTRAINT FK_ETL_Agent_Commands_Agent;

IF EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Agent_Tables' AND xtype='U')
    DROP TABLE APP_ETL_Agent_Tables;

IF EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Agent_Heartbeats' AND xtype='U')
    DROP TABLE APP_ETL_Agent_Heartbeats;

IF EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Agent_Sync_Log' AND xtype='U')
    DROP TABLE APP_ETL_Agent_Sync_Log;

IF EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Agent_Commands' AND xtype='U')
    DROP TABLE APP_ETL_Agent_Commands;

IF EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Audit_Log' AND xtype='U')
    DROP TABLE APP_ETL_Audit_Log;

IF EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Agents' AND xtype='U')
    DROP TABLE APP_ETL_Agents;
GO

PRINT 'Creation de la table APP_ETL_Agents avec le nouveau schema...';

-- Creer la table avec le schema compatible backend
CREATE TABLE APP_ETL_Agents (
    id INT IDENTITY(1,1) PRIMARY KEY,
    agent_id UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID() UNIQUE,
    dwh_code VARCHAR(50) NOT NULL,
    name NVARCHAR(200) NOT NULL,
    description NVARCHAR(500),

    -- Cle API
    api_key_hash VARCHAR(64) NOT NULL,
    api_key_prefix VARCHAR(20),                       -- Prefixe pour identification

    -- Config Sage
    sage_server NVARCHAR(200),
    sage_database NVARCHAR(200),
    sage_username NVARCHAR(100),

    -- Info machine
    hostname NVARCHAR(200),
    ip_address VARCHAR(50),
    os_info NVARCHAR(200),
    agent_version VARCHAR(50),

    -- Etat
    status VARCHAR(20) DEFAULT 'inactive',
    last_heartbeat DATETIME NULL,
    last_sync DATETIME NULL,
    last_sync_status VARCHAR(20) NULL,
    last_error NVARCHAR(MAX) NULL,
    consecutive_failures INT DEFAULT 0,

    -- Configuration
    sync_interval_seconds INT DEFAULT 300,
    heartbeat_interval_seconds INT DEFAULT 30,
    max_retry_count INT DEFAULT 3,
    batch_size INT DEFAULT 5000,

    -- Metriques
    total_syncs BIGINT DEFAULT 0,
    total_rows_synced BIGINT DEFAULT 0,

    -- Parametres
    is_enabled BIT DEFAULT 1,
    is_active BIT DEFAULT 1,
    auto_start BIT DEFAULT 1,

    -- Audit
    created_at DATETIME DEFAULT GETDATE(),
    updated_at DATETIME DEFAULT GETDATE(),
    created_by INT NULL
);
GO

-- Index
CREATE INDEX IX_ETL_Agents_dwh_code ON APP_ETL_Agents(dwh_code);
CREATE INDEX IX_ETL_Agents_status ON APP_ETL_Agents(status);
CREATE INDEX IX_ETL_Agents_agent_id ON APP_ETL_Agents(agent_id);
CREATE INDEX IX_ETL_Agents_is_enabled ON APP_ETL_Agents(is_enabled);
GO

PRINT 'Table APP_ETL_Agents creee avec succes';
GO

-- =====================================================
-- TABLE: APP_ETL_Agent_Tables
-- =====================================================
CREATE TABLE APP_ETL_Agent_Tables (
    id INT IDENTITY(1,1) PRIMARY KEY,
    agent_id UNIQUEIDENTIFIER NOT NULL,
    table_name NVARCHAR(100) NOT NULL,
    source_query NVARCHAR(MAX) NOT NULL,
    societe_code VARCHAR(50) NOT NULL,
    target_table NVARCHAR(100) NOT NULL,
    primary_key_columns NVARCHAR(500) NOT NULL,
    sync_type VARCHAR(20) DEFAULT 'incremental',
    timestamp_column NVARCHAR(100) DEFAULT 'cbModification',
    watermark_value NVARCHAR(100) NULL,
    is_enabled BIT DEFAULT 1,
    priority VARCHAR(20) DEFAULT 'normal',
    last_sync DATETIME NULL,
    last_sync_status VARCHAR(20) NULL,
    last_sync_rows INT DEFAULT 0,
    last_sync_duration_seconds FLOAT DEFAULT 0,
    total_syncs BIGINT DEFAULT 0,
    total_rows_synced BIGINT DEFAULT 0,
    last_error NVARCHAR(MAX) NULL,
    created_at DATETIME DEFAULT GETDATE(),
    updated_at DATETIME DEFAULT GETDATE(),
    CONSTRAINT FK_ETL_Agent_Tables_Agent FOREIGN KEY (agent_id) REFERENCES APP_ETL_Agents(agent_id) ON DELETE CASCADE
);
GO

CREATE INDEX IX_ETL_Agent_Tables_agent ON APP_ETL_Agent_Tables(agent_id);
CREATE INDEX IX_ETL_Agent_Tables_enabled ON APP_ETL_Agent_Tables(is_enabled);
GO

PRINT 'Table APP_ETL_Agent_Tables creee';
GO

-- =====================================================
-- TABLE: APP_ETL_Agent_Commands
-- =====================================================
CREATE TABLE APP_ETL_Agent_Commands (
    id INT IDENTITY(1,1) PRIMARY KEY,
    agent_id UNIQUEIDENTIFIER NOT NULL,
    command_type VARCHAR(50) NOT NULL,
    command_data NVARCHAR(MAX) NULL,
    status VARCHAR(20) DEFAULT 'pending',
    priority INT DEFAULT 5,
    created_at DATETIME DEFAULT GETDATE(),
    expires_at DATETIME NULL,
    acknowledged_at DATETIME NULL,
    completed_at DATETIME NULL,
    result NVARCHAR(MAX) NULL,
    error_message NVARCHAR(MAX) NULL,
    CONSTRAINT FK_ETL_Agent_Commands_Agent FOREIGN KEY (agent_id) REFERENCES APP_ETL_Agents(agent_id) ON DELETE CASCADE
);
GO

CREATE INDEX IX_ETL_Commands_agent_status ON APP_ETL_Agent_Commands(agent_id, status);
CREATE INDEX IX_ETL_Commands_pending ON APP_ETL_Agent_Commands(status, priority) WHERE status = 'pending';
GO

PRINT 'Table APP_ETL_Agent_Commands creee';
GO

-- =====================================================
-- TABLE: APP_ETL_Agent_Sync_Log
-- =====================================================
CREATE TABLE APP_ETL_Agent_Sync_Log (
    id INT IDENTITY(1,1) PRIMARY KEY,
    agent_id UNIQUEIDENTIFIER NOT NULL,
    table_name NVARCHAR(100) NOT NULL,
    societe_code VARCHAR(50),
    started_at DATETIME NOT NULL,
    completed_at DATETIME NULL,
    duration_seconds FLOAT NULL,
    status VARCHAR(20) NOT NULL,
    rows_extracted INT DEFAULT 0,
    rows_inserted INT DEFAULT 0,
    rows_updated INT DEFAULT 0,
    rows_failed INT DEFAULT 0,
    error_message NVARCHAR(MAX) NULL,
    sync_timestamp_start DATETIME NULL,
    sync_timestamp_end DATETIME NULL,
    CONSTRAINT FK_ETL_Agent_Sync_Log_Agent FOREIGN KEY (agent_id) REFERENCES APP_ETL_Agents(agent_id) ON DELETE CASCADE
);
GO

CREATE INDEX IX_ETL_Sync_Log_agent ON APP_ETL_Agent_Sync_Log(agent_id);
CREATE INDEX IX_ETL_Sync_Log_date ON APP_ETL_Agent_Sync_Log(started_at DESC);
GO

PRINT 'Table APP_ETL_Agent_Sync_Log creee';
GO

-- =====================================================
-- TABLE: APP_ETL_Agent_Heartbeats
-- =====================================================
CREATE TABLE APP_ETL_Agent_Heartbeats (
    id INT IDENTITY(1,1) PRIMARY KEY,
    agent_id UNIQUEIDENTIFIER NOT NULL,
    timestamp DATETIME DEFAULT GETDATE(),
    status VARCHAR(20) NOT NULL,
    current_task NVARCHAR(200) NULL,
    cpu_usage FLOAT NULL,
    memory_usage FLOAT NULL,
    disk_usage FLOAT NULL,
    queue_size INT DEFAULT 0,
    CONSTRAINT FK_ETL_Agent_Heartbeats_Agent FOREIGN KEY (agent_id) REFERENCES APP_ETL_Agents(agent_id) ON DELETE CASCADE
);
GO

CREATE INDEX IX_ETL_Heartbeats_agent ON APP_ETL_Agent_Heartbeats(agent_id, timestamp DESC);
GO

PRINT 'Table APP_ETL_Agent_Heartbeats creee';
GO

-- =====================================================
-- TABLE: APP_ETL_Audit_Log
-- =====================================================
CREATE TABLE APP_ETL_Audit_Log (
    id INT IDENTITY(1,1) PRIMARY KEY,
    agent_id UNIQUEIDENTIFIER NULL,
    action VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id NVARCHAR(100) NULL,
    old_values NVARCHAR(MAX) NULL,
    new_values NVARCHAR(MAX) NULL,
    performed_by INT NULL,
    performed_at DATETIME DEFAULT GETDATE(),
    ip_address VARCHAR(50) NULL
);
GO

CREATE INDEX IX_ETL_Audit_agent ON APP_ETL_Audit_Log(agent_id);
CREATE INDEX IX_ETL_Audit_date ON APP_ETL_Audit_Log(performed_at DESC);
GO

PRINT 'Table APP_ETL_Audit_Log creee';
GO

PRINT '=====================================================';
PRINT 'TABLES ETL AGENTS RECREEES AVEC SUCCES';
PRINT '=====================================================';
PRINT '- APP_ETL_Agents (Registre agents)';
PRINT '- APP_ETL_Agent_Tables (Config tables)';
PRINT '- APP_ETL_Agent_Commands (File commandes)';
PRINT '- APP_ETL_Agent_Sync_Log (Journaux sync)';
PRINT '- APP_ETL_Agent_Heartbeats (Monitoring)';
PRINT '- APP_ETL_Audit_Log (Audit)';
PRINT '=====================================================';
GO
