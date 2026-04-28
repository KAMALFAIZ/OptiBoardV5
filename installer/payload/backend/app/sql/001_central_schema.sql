-- ============================================================
-- SCHEMA BASE CENTRALE : OptiBoard_SaaS
-- Serveur KASOFT uniquement
-- Contient : registre clients, superadmins, templates, licences, ETL config
-- NE CONTIENT AUCUNE DONNEE CLIENT
--
-- LOGIQUE METIER :
--   - Central = catalogue officiel ETL + templates Builder
--   - Client   = config agents, tables choisies, builder personnalise
--   - APP_ETL_Agents ici = MONITORING UNIQUEMENT (pas de credentials Sage)
--   - Les credentials et config agents sont dans la base CLIENT
-- ============================================================

USE OptiBoard_SaaS;
GO

-- ============================================================
-- 1. REGISTRE DES CLIENTS DWH
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_DWH' AND xtype='U')
CREATE TABLE APP_DWH (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    code            VARCHAR(50)  UNIQUE NOT NULL,
    nom             NVARCHAR(200) NOT NULL,
    raison_sociale  NVARCHAR(200),
    adresse         NVARCHAR(300),
    ville           NVARCHAR(100),
    pays            VARCHAR(50) DEFAULT 'Maroc',
    telephone       VARCHAR(50),
    email           VARCHAR(200),
    logo_url        VARCHAR(500),
    -- Connexion base DWH du client (chez lui)
    serveur_dwh     VARCHAR(200),
    base_dwh        VARCHAR(100),
    user_dwh        VARCHAR(100),
    password_dwh    VARCHAR(200),
    -- Connexion base client OptiBoard_cltXXX (chez lui ou distant)
    client_db_server    VARCHAR(200),
    client_db_name      VARCHAR(100),
    client_db_user      VARCHAR(100),
    client_db_password  VARCHAR(200),
    -- Type de deploiement du client
    -- 'connecte'  : portail sur serveur distant, DWH sur serveur distant
    -- 'autonome'  : portail + DWH 100% local, connexion internet ponctuelle (MAJ uniquement)
    type_client     VARCHAR(20) DEFAULT 'connecte' CHECK (type_client IN ('connecte','autonome')),
    actif           BIT DEFAULT 1,
    date_creation   DATETIME DEFAULT GETDATE(),
    date_modification DATETIME DEFAULT GETDATE()
);
GO

-- ============================================================
-- 2. UTILISATEURS SUPERADMIN (central uniquement)
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Users' AND xtype='U')
CREATE TABLE APP_Users (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    username        VARCHAR(50) UNIQUE NOT NULL,
    password_hash   VARCHAR(64) NOT NULL,
    nom             NVARCHAR(100) NOT NULL,
    prenom          NVARCHAR(100),
    email           VARCHAR(200),
    role_global     VARCHAR(20) DEFAULT 'superadmin', -- superadmin uniquement ici
    actif           BIT DEFAULT 1,
    date_creation   DATETIME DEFAULT GETDATE(),
    derniere_connexion DATETIME
);
GO

-- ============================================================
-- 3. LICENCES
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Licenses' AND xtype='U')
CREATE TABLE APP_Licenses (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    dwh_code        VARCHAR(50) NOT NULL REFERENCES APP_DWH(code),
    license_key     VARCHAR(500) UNIQUE NOT NULL,
    organisation    NVARCHAR(200),
    plan            VARCHAR(50) DEFAULT 'starter', -- starter, professional, enterprise
    max_users       INT DEFAULT 5,
    max_dwh         INT DEFAULT 1,
    features        NVARCHAR(MAX), -- JSON ["dashboard","ventes","stocks",...]
    date_debut      DATE,
    date_expiration DATE,
    machine_id      VARCHAR(200),
    deployment_mode VARCHAR(50) DEFAULT 'on-premise',
    actif           BIT DEFAULT 1,
    date_creation   DATETIME DEFAULT GETDATE()
);
GO

-- ============================================================
-- 4. TEMPLATES MASTER (publies vers les clients)
-- ============================================================

-- Templates Dashboards
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Dashboards_Templates' AND xtype='U')
CREATE TABLE APP_Dashboards_Templates (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    code            VARCHAR(100) UNIQUE NOT NULL,
    nom             NVARCHAR(200) NOT NULL,
    description     NVARCHAR(500),
    config          NVARCHAR(MAX),
    widgets         NVARCHAR(MAX),
    is_public       BIT DEFAULT 1,
    actif           BIT DEFAULT 1,
    date_creation   DATETIME DEFAULT GETDATE(),
    date_modification DATETIME DEFAULT GETDATE()
);
GO

-- Templates GridViews
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_GridViews_Templates' AND xtype='U')
CREATE TABLE APP_GridViews_Templates (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    code            VARCHAR(100) UNIQUE NOT NULL,
    nom             NVARCHAR(200) NOT NULL,
    description     NVARCHAR(500),
    query_template  NVARCHAR(MAX),
    columns_config  NVARCHAR(MAX),
    parameters      NVARCHAR(MAX),
    features        NVARCHAR(MAX),
    actif           BIT DEFAULT 1,
    date_creation   DATETIME DEFAULT GETDATE(),
    date_modification DATETIME DEFAULT GETDATE()
);
GO

-- Templates Pivots
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Pivots_Templates' AND xtype='U')
CREATE TABLE APP_Pivots_Templates (
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
    actif           BIT DEFAULT 1,
    date_creation   DATETIME DEFAULT GETDATE(),
    date_modification DATETIME DEFAULT GETDATE()
);
GO

-- Templates Menus
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Menus_Templates' AND xtype='U')
CREATE TABLE APP_Menus_Templates (
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
    actif           BIT DEFAULT 1,
    date_creation   DATETIME DEFAULT GETDATE()
);
GO

-- Templates DataSources
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_DataSources_Templates' AND xtype='U')
CREATE TABLE APP_DataSources_Templates (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    code            VARCHAR(100) UNIQUE NOT NULL,
    nom             NVARCHAR(200) NOT NULL,
    type            VARCHAR(50),
    query_template  NVARCHAR(MAX),
    parameters      NVARCHAR(MAX),
    description     NVARCHAR(500),
    date_creation   DATETIME DEFAULT GETDATE()
);
GO

-- ============================================================
-- 5. ETL TABLES CONFIG (cree par central, publie vers clients)
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Tables_Config' AND xtype='U')
CREATE TABLE APP_ETL_Tables_Config (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    code            VARCHAR(100) UNIQUE NOT NULL,     -- identifiant unique de la table
    table_name      VARCHAR(200) NOT NULL,            -- nom table source Sage
    target_table    VARCHAR(200) NOT NULL,            -- nom table cible DWH
    source_query    NVARCHAR(MAX),                    -- requete SQL source
    primary_key_columns NVARCHAR(500),               -- colonnes PK (JSON array)
    sync_type       VARCHAR(50) DEFAULT 'incremental', -- incremental, full
    timestamp_column VARCHAR(100) DEFAULT 'cbModification',
    interval_minutes INT DEFAULT 5,
    priority        VARCHAR(20) DEFAULT 'normal',
    delete_detection BIT DEFAULT 0,
    description     NVARCHAR(500),
    version         INT DEFAULT 1,                   -- version pour suivi changements
    actif           BIT DEFAULT 1,
    created_by      VARCHAR(100),
    date_creation   DATETIME DEFAULT GETDATE(),
    date_modification DATETIME DEFAULT GETDATE()
);
GO

-- ============================================================
-- 6. ETL COLONNES DU CATALOGUE
-- Logique metier :
--   Chaque table du catalogue a des colonnes officielles.
--   - obligatoire = le client ne peut PAS exclure cette colonne
--   - visible_client = affiche dans l'UI client pour selection
--   Quand le central publie une MAJ de table, les nouvelles colonnes
--   sont proposees au client ; les existantes ne sont pas ecrasees.
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Tables_Colonnes' AND xtype='U')
CREATE TABLE APP_ETL_Tables_Colonnes (
    id                  INT IDENTITY(1,1) PRIMARY KEY,
    etl_table_code      VARCHAR(100) NOT NULL REFERENCES APP_ETL_Tables_Config(code) ON DELETE CASCADE,
    nom_colonne         VARCHAR(200) NOT NULL,
    type_donnee         VARCHAR(50) NOT NULL,          -- VARCHAR, INT, DECIMAL, DATE, BIT...
    longueur            INT,                           -- pour VARCHAR : longueur max
    description         NVARCHAR(500),
    -- Regles metier
    obligatoire         BIT DEFAULT 0,                -- 1 = client ne peut pas exclure
    visible_client      BIT DEFAULT 1,                -- 0 = colonne interne, invisible dans UI
    valeur_defaut       NVARCHAR(200),                -- valeur par defaut si NULL dans Sage
    -- Suivi versions
    version_ajout       INT DEFAULT 1,                -- version de la table ou cette colonne est apparue
    version_supprime    INT,                          -- NULL si encore active, sinon version ou supprimee
    actif               BIT DEFAULT 1,
    UNIQUE(etl_table_code, nom_colonne)
);
GO

-- ============================================================
-- 7. ETL PROPOSITIONS (clients proposent de nouvelles tables)
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Proposals' AND xtype='U')
CREATE TABLE APP_ETL_Proposals (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    dwh_code        VARCHAR(50) NOT NULL,             -- client qui propose
    table_name      VARCHAR(200) NOT NULL,            -- table souhaitee
    target_table    VARCHAR(200),
    source_query    NVARCHAR(MAX),
    description     NVARCHAR(1000),
    justification   NVARCHAR(1000),                  -- pourquoi ce besoin
    statut          VARCHAR(20) DEFAULT 'en_attente', -- en_attente, validee, rejetee
    commentaire_central NVARCHAR(500),               -- reponse du superadmin
    validated_by    VARCHAR(100),
    date_validation DATETIME,
    date_creation   DATETIME DEFAULT GETDATE()
);
GO

-- ============================================================
-- 8. AGENTS ETL - MONITORING GLOBAL UNIQUEMENT
-- Logique metier :
--   La configuration complete des agents (credentials Sage, intervalles,
--   batch_size...) est geree par le CLIENT dans sa propre base.
--   Le central ne stocke ici que les donnees de MONITORING :
--   statut, heartbeat, metriques. Ces donnees sont poussees par
--   l'agent via API (heartbeat endpoint) pour les clients connectes.
--   Les clients autonomes n'alimentent PAS cette table.
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Agents_Monitoring' AND xtype='U')
CREATE TABLE APP_ETL_Agents_Monitoring (
    id                      INT IDENTITY(1,1) PRIMARY KEY,
    agent_id                VARCHAR(100) UNIQUE NOT NULL,  -- meme ID que dans base client
    dwh_code                VARCHAR(50) NOT NULL REFERENCES APP_DWH(code),
    nom                     NVARCHAR(200) NOT NULL,
    -- Infos machine (remontees par l'agent)
    hostname                VARCHAR(200),
    ip_address              VARCHAR(50),
    os_info                 VARCHAR(200),
    agent_version           VARCHAR(50),
    -- Statut temps reel (mis a jour via heartbeat)
    statut                  VARCHAR(20) DEFAULT 'inconnu'
                            CHECK (statut IN ('actif','inactif','erreur','inconnu')),
    last_heartbeat          DATETIME,
    last_sync               DATETIME,
    last_sync_statut        VARCHAR(20),
    consecutive_failures    INT DEFAULT 0,
    -- Metriques globales (incrementees par l'agent)
    total_syncs             INT DEFAULT 0,
    total_lignes_sync       BIGINT DEFAULT 0,
    -- Pas de : sage_server, sage_password, sync_interval, batch_size
    -- Ces champs sont dans APP_ETL_Agents de la base CLIENT
    date_enregistrement     DATETIME DEFAULT GETDATE(),
    date_modification       DATETIME DEFAULT GETDATE()
);
GO

-- ============================================================
-- 9. PUBLICATION LOG (trace des publications master -> clients)
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Publish_Log' AND xtype='U')
CREATE TABLE APP_Publish_Log (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    entity_type     VARCHAR(50),   -- gridviews, pivots, dashboards, etl_tables
    entity_code     VARCHAR(100),
    dwh_code        VARCHAR(50),   -- client cible
    action          VARCHAR(20),   -- published, skipped, failed
    published_by    VARCHAR(100),
    details         NVARCHAR(500),
    date_publication DATETIME DEFAULT GETDATE()
);
GO

-- ============================================================
-- Tables de configuration par agent (catalogue côté central)
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Agent_Tables' AND xtype='U')
CREATE TABLE APP_ETL_Agent_Tables (
    id                  INT IDENTITY(1,1) PRIMARY KEY,
    agent_id            VARCHAR(100) NOT NULL,
    table_name          VARCHAR(200) NOT NULL,
    source_query        NVARCHAR(MAX),
    target_table        VARCHAR(200),
    societe_code        VARCHAR(50) NOT NULL DEFAULT '',
    primary_key_columns NVARCHAR(500),
    sync_type           VARCHAR(20) DEFAULT 'incremental',
    timestamp_column    VARCHAR(100) DEFAULT 'cbModification',
    interval_minutes    INT DEFAULT 5,
    priority            VARCHAR(20) DEFAULT 'normal',
    is_enabled          BIT DEFAULT 1,
    delete_detection    BIT DEFAULT 0,
    description         NVARCHAR(500),
    -- Heritage depuis le catalogue maitre
    is_inherited        BIT NOT NULL DEFAULT 0,
    is_customized       BIT NOT NULL DEFAULT 0,
    -- Stats
    last_sync           DATETIME,
    last_sync_status    VARCHAR(20),
    last_sync_rows      INT DEFAULT 0,
    last_error          NVARCHAR(MAX),
    created_at          DATETIME DEFAULT GETDATE(),
    updated_at          DATETIME DEFAULT GETDATE()
);
GO

PRINT 'Schema central OptiBoard_SaaS cree avec succes';
GO
