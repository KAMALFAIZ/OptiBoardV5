"""
Script d'initialisation : crée les tables de base et l'utilisateur superadmin
dans OptiBoard_SaaS (base centrale).
"""
import hashlib
import pyodbc

CONN_STRING = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=kasoft.selfip.net;"
    "DATABASE=OptiBoard_SaaS;"
    "UID=sa;"
    "PWD=SQL@2019;"
    "TrustServerCertificate=yes"
)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def run():
    print("Connexion a OptiBoard_SaaS...")
    conn = pyodbc.connect(CONN_STRING)
    cursor = conn.cursor()

    # ── 1. Creer APP_Users si absent ─────────────────────────────────────────
    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Users' AND xtype='U')
        CREATE TABLE APP_Users (
            id                INT IDENTITY(1,1) PRIMARY KEY,
            username          VARCHAR(50) UNIQUE NOT NULL,
            password_hash     VARCHAR(64) NOT NULL,
            nom               NVARCHAR(100),
            prenom            NVARCHAR(100),
            email             VARCHAR(200),
            role_global       VARCHAR(20) DEFAULT 'user',
            actif             BIT DEFAULT 1,
            date_creation     DATETIME DEFAULT GETDATE(),
            derniere_connexion DATETIME
        )
    """)
    conn.commit()
    print("Table APP_Users : OK")

    # ── 2. Creer APP_UserSocietes si absent ───────────────────────────────────
    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_UserSocietes' AND xtype='U')
        CREATE TABLE APP_UserSocietes (
            id           INT IDENTITY(1,1) PRIMARY KEY,
            user_id      INT NOT NULL,
            societe_code VARCHAR(50) NOT NULL
        )
    """)
    conn.commit()
    print("Table APP_UserSocietes : OK")

    # ── 3. Creer APP_UserPages si absent ─────────────────────────────────────
    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_UserPages' AND xtype='U')
        CREATE TABLE APP_UserPages (
            id        INT IDENTITY(1,1) PRIMARY KEY,
            user_id   INT NOT NULL,
            page_code VARCHAR(50) NOT NULL
        )
    """)
    conn.commit()
    print("Table APP_UserPages : OK")

    # ── 4. Creer APP_Societes si absent ──────────────────────────────────────
    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Societes' AND xtype='U')
        CREATE TABLE APP_Societes (
            id           INT IDENTITY(1,1) PRIMARY KEY,
            code         VARCHAR(50) UNIQUE NOT NULL,
            nom          NVARCHAR(200) NOT NULL,
            serveur      VARCHAR(100),
            base_donnees VARCHAR(100),
            username     VARCHAR(50),
            password     VARCHAR(100),
            description  NVARCHAR(500),
            actif        BIT DEFAULT 1,
            date_creation DATETIME DEFAULT GETDATE()
        )
    """)
    conn.commit()
    print("Table APP_Societes : OK")

    # ── 5. Verifier / insérer l'admin ─────────────────────────────────────────
    cursor.execute("SELECT id FROM APP_Users WHERE username = ?", ("admin",))
    existing = cursor.fetchone()
    if existing:
        # Mettre a jour le mot de passe et le role au cas ou
        cursor.execute(
            "UPDATE APP_Users SET password_hash=?, role_global=?, actif=1 WHERE username=?",
            (hash_password("admin123"), "superadmin", "admin")
        )
        conn.commit()
        print("Utilisateur 'admin' mis a jour (password=admin123, role=superadmin)")
    else:
        cursor.execute(
            """INSERT INTO APP_Users (username, password_hash, nom, prenom, email, role_global, actif)
               VALUES (?, ?, ?, ?, ?, ?, 1)""",
            ("admin", hash_password("admin123"), "Administrateur", "Central",
             "admin@kasoft.ma", "superadmin")
        )
        conn.commit()
        print("Utilisateur 'admin' cree (password=admin123, role=superadmin)")

    # ── 6. Recuperer l'id de l'admin ──────────────────────────────────────────
    cursor.execute("SELECT id FROM APP_Users WHERE username = ?", ("admin",))
    row = cursor.fetchone()
    admin_id = row[0] if row else None

    # ── 7. Ajouter toutes les pages autorisees ────────────────────────────────
    if admin_id:
        all_pages = [
            "dashboard", "ventes", "stocks", "recouvrement",
            "admin", "etl_admin", "settings", "users",
            "dwh_management", "client_users", "client_dwh",
            "report_scheduler", "database", "datasources",
        ]
        cursor.execute("DELETE FROM APP_UserPages WHERE user_id = ?", (admin_id,))
        for page in all_pages:
            cursor.execute(
                "INSERT INTO APP_UserPages (user_id, page_code) VALUES (?, ?)",
                (admin_id, page)
            )
        conn.commit()
        print(f"Pages autorisees ajoutees pour admin (id={admin_id}): {len(all_pages)} pages")

    cursor.close()
    conn.close()
    print("\nInitialisation terminee avec succes!")
    print("  Login : admin")
    print("  Mot de passe : admin123")


if __name__ == "__main__":
    run()
