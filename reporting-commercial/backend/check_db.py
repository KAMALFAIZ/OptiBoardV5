"""Script pour verifier la base de donnees"""
import os
import sys

import pyodbc

# Secrets lus dans l'environnement — jamais en dur dans le code.
_PWD = os.environ.get("DB_PASSWORD")
if not _PWD:
    sys.exit("ERREUR: definissez DB_PASSWORD (et optionnellement DB_SERVER/DB_USER/DB_NAME).")

conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    f"SERVER={os.environ.get('DB_SERVER', 'kasoft.selfip.net')};"
    f"DATABASE={os.environ.get('DB_NAME', 'OptiBoard_SaaS')};"
    f"UID={os.environ.get('DB_USER', 'sa')};"
    f"PWD={_PWD};"
    "TrustServerCertificate=yes"
)

try:
    conn = pyodbc.connect(conn_str, timeout=10)
    cursor = conn.cursor()

    print("=== COLONNES DE APP_Users ===")
    cursor.execute("""
        SELECT COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'APP_Users'
        ORDER BY ORDINAL_POSITION
    """)
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")

    print("\n=== UTILISATEURS ===")
    cursor.execute("SELECT id, username, nom, prenom, role_global, actif FROM APP_Users")
    for row in cursor.fetchall():
        print(f"  ID={row[0]}, username={row[1]}, nom={row[2]}, role={row[4]}, actif={row[5]}")

    print("\n=== TEST LOGIN superadmin ===")
    import hashlib
    password_hash = hashlib.sha256("admin".encode()).hexdigest()
    print(f"  Hash attendu: {password_hash}")

    cursor.execute("SELECT id, username, password_hash FROM APP_Users WHERE username = 'superadmin'")
    row = cursor.fetchone()
    if row:
        print(f"  Hash en base: {row[2]}")
        print(f"  Match: {row[2] == password_hash}")
    else:
        print("  Utilisateur superadmin NON TROUVE!")

    cursor.close()
    conn.close()
    print("\nConnexion OK!")

except Exception as e:
    print(f"Erreur: {e}")
