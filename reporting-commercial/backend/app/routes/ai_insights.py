"""Routes pour la génération d'insights IA automatiques sur les rapports."""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from ..services.ai_insights_service import generate_insights, invalidate_cache

router = APIRouter(prefix="/api/ai-insights", tags=["AI Insights"])


class InsightsRequest(BaseModel):
    report_type: str           # gridview | dashboard | pivot
    report_id: int
    report_nom: str
    data: List[Dict[str, Any]]
    columns_info: Optional[List[Dict]] = None
    context: Optional[str] = None
    force_refresh: bool = False


@router.post("/generate")
async def generate_report_insights(req: InsightsRequest):
    """
    Génère des insights IA pour un rapport.
    Envoie un résumé statistique des données au LLM configuré
    et retourne une liste d'observations métier structurées.
    """
    result = await generate_insights(
        report_type=req.report_type,
        report_id=req.report_id,
        report_nom=req.report_nom,
        data=req.data,
        columns_info=req.columns_info or [],
        context=req.context,
        force_refresh=req.force_refresh
    )
    return result


@router.delete("/cache/{report_type}/{report_id}")
async def clear_insights_cache(report_type: str, report_id: int):
    """Invalide le cache d'insights pour un rapport."""
    invalidate_cache(report_type, report_id)
    return {"success": True, "message": "Cache invalidé"}
