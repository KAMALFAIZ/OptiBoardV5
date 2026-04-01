import pyodbc
conn_str = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019;TrustServerCertificate=yes;"
conn = pyodbc.connect(conn_str, timeout=15)
cursor = conn.cursor()
cursor.execute("SELECT code, nom, actif FROM APP_DWH WHERE code='KASOFT'")
row = cursor.fetchone()
print(f"code={row[0]}, nom={row[1]}, actif={row[2]}, type={type(row[2])}")
conn.close()
