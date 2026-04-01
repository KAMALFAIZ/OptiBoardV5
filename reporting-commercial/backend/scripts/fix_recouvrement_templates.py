"""Fix Recouvrement SQL templates to work with DWH schema.

DWH differences from source DB:
- Echéances_Ventes: no [Régler], no [Collaborateur], no [Charge Recouvr], no [Montant TTC]
- [Régler] = SUM of [Montant régler] from Imputation_Factures_Ventes (linked by Id échéance = N° interne)
- Commercial info = from Entête_des_ventes via [N° pièce] JOIN, then [Code représentant] / [Nom représentant]
- [Charge Recouvr] = from Collaborateurs table via Code représentant
- No [Code collaborateur] -> use [Code représentant]
- [Inititulé tier payeur] (typo) -> [Intitulé Tiers payeur] (actual DWH column name, capital T)
- [Code tier payeur] -> [Code tiers payeur] (with 's')
- Règlements_Ventes doesn't exist -> use Règlements_Clients
- [Montant TTC] in Echéances doesn't exist -> use [Montant TTC Net]
"""
import pyodbc

conn_str = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019"
conn = pyodbc.connect(conn_str, autocommit=True)
cursor = conn.cursor()

# New templates adapted to DWH schema
new_templates = {

"DS_BALANCE_AGEE": """SELECT
    e.[Code client] AS [Code Client],
    e.[Intitul\u00e9 client] AS [Client],
    ISNULL(v.[Nom repr\u00e9sentant], '') AS [Commercial],
    ISNULL(co.[Charge Recouvr], '') AS [Charge Recouvrement],
    e.[societe] AS [Societe],
    SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'\u00e9ch\u00e9ance], GETDATE()) <= 0
        THEN e.[Montant \u00e9ch\u00e9ance] - ISNULL(imp.Regle, 0) ELSE 0 END) AS [Non Echu],
    SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'\u00e9ch\u00e9ance], GETDATE()) BETWEEN 1 AND 30
        THEN e.[Montant \u00e9ch\u00e9ance] - ISNULL(imp.Regle, 0) ELSE 0 END) AS [0-30j],
    SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'\u00e9ch\u00e9ance], GETDATE()) BETWEEN 31 AND 60
        THEN e.[Montant \u00e9ch\u00e9ance] - ISNULL(imp.Regle, 0) ELSE 0 END) AS [31-60j],
    SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'\u00e9ch\u00e9ance], GETDATE()) BETWEEN 61 AND 90
        THEN e.[Montant \u00e9ch\u00e9ance] - ISNULL(imp.Regle, 0) ELSE 0 END) AS [61-90j],
    SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'\u00e9ch\u00e9ance], GETDATE()) BETWEEN 91 AND 120
        THEN e.[Montant \u00e9ch\u00e9ance] - ISNULL(imp.Regle, 0) ELSE 0 END) AS [91-120j],
    SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'\u00e9ch\u00e9ance], GETDATE()) > 120
        THEN e.[Montant \u00e9ch\u00e9ance] - ISNULL(imp.Regle, 0) ELSE 0 END) AS [+120j],
    SUM(e.[Montant \u00e9ch\u00e9ance] - ISNULL(imp.Regle, 0)) AS [Total Creance],
    SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'\u00e9ch\u00e9ance], GETDATE()) > 0
        THEN e.[Montant \u00e9ch\u00e9ance] - ISNULL(imp.Regle, 0) ELSE 0 END) AS [Total Echu],
    COUNT(*) AS [Nb Echeances],
    MAX(DATEDIFF(DAY, e.[Date d'\u00e9ch\u00e9ance], GETDATE())) AS [Max Retard Jours]
FROM [\u00c9ch\u00e9ances_Ventes] e
LEFT JOIN (SELECT [Id \u00e9ch\u00e9ance], SUM([Montant r\u00e9gler]) AS Regle
           FROM [Imputation_Factures_Ventes] GROUP BY [Id \u00e9ch\u00e9ance]) imp
    ON e.[N\u00b0 interne] = imp.[Id \u00e9ch\u00e9ance]
LEFT JOIN [Ent\u00eate_des_ventes] v
    ON e.[N\u00b0 Pi\u00e8ce] = v.[N\u00b0 pi\u00e8ce] AND e.[societe] = v.[societe]
LEFT JOIN [Collaborateurs] co
    ON v.[Code repr\u00e9sentant] = co.[Code collaborateur] AND v.[societe] = co.[societe]
WHERE e.[Montant \u00e9ch\u00e9ance] > ISNULL(imp.Regle, 0)
  AND (@societe IS NULL OR e.[societe] = @societe)
GROUP BY e.[Code client], e.[Intitul\u00e9 client],
         v.[Nom repr\u00e9sentant], co.[Charge Recouvr], e.[societe]
ORDER BY [Total Creance] DESC""",

"DS_DSO": """WITH Encours AS (
    SELECT
        e.[Code client],
        e.[Intitul\u00e9 client],
        e.[societe],
        SUM(e.[Montant \u00e9ch\u00e9ance] - ISNULL(imp.Regle, 0)) AS Total_Encours
    FROM [\u00c9ch\u00e9ances_Ventes] e
    LEFT JOIN (SELECT [Id \u00e9ch\u00e9ance], SUM([Montant r\u00e9gler]) AS Regle
               FROM [Imputation_Factures_Ventes] GROUP BY [Id \u00e9ch\u00e9ance]) imp
        ON e.[N\u00b0 interne] = imp.[Id \u00e9ch\u00e9ance]
    WHERE e.[Montant \u00e9ch\u00e9ance] > ISNULL(imp.Regle, 0)
      AND (@societe IS NULL OR e.[societe] = @societe)
    GROUP BY e.[Code client], e.[Intitul\u00e9 client], e.[societe]
),
CA AS (
    SELECT [Code client], [societe],
        SUM([Montant TTC Net]) AS CA_12M
    FROM [\u00c9ch\u00e9ances_Ventes]
    WHERE [Date document] >= DATEADD(MONTH, -12, GETDATE())
      AND (@societe IS NULL OR [societe] = @societe)
    GROUP BY [Code client], [societe]
),
Reglements AS (
    SELECT [Code client], [societe],
        SUM([Montant r\u00e9gler]) AS Total_Regle,
        COUNT(DISTINCT [id R\u00e8glement]) AS Nb_Reglements,
        AVG(DATEDIFF(DAY, [Date document], [Date r\u00e8glement])) AS Delai_Moyen
    FROM [Imputation_Factures_Ventes]
    WHERE [Date r\u00e8glement] >= DATEADD(MONTH, -12, GETDATE())
      AND (@societe IS NULL OR [societe] = @societe)
    GROUP BY [Code client], [societe]
)
SELECT
    enc.[Code client] AS [Code Client],
    enc.[Intitul\u00e9 client] AS [Client],
    enc.[societe] AS [Societe],
    enc.Total_Encours AS [Encours],
    ISNULL(ca.CA_12M, 0) AS [CA 12 Mois],
    ISNULL(reg.Total_Regle, 0) AS [Regle 12 Mois],
    ISNULL(reg.Delai_Moyen, 0) AS [Delai Moyen Paiement],
    ISNULL(reg.Nb_Reglements, 0) AS [Nb Reglements],
    CASE WHEN ISNULL(ca.CA_12M, 0) > 0
        THEN CAST(enc.Total_Encours / (ca.CA_12M / 365.0) AS INT)
        ELSE 0 END AS [DSO Jours]
FROM Encours enc
LEFT JOIN CA ca ON enc.[Code client] = ca.[Code client] AND enc.[societe] = ca.[societe]
LEFT JOIN Reglements reg ON enc.[Code client] = reg.[Code client] AND enc.[societe] = reg.[societe]
ORDER BY enc.Total_Encours DESC""",

"DS_CREANCES_DOUTEUSES": """SELECT
    e.[Code client] AS [Code Client],
    e.[Intitul\u00e9 client] AS [Client],
    ISNULL(v.[Nom repr\u00e9sentant], '') AS [Commercial],
    ISNULL(co.[Charge Recouvr], '') AS [Charge Recouvrement],
    e.[societe] AS [Societe],
    SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'\u00e9ch\u00e9ance], GETDATE()) > 120
        THEN e.[Montant \u00e9ch\u00e9ance] - ISNULL(imp.Regle, 0) ELSE 0 END) AS [Montant +120j],
    SUM(e.[Montant \u00e9ch\u00e9ance] - ISNULL(imp.Regle, 0)) AS [Total Creance],
    CASE WHEN SUM(e.[Montant \u00e9ch\u00e9ance] - ISNULL(imp.Regle, 0)) > 0
        THEN ROUND(100.0 * SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'\u00e9ch\u00e9ance], GETDATE()) > 120
            THEN e.[Montant \u00e9ch\u00e9ance] - ISNULL(imp.Regle, 0) ELSE 0 END)
            / SUM(e.[Montant \u00e9ch\u00e9ance] - ISNULL(imp.Regle, 0)), 1)
        ELSE 0 END AS [% Douteux],
    SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'\u00e9ch\u00e9ance], GETDATE()) > 120 THEN 1 ELSE 0 END) AS [Nb Echeances +120j],
    MAX(DATEDIFF(DAY, e.[Date d'\u00e9ch\u00e9ance], GETDATE())) AS [Max Retard Jours]
FROM [\u00c9ch\u00e9ances_Ventes] e
LEFT JOIN (SELECT [Id \u00e9ch\u00e9ance], SUM([Montant r\u00e9gler]) AS Regle
           FROM [Imputation_Factures_Ventes] GROUP BY [Id \u00e9ch\u00e9ance]) imp
    ON e.[N\u00b0 interne] = imp.[Id \u00e9ch\u00e9ance]
LEFT JOIN [Ent\u00eate_des_ventes] v
    ON e.[N\u00b0 Pi\u00e8ce] = v.[N\u00b0 pi\u00e8ce] AND e.[societe] = v.[societe]
LEFT JOIN [Collaborateurs] co
    ON v.[Code repr\u00e9sentant] = co.[Code collaborateur] AND v.[societe] = co.[societe]
WHERE e.[Montant \u00e9ch\u00e9ance] > ISNULL(imp.Regle, 0)
  AND (@societe IS NULL OR e.[societe] = @societe)
GROUP BY e.[Code client], e.[Intitul\u00e9 client],
         v.[Nom repr\u00e9sentant], co.[Charge Recouvr], e.[societe]
HAVING SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'\u00e9ch\u00e9ance], GETDATE()) > 120
    THEN e.[Montant \u00e9ch\u00e9ance] - ISNULL(imp.Regle, 0) ELSE 0 END) > 0
ORDER BY [Montant +120j] DESC""",

"DS_KPI_RECOUVREMENT": """SELECT
    (SELECT SUM(e.[Montant \u00e9ch\u00e9ance] - ISNULL(imp.Regle, 0))
     FROM [\u00c9ch\u00e9ances_Ventes] e
     LEFT JOIN (SELECT [Id \u00e9ch\u00e9ance], SUM([Montant r\u00e9gler]) AS Regle
                FROM [Imputation_Factures_Ventes] GROUP BY [Id \u00e9ch\u00e9ance]) imp
         ON e.[N\u00b0 interne] = imp.[Id \u00e9ch\u00e9ance]
     WHERE e.[Montant \u00e9ch\u00e9ance] > ISNULL(imp.Regle, 0)) AS [Encours Total],

    (SELECT SUM(e.[Montant \u00e9ch\u00e9ance] - ISNULL(imp.Regle, 0))
     FROM [\u00c9ch\u00e9ances_Ventes] e
     LEFT JOIN (SELECT [Id \u00e9ch\u00e9ance], SUM([Montant r\u00e9gler]) AS Regle
                FROM [Imputation_Factures_Ventes] GROUP BY [Id \u00e9ch\u00e9ance]) imp
         ON e.[N\u00b0 interne] = imp.[Id \u00e9ch\u00e9ance]
     WHERE e.[Montant \u00e9ch\u00e9ance] > ISNULL(imp.Regle, 0)
       AND e.[Date d'\u00e9ch\u00e9ance] >= GETDATE()) AS [A Echoir],

    (SELECT SUM(e.[Montant \u00e9ch\u00e9ance] - ISNULL(imp.Regle, 0))
     FROM [\u00c9ch\u00e9ances_Ventes] e
     LEFT JOIN (SELECT [Id \u00e9ch\u00e9ance], SUM([Montant r\u00e9gler]) AS Regle
                FROM [Imputation_Factures_Ventes] GROUP BY [Id \u00e9ch\u00e9ance]) imp
         ON e.[N\u00b0 interne] = imp.[Id \u00e9ch\u00e9ance]
     WHERE e.[Montant \u00e9ch\u00e9ance] > ISNULL(imp.Regle, 0)
       AND e.[Date d'\u00e9ch\u00e9ance] < GETDATE()) AS [Echu],

    (SELECT COUNT(*)
     FROM [\u00c9ch\u00e9ances_Ventes] e
     LEFT JOIN (SELECT [Id \u00e9ch\u00e9ance], SUM([Montant r\u00e9gler]) AS Regle
                FROM [Imputation_Factures_Ventes] GROUP BY [Id \u00e9ch\u00e9ance]) imp
         ON e.[N\u00b0 interne] = imp.[Id \u00e9ch\u00e9ance]
     WHERE e.[Montant \u00e9ch\u00e9ance] > ISNULL(imp.Regle, 0)
       AND e.[Date d'\u00e9ch\u00e9ance] < GETDATE()) AS [Nb Echeances Retard],

    (SELECT COUNT(DISTINCT e.[Code client])
     FROM [\u00c9ch\u00e9ances_Ventes] e
     LEFT JOIN (SELECT [Id \u00e9ch\u00e9ance], SUM([Montant r\u00e9gler]) AS Regle
                FROM [Imputation_Factures_Ventes] GROUP BY [Id \u00e9ch\u00e9ance]) imp
         ON e.[N\u00b0 interne] = imp.[Id \u00e9ch\u00e9ance]
     WHERE e.[Montant \u00e9ch\u00e9ance] > ISNULL(imp.Regle, 0)
       AND e.[Date d'\u00e9ch\u00e9ance] < GETDATE()) AS [Nb Clients Retard],

    (SELECT SUM([Montant r\u00e9gler])
     FROM [Imputation_Factures_Ventes]
     WHERE [Date r\u00e8glement] >= DATEADD(MONTH, -1, GETDATE())) AS [Reglements Mois],

    (SELECT AVG(DATEDIFF(DAY, e.[Date d'\u00e9ch\u00e9ance], GETDATE()))
     FROM [\u00c9ch\u00e9ances_Ventes] e
     LEFT JOIN (SELECT [Id \u00e9ch\u00e9ance], SUM([Montant r\u00e9gler]) AS Regle
                FROM [Imputation_Factures_Ventes] GROUP BY [Id \u00e9ch\u00e9ance]) imp
         ON e.[N\u00b0 interne] = imp.[Id \u00e9ch\u00e9ance]
     WHERE e.[Montant \u00e9ch\u00e9ance] > ISNULL(imp.Regle, 0)
       AND e.[Date d'\u00e9ch\u00e9ance] < GETDATE()) AS [Retard Moyen Jours]""",

"DS_ECHEANCES_NON_REGLEES": """SELECT
    e.[societe] AS [Societe],
    e.[Code client] AS [Code Client],
    e.[Intitul\u00e9 client] AS [Client],
    e.[Code tiers payeur] AS [Code Tier Payeur],
    e.[Intitul\u00e9 Tiers payeur] AS [Tier Payeur],
    e.[N\u00b0 Pi\u00e8ce] AS [Num Piece],
    e.[Date document] AS [Date Document],
    e.[Date d'\u00e9ch\u00e9ance] AS [Date Echeance],
    e.[Montant \u00e9ch\u00e9ance] AS [Montant Echeance],
    ISNULL(imp.Regle, 0) AS [Montant Regle],
    e.[Montant \u00e9ch\u00e9ance] - ISNULL(imp.Regle, 0) AS [Reste A Regler],
    e.[Mode de r\u00e8glement] AS [Mode Reglement],
    ISNULL(v.[Code repr\u00e9sentant], '') AS [Code Commercial],
    ISNULL(v.[Nom repr\u00e9sentant], '') AS [Commercial],
    ISNULL(co.[Charge Recouvr], '') AS [Charge Recouvrement],
    DATEDIFF(DAY, e.[Date d'\u00e9ch\u00e9ance], GETDATE()) AS [Jours Retard],
    CASE
        WHEN DATEDIFF(DAY, e.[Date d'\u00e9ch\u00e9ance], GETDATE()) <= 0 THEN 'A echoir'
        WHEN DATEDIFF(DAY, e.[Date d'\u00e9ch\u00e9ance], GETDATE()) <= 30 THEN '0-30 jours'
        WHEN DATEDIFF(DAY, e.[Date d'\u00e9ch\u00e9ance], GETDATE()) <= 60 THEN '31-60 jours'
        WHEN DATEDIFF(DAY, e.[Date d'\u00e9ch\u00e9ance], GETDATE()) <= 90 THEN '61-90 jours'
        WHEN DATEDIFF(DAY, e.[Date d'\u00e9ch\u00e9ance], GETDATE()) <= 120 THEN '91-120 jours'
        ELSE '+120 jours'
    END AS [Tranche Age]
FROM [\u00c9ch\u00e9ances_Ventes] e
LEFT JOIN (SELECT [Id \u00e9ch\u00e9ance], SUM([Montant r\u00e9gler]) AS Regle
           FROM [Imputation_Factures_Ventes] GROUP BY [Id \u00e9ch\u00e9ance]) imp
    ON e.[N\u00b0 interne] = imp.[Id \u00e9ch\u00e9ance]
LEFT JOIN [Ent\u00eate_des_ventes] v
    ON e.[N\u00b0 Pi\u00e8ce] = v.[N\u00b0 pi\u00e8ce] AND e.[societe] = v.[societe]
LEFT JOIN [Collaborateurs] co
    ON v.[Code repr\u00e9sentant] = co.[Code collaborateur] AND v.[societe] = co.[societe]
WHERE e.[Montant \u00e9ch\u00e9ance] > ISNULL(imp.Regle, 0)
  AND (@societe IS NULL OR e.[societe] = @societe)
ORDER BY [Reste A Regler] DESC""",

"DS_ECHEANCES_PAR_CLIENT": """SELECT
    e.[Code client] AS [Code Client],
    e.[Intitul\u00e9 client] AS [Client],
    e.[societe] AS [Societe],
    COUNT(*) AS [Nb Echeances],
    SUM(e.[Montant \u00e9ch\u00e9ance]) AS [Total Echeances],
    SUM(ISNULL(imp.Regle, 0)) AS [Total Regle],
    SUM(e.[Montant \u00e9ch\u00e9ance] - ISNULL(imp.Regle, 0)) AS [Reste A Regler],
    SUM(CASE WHEN e.[Date d'\u00e9ch\u00e9ance] >= GETDATE()
        THEN e.[Montant \u00e9ch\u00e9ance] - ISNULL(imp.Regle, 0) ELSE 0 END) AS [A Echoir],
    SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'\u00e9ch\u00e9ance], GETDATE()) BETWEEN 1 AND 30
        THEN e.[Montant \u00e9ch\u00e9ance] - ISNULL(imp.Regle, 0) ELSE 0 END) AS [0-30j],
    SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'\u00e9ch\u00e9ance], GETDATE()) BETWEEN 31 AND 60
        THEN e.[Montant \u00e9ch\u00e9ance] - ISNULL(imp.Regle, 0) ELSE 0 END) AS [31-60j],
    SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'\u00e9ch\u00e9ance], GETDATE()) BETWEEN 61 AND 90
        THEN e.[Montant \u00e9ch\u00e9ance] - ISNULL(imp.Regle, 0) ELSE 0 END) AS [61-90j],
    SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'\u00e9ch\u00e9ance], GETDATE()) BETWEEN 91 AND 120
        THEN e.[Montant \u00e9ch\u00e9ance] - ISNULL(imp.Regle, 0) ELSE 0 END) AS [91-120j],
    SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'\u00e9ch\u00e9ance], GETDATE()) > 120
        THEN e.[Montant \u00e9ch\u00e9ance] - ISNULL(imp.Regle, 0) ELSE 0 END) AS [+120j],
    MAX(e.[Date d'\u00e9ch\u00e9ance]) AS [Derniere Echeance],
    MAX(DATEDIFF(DAY, e.[Date d'\u00e9ch\u00e9ance], GETDATE())) AS [Max Jours Retard]
FROM [\u00c9ch\u00e9ances_Ventes] e
LEFT JOIN (SELECT [Id \u00e9ch\u00e9ance], SUM([Montant r\u00e9gler]) AS Regle
           FROM [Imputation_Factures_Ventes] GROUP BY [Id \u00e9ch\u00e9ance]) imp
    ON e.[N\u00b0 interne] = imp.[Id \u00e9ch\u00e9ance]
WHERE e.[Montant \u00e9ch\u00e9ance] > ISNULL(imp.Regle, 0)
  AND (@societe IS NULL OR e.[societe] = @societe)
GROUP BY e.[Code client], e.[Intitul\u00e9 client], e.[societe]
ORDER BY [Reste A Regler] DESC""",

"DS_ECHEANCES_PAR_COMMERCIAL": """SELECT
    ISNULL(v.[Code repr\u00e9sentant], 'N/A') AS [Code Commercial],
    ISNULL(v.[Nom repr\u00e9sentant], 'Non affect\u00e9') AS [Commercial],
    ISNULL(co.[Charge Recouvr], '') AS [Charge Recouvrement],
    COUNT(DISTINCT e.[Code client]) AS [Nb Clients],
    COUNT(*) AS [Nb Echeances],
    SUM(e.[Montant \u00e9ch\u00e9ance] - ISNULL(imp.Regle, 0)) AS [Encours Total],
    SUM(CASE WHEN e.[Date d'\u00e9ch\u00e9ance] >= GETDATE()
        THEN e.[Montant \u00e9ch\u00e9ance] - ISNULL(imp.Regle, 0) ELSE 0 END) AS [A Echoir],
    SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'\u00e9ch\u00e9ance], GETDATE()) BETWEEN 1 AND 30
        THEN e.[Montant \u00e9ch\u00e9ance] - ISNULL(imp.Regle, 0) ELSE 0 END) AS [0-30j],
    SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'\u00e9ch\u00e9ance], GETDATE()) BETWEEN 31 AND 60
        THEN e.[Montant \u00e9ch\u00e9ance] - ISNULL(imp.Regle, 0) ELSE 0 END) AS [31-60j],
    SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'\u00e9ch\u00e9ance], GETDATE()) BETWEEN 61 AND 90
        THEN e.[Montant \u00e9ch\u00e9ance] - ISNULL(imp.Regle, 0) ELSE 0 END) AS [61-90j],
    SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'\u00e9ch\u00e9ance], GETDATE()) BETWEEN 91 AND 120
        THEN e.[Montant \u00e9ch\u00e9ance] - ISNULL(imp.Regle, 0) ELSE 0 END) AS [91-120j],
    SUM(CASE WHEN DATEDIFF(DAY, e.[Date d'\u00e9ch\u00e9ance], GETDATE()) > 120
        THEN e.[Montant \u00e9ch\u00e9ance] - ISNULL(imp.Regle, 0) ELSE 0 END) AS [+120j]
FROM [\u00c9ch\u00e9ances_Ventes] e
LEFT JOIN (SELECT [Id \u00e9ch\u00e9ance], SUM([Montant r\u00e9gler]) AS Regle
           FROM [Imputation_Factures_Ventes] GROUP BY [Id \u00e9ch\u00e9ance]) imp
    ON e.[N\u00b0 interne] = imp.[Id \u00e9ch\u00e9ance]
LEFT JOIN [Ent\u00eate_des_ventes] v
    ON e.[N\u00b0 Pi\u00e8ce] = v.[N\u00b0 pi\u00e8ce] AND e.[societe] = v.[societe]
LEFT JOIN [Collaborateurs] co
    ON v.[Code repr\u00e9sentant] = co.[Code collaborateur] AND v.[societe] = co.[societe]
WHERE e.[Montant \u00e9ch\u00e9ance] > ISNULL(imp.Regle, 0)
  AND (@societe IS NULL OR e.[societe] = @societe)
GROUP BY v.[Code repr\u00e9sentant], v.[Nom repr\u00e9sentant], co.[Charge Recouvr]
ORDER BY [Encours Total] DESC""",

"DS_ECHEANCES_PAR_MODE": """SELECT
    e.[Mode de r\u00e8glement] AS [Mode Reglement],
    e.[Code mode r\u00e8glement] AS [Code Mode],
    COUNT(*) AS [Nb Echeances],
    SUM(e.[Montant \u00e9ch\u00e9ance]) AS [Total Echeances],
    SUM(e.[Montant \u00e9ch\u00e9ance] - ISNULL(imp.Regle, 0)) AS [Reste A Regler],
    AVG(DATEDIFF(DAY, e.[Date d'\u00e9ch\u00e9ance], GETDATE())) AS [Retard Moyen Jours]
FROM [\u00c9ch\u00e9ances_Ventes] e
LEFT JOIN (SELECT [Id \u00e9ch\u00e9ance], SUM([Montant r\u00e9gler]) AS Regle
           FROM [Imputation_Factures_Ventes] GROUP BY [Id \u00e9ch\u00e9ance]) imp
    ON e.[N\u00b0 interne] = imp.[Id \u00e9ch\u00e9ance]
WHERE e.[Montant \u00e9ch\u00e9ance] > ISNULL(imp.Regle, 0)
  AND (@societe IS NULL OR e.[societe] = @societe)
GROUP BY e.[Mode de r\u00e8glement], e.[Code mode r\u00e8glement]
ORDER BY [Reste A Regler] DESC""",

"DS_ECHEANCES_A_ECHOIR": """SELECT
    e.[societe] AS [Societe],
    e.[Code client] AS [Code Client],
    e.[Intitul\u00e9 client] AS [Client],
    e.[N\u00b0 Pi\u00e8ce] AS [Num Piece],
    e.[Date document] AS [Date Document],
    e.[Date d'\u00e9ch\u00e9ance] AS [Date Echeance],
    e.[Montant \u00e9ch\u00e9ance] - ISNULL(imp.Regle, 0) AS [Montant A Regler],
    e.[Mode de r\u00e8glement] AS [Mode Reglement],
    ISNULL(v.[Nom repr\u00e9sentant], '') AS [Commercial],
    DATEDIFF(DAY, GETDATE(), e.[Date d'\u00e9ch\u00e9ance]) AS [Jours Avant Echeance],
    CASE
        WHEN DATEDIFF(DAY, GETDATE(), e.[Date d'\u00e9ch\u00e9ance]) <= 7 THEN 'Urgent'
        WHEN DATEDIFF(DAY, GETDATE(), e.[Date d'\u00e9ch\u00e9ance]) <= 30 THEN 'Proche'
        ELSE 'Normal'
    END AS [Urgence]
FROM [\u00c9ch\u00e9ances_Ventes] e
LEFT JOIN (SELECT [Id \u00e9ch\u00e9ance], SUM([Montant r\u00e9gler]) AS Regle
           FROM [Imputation_Factures_Ventes] GROUP BY [Id \u00e9ch\u00e9ance]) imp
    ON e.[N\u00b0 interne] = imp.[Id \u00e9ch\u00e9ance]
LEFT JOIN [Ent\u00eate_des_ventes] v
    ON e.[N\u00b0 Pi\u00e8ce] = v.[N\u00b0 pi\u00e8ce] AND e.[societe] = v.[societe]
WHERE e.[Montant \u00e9ch\u00e9ance] > ISNULL(imp.Regle, 0)
  AND e.[Date d'\u00e9ch\u00e9ance] >= GETDATE()
  AND (@societe IS NULL OR e.[societe] = @societe)
ORDER BY e.[Date d'\u00e9ch\u00e9ance] ASC""",

"DS_REGLEMENTS_PAR_PERIODE": """SELECT
    YEAR([Date r\u00e8glement]) AS [Annee],
    MONTH([Date r\u00e8glement]) AS [Mois],
    FORMAT([Date r\u00e8glement], 'yyyy-MM') AS [Periode],
    COUNT(DISTINCT [id R\u00e8glement]) AS [Nb Reglements],
    SUM([Montant r\u00e9gler]) AS [Total Reglements],
    COUNT(DISTINCT [Code client]) AS [Nb Clients],
    AVG(DATEDIFF(DAY, [Date document], [Date r\u00e8glement])) AS [Delai Moyen Jours]
FROM [Imputation_Factures_Ventes]
WHERE (@societe IS NULL OR [societe] = @societe)
GROUP BY YEAR([Date r\u00e8glement]), MONTH([Date r\u00e8glement]), FORMAT([Date r\u00e8glement], 'yyyy-MM')
ORDER BY [Annee] DESC, [Mois] DESC""",

"DS_REGLEMENTS_PAR_CLIENT": """SELECT
    [Code client] AS [Code Client],
    [Intitul\u00e9 client] AS [Client],
    [societe] AS [Societe],
    COUNT(DISTINCT [id R\u00e8glement]) AS [Nb Reglements],
    SUM([Montant r\u00e9gler]) AS [Total Regle],
    MIN([Date r\u00e8glement]) AS [Premier Reglement],
    MAX([Date r\u00e8glement]) AS [Dernier Reglement],
    AVG(DATEDIFF(DAY, [Date document], [Date r\u00e8glement])) AS [Delai Moyen Jours]
FROM [Imputation_Factures_Ventes]
WHERE (@societe IS NULL OR [societe] = @societe)
GROUP BY [Code client], [Intitul\u00e9 client], [societe]
ORDER BY [Total Regle] DESC""",

"DS_REGLEMENTS_PAR_MODE": """SELECT
    [Mode de r\u00e8glement] AS [Mode Reglement],
    COUNT(DISTINCT [id R\u00e8glement]) AS [Nb Reglements],
    SUM([Montant r\u00e9gler]) AS [Total Regle],
    COUNT(DISTINCT [Code client]) AS [Nb Clients],
    AVG(DATEDIFF(DAY, [Date document], [Date r\u00e8glement])) AS [Delai Moyen Jours]
FROM [Imputation_Factures_Ventes]
WHERE (@societe IS NULL OR [societe] = @societe)
GROUP BY [Mode de r\u00e8glement]
ORDER BY [Total Regle] DESC""",

"DS_FACTURES_NON_REGLEES": """SELECT
    e.[societe] AS [Societe],
    e.[Code client] AS [Code Client],
    e.[Intitul\u00e9 client] AS [Client],
    e.[Type Document],
    e.[N\u00b0 Pi\u00e8ce] AS [Num Piece],
    e.[Date document] AS [Date Document],
    e.[Montant TTC Net] AS [Montant TTC],
    ISNULL(imp.Regle, 0) AS [Montant Regle],
    e.[Montant TTC Net] - ISNULL(imp.Regle, 0) AS [Reste A Regler],
    DATEDIFF(DAY, e.[Date document], GETDATE()) AS [Age Jours]
FROM [\u00c9ch\u00e9ances_Ventes] e
LEFT JOIN (SELECT [Id \u00e9ch\u00e9ance], SUM([Montant r\u00e9gler]) AS Regle
           FROM [Imputation_Factures_Ventes] GROUP BY [Id \u00e9ch\u00e9ance]) imp
    ON e.[N\u00b0 interne] = imp.[Id \u00e9ch\u00e9ance]
WHERE e.[Montant TTC Net] > ISNULL(imp.Regle, 0)
  AND e.[Type Document] IN ('Facture', 'Facture comptabilis\u00e9e')
  AND (@societe IS NULL OR e.[societe] = @societe)
ORDER BY [Reste A Regler] DESC""",

}

print(f"Updating {len(new_templates)} Recouvrement SQL templates...\n")

ok = 0
for code, new_query in new_templates.items():
    cursor.execute("SELECT id FROM APP_DataSources_Templates WHERE code = ?", (code,))
    row = cursor.fetchone()
    if row:
        cursor.execute("UPDATE APP_DataSources_Templates SET query_template = ? WHERE id = ?", (new_query, row.id))
        print(f"  OK: {code} (id={row.id})")
        ok += 1
    else:
        print(f"  NOT FOUND: {code}")

cursor.close()
conn.close()
print(f"\nDone: {ok}/{len(new_templates)} templates updated")
