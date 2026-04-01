"""Routes pour la génération de résumés exécutifs IA."""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from ..services.ai_summary_service import generate_executive_summary

router = APIRouter(prefix="/api/ai-summary", tags=["AI Résumé Exécutif"])


class SummaryRequest(BaseModel):
    report_type: str
    report_id: int
    report_nom: str
    data: List[Dict[str, Any]]
    columns_info: Optional[List[Dict]] = None
    period: Optional[str] = None       # Ex: "Janvier–Mars 2026"
    entity: Optional[str] = None       # Ex: "Groupe AlBoughaze"
    context: Optional[str] = None      # Contexte métier libre
    force_refresh: bool = False


@router.post("/generate")
async def generate_summary(req: SummaryRequest):
    """
    Génère un résumé exécutif narratif structuré pour un rapport.
    Retourne des sections (titre + paragraphe) et des KPIs clés.
    """
    result = await generate_executive_summary(
        report_type=req.report_type,
        report_id=req.report_id,
        report_nom=req.report_nom,
        data=req.data,
        columns_info=req.columns_info or [],
        period=req.period,
        entity=req.entity,
        context=req.context,
        force_refresh=req.force_refresh
    )
    return result
