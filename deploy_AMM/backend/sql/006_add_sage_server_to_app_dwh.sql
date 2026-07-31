-- =====================================================
-- Migration: Ajouter les colonnes Sage dans APP_DWH
-- Permet de stocker les infos de connexion au serveur Sage
-- pour le controle du SQL Agent (start/stop/status)
-- =====================================================

USE OptiBoard_SaaS;
GO

IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('APP_DWH') AND name = 'sage_server')
    ALTER TABLE APP_DWH ADD sage_server VARCHAR(200) NULL;
GO

IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('APP_DWH') AND name = 'sage_user')
    ALTER TABLE APP_DWH ADD sage_user VARCHAR(100) NULL;
GO

IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('APP_DWH') AND name = 'sage_pwd')
    ALTER TABLE APP_DWH ADD sage_pwd VARCHAR(200) NULL;
GO

PRINT 'Colonnes sage_server, sage_user, sage_pwd ajoutees a APP_DWH';
GO
