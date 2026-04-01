"""Decouvre les vraies tables et colonnes de la base Sage ORQUE_SANITAIRE_2022."""
import pyodbc

conn_str = (
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=tcp:localhost,1433;DATABASE=ORQUE_SANITAIRE_2022;'
    'UID=sa;PWD=SQL@2019;TrustServerCertificate=yes'
)
conn = pyodbc.connect(conn_str)
cursor = conn.cursor()

# Tables qui nous interessent
targets = [
    'F_ECHEANCE', 'F_MOUVEMENST', 'F_MOUVEMENT',
    'F_CREGLEMENT', 'F_REGLEMENT', 'F_REGLEMENTL',
    'F_DOCREGL', 'F_DOCLIGNE', 'F_DOCENTETE',
    'F_COMPTET', 'F_ECRITUREC'
]

print("=== TABLES EXISTANTES ===")
existing = []
for t in targets:
    cursor.execute(f"SELECT TOP 1 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = '{t}'")
    row = cursor.fetchone()
    status = "OK" if row else "ABSENT"
    print(f"  {t}: {status}")
    if row:
        existing.append(t)

print()

# Colonnes pour les tables qui nous posent probleme
inspect = {
    'F_DOCENTETE': ['CT_Num', 'CT_Intitule', 'DO_Remise', 'DO_Period', 'DO_Expedit', 'DO_Colisage'],
    'F_DOCLIGNE':  ['DL_QteLS', 'DL_QteReel', 'DO_Date', 'DO_Ref', 'DE_No', 'cbCreation', 'cbModification', 'DL_Remise01REM_Valeur'],
    'F_ECRITUREC': ['EC_Cours', 'EC_PieceType', 'EC_RefPiece', 'EC_Devise'],
    'F_DOCREGL':   ['DL_No', 'cbIndice', 'DR_Piece', 'DR_Qte', 'DR_No'],
}

for table, cols in inspect.items():
    if table not in existing:
        continue
    print(f"=== {table} colonnes ===")
    for col in cols:
        cursor.execute(f"SELECT TOP 1 1 FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='{table}' AND COLUMN_NAME='{col}'")
        row = cursor.fetchone()
        print(f"  {col}: {'OK' if row else 'ABSENT'}")
    print()

# Lister TOUTES les colonnes de F_DOCENTETE
print("=== F_DOCENTETE toutes colonnes ===")
cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='F_DOCENTETE' ORDER BY ORDINAL_POSITION")
for row in cursor.fetchall():
    print(f"  {row[0]}")

print()
print("=== F_DOCREGL toutes colonnes ===")
cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='F_DOCREGL' ORDER BY ORDINAL_POSITION")
for row in cursor.fetchall():
    print(f"  {row[0]}")

conn.close()
