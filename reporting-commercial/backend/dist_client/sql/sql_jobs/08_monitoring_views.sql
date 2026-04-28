-- =====================================================================
-- 08_monitoring_views.sql
-- Vues de monitoring ETL (architecture 3 bases)
-- A executer dans la base DWH
-- =====================================================================
-- PREREQUIS :
--   - 02_create_etl_config_tables.sql execute (SyncControl, ETL_Sources, etc.)
--   - {OPTIBOARD_DB} accessible en cross-database (meme serveur)
--     OU synonyme cree (voir section SYNONYME en bas)
-- =====================================================================
-- VARIABLES A REMPLACER :
--   {DWH_NAME}      -> nom de votre base DWH (ex: DWH_Alboughaze)
--   {OPTIBOARD_DB}  -> nom de votre base OptiBoard (ex: OptiBoard_SaaS)
-- =====================================================================
-- NOTE: Chaque batch inclut son propre USE pour garantir le contexte DB
--       meme si pyodbc ne propage pas le USE entre cursor.execute() calls.
-- =====================================================================

SET NOCOUNT ON;
GO

USE [{DWH_NAME}];
PRINT '══════════════════════════════════════════════════════════════';
PRINT ' CREATION DES VUES DE MONITORING ETL';
PRINT '══════════════════════════════════════════════════════════════';
GO

-- =====================================================================
-- OPTIONNEL : Creer un synonyme pour eviter les noms 3 parties
-- Decommenter si OptiBoard est sur le meme serveur
-- =====================================================================
-- USE [{DWH_NAME}];
-- IF NOT EXISTS (SELECT * FROM sys.synonyms WHERE name = 'SYN_ETL_Tables_Config')
--     CREATE SYNONYM dbo.SYN_ETL_Tables_Config
--     FOR [{OPTIBOARD_DB}].dbo.ETL_Tables_Config;
-- GO

-- =====================================================================
-- 1. V_ETL_Dashboard - Etat en temps reel de chaque source x table
-- =====================================================================
USE [{DWH_NAME}];
IF EXISTS (SELECT * FROM sys.views WHERE name = 'V_ETL_Dashboard')
    DROP VIEW V_ETL_Dashboard;
GO

USE [{DWH_NAME}];
CREATE VIEW V_ETL_Dashboard AS
SELECT
    src.source_code                         AS [Source],
    cfg.table_name                          AS [Table],
    cfg.target_table                        AS [Table DWH],
    cfg.sync_type                           AS [Type Sync],
    cfg.priority                            AS [Priorite],

    -- Statut
    CASE
        WHEN sc.LastStatus = 'Error'                                                THEN 'ERREUR'
        WHEN sc.TableName IS NULL                                                   THEN 'Jamais synce'
        WHEN cfg.priority = 'high'   AND DATEDIFF(MINUTE, sc.LastSyncDate, GETDATE()) > 10  THEN 'Retard'
        WHEN cfg.priority = 'normal' AND DATEDIFF(MINUTE, sc.LastSyncDate, GETDATE()) > 30  THEN 'Retard'
        WHEN cfg.priority = 'low'    AND DATEDIFF(MINUTE, sc.LastSyncDate, GETDATE()) > 120 THEN 'Retard'
        ELSE 'OK'
    END                                     AS [Statut],

    -- Derniere synchronisation
    sc.LastSyncDate                         AS [Dernier Sync],
    DATEDIFF(MINUTE, sc.LastSyncDate, GETDATE()) AS [Minutes depuis],
    sc.LastSyncDuration                     AS [Duree (s)],

    -- Compteurs cumules
    sc.TotalInserted                        AS [Total Inseres],
    sc.TotalUpdated                         AS [Total MAJ],
    sc.TotalDeleted                         AS [Total Supprimes],

    -- Erreur
    sc.LastStatus                           AS [Dernier Statut],
    LEFT(sc.LastError, 200)                 AS [Derniere Erreur],

    -- Dernier log
    l.rows_extracted                        AS [Dern. Extraites],
    l.rows_inserted                         AS [Dern. Inserees],
    l.rows_updated                          AS [Dern. MAJ],
    l.rows_deleted                          AS [Dern. Supprimees],
    l.duration_seconds                      AS [Dern. Duree (s)],

    -- Source info
    src.source_caption                      AS [Nom Source],
    src.database_name                       AS [Base Sage],
    CASE src.is_linked_server WHEN 1 THEN 'Linked Server' ELSE 'Local' END AS [Mode]

FROM [{OPTIBOARD_DB}].dbo.ETL_Tables_Config cfg
CROSS JOIN ETL_Sources src
LEFT JOIN SyncControl sc
    ON sc.TableName = src.source_code + '_' + cfg.target_table
OUTER APPLY (
    SELECT TOP 1
        rows_extracted, rows_inserted, rows_updated, rows_deleted,
        duration_seconds
    FROM ETL_Sync_Log
    WHERE sync_control_name = src.source_code + '_' + cfg.target_table
    ORDER BY id DESC
) l
WHERE cfg.is_active = 1
  AND src.is_active = 1;
GO

USE [{DWH_NAME}];
PRINT 'V Vue V_ETL_Dashboard creee';
GO

-- =====================================================================
-- 2. V_ETL_Alertes - Tables en erreur ou en retard
-- =====================================================================
USE [{DWH_NAME}];
IF EXISTS (SELECT * FROM sys.views WHERE name = 'V_ETL_Alertes')
    DROP VIEW V_ETL_Alertes;
GO

USE [{DWH_NAME}];
CREATE VIEW V_ETL_Alertes AS
SELECT
    src.source_code                         AS [Source],
    cfg.table_name                          AS [Table],
    cfg.target_table                        AS [Table DWH],
    cfg.priority                            AS [Priorite],

    CASE
        WHEN sc.LastStatus = 'Error'                                                THEN 'ERREUR - ' + LEFT(ISNULL(sc.LastError, '?'), 100)
        WHEN sc.TableName IS NULL                                                   THEN 'JAMAIS SYNCE'
        WHEN cfg.priority = 'high'   AND DATEDIFF(MINUTE, sc.LastSyncDate, GETDATE()) > 10  THEN 'RETARD - ' + CAST(DATEDIFF(MINUTE, sc.LastSyncDate, GETDATE()) AS VARCHAR) + ' min'
        WHEN cfg.priority = 'normal' AND DATEDIFF(MINUTE, sc.LastSyncDate, GETDATE()) > 30  THEN 'RETARD - ' + CAST(DATEDIFF(MINUTE, sc.LastSyncDate, GETDATE()) AS VARCHAR) + ' min'
        WHEN cfg.priority = 'low'    AND DATEDIFF(MINUTE, sc.LastSyncDate, GETDATE()) > 120 THEN 'RETARD - ' + CAST(DATEDIFF(MINUTE, sc.LastSyncDate, GETDATE()) AS VARCHAR) + ' min'
    END                                     AS [Alerte],

    sc.LastSyncDate                         AS [Dernier Sync OK],
    sc.LastSyncDuration                     AS [Duree (s)],
    LEFT(sc.LastError, 300)                 AS [Erreur]

FROM [{OPTIBOARD_DB}].dbo.ETL_Tables_Config cfg
CROSS JOIN ETL_Sources src
LEFT JOIN SyncControl sc
    ON sc.TableName = src.source_code + '_' + cfg.target_table
WHERE cfg.is_active = 1
  AND src.is_active = 1
  AND (
      sc.LastStatus = 'Error'
      OR sc.TableName IS NULL
      OR (cfg.priority = 'high'   AND DATEDIFF(MINUTE, sc.LastSyncDate, GETDATE()) > 10)
      OR (cfg.priority = 'normal' AND DATEDIFF(MINUTE, sc.LastSyncDate, GETDATE()) > 30)
      OR (cfg.priority = 'low'    AND DATEDIFF(MINUTE, sc.LastSyncDate, GETDATE()) > 120)
  );
GO

USE [{DWH_NAME}];
PRINT 'V Vue V_ETL_Alertes creee';
GO

-- =====================================================================
-- 3. V_ETL_Stats_24H - Statistiques des dernieres 24 heures
-- =====================================================================
USE [{DWH_NAME}];
IF EXISTS (SELECT * FROM sys.views WHERE name = 'V_ETL_Stats_24H')
    DROP VIEW V_ETL_Stats_24H;
GO

USE [{DWH_NAME}];
CREATE VIEW V_ETL_Stats_24H AS
SELECT
    source_code                             AS [Source],
    table_name                              AS [Table],
    COUNT(*)                                AS [Total Syncs],
    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS [Succes],
    SUM(CASE WHEN status = 'failed'  THEN 1 ELSE 0 END) AS [Echecs],
    SUM(rows_extracted)                     AS [Total Extraites],
    SUM(rows_inserted)                      AS [Total Inserees],
    SUM(rows_updated)                       AS [Total MAJ],
    SUM(rows_deleted)                       AS [Total Supprimees],
    AVG(duration_seconds)                   AS [Duree Moy (s)],
    MAX(duration_seconds)                   AS [Duree Max (s)],
    MIN(started_at)                         AS [Premier Sync],
    MAX(started_at)                         AS [Dernier Sync]
FROM ETL_Sync_Log
WHERE started_at >= DATEADD(HOUR, -24, GETDATE())
GROUP BY source_code, table_name;
GO

USE [{DWH_NAME}];
PRINT 'V Vue V_ETL_Stats_24H creee';
GO

-- =====================================================================
-- 4. V_ETL_Sources_Status - Resume par source
-- =====================================================================
USE [{DWH_NAME}];
IF EXISTS (SELECT * FROM sys.views WHERE name = 'V_ETL_Sources_Status')
    DROP VIEW V_ETL_Sources_Status;
GO

USE [{DWH_NAME}];
CREATE VIEW V_ETL_Sources_Status AS
SELECT
    src.source_code                         AS [Code Source],
    src.source_caption                      AS [Nom],
    src.database_name                       AS [Base Sage],
    CASE src.is_linked_server WHEN 1 THEN src.linked_server_name ELSE 'Local' END AS [Mode Connexion],

    COUNT(sc.TableName)                     AS [Tables Syncees],
    SUM(CASE WHEN sc.LastStatus = 'Error' THEN 1 ELSE 0 END) AS [Tables en Erreur],
    SUM(CASE WHEN sc.LastSyncDate IS NULL THEN 1 ELSE 0 END) AS [Jamais Syncees],

    MAX(sc.LastSyncDate)                    AS [Dernier Sync Global],
    DATEDIFF(MINUTE, MAX(sc.LastSyncDate), GETDATE()) AS [Min Depuis Sync],

    SUM(ISNULL(sc.TotalInserted, 0) + ISNULL(sc.TotalUpdated, 0)) AS [Total Lignes Syncees],

    CASE
        WHEN SUM(CASE WHEN sc.LastStatus = 'Error' THEN 1 ELSE 0 END) > 0 THEN 'ERREUR'
        WHEN MAX(sc.LastSyncDate) IS NULL                                  THEN 'NON INITIALISE'
        ELSE 'OK'
    END                                     AS [Statut Global]

FROM ETL_Sources src
LEFT JOIN SyncControl sc
    ON sc.TableName LIKE src.source_code + '_%'
WHERE src.is_active = 1
GROUP BY src.source_code, src.source_caption, src.database_name, src.is_linked_server, src.linked_server_name;
GO

USE [{DWH_NAME}];
PRINT 'V Vue V_ETL_Sources_Status creee';
GO

-- =====================================================================
-- 5. V_ETL_Alerts_History - Historique des alertes recentes
-- =====================================================================
USE [{DWH_NAME}];
IF EXISTS (SELECT * FROM sys.views WHERE name = 'V_ETL_Alerts_History')
    DROP VIEW V_ETL_Alerts_History;
GO

USE [{DWH_NAME}];
CREATE VIEW V_ETL_Alerts_History AS
SELECT
    alert_id                                AS [ID],
    alert_time                              AS [Date],
    alert_type                              AS [Type],
    severity                                AS [Severite],
    source_code                             AS [Source],
    table_name                              AS [Table],
    LEFT(message, 300)                      AS [Message],
    is_acknowledged                         AS [Acquitte]
FROM ETL_Alerts
WHERE is_acknowledged = 0
  OR alert_time >= DATEADD(DAY, -7, GETDATE());
GO

USE [{DWH_NAME}];
PRINT 'V Vue V_ETL_Alerts_History creee';
GO

-- =====================================================================
-- 6. V_ETL_SyncControl_Status - Vue directe sur SyncControl
-- =====================================================================
USE [{DWH_NAME}];
IF EXISTS (SELECT * FROM sys.views WHERE name = 'V_ETL_SyncControl_Status')
    DROP VIEW V_ETL_SyncControl_Status;
GO

USE [{DWH_NAME}];
CREATE VIEW V_ETL_SyncControl_Status AS
SELECT
    sc.TableName                            AS [Cle SyncControl],
    -- Extraire source_code et target_table via JOIN ETL_Sources
    -- (evite le parsing CHARINDEX qui echoue si source_code contient '_')
    es.source_code                          AS [Source],
    STUFF(sc.TableName, 1, LEN(es.source_code) + 1, '') AS [Table],
    sc.LastSyncDate                         AS [Dernier Sync],
    DATEDIFF(MINUTE, sc.LastSyncDate, GETDATE()) AS [Minutes depuis],
    sc.LastStatus                           AS [Statut],
    sc.LastSyncDuration                     AS [Duree (s)],
    sc.TotalInserted                        AS [Total Inseres],
    sc.TotalUpdated                         AS [Total MAJ],
    sc.TotalDeleted                         AS [Total Supprimes],
    LEFT(sc.LastError, 200)                 AS [Erreur]
FROM SyncControl sc
LEFT JOIN ETL_Sources es
    ON sc.TableName LIKE es.source_code + '_%'
    AND es.is_active = 1;
GO

USE [{DWH_NAME}];
PRINT 'V Vue V_ETL_SyncControl_Status creee';
GO

USE [{DWH_NAME}];
PRINT '';
PRINT '══════════════════════════════════════════════════════════════';
PRINT ' VUES DE MONITORING CREEES';
PRINT '══════════════════════════════════════════════════════════════';
PRINT '';
PRINT ' SELECT * FROM V_ETL_Dashboard          -- Dashboard complet';
PRINT ' SELECT * FROM V_ETL_Alertes            -- Tables en anomalie';
PRINT ' SELECT * FROM V_ETL_Stats_24H          -- Stats dernieres 24h';
PRINT ' SELECT * FROM V_ETL_Sources_Status     -- Resume par source';
PRINT ' SELECT * FROM V_ETL_Alerts_History     -- Alertes recentes';
PRINT ' SELECT * FROM V_ETL_SyncControl_Status -- Etat SyncControl brut';
PRINT '';
PRINT ' NOTE : Les vues V_ETL_Dashboard et V_ETL_Alertes utilisent';
PRINT '        une reference cross-database vers {OPTIBOARD_DB}.';
PRINT '        Si les bases sont sur des serveurs differents,';
PRINT '        creez un synonyme (voir section SYNONYME en haut).';
PRINT '══════════════════════════════════════════════════════════════';
GO
