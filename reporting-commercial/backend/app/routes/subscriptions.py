"""Routes pour les abonnements utilisateurs (email, WhatsApp, Telegram)"""
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime, timedelta
import json

from ..database_unified import execute_central as execute_query, write_central as _write
from ..services.email_service import send_email
from ..services.telegram_service import (
    send_telegram_message, send_telegram_document,
    build_telegram_message, test_telegram_connection,
)
from ..services.whatsapp_service import (
    send_whatsapp_message, build_whatsapp_message, test_whatsapp_connection,
)

router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])

FREQUENCIES = {
    "daily":   {"label": "Quotidien",    "days": 1},
    "weekly":  {"label": "Hebdomadaire", "days": 7},
    "monthly": {"label": "Mensuel",      "days": 30},
}


# ==================== SCHEMAS ====================

class RecipientIn(BaseModel):
    nom: Optional[str] = None
    channel: str = "email"
    contact_info: str


class SubscriptionCreate(BaseModel):
    user_email: str
    report_type: str       # gridview | dashboard | pivot
    report_id: int
    report_nom: str
    frequency: str         # daily | weekly | monthly
    export_format: str = "excel"
    channel: str = "email"
    contact_info: Optional[str] = None
    # Planification avancée
    heure_envoi: int = 7
    jour_semaine: Optional[int] = None   # 0=lundi…6=dim (weekly)
    jour_mois: Optional[int] = None      # 1-28 (monthly)
    date_debut: Optional[str] = None     # ISO date "YYYY-MM-DD"
    date_fin: Optional[str] = None       # ISO date "YYYY-MM-DD" (optionnel)
    # Destinataires supplémentaires
    recipients: Optional[list] = None   # List[RecipientIn]


class SubscriptionUpdate(BaseModel):
    frequency: Optional[str] = None
    export_format: Optional[str] = None
    is_active: Optional[bool] = None
    heure_envoi: Optional[int] = None
    jour_semaine: Optional[int] = None
    jour_mois: Optional[int] = None
    date_debut: Optional[str] = None
    date_fin: Optional[str] = None
    channel: Optional[str] = None
    contact_info: Optional[str] = None


# ==================== INIT TABLE ====================

def _init_message_templates_table():
    """Crée la table APP_MessageTemplates si elle n'existe pas."""
    try:
        _write("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'APP_MessageTemplates')
        CREATE TABLE APP_MessageTemplates (
            id         INT IDENTITY(1,1) PRIMARY KEY,
            nom        NVARCHAR(100)  NOT NULL,
            channel    NVARCHAR(20)   NOT NULL,
            contenu    NVARCHAR(MAX)  NOT NULL,
            is_default BIT            NOT NULL DEFAULT 0,
            created_at DATETIME       DEFAULT GETDATE(),
            updated_at DATETIME       DEFAULT GETDATE()
        )
        """)
    except Exception as e:
        print(f"[TEMPLATES] init error: {e}")


def init_subscription_tables():
    """Crée/migre la table d'abonnements (base centrale)."""
    _init_message_templates_table()
    _init_recipients_table()
    sql_create = """
    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'APP_UserSubscriptions')
    CREATE TABLE APP_UserSubscriptions (
        id            INT IDENTITY(1,1) PRIMARY KEY,
        user_email    NVARCHAR(255) NOT NULL,
        report_type   NVARCHAR(50)  NOT NULL,
        report_id     INT           NOT NULL,
        report_nom    NVARCHAR(255) NOT NULL,
        frequency     NVARCHAR(20)  NOT NULL DEFAULT 'daily',
        export_format NVARCHAR(20)  NOT NULL DEFAULT 'excel',
        is_active     BIT           NOT NULL DEFAULT 1,
        last_sent     DATETIME,
        next_send     DATETIME,
        created_at    DATETIME      DEFAULT GETDATE(),
        updated_at    DATETIME      DEFAULT GETDATE()
    )
    """
    def _mig(col): return f"SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_UserSubscriptions') AND name='{col}'"
    migrations = [
        f"IF NOT EXISTS ({_mig('channel')}) ALTER TABLE APP_UserSubscriptions ADD channel NVARCHAR(20) NOT NULL DEFAULT 'email'",
        f"IF NOT EXISTS ({_mig('contact_info')}) ALTER TABLE APP_UserSubscriptions ADD contact_info NVARCHAR(255) NULL",
        f"IF NOT EXISTS ({_mig('heure_envoi')}) ALTER TABLE APP_UserSubscriptions ADD heure_envoi INT NOT NULL DEFAULT 7",
        f"IF NOT EXISTS ({_mig('jour_semaine')}) ALTER TABLE APP_UserSubscriptions ADD jour_semaine INT NULL",
        f"IF NOT EXISTS ({_mig('jour_mois')}) ALTER TABLE APP_UserSubscriptions ADD jour_mois INT NULL",
        f"IF NOT EXISTS ({_mig('date_debut')}) ALTER TABLE APP_UserSubscriptions ADD date_debut DATE NULL",
        f"IF NOT EXISTS ({_mig('date_fin')}) ALTER TABLE APP_UserSubscriptions ADD date_fin DATE NULL",
    ]
    try:
        _write(sql_create)
        for mig in migrations:
            try:
                _write(mig)
            except Exception as me:
                print(f"[SUBSCRIPTIONS] Migration warning: {me}")
        return True
    except Exception as e:
        print(f"[SUBSCRIPTIONS] Erreur init table: {e}")
        return False


def _init_recipients_table():
    """Crée APP_SubscriptionRecipients (destinataires supplémentaires)."""
    try:
        _write("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'APP_SubscriptionRecipients')
        CREATE TABLE APP_SubscriptionRecipients (
            id           INT IDENTITY(1,1) PRIMARY KEY,
            sub_id       INT           NOT NULL,
            nom          NVARCHAR(100) NULL,
            channel      NVARCHAR(20)  NOT NULL DEFAULT 'email',
            contact_info NVARCHAR(255) NOT NULL,
            is_active    BIT           NOT NULL DEFAULT 1,
            created_at   DATETIME      DEFAULT GETDATE()
        )
        """)
    except Exception as e:
        print(f"[SUBSCRIPTIONS] _init_recipients_table error: {e}")


def _next_send_date(
    frequency: str,
    heure: int = 7,
    jour_semaine: int = None,   # 0=lundi … 6=dimanche
    jour_mois: int = None,      # 1-28
) -> datetime:
    """Calcule la prochaine date de livraison selon la fréquence avancée."""
    now = datetime.now()
    h = max(0, min(23, int(heure or 7)))

    if frequency == "daily":
        candidate = now.replace(hour=h, minute=0, second=0, microsecond=0)
        if candidate <= now:
            candidate += timedelta(days=1)
        next_d = candidate

    elif frequency == "weekly":
        target = int(jour_semaine) if jour_semaine is not None else 0
        days_ahead = (target - now.weekday()) % 7
        if days_ahead == 0 and now.hour >= h:
            days_ahead = 7
        next_d = (now + timedelta(days=days_ahead)).replace(hour=h, minute=0, second=0, microsecond=0)

    elif frequency == "monthly":
        day = max(1, min(28, int(jour_mois) if jour_mois else 1))
        candidate = now.replace(day=day, hour=h, minute=0, second=0, microsecond=0)
        if candidate <= now:
            if now.month == 12:
                candidate = datetime(now.year + 1, 1, day, h, 0, 0)
            else:
                candidate = datetime(now.year, now.month + 1, day, h, 0, 0)
        next_d = candidate

    else:
        next_d = (now + timedelta(days=1)).replace(hour=h, minute=0, second=0, microsecond=0)

    return next_d


# ==================== RECIPIENTS HELPERS ====================

def _sync_recipients(sub_id: int, recipients: list):
    """Remplace les destinataires d'un abonnement."""
    try:
        _write("DELETE FROM APP_SubscriptionRecipients WHERE sub_id=?", (sub_id,))
        for r in recipients:
            if not r.get("contact_info"):
                continue
            _write(
                "INSERT INTO APP_SubscriptionRecipients (sub_id, nom, channel, contact_info) VALUES (?,?,?,?)",
                (sub_id, r.get("nom"), r.get("channel", "email"), r["contact_info"])
            )
    except Exception as e:
        print(f"[RECIPIENTS] sync error: {e}")


def _get_recipients(sub_id: int) -> list:
    try:
        return execute_query(
            "SELECT * FROM APP_SubscriptionRecipients WHERE sub_id=? AND is_active=1",
            (sub_id,), use_cache=False
        )
    except Exception:
        return []


# ==================== CRUD ====================

@router.get("")
async def get_subscriptions(email: Optional[str] = None):
    """Retourne les abonnements (filtrés par email si fourni)."""
    try:
        init_subscription_tables()
        if email:
            rows = execute_query(
                "SELECT * FROM APP_UserSubscriptions WHERE user_email = ? ORDER BY created_at DESC",
                (email,), use_cache=False
            )
        else:
            rows = execute_query(
                "SELECT * FROM APP_UserSubscriptions ORDER BY user_email, report_type, report_nom",
                use_cache=False
            )
        return {"success": True, "data": rows}
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}


@router.get("/check")
async def check_subscription(email: str, report_type: str, report_id: int):
    """Vérifie si un abonnement existe pour cet email + rapport."""
    try:
        init_subscription_tables()
        rows = execute_query(
            """SELECT id, frequency, export_format, is_active
               FROM APP_UserSubscriptions
               WHERE user_email = ? AND report_type = ? AND report_id = ?""",
            (email, report_type, report_id), use_cache=False
        )
        if rows:
            return {"success": True, "subscribed": True, "subscription": rows[0]}
        return {"success": True, "subscribed": False}
    except Exception as e:
        return {"success": False, "error": str(e), "subscribed": False}


@router.post("")
async def create_subscription(sub: SubscriptionCreate):
    """Crée ou réactive un abonnement."""
    try:
        init_subscription_tables()

        # Vérifier si déjà abonné
        existing = execute_query(
            """SELECT id, is_active FROM APP_UserSubscriptions
               WHERE user_email = ? AND report_type = ? AND report_id = ?""",
            (sub.user_email, sub.report_type, sub.report_id), use_cache=False
        )

        next_d = _next_send_date(sub.frequency, sub.heure_envoi, sub.jour_semaine, sub.jour_mois)

        contact = sub.contact_info or sub.user_email
        date_debut = sub.date_debut or None
        date_fin   = sub.date_fin   or None

        if existing:
            _write("""
                UPDATE APP_UserSubscriptions
                SET frequency=?, export_format=?, is_active=1,
                    channel=?, contact_info=?,
                    heure_envoi=?, jour_semaine=?, jour_mois=?,
                    date_debut=?, date_fin=?,
                    next_send=?, updated_at=GETDATE()
                WHERE id=?
            """, (sub.frequency, sub.export_format, sub.channel, contact,
                  sub.heure_envoi, sub.jour_semaine, sub.jour_mois,
                  date_debut, date_fin, next_d, existing[0]["id"]))
            sub_id = existing[0]["id"]
            _sync_recipients(sub_id, sub.recipients or [])
            return {"success": True, "message": "Abonnement réactivé", "id": sub_id}

        _write("""
            INSERT INTO APP_UserSubscriptions
                (user_email, report_type, report_id, report_nom, frequency, export_format,
                 channel, contact_info, heure_envoi, jour_semaine, jour_mois,
                 date_debut, date_fin, next_send)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (sub.user_email, sub.report_type, sub.report_id,
              sub.report_nom, sub.frequency, sub.export_format,
              sub.channel, contact, sub.heure_envoi, sub.jour_semaine, sub.jour_mois,
              date_debut, date_fin, next_d))
        rows = execute_query(
            "SELECT TOP 1 id FROM APP_UserSubscriptions ORDER BY id DESC",
            use_cache=False
        )
        new_id = rows[0]["id"] if rows else None
        if new_id:
            _sync_recipients(new_id, sub.recipients or [])

        return {"success": True, "message": "Abonnement créé", "id": new_id,
                "next_send": next_d.strftime("%d/%m/%Y à %H:%M")}

    except Exception as e:
        return {"success": False, "error": str(e)}


@router.put("/{sub_id}")
async def update_subscription(sub_id: int, sub: SubscriptionUpdate):
    """Met à jour un abonnement (planification, canal, format, statut)."""
    try:
        updates, params = [], []

        if sub.frequency is not None:
            updates.append("frequency = ?"); params.append(sub.frequency)
        if sub.heure_envoi is not None:
            updates.append("heure_envoi = ?"); params.append(sub.heure_envoi)
        if sub.jour_semaine is not None:
            updates.append("jour_semaine = ?"); params.append(sub.jour_semaine)
        if sub.jour_mois is not None:
            updates.append("jour_mois = ?"); params.append(sub.jour_mois)
        if sub.export_format is not None:
            updates.append("export_format = ?"); params.append(sub.export_format)
        if sub.is_active is not None:
            updates.append("is_active = ?"); params.append(sub.is_active)
        if sub.channel is not None:
            updates.append("channel = ?"); params.append(sub.channel)
        if sub.contact_info is not None:
            updates.append("contact_info = ?"); params.append(sub.contact_info)
        if sub.date_debut is not None:
            updates.append("date_debut = ?"); params.append(sub.date_debut or None)
        if sub.date_fin is not None:
            updates.append("date_fin = ?"); params.append(sub.date_fin or None)

        if not updates:
            return {"success": False, "error": "Aucune modification"}

        # Recalcul next_send si planification modifiée
        need_reschedule = any(f is not None for f in [
            sub.frequency, sub.heure_envoi, sub.jour_semaine, sub.jour_mois
        ])
        if need_reschedule:
            current = execute_query(
                "SELECT frequency, heure_envoi, jour_semaine, jour_mois FROM APP_UserSubscriptions WHERE id=?",
                (sub_id,), use_cache=False
            )
            if current:
                c = current[0]
                freq  = sub.frequency  if sub.frequency  is not None else c["frequency"]
                heure = sub.heure_envoi if sub.heure_envoi is not None else (c.get("heure_envoi") or 7)
                jsem  = sub.jour_semaine if sub.jour_semaine is not None else c.get("jour_semaine")
                jmois = sub.jour_mois   if sub.jour_mois   is not None else c.get("jour_mois")
                next_d = _next_send_date(freq, heure, jsem, jmois)
                updates.append("next_send = ?"); params.append(next_d)

        updates.append("updated_at = GETDATE()")
        params.append(sub_id)

        _write(f"UPDATE APP_UserSubscriptions SET {', '.join(updates)} WHERE id = ?", tuple(params))

        # Retourner la ligne mise à jour
        updated = execute_query("SELECT * FROM APP_UserSubscriptions WHERE id=?", (sub_id,), use_cache=False)
        return {"success": True, "message": "Abonnement mis à jour", "data": updated[0] if updated else None}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.delete("/{sub_id}")
async def delete_subscription(sub_id: int):
    """Supprime un abonnement."""
    try:
        _write("DELETE FROM APP_UserSubscriptions WHERE id = ?", (sub_id,))
        return {"success": True, "message": "Désabonnement effectué"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/{sub_id}/toggle")
async def toggle_subscription(sub_id: int):
    """Active/désactive un abonnement."""
    try:
        _write("""
                UPDATE APP_UserSubscriptions
                SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END,
                    updated_at = GETDATE()
                WHERE id = ?
            """, (sub_id,))
        rows = execute_query(
            "SELECT is_active FROM APP_UserSubscriptions WHERE id = ?",
            (sub_id,), use_cache=False
        )
        return {"success": True, "is_active": rows[0]["is_active"] if rows else None}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== LIVRAISON ====================

def _send_to_contact(channel, contact, file_path, report_name, freq_label, date_str, cfg):
    """Envoie le rapport à un destinataire selon le canal."""
    app_name = cfg.get("nom_entreprise", "OptiBoard")
    if channel == "telegram":
        custom = execute_query(
            "SELECT contenu FROM APP_MessageTemplates WHERE channel='telegram' AND is_default=1",
            use_cache=False
        )
        text = (custom[0]["contenu"].format(nom_app=app_name, rapport=report_name, frequence=freq_label, date=date_str)
                if custom else build_telegram_message(report_name, freq_label, date_str, app_name))
        sent = send_telegram_message(cfg.get("telegram_bot_token", ""), contact, text)
        if file_path and sent:
            with open(file_path, "rb") as f:
                send_telegram_document(cfg.get("telegram_bot_token", ""), contact,
                                       f.read(), f"{report_name}.xlsx", caption=f"📊 {report_name}")
    elif channel == "whatsapp":
        custom = execute_query(
            "SELECT contenu FROM APP_MessageTemplates WHERE channel='whatsapp' AND is_default=1",
            use_cache=False
        )
        text = (custom[0]["contenu"].format(nom_app=app_name, rapport=report_name, frequence=freq_label, date=date_str)
                if custom else build_whatsapp_message(report_name, freq_label, date_str, app_name))
        send_whatsapp_message(cfg.get("twilio_account_sid",""), cfg.get("twilio_auth_token",""),
                              cfg.get("twilio_whatsapp_from",""), contact, text)
    else:  # email
        html = build_email_html(
            template=cfg.get("template_defaut", "moderne"),
            report_name=report_name, freq_label=freq_label, date_str=date_str,
            app_name=app_name,
            color=cfg.get("couleur_principale", "#6366f1"),
            greeting=cfg.get("texte_accueil", "Bonjour,"),
            footer_text=cfg.get("texte_footer", "Ce message est généré automatiquement."),
        )
        send_email(
            to_emails=[contact],
            subject=f"[{freq_label}] {report_name} — {datetime.now().strftime('%d/%m/%Y')}",
            body_html=html,
            attachments=[file_path] if file_path else None
        )


async def deliver_due_subscriptions():
    """Livre les rapports aux abonnés échus, en respectant la période de validité."""
    from .export import generate_report_file
    from .admin_subscriptions import log_delivery

    try:
        due = execute_query("""
            SELECT * FROM APP_UserSubscriptions
            WHERE is_active = 1
              AND (next_send IS NULL OR next_send <= GETDATE())
        """, use_cache=False)
    except Exception as e:
        print(f"[SUBSCRIPTIONS] Erreur chargement abonnements: {e}")
        return

    today = datetime.now().date()
    delivered = 0

    for sub in due:
        try:
            # ── Vérification période de validité ──────────────────────────────
            date_debut = sub.get("date_debut")
            date_fin   = sub.get("date_fin")

            if date_debut:
                dd = date_debut.date() if hasattr(date_debut, 'date') else datetime.fromisoformat(str(date_debut)).date()
                if today < dd:
                    # Pas encore commencé — avancer next_send
                    next_d = _next_send_date(sub["frequency"],
                                             sub.get("heure_envoi", 7),
                                             sub.get("jour_semaine"),
                                             sub.get("jour_mois"))
                    _write("UPDATE APP_UserSubscriptions SET next_send=? WHERE id=?", (next_d, sub["id"]))
                    continue

            if date_fin:
                df = date_fin.date() if hasattr(date_fin, 'date') else datetime.fromisoformat(str(date_fin)).date()
                if today > df:
                    # Période expirée — désactiver automatiquement
                    _write("UPDATE APP_UserSubscriptions SET is_active=0, updated_at=GETDATE() WHERE id=?", (sub["id"],))
                    log_delivery(sub["id"], sub["user_email"], sub["report_nom"],
                                 sub.get("channel","email"), "skipped", "Période d'abonnement expirée")
                    continue

            # ── Génération du fichier ─────────────────────────────────────────
            report_result = await generate_report_file(
                report_type=sub["report_type"],
                report_id=sub["report_id"],
                export_format=sub["export_format"],
                filters=None
            )

            freq_label  = FREQUENCIES.get(sub["frequency"], {}).get("label", sub["frequency"])
            report_name = sub["report_nom"]
            next_d = _next_send_date(sub["frequency"],
                                     sub.get("heure_envoi", 7),
                                     sub.get("jour_semaine"),
                                     sub.get("jour_mois"))
            date_str = datetime.now().strftime('%d/%m/%Y à %H:%M')
            cfg      = _get_template_config()

            if report_result.get("success"):
                file_path = report_result.get("file_path")

                # ── Destinataire principal ────────────────────────────────────
                channel = sub.get("channel", "email") or "email"
                contact = sub.get("contact_info") or sub["user_email"]
                _send_to_contact(channel, contact, file_path, report_name, freq_label, date_str, cfg)
                log_delivery(sub["id"], sub["user_email"], report_name, channel, "success")

                # ── Destinataires supplémentaires ────────────────────────────
                extra = _get_recipients(sub["id"])
                for r in extra:
                    try:
                        _send_to_contact(r["channel"], r["contact_info"],
                                         file_path, report_name, freq_label, date_str, cfg)
                        log_delivery(sub["id"], r["contact_info"], report_name, r["channel"], "success")
                    except Exception as re:
                        log_delivery(sub["id"], r["contact_info"], report_name,
                                     r["channel"], "error", str(re)[:500])

                delivered += 1

            # ── Mise à jour planning ─────────────────────────────────────────
            _write("""
                UPDATE APP_UserSubscriptions
                SET last_sent=GETDATE(), next_send=?, updated_at=GETDATE()
                WHERE id=?
            """, (next_d, sub["id"]))

        except Exception as e:
            log_delivery(sub.get("id"), sub.get("user_email","?"), sub.get("report_nom","?"),
                         sub.get("channel","email"), "error", str(e)[:500])
            print(f"[SUBSCRIPTIONS] Erreur livraison #{sub.get('id')}: {e}")

    print(f"[SUBSCRIPTIONS] {delivered}/{len(due)} rapport(s) livrés")


def _build_subscription_email(report_name: str, freq_label: str, email: str, sub_id: int) -> str:
    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8">
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #333; margin:0; padding:0; }}
  .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
  .header {{ background: linear-gradient(135deg, #059669, #047857); color: white; padding: 24px; border-radius: 8px 8px 0 0; }}
  .content {{ background: #f9fafb; padding: 24px; border: 1px solid #e5e7eb; }}
  .badge {{ display: inline-block; background: #d1fae5; color: #065f46; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; }}
  .report-box {{ background: white; border-left: 4px solid #059669; padding: 16px; border-radius: 4px; margin: 16px 0; }}
  .report-name {{ font-size: 18px; font-weight: 700; color: #111; }}
  .unsubscribe {{ font-size: 11px; color: #9ca3af; text-align: center; margin-top: 12px; }}
  .footer {{ background: #f3f4f6; padding: 12px; text-align: center; font-size: 11px; color: #6b7280; border-radius: 0 0 8px 8px; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h2 style="margin:0;">OptiBoard — Rapport Abonnement</h2>
    <p style="margin:4px 0 0;opacity:.85;font-size:13px;">Livraison automatique de vos rapports</p>
  </div>
  <div class="content">
    <p>Bonjour,</p>
    <p>Voici votre rapport <span class="badge">{freq_label}</span> :</p>
    <div class="report-box">
      <div class="report-name">{report_name}</div>
      <p style="margin:6px 0 0;color:#6b7280;font-size:13px;">
        Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} • Fichier joint
      </p>
    </div>
    <p style="color:#6b7280;font-size:13px;">
      Vous recevez ce rapport car vous vous êtes abonné(e) à la fréquence <strong>{freq_label.lower()}</strong>.
    </p>
    <div class="unsubscribe">
      Pour vous désabonner, rendez-vous dans <strong>Mes Abonnements</strong> dans l'application.
    </div>
  </div>
  <div class="footer">OptiBoard — KAsoft Reporting • Ce message est généré automatiquement.</div>
</div>
</body>
</html>"""


# ==================== RECIPIENTS ROUTES ====================

@router.get("/{sub_id}/recipients")
async def get_recipients(sub_id: int):
    return {"success": True, "data": _get_recipients(sub_id)}


@router.post("/{sub_id}/recipients")
async def add_recipient(sub_id: int, body: RecipientIn):
    try:
        _init_recipients_table()
        _write(
            "INSERT INTO APP_SubscriptionRecipients (sub_id, nom, channel, contact_info) VALUES (?,?,?,?)",
            (sub_id, body.nom, body.channel, body.contact_info)
        )
        rows = execute_query(
            "SELECT TOP 1 * FROM APP_SubscriptionRecipients ORDER BY id DESC", use_cache=False
        )
        return {"success": True, "data": rows[0] if rows else None}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.delete("/{sub_id}/recipients/{r_id}")
async def delete_recipient(sub_id: int, r_id: int):
    try:
        _write("DELETE FROM APP_SubscriptionRecipients WHERE id=? AND sub_id=?", (r_id, sub_id))
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== DELIVER-NOW ====================

@router.post("/deliver-now")
async def deliver_now(background_tasks: BackgroundTasks):
    """Déclenche manuellement la livraison des abonnements échus."""
    background_tasks.add_task(deliver_due_subscriptions)
    return {"success": True, "message": "Livraison lancée en arrière-plan"}


# ==================== SEED DEMO ====================

@router.post("/seed-demo")
async def seed_demo_subscriptions():
    """Injecte des abonnements demo en base centrale."""
    try:
        init_subscription_tables()
        _write("DELETE FROM APP_UserSubscriptions")

        demo_subs = [
            ("direction@sg.ma",    "gridview",  1, "Tableau de bord Ventes",          "daily",   "excel"),
            ("direction@sg.ma",    "dashboard", 2, "Dashboard Recouvrement",           "weekly",  "pdf"),
            ("direction@sg.ma",    "pivot",     1, "Analyse CA par Gamme",             "monthly", "excel"),
            ("finance@sg.ma",      "gridview",  2, "Liste Créances en Attente",        "daily",   "excel"),
            ("finance@sg.ma",      "gridview",  3, "Rapport Balance Agée",             "weekly",  "excel"),
            ("recouvrement@sg.ma", "gridview",  4, "Suivi DSO Mensuel",                "monthly", "pdf"),
            ("recouvrement@sg.ma", "dashboard", 3, "Dashboard Impayés Critiques",      "weekly",  "pdf"),
            ("commercial@sg.ma",   "pivot",     2, "Performance Commerciale",          "monthly", "excel"),
            ("commercial@sg.ma",   "gridview",  5, "Top Clients par CA",               "weekly",  "excel"),
            ("admin@sg.ma",        "gridview",  1, "Tableau de bord Ventes",           "daily",   "excel"),
            ("admin@sg.ma",        "dashboard", 1, "Dashboard Exécutif",               "weekly",  "pdf"),
        ]

        inserted = 0
        for email, rtype, rid, nom, freq, fmt in demo_subs:
            next_d = _next_send_date(freq)
            _write("""
                INSERT INTO APP_UserSubscriptions
                    (user_email, report_type, report_id, report_nom, frequency, export_format, next_send)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (email, rtype, rid, nom, freq, fmt, next_d))
            inserted += 1

        return {"success": True, "inserted": inserted, "message": f"{inserted} abonnements demo créés"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== TEMPLATES EMAIL (PREVIEW) ====================

EMAIL_TEMPLATES = {
    "moderne": {
        "label": "Moderne",
        "description": "Design épuré avec dégradé coloré et icônes",
        "preview_color": "#6366f1",
    },
    "professionnel": {
        "label": "Professionnel",
        "description": "Style corporate classique, sobre et fiable",
        "preview_color": "#1e40af",
    },
    "minimaliste": {
        "label": "Minimaliste",
        "description": "Simple, lisible, focus sur le contenu",
        "preview_color": "#374151",
    },
    "alerte": {
        "label": "Rapport Alerte",
        "description": "Pour les rapports urgents avec indicateurs KPI",
        "preview_color": "#dc2626",
    },
}


def build_email_html(
    template: str,
    report_name: str,
    freq_label: str,
    date_str: str,
    app_name: str = "OptiBoard",
    color: str = "#6366f1",
    greeting: str = "Bonjour,",
    footer_text: str = "Ce message est généré automatiquement.",
) -> str:
    """Génère le HTML de l'email selon le template et la config personnalisée."""

    # Dériver une couleur foncée pour les dégradés
    def _darken(hex_color: str) -> str:
        try:
            h = hex_color.lstrip('#')
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            return '#{:02x}{:02x}{:02x}'.format(max(0, r - 30), max(0, g - 30), max(0, b - 30))
        except Exception:
            return hex_color
    dark = _darken(color)

    if template == "professionnel":
        return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
  body{{font-family:'Segoe UI',Arial,sans-serif;color:#1f2937;margin:0;padding:0;background:#f3f4f6}}
  .wrap{{max-width:600px;margin:0 auto;background:#fff;border:1px solid #d1d5db;border-radius:4px}}
  .hdr{{background:{color};color:#fff;padding:20px 28px;border-radius:4px 4px 0 0}}
  .hdr h1{{margin:0;font-size:20px;letter-spacing:.5px}}.hdr p{{margin:4px 0 0;font-size:12px;opacity:.75}}
  .body{{padding:28px}}.badge{{display:inline-block;background:#dbeafe;color:{color};
    padding:3px 12px;border-radius:3px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px}}
  .report-box{{border:1px solid #e5e7eb;border-left:4px solid {color};padding:16px;border-radius:4px;
    margin:18px 0;background:#f8fafc}}
  .report-title{{font-size:17px;font-weight:700;color:#111827}}
  .meta{{font-size:12px;color:#6b7280;margin-top:5px}}
  .divider{{border:none;border-top:1px solid #e5e7eb;margin:20px 0}}
  .footer{{background:#f9fafb;padding:14px;text-align:center;font-size:11px;color:#9ca3af;border-top:1px solid #e5e7eb;border-radius:0 0 4px 4px}}
</style></head>
<body><div class="wrap">
<div class="hdr"><h1>{app_name}</h1><p>Rapport automatique — Livraison planifiée</p></div>
<div class="body">
  <p>{greeting}</p>
  <p>Vous trouverez ci-joint votre rapport <span class="badge">{freq_label}</span> :</p>
  <div class="report-box">
    <div class="report-title">{report_name}</div>
    <div class="meta">Généré le {date_str} • Fichier joint à cet email</div>
  </div>
  <hr class="divider">
  <p style="font-size:13px;color:#6b7280">{footer_text}</p>
</div>
<div class="footer">{app_name} — Reporting Commercial • Message généré automatiquement</div>
</div></body></html>"""

    elif template == "minimaliste":
        return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
  body{{font-family:'Helvetica Neue',Arial,sans-serif;color:#374151;margin:0;padding:30px 0;background:#fff}}
  .wrap{{max-width:520px;margin:0 auto;padding:0 20px}}
  .logo{{font-size:13px;font-weight:700;color:{color};letter-spacing:1px;text-transform:uppercase;margin-bottom:28px}}
  h2{{font-size:22px;margin:0 0 6px;color:#111827}}.sub{{font-size:13px;color:#9ca3af;margin:0 0 24px}}
  .box{{background:#f9fafb;border-radius:6px;padding:18px;margin:20px 0;border-left:3px solid {color}}}
  .box-title{{font-weight:700;font-size:15px;margin:0 0 4px}}.box-meta{{font-size:12px;color:#9ca3af}}
  .tag{{display:inline-block;background:#f3f4f6;border-radius:3px;padding:2px 8px;font-size:11px;color:{color};font-weight:600}}
  hr{{border:none;border-top:1px solid #f3f4f6;margin:24px 0}}
  .footer{{font-size:11px;color:#d1d5db}}
</style></head>
<body><div class="wrap">
<div class="logo">{app_name}</div>
<h2>Votre rapport <span class="tag">{freq_label}</span></h2>
<p class="sub">Livraison automatique du {date_str}</p>
<div class="box">
  <div class="box-title">{report_name}</div>
  <div class="box-meta">Fichier joint • Généré le {date_str}</div>
</div>
<hr>
<p>{greeting}</p>
<p class="footer">{footer_text}</p>
</div></body></html>"""

    elif template == "alerte":
        return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
  body{{font-family:'Segoe UI',Arial,sans-serif;color:#1f2937;margin:0;padding:0;background:#fff9f9}}
  .wrap{{max-width:600px;margin:0 auto;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08)}}
  .hdr{{background:linear-gradient(135deg,{color},{dark});padding:22px 28px;color:#fff}}
  .hdr h1{{margin:0;font-size:18px}}.hdr p{{margin:4px 0 0;font-size:12px;opacity:.8}}
  .alert-banner{{background:#fef2f2;border-left:5px solid {color};padding:14px 20px;margin:18px;border-radius:4px}}
  .alert-banner strong{{font-size:15px;color:#7f1d1d}}.alert-banner p{{margin:4px 0 0;font-size:13px;color:#991b1b}}
  .body{{padding:0 28px 28px}}
  .footer{{background:#f3f4f6;padding:12px;text-align:center;font-size:11px;color:#9ca3af}}
</style></head>
<body><div class="wrap">
<div class="hdr"><h1>⚠ Rapport Alerte — {app_name}</h1><p>Indicateurs critiques détectés</p></div>
<div class="alert-banner">
  <strong>{report_name}</strong>
  <p>Rapport généré le {date_str} — {freq_label} — Fichier joint</p>
</div>
<div class="body">
  <p>{greeting}</p>
  <p>Ce rapport contient des indicateurs nécessitant votre attention immédiate.</p>
  <p style="font-size:13px;color:#6b7280">Consultez le fichier joint pour le détail complet des données.</p>
  <p style="font-size:12px;color:#9ca3af">{footer_text}</p>
</div>
<div class="footer">{app_name} — Alertes automatiques</div>
</div></body></html>"""

    else:  # moderne (default)
        return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
  body{{font-family:'Segoe UI',Arial,sans-serif;color:#374151;margin:0;padding:0;background:#f5f3ff}}
  .wrap{{max-width:600px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(99,102,241,.15)}}
  .hdr{{background:linear-gradient(135deg,{color},{dark});padding:28px;color:#fff;text-align:center}}
  .hdr .icon{{font-size:36px;margin-bottom:8px}}.hdr h1{{margin:0;font-size:22px;font-weight:700}}
  .hdr p{{margin:6px 0 0;font-size:13px;opacity:.85}}
  .badge{{display:inline-block;background:rgba(255,255,255,.2);color:#fff;padding:4px 14px;border-radius:20px;font-size:12px;font-weight:600}}
  .body{{padding:32px}}
  .report-card{{background:linear-gradient(135deg,#f5f3ff,#ede9fe);border-radius:10px;padding:20px;
    margin:20px 0;border:1px solid {color}40}}
  .report-card h2{{margin:0;font-size:17px;color:{color}}}.report-card p{{margin:6px 0 0;font-size:13px;color:{dark}}}
  .divider{{border:none;border-top:1px solid #f0f0f0;margin:24px 0}}
  .footer{{background:#f9fafb;padding:14px;text-align:center;font-size:11px;color:#9ca3af;border-top:1px solid #f0f0f0}}
</style></head>
<body><div class="wrap">
<div class="hdr">
  <div class="icon">📊</div>
  <h1>{app_name}</h1>
  <p>Votre rapport <span class="badge">{freq_label}</span> est prêt</p>
</div>
<div class="body">
  <p>{greeting}</p>
  <p>Votre rapport automatique a été généré avec succès :</p>
  <div class="report-card">
    <h2>{report_name}</h2>
    <p>📅 {date_str} — Fichier joint à cet email</p>
  </div>
  <hr class="divider">
  <p style="font-size:13px;color:#9ca3af">{footer_text}</p>
</div>
<div class="footer">{app_name} — KAsoft Reporting • Ce message est généré automatiquement</div>
</div></body></html>"""


_DEFAULT_TEMPLATE_CONFIG = {
    "template_defaut": "moderne",
    "nom_entreprise": "OptiBoard",
    "couleur_principale": "#6366f1",
    "logo_url": "",
    "texte_accueil": "Bonjour,",
    "texte_footer": "Ce message est généré automatiquement par OptiBoard.",
    "afficher_logo": False,
}

SETTING_KEY = "email_template_config"


def _get_template_config() -> dict:
    """Lit la config template depuis APP_Settings."""
    try:
        rows = execute_query(
            "SELECT setting_value FROM APP_Settings WHERE setting_key = ? AND dwh_code IS NULL",
            (SETTING_KEY,)
        )
        if rows and rows[0].get("setting_value"):
            saved = json.loads(rows[0]["setting_value"])
            return {**_DEFAULT_TEMPLATE_CONFIG, **saved}
    except Exception:
        pass
    return dict(_DEFAULT_TEMPLATE_CONFIG)


def _save_template_config(cfg: dict) -> None:
    rows = execute_query(
        "SELECT id FROM APP_Settings WHERE setting_key = ? AND dwh_code IS NULL",
        (SETTING_KEY,)
    )
    val = json.dumps(cfg, ensure_ascii=False)
    if rows:
        _write(
            "UPDATE APP_Settings SET setting_value=?, date_modification=GETDATE() WHERE setting_key=? AND dwh_code IS NULL",
            (val, SETTING_KEY)
        )
    else:
        _write(
            "INSERT INTO APP_Settings (setting_key, setting_value, setting_type, description) VALUES (?,?,?,?)",
            (SETTING_KEY, val, "json", "Configuration templates email abonnements")
        )


class TemplateConfigUpdate(BaseModel):
    template_defaut: Optional[str] = None
    nom_entreprise: Optional[str] = None
    couleur_principale: Optional[str] = None
    logo_url: Optional[str] = None
    texte_accueil: Optional[str] = None
    texte_footer: Optional[str] = None
    afficher_logo: Optional[bool] = None
    # Telegram
    telegram_bot_token: Optional[str] = None
    # WhatsApp (Twilio)
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_whatsapp_from: Optional[str] = None


class ChannelTestRequest(BaseModel):
    channel: str           # telegram | whatsapp
    contact_info: str      # chat_id ou numéro phone
    message: Optional[str] = None


@router.get("/email-templates")
async def get_email_templates():
    """Retourne la liste des templates email disponibles."""
    return {"success": True, "data": [
        {"key": k, **v} for k, v in EMAIL_TEMPLATES.items()
    ]}


@router.get("/email-templates/config")
async def get_template_config():
    """Retourne la configuration courante des templates email."""
    return {"success": True, "data": _get_template_config()}


@router.post("/email-templates/config")
async def save_template_config(body: TemplateConfigUpdate):
    """Sauvegarde la configuration des templates email."""
    current = _get_template_config()
    update = {k: v for k, v in body.dict().items() if v is not None}
    merged = {**current, **update}
    _save_template_config(merged)
    return {"success": True, "data": merged}


@router.get("/email-templates/{template_key}/preview")
async def preview_email_template(
    template_key: str,
    nom_entreprise: Optional[str] = None,
    couleur_principale: Optional[str] = None,
    texte_accueil: Optional[str] = None,
    texte_footer: Optional[str] = None,
):
    """Retourne le HTML d'un template email en mode preview (avec params live)."""
    if template_key not in EMAIL_TEMPLATES:
        return {"success": False, "error": "Template inconnu"}
    cfg = _get_template_config()
    app_name = nom_entreprise or cfg.get("nom_entreprise", "OptiBoard")
    color = couleur_principale or cfg.get("couleur_principale", "#6366f1")
    greeting = texte_accueil or cfg.get("texte_accueil", "Bonjour,")
    footer = texte_footer or cfg.get("texte_footer", "Ce message est généré automatiquement.")
    html = build_email_html(
        template=template_key,
        report_name="Tableau de Bord Ventes — Synthèse Mensuelle",
        freq_label="Mensuel",
        date_str="27/03/2026 à 07:00",
        app_name=app_name,
        color=color,
        greeting=greeting,
        footer_text=footer,
    )
    return {"success": True, "html": html, "template": template_key, **EMAIL_TEMPLATES[template_key]}


# ==================== CANAUX MESSAGING ====================

@router.get("/channels/config")
async def get_channels_config():
    """Retourne la config des canaux (tokens masqués)."""
    cfg = _get_template_config()
    return {
        "success": True,
        "data": {
            "telegram_configured": bool(cfg.get("telegram_bot_token")),
            "telegram_bot_token": _mask(cfg.get("telegram_bot_token", "")),
            "whatsapp_configured": bool(cfg.get("twilio_account_sid")),
            "twilio_account_sid":  cfg.get("twilio_account_sid", ""),
            "twilio_auth_token":   _mask(cfg.get("twilio_auth_token", "")),
            "twilio_whatsapp_from": cfg.get("twilio_whatsapp_from", ""),
        }
    }


@router.post("/channels/test")
async def test_channel(body: ChannelTestRequest):
    """Envoie un message de test sur le canal configuré."""
    cfg = _get_template_config()
    app_name = cfg.get("nom_entreprise", "OptiBoard")
    date_str = datetime.now().strftime('%d/%m/%Y à %H:%M')
    test_msg = body.message or f"✅ Message test de *{app_name}* — configuration OK ({date_str})"

    if body.channel == "telegram":
        token = cfg.get("telegram_bot_token", "")
        if not token:
            return {"success": False, "error": "Token Telegram non configuré"}
        ok = send_telegram_message(token, body.contact_info, test_msg)
        return {"success": ok, "error": None if ok else "Échec envoi — vérifiez le token et le chat_id"}

    elif body.channel == "whatsapp":
        sid = cfg.get("twilio_account_sid", "")
        tok = cfg.get("twilio_auth_token", "")
        frm = cfg.get("twilio_whatsapp_from", "")
        if not all([sid, tok, frm]):
            return {"success": False, "error": "Configuration Twilio incomplète"}
        ok = send_whatsapp_message(sid, tok, frm, body.contact_info, test_msg)
        return {"success": ok, "error": None if ok else "Échec envoi — vérifiez les credentials Twilio"}

    return {"success": False, "error": f"Canal inconnu: {body.channel}"}


@router.post("/channels/verify")
async def verify_channel_credentials(body: TemplateConfigUpdate):
    """Vérifie les credentials d'un canal sans les sauvegarder."""
    result = {}
    if body.telegram_bot_token:
        result["telegram"] = test_telegram_connection(body.telegram_bot_token)
    if body.twilio_account_sid and body.twilio_auth_token:
        result["whatsapp"] = test_whatsapp_connection(body.twilio_account_sid, body.twilio_auth_token)
    return {"success": True, "data": result}


def _mask(value: str) -> str:
    """Masque un token/secret en ne montrant que les 4 derniers caractères."""
    if not value or len(value) < 6:
        return "****"
    return "*" * (len(value) - 4) + value[-4:]


# ==================== TEMPLATES PERSONNALISÉS (CRUD) ====================

_TEMPLATE_VARS_SAMPLE = {
    "nom_app":   "OptiBoard",
    "rapport":   "Tableau de Bord Ventes",
    "frequence": "Mensuel",
    "date":      "27/03/2026 à 07:00",
}

_DEFAULT_MESSAGING_TEMPLATES = {
    "telegram": (
        "📊 *{nom_app}* — Rapport Automatique\n\n"
        "Bonjour 👋\n\n"
        "Votre rapport *{rapport}* est prêt.\n\n"
        "📅 Généré le {date}\n"
        "🔄 Fréquence : {frequence}\n\n"
        "_Message automatique — {nom_app}_"
    ),
    "whatsapp": (
        "📊 *{nom_app}* — Rapport Automatique\n\n"
        "Bonjour 👋\n\n"
        "Votre rapport *{rapport}* est prêt.\n\n"
        "📅 Généré le {date}\n"
        "🔄 Fréquence : {frequence}\n\n"
        "_Message automatique — {nom_app}_"
    ),
}


def _render_template(contenu: str, sample: bool = True) -> str:
    """Remplace les variables {nom_app}, {rapport}, {frequence}, {date}."""
    data = _TEMPLATE_VARS_SAMPLE if sample else {}
    try:
        return contenu.format(**data)
    except Exception:
        return contenu


class MessageTemplateCreate(BaseModel):
    nom: str
    channel: str          # email | telegram | whatsapp
    contenu: str
    is_default: bool = False


class MessageTemplateUpdate(BaseModel):
    nom: Optional[str] = None
    contenu: Optional[str] = None
    is_default: Optional[bool] = None


class TemplatePreviewRequest(BaseModel):
    channel: str
    contenu: str


@router.get("/message-templates")
async def list_message_templates(channel: Optional[str] = None):
    """Liste tous les templates personnalisés (filtrables par canal)."""
    _init_message_templates_table()
    try:
        if channel:
            rows = execute_query(
                "SELECT * FROM APP_MessageTemplates WHERE channel=? ORDER BY is_default DESC, created_at DESC",
                (channel,), use_cache=False
            )
        else:
            rows = execute_query(
                "SELECT * FROM APP_MessageTemplates ORDER BY channel, is_default DESC, created_at DESC",
                use_cache=False
            )
        return {"success": True, "data": rows}
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}


@router.post("/message-templates")
async def create_message_template(body: MessageTemplateCreate):
    """Crée un nouveau template personnalisé."""
    _init_message_templates_table()
    try:
        if body.is_default:
            _write(
                "UPDATE APP_MessageTemplates SET is_default=0, updated_at=GETDATE() WHERE channel=?",
                (body.channel,)
            )
        _write(
            """INSERT INTO APP_MessageTemplates (nom, channel, contenu, is_default)
               VALUES (?, ?, ?, ?)""",
            (body.nom, body.channel, body.contenu, 1 if body.is_default else 0)
        )
        rows = execute_query(
            "SELECT TOP 1 * FROM APP_MessageTemplates ORDER BY id DESC", use_cache=False
        )
        return {"success": True, "data": rows[0] if rows else None}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.put("/message-templates/{tpl_id}")
async def update_message_template(tpl_id: int, body: MessageTemplateUpdate):
    """Met à jour un template personnalisé."""
    try:
        updates, params = [], []
        if body.nom is not None:
            updates.append("nom=?"); params.append(body.nom)
        if body.contenu is not None:
            updates.append("contenu=?"); params.append(body.contenu)
        if body.is_default is not None:
            if body.is_default:
                rows = execute_query(
                    "SELECT channel FROM APP_MessageTemplates WHERE id=?", (tpl_id,), use_cache=False
                )
                if rows:
                    _write(
                        "UPDATE APP_MessageTemplates SET is_default=0, updated_at=GETDATE() WHERE channel=?",
                        (rows[0]["channel"],)
                    )
            updates.append("is_default=?"); params.append(1 if body.is_default else 0)
        if not updates:
            return {"success": False, "error": "Aucune modification"}
        updates.append("updated_at=GETDATE()")
        params.append(tpl_id)
        _write(f"UPDATE APP_MessageTemplates SET {', '.join(updates)} WHERE id=?", tuple(params))
        rows = execute_query(
            "SELECT * FROM APP_MessageTemplates WHERE id=?", (tpl_id,), use_cache=False
        )
        return {"success": True, "data": rows[0] if rows else None}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.delete("/message-templates/{tpl_id}")
async def delete_message_template(tpl_id: int):
    """Supprime un template personnalisé."""
    try:
        _write("DELETE FROM APP_MessageTemplates WHERE id=?", (tpl_id,))
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/message-templates/{tpl_id}/set-default")
async def set_default_template(tpl_id: int):
    """Définit un template comme défaut pour son canal."""
    try:
        rows = execute_query(
            "SELECT channel FROM APP_MessageTemplates WHERE id=?", (tpl_id,), use_cache=False
        )
        if not rows:
            return {"success": False, "error": "Template introuvable"}
        channel = rows[0]["channel"]
        _write(
            "UPDATE APP_MessageTemplates SET is_default=0, updated_at=GETDATE() WHERE channel=?",
            (channel,)
        )
        _write(
            "UPDATE APP_MessageTemplates SET is_default=1, updated_at=GETDATE() WHERE id=?",
            (tpl_id,)
        )
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/message-templates/preview")
async def preview_message_template(body: TemplatePreviewRequest):
    """Prévisualise un template avec des données d'exemple."""
    if body.channel == "email":
        html = build_email_html(
            template="moderne",
            report_name=_TEMPLATE_VARS_SAMPLE["rapport"],
            freq_label=_TEMPLATE_VARS_SAMPLE["frequence"],
            date_str=_TEMPLATE_VARS_SAMPLE["date"],
            app_name=_TEMPLATE_VARS_SAMPLE["nom_app"],
        )
        return {"success": True, "rendered": html, "type": "html"}
    rendered = _render_template(body.contenu)
    return {"success": True, "rendered": rendered, "type": "text"}
