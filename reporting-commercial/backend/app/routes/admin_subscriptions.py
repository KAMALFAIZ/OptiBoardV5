"""Administration des abonnements — logs de livraison, statistiques, actions manuelles."""
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta

from ..database_unified import execute_central as _read, write_central as _write

router = APIRouter(prefix="/api/admin/subscriptions", tags=["admin-subscriptions"])


# ==================== TABLE LOGS ====================

def init_delivery_logs_table():
    """Crée APP_DeliveryLogs si elle n'existe pas."""
    try:
        _write("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'APP_DeliveryLogs')
        CREATE TABLE APP_DeliveryLogs (
            id          INT IDENTITY(1,1) PRIMARY KEY,
            sub_id      INT            NULL,
            user_email  NVARCHAR(255)  NOT NULL,
            report_nom  NVARCHAR(255)  NOT NULL,
            channel     NVARCHAR(20)   NOT NULL DEFAULT 'email',
            status      NVARCHAR(20)   NOT NULL,   -- success | error | skipped
            error_msg   NVARCHAR(500)  NULL,
            sent_at     DATETIME       DEFAULT GETDATE()
        )
        """)
    except Exception as e:
        print(f"[ADMIN-SUBS] init_delivery_logs error: {e}")


def log_delivery(sub_id, user_email, report_nom, channel, status, error_msg=None):
    """Enregistre une tentative de livraison."""
    try:
        init_delivery_logs_table()
        _write(
            """INSERT INTO APP_DeliveryLogs (sub_id, user_email, report_nom, channel, status, error_msg)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (sub_id, user_email, report_nom, channel, status, error_msg)
        )
    except Exception as e:
        print(f"[ADMIN-SUBS] log_delivery error: {e}")


# ==================== STATS ====================

@router.get("/stats")
async def get_stats():
    """KPIs globaux : total abonnés, actifs, livrés aujourd'hui, échecs."""
    init_delivery_logs_table()
    try:
        total = _read("SELECT COUNT(*) AS n FROM APP_UserSubscriptions", use_cache=False)
        actifs = _read("SELECT COUNT(*) AS n FROM APP_UserSubscriptions WHERE is_active=1", use_cache=False)
        pauses = _read("SELECT COUNT(*) AS n FROM APP_UserSubscriptions WHERE is_active=0", use_cache=False)

        today_ok = _read(
            "SELECT COUNT(*) AS n FROM APP_DeliveryLogs WHERE status='success' AND CAST(sent_at AS DATE)=CAST(GETDATE() AS DATE)",
            use_cache=False
        )
        today_err = _read(
            "SELECT COUNT(*) AS n FROM APP_DeliveryLogs WHERE status='error' AND CAST(sent_at AS DATE)=CAST(GETDATE() AS DATE)",
            use_cache=False
        )
        total_logs = _read("SELECT COUNT(*) AS n FROM APP_DeliveryLogs WHERE status='success'", use_cache=False)

        by_channel = _read(
            """SELECT channel, COUNT(*) AS n FROM APP_UserSubscriptions
               WHERE is_active=1 GROUP BY channel""",
            use_cache=False
        )
        by_freq = _read(
            """SELECT frequency, COUNT(*) AS n FROM APP_UserSubscriptions
               WHERE is_active=1 GROUP BY frequency""",
            use_cache=False
        )
        next_due = _read(
            """SELECT TOP 5 user_email, report_nom, channel, next_send
               FROM APP_UserSubscriptions
               WHERE is_active=1 AND next_send IS NOT NULL
               ORDER BY next_send ASC""",
            use_cache=False
        )

        return {
            "success": True,
            "data": {
                "total":       total[0]["n"]     if total     else 0,
                "actifs":      actifs[0]["n"]    if actifs    else 0,
                "pauses":      pauses[0]["n"]    if pauses    else 0,
                "today_ok":    today_ok[0]["n"]  if today_ok  else 0,
                "today_err":   today_err[0]["n"] if today_err else 0,
                "total_sent":  total_logs[0]["n"] if total_logs else 0,
                "by_channel":  {r["channel"]: r["n"] for r in by_channel},
                "by_freq":     {r["frequency"]: r["n"] for r in by_freq},
                "next_due":    next_due,
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== LISTE ADMIN ====================

@router.get("")
async def list_all_subscriptions(
    channel: Optional[str] = None,
    frequency: Optional[str] = None,
    is_active: Optional[int] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
):
    """Liste tous les abonnements avec filtres + pagination."""
    try:
        where, params = ["1=1"], []

        if channel:
            where.append("channel=?"); params.append(channel)
        if frequency:
            where.append("frequency=?"); params.append(frequency)
        if is_active is not None:
            where.append("is_active=?"); params.append(is_active)
        if search:
            where.append("(user_email LIKE ? OR report_nom LIKE ?)")
            params += [f"%{search}%", f"%{search}%"]

        w = " AND ".join(where)
        offset = (page - 1) * page_size

        count = _read(
            f"SELECT COUNT(*) AS n FROM APP_UserSubscriptions WHERE {w}",
            tuple(params), use_cache=False
        )
        rows = _read(
            f"""SELECT * FROM APP_UserSubscriptions
                WHERE {w}
                ORDER BY created_at DESC
                OFFSET {offset} ROWS FETCH NEXT {page_size} ROWS ONLY""",
            tuple(params) if params else None, use_cache=False
        )
        return {
            "success": True,
            "data": rows,
            "total": count[0]["n"] if count else 0,
            "page": page,
            "page_size": page_size,
        }
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}


# ==================== LOGS ====================

@router.get("/logs")
async def get_delivery_logs(
    sub_id: Optional[int] = None,
    channel: Optional[str] = None,
    status: Optional[str] = None,
    days: int = 7,
    page: int = 1,
    page_size: int = 30,
):
    """Historique des livraisons avec filtres."""
    init_delivery_logs_table()
    try:
        where = ["sent_at >= DATEADD(day, ?, GETDATE())"]
        params = [-days]

        if sub_id:
            where.append("sub_id=?"); params.append(sub_id)
        if channel:
            where.append("channel=?"); params.append(channel)
        if status:
            where.append("status=?"); params.append(status)

        w = " AND ".join(where)
        offset = (page - 1) * page_size

        count = _read(
            f"SELECT COUNT(*) AS n FROM APP_DeliveryLogs WHERE {w}",
            tuple(params), use_cache=False
        )
        rows = _read(
            f"""SELECT * FROM APP_DeliveryLogs
                WHERE {w}
                ORDER BY sent_at DESC
                OFFSET {offset} ROWS FETCH NEXT {page_size} ROWS ONLY""",
            tuple(params), use_cache=False
        )
        return {
            "success": True,
            "data": rows,
            "total": count[0]["n"] if count else 0,
        }
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}


@router.get("/logs/summary")
async def get_logs_summary(days: int = 30):
    """Résumé quotidien des livraisons (pour graphique)."""
    init_delivery_logs_table()
    try:
        rows = _read(
            """SELECT
                CAST(sent_at AS DATE) AS day,
                SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) AS success,
                SUM(CASE WHEN status='error'   THEN 1 ELSE 0 END) AS errors
               FROM APP_DeliveryLogs
               WHERE sent_at >= DATEADD(day, ?, GETDATE())
               GROUP BY CAST(sent_at AS DATE)
               ORDER BY day ASC""",
            (-days,), use_cache=False
        )
        return {"success": True, "data": rows}
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}


# ==================== ACTIONS ====================

class RescheduleBody(BaseModel):
    next_send: str   # ISO datetime string


@router.post("/{sub_id}/deliver-now")
async def admin_deliver_now(sub_id: int, background_tasks: BackgroundTasks):
    """Force la livraison immédiate d'un abonnement."""
    from .subscriptions import deliver_due_subscriptions
    from ..database_unified import execute_central

    try:
        rows = _read(
            "SELECT * FROM APP_UserSubscriptions WHERE id=?", (sub_id,), use_cache=False
        )
        if not rows:
            return {"success": False, "error": "Abonnement introuvable"}

        # Forcer next_send dans le passé pour qu'il soit traité
        _write(
            "UPDATE APP_UserSubscriptions SET next_send=DATEADD(hour,-1,GETDATE()), updated_at=GETDATE() WHERE id=?",
            (sub_id,)
        )
        background_tasks.add_task(deliver_due_subscriptions)
        return {"success": True, "message": f"Livraison lancée pour l'abonnement #{sub_id}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.put("/{sub_id}/reschedule")
async def reschedule_subscription(sub_id: int, body: RescheduleBody):
    """Reprogramme la prochaine livraison d'un abonnement."""
    try:
        dt = datetime.fromisoformat(body.next_send.replace("Z", ""))
        _write(
            "UPDATE APP_UserSubscriptions SET next_send=?, updated_at=GETDATE() WHERE id=?",
            (dt, sub_id)
        )
        return {"success": True, "next_send": dt.strftime("%d/%m/%Y à %H:%M")}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.put("/{sub_id}/toggle")
async def admin_toggle(sub_id: int):
    """Active/désactive un abonnement (admin)."""
    try:
        _write(
            """UPDATE APP_UserSubscriptions
               SET is_active=CASE WHEN is_active=1 THEN 0 ELSE 1 END, updated_at=GETDATE()
               WHERE id=?""",
            (sub_id,)
        )
        rows = _read(
            "SELECT is_active FROM APP_UserSubscriptions WHERE id=?", (sub_id,), use_cache=False
        )
        return {"success": True, "is_active": rows[0]["is_active"] if rows else None}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.delete("/{sub_id}")
async def admin_delete(sub_id: int):
    """Supprime définitivement un abonnement (admin)."""
    try:
        _write("DELETE FROM APP_UserSubscriptions WHERE id=?", (sub_id,))
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/deliver-all")
async def deliver_all_due(background_tasks: BackgroundTasks):
    """Déclenche manuellement la livraison de tous les abonnements échus."""
    from .subscriptions import deliver_due_subscriptions
    background_tasks.add_task(deliver_due_subscriptions)
    return {"success": True, "message": "Livraison globale lancée en arrière-plan"}
