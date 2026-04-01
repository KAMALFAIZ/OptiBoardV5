import pyodbc
conn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019;TrustServerCertificate=yes')
cursor = conn.cursor()

cursor.execute('SELECT MAX(id) FROM APP_DataSources_Templates')
print('Max DataSource Template ID:', cursor.fetchone()[0])

cursor.execute('SELECT MAX(id) FROM APP_GridViews')
print('Max GridView ID:', cursor.fetchone()[0])

cursor.execute('SELECT MAX(id) FROM APP_Pivots_V2')
print('Max Pivot ID:', cursor.fetchone()[0])

cursor.execute('SELECT MAX(id) FROM APP_Dashboards')
print('Max Dashboard ID:', cursor.fetchone()[0])

cursor.execute('SELECT MAX(id) FROM APP_Menus')
print('Max Menu ID:', cursor.fetchone()[0])

cursor.execute('SELECT MAX(id) FROM APP_DataSources')
print('Max DataSource ID:', cursor.fetchone()[0])

conn.close()
