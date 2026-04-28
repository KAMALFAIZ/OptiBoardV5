-- ============================================================
-- MIGRATION : Nouveau schema multi-tenant
-- A executer UNE SEULE FOIS sur les bases existantes
--
-- Ce script fait :
--   1. BASE CENTRALE : ajout type_client + APP_ETL_Tables_Colonnes
--                      + remplacement APP_ETL_Agents par APP_ETL_Agents_Monitoring
--   2. BASE CLIENT   : ajout APP_ETL_Agents (config complete)
--                      + APP_ETL_Published_Colonnes
--                      + APP_Update_History
-- ============================================================

-- ============================================================
-- PARTIE 1 : BASE CENTRALE OptiBoard_SaaS
-- ============================================================
USE OptiBoard_SaaS;
GO

-- 1.1 Ajouter type_client dans APP_DWH
IF NOT EXISTS (
    SELECT * FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME='APP_DWH' AND COLUMN_NAME='type_client'
)
BEGIN
    ALTER TABLE APP_DWH
    ADD type_client VARCHAR(20) DEFAULT 'connecte'
        CHECK (type_client IN ('connecte','autonome'));
    PRINT '  [OK] APP_DWH.type_client ajoute';
END
ELSE
    PRINT '  [SKIP] APP_DWH.type_client existe deja';
GO

-- 1.2 Creer APP_ETL_Tables_Colonnes
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Tables_Colonnes' AND xtype='U')
BEGIN
    CREATE TABLE APP_ETL_Tables_Colonnes (
        id                  INT IDENTITY(1,1) PRIMARY KEY,
        etl_table_code      VARCHAR(100) NOT NULL REFERENCES APP_ETL_Tables_Config(code) ON DELETE CASCADE,
        nom_colonne         VARCHAR(200) NOT NULL,
        type_donnee         VARCHAR(50) NOT NULL,
        longueur            INT,
        description         NVARCHAR(500),
        obligatoire         BIT DEFAULT 0,
        visible_client      BIT DEFAULT 1,
        valeur_defaut       NVARCHAR(200),
        version_ajout       INT DEFAULT 1,
        version_supprime    INT,
        actif               BIT DEFAULT 1,
        UNIQUE(etl_table_code, nom_colonne)
    );
    PRINT '  [OK] APP_ETL_Tables_Colonnes creee';
END
ELSE
    PRINT '  [SKIP] APP_ETL_Tables_Colonnes existe deja';
GO

-- 1.3 Creer APP_ETL_Agents_Monitoring (remplace APP_ETL_Agents en central)
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Agents_Monitoring' AND xtype='U')
BEGIN
    CREATE TABLE APP_ETL_Agents_Monitoring (
        id                      INT IDENTITY(1,1) PRIMARY KEY,
        agent_id                VARCHAR(100) UNIQUE NOT NULL,
        dwh_code                VARCHAR(50) NOT NULL REFERENCES APP_DWH(code),
        nom                     NVARCHAR(200) NOT NULL,
        hostname                VARCHAR(200),
        ip_address              VARCHAR(50),
        os_info                 VARCHAR(200),
        agent_version           VARCHAR(50),
        statut                  VARCHAR(20) DEFAULT 'inconnu'
                                CHECK (statut IN ('actif','inactif','erreur','inconnu')),
        last_heartbeat          DATETIME,
        last_sync               DATETIME,
        last_sync_statut        VARCHAR(20),
        consecutive_failures    INT DEFAULT 0,
        total_syncs             INT DEFAULT 0,
        total_lignes_sync       BIGINT DEFAULT 0,
        date_enregistrement     DATETIME DEFAULT GETDATE(),
        date_modification       DATETIME DEFAULT GETDATE()
    );
    PRINT '  [OK] APP_ETL_Agents_Monitoring creee';
END
ELSE
    PRINT '  [SKIP] APP_ETL_Agents_Monitoring existe deja';
GO

-- 1.4 Migrer les donnees de monitoring depuis APP_ETL_Agents vers APP_ETL_Agents_Monitoring
IF EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Agents' AND xtype='U')
BEGIN
    INSERT INTO APP_ETL_Agents_Monitoring (
        agent_id, dwh_code, nom,
        hostname, ip_address, os_info, agent_version,
        statut, last_heartbeat, last_sync, last_sync_statut,
        consecutive_failures, total_syncs, total_lignes_sync,
        date_enregistrement
    )
    SELECT
        agent_id, dwh_code, name,
        hostname, ip_address, os_info, agent_version,
        CASE status
            WHEN 'active'   THEN 'actif'
            WHEN 'inactive' THEN 'inactif'
            WHEN 'error'    THEN 'erreur'
            ELSE 'inconnu'
        END,
        last_heartbeat, last_sync, last_sync_status,
        consecutive_failures, total_syncs, total_rows_synced,
        created_at
    FROM APP_ETL_Agents
    WHERE agent_id NOT IN (SELECT agent_id FROM APP_ETL_Agents_Monitoring);

    PRINT '  [OK] Donnees migrees de APP_ETL_Agents vers APP_ETL_Agents_Monitoring';
    PRINT '  [INFO] APP_ETL_Agents (ancienne) conservee - supprimer manuellement apres validation';
END
GO

PRINT '[CENTRAL] Migration terminee';
GO


-- ============================================================
-- PARTIE 2 : BASES CLIENTS
-- A executer sur chaque base OptiBoard_cltXXX
-- Remplacer XXX par le code client avant execution
-- ============================================================

-- USE OptiBoard_cltXXX;  -- <-- decommenter et remplacer XXX
-- GO

-- 2.1 Creer APP_ETL_Agents (config complete cote client)
-- IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Agents' AND xtype='U')
-- BEGIN
--     CREATE TABLE APP_ETL_Agents ( ... );
--     PRINT '  [OK] APP_ETL_Agents creee dans base client';
-- END

-- NOTE : Le script complet de creation des tables client est dans 002_client_schema.sql
-- Executer 002_client_schema.sql directement sur chaque base client pour creer
-- les nouvelles tables (APP_ETL_Agents, APP_ETL_Published_Colonnes, APP_Update_History)
-- Les tables existantes ne seront pas recrees (IF NOT EXISTS)

PRINT '';
PRINT '=== INSTRUCTIONS MIGRATION BASES CLIENTS ===';
PRINT '  Executer 002_client_schema.sql sur chaque base OptiBoard_cltXXX';
PRINT '  Les nouvelles tables seront creees sans toucher les existantes.';
PRINT '  Ensuite migrer les agents depuis la base centrale si necessaire.';
PRINT '============================================';
GO
