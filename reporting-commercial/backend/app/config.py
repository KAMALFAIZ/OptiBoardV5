from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path
import os

# Chemin absolu vers le fichier .env
ENV_FILE_PATH = Path(__file__).parent.parent / ".env"


class Settings(BaseSettings):
    # Database settings - valeurs par defaut vides pour forcer la configuration
    DB_SERVER: str = ""
    DB_NAME: str = ""
    DB_USER: str = ""
    DB_PASSWORD: str = ""
    DB_DRIVER: str = "{ODBC Driver 17 for SQL Server}"

    # Central Database (Multi-tenant) - optionnel
    CENTRAL_DB_SERVER: str = ""
    CENTRAL_DB_NAME: str = ""
    CENTRAL_DB_USER: str = ""
    CENTRAL_DB_PASSWORD: str = ""

    # Mode client autonome (standalone)
    STANDALONE_MODE: bool = False
    DWH_CODE: str = ""           # Code client injecté automatiquement en mode standalone

    # Application settings
    APP_NAME: str = "OptiBoard - Reporting Commercial"
    DEBUG: bool = True

    # Cache settings
    CACHE_TTL: int = 300  # 5 minutes

    # Query settings
    MAX_ROWS: int = 10000
    QUERY_TIMEOUT: int = 30

    # License settings
    LICENSE_KEY: str = ""
    LICENSE_SERVER_URL: str = "http://kasoft.selfip.net:44100/api"
    LICENSE_CHECK_INTERVAL: int = 86400  # 24h en secondes
    LICENSE_GRACE_DAYS: int = 7  # Jours de grace si serveur injoignable
    LICENSE_SIGNING_SECRET: str = "optiboard-license-secret-clé-2025-kasoft"  # Overridable via .env

    # Master Catalog (sync depuis serveur central distant)
    # Si MASTER_API_URL est configuré, le bouton "Récupérer base maître"
    # tire les menus/dashboards/gridviews/pivots depuis cette URL distante
    # au lieu de la base centrale locale.
    # Si MASTER_API_KEY est configuré sur le serveur central, il expose
    # /api/master/* (sinon ces routes renvoient 503).
    MASTER_API_URL: str = ""        # ex: "https://central.kasoft.ma" (sans /api final)
    MASTER_API_KEY: str = ""        # clé API partagée serveur central <-> clients
    MASTER_TIMEOUT: int = 30        # timeout HTTP en secondes

    # AI Module settings
    AI_PROVIDER: str = ""  # "openai" | "anthropic" | "ollama"
    AI_MODEL: str = ""
    AI_API_KEY: str = ""
    AI_OLLAMA_URL: str = "http://localhost:11434"
    AI_MAX_TOKENS: int = 4096
    AI_TEMPERATURE: float = 0.2
    AI_ENABLED: bool = False
    AI_RATE_LIMIT_PER_MINUTE: int = 20
    AI_HISTORY_MAX_MESSAGES: int = 50
    AI_SQL_MAX_ROWS: int = 500

    @property
    def database_url(self) -> str:
        return (
            f"DRIVER={self.DB_DRIVER};"
            f"SERVER={self.DB_SERVER};"
            f"DATABASE={self.DB_NAME};"
            f"UID={self.DB_USER};"
            f"PWD={self.DB_PASSWORD};"
            f"TrustServerCertificate=yes"
        )

    @property
    def is_configured(self) -> bool:
        """Verifie si la base de donnees est configuree"""
        return bool(self.DB_SERVER and self.DB_NAME and self.DB_USER and self.DB_PASSWORD)

    @property
    def is_standalone(self) -> bool:
        """Retourne True si le mode client autonome est activé"""
        return self.STANDALONE_MODE

    @property
    def is_licensed(self) -> bool:
        """Verifie si une cle de licence est configuree (toujours True en standalone sans URL)"""
        if self.STANDALONE_MODE and not self.LICENSE_SERVER_URL:
            return True
        return bool(self.LICENSE_KEY)

    class Config:
        env_file = str(ENV_FILE_PATH)
        env_file_encoding = 'utf-8'
        extra = 'ignore'  # Ignorer les variables non definies


# Cache global pour les settings (permet de recharger apres configuration)
_settings_cache = None


def get_settings() -> Settings:
    """Retourne les settings, recharge si necessaire"""
    global _settings_cache
    if _settings_cache is None:
        _settings_cache = Settings()
    return _settings_cache


def reload_settings() -> Settings:
    """Force le rechargement des settings depuis le fichier .env"""
    global _settings_cache
    _settings_cache = Settings()
    return _settings_cache


def get_env_file_path() -> Path:
    """Retourne le chemin du fichier .env"""
    return ENV_FILE_PATH


def save_env_config(config: dict) -> bool:
    """Sauvegarde la configuration dans le fichier .env"""
    env_path = get_env_file_path()

    print(f"[CONFIG] Saving to: {env_path}")
    print(f"[CONFIG] Config to save: {config}")

    # Lire le fichier existant ou creer un nouveau contenu
    existing_content = {}
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    existing_content[key.strip()] = value.strip()

    # Mettre a jour avec les nouvelles valeurs
    existing_content.update(config)

    print(f"[CONFIG] Merged content: {existing_content}")

    # Ecrire le fichier
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write("# Database Configuration\n")
        f.write(f"DB_SERVER={existing_content.get('DB_SERVER', '')}\n")
        f.write(f"DB_NAME={existing_content.get('DB_NAME', '')}\n")
        f.write(f"DB_USER={existing_content.get('DB_USER', '')}\n")
        f.write(f"DB_PASSWORD={existing_content.get('DB_PASSWORD', '')}\n")
        f.write(f"DB_DRIVER={existing_content.get('DB_DRIVER', '{ODBC Driver 17 for SQL Server}')}\n")
        f.write("\n# Application Settings\n")
        f.write(f"DEBUG={existing_content.get('DEBUG', 'True')}\n")
        f.write(f"APP_NAME={existing_content.get('APP_NAME', 'OptiBoard - Reporting Commercial')}\n")
        f.write("\n# Cache Settings\n")
        f.write(f"CACHE_TTL={existing_content.get('CACHE_TTL', '300')}\n")
        f.write("\n# Query Settings\n")
        f.write(f"MAX_ROWS={existing_content.get('MAX_ROWS', '10000')}\n")
        f.write(f"QUERY_TIMEOUT={existing_content.get('QUERY_TIMEOUT', '30')}\n")
        f.write("\n# License Settings\n")
        f.write(f"LICENSE_KEY={existing_content.get('LICENSE_KEY', '')}\n")
        f.write(f"LICENSE_SERVER_URL={existing_content.get('LICENSE_SERVER_URL', 'http://kasoft.selfip.net:44100/api')}\n")
        f.write("\n# Master Catalog Settings\n")
        f.write(f"MASTER_API_URL={existing_content.get('MASTER_API_URL', '')}\n")
        f.write(f"MASTER_API_KEY={existing_content.get('MASTER_API_KEY', '')}\n")
        f.write(f"MASTER_TIMEOUT={existing_content.get('MASTER_TIMEOUT', '30')}\n")
        f.write("\n# AI Module Settings\n")
        f.write(f"AI_PROVIDER={existing_content.get('AI_PROVIDER', '')}\n")
        f.write(f"AI_MODEL={existing_content.get('AI_MODEL', '')}\n")
        f.write(f"AI_API_KEY={existing_content.get('AI_API_KEY', '')}\n")
        f.write(f"AI_OLLAMA_URL={existing_content.get('AI_OLLAMA_URL', 'http://localhost:11434')}\n")
        f.write(f"AI_MAX_TOKENS={existing_content.get('AI_MAX_TOKENS', '4096')}\n")
        f.write(f"AI_TEMPERATURE={existing_content.get('AI_TEMPERATURE', '0.2')}\n")
        f.write(f"AI_ENABLED={existing_content.get('AI_ENABLED', 'False')}\n")
        f.write(f"AI_RATE_LIMIT_PER_MINUTE={existing_content.get('AI_RATE_LIMIT_PER_MINUTE', '20')}\n")
        f.write(f"AI_HISTORY_MAX_MESSAGES={existing_content.get('AI_HISTORY_MAX_MESSAGES', '50')}\n")
        f.write(f"AI_SQL_MAX_ROWS={existing_content.get('AI_SQL_MAX_ROWS', '500')}\n")

    print(f"[CONFIG] File written successfully")

    # Recharger les settings
    new_settings = reload_settings()
    print(f"[CONFIG] Reloaded settings - DB_SERVER: {new_settings.DB_SERVER}, DB_NAME: {new_settings.DB_NAME}")

    return True
