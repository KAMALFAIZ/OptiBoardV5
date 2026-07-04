"""
Module Console Stats
====================
Endpoint de monitoring lu par la console KASOFT (gestion du parc multi-produits).

    GET /api/console/instance-stats   (header obligatoire : X-Console-Token)
    - 404 si CONSOLE_TOKEN non configuré (endpoint désactivé, défaut)
    - 401 si le token est absent ou erroné
    - 200 + snapshot JSON sinon

Contrat aligné sur le type `InstanceStats` du front console (api.ts) :
    version, schemaVersion, users*/companies*, modulesVisible/Active,
    license{customerCode,customerName,packCode,expiryDate,maxUsers,usedUsers,
            maxCompanies,usedCompanies,aiMonthlyTokens,aiTokensUsedMonth},
    ai{tokensMonth,callsMonth,costMonth,currency,monthlyTokenLimit}.

Sources :
    - Base centrale OptiBoard_SaaS (APP_DWH, APP_Users) — parc & utilisateurs
    - Licence locale signée par la console (JWT RS256) — pack, quotas, modules
    - APP_AI_Usage (services.ai_usage) — usage IA du mois (Phase 1)

Note : le coût IA (costMonth/currency) reste à None — la facturation MAD est
décidée en Phase 2b (arbitrage). Le quota IA est ici EXPOSÉ (monthlyTokenLimit)
mais PAS appliqué : l'application du plafond est la Phase 2b.
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


def _license_claims() -> Optional[dict]:
    """Claims VÉRIFIÉS de la licence console (JWT RS256), ou None (absente/legacy).

    Vérifie la SIGNATURE avec la clé publique embarquée (license-public.pem).
    Renvoie les claims même si expirée (l'affichage montre expiryDate).
    """
    try:
        from ..services.license_service import _verify_console_jwt
        key = (getattr(get_settings(), "LICENSE_KEY", "") or "").strip()
        if not key:
            return None
        return _verify_console_jwt(key)  # None si signature/format non-console
    except Exception as e:
        logger.warning(f"console_stats license claims: {e}")
        return None


def _iso_date_from_exp(exp) -> Optional[str]:
    """Timestamp Unix (claim exp) → 'YYYY-MM-DD', ou None si invalide."""
    try:
        return datetime.fromtimestamp(int(exp), timezone.utc).date().isoformat()
    except (ValueError, TypeError, OSError):
        return None


def _modules(claims: Optional[dict]):
    """(modulesVisible, modulesActive) depuis la licence.
    Visible = `modules` ; Active = modules + `engines` (moteurs cachés licenciés)."""
    if not claims:
        return [], []
    visible = [m for m in (claims.get("modules") or [])]
    engines = [e for e in (claims.get("engines") or [])]
    active = visible + [e for e in engines if e not in visible]
    return visible, active


def _ai_usage_month() -> dict:
    """Usage IA agrégé du mois courant (toute l'installation)."""
    try:
        from ..services.ai_usage import monthly_usage
        return monthly_usage()
    except Exception as e:
        logger.warning(f"console_stats ai usage: {e}")
        return {"calls": 0, "tokensMonth": 0}


def _license_block(claims: Optional[dict], users_active, companies, tokens_used):
    """Bloc `license` aligné sur le front console.
    Champs de plafond absents = illimité → None (JAMAIS 0)."""
    if claims:
        return {
            "customerCode": claims.get("sub"),
            "customerName": claims.get("customer"),
            "packCode": claims.get("pack"),
            "expiryDate": _iso_date_from_exp(claims.get("exp")),
            "maxUsers": claims.get("maxUsers"),           # absent = illimité → null
            "usedUsers": users_active,
            "maxCompanies": claims.get("maxCompanies"),   # absent = illimité → null
            "usedCompanies": companies,
            "aiMonthlyTokens": claims.get("aiMonthlyTokens"),  # absent = illimité → null
            "aiTokensUsedMonth": tokens_used,
        }
    # Repli : licence legacy (HMAC / serveur) via le statut mis en cache.
    try:
        from ..services.license_service import get_cached_license_status
        st = get_cached_license_status()
        if not st:
            return None
        exp = getattr(st, "expiry_date", None)
        return {
            "customerCode": None,
            "customerName": getattr(st, "organization", None),
            "packCode": getattr(st, "plan", None),
            "expiryDate": exp.date().isoformat() if exp else None,
            "maxUsers": (getattr(st, "max_users", 0) or None),
            "usedUsers": users_active,
            "maxCompanies": (getattr(st, "max_dwh", 0) or None),
            "usedCompanies": companies,
            "aiMonthlyTokens": None,
            "aiTokensUsedMonth": tokens_used,
        }
    except Exception as e:
        logger.warning(f"console_stats legacy license: {e}")
        return None


@router.get("/instance-stats")
def instance_stats(x_console_token: Optional[str] = Header(None, alias="X-Console-Token")):
    """Snapshot de l'instance pour le monitoring console (parc KASOFT)."""
    _check_token(x_console_token)

    companies    = _scalar_central("SELECT COUNT(*) AS n FROM APP_DWH")
    users_total  = _scalar_central("SELECT COUNT(*) AS n FROM APP_Users")
    users_active = _scalar_central("SELECT COUNT(*) AS n FROM APP_Users WHERE actif = 1")

    claims = _license_claims()
    usage = _ai_usage_month()
    tokens_used = int(usage.get("tokensMonth") or 0)
    calls_month = int(usage.get("calls") or 0)
    # Quota IA mensuel : claim absent = illimité → None (jamais 0)
    ai_limit = claims.get("aiMonthlyTokens") if claims else None

    modules_visible, modules_active = _modules(claims)

    return {
        "version": os.environ.get("APP_VERSION") or "dev",
        "schemaVersion": "1",
        "usersActive": users_active,
        "usersTotal": users_total,
        "companiesActive": companies,
        "companiesTotal": companies,
        "modulesVisible": modules_visible,
        "modulesActive": modules_active,
        "license": _license_block(claims, users_active, companies, tokens_used),
        "ai": {
            "tokensMonth": tokens_used,
            "callsMonth": calls_month,
            "costMonth": None,        # Phase 2b — arbitrage n°2 (calcul du coût MAD)
            "currency": None,
            "monthlyTokenLimit": ai_limit,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
