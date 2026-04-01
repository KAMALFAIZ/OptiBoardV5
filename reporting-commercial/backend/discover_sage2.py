"""Decouvre les tables manquantes dans Sage."""
import pyodbc

conn_str = (
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=tcp:localhost,1433;DATABASE=ORQUE_SANITAIRE_2022;'
    'UID=sa;PWD=SQL@2019;TrustServerCertificate=yes'
)
conn = pyodbc.connect(conn_str)
cursor = conn.cursor()

# Chercher les tables liees aux concepts manquants
print("=== TABLES contenant ECHEANCE, MOUVEMENT, REGLEMENT ===")
cursor.execute("""
    SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_TYPE='BASE TABLE'
    AND (TABLE_NAME LIKE '%ECHEANCE%' OR TABLE_NAME LIKE '%MOUVEMENT%'
         OR TABLE_NAME LIKE '%REGLEMENT%' OR TABLE_NAME LIKE '%STOCK%')
    ORDER BY TABLE_NAME
""")
for row in cursor.fetchall():
    print(f"  {row[0]}")

print()

# Colonnes F_CREGLEMENT
print("=== F_CREGLEMENT toutes colonnes ===")
cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='F_CREGLEMENT' ORDER BY ORDINAL_POSITION")
for row in cursor.fetchall():
    print(f"  {row[0]}")

print()

# Colonnes F_ECRITUREC
print("=== F_ECRITUREC toutes colonnes ===")
cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='F_ECRITUREC' ORDER BY ORDINAL_POSITION")
for row in cursor.fetchall():
    print(f"  {row[0]}")

print()

# Colonnes F_DOCLIGNE
print("=== F_DOCLIGNE toutes colonnes ===")
cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='F_DOCLIGNE' ORDER BY ORDINAL_POSITION")
for row in cursor.fetchall():
    print(f"  {row[0]}")

conn.close()
