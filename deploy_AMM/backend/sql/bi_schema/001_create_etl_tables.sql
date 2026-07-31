-- ══════════════════════════════════════════════════════════════════════════════
-- CRÉATION DES TABLES ETL MÉTADONNÉES
-- Base: DWH_ALBOUGHAZE
-- ══════════════════════════════════════════════════════════════════════════════

-- ══════════════════════════════════════════════════════════════════════════════
-- TABLE: ETL_TABLE_CONFIG - Configuration des tables à synchroniser
-- ══════════════════════════════════════════════════════════════════════════════
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'ETL_TABLE_CONFIG')
BEGIN
    CREATE TABLE ETL_TABLE_CONFIG (
        config_id INT IDENTITY(1,1) PRIMARY KEY,
        table_name NVARCHAR(100) NOT NULL UNIQUE,
        source_table NVARCHAR(100) NOT NULL,
        source_query NVARCHAR(MAX) NULL,
        primary_key_columns NVARCHAR(500) NOT NULL,
        sync_type NVARCHAR(20) DEFAULT 'incremental',
        priority NVARCHAR(20) DEFAULT 'normal',
        sync_interval_seconds INT DEFAULT 15,
        is_active BIT DEFAULT 1,
        created_at DATETIME2 DEFAULT GETDATE(),
        updated_at DATETIME2 DEFAULT GETDATE()
    );

    CREATE INDEX IX_ETL_TABLE_CONFIG_Active ON ETL_TABLE_CONFIG (is_active);

    PRINT 'Table ETL_TABLE_CONFIG créée';
END
GO

-- ══════════════════════════════════════════════════════════════════════════════
-- TABLE: ETL_SYNC_STATE - État courant de synchronisation par table
-- ══════════════════════════════════════════════════════════════════════════════
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'ETL_SYNC_STATE')
BEGIN
    CREATE TABLE ETL_SYNC_STATE (
        table_name NVARCHAR(100) PRIMARY KEY,
        last_sync_timestamp DATETIME2 NULL,
        last_successful_sync DATETIME2 NULL,
        total_rows_synced BIGINT DEFAULT 0,
        consecutive_failures INT DEFAULT 0,
        is_syncing BIT DEFAULT 0,
        is_enabled BIT DEFAULT 1,
        last_error NVARCHAR(MAX) NULL,
        created_at DATETIME2 DEFAULT GETDATE(),
        updated_at DATETIME2 DEFAULT GETDATE()
    );

    PRINT 'Table ETL_SYNC_STATE créée';
END
GO

-- ══════════════════════════════════════════════════════════════════════════════
-- TABLE: ETL_SYNC_LOG - Historique des synchronisations
-- ══════════════════════════════════════════════════════════════════════════════
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'ETL_SYNC_LOG')
BEGIN
    CREATE TABLE ETL_SYNC_LOG (
        id BIGINT IDENTITY(1,1) PRIMARY KEY,
        table_name NVARCHAR(100) NOT NULL,
        batch_id NVARCHAR(50) NULL,
        sync_type NVARCHAR(20) DEFAULT 'full',
        sync_start DATETIME2 NULL,
        sync_end DATETIME2 NULL,
        started_at DATETIME2 DEFAULT GETDATE(),
        completed_at DATETIME2 NULL,
        status NVARCHAR(20) DEFAULT 'running',
        rows_extracted INT DEFAULT 0,
        rows_loaded INT DEFAULT 0,
        rows_inserted INT DEFAULT 0,
        rows_updated INT DEFAULT 0,
        rows_failed INT DEFAULT 0,
        duration_seconds FLOAT NULL,
        last_sync_timestamp DATETIME2 NULL,
        error_message NVARCHAR(MAX) NULL,
        execution_time_ms INT NULL,
        network_latency_ms INT NULL
    );

    CREATE INDEX IX_ETL_SYNC_LOG_Table ON ETL_SYNC_LOG (table_name, started_at DESC);
    CREATE INDEX IX_ETL_SYNC_LOG_Status ON ETL_SYNC_LOG (status);
    CREATE INDEX IX_ETL_SYNC_LOG_BatchId ON ETL_SYNC_LOG (batch_id);

    PRINT 'Table ETL_SYNC_LOG créée';
END
GO

-- Ajouter les colonnes manquantes si la table existe deja
IF EXISTS (SELECT * FROM sys.tables WHERE name = 'ETL_SYNC_LOG')
BEGIN
    IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('ETL_SYNC_LOG') AND name = 'id')
    BEGIN
        -- Renommer log_id en id si log_id existe
        IF EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('ETL_SYNC_LOG') AND name = 'log_id')
            EXEC sp_rename 'ETL_SYNC_LOG.log_id', 'id', 'COLUMN';
    END

    IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('ETL_SYNC_LOG') AND name = 'sync_type')
        ALTER TABLE ETL_SYNC_LOG ADD sync_type NVARCHAR(20) DEFAULT 'full';

    IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('ETL_SYNC_LOG') AND name = 'started_at')
        ALTER TABLE ETL_SYNC_LOG ADD started_at DATETIME2 DEFAULT GETDATE();

    IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('ETL_SYNC_LOG') AND name = 'completed_at')
        ALTER TABLE ETL_SYNC_LOG ADD completed_at DATETIME2 NULL;

    IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('ETL_SYNC_LOG') AND name = 'rows_loaded')
        ALTER TABLE ETL_SYNC_LOG ADD rows_loaded INT DEFAULT 0;

    IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('ETL_SYNC_LOG') AND name = 'duration_seconds')
        ALTER TABLE ETL_SYNC_LOG ADD duration_seconds FLOAT NULL;

    PRINT 'Colonnes ETL_SYNC_LOG mises a jour';
END
GO

-- ══════════════════════════════════════════════════════════════════════════════
-- TABLE: ETL_ERROR_LOG - Détail des erreurs
-- ══════════════════════════════════════════════════════════════════════════════
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'ETL_ERROR_LOG')
BEGIN
    CREATE TABLE ETL_ERROR_LOG (
        error_id BIGINT IDENTITY(1,1) PRIMARY KEY,
        log_id BIGINT NULL,
        table_name NVARCHAR(100) NOT NULL,
        error_time DATETIME2 DEFAULT GETDATE(),
        error_type NVARCHAR(100) NULL,
        error_message NVARCHAR(MAX) NULL,
        stack_trace NVARCHAR(MAX) NULL,
        source_record NVARCHAR(MAX) NULL,
        retry_count INT DEFAULT 0,
        is_resolved BIT DEFAULT 0,
        resolved_at DATETIME2 NULL,
        resolved_by NVARCHAR(100) NULL,
        CONSTRAINT FK_ETL_ERROR_LOG_SyncLog FOREIGN KEY (log_id)
            REFERENCES ETL_SYNC_LOG(log_id) ON DELETE SET NULL
    );

    CREATE INDEX IX_ETL_ERROR_LOG_Table ON ETL_ERROR_LOG (table_name, error_time DESC);
    CREATE INDEX IX_ETL_ERROR_LOG_Resolved ON ETL_ERROR_LOG (is_resolved);

    PRINT 'Table ETL_ERROR_LOG créée';
END
GO

-- ══════════════════════════════════════════════════════════════════════════════
-- TABLE: ETL_METRICS - Métriques de performance
-- ══════════════════════════════════════════════════════════════════════════════
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'ETL_METRICS')
BEGIN
    CREATE TABLE ETL_METRICS (
        metric_id BIGINT IDENTITY(1,1) PRIMARY KEY,
        metric_time DATETIME2 DEFAULT GETDATE(),
        metric_type NVARCHAR(50) NOT NULL,
        metric_name NVARCHAR(100) NOT NULL,
        metric_value FLOAT NOT NULL,
        table_name NVARCHAR(100) NULL,
        additional_data NVARCHAR(MAX) NULL
    );

    CREATE INDEX IX_ETL_METRICS_Time ON ETL_METRICS (metric_time DESC);
    CREATE INDEX IX_ETL_METRICS_Type ON ETL_METRICS (metric_type, metric_name);

    PRINT 'Table ETL_METRICS créée';
END
GO

-- ══════════════════════════════════════════════════════════════════════════════
-- TABLE: ETL_ALERTS - Alertes générées
-- ══════════════════════════════════════════════════════════════════════════════
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'ETL_ALERTS')
BEGIN
    CREATE TABLE ETL_ALERTS (
        alert_id BIGINT IDENTITY(1,1) PRIMARY KEY,
        alert_time DATETIME2 DEFAULT GETDATE(),
        alert_type NVARCHAR(50) NOT NULL,
        severity NVARCHAR(20) NOT NULL,
        table_name NVARCHAR(100) NULL,
        message NVARCHAR(MAX) NOT NULL,
        is_acknowledged BIT DEFAULT 0,
        acknowledged_at DATETIME2 NULL,
        acknowledged_by NVARCHAR(100) NULL
    );

    CREATE INDEX IX_ETL_ALERTS_Time ON ETL_ALERTS (alert_time DESC);
    CREATE INDEX IX_ETL_ALERTS_Acknowledged ON ETL_ALERTS (is_acknowledged, severity);

    PRINT 'Table ETL_ALERTS créée';
END
GO

-- ══════════════════════════════════════════════════════════════════════════════
-- VUES UTILES
-- ══════════════════════════════════════════════════════════════════════════════

-- Vue: Statut actuel de toutes les tables
IF EXISTS (SELECT * FROM sys.views WHERE name = 'VW_ETL_STATUS')
    DROP VIEW VW_ETL_STATUS;
GO

CREATE VIEW VW_ETL_STATUS AS
SELECT
    s.table_name,
    s.last_sync_timestamp,
    s.last_successful_sync,
    s.total_rows_synced,
    s.consecutive_failures,
    s.is_syncing,
    s.is_enabled,
    CASE
        WHEN s.is_syncing = 1 THEN 'En cours'
        WHEN s.consecutive_failures > 0 THEN 'Erreur'
        WHEN s.last_successful_sync IS NULL THEN 'Jamais synchronisé'
        WHEN DATEDIFF(MINUTE, s.last_successful_sync, GETDATE()) > 5 THEN 'Retard'
        ELSE 'OK'
    END AS status,
    s.last_error,
    c.sync_type,
    c.priority
FROM ETL_SYNC_STATE s
LEFT JOIN ETL_TABLE_CONFIG c ON s.table_name = c.table_name;
GO

PRINT 'Vue VW_ETL_STATUS créée';
GO

-- Vue: Derniers logs par table
IF EXISTS (SELECT * FROM sys.views WHERE name = 'VW_ETL_LATEST_LOGS')
    DROP VIEW VW_ETL_LATEST_LOGS;
GO

CREATE VIEW VW_ETL_LATEST_LOGS AS
SELECT
    l.*
FROM ETL_SYNC_LOG l
INNER JOIN (
    SELECT table_name, MAX(log_id) AS max_log_id
    FROM ETL_SYNC_LOG
    GROUP BY table_name
) latest ON l.log_id = latest.max_log_id;
GO

PRINT 'Vue VW_ETL_LATEST_LOGS créée';
GO

-- Vue: Statistiques des dernières 24h
IF EXISTS (SELECT * FROM sys.views WHERE name = 'VW_ETL_STATS_24H')
    DROP VIEW VW_ETL_STATS_24H;
GO

CREATE VIEW VW_ETL_STATS_24H AS
SELECT
    table_name,
    COUNT(*) AS total_syncs,
    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS successful_syncs,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed_syncs,
    SUM(rows_extracted) AS total_rows_extracted,
    SUM(rows_inserted) AS total_rows_inserted,
    SUM(rows_updated) AS total_rows_updated,
    AVG(execution_time_ms) AS avg_execution_time_ms,
    MAX(execution_time_ms) AS max_execution_time_ms,
    AVG(network_latency_ms) AS avg_latency_ms
FROM ETL_SYNC_LOG
WHERE sync_start >= DATEADD(HOUR, -24, GETDATE())
GROUP BY table_name;
GO

PRINT 'Vue VW_ETL_STATS_24H créée';
GO

-- ══════════════════════════════════════════════════════════════════════════════
-- PROCÉDURES STOCKÉES
-- ══════════════════════════════════════════════════════════════════════════════

-- Procédure: Enregistrer le début d'une synchronisation
IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'SP_ETL_START_SYNC')
    DROP PROCEDURE SP_ETL_START_SYNC;
GO

CREATE PROCEDURE SP_ETL_START_SYNC
    @table_name NVARCHAR(100),
    @batch_id NVARCHAR(50),
    @log_id BIGINT OUTPUT
AS
BEGIN
    SET NOCOUNT ON;

    -- Insérer le log
    INSERT INTO ETL_SYNC_LOG (table_name, batch_id, sync_start, status)
    VALUES (@table_name, @batch_id, GETDATE(), 'running');

    SET @log_id = SCOPE_IDENTITY();

    -- Mettre à jour l'état
    UPDATE ETL_SYNC_STATE
    SET is_syncing = 1, updated_at = GETDATE()
    WHERE table_name = @table_name;

    IF @@ROWCOUNT = 0
    BEGIN
        INSERT INTO ETL_SYNC_STATE (table_name, is_syncing)
        VALUES (@table_name, 1);
    END
END
GO

PRINT 'Procédure SP_ETL_START_SYNC créée';
GO

-- Procédure: Enregistrer la fin d'une synchronisation (succès)
IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'SP_ETL_END_SYNC_SUCCESS')
    DROP PROCEDURE SP_ETL_END_SYNC_SUCCESS;
GO

CREATE PROCEDURE SP_ETL_END_SYNC_SUCCESS
    @log_id BIGINT,
    @rows_extracted INT,
    @rows_inserted INT,
    @rows_updated INT,
    @last_sync_timestamp DATETIME2,
    @execution_time_ms INT
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @table_name NVARCHAR(100);

    -- Mettre à jour le log
    UPDATE ETL_SYNC_LOG
    SET
        sync_end = GETDATE(),
        status = 'success',
        rows_extracted = @rows_extracted,
        rows_inserted = @rows_inserted,
        rows_updated = @rows_updated,
        last_sync_timestamp = @last_sync_timestamp,
        execution_time_ms = @execution_time_ms
    WHERE log_id = @log_id;

    SELECT @table_name = table_name FROM ETL_SYNC_LOG WHERE log_id = @log_id;

    -- Mettre à jour l'état
    UPDATE ETL_SYNC_STATE
    SET
        is_syncing = 0,
        last_sync_timestamp = @last_sync_timestamp,
        last_successful_sync = GETDATE(),
        total_rows_synced = total_rows_synced + @rows_inserted + @rows_updated,
        consecutive_failures = 0,
        last_error = NULL,
        updated_at = GETDATE()
    WHERE table_name = @table_name;
END
GO

PRINT 'Procédure SP_ETL_END_SYNC_SUCCESS créée';
GO

-- Procédure: Enregistrer la fin d'une synchronisation (échec)
IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'SP_ETL_END_SYNC_FAILURE')
    DROP PROCEDURE SP_ETL_END_SYNC_FAILURE;
GO

CREATE PROCEDURE SP_ETL_END_SYNC_FAILURE
    @log_id BIGINT,
    @error_message NVARCHAR(MAX),
    @execution_time_ms INT
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @table_name NVARCHAR(100);

    -- Mettre à jour le log
    UPDATE ETL_SYNC_LOG
    SET
        sync_end = GETDATE(),
        status = 'failed',
        error_message = @error_message,
        execution_time_ms = @execution_time_ms
    WHERE log_id = @log_id;

    SELECT @table_name = table_name FROM ETL_SYNC_LOG WHERE log_id = @log_id;

    -- Mettre à jour l'état
    UPDATE ETL_SYNC_STATE
    SET
        is_syncing = 0,
        consecutive_failures = consecutive_failures + 1,
        last_error = @error_message,
        updated_at = GETDATE()
    WHERE table_name = @table_name;

    -- Créer une alerte si trop d'échecs
    IF EXISTS (
        SELECT 1 FROM ETL_SYNC_STATE
        WHERE table_name = @table_name AND consecutive_failures >= 3
    )
    BEGIN
        INSERT INTO ETL_ALERTS (alert_type, severity, table_name, message)
        VALUES (
            'SYNC_FAILURE',
            'HIGH',
            @table_name,
            'La table ' + @table_name + ' a échoué 3 fois consécutives: ' + @error_message
        );
    END
END
GO

PRINT 'Procédure SP_ETL_END_SYNC_FAILURE créée';
GO

-- Procédure: Nettoyer les anciens logs
IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'SP_ETL_CLEANUP_LOGS')
    DROP PROCEDURE SP_ETL_CLEANUP_LOGS;
GO

CREATE PROCEDURE SP_ETL_CLEANUP_LOGS
    @retention_days INT = 30
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @cutoff_date DATETIME2 = DATEADD(DAY, -@retention_days, GETDATE());

    -- Supprimer les erreurs orphelines
    DELETE FROM ETL_ERROR_LOG
    WHERE log_id IN (
        SELECT log_id FROM ETL_SYNC_LOG
        WHERE sync_start < @cutoff_date
    );

    -- Supprimer les anciens logs
    DELETE FROM ETL_SYNC_LOG
    WHERE sync_start < @cutoff_date;

    -- Supprimer les anciennes métriques
    DELETE FROM ETL_METRICS
    WHERE metric_time < @cutoff_date;

    -- Supprimer les anciennes alertes acquittées
    DELETE FROM ETL_ALERTS
    WHERE is_acknowledged = 1 AND alert_time < @cutoff_date;

    PRINT 'Nettoyage terminé - Logs antérieurs à ' + CONVERT(VARCHAR, @cutoff_date, 120) + ' supprimés';
END
GO

PRINT 'Procédure SP_ETL_CLEANUP_LOGS créée';
GO

PRINT '';
PRINT '══════════════════════════════════════════════════════════════════════════════';
PRINT ' INSTALLATION DES TABLES ETL TERMINÉE';
PRINT '══════════════════════════════════════════════════════════════════════════════';
