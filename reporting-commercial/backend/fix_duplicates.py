"""
Script pour ajouter la cle primaire a la table Clients du DWH
"""
import pyodbc

# Configuration DWH - DWH_ESSAIDI26
DWH_SERVER = "kasoft.selfip.net"
DWH_DATABASE = "DWH_ESSAIDI26"
DWH_USER = "sa"
DWH_PASSWORD = "SQL@2019"

conn_str = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={DWH_SERVER};"
    f"DATABASE={DWH_DATABASE};"
    f"UID={DWH_USER};"
    f"PWD={DWH_PASSWORD};"
    f"TrustServerCertificate=yes;"
)

print(f"Connexion a {DWH_SERVER}/{DWH_DATABASE}...")

try:
    conn = pyodbc.connect(conn_str, timeout=30)
    cursor = conn.cursor()
    print("Connexion OK!\n")

    # 1. Verifier l'etat actuel
    cursor.execute("SELECT COUNT(*) FROM [Clients]")
    count = cursor.fetchone()[0]
    print(f"Nombre de lignes: {count}")

    # 2. Modifier les colonnes pour les rendre NOT NULL
    print("\nModification des colonnes pour NOT NULL...")

    try:
        # D'abord mettre des valeurs par defaut si NULL
        cursor.execute("UPDATE [Clients] SET [societe] = '' WHERE [societe] IS NULL")
        cursor.execute("UPDATE [Clients] SET [Code client] = '' WHERE [Code client] IS NULL")
        conn.commit()
        print("Valeurs NULL remplacees")
    except Exception as e:
        print(f"Mise a jour NULL: {e}")

    try:
        cursor.execute("ALTER TABLE [Clients] ALTER COLUMN [societe] NVARCHAR(255) NOT NULL")
        conn.commit()
        print("Colonne [societe] modifiee en NOT NULL")
    except Exception as e:
        print(f"Erreur modification societe: {e}")

    try:
        cursor.execute("ALTER TABLE [Clients] ALTER COLUMN [Code client] NVARCHAR(255) NOT NULL")
        conn.commit()
        print("Colonne [Code client] modifiee en NOT NULL")
    except Exception as e:
        print(f"Erreur modification Code client: {e}")

    # 3. Ajouter la cle primaire
    print("\nAjout de la contrainte de cle primaire...")
    try:
        cursor.execute("""
            ALTER TABLE [Clients]
            ADD CONSTRAINT PK_Clients PRIMARY KEY ([societe], [Code client])
        """)
        conn.commit()
        print("Cle primaire PK_Clients ajoutee avec succes!")
    except Exception as e:
        if "already" in str(e).lower() or "existe" in str(e).lower() or "PK_Clients" in str(e):
            print("Cle primaire deja existante")
        else:
            print(f"Erreur ajout PK: {e}")

    # 4. Verifier la structure
    print("\nVerification de la structure:")
    cursor.execute("""
        SELECT
            c.COLUMN_NAME,
            c.IS_NULLABLE,
            CASE WHEN pk.COLUMN_NAME IS NOT NULL THEN 'PK' ELSE '' END as IS_PK
        FROM INFORMATION_SCHEMA.COLUMNS c
        LEFT JOIN (
            SELECT ku.COLUMN_NAME
            FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
            JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE ku
                ON tc.CONSTRAINT_NAME = ku.CONSTRAINT_NAME
            WHERE tc.TABLE_NAME = 'Clients' AND tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
        ) pk ON c.COLUMN_NAME = pk.COLUMN_NAME
        WHERE c.TABLE_NAME = 'Clients'
        AND c.COLUMN_NAME IN ('societe', 'Code client')
    """)
    for row in cursor.fetchall():
        print(f"  {row[0]}: Nullable={row[1]}, PK={row[2]}")

    cursor.close()
    conn.close()
    print("\nTermine!")

except Exception as e:
    print(f"ERREUR: {e}")
    import traceback
    traceback.print_exc()
