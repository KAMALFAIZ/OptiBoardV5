"""CRUD Tickets SAV + messages + changement de statut."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from ..database import execute, write, write_returning_id
from ..services.automation_engine import _send_message_to_contact

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


class TicketCreate(BaseModel):
    product_code: str
    contact_id: Optional[int] = None
    sujet: str
    description: Optional[str] = None
    priorite: str = "medium"
    canal_ouverture: str = "manual"
    assigned_to: Optional[str] = None
    sla_hours: int = 24


class TicketReply(BaseModel):
    contenu: str
    channel: str = "email"
    sent_by: str = "agent"


class TicketStatusUpdate(BaseModel):
    statut: str
    note: Optional[str] = None


@router.get("")
async def list_tickets(
    product_code: Optional[str] = None,
    statut: Optional[str] = None,
    priorite: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    where = ["1=1"]
    params = []
    if product_code:
        where.append("t.product_code=?")
        params.append(product_code.upper())
    if statut:
        where.append("t.statut=?")
        params.append(statut)
    if priorite:
        where.append("t.priorite=?")
        params.append(priorite)
    if search:
        where.append("(t.sujet LIKE ? OR t.numero LIKE ?)")
        s = f"%{search}%"
        params.extend([s, s])

    where_sql = " AND ".join(where)
    tickets = execute(
        f"""SELECT t.*, c.nom AS contact_nom, c.email AS contact_email, c.telephone AS contact_tel
            FROM HUB_Tickets t
            LEFT JOIN HUB_Contacts c ON c.id = t.contact_id
            WHERE {where_sql}
            ORDER BY t.created_at DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY""",
        tuple(params) + (offset, limit),
    )
    total = execute(
        f"SELECT COUNT(*) AS cnt FROM HUB_Tickets t WHERE {where_sql}",
        tuple(params),
    )
    return {"success": True, "data": tickets, "total": total[0]["cnt"] if total else 0}


@router.get("/stats")
async def ticket_stats():
    """KPIs SAV pour le dashboard."""
    rows = execute(
        """SELECT
             SUM(CASE WHEN statut='open' THEN 1 ELSE 0 END) AS open_count,
             SUM(CASE WHEN statut='in_progress' THEN 1 ELSE 0 END) AS inprog_count,
             SUM(CASE WHEN statut='overdue' THEN 1 ELSE 0 END) AS overdue_count,
             SUM(CASE WHEN statut='resolved' THEN 1 ELSE 0 END) AS resolved_count,
             SUM(CASE WHEN statut='closed' THEN 1 ELSE 0 END) AS closed_count,
             AVG(CASE WHEN resolved_at IS NOT NULL
                 THEN DATEDIFF(HOUR, created_at, resolved_at) END) AS avg_resolution_hours
           FROM HUB_Tickets"""
    )
    return {"success": True, "data": rows[0] if rows else {}}


@router.get("/{ticket_id}")
async def get_ticket(ticket_id: int):
    rows = execute(
        """SELECT t.*, c.nom AS contact_nom, c.email AS contact_email,
                  c.telephone AS contact_tel, c.whatsapp AS contact_whatsapp
           FROM HUB_Tickets t
           LEFT JOIN HUB_Contacts c ON c.id = t.contact_id
           WHERE t.id=?""",
        (ticket_id,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Ticket non trouvé")
    ticket = rows[0]
    messages = execute(
        "SELECT * FROM HUB_TicketMessages WHERE ticket_id=? ORDER BY sent_at",
        (ticket_id,),
    )
    ticket["messages"] = messages
    return {"success": True, "data": ticket}


@router.post("")
async def create_ticket(body: TicketCreate):
    # Générer numéro
    year = datetime.now().year
    rows = execute(
        "SELECT COUNT(*) AS cnt FROM HUB_Tickets WHERE product_code=? AND YEAR(created_at)=?",
        (body.product_code.upper(), year),
    )
    seq = (rows[0]["cnt"] + 1) if rows else 1
    numero = f"{body.product_code[:3].upper()}-{year}-{seq:04d}"

    ticket_id = write_returning_id(
        """INSERT INTO HUB_Tickets
           (product_code, contact_id, numero, sujet, description, priorite, canal_ouverture, assigned_to, sla_hours)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            body.product_code.upper(), body.contact_id, numero,
            body.sujet, body.description, body.priorite,
            body.canal_ouverture, body.assigned_to, body.sla_hours,
        ),
    )
    rows = execute("SELECT * FROM HUB_Tickets WHERE id=?", (ticket_id,))
    return {"success": True, "data": rows[0]}


@router.put("/{ticket_id}/status")
async def update_ticket_status(ticket_id: int, body: TicketStatusUpdate):
    valid_statuts = ["open", "in_progress", "pending", "resolved", "closed"]
    if body.statut not in valid_statuts:
        raise HTTPException(status_code=400, detail=f"Statut invalide. Valeurs: {valid_statuts}")

    resolved_at = "GETDATE()" if body.statut == "resolved" else "NULL"
    write(
        f"UPDATE HUB_Tickets SET statut=?, updated_at=GETDATE(), resolved_at={resolved_at} WHERE id=?",
        (body.statut, ticket_id),
    )
    if body.note:
        write(
            "INSERT INTO HUB_TicketMessages (ticket_id, direction, channel, contenu, sent_by) VALUES (?, 'out', 'internal', ?, 'system')",
            (ticket_id, f"[Statut → {body.statut}] {body.note}"),
        )
    rows = execute("SELECT * FROM HUB_Tickets WHERE id=?", (ticket_id,))
    return {"success": True, "data": rows[0]}


@router.post("/{ticket_id}/reply")
async def reply_to_ticket(ticket_id: int, body: TicketReply):
    """Envoie une réponse au contact et enregistre le message."""
    tickets = execute(
        "SELECT t.*, c.* FROM HUB_Tickets t LEFT JOIN HUB_Contacts c ON c.id=t.contact_id WHERE t.id=?",
        (ticket_id,),
    )
    if not tickets:
        raise HTTPException(status_code=404, detail="Ticket non trouvé")
    ticket = tickets[0]

    # Enregistrer le message
    write(
        "INSERT INTO HUB_TicketMessages (ticket_id, direction, channel, contenu, sent_by) VALUES (?, 'out', ?, ?, ?)",
        (ticket_id, body.channel, body.contenu, body.sent_by),
    )

    # Envoyer au contact si canal disponible
    sent = False
    if ticket.get("contact_id"):
        contact = execute("SELECT * FROM HUB_Contacts WHERE id=?", (ticket["contact_id"],))
        if contact:
            c = contact[0]
            cfg_rows = execute("SELECT * FROM HUB_ChannelConfig WHERE id=1")
            cfg = cfg_rows[0] if cfg_rows else {}

            if body.channel == "telegram" and c.get("telegram_chat_id"):
                from ..services.telegram_service import send_telegram_message
                sent = send_telegram_message(cfg.get("telegram_bot_token", ""), c["telegram_chat_id"], body.contenu)
            elif body.channel == "whatsapp" and (c.get("whatsapp") or c.get("telephone")):
                from ..services.whatsapp_service import send_whatsapp_message
                num = c.get("whatsapp") or c.get("telephone")
                sent = send_whatsapp_message(
                    cfg.get("twilio_account_sid", ""), cfg.get("twilio_auth_token", ""),
                    cfg.get("twilio_whatsapp_from", ""), num, body.contenu,
                )
            elif body.channel == "email" and c.get("email"):
                from ..services.email_service import send_email
                res = send_email([c["email"]], f"Re: {ticket.get('sujet', 'Ticket')}", f"<p>{body.contenu}</p>")
                sent = res.get("success", False)

    # Mettre à jour statut → in_progress si encore open
    if ticket.get("statut") == "open":
        write("UPDATE HUB_Tickets SET statut='in_progress', updated_at=GETDATE() WHERE id=?", (ticket_id,))

    return {"success": True, "sent": sent}
