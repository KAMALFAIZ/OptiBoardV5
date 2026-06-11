import pyodbc, sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CONN = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_cltKA;UID=sa;PWD=SQL@2019;TrustServerCertificate=yes"
c = pyodbc.connect(CONN)
cur = c.cursor()
cur.execute("""
    SELECT id, table_name, target_table, is_customized, is_inherited,
           LEN(source_query) as qlen,
           LEFT(CAST(source_query AS NVARCHAR(MAX)), 200) as qstart
    FROM APP_ETL_Agent_Tables
    WHERE target_table = N'Entête_des_ventes'
""")
rows = cur.fetchall()
if not rows:
    print("Aucune entrée trouvée pour Entête_des_ventes")
else:
    for r in rows:
        print(f"id={r[0]} | table={r[1]} | target={r[2]}")
        print(f"customized={r[3]} | inherited={r[4]} | qlen={r[5]}")
        print(f"query[:200] = {r[6]}")
        print()
