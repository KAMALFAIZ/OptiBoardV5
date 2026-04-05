"""Service d'envoi de notifications WhatsApp via Twilio API."""
import logging
import urllib.request
import urllib.parse
import base64
import json
from typing import Optional

logger = logging.getLogger(__name__)


def _twilio_request(account_sid: str, auth_token: str, url: str, data: dict) -> dict:
    """Effectue une requête POST authentifiée vers l'API Twilio."""
    credentials = base64.b64encode(f"{account_sid}:{auth_token}".encode()).decode()
    payload = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def send_whatsapp_message(
    account_sid: str,
    auth_token: str,
    from_number: str,
    to_number: str,
    body: str,
) -> bool:
    """Envoie un message WhatsApp texte via Twilio."""
    if not all([account_sid, auth_token, from_number, to_number]):
        logger.warning("WhatsApp: configuration Twilio incomplète")
        return False
    try:
        frm = from_number if from_number.startswith("whatsapp:") else f"whatsapp:{from_number}"
        to  = to_number   if to_number.startswith("whatsapp:")  else f"whatsapp:{to_number}"
        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
        result = _twilio_request(account_sid, auth_token, url, {
            "From": frm,
            "To":   to,
            "Body": body,
        })
        sid = result.get("sid")
        if sid:
            logger.info(f"WhatsApp: message envoyé sid={sid}")
            return True
        logger.error(f"WhatsApp error: {result.get('message')}")
        return False
    except Exception as e:
        logger.error(f"WhatsApp send error: {e}")
        return False


def test_whatsapp_connection(account_sid: str, auth_token: str) -> dict:
    """Teste les credentials Twilio."""
    try:
        credentials = base64.b64encode(f"{account_sid}:{auth_token}".encode()).decode()
        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}.json"
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Basic {credentials}"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            result = json.loads(resp.read().decode())
            return {
                "success": True,
                "account_name": result.get("friendly_name"),
                "status": result.get("status"),
            }
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return {"success": False, "error": "Credentials invalides (401 Unauthorized)"}
        return {"success": False, "error": f"HTTP {e.code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
