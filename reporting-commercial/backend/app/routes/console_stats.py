"""
Module Console Stats
====================
Endpoint de monitoring lu par la console KASOFT (gestion du parc multi-produits).

Contrat aligné sur ERP-Vision (/api/admin/instance-stats) :
    GET /api/console/instance-stats   (header obligatoire : X-Console-Token)
    - 404 si CONSOLE_TOKEN non configuré (endpoint désactivé, défaut)
    - 401 si le token est absent ou erroné
    - 200 + snapshot JSON sinon

Source des données :
    Base centrale OptiBoard_SaaS (APP_DWH = clients/DWH, APP_User = utilisateurs)
    + licence locale hors-ligne (services.license_service).
"""
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Header, HTTPException

from ..config import get_settings
from ..database_unified import execute_central

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/console", tags=["Console KASOFT"])


def _check_token(token: Optional[str]) -> None:
    """404 si l'endpoint est désactivé (token non configuré), 401 si token invalide."""
    settings = get_settings()
    expected = (getattr(settings, "CONSOLE_TOKEN", "") or "").strip()
    if not expected:
        raise HTTPException(status_code=404, detail="Endpoint console désactivé (CONSOLE_TOKEN non configuré)")
    if not token or token.strip() != expected:
        raise HTTPException(status_code=401, detail="X-Console-Token absent ou invalide")


def _scalar_central(sql: str):
    """SELECT COUNT(*) AS n sur la base centrale — None si la table/base est absente."""
    try:
        rows = execute_central(sql, use_cache=False)
        if rows:
            first = rows[0]
            if isinstance(first, dict):
                return next(iter(first.values()), None)
            return first
        return 0
    except Exception as e:
        logger.warning(f"console_stats scalar: {e}")
        return None


def _license_block(companies):
    """Licence locale (hors-ligne) décodée depuis LICENSE_KEY — None si indisponible."""
    try:
        from ..services.license_service import decode_license_payload, get_cached_license_status
        settings = get_settings()
        payload = decode_license_payload(getattr(settings, "LICENSE_KEY", "") or "")
        status = get_cached_license_status()
        if not payload and status is None:
            return None
        block = {}
        if payload:
            block["customerName"] = payload.get("organization") or payload.get("org")
            block["packCode"] = payload.get("plan")
            block["maxUsers"] = payload.get("max_users")
            block["maxCompanies"] = payload.get("max_dwh")
            block["expiryDate"] = payload.get("expiry_date") or payload.get("expiry")
        block["usedCompanies"] = companies
        return block or None
    except Exception as e:
        logger.warning(f"console_stats license: {e}")
        return None


@router.get("/instance-stats")
def instance_stats(x_console_token: Optional[str] = Header(None, alias="X-Console-Token")):
    """Snapshot de l'instance pour le monitoring console (parc KASOFT)."""
    _check_token(x_console_token)

    companies = _scalar_central("SELECT COUNT(*) AS n FROM APP_DWH")
    users = _scalar_central("SELECT COUNT(*) AS n FROM APP_User")

    return {
        "version": os.environ.get("APP_VERSION") or "dev",
        "usersActive": users,
        "usersTotal": users,
        "companiesActive": companies,
        "companiesTotal": companies,
        "license": _license_block(companies),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
