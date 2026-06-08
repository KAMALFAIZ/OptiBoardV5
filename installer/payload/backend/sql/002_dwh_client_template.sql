-- =====================================================
-- Script d'initialisation - BASE CLIENT DWH
-- Template pour creer une nouvelle base DWH_[ClientName]
-- =====================================================
-- USAGE: Remplacer {DWH_NAME} par le nom de la base client
--        Ex: DWH_Alboughaze, DWH_ClientXYZ
-- =====================================================

-- Creer la base si elle n'existe pas
-- EXEC('CREATE DATABASE {DWH_NAME}');
-- GO

-- USE {DWH_NAME};
-- GO

-- =====================================================
-- SECTION 1: TABLES DE DONNEES BI
-- =====================================================

-- ===================== Clients =====================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Clients' AND xtype='U')
CREATE TABLE Clients (
    id INT IDENTITY(1,1) PRIMARY KEY,
    societe_code VARCHAR(50) NOT NULL,             -- Code societe Sage source
    code_client VARCHAR(50) NOT NULL,              -- CT_Num dans Sage
    nom NVARCHAR(200) NOT NULL,
    adresse NVARCHAR(500),
    ville NVARCHAR(100),
    code_postal VARCHAR(20),
    pays NVARCHAR(100),
    telephone VARCHAR(50),
    email VARCHAR(200),
    -- Classification
    categorie VARCHAR(50),                         -- A, B, C ou categorie custom
    secteur NVARCHAR(100),                         -- Secteur d'activite
    commercial_code VARCHAR(50),                   -- Code commercial assigne
    commercial_nom NVARCHAR(200),
    zone_geo NVARCHAR(100),                        -- Zone geographique
    canal VARCHAR(50),                             -- Canal de distribution
    -- Financier
    encours_autorise DECIMAL(18,2) DEFAULT 0,
    mode_reglement VARCHAR(50),
    delai_paiement INT DEFAULT 30,
    -- Metadata
    date_creation_sage DATETIME,
    date_sync DATETIME DEFAULT GETDATE(),
    actif BIT DEFAULT 1,
    CONSTRAINT UQ_Client UNIQUE (societe_code, code_client)
);
GO

-- ===================== Articles =====================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Articles' AND xtype='U')
CREATE TABLE Articles (
    id INT IDENTITY(1,1) PRIMARY KEY,
    societe_code VARCHAR(50) NOT NULL,
    code_article VARCHAR(50) NOT NULL,             -- AR_Ref dans Sage
    designation NVARCHAR(300) NOT NULL,
    -- Classification
    famille VARCHAR(100),
    sous_famille VARCHAR(100),
    gamme NVARCHAR(100),
    marque NVARCHAR(100),
    -- Prix et couts
    prix_vente DECIMAL(18,4) DEFAULT 0,
    prix_achat DECIMAL(18,4) DEFAULT 0,
    -- Unites
    unite_vente VARCHAR(20),
    unite_stock VARCHAR(20),
    -- Metadata
    date_creation_sage DATETIME,
    date_sync DATETIME DEFAULT GETDATE(),
    actif BIT DEFAULT 1,
    CONSTRAINT UQ_Article UNIQUE (societe_code, code_article)
);
GO

-- ===================== Entete_Ventes =====================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Entete_Ventes' AND xtype='U')
CREATE TABLE Entete_Ventes (
    id INT IDENTITY(1,1) PRIMARY KEY,
    societe_code VARCHAR(50) NOT NULL,
    numero_piece VARCHAR(50) NOT NULL,             -- DO_Piece dans Sage
    type_document VARCHAR(20) NOT NULL,            -- FA, AV, BL, etc.
    date_piece DATE NOT NULL,
    -- Client
    code_client VARCHAR(50) NOT NULL,
    nom_client NVARCHAR(200),
    -- Commercial
    commercial_code VARCHAR(50),
    commercial_nom NVARCHAR(200),
    -- Montants
    montant_ht DECIMAL(18,2) DEFAULT 0,
    montant_tva DECIMAL(18,2) DEFAULT 0,
    montant_ttc DECIMAL(18,2) DEFAULT 0,
    montant_regle DECIMAL(18,2) DEFAULT 0,
    -- Remise
    remise_pied DECIMAL(18,2) DEFAULT 0,
    taux_remise DECIMAL(5,2) DEFAULT 0,
    -- Metadata
    date_sync DATETIME DEFAULT GETDATE(),
    CONSTRAINT UQ_Entete_Vente UNIQUE (societe_code, numero_piece, type_document)
);
GO

-- ===================== Lignes_Ventes =====================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Lignes_Ventes' AND xtype='U')
CREATE TABLE Lignes_Ventes (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    societe_code VARCHAR(50) NOT NULL,
    numero_piece VARCHAR(50) NOT NULL,
    type_document VARCHAR(20) NOT NULL,
    numero_ligne INT NOT NULL,
    date_piece DATE NOT NULL,
    -- Article
    code_article VARCHAR(50),
    designation NVARCHAR(300),
    famille VARCHAR(100),
    gamme NVARCHAR(100),
    -- Client
    code_client VARCHAR(50) NOT NULL,
    nom_client NVARCHAR(200),
    zone_geo NVARCHAR(100),
    canal VARCHAR(50),
    -- Commercial
    commercial_code VARCHAR(50),
    commercial_nom NVARCHAR(200),
    -- Quantites et prix
    quantite DECIMAL(18,4) DEFAULT 0,
    prix_unitaire DECIMAL(18,4) DEFAULT 0,
    taux_remise DECIMAL(5,2) DEFAULT 0,
    montant_remise DECIMAL(18,2) DEFAULT 0,
    -- Montants
    montant_ht DECIMAL(18,2) DEFAULT 0,
    montant_tva DECIMAL(18,2) DEFAULT 0,
    montant_ttc DECIMAL(18,2) DEFAULT 0,
    -- Cout et marge
    cout_revient DECIMAL(18,4) DEFAULT 0,
    marge DECIMAL(18,2) DEFAULT 0,
    taux_marge DECIMAL(5,2) DEFAULT 0,
    -- Metadata
    date_sync DATETIME DEFAULT GETDATE(),
    INDEX IX_Lignes_Ventes_societe (societe_code),
    INDEX IX_Lignes_Ventes_date (date_piece),
    INDEX IX_Lignes_Ventes_client (code_client),
    INDEX IX_Lignes_Ventes_article (code_article)
);
GO

-- ===================== Stock =====================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Stock' AND xtype='U')
CREATE TABLE Stock (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    societe_code VARCHAR(50) NOT NULL,
    code_article VARCHAR(50) NOT NULL,
    designation NVARCHAR(300),
    -- Classification
    famille VARCHAR(100),
    gamme NVARCHAR(100),
    -- Depot
    code_depot VARCHAR(50),
    nom_depot NVARCHAR(200),
    -- Quantites
    quantite_stock DECIMAL(18,4) DEFAULT 0,
    quantite_reservee DECIMAL(18,4) DEFAULT 0,
    quantite_commandee DECIMAL(18,4) DEFAULT 0,
    quantite_disponible AS (quantite_stock - quantite_reservee),
    -- Valorisation
    prix_moyen_pondere DECIMAL(18,4) DEFAULT 0,
    valeur_stock DECIMAL(18,2) DEFAULT 0,
    -- Rotation
    date_dernier_mouvement DATE,
    jours_sans_mouvement AS DATEDIFF(DAY, date_dernier_mouvement, GETDATE()),
    -- Metadata
    date_sync DATETIME DEFAULT GETDATE(),
    CONSTRAINT UQ_Stock UNIQUE (societe_code, code_article, code_depot),
    INDEX IX_Stock_societe (societe_code),
    INDEX IX_Stock_article (code_article)
);
GO

-- ===================== Mouvement_Stock =====================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Mouvement_Stock' AND xtype='U')
CREATE TABLE Mouvement_Stock (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    societe_code VARCHAR(50) NOT NULL,
    code_article VARCHAR(50) NOT NULL,
    code_depot VARCHAR(50),
    -- Mouvement
    date_mouvement DATE NOT NULL,
    type_mouvement VARCHAR(20),                    -- ENTREE, SORTIE, TRANSFERT
    numero_piece VARCHAR(50),
    -- Quantites
    quantite_entree DECIMAL(18,4) DEFAULT 0,
    quantite_sortie DECIMAL(18,4) DEFAULT 0,
    -- Valorisation
    prix_unitaire DECIMAL(18,4) DEFAULT 0,
    valeur_mouvement DECIMAL(18,2) DEFAULT 0,
    -- Stock resultant
    stock_avant DECIMAL(18,4) DEFAULT 0,
    stock_apres DECIMAL(18,4) DEFAULT 0,
    -- Metadata
    date_sync DATETIME DEFAULT GETDATE(),
    INDEX IX_Mvt_Stock_date (date_mouvement),
    INDEX IX_Mvt_Stock_article (code_article)
);
GO

-- ===================== BalanceAgee =====================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='BalanceAgee' AND xtype='U')
CREATE TABLE BalanceAgee (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    societe_code VARCHAR(50) NOT NULL,
    code_client VARCHAR(50) NOT NULL,
    nom_client NVARCHAR(200),
    -- Commercial
    commercial_code VARCHAR(50),
    commercial_nom NVARCHAR(200),
    zone_geo NVARCHAR(100),
    -- Tranches d'age
    non_echu DECIMAL(18,2) DEFAULT 0,
    tranche_0_30 DECIMAL(18,2) DEFAULT 0,
    tranche_31_60 DECIMAL(18,2) DEFAULT 0,
    tranche_61_90 DECIMAL(18,2) DEFAULT 0,
    tranche_91_120 DECIMAL(18,2) DEFAULT 0,
    tranche_plus_120 DECIMAL(18,2) DEFAULT 0,
    -- Totaux
    total_creance DECIMAL(18,2) DEFAULT 0,
    total_echu DECIMAL(18,2) DEFAULT 0,
    -- Metadata
    date_calcul DATE DEFAULT GETDATE(),
    date_sync DATETIME DEFAULT GETDATE(),
    INDEX IX_BalanceAgee_societe (societe_code),
    INDEX IX_BalanceAgee_client (code_client)
);
GO

-- ===================== Echeancier =====================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Echeancier' AND xtype='U')
CREATE TABLE Echeancier (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    societe_code VARCHAR(50) NOT NULL,
    code_client VARCHAR(50) NOT NULL,
    nom_client NVARCHAR(200),
    -- Document
    numero_piece VARCHAR(50) NOT NULL,
    date_piece DATE,
    date_echeance DATE NOT NULL,
    -- Montants
    montant_origine DECIMAL(18,2) DEFAULT 0,
    montant_regle DECIMAL(18,2) DEFAULT 0,
    montant_reste DECIMAL(18,2) DEFAULT 0,
    -- Calcul retard
    jours_retard AS CASE WHEN date_echeance < GETDATE() THEN DATEDIFF(DAY, date_echeance, GETDATE()) ELSE 0 END,
    -- Metadata
    date_sync DATETIME DEFAULT GETDATE(),
    INDEX IX_Echeancier_societe (societe_code),
    INDEX IX_Echeancier_client (code_client),
    INDEX IX_Echeancier_echeance (date_echeance)
);
GO

-- ===================== Commerciaux =====================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Commerciaux' AND xtype='U')
CREATE TABLE Commerciaux (
    id INT IDENTITY(1,1) PRIMARY KEY,
    societe_code VARCHAR(50) NOT NULL,
    code_commercial VARCHAR(50) NOT NULL,
    nom NVARCHAR(200) NOT NULL,
    prenom NVARCHAR(100),
    email VARCHAR(200),
    telephone VARCHAR(50),
    zone_geo NVARCHAR(100),
    -- Objectifs
    objectif_ca_annuel DECIMAL(18,2) DEFAULT 0,
    objectif_ca_mensuel DECIMAL(18,2) DEFAULT 0,
    -- Metadata
    date_sync DATETIME DEFAULT GETDATE(),
    actif BIT DEFAULT 1,
    CONSTRAINT UQ_Commercial UNIQUE (societe_code, code_commercial)
);
GO

-- =====================================================
-- SECTION 2: CONFIGURATION PERSONNALISEE DWH
-- =====================================================

-- ===================== APP_DataSources (Custom par DWH) =====================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_DataSources' AND xtype='U')
CREATE TABLE APP_DataSources (
    id INT IDENTITY(1,1) PRIMARY KEY,
    template_code VARCHAR(100) NULL,               -- Reference template si override
    nom NVARCHAR(200) NOT NULL,
    code VARCHAR(100) UNIQUE NOT NULL,
    type VARCHAR(50) NOT NULL DEFAULT 'query',
    category VARCHAR(50),
    description NVARCHAR(500),
    query_template NVARCHAR(MAX),
    parameters NVARCHAR(MAX),
    is_custom BIT DEFAULT 1,                       -- true = cree par client
    created_by INT NULL,
    actif BIT DEFAULT 1,
    date_creation DATETIME DEFAULT GETDATE(),
    date_modification DATETIME DEFAULT GETDATE()
);
GO

-- ===================== APP_Dashboards (Custom par DWH) =====================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Dashboards' AND xtype='U')
CREATE TABLE APP_Dashboards (
    id INT IDENTITY(1,1) PRIMARY KEY,
    template_code VARCHAR(100) NULL,
    nom NVARCHAR(200) NOT NULL,
    code VARCHAR(100) UNIQUE NOT NULL,
    description NVARCHAR(500),
    config NVARCHAR(MAX),
    widgets NVARCHAR(MAX),
    is_custom BIT DEFAULT 1,
    is_public BIT DEFAULT 0,
    created_by INT NULL,
    actif BIT DEFAULT 1,
    date_creation DATETIME DEFAULT GETDATE(),
    date_modification DATETIME DEFAULT GETDATE()
);
GO

-- ===================== APP_GridViews (Custom par DWH) =====================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_GridViews' AND xtype='U')
CREATE TABLE APP_GridViews (
    id INT IDENTITY(1,1) PRIMARY KEY,
    template_code VARCHAR(100) NULL,
    nom NVARCHAR(200) NOT NULL,
    code VARCHAR(100) UNIQUE NOT NULL,
    description NVARCHAR(500),
    datasource_code VARCHAR(100),
    columns_config NVARCHAR(MAX),
    features NVARCHAR(MAX),
    is_custom BIT DEFAULT 1,
    is_public BIT DEFAULT 0,
    created_by INT NULL,
    actif BIT DEFAULT 1,
    date_creation DATETIME DEFAULT GETDATE(),
    date_modification DATETIME DEFAULT GETDATE()
);
GO

-- ===================== APP_Pivots (Custom par DWH) =====================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Pivots' AND xtype='U')
CREATE TABLE APP_Pivots (
    id INT IDENTITY(1,1) PRIMARY KEY,
    template_code VARCHAR(100) NULL,
    nom NVARCHAR(200) NOT NULL,
    code VARCHAR(100) UNIQUE NOT NULL,
    description NVARCHAR(500),
    datasource_code VARCHAR(100),
    pivot_config NVARCHAR(MAX),
    is_custom BIT DEFAULT 1,
    is_public BIT DEFAULT 0,
    created_by INT NULL,
    actif BIT DEFAULT 1,
    date_creation DATETIME DEFAULT GETDATE(),
    date_modification DATETIME DEFAULT GETDATE()
);
GO

-- ===================== APP_Menus (Custom par DWH) =====================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Menus' AND xtype='U')
CREATE TABLE APP_Menus (
    id INT IDENTITY(1,1) PRIMARY KEY,
    template_code VARCHAR(100) NULL,
    nom NVARCHAR(100) NOT NULL,
    code VARCHAR(100) NOT NULL,
    icon VARCHAR(50),
    url VARCHAR(200),
    parent_id INT NULL,
    ordre INT DEFAULT 0,
    type VARCHAR(20) DEFAULT 'link',
    target_type VARCHAR(50) NULL,
    target_code VARCHAR(100) NULL,
    is_custom BIT DEFAULT 1,
    actif BIT DEFAULT 1,
    roles NVARCHAR(200),
    date_creation DATETIME DEFAULT GETDATE(),
    INDEX IX_Menus_parent (parent_id)
);
GO

-- ===================== APP_ReportSchedules (par DWH) =====================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ReportSchedules' AND xtype='U')
CREATE TABLE APP_ReportSchedules (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nom NVARCHAR(200) NOT NULL,
    description NVARCHAR(500),
    report_type VARCHAR(50) NOT NULL,              -- dashboard, gridview, pivot, custom
    report_code VARCHAR(100),
    report_config NVARCHAR(MAX),
    -- Planification
    schedule_type VARCHAR(20) NOT NULL,            -- daily, weekly, monthly
    schedule_config NVARCHAR(MAX),                 -- JSON cron config
    -- Email
    email_recipients NVARCHAR(MAX),
    email_subject NVARCHAR(200),
    email_body NVARCHAR(MAX),
    -- Status
    actif BIT DEFAULT 1,
    last_run DATETIME,
    last_status VARCHAR(20),
    next_run DATETIME,
    -- Metadata
    created_by INT,
    date_creation DATETIME DEFAULT GETDATE()
);
GO

-- ===================== APP_ReportHistory (par DWH) =====================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ReportHistory' AND xtype='U')
CREATE TABLE APP_ReportHistory (
    id INT IDENTITY(1,1) PRIMARY KEY,
    schedule_id INT NULL,
    report_name NVARCHAR(200) NOT NULL,
    report_type VARCHAR(50),
    parameters NVARCHAR(MAX),
    file_path NVARCHAR(500),
    file_size INT,
    status VARCHAR(20) DEFAULT 'pending',          -- pending, running, success, error
    error_message NVARCHAR(MAX),
    execution_time_ms INT,
    created_by INT,
    date_creation DATETIME DEFAULT GETDATE(),
    date_completion DATETIME
);
GO

-- =====================================================
-- SECTION 3: ETL TRACKING
-- =====================================================

-- ===================== ETL_SyncLog =====================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='ETL_SyncLog' AND xtype='U')
CREATE TABLE ETL_SyncLog (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    societe_code VARCHAR(50) NOT NULL,
    table_name VARCHAR(100) NOT NULL,
    sync_type VARCHAR(20),                         -- full, incremental
    status VARCHAR(20),                            -- started, success, error
    rows_extracted INT DEFAULT 0,
    rows_inserted INT DEFAULT 0,
    rows_updated INT DEFAULT 0,
    rows_deleted INT DEFAULT 0,
    error_message NVARCHAR(MAX),
    started_at DATETIME,
    completed_at DATETIME,
    duration_seconds AS DATEDIFF(SECOND, started_at, completed_at),
    INDEX IX_ETL_Log_societe (societe_code),
    INDEX IX_ETL_Log_date (started_at)
);
GO

-- ===================== ETL_Watermarks =====================
-- Pour tracking du sync incremental
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='ETL_Watermarks' AND xtype='U')
CREATE TABLE ETL_Watermarks (
    id INT IDENTITY(1,1) PRIMARY KEY,
    societe_code VARCHAR(50) NOT NULL,
    table_name VARCHAR(100) NOT NULL,
    watermark_column VARCHAR(100),
    watermark_value NVARCHAR(100),
    last_sync DATETIME,
    CONSTRAINT UQ_Watermark UNIQUE (societe_code, table_name)
);
GO

-- =====================================================
-- SECTION 4: VUES UTILES
-- =====================================================

-- Vue: Chiffre d'affaires par periode
IF EXISTS (SELECT * FROM sys.views WHERE name = 'V_CA_Periode')
    DROP VIEW V_CA_Periode;
GO

CREATE VIEW V_CA_Periode AS
SELECT
    societe_code,
    YEAR(date_piece) AS annee,
    MONTH(date_piece) AS mois,
    code_client,
    nom_client,
    commercial_code,
    commercial_nom,
    zone_geo,
    canal,
    famille,
    gamme,
    SUM(montant_ht) AS ca_ht,
    SUM(montant_ttc) AS ca_ttc,
    SUM(marge) AS marge_totale,
    SUM(quantite) AS quantite_totale,
    COUNT(DISTINCT numero_piece) AS nb_factures
FROM Lignes_Ventes
WHERE type_document IN ('FA', 'FC')  -- Factures uniquement
GROUP BY
    societe_code,
    YEAR(date_piece),
    MONTH(date_piece),
    code_client,
    nom_client,
    commercial_code,
    commercial_nom,
    zone_geo,
    canal,
    famille,
    gamme;
GO

-- Vue: Stock valorise
IF EXISTS (SELECT * FROM sys.views WHERE name = 'V_Stock_Valorise')
    DROP VIEW V_Stock_Valorise;
GO

CREATE VIEW V_Stock_Valorise AS
SELECT
    societe_code,
    code_article,
    designation,
    famille,
    gamme,
    SUM(quantite_stock) AS qte_totale,
    SUM(valeur_stock) AS valeur_totale,
    MIN(date_dernier_mouvement) AS dernier_mouvement_min,
    MAX(jours_sans_mouvement) AS jours_sans_mvt_max,
    CASE
        WHEN MAX(jours_sans_mouvement) > 180 THEN 'Dormant'
        WHEN MAX(jours_sans_mouvement) > 90 THEN 'Lent'
        ELSE 'Actif'
    END AS statut_rotation
FROM Stock
GROUP BY
    societe_code,
    code_article,
    designation,
    famille,
    gamme;
GO

-- Vue: DSO par client
IF EXISTS (SELECT * FROM sys.views WHERE name = 'V_DSO_Client')
    DROP VIEW V_DSO_Client;
GO

CREATE VIEW V_DSO_Client AS
SELECT
    b.societe_code,
    b.code_client,
    b.nom_client,
    b.commercial_code,
    b.commercial_nom,
    b.total_creance,
    b.total_echu,
    b.tranche_plus_120 AS creances_douteuses,
    -- Calcul DSO simplifie
    CASE
        WHEN ISNULL(ca.ca_90j, 0) = 0 THEN 0
        ELSE (b.total_creance / (ca.ca_90j / 90.0))
    END AS dso_jours
FROM BalanceAgee b
LEFT JOIN (
    SELECT
        societe_code,
        code_client,
        SUM(montant_ht) AS ca_90j
    FROM Lignes_Ventes
    WHERE date_piece >= DATEADD(DAY, -90, GETDATE())
    AND type_document IN ('FA', 'FC')
    GROUP BY societe_code, code_client
) ca ON b.societe_code = ca.societe_code AND b.code_client = ca.code_client;
GO

PRINT '=====================================================';
PRINT 'Base DWH Client initialisee avec succes!';
PRINT 'Tables BI: Clients, Articles, Lignes_Ventes, Stock...';
PRINT 'Tables Config: APP_DataSources, APP_Dashboards...';
PRINT 'Tables ETL: ETL_SyncLog, ETL_Watermarks';
PRINT '=====================================================';
