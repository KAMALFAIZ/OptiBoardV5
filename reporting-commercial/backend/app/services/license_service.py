"""
Service de gestion des licences OptiBoard
- Generation d'empreinte machine unique (hardware fingerprint)
- Validation de licence par signature HMAC-SHA256
- Verification locale + verification serveur distant
- Mode grace si serveur injoignable
- Licences flottantes (acquire/heartbeat/release)
- Support trial, grace_period_days, is_trial
"""
import hashlib
import hmac
import json
import platform
import subprocess
import uuid
import time
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

LICENSE_SIGNING_SECRET = os.environ.get("LICENSE_SIGNING_SECRET", "")
LICENSE_CACHE_FILE = Path(__file__).parent.parent.parent / ".license_cache"


def get_machine_id() -> str:
    """
    Genere une empreinte unique de la machine basee sur le hardware.
    Combine : UUID de la carte mere + nom machine + OS
    """
    components = []

    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                ["wmic", "csproduct", "get", "UUID"],
                capture_output=True, text=True, timeout=10
            )
            lines = [l.strip() for l in result.stdout.strip().split('\n') if l.strip() and l.strip() != 'UUID']
            if lines:
                components.append(lines[0])
        elif platform.system() == "Linux":
            try:
                with open("/etc/machine-id", "r") as f:
                    components.append(f.read().strip())
            except FileNotFoundError:
                result = subprocess.run(
                    ["cat", "/sys/class/dmi/id/product_uuid"],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    components.append(result.stdout.strip())
    except Exception as e:
        logger.warning(f"[LICENSE] Impossible de lire UUID machine: {e}")

    if not components:
        components.append(str(uuid.getnode()))

    components.append(platform.node())

    raw = "|".join(components)
    machine_id = hashlib.sha256(raw.encode()).hexdigest()[:32]
    logger.info(f"[LICENSE] Machine ID: {machine_id}")
    return machine_id


def generate_license_key(
    organization: str,
    machine_id: str,
    plan: str,
    max_users: int,
    max_dwh: int,
    features: list,
    expiry_date: str,
    signing_secret: str
) -> str:
    """Genere une cle de licence signee. UTILISEE UNIQUEMENT SUR LE SERVEUR DE LICENCES."""
    import base64

    payload = {
        "org": organization,
        "mid": machine_id,
        "plan": plan,
        "max_u": max_users,
        "max_d": max_dwh,
        "feat": features,
        "exp": expiry_date,
        "iat": int(time.time())
    }

    payload_json = json.dumps(payload, separators=(',', ':'))
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode()

    signature = hmac.new(
        signing_secret.encode(),
        payload_b64.encode(),
        hashlib.sha256
    ).hexdigest()

    return f"{payload_b64}.{signature}"


def decode_license_payload(license_key: str) -> Optional[dict]:
    """Decode le payload d'une licence (sans verifier la signature)."""
    import base64

    try:
        parts = license_key.split(".")
        if len(parts) != 2:
            return None

        payload_b64 = parts[0]
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding

        payload_json = base64.urlsafe_b64decode(payload_b64).decode()
        return json.loads(payload_json)
    except Exception as e:
        logger.error(f"[LICENSE] Erreur decodage licence: {e}")
        return None


def verify_license_signature(license_key: str, signing_secret: str) -> bool:
    """Verifie la signature HMAC d'une licence. UTILISEE UNIQUEMENT SUR LE SERVEUR DE LICENCES."""
    try:
        parts = license_key.split(".")
        if len(parts) != 2:
            return False

        payload_b64, provided_signature = parts

        expected_signature = hmac.new(
            signing_secret.encode(),
            payload_b64.encode(),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(provided_signature, expected_signature)
    except Exception:
        return False


class LicenseStatus:
    """Resultat de la validation de licence"""
    def __init__(self):
        self.valid = False
        self.status = "unknown"   # valid, expired, invalid, revoked, suspended, grace, no_license
        self.organization = ""
        self.plan = ""
        self.is_trial = False
        self.max_users = 0
        self.max_dwh = 0
        self.features = []
        self.expiry_date = None
        self.days_remaining = 0
        self.machine_id = ""
        self.message = ""
        self.grace_mode = False
        self.grace_days_remaining = 0

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "status": self.status,
            "organization": self.organization,
            "plan": self.plan,
            "is_trial": self.is_trial,
            "max_users": self.max_users,
            "max_dwh": self.max_dwh,
            "features": self.features,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "days_remaining": self.days_remaining,
            "machine_id": self.machine_id,
            "message": self.message,
            "grace_mode": self.grace_mode,
            "grace_days_remaining": self.grace_days_remaining
        }


def _save_license_cache(data: dict):
    try:
        cache = {"timestamp": int(time.time()), "data": data}
        with open(LICENSE_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f)
    except Exception as e:
        logger.warning(f"[LICENSE] Erreur sauvegarde cache: {e}")


def _load_license_cache() -> Optional[dict]:
    try:
        if not LICENSE_CACHE_FILE.exists():
            return None
        with open(LICENSE_CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"[LICENSE] Erreur lecture cache: {e}")
        return None


def validate_license_remote(license_key: str, machine_id: str, server_url: str) -> Optional[dict]:
    """
    Valide la licence aupres du serveur de licences distant.
    Retourne le dict complet de la reponse serveur, ou None si erreur reseau.
    """
    import urllib.request
    import urllib.error

    try:
        url = f"{server_url.rstrip('/')}/license/validate"
        payload = json.dumps({
            "license_key": license_key,
            "machine_id": machine_id,
            "app_version": "1.0.0",
            "hostname": platform.node()
        }).encode()

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
            logger.info(f"[LICENSE] Validation serveur: {result.get('status', 'unknown')}")
            return result

    except urllib.error.URLError as e:
        logger.warning(f"[LICENSE] Serveur de licences injoignable: {e}")
        return None
    except Exception as e:
        logger.error(f"[LICENSE] Erreur validation distante: {e}")
        return None


def validate_license(license_key: str, server_url: str = "", grace_days: int = 7) -> LicenseStatus:
    """
    Valide une licence complete:
    1. Decode le payload pour extraire les infos locales
    2. Verifie aupres du serveur distant
    3. Si serveur injoignable, utilise le cache local (mode grace)
    4. Verifie la date d'expiration
    5. Verifie le machine_id
    """
    status = LicenseStatus()
    machine_id = get_machine_id()
    status.machine_id = machine_id

    if not license_key:
        status.status = "no_license"
        status.message = "Aucune cle de licence configuree"
        return status

    # 1. Decoder le payload
    payload = decode_license_payload(license_key)
    if not payload:
        status.status = "invalid"
        status.message = "Format de licence invalide"
        return status

    # Extraire les infos depuis le payload local
    status.organization = payload.get("org", "")
    status.plan = payload.get("plan", "")
    status.is_trial = bool(payload.get("trial", False)) or status.plan == "trial"
    status.max_users = payload.get("max_u", 0)
    status.max_dwh = payload.get("max_d", 0)
    status.features = payload.get("feat", [])

    try:
        status.expiry_date = datetime.strptime(payload.get("exp", ""), "%Y-%m-%d")
    except (ValueError, TypeError):
        status.status = "invalid"
        status.message = "Date d'expiration invalide dans la licence"
        return status

    # 2. Verifier la date d'expiration locale
    now = datetime.now()
    if status.expiry_date < now:
        status.status = "expired"
        status.days_remaining = 0
        status.message = f"Licence expiree le {status.expiry_date.strftime('%d/%m/%Y')}"
        return status

    status.days_remaining = (status.expiry_date - now).days

    # 3. Verifier le mode de deploiement
    deployment_mode = payload.get("mode", "on-premise")

    if deployment_mode != "saas":
        license_mid = payload.get("mid", "")
        if license_mid and license_mid != "*" and license_mid != machine_id:
            status.status = "invalid"
            status.message = "Cette licence n'est pas associee a cette machine"
            return status

    # 4. Verification serveur distant
    if server_url:
        remote_result = validate_license_remote(license_key, machine_id, server_url)

        if remote_result is not None:
            if remote_result.get("valid"):
                status.valid = True
                status.status = remote_result.get("status", "valid")
                status.message = remote_result.get("message", "Licence valide")
                # Synchroniser avec les infos du serveur (source de verite)
                status.is_trial = remote_result.get("is_trial", status.is_trial)
                status.features = remote_result.get("features", status.features) or status.features
                status.max_users = remote_result.get("max_users", status.max_users) or status.max_users
                status.days_remaining = remote_result.get("days_remaining", status.days_remaining)
                _save_license_cache({
                    "status": "valid",
                    "is_trial": status.is_trial,
                    "features": status.features,
                    "max_users": status.max_users,
                    "timestamp": int(time.time())
                })
            elif remote_result.get("status") == "revoked":
                status.status = "revoked"
                status.message = "Licence revoquee par l'administrateur"
                _save_license_cache({"status": "revoked", "timestamp": int(time.time())})
            elif remote_result.get("status") == "suspended":
                status.status = "suspended"
                status.message = "Licence suspendue"
                _save_license_cache({"status": "suspended", "timestamp": int(time.time())})
            elif remote_result.get("status") == "grace":
                # Grace period cote serveur
                status.valid = True
                status.status = "grace"
                status.grace_mode = True
                status.message = remote_result.get("message", "Grace period active")
                _save_license_cache({"status": "grace", "timestamp": int(time.time())})
            else:
                status.status = remote_result.get("status", "invalid")
                status.message = remote_result.get("message", "Licence invalide")
            return status
        else:
            # Serveur injoignable — mode grace local
            cache = _load_license_cache()
            if cache:
                cache_age_days = (int(time.time()) - cache.get("timestamp", 0)) / 86400
                cached_status = cache.get("data", {}).get("status", "")

                if cached_status == "revoked":
                    status.status = "revoked"
                    status.message = "Licence revoquee (cache)"
                    return status

                if cache_age_days <= grace_days:
                    status.valid = True
                    status.status = "valid"
                    status.grace_mode = True
                    status.grace_days_remaining = int(grace_days - cache_age_days)
                    # Restaurer depuis le cache
                    cached_data = cache.get("data", {})
                    status.is_trial = cached_data.get("is_trial", status.is_trial)
                    status.features = cached_data.get("features", status.features) or status.features
                    status.max_users = cached_data.get("max_users", status.max_users) or status.max_users
                    status.message = f"Mode grace - serveur injoignable ({status.grace_days_remaining}j restants)"
                    logger.warning(f"[LICENSE] Mode grace: {status.grace_days_remaining} jours restants")
                    return status
                else:
                    status.status = "grace_expired"
                    status.message = "Periode de grace expiree - serveur de licences injoignable"
                    return status
            else:
                status.status = "server_unreachable"
                status.message = "Serveur de licences injoignable et pas de cache local"
                return status

    # Mode offline — validation locale uniquement
    status.valid = True
    status.status = "valid"
    status.message = "Licence valide (mode offline)"
    return status


def check_feature_access(license_status: LicenseStatus, feature: str) -> bool:
    """Verifie si une fonctionnalite est incluse dans la licence"""
    if not license_status.valid:
        return False
    if "all" in license_status.features:
        return True
    return feature in license_status.features


def check_user_limit(license_status: LicenseStatus, current_users: int) -> bool:
    if not license_status.valid:
        return False
    if license_status.max_users == 0:
        return True
    return current_users <= license_status.max_users


def check_dwh_limit(license_status: LicenseStatus, current_dwh: int) -> bool:
    if not license_status.valid:
        return False
    if license_status.max_dwh == 0:
        return True
    return current_dwh <= license_status.max_dwh


# ============================================================
# Licences flottantes
# ============================================================
def acquire_floating_slot(license_key: str, server_url: str) -> dict:
    """Acquiert un slot de session flottante aupres du serveur"""
    import urllib.request
    import urllib.error

    machine_id = get_machine_id()
    try:
        url = f"{server_url.rstrip('/')}/license/floating/acquire"
        payload = json.dumps({
            "license_key": license_key,
            "machine_id": machine_id,
            "hostname": platform.node(),
            "app_version": "1.0.0"
        }).encode()

        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        logger.warning(f"[LICENSE] Erreur acquire floating slot: {e}")
        return {"valid": False, "status": "server_unreachable", "message": str(e)}


def floating_heartbeat(license_key: str, server_url: str) -> bool:
    """Envoie un heartbeat pour maintenir la session flottante active"""
    import urllib.request

    machine_id = get_machine_id()
    try:
        url = f"{server_url.rstrip('/')}/license/floating/heartbeat"
        payload = json.dumps({
            "license_key": license_key,
            "machine_id": machine_id,
            "hostname": platform.node()
        }).encode()

        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read().decode())
            return result.get("success", False)
    except Exception as e:
        logger.warning(f"[LICENSE] Erreur floating heartbeat: {e}")
        return False


def release_floating_slot(license_key: str, server_url: str) -> bool:
    """Libere le slot flottant lors de la deconnexion"""
    import urllib.request

    machine_id = get_machine_id()
    try:
        url = f"{server_url.rstrip('/')}/license/floating/release"
        payload = json.dumps({
            "license_key": license_key,
            "machine_id": machine_id
        }).encode()

        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read().decode())
            return result.get("success", False)
    except Exception as e:
        logger.warning(f"[LICENSE] Erreur release floating slot: {e}")
        return False


# ============================================================
# Cache global du statut de licence
# ============================================================
_license_cache = None
_license_cache_time = 0
LICENSE_CACHE_TTL = 3600  # Re-valider toutes les heures


def get_cached_license_status() -> Optional[LicenseStatus]:
    global _license_cache, _license_cache_time
    if _license_cache and (time.time() - _license_cache_time) < LICENSE_CACHE_TTL:
        return _license_cache
    return None


def set_cached_license_status(status: LicenseStatus):
    global _license_cache, _license_cache_time
    _license_cache = status
    _license_cache_time = time.time()


def invalidate_license_cache():
    global _license_cache, _license_cache_time
    _license_cache = None
    _license_cache_time = 0
