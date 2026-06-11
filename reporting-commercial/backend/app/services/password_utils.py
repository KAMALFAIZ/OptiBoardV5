"""
Utilitaires de hachage de mot de passe — migration progressive SHA256 -> bcrypt.

Objectif : remplacer le SHA256 nu (sans sel, vulnérable au brute-force GPU et aux
rainbow tables) par bcrypt, SANS invalider les comptes existants.

- hash_password()   : produit un hash bcrypt (fallback SHA256 si bcrypt indisponible).
- verify_password() : accepte bcrypt ET l'ancien SHA256 (comparaison constant-time
                      via hmac.compare_digest pour éviter les timing attacks).
- needs_rehash()    : True si le hash stocké doit être ré-haché (ancien SHA256 ou
                      coût bcrypt inférieur au coût cible).

Rétro-compatibilité : un compte créé en SHA256 (y compris par FIX_ADMIN_CLIENT.ps1)
continue de fonctionner et est ré-haché en bcrypt lors de sa prochaine connexion
réussie (voir auth_multitenant.login).

Note : on utilise la bibliothèque `bcrypt` directement (pas passlib) pour éviter
le warning cosmétique "error reading bcrypt version" de passlib 1.7.4 + bcrypt 4.x.
"""
import hashlib
import hmac
import logging
import re

logger = logging.getLogger("PasswordUtils")

_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_BCRYPT_PREFIXES = ("$2a$", "$2b$", "$2y$")
_BCRYPT_ROUNDS = 12
_BCRYPT_MAX_BYTES = 72  # bcrypt ignore les octets au-delà de 72

_bcrypt = None
try:
    import bcrypt as _bcrypt  # fourni par passlib[bcrypt] dans requirements.txt
except Exception as e:  # pragma: no cover - environnement embarqué sans bcrypt
    logger.warning(f"[PASSWORD] bcrypt indisponible — fallback SHA256 actif: {e}")

_bcrypt_ready = _bcrypt is not None


def is_bcrypt_hash(h) -> bool:
    return isinstance(h, str) and h.startswith(_BCRYPT_PREFIXES)


def is_sha256_hash(h) -> bool:
    return isinstance(h, str) and bool(_SHA256_RE.match(h or ""))


def _sha256(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _prep(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    """Hash un mot de passe en bcrypt (ou SHA256 en dernier recours)."""
    if _bcrypt_ready:
        try:
            return _bcrypt.hashpw(_prep(password), _bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode("ascii")
        except Exception as e:  # pragma: no cover
            logger.error(f"[PASSWORD] Échec bcrypt, fallback SHA256: {e}")
    return _sha256(password)


def verify_password(password: str, stored_hash) -> bool:
    """Vérifie un mot de passe contre un hash bcrypt OU SHA256 (constant-time)."""
    if not stored_hash or not isinstance(stored_hash, str):
        return False
    if is_bcrypt_hash(stored_hash):
        if not _bcrypt_ready:
            return False
        try:
            return _bcrypt.checkpw(_prep(password), stored_hash.encode("ascii"))
        except Exception:
            return False
    if is_sha256_hash(stored_hash):
        return hmac.compare_digest(_sha256(password), stored_hash.lower())
    # Format inconnu : comparaison constant-time qui échouera proprement
    return hmac.compare_digest(_sha256(password), stored_hash)


def needs_rehash(stored_hash) -> bool:
    """True si le hash doit être ré-haché (ancien SHA256 ou coût bcrypt trop faible)."""
    if is_bcrypt_hash(stored_hash):
        try:
            cost = int(stored_hash.split("$")[2])
            return cost < _BCRYPT_ROUNDS
        except Exception:
            return False
    # SHA256 ou tout format legacy -> à upgrader vers bcrypt
    return True
