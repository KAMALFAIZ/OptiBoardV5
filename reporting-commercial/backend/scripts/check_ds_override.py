import pyodbc
conn_str = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019"
conn = pyodbc.connect(conn_str)
cursor = conn.cursor()

# 1. Verifier le template mis a jour
cursor.execute("SELECT id, code, LEFT(query_template, 300) FROM APP_DataSources_Templates WHERE code='DS_VTE_TAUX_SERVICE'")
row = cursor.fetchone()
print("TEMPLATE:")
print(f"  id={row[0]}, code={row[1]}")
print(f"  query={row[2]}")
print()

# 2. Chercher des overrides dans les bases DWH
cursor.execute("SELECT name FROM sys.databases WHERE name LIKE 'OptiBoard[_]%' AND name != 'OptiBoard_SaaS'")
dwh_dbs = [r[0] for r in cursor.fetchall()]
print(f"DWH databases: {dwh_dbs}")

for db in dwh_dbs:
    try:
        cursor.execute(f"SELECT id, code, LEFT(query_template,150) FROM [{db}].dbo.APP_DataSources WHERE code='DS_VTE_TAUX_SERVICE'")
        rows = cursor.fetchall()
        if rows:
            print(f"\nOVERRIDE in {db}:")
            for r in rows:
                print(f"  id={r[0]}, code={r[1]}")
                print(f"  query={r[2]}")
        else:
            print(f"  {db}: pas d'override")
    except Exception as e:
        print(f"  {db}: {e}")

conn.close()
