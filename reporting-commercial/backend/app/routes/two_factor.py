"""
Routes 2FA (Two-Factor Authentication) — OptiBoard.

Flux complet :
  1. Admin demande la configuration : GET  /api/auth/2fa/setup
     → génère un secret TOTP + retourne le QR code en base64
  2. Admin valide le premier code    : POST /api/auth/2fa/activate
     → active le 2FA sur le compte si le code est correct
  3. Admin désactive le 2FA          : POST /api/auth/2fa/disable
  4. Vérification au login           : POST /api/auth/2fa/verify
     → appelée par LoginPage avec le temp_token + code 6 chiffres
"""

import base64
import io
import time
import hashlib
import logging
from typing import Dict, Any, Optional

import pyotp
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth/2fa", tags=["2FA"])

# ── Stockage temporaire des tokens en attente de validation 2FA ───────────────
# {temp_token: {"user_id": int, "username": str, "expires": float, "login_data": dict}}
_pending_2fa: Dict[str, Dict[str, Any]] = {}
_TEMP_TOKEN_TTL = 300   # 5 minutes


def _cleanup_pending():
    now = time.time()
    expired = [k for k, v in _pending_2fa.items() if v["expires"] < now]
    for k in expired:
        del _pending_2fa[k]


def create_temp_token(user_id: int, username: str, login_data: dict) -> str:
    """Crée un token temporaire en attente de validation 2FA."""
    _cleanup_pending()
    raw = f"{user_id}:{username}:{time.time()}"
    token = hashlib.sha256(raw.encode()).hexdigest()[:32]
    _pending_2fa[token] = {
        "user_id": user_id,
        "username": username,
        "expires": time.time() + _TEMP_TOKEN_TTL,
        "login_data": login_data,
    }
    return token


def consume_temp_token(token: str) -> Optional[Dict[str, Any]]:
    """Consomme un token temporaire (le supprime après lecture)."""
    _cleanup_pending()
    data = _pending_2fa.pop(token, None)
    if data and data["expires"] >= time.time():
        return data
    return None


# ── Schemas ───────────────────────────────────────────────────────────────────

class SetupRequest(BaseModel):
    user_id: int
    is_central: bool = True    # True = base centrale, False = base client
    dwh_code: Optional[str] = None

class ActivateRequest(BaseModel):
    user_id: int
    totp_code: str
    is_central: bool = True
    dwh_code: Optional[str] = None

class DisableRequest(BaseModel):
    user_id: int
    totp_code: str
    is_central: bool = True
    dwh_code: Optional[str] = None

class VerifyRequest(BaseModel):
    temp_token: str
    totp_code: str


# ── Helpers DB ────────────────────────────────────────────────────────────────

def _get_user_totp(user_id: int, is_central: bool, dwh_code: Optional[str]) -> Optional[Dict]:
    from ..database_unified import execute_central, execute_client
    try:
        if is_central:
            rows = execute_central(
                "SELECT id, totp_secret, ISNULL(totp_enabled,0) AS totp_enabled FROM APP_Users WHERE id = ?",
                (user_id,), use_cache=False,
            )
        else:
            rows = execute_client(
                "SELECT id, totp_secret, ISNULL(totp_enabled,0) AS totp_enabled FROM APP_Users WHERE id = ?",
                (user_id,), dwh_code=dwh_code, use_cache=False,
            )
        return rows[0] if rows else None
    except Exception as e:
        logger.error(f"[2FA] _get_user_totp error: {e}")
        return None


def _write_totp(user_id: int, secret: str, enabled: bool, is_central: bool, dwh_code: Optional[str]):
    from ..database_unified import write_central, write_client
    sql = "UPDATE APP_Users SET totp_secret = ?, totp_enabled = ? WHERE id = ?"
    params = (secret, 1 if enabled else 0, user_id)
    if is_central:
        write_central(sql, params)
    else:
        write_client(sql, params, dwh_code=dwh_code)


# ── Route : générer QR code ───────────────────────────────────────────────────

@router.post("/setup")
async def setup_2fa(body: SetupRequest):
    """
    Génère un secret TOTP et retourne le QR code en base64.
    N'active PAS encore le 2FA — l'utilisateur doit valider un premier code.
    """
    user = _get_user_totp(body.user_id, body.is_central, body.dwh_code)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

    # Réutiliser le secret existant si déjà généré mais pas encore activé
    if user.get("totp_secret") and not user.get("totp_enabled"):
        secret = user["totp_secret"]
    else:
        secret = pyotp.random_base32()
        _write_totp(body.user_id, secret, enabled=False,
                    is_central=body.is_central, dwh_code=body.dwh_code)

    # Générer l'URI otpauth://
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=f"user_{body.user_id}", issuer_name="OptiBoard")

    # Générer le QR code PNG en base64
    try:
        import qrcode
        qr = qrcode.make(uri)
        buf = io.BytesIO()
        qr.save(buf, format="PNG")
        qr_b64 = base64.b64encode(buf.getvalue()).decode()
    except ImportError:
        qr_b64 = None   # qrcode non installé — frontend affiche l'URI en texte

    return {
        "success": True,
        "secret": secret,
        "uri": uri,
        "qr_code_base64": qr_b64,
        "instructions": "Scannez le QR code avec Google Authenticator ou Authy, puis entrez le code à 6 chiffres pour activer.",
    }


# ── Route : activer le 2FA ────────────────────────────────────────────────────

@router.post("/activate")
async def activate_2fa(body: ActivateRequest):
    """
    Valide le premier code TOTP et active le 2FA sur le compte.
    """
    user = _get_user_totp(body.user_id, body.is_central, body.dwh_code)
    if not user or not user.get("totp_secret"):
        raise HTTPException(status_code=400, detail="Aucun secret 2FA en attente — lancez d'abord /setup")

    secret = user["totp_secret"]
    totp = pyotp.TOTP(secret)

    if not totp.verify(body.totp_code, valid_window=1):
        raise HTTPException(status_code=400, detail="Code 2FA invalide")

    _write_totp(body.user_id, secret, enabled=True,
                is_central=body.is_central, dwh_code=body.dwh_code)

    logger.info(f"[2FA] Activé pour user_id={body.user_id}")
    return {"success": True, "message": "Authentification à deux facteurs activée avec succès"}


# ── Route : désactiver le 2FA ─────────────────────────────────────────────────

@router.post("/disable")
async def disable_2fa(body: DisableRequest):
    """
    Désactive le 2FA après validation du code actuel.
    """
    user = _get_user_totp(body.user_id, body.is_central, body.dwh_code)
    if not user or not user.get("totp_secret") or not user.get("totp_enabled"):
        raise HTTPException(status_code=400, detail="Le 2FA n'est pas activé sur ce compte")

    totp = pyotp.TOTP(user["totp_secret"])
    if not totp.verify(body.totp_code, valid_window=1):
        raise HTTPException(status_code=400, detail="Code 2FA invalide")

    _write_totp(body.user_id, "", enabled=False,
                is_central=body.is_central, dwh_code=body.dwh_code)

    logger.info(f"[2FA] Désactivé pour user_id={body.user_id}")
    return {"success": True, "message": "Authentification à deux facteurs désactivée"}


# ── Route : vérifier le code au login ────────────────────────────────────────

@router.post("/verify")
async def verify_2fa(body: VerifyRequest):
    """
    Valide le code TOTP pendant le flux de login.
    Consomme le temp_token et retourne le LoginResponse complet si le code est valide.
    """
    pending = consume_temp_token(body.temp_token)
    if not pending:
        raise HTTPException(status_code=401, detail="Session 2FA expirée ou invalide — reconnectez-vous")

    login_data = pending["login_data"]
    totp_secret = login_data.get("totp_secret")
    if not totp_secret:
        raise HTTPException(status_code=500, detail="Secret 2FA absent du contexte")

    totp = pyotp.TOTP(totp_secret)
    if not totp.verify(body.totp_code, valid_window=1):
        # Remettre le token en attente pour permettre un nouvel essai
        _pending_2fa[body.temp_token] = {**pending, "expires": time.time() + 60}
        raise HTTPException(status_code=400, detail="Code 2FA invalide")

    # Retourner les données complètes de login (sans le secret TOTP)
    safe_data = {k: v for k, v in login_data.items() if k != "totp_secret"}
    logger.info(f"[2FA] Vérifié avec succès pour user_id={pending['user_id']}")
    return {"success": True, "verified": True, **safe_data}


# ── Route : statut 2FA d'un utilisateur ──────────────────────────────────────

@router.get("/status/{user_id}")
async def get_2fa_status(user_id: int, is_central: bool = True, dwh_code: Optional[str] = None):
    """Retourne si le 2FA est activé pour un utilisateur."""
    user = _get_user_totp(user_id, is_central, dwh_code)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    return {
        "user_id": user_id,
        "totp_enabled": bool(user.get("totp_enabled")),
    }
