"""Service d'envoi de notifications Telegram via Bot API."""
import logging
import urllib.request
import urllib.parse
import json
from typing import Optional

logger = logging.getLogger(__name__)


def send_telegram_message(
    bot_token: str,
    chat_id: str,
    text: str,
    parse_mode: str = "Markdown",
) -> bool:
    """Envoie un message texte via Telegram Bot API."""
    if not bot_token or not chat_id:
        logger.warning("Telegram: bot_token ou chat_id manquant")
        return False
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = json.dumps({
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode())
            if result.get("ok"):
                logger.info(f"Telegram: message envoyé à chat_id={chat_id}")
                return True
            logger.error(f"Telegram API error: {result.get('description')}")
            return False
    except Exception as e:
        logger.error(f"Telegram send error: {e}")
        return False


def send_telegram_document(
    bot_token: str,
    chat_id: str,
    file_bytes: bytes,
    filename: str,
    caption: str = "",
) -> bool:
    """Envoie un fichier (document) via Telegram Bot API."""
    if not bot_token or not chat_id or not file_bytes:
        return False
    try:
        boundary = "----KAsoftHub"
        url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
        body_parts = []
        body_parts.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{chat_id}"
        )
        if caption:
            body_parts.append(
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"caption\"\r\n\r\n{caption}"
            )
        body_parts.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"document\"; filename=\"{filename}\"\r\n"
            f"Content-Type: application/octet-stream\r\n\r\n"
        )
        body_start = ("\r\n".join(body_parts)).encode("utf-8")
        body_end = f"\r\n--{boundary}--\r\n".encode("utf-8")
        body = body_start + file_bytes + body_end
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            return result.get("ok", False)
    except Exception as e:
        logger.error(f"Telegram document send error: {e}")
        return False


def test_telegram_connection(bot_token: str) -> dict:
    """Teste la connexion au bot Telegram."""
    try:
        url = f"https://api.telegram.org/bot{bot_token}/getMe"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=8) as resp:
            result = json.loads(resp.read().decode())
            if result.get("ok"):
                bot = result["result"]
                return {
                    "success": True,
                    "bot_name": bot.get("first_name"),
                    "username": bot.get("username"),
                }
            return {"success": False, "error": result.get("description", "Erreur inconnue")}
    except Exception as e:
        return {"success": False, "error": str(e)}
