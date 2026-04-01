"""
Routes API pour la gestion des licences OptiBoard
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import logging

from app.config import get_settings, save_env_config, reload_settings
from app.database_unified import execute_central as execute_master_query
from app.services.license_service import (
    validate_license,
    get_machine_id,
    decode_license_payload,
    get_cached_license_status,
    set_cached_license_status,
    invalidate_license_cache,
    check_user_limit,
    check_dwh_limit,
    check_feature_access,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/license", tags=["License"])


# ============================================================
# Schemas
# ============================================================
class ActivateLicenseRequest(BaseModel):
    license_key: str


class LicenseResponse(BaseModel):
    success: bool
    license: Optional[dict] = None
    message: str = ""


# ============================================================
# Endpoints
# ============================================================

@router.get("/status")
async def license_status():
    """
    Retourne le statut actuel de la licence.
    Appele au demarrage du frontend pour verifier si l'app est licenciee.
    """
    settings = get_settings()

    if not settings.LICENSE_KEY:
        return {
            "success": True,
            "licensed": False,
            "status": "no_license",
            "machine_id": get_machine_id(),
            "message": "Aucune licence activee"
        }

    # Verifier le cache d'abord
    cached = get_cached_license_status()
    if cached:
        return {
            "success": True,
            "licensed": cached.valid,
            "license": cached.to_dict()
        }

    # Valider la licence
    status = validate_license(
        license_key=settings.LICENSE_KEY,
        server_url=settings.LICENSE_SERVER_URL,
        grace_days=settings.LICENSE_GRACE_DAYS
    )

    # Mettre en cache
    set_cached_license_status(status)

    return {
        "success": True,
        "licensed": status.valid,
        "license": status.to_dict()
    }


@router.get("/machine-id")
async def get_machine_info():
    """
    Retourne l'identifiant unique de cette machine.
    Necessaire pour generer une licence liee a cette machine.
    """
    return {
        "success": True,
        "machine_id": get_machine_id()
    }


@router.post("/activate")
async def activate_license(request: ActivateLicenseRequest):
    """
    Active une licence sur cette installation.
    1. Decode la licence pour verifier le format
    2. Valide aupres du serveur distant
    3. Sauvegarde dans .env si valide
    """
    license_key = request.license_key.strip()

    if not license_key:
        raise HTTPException(status_code=400, detail="Cle de licence requise")

    # 1. Decoder pour verifier le format
    payload = decode_license_payload(license_key)
    if not payload:
        raise HTTPException(status_code=400, detail="Format de licence invalide")

    # 2. Valider la licence
    settings = get_settings()
    status = validate_license(
        license_key=license_key,
        server_url=settings.LICENSE_SERVER_URL,
        grace_days=settings.LICENSE_GRACE_DAYS
    )

    if not status.valid:
        raise HTTPException(
            status_code=403,
            detail=f"Licence invalide: {status.message}"
        )

    # 3. Sauvegarder dans .env
    save_env_config({"LICENSE_KEY": license_key})
    reload_settings()

    # 4. Mettre en cache
    invalidate_license_cache()
    set_cached_license_status(status)

    logger.info(f"[LICENSE] Licence activee pour: {status.organization} (plan: {status.plan})")

    return {
        "success": True,
        "message": f"Licence activee avec succes pour {status.organization}",
        "license": status.to_dict()
    }


@router.post("/deactivate")
async def deactivate_license():
    """
    Desactive la licence sur cette installation.
    Necessaire pour transferer la licence sur une autre machine.
    """
    settings = get_settings()
    if not settings.LICENSE_KEY:
        return {"success": True, "message": "Aucune licence a desactiver"}

    # Notifier le serveur de licences (liberer le slot machine)
    from app.services.license_service import validate_license_remote
    machine_id = get_machine_id()

    try:
        import urllib.request
        url = f"{settings.LICENSE_SERVER_URL.rstrip('/')}/license/deactivate"
        payload_data = json.dumps({
            "license_key": settings.LICENSE_KEY,
            "machine_id": machine_id
        }).encode()
        req = urllib.request.Request(
            url, data=payload_data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        urllib.request.urlopen(req, timeout=15)
    except Exception as e:
        logger.warning(f"[LICENSE] Impossible de notifier le serveur: {e}")

    # Supprimer la licence locale
    save_env_config({"LICENSE_KEY": ""})
    reload_settings()
    invalidate_license_cache()

    logger.info("[LICENSE] Licence desactivee")

    return {
        "success": True,
        "message": "Licence desactivee"
    }


@router.post("/refresh")
async def refresh_license():
    """
    Force la re-validation de la licence aupres du serveur.
    """
    invalidate_license_cache()

    settings = get_settings()
    if not settings.LICENSE_KEY:
        return {"success": False, "message": "Aucune licence configuree"}

    status = validate_license(
        license_key=settings.LICENSE_KEY,
        server_url=settings.LICENSE_SERVER_URL,
        grace_days=settings.LICENSE_GRACE_DAYS
    )

    set_cached_license_status(status)

    return {
        "success": status.valid,
        "license": status.to_dict()
    }


@router.get("/features")
async def get_license_features():
    """
    Retourne la liste des fonctionnalites disponibles selon la licence.
    """
    settings = get_settings()

    if not settings.LICENSE_KEY:
        return {
            "success": True,
            "features": [],
            "plan": "none"
        }

    cached = get_cached_license_status()
    if not cached:
        cached = validate_license(
            license_key=settings.LICENSE_KEY,
            server_url=settings.LICENSE_SERVER_URL,
            grace_days=settings.LICENSE_GRACE_DAYS
        )
        set_cached_license_status(cached)

    return {
        "success": True,
        "features": cached.features,
        "plan": cached.plan,
        "max_users": cached.max_users,
        "max_dwh": cached.max_dwh
    }


@router.get("/check-limits")
async def check_limits():
    """
    Verifie les limites de la licence (utilisateurs, DWH).
    """
    settings = get_settings()
    if not settings.LICENSE_KEY:
        return {"success": False, "message": "Aucune licence"}

    cached = get_cached_license_status()
    if not cached:
        cached = validate_license(
            license_key=settings.LICENSE_KEY,
            server_url=settings.LICENSE_SERVER_URL,
            grace_days=settings.LICENSE_GRACE_DAYS
        )
        set_cached_license_status(cached)

    # Compter les utilisateurs et DWH actuels
    from app.database_unified import execute_central as execute_master_query
    try:
        users_result = execute_master_query(
            "SELECT COUNT(*) as total FROM APP_Users WHERE actif = 1",
            use_cache=False
        )
        current_users = users_result[0]["total"] if users_result else 0
    except Exception:
        current_users = 0

    try:
        dwh_result = execute_master_query(
            "SELECT COUNT(*) as total FROM APP_DWH WHERE actif = 1",
            use_cache=False
        )
        current_dwh = dwh_result[0]["total"] if dwh_result else 0
    except Exception:
        current_dwh = 0

    return {
        "success": True,
        "users": {
            "current": current_users,
            "max": cached.max_users,
            "within_limit": check_user_limit(cached, current_users)
        },
        "dwh": {
            "current": current_dwh,
            "max": cached.max_dwh,
            "within_limit": check_dwh_limit(cached, current_dwh)
        }
    }


import json
