-- =====================================================================
-- 04_sp_sync_generic.sql
-- LA PROCEDURE GENERIQUE UNIQUE : sp_Sync_Generic
-- Utilise INFORMATION_SCHEMA.COLUMNS + STRING_AGG pour MERGE dynamique
-- A executer dans la base DWH
-- =====================================================================
-- PATTERN : La SP ne lit AUCUNE config. Tout est passe en parametre
--           par le Job SQL Agent (WHILE 1=1).
-- =====================================================================

SET NOCOUNT ON;
GO

-- Batch 1 : DROP ancienne SP si existe
USE [{DWH_NAME}];
IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'sp_Sync_Generic')
    DROP PROCEDURE sp_Sync_Generic;
GO

-- Batch 2 : CREATE PROCEDURE
USE [{DWH_NAME}];
CREATE PROCEDURE dbo.sp_Sync_Generic
    @TargetTable      NVARCHAR(200),         -- Table cible DWH (ex: 'Collaborateurs')
    @SourceSelect     NVARCHAR(MAX),         -- SELECT complet avec prefixes DB appliques
    @JoinColumn       NVARCHAR(200),         -- Colonne PK pour MERGE ON (ex: 'Code collaborateur')
    @FilterColumn     NVARCHAR(100),         -- Colonne multi-source (ex: 'DB')
    @FilterValue      NVARCHAR(200),         -- Valeur source (ex: 'CASHPLUS_2026')
    @TimestampColumn  NVARCHAR(100) = NULL,  -- Colonne pour sync incremental (ex: 'cbModification')
    @SyncControlName  NVARCHAR(200),         -- Cle dans SyncControl (ex: 'CASHPLUS_2026_Collaborateurs')
    @DeleteOrphans    BIT = 0                -- Supprimer les orphelins ?
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT OFF;

    -- ═══════════════════════════════════════════════════════════════
    -- VARIABLES
    -- ═══════════════════════════════════════════════════════════════
    DECLARE @StartTime       DATETIME2 = GETDATE();
    DECLARE @LastSyncDate    DATETIME;
    DECLARE @LogId           BIGINT;
    DECLARE @ActualSyncType  NVARCHAR(20);

    -- Colonnes dynamiques
    DECLARE @ColList          NVARCHAR(MAX);
    DECLARE @UpdateSet        NVARCHAR(MAX);
    DECLARE @InsertCols       NVARCHAR(MAX);
    DECLARE @InsertVals       NVARCHAR(MAX);

    -- Compteurs
    DECLARE @RowsInserted    INT = 0;
    DECLARE @RowsUpdated     INT = 0;
    DECLARE @RowsDeleted     INT = 0;
    DECLARE @RowsExtracted   INT = 0;

    DECLARE @SQL             NVARCHAR(MAX);
    DECLARE @ErrorMsg        NVARCHAR(MAX);

    -- ═══════════════════════════════════════════════════════════════
    -- 1. LIRE / INITIALISER SyncControl
    -- ═══════════════════════════════════════════════════════════════
    IF NOT EXISTS (SELECT 1 FROM SyncControl WHERE TableName = @SyncControlName)
    BEGIN
        INSERT INTO SyncControl (TableName) VALUES (@SyncControlName);
    END

    SELECT @LastSyncDate = LastSyncDate
    FROM SyncControl
    WHERE TableName = @SyncControlName;

    -- Determiner le type de sync effectif
    SET @ActualSyncType = CASE
        WHEN @TimestampColumn IS NOT NULL AND @LastSyncDate IS NOT NULL THEN 'incremental'
        ELSE 'full'
    END;

    -- ═══════════════════════════════════════════════════════════════
    -- 2. LOG DEBUT
    -- ═══════════════════════════════════════════════════════════════
    INSERT INTO ETL_Sync_Log (sync_control_name, source_code, table_name, sync_type, started_at, status, watermark_before)
    VALUES (@SyncControlName, @FilterValue, @TargetTable, @ActualSyncType, @StartTime, 'running',
            CONVERT(NVARCHAR(100), @LastSyncDate, 126));

    SET @LogId = SCOPE_IDENTITY();

    -- ═══════════════════════════════════════════════════════════════
    -- DEBUT TRY/CATCH
    -- ═══════════════════════════════════════════════════════════════
    BEGIN TRY

        -- ═══════════════════════════════════════════════════════════
        -- 3. DECOUVERTE DES COLONNES via INFORMATION_SCHEMA
        -- ═══════════════════════════════════════════════════════════

        -- Liste de toutes les colonnes (sauf 'id' identity)
        SELECT @ColList = STRING_AGG(QUOTENAME(COLUMN_NAME), ', ')
                          WITHIN GROUP (ORDER BY ORDINAL_POSITION)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = @TargetTable
          AND TABLE_SCHEMA = 'dbo'
          AND COLUMN_NAME <> 'id'
          AND COLUMNPROPERTY(OBJECT_ID('dbo.' + @TargetTable), COLUMN_NAME, 'IsIdentity') = 0;

        IF @ColList IS NULL
        BEGIN
            RAISERROR('Table cible [%s] introuvable ou sans colonnes dans INFORMATION_SCHEMA', 16, 1, @TargetTable);
            RETURN -1;
        END

        -- Colonnes pour UPDATE SET (exclut JoinColumn et FilterColumn)
        SELECT @UpdateSet = STRING_AGG(
                'target.' + QUOTENAME(COLUMN_NAME) + ' = source.' + QUOTENAME(COLUMN_NAME),
                ', '
            ) WITHIN GROUP (ORDER BY ORDINAL_POSITION)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = @TargetTable
          AND TABLE_SCHEMA = 'dbo'
          AND COLUMN_NAME <> 'id'
          AND COLUMN_NAME <> @JoinColumn
          AND COLUMN_NAME <> @FilterColumn
          AND COLUMNPROPERTY(OBJECT_ID('dbo.' + @TargetTable), COLUMN_NAME, 'IsIdentity') = 0;

        -- Colonnes pour INSERT VALUES (prefixe source.)
        SELECT @InsertVals = STRING_AGG('source.' + QUOTENAME(COLUMN_NAME), ', ')
                             WITHIN GROUP (ORDER BY ORDINAL_POSITION)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = @TargetTable
          AND TABLE_SCHEMA = 'dbo'
          AND COLUMN_NAME <> 'id'
          AND COLUMNPROPERTY(OBJECT_ID('dbo.' + @TargetTable), COLUMN_NAME, 'IsIdentity') = 0;

        -- ═══════════════════════════════════════════════════════════
        -- 4. FILTRE INCREMENTAL (si applicable)
        -- ═══════════════════════════════════════════════════════════
        DECLARE @FinalSourceSQL NVARCHAR(MAX) = @SourceSelect;

        IF @ActualSyncType = 'incremental' AND @LastSyncDate IS NOT NULL AND @TimestampColumn IS NOT NULL
        BEGIN
            DECLARE @FilterDate NVARCHAR(50) = CONVERT(NVARCHAR(50), DATEADD(SECOND, -5, @LastSyncDate), 126);

            -- Encapsuler dans un sous-SELECT pour ajouter le filtre incremental
            SET @FinalSourceSQL = N'SELECT * FROM (' + @SourceSelect + N') AS _src WHERE _src.'
                + QUOTENAME(@TimestampColumn) + N' > ''' + @FilterDate + N'''
                OR _src.cbCreation > ''' + @FilterDate + N'''';
        END

        -- ═══════════════════════════════════════════════════════════
        -- 5. EXTRACTION DANS #staging
        -- ═══════════════════════════════════════════════════════════
        SET @SQL = N'SELECT * INTO #staging FROM (' + @FinalSourceSQL + N') AS src';

        -- Creer la table staging
        -- NOTE : EXEC() au lieu de sp_executesql pour que #staging reste
        --        visible dans le scope de la SP (les tables temp creees par
        --        sp_executesql sont detruites a la fin de son scope enfant).
        IF OBJECT_ID('tempdb..#staging') IS NOT NULL DROP TABLE #staging;
        EXEC(@SQL);

        SET @RowsExtracted = @@ROWCOUNT;

        PRINT CONVERT(VARCHAR, GETDATE(), 120) + ' | ' + @SyncControlName
            + ' | Extracted: ' + CAST(@RowsExtracted AS VARCHAR) + ' rows'
            + ' (' + @ActualSyncType + ')';

        -- ═══════════════════════════════════════════════════════════
        -- 6. CHARGEMENT : MERGE ou DELETE+INSERT
        -- ═══════════════════════════════════════════════════════════
        DECLARE @pIns INT = 0, @pUpd INT = 0;

        IF @RowsExtracted > 0
        BEGIN
            IF @JoinColumn IS NOT NULL AND LEN(@JoinColumn) > 0
            BEGIN
                -- === CAS 1 : MERGE classique (tables avec PK) ===
                SET @SQL = N'
                    DECLARE @MergeLog TABLE (MergeAction VARCHAR(10));

                    MERGE INTO ' + QUOTENAME(@TargetTable) + N' AS target
                    USING #staging AS source
                    ON target.' + QUOTENAME(@JoinColumn) + N' = source.' + QUOTENAME(@JoinColumn) + N'
                       AND target.' + QUOTENAME(@FilterColumn) + N' = @fv
                    WHEN MATCHED THEN
                        UPDATE SET ' + @UpdateSet + N'
                    WHEN NOT MATCHED BY TARGET THEN
                        INSERT (' + @ColList + N')
                        VALUES (' + @InsertVals + N')
                    OUTPUT $action INTO @MergeLog;

                    SELECT
                        @ins = SUM(CASE WHEN MergeAction = ''INSERT'' THEN 1 ELSE 0 END),
                        @upd = SUM(CASE WHEN MergeAction = ''UPDATE'' THEN 1 ELSE 0 END)
                    FROM @MergeLog;';

                EXEC sp_executesql @SQL,
                    N'@fv NVARCHAR(200), @ins INT OUTPUT, @upd INT OUTPUT',
                    @fv = @FilterValue, @ins = @pIns OUTPUT, @upd = @pUpd OUTPUT;

                SET @RowsInserted = ISNULL(@pIns, 0);
                SET @RowsUpdated  = ISNULL(@pUpd, 0);
            END
            ELSE
            BEGIN
                -- === CAS 2 : DELETE + INSERT (tables sans PK / full reload par source) ===
                -- Supprimer les donnees existantes pour cette source
                SET @SQL = N'DELETE FROM ' + QUOTENAME(@TargetTable)
                    + N' WHERE ' + QUOTENAME(@FilterColumn) + N' = @fv';
                EXEC sp_executesql @SQL, N'@fv NVARCHAR(200)', @fv = @FilterValue;
                SET @RowsDeleted = @@ROWCOUNT;

                -- Inserer toutes les lignes du staging
                SET @SQL = N'INSERT INTO ' + QUOTENAME(@TargetTable)
                    + N' (' + @ColList + N') SELECT ' + @InsertVals
                    + N' FROM #staging AS source';
                EXEC sp_executesql @SQL;
                SET @RowsInserted = @@ROWCOUNT;
            END
        END

        -- ═══════════════════════════════════════════════════════════
        -- 7. DETECTION DES SUPPRESSIONS (orphelins)
        -- ═══════════════════════════════════════════════════════════
        IF @DeleteOrphans = 1 AND @JoinColumn IS NOT NULL AND LEN(@JoinColumn) > 0
        BEGIN
            DECLARE @Del INT = 1;
            WHILE @Del > 0
            BEGIN
                SET @SQL = N'
                    DELETE TOP (10000) target
                    FROM ' + QUOTENAME(@TargetTable) + N' target
                    WHERE target.' + QUOTENAME(@FilterColumn) + N' = @fv
                      AND NOT EXISTS (
                          SELECT 1 FROM #staging source
                          WHERE source.' + QUOTENAME(@JoinColumn) + N' = target.' + QUOTENAME(@JoinColumn) + N'
                      )';

                EXEC sp_executesql @SQL, N'@fv NVARCHAR(200)', @fv = @FilterValue;
                SET @Del = @@ROWCOUNT;
                SET @RowsDeleted = @RowsDeleted + @Del;

                IF @Del > 0 WAITFOR DELAY '00:00:00.200';
            END
        END

        -- ═══════════════════════════════════════════════════════════
        -- 8. NETTOYAGE STAGING
        -- ═══════════════════════════════════════════════════════════
        IF OBJECT_ID('tempdb..#staging') IS NOT NULL DROP TABLE #staging;

        -- ═══════════════════════════════════════════════════════════
        -- 9. MISE A JOUR SyncControl (SUCCES)
        -- ═══════════════════════════════════════════════════════════
        DECLARE @Duration INT = DATEDIFF(SECOND, @StartTime, GETDATE());

        UPDATE SyncControl
        SET
            LastSyncDate     = GETDATE(),
            TotalInserted    = TotalInserted + @RowsInserted,
            TotalUpdated     = TotalUpdated + @RowsUpdated,
            TotalDeleted     = TotalDeleted + @RowsDeleted,
            LastStatus       = 'Success',
            LastError        = NULL,
            LastSyncDuration = @Duration
        WHERE TableName = @SyncControlName;

        -- ═══════════════════════════════════════════════════════════
        -- 10. LOG FIN (SUCCES)
        -- ═══════════════════════════════════════════════════════════
        UPDATE ETL_Sync_Log
        SET
            completed_at     = GETDATE(),
            status           = 'success',
            rows_extracted   = @RowsExtracted,
            rows_inserted    = @RowsInserted,
            rows_updated     = @RowsUpdated,
            rows_deleted     = @RowsDeleted,
            watermark_after  = CONVERT(NVARCHAR(100), GETDATE(), 126)
        WHERE id = @LogId;

        -- Resume
        IF @RowsInserted + @RowsUpdated + @RowsDeleted > 0
            PRINT CONVERT(VARCHAR, GETDATE(), 120)
                + ' | V ' + @SyncControlName
                + ' | INSERT: '  + CAST(@RowsInserted AS VARCHAR)
                + ' | UPDATE: '  + CAST(@RowsUpdated  AS VARCHAR)
                + ' | DELETE: '  + CAST(@RowsDeleted   AS VARCHAR)
                + ' | Duree: '   + CAST(@Duration AS VARCHAR) + 's';
        ELSE
            PRINT CONVERT(VARCHAR, GETDATE(), 120)
                + ' | V ' + @SyncControlName
                + ' | Aucune modification'
                + ' | Duree: '   + CAST(@Duration AS VARCHAR) + 's';

    END TRY
    BEGIN CATCH
        -- ═══════════════════════════════════════════════════════════
        -- GESTION DES ERREURS
        -- ═══════════════════════════════════════════════════════════
        SET @ErrorMsg = ERROR_MESSAGE() + ' (Ligne: ' + CAST(ERROR_LINE() AS VARCHAR) + ')';

        -- Nettoyage staging en cas d'erreur
        BEGIN TRY
            IF OBJECT_ID('tempdb..#staging') IS NOT NULL DROP TABLE #staging;
        END TRY
        BEGIN CATCH END CATCH

        -- Mettre a jour SyncControl
        UPDATE SyncControl
        SET
            LastStatus       = 'Error',
            LastError        = @ErrorMsg,
            LastSyncDuration = DATEDIFF(SECOND, @StartTime, GETDATE())
        WHERE TableName = @SyncControlName;

        -- Log echec
        UPDATE ETL_Sync_Log
        SET
            completed_at   = GETDATE(),
            status         = 'failed',
            rows_extracted = @RowsExtracted,
            error_message  = @ErrorMsg
        WHERE id = @LogId;

        -- Alerte si erreur
        INSERT INTO ETL_Alerts (alert_type, severity, source_code, table_name, sync_control_name, message)
        VALUES (
            'SYNC_FAILURE', 'HIGH', @FilterValue, @TargetTable, @SyncControlName,
            @SyncControlName + ' a echoue: ' + @ErrorMsg
        );

        PRINT CONVERT(VARCHAR, GETDATE(), 120)
            + ' | X ' + @SyncControlName
            + ' | ERREUR: ' + @ErrorMsg;

    END CATCH
END;
GO

-- Batch 3 : Confirmation
USE [{DWH_NAME}];
PRINT 'V Procedure sp_Sync_Generic creee dans {DWH_NAME}';
GO
