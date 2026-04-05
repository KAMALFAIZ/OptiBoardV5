"""CRUD règles d'automation (workflows if/then)."""
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from ..database import execute, write, write_returning_id

router = APIRouter(prefix="/api/workflows", tags=["workflows"])

VALID_EVENTS = [
    "new_prospect", "new_client", "demo_requested", "demo_completed",
    "ticket_opened", "ticket_resolved", "payment_late", "subscription_expiring",
]


class WorkflowCreate(BaseModel):
    nom: str
    trigger_event: str
    trigger_condition: Optional[dict] = None
    actions: list
    product_code: str = "ALL"
    is_active: bool = True


class WorkflowUpdate(BaseModel):
    nom: Optional[str] = None
    trigger_condition: Optional[dict] = None
    actions: Optional[list] = None
    is_active: Optional[bool] = None


@router.get("")
async def list_workflows(product_code: Optional[str] = None):
    where = ["1=1"]
    params = []
    if product_code:
        where.append("(product_code=? OR product_code='ALL')")
        params.append(product_code.upper())
    rows = execute(
        f"SELECT * FROM HUB_Workflows WHERE {' AND '.join(where)} ORDER BY created_at DESC",
        tuple(params),
    )
    return {"success": True, "data": rows}


@router.post("")
async def create_workflow(body: WorkflowCreate):
    if body.trigger_event not in VALID_EVENTS:
        raise HTTPException(status_code=400, detail=f"Événement invalide. Valeurs: {VALID_EVENTS}")
    wid = write_returning_id(
        """INSERT INTO HUB_Workflows
           (product_code, nom, trigger_event, trigger_condition, actions, is_active)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            body.product_code.upper(),
            body.nom,
            body.trigger_event,
            json.dumps(body.trigger_condition) if body.trigger_condition else None,
            json.dumps(body.actions),
            1 if body.is_active else 0,
        ),
    )
    rows = execute("SELECT * FROM HUB_Workflows WHERE id=?", (wid,))
    return {"success": True, "data": rows[0]}


@router.put("/{workflow_id}")
async def update_workflow(workflow_id: int, body: WorkflowUpdate):
    updates = {}
    if body.nom is not None:              updates["nom"] = body.nom
    if body.trigger_condition is not None: updates["trigger_condition"] = json.dumps(body.trigger_condition)
    if body.actions is not None:          updates["actions"] = json.dumps(body.actions)
    if body.is_active is not None:        updates["is_active"] = 1 if body.is_active else 0
    if updates:
        set_clause = ", ".join(f"{k}=?" for k in updates)
        write(
            f"UPDATE HUB_Workflows SET {set_clause}, updated_at=GETDATE() WHERE id=?",
            tuple(updates.values()) + (workflow_id,),
        )
    rows = execute("SELECT * FROM HUB_Workflows WHERE id=?", (workflow_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Workflow non trouvé")
    return {"success": True, "data": rows[0]}


@router.delete("/{workflow_id}")
async def delete_workflow(workflow_id: int):
    write("DELETE FROM HUB_Workflows WHERE id=?", (workflow_id,))
    return {"success": True}
