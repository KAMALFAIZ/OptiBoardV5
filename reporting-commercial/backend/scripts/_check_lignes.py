"""Verifie que Lignes_des_ventes a LEFT OUTER JOIN F_FAMILLE."""
import pyodbc, os

env = {}
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
with open(env_path, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            key, val = line.split('=', 1)
            env[key.strip()] = val.strip()

server = env.get('DB_SERVER', 'localhost')
port = env.get('DB_PORT', '1433')
db = env.get('DB_NAME', 'OptiBoard_SaaS')
user = env.get('DB_USER', 'sa')
pwd = env.get('DB_PASSWORD', '')

conn_str = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={server},{port};DATABASE={db};"
    f"UID={user};PWD={pwd};TrustServerCertificate=yes"
)
conn = pyodbc.connect(conn_str)
cursor = conn.cursor()

cursor.execute("SELECT table_name, source_query FROM ETL_Tables_Config WHERE table_name LIKE '%ignes%ventes%'")
rows = cursor.fetchall()
print(f"Found {len(rows)} matching rows")
for row in rows:
    print(f"  table_name = '{row.table_name}'")

if not rows:
    cursor.execute("SELECT table_name FROM ETL_Tables_Config")
    print("All table names:")
    for r in cursor.fetchall():
        print(f"  '{r.table_name}'")
if rows:
    q = rows[0].source_query
    has_left = 'LEFT OUTER JOIN F_FAMILLE' in q
    has_inner = 'INNER JOIN F_FAMILLE' in q
    print(f"\nLEFT OUTER JOIN F_FAMILLE: {has_left}")
    print(f"INNER JOIN F_FAMILLE: {has_inner}")
    print()
    for line in q.split('\n'):
        if 'F_FAMILLE' in line or 'F_COMPTET_1' in line:
            print(line.rstrip())

cursor.close()
conn.close()
