-- =============================================================
-- Migration 010 — Ajout APP_ETL_Agents dans toutes les bases client
-- =============================================================
-- À exécuter sur CHAQUE base client OptiBoard_cltXXX
-- (ou utiliser le script Python migrate_all_clients_step2.py)
--
-- Si vous exécutez manuellement, remplacez OptiBoard_cltXXX
-- par le nom réel de la base client (ex: OptiBoard_cltQSD)
-- =============================================================

-- USE [OptiBoard_cltXXX];
-- GO

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Agents' AND xtype='U')
BEGIN
    CREATE TABLE APP_ETL_Agents (
        id                          INT IDENTITY(1,1) PRIMARY KEY,
        agent_id                    VARCHAR(100) UNIQUE NOT NULL,
        nom                         NVARCHAR(200) NOT NULL,
        description                 NVARCHAR(500) NULL,
        -- Connexion Sage (credentials stockes cote client uniquement)
        sage_server                 VARCHAR(200) NULL,
        sage_database               VARCHAR(100) NULL,
        sage_username               VARCHAR(100) NULL,
        sage_password               VARCHAR(200) NULL,
        -- Configuration synchronisation
        sync_interval_secondes      INT  DEFAULT 300,
        heartbeat_interval_secondes INT  DEFAULT 30,
        batch_size                  INT  DEFAULT 10000,
        -- Options
        is_active                   BIT  DEFAULT 1,
        auto_start                  BIT  DEFAULT 1,
        -- Statut local
        statut                      VARCHAR(20) DEFAULT 'inactif',
        last_heartbeat              DATETIME NULL,
        last_sync                   DATETIME NULL,
        last_sync_statut            VARCHAR(20) NULL,
        consecutive_failures        INT  DEFAULT 0,
        total_syncs                 INT  DEFAULT 0,
        total_lignes_sync           BIGINT DEFAULT 0,
        -- Infos machine
        hostname                    VARCHAR(200) NULL,
        ip_address                  VARCHAR(50)  NULL,
        os_info                     VARCHAR(200) NULL,
        agent_version               VARCHAR(50)  NULL,
        -- Auth portail local
        api_key_hash                VARCHAR(64)  NULL,
        api_key_prefix              VARCHAR(20)  NULL,
        created_at                  DATETIME DEFAULT GETDATE(),
        updated_at                  DATETIME DEFAULT GETDATE()
    );

    IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='IX_CLIENT_ETL_Agents_agent_id')
        CREATE INDEX IX_CLIENT_ETL_Agents_agent_id ON APP_ETL_Agents(agent_id);

    PRINT 'APP_ETL_Agents creee avec succes';
END
ELSE
BEGIN
    PRINT 'APP_ETL_Agents existe deja - aucune action';
END
