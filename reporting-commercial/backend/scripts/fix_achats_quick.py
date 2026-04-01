"""Quick fix for Achats templates - uses pyodbc directly to avoid hanging"""
import pyodbc
import sys

conn_str = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019"
conn = pyodbc.connect(conn_str, autocommit=True)
cursor = conn.cursor()

# Fix 1: DB_Id joins -> proper column joins
join_fixes = [
    ("DS_ACHATS_PAR_FOURNISSEUR", "l.[DB_Id] = f.[DB_Id] AND l.[Code fournisseur] = f.[Code fournisseur]", "l.[Code fournisseur] = f.[Code fournisseur] AND l.[societe] = f.[societe]"),
    ("DS_ACHATS_PAR_ACHETEUR", "l.[DB_Id] = f.[DB_Id] AND l.[Code fournisseur] = f.[Code fournisseur]", "l.[Code fournisseur] = f.[Code fournisseur] AND l.[societe] = f.[societe]"),
    ("DS_TOP_FOURNISSEURS", "l.[DB_Id] = f.[DB_Id] AND l.[Code fournisseur] = f.[Code fournisseur]", "l.[Code fournisseur] = f.[Code fournisseur] AND l.[societe] = f.[societe]"),
    ("DS_ACHATS_PAR_ARTICLE", "l.[DB_Id] = a.[DB_Id] AND l.[Code article] = a.[Code Article]", "l.[Code article] = a.[Code Article] AND l.[societe] = a.[societe]"),
    ("DS_ACHATS_PAR_FAMILLE", "l.[DB_Id] = a.[DB_Id] AND l.[Code article] = a.[Code Article]", "l.[Code article] = a.[Code Article] AND l.[societe] = a.[societe]"),
    ("DS_ACHATS_PAR_CATALOGUE", "l.[DB_Id] = a.[DB_Id] AND l.[Code article] = a.[Code Article]", "l.[Code article] = a.[Code Article] AND l.[societe] = a.[societe]"),
    ("DS_TOP_ARTICLES_ACHATS", "l.[DB_Id] = a.[DB_Id] AND l.[Code article] = a.[Code Article]", "l.[Code article] = a.[Code Article] AND l.[societe] = a.[societe]"),
    ("DS_EVOLUTION_PRIX_ACHATS", "l.[DB_Id] = a.[DB_Id] AND l.[Code article] = a.[Code Article]", "l.[Code article] = a.[Code Article] AND l.[societe] = a.[societe]"),
    ("DS_COMPARAISON_FOURNISSEURS", "l.[DB_Id] = a.[DB_Id] AND l.[Code article] = a.[Code Article]", "l.[Code article] = a.[Code Article] AND l.[societe] = a.[societe]"),
    ("DS_COMMANDES_ACHATS", "l.[DB_Id] = e.[DB_Id] AND l.[Type Document] = e.[Type Document]", "l.[societe] = e.[societe] AND l.[Type Document] = e.[Type Document]"),
    ("DS_COMMANDES_ACHATS_EN_COURS", "l.[DB_Id] = e.[DB_Id] AND l.[Type Document] = e.[Type Document]", "l.[societe] = e.[societe] AND l.[Type Document] = e.[Type Document]"),
]

print("=== Fix 1: DB_Id JOIN fixes ===")
for code, old, new in join_fixes:
    cursor.execute("SELECT id, query_template FROM APP_DataSources_Templates WHERE code = ?", (code,))
    row = cursor.fetchone()
    if row and old in row.query_template:
        fixed = row.query_template.replace(old, new)
        cursor.execute("UPDATE APP_DataSources_Templates SET query_template = ? WHERE id = ?", (fixed, row.id))
        print(f"  OK: {code} (id={row.id})")
    else:
        print(f"  SKIP: {code}")

# Fix 2: l.[Désignation Article] -> l.[Désignation] in Lignes_des_achats references
desig_codes = ["DS_FACTURES_ACHATS", "DS_BONS_RECEPTION", "DS_COMMANDES_ACHATS", "DS_AVOIRS_ACHATS", "DS_COMMANDES_ACHATS_EN_COURS"]

print("\n=== Fix 2: Designation Article -> Designation ===")
for code in desig_codes:
    cursor.execute("SELECT id, query_template FROM APP_DataSources_Templates WHERE code = ?", (code,))
    row = cursor.fetchone()
    if row:
        q = row.query_template
        # The column in Lignes_des_achats is [Désignation] not [Désignation Article]
        # But in the query it's referenced as l.[Désignation Article]
        if "signation Article]" in q:
            fixed = q.replace("signation Article]", "signation]")
            cursor.execute("UPDATE APP_DataSources_Templates SET query_template = ? WHERE id = ?", (fixed, row.id))
            print(f"  OK: {code} (id={row.id})")
        else:
            print(f"  SKIP: {code} - no match")
    else:
        print(f"  SKIP: {code} - not found")

cursor.close()
conn.close()
print("\nDone!")
