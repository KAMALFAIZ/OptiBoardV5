"""Create APP_Users in OptiBoard_cltKA and add superadmin."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import warnings; warnings.filterwarnings('ignore')
from app.database_unified import execute_central, execute_client, client_cursor

# Get superadmin password hash from central
users = execute_central("SELECT password_hash FROM APP_Users WHERE username = 'superadmin'")
pwd_hash = users[0]['password_hash']
print(f"Got superadmin hash from central")

with client_cursor('KA') as c:
    c.execute("""
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
    print("APP_Users table created in OptiBoard_cltKA")

    c.execute("""
        IF NOT EXISTS (SELECT 1 FROM APP_Users WHERE username = 'superadmin')
        INSERT INTO APP_Users (username, password_hash, nom, prenom, email, role_global, actif)
        VALUES ('superadmin', ?, 'Super', 'Admin', 'admin@kasoft.ma', 'superadmin', 1)
    """, (pwd_hash,))
    print("superadmin user inserted")

# Verify
rows = execute_client("SELECT id, username, role_global FROM APP_Users", dwh_code='KA')
print(f"\nUsers in OptiBoard_cltKA: {len(rows)}")
for r in rows:
    print(f"  id={r['id']} username={r['username']} role={r['role_global']}")
