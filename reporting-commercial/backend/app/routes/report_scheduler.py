"""Routes pour la gestion des rapports programmes et envoi par email"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, date as date_type
import json
import os
import tempfile

from ..database_unified import execute_client as execute_query, client_cursor as get_db_cursor
# Report Scheduler : 100% client local — aucune lecture/ecriture vers le central
from ..services.email_service import send_email, test_email_config, get_email_template

router = APIRouter(prefix="/api/report-scheduler", tags=["report-scheduler"])


# ==================== SCHEMAS ====================

class EmailConfigCreate(BaseModel):
    smtp_host: str
    smtp_port: int = 587
    smtp_user: str
    smtp_password: str
    sender_name: str = "Reporting KAsoft"
    use_ssl: bool = True
    use_tls: bool = False
    is_active: bool = True


class ScheduleCreate(BaseModel):
    nom: str
    description: Optional[str] = None
    report_type: str  # pivot, gridview, dashboard, export
    report_id: Optional[int] = None
    export_format: str = "excel"  # excel, pdf, csv
    frequency: str  # daily, weekly, monthly, once
    schedule_time: str = "08:00"  # HH:MM
    schedule_day: Optional[int] = None  # 1-7 pour weekly, 1-31 pour monthly
    recipients: List[str]  # Liste d'emails
    cc_recipients: Optional[List[str]] = None
    filters: Optional[Dict[str, Any]] = None  # Filtres a appliquer
    is_active: bool = True
    date_debut: Optional[str] = None
    date_fin: Optional[str] = None
    tags: Optional[str] = None
    objet_email: Optional[str] = None
    message_email: Optional[str] = None


class ScheduleUpdate(BaseModel):
    nom: Optional[str] = None
    description: Optional[str] = None
    report_type: Optional[str] = None
    report_id: Optional[int] = None
    export_format: Optional[str] = None
    frequency: Optional[str] = None
    schedule_time: Optional[str] = None
    schedule_day: Optional[int] = None
    recipients: Optional[List[str]] = None
    cc_recipients: Optional[List[str]] = None
    filters: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    date_debut: Optional[str] = None
    date_fin: Optional[str] = None
    tags: Optional[str] = None
    objet_email: Optional[str] = None
    message_email: Optional[str] = None


class SendNowRequest(BaseModel):
    recipients: List[str]
    cc_recipients: Optional[List[str]] = None
    subject: Optional[str] = None
    message: Optional[str] = None


# ==================== INIT TABLES ====================

def init_scheduler_tables():
    """Initialise les tables necessaires pour le scheduler"""
    tables_sql = [
        # Configuration email
        """
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'APP_EmailConfig')
        CREATE TABLE APP_EmailConfig (
            id INT IDENTITY(1,1) PRIMARY KEY,
            smtp_host NVARCHAR(255) NOT NULL,
            smtp_port INT DEFAULT 587,
            smtp_user NVARCHAR(255) NOT NULL,
            smtp_password NVARCHAR(255) NOT NULL,
            sender_name NVARCHAR(255) DEFAULT 'Reporting',
            use_ssl BIT DEFAULT 1,
            use_tls BIT DEFAULT 0,
            is_active BIT DEFAULT 1,
            created_at DATETIME DEFAULT GETDATE(),
            updated_at DATETIME DEFAULT GETDATE()
        )
        """,
        # Schedules de rapports
        """
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'APP_ReportSchedules')
        CREATE TABLE APP_ReportSchedules (
            id INT IDENTITY(1,1) PRIMARY KEY,
            nom NVARCHAR(255) NOT NULL,
            description NVARCHAR(MAX),
            report_type NVARCHAR(50) NOT NULL,
            report_id INT,
            export_format NVARCHAR(20) DEFAULT 'excel',
            frequency NVARCHAR(20) NOT NULL,
            schedule_time NVARCHAR(10) DEFAULT '08:00',
            schedule_day INT,
            recipients NVARCHAR(MAX) NOT NULL,
            cc_recipients NVARCHAR(MAX),
            filters NVARCHAR(MAX),
            is_active BIT DEFAULT 1,
            last_run DATETIME,
            next_run DATETIME,
            created_by INT,
            created_at DATETIME DEFAULT GETDATE(),
            updated_at DATETIME DEFAULT GETDATE()
        )
        """,
        # Historique des envois
        """
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'APP_ReportHistory')
        CREATE TABLE APP_ReportHistory (
            id INT IDENTITY(1,1) PRIMARY KEY,
            schedule_id INT,
            report_name NVARCHAR(255),
            recipients NVARCHAR(MAX),
            status NVARCHAR(20) NOT NULL,
            error_message NVARCHAR(MAX),
            file_path NVARCHAR(500),
            file_size INT,
            sent_at DATETIME DEFAULT GETDATE(),
            FOREIGN KEY (schedule_id) REFERENCES APP_ReportSchedules(id) ON DELETE SET NULL
        )
        """
    ]

    # Scripts pour ajouter les colonnes manquantes sur tables existantes
    alter_scripts = [
        """
        IF EXISTS (SELECT * FROM sys.tables WHERE name = 'APP_ReportSchedules')
        AND NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('APP_ReportSchedules') AND name = 'is_active')
        BEGIN
            ALTER TABLE APP_ReportSchedules ADD is_active BIT DEFAULT 1
        END
        """,
        """
        IF EXISTS (SELECT * FROM sys.tables WHERE name = 'APP_ReportSchedules')
        BEGIN
            UPDATE APP_ReportSchedules SET is_active = 1 WHERE is_active IS NULL
        END
        """,
        # Nouvelles colonnes enrichies
        """
        IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id=OBJECT_ID('APP_ReportSchedules') AND name='date_debut')
            ALTER TABLE APP_ReportSchedules ADD date_debut DATE NULL
        """,
        """
        IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id=OBJECT_ID('APP_ReportSchedules') AND name='date_fin')
            ALTER TABLE APP_ReportSchedules ADD date_fin DATE NULL
        """,
        """
        IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id=OBJECT_ID('APP_ReportSchedules') AND name='tags')
            ALTER TABLE APP_ReportSchedules ADD tags NVARCHAR(255) NULL
        """,
        """
        IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id=OBJECT_ID('APP_ReportSchedules') AND name='objet_email')
            ALTER TABLE APP_ReportSchedules ADD objet_email NVARCHAR(500) NULL
        """,
        """
        IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id=OBJECT_ID('APP_ReportSchedules') AND name='message_email')
            ALTER TABLE APP_ReportSchedules ADD message_email NVARCHAR(MAX) NULL
        """,
        """
        IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id=OBJECT_ID('APP_ReportSchedules') AND name='run_count')
            ALTER TABLE APP_ReportSchedules ADD run_count INT NOT NULL DEFAULT 0
        """,
        """
        IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id=OBJECT_ID('APP_ReportSchedules') AND name='success_count')
            ALTER TABLE APP_ReportSchedules ADD success_count INT NOT NULL DEFAULT 0
        """,
    ]

    try:
        with get_db_cursor() as cursor:
            for sql in tables_sql:
                cursor.execute(sql)
            # Appliquer les migrations pour colonnes manquantes
            for sql in alter_scripts:
                try:
                    cursor.execute(sql)
                except:
                    pass
        return True
    except Exception as e:
        print(f"Erreur init tables scheduler: {e}")
        return False


# ==================== EMAIL CONFIG ====================

@router.get("/email-config")
async def get_email_config():
    """Recupere la configuration email active"""
    try:
        results = execute_query(
            """SELECT id,
                      smtp_server AS smtp_host, smtp_port,
                      smtp_username AS smtp_user, from_name AS sender_name,
                      use_ssl, use_tls, actif AS is_active, date_modification
               FROM APP_EmailConfig ORDER BY id DESC""",
            use_cache=False
        )
        # Ne pas retourner le mot de passe
        return {"success": True, "data": results[0] if results else None}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/email-config")
async def save_email_config(config: EmailConfigCreate):
    """Sauvegarde la configuration email"""
    try:
        init_scheduler_tables()

        with get_db_cursor() as cursor:
            # Desactiver les anciennes configs
            cursor.execute("UPDATE APP_EmailConfig SET actif = 0")

            # Inserer la nouvelle config
            cursor.execute("""
                INSERT INTO APP_EmailConfig (smtp_server, smtp_port, smtp_username, smtp_password, from_email, from_name, use_ssl, use_tls, actif)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (config.smtp_host, config.smtp_port, config.smtp_user, config.smtp_password,
                  config.smtp_user, config.sender_name, config.use_ssl, config.use_tls, 1 if config.is_active else 0))

        return {"success": True, "message": "Configuration email sauvegardee"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/email-config/test")
async def test_email_configuration(config: EmailConfigCreate):
    """Teste une configuration email"""
    result = test_email_config({
        "smtp_host": config.smtp_host,
        "smtp_port": config.smtp_port,
        "smtp_user": config.smtp_user,
        "smtp_password": config.smtp_password,
        "use_ssl": config.use_ssl,
        "use_tls": config.use_tls
    })
    return result


@router.post("/email-config/send-test")
async def send_test_email(to_email: str):
    """Envoie un email de test"""
    html_content = get_email_template("test_email", {
        "sent_at": datetime.now().strftime("%d/%m/%Y %H:%M")
    })

    result = send_email(
        to_emails=[to_email],
        subject="Test Configuration Email - KAsoft",
        body_html=html_content
    )
    return result


# ==================== SCHEDULES CRUD ====================

@router.get("/schedules")
async def get_all_schedules():
    """Recupere tous les schedules"""
    try:
        init_scheduler_tables()

        results = execute_query("""
            SELECT s.id, s.nom, s.description, s.report_type, s.report_id,
                   s.export_format, s.frequency, s.schedule_time, s.schedule_day,
                   s.recipients, s.cc_recipients, s.filters, s.is_active,
                   s.last_run, s.next_run, s.created_at, s.updated_at,
                   s.date_debut, s.date_fin, s.tags, s.objet_email,
                   ISNULL(s.run_count, 0) AS run_count,
                   ISNULL(s.success_count, 0) AS success_count,
                   CASE
                       WHEN s.report_type = 'pivot' THEN (SELECT nom FROM APP_Pivots WHERE id = s.report_id)
                       WHEN s.report_type = 'gridview' THEN (SELECT nom FROM APP_GridViews WHERE id = s.report_id)
                       WHEN s.report_type = 'dashboard' THEN (SELECT nom FROM APP_Dashboards WHERE id = s.report_id)
                       ELSE NULL
                   END as report_name,
                   (SELECT COUNT(*) FROM APP_ReportHistory WHERE schedule_id = s.id) as total_sent,
                   (SELECT MAX(sent_at) FROM APP_ReportHistory WHERE schedule_id = s.id AND status = 'success') as last_success
            FROM APP_ReportSchedules s
            ORDER BY s.is_active DESC, s.nom
        """, use_cache=False)

        # Parser les JSON
        for r in results:
            if r.get('recipients'):
                r['recipients'] = json.loads(r['recipients'])
            if r.get('cc_recipients'):
                r['cc_recipients'] = json.loads(r['cc_recipients'])
            if r.get('filters'):
                r['filters'] = json.loads(r['filters'])

        return {"success": True, "data": results}
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}


@router.get("/schedules/{schedule_id}")
async def get_schedule(schedule_id: int):
    """Recupere un schedule par ID"""
    try:
        results = execute_query(
            "SELECT * FROM APP_ReportSchedules WHERE id = ?",
            (schedule_id,),
            use_cache=False
        )
        if not results:
            raise HTTPException(status_code=404, detail="Schedule non trouve")

        schedule = results[0]
        if schedule.get('recipients'):
            schedule['recipients'] = json.loads(schedule['recipients'])
        if schedule.get('cc_recipients'):
            schedule['cc_recipients'] = json.loads(schedule['cc_recipients'])
        if schedule.get('filters'):
            schedule['filters'] = json.loads(schedule['filters'])

        return {"success": True, "data": schedule}
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/schedules")
async def create_schedule(schedule: ScheduleCreate):
    """Cree un nouveau schedule"""
    try:
        init_scheduler_tables()

        # Calculer le prochain run
        next_run = calculate_next_run(schedule.frequency, schedule.schedule_time, schedule.schedule_day)

        with get_db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO APP_ReportSchedules
                (nom, description, report_type, report_id, export_format, frequency, schedule_time, schedule_day,
                 recipients, cc_recipients, filters, is_active, next_run,
                 date_debut, date_fin, tags, objet_email, message_email)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                schedule.nom, schedule.description, schedule.report_type, schedule.report_id,
                schedule.export_format, schedule.frequency, schedule.schedule_time, schedule.schedule_day,
                json.dumps(schedule.recipients), json.dumps(schedule.cc_recipients) if schedule.cc_recipients else None,
                json.dumps(schedule.filters) if schedule.filters else None, schedule.is_active, next_run,
                schedule.date_debut, schedule.date_fin, schedule.tags, schedule.objet_email, schedule.message_email
            ))

            cursor.execute("SELECT @@IDENTITY AS id")
            new_id = cursor.fetchone()[0]

        return {"success": True, "id": new_id, "message": "Schedule cree avec succes"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.put("/schedules/{schedule_id}")
async def update_schedule(schedule_id: int, schedule: ScheduleUpdate):
    """Met a jour un schedule"""
    try:
        updates = []
        params = []

        if schedule.nom is not None:
            updates.append("nom = ?")
            params.append(schedule.nom)
        if schedule.description is not None:
            updates.append("description = ?")
            params.append(schedule.description)
        if schedule.report_type is not None:
            updates.append("report_type = ?")
            params.append(schedule.report_type)
        if schedule.report_id is not None:
            updates.append("report_id = ?")
            params.append(schedule.report_id)
        if schedule.export_format is not None:
            updates.append("export_format = ?")
            params.append(schedule.export_format)
        if schedule.frequency is not None:
            updates.append("frequency = ?")
            params.append(schedule.frequency)
        if schedule.schedule_time is not None:
            updates.append("schedule_time = ?")
            params.append(schedule.schedule_time)
        if schedule.schedule_day is not None:
            updates.append("schedule_day = ?")
            params.append(schedule.schedule_day)
        if schedule.recipients is not None:
            updates.append("recipients = ?")
            params.append(json.dumps(schedule.recipients))
        if schedule.cc_recipients is not None:
            updates.append("cc_recipients = ?")
            params.append(json.dumps(schedule.cc_recipients))
        if schedule.filters is not None:
            updates.append("filters = ?")
            params.append(json.dumps(schedule.filters))
        if schedule.is_active is not None:
            updates.append("is_active = ?")
            params.append(schedule.is_active)
        if schedule.date_debut is not None:
            updates.append("date_debut = ?")
            params.append(schedule.date_debut)
        if schedule.date_fin is not None:
            updates.append("date_fin = ?")
            params.append(schedule.date_fin)
        if schedule.tags is not None:
            updates.append("tags = ?")
            params.append(schedule.tags)
        if schedule.objet_email is not None:
            updates.append("objet_email = ?")
            params.append(schedule.objet_email)
        if schedule.message_email is not None:
            updates.append("message_email = ?")
            params.append(schedule.message_email)

        updates.append("updated_at = GETDATE()")

        if not updates:
            return {"success": False, "error": "Aucune modification"}

        params.append(schedule_id)

        with get_db_cursor() as cursor:
            cursor.execute(f"UPDATE APP_ReportSchedules SET {', '.join(updates)} WHERE id = ?", params)

        # Recalculer next_run si necessaire
        if any(x is not None for x in [schedule.frequency, schedule.schedule_time, schedule.schedule_day]):
            current = execute_query("SELECT frequency, schedule_time, schedule_day FROM APP_ReportSchedules WHERE id = ?", (schedule_id,), use_cache=False)
            if current:
                next_run = calculate_next_run(current[0]['frequency'], current[0]['schedule_time'], current[0]['schedule_day'])
                with get_db_cursor() as cursor:
                    cursor.execute("UPDATE APP_ReportSchedules SET next_run = ? WHERE id = ?", (next_run, schedule_id))

        return {"success": True, "message": "Schedule mis a jour"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/schedules/{schedule_id}/duplicate")
async def duplicate_schedule(schedule_id: int):
    """Duplique un schedule existant"""
    try:
        orig = execute_query("SELECT * FROM APP_ReportSchedules WHERE id=?", (schedule_id,), use_cache=False)
        if not orig:
            raise HTTPException(404, "Schedule non trouve")
        s = orig[0]
        next_run = calculate_next_run(s['frequency'], s['schedule_time'], s['schedule_day'])
        with get_db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO APP_ReportSchedules
                (nom, description, report_type, report_id, export_format, frequency, schedule_time, schedule_day,
                 recipients, cc_recipients, filters, is_active, next_run, date_debut, date_fin, tags, objet_email, message_email)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,0,?,?,?,?,?,?)
            """, (
                f"Copie - {s['nom']}", s['description'], s['report_type'], s['report_id'],
                s['export_format'], s['frequency'], s['schedule_time'], s['schedule_day'],
                s['recipients'], s['cc_recipients'], s['filters'], next_run,
                s.get('date_debut'), s.get('date_fin'), s.get('tags'), s.get('objet_email'), s.get('message_email')
            ))
            cursor.execute("SELECT @@IDENTITY AS id")
            new_id = cursor.fetchone()[0]
        return {"success": True, "id": new_id}
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.delete("/schedules/{schedule_id}")
async def delete_schedule(schedule_id: int):
    """Supprime un schedule"""
    try:
        with get_db_cursor() as cursor:
            # Supprimer l'historique associe
            cursor.execute("DELETE FROM APP_ReportHistory WHERE schedule_id = ?", (schedule_id,))
            # Supprimer le schedule
            cursor.execute("DELETE FROM APP_ReportSchedules WHERE id = ?", (schedule_id,))

        return {"success": True, "message": "Schedule supprime"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/schedules/{schedule_id}/toggle")
async def toggle_schedule(schedule_id: int):
    """Active/desactive un schedule"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                UPDATE APP_ReportSchedules
                SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END,
                    updated_at = GETDATE()
                WHERE id = ?
            """, (schedule_id,))

        result = execute_query("SELECT is_active FROM APP_ReportSchedules WHERE id = ?", (schedule_id,), use_cache=False)
        new_status = result[0]['is_active'] if result else None

        return {"success": True, "is_active": new_status}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== EXECUTION ====================

@router.post("/schedules/{schedule_id}/run-now")
async def run_schedule_now(schedule_id: int, background_tasks: BackgroundTasks):
    """Execute immediatement un schedule"""
    try:
        schedule = execute_query(
            "SELECT * FROM APP_ReportSchedules WHERE id = ?",
            (schedule_id,),
            use_cache=False
        )
        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule non trouve")

        schedule = schedule[0]
        schedule['recipients'] = json.loads(schedule['recipients']) if schedule.get('recipients') else []
        schedule['cc_recipients'] = json.loads(schedule['cc_recipients']) if schedule.get('cc_recipients') else None
        schedule['filters'] = json.loads(schedule['filters']) if schedule.get('filters') else None

        # Executer en arriere-plan
        background_tasks.add_task(execute_schedule, schedule)

        return {"success": True, "message": "Execution lancee en arriere-plan"}
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/send-report")
async def send_report_now(
    report_type: str,
    report_id: int,
    export_format: str,
    request: SendNowRequest,
    background_tasks: BackgroundTasks
):
    """Envoie immediatement un rapport par email"""
    try:
        # Creer un schedule temporaire
        temp_schedule = {
            "id": None,
            "nom": f"Envoi manuel - {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            "report_type": report_type,
            "report_id": report_id,
            "export_format": export_format,
            "recipients": request.recipients,
            "cc_recipients": request.cc_recipients,
            "filters": None
        }

        background_tasks.add_task(execute_schedule, temp_schedule, request.subject, request.message)

        return {"success": True, "message": f"Envoi en cours vers {len(request.recipients)} destinataire(s)"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== HISTORY ====================

@router.get("/history")
async def get_history(limit: int = 100, schedule_id: Optional[int] = None, status: Optional[str] = None):
    """Recupere l'historique des envois"""
    try:
        query = """
            SELECT h.*, s.nom as schedule_name
            FROM APP_ReportHistory h
            LEFT JOIN APP_ReportSchedules s ON h.schedule_id = s.id
        """
        params = []
        conditions = []

        if schedule_id:
            conditions.append("h.schedule_id = ?")
            params.append(schedule_id)

        if status:
            conditions.append("h.status = ?")
            params.append(status)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += f" ORDER BY h.sent_at DESC OFFSET 0 ROWS FETCH NEXT {limit} ROWS ONLY"

        results = execute_query(query, tuple(params) if params else None, use_cache=False)

        for r in results:
            if r.get('recipients'):
                r['recipients'] = json.loads(r['recipients'])

        return {"success": True, "data": results}
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}


@router.get("/history/stats")
async def get_history_stats():
    """Statistiques des envois enrichies"""
    try:
        global_stats = execute_query("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) as success,
                SUM(CASE WHEN status='error' THEN 1 ELSE 0 END) as errors,
                COUNT(DISTINCT schedule_id) as schedules_used
            FROM APP_ReportHistory WHERE sent_at >= DATEADD(day,-30,GETDATE())
        """, use_cache=False)

        per_schedule = execute_query("""
            SELECT h.schedule_id, s.nom,
                COUNT(*) as total,
                SUM(CASE WHEN h.status='success' THEN 1 ELSE 0 END) as success
            FROM APP_ReportHistory h
            JOIN APP_ReportSchedules s ON h.schedule_id = s.id
            WHERE h.sent_at >= DATEADD(day,-30,GETDATE())
            GROUP BY h.schedule_id, s.nom
            ORDER BY total DESC
        """, use_cache=False)

        trend = execute_query("""
            SELECT CAST(sent_at AS DATE) as day,
                COUNT(*) as total,
                SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) as success
            FROM APP_ReportHistory
            WHERE sent_at >= DATEADD(day,-7,GETDATE())
            GROUP BY CAST(sent_at AS DATE)
            ORDER BY day
        """, use_cache=False)

        return {"success": True, "data": {
            "global": global_stats[0] if global_stats else {},
            "per_schedule": per_schedule,
            "trend": trend
        }}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== HELPERS ====================

def calculate_next_run(frequency: str, schedule_time: str, schedule_day: Optional[int] = None) -> datetime:
    """Calcule la prochaine execution"""
    now = datetime.now()
    hour, minute = map(int, schedule_time.split(':'))

    if frequency == 'once':
        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)

    elif frequency == 'daily':
        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)

    elif frequency == 'weekly':
        day = schedule_day or 1  # 1 = Lundi
        days_ahead = day - now.isoweekday()
        if days_ahead <= 0:
            days_ahead += 7
        next_run = now + timedelta(days=days_ahead)
        next_run = next_run.replace(hour=hour, minute=minute, second=0, microsecond=0)

    elif frequency == 'monthly':
        day = schedule_day or 1
        next_run = now.replace(day=day, hour=hour, minute=minute, second=0, microsecond=0)
        if next_run <= now:
            if now.month == 12:
                next_run = next_run.replace(year=now.year + 1, month=1)
            else:
                next_run = next_run.replace(month=now.month + 1)

    else:
        next_run = now + timedelta(hours=1)

    return next_run


async def execute_schedule(schedule: dict, custom_subject: str = None, custom_message: str = None):
    """Execute un schedule et envoie le rapport par email"""
    from .export import generate_report_file

    status = 'error'
    error_message = None
    file_path = None
    file_size = 0

    # Verifier la periode de validite du schedule
    today = datetime.now().date()
    date_debut = schedule.get('date_debut')
    date_fin = schedule.get('date_fin')
    if date_debut:
        dd = date_debut if isinstance(date_debut, date_type) else datetime.fromisoformat(str(date_debut)).date()
        if today < dd:
            return  # pas encore commence
    if date_fin:
        df = date_fin if isinstance(date_fin, date_type) else datetime.fromisoformat(str(date_fin)).date()
        if today > df:
            # auto-desactiver
            try:
                with get_db_cursor() as cursor:
                    cursor.execute("UPDATE APP_ReportSchedules SET is_active=0 WHERE id=?", (schedule.get('id'),))
            except Exception as e:
                print(f"Erreur desactivation schedule expire: {e}")
            return

    try:
        # Generer le fichier de rapport
        report_result = await generate_report_file(
            report_type=schedule['report_type'],
            report_id=schedule['report_id'],
            export_format=schedule['export_format'],
            filters=schedule.get('filters')
        )

        if not report_result.get('success'):
            raise Exception(report_result.get('error', 'Erreur generation rapport'))

        file_path = report_result['file_path']
        file_size = os.path.getsize(file_path) if file_path and os.path.exists(file_path) else 0
        report_name = report_result.get('report_name', schedule['nom'])

        # Preparer l'email
        subject = custom_subject or schedule.get('objet_email') or f"Rapport: {report_name} - {datetime.now().strftime('%d/%m/%Y')}"
        message_body = custom_message or schedule.get('message_email')

        html_content = get_email_template("report_delivery", {
            "title": subject,
            "report_name": report_name,
            "report_type": schedule['report_type'].capitalize(),
            "period": schedule.get('filters', {}).get('period', 'Non specifie') if schedule.get('filters') else 'Non specifie',
            "generated_at": datetime.now().strftime("%d/%m/%Y %H:%M")
        })

        if message_body:
            html_content = html_content.replace("</div>\n        <div class=\"content\">", f"</div>\n        <div class=\"content\"><p>{message_body}</p>")

        # Envoyer l'email
        email_result = send_email(
            to_emails=schedule['recipients'],
            subject=subject,
            body_html=html_content,
            attachments=[file_path] if file_path else None,
            cc_emails=schedule.get('cc_recipients')
        )

        if email_result.get('success'):
            status = 'success'
        else:
            status = 'error'
            error_message = email_result.get('error')

    except Exception as e:
        status = 'error'
        error_message = str(e)

    # Enregistrer dans l'historique
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO APP_ReportHistory (schedule_id, report_name, recipients, status, error_message, file_path, file_size)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                schedule.get('id'),
                schedule['nom'],
                json.dumps(schedule['recipients']),
                status,
                error_message,
                file_path,
                file_size
            ))

            # Mettre a jour last_run, next_run, run_count et success_count en une seule requete
            if schedule.get('id'):
                cursor.execute("""
                    UPDATE APP_ReportSchedules
                    SET last_run=GETDATE(), next_run=?,
                        run_count = ISNULL(run_count,0) + 1,
                        success_count = ISNULL(success_count,0) + CASE WHEN ? = 'success' THEN 1 ELSE 0 END
                    WHERE id=?
                """, (
                    calculate_next_run(schedule['frequency'], schedule['schedule_time'], schedule.get('schedule_day')),
                    status,
                    schedule['id']
                ))
    except Exception as e:
        print(f"Erreur enregistrement historique: {e}")

    # Nettoyer le fichier temporaire
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except:
            pass


# ==================== USERS FOR RECIPIENTS ====================

@router.get("/users-with-emails")
async def get_users_with_emails():
    """Recupere la liste des utilisateurs avec leurs emails pour la selection des destinataires"""
    try:
        # APP_Users est toujours dans MASTER
        users = execute_master_query("""
            SELECT id, username, nom, prenom, email
            FROM APP_Users
            WHERE actif = 1 AND email IS NOT NULL
            ORDER BY nom, prenom
        """, use_cache=False)

        print(f"[USERS-WITH-EMAILS] Utilisateurs trouves: {len(users) if users else 0}")
        if users:
            for u in users:
                print(f"  - {u.get('nom')} {u.get('prenom')}: {u.get('email')}")

        return {"success": True, "data": users or []}
    except Exception as e:
        import traceback
        print(f"[USERS-WITH-EMAILS] Erreur: {e}")
        print(traceback.format_exc())
        return {"success": False, "error": str(e), "data": []}


# ==================== AVAILABLE REPORTS ====================

@router.get("/available-reports")
async def get_available_reports():
    """Liste les rapports disponibles pour la programmation"""
    try:
        reports = {
            "pivots": [],
            "gridviews": [],
            "dashboards": [],
            "exports": [
                {"id": "ventes", "nom": "Export Ventes Complet", "type": "export"},
                {"id": "stocks", "nom": "Export Stocks", "type": "export"},
                {"id": "recouvrement", "nom": "Export Recouvrement", "type": "export"},
                {"id": "complet", "nom": "Rapport Complet", "type": "export"},
            ]
        }

        # Pivots
        pivots = execute_query("SELECT id, nom FROM APP_Pivots ORDER BY nom", use_cache=False)
        reports["pivots"] = [{"id": p['id'], "nom": p['nom'], "type": "pivot"} for p in pivots]

        # GridViews
        gridviews = execute_query("SELECT id, nom FROM APP_GridViews ORDER BY nom", use_cache=False)
        reports["gridviews"] = [{"id": g['id'], "nom": g['nom'], "type": "gridview"} for g in gridviews]

        # Dashboards
        dashboards = execute_query("SELECT id, nom FROM APP_Dashboards ORDER BY nom", use_cache=False)
        reports["dashboards"] = [{"id": d['id'], "nom": d['nom'], "type": "dashboard"} for d in dashboards]

        return {"success": True, "data": reports}
    except Exception as e:
        return {"success": False, "error": str(e), "data": {}}
