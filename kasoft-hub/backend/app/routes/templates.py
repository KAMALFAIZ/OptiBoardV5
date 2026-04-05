"""CRUD templates de messages (WhatsApp / Telegram / Email)."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from ..database import execute, write, write_returning_id

router = APIRouter(prefix="/api/templates", tags=["templates"])


class TemplateCreate(BaseModel):
    nom: str
    channel: str
    contenu: str
    sujet: Optional[str] = None
    product_code: str = "ALL"
    variables: Optional[str] = None


class TemplateUpdate(BaseModel):
    nom: Optional[str] = None
    contenu: Optional[str] = None
    sujet: Optional[str] = None
    variables: Optional[str] = None


@router.get("")
async def list_templates(product_code: Optional[str] = None, channel: Optional[str] = None):
    where = ["1=1"]
    params = []
    if product_code:
        where.append("(product_code=? OR product_code='ALL')")
        params.append(product_code.upper())
    if channel:
        where.append("channel=?")
        params.append(channel)
    rows = execute(
        f"SELECT * FROM HUB_Templates WHERE {' AND '.join(where)} ORDER BY nom",
        tuple(params),
    )
    return {"success": True, "data": rows}


@router.post("")
async def create_template(body: TemplateCreate):
    valid_channels = ["telegram", "whatsapp", "email"]
    if body.channel not in valid_channels:
        raise HTTPException(status_code=400, detail=f"Canal invalide. Valeurs: {valid_channels}")
    tid = write_returning_id(
        "INSERT INTO HUB_Templates (product_code, nom, channel, sujet, contenu, variables) VALUES (?, ?, ?, ?, ?, ?)",
        (body.product_code.upper(), body.nom, body.channel, body.sujet, body.contenu, body.variables),
    )
    rows = execute("SELECT * FROM HUB_Templates WHERE id=?", (tid,))
    return {"success": True, "data": rows[0]}


@router.put("/{template_id}")
async def update_template(template_id: int, body: TemplateUpdate):
    updates = {}
    if body.nom is not None:       updates["nom"] = body.nom
    if body.contenu is not None:   updates["contenu"] = body.contenu
    if body.sujet is not None:     updates["sujet"] = body.sujet
    if body.variables is not None: updates["variables"] = body.variables
    if updates:
        set_clause = ", ".join(f"{k}=?" for k in updates)
        write(
            f"UPDATE HUB_Templates SET {set_clause}, updated_at=GETDATE() WHERE id=?",
            tuple(updates.values()) + (template_id,),
        )
    rows = execute("SELECT * FROM HUB_Templates WHERE id=?", (template_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Template non trouvé")
    return {"success": True, "data": rows[0]}


@router.delete("/{template_id}")
async def delete_template(template_id: int):
    write("DELETE FROM HUB_Templates WHERE id=?", (template_id,))
    return {"success": True}
