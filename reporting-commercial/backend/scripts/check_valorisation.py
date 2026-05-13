# -*- coding: utf-8 -*-
import pyodbc
conn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019', timeout=15)
c = conn.cursor()
c.execute("SELECT id, code, query_template FROM APP_DataSources_Templates WHERE code IN ('DS_CA_MARGE_DYNAMIQUE', 'DS_COM_MARGE_PAR_LIGNE') AND actif = 1")
for row in c.fetchall():
    print(f'=== {row[1]} (id={row[0]}) ===')
    print(row[2])
    print()
conn.close()
