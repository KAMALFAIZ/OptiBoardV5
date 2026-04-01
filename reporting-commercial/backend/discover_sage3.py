"""Decouvre les colonnes des tables manquantes."""
import pyodbc

conn_str = (
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=tcp:localhost,1433;DATABASE=ORQUE_SANITAIRE_2022;'
    'UID=sa;PWD=SQL@2019;TrustServerCertificate=yes'
)
conn = pyodbc.connect(conn_str)
cursor = conn.cursor()

for table in ['F_ECHEANCES', 'F_ARTSTOCK']:
    print(f"=== {table} colonnes ===")
    cursor.execute(f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='{table}' ORDER BY ORDINAL_POSITION")
    rows = cursor.fetchall()
    for r in rows:
        print(f"  {r[0]}")
    print()

# Verifier RG_Type values in F_CREGLEMENT
print("=== F_CREGLEMENT RG_Type sample ===")
cursor.execute("SELECT TOP 5 RG_Type, CT_NumPayeur, RG_Date, RG_Montant FROM F_CREGLEMENT ORDER BY RG_Date DESC")
for r in cursor.fetchall():
    print(f"  RG_Type={r[0]}, CT={r[1]}, Date={r[2]}, Montant={r[3]}")

conn.close()
