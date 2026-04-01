"""Routes de prévision (forecasting) pour OptiBoard."""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List, Any

from ..services.forecasting_service import run_forecast

router = APIRouter(prefix="/api/forecast", tags=["Forecasting"])


class ForecastRequest(BaseModel):
    values: List[Any]                   # Série de valeurs numériques (ordre chronologique)
    labels: Optional[List[str]] = None  # Étiquettes x-axis (mois, années…)
    periods: int = 6                    # Nombre de périodes futures
    method: str = "auto"                # "linear" | "moving_avg" | "holt" | "auto"


@router.post("/predict")
async def predict(req: ForecastRequest):
    """
    Prédit les valeurs futures d'une série temporelle.
    Méthodes : régression linéaire, moyenne mobile pondérée, lissage exponentiel (Holt).
    En mode auto, sélectionne la méthode avec le MAE le plus faible.
    Retourne historique + prévisions avec intervalle de confiance 95%.
    """
    return run_forecast(
        values=req.values,
        labels=req.labels,
        periods=req.periods,
        method=req.method,
    )
