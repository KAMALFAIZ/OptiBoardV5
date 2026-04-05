"""Configuration et test des canaux de communication."""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from ..database import execute, write
from ..services.telegram_service import test_telegram_connection, send_telegram_message
from ..services.whatsapp_service import test_whatsapp_connection, send_whatsapp_message
from ..services.email_service import test_email_config, send_email

router = APIRouter(prefix="/api/channels", tags=["channels"])


class ChannelConfig(BaseModel):
    telegram_bot_token: Optional[str] = None
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_whatsapp_from: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_name: Optional[str] = None
    smtp_use_ssl: Optional[bool] = None
    smtp_use_tls: Optional[bool] = None


class ChannelTestRequest(BaseModel):
    channel: str
    contact_info: str
    message: Optional[str] = "✅ Test KAsoft Hub — configuration OK"


def _mask(val: str) -> str:
    if not val or len(val) < 6:
        return "***"
    return val[:3] + "***" + val[-3:]


@router.get("/config")
async def get_channel_config():
    rows = execute("SELECT * FROM HUB_ChannelConfig WHERE id=1")
    if not rows:
        return {"success": True, "data": {}}
    cfg = rows[0]
    return {
        "success": True,
        "data": {
            "telegram_configured": bool(cfg.get("telegram_bot_token")),
            "telegram_bot_token": _mask(cfg.get("telegram_bot_token") or ""),
            "whatsapp_configured": bool(cfg.get("twilio_account_sid")),
            "twilio_account_sid": cfg.get("twilio_account_sid", ""),
            "twilio_auth_token": _mask(cfg.get("twilio_auth_token") or ""),
            "twilio_whatsapp_from": cfg.get("twilio_whatsapp_from", ""),
            "email_configured": bool(cfg.get("smtp_host")),
            "smtp_host": cfg.get("smtp_host", ""),
            "smtp_port": cfg.get("smtp_port", 587),
            "smtp_user": cfg.get("smtp_user", ""),
            "smtp_from_name": cfg.get("smtp_from_name", ""),
        },
    }


@router.put("/config")
async def update_channel_config(body: ChannelConfig):
    updates = {}
    fields = [
        "telegram_bot_token", "twilio_account_sid", "twilio_auth_token",
        "twilio_whatsapp_from", "smtp_host", "smtp_port", "smtp_user",
        "smtp_password", "smtp_from_name", "smtp_use_ssl", "smtp_use_tls",
    ]
    for f in fields:
        val = getattr(body, f)
        if val is not None:
            updates[f] = val
    if updates:
        set_clause = ", ".join(f"{k}=?" for k in updates)
        write(
            f"UPDATE HUB_ChannelConfig SET {set_clause}, updated_at=GETDATE() WHERE id=1",
            tuple(updates.values()),
        )
    return {"success": True, "message": "Configuration sauvegardée"}


@router.post("/test")
async def test_channel(body: ChannelTestRequest):
    rows = execute("SELECT * FROM HUB_ChannelConfig WHERE id=1")
    cfg = rows[0] if rows else {}

    if body.channel == "telegram":
        token = cfg.get("telegram_bot_token", "")
        if not token:
            return {"success": False, "error": "Token Telegram non configuré"}
        ok = send_telegram_message(token, body.contact_info, body.message)
        return {"success": ok, "error": None if ok else "Échec — vérifiez le token et le chat_id"}

    elif body.channel == "whatsapp":
        sid = cfg.get("twilio_account_sid", "")
        tok = cfg.get("twilio_auth_token", "")
        frm = cfg.get("twilio_whatsapp_from", "")
        if not all([sid, tok, frm]):
            return {"success": False, "error": "Configuration Twilio incomplète"}
        ok = send_whatsapp_message(sid, tok, frm, body.contact_info, body.message)
        return {"success": ok, "error": None if ok else "Échec — vérifiez les credentials Twilio"}

    elif body.channel == "email":
        res = send_email([body.contact_info], "Test KAsoft Hub", f"<p>{body.message}</p>")
        return res

    return {"success": False, "error": f"Canal inconnu: {body.channel}"}


@router.post("/verify")
async def verify_credentials(body: ChannelConfig):
    """Vérifie les credentials sans les sauvegarder."""
    result = {}
    if body.telegram_bot_token:
        result["telegram"] = test_telegram_connection(body.telegram_bot_token)
    if body.twilio_account_sid and body.twilio_auth_token:
        result["whatsapp"] = test_whatsapp_connection(body.twilio_account_sid, body.twilio_auth_token)
    if body.smtp_host and body.smtp_user and body.smtp_password:
        result["email"] = test_email_config({
            "smtp_host": body.smtp_host,
            "smtp_port": body.smtp_port or 587,
            "smtp_user": body.smtp_user,
            "smtp_password": body.smtp_password,
            "smtp_use_ssl": body.smtp_use_ssl,
            "smtp_use_tls": body.smtp_use_tls,
        })
    return {"success": True, "data": result}
