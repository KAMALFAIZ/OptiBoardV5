"""Create OptiBoard_KA database on remote server and add superadmin user."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import warnings; warnings.filterwarnings('ignore')
import pyodbc

from app.database_unified import execute_central

# Get superadmin password hash
users = execute_central("SELECT password_hash FROM APP_Users WHERE username = 'superadmin'")
pwd_hash = users[0]['password_hash']
print(f"superadmin hash: {pwd_hash[:20]}...")

SERVER = 'kasoft.selfip.net'
UID = 'SA'
PWD = 'SQL@2019'

conn_str = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={SERVER};DATABASE=master;UID={UID};PWD={PWD};"
    f"TrustServerCertificate=yes"
)

try:
    conn = pyodbc.connect(conn_str, timeout=10, autocommit=True)
    c = conn.cursor()

    # Create DB if not exists
    c.execute("SELECT DB_ID('OptiBoard_KA')")
    if c.fetchone()[0] is None:
        c.execute("CREATE DATABASE [OptiBoard_KA]")
        print("Database OptiBoard_KA created")
    else:
        print("Database OptiBoard_KA already exists")
    conn.close()

    # Connect to OptiBoard_KA
    conn2_str = conn_str.replace("DATABASE=master", "DATABASE=OptiBoard_KA")
    conn2 = pyodbc.connect(conn2_str, timeout=10, autocommit=True)
    c2 = conn2.cursor()

    # Create APP_Users table
    c2.execute("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'APP_Users')
        CREATE TABLE APP_Users (
            id INT IDENTITY(1,1) PRIMARY KEY,
            username NVARCHAR(100) NOT NULL,
            password_hash NVARCHAR(255) NOT NULL,
            nom NVARCHAR(100) NULL,
            prenom NVARCHAR(100) NULL,
            email NVARCHAR(255) NULL,
            telephone NVARCHAR(50) NULL,
            fonction NVARCHAR(100) NULL,
            role_global NVARCHAR(50) DEFAULT 'user',
            actif BIT DEFAULT 1,
            date_creation DATETIME DEFAULT GETDATE(),
            derniere_connexion DATETIME NULL,
            avatar_url NVARCHAR(500) NULL,
            totp_secret NVARCHAR(255) NULL,
            totp_enabled BIT DEFAULT 0,
            role_dwh NVARCHAR(50) NULL,
            must_change_password BIT DEFAULT 0,
            onboarding_done BIT DEFAULT 0,
            mobile_access BIT DEFAULT 1
        )
    """)
    print("APP_Users table ensured")

    # Insert superadmin if not exists
    c2.execute("SELECT id FROM APP_Users WHERE username = 'superadmin'")
    if c2.fetchone() is None:
        c2.execute("""
            INSERT INTO APP_Users (username, password_hash, nom, prenom, email, role_global, actif)
            VALUES ('superadmin', ?, 'Super', 'Admin', 'admin@kasoft.ma', 'superadmin', 1)
        """, (pwd_hash,))
        print("superadmin user inserted")
    else:
        print("superadmin already exists")

    conn2.close()
    print("\nDone! OptiBoard_KA is ready for login.")

except Exception as e:
    print(f"Error: {e}")
