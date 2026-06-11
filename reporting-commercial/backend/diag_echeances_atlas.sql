-- ============================================================
-- DIAGNOSTIC : Echéances_Ventes non synchronisée — ATLASMULTIMATERIAL
-- Exécuter dans SSMS connecté au serveur OptiBoard
-- ============================================================

-- ─────────────────────────────────────────────────────────────
-- ÉTAPE 1 : Trouver le DWH code d'ATLASMULTIMATERIAL
--           (base centrale OptiBoard_SaaS)
-- ─────────────────────────────────────────────────────────────
PRINT '=== 1. DWH CODE ATLASMULTIMATERIAL ==='
USE OptiBoard_SaaS

SELECT dwh_code, nom, db_name, actif
FROM APP_DWH
WHERE nom LIKE '%ATLAS%' OR dwh_code LIKE '%ATLAS%'


-- ─────────────────────────────────────────────────────────────
-- ÉTAPE 2 : Vérifier APP_ETL_Tables_Config (centrale)
--           La source_query doit être définie (pas TODO)
-- ─────────────────────────────────────────────────────────────
PRINT '=== 2. APP_ETL_Tables_Config (centrale) ==='
USE OptiBoard_SaaS

SELECT
    code,
    actif,
    LEFT(source_query, 100) AS [source_query debut],
    CASE WHEN LTRIM(UPPER(ISNULL(source_query,''))) LIKE 'TODO%'
         THEN '*** PLACEHOLDER TODO — table ignorée ***'
         WHEN source_query IS NULL OR source_query = ''
         THEN '*** VIDE — table ignorée ***'
         ELSE 'OK'
    END AS [Statut source_query]
FROM APP_ETL_Tables_Config
WHERE code LIKE '%cheance%' OR code LIKE '%Echeance%'


-- ─────────────────────────────────────────────────────────────
-- ÉTAPE 3 : Vérifier l'agent ETL lié à ATLASMULTIMATERIAL
-- ─────────────────────────────────────────────────────────────
PRINT '=== 3. AGENT ETL ATLASMULTIMATERIAL ==='
USE OptiBoard_SaaS

SELECT
    a.agent_id,
    a.nom,
    a.dwh_code,
    a.is_enabled,
    a.is_active,
    a.last_heartbeat
FROM APP_ETL_Agents a
WHERE a.dwh_code LIKE '%ATLAS%' OR a.nom LIKE '%ATLAS%'


-- ─────────────────────────────────────────────────────────────
-- ÉTAPE 4 : APP_ETL_Agent_Tables pour l'agent ATLAS
--           Remplacer '<AGENT_ID>' par l'agent_id trouvé étape 3
-- ─────────────────────────────────────────────────────────────
PRINT '=== 4. APP_ETL_Agent_Tables (centrale) ==='
USE OptiBoard_SaaS

SELECT
    table_name,
    target_table,
    sync_type,
    is_enabled,
    priority,
    last_sync,
    last_sync_status
FROM APP_ETL_Agent_Tables
WHERE agent_id IN (
    SELECT agent_id FROM APP_ETL_Agents
    WHERE dwh_code LIKE '%ATLAS%' OR nom LIKE '%ATLAS%'
)
AND (table_name LIKE '%cheance%' OR target_table LIKE '%cheance%')


-- ─────────────────────────────────────────────────────────────
-- ÉTAPE 5 : APP_ETL_Tables_Published dans la base DWH client
--           Remplacer 'OptiBoard_ATLAS' par le vrai db_name (étape 1)
-- ─────────────────────────────────────────────────────────────
PRINT '=== 5. APP_ETL_Tables_Published (base DWH cliente) ==='
-- Adapter le nom de la base DWH selon résultat étape 1 :
USE [OptiBoard_ATLAS]  -- ← CHANGER ICI

SELECT
    code,
    target_table,
    sync_type,
    is_enabled,
    interval_minutes,
    priority
FROM APP_ETL_Tables_Published
WHERE code LIKE '%cheance%' OR target_table LIKE '%cheance%'
ORDER BY code


-- ─────────────────────────────────────────────────────────────
-- ÉTAPE 6 : Logs ETL récents pour cette table
-- ─────────────────────────────────────────────────────────────
PRINT '=== 6. LOGS ETL RECENTS Echéances_Ventes ==='
USE OptiBoard_SaaS

SELECT TOP 20
    agent_id,
    table_name,
    sync_type,
    status,
    rows_extracted,
    rows_inserted,
    error_message,
    created_at
FROM APP_ETL_Sync_Log
WHERE (table_name LIKE '%cheance%' OR table_name LIKE '%Echeance%')
  AND agent_id IN (
      SELECT agent_id FROM APP_ETL_Agents
      WHERE dwh_code LIKE '%ATLAS%' OR nom LIKE '%ATLAS%'
  )
ORDER BY created_at DESC


-- ─────────────────────────────────────────────────────────────
-- ÉTAPE 7 : La table Echéances_Ventes existe-t-elle dans le DWH ?
--           Adapter 'OptiBoard_ATLAS' selon étape 1
-- ─────────────────────────────────────────────────────────────
PRINT '=== 7. EXISTENCE TABLE + NB LIGNES ==='
USE [OptiBoard_ATLAS]  -- ← CHANGER ICI

SELECT
    t.name AS [Table],
    p.rows AS [Nb lignes]
FROM sys.tables t
JOIN sys.partitions p ON t.object_id = p.object_id AND p.index_id IN (0,1)
WHERE t.name LIKE '%cheance%' OR t.name LIKE '%Echeance%'
