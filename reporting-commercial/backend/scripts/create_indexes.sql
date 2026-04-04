-- ============================================
-- Script de création d'index pour le Reporting Commercial
-- Tables: DashBoard_CA, Mouvement_stock
-- USAGE: Remplacer YOUR_DB_NAME par le nom de votre base de données
-- ============================================

-- USE [YOUR_DB_NAME]
-- GO

-- ============================================
-- INDEX PRINCIPAL sur Date BL
-- Utilisé dans presque toutes les requêtes WHERE [Date BL] BETWEEN
-- ============================================
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_DashBoard_CA_DateBL' AND object_id = OBJECT_ID('[dbo].[DashBoard_CA]'))
BEGIN
    CREATE NONCLUSTERED INDEX [IX_DashBoard_CA_DateBL]
    ON [dbo].[DashBoard_CA] ([Date BL])
    INCLUDE ([Montant HT Net], [Montant TTC Net], [Coût], [Code client], [Quantité])
    WITH (ONLINE = OFF, FILLFACTOR = 90)

    PRINT 'Index IX_DashBoard_CA_DateBL créé avec succès'
END
ELSE
    PRINT 'Index IX_DashBoard_CA_DateBL existe déjà'
GO

-- ============================================
-- INDEX pour les requêtes par Commercial
-- Utilisé dans: CA par commercial, détail commercial
-- ============================================
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_DashBoard_CA_Representant' AND object_id = OBJECT_ID('[dbo].[DashBoard_CA]'))
BEGIN
    CREATE NONCLUSTERED INDEX [IX_DashBoard_CA_Representant]
    ON [dbo].[DashBoard_CA] ([Représentant], [Date BL])
    INCLUDE ([Montant HT Net], [Code client])
    WITH (ONLINE = OFF, FILLFACTOR = 90)

    PRINT 'Index IX_DashBoard_CA_Representant créé avec succès'
END
ELSE
    PRINT 'Index IX_DashBoard_CA_Representant existe déjà'
GO

-- ============================================
-- INDEX pour les requêtes par Gamme (Catalogue 1)
-- Utilisé dans: CA par gamme, détail gamme
-- ============================================
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_DashBoard_CA_Catalogue1' AND object_id = OBJECT_ID('[dbo].[DashBoard_CA]'))
BEGIN
    CREATE NONCLUSTERED INDEX [IX_DashBoard_CA_Catalogue1]
    ON [dbo].[DashBoard_CA] ([Catalogue 1], [Date BL])
    INCLUDE ([Montant HT Net], [Coût], [Code article])
    WITH (ONLINE = OFF, FILLFACTOR = 90)

    PRINT 'Index IX_DashBoard_CA_Catalogue1 créé avec succès'
END
ELSE
    PRINT 'Index IX_DashBoard_CA_Catalogue1 existe déjà'
GO

-- ============================================
-- INDEX pour les requêtes par Client
-- Utilisé dans: Top clients, détail client
-- ============================================
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_DashBoard_CA_CodeClient' AND object_id = OBJECT_ID('[dbo].[DashBoard_CA]'))
BEGIN
    CREATE NONCLUSTERED INDEX [IX_DashBoard_CA_CodeClient]
    ON [dbo].[DashBoard_CA] ([Code client], [Date BL])
    INCLUDE ([Montant HT Net], [Intitulé client], [Représentant])
    WITH (ONLINE = OFF, FILLFACTOR = 90)

    PRINT 'Index IX_DashBoard_CA_CodeClient créé avec succès'
END
ELSE
    PRINT 'Index IX_DashBoard_CA_CodeClient existe déjà'
GO

-- ============================================
-- INDEX pour les requêtes par Article
-- Utilisé dans: Top produits, détail produit
-- ============================================
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_DashBoard_CA_CodeArticle' AND object_id = OBJECT_ID('[dbo].[DashBoard_CA]'))
BEGIN
    CREATE NONCLUSTERED INDEX [IX_DashBoard_CA_CodeArticle]
    ON [dbo].[DashBoard_CA] ([Code article], [Date BL])
    INCLUDE ([Montant HT Net], [Désignation], [Quantité], [Coût])
    WITH (ONLINE = OFF, FILLFACTOR = 90)

    PRINT 'Index IX_DashBoard_CA_CodeArticle créé avec succès'
END
ELSE
    PRINT 'Index IX_DashBoard_CA_CodeArticle existe déjà'
GO

-- ============================================
-- INDEX pour les requêtes par Canal (Catégorie)
-- Utilisé dans: CA par canal
-- ============================================
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_DashBoard_CA_Categorie' AND object_id = OBJECT_ID('[dbo].[DashBoard_CA]'))
BEGIN
    CREATE NONCLUSTERED INDEX [IX_DashBoard_CA_Categorie]
    ON [dbo].[DashBoard_CA] ([Catégorie_], [Date BL])
    INCLUDE ([Montant HT Net], [Code client])
    WITH (ONLINE = OFF, FILLFACTOR = 90)

    PRINT 'Index IX_DashBoard_CA_Categorie créé avec succès'
END
ELSE
    PRINT 'Index IX_DashBoard_CA_Categorie existe déjà'
GO

-- ============================================
-- INDEX pour les requêtes par Zone (Souche)
-- Utilisé dans: CA par zone
-- ============================================
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_DashBoard_CA_Souche' AND object_id = OBJECT_ID('[dbo].[DashBoard_CA]'))
BEGIN
    CREATE NONCLUSTERED INDEX [IX_DashBoard_CA_Souche]
    ON [dbo].[DashBoard_CA] ([Souche], [Date BL])
    INCLUDE ([Montant HT Net], [Code client])
    WITH (ONLINE = OFF, FILLFACTOR = 90)

    PRINT 'Index IX_DashBoard_CA_Souche créé avec succès'
END
ELSE
    PRINT 'Index IX_DashBoard_CA_Souche existe déjà'
GO

-- ============================================
-- Vérification des index créés
-- ============================================
SELECT
    i.name AS IndexName,
    i.type_desc AS IndexType,
    STUFF((
        SELECT ', ' + c.name
        FROM sys.index_columns ic
        JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
        WHERE ic.object_id = i.object_id AND ic.index_id = i.index_id AND ic.is_included_column = 0
        ORDER BY ic.key_ordinal
        FOR XML PATH('')
    ), 1, 2, '') AS KeyColumns,
    STUFF((
        SELECT ', ' + c.name
        FROM sys.index_columns ic
        JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
        WHERE ic.object_id = i.object_id AND ic.index_id = i.index_id AND ic.is_included_column = 1
        ORDER BY ic.key_ordinal
        FOR XML PATH('')
    ), 1, 2, '') AS IncludedColumns
FROM sys.indexes i
WHERE i.object_id = OBJECT_ID('[dbo].[DashBoard_CA]')
    AND i.name LIKE 'IX_DashBoard_CA%'
ORDER BY i.name
GO

-- ============================================
-- INDEX pour Mouvement_stock
-- ============================================

-- INDEX PRINCIPAL sur Date Mouvement
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_Mouvement_stock_DateMouvement' AND object_id = OBJECT_ID('[dbo].[Mouvement_stock]'))
BEGIN
    CREATE NONCLUSTERED INDEX [IX_Mouvement_stock_DateMouvement]
    ON [dbo].[Mouvement_stock] ([Date Mouvement])
    INCLUDE ([Code article], [Quantité], [Sens de mouvement], [CMUP], [Montant Stock])
    WITH (ONLINE = OFF, FILLFACTOR = 90)

    PRINT 'Index IX_Mouvement_stock_DateMouvement créé avec succès'
END
ELSE
    PRINT 'Index IX_Mouvement_stock_DateMouvement existe déjà'
GO

-- INDEX pour les requêtes par Article
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_Mouvement_stock_CodeArticle' AND object_id = OBJECT_ID('[dbo].[Mouvement_stock]'))
BEGIN
    CREATE NONCLUSTERED INDEX [IX_Mouvement_stock_CodeArticle]
    ON [dbo].[Mouvement_stock] ([Code article], [Date Mouvement])
    INCLUDE ([Quantité], [Sens de mouvement], [CMUP], [Désignation])
    WITH (ONLINE = OFF, FILLFACTOR = 90)

    PRINT 'Index IX_Mouvement_stock_CodeArticle créé avec succès'
END
ELSE
    PRINT 'Index IX_Mouvement_stock_CodeArticle existe déjà'
GO

-- INDEX pour les requêtes par Gamme (Catalogue 1)
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_Mouvement_stock_Catalogue1' AND object_id = OBJECT_ID('[dbo].[Mouvement_stock]'))
BEGIN
    CREATE NONCLUSTERED INDEX [IX_Mouvement_stock_Catalogue1]
    ON [dbo].[Mouvement_stock] ([Catalogue 1], [Date Mouvement])
    INCLUDE ([Code article], [Quantité], [Sens de mouvement], [CMUP])
    WITH (ONLINE = OFF, FILLFACTOR = 90)

    PRINT 'Index IX_Mouvement_stock_Catalogue1 créé avec succès'
END
ELSE
    PRINT 'Index IX_Mouvement_stock_Catalogue1 existe déjà'
GO

-- INDEX pour les requêtes par Sens de mouvement (E/S)
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_Mouvement_stock_SensMouvement' AND object_id = OBJECT_ID('[dbo].[Mouvement_stock]'))
BEGIN
    CREATE NONCLUSTERED INDEX [IX_Mouvement_stock_SensMouvement]
    ON [dbo].[Mouvement_stock] ([Sens de mouvement], [Date Mouvement])
    INCLUDE ([Code article], [Quantité], [CMUP])
    WITH (ONLINE = OFF, FILLFACTOR = 90)

    PRINT 'Index IX_Mouvement_stock_SensMouvement créé avec succès'
END
ELSE
    PRINT 'Index IX_Mouvement_stock_SensMouvement existe déjà'
GO

-- ============================================
-- Vérification des index Mouvement_stock
-- ============================================
SELECT
    i.name AS IndexName,
    i.type_desc AS IndexType,
    STUFF((
        SELECT ', ' + c.name
        FROM sys.index_columns ic
        JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
        WHERE ic.object_id = i.object_id AND ic.index_id = i.index_id AND ic.is_included_column = 0
        ORDER BY ic.key_ordinal
        FOR XML PATH('')
    ), 1, 2, '') AS KeyColumns
FROM sys.indexes i
WHERE i.object_id = OBJECT_ID('[dbo].[Mouvement_stock]')
    AND i.name LIKE 'IX_Mouvement_stock%'
ORDER BY i.name
GO

PRINT ''
PRINT '============================================'
PRINT 'Script terminé - Index créés'
PRINT '  - DashBoard_CA: 4 index'
PRINT '  - Mouvement_stock: 4 index'
PRINT '============================================'
GO
