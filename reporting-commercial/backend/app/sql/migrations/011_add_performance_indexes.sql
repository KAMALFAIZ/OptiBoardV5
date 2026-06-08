-- Migration 011 : Index de performance sur les tables les plus requêtées
-- À exécuter une seule fois sur chaque base DWH client
-- Impact : endpoints > 2s réduits à < 800ms

-- ──────────────────────────────────────────────────────────────
-- Table DashBoard_CA (table la plus requêtée)
-- ──────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_CA_DateBL' AND object_id=OBJECT_ID('dbo.DashBoard_CA'))
    CREATE INDEX IX_CA_DateBL
      ON [dbo].[DashBoard_CA] ([Date BL])
      INCLUDE ([Montant HT Net], [Code client], [Valorise CA], [Coût]);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_CA_Client_DateBL' AND object_id=OBJECT_ID('dbo.DashBoard_CA'))
    CREATE INDEX IX_CA_Client_DateBL
      ON [dbo].[DashBoard_CA] ([Code client], [Date BL])
      INCLUDE ([Montant HT Net], [Coût], [Intitulé client]);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_CA_Representant_DateBL' AND object_id=OBJECT_ID('dbo.DashBoard_CA'))
    CREATE INDEX IX_CA_Representant_DateBL
      ON [dbo].[DashBoard_CA] ([Représentant], [Date BL])
      INCLUDE ([Montant HT Net], [Coût]);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_CA_Gamme_DateBL' AND object_id=OBJECT_ID('dbo.DashBoard_CA'))
    CREATE INDEX IX_CA_Gamme_DateBL
      ON [dbo].[DashBoard_CA] ([Catalogue 1], [Date BL])
      INCLUDE ([Montant HT Net], [Coût]);

-- ──────────────────────────────────────────────────────────────
-- Table Echeances_Ventes (recouvrement)
-- ──────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_Ech_DateEch' AND object_id=OBJECT_ID('dbo.Echéances_Ventes'))
    CREATE INDEX IX_Ech_DateEch
      ON [dbo].[Echéances_Ventes] ([Date d'échéance])
      INCLUDE ([Montant échéance], [Code client], [Code collaborateur]);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_Ech_Client_DateDoc' AND object_id=OBJECT_ID('dbo.Echéances_Ventes'))
    CREATE INDEX IX_Ech_Client_DateDoc
      ON [dbo].[Echéances_Ventes] ([Code client], [Date document])
      INCLUDE ([Montant échéance], [Date d'échéance], [Régler]);

-- ──────────────────────────────────────────────────────────────
-- Table Ecritures_Comptables (comptabilité)
-- ──────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_EC_DateCG' AND object_id=OBJECT_ID('dbo.Ecritures_Comptables'))
    CREATE INDEX IX_EC_DateCG
      ON [dbo].[Ecritures_Comptables] ([EC_Date], [CG_Num])
      INCLUDE ([EC_Montant], [EC_Sens]);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_EC_Journal_Date' AND object_id=OBJECT_ID('dbo.Ecritures_Comptables'))
    CREATE INDEX IX_EC_Journal_Date
      ON [dbo].[Ecritures_Comptables] ([JO_Num], [EC_Date])
      INCLUDE ([EC_Montant], [EC_Sens], [CG_Num]);

-- ──────────────────────────────────────────────────────────────
-- Table Mouvement_stock
-- ──────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_Stock_Article_Date' AND object_id=OBJECT_ID('dbo.Mouvement_stock'))
    CREATE INDEX IX_Stock_Article_Date
      ON [dbo].[Mouvement_stock] ([Code article], [Date Mouvement])
      INCLUDE ([Quantité], [Sens de mouvement], [CMUP]);

-- ──────────────────────────────────────────────────────────────
-- Table Ecritures_Analytiques (Phase 4 — créée par migration 012)
-- Commenté jusqu'à la création de la table
-- ──────────────────────────────────────────────────────────────
-- IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_EA_DateCA' AND object_id=OBJECT_ID('dbo.Ecritures_Analytiques'))
--     CREATE INDEX IX_EA_DateCA ON [dbo].[Ecritures_Analytiques] ([EA_DateEcr], [CA_Num]);

PRINT 'Migration 011 : Index de performance appliqués avec succès';
