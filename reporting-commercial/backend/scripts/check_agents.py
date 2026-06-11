import pyodbc, sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
CONN = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019;TrustServerCertificate=yes"
c = pyodbc.connect(CONN)
cur = c.cursor()

# Chercher les tables ETL agents
cur.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME LIKE '%ETL%Agent%' OR TABLE_NAME LIKE '%Agent%ETL%'")
print("Tables ETL Agent:", [r[0] for r in cur.fetchall()])

# Lister les DWH
print("\n=== APP_ClientDB ===")
cur.execute("SELECT dwh_code, db_name FROM APP_ClientDB ORDER BY dwh_code")
for r in cur.fetchall():
    print(f"  {r[0]} -> {r[1]}")

# Chercher un DWH avec "GB" ou "Saint Gobain" ou "MATERIAL"
print("\n=== APP_DWH (recherche GB/MATERIAL) ===")
try:
    cur.execute("SELECT dwh_code, nom, db_name FROM APP_DWH WHERE dwh_code LIKE '%GB%' OR nom LIKE '%GOBAIN%' OR nom LIKE '%MATERIAL%' OR db_name LIKE '%MATERIAL%'")
    for r in cur.fetchall():
        print(f"  {r[0]} | {r[1]} | {r[2]}")
except Exception as e:
    print(f"  {e}")
