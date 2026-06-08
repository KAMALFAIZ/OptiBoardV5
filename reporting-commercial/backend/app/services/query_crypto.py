"""
Chiffrement AES-256-GCM pour APP_ETL_Agent_Tables.source_query.
Format stocke : $enc1$<base64(nonce[12] + ciphertext)>
Les valeurs sans prefix sont du plaintext legacy — elles sont lisibles telles quelles.
"""
import os
import base64
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_KEY = b"optiboard-query-encrypt-2026-ks!"  # 32 octets
_PREFIX = "$enc1$"


def enc_query(value: Optional[str]) -> Optional[str]:
    """Chiffre une source_query avant stockage en base. Retourne None si vide."""
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
        logger.warning(f"[query_crypto] Echec chiffrement, stockage plaintext: {e}")
        return value


def dec_query(value: Optional[str]) -> Optional[str]:
    """Dechiffre une source_query lue depuis la base. Plaintext legacy retourne tel quel."""
    if not value or not value.startswith(_PREFIX):
        return value
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        raw = base64.b64decode(value[len(_PREFIX):])
        nonce, ct = raw[:12], raw[12:]
        aesgcm = AESGCM(_KEY)
        return aesgcm.decrypt(nonce, ct, None).decode("utf-8")
    except Exception as e:
        logger.warning(f"[query_crypto] Echec dechiffrement: {e}")
        return value


def dec_rows(rows: list) -> list:
    """Dechiffre source_query dans chaque dict d'une liste de lignes SQL."""
    if not rows:
        return rows
    for row in rows:
        if isinstance(row, dict) and "source_query" in row:
            row["source_query"] = dec_query(row["source_query"])
    return rows


def migrate_encrypt_existing(cursor) -> int:
    """
    Chiffre les lignes APP_ETL_Agent_Tables.source_query qui sont encore en plaintext.
    Appelee une fois au demarrage via _ensure_agent_table_columns().
    Retourne le nombre de lignes mises a jour.
    """
    try:
        cursor.execute(
            "SELECT id, source_query FROM APP_ETL_Agent_Tables "
            "WHERE source_query IS NOT NULL AND source_query != '' "
            "AND source_query NOT LIKE '$enc1$%'"
        )
        rows = cursor.fetchall()
        count = 0
        for row in rows:
            row_id = row[0]
            plain = row[1]
            encrypted = enc_query(plain)
            if encrypted and encrypted != plain:
                cursor.execute(
                    "UPDATE APP_ETL_Agent_Tables SET source_query = ? WHERE id = ?",
                    (encrypted, row_id)
                )
                count += 1
        if count:
            cursor.commit()
            logger.info(f"[query_crypto] {count} source_query migrees vers AES-GCM")
        return count
    except Exception as e:
        logger.warning(f"[query_crypto] Migration chiffrement partielle: {e}")
        return 0


def migrate_encrypt_config(central_cursor) -> int:
    """
    Chiffre les lignes APP_ETL_Tables_Config.source_query qui sont encore en plaintext.
    A executer une fois apres le deploiement (base centrale OptiBoard_SaaS).
    Retourne le nombre de lignes mises a jour.
    """
    try:
        central_cursor.execute(
            "SELECT id, source_query FROM APP_ETL_Tables_Config "
            "WHERE source_query IS NOT NULL AND source_query != '' "
            "AND source_query NOT LIKE '$enc1$%'"
        )
        rows = central_cursor.fetchall()
        count = 0
        for row in rows:
            row_id = row[0]
            plain = row[1]
            encrypted = enc_query(plain)
            if encrypted and encrypted != plain:
                central_cursor.execute(
                    "UPDATE APP_ETL_Tables_Config SET source_query = ? WHERE id = ?",
                    (encrypted, row_id)
                )
                count += 1
        if count:
            central_cursor.commit()
            logger.info(f"[query_crypto] {count} source_query Config migrees vers AES-GCM")
        return count
    except Exception as e:
        logger.warning(f"[query_crypto] Migration chiffrement Config partielle: {e}")
        return 0


def migrate_encrypt_published(client_cursor) -> int:
    """
    Chiffre les lignes APP_ETL_Tables_Published.source_query qui sont encore en plaintext.
    Retourne le nombre de lignes mises a jour.
    """
    try:
        client_cursor.execute(
            "SELECT id, source_query FROM APP_ETL_Tables_Published "
            "WHERE source_query IS NOT NULL AND source_query != '' "
            "AND source_query NOT LIKE '$enc1$%'"
        )
        rows = client_cursor.fetchall()
        count = 0
        for row in rows:
            row_id = row[0]
            plain = row[1]
            encrypted = enc_query(plain)
            if encrypted and encrypted != plain:
                client_cursor.execute(
                    "UPDATE APP_ETL_Tables_Published SET source_query = ? WHERE id = ?",
                    (encrypted, row_id)
                )
                count += 1
        if count:
            client_cursor.commit()
            logger.info(f"[query_crypto] {count} source_query Published migrees vers AES-GCM")
        return count
    except Exception as e:
        logger.warning(f"[query_crypto] Migration chiffrement Published partielle: {e}")
        return 0
