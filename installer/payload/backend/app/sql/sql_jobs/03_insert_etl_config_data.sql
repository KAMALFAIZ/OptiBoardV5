-- Configuration ETL : tables à synchroniser depuis Sage vers le DWH client
-- Exécuter sur la base OptiBoard_SaaS (centrale)
-- Les entrées avec dwh_code='*' s'appliquent à tous les DWH

-- ──────────────────────────────────────────────────────────────
-- Tables existantes (standard)
-- ──────────────────────────────────────────────────────────────

-- Chiffre d'Affaires (priorité haute)
MERGE APP_ETL_Tables AS target
USING (VALUES
    ('*', 'F_DOCENTETE + F_DOCLIGNE',  'DashBoard_CA',           1, 10),
    ('*', 'F_CREGLEMENT',              'Imputation_Factures_Ventes', 1, 20),
    ('*', 'F_ECHEANCECLIENT',          'Echéances_Ventes',        1, 21),
    ('*', 'F_ECHEANCEFOURNISSEUR',     'Echeances_Achats',        1, 22),
    ('*', 'F_REGLEMENTVENTE',         'Paiements_Clients',        1, 25),
    ('*', 'F_REGLEMENTA',             'Paiements_Fournisseurs',   1, 26),
    ('*', 'F_COMPTET',                'Clients',                  1, 30),
    ('*', 'F_COMPTEF',                'Fournisseurs',             1, 31),
    ('*', 'F_ARTICLE',                'Articles',                 1, 35),
    ('*', 'F_MVTSTOCK',               'Mouvement_stock',          1, 40),
    ('*', 'F_ECRITURED',              'Ecritures_Comptables',     1, 45),
    ('*', 'F_BALANCE',                'BalanceAgee',              1, 46),
    ('*', 'F_DOCENTETEA + F_DOCLIGNEAC', 'Entête_des_achats',   1, 47)
) AS source (dwh_code, table_source, table_dest, actif, priorite)
ON target.dwh_code = source.dwh_code AND target.table_dest = source.table_dest
WHEN NOT MATCHED THEN
    INSERT (dwh_code, table_source, table_dest, actif, priorite)
    VALUES (source.dwh_code, source.table_source, source.table_dest, source.actif, source.priorite);

-- ──────────────────────────────────────────────────────────────
-- Tables Comptabilité Analytique (Phase 4)
-- ──────────────────────────────────────────────────────────────

MERGE APP_ETL_Tables AS target
USING (VALUES
    ('*', 'F_ANALCPTA',  'Axes_Analytiques',      1, 50),
    ('*', 'F_CENTREAN',  'Centres_Analytiques',   1, 51),
    ('*', 'F_ECRITUREA', 'Ecritures_Analytiques', 1, 52),
    ('*', 'F_BUDGETA',   'Budgets_Analytiques',   1, 53)
) AS source (dwh_code, table_source, table_dest, actif, priorite)
ON target.dwh_code = source.dwh_code AND target.table_dest = source.table_dest
WHEN NOT MATCHED THEN
    INSERT (dwh_code, table_source, table_dest, actif, priorite)
    VALUES (source.dwh_code, source.table_source, source.table_dest, source.actif, source.priorite);

PRINT 'ETL config data insérée avec succès (standard + analytique)';
