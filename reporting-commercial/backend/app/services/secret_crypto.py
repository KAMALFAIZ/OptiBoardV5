"""
Chiffrement au repos des secrets stockés en base (mots de passe de sources).

Cible actuelle : `APP_ETL_Agents.sage_password` (base client) — le mot de passe du
serveur Sage, jusqu'ici stocké en clair et donc lisible par tout porteur d'un dump
SQL ou d'un accès lecture à la base client.

Format stocké : `$sec1$<base64(nonce[12] + ciphertext AES-256-GCM)>`
Les valeurs sans préfixe sont du plaintext legacy : elles sont retournées telles
quelles par `dec_secret`, ce qui rend la migration progressive (une valeur est
chiffrée à sa prochaine écriture, ou en masse via
`scripts/encrypt_etl_agent_secrets.py`).

Le chiffrement est **au repos uniquement** : les routes qui doivent fournir le mot
de passe à un appelant authentifié (agent ETL via `/api/agents/for-dwh`, résolveur
de credentials pour les requêtes Sage directes) déchiffrent à la lecture. L'objectif
est de retirer le secret des dumps/sauvegardes SQL, pas de le cacher au service qui
en a besoin pour se connecter à Sage.

Même conception que `query_crypto.py` (préfixe versionné, clé externalisable, repli
legacy) afin de garder un seul modèle mental pour les secrets de l'application.
"""
import os
import base64
import logging
from typing import Optional, Iterable

logger = logging.getLogger(__name__)

# Clé AES-256 (32 octets) de repli. Utilisée tant qu'aucune variable d'environnement
# n'est définie : elle protège d'une simple lecture de base/dump, pas d'un attaquant
# qui a aussi le code. Définir OPTIBOARD_SECRETS_AES_KEY en production.
_LEGACY_KEY = b"optiboard-secrets-encrypt-2026ks"  # 32 octets

_PREFIX = "$sec1$"


def _resolve_key() -> bytes:
    """OPTIBOARD_SECRETS_AES_KEY, sinon la clé des requêtes, sinon le repli legacy."""
    for var in ("OPTIBOARD_SECRETS_AES_KEY", "OPTIBOARD_QUERY_AES_KEY"):
        env_key = os.environ.get(var)
        if not env_key:
            continue
        kb = env_key.encode("utf-8")
        if len(kb) == 32:
            return kb
        logger.error(
            "[secret_crypto] %s doit faire exactement 32 octets (%d fournis) — "
            "repli sur la clé suivante.", var, len(kb),
        )
    return _LEGACY_KEY


_KEY = _resolve_key()


def is_encrypted(value: Optional[str]) -> bool:
    """True si la valeur porte déjà le préfixe de chiffrement."""
    return bool(value) and value.startswith(_PREFIX)


def enc_secret(value: Optional[str]) -> Optional[str]:
    """
    Chiffre un secret avant stockage. Valeur vide/None retournée telle quelle
    (une absence de mot de passe reste une absence, pas un blob).

    En cas d'échec de chiffrement on stocke le plaintext plutôt que de perdre la
    donnée : mieux vaut un secret en clair qu'un agent qui ne peut plus joindre Sage.
    L'échec est journalisé en warning pour être visible en exploitation.
    """
    if not value:
        return value
    if is_encrypted(value):
        return value  # déjà chiffré — idempotent
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        aesgcm = AESGCM(_KEY)
        nonce = os.urandom(12)
        ct = aesgcm.encrypt(nonce, value.encode("utf-8"), None)
        return f"{_PREFIX}{base64.b64encode(nonce + ct).decode()}"
    except Exception as e:
        logger.warning(f"[secret_crypto] Echec chiffrement, stockage plaintext: {e}")
        return value


def dec_secret(value: Optional[str]) -> Optional[str]:
    """Déchiffre un secret lu en base. Plaintext legacy retourné tel quel."""
    if not is_encrypted(value):
        return value
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        raw = base64.b64decode(value[len(_PREFIX):])
        nonce, ct = raw[:12], raw[12:]
        return AESGCM(_KEY).decrypt(nonce, ct, None).decode("utf-8")
    except Exception as e:
        # Mauvaise clé (rotation incomplète) ou donnée corrompue : ne jamais renvoyer
        # le blob comme s'il s'agissait du mot de passe — la connexion Sage échouerait
        # avec un message trompeur.
        logger.error(f"[secret_crypto] Echec dechiffrement d'un secret: {e}")
        return ""


def dec_rows(rows, fields: Iterable[str] = ("sage_password",)):
    """Déchiffre en place les champs secrets de chaque dict d'un résultat SQL."""
    if not rows:
        return rows
    for row in rows:
        if not isinstance(row, dict):
            continue
        for f in fields:
            if f in row:
                row[f] = dec_secret(row[f])
    return rows
