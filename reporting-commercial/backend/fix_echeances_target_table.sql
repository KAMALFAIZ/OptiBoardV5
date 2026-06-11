-- ============================================================
-- FIX COMPLET : Echéances_Ventes — correction du nom de table
-- RACINE : APP_ETL_Tables_Config (centrale) avait 'é' minuscule
--          → propagé vers APP_ETL_Tables_Published (DWH clients)
--          → agent C# créait la table [échéances_Ventes]
--
-- STRUCTURE RÉELLE :
--   APP_DWH          : colonnes code, nom, base_dwh (PAS dwh_code/db_name)
--   APP_ClientDB     : colonnes dwh_code, db_name (routage auth)
--   APP_ETL_Agents   : dans la base cliente (code_societe, pas dwh_code)
--
-- INSTRUCTIONS :
--   1. Exécuter ÉTAPE A dans OptiBoard_SaaS
--   2. Adapter le USE avec le db_name trouvé en A2
--   3. Exécuter ÉTAPE B dans la base DWH ATLAS
-- ============================================================

-- ════════════════════════════════════════════════════════════
-- ÉTAPE A — BASE CENTRALE (OptiBoard_SaaS)
-- ════════════════════════════════════════════════════════════
USE OptiBoard_SaaS

-- A1. État avant fix
PRINT '=== A1. ETAT AVANT FIX — APP_ETL_Tables_Config ==='
SELECT code, target_table, actif
FROM APP_ETL_Tables_Config
WHERE code        LIKE '%cheance%'
   OR target_table LIKE '%cheance%'

-- A2. Trouver le db_name de la base DWH ATLAS
--     APP_DWH.code  = identifiant DWH (ex: ATLAS)
--     APP_DWH.base_dwh = nom de la base DWH locale
--     APP_ClientDB.db_name = nom de la base tel qu'utilisé par le routage
PRINT '=== A2. BASES DWH ATLAS ==='
SELECT d.code, d.nom, d.base_dwh, c.db_name, d.actif
FROM APP_DWH d
LEFT JOIN APP_ClientDB c ON c.dwh_code = d.code
WHERE d.nom  LIKE '%ATLAS%'
   OR d.code LIKE '%ATLAS%'

-- A3. FIX : corriger target_table dans APP_ETL_Tables_Config
UPDATE APP_ETL_Tables_Config
SET target_table = N'Echéances_Ventes'
WHERE target_table COLLATE Latin1_General_CS_AS IN (
    N'échéances_Ventes',
    N'Echeances_Ventes',
    N'echeances_Ventes',
    N'echeances_ventes'
)
PRINT CONCAT('A3. APP_ETL_Tables_Config corrigé : ', @@ROWCOUNT, ' ligne(s)')

-- A4. FIX : corriger target_table dans APP_ETL_Agent_Tables (toutes lignes, tous agents)
UPDATE APP_ETL_Agent_Tables
SET target_table = N'Echéances_Ventes'
WHERE target_table COLLATE Latin1_General_CS_AS IN (
    N'échéances_Ventes',
    N'Echeances_Ventes',
    N'echeances_Ventes',
    N'echeances_ventes'
)
PRINT CONCAT('A4. APP_ETL_Agent_Tables corrigé : ', @@ROWCOUNT, ' ligne(s)')

-- A5. Vérification finale centrale
PRINT '=== A5. ETAT APRES FIX — APP_ETL_Tables_Config ==='
SELECT code, target_table, actif
FROM APP_ETL_Tables_Config
WHERE code LIKE '%cheance%' OR target_table LIKE '%cheance%'


-- ════════════════════════════════════════════════════════════
-- ÉTAPE B — BASE DWH CLIENT (ATLASMULTIMATERIAL)
-- Remplacer 'GROUPE_ATLAS' par le db_name trouvé en A2
-- ════════════════════════════════════════════════════════════
USE [GROUPE_ATLAS]   -- ← ADAPTER avec le vrai db_name (colonne base_dwh ou db_name de A2)

-- B1. État avant fix
PRINT '=== B1. ETAT AVANT FIX — APP_ETL_Tables_Published ==='
SELECT code, target_table, is_enabled
FROM APP_ETL_Tables_Published
WHERE code        LIKE '%cheance%'
   OR target_table LIKE '%cheance%'

-- B2. FIX : corriger target_table dans APP_ETL_Tables_Published
UPDATE APP_ETL_Tables_Published
SET target_table = N'Echéances_Ventes'
WHERE target_table COLLATE Latin1_General_CS_AS IN (
    N'échéances_Ventes',
    N'Echeances_Ventes',
    N'echeances_Ventes',
    N'echeances_ventes'
)
PRINT CONCAT('B2. APP_ETL_Tables_Published corrigé : ', @@ROWCOUNT, ' ligne(s)')

-- B3. Renommer la table DWH si elle existe avec le mauvais 'é'
IF EXISTS (
    SELECT 1 FROM sys.tables
    WHERE name COLLATE Latin1_General_CS_AS = N'échéances_Ventes'
)
BEGIN
    EXEC sp_rename N'échéances_Ventes', N'Echéances_Ventes'
    PRINT 'B3. Table renommée : [échéances_Ventes] → [Echéances_Ventes]'
END
ELSE IF EXISTS (
    SELECT 1 FROM sys.tables
    WHERE name COLLATE Latin1_General_CS_AS = N'Echeances_Ventes'
)
BEGIN
    EXEC sp_rename N'Echeances_Ventes', N'Echéances_Ventes'
    PRINT 'B3. Table renommée : [Echeances_Ventes] → [Echéances_Ventes]'
END
ELSE
BEGIN
    PRINT 'B3. Aucun renommage nécessaire (table absente ou déjà correcte)'
END

-- B4. Vérification finale
PRINT '=== B4. ETAT APRES FIX ==='
SELECT code, target_table, is_enabled
FROM APP_ETL_Tables_Published
WHERE code LIKE '%cheance%' OR target_table LIKE '%cheance%'

SELECT name AS [Table], create_date
FROM sys.tables
WHERE name LIKE '%cheance%' OR name LIKE '%Echeance%'
