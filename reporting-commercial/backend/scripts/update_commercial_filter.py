"""
=============================================================================
  UPDATE - Ajout du filtre @commercial sur toutes les datasources ventes

  Problème résolu: le filtre Commercial dans les pivots n'avait aucun effet
  sur la requête SQL car @commercial n'existait pas dans le WHERE.

  Ce script met à jour les query_template de toutes les datasources ventes
  pour ajouter AND (@commercial IS NULL OR en.[Nom représentant] = @commercial)

  Exécution: python scripts/update_commercial_filter.py
=============================================================================
"""
import pyodbc
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

conn_str = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019"
conn = pyodbc.connect(conn_str, autocommit=True)
cursor = conn.cursor()

# ============================================================================
#  COMMON SQL FRAGMENTS (mêmes que create_ventes_reports.py)
# ============================================================================
BASE_JOIN = """FROM [Lignes_des_ventes] li
INNER JOIN [Entête_des_ventes] en
    ON li.[societe] = en.[societe]
    AND li.[Type Document] = en.[Type Document]
    AND li.[N° Pièce] = en.[N° pièce]"""

CA_FILTER = "li.[Valorise CA] = 'Oui'"
DATE_FILTER = "li.[Date BL] BETWEEN @dateDebut AND @dateFin"
SOCIETE_FILTER = "(@societe IS NULL OR li.[societe] = @societe)"
COMMERCIAL_FILTER = "(@commercial IS NULL OR en.[Nom représentant] = @commercial)"

WHERE_CA = f"WHERE {CA_FILTER} AND {DATE_FILTER} AND {SOCIETE_FILTER} AND {COMMERCIAL_FILTER}"
WHERE_ALL = f"WHERE {DATE_FILTER} AND {SOCIETE_FILTER} AND {COMMERCIAL_FILTER}"

# ============================================================================
#  REQUÊTES MISES À JOUR (même contenu que create_ventes_reports.py après modif)
# ============================================================================
updates = []

# 1. Factures de Ventes
updates.append(("DS_VTE_FACTURES", f"""SELECT
    li.[societe] AS [Societe],
    li.[Type Document],
    li.[N° Pièce] AS [Num Piece],
    li.[Date document] AS [Date Document],
    li.[Code client] AS [Code Client],
    li.[Intitulé client] AS [Client],
    en.[Nom représentant] AS [Commercial],
    li.[Code article] AS [Code Article],
    li.[Désignation ligne] AS [Designation],
    li.[Quantité] AS [Quantite],
    li.[Prix unitaire] AS [Prix Unitaire],
    li.[Montant HT Net] AS [Montant HT],
    li.[Montant TTC Net] AS [Montant TTC],
    li.[Catalogue 1] AS [Famille],
    li.[Code dépôt] AS [Code Depot],
    li.[Intitulé dépôt] AS [Depot],
    en.[Statut],
    en.Souche
{BASE_JOIN}
WHERE li.[Type Document] IN ('Facture', 'Facture comptabilisée')
  AND {DATE_FILTER} AND {SOCIETE_FILTER} AND {COMMERCIAL_FILTER}
ORDER BY li.[Date document] DESC, li.[N° Pièce]"""))

# 2. Bons de Livraison
updates.append(("DS_VTE_BL", f"""SELECT
    li.[societe] AS [Societe],
    li.[N° Pièce BL] AS [Num BL],
    li.[Date BL] AS [Date BL],
    li.[N° Pièce] AS [Num Piece Origine],
    li.[Type Document],
    li.[Code client] AS [Code Client],
    li.[Intitulé client] AS [Client],
    en.[Nom représentant] AS [Commercial],
    li.[Code article] AS [Code Article],
    li.[Désignation ligne] AS [Designation],
    li.[Quantité BL] AS [Quantite BL],
    li.[Montant HT Net] AS [Montant HT],
    li.[Montant TTC Net] AS [Montant TTC],
    li.[Code dépôt] AS [Code Depot],
    li.[Intitulé dépôt] AS [Depot]
{BASE_JOIN}
WHERE li.[N° Pièce BL] <> ''
  AND {DATE_FILTER} AND {SOCIETE_FILTER} AND {COMMERCIAL_FILTER}
ORDER BY li.[Date BL] DESC"""))

# 3. Bons de Commande
updates.append(("DS_VTE_BC", f"""SELECT
    li.[societe] AS [Societe],
    li.[N° Pièce BC] AS [Num BC],
    li.[Date BC] AS [Date BC],
    li.[N° Pièce] AS [Num Piece Origine],
    li.[Type Document],
    li.[Code client] AS [Code Client],
    li.[Intitulé client] AS [Client],
    en.[Nom représentant] AS [Commercial],
    li.[Code article] AS [Code Article],
    li.[Désignation ligne] AS [Designation],
    li.[Quantité BC] AS [Quantite BC],
    li.[Montant HT Net] AS [Montant HT],
    li.[Montant TTC Net] AS [Montant TTC]
{BASE_JOIN}
WHERE li.[N° Pièce BC] <> ''
  AND {DATE_FILTER} AND {SOCIETE_FILTER} AND {COMMERCIAL_FILTER}
ORDER BY li.[Date BC] DESC"""))

# 4. Devis
updates.append(("DS_VTE_DEVIS", f"""SELECT
    li.[societe] AS [Societe],
    li.[N° Pièce] AS [Num Piece],
    li.[Date document] AS [Date Document],
    li.[Code client] AS [Code Client],
    li.[Intitulé client] AS [Client],
    en.[Nom représentant] AS [Commercial],
    li.[Code article] AS [Code Article],
    li.[Désignation ligne] AS [Designation],
    li.[Quantité devis] AS [Quantite],
    li.[Prix unitaire] AS [Prix Unitaire],
    li.[Montant HT Net] AS [Montant HT],
    li.[Montant TTC Net] AS [Montant TTC],
    en.[Statut],
    li.[Catalogue 1] AS [Famille]
{BASE_JOIN}
WHERE li.[Type Document] = 'Devis'
  AND {DATE_FILTER} AND {SOCIETE_FILTER} AND {COMMERCIAL_FILTER}
ORDER BY li.[Date document] DESC"""))

# 5. Avoirs
updates.append(("DS_VTE_AVOIRS", f"""SELECT
    li.[societe] AS [Societe],
    li.[Type Document],
    li.[N° Pièce] AS [Num Piece],
    li.[Date document] AS [Date Document],
    li.[Code client] AS [Code Client],
    li.[Intitulé client] AS [Client],
    en.[Nom représentant] AS [Commercial],
    li.[Code article] AS [Code Article],
    li.[Désignation ligne] AS [Designation],
    li.[Quantité] AS [Quantite],
    li.[Montant HT Net] AS [Montant HT],
    li.[Montant TTC Net] AS [Montant TTC],
    li.[Catalogue 1] AS [Famille]
{BASE_JOIN}
WHERE li.[Type Document] IN ('Bon avoir financier', 'Facture avoir', 'Facture avoir comptabilisée')
  AND {DATE_FILTER} AND {SOCIETE_FILTER} AND {COMMERCIAL_FILTER}
ORDER BY li.[Date document] DESC"""))

# 6. Bons de Retour
updates.append(("DS_VTE_RETOURS", f"""SELECT
    li.[societe] AS [Societe],
    li.[Type Document],
    li.[N° Pièce] AS [Num Piece],
    li.[Date document] AS [Date Document],
    li.[Code client] AS [Code Client],
    li.[Intitulé client] AS [Client],
    en.[Nom représentant] AS [Commercial],
    li.[Code article] AS [Code Article],
    li.[Désignation ligne] AS [Designation],
    li.[Quantité] AS [Quantite],
    li.[Montant HT Net] AS [Montant HT],
    li.[Montant TTC Net] AS [Montant TTC],
    li.[Code dépôt] AS [Code Depot],
    li.[Intitulé dépôt] AS [Depot]
{BASE_JOIN}
WHERE li.[Type Document] IN ('Bon de retour', 'Facture de retour', 'Facture de retour comptabilisée')
  AND {DATE_FILTER} AND {SOCIETE_FILTER} AND {COMMERCIAL_FILTER}
ORDER BY li.[Date document] DESC"""))

# 7. Préparations de Livraison
updates.append(("DS_VTE_PL", f"""SELECT
    li.[societe] AS [Societe],
    li.[N° pièce PL] AS [Num PL],
    li.[Date PL] AS [Date PL],
    li.[N° Pièce] AS [Num Piece Origine],
    li.[Code client] AS [Code Client],
    li.[Intitulé client] AS [Client],
    en.[Nom représentant] AS [Commercial],
    li.[Code article] AS [Code Article],
    li.[Désignation ligne] AS [Designation],
    li.[Quantité PL] AS [Quantite PL],
    li.[Montant HT Net] AS [Montant HT],
    li.[Code dépôt] AS [Code Depot],
    li.[Intitulé dépôt] AS [Depot]
{BASE_JOIN}
WHERE li.[Type Document] = 'Préparation de livraison'
  AND {DATE_FILTER} AND {SOCIETE_FILTER} AND {COMMERCIAL_FILTER}
ORDER BY li.[Date PL] DESC"""))

# 8. CA par Client
updates.append(("DS_VTE_CA_CLIENT", f"""SELECT
    li.[Code client] AS [Code Client],
    li.[Intitulé client] AS [Client],
    li.[societe] AS [Societe],
    en.[Nom représentant] AS [Commercial],
    COUNT(DISTINCT li.[N° Pièce]) AS [Nb Documents],
    SUM(li.[Quantité]) AS [Quantite Totale],
    SUM(li.[Montant HT Net]) AS [CA HT],
    SUM(li.[Montant TTC Net]) AS [CA TTC],
    SUM(li.[Quantité] * li.[Prix de revient]) AS [Cout Revient],
    SUM(li.[Montant HT Net]) - SUM(li.[Quantité] * li.[Prix de revient]) AS [Marge Brute],
    CASE WHEN SUM(li.[Montant HT Net]) <> 0
        THEN ROUND(100.0 * (SUM(li.[Montant HT Net]) - SUM(li.[Quantité] * li.[Prix de revient])) / SUM(li.[Montant HT Net]), 2)
        ELSE 0 END AS [Taux Marge %]
{BASE_JOIN}
{WHERE_CA}
GROUP BY li.[Code client], li.[Intitulé client], li.[societe], en.[Nom représentant]
ORDER BY [CA HT] DESC"""))

# 9. CA par Article
updates.append(("DS_VTE_CA_ARTICLE", f"""SELECT
    li.[Code article] AS [Code Article],
    li.[Désignation ligne] AS [Designation],
    li.[Catalogue 1] AS [Famille],
    li.[societe] AS [Societe],
    COUNT(DISTINCT li.[Code client]) AS [Nb Clients],
    SUM(li.[Quantité]) AS [Quantite Vendue],
    SUM(li.[Montant HT Net]) AS [CA HT],
    SUM(li.[Montant TTC Net]) AS [CA TTC],
    SUM(li.[Quantité] * li.[Prix de revient]) AS [Cout Revient],
    SUM(li.[Montant HT Net]) - SUM(li.[Quantité] * li.[Prix de revient]) AS [Marge Brute],
    CASE WHEN SUM(li.[Montant HT Net]) <> 0
        THEN ROUND(100.0 * (SUM(li.[Montant HT Net]) - SUM(li.[Quantité] * li.[Prix de revient])) / SUM(li.[Montant HT Net]), 2)
        ELSE 0 END AS [Taux Marge %],
    AVG(li.[Prix unitaire]) AS [Prix Moyen]
{BASE_JOIN}
{WHERE_CA}
GROUP BY li.[Code article], li.[Désignation ligne], li.[Catalogue 1], li.[societe]
ORDER BY [CA HT] DESC"""))

# 10. CA par Commercial
updates.append(("DS_VTE_CA_COMMERCIAL", f"""SELECT
    en.[Code représentant] AS [Code Commercial],
    ISNULL(en.[Nom représentant], 'Non affecté') AS [Commercial],
    li.[societe] AS [Societe],
    COUNT(DISTINCT li.[Code client]) AS [Nb Clients],
    COUNT(DISTINCT li.[N° Pièce]) AS [Nb Documents],
    SUM(li.[Quantité]) AS [Quantite],
    SUM(li.[Montant HT Net]) AS [CA HT],
    SUM(li.[Montant TTC Net]) AS [CA TTC],
    SUM(li.[Montant HT Net]) - SUM(li.[Quantité] * li.[Prix de revient]) AS [Marge Brute],
    CASE WHEN SUM(li.[Montant HT Net]) <> 0
        THEN ROUND(100.0 * (SUM(li.[Montant HT Net]) - SUM(li.[Quantité] * li.[Prix de revient])) / SUM(li.[Montant HT Net]), 2)
        ELSE 0 END AS [Taux Marge %]
{BASE_JOIN}
{WHERE_CA}
GROUP BY en.[Code représentant], en.[Nom représentant], li.[societe]
ORDER BY [CA HT] DESC"""))

# ============================================================================
#  APPLY UPDATES
# ============================================================================
print(f"Mise à jour du filtre @commercial sur {len(updates)} datasources...\n")

ok = 0
for code, query in updates:
    cursor.execute(
        "UPDATE APP_DataSources_Templates SET query_template = ? WHERE code = ?",
        (query, code)
    )
    rows = cursor.rowcount
    if rows > 0:
        print(f"  ✓ {code}")
        ok += 1
    else:
        print(f"  ✗ {code} — non trouvé en base")

print(f"\n{ok}/{len(updates)} datasources mis à jour.")
print("Le filtre @commercial est maintenant actif sur toutes ces datasources.")
