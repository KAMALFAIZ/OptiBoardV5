-- ============================================================
-- Script de reset complet de la table ETL_Tables_Config
-- Execute ce script dans la base OptiBoard_SaaS
-- ============================================================

-- 1. Vider completement la table
DELETE FROM ETL_Tables_Config;
PRINT 'Table ETL_Tables_Config videe: ' + CAST(@@ROWCOUNT AS VARCHAR) + ' lignes supprimees';
GO

-- 2. Verifier que la table est vide
SELECT COUNT(*) AS [Nombre de lignes restantes] FROM ETL_Tables_Config;
GO

PRINT 'Reset termine. L''agent ETL utilisera maintenant le fichier YAML.';
GO
