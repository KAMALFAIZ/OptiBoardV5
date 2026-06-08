"""
Sage Direct Config — API Admin
================================
CRUD pour gérer les mappings de vues Sage Direct
(table APP_Sage_View_Config).
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from ..sage_direct import db_store

router = APIRouter(prefix="/api/admin/sage-config", tags=["Sage Config Admin"])


class MappingCreate(BaseModel):
    table_name: str
    sage_sql: str
    is_stub: bool = False
    description: Optional[str] = None


class MappingUpdate(BaseModel):
    table_name: Optional[str] = None
    sage_sql: Optional[str] = None
    is_stub: Optional[bool] = None
    actif: Optional[bool] = None
    description: Optional[str] = None


class TestMappingRequest(BaseModel):
    sage_sql: str
    db_name: str = "bijou"
    societe_code: str = "TEST"
    # dwh_code optionnel — si absent, résolu automatiquement depuis APP_DWH_Sources
    dwh_code: Optional[str] = None


@router.get("")
async def list_mappings(include_inactive: bool = True):
    """Liste tous les mappings Sage Direct."""
    try:
        data = db_store.list_all(include_inactive=include_inactive)
        # Convertir dates en string
        for row in data:
            for k in ("created_at", "updated_at"):
                if row.get(k):
                    row[k] = row[k].isoformat()
        return {"success": True, "data": data, "total": len(data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{mapping_id}")
async def get_mapping(mapping_id: int):
    """Récupère un mapping par son ID."""
    try:
        mapping = db_store.get_one(mapping_id)
        if not mapping:
            raise HTTPException(status_code=404, detail="Mapping non trouvé")
        for k in ("created_at", "updated_at"):
            if mapping.get(k):
                mapping[k] = mapping[k].isoformat()
        return {"success": True, "data": mapping}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def create_mapping(payload: MappingCreate):
    """Crée un nouveau mapping."""
    try:
        if not payload.table_name.strip():
            raise HTTPException(400, "table_name requis")
        if not payload.sage_sql.strip():
            raise HTTPException(400, "sage_sql requis")

        new_id = db_store.create_mapping(
            table_name=payload.table_name.strip(),
            sage_sql=payload.sage_sql.strip(),
            is_stub=payload.is_stub,
            description=payload.description,
        )
        return {"success": True, "id": new_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{mapping_id}")
async def update_mapping(mapping_id: int, payload: MappingUpdate):
    """Met à jour un mapping existant."""
    try:
        ok = db_store.update_mapping(
            mapping_id=mapping_id,
            table_name=payload.table_name,
            sage_sql=payload.sage_sql,
            is_stub=payload.is_stub,
            actif=payload.actif,
            description=payload.description,
        )
        if not ok:
            raise HTTPException(400, "Aucun champ à mettre à jour")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{mapping_id}")
async def delete_mapping(mapping_id: int):
    """Supprime un mapping."""
    try:
        db_store.delete_mapping(mapping_id)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset")
async def reset_mappings():
    """Réinitialise depuis config.py (remplace tous les mappings)."""
    try:
        count = db_store.reset_to_static_config()
        return {
            "success": True,
            "message": f"{count} mappings réinitialisés depuis config.py",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/invalidate-cache")
async def invalidate_cache():
    """Force le rechargement du cache (utile après modification externe)."""
    db_store.invalidate_cache()
    return {"success": True, "message": "Cache invalidé"}


@router.post("/test-sql")
async def test_sql(payload: TestMappingRequest):
    """
    Teste une requête Sage avec les placeholders {db} et {societe}.
    Exécute en LIMIT 5 pour valider la syntaxe.
    """
    try:
        sql = payload.sage_sql.format(
            db=payload.db_name,
            societe=payload.societe_code,
        )
        # Préfixe TOP 5 (SQL Server) pour limiter
        sql_test = f"SELECT TOP 5 * FROM (\n{sql}\n) AS _test"

        import pyodbc
        from ..database_unified import execute_central
        from ..services.credential_resolver import CredentialResolver, SageSourceNotFoundError

        # Résoudre le dwh_code si non fourni (lookup via APP_DWH_Sources)
        dwh_code = payload.dwh_code
        if not dwh_code:
            lookup = execute_central(
                "SELECT TOP 1 dwh_code FROM APP_DWH_Sources WHERE code_societe = ? AND actif = 1",
                (payload.societe_code,),
                use_cache=False,
            )
            if not lookup:
                lookup = execute_central(
                    "SELECT TOP 1 dwh_code FROM APP_DWH_Sources WHERE actif = 1 ORDER BY id",
                    use_cache=False,
                )
            if not lookup:
                raise HTTPException(400, "Aucune source Sage configurée — précisez dwh_code dans la requête")
            dwh_code = lookup[0]["dwh_code"]

        # Résoudre les credentials via CredentialResolver (source : APP_ETL_Agents puis fallback APP_DWH_Sources)
        try:
            creds = CredentialResolver.get(dwh_code=dwh_code, societe_code=payload.societe_code)
        except SageSourceNotFoundError:
            raise HTTPException(400, f"Aucune source Sage trouvée pour DWH={dwh_code} / societe={payload.societe_code}")

        user = (creds.username or "").strip()
        pwd  = (creds.password or "").strip()
        if user:
            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={creds.serveur};DATABASE={creds.base};"
                f"UID={user};PWD={pwd};"
                f"TrustServerCertificate=yes;Connection Timeout=15;"
            )
        else:
            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={creds.serveur};DATABASE={creds.base};"
                f"Trusted_Connection=yes;"
                f"TrustServerCertificate=yes;Connection Timeout=15;"
            )

        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute(sql_test)

        columns = [c[0] for c in cursor.description] if cursor.description else []
        rows_raw = cursor.fetchall()
        rows = []
        for r in rows_raw:
            rows.append({
                col: (str(val) if val is not None else None)
                for col, val in zip(columns, r)
            })
        conn.close()

        return {
            "success": True,
            "columns": columns,
            "rows": rows,
            "nb_rows": len(rows),
        }
    except HTTPException:
        raise
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "columns": [],
            "rows": [],
        }
