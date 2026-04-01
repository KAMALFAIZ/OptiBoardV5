"""
Routes API pour le module d'apprentissage IA (Query Library + Feedback).
"""
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
import logging

from ..database_unified import execute_central
from ..services.ai_query_library import (
    add_to_library, record_feedback, get_library,
    validate_library_entry, reject_library_entry,
    delete_library_entry, update_library_entry,
    get_library_stats, seed_library
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ai/learning", tags=["IA Learning"])


def _get_user_role(user_id: int) -> str:
    if not user_id:
        return ""
    try:
        rows = execute_central(
            "SELECT role_global FROM APP_Users WHERE id = ?",
            (user_id,), use_cache=False
        )
        return rows[0].get("role_global", "") if rows else ""
    except Exception:
        return ""


class FeedbackRequest(BaseModel):
    question_text: str
    sql_query: str
    rating: str  # 'positive' | 'negative'
    dwh_code: Optional[str] = None


class LibraryEntryCreate(BaseModel):
    question_text: str
    sql_query: str
    dwh_code: Optional[str] = None


class LibraryEntryUpdate(BaseModel):
    question_text: Optional[str] = None
    sql_query: Optional[str] = None
    validated: Optional[bool] = None


@router.post("/feedback")
async def submit_feedback(
    request: FeedbackRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """Enregistre un feedback utilisateur (👍/👎)."""
    user_id = int(x_user_id) if x_user_id and x_user_id.isdigit() else 0
    if request.rating not in ('positive', 'negative'):
        raise HTTPException(status_code=400, detail="rating doit être 'positive' ou 'negative'")
    success = record_feedback(
        question_text=request.question_text,
        sql_query=request.sql_query or "",
        rating=request.rating,
        dwh_code=request.dwh_code,
        user_id=user_id
    )
    return {"success": success}


@router.get("/library")
async def get_query_library(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """Retourne la liste des requêtes (superadmin uniquement)."""
    user_id = int(x_user_id) if x_user_id and x_user_id.isdigit() else 0
    if _get_user_role(user_id) != "superadmin":
        raise HTTPException(status_code=403, detail="Accès réservé aux super-administrateurs")
    entries = get_library()
    stats = get_library_stats()
    return {"success": True, "entries": entries, "total": len(entries), "stats": stats}


@router.post("/library")
async def add_library_entry(
    entry: LibraryEntryCreate,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """Ajoute manuellement une requête (superadmin)."""
    user_id = int(x_user_id) if x_user_id and x_user_id.isdigit() else 0
    if _get_user_role(user_id) != "superadmin":
        raise HTTPException(status_code=403, detail="Accès réservé aux super-administrateurs")
    entry_id = add_to_library(
        question_text=entry.question_text,
        sql_query=entry.sql_query,
        dwh_code=entry.dwh_code,
        validated_by=f"user_{user_id}",
        is_validated=True
    )
    return {"success": True, "id": entry_id}


@router.put("/library/{entry_id}")
async def update_entry(
    entry_id: int,
    update: LibraryEntryUpdate,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """Met à jour une entrée (superadmin)."""
    user_id = int(x_user_id) if x_user_id and x_user_id.isdigit() else 0
    if _get_user_role(user_id) != "superadmin":
        raise HTTPException(status_code=403, detail="Accès réservé aux super-administrateurs")
    if update.validated is True:
        validate_library_entry(entry_id, validated_by=f"user_{user_id}")
    elif update.validated is False:
        reject_library_entry(entry_id)
    if update.question_text or update.sql_query:
        update_library_entry(entry_id, update.question_text, update.sql_query)
    return {"success": True}


@router.delete("/library/{entry_id}")
async def delete_entry(
    entry_id: int,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """Supprime une entrée (superadmin)."""
    user_id = int(x_user_id) if x_user_id and x_user_id.isdigit() else 0
    if _get_user_role(user_id) != "superadmin":
        raise HTTPException(status_code=403, detail="Accès réservé aux super-administrateurs")
    return {"success": delete_library_entry(entry_id)}


@router.get("/stats")
async def get_stats(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """Statistiques de la query library (superadmin)."""
    user_id = int(x_user_id) if x_user_id and x_user_id.isdigit() else 0
    if _get_user_role(user_id) != "superadmin":
        raise HTTPException(status_code=403, detail="Accès réservé aux super-administrateurs")
    return {"success": True, "stats": get_library_stats()}


@router.post("/seed")
async def seed_examples(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """Initialise la Query Library avec les 15 exemples de référence (superadmin)."""
    user_id = int(x_user_id) if x_user_id and x_user_id.isdigit() else 0
    if _get_user_role(user_id) != "superadmin":
        raise HTTPException(status_code=403, detail="Accès réservé aux super-administrateurs")
    count = seed_library(validated_by=f"user_{user_id}")
    return {"success": True, "inserted": count, "message": f"{count} exemple(s) ajouté(s)"}
