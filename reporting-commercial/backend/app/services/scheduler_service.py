"""Service de planification des rapports automatiques"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import json
import asyncio

scheduler = AsyncIOScheduler()
_scheduler_started = False


def start_scheduler():
    """Demarre le scheduler s'il n'est pas deja demarre"""
    global _scheduler_started
    if not _scheduler_started:
        scheduler.start()
        _scheduler_started = True
        print("[SCHEDULER] Demarrage du scheduler")
        # Charger les taches programmees existantes
        asyncio.create_task(load_scheduled_tasks())

    # Job d'évaluation des alertes KPI toutes les heures
    scheduler.add_job(
        evaluate_kpi_alerts,
        trigger=CronTrigger(minute=0),   # Chaque heure pile
        id="kpi_alert_evaluation",
        name="Évaluation Alertes KPI",
        replace_existing=True
    )
    print("[SCHEDULER] Job alertes KPI enregistré (toutes les heures)")

    # Job de livraison des abonnements chaque matin à 7h00
    scheduler.add_job(
        deliver_subscriptions,
        trigger=CronTrigger(hour=7, minute=0),
        id="subscription_delivery",
        name="Livraison Abonnements Rapports",
        replace_existing=True
    )
    print("[SCHEDULER] Job abonnements enregistré (quotidien à 07h00)")


def stop_scheduler():
    """Arrete le scheduler"""
    global _scheduler_started
    if _scheduler_started:
        scheduler.shutdown()
        _scheduler_started = False
        print("[SCHEDULER] Arret du scheduler")


async def load_scheduled_tasks():
    """Charge les taches programmees depuis la base de donnees"""
    from ..database_unified import execute_app as execute_query

    try:
        schedules = execute_query(
            "SELECT * FROM APP_ReportSchedules WHERE is_active = 1",
            use_cache=False
        )

        for schedule in schedules:
            add_schedule_job(schedule)

        print(f"[SCHEDULER] {len(schedules)} tache(s) programmee(s) chargee(s)")
    except Exception as e:
        print(f"[SCHEDULER] Erreur chargement taches: {e}")


def add_schedule_job(schedule: dict):
    """Ajoute une tache au scheduler"""
    job_id = f"report_schedule_{schedule['id']}"

    # Supprimer le job existant s'il existe
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    if not schedule.get('is_active', True):
        return

    # Creer le trigger selon la frequence
    hour, minute = map(int, schedule.get('schedule_time', '08:00').split(':'))
    frequency = schedule.get('frequency', 'daily')

    if frequency == 'daily':
        trigger = CronTrigger(hour=hour, minute=minute)
    elif frequency == 'weekly':
        day_of_week = schedule.get('schedule_day', 1) - 1  # 0=lundi dans cron
        trigger = CronTrigger(day_of_week=day_of_week, hour=hour, minute=minute)
    elif frequency == 'monthly':
        day = schedule.get('schedule_day', 1)
        trigger = CronTrigger(day=day, hour=hour, minute=minute)
    else:
        # Une seule execution
        trigger = CronTrigger(hour=hour, minute=minute)

    scheduler.add_job(
        execute_scheduled_report,
        trigger=trigger,
        id=job_id,
        args=[schedule['id']],
        name=f"Report: {schedule.get('nom', 'Unknown')}",
        replace_existing=True
    )

    print(f"[SCHEDULER] Job ajoute: {job_id} ({frequency} a {hour:02d}:{minute:02d})")


def remove_schedule_job(schedule_id: int):
    """Supprime une tache du scheduler"""
    job_id = f"report_schedule_{schedule_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        print(f"[SCHEDULER] Job supprime: {job_id}")


async def execute_scheduled_report(schedule_id: int):
    """Execute un rapport programme"""
    from ..database_unified import execute_app as execute_query, app_cursor as get_db_cursor
    from ..routes.report_scheduler import execute_schedule

    print(f"[SCHEDULER] Execution du rapport schedule_id={schedule_id}")

    try:
        schedule = execute_query(
            "SELECT * FROM APP_ReportSchedules WHERE id = ? AND is_active = 1",
            (schedule_id,),
            use_cache=False
        )

        if not schedule:
            print(f"[SCHEDULER] Schedule {schedule_id} non trouve ou inactif")
            return

        schedule = schedule[0]
        schedule['recipients'] = json.loads(schedule['recipients']) if schedule.get('recipients') else []
        schedule['cc_recipients'] = json.loads(schedule['cc_recipients']) if schedule.get('cc_recipients') else None
        schedule['filters'] = json.loads(schedule['filters']) if schedule.get('filters') else None

        # Executer le rapport
        await execute_schedule(schedule)

        print(f"[SCHEDULER] Rapport {schedule_id} execute avec succes")

    except Exception as e:
        print(f"[SCHEDULER] Erreur execution rapport {schedule_id}: {e}")


async def deliver_subscriptions():
    """Livre les rapports aux abonnés dont la date de livraison est échue."""
    from ..routes.subscriptions import deliver_due_subscriptions
    try:
        await deliver_due_subscriptions()
    except Exception as e:
        print(f"[SCHEDULER] Erreur livraison abonnements: {e}")


async def evaluate_kpi_alerts():
    """Évalue périodiquement toutes les règles d'alerte KPI actives."""
    from ..database_unified import execute_client, execute_dwh
    from .alert_service import evaluate_all_alerts
    try:
        result = evaluate_all_alerts(execute_client, execute_dwh)
        print(f"[SCHEDULER] Alertes KPI: {result['triggered']} déclenchée(s)")
    except Exception as e:
        print(f"[SCHEDULER] Erreur évaluation alertes KPI: {e}")


def get_scheduler_status():
    """Retourne le statut du scheduler"""
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger)
        })

    return {
        "running": _scheduler_started,
        "jobs_count": len(jobs),
        "jobs": jobs
    }


def refresh_schedule(schedule_id: int):
    """Rafraichit une tache dans le scheduler"""
    from ..database_unified import execute_app as execute_query

    schedule = execute_query(
        "SELECT * FROM APP_ReportSchedules WHERE id = ?",
        (schedule_id,),
        use_cache=False
    )

    if schedule:
        add_schedule_job(schedule[0])
    else:
        remove_schedule_job(schedule_id)
