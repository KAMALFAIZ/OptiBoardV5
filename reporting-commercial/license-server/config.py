"""Configuration du serveur de licences"""
from pydantic_settings import BaseSettings
from pathlib import Path

ENV_FILE_PATH = Path(__file__).parent / ".env"


class Settings(BaseSettings):
    # Base de donnees du serveur de licences
    DB_SERVER: str = "localhost"
    DB_NAME: str = "OptiBoard_Licenses"
    DB_USER: str = "sa"
    DB_PASSWORD: str = ""
    DB_DRIVER: str = "{ODBC Driver 17 for SQL Server}"

    # Cle secrete pour signer les licences (GARDEZ-LA SECRETE!)
    LICENSE_SIGNING_SECRET: str = "CHANGEZ-MOI-en-production-clé-très-longue-et-complexe"

    # Cle API pour proteger le panneau d'administration
    ADMIN_API_KEY: str = "CHANGEZ-MOI-admin-api-key"

    # Application
    APP_NAME: str = "OptiBoard License Server"
    DEBUG: bool = False
    PORT: int = 44100

    class Config:
        env_file = str(ENV_FILE_PATH)
        env_file_encoding = 'utf-8'
        extra = 'ignore'


_settings = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
