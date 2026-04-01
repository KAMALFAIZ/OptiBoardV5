-- ============================================================
-- Script de correction des caracteres speciaux
-- Execute ce script dans la base OptiBoard_SaaS
-- ============================================================

-- Correction des noms avec accents
UPDATE ETL_Tables_Config SET name = N'Entetes des ventes', target_table = N'Entete_des_ventes' WHERE sort_order = 7;
UPDATE ETL_Tables_Config SET name = N'Reglements clients', target_table = N'Reglements_Clients' WHERE sort_order = 8;
UPDATE ETL_Tables_Config SET name = N'Echeances ventes', target_table = N'Echeances_Ventes' WHERE sort_order = 12;
UPDATE ETL_Tables_Config SET name = N'Entetes des achats', target_table = N'Entete_des_achats' WHERE sort_order = 15;
UPDATE ETL_Tables_Config SET name = N'Reglements fournisseurs' WHERE sort_order = 16;
UPDATE ETL_Tables_Config SET name = N'Echeances achats' WHERE sort_order = 19;
UPDATE ETL_Tables_Config SET name = N'Entete des documents interne', target_table = N'Entete_des_documents_internes' WHERE sort_order = 21;
UPDATE ETL_Tables_Config SET name = N'Les ecritures comptables' WHERE sort_order = 29;
UPDATE ETL_Tables_Config SET name = N'Decaissement (MP)' WHERE sort_order = 34;
UPDATE ETL_Tables_Config SET name = N'Detail paie' WHERE sort_order = 38;
UPDATE ETL_Tables_Config SET name = N'Historique conge', target_table = N'RH_Conge_Histo' WHERE sort_order = 39;

PRINT 'Caracteres speciaux corriges';

-- Afficher le resultat
SELECT
    sort_order AS [Ordre],
    name AS [Nom],
    target_table AS [Table cible],
    sync_type AS [Type sync],
    priority AS [Priorite]
FROM ETL_Tables_Config
ORDER BY sort_order;
GO
