-- ============================================================
-- MIGRATION STEP 1 : BASE CENTRALE (OptiBoard_SaaS)
-- ============================================================
-- Objectif : transformer APP_ETL_Agents (config complete)
--            en APP_ETL_Agents_Monitoring (metriques uniquement)
--
-- A executer SUR OptiBoard_SaaS AVANT le script Python de migration.
--
-- Logique metier :
--   - Les credentials Sage et la config complete restent dans les bases CLIENT
--   - Le central ne garde que les metriques de monitoring (statut, heartbeat...)
--   - Les agents existants sont sauvegardes dans APP_ETL_Agents_OLD (backup)
--
-- Ordre d execution :
--   1. Ce script (central)
--   2. 008_migrate_agents_client_template.sql  (chaque base client)
--   3. migrate_agents.py  (deplace les donnees central -> client)
-- ============================================================

USE OptiBoard_SaaS;
GO

PRINT '============================================================';
PRINT ' MIGRATION AGENTS ETL — STEP 1 (BASE CENTRALE)';
PRINT ' ' + CONVERT(VARCHAR, GETDATE(), 120);
PRINT '============================================================';
GO

-- ============================================================
-- 1. SAUVEGARDE : renommer l ancienne table en _OLD
-- ============================================================
IF EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Agents' AND xtype='U')
AND NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Agents_OLD' AND xtype='U')
BEGIN
    EXEC sp_rename 'APP_ETL_Agents', 'APP_ETL_Agents_OLD';
    PRINT '[OK] APP_ETL_Agents renommee en APP_ETL_Agents_OLD (backup)';
END
ELSE IF EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Agents_OLD' AND xtype='U')
BEGIN
    PRINT '[SKIP] APP_ETL_Agents_OLD existe deja — backup deja fait';
END
ELSE
BEGIN
    PRINT '[INFO] APP_ETL_Agents absente — pas de backup necessaire';
END
GO

-- ============================================================
-- 2. SAUVEGARDE APP_ETL_Agent_Tables → _OLD
-- ============================================================
IF EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Agent_Tables' AND xtype='U')
AND NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Agent_Tables_OLD' AND xtype='U')
BEGIN
    EXEC sp_rename 'APP_ETL_Agent_Tables', 'APP_ETL_Agent_Tables_OLD';
    PRINT '[OK] APP_ETL_Agent_Tables renommee en APP_ETL_Agent_Tables_OLD (backup)';
END
GO

-- ============================================================
-- 3. SAUVEGARDE APP_ETL_Agent_Sync_Log → _OLD
-- ============================================================
IF EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Agent_Sync_Log' AND xtype='U')
AND NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Agent_Sync_Log_OLD' AND xtype='U')
BEGIN
    EXEC sp_rename 'APP_ETL_Agent_Sync_Log', 'APP_ETL_Agent_Sync_Log_OLD';
    PRINT '[OK] APP_ETL_Agent_Sync_Log renommee en APP_ETL_Agent_Sync_Log_OLD (backup)';
END
GO

-- ============================================================
-- 4. CREER APP_ETL_Agents_Monitoring (remplace APP_ETL_Agents)
--    Metriques uniquement — PAS de credentials Sage
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Agents_Monitoring' AND xtype='U')
BEGIN
    CREATE TABLE APP_ETL_Agents_Monitoring (
        id                      INT IDENTITY(1,1) PRIMARY KEY,
        agent_id                VARCHAR(100) UNIQUE NOT NULL,
        dwh_code                VARCHAR(50)  NOT NULL REFERENCES APP_DWH(code),
        nom                     NVARCHAR(200) NOT NULL,
        -- Infos machine (remontees par l agent via heartbeat)
        hostname                VARCHAR(200),
        ip_address              VARCHAR(50),
        os_info                 VARCHAR(200),
        agent_version           VARCHAR(50),
        -- Statut temps reel
        statut                  VARCHAR(20) DEFAULT 'inconnu'
                                CHECK (statut IN ('actif','inactif','erreur','inconnu')),
        last_heartbeat          DATETIME,
        last_sync               DATETIME,
        last_sync_statut        VARCHAR(20),
        consecutive_failures    INT DEFAULT 0,
        -- Metriques globales
        total_syncs             INT DEFAULT 0,
        total_lignes_sync       BIGINT DEFAULT 0,
        -- PAS de : sage_server, sage_password, sync_interval, batch_size
        -- Ces champs sont UNIQUEMENT dans la base CLIENT
        date_enregistrement     DATETIME DEFAULT GETDATE(),
        date_modification       DATETIME DEFAULT GETDATE()
    );
    PRINT '[OK] APP_ETL_Agents_Monitoring creee';
END
ELSE
    PRINT '[SKIP] APP_ETL_Agents_Monitoring existe deja';
GO

-- ============================================================
-- 5. MIGRER LES METRIQUES vers APP_ETL_Agents_Monitoring
--    (depuis le backup APP_ETL_Agents_OLD)
-- ============================================================
IF EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Agents_OLD' AND xtype='U')
BEGIN
    INSERT INTO APP_ETL_Agents_Monitoring (
        agent_id, dwh_code, nom,
        hostname, ip_address, os_info, agent_version,
        statut, last_heartbeat, last_sync, last_sync_statut,
        consecutive_failures, total_syncs, total_lignes_sync,
        date_enregistrement, date_modification
    )
    SELECT
        CAST(agent_id AS VARCHAR(100)),
        dwh_code,
        ISNULL(name, 'Agent ' + dwh_code),
        hostname, ip_address, os_info, agent_version,
        CASE
            WHEN is_active = 0 THEN 'inactif'
            WHEN status = 'error' THEN 'erreur'
            WHEN status IN ('active','syncing','idle') THEN 'actif'
            ELSE 'inconnu'
        END,
        last_heartbeat, last_sync, last_sync_status,
        ISNULL(consecutive_failures, 0),
        ISNULL(total_syncs, 0),
        ISNULL(total_rows_synced, 0),
        ISNULL(created_at, GETDATE()),
        ISNULL(updated_at, GETDATE())
    FROM APP_ETL_Agents_OLD a
    WHERE NOT EXISTS (
        SELECT 1 FROM APP_ETL_Agents_Monitoring m
        WHERE m.agent_id = CAST(a.agent_id AS VARCHAR(100))
    );

    PRINT '[OK] ' + CAST(@@ROWCOUNT AS VARCHAR) + ' agent(s) migres vers APP_ETL_Agents_Monitoring';
END
ELSE
    PRINT '[INFO] Pas de donnees a migrer (APP_ETL_Agents_OLD absente)';
GO

-- ============================================================
-- 6. CREER APP_ETL_Agent_Commands dans la centrale
--    (les commandes restent dans la centrale car elles viennent
--     du superadmin vers les agents, via heartbeat pull)
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Agent_Commands' AND xtype='U')
BEGIN
    CREATE TABLE APP_ETL_Agent_Commands (
        id              INT IDENTITY(1,1) PRIMARY KEY,
        agent_id        VARCHAR(100) NOT NULL,
        command_type    VARCHAR(50)  NOT NULL,
        command_data    NVARCHAR(MAX),
        priority        INT DEFAULT 5,
        status          VARCHAR(20)  DEFAULT 'pending',
        created_at      DATETIME DEFAULT GETDATE(),
        acknowledged_at DATETIME,
        completed_at    DATETIME,
        expires_at      DATETIME,
        result          NVARCHAR(MAX),
        error_message   NVARCHAR(MAX)
    );
    CREATE INDEX IX_ETL_Commands_agent ON APP_ETL_Agent_Commands(agent_id, status, priority);
    PRINT '[OK] APP_ETL_Agent_Commands creee (dans centrale — pull par les agents)';
END
ELSE
    PRINT '[SKIP] APP_ETL_Agent_Commands existe deja';
GO

-- ============================================================
-- 7. MIGRER les commandes en attente → nouvelle table
-- ============================================================
IF EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Agent_Commands_OLD' AND xtype='U')
BEGIN
    -- Renommer l ancienne si elle existe
    IF EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Agent_Commands' AND xtype='U')
    BEGIN
        INSERT INTO APP_ETL_Agent_Commands (agent_id, command_type, command_data, priority, status, created_at, expires_at)
        SELECT CAST(agent_id AS VARCHAR(100)), command_type, command_data, priority, status, created_at, expires_at
        FROM APP_ETL_Agent_Commands_OLD
        WHERE status = 'pending'
          AND (expires_at IS NULL OR expires_at > GETDATE());
        PRINT '[OK] Commandes pending migrees : ' + CAST(@@ROWCOUNT AS VARCHAR);
    END
END
GO

-- ============================================================
-- 8. INDEXES sur APP_ETL_Agents_Monitoring
-- ============================================================
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='IX_ETL_Monitoring_dwh_code')
    CREATE INDEX IX_ETL_Monitoring_dwh_code ON APP_ETL_Agents_Monitoring(dwh_code);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='IX_ETL_Monitoring_statut')
    CREATE INDEX IX_ETL_Monitoring_statut   ON APP_ETL_Agents_Monitoring(statut);
GO

-- ============================================================
-- 9. RESUME
-- ============================================================
PRINT '';
PRINT '============================================================';
PRINT ' STEP 1 TERMINE — BASE CENTRALE';
PRINT '------------------------------------------------------------';
PRINT ' Backup :';
PRINT '   APP_ETL_Agents        → APP_ETL_Agents_OLD';
PRINT '   APP_ETL_Agent_Tables  → APP_ETL_Agent_Tables_OLD';
PRINT '   APP_ETL_Agent_Sync_Log→ APP_ETL_Agent_Sync_Log_OLD';
PRINT ' Nouvelles tables :';
PRINT '   APP_ETL_Agents_Monitoring (metriques uniquement)';
PRINT '   APP_ETL_Agent_Commands    (commandes pull agents)';
PRINT ' Etape suivante :';
PRINT '   Executer 008_migrate_agents_client_template.sql';
PRINT '   sur chaque base client OptiBoard_cltXXX';
PRINT '   puis lancer : python migrate_agents.py';
PRINT '============================================================';
GO
