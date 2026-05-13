import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import warnings; warnings.filterwarnings('ignore')
import pyodbc

# Test DWH connection (works for data queries)
try:
    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=kasoft.selfip.net;"
        "DATABASE=DWH_KA;"
        "UID=sa;PWD=SQL@2019;"
        "TrustServerCertificate=yes",
        timeout=10
    )
    c = conn.cursor()
    c.execute("SELECT DB_NAME() AS db")
    print(f"DWH_KA: OK - {c.fetchone()[0]}")
    conn.close()
except Exception as e:
    print(f"DWH_KA: FAIL - {e}")

# Test OptiBoard_KA client DB
try:
    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=kasoft.selfip.net;"
        "DATABASE=OptiBoard_KA;"
        "UID=SA;PWD=SQL@2019;"
        "TrustServerCertificate=yes",
        timeout=10
    )
    c = conn.cursor()
    c.execute("SELECT DB_NAME() AS db")
    print(f"OptiBoard_KA: OK - {c.fetchone()[0]}")
    conn.close()
except Exception as e:
    print(f"OptiBoard_KA: FAIL - {e}")

# List all databases on server
try:
    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=kasoft.selfip.net;"
        "DATABASE=master;"
        "UID=sa;PWD=SQL@2019;"
        "TrustServerCertificate=yes",
        timeout=10
    )
    c = conn.cursor()
    c.execute("SELECT name FROM sys.databases WHERE name LIKE '%KA%' OR name LIKE '%Opti%' ORDER BY name")
    print("\nDatabases matching KA/Opti:")
    for row in c.fetchall():
        print(f"  {row[0]}")
    conn.close()
except Exception as e:
    print(f"master: FAIL - {e}")
