"""
Script pour lister les tables/vues dans la base Sage
"""
import pyodbc

# Configuration Sage
SAGE_SERVER = "."
SAGE_DATABASE = "bijou"
SAGE_USER = "sa"
SAGE_PASSWORD = "SQL@2019"

conn_str = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={SAGE_SERVER};"
    f"DATABASE={SAGE_DATABASE};"
    f"UID={SAGE_USER};"
    f"PWD={SAGE_PASSWORD};"
    f"TrustServerCertificate=yes;"
)

print(f"Connexion a {SAGE_SERVER}/{SAGE_DATABASE}...")

try:
    conn = pyodbc.connect(conn_str, timeout=30)
    cursor = conn.cursor()
    print("Connexion OK!\n")

    # Chercher les tables/vues qui contiennent "client" dans le nom
    print("=" * 60)
    print("TABLES/VUES contenant 'client':")
    print("=" * 60)

    cursor.execute("""
        SELECT TABLE_NAME, TABLE_TYPE
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_NAME LIKE '%client%'
        ORDER BY TABLE_TYPE, TABLE_NAME
    """)
    tables = cursor.fetchall()
    for t in tables:
        print(f"  {t[1]}: {t[0]}")

    # Chercher les tables/vues qui contiennent "Liste"
    print("\n" + "=" * 60)
    print("TABLES/VUES contenant 'Liste':")
    print("=" * 60)

    cursor.execute("""
        SELECT TABLE_NAME, TABLE_TYPE
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_NAME LIKE '%Liste%'
        ORDER BY TABLE_TYPE, TABLE_NAME
    """)
    tables = cursor.fetchall()
    for t in tables:
        print(f"  {t[1]}: {t[0]}")

    # Lister les vues
    print("\n" + "=" * 60)
    print("TOUTES LES VUES:")
    print("=" * 60)

    cursor.execute("""
        SELECT TABLE_NAME
        FROM INFORMATION_SCHEMA.VIEWS
        ORDER BY TABLE_NAME
    """)
    views = cursor.fetchall()
    for v in views[:30]:
        print(f"  {v[0]}")
    if len(views) > 30:
        print(f"  ... et {len(views) - 30} autres vues")

    # Chercher F_COMPTET (table clients Sage)
    print("\n" + "=" * 60)
    print("TABLE F_COMPTET (Clients Sage):")
    print("=" * 60)

    cursor.execute("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_NAME = 'F_COMPTET'
    """)
    exists = cursor.fetchone()[0] > 0
    print(f"  Existe: {exists}")

    if exists:
        cursor.execute("SELECT COUNT(*) FROM F_COMPTET WHERE CT_Type = 0")
        count = cursor.fetchone()[0]
        print(f"  Nombre de clients (CT_Type=0): {count}")

    cursor.close()
    conn.close()

except Exception as e:
    print(f"ERREUR: {e}")
    import traceback
    traceback.print_exc()
