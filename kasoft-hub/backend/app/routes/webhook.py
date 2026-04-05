"""Route webhook — les produits KAsoft envoient leurs événements ici."""
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from ..database import execute
from ..services.automation_engine import process_event, SUPPORTED_EVENTS

router = APIRouter(prefix="/api/webhook", tags=["webhook"])


class WebhookPayload(BaseModel):
    event: str
    secret: str
    data: dict = {}


@router.post("/{product_code}")
async def receive_webhook(product_code: str, body: WebhookPayload):
    """Reçoit un événement d'un produit et déclenche les automatisations."""
    # Vérifier le produit
    products = execute(
        "SELECT * FROM HUB_Products WHERE code=? AND actif=1",
        (product_code.upper(),),
    )
    if not products:
        raise HTTPException(status_code=404, detail=f"Produit {product_code} non trouvé ou inactif")

    product = products[0]

    # Vérifier le secret
    if body.secret != product["webhook_secret"]:
        raise HTTPException(status_code=401, detail="Secret invalide")

    # Vérifier l'événement
    if body.event not in SUPPORTED_EVENTS:
        raise HTTPException(
            status_code=400,
            detail=f"Événement '{body.event}' non supporté. Supportés: {SUPPORTED_EVENTS}",
        )

    result = process_event(product_code.upper(), body.event, body.data)
    return {"success": True, "data": result}


@router.get("/events/supported")
async def list_supported_events():
    """Retourne la liste des événements supportés."""
    return {"success": True, "events": SUPPORTED_EVENTS}
