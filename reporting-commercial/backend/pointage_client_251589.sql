-- ============================================================
-- POINTAGE CLIENT 251589 — Diagnostic pas à pas (CORRIGE)
-- Echéances_Ventes : [N° Pièce], [Date d'échéance] (sans doubler l'apostrophe dans [])
-- Règlements_Clients : [Date] (pas [Date règlement])
-- ============================================================
DECLARE @client  VARCHAR(50)  = '251589'
DECLARE @dateFin DATETIME     = '12/31/2026'
DECLARE @societe VARCHAR(255) = 'AMM'

-- ─────────────────────────────────────────────────────────────
-- 1. Échéances brutes
--    → vérifie N° internes, types de documents, dates
-- ─────────────────────────────────────────────────────────────
PRINT '=== 1. ECHEANCES BRUTES ==='

SELECT
    ev.[N° interne]              AS [Id_Echeance],
    ev.[N° Pièce]                AS [N° Document],
    ev.[Type Document],
    ev.[Date document],
    ev.[Date d'échéance],
    ev.[Montant échéance],
    DATEDIFF(day, ev.[Date d'échéance], @dateFin) AS [Jours retard]
FROM [Echéances_Ventes] ev
WHERE ev.[Code client] = @client
  AND ev.societe = @societe
  AND ev.[Type Document] LIKE '%facture%'
  AND ev.[Type Document] <> 'Facture d''accompte'
  AND ev.[Type de règlement] <> 'Acompte'
ORDER BY ev.[Date d'échéance]


-- ─────────────────────────────────────────────────────────────
-- 2. Imputations dans Imputation_Factures_Ventes
--    → vérifie si des règlements sont imputés à ce client
-- ─────────────────────────────────────────────────────────────
PRINT '=== 2. IMPUTATIONS (Imputation_Factures_Ventes) ==='

SELECT
    ifv.[Id échéance],
    ifv.[N° pièce]           AS [N° Document],
    ifv.[Code client],
    ifv.[Date règlement],
    ifv.[Date d'échéance],
    ifv.[Montant régler],
    ifv.societe
FROM Imputation_Factures_Ventes ifv
WHERE ifv.[Code client] = @client
  AND ifv.societe = @societe
ORDER BY ifv.[Date règlement]


-- ─────────────────────────────────────────────────────────────
-- 3. Pointage croisé Échéances ↔ Imputations
--    Statut = AUCUNE IMPUTATION → la jointure ne remonte rien
-- ─────────────────────────────────────────────────────────────
PRINT '=== 3. POINTAGE CROISE ==='

SELECT
    ev.[N° interne]                AS [Id_Echeance],
    ev.[N° Pièce]                  AS [N° Document],
    ev.[Date d'échéance],
    ev.[Montant échéance],
    ISNULL(reg.MontantRegle, 0)    AS [Montant Regle],
    ev.[Montant échéance] - ISNULL(reg.MontantRegle, 0) AS [Reste],
    CASE WHEN reg.MontantRegle IS NULL THEN 'AUCUNE IMPUTATION' ELSE 'OK' END AS [Statut]
FROM [Echéances_Ventes] ev
LEFT JOIN (
    SELECT [Id échéance], societe, SUM([Montant régler]) AS MontantRegle
    FROM Imputation_Factures_Ventes
    WHERE [Date règlement] <= @dateFin
      AND [Code client] = @client
    GROUP BY [Id échéance], societe
) reg ON ev.[N° interne] = reg.[Id échéance]
      AND ev.societe = reg.societe
WHERE ev.[Code client] = @client
  AND ev.societe = @societe
  AND ev.[Type Document] LIKE '%facture%'
  AND ev.[Type Document] <> 'Facture d''accompte'
  AND ev.[Type de règlement] <> 'Acompte'
ORDER BY ev.[Date d'échéance]


-- ─────────────────────────────────────────────────────────────
-- 4. Règlements dans Règlements_Clients
--    ATTENTION : la colonne date s'appelle [Date], pas [Date règlement]
-- ─────────────────────────────────────────────────────────────
PRINT '=== 4. REGLEMENTS_CLIENTS ==='

SELECT
    rc.[Code client],
    rc.[Date]                 AS [Date Reglement],
    rc.[Mode de règlement],
    rc.Montant,
    rc.societe
FROM [Règlements_Clients] rc
WHERE rc.[Code client] = @client
  AND rc.societe = @societe
ORDER BY rc.[Date]


-- ─────────────────────────────────────────────────────────────
-- 5. Vérification clé de jointure (N° interne EV vs Id échéance IFV)
--    Si "sans filtre societe" > 0 mais "avec filtre societe" = 0
--    → la valeur de [societe] est différente entre les deux tables
-- ─────────────────────────────────────────────────────────────
PRINT '=== 5. VERIFICATION CLE DE JOINTURE ==='

SELECT
    ev.[N° interne]           AS [Id_Echeance_EV],
    ev.[N° Pièce]             AS [N° Document],
    ev.[Montant échéance],
    (SELECT COUNT(*) FROM Imputation_Factures_Ventes
     WHERE [Id échéance] = ev.[N° interne])            AS [Nb IFV sans filtre societe],
    (SELECT COUNT(*) FROM Imputation_Factures_Ventes
     WHERE [Id échéance] = ev.[N° interne]
       AND societe = ev.societe)                        AS [Nb IFV avec filtre societe],
    (SELECT SUM([Montant régler]) FROM Imputation_Factures_Ventes
     WHERE [Id échéance] = ev.[N° interne]
       AND societe = ev.societe)                        AS [Total regle avec societe]
FROM [Echéances_Ventes] ev
WHERE ev.[Code client] = @client
  AND ev.societe = @societe
  AND ev.[Type Document] LIKE '%facture%'
  AND ev.[Type Document] <> 'Facture d''accompte'
  AND ev.[Type de règlement] <> 'Acompte'
ORDER BY ev.[Date d'échéance]


-- ─────────────────────────────────────────────────────────────
-- 6. Résumé global client
-- ─────────────────────────────────────────────────────────────
PRINT '=== 6. RESUME GLOBAL ==='

SELECT
    ev.[Code client],
    COUNT(*)                                                          AS [Nb Echeances],
    SUM(ev.[Montant échéance])                                        AS [Total Facture],
    ISNULL(SUM(ifv_tot.MontantRegle), 0)                              AS [Total Regle IFV],
    SUM(ev.[Montant échéance]) - ISNULL(SUM(ifv_tot.MontantRegle), 0) AS [Encours Calcule],
    (SELECT SUM(Montant) FROM [Règlements_Clients]
     WHERE [Code client] = @client AND societe = @societe)            AS [Total Reglements_Clients]
FROM [Echéances_Ventes] ev
LEFT JOIN (
    SELECT [Id échéance], societe, SUM([Montant régler]) AS MontantRegle
    FROM Imputation_Factures_Ventes
    WHERE [Date règlement] <= @dateFin
    GROUP BY [Id échéance], societe
) ifv_tot ON ev.[N° interne] = ifv_tot.[Id échéance]
          AND ev.societe = ifv_tot.societe
WHERE ev.[Code client] = @client
  AND ev.societe = @societe
  AND ev.[Type Document] LIKE '%facture%'
  AND ev.[Type Document] <> 'Facture d''accompte'
  AND ev.[Type de règlement] <> 'Acompte'
GROUP BY ev.[Code client]
