"""Affiche toutes les requetes ETL depuis la base de donnees."""
import pyodbc
import os

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

cursor.execute(
    "SELECT table_name, primary_key, sync_type, source_query "
    "FROM ETL_Tables_Config ORDER BY ISNULL(sort_order, 999)"
)

for i, row in enumerate(cursor.fetchall(), 1):
    print("=" * 100)
    print(f"[{i}] TABLE: {row.table_name}  |  PK: {row.primary_key}  |  Sync: {row.sync_type}")
    print("=" * 100)
    print(row.source_query)
    print()

cursor.close()
conn.close()
