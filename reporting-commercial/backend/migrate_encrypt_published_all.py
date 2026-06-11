"""
Migration one-shot : chiffre toutes les source_query en clair
dans APP_ETL_Tables_Published de chaque base client.

Usage :
    cd reporting-commercial\backend
    python migrate_encrypt_published_all.py
"""
import pyodbc
import os
import sys
import base64
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# ── Config connexion depuis .env ───────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

DB_SERVER   = os.getenv("DB_SERVER", "")
DB_NAME     = os.getenv("DB_NAME", "OptiBoard_SaaS")
DB_USER     = os.getenv("DB_USER", "")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_DRIVER   = os.getenv("DB_DRIVER", "{ODBC Driver 17 for SQL Server}")

CENTRAL_CONN = (
    f"DRIVER={DB_DRIVER};SERVER={DB_SERVER};DATABASE={DB_NAME};"
    f"UID={DB_USER};PWD={DB_PASSWORD};TrustServerCertificate=yes;"
)

# ── Crypto AES-256-GCM (copie de query_crypto.py) ─────────────────────────
_KEY = b"optiboard-query-encrypt-2026-ks!"
_PREFIX = "$enc1$"

def enc_query(value):
    if not value:
        return value
    if value.startswith(_PREFIX):
        return value  # deja chiffre
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        aesgcm = AESGCM(_KEY)
        nonce = os.urandom(12)
        ct = aesgcm.encrypt(nonce, value.encode("utf-8"), None)
        encoded = base64.b64encode(nonce + ct).decode()
        return f"{_PREFIX}{encoded}"
    except Exception as e:
        logger.error(f"ERREUR chiffrement : {e}")
        return value


def main():
    # 1. Lister les clients actifs
    logger.info(f"Connexion centrale : {DB_SERVER} / {DB_NAME}")
    conn_central = pyodbc.connect(CENTRAL_CONN, timeout=15)
    cur = conn_central.cursor()
    cur.execute("""
        SELECT d.code, d.nom, c.db_name, c.db_server, c.db_user, c.db_password
        FROM APP_DWH d
        JOIN APP_ClientDB c ON d.code = c.dwh_code
        WHERE d.actif = 1 AND c.actif = 1
        ORDER BY d.nom
    """)
    clients = []
    for row in cur.fetchall():
        clients.append({
            "code": row[0], "nom": row[1], "db_name": row[2],
            "db_server": row[3], "db_user": row[4], "db_password": row[5],
        })
    conn_central.close()

    if not clients:
        logger.info("Aucun client actif trouve.")
        return

    logger.info(f"\n{'='*60}")
    logger.info(f"  {len(clients)} client(s) actif(s) a migrer")
    logger.info(f"{'='*60}\n")

    total_migrated = 0

    for client in clients:
        code = client["code"]
        db_name = client["db_name"]
        server = client["db_server"] or DB_SERVER
        user = client["db_user"] or DB_USER
        password = client["db_password"] or DB_PASSWORD

        conn_str = (
            f"DRIVER={DB_DRIVER};SERVER={server};DATABASE={db_name};"
            f"UID={user};PWD={password};TrustServerCertificate=yes;"
        )

        try:
            conn = pyodbc.connect(conn_str, timeout=15)
            cursor = conn.cursor()

            # Verifier si la table existe
            cursor.execute(
                "SELECT COUNT(*) FROM sysobjects WHERE name='APP_ETL_Tables_Published' AND xtype='U'"
            )
            if cursor.fetchone()[0] == 0:
                logger.info(f"  [{code}] {db_name} : table APP_ETL_Tables_Published absente — skip")
                conn.close()
                continue

            # Trouver les lignes en clair
            cursor.execute(
                "SELECT id, code, source_query FROM APP_ETL_Tables_Published "
                "WHERE source_query IS NOT NULL AND source_query != '' "
                "AND source_query NOT LIKE '$enc1$%'"
            )
            rows = cursor.fetchall()

            if not rows:
                logger.info(f"  [{code}] {db_name} : toutes les lignes sont deja chiffrees ({len(rows)} en clair)")
                # Compter total
                cursor.execute("SELECT COUNT(*) FROM APP_ETL_Tables_Published")
                total = cursor.fetchone()[0]
                logger.info(f"           {total} lignes total, 0 en clair")
                conn.close()
                continue

            count = 0
            for row in rows:
                row_id = row[0]
                row_code = row[1]
                plain = row[2]
                encrypted = enc_query(plain)
                if encrypted and encrypted != plain:
                    cursor.execute(
                        "UPDATE APP_ETL_Tables_Published SET source_query = ? WHERE id = ?",
                        (encrypted, row_id)
                    )
                    count += 1
                    logger.info(f"    -> {row_code} : chiffre OK")
                else:
                    logger.warning(f"    -> {row_code} : chiffrement echoue !")

            conn.commit()
            conn.close()
            total_migrated += count
            logger.info(f"  [{code}] {db_name} : {count}/{len(rows)} lignes chiffrees\n")

        except Exception as e:
            logger.error(f"  [{code}] {db_name} : ERREUR — {e}\n")

    logger.info(f"{'='*60}")
    logger.info(f"  TOTAL : {total_migrated} source_query migrees vers AES-256-GCM")
    logger.info(f"{'='*60}")


if __name__ == "__main__":
    main()
