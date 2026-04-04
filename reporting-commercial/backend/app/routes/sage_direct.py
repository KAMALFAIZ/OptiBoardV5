"""
Sage Direct — Accès lecture seule sans synchronisation ETL
Credentials lus depuis APP_DWH_Sources (base centrale OptiBoard_SaaS)
Aucune écriture dans DWH, aucun changement de datasource.
"""
import asyncio
import logging
import pyodbc
from datetime import date, datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from ..database_unified import execute_central

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sage-direct", tags=["Sage Direct"])


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_sage_credentials(dwh_code: str, code_societe: str) -> Dict[str, Any]:
    """Récupère les credentials Sage depuis APP_DWH_Sources (lecture seule)."""
    rows = execute_central(
        """
        SELECT serveur_sage, base_sage, user_sage, password_sage, nom_societe
        FROM APP_DWH_Sources
        WHERE dwh_code = ? AND code_societe = ? AND actif = 1
        """,
        (dwh_code, code_societe),
        use_cache=False,
    )
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"Source Sage '{code_societe}' introuvable ou inactive pour ce DWH"
        )
    return rows[0]


def _open_sage_connection(creds: Dict[str, Any]) -> pyodbc.Connection:
    """Ouvre une connexion temporaire vers la base Sage (fermée après chaque requête).
    Utilise Windows Auth si user_sage est vide, sinon SQL Auth.
    """
    user = (creds.get('user_sage') or '').strip()
    pwd  = (creds.get('password_sage') or '').strip()

    if user:
        # SQL Server Auth
        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={creds['serveur_sage']};"
            f"DATABASE={creds['base_sage']};"
            f"UID={user};PWD={pwd};"
            f"TrustServerCertificate=yes;Connection Timeout=15;"
        )
    else:
        # Windows Auth (Trusted Connection)
        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={creds['serveur_sage']};"
            f"DATABASE={creds['base_sage']};"
            f"Trusted_Connection=yes;"
            f"TrustServerCertificate=yes;Connection Timeout=15;"
        )
    try:
        return pyodbc.connect(conn_str)
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Connexion Sage impossible : {str(e)}"
        )


def _rows_to_list(cursor) -> List[Dict[str, Any]]:
    """Convertit les résultats pyodbc en liste de dicts sérialisables."""
    cols = [c[0] for c in cursor.description]
    result = []
    for row in cursor.fetchall():
        d = {}
        for col, val in zip(cols, row):
            if isinstance(val, (datetime, date)):
                d[col] = val.isoformat()
            elif isinstance(val, bytes):
                d[col] = val.hex()
            else:
                d[col] = val
        result.append(d)
    return result


def _require_dwh(dwh_code: Optional[str]) -> str:
    if not dwh_code:
        raise HTTPException(status_code=400, detail="Header X-DWH-Code manquant")
    return dwh_code


# ─── Schemas ──────────────────────────────────────────────────────────────────

class EnteteRequest(BaseModel):
    code_societe: str
    date_debut: Optional[str] = None   # format YYYY-MM-DD
    date_fin: Optional[str] = None     # format YYYY-MM-DD
    type_doc: Optional[int] = None     # 6=Facture, 7=Avoir, None=Tous (6+7)
    code_tiers: Optional[str] = None   # filtre optionnel par client
    limit: int = 200


class LigneRequest(BaseModel):
    code_societe: str
    numero_piece: str


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/societes")
async def list_sage_societes(
    dwh_code: Optional[str] = Header(None, alias="X-DWH-Code")
):
    """Liste les sources Sage actives pour ce DWH (depuis APP_DWH_Sources)."""
    code = _require_dwh(dwh_code)

    def _fetch():
        return execute_central(
            """
            SELECT code_societe, nom_societe, serveur_sage, base_sage, etl_enabled
            FROM APP_DWH_Sources
            WHERE dwh_code = ? AND actif = 1
            ORDER BY nom_societe
            """,
            (code,),
            use_cache=False,
        )

    rows = await asyncio.to_thread(_fetch)
    return {"success": True, "data": rows}


@router.post("/entetes")
async def get_entetes_sage(
    body: EnteteRequest,
    dwh_code: Optional[str] = Header(None, alias="X-DWH-Code")
):
    """
    Lecture directe de F_DOCENTETE dans la base Sage.
    Aucune écriture — connexion fermée après la requête.
    """
    code = _require_dwh(dwh_code)

    def _query():
        creds = _get_sage_credentials(code, body.code_societe)
        conn = _open_sage_connection(creds)
        try:
            cursor = conn.cursor()

            # Types de documents : factures (6) et avoirs (7) par défaut
            conditions = []
            params: List[Any] = []

            if body.type_doc is not None:
                conditions.append("DO_Type = ?")
                params.append(body.type_doc)
            else:
                conditions.append("DO_Type IN (6, 7)")

            if body.date_debut:
                conditions.append("DO_Date >= ?")
                params.append(body.date_debut)

            if body.date_fin:
                conditions.append("DO_Date <= ?")
                params.append(body.date_fin)

            if body.code_tiers:
                conditions.append("DO_Tiers LIKE ?")
                params.append(f"%{body.code_tiers}%")

            where = " AND ".join(conditions) if conditions else "1=1"
            limit = min(body.limit, 1000)

            sql = f"""
                SELECT TOP {limit}
                    DO_Piece        AS Numero_Piece,
                    DO_Type         AS Type_Doc,
                    CONVERT(varchar(10), DO_Date, 120) AS Date_Doc,
                    DO_Tiers        AS Code_Client,
                    DO_Ref          AS Reference,
                    DO_TotalHT      AS Total_HT,
                    DO_TotalTTC     AS Total_TTC,
                    DO_Statut       AS Statut,
                    DO_Devise       AS Devise,
                    DO_NbFacture    AS Nb_Lignes
                FROM F_DOCENTETE
                WHERE {where}
                ORDER BY DO_Date DESC, DO_Piece DESC
            """
            cursor.execute(sql, params)
            return _rows_to_list(cursor)
        finally:
            conn.close()

    try:
        rows = await asyncio.to_thread(_query)
        return {"success": True, "count": len(rows), "data": rows}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SAGE DIRECT] entetes error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lignes")
async def get_lignes_sage(
    body: LigneRequest,
    dwh_code: Optional[str] = Header(None, alias="X-DWH-Code")
):
    """
    Lecture directe de F_DOCLIGNE pour une pièce donnée.
    Aucune écriture — connexion fermée après la requête.
    """
    code = _require_dwh(dwh_code)

    def _query():
        creds = _get_sage_credentials(code, body.code_societe)
        conn = _open_sage_connection(creds)
        try:
            cursor = conn.cursor()
            sql = """
                SELECT
                    DL_Ligne            AS Num_Ligne,
                    AR_Ref              AS Code_Article,
                    DL_Design           AS Designation,
                    DL_Qte              AS Quantite,
                    DL_PrixUnitaire     AS Prix_Unitaire,
                    DL_PUTTC            AS Prix_TTC,
                    DL_MontantHT        AS Montant_HT,
                    DL_MontantTTC       AS Montant_TTC,
                    DL_Remise01REM_Valeur AS Remise,
                    EU_Enumere          AS Unite,
                    DL_CodeTaxe1        AS Code_Taxe,
                    FA_CodeFamille      AS Famille
                FROM F_DOCLIGNE
                WHERE DO_Piece = ?
                ORDER BY DL_Ligne
            """
            cursor.execute(sql, (body.numero_piece,))
            return _rows_to_list(cursor)
        finally:
            conn.close()

    try:
        rows = await asyncio.to_thread(_query)
        return {"success": True, "count": len(rows), "data": rows}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SAGE DIRECT] lignes error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
