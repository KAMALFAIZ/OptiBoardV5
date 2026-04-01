-- ============================================================
-- Script d'import des tables ETL depuis SyncQuery
-- Execute ce script dans la base OptiBoard_SaaS
-- ============================================================

-- 1. Ajouter la colonne sort_order si elle n'existe pas
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('ETL_Tables_Config') AND name = 'sort_order')
BEGIN
    ALTER TABLE ETL_Tables_Config ADD sort_order INT DEFAULT 0;
    PRINT 'Colonne sort_order ajoutee';
END
GO

-- 2. Vider la table existante (optionnel - decommenter si besoin)
-- DELETE FROM ETL_Tables_Config;
-- PRINT 'Table ETL_Tables_Config videe';

-- 3. Importer les donnees depuis SyncQuery
INSERT INTO ETL_Tables_Config (
    name,
    source_table,
    source_query,
    target_table,
    primary_key,
    sync_type,
    timestamp_column,
    priority,
    batch_size,
    description,
    enabled,
    sort_order,
    created_at,
    updated_at
)
SELECT
    sq.Caption AS name,
    NULL AS source_table,  -- On utilise la query, pas la table
    sq.Query1 AS source_query,
    sq.DestTable AS target_table,
    sq.PrimaryKey1 AS primary_key,
    CASE
        WHEN sq.[Colonne incrementale] IS NOT NULL AND sq.[Colonne incrementale] <> ''
        THEN 'incremental'
        ELSE 'full'
    END AS sync_type,
    sq.[Colonne incrementale] AS timestamp_column,
    CASE
        WHEN sq.[Order] <= 10 THEN 'high'
        WHEN sq.[Order] <= 50 THEN 'normal'
        ELSE 'low'
    END AS priority,
    10000 AS batch_size,
    sq.Caption AS description,
    1 AS enabled,
    sq.[Order] AS sort_order,
    GETDATE() AS created_at,
    GETDATE() AS updated_at
FROM SyncQuery sq
WHERE sq.Query1 IS NOT NULL AND sq.Query1 <> ''
  AND NOT EXISTS (
      SELECT 1 FROM ETL_Tables_Config etc
      WHERE etc.name = sq.Caption
  );

PRINT CAST(@@ROWCOUNT AS VARCHAR) + ' tables importees depuis SyncQuery';
GO

-- 4. Afficher le resultat
SELECT
    id,
    name,
    target_table,
    sync_type,
    timestamp_column,
    priority,
    sort_order,
    enabled
FROM ETL_Tables_Config
ORDER BY sort_order, name;
GO
