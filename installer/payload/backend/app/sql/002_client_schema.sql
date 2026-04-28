-- ============================================================
-- SCHEMA BASE CLIENT : OptiBoard_cltXXX
-- Serveur du CLIENT (ou serveur distant si client connecte)
-- Contient : users locaux, droits, personnalisations, scheduler,
--            agents ETL (config complete), ETL tables publiees,
--            colonnes choisies, historique MAJ, datasources
--
-- LOGIQUE METIER :
--   - Le client est PROPRIETAIRE de ses agents (config complete ici)
--   - Le central ne voit que les metriques de monitoring (pas les credentials)
--   - APP_ETL_Agents ici = config complete + credentials Sage
--   - APP_ETL_Published_Colonnes = colonnes choisies par le client
--   - APP_Update_History = traçabilite de chaque MAJ recue du central
--   - Clients autonomes : cette base tourne en LOCAL, sans internet
--   - Clients connectes : cette base est sur le serveur distant
-- ============================================================

-- Remplacer XXX par le code client (ex: ALBG, ESSAIDI...)
-- Ex: USE OptiBoard_cltALBG;
USE OptiBoard_cltXXX;
GO

-- ============================================================
-- 1. UTILISATEURS LOCAUX DU CLIENT
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Users' AND xtype='U')
CREATE TABLE APP_Users (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    username        VARCHAR(50) UNIQUE NOT NULL,
    password_hash   VARCHAR(64) NOT NULL,
    nom             NVARCHAR(100) NOT NULL,
    prenom          NVARCHAR(100),
    email           VARCHAR(200),
    role            VARCHAR(20) DEFAULT 'user', -- admin_client, user
    actif           BIT DEFAULT 1,
    date_creation   DATETIME DEFAULT GETDATE(),
    derniere_connexion DATETIME
);
GO

-- ============================================================
-- 2. DROITS USER <-> DWH (geres par le client, invisibles du central)
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_UserDWH' AND xtype='U')
CREATE TABLE APP_UserDWH (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    user_id         INT NOT NULL REFERENCES APP_Users(id) ON DELETE CASCADE,
    dwh_code        VARCHAR(50) NOT NULL,         -- code du DWH accessible
    role_dwh        VARCHAR(30) DEFAULT 'user',   -- admin_client, user
    is_default      BIT DEFAULT 0,               -- DWH ouvert par defaut
    societes        NVARCHAR(MAX),               -- JSON ["SOC1","SOC2"] ou NULL = toutes
    date_attribution DATETIME DEFAULT GETDATE(),
    UNIQUE(user_id, dwh_code)
);
GO

-- ============================================================
-- 3. AGENTS ETL (config complete - propriete du client)
-- Logique metier :
--   C'est ici que le client configure ses agents ETL.
--   Le central n'a PAS acces a ces donnees en ecriture.
--   Pour les clients connectes : l'agent lit sa config depuis cette base
--   Pour les clients autonomes : l'agent lit sa config en local
--   Un agent = une connexion Sage (un serveur Sage peut avoir N societes)
--   Le champ api_key_hash sert a authentifier l'agent aupres du portail
--   local uniquement (pas du central).
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Agents' AND xtype='U')
CREATE TABLE APP_ETL_Agents (
    id                          INT IDENTITY(1,1) PRIMARY KEY,
    agent_id                    VARCHAR(100) UNIQUE NOT NULL,  -- GUID genere a l'installation
    nom                         NVARCHAR(200) NOT NULL,
    description                 NVARCHAR(500),
    -- Connexion Sage (credentials stockes cote client uniquement)
    sage_server                 VARCHAR(200) NOT NULL,
    sage_database               VARCHAR(100) NOT NULL,
    sage_username               VARCHAR(100),
    sage_password               VARCHAR(200),
    -- Configuration synchronisation
    sync_interval_secondes      INT DEFAULT 300,               -- intervalle entre syncs (defaut 5 min)
    heartbeat_interval_secondes INT DEFAULT 30,
    batch_size                  INT DEFAULT 10000,
    -- Options
    is_active                   BIT DEFAULT 1,
    auto_start                  BIT DEFAULT 1,                 -- demarre automatiquement au boot
    -- Statut local (mis a jour par l'agent)
    statut                      VARCHAR(20) DEFAULT 'inactif'
                                CHECK (statut IN ('actif','inactif','erreur','inactif')),
    last_heartbeat              DATETIME,
    last_sync                   DATETIME,
    last_sync_statut            VARCHAR(20),
    consecutive_failures        INT DEFAULT 0,
    total_syncs                 INT DEFAULT 0,
    total_lignes_sync           BIGINT DEFAULT 0,
    -- Infos machine (remplies automatiquement au premier demarrage)
    hostname                    VARCHAR(200),
    ip_address                  VARCHAR(50),
    os_info                     VARCHAR(200),
    agent_version               VARCHAR(50),
    -- Auth portail local
    api_key_hash                VARCHAR(64),
    api_key_prefix              VARCHAR(20),
    created_at                  DATETIME DEFAULT GETDATE(),
    updated_at                  DATETIME DEFAULT GETDATE()
);
GO

-- ============================================================
-- 4. DASHBOARDS PERSONNALISES
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Dashboards' AND xtype='U')
CREATE TABLE APP_Dashboards (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    code            VARCHAR(100) UNIQUE NOT NULL,
    nom             NVARCHAR(200) NOT NULL,
    description     NVARCHAR(500),
    config          NVARCHAR(MAX),
    widgets         NVARCHAR(MAX),
    is_public       BIT DEFAULT 1,
    is_customized   BIT DEFAULT 0,  -- 1 = protege, le master ne peut pas ecraser
    created_by      INT,
    actif           BIT DEFAULT 1,
    date_creation   DATETIME DEFAULT GETDATE(),
    date_modification DATETIME DEFAULT GETDATE()
);
GO

-- ============================================================
-- 4. GRIDVIEWS PERSONNALISEES
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_GridViews' AND xtype='U')
CREATE TABLE APP_GridViews (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    code            VARCHAR(100) UNIQUE NOT NULL,
    nom             NVARCHAR(200) NOT NULL,
    description     NVARCHAR(500),
    query_template  NVARCHAR(MAX),
    columns_config  NVARCHAR(MAX),
    parameters      NVARCHAR(MAX),
    features        NVARCHAR(MAX),
    is_customized   BIT DEFAULT 0,
    actif           BIT DEFAULT 1,
    date_creation   DATETIME DEFAULT GETDATE(),
    date_modification DATETIME DEFAULT GETDATE()
);
GO

-- ============================================================
-- 5. PIVOTS PERSONNALISES
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Pivots_V2' AND xtype='U')
CREATE TABLE APP_Pivots_V2 (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    code            VARCHAR(100) UNIQUE NOT NULL,
    nom             NVARCHAR(200) NOT NULL,
    description     NVARCHAR(500),
    data_source_code VARCHAR(100),
    rows_config     NVARCHAR(MAX),
    columns_config  NVARCHAR(MAX),
    filters_config  NVARCHAR(MAX),
    values_config   NVARCHAR(MAX),
    formatting_rules NVARCHAR(MAX),
    source_params   NVARCHAR(MAX),
    is_customized   BIT DEFAULT 0,
    is_public       BIT DEFAULT 1,
    created_by      INT,
    actif           BIT DEFAULT 1,
    created_at      DATETIME DEFAULT GETDATE(),
    updated_at      DATETIME DEFAULT GETDATE()
);
GO

-- ============================================================
-- 6. MENUS PERSONNALISES
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Menus' AND xtype='U')
CREATE TABLE APP_Menus (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    code            VARCHAR(100) UNIQUE NOT NULL,
    nom             NVARCHAR(200) NOT NULL,
    icon            VARCHAR(100),
    url             VARCHAR(500),
    parent_code     VARCHAR(100),
    ordre           INT DEFAULT 0,
    type            VARCHAR(50),
    target_id       INT,
    roles           NVARCHAR(MAX),
    is_customized   BIT DEFAULT 0,
    actif           BIT DEFAULT 1,
    date_creation   DATETIME DEFAULT GETDATE()
);
GO

-- ============================================================
-- 7. SOURCES DE DONNEES (connexions DWH du client)
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_DataSources' AND xtype='U')
CREATE TABLE APP_DataSources (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    code            VARCHAR(100) UNIQUE NOT NULL,
    nom             NVARCHAR(200) NOT NULL,
    type            VARCHAR(50) DEFAULT 'sql',   -- sql, api, file
    -- Connexion specifique si differente du DWH principal
    db_server       VARCHAR(200),
    db_name         VARCHAR(100),
    db_user         VARCHAR(100),
    db_password     VARCHAR(200),
    query_template  NVARCHAR(MAX),
    parameters      NVARCHAR(MAX),
    description     NVARCHAR(500),
    is_customized   BIT DEFAULT 0,
    actif           BIT DEFAULT 1,
    created_by      INT,
    date_creation   DATETIME DEFAULT GETDATE()
);
GO

-- ============================================================
-- 8. ETL TABLES PUBLIEES (copie read-only depuis le central)
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Tables_Published' AND xtype='U')
CREATE TABLE APP_ETL_Tables_Published (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    code            VARCHAR(100) UNIQUE NOT NULL,  -- meme code que central
    table_name      VARCHAR(200) NOT NULL,
    target_table    VARCHAR(200) NOT NULL,
    source_query    NVARCHAR(MAX),
    primary_key_columns NVARCHAR(500),
    sync_type       VARCHAR(50) DEFAULT 'incremental',
    timestamp_column VARCHAR(100) DEFAULT 'cbModification',
    interval_minutes INT DEFAULT 5,
    priority        VARCHAR(20) DEFAULT 'normal',
    delete_detection BIT DEFAULT 0,
    description     NVARCHAR(500),
    version_centrale INT DEFAULT 1,               -- version recue du central
    -- Controle client (le seul droit du client)
    is_enabled      BIT DEFAULT 1,               -- le client peut activer/desactiver
    date_publication DATETIME DEFAULT GETDATE(),  -- quand le central a publie
    date_modification DATETIME DEFAULT GETDATE()  -- quand le client a modifie is_enabled
);
GO

-- ============================================================
-- 9. ETL COLONNES PUBLIEES (choix du client par table)
-- Logique metier :
--   Quand le central publie une table, il publie aussi ses colonnes
--   (via APP_ETL_Tables_Colonnes central).
--   Le client decide quelles colonnes optionnelles il veut inclure.
--   Les colonnes obligatoires (obligatoire=1) sont toujours incluses.
--   Cette table pilote la structure de la table DWH cible :
--   l'agent ETL genere le CREATE TABLE / ALTER TABLE selon ce choix.
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Published_Colonnes' AND xtype='U')
CREATE TABLE APP_ETL_Published_Colonnes (
    id                  INT IDENTITY(1,1) PRIMARY KEY,
    table_code          VARCHAR(100) NOT NULL REFERENCES APP_ETL_Tables_Published(code) ON DELETE CASCADE,
    nom_colonne         VARCHAR(200) NOT NULL,
    type_donnee         VARCHAR(50) NOT NULL,
    longueur            INT,
    -- Decision du client
    inclus              BIT DEFAULT 1,          -- 0 = exclu par le client (si non obligatoire)
    alias               NVARCHAR(200),          -- nom d'affichage personnalise dans les rapports
    -- Metadonnees recues du central
    obligatoire         BIT DEFAULT 0,          -- copie du flag central (ne peut pas etre modifie)
    version_ajout       INT DEFAULT 1,
    UNIQUE(table_code, nom_colonne)
);
GO

-- ============================================================
-- 10. ETL PROPOSITIONS DU CLIENT (soumises au central)
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Proposals' AND xtype='U')
CREATE TABLE APP_ETL_Proposals (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    table_name      VARCHAR(200) NOT NULL,
    target_table    VARCHAR(200),
    source_query    NVARCHAR(MAX),
    description     NVARCHAR(1000),
    justification   NVARCHAR(1000),
    statut          VARCHAR(20) DEFAULT 'en_attente', -- en_attente, validee, rejetee
    commentaire_central NVARCHAR(500),
    submitted_by    INT,                             -- user_id local
    date_creation   DATETIME DEFAULT GETDATE(),
    date_reponse    DATETIME
);
GO

-- ============================================================
-- 10. RAPPORTS PROGRAMMES (100% autonome, invisible du central)
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Scheduler_Jobs' AND xtype='U')
CREATE TABLE APP_Scheduler_Jobs (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    nom             NVARCHAR(200) NOT NULL,
    description     NVARCHAR(500),
    report_type     VARCHAR(50),   -- pivot, gridview, dashboard, export
    report_code     VARCHAR(100),
    export_format   VARCHAR(20) DEFAULT 'excel',  -- excel, pdf, csv
    frequency       VARCHAR(20),   -- daily, weekly, monthly, once
    schedule_time   VARCHAR(5) DEFAULT '08:00',   -- HH:MM
    schedule_day    INT,           -- 1-7 weekly, 1-31 monthly
    recipients      NVARCHAR(MAX), -- JSON array emails
    cc_recipients   NVARCHAR(MAX),
    filters         NVARCHAR(MAX),
    is_active       BIT DEFAULT 1,
    last_run        DATETIME,
    last_run_status VARCHAR(20),
    next_run        DATETIME,
    created_by      INT,
    date_creation   DATETIME DEFAULT GETDATE(),
    date_modification DATETIME DEFAULT GETDATE()
);
GO

-- ============================================================
-- 11. HISTORIQUE EXECUTION RAPPORTS
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Scheduler_History' AND xtype='U')
CREATE TABLE APP_Scheduler_History (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    job_id          INT NOT NULL REFERENCES APP_Scheduler_Jobs(id) ON DELETE CASCADE,
    statut          VARCHAR(20),   -- success, failed, running
    recipients_count INT DEFAULT 0,
    rows_exported   INT DEFAULT 0,
    error_message   NVARCHAR(MAX),
    duration_seconds FLOAT,
    date_execution  DATETIME DEFAULT GETDATE()
);
GO

-- ============================================================
-- 12. CONFIGURATION EMAIL DU CLIENT
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_EmailConfig' AND xtype='U')
CREATE TABLE APP_EmailConfig (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    smtp_host       VARCHAR(200) NOT NULL,
    smtp_port       INT DEFAULT 587,
    smtp_user       VARCHAR(200),
    smtp_password   VARCHAR(200),
    sender_name     NVARCHAR(200) DEFAULT 'OptiBoard Reporting',
    use_ssl         BIT DEFAULT 1,
    use_tls         BIT DEFAULT 0,
    is_active       BIT DEFAULT 1,
    date_creation   DATETIME DEFAULT GETDATE()
);
GO

-- ============================================================
-- 13. ETL LOGS DE SYNC (propres au client, invisibles du central)
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Sync_Log' AND xtype='U')
CREATE TABLE APP_ETL_Sync_Log (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    agent_id        VARCHAR(100),
    table_code      VARCHAR(100),
    table_name      VARCHAR(200),
    societe_code    VARCHAR(50),
    success         BIT,
    rows_extracted  INT DEFAULT 0,
    rows_inserted   INT DEFAULT 0,
    rows_updated    INT DEFAULT 0,
    rows_failed     INT DEFAULT 0,
    duration_seconds FLOAT,
    error_message   NVARCHAR(MAX),
    date_sync       DATETIME DEFAULT GETDATE()
);
GO

-- ============================================================
-- 14. HISTORIQUE DES MISES A JOUR (MAJ recues du central)
-- Logique metier :
--   Trace chaque element installe ou mis a jour depuis le central.
--   Permet au module MAJ de comparer version_installee vs version
--   disponible sur le central pour proposer une mise a jour.
--   statut 'rollback' = client a annule une MAJ (restaure version precedente)
--   Pour clients connectes : alimente automatiquement lors des publications
--   Pour clients autonomes : alimente lors de la connexion ponctuelle
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Update_History' AND xtype='U')
CREATE TABLE APP_Update_History (
    id                  INT IDENTITY(1,1) PRIMARY KEY,
    -- Type d'element mis a jour
    type_entite         VARCHAR(30) NOT NULL
                        CHECK (type_entite IN ('etl_table','dashboard','gridview','pivot','menu','datasource')),
    code_entite         VARCHAR(100) NOT NULL,        -- code de l'element (meme code que central)
    nom_entite          NVARCHAR(200),
    -- Versions
    version_precedente  INT,                          -- NULL si premiere installation
    version_installee   INT NOT NULL,
    -- Statut de la MAJ
    statut              VARCHAR(20) DEFAULT 'succes'
                        CHECK (statut IN ('succes','echec','rollback')),
    message_erreur      NVARCHAR(500),
    -- Qui / quand
    installe_par        INT REFERENCES APP_Users(id), -- NULL si automatique
    date_installation   DATETIME DEFAULT GETDATE()
);
GO

-- ============================================================
-- 15. COMMANDES ETL (envoyees depuis le portail, lues par l'agent)
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Agent_Commands' AND xtype='U')
CREATE TABLE APP_ETL_Agent_Commands (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    agent_id        VARCHAR(100) NOT NULL,
    command_type    VARCHAR(50) NOT NULL,   -- sync_now | sync_table | pause | resume
    command_data    NVARCHAR(MAX),          -- JSON optionnel (ex: {"table_name": "..."})
    priority        INT DEFAULT 1,
    status          VARCHAR(20) DEFAULT 'pending'
                    CHECK (status IN ('pending','processing','completed','failed','cancelled')),
    created_at      DATETIME DEFAULT GETDATE(),
    expires_at      DATETIME,
    executed_at     DATETIME,
    result          NVARCHAR(MAX)
);
GO

PRINT 'Schema client OptiBoard_cltXXX cree avec succes';
GO
