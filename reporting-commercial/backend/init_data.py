"""Script pour initialiser les donnees: utilisateurs et societes"""
import pyodbc
import hashlib

# Configuration connexion
conn_string = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=kasoft.selfip.net;"
    "DATABASE=GROUPE_ALBOUGHAZE;"
    "UID=sa;"
    "PWD=SQL@2019;"
    "TrustServerCertificate=yes"
)

def hash_password(password: str) -> str:
    """Hash un mot de passe avec SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()


def init_tables(cursor):
    """Cree les tables si elles n'existent pas"""
    queries = [
        """
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Societes' AND xtype='U')
        CREATE TABLE APP_Societes (
            id INT IDENTITY(1,1) PRIMARY KEY,
            code VARCHAR(50) UNIQUE NOT NULL,
            nom NVARCHAR(200) NOT NULL,
            base_donnees VARCHAR(100) NOT NULL,
            serveur VARCHAR(100),
            actif BIT DEFAULT 1,
            date_creation DATETIME DEFAULT GETDATE()
        )
        """,
        """
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Users' AND xtype='U')
        CREATE TABLE APP_Users (
            id INT IDENTITY(1,1) PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(64) NOT NULL,
            nom NVARCHAR(100) NOT NULL,
            prenom NVARCHAR(100) NOT NULL,
            email VARCHAR(200),
            role VARCHAR(20) DEFAULT 'user',
            actif BIT DEFAULT 1,
            date_creation DATETIME DEFAULT GETDATE(),
            derniere_connexion DATETIME
        )
        """,
        """
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_UserSocietes' AND xtype='U')
        CREATE TABLE APP_UserSocietes (
            id INT IDENTITY(1,1) PRIMARY KEY,
            user_id INT NOT NULL,
            societe_code VARCHAR(50) NOT NULL,
            FOREIGN KEY (user_id) REFERENCES APP_Users(id) ON DELETE CASCADE
        )
        """,
        """
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_UserPages' AND xtype='U')
        CREATE TABLE APP_UserPages (
            id INT IDENTITY(1,1) PRIMARY KEY,
            user_id INT NOT NULL,
            page_code VARCHAR(50) NOT NULL,
            FOREIGN KEY (user_id) REFERENCES APP_Users(id) ON DELETE CASCADE
        )
        """
    ]

    for query in queries:
        cursor.execute(query)
    print("Tables initialisees avec succes")


def add_societe(cursor, code, nom, base_donnees, serveur=None):
    """Ajoute une societe si elle n'existe pas"""
    cursor.execute("SELECT code FROM APP_Societes WHERE code = ?", (code,))
    if cursor.fetchone():
        print(f"Societe {code} existe deja")
        return

    cursor.execute(
        """INSERT INTO APP_Societes (code, nom, base_donnees, serveur, actif)
           VALUES (?, ?, ?, ?, 1)""",
        (code, nom, base_donnees, serveur)
    )
    print(f"Societe '{nom}' ({code}) ajoutee avec succes")


def add_user(cursor, username, password, nom, prenom, email, role, societes, pages):
    """Ajoute un utilisateur si il n'existe pas"""
    cursor.execute("SELECT id FROM APP_Users WHERE username = ?", (username,))
    existing = cursor.fetchone()
    if existing:
        print(f"Utilisateur {username} existe deja")
        return existing[0]

    password_hash = hash_password(password)

    cursor.execute(
        """INSERT INTO APP_Users (username, password_hash, nom, prenom, email, role, actif)
           VALUES (?, ?, ?, ?, ?, ?, 1)""",
        (username, password_hash, nom, prenom, email, role)
    )

    cursor.execute("SELECT @@IDENTITY AS id")
    user_id = cursor.fetchone()[0]

    # Ajouter les societes
    for societe_code in societes:
        cursor.execute(
            "INSERT INTO APP_UserSocietes (user_id, societe_code) VALUES (?, ?)",
            (user_id, societe_code)
        )

    # Ajouter les pages
    for page_code in pages:
        cursor.execute(
            "INSERT INTO APP_UserPages (user_id, page_code) VALUES (?, ?)",
            (user_id, page_code)
        )

    print(f"Utilisateur '{nom} {prenom}' ({username}) cree avec role '{role}'")
    print(f"  - Societes: {', '.join(societes) if societes else 'Aucune'}")
    print(f"  - Pages: {', '.join(pages) if pages else 'Aucune'}")
    return user_id


def main():
    print("Connexion a la base de donnees...")
    conn = pyodbc.connect(conn_string)
    cursor = conn.cursor()

    try:
        # 1. Initialiser les tables
        init_tables(cursor)
        conn.commit()

        # 2. Ajouter la societe Groupe ESSAIDI
        add_societe(
            cursor,
            code="ESSAIDI",
            nom="Groupe ESSAIDI",
            base_donnees="GROUPE_ESSAIDI",
            serveur=None  # Utilise le serveur par defaut
        )
        conn.commit()

        # 3. Ajouter la societe Groupe ALBOUGHAZE (si pas encore)
        add_societe(
            cursor,
            code="ALBG",
            nom="Groupe ALBOUGHAZE",
            base_donnees="GROUPE_ALBOUGHAZE",
            serveur=None
        )
        conn.commit()

        # 4. Ajouter l'utilisateur Admin
        all_pages = ["dashboard", "ventes", "stocks", "recouvrement", "admin", "users"]
        all_societes = ["ALBG", "ESSAIDI"]

        add_user(
            cursor,
            username="admin",
            password="admin123",
            nom="Administrateur",
            prenom="Systeme",
            email="admin@groupe-alboughaze.ma",
            role="admin",
            societes=all_societes,
            pages=all_pages
        )
        conn.commit()

        # 5. Ajouter l'utilisateur standard
        user_pages = ["dashboard", "ventes", "stocks", "recouvrement"]

        add_user(
            cursor,
            username="user",
            password="user123",
            nom="Utilisateur",
            prenom="Standard",
            email="user@groupe-alboughaze.ma",
            role="user",
            societes=["ALBG"],
            pages=user_pages
        )
        conn.commit()

        print("\n" + "="*50)
        print("INITIALISATION TERMINEE AVEC SUCCES!")
        print("="*50)
        print("\nComptes crees:")
        print("  1. admin / admin123 (Administrateur - toutes les pages et societes)")
        print("  2. user / user123 (Utilisateur standard - pages limitees)")
        print("\nSocietes:")
        print("  1. ALBG - Groupe ALBOUGHAZE (GROUPE_ALBOUGHAZE)")
        print("  2. ESSAIDI - Groupe ESSAIDI (GROUPE_ESSAIDI)")

    except Exception as e:
        print(f"Erreur: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
