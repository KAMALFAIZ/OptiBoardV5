"""Configuration KAsoft Hub via .env"""
import os
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv(override=True)


class Settings:
    # Database
    DB_SERVER: str = os.getenv("HUB_DB_SERVER", ".")
    DB_NAME: str = os.getenv("HUB_DB_NAME", "KAsoft_Hub")
    DB_USER: str = os.getenv("HUB_DB_USER", "sa")
    DB_PASSWORD: str = os.getenv("HUB_DB_PASSWORD", "")
    DB_DRIVER: str = os.getenv("HUB_DB_DRIVER", "{ODBC Driver 17 for SQL Server}")

    # App
    APP_NAME: str = os.getenv("HUB_APP_NAME", "KAsoft Automation Hub")
    DEBUG: bool = os.getenv("HUB_DEBUG", "true").lower() == "true"
    PORT: int = int(os.getenv("HUB_PORT", "8085"))
    SECRET_KEY: str = os.getenv("HUB_SECRET_KEY", "kasoft-hub-secret-change-me")

    # Telegram
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

    # WhatsApp (Twilio)
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_WHATSAPP_FROM: str = os.getenv("TWILIO_WHATSAPP_FROM", "")

    # Email (SMTP)
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "KAsoft Hub")
    SMTP_USE_SSL: bool = os.getenv("SMTP_USE_SSL", "false").lower() == "true"
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

    @property
    def is_configured(self) -> bool:
        return bool(self.DB_SERVER and self.DB_NAME and self.DB_USER and self.DB_PASSWORD)

    @property
    def connection_string(self) -> str:
        return (
            f"DRIVER={self.DB_DRIVER};"
            f"SERVER={self.DB_SERVER};"
            f"DATABASE={self.DB_NAME};"
            f"UID={self.DB_USER};"
            f"PWD={self.DB_PASSWORD};"
            "TrustServerCertificate=yes;"
            "Connect Timeout=30;"
        )


_settings = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    global _settings
    load_dotenv(override=True)
    _settings = Settings()
    return _settings
