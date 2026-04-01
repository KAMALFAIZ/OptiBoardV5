-- ============================================================
-- Script d'insertion des configurations ETL depuis SyncQuery
-- Execute ce script dans la base OptiBoard_SaaS
-- ============================================================

-- 1. Ajouter la colonne sort_order si elle n'existe pas
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('ETL_Tables_Config') AND name = 'sort_order')
BEGIN
    ALTER TABLE ETL_Tables_Config ADD sort_order INT DEFAULT 0;
    PRINT 'Colonne sort_order ajoutee';
END
GO

-- 2. Vider la table existante pour reimporter
DELETE FROM ETL_Tables_Config;
PRINT 'Table ETL_Tables_Config videe';
GO

-- 3. Insertion des donnees
SET IDENTITY_INSERT ETL_Tables_Config OFF;

-- Collaborateurs (Order: 1)
INSERT INTO ETL_Tables_Config (name, source_query, target_table, primary_key, sync_type, timestamp_column, priority, batch_size, sort_order, enabled)
VALUES (N'Collaborateurs', N'SELECT * FROM (SELECT ISNULL(CO_No, ''0'') [Code collaborateur], CO_Nom [Nom collaborateur], CO_Prenom [Prénom collaborateur], CO_Fonction [Fonction collaborateur], CO_Adresse + ISNULL(CO_Complement, '''') [Adresse collaborateur], CO_CodePostal [CP collaborateur], CO_Ville [Ville collaborateur], CO_CodeRegion [Région collaborateur], CO_Pays [Pays collaborateur], CO_Service [Service collaborateur], CASE WHEN CO_Vendeur = 1 THEN ''Oui'' ELSE ''Non'' END Vendeur, CASE WHEN CO_Caissier = 1 THEN ''Oui'' ELSE ''Non'' END Caissier, CASE WHEN CO_Acheteur = 1 THEN ''Oui'' ELSE ''Non'' END Acheteur, CO_Telephone [Tél collaborateur], CO_Telecopie [Fax collaborateur], CO_EMail [Email collaborateur], CO_TelPortable [GSM collaborateur], CASE WHEN CO_ChargeRecouvr = 1 THEN ''Oui'' ELSE ''Non'' END [Charge Recouvr], CASE WHEN CO_Financier = 1 THEN ''Oui'' ELSE ''Non'' END Financier, CO_Facebook [FaceBook collaborateur], CO_LinkedIn [LinkdIn collaborateur], CO_Skype [Skyp collaborateur] FROM F_COLLABORATEUR UNION ALL SELECT ''0'', '''' [Nom collaborateur], '''' [Prénom collaborateur], '''' [Fonction collaborateur], '''' [Adresse collaborateur], '''' [CP collaborateur], '''' [Ville collaborateur], '''' [Région collaborateur], '''' [Pays collaborateur], '''' [Service collaborateur], '''' Vendeur, '''' Caissier, '''' Acheteur, '''' [Tél collaborateur], '''' [Fax collaborateur], '''' [Email collaborateur], '''' [GSM collaborateur], '''' [Charge Recouvr], '''' Financier, '''' [FaceBook collaborateur], '''' [LinkdIn collaborateur], '''' [Skyp collaborateur]) tab;',
N'Collaborateurs', N'Code collaborateur', 'full', NULL, 'high', 10000, 1, 1);

-- Informations libres (Order: 2)
INSERT INTO ETL_Tables_Config (name, source_query, target_table, primary_key, sync_type, timestamp_column, priority, batch_size, sort_order, enabled)
VALUES (N'Informations libres', N'SELECT [CB_File], [CB_Name] FROM [cbSysLibre];',
N'Info_Libres', NULL, 'full', NULL, 'high', 10000, 2, 1);

-- Liste des articles (Order: 3)
INSERT INTO ETL_Tables_Config (name, source_query, target_table, primary_key, sync_type, timestamp_column, priority, batch_size, sort_order, enabled)
VALUES (N'Liste des articles', N'SELECT F_ARTICLE.cbMarq AS [Code interne], CASE F_ARTICLE.AR_Type WHEN 0 THEN ''Standard'' WHEN 1 THEN ''Gamme'' WHEN 2 THEN ''Ressource Prestation'' WHEN 3 THEN ''Ressource Location'' END AS [Type Article], F_ARTICLE.AR_Ref AS [Code Article], F_ARTICLE.AR_Design AS [Désignation Article], F_ARTICLE.FA_CodeFamille AS [Code Famille], F_FAMILLE.FA_Intitule AS [Intitulé famille], F_FAMILLE_1.FA_Intitule AS [Intitulé Famille Centralisatrice], P_GAMME.G_Intitule AS [Libellé Gamme 1], P_GAMME_1.G_Intitule AS [Libellé Gamme 2], F_CATALOGUE.CL_Intitule AS [Catalogue 1], F_CATALOGUE_1.CL_Intitule AS [Catalogue 2], F_CATALOGUE_2.CL_Intitule AS [Catalogue 3], F_CATALOGUE_3.CL_Intitule AS [Catalogue 4], ISNULL(P_CONDITIONNEMENT.P_Conditionnement, ''Aucun'') AS Conditionnement, P_UNITE.U_Intitule AS [Unité Vente], F_ARTICLE.AR_PrixAch AS [Prix d''achat], F_ARTICLE.AR_PUNet AS [Dernier prix d''achat], F_ARTICLE.AR_Coef AS Coefficient, F_ARTICLE.AR_PrixVen AS [Prix de vente], CASE F_ARTICLE.AR_SuiviStock WHEN 0 THEN ''Aucun'' WHEN 1 THEN ''Sérialisé'' WHEN 2 THEN ''CMUP'' WHEN 3 THEN ''FIFO'' WHEN 4 THEN ''LIFO'' WHEN 5 THEN ''Par lot'' END AS [Suivi Stock], F_ARTICLE.AR_PoidsNet AS [Poids Net], F_ARTICLE.AR_PoidsBrut AS [Poids Brut], CASE F_ARTICLE.AR_Sommeil WHEN 0 THEN ''Actif'' WHEN 1 THEN ''En sommeil'' END AS [Actif / Sommeil], F_ARTICLE.AR_CodeBarre AS [Code Barres], F_ARTICLE.cbCreation [Date création], F_ARTICLE.cbModification [Date modification] FROM P_CONDITIONNEMENT RIGHT OUTER JOIN P_UNITE RIGHT OUTER JOIN F_CATALOGUE RIGHT OUTER JOIN F_ARTICLE LEFT OUTER JOIN F_FAMILLE AS F_FAMILLE_1 RIGHT OUTER JOIN F_FAMILLE ON F_FAMILLE_1.FA_CodeFamille = F_FAMILLE.FA_Central ON F_ARTICLE.FA_CodeFamille = F_FAMILLE.FA_CodeFamille LEFT OUTER JOIN F_CATALOGUE AS F_CATALOGUE_3 ON F_ARTICLE.CL_No4 = F_CATALOGUE_3.CL_No LEFT OUTER JOIN F_CATALOGUE AS F_CATALOGUE_2 ON F_ARTICLE.CL_No3 = F_CATALOGUE_2.CL_No LEFT OUTER JOIN F_CATALOGUE AS F_CATALOGUE_1 ON F_ARTICLE.CL_No2 = F_CATALOGUE_1.CL_No ON F_CATALOGUE.CL_No = F_ARTICLE.CL_No1 ON P_UNITE.cbIndice = F_ARTICLE.AR_UniteVen ON P_CONDITIONNEMENT.cbIndice = F_ARTICLE.AR_Condition LEFT OUTER JOIN P_GAMME AS P_GAMME_1 ON F_ARTICLE.AR_Gamme2 = P_GAMME_1.cbIndice LEFT OUTER JOIN P_GAMME ON F_ARTICLE.AR_Gamme1 = P_GAMME.cbIndice;',
N'Articles', N'Code Article', 'incremental', N'Date modification', 'high', 10000, 3, 1);

-- Liste des clients (Order: 5)
INSERT INTO ETL_Tables_Config (name, source_query, target_table, primary_key, sync_type, timestamp_column, priority, batch_size, sort_order, enabled)
VALUES (N'Liste des clients', N'SELECT F_COMPTET.CT_Qualite AS Qualité, F_COMPTET.CT_Num AS [Code client], F_COMPTET.CT_Intitule AS [Intitulé], F_COMPTET.CT_Classement AS [Classement], case when F_COMPTET.CO_No =0 then null else F_COMPTET.CO_No end AS [Code représentant], CO_Nom+'' ''+CO_Prenom AS [Représentant], F_COMPTET.CT_NumPayeur AS [Code payeur], F_COMPTET_1.CT_Intitule AS [Tiers payeur], ISNULL(P_DEVISE.D_Intitule, ''Aucune'') AS [Devise], P_CATTARIF.CT_Intitule AS [Catégorie tarifaire], ISNULL(F_DEPOT.DE_Intitule, ''Dépôt principal'') AS [Dépôt de rattachement], CASE F_COMPTET.CT_Sommeil WHEN 0 THEN ''Actif'' WHEN 1 THEN ''En sommeil'' END AS [En sommeil], F_COMPTET.CG_NumPrinc AS [Compte comptable], F_COMPTET.CT_Contact AS [Contact], F_COMPTET.CT_Adresse AS [Adresse], F_COMPTET.CT_Complement AS [Complément], F_COMPTET.CT_CodePostal AS [Code postal], F_COMPTET.CT_Ville AS Ville, F_COMPTET.CT_CodeRegion AS [Région], F_COMPTET.CT_Pays AS [Pays], F_COMPTET.CT_Telephone AS Téléphone, F_COMPTET.CT_EMail AS Email, F_COMPTET.cbCreation [Date de création], F_COMPTET.cbModification [Date de modification] FROM F_COMPTET LEFT OUTER JOIN F_COMPTET AS F_COMPTET_1 ON F_COMPTET.CT_NumPayeur = F_COMPTET_1.CT_Num LEFT OUTER JOIN P_CRISQUE ON F_COMPTET.N_Risque = P_CRISQUE.cbIndice LEFT OUTER JOIN F_COLLABORATEUR ON F_COMPTET.CO_No = F_COLLABORATEUR.CO_No LEFT OUTER JOIN F_DEPOT ON F_COMPTET.DE_No = F_DEPOT.DE_No LEFT OUTER JOIN P_DEVISE ON F_COMPTET.N_Devise = P_DEVISE.cbIndice LEFT OUTER JOIN P_CATTARIF ON F_COMPTET.N_CatTarif = P_CATTARIF.cbIndice WHERE (F_COMPTET.CT_Type = 0);',
N'Clients', N'Code client', 'incremental', N'Date de modification', 'high', 10000, 5, 1);

-- Lieu de livraison clients (Order: 6)
INSERT INTO ETL_Tables_Config (name, source_query, target_table, primary_key, sync_type, timestamp_column, priority, batch_size, sort_order, enabled)
VALUES (N'Lieu de livraison clients', N'SELECT F_LIVRAISON.LI_No [N° interne], F_LIVRAISON.CT_Num AS [Code client], F_LIVRAISON.LI_Intitule AS [Intitule livraison], ISNULL(F_LIVRAISON.LI_Adresse, '''') + ISNULL(F_LIVRAISON.LI_Complement, '''') AS Adresse, F_LIVRAISON.LI_CodePostal AS [Code postal], F_LIVRAISON.LI_Ville AS Ville, F_LIVRAISON.LI_CodeRegion AS Région, F_LIVRAISON.LI_Pays AS Pays, F_LIVRAISON.LI_Contact AS Contact, CASE WHEN LI_Principal = 1 THEN ''Oui'' ELSE ''Non'' END AS [Dépôt principal], F_LIVRAISON.LI_Telephone AS Téléphone, F_LIVRAISON.LI_Telecopie AS Fax, F_LIVRAISON.LI_EMail AS Email, P_EXPEDITION.E_Intitule AS Expédition, P_CONDLIVR.C_Intitule [Condition de livraison] FROM F_LIVRAISON INNER JOIN P_EXPEDITION ON F_LIVRAISON.N_Expedition = P_EXPEDITION.cbIndice INNER JOIN P_CONDLIVR ON F_LIVRAISON.N_Condition = P_CONDLIVR.cbIndice',
N'Lieu_Livraison_Client', N'N° interne', 'full', NULL, 'normal', 10000, 6, 1);

-- Entêtes des ventes (Order: 7)
INSERT INTO ETL_Tables_Config (name, source_query, target_table, primary_key, sync_type, timestamp_column, priority, batch_size, sort_order, enabled)
VALUES (N'Entêtes des ventes', N'-- Query trop longue, voir SyncQuery source',
N'Entête_des_ventes', N'Type Document,N° Pièce', 'incremental', N'Date modification', 'high', 10000, 7, 1);

-- Règlements clients (Order: 8)
INSERT INTO ETL_Tables_Config (name, source_query, target_table, primary_key, sync_type, timestamp_column, priority, batch_size, sort_order, enabled)
VALUES (N'Règlements clients', N'SELECT ISNULL(F_CREGLEMENT.CT_NumPayeur, '''') AS [Code client], F_COMPTET_1.CT_Intitule AS Intitulé, F_CREGLEMENT.CT_NumPayeurOrig AS [Code client original], F_COMPTET.CT_Intitule AS [Intitulé original], F_CREGLEMENT.RG_Date AS Date, F_CREGLEMENT.RG_DateEchCont AS [Date d''échéance], F_CREGLEMENT.RG_Reference AS Référence, F_CREGLEMENT.RG_Libelle AS Libellé, CASE WHEN F_CREGLEMENT.RG_Impute = 0 THEN ''Non'' ELSE ''Oui'' END AS Impute, CASE WHEN F_CREGLEMENT.RG_Compta = 0 THEN ''Non'' ELSE ''Oui'' END AS Comptabilisé, F_CREGLEMENT.JO_Num AS [Code journal], F_JOURNAUX.JO_Intitule AS Journal, F_CREGLEMENT.CG_Num AS [Compte générale], F_CREGLEMENT.RG_Piece AS [N° piéce], CASE WHEN F_CREGLEMENT.RG_Valide = 0 THEN ''Non'' ELSE ''Oui'' END AS Valide, P_REGLEMENT.R_Intitule AS [Mode de règlement], ISNULL(P_DEVISE.D_Intitule, ''Aucune'') AS Devise, F_CREGLEMENT.RG_MontantDev AS [Montant en devise], F_CREGLEMENT.RG_Cours AS Cours, F_CREGLEMENT.RG_Montant AS Montant, ISNULL(RG_No, '''') [N° interne], F_CREGLEMENT.RG_Montant-isnull((select sum(RC_Montant) from F_REGLECH where F_REGLECH.rg_no=F_CREGLEMENT.RG_No),0) solde, r_code [Code règlement], F_CREGLEMENT.cbCreation [Date création], F_CREGLEMENT.cbModification [Date modification] FROM F_CREGLEMENT INNER JOIN F_COMPTET AS F_COMPTET_1 ON F_CREGLEMENT.CT_NumPayeur = F_COMPTET_1.CT_Num INNER JOIN F_COMPTET ON F_CREGLEMENT.CT_NumPayeurOrig = F_COMPTET.CT_Num INNER JOIN F_JOURNAUX ON F_CREGLEMENT.JO_Num = F_JOURNAUX.JO_Num LEFT OUTER JOIN P_REGLEMENT ON F_CREGLEMENT.N_Reglement = P_REGLEMENT.cbIndice LEFT OUTER JOIN P_DEVISE ON F_CREGLEMENT.N_Devise = P_DEVISE.cbIndice WHERE (F_CREGLEMENT.RG_Type = 0);',
N'Règlements_Clients', N'N° interne', 'incremental', N'Date modification', 'normal', 10000, 8, 1);

-- Imputation les factures des ventes (Order: 9)
INSERT INTO ETL_Tables_Config (name, source_query, target_table, primary_key, sync_type, timestamp_column, priority, batch_size, sort_order, enabled)
VALUES (N'Imputation les factures des ventes', N'-- Query complexe, voir SyncQuery source',
N'Imputation_Factures_Ventes', NULL, 'incremental', N'Date modification', 'normal', 10000, 9, 1);

-- Lignes des ventes (Order: 10)
INSERT INTO ETL_Tables_Config (name, source_query, target_table, primary_key, sync_type, timestamp_column, priority, batch_size, sort_order, enabled)
VALUES (N'Lignes des ventes', N'-- Query trop longue, voir SyncQuery source',
N'Lignes_des_ventes', NULL, 'incremental', N'Date modification', 'high', 10000, 10, 1);

-- Imputation BLs (Order: 11)
INSERT INTO ETL_Tables_Config (name, source_query, target_table, primary_key, sync_type, timestamp_column, priority, batch_size, sort_order, enabled)
VALUES (N'Imputation BLs', N'-- Query complexe, voir SyncQuery source',
N'Imputation_BL', NULL, 'full', NULL, 'normal', 10000, 11, 1);

-- Echéances ventes (Order: 12)
INSERT INTO ETL_Tables_Config (name, source_query, target_table, primary_key, sync_type, timestamp_column, priority, batch_size, sort_order, enabled)
VALUES (N'Echéances ventes', N'-- Query avec CTE, voir SyncQuery source',
N'Echéances_Ventes', NULL, 'full', NULL, 'normal', 10000, 12, 1);

-- Liste des fournisseurs (Order: 14)
INSERT INTO ETL_Tables_Config (name, source_query, target_table, primary_key, sync_type, timestamp_column, priority, batch_size, sort_order, enabled)
VALUES (N'Liste des fournisseurs', N'SELECT F_COMPTET.CT_Qualite AS Qualité, F_COMPTET.CT_Num AS [Code fournisseur], F_COMPTET.CT_Intitule AS [Intitulé], F_COMPTET.CT_Classement AS [Classement], F_COMPTET.CO_No AS [Code acheteur], F_COLLABORATEUR.CO_Nom+'' ''+CO_Prenom AS Acheteur, F_COMPTET.CT_NumPayeur AS [Code encaisseur], F_COMPTET_1.CT_Intitule AS [Tiers encaisseur], ISNULL(P_DEVISE.D_Intitule, ''Aucune'') AS [Devise], P_CATTARIF.CT_Intitule AS [Catégorie tarifaire], ISNULL(F_DEPOT.DE_Intitule, ''Dépôt principal'') AS [Dépôt], CASE F_COMPTET.CT_Sommeil WHEN 0 THEN ''Actif'' WHEN 1 THEN ''En sommeil'' END AS [En sommeil], F_COMPTET.CG_NumPrinc AS [Compte comptable], F_COMPTET.CT_Contact AS [Contact], F_COMPTET.CT_Adresse AS [Adresse], F_COMPTET.CT_CodePostal AS [Code postal], F_COMPTET.CT_Ville AS Ville, F_COMPTET.CT_Telephone AS Téléphone, F_COMPTET.CT_EMail AS Email, F_COMPTET.cbCreation [Date de création], F_COMPTET.cbModification [Date modification] FROM F_COMPTET INNER JOIN F_COMPTET F_COMPTET_1 ON F_COMPTET.CT_NumPayeur = F_COMPTET_1.CT_Num LEFT OUTER JOIN P_CRISQUE ON F_COMPTET.N_Risque = P_CRISQUE.cbIndice LEFT OUTER JOIN F_COLLABORATEUR ON F_COMPTET.CO_No = F_COLLABORATEUR.CO_No LEFT OUTER JOIN F_DEPOT ON F_COMPTET.DE_No = F_DEPOT.DE_No LEFT OUTER JOIN P_DEVISE ON F_COMPTET.N_Devise = P_DEVISE.cbIndice LEFT OUTER JOIN P_CATTARIF ON F_COMPTET.N_CatTarif = P_CATTARIF.cbIndice WHERE (F_COMPTET.CT_Type = 1);',
N'Fournisseurs', N'Code fournisseur', 'incremental', N'Date modification', 'normal', 10000, 14, 1);

-- Entêtes des achats (Order: 15)
INSERT INTO ETL_Tables_Config (name, source_query, target_table, primary_key, sync_type, timestamp_column, priority, batch_size, sort_order, enabled)
VALUES (N'Entêtes des achats', N'-- Query trop longue, voir SyncQuery source',
N'Entête_des_achats', N'Type Document,N° Pièce', 'incremental', N'Date modification', 'normal', 10000, 15, 1);

-- Réglements fournisseurs (Order: 16)
INSERT INTO ETL_Tables_Config (name, source_query, target_table, primary_key, sync_type, timestamp_column, priority, batch_size, sort_order, enabled)
VALUES (N'Réglements fournisseurs', N'SELECT ISNULL(F_CREGLEMENT.CT_NumPayeur, '''') AS [Code fournisseur], F_COMPTET_1.CT_Intitule AS Intitulé, F_CREGLEMENT.RG_Date AS Date, F_CREGLEMENT.RG_DateEchCont AS [Date d''échéance], F_CREGLEMENT.RG_Reference AS Référence, F_CREGLEMENT.RG_Libelle AS Libellé, CASE WHEN F_CREGLEMENT.RG_Impute = 0 THEN ''Non'' ELSE ''Oui'' END AS Impute, CASE WHEN F_CREGLEMENT.RG_Compta = 0 THEN ''Non'' ELSE ''Oui'' END AS Comptabilisé, F_CREGLEMENT.JO_Num AS [Code journal], F_JOURNAUX.JO_Intitule AS Journal, F_CREGLEMENT.CG_Num AS [Compte générale], F_CREGLEMENT.RG_Piece AS [N° piéce], P_REGLEMENT.R_Intitule AS [Mode réglement], ISNULL(P_DEVISE.D_Intitule, ''Aucune'') AS Devise, F_CREGLEMENT.RG_MontantDev AS [Montant en devise], F_CREGLEMENT.RG_Cours AS Cours, F_CREGLEMENT.RG_Montant AS Montant, ISNULL(RG_No, '''') [N° interne], F_CREGLEMENT.RG_Montant-isnull((select sum(RC_Montant) from F_REGLECH where F_REGLECH.rg_no=F_CREGLEMENT.RG_No),0) solde, r_code [Code réglement], F_CREGLEMENT.cbCreation [Date création], F_CREGLEMENT.cbModification [Date modification] FROM F_CREGLEMENT INNER JOIN F_COMPTET AS F_COMPTET_1 ON F_CREGLEMENT.CT_NumPayeur = F_COMPTET_1.CT_Num INNER JOIN F_COMPTET ON F_CREGLEMENT.CT_NumPayeurOrig = F_COMPTET.CT_Num INNER JOIN F_JOURNAUX ON F_CREGLEMENT.JO_Num = F_JOURNAUX.JO_Num LEFT OUTER JOIN P_REGLEMENT ON F_CREGLEMENT.N_Reglement = P_REGLEMENT.cbIndice LEFT OUTER JOIN P_DEVISE ON F_CREGLEMENT.N_Devise = P_DEVISE.cbIndice WHERE (F_CREGLEMENT.RG_Type = 1);',
N'Paiements_Fournisseurs', N'N° interne', 'incremental', N'Date modification', 'normal', 10000, 16, 1);

-- Imputation factures des achats (Order: 17)
INSERT INTO ETL_Tables_Config (name, source_query, target_table, primary_key, sync_type, timestamp_column, priority, batch_size, sort_order, enabled)
VALUES (N'Imputation factures des achats', N'-- Query complexe, voir SyncQuery source',
N'Imputation_Factures_Achats', NULL, 'incremental', N'Date modification', 'normal', 10000, 17, 1);

-- Lignes des achats (Order: 18)
INSERT INTO ETL_Tables_Config (name, source_query, target_table, primary_key, sync_type, timestamp_column, priority, batch_size, sort_order, enabled)
VALUES (N'Lignes des achats', N'-- Query trop longue, voir SyncQuery source',
N'Lignes_des_achats', NULL, 'incremental', N'Date modification', 'normal', 10000, 18, 1);

-- Echéances achats (Order: 19)
INSERT INTO ETL_Tables_Config (name, source_query, target_table, primary_key, sync_type, timestamp_column, priority, batch_size, sort_order, enabled)
VALUES (N'Echéances achats', N'-- Query complexe, voir SyncQuery source',
N'Echeances_Achats', NULL, 'incremental', N'Date modification', 'normal', 10000, 19, 1);

-- Entête des documents interne (Order: 21)
INSERT INTO ETL_Tables_Config (name, source_query, target_table, primary_key, sync_type, timestamp_column, priority, batch_size, sort_order, enabled)
VALUES (N'Entête des documents interne', N'-- Query longue, voir SyncQuery source',
N'Entête_des_documents_internes', N'Type Document,N° Pièce', 'full', NULL, 'normal', 10000, 21, 1);

-- Ligne des documents internes (Order: 22)
INSERT INTO ETL_Tables_Config (name, source_query, target_table, primary_key, sync_type, timestamp_column, priority, batch_size, sort_order, enabled)
VALUES (N'Ligne des documents internes', N'-- Query longue, voir SyncQuery source',
N'Ligne_des_documents_interne', NULL, 'full', NULL, 'normal', 10000, 22, 1);

-- Etat du stock (Order: 24)
INSERT INTO ETL_Tables_Config (name, source_query, target_table, primary_key, sync_type, timestamp_column, priority, batch_size, sort_order, enabled)
VALUES (N'Etat du stock', N'SELECT F_ARTSTOCK.AR_Ref AS [Code article], F_ARTSTOCK.DE_No AS [Code dépôt], F_ARTSTOCK.AS_QteMini AS [Quantité minimale], F_ARTSTOCK.AS_QteMaxi AS [Quantité maximale], F_ARTSTOCK.AS_MontSto AS [Valeur du stock (montant)], F_ARTSTOCK.AS_QteSto AS [Quantité en stock], F_ARTSTOCK.AS_QteRes AS [Quntitté réservée], F_ARTSTOCK.AS_QteCom AS [Quantité commandée], F_ARTSTOCK.AS_Principal AS [Dépôt principale], F_ARTSTOCK.cbMarq AS [N° intene], CASE WHEN AS_Mouvemente = 0 THEN ''Non'' ELSE ''Oui'' END AS [Stock mouvementé], FART.AR_Design AS [Désignation article], F_FAMILLE.FA_CodeFamille AS [Code famille], F_FAMILLE.FA_Intitule AS Intitule, F_DEPOT.DE_Intitule, P_UNITE.U_Intitule AS Unité FROM F_FAMILLE INNER JOIN F_ARTICLE AS FART INNER JOIN F_ARTSTOCK AS F_ARTSTOCK ON FART.cbAR_Ref = F_ARTSTOCK.cbAR_Ref INNER JOIN F_DEPOT ON F_ARTSTOCK.DE_No = F_DEPOT.DE_No ON F_FAMILLE.FA_CodeFamille = FART.FA_CodeFamille INNER JOIN P_UNITE ON FART.AR_UniteVen = P_UNITE.cbIndice;',
N'Etat_Stock', NULL, 'full', NULL, 'normal', 10000, 24, 1);

-- Mouvement stock (Order: 25)
INSERT INTO ETL_Tables_Config (name, source_query, target_table, primary_key, sync_type, timestamp_column, priority, batch_size, sort_order, enabled)
VALUES (N'Mouvement stock', N'-- Query tres longue, voir SyncQuery source',
N'Mouvement_stock', NULL, 'full', NULL, 'normal', 10000, 25, 1);

-- Plan reporting (Order: 27)
INSERT INTO ETL_Tables_Config (name, source_query, target_table, primary_key, sync_type, timestamp_column, priority, batch_size, sort_order, enabled)
VALUES (N'Plan reporting', N'SELECT [CR_Num] Code, CASE WHEN [CR_Type] = 0 THEN ''Détail'' ELSE ''Total'' END [Type de compte], [CR_Intitule] Intitulé FROM [F_COMPTER]',
N'Plan_Reporting', NULL, 'full', NULL, 'normal', 10000, 27, 1);

-- Plan comptable (Order: 28)
INSERT INTO ETL_Tables_Config (name, source_query, target_table, primary_key, sync_type, timestamp_column, priority, batch_size, sort_order, enabled)
VALUES (N'Plan comptable', N'SELECT CG_Num [Numéro compte], case when CG_Type=0 then ''Détail'' else ''Total'' end [Type de compte], CG_Intitule Intitulé, CG_Classement Classement, case N_Nature when 0 then ''Aucune'' when 1 then ''Client'' when 2 then ''Fournisseur'' when 3 then ''Salarié'' when 4 then ''Banque'' when 5 then ''Caisse'' when 6 then ''Amortissement/Provision'' when 7 then ''Résultat bilan'' when 8 then ''charge'' when 9 then ''Produit'' when 10 then ''Résultat Gestion'' when 11 then ''Immobilisation'' when 12 then ''Capitaux'' when 13 then ''Stock'' when 14 then ''Titre'' end Nature, case CG_Report when 0 then ''Aucun'' when 1 then ''Solde'' when 2 then ''Détail'' end [Type report], F_COMPTEG.CR_Num [Code reporting], case when CG_Sommeil=0 then ''Actif'' else ''En sommeil'' end [Mise en sommeil], F_COMPTEG.cbCreation [Date de création], F_COMPTER.CR_Intitule [Intitulé reporting] FROM F_COMPTEG LEFT OUTER JOIN F_COMPTER ON F_COMPTEG.CR_Num = F_COMPTER.CR_Num',
N'Plan_Comptable', N'Numéro compte', 'full', NULL, 'normal', 10000, 28, 1);

-- Les écritures comptables (Order: 29)
INSERT INTO ETL_Tables_Config (name, source_query, target_table, primary_key, sync_type, timestamp_column, priority, batch_size, sort_order, enabled)
VALUES (N'Les écritures comptables', N'-- Query tres complexe, voir SyncQuery source',
N'Ecritures_Comptables', N'N° interne', 'full', NULL, 'normal', 10000, 29, 1);

-- Ecritures Analytiques (Order: 30)
INSERT INTO ETL_Tables_Config (name, source_query, target_table, primary_key, sync_type, timestamp_column, priority, batch_size, sort_order, enabled)
VALUES (N'Ecritures Analytiques', N'SELECT F_ECRITUREA.cbMarq [N° interne], F_ECRITUREA.EC_No AS [N° interne EG], F_ECRITUREA.N_Analytique, F_ECRITUREA.EA_Ligne AS Ligne, F_ECRITUREA.CA_Num AS [Compte analytique], F_ECRITUREA.EA_Montant AS [Montant analytique], F_ECRITUREA.EA_Quantite AS Quantité, P_ANALYTIQUE.A_Intitule AS Intitulé, P_ANALYSE.A_Intitule [Plan analytique] FROM F_ECRITUREA INNER JOIN F_COMPTEA ON F_ECRITUREA.N_Analytique = F_COMPTEA.N_Analytique AND F_ECRITUREA.CA_Num = F_COMPTEA.CA_Num INNER JOIN P_ANALYTIQUE ON F_COMPTEA.CA_Num = P_ANALYTIQUE.CA_Num INNER JOIN P_ANALYSE ON F_ECRITUREA.N_Analytique = P_ANALYSE.cbIndice',
N'Ecritures_Analytiques', NULL, 'full', NULL, 'normal', 10000, 30, 1);

-- Conditions de paiement (Order: 32)
INSERT INTO ETL_Tables_Config (name, source_query, target_table, primary_key, sync_type, timestamp_column, priority, batch_size, sort_order, enabled)
VALUES (N'Conditions de paiement', N'SELECT CT_Num [Code tiers], N_Reglement [Code interne réglement], CASE RT_Condition WHEN 0 THEN ''Jour(s) net(s)'' WHEN 1 THEN ''Fin mois civil'' ELSE ''Fin mois'' END [Condition], F_REGLEMENTT.RT_NbJour [Nbr jour], RT_JourTb01 [Jour mois 1], RT_JourTb02 [Jour mois 2], RT_JourTb03 [Jour mois 3], RT_JourTb04 [Jour mois 4], RT_JourTb05 [Jour mois 5], RT_JourTb06 [Jour mois 6], RT_TRepart, CASE RT_TRepart WHEN 0 THEN ''Pourcentage'' WHEN 1 THEN ''Equilibre'' ELSE ''Valeur'' END Equilibre, RT_VRepart Valeur, P_REGLEMENT.R_Intitule [Mode réglement], P_REGLEMENT.R_Code [Code réglement] FROM F_REGLEMENTT INNER JOIN P_REGLEMENT ON F_REGLEMENTT.N_Reglement = P_REGLEMENT.cbIndice',
N'Conditions_Paiement', N'N° interne', 'full', NULL, 'normal', 10000, 32, 1);

-- Encaissements (MP) (Order: 33)
INSERT INTO ETL_Tables_Config (name, source_query, target_table, primary_key, sync_type, timestamp_column, priority, batch_size, sort_order, enabled)
VALUES (N'Encaissements (MP)', N'-- Query tres longue, voir SyncQuery source',
N'Encaissement_MP', NULL, 'full', NULL, 'normal', 10000, 33, 1);

-- Décaissement (MP) (Order: 34)
INSERT INTO ETL_Tables_Config (name, source_query, target_table, primary_key, sync_type, timestamp_column, priority, batch_size, sort_order, enabled)
VALUES (N'Décaissement (MP)', N'-- Query tres longue, voir SyncQuery source',
N'Decaissement_MP', NULL, 'full', NULL, 'normal', 10000, 34, 1);

-- Historique affectations (Order: 36)
INSERT INTO ETL_Tables_Config (name, source_query, target_table, primary_key, sync_type, timestamp_column, priority, batch_size, sort_order, enabled)
VALUES (N'Historique affectations', N'-- Query avec curseurs, voir SyncQuery source',
N'RH_Affectation_Histo', NULL, 'full', NULL, 'low', 10000, 36, 1);

-- Détail paie (Order: 38)
INSERT INTO ETL_Tables_Config (name, source_query, target_table, primary_key, sync_type, timestamp_column, priority, batch_size, sort_order, enabled)
VALUES (N'Détail paie', N'-- Query tres complexe avec UNION ALL, voir SyncQuery source',
N'RH_Paie', NULL, 'full', NULL, 'low', 10000, 38, 1);

-- Historique congé (Order: 39)
INSERT INTO ETL_Tables_Config (name, source_query, target_table, primary_key, sync_type, timestamp_column, priority, batch_size, sort_order, enabled)
VALUES (N'Historique congé', N'SELECT MatriculeSalarie AS Matricule, T_HST_CONGE.DateDebutConges1 AS [Date début congé 1], T_HST_CONGE.DateFinConges1 AS [Date fin congé 1], T_HST_CONGE.DateDebut AS [Date début congé], T_HST_CONGE.DateHist AS [Date fin congé] FROM T_HST_CONGE INNER JOIN T_SAL ON T_HST_CONGE.NumSalarie = T_SAL.SA_CompteurNumero WHERE (T_HST_CONGE.InfoEnCours = 0);',
N'RH_Congé_Histo', NULL, 'full', NULL, 'low', 10000, 39, 1);

-- Historique salaire (Order: 40)
INSERT INTO ETL_Tables_Config (name, source_query, target_table, primary_key, sync_type, timestamp_column, priority, batch_size, sort_order, enabled)
VALUES (N'Historique salaire', N'-- Query tres complexe avec tables temp, voir SyncQuery source',
N'RH_Salaire_Histo', NULL, 'full', NULL, 'low', 10000, 40, 1);

-- Historique contrat travail (Order: 41)
INSERT INTO ETL_Tables_Config (name, source_query, target_table, primary_key, sync_type, timestamp_column, priority, batch_size, sort_order, enabled)
VALUES (N'Historique contrat travail', N'SELECT MatriculeSalarie AS Matricule, T_HST_CONTRAT.NoContrat AS [Numéro contrat], T_HST_CONTRAT.CodeNatureDeContrat AS [Code], (SELECT Intitule FROM T_NATUREDECONTRAT WHERE Code = T_HST_CONTRAT.CodeNatureDeContrat) [Intitulé contrat], T_HST_CONTRAT.DateDebutContrat AS [Date début contrat], T_HST_CONTRAT.DateFinContrat AS [Date fin contrat], T_HST_CONTRAT.FinPeriodeEssai AS [Fin période essai], T_HST_CONTRAT.DateDebut AS [Date Début], T_HST_CONTRAT.DateHist AS [Date fin] FROM T_HST_CONTRAT INNER JOIN T_SAL ON T_HST_CONTRAT.NumSalarie = T_SAL.SA_CompteurNumero WHERE (T_HST_CONTRAT.InfoEnCours = 0);',
N'RH_Contrat_Tra_Histo', NULL, 'full', NULL, 'low', 10000, 41, 1);

-- Historique effectifs (Order: 42)
INSERT INTO ETL_Tables_Config (name, source_query, target_table, primary_key, sync_type, timestamp_column, priority, batch_size, sort_order, enabled)
VALUES (N'Historique effectifs', N'-- Query tres complexe avec tables temp, voir SyncQuery source',
N'RH_Effectif_Histo', NULL, 'full', NULL, 'low', 10000, 42, 1);

-- Historique (Order: 43)
INSERT INTO ETL_Tables_Config (name, source_query, target_table, primary_key, sync_type, timestamp_column, priority, batch_size, sort_order, enabled)
VALUES (N'Historique', N'-- Query avec curseurs et tables temp, voir SyncQuery source',
N'RH_Historique', NULL, 'full', NULL, 'low', 10000, 43, 1);

GO

-- 4. Afficher le resultat
SELECT
    name AS [Nom],
    target_table AS [Table cible],
    sort_order AS [Ordre],
    sync_type AS [Type sync],
    timestamp_column AS [Colonne increment.],
    priority AS [Priorité],
    enabled AS [Actif]
FROM ETL_Tables_Config
ORDER BY sort_order, name;
GO

PRINT 'Import termine: ' + CAST((SELECT COUNT(*) FROM ETL_Tables_Config) AS VARCHAR) + ' tables configurees';
GO
