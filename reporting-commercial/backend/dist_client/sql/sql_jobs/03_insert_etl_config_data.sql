-- =====================================================================
-- 03_insert_etl_config_data.sql
-- Insertion des 35 configurations de tables + exemples de sources
-- Architecture 3 bases : OptiBoard_xxxx + DWH_yyyy + Sage 1..N
-- =====================================================================
-- PARTIE A : ETL_Tables_Config    -> dans {OPTIBOARD_DB} (config centrale)
-- PARTIE B : ETL_Sources exemples -> dans {DWH_NAME}
-- =====================================================================
-- VARIABLES A REMPLACER :
--   {OPTIBOARD_DB}  -> nom de votre base OptiBoard (ex: OptiBoard_SaaS)
--   {DWH_NAME}      -> nom de votre base DWH (ex: DWH_Alboughaze)
-- =====================================================================
-- NOTE : Les requetes source completes sont dans :
--   - backend/sql/insert_sync_query_data.sql  (queries disponibles)
--   - backend/etl/config/sync_tables.yaml     (queries completes)
-- Pour les queries marquees 'TODO', copiez depuis sync_tables.yaml
-- =====================================================================

SET NOCOUNT ON;
GO

-- ═══════════════════════════════════════════════════════════════
-- PARTIE A : DANS OPTIBOARD (CONFIG CENTRALE)
-- ═══════════════════════════════════════════════════════════════
-- NOTE: Chaque batch inclut son propre USE pour garantir le contexte DB
--       meme si pyodbc ne propage pas le USE entre cursor.execute() calls.

-- Batch 1 : Vider pour reimportation propre
USE [{OPTIBOARD_DB}];
PRINT '══════════════════════════════════════════════════════════════';
PRINT ' PARTIE A : INSERTION CONFIG DANS {OPTIBOARD_DB}';
PRINT '══════════════════════════════════════════════════════════════';
DELETE FROM ETL_Tables_Config;
PRINT ' -> Table ETL_Tables_Config videe';
GO

-- Batch 2 : INSERT des 35 configurations
USE [{OPTIBOARD_DB}];

-- ─────────────────────────────────────────────────────────────────
-- PRIORITE HIGH (5 tables)
-- ─────────────────────────────────────────────────────────────────

-- 1. Collaborateurs (FULL)
INSERT INTO ETL_Tables_Config (table_name, source_query, target_table, join_column, filter_column, sync_type, timestamp_column, priority, sort_order, delete_orphans)
VALUES (N'Collaborateurs',
N'SELECT * FROM (SELECT ISNULL(CO_No, ''0'') [Code collaborateur], CO_Nom [Nom collaborateur], CO_Prenom [Prénom collaborateur], CO_Fonction [Fonction collaborateur], CO_Adresse + ISNULL(CO_Complement, '''') [Adresse collaborateur], CO_CodePostal [CP collaborateur], CO_Ville [Ville collaborateur], CO_CodeRegion [Région collaborateur], CO_Pays [Pays collaborateur], CO_Service [Service collaborateur], CASE WHEN CO_Vendeur = 1 THEN ''Oui'' ELSE ''Non'' END Vendeur, CASE WHEN CO_Caissier = 1 THEN ''Oui'' ELSE ''Non'' END Caissier, CASE WHEN CO_Acheteur = 1 THEN ''Oui'' ELSE ''Non'' END Acheteur, CO_Telephone [Tél collaborateur], CO_Telecopie [Fax collaborateur], CO_EMail [Email collaborateur], CO_TelPortable [GSM collaborateur], CASE WHEN CO_ChargeRecouvr = 1 THEN ''Oui'' ELSE ''Non'' END [Charge Recouvr], CASE WHEN CO_Financier = 1 THEN ''Oui'' ELSE ''Non'' END Financier, CO_Facebook [FaceBook collaborateur], CO_LinkedIn [LinkdIn collaborateur], CO_Skype [Skyp collaborateur] FROM F_COLLABORATEUR UNION ALL SELECT ''0'', '''', '''', '''', '''', '''', '''', '''', '''', '''', '''', '''', '''', '''', '''', '''', '''', '''', '''', '''', '''', '''') tab',
N'Collaborateurs', N'Code collaborateur', N'DB', 'full', NULL, 'high', 1, 1);

-- 2. Informations libres (FULL)
INSERT INTO ETL_Tables_Config (table_name, source_query, target_table, join_column, filter_column, sync_type, timestamp_column, priority, sort_order, delete_orphans)
VALUES (N'Informations libres',
N'SELECT [CB_File], [CB_Name] FROM [cbSysLibre]',
N'Info_Libres', NULL, N'DB', 'full', NULL, 'high', 2, 0);

-- 3. Liste des articles (INCREMENTAL)
INSERT INTO ETL_Tables_Config (table_name, source_query, target_table, join_column, filter_column, sync_type, timestamp_column, priority, sort_order, delete_orphans)
VALUES (N'Liste des articles',
N'SELECT F_ARTICLE.cbMarq AS [Code interne], CASE F_ARTICLE.AR_Type WHEN 0 THEN ''Standard'' WHEN 1 THEN ''Gamme'' WHEN 2 THEN ''Ressource Prestation'' WHEN 3 THEN ''Ressource Location'' END AS [Type Article], F_ARTICLE.AR_Ref AS [Code Article], F_ARTICLE.AR_Design AS [Désignation Article], F_ARTICLE.FA_CodeFamille AS [Code Famille], F_FAMILLE.FA_Intitule AS [Intitulé famille], F_FAMILLE_1.FA_Intitule AS [Intitulé Famille Centralisatrice], P_GAMME.G_Intitule AS [Libellé Gamme 1], P_GAMME_1.G_Intitule AS [Libellé Gamme 2], F_CATALOGUE.CL_Intitule AS [Catalogue 1], F_CATALOGUE_1.CL_Intitule AS [Catalogue 2], F_CATALOGUE_2.CL_Intitule AS [Catalogue 3], F_CATALOGUE_3.CL_Intitule AS [Catalogue 4], ISNULL(P_CONDITIONNEMENT.P_Conditionnement, ''Aucun'') AS Conditionnement, P_UNITE.U_Intitule AS [Unité Vente], F_ARTICLE.AR_PrixAch AS [Prix d''achat], F_ARTICLE.AR_PUNet AS [Dernier prix d''achat], F_ARTICLE.AR_Coef AS Coefficient, F_ARTICLE.AR_PrixVen AS [Prix de vente], CASE F_ARTICLE.AR_SuiviStock WHEN 0 THEN ''Aucun'' WHEN 1 THEN ''Sérialisé'' WHEN 2 THEN ''CMUP'' WHEN 3 THEN ''FIFO'' WHEN 4 THEN ''LIFO'' WHEN 5 THEN ''Par lot'' END AS [Suivi Stock], F_ARTICLE.AR_PoidsNet AS [Poids Net], F_ARTICLE.AR_PoidsBrut AS [Poids Brut], CASE F_ARTICLE.AR_Sommeil WHEN 0 THEN ''Actif'' WHEN 1 THEN ''En sommeil'' END AS [Actif / Sommeil], F_ARTICLE.AR_CodeBarre AS [Code Barres], F_ARTICLE.cbCreation [Date création], F_ARTICLE.cbModification [Date modification] FROM P_CONDITIONNEMENT RIGHT OUTER JOIN P_UNITE RIGHT OUTER JOIN F_CATALOGUE RIGHT OUTER JOIN F_ARTICLE LEFT OUTER JOIN F_FAMILLE AS F_FAMILLE_1 RIGHT OUTER JOIN F_FAMILLE ON F_FAMILLE_1.FA_CodeFamille = F_FAMILLE.FA_Central ON F_ARTICLE.FA_CodeFamille = F_FAMILLE.FA_CodeFamille LEFT OUTER JOIN F_CATALOGUE AS F_CATALOGUE_3 ON F_ARTICLE.CL_No4 = F_CATALOGUE_3.CL_No LEFT OUTER JOIN F_CATALOGUE AS F_CATALOGUE_2 ON F_ARTICLE.CL_No3 = F_CATALOGUE_2.CL_No LEFT OUTER JOIN F_CATALOGUE AS F_CATALOGUE_1 ON F_ARTICLE.CL_No2 = F_CATALOGUE_1.CL_No ON F_CATALOGUE.CL_No = F_ARTICLE.CL_No1 ON P_UNITE.cbIndice = F_ARTICLE.AR_UniteVen ON P_CONDITIONNEMENT.cbIndice = F_ARTICLE.AR_Condition LEFT OUTER JOIN P_GAMME AS P_GAMME_1 ON F_ARTICLE.AR_Gamme2 = P_GAMME_1.cbIndice LEFT OUTER JOIN P_GAMME ON F_ARTICLE.AR_Gamme1 = P_GAMME.cbIndice',
N'Articles', N'Code Article', N'DB', 'incremental', N'Date modification', 'high', 3, 1);

-- 4. Liste des clients (INCREMENTAL)
INSERT INTO ETL_Tables_Config (table_name, source_query, target_table, join_column, filter_column, sync_type, timestamp_column, priority, sort_order, delete_orphans)
VALUES (N'Liste des clients',
N'SELECT F_COMPTET.CT_Qualite AS Qualité, F_COMPTET.CT_Num AS [Code client], F_COMPTET.CT_Intitule AS [Intitulé], F_COMPTET.CT_Classement AS [Classement], case when F_COMPTET.CO_No =0 then null else F_COMPTET.CO_No end AS [Code représentant], CO_Nom+'' ''+CO_Prenom AS [Représentant], F_COMPTET.CT_NumPayeur AS [Code payeur], F_COMPTET_1.CT_Intitule AS [Tiers payeur], ISNULL(P_DEVISE.D_Intitule, ''Aucune'') AS [Devise], P_CATTARIF.CT_Intitule AS [Catégorie tarifaire], ISNULL(F_DEPOT.DE_Intitule, ''Dépôt principal'') AS [Dépôt de rattachement], CASE F_COMPTET.CT_Sommeil WHEN 0 THEN ''Actif'' WHEN 1 THEN ''En sommeil'' END AS [En sommeil], F_COMPTET.CG_NumPrinc AS [Compte comptable], F_COMPTET.CT_Contact AS [Contact], F_COMPTET.CT_Adresse AS [Adresse], F_COMPTET.CT_Complement AS [Complément], F_COMPTET.CT_CodePostal AS [Code postal], F_COMPTET.CT_Ville AS Ville, F_COMPTET.CT_CodeRegion AS [Région], F_COMPTET.CT_Pays AS [Pays], F_COMPTET.CT_Telephone AS Téléphone, F_COMPTET.CT_EMail AS Email, F_COMPTET.cbCreation [Date de création], F_COMPTET.cbModification [Date de modification] FROM F_COMPTET LEFT OUTER JOIN F_COMPTET AS F_COMPTET_1 ON F_COMPTET.CT_NumPayeur = F_COMPTET_1.CT_Num LEFT OUTER JOIN P_CRISQUE ON F_COMPTET.N_Risque = P_CRISQUE.cbIndice LEFT OUTER JOIN F_COLLABORATEUR ON F_COMPTET.CO_No = F_COLLABORATEUR.CO_No LEFT OUTER JOIN F_DEPOT ON F_COMPTET.DE_No = F_DEPOT.DE_No LEFT OUTER JOIN P_DEVISE ON F_COMPTET.N_Devise = P_DEVISE.cbIndice LEFT OUTER JOIN P_CATTARIF ON F_COMPTET.N_CatTarif = P_CATTARIF.cbIndice WHERE (F_COMPTET.CT_Type = 0)',
N'Clients', N'Code client', N'DB', 'incremental', N'Date de modification', 'high', 5, 1);

-- 5. Lignes des ventes (INCREMENTAL)
INSERT INTO ETL_Tables_Config (table_name, source_query, target_table, join_column, filter_column, sync_type, timestamp_column, priority, sort_order, delete_orphans)
VALUES (N'Lignes des ventes',
N'TODO: Copier depuis sync_tables.yaml - Lignes des ventes (YAML L588)',
N'Lignes_des_ventes', N'N° interne', N'DB', 'incremental', N'Date modification', 'high', 10, 0);

-- ─────────────────────────────────────────────────────────────────
-- PRIORITE NORMAL - VENTES (6 tables)
-- ─────────────────────────────────────────────────────────────────

-- 6. Lieu de livraison clients (FULL)
INSERT INTO ETL_Tables_Config (table_name, source_query, target_table, join_column, filter_column, sync_type, timestamp_column, priority, sort_order, delete_orphans)
VALUES (N'Lieu de livraison clients',
N'SELECT F_LIVRAISON.LI_No [N° interne], F_LIVRAISON.CT_Num AS [Code client], F_LIVRAISON.LI_Intitule AS [Intitule livraison], ISNULL(F_LIVRAISON.LI_Adresse, '''') + ISNULL(F_LIVRAISON.LI_Complement, '''') AS Adresse, F_LIVRAISON.LI_CodePostal AS [Code postal], F_LIVRAISON.LI_Ville AS Ville, F_LIVRAISON.LI_CodeRegion AS Région, F_LIVRAISON.LI_Pays AS Pays, F_LIVRAISON.LI_Contact AS Contact, CASE WHEN LI_Principal = 1 THEN ''Oui'' ELSE ''Non'' END AS [Dépôt principal], F_LIVRAISON.LI_Telephone AS Téléphone, F_LIVRAISON.LI_Telecopie AS Fax, F_LIVRAISON.LI_EMail AS Email, P_EXPEDITION.E_Intitule AS Expédition, P_CONDLIVR.C_Intitule [Condition de livraison] FROM F_LIVRAISON INNER JOIN P_EXPEDITION ON F_LIVRAISON.N_Expedition = P_EXPEDITION.cbIndice INNER JOIN P_CONDLIVR ON F_LIVRAISON.N_Condition = P_CONDLIVR.cbIndice',
N'Lieu_Livraison_Client', N'N° interne', N'DB', 'full', NULL, 'normal', 6, 1);

-- 7. Entetes des ventes (INCREMENTAL)
INSERT INTO ETL_Tables_Config (table_name, source_query, target_table, join_column, filter_column, sync_type, timestamp_column, priority, sort_order, delete_orphans)
VALUES (N'Entêtes des ventes',
N'TODO: Copier depuis sync_tables.yaml - Entetes des ventes DO_Domaine=0 (YAML L303)',
N'Entête_des_ventes', N'N° Pièce', N'DB', 'incremental', N'Date modification', 'normal', 7, 1);

-- 8. Reglements clients (INCREMENTAL)
INSERT INTO ETL_Tables_Config (table_name, source_query, target_table, join_column, filter_column, sync_type, timestamp_column, priority, sort_order, delete_orphans)
VALUES (N'Règlements clients',
N'SELECT ISNULL(F_CREGLEMENT.CT_NumPayeur, '''') AS [Code client], F_COMPTET_1.CT_Intitule AS Intitulé, F_CREGLEMENT.CT_NumPayeurOrig AS [Code client original], F_COMPTET.CT_Intitule AS [Intitulé original], F_CREGLEMENT.RG_Date AS Date, F_CREGLEMENT.RG_DateEchCont AS [Date d''échéance], F_CREGLEMENT.RG_Reference AS Référence, F_CREGLEMENT.RG_Libelle AS Libellé, CASE WHEN F_CREGLEMENT.RG_Impute = 0 THEN ''Non'' ELSE ''Oui'' END AS Impute, CASE WHEN F_CREGLEMENT.RG_Compta = 0 THEN ''Non'' ELSE ''Oui'' END AS Comptabilisé, F_CREGLEMENT.JO_Num AS [Code journal], F_JOURNAUX.JO_Intitule AS Journal, F_CREGLEMENT.CG_Num AS [Compte générale], F_CREGLEMENT.RG_Piece AS [N° piéce], CASE WHEN F_CREGLEMENT.RG_Valide = 0 THEN ''Non'' ELSE ''Oui'' END AS Valide, P_REGLEMENT.R_Intitule AS [Mode de règlement], ISNULL(P_DEVISE.D_Intitule, ''Aucune'') AS Devise, F_CREGLEMENT.RG_MontantDev AS [Montant en devise], F_CREGLEMENT.RG_Cours AS Cours, F_CREGLEMENT.RG_Montant AS Montant, ISNULL(RG_No, '''') [N° interne], F_CREGLEMENT.RG_Montant-isnull((select sum(RC_Montant) from F_REGLECH where F_REGLECH.rg_no=F_CREGLEMENT.RG_No),0) solde, r_code [Code règlement], F_CREGLEMENT.cbCreation [Date création], F_CREGLEMENT.cbModification [Date modification] FROM F_CREGLEMENT INNER JOIN F_COMPTET AS F_COMPTET_1 ON F_CREGLEMENT.CT_NumPayeur = F_COMPTET_1.CT_Num INNER JOIN F_COMPTET ON F_CREGLEMENT.CT_NumPayeurOrig = F_COMPTET.CT_Num INNER JOIN F_JOURNAUX ON F_CREGLEMENT.JO_Num = F_JOURNAUX.JO_Num LEFT OUTER JOIN P_REGLEMENT ON F_CREGLEMENT.N_Reglement = P_REGLEMENT.cbIndice LEFT OUTER JOIN P_DEVISE ON F_CREGLEMENT.N_Devise = P_DEVISE.cbIndice WHERE (F_CREGLEMENT.RG_Type = 0)',
N'Règlements_Clients', N'N° interne', N'DB', 'incremental', N'Date modification', 'normal', 8, 1);

-- 9. Imputation factures ventes (INCREMENTAL)
INSERT INTO ETL_Tables_Config (table_name, source_query, target_table, join_column, filter_column, sync_type, timestamp_column, priority, sort_order, delete_orphans)
VALUES (N'Imputation les factures des ventes',
N'TODO: Copier depuis sync_tables.yaml - Imputation factures ventes (YAML L532)',
N'Imputation_Factures_Ventes', NULL, N'DB', 'incremental', N'Date modification', 'normal', 9, 0);

-- 10. Imputation BLs (FULL)
INSERT INTO ETL_Tables_Config (table_name, source_query, target_table, join_column, filter_column, sync_type, timestamp_column, priority, sort_order, delete_orphans)
VALUES (N'Imputation BLs',
N'TODO: Non disponible dans sync_tables.yaml - a definir manuellement',
N'Imputation_BL', NULL, N'DB', 'full', NULL, 'normal', 11, 0);

-- 11. Echeances ventes (FULL)
INSERT INTO ETL_Tables_Config (table_name, source_query, target_table, join_column, filter_column, sync_type, timestamp_column, priority, sort_order, delete_orphans)
VALUES (N'Echéances ventes',
N'TODO: Copier depuis sync_tables.yaml - Echeances ventes avec CTE (YAML L825)',
N'Échéances_Ventes', N'N° interne', N'DB', 'incremental', N'cbModification', 'normal', 12, 0);

-- ─────────────────────────────────────────────────────────────────
-- PRIORITE NORMAL - ACHATS (6 tables)
-- ─────────────────────────────────────────────────────────────────

-- 12. Liste des fournisseurs (INCREMENTAL)
INSERT INTO ETL_Tables_Config (table_name, source_query, target_table, join_column, filter_column, sync_type, timestamp_column, priority, sort_order, delete_orphans)
VALUES (N'Liste des fournisseurs',
N'SELECT F_COMPTET.CT_Qualite AS Qualité, F_COMPTET.CT_Num AS [Code fournisseur], F_COMPTET.CT_Intitule AS [Intitulé], F_COMPTET.CT_Classement AS [Classement], F_COMPTET.CO_No AS [Code acheteur], F_COLLABORATEUR.CO_Nom+'' ''+CO_Prenom AS Acheteur, F_COMPTET.CT_NumPayeur AS [Code encaisseur], F_COMPTET_1.CT_Intitule AS [Tiers encaisseur], ISNULL(P_DEVISE.D_Intitule, ''Aucune'') AS [Devise], P_CATTARIF.CT_Intitule AS [Catégorie tarifaire], ISNULL(F_DEPOT.DE_Intitule, ''Dépôt principal'') AS [Dépôt], CASE F_COMPTET.CT_Sommeil WHEN 0 THEN ''Actif'' WHEN 1 THEN ''En sommeil'' END AS [En sommeil], F_COMPTET.CG_NumPrinc AS [Compte comptable], F_COMPTET.CT_Contact AS [Contact], F_COMPTET.CT_Adresse AS [Adresse], F_COMPTET.CT_CodePostal AS [Code postal], F_COMPTET.CT_Ville AS Ville, F_COMPTET.CT_Telephone AS Téléphone, F_COMPTET.CT_EMail AS Email, F_COMPTET.cbCreation [Date de création], F_COMPTET.cbModification [Date modification] FROM F_COMPTET INNER JOIN F_COMPTET F_COMPTET_1 ON F_COMPTET.CT_NumPayeur = F_COMPTET_1.CT_Num LEFT OUTER JOIN P_CRISQUE ON F_COMPTET.N_Risque = P_CRISQUE.cbIndice LEFT OUTER JOIN F_COLLABORATEUR ON F_COMPTET.CO_No = F_COLLABORATEUR.CO_No LEFT OUTER JOIN F_DEPOT ON F_COMPTET.DE_No = F_DEPOT.DE_No LEFT OUTER JOIN P_DEVISE ON F_COMPTET.N_Devise = P_DEVISE.cbIndice LEFT OUTER JOIN P_CATTARIF ON F_COMPTET.N_CatTarif = P_CATTARIF.cbIndice WHERE (F_COMPTET.CT_Type = 1)',
N'Fournisseurs', N'Code fournisseur', N'DB', 'incremental', N'Date modification', 'normal', 14, 1);

-- 13. Entetes des achats (INCREMENTAL)
INSERT INTO ETL_Tables_Config (table_name, source_query, target_table, join_column, filter_column, sync_type, timestamp_column, priority, sort_order, delete_orphans)
VALUES (N'Entêtes des achats',
N'TODO: Copier depuis sync_tables.yaml - Entetes des achats DO_Domaine=1 (YAML L1081)',
N'Entête_des_achats', N'N° Pièce', N'DB', 'incremental', N'Date modification', 'normal', 15, 1);

-- 14. Reglements fournisseurs (INCREMENTAL)
INSERT INTO ETL_Tables_Config (table_name, source_query, target_table, join_column, filter_column, sync_type, timestamp_column, priority, sort_order, delete_orphans)
VALUES (N'Réglements fournisseurs',
N'SELECT ISNULL(F_CREGLEMENT.CT_NumPayeur, '''') AS [Code fournisseur], F_COMPTET_1.CT_Intitule AS Intitulé, F_CREGLEMENT.RG_Date AS Date, F_CREGLEMENT.RG_DateEchCont AS [Date d''échéance], F_CREGLEMENT.RG_Reference AS Référence, F_CREGLEMENT.RG_Libelle AS Libellé, CASE WHEN F_CREGLEMENT.RG_Impute = 0 THEN ''Non'' ELSE ''Oui'' END AS Impute, CASE WHEN F_CREGLEMENT.RG_Compta = 0 THEN ''Non'' ELSE ''Oui'' END AS Comptabilisé, F_CREGLEMENT.JO_Num AS [Code journal], F_JOURNAUX.JO_Intitule AS Journal, F_CREGLEMENT.CG_Num AS [Compte générale], F_CREGLEMENT.RG_Piece AS [N° piéce], P_REGLEMENT.R_Intitule AS [Mode réglement], ISNULL(P_DEVISE.D_Intitule, ''Aucune'') AS Devise, F_CREGLEMENT.RG_MontantDev AS [Montant en devise], F_CREGLEMENT.RG_Cours AS Cours, F_CREGLEMENT.RG_Montant AS Montant, ISNULL(RG_No, '''') [N° interne], F_CREGLEMENT.RG_Montant-isnull((select sum(RC_Montant) from F_REGLECH where F_REGLECH.rg_no=F_CREGLEMENT.RG_No),0) solde, r_code [Code réglement], F_CREGLEMENT.cbCreation [Date création], F_CREGLEMENT.cbModification [Date modification] FROM F_CREGLEMENT INNER JOIN F_COMPTET AS F_COMPTET_1 ON F_CREGLEMENT.CT_NumPayeur = F_COMPTET_1.CT_Num INNER JOIN F_COMPTET ON F_CREGLEMENT.CT_NumPayeurOrig = F_COMPTET.CT_Num INNER JOIN F_JOURNAUX ON F_CREGLEMENT.JO_Num = F_JOURNAUX.JO_Num LEFT OUTER JOIN P_REGLEMENT ON F_CREGLEMENT.N_Reglement = P_REGLEMENT.cbIndice LEFT OUTER JOIN P_DEVISE ON F_CREGLEMENT.N_Devise = P_DEVISE.cbIndice WHERE (F_CREGLEMENT.RG_Type = 1)',
N'Paiements_Fournisseurs', N'N° interne', N'DB', 'incremental', N'Date modification', 'normal', 16, 1);

-- 15. Imputation factures achats (INCREMENTAL)
INSERT INTO ETL_Tables_Config (table_name, source_query, target_table, join_column, filter_column, sync_type, timestamp_column, priority, sort_order, delete_orphans)
VALUES (N'Imputation factures des achats',
N'TODO: Copier depuis sync_tables.yaml - Imputation factures achats (YAML L1305)',
N'Imputation_Factures_Achats', NULL, N'DB', 'incremental', N'Date modification', 'normal', 17, 0);

-- 16. Lignes des achats (INCREMENTAL)
INSERT INTO ETL_Tables_Config (table_name, source_query, target_table, join_column, filter_column, sync_type, timestamp_column, priority, sort_order, delete_orphans)
VALUES (N'Lignes des achats',
N'TODO: Copier depuis sync_tables.yaml - Lignes des achats (YAML L1405)',
N'Lignes_des_achats', N'N° interne', N'DB', 'incremental', N'Date modification', 'normal', 18, 0);

-- 17. Echeances achats (INCREMENTAL)
INSERT INTO ETL_Tables_Config (table_name, source_query, target_table, join_column, filter_column, sync_type, timestamp_column, priority, sort_order, delete_orphans)
VALUES (N'Echéances achats',
N'TODO: Copier depuis sync_tables.yaml - Echeances achats (YAML L1617)',
N'Echeances_Achats', N'N° interne', N'DB', 'incremental', N'Date modification', 'normal', 19, 0);

-- ─────────────────────────────────────────────────────────────────
-- PRIORITE NORMAL - DOCUMENTS INTERNES (2 tables)
-- ─────────────────────────────────────────────────────────────────

-- 18. Entete documents internes (FULL)
INSERT INTO ETL_Tables_Config (table_name, source_query, target_table, join_column, filter_column, sync_type, timestamp_column, priority, sort_order, delete_orphans)
VALUES (N'Entête des documents interne',
N'TODO: Copier depuis sync_tables.yaml - Entete docs internes DO_Domaine=4 (YAML L1731)',
N'Entête_des_documents_internes', N'N° pièce', N'DB', 'incremental', N'Date modification', 'normal', 21, 1);

-- 19. Lignes documents internes (FULL)
INSERT INTO ETL_Tables_Config (table_name, source_query, target_table, join_column, filter_column, sync_type, timestamp_column, priority, sort_order, delete_orphans)
VALUES (N'Ligne des documents internes',
N'TODO: Copier depuis sync_tables.yaml - Ligne docs internes (YAML L1827)',
N'Ligne_des_documents_interne', N'N° interne', N'DB', 'incremental', N'Date modification', 'normal', 22, 0);

-- ─────────────────────────────────────────────────────────────────
-- PRIORITE NORMAL - STOCK (2 tables)
-- ─────────────────────────────────────────────────────────────────

-- 20. Etat du stock (FULL)
INSERT INTO ETL_Tables_Config (table_name, source_query, target_table, join_column, filter_column, sync_type, timestamp_column, priority, sort_order, delete_orphans)
VALUES (N'Etat du stock',
N'SELECT F_ARTSTOCK.AR_Ref AS [Code article], F_ARTSTOCK.DE_No AS [Code dépôt], F_ARTSTOCK.AS_QteMini AS [Quantité minimale], F_ARTSTOCK.AS_QteMaxi AS [Quantité maximale], F_ARTSTOCK.AS_MontSto AS [Valeur du stock (montant)], F_ARTSTOCK.AS_QteSto AS [Quantité en stock], F_ARTSTOCK.AS_QteRes AS [Quntitté réservée], F_ARTSTOCK.AS_QteCom AS [Quantité commandée], F_ARTSTOCK.AS_Principal AS [Dépôt principale], F_ARTSTOCK.cbMarq AS [N° intene], CASE WHEN AS_Mouvemente = 0 THEN ''Non'' ELSE ''Oui'' END AS [Stock mouvementé], FART.AR_Design AS [Désignation article], F_FAMILLE.FA_CodeFamille AS [Code famille], F_FAMILLE.FA_Intitule AS Intitule, F_DEPOT.DE_Intitule, P_UNITE.U_Intitule AS Unité FROM F_FAMILLE INNER JOIN F_ARTICLE AS FART INNER JOIN F_ARTSTOCK AS F_ARTSTOCK ON FART.cbAR_Ref = F_ARTSTOCK.cbAR_Ref INNER JOIN F_DEPOT ON F_ARTSTOCK.DE_No = F_DEPOT.DE_No ON F_FAMILLE.FA_CodeFamille = FART.FA_CodeFamille INNER JOIN P_UNITE ON FART.AR_UniteVen = P_UNITE.cbIndice',
N'Etat_Stock', N'N° intene', N'DB', 'full', NULL, 'normal', 24, 0);

-- 21. Mouvement stock (FULL)
INSERT INTO ETL_Tables_Config (table_name, source_query, target_table, join_column, filter_column, sync_type, timestamp_column, priority, sort_order, delete_orphans)
VALUES (N'Mouvement stock',
N'TODO: Copier depuis sync_tables.yaml - Mouvement stock (YAML L2023)',
N'Mouvement_stock', N'N° interne', N'DB', 'incremental', N'Date modification', 'normal', 25, 0);

-- ─────────────────────────────────────────────────────────────────
-- PRIORITE NORMAL - COMPTABILITE (5 tables)
-- ─────────────────────────────────────────────────────────────────

-- 22. Plan reporting (FULL)
INSERT INTO ETL_Tables_Config (table_name, source_query, target_table, join_column, filter_column, sync_type, timestamp_column, priority, sort_order, delete_orphans)
VALUES (N'Plan reporting',
N'SELECT [CR_Num] Code, CASE WHEN [CR_Type] = 0 THEN ''Détail'' ELSE ''Total'' END [Type de compte], [CR_Intitule] Intitulé FROM [F_COMPTER]',
N'Plan_Reporting', NULL, N'DB', 'full', NULL, 'normal', 27, 0);

-- 23. Plan comptable (FULL)
INSERT INTO ETL_Tables_Config (table_name, source_query, target_table, join_column, filter_column, sync_type, timestamp_column, priority, sort_order, delete_orphans)
VALUES (N'Plan comptable',
N'SELECT CG_Num [Numéro compte], case when CG_Type=0 then ''Détail'' else ''Total'' end [Type de compte], CG_Intitule Intitulé, CG_Classement Classement, case N_Nature when 0 then ''Aucune'' when 1 then ''Client'' when 2 then ''Fournisseur'' when 3 then ''Salarié'' when 4 then ''Banque'' when 5 then ''Caisse'' when 6 then ''Amortissement/Provision'' when 7 then ''Résultat bilan'' when 8 then ''charge'' when 9 then ''Produit'' when 10 then ''Résultat Gestion'' when 11 then ''Immobilisation'' when 12 then ''Capitaux'' when 13 then ''Stock'' when 14 then ''Titre'' end Nature, case CG_Report when 0 then ''Aucun'' when 1 then ''Solde'' when 2 then ''Détail'' end [Type report], F_COMPTEG.CR_Num [Code reporting], case when CG_Sommeil=0 then ''Actif'' else ''En sommeil'' end [Mise en sommeil], F_COMPTEG.cbCreation [Date de création], F_COMPTER.CR_Intitule [Intitulé reporting] FROM F_COMPTEG LEFT OUTER JOIN F_COMPTER ON F_COMPTEG.CR_Num = F_COMPTER.CR_Num',
N'Plan_Comptable', N'Numéro compte', N'DB', 'full', NULL, 'normal', 28, 1);

-- 24. Ecritures Comptables (INCREMENTAL)
INSERT INTO ETL_Tables_Config (table_name, source_query, target_table, join_column, filter_column, sync_type, timestamp_column, priority, sort_order, delete_orphans)
VALUES (N'Les écritures comptables',
N'TODO: Copier depuis sync_tables.yaml (YAML L2224) - AJOUTER CAST(EC_No AS NVARCHAR(250)) AS [id] dans le SELECT',
N'Ecritures_Comptables', N'N° interne', N'DB', 'incremental', N'Date modification', 'normal', 29, 1);

-- 25. Ecritures Analytiques (FULL)
INSERT INTO ETL_Tables_Config (table_name, source_query, target_table, join_column, filter_column, sync_type, timestamp_column, priority, sort_order, delete_orphans)
VALUES (N'Ecritures Analytiques',
N'SELECT F_ECRITUREA.cbMarq [N° interne], F_ECRITUREA.EC_No AS [N° interne EG], F_ECRITUREA.N_Analytique, F_ECRITUREA.EA_Ligne AS Ligne, F_ECRITUREA.CA_Num AS [Compte analytique], F_ECRITUREA.EA_Montant AS [Montant analytique], F_ECRITUREA.EA_Quantite AS Quantité, P_ANALYTIQUE.A_Intitule AS Intitulé, P_ANALYSE.A_Intitule [Plan analytique] FROM F_ECRITUREA INNER JOIN F_COMPTEA ON F_ECRITUREA.N_Analytique = F_COMPTEA.N_Analytique AND F_ECRITUREA.CA_Num = F_COMPTEA.CA_Num INNER JOIN P_ANALYTIQUE ON F_COMPTEA.CA_Num = P_ANALYTIQUE.CA_Num INNER JOIN P_ANALYSE ON F_ECRITUREA.N_Analytique = P_ANALYSE.cbIndice',
N'Ecritures_Analytiques', NULL, N'DB', 'full', NULL, 'normal', 30, 0);

-- ─────────────────────────────────────────────────────────────────
-- PRIORITE NORMAL - TRESORERIE (3 tables)
-- ─────────────────────────────────────────────────────────────────

-- 26. Conditions de paiement (FULL)
INSERT INTO ETL_Tables_Config (table_name, source_query, target_table, join_column, filter_column, sync_type, timestamp_column, priority, sort_order, delete_orphans)
VALUES (N'Conditions de paiement',
N'SELECT CT_Num [Code tiers], N_Reglement [Code interne réglement], CASE RT_Condition WHEN 0 THEN ''Jour(s) net(s)'' WHEN 1 THEN ''Fin mois civil'' ELSE ''Fin mois'' END [Condition], F_REGLEMENTT.RT_NbJour [Nbr jour], RT_JourTb01 [Jour mois 1], RT_JourTb02 [Jour mois 2], RT_JourTb03 [Jour mois 3], RT_JourTb04 [Jour mois 4], RT_JourTb05 [Jour mois 5], RT_JourTb06 [Jour mois 6], RT_TRepart, CASE RT_TRepart WHEN 0 THEN ''Pourcentage'' WHEN 1 THEN ''Equilibre'' ELSE ''Valeur'' END Equilibre, RT_VRepart Valeur, P_REGLEMENT.R_Intitule [Mode réglement], P_REGLEMENT.R_Code [Code réglement] FROM F_REGLEMENTT INNER JOIN P_REGLEMENT ON F_REGLEMENTT.N_Reglement = P_REGLEMENT.cbIndice',
N'Conditions_Paiement', NULL, N'DB', 'full', NULL, 'normal', 32, 0);

-- 27. Encaissements MP (FULL)
INSERT INTO ETL_Tables_Config (table_name, source_query, target_table, join_column, filter_column, sync_type, timestamp_column, priority, sort_order, delete_orphans)
VALUES (N'Encaissements (MP)',
N'TODO: Non disponible dans sync_tables.yaml - a definir manuellement',
N'Encaissement_MP', NULL, N'DB', 'full', NULL, 'normal', 33, 0);

-- 28. Decaissement MP (FULL)
INSERT INTO ETL_Tables_Config (table_name, source_query, target_table, join_column, filter_column, sync_type, timestamp_column, priority, sort_order, delete_orphans)
VALUES (N'Décaissement (MP)',
N'TODO: Non disponible dans sync_tables.yaml - a definir manuellement',
N'Decaissement_MP', NULL, N'DB', 'full', NULL, 'normal', 34, 0);

-- ─────────────────────────────────────────────────────────────────
-- PRIORITE LOW - RH (7 tables)
-- ─────────────────────────────────────────────────────────────────

-- 29. Historique affectations (FULL)
INSERT INTO ETL_Tables_Config (table_name, source_query, target_table, join_column, filter_column, sync_type, timestamp_column, priority, sort_order, delete_orphans)
VALUES (N'Historique affectations',
N'TODO: Non disponible dans sync_tables.yaml - a definir manuellement',
N'RH_Affectation_Histo', NULL, N'DB', 'full', NULL, 'low', 36, 0);

-- 30. Detail paie (FULL)
INSERT INTO ETL_Tables_Config (table_name, source_query, target_table, join_column, filter_column, sync_type, timestamp_column, priority, sort_order, delete_orphans)
VALUES (N'Détail paie',
N'TODO: Non disponible dans sync_tables.yaml - a definir manuellement (UNION ALL complexe)',
N'RH_Paie', NULL, N'DB', 'full', NULL, 'low', 38, 0);

-- 31. Historique conge (FULL) — DESACTIVE : T_HST_CONGE n'existe pas dans Sage commercial
INSERT INTO ETL_Tables_Config (table_name, source_query, target_table, join_column, filter_column, sync_type, timestamp_column, priority, sort_order, delete_orphans, is_active)
VALUES (N'Historique congé',
N'SELECT MatriculeSalarie AS Matricule, T_HST_CONGE.DateDebutConges1 AS [Date début congé 1], T_HST_CONGE.DateFinConges1 AS [Date fin congé 1], T_HST_CONGE.DateDebut AS [Date début congé], T_HST_CONGE.DateHist AS [Date fin congé] FROM T_HST_CONGE INNER JOIN T_SAL ON T_HST_CONGE.NumSalarie = T_SAL.SA_CompteurNumero WHERE (T_HST_CONGE.InfoEnCours = 0)',
N'RH_Congé_Histo', NULL, N'DB', 'full', NULL, 'low', 39, 0, 0);

-- 32. Historique salaire (FULL)
INSERT INTO ETL_Tables_Config (table_name, source_query, target_table, join_column, filter_column, sync_type, timestamp_column, priority, sort_order, delete_orphans)
VALUES (N'Historique salaire',
N'TODO: Non disponible dans sync_tables.yaml - a definir manuellement',
N'RH_Salaire_Histo', NULL, N'DB', 'full', NULL, 'low', 40, 0);

-- 33. Historique contrat travail (FULL) — DESACTIVE : T_HST_CONTRAT n'existe pas dans Sage commercial
INSERT INTO ETL_Tables_Config (table_name, source_query, target_table, join_column, filter_column, sync_type, timestamp_column, priority, sort_order, delete_orphans, is_active)
VALUES (N'Historique contrat travail',
N'SELECT MatriculeSalarie AS Matricule, T_HST_CONTRAT.NoContrat AS [Numéro contrat], T_HST_CONTRAT.CodeNatureDeContrat AS [Code], (SELECT Intitule FROM T_NATUREDECONTRAT WHERE Code = T_HST_CONTRAT.CodeNatureDeContrat) [Intitulé contrat], T_HST_CONTRAT.DateDebutContrat AS [Date début contrat], T_HST_CONTRAT.DateFinContrat AS [Date fin contrat], T_HST_CONTRAT.FinPeriodeEssai AS [Fin période essai], T_HST_CONTRAT.DateDebut AS [Date Début], T_HST_CONTRAT.DateHist AS [Date fin] FROM T_HST_CONTRAT INNER JOIN T_SAL ON T_HST_CONTRAT.NumSalarie = T_SAL.SA_CompteurNumero WHERE (T_HST_CONTRAT.InfoEnCours = 0)',
N'RH_Contrat_Tra_Histo', NULL, N'DB', 'full', NULL, 'low', 41, 0, 0);

-- 34. Historique effectifs (FULL)
INSERT INTO ETL_Tables_Config (table_name, source_query, target_table, join_column, filter_column, sync_type, timestamp_column, priority, sort_order, delete_orphans)
VALUES (N'Historique effectifs',
N'TODO: Non disponible dans sync_tables.yaml - a definir manuellement',
N'RH_Effectif_Histo', NULL, N'DB', 'full', NULL, 'low', 42, 0);

-- 35. Historique (FULL)
INSERT INTO ETL_Tables_Config (table_name, source_query, target_table, join_column, filter_column, sync_type, timestamp_column, priority, sort_order, delete_orphans)
VALUES (N'Historique',
N'TODO: Non disponible dans sync_tables.yaml - a definir manuellement',
N'RH_Historique', NULL, N'DB', 'full', NULL, 'low', 43, 0);
GO

-- ─────────────────────────────────────────────────────────────────
-- Batch 3 : VERIFICATION
-- ─────────────────────────────────────────────────────────────────
USE [{OPTIBOARD_DB}];
PRINT '';

SELECT
    [table_name]        AS [Table],
    [target_table]      AS [Cible DWH],
    [sort_order]        AS [Ordre],
    [sync_type]         AS [Type],
    [join_column]       AS [Join Column],
    [filter_column]     AS [Filter Column],
    [timestamp_column]  AS [TS Column],
    [priority]          AS [Priorite],
    [delete_orphans]    AS [Delete],
    CASE WHEN [source_query] LIKE 'TODO%' THEN 'TODO' ELSE 'OK' END AS [Query]
FROM [ETL_Tables_Config]
WHERE [is_active] = 1
ORDER BY [sort_order];

DECLARE @total INT = (SELECT COUNT(*) FROM [ETL_Tables_Config]);
DECLARE @todo INT = (SELECT COUNT(*) FROM [ETL_Tables_Config] WHERE [source_query] LIKE 'TODO%');
DECLARE @ok INT = @total - @todo;

PRINT '';
PRINT '══════════════════════════════════════════════════════════════';
PRINT ' CONFIGURATIONS ETL INSEREES DANS {OPTIBOARD_DB}';
PRINT '══════════════════════════════════════════════════════════════';
PRINT ' Total tables configurees: ' + CAST(@total AS VARCHAR);
PRINT ' Queries completes:        ' + CAST(@ok AS VARCHAR);
PRINT ' Queries a completer:      ' + CAST(@todo AS VARCHAR);
PRINT '';
PRINT ' Nouvelles colonnes v2 :';
PRINT '   - join_column    : Colonne PK pour MERGE ON (-> @JoinColumn)';
PRINT '   - filter_column  : Colonne multi-source (-> @FilterColumn, defaut DB)';
PRINT '   - delete_orphans : Detection suppressions (-> @DeleteOrphans)';
PRINT '';
PRINT ' IMPORTANT: Remplacez les queries "TODO" par les requetes';
PRINT ' completes depuis sync_tables.yaml ou insert_sync_query_data.sql';
PRINT '══════════════════════════════════════════════════════════════';
GO

-- ═══════════════════════════════════════════════════════════════
-- PARTIE B : EXEMPLES DE SOURCES DANS DWH
-- ═══════════════════════════════════════════════════════════════

-- Batch 5 : Source exemple
USE [{DWH_NAME}];
PRINT '';
PRINT '══════════════════════════════════════════════════════════════';
PRINT ' PARTIE B : EXEMPLES DE SOURCES DANS {DWH_NAME}';
PRINT '══════════════════════════════════════════════════════════════';
-- Source exemple : CASHPLUS_2026 (meme serveur - Scenario A)
-- Utilise SP_ETL_Setup_Source pour creer proprement
IF NOT EXISTS (SELECT 1 FROM ETL_Sources WHERE source_code = 'CASHPLUS_2026')
BEGIN
    EXEC SP_ETL_Setup_Source
        @SourceCode       = 'CASHPLUS_2026',
        @SourceCaption    = 'GROUPE CASHPLUS',
        @DbId             = 1,
        @ServerName       = '.',
        @DatabaseName     = 'CASHPLUS_2026',
        @IsLinkedServer   = 0;
END
GO

-- Exemples commentes pour d'autres sources :
/*
-- Source meme serveur (Scenario A) :
EXEC SP_ETL_Setup_Source
    @SourceCode    = 'BIJOU',
    @SourceCaption = 'BIJOU SANITAIRE',
    @DbId          = 2,
    @ServerName    = '.',
    @DatabaseName  = 'BIJOU';

-- Source serveur distant (Scenario B - Linked Server) :
EXEC SP_ETL_Setup_Source
    @SourceCode       = 'DIAMOND',
    @SourceCaption    = 'DIAMOND OPERATIONS',
    @DbId             = 3,
    @ServerName       = '192.168.1.100',
    @DatabaseName     = 'DIAMOND',
    @IsLinkedServer   = 1,
    @LinkedServerName = 'SAGE_SRV_01';
*/

PRINT '';
PRINT '══════════════════════════════════════════════════════════════';
PRINT ' INSERTION TERMINEE';
PRINT '';
PRINT ' NOTE : SyncControl sera cree automatiquement (lazy init)';
PRINT '        par sp_Sync_Generic au premier cycle du Job.';
PRINT '══════════════════════════════════════════════════════════════';
