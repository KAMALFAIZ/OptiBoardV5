-- ============================================================
-- Script de configuration des intervalles differencies par table
-- 3 niveaux: CRITIQUE (1 min), MOYEN (3 min), STABLE (10 min)
-- Cible: ETL_Tables_Config (config globale)
--       + APP_ETL_Agent_Tables (si non vide, config par agent)
-- ============================================================

-- D'abord, lister les noms exacts dans les 2 tables
PRINT '=== Contenu ETL_Tables_Config ===';
SELECT name, interval_minutes, priority FROM ETL_Tables_Config ORDER BY name;

PRINT '';
PRINT '=== Contenu APP_ETL_Agent_Tables ===';
SELECT table_name, interval_minutes, priority FROM APP_ETL_Agent_Tables ORDER BY table_name;

PRINT '';
PRINT '=== Mise a jour ETL_Tables_Config ===';
PRINT '';

-- ============================================================
-- TABLES CRITIQUES: interval_minutes = 1, priority = high
-- ============================================================
PRINT '--- Tables CRITIQUES (1 min) ---';

UPDATE ETL_Tables_Config SET interval_minutes = 1, priority = 'high'
WHERE name LIKE '%tes des ventes';
PRINT CONCAT('  Entetes des ventes: ', @@ROWCOUNT);

UPDATE ETL_Tables_Config SET interval_minutes = 1, priority = 'high'
WHERE name LIKE '%glements clients';
PRINT CONCAT('  Reglements clients: ', @@ROWCOUNT);

UPDATE ETL_Tables_Config SET interval_minutes = 1, priority = 'high'
WHERE name = 'Lignes des ventes';
PRINT CONCAT('  Lignes des ventes: ', @@ROWCOUNT);

UPDATE ETL_Tables_Config SET interval_minutes = 1, priority = 'high'
WHERE name LIKE '%ances ventes';
PRINT CONCAT('  Echeances ventes: ', @@ROWCOUNT);

UPDATE ETL_Tables_Config SET interval_minutes = 1, priority = 'high'
WHERE name LIKE '%tes des achats';
PRINT CONCAT('  Entetes des achats: ', @@ROWCOUNT);

UPDATE ETL_Tables_Config SET interval_minutes = 1, priority = 'high'
WHERE name LIKE '%glements fournisseurs';
PRINT CONCAT('  Reglements fournisseurs: ', @@ROWCOUNT);

UPDATE ETL_Tables_Config SET interval_minutes = 1, priority = 'high'
WHERE name = 'Lignes des achats';
PRINT CONCAT('  Lignes des achats: ', @@ROWCOUNT);

UPDATE ETL_Tables_Config SET interval_minutes = 1, priority = 'high'
WHERE name LIKE '%ances achats';
PRINT CONCAT('  Echeances achats: ', @@ROWCOUNT);

-- ============================================================
-- TABLES MOYENNES: interval_minutes = 3, priority = normal
-- ============================================================
PRINT '';
PRINT '--- Tables MOYENNES (3 min) ---';

UPDATE ETL_Tables_Config SET interval_minutes = 3, priority = 'normal'
WHERE name = 'Liste des articles';
PRINT CONCAT('  Liste des articles: ', @@ROWCOUNT);

UPDATE ETL_Tables_Config SET interval_minutes = 3, priority = 'normal'
WHERE name LIKE 'Imputation%factures des ventes';
PRINT CONCAT('  Imputation factures ventes: ', @@ROWCOUNT);

UPDATE ETL_Tables_Config SET interval_minutes = 3, priority = 'normal'
WHERE name = 'Liste des fournisseurs';
PRINT CONCAT('  Liste des fournisseurs: ', @@ROWCOUNT);

UPDATE ETL_Tables_Config SET interval_minutes = 3, priority = 'normal'
WHERE name = 'Imputation factures des achats';
PRINT CONCAT('  Imputation factures achats: ', @@ROWCOUNT);

UPDATE ETL_Tables_Config SET interval_minutes = 3, priority = 'normal'
WHERE name LIKE 'Ent%te des documents interne';
PRINT CONCAT('  Entete documents interne: ', @@ROWCOUNT);

UPDATE ETL_Tables_Config SET interval_minutes = 3, priority = 'normal'
WHERE name = 'Ligne des documents internes';
PRINT CONCAT('  Ligne documents internes: ', @@ROWCOUNT);

UPDATE ETL_Tables_Config SET interval_minutes = 3, priority = 'normal'
WHERE name = 'Etat du stock';
PRINT CONCAT('  Etat du stock: ', @@ROWCOUNT);

UPDATE ETL_Tables_Config SET interval_minutes = 3, priority = 'normal'
WHERE name = 'Mouvement stock';
PRINT CONCAT('  Mouvement stock: ', @@ROWCOUNT);

UPDATE ETL_Tables_Config SET interval_minutes = 3, priority = 'normal'
WHERE name LIKE 'Les %critures comptables';
PRINT CONCAT('  Les ecritures comptables: ', @@ROWCOUNT);

-- ============================================================
-- TABLES STABLES: interval_minutes = 10, priority = low
-- ============================================================
PRINT '';
PRINT '--- Tables STABLES (10 min) ---';

UPDATE ETL_Tables_Config SET interval_minutes = 10, priority = 'low'
WHERE name = 'Collaborateurs';
PRINT CONCAT('  Collaborateurs: ', @@ROWCOUNT);

UPDATE ETL_Tables_Config SET interval_minutes = 10, priority = 'low'
WHERE name = 'Informations libres';
PRINT CONCAT('  Informations libres: ', @@ROWCOUNT);

UPDATE ETL_Tables_Config SET interval_minutes = 10, priority = 'low'
WHERE name = 'Liste des clients';
PRINT CONCAT('  Liste des clients: ', @@ROWCOUNT);

UPDATE ETL_Tables_Config SET interval_minutes = 10, priority = 'low'
WHERE name = 'Lieu de livraison clients';
PRINT CONCAT('  Lieu de livraison clients: ', @@ROWCOUNT);

UPDATE ETL_Tables_Config SET interval_minutes = 10, priority = 'low'
WHERE name = 'Plan reporting';
PRINT CONCAT('  Plan reporting: ', @@ROWCOUNT);

UPDATE ETL_Tables_Config SET interval_minutes = 10, priority = 'low'
WHERE name = 'Plan comptable';
PRINT CONCAT('  Plan comptable: ', @@ROWCOUNT);

UPDATE ETL_Tables_Config SET interval_minutes = 10, priority = 'low'
WHERE name = 'Ecritures Analytiques';
PRINT CONCAT('  Ecritures Analytiques: ', @@ROWCOUNT);

UPDATE ETL_Tables_Config SET interval_minutes = 10, priority = 'low'
WHERE name = 'Conditions de paiement';
PRINT CONCAT('  Conditions de paiement: ', @@ROWCOUNT);

-- ============================================================
-- AUSSI METTRE A JOUR APP_ETL_Agent_Tables (si non vide)
-- ============================================================
IF EXISTS (SELECT 1 FROM APP_ETL_Agent_Tables)
BEGIN
    PRINT '';
    PRINT '=== Mise a jour APP_ETL_Agent_Tables ===';

    -- Critiques
    UPDATE APP_ETL_Agent_Tables SET interval_minutes = 1, priority = 'high'
    WHERE table_name LIKE '%tes des ventes' OR table_name LIKE '%glements clients'
       OR table_name = 'Lignes des ventes' OR table_name LIKE '%ances ventes'
       OR table_name LIKE '%tes des achats' OR table_name LIKE '%glements fournisseurs'
       OR table_name = 'Lignes des achats' OR table_name LIKE '%ances achats';
    PRINT CONCAT('  Critiques: ', @@ROWCOUNT);

    -- Moyennes
    UPDATE APP_ETL_Agent_Tables SET interval_minutes = 3, priority = 'normal'
    WHERE table_name = 'Liste des articles' OR table_name LIKE 'Imputation%factures des ventes'
       OR table_name = 'Liste des fournisseurs' OR table_name = 'Imputation factures des achats'
       OR table_name LIKE 'Ent%te des documents interne' OR table_name = 'Ligne des documents internes'
       OR table_name = 'Etat du stock' OR table_name = 'Mouvement stock'
       OR table_name LIKE 'Les %critures comptables';
    PRINT CONCAT('  Moyennes: ', @@ROWCOUNT);

    -- Stables
    UPDATE APP_ETL_Agent_Tables SET interval_minutes = 10, priority = 'low'
    WHERE table_name = 'Collaborateurs' OR table_name = 'Informations libres'
       OR table_name = 'Liste des clients' OR table_name = 'Lieu de livraison clients'
       OR table_name = 'Plan reporting' OR table_name = 'Plan comptable'
       OR table_name = 'Ecritures Analytiques' OR table_name = 'Conditions de paiement';
    PRINT CONCAT('  Stables: ', @@ROWCOUNT);
END
ELSE
    PRINT '(APP_ETL_Agent_Tables est vide, pas de mise a jour)';

-- ============================================================
-- VERIFICATION FINALE
-- ============================================================
PRINT '';
PRINT '=== Verification ETL_Tables_Config ===';

SELECT
    name AS table_name,
    priority,
    interval_minutes,
    CASE
        WHEN interval_minutes = 1 THEN 'CRITIQUE (1 min)'
        WHEN interval_minutes = 3 THEN 'MOYEN (3 min)'
        WHEN interval_minutes = 10 THEN 'STABLE (10 min)'
        ELSE 'CUSTOM (' + CAST(interval_minutes AS VARCHAR) + ' min)'
    END AS categorie
FROM ETL_Tables_Config
WHERE enabled = 1
ORDER BY interval_minutes, name;

PRINT '';
PRINT 'Termine. Redemarrer SageETLAgent pour appliquer.';
