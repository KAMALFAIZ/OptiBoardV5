"""
Gestion de la configuration .env via l'interface d'administration.
Permet de lire et modifier les variables d'environnement sans accès SSH.
"""
import re
import os
import logging
import pyodbc
import urllib.request
import json
from pathlib import Path
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/env", tags=["env-manager"])

ENV_PATH = Path(__file__).parent.parent.parent / ".env"

# ─── Variables sensibles : valeur masquée en lecture ─────────────────────────
SENSITIVE_KEYS = {
    "DB_PASSWORD", "LICENSE_KEY", "LICENSE_SIGNING_SECRET",
    "AI_API_KEY", "ADMIN_API_KEY", "SMTP_PASSWORD"
}

# ─── Définition des sections et champs ───────────────────────────────────────
ENV_SCHEMA = [
    {
        "id": "database",
        "label": "Base de données centrale",
        "icon": "database",
        "fields": [
            {"key": "DB_SERVER",   "label": "Serveur SQL",       "type": "text",     "placeholder": "localhost ou IP"},
            {"key": "DB_NAME",     "label": "Nom de la base",     "type": "text",     "placeholder": "OptiBoard_SaaS"},
            {"key": "DB_USER",     "label": "Utilisateur",        "type": "text",     "placeholder": "sa"},
            {"key": "DB_PASSWORD", "label": "Mot de passe",       "type": "password", "placeholder": ""},
            {"key": "DB_DRIVER",   "label": "Driver ODBC",        "type": "select",
             "options": ["{ODBC Driver 17 for SQL Server}", "{ODBC Driver 18 for SQL Server}", "{SQL Server}"]},
        ]
    },
    {
        "id": "license",
        "label": "Licence",
        "icon": "key",
        "fields": [
            {"key": "LICENSE_KEY",            "label": "Clé de licence",             "type": "password", "placeholder": "eyJ..."},
            {"key": "LICENSE_SERVER_URL",      "label": "URL serveur de licences",    "type": "text",     "placeholder": "http://localhost:44100/api"},
            {"key": "LICENSE_SIGNING_SECRET",  "label": "Secret de signature HMAC",   "type": "password", "placeholder": "OptiBoard-..."},
        ]
    },
    {
        "id": "ai",
        "label": "Module IA",
        "icon": "bot",
        "fields": [
            {"key": "AI_ENABLED",               "label": "IA activée",              "type": "boolean"},
            {"key": "AI_PROVIDER",              "label": "Fournisseur",              "type": "select",
             "options": ["anthropic", "ollama", "openai"]},
            {"key": "AI_MODEL",                 "label": "Modèle",                   "type": "text",    "placeholder": "claude-sonnet-4-5..."},
            {"key": "AI_API_KEY",               "label": "Clé API",                  "type": "password","placeholder": "sk-ant-..."},
            {"key": "AI_OLLAMA_URL",            "label": "URL Ollama",               "type": "text",    "placeholder": "http://localhost:11434"},
            {"key": "AI_MAX_TOKENS",            "label": "Tokens max",               "type": "number",  "min": 256,   "max": 32000},
            {"key": "AI_TEMPERATURE",           "label": "Température",              "type": "number",  "min": 0,     "max": 2,    "step": 0.1},
            {"key": "AI_SQL_MAX_ROWS",          "label": "Lignes max SQL",           "type": "number",  "min": 10,    "max": 10000},
            {"key": "AI_RATE_LIMIT_PER_MINUTE", "label": "Limite req/min",           "type": "number",  "min": 1,     "max": 100},
            {"key": "AI_HISTORY_MAX_MESSAGES",  "label": "Historique max (messages)","type": "number",  "min": 5,     "max": 200},
        ]
    },
    {
        "id": "smtp",
        "label": "Email (SMTP)",
        "icon": "mail",
        "fields": [
            {"key": "SMTP_HOST",      "label": "Serveur SMTP",         "type": "text",     "placeholder": "smtp.gmail.com"},
            {"key": "SMTP_PORT",      "label": "Port",                  "type": "number",   "min": 1, "max": 65535, "placeholder": "587"},
            {"key": "SMTP_USER",      "label": "Adresse email",         "type": "text",     "placeholder": "contact@societe.ma"},
            {"key": "SMTP_PASSWORD",  "label": "Mot de passe / App Password", "type": "password", "placeholder": ""},
            {"key": "SMTP_FROM_NAME", "label": "Nom de l'expéditeur",   "type": "text",     "placeholder": "OptiBoard"},
            {"key": "SMTP_USE_TLS",   "label": "Utiliser TLS (port 587)","type": "boolean"},
            {"key": "SMTP_USE_SSL",   "label": "Utiliser SSL (port 465)","type": "boolean"},
        ]
    },
    {
        "id": "app",
        "label": "Application",
        "icon": "settings",
        "fields": [
            {"key": "APP_NAME",      "label": "Nom de l'application", "type": "text",    "placeholder": "OptiBoard"},
            {"key": "APP_URL",       "label": "URL publique du serveur (API)", "type": "text", "placeholder": "http://localhost:8084"},
            {"key": "FRONTEND_URL",  "label": "URL publique du frontend", "type": "text", "placeholder": "http://localhost:3003"},
            {"key": "DEBUG",         "label": "Mode debug",           "type": "boolean"},
            {"key": "CACHE_TTL",     "label": "Cache TTL (secondes)", "type": "number",  "min": 0, "max": 3600},
            {"key": "MAX_ROWS",      "label": "Lignes max (requêtes)","type": "number",  "min": 100, "max": 100000},
            {"key": "QUERY_TIMEOUT", "label": "Timeout SQL (secondes)","type": "number", "min": 5,   "max": 300},
        ]
    },
]


# ─── Helpers ─────────────────────────────────────────────────────────────────
def _read_env() -> Dict[str, str]:
    """Lit le fichier .env et retourne un dict key->value."""
    result = {}
    if not ENV_PATH.exists():
        return result
    with open(ENV_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, val = line.partition("=")
                result[key.strip()] = val.strip()
    return result


def _write_env_key(key: str, value: str):
    """Met à jour ou ajoute une clé dans le fichier .env."""
    if not ENV_PATH.exists():
        raise HTTPException(status_code=404, detail=".env introuvable")

    with open(ENV_PATH, encoding="utf-8") as f:
        content = f.read()

    pattern = rf"^({re.escape(key)}\s*=).*$"
    new_line = f"{key}={value}"

    if re.search(pattern, content, flags=re.MULTILINE):
        content = re.sub(pattern, new_line, content, flags=re.MULTILINE)
    else:
        # Ajouter à la fin
        content = content.rstrip("\n") + f"\n{new_line}\n"

    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.write(content)


def _mask(key: str, value: str) -> str:
    """Masque la valeur si la clé est sensible."""
    if key not in SENSITIVE_KEYS or not value:
        return value
    visible = min(6, len(value) // 4)
    return value[:visible] + "•" * 12


# ─── Routes ──────────────────────────────────────────────────────────────────
@router.get("/schema")
async def get_schema():
    """Retourne le schéma des sections/champs."""
    return {"success": True, "schema": ENV_SCHEMA}


@router.get("/config")
async def get_config():
    """Retourne les valeurs courantes du .env (sensibles masquées)."""
    raw = _read_env()
    masked = {k: _mask(k, v) for k, v in raw.items()}
    # Indiquer quelles clés sont sensibles
    sensitive_set = {k for k in raw if k in SENSITIVE_KEYS and raw[k]}
    return {
        "success": True,
        "values": masked,
        "sensitive_keys": list(sensitive_set),
    }


class UpdateEnvRequest(BaseModel):
    updates: Dict[str, Any]  # {KEY: new_value}


@router.put("/config")
async def update_config(req: UpdateEnvRequest):
    """Met à jour une ou plusieurs valeurs dans le .env."""
    if not req.updates:
        raise HTTPException(status_code=400, detail="Aucune mise à jour fournie")

    updated = []
    for key, value in req.updates.items():
        # Ignorer les valeurs masquées (inchangées)
        if isinstance(value, str) and "•" in value:
            continue
        _write_env_key(key, str(value))
        updated.append(key)

    logger.info(f"[ENV] Clés mises à jour: {updated}")
    return {
        "success": True,
        "updated": updated,
        "message": f"{len(updated)} variable(s) mise(s) à jour. Redémarrer le backend pour appliquer.",
        "restart_required": True,
    }


class TestDBRequest(BaseModel):
    server: str
    database: str
    username: str
    password: str
    driver: str = "{ODBC Driver 17 for SQL Server}"


@router.post("/test-db")
async def test_db_connection(req: TestDBRequest):
    """Teste une connexion SQL Server avec les paramètres fournis."""
    # Si le mot de passe est masqué (contient ●), utiliser la valeur réelle du .env
    password = req.password
    if "•" in password:
        password = _read_env().get("DB_PASSWORD", "")

    conn_str = (
        f"DRIVER={req.driver};"
        f"SERVER={req.server};"
        f"DATABASE={req.database};"
        f"UID={req.username};"
        f"PWD={password};"
        f"TrustServerCertificate=yes;"
        f"Connect Timeout=10"
    )
    try:
        conn = pyodbc.connect(conn_str, timeout=10)
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION")
        version = cursor.fetchone()[0].split("\n")[0].strip()
        conn.close()
        return {"success": True, "message": "Connexion réussie", "version": version}
    except pyodbc.Error as e:
        return {"success": False, "message": str(e)}


class TestLicenseServerRequest(BaseModel):
    url: str


@router.post("/test-license-server")
async def test_license_server(req: TestLicenseServerRequest):
    """Teste la connectivité avec le serveur de licences."""
    try:
        health_url = req.url.rstrip("/api").rstrip("/") + "/api/health"
        r = urllib.request.urlopen(health_url, timeout=8)
        data = json.loads(r.read())
        if data.get("status") == "healthy":
            return {"success": True, "message": "Serveur de licences joignable", "db": data.get("database")}
        return {"success": False, "message": f"Statut inattendu: {data}"}
    except Exception as e:
        return {"success": False, "message": f"Injoignable: {e}"}


class TestSMTPRequest(BaseModel):
    test_to: str = ""


@router.post("/test-smtp")
async def test_smtp(req: TestSMTPRequest):
    """Teste l'envoi SMTP en lisant les credentials depuis .env (evite le masquage frontend)."""
    import smtplib
    import ssl as ssl_lib
    from email.message import EmailMessage

    # Lire les credentials directement depuis .env — jamais depuis le frontend
    env = _read_env()
    smtp_host     = env.get("SMTP_HOST", "")
    smtp_port     = int(env.get("SMTP_PORT", "587"))
    smtp_user     = env.get("SMTP_USER", "")
    smtp_password = env.get("SMTP_PASSWORD", "")
    use_ssl       = env.get("SMTP_USE_SSL", "false").lower() == "true"
    use_tls       = env.get("SMTP_USE_TLS", "true").lower() == "true"

    if not smtp_host or not smtp_user or not smtp_password:
        return {"success": False, "message": "Configuration SMTP incomplete dans .env"}

    dest = req.test_to.strip() or smtp_user

    try:
        msg = EmailMessage()
        msg['From']    = smtp_user
        msg['To']      = dest
        msg['Subject'] = "Test SMTP - OptiBoard"
        msg.set_content(f"Test SMTP OK.\nServeur : {smtp_host}:{smtp_port}")

        if smtp_port == 465 or use_ssl:
            ctx = ssl_lib.create_default_context()
            with smtplib.SMTP_SSL(smtp_host, smtp_port, context=ctx) as server:
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                if use_tls or smtp_port == 587:
                    ctx = ssl_lib.create_default_context()
                    server.starttls(context=ctx)
                server.login(smtp_user, smtp_password)
                server.send_message(msg)

        return {"success": True, "message": f"Email envoye a {dest}"}

    except smtplib.SMTPAuthenticationError:
        return {"success": False, "message": "Authentification echouee. Verifiez App Password Gmail."}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.post("/restart")
async def restart_backend():
    """Déclenche un redémarrage du backend (uvicorn reload)."""
    import threading

    def _restart():
        import time, signal
        time.sleep(0.5)
        os.kill(os.getpid(), signal.SIGTERM)

    threading.Thread(target=_restart, daemon=True).start()
    return {"success": True, "message": "Redémarrage en cours..."}
