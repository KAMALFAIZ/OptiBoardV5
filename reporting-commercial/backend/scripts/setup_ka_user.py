"""Add superadmin access to KA DWH and ensure client DB user exists."""
import sys, os, hashlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import warnings
warnings.filterwarnings('ignore')

from app.database_unified import execute_central, central_cursor, execute_client, client_cursor

DWH = 'KA'
USERNAME = 'superadmin'

def main():
    # 1. Get superadmin from central
    users = execute_central(
        "SELECT id, username, password_hash FROM APP_Users WHERE username = ?",
        (USERNAME,)
    )
    if not users:
        print(f"User {USERNAME} not found in central APP_Users!")
        return
    uid = users[0]['id']
    pwd_hash = users[0]['password_hash']
    print(f"Found {USERNAME} id={uid}")

    # 2. Check if UserDWH mapping exists
    existing = execute_central(
        "SELECT id FROM APP_UserDWH WHERE user_id = ? AND dwh_code = ?",
        (uid, DWH)
    )
    if existing:
        print(f"UserDWH mapping already exists (id={existing[0]['id']})")
    else:
        with central_cursor() as c:
            c.execute(
                "INSERT INTO APP_UserDWH (user_id, dwh_code, role_dwh, is_default) VALUES (?, ?, 'admin_client', 0)",
                (uid, DWH)
            )
        print(f"UserDWH mapping created: {USERNAME} -> {DWH}")

    # 3. Ensure APP_Users exists in client DB with this user
    try:
        client_users = execute_client(
            "SELECT username FROM APP_Users WHERE username = ?",
            (USERNAME,), dwh_code=DWH
        )
        if client_users:
            print(f"User {USERNAME} already exists in client DB OptiBoard_{DWH}")
        else:
            with client_cursor(DWH) as c:
                c.execute("""
                    INSERT INTO APP_Users (username, password_hash, nom, prenom, email, role_global, actif)
                    VALUES (?, ?, 'Super', 'Admin', 'admin@kasoft.ma', 'superadmin', 1)
                """, (USERNAME, pwd_hash))
            print(f"User {USERNAME} created in client DB OptiBoard_{DWH}")
    except Exception as e:
        err = str(e)
        if 'APP_Users' in err and ('Invalid object' in err or 'objet' in err.lower()):
            print(f"APP_Users table missing in OptiBoard_{DWH}, creating...")
            with client_cursor(DWH) as c:
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
                c.execute("""
                    INSERT INTO APP_Users (username, password_hash, nom, prenom, email, role_global, actif)
                    VALUES (?, ?, 'Super', 'Admin', 'admin@kasoft.ma', 'superadmin', 1)
                """, (USERNAME, pwd_hash))
            print(f"APP_Users table created and {USERNAME} inserted in OptiBoard_{DWH}")
        else:
            print(f"Error: {e}")

    print("\nDone! You can now login with superadmin on DWH KA.")

if __name__ == '__main__':
    main()
