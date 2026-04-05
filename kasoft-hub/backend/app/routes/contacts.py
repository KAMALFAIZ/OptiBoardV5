"""CRUD contacts unifiés."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from ..database import execute, write, write_returning_id

router = APIRouter(prefix="/api/contacts", tags=["contacts"])


class ContactCreate(BaseModel):
    product_code: str
    nom: str
    prenom: Optional[str] = None
    email: Optional[str] = None
    telephone: Optional[str] = None
    whatsapp: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    societe: Optional[str] = None
    poste: Optional[str] = None
    segment: str = "prospect"
    source: str = "manual"
    tags: Optional[str] = None
    notes: Optional[str] = None


class ContactUpdate(BaseModel):
    nom: Optional[str] = None
    prenom: Optional[str] = None
    email: Optional[str] = None
    telephone: Optional[str] = None
    whatsapp: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    societe: Optional[str] = None
    poste: Optional[str] = None
    segment: Optional[str] = None
    tags: Optional[str] = None
    notes: Optional[str] = None
    actif: Optional[bool] = None


@router.get("")
async def list_contacts(
    product_code: Optional[str] = None,
    segment: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    where = ["actif=1"]
    params = []
    if product_code:
        where.append("product_code=?")
        params.append(product_code.upper())
    if segment:
        where.append("segment=?")
        params.append(segment)
    if search:
        where.append("(nom LIKE ? OR email LIKE ? OR societe LIKE ? OR telephone LIKE ?)")
        s = f"%{search}%"
        params.extend([s, s, s, s])

    where_sql = " AND ".join(where)
    contacts = execute(
        f"SELECT * FROM HUB_Contacts WHERE {where_sql} ORDER BY created_at DESC OFFSET ? ROWS FETCH NEXT ? ROWS ONLY",
        tuple(params) + (offset, limit),
    )
    total = execute(f"SELECT COUNT(*) AS cnt FROM HUB_Contacts WHERE {where_sql}", tuple(params))
    return {"success": True, "data": contacts, "total": total[0]["cnt"] if total else 0}


@router.get("/{contact_id}")
async def get_contact(contact_id: int):
    rows = execute("SELECT * FROM HUB_Contacts WHERE id=?", (contact_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Contact non trouvé")
    return {"success": True, "data": rows[0]}


@router.post("")
async def create_contact(body: ContactCreate):
    contact_id = write_returning_id(
        """INSERT INTO HUB_Contacts
           (product_code, nom, prenom, email, telephone, whatsapp, telegram_chat_id,
            societe, poste, segment, source, tags, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            body.product_code.upper(), body.nom, body.prenom, body.email,
            body.telephone, body.whatsapp, body.telegram_chat_id,
            body.societe, body.poste, body.segment, body.source, body.tags, body.notes,
        ),
    )
    rows = execute("SELECT * FROM HUB_Contacts WHERE id=?", (contact_id,))
    return {"success": True, "data": rows[0]}


@router.put("/{contact_id}")
async def update_contact(contact_id: int, body: ContactUpdate):
    rows = execute("SELECT id FROM HUB_Contacts WHERE id=?", (contact_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Contact non trouvé")

    updates = {}
    if body.nom is not None:              updates["nom"] = body.nom
    if body.prenom is not None:           updates["prenom"] = body.prenom
    if body.email is not None:            updates["email"] = body.email
    if body.telephone is not None:        updates["telephone"] = body.telephone
    if body.whatsapp is not None:         updates["whatsapp"] = body.whatsapp
    if body.telegram_chat_id is not None: updates["telegram_chat_id"] = body.telegram_chat_id
    if body.societe is not None:          updates["societe"] = body.societe
    if body.poste is not None:            updates["poste"] = body.poste
    if body.segment is not None:          updates["segment"] = body.segment
    if body.tags is not None:             updates["tags"] = body.tags
    if body.notes is not None:            updates["notes"] = body.notes
    if body.actif is not None:            updates["actif"] = 1 if body.actif else 0

    if updates:
        set_clause = ", ".join(f"{k}=?" for k in updates)
        write(
            f"UPDATE HUB_Contacts SET {set_clause}, updated_at=GETDATE() WHERE id=?",
            tuple(updates.values()) + (contact_id,),
        )
    rows = execute("SELECT * FROM HUB_Contacts WHERE id=?", (contact_id,))
    return {"success": True, "data": rows[0]}


@router.delete("/{contact_id}")
async def delete_contact(contact_id: int):
    write("UPDATE HUB_Contacts SET actif=0, updated_at=GETDATE() WHERE id=?", (contact_id,))
    return {"success": True}
