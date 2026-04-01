"""
Routes API pour la gestion des agents ETL
Administration des agents, reception des donnees, commandes
"""
import hashlib
import os
import secrets
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Header, Query, Request, Depends, Body
from pydantic import BaseModel, Field

from app.database_unified import (
    execute_central as execute_query, central_cursor as get_db_cursor,
    DWHConnectionManager, get_central_connection as get_connection,
    # Fonctions base CLIENT (agents geres cote client)
    execute_client, write_client, client_cursor,
    execute_central, write_central,
)
from app.config_multitenant import get_central_settings as _get_central_settings, reload_central_settings as _reload_central_settings

# Instance du gestionnaire DWH
dwh_manager = DWHConnectionManager()

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["ETL Agents"])


# ============================================================
# Modeles Pydantic
# ============================================================

class AgentCreate(BaseModel):
    """Creation d'un nouvel agent"""
    dwh_code: str
    name: str
    description: Optional[str] = None
    sync_interval_seconds: int = 300
    heartbeat_interval_seconds: int = 30
    batch_size: int = 10000
    # Connexion Sage
    sage_server: Optional[str] = None
    sage_database: Optional[str] = None
    sage_username: Optional[str] = None
    sage_password: Optional[str] = None
    # Identifiants société (source Sage liée)
    code_societe: Optional[str] = None
    nom_societe: Optional[str] = None


class AgentUpdate(BaseModel):
    """Mise a jour d'un agent"""
    name: Optional[str] = None
    description: Optional[str] = None
    sync_interval_seconds: Optional[int] = None
    heartbeat_interval_seconds: Optional[int] = None
    batch_size: Optional[int] = None
    is_active: Optional[bool] = None
    auto_start: Optional[bool] = None
    # Connexion Sage
    sage_server: Optional[str] = None
    sage_database: Optional[str] = None
    sage_username: Optional[str] = None
    sage_password: Optional[str] = None
    # Identifiants société
    code_societe: Optional[str] = None
    nom_societe: Optional[str] = None


class TableConfigCreate(BaseModel):
    """Configuration d'une table a synchroniser"""
    table_name: str
    source_query: str
    target_table: str
    societe_code: str
    primary_key_columns: List[str]
    sync_type: str = "incremental"
    timestamp_column: str = "cbModification"
    priority: str = "normal"
    is_enabled: bool = True


class TableConfigUpdate(BaseModel):
    """Mise a jour d'une table"""
    source_query: Optional[str] = None
    target_table: Optional[str] = None
    primary_key_columns: Optional[List[str]] = None
    sync_type: Optional[str] = None
    timestamp_column: Optional[str] = None
    priority: Optional[str] = None
    is_enabled: Optional[bool] = None


class HeartbeatRequest(BaseModel):
    """Requete heartbeat d'un agent"""
    status: str = "idle"
    current_task: Optional[str] = None
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    disk_usage: Optional[float] = None
    queue_size: int = 0
    hostname: Optional[str] = None
    ip_address: Optional[str] = None
    os_info: Optional[str] = None
    agent_version: Optional[str] = None
    # Stats de sync (optionnel, mode direct)
    last_sync: Optional[str] = None       # ISO datetime string
    total_syncs: Optional[int] = None
    total_lignes_sync: Optional[int] = None


class PushDataRequest(BaseModel):
    """Requete d'envoi de donnees"""
    table_name: str
    target_table: str
    societe_code: str
    sync_type: str = "incremental"
    primary_key: List[str]
    columns: List[str]
    rows_count: int
    data: List[Dict[str, Any]]
    batch_id: Optional[str] = None
    sync_timestamp_start: Optional[str] = None
    sync_timestamp_end: Optional[str] = None


class CommandCreate(BaseModel):
    """Creation d'une commande"""
    command_type: str  # sync_now, sync_table, pause, resume, update_config
    command_data: Optional[Dict[str, Any]] = None
    priority: int = 5
    expires_in_minutes: Optional[int] = None


class SyncResultRequest(BaseModel):
    """Rapport de resultat de synchronisation"""
    table_name: str
    societe_code: str
    success: bool
    rows_extracted: int = 0
    rows_inserted: int = 0
    rows_updated: int = 0
    rows_failed: int = 0
    duration_seconds: float = 0
    error_message: Optional[str] = None
    sync_timestamp_start: Optional[str] = None
    sync_timestamp_end: Optional[str] = None


# ============================================================
# Fonctions utilitaires
# ============================================================

def _ensure_agent_table_columns():
    """
    Migration automatique : ajoute les colonnes d'heritage a APP_ETL_Agent_Tables
    si elles n'existent pas encore.
    """
    migrations = [
        "IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_ETL_Agent_Tables') AND name='is_inherited') ALTER TABLE APP_ETL_Agent_Tables ADD is_inherited BIT NOT NULL DEFAULT 0",
        "IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_ETL_Agent_Tables') AND name='is_customized') ALTER TABLE APP_ETL_Agent_Tables ADD is_customized BIT NOT NULL DEFAULT 0",
        "IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_ETL_Agent_Tables') AND name='interval_minutes') ALTER TABLE APP_ETL_Agent_Tables ADD interval_minutes INT DEFAULT 5",
        "IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_ETL_Agent_Tables') AND name='delete_detection') ALTER TABLE APP_ETL_Agent_Tables ADD delete_detection BIT DEFAULT 0",
        "IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_ETL_Agent_Tables') AND name='description') ALTER TABLE APP_ETL_Agent_Tables ADD description NVARCHAR(500) NULL",
        # S'assurer que societe_code a un DEFAULT pour les tables heritees du maitre
        "IF NOT EXISTS (SELECT 1 FROM sys.default_constraints WHERE parent_object_id=OBJECT_ID('APP_ETL_Agent_Tables') AND col_name(parent_object_id,parent_column_id)='societe_code') ALTER TABLE APP_ETL_Agent_Tables ADD CONSTRAINT DF_agent_table_societe_code DEFAULT '' FOR societe_code",
    ]
    try:
        with get_db_cursor() as cursor:
            for sql in migrations:
                try:
                    cursor.execute(sql)
                    cursor.commit()
                except Exception as e:
                    logger.debug(f"Migration skipped: {e}")
        logger.info("APP_ETL_Agent_Tables: colonnes d'heritage verifiees")
    except Exception as e:
        logger.warning(f"Migration APP_ETL_Agent_Tables partielle: {e}")


# Lancer la migration au chargement du module
try:
    _ensure_agent_table_columns()
except Exception:
    pass


def hash_api_key(api_key: str) -> str:
    """Hash une cle API avec SHA256"""
    return hashlib.sha256(api_key.encode()).hexdigest()


def generate_api_key() -> str:
    """Genere une nouvelle cle API"""
    return secrets.token_urlsafe(32)


# ============================================================
# Helpers mode DÉMO
# ============================================================

def _get_demo_session(token: str) -> Optional[dict]:
    """Retourne la session démo si le token est valide, sinon None."""
    if not token or len(token) < 20:
        return None
    try:
        rows = execute_central(
            "SELECT * FROM APP_Demo_Sessions WHERE token = ? AND revoked = 0 AND confirmed = 1",
            (token,), use_cache=False
        )
        if rows:
            s = rows[0]
            if s["expires_at"] > datetime.utcnow():
                return s
    except Exception:
        pass
    return None


def _demo_table_prefix(token: str) -> str:
    return "DEMO_" + hashlib.sha256(token.encode()).hexdigest()[:12].upper() + "_"


DEMO_TABLES = [
    {"name": "F_DOCENTETE", "target_table": "F_DOCENTETE", "primary_key_columns": "DO_Piece",
     "sync_type": "full", "timestamp_column": "cbModification", "batch_size": 500},
    {"name": "F_DOCLIGNE",  "target_table": "F_DOCLIGNE",  "primary_key_columns": "DL_Ligne",
     "sync_type": "full", "timestamp_column": "cbModification", "batch_size": 1000},
    {"name": "F_COMPTET",   "target_table": "F_COMPTET",   "primary_key_columns": "CT_Num",
     "sync_type": "full", "timestamp_column": "cbModification", "batch_size": 500},
    {"name": "F_ARTICLE",   "target_table": "F_ARTICLE",   "primary_key_columns": "AR_Ref",
     "sync_type": "full", "timestamp_column": "cbModification", "batch_size": 500},
]


def verify_agent(agent_id: str, api_key: str, dwh_code: str) -> bool:
    """
    Verifie les credentials d'un agent.
    Logique metier : les credentials sont dans la base CLIENT (pas centrale).
    """
    try:
        api_key_hash = hash_api_key(api_key)
        with client_cursor(dwh_code) as cursor:
            cursor.execute(
                "SELECT 1 FROM APP_ETL_Agents WHERE agent_id = ? AND api_key_hash = ? AND is_active = 1",
                (agent_id, api_key_hash)
            )
            return cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"Erreur verification agent: {e}")
        return False


def _get_dwh_for_agent(agent_id: str, x_dwh_code: Optional[str]) -> str:
    """
    Resout le dwh_code pour un agent donne.
    Si x_dwh_code est absent ou 'CENTRAL', interroge APP_ETL_Agents_Monitoring.
    Leve HTTPException 404 si l'agent est inconnu.
    """
    if x_dwh_code and x_dwh_code.upper() != 'CENTRAL':
        return x_dwh_code
    rows = execute_central(
        "SELECT dwh_code FROM APP_ETL_Agents_Monitoring WHERE agent_id = ?",
        (agent_id,), use_cache=False
    )
    if not rows:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' introuvable dans le monitoring central")
    return rows[0]['dwh_code']


async def get_agent_auth(
    x_api_key: str = Header(..., description="Cle API de l'agent"),
    x_agent_id: str = Header(..., description="ID de l'agent"),
    x_dwh_code: str = Header(..., alias="X-DWH-Code", description="Code client")
) -> str:
    """Dependance pour l'authentification des agents (verifie dans base client)"""
    if not verify_agent(x_agent_id, x_api_key, x_dwh_code):
        raise HTTPException(status_code=401, detail="Agent non autorise")
    return x_agent_id


# ============================================================
# Routes Administration (UI)
# ============================================================

@router.get("/admin/etl/agents")
async def list_agents(
    x_dwh_code: Optional[str] = Header(None, alias="X-DWH-Code"),
    status: Optional[str] = Query(None, description="Filtrer par statut"),
    dwh_code: Optional[str] = Query(None, description="Filtrer par DWH (vue centrale uniquement)"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role")
):
    """
    Liste les agents ETL.
    - Si X-DWH-Code absent ou 'CENTRAL' → superadmin : lit APP_ETL_Agents_Monitoring (toutes bases).
    - Si X-DWH-Code present → client : lit APP_ETL_Agents de sa base.
    """
    # Superadmin = pas de code, ou code 'CENTRAL', ou role superadmin explicite
    is_central = not x_dwh_code or x_dwh_code.upper() == 'CENTRAL' or x_user_role == 'superadmin'

    # ── Mode Démo : token = DWH code ──────────────────────────────────────────
    if x_dwh_code and not is_central:
        demo = _get_demo_session(x_dwh_code)
        if demo:
            return {
                "success": True,
                "data": [{
                    "agent_id":              x_dwh_code,
                    "name":                  f"Demo {demo['prenom']} {demo['nom']}",
                    "dwh_code":              x_dwh_code,
                    "dwh_name":              demo.get('societe') or 'Demo',
                    "description":           "Agent démo OptiBoard",
                    "sage_server":           demo.get("sage_server") or "localhost",
                    "sage_database":         demo.get("sage_database") or "",
                    "sage_username":         demo.get("sage_username") or "",
                    "sage_password":         demo.get("sage_password") or "",
                    "dwh_server":            _reload_central_settings()._effective_server or "kasoft.selfip.net",
                    "dwh_database":          _reload_central_settings()._effective_name or "OptiBoard_SaaS",
                    "dwh_username":          _reload_central_settings()._effective_user or "sa",
                    "dwh_password":          _reload_central_settings()._effective_password or "SQL@2019",
                    "status":                "inactive",
                    "health_status":         "Jamais connecte",
                    "last_heartbeat":        None,
                    "last_sync":             demo.get('last_seen'),
                    "last_sync_statut":      None,
                    "consecutive_failures":  0,
                    "total_syncs":           demo.get('tables_synced', 0),
                    "total_lignes_sync":     demo.get('rows_total', 0),
                    "is_active":             True,
                    "tables_count":          len(DEMO_TABLES),
                    "api_key":               x_dwh_code,
                    "sync_interval_seconds": 0,
                    "auto_start":            True,
                }]
            }
    # ─────────────────────────────────────────────────────────────────────────

    try:
        if is_central:
            # ── Vue superadmin : monitoring central (toutes bases clients) ──
            query = """
                SELECT
                    m.agent_id,
                    m.nom,
                    m.dwh_code,
                    d.nom          AS dwh_name,
                    m.hostname,
                    m.ip_address,
                    m.os_info,
                    m.agent_version,
                    m.statut,
                    m.last_heartbeat,
                    m.last_sync,
                    m.last_sync_statut,
                    m.consecutive_failures,
                    m.total_syncs,
                    m.total_lignes_sync,
                    m.date_enregistrement  AS created_at,
                    m.date_modification    AS updated_at,
                    NULL                   AS description,
                    NULL                   AS sage_server,
                    NULL                   AS sage_database,
                    1                      AS is_active,
                    CASE
                        WHEN m.last_heartbeat IS NULL THEN 'Jamais connecte'
                        WHEN DATEDIFF(SECOND, m.last_heartbeat, GETDATE()) > 180 THEN 'Hors ligne'
                        WHEN m.statut = 'erreur' THEN 'Erreur'
                        WHEN m.statut = 'actif'  THEN 'En ligne'
                        ELSE 'Inactif'
                    END AS health_status
                FROM APP_ETL_Agents_Monitoring m
                LEFT JOIN APP_DWH d ON m.dwh_code = d.code
                WHERE 1=1
            """
            params = []
            if status:
                query += " AND m.statut = ?"
                params.append(status)
            if dwh_code:
                query += " AND m.dwh_code = ?"
                params.append(dwh_code)
            query += " ORDER BY d.nom, m.nom"
            agents_monitoring = execute_central(query, tuple(params) if params else (), use_cache=False)

            # ── Enrichir avec les agents des bases clients (non encore connectés) ──
            # Récupérer tous les DWH actifs
            dwh_list = execute_central("SELECT code, nom FROM APP_DWH WHERE actif = 1", use_cache=False)
            # Index des agent_ids déjà dans le monitoring
            monitoring_ids = {a["agent_id"] for a in agents_monitoring if a.get("agent_id")}

            extra_agents = []
            for dwh in dwh_list:
                dwh_code = dwh["code"]
                try:
                    client_agents = execute_client("""
                        SELECT agent_id, nom, statut, is_active, last_heartbeat, last_sync,
                               last_sync_statut, consecutive_failures, total_syncs,
                               total_lignes_sync, hostname, ip_address, agent_version,
                               created_at, updated_at,
                               (SELECT COUNT(*) FROM APP_ETL_Tables_Published WHERE is_enabled = 1) AS tables_count
                        FROM APP_ETL_Agents
                    """, dwh_code=dwh_code, use_cache=False)
                    for ca in client_agents:
                        if ca.get("agent_id") not in monitoring_ids:
                            ca["dwh_code"] = dwh_code
                            ca["dwh_name"] = dwh.get("nom", dwh_code)
                            # Filtre statut
                            if status and ca.get("statut") != status:
                                continue
                            extra_agents.append(ca)
                            monitoring_ids.add(ca.get("agent_id"))
                except Exception:
                    pass  # Base client inaccessible → ignorer

            agents = agents_monitoring + extra_agents

        else:
            # ── Vue client : base client (credentials + config complète) ──
            query = """
                SELECT
                    a.agent_id, a.nom, a.description,
                    a.sage_server, a.sage_database, a.sage_username, a.sage_password,
                    a.sync_interval_secondes, a.heartbeat_interval_secondes, a.batch_size,
                    a.is_active, a.auto_start,
                    a.statut, a.last_heartbeat, a.last_sync, a.last_sync_statut,
                    a.consecutive_failures, a.total_syncs, a.total_lignes_sync,
                    a.hostname, a.ip_address, a.agent_version, a.created_at, a.updated_at,
                    (SELECT COUNT(*) FROM APP_ETL_Tables_Published WHERE is_enabled = 1) AS tables_count,
                    CASE
                        WHEN a.is_active = 0 THEN 'Desactive'
                        WHEN a.last_heartbeat IS NULL THEN 'Jamais connecte'
                        WHEN DATEDIFF(SECOND, a.last_heartbeat, GETDATE()) > a.heartbeat_interval_secondes * 3 THEN 'Hors ligne'
                        WHEN a.statut = 'erreur' THEN 'Erreur'
                        WHEN a.statut = 'actif'  THEN 'En ligne'
                        ELSE 'Inactif'
                    END AS health_status
                FROM APP_ETL_Agents a WHERE 1=1
            """
            params = []
            if status:
                query += " AND statut = ?"
                params.append(status)
            query += " ORDER BY nom"

            with client_cursor(x_dwh_code) as cursor:
                cursor.execute(query, tuple(params) if params else ())
                cols = [c[0] for c in cursor.description]
                agents = [dict(zip(cols, row)) for row in cursor.fetchall()]

            # Recuperer les credentials DWH depuis APP_DWH (base centrale)
            dwh_info_rows = execute_central(
                "SELECT serveur_dwh, base_dwh, user_dwh, password_dwh FROM APP_DWH WHERE code = ?",
                (x_dwh_code,), use_cache=False
            )
            dwh_info = dwh_info_rows[0] if dwh_info_rows else {}
            for a in agents:
                a['dwh_server']   = dwh_info.get('serveur_dwh') or ''
                a['dwh_database'] = dwh_info.get('base_dwh') or ''
                a['dwh_username'] = dwh_info.get('user_dwh') or 'sa'
                a['dwh_password'] = dwh_info.get('password_dwh') or ''

        # Normaliser les noms de champs pour le frontend
        result = []
        for a in agents:
            result.append({
                "agent_id":           a.get("agent_id"),
                "name":               a.get("nom"),
                "dwh_code":           a.get("dwh_code") or x_dwh_code,
                "dwh_name":           a.get("dwh_name") or x_dwh_code,
                "description":        a.get("description"),
                "sage_server":        a.get("sage_server"),
                "sage_database":      a.get("sage_database"),
                # Credentials Sage (base client uniquement)
                "sage_username":      a.get("sage_username"),
                "sage_password":      a.get("sage_password"),
                # Credentials DWH cible (depuis APP_DWH central)
                "dwh_server":         a.get("dwh_server"),
                "dwh_database":       a.get("dwh_database"),
                "dwh_username":       a.get("dwh_username"),
                "dwh_password":       a.get("dwh_password"),
                "status":             _map_statut(a.get("statut"), a.get("is_active")),
                "health_status":      a.get("health_status") or _map_statut(a.get("statut"), a.get("is_active")),
                "last_heartbeat":     a.get("last_heartbeat"),
                "last_sync":          a.get("last_sync"),
                "last_sync_statut":   a.get("last_sync_statut"),
                "consecutive_failures": a.get("consecutive_failures", 0),
                "total_syncs":        a.get("total_syncs", 0),
                "total_lignes_sync":  a.get("total_lignes_sync", 0),
                "tables_count":       a.get("tables_count", 0),
                "hostname":           a.get("hostname"),
                "ip_address":         a.get("ip_address"),
                "agent_version":      a.get("agent_version"),
                "is_active":          a.get("is_active", 1),
                "sync_interval_seconds": a.get("sync_interval_secondes") or a.get("sync_interval_seconds") or 300,
                "batch_size":         a.get("batch_size") or 10000,
                "created_at":         a.get("created_at"),
                "updated_at":         a.get("updated_at"),
            })

        return {"success": True, "data": result, "count": len(result)}

    except Exception as e:
        error_msg = str(e).lower()
        if "invalid object name" in error_msg or "does not exist" in error_msg:
            logger.warning("Tables ETL non initialisees")
            return {"success": True, "data": [], "count": 0, "warning": "Tables ETL non initialisees"}
        logger.error(f"Erreur liste agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _map_statut(statut: Optional[str], is_active) -> str:
    """Convertit le statut SQL vers le format frontend."""
    if is_active == 0:
        return 'inactive'
    if statut == 'actif':
        return 'active'
    if statut == 'erreur':
        return 'error'
    if statut == 'pause':
        return 'paused'
    if statut == 'sync':
        return 'syncing'
    return 'inactive'


@router.post("/admin/etl/agents")
async def create_agent(
    agent: AgentCreate,
    x_dwh_code: str = Header(..., alias="X-DWH-Code")
):
    """
    [CLIENT] Cree un nouvel agent ETL dans la base client.
    Logique metier : le client est proprietaire de ses agents.
    Les credentials Sage ne transitent jamais par la base centrale.
    """
    try:
        agent_id = str(uuid4())
        api_key = generate_api_key()
        api_key_hash = hash_api_key(api_key)
        api_key_prefix = api_key[:7] + "..."  # 10 chars max (VARCHAR(10))

        client_db_saved = False
        try:
            with client_cursor(x_dwh_code) as cursor:
                # Migration auto : ajouter les colonnes si elles n'existent pas
                for col, definition in [
                    ("code_societe", "VARCHAR(100) NULL"),
                    ("nom_societe",  "NVARCHAR(200) NULL"),
                ]:
                    try:
                        cursor.execute(
                            f"IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS "
                            f"WHERE TABLE_NAME='APP_ETL_Agents' AND COLUMN_NAME='{col}') "
                            f"ALTER TABLE APP_ETL_Agents ADD [{col}] {definition}"
                        )
                        cursor.commit()
                    except Exception:
                        pass

                cursor.execute(
                    """
                    INSERT INTO APP_ETL_Agents (
                        agent_id, nom, description,
                        sage_server, sage_database, sage_username, sage_password,
                        code_societe, nom_societe,
                        api_key_hash, api_key_prefix,
                        sync_interval_secondes, heartbeat_interval_secondes, batch_size,
                        statut, is_active, auto_start, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'inactif', 1, 1, GETDATE(), GETDATE())
                    """,
                    (
                        agent_id, agent.name, agent.description,
                        agent.sage_server, agent.sage_database,
                        agent.sage_username, agent.sage_password,
                        agent.code_societe, agent.nom_societe,
                        api_key_hash, api_key_prefix,
                        agent.sync_interval_seconds,
                        agent.heartbeat_interval_seconds,
                        agent.batch_size
                    )
                )
                cursor.commit()
                client_db_saved = True
        except Exception as e_client:
            logger.warning(f"Base client {x_dwh_code} inaccessible — agent enregistré en monitoring central uniquement: {e_client}")

        # Enregistrer dans le monitoring central (sans credentials) — toujours
        try:
            write_central(
                """
                IF NOT EXISTS (SELECT 1 FROM APP_ETL_Agents_Monitoring WHERE agent_id = ?)
                INSERT INTO APP_ETL_Agents_Monitoring
                    (agent_id, dwh_code, nom, statut, date_enregistrement, date_modification)
                VALUES (?, ?, ?, 'inactif', GETDATE(), GETDATE())
                """,
                (agent_id, agent_id, x_dwh_code, agent.name)
            )
        except Exception as e:
            logger.warning(f"Monitoring central non enregistre (non bloquant): {e}")

        # ── Auto-publier le catalogue ETL vers la base client ────────────────
        tables_publies = 0
        try:
            catalogue = execute_central(
                "SELECT * FROM APP_ETL_Tables_Config WHERE actif = 1 ORDER BY code",
                use_cache=False
            )
            if catalogue:
                with client_cursor(x_dwh_code) as cur:
                    for t in catalogue:
                        code               = t.get('code')
                        table_name         = t.get('table_name')        or t.get('nom')        or code
                        target_table       = t.get('target_table')      or table_name
                        source_query       = t.get('source_query')      or ''
                        primary_key_cols   = t.get('primary_key_columns') or '[]'
                        sync_type          = t.get('sync_type')         or 'incremental'
                        timestamp_col      = t.get('timestamp_column')  or 'cbModification'
                        interval_min       = t.get('interval_minutes')  or 5
                        priority           = t.get('priority')          or 'normal'
                        delete_detection   = t.get('delete_detection')  or 0
                        description        = t.get('description')       or ''
                        version_centrale   = t.get('version')           or '1.0'

                        if not code:
                            continue

                        # Sérialiser primary_key_columns si c'est une liste
                        import json as _json
                        if isinstance(primary_key_cols, list):
                            primary_key_cols = _json.dumps(primary_key_cols)

                        # Upsert : ne pas écraser is_enabled si déjà présent (droit du client)
                        cur.execute(
                            "SELECT id FROM APP_ETL_Tables_Published WHERE code = ?",
                            (code,)
                        )
                        exists = cur.fetchone()
                        if not exists:
                            cur.execute(
                                """INSERT INTO APP_ETL_Tables_Published
                                   (code, table_name, target_table, source_query,
                                    primary_key_columns, sync_type, timestamp_column,
                                    interval_minutes, priority, delete_detection,
                                    description, version_centrale, is_enabled, date_publication)
                                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,1,GETDATE())""",
                                (code, table_name, target_table, source_query,
                                 primary_key_cols, sync_type, timestamp_col,
                                 interval_min, priority, int(delete_detection),
                                 description, version_centrale)
                            )
                            tables_publies += 1
                    cur.commit()
                logger.info(f"[create_agent] {tables_publies} tables ETL publiees vers {x_dwh_code}")
        except Exception as e:
            logger.warning(f"Auto-publication tables ETL (non bloquant): {e}")

        return {
            "success": True,
            "message": f"Agent cree dans la base client ({tables_publies} tables ETL initialisees)",
            "agent": {
                "agent_id": agent_id,
                "name": agent.name,
            },
            "data": {
                "agent_id": agent_id,
                "api_key": api_key,
                "nom": agent.name,
                "dwh_code": x_dwh_code,
                "sage_server": agent.sage_server,
                "sage_database": agent.sage_database,
                "tables_etl_publies": tables_publies
            },
            "warning": "Sauvegardez la cle API immediatement, elle ne sera plus affichee!"
        }

    except Exception as e:
        logger.error(f"Erreur creation agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/etl/agents/{agent_id}")
async def get_agent(
    agent_id: str,
    x_dwh_code: Optional[str] = Header(None, alias="X-DWH-Code")
):
    """[CLIENT] Recupere les details d'un agent depuis la base client."""
    try:
        dwh_code = _get_dwh_for_agent(agent_id, x_dwh_code)
        with client_cursor(dwh_code) as cursor:
            cursor.execute(
                """
                SELECT *,
                    CASE
                        WHEN is_active = 0 THEN 'Desactive'
                        WHEN last_heartbeat IS NULL THEN 'Jamais connecte'
                        WHEN DATEDIFF(SECOND, last_heartbeat, GETDATE()) > heartbeat_interval_secondes * 3 THEN 'Hors ligne'
                        WHEN statut = 'erreur' THEN 'Erreur'
                        WHEN statut = 'actif' THEN 'En ligne'
                        ELSE 'Inactif'
                    END AS health_status
                FROM APP_ETL_Agents WHERE agent_id = ?
                """,
                (agent_id,)
            )
            row = cursor.fetchone()
            cols = [c[0] for c in cursor.description] if cursor.description else []

        if not row:
            raise HTTPException(status_code=404, detail="Agent non trouve")

        return {"success": True, "data": dict(zip(cols, row))}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur get agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/admin/etl/agents/{agent_id}")
async def update_agent(
    agent_id: str,
    updates: AgentUpdate,
    x_dwh_code: Optional[str] = Header(None, alias="X-DWH-Code")
):
    """
    [CLIENT] Met a jour un agent dans la base client.
    Logique metier : credentials Sage modifiables uniquement par le client.
    """
    try:
        dwh_code = _get_dwh_for_agent(agent_id, x_dwh_code)
        set_clauses = ["updated_at = GETDATE()"]
        params = []

        if updates.name is not None:
            set_clauses.append("nom = ?"); params.append(updates.name)
        if updates.description is not None:
            set_clauses.append("description = ?"); params.append(updates.description)
        if updates.sync_interval_seconds is not None:
            set_clauses.append("sync_interval_secondes = ?"); params.append(updates.sync_interval_seconds)
        if updates.heartbeat_interval_seconds is not None:
            set_clauses.append("heartbeat_interval_secondes = ?"); params.append(updates.heartbeat_interval_seconds)
        if updates.batch_size is not None:
            set_clauses.append("batch_size = ?"); params.append(updates.batch_size)
        if updates.is_active is not None:
            set_clauses.append("is_active = ?"); params.append(1 if updates.is_active else 0)
        if updates.auto_start is not None:
            set_clauses.append("auto_start = ?"); params.append(1 if updates.auto_start else 0)
        # Credentials Sage — stockes dans base client uniquement
        if updates.sage_server is not None:
            set_clauses.append("sage_server = ?"); params.append(updates.sage_server)
        if updates.sage_database is not None:
            set_clauses.append("sage_database = ?"); params.append(updates.sage_database)
        if updates.sage_username is not None:
            set_clauses.append("sage_username = ?"); params.append(updates.sage_username)
        if updates.sage_password is not None:
            set_clauses.append("sage_password = ?"); params.append(updates.sage_password)

        params.append(agent_id)

        with client_cursor(dwh_code) as cursor:
            cursor.execute(
                f"UPDATE APP_ETL_Agents SET {', '.join(set_clauses)} WHERE agent_id = ?",
                tuple(params)
            )
            cursor.commit()

        return {"success": True, "message": "Agent mis a jour"}

    except Exception as e:
        logger.error(f"Erreur update agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/etl/agents/{agent_id}/sync-published-tables")
async def sync_published_tables(
    agent_id: str,
    x_dwh_code: str = Header(..., alias="X-DWH-Code")
):
    """
    [CLIENT] Re-synchronise le catalogue ETL central vers APP_ETL_Tables_Published.
    Ajoute les nouvelles tables publiees par KASOFT sans ecraser is_enabled existant.
    """
    try:
        catalogue = execute_central(
            "SELECT * FROM APP_ETL_Tables_Config WHERE actif = 1 ORDER BY code",
            use_cache=False
        )
        if not catalogue:
            return {"success": True, "added": 0, "message": "Catalogue ETL vide"}

        import json as _json
        added = 0
        updated = 0

        with client_cursor(x_dwh_code) as cursor:
            for t in catalogue:
                code             = t.get('code')
                table_name       = t.get('table_name')       or t.get('nom')      or code
                target_table     = t.get('target_table')     or table_name
                source_query     = t.get('source_query')     or ''
                primary_key_cols = t.get('primary_key_columns') or '[]'
                sync_type        = t.get('sync_type')        or 'incremental'
                timestamp_col    = t.get('timestamp_column') or 'cbModification'
                interval_min     = t.get('interval_minutes') or 5
                priority         = t.get('priority')         or 'normal'
                delete_detection = t.get('delete_detection') or 0
                description      = t.get('description')      or ''
                version_centrale = t.get('version')          or '1.0'

                if not code:
                    continue
                if isinstance(primary_key_cols, list):
                    primary_key_cols = _json.dumps(primary_key_cols)

                cursor.execute(
                    "SELECT id FROM APP_ETL_Tables_Published WHERE code = ?", (code,)
                )
                exists = cursor.fetchone()

                if not exists:
                    cursor.execute(
                        """INSERT INTO APP_ETL_Tables_Published
                           (code, table_name, target_table, source_query,
                            primary_key_columns, sync_type, timestamp_column,
                            interval_minutes, priority, delete_detection,
                            description, version_centrale, is_enabled, date_publication)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,1,GETDATE())""",
                        (code, table_name, target_table, source_query,
                         primary_key_cols, sync_type, timestamp_col,
                         interval_min, priority, int(delete_detection),
                         description, version_centrale)
                    )
                    added += 1
                else:
                    # Mettre a jour les metadonnees sans toucher is_enabled
                    cursor.execute(
                        """UPDATE APP_ETL_Tables_Published SET
                           table_name=?, target_table=?, source_query=?,
                           primary_key_columns=?, sync_type=?, timestamp_column=?,
                           interval_minutes=?, priority=?, delete_detection=?,
                           description=?, version_centrale=?, date_publication=GETDATE()
                           WHERE code=?""",
                        (table_name, target_table, source_query,
                         primary_key_cols, sync_type, timestamp_col,
                         interval_min, priority, int(delete_detection),
                         description, version_centrale, code)
                    )
                    updated += 1

            cursor.commit()

        return {
            "success": True,
            "added": added,
            "updated": updated,
            "message": f"{added} nouvelle(s) table(s) ajoutee(s), {updated} mise(s) a jour"
        }

    except Exception as e:
        logger.error(f"Erreur sync-published-tables: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/etl/migrate-commands-table")
async def migrate_commands_table():
    """Cree APP_ETL_Agent_Commands dans toutes les bases clients actives (migration one-shot)."""
    CREATE_SQL = """
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Agent_Commands' AND xtype='U')
    CREATE TABLE APP_ETL_Agent_Commands (
        id              INT IDENTITY(1,1) PRIMARY KEY,
        agent_id        VARCHAR(100) NOT NULL,
        command_type    VARCHAR(50) NOT NULL,
        command_data    NVARCHAR(MAX),
        priority        INT DEFAULT 1,
        status          VARCHAR(20) DEFAULT 'pending',
        created_at      DATETIME DEFAULT GETDATE(),
        expires_at      DATETIME,
        executed_at     DATETIME,
        result          NVARCHAR(MAX)
    )
    """
    results = {"ok": [], "failed": []}
    try:
        clients = execute_central(
            """SELECT d.code FROM APP_DWH d
               JOIN APP_ClientDB c ON d.code = c.dwh_code
               WHERE d.actif = 1 AND c.actif = 1""",
            use_cache=False
        )
        for client in clients:
            try:
                with client_cursor(client['code']) as cursor:
                    cursor.execute(CREATE_SQL)
                    cursor.commit()
                results["ok"].append(client['code'])
            except Exception as e:
                results["failed"].append({"code": client['code'], "error": str(e)})
        return {"success": True, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/admin/etl/agents/{agent_id}")
async def delete_agent(
    agent_id: str,
    x_dwh_code: Optional[str] = Header(None, alias="X-DWH-Code")
):
    """[CLIENT] Supprime un agent de la base client + monitoring central."""
    try:
        # 1. Résoudre le dwh_code sans lever d'exception si introuvable
        if x_dwh_code and x_dwh_code.upper() != 'CENTRAL':
            resolved_dwh = x_dwh_code
        else:
            rows = execute_central(
                "SELECT dwh_code FROM APP_ETL_Agents_Monitoring WHERE agent_id = ?",
                (agent_id,), use_cache=False
            )
            resolved_dwh = rows[0]['dwh_code'] if rows else None

        # 2. Supprimer de la base client (best-effort)
        client_deleted = False
        if resolved_dwh:
            try:
                with client_cursor(resolved_dwh) as cursor:
                    cursor.execute("DELETE FROM APP_ETL_Agents WHERE agent_id = ?", (agent_id,))
                    client_deleted = cursor.rowcount > 0
                    cursor.commit()
            except Exception:
                pass

        # 3. Supprimer du monitoring central (toujours)
        try:
            write_central("DELETE FROM APP_ETL_Agents_Monitoring WHERE agent_id = ?", (agent_id,))
        except Exception:
            pass

        if not client_deleted and not resolved_dwh:
            raise HTTPException(status_code=404, detail="Agent non trouve")

        return {"success": True, "message": "Agent supprime"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur delete agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/etl/agents/{agent_id}/clear-error")
async def clear_agent_error(agent_id: str):
    """Efface la derniere erreur d'un agent"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                "UPDATE APP_ETL_Agents SET last_error = NULL, updated_at = GETDATE() WHERE agent_id = ?",
                (agent_id,)
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Agent non trouve")
            cursor.commit()

        return {"success": True, "message": "Erreur effacee"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur clear error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/etl/agents/{agent_id}/regenerate-key")
async def regenerate_api_key(agent_id: str):
    """Regenere la cle API d'un agent"""
    try:
        api_key = generate_api_key()
        api_key_hash = hash_api_key(api_key)

        with get_db_cursor() as cursor:
            cursor.execute(
                "UPDATE APP_ETL_Agents SET api_key_hash = ?, updated_at = GETDATE() WHERE agent_id = ?",
                (api_key_hash, agent_id)
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Agent non trouve")
            cursor.commit()

        return {
            "success": True,
            "message": "Cle API regeneree",
            "data": {"api_key": api_key},
            "warning": "Sauvegardez la nouvelle cle API immediatement!"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur regeneration cle: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Routes Configuration Tables
# ============================================================

@router.get("/admin/etl/agents/{agent_id}/tables")
async def list_agent_tables(agent_id: str):
    """Liste les tables configurees pour un agent"""
    try:
        tables = execute_query(
            """
            SELECT
                id, agent_id, table_name, source_query, target_table,
                societe_code, primary_key_columns, sync_type, timestamp_column,
                is_enabled, priority, last_sync, last_sync_status,
                last_sync_rows, last_error, created_at
            FROM APP_ETL_Agent_Tables
            WHERE agent_id = ?
            ORDER BY priority, table_name
            """,
            (agent_id,),
            use_cache=False
        )

        return {"success": True, "data": tables, "count": len(tables)}

    except Exception as e:
        logger.error(f"Erreur liste tables agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/etl/agents/{agent_id}/tables")
async def add_agent_table(agent_id: str, table: TableConfigCreate):
    """
    Ajoute une table propre a un agent (is_inherited=0).
    Ces tables ne sont jamais affectees par les syncs depuis le maitre.
    """
    try:
        pk_json = json.dumps(table.primary_key_columns)

        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO APP_ETL_Agent_Tables (
                    agent_id, table_name, source_query, target_table,
                    societe_code, primary_key_columns, sync_type,
                    timestamp_column, priority, is_enabled,
                    is_inherited, is_customized, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, GETDATE())
                """,
                (
                    agent_id, table.table_name, table.source_query,
                    table.target_table, table.societe_code, pk_json,
                    table.sync_type, table.timestamp_column,
                    table.priority, 1 if table.is_enabled else 0
                )
            )
            cursor.commit()

        return {"success": True, "message": "Table propre ajoutee (non affectee par les syncs maitre)"}

    except Exception as e:
        logger.error(f"Erreur ajout table: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/admin/etl/agents/{agent_id}/tables/{table_id}")
async def update_agent_table(agent_id: str, table_id: int, updates: TableConfigUpdate):
    """Met a jour une table"""
    try:
        set_clauses = ["updated_at = GETDATE()"]
        params = []

        if updates.source_query is not None:
            set_clauses.append("source_query = ?")
            params.append(updates.source_query)
        if updates.target_table is not None:
            set_clauses.append("target_table = ?")
            params.append(updates.target_table)
        if updates.primary_key_columns is not None:
            set_clauses.append("primary_key_columns = ?")
            params.append(json.dumps(updates.primary_key_columns))
        if updates.sync_type is not None:
            set_clauses.append("sync_type = ?")
            params.append(updates.sync_type)
        if updates.timestamp_column is not None:
            set_clauses.append("timestamp_column = ?")
            params.append(updates.timestamp_column)
        if updates.priority is not None:
            set_clauses.append("priority = ?")
            params.append(updates.priority)
        if updates.is_enabled is not None:
            set_clauses.append("is_enabled = ?")
            params.append(1 if updates.is_enabled else 0)

        params.extend([table_id, agent_id])

        with get_db_cursor() as cursor:
            # Auto-marquer is_customized=1 si la table est heritee et qu'on la modifie
            cursor.execute(
                f"""
                UPDATE APP_ETL_Agent_Tables SET {', '.join(set_clauses)},
                    is_customized = CASE WHEN ISNULL(is_inherited,0)=1 THEN 1 ELSE ISNULL(is_customized,0) END
                WHERE id = ? AND agent_id = ?
                """,
                tuple(params)
            )
            cursor.commit()

        return {"success": True, "message": "Table mise a jour"}

    except Exception as e:
        logger.error(f"Erreur update table: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/admin/etl/agents/{agent_id}/tables/{table_id}")
async def delete_agent_table(agent_id: str, table_id: int):
    """Supprime une table"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                "DELETE FROM APP_ETL_Agent_Tables WHERE id = ? AND agent_id = ?",
                (table_id, agent_id)
            )
            cursor.commit()

        return {"success": True, "message": "Table supprimee"}

    except Exception as e:
        logger.error(f"Erreur delete table: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/admin/etl/agents/{agent_id}/tables")
async def delete_all_agent_tables(agent_id: str):
    """Supprime toutes les tables d'un agent"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                "DELETE FROM APP_ETL_Agent_Tables WHERE agent_id = ?",
                (agent_id,)
            )
            deleted = cursor.rowcount
            cursor.commit()

        return {
            "success": True,
            "message": f"{deleted} tables supprimees pour l'agent {agent_id}",
            "deleted": deleted
        }

    except Exception as e:
        logger.error(f"Erreur suppression tables agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/etl/agents/{agent_id}/sync-tables")
async def sync_agent_tables_with_config(agent_id: str):
    """
    Synchronise INTELLIGEMMENT les tables de l'agent avec le catalogue maitre ETL_Tables_Config.

    Regles d'heritage :
    - Table absente de l'agent  → INSERT  avec is_inherited=1, is_customized=0
    - Table heritee non modifiee (is_inherited=1, is_customized=0) → UPDATE depuis maitre
    - Table heritee modifiee    (is_inherited=1, is_customized=1) → SKIP (protegee)
    - Table propre              (is_inherited=0)                  → SKIP (jamais touchee)
    - Table heritee supprimee du maitre (is_inherited=1, is_customized=0) → DELETE
    """
    try:
        from etl.config.table_config import get_enabled_tables

        # 1. Recuperer les tables du catalogue maitre (activees)
        master_tables = get_enabled_tables()
        master_names = {t.get('name') for t in master_tables if t.get('name')}

        # 2. Recuperer les tables existantes de l'agent (avec colonnes heritage)
        existing_rows = execute_query(
            """
            SELECT id, table_name,
                   ISNULL(is_inherited, 0) as is_inherited,
                   ISNULL(is_customized, 0) as is_customized
            FROM APP_ETL_Agent_Tables
            WHERE agent_id = ?
            """,
            (agent_id,),
            use_cache=False
        )
        existing_map = {r['table_name']: r for r in existing_rows}

        added = updated = skipped_customized = custom_preserved = removed = 0

        # 3. Pour chaque table du maitre
        for table in master_tables:
            name = table.get('name')
            if not name:
                continue

            source = table.get('source', {})
            target = table.get('target', {})
            source_query = source.get('query', '') if isinstance(source, dict) else ''
            source_table = source.get('table', name) if isinstance(source, dict) else name
            target_table = target.get('table', '') if isinstance(target, dict) else ''
            pk = target.get('primary_key', []) if isinstance(target, dict) else []
            pk_str = json.dumps(pk) if isinstance(pk, list) else str(pk or '[]')
            sync_type = table.get('sync_type', 'incremental')
            ts_col = table.get('timestamp_column') or ''
            priority = table.get('priority', 'normal')
            interval = table.get('interval_minutes', 5)
            del_detect = 1 if table.get('delete_detection', False) else 0
            description = table.get('description', '') or ''

            existing = existing_map.get(name)

            try:
                if existing is None:
                    # Nouvelle table — INSERT avec is_inherited=1
                    with get_db_cursor() as cursor:
                        cursor.execute(
                            """
                            INSERT INTO APP_ETL_Agent_Tables (
                                agent_id, table_name, source_query, target_table,
                                societe_code, primary_key_columns, sync_type, timestamp_column,
                                priority, is_enabled, interval_minutes, delete_detection,
                                description, is_inherited, is_customized, created_at
                            ) VALUES (?, ?, ?, ?, '', ?, ?, ?, ?, 1, ?, ?, ?, 1, 0, GETDATE())
                            """,
                            (agent_id, name, source_query, target_table,
                             pk_str, sync_type, ts_col, priority,
                             interval, del_detect, description)
                        )
                        cursor.commit()
                    added += 1

                elif existing['is_customized'] == 1:
                    # Protegee par l'admin — ne pas toucher
                    skipped_customized += 1

                elif existing['is_inherited'] == 1:
                    # Heritee non modifiee — UPDATE depuis maitre
                    with get_db_cursor() as cursor:
                        cursor.execute(
                            """
                            UPDATE APP_ETL_Agent_Tables SET
                                source_query = ?, target_table = ?,
                                primary_key_columns = ?, sync_type = ?,
                                timestamp_column = ?, priority = ?,
                                interval_minutes = ?, delete_detection = ?,
                                description = ?, updated_at = GETDATE()
                            WHERE id = ? AND agent_id = ?
                            """,
                            (source_query, target_table, pk_str, sync_type,
                             ts_col, priority, interval, del_detect,
                             description, existing['id'], agent_id)
                        )
                        cursor.commit()
                    updated += 1

                else:
                    # is_inherited=0 → table propre, on ne touche pas
                    custom_preserved += 1

            except Exception as e:
                logger.warning(f"Erreur sync table {name}: {e}")

        # 4. Supprimer les tables heritees non personnalisees qui ont disparu du maitre
        for name, row in existing_map.items():
            if name not in master_names and row['is_inherited'] == 1 and row['is_customized'] == 0:
                try:
                    with get_db_cursor() as cursor:
                        cursor.execute(
                            "DELETE FROM APP_ETL_Agent_Tables WHERE id = ? AND agent_id = ?",
                            (row['id'], agent_id)
                        )
                        cursor.commit()
                    removed += 1
                except Exception as e:
                    logger.warning(f"Erreur suppression table obsolete {name}: {e}")

        msg = (f"Sync intelligent: {added} ajoutees, {updated} mises a jour, "
               f"{skipped_customized} ignorees (personnalisees), "
               f"{custom_preserved} propres preservees, {removed} obsoletes supprimees")
        logger.info(msg)

        return {
            "success": True,
            "message": msg,
            "added": added,
            "updated": updated,
            "skipped_customized": skipped_customized,
            "custom_preserved": custom_preserved,
            "removed": removed
        }

    except Exception as e:
        logger.error(f"Erreur sync tables agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/etl/agents/{agent_id}/tables-status")
async def get_agent_tables_status(agent_id: str):
    """
    Retourne le statut d'heritage de chaque table pour cet agent.
    Compare le catalogue maitre (ETL_Tables_Config) avec les tables de l'agent.
    Status possibles : inherited | customized | custom | not_deployed
    """
    try:
        from etl.config.table_config import get_tables as get_master_tables

        master_tables = get_master_tables()
        master_map = {t['name']: t for t in master_tables if t.get('name')}

        agent_rows = execute_query(
            """
            SELECT id, table_name, source_query, target_table, societe_code,
                   primary_key_columns, sync_type, timestamp_column,
                   priority, is_enabled, last_sync, last_sync_status, last_sync_rows,
                   ISNULL(interval_minutes, 5) as interval_minutes,
                   ISNULL(delete_detection, 0) as delete_detection,
                   ISNULL(is_inherited, 0) as is_inherited,
                   ISNULL(is_customized, 0) as is_customized,
                   description, created_at, updated_at
            FROM APP_ETL_Agent_Tables
            WHERE agent_id = ?
            ORDER BY table_name
            """,
            (agent_id,),
            use_cache=False
        )
        agent_map = {r['table_name']: r for r in agent_rows}

        result = []

        # Tables de l'agent
        for row in agent_rows:
            name = row['table_name']
            is_inherited = row.get('is_inherited', 0)
            is_customized = row.get('is_customized', 0)

            if is_inherited and is_customized:
                status = 'customized'
            elif is_inherited:
                status = 'inherited'
            else:
                status = 'custom'

            result.append({**row, 'status': status})

        # Tables du maitre non deployees sur cet agent
        for name, master in master_map.items():
            if name not in agent_map:
                result.append({
                    'id': None,
                    'table_name': name,
                    'status': 'not_deployed',
                    'sync_type': master.get('sync_type', 'incremental'),
                    'priority': master.get('priority', 'normal'),
                    'is_enabled': master.get('enabled', True),
                    'is_inherited': 0,
                    'is_customized': 0,
                    'description': master.get('description', ''),
                    'source_query': (master.get('source') or {}).get('query', ''),
                    'target_table': (master.get('target') or {}).get('table', ''),
                })

        stats = {
            'inherited': sum(1 for r in result if r['status'] == 'inherited'),
            'customized': sum(1 for r in result if r['status'] == 'customized'),
            'custom': sum(1 for r in result if r['status'] == 'custom'),
            'not_deployed': sum(1 for r in result if r['status'] == 'not_deployed'),
        }

        return {
            "success": True,
            "agent_id": agent_id,
            "stats": stats,
            "tables": result,
            "count": len(result)
        }

    except Exception as e:
        logger.error(f"Erreur tables-status agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/etl/agents/{agent_id}/tables/{table_id}/mark-customized")
async def mark_table_as_customized(agent_id: str, table_id: int):
    """
    Marque une table heritee comme personnalisee (is_customized=1).
    Elle sera ignoree lors des prochains syncs depuis le maitre.
    """
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                UPDATE APP_ETL_Agent_Tables
                SET is_customized = 1, updated_at = GETDATE()
                WHERE id = ? AND agent_id = ? AND ISNULL(is_inherited, 0) = 1
                """,
                (table_id, agent_id)
            )
            affected = cursor.rowcount
            cursor.commit()

        if affected == 0:
            raise HTTPException(status_code=404, detail="Table non trouvee ou non heritee")

        return {"success": True, "message": "Table marquee comme personnalisee — protegee des syncs futurs"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur mark-customized: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/etl/agents/{agent_id}/tables/{table_id}/reset-to-master")
async def reset_table_to_master(agent_id: str, table_id: int):
    """
    Reinitialise une table personnalisee vers les valeurs du maitre.
    Remet is_customized=0 → elle sera a nouveau mise a jour lors des syncs.
    """
    try:
        from etl.config.table_config import get_table_by_name

        # Recuperer le nom de la table
        row = execute_query(
            "SELECT table_name FROM APP_ETL_Agent_Tables WHERE id = ? AND agent_id = ?",
            (table_id, agent_id),
            use_cache=False
        )
        if not row:
            raise HTTPException(status_code=404, detail="Table non trouvee")

        table_name = row[0]['table_name']
        master = get_table_by_name(table_name)
        if not master:
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' absente du catalogue maitre")

        source = master.get('source') or {}
        target = master.get('target') or {}
        source_query = source.get('query', '') if isinstance(source, dict) else ''
        target_table = target.get('table', '') if isinstance(target, dict) else ''
        pk = target.get('primary_key', []) if isinstance(target, dict) else []
        pk_str = json.dumps(pk) if isinstance(pk, list) else str(pk or '[]')

        with get_db_cursor() as cursor:
            cursor.execute(
                """
                UPDATE APP_ETL_Agent_Tables SET
                    source_query = ?, target_table = ?,
                    primary_key_columns = ?, sync_type = ?,
                    timestamp_column = ?, priority = ?,
                    interval_minutes = ?, delete_detection = ?,
                    description = ?,
                    is_inherited = 1, is_customized = 0,
                    updated_at = GETDATE()
                WHERE id = ? AND agent_id = ?
                """,
                (source_query, target_table, pk_str,
                 master.get('sync_type', 'incremental'),
                 master.get('timestamp_column') or '',
                 master.get('priority', 'normal'),
                 master.get('interval_minutes', 5),
                 1 if master.get('delete_detection') else 0,
                 master.get('description', '') or '',
                 table_id, agent_id)
            )
            cursor.commit()

        return {"success": True, "message": f"Table '{table_name}' reinitialisee depuis le maitre"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur reset-to-master: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/etl/agents/{agent_id}/deploy-master-table")
async def deploy_master_table_to_agent(agent_id: str, table_name: str = Body(..., embed=True)):
    """
    Deploie une table du catalogue maitre vers cet agent (is_inherited=1).
    Utilise quand la table est presente dans le maitre mais pas encore deployee.
    """
    try:
        from etl.config.table_config import get_table_by_name

        master = get_table_by_name(table_name)
        if not master:
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' absente du catalogue maitre")

        source = master.get('source') or {}
        target = master.get('target') or {}
        source_query = source.get('query', '') if isinstance(source, dict) else ''
        target_table = target.get('table', '') if isinstance(target, dict) else ''
        pk = target.get('primary_key', []) if isinstance(target, dict) else []
        pk_str = json.dumps(pk) if isinstance(pk, list) else str(pk or '[]')

        with get_db_cursor() as cursor:
            cursor.execute(
                """
                IF NOT EXISTS (
                    SELECT 1 FROM APP_ETL_Agent_Tables WHERE agent_id = ? AND table_name = ?
                )
                INSERT INTO APP_ETL_Agent_Tables (
                    agent_id, table_name, source_query, target_table,
                    societe_code, primary_key_columns, sync_type, timestamp_column,
                    priority, is_enabled, interval_minutes, delete_detection,
                    description, is_inherited, is_customized, created_at
                ) VALUES (?, ?, ?, ?, '', ?, ?, ?, ?, 1, ?, ?, ?, 1, 0, GETDATE())
                """,
                (agent_id, table_name,
                 agent_id, table_name, source_query, target_table,
                 pk_str, master.get('sync_type', 'incremental'),
                 master.get('timestamp_column') or '',
                 master.get('priority', 'normal'),
                 master.get('interval_minutes', 5),
                 1 if master.get('delete_detection') else 0,
                 master.get('description', '') or '')
            )
            cursor.commit()

        return {"success": True, "message": f"Table '{table_name}' deployee depuis le maitre"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur deploy-master-table: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/etl/agents/{agent_id}/import-tables")
async def import_tables_from_yaml(agent_id: str, societe_code: str = Query(...)):
    """Importe les tables depuis la configuration YAML"""
    try:
        from etl.config.table_config import get_enabled_tables

        tables = get_enabled_tables()

        added = 0
        for table in tables:
            pk_columns = table.get('target', {}).get('primary_key', [])
            pk_json = json.dumps(pk_columns)

            try:
                with get_db_cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO APP_ETL_Agent_Tables (
                            agent_id, table_name, source_query, target_table,
                            societe_code, primary_key_columns, sync_type,
                            timestamp_column, priority, is_enabled, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, GETDATE())
                        """,
                        (
                            agent_id,
                            table.get('name'),
                            table.get('source', {}).get('query', ''),
                            table.get('target', {}).get('table', ''),
                            societe_code,
                            pk_json,
                            table.get('sync_type', 'incremental'),
                            table.get('timestamp_column', 'cbModification'),
                            table.get('priority', 'normal')
                        )
                    )
                    cursor.commit()
                    added += 1
            except Exception as e:
                logger.warning(f"Table {table.get('name')} deja existante ou erreur: {e}")

        return {"success": True, "message": f"{added} tables importees"}

    except Exception as e:
        logger.error(f"Erreur import tables: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Routes Commandes
# ============================================================

@router.get("/admin/etl/agents/{agent_id}/commands")
async def list_agent_commands(
    agent_id: str,
    status: Optional[str] = Query(None),
    limit: int = Query(50)
):
    """Liste les commandes d'un agent (lit depuis la base client)"""
    try:
        # Trouver le dwh_code de l'agent
        rows = execute_central(
            "SELECT dwh_code FROM APP_ETL_Agents_Monitoring WHERE agent_id = ?",
            (agent_id,), use_cache=False
        )
        if not rows:
            return {"success": True, "data": []}

        dwh_code = rows[0]['dwh_code']
        query = """
            SELECT id, agent_id, command_type, command_data, priority,
                   status, created_at, expires_at, executed_at, result
            FROM APP_ETL_Agent_Commands
            WHERE agent_id = ?
        """
        params = [agent_id]

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_at DESC"

        commands = execute_client(query, tuple(params), dwh_code=dwh_code, use_cache=False)[:limit]

        return {"success": True, "data": commands}

    except Exception as e:
        logger.error(f"Erreur liste commandes: {e}")
        if "invalid object name" in str(e).lower():
            return {"success": True, "data": [], "warning": "Table APP_ETL_Agent_Commands non initialisee"}
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/etl/agents/{agent_id}/commands")
async def create_command(agent_id: str, command: CommandCreate):
    """Cree une commande pour un agent (ecrit dans la base client de l'agent)"""
    try:
        # Trouver le dwh_code de l'agent via la table de monitoring centrale
        rows = execute_central(
            "SELECT dwh_code FROM APP_ETL_Agents_Monitoring WHERE agent_id = ?",
            (agent_id,), use_cache=False
        )
        if not rows:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' introuvable dans le monitoring central")

        dwh_code = rows[0]['dwh_code']

        expires_at = None
        if command.expires_in_minutes:
            expires_at = datetime.now()

        with client_cursor(dwh_code) as cursor:
            cursor.execute(
                """
                INSERT INTO APP_ETL_Agent_Commands (
                    agent_id, command_type, command_data, priority,
                    status, created_at, expires_at
                ) VALUES (?, ?, ?, ?, 'pending', GETDATE(), ?)
                """,
                (
                    agent_id,
                    command.command_type,
                    json.dumps(command.command_data) if command.command_data else None,
                    command.priority,
                    expires_at
                )
            )
            cursor.commit()

        return {"success": True, "message": "Commande creee"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur creation commande: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Routes Logs et Monitoring
# ============================================================

@router.get("/admin/etl/agents/{agent_id}/logs")
async def list_agent_logs(
    agent_id: str,
    table_name: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100)
):
    """Liste les logs de synchronisation d'un agent"""
    try:
        query = """
            SELECT id, agent_id, table_name, societe_code,
                   started_at, completed_at, duration_seconds, status,
                   rows_extracted, rows_inserted, rows_updated, rows_failed,
                   error_message
            FROM APP_ETL_Agent_Sync_Log
            WHERE agent_id = ?
        """
        params = [agent_id]

        if table_name:
            query += " AND table_name = ?"
            params.append(table_name)

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY started_at DESC"

        logs = execute_query(query, tuple(params), use_cache=False)[:limit]

        return {"success": True, "data": logs}

    except Exception as e:
        logger.error(f"Erreur liste logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/etl/agents/{agent_id}/heartbeats")
async def list_agent_heartbeats(agent_id: str, limit: int = Query(50)):
    """Liste les heartbeats d'un agent"""
    try:
        heartbeats = execute_query(
            """
            SELECT id, agent_id, heartbeat_time, status, current_task,
                   cpu_usage, memory_usage, disk_usage, queue_size
            FROM APP_ETL_Agent_Heartbeats
            WHERE agent_id = ?
            ORDER BY heartbeat_time DESC
            """,
            (agent_id,),
            use_cache=False
        )[:limit]

        return {"success": True, "data": heartbeats}

    except Exception as e:
        logger.error(f"Erreur liste heartbeats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/etl/stats")
async def get_etl_stats():
    """Statistiques globales ETL"""
    try:
        # Agents
        agents_stats = execute_query(
            """
            SELECT
                COUNT(*) AS total_agents,
                SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) AS active_agents,
                SUM(CASE WHEN status = 'syncing' THEN 1 ELSE 0 END) AS syncing_agents,
                SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) AS error_agents,
                SUM(CASE WHEN DATEDIFF(SECOND, last_heartbeat, GETDATE()) <= heartbeat_interval_seconds * 3 THEN 1 ELSE 0 END) AS online_agents
            FROM APP_ETL_Agents
            """,
            use_cache=False
        )[0]

        # Syncs aujourd'hui
        sync_stats = execute_query(
            """
            SELECT
                COUNT(*) AS total_syncs,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS success_syncs,
                SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) AS error_syncs,
                SUM(rows_extracted) AS total_rows_extracted,
                SUM(rows_inserted + rows_updated) AS total_rows_synced,
                AVG(duration_seconds) AS avg_duration
            FROM APP_ETL_Agent_Sync_Log
            WHERE started_at >= CAST(GETDATE() AS DATE)
            """,
            use_cache=False
        )[0]

        return {
            "success": True,
            "data": {
                "agents": agents_stats,
                "syncs_today": sync_stats
            }
        }

    except Exception as e:
        logger.error(f"Erreur stats ETL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/etl/sync-dashboard")
async def get_sync_dashboard():
    """Dashboard de monitoring sync - stats pour tous les DWH"""
    try:
        # 1. Liste des DWH actifs
        dwh_list = execute_query(
            "SELECT code, nom, serveur_dwh, base_dwh FROM APP_DWH WHERE actif = 1 ORDER BY nom",
            use_cache=False
        )

        # 2. Stats agents par DWH (base centrale)
        try:
            agent_stats = execute_query(
                """
                SELECT
                    a.dwh_code,
                    COUNT(DISTINCT a.agent_id) AS agent_count,
                    SUM(ISNULL(a.total_syncs, 0)) AS total_syncs,
                    SUM(ISNULL(a.total_rows_synced, 0)) AS total_rows_synced
                FROM APP_ETL_Agents a
                WHERE a.is_active = 1
                GROUP BY a.dwh_code
                """,
                use_cache=False
            )
            agent_map = {s['dwh_code']: s for s in agent_stats}
        except Exception:
            agent_map = {}

        # 3. Stats syncs du jour (base centrale)
        try:
            today_stats = execute_query(
                """
                SELECT
                    a.dwh_code,
                    SUM(ISNULL(l.rows_inserted, 0)) AS rows_inserted_today,
                    SUM(ISNULL(l.rows_updated, 0)) AS rows_updated_today,
                    SUM(ISNULL(l.rows_failed, 0)) AS rows_failed_today,
                    COUNT(*) AS syncs_today
                FROM APP_ETL_Agent_Sync_Log l
                JOIN APP_ETL_Agents a ON l.agent_id = a.agent_id
                WHERE l.started_at >= CAST(GETDATE() AS DATE)
                GROUP BY a.dwh_code
                """,
                use_cache=False
            )
            today_map = {s['dwh_code']: s for s in today_stats}
        except Exception:
            today_map = {}

        # 4. Per-DWH: taille DB, lignes, SyncControl
        dashboard_items = []
        totals = {'total_db_size_mb': 0, 'total_rows': 0, 'total_inserted': 0, 'total_updated': 0}

        for dwh in dwh_list:
            code = dwh['code']
            item = {
                'dwh_code': code,
                'dwh_name': dwh['nom'],
                'server': dwh['serveur_dwh'],
                'database': dwh['base_dwh'],
                'db_size_mb': None,
                'total_rows': 0,
                'total_inserted': 0,
                'total_updated': 0,
                'table_rows': [],
                'sync_control': [],
                'agent_stats': agent_map.get(code, {}),
                'today_stats': today_map.get(code, {}),
                'error': None
            }

            try:
                # Taille DB (MB)
                size_res = dwh_manager.execute_dwh_query(
                    code,
                    "SELECT SUM(size) * 8.0 / 1024 AS size_mb FROM sys.database_files",
                    use_cache=False
                )
                if size_res:
                    item['db_size_mb'] = round(size_res[0].get('size_mb') or 0, 2)

                # Lignes par table
                rows_res = dwh_manager.execute_dwh_query(
                    code,
                    """
                    SELECT t.name AS table_name, SUM(p.rows) AS row_count
                    FROM sys.tables t
                    JOIN sys.partitions p ON t.object_id = p.object_id
                    WHERE p.index_id IN (0, 1)
                    GROUP BY t.name
                    ORDER BY SUM(p.rows) DESC
                    """,
                    use_cache=False
                )
                item['table_rows'] = rows_res or []
                item['total_rows'] = sum(r.get('row_count', 0) or 0 for r in rows_res) if rows_res else 0

                # SyncControl totaux
                try:
                    sc_res = dwh_manager.execute_dwh_query(
                        code,
                        """
                        SELECT TableName, LastSyncDate, LastStatus,
                               ISNULL(TotalInserted, 0) AS TotalInserted,
                               ISNULL(TotalUpdated, 0) AS TotalUpdated,
                               ISNULL(TotalDeleted, 0) AS TotalDeleted
                        FROM SyncControl ORDER BY TableName
                        """,
                        use_cache=False
                    )
                    item['sync_control'] = sc_res or []
                    item['total_inserted'] = sum(r.get('TotalInserted', 0) or 0 for r in sc_res) if sc_res else 0
                    item['total_updated'] = sum(r.get('TotalUpdated', 0) or 0 for r in sc_res) if sc_res else 0
                except Exception:
                    # SyncControl n'existe pas encore dans ce DWH
                    item['sync_control'] = []

            except Exception as e:
                item['error'] = str(e)
                logger.warning(f"Erreur monitoring DWH {code}: {e}")

            dashboard_items.append(item)
            totals['total_db_size_mb'] += item.get('db_size_mb') or 0
            totals['total_rows'] += item.get('total_rows') or 0
            totals['total_inserted'] += item.get('total_inserted') or 0
            totals['total_updated'] += item.get('total_updated') or 0

        return {
            "success": True,
            "data": dashboard_items,
            "totals": totals,
            "count": len(dashboard_items)
        }

    except Exception as e:
        logger.error(f"Erreur sync dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Routes Agent (appelees par l'agent lui-meme)
# ============================================================

@router.post("/agents/{agent_id}/register")
async def agent_register(
    agent_id: str,
    request: Request,
    x_dwh_code: str = Header(..., alias="X-DWH-Code")
):
    """
    Enregistrement d'un agent au demarrage.
    Dual-write : base client (statut complet) + central monitoring (metriques).
    """
    try:
        data = await request.json()

        # 1. Mise a jour base CLIENT
        with client_cursor(x_dwh_code) as cursor:
            cursor.execute(
                """
                UPDATE APP_ETL_Agents SET
                    hostname = ?,
                    ip_address = ?,
                    os_info = ?,
                    agent_version = ?,
                    statut = 'actif',
                    last_heartbeat = GETDATE(),
                    updated_at = GETDATE()
                WHERE agent_id = ?
                """,
                (data.get('hostname'), data.get('ip_address'),
                 data.get('os_info'), data.get('agent_version'), agent_id)
            )
            cursor.commit()

        # 2. Update monitoring central uniquement si l'agent y est déjà enregistré (créé depuis master)
        # Ne jamais auto-insérer depuis un heartbeat → seul le master admin peut créer dans central
        try:
            write_central(
                """
                UPDATE APP_ETL_Agents_Monitoring SET
                    hostname = ?, ip_address = ?, os_info = ?,
                    agent_version = ?, statut = 'actif',
                    last_heartbeat = GETDATE(), date_modification = GETDATE()
                WHERE agent_id = ?
                """,
                (data.get('hostname'), data.get('ip_address'), data.get('os_info'),
                 data.get('agent_version'), agent_id)
            )
        except Exception as e:
            logger.debug(f"Update monitoring central non bloquant: {e}")

        return {"success": True, "message": "Agent enregistre"}

    except Exception as e:
        logger.error(f"Erreur register agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/{agent_id}/heartbeat")
async def agent_heartbeat(
    agent_id: str,
    hb: HeartbeatRequest,
    x_dwh_code: Optional[str] = Header(None, alias="X-DWH-Code")
):
    """
    Heartbeat d'un agent.
    Logique metier (dual-write) :
      1. Met a jour APP_ETL_Agents dans la BASE CLIENT (config + statut complet)
      2. Met a jour APP_ETL_Agents_Monitoring dans la BASE CENTRALE (metriques uniquement)
    Les clients autonomes n'alimentent PAS le central (pas de connexion internet).
    X-DWH-Code optionnel : si absent, resolu depuis APP_ETL_Agents_Monitoring.
    """
    # ── Mode Démo ─────────────────────────────────────────────────────────────
    demo = _get_demo_session(agent_id)
    if demo:
        try:
            prefix = _demo_table_prefix(agent_id)
            # Compter les tables DEMO_ qui existent et ont des lignes
            tables_ok = 0
            rows_total = 0
            for t in DEMO_TABLES:
                tname = f"{prefix}{t['target_table']}"
                try:
                    exists = execute_central(
                        "SELECT COUNT(*) AS n FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = ?",
                        (tname,), use_cache=False
                    )
                    if exists and exists[0]["n"] > 0:
                        cnt = execute_central(
                            f"SELECT COUNT(*) AS n FROM [{tname}]",
                            use_cache=False
                        )
                        if cnt and cnt[0]["n"] > 0:
                            tables_ok += 1
                            rows_total += cnt[0]["n"]
                except Exception:
                    pass

            completed = 1 if tables_ok >= len(DEMO_TABLES) else 0
            write_central(
                """UPDATE APP_Demo_Sessions SET
                     last_seen      = GETDATE(),
                     sync_started   = 1,
                     rows_total     = ?,
                     tables_synced  = ?,
                     sync_completed = CASE WHEN ? = 1 THEN 1 ELSE sync_completed END
                   WHERE token = ?""",
                (rows_total, tables_ok, completed, agent_id)
            )
            logger.info(f"Demo heartbeat [{agent_id[:8]}]: {tables_ok}/{len(DEMO_TABLES)} tables, {rows_total} lignes, completed={completed}")
        except Exception as e:
            logger.warning(f"demo heartbeat update error: {e}")
        return {"success": True, "commands": [], "demo": True}
    # ─────────────────────────────────────────────────────────────────────────

    dwh_code = _get_dwh_for_agent(agent_id, x_dwh_code)
    # Mapper statut anglais -> francais pour coherence DB
    _STATUS_MAP = {
        'active': 'actif', 'syncing': 'actif', 'idle': 'actif',
        'paused': 'inactif', 'offline': 'inactif',
        'error': 'erreur', 'erreur': 'erreur', 'actif': 'actif', 'inactif': 'inactif',
    }
    statut_fr = _STATUS_MAP.get(hb.status, 'actif')

    try:
        # 1. Mise a jour BASE CLIENT (statut complet) — non bloquant si DB inaccessible
        try:
            with client_cursor(dwh_code) as cursor:
                cursor.execute(
                    """
                    UPDATE APP_ETL_Agents SET
                        last_heartbeat = GETDATE(),
                        statut = ?,
                        hostname = COALESCE(?, hostname),
                        ip_address = COALESCE(?, ip_address),
                        os_info = COALESCE(?, os_info),
                        agent_version = COALESCE(?, agent_version),
                        updated_at = GETDATE()
                    WHERE agent_id = ?
                    """,
                    (statut_fr, hb.hostname, hb.ip_address, hb.os_info, hb.agent_version, agent_id)
                )
                # Mettre a jour les stats de sync si fournies (mode direct)
                if hb.last_sync:
                    cursor.execute(
                        """
                        UPDATE APP_ETL_Agents SET
                            last_sync = ?,
                            total_syncs = COALESCE(?, total_syncs),
                            total_lignes_sync = COALESCE(?, total_lignes_sync),
                            updated_at = GETDATE()
                        WHERE agent_id = ?
                        """,
                        (hb.last_sync, hb.total_syncs, hb.total_lignes_sync, agent_id)
                    )
                cursor.commit()
        except Exception as e:
            logger.warning(f"Heartbeat: mise a jour base client '{dwh_code}' echouee (non bloquant): {e}")

        # 2. Mise a jour BASE CENTRALE monitoring (non bloquant)
        try:
            write_central(
                """
                UPDATE APP_ETL_Agents_Monitoring SET
                    statut = ?,
                    last_heartbeat = GETDATE(),
                    hostname = COALESCE(?, hostname),
                    ip_address = COALESCE(?, ip_address),
                    os_info = COALESCE(?, os_info),
                    agent_version = COALESCE(?, agent_version),
                    date_modification = GETDATE()
                WHERE agent_id = ?
                """,
                (statut_fr, hb.hostname, hb.ip_address, hb.os_info, hb.agent_version, agent_id)
            )
        except Exception as e:
            logger.debug(f"Monitoring central non mis a jour (non bloquant): {e}")

        # 3. Recuperer les commandes en attente depuis la base centrale
        commands = execute_query(
            """
            SELECT id, command_type, command_data, priority
            FROM APP_ETL_Agent_Commands
            WHERE agent_id = ? AND status = 'pending'
              AND (expires_at IS NULL OR expires_at > GETDATE())
            ORDER BY priority ASC, created_at ASC
            """,
            (agent_id,),
            use_cache=False
        )

        for cmd in commands:
            if cmd.get('command_data') and isinstance(cmd['command_data'], str):
                try:
                    cmd['command_data'] = json.loads(cmd['command_data'])
                except (json.JSONDecodeError, TypeError):
                    pass

        return {"success": True, "commands": commands}

    except Exception as e:
        logger.error(f"Erreur heartbeat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_id}/tables")
async def agent_get_tables(
    agent_id: str,
    x_dwh_code: Optional[str] = Header(None, alias="X-DWH-Code")
):
    """Recupere la configuration des tables pour un agent.
    Source prioritaire : APP_ETL_Tables_Published (client) + APP_ETL_Tables_Config (central).
    Fallback : APP_ETL_Agent_Tables (central), puis YAML.
    """
    # ── Mode Démo ─────────────────────────────────────────────────────────────
    demo = _get_demo_session(agent_id)
    if demo:
        prefix = _demo_table_prefix(agent_id)
        return {
            "success": True,
            "tables": [
                {
                    "name":                 t["name"],
                    "target_table":         f"{prefix}{t['target_table']}",
                    "source_query":         None,
                    "societe_code":         "DEMO",
                    "sync_type":            t["sync_type"],
                    "timestamp_column":     t["timestamp_column"],
                    "primary_key_columns":  t["primary_key_columns"],
                    "is_enabled":           True,
                    "delete_detection":     False,
                    "batch_size":           t["batch_size"],
                    "date_debut":           "2026-01-01",
                    "date_fin":             "2026-02-28",
                }
                for t in DEMO_TABLES
            ]
        }
    # ─────────────────────────────────────────────────────────────────────────
    try:
        # ── Source principale : tables publiees par KASOFT admin ──
        # APP_ETL_Tables_Published (client DB) => is_enabled activee par le client
        # APP_ETL_Tables_Config (central) => source_query, primary_key_columns, timestamp_column
        if x_dwh_code:
            try:
                published = execute_client(
                    """SELECT code, target_table, sync_type, interval_minutes,
                              priority, delete_detection, is_enabled
                       FROM APP_ETL_Tables_Published
                       WHERE is_enabled = 1
                       ORDER BY priority DESC, code""",
                    dwh_code=x_dwh_code,
                    use_cache=False
                )
                if published:
                    # Recuperer les configs centrales pour source_query
                    codes = [p['code'] for p in published]
                    placeholders = ','.join(['?' for _ in codes])
                    central_configs = execute_central(
                        f"""SELECT code, source_query, primary_key_columns,
                                   timestamp_column
                            FROM APP_ETL_Tables_Config
                            WHERE code IN ({placeholders}) AND actif = 1""",
                        tuple(codes), use_cache=False
                    )
                    central_map = {c['code']: c for c in central_configs}

                    result_tables = []
                    for p in published:
                        code = p['code']
                        cfg = central_map.get(code, {})
                        sq = cfg.get('source_query') or ''
                        # Ignorer les tables dont la source_query est un placeholder TODO
                        if not sq or sq.strip().upper().startswith('TODO'):
                            logger.debug(f"Table {code}: source_query non definie, ignoree")
                            continue
                        result_tables.append({
                            'name':                code,
                            'source_query':        sq,
                            'target_table':        p.get('target_table') or code,
                            'societe_code':        '',
                            'primary_key_columns': cfg.get('primary_key_columns') or '',
                            'sync_type':           p.get('sync_type') or 'full',
                            'timestamp_column':    cfg.get('timestamp_column') or 'cbModification',
                            'priority':            p.get('priority') or 'normal',
                            'batch_size':          10000,
                            'is_enabled':          1,
                            'interval_minutes':    p.get('interval_minutes') or 5,
                            'delete_detection':    1 if p.get('delete_detection') else 0
                        })

                    logger.info(f"Agent {agent_id[:8]}... {len(result_tables)} tables depuis APP_ETL_Tables_Published")
                    return {"success": True, "tables": result_tables}
            except Exception as ex:
                logger.warning(f"Impossible de charger tables publiees pour {x_dwh_code}: {ex}")

        # ── Fallback : tables specifiques a cet agent (APP_ETL_Agent_Tables) ──
        agent_tables = execute_query(
            """
            SELECT
                table_name, source_query, target_table, societe_code,
                primary_key_columns, sync_type, timestamp_column,
                priority, is_enabled, interval_minutes, delete_detection
            FROM APP_ETL_Agent_Tables
            WHERE agent_id = ? AND is_enabled = 1
            ORDER BY priority, table_name
            """,
            (agent_id,),
            use_cache=False
        )

        if not agent_tables:
            logger.info(f"Agent {agent_id[:8]}... aucune table, fallback YAML")
            from etl.config.table_config import get_enabled_tables
            tables = get_enabled_tables()
            result_tables = []
            for t in tables:
                source = t.get('source', {})
                source_query = source.get('query', '') if isinstance(source, dict) else ''
                target = t.get('target', {})
                target_table = target.get('table', '') if isinstance(target, dict) else ''
                pk = target.get('primary_key', []) if isinstance(target, dict) else []
                if pk is None:
                    pk = []
                pk_str = ','.join(pk) if isinstance(pk, list) else str(pk)
                result_tables.append({
                    'name': t.get('name'),
                    'source_query': source_query,
                    'target_table': target_table,
                    'societe_code': '',
                    'primary_key_columns': pk_str,
                    'sync_type': t.get('sync_type', 'full'),
                    'timestamp_column': t.get('timestamp_column'),
                    'priority': t.get('priority', 'normal'),
                    'batch_size': t.get('batch_size') or 10000,
                    'is_enabled': 1,
                    'interval_minutes': t.get('interval_minutes', 5),
                    'delete_detection': 1 if t.get('delete_detection', False) else 0
                })
            return {"success": True, "tables": result_tables}

        result_tables = []
        for t in agent_tables:
            result_tables.append({
                'name': t.get('table_name'),
                'source_query': t.get('source_query', ''),
                'target_table': t.get('target_table', ''),
                'societe_code': t.get('societe_code', ''),
                'primary_key_columns': t.get('primary_key_columns', ''),
                'sync_type': t.get('sync_type', 'full'),
                'timestamp_column': t.get('timestamp_column'),
                'priority': t.get('priority', 'normal'),
                'batch_size': 10000,
                'is_enabled': 1,
                'interval_minutes': t.get('interval_minutes', 5),
                'delete_detection': 1 if t.get('delete_detection') else 0
            })

        logger.info(f"Agent {agent_id[:8]}... a {len(result_tables)} tables configurees")
        return {"success": True, "tables": result_tables}

    except Exception as e:
        logger.error(f"Erreur get tables: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/etl/reload-config")
async def reload_etl_config():
    """Recharge la configuration YAML (invalide le cache)"""
    try:
        from etl.config.table_config import invalidate_cache, get_tables

        # Invalider le cache
        invalidate_cache()

        # Recharger les tables
        tables = get_tables()

        return {
            "success": True,
            "message": "Configuration rechargee",
            "tables_count": len(tables)
        }
    except Exception as e:
        logger.error(f"Erreur reload config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/{agent_id}/push-data")
async def agent_push_data(agent_id: str, push: PushDataRequest):
    """Reception des donnees synchronisees"""
    # ── Mode Démo : stocker dans tables préfixées DEMO_{hash}_ ───────────────
    demo = _get_demo_session(agent_id)
    if demo:
        prefix = _demo_table_prefix(agent_id)
        table_name = f"{prefix}{push.target_table}"
        inserted = 0
        updated = 0
        try:
            with get_db_cursor() as cursor:
                # Créer la table si elle n'existe pas
                if push.columns and push.data:
                    col_defs = ", ".join(f"[{c}] NVARCHAR(MAX)" for c in push.columns)
                    pk_cols  = [pk.strip() for pk in (push.primary_key or []) if pk.strip()]
                    pk_constraint = f", PRIMARY KEY ({', '.join(f'[{p}]' for p in pk_cols)})" if pk_cols else ""
                    cursor.execute(f"""
                        IF OBJECT_ID(N'{table_name}', N'U') IS NULL
                        CREATE TABLE [{table_name}] ({col_defs}{pk_constraint})
                    """)
                    # MERGE / INSERT
                    for row in push.data:
                        if pk_cols:
                            # UPSERT via MERGE
                            on_clause = " AND ".join(f"T.[{p}] = S.[{p}]" for p in pk_cols)
                            update_cols = [c for c in push.columns if c not in pk_cols]
                            update_set  = ", ".join(f"T.[{c}] = S.[{c}]" for c in update_cols) if update_cols else "T.[{pk_cols[0]}] = T.[{pk_cols[0]}]"
                            all_cols    = ", ".join(f"[{c}]" for c in push.columns)
                            all_vals    = ", ".join(f"S.[{c}]" for c in push.columns)
                            using_vals  = ", ".join(f"? AS [{c}]" for c in push.columns)
                            row_vals    = [str(row.get(c, "")) if row.get(c) is not None else None for c in push.columns]
                            cursor.execute(
                                f"MERGE [{table_name}] AS T "
                                f"USING (SELECT {using_vals}) AS S ON {on_clause} "
                                f"WHEN MATCHED THEN UPDATE SET {update_set} "
                                f"WHEN NOT MATCHED THEN INSERT ({all_cols}) VALUES ({all_vals});",
                                row_vals
                            )
                        else:
                            cols = ", ".join(f"[{c}]" for c in push.columns)
                            vals = ", ".join("?" for _ in push.columns)
                            row_vals = [str(row.get(c, "")) if row.get(c) is not None else None for c in push.columns]
                            cursor.execute(f"INSERT INTO [{table_name}] ({cols}) VALUES ({vals})", row_vals)
                        inserted += 1
                    cursor.commit()

            # Mise à jour session démo
            write_central(
                """UPDATE APP_Demo_Sessions SET
                    sync_started = 1,
                    tables_synced = CASE WHEN tables_synced IS NULL THEN 1 ELSE tables_synced + 1 END,
                    rows_total = CASE WHEN rows_total IS NULL THEN ? ELSE rows_total + ? END,
                    last_seen = GETDATE()
                   WHERE token = ?""",
                (push.rows_count, push.rows_count, agent_id)
            )
            logger.info(f"[DEMO] Push {push.target_table} → {table_name}: {push.rows_count} lignes")
        except Exception as e:
            logger.error(f"[DEMO] Erreur push-data {push.target_table}: {e}")
            raise HTTPException(status_code=500, detail=f"Erreur stockage démo: {e}")

        return {"success": True, "inserted": inserted, "updated": updated, "demo": True}
    # ─────────────────────────────────────────────────────────────────────────

    try:
        start_time = datetime.now()
        rows_inserted = 0
        rows_updated = 0

        # Recuperer le DWH code de l'agent
        agents = execute_query(
            "SELECT dwh_code FROM APP_ETL_Agents WHERE agent_id = ?",
            (agent_id,),
            use_cache=False
        )
        if not agents:
            raise HTTPException(status_code=404, detail="Agent non trouve")

        dwh_code = agents[0]['dwh_code']

        # Creer le log de sync
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO APP_ETL_Agent_Sync_Log (
                    agent_id, table_name, societe_code,
                    started_at, status, rows_extracted
                ) VALUES (?, ?, ?, GETDATE(), 'running', ?)
                """,
                (agent_id, push.table_name, push.societe_code, push.rows_count)
            )
            cursor.execute("SELECT SCOPE_IDENTITY()")
            log_id = cursor.fetchone()[0]
            cursor.commit()

        try:
            # Charger les donnees dans le DWH
            result = await _load_data_to_dwh(
                dwh_code=dwh_code,
                target_table=push.target_table,
                data=push.data,
                columns=push.columns,
                primary_key=push.primary_key,
                societe_code=push.societe_code
            )

            rows_inserted = result.get('inserted', 0)
            rows_updated = result.get('updated', 0)

            # Mettre a jour le log
            duration = (datetime.now() - start_time).total_seconds()

            with get_db_cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE APP_ETL_Agent_Sync_Log
                    SET completed_at = GETDATE(), status = 'success',
                        rows_inserted = ?, rows_updated = ?,
                        duration_seconds = ?,
                        sync_timestamp_start = ?, sync_timestamp_end = ?
                    WHERE id = ?
                    """,
                    (
                        rows_inserted, rows_updated, duration,
                        push.sync_timestamp_start, push.sync_timestamp_end,
                        log_id
                    )
                )

                # Mettre a jour l'agent
                cursor.execute(
                    """
                    UPDATE APP_ETL_Agents
                    SET last_sync = GETDATE(), last_sync_status = 'success',
                        total_syncs = total_syncs + 1,
                        total_rows_synced = total_rows_synced + ?,
                        consecutive_failures = 0,
                        updated_at = GETDATE()
                    WHERE agent_id = ?
                    """,
                    (rows_inserted + rows_updated, agent_id)
                )
                cursor.commit()

            return {
                "success": True,
                "rows_inserted": rows_inserted,
                "rows_updated": rows_updated,
                "duration_seconds": duration
            }

        except Exception as e:
            # Erreur - mettre a jour le log
            with get_db_cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE APP_ETL_Agent_Sync_Log
                    SET completed_at = GETDATE(), status = 'error',
                        error_message = ?, duration_seconds = ?
                    WHERE id = ?
                    """,
                    (str(e), (datetime.now() - start_time).total_seconds(), log_id)
                )

                cursor.execute(
                    """
                    UPDATE APP_ETL_Agents
                    SET last_sync = GETDATE(), last_sync_status = 'error',
                        consecutive_failures = consecutive_failures + 1,
                        last_error = ?, updated_at = GETDATE()
                    WHERE agent_id = ?
                    """,
                    (str(e), agent_id)
                )
                cursor.commit()

            raise

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur push data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _load_data_to_dwh(
    dwh_code: str,
    target_table: str,
    data: List[Dict[str, Any]],
    columns: List[str],
    primary_key: List[str],
    societe_code: str
) -> Dict[str, int]:
    """
    Charge les donnees dans le DWH avec MERGE (UPSERT).
    Cree la table si elle n'existe pas.
    Ajoute automatiquement la colonne 'societe' avec le code societe.
    Utilise MERGE pour eviter les doublons.
    """
    if not data:
        return {"inserted": 0, "updated": 0}

    # Ajouter la colonne societe aux donnees si pas deja presente
    if 'societe' not in columns:
        columns = ['societe'] + list(columns)
        for row in data:
            row['societe'] = societe_code

    # S'assurer que societe fait partie de la cle primaire pour le multi-tenant
    if primary_key and 'societe' not in primary_key:
        primary_key = ['societe'] + list(primary_key)

    # Obtenir la connexion DWH
    conn = dwh_manager.get_dwh_connection(dwh_code)
    if not conn:
        raise Exception(f"Connexion DWH {dwh_code} non disponible")

    try:
        cursor = conn.cursor()

        # Verifier si la table existe
        cursor.execute(f"""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = '{target_table}'
        """)
        table_exists = cursor.fetchone()[0] > 0

        # Creer la table si elle n'existe pas
        if not table_exists:
            logger.info(f"Creation de la table {target_table} dans le DWH {dwh_code}")

            # Deduire les types de colonnes a partir des donnees
            col_defs = []
            sample_row = data[0]
            for col in columns:
                val = sample_row.get(col)
                if val is None:
                    sql_type = "NVARCHAR(500) NULL"
                elif isinstance(val, bool):
                    sql_type = "BIT NULL"
                elif isinstance(val, int):
                    sql_type = "BIGINT NULL"
                elif isinstance(val, float):
                    sql_type = "FLOAT NULL"
                elif isinstance(val, (datetime,)):
                    sql_type = "DATETIME NULL"
                else:
                    # String - estimer la taille
                    str_val = str(val)
                    if len(str_val) > 4000:
                        sql_type = "NVARCHAR(MAX) NULL"
                    elif len(str_val) > 500:
                        sql_type = "NVARCHAR(4000) NULL"
                    elif len(str_val) > 100:
                        sql_type = "NVARCHAR(500) NULL"
                    else:
                        sql_type = "NVARCHAR(255) NULL"

                col_defs.append(f"[{col}] {sql_type}")

            # Ajouter la cle primaire
            pk_constraint = ""
            if primary_key:
                pk_cols = ', '.join([f'[{pk}]' for pk in primary_key])
                # Nettoyer le nom de la table pour la contrainte
                safe_table_name = target_table.replace(' ', '_').replace('-', '_')
                pk_constraint = f", CONSTRAINT PK_{safe_table_name} PRIMARY KEY ({pk_cols})"

            create_sql = f"""
                CREATE TABLE [{target_table}] (
                    {', '.join(col_defs)}
                    {pk_constraint}
                )
            """
            try:
                cursor.execute(create_sql)
                conn.commit()
                logger.info(f"Table {target_table} creee avec succes avec PK: {primary_key}")
            except Exception as e:
                logger.error(f"Erreur creation table {target_table}: {e}")
                # Essayer sans contrainte PK
                create_sql_no_pk = f"""
                    CREATE TABLE [{target_table}] (
                        {', '.join(col_defs)}
                    )
                """
                cursor.execute(create_sql_no_pk)
                conn.commit()
                logger.info(f"Table {target_table} creee sans PK")

        inserted = 0
        updated = 0

        # Utiliser MERGE si on a une cle primaire, sinon INSERT direct
        columns_str = ', '.join([f'[{c}]' for c in columns])
        placeholders = ', '.join(['?' for _ in columns])

        if primary_key:
            # STRATEGIE OPTIMISEE: Utiliser une table temporaire + MERGE SQL
            # Beaucoup plus rapide que DELETE/INSERT ligne par ligne

            temp_table = f"#temp_{target_table.replace(' ', '_').replace('-', '_')}"

            # Creer table temporaire avec la meme structure
            temp_columns_def = ', '.join([f'[{c}] NVARCHAR(MAX)' for c in columns])
            cursor.execute(f"CREATE TABLE {temp_table} ({temp_columns_def})")

            # Inserer toutes les donnees dans la table temporaire en batch
            insert_temp_sql = f"INSERT INTO {temp_table} ({columns_str}) VALUES ({placeholders})"
            batch_size = 1000

            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                all_values = [[row.get(c) for c in columns] for row in batch]
                try:
                    cursor.executemany(insert_temp_sql, all_values)
                except Exception as e:
                    logger.warning(f"Erreur batch temp INSERT: {e}")
                    for row in batch:
                        values = [row.get(c) for c in columns]
                        try:
                            cursor.execute(insert_temp_sql, values)
                        except Exception:
                            continue

            # Construire la condition de jointure sur la cle primaire
            pk_join = ' AND '.join([f'target.[{pk}] = source.[{pk}]' for pk in primary_key])

            # Construire les colonnes pour UPDATE (exclure les PK)
            update_cols = [c for c in columns if c not in primary_key]
            update_set = ', '.join([f'target.[{c}] = source.[{c}]' for c in update_cols]) if update_cols else 'target.[societe] = source.[societe]'

            # Construire INSERT columns
            insert_cols = ', '.join([f'[{c}]' for c in columns])
            insert_vals = ', '.join([f'source.[{c}]' for c in columns])

            # Executer MERGE SQL (tres performant)
            merge_sql = f"""
                MERGE [{target_table}] AS target
                USING {temp_table} AS source
                ON {pk_join}
                WHEN MATCHED THEN
                    UPDATE SET {update_set}
                WHEN NOT MATCHED THEN
                    INSERT ({insert_cols})
                    VALUES ({insert_vals});
            """

            try:
                cursor.execute(merge_sql)
                inserted = len(data)  # Approximation - MERGE ne donne pas le detail
            except Exception as e:
                logger.error(f"Erreur MERGE: {e}")
                # Fallback: methode classique DELETE + INSERT par batch de PK
                logger.info("Fallback vers DELETE + INSERT batch")

                # Supprimer en batch par PK (plus efficace)
                pk_cols = ', '.join([f'[{pk}]' for pk in primary_key])
                pk_conditions = ' AND '.join([f't.[{pk}] = s.[{pk}]' for pk in primary_key])

                delete_sql = f"""
                    DELETE t FROM [{target_table}] t
                    WHERE EXISTS (
                        SELECT 1 FROM {temp_table} s
                        WHERE {pk_conditions}
                    )
                """
                try:
                    cursor.execute(delete_sql)
                except Exception as del_err:
                    logger.warning(f"Erreur DELETE batch: {del_err}")

                # Inserer depuis temp
                insert_from_temp = f"""
                    INSERT INTO [{target_table}] ({columns_str})
                    SELECT {columns_str} FROM {temp_table}
                """
                try:
                    cursor.execute(insert_from_temp)
                    inserted = len(data)
                except Exception as ins_err:
                    logger.error(f"Erreur INSERT from temp: {ins_err}")

            # Supprimer la table temporaire
            try:
                cursor.execute(f"DROP TABLE {temp_table}")
            except Exception:
                pass

            conn.commit()
        else:
            # Pas de cle primaire - utiliser INSERT batch direct
            insert_sql = f"INSERT INTO [{target_table}] ({columns_str}) VALUES ({placeholders})"

            batch_size = 1000
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                all_values = [[row.get(c) for c in columns] for row in batch]

                try:
                    cursor.executemany(insert_sql, all_values)
                    inserted += len(batch)
                except Exception as e:
                    # Fallback: insertion ligne par ligne
                    logger.warning(f"Erreur batch INSERT, fallback: {e}")
                    for row in batch:
                        values = [row.get(c) for c in columns]
                        try:
                            cursor.execute(insert_sql, values)
                            inserted += 1
                        except Exception as e2:
                            logger.warning(f"Erreur INSERT ligne: {e2}")
                            continue

                conn.commit()

        cursor.close()
        return {"inserted": inserted, "updated": updated}

    except Exception as e:
        logger.error(f"Erreur load DWH: {e}")
        raise


@router.get("/agents/{agent_id}/commands")
async def agent_get_commands(agent_id: str):
    """Recupere les commandes en attente pour un agent"""
    try:
        commands = execute_query(
            """
            SELECT id, command_type, command_data, priority
            FROM APP_ETL_Agent_Commands
            WHERE agent_id = ? AND status = 'pending'
              AND (expires_at IS NULL OR expires_at > GETDATE())
            ORDER BY priority ASC, created_at ASC
            """,
            (agent_id,),
            use_cache=False
        )

        # Parser command_data JSON si c'est une string
        for cmd in commands:
            if cmd.get('command_data') and isinstance(cmd['command_data'], str):
                try:
                    cmd['command_data'] = json.loads(cmd['command_data'])
                except (json.JSONDecodeError, TypeError):
                    pass  # Garder la valeur originale si parsing echoue

        return {"success": True, "commands": commands}

    except Exception as e:
        logger.error(f"Erreur get commands: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/{agent_id}/commands/{command_id}/ack")
async def agent_ack_command(agent_id: str, command_id: int):
    """Acquitte une commande"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                UPDATE APP_ETL_Agent_Commands
                SET status = 'acknowledged', acknowledged_at = GETDATE()
                WHERE id = ? AND agent_id = ?
                """,
                (command_id, agent_id)
            )
            cursor.commit()

        return {"success": True}

    except Exception as e:
        logger.error(f"Erreur ack command: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/{agent_id}/commands/{command_id}/complete")
async def agent_complete_command(agent_id: str, command_id: int, request: Request):
    """Marque une commande comme terminee"""
    try:
        data = await request.json()

        with get_db_cursor() as cursor:
            cursor.execute(
                """
                UPDATE APP_ETL_Agent_Commands
                SET status = ?, completed_at = GETDATE(),
                    result = ?, error_message = ?
                WHERE id = ? AND agent_id = ?
                """,
                (
                    'completed' if data.get('success') else 'failed',
                    json.dumps(data.get('result')) if data.get('result') else None,
                    data.get('error'),
                    command_id, agent_id
                )
            )
            cursor.commit()

        return {"success": True}

    except Exception as e:
        logger.error(f"Erreur complete command: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Routes Tables ETL Globales (partagees entre agents)
# ============================================================

@router.get("/admin/etl/tables/available")
async def list_available_etl_tables():
    """Liste les tables ETL disponibles (configuration globale)

    IMPORTANT: Cette route utilise la meme source que les routes de modification/suppression
    (ETL_Tables_Config via table_config.py) pour garantir la coherence.
    """
    try:
        from etl.config.table_config import get_tables

        # Lire depuis ETL_Tables_Config (meme source que delete/update)
        raw_tables = get_tables()

        # Formater pour le frontend
        tables = []
        for t in raw_tables:
            tables.append({
                'name': t.get('name'),
                'source_table': t.get('source', {}).get('table', ''),
                'source_query': t.get('source', {}).get('query', ''),
                'target_table': t.get('target', {}).get('table', ''),
                'sync_type': t.get('sync_type', 'incremental'),
                'priority': t.get('priority', 'normal'),
                'description': t.get('description', ''),
                'primary_key': t.get('target', {}).get('primary_key', []),
                'timestamp_column': t.get('timestamp_column', ''),
                'interval_minutes': t.get('interval_minutes', 5),
                'delete_detection': t.get('delete_detection', False),
                'is_enabled': t.get('enabled', True)
            })

        return {"success": True, "data": tables, "count": len(tables)}

    except Exception as e:
        logger.error(f"Erreur liste tables ETL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/etl/tables/import-yaml")
async def import_yaml_to_sql_tables():
    """
    Importe les tables du fichier YAML vers la table SQL ETL_Tables_Config.
    Permet de migrer d'une configuration YAML vers SQL pour beneficier
    de la gestion complete (ajout, modification, suppression) via l'UI.
    """
    try:
        from etl.config.table_config import import_yaml_to_sql

        result = import_yaml_to_sql()

        return {
            "success": result['success'],
            "message": f"Import termine: {result['imported']} importees, {result['skipped']} ignorees, {result['errors']} erreurs",
            "imported": result['imported'],
            "skipped": result['skipped'],
            "errors": result['errors'],
            "details": result.get('details', [])
        }

    except Exception as e:
        logger.error(f"Erreur import YAML->SQL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/etl/agents/{agent_id}/sync-status")
async def get_agent_sync_status(agent_id: str):
    """Recupere le statut de sync de toutes les tables pour un agent"""
    try:
        # Recuperer le statut des syncs par table depuis les logs
        sync_status = execute_query(
            """
            SELECT
                t.table_name,
                t.societe_code,
                t.target_table,
                t.sync_type,
                t.is_enabled,
                t.last_sync,
                t.last_sync_status,
                t.last_sync_rows,
                t.last_error
            FROM APP_ETL_Agent_Tables t
            WHERE t.agent_id = ?
            ORDER BY t.table_name, t.societe_code
            """,
            (agent_id,),
            use_cache=False
        )

        # Recuperer les stats globales
        stats = execute_query(
            """
            SELECT
                COUNT(*) AS total_tables,
                SUM(CASE WHEN is_enabled = 1 THEN 1 ELSE 0 END) AS enabled_tables,
                SUM(CASE WHEN last_sync_status = 'success' THEN 1 ELSE 0 END) AS success_tables,
                SUM(CASE WHEN last_sync_status = 'error' THEN 1 ELSE 0 END) AS error_tables,
                SUM(COALESCE(last_sync_rows, 0)) AS total_rows
            FROM APP_ETL_Agent_Tables
            WHERE agent_id = ?
            """,
            (agent_id,),
            use_cache=False
        )

        return {
            "success": True,
            "data": sync_status,
            "stats": stats[0] if stats else {},
            "count": len(sync_status)
        }

    except Exception as e:
        logger.error(f"Erreur sync status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Routes DWH
# ============================================================

@router.get("/admin/dwh")
async def list_dwh():
    """Liste les DWH disponibles"""
    print("[DEBUG] list_dwh() APPELE - entree fonction")
    try:
        print("[DEBUG] list_dwh() - avant execute_query")
        dwh_list = execute_query(
            """
            SELECT code, nom, serveur_dwh, base_dwh, actif, ISNULL(is_demo,0) AS is_demo
            FROM APP_DWH
            WHERE actif = 1
            ORDER BY nom
            """,
            use_cache=False
        )
        print(f"[DEBUG] list_dwh() - apres execute_query, resultat: {dwh_list}")
        return {"success": True, "data": dwh_list}
    except Exception as e:
        import traceback
        print(f"[DEBUG] list_dwh() ERREUR: {e}")
        print(f"[DEBUG] Traceback: {traceback.format_exc()}")
        return {"success": True, "data": []}


# ============================================================
# Routes DWH Admin (Multi-tenant)
# ============================================================

@router.get("/dwh-admin/list")
async def dwh_admin_list():
    """Liste tous les DWH clients pour l'administration"""
    try:
        dwh_list = execute_query(
            """
            SELECT
                id, code, nom, raison_sociale, adresse, ville, pays,
                telephone, email, logo_url, serveur_dwh, base_dwh,
                user_dwh, actif, date_creation
            FROM APP_DWH
            ORDER BY nom
            """,
            use_cache=False
        )

        # Compter les sources par DWH
        for dwh in dwh_list:
            try:
                sources = execute_query(
                    "SELECT COUNT(*) as cnt FROM APP_DWH_Sources WHERE dwh_code = ?",
                    (dwh['code'],),
                    use_cache=False
                )
                dwh['sources_count'] = sources[0]['cnt'] if sources else 0
            except:
                dwh['sources_count'] = 0

        return {"success": True, "data": dwh_list}
    except Exception as e:
        logger.error(f"Erreur liste DWH admin: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dwh-admin/client-databases")
async def dwh_admin_list_client_databases_early():
    """Liste toutes les bases client OptiBoard_XXX avec statut de connexion."""
    import asyncio
    try:
        result = await asyncio.to_thread(_list_client_databases)
        return result
    except Exception as e:
        logger.error(f"Erreur liste bases client: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dwh-admin/{code}")
async def dwh_admin_get(code: str):
    """Recupere les details d'un DWH"""
    try:
        dwh = execute_query(
            """
            SELECT
                id, code, nom, raison_sociale, adresse, ville, pays,
                telephone, email, logo_url, serveur_dwh, base_dwh,
                user_dwh, password_dwh,
                serveur_optiboard, base_optiboard, user_optiboard,
                actif, date_creation
            FROM APP_DWH
            WHERE code = ?
            """,
            (code,),
            use_cache=False
        )
        if not dwh:
            raise HTTPException(status_code=404, detail="DWH non trouve")
        return {"success": True, "data": dwh[0]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur get DWH: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dwh-admin")
async def dwh_admin_create(dwh: Dict[str, Any] = Body(...)):
    """Cree un nouveau DWH. Si la base de donnees n'existe pas, la cree automatiquement avec les 35 tables."""
    try:
        serveur = dwh.get('serveur_dwh')
        base = dwh.get('base_dwh')
        user_dwh = dwh.get('user_dwh')
        pwd_dwh = dwh.get('password_dwh')

        # Auto-creation de la base si elle n'existe pas
        db_init_result = None
        if all([serveur, base, user_dwh, pwd_dwh]):
            try:
                db_exists = _check_db_exists(serveur, base, user_dwh, pwd_dwh)
                if not db_exists:
                    logger.info(f"Base '{base}' inexistante sur {serveur}, creation automatique...")
                    db_init_result = _create_dwh_database(serveur, base, user_dwh, pwd_dwh)
                    logger.info(f"Resultat init DB: {db_init_result}")
            except Exception as init_err:
                logger.warning(f"Impossible de verifier/creer la base '{base}': {init_err}")
                # On continue quand meme avec l'enregistrement dans APP_DWH

        # Inserer le DWH dans la table centrale APP_DWH
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO APP_DWH (
                    code, nom, raison_sociale, adresse, ville, pays,
                    telephone, email, logo_url, serveur_dwh, base_dwh,
                    user_dwh, password_dwh,
                    serveur_optiboard, base_optiboard, user_optiboard, password_optiboard,
                    actif
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    dwh.get('code'), dwh.get('nom'), dwh.get('raison_sociale'),
                    dwh.get('adresse'), dwh.get('ville'), dwh.get('pays', 'Maroc'),
                    dwh.get('telephone'), dwh.get('email'), dwh.get('logo_url'),
                    serveur, base, user_dwh, pwd_dwh,
                    dwh.get('serveur_optiboard') or serveur,
                    dwh.get('base_optiboard') or f"OptiBoard_clt{dwh.get('code')}",
                    dwh.get('user_optiboard') or user_dwh,
                    dwh.get('password_optiboard') or pwd_dwh,
                    1 if dwh.get('actif', True) else 0
                )
            )
            cursor.commit()

        # NOTE: La base OptiBoard n'est PAS créée automatiquement ici.
        # Le serveur backend ne peut pas créer une base sur un serveur "localhost" qui
        # serait la machine du client (pas le backend). Utiliser le bouton
        # "Initialiser base OptiBoard" dans l'interface, ou l'endpoint /init-optiboard.

        message = "DWH cree avec succes"
        if db_init_result and db_init_result.get('created'):
            message += f". Base DWH '{base}' creee avec {db_init_result.get('tables_count', 0)} tables"

        return {
            "success": True,
            "message": message,
            "db_created": db_init_result.get('created', False) if db_init_result else False,
            "tables_count": db_init_result.get('tables_count', 0) if db_init_result else 0,
            "client_db_created": False,
            "client_db_name": None
        }
    except Exception as e:
        logger.error(f"Erreur creation DWH: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/dwh-admin/{code}")
async def dwh_admin_update(code: str, dwh: Dict[str, Any] = Body(...)):
    """Met a jour un DWH"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                UPDATE APP_DWH SET
                    nom = ?, raison_sociale = ?, adresse = ?, ville = ?, pays = ?,
                    telephone = ?, email = ?, logo_url = ?, serveur_dwh = ?,
                    base_dwh = ?, user_dwh = ?, password_dwh = COALESCE(NULLIF(?, ''), password_dwh),
                    serveur_optiboard = ?, base_optiboard = ?, user_optiboard = ?,
                    password_optiboard = COALESCE(NULLIF(?, ''), password_optiboard),
                    actif = ?, date_modification = GETDATE()
                WHERE code = ?
                """,
                (
                    dwh.get('nom'), dwh.get('raison_sociale'), dwh.get('adresse'),
                    dwh.get('ville'), dwh.get('pays'), dwh.get('telephone'),
                    dwh.get('email'), dwh.get('logo_url'), dwh.get('serveur_dwh'),
                    dwh.get('base_dwh'), dwh.get('user_dwh'), dwh.get('password_dwh') or None,
                    dwh.get('serveur_optiboard'), dwh.get('base_optiboard'),
                    dwh.get('user_optiboard'), dwh.get('password_optiboard') or None,
                    1 if dwh.get('actif', True) else 0, code
                )
            )
            cursor.commit()
        return {"success": True, "message": "DWH mis a jour"}
    except Exception as e:
        logger.error(f"Erreur update DWH: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dwh-admin/{code}/optiboard-sql-script")
async def dwh_admin_optiboard_sql_script(code: str):
    """
    Retourne un script SQL complet pret a executer en SSMS sur le serveur local.
    Cree la base OptiBoard_cltXXX et toutes ses tables.
    """
    from fastapi.responses import PlainTextResponse
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT base_optiboard, serveur_optiboard, serveur_dwh
                FROM APP_DWH WHERE code = ?
            """, (code,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail=f"DWH '{code}' non trouve")
            db_name = row[0] or f"OptiBoard_clt{code}"
            srv     = row[1] or row[2] or '.'

        # Construire le script SQL complet
        # Remplacer les blocs IF NOT EXISTS par version compatible batch SSMS
        tables_sql = CLIENT_OPTIBOARD_TABLES_SQL.strip()

        script = f"""-- ============================================================
-- Script d'initialisation de la base {db_name}
-- Serveur cible : {srv}
-- Genere automatiquement par OptiBoard
-- INSTRUCTIONS : Ouvrir ce fichier dans SSMS, se connecter au
--   serveur "{srv}", puis executer (F5)
-- ============================================================

USE master;
GO

-- Creer la base si elle n'existe pas
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = N'{db_name}')
BEGIN
    CREATE DATABASE [{db_name}];
    PRINT 'Base {db_name} creee.';
END
ELSE
    PRINT 'Base {db_name} existe deja.';
GO

USE [{db_name}];
GO

-- ============================================================
-- Creation des tables
-- ============================================================
{tables_sql}
GO

PRINT 'Initialisation de {db_name} terminee avec succes.';
GO
"""
        from fastapi.responses import Response
        return Response(
            content=script,
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="init_{db_name}.sql"'}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dwh-admin/{code}/init-optiboard")
async def dwh_admin_init_optiboard(code: str):
    """
    Cree (ou reInitialise) la base OptiBoard_cltXXX en utilisant
    les infos de connexion OptiBoard stockees dans APP_DWH.
    A appeler manuellement depuis l'interface apres creation du DWH.
    """
    try:
        # Lire les infos OptiBoard depuis APP_DWH
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT serveur_optiboard, base_optiboard, user_optiboard, password_optiboard,
                       serveur_dwh, user_dwh, password_dwh
                FROM APP_DWH WHERE code = ?
            """, (code,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail=f"DWH '{code}' non trouve")
            srv   = row[0] or row[4]   # serveur_optiboard ou fallback serveur_dwh
            db    = row[1] or f"OptiBoard_clt{code}"
            user  = row[2] or row[5]   # user_optiboard ou fallback user_dwh
            pwd   = row[3] or row[6]   # password_optiboard ou fallback password_dwh

        if not srv:
            raise HTTPException(status_code=400, detail="Serveur OptiBoard non configure")

        logger.info(f"[INIT-OPTIBOARD] Creation de {db} sur {srv} (user={user})")
        result = _create_client_optiboard_db(code, srv, user, pwd, db_name=db)

        if result.get("error"):
            raise HTTPException(status_code=500, detail=result["error"])

        return {
            "success": True,
            "db_name": db,
            "server": srv,
            "created": result.get("created", False),
            "tables_count": result.get("tables_count", 0),
            "message": (
                f"Base '{db}' creee avec succes sur {srv} ({result.get('tables_count', 0)} tables)"
                if result.get("created")
                else f"Base '{db}' deja existante sur {srv} — tables verifiees"
            )
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur init-optiboard {code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _drop_database_if_exists(serveur: str, db_name: str, user: str, password: str) -> Dict[str, Any]:
    """Supprime (DROP) une base SQL Server si elle existe."""
    import pyodbc as _pyodbc
    if not db_name or not serveur:
        return {"dropped": False, "db": db_name, "reason": "infos manquantes"}
    try:
        conn_str = _build_conn_str(serveur, "master", user, password)
        conn = _pyodbc.connect(conn_str, timeout=15)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM sys.databases WHERE name = ?", (db_name,))
        if cur.fetchone()[0] == 0:
            conn.close()
            return {"dropped": False, "db": db_name, "reason": "n'existe pas"}
        cur.execute(f"ALTER DATABASE [{db_name}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE")
        cur.execute(f"DROP DATABASE [{db_name}]")
        conn.close()
        logger.info(f"[DROP-DB] Base '{db_name}' supprimee sur {serveur}")
        return {"dropped": True, "db": db_name}
    except Exception as e:
        logger.warning(f"[DROP-DB] Impossible de supprimer '{db_name}' sur {serveur}: {e}")
        return {"dropped": False, "db": db_name, "error": str(e)}


@router.delete("/dwh-admin/{code}")
async def dwh_admin_delete(code: str, force: bool = Query(False), drop_databases: bool = Query(False)):
    """
    Supprime un DWH du registre + DROP automatique de DWH_XXX et OptiBoard_cltXXX.
    """
    try:
        drop_results = []

        with get_db_cursor() as cursor:
            # ── Lire les infos de connexion AVANT suppression ────────────────
            cursor.execute("""
                SELECT serveur_dwh, base_dwh, user_dwh, password_dwh,
                       serveur_optiboard, base_optiboard, user_optiboard, password_optiboard
                FROM APP_DWH WHERE code = ?
            """, (code,))
            row = cursor.fetchone()
            if row:
                dwh_srv  = row[0] or ''
                dwh_base = row[1] or f"DWH_{code}"
                dwh_user = row[2] or ''
                dwh_pwd  = row[3] or ''
                ob_srv   = row[4] or dwh_srv
                ob_base  = row[5] or f"OptiBoard_clt{code}"
                ob_user  = row[6] or dwh_user
                ob_pwd   = row[7] or dwh_pwd

                # DROP automatique des deux bases
                drop_results.append(_drop_database_if_exists(dwh_srv, dwh_base, dwh_user, dwh_pwd))
                drop_results.append(_drop_database_if_exists(ob_srv,  ob_base,  ob_user,  ob_pwd))

            # ── Cascade manuelle ────────────────────────────────────────────────
            child_tables = [
                "APP_ETL_Agents_Monitoring",
                "APP_DWH_Sources",
                "APP_ETL_Agent_Tables",
                "APP_ClientDB",
            ]
            for tbl in child_tables:
                try:
                    cursor.execute(f"DELETE FROM {tbl} WHERE dwh_code = ?", (code,))
                except Exception:
                    pass

            cursor.execute("DELETE FROM APP_DWH WHERE code = ?", (code,))
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="DWH non trouve")
            cursor.commit()

        msg = f"DWH '{code}' supprime"
        if drop_results:
            dropped = [r['db'] for r in drop_results if r.get('dropped')]
            skipped = [r['db'] for r in drop_results if not r.get('dropped')]
            if dropped:
                msg += f" | Bases supprimees: {', '.join(dropped)}"
            if skipped:
                msg += f" | Non supprimees: {', '.join(skipped)}"

        return {"success": True, "message": msg, "drop_results": drop_results}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur suppression DWH: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _is_local_server(server: str) -> bool:
    """Detecte si le serveur est local (localhost, ., 127.0.0.1...)"""
    if not server:
        return False
    s = server.strip().lower()
    return s in ('.', 'localhost', '(local)', '127.0.0.1') or \
           s.startswith('tcp:localhost') or s.startswith('tcp:127.0.0.1') or \
           s.startswith('.\\') or s.startswith('localhost\\')

def _build_conn_str(server: str, database: str, user: str, password: str, driver: str = None) -> str:
    """Construit une connection string SQL Server.
    Utilise toujours SQL Auth (UID/PWD) si les credentials sont fournis,
    sinon Windows Auth (pour les serveurs locaux sans mot de passe configure).
    """
    drv = driver or "{ODBC Driver 17 for SQL Server}"
    # Utiliser SQL Auth si des credentials sont fournis, sinon Windows Auth
    if user and password:
        auth = f"UID={user};PWD={password}"
    elif _is_local_server(server):
        auth = "Integrated Security=yes;Trusted_Connection=yes"
    else:
        auth = f"UID={user};PWD={password}"
    return (
        f"DRIVER={drv};SERVER={server};DATABASE={database};"
        f"{auth};TrustServerCertificate=yes;"
    )


def _check_db_exists(serveur: str, base: str, user: str, password: str) -> bool:
    """Verifie si une base de donnees existe sur le serveur SQL"""
    import pyodbc
    conn_str = _build_conn_str(serveur, "master", user, password)
    conn = pyodbc.connect(conn_str, timeout=10)
    cursor = conn.cursor()
    cursor.execute("SELECT DB_ID(?)", (base,))
    result = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return result is not None


def _create_dwh_database(serveur: str, base: str, user: str, password: str) -> Dict[str, Any]:
    """Cree la base DWH et initialise les 35 tables depuis le template SQL"""
    import pyodbc
    import re
    from pathlib import Path

    # 1. Connexion a master pour creer la base
    conn_master_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={serveur};"
        f"DATABASE=master;"
        f"UID={user};"
        f"PWD={password};"
        "TrustServerCertificate=yes;"
    )
    conn_master = pyodbc.connect(conn_master_str, timeout=30)
    conn_master.autocommit = True
    cursor_master = conn_master.cursor()

    # 2. Verifier si la base existe deja
    cursor_master.execute("SELECT DB_ID(?)", (base,))
    if cursor_master.fetchone()[0] is not None:
        cursor_master.close()
        conn_master.close()
        return {"created": False, "message": f"La base '{base}' existe deja", "tables_count": 0}

    # 3. Creer la base
    logger.info(f"Creation de la base de donnees [{base}]...")
    cursor_master.execute(f"CREATE DATABASE [{base}]")
    cursor_master.close()
    conn_master.close()
    logger.info(f"Base [{base}] creee avec succes")

    # 4. Se connecter a la nouvelle base pour creer les tables
    conn_dwh_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={serveur};"
        f"DATABASE={base};"
        f"UID={user};"
        f"PWD={password};"
        "TrustServerCertificate=yes;"
    )
    conn_dwh = pyodbc.connect(conn_dwh_str, timeout=30)
    conn_dwh.autocommit = True
    cursor_dwh = conn_dwh.cursor()

    # 5. Charger et preparer le script SQL template
    sql_path = Path(__file__).parent.parent.parent / "sql" / "sql_jobs" / "01_create_dwh_database.sql"
    if not sql_path.exists():
        cursor_dwh.close()
        conn_dwh.close()
        return {"created": True, "message": f"Base '{base}' creee mais template SQL introuvable", "tables_count": 0}

    sql_content = sql_path.read_text(encoding='utf-8')

    # Remplacer le placeholder par le nom reel de la base
    sql_content = sql_content.replace('{DWH_NAME}', base)

    # Splitter par GO (separateur de batch SQL Server)
    batches = re.split(r'^\s*GO\s*$', sql_content, flags=re.MULTILINE | re.IGNORECASE)

    tables_created = 0
    errors = []
    for i, batch in enumerate(batches):
        # Supprimer les lignes USE [...] du batch — on est deja connecte a la bonne base
        clean_lines = [l for l in batch.split('\n') if not re.match(r'^\s*USE\s+\[', l, re.IGNORECASE)]
        clean_batch = '\n'.join(clean_lines).strip()
        if not clean_batch:
            continue

        # Ignorer les batches qui ne sont que des PRINT ou SET
        lines = [l.strip() for l in clean_batch.split('\n') if l.strip() and not l.strip().startswith('--')]
        if not lines:
            continue
        if all(l.upper().startswith('PRINT') or l.upper().startswith('SET NOCOUNT') for l in lines):
            continue

        try:
            cursor_dwh.execute(clean_batch)
            if 'CREATE TABLE' in clean_batch.upper():
                tables_created += 1
        except Exception as e:
            error_msg = str(e)
            # Ignorer les erreurs "table existe deja" (IF NOT EXISTS devrait les prevenir)
            if '2714' not in error_msg:  # Error 2714 = object already exists
                errors.append(f"Batch {i}: {error_msg[:100]}")
                logger.warning(f"Erreur batch {i} pour [{base}]: {error_msg[:200]}")

    cursor_dwh.close()
    conn_dwh.close()

    message = f"Base '{base}' creee avec {tables_created} tables"
    if errors:
        message += f" ({len(errors)} avertissements)"

    logger.info(f"Init DWH [{base}] termine: {tables_created} tables, {len(errors)} erreurs")
    return {"created": True, "message": message, "tables_count": tables_created, "warnings": errors[:5]}


# =====================================================
# CREATION BASE CLIENT OptiBoard_XXX (Multi-Tenant)
# =====================================================

# SQL de creation des tables dans chaque base client OptiBoard_XXX
CLIENT_OPTIBOARD_TABLES_SQL = """
-- Permissions pages par utilisateur
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_UserPages' AND xtype='U')
CREATE TABLE APP_UserPages (
    id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NOT NULL,
    page_code VARCHAR(50) NOT NULL
);

-- Permissions menus par utilisateur
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_UserMenus' AND xtype='U')
CREATE TABLE APP_UserMenus (
    id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NOT NULL,
    menu_id INT NOT NULL,
    can_view BIT DEFAULT 1,
    can_export BIT DEFAULT 1
);

-- Dashboards
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Dashboards' AND xtype='U')
CREATE TABLE APP_Dashboards (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nom NVARCHAR(200) NOT NULL,
    code VARCHAR(100) NULL,
    description NVARCHAR(500),
    config NVARCHAR(MAX),
    widgets NVARCHAR(MAX),
    is_public BIT DEFAULT 0,
    is_custom BIT DEFAULT 0,
    created_by INT NULL,
    actif BIT DEFAULT 1,
    date_creation DATETIME DEFAULT GETDATE(),
    date_modification DATETIME DEFAULT GETDATE()
);

-- DataSources custom
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_DataSources' AND xtype='U')
CREATE TABLE APP_DataSources (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nom NVARCHAR(200) NOT NULL,
    code VARCHAR(100) NULL,
    type VARCHAR(50) NOT NULL DEFAULT 'query',
    query_template NVARCHAR(MAX),
    parameters NVARCHAR(MAX),
    description NVARCHAR(500),
    is_custom BIT DEFAULT 0,
    date_creation DATETIME DEFAULT GETDATE()
);

-- GridViews
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_GridViews' AND xtype='U')
CREATE TABLE APP_GridViews (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nom NVARCHAR(200) NOT NULL,
    code VARCHAR(100) NULL,
    description NVARCHAR(500),
    query_template NVARCHAR(MAX),
    columns_config NVARCHAR(MAX),
    parameters NVARCHAR(MAX),
    features NVARCHAR(MAX),
    is_custom BIT DEFAULT 0,
    actif BIT DEFAULT 1,
    date_creation DATETIME DEFAULT GETDATE(),
    date_modification DATETIME DEFAULT GETDATE()
);

-- GridView User Prefs
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_GridView_User_Prefs' AND xtype='U')
CREATE TABLE APP_GridView_User_Prefs (
    id INT IDENTITY(1,1) PRIMARY KEY,
    gridview_id INT NOT NULL,
    user_id INT NOT NULL,
    columns_config NVARCHAR(MAX),
    date_modification DATETIME DEFAULT GETDATE(),
    CONSTRAINT UQ_GridView_User UNIQUE (gridview_id, user_id)
);

-- Pivots (legacy)
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Pivots' AND xtype='U')
CREATE TABLE APP_Pivots (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nom NVARCHAR(200) NOT NULL,
    description NVARCHAR(500),
    query_template NVARCHAR(MAX),
    pivot_config NVARCHAR(MAX),
    parameters NVARCHAR(MAX),
    actif BIT DEFAULT 1,
    date_creation DATETIME DEFAULT GETDATE(),
    date_modification DATETIME DEFAULT GETDATE()
);

-- Pivots V2
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Pivots_V2' AND xtype='U')
CREATE TABLE APP_Pivots_V2 (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nom NVARCHAR(200) NOT NULL,
    code VARCHAR(100) NULL,
    description NVARCHAR(500),
    data_source_id INT NULL,
    data_source_code VARCHAR(100),
    rows_config NVARCHAR(MAX),
    columns_config NVARCHAR(MAX),
    filters_config NVARCHAR(MAX),
    values_config NVARCHAR(MAX),
    show_grand_totals BIT DEFAULT 1,
    show_subtotals BIT DEFAULT 0,
    show_row_percent BIT DEFAULT 0,
    show_col_percent BIT DEFAULT 0,
    show_total_percent BIT DEFAULT 0,
    comparison_mode NVARCHAR(50),
    formatting_rules NVARCHAR(MAX),
    source_params NVARCHAR(MAX),
    is_public BIT DEFAULT 0,
    is_custom BIT DEFAULT 0,
    created_by INT NULL,
    created_at DATETIME DEFAULT GETDATE(),
    updated_at DATETIME DEFAULT GETDATE(),
    grand_total_position NVARCHAR(20) DEFAULT 'bottom',
    subtotal_position NVARCHAR(20) DEFAULT 'bottom',
    show_summary_row BIT DEFAULT 0,
    summary_functions NVARCHAR(MAX),
    window_calculations NVARCHAR(MAX)
);

-- Pivot User Prefs
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Pivot_User_Prefs' AND xtype='U')
CREATE TABLE APP_Pivot_User_Prefs (
    id INT IDENTITY(1,1) PRIMARY KEY,
    pivot_id INT NOT NULL,
    user_id INT NOT NULL,
    custom_config NVARCHAR(MAX),
    date_modification DATETIME DEFAULT GETDATE(),
    CONSTRAINT UQ_Pivot_User UNIQUE (pivot_id, user_id)
);

-- Menus
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Menus' AND xtype='U')
CREATE TABLE APP_Menus (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nom NVARCHAR(100) NOT NULL,
    code VARCHAR(100),
    icon VARCHAR(50),
    url VARCHAR(200),
    parent_id INT NULL,
    ordre INT DEFAULT 0,
    type VARCHAR(20) DEFAULT 'link',
    target_id INT NULL,
    actif BIT DEFAULT 1,
    is_custom BIT DEFAULT 0,
    roles NVARCHAR(200),
    date_creation DATETIME DEFAULT GETDATE()
);

-- Email Config
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_EmailConfig' AND xtype='U')
CREATE TABLE APP_EmailConfig (
    id INT IDENTITY(1,1) PRIMARY KEY,
    smtp_server VARCHAR(200),
    smtp_port INT DEFAULT 587,
    smtp_username VARCHAR(200),
    smtp_password VARCHAR(200),
    from_email VARCHAR(200),
    from_name NVARCHAR(100),
    use_ssl BIT DEFAULT 0,
    use_tls BIT DEFAULT 1,
    actif BIT DEFAULT 1,
    date_modification DATETIME DEFAULT GETDATE()
);

-- Settings
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Settings' AND xtype='U')
CREATE TABLE APP_Settings (
    id INT IDENTITY(1,1) PRIMARY KEY,
    setting_key VARCHAR(100) NOT NULL,
    setting_value NVARCHAR(MAX),
    setting_type VARCHAR(20) DEFAULT 'string',
    description NVARCHAR(500),
    date_modification DATETIME DEFAULT GETDATE()
);

-- Report Schedules
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ReportSchedules' AND xtype='U')
CREATE TABLE APP_ReportSchedules (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nom NVARCHAR(255) NOT NULL,
    description NVARCHAR(MAX),
    report_type NVARCHAR(50) NOT NULL,
    report_id INT,
    export_format NVARCHAR(20) DEFAULT 'excel',
    frequency NVARCHAR(20) NOT NULL,
    schedule_time NVARCHAR(10) DEFAULT '08:00',
    schedule_day INT,
    recipients NVARCHAR(MAX) NOT NULL,
    cc_recipients NVARCHAR(MAX),
    filters NVARCHAR(MAX),
    is_active BIT DEFAULT 1,
    last_run DATETIME,
    next_run DATETIME,
    created_by INT,
    created_at DATETIME DEFAULT GETDATE(),
    updated_at DATETIME DEFAULT GETDATE()
);

-- Report History
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ReportHistory' AND xtype='U')
CREATE TABLE APP_ReportHistory (
    id INT IDENTITY(1,1) PRIMARY KEY,
    schedule_id INT,
    report_name NVARCHAR(255),
    recipients NVARCHAR(MAX),
    status NVARCHAR(20) NOT NULL,
    error_message NVARCHAR(MAX),
    file_path NVARCHAR(500),
    file_size INT,
    sent_at DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (schedule_id) REFERENCES APP_ReportSchedules(id) ON DELETE SET NULL
);

-- Audit Log
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_AuditLog' AND xtype='U')
CREATE TABLE APP_AuditLog (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NULL,
    action VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50),
    entity_id INT NULL,
    details NVARCHAR(MAX),
    ip_address VARCHAR(50),
    user_agent NVARCHAR(500),
    date_action DATETIME DEFAULT GETDATE()
);

-- Migration: ajouter code et is_custom aux tables client existantes
IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_GridViews') AND name='code')
    ALTER TABLE APP_GridViews ADD code VARCHAR(100) NULL;
IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_GridViews') AND name='is_custom')
    ALTER TABLE APP_GridViews ADD is_custom BIT DEFAULT 0;
IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_Pivots_V2') AND name='code')
    ALTER TABLE APP_Pivots_V2 ADD code VARCHAR(100) NULL;
IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_Pivots_V2') AND name='is_custom')
    ALTER TABLE APP_Pivots_V2 ADD is_custom BIT DEFAULT 0;
IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_Dashboards') AND name='code')
    ALTER TABLE APP_Dashboards ADD code VARCHAR(100) NULL;
IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_Dashboards') AND name='is_custom')
    ALTER TABLE APP_Dashboards ADD is_custom BIT DEFAULT 0;
IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_DataSources') AND name='code')
    ALTER TABLE APP_DataSources ADD code VARCHAR(100) NULL;
IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_DataSources') AND name='is_custom')
    ALTER TABLE APP_DataSources ADD is_custom BIT DEFAULT 0;
IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_Menus') AND name='is_custom')
    ALTER TABLE APP_Menus ADD is_custom BIT DEFAULT 0;

-- Index
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_CLIENT_AuditLog_date')
    CREATE INDEX IX_CLIENT_AuditLog_date ON APP_AuditLog(date_action);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_CLIENT_UserPages_user')
    CREATE INDEX IX_CLIENT_UserPages_user ON APP_UserPages(user_id);
"""


def _create_client_optiboard_db(dwh_code: str, serveur: str, user: str, password: str, db_name: str = None) -> Dict[str, Any]:
    """
    Cree la base OptiBoard_cltXXX sur le serveur specifie.
    Utilise Windows Auth automatiquement si le serveur est local (., localhost, 127.0.0.1).
    """
    import pyodbc
    db_name = db_name or f"OptiBoard_clt{dwh_code}"

    logger.info(f"[CLIENT-DB] Creation de {db_name} sur {serveur} (local={_is_local_server(serveur)})...")

    # 1. Creer la base si elle n'existe pas
    try:
        if not _check_db_exists(serveur, db_name, user, password):
            conn_master_str = _build_conn_str(serveur, "master", user, password)
            conn_master = pyodbc.connect(conn_master_str, timeout=30)
            conn_master.autocommit = True
            cursor_master = conn_master.cursor()
            cursor_master.execute(f"CREATE DATABASE [{db_name}]")
            cursor_master.close()
            conn_master.close()
            logger.info(f"[CLIENT-DB] Base {db_name} creee sur {serveur}")
        else:
            logger.info(f"[CLIENT-DB] Base {db_name} existe deja sur {serveur}")
    except Exception as e:
        logger.error(f"[CLIENT-DB] Erreur creation base {db_name}: {e}")
        return {"created": False, "db_name": db_name, "error": str(e)}

    # 2. Creer les tables client
    tables_created = 0
    try:
        client_conn_str = _build_conn_str(serveur, db_name, user, password)
        client_conn = pyodbc.connect(client_conn_str, timeout=30, autocommit=True)
        client_cursor = client_conn.cursor()

        for statement in CLIENT_OPTIBOARD_TABLES_SQL.split(';'):
            # Supprimer les lignes de commentaires au debut
            lines = statement.strip().split('\n')
            clean_lines = [l for l in lines if l.strip() and not l.strip().startswith('--')]
            statement = '\n'.join(clean_lines).strip()
            if not statement:
                continue
            try:
                client_cursor.execute(statement)
                if 'CREATE TABLE' in statement.upper():
                    tables_created += 1
            except Exception as e:
                if 'already exists' not in str(e).lower():
                    logger.warning(f"[CLIENT-DB] Table warning: {str(e)[:80]}")

        logger.info(f"[CLIENT-DB] {tables_created} tables creees dans {db_name}")
    except Exception as e:
        logger.error(f"[CLIENT-DB] Erreur creation tables dans {db_name}: {e}")
        return {"created": True, "db_name": db_name, "tables_count": 0, "error": str(e)}

    # 3. Enregistrer dans APP_ClientDB (MASTER)
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM APP_ClientDB WHERE dwh_code = ?", (dwh_code,))
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    "INSERT INTO APP_ClientDB (dwh_code, db_name) VALUES (?, ?)",
                    (dwh_code, db_name)
                )
                logger.info(f"[CLIENT-DB] {dwh_code} enregistre dans APP_ClientDB -> {db_name}")
            else:
                logger.info(f"[CLIENT-DB] {dwh_code} deja present dans APP_ClientDB")
    except Exception as e:
        # APP_ClientDB n'existe peut-etre pas encore
        logger.warning(f"[CLIENT-DB] Impossible d'enregistrer dans APP_ClientDB: {e}")
        # Creer APP_ClientDB et reessayer
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ClientDB' AND xtype='U')
                    CREATE TABLE APP_ClientDB (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        dwh_code VARCHAR(50) UNIQUE NOT NULL,
                        db_name NVARCHAR(100) NOT NULL,
                        db_server NVARCHAR(200) NULL,
                        db_user NVARCHAR(100) NULL,
                        db_password NVARCHAR(200) NULL,
                        actif BIT DEFAULT 1,
                        date_creation DATETIME DEFAULT GETDATE()
                    )
                """)
            with get_db_cursor() as cursor:
                cursor.execute(
                    "INSERT INTO APP_ClientDB (dwh_code, db_name) VALUES (?, ?)",
                    (dwh_code, db_name)
                )
                logger.info(f"[CLIENT-DB] APP_ClientDB creee + {dwh_code} enregistre")
        except Exception as e2:
            logger.error(f"[CLIENT-DB] Echec total APP_ClientDB: {e2}")

    # 4. Migrer les donnees depuis MASTER vers OptiBoard_XXX
    try:
        client_conn.autocommit = False  # Repasser en mode transactionnel
        _migrate_data_to_client(dwh_code, client_conn)
        client_conn.commit()
    except Exception as e:
        logger.warning(f"[CLIENT-DB] Erreur migration donnees: {e}")
        try:
            client_conn.rollback()
        except:
            pass

    try:
        client_cursor.close()
        client_conn.close()
    except:
        pass

    # 5. Vider le cache du ClientConnectionManager
    try:
        from ..database_unified import client_manager
        client_manager.clear_cache(dwh_code)
    except:
        pass

    return {"created": True, "db_name": db_name, "tables_count": tables_created}


def _migrate_data_to_client(dwh_code: str, client_conn):
    """Copie les donnees depuis MASTER vers la base client OptiBoard_XXX"""
    from app.database_unified import get_central_connection
    master_conn = get_central_connection()
    master_cursor = master_conn.cursor()
    client_cursor = client_conn.cursor()

    # Trouver les user_ids lies a ce DWH
    master_cursor.execute(
        "SELECT user_id FROM APP_UserDWH WHERE dwh_code = ?", (dwh_code,)
    )
    user_ids = [row[0] for row in master_cursor.fetchall()]
    placeholders = ','.join(['?' for _ in user_ids]) if user_ids else '0'

    migrated = {}

    # --- APP_UserPages ---
    if user_ids:
        try:
            master_cursor.execute(
                f"SELECT user_id, page_code FROM APP_UserPages WHERE user_id IN ({placeholders})",
                user_ids
            )
            rows = master_cursor.fetchall()
            for row in rows:
                try:
                    client_cursor.execute(
                        "INSERT INTO APP_UserPages (user_id, page_code) VALUES (?, ?)",
                        (row[0], row[1])
                    )
                except:
                    pass
            client_conn.commit()
            migrated['APP_UserPages'] = len(rows)
        except Exception as e:
            logger.debug(f"[MIGRATE] UserPages: {e}")
            client_conn.rollback()

    # --- APP_UserMenus ---
    if user_ids:
        try:
            master_cursor.execute(
                f"SELECT user_id, menu_id, can_view, can_export FROM APP_UserMenus WHERE user_id IN ({placeholders})",
                user_ids
            )
            rows = master_cursor.fetchall()
            for row in rows:
                try:
                    client_cursor.execute(
                        "INSERT INTO APP_UserMenus (user_id, menu_id, can_view, can_export) VALUES (?, ?, ?, ?)",
                        (row[0], row[1], row[2], row[3])
                    )
                except:
                    pass
            client_conn.commit()
            migrated['APP_UserMenus'] = len(rows)
        except Exception as e:
            logger.debug(f"[MIGRATE] UserMenus: {e}")
            client_conn.rollback()

    # --- APP_Menus (toute l'arborescence) ---
    # Strategie: inserer avec parent_id=NULL, puis remappe via self-join sur code.
    # Cela evite les conflits d'ID IDENTITY entre master et client.
    try:
        master_cursor.execute(
            """SELECT m.nom, m.code, m.icon, m.url, p.code AS parent_code,
                      m.ordre, m.type, m.target_id, m.actif, m.roles, m.date_creation
               FROM APP_Menus m
               LEFT JOIN APP_Menus p ON p.id = m.parent_id
               ORDER BY m.id"""
        )
        rows = master_cursor.fetchall()
        # 1) Inserer tous les menus avec parent_id=NULL
        for row in rows:
            try:
                client_cursor.execute(
                    "INSERT INTO APP_Menus (nom, code, icon, url, parent_id, ordre, type, target_id, actif, roles, date_creation) VALUES (?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?)",
                    (row[0], row[1], row[2], row[3], row[5], row[6], row[7], row[8], row[9], row[10])
                )
            except:
                pass
        # 2) Remappe parent_id via code du parent
        for row in rows:
            parent_code = row[4]
            child_code  = row[1]
            if parent_code and child_code:
                try:
                    client_cursor.execute(
                        "UPDATE APP_Menus SET parent_id = (SELECT id FROM APP_Menus WHERE code = ?) WHERE code = ?",
                        (parent_code, child_code)
                    )
                except:
                    pass
        client_conn.commit()
        migrated['APP_Menus'] = len(rows)
    except Exception as e:
        logger.debug(f"[MIGRATE] Menus: {e}")
        client_conn.rollback()

    # --- APP_GridViews (tous) ---
    try:
        master_cursor.execute(
            "SELECT nom, description, query_template, columns_config, parameters, features, actif, date_creation, date_modification FROM APP_GridViews"
        )
        rows = master_cursor.fetchall()
        for row in rows:
            try:
                client_cursor.execute(
                    "INSERT INTO APP_GridViews (nom, description, query_template, columns_config, parameters, features, actif, date_creation, date_modification) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    row
                )
            except:
                pass
        client_conn.commit()
        migrated['APP_GridViews'] = len(rows)
    except Exception as e:
        logger.debug(f"[MIGRATE] GridViews: {e}")
        client_conn.rollback()

    # --- APP_Pivots_V2 (tous) ---
    try:
        master_cursor.execute(
            "SELECT nom, description, data_source_code, pivot_config, columns_config, values_config, filters_config, chart_config, features, created_by, actif, date_creation, date_modification FROM APP_Pivots_V2"
        )
        rows = master_cursor.fetchall()
        for row in rows:
            try:
                client_cursor.execute(
                    "INSERT INTO APP_Pivots_V2 (nom, description, data_source_code, pivot_config, columns_config, values_config, filters_config, chart_config, features, created_by, actif, date_creation, date_modification) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    row
                )
            except:
                pass
        client_conn.commit()
        migrated['APP_Pivots_V2'] = len(rows)
    except Exception as e:
        logger.debug(f"[MIGRATE] Pivots_V2: {e}")
        client_conn.rollback()

    # --- APP_Dashboards (par les utilisateurs du client ou publics) ---
    if user_ids:
        try:
            master_cursor.execute(
                f"SELECT nom, description, config, widgets, is_public, created_by, actif, date_creation, date_modification FROM APP_Dashboards WHERE created_by IN ({placeholders}) OR created_by IS NULL OR is_public = 1",
                user_ids
            )
            rows = master_cursor.fetchall()
            for row in rows:
                try:
                    client_cursor.execute(
                        "INSERT INTO APP_Dashboards (nom, description, config, widgets, is_public, created_by, actif, date_creation, date_modification) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        row
                    )
                except:
                    pass
            client_conn.commit()
            migrated['APP_Dashboards'] = len(rows)
        except Exception as e:
            logger.debug(f"[MIGRATE] Dashboards: {e}")
            client_conn.rollback()

    # --- APP_EmailConfig ---
    try:
        master_cursor.execute(
            "SELECT smtp_server, smtp_port, smtp_username, smtp_password, from_email, from_name, use_ssl, use_tls, actif FROM APP_EmailConfig WHERE dwh_code = ? OR dwh_code IS NULL",
            (dwh_code,)
        )
        rows = master_cursor.fetchall()
        for row in rows:
            try:
                client_cursor.execute(
                    "INSERT INTO APP_EmailConfig (smtp_server, smtp_port, smtp_username, smtp_password, from_email, from_name, use_ssl, use_tls, actif) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    row
                )
            except:
                pass
        client_conn.commit()
        migrated['APP_EmailConfig'] = len(rows)
    except Exception as e:
        logger.debug(f"[MIGRATE] EmailConfig: {e}")
        client_conn.rollback()

    # --- APP_Settings ---
    try:
        master_cursor.execute(
            "SELECT setting_key, setting_value, setting_type, description FROM APP_Settings WHERE dwh_code = ? OR dwh_code IS NULL",
            (dwh_code,)
        )
        rows = master_cursor.fetchall()
        for row in rows:
            try:
                client_cursor.execute(
                    "INSERT INTO APP_Settings (setting_key, setting_value, setting_type, description) VALUES (?, ?, ?, ?)",
                    row
                )
            except:
                pass
        client_conn.commit()
        migrated['APP_Settings'] = len(rows)
    except Exception as e:
        logger.debug(f"[MIGRATE] Settings: {e}")
        client_conn.rollback()

    # --- APP_ReportSchedules ---
    try:
        master_cursor.execute(
            "SELECT nom, description, report_type, report_id, export_format, frequency, schedule_time, schedule_day, recipients, cc_recipients, filters, is_active, last_run, next_run, created_by, created_at, updated_at FROM APP_ReportSchedules"
        )
        rows = master_cursor.fetchall()
        for row in rows:
            try:
                client_cursor.execute(
                    "INSERT INTO APP_ReportSchedules (nom, description, report_type, report_id, export_format, frequency, schedule_time, schedule_day, recipients, cc_recipients, filters, is_active, last_run, next_run, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    row
                )
            except:
                pass
        client_conn.commit()
        migrated['APP_ReportSchedules'] = len(rows)
    except Exception as e:
        logger.debug(f"[MIGRATE] ReportSchedules: {e}")
        client_conn.rollback()

    master_cursor.close()
    master_conn.close()
    logger.info(f"[CLIENT-DB] Migration terminee pour {dwh_code}: {migrated}")


@router.post("/dwh-admin/init-database")
async def dwh_admin_init_database(request: Dict[str, Any] = Body(...)):
    """Cree la base DWH et initialise les 35 tables si la base n'existe pas"""
    try:
        serveur = request.get('serveur')
        base = request.get('base')
        user = request.get('user')
        password = request.get('password')

        if not all([serveur, base, user, password]):
            return {"success": False, "message": "Parametres de connexion incomplets"}

        result = _create_dwh_database(serveur, base, user, password)
        return {"success": True, **result}
    except Exception as e:
        logger.error(f"Erreur init database: {e}")
        return {"success": False, "message": str(e)}


def _run_migrate_all_clients() -> Dict[str, Any]:
    """Fonction synchrone de migration - executee dans un thread separe"""
    # Lire tous les DWH actifs
    dwh_list = execute_query(
        "SELECT code, nom, serveur_dwh, user_dwh, password_dwh, serveur_optiboard, base_optiboard, user_optiboard, password_optiboard FROM APP_DWH WHERE actif = 1 ORDER BY nom",
        use_cache=False
    )

    if not dwh_list:
        return {"success": True, "message": "Aucun DWH actif trouve", "results": []}

    # Verifier quels clients ont deja une base OptiBoard_XXX
    existing_clients = set()
    try:
        rows = execute_query(
            "SELECT dwh_code FROM APP_ClientDB WHERE actif = 1",
            use_cache=False
        )
        existing_clients = {r['dwh_code'] for r in rows}
    except Exception:
        pass

    results = []
    for dwh in dwh_list:
        code = dwh['code']
        if code in existing_clients:
            results.append({
                "dwh_code": code,
                "nom": dwh['nom'],
                "status": "exists",
                "message": f"OptiBoard_{code} deja configure"
            })
            continue

        serveur  = dwh.get('serveur_optiboard') or dwh.get('serveur_dwh')
        user_dwh = dwh.get('user_optiboard')    or dwh.get('user_dwh')
        pwd_dwh  = dwh.get('password_optiboard') or dwh.get('password_dwh')
        opti_db  = dwh.get('base_optiboard')     or f"OptiBoard_clt{code}"

        if not all([serveur, user_dwh, pwd_dwh]):
            results.append({
                "dwh_code": code,
                "nom": dwh['nom'],
                "status": "skipped",
                "message": "Parametres de connexion incomplets"
            })
            continue

        try:
            result = _create_client_optiboard_db(code, serveur, user_dwh, pwd_dwh, db_name=opti_db)
            results.append({
                "dwh_code": code,
                "nom": dwh['nom'],
                "status": "created" if result.get('created') else "error",
                "db_name": result.get('db_name'),
                "tables_count": result.get('tables_count', 0),
                "message": f"OptiBoard_{code} cree avec {result.get('tables_count', 0)} tables"
            })
        except Exception as e:
            results.append({
                "dwh_code": code,
                "nom": dwh['nom'],
                "status": "error",
                "message": str(e)
            })

    created_count = sum(1 for r in results if r['status'] == 'created')
    existing_count = sum(1 for r in results if r['status'] == 'exists')

    return {
        "success": True,
        "message": f"{created_count} base(s) creee(s), {existing_count} deja existante(s)",
        "total": len(dwh_list),
        "created": created_count,
        "existing": existing_count,
        "results": results
    }


@router.post("/dwh-admin/migrate-all")
async def dwh_admin_migrate_all_clients():
    """
    Cree les bases OptiBoard_XXX pour tous les clients existants.
    Pour chaque DWH actif sans entree dans APP_ClientDB, cree la base + tables + migration donnees.
    Execute dans un thread separe pour ne pas bloquer l'event loop.
    """
    import asyncio
    try:
        result = await asyncio.to_thread(_run_migrate_all_clients)
        return result
    except Exception as e:
        logger.error(f"Erreur migration globale: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dwh-admin/test-connection")
async def dwh_admin_test_connection_direct(request: Dict[str, Any] = Body(...)):
    """Teste une connexion DWH avec les parametres fournis (sans code DWH pre-existant).
    Si la base n'existe pas, retourne db_exists=false avec un message informatif."""
    try:
        import pyodbc
        serveur = request.get('serveur')
        base = request.get('base')
        user = request.get('user')
        password = request.get('password')

        if not all([serveur, base, user, password]):
            return {"success": False, "message": "Parametres de connexion incomplets"}

        # D'abord verifier si la base existe
        try:
            db_exists = _check_db_exists(serveur, base, user, password)
        except Exception as conn_err:
            # Si meme la connexion a master echoue, le serveur est inaccessible
            return {"success": False, "message": f"Impossible de se connecter au serveur: {conn_err}", "db_exists": False}

        if not db_exists:
            return {
                "success": True,
                "db_exists": False,
                "message": f"Le serveur est accessible mais la base '{base}' n'existe pas. Elle sera creee automatiquement lors de l'enregistrement."
            }

        # La base existe, tester la connexion complete
        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={serveur};"
            f"DATABASE={base};"
            f"UID={user};"
            f"PWD={password};"
            "TrustServerCertificate=yes;"
        )
        conn = pyodbc.connect(conn_str, timeout=10)
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION")
        version = cursor.fetchone()[0].split('\n')[0]
        cursor.close()
        conn.close()
        return {"success": True, "db_exists": True, "message": f"Connexion OK: {version}"}
    except Exception as e:
        logger.error(f"Erreur test connexion DWH: {e}")
        return {"success": False, "message": str(e)}


@router.post("/dwh-admin/{code}/test")
async def dwh_admin_test_connection(code: str):
    """Teste la connexion a un DWH"""
    try:
        conn = dwh_manager.get_dwh_connection(code)
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION")
        version = cursor.fetchone()[0].split('\n')[0]
        cursor.close()
        conn.close()
        return {"success": True, "message": f"Connexion OK: {version}"}
    except Exception as e:
        logger.error(f"Erreur test DWH: {e}")
        return {"success": False, "message": str(e)}


# ============================================================
# Gestion des bases client OptiBoard_XXX
# ============================================================

# Tables synchronisables depuis MASTER vers les bases client
SYNCABLE_TABLES_CONFIG = {
    'APP_Menus': {
        'select': 'SELECT nom, code, icon, url, parent_id, ordre, type, target_id, actif, is_custom, roles, date_creation FROM APP_Menus',
        'insert': 'INSERT INTO APP_Menus (nom, code, icon, url, parent_id, ordre, type, target_id, actif, is_custom, roles, date_creation) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
        'filter': None
    },
    'APP_GridViews': {
        'select': 'SELECT nom, code, description, query_template, columns_config, parameters, features, is_custom, actif, date_creation, date_modification FROM APP_GridViews',
        'insert': 'INSERT INTO APP_GridViews (nom, code, description, query_template, columns_config, parameters, features, is_custom, actif, date_creation, date_modification) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
        'filter': None
    },
    'APP_Pivots_V2': {
        'select': 'SELECT nom, code, description, data_source_code, columns_config, values_config, filters_config, is_custom, created_by FROM APP_Pivots_V2',
        'insert': 'INSERT INTO APP_Pivots_V2 (nom, code, description, data_source_code, columns_config, values_config, filters_config, is_custom, created_by) VALUES (?,?,?,?,?,?,?,?,?)',
        'filter': None
    },
    'APP_Dashboards': {
        'select': 'SELECT nom, code, description, config, widgets, is_public, is_custom, created_by, actif, date_creation, date_modification FROM APP_Dashboards',
        'insert': 'INSERT INTO APP_Dashboards (nom, code, description, config, widgets, is_public, is_custom, created_by, actif, date_creation, date_modification) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
        'filter': None
    },
    'APP_DataSources': {
        'select': 'SELECT nom, code, type, query_template, parameters, description, is_custom, date_creation FROM APP_DataSources',
        'insert': 'INSERT INTO APP_DataSources (nom, code, type, query_template, parameters, description, is_custom, date_creation) VALUES (?,?,?,?,?,?,?,?)',
        'filter': None
    },
    'APP_EmailConfig': {
        'select': "SELECT smtp_server, smtp_port, smtp_username, smtp_password, from_email, from_name, use_ssl, use_tls, actif FROM APP_EmailConfig WHERE dwh_code = ? OR dwh_code IS NULL",
        'insert': 'INSERT INTO APP_EmailConfig (smtp_server, smtp_port, smtp_username, smtp_password, from_email, from_name, use_ssl, use_tls, actif) VALUES (?,?,?,?,?,?,?,?,?)',
        'filter': 'dwh_code'
    },
    'APP_Settings': {
        'select': "SELECT setting_key, setting_value, setting_type, description FROM APP_Settings WHERE dwh_code = ? OR dwh_code IS NULL",
        'insert': 'INSERT INTO APP_Settings (setting_key, setting_value, setting_type, description) VALUES (?,?,?,?)',
        'filter': 'dwh_code'
    },
    'APP_ReportSchedules': {
        'select': 'SELECT nom, description, report_type, report_id, export_format, frequency, schedule_time, schedule_day, recipients, cc_recipients, filters, is_active, last_run, next_run, created_by, created_at, updated_at FROM APP_ReportSchedules',
        'insert': 'INSERT INTO APP_ReportSchedules (nom, description, report_type, report_id, export_format, frequency, schedule_time, schedule_day, recipients, cc_recipients, filters, is_active, last_run, next_run, created_by, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
        'filter': None
    },
    'APP_UserPages': {
        'select': 'SELECT user_id, page_code FROM APP_UserPages WHERE user_id IN ({user_ids})',
        'insert': 'INSERT INTO APP_UserPages (user_id, page_code) VALUES (?,?)',
        'filter': 'user_ids'
    },
    'APP_UserMenus': {
        'select': 'SELECT user_id, menu_id, can_view, can_export FROM APP_UserMenus WHERE user_id IN ({user_ids})',
        'insert': 'INSERT INTO APP_UserMenus (user_id, menu_id, can_view, can_export) VALUES (?,?,?,?)',
        'filter': 'user_ids'
    },
}

EXPECTED_CLIENT_TABLES = [
    "APP_UserPages", "APP_UserMenus", "APP_Dashboards", "APP_DataSources",
    "APP_GridViews", "APP_GridView_User_Prefs", "APP_Pivots", "APP_Pivots_V2",
    "APP_Pivot_User_Prefs", "APP_Menus", "APP_EmailConfig", "APP_Settings",
    "APP_ReportSchedules", "APP_ReportHistory", "APP_AuditLog"
]


def _list_client_databases() -> Dict[str, Any]:
    """Liste toutes les bases client OptiBoard_XXX avec statut (sync)"""
    import pyodbc

    dwh_list = execute_query(
        """SELECT d.code, d.nom, d.serveur_dwh, d.user_dwh, d.password_dwh,
                  c.db_name AS client_db_name, c.actif AS client_actif
           FROM APP_DWH d
           LEFT JOIN APP_ClientDB c ON d.code = c.dwh_code
           WHERE d.actif = 1 ORDER BY d.nom""",
        use_cache=False
    )

    results = []
    healthy = 0
    unhealthy = 0
    pending = 0

    for dwh in dwh_list:
        db_name = dwh.get('client_db_name') or f"OptiBoard_{dwh['code']}"
        has_client_db = dwh.get('client_db_name') is not None

        info = {
            "dwh_code": dwh['code'],
            "dwh_nom": dwh['nom'],
            "db_name": db_name,
            "server": dwh['serveur_dwh'] or '',
            "has_client_db": has_client_db,
            "connection_status": "not_configured",
            "tables_count": 0,
            "total_rows": 0,
            "size_mb": 0,
            "tables": [],
            "error": None
        }

        if not has_client_db:
            pending += 1
            results.append(info)
            continue

        try:
            conn_str = _build_conn_str(
                dwh['serveur_dwh'] or '', db_name,
                dwh['user_dwh'] or '', dwh['password_dwh'] or ''
            )
            conn = pyodbc.connect(conn_str, timeout=5)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT t.name, p.rows
                FROM sys.tables t
                INNER JOIN sys.partitions p ON t.object_id = p.object_id AND p.index_id IN (0,1)
                WHERE t.is_ms_shipped = 0 ORDER BY t.name
            """)
            tables = [{"name": r[0], "rows": r[1]} for r in cursor.fetchall()]

            cursor.execute("SELECT SUM(CAST(size AS BIGINT))*8/1024.0 FROM sys.database_files")
            size = cursor.fetchone()[0] or 0

            cursor.close()
            conn.close()

            info["connection_status"] = "ok"
            info["tables"] = tables
            info["tables_count"] = len(tables)
            info["total_rows"] = sum(t["rows"] for t in tables)
            info["size_mb"] = round(float(size), 2)
            healthy += 1
        except Exception as e:
            info["connection_status"] = "error"
            info["error"] = str(e)[:200]
            unhealthy += 1

        results.append(info)

    return {
        "success": True,
        "total": len(results),
        "healthy": healthy,
        "unhealthy": unhealthy,
        "pending_migration": pending,
        "data": results
    }


def _get_client_db_status(code: str) -> Dict[str, Any]:
    """Detail du statut d'une base client (sync)"""
    import pyodbc

    dwh = execute_query(
        "SELECT code, nom, serveur_dwh, user_dwh, password_dwh FROM APP_DWH WHERE code = ?",
        (code,), use_cache=False
    )
    if not dwh:
        return {"success": False, "message": "DWH non trouve"}
    dwh = dwh[0]

    db_name = f"OptiBoard_{code}"
    client_db = execute_query(
        "SELECT db_name FROM APP_ClientDB WHERE dwh_code = ?", (code,), use_cache=False
    )
    if client_db:
        db_name = client_db[0]["db_name"]

    conn_str = _build_conn_str(
        dwh['serveur_dwh'] or '', db_name,
        dwh['user_dwh'] or '', dwh['password_dwh'] or ''
    )
    conn = pyodbc.connect(conn_str, timeout=10)
    cursor = conn.cursor()

    # Tables avec row counts et dates
    cursor.execute("""
        SELECT t.name, p.rows, t.create_date, t.modify_date
        FROM sys.tables t
        INNER JOIN sys.partitions p ON t.object_id = p.object_id AND p.index_id IN (0,1)
        WHERE t.is_ms_shipped = 0 ORDER BY t.name
    """)
    tables = [{
        "name": r[0], "rows": r[1],
        "created": str(r[2])[:19] if r[2] else None,
        "modified": str(r[3])[:19] if r[3] else None
    } for r in cursor.fetchall()]

    # Tailles
    cursor.execute("""
        SELECT type_desc, SUM(CAST(size AS BIGINT))*8/1024.0
        FROM sys.database_files GROUP BY type_desc
    """)
    sizes = {r[0]: round(float(r[1]), 2) for r in cursor.fetchall()}

    # Version
    cursor.execute("SELECT @@VERSION")
    version = cursor.fetchone()[0].split('\n')[0]

    cursor.close()
    conn.close()

    existing_names = {t["name"] for t in tables}
    missing_tables = [t for t in EXPECTED_CLIENT_TABLES if t not in existing_names]

    return {
        "success": True,
        "dwh_code": code,
        "dwh_nom": dwh['nom'],
        "db_name": db_name,
        "server_version": version,
        "tables_count": len(tables),
        "total_rows": sum(t["rows"] for t in tables),
        "size_data_mb": sizes.get("ROWS", 0),
        "size_log_mb": sizes.get("LOG", 0),
        "tables": tables,
        "expected_tables": EXPECTED_CLIENT_TABLES,
        "missing_tables": missing_tables,
        "all_tables_present": len(missing_tables) == 0
    }


@router.get("/dwh-admin/{code}/client-db-status")
async def dwh_admin_client_db_status(code: str):
    """Detail du statut d'une base client OptiBoard_XXX."""
    import asyncio
    try:
        result = await asyncio.to_thread(_get_client_db_status, code)
        return result
    except Exception as e:
        logger.error(f"Erreur statut base client {code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _sync_data_to_client(code: str, tables_filter: Optional[List[str]], mode: str) -> Dict[str, Any]:
    """Synchronise les donnees MASTER vers OptiBoard_XXX (sync)"""
    import pyodbc
    from app.database_unified import get_central_connection

    dwh = execute_query(
        "SELECT code, nom, serveur_dwh, user_dwh, password_dwh FROM APP_DWH WHERE code = ?",
        (code,), use_cache=False
    )
    if not dwh:
        return {"success": False, "message": "DWH non trouve"}
    dwh = dwh[0]

    db_name = f"OptiBoard_{code}"
    client_db = execute_query(
        "SELECT db_name FROM APP_ClientDB WHERE dwh_code = ?", (code,), use_cache=False
    )
    if client_db:
        db_name = client_db[0]["db_name"]

    conn_str = _build_conn_str(
        dwh['serveur_dwh'] or '', db_name,
        dwh['user_dwh'] or '', dwh['password_dwh'] or ''
    )
    client_conn = pyodbc.connect(conn_str, timeout=30)
    master_conn = get_central_connection()

    master_cursor = master_conn.cursor()
    client_cursor = client_conn.cursor()

    # User IDs lies a ce DWH
    master_cursor.execute("SELECT user_id FROM APP_UserDWH WHERE dwh_code = ?", (code,))
    user_ids = [row[0] for row in master_cursor.fetchall()]
    user_placeholders = ','.join(['?' for _ in user_ids]) if user_ids else '0'

    # Tables a synchroniser
    target_tables = tables_filter if tables_filter else list(SYNCABLE_TABLES_CONFIG.keys())

    details = {}
    for table_name in target_tables:
        if table_name not in SYNCABLE_TABLES_CONFIG:
            details[table_name] = {"status": "skipped", "message": "Table non synchronisable"}
            continue

        config = SYNCABLE_TABLES_CONFIG[table_name]

        # Skip user-filtered tables si pas d'utilisateurs
        if config['filter'] == 'user_ids' and not user_ids:
            details[table_name] = {"status": "ok", "rows_synced": 0, "message": "Aucun utilisateur lie"}
            continue

        try:
            # Mode replace: supprimer puis re-inserer
            if mode == 'replace':
                client_cursor.execute(f"DELETE FROM [{table_name}]")
                client_conn.commit()

            # Lire depuis MASTER
            select_sql = config['select']
            params = None
            if config['filter'] == 'dwh_code':
                params = (code,)
            elif config['filter'] == 'user_ids':
                select_sql = select_sql.replace('{user_ids}', user_placeholders)
                params = user_ids

            if params:
                master_cursor.execute(select_sql, params)
            else:
                master_cursor.execute(select_sql)
            rows = master_cursor.fetchall()

            # Inserer dans client
            count = 0
            for row in rows:
                try:
                    client_cursor.execute(config['insert'], row)
                    count += 1
                except Exception:
                    pass
            client_conn.commit()
            details[table_name] = {"status": "ok", "rows_synced": count}

        except Exception as e:
            details[table_name] = {"status": "error", "error": str(e)[:200]}
            try:
                client_conn.rollback()
            except Exception:
                pass

    master_cursor.close()
    master_conn.close()
    client_cursor.close()
    client_conn.close()

    # Clear cache
    try:
        from app.database_unified import client_manager
        client_manager.clear_cache(code)
    except Exception:
        pass

    synced = sum(1 for r in details.values() if r.get("status") == "ok")
    return {
        "success": True,
        "dwh_code": code,
        "db_name": db_name,
        "tables_synced": synced,
        "tables_failed": len(details) - synced,
        "details": details
    }


@router.post("/dwh-admin/{code}/sync-data")
async def dwh_admin_sync_data(code: str, request: Dict[str, Any] = Body(...)):
    """Synchronise les donnees partagees MASTER vers OptiBoard_{code}."""
    import asyncio
    tables = request.get('tables', None)
    mode = request.get('mode', 'replace')
    try:
        result = await asyncio.to_thread(_sync_data_to_client, code, tables, mode)
        return result
    except Exception as e:
        logger.error(f"Erreur sync data {code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _reset_client_db(code: str, keep_user_data: bool) -> Dict[str, Any]:
    """Reinitialise une base client (sync)"""
    import pyodbc

    dwh = execute_query(
        "SELECT code, nom, serveur_dwh, user_dwh, password_dwh FROM APP_DWH WHERE code = ?",
        (code,), use_cache=False
    )
    if not dwh:
        return {"success": False, "message": "DWH non trouve"}
    dwh = dwh[0]

    db_name = f"OptiBoard_{code}"
    client_db = execute_query(
        "SELECT db_name FROM APP_ClientDB WHERE dwh_code = ?", (code,), use_cache=False
    )
    if client_db:
        db_name = client_db[0]["db_name"]

    conn_str = _build_conn_str(
        dwh['serveur_dwh'] or '', db_name,
        dwh['user_dwh'] or '', dwh['password_dwh'] or ''
    )
    conn = pyodbc.connect(conn_str, timeout=30, autocommit=True)
    cursor = conn.cursor()

    # Drop tables dans le bon ordre (FK en premier)
    tables_to_drop = [
        "APP_ReportHistory", "APP_AuditLog",
        "APP_Pivot_User_Prefs", "APP_GridView_User_Prefs",
        "APP_Pivots_V2", "APP_Pivots", "APP_GridViews",
        "APP_Dashboards", "APP_DataSources", "APP_Menus",
        "APP_EmailConfig", "APP_Settings",
        "APP_ReportSchedules"
    ]
    if not keep_user_data:
        tables_to_drop += ["APP_UserPages", "APP_UserMenus"]

    dropped = 0
    for table in tables_to_drop:
        try:
            cursor.execute(f"IF OBJECT_ID('{table}', 'U') IS NOT NULL DROP TABLE [{table}]")
            dropped += 1
        except Exception:
            pass

    # Recreer les tables
    tables_created = 0
    for statement in CLIENT_OPTIBOARD_TABLES_SQL.split(';'):
        lines = statement.strip().split('\n')
        clean_lines = [l for l in lines if l.strip() and not l.strip().startswith('--')]
        statement = '\n'.join(clean_lines).strip()
        if not statement:
            continue
        try:
            cursor.execute(statement)
            if 'CREATE TABLE' in statement.upper():
                tables_created += 1
        except Exception:
            pass

    # Re-migrer les donnees depuis MASTER
    conn.autocommit = False
    try:
        _migrate_data_to_client(code, conn)
    except Exception:
        pass

    cursor.close()
    conn.close()

    # Clear cache
    try:
        from app.database_unified import client_manager
        client_manager.clear_cache(code)
    except Exception:
        pass

    return {
        "success": True,
        "message": f"Base {db_name} reinitialisee",
        "tables_dropped": dropped,
        "tables_created": tables_created
    }


@router.post("/dwh-admin/{code}/reset-client-db")
async def dwh_admin_reset_client_db(code: str, request: Dict[str, Any] = Body(...)):
    """Reinitialise la base client OptiBoard_{code}. Requiert confirm=true."""
    if not request.get('confirm', False):
        raise HTTPException(status_code=400, detail="Confirmation requise (confirm=true)")
    import asyncio
    keep_user_data = request.get('keep_user_data', True)
    try:
        result = await asyncio.to_thread(_reset_client_db, code, keep_user_data)
        return result
    except Exception as e:
        logger.error(f"Erreur reset base client {code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dwh-admin/{code}/create-client-db")
async def dwh_admin_create_single_client_db(code: str):
    """Cree la base OptiBoard_{code} pour un client qui n'en a pas encore."""
    import asyncio
    try:
        dwh = execute_query(
            "SELECT code, nom, serveur_dwh, user_dwh, password_dwh FROM APP_DWH WHERE code = ?",
            (code,), use_cache=False
        )
        if not dwh:
            raise HTTPException(status_code=404, detail="DWH non trouve")
        dwh = dwh[0]

        # Verifier si deja configure
        existing = execute_query(
            "SELECT dwh_code FROM APP_ClientDB WHERE dwh_code = ?", (code,), use_cache=False
        )
        if existing:
            return {"success": True, "message": f"OptiBoard_{code} existe deja", "already_exists": True}

        result = await asyncio.to_thread(
            _create_client_optiboard_db,
            code, dwh['serveur_dwh'], dwh['user_dwh'], dwh['password_dwh']
        )
        return {"success": True, **result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur creation base client {code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/{agent_id}/sync-result")
async def agent_sync_result(agent_id: str, result: SyncResultRequest):
    """Rapporte le resultat d'une synchronisation"""
    try:
        with get_db_cursor() as cursor:
            # Inserer le log
            cursor.execute(
                """
                INSERT INTO APP_ETL_Agent_Sync_Log (
                    agent_id, table_name, societe_code,
                    started_at, completed_at, duration_seconds,
                    status, rows_extracted, rows_inserted, rows_updated,
                    rows_failed, error_message,
                    sync_timestamp_start, sync_timestamp_end
                ) VALUES (
                    ?, ?, ?,
                    DATEADD(SECOND, -?, GETDATE()), GETDATE(), ?,
                    ?, ?, ?, ?,
                    ?, ?,
                    ?, ?
                )
                """,
                (
                    agent_id, result.table_name, result.societe_code,
                    result.duration_seconds, result.duration_seconds,
                    'success' if result.success else 'error',
                    result.rows_extracted, result.rows_inserted, result.rows_updated,
                    result.rows_failed, result.error_message,
                    result.sync_timestamp_start, result.sync_timestamp_end
                )
            )
            cursor.commit()

        return {"success": True}

    except Exception as e:
        logger.error(f"Erreur sync result: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Routes Configuration Tables ETL Globales
# ============================================================

@router.get("/etl/config/tables")
async def list_etl_tables():
    """Liste toutes les tables ETL configurees (stockage SQL)"""
    try:
        from etl.config.table_config import get_tables
        tables = get_tables()
        return {"success": True, "tables": tables, "count": len(tables)}
    except Exception as e:
        logger.error(f"Erreur liste tables ETL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/etl/config/tables")
async def create_etl_table(request: Request):
    """Cree une nouvelle table ETL"""
    try:
        data = await request.json()
        from etl.config.table_config import add_table, get_table_by_name, _ensure_table_exists

        if not data.get('name'):
            raise HTTPException(status_code=400, detail="Le nom de la table est requis")

        # S'assurer que le schema est a jour (migration colonnes manquantes)
        _ensure_table_exists()

        # Verifier si existe deja
        if get_table_by_name(data['name']):
            raise HTTPException(status_code=409, detail=f"La table '{data['name']}' existe deja")

        if add_table(data):
            return {"success": True, "message": f"Table '{data['name']}' creee avec succes"}
        else:
            raise HTTPException(status_code=500, detail=f"Erreur lors de la creation de la table '{data.get('name')}'")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur creation table ETL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/etl/config/tables/{table_name}")
async def get_etl_table(table_name: str):
    """Recupere une table ETL par son nom"""
    try:
        from etl.config.table_config import get_table_by_name
        table = get_table_by_name(table_name)

        if not table:
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' non trouvee")

        return {"success": True, "table": table}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur recuperation table ETL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/etl/config/tables/{table_name}")
async def update_etl_table(table_name: str, request: Request):
    """Met a jour une table ETL"""
    try:
        data = await request.json()
        from etl.config.table_config import update_table, get_table_by_name

        if not get_table_by_name(table_name):
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' non trouvee")

        if update_table(table_name, data):
            return {"success": True, "message": f"Table '{table_name}' mise a jour avec succes"}
        else:
            raise HTTPException(status_code=500, detail="Erreur lors de la mise a jour")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur mise a jour table ETL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/etl/config/tables/{table_name}")
async def delete_etl_table(table_name: str):
    """Supprime une table ETL"""
    try:
        from etl.config.table_config import delete_table
        from urllib.parse import unquote

        # Decoder le nom de table (au cas ou il serait encode en URL)
        decoded_name = unquote(table_name)
        logger.info(f"Requete suppression table - brut: '{table_name}', decode: '{decoded_name}'")

        if delete_table(decoded_name):
            return {"success": True, "message": f"Table '{decoded_name}' supprimee avec succes"}
        else:
            raise HTTPException(status_code=404, detail=f"Table '{decoded_name}' non trouvee")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur suppression table ETL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/etl/config/tables")
async def delete_all_etl_tables():
    """Supprime toutes les tables ETL (SQL et YAML)"""
    try:
        from etl.config.table_config import invalidate_cache, clear_yaml_tables, get_tables
        from app.database_unified import get_central_connection as get_connection

        logger.info("Suppression de toutes les tables ETL...")

        # Compter les tables actuellement visibles (SQL + YAML)
        current_tables = get_tables()
        total_visible = len(current_tables)
        logger.info(f"Tables actuellement visibles: {total_visible}")

        # 1. D'abord vider le fichier YAML (source principale des tables)
        yaml_cleared = False
        try:
            clear_yaml_tables()
            yaml_cleared = True
            logger.info("Fichier YAML vide avec succes")
        except Exception as yaml_err:
            logger.error(f"Erreur vidage YAML: {yaml_err}")

        # 2. Ensuite supprimer en SQL
        conn = get_connection()
        cursor = conn.cursor()

        # Compter avant suppression SQL
        cursor.execute("SELECT COUNT(*) FROM ETL_Tables_Config")
        count_config = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM APP_ETL_Agent_Tables")
        count_agents = cursor.fetchone()[0]

        logger.info(f"Tables SQL a supprimer: {count_config} config, {count_agents} agent_tables")

        # Supprimer toutes les tables SQL
        cursor.execute("DELETE FROM ETL_Tables_Config")
        cursor.execute("DELETE FROM APP_ETL_Agent_Tables")

        conn.commit()
        cursor.close()
        conn.close()

        # 3. Invalider le cache pour forcer le rechargement
        invalidate_cache()
        logger.info("Cache invalide")

        logger.info(f"Suppression terminee: {total_visible} tables (SQL: {count_config}, YAML vide: {yaml_cleared})")

        return {
            "success": True,
            "message": f"Toutes les tables ETL supprimees",
            "deleted_total": total_visible,
            "deleted_config": count_config,
            "deleted_agent_tables": count_agents,
            "yaml_cleared": yaml_cleared
        }

    except Exception as e:
        logger.error(f"Erreur suppression toutes tables ETL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/etl/config/import-from-optiboard")
async def import_etl_tables_from_optiboard():
    """
    Importe les tables ETL depuis la table SyncQuery de OptiBoard.
    Connexion: localhost, sa, SQL@2019, OptiBoard
    """
    import pyodbc

    try:
        from etl.config.table_config import add_table, invalidate_cache

        # Connexion a OptiBoard
        conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=localhost;"
            "DATABASE=OptiBoard;"
            "UID=sa;"
            "PWD=SQL@2019;"
            "TrustServerCertificate=yes;"
        )

        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        # Requete pour recuperer les tables a synchroniser
        query = """
            SELECT [Id], [Caption], [Order], [DestTable], [Query1], [PrimaryKey1], [Colonne incrementale]
            FROM [OptiBoard].[dbo].[SyncQuery]
            WHERE ISNULL([Query1], '') <> ''
            ORDER BY [Order]
        """

        cursor.execute(query)
        rows = cursor.fetchall()

        imported = 0
        skipped = 0
        errors = []

        for row in rows:
            try:
                id_val, caption, order_val, dest_table, query1, primary_key, incremental_col = row

                # Construire la config de la table
                table_config = {
                    'name': caption or f"Table_{id_val}",
                    'source_query': query1,
                    'target_table': dest_table or caption,
                    'primary_key': [pk.strip() for pk in (primary_key or '').split(',') if pk.strip()],
                    'sync_type': 'incremental' if incremental_col else 'full',
                    'timestamp_column': incremental_col or '',
                    'priority': 'normal',
                    'enabled': True,
                    'sort_order': order_val or 0,
                    'batch_size': 10000
                }

                if add_table(table_config):
                    imported += 1
                    logger.info(f"Table importee: {caption}")
                else:
                    skipped += 1
                    logger.debug(f"Table ignoree (deja existante): {caption}")

            except Exception as e:
                errors.append(f"{caption}: {str(e)}")
                logger.error(f"Erreur import table {caption}: {e}")

        cursor.close()
        conn.close()

        # Invalider le cache
        invalidate_cache()

        return {
            "success": True,
            "message": f"Import termine: {imported} tables importees, {skipped} ignorees",
            "imported": imported,
            "skipped": skipped,
            "total": len(rows),
            "errors": errors if errors else None
        }

    except pyodbc.Error as e:
        logger.error(f"Erreur connexion OptiBoard: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur connexion OptiBoard: {str(e)}")
    except Exception as e:
        logger.error(f"Erreur import depuis OptiBoard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/etl/config/tables/{table_name}/toggle")
async def toggle_etl_table(table_name: str):
    """Active/Desactive une table ETL"""
    try:
        from etl.config.table_config import toggle_table

        new_state = toggle_table(table_name)

        if new_state is None:
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' non trouvee")

        return {
            "success": True,
            "enabled": new_state,
            "message": f"Table '{table_name}' {'activee' if new_state else 'desactivee'}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur toggle table ETL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/etl/config/global")
async def get_etl_global_config():
    """Recupere la configuration globale ETL"""
    try:
        from etl.config.table_config import get_global_config
        config = get_global_config()
        return {"success": True, "config": config}
    except Exception as e:
        logger.error(f"Erreur config globale ETL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/etl/config/global")
async def update_etl_global_config(request: Request):
    """Met a jour la configuration globale ETL"""
    try:
        data = await request.json()
        from etl.config.table_config import update_global_config
        update_global_config(data)
        return {"success": True, "message": "Configuration globale mise a jour"}
    except Exception as e:
        logger.error(f"Erreur mise a jour config globale ETL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/etl/config/migrate")
async def migrate_etl_config():
    """Migre la configuration ETL du fichier YAML vers SQL"""
    try:
        from etl.config.table_config import migrate_from_yaml
        result = migrate_from_yaml()

        if result.get('success'):
            return {
                "success": True,
                "message": f"Migration terminee: {result['migrated']} tables migrees, {result['skipped']} ignorees",
                "migrated": result['migrated'],
                "skipped": result['skipped'],
                "total": result['total']
            }
        else:
            raise HTTPException(status_code=400, detail=result.get('error', 'Erreur inconnue'))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur migration ETL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Telechargement Package Agent
# ============================================================

@router.get("/admin/etl/agents/download/package")
async def download_agent_package():
    """Telecharge le package d'installation de l'agent ETL"""
    import zipfile
    import io
    from fastapi.responses import StreamingResponse
    from pathlib import Path

    try:
        # Chemin vers le dossier agent-etl
        agent_dir = Path(__file__).parent.parent.parent.parent / "agent-etl"

        if not agent_dir.exists():
            raise HTTPException(status_code=404, detail="Package agent non trouve")

        # Fichiers a inclure
        files_to_include = [
            "agent.py",
            "api_client.py",
            "config.py",
            "sync_engine.py",
            "service_windows.py",
            "requirements.txt",
            ".env.example",
            "README.md",
        ]

        # Creer le ZIP en memoire
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for filename in files_to_include:
                filepath = agent_dir / filename
                if filepath.exists():
                    zipf.write(filepath, f"ETLAgent/{filename}")

            # Ajouter le dossier deploy
            deploy_dir = agent_dir / "deploy"
            if deploy_dir.exists():
                for file in deploy_dir.iterdir():
                    if file.is_file():
                        zipf.write(file, f"ETLAgent/deploy/{file.name}")

        zip_buffer.seek(0)

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": "attachment; filename=ETLAgent.zip"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur telechargement package: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Routes Detection des Suppressions
# ============================================================

class PushDeletionsRequest(BaseModel):
    """Requete de detection des suppressions"""
    table_name: str
    target_table: str
    societe_code: str
    primary_key: List[str]
    source_ids: List[Any]
    source_count: int


@router.post("/agents/{agent_id}/push-deletions")
async def agent_push_deletions(agent_id: str, req: PushDeletionsRequest):
    """
    Detecte et supprime les lignes orphelines cote destination.
    Compare les IDs source recus avec ceux en destination.
    Supprime les IDs presents en destination mais absents de la source.
    """
    try:
        start_time = datetime.now()

        # Recuperer le DWH code de l'agent
        agents = execute_query(
            "SELECT dwh_code FROM APP_ETL_Agents WHERE agent_id = ?",
            (agent_id,),
            use_cache=False
        )
        if not agents:
            raise HTTPException(status_code=404, detail="Agent non trouve")

        dwh_code = agents[0]['dwh_code']

        # Executer la detection et suppression
        result = await _detect_and_delete_orphans(
            dwh_code=dwh_code,
            target_table=req.target_table,
            societe_code=req.societe_code,
            primary_key=req.primary_key,
            source_ids=req.source_ids
        )

        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        # Log de la detection
        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO APP_ETL_Deletion_Log (
                        agent_id, table_name, societe_code,
                        source_count, destination_count, deleted_count,
                        duration_ms, status, error_message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        agent_id, req.table_name, req.societe_code,
                        req.source_count, result.get('destination_count', 0),
                        result.get('deleted_count', 0), duration_ms,
                        'success' if result.get('success') else 'error',
                        result.get('error')
                    )
                )
                cursor.commit()
        except Exception as e:
            logger.warning(f"Erreur log deletion (non bloquant): {e}")

        return {
            "success": result.get('success', False),
            "deleted_count": result.get('deleted_count', 0),
            "destination_count": result.get('destination_count', 0),
            "source_count": req.source_count,
            "duration_ms": duration_ms,
            "error": result.get('error')
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur push deletions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _detect_and_delete_orphans(
    dwh_code: str,
    target_table: str,
    societe_code: str,
    primary_key: List[str],
    source_ids: List[Any]
) -> Dict[str, Any]:
    """
    Detecte et supprime les lignes orphelines dans le DWH.

    Args:
        dwh_code: Code du DWH cible
        target_table: Nom de la table cible
        societe_code: Code societe (multi-tenant)
        primary_key: Colonnes de cle primaire
        source_ids: Liste des IDs presents cote source

    Returns:
        Dict avec success, deleted_count, destination_count, error
    """
    if not primary_key:
        return {"success": False, "error": "Cle primaire non definie", "deleted_count": 0}

    if not source_ids:
        # Si pas d'IDs source, ne rien supprimer (table vide cote source = attention)
        logger.warning(f"Aucun ID source pour {target_table} - suppression ignoree")
        return {"success": True, "deleted_count": 0, "destination_count": 0}

    # S'assurer que societe fait partie de la cle primaire
    if 'societe' not in primary_key:
        primary_key = ['societe'] + list(primary_key)

    # Obtenir la connexion DWH
    conn = dwh_manager.get_dwh_connection(dwh_code)
    if not conn:
        return {"success": False, "error": f"Connexion DWH {dwh_code} non disponible", "deleted_count": 0}

    try:
        cursor = conn.cursor()

        # Verifier si la table existe
        cursor.execute(f"""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = '{target_table}'
        """)
        if cursor.fetchone()[0] == 0:
            cursor.close()
            return {"success": True, "deleted_count": 0, "destination_count": 0,
                    "error": f"Table {target_table} n'existe pas"}

        # Compter les lignes en destination pour cette societe
        cursor.execute(
            f"SELECT COUNT(*) FROM [{target_table}] WHERE societe = ?",
            (societe_code,)
        )
        destination_count = cursor.fetchone()[0]

        if destination_count == 0:
            cursor.close()
            return {"success": True, "deleted_count": 0, "destination_count": 0}

        # Determiner la colonne PK principale (hors societe)
        pk_columns = [pk for pk in primary_key if pk != 'societe']
        if not pk_columns:
            cursor.close()
            return {"success": False, "error": "Pas de colonne PK autre que societe", "deleted_count": 0}

        # Strategie: Creer une table temporaire avec les IDs source
        # puis supprimer les lignes en destination qui n'ont pas de correspondance

        # Creer table temporaire
        temp_table = f"#temp_source_ids_{target_table.replace(' ', '_')}"

        # Structure de la table temporaire selon le type de cle
        if len(pk_columns) == 1:
            # Cle simple
            pk_col = pk_columns[0]
            # Determiner le type de la colonne
            sample_id = source_ids[0] if source_ids else None
            if isinstance(sample_id, int):
                pk_type = "BIGINT"
            else:
                pk_type = "NVARCHAR(500)"

            cursor.execute(f"CREATE TABLE {temp_table} ([{pk_col}] {pk_type})")

            # Inserer les IDs source par batch avec executemany (plus performant)
            batch_size = 1000
            insert_sql = f"INSERT INTO {temp_table} ([{pk_col}]) VALUES (?)"
            for i in range(0, len(source_ids), batch_size):
                batch = source_ids[i:i + batch_size]
                try:
                    cursor.executemany(insert_sql, [[sid] for sid in batch])
                except Exception:
                    # Fallback ligne par ligne
                    for sid in batch:
                        try:
                            cursor.execute(insert_sql, (sid,))
                        except Exception:
                            continue
            conn.commit()

            # Supprimer les lignes orphelines avec NOT EXISTS (plus performant que NOT IN)
            delete_sql = f"""
                DELETE dest FROM [{target_table}] dest
                WHERE dest.societe = ?
                  AND NOT EXISTS (
                      SELECT 1 FROM {temp_table} src
                      WHERE src.[{pk_col}] = dest.[{pk_col}]
                  )
            """
            cursor.execute(delete_sql, (societe_code,))
            deleted_count = cursor.rowcount

            # Nettoyer la table temporaire
            try:
                cursor.execute(f"DROP TABLE {temp_table}")
            except Exception:
                pass

        else:
            # Cle composite - utiliser aussi une table temporaire + NOT EXISTS
            temp_table = f"#temp_composite_{target_table.replace(' ', '_')}"

            # Creer table temporaire avec les colonnes PK
            temp_cols_def = ', '.join([f'[{pk}] NVARCHAR(500)' for pk in pk_columns])
            cursor.execute(f"CREATE TABLE {temp_table} ({temp_cols_def})")

            # Inserer les IDs source par batch
            pk_cols_str = ', '.join([f'[{pk}]' for pk in pk_columns])
            placeholders = ', '.join(['?' for _ in pk_columns])
            insert_sql = f"INSERT INTO {temp_table} ({pk_cols_str}) VALUES ({placeholders})"

            batch_size = 500
            for i in range(0, len(source_ids), batch_size):
                batch = source_ids[i:i + batch_size]
                batch_values = []
                for sid in batch:
                    if isinstance(sid, (list, tuple)):
                        batch_values.append(list(sid))
                    else:
                        batch_values.append([sid])
                try:
                    cursor.executemany(insert_sql, batch_values)
                except Exception:
                    for vals in batch_values:
                        try:
                            cursor.execute(insert_sql, vals)
                        except Exception:
                            continue
            conn.commit()

            # Supprimer avec NOT EXISTS (performant)
            pk_join = ' AND '.join([f'dest.[{pk}] = src.[{pk}]' for pk in pk_columns])
            delete_sql = f"""
                DELETE dest FROM [{target_table}] dest
                WHERE dest.societe = ?
                  AND NOT EXISTS (
                      SELECT 1 FROM {temp_table} src
                      WHERE {pk_join}
                  )
            """
            cursor.execute(delete_sql, (societe_code,))
            deleted_count = cursor.rowcount

            # Nettoyer la table temporaire
            try:
                cursor.execute(f"DROP TABLE {temp_table}")
            except Exception:
                pass

        conn.commit()
        cursor.close()

        logger.info(f"Detection suppressions {target_table}: {deleted_count} lignes supprimees sur {destination_count}")

        return {
            "success": True,
            "deleted_count": deleted_count,
            "destination_count": destination_count
        }

    except Exception as e:
        logger.error(f"Erreur detection suppressions: {e}")
        return {"success": False, "error": str(e), "deleted_count": 0}


@router.get("/admin/etl/agents/{agent_id}/config-file")
async def get_agent_config_file(agent_id: str):
    """Genere le fichier de configuration .env pour un agent specifique"""
    try:
        # Recuperer les infos de l'agent
        agents = execute_query(
            """
            SELECT agent_id, name, api_key_hash, dwh_code,
                   sync_interval_seconds, heartbeat_interval_seconds,
                   sage_server, sage_database, sage_username
            FROM APP_ETL_Agents
            WHERE agent_id = ?
            """,
            (agent_id,),
            use_cache=False
        )

        if not agents:
            raise HTTPException(status_code=404, detail="Agent non trouve")

        agent = agents[0]

        # Generer le contenu du fichier .env
        config_content = f"""# Configuration Agent ETL
# Agent: {agent.get('name', 'Agent')}
# Genere automatiquement

# Serveur Central
SERVER_URL=http://VOTRE_SERVEUR:8080
AGENT_ID={agent_id}
API_KEY=VOTRE_CLE_API

# Base Sage (Source)
SAGE_SERVER={agent.get('sage_server') or '.'}
SAGE_DATABASE={agent.get('sage_database') or 'NOM_BASE_SAGE'}
SAGE_USERNAME={agent.get('sage_username') or 'sa'}
SAGE_PASSWORD=VOTRE_MOT_DE_PASSE
SAGE_DRIVER=ODBC Driver 17 for SQL Server

# Identifiants société (utilisés comme DB_Id et societe dans le DWH)
CODE_SOCIETE={agent.get('code_societe') or agent.get('name') or ''}
NOM_SOCIETE={agent.get('nom_societe') or agent.get('name') or ''}

# Intervalles (en secondes)
SYNC_INTERVAL={agent.get('sync_interval_seconds') or 300}
HEARTBEAT_INTERVAL={agent.get('heartbeat_interval_seconds') or 30}

# Options
BATCH_SIZE=10000
LOG_LEVEL=INFO
LOG_FILE=agent_etl.log
"""

        return {
            "success": True,
            "agent_id": agent_id,
            "config": config_content
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur generation config agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Test BULK INSERT Performance
# ============================================================

class BulkInsertTestRequest(BaseModel):
    """Requete pour le test BULK INSERT"""
    table_name: str = Field(..., description="Nom de la table ETL a tester")
    row_limit: int = Field(default=10000, description="Nombre max de lignes a tester")


class BulkInsertTestResult(BaseModel):
    """Resultat d'un test d'insertion"""
    method: str
    rows: int
    duration_ms: int
    rows_per_sec: int
    status: str
    error: Optional[str] = None
    note: Optional[str] = None


@router.post("/etl/test/bulk-insert")
async def test_bulk_insert_performance(req: BulkInsertTestRequest):
    """
    Test de performance comparant differentes methodes d'insertion:
    1. fast_executemany (methode actuelle)
    2. INSERT VALUES multiples
    3. executemany standard

    Insere dans la base DWH configuree dans APP_DWH.
    """
    import time
    import traceback as tb_module
    import pyodbc

    results = []
    start_time = datetime.now()
    conn = None
    cursor = None
    dwh_info = None

    try:
        logger.info(f"=== DEBUT Test BULK INSERT ===")
        logger.info(f"Params: table={req.table_name}, limit={req.row_limit}")

        # 1. Recuperer les infos DWH depuis APP_DWH
        logger.info("Etape 1: Lecture config DWH...")
        dwh_config = execute_query(
            "SELECT TOP 1 code, nom, serveur_dwh, base_dwh, user_dwh, password_dwh FROM APP_DWH WHERE actif = 1",
            use_cache=False
        )

        if not dwh_config:
            raise HTTPException(status_code=400, detail="Aucun DWH actif dans APP_DWH")

        dwh_info = dwh_config[0]
        logger.info(f"DWH trouve: {dwh_info['nom']} ({dwh_info['serveur_dwh']}/{dwh_info['base_dwh']})")

        # 2. Connexion directe au DWH
        logger.info("Etape 2: Connexion au DWH...")
        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={dwh_info['serveur_dwh']};"
            f"DATABASE={dwh_info['base_dwh']};"
            f"UID={dwh_info['user_dwh']};"
            f"PWD={dwh_info['password_dwh']};"
            f"TrustServerCertificate=yes;"
        )
        conn = pyodbc.connect(conn_str, timeout=30)
        cursor = conn.cursor()
        logger.info("OK - Connexion DWH etablie")

        # 3. Generer des donnees de test
        num_rows = min(req.row_limit, 50000)
        num_cols = 20

        columns = [f"col_{i}" for i in range(num_cols)]
        cols_str = ', '.join([f'[{c}]' for c in columns])
        placeholders = ', '.join(['?' for _ in columns])

        logger.info(f"Etape 3: Generation de {num_rows} lignes...")
        batch_values = []
        for row_idx in range(num_rows):
            row = []
            for col_idx in range(num_cols):
                if col_idx == 0:
                    row.append(str(row_idx))
                elif col_idx < 5:
                    row.append(f"Text_{row_idx}_{col_idx}")
                elif col_idx < 10:
                    row.append(str(row_idx * col_idx))
                else:
                    row.append(f"Long_{row_idx}_{col_idx}_" + "x" * 30)
            batch_values.append(row)

        # 4. Creer table temporaire dans le DWH
        test_table = "#bulk_perf_test"
        logger.info(f"Etape 4: Creation table {test_table}...")
        try:
            cursor.execute(f"DROP TABLE IF EXISTS {test_table}")
        except:
            pass

        cols_def = ', '.join([f'[{c}] NVARCHAR(500)' for c in columns])
        cursor.execute(f"CREATE TABLE {test_table} ({cols_def})")
        conn.commit()
        logger.info("OK - Table temporaire creee")

        # ========== TEST 1: fast_executemany ==========
        try:
            logger.info("Test 1: fast_executemany...")
            cursor.execute(f"TRUNCATE TABLE {test_table}")
            conn.commit()

            cursor.fast_executemany = True
            insert_sql = f"INSERT INTO {test_table} ({cols_str}) VALUES ({placeholders})"

            t1_start = time.perf_counter()
            batch_size = 5000
            for i in range(0, len(batch_values), batch_size):
                batch = batch_values[i:i+batch_size]
                cursor.executemany(insert_sql, batch)
            conn.commit()
            t1_duration = time.perf_counter() - t1_start

            results.append(BulkInsertTestResult(
                method="fast_executemany",
                rows=num_rows,
                duration_ms=int(t1_duration * 1000),
                rows_per_sec=int(num_rows / t1_duration) if t1_duration > 0 else 0,
                status="success",
                note="Methode pyodbc optimisee (actuelle)"
            ))
            logger.info(f"  -> {int(t1_duration * 1000)}ms")
        except Exception as e:
            logger.error(f"Erreur test 1: {e}")
            results.append(BulkInsertTestResult(
                method="fast_executemany",
                rows=0, duration_ms=0, rows_per_sec=0,
                status="error", error=str(e)
            ))

        # ========== TEST 2: INSERT VALUES multiples ==========
        try:
            logger.info("Test 2: INSERT VALUES multiples...")
            cursor.execute(f"TRUNCATE TABLE {test_table}")
            conn.commit()

            t2_start = time.perf_counter()
            batch_size = 500  # Plus petit pour eviter query trop longue
            for i in range(0, len(batch_values), batch_size):
                batch = batch_values[i:i+batch_size]
                values_strs = []
                for row_vals in batch:
                    escaped = []
                    for v in row_vals:
                        if v is None:
                            escaped.append('NULL')
                        else:
                            v_escaped = str(v).replace("'", "''")
                            escaped.append(f"N'{v_escaped}'")
                    values_strs.append(f"({', '.join(escaped)})")

                insert_sql_batch = f"INSERT INTO {test_table} ({cols_str}) VALUES {', '.join(values_strs)}"
                cursor.execute(insert_sql_batch)
            conn.commit()
            t2_duration = time.perf_counter() - t2_start

            results.append(BulkInsertTestResult(
                method="insert_values_multiples",
                rows=num_rows,
                duration_ms=int(t2_duration * 1000),
                rows_per_sec=int(num_rows / t2_duration) if t2_duration > 0 else 0,
                status="success",
                note="Batch de 500 valeurs par INSERT"
            ))
            logger.info(f"  -> {int(t2_duration * 1000)}ms")
        except Exception as e:
            logger.error(f"Erreur test 2: {e}")
            results.append(BulkInsertTestResult(
                method="insert_values_multiples",
                rows=0, duration_ms=0, rows_per_sec=0,
                status="error", error=str(e)
            ))

        # ========== TEST 3: executemany standard (sans fast) ==========
        try:
            test_rows_std = min(2000, num_rows)  # Limite car tres lent
            logger.info(f"Test 3: executemany standard ({test_rows_std} lignes)...")
            cursor.execute(f"TRUNCATE TABLE {test_table}")
            conn.commit()

            cursor.fast_executemany = False
            insert_sql = f"INSERT INTO {test_table} ({cols_str}) VALUES ({placeholders})"
            batch_values_std = batch_values[:test_rows_std]

            t3_start = time.perf_counter()
            batch_size = 200
            for i in range(0, len(batch_values_std), batch_size):
                batch = batch_values_std[i:i+batch_size]
                cursor.executemany(insert_sql, batch)
            conn.commit()
            t3_duration = time.perf_counter() - t3_start

            results.append(BulkInsertTestResult(
                method="executemany_standard",
                rows=test_rows_std,
                duration_ms=int(t3_duration * 1000),
                rows_per_sec=int(test_rows_std / t3_duration) if t3_duration > 0 else 0,
                status="success",
                note=f"Limite a {test_rows_std} lignes (reference lente)"
            ))
            logger.info(f"  -> {int(t3_duration * 1000)}ms")
        except Exception as e:
            logger.error(f"Erreur test 3: {e}")
            results.append(BulkInsertTestResult(
                method="executemany_standard",
                rows=0, duration_ms=0, rows_per_sec=0,
                status="error", error=str(e)
            ))

        # Nettoyer
        try:
            cursor.execute(f"DROP TABLE IF EXISTS {test_table}")
            conn.commit()
        except:
            pass

        cursor.close()

        # Trier par performance (les reussis d'abord, puis par vitesse)
        results_sorted = sorted(
            results,
            key=lambda x: (0 if x.status == "success" else 1, x.duration_ms if x.duration_ms > 0 else 999999)
        )

        total_duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        dwh_name = dwh_info['nom'] if dwh_info else "DWH"
        dwh_server = dwh_info['serveur_dwh'] if dwh_info else ""
        dwh_db = dwh_info['base_dwh'] if dwh_info else ""

        return {
            "success": True,
            "table_tested": req.table_name,
            "source": "Donnees generees en memoire",
            "destination": f"{dwh_name} ({dwh_server}/{dwh_db})",
            "rows_read": num_rows,
            "columns_count": num_cols,
            "total_duration_ms": total_duration_ms,
            "results": [r.dict() for r in results_sorted],
            "best_method": results_sorted[0].method if results_sorted and results_sorted[0].status == "success" else None,
            "recommendation": _get_bulk_recommendation(results_sorted)
        }

    except HTTPException:
        raise
    except Exception as e:
        full_tb = tb_module.format_exc()
        logger.error(f"=== ERREUR Test BULK INSERT ===\n{full_tb}")
        # Retourner un detail complet de l'erreur
        error_detail = f"{type(e).__name__}: {str(e)}"
        raise HTTPException(status_code=500, detail=error_detail)
    finally:
        logger.info("=== FIN Test BULK INSERT (cleanup) ===")
        if cursor:
            try:
                cursor.close()
            except:
                pass
        if conn:
            try:
                conn.close()
            except:
                pass


def _get_bulk_recommendation(results: List[BulkInsertTestResult]) -> str:
    """Genere une recommandation basee sur les resultats du test."""
    if not results:
        return "Aucun resultat disponible"

    successful = [r for r in results if r.status == "success"]
    if not successful:
        return "Tous les tests ont echoue"

    best = successful[0]

    if best.method == "fast_executemany":
        return (
            f"fast_executemany est la methode la plus rapide ({best.rows_per_sec} rows/sec). "
            "C'est la methode actuellement utilisee - aucun changement necessaire."
        )
    elif best.method == "insert_values_multiples":
        fast_result = next((r for r in successful if r.method == "fast_executemany"), None)
        if fast_result:
            ratio = fast_result.duration_ms / best.duration_ms if best.duration_ms > 0 else 0
            return (
                f"INSERT VALUES multiples est {ratio:.1f}x plus rapide que fast_executemany. "
                "Envisagez de modifier direct_sync.py pour utiliser cette methode."
            )
        return f"INSERT VALUES multiples est la methode la plus rapide ({best.rows_per_sec} rows/sec)."
    else:
        return f"{best.method} est la methode la plus rapide ({best.rows_per_sec} rows/sec)."
