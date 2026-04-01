"""Script pour creer les tables utilisateur manquantes"""
import pyodbc

conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=kasoft.selfip.net;"
    "DATABASE=OptiBoard_SaaS;"
    "UID=sa;"
    "PWD=SQL@2019;"
    "TrustServerCertificate=yes"
)

try:
    conn = pyodbc.connect(conn_str, timeout=10)
    cursor = conn.cursor()

    # Verifier les tables existantes
    cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME LIKE 'APP_%' ORDER BY TABLE_NAME")
    tables = [row[0] for row in cursor.fetchall()]
    print("Tables existantes:", tables)

    # Creer APP_User_DWH si n'existe pas
    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_User_DWH' AND xtype='U')
        CREATE TABLE APP_User_DWH (
            id INT IDENTITY(1,1) PRIMARY KEY,
            user_id INT NOT NULL,
            dwh_code VARCHAR(50) NOT NULL,
            CONSTRAINT FK_User_DWH_User FOREIGN KEY (user_id) REFERENCES APP_Users(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    print("Table APP_User_DWH creee ou existe deja")

    # Creer APP_User_Societes si n'existe pas
    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_User_Societes' AND xtype='U')
        CREATE TABLE APP_User_Societes (
            id INT IDENTITY(1,1) PRIMARY KEY,
            user_id INT NOT NULL,
            dwh_code VARCHAR(50) NOT NULL,
            societe_code VARCHAR(50) NOT NULL,
            CONSTRAINT FK_User_Societes_User FOREIGN KEY (user_id) REFERENCES APP_Users(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    print("Table APP_User_Societes creee ou existe deja")

    # Verifier a nouveau
    cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME LIKE 'APP_%' ORDER BY TABLE_NAME")
    tables = [row[0] for row in cursor.fetchall()]
    print("Tables apres creation:", tables)

    cursor.close()
    conn.close()
    print("OK!")

except Exception as e:
    print(f"Erreur: {e}")
