"""
CredentialResolver — Source de vérité unique pour les credentials Sage
======================================================================
Principe : les credentials Sage appartiennent au client et résident dans
APP_ETL_Agents (base client OptiBoard_cltXXX).

APP_DWH_Sources (base centrale) ne contient PLUS de credentials depuis
la refactorisation v3 (Phase 3) — les colonnes serveur_sage, base_sage,
user_sage, password_sage ont été supprimées. APP_DWH_Sources ne porte
que le planning ETL, le lien agent_id et le monitoring.

Fallback (rétrocompat pre-Phase-3) : si APP_ETL_Agents est inaccessible,
la Stratégie 2 tente de lire les credentials depuis APP_DWH_Sources.
Ce fallback ne fonctionne plus après la migration Phase 3 (colonnes DROP).

Cache TTL : 5 minutes (300s) par clé (dwh_code, code_societe).
Invalidation : appeler CredentialResolver.invalidate(dwh_code) après
tout changement de credentials dans APP_ETL_Agents.
"""

import logging
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, NamedTuple

from .secret_crypto import dec_secret

logger = logging.getLogger(__name__)

# Import lazy pour éviter les imports circulaires
_db = None


def _get_db():
    global _db
    if _db is None:
        from ..database_unified import execute_client, execute_central
        _db = {"execute_client": execute_client, "execute_central": execute_central}
    return _db


class SageCredentials(NamedTuple):
    serveur:    str
    base:       str
    username:   str
    password:   str
    nom_societe: str = ""
    source:     str = "agent"  # "agent" | "dwh_sources" (fallback)


class SageSourceNotFoundError(Exception):
    pass


class CredentialResolver:
    """
    Résolveur de credentials Sage — singleton thread-safe avec cache TTL.

    Usage :
        creds = CredentialResolver.get(dwh_code="KA", societe_code="KA")
        conn_str = f"SERVER={creds.serveur};DATABASE={creds.base};UID={creds.username};PWD={creds.password}"
    """

    _cache: Dict[str, tuple] = {}
    _lock = threading.Lock()
    _TTL = timedelta(seconds=300)

    # ──────────────────────────────────────────────────────────────
    # API publique
    # ──────────────────────────────────────────────────────────────

    @classmethod
    def get(cls, dwh_code: str, societe_code: Optional[str] = None) -> SageCredentials:
        """
        Retourne les credentials Sage pour (dwh_code, societe_code).
        Lève SageSourceNotFoundError si aucun agent actif trouvé.
        """
        cache_key = f"{dwh_code}:{societe_code or '*'}"

        # Lecture cache
        with cls._lock:
            if cache_key in cls._cache:
                creds, ts = cls._cache[cache_key]
                if datetime.now() - ts < cls._TTL:
                    return creds

        # Résolution
        creds = cls._resolve(dwh_code, societe_code)

        with cls._lock:
            cls._cache[cache_key] = (creds, datetime.now())

        return creds

    @classmethod
    def invalidate(cls, dwh_code: str, societe_code: Optional[str] = None):
        """Invalide le cache pour un DWH (ou une société spécifique)."""
        with cls._lock:
            if societe_code:
                cls._cache.pop(f"{dwh_code}:{societe_code}", None)
            else:
                keys_to_del = [k for k in cls._cache if k.startswith(f"{dwh_code}:")]
                for k in keys_to_del:
                    del cls._cache[k]

    @classmethod
    def invalidate_all(cls):
        """Vide tout le cache (ex: après migration)."""
        with cls._lock:
            cls._cache.clear()

    # ──────────────────────────────────────────────────────────────
    # Résolution interne
    # ──────────────────────────────────────────────────────────────

    @classmethod
    def _resolve(cls, dwh_code: str, societe_code: Optional[str]) -> SageCredentials:
        db = _get_db()

        # ── Stratégie 1 : APP_ETL_Agents (base client — source de vérité) ──
        try:
            creds = cls._from_etl_agents(db, dwh_code, societe_code)
            if creds:
                logger.debug(
                    f"[CredentialResolver] {dwh_code}/{societe_code} → APP_ETL_Agents ✓"
                )
                return creds
        except Exception as e:
            logger.warning(
                f"[CredentialResolver] APP_ETL_Agents inaccessible pour {dwh_code}: {e}"
            )

        # ── Stratégie 2 : APP_DWH_Sources (fallback rétrocompat) ──
        try:
            creds = cls._from_dwh_sources(db, dwh_code, societe_code)
            if creds:
                logger.warning(
                    f"[CredentialResolver] {dwh_code}/{societe_code} → fallback APP_DWH_Sources "
                    f"(migrez les credentials vers APP_ETL_Agents)"
                )
                return creds
        except Exception as e:
            logger.error(
                f"[CredentialResolver] Fallback APP_DWH_Sources échoué pour {dwh_code}: {e}"
            )

        raise SageSourceNotFoundError(
            f"Aucun credentials Sage trouvé pour DWH='{dwh_code}', "
            f"société='{societe_code or 'any'}'. "
            f"Vérifiez qu'un agent ETL actif est configuré pour ce DWH."
        )

    @classmethod
    def _from_etl_agents(
        cls, db, dwh_code: str, societe_code: Optional[str]
    ) -> Optional[SageCredentials]:
        """Lit depuis APP_ETL_Agents (base client)."""
        execute_client = db["execute_client"]

        # Filtre optionnel sur code_societe si la colonne existe
        # On tente d'abord avec code_societe, puis sans si la colonne n'existe pas
        queries = []
        if societe_code:
            queries.append((
                """
                SELECT TOP 1
                    sage_server   AS serveur,
                    sage_database AS base,
                    sage_username AS username,
                    sage_password AS password,
                    ISNULL(nom, '') AS nom_societe
                FROM APP_ETL_Agents
                WHERE is_active = 1
                  AND (
                      code_societe = ?
                      OR sage_database = ?
                  )
                ORDER BY last_heartbeat DESC
                """,
                (societe_code, societe_code)
            ))

        # Fallback : premier agent actif du DWH
        queries.append((
            """
            SELECT TOP 1
                sage_server   AS serveur,
                sage_database AS base,
                sage_username AS username,
                sage_password AS password,
                ISNULL(nom, '') AS nom_societe
            FROM APP_ETL_Agents
            WHERE is_active = 1
            ORDER BY last_heartbeat DESC
            """,
            ()
        ))

        for query, params in queries:
            try:
                rows = execute_client(query, params or None, dwh_code=dwh_code, use_cache=False)
                if rows:
                    r = rows[0]
                    if r.get("serveur") and r.get("base"):
                        return SageCredentials(
                            serveur=r["serveur"],
                            base=r["base"],
                            username=r.get("username") or "",
                            # Secret chiffre au repos depuis 2026-08 (prefix $sec1$) —
                            # dec_secret laisse passer le plaintext legacy tel quel.
                            password=dec_secret(r.get("password")) or "",
                            nom_societe=r.get("nom_societe") or "",
                            source="agent",
                        )
            except Exception as e:
                # Colonne code_societe peut ne pas exister sur ancienne install
                logger.debug(f"[CredentialResolver] query attempt failed: {e}")
                continue

        return None

    @classmethod
    def _from_dwh_sources(
        cls, db, dwh_code: str, societe_code: Optional[str]
    ) -> Optional[SageCredentials]:
        """
        Fallback rétrocompat : lit les credentials depuis APP_DWH_Sources (base centrale).

        ⚠️  Après la migration Phase 3, les colonnes serveur_sage/base_sage/user_sage/
        password_sage ont été supprimées de APP_DWH_Sources.
        Cette méthode est conservée pour les installations pre-Phase-3 qui n'ont pas
        encore de colonne agent_id. Elle lève une exception si les colonnes sont absentes,
        ce qui est capturé par _resolve() qui passe alors à SageSourceNotFoundError.
        """
        execute_central = db["execute_central"]

        where = "dwh_code = ? AND actif = 1"
        params: tuple = (dwh_code,)
        if societe_code:
            where += " AND code_societe = ?"
            params = (dwh_code, societe_code)

        # Vérifier si les colonnes credentials existent encore (pre-Phase-3)
        check = execute_central(
            "SELECT 1 FROM sys.columns "
            "WHERE object_id = OBJECT_ID('APP_DWH_Sources') AND name = 'serveur_sage'",
            use_cache=False,
        )
        if not check:
            # Phase 3 migrée — colonnes supprimées, fallback impossible
            logger.debug(
                "[CredentialResolver] APP_DWH_Sources colonnes credentials absentes "
                "(Phase 3 complète) — fallback indisponible pour %s/%s",
                dwh_code, societe_code
            )
            return None

        rows = execute_central(
            f"""
            SELECT TOP 1
                serveur_sage  AS serveur,
                base_sage     AS base,
                user_sage     AS username,
                password_sage AS password,
                ISNULL(nom_societe, '') AS nom_societe
            FROM APP_DWH_Sources
            WHERE {where}
              AND serveur_sage IS NOT NULL
              AND base_sage    IS NOT NULL
            ORDER BY id
            """,
            params,
            use_cache=False,
        )
        if not rows:
            return None
        r = rows[0]
        if not r.get("serveur") or not r.get("base"):
            return None
        return SageCredentials(
            serveur=r["serveur"],
            base=r["base"],
            username=r.get("username") or "",
            password=r.get("password") or "",
            nom_societe=r.get("nom_societe") or "",
            source="dwh_sources",
        )
