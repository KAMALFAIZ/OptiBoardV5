"""Service d'envoi d'emails pour les rapports"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional
from pathlib import Path
import os
from ..database_unified import execute_app as execute_query, app_cursor as get_db_cursor


def get_email_config():
    """
    Recupere la configuration email.
    Priorite : APP_EmailConfig (base) → variables d'environnement (.env)
    """
    try:
        result = execute_query(
            """SELECT smtp_server AS smtp_host, smtp_port,
                      smtp_username AS smtp_user, smtp_password,
                      from_email, from_name AS sender_name,
                      use_ssl, use_tls
               FROM APP_EmailConfig WHERE actif = 1""",
            use_cache=False
        )
        if result:
            return result[0]
    except Exception:
        pass

    # Fallback : variables d'environnement
    smtp_host = os.getenv('SMTP_HOST', '')
    smtp_user = os.getenv('SMTP_USER', '')
    smtp_password = os.getenv('SMTP_PASSWORD', '')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    if smtp_host and smtp_user and smtp_password:
        return {
            'smtp_host': smtp_host,
            'smtp_port': smtp_port,
            'smtp_user': smtp_user,
            'smtp_password': smtp_password,
            'sender_name': os.getenv('SMTP_FROM_NAME', 'OptiBoard'),
            'use_ssl': os.getenv('SMTP_USE_SSL', 'false').lower() == 'true',
            'use_tls': os.getenv('SMTP_USE_TLS', 'true').lower() == 'true',
        }
    return None


def send_email(
    to_emails: List[str],
    subject: str,
    body_html: str,
    attachments: Optional[List[str]] = None,
    cc_emails: Optional[List[str]] = None
) -> dict:
    """
    Envoie un email avec pieces jointes optionnelles

    Args:
        to_emails: Liste des destinataires
        subject: Sujet de l'email
        body_html: Corps de l'email en HTML
        attachments: Liste des chemins de fichiers a joindre
        cc_emails: Liste des destinataires en copie

    Returns:
        dict avec success et message
    """
    config = get_email_config()
    if not config:
        return {"success": False, "error": "Configuration email non trouvee ou inactive"}

    try:
        # Creer le message
        msg = MIMEMultipart('alternative')
        msg['From'] = f"{config.get('sender_name', 'Reporting')} <{config['smtp_user']}>"
        msg['To'] = ', '.join(to_emails)
        msg['Subject'] = subject

        if cc_emails:
            msg['Cc'] = ', '.join(cc_emails)

        # Corps du message en HTML
        html_part = MIMEText(body_html, 'html', 'utf-8')
        msg.attach(html_part)

        # Ajouter les pieces jointes
        if attachments:
            for filepath in attachments:
                if os.path.exists(filepath):
                    with open(filepath, 'rb') as f:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(f.read())
                    encoders.encode_base64(part)
                    filename = os.path.basename(filepath)
                    part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
                    msg.attach(part)

        # Connexion et envoi
        all_recipients = to_emails + (cc_emails or [])
        port = int(config.get('smtp_port', 587))
        use_ssl = config.get('use_ssl', False)
        use_tls = config.get('use_tls', False)

        if port == 465 or (use_ssl and port != 587):
            # SSL direct (port 465)
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(config['smtp_host'], port, context=context) as server:
                server.login(config['smtp_user'], config['smtp_password'])
                server.sendmail(config['smtp_user'], all_recipients, msg.as_string())
        else:
            # Port 587 ou autre : SMTP + STARTTLS
            with smtplib.SMTP(config['smtp_host'], port) as server:
                if use_ssl or use_tls or port == 587:
                    context = ssl.create_default_context()
                    server.starttls(context=context)
                server.login(config['smtp_user'], config['smtp_password'])
                server.sendmail(config['smtp_user'], all_recipients, msg.as_string())

        return {"success": True, "message": f"Email envoye a {len(all_recipients)} destinataire(s)"}

    except smtplib.SMTPAuthenticationError:
        return {"success": False, "error": "Erreur d'authentification SMTP"}
    except smtplib.SMTPException as e:
        return {"success": False, "error": f"Erreur SMTP: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Erreur: {str(e)}"}


def test_email_config(config: dict) -> dict:
    """Teste une configuration email"""
    try:
        port = int(config.get('smtp_port', 587))
        use_ssl = config.get('use_ssl', False)
        use_tls = config.get('use_tls', False)

        if port == 465 or (use_ssl and port != 587):
            # SSL direct (port 465)
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(config['smtp_host'], port, context=context) as server:
                server.login(config['smtp_user'], config['smtp_password'])
        else:
            # Port 587 ou autre : SMTP + STARTTLS
            with smtplib.SMTP(config['smtp_host'], port) as server:
                if use_ssl or use_tls or port == 587:
                    context = ssl.create_default_context()
                    server.starttls(context=context)
                server.login(config['smtp_user'], config['smtp_password'])

        return {"success": True, "message": "Connexion SMTP réussie"}
    except smtplib.SMTPAuthenticationError:
        return {"success": False, "error": "Authentification échouée. Pour Gmail, utilisez un mot de passe d'application (App Password)."}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_email_template(template_name: str, variables: dict) -> str:
    """Genere le contenu HTML d'un email a partir d'un template"""

    templates = {
        "report_delivery": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #059669 0%, #047857 100%); color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f9fafb; padding: 20px; border: 1px solid #e5e7eb; }}
        .footer {{ background: #f3f4f6; padding: 15px; text-align: center; font-size: 12px; color: #6b7280; border-radius: 0 0 8px 8px; }}
        .btn {{ display: inline-block; background: #059669; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin: 10px 0; }}
        .info-box {{ background: white; padding: 15px; border-radius: 5px; margin: 10px 0; border-left: 4px solid #059669; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2 style="margin: 0;">KAsoft - Reporting</h2>
            <p style="margin: 5px 0 0 0; opacity: 0.9;">{title}</p>
        </div>
        <div class="content">
            <p>Bonjour,</p>
            <p>Veuillez trouver ci-joint le rapport <strong>{report_name}</strong> généré automatiquement.</p>

            <div class="info-box">
                <p style="margin: 0;"><strong>Détails du rapport :</strong></p>
                <ul style="margin: 10px 0;">
                    <li>Type: {report_type}</li>
                    <li>Période : {period}</li>
                    <li>Date de génération : {generated_at}</li>
                </ul>
            </div>

            <p>Le fichier est disponible en pièce jointe.</p>

            <p>Cordialement,<br>L'équipe Reporting</p>
        </div>
        <div class="footer">
            <p>Ce message a été envoyé automatiquement. Merci de ne pas y répondre.</p>
            <p>KAsoft - Système de Reporting Commercial</p>
        </div>
    </div>
</body>
</html>
""",
        "test_email": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; }}
        .container {{ max-width: 500px; margin: 0 auto; padding: 20px; text-align: center; }}
        .success {{ background: #d1fae5; color: #065f46; padding: 20px; border-radius: 8px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="success">
            <h2>Configuration Email Validée</h2>
            <p>La configuration SMTP fonctionne correctement.</p>
            <p>Envoyé le : {sent_at}</p>
        </div>
    </div>
</body>
</html>
"""
    }

    template = templates.get(template_name, templates["report_delivery"])
    return template.format(**variables)
