"""
Configuration des vues Sage Direct
====================================
Chaque entrée mappe une vue/table DWH vers une requête Sage
qui produit les MEMES colonnes que la vue DWH.

Le placeholder {db} est remplacé par le nom de la base Sage (ex: bijou).
Le placeholder {societe} est remplacé par le code_societe.
"""

# ─────────────────────────────────────────────────────────────────────────────
# SAGE_VIEW_CONFIG : clé = nom exact de la table DWH (telle que référencée
# dans query_templates.py entre [dbo].[...])
# ─────────────────────────────────────────────────────────────────────────────

SAGE_VIEW_CONFIG = {

    # ═══════════════════════════════════════════════════════════════════════
    # DashBoard_CA — source principale pour Ventes, Dashboard, FicheClient
    # ═══════════════════════════════════════════════════════════════════════
    "DashBoard_CA": {
        "sage_sql": """
            SELECT
                e.DO_Date                                        AS [Date BL],
                l.DL_MontantHT                                   AS [Montant HT Net],
                l.DL_MontantTTC                                  AS [Montant TTC Net],
                l.DL_Qte * ISNULL(l.DL_PrixUnitaire, 0)           AS [Coût],
                e.DO_Tiers                                       AS [Code client],
                c.CT_Intitule                                    AS [Intitulé client],
                l.AR_Ref                                         AS [Code article],
                l.DL_Design                                      AS [Désignation],
                l.DL_Qte                                         AS [Quantité],
                ISNULL(a.FA_CodeFamille, '')                     AS [Catalogue 1],
                ISNULL(c.CT_Classement, '')                      AS [Catégorie_],
                ISNULL(e.DO_Souche, 0)                           AS [Souche],
                ISNULL(co.CO_Prenom + ' ' + co.CO_Nom,
                       CAST(e.CO_No AS VARCHAR(20)))             AS [Représentant],
                '{societe}'                                      AS [Société]
            FROM [{db}].[dbo].[F_DOCLIGNE] l
            INNER JOIN [{db}].[dbo].[F_DOCENTETE] e
                ON l.DO_Piece = e.DO_Piece AND l.DO_Type = e.DO_Type
            LEFT JOIN [{db}].[dbo].[F_ARTICLE] a
                ON l.AR_Ref = a.AR_Ref
            LEFT JOIN [{db}].[dbo].[F_COMPTET] c
                ON e.DO_Tiers = c.CT_Num
            LEFT JOIN [{db}].[dbo].[F_COLLABORATEUR] co
                ON e.CO_No = co.CO_No
            WHERE e.DO_Type IN (6, 7)
              AND l.AR_Ref <> ''
        """,
    },

    # ═══════════════════════════════════════════════════════════════════════
    # Mouvement_stock — source pour Stocks (rotation, dormant, par article)
    # ═══════════════════════════════════════════════════════════════════════
    "Mouvement_stock": {
        "sage_sql": """
            SELECT
                '{societe}'                                      AS [DB],
                '{societe}'                                      AS [societe],
                l.AR_Ref                                         AS [Code article],
                ISNULL(a.AR_Design, l.DL_Design)                 AS [Désignation],
                CASE e.DO_Type
                    WHEN 3  THEN 'BL'
                    WHEN 6  THEN 'Facture'
                    WHEN 7  THEN 'Avoir'
                    WHEN 12 THEN 'BL Achat'
                    WHEN 13 THEN 'BR Achat'
                    WHEN 14 THEN 'Facture Achat'
                    WHEN 15 THEN 'Avoir Achat'
                    ELSE 'Type ' + CAST(e.DO_Type AS VARCHAR(5))
                END                                              AS [Type Mouvement],
                CASE e.DO_Domaine
                    WHEN 0 THEN 'Ventes'
                    WHEN 1 THEN 'Achats'
                    WHEN 2 THEN 'Stock'
                    ELSE CAST(e.DO_Domaine AS VARCHAR(5))
                END                                              AS [Domaine mouvement],
                CONVERT(VARCHAR(10), e.DO_Date, 120)             AS [Date Mouvement],
                e.DO_Piece                                       AS [N° Pièce],
                l.DL_CMUP                                        AS [CMUP],
                l.DL_PrixUnitaire                                AS [Prix unitaire],
                l.DL_CMUP                                        AS [Prix de revient],
                l.DL_Qte                                         AS [Quantité],
                CASE
                    WHEN e.DO_Type IN (3, 6)       THEN 'S'
                    WHEN e.DO_Type IN (7)          THEN 'E'
                    WHEN e.DO_Type IN (12, 13, 14) THEN 'E'
                    WHEN e.DO_Type IN (15)         THEN 'S'
                    ELSE 'E'
                END                                              AS [Sens de mouvement],
                l.DL_Qte * l.DL_CMUP                             AS [Montant Stock],
                e.CO_No                                          AS [Code coloboratore],
                ISNULL(co.CO_Prenom + ' ' + co.CO_Nom,
                       CAST(e.CO_No AS VARCHAR(20)))             AS [Représentant],
                ISNULL(a.FA_CodeFamille, '')                     AS [Code famille],
                ISNULL(fa.FA_Intitule, '')                        AS [Intitulé famille],
                ISNULL(cat1.CL_Intitule, '')                     AS [Catalogue 1],
                ISNULL(cat2.CL_Intitule, '')                     AS [Catalogue 2],
                ISNULL(cat3.CL_Intitule, '')                     AS [Catalogue 3],
                ISNULL(cat4.CL_Intitule, '')                     AS [Catalogue 4],
                ISNULL(g1.G_Intitule, '')                        AS [Gamme 1],
                ISNULL(g2.G_Intitule, '')                        AS [Gamme 2],
                l.DE_No                                          AS [Code Dépôt],
                ISNULL(dep.DE_Intitule, '')                      AS [Dépôt],
                c.CT_Intitule                                    AS [Intitulé tiers],
                e.DO_Tiers                                       AS [Code tiers],
                c.CT_Intitule                                    AS [Intitulé client],
                CAST(NULL AS VARCHAR(50))                        AS [N° Série / Lot],
                CAST(NULL AS VARCHAR(20))                        AS [Suivi Stock],
                CAST(NULL AS VARCHAR(20))                        AS [DPA-Période],
                CAST(NULL AS FLOAT)                              AS [DPA-Vente],
                CAST(NULL AS FLOAT)                              AS [Coût standard],
                CAST(NULL AS FLOAT)                              AS [DPR-Vente],
                CAST(NULL AS DATETIME)                           AS [Date Péremption],
                CAST(NULL AS DATETIME)                           AS [Date Fabrication]
            FROM [{db}].[dbo].[F_DOCLIGNE] l
            INNER JOIN [{db}].[dbo].[F_DOCENTETE] e
                ON l.DO_Piece = e.DO_Piece AND l.DO_Type = e.DO_Type
            LEFT JOIN [{db}].[dbo].[F_ARTICLE] a
                ON l.AR_Ref = a.AR_Ref
            LEFT JOIN [{db}].[dbo].[F_COMPTET] c
                ON e.DO_Tiers = c.CT_Num
            LEFT JOIN [{db}].[dbo].[F_COLLABORATEUR] co
                ON e.CO_No = co.CO_No
            LEFT JOIN [{db}].[dbo].[F_FAMILLE] fa
                ON a.FA_CodeFamille = fa.FA_CodeFamille
            LEFT JOIN [{db}].[dbo].[F_CATALOGUE] cat1
                ON a.CL_No1 = cat1.CL_No
            LEFT JOIN [{db}].[dbo].[F_CATALOGUE] cat2
                ON a.CL_No2 = cat2.CL_No
            LEFT JOIN [{db}].[dbo].[F_CATALOGUE] cat3
                ON a.CL_No3 = cat3.CL_No
            LEFT JOIN [{db}].[dbo].[F_CATALOGUE] cat4
                ON a.CL_No4 = cat4.CL_No
            LEFT JOIN [{db}].[dbo].[P_GAMME] g1
                ON l.AG_No1 = g1.cbIndice
            LEFT JOIN [{db}].[dbo].[P_GAMME] g2
                ON l.AG_No2 = g2.cbIndice
            LEFT JOIN [{db}].[dbo].[F_DEPOT] dep
                ON l.DE_No = dep.DE_No
            WHERE e.DO_TYPE IN (3, 6, 7, 12, 13, 14, 15)
              AND l.AR_Ref <> ''
              AND l.DL_Qte <> 0
        """,
    },

    # ═══════════════════════════════════════════════════════════════════════
    # Clients — fiche client, info client
    # ═══════════════════════════════════════════════════════════════════════
    "Clients": {
        "sage_sql": """
            SELECT
                c.CT_Num                                         AS [Code client],
                c.CT_Intitule                                    AS [Intitulé],
                ISNULL(co.CO_Prenom + ' ' + co.CO_Nom,
                       CAST(c.CO_No AS VARCHAR(20)))             AS [Représentant],
                CAST(NULL AS INT)                                AS [Risque client],
                c.CT_Encours                                     AS [Encours de l'autorisation],
                CAST(0 AS DECIMAL(18,2))                         AS [Assurance],
                ISNULL(c.CT_Telephone, '')                       AS [Téléphone],
                ISNULL(c.CT_Email, '')                           AS [Email],
                ISNULL(c.CT_Adresse, '')                         AS [Adresse],
                ISNULL(c.CT_Ville, '')                           AS [Ville],
                ''                                               AS [ICE_],
                ''                                               AS [RC_],
                ''                                               AS [Capital_],
                ''                                               AS [Forme juridique_],
                CAST(NULL AS DATETIME)                           AS [Date de création]
            FROM [{db}].[dbo].[F_COMPTET] c
            LEFT JOIN [{db}].[dbo].[F_COLLABORATEUR] co
                ON c.CO_No = co.CO_No
            WHERE c.CT_Type = 0
        """,
    },

    # ═══════════════════════════════════════════════════════════════════════
    # Fournisseurs — fiche fournisseur, info fournisseur (F_COMPTET CT_Type=1)
    # ═══════════════════════════════════════════════════════════════════════
    "Fournisseurs": {
        "sage_sql": """
            SELECT
                f.CT_Num                                         AS [Code fournisseur],
                f.CT_Intitule                                    AS [Intitulé],
                ISNULL(co.CO_Prenom + ' ' + co.CO_Nom,
                       CAST(f.CO_No AS VARCHAR(20)))             AS [Acheteur],
                CAST(NULL AS INT)                                AS [Risque fournisseur],
                f.CT_Encours                                     AS [Encours de l'autorisation],
                CAST(0 AS DECIMAL(18,2))                         AS [Assurance],
                ISNULL(f.CT_Telephone, '')                       AS [Téléphone],
                ISNULL(f.CT_Telecopie, '')                       AS [Fax],
                ISNULL(f.CT_Email, '')                           AS [Email],
                ISNULL(f.CT_Adresse, '')                         AS [Adresse],
                ISNULL(f.CT_Ville, '')                           AS [Ville],
                ''                                               AS [ICE],
                ''                                               AS [RC],
                CAST(0 AS DECIMAL(18,2))                         AS [Capital],
                ''                                               AS [Forme_Juridique],
                CAST(NULL AS DATETIME)                           AS [Date de création]
            FROM [{db}].[dbo].[F_COMPTET] f
            LEFT JOIN [{db}].[dbo].[F_COLLABORATEUR] co
                ON f.CO_No = co.CO_No
            WHERE f.CT_Type = 1
        """,
    },

    # ═══════════════════════════════════════════════════════════════════════
    # Entête_des_ventes — documents vente (factures, avoirs, BL)
    # ═══════════════════════════════════════════════════════════════════════
    "Entête_des_ventes": {
        "sage_sql": """
            SELECT
                '{societe}'                                      AS [societe],
                '{societe}'                                      AS [DB_Caption],
                CASE e.DO_Type
                    WHEN 0  THEN 'Devis'
                    WHEN 1  THEN 'Bon de commande'
                    WHEN 2  THEN 'Préparation de livraison'
                    WHEN 3  THEN 'Bon de livraison'
                    WHEN 4  THEN 'Bon de retour'
                    WHEN 5  THEN 'Bon avoir financier'
                    WHEN 6  THEN 'Facture'
                    WHEN 7  THEN 'Facture comptabilisée'
                    ELSE 'Type ' + CAST(e.DO_Type AS VARCHAR(5))
                END                                              AS [Type Document],
                ISNULL(e.DO_Souche, 0)                           AS [Souche],
                e.DO_Piece                                       AS [N° pièce],
                CONVERT(DATETIME, e.DO_Date, 120)                AS [Date],
                e.DO_TotalHT                                     AS [Montant HT],
                e.DO_TotalTTC                                    AS [Montant TTC],
                CAST(0 AS FLOAT)                                 AS [Montant réglé],
                e.DO_Statut                                      AS [Statut],
                CAST('' AS VARCHAR(50))                          AS [Etat],
                e.CO_No                                          AS [Code représentant],
                ISNULL(co.CO_Prenom + ' ' + co.CO_Nom,
                       CAST(e.CO_No AS VARCHAR(20)))             AS [Nom représentant],
                e.DO_Ref                                         AS [Référence],
                CAST(NULL AS VARCHAR(100))                       AS [Entête 1],
                CAST(NULL AS VARCHAR(100))                       AS [Entête 2],
                CAST(NULL AS VARCHAR(100))                       AS [Entête 3],
                CAST(NULL AS VARCHAR(100))                       AS [Entête 4],
                dev.D_Intitule                                   AS [Devise],
                CAST(NULL AS VARCHAR(50))                        AS [Expédition],
                e.DO_Cours                                       AS [Cours],
                CAST(NULL AS VARCHAR(20))                        AS [N° Compte Payeur],
                CAST(NULL AS VARCHAR(100))                       AS [Intitulé tiers payeur],
                CAST(NULL AS INT)                                AS [Catégorie Comptable],
                CONVERT(DATETIME, e.cbCreation, 120)             AS [Date création],
                CONVERT(DATETIME, e.cbModification, 120)         AS [Date modification],
                e.DO_Tiers                                       AS [Code client],
                ISNULL(ct.CT_Intitule, e.DO_Tiers)              AS [Intitulé client]
            FROM [{db}].[dbo].[F_DOCENTETE] e
            LEFT JOIN [{db}].[dbo].[F_COLLABORATEUR] co
                ON e.CO_No = co.CO_No
            LEFT JOIN [{db}].[dbo].[P_DEVISE] dev
                ON e.DO_Devise = dev.cbIndice
            LEFT JOIN [{db}].[dbo].[F_COMPTET] ct
                ON e.DO_Tiers = ct.CT_Num
            WHERE e.DO_Domaine = 0
        """,
    },

    # ═══════════════════════════════════════════════════════════════════════
    # Lignes_des_ventes — lignes de documents de vente
    # ═══════════════════════════════════════════════════════════════════════
    "Lignes_des_ventes": {
        "sage_sql": """
            SELECT
                '{societe}'                                      AS [societe],
                l.DL_No                                          AS [N° interne],
                CASE l.DO_Type
                    WHEN 0 THEN 'Devis'
                    WHEN 1 THEN 'Bon de commande'
                    WHEN 2 THEN 'Préparation de livraison'
                    WHEN 3 THEN 'Bon de livraison'
                    WHEN 4 THEN 'Bon de retour'
                    WHEN 5 THEN 'Bon avoir financier'
                    WHEN 6 THEN 'Facture'
                    WHEN 7 THEN 'Facture comptabilisée'
                    ELSE '' END                                  AS [Type Document],
                CASE WHEN l.DO_Type < 3 THEN 'Non' ELSE 'Oui' END AS [Valorise CA],
                e.DO_Tiers                                       AS [Code client],
                ct.CT_Intitule                                   AS [Intitulé client],
                ISNULL(l.DO_Piece, '')                           AS [N° Pièce],
                CONVERT(DATETIME, e.DO_Date, 120)                AS [Date document],
                CASE
                    WHEN l.DO_Type = 3 THEN l.DO_Piece
                    WHEN l.DO_Type > 3 THEN l.DL_PieceBL
                    ELSE '' END                                  AS [N° Pièce BL],
                CASE
                    WHEN l.DO_Type = 3 THEN l.DO_Date
                    WHEN l.DO_Type > 3 AND l.DL_DateBL > '1900-01-01' THEN l.DL_DateBL
                    ELSE l.DO_Date END                           AS [Date BL],
                CASE l.DO_Type WHEN 1 THEN l.DO_Piece ELSE l.DL_PieceBC END AS [N° Pièce BC],
                CASE
                    WHEN l.DO_Type = 1 THEN l.DO_Date
                    WHEN l.DL_DateBC > '1900-01-01' THEN l.DL_DateBC
                    ELSE l.DO_Date END                           AS [Date BC],
                CASE l.DO_Type WHEN 2 THEN l.DO_Piece ELSE l.DL_PieceBC END AS [N° pièce PL],
                CASE
                    WHEN l.DO_Type = 2 THEN l.DO_Date
                    WHEN l.DL_DatePL > '1900-01-01' THEN l.DL_DatePL
                    ELSE l.DO_Date END                           AS [Date PL],
                l.AR_Ref                                         AS [Code article],
                l.DL_Design                                      AS [Désignation ligne],
                cat1.CL_Intitule                                 AS [Catalogue 1],
                cat2.CL_Intitule                                 AS [Catalogue 2],
                cat3.CL_Intitule                                 AS [Catalogue 3],
                cat4.CL_Intitule                                 AS [Catalogue 4],
                g1.G_Intitule                                    AS [Gamme 1],
                g2.G_Intitule                                    AS [Gamme 2],
                CASE
                    WHEN l.DO_Type <> 5 AND l.DO_Type <> 15
                         AND l.DL_TRemPied = 0 AND l.DL_TRemExep = 0
                         AND l.DL_TypePL < 2
                    THEN CASE WHEN l.DO_Type IN (4, 14) THEN -l.DL_Qte ELSE l.DL_Qte END
                    ELSE 0 END                                   AS [Quantité],
                l.DL_QtePL                                       AS [Quantité PL],
                l.DL_QteBC                                       AS [Quantité BC],
                l.DL_QteBL                                       AS [Quantité BL],
                l.DL_QteDE                                       AS [Quantité devis],
                l.DL_CMUP                                        AS [CMUP],
                l.DL_PrixUnitaire                                AS [Prix unitaire],
                l.DL_PUTTC                                       AS [Prix unitaire TTC],
                l.DL_PUBC                                        AS [Prix unitaire BC],
                l.DL_PrixRU                                      AS [Prix de revient],
                CASE
                    WHEN (l.DO_Type BETWEEN 4 AND 5) OR (l.DO_Type BETWEEN 14 AND 15)
                    THEN -l.DL_MontantHT ELSE l.DL_MontantHT END AS [Montant HT Net],
                CASE
                    WHEN (l.DO_Type BETWEEN 4 AND 5) OR (l.DO_Type BETWEEN 14 AND 15)
                    THEN -l.DL_MontantTTC ELSE l.DL_MontantTTC END AS [Montant TTC Net],
                l.DE_No                                          AS [Code dépôt],
                d.DE_Intitule                                    AS [Intitulé dépôt],
                CONVERT(DATETIME, l.cbCreation, 120)             AS [Date création],
                CONVERT(DATETIME, l.cbModification, 120)         AS [Date modification],
                l.DO_Ref                                         AS [Référence],
                CAST(l.DL_PoidsBrut AS FLOAT)                    AS [Poids brut],
                CAST(l.DL_PoidsNet AS FLOAT)                     AS [Poids net],
                CAST(NULL AS VARCHAR(100))                       AS [Intitulé affaire],
                l.CA_Num                                         AS [Code d'affaire],
                CAST(NULL AS VARCHAR(50))                        AS [N° Série/Lot],
                CAST(l.DL_Taxe1 AS VARCHAR(20))                  AS [Taxe1],
                CAST(l.DL_Taxe2 AS VARCHAR(20))                  AS [Taxe2],
                CAST(l.DL_Taxe3 AS VARCHAR(20))                  AS [Taxe3],
                CASE l.DL_TypeTaux1 WHEN 0 THEN 'Taux %' WHEN 1 THEN 'Montant forfait' WHEN 2 THEN 'Quantité' ELSE '' END AS [Type taux taxe 1],
                CASE l.DL_TypeTaux2 WHEN 0 THEN 'Taux %' WHEN 1 THEN 'Montant forfait' WHEN 2 THEN 'Quantité' ELSE '' END AS [Type taux taxe 2],
                CASE l.DL_TypeTaux3 WHEN 0 THEN 'Taux %' WHEN 1 THEN 'Montant forfait' WHEN 2 THEN 'Quantité' ELSE '' END AS [Type taux taxe 3],
                CASE l.DL_TypeTaxe1 WHEN 0 THEN 'TVA/débit' WHEN 1 THEN 'TVA/Encaissement' WHEN 2 THEN 'TP/HT' WHEN 3 THEN 'TP/TTC' WHEN 4 THEN 'TP/Poids' ELSE '' END AS [Type taxe 1],
                CASE l.DL_TypeTaxe2 WHEN 0 THEN 'TVA/débit' WHEN 1 THEN 'TVA/Encaissement' WHEN 2 THEN 'TP/HT' WHEN 3 THEN 'TP/TTC' WHEN 4 THEN 'TP/Poids' ELSE '' END AS [Type taxe 2],
                CASE l.DL_TypeTaxe3 WHEN 0 THEN 'TVA/débit' WHEN 1 THEN 'TVA/Encaissement' WHEN 2 THEN 'TP/HT' WHEN 3 THEN 'TP/TTC' WHEN 4 THEN 'TP/Poids' ELSE '' END AS [Type taxe 3],
                FORMAT(l.DL_Remise01REM_Valeur, 'P2')            AS [Remise 1],
                FORMAT(l.DL_Remise02REM_Valeur, 'P2')            AS [Remise 2],
                CASE l.DL_Remise01REM_Type WHEN 0 THEN 'Montant' WHEN 1 THEN 'Pourcentage' WHEN 2 THEN 'Quantité' ELSE '' END AS [Type de la remise 1],
                CASE l.DL_Remise02REM_Type WHEN 0 THEN 'Montant' WHEN 1 THEN 'Pourcentage' WHEN 2 THEN 'Quantité' ELSE '' END AS [Type de la remise 2],
                CAST(l.DL_Frais AS FLOAT)                        AS [Frais d'approche],
                l.DL_PUDevise                                    AS [PU Devise],
                CAST(NULL AS VARCHAR(50))                        AS [Colisage],
                CASE l.DL_TNomencl WHEN 0 THEN 'Oui' WHEN 1 THEN 'Non' ELSE '' END AS [Nomenclature],
                CASE l.DL_TRemPied WHEN 0 THEN 'Oui' WHEN 1 THEN 'Non' ELSE '' END AS [Type remise de pied],
                CASE l.DL_TRemExep WHEN 0 THEN 'Oui' WHEN 1 THEN 'Non' ELSE '' END AS [Type remise exceptionnelle],
                CAST(NULL AS VARCHAR(50))                        AS [Conditionnement],
                l.AC_RefClient                                   AS [Référence article client],
                l.DL_FactPoids                                   AS [Article facturé au poids],
                CASE
                    WHEN l.DO_DateLivr < '1900-01-01' THEN NULL
                    ELSE l.DO_DateLivr
                END                                              AS [Date Livraison]
            FROM [{db}].[dbo].[F_DOCLIGNE] l
            INNER JOIN [{db}].[dbo].[F_ARTICLE] fart
                ON l.cbAR_Ref = fart.cbAR_Ref
            INNER JOIN [{db}].[dbo].[F_DOCENTETE] e
                ON l.DO_Type = e.DO_Type AND l.DO_Piece = e.DO_Piece
            INNER JOIN [{db}].[dbo].[F_COMPTET] ct
                ON e.cbDO_Tiers = ct.cbCT_Num
            LEFT OUTER JOIN [{db}].[dbo].[F_DEPOT] d
                ON l.DE_No = d.DE_No
            LEFT OUTER JOIN [{db}].[dbo].[P_GAMME] g1
                ON l.AG_No1 = g1.cbIndice
            LEFT OUTER JOIN [{db}].[dbo].[P_GAMME] g2
                ON l.AG_No2 = g2.cbIndice
            LEFT OUTER JOIN [{db}].[dbo].[F_CATALOGUE] cat1
                ON fart.CL_No1 = cat1.CL_No
            LEFT OUTER JOIN [{db}].[dbo].[F_CATALOGUE] cat2
                ON fart.CL_No2 = cat2.CL_No
            LEFT OUTER JOIN [{db}].[dbo].[F_CATALOGUE] cat3
                ON fart.CL_No3 = cat3.CL_No
            LEFT OUTER JOIN [{db}].[dbo].[F_CATALOGUE] cat4
                ON fart.CL_No4 = cat4.CL_No
            WHERE l.DO_Domaine = 0
              AND l.DL_TRemExep < 2
              AND l.DL_NonLivre = 0
        """,
    },

    # ═══════════════════════════════════════════════════════════════════════
    # Entête_des_achats — documents achat (factures fournisseurs, BL, BC, ...)
    # ═══════════════════════════════════════════════════════════════════════
    "Entête_des_achats": {
        "sage_sql": """
            SELECT
                '{societe}'                                      AS [societe],
                '{societe}'                                      AS [DB_Caption],
                CASE e.DO_Type
                    WHEN 10 THEN 'Demande d''achat'
                    WHEN 11 THEN 'Bon de commande'
                    WHEN 12 THEN 'Préparation de livraison'
                    WHEN 13 THEN 'Bon de livraison'
                    WHEN 14 THEN 'Bon de retour'
                    WHEN 15 THEN 'Bon avoir financier'
                    WHEN 16 THEN 'Facture'
                    WHEN 17 THEN 'Facture comptabilisée'
                    ELSE 'Type ' + CAST(e.DO_Type AS VARCHAR(5))
                END                                              AS [Type Document],
                ISNULL(e.DO_Souche, 0)                           AS [Souche],
                e.DO_Piece                                       AS [N° pièce],
                CONVERT(DATETIME, e.DO_Date, 120)                AS [Date],
                e.DO_TotalHT                                     AS [Montant HT],
                e.DO_TotalTTC                                    AS [Montant TTC],
                CAST(0 AS FLOAT)                                 AS [Montant réglé],
                e.DO_Statut                                      AS [Statut],
                CAST('' AS VARCHAR(50))                          AS [Etat],
                e.CO_No                                          AS [Code représentant],
                ISNULL(co.CO_Prenom + ' ' + co.CO_Nom,
                       CAST(e.CO_No AS VARCHAR(20)))             AS [Nom représentant],
                e.DO_Ref                                         AS [Référence],
                CAST(NULL AS VARCHAR(100))                       AS [Entête 1],
                CAST(NULL AS VARCHAR(100))                       AS [Entête 2],
                CAST(NULL AS VARCHAR(100))                       AS [Entête 3],
                CAST(NULL AS VARCHAR(100))                       AS [Entête 4],
                dev.D_Intitule                                   AS [Devise],
                CAST(NULL AS VARCHAR(50))                        AS [Expédition],
                e.DO_Cours                                       AS [Cours],
                CAST(NULL AS VARCHAR(20))                        AS [N° Compte Payeur],
                CAST(NULL AS VARCHAR(100))                       AS [Intitulé tiers payeur],
                CAST(NULL AS INT)                                AS [Catégorie Comptable],
                CONVERT(DATETIME, e.cbCreation, 120)             AS [Date création],
                CONVERT(DATETIME, e.cbModification, 120)         AS [Date modification]
            FROM [{db}].[dbo].[F_DOCENTETE] e
            LEFT JOIN [{db}].[dbo].[F_COLLABORATEUR] co
                ON e.CO_No = co.CO_No
            LEFT JOIN [{db}].[dbo].[P_DEVISE] dev
                ON e.DO_Devise = dev.cbIndice
            WHERE e.DO_Domaine = 1
        """,
    },

    # ═══════════════════════════════════════════════════════════════════════
    # Lignes_des_achats — lignes de documents d'achat
    # ═══════════════════════════════════════════════════════════════════════
    "Lignes_des_achats": {
        "sage_sql": """
            SELECT
                '{societe}'                                      AS [societe],
                l.DL_No                                          AS [N° interne],
                CASE l.DO_Type
                    WHEN 10 THEN 'Demande d''achat'
                    WHEN 11 THEN 'Bon de commande'
                    WHEN 12 THEN 'Préparation de livraison'
                    WHEN 13 THEN 'Bon de livraison'
                    WHEN 14 THEN 'Bon de retour'
                    WHEN 15 THEN 'Bon avoir financier'
                    WHEN 16 THEN 'Facture'
                    WHEN 17 THEN 'Facture comptabilisée'
                    ELSE '' END                                  AS [Type Document],
                e.DO_Tiers                                       AS [Code fournisseur],
                ct.CT_Intitule                                   AS [Intitulé fournisseur],
                ISNULL(l.DO_Piece, '')                           AS [N° Pièce],
                CONVERT(DATETIME, e.DO_Date, 120)                AS [Date],
                CONVERT(DATETIME, e.DO_Date, 120)                AS [Date document],
                CASE
                    WHEN l.DO_Type = 13 THEN l.DO_Piece
                    WHEN l.DO_Type > 13 THEN l.DL_PieceBL
                    ELSE '' END                                  AS [N° Pièce BL],
                CASE
                    WHEN l.DO_Type = 13 THEN l.DO_Date
                    WHEN l.DO_Type > 13 AND l.DL_DateBL > '1900-01-01' THEN l.DL_DateBL
                    ELSE l.DO_Date END                           AS [Date BL],
                CASE l.DO_Type WHEN 11 THEN l.DO_Piece ELSE l.DL_PieceBC END AS [N° Pièce BC],
                CASE
                    WHEN l.DO_Type = 11 THEN l.DO_Date
                    WHEN l.DL_DateBC > '1900-01-01' THEN l.DL_DateBC
                    ELSE l.DO_Date END                           AS [Date BC],
                CASE l.DO_Type WHEN 12 THEN l.DO_Piece ELSE l.DL_PieceBC END AS [N° pièce PL],
                CASE
                    WHEN l.DO_Type = 12 THEN l.DO_Date
                    WHEN l.DL_DatePL > '1900-01-01' THEN l.DL_DatePL
                    ELSE l.DO_Date END                           AS [Date PL],
                l.AR_Ref                                         AS [Code article],
                l.DL_Design                                      AS [Désignation ligne],
                l.DL_Design                                      AS [Désignation],
                cat1.CL_Intitule                                 AS [Catalogue 1],
                cat2.CL_Intitule                                 AS [Catalogue 2],
                cat3.CL_Intitule                                 AS [Catalogue 3],
                cat4.CL_Intitule                                 AS [Catalogue 4],
                g1.G_Intitule                                    AS [Gamme 1],
                g2.G_Intitule                                    AS [Gamme 2],
                CASE
                    WHEN l.DO_Type <> 15 AND l.DL_TRemPied = 0 AND l.DL_TRemExep = 0
                         AND l.DL_TypePL < 2
                    THEN CASE WHEN l.DO_Type IN (14) THEN -l.DL_Qte ELSE l.DL_Qte END
                    ELSE 0 END                                   AS [Quantité],
                l.DL_QtePL                                       AS [Quantité PL],
                l.DL_QteBC                                       AS [Quantité BC],
                l.DL_QteBL                                       AS [Quantité BL],
                l.DL_QteDE                                       AS [Quantité devis],
                l.DL_CMUP                                        AS [CMUP],
                l.DL_PrixUnitaire                                AS [Prix unitaire],
                l.DL_PUTTC                                       AS [Prix unitaire TTC],
                l.DL_PUBC                                        AS [Prix unitaire BC],
                l.DL_PrixRU                                      AS [Prix de revient],
                CASE
                    WHEN l.DO_Type BETWEEN 14 AND 15
                    THEN -l.DL_MontantHT ELSE l.DL_MontantHT END AS [Montant HT Net],
                CASE
                    WHEN l.DO_Type BETWEEN 14 AND 15
                    THEN -l.DL_MontantTTC ELSE l.DL_MontantTTC END AS [Montant TTC Net],
                l.DE_No                                          AS [Code dépôt],
                d.DE_Intitule                                    AS [Intitulé dépôt],
                CONVERT(DATETIME, l.cbCreation, 120)             AS [Date création],
                CONVERT(DATETIME, l.cbModification, 120)         AS [Date modification],
                l.DO_Ref                                         AS [Référence],
                CAST(l.DL_PoidsBrut AS FLOAT)                    AS [Poids brut],
                CAST(l.DL_PoidsNet AS FLOAT)                     AS [Poids net],
                CAST(NULL AS VARCHAR(100))                       AS [Intitulé affaire],
                l.CA_Num                                         AS [Code d'affaire],
                CAST(NULL AS VARCHAR(50))                        AS [N° Série/Lot],
                CAST(l.DL_Taxe1 AS VARCHAR(20))                  AS [Taxe1],
                CAST(l.DL_Taxe2 AS VARCHAR(20))                  AS [Taxe2],
                CAST(l.DL_Taxe3 AS VARCHAR(20))                  AS [Taxe3],
                CASE l.DL_TypeTaux1 WHEN 0 THEN 'Taux %' WHEN 1 THEN 'Montant forfait' WHEN 2 THEN 'Quantité' ELSE '' END AS [Type taux taxe 1],
                CASE l.DL_TypeTaux2 WHEN 0 THEN 'Taux %' WHEN 1 THEN 'Montant forfait' WHEN 2 THEN 'Quantité' ELSE '' END AS [Type taux taxe 2],
                CASE l.DL_TypeTaux3 WHEN 0 THEN 'Taux %' WHEN 1 THEN 'Montant forfait' WHEN 2 THEN 'Quantité' ELSE '' END AS [Type taux taxe 3],
                CASE l.DL_TypeTaxe1 WHEN 0 THEN 'TVA/débit' WHEN 1 THEN 'TVA/Encaissement' WHEN 2 THEN 'TP/HT' WHEN 3 THEN 'TP/TTC' WHEN 4 THEN 'TP/Poids' ELSE '' END AS [Type taxe 1],
                CASE l.DL_TypeTaxe2 WHEN 0 THEN 'TVA/débit' WHEN 1 THEN 'TVA/Encaissement' WHEN 2 THEN 'TP/HT' WHEN 3 THEN 'TP/TTC' WHEN 4 THEN 'TP/Poids' ELSE '' END AS [Type taxe 2],
                CASE l.DL_TypeTaxe3 WHEN 0 THEN 'TVA/débit' WHEN 1 THEN 'TVA/Encaissement' WHEN 2 THEN 'TP/HT' WHEN 3 THEN 'TP/TTC' WHEN 4 THEN 'TP/Poids' ELSE '' END AS [Type taxe 3],
                FORMAT(l.DL_Remise01REM_Valeur, 'P2')            AS [Remise 1],
                FORMAT(l.DL_Remise02REM_Valeur, 'P2')            AS [Remise 2],
                CASE l.DL_Remise01REM_Type WHEN 0 THEN 'Montant' WHEN 1 THEN 'Pourcentage' WHEN 2 THEN 'Quantité' ELSE '' END AS [Type de la remise 1],
                CASE l.DL_Remise02REM_Type WHEN 0 THEN 'Montant' WHEN 1 THEN 'Pourcentage' WHEN 2 THEN 'Quantité' ELSE '' END AS [Type de la remise 2],
                CAST(l.DL_Frais AS FLOAT)                        AS [Frais d'approche],
                l.DL_PUDevise                                    AS [PU Devise],
                CAST(NULL AS VARCHAR(50))                        AS [Colisage],
                CASE l.DL_TNomencl WHEN 0 THEN 'Oui' WHEN 1 THEN 'Non' ELSE '' END AS [Nomenclature],
                CASE l.DL_TRemPied WHEN 0 THEN 'Oui' WHEN 1 THEN 'Non' ELSE '' END AS [Type remise de pied],
                CASE l.DL_TRemExep WHEN 0 THEN 'Oui' WHEN 1 THEN 'Non' ELSE '' END AS [Type remise exceptionnelle],
                CAST(NULL AS VARCHAR(50))                        AS [Conditionnement],
                l.AC_RefClient                                   AS [Référence article client],
                l.DL_FactPoids                                   AS [Article facturé au poids],
                CASE
                    WHEN l.DO_DateLivr < '1900-01-01' THEN NULL
                    ELSE l.DO_DateLivr
                END                                              AS [Date Livraison]
            FROM [{db}].[dbo].[F_DOCLIGNE] l
            INNER JOIN [{db}].[dbo].[F_ARTICLE] fart
                ON l.cbAR_Ref = fart.cbAR_Ref
            INNER JOIN [{db}].[dbo].[F_DOCENTETE] e
                ON l.DO_Type = e.DO_Type AND l.DO_Piece = e.DO_Piece
            INNER JOIN [{db}].[dbo].[F_COMPTET] ct
                ON e.cbDO_Tiers = ct.cbCT_Num
            LEFT OUTER JOIN [{db}].[dbo].[F_DEPOT] d
                ON l.DE_No = d.DE_No
            LEFT OUTER JOIN [{db}].[dbo].[P_GAMME] g1
                ON l.AG_No1 = g1.cbIndice
            LEFT OUTER JOIN [{db}].[dbo].[P_GAMME] g2
                ON l.AG_No2 = g2.cbIndice
            LEFT OUTER JOIN [{db}].[dbo].[F_CATALOGUE] cat1
                ON fart.CL_No1 = cat1.CL_No
            LEFT OUTER JOIN [{db}].[dbo].[F_CATALOGUE] cat2
                ON fart.CL_No2 = cat2.CL_No
            LEFT OUTER JOIN [{db}].[dbo].[F_CATALOGUE] cat3
                ON fart.CL_No3 = cat3.CL_No
            LEFT OUTER JOIN [{db}].[dbo].[F_CATALOGUE] cat4
                ON fart.CL_No4 = cat4.CL_No
            WHERE l.DO_Domaine = 1
              AND l.DL_TRemExep < 2
              AND l.DL_NonLivre = 0
        """,
    },

    # ═══════════════════════════════════════════════════════════════════════
    # Balance_Generale — comptabilité
    # ═══════════════════════════════════════════════════════════════════════
    "Balance_Generale": {
        "sage_sql": """
            SELECT
                ec.CG_Num                                        AS [Compte],
                cg.CG_Intitule                                   AS [Intitulé],
                LEFT(ec.CG_Num, 1)                               AS [Classe],
                SUM(ec.EC_Montant_D)                             AS [Solde Débit],
                SUM(ec.EC_Montant_C)                             AS [Solde Crédit],
                ec.JO_Num                                        AS [Période],
                ec.EC_Intitule                                   AS [Exercice]
            FROM [{db}].[dbo].[F_ECRITUREC] ec
            LEFT JOIN [{db}].[dbo].[F_COMPTEG] cg
                ON ec.CG_Num = cg.CG_Num
            GROUP BY ec.CG_Num, cg.CG_Intitule, LEFT(ec.CG_Num, 1),
                     ec.JO_Num, ec.EC_Intitule
        """,
    },

    # ═══════════════════════════════════════════════════════════════════════
    # Journal_Ecritures — comptabilité détail
    # ═══════════════════════════════════════════════════════════════════════
    "Journal_Ecritures": {
        "sage_sql": """
            SELECT
                ec.JO_Num                                        AS [Journal],
                j.JO_Intitule                                    AS [Libellé journal],
                ec.EC_RefPiece                                   AS [N° pièce],
                ec.EC_Date                                       AS [Date],
                ec.CG_Num                                        AS [Compte],
                cg.CG_Intitule                                   AS [Intitulé compte],
                ec.EC_Intitule                                   AS [Libellé],
                ec.EC_Montant_D                                  AS [Débit],
                ec.EC_Montant_C                                  AS [Crédit],
                ec.CT_Num                                        AS [Code tiers],
                c.CT_Intitule                                    AS [Intitulé tiers],
                ''                                               AS [Devise],
                ec.EC_Lettre                                     AS [Lettrage]
            FROM [{db}].[dbo].[F_ECRITUREC] ec
            LEFT JOIN [{db}].[dbo].[F_COMPTEG] cg
                ON ec.CG_Num = cg.CG_Num
            LEFT JOIN [{db}].[dbo].[F_JOURNAUX] j
                ON ec.JO_Num = j.JO_Num
            LEFT JOIN [{db}].[dbo].[F_COMPTET] c
                ON ec.CT_Num = c.CT_Num
        """,
    },

    # ═══════════════════════════════════════════════════════════════════════
    # Ecritures_Tresorerie — comptabilité trésorerie (comptes banque 51x)
    # ═══════════════════════════════════════════════════════════════════════
    "Ecritures_Tresorerie": {
        "sage_sql": """
            SELECT
                ec.CG_Num                                        AS [Compte banque],
                cg.CG_Intitule                                   AS [Banque],
                ec.EC_Date                                       AS [Date opération],
                ec.EC_Date                                       AS [Date valeur],
                ec.EC_Intitule                                   AS [Libellé],
                ''                                               AS [Type],
                ec.EC_Montant_D                                  AS [Débit],
                ec.EC_Montant_C                                  AS [Crédit],
                0                                                AS [Solde],
                ec.EC_RefPiece                                   AS [Référence],
                CASE WHEN ec.EC_Lettre IS NOT NULL
                          AND ec.EC_Lettre <> ''
                     THEN 'Oui' ELSE 'Non'
                END                                              AS [Rapproché]
            FROM [{db}].[dbo].[F_ECRITUREC] ec
            LEFT JOIN [{db}].[dbo].[F_COMPTEG] cg
                ON ec.CG_Num = cg.CG_Num
            WHERE ec.CG_Num LIKE '51%'
        """,
    },

    # ═══════════════════════════════════════════════════════════════════════
    # BalanceAgee — encours clients vieillis depuis F_ECRITUREC (non lettrées)
    # Colonnes: CLIENTS (=CT_Intitule), Représenant, SOCIETE,
    #           Solde Clôture, Impayés (>30j), 0-30, 31-60, 61-90, 91-120, +120
    # ═══════════════════════════════════════════════════════════════════════
    "BalanceAgee": {
        "sage_sql": """
            SELECT
                e.CT_Intitule                                        AS [CLIENTS ],
                MAX(e.Representant)                                  AS [Représenant],
                '{societe}'                                          AS [SOCIETE],
                CAST(SUM(CASE WHEN e.EC_Sens=0 THEN e.EC_Montant ELSE -e.EC_Montant END)
                    AS DECIMAL(18,2))                                AS [Solde Clôture],
                CAST(SUM(CASE WHEN (e.EC_Lettrage IS NULL OR e.EC_Lettrage='')
                    AND e.EC_Sens=0 AND e.Age_Jours>30
                    THEN e.EC_Montant ELSE 0 END) AS DECIMAL(18,2)) AS [Impayés],
                CAST(SUM(CASE WHEN (e.EC_Lettrage IS NULL OR e.EC_Lettrage='')
                    AND e.EC_Sens=0 AND e.Age_Jours BETWEEN 0 AND 30
                    THEN e.EC_Montant ELSE 0 END) AS DECIMAL(18,2)) AS [0-30],
                CAST(SUM(CASE WHEN (e.EC_Lettrage IS NULL OR e.EC_Lettrage='')
                    AND e.EC_Sens=0 AND e.Age_Jours BETWEEN 31 AND 60
                    THEN e.EC_Montant ELSE 0 END) AS DECIMAL(18,2)) AS [31-60],
                CAST(SUM(CASE WHEN (e.EC_Lettrage IS NULL OR e.EC_Lettrage='')
                    AND e.EC_Sens=0 AND e.Age_Jours BETWEEN 61 AND 90
                    THEN e.EC_Montant ELSE 0 END) AS DECIMAL(18,2)) AS [61-90],
                CAST(SUM(CASE WHEN (e.EC_Lettrage IS NULL OR e.EC_Lettrage='')
                    AND e.EC_Sens=0 AND e.Age_Jours BETWEEN 91 AND 120
                    THEN e.EC_Montant ELSE 0 END) AS DECIMAL(18,2)) AS [91-120],
                CAST(SUM(CASE WHEN (e.EC_Lettrage IS NULL OR e.EC_Lettrage='')
                    AND e.EC_Sens=0 AND e.Age_Jours>120
                    THEN e.EC_Montant ELSE 0 END) AS DECIMAL(18,2)) AS [+120]
            FROM (
                SELECT
                    ec.CT_Num,
                    ct.CT_Intitule,
                    ISNULL(co.CO_Nom, '')                            AS Representant,
                    ec.EC_Sens,
                    ec.EC_Montant,
                    ec.EC_Lettrage,
                    DATEDIFF(DAY, ec.EC_Date, GETDATE())             AS Age_Jours
                FROM [{db}].[dbo].[F_ECRITUREC] ec
                INNER JOIN [{db}].[dbo].[F_COMPTET] ct
                    ON ec.CT_Num = ct.CT_Num AND ct.CT_Type = 0
                LEFT JOIN [{db}].[dbo].[F_COLLABORATEUR] co
                    ON ct.CO_No = co.CO_No
                WHERE ec.CT_Num IS NOT NULL AND ec.CT_Num <> ''
                  AND ec.CG_Num LIKE '34%'
            ) e
            GROUP BY e.CT_Num, e.CT_Intitule
            HAVING SUM(CASE WHEN e.EC_Sens=0 THEN e.EC_Montant ELSE -e.EC_Montant END) > 0
        """,
        "stub": False,
    },

    # Échéances — stub pour Phase 1
    "Echéances_Ventes": {
        "sage_sql": """
            SELECT TOP 0
                '' AS [DB_Caption], '' AS [Code client], '' AS [Intitulé client],
                '' AS [Code tier payeur], '' AS [Inititulé tier payeur],
                '' AS [Type Document], '' AS [N° pièce],
                GETDATE() AS [Date document], GETDATE() AS [Date d'échéance],
                CAST(0 AS DECIMAL(18,2)) AS [Montant échéance],
                CAST(0 AS DECIMAL(18,2)) AS [Montant TTC],
                CAST(0 AS DECIMAL(18,2)) AS [Régler],
                '' AS [Mode de réglement],
                '' AS [Code collaborateur], '' AS [Nom collaborateur],
                '' AS [Prénom collaborateur], '' AS [Charge Recouvr]
        """,
        "stub": True,
    },

    # ═══════════════════════════════════════════════════════════════════════
    # Articles — catalogue articles (famille, prix, stock)
    # ═══════════════════════════════════════════════════════════════════════
    "Articles": {
        "sage_sql": """
            SELECT
                F_ARTICLE.cbMarq AS [Code interne],
                CASE F_ARTICLE.AR_Type
                    WHEN 0 THEN 'Standard'
                    WHEN 1 THEN 'Gamme'
                    WHEN 2 THEN 'Ressource Prestation'
                    WHEN 3 THEN 'Ressource Location'
                END AS [Type Article],
                F_ARTICLE.AR_Ref AS [Code Article],
                F_ARTICLE.AR_Design AS [Désignation Article],
                F_ARTICLE.FA_CodeFamille AS [Code Famille],
                F_FAMILLE.FA_Intitule AS [Intitulé famille],
                F_FAMILLE_1.FA_Intitule AS [Intitulé Famille Centralisatrice],
                P_GAMME.G_Intitule AS [Libellé Gamme 1],
                P_GAMME_1.G_Intitule AS [Libellé Gamme 2],
                F_CATALOGUE.CL_Intitule AS [Catalogue 1],
                F_CATALOGUE_1.CL_Intitule AS [Catalogue 2],
                F_CATALOGUE_2.CL_Intitule AS [Catalogue 3],
                F_CATALOGUE_3.CL_Intitule AS [Catalogue 4],
                ISNULL(P_CONDITIONNEMENT.P_Conditionnement, 'Aucun') AS Conditionnement,
                P_UNITE.U_Intitule AS [Unité Vente],
                CAST(NULL AS NVARCHAR(50)) AS [Libellé Statistique01 A],
                CAST(NULL AS NVARCHAR(50)) AS [Libellé Statistique02 A],
                CAST(NULL AS NVARCHAR(50)) AS [Libellé Statistique03 A],
                CAST(NULL AS NVARCHAR(50)) AS [Libellé Statistique04 A],
                CAST(NULL AS NVARCHAR(50)) AS [Libellé Statistique05 A],
                F_ARTICLE.AR_Stat01 AS [Statistique01 A],
                F_ARTICLE.AR_Stat02 AS [Statistique02 A],
                F_ARTICLE.AR_Stat03 AS [Statistique03 A],
                F_ARTICLE.AR_Stat04 AS [Statistique04 A],
                F_ARTICLE.AR_Stat05 AS [Statistique05 A],
                F_ARTICLE.AR_PrixAch AS [Prix d'achat],
                F_ARTICLE.AR_PUNet AS [Dernier prix d'achat],
                F_ARTICLE.AR_Coef AS Coefficient,
                F_ARTICLE.AR_PrixVen AS [Prix de vente],
                CAST(NULL AS NVARCHAR(50)) AS [Type Prix Vente],
                CASE F_ARTICLE.AR_SuiviStock
                    WHEN 0 THEN 'Aucun' WHEN 1 THEN 'Sérialisé' WHEN 2 THEN 'CMUP'
                    WHEN 3 THEN 'FIFO' WHEN 4 THEN 'LIFO' WHEN 5 THEN 'Par lot'
                END AS [Suivi Stock],
                F_ARTICLE.AR_PoidsNet AS [Poids Net],
                F_ARTICLE.AR_PoidsBrut AS [Poids Brut],
                CAST(NULL AS NVARCHAR(50)) AS [Unité Poids],
                CAST(NULL AS INT) AS [Délai Livraison],
                CAST(NULL AS INT) AS [Garantie],
                CAST(NULL AS NVARCHAR(10)) AS [Article en contremarque],
                CAST(NULL AS NVARCHAR(10)) AS [Vente au débit],
                CAST(NULL AS NVARCHAR(10)) AS [Facturation / poids Net],
                CAST(NULL AS NVARCHAR(10)) AS [Facturation forfaitaire],
                CAST(NULL AS NVARCHAR(10)) AS [Non soumis à l'escompte],
                CAST(NULL AS NVARCHAR(10)) AS [Non impression document],
                CAST(NULL AS NVARCHAR(10)) AS [Hors statistiques],
                CASE F_ARTICLE.AR_Sommeil WHEN 0 THEN 'Actif' WHEN 1 THEN 'En sommeil' END AS [Actif / Sommeil],
                CAST(NULL AS NVARCHAR(10)) AS [Publié sur le site Marchand],
                CAST(NULL AS NVARCHAR(50)) AS [Langue 1],
                CAST(NULL AS NVARCHAR(50)) AS [Langue 2],
                F_ARTICLE.AR_CodeBarre AS [Code Barres],
                CAST(NULL AS NVARCHAR(50)) AS [Code Fiscal],
                CAST(NULL AS NVARCHAR(50)) AS [Pays Origine],
                CAST(NULL AS INT) AS [Délai de sécurité],
                CAST(NULL AS NVARCHAR(255)) AS [Photo],
                CAST(NULL AS VARBINARY(MAX)) AS [BinaryImage],
                F_ARTICLE.cbCreation AS [Date création],
                F_ARTICLE.cbModification AS [Date modification],
                CAST(NULL AS INT) AS [DB_Id],
                '{societe}' AS societe
            FROM [{db}].[dbo].[P_CONDITIONNEMENT] P_CONDITIONNEMENT
            RIGHT OUTER JOIN [{db}].[dbo].[P_UNITE] P_UNITE
            RIGHT OUTER JOIN [{db}].[dbo].[F_CATALOGUE] F_CATALOGUE
            RIGHT OUTER JOIN [{db}].[dbo].[F_ARTICLE] F_ARTICLE
            LEFT OUTER JOIN [{db}].[dbo].[F_FAMILLE] AS F_FAMILLE_1
            RIGHT OUTER JOIN [{db}].[dbo].[F_FAMILLE] F_FAMILLE
                ON F_FAMILLE_1.FA_CodeFamille = F_FAMILLE.FA_Central
                ON F_ARTICLE.FA_CodeFamille = F_FAMILLE.FA_CodeFamille
            LEFT OUTER JOIN [{db}].[dbo].[F_CATALOGUE] AS F_CATALOGUE_3
                ON F_ARTICLE.CL_No4 = F_CATALOGUE_3.CL_No
            LEFT OUTER JOIN [{db}].[dbo].[F_CATALOGUE] AS F_CATALOGUE_2
                ON F_ARTICLE.CL_No3 = F_CATALOGUE_2.CL_No
            LEFT OUTER JOIN [{db}].[dbo].[F_CATALOGUE] AS F_CATALOGUE_1
                ON F_ARTICLE.CL_No2 = F_CATALOGUE_1.CL_No
                ON F_CATALOGUE.CL_No = F_ARTICLE.CL_No1
                ON P_UNITE.cbIndice = F_ARTICLE.AR_UniteVen
                ON P_CONDITIONNEMENT.cbIndice = F_ARTICLE.AR_Condition
            LEFT OUTER JOIN [{db}].[dbo].[P_GAMME] AS P_GAMME_1
                ON F_ARTICLE.AR_Gamme2 = P_GAMME_1.cbIndice
            LEFT OUTER JOIN [{db}].[dbo].[P_GAMME] P_GAMME
                ON F_ARTICLE.AR_Gamme1 = P_GAMME.cbIndice
        """,
    },

    # ═══════════════════════════════════════════════════════════════════════
    # Paiements_Fournisseurs — F_CREGLEMENT + F_REGLECH domain=1 (achats)
    # ═══════════════════════════════════════════════════════════════════════
    "Paiements_Fournisseurs": {
        "sage_sql": """
            SELECT
                rg.CT_NumPayeur                                      AS [Code fournisseur],
                ISNULL(ct.CT_Intitule, rg.CT_NumPayeur)              AS [Intitulé],
                CONVERT(VARCHAR(10), rg.RG_Date, 120)                AS [Date],
                CAST(NULL AS VARCHAR(10))                            AS [Date d'échéance],
                ISNULL(rg.RG_Reference, '')                          AS [Référence],
                ISNULL(rg.RG_Libelle, '')                            AS [Libellé],
                ISNULL(rg.JO_Num, '')                                AS [Code journal],
                ISNULL(j.JO_Intitule, '')                            AS [Journal],
                ISNULL(rg.CG_Num, '')                                AS [Compte générale],
                CAST(rg.RG_No AS VARCHAR(20))                        AS [N° piéce],
                CAST(ISNULL(rg.N_Reglement, 0) AS VARCHAR(10))       AS [Mode réglement],
                rg.RG_Montant                                        AS [Montant],
                CAST(0 AS DECIMAL(18,2))                             AS [solde],
                ''                                                   AS [Devise],
                CASE rg.RG_Valide WHEN 0 THEN 'Non' ELSE 'Oui' END  AS [Valide],
                CASE rg.RG_Impute WHEN 0 THEN 'Non' ELSE 'Oui' END  AS [Impute],
                '{societe}'                                          AS societe
            FROM [{db}].[dbo].[F_CREGLEMENT] rg
            INNER JOIN [{db}].[dbo].[F_REGLECH] re
                ON rg.RG_No = re.RG_No AND re.DO_Domaine = 1
            LEFT JOIN [{db}].[dbo].[F_COMPTET] ct
                ON rg.CT_NumPayeur = ct.CT_Num
            LEFT JOIN [{db}].[dbo].[F_JOURNAUX] j
                ON rg.JO_Num = j.JO_Num
        """,
    },

    # ═══════════════════════════════════════════════════════════════════════
    # Règlements_Clients — F_CREGLEMENT + F_REGLECH domain=0 (ventes)
    # ═══════════════════════════════════════════════════════════════════════
    "Règlements_Clients": {
        "sage_sql": """
            SELECT
                rg.CT_NumPayeur                                      AS [Code client],
                ISNULL(ct.CT_Intitule, rg.CT_NumPayeur)              AS [Intitulé],
                rg.CT_NumPayeur                                      AS [Code client original],
                ISNULL(ct.CT_Intitule, rg.CT_NumPayeur)              AS [Intitulé original],
                CONVERT(VARCHAR(10), rg.RG_Date, 120)                AS [Date],
                CAST(NULL AS VARCHAR(10))                            AS [Date d'échéance],
                ISNULL(rg.RG_Reference, '')                          AS [Référence],
                ISNULL(rg.RG_Libelle, '')                            AS [Libellé],
                ISNULL(rg.JO_Num, '')                                AS [Code journal],
                ISNULL(j.JO_Intitule, '')                            AS [Journal],
                ISNULL(rg.CG_Num, '')                                AS [Compte générale],
                CAST(rg.RG_No AS VARCHAR(20))                        AS [N° piéce],
                CAST(ISNULL(rg.N_Reglement, 0) AS VARCHAR(10))       AS [Mode de règlement],
                rg.RG_Montant                                        AS [Montant],
                CAST(0 AS DECIMAL(18,2))                             AS [solde],
                ''                                                   AS [Devise],
                CASE rg.RG_Valide WHEN 0 THEN 'Non' ELSE 'Oui' END  AS [Valide],
                CASE rg.RG_Impute WHEN 0 THEN 'Non' ELSE 'Oui' END  AS [Impute],
                '{societe}'                                          AS societe
            FROM [{db}].[dbo].[F_CREGLEMENT] rg
            INNER JOIN [{db}].[dbo].[F_REGLECH] re
                ON rg.RG_No = re.RG_No AND re.DO_Domaine = 0
            LEFT JOIN [{db}].[dbo].[F_COMPTET] ct
                ON rg.CT_NumPayeur = ct.CT_Num
            LEFT JOIN [{db}].[dbo].[F_JOURNAUX] j
                ON rg.JO_Num = j.JO_Num
        """,
    },

    # Échéances achats — stub (calcul complexe, même pattern qu'Echéances_Ventes)
    "Echeances_Achats": {
        "sage_sql": """
            SELECT TOP 0
                '' AS [Code fournisseur], '' AS [Intitulé fournisseur],
                '' AS [Code tier payeur], '' AS [Tier payeur],
                '' AS [Type Document], '' AS [N° pièce],
                GETDATE() AS [Date document], GETDATE() AS [Date d'échéance],
                CAST(0 AS DECIMAL(18,2)) AS [Montant TTC],
                CAST(0 AS DECIMAL(18,2)) AS [Montant échéance],
                '' AS [Mode de réglement],
                CAST(0 AS DECIMAL(18,2)) AS [Régler],
                '' AS societe
        """,
        "stub": True,
    },

    # Imputations achats — stub (même pattern qu'Imputation_Factures_Ventes)
    "Imputation_Factures_Achats": {
        "sage_sql": """
            SELECT TOP 0
                '' AS [Code fournisseur], '' AS [Intitulé fournisseur],
                '' AS [Code tier encaisseur], '' AS [Intitulé tier encaisseur],
                '' AS [Type Document], '' AS [N° pièce],
                GETDATE() AS [Date document], GETDATE() AS [Date réglement],
                CAST(0 AS DECIMAL(18,2)) AS [Montant facture TTC],
                CAST(0 AS DECIMAL(18,2)) AS [Montant régler],
                CAST(0 AS DECIMAL(18,2)) AS [Montant réglement],
                '' AS [Mode de réglement], '' AS [Référence], '' AS societe
        """,
        "stub": True,
    },

    # Imputations — stub pour Phase 1
    "Imputation_Factures_Ventes": {
        "sage_sql": """
            SELECT TOP 0
                '' AS [DB], '' AS [DB_Caption], '' AS [Référence],
                '' AS [Libellé], 0 AS [id Réglement],
                GETDATE() AS [Date réglement], GETDATE() AS [Date d'échance],
                0 AS [Id écheance], '' AS [Type Document], '' AS [N° pièce],
                CAST(0 AS DECIMAL(18,2)) AS [Montant facture TTC],
                CAST(0 AS DECIMAL(18,2)) AS [Montant régler],
                GETDATE() AS [Date document], '' AS [Mode de réglement],
                '' AS [Code client], '' AS [Intitulé client],
                CAST(0 AS DECIMAL(18,2)) AS [Montant réglement],
                '' AS [Valorise CA]
        """,
        "stub": True,
    },
}


# Liste des tables connues — utilisée par le détecteur de tables
KNOWN_TABLES = set(SAGE_VIEW_CONFIG.keys())
