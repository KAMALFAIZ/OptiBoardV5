"""Campagnes marketing + étapes + enrollment contacts."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from ..database import execute, write, write_returning_id

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


class CampaignCreate(BaseModel):
    nom: str
    type_camp: str = "nurturing"
    channel: str = "multi"
    description: Optional[str] = None
    product_code: str = "ALL"
    segment_cible: Optional[str] = None


class CampaignStep(BaseModel):
    step_order: int
    delay_days: int = 0
    channel: str
    template_id: Optional[int] = None
    condition_type: str = "always"


class EnrollRequest(BaseModel):
    contact_ids: List[int]


@router.get("")
async def list_campaigns(product_code: Optional[str] = None, statut: Optional[str] = None):
    where = ["1=1"]
    params = []
    if product_code:
        where.append("(product_code=? OR product_code='ALL')")
        params.append(product_code.upper())
    if statut:
        where.append("statut=?")
        params.append(statut)
    rows = execute(
        f"SELECT * FROM HUB_Campaigns WHERE {' AND '.join(where)} ORDER BY created_at DESC",
        tuple(params),
    )
    for camp in rows:
        steps = execute("SELECT COUNT(*) AS cnt FROM HUB_CampaignSteps WHERE campaign_id=? AND actif=1", (camp["id"],))
        enrolled = execute("SELECT COUNT(*) AS cnt FROM HUB_CampaignEnrollments WHERE campaign_id=? AND statut='active'", (camp["id"],))
        camp["steps_count"] = steps[0]["cnt"] if steps else 0
        camp["enrolled_count"] = enrolled[0]["cnt"] if enrolled else 0
    return {"success": True, "data": rows}


@router.get("/{campaign_id}")
async def get_campaign(campaign_id: int):
    rows = execute("SELECT * FROM HUB_Campaigns WHERE id=?", (campaign_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Campagne non trouvée")
    camp = rows[0]
    camp["steps"] = execute(
        "SELECT * FROM HUB_CampaignSteps WHERE campaign_id=? ORDER BY step_order",
        (campaign_id,),
    )
    return {"success": True, "data": camp}


@router.post("")
async def create_campaign(body: CampaignCreate):
    camp_id = write_returning_id(
        "INSERT INTO HUB_Campaigns (nom, type_camp, channel, description, product_code, segment_cible) VALUES (?, ?, ?, ?, ?, ?)",
        (body.nom, body.type_camp, body.channel, body.description, body.product_code.upper(), body.segment_cible),
    )
    rows = execute("SELECT * FROM HUB_Campaigns WHERE id=?", (camp_id,))
    return {"success": True, "data": rows[0]}


@router.post("/{campaign_id}/steps")
async def add_step(campaign_id: int, body: CampaignStep):
    """Ajoute une étape à la campagne."""
    camp = execute("SELECT id FROM HUB_Campaigns WHERE id=?", (campaign_id,))
    if not camp:
        raise HTTPException(status_code=404, detail="Campagne non trouvée")
    sid = write_returning_id(
        "INSERT INTO HUB_CampaignSteps (campaign_id, step_order, delay_days, channel, template_id, condition_type) VALUES (?, ?, ?, ?, ?, ?)",
        (campaign_id, body.step_order, body.delay_days, body.channel, body.template_id, body.condition_type),
    )
    rows = execute("SELECT * FROM HUB_CampaignSteps WHERE id=?", (sid,))
    return {"success": True, "data": rows[0]}


@router.post("/{campaign_id}/start")
async def start_campaign(campaign_id: int):
    """Active la campagne."""
    camp = execute("SELECT * FROM HUB_Campaigns WHERE id=?", (campaign_id,))
    if not camp:
        raise HTTPException(status_code=404, detail="Campagne non trouvée")
    steps = execute("SELECT COUNT(*) AS cnt FROM HUB_CampaignSteps WHERE campaign_id=? AND actif=1", (campaign_id,))
    if not steps or steps[0]["cnt"] == 0:
        raise HTTPException(status_code=400, detail="Aucune étape définie pour cette campagne")
    write("UPDATE HUB_Campaigns SET statut='active', updated_at=GETDATE() WHERE id=?", (campaign_id,))
    return {"success": True, "message": "Campagne activée"}


@router.post("/{campaign_id}/pause")
async def pause_campaign(campaign_id: int):
    write("UPDATE HUB_Campaigns SET statut='paused', updated_at=GETDATE() WHERE id=?", (campaign_id,))
    return {"success": True, "message": "Campagne mise en pause"}


@router.post("/{campaign_id}/enroll")
async def enroll_contacts(campaign_id: int, body: EnrollRequest):
    """Inscrit des contacts dans une campagne."""
    camp = execute("SELECT * FROM HUB_Campaigns WHERE id=? AND statut='active'", (campaign_id,))
    if not camp:
        raise HTTPException(status_code=400, detail="Campagne non trouvée ou non active")

    first_step = execute(
        "SELECT delay_days FROM HUB_CampaignSteps WHERE campaign_id=? AND step_order=1 AND actif=1",
        (campaign_id,),
    )
    next_send = datetime.now() + timedelta(days=first_step[0]["delay_days"] if first_step else 0)

    enrolled = 0
    for cid in body.contact_ids:
        existing = execute(
            "SELECT id FROM HUB_CampaignEnrollments WHERE campaign_id=? AND contact_id=? AND statut='active'",
            (campaign_id, cid),
        )
        if not existing:
            write_returning_id(
                "INSERT INTO HUB_CampaignEnrollments (campaign_id, contact_id, current_step, next_send_at) VALUES (?, ?, 0, ?)",
                (campaign_id, cid, next_send),
            )
            enrolled += 1

    return {"success": True, "enrolled": enrolled}
