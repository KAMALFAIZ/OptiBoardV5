import pyodbc, sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CONN = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019;TrustServerCertificate=yes"
c = pyodbc.connect(CONN)
cur = c.cursor()

# Vérifier que APP_ETL_Tables_Config existe et voir ses colonnes
cur.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'APP_ETL_Tables_Config' ORDER BY ORDINAL_POSITION")
cols = [r[0] for r in cur.fetchall()]
print("Colonnes APP_ETL_Tables_Config:", cols)
print()

# Chercher les entrées liées aux entêtes de ventes
cur.execute("SELECT TOP 20 * FROM APP_ETL_Tables_Config ORDER BY id")
rows = cur.fetchall()
col_names = [desc[0] for desc in cur.description]
print("Colonnes:", col_names)
print()
for r in rows:
    d = dict(zip(col_names, r))
    sq = str(d.get('source_query', ''))[:80]
    print(f"code={d.get('code')} | table_name={d.get('table_name')} | target={d.get('target_table')} | qlen={len(sq)}")
    print(f"  query: {sq}")
    print()
