import pyodbc
conn_str = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019;TrustServerCertificate=yes;"
conn = pyodbc.connect(conn_str, timeout=15)
conn.autocommit = False
cursor = conn.cursor()

# Verifier avant
cursor.execute("SELECT actif FROM APP_DWH WHERE code='KASOFT'")
print(f"Avant: actif = {cursor.fetchone()[0]}")

# Mettre a jour
cursor.execute("UPDATE APP_DWH SET actif = 0 WHERE code = 'KASOFT'")
print(f"Rows affected: {cursor.rowcount}")
conn.commit()

# Verifier apres
cursor.execute("SELECT actif FROM APP_DWH WHERE code='KASOFT'")
print(f"Apres: actif = {cursor.fetchone()[0]}")

conn.close()
print("Done.")
