-- Migration 012 : Tables Comptabilité Analytique
-- À exécuter sur chaque base DWH client (OptiBoard_<CODE>)
-- Prérequis : tables Sage F_ECRITUREA et F_CENTREAN synchronisées (ETL config)

-- ──────────────────────────────────────────────────────────────
-- Axes analytiques (niveaux de ventilation)
-- ──────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name='Axes_Analytiques')
CREATE TABLE [dbo].[Axes_Analytiques] (
    [cbIndice]    TINYINT PRIMARY KEY,
    [cbIntitule]  NVARCHAR(200)  NOT NULL,
    [cbActif]     BIT            NOT NULL DEFAULT 1
);

-- ──────────────────────────────────────────────────────────────
-- Centres analytiques
-- ──────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name='Centres_Analytiques')
CREATE TABLE [dbo].[Centres_Analytiques] (
    [CA_Num]      NVARCHAR(20)   NOT NULL PRIMARY KEY,
    [CA_Intitule] NVARCHAR(200)  NOT NULL,
    [cbIndice]    TINYINT        NULL,
    [CA_Niv]      TINYINT        NULL DEFAULT 1
);

-- ──────────────────────────────────────────────────────────────
-- Écritures analytiques
-- ──────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name='Ecritures_Analytiques')
CREATE TABLE [dbo].[Ecritures_Analytiques] (
    [EA_Num]      INT            IDENTITY(1,1) PRIMARY KEY,
    [EA_DateEcr]  DATE           NOT NULL,
    [CA_Num]      NVARCHAR(20)   NOT NULL,
    [CG_Num]      NVARCHAR(20)   NOT NULL,
    [EA_Montant]  DECIMAL(18,2)  NOT NULL DEFAULT 0,
    [EA_Sens]     TINYINT        NOT NULL,   -- 1=Débit, 2=Crédit
    [JO_Num]      NVARCHAR(10)   NULL,
    [EC_Num]      INT            NULL,
    [EA_Libelle]  NVARCHAR(200)  NULL
);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_EA_DateCA' AND object_id=OBJECT_ID('dbo.Ecritures_Analytiques'))
    CREATE INDEX IX_EA_DateCA
      ON [dbo].[Ecritures_Analytiques] ([EA_DateEcr], [CA_Num])
      INCLUDE ([EA_Montant], [EA_Sens], [CG_Num]);

-- ──────────────────────────────────────────────────────────────
-- Budgets analytiques (saisie manuelle depuis l'UI)
-- ──────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name='Budgets_Analytiques')
CREATE TABLE [dbo].[Budgets_Analytiques] (
    [id]          INT            IDENTITY(1,1) PRIMARY KEY,
    [exercice]    INT            NOT NULL,
    [mois]        TINYINT        NOT NULL,       -- 1 à 12
    [CA_Num]      NVARCHAR(20)   NOT NULL,
    [CG_Num]      NVARCHAR(20)   NULL,
    [montant]     DECIMAL(18,2)  NOT NULL DEFAULT 0,
    CONSTRAINT UQ_Budget_Analytique UNIQUE (exercice, mois, CA_Num, CG_Num)
);

-- ──────────────────────────────────────────────────────────────
-- Table budget global (Phase 5 — Budget vs Réalisé)
-- ──────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name='APP_Budgets')
CREATE TABLE [dbo].[APP_Budgets] (
    [id]             INT           IDENTITY(1,1) PRIMARY KEY,
    [exercice]       INT           NOT NULL,
    [mois]           TINYINT       NOT NULL,       -- 1 à 12
    [axe]            NVARCHAR(50)  NOT NULL,        -- 'CA', 'CHARGES', 'MARGE', 'PAIE'
    [code_poste]     NVARCHAR(50)  NULL,
    [libelle_poste]  NVARCHAR(200) NULL,
    [montant_budget] DECIMAL(18,2) NOT NULL DEFAULT 0,
    [created_at]     DATETIME      NOT NULL DEFAULT GETDATE(),
    CONSTRAINT UQ_Budget UNIQUE (exercice, mois, axe, code_poste)
);

PRINT 'Migration 012 : Tables Analytique + Budget créées avec succès';
