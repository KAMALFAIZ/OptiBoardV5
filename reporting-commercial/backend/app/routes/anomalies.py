"""Routes pour la détection d'anomalies statistiques dans les rapports."""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from ..services.anomaly_detection_service import detect_anomalies

router = APIRouter(prefix="/api/anomalies", tags=["Détection Anomalies"])


class AnomalyRequest(BaseModel):
    data: List[Dict[str, Any]]
    columns_info: Optional[List[Dict]] = None
    max_anomalies: int = 50
    zscore_critical: float = 3.0   # > Nσ → critique  (défaut: 3.0)
    zscore_warning: float = 2.5    # > Nσ → alerte    (défaut: 2.5)
    iqr_multiplier: float = 2.0    # outlier IQR ×N   (défaut: 2.0)
    min_rows: int = 5              # min lignes pour stats fiables


@router.post("/detect")
async def detect(req: AnomalyRequest):
    """
    Détecte les anomalies statistiques (Z-score + IQR) dans les données.
    Paramètres configurables : zscore_critical, zscore_warning, iqr_multiplier, min_rows.
    Traitement 100% local, sans appel IA.
    """
    result = detect_anomalies(
        data=req.data,
        columns_info=req.columns_info or [],
        max_anomalies=req.max_anomalies,
        zscore_critical=req.zscore_critical,
        zscore_warning=req.zscore_warning,
        iqr_multiplier=req.iqr_multiplier,
        min_rows=req.min_rows,
    )
    return result
