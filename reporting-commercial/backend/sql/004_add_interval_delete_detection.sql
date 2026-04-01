-- =====================================================
-- Script d'ajout des colonnes interval_minutes et delete_detection
-- Pour la synchronisation personnalisee par table
-- Base: OptiBoard_SaaS
-- =====================================================

USE OptiBoard_SaaS;
GO

-- =====================================================
-- 1. Ajouter les colonnes a APP_ETL_Agent_Tables
-- =====================================================

-- Colonne interval_minutes (intervalle de sync en minutes)
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('APP_ETL_Agent_Tables') AND name = 'interval_minutes')
BEGIN
    ALTER TABLE APP_ETL_Agent_Tables ADD interval_minutes INT DEFAULT 5;
    PRINT 'Colonne interval_minutes ajoutee a APP_ETL_Agent_Tables';
END
GO

-- Colonne delete_detection (activer la detection des suppressions)
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('APP_ETL_Agent_Tables') AND name = 'delete_detection')
BEGIN
    ALTER TABLE APP_ETL_Agent_Tables ADD delete_detection BIT DEFAULT 0;
    PRINT 'Colonne delete_detection ajoutee a APP_ETL_Agent_Tables';
END
GO

-- Colonne last_sync_at (derniere synchronisation effectuee pour cette table)
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('APP_ETL_Agent_Tables') AND name = 'last_sync_at')
BEGIN
    ALTER TABLE APP_ETL_Agent_Tables ADD last_sync_at DATETIME NULL;
    PRINT 'Colonne last_sync_at ajoutee a APP_ETL_Agent_Tables';
END
GO

-- Colonne last_delete_check_at (derniere verification des suppressions)
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('APP_ETL_Agent_Tables') AND name = 'last_delete_check_at')
BEGIN
    ALTER TABLE APP_ETL_Agent_Tables ADD last_delete_check_at DATETIME NULL;
    PRINT 'Colonne last_delete_check_at ajoutee a APP_ETL_Agent_Tables';
END
GO

-- =====================================================
-- 2. Ajouter les colonnes a ETL_Tables_Config (config globale)
-- =====================================================

IF EXISTS (SELECT * FROM sysobjects WHERE name='ETL_Tables_Config' AND xtype='U')
BEGIN
    -- Colonne interval_minutes
    IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('ETL_Tables_Config') AND name = 'interval_minutes')
    BEGIN
        ALTER TABLE ETL_Tables_Config ADD interval_minutes INT DEFAULT 5;
        PRINT 'Colonne interval_minutes ajoutee a ETL_Tables_Config';
    END

    -- Colonne delete_detection
    IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('ETL_Tables_Config') AND name = 'delete_detection')
    BEGIN
        ALTER TABLE ETL_Tables_Config ADD delete_detection BIT DEFAULT 0;
        PRINT 'Colonne delete_detection ajoutee a ETL_Tables_Config';
    END
END
GO

-- =====================================================
-- 3. Table de log des suppressions detectees
-- =====================================================

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Deletion_Log' AND xtype='U')
CREATE TABLE APP_ETL_Deletion_Log (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    agent_id UNIQUEIDENTIFIER NOT NULL,
    table_name NVARCHAR(100) NOT NULL,
    societe_code VARCHAR(50) NOT NULL,
    -- Stats de la detection
    detected_at DATETIME DEFAULT GETDATE(),
    source_count INT NOT NULL,              -- Nombre d'IDs cote source
    destination_count INT NOT NULL,         -- Nombre d'IDs cote destination avant suppression
    deleted_count INT NOT NULL,             -- Nombre de lignes supprimees
    duration_ms INT NULL,                   -- Duree de l'operation en ms
    -- Info
    status VARCHAR(20) DEFAULT 'success',   -- success/error
    error_message NVARCHAR(MAX) NULL,
    CONSTRAINT FK_Deletion_Log_Agent FOREIGN KEY (agent_id) REFERENCES APP_ETL_Agents(agent_id) ON DELETE CASCADE
);
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_Deletion_Log_agent_table')
    CREATE INDEX IX_Deletion_Log_agent_table ON APP_ETL_Deletion_Log(agent_id, table_name);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_Deletion_Log_detected_at')
    CREATE INDEX IX_Deletion_Log_detected_at ON APP_ETL_Deletion_Log(detected_at DESC);
GO

PRINT 'Table APP_ETL_Deletion_Log creee';
GO

-- =====================================================
-- 4. Vue pour le statut des tables avec intervalles
-- =====================================================

IF EXISTS (SELECT * FROM sys.views WHERE name = 'VW_ETL_Tables_Sync_Status')
    DROP VIEW VW_ETL_Tables_Sync_Status;
GO

CREATE VIEW VW_ETL_Tables_Sync_Status AS
SELECT
    t.id,
    t.agent_id,
    a.name AS agent_name,
    t.table_name,
    t.societe_code,
    t.sync_type,
    t.priority,
    t.is_enabled,
    t.interval_minutes,
    t.delete_detection,
    t.last_sync_at,
    t.last_delete_check_at,
    t.last_sync_status,
    t.last_sync_rows,
    -- Calcul si sync necessaire
    CASE
        WHEN t.is_enabled = 0 THEN 'Desactive'
        WHEN t.last_sync_at IS NULL THEN 'Jamais synchronise'
        WHEN DATEDIFF(MINUTE, t.last_sync_at, GETDATE()) >= ISNULL(t.interval_minutes, 5) THEN 'Sync necessaire'
        ELSE 'A jour'
    END AS sync_status,
    -- Minutes depuis derniere sync
    DATEDIFF(MINUTE, t.last_sync_at, GETDATE()) AS minutes_since_last_sync,
    -- Prochaine sync prevue
    DATEADD(MINUTE, ISNULL(t.interval_minutes, 5), t.last_sync_at) AS next_sync_expected
FROM APP_ETL_Agent_Tables t
INNER JOIN APP_ETL_Agents a ON t.agent_id = a.agent_id;
GO

PRINT 'Vue VW_ETL_Tables_Sync_Status creee';
GO

-- =====================================================
-- 5. Procedure pour obtenir les tables a synchroniser
-- =====================================================

IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'SP_ETL_Get_Tables_To_Sync')
    DROP PROCEDURE SP_ETL_Get_Tables_To_Sync;
GO

CREATE PROCEDURE SP_ETL_Get_Tables_To_Sync
    @agent_id UNIQUEIDENTIFIER
AS
BEGIN
    SET NOCOUNT ON;

    -- Retourne les tables dont l'intervalle est atteint
    SELECT
        t.id,
        t.table_name,
        t.source_query,
        t.target_table,
        t.societe_code,
        t.primary_key_columns,
        t.sync_type,
        t.timestamp_column,
        t.last_sync_timestamp,
        t.priority,
        t.interval_minutes,
        t.delete_detection,
        t.last_sync_at,
        t.batch_size
    FROM APP_ETL_Agent_Tables t
    WHERE t.agent_id = @agent_id
      AND t.is_enabled = 1
      AND (
          t.last_sync_at IS NULL
          OR DATEDIFF(MINUTE, t.last_sync_at, GETDATE()) >= ISNULL(t.interval_minutes, 5)
      )
    ORDER BY
        CASE t.priority
            WHEN 'high' THEN 1
            WHEN 'normal' THEN 2
            WHEN 'low' THEN 3
            ELSE 4
        END,
        t.table_name;
END
GO

PRINT 'Procedure SP_ETL_Get_Tables_To_Sync creee';
GO

-- =====================================================
-- 6. Procedure pour marquer une table comme synchronisee
-- =====================================================

IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'SP_ETL_Mark_Table_Synced')
    DROP PROCEDURE SP_ETL_Mark_Table_Synced;
GO

CREATE PROCEDURE SP_ETL_Mark_Table_Synced
    @agent_id UNIQUEIDENTIFIER,
    @table_name NVARCHAR(100),
    @societe_code VARCHAR(50),
    @rows_synced INT = 0,
    @last_timestamp NVARCHAR(50) = NULL,
    @status VARCHAR(20) = 'success',
    @error_message NVARCHAR(MAX) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    UPDATE APP_ETL_Agent_Tables
    SET
        last_sync_at = GETDATE(),
        last_sync = GETDATE(),
        last_sync_status = @status,
        last_sync_rows = @rows_synced,
        last_sync_timestamp = COALESCE(@last_timestamp, last_sync_timestamp),
        last_error = @error_message,
        updated_at = GETDATE()
    WHERE agent_id = @agent_id
      AND table_name = @table_name
      AND (societe_code = @societe_code OR @societe_code IS NULL);

    SELECT @@ROWCOUNT AS rows_updated;
END
GO

PRINT 'Procedure SP_ETL_Mark_Table_Synced creee';
GO

-- =====================================================
-- 7. Procedure pour enregistrer une detection de suppressions
-- =====================================================

IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'SP_ETL_Log_Deletion_Check')
    DROP PROCEDURE SP_ETL_Log_Deletion_Check;
GO

CREATE PROCEDURE SP_ETL_Log_Deletion_Check
    @agent_id UNIQUEIDENTIFIER,
    @table_name NVARCHAR(100),
    @societe_code VARCHAR(50),
    @source_count INT,
    @destination_count INT,
    @deleted_count INT,
    @duration_ms INT = NULL,
    @status VARCHAR(20) = 'success',
    @error_message NVARCHAR(MAX) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    -- Inserer le log
    INSERT INTO APP_ETL_Deletion_Log (
        agent_id, table_name, societe_code,
        source_count, destination_count, deleted_count,
        duration_ms, status, error_message
    )
    VALUES (
        @agent_id, @table_name, @societe_code,
        @source_count, @destination_count, @deleted_count,
        @duration_ms, @status, @error_message
    );

    -- Mettre a jour last_delete_check_at
    UPDATE APP_ETL_Agent_Tables
    SET last_delete_check_at = GETDATE(), updated_at = GETDATE()
    WHERE agent_id = @agent_id
      AND table_name = @table_name
      AND (societe_code = @societe_code OR @societe_code IS NULL);

    SELECT SCOPE_IDENTITY() AS log_id;
END
GO

PRINT 'Procedure SP_ETL_Log_Deletion_Check creee';
GO

-- =====================================================
-- 8. Mettre a jour les valeurs par defaut existantes
-- =====================================================

-- Mettre interval_minutes = 5 pour les tables sans valeur
UPDATE APP_ETL_Agent_Tables
SET interval_minutes = 5
WHERE interval_minutes IS NULL;

-- Mettre delete_detection = 0 pour les tables sans valeur
UPDATE APP_ETL_Agent_Tables
SET delete_detection = 0
WHERE delete_detection IS NULL;

PRINT 'Valeurs par defaut mises a jour';
GO

-- =====================================================
PRINT '';
PRINT '=====================================================';
PRINT ' COLONNES INTERVAL ET DELETE DETECTION AJOUTEES';
PRINT '=====================================================';
PRINT ' - APP_ETL_Agent_Tables.interval_minutes';
PRINT ' - APP_ETL_Agent_Tables.delete_detection';
PRINT ' - APP_ETL_Agent_Tables.last_sync_at';
PRINT ' - APP_ETL_Agent_Tables.last_delete_check_at';
PRINT ' - Table APP_ETL_Deletion_Log creee';
PRINT ' - Vue VW_ETL_Tables_Sync_Status creee';
PRINT ' - Procedures SP_ETL_* creees';
PRINT '=====================================================';
GO
