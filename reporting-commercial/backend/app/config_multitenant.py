"""
Configuration Multi-Tenant pour OptiBoard
==========================================
Gestion de la connexion centrale (OptiBoard_SaaS) et des DWH clients
"""

from pydantic_settings import BaseSettings
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from pathlib import Path
from functools import lru_cache
import os


# Chemin absolu vers le fichier .env
ENV_FILE_PATH = Path(__file__).parent.parent / ".env"


class CentralDBSettings(BaseSettings):
    """Configuration de la base centrale OptiBoard_SaaS"""

    # Base centrale (CENTRAL_DB_*) avec fallback sur DB_* pour compatibilite
    CENTRAL_DB_SERVER: str = ""
    CENTRAL_DB_NAME: str = ""
    CENTRAL_DB_USER: str = ""
    CENTRAL_DB_PASSWORD: str = ""
    CENTRAL_DB_DRIVER: str = "{ODBC Driver 17 for SQL Server}"

    # Fallback: anciennes cles DB_* (utilisees si CENTRAL_DB_* vides)
    DB_SERVER: str = ""
    DB_NAME: str = ""
    DB_USER: str = ""
    DB_PASSWORD: str = ""
    DB_DRIVER: str = "{ODBC Driver 17 for SQL Server}"

    # Application settings
    APP_NAME: str = "OptiBoard"
    DEBUG: bool = True
    SECRET_KEY: str = "optiboard-secret-key-change-in-production"

    # Cache settings
    CACHE_TTL: int = 300  # 5 minutes
    CACHE_TTL_DASHBOARD: int = 300
    CACHE_TTL_VENTES: int = 600
    CACHE_TTL_STOCKS: int = 300
    CACHE_TTL_RECOUVREMENT: int = 600

    # Query settings
    MAX_ROWS: int = 10000
    QUERY_TIMEOUT: int = 30

    # Session settings
    SESSION_EXPIRE_MINUTES: int = 480  # 8 heures

    @property
    def _effective_server(self) -> str:
        return self.CENTRAL_DB_SERVER or self.DB_SERVER

    @property
    def _effective_name(self) -> str:
        return self.CENTRAL_DB_NAME or self.DB_NAME

    @property
    def _effective_user(self) -> str:
        return self.CENTRAL_DB_USER or self.DB_USER

    @property
    def _effective_password(self) -> str:
        return self.CENTRAL_DB_PASSWORD or self.DB_PASSWORD

    @property
    def _effective_driver(self) -> str:
        return self.CENTRAL_DB_DRIVER or self.DB_DRIVER

    @property
    def central_database_url(self) -> str:
        """Connection string pour la base centrale"""
        return (
            f"DRIVER={self._effective_driver};"
            f"SERVER={self._effective_server};"
            f"DATABASE={self._effective_name};"
            f"UID={self._effective_user};"
            f"PWD={self._effective_password};"
            f"TrustServerCertificate=yes"
        )

    @property
    def is_configured(self) -> bool:
        """Verifie si la base centrale est configuree (CENTRAL_DB_* ou DB_*)"""
        return bool(
            self._effective_server and
            self._effective_name and
            self._effective_user and
            self._effective_password
        )

    class Config:
        env_file = str(ENV_FILE_PATH)
        env_file_encoding = 'utf-8'
        extra = 'ignore'


class DWHConfig(BaseModel):
    """Configuration d'un DWH client"""
    code: str
    nom: str
    raison_sociale: Optional[str] = None
    serveur_dwh: str
    base_dwh: str
    user_dwh: str
    password_dwh: str
    logo_url: Optional[str] = None
    actif: bool = True

    @property
    def connection_string(self) -> str:
        """Connection string pour ce DWH"""
        return (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={self.serveur_dwh};"
            f"DATABASE={self.base_dwh};"
            f"UID={self.user_dwh};"
            f"PWD={self.password_dwh};"
            f"TrustServerCertificate=yes"
        )


class ClientDBConfig(BaseModel):
    """Configuration d'une base client OptiBoard_XXX"""
    dwh_code: str
    db_name: str
    db_server: Optional[str] = None   # NULL = meme serveur que MASTER
    db_user: Optional[str] = None     # NULL = memes credentials que MASTER
    db_password: Optional[str] = None
    actif: bool = True

    def get_connection_string(self, master_settings: 'CentralDBSettings') -> str:
        """Connection string pour la base client"""
        server = self.db_server or master_settings._effective_server
        user = self.db_user or master_settings._effective_user
        password = self.db_password or master_settings._effective_password
        driver = master_settings._effective_driver
        return (
            f"DRIVER={driver};"
            f"SERVER={server};"
            f"DATABASE={self.db_name};"
            f"UID={user};"
            f"PWD={password};"
            f"TrustServerCertificate=yes"
        )


class SocieteConfig(BaseModel):
    """Configuration d'une societe Sage source"""
    dwh_code: str
    code_societe: str
    nom_societe: str
    serveur_sage: str
    base_sage: str
    user_sage: str
    password_sage: str
    etl_enabled: bool = True
    etl_mode: str = "incremental"
    actif: bool = True

    @property
    def connection_string(self) -> str:
        """Connection string pour la base Sage"""
        return (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={self.serveur_sage};"
            f"DATABASE={self.base_sage};"
            f"UID={self.user_sage};"
            f"PWD={self.password_sage};"
            f"TrustServerCertificate=yes"
        )


class UserContext(BaseModel):
    """Contexte utilisateur pour une session"""
    user_id: int
    username: str
    nom: str
    prenom: str
    email: Optional[str] = None
    role_global: str = "user"

    # DWH actif
    current_dwh_code: Optional[str] = None
    current_dwh_nom: Optional[str] = None
    role_dwh: str = "user"

    # Societes accessibles dans le DWH actif
    societes_accessibles: List[str] = []
    societe_active: Optional[str] = None  # Filtre societe actif

    # DWH accessibles
    dwh_accessibles: List[Dict[str, Any]] = []

    # Pages accessibles
    pages_accessibles: List[str] = []

    def has_page_access(self, page_code: str) -> bool:
        """Verifie si l'utilisateur a acces a une page"""
        if self.role_global == "superadmin":
            return True
        return page_code in self.pages_accessibles

    def has_dwh_access(self, dwh_code: str) -> bool:
        """Verifie si l'utilisateur a acces a un DWH"""
        if self.role_global == "superadmin":
            return True
        return any(d.get("code") == dwh_code for d in self.dwh_accessibles)

    def has_societe_access(self, societe_code: str) -> bool:
        """Verifie si l'utilisateur a acces a une societe"""
        if self.role_global == "superadmin" or self.role_dwh == "admin_client":
            return True
        return societe_code in self.societes_accessibles

    def get_societe_filter(self) -> List[str]:
        """Retourne la liste des societes pour le filtre SQL"""
        if self.societe_active:
            return [self.societe_active]
        return self.societes_accessibles if self.societes_accessibles else []

    def is_admin(self) -> bool:
        """Verifie si l'utilisateur est admin (global ou DWH)"""
        return self.role_global in ["superadmin", "admin"] or self.role_dwh == "admin_client"


# Cache global pour les settings
_settings_cache: Optional[CentralDBSettings] = None


def get_central_settings() -> CentralDBSettings:
    """Retourne les settings de la base centrale"""
    global _settings_cache
    if _settings_cache is None:
        _settings_cache = CentralDBSettings()
    return _settings_cache


def reload_central_settings() -> CentralDBSettings:
    """Force le rechargement des settings"""
    global _settings_cache
    _settings_cache = CentralDBSettings()
    return _settings_cache


def save_central_config(config: dict) -> bool:
    """Sauvegarde la configuration centrale dans le fichier .env"""
    env_path = ENV_FILE_PATH

    # Lire le fichier existant
    existing_content = {}
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    existing_content[key.strip()] = value.strip()

    # Mapper les anciennes cles vers les nouvelles si necessaire
    key_mapping = {
        'DB_SERVER': 'CENTRAL_DB_SERVER',
        'DB_NAME': 'CENTRAL_DB_NAME',
        'DB_USER': 'CENTRAL_DB_USER',
        'DB_PASSWORD': 'CENTRAL_DB_PASSWORD',
        'DB_DRIVER': 'CENTRAL_DB_DRIVER'
    }

    for old_key, new_key in key_mapping.items():
        if old_key in config:
            config[new_key] = config.pop(old_key)
        if old_key in existing_content and new_key not in existing_content:
            existing_content[new_key] = existing_content.pop(old_key)

    # Mettre a jour avec les nouvelles valeurs
    existing_content.update(config)

    # Ecrire le fichier
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write("# =====================================================\n")
        f.write("# OptiBoard Configuration - Multi-Tenant\n")
        f.write("# =====================================================\n\n")

        f.write("# Base Centrale (OptiBoard_SaaS)\n")
        f.write(f"CENTRAL_DB_SERVER={existing_content.get('CENTRAL_DB_SERVER', '')}\n")
        f.write(f"CENTRAL_DB_NAME={existing_content.get('CENTRAL_DB_NAME', 'OptiBoard_SaaS')}\n")
        f.write(f"CENTRAL_DB_USER={existing_content.get('CENTRAL_DB_USER', '')}\n")
        f.write(f"CENTRAL_DB_PASSWORD={existing_content.get('CENTRAL_DB_PASSWORD', '')}\n")
        f.write(f"CENTRAL_DB_DRIVER={existing_content.get('CENTRAL_DB_DRIVER', '{ODBC Driver 17 for SQL Server}')}\n")

        f.write("\n# Application Settings\n")
        f.write(f"APP_NAME={existing_content.get('APP_NAME', 'OptiBoard')}\n")
        f.write(f"DEBUG={existing_content.get('DEBUG', 'True')}\n")
        f.write(f"SECRET_KEY={existing_content.get('SECRET_KEY', 'optiboard-secret-key-change-in-production')}\n")

        f.write("\n# Cache Settings (en secondes)\n")
        f.write(f"CACHE_TTL={existing_content.get('CACHE_TTL', '300')}\n")
        f.write(f"CACHE_TTL_DASHBOARD={existing_content.get('CACHE_TTL_DASHBOARD', '300')}\n")
        f.write(f"CACHE_TTL_VENTES={existing_content.get('CACHE_TTL_VENTES', '600')}\n")
        f.write(f"CACHE_TTL_STOCKS={existing_content.get('CACHE_TTL_STOCKS', '300')}\n")
        f.write(f"CACHE_TTL_RECOUVREMENT={existing_content.get('CACHE_TTL_RECOUVREMENT', '600')}\n")

        f.write("\n# Query Settings\n")
        f.write(f"MAX_ROWS={existing_content.get('MAX_ROWS', '10000')}\n")
        f.write(f"QUERY_TIMEOUT={existing_content.get('QUERY_TIMEOUT', '30')}\n")

        f.write("\n# Session Settings\n")
        f.write(f"SESSION_EXPIRE_MINUTES={existing_content.get('SESSION_EXPIRE_MINUTES', '480')}\n")

    # Recharger les settings
    reload_central_settings()
    return True
