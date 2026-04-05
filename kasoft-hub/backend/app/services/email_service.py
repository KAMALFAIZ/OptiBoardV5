"""Service d'envoi d'emails pour KAsoft Hub."""
import smtplib
import ssl
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional
from ..database import execute


def get_email_config() -> Optional[dict]:
    """Récupère la config SMTP depuis HUB_ChannelConfig ou .env."""
    try:
        result = execute(
            "SELECT smtp_host, smtp_port, smtp_user, smtp_password, smtp_from_name, smtp_use_ssl, smtp_use_tls "
            "FROM HUB_ChannelConfig WHERE id=1"
        )
        if result and result[0].get("smtp_host"):
            return result[0]
    except Exception:
        pass

    smtp_host = os.getenv("SMTP_HOST", "")
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    if smtp_host and smtp_user and smtp_password:
        return {
            "smtp_host": smtp_host,
            "smtp_port": int(os.getenv("SMTP_PORT", "587")),
            "smtp_user": smtp_user,
            "smtp_password": smtp_password,
            "smtp_from_name": os.getenv("SMTP_FROM_NAME", "KAsoft Hub"),
            "smtp_use_ssl": os.getenv("SMTP_USE_SSL", "false").lower() == "true",
            "smtp_use_tls": os.getenv("SMTP_USE_TLS", "true").lower() == "true",
        }
    return None


def send_email(
    to_emails: List[str],
    subject: str,
    body_html: str,
    attachments: Optional[List[str]] = None,
    cc_emails: Optional[List[str]] = None,
) -> dict:
    """Envoie un email HTML avec pièces jointes optionnelles."""
    config = get_email_config()
    if not config:
        return {"success": False, "error": "Configuration SMTP non trouvée"}

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{config.get('smtp_from_name', 'KAsoft Hub')} <{config['smtp_user']}>"
        msg["To"] = ", ".join(to_emails)
        msg["Subject"] = subject
        if cc_emails:
            msg["Cc"] = ", ".join(cc_emails)
        msg.attach(MIMEText(body_html, "html", "utf-8"))

        if attachments:
            for filepath in attachments:
                if os.path.exists(filepath):
                    with open(filepath, "rb") as f:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", f'attachment; filename="{os.path.basename(filepath)}"')
                    msg.attach(part)

        all_recipients = to_emails + (cc_emails or [])
        port = int(config.get("smtp_port", 587))
        use_ssl = config.get("smtp_use_ssl", False)
        use_tls = config.get("smtp_use_tls", False)

        if port == 465 or (use_ssl and port != 587):
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(config["smtp_host"], port, context=ctx) as srv:
                srv.login(config["smtp_user"], config["smtp_password"])
                srv.sendmail(config["smtp_user"], all_recipients, msg.as_string())
        else:
            with smtplib.SMTP(config["smtp_host"], port) as srv:
                if use_ssl or use_tls or port == 587:
                    srv.starttls(context=ssl.create_default_context())
                srv.login(config["smtp_user"], config["smtp_password"])
                srv.sendmail(config["smtp_user"], all_recipients, msg.as_string())

        return {"success": True, "message": f"Email envoyé à {len(all_recipients)} destinataire(s)"}
    except smtplib.SMTPAuthenticationError:
        return {"success": False, "error": "Erreur d'authentification SMTP"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def test_email_config(config: dict) -> dict:
    """Teste une configuration SMTP."""
    try:
        port = int(config.get("smtp_port", 587))
        if port == 465 or config.get("smtp_use_ssl"):
            with smtplib.SMTP_SSL(config["smtp_host"], port, context=ssl.create_default_context()) as srv:
                srv.login(config["smtp_user"], config["smtp_password"])
        else:
            with smtplib.SMTP(config["smtp_host"], port) as srv:
                srv.starttls(context=ssl.create_default_context())
                srv.login(config["smtp_user"], config["smtp_password"])
        return {"success": True, "message": "Connexion SMTP réussie"}
    except smtplib.SMTPAuthenticationError:
        return {"success": False, "error": "Authentification échouée"}
    except Exception as e:
        return {"success": False, "error": str(e)}
