"""Scheduler APScheduler pour KAsoft Hub."""
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()
_started = False


def start_scheduler():
    global _started
    if _started:
        return
    scheduler.start()
    _started = True

    scheduler.add_job(
        process_campaign_steps,
        trigger=CronTrigger(minute="*/30"),
        id="campaign_steps",
        name="Livraison étapes campagnes",
        replace_existing=True,
    )
    scheduler.add_job(
        check_ticket_sla,
        trigger=CronTrigger(minute=0),
        id="ticket_sla",
        name="Vérification SLA tickets",
        replace_existing=True,
    )
    scheduler.add_job(
        send_sav_digest,
        trigger=CronTrigger(hour=8, minute=0),
        id="sav_digest",
        name="Digest SAV quotidien",
        replace_existing=True,
    )
    scheduler.add_job(
        cleanup_old_events,
        trigger=CronTrigger(day_of_week="sun", hour=2, minute=0),
        id="cleanup_events",
        name="Nettoyage événements anciens",
        replace_existing=True,
    )
    logger.info("[HUB SCHEDULER] Démarré — 4 jobs enregistrés")


def stop_scheduler():
    global _started
    if _started:
        scheduler.shutdown()
        _started = False


def get_status() -> dict:
    return {
        "running": _started,
        "jobs": [
            {
                "id": j.id,
                "name": j.name,
                "next_run": j.next_run_time.isoformat() if j.next_run_time else None,
            }
            for j in scheduler.get_jobs()
        ],
    }


async def process_campaign_steps():
    """Livre les étapes de campagne dont la date d'envoi est échue."""
    from ..database import execute, write
    from .automation_engine import _send_message_to_contact, _get_channel_config
    try:
        due = execute(
            """SELECT e.id AS enroll_id, e.contact_id, e.campaign_id, e.current_step,
                      s.channel, s.template_id, c.product_code
               FROM HUB_CampaignEnrollments e
               JOIN HUB_Campaigns c ON c.id = e.campaign_id
               JOIN HUB_CampaignSteps s ON s.campaign_id = e.campaign_id AND s.step_order = e.current_step + 1
               WHERE e.statut = 'active'
               AND (e.next_send_at IS NULL OR e.next_send_at <= GETDATE())
               AND c.statut = 'active'
               AND s.actif = 1"""
        )
        for row in due:
            _send_message_to_contact(
                row["contact_id"], row["channel"], row["template_id"], {}, row["product_code"]
            )
            # Calculer prochaine étape
            next_steps = execute(
                "SELECT step_order, delay_days FROM HUB_CampaignSteps WHERE campaign_id=? AND step_order=? AND actif=1",
                (row["campaign_id"], row["current_step"] + 2),
            )
            if next_steps:
                from datetime import timedelta
                delay = next_steps[0]["delay_days"]
                next_send = datetime.now() + timedelta(days=delay)
                write(
                    "UPDATE HUB_CampaignEnrollments SET current_step=current_step+1, next_send_at=? WHERE id=?",
                    (next_send, row["enroll_id"]),
                )
            else:
                write(
                    "UPDATE HUB_CampaignEnrollments SET statut='completed', completed_at=GETDATE() WHERE id=?",
                    (row["enroll_id"],),
                )
        if due:
            logger.info(f"[CAMPAIGN] {len(due)} étapes livrées")
    except Exception as e:
        logger.error(f"[CAMPAIGN] process_campaign_steps error: {e}")


async def check_ticket_sla():
    """Marque les tickets en retard (SLA dépassé)."""
    from ..database import write
    try:
        updated = write(
            """UPDATE HUB_Tickets
               SET statut='overdue'
               WHERE statut IN ('open', 'in_progress')
               AND DATEDIFF(HOUR, created_at, GETDATE()) > sla_hours"""
        )
        if updated:
            logger.info(f"[SLA] {updated} ticket(s) marqués en retard")
    except Exception as e:
        logger.error(f"[SLA] check_ticket_sla error: {e}")


async def send_sav_digest():
    """Envoie un résumé quotidien des tickets ouverts."""
    from ..database import execute
    from .email_service import send_email, get_email_config
    try:
        stats = execute(
            """SELECT
                 SUM(CASE WHEN statut='open' THEN 1 ELSE 0 END) AS open_count,
                 SUM(CASE WHEN statut='in_progress' THEN 1 ELSE 0 END) AS inprog_count,
                 SUM(CASE WHEN statut='overdue' THEN 1 ELSE 0 END) AS overdue_count,
                 SUM(CASE WHEN statut='resolved' AND CAST(resolved_at AS DATE)=CAST(GETDATE() AS DATE) THEN 1 ELSE 0 END) AS resolved_today
               FROM HUB_Tickets"""
        )
        if not stats or not get_email_config():
            return
        s = stats[0]
        date_str = datetime.now().strftime("%d/%m/%Y")
        html = f"""
        <h2>Digest SAV — {date_str}</h2>
        <table border="1" cellpadding="8" style="border-collapse:collapse;">
          <tr><td>Tickets ouverts</td><td><b>{s['open_count'] or 0}</b></td></tr>
          <tr><td>En cours</td><td><b>{s['inprog_count'] or 0}</b></td></tr>
          <tr><td>En retard (SLA)</td><td><b style="color:red">{s['overdue_count'] or 0}</b></td></tr>
          <tr><td>Résolus aujourd'hui</td><td><b style="color:green">{s['resolved_today'] or 0}</b></td></tr>
        </table>
        """
        # Récupérer les emails admin depuis HUB_ChannelConfig (smtp_user comme fallback)
        cfg_rows = execute("SELECT smtp_user FROM HUB_ChannelConfig WHERE id=1")
        admin_email = cfg_rows[0]["smtp_user"] if cfg_rows and cfg_rows[0].get("smtp_user") else None
        if admin_email:
            send_email([admin_email], f"Digest SAV — {date_str}", html)
            logger.info("[DIGEST] Digest SAV envoyé")
    except Exception as e:
        logger.error(f"[DIGEST] send_sav_digest error: {e}")


async def cleanup_old_events():
    """Archive les événements traités de plus de 30 jours."""
    from ..database import write
    try:
        deleted = write(
            "DELETE FROM HUB_Events WHERE processed=1 AND DATEDIFF(DAY, created_at, GETDATE()) > 30"
        )
        logger.info(f"[CLEANUP] {deleted} événements archivés")
    except Exception as e:
        logger.error(f"[CLEANUP] cleanup_old_events error: {e}")
