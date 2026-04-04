"""
Configuration des vues Sage Direct
====================================
Chaque entrée mappe une vue/table DWH vers une requête Sage
qui produit les MEMES colonnes que la vue DWH.

Le placeholder {db} est remplacé par le nom de la base Sage (ex: ESSAIDI2022).
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
                ISNULL(a.FA_CodeFamille, '')                     AS [Catalogue 1],
                c.CT_Intitule                                    AS [Intitulé tiers],
                e.DO_Tiers                                       AS [Code tiers],
                c.CT_Intitule                                    AS [Intitulé client]
            FROM [{db}].[dbo].[F_DOCLIGNE] l
            INNER JOIN [{db}].[dbo].[F_DOCENTETE] e
                ON l.DO_Piece = e.DO_Piece AND l.DO_Type = e.DO_Type
            LEFT JOIN [{db}].[dbo].[F_ARTICLE] a
                ON l.AR_Ref = a.AR_Ref
            LEFT JOIN [{db}].[dbo].[F_COMPTET] c
                ON e.DO_Tiers = c.CT_Num
            LEFT JOIN [{db}].[dbo].[F_COLLABORATEUR] co
                ON e.CO_No = co.CO_No
            WHERE e.DO_Type IN (3, 6, 7, 12, 13, 14, 15)
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
                c.CT_Risque                                      AS [Risque client],
                c.CT_Encours                                     AS [Encours de l'autorisation],
                c.CT_Assession                                   AS [Assurance],
                c.CT_Telephone                                   AS [Téléphone],
                c.CT_Email                                       AS [Email],
                c.CT_Adresse                                     AS [Adresse],
                c.CT_Ville                                       AS [Ville],
                ''                                               AS [ICE_],
                ''                                               AS [RC_],
                ''                                               AS [Capital_],
                ''                                               AS [Forme juridique_],
                c.CT_DateCreate                                  AS [Date de création]
            FROM [{db}].[dbo].[F_COMPTET] c
            LEFT JOIN [{db}].[dbo].[F_COLLABORATEUR] co
                ON c.CO_No = co.CO_No
            WHERE c.CT_Type = 0
        """,
    },

    # ═══════════════════════════════════════════════════════════════════════
    # Entête_des_ventes — documents vente (factures, avoirs, BL)
    # ═══════════════════════════════════════════════════════════════════════
    "Entête_des_ventes": {
        "sage_sql": """
            SELECT
                '{societe}'                                      AS [DB_Caption],
                CASE e.DO_Type
                    WHEN 3  THEN 'Bon de livraison'
                    WHEN 6  THEN 'Facture'
                    WHEN 7  THEN 'Avoir'
                    ELSE 'Type ' + CAST(e.DO_Type AS VARCHAR(5))
                END                                              AS [Type Document],
                ISNULL(e.DO_Souche, 0)                           AS [Souche],
                e.DO_Piece                                       AS [N° pièce],
                CONVERT(VARCHAR(10), e.DO_Date, 120)             AS [Date],
                e.DO_TotalHT                                     AS [Montant HT],
                e.DO_TotalTTC                                    AS [Montant TTC],
                0                                                AS [Montant réglé],
                e.DO_Statut                                      AS [Statut],
                ''                                               AS [Etat],
                e.CO_No                                          AS [Code représentant],
                ISNULL(co.CO_Prenom + ' ' + co.CO_Nom,
                       CAST(e.CO_No AS VARCHAR(20)))             AS [Nom représentant]
            FROM [{db}].[dbo].[F_DOCENTETE] e
            LEFT JOIN [{db}].[dbo].[F_COLLABORATEUR] co
                ON e.CO_No = co.CO_No
            WHERE e.DO_Type IN (3, 6, 7)
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
    # BalanceAgee — non supporté en Sage Direct (calcul complexe)
    # → retourne un dataset vide avec les bonnes colonnes
    # ═══════════════════════════════════════════════════════════════════════
    "BalanceAgee": {
        "sage_sql": """
            SELECT TOP 0
                '' AS [CLIENTS ],
                '' AS [Représenant],
                '' AS [SOCIETE],
                CAST(0 AS DECIMAL(18,2)) AS [Solde Clôture],
                CAST(0 AS DECIMAL(18,2)) AS [Impayés],
                CAST(0 AS DECIMAL(18,2)) AS [0-30],
                CAST(0 AS DECIMAL(18,2)) AS [31-60],
                CAST(0 AS DECIMAL(18,2)) AS [61-90],
                CAST(0 AS DECIMAL(18,2)) AS [91-120],
                CAST(0 AS DECIMAL(18,2)) AS [+120]
        """,
        "stub": True,
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
