"""Routes WhatsApp Business — Webhook Meta + Admin config + Historique.

Endpoints :
  GET  /api/whatsapp/webhook     — Vérification webhook Meta (challenge)
  POST /api/whatsapp/webhook     — Réception messages entrants
  GET  /api/whatsapp/config      — Lire config WhatsApp courante
  POST /api/whatsapp/config      — Sauvegarder config WhatsApp dans .env
  POST /api/whatsapp/test        — Tester la connexion Meta Cloud API
  POST /api/whatsapp/send        — Envoi manuel (admin)
  GET  /api/whatsapp/history     — Historique des messages
  GET  /api/whatsapp/mappings    — Mapping numéro ↔ utilisateur OptiBoard
  POST /api/whatsapp/mappings    — Associer un numéro à un utilisateur + DWH
"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request, Response, BackgroundTasks
from pydantic import BaseModel

from app.config import get_settings, save_env_config, reload_settings
from app.database_unified import execute_central, write_central
from app.services.whatsapp_service import (
    send_text_message,
    test_whatsapp_connection,
    extract_messages,
    verify_webhook_signature,
    mark_as_read,
    process_bot_command,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])


# ─── Schemas ────────────────────────────────────────────────────────────────────

class WAConfigUpdate(BaseModel):
    provider: str = "360dialog"
    # 360dialog
    api_key_360dialog: str = ""
    # Meta direct
    phone_number_id: str = ""
    access_token: str = ""
    api_version: str = "v21.0"
    # commun
    verify_token: str = ""
    app_secret: str = ""
    bot_enabled: bool = False


class WASendRequest(BaseModel):
    to: str
    message: str


class WAMappingCreate(BaseModel):
    phone_number: str
    dwh_code: str
    user_id: Optional[int] = None
    label: str = ""


# ─── Init tables ────────────────────────────────────────────────────────────────

def init_whatsapp_tables():
    """Crée les tables WhatsApp dans la base centrale si elles n'existent pas."""
    write_central("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'WA_Messages')
        CREATE TABLE WA_Messages (
            id INT IDENTITY(1,1) PRIMARY KEY,
            direction VARCHAR(10) NOT NULL,
            phone_number VARCHAR(30) NOT NULL,
            contact_name NVARCHAR(200) NULL,
            message_id VARCHAR(200) NULL,
            message_type VARCHAR(30) DEFAULT 'text',
            body NVARCHAR(MAX) NULL,
            dwh_code VARCHAR(20) NULL,
            status VARCHAR(30) DEFAULT 'received',
            created_at DATETIME DEFAULT GETDATE()
        )
    """)
    write_central("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'WA_UserMappings')
        CREATE TABLE WA_UserMappings (
            id INT IDENTITY(1,1) PRIMARY KEY,
            phone_number VARCHAR(30) NOT NULL UNIQUE,
            dwh_code VARCHAR(20) NOT NULL,
            user_id INT NULL,
            label NVARCHAR(200) NULL,
            created_at DATETIME DEFAULT GETDATE()
        )
    """)


# ─── Webhook Meta (public, pas d'auth) ─────────────────────────────────────────

@router.get("/webhook")
async def webhook_verify(request: Request):
    """Vérification du webhook par Meta (challenge handshake)."""
    params = request.query_params
    mode = params.get("hub.mode", "")
    token = params.get("hub.verify_token", "")
    challenge = params.get("hub.challenge", "")

    s = get_settings()
    if mode == "subscribe" and token == s.WA_VERIFY_TOKEN and s.WA_VERIFY_TOKEN:
        logger.info("[WA] Webhook vérifié avec succès")
        return Response(content=challenge, media_type="text/plain")

    logger.warning(f"[WA] Webhook verification échouée — token={token}")
    return Response(content="Forbidden", status_code=403)


@router.post("/webhook")
async def webhook_receive(request: Request, background_tasks: BackgroundTasks):
    """Réception des messages entrants depuis Meta."""
    s = get_settings()
    if not s.WA_BOT_ENABLED:
        return {"status": "bot_disabled"}

    body_bytes = await request.body()

    if s.WA_APP_SECRET:
        sig = request.headers.get("X-Hub-Signature-256", "")
        if not verify_webhook_signature(body_bytes, sig, s.WA_APP_SECRET):
            logger.warning("[WA] Signature webhook invalide")
            return Response(content="Invalid signature", status_code=403)

    try:
        payload = await request.json()
    except Exception:
        return {"status": "invalid_json"}

    messages = extract_messages(payload)
    if messages:
        background_tasks.add_task(_handle_incoming_messages, messages, s)

    return {"status": "ok"}


async def _handle_incoming_messages(messages: list, settings):
    """Traite les messages entrants en arrière-plan."""
    for msg in messages:
        phone = msg["from"]
        text = msg.get("text", "")
        name = msg.get("name", "")
        msg_id = msg.get("message_id", "")

        try:
            write_central(
                "INSERT INTO WA_Messages (direction, phone_number, contact_name, message_id, message_type, body, dwh_code) "
                "VALUES ('in', ?, ?, ?, ?, ?, ?)",
                (phone, name, msg_id, msg.get("type", "text"), text, _get_dwh_for_phone(phone)),
            )
        except Exception as e:
            logger.error(f"[WA] Erreur log message: {e}")

        mark_as_read(settings.WA_PHONE_NUMBER_ID, settings.WA_ACCESS_TOKEN, msg_id, settings.WA_API_VERSION)

        dwh_code = _get_dwh_for_phone(phone)
        if not dwh_code:
            reply = (
                "Votre numéro n'est pas associé à un compte OptiBoard.\n"
                "Contactez votre administrateur pour activer le service."
            )
        else:
            reply = process_bot_command(text, dwh_code)

        result = send_text_message(
            settings.WA_PHONE_NUMBER_ID,
            settings.WA_ACCESS_TOKEN,
            phone,
            reply,
            settings.WA_API_VERSION,
        )

        try:
            write_central(
                "INSERT INTO WA_Messages (direction, phone_number, contact_name, message_id, message_type, body, dwh_code, status) "
                "VALUES ('out', ?, ?, ?, 'text', ?, ?, ?)",
                (phone, name, result.get("message_id", ""), reply, dwh_code, "sent" if result.get("success") else "failed"),
            )
        except Exception as e:
            logger.error(f"[WA] Erreur log réponse: {e}")


def _get_dwh_for_phone(phone: str) -> Optional[str]:
    """Cherche le dwh_code associé à un numéro de téléphone."""
    try:
        rows = execute_central(
            "SELECT dwh_code FROM WA_UserMappings WHERE phone_number = ?",
            (phone,),
            use_cache=True,
        )
        if rows:
            return rows[0]["dwh_code"]
    except Exception:
        pass
    return None


# ─── Config admin ───────────────────────────────────────────────────────────────

@router.get("/config")
async def get_wa_config():
    """Retourne la configuration WhatsApp courante (secrets masqués)."""
    s = get_settings()
    provider = getattr(s, "WA_PROVIDER", "360dialog")
    api_key = getattr(s, "WA_360DIALOG_API_KEY", "")
    return {
        "success": True,
        "data": {
            "provider": provider,
            # 360dialog
            "api_key_360dialog": "***" if api_key else "",
            # Meta
            "phone_number_id": s.WA_PHONE_NUMBER_ID,
            "access_token": "***" if s.WA_ACCESS_TOKEN else "",
            "api_version": s.WA_API_VERSION,
            # commun
            "verify_token": s.WA_VERIFY_TOKEN,
            "app_secret": "***" if s.WA_APP_SECRET else "",
            "bot_enabled": s.WA_BOT_ENABLED,
            "webhook_url": "/api/whatsapp/webhook",
        },
    }


@router.post("/config")
async def update_wa_config(data: WAConfigUpdate):
    """Sauvegarde la configuration WhatsApp dans .env."""
    try:
        env_updates = {
            "WA_PROVIDER": data.provider,
            "WA_PHONE_NUMBER_ID": data.phone_number_id,
            "WA_VERIFY_TOKEN": data.verify_token,
            "WA_API_VERSION": data.api_version,
            "WA_BOT_ENABLED": str(data.bot_enabled),
        }
        if data.api_key_360dialog and data.api_key_360dialog != "***":
            env_updates["WA_360DIALOG_API_KEY"] = data.api_key_360dialog
        if data.access_token and data.access_token != "***":
            env_updates["WA_ACCESS_TOKEN"] = data.access_token
        if data.app_secret and data.app_secret != "***":
            env_updates["WA_APP_SECRET"] = data.app_secret

        save_env_config(env_updates)
        reload_settings()
        return {"success": True, "message": "Configuration WhatsApp sauvegardée"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/test")
async def test_wa_connection():
    """Teste la connexion selon le provider configuré."""
    s = get_settings()
    provider = getattr(s, "WA_PROVIDER", "360dialog")

    if provider == "360dialog":
        api_key = getattr(s, "WA_360DIALOG_API_KEY", "")
        if not api_key:
            return {"success": False, "error": "Clé API 360dialog non configurée"}
        return _test_360dialog(api_key)

    # Meta direct
    if not s.WA_PHONE_NUMBER_ID or not s.WA_ACCESS_TOKEN:
        return {"success": False, "error": "Phone Number ID ou Access Token manquant"}
    return test_whatsapp_connection(s.WA_PHONE_NUMBER_ID, s.WA_ACCESS_TOKEN, s.WA_API_VERSION)


def _test_360dialog(api_key: str) -> dict:
    """Teste la clé API 360dialog en récupérant les infos du compte."""
    import urllib.request, urllib.error, json
    from app.config import get_settings as _gs
    _s = _gs()
    is_sandbox = getattr(_s, "WA_360DIALOG_SANDBOX", True)
    base = "https://waba-sandbox.360dialog.io" if is_sandbox else "https://waba-v2.360dialog.io"
    url = f"{base}/v1/configs/webhook"
    req = urllib.request.Request(url, headers={"D360-API-KEY": api_key, "Content-Type": "application/json"}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return {"success": True, "webhook_url": data.get("url", ""), "provider": "360dialog"}
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return {"success": False, "error": "Clé API invalide (401 Unauthorized)"}
        # 404 = pas encore de webhook configuré, mais la clé est valide
        if e.code == 404:
            return {"success": True, "webhook_url": "(non configuré)", "provider": "360dialog"}
        return {"success": False, "error": f"HTTP {e.code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── Test bot (dev) ─────────────────────────────────────────────────────────────

class WABotTestRequest(BaseModel):
    text: str
    dwh_code: str = "KA"


@router.post("/bot-test")
async def bot_test(data: WABotTestRequest):
    """Teste la logique du bot sans envoyer de message WhatsApp (dev/admin)."""
    try:
        reply = process_bot_command(data.text, data.dwh_code)
        return {"success": True, "input": data.text, "dwh_code": data.dwh_code, "reply": reply}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/discover-tables")
async def discover_tables(dwh_code: str = "KA"):
    """Découverte des tables disponibles dans un DWH (dev/admin)."""
    from app.database_unified import execute_dwh
    try:
        rows = execute_dwh(
            """
            SELECT TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_TYPE IN ('BASE TABLE', 'VIEW')
            ORDER BY TABLE_NAME
            """,
            dwh_code=dwh_code, use_cache=False,
        )
        tables = [r["TABLE_NAME"] for r in rows] if rows else []
        # Filtrer celles qui pourraient être liées aux impayés
        keywords = ["echeance", "Echeance", "impaye", "Impaye", "reglement", "Reglement",
                    "balance", "Balance", "creance", "Creance", "client", "vente"]
        related = [t for t in tables if any(k.lower() in t.lower() for k in keywords)]
        return {"success": True, "dwh_code": dwh_code, "total": len(tables),
                "all_tables": tables, "related_to_impayes": related}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/discover-columns")
async def discover_columns(dwh_code: str = "KA", table: str = ""):
    """Retourne les colonnes d'une table DWH (dev/admin)."""
    from app.database_unified import execute_dwh
    if not table:
        return {"success": False, "error": "Paramètre 'table' requis"}
    try:
        rows = execute_dwh(
            "SELECT TOP 3 * FROM [dbo].[" + table + "]",
            dwh_code=dwh_code, use_cache=False,
        )
        cols = list(rows[0].keys()) if rows else []
        return {"success": True, "table": table, "columns": cols, "sample_row": rows[0] if rows else {}}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── Envoi manuel (admin) ──────────────────────────────────────────────────────

@router.post("/send")
async def send_manual(data: WASendRequest):
    """Envoie un message manuellement (admin)."""
    s = get_settings()
    if not s.WA_PHONE_NUMBER_ID or not s.WA_ACCESS_TOKEN:
        return {"success": False, "error": "WhatsApp non configuré"}
    result = send_text_message(
        s.WA_PHONE_NUMBER_ID, s.WA_ACCESS_TOKEN, data.to, data.message, s.WA_API_VERSION
    )
    if result.get("success"):
        try:
            write_central(
                "INSERT INTO WA_Messages (direction, phone_number, message_id, body, status) "
                "VALUES ('out', ?, ?, ?, 'sent')",
                (data.to, result.get("message_id", ""), data.message),
            )
        except Exception:
            pass
    return result


# ─── Historique ─────────────────────────────────────────────────────────────────

@router.get("/history")
async def get_history(limit: int = 50, phone: Optional[str] = None):
    """Retourne l'historique des messages WhatsApp."""
    try:
        if phone:
            rows = execute_central(
                f"SELECT TOP {min(limit, 500)} * FROM WA_Messages WHERE phone_number = ? ORDER BY created_at DESC",
                (phone,),
                use_cache=False,
            )
        else:
            rows = execute_central(
                f"SELECT TOP {min(limit, 500)} * FROM WA_Messages ORDER BY created_at DESC",
                use_cache=False,
            )
        return {"success": True, "data": rows, "count": len(rows)}
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}


# ─── Mappings numéro ↔ utilisateur ──────────────────────────────────────────────

@router.get("/mappings")
async def get_mappings():
    """Liste les mappings numéro ↔ DWH."""
    try:
        rows = execute_central(
            "SELECT * FROM WA_UserMappings ORDER BY created_at DESC",
            use_cache=False,
        )
        return {"success": True, "data": rows}
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}


@router.post("/mappings")
async def create_mapping(data: WAMappingCreate):
    """Associe un numéro WhatsApp à un DWH client."""
    try:
        write_central(
            """
            IF EXISTS (SELECT 1 FROM WA_UserMappings WHERE phone_number = ?)
                UPDATE WA_UserMappings SET dwh_code = ?, user_id = ?, label = ? WHERE phone_number = ?
            ELSE
                INSERT INTO WA_UserMappings (phone_number, dwh_code, user_id, label)
                VALUES (?, ?, ?, ?)
            """,
            (data.phone_number, data.dwh_code, data.user_id, data.label, data.phone_number,
             data.phone_number, data.dwh_code, data.user_id, data.label),
        )
        return {"success": True, "message": f"Numéro {data.phone_number} associé à {data.dwh_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.delete("/mappings/{phone_number}")
async def delete_mapping(phone_number: str):
    """Supprime un mapping numéro ↔ DWH."""
    try:
        write_central(
            "DELETE FROM WA_UserMappings WHERE phone_number = ?",
            (phone_number,),
        )
        return {"success": True, "message": f"Mapping {phone_number} supprimé"}
    except Exception as e:
        return {"success": False, "error": str(e)}
