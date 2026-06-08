-- =====================================================
-- Script de Migration Multi-Tenant
-- De: OptiBoard_SaaS (base unique)
-- Vers: OptiBoard_SaaS (MASTER) + OptiBoard_XXX (par client)
-- =====================================================
--
-- Architecture cible:
--   OptiBoard_SaaS (MASTER) = auth, routage, templates systeme
--   OptiBoard_XXX (CLIENT) = config client (dashboards, menus, etc.)
--   DWH_XXX = donnees client (inchange)
-- =====================================================

USE OptiBoard_SaaS;
GO

-- =====================================================
-- ETAPE 1: Table de routage client dans MASTER
-- =====================================================

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ClientDB' AND xtype='U')
CREATE TABLE APP_ClientDB (
    id INT IDENTITY(1,1) PRIMARY KEY,
    dwh_code VARCHAR(50) UNIQUE NOT NULL,       -- lien vers APP_DWH.code
    db_name NVARCHAR(100) NOT NULL,             -- ex: OptiBoard_ESSAIDI
    db_server NVARCHAR(200) NULL,               -- NULL = meme serveur que MASTER
    db_user NVARCHAR(100) NULL,                 -- NULL = memes credentials que MASTER
    db_password NVARCHAR(200) NULL,             -- NULL = memes credentials que MASTER
    actif BIT DEFAULT 1,
    date_creation DATETIME DEFAULT GETDATE(),
    CONSTRAINT FK_ClientDB_DWH FOREIGN KEY (dwh_code) REFERENCES APP_DWH(code) ON DELETE CASCADE
);
GO

-- Index pour performance
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_APP_ClientDB_dwh_code')
    CREATE INDEX IX_APP_ClientDB_dwh_code ON APP_ClientDB(dwh_code);
GO

PRINT 'Table APP_ClientDB creee dans MASTER';
GO
