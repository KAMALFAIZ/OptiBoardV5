"""
Database Unified Module pour OptiBoard
========================================
Module unifie remplacant database.py et database_multitenant.py

Architecture 3 niveaux:
- CENTRAL (OptiBoard_SaaS)  : utilisateurs, config, licences, DWH registry
- CLIENT  (OptiBoard_XXX)   : parametres specifiques client (dashboards, menus, etc.)
- DWH     (DWH_XXX)         : donnees commerciales (ventes, stocks, recouvrement)

Fonctions d'acces:
- execute_central()  : toujours vers OptiBoard_SaaS
- execute_client()   : vers OptiBoard_XXX du tenant courant
- execute_dwh()      : vers DWH_XXX du tenant courant
- execute_app()      : vers OptiBoard_XXX si existe, sinon OptiBoard_SaaS (avec log)
"""

import pyodbc
import logging
import warnings
import threading
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Generator, List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

import pandas as pd

from .config_multitenant import (
    get_central_settings,
    DWHConfig,
    ClientDBConfig,
    SocieteConfig,
    UserContext
)
from .services.cache import query_cache, CACHE_TTL

logger = logging.getLogger(__name__)


# =====================================================
# EXCEPTIONS
# =====================================================

class DatabaseNotConfiguredError(Exception):
    """Base centrale non configuree"""
    pass


class DWHNotFoundError(Exception):
    """DWH non trouve ou inactif"""
    pass


class ClientDBNotFoundError(Exception):
    """Base client OptiBoard_XXX non trouvee"""
    pass


class TenantContextError(Exception):
    """Contexte tenant manquant ou invalide"""
    pass


# =====================================================
# CONTEXTE TENANT (contextvars - async-safe)
# =====================================================

current_dwh_code: ContextVar[Optional[str]] = ContextVar('current_dwh_code', default=None)
current_user_id: ContextVar[Optional[int]] = ContextVar('current_user_id', default=None)
current_societe: ContextVar[Optional[str]] = ContextVar('current_societe', default=None)


def set_tenant_context(
    dwh_code: Optional[str] = None,
    user_id: Optional[int] = None,
    societe: Optional[str] = None
) -> Dict[str, Any]:
    """
    Definit le contexte tenant pour la coroutine courante.
    Retourne les tokens pour reset ulterieur.
    """
    tokens = {}
    if dwh_code is not None:
        tokens['dwh'] = current_dwh_code.set(dwh_code)
    if user_id is not None:
        tokens['user'] = current_user_id.set(user_id)
    if societe is not None:
        tokens['societe'] = current_societe.set(societe)
    return tokens


def reset_tenant_context(tokens: Dict[str, Any]):
    """Reset le contexte tenant avec les tokens de set_tenant_context."""
    if 'dwh' in tokens:
        current_dwh_code.reset(tokens['dwh'])
    if 'user' in tokens:
        current_user_id.reset(tokens['user'])
    if 'societe' in tokens:
        current_societe.reset(tokens['societe'])


def clear_tenant_context():
    """Efface completement le contexte tenant."""
    current_dwh_code.set(None)
    current_user_id.set(None)
    current_societe.set(None)


def get_tenant_dwh_code() -> Optional[str]:
    """Retourne le DWH code du contexte courant."""
    return current_dwh_code.get()


def get_tenant_user_id() -> Optional[int]:
    """Retourne le user ID du contexte courant."""
    return current_user_id.get()


def require_dwh_code() -> str:
    """Retourne le DWH code ou leve TenantContextError si absent."""
    code = current_dwh_code.get()
    if not code:
        raise TenantContextError(
            "Aucun DWH selectionne. Header X-DWH-Code requis."
        )
    return code


# =====================================================
# CONNEXION CENTRALE (OptiBoard_SaaS)
# =====================================================

def get_central_connection() -> pyodbc.Connection:
    """Cree une connexion vers la base centrale OptiBoard_SaaS."""
    settings = get_central_settings()
    if not settings.is_configured:
        raise DatabaseNotConfiguredError(
            "La base centrale n'est pas configuree. "
            "Verifiez le fichier .env ou utilisez /api/setup/configure"
        )
    return pyodbc.connect(settings.central_database_url)


@contextmanager
def central_cursor() -> Generator[pyodbc.Cursor, None, None]:
    """Context manager pour un cursor vers la base centrale."""
    conn = get_central_connection()
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()


def execute_central(
    query: str,
    params: Optional[tuple] = None,
    use_cache: bool = True,
    cache_ttl: int = None
) -> List[Dict[str, Any]]:
    """
    Execute une requete SELECT sur la base centrale OptiBoard_SaaS.
    TOUJOURS vers CENTRAL - jamais de routing implicite.
    """
    cache_key = f"central:__:{query}"

    if use_cache:
        cached_result = query_cache.get(cache_key, params)
        if cached_result is not None:
            return cached_result

    with central_cursor() as cursor:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        if cursor.description is None:
            return []

        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]

    if use_cache and results:
        ttl = cache_ttl or CACHE_TTL.get("default", 300)
        query_cache.set(cache_key, params, results, ttl)

    return results


def write_central(
    query: str,
    params: Optional[tuple] = None
) -> int:
    """Execute une requete d'ecriture sur la base centrale. Retourne rowcount."""
    with central_cursor() as cursor:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor.rowcount


def test_central_connection() -> bool:
    """Teste la connexion a la base centrale."""
    try:
        with central_cursor() as cursor:
            cursor.execute("SELECT 1")
            return True
    except Exception as e:
        logger.error(f"Central DB connection error: {e}")
        return False


# =====================================================
# GESTION DES DWH CLIENTS (DWH_XXX)
# =====================================================

class DWHConnectionPool:
    """
    Pool de connexions pour les DWH clients.
    Thread-safe singleton avec cache des configurations.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._dwh_cache = {}
                    cls._instance._cache_lock = threading.Lock()
                    cls._instance._cache_ttl = 300
        return cls._instance

    def _get_dwh_info(self, dwh_code: str) -> Optional[DWHConfig]:
        """Recupere les infos DWH depuis le cache ou la DB centrale."""
        now = datetime.now()

        with self._cache_lock:
            if dwh_code in self._dwh_cache:
                cached, timestamp = self._dwh_cache[dwh_code]
                if now - timestamp < timedelta(seconds=self._cache_ttl):
                    return cached

        # Charger depuis la base centrale (hors du lock)
        query = """
            SELECT code, nom, raison_sociale, serveur_dwh, base_dwh,
                   user_dwh, password_dwh, logo_url, actif
            FROM APP_DWH
            WHERE code = ? AND actif = 1
        """
        results = execute_central(query, (dwh_code,), use_cache=False)

        if not results:
            return None

        dwh_config = DWHConfig(**results[0])
        with self._cache_lock:
            self._dwh_cache[dwh_code] = (dwh_config, now)
        return dwh_config

    def get_connection(self, dwh_code: str) -> pyodbc.Connection:
        """Obtient une connexion vers un DWH. Leve DWHNotFoundError si absent."""
        dwh_info = self._get_dwh_info(dwh_code)
        if not dwh_info:
            raise DWHNotFoundError(f"DWH '{dwh_code}' non trouve ou inactif")
        return pyodbc.connect(dwh_info.connection_string)

    def clear_cache(self, dwh_code: str = None):
        """Vide le cache des DWH."""
        with self._cache_lock:
            if dwh_code:
                self._dwh_cache.pop(dwh_code, None)
            else:
                self._dwh_cache.clear()


# Instance globale du pool DWH
dwh_pool = DWHConnectionPool()


@contextmanager
def dwh_cursor(dwh_code: str) -> Generator[pyodbc.Cursor, None, None]:
    """Context manager pour un cursor vers un DWH client."""
    conn = dwh_pool.get_connection(dwh_code)
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()


def execute_dwh(
    query: str,
    params: Optional[tuple] = None,
    dwh_code: Optional[str] = None,
    use_cache: bool = True,
    cache_ttl: int = None
) -> List[Dict[str, Any]]:
    """
    Execute une requete SELECT sur le DWH du tenant courant (DWH_XXX).

    Args:
        query: Requete SQL
        params: Parametres de la requete
        dwh_code: Code DWH explicite. Si None, utilise le contexte courant.
        use_cache: Activer le cache
        cache_ttl: TTL du cache en secondes

    Raises:
        TenantContextError: Si aucun DWH dans le contexte
        DWHNotFoundError: Si le DWH n'existe pas
    """
    code = dwh_code or require_dwh_code()
    cache_key = f"dwh:{code}:{query}"

    if use_cache:
        cached_result = query_cache.get(cache_key, params)
        if cached_result is not None:
            return cached_result

    # Prefixe SQL: forcer le format de date YMD (ISO) et supprimer les erreurs
    # de conversion implicite varchar→datetime qui renvoient NULL au lieu d'exception.
    # Cela evite l'erreur 242 (out-of-range smalldatetime) sur les donnees DWH
    # qui peuvent contenir des dates hors limites (ex: 0001-01-01, valeurs nulles Sage).
    _DWH_PREFIX = "SET DATEFORMAT YMD; SET ANSI_WARNINGS OFF; SET ARITHABORT OFF;\n"
    query_prefixed = _DWH_PREFIX + query

    with dwh_cursor(code) as cursor:
        if params:
            cursor.execute(query_prefixed, params)
        else:
            cursor.execute(query_prefixed)

        if cursor.description is None:
            return []

        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]

    if use_cache and results:
        ttl = cache_ttl or CACHE_TTL.get("default", 300)
        query_cache.set(cache_key, params, results, ttl)

    return results


def write_dwh(
    query: str,
    params: Optional[tuple] = None,
    dwh_code: Optional[str] = None
) -> int:
    """Execute une ecriture sur le DWH du tenant courant."""
    code = dwh_code or require_dwh_code()
    with dwh_cursor(code) as cursor:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor.rowcount


def execute_dwh_df(
    query: str,
    params: Optional[tuple] = None,
    dwh_code: Optional[str] = None
) -> pd.DataFrame:
    """Execute une requete sur le DWH et retourne un DataFrame."""
    code = dwh_code or require_dwh_code()
    conn = dwh_pool.get_connection(code)
    try:
        if params:
            df = pd.read_sql(query, conn, params=params)
        else:
            df = pd.read_sql(query, conn)
        return df
    finally:
        conn.close()


def test_dwh_connection(dwh_code: str) -> Tuple[bool, str]:
    """Teste la connexion a un DWH."""
    try:
        with dwh_cursor(dwh_code) as cursor:
            cursor.execute("SELECT 1")
            return True, "Connexion reussie"
    except DWHNotFoundError:
        return False, f"DWH '{dwh_code}' non trouve"
    except Exception as e:
        return False, f"Erreur de connexion: {str(e)}"


# =====================================================
# GESTION DES BASES CLIENT (OptiBoard_XXX)
# =====================================================

class ClientConnectionManager:
    """
    Gestionnaire de connexions vers les bases client OptiBoard_XXX.
    Thread-safe singleton avec cache des configurations.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._client_cache = {}
                    cls._instance._cache_lock = threading.Lock()
                    cls._instance._cache_ttl = 300
        return cls._instance

    def _get_client_db_info(self, dwh_code: str) -> Optional[ClientDBConfig]:
        """
        Recupere les infos de la base client depuis le cache ou CENTRAL.
        Priorité credentials : APP_ClientDB.db_server > APP_DWH.serveur_optiboard
                               > APP_DWH.serveur_dwh > settings centraux.
        """
        now = datetime.now()

        with self._cache_lock:
            if dwh_code in self._client_cache:
                cached, timestamp = self._client_cache[dwh_code]
                if now - timestamp < timedelta(seconds=self._cache_ttl):
                    return cached

        try:
            # JOIN avec APP_DWH pour récupérer les credentials optiboard per-client
            query = """
                SELECT
                    c.dwh_code, c.db_name, c.actif,
                    COALESCE(c.db_server,   d.serveur_optiboard, d.serveur_dwh)   AS db_server,
                    COALESCE(c.db_user,     d.user_optiboard,    d.user_dwh)       AS db_user,
                    COALESCE(c.db_password, d.password_optiboard, d.password_dwh)  AS db_password
                FROM APP_ClientDB c
                LEFT JOIN APP_DWH d ON d.code = c.dwh_code
                WHERE UPPER(c.dwh_code) = UPPER(?) AND c.actif = 1
            """
            results = execute_central(query, (dwh_code,), use_cache=False)
        except Exception as e:
            logger.warning(f"APP_ClientDB lookup failed for '{dwh_code}': {e}")
            return None

        if not results:
            # Fallback : essayer directement APP_DWH (cas où APP_ClientDB n'a pas d'entrée)
            try:
                fallback = execute_central("""
                    SELECT code AS dwh_code, base_optiboard AS db_name,
                           serveur_optiboard AS db_server,
                           COALESCE(user_optiboard, user_dwh) AS db_user,
                           COALESCE(password_optiboard, password_dwh) AS db_password,
                           1 AS actif
                    FROM APP_DWH
                    WHERE UPPER(code) = UPPER(?) AND actif = 1
                      AND base_optiboard IS NOT NULL AND base_optiboard != ''
                """, (dwh_code,), use_cache=False)
                if not fallback:
                    return None
                results = fallback
            except Exception:
                return None

        config = ClientDBConfig(**results[0])
        with self._cache_lock:
            self._client_cache[dwh_code] = (config, now)
        return config

    def get_connection(self, dwh_code: str) -> pyodbc.Connection:
        """
        Obtient une connexion vers une base client OptiBoard_XXX.
        Leve ClientDBNotFoundError si pas de base client configuree.
        PAS de fallback silencieux vers CENTRAL.
        """
        config = self._get_client_db_info(dwh_code)
        if not config:
            raise ClientDBNotFoundError(
                f"Pas de base client configuree pour DWH '{dwh_code}'"
            )

        settings = get_central_settings()
        conn_str = config.get_connection_string(settings)
        return pyodbc.connect(conn_str)

    def has_client_db(self, dwh_code: str) -> bool:
        """Verifie si un DWH a une base client configuree."""
        return self._get_client_db_info(dwh_code) is not None

    def clear_cache(self, dwh_code: str = None):
        """Vide le cache des bases client."""
        with self._cache_lock:
            if dwh_code:
                self._client_cache.pop(dwh_code, None)
            else:
                self._client_cache.clear()


# Instance globale
client_manager = ClientConnectionManager()


@contextmanager
def client_cursor(dwh_code: str) -> Generator[pyodbc.Cursor, None, None]:
    """Context manager pour un cursor vers une base client OptiBoard_XXX."""
    conn = client_manager.get_connection(dwh_code)
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()


def execute_client(
    query: str,
    params: Optional[tuple] = None,
    dwh_code: Optional[str] = None,
    use_cache: bool = True,
    cache_ttl: int = None
) -> List[Dict[str, Any]]:
    """
    Execute une requete SELECT sur la base client OptiBoard_XXX.

    Raises:
        TenantContextError: Si aucun DWH dans le contexte
        ClientDBNotFoundError: Si pas de base client pour ce DWH
    """
    code = dwh_code or require_dwh_code()
    cache_key = f"client:{code}:{query}"

    if use_cache:
        cached_result = query_cache.get(cache_key, params)
        if cached_result is not None:
            return cached_result

    with client_cursor(code) as cursor:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        if cursor.description is None:
            return []

        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]

    if use_cache and results:
        ttl = cache_ttl or CACHE_TTL.get("default", 300)
        query_cache.set(cache_key, params, results, ttl)

    return results


def write_client(
    query: str,
    params: Optional[tuple] = None,
    dwh_code: Optional[str] = None
) -> int:
    """Execute une ecriture sur la base client."""
    code = dwh_code or require_dwh_code()
    with client_cursor(code) as cursor:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor.rowcount


# =====================================================
# ROUTAGE APP (client si existe, sinon central)
# =====================================================

def execute_app(
    query: str,
    params: Optional[tuple] = None,
    dwh_code: Optional[str] = None,
    use_cache: bool = True,
    cache_ttl: int = None
) -> List[Dict[str, Any]]:
    """
    Execute une requete sur la base client OptiBoard_XXX si disponible,
    sinon sur CENTRAL. Utiliser pour les tables APP_ specifiques au client.

    C'est le SEUL fallback autorise. Il est logue pour faciliter la migration.
    """
    code = dwh_code or current_dwh_code.get()

    if code and client_manager.has_client_db(code):
        return execute_client(query, params, dwh_code=code,
                              use_cache=use_cache, cache_ttl=cache_ttl)

    # Fallback vers CENTRAL - logue pour tracking
    if code:
        logger.debug(
            f"execute_app fallback vers CENTRAL pour DWH '{code}' "
            f"(pas de base client)"
        )
    return execute_central(query, params, use_cache=use_cache, cache_ttl=cache_ttl)


def write_app(
    query: str,
    params: Optional[tuple] = None,
    dwh_code: Optional[str] = None
) -> int:
    """
    Execute une ecriture sur la base client si disponible, sinon CENTRAL.
    """
    code = dwh_code or current_dwh_code.get()

    if code and client_manager.has_client_db(code):
        return write_client(query, params, dwh_code=code)

    if code:
        logger.debug(
            f"write_app fallback vers CENTRAL pour DWH '{code}'"
        )
    return write_central(query, params)


@contextmanager
def app_cursor(dwh_code: Optional[str] = None) -> Generator[pyodbc.Cursor, None, None]:
    """
    Context manager pour un cursor vers la base client si disponible,
    sinon vers CENTRAL.
    """
    code = dwh_code or current_dwh_code.get()

    if code and client_manager.has_client_db(code):
        with client_cursor(code) as cursor:
            yield cursor
    else:
        if code:
            logger.debug(f"app_cursor fallback vers CENTRAL pour DWH '{code}'")
        with central_cursor() as cursor:
            yield cursor


# =====================================================
# FONCTIONS UTILITAIRES
# =====================================================

def get_user_dwh_list(user_id: int) -> List[Dict[str, Any]]:
    """Recupere la liste des DWH accessibles par un utilisateur."""
    query = """
        SELECT d.code, d.nom, d.raison_sociale, d.logo_url,
               ud.role_dwh, ud.is_default
        FROM APP_UserDWH ud
        INNER JOIN APP_DWH d ON ud.dwh_code = d.code
        WHERE ud.user_id = ? AND d.actif = 1
        ORDER BY ud.is_default DESC, d.nom
    """
    return execute_central(query, (user_id,), use_cache=False)


def get_user_societes(user_id: int, dwh_code: str) -> List[Dict[str, Any]]:
    """Recupere les societes accessibles par un utilisateur dans un DWH."""
    query = """
        SELECT us.societe_code, s.nom_societe,
               us.can_view, us.can_export, us.can_edit
        FROM APP_UserSocietes us
        INNER JOIN APP_DWH_Sources s ON us.dwh_code = s.dwh_code AND us.societe_code = s.code_societe
        WHERE us.user_id = ? AND us.dwh_code = ? AND s.actif = 1
    """
    return execute_central(query, (user_id, dwh_code), use_cache=False)


def get_all_dwh_societes(dwh_code: str) -> List[Dict[str, Any]]:
    """Recupere toutes les societes d'un DWH (pour admin)."""
    query = """
        SELECT code_societe, nom_societe, serveur_sage, base_sage,
               etl_enabled, last_sync, last_sync_status, actif
        FROM APP_DWH_Sources
        WHERE dwh_code = ?
        ORDER BY nom_societe
    """
    return execute_central(query, (dwh_code,), use_cache=False)


def get_dwh_info(dwh_code: str) -> Optional[Dict[str, Any]]:
    """Recupere les informations d'un DWH."""
    query = """
        SELECT code, nom, raison_sociale, adresse, ville, pays,
               telephone, email, logo_url, serveur_dwh, base_dwh,
               actif, date_creation
        FROM APP_DWH
        WHERE code = ?
    """
    results = execute_central(query, (dwh_code,), use_cache=True)
    return results[0] if results else None


def create_user_context(user_data: Dict[str, Any], dwh_code: str = None) -> UserContext:
    """Cree un contexte utilisateur complet."""
    user_id = user_data["id"]

    # Charger les DWH accessibles
    dwh_list = get_user_dwh_list(user_id)

    # Determiner le DWH actif
    if dwh_code:
        current_dwh = next((d for d in dwh_list if d["code"] == dwh_code), None)
    else:
        current_dwh = next((d for d in dwh_list if d.get("is_default")), None)
        if not current_dwh and dwh_list:
            current_dwh = dwh_list[0]

    # Charger les societes accessibles
    societes = []
    role_dwh = "user"
    if current_dwh:
        role_dwh = current_dwh.get("role_dwh", "user")

        if role_dwh == "admin_client" or user_data.get("role_global") == "superadmin":
            all_societes = get_all_dwh_societes(current_dwh["code"])
            societes = [s["code_societe"] for s in all_societes if s.get("actif")]
        else:
            user_societes = get_user_societes(user_id, current_dwh["code"])
            societes = [s["societe_code"] for s in user_societes if s.get("can_view")]

    # Charger les pages accessibles (via execute_app pour client ou central)
    pages_query = "SELECT page_code FROM APP_UserPages WHERE user_id = ?"
    if current_dwh:
        pages = execute_app(pages_query, (user_id,), dwh_code=current_dwh["code"],
                            use_cache=False)
    else:
        pages = execute_central(pages_query, (user_id,), use_cache=False)
    pages_list = [p["page_code"] for p in pages]

    return UserContext(
        user_id=user_id,
        username=user_data["username"],
        nom=user_data["nom"],
        prenom=user_data["prenom"],
        email=user_data.get("email"),
        role_global=user_data.get("role_global", "user"),
        current_dwh_code=current_dwh["code"] if current_dwh else None,
        current_dwh_nom=current_dwh["nom"] if current_dwh else None,
        role_dwh=role_dwh,
        societes_accessibles=societes,
        dwh_accessibles=[{
            "code": d["code"],
            "nom": d["nom"],
            "raison_sociale": d.get("raison_sociale"),
            "logo_url": d.get("logo_url"),
            "is_default": d.get("is_default", False)
        } for d in dwh_list],
        pages_accessibles=pages_list
    )


def build_societe_filter(
    user_context: UserContext,
    column_name: str = "societe_code"
) -> Tuple[str, tuple]:
    """
    Construit une clause WHERE pour filtrer par societe.
    Retourne (clause_sql, params).
    """
    societes = user_context.get_societe_filter()

    if not societes:
        return "", ()

    if len(societes) == 1:
        return f"{column_name} = ?", (societes[0],)

    placeholders = ",".join(["?" for _ in societes])
    return f"{column_name} IN ({placeholders})", tuple(societes)


# =====================================================
# SHIM DWHConnectionManager (compatibilite arriere)
# =====================================================

class DWHConnectionManager:
    """
    DEPRECIE: Shim de compatibilite pour l'ancien DWHConnectionManager.
    Utiliser execute_dwh(), dwh_cursor(), etc. a la place.
    """

    @staticmethod
    def get_dwh_connection_string(dwh_info: Dict[str, str]) -> str:
        """Construit la chaine de connexion pour un DWH."""
        return (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={dwh_info['serveur_dwh']};"
            f"DATABASE={dwh_info['base_dwh']};"
            f"UID={dwh_info['user_dwh']};"
            f"PWD={dwh_info['password_dwh']};"
            f"TrustServerCertificate=yes"
        )

    @staticmethod
    def get_dwh_by_code(dwh_code: str) -> Optional[Dict[str, Any]]:
        """Recupere les informations d'un DWH par son code."""
        return get_dwh_info(dwh_code)

    @staticmethod
    def get_dwh_connection(dwh_code: str) -> pyodbc.Connection:
        """Cree une connexion vers un DWH specifique."""
        return dwh_pool.get_connection(dwh_code)

    @staticmethod
    @contextmanager
    def dwh_cursor(dwh_code_param: str) -> Generator[pyodbc.Cursor, None, None]:
        """Context manager pour un cursor vers un DWH specifique."""
        with dwh_cursor(dwh_code_param) as cursor:
            yield cursor

    @staticmethod
    def execute_dwh_query(
        dwh_code: str,
        query: str,
        params: Optional[tuple] = None,
        use_cache: bool = True,
        cache_ttl: int = None
    ) -> List[Dict[str, Any]]:
        """Execute une requete sur un DWH specifique."""
        return execute_dwh(query, params, dwh_code=dwh_code,
                           use_cache=use_cache, cache_ttl=cache_ttl)

    @staticmethod
    def execute_dwh_query_df(
        dwh_code: str,
        query: str,
        params: Optional[tuple] = None
    ) -> pd.DataFrame:
        """Execute une requete sur un DWH et retourne un DataFrame."""
        return execute_dwh_df(query, params, dwh_code=dwh_code)

    @staticmethod
    def test_dwh_connection(dwh_code: str) -> bool:
        """Teste la connexion a un DWH."""
        ok, _ = test_dwh_connection(dwh_code)
        return ok


# Instance globale du gestionnaire (compatibilite)
dwh_manager = DWHConnectionManager()


# =====================================================
# COMPATIBILITE ARRIERE (shims avec deprecation)
# =====================================================
# Ces fonctions permettent la migration progressive.
# Chaque appel emet un DeprecationWarning.

def _deprecation_shim(old_name: str, new_name: str):
    """Emet un warning de deprecation."""
    warnings.warn(
        f"{old_name}() est deprecie. Utiliser {new_name}() a la place.",
        DeprecationWarning,
        stacklevel=3
    )
    logger.warning(f"DEPRECATION: {old_name}() appele, migrer vers {new_name}()")


# --- Shims depuis database.py ---

def set_current_dwh_code(dwh_code: Optional[str]):
    """DEPRECIE: Utiliser set_tenant_context(dwh_code=...)"""
    _deprecation_shim("set_current_dwh_code", "set_tenant_context")
    current_dwh_code.set(dwh_code)


def get_current_dwh_code() -> Optional[str]:
    """DEPRECIE: Utiliser get_tenant_dwh_code()"""
    _deprecation_shim("get_current_dwh_code", "get_tenant_dwh_code")
    return current_dwh_code.get()


def get_connection() -> pyodbc.Connection:
    """DEPRECIE: Utiliser get_central_connection()"""
    _deprecation_shim("get_connection", "get_central_connection")
    return get_central_connection()


def get_master_connection() -> pyodbc.Connection:
    """DEPRECIE: Utiliser get_central_connection()"""
    _deprecation_shim("get_master_connection", "get_central_connection")
    return get_central_connection()


def get_db_cursor():
    """DEPRECIE: Utiliser central_cursor() ou app_cursor()"""
    _deprecation_shim("get_db_cursor", "central_cursor/app_cursor")
    return central_cursor()


def get_master_cursor():
    """DEPRECIE: Utiliser central_cursor()"""
    _deprecation_shim("get_master_cursor", "central_cursor")
    return central_cursor()


def execute_query(
    query: str,
    params: Optional[tuple] = None,
    use_cache: bool = True,
    cache_ttl: int = None
) -> List[Dict[str, Any]]:
    """DEPRECIE: Utiliser execute_central(), execute_dwh() ou execute_app()"""
    _deprecation_shim("execute_query", "execute_central/execute_dwh/execute_app")
    return execute_central(query, params, use_cache, cache_ttl)


def execute_master_query(
    query: str,
    params: Optional[tuple] = None,
    use_cache: bool = True,
    cache_ttl: int = None
) -> List[Dict[str, Any]]:
    """DEPRECIE: Utiliser execute_central()"""
    _deprecation_shim("execute_master_query", "execute_central")
    return execute_central(query, params, use_cache, cache_ttl)


def execute_query_df(query: str, params: Optional[tuple] = None) -> pd.DataFrame:
    """DEPRECIE: Utiliser execute_dwh_df() ou pd.read_sql avec get_central_connection()"""
    _deprecation_shim("execute_query_df", "execute_dwh_df")
    conn = get_central_connection()
    try:
        if params:
            df = pd.read_sql(query, conn, params=params)
        else:
            df = pd.read_sql(query, conn)
        return df
    finally:
        conn.close()


def test_connection() -> bool:
    """DEPRECIE: Utiliser test_central_connection()"""
    _deprecation_shim("test_connection", "test_central_connection")
    return test_central_connection()


# --- Shims depuis database_multitenant.py ---

def execute_central_query(
    query: str,
    params: Optional[tuple] = None,
    use_cache: bool = True,
    cache_ttl: int = None
) -> List[Dict[str, Any]]:
    """DEPRECIE: Utiliser execute_central()"""
    _deprecation_shim("execute_central_query", "execute_central")
    return execute_central(query, params, use_cache, cache_ttl)


def execute_central_write(
    query: str,
    params: Optional[tuple] = None
) -> int:
    """DEPRECIE: Utiliser write_central()"""
    _deprecation_shim("execute_central_write", "write_central")
    return write_central(query, params)


def execute_dwh_query(
    dwh_code: str,
    query: str,
    params: Optional[tuple] = None,
    use_cache: bool = True,
    cache_ttl: int = None
) -> List[Dict[str, Any]]:
    """DEPRECIE: Utiliser execute_dwh(query, params, dwh_code=code)"""
    _deprecation_shim("execute_dwh_query", "execute_dwh")
    return execute_dwh(query, params, dwh_code=dwh_code,
                       use_cache=use_cache, cache_ttl=cache_ttl)


def execute_dwh_write(
    dwh_code: str,
    query: str,
    params: Optional[tuple] = None
) -> int:
    """DEPRECIE: Utiliser write_dwh(query, params, dwh_code=code)"""
    _deprecation_shim("execute_dwh_write", "write_dwh")
    return write_dwh(query, params, dwh_code=dwh_code)


def execute_dwh_query_df(
    dwh_code: str,
    query: str,
    params: Optional[tuple] = None
) -> pd.DataFrame:
    """DEPRECIE: Utiliser execute_dwh_df(query, params, dwh_code=code)"""
    _deprecation_shim("execute_dwh_query_df", "execute_dwh_df")
    return execute_dwh_df(query, params, dwh_code=dwh_code)


def execute_client_query(
    dwh_code: str,
    query: str,
    params: Optional[tuple] = None,
    use_cache: bool = True,
    cache_ttl: int = None
) -> List[Dict[str, Any]]:
    """DEPRECIE: Utiliser execute_client(query, params, dwh_code=code)"""
    _deprecation_shim("execute_client_query", "execute_client")
    return execute_client(query, params, dwh_code=dwh_code,
                          use_cache=use_cache, cache_ttl=cache_ttl)


def execute_client_write(
    dwh_code: str,
    query: str,
    params: Optional[tuple] = None
) -> int:
    """DEPRECIE: Utiliser write_client(query, params, dwh_code=code)"""
    _deprecation_shim("execute_client_write", "write_client")
    return write_client(query, params, dwh_code=dwh_code)


def execute_app_query(
    dwh_code: Optional[str],
    query: str,
    params: Optional[tuple] = None,
    use_cache: bool = True,
    cache_ttl: int = None
) -> List[Dict[str, Any]]:
    """DEPRECIE: Utiliser execute_app(query, params, dwh_code=code)"""
    _deprecation_shim("execute_app_query", "execute_app")
    return execute_app(query, params, dwh_code=dwh_code,
                       use_cache=use_cache, cache_ttl=cache_ttl)


def execute_app_write(
    dwh_code: Optional[str],
    query: str,
    params: Optional[tuple] = None
) -> int:
    """DEPRECIE: Utiliser write_app(query, params, dwh_code=code)"""
    _deprecation_shim("execute_app_write", "write_app")
    return write_app(query, params, dwh_code=dwh_code)


def execute_query_with_context(
    user_context: UserContext,
    query: str,
    params: Optional[tuple] = None,
    use_cache: bool = True,
    cache_ttl: int = None
) -> List[Dict[str, Any]]:
    """DEPRECIE: Utiliser execute_dwh() avec le contexte tenant"""
    _deprecation_shim("execute_query_with_context", "execute_dwh")
    if not user_context.current_dwh_code:
        raise ValueError("Aucun DWH selectionne pour l'utilisateur")
    return execute_dwh(query, params, dwh_code=user_context.current_dwh_code,
                       use_cache=use_cache, cache_ttl=cache_ttl)
