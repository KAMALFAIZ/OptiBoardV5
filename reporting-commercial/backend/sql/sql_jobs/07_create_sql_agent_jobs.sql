-- =====================================================================
-- 07_create_sql_agent_jobs.sql
-- Creation du Job SQL Server Agent : SYNC_GENERIC_MULTI
-- Architecture 3 bases : OptiBoard (config) -> DWH (cible) <- Sage (source)
-- A executer sur le SERVEUR SAGE (requiert SQL Server Agent actif)
-- =====================================================================
-- PREREQUIS :
--   1. SQL Server Agent doit etre demarre sur le serveur Sage
--   2. Le Linked Server vers le DWH doit etre cree (script 06)
--   3. Les tables ETL et SPs doivent exister sur le DWH
-- PARAMETRES :
--   {DWH_NAME}            = Nom de la base DWH (ex: DWH_ESSAIDI26)
--   {OPTIBOARD_DB}        = Nom de la base OptiBoard (ex: OptiBoard_ESSAIDI26)
--   {LINKED_SERVER_DWH}   = Nom du Linked Server vers le DWH (ex: DWH_ESSAIDI26)
-- =====================================================================

SET NOCOUNT ON;
GO

USE msdb;
SET NOCOUNT ON;

-- ═══════════════════════════════════════════════════════════════
-- VARIABLES A PERSONNALISER
-- ═══════════════════════════════════════════════════════════════
DECLARE @DWH_DB       NVARCHAR(100) = N'{DWH_NAME}';
DECLARE @OPTIBOARD_DB NVARCHAR(100) = N'{OPTIBOARD_DB}';
DECLARE @LS_DWH       NVARCHAR(200) = N'{LINKED_SERVER_DWH}';  -- Linked Server vers le DWH
DECLARE @OwnerLogin   NVARCHAR(100) = N'sa';
DECLARE @MailOperator NVARCHAR(100) = N'DBA_ETL';
DECLARE @ServerName   NVARCHAR(200) = N'(local)';

-- Prefixes pour acceder au DWH distant via Linked Server
DECLARE @DWH_PREFIX       NVARCHAR(500) = QUOTENAME(@LS_DWH) + N'.' + QUOTENAME(@DWH_DB);
DECLARE @OPTIBOARD_PREFIX NVARCHAR(500) = QUOTENAME(@LS_DWH) + N'.' + QUOTENAME(@OPTIBOARD_DB);

-- ═══════════════════════════════════════════════════════════════
-- NETTOYAGE : Supprimer les jobs existants
-- ═══════════════════════════════════════════════════════════════
DECLARE @JobNames TABLE (name NVARCHAR(200));
INSERT INTO @JobNames VALUES
    ('SYNC_GENERIC_MULTI'),
    ('ETL_Cleanup_Logs'),
    -- Anciens jobs v1 a supprimer si existants
    ('ETL_Sync_High_Priority'),
    ('ETL_Sync_Normal_Priority'),
    ('ETL_Sync_Low_Priority'),
    ('ETL_Sync_Full_Reload');

DECLARE @jn NVARCHAR(200);
DECLARE cur_del CURSOR LOCAL FAST_FORWARD FOR SELECT name FROM @JobNames;
OPEN cur_del;
FETCH NEXT FROM cur_del INTO @jn;
WHILE @@FETCH_STATUS = 0
BEGIN
    IF EXISTS (SELECT 1 FROM msdb.dbo.sysjobs WHERE name = @jn)
    BEGIN
        EXEC msdb.dbo.sp_delete_job @job_name = @jn, @delete_unused_schedule = 1;
        PRINT '-> Job "' + @jn + '" supprime';
    END
    FETCH NEXT FROM cur_del INTO @jn;
END
CLOSE cur_del;
DEALLOCATE cur_del;

-- ═══════════════════════════════════════════════════════════════
-- CREER L'OPERATEUR (si pas existant)
-- ═══════════════════════════════════════════════════════════════
IF NOT EXISTS (SELECT 1 FROM msdb.dbo.sysoperators WHERE name = @MailOperator)
BEGIN
    EXEC msdb.dbo.sp_add_operator
        @name                = @MailOperator,
        @enabled             = 1,
        @email_address       = N'dba@company.com';
    PRINT 'V Operateur "' + @MailOperator + '" cree';
END

-- ═══════════════════════════════════════════════════════════════
-- JOB 1 : SYNC_GENERIC_MULTI (Boucle infinie WHILE 1=1)
-- Tourne SUR le serveur Sage, accede au DWH via Linked Server
-- ═══════════════════════════════════════════════════════════════
DECLARE @SyncJobDesc NVARCHAR(500) = N'Synchronisation continue Sage -> DWH via Linked Server [' + @LS_DWH + N']. Tourne sur le serveur Sage, lit les donnees localement, ecrit dans le DWH distant.';

EXEC msdb.dbo.sp_add_job
    @job_name           = N'SYNC_GENERIC_MULTI',
    @enabled            = 1,
    @description        = @SyncJobDesc,
    @category_name      = N'[Uncategorized (Local)]',
    @owner_login_name   = @OwnerLogin,
    @notify_level_email = 2;

-- Le Step contient toute la logique WHILE 1=1
-- Les tables DWH sont accedees via le Linked Server
-- Les tables Sage sont accedees localement
-- IMPORTANT : Construction par blocs SET += pour eviter la troncature NVARCHAR(4000)
-- SQL Server tronque a 4000 cars si toute la concatenation est dans un seul DECLARE = N'...' + var + N'...'
DECLARE @JobCommand NVARCHAR(MAX) = CAST(N'' AS NVARCHAR(MAX));

-- ── Bloc 1 : En-tete et declarations de variables ──
SET @JobCommand = @JobCommand + N'
-- SYNC_GENERIC_MULTI - Boucle continue de synchronisation
-- Serveur Sage -> DWH distant via Linked Server ' + @LS_DWH + N'
-- Config:  ' + @OPTIBOARD_PREFIX + N'.dbo.ETL_Tables_Config
-- Sources: ' + @DWH_PREFIX + N'.dbo.ETL_Sources
-- SP:      dbo.sp_Sync_Generic_Local (locale sur Sage)

SET NOCOUNT ON;

DECLARE @SourceCode      VARCHAR(50);
DECLARE @SourceCaption   NVARCHAR(200);
DECLARE @DbId            INT;
DECLARE @DatabaseName    VARCHAR(100);
DECLARE @IsLinkedServer  BIT;
DECLARE @LinkedServerName VARCHAR(200);

DECLARE @TableName       NVARCHAR(100);
DECLARE @SourceQuery     NVARCHAR(MAX);
DECLARE @TargetTable     NVARCHAR(100);
DECLARE @JoinColumn      NVARCHAR(200);
DECLARE @FilterColumn    NVARCHAR(100);
DECLARE @SyncType        NVARCHAR(20);
DECLARE @TimestampColumn NVARCHAR(100);
DECLARE @DeleteOrphans   BIT;
DECLARE @Priority        NVARCHAR(20);

DECLARE @SourceSelect    NVARCHAR(MAX);
DECLARE @SyncControlName NVARCHAR(200);
DECLARE @CycleCount      INT = 0;
DECLARE @LastSync        DATETIME;
DECLARE @MinInterval     INT;

';

-- ── Bloc 2 : (vide - le prefixage est gere par la SP via USE @SourceDatabase) ──

-- ── Bloc 3 : Debut WHILE 1=1 et cursor sources ──
SET @JobCommand = @JobCommand + N'
WHILE 1 = 1
BEGIN
    BEGIN TRY
        SET @CycleCount = @CycleCount + 1;

        IF @CycleCount % 100 = 1
            PRINT CONVERT(VARCHAR, GETDATE(), 120) + '' | === CYCLE '' + CAST(@CycleCount AS VARCHAR) + '' ==='';

        -- Boucle sur les SOURCES (lues depuis le DWH via Linked Server)
        DECLARE cur_sources CURSOR LOCAL FAST_FORWARD FOR
            SELECT source_code, source_caption, db_id, database_name, is_linked_server, linked_server_name
            FROM ' + @DWH_PREFIX + N'.dbo.ETL_Sources
            WHERE is_active = 1
            ORDER BY db_id;

        OPEN cur_sources;
        FETCH NEXT FROM cur_sources INTO @SourceCode, @SourceCaption, @DbId, @DatabaseName, @IsLinkedServer, @LinkedServerName;

        WHILE @@FETCH_STATUS = 0
        BEGIN
            -- Boucle sur les TABLES (config lue depuis OptiBoard via Linked Server)
            DECLARE cur_tables CURSOR LOCAL FAST_FORWARD FOR
                SELECT table_name, source_query, target_table, join_column,
                       ISNULL(filter_column, ''DB''), sync_type, timestamp_column, ISNULL(delete_orphans, 0),
                       ISNULL(priority, ''normal'')
                FROM ' + @OPTIBOARD_PREFIX + N'.dbo.ETL_Tables_Config
                WHERE is_active = 1
                  AND source_query IS NOT NULL
                  AND source_query NOT LIKE ''TODO%''
                ORDER BY sort_order, table_name;

            OPEN cur_tables;
            FETCH NEXT FROM cur_tables INTO @TableName, @SourceQuery, @TargetTable, @JoinColumn,
                                            @FilterColumn, @SyncType, @TimestampColumn, @DeleteOrphans, @Priority;

';

-- ── Bloc 4 : Boucle tables (pas de prefixage - la SP fait USE @SourceDatabase) ──
SET @JobCommand = @JobCommand + N'
            WHILE @@FETCH_STATUS = 0
            BEGIN
                BEGIN TRY
                    SET @SourceSelect = @SourceQuery;

';

-- ── Bloc 5 : SyncControl + appel sp_Sync_Generic_Local + gestion erreurs + fin boucles ──
SET @JobCommand = @JobCommand + N'
                    SET @SyncControlName = @SourceCode + ''_'' + @TargetTable;

                    SET @LastSync = NULL;
                    SELECT @LastSync = LastSyncDate FROM ' + @DWH_PREFIX + N'.dbo.SyncControl
                        WHERE TableName = @SyncControlName;

                    SET @MinInterval = CASE @Priority
                        WHEN ''high'' THEN 5 WHEN ''normal'' THEN 15 WHEN ''low'' THEN 60 ELSE 15 END;

                    IF ISNULL(DATEDIFF(MINUTE, @LastSync, GETDATE()), 999) >= @MinInterval
                    BEGIN
                        EXEC dbo.sp_Sync_Generic_Local
                            @TargetTable      = @TargetTable,
                            @SourceSelect     = @SourceSelect,
                            @JoinColumn       = @JoinColumn,
                            @FilterColumn     = @FilterColumn,
                            @FilterValue      = @SourceCode,
                            @TimestampColumn  = @TimestampColumn,
                            @SyncControlName  = @SyncControlName,
                            @DeleteOrphans    = @DeleteOrphans,
                            @RemotePrefix     = N''' + @DWH_PREFIX + N''',
                            @SourceDatabase   = @DatabaseName,
                            @SourceDbId       = @DbId,
                            @SourceCaption    = @SourceCaption;
                    END

                END TRY
                BEGIN CATCH
                    PRINT CONVERT(VARCHAR, GETDATE(), 120) + '' | X '' + @SourceCode + ''.'' + @TableName
                        + '' | ERREUR: '' + ERROR_MESSAGE();
                    WAITFOR DELAY ''00:00:30'';
                END CATCH

                FETCH NEXT FROM cur_tables INTO @TableName, @SourceQuery, @TargetTable, @JoinColumn,
                                                @FilterColumn, @SyncType, @TimestampColumn, @DeleteOrphans, @Priority;
            END

            CLOSE cur_tables;
            DEALLOCATE cur_tables;

            FETCH NEXT FROM cur_sources INTO @SourceCode, @SourceCaption, @DbId, @DatabaseName, @IsLinkedServer, @LinkedServerName;
        END

        CLOSE cur_sources;
        DEALLOCATE cur_sources;

        WAITFOR DELAY ''00:00:05'';

    END TRY
    BEGIN CATCH
        PRINT CONVERT(VARCHAR, GETDATE(), 120) + '' | === ERREUR CYCLE: '' + ERROR_MESSAGE() + '' ==='';

        BEGIN TRY CLOSE cur_tables; DEALLOCATE cur_tables; END TRY BEGIN CATCH END CATCH
        BEGIN TRY CLOSE cur_sources; DEALLOCATE cur_sources; END TRY BEGIN CATCH END CATCH

        WAITFOR DELAY ''00:00:30'';
    END CATCH
END
';

-- Verifier la taille du @JobCommand (debug)
PRINT 'Taille @JobCommand: ' + CAST(LEN(@JobCommand) AS VARCHAR) + ' caracteres';

EXEC msdb.dbo.sp_add_jobstep
    @job_name        = N'SYNC_GENERIC_MULTI',
    @step_name       = N'Boucle Sync Continue',
    @step_id         = 1,
    @subsystem       = N'TSQL',
    @command          = @JobCommand,
    @database_name   = N'master',
    @retry_attempts  = 0,
    @retry_interval  = 0,
    @on_success_action = 1,
    @on_fail_action    = 2;

-- Schedule : demarrage au lancement de SQL Agent
EXEC msdb.dbo.sp_add_jobschedule
    @job_name            = N'SYNC_GENERIC_MULTI',
    @name                = N'Start_On_Agent_Start',
    @enabled             = 1,
    @freq_type           = 64,
    @freq_interval       = 0,
    @freq_subday_type    = 0,
    @freq_subday_interval = 0,
    @active_start_time   = 0;

EXEC msdb.dbo.sp_add_jobserver
    @job_name    = N'SYNC_GENERIC_MULTI',
    @server_name = @ServerName;

PRINT 'V Job "SYNC_GENERIC_MULTI" cree sur le serveur Sage (accede au DWH via [' + @LS_DWH + '])';

-- ═══════════════════════════════════════════════════════════════
-- JOB 2 : ETL_Cleanup_Logs (1x/semaine dimanche 03:00)
-- Execute la SP de cleanup sur le DWH distant
-- ═══════════════════════════════════════════════════════════════
DECLARE @CleanupJobDesc NVARCHAR(500) = N'Purge des logs ETL de plus de 90 jours sur le DWH via [' + @LS_DWH + N'] (dimanche 03:00)';

EXEC msdb.dbo.sp_add_job
    @job_name           = N'ETL_Cleanup_Logs',
    @enabled            = 1,
    @description        = @CleanupJobDesc,
    @category_name      = N'[Uncategorized (Local)]',
    @owner_login_name   = @OwnerLogin;

DECLARE @CleanupCmd NVARCHAR(MAX) = N'EXEC ' + @DWH_PREFIX + N'.dbo.SP_ETL_Cleanup_Logs @RetentionDays = 90';

EXEC msdb.dbo.sp_add_jobstep
    @job_name        = N'ETL_Cleanup_Logs',
    @step_name       = N'Cleanup Logs',
    @step_id         = 1,
    @subsystem       = N'TSQL',
    @command          = @CleanupCmd,
    @database_name   = N'master',
    @on_success_action = 1,
    @on_fail_action    = 2;

EXEC msdb.dbo.sp_add_jobschedule
    @job_name            = N'ETL_Cleanup_Logs',
    @name                = N'Weekly_Sunday_0300',
    @enabled             = 1,
    @freq_type           = 8,
    @freq_interval       = 1,
    @freq_recurrence_factor = 1,
    @active_start_time   = 030000;

EXEC msdb.dbo.sp_add_jobserver
    @job_name    = N'ETL_Cleanup_Logs',
    @server_name = @ServerName;

PRINT 'V Job "ETL_Cleanup_Logs" cree (dimanche 03:00)';

-- ═══════════════════════════════════════════════════════════════
-- RESUME
-- ═══════════════════════════════════════════════════════════════
PRINT '';
PRINT '==============================================================';
PRINT ' 2 SQL AGENT JOBS CREES SUR LE SERVEUR SAGE';
PRINT '==============================================================';
PRINT '';
PRINT ' Linked Server DWH : ' + @LS_DWH;
PRINT ' DWH distant :       ' + @DWH_DB;
PRINT ' OptiBoard :         ' + @OPTIBOARD_DB;
PRINT '';
PRINT ' Job                    | Description';
PRINT ' -------------------------------------------------------';
PRINT ' SYNC_GENERIC_MULTI     | Boucle WHILE 1=1 continue';
PRINT '                        | Lit Sage LOCAL, ecrit DWH DISTANT';
PRINT '                        | via [' + @LS_DWH + ']';
PRINT ' -------------------------------------------------------';
PRINT ' ETL_Cleanup_Logs       | Purge logs > 90 jours';
PRINT '                        | Dimanche 03:00';
PRINT '==============================================================';
GO
