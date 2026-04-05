"""Registry des produits KAsoft + gestion des secrets webhook."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid
from ..database import execute, write, write_returning_id

router = APIRouter(prefix="/api/products", tags=["products"])


class ProductCreate(BaseModel):
    code: str
    nom: str
    description: Optional[str] = None
    couleur: str = "#3B82F6"


@router.get("")
async def list_products():
    rows = execute("SELECT id, code, nom, description, couleur, actif, created_at FROM HUB_Products ORDER BY code")
    return {"success": True, "data": rows}


@router.get("/{code}")
async def get_product(code: str):
    rows = execute("SELECT id, code, nom, description, couleur, actif FROM HUB_Products WHERE code=?", (code.upper(),))
    if not rows:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    p = rows[0]
    # Stats
    p["contacts_count"] = (execute("SELECT COUNT(*) AS c FROM HUB_Contacts WHERE product_code=?", (code.upper(),)) or [{"c": 0}])[0]["c"]
    p["tickets_open"] = (execute("SELECT COUNT(*) AS c FROM HUB_Tickets WHERE product_code=? AND statut IN ('open','in_progress')", (code.upper(),)) or [{"c": 0}])[0]["c"]
    p["campaigns_active"] = (execute("SELECT COUNT(*) AS c FROM HUB_Campaigns WHERE product_code=? AND statut='active'", (code.upper(),)) or [{"c": 0}])[0]["c"]
    return {"success": True, "data": p}


@router.get("/{code}/secret")
async def get_webhook_secret(code: str):
    """Retourne le secret webhook (admin only)."""
    rows = execute("SELECT webhook_secret FROM HUB_Products WHERE code=?", (code.upper(),))
    if not rows:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    return {"success": True, "secret": rows[0]["webhook_secret"]}


@router.post("/{code}/regenerate-secret")
async def regenerate_secret(code: str):
    """Régénère le secret webhook du produit."""
    new_secret = str(uuid.uuid4())
    write("UPDATE HUB_Products SET webhook_secret=? WHERE code=?", (new_secret, code.upper()))
    return {"success": True, "secret": new_secret}
