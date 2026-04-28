"""Routes pour le module Classeurs (Spreadsheet) — stockage de classeurs tabulaires par utilisateur"""
import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel

from ..database_unified import (
    central_cursor as get_db_cursor,
    execute_central as execute_query,
)

logger = logging.getLogger("Spreadsheet")

_tables_initialized = False


# =============================================================================
# INITIALISATION TABLE
# =============================================================================

def init_spreadsheet_tables() -> bool:
    global _tables_initialized
    if _tables_initialized:
        return True

    ddl = """
    IF NOT EXISTS (SELECT * FROM sys.objects WHERE name = 'APP_Spreadsheets' AND type = 'U')
    CREATE TABLE APP_Spreadsheets (
        id          INT IDENTITY(1,1) PRIMARY KEY,
        user_id     INT NOT NULL,
        name        NVARCHAR(255) NOT NULL DEFAULT 'Nouveau classeur',
        data        NVARCHAR(MAX) NOT NULL DEFAULT '{}',
        created_at  DATETIME DEFAULT GETDATE(),
        updated_at  DATETIME DEFAULT GETDATE()
    )
    """
    try:
        with get_db_cursor() as cursor:
            cursor.execute(ddl)
        _tables_initialized = True
        logger.info("Table APP_Spreadsheets initialisee.")
        return True
    except Exception as e:
        logger.error(f"init_spreadsheet_tables: {e}")
        return False


# =============================================================================
# ROUTER
# =============================================================================

router = APIRouter(prefix="/api/spreadsheet", tags=["spreadsheet"])


# =============================================================================
# MODELES
# =============================================================================

class SpreadsheetCreate(BaseModel):
    user_id: int
    name: str = "Nouveau classeur"
    data: Dict[str, Any] = {}


class SpreadsheetUpdate(BaseModel):
    name: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/list")
async def list_spreadsheets(user_id: int = Query(...)):
    """Liste les classeurs d'un utilisateur."""
    try:
        init_spreadsheet_tables()
        rows = execute_query(
            """SELECT id, user_id, name, created_at, updated_at
               FROM APP_Spreadsheets
               WHERE user_id = ?
               ORDER BY updated_at DESC""",
            (user_id,),
            use_cache=False,
        )
        return {"success": True, "data": rows or []}
    except Exception as e:
        logger.error(f"list_spreadsheets(user_id={user_id}): {e}")
        return {"success": False, "error": str(e), "data": []}


@router.get("/{spreadsheet_id}")
async def get_spreadsheet(spreadsheet_id: int):
    """Recupere un classeur avec ses donnees."""
    try:
        rows = execute_query(
            "SELECT * FROM APP_Spreadsheets WHERE id = ?",
            (spreadsheet_id,),
            use_cache=False,
        )
        if not rows:
            raise HTTPException(status_code=404, detail="Classeur non trouve")
        item = dict(rows[0])
        raw = item.get("data") or "{}"
        item["data"] = json.loads(raw) if isinstance(raw, str) else raw
        return {"success": True, "data": item}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_spreadsheet({spreadsheet_id}): {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def create_spreadsheet(payload: SpreadsheetCreate):
    """Cree un nouveau classeur."""
    try:
        init_spreadsheet_tables()
        data_json = json.dumps(payload.data, ensure_ascii=False)
        with get_db_cursor() as cursor:
            cursor.execute(
                """INSERT INTO APP_Spreadsheets (user_id, name, data)
                   VALUES (?, ?, ?)""",
                (payload.user_id, payload.name, data_json),
            )
            cursor.execute("SELECT @@IDENTITY AS id")
            row = cursor.fetchone()
            new_id = int(row[0]) if row else None
        return {"success": True, "id": new_id, "message": "Classeur cree"}
    except Exception as e:
        logger.error(f"create_spreadsheet: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{spreadsheet_id}")
async def update_spreadsheet(spreadsheet_id: int, payload: SpreadsheetUpdate):
    """Met a jour le nom et/ou les donnees d'un classeur."""
    try:
        updates: List[str] = []
        params: List[Any] = []

        if payload.name is not None:
            updates.append("name = ?")
            params.append(payload.name)
        if payload.data is not None:
            updates.append("data = ?")
            params.append(json.dumps(payload.data, ensure_ascii=False))

        if not updates:
            return {"success": False, "message": "Aucune modification fournie"}

        updates.append("updated_at = GETDATE()")
        params.append(spreadsheet_id)
        query = f"UPDATE APP_Spreadsheets SET {', '.join(updates)} WHERE id = ?"

        with get_db_cursor() as cursor:
            cursor.execute(query, tuple(params))

        return {"success": True, "message": "Classeur mis a jour"}
    except Exception as e:
        logger.error(f"update_spreadsheet({spreadsheet_id}): {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{spreadsheet_id}")
async def delete_spreadsheet(spreadsheet_id: int):
    """Supprime un classeur."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("DELETE FROM APP_Spreadsheets WHERE id = ?", (spreadsheet_id,))
        return {"success": True, "message": "Classeur supprime"}
    except Exception as e:
        logger.error(f"delete_spreadsheet({spreadsheet_id}): {e}")
        raise HTTPException(status_code=400, detail=str(e))
