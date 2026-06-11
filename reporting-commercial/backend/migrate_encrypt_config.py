"""
Migration : chiffrement AES-256-GCM des source_query dans APP_ETL_Tables_Config
Base centrale OptiBoard_SaaS — lignes encore en clair.
"""
import pyodbc
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

CONN = (
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=kasoft.selfip.net;'
    'DATABASE=OptiBoard_SaaS;'
    'UID=sa;PWD=SQL@2019;'
    'TrustServerCertificate=yes;'
)

_KEY  = b"optiboard-query-encrypt-2026-ks!"
_PRE  = "$enc1$"

def enc(val):
    if not val or val.startswith(_PRE):
        return val
    import base64, os as _os
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    nonce = _os.urandom(12)
    ct = AESGCM(_KEY).encrypt(nonce, val.encode(), None)
    return f"{_PRE}{base64.b64encode(nonce + ct).decode()}"

conn = pyodbc.connect(CONN, timeout=15)
cur  = conn.cursor()

# Etat avant
cur.execute(
    "SELECT COUNT(*) FROM APP_ETL_Tables_Config "
    "WHERE source_query IS NOT NULL AND source_query != '' "
    "AND source_query NOT LIKE '$enc1$%'"
)
nb_clear = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM APP_ETL_Tables_Config")
total = cur.fetchone()[0]

print("=" * 60)
print("  MIGRATION : APP_ETL_Tables_Config - AES-256-GCM")
print("=" * 60)
print(f"\nTotal lignes  : {total}")
print(f"En clair      : {nb_clear}")
print(f"Deja chiffrees: {total - nb_clear}")

if nb_clear == 0:
    print("\nRien a faire — toutes les requetes sont deja chiffrees.")
    conn.close()
    sys.exit(0)

# Chiffrer
cur.execute(
    "SELECT id, code, source_query FROM APP_ETL_Tables_Config "
    "WHERE source_query IS NOT NULL AND source_query != '' "
    "AND source_query NOT LIKE '$enc1$%'"
)
rows = cur.fetchall()

print(f"\nChiffrement de {len(rows)} lignes...")
count = 0
for row in rows:
    rid, code, plain = row[0], row[1], row[2]
    encrypted = enc(plain)
    if encrypted and encrypted != plain:
        cur.execute(
            "UPDATE APP_ETL_Tables_Config SET source_query = ? WHERE id = ?",
            (encrypted, rid)
        )
        print(f"  OK  [{code}]  {plain[:60]}...")
        count += 1

conn.commit()

# Verification
cur.execute(
    "SELECT COUNT(*) FROM APP_ETL_Tables_Config "
    "WHERE source_query IS NOT NULL AND source_query != '' "
    "AND source_query NOT LIKE '$enc1$%'"
)
remaining_clear = cur.fetchone()[0]

print(f"\nChiffrees : {count} lignes")
print(f"Restant en clair : {remaining_clear}")
conn.close()
print("\nOK")
