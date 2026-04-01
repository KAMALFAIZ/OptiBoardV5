"""
SQL Jobs Routes
===============
Routes FastAPI pour la gestion de l'infrastructure ETL SQL Agent Jobs.
Permet de deployer, configurer et monitorer les jobs ETL depuis l'interface web.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
import logging

from ..services import sql_jobs_service as svc

router = APIRouter(prefix="/api/admin/sql-jobs", tags=["SQL Jobs Admin"])
logger = logging.getLogger("sql_jobs_routes")


# =====================================================
# MODELES PYDANTIC
# =====================================================

class ExecuteScriptRequest(BaseModel):
    script_name: str = Field(..., description="Nom du script SQL (sans extension)")
    # Parametres pour le Linked Server (script 06)
    # Direction : cree SUR le serveur Sage, pointe VERS le DWH
    linked_server_name: Optional[str] = Field(None, description="Nom du Linked Server (ex: DWH_ESSAIDI26)")
    sage_server_ip: Optional[str] = Field(None, description="IP ou hostname du serveur Sage (ou on execute)")
    sage_user: Optional[str] = Field(None, description="Utilisateur SQL du serveur Sage")
    sage_pwd: Optional[str] = Field(None, description="Mot de passe SQL du serveur Sage")

class AddSourceRequest(BaseModel):
    source_code: str = Field(..., description="Code unique de la source (ex: CASHPLUS_2026)")
    source_caption: str = Field(..., description="Libelle de la source")
    db_id: int = Field(..., description="Identifiant DB (1, 2, 3...)")
    server_name: str = Field(..., description="Nom ou IP du serveur SQL")
    database_name: str = Field(..., description="Nom de la base Sage")
    is_linked_server: bool = Field(False, description="Utiliser un Linked Server")
    linked_server_name: Optional[str] = Field(None, description="Nom du Linked Server")

class JobActionRequest(BaseModel):
    job_name: str = Field(..., description="Nom du job SQL Agent")

class AgentServiceActionRequest(BaseModel):
    action: str = Field(..., description="Action: 'start' ou 'stop'")

class ResetSyncRequest(BaseModel):
    target_table: Optional[str] = Field(None, description="Table cible (None = toutes)")


# =====================================================
# ENDPOINTS DWH
# =====================================================

@router.get("/dwh-list")
async def list_dwh():
    """Liste les DWH disponibles pour selection"""
    try:
        data = svc.get_dwh_list()
        return {"success": True, "data": data, "count": len(data)}
    except Exception as e:
        logger.error(f"Erreur list_dwh: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{dwh_code}/status")
async def get_dwh_status(dwh_code: str):
    """Statut complet du DWH : connexion, SQL Agent, infrastructure, config Sage"""
    try:
        sage_cfg = svc.get_sage_config(dwh_code)
        agent = svc.check_sql_agent_status(dwh_code)
        infra = svc.check_infrastructure_status(dwh_code)
        return {
            "success": True,
            "data": {
                "sql_agent": agent,
                "infrastructure": infra,
                "sage_config": sage_cfg
            }
        }
    except Exception as e:
        logger.error(f"Erreur status {dwh_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{dwh_code}/infrastructure")
async def get_infrastructure(dwh_code: str):
    """Detail de l'infrastructure ETL"""
    try:
        data = svc.check_infrastructure_status(dwh_code)
        return {"success": True, "data": data}
    except Exception as e:
        logger.error(f"Erreur infrastructure {dwh_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# ENDPOINTS CONFIG SAGE (serveur ou tourne SQL Agent)
# =====================================================

class SageConfigRequest(BaseModel):
    sage_server: str = Field(..., description="IP ou hostname du serveur Sage")
    sage_user: str = Field(..., description="Utilisateur SQL du serveur Sage")
    sage_pwd: str = Field("", description="Mot de passe SQL du serveur Sage")


@router.get("/{dwh_code}/sage-config")
async def get_sage_config(dwh_code: str):
    """Recupere la config Sage du DWH"""
    try:
        data = svc.get_sage_config(dwh_code)
        return {"success": True, "data": data}
    except Exception as e:
        logger.error(f"Erreur get sage config {dwh_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{dwh_code}/sage-config")
async def update_sage_config(dwh_code: str, req: SageConfigRequest):
    """Sauvegarde les infos de connexion Sage dans APP_DWH"""
    try:
        result = svc.update_sage_config(dwh_code, req.sage_server, req.sage_user, req.sage_pwd)
        if result["success"]:
            return {"success": True, "message": result["message"]}
        else:
            raise HTTPException(status_code=400, detail=result["message"])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur update sage config {dwh_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# ENDPOINTS SCRIPTS SQL
# =====================================================

@router.get("/{dwh_code}/script-preview/{script_name}")
async def preview_script(dwh_code: str, script_name: str):
    """Preview du SQL parametrise avant execution"""
    try:
        data = svc.preview_script(script_name, dwh_code)
        return {"success": True, "data": data}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Erreur preview {script_name} sur {dwh_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{dwh_code}/execute-script")
async def execute_script(dwh_code: str, req: ExecuteScriptRequest):
    """Execute un script SQL sur le DWH"""
    try:
        # Scripts 06 et 07 : executent SUR le serveur Sage (pas le DWH)
        # 06 = Linked Server (Sage → DWH)
        # 07 = SQL Agent Jobs (tournent sur Sage, accedent DWH via LS)
        scripts_on_sage = ["04b_sp_sync_generic_local", "06_setup_linked_server", "07_create_sql_agent_jobs"]

        if req.script_name in scripts_on_sage:
            if not req.sage_server_ip:
                raise HTTPException(
                    status_code=400,
                    detail="IP/Hostname du serveur Sage requis pour ce script"
                )
            # Recuperer les infos du DWH (cible du Linked Server)
            dwh_info = svc._get_dwh_db_info(dwh_code)
            ls_name = req.linked_server_name or dwh_info["base_dwh"]
            extra_params = {
                "LINKED_SERVER_NAME": ls_name,
                "LINKED_SERVER_DWH": ls_name,
                "DWH_SERVER_IP": dwh_info["serveur_dwh"],
                "DWH_USER": dwh_info["user_dwh"],
                "DWH_PWD": dwh_info["password_dwh"],
            }
            # Executer sur le serveur SAGE
            sage_conn_info = {
                "server": req.sage_server_ip,
                "user": req.sage_user or "sa",
                "password": req.sage_pwd or "",
            }
            result = svc.execute_script_on_server(req.script_name, dwh_code, extra_params, sage_conn_info)
        else:
            result = svc.execute_script(req.script_name, dwh_code)
        if result["success"]:
            return {"success": True, "message": f"Script '{req.script_name}' execute avec succes", "data": result}
        else:
            return {"success": False, "message": f"Script '{req.script_name}' termine avec des erreurs", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Erreur execute {req.script_name} sur {dwh_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# ENDPOINTS SOURCES ETL
# =====================================================

@router.get("/{dwh_code}/sources")
async def list_sources(dwh_code: str):
    """Liste les sources ETL du DWH"""
    try:
        data = svc.get_etl_sources(dwh_code)
        return {"success": True, "data": data, "count": len(data)}
    except Exception as e:
        logger.error(f"Erreur list sources {dwh_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{dwh_code}/sources")
async def add_source(dwh_code: str, req: AddSourceRequest):
    """Ajoute une source Sage via SP_ETL_Setup_Source"""
    try:
        result = svc.add_etl_source(dwh_code, req.dict())
        if result["success"]:
            return {"success": True, "message": "Source ajoutee avec succes", "data": result}
        else:
            raise HTTPException(status_code=400, detail=result.get("message", "Erreur"))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur add source {dwh_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{dwh_code}/sources/{source_code}")
async def update_source(dwh_code: str, source_code: str, req: AddSourceRequest):
    """Met a jour une source Sage existante"""
    try:
        result = svc.update_etl_source(dwh_code, source_code, req.dict())
        if result["success"]:
            return {"success": True, "message": "Source mise a jour", "data": result}
        else:
            raise HTTPException(status_code=400, detail=result.get("message", "Erreur"))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur update source {dwh_code}/{source_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{dwh_code}/sources/{source_code}")
async def delete_source(dwh_code: str, source_code: str):
    """Supprime une source ETL"""
    try:
        result = svc.delete_etl_source(dwh_code, source_code)
        if result["success"]:
            return {"success": True, "message": "Source supprimee"}
        else:
            raise HTTPException(status_code=400, detail=result.get("message", "Erreur"))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur delete source {dwh_code}/{source_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{dwh_code}/sources/{source_code}/toggle")
async def toggle_source(dwh_code: str, source_code: str):
    """Active/desactive une source ETL"""
    try:
        result = svc.toggle_source(dwh_code, source_code)
        return {"success": result["success"], "data": result}
    except Exception as e:
        logger.error(f"Erreur toggle source {dwh_code}/{source_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{dwh_code}/sources/{source_code}/test")
async def test_source(dwh_code: str, source_code: str):
    """Teste la connexion vers une source Sage"""
    try:
        result = svc.test_source_connection(dwh_code, source_code)
        return {"success": result["success"], "message": result["message"]}
    except Exception as e:
        logger.error(f"Erreur test source {dwh_code}/{source_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# ENDPOINTS LINKED SERVERS
# =====================================================

@router.get("/{dwh_code}/linked-servers")
async def list_linked_servers(dwh_code: str):
    """Liste les Linked Servers existants"""
    try:
        data = svc.get_linked_servers(dwh_code)
        return {"success": True, "data": data, "count": len(data)}
    except Exception as e:
        logger.error(f"Erreur list linked servers {dwh_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{dwh_code}/linked-servers/{ls_name}")
async def drop_linked_server(dwh_code: str, ls_name: str):
    """Supprime un Linked Server"""
    try:
        result = svc.drop_linked_server(dwh_code, ls_name)
        if result["success"]:
            return {"success": True, "message": result["message"]}
        else:
            raise HTTPException(status_code=400, detail=result["message"])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur drop linked server {dwh_code}/{ls_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# ENDPOINTS JOBS SQL AGENT
# =====================================================

@router.get("/{dwh_code}/jobs")
async def get_jobs(dwh_code: str):
    """Statut des SQL Agent Jobs"""
    try:
        data = svc.get_jobs_status(dwh_code)
        return {"success": True, "data": data, "count": len(data)}
    except Exception as e:
        logger.error(f"Erreur jobs status {dwh_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{dwh_code}/jobs/start")
async def start_job(dwh_code: str, req: JobActionRequest):
    """Demarre un SQL Agent Job"""
    try:
        result = svc.start_job(dwh_code, req.job_name)
        if result["success"]:
            return {"success": True, "message": result["message"]}
        else:
            raise HTTPException(status_code=400, detail=result["message"])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur start job {dwh_code}/{req.job_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{dwh_code}/jobs/stop")
async def stop_job(dwh_code: str, req: JobActionRequest):
    """Arrete un SQL Agent Job"""
    try:
        result = svc.stop_job(dwh_code, req.job_name)
        if result["success"]:
            return {"success": True, "message": result["message"]}
        else:
            raise HTTPException(status_code=400, detail=result["message"])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur stop job {dwh_code}/{req.job_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{dwh_code}/agent-service")
async def control_agent_service(dwh_code: str, req: AgentServiceActionRequest):
    """Demarre ou arrete le service SQL Server Agent"""
    try:
        result = svc.control_sql_agent_service(dwh_code, req.action)
        if result["success"]:
            return {"success": True, "message": result["message"], "data": result.get("new_status")}
        else:
            raise HTTPException(status_code=400, detail=result["message"])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur agent-service {dwh_code}/{req.action}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# ENDPOINTS MONITORING
# =====================================================

@router.get("/{dwh_code}/sync-control")
async def get_sync_control(dwh_code: str):
    """Resume du SyncControl"""
    try:
        data = svc.get_sync_control(dwh_code)
        return {"success": True, "data": data, "count": len(data)}
    except Exception as e:
        logger.error(f"Erreur sync-control {dwh_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{dwh_code}/sync-logs")
async def get_sync_logs(dwh_code: str, limit: int = Query(50, ge=1, le=500)):
    """Logs de synchronisation recents"""
    try:
        data = svc.get_sync_logs(dwh_code, limit)
        return {"success": True, "data": data, "count": len(data)}
    except Exception as e:
        logger.error(f"Erreur sync-logs {dwh_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{dwh_code}/etl-tables-config")
async def get_etl_tables_config(dwh_code: str):
    """Configuration des tables ETL depuis OptiBoard"""
    try:
        data = svc.get_etl_tables_config()
        return {"success": True, "data": data, "count": len(data)}
    except Exception as e:
        logger.error(f"Erreur etl-tables-config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{dwh_code}/reset-sync/{target_table}")
async def reset_sync(dwh_code: str, target_table: str):
    """Reset SyncControl pour forcer un full sync"""
    try:
        result = svc.reset_sync_control(dwh_code, target_table if target_table != "_all" else None)
        return {"success": result["success"], "data": result}
    except Exception as e:
        logger.error(f"Erreur reset sync {dwh_code}/{target_table}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{dwh_code}/cleanup-logs")
async def cleanup_logs(dwh_code: str, retention_days: int = 0):
    """Purge les logs ETL (ETL_Sync_Log, ETL_Alerts, SyncControl orphelins)"""
    try:
        result = svc.cleanup_etl_logs(dwh_code, retention_days)
        if result["success"]:
            return {"success": True, "data": result}
        raise HTTPException(status_code=500, detail=result.get("message", "Erreur inconnue"))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur cleanup logs {dwh_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
