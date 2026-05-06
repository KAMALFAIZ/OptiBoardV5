"""
Mise à jour ciblée de la datasource DS_VTE_TAUX_SERVICE :
  - Filtre WHERE_CA (ajout [Valorise CA]='Oui')
  - CA HT Net = SUM([Montant HT Net]) avec WHERE_CA
  => aligne le CA HT sur la valeur de référence 309 987 555,38
"""
import pyodbc

conn_str = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019"

BASE_JOIN = """FROM [Lignes_des_ventes] li
INNER JOIN [Entête_des_ventes] en
    ON li.[societe] = en.[societe]
    AND li.[Type Document] = en.[Type Document]
    AND li.[N° Pièce] = en.[N° pièce]"""

WHERE_CA = (
    "WHERE li.[Valorise CA] = 'Oui'"
    " AND li.[Date BL] BETWEEN @dateDebut AND @dateFin"
    " AND (@societe IS NULL OR li.[societe] = @societe)"
    " AND (@commercial IS NULL OR en.[Nom représentant] = @commercial)"
)

new_query = f"""SELECT
    li.[Code client] AS [Code Client],
    li.[Intitulé client] AS [Client],
    li.[societe] AS [Societe],
    COUNT(DISTINCT li.[N° Pièce]) AS [Nb Documents Total],
    COUNT(DISTINCT CASE WHEN li.[Type Document] IN ('Facture', 'Facture comptabilisée', 'Bon de livraison') THEN li.[N° Pièce] END) AS [Nb Livres],
    COUNT(DISTINCT CASE WHEN li.[Type Document] IN ('Bon de retour', 'Facture de retour', 'Facture de retour comptabilisée') THEN li.[N° Pièce] END) AS [Nb Retours],
    CASE WHEN COUNT(DISTINCT li.[N° Pièce]) > 0
        THEN ROUND(100.0 * COUNT(DISTINCT CASE WHEN li.[Type Document] IN ('Bon de retour', 'Facture de retour', 'Facture de retour comptabilisée') THEN li.[N° Pièce] END)
            / COUNT(DISTINCT li.[N° Pièce]), 2)
        ELSE 0 END AS [Taux Retour %],
    SUM(li.[Montant HT Net]) AS [CA HT Net],
    SUM(CASE WHEN li.[Type Document] IN ('Bon de retour', 'Facture de retour', 'Facture de retour comptabilisée')
        THEN ABS(li.[Montant HT Net]) ELSE 0 END) AS [Montant Retours]
{BASE_JOIN}
{WHERE_CA}
GROUP BY li.[Code client], li.[Intitulé client], li.[societe]
HAVING COUNT(DISTINCT li.[N° Pièce]) >= 3
ORDER BY [Taux Retour %] DESC"""

conn = pyodbc.connect(conn_str, autocommit=True)
cursor = conn.cursor()

cursor.execute(
    "UPDATE APP_DataSources_Templates SET query_template = ? WHERE code = ?",
    (new_query, "DS_VTE_TAUX_SERVICE")
)
print(f"Lignes mises à jour : {cursor.rowcount}")
cursor.execute(
    "SELECT id, code, nom FROM APP_DataSources_Templates WHERE code = 'DS_VTE_TAUX_SERVICE'"
)
row = cursor.fetchone()
if row:
    print(f"  id={row[0]}  code={row[1]}  nom={row[2]}")
conn.close()
print("Done.")
