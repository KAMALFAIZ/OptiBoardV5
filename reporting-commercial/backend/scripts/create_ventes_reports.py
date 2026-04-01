"""
=============================================================================
  CREATE ALL 35 VENTES REPORTS - OptiBoard
  - 7 Documents Ventes (GridView)
  - 13 Analyses Ventes (8 Pivot-style + 5 Dashboard-style as GridView)
  - 15 Rapports Avances

  Base JOIN:
    Lignes_des_ventes li
    INNER JOIN Entete_des_ventes en
      ON li.societe = en.societe
      AND li.[Type Document] = en.[Type Document]
      AND li.[N° Piece] = en.[N° piece]

  Business rules:
    - CA = WHERE li.[Valorise CA] = 'Oui'
    - @societe filter on li.[societe]
    - @dateDebut / @dateFin on li.[Date BL] (date livraison = date reelle d'activite)
=============================================================================
"""
import pyodbc, json

conn_str = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019"
conn = pyodbc.connect(conn_str, autocommit=True)
cursor = conn.cursor()

# ===========================
#  COMMON SQL FRAGMENTS
# ===========================
BASE_JOIN = """FROM [Lignes_des_ventes] li
INNER JOIN [Ent\u00eate_des_ventes] en
    ON li.[societe] = en.[societe]
    AND li.[Type Document] = en.[Type Document]
    AND li.[N\u00b0 Pi\u00e8ce] = en.[N\u00b0 pi\u00e8ce]"""

CA_FILTER = "li.[Valorise CA] = 'Oui'"

DATE_FILTER = "li.[Date BL] BETWEEN @dateDebut AND @dateFin"

SOCIETE_FILTER = "(@societe IS NULL OR li.[societe] = @societe)"

COMMERCIAL_FILTER = "(@commercial IS NULL OR en.[Nom représentant] = @commercial)"

WHERE_CA = f"WHERE {CA_FILTER} AND {DATE_FILTER} AND {SOCIETE_FILTER} AND {COMMERCIAL_FILTER}"

WHERE_ALL = f"WHERE {DATE_FILTER} AND {SOCIETE_FILTER} AND {COMMERCIAL_FILTER}"

# =============================================================================
#  DATASOURCE TEMPLATES
# =============================================================================
templates = []

# =========================================================
#  1. DOCUMENTS VENTES (7 rapports Grid)
# =========================================================

# --- 1. Factures de Ventes ---
templates.append(("DS_VTE_FACTURES", "Factures de Ventes", f"""SELECT
    li.[societe] AS [Societe],
    li.[Type Document],
    li.[N\u00b0 Pi\u00e8ce] AS [Num Piece],
    li.[Date document] AS [Date Document],
    li.[Code client] AS [Code Client],
    li.[Intitul\u00e9 client] AS [Client],
    en.[Nom repr\u00e9sentant] AS [Commercial],
    li.[Code article] AS [Code Article],
    li.[D\u00e9signation ligne] AS [Designation],
    li.[Quantit\u00e9] AS [Quantite],
    li.[Prix unitaire] AS [Prix Unitaire],
    li.[Montant HT Net] AS [Montant HT],
    li.[Montant TTC Net] AS [Montant TTC],
    li.[Catalogue 1] AS [Famille],
    li.[Code d\u00e9p\u00f4t] AS [Code Depot],
    li.[Intitul\u00e9 d\u00e9p\u00f4t] AS [Depot],
    en.[Statut],
    en.Souche
{BASE_JOIN}
WHERE li.[Type Document] IN ('Facture', 'Facture comptabilis\u00e9e')
  AND {DATE_FILTER} AND {SOCIETE_FILTER} AND {COMMERCIAL_FILTER}
ORDER BY li.[Date document] DESC, li.[N\u00b0 Pi\u00e8ce]"""))

# --- 2. Bons de Livraison ---
templates.append(("DS_VTE_BL", "Bons de Livraison", f"""SELECT
    li.[societe] AS [Societe],
    li.[N\u00b0 Pi\u00e8ce BL] AS [Num BL],
    li.[Date BL] AS [Date BL],
    li.[N\u00b0 Pi\u00e8ce] AS [Num Piece Origine],
    li.[Type Document],
    li.[Code client] AS [Code Client],
    li.[Intitul\u00e9 client] AS [Client],
    en.[Nom repr\u00e9sentant] AS [Commercial],
    li.[Code article] AS [Code Article],
    li.[D\u00e9signation ligne] AS [Designation],
    li.[Quantit\u00e9 BL] AS [Quantite BL],
    li.[Montant HT Net] AS [Montant HT],
    li.[Montant TTC Net] AS [Montant TTC],
    li.[Code d\u00e9p\u00f4t] AS [Code Depot],
    li.[Intitul\u00e9 d\u00e9p\u00f4t] AS [Depot]
{BASE_JOIN}
WHERE li.[N\u00b0 Pi\u00e8ce BL] <> ''
  AND {DATE_FILTER} AND {SOCIETE_FILTER} AND {COMMERCIAL_FILTER}
ORDER BY li.[Date BL] DESC"""))

# --- 3. Bons de Commande ---
templates.append(("DS_VTE_BC", "Bons de Commande", f"""SELECT
    li.[societe] AS [Societe],
    li.[N\u00b0 Pi\u00e8ce BC] AS [Num BC],
    li.[Date BC] AS [Date BC],
    li.[N\u00b0 Pi\u00e8ce] AS [Num Piece Origine],
    li.[Type Document],
    li.[Code client] AS [Code Client],
    li.[Intitul\u00e9 client] AS [Client],
    en.[Nom repr\u00e9sentant] AS [Commercial],
    li.[Code article] AS [Code Article],
    li.[D\u00e9signation ligne] AS [Designation],
    li.[Quantit\u00e9 BC] AS [Quantite BC],
    li.[Montant HT Net] AS [Montant HT],
    li.[Montant TTC Net] AS [Montant TTC]
{BASE_JOIN}
WHERE li.[N\u00b0 Pi\u00e8ce BC] <> ''
  AND {DATE_FILTER} AND {SOCIETE_FILTER} AND {COMMERCIAL_FILTER}
ORDER BY li.[Date BC] DESC"""))

# --- 4. Devis ---
templates.append(("DS_VTE_DEVIS", "Devis", f"""SELECT
    li.[societe] AS [Societe],
    li.[N\u00b0 Pi\u00e8ce] AS [Num Piece],
    li.[Date document] AS [Date Document],
    li.[Code client] AS [Code Client],
    li.[Intitul\u00e9 client] AS [Client],
    en.[Nom repr\u00e9sentant] AS [Commercial],
    li.[Code article] AS [Code Article],
    li.[D\u00e9signation ligne] AS [Designation],
    li.[Quantit\u00e9 devis] AS [Quantite],
    li.[Prix unitaire] AS [Prix Unitaire],
    li.[Montant HT Net] AS [Montant HT],
    li.[Montant TTC Net] AS [Montant TTC],
    en.[Statut],
    li.[Catalogue 1] AS [Famille]
{BASE_JOIN}
WHERE li.[Type Document] = 'Devis'
  AND {DATE_FILTER} AND {SOCIETE_FILTER} AND {COMMERCIAL_FILTER}
ORDER BY li.[Date document] DESC"""))

# --- 5. Avoirs ---
templates.append(("DS_VTE_AVOIRS", "Avoirs", f"""SELECT
    li.[societe] AS [Societe],
    li.[Type Document],
    li.[N\u00b0 Pi\u00e8ce] AS [Num Piece],
    li.[Date document] AS [Date Document],
    li.[Code client] AS [Code Client],
    li.[Intitul\u00e9 client] AS [Client],
    en.[Nom repr\u00e9sentant] AS [Commercial],
    li.[Code article] AS [Code Article],
    li.[D\u00e9signation ligne] AS [Designation],
    li.[Quantit\u00e9] AS [Quantite],
    li.[Montant HT Net] AS [Montant HT],
    li.[Montant TTC Net] AS [Montant TTC],
    li.[Catalogue 1] AS [Famille]
{BASE_JOIN}
WHERE li.[Type Document] IN ('Bon avoir financier', 'Facture avoir', 'Facture avoir comptabilis\u00e9e')
  AND {DATE_FILTER} AND {SOCIETE_FILTER} AND {COMMERCIAL_FILTER}
ORDER BY li.[Date document] DESC"""))

# --- 6. Bons de Retour ---
templates.append(("DS_VTE_RETOURS", "Bons de Retour", f"""SELECT
    li.[societe] AS [Societe],
    li.[Type Document],
    li.[N\u00b0 Pi\u00e8ce] AS [Num Piece],
    li.[Date document] AS [Date Document],
    li.[Code client] AS [Code Client],
    li.[Intitul\u00e9 client] AS [Client],
    en.[Nom repr\u00e9sentant] AS [Commercial],
    li.[Code article] AS [Code Article],
    li.[D\u00e9signation ligne] AS [Designation],
    li.[Quantit\u00e9] AS [Quantite],
    li.[Montant HT Net] AS [Montant HT],
    li.[Montant TTC Net] AS [Montant TTC],
    li.[Code d\u00e9p\u00f4t] AS [Code Depot],
    li.[Intitul\u00e9 d\u00e9p\u00f4t] AS [Depot]
{BASE_JOIN}
WHERE li.[Type Document] IN ('Bon de retour', 'Facture de retour', 'Facture de retour comptabilis\u00e9e')
  AND {DATE_FILTER} AND {SOCIETE_FILTER} AND {COMMERCIAL_FILTER}
ORDER BY li.[Date document] DESC"""))

# --- 7. Preparations Livraison ---
templates.append(("DS_VTE_PL", "Preparations de Livraison", f"""SELECT
    li.[societe] AS [Societe],
    li.[N\u00b0 pi\u00e8ce PL] AS [Num PL],
    li.[Date PL] AS [Date PL],
    li.[N\u00b0 Pi\u00e8ce] AS [Num Piece Origine],
    li.[Code client] AS [Code Client],
    li.[Intitul\u00e9 client] AS [Client],
    en.[Nom repr\u00e9sentant] AS [Commercial],
    li.[Code article] AS [Code Article],
    li.[D\u00e9signation ligne] AS [Designation],
    li.[Quantit\u00e9 PL] AS [Quantite PL],
    li.[Montant HT Net] AS [Montant HT],
    li.[Code d\u00e9p\u00f4t] AS [Code Depot],
    li.[Intitul\u00e9 d\u00e9p\u00f4t] AS [Depot]
{BASE_JOIN}
WHERE li.[Type Document] = 'Pr\u00e9paration de livraison'
  AND {DATE_FILTER} AND {SOCIETE_FILTER} AND {COMMERCIAL_FILTER}
ORDER BY li.[Date PL] DESC"""))

# =========================================================
#  2. ANALYSES VENTES (13 rapports)
# =========================================================

# --- 8. CA par Client ---
templates.append(("DS_VTE_CA_CLIENT", "CA par Client", f"""SELECT
    li.[Code client] AS [Code Client],
    li.[Intitul\u00e9 client] AS [Client],
    li.[societe] AS [Societe],
    en.[Nom repr\u00e9sentant] AS [Commercial],
    COUNT(DISTINCT li.[N\u00b0 Pi\u00e8ce]) AS [Nb Documents],
    SUM(li.[Quantit\u00e9]) AS [Quantite Totale],
    SUM(li.[Montant HT Net]) AS [CA HT],
    SUM(li.[Montant TTC Net]) AS [CA TTC],
    SUM(li.[Quantit\u00e9] * li.[Prix de revient]) AS [Cout Revient],
    SUM(li.[Montant HT Net]) - SUM(li.[Quantit\u00e9] * li.[Prix de revient]) AS [Marge Brute],
    CASE WHEN SUM(li.[Montant HT Net]) <> 0
        THEN ROUND(100.0 * (SUM(li.[Montant HT Net]) - SUM(li.[Quantit\u00e9] * li.[Prix de revient])) / SUM(li.[Montant HT Net]), 2)
        ELSE 0 END AS [Taux Marge %]
{BASE_JOIN}
{WHERE_CA}
GROUP BY li.[Code client], li.[Intitul\u00e9 client], li.[societe], en.[Nom repr\u00e9sentant]
ORDER BY [CA HT] DESC"""))

# --- 9. CA par Article ---
templates.append(("DS_VTE_CA_ARTICLE", "CA par Article", f"""SELECT
    li.[Code article] AS [Code Article],
    li.[D\u00e9signation ligne] AS [Designation],
    li.[Catalogue 1] AS [Famille],
    li.[societe] AS [Societe],
    COUNT(DISTINCT li.[Code client]) AS [Nb Clients],
    SUM(li.[Quantit\u00e9]) AS [Quantite Vendue],
    SUM(li.[Montant HT Net]) AS [CA HT],
    SUM(li.[Montant TTC Net]) AS [CA TTC],
    SUM(li.[Quantit\u00e9] * li.[Prix de revient]) AS [Cout Revient],
    SUM(li.[Montant HT Net]) - SUM(li.[Quantit\u00e9] * li.[Prix de revient]) AS [Marge Brute],
    CASE WHEN SUM(li.[Montant HT Net]) <> 0
        THEN ROUND(100.0 * (SUM(li.[Montant HT Net]) - SUM(li.[Quantit\u00e9] * li.[Prix de revient])) / SUM(li.[Montant HT Net]), 2)
        ELSE 0 END AS [Taux Marge %],
    AVG(li.[Prix unitaire]) AS [Prix Moyen]
{BASE_JOIN}
{WHERE_CA}
GROUP BY li.[Code article], li.[D\u00e9signation ligne], li.[Catalogue 1], li.[societe]
ORDER BY [CA HT] DESC"""))

# --- 10. CA par Commercial ---
templates.append(("DS_VTE_CA_COMMERCIAL", "CA par Commercial", f"""SELECT
    en.[Code repr\u00e9sentant] AS [Code Commercial],
    ISNULL(en.[Nom repr\u00e9sentant], 'Non affect\u00e9') AS [Commercial],
    li.[societe] AS [Societe],
    COUNT(DISTINCT li.[Code client]) AS [Nb Clients],
    COUNT(DISTINCT li.[N\u00b0 Pi\u00e8ce]) AS [Nb Documents],
    SUM(li.[Quantit\u00e9]) AS [Quantite],
    SUM(li.[Montant HT Net]) AS [CA HT],
    SUM(li.[Montant TTC Net]) AS [CA TTC],
    SUM(li.[Montant HT Net]) - SUM(li.[Quantit\u00e9] * li.[Prix de revient]) AS [Marge Brute],
    CASE WHEN SUM(li.[Montant HT Net]) <> 0
        THEN ROUND(100.0 * (SUM(li.[Montant HT Net]) - SUM(li.[Quantit\u00e9] * li.[Prix de revient])) / SUM(li.[Montant HT Net]), 2)
        ELSE 0 END AS [Taux Marge %]
{BASE_JOIN}
{WHERE_CA}
GROUP BY en.[Code repr\u00e9sentant], en.[Nom repr\u00e9sentant], li.[societe]
ORDER BY [CA HT] DESC"""))

# --- 11. CA par Region / Ville ---
templates.append(("DS_VTE_CA_REGION", "CA par Region / Ville", f"""SELECT
    ISNULL(cl.[R\u00e9gion], 'Non renseigne') AS [Region],
    ISNULL(cl.[Ville], 'Non renseigne') AS [Ville],
    li.[societe] AS [Societe],
    COUNT(DISTINCT li.[Code client]) AS [Nb Clients],
    SUM(li.[Montant HT Net]) AS [CA HT],
    SUM(li.[Montant TTC Net]) AS [CA TTC],
    SUM(li.[Montant HT Net]) - SUM(li.[Quantit\u00e9] * li.[Prix de revient]) AS [Marge Brute],
    CASE WHEN SUM(li.[Montant HT Net]) <> 0
        THEN ROUND(100.0 * (SUM(li.[Montant HT Net]) - SUM(li.[Quantit\u00e9] * li.[Prix de revient])) / SUM(li.[Montant HT Net]), 2)
        ELSE 0 END AS [Taux Marge %]
{BASE_JOIN}
LEFT JOIN [Clients] cl ON li.[Code client] = cl.[Code client] AND li.[societe] = cl.[societe]
{WHERE_CA}
GROUP BY cl.[R\u00e9gion], cl.[Ville], li.[societe]
ORDER BY [CA HT] DESC"""))

# --- 12. CA par Famille Article ---
templates.append(("DS_VTE_CA_FAMILLE", "CA par Famille Article", f"""SELECT
    ISNULL(li.[Catalogue 1], 'Non classe') AS [Famille],
    ISNULL(li.[Catalogue 2], '') AS [Sous Famille],
    li.[societe] AS [Societe],
    COUNT(DISTINCT li.[Code article]) AS [Nb Articles],
    COUNT(DISTINCT li.[Code client]) AS [Nb Clients],
    SUM(li.[Quantit\u00e9]) AS [Quantite],
    SUM(li.[Montant HT Net]) AS [CA HT],
    SUM(li.[Montant TTC Net]) AS [CA TTC],
    SUM(li.[Montant HT Net]) - SUM(li.[Quantit\u00e9] * li.[Prix de revient]) AS [Marge Brute],
    CASE WHEN SUM(li.[Montant HT Net]) <> 0
        THEN ROUND(100.0 * (SUM(li.[Montant HT Net]) - SUM(li.[Quantit\u00e9] * li.[Prix de revient])) / SUM(li.[Montant HT Net]), 2)
        ELSE 0 END AS [Taux Marge %]
{BASE_JOIN}
{WHERE_CA}
GROUP BY li.[Catalogue 1], li.[Catalogue 2], li.[societe]
ORDER BY [CA HT] DESC"""))

# --- 13. Evolution CA Mensuelle ---
templates.append(("DS_VTE_CA_MENSUEL", "Evolution CA Mensuelle", f"""SELECT
    YEAR(li.[Date BL]) AS [Annee],
    MONTH(li.[Date BL]) AS [Mois],
    FORMAT(li.[Date BL], 'yyyy-MM') AS [Periode],
    li.[societe] AS [Societe],
    COUNT(DISTINCT li.[Code client]) AS [Nb Clients],
    COUNT(DISTINCT li.[N\u00b0 Pi\u00e8ce]) AS [Nb Documents],
    SUM(li.[Quantit\u00e9]) AS [Quantite],
    SUM(li.[Montant HT Net]) AS [CA HT],
    SUM(li.[Montant TTC Net]) AS [CA TTC],
    SUM(li.[Montant HT Net]) - SUM(li.[Quantit\u00e9] * li.[Prix de revient]) AS [Marge Brute],
    CASE WHEN SUM(li.[Montant HT Net]) <> 0
        THEN ROUND(100.0 * (SUM(li.[Montant HT Net]) - SUM(li.[Quantit\u00e9] * li.[Prix de revient])) / SUM(li.[Montant HT Net]), 2)
        ELSE 0 END AS [Taux Marge %]
{BASE_JOIN}
{WHERE_CA}
GROUP BY YEAR(li.[Date BL]), MONTH(li.[Date BL]), FORMAT(li.[Date BL], 'yyyy-MM'), li.[societe]
ORDER BY [Annee] DESC, [Mois] DESC"""))

# --- 14. Top 20 Clients ---
templates.append(("DS_VTE_TOP_CLIENTS", "Top 20 Clients", f"""SELECT TOP 20
    li.[Code client] AS [Code Client],
    li.[Intitul\u00e9 client] AS [Client],
    li.[societe] AS [Societe],
    en.[Nom repr\u00e9sentant] AS [Commercial],
    COUNT(DISTINCT li.[N\u00b0 Pi\u00e8ce]) AS [Nb Documents],
    SUM(li.[Montant HT Net]) AS [CA HT],
    SUM(li.[Montant TTC Net]) AS [CA TTC],
    SUM(li.[Montant HT Net]) - SUM(li.[Quantit\u00e9] * li.[Prix de revient]) AS [Marge Brute],
    CASE WHEN SUM(li.[Montant HT Net]) <> 0
        THEN ROUND(100.0 * (SUM(li.[Montant HT Net]) - SUM(li.[Quantit\u00e9] * li.[Prix de revient])) / SUM(li.[Montant HT Net]), 2)
        ELSE 0 END AS [Taux Marge %]
{BASE_JOIN}
{WHERE_CA}
GROUP BY li.[Code client], li.[Intitul\u00e9 client], li.[societe], en.[Nom repr\u00e9sentant]
ORDER BY [CA HT] DESC"""))

# --- 15. Top 20 Articles ---
templates.append(("DS_VTE_TOP_ARTICLES", "Top 20 Articles", f"""SELECT TOP 20
    li.[Code article] AS [Code Article],
    li.[D\u00e9signation ligne] AS [Designation],
    li.[Catalogue 1] AS [Famille],
    li.[societe] AS [Societe],
    COUNT(DISTINCT li.[Code client]) AS [Nb Clients],
    SUM(li.[Quantit\u00e9]) AS [Quantite Vendue],
    SUM(li.[Montant HT Net]) AS [CA HT],
    SUM(li.[Montant HT Net]) - SUM(li.[Quantit\u00e9] * li.[Prix de revient]) AS [Marge Brute],
    CASE WHEN SUM(li.[Montant HT Net]) <> 0
        THEN ROUND(100.0 * (SUM(li.[Montant HT Net]) - SUM(li.[Quantit\u00e9] * li.[Prix de revient])) / SUM(li.[Montant HT Net]), 2)
        ELSE 0 END AS [Taux Marge %]
{BASE_JOIN}
{WHERE_CA}
GROUP BY li.[Code article], li.[D\u00e9signation ligne], li.[Catalogue 1], li.[societe]
ORDER BY [CA HT] DESC"""))

# --- 16. Analyse Marges ---
templates.append(("DS_VTE_MARGES", "Analyse Marges", f"""SELECT
    li.[Code client] AS [Code Client],
    li.[Intitul\u00e9 client] AS [Client],
    li.[Code article] AS [Code Article],
    li.[D\u00e9signation ligne] AS [Designation],
    li.[Catalogue 1] AS [Famille],
    en.[Nom repr\u00e9sentant] AS [Commercial],
    li.[societe] AS [Societe],
    SUM(li.[Quantit\u00e9]) AS [Quantite],
    SUM(li.[Montant HT Net]) AS [CA HT],
    SUM(li.[Quantit\u00e9] * li.[Prix de revient]) AS [Cout Revient],
    SUM(li.[Montant HT Net]) - SUM(li.[Quantit\u00e9] * li.[Prix de revient]) AS [Marge Brute],
    CASE WHEN SUM(li.[Montant HT Net]) <> 0
        THEN ROUND(100.0 * (SUM(li.[Montant HT Net]) - SUM(li.[Quantit\u00e9] * li.[Prix de revient])) / SUM(li.[Montant HT Net]), 2)
        ELSE 0 END AS [Taux Marge %],
    AVG(li.[Prix unitaire]) AS [Prix Moyen Vente],
    AVG(li.[Prix de revient]) AS [Prix Moyen Revient]
{BASE_JOIN}
{WHERE_CA}
GROUP BY li.[Code client], li.[Intitul\u00e9 client], li.[Code article], li.[D\u00e9signation ligne],
         li.[Catalogue 1], en.[Nom repr\u00e9sentant], li.[societe]
ORDER BY [Marge Brute] DESC"""))

# --- 17. Commandes en Cours ---
templates.append(("DS_VTE_CMD_EN_COURS", "Commandes en Cours", f"""SELECT
    li.[societe] AS [Societe],
    li.[N\u00b0 Pi\u00e8ce] AS [Num Piece],
    li.[Date document] AS [Date Commande],
    li.[Code client] AS [Code Client],
    li.[Intitul\u00e9 client] AS [Client],
    en.[Nom repr\u00e9sentant] AS [Commercial],
    li.[Code article] AS [Code Article],
    li.[D\u00e9signation ligne] AS [Designation],
    li.[Quantit\u00e9] AS [Qte Commandee],
    li.[Quantit\u00e9 BL] AS [Qte Livree],
    li.[Quantit\u00e9] - ISNULL(li.[Quantit\u00e9 BL], 0) AS [Reste a Livrer],
    li.[Montant HT Net] AS [Montant HT],
    en.[Statut],
    DATEDIFF(DAY, li.[Date document], GETDATE()) AS [Anciennete Jours]
{BASE_JOIN}
WHERE li.[Type Document] = 'Bon de commande'
  AND li.[Quantit\u00e9] > ISNULL(li.[Quantit\u00e9 BL], 0)
  AND {SOCIETE_FILTER} AND {COMMERCIAL_FILTER}
ORDER BY [Anciennete Jours] DESC"""))

# --- 18. Comparatif N / N-1 ---
templates.append(("DS_VTE_COMPARATIF", "Comparatif Annuel N vs N-1", f"""SELECT
    li.[societe] AS [Societe],
    MONTH(li.[Date BL]) AS [Mois],
    FORMAT(li.[Date BL], 'MMMM', 'fr-FR') AS [Nom Mois],
    SUM(CASE WHEN YEAR(li.[Date BL]) = YEAR(GETDATE()) THEN li.[Montant HT Net] ELSE 0 END) AS [CA HT N],
    SUM(CASE WHEN YEAR(li.[Date BL]) = YEAR(GETDATE()) - 1 THEN li.[Montant HT Net] ELSE 0 END) AS [CA HT N-1],
    SUM(CASE WHEN YEAR(li.[Date BL]) = YEAR(GETDATE()) THEN li.[Montant HT Net] ELSE 0 END)
    - SUM(CASE WHEN YEAR(li.[Date BL]) = YEAR(GETDATE()) - 1 THEN li.[Montant HT Net] ELSE 0 END) AS [Ecart],
    CASE WHEN SUM(CASE WHEN YEAR(li.[Date BL]) = YEAR(GETDATE()) - 1 THEN li.[Montant HT Net] ELSE 0 END) <> 0
        THEN ROUND(100.0 * (SUM(CASE WHEN YEAR(li.[Date BL]) = YEAR(GETDATE()) THEN li.[Montant HT Net] ELSE 0 END)
            - SUM(CASE WHEN YEAR(li.[Date BL]) = YEAR(GETDATE()) - 1 THEN li.[Montant HT Net] ELSE 0 END))
            / ABS(SUM(CASE WHEN YEAR(li.[Date BL]) = YEAR(GETDATE()) - 1 THEN li.[Montant HT Net] ELSE 0 END)), 2)
        ELSE 0 END AS [Evolution %],
    SUM(CASE WHEN YEAR(li.[Date BL]) = YEAR(GETDATE()) THEN li.[Montant HT Net] - li.[Quantit\u00e9] * li.[Prix de revient] ELSE 0 END) AS [Marge N],
    SUM(CASE WHEN YEAR(li.[Date BL]) = YEAR(GETDATE()) - 1 THEN li.[Montant HT Net] - li.[Quantit\u00e9] * li.[Prix de revient] ELSE 0 END) AS [Marge N-1]
{BASE_JOIN}
WHERE {CA_FILTER}
  AND YEAR(li.[Date BL]) IN (YEAR(GETDATE()), YEAR(GETDATE()) - 1)
  AND {SOCIETE_FILTER}
GROUP BY li.[societe], MONTH(li.[Date BL]), FORMAT(li.[Date BL], 'MMMM', 'fr-FR')
ORDER BY [Mois]"""))

# --- 19. CA par Mode de Reglement ---
templates.append(("DS_VTE_CA_MODE_REGLEMENT", "CA par Mode de Reglement", f"""SELECT
    en.[Intitul\u00e9 tiers payeur] AS [Tiers Payeur],
    en.[Cat\u00e9gorie Comptable] AS [Categorie Comptable],
    li.[societe] AS [Societe],
    COUNT(DISTINCT li.[Code client]) AS [Nb Clients],
    COUNT(DISTINCT li.[N\u00b0 Pi\u00e8ce]) AS [Nb Documents],
    SUM(li.[Montant HT Net]) AS [CA HT],
    SUM(li.[Montant TTC Net]) AS [CA TTC]
{BASE_JOIN}
{WHERE_CA}
GROUP BY en.[Intitul\u00e9 tiers payeur], en.[Cat\u00e9gorie Comptable], li.[societe]
ORDER BY [CA HT] DESC"""))

# --- 20. Statistiques Remises ---
templates.append(("DS_VTE_REMISES", "Statistiques Remises", f"""SELECT
    li.[Code client] AS [Code Client],
    li.[Intitul\u00e9 client] AS [Client],
    li.[Code article] AS [Code Article],
    li.[D\u00e9signation ligne] AS [Designation],
    li.[societe] AS [Societe],
    li.[Remise 1] AS [Remise 1],
    li.[Type de la remise 1] AS [Type Remise 1],
    li.[Remise 2] AS [Remise 2],
    li.[Type de la remise 2] AS [Type Remise 2],
    li.[Type remise exceptionnelle] AS [Remise Exceptionnelle],
    SUM(li.[Quantit\u00e9]) AS [Quantite],
    SUM(li.[Montant HT Net]) AS [CA HT],
    SUM(li.[Quantit\u00e9] * li.[Prix unitaire]) AS [Montant Brut],
    SUM(li.[Quantit\u00e9] * li.[Prix unitaire]) - SUM(li.[Montant HT Net]) AS [Total Remises]
{BASE_JOIN}
{WHERE_CA}
GROUP BY li.[Code client], li.[Intitul\u00e9 client], li.[Code article], li.[D\u00e9signation ligne],
         li.[societe], li.[Remise 1], li.[Type de la remise 1], li.[Remise 2],
         li.[Type de la remise 2], li.[Type remise exceptionnelle]
HAVING SUM(li.[Quantit\u00e9] * li.[Prix unitaire]) - SUM(li.[Montant HT Net]) <> 0
ORDER BY [Total Remises] DESC"""))

# =========================================================
#  3. RAPPORTS AVANCES (15 rapports)
# =========================================================

# --- 21. CA par Depot ---
templates.append(("DS_VTE_CA_DEPOT", "CA par Depot", f"""SELECT
    li.[Code d\u00e9p\u00f4t] AS [Code Depot],
    li.[Intitul\u00e9 d\u00e9p\u00f4t] AS [Depot],
    li.[societe] AS [Societe],
    COUNT(DISTINCT li.[Code client]) AS [Nb Clients],
    COUNT(DISTINCT li.[Code article]) AS [Nb Articles],
    SUM(li.[Quantit\u00e9]) AS [Quantite],
    SUM(li.[Poids net]) AS [Poids Net Total],
    SUM(li.[Montant HT Net]) AS [CA HT],
    SUM(li.[Montant TTC Net]) AS [CA TTC],
    SUM(li.[Montant HT Net]) - SUM(li.[Quantit\u00e9] * li.[Prix de revient]) AS [Marge Brute]
{BASE_JOIN}
{WHERE_CA}
GROUP BY li.[Code d\u00e9p\u00f4t], li.[Intitul\u00e9 d\u00e9p\u00f4t], li.[societe]
ORDER BY [CA HT] DESC"""))

# --- 22. CA par Affaire ---
templates.append(("DS_VTE_CA_AFFAIRE", "CA par Affaire", f"""SELECT
    li.[Code d'affaire] AS [Code Affaire],
    li.[Intitul\u00e9 affaire] AS [Affaire],
    li.[societe] AS [Societe],
    COUNT(DISTINCT li.[Code client]) AS [Nb Clients],
    COUNT(DISTINCT li.[N\u00b0 Pi\u00e8ce]) AS [Nb Documents],
    SUM(li.[Montant HT Net]) AS [CA HT],
    SUM(li.[Montant TTC Net]) AS [CA TTC],
    SUM(li.[Montant HT Net]) - SUM(li.[Quantit\u00e9] * li.[Prix de revient]) AS [Marge Brute],
    CASE WHEN SUM(li.[Montant HT Net]) <> 0
        THEN ROUND(100.0 * (SUM(li.[Montant HT Net]) - SUM(li.[Quantit\u00e9] * li.[Prix de revient])) / SUM(li.[Montant HT Net]), 2)
        ELSE 0 END AS [Taux Marge %]
{BASE_JOIN}
{WHERE_CA}
GROUP BY li.[Code d'affaire], li.[Intitul\u00e9 affaire], li.[societe]
ORDER BY [CA HT] DESC"""))

# --- 23. Analyse RFM Clients ---
templates.append(("DS_VTE_RFM", "Analyse RFM Clients", f"""WITH ClientData AS (
    SELECT
        li.[Code client],
        li.[Intitul\u00e9 client],
        li.[societe],
        MAX(li.[Date BL]) AS [Derniere Vente],
        COUNT(DISTINCT li.[N\u00b0 Pi\u00e8ce]) AS [Nb Transactions],
        SUM(li.[Montant HT Net]) AS [CA Total]
    {BASE_JOIN}
    {WHERE_CA}
    GROUP BY li.[Code client], li.[Intitul\u00e9 client], li.[societe]
)
SELECT
    [Code client] AS [Code Client],
    [Intitul\u00e9 client] AS [Client],
    [societe] AS [Societe],
    [Derniere Vente],
    DATEDIFF(DAY, [Derniere Vente], GETDATE()) AS [Recence Jours],
    [Nb Transactions] AS [Frequence],
    [CA Total] AS [Montant],
    CASE
        WHEN DATEDIFF(DAY, [Derniere Vente], GETDATE()) <= 30 THEN 5
        WHEN DATEDIFF(DAY, [Derniere Vente], GETDATE()) <= 90 THEN 4
        WHEN DATEDIFF(DAY, [Derniere Vente], GETDATE()) <= 180 THEN 3
        WHEN DATEDIFF(DAY, [Derniere Vente], GETDATE()) <= 365 THEN 2
        ELSE 1 END AS [Score R],
    NTILE(5) OVER (ORDER BY [Nb Transactions]) AS [Score F],
    NTILE(5) OVER (ORDER BY [CA Total]) AS [Score M],
    CASE
        WHEN DATEDIFF(DAY, [Derniere Vente], GETDATE()) <= 90 AND [Nb Transactions] >= 10 THEN 'Champion'
        WHEN DATEDIFF(DAY, [Derniere Vente], GETDATE()) <= 90 THEN 'Client Recent'
        WHEN [Nb Transactions] >= 10 THEN 'Client Fidele'
        WHEN DATEDIFF(DAY, [Derniere Vente], GETDATE()) > 365 THEN 'Client Perdu'
        WHEN DATEDIFF(DAY, [Derniere Vente], GETDATE()) > 180 THEN 'A Risque'
        ELSE 'Client Regulier'
    END AS [Segment]
FROM ClientData
ORDER BY [CA Total] DESC"""))

# --- 24. Saisonnalite des Ventes ---
templates.append(("DS_VTE_SAISONNALITE", "Saisonnalite des Ventes", f"""SELECT
    MONTH(li.[Date BL]) AS [Mois],
    FORMAT(li.[Date BL], 'MMMM', 'fr-FR') AS [Nom Mois],
    li.[Catalogue 1] AS [Famille],
    li.[societe] AS [Societe],
    SUM(CASE WHEN YEAR(li.[Date BL]) = YEAR(GETDATE()) THEN li.[Montant HT Net] ELSE 0 END) AS [CA N],
    SUM(CASE WHEN YEAR(li.[Date BL]) = YEAR(GETDATE()) - 1 THEN li.[Montant HT Net] ELSE 0 END) AS [CA N-1],
    SUM(CASE WHEN YEAR(li.[Date BL]) = YEAR(GETDATE()) - 2 THEN li.[Montant HT Net] ELSE 0 END) AS [CA N-2],
    AVG(li.[Montant HT Net]) AS [Moyenne],
    SUM(li.[Quantit\u00e9]) AS [Quantite Totale]
{BASE_JOIN}
WHERE {CA_FILTER}
  AND YEAR(li.[Date BL]) >= YEAR(GETDATE()) - 2
  AND {SOCIETE_FILTER}
GROUP BY MONTH(li.[Date BL]), FORMAT(li.[Date BL], 'MMMM', 'fr-FR'), li.[Catalogue 1], li.[societe]
ORDER BY li.[Catalogue 1], [Mois]"""))

# --- 25. Panier Moyen par Client ---
templates.append(("DS_VTE_PANIER_MOYEN", "Panier Moyen par Client", f"""SELECT
    li.[Code client] AS [Code Client],
    li.[Intitul\u00e9 client] AS [Client],
    li.[societe] AS [Societe],
    en.[Nom repr\u00e9sentant] AS [Commercial],
    COUNT(DISTINCT li.[N\u00b0 Pi\u00e8ce]) AS [Nb Transactions],
    SUM(li.[Montant HT Net]) AS [CA HT Total],
    CASE WHEN COUNT(DISTINCT li.[N\u00b0 Pi\u00e8ce]) > 0
        THEN ROUND(SUM(li.[Montant HT Net]) / COUNT(DISTINCT li.[N\u00b0 Pi\u00e8ce]), 2)
        ELSE 0 END AS [Panier Moyen HT],
    COUNT(DISTINCT li.[Code article]) AS [Nb Articles Distincts],
    CASE WHEN COUNT(DISTINCT li.[N\u00b0 Pi\u00e8ce]) > 0
        THEN ROUND(CAST(SUM(li.[Quantit\u00e9]) AS FLOAT) / COUNT(DISTINCT li.[N\u00b0 Pi\u00e8ce]), 2)
        ELSE 0 END AS [Qte Moy par Transaction],
    MIN(li.[Date BL]) AS [Premiere Vente],
    MAX(li.[Date BL]) AS [Derniere Vente]
{BASE_JOIN}
{WHERE_CA}
GROUP BY li.[Code client], li.[Intitul\u00e9 client], li.[societe], en.[Nom repr\u00e9sentant]
ORDER BY [Panier Moyen HT] DESC"""))

# --- 26. Clients a Risque de Churn ---
templates.append(("DS_VTE_CHURN", "Clients a Risque de Churn", f"""WITH ClientHistory AS (
    SELECT
        li.[Code client],
        li.[Intitul\u00e9 client],
        li.[societe],
        en.[Nom repr\u00e9sentant],
        MAX(li.[Date BL]) AS [Derniere Vente],
        SUM(CASE WHEN li.[Date BL] >= DATEADD(MONTH, -6, GETDATE()) THEN li.[Montant HT Net] ELSE 0 END) AS [CA 6M],
        SUM(CASE WHEN li.[Date BL] >= DATEADD(MONTH, -12, GETDATE()) AND li.[Date BL] < DATEADD(MONTH, -6, GETDATE())
            THEN li.[Montant HT Net] ELSE 0 END) AS [CA 6M Precedent],
        COUNT(DISTINCT CASE WHEN li.[Date BL] >= DATEADD(MONTH, -6, GETDATE()) THEN li.[N\u00b0 Pi\u00e8ce] END) AS [Freq 6M],
        COUNT(DISTINCT CASE WHEN li.[Date BL] >= DATEADD(MONTH, -12, GETDATE()) AND li.[Date BL] < DATEADD(MONTH, -6, GETDATE())
            THEN li.[N\u00b0 Pi\u00e8ce] END) AS [Freq 6M Precedent]
    {BASE_JOIN}
    WHERE {CA_FILTER} AND li.[Date BL] >= DATEADD(MONTH, -12, GETDATE()) AND {SOCIETE_FILTER}
    GROUP BY li.[Code client], li.[Intitul\u00e9 client], li.[societe], en.[Nom repr\u00e9sentant]
    HAVING SUM(li.[Montant HT Net]) > 0
)
SELECT
    [Code client] AS [Code Client],
    [Intitul\u00e9 client] AS [Client],
    [societe] AS [Societe],
    [Nom repr\u00e9sentant] AS [Commercial],
    [Derniere Vente],
    DATEDIFF(DAY, [Derniere Vente], GETDATE()) AS [Jours Sans Achat],
    [CA 6M],
    [CA 6M Precedent],
    CASE WHEN [CA 6M Precedent] > 0
        THEN ROUND(100.0 * ([CA 6M] - [CA 6M Precedent]) / [CA 6M Precedent], 2)
        ELSE -100 END AS [Evolution CA %],
    [Freq 6M],
    [Freq 6M Precedent],
    CASE
        WHEN DATEDIFF(DAY, [Derniere Vente], GETDATE()) > 180 THEN 'PERDU'
        WHEN [CA 6M] = 0 AND [CA 6M Precedent] > 0 THEN 'INACTIF'
        WHEN [CA 6M] < [CA 6M Precedent] * 0.5 THEN 'RISQUE ELEVE'
        WHEN [CA 6M] < [CA 6M Precedent] * 0.8 THEN 'RISQUE MODERE'
        ELSE 'STABLE'
    END AS [Statut Risque]
FROM ClientHistory
WHERE [CA 6M] < [CA 6M Precedent] OR DATEDIFF(DAY, [Derniere Vente], GETDATE()) > 90
ORDER BY [CA 6M Precedent] DESC"""))

# --- 27. Analyse des Prix de Vente ---
templates.append(("DS_VTE_ANALYSE_PRIX", "Analyse des Prix de Vente", f"""SELECT
    li.[Code article] AS [Code Article],
    li.[D\u00e9signation ligne] AS [Designation],
    li.[Catalogue 1] AS [Famille],
    li.[societe] AS [Societe],
    COUNT(*) AS [Nb Lignes],
    MIN(li.[Prix unitaire]) AS [Prix Min],
    MAX(li.[Prix unitaire]) AS [Prix Max],
    AVG(li.[Prix unitaire]) AS [Prix Moyen],
    STDEV(li.[Prix unitaire]) AS [Ecart Type Prix],
    AVG(li.[Prix de revient]) AS [Cout Revient Moyen],
    AVG(li.[Prix unitaire]) - AVG(li.[Prix de revient]) AS [Marge Unitaire Moy],
    CASE WHEN AVG(li.[Prix unitaire]) > 0
        THEN ROUND(100.0 * (AVG(li.[Prix unitaire]) - AVG(li.[Prix de revient])) / AVG(li.[Prix unitaire]), 2)
        ELSE 0 END AS [Taux Marge Moy %]
{BASE_JOIN}
{WHERE_CA}
GROUP BY li.[Code article], li.[D\u00e9signation ligne], li.[Catalogue 1], li.[societe]
HAVING COUNT(*) >= 5
ORDER BY [Ecart Type Prix] DESC"""))

# --- 28. Taux de Service Client ---
templates.append(("DS_VTE_TAUX_SERVICE", "Taux de Service Client", f"""SELECT
    li.[Code client] AS [Code Client],
    li.[Intitul\u00e9 client] AS [Client],
    li.[societe] AS [Societe],
    COUNT(DISTINCT li.[N\u00b0 Pi\u00e8ce]) AS [Nb Documents Total],
    COUNT(DISTINCT CASE WHEN li.[Type Document] IN ('Facture', 'Facture comptabilis\u00e9e', 'Bon de livraison') THEN li.[N\u00b0 Pi\u00e8ce] END) AS [Nb Livres],
    COUNT(DISTINCT CASE WHEN li.[Type Document] IN ('Bon de retour', 'Facture de retour', 'Facture de retour comptabilis\u00e9e') THEN li.[N\u00b0 Pi\u00e8ce] END) AS [Nb Retours],
    CASE WHEN COUNT(DISTINCT li.[N\u00b0 Pi\u00e8ce]) > 0
        THEN ROUND(100.0 * COUNT(DISTINCT CASE WHEN li.[Type Document] IN ('Bon de retour', 'Facture de retour', 'Facture de retour comptabilis\u00e9e') THEN li.[N\u00b0 Pi\u00e8ce] END)
            / COUNT(DISTINCT li.[N\u00b0 Pi\u00e8ce]), 2)
        ELSE 0 END AS [Taux Retour %],
    SUM(li.[Montant HT Net]) AS [CA HT Net],
    SUM(CASE WHEN li.[Type Document] IN ('Bon de retour', 'Facture de retour', 'Facture de retour comptabilis\u00e9e')
        THEN ABS(li.[Montant HT Net]) ELSE 0 END) AS [Montant Retours]
{BASE_JOIN}
{WHERE_ALL}
GROUP BY li.[Code client], li.[Intitul\u00e9 client], li.[societe]
HAVING COUNT(DISTINCT li.[N\u00b0 Pi\u00e8ce]) >= 3
ORDER BY [Taux Retour %] DESC"""))

# --- 29. Analyse des Retours ---
templates.append(("DS_VTE_ANALYSE_RETOURS", "Analyse des Retours", f"""SELECT
    li.[Code article] AS [Code Article],
    li.[D\u00e9signation ligne] AS [Designation],
    li.[Catalogue 1] AS [Famille],
    li.[Code client] AS [Code Client],
    li.[Intitul\u00e9 client] AS [Client],
    li.[societe] AS [Societe],
    li.[Type Document],
    SUM(ABS(li.[Quantit\u00e9])) AS [Quantite Retournee],
    SUM(ABS(li.[Montant HT Net])) AS [Montant HT Retour],
    COUNT(DISTINCT li.[N\u00b0 Pi\u00e8ce]) AS [Nb Documents Retour]
{BASE_JOIN}
WHERE li.[Type Document] IN ('Bon de retour', 'Facture de retour', 'Facture de retour comptabilis\u00e9e')
  AND {DATE_FILTER} AND {SOCIETE_FILTER}
GROUP BY li.[Code article], li.[D\u00e9signation ligne], li.[Catalogue 1],
         li.[Code client], li.[Intitul\u00e9 client], li.[societe], li.[Type Document]
ORDER BY [Montant HT Retour] DESC"""))

# --- 30. Rentabilite par Client ---
templates.append(("DS_VTE_RENTABILITE_CLIENT", "Rentabilite par Client", f"""SELECT
    li.[Code client] AS [Code Client],
    li.[Intitul\u00e9 client] AS [Client],
    li.[societe] AS [Societe],
    en.[Nom repr\u00e9sentant] AS [Commercial],
    SUM(li.[Montant HT Net]) AS [CA HT],
    SUM(li.[Quantit\u00e9] * li.[Prix de revient]) AS [Cout Revient Total],
    SUM(li.[Montant HT Net]) - SUM(li.[Quantit\u00e9] * li.[Prix de revient]) AS [Marge Brute],
    CASE WHEN SUM(li.[Montant HT Net]) <> 0
        THEN ROUND(100.0 * (SUM(li.[Montant HT Net]) - SUM(li.[Quantit\u00e9] * li.[Prix de revient])) / SUM(li.[Montant HT Net]), 2)
        ELSE 0 END AS [Taux Marge %],
    COUNT(DISTINCT li.[N\u00b0 Pi\u00e8ce]) AS [Nb Transactions],
    COUNT(DISTINCT li.[Code article]) AS [Nb Articles],
    SUM(li.[Poids net]) AS [Poids Total],
    CASE WHEN SUM(li.[Poids net]) > 0
        THEN ROUND(SUM(li.[Montant HT Net]) / SUM(li.[Poids net]), 2)
        ELSE 0 END AS [CA par Kg]
{BASE_JOIN}
{WHERE_CA}
GROUP BY li.[Code client], li.[Intitul\u00e9 client], li.[societe], en.[Nom repr\u00e9sentant]
ORDER BY [Marge Brute] DESC"""))

# --- 31. Fidelite Clients ---
templates.append(("DS_VTE_FIDELITE", "Fidelite Clients", f"""SELECT
    li.[Code client] AS [Code Client],
    li.[Intitul\u00e9 client] AS [Client],
    li.[societe] AS [Societe],
    en.[Nom repr\u00e9sentant] AS [Commercial],
    MIN(li.[Date BL]) AS [Premiere Vente],
    MAX(li.[Date BL]) AS [Derniere Vente],
    DATEDIFF(MONTH, MIN(li.[Date BL]), MAX(li.[Date BL])) AS [Anciennete Mois],
    COUNT(DISTINCT FORMAT(li.[Date BL], 'yyyy-MM')) AS [Nb Mois Actifs],
    COUNT(DISTINCT li.[N\u00b0 Pi\u00e8ce]) AS [Nb Transactions],
    SUM(li.[Montant HT Net]) AS [CA HT Total],
    CASE WHEN DATEDIFF(MONTH, MIN(li.[Date BL]), MAX(li.[Date BL])) > 0
        THEN ROUND(SUM(li.[Montant HT Net]) / DATEDIFF(MONTH, MIN(li.[Date BL]), MAX(li.[Date BL])), 2)
        ELSE SUM(li.[Montant HT Net]) END AS [CA Moyen Mensuel],
    CASE
        WHEN DATEDIFF(MONTH, MIN(li.[Date BL]), GETDATE()) >= 36 THEN 'Historique (+3 ans)'
        WHEN DATEDIFF(MONTH, MIN(li.[Date BL]), GETDATE()) >= 12 THEN 'Fidele (1-3 ans)'
        WHEN DATEDIFF(MONTH, MIN(li.[Date BL]), GETDATE()) >= 3 THEN 'Recent (3-12 mois)'
        ELSE 'Nouveau (< 3 mois)'
    END AS [Segment Fidelite]
{BASE_JOIN}
{WHERE_CA}
GROUP BY li.[Code client], li.[Intitul\u00e9 client], li.[societe], en.[Nom repr\u00e9sentant]
ORDER BY [CA HT Total] DESC"""))

# --- 32. Performance des Devis ---
templates.append(("DS_VTE_PERF_DEVIS", "Performance des Devis", f"""WITH DevisData AS (
    SELECT
        li.[Code client],
        li.[Intitul\u00e9 client],
        li.[societe],
        en.[Nom repr\u00e9sentant],
        li.[N\u00b0 Pi\u00e8ce] AS [Num Devis],
        li.[Date document] AS [Date Devis],
        SUM(li.[Montant HT Net]) AS [Montant Devis],
        MAX(CASE WHEN li.[N\u00b0 Pi\u00e8ce BC] <> '' THEN 1 ELSE 0 END) AS [Converti BC],
        MAX(CASE WHEN li.[N\u00b0 Pi\u00e8ce BL] <> '' THEN 1 ELSE 0 END) AS [Converti BL]
    {BASE_JOIN}
    WHERE li.[Type Document] = 'Devis'
      AND {DATE_FILTER} AND {SOCIETE_FILTER}
    GROUP BY li.[Code client], li.[Intitul\u00e9 client], li.[societe], en.[Nom repr\u00e9sentant], li.[N\u00b0 Pi\u00e8ce], li.[Date document]
)
SELECT
    [Code client] AS [Code Client],
    [Intitul\u00e9 client] AS [Client],
    [societe] AS [Societe],
    [Nom repr\u00e9sentant] AS [Commercial],
    COUNT(*) AS [Nb Devis],
    SUM([Montant Devis]) AS [Montant Total Devis],
    SUM([Converti BC]) AS [Nb Convertis BC],
    SUM([Converti BL]) AS [Nb Convertis BL],
    CASE WHEN COUNT(*) > 0
        THEN ROUND(100.0 * SUM([Converti BL]) / COUNT(*), 2)
        ELSE 0 END AS [Taux Conversion %],
    AVG([Montant Devis]) AS [Montant Moyen Devis]
FROM DevisData
GROUP BY [Code client], [Intitul\u00e9 client], [societe], [Nom repr\u00e9sentant]
ORDER BY [Nb Devis] DESC"""))

# --- 33. Ventes Detail Complet ---
templates.append(("DS_VTE_DETAIL_COMPLET", "Ventes Detail Complet", f"""SELECT
    li.societe AS Societe,
    li.[Type Document],
    li.[N° Pièce] AS [Num Piece],
    li.[Date document] AS [Date Document],
    li.[Date BL],
    FORMAT(li.[Date BL], 'MMMM', 'fr-FR') AS [Nom Mois],
    li.[Code client] AS [Code Client],
    li.[Intitulé client] AS Client,
    en.[Code représentant] AS [Code Commercial],
    en.[Nom représentant] AS Commercial,
    en.Souche,
    en.Statut,
    li.[Code article] AS [Code Article],
    li.[Désignation ligne] AS Designation,
    li.[Catalogue 1] AS Famille,
    li.[Catalogue 2] AS [Sous Famille],
    li.Quantité AS Quantite,
    li.[Prix unitaire] AS [Prix Unitaire],
    li.[Montant HT Net] AS [Montant HT],
    li.[Montant TTC Net] AS [Montant TTC],
    li.[Prix de revient] AS [Prix Revient],
    li.[Montant HT Net] - li.Quantité * li.[Prix de revient] AS Marge,
    li.[Poids net] AS [Poids Net],
    li.[Code dépôt] AS [Code Depot],
    li.[Intitulé dépôt] AS Depot,
    ISNULL(cl.[Région], '') AS [Region],
    ISNULL(cl.[Ville], '') AS [Ville],
    li.[Valorise CA],
    li.[Remise 1],
    li.[N° Pièce BL] AS [Num BL],
    li.[N° Pièce BC] AS [Num BC],
    en.[Entête 1],
    en.[Entête 2],
    en.[Entête 3],
    en.[Entête 4],
    en.Etat,
    en.Devise,
    en.Expédition,
    li.[Intitulé affaire],
    en.Référence,
    en.Cours,
    en.[N° Compte Payeur],
    en.[Intitulé tiers payeur] AS [Tiers Payeur],
    en.[Catégorie Comptable] AS [Categorie Comptable],
    li.[Catalogue 3],
    li.[Catalogue 4],
    li.[Gamme 1],
    li.[Gamme 2],
    li.[Poids brut],
    li.[N° Série/Lot],
    li.Taxe1,
    li.Taxe2,
    li.[Type taxe 1],
    li.[Type taxe 2],
    li.[PU Devise],
    li.[Frais d'approche],
    li.[Type de la remise 1]
{BASE_JOIN}
LEFT JOIN [Clients] cl ON li.[Code client] = cl.[Code client] AND li.[societe] = cl.[societe]
{WHERE_ALL}
ORDER BY [Date Document] DESC, [Num Piece]"""))

# --- 34. Ventes par Type Document ---
templates.append(("DS_VTE_PAR_TYPE_DOC", "Ventes par Type Document", f"""SELECT
    li.[Type Document],
    li.[societe] AS [Societe],
    COUNT(DISTINCT li.[N\u00b0 Pi\u00e8ce]) AS [Nb Documents],
    COUNT(DISTINCT li.[Code client]) AS [Nb Clients],
    SUM(li.[Quantit\u00e9]) AS [Quantite Totale],
    SUM(li.[Montant HT Net]) AS [Total HT],
    SUM(li.[Montant TTC Net]) AS [Total TTC],
    AVG(li.[Montant HT Net]) AS [Montant Moyen Ligne]
{BASE_JOIN}
{WHERE_ALL}
GROUP BY li.[Type Document], li.[societe]
ORDER BY [Total HT] DESC"""))

# --- 35. Clients Inactifs ---
templates.append(("DS_VTE_CLIENTS_INACTIFS", "Clients Inactifs", f"""SELECT
    li.[Code client] AS [Code Client],
    li.[Intitul\u00e9 client] AS [Client],
    li.[societe] AS [Societe],
    en.[Nom repr\u00e9sentant] AS [Commercial],
    MAX(li.[Date BL]) AS [Derniere Vente],
    DATEDIFF(DAY, MAX(li.[Date BL]), GETDATE()) AS [Jours Inactif],
    SUM(li.[Montant HT Net]) AS [CA HT Historique],
    COUNT(DISTINCT li.[N\u00b0 Pi\u00e8ce]) AS [Nb Documents Historique]
{BASE_JOIN}
WHERE {CA_FILTER} AND {SOCIETE_FILTER} AND {COMMERCIAL_FILTER}
GROUP BY li.[Code client], li.[Intitul\u00e9 client], li.[societe], en.[Nom repr\u00e9sentant]
HAVING MAX(li.[Date BL]) < DATEADD(MONTH, -3, GETDATE())
ORDER BY [CA HT Historique] DESC"""))


# =============================================================================
#  INSERT ALL TEMPLATES INTO DATABASE
# =============================================================================
print(f"Creation de {len(templates)} DataSource Templates Ventes...\n")

template_ids = {}
for code, nom, query in templates:
    cursor.execute("""
        INSERT INTO APP_DataSources_Templates (code, nom, query_template, type, actif)
        OUTPUT INSERTED.id
        VALUES (?, ?, ?, 'SQL', 1)
    """, (code, nom, query))
    tid = cursor.fetchone()[0]
    template_ids[code] = tid
    print(f"  Template {tid:3d}: {code}")

print(f"\n{len(template_ids)} templates crees.")

# =============================================================================
#  GRIDVIEW DEFINITIONS
# =============================================================================
gridviews = [
    # === DOCUMENTS VENTES ===
    ("Factures de Ventes", "DS_VTE_FACTURES", [
        {"field": "Societe", "header": "Societe", "width": 90},
        {"field": "Type Document", "header": "Type Document", "width": 150},
        {"field": "Num Piece", "header": "N. Piece", "width": 120},
        {"field": "Date Document", "header": "Date Document", "width": 110, "type": "date"},
        {"field": "Code Client", "header": "Code Client", "width": 100},
        {"field": "Client", "header": "Client", "width": 200},
        {"field": "Commercial", "header": "Commercial", "width": 140},
        {"field": "Code Article", "header": "Code Article", "width": 110},
        {"field": "Designation", "header": "Designation", "width": 200},
        {"field": "Quantite", "header": "Quantite", "width": 90, "type": "number"},
        {"field": "Prix Unitaire", "header": "Prix Unitaire", "width": 110, "type": "number", "format": "#,##0.00"},
        {"field": "Montant HT", "header": "Montant HT", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Montant TTC", "header": "Montant TTC", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Famille", "header": "Famille", "width": 120},
        {"field": "Depot", "header": "Depot", "width": 140},
    ]),
    ("Bons de Livraison", "DS_VTE_BL", [
        {"field": "Societe", "header": "Societe", "width": 90},
        {"field": "Num BL", "header": "N. BL", "width": 120},
        {"field": "Date BL", "header": "Date BL", "width": 110, "type": "date"},
        {"field": "Type Document", "header": "Type Document", "width": 140},
        {"field": "Code Client", "header": "Code Client", "width": 100},
        {"field": "Client", "header": "Client", "width": 200},
        {"field": "Commercial", "header": "Commercial", "width": 140},
        {"field": "Code Article", "header": "Code Article", "width": 110},
        {"field": "Designation", "header": "Designation", "width": 200},
        {"field": "Quantite BL", "header": "Qte BL", "width": 90, "type": "number"},
        {"field": "Montant HT", "header": "Montant HT", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Montant TTC", "header": "Montant TTC", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Depot", "header": "Depot", "width": 140},
    ]),
    ("Bons de Commande", "DS_VTE_BC", [
        {"field": "Societe", "header": "Societe", "width": 90},
        {"field": "Num BC", "header": "N. BC", "width": 120},
        {"field": "Date BC", "header": "Date BC", "width": 110, "type": "date"},
        {"field": "Type Document", "header": "Type Document", "width": 140},
        {"field": "Code Client", "header": "Code Client", "width": 100},
        {"field": "Client", "header": "Client", "width": 200},
        {"field": "Commercial", "header": "Commercial", "width": 140},
        {"field": "Code Article", "header": "Code Article", "width": 110},
        {"field": "Designation", "header": "Designation", "width": 200},
        {"field": "Quantite BC", "header": "Qte BC", "width": 90, "type": "number"},
        {"field": "Montant HT", "header": "Montant HT", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Montant TTC", "header": "Montant TTC", "width": 120, "type": "number", "format": "#,##0.00"},
    ]),
    ("Devis", "DS_VTE_DEVIS", [
        {"field": "Societe", "header": "Societe", "width": 90},
        {"field": "Num Piece", "header": "N. Piece", "width": 120},
        {"field": "Date Document", "header": "Date", "width": 110, "type": "date"},
        {"field": "Code Client", "header": "Code Client", "width": 100},
        {"field": "Client", "header": "Client", "width": 200},
        {"field": "Commercial", "header": "Commercial", "width": 140},
        {"field": "Code Article", "header": "Code Article", "width": 110},
        {"field": "Designation", "header": "Designation", "width": 200},
        {"field": "Quantite", "header": "Quantite", "width": 90, "type": "number"},
        {"field": "Prix Unitaire", "header": "Prix Unitaire", "width": 110, "type": "number", "format": "#,##0.00"},
        {"field": "Montant HT", "header": "Montant HT", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Montant TTC", "header": "Montant TTC", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Statut", "header": "Statut", "width": 100},
    ]),
    ("Avoirs", "DS_VTE_AVOIRS", [
        {"field": "Societe", "header": "Societe", "width": 90},
        {"field": "Type Document", "header": "Type Document", "width": 160},
        {"field": "Num Piece", "header": "N. Piece", "width": 120},
        {"field": "Date Document", "header": "Date", "width": 110, "type": "date"},
        {"field": "Code Client", "header": "Code Client", "width": 100},
        {"field": "Client", "header": "Client", "width": 200},
        {"field": "Commercial", "header": "Commercial", "width": 140},
        {"field": "Code Article", "header": "Code Article", "width": 110},
        {"field": "Designation", "header": "Designation", "width": 200},
        {"field": "Quantite", "header": "Quantite", "width": 90, "type": "number"},
        {"field": "Montant HT", "header": "Montant HT", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Montant TTC", "header": "Montant TTC", "width": 120, "type": "number", "format": "#,##0.00"},
    ]),
    ("Bons de Retour", "DS_VTE_RETOURS", [
        {"field": "Societe", "header": "Societe", "width": 90},
        {"field": "Type Document", "header": "Type Document", "width": 160},
        {"field": "Num Piece", "header": "N. Piece", "width": 120},
        {"field": "Date Document", "header": "Date", "width": 110, "type": "date"},
        {"field": "Code Client", "header": "Code Client", "width": 100},
        {"field": "Client", "header": "Client", "width": 200},
        {"field": "Commercial", "header": "Commercial", "width": 140},
        {"field": "Code Article", "header": "Code Article", "width": 110},
        {"field": "Designation", "header": "Designation", "width": 200},
        {"field": "Quantite", "header": "Quantite", "width": 90, "type": "number"},
        {"field": "Montant HT", "header": "Montant HT", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Montant TTC", "header": "Montant TTC", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Depot", "header": "Depot", "width": 140},
    ]),
    ("Preparations de Livraison", "DS_VTE_PL", [
        {"field": "Societe", "header": "Societe", "width": 90},
        {"field": "Num PL", "header": "N. PL", "width": 120},
        {"field": "Date PL", "header": "Date PL", "width": 110, "type": "date"},
        {"field": "Code Client", "header": "Code Client", "width": 100},
        {"field": "Client", "header": "Client", "width": 200},
        {"field": "Commercial", "header": "Commercial", "width": 140},
        {"field": "Code Article", "header": "Code Article", "width": 110},
        {"field": "Designation", "header": "Designation", "width": 200},
        {"field": "Quantite PL", "header": "Qte PL", "width": 90, "type": "number"},
        {"field": "Montant HT", "header": "Montant HT", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Depot", "header": "Depot", "width": 140},
    ]),

    # === ANALYSES VENTES ===
    ("CA par Client", "DS_VTE_CA_CLIENT", [
        {"field": "Code Client", "header": "Code Client", "width": 100},
        {"field": "Client", "header": "Client", "width": 200},
        {"field": "Societe", "header": "Societe", "width": 90},
        {"field": "Commercial", "header": "Commercial", "width": 140},
        {"field": "Nb Documents", "header": "Nb Docs", "width": 80, "type": "number"},
        {"field": "Quantite Totale", "header": "Quantite", "width": 100, "type": "number"},
        {"field": "CA HT", "header": "CA HT", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "CA TTC", "header": "CA TTC", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "Cout Revient", "header": "Cout Revient", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Marge Brute", "header": "Marge Brute", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Taux Marge %", "header": "Marge %", "width": 90, "type": "number", "format": "#,##0.00"},
    ]),
    ("CA par Article", "DS_VTE_CA_ARTICLE", [
        {"field": "Code Article", "header": "Code Article", "width": 110},
        {"field": "Designation", "header": "Designation", "width": 200},
        {"field": "Famille", "header": "Famille", "width": 120},
        {"field": "Societe", "header": "Societe", "width": 90},
        {"field": "Nb Clients", "header": "Nb Clients", "width": 90, "type": "number"},
        {"field": "Quantite Vendue", "header": "Qte Vendue", "width": 100, "type": "number"},
        {"field": "CA HT", "header": "CA HT", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "CA TTC", "header": "CA TTC", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "Marge Brute", "header": "Marge Brute", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Taux Marge %", "header": "Marge %", "width": 90, "type": "number", "format": "#,##0.00"},
        {"field": "Prix Moyen", "header": "Prix Moyen", "width": 110, "type": "number", "format": "#,##0.00"},
    ]),
    ("CA par Commercial", "DS_VTE_CA_COMMERCIAL", [
        {"field": "Code Commercial", "header": "Code", "width": 70},
        {"field": "Commercial", "header": "Commercial", "width": 180},
        {"field": "Societe", "header": "Societe", "width": 90},
        {"field": "Nb Clients", "header": "Nb Clients", "width": 90, "type": "number"},
        {"field": "Nb Documents", "header": "Nb Docs", "width": 80, "type": "number"},
        {"field": "Quantite", "header": "Quantite", "width": 100, "type": "number"},
        {"field": "CA HT", "header": "CA HT", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "CA TTC", "header": "CA TTC", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "Marge Brute", "header": "Marge Brute", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Taux Marge %", "header": "Marge %", "width": 90, "type": "number", "format": "#,##0.00"},
    ]),
    ("CA par Region / Ville", "DS_VTE_CA_REGION", [
        {"field": "Region", "header": "Region", "width": 140},
        {"field": "Ville", "header": "Ville", "width": 140},
        {"field": "Societe", "header": "Societe", "width": 90},
        {"field": "Nb Clients", "header": "Nb Clients", "width": 90, "type": "number"},
        {"field": "CA HT", "header": "CA HT", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "CA TTC", "header": "CA TTC", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "Marge Brute", "header": "Marge Brute", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Taux Marge %", "header": "Marge %", "width": 90, "type": "number", "format": "#,##0.00"},
    ]),
    ("CA par Famille Article", "DS_VTE_CA_FAMILLE", [
        {"field": "Famille", "header": "Famille", "width": 150},
        {"field": "Sous Famille", "header": "Sous Famille", "width": 150},
        {"field": "Societe", "header": "Societe", "width": 90},
        {"field": "Nb Articles", "header": "Nb Articles", "width": 90, "type": "number"},
        {"field": "Nb Clients", "header": "Nb Clients", "width": 90, "type": "number"},
        {"field": "Quantite", "header": "Quantite", "width": 100, "type": "number"},
        {"field": "CA HT", "header": "CA HT", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "CA TTC", "header": "CA TTC", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "Marge Brute", "header": "Marge Brute", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Taux Marge %", "header": "Marge %", "width": 90, "type": "number", "format": "#,##0.00"},
    ]),
    ("Evolution CA Mensuelle", "DS_VTE_CA_MENSUEL", [
        {"field": "Annee", "header": "Annee", "width": 70, "type": "number"},
        {"field": "Mois", "header": "Mois", "width": 60, "type": "number"},
        {"field": "Periode", "header": "Periode", "width": 100},
        {"field": "Societe", "header": "Societe", "width": 90},
        {"field": "Nb Clients", "header": "Nb Clients", "width": 90, "type": "number"},
        {"field": "Nb Documents", "header": "Nb Docs", "width": 80, "type": "number"},
        {"field": "Quantite", "header": "Quantite", "width": 100, "type": "number"},
        {"field": "CA HT", "header": "CA HT", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "CA TTC", "header": "CA TTC", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "Marge Brute", "header": "Marge Brute", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Taux Marge %", "header": "Marge %", "width": 90, "type": "number", "format": "#,##0.00"},
    ]),
    ("Top 20 Clients", "DS_VTE_TOP_CLIENTS", [
        {"field": "Code Client", "header": "Code Client", "width": 100},
        {"field": "Client", "header": "Client", "width": 200},
        {"field": "Societe", "header": "Societe", "width": 90},
        {"field": "Commercial", "header": "Commercial", "width": 140},
        {"field": "Nb Documents", "header": "Nb Docs", "width": 80, "type": "number"},
        {"field": "CA HT", "header": "CA HT", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "CA TTC", "header": "CA TTC", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "Marge Brute", "header": "Marge Brute", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Taux Marge %", "header": "Marge %", "width": 90, "type": "number", "format": "#,##0.00"},
    ]),
    ("Top 20 Articles", "DS_VTE_TOP_ARTICLES", [
        {"field": "Code Article", "header": "Code Article", "width": 110},
        {"field": "Designation", "header": "Designation", "width": 200},
        {"field": "Famille", "header": "Famille", "width": 120},
        {"field": "Societe", "header": "Societe", "width": 90},
        {"field": "Nb Clients", "header": "Nb Clients", "width": 90, "type": "number"},
        {"field": "Quantite Vendue", "header": "Qte Vendue", "width": 100, "type": "number"},
        {"field": "CA HT", "header": "CA HT", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "Marge Brute", "header": "Marge Brute", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Taux Marge %", "header": "Marge %", "width": 90, "type": "number", "format": "#,##0.00"},
    ]),
    ("Analyse Marges", "DS_VTE_MARGES", [
        {"field": "Code Client", "header": "Code Client", "width": 100},
        {"field": "Client", "header": "Client", "width": 170},
        {"field": "Code Article", "header": "Code Article", "width": 100},
        {"field": "Designation", "header": "Designation", "width": 170},
        {"field": "Famille", "header": "Famille", "width": 110},
        {"field": "Commercial", "header": "Commercial", "width": 130},
        {"field": "Societe", "header": "Societe", "width": 80},
        {"field": "Quantite", "header": "Qte", "width": 70, "type": "number"},
        {"field": "CA HT", "header": "CA HT", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Cout Revient", "header": "Cout Revient", "width": 110, "type": "number", "format": "#,##0.00"},
        {"field": "Marge Brute", "header": "Marge Brute", "width": 110, "type": "number", "format": "#,##0.00"},
        {"field": "Taux Marge %", "header": "Marge %", "width": 80, "type": "number", "format": "#,##0.00"},
        {"field": "Prix Moyen Vente", "header": "PV Moyen", "width": 100, "type": "number", "format": "#,##0.00"},
        {"field": "Prix Moyen Revient", "header": "PR Moyen", "width": 100, "type": "number", "format": "#,##0.00"},
    ]),
    ("Commandes en Cours", "DS_VTE_CMD_EN_COURS", [
        {"field": "Societe", "header": "Societe", "width": 90},
        {"field": "Num Piece", "header": "N. Piece", "width": 120},
        {"field": "Date Commande", "header": "Date Cmd", "width": 110, "type": "date"},
        {"field": "Code Client", "header": "Code Client", "width": 100},
        {"field": "Client", "header": "Client", "width": 200},
        {"field": "Commercial", "header": "Commercial", "width": 140},
        {"field": "Code Article", "header": "Code Article", "width": 110},
        {"field": "Designation", "header": "Designation", "width": 200},
        {"field": "Qte Commandee", "header": "Qte Cmd", "width": 90, "type": "number"},
        {"field": "Qte Livree", "header": "Qte Livree", "width": 90, "type": "number"},
        {"field": "Reste a Livrer", "header": "Reste", "width": 80, "type": "number"},
        {"field": "Montant HT", "header": "Montant HT", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Statut", "header": "Statut", "width": 100},
        {"field": "Anciennete Jours", "header": "Age (j)", "width": 80, "type": "number"},
    ]),
    ("Comparatif Annuel N vs N-1", "DS_VTE_COMPARATIF", [
        {"field": "Societe", "header": "Societe", "width": 90},
        {"field": "Mois", "header": "Mois", "width": 60, "type": "number"},
        {"field": "Nom Mois", "header": "Nom Mois", "width": 100},
        {"field": "CA HT N", "header": "CA N", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "CA HT N-1", "header": "CA N-1", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "Ecart", "header": "Ecart", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Evolution %", "header": "Evol %", "width": 90, "type": "number", "format": "#,##0.00"},
        {"field": "Marge N", "header": "Marge N", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Marge N-1", "header": "Marge N-1", "width": 120, "type": "number", "format": "#,##0.00"},
    ]),
    ("CA par Mode de Reglement", "DS_VTE_CA_MODE_REGLEMENT", [
        {"field": "Tiers Payeur", "header": "Tiers Payeur", "width": 200},
        {"field": "Categorie Comptable", "header": "Cat. Comptable", "width": 150},
        {"field": "Societe", "header": "Societe", "width": 90},
        {"field": "Nb Clients", "header": "Nb Clients", "width": 90, "type": "number"},
        {"field": "Nb Documents", "header": "Nb Docs", "width": 90, "type": "number"},
        {"field": "CA HT", "header": "CA HT", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "CA TTC", "header": "CA TTC", "width": 130, "type": "number", "format": "#,##0.00"},
    ]),
    ("Statistiques Remises", "DS_VTE_REMISES", [
        {"field": "Code Client", "header": "Code Client", "width": 100},
        {"field": "Client", "header": "Client", "width": 170},
        {"field": "Code Article", "header": "Code Article", "width": 100},
        {"field": "Designation", "header": "Designation", "width": 170},
        {"field": "Societe", "header": "Societe", "width": 80},
        {"field": "Remise 1", "header": "Remise 1", "width": 90},
        {"field": "Type Remise 1", "header": "Type R1", "width": 90},
        {"field": "Quantite", "header": "Qte", "width": 70, "type": "number"},
        {"field": "CA HT", "header": "CA HT", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Montant Brut", "header": "Montant Brut", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Total Remises", "header": "Total Remises", "width": 120, "type": "number", "format": "#,##0.00"},
    ]),

    # === RAPPORTS AVANCES ===
    ("CA par Depot", "DS_VTE_CA_DEPOT", [
        {"field": "Code Depot", "header": "Code Depot", "width": 90},
        {"field": "Depot", "header": "Depot", "width": 200},
        {"field": "Societe", "header": "Societe", "width": 90},
        {"field": "Nb Clients", "header": "Nb Clients", "width": 90, "type": "number"},
        {"field": "Nb Articles", "header": "Nb Articles", "width": 90, "type": "number"},
        {"field": "Quantite", "header": "Quantite", "width": 100, "type": "number"},
        {"field": "Poids Net Total", "header": "Poids Net", "width": 100, "type": "number", "format": "#,##0.00"},
        {"field": "CA HT", "header": "CA HT", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "Marge Brute", "header": "Marge Brute", "width": 120, "type": "number", "format": "#,##0.00"},
    ]),
    ("CA par Affaire", "DS_VTE_CA_AFFAIRE", [
        {"field": "Code Affaire", "header": "Code Affaire", "width": 110},
        {"field": "Affaire", "header": "Affaire", "width": 200},
        {"field": "Societe", "header": "Societe", "width": 90},
        {"field": "Nb Clients", "header": "Nb Clients", "width": 90, "type": "number"},
        {"field": "Nb Documents", "header": "Nb Docs", "width": 80, "type": "number"},
        {"field": "CA HT", "header": "CA HT", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "Marge Brute", "header": "Marge Brute", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Taux Marge %", "header": "Marge %", "width": 90, "type": "number", "format": "#,##0.00"},
    ]),
    ("Analyse RFM Clients", "DS_VTE_RFM", [
        {"field": "Code Client", "header": "Code Client", "width": 100},
        {"field": "Client", "header": "Client", "width": 180},
        {"field": "Societe", "header": "Societe", "width": 80},
        {"field": "Derniere Vente", "header": "Derniere Vente", "width": 110, "type": "date"},
        {"field": "Recence Jours", "header": "Recence (j)", "width": 90, "type": "number"},
        {"field": "Frequence", "header": "Frequence", "width": 90, "type": "number"},
        {"field": "Montant", "header": "Montant", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "Score R", "header": "R", "width": 50, "type": "number"},
        {"field": "Score F", "header": "F", "width": 50, "type": "number"},
        {"field": "Score M", "header": "M", "width": 50, "type": "number"},
        {"field": "Segment", "header": "Segment", "width": 130},
    ]),
    ("Saisonnalite des Ventes", "DS_VTE_SAISONNALITE", [
        {"field": "Mois", "header": "Mois", "width": 60, "type": "number"},
        {"field": "Nom Mois", "header": "Nom Mois", "width": 100},
        {"field": "Famille", "header": "Famille", "width": 130},
        {"field": "Societe", "header": "Societe", "width": 90},
        {"field": "CA N", "header": "CA N", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "CA N-1", "header": "CA N-1", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "CA N-2", "header": "CA N-2", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "Quantite Totale", "header": "Quantite", "width": 100, "type": "number"},
    ]),
    ("Panier Moyen par Client", "DS_VTE_PANIER_MOYEN", [
        {"field": "Code Client", "header": "Code Client", "width": 100},
        {"field": "Client", "header": "Client", "width": 200},
        {"field": "Societe", "header": "Societe", "width": 90},
        {"field": "Commercial", "header": "Commercial", "width": 140},
        {"field": "Nb Transactions", "header": "Nb Trans.", "width": 90, "type": "number"},
        {"field": "CA HT Total", "header": "CA HT Total", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "Panier Moyen HT", "header": "Panier Moyen", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Nb Articles Distincts", "header": "Nb Articles", "width": 90, "type": "number"},
        {"field": "Qte Moy par Transaction", "header": "Qte Moy/Trans", "width": 110, "type": "number", "format": "#,##0.00"},
    ]),
    ("Clients a Risque de Churn", "DS_VTE_CHURN", [
        {"field": "Code Client", "header": "Code Client", "width": 100},
        {"field": "Client", "header": "Client", "width": 180},
        {"field": "Societe", "header": "Societe", "width": 80},
        {"field": "Commercial", "header": "Commercial", "width": 130},
        {"field": "Derniere Vente", "header": "Derniere Vente", "width": 110, "type": "date"},
        {"field": "Jours Sans Achat", "header": "J. Sans Achat", "width": 100, "type": "number"},
        {"field": "CA 6M", "header": "CA 6M", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "CA 6M Precedent", "header": "CA 6M Prec.", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Evolution CA %", "header": "Evol. %", "width": 90, "type": "number", "format": "#,##0.00"},
        {"field": "Statut Risque", "header": "Statut Risque", "width": 120},
    ]),
    ("Analyse des Prix de Vente", "DS_VTE_ANALYSE_PRIX", [
        {"field": "Code Article", "header": "Code Article", "width": 110},
        {"field": "Designation", "header": "Designation", "width": 200},
        {"field": "Famille", "header": "Famille", "width": 120},
        {"field": "Societe", "header": "Societe", "width": 80},
        {"field": "Nb Lignes", "header": "Nb Lignes", "width": 80, "type": "number"},
        {"field": "Prix Min", "header": "Prix Min", "width": 100, "type": "number", "format": "#,##0.00"},
        {"field": "Prix Max", "header": "Prix Max", "width": 100, "type": "number", "format": "#,##0.00"},
        {"field": "Prix Moyen", "header": "Prix Moyen", "width": 100, "type": "number", "format": "#,##0.00"},
        {"field": "Ecart Type Prix", "header": "Ecart Type", "width": 100, "type": "number", "format": "#,##0.00"},
        {"field": "Cout Revient Moyen", "header": "Cout Rev. Moy", "width": 110, "type": "number", "format": "#,##0.00"},
        {"field": "Taux Marge Moy %", "header": "Marge %", "width": 90, "type": "number", "format": "#,##0.00"},
    ]),
    ("Taux de Service Client", "DS_VTE_TAUX_SERVICE", [
        {"field": "Code Client", "header": "Code Client", "width": 100},
        {"field": "Client", "header": "Client", "width": 200},
        {"field": "Societe", "header": "Societe", "width": 90},
        {"field": "Nb Documents Total", "header": "Nb Docs", "width": 80, "type": "number"},
        {"field": "Nb Livres", "header": "Nb Livres", "width": 80, "type": "number"},
        {"field": "Nb Retours", "header": "Nb Retours", "width": 80, "type": "number"},
        {"field": "Taux Retour %", "header": "Taux Retour %", "width": 110, "type": "number", "format": "#,##0.00"},
        {"field": "CA HT Net", "header": "CA HT Net", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "Montant Retours", "header": "Mnt Retours", "width": 120, "type": "number", "format": "#,##0.00"},
    ]),
    ("Analyse des Retours", "DS_VTE_ANALYSE_RETOURS", [
        {"field": "Code Article", "header": "Code Article", "width": 110},
        {"field": "Designation", "header": "Designation", "width": 180},
        {"field": "Famille", "header": "Famille", "width": 120},
        {"field": "Code Client", "header": "Code Client", "width": 100},
        {"field": "Client", "header": "Client", "width": 170},
        {"field": "Societe", "header": "Societe", "width": 80},
        {"field": "Type Document", "header": "Type Doc", "width": 160},
        {"field": "Quantite Retournee", "header": "Qte Retour", "width": 100, "type": "number"},
        {"field": "Montant HT Retour", "header": "Montant HT", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Nb Documents Retour", "header": "Nb Docs", "width": 80, "type": "number"},
    ]),
    ("Rentabilite par Client", "DS_VTE_RENTABILITE_CLIENT", [
        {"field": "Code Client", "header": "Code Client", "width": 100},
        {"field": "Client", "header": "Client", "width": 200},
        {"field": "Societe", "header": "Societe", "width": 80},
        {"field": "Commercial", "header": "Commercial", "width": 130},
        {"field": "CA HT", "header": "CA HT", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "Cout Revient Total", "header": "Cout Revient", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Marge Brute", "header": "Marge Brute", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Taux Marge %", "header": "Marge %", "width": 90, "type": "number", "format": "#,##0.00"},
        {"field": "Nb Transactions", "header": "Nb Trans.", "width": 80, "type": "number"},
        {"field": "Nb Articles", "header": "Nb Articles", "width": 80, "type": "number"},
        {"field": "Poids Total", "header": "Poids (Kg)", "width": 100, "type": "number", "format": "#,##0.00"},
        {"field": "CA par Kg", "header": "CA/Kg", "width": 90, "type": "number", "format": "#,##0.00"},
    ]),
    ("Fidelite Clients", "DS_VTE_FIDELITE", [
        {"field": "Code Client", "header": "Code Client", "width": 100},
        {"field": "Client", "header": "Client", "width": 180},
        {"field": "Societe", "header": "Societe", "width": 80},
        {"field": "Commercial", "header": "Commercial", "width": 130},
        {"field": "Premiere Vente", "header": "1ere Vente", "width": 100, "type": "date"},
        {"field": "Derniere Vente", "header": "Derniere Vente", "width": 110, "type": "date"},
        {"field": "Anciennete Mois", "header": "Anciennete (mois)", "width": 120, "type": "number"},
        {"field": "Nb Mois Actifs", "header": "Mois Actifs", "width": 100, "type": "number"},
        {"field": "Nb Transactions", "header": "Nb Trans.", "width": 80, "type": "number"},
        {"field": "CA HT Total", "header": "CA HT Total", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "CA Moyen Mensuel", "header": "CA Moy/Mois", "width": 120, "type": "number", "format": "#,##0.00"},
        {"field": "Segment Fidelite", "header": "Segment", "width": 140},
    ]),
    ("Performance des Devis", "DS_VTE_PERF_DEVIS", [
        {"field": "Code Client", "header": "Code Client", "width": 100},
        {"field": "Client", "header": "Client", "width": 200},
        {"field": "Societe", "header": "Societe", "width": 90},
        {"field": "Commercial", "header": "Commercial", "width": 140},
        {"field": "Nb Devis", "header": "Nb Devis", "width": 80, "type": "number"},
        {"field": "Montant Total Devis", "header": "Total Devis", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "Nb Convertis BL", "header": "Convertis BL", "width": 100, "type": "number"},
        {"field": "Taux Conversion %", "header": "Taux Conv. %", "width": 110, "type": "number", "format": "#,##0.00"},
        {"field": "Montant Moyen Devis", "header": "Moy. Devis", "width": 120, "type": "number", "format": "#,##0.00"},
    ]),
    ("Ventes Detail Complet", "DS_VTE_DETAIL_COMPLET", [
        {"field": "Societe", "header": "Societe", "width": 80},
        {"field": "Type Document", "header": "Type Doc", "width": 150},
        {"field": "Num Piece", "header": "N. Piece", "width": 110},
        {"field": "Date Document", "header": "Date Doc", "width": 100, "type": "date"},
        {"field": "Date BL", "header": "Date BL", "width": 100, "type": "date"},
        {"field": "Code Client", "header": "Client", "width": 90},
        {"field": "Client", "header": "Nom Client", "width": 160},
        {"field": "Commercial", "header": "Commercial", "width": 120},
        {"field": "Code Article", "header": "Article", "width": 90},
        {"field": "Designation", "header": "Designation", "width": 160},
        {"field": "Famille", "header": "Famille", "width": 100},
        {"field": "Quantite", "header": "Qte", "width": 70, "type": "number"},
        {"field": "Montant HT", "header": "HT", "width": 100, "type": "number", "format": "#,##0.00"},
        {"field": "Montant TTC", "header": "TTC", "width": 100, "type": "number", "format": "#,##0.00"},
        {"field": "Marge", "header": "Marge", "width": 100, "type": "number", "format": "#,##0.00"},
        {"field": "Depot", "header": "Depot", "width": 120},
        {"field": "Valorise CA", "header": "Val. CA", "width": 70},
    ]),
    ("Ventes par Type Document", "DS_VTE_PAR_TYPE_DOC", [
        {"field": "Type Document", "header": "Type Document", "width": 200},
        {"field": "Societe", "header": "Societe", "width": 90},
        {"field": "Nb Documents", "header": "Nb Documents", "width": 110, "type": "number"},
        {"field": "Nb Clients", "header": "Nb Clients", "width": 100, "type": "number"},
        {"field": "Quantite Totale", "header": "Quantite", "width": 100, "type": "number"},
        {"field": "Total HT", "header": "Total HT", "width": 140, "type": "number", "format": "#,##0.00"},
        {"field": "Total TTC", "header": "Total TTC", "width": 140, "type": "number", "format": "#,##0.00"},
        {"field": "Montant Moyen Ligne", "header": "Moy. Ligne", "width": 120, "type": "number", "format": "#,##0.00"},
    ]),
    ("Clients Inactifs", "DS_VTE_CLIENTS_INACTIFS", [
        {"field": "Code Client", "header": "Code Client", "width": 100},
        {"field": "Client", "header": "Client", "width": 200},
        {"field": "Societe", "header": "Societe", "width": 90},
        {"field": "Commercial", "header": "Commercial", "width": 140},
        {"field": "Derniere Vente", "header": "Derniere Vente", "width": 110, "type": "date"},
        {"field": "Jours Inactif", "header": "J. Inactif", "width": 90, "type": "number"},
        {"field": "CA HT Historique", "header": "CA Historique", "width": 130, "type": "number", "format": "#,##0.00"},
        {"field": "Nb Documents Historique", "header": "Nb Docs Hist.", "width": 100, "type": "number"},
    ]),
]

# =============================================================================
#  CREATE GRIDVIEWS
# =============================================================================
print(f"\nCreation de {len(gridviews)} GridViews...\n")

gv_ids = []
for nom, ds_code, columns in gridviews:
    cols_json = json.dumps(columns, ensure_ascii=False)
    cursor.execute("""
        INSERT INTO APP_GridViews (nom, description, columns_config, data_source_code, page_size, actif, is_public, show_totals)
        OUTPUT INSERTED.id
        VALUES (?, ?, ?, ?, 50, 1, 0, 1)
    """, (nom, f"Ventes - {nom}", cols_json, ds_code))
    gv_id = cursor.fetchone()[0]
    gv_ids.append((gv_id, nom, ds_code))
    print(f"  GV {gv_id:3d}: {nom}")

# =============================================================================
#  CREATE MENU TREE
# =============================================================================
print(f"\nCreation de l'arborescence de menus...\n")

# Root: Ventes
cursor.execute("""
    INSERT INTO APP_Menus (nom, type, parent_id, ordre, actif)
    OUTPUT INSERTED.id
    VALUES ('Ventes', 'folder', NULL, 1, 1)
""")
root_id = cursor.fetchone()[0]
print(f"  Root: Ventes (id={root_id})")

# Sub-folders
folders = [
    ("Documents Ventes", 1, 7),        # items 0-6
    ("Analyses Ventes", 2, 13),         # items 7-19
    ("Rapports Avances", 3, 15),        # items 20-34
]

folder_ids = {}
for folder_name, ordre, count in folders:
    cursor.execute("""
        INSERT INTO APP_Menus (nom, type, parent_id, ordre, actif)
        OUTPUT INSERTED.id
        VALUES (?, 'folder', ?, ?, 1)
    """, (folder_name, root_id, ordre))
    fid = cursor.fetchone()[0]
    folder_ids[folder_name] = fid
    print(f"  Folder: {folder_name} (id={fid})")

# Menu items
item_index = 0
menu_mapping = [
    ("Documents Ventes", 7),
    ("Analyses Ventes", 13),
    ("Rapports Avances", 15),
]

for folder_name, count in menu_mapping:
    fid = folder_ids[folder_name]
    for i in range(count):
        gv_id, nom, ds_code = gv_ids[item_index]
        cursor.execute("""
            INSERT INTO APP_Menus (nom, type, target_id, parent_id, ordre, actif)
            VALUES (?, 'gridview', ?, ?, ?, 1)
        """, (nom, gv_id, fid, i + 1))
        item_index += 1

print(f"\n  {item_index} menu items crees")

# =============================================================================
#  SUMMARY
# =============================================================================
cursor.execute("SELECT COUNT(*) FROM APP_DataSources_Templates")
t_count = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM APP_GridViews")
g_count = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM APP_Menus")
m_count = cursor.fetchone()[0]

print(f"""
============================================
  RESUME
============================================
  DataSource Templates : {t_count}
  GridViews            : {g_count}
  Menus                : {m_count}

  35 rapports Ventes crees avec succes!
============================================
""")

cursor.close()
conn.close()
