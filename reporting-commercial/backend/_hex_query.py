import pyodbc

conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=kasoft.selfip.net;'
    'DATABASE=DWH_ESSAIDI26;'
    'UID=sa;PWD=SQL@2019;'
    'TrustServerCertificate=yes'
)
cursor = conn.cursor()

# Get exact table name hex
cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME LIKE '%glement%Client%'")
for r in cursor.fetchall():
    tname = r[0]
    hex_repr = ' '.join(f'{ord(c):04x}' for c in tname)
    print(f'TABLE: {tname} => {hex_repr}')

# Get column hex
tbl = 'R\u00e8glements_Clients'
cursor.execute(f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{tbl}' ORDER BY ORDINAL_POSITION")
for r in cursor.fetchall():
    col = r[0]
    hex_repr = ' '.join(f'{ord(c):04x}' for c in col)
    print(f'COL: {col} => {hex_repr}')

# Also check: does 'Code client original' and 'Intitule original' exist?
try:
    cursor.execute(f"SELECT TOP 2 [Code client original], [Intitul\u00e9 original] FROM [{tbl}]")
    for r in cursor.fetchall():
        print(f'Code client original={r[0]}, Intitule original={r[1]}')
except Exception as e:
    print(f'ERROR querying Code client original / Intitule original: {e}')

conn.close()
