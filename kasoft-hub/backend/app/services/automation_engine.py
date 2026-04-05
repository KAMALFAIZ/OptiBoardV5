"""Moteur d'automation : traite les événements et déclenche les workflows."""
import json
import logging
from datetime import datetime
from typing import Optional
from ..database import execute, write, write_returning_id

logger = logging.getLogger(__name__)

SUPPORTED_EVENTS = [
    "new_prospect", "new_client", "demo_requested", "demo_completed",
    "ticket_opened", "ticket_resolved", "payment_late", "subscription_expiring",
    "contact_updated",
]


def process_event(product_code: str, event_type: str, payload: dict) -> dict:
    """
    Point d'entrée principal : enregistre l'événement et déclenche les workflows correspondants.
    Crée ou met à jour le contact si les données le permettent.
    """
    # 1 — Enregistrer l'événement
    event_id = write_returning_id(
        "INSERT INTO HUB_Events (product_code, event_type, payload) VALUES (?, ?, ?)",
        (product_code, event_type, json.dumps(payload, ensure_ascii=False)),
    )

    # 2 — Créer/identifier le contact
    contact_id = _upsert_contact(product_code, event_type, payload)

    # 3 — Action spécifique selon l'événement
    ticket_id = None
    if event_type == "ticket_opened":
        ticket_id = _create_ticket_from_event(product_code, contact_id, payload)

    # 4 — Déclencher les workflows actifs correspondants
    workflows = execute(
        """SELECT * FROM HUB_Workflows
           WHERE is_active=1
           AND trigger_event=?
           AND (product_code=? OR product_code='ALL')""",
        (event_type, product_code),
    )
    actions_count = 0
    for wf in workflows:
        if _matches_condition(wf.get("trigger_condition"), payload):
            _execute_workflow(wf, contact_id, ticket_id, payload)
            write(
                "UPDATE HUB_Workflows SET executions_count=executions_count+1 WHERE id=?",
                (wf["id"],),
            )
            actions_count += 1

    # 5 — Marquer l'événement comme traité
    write(
        "UPDATE HUB_Events SET processed=1, processed_at=GETDATE() WHERE id=?",
        (event_id,),
    )

    return {
        "event_id": event_id,
        "contact_id": contact_id,
        "ticket_id": ticket_id,
        "workflows_triggered": actions_count,
    }


def _upsert_contact(product_code: str, event_type: str, payload: dict) -> Optional[int]:
    """Crée ou met à jour le contact à partir du payload."""
    email = payload.get("email")
    telephone = payload.get("telephone") or payload.get("phone")
    nom = payload.get("nom") or payload.get("name") or "Inconnu"
    external_id = str(payload.get("id") or payload.get("external_id") or "")

    if not email and not telephone and not external_id:
        return None

    # Chercher par external_id ou email
    existing = None
    if external_id:
        rows = execute(
            "SELECT id FROM HUB_Contacts WHERE product_code=? AND external_id=?",
            (product_code, external_id),
        )
        existing = rows[0] if rows else None
    if not existing and email:
        rows = execute(
            "SELECT id FROM HUB_Contacts WHERE product_code=? AND email=?",
            (product_code, email),
        )
        existing = rows[0] if rows else None

    # Déterminer le segment selon l'événement
    segment_map = {
        "new_prospect": "prospect",
        "demo_requested": "prospect",
        "demo_completed": "lead",
        "new_client": "client",
    }
    segment = segment_map.get(event_type, "prospect")

    if existing:
        write(
            "UPDATE HUB_Contacts SET nom=?, email=?, telephone=?, whatsapp=?, societe=?, segment=?, updated_at=GETDATE() WHERE id=?",
            (
                nom,
                email or "",
                telephone or "",
                payload.get("whatsapp") or telephone or "",
                payload.get("societe") or payload.get("company") or "",
                segment,
                existing["id"],
            ),
        )
        return existing["id"]
    else:
        return write_returning_id(
            """INSERT INTO HUB_Contacts
               (product_code, external_id, nom, prenom, email, telephone, whatsapp, societe, poste, segment, source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                product_code,
                external_id,
                nom,
                payload.get("prenom") or payload.get("first_name") or "",
                email or "",
                telephone or "",
                payload.get("whatsapp") or telephone or "",
                payload.get("societe") or payload.get("company") or "",
                payload.get("poste") or payload.get("position") or "",
                segment,
                payload.get("source") or "webhook",
            ),
        )


def _create_ticket_from_event(product_code: str, contact_id: Optional[int], payload: dict) -> Optional[int]:
    """Crée un ticket SAV depuis un événement webhook."""
    # Générer numéro séquentiel
    year = datetime.now().year
    rows = execute(
        "SELECT COUNT(*) AS cnt FROM HUB_Tickets WHERE product_code=? AND YEAR(created_at)=?",
        (product_code, year),
    )
    seq = (rows[0]["cnt"] + 1) if rows else 1
    numero = f"{product_code[:3]}-{year}-{seq:04d}"

    return write_returning_id(
        """INSERT INTO HUB_Tickets
           (product_code, contact_id, numero, sujet, description, priorite, canal_ouverture)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            product_code,
            contact_id,
            numero,
            payload.get("sujet") or payload.get("subject") or "Ticket ouvert via webhook",
            payload.get("description") or "",
            payload.get("priorite") or "medium",
            payload.get("canal") or "webhook",
        ),
    )


def _matches_condition(condition_json: Optional[str], payload: dict) -> bool:
    """Vérifie si le payload correspond aux conditions du workflow."""
    if not condition_json:
        return True
    try:
        conditions = json.loads(condition_json)
        for key, expected in conditions.items():
            if str(payload.get(key, "")).lower() != str(expected).lower():
                return False
        return True
    except Exception:
        return True


def _execute_workflow(workflow: dict, contact_id: Optional[int], ticket_id: Optional[int], payload: dict):
    """Exécute les actions d'un workflow."""
    try:
        actions = json.loads(workflow.get("actions", "[]"))
    except Exception:
        return

    for action in actions:
        action_type = action.get("type", "send_message")
        channel = action.get("channel", "telegram")
        template_id = action.get("template_id")
        delay_hours = action.get("delay_hours", 0)

        # Délai > 0 : créer un enrollment différé (traité par le scheduler)
        if delay_hours > 0 and contact_id:
            _schedule_deferred_action(contact_id, ticket_id, channel, template_id, delay_hours, workflow["id"])
            continue

        # Envoi immédiat
        if contact_id and action_type == "send_message":
            _send_message_to_contact(contact_id, channel, template_id, payload, workflow.get("product_code"))

        elif action_type == "create_ticket" and contact_id and not ticket_id:
            _create_ticket_from_event(workflow.get("product_code", ""), contact_id, payload)


def _schedule_deferred_action(contact_id: int, ticket_id, channel: str, template_id, delay_hours: int, workflow_id: int):
    """Planifie une action différée dans HUB_DeliveryLog (statut=pending)."""
    from datetime import timedelta
    send_at = datetime.now() + timedelta(hours=delay_hours)
    write(
        """INSERT INTO HUB_DeliveryLog (contact_id, ticket_id, channel, template_id, recipient, statut, sent_at)
           VALUES (?, ?, ?, ?, 'deferred', 'pending', ?)""",
        (contact_id, ticket_id, channel, template_id, send_at),
    )


def _send_message_to_contact(contact_id: int, channel: str, template_id: Optional[int], payload: dict, product_code: str):
    """Récupère les infos de contact et envoie le message selon le canal."""
    contacts = execute("SELECT * FROM HUB_Contacts WHERE id=?", (contact_id,))
    if not contacts:
        return
    contact = contacts[0]

    # Récupérer le template
    text = _render_template(template_id, contact, payload, product_code)
    if not text:
        return

    # Config canaux
    cfg = _get_channel_config()

    sent = False
    recipient = ""
    if channel == "telegram" and contact.get("telegram_chat_id"):
        from .telegram_service import send_telegram_message
        recipient = contact["telegram_chat_id"]
        sent = send_telegram_message(cfg.get("telegram_bot_token", ""), recipient, text)
    elif channel == "whatsapp" and (contact.get("whatsapp") or contact.get("telephone")):
        from .whatsapp_service import send_whatsapp_message
        recipient = contact.get("whatsapp") or contact.get("telephone")
        sent = send_whatsapp_message(
            cfg.get("twilio_account_sid", ""),
            cfg.get("twilio_auth_token", ""),
            cfg.get("twilio_whatsapp_from", ""),
            recipient, text,
        )
    elif channel == "email" and contact.get("email"):
        from .email_service import send_email
        recipient = contact["email"]
        result = send_email([recipient], f"Message de {product_code}", f"<p>{text}</p>")
        sent = result.get("success", False)

    # Log livraison
    write(
        "INSERT INTO HUB_DeliveryLog (contact_id, channel, template_id, recipient, statut) VALUES (?, ?, ?, ?, ?)",
        (contact_id, channel, template_id, recipient, "sent" if sent else "failed"),
    )


def _render_template(template_id: Optional[int], contact: dict, payload: dict, product_code: str) -> Optional[str]:
    """Récupère et remplace les variables du template."""
    if not template_id:
        nom = contact.get("nom", "")
        return f"Bonjour {nom}, merci pour votre intérêt pour {product_code}."
    rows = execute("SELECT contenu FROM HUB_Templates WHERE id=?", (template_id,))
    if not rows:
        return None
    text = rows[0]["contenu"]
    variables = {
        "nom": contact.get("nom", ""),
        "prenom": contact.get("prenom", ""),
        "societe": contact.get("societe", ""),
        "email": contact.get("email", ""),
        "produit": product_code,
        **payload,
    }
    for key, val in variables.items():
        text = text.replace(f"{{{key}}}", str(val or ""))
    return text


def _get_channel_config() -> dict:
    """Récupère la configuration des canaux."""
    rows = execute("SELECT * FROM HUB_ChannelConfig WHERE id=1")
    return rows[0] if rows else {}
