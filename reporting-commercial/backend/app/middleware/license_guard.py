"""
License Guard — utilitaires de contrôle des fonctionnalités par licence.

Usage dans les routes :
    from app.middleware.license_guard import get_effective_row_limit, is_feature_licensed, is_limited_mode

Fonctionnalités licensiables :
    ai_assistant    — Assistant IA (chat + génération SQL)
    unlimited_rows  — Résultats illimités (sinon TOP 100)
    multi_dwh       — Connexions DWH multiples
    export          — Export Excel / PDF
    user_management — Gestion utilisateurs et rôles
    advanced_reports— Rapports avancés / pivots
    all             — Accès complet (toutes fonctionnalités)
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Limite imposée quand la licence ne couvre pas unlimited_rows
RESTRICTED_ROW_LIMIT = 100


def get_effective_row_limit() -> int:
    """
    Retourne le nombre maximum de lignes autorisé selon la licence active.
    - Si mode DEBUG → utilise AI_SQL_MAX_ROWS configuré
    - Si unlimited_rows ou all dans les features → utilise AI_SQL_MAX_ROWS
    - Sinon → 100
    """
    try:
        from ..config import get_settings
        settings = get_settings()

        # En mode DEBUG, pas de restriction
        if settings.DEBUG:
            return getattr(settings, "AI_SQL_MAX_ROWS", 500) or 500

        from ..services.license_service import get_cached_license_status
        cached = get_cached_license_status()

        if not cached or not cached.valid:
            logger.debug("[LICENSE GUARD] Licence invalide/absente → TOP 100")
            return RESTRICTED_ROW_LIMIT

        feats = cached.features or []
        if "all" in feats or "unlimited_rows" in feats:
            return getattr(settings, "AI_SQL_MAX_ROWS", 500) or 500

        logger.debug("[LICENSE GUARD] unlimited_rows non licencié → TOP 100")
        return RESTRICTED_ROW_LIMIT

    except Exception as e:
        logger.warning(f"[LICENSE GUARD] get_effective_row_limit error: {e}")
        return RESTRICTED_ROW_LIMIT


def is_feature_licensed(feature: str) -> bool:
    """
    Vérifie si une fonctionnalité est couverte par la licence active.
    Retourne True en mode DEBUG.
    """
    try:
        from ..config import get_settings
        settings = get_settings()

        if settings.DEBUG:
            return True

        from ..services.license_service import get_cached_license_status, check_feature_access
        cached = get_cached_license_status()

        if not cached:
            return False

        return check_feature_access(cached, feature)

    except Exception as e:
        logger.warning(f"[LICENSE GUARD] is_feature_licensed({feature}) error: {e}")
        return False


def is_limited_mode() -> bool:
    """
    Retourne True si l'application tourne en mode limité (TOP 100).
    Utile pour inclure un avertissement dans les réponses API.
    """
    return not is_feature_licensed("unlimited_rows")


def get_license_restriction_info() -> Optional[dict]:
    """
    Retourne un dict d'info sur la restriction active, ou None si aucune restriction.
    Injecté dans les réponses API pour informer le frontend.

    Exemple de retour :
    {
        "limited": True,
        "row_limit": 100,
        "reason": "unlimited_rows non inclus dans votre licence",
        "feature_required": "unlimited_rows"
    }
    """
    if not is_limited_mode():
        return None

    return {
        "limited": True,
        "row_limit": RESTRICTED_ROW_LIMIT,
        "reason": "Résultats limités à 100 lignes — passez à un plan supérieur pour lever cette restriction",
        "feature_required": "unlimited_rows"
    }
