-- Script de correction: Ajouter colonnes manquantes à APP_ETL_Agents
-- Exécuter ce script sur OptiBoard_SaaS

USE OptiBoard_SaaS;
GO

-- Ajouter la colonne last_sync_message si elle n'existe pas
IF NOT EXISTS (
    SELECT * FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'APP_ETL_Agents'
    AND COLUMN_NAME = 'last_sync_message'
)
BEGIN
    ALTER TABLE APP_ETL_Agents ADD last_sync_message NVARCHAR(MAX) NULL;
    PRINT 'Colonne last_sync_message ajoutee avec succes';
END
GO

-- Ajouter api_key_prefix si elle n'existe pas
IF NOT EXISTS (
    SELECT * FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'APP_ETL_Agents'
    AND COLUMN_NAME = 'api_key_prefix'
)
BEGIN
    ALTER TABLE APP_ETL_Agents ADD api_key_prefix VARCHAR(20) NULL;
    PRINT 'Colonne api_key_prefix ajoutee avec succes';
END
GO

-- Ajouter sage_server si elle n'existe pas
IF NOT EXISTS (
    SELECT * FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'APP_ETL_Agents'
    AND COLUMN_NAME = 'sage_server'
)
BEGIN
    ALTER TABLE APP_ETL_Agents ADD sage_server NVARCHAR(200) NULL;
    PRINT 'Colonne sage_server ajoutee avec succes';
END
GO

-- Ajouter sage_database si elle n'existe pas
IF NOT EXISTS (
    SELECT * FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'APP_ETL_Agents'
    AND COLUMN_NAME = 'sage_database'
)
BEGIN
    ALTER TABLE APP_ETL_Agents ADD sage_database NVARCHAR(200) NULL;
    PRINT 'Colonne sage_database ajoutee avec succes';
END
GO

-- Ajouter sage_username si elle n'existe pas
IF NOT EXISTS (
    SELECT * FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'APP_ETL_Agents'
    AND COLUMN_NAME = 'sage_username'
)
BEGIN
    ALTER TABLE APP_ETL_Agents ADD sage_username NVARCHAR(100) NULL;
    PRINT 'Colonne sage_username ajoutee avec succes';
END
GO

PRINT 'Script de correction termine';
GO
