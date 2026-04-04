"""
Route de gestion du digest IA hebdomadaire.

Endpoints :
  POST /api/admin/digest/trigger           — déclenche le digest pour tous les DWH (test manuel)
  POST /api/admin/digest/trigger/{dwh}     — déclenche pour un DWH spécifique
  GET  /api/admin/digest/status            — statut du job scheduler
"""
from fastapi import APIRouter, HTTPException
from typing import Optional

router = APIRouter(prefix="/api/admin/digest", tags=["Digest Hebdomadaire"])


@router.post("/trigger")
async def trigger_all_digests():
    """
    Déclenche immédiatement le digest IA pour tous les DWH actifs.
    Utile pour tester sans attendre le lundi 8h00.
    """
    from ..services.weekly_digest_service import send_all_digests
    try:
        result = await send_all_digests()
        return {
            "success": True,
            "message": f"Digest envoyé à {result['success']}/{result['total_dwh']} DWH",
            "details": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur digest: {str(e)}")


@router.post("/trigger/{dwh_code}")
async def trigger_digest_for_dwh(dwh_code: str):
    """
    Déclenche le digest IA pour un DWH spécifique.
    Exemple : POST /api/admin/digest/trigger/KA01
    """
    from ..services.weekly_digest_service import send_weekly_digest
    try:
        result = await send_weekly_digest(dwh_code.upper())
        return {
            "success": result["success"],
            "message": f"{result['nb_sent']} email(s) envoyé(s)" if result["success"] else "Échec",
            "details": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur digest {dwh_code}: {str(e)}")


@router.get("/status")
async def digest_job_status():
    """Retourne le statut du job digest dans le scheduler."""
    from ..services.scheduler_service import scheduler
    job = scheduler.get_job("weekly_ai_digest")
    if not job:
        return {"registered": False, "message": "Job digest non trouvé dans le scheduler"}
    return {
        "registered": True,
        "job_id": job.id,
        "name": job.name,
        "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
        "trigger": str(job.trigger),
    }
