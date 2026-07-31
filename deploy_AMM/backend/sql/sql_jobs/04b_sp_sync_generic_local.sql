-- =====================================================================
-- 04b_sp_sync_generic_local.sql
-- PROCEDURE GENERIQUE : sp_Sync_Generic_Local
-- S'execute SUR LE SERVEUR SAGE (pas le DWH)
-- Lit les donnees Sage localement, ecrit dans le DWH via Linked Server
-- Utilise DELETE+INSERT (pas MERGE) pour eviter MSDTC
-- =====================================================================
-- PATTERN :
--   - Les tables SOURCE (Sage) sont accessibles localement
--   - Les tables CIBLE (DWH) sont accedees via @RemotePrefix (Linked Server)
--   - SyncControl, ETL_Sync_Log, ETL_Alerts sont sur le DWH (via @RemotePrefix)
--   - INFORMATION_SCHEMA est lu sur le DWH distant pour decouvrir les colonnes
-- =====================================================================
-- PARAMETRES DE DEPLOIEMENT :
--   Aucun placeholder {DWH_NAME} - la SP est creee dans master sur Sage
-- =====================================================================

SET NOCOUNT ON;
GO

-- Batch 1 : DROP ancienne SP si existe (sur Sage, dans master)
USE master;
IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'sp_Sync_Generic_Local')
    DROP PROCEDURE sp_Sync_Generic_Local;
GO

-- Batch 2 : CREATE PROCEDURE (pas de USE ici, CREATE PROCEDURE doit etre la 1ere instruction)
CREATE PROCEDURE dbo.sp_Sync_Generic_Local
    @TargetTable      NVARCHAR(200),         -- Table cible DWH (ex: 'Collaborateurs')
    @SourceSelect     NVARCHAR(MAX),         -- SELECT brut (sans prefixes DB - on fera USE @SourceDatabase)
    @JoinColumn       NVARCHAR(200),         -- Colonne PK pour ON (ex: 'Code collaborateur')
    @FilterColumn     NVARCHAR(100),         -- Colonne multi-source (ex: 'DB')
    @FilterValue      NVARCHAR(200),         -- Valeur source (ex: 'ESSAIDI2022')
    @TimestampColumn  NVARCHAR(100) = NULL,  -- Colonne pour sync incremental
    @SyncControlName  NVARCHAR(200),         -- Cle dans SyncControl
    @DeleteOrphans    BIT = 0,               -- Supprimer les orphelins ?
    @RemotePrefix     NVARCHAR(500),         -- Prefixe LS vers DWH (ex: '[DWH_ESSAIDI26].[DWH_ESSAIDI26]')
    @SourceDatabase   NVARCHAR(200) = NULL,  -- Base Sage locale (ex: 'ESSAIDI2022') - si NULL utilise @FilterValue
    @SourceDbId       INT = 0,               -- db_id de ETL_Sources (pour colonne DWH DB_Id)
    @SourceCaption    NVARCHAR(200) = N''    -- source_caption de ETL_Sources (pour colonne DWH DB_Caption)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT OFF;

    -- Resoudre le nom de la base source Sage
    IF @SourceDatabase IS NULL SET @SourceDatabase = @FilterValue;

    -- =================================================================
    -- VARIABLES
    -- =================================================================
    DECLARE @StartTime       DATETIME2;
    SET @StartTime = GETDATE();
    DECLARE @LastSyncDate    DATETIME;
    DECLARE @LogId           BIGINT;
    DECLARE @ActualSyncType  NVARCHAR(20);

    -- Colonnes dynamiques (lues depuis le DWH distant)
    DECLARE @ColList          NVARCHAR(MAX);
    DECLARE @InsertCols       NVARCHAR(MAX);
    DECLARE @InsertVals       NVARCHAR(MAX);

    -- Compteurs
    DECLARE @RowsInserted    INT;
    DECLARE @RowsUpdated     INT;
    DECLARE @RowsDeleted     INT;
    DECLARE @RowsExtracted   INT;
    SET @RowsInserted = 0;
    SET @RowsUpdated  = 0;
    SET @RowsDeleted  = 0;
    SET @RowsExtracted = 0;

    DECLARE @SQL             NVARCHAR(MAX);
    DECLARE @ErrorMsg        NVARCHAR(MAX);

    -- Prefixes pour les tables distantes
    DECLARE @RemoteSyncControl NVARCHAR(600);
    DECLARE @RemoteSyncLog     NVARCHAR(600);
    DECLARE @RemoteAlerts      NVARCHAR(600);
    DECLARE @RemoteTarget      NVARCHAR(600);
    DECLARE @RemoteInfoSchema  NVARCHAR(600);
    SET @RemoteSyncControl = @RemotePrefix + N'.dbo.SyncControl';
    SET @RemoteSyncLog     = @RemotePrefix + N'.dbo.ETL_Sync_Log';
    SET @RemoteAlerts      = @RemotePrefix + N'.dbo.ETL_Alerts';
    SET @RemoteTarget      = @RemotePrefix + N'.dbo.' + QUOTENAME(@TargetTable);
    SET @RemoteInfoSchema  = @RemotePrefix + N'.INFORMATION_SCHEMA.COLUMNS';

    -- =================================================================
    -- 1. LIRE / INITIALISER SyncControl (sur DWH distant)
    -- =================================================================

    -- Verifier si l'entree SyncControl existe, sinon la creer
    SET @SQL = N'IF NOT EXISTS (SELECT 1 FROM ' + @RemoteSyncControl + N' WHERE TableName = @scn)
        INSERT INTO ' + @RemoteSyncControl + N' (TableName) VALUES (@scn)';
    EXEC sp_executesql @SQL, N'@scn NVARCHAR(200)', @scn = @SyncControlName;

    -- Lire la derniere date de sync
    SET @SQL = N'SELECT @lsd = LastSyncDate FROM ' + @RemoteSyncControl + N' WHERE TableName = @scn';
    EXEC sp_executesql @SQL, N'@scn NVARCHAR(200), @lsd DATETIME OUTPUT',
        @scn = @SyncControlName, @lsd = @LastSyncDate OUTPUT;

    -- Determiner le type de sync effectif
    SET @ActualSyncType = CASE
        WHEN @TimestampColumn IS NOT NULL AND @LastSyncDate IS NOT NULL THEN 'incremental'
        ELSE 'full'
    END;

    -- =================================================================
    -- 2. LOG DEBUT (sur DWH distant)
    -- =================================================================
    DECLARE @WatermarkBefore NVARCHAR(100);
    IF @LastSyncDate IS NOT NULL
        SET @WatermarkBefore = CONVERT(NVARCHAR(100), @LastSyncDate, 126);

    SET @SQL = N'INSERT INTO ' + @RemoteSyncLog
        + N' (sync_control_name, source_code, table_name, sync_type, started_at, status, watermark_before)'
        + N' VALUES (@scn, @fv, @tt, @st, @start, ''running'', @wb)';
    EXEC sp_executesql @SQL,
        N'@scn NVARCHAR(200), @fv NVARCHAR(200), @tt NVARCHAR(200), @st NVARCHAR(20), @start DATETIME2, @wb NVARCHAR(100)',
        @scn = @SyncControlName, @fv = @FilterValue, @tt = @TargetTable,
        @st = @ActualSyncType, @start = @StartTime,
        @wb = @WatermarkBefore;

    -- Recuperer le LogId via MAX(id) car SCOPE_IDENTITY() ne fonctionne pas cross-LS
    SET @SQL = N'SELECT @lid = MAX(id) FROM ' + @RemoteSyncLog
        + N' WHERE sync_control_name = @scn AND status = ''running''';
    EXEC sp_executesql @SQL, N'@scn NVARCHAR(200), @lid BIGINT OUTPUT',
        @scn = @SyncControlName, @lid = @LogId OUTPUT;

    -- =================================================================
    -- DEBUT TRY/CATCH
    -- =================================================================
    BEGIN TRY

        -- =============================================================
        -- 3. DECOUVERTE DES COLONNES via INFORMATION_SCHEMA (DWH distant)
        -- =============================================================

        -- Recuperer la liste des colonnes de la table cible DWH (sauf 'id' identity)
        -- On inclut le type pour pouvoir creer #staging avec CREATE TABLE
        IF OBJECT_ID('tempdb..#remote_cols') IS NOT NULL DROP TABLE #remote_cols;
        CREATE TABLE #remote_cols (
            COLUMN_NAME NVARCHAR(128),
            ORDINAL_POSITION INT,
            DATA_TYPE NVARCHAR(128),
            CHARACTER_MAXIMUM_LENGTH INT,
            NUMERIC_PRECISION TINYINT,
            NUMERIC_SCALE INT,
            IsIdentity BIT DEFAULT 0
        );

        SET @SQL = N'INSERT INTO #remote_cols (COLUMN_NAME, ORDINAL_POSITION, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, NUMERIC_PRECISION, NUMERIC_SCALE)
            SELECT COLUMN_NAME, ORDINAL_POSITION, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, NUMERIC_PRECISION, NUMERIC_SCALE
            FROM ' + @RemoteInfoSchema + N'
            WHERE TABLE_NAME = @tt AND TABLE_SCHEMA = ''dbo''
              AND COLUMN_NAME <> ''id''
              AND COLUMN_NAME NOT IN (''DB_Id'', ''DB'', ''DB_Caption'', ''SyncDate'', ''cbCreation'', ''cbModification'')
            ORDER BY ORDINAL_POSITION';
        EXEC sp_executesql @SQL, N'@tt NVARCHAR(200)', @tt = @TargetTable;

        -- Construire la liste des colonnes
        SELECT @ColList = STRING_AGG(QUOTENAME(COLUMN_NAME), ', ')
                          WITHIN GROUP (ORDER BY ORDINAL_POSITION)
        FROM #remote_cols;

        IF @ColList IS NULL
        BEGIN
            RAISERROR('Table cible [%s] introuvable ou sans colonnes dans INFORMATION_SCHEMA distant', 16, 1, @TargetTable);
            RETURN -1;
        END

        -- Liste pour INSERT VALUES (prefixe source.)
        SELECT @InsertVals = STRING_AGG('source.' + QUOTENAME(COLUMN_NAME), ', ')
                             WITHIN GROUP (ORDER BY ORDINAL_POSITION)
        FROM #remote_cols;

        -- =============================================================
        -- 4. FILTRE INCREMENTAL (si applicable)
        -- =============================================================
        DECLARE @FinalSourceSQL NVARCHAR(MAX);
        SET @FinalSourceSQL = @SourceSelect;

        IF @ActualSyncType = 'incremental' AND @LastSyncDate IS NOT NULL AND @TimestampColumn IS NOT NULL
        BEGIN
            DECLARE @FilterDate NVARCHAR(50);
            SET @FilterDate = CONVERT(NVARCHAR(50), DATEADD(SECOND, -5, @LastSyncDate), 126);

            SET @FinalSourceSQL = N'SELECT * FROM (' + @SourceSelect + N') AS _src WHERE _src.'
                + QUOTENAME(@TimestampColumn) + N' > ''' + @FilterDate + N'''';
        END

        -- =============================================================
        -- 5. EXTRACTION Sage -> ##staging global (EXEC separe)
        -- On utilise une table globale ##staging_xxx pour persister
        -- entre les EXEC() et eviter MSDTC (pas de mix local+remote)
        -- =============================================================

        -- Nom unique pour la table globale (evite conflit concurrence)
        DECLARE @StagingTable NVARCHAR(200);
        SET @StagingTable = N'##stg_' + REPLACE(@SyncControlName, ' ', '_');

        -- Cleanup prealable
        SET @SQL = N'IF OBJECT_ID(''tempdb..' + @StagingTable + N''') IS NOT NULL DROP TABLE ' + @StagingTable;
        EXEC(@SQL);

        -- Extraction : USE base Sage + SELECT INTO ##staging (EXEC local uniquement)
        SET @SQL = N'USE ' + QUOTENAME(@SourceDatabase) + N'; '
                 + N'SELECT * INTO ' + @StagingTable + N' FROM (' + @FinalSourceSQL + N') AS src';
        EXEC(@SQL);

        SET @RowsExtracted = @@ROWCOUNT;

        PRINT CONVERT(VARCHAR, GETDATE(), 120) + ' | ' + @SyncControlName
            + ' | Extracted: ' + CAST(@RowsExtracted AS VARCHAR) + ' rows'
            + ' (' + @ActualSyncType + ')';

        -- =============================================================
        -- 6. CHARGEMENT : DELETE + INSERT via Linked Server (EXEC separe)
        --    Pas de MSDTC car c'est un EXEC distinct, operations remote only
        -- =============================================================

        IF @RowsExtracted > 0
        BEGIN
            -- Supprimer les donnees existantes pour cette source sur le DWH distant
            SET @SQL = N'DELETE FROM ' + @RemoteTarget
                + N' WHERE ' + QUOTENAME(@FilterColumn) + N' = @fv';
            EXEC sp_executesql @SQL, N'@fv NVARCHAR(200)', @fv = @FilterValue;
            SET @RowsDeleted = @@ROWCOUNT;

            -- Inserer depuis la table globale staging vers le DWH distant
            -- On injecte DB_Id, DB, DB_Caption comme valeurs litterales
            SET @SQL = N'INSERT INTO ' + @RemoteTarget
                + N' ([DB_Id], [DB], [DB_Caption], ' + @ColList + N') '
                + N'SELECT '
                + CAST(@SourceDbId AS NVARCHAR(20)) + N', '
                + N'N''' + REPLACE(@FilterValue, '''', '''''') + N''', '
                + N'N''' + REPLACE(@SourceCaption, '''', '''''') + N''', '
                + @InsertVals
                + N' FROM ' + @StagingTable + N' AS source';
            EXEC(@SQL);
            SET @RowsInserted = @@ROWCOUNT;
        END
        ELSE
        BEGIN
            -- Aucune ligne extraite : si full sync + DeleteOrphans, vider la cible
            IF @ActualSyncType = 'full' AND @DeleteOrphans = 1
            BEGIN
                SET @SQL = N'DELETE FROM ' + @RemoteTarget
                    + N' WHERE ' + QUOTENAME(@FilterColumn) + N' = @fv';
                EXEC sp_executesql @SQL, N'@fv NVARCHAR(200)', @fv = @FilterValue;
                SET @RowsDeleted = @@ROWCOUNT;
            END
        END

        PRINT CONVERT(VARCHAR, GETDATE(), 120) + ' | ' + @SyncControlName
            + ' | Inserted: ' + CAST(@RowsInserted AS VARCHAR)
            + ' | Deleted: '  + CAST(@RowsDeleted AS VARCHAR);

        -- =============================================================
        -- 7. NETTOYAGE
        -- =============================================================
        SET @SQL = N'IF OBJECT_ID(''tempdb..' + @StagingTable + N''') IS NOT NULL DROP TABLE ' + @StagingTable;
        EXEC(@SQL);
        IF OBJECT_ID('tempdb..#remote_cols') IS NOT NULL DROP TABLE #remote_cols;

        -- =============================================================
        -- 8. MISE A JOUR SyncControl (SUCCES) sur DWH distant
        -- =============================================================
        DECLARE @Duration INT;
        SET @Duration = DATEDIFF(SECOND, @StartTime, GETDATE());

        SET @SQL = N'UPDATE ' + @RemoteSyncControl + N'
            SET
                LastSyncDate     = GETDATE(),
                TotalInserted    = ISNULL(TotalInserted, 0) + @ins,
                TotalUpdated     = ISNULL(TotalUpdated, 0) + @upd,
                TotalDeleted     = ISNULL(TotalDeleted, 0) + @del,
                LastStatus       = ''Success'',
                LastError        = NULL,
                LastSyncDuration = @dur
            WHERE TableName = @scn';
        EXEC sp_executesql @SQL,
            N'@scn NVARCHAR(200), @ins INT, @upd INT, @del INT, @dur INT',
            @scn = @SyncControlName, @ins = @RowsInserted, @upd = @RowsUpdated,
            @del = @RowsDeleted, @dur = @Duration;

        -- =============================================================
        -- 9. LOG FIN (SUCCES) sur DWH distant
        -- =============================================================
        SET @SQL = N'UPDATE ' + @RemoteSyncLog + N'
            SET
                completed_at     = GETDATE(),
                status           = ''success'',
                rows_extracted   = @ext,
                rows_inserted    = @ins,
                rows_updated     = @upd,
                rows_deleted     = @del,
                watermark_after  = CONVERT(NVARCHAR(100), GETDATE(), 126)
            WHERE id = @lid';
        EXEC sp_executesql @SQL,
            N'@lid BIGINT, @ext INT, @ins INT, @upd INT, @del INT',
            @lid = @LogId, @ext = @RowsExtracted,
            @ins = @RowsInserted, @upd = @RowsUpdated, @del = @RowsDeleted;

        -- Resume
        IF @RowsInserted + @RowsUpdated + @RowsDeleted > 0
            PRINT CONVERT(VARCHAR, GETDATE(), 120)
                + ' | V ' + @SyncControlName
                + ' | INSERT: '  + CAST(@RowsInserted AS VARCHAR)
                + ' | DELETE: '  + CAST(@RowsDeleted   AS VARCHAR)
                + ' | Duree: '   + CAST(@Duration AS VARCHAR) + 's';
        ELSE
            PRINT CONVERT(VARCHAR, GETDATE(), 120)
                + ' | V ' + @SyncControlName
                + ' | Aucune modification'
                + ' | Duree: '   + CAST(@Duration AS VARCHAR) + 's';

    END TRY
    BEGIN CATCH
        -- =============================================================
        -- GESTION DES ERREURS
        -- =============================================================
        SET @ErrorMsg = ERROR_MESSAGE() + ' (Ligne: ' + CAST(ERROR_LINE() AS VARCHAR) + ')';

        -- Nettoyage staging en cas d'erreur
        BEGIN TRY
            IF @StagingTable IS NOT NULL
            BEGIN
                SET @SQL = N'IF OBJECT_ID(''tempdb..' + @StagingTable + N''') IS NOT NULL DROP TABLE ' + @StagingTable;
                EXEC(@SQL);
            END
            IF OBJECT_ID('tempdb..#remote_cols') IS NOT NULL DROP TABLE #remote_cols;
        END TRY
        BEGIN CATCH END CATCH

        -- Mettre a jour SyncControl (distant)
        BEGIN TRY
            DECLARE @ErrDuration INT;
            SET @ErrDuration = DATEDIFF(SECOND, @StartTime, GETDATE());
            SET @SQL = N'UPDATE ' + @RemoteSyncControl + N'
                SET
                    LastStatus       = ''Error'',
                    LastError        = @err,
                    LastSyncDuration = @dur
                WHERE TableName = @scn';
            EXEC sp_executesql @SQL,
                N'@scn NVARCHAR(200), @err NVARCHAR(MAX), @dur INT',
                @scn = @SyncControlName, @err = @ErrorMsg,
                @dur = @ErrDuration;
        END TRY
        BEGIN CATCH END CATCH

        -- Log echec (distant)
        BEGIN TRY
            SET @SQL = N'UPDATE ' + @RemoteSyncLog + N'
                SET
                    completed_at   = GETDATE(),
                    status         = ''failed'',
                    rows_extracted = @ext,
                    error_message  = @err
                WHERE id = @lid';
            EXEC sp_executesql @SQL,
                N'@lid BIGINT, @ext INT, @err NVARCHAR(MAX)',
                @lid = @LogId, @ext = @RowsExtracted, @err = @ErrorMsg;
        END TRY
        BEGIN CATCH END CATCH

        -- Alerte (distant)
        BEGIN TRY
            DECLARE @AlertMsg NVARCHAR(MAX);
            SET @AlertMsg = @SyncControlName + N' a echoue: ' + @ErrorMsg;
            SET @SQL = N'INSERT INTO ' + @RemoteAlerts
                + N' (alert_type, severity, source_code, table_name, sync_control_name, message)'
                + N' VALUES (''SYNC_FAILURE'', ''HIGH'', @fv, @tt, @scn, @msg)';
            EXEC sp_executesql @SQL,
                N'@fv NVARCHAR(200), @tt NVARCHAR(200), @scn NVARCHAR(200), @msg NVARCHAR(MAX)',
                @fv = @FilterValue, @tt = @TargetTable, @scn = @SyncControlName,
                @msg = @AlertMsg;
        END TRY
        BEGIN CATCH END CATCH

        PRINT CONVERT(VARCHAR, GETDATE(), 120)
            + ' | X ' + @SyncControlName
            + ' | ERREUR: ' + @ErrorMsg;

    END CATCH
END;
GO

-- Batch 3 : Confirmation
PRINT 'V Procedure sp_Sync_Generic_Local creee dans master (serveur Sage)';
PRINT '  Cette SP lit les donnees Sage localement et ecrit dans le DWH via Linked Server';
GO
