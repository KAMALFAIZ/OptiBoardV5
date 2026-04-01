-- =====================================================
-- Script pour ajouter la colonne societe_db dans APP_DWH
-- Cette colonne stocke le nom de la societe tel qu'il apparait
-- dans les donnees (colonne DB_Caption / societe dans les tables)
-- Separe du nom d'affichage (nom) utilise dans l'interface
-- =====================================================

USE OptiBoard_SaaS;
GO

-- =====================================================
-- PARTIE 1: Modifier APP_DWH
-- =====================================================

-- Verifier si la colonne existe deja dans APP_DWH
IF NOT EXISTS (
    SELECT * FROM sys.columns
    WHERE object_id = OBJECT_ID('APP_DWH')
    AND name = 'societe_db'
)
BEGIN
    -- Ajouter la colonne societe_db
    ALTER TABLE APP_DWH
    ADD societe_db NVARCHAR(100) NULL;

    PRINT 'Colonne societe_db ajoutee a APP_DWH';
END
ELSE
BEGIN
    PRINT 'Colonne societe_db existe deja dans APP_DWH';
END
GO

-- =====================================================
-- PARTIE 2: Mettre a jour les valeurs
-- =====================================================

-- IMPORTANT: Executez cette mise a jour avec VOS valeurs reelles
-- Exemple pour ESSAIDI:
-- UPDATE APP_DWH
-- SET societe_db = 'ESSAIDI2022'   -- Valeur dans DB_Caption/societe des donnees
-- WHERE nom = 'ESSAIDI';           -- Nom d'affichage

-- Afficher les DWH actuels pour reference
SELECT
    code,
    nom AS [Nom Affichage],
    base_donnees AS [Base DWH],
    societe_db AS [Societe dans Donnees (a remplir)]
FROM APP_DWH
WHERE actif = 1;

PRINT '';
PRINT '=====================================================';
PRINT ' IMPORTANT: Mettez a jour societe_db pour chaque DWH';
PRINT '';
PRINT ' Cette valeur doit correspondre a la colonne [societe]';
PRINT ' ou [DB_Caption] dans vos tables de donnees.';
PRINT '';
PRINT ' Exemple:';
PRINT '   UPDATE APP_DWH';
PRINT '   SET societe_db = ''ESSAIDI2022''';
PRINT '   WHERE nom = ''ESSAIDI'';';
PRINT '';
PRINT ' Verifiez avec:';
PRINT '   SELECT DISTINCT societe FROM Lignes_des_ventes';
PRINT '=====================================================';
GO
