"""
Fix final KASOFT : mettre les bons credentials optiboard dans APP_DWH
"""
import pyodbc, sys
conn_str = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019;TrustServerCertificate=yes;"
conn = pyodbc.connect(conn_str, timeout=15)
conn.autocommit = False
cur = conn.cursor()

cur.execute("""
    UPDATE APP_DWH SET
        serveur_optiboard  = '.',
        base_optiboard     = 'OptiBoard_cltKASOFT',
        user_optiboard     = 'sa',
        password_optiboard = 'SQL@2019',
        actif = 1
    WHERE code = 'KASOFT'
""")
print(f"APP_DWH mis a jour : {cur.rowcount} ligne(s)")
conn.commit()

cur.execute("SELECT code, actif, serveur_optiboard, base_optiboard, user_optiboard FROM APP_DWH WHERE code='KASOFT'")
row = cur.fetchone()
print(f"Verification: code={row[0]}, actif={row[1]}, serveur_optiboard={row[2]}, base_optiboard={row[3]}, user={row[4]}")
conn.close()
print("Done.")
