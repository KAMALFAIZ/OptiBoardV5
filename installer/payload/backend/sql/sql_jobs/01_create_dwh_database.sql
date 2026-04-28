-- =====================================================================
-- 01_create_dwh_database.sql
-- Creation de la base DWH dediee + tables cibles (35 tables)
-- Architecture 3 bases : OptiBoard_xxxx + DWH_yyyy + Sage 1..N
-- =====================================================================
-- USAGE : Remplacer {DWH_NAME} par le nom souhaite (ex: DWH_Alboughaze)
--         Executer sur le serveur DWH
-- =====================================================================
-- IMPORTANT : sp_Sync_Generic utilise INFORMATION_SCHEMA.COLUMNS pour
--   decouvrir dynamiquement les colonnes de chaque table cible.
--   TOUTES les colonnes metier doivent etre definies a l'avance.
--   Les tables avec schema minimal (SyncDate uniquement) ne pourront
--   PAS etre synchronisees correctement tant que leurs colonnes
--   ne sont pas ajoutees. Completez-les depuis sync_tables.yaml.
-- =====================================================================

-- === Décommenter pour créer la base ===
-- CREATE DATABASE [{DWH_NAME}];
-- GO

SET NOCOUNT ON;
GO

-- Chaque batch cible la base DWH
USE [{DWH_NAME}];

PRINT '══════════════════════════════════════════════════════════════';
PRINT ' CRÉATION DES 35 TABLES CIBLES DWH';
PRINT '══════════════════════════════════════════════════════════════';

-- =====================================================================
-- 1. Collaborateurs (sort_order: 1, FULL, priority: high)
-- =====================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Collaborateurs')
CREATE TABLE Collaborateurs (
    [id]                     INT IDENTITY(1,1) PRIMARY KEY,
    [DB_Id]                  INT NOT NULL,
    [DB]                     VARCHAR(100) NOT NULL,
    [DB_Caption]             NVARCHAR(200) NOT NULL,
    [Code collaborateur]     NVARCHAR(50),
    [Nom collaborateur]      NVARCHAR(200),
    [Prénom collaborateur]   NVARCHAR(200),
    [Fonction collaborateur] NVARCHAR(200),
    [Adresse collaborateur]  NVARCHAR(500),
    [CP collaborateur]       NVARCHAR(20),
    [Ville collaborateur]    NVARCHAR(100),
    [Région collaborateur]   NVARCHAR(100),
    [Pays collaborateur]     NVARCHAR(100),
    [Service collaborateur]  NVARCHAR(100),
    [Vendeur]                NVARCHAR(10),
    [Caissier]               NVARCHAR(10),
    [Acheteur]               NVARCHAR(10),
    [Tél collaborateur]      NVARCHAR(50),
    [Fax collaborateur]      NVARCHAR(50),
    [Email collaborateur]    NVARCHAR(200),
    [GSM collaborateur]      NVARCHAR(50),
    [Charge Recouvr]         NVARCHAR(10),
    [Financier]              NVARCHAR(10),
    [FaceBook collaborateur] NVARCHAR(200),
    [LinkdIn collaborateur]  NVARCHAR(200),
    [Skyp collaborateur]     NVARCHAR(200),
    [SyncDate]               DATETIME DEFAULT GETDATE()
);
GO

-- =====================================================================
-- 2. Info_Libres (sort_order: 2, FULL, priority: high)
-- =====================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Info_Libres')
CREATE TABLE Info_Libres (
    [id]         INT IDENTITY(1,1) PRIMARY KEY,
    [DB_Id]      INT NOT NULL,
    [DB]         VARCHAR(100) NOT NULL,
    [DB_Caption] NVARCHAR(200) NOT NULL,
    [CB_File]    NVARCHAR(200),
    [CB_Name]    NVARCHAR(200),
    [SyncDate]   DATETIME DEFAULT GETDATE()
);
GO

-- =====================================================================
-- 3. Articles (sort_order: 3, INCREMENTAL, priority: high)
-- =====================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Articles')
CREATE TABLE Articles (
    [id]                        INT IDENTITY(1,1) PRIMARY KEY,
    [DB_Id]                     INT NOT NULL,
    [DB]                        VARCHAR(100) NOT NULL,
    [DB_Caption]                NVARCHAR(200) NOT NULL,
    [Code interne]              INT,
    [Type Article]              NVARCHAR(50),
    [Code Article]              NVARCHAR(100),
    [Désignation Article]       NVARCHAR(500),
    [Code Famille]              NVARCHAR(50),
    [Intitulé famille]          NVARCHAR(200),
    [Intitulé Famille Centralisatrice] NVARCHAR(200),
    [Libellé Gamme 1]           NVARCHAR(200),
    [Libellé Gamme 2]           NVARCHAR(200),
    [Catalogue 1]               NVARCHAR(200),
    [Catalogue 2]               NVARCHAR(200),
    [Catalogue 3]               NVARCHAR(200),
    [Catalogue 4]               NVARCHAR(200),
    [Conditionnement]           NVARCHAR(100),
    [Unité Vente]               NVARCHAR(50),
    [Prix d'achat]              DECIMAL(18,4),
    [Dernier prix d'achat]      DECIMAL(18,4),
    [Coefficient]               DECIMAL(18,4),
    [Prix de vente]             DECIMAL(18,4),
    [Suivi Stock]               NVARCHAR(50),
    [Poids Net]                 DECIMAL(18,4),
    [Poids Brut]                DECIMAL(18,4),
    [Actif / Sommeil]           NVARCHAR(20),
    [Code Barres]               NVARCHAR(100),
    [Date création]             DATETIME,
    [Date modification]         DATETIME,
    [cbCreation]                DATETIME,
    [cbModification]            DATETIME,
    [SyncDate]                  DATETIME DEFAULT GETDATE()
);
GO

-- =====================================================================
-- 4. Clients (sort_order: 5, INCREMENTAL, priority: high)
-- =====================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Clients')
CREATE TABLE Clients (
    [id]                   INT IDENTITY(1,1) PRIMARY KEY,
    [DB_Id]                INT NOT NULL,
    [DB]                   VARCHAR(100) NOT NULL,
    [DB_Caption]           NVARCHAR(200) NOT NULL,
    [Qualité]              NVARCHAR(50),
    [Code client]          NVARCHAR(50),
    [Intitulé]             NVARCHAR(300),
    [Classement]           NVARCHAR(100),
    [Code représentant]    INT,
    [Représentant]         NVARCHAR(200),
    [Code payeur]          NVARCHAR(50),
    [Tiers payeur]         NVARCHAR(300),
    [Devise]               NVARCHAR(50),
    [Catégorie tarifaire]  NVARCHAR(100),
    [Dépôt de rattachement] NVARCHAR(200),
    [En sommeil]           NVARCHAR(20),
    [Compte comptable]     NVARCHAR(50),
    [Contact]              NVARCHAR(200),
    [Adresse]              NVARCHAR(500),
    [Complément]           NVARCHAR(200),
    [Code postal]          NVARCHAR(20),
    [Ville]                NVARCHAR(100),
    [Région]               NVARCHAR(100),
    [Pays]                 NVARCHAR(100),
    [Téléphone]            NVARCHAR(50),
    [Email]                NVARCHAR(200),
    [Date de création]     DATETIME,
    [Date de modification] DATETIME,
    [cbCreation]           DATETIME,
    [cbModification]       DATETIME,
    [SyncDate]             DATETIME DEFAULT GETDATE()
);
GO

-- =====================================================================
-- 5. Lieu_Livraison_Client (sort_order: 6, FULL, priority: normal)
-- =====================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Lieu_Livraison_Client')
CREATE TABLE Lieu_Livraison_Client (
    [id]                      INT IDENTITY(1,1) PRIMARY KEY,
    [DB_Id]                   INT NOT NULL,
    [DB]                      VARCHAR(100) NOT NULL,
    [DB_Caption]              NVARCHAR(200) NOT NULL,
    [N° interne]              INT,
    [Code client]             NVARCHAR(50),
    [Intitule livraison]      NVARCHAR(200),
    [Adresse]                 NVARCHAR(500),
    [Code postal]             NVARCHAR(20),
    [Ville]                   NVARCHAR(100),
    [Région]                  NVARCHAR(100),
    [Pays]                    NVARCHAR(100),
    [Contact]                 NVARCHAR(200),
    [Dépôt principal]         NVARCHAR(10),
    [Téléphone]               NVARCHAR(50),
    [Fax]                     NVARCHAR(50),
    [Email]                   NVARCHAR(200),
    [Expédition]              NVARCHAR(100),
    [Condition de livraison]  NVARCHAR(100),
    [SyncDate]                DATETIME DEFAULT GETDATE()
);
GO

-- =====================================================================
-- 6. Entête_des_ventes (sort_order: 7, INCREMENTAL, priority: high)
-- =====================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = N'Entête_des_ventes')
CREATE TABLE [Entête_des_ventes] (
    [id]                       INT IDENTITY(1,1) PRIMARY KEY,
    [DB_Id]                    INT NOT NULL,
    [DB]                       VARCHAR(100) NOT NULL,
    [DB_Caption]               NVARCHAR(200) NOT NULL,
    [N° interne]               INT,
    [Encours]                  NVARCHAR(10),
    [Type Document]            NVARCHAR(200),
    [Souche]                   NVARCHAR(100),
    [Statut]                   NVARCHAR(100),
    [Code client]              NVARCHAR(50),
    [Intitulé client]          NVARCHAR(300),
    [Code représentant]        INT,
    [Nom représentant]         NVARCHAR(200),
    [Date]                     DATETIME,
    [N° Pièce]                 NVARCHAR(50),
    [Document ventilé]         NVARCHAR(10),
    [Etat]                     NVARCHAR(50),
    [Entête 1]                 NVARCHAR(200),
    [Entête 2]                 NVARCHAR(200),
    [Entête 3]                 NVARCHAR(200),
    [Entête 4]                 NVARCHAR(200),
    [N° Compte Payeur]         NVARCHAR(50),
    [Intitulé tiers payeur]    NVARCHAR(300),
    [Dépôt]                    NVARCHAR(200),
    [Devise]                   NVARCHAR(50),
    [Expédition]               NVARCHAR(100),
    [Langue]                   NVARCHAR(20),
    [Fact/BL]                  NVARCHAR(10),
    [Nb Facture]               INT,
    [Compte Général]           NVARCHAR(50),
    [Code d'affaire]           NVARCHAR(50),
    [Intitulé affaire]         NVARCHAR(200),
    [Catégorie Comptable]      NVARCHAR(200),
    [Code dépôt]               INT,
    [Référence]                NVARCHAR(200),
    [Cours]                    DECIMAL(18,4),
    [Taux escompte]            DECIMAL(18,4),
    [Document de reliquat]     NVARCHAR(10),
    [Document imprimé ]        NVARCHAR(10),
    [Date livraison souhite]   DATETIME,
    [Date début de l'abonnement lié] DATETIME,
    [Date fin de l'abonnement lié]   DATETIME,
    [Date début de la périodicité liée] DATETIME,
    [Date Fin de la périodicité liée]   DATETIME,
    [Document clôturé]         NVARCHAR(10),
    [Type frais]               NVARCHAR(50),
    [Valeur frais]             DECIMAL(18,4),
    [Type HT/TTC frais]       NVARCHAR(10),
    [Statut validé]            NVARCHAR(10),
    [Intitulé Devise]          NVARCHAR(50),
    [Catégorie tarifaire ]     NVARCHAR(100),
    [Condition de livraison]   NVARCHAR(100),
    [Colisage]                 NVARCHAR(100),
    [Montant HT]               DECIMAL(18,4),
    [Montant TTC]              DECIMAL(18,4),
    [Montant net à payer]      DECIMAL(18,4),
    [Montant réglé]            DECIMAL(18,4),
    [Code lieu de livraison]   INT,
    [Lieu de livraison]        NVARCHAR(200),
    [Date création]            DATETIME,
    [Date modification]        DATETIME,
    [Valorise CA]              NVARCHAR(10),
    [cbCreation]               DATETIME,
    [cbModification]           DATETIME,
    [SyncDate]                 DATETIME DEFAULT GETDATE()
);
GO

-- =====================================================================
-- 7. Règlements_Clients (sort_order: 8, INCREMENTAL, priority: normal)
-- =====================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = N'Règlements_Clients')
CREATE TABLE [Règlements_Clients] (
    [id]                   INT IDENTITY(1,1) PRIMARY KEY,
    [DB_Id]                INT NOT NULL,
    [DB]                   VARCHAR(100) NOT NULL,
    [DB_Caption]           NVARCHAR(200) NOT NULL,
    [Code client]          NVARCHAR(50),
    [Intitulé]             NVARCHAR(300),
    [Code client original] NVARCHAR(50),
    [Intitulé original]    NVARCHAR(300),
    [Date]                 DATETIME,
    [Date d'échéance]      DATETIME,
    [Référence]            NVARCHAR(200),
    [Libellé]              NVARCHAR(500),
    [Impute]               NVARCHAR(10),
    [Comptabilisé]         NVARCHAR(10),
    [Code journal]         NVARCHAR(50),
    [Journal]              NVARCHAR(200),
    [Compte générale]      NVARCHAR(50),
    [N° piéce]             NVARCHAR(50),
    [Valide]               NVARCHAR(10),
    [Mode de règlement]    NVARCHAR(100),
    [Devise]               NVARCHAR(50),
    [Montant en devise]    DECIMAL(18,4),
    [Cours]                DECIMAL(18,4),
    [Montant]              DECIMAL(18,4),
    [N° interne]           NVARCHAR(250),
    [solde]                DECIMAL(18,4),
    [Code règlement]       NVARCHAR(50),
    [Date création]        DATETIME,
    [Date modification]    DATETIME,
    [cbCreation]           DATETIME,
    [cbModification]       DATETIME,
    [SyncDate]             DATETIME DEFAULT GETDATE()
);
GO

-- =====================================================================
-- 8. Imputation_Factures_Ventes (sort_order: 9, INCREMENTAL, priority: normal)
-- =====================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Imputation_Factures_Ventes')
CREATE TABLE Imputation_Factures_Ventes (
    [id]                     INT IDENTITY(1,1) PRIMARY KEY,
    [DB_Id]                  INT NOT NULL,
    [DB]                     VARCHAR(100) NOT NULL,
    [DB_Caption]             NVARCHAR(200) NOT NULL,
    [Référence]              NVARCHAR(200),
    [Libellé]                NVARCHAR(500),
    [id Règlement]           INT,
    [Date règlement]         DATETIME,
    [Date d'échéance]        DATETIME,
    [Id échéance]            INT,
    [Type Document]          NVARCHAR(500),
    [N° pièce]               NVARCHAR(50),
    [Montant facture TTC]    DECIMAL(18,4),
    [Montant régler]         DECIMAL(18,4),
    [Date document]          DATETIME,
    [Mode de réglement]      NVARCHAR(200),
    [Code client]            NVARCHAR(50),
    [Intitulé client]        NVARCHAR(300),
    [Code tier payeur]       NVARCHAR(50),
    [Intitulé tier payeur]   NVARCHAR(300),
    [Montant réglement]      DECIMAL(18,4),
    [Date création]          DATETIME,
    [Date modification]      DATETIME,
    [SyncDate]               DATETIME DEFAULT GETDATE()
);
GO

-- =====================================================================
-- 9. Lignes_des_ventes (sort_order: 10, INCREMENTAL, priority: high)
-- =====================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Lignes_des_ventes')
CREATE TABLE Lignes_des_ventes (
    [id]                          INT IDENTITY(1,1) PRIMARY KEY,
    [DB_Id]                       INT NOT NULL,
    [DB]                          VARCHAR(100) NOT NULL,
    [DB_Caption]                  NVARCHAR(200) NOT NULL,
    [N° interne]                  INT,
    [Type Document]               NVARCHAR(500),
    [Valorise CA]                 NVARCHAR(10),
    [Code client]                 NVARCHAR(50),
    [Intitulé client]             NVARCHAR(300),
    [N° Pièce]                    NVARCHAR(50),
    [Référence]                   NVARCHAR(200),
    [Intitulé affaire]            NVARCHAR(200),
    [Code d'affaire]              NVARCHAR(50),
    [Date]                        DATETIME,
    [Date document]               DATETIME,
    [N° Pièce BL]                 NVARCHAR(50),
    [Date BL]                     DATETIME,
    [N° Pièce BC]                 NVARCHAR(50),
    [Date BC]                     DATETIME,
    [N° pièce PL]                 NVARCHAR(50),
    [Date PL]                     DATETIME,
    [Date Livraison]              DATETIME,
    [Code article]                NVARCHAR(100),
    [Désignation ligne]           NVARCHAR(500),
    [Catalogue 1]                 NVARCHAR(200),
    [Catalogue 2]                 NVARCHAR(200),
    [Catalogue 3]                 NVARCHAR(200),
    [Catalogue 4]                 NVARCHAR(200),
    [Gamme 1]                     NVARCHAR(200),
    [Gamme 2]                     NVARCHAR(200),
    [Colisage]                    NVARCHAR(200),
    [Poids brut]                  FLOAT,
    [Poids net]                   FLOAT,
    [N° Série/Lot]                NVARCHAR(200),
    [Taxe1]                       NVARCHAR(50),
    [Taxe2]                       NVARCHAR(50),
    [Taxe3]                       NVARCHAR(50),
    [Type taux taxe 1]            NVARCHAR(50),
    [Type taux taxe 2]            NVARCHAR(50),
    [Type taux taxe 3]            NVARCHAR(50),
    [Type taxe 1]                 NVARCHAR(50),
    [Type taxe 2]                 NVARCHAR(50),
    [Type taxe 3]                 NVARCHAR(50),
    [Remise 1]                    NVARCHAR(50),
    [Remise 2]                    NVARCHAR(50),
    [Frais d'approche]            FLOAT,
    [PU Devise]                   DECIMAL(18,4),
    [Type de la remise 1]         NVARCHAR(50),
    [Type de la remise 2]         NVARCHAR(50),
    [Référence article client]    NVARCHAR(200),
    [Article facturé au poids]    INT,
    [Nomenclature]                NVARCHAR(10),
    [Type remise de pied]         NVARCHAR(10),
    [Type remise exceptionnelle]  NVARCHAR(10),
    [CMUP]                        DECIMAL(18,4),
    [Prix unitaire]               DECIMAL(18,4),
    [Prix unitaire TTC]           DECIMAL(18,4),
    [Prix unitaire BC]            DECIMAL(18,4),
    [Conditionnement]             NVARCHAR(100),
    [Quantité]                    DECIMAL(18,4),
    [Quantité PL]                 DECIMAL(18,4),
    [Quantité BC]                 DECIMAL(18,4),
    [Quantité BL]                 DECIMAL(18,4),
    [Quantité devis]              DECIMAL(18,4),
    [Montant HT Net]              DECIMAL(18,4),
    [Montant TTC Net]             DECIMAL(18,4),
    [Prix de revient]             DECIMAL(18,4),
    [Code dépôt]                  INT,
    [Intitulé dépôt]              NVARCHAR(200),
    [Date création]               DATETIME,
    [Date modification]           DATETIME,
    [DPA-Période]                 FLOAT,
    [DPA-Vente]                   FLOAT,
    [Coût standard]               FLOAT,
    [SyncDate]                    DATETIME DEFAULT GETDATE()
);
GO

-- =====================================================================
-- 10. Imputation_BL (sort_order: 11, FULL, priority: normal)
-- =====================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Imputation_BL')
CREATE TABLE Imputation_BL (
    [id]                INT IDENTITY(1,1) PRIMARY KEY,
    [DB_Id]             INT NOT NULL,
    [DB]                VARCHAR(100) NOT NULL,
    [DB_Caption]        NVARCHAR(200) NOT NULL,
    [SyncDate]          DATETIME DEFAULT GETDATE()
);
GO

-- =====================================================================
-- 11. Échéances_Ventes (sort_order: 12, FULL, priority: normal)
-- =====================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = N'Échéances_Ventes')
CREATE TABLE [Échéances_Ventes] (
    [id]                        INT IDENTITY(1,1) PRIMARY KEY,
    [DB_Id]                     INT NOT NULL,
    [DB]                        VARCHAR(100) NOT NULL,
    [DB_Caption]                NVARCHAR(200) NOT NULL,
    [N° interne]                INT,
    [Code tiers payeur]         NVARCHAR(50),
    [Intitulé Tiers payeur]     NVARCHAR(300),
    [Code client]               NVARCHAR(50),
    [Intitulé client]           NVARCHAR(300),
    [Type Document]             NVARCHAR(500),
    [N° Pièce]                  NVARCHAR(50),
    [Date document]             DATETIME,
    [Date d'échéance]           DATETIME,
    [Montant TTC Net]           DECIMAL(18,4),
    [Montant en devise]         DECIMAL(18,4),
    [Cours]                     DECIMAL(18,4),
    [Libellé du règlement]      NVARCHAR(500),
    [Montant échéance]          DECIMAL(18,4),
    [Montant HT brut]           DECIMAL(18,4),
    [Montant TTC brut]          DECIMAL(18,4),
    [Type de règlement]         NVARCHAR(50),
    [Pourcentage du règlement]  DECIMAL(18,4),
    [Montant du règlement]      DECIMAL(18,4),
    [Ligne d'équilibrage]       NVARCHAR(10),
    [Code mode règlement]       INT,
    [Mode de règlement]         NVARCHAR(200),
    [cbModification]            DATETIME,
    [SyncDate]                  DATETIME DEFAULT GETDATE()
);
GO

-- =====================================================================
-- 12. Fournisseurs (sort_order: 14, INCREMENTAL, priority: normal)
-- =====================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Fournisseurs')
CREATE TABLE Fournisseurs (
    [id]                   INT IDENTITY(1,1) PRIMARY KEY,
    [DB_Id]                INT NOT NULL,
    [DB]                   VARCHAR(100) NOT NULL,
    [DB_Caption]           NVARCHAR(200) NOT NULL,
    [Qualité]              NVARCHAR(50),
    [Code fournisseur]     NVARCHAR(50),
    [Intitulé]             NVARCHAR(300),
    [Classement]           NVARCHAR(100),
    [Code acheteur]        INT,
    [Acheteur]             NVARCHAR(200),
    [Code encaisseur]      NVARCHAR(50),
    [Tiers encaisseur]     NVARCHAR(300),
    [Devise]               NVARCHAR(50),
    [Catégorie tarifaire]  NVARCHAR(100),
    [Dépôt]                NVARCHAR(200),
    [En sommeil]           NVARCHAR(20),
    [Compte comptable]     NVARCHAR(50),
    [Contact]              NVARCHAR(200),
    [Adresse]              NVARCHAR(500),
    [Code postal]          NVARCHAR(20),
    [Ville]                NVARCHAR(100),
    [Téléphone]            NVARCHAR(50),
    [Email]                NVARCHAR(200),
    [Date de création]     DATETIME,
    [Date modification]    DATETIME,
    [cbCreation]           DATETIME,
    [cbModification]       DATETIME,
    [SyncDate]             DATETIME DEFAULT GETDATE()
);
GO

-- =====================================================================
-- 13. Entête_des_achats (sort_order: 15, INCREMENTAL, priority: normal)
-- =====================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = N'Entête_des_achats')
CREATE TABLE [Entête_des_achats] (
    [id]                                   INT IDENTITY(1,1) PRIMARY KEY,
    [DB_Id]                                INT NOT NULL,
    [DB]                                   VARCHAR(100) NOT NULL,
    [DB_Caption]                           NVARCHAR(200) NOT NULL,
    [Type Document]                        NVARCHAR(500),
    [Encours]                              NVARCHAR(10),
    [Statut]                               NVARCHAR(200),
    [Statut validé]                        NVARCHAR(10),
    [Document reliquat]                    NVARCHAR(10),
    [Document clôturé]                     NVARCHAR(10),
    [Date]                                 DATETIME,
    [N° Pièce]                             NVARCHAR(50),
    [Souche]                               NVARCHAR(100),
    [Référence]                            NVARCHAR(200),
    [Code Fournisseur]                     NVARCHAR(50),
    [Intitulé Fournisseur]                 NVARCHAR(300),
    [N° Compte tiers encaisseur]           NVARCHAR(50),
    [Intitulé tiers encaisseur]            NVARCHAR(300),
    [Code acheteur]                        INT,
    [Nom acheteur]                         NVARCHAR(200),
    [Document ventilé]                     NVARCHAR(10),
    [Etat]                                 NVARCHAR(50),
    [Entête 1]                             NVARCHAR(200),
    [Entête 2]                             NVARCHAR(200),
    [Entête 3]                             NVARCHAR(200),
    [Entête 4]                             NVARCHAR(200),
    [Code dépôt]                           INT,
    [Intitulé dépôt]                       NVARCHAR(200),
    [Devise]                               NVARCHAR(50),
    [Cours]                                DECIMAL(18,4),
    [Expédition]                           NVARCHAR(100),
    [Langue]                               NVARCHAR(20),
    [Fact/BL]                              NVARCHAR(10),
    [Nb Facture]                           INT,
    [Code d'affaire]                       NVARCHAR(50),
    [Intitulé affaire]                     NVARCHAR(200),
    [Compte Général]                       NVARCHAR(50),
    [Catégorie Comptable]                  NVARCHAR(200),
    [Colisage]                             NVARCHAR(200),
    [Taux escompte]                        DECIMAL(18,4),
    [Ecart]                                DECIMAL(18,4),
    [Document imprimé ]                    NVARCHAR(10),
    [Date livraison souhaite]              DATETIME,
    [Date début de l'abonnement lié]       DATETIME,
    [Date fin de l'abonnement lié]         DATETIME,
    [Date début de la périodicité liée]    DATETIME,
    [Date Fin de la périodicité liée]      DATETIME,
    [N° facture Fournisseur]               NVARCHAR(50),
    [Type frais]                           NVARCHAR(50),
    [Valeur frais]                         DECIMAL(18,4),
    [Type HT/TTC frais]                   NVARCHAR(10),
    [Catégorie tarifaire ]                 NVARCHAR(100),
    [Condition de livraison]               NVARCHAR(100),
    [Code lieu de livraison]               INT,
    [Lieu de livraison]                    NVARCHAR(200),
    [Montant HT]                           DECIMAL(18,4),
    [Montant TTC]                          DECIMAL(18,4),
    [Montant net à payer]                  DECIMAL(18,4),
    [Montant réglé]                        DECIMAL(18,4),
    [Souche Ach. Imoprt]                   NVARCHAR(50),
    [Date création]                        DATETIME,
    [Date modification]                    DATETIME,
    [SyncDate]                             DATETIME DEFAULT GETDATE()
);
GO

-- =====================================================================
-- 14. Paiements_Fournisseurs (sort_order: 16, INCREMENTAL, priority: normal)
-- =====================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Paiements_Fournisseurs')
CREATE TABLE Paiements_Fournisseurs (
    [id]                   INT IDENTITY(1,1) PRIMARY KEY,
    [DB_Id]                INT NOT NULL,
    [DB]                   VARCHAR(100) NOT NULL,
    [DB_Caption]           NVARCHAR(200) NOT NULL,
    [Code fournisseur]     NVARCHAR(50),
    [Intitulé]             NVARCHAR(300),
    [Date]                 DATETIME,
    [Date d'échéance]      DATETIME,
    [Référence]            NVARCHAR(200),
    [Libellé]              NVARCHAR(500),
    [Impute]               NVARCHAR(10),
    [Comptabilisé]         NVARCHAR(10),
    [Code journal]         NVARCHAR(50),
    [Journal]              NVARCHAR(200),
    [Compte générale]      NVARCHAR(50),
    [N° piéce]             NVARCHAR(50),
    [Mode réglement]       NVARCHAR(100),
    [Devise]               NVARCHAR(50),
    [Montant en devise]    DECIMAL(18,4),
    [Cours]                DECIMAL(18,4),
    [Montant]              DECIMAL(18,4),
    [N° interne]           NVARCHAR(250),
    [solde]                DECIMAL(18,4),
    [Code réglement]       NVARCHAR(50),
    [Date création]        DATETIME,
    [Date modification]    DATETIME,
    [cbCreation]           DATETIME,
    [cbModification]       DATETIME,
    [SyncDate]             DATETIME DEFAULT GETDATE()
);
GO

-- =====================================================================
-- 15. Imputation_Factures_Achats (sort_order: 17, INCREMENTAL, priority: normal)
-- =====================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Imputation_Factures_Achats')
CREATE TABLE Imputation_Factures_Achats (
    [id]                     INT IDENTITY(1,1) PRIMARY KEY,
    [DB_Id]                  INT NOT NULL,
    [DB]                     VARCHAR(100) NOT NULL,
    [DB_Caption]             NVARCHAR(200) NOT NULL,
    [Référence]              NVARCHAR(200),
    [Libellé]                NVARCHAR(500),
    [id Réglement]           INT,
    [Date réglement]         DATETIME,
    [Date d'échance]         DATETIME,
    [Id écheance]            INT,
    [Type Document]          NVARCHAR(500),
    [N° pièce]               NVARCHAR(50),
    [Montant facture TTC]    DECIMAL(18,4),
    [Montant régler]         DECIMAL(18,4),
    [Date document]          DATETIME,
    [Mode de réglement]      NVARCHAR(200),
    [Code fournisseur]       NVARCHAR(50),
    [Intitulé fournisseur]   NVARCHAR(300),
    [Code tier payeur]       NVARCHAR(50),
    [Intitulé tier payeur]   NVARCHAR(300),
    [Montant réglement]      DECIMAL(18,4),
    [Date création]          DATETIME,
    [Date modification]      DATETIME,
    [SyncDate]               DATETIME DEFAULT GETDATE()
);
GO

-- =====================================================================
-- 16. Lignes_des_achats (sort_order: 18, INCREMENTAL, priority: normal)
-- =====================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Lignes_des_achats')
CREATE TABLE Lignes_des_achats (
    [id]                              INT IDENTITY(1,1) PRIMARY KEY,
    [DB_Id]                           INT NOT NULL,
    [DB]                              VARCHAR(100) NOT NULL,
    [DB_Caption]                      NVARCHAR(200) NOT NULL,
    [N° interne]                      INT,
    [Type Document]                   NVARCHAR(500),
    [Valorise CA]                     NVARCHAR(10),
    [Code fournisseur]                NVARCHAR(50),
    [Intitulé fournisseur]            NVARCHAR(300),
    [N° Pièce]                        NVARCHAR(50),
    [Référence]                       NVARCHAR(200),
    [Intitulé affaire]                NVARCHAR(200),
    [Code d'affaire]                  NVARCHAR(50),
    [Date]                            DATETIME,
    [N° Pièce BL]                     NVARCHAR(50),
    [Date BL]                         DATETIME,
    [N° Pièce BC]                     NVARCHAR(50),
    [Date BC]                         DATETIME,
    [N° pièce PL]                     NVARCHAR(50),
    [Date PL]                         DATETIME,
    [Date Livraison]                  DATETIME,
    [Code article]                    NVARCHAR(100),
    [Désignation]                     NVARCHAR(500),
    [Catalogue 1]                     NVARCHAR(200),
    [Catalogue 2]                     NVARCHAR(200),
    [Catalogue 3]                     NVARCHAR(200),
    [Catalogue 4]                     NVARCHAR(200),
    [Gamme 1]                         NVARCHAR(200),
    [Gamme 2]                         NVARCHAR(200),
    [Colisage]                        NVARCHAR(200),
    [Poids brut]                      FLOAT,
    [Poids net]                       FLOAT,
    [N° Série/Lot]                    NVARCHAR(200),
    [Taxe1]                           NVARCHAR(50),
    [Taxe2]                           NVARCHAR(50),
    [Taxe3]                           NVARCHAR(50),
    [Type taux taxe 1]                NVARCHAR(50),
    [Type taux taxe 2]                NVARCHAR(50),
    [Type taux taxe 3]                NVARCHAR(50),
    [Type taxe 1]                     NVARCHAR(50),
    [Type taxe 2]                     NVARCHAR(50),
    [Type taxe 3]                     NVARCHAR(50),
    [Remise 1]                        NVARCHAR(50),
    [Remise 2]                        NVARCHAR(50),
    [Frais d'approche]                FLOAT,
    [PU Devise]                       DECIMAL(18,4),
    [Nomenclature]                    NVARCHAR(10),
    [Type remise de pied]             NVARCHAR(10),
    [Type remise exceptionnelle]      NVARCHAR(10),
    [CMUP]                            DECIMAL(18,4),
    [Prix unitaire]                   DECIMAL(18,4),
    [Prix unitaire TTC]               DECIMAL(18,4),
    [Quantité]                        DECIMAL(18,4),
    [Quantité PL]                     DECIMAL(18,4),
    [Qté Ressource]                   DECIMAL(18,4),
    [Montant HT Net]                  DECIMAL(18,4),
    [Montant TTC Net]                 DECIMAL(18,4),
    [Prix de revient]                 DECIMAL(18,4),
    [Code dépôt]                      INT,
    [Intitulé dépôt]                  NVARCHAR(200),
    [Prix unitaire BC]                DECIMAL(18,4),
    [Conditionnement]                 NVARCHAR(100),
    [Type de la remise 1]             NVARCHAR(50),
    [Type de la remise 2]             NVARCHAR(50),
    [Référence article fournisseur]   NVARCHAR(200),
    [Article facturé au poids]        INT,
    [Date création]                   DATETIME,
    [Date modification]               DATETIME,
    [SyncDate]                        DATETIME DEFAULT GETDATE()
);
GO

-- =====================================================================
-- 17. Echeances_Achats (sort_order: 19, INCREMENTAL, priority: normal)
-- =====================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Echeances_Achats')
CREATE TABLE Echeances_Achats (
    [id]                       INT IDENTITY(1,1) PRIMARY KEY,
    [DB_Id]                    INT NOT NULL,
    [DB]                       VARCHAR(100) NOT NULL,
    [DB_Caption]               NVARCHAR(200) NOT NULL,
    [Code tier payeur]         NVARCHAR(50),
    [Type Document]            NVARCHAR(500),
    [Date d'échéance]          DATETIME,
    [Pourcentage]              DECIMAL(18,4),
    [N° pièce]                 NVARCHAR(50),
    [Montant échéance devise]  DECIMAL(18,4),
    [Régler]                   NVARCHAR(10),
    [Montant TTC]              DECIMAL(18,4),
    [Mode de réglement]        NVARCHAR(200),
    [Tier payeur]              NVARCHAR(300),
    [Intitulé fournisseur]     NVARCHAR(300),
    [Code fournisseur]         NVARCHAR(50),
    [Date document]            DATETIME,
    [Montant échéance]         DECIMAL(18,4),
    [N° interne]               INT,
    [Date création]            DATETIME,
    [Date modification]        DATETIME,
    [SyncDate]                 DATETIME DEFAULT GETDATE()
);
GO

-- =====================================================================
-- 18. Entête_des_documents_internes (sort_order: 21, FULL, priority: normal)
-- =====================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = N'Entête_des_documents_internes')
CREATE TABLE [Entête_des_documents_internes] (
    [id]                                   INT IDENTITY(1,1) PRIMARY KEY,
    [DB_Id]                                INT NOT NULL,
    [DB]                                   VARCHAR(100) NOT NULL,
    [DB_Caption]                           NVARCHAR(200) NOT NULL,
    [Encours]                              NVARCHAR(10),
    [Type Document]                        NVARCHAR(500),
    [Souche]                               NVARCHAR(100),
    [Statut]                               NVARCHAR(100),
    [Code client]                          NVARCHAR(50),
    [Intitulé client]                      NVARCHAR(300),
    [Code représentant]                    INT,
    [Nom représentant]                     NVARCHAR(200),
    [Date]                                 DATETIME,
    [N° pièce]                             NVARCHAR(50),
    [Document ventilé]                     NVARCHAR(10),
    [Etat]                                 NVARCHAR(200),
    [Entête 1]                             NVARCHAR(200),
    [Entête 2]                             NVARCHAR(200),
    [Entête 3]                             NVARCHAR(200),
    [Entête 4]                             NVARCHAR(200),
    [N° Compte Payeur]                     NVARCHAR(50),
    [Intitulé tiers payeur]                NVARCHAR(300),
    [Dépôt]                                NVARCHAR(200),
    [Devise]                               NVARCHAR(50),
    [Expédition]                           NVARCHAR(100),
    [Langue]                               NVARCHAR(20),
    [Fact/BL]                              NVARCHAR(10),
    [Nb Facture]                           INT,
    [Compte Général]                       NVARCHAR(50),
    [Code d'affaire]                       NVARCHAR(50),
    [Intitulé affaire]                     NVARCHAR(200),
    [Catégorie Comptable]                  NVARCHAR(200),
    [Code dépôt]                           INT,
    [Référence]                            NVARCHAR(200),
    [Cours]                                DECIMAL(18,4),
    [Taux escompte]                        DECIMAL(18,4),
    [Document de reliquat]                 NVARCHAR(10),
    [Document imprimé ]                    NVARCHAR(10),
    [Date livraison souhite]               DATETIME,
    [Date début de l'abonnement lié]       DATETIME,
    [Date fin de l'abonnement lié]         DATETIME,
    [Date début de la périodicité liée]    DATETIME,
    [Date Fin de la périodicité liée]      DATETIME,
    [Document clôturé]                     INT,
    [Type frais]                           NVARCHAR(50),
    [Valeur frais]                         DECIMAL(18,4),
    [Type HT/TTC frais]                   NVARCHAR(10),
    [Statut validé]                        NVARCHAR(10),
    [Intitulé Devise]                      NVARCHAR(50),
    [Catégorie tarifaire ]                 NVARCHAR(100),
    [Condition de livraison]               NVARCHAR(100),
    [Colisage]                             NVARCHAR(200),
    [Montant HT]                           DECIMAL(18,4),
    [Montant TTC]                          DECIMAL(18,4),
    [Montant net à payer]                  DECIMAL(18,4),
    [Montant réglé]                        DECIMAL(18,4),
    [Code lieu de livraison]               INT,
    [Lieu de livraison]                    NVARCHAR(200),
    [Date modification]                    DATETIME,
    [SyncDate]                             DATETIME DEFAULT GETDATE()
);
GO

-- =====================================================================
-- 19. Ligne_des_documents_interne (sort_order: 22, FULL, priority: normal)
-- =====================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Ligne_des_documents_interne')
CREATE TABLE Ligne_des_documents_interne (
    [id]                          INT IDENTITY(1,1) PRIMARY KEY,
    [DB_Id]                       INT NOT NULL,
    [DB]                          VARCHAR(100) NOT NULL,
    [DB_Caption]                  NVARCHAR(200) NOT NULL,
    [N° interne]                  INT,
    [Type Document]               NVARCHAR(500),
    [Code client]                 NVARCHAR(50),
    [Intitulé client]             NVARCHAR(300),
    [N° Pièce]                    NVARCHAR(50),
    [Référence]                   NVARCHAR(200),
    [Intitule affaire]            NVARCHAR(200),
    [Code affaire]                NVARCHAR(50),
    [Date]                        DATETIME,
    [Date document]               DATETIME,
    [Date Livraison]              DATETIME,
    [Code article]                NVARCHAR(100),
    [Désignation]                 NVARCHAR(500),
    [Catalogue 1]                 NVARCHAR(200),
    [Catalogue 2]                 NVARCHAR(200),
    [Catalogue 3]                 NVARCHAR(200),
    [Catalogue 4]                 NVARCHAR(200),
    [Gamme 1]                     NVARCHAR(200),
    [Gamme 2]                     NVARCHAR(200),
    [Colisage]                    NVARCHAR(200),
    [Poids brut]                  FLOAT,
    [Poids net]                   FLOAT,
    [N° Série/Lot]                NVARCHAR(200),
    [Taxe1]                       NVARCHAR(50),
    [Taxe2]                       NVARCHAR(50),
    [Taxe3]                       NVARCHAR(50),
    [Type taux taxe 1]            NVARCHAR(50),
    [Type taux taxe 2]            NVARCHAR(50),
    [Type taux taxe 3]            NVARCHAR(50),
    [Type taxe 1]                 NVARCHAR(50),
    [Type taxe 2]                 NVARCHAR(50),
    [Type taxe 3]                 NVARCHAR(50),
    [Remise 1]                    NVARCHAR(50),
    [Remise 2]                    NVARCHAR(50),
    [Frais d'approche]            FLOAT,
    [PU Devise]                   DECIMAL(18,4),
    [Nomenclature]                NVARCHAR(10),
    [Type remise de pied]         NVARCHAR(10),
    [Type remise exceptionnelle]  NVARCHAR(10),
    [CMUP]                        DECIMAL(18,4),
    [Prix unitaire]               DECIMAL(18,4),
    [Prix unitaire TTC]           DECIMAL(18,4),
    [Quantité]                    DECIMAL(18,4),
    [Montant HT Net]              DECIMAL(18,4),
    [Montant TTC Net]             DECIMAL(18,4),
    [Prix de revient]             DECIMAL(18,4),
    [Date modification]           DATETIME,
    [SyncDate]                    DATETIME DEFAULT GETDATE()
);
GO

-- =====================================================================
-- 20. Etat_Stock (sort_order: 24, FULL, priority: normal)
-- =====================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Etat_Stock')
CREATE TABLE Etat_Stock (
    [id]                     INT IDENTITY(1,1) PRIMARY KEY,
    [DB_Id]                  INT NOT NULL,
    [DB]                     VARCHAR(100) NOT NULL,
    [DB_Caption]             NVARCHAR(200) NOT NULL,
    [Code article]           NVARCHAR(100),
    [Code dépôt]             INT,
    [Quantité minimale]      DECIMAL(18,4),
    [Quantité maximale]      DECIMAL(18,4),
    [Valeur du stock (montant)] DECIMAL(18,4),
    [Quantité en stock]      DECIMAL(18,4),
    [Quntitté réservée]      DECIMAL(18,4),
    [Quantité commandée]     DECIMAL(18,4),
    [Dépôt principale]       INT,
    [N° intene]              INT,
    [Stock mouvementé]       NVARCHAR(10),
    [Désignation article]    NVARCHAR(500),
    [Code famille]           NVARCHAR(50),
    [Intitule]               NVARCHAR(200),
    [DE_Intitule]            NVARCHAR(200),
    [Unité]                  NVARCHAR(50),
    [SyncDate]               DATETIME DEFAULT GETDATE()
);
GO

-- =====================================================================
-- 21. Mouvement_stock (sort_order: 25, FULL, priority: normal)
-- =====================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Mouvement_stock')
CREATE TABLE Mouvement_stock (
    [id]                               INT IDENTITY(1,1) PRIMARY KEY,
    [DB_Id]                            INT NOT NULL,
    [DB]                               VARCHAR(100) NOT NULL,
    [DB_Caption]                       NVARCHAR(200) NOT NULL,
    [Exclure du réapprovisionnement]   NVARCHAR(10),
    [Dépôt]                            NVARCHAR(200),
    [Code Dépôt]                       INT,
    [Code famille]                     NVARCHAR(50),
    [Intitulé famille]                 NVARCHAR(200),
    [Code article]                     NVARCHAR(100),
    [Référence]                        NVARCHAR(200),
    [Domaine mouvement]                NVARCHAR(50),
    [Désignation]                      NVARCHAR(500),
    [Type Mouvement]                   NVARCHAR(200),
    [Date Mouvement]                   DATETIME,
    [N° Pièce]                         NVARCHAR(50),
    [CMUP]                             DECIMAL(18,4),
    [Prix unitaire]                    DECIMAL(18,4),
    [Prix de revient]                  DECIMAL(18,4),
    [DPA-Période]                      FLOAT,
    [Coût standard]                    DECIMAL(18,4),
    [DPA-Vente]                        FLOAT,
    [DPR-Vente]                        FLOAT,
    [Quantité]                         DECIMAL(18,4),
    [N° Série / Lot]                   NVARCHAR(200),
    [Suivi Stock]                      NVARCHAR(50),
    [Gamme 1]                          NVARCHAR(200),
    [Gamme 2]                          NVARCHAR(200),
    [Date Péremption]                  DATETIME,
    [Date Fabrication]                 DATETIME,
    [Sens de mouvement]                NVARCHAR(10),
    [N° interne]                       INT,
    [Montant Stock]                    DECIMAL(18,4),
    [Code coloboratore]                INT,
    [Représentant]                     NVARCHAR(200),
    [Catalogue 1]                      NVARCHAR(200),
    [Catalogue 2]                      NVARCHAR(200),
    [Catalogue 3]                      NVARCHAR(200),
    [Catalogue 4]                      NVARCHAR(200),
    [Intitulé tiers]                   NVARCHAR(300),
    [Code tiers]                       NVARCHAR(50),
    [Article composé]                  NVARCHAR(100),
    [Date modification]                DATETIME,
    [SyncDate]                         DATETIME DEFAULT GETDATE()
);
GO

-- =====================================================================
-- 22. Plan_Reporting (sort_order: 27, FULL, priority: normal)
-- =====================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Plan_Reporting')
CREATE TABLE Plan_Reporting (
    [id]                INT IDENTITY(1,1) PRIMARY KEY,
    [DB_Id]             INT NOT NULL,
    [DB]                VARCHAR(100) NOT NULL,
    [DB_Caption]        NVARCHAR(200) NOT NULL,
    [Code]              NVARCHAR(50),
    [Type de compte]    NVARCHAR(20),
    [Intitulé]          NVARCHAR(300),
    [SyncDate]          DATETIME DEFAULT GETDATE()
);
GO

-- =====================================================================
-- 23. Plan_Comptable (sort_order: 28, FULL, priority: normal)
-- =====================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Plan_Comptable')
CREATE TABLE Plan_Comptable (
    [id]                   INT IDENTITY(1,1) PRIMARY KEY,
    [DB_Id]                INT NOT NULL,
    [DB]                   VARCHAR(100) NOT NULL,
    [DB_Caption]           NVARCHAR(200) NOT NULL,
    [Numéro compte]        NVARCHAR(50),
    [Type de compte]       NVARCHAR(20),
    [Intitulé]             NVARCHAR(300),
    [Classement]           NVARCHAR(100),
    [Nature]               NVARCHAR(100),
    [Type report]          NVARCHAR(20),
    [Code reporting]       NVARCHAR(50),
    [Mise en sommeil]      NVARCHAR(20),
    [Date de création]     DATETIME,
    [Intitulé reporting]   NVARCHAR(300),
    [SyncDate]             DATETIME DEFAULT GETDATE()
);
GO

-- =====================================================================
-- 24. Ecritures_Comptables (sort_order: 29, FULL/INCREMENTAL, priority: normal)
-- Schéma basé sur l'exemple sp_Sync_ECR_CASHPLUS_2026 fourni
-- =====================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Ecritures_Comptables')
CREATE TABLE Ecritures_Comptables (
    [id]                        NVARCHAR(250),
    [DB_Id]                     INT NOT NULL,
    [DB]                        VARCHAR(100) NOT NULL,
    [DB_Caption]                NVARCHAR(200) NOT NULL,
    [Date d'écriture]           DATETIME,
    [N° Compte Général]         NVARCHAR(50),
    [Intitulé compte général]   NVARCHAR(300),
    [Compte Tiers]              NVARCHAR(50),
    [Intitulé tiers]            NVARCHAR(300),
    [N° Pièce]                  NVARCHAR(50),
    [N° facture]                NVARCHAR(50),
    [Code Journal]              NVARCHAR(50),
    [N° Pièce de tréso]         NVARCHAR(50),
    [Libellé]                   NVARCHAR(500),
    [Débit]                     DECIMAL(18,4) DEFAULT 0,
    [Crédit]                    DECIMAL(18,4) DEFAULT 0,
    [Masse]                     VARCHAR(64),
    [Rubrique]                  VARCHAR(64),
    [Poste]                     VARCHAR(64),
    [Compte principal]          VARCHAR(64),
    [Report à Nouveau]          NVARCHAR(20),
    [Regroupement]              NVARCHAR(20),
    [Saisie Analytique]         NVARCHAR(20),
    [Saisie Echéance]           NVARCHAR(20),
    [Saisie Quantité]           NVARCHAR(20),
    [Clé Comptabilité]          INT,
    [Exercice]                  NVARCHAR(10),
    [N° interne]                INT NOT NULL,
    [N° interne de lien]        INT,
    [Date de saisier]           DATETIME,
    [Pointage]                  NVARCHAR(10),
    [Lettre de pointage]        NVARCHAR(20),
    [Lettrage]                  NVARCHAR(10),
    [Lettre]                    NVARCHAR(20),
    [Date d'échéance]           DATETIME,
    [Révision]                  NVARCHAR(20),
    [Parité]                    DECIMAL(18,4),
    [Quantité]                  DECIMAL(18,4),
    [Contrepartie Tiers]        NVARCHAR(50),
    [Code Taxe]                 NVARCHAR(50),
    [Sens]                      NVARCHAR(10),
    [Niveau Rappel]             INT,
    [Montant]                   DECIMAL(18,4),
    [Montnat en devis]          DECIMAL(18,4),
    [Mode de réglement]         NVARCHAR(100),
    [Type à Nouveau]            NVARCHAR(10),
    [Type Ecriture]             NVARCHAR(100),
    [Devise]                    NVARCHAR(100),
    [Référence]                 NVARCHAR(200),
    [N° Dossier Recouvrement]   NVARCHAR(50),
    [Type tiers]                NVARCHAR(20),
    [Nature Compte]             NVARCHAR(100),
    [Libellé Journal]           NVARCHAR(200),
    [Type Code Journal]         NVARCHAR(20),
    [Mois]                      DATETIME,
    [Année]                     INT,
    [cbCreation]                DATETIME,
    [cbModification]            DATETIME,
    [SyncDate]                  DATETIME DEFAULT GETDATE(),
    CONSTRAINT PK_Ecritures_Comptables PRIMARY KEY ([DB], [N° interne])
);
GO

-- =====================================================================
-- 25. Ecritures_Analytiques (sort_order: 30, FULL, priority: normal)
-- =====================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Ecritures_Analytiques')
CREATE TABLE Ecritures_Analytiques (
    [id]                  INT IDENTITY(1,1) PRIMARY KEY,
    [DB_Id]               INT NOT NULL,
    [DB]                  VARCHAR(100) NOT NULL,
    [DB_Caption]          NVARCHAR(200) NOT NULL,
    [N° interne]          INT,
    [N° interne EG]       INT,
    [N_Analytique]        INT,
    [Ligne]               INT,
    [Compte analytique]   NVARCHAR(50),
    [Montant analytique]  DECIMAL(18,4),
    [Quantité]            DECIMAL(18,4),
    [Intitulé]            NVARCHAR(300),
    [Plan analytique]     NVARCHAR(200),
    [SyncDate]            DATETIME DEFAULT GETDATE()
);
GO

-- =====================================================================
-- 26. Conditions_Paiement (sort_order: 32, FULL, priority: normal)
-- =====================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Conditions_Paiement')
CREATE TABLE Conditions_Paiement (
    [id]                INT IDENTITY(1,1) PRIMARY KEY,
    [DB_Id]             INT NOT NULL,
    [DB]                VARCHAR(100) NOT NULL,
    [DB_Caption]        NVARCHAR(200) NOT NULL,
    [Code tiers]        NVARCHAR(50),
    [Code interne réglement] INT,
    [Condition]         NVARCHAR(50),
    [Nbr jour]          INT,
    [Jour mois 1]       INT,
    [Jour mois 2]       INT,
    [Jour mois 3]       INT,
    [Jour mois 4]       INT,
    [Jour mois 5]       INT,
    [Jour mois 6]       INT,
    [RT_TRepart]        INT,
    [Equilibre]         NVARCHAR(20),
    [Valeur]            DECIMAL(18,4),
    [Mode réglement]    NVARCHAR(100),
    [Code réglement]    NVARCHAR(50),
    [SyncDate]          DATETIME DEFAULT GETDATE()
);
GO

-- =====================================================================
-- 27. Encaissement_MP (sort_order: 33, FULL, priority: normal)
-- =====================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Encaissement_MP')
CREATE TABLE Encaissement_MP (
    [id]                INT IDENTITY(1,1) PRIMARY KEY,
    [DB_Id]             INT NOT NULL,
    [DB]                VARCHAR(100) NOT NULL,
    [DB_Caption]        NVARCHAR(200) NOT NULL,
    [SyncDate]          DATETIME DEFAULT GETDATE()
);
GO

-- =====================================================================
-- 28. Decaissement_MP (sort_order: 34, FULL, priority: normal)
-- =====================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Decaissement_MP')
CREATE TABLE Decaissement_MP (
    [id]                INT IDENTITY(1,1) PRIMARY KEY,
    [DB_Id]             INT NOT NULL,
    [DB]                VARCHAR(100) NOT NULL,
    [DB_Caption]        NVARCHAR(200) NOT NULL,
    [SyncDate]          DATETIME DEFAULT GETDATE()
);
GO

-- =====================================================================
-- 29. RH_Affectation_Histo (sort_order: 36, FULL, priority: low)
-- =====================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'RH_Affectation_Histo')
CREATE TABLE RH_Affectation_Histo (
    [id]                INT IDENTITY(1,1) PRIMARY KEY,
    [DB_Id]             INT NOT NULL,
    [DB]                VARCHAR(100) NOT NULL,
    [DB_Caption]        NVARCHAR(200) NOT NULL,
    [SyncDate]          DATETIME DEFAULT GETDATE()
);
GO

-- =====================================================================
-- 30. RH_Paie (sort_order: 38, FULL, priority: low)
-- =====================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'RH_Paie')
CREATE TABLE RH_Paie (
    [id]                INT IDENTITY(1,1) PRIMARY KEY,
    [DB_Id]             INT NOT NULL,
    [DB]                VARCHAR(100) NOT NULL,
    [DB_Caption]        NVARCHAR(200) NOT NULL,
    [SyncDate]          DATETIME DEFAULT GETDATE()
);
GO

-- =====================================================================
-- 31. RH_Congé_Histo (sort_order: 39, FULL, priority: low)
-- =====================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = N'RH_Congé_Histo')
CREATE TABLE [RH_Congé_Histo] (
    [id]                    INT IDENTITY(1,1) PRIMARY KEY,
    [DB_Id]                 INT NOT NULL,
    [DB]                    VARCHAR(100) NOT NULL,
    [DB_Caption]            NVARCHAR(200) NOT NULL,
    [Matricule]             NVARCHAR(50),
    [Date début congé 1]    DATETIME,
    [Date fin congé 1]      DATETIME,
    [Date début congé]      DATETIME,
    [Date fin congé]        DATETIME,
    [SyncDate]              DATETIME DEFAULT GETDATE()
);
GO

-- =====================================================================
-- 32. RH_Salaire_Histo (sort_order: 40, FULL, priority: low)
-- =====================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'RH_Salaire_Histo')
CREATE TABLE RH_Salaire_Histo (
    [id]                INT IDENTITY(1,1) PRIMARY KEY,
    [DB_Id]             INT NOT NULL,
    [DB]                VARCHAR(100) NOT NULL,
    [DB_Caption]        NVARCHAR(200) NOT NULL,
    [SyncDate]          DATETIME DEFAULT GETDATE()
);
GO

-- =====================================================================
-- 33. RH_Contrat_Tra_Histo (sort_order: 41, FULL, priority: low)
-- =====================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'RH_Contrat_Tra_Histo')
CREATE TABLE RH_Contrat_Tra_Histo (
    [id]                   INT IDENTITY(1,1) PRIMARY KEY,
    [DB_Id]                INT NOT NULL,
    [DB]                   VARCHAR(100) NOT NULL,
    [DB_Caption]           NVARCHAR(200) NOT NULL,
    [Matricule]            NVARCHAR(50),
    [Numéro contrat]       NVARCHAR(50),
    [Code]                 NVARCHAR(50),
    [Intitulé contrat]     NVARCHAR(200),
    [Date début contrat]   DATETIME,
    [Date fin contrat]     DATETIME,
    [Fin période essai]    DATETIME,
    [Date Début]           DATETIME,
    [Date fin]             DATETIME,
    [SyncDate]             DATETIME DEFAULT GETDATE()
);
GO

-- =====================================================================
-- 34. RH_Effectif_Histo (sort_order: 42, FULL, priority: low)
-- =====================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'RH_Effectif_Histo')
CREATE TABLE RH_Effectif_Histo (
    [id]                INT IDENTITY(1,1) PRIMARY KEY,
    [DB_Id]             INT NOT NULL,
    [DB]                VARCHAR(100) NOT NULL,
    [DB_Caption]        NVARCHAR(200) NOT NULL,
    [SyncDate]          DATETIME DEFAULT GETDATE()
);
GO

-- =====================================================================
-- 35. RH_Historique (sort_order: 43, FULL, priority: low)
-- =====================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'RH_Historique')
CREATE TABLE RH_Historique (
    [id]                INT IDENTITY(1,1) PRIMARY KEY,
    [DB_Id]             INT NOT NULL,
    [DB]                VARCHAR(100) NOT NULL,
    [DB_Caption]        NVARCHAR(200) NOT NULL,
    [SyncDate]          DATETIME DEFAULT GETDATE()
);
GO

-- =====================================================================
-- INDEX UTILES
-- =====================================================================
-- Index sur DB pour filtrage par source
CREATE NONCLUSTERED INDEX IX_Collaborateurs_DB ON Collaborateurs ([DB]);
CREATE NONCLUSTERED INDEX IX_Articles_DB ON Articles ([DB]);
CREATE NONCLUSTERED INDEX IX_Clients_DB ON Clients ([DB]);
CREATE NONCLUSTERED INDEX IX_Fournisseurs_DB ON Fournisseurs ([DB]);
CREATE NONCLUSTERED INDEX IX_Ecritures_Comptables_DB ON Ecritures_Comptables ([DB]);
CREATE NONCLUSTERED INDEX IX_Etat_Stock_DB ON Etat_Stock ([DB]);
GO

PRINT '';
PRINT '══════════════════════════════════════════════════════════════';
PRINT ' 35 TABLES CIBLES DWH CREEES AVEC SUCCES';
PRINT '══════════════════════════════════════════════════════════════';
PRINT '';
PRINT ' ATTENTION : sp_Sync_Generic utilise INFORMATION_SCHEMA.COLUMNS';
PRINT ' pour decouvrir les colonnes de chaque table cible.';
PRINT ' Les tables avec schema minimal (SyncDate uniquement)';
PRINT ' DOIVENT etre completees avant synchronisation.';
PRINT ' Ajoutez les colonnes metier depuis sync_tables.yaml';
PRINT ' ou insert_sync_query_data.sql.';
PRINT '';
PRINT ' Tables completes : Collaborateurs, Info_Libres, Articles,';
PRINT '   Clients, Lieu_Livraison_Client, Entete_des_ventes,';
PRINT '   Reglements_Clients, Fournisseurs, Paiements_Fournisseurs,';
PRINT '   Etat_Stock, Plan_Reporting, Plan_Comptable,';
PRINT '   Ecritures_Comptables, Ecritures_Analytiques,';
PRINT '   Conditions_Paiement, RH_Conge_Histo, RH_Contrat_Tra_Histo';
PRINT '';
PRINT ' Tables stub (a completer) : Lignes_des_ventes,';
PRINT '   Imputation_Factures_Ventes, Imputation_BL,';
PRINT '   Echeances_Ventes, Entete_des_achats, Lignes_des_achats,';
PRINT '   Echeances_Achats, Imputation_Factures_Achats,';
PRINT '   Entete_des_documents_internes, Ligne_des_documents_interne,';
PRINT '   Mouvement_stock, Encaissement_MP, Decaissement_MP,';
PRINT '   RH_Affectation_Histo, RH_Paie, RH_Salaire_Histo,';
PRINT '   RH_Effectif_Histo, RH_Historique';
PRINT '';
