-- =====================================================================
-- 05_sp_etl_orchestrators.sql
-- Procedures utilitaires ETL (architecture 3 bases)
-- A executer dans la base DWH
-- =====================================================================
-- PROCEDURES :
--   1. SP_ETL_Setup_Source     : Initialiser une nouvelle source Sage
--   2. SP_ETL_Cleanup_Logs     : Purger les anciens logs et alertes
--   3. SP_ETL_Reset_SyncControl: Forcer un full sync (reset watermarks)
-- =====================================================================
-- NOTE : Les orchestrateurs (Sync_Source, Sync_By_Priority, Sync_All)
--        sont SUPPRIMES — la boucle WHILE 1=1 du Job SQL Agent
--        (07_create_sql_agent_jobs.sql) gere l'iteration directement.
--        Le verrou is_syncing est egalement supprime (SyncControl).
-- =====================================================================
-- VARIABLES A REMPLACER :
--   {DWH_NAME}  -> nom de votre base DWH (ex: DWH_Alboughaze)
-- =====================================================================

SET NOCOUNT ON;
GO

-- NOTE: Chaque batch inclut son propre USE pour garantir le contexte DB
--       meme si pyodbc ne propage pas le USE entre cursor.execute() calls.

-- =====================================================================
-- 1. SP_ETL_Setup_Source - Initialiser une nouvelle source Sage
-- =====================================================================
USE [{DWH_NAME}];
PRINT '══════════════════════════════════════════════════════════════';
PRINT ' CREATION DES PROCEDURES UTILITAIRES ETL';
PRINT '══════════════════════════════════════════════════════════════';
IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'SP_ETL_Setup_Source')
    DROP PROCEDURE SP_ETL_Setup_Source;
GO

USE [{DWH_NAME}];
CREATE PROCEDURE dbo.SP_ETL_Setup_Source
    @SourceCode       VARCHAR(50),
    @SourceCaption    NVARCHAR(200),
    @DbId             INT,
    @ServerName       VARCHAR(200),
    @DatabaseName     VARCHAR(100),
    @IsLinkedServer   BIT = 0,
    @LinkedServerName VARCHAR(200) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    -- Inserer ou mettre a jour la source
    IF EXISTS (SELECT 1 FROM ETL_Sources WHERE source_code = @SourceCode)
    BEGIN
        UPDATE ETL_Sources
        SET source_caption     = @SourceCaption,
            db_id              = @DbId,
            server_name        = @ServerName,
            database_name      = @DatabaseName,
            is_linked_server   = @IsLinkedServer,
            linked_server_name = @LinkedServerName,
            is_active          = 1,
            updated_at         = GETDATE()
        WHERE source_code = @SourceCode;

        PRINT 'V Source "' + @SourceCode + '" mise a jour';
    END
    ELSE
    BEGIN
        INSERT INTO ETL_Sources (source_code, source_caption, db_id, server_name, database_name, is_linked_server, linked_server_name)
        VALUES (@SourceCode, @SourceCaption, @DbId, @ServerName, @DatabaseName, @IsLinkedServer, @LinkedServerName);

        PRINT 'V Source "' + @SourceCode + '" creee';
    END

    -- NOTE : SyncControl est cree paresseusement par sp_Sync_Generic
    --        au premier appel pour chaque source x table.
    --        Pas besoin d'initialiser ici.

    PRINT 'V Source "' + @SourceCode + '" prete';
    PRINT '  Base Sage : ' + @DatabaseName;
    PRINT '  Serveur   : ' + @ServerName;
    PRINT '  Mode      : ' + CASE WHEN @IsLinkedServer = 1 THEN 'Linked Server (' + ISNULL(@LinkedServerName, '?') + ')' ELSE 'Local (meme serveur)' END;
END;
GO

USE [{DWH_NAME}];
PRINT 'V Procedure SP_ETL_Setup_Source creee';
GO

-- =====================================================================
-- 2. SP_ETL_Cleanup_Logs - Purger les anciens logs et alertes
-- =====================================================================
USE [{DWH_NAME}];
IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'SP_ETL_Cleanup_Logs')
    DROP PROCEDURE SP_ETL_Cleanup_Logs;
GO

USE [{DWH_NAME}];
CREATE PROCEDURE dbo.SP_ETL_Cleanup_Logs
    @RetentionDays INT = 90
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @CutoffDate DATETIME2 = DATEADD(DAY, -@RetentionDays, GETDATE());
    DECLARE @LogsDeleted INT;
    DECLARE @AlertsDeleted INT;
    DECLARE @SyncControlCleaned INT;

    -- Purger les anciens logs de sync
    DELETE FROM ETL_Sync_Log WHERE started_at < @CutoffDate;
    SET @LogsDeleted = @@ROWCOUNT;

    -- Purger les alertes acquittees de plus de @RetentionDays jours
    DELETE FROM ETL_Alerts WHERE is_acknowledged = 1 AND alert_time < @CutoffDate;
    SET @AlertsDeleted = @@ROWCOUNT;

    -- Nettoyer les entrees SyncControl orphelines
    -- (source_code n'existe plus dans ETL_Sources)
    DELETE sc FROM SyncControl sc
    WHERE NOT EXISTS (
        SELECT 1 FROM ETL_Sources es
        WHERE es.is_active = 1
          AND sc.TableName LIKE es.source_code + '_%'
    );
    SET @SyncControlCleaned = @@ROWCOUNT;

    PRINT 'V Nettoyage termine:';
    PRINT '  Logs supprimes:         ' + CAST(@LogsDeleted AS VARCHAR);
    PRINT '  Alertes purgees:        ' + CAST(@AlertsDeleted AS VARCHAR);
    PRINT '  SyncControl nettoyees:  ' + CAST(@SyncControlCleaned AS VARCHAR);
    PRINT '  Retention:              ' + CAST(@RetentionDays AS VARCHAR) + ' jours';
END;
GO

USE [{DWH_NAME}];
PRINT 'V Procedure SP_ETL_Cleanup_Logs creee';
GO

-- =====================================================================
-- 3. SP_ETL_Reset_SyncControl - Forcer un full sync
--    Remet LastSyncDate a NULL pour forcer un rechargement complet
--    au prochain cycle du Job WHILE 1=1
-- =====================================================================
USE [{DWH_NAME}];
IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'SP_ETL_Reset_SyncControl')
    DROP PROCEDURE SP_ETL_Reset_SyncControl;
GO

USE [{DWH_NAME}];
CREATE PROCEDURE dbo.SP_ETL_Reset_SyncControl
    @SourceCode    VARCHAR(50)  = NULL,   -- NULL = toutes les sources
    @TargetTable   NVARCHAR(100) = NULL,  -- NULL = toutes les tables
    @ResetCounters BIT = 0                -- 1 = remettre aussi les compteurs a zero
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @Affected INT;

    IF @ResetCounters = 1
    BEGIN
        UPDATE SyncControl
        SET LastSyncDate     = NULL,
            TotalInserted    = 0,
            TotalUpdated     = 0,
            TotalDeleted     = 0,
            LastStatus       = NULL,
            LastError        = NULL,
            LastSyncDuration = NULL
        WHERE (@SourceCode IS NULL OR TableName LIKE @SourceCode + '_%')
          AND (@TargetTable IS NULL OR TableName LIKE '%_' + @TargetTable);
    END
    ELSE
    BEGIN
        UPDATE SyncControl
        SET LastSyncDate = NULL,
            LastStatus   = NULL,
            LastError    = NULL
        WHERE (@SourceCode IS NULL OR TableName LIKE @SourceCode + '_%')
          AND (@TargetTable IS NULL OR TableName LIKE '%_' + @TargetTable);
    END

    SET @Affected = @@ROWCOUNT;

    PRINT 'V ' + CAST(@Affected AS VARCHAR) + ' entree(s) SyncControl remise(s) a zero';
    PRINT '  Source    : ' + ISNULL(@SourceCode, 'TOUTES');
    PRINT '  Table     : ' + ISNULL(@TargetTable, 'TOUTES');
    PRINT '  Compteurs : ' + CASE WHEN @ResetCounters = 1 THEN 'Remis a zero' ELSE 'Conserves' END;
    PRINT '  -> Le prochain cycle du Job effectuera un FULL SYNC';
END;
GO

USE [{DWH_NAME}];
PRINT 'V Procedure SP_ETL_Reset_SyncControl creee';
GO

-- =====================================================================
-- NETTOYAGE : Supprimer les anciennes procedures v1 si elles existent
-- =====================================================================
USE [{DWH_NAME}];
IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'SP_ETL_Sync_Source')
BEGIN
    DROP PROCEDURE SP_ETL_Sync_Source;
    PRINT '  -> Ancienne SP_ETL_Sync_Source supprimee';
END

IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'SP_ETL_Sync_By_Priority')
BEGIN
    DROP PROCEDURE SP_ETL_Sync_By_Priority;
    PRINT '  -> Ancienne SP_ETL_Sync_By_Priority supprimee';
END

IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'SP_ETL_Sync_All')
BEGIN
    DROP PROCEDURE SP_ETL_Sync_All;
    PRINT '  -> Ancienne SP_ETL_Sync_All supprimee';
END

IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'SP_ETL_Reset_Lock')
BEGIN
    DROP PROCEDURE SP_ETL_Reset_Lock;
    PRINT '  -> Ancienne SP_ETL_Reset_Lock supprimee';
END

IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'SP_ETL_Sync_Table')
BEGIN
    DROP PROCEDURE SP_ETL_Sync_Table;
    PRINT '  -> Ancienne SP_ETL_Sync_Table supprimee (remplacee par sp_Sync_Generic)';
END
GO

USE [{DWH_NAME}];
PRINT '';
PRINT '══════════════════════════════════════════════════════════════';
PRINT ' PROCEDURES UTILITAIRES ETL CREEES';
PRINT '  - SP_ETL_Setup_Source       (initialiser une source Sage)';
PRINT '  - SP_ETL_Cleanup_Logs       (purge logs + alertes)';
PRINT '  - SP_ETL_Reset_SyncControl  (forcer full sync)';
PRINT '';
PRINT ' ANCIENNES PROCEDURES SUPPRIMEES (v1) :';
PRINT '  - SP_ETL_Sync_Source, Sync_By_Priority, Sync_All';
PRINT '  - SP_ETL_Reset_Lock, SP_ETL_Sync_Table';
PRINT '══════════════════════════════════════════════════════════════';
