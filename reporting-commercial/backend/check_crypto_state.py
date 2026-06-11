"""Vérifie l'état du chiffrement dans APP_ETL_Tables_Published de chaque client."""
import pyodbc

CONN = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;UID=sa;PWD=SQL@2019;TrustServerCertificate=yes;'

for db in ['OptiBoard_cltAMM', 'OptiBoard_cltGO', 'OptiBoard_cltKA']:
    try:
        conn = pyodbc.connect(CONN + f'DATABASE={db};', timeout=15)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM APP_ETL_Tables_Published")
        total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM APP_ETL_Tables_Published WHERE source_query IS NOT NULL AND source_query != '' AND source_query NOT LIKE '$enc1$%'")
        clair = cur.fetchone()[0]
        crypto = total - clair
        print(f"{db}: {total} total | {crypto} crypto | {clair} clair")
        if clair > 0:
            cur.execute("SELECT TOP 3 code, LEFT(source_query, 50) FROM APP_ETL_Tables_Published WHERE source_query NOT LIKE '$enc1$%'")
            for r in cur.fetchall():
                print(f"  CLAIR: {r[0]} -> {r[1]}")
        if crypto > 0:
            cur.execute("SELECT TOP 2 code, LEFT(source_query, 50) FROM APP_ETL_Tables_Published WHERE source_query LIKE '$enc1$%'")
            for r in cur.fetchall():
                print(f"  CRYPTO: {r[0]} -> {r[1]}")
        conn.close()
    except Exception as e:
        print(f"{db}: ERREUR - {e}")
