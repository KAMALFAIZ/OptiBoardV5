"""
ETL Tables — Gestion centralisee et publication
================================================
Architecture :
  - CENTRAL : cree/modifie les tables ETL (APP_ETL_Tables_Config)
  - PUBLICATION : central publie vers bases clients (APP_ETL_Tables_Published)
  - CLIENT : lecture seule + on/off + soumettre propositions
  - PROPOSITIONS : client propose → central valide → publie si ok
"""
import logging
import json
import pyodbc
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Query, Header
from pydantic import BaseModel

from ..database_unified import (
    execute_central, write_central, central_cursor,
    execute_client, write_client, client_cursor,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/etl-tables", tags=["ETL Tables"])


def clean_pk_columns(pks: List[str]) -> List[str]:
    """
    Nettoie les noms de colonnes PK : supprime crochets SQL et guillemets.
    Ex: ["[N° interne]"] → ["N° interne"]  |  ["cbMarq"] → ["cbMarq"]
    Empeche le stockage de ["[col]"] qui cause des [[col]] en C#.
    """
    result = []
    for pk in pks:
        clean = pk.strip().strip('[').strip(']').strip('"').strip('[').strip(']').strip()
        if clean:
            result.append(clean)
    return result


# ============================================================
# Schemas Pydantic
# ============================================================

class ETLTableCreate(BaseModel):
    code: str
    table_name: str
    target_table: str
    source_query: str
    primary_key_columns: List[str]
    sync_type: str = "incremental"
    timestamp_column: str = "cbModification"
    interval_minutes: int = 5
    priority: str = "normal"
    delete_detection: bool = False
    description: Optional[str] = None

class ETLTableUpdate(BaseModel):
    table_name: Optional[str] = None
    target_table: Optional[str] = None
    source_query: Optional[str] = None
    primary_key_columns: Optional[List[str]] = None
    sync_type: Optional[str] = None
    timestamp_column: Optional[str] = None
    interval_minutes: Optional[int] = None
    priority: Optional[str] = None
    delete_detection: Optional[bool] = None
    description: Optional[str] = None
    actif: Optional[bool] = None

class ETLTableToggle(BaseModel):
    is_enabled: bool

class ETLProposalCreate(BaseModel):
    table_name: str
    target_table: Optional[str] = None
    source_query: Optional[str] = None
    description: str
    justification: str

class ETLProposalValidate(BaseModel):
    statut: str          # validee | rejetee
    commentaire: Optional[str] = None
    publier_si_valide: bool = True   # publier automatiquement si validee

class PublishToClientsRequest(BaseModel):
    codes: Optional[List[str]] = None      # None = toutes les tables actives
    dwh_codes: Optional[List[str]] = None  # None = tous les clients actifs


# ============================================================
# HELPERS
# ============================================================

def _build_client_conn_str(client_info: Dict) -> str:
    from ..config_multitenant import get_central_settings
    central = get_central_settings()
    server   = client_info.get('db_server')   or central._effective_server
    db_name  = client_info.get('db_name')     or ''
    user     = client_info.get('db_user')     or central._effective_user
    password = client_info.get('db_password') or central._effective_password
    return (
        f"DRIVER={central._effective_driver};"
        f"SERVER={server};"
        f"DATABASE={db_name};"
        f"UID={user};"
        f"PWD={password};"
        "TrustServerCertificate=yes;"
    )

def _get_all_active_clients() -> List[Dict]:
    """Recupere tous les clients actifs avec leurs infos de connexion (APP_ClientDB)."""
    return execute_central(
        """SELECT d.code, d.nom, c.db_name, c.db_server, c.db_user, c.db_password
           FROM APP_DWH d
           JOIN APP_ClientDB c ON d.code = c.dwh_code
           WHERE d.actif = 1 AND c.actif = 1
           ORDER BY d.nom""",
        use_cache=False
    )

def _publish_table_to_client(table: Dict, client: Dict) -> Dict:
    """Publie une table ETL vers la base d'un client (upsert dans APP_ETL_Tables_Published)."""
    try:
        conn_str = _build_client_conn_str(client)
        conn = pyodbc.connect(conn_str, timeout=15)
        conn.autocommit = False
        cursor = conn.cursor()

        # Verifier si la table existe deja chez le client
        cursor.execute(
            "SELECT id, is_enabled FROM APP_ETL_Tables_Published WHERE code = ?",
            (table['code'],)
        )
        existing = cursor.fetchone()

        if existing:
            version_precedente = existing[1] if len(existing) > 1 else None
            # UPDATE — ne pas toucher is_enabled (droit du client)
            cursor.execute(
                """UPDATE APP_ETL_Tables_Published SET
                     table_name = ?, target_table = ?, source_query = ?,
                     primary_key_columns = ?, sync_type = ?, timestamp_column = ?,
                     interval_minutes = ?, priority = ?, delete_detection = ?,
                     description = ?, version_centrale = ?,
                     date_publication = GETDATE()
                   WHERE code = ?""",
                (
                    table['table_name'], table['target_table'], table['source_query'],
                    table['primary_key_columns'], table['sync_type'], table['timestamp_column'],
                    table['interval_minutes'], table['priority'], table['delete_detection'],
                    table['description'], table['version'],
                    table['code']
                )
            )
            action = "updated"
        else:
            version_precedente = None
            # INSERT
            cursor.execute(
                """INSERT INTO APP_ETL_Tables_Published
                     (code, table_name, target_table, source_query, primary_key_columns,
                      sync_type, timestamp_column, interval_minutes, priority,
                      delete_detection, description, version_centrale, is_enabled, date_publication)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,1,GETDATE())""",
                (
                    table['code'], table['table_name'], table['target_table'],
                    table['source_query'], table['primary_key_columns'],
                    table['sync_type'], table['timestamp_column'],
                    table['interval_minutes'], table['priority'],
                    table['delete_detection'], table['description'], table['version']
                )
            )
            action = "published"

        # Enregistrer dans APP_Update_History (traçabilite MAJ)
        try:
            cursor.execute(
                """IF NOT EXISTS (SELECT 1 FROM sysobjects WHERE name='APP_Update_History' AND xtype='U')
                   RETURN;
                   INSERT INTO APP_Update_History
                     (type_entite, code_entite, nom_entite, version_precedente,
                      version_installee, statut, date_installation)
                   VALUES ('etl_table', ?, ?, ?, ?, 'succes', GETDATE())""",
                (table['code'], table['table_name'], version_precedente, table['version'])
            )
        except Exception:
            pass  # Non bloquant

        conn.commit()
        conn.close()
        return {"success": True, "action": action, "client": client['code']}

    except Exception as e:
        logger.error(f"Erreur publication table {table['code']} -> {client['code']}: {e}")
        return {"success": False, "error": str(e), "client": client['code']}


# ============================================================
# ROUTES CENTRAL — Gestion des tables ETL
# ============================================================

@router.get("/central")
async def list_central_tables(actif: Optional[bool] = Query(None)):
    """[CENTRAL] Liste toutes les tables ETL configurees."""
    try:
        query = "SELECT * FROM APP_ETL_Tables_Config WHERE 1=1"
        params = []
        if actif is not None:
            query += " AND actif = ?"
            params.append(1 if actif else 0)
        query += " ORDER BY priority DESC, table_name"
        tables = execute_central(query, tuple(params) if params else None, use_cache=False)
        return {"success": True, "data": tables, "count": len(tables)}
    except Exception as e:
        if "invalid object name" in str(e).lower():
            return {"success": True, "data": [], "count": 0,
                    "warning": "Table APP_ETL_Tables_Config non initialisee. Executez 001_central_schema.sql"}
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/central")
async def create_central_table(table: ETLTableCreate):
    """[CENTRAL] Cree une nouvelle table ETL."""
    try:
        with central_cursor() as cursor:
            cursor.execute(
                """INSERT INTO APP_ETL_Tables_Config
                     (code, table_name, target_table, source_query, primary_key_columns,
                      sync_type, timestamp_column, interval_minutes, priority,
                      delete_detection, description, version, actif, date_creation)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,1,1,GETDATE())""",
                (
                    table.code, table.table_name, table.target_table, table.source_query,
                    json.dumps(clean_pk_columns(table.primary_key_columns)),
                    table.sync_type, table.timestamp_column, table.interval_minutes,
                    table.priority, 1 if table.delete_detection else 0,
                    table.description
                )
            )
            cursor.commit()
        return {"success": True, "message": f"Table '{table.code}' creee"}
    except Exception as e:
        if "unique" in str(e).lower() or "violation" in str(e).lower():
            raise HTTPException(status_code=409, detail=f"Code '{table.code}' deja existant")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/central/{code}")
async def update_central_table(code: str, update: ETLTableUpdate):
    """[CENTRAL] Modifie une table ETL et incremente la version."""
    try:
        fields = []
        params = []
        if update.table_name is not None:
            fields.append("table_name = ?"); params.append(update.table_name)
        if update.target_table is not None:
            fields.append("target_table = ?"); params.append(update.target_table)
        if update.source_query is not None:
            fields.append("source_query = ?"); params.append(update.source_query)
        if update.primary_key_columns is not None:
            fields.append("primary_key_columns = ?"); params.append(json.dumps(clean_pk_columns(update.primary_key_columns)))
        if update.sync_type is not None:
            fields.append("sync_type = ?"); params.append(update.sync_type)
        if update.timestamp_column is not None:
            fields.append("timestamp_column = ?"); params.append(update.timestamp_column)
        if update.interval_minutes is not None:
            fields.append("interval_minutes = ?"); params.append(update.interval_minutes)
        if update.priority is not None:
            fields.append("priority = ?"); params.append(update.priority)
        if update.delete_detection is not None:
            fields.append("delete_detection = ?"); params.append(1 if update.delete_detection else 0)
        if update.description is not None:
            fields.append("description = ?"); params.append(update.description)
        if update.actif is not None:
            fields.append("actif = ?"); params.append(1 if update.actif else 0)

        if not fields:
            raise HTTPException(status_code=400, detail="Aucun champ a mettre a jour")

        # Incrementer la version a chaque modification
        fields.append("version = version + 1")
        fields.append("date_modification = GETDATE()")
        params.append(code)

        write_central(
            f"UPDATE APP_ETL_Tables_Config SET {', '.join(fields)} WHERE code = ?",
            tuple(params)
        )
        return {"success": True, "message": f"Table '{code}' mise a jour"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/central/{code}")
async def delete_central_table(code: str):
    """[CENTRAL] Supprime une table ETL."""
    try:
        write_central("DELETE FROM APP_ETL_Tables_Config WHERE code = ?", (code,))
        return {"success": True, "message": f"Table '{code}' supprimee"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# ROUTES CENTRAL — Publication vers clients
# ============================================================

@router.post("/central/publish")
async def publish_tables_to_clients(req: PublishToClientsRequest):
    """
    [CENTRAL] Publie les tables ETL vers toutes les bases clients.
    - codes=None  → toutes les tables actives
    - dwh_codes=None → tous les clients actifs
    """
    try:
        # 1. Charger les tables a publier
        if req.codes:
            placeholders = ','.join(['?' for _ in req.codes])
            tables = execute_central(
                f"SELECT * FROM APP_ETL_Tables_Config WHERE code IN ({placeholders}) AND actif = 1",
                tuple(req.codes), use_cache=False
            )
        else:
            tables = execute_central(
                "SELECT * FROM APP_ETL_Tables_Config WHERE actif = 1",
                use_cache=False
            )

        if not tables:
            return {"success": False, "message": "Aucune table a publier"}

        # 2. Charger les clients cibles
        if req.dwh_codes:
            placeholders = ','.join(['?' for _ in req.dwh_codes])
            clients = execute_central(
                f"""SELECT d.code, d.nom, c.db_name, c.db_server, c.db_user, c.db_password
                    FROM APP_DWH d
                    JOIN APP_ClientDB c ON d.code = c.dwh_code
                    WHERE d.code IN ({placeholders}) AND d.actif = 1 AND c.actif = 1""",
                tuple(req.dwh_codes), use_cache=False
            )
        else:
            clients = _get_all_active_clients()

        if not clients:
            return {"success": False, "message": "Aucun client cible"}

        # 3. Publier
        results = {"published": 0, "updated": 0, "failed": 0, "details": []}
        for client in clients:
            if not client.get('db_name'):
                continue
            for table in tables:
                res = _publish_table_to_client(table, client)
                if res['success']:
                    if res['action'] == 'published':
                        results['published'] += 1
                    else:
                        results['updated'] += 1
                    # Log publication
                    try:
                        write_central(
                            """INSERT INTO APP_Publish_Log
                                 (entity_type, entity_code, dwh_code, action, date_publication)
                               VALUES ('etl_table', ?, ?, ?, GETDATE())""",
                            (table['code'], client['code'], res['action'])
                        )
                    except Exception:
                        pass
                else:
                    results['failed'] += 1
                    results['details'].append(res)

        return {"success": True, "results": results,
                "tables": len(tables), "clients": len(clients)}

    except Exception as e:
        logger.error(f"Erreur publication ETL tables: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/central/publish-log")
async def get_publish_log(dwh_code: Optional[str] = Query(None), limit: int = Query(50)):
    """[CENTRAL] Historique des publications."""
    try:
        query = """SELECT * FROM APP_Publish_Log
                   WHERE entity_type = 'etl_table'"""
        params = []
        if dwh_code:
            query += " AND dwh_code = ?"
            params.append(dwh_code)
        query += f" ORDER BY date_publication DESC OFFSET 0 ROWS FETCH NEXT {limit} ROWS ONLY"
        logs = execute_central(query, tuple(params) if params else None, use_cache=False)
        return {"success": True, "data": logs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# ROUTES CLIENT — Tables publiees (lecture seule + on/off)
# ============================================================

@router.get("/client")
async def list_client_tables(
    x_dwh_code: str = Header(..., alias="X-DWH-Code")
):
    """
    [CLIENT] Liste les tables ETL publiees par le central.
    Lecture seule — le client peut uniquement voir et toggler is_enabled.
    """
    try:
        tables = execute_client(
            """SELECT id, code, table_name, target_table, description,
                      sync_type, interval_minutes, priority, delete_detection,
                      is_enabled, version_centrale, date_publication
               FROM APP_ETL_Tables_Published
               ORDER BY priority DESC, table_name""",
            use_cache=False
        )
        return {"success": True, "data": tables, "count": len(tables)}
    except Exception as e:
        if "invalid object name" in str(e).lower():
            return {"success": True, "data": [], "count": 0,
                    "warning": "Tables ETL non encore publiees par l'administrateur"}
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/client/{code}/toggle")
async def toggle_client_table(
    code: str,
    toggle: ETLTableToggle,
    x_dwh_code: str = Header(..., alias="X-DWH-Code")
):
    """
    [CLIENT] Active ou desactive une table ETL.
    C'est le SEUL droit de modification du client sur les tables ETL.
    """
    try:
        write_client(
            """UPDATE APP_ETL_Tables_Published
               SET is_enabled = ?, date_modification = GETDATE()
               WHERE code = ?""",
            (1 if toggle.is_enabled else 0, code)
        )
        statut = "activee" if toggle.is_enabled else "desactivee"
        return {"success": True, "message": f"Table '{code}' {statut}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# ROUTES CLIENT — Tables personnalisees (APP_ETL_Tables_Config client)
# ============================================================

@router.get("/client/custom")
async def list_client_custom_tables(
    x_dwh_code: str = Header(..., alias="X-DWH-Code")
):
    """
    [CLIENT] Liste les tables ETL propres au client
    (APP_ETL_Tables_Config dans la base OptiBoard_XXX du client).
    Ces tables sont publiees uniquement vers l'agent ETL de ce client.
    """
    try:
        tables = execute_client(
            """SELECT id, code, table_name, target_table, source_query,
                      primary_key_columns, sync_type, timestamp_column,
                      interval_minutes, priority, delete_detection,
                      description, version, actif, date_creation, date_modification
               FROM APP_ETL_Tables_Config
               ORDER BY table_name""",
            use_cache=False
        )
        return {"success": True, "data": tables, "count": len(tables)}
    except Exception as e:
        if "invalid object name" in str(e).lower():
            return {"success": True, "data": [], "count": 0,
                    "warning": "Table APP_ETL_Tables_Config non initialisee dans la base client"}
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/client/custom")
async def create_client_custom_table(
    table: ETLTableCreate,
    x_dwh_code: str = Header(..., alias="X-DWH-Code")
):
    """[CLIENT] Cree une table ETL personnalisee dans la base client."""
    try:
        with client_cursor(x_dwh_code) as cursor:
            cursor.execute(
                """INSERT INTO APP_ETL_Tables_Config
                     (code, table_name, target_table, source_query, primary_key_columns,
                      sync_type, timestamp_column, interval_minutes, priority,
                      delete_detection, description, version, actif, date_creation)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,1,1,GETDATE())""",
                (
                    table.code, table.table_name, table.target_table, table.source_query,
                    json.dumps(clean_pk_columns(table.primary_key_columns)),
                    table.sync_type, table.timestamp_column, table.interval_minutes,
                    table.priority, 1 if table.delete_detection else 0,
                    table.description
                )
            )
            cursor.commit()
        return {"success": True, "message": f"Table '{table.code}' creee"}
    except Exception as e:
        if "unique" in str(e).lower() or "violation" in str(e).lower():
            raise HTTPException(status_code=409, detail=f"Code '{table.code}' deja existant")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/client/custom/{code}")
async def update_client_custom_table(
    code: str,
    update: ETLTableUpdate,
    x_dwh_code: str = Header(..., alias="X-DWH-Code")
):
    """[CLIENT] Modifie une table ETL personnalisee."""
    try:
        fields = []
        params = []
        if update.table_name is not None:
            fields.append("table_name = ?"); params.append(update.table_name)
        if update.target_table is not None:
            fields.append("target_table = ?"); params.append(update.target_table)
        if update.source_query is not None:
            fields.append("source_query = ?"); params.append(update.source_query)
        if update.primary_key_columns is not None:
            fields.append("primary_key_columns = ?"); params.append(json.dumps(clean_pk_columns(update.primary_key_columns)))
        if update.sync_type is not None:
            fields.append("sync_type = ?"); params.append(update.sync_type)
        if update.timestamp_column is not None:
            fields.append("timestamp_column = ?"); params.append(update.timestamp_column)
        if update.interval_minutes is not None:
            fields.append("interval_minutes = ?"); params.append(update.interval_minutes)
        if update.priority is not None:
            fields.append("priority = ?"); params.append(update.priority)
        if update.delete_detection is not None:
            fields.append("delete_detection = ?"); params.append(1 if update.delete_detection else 0)
        if update.description is not None:
            fields.append("description = ?"); params.append(update.description)
        if update.actif is not None:
            fields.append("actif = ?"); params.append(1 if update.actif else 0)

        if not fields:
            raise HTTPException(status_code=400, detail="Aucun champ a mettre a jour")

        fields.append("version = version + 1")
        fields.append("date_modification = GETDATE()")
        params.append(code)

        write_client(
            f"UPDATE APP_ETL_Tables_Config SET {', '.join(fields)} WHERE code = ?",
            tuple(params)
        )
        return {"success": True, "message": f"Table '{code}' mise a jour"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/client/custom/{code}")
async def delete_client_custom_table(
    code: str,
    x_dwh_code: str = Header(..., alias="X-DWH-Code")
):
    """[CLIENT] Supprime une table ETL personnalisee."""
    try:
        write_client(
            "DELETE FROM APP_ETL_Tables_Config WHERE code = ?",
            (code,)
        )
        return {"success": True, "message": f"Table '{code}' supprimee"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/client/custom/publish")
async def publish_client_custom_tables(
    x_dwh_code: str = Header(..., alias="X-DWH-Code")
):
    """
    [CLIENT] Publie les tables ETL personnalisees vers l'agent ETL du client.
    Les tables actives de APP_ETL_Tables_Config (base client) sont inserees /
    mises a jour dans APP_ETL_Agent_Tables (base centrale) pour l'agent
    appartenant a ce client (dwh_code = x_dwh_code).
    """
    try:
        # 1. Charger les tables actives du client
        tables = execute_client(
            """SELECT code, table_name, target_table, source_query,
                      primary_key_columns, sync_type, timestamp_column,
                      interval_minutes, priority, delete_detection, description
               FROM APP_ETL_Tables_Config
               WHERE actif = 1
               ORDER BY table_name""",
            use_cache=False
        )

        if not tables:
            return {"success": False, "message": "Aucune table active a publier"}

        # 2. Recuperer l'agent du client depuis la BASE CLIENT (pas centrale)
        # Logique metier : les agents sont maintenant dans la base client
        agents = execute_client(
            "SELECT agent_id FROM APP_ETL_Agents WHERE is_active = 1",
            use_cache=False
        )

        if not agents:
            return {"success": False, "message": "Aucun agent actif pour ce client"}

        agent_id = agents[0]["agent_id"]

        # 3. Upsert chaque table dans APP_ETL_Agent_Tables (base centrale)
        published = 0
        updated = 0
        failed = 0
        details = []

        for table in tables:
            try:
                pk_json = table["primary_key_columns"]
                # Normaliser en JSON si c'est deja une chaine
                if isinstance(pk_json, str):
                    try:
                        import json as _json
                        _json.loads(pk_json)  # valider
                    except Exception:
                        pk_json = json.dumps([pk_json])
                else:
                    pk_json = json.dumps(pk_json)

                existing = execute_central(
                    "SELECT id FROM APP_ETL_Agent_Tables WHERE agent_id = ? AND table_name = ?",
                    (agent_id, table["table_name"]), use_cache=False
                )

                if existing:
                    write_central(
                        """UPDATE APP_ETL_Agent_Tables SET
                             source_query = ?, target_table = ?,
                             primary_key_columns = ?, sync_type = ?,
                             timestamp_column = ?, priority = ?,
                             delete_detection = ?, description = ?,
                             updated_at = GETDATE()
                           WHERE agent_id = ? AND table_name = ?""",
                        (
                            table["source_query"], table["target_table"],
                            pk_json, table["sync_type"],
                            table.get("timestamp_column", "cbModification"),
                            table["priority"],
                            1 if table.get("delete_detection") else 0,
                            table.get("description"),
                            agent_id, table["table_name"]
                        )
                    )
                    updated += 1
                else:
                    write_central(
                        """INSERT INTO APP_ETL_Agent_Tables
                             (agent_id, table_name, source_query, target_table,
                              societe_code, primary_key_columns, sync_type,
                              timestamp_column, priority, is_enabled,
                              delete_detection, description,
                              is_inherited, is_customized, created_at)
                           VALUES (?,?,?,?,?,?,?,?,?,1,?,?,0,0,GETDATE())""",
                        (
                            agent_id, table["table_name"], table["source_query"],
                            table["target_table"], "",
                            pk_json, table["sync_type"],
                            table.get("timestamp_column", "cbModification"),
                            table["priority"],
                            1 if table.get("delete_detection") else 0,
                            table.get("description")
                        )
                    )
                    published += 1
            except Exception as e:
                failed += 1
                details.append({"table": table["table_name"], "error": str(e)})
                logger.error(f"Erreur publication table client {table['table_name']}: {e}")

        return {
            "success": True,
            "agent_id": str(agent_id),
            "results": {
                "published": published,
                "updated": updated,
                "failed": failed,
                "details": details,
            },
            "tables": len(tables),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur publication tables client custom: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# ROUTES PROPOSITIONS — Client soumet, Central valide
# ============================================================

@router.post("/proposals")
async def submit_proposal(
    proposal: ETLProposalCreate,
    x_dwh_code: str = Header(..., alias="X-DWH-Code")
):
    """[CLIENT] Soumet une proposition de nouvelle table ETL au central."""
    try:
        # Enregistrer dans la base client
        write_client(
            """INSERT INTO APP_ETL_Proposals
                 (table_name, target_table, source_query, description,
                  justification, statut, date_creation)
               VALUES (?,?,?,?,?,'en_attente',GETDATE())""",
            (
                proposal.table_name, proposal.target_table, proposal.source_query,
                proposal.description, proposal.justification
            )
        )

        # Notifier le central
        try:
            write_central(
                """INSERT INTO APP_ETL_Proposals
                     (dwh_code, table_name, target_table, source_query, description,
                      justification, statut, date_creation)
                   VALUES (?,?,?,?,?,?,'en_attente',GETDATE())""",
                (
                    x_dwh_code, proposal.table_name, proposal.target_table,
                    proposal.source_query, proposal.description, proposal.justification
                )
            )
        except Exception as e:
            logger.warning(f"Proposition non transmise au central: {e}")

        return {"success": True, "message": "Proposition soumise au central"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/proposals/client")
async def list_client_proposals(
    x_dwh_code: str = Header(..., alias="X-DWH-Code")
):
    """[CLIENT] Liste ses propres propositions et leur statut."""
    try:
        proposals = execute_client(
            """SELECT id, table_name, target_table, description, justification,
                      statut, commentaire_central, date_creation, date_reponse
               FROM APP_ETL_Proposals
               ORDER BY date_creation DESC""",
            use_cache=False
        )
        return {"success": True, "data": proposals}
    except Exception as e:
        if "invalid object name" in str(e).lower():
            return {"success": True, "data": []}
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/proposals/central")
async def list_central_proposals(
    statut: Optional[str] = Query(None),
    dwh_code: Optional[str] = Query(None)
):
    """[CENTRAL] Liste toutes les propositions recues des clients."""
    try:
        query = "SELECT * FROM APP_ETL_Proposals WHERE 1=1"
        params = []
        if statut:
            query += " AND statut = ?"
            params.append(statut)
        if dwh_code:
            query += " AND dwh_code = ?"
            params.append(dwh_code)
        query += " ORDER BY date_creation DESC"
        proposals = execute_central(query, tuple(params) if params else None, use_cache=False)
        return {"success": True, "data": proposals, "count": len(proposals)}
    except Exception as e:
        if "invalid object name" in str(e).lower():
            return {"success": True, "data": [], "count": 0}
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/proposals/central/{proposal_id}/validate")
async def validate_proposal(proposal_id: int, validation: ETLProposalValidate):
    """
    [CENTRAL] Valide ou rejette une proposition.
    Si validee et publier_si_valide=True, cree la table dans le central
    et la publie vers le client demandeur.
    """
    try:
        # 1. Recuperer la proposition
        proposals = execute_central(
            "SELECT * FROM APP_ETL_Proposals WHERE id = ?",
            (proposal_id,), use_cache=False
        )
        if not proposals:
            raise HTTPException(status_code=404, detail="Proposition introuvable")
        proposal = proposals[0]

        if proposal['statut'] != 'en_attente':
            raise HTTPException(status_code=400, detail="Proposition deja traitee")

        # 2. Mettre a jour le statut dans le central
        write_central(
            """UPDATE APP_ETL_Proposals SET
                 statut = ?, commentaire_central = ?,
                 date_validation = GETDATE()
               WHERE id = ?""",
            (validation.statut, validation.commentaire, proposal_id)
        )

        result = {"success": True, "statut": validation.statut}

        # 3. Si validee → creer dans APP_ETL_Tables_Config + publier vers ce client
        if validation.statut == 'validee' and validation.publier_si_valide:
            import secrets
            code = f"PROP_{proposal['dwh_code']}_{secrets.token_hex(4).upper()}"
            try:
                write_central(
                    """INSERT INTO APP_ETL_Tables_Config
                         (code, table_name, target_table, source_query,
                          description, version, actif, date_creation)
                       VALUES (?,?,?,?,?,1,1,GETDATE())""",
                    (
                        code, proposal['table_name'],
                        proposal.get('target_table') or proposal['table_name'],
                        proposal.get('source_query', ''),
                        proposal.get('description', '')
                    )
                )
                # Publier uniquement vers le client demandeur
                clients = execute_central(
                    """SELECT code, nom, client_db_server, client_db_name,
                              client_db_user, client_db_password
                       FROM APP_DWH WHERE code = ? AND actif = 1""",
                    (proposal['dwh_code'],), use_cache=False
                )
                if clients:
                    tables = execute_central(
                        "SELECT * FROM APP_ETL_Tables_Config WHERE code = ?",
                        (code,), use_cache=False
                    )
                    if tables:
                        pub_res = _publish_table_to_client(tables[0], clients[0])
                        result["published"] = pub_res['success']
                        result["table_code"] = code
            except Exception as e:
                logger.error(f"Erreur creation/publication apres validation: {e}")
                result["warning"] = str(e)

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
