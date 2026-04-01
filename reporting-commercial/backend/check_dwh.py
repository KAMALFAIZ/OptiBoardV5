"""
Script pour verifier l'etat du DWH
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

    # Verifier la table 'Clients'
    print("=" * 60)
    print("TABLE 'Clients':")
    print("=" * 60)

    # Compter les lignes
    cursor.execute("SELECT COUNT(*) FROM [Clients]")
    count = cursor.fetchone()[0]
    print(f"  Nombre de lignes: {count}")

    # Lister les colonnes
    cursor.execute("""
        SELECT COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'Clients'
        ORDER BY ORDINAL_POSITION
    """)
    columns = cursor.fetchall()
    print(f"  Colonnes ({len(columns)}):")
    for col in columns[:15]:
        print(f"    - {col[0]}: {col[1]}")
    if len(columns) > 15:
        print(f"    ... et {len(columns) - 15} autres colonnes")

    # Verifier si societe existe
    has_societe = any(col[0].lower() == 'societe' for col in columns)
    print(f"\n  Colonne 'societe' presente: {has_societe}")

    if has_societe:
        cursor.execute("SELECT DISTINCT societe FROM [Clients]")
        societes = cursor.fetchall()
        print(f"  Valeurs de 'societe': {[s[0] for s in societes]}")

    # Afficher quelques lignes
    print("\n  Exemple de donnees (3 premieres lignes):")
    cursor.execute("SELECT TOP 3 * FROM [Clients]")
    rows = cursor.fetchall()
    col_names = [desc[0] for desc in cursor.description]
    for i, row in enumerate(rows):
        print(f"    Ligne {i+1}:")
        for j, val in enumerate(row[:5]):  # 5 premieres colonnes
            print(f"      {col_names[j]}: {val}")

    cursor.close()
    conn.close()

except Exception as e:
    print(f"ERREUR: {e}")
    import traceback
    traceback.print_exc()
