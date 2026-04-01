"""
SQL Jobs Service
================
Service pour la gestion de l'infrastructure ETL SQL Server Agent Jobs.
Lit, parametrise et execute les scripts SQL depuis sql/sql_jobs/
pour deployer tables, SPs, vues et jobs sur un DWH selectionne.
"""

import re
import time
import logging
import pyodbc
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

from ..database_unified import (
    execute_central as execute_central_query,
    write_central as execute_central_write,
    execute_dwh_query,
    execute_dwh_write,
    dwh_pool,
)
from ..config_multitenant import get_central_settings

logger = logging.getLogger("SQLJobsService")

# Repertoire des scripts SQL
SQL_SCRIPTS_DIR = Path(__file__).parent.parent.parent / "sql" / "sql_jobs"

# Whitelist des scripts autorises (sans extension .sql)
ALLOWED_SCRIPTS = [
    "01_create_dwh_database",
    "02_create_etl_config_tables",
    "03_insert_etl_config_data",
    "04_sp_sync_generic",
    "04b_sp_sync_generic_local",
    "05_sp_etl_orchestrators",
    "06_setup_linked_server",
    "07_create_sql_agent_jobs",
    "08_monitoring_views",
]


# =====================================================
# UTILITAIRES
# =====================================================

def _get_dwh_db_info(dwh_code: str) -> Dict[str, str]:
    """Recupere les infos de connexion du DWH depuis la base centrale"""
    results = execute_central_query(
        "SELECT code, nom, serveur_dwh, base_dwh, user_dwh, password_dwh, "
        "sage_server, sage_user, sage_pwd "
        "FROM APP_DWH WHERE code = ? AND actif = 1",
        (dwh_code,),
        use_cache=False
    )
    if not results:
        raise ValueError(f"DWH '{dwh_code}' non trouve ou inactif")
    return results[0]


def _get_sage_connection(dwh_code: str) -> pyodbc.Connection:
    """
    Obtient une connexion brute pyodbc vers le serveur Sage (ou tourne SQL Agent).
    Cherche les infos de connexion dans cet ordre :
      1. APP_DWH (colonnes sage_server, sage_user, sage_pwd)
      2. APP_DWH_Sources (base centrale, premiere source active)
      3. ETL_Sources (base DWH, premiere source active)
    """
    info = _get_dwh_db_info(dwh_code)
    sage_server = info.get("sage_server")
    sage_user = info.get("sage_user")
    sage_pwd = info.get("sage_pwd")

    # Fallback 1 : APP_DWH_Sources (base centrale OptiBoard_SaaS)
    if not sage_server or not sage_user:
        try:
            sources = execute_central_query(
                "SELECT TOP 1 serveur_sage, user_sage, password_sage "
                "FROM APP_DWH_Sources WHERE dwh_code = ? AND actif = 1 ORDER BY id",
                (dwh_code,), use_cache=False
            )
            if sources:
                sage_server = sage_server or sources[0].get("serveur_sage")
                sage_user = sage_user or sources[0].get("user_sage")
                sage_pwd = sage_pwd or sources[0].get("password_sage")
                logger.info(f"Sage config pour {dwh_code}: fallback APP_DWH_Sources -> {sage_server}")
        except Exception:
            pass

    # Fallback 2 : ETL_Sources (base DWH du client)
    if not sage_server:
        try:
            etl = execute_dwh_query(
                dwh_code,
                "SELECT TOP 1 server_name FROM ETL_Sources WHERE is_active = 1 ORDER BY source_id",
                use_cache=False
            )
            if etl:
                sage_server = etl[0].get("server_name")
                sage_user = sage_user or info.get("user_dwh")
                sage_pwd = sage_pwd or info.get("password_dwh")
                logger.info(f"Sage config pour {dwh_code}: fallback ETL_Sources -> {sage_server}")
        except Exception:
            pass

    if not sage_server or not sage_user:
        raise ValueError(
            "Infos de connexion Sage introuvables. Aucune source Sage configuree "
            "dans APP_DWH, APP_DWH_Sources ou ETL_Sources."
        )

    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={sage_server};"
        f"DATABASE=master;"
        f"UID={sage_user};"
        f"PWD={sage_pwd or ''};"
        f"TrustServerCertificate=yes;"
        f"Connection Timeout=10;"
    )
    conn = pyodbc.connect(conn_str, autocommit=True)
    return conn


def _get_raw_connection(dwh_code: str) -> pyodbc.Connection:
    """Obtient une connexion brute pyodbc vers le serveur DWH avec autocommit"""
    conn = dwh_pool.get_connection(dwh_code)
    conn.autocommit = True
    return conn


def _split_go_batches(sql_content: str) -> List[str]:
    """
    Decoupe un script SQL en batches separees par GO.
    Gere les variantes : GO seul sur une ligne, avec espaces, etc.
    Supprime d'abord les commentaires multi-lignes /* ... */ pour eviter
    que les GO a l'interieur des commentaires ne cassent le split.
    """
    # Etape 1: Supprimer les blocs commentaires /* ... */ (non-greedy)
    # Cela evite que les GO dans les commentaires ne soient interpretes
    cleaned = re.sub(r'/\*.*?\*/', '', sql_content, flags=re.DOTALL)
    # Etape 2: Split sur GO seul sur une ligne
    batches = re.split(r'^\s*GO\s*$', cleaned, flags=re.MULTILINE | re.IGNORECASE)
    # Etape 3: Filtrer les batches vides ou ne contenant que des commentaires/espaces
    result = []
    for b in batches:
        stripped = b.strip()
        if not stripped:
            continue
        # Verifier que le batch contient du SQL reel (pas uniquement des commentaires --)
        has_sql = False
        for line in stripped.split('\n'):
            line_clean = line.strip()
            if line_clean and not line_clean.startswith('--'):
                has_sql = True
                break
        if has_sql:
            result.append(stripped)
    return result


def _ensure_use_per_batch(batches: List[str]) -> List[str]:
    """
    Garantit que chaque batch a son propre USE [database] si le script
    en utilise. pyodbc avec autocommit=True ne propage PAS toujours
    le USE entre cursor.execute() calls. On track le dernier USE vu
    et on le pre-injecte dans les batches qui n'en ont pas.
    """
    use_pattern = re.compile(r'^\s*USE\s+\[?([^\];\s]+)\]?\s*;?', re.IGNORECASE | re.MULTILINE)
    last_use_stmt = None
    result = []

    for batch in batches:
        # Chercher si ce batch contient un USE [...]
        match = use_pattern.search(batch)
        if match:
            # Ce batch a son propre USE — extraire la version canonique
            db_name = match.group(1)
            last_use_stmt = f"USE [{db_name}];\n"
        elif last_use_stmt:
            # Ce batch n'a pas de USE mais on en a vu un avant → injecter
            batch = last_use_stmt + batch

        result.append(batch)

    return result


# =====================================================
# LISTE DES DWH
# =====================================================

def get_dwh_list() -> List[Dict[str, Any]]:
    """Liste tous les DWH actifs pour le dropdown de selection"""
    return execute_central_query(
        "SELECT code, nom, raison_sociale, serveur_dwh, base_dwh, actif "
        "FROM APP_DWH WHERE actif = 1 ORDER BY nom",
        use_cache=False
    )


def get_sage_config(dwh_code: str) -> Dict[str, Any]:
    """Recupere la config Sage (serveur, user) depuis APP_DWH"""
    info = _get_dwh_db_info(dwh_code)
    return {
        "sage_server": info.get("sage_server"),
        "sage_user": info.get("sage_user"),
        "sage_configured": bool(info.get("sage_server") and info.get("sage_user")),
    }


def update_sage_config(dwh_code: str, sage_server: str, sage_user: str, sage_pwd: str) -> Dict[str, Any]:
    """Sauvegarde les infos de connexion Sage dans APP_DWH"""
    try:
        execute_central_write(
            "UPDATE APP_DWH SET sage_server = ?, sage_user = ?, sage_pwd = ?, "
            "date_modification = GETDATE() WHERE code = ?",
            (sage_server, sage_user, sage_pwd, dwh_code)
        )
        logger.info(f"Config Sage mise a jour pour {dwh_code}: server={sage_server}, user={sage_user}")
        return {"success": True, "message": "Configuration Sage sauvegardee"}
    except Exception as e:
        logger.error(f"Erreur update sage config pour {dwh_code}: {e}")
        return {"success": False, "message": str(e)}


# =====================================================
# STATUT ET INFRASTRUCTURE
# =====================================================

def check_sql_agent_status(dwh_code: str) -> Dict[str, Any]:
    """Verifie si SQL Server Agent est actif sur le serveur Sage"""
    try:
        conn = _get_sage_connection(dwh_code)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT
                    CAST(servicename AS NVARCHAR(256)) AS svc_display_name,
                    CAST(status_desc AS NVARCHAR(256)) AS svc_status,
                    CAST(startup_type_desc AS NVARCHAR(256)) AS svc_startup
                FROM sys.dm_server_services
                WHERE servicename LIKE N'SQL Server Agent%'
            """)
            row = cursor.fetchone()
            if row:
                return {
                    "running": row.svc_status == "Running",
                    "status": row.svc_status,
                    "service_name": row.svc_display_name,
                    "startup_type": row.svc_startup
                }
            return {"running": False, "status": "Not Found", "service_name": None, "startup_type": None}
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.warning(f"Erreur check SQL Agent pour {dwh_code}: {e}")
        return {"running": False, "status": f"Erreur: {str(e)}", "service_name": None, "startup_type": None}


def control_sql_agent_service(dwh_code: str, action: str) -> Dict[str, Any]:
    """
    Demarre ou arrete le service SQL Server Agent sur le serveur Sage.
    Utilise xp_servicecontrol (extended procedure native SQL Server, requiert sysadmin).
    """
    if action not in ("start", "stop"):
        return {"success": False, "message": f"Action '{action}' non valide. Utilisez 'start' ou 'stop'"}

    try:
        conn = _get_sage_connection(dwh_code)
        cursor = conn.cursor()
        try:
            # 1. Recuperer le nom Windows du service SQL Agent
            cursor.execute("""
                SELECT
                    CAST(servicename AS NVARCHAR(256)) AS svc_display_name,
                    CAST(status_desc AS NVARCHAR(256)) AS svc_status
                FROM sys.dm_server_services
                WHERE servicename LIKE N'SQL Server Agent%'
            """)
            row = cursor.fetchone()
            if not row:
                return {"success": False, "message": "Service SQL Server Agent introuvable sur ce serveur"}

            # Determiner le nom Windows du service a partir du nom d'affichage
            display_name = row.svc_display_name  # ex: "SQL Server Agent (MSSQLSERVER)"
            current_status = row.svc_status       # Running, Stopped, etc.
            # Extraire le nom du service Windows : SQLAgent$INSTANCE ou SQLSERVERAGENT
            if "(" in display_name:
                instance = display_name.split("(")[-1].rstrip(")")
                win_service_name = "SQLSERVERAGENT" if instance == "MSSQLSERVER" else f"SQLAgent${instance}"
            else:
                win_service_name = "SQLSERVERAGENT"

            # 2. Verifier si deja dans l'etat souhaite
            if action == "start" and current_status == "Running":
                return {"success": True, "message": "SQL Server Agent est deja en cours d'execution", "already": True}
            if action == "stop" and current_status == "Stopped":
                return {"success": True, "message": "SQL Server Agent est deja arrete", "already": True}

            # 3. Executer xp_servicecontrol
            # action et win_service_name sont valides (action whitelistee, service_name vient de sys.dm_server_services)
            cursor.execute(f"EXEC xp_servicecontrol N'{action}', N'{win_service_name}'")

            # 4. Attendre que le service change d'etat (max 8 secondes)
            time.sleep(3)
            new_status = check_sql_agent_status(dwh_code)

            action_label = "demarre" if action == "start" else "arrete"
            return {
                "success": True,
                "message": f"SQL Server Agent {action_label} avec succes",
                "new_status": new_status
            }
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Erreur {action} SQL Agent service pour {dwh_code}: {e}")
        return {"success": False, "message": f"Erreur: {str(e)}"}


def check_infrastructure_status(dwh_code: str) -> Dict[str, Any]:
    """
    Verifie l'etat complet de l'infrastructure ETL sur un DWH.
    Retourne un dict avec le statut de chaque composant.
    """
    dwh_info = _get_dwh_db_info(dwh_code)
    result = {
        "dwh_code": dwh_code,
        "dwh_name": dwh_info["nom"],
        "server": dwh_info["serveur_dwh"],
        "database": dwh_info["base_dwh"],
        "components": {}
    }

    try:
        conn = _get_raw_connection(dwh_code)
        cursor = conn.cursor()
        try:
            # 1. Tables DWH metier (verifier quelques tables cles)
            cursor.execute("""
                SELECT name FROM sys.tables
                WHERE name IN ('Collaborateurs','Liste_des_articles','Liste_des_clients',
                               'Entetes_des_ventes','Lignes_des_ventes','Mouvement_stock')
            """)
            dwh_tables = [r.name for r in cursor.fetchall()]
            result["components"]["dwh_tables"] = {
                "status": len(dwh_tables) >= 3,
                "count": len(dwh_tables),
                "label": "Tables metier DWH"
            }

            # 2. Tables ETL (ETL_Sources, SyncControl, ETL_Sync_Log)
            cursor.execute("""
                SELECT name FROM sys.tables
                WHERE name IN ('ETL_Sources','SyncControl','ETL_Sync_Log','ETL_Alerts')
            """)
            etl_tables = [r.name for r in cursor.fetchall()]
            result["components"]["etl_tables"] = {
                "status": len(etl_tables) >= 3,
                "count": len(etl_tables),
                "label": "Tables ETL (Sources, SyncControl, Logs)"
            }

            # 3. Config data dans OptiBoard
            settings = get_central_settings()
            try:
                cursor.execute(f"SELECT COUNT(*) AS cnt FROM [{settings.CENTRAL_DB_NAME}].dbo.ETL_Tables_Config")
                row = cursor.fetchone()
                config_count = row.cnt if row else 0
            except Exception:
                config_count = 0
            result["components"]["config_data"] = {
                "status": config_count >= 20,
                "count": config_count,
                "label": "Configuration tables ETL"
            }

            # 4. Stored Procedure sp_Sync_Generic
            cursor.execute("SELECT name FROM sys.procedures WHERE name = 'sp_Sync_Generic'")
            result["components"]["sp_sync"] = {
                "status": cursor.fetchone() is not None,
                "label": "sp_Sync_Generic"
            }

            # 5. SPs orchestrateurs
            cursor.execute("""
                SELECT name FROM sys.procedures
                WHERE name IN ('SP_ETL_Setup_Source','SP_ETL_Cleanup_Logs','SP_ETL_Reset_SyncControl')
            """)
            sp_orch = [r.name for r in cursor.fetchall()]
            result["components"]["sp_orchestrators"] = {
                "status": len(sp_orch) >= 2,
                "count": len(sp_orch),
                "label": "SPs utilitaires"
            }

            # 6. Vues monitoring
            cursor.execute("""
                SELECT name FROM sys.views WHERE name LIKE 'V_ETL_%'
            """)
            views = [r.name for r in cursor.fetchall()]
            result["components"]["views"] = {
                "status": len(views) >= 3,
                "count": len(views),
                "label": "Vues monitoring"
            }

            # 7. SQL Agent Jobs
            try:
                cursor.execute("""
                    SELECT name FROM msdb.dbo.sysjobs
                    WHERE name IN ('SYNC_GENERIC_MULTI','ETL_Cleanup_Logs')
                """)
                jobs = [r.name for r in cursor.fetchall()]
                result["components"]["jobs"] = {
                    "status": len(jobs) >= 1,
                    "count": len(jobs),
                    "label": "SQL Agent Jobs"
                }
            except Exception:
                result["components"]["jobs"] = {
                    "status": False,
                    "count": 0,
                    "label": "SQL Agent Jobs (acces msdb requis)"
                }

        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        logger.error(f"Erreur check infrastructure {dwh_code}: {e}")
        result["error"] = str(e)

    # Compter les composants OK
    total = len(result.get("components", {}))
    ok = sum(1 for c in result.get("components", {}).values() if c.get("status"))
    result["summary"] = {"total": total, "ok": ok, "complete": ok == total}

    return result


# =====================================================
# LECTURE / PARAMETRAGE / EXECUTION SCRIPTS SQL
# =====================================================

def read_sql_script(script_name: str) -> str:
    """Lit un script SQL depuis le repertoire sql_jobs"""
    if script_name not in ALLOWED_SCRIPTS:
        raise ValueError(f"Script '{script_name}' non autorise. Scripts valides: {ALLOWED_SCRIPTS}")

    file_path = SQL_SCRIPTS_DIR / f"{script_name}.sql"
    if not file_path.exists():
        raise FileNotFoundError(f"Script non trouve: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def parameterize_script(sql_content: str, dwh_code: str, extra_params: dict = None) -> str:
    """
    Remplace les placeholders {DWH_NAME} et {OPTIBOARD_DB} dans le script SQL
    avec les valeurs reelles du DWH et de la base centrale.
    Supporte aussi les parametres supplementaires (ex: Linked Server).
    """
    dwh_info = _get_dwh_db_info(dwh_code)
    settings = get_central_settings()

    sql = sql_content.replace("{DWH_NAME}", dwh_info["base_dwh"])
    sql = sql.replace("{OPTIBOARD_DB}", settings.CENTRAL_DB_NAME)

    # Parametres supplementaires (ex: Linked Server)
    if extra_params:
        for key, value in extra_params.items():
            sql = sql.replace("{" + key + "}", value or "")

    return sql


def preview_script(script_name: str, dwh_code: str, extra_params: dict = None) -> Dict[str, Any]:
    """Retourne le SQL parametrise pour preview avant execution"""
    raw_sql = read_sql_script(script_name)
    dwh_info = _get_dwh_db_info(dwh_code)
    settings = get_central_settings()

    parameterized_sql = parameterize_script(raw_sql, dwh_code, extra_params)

    placeholders = {
        "DWH_NAME": dwh_info["base_dwh"],
        "OPTIBOARD_DB": settings.CENTRAL_DB_NAME
    }
    if extra_params:
        placeholders.update(extra_params)

    return {
        "script_name": script_name,
        "dwh_code": dwh_code,
        "placeholders": placeholders,
        "sql_length": len(parameterized_sql),
        "sql_preview": parameterized_sql
    }


def _check_prerequisites(script_name: str, dwh_code: str) -> Optional[str]:
    """
    Verifie les prerequis avant execution d'un script.
    Retourne un message d'erreur si prerequis manquant, None sinon.
    """
    prereqs = {
        "03_insert_etl_config_data": {
            "description": "Necessite 02_create_etl_config_tables",
            "check": "SELECT COUNT(*) AS cnt FROM sys.tables WHERE name = 'ETL_Tables_Config'",
            "database": "optiboard",
            "expect_min": 1,
            "message": "Table ETL_Tables_Config introuvable. Executez d'abord 02_create_etl_config_tables."
        },
        "04_sp_sync_generic": {
            "description": "Necessite 01_create_dwh_database et 02_create_etl_config_tables",
            "check": "SELECT COUNT(*) AS cnt FROM sys.tables WHERE name IN ('SyncControl','ETL_Sources','ETL_Sync_Log')",
            "database": "dwh",
            "expect_min": 3,
            "message": "Tables ETL (SyncControl, ETL_Sources, ETL_Sync_Log) introuvables dans le DWH. Executez d'abord 02_create_etl_config_tables."
        },
        "05_sp_etl_orchestrators": {
            "description": "Necessite 04_sp_sync_generic",
            "check": "SELECT COUNT(*) AS cnt FROM sys.procedures WHERE name = 'sp_Sync_Generic'",
            "database": "dwh",
            "expect_min": 1,
            "message": "sp_Sync_Generic introuvable. Executez d'abord 04_sp_sync_generic."
        },
        "07_create_sql_agent_jobs": {
            "description": "Necessite 04 + 05 + config",
            "check": "SELECT COUNT(*) AS cnt FROM sys.procedures WHERE name IN ('sp_Sync_Generic','SP_ETL_Cleanup_Logs')",
            "database": "dwh",
            "expect_min": 2,
            "message": "SPs ETL introuvables. Executez d'abord 04_sp_sync_generic et 05_sp_etl_orchestrators."
        },
        "08_monitoring_views": {
            "description": "Necessite 02_create_etl_config_tables (tables ETL dans DWH)",
            "check": "SELECT COUNT(*) AS cnt FROM sys.tables WHERE name IN ('ETL_Sources','SyncControl','ETL_Sync_Log','ETL_Alerts')",
            "database": "dwh",
            "expect_min": 4,
            "message": "Tables ETL (ETL_Sources, SyncControl, ETL_Sync_Log, ETL_Alerts) introuvables dans le DWH. Executez d'abord 02_create_etl_config_tables."
        },
    }

    if script_name not in prereqs:
        return None

    prereq = prereqs[script_name]
    try:
        conn = _get_raw_connection(dwh_code)
        cursor = conn.cursor()
        try:
            if prereq["database"] == "optiboard":
                settings = get_central_settings()
                cursor.execute(f"USE [{settings.CENTRAL_DB_NAME}]")
            # else: DWH is already the default database

            cursor.execute(prereq["check"])
            row = cursor.fetchone()
            count = row.cnt if row else 0

            if count < prereq["expect_min"]:
                return prereq["message"]
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.warning(f"Erreur verification prerequis pour {script_name}: {e}")
        # Ne pas bloquer si la verification echoue
        return None

    return None


def execute_script(script_name: str, dwh_code: str, extra_params: dict = None) -> Dict[str, Any]:
    """
    Execute un script SQL sur le DWH cible.
    - Verifie les prerequis
    - Lit et parametrise le script
    - Split sur GO
    - Execute chaque batch via connexion raw avec autocommit
    - Collecte les messages PRINT
    - Detecte les USE [db] pour suivre le contexte de base
    """
    logger.info(f"Execution script '{script_name}' sur DWH '{dwh_code}'")

    # --- Verification des prerequis ---
    prereq_error = _check_prerequisites(script_name, dwh_code)
    if prereq_error:
        logger.warning(f"Prerequis manquant pour {script_name} sur {dwh_code}: {prereq_error}")
        return {
            "success": False,
            "script_name": script_name,
            "dwh_code": dwh_code,
            "messages": [],
            "errors": [f"Prerequis manquant: {prereq_error}"],
            "batches_total": 0,
            "batches_executed": 0
        }

    raw_sql = read_sql_script(script_name)
    parameterized_sql = parameterize_script(raw_sql, dwh_code, extra_params)
    batches = _split_go_batches(parameterized_sql)
    # Garantir que chaque batch a son propre USE [database]
    # pour eviter les problemes de contexte pyodbc
    batches = _ensure_use_per_batch(batches)

    logger.info(f"Script '{script_name}': {len(batches)} batches apres split+USE-injection")

    messages = []
    errors = []
    batches_ok = 0

    try:
        conn = _get_raw_connection(dwh_code)
        cursor = conn.cursor()

        try:
            for i, batch in enumerate(batches):
                if not batch.strip():
                    continue
                try:
                    cursor.execute(batch)
                    # Collecter les messages PRINT via cursor.messages
                    if hasattr(cursor, 'messages') and cursor.messages:
                        for msg_type, msg_text in cursor.messages:
                            messages.append(f"[Batch {i+1}] {msg_text}")
                        cursor.messages.clear()
                    # Consommer tous les resultats pour eviter les erreurs
                    while cursor.nextset():
                        pass
                    batches_ok += 1
                except pyodbc.Error as e:
                    error_msg = f"[Batch {i+1}/{len(batches)}] {str(e)}"
                    errors.append(error_msg)
                    logger.warning(f"Erreur batch {i+1} du script {script_name}: {e}")
                    # Continuer avec les batches suivants (les scripts sont idempotents)
                    continue

        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        logger.error(f"Erreur connexion pour script {script_name} sur {dwh_code}: {e}")
        return {
            "success": False,
            "script_name": script_name,
            "dwh_code": dwh_code,
            "messages": messages,
            "errors": [f"Erreur de connexion: {str(e)}"],
            "batches_total": len(batches),
            "batches_executed": 0
        }

    success = len(errors) == 0
    logger.info(
        f"Script '{script_name}' termine: {batches_ok}/{len(batches)} batches OK, "
        f"{len(errors)} erreurs"
    )

    return {
        "success": success,
        "script_name": script_name,
        "dwh_code": dwh_code,
        "messages": messages,
        "errors": errors,
        "batches_total": len(batches),
        "batches_executed": batches_ok
    }


def execute_script_on_server(script_name: str, dwh_code: str, extra_params: dict, server_conn: dict) -> Dict[str, Any]:
    """
    Execute un script SQL sur un serveur SPECIFIQUE (pas le DWH).
    Utilise pour le script 06 : creer le Linked Server SUR le serveur Sage.

    server_conn = {"server": "...", "user": "sa", "password": "..."}
    """
    logger.info(f"Execution script '{script_name}' sur serveur '{server_conn['server']}'")

    raw_sql = read_sql_script(script_name)
    parameterized_sql = parameterize_script(raw_sql, dwh_code, extra_params)
    batches = _split_go_batches(parameterized_sql)

    logger.info(f"Script '{script_name}': {len(batches)} batches pour serveur {server_conn['server']}")

    messages = []
    errors = []
    batches_ok = 0

    try:
        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={server_conn['server']};"
            f"DATABASE=master;"
            f"UID={server_conn['user']};"
            f"PWD={server_conn['password']};"
            f"TrustServerCertificate=yes;"
            f"Connection Timeout=15;"
        )
        conn = pyodbc.connect(conn_str, autocommit=True)
        cursor = conn.cursor()

        try:
            for i, batch in enumerate(batches):
                if not batch.strip():
                    continue
                try:
                    cursor.execute(batch)
                    if hasattr(cursor, 'messages') and cursor.messages:
                        for msg_type, msg_text in cursor.messages:
                            messages.append(f"[Batch {i+1}] {msg_text}")
                        cursor.messages.clear()
                    while cursor.nextset():
                        pass
                    batches_ok += 1
                except pyodbc.Error as e:
                    error_msg = f"[Batch {i+1}/{len(batches)}] {str(e)}"
                    errors.append(error_msg)
                    logger.warning(f"Erreur batch {i+1} du script {script_name}: {e}")
                    continue
        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        logger.error(f"Erreur connexion au serveur Sage {server_conn['server']}: {e}")
        return {
            "success": False,
            "script_name": script_name,
            "dwh_code": dwh_code,
            "messages": messages,
            "errors": [f"Erreur connexion au serveur Sage ({server_conn['server']}): {str(e)}"],
            "batches_total": len(batches),
            "batches_executed": 0
        }

    success = len(errors) == 0
    logger.info(
        f"Script '{script_name}' sur {server_conn['server']}: {batches_ok}/{len(batches)} batches OK, "
        f"{len(errors)} erreurs"
    )

    return {
        "success": success,
        "script_name": script_name,
        "dwh_code": dwh_code,
        "messages": messages,
        "errors": errors,
        "batches_total": len(batches),
        "batches_executed": batches_ok
    }


# =====================================================
# GESTION DES SOURCES ETL
# =====================================================

def get_etl_sources(dwh_code: str) -> List[Dict[str, Any]]:
    """Liste les sources ETL enregistrees dans le DWH"""
    try:
        return execute_dwh_query(
            dwh_code,
            "SELECT source_id, source_code, source_caption, db_id, "
            "server_name, database_name, is_linked_server, linked_server_name, "
            "is_active, created_at, updated_at "
            "FROM ETL_Sources ORDER BY source_code",
            use_cache=False
        )
    except Exception as e:
        logger.warning(f"Erreur lecture ETL_Sources pour {dwh_code}: {e}")
        return []


def add_etl_source(dwh_code: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Ajoute une source Sage via SP_ETL_Setup_Source"""
    try:
        conn = _get_raw_connection(dwh_code)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                EXEC dbo.SP_ETL_Setup_Source
                    @SourceCode       = ?,
                    @SourceCaption    = ?,
                    @DbId             = ?,
                    @ServerName       = ?,
                    @DatabaseName     = ?,
                    @IsLinkedServer   = ?,
                    @LinkedServerName = ?
            """, (
                data["source_code"],
                data["source_caption"],
                data["db_id"],
                data["server_name"],
                data["database_name"],
                data.get("is_linked_server", False),
                data.get("linked_server_name")
            ))
            # Collecter les messages PRINT
            messages = []
            if hasattr(cursor, 'messages') and cursor.messages:
                for _, msg in cursor.messages:
                    messages.append(msg)
            return {"success": True, "message": "Source ajoutee", "details": messages}
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Erreur ajout source {dwh_code}: {e}")
        return {"success": False, "message": str(e)}


def update_etl_source(dwh_code: str, source_code: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Met a jour une source Sage existante via SP_ETL_Setup_Source (upsert)"""
    try:
        conn = _get_raw_connection(dwh_code)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                EXEC dbo.SP_ETL_Setup_Source
                    @SourceCode       = ?,
                    @SourceCaption    = ?,
                    @DbId             = ?,
                    @ServerName       = ?,
                    @DatabaseName     = ?,
                    @IsLinkedServer   = ?,
                    @LinkedServerName = ?
            """, (
                source_code,
                data["source_caption"],
                data["db_id"],
                data["server_name"],
                data["database_name"],
                data.get("is_linked_server", False),
                data.get("linked_server_name") or None
            ))
            messages = []
            if hasattr(cursor, 'messages') and cursor.messages:
                for _, msg in cursor.messages:
                    messages.append(msg)
            return {"success": True, "message": "Source mise a jour", "details": messages}
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Erreur update source {dwh_code}/{source_code}: {e}")
        return {"success": False, "message": str(e)}


def delete_etl_source(dwh_code: str, source_code: str) -> Dict[str, Any]:
    """Supprime une source ETL"""
    try:
        rows = execute_dwh_write(
            dwh_code,
            "DELETE FROM ETL_Sources WHERE source_code = ?",
            (source_code,)
        )
        return {"success": rows > 0, "rows_affected": rows}
    except Exception as e:
        return {"success": False, "message": str(e)}


def toggle_source(dwh_code: str, source_code: str) -> Dict[str, Any]:
    """Active/desactive une source ETL"""
    try:
        rows = execute_dwh_write(
            dwh_code,
            "UPDATE ETL_Sources SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END, "
            "updated_at = GETDATE() WHERE source_code = ?",
            (source_code,)
        )
        return {"success": rows > 0, "rows_affected": rows}
    except Exception as e:
        return {"success": False, "message": str(e)}


def test_source_connection(dwh_code: str, source_code: str) -> Dict[str, Any]:
    """Teste la connexion vers une source Sage"""
    sources = execute_dwh_query(
        dwh_code,
        "SELECT server_name, database_name, is_linked_server, linked_server_name "
        "FROM ETL_Sources WHERE source_code = ?",
        (source_code,),
        use_cache=False
    )
    if not sources:
        return {"success": False, "message": f"Source '{source_code}' non trouvee"}

    src = sources[0]

    if src["is_linked_server"]:
        # Tester via le linked server
        try:
            conn = _get_raw_connection(dwh_code)
            cursor = conn.cursor()
            try:
                ls_name = src["linked_server_name"]
                db_name = src["database_name"]
                cursor.execute(f"SELECT TOP 1 1 AS test FROM [{ls_name}].[{db_name}].sys.objects")
                return {"success": True, "message": f"Linked Server '{ls_name}' accessible"}
            finally:
                cursor.close()
                conn.close()
        except Exception as e:
            return {"success": False, "message": f"Linked Server inaccessible: {str(e)}"}
    else:
        # Tester connexion directe au serveur Sage
        try:
            # Utiliser les memes credentials que le DWH (meme serveur)
            dwh_info = _get_dwh_db_info(dwh_code)
            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={src['server_name']};"
                f"DATABASE={src['database_name']};"
                f"UID={dwh_info['user_dwh']};"
                f"PWD={dwh_info['password_dwh']};"
                f"TrustServerCertificate=yes;"
                f"Connection Timeout=10;"
            )
            conn = pyodbc.connect(conn_str)
            conn.close()
            return {"success": True, "message": f"Connexion a '{src['database_name']}' reussie"}
        except Exception as e:
            return {"success": False, "message": f"Connexion echouee: {str(e)}"}


# =====================================================
# GESTION DES LINKED SERVERS
# =====================================================

def get_linked_servers(dwh_code: str) -> List[Dict[str, Any]]:
    """Liste les Linked Servers existants sur le serveur DWH"""
    try:
        conn = _get_raw_connection(dwh_code)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT
                    s.name AS linked_server_name,
                    s.data_source AS server_address,
                    s.provider AS provider,
                    s.product AS product,
                    s.modify_date
                FROM sys.servers s
                WHERE s.is_linked = 1
                ORDER BY s.name
            """)
            cols = [c[0] for c in cursor.description]
            rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
            return rows
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Erreur get_linked_servers: {e}")
        return []


def drop_linked_server(dwh_code: str, linked_server_name: str) -> Dict[str, Any]:
    """Supprime un Linked Server"""
    try:
        conn = _get_raw_connection(dwh_code)
        cursor = conn.cursor()
        try:
            # Verifier que le Linked Server existe
            cursor.execute("SELECT 1 FROM sys.servers WHERE name = ? AND is_linked = 1", (linked_server_name,))
            if not cursor.fetchone():
                return {"success": False, "message": f"Linked Server '{linked_server_name}' non trouve"}

            cursor.execute(f"EXEC sp_dropserver @server = ?, @droplogins = 'droplogins'", (linked_server_name,))
            conn.commit()
            return {"success": True, "message": f"Linked Server '{linked_server_name}' supprime"}
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        return {"success": False, "message": str(e)}


# =====================================================
# GESTION DES JOBS SQL AGENT
# =====================================================

def get_jobs_status(dwh_code: str) -> List[Dict[str, Any]]:
    """Recupere le statut des SQL Agent Jobs ETL (sur le serveur Sage)"""
    try:
        conn = _get_sage_connection(dwh_code)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT
                    j.name AS job_name,
                    j.enabled,
                    j.description,
                    j.date_created,
                    CASE
                        WHEN ja.run_requested_date IS NOT NULL
                             AND ja.stop_execution_date IS NULL THEN 'Running'
                        WHEN j.enabled = 0 THEN 'Disabled'
                        ELSE 'Idle'
                    END AS current_status,
                    ja.run_requested_date AS last_run_requested,
                    jh.run_date AS last_run_date,
                    jh.run_time AS last_run_time,
                    jh.run_duration AS last_run_duration,
                    CASE jh.run_status
                        WHEN 0 THEN 'Failed'
                        WHEN 1 THEN 'Succeeded'
                        WHEN 2 THEN 'Retry'
                        WHEN 3 THEN 'Cancelled'
                        WHEN 4 THEN 'In Progress'
                    END AS last_run_status
                FROM msdb.dbo.sysjobs j
                LEFT JOIN msdb.dbo.sysjobactivity ja
                    ON j.job_id = ja.job_id
                    AND ja.session_id = (SELECT MAX(session_id) FROM msdb.dbo.syssessions)
                LEFT JOIN (
                    SELECT job_id, run_date, run_time, run_duration, run_status,
                           ROW_NUMBER() OVER (PARTITION BY job_id ORDER BY run_date DESC, run_time DESC) AS rn
                    FROM msdb.dbo.sysjobhistory
                    WHERE step_id = 0
                ) jh ON j.job_id = jh.job_id AND jh.rn = 1
                WHERE j.name IN ('SYNC_GENERIC_MULTI', 'ETL_Cleanup_Logs')
                ORDER BY j.name
            """)
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.warning(f"Erreur lecture jobs status {dwh_code}: {e}")
        return []


def start_job(dwh_code: str, job_name: str) -> Dict[str, Any]:
    """Demarre un SQL Agent Job (sur le serveur Sage)"""
    if job_name not in ("SYNC_GENERIC_MULTI", "ETL_Cleanup_Logs"):
        return {"success": False, "message": f"Job '{job_name}' non autorise"}
    try:
        conn = _get_sage_connection(dwh_code)
        cursor = conn.cursor()
        try:
            try:
                cursor.execute("EXEC msdb.dbo.sp_start_job @job_name = ?", (job_name,))
            except pyodbc.Error as e:
                # Erreur 14256 : pas de serveur de travail defini → associer et reessayer
                if "14256" in str(e) or "sp_add_jobserver" in str(e) or "14262" in str(e):
                    logger.info(f"Job '{job_name}' sans serveur cible, execution sp_add_jobserver (local)...")
                    cursor.execute(
                        "EXEC msdb.dbo.sp_add_jobserver @job_name = ?, @server_name = N'(local)'",
                        (job_name,)
                    )
                    cursor.execute("EXEC msdb.dbo.sp_start_job @job_name = ?", (job_name,))
                else:
                    raise
            return {"success": True, "message": f"Job '{job_name}' demarre"}
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        return {"success": False, "message": str(e)}


def stop_job(dwh_code: str, job_name: str) -> Dict[str, Any]:
    """Arrete un SQL Agent Job (sur le serveur Sage)"""
    if job_name not in ("SYNC_GENERIC_MULTI", "ETL_Cleanup_Logs"):
        return {"success": False, "message": f"Job '{job_name}' non autorise"}
    try:
        conn = _get_sage_connection(dwh_code)
        cursor = conn.cursor()
        try:
            cursor.execute("EXEC msdb.dbo.sp_stop_job @job_name = ?", (job_name,))
            return {"success": True, "message": f"Job '{job_name}' arrete"}
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        return {"success": False, "message": str(e)}


# =====================================================
# MONITORING
# =====================================================

def get_sync_control(dwh_code: str) -> List[Dict[str, Any]]:
    """Recupere le resume SyncControl"""
    try:
        return execute_dwh_query(
            dwh_code,
            "SELECT TableName, LastSyncDate, LastStatus, LastSyncDuration, "
            "TotalInserted, TotalUpdated, TotalDeleted, "
            "LEFT(LastError, 300) AS LastError, "
            "DATEDIFF(MINUTE, LastSyncDate, GETDATE()) AS MinutesSince "
            "FROM SyncControl ORDER BY TableName",
            use_cache=False
        )
    except Exception as e:
        logger.warning(f"Erreur lecture SyncControl {dwh_code}: {e}")
        return []


def get_sync_logs(dwh_code: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Recupere les logs de synchronisation recents"""
    try:
        return execute_dwh_query(
            dwh_code,
            f"SELECT TOP ({limit}) id, sync_control_name, source_code, table_name, "
            "sync_type, started_at, completed_at, status, "
            "rows_extracted, rows_inserted, rows_updated, rows_deleted, "
            "duration_seconds, LEFT(error_message, 300) AS error_message "
            "FROM ETL_Sync_Log ORDER BY started_at DESC",
            use_cache=False
        )
    except Exception as e:
        logger.warning(f"Erreur lecture ETL_Sync_Log {dwh_code}: {e}")
        return []


def get_etl_tables_config() -> List[Dict[str, Any]]:
    """Recupere la configuration des tables ETL depuis OptiBoard"""
    try:
        return execute_central_query(
            "SELECT config_id, table_name, target_table, join_column, "
            "filter_column, sync_type, timestamp_column, priority, "
            "sort_order, delete_orphans, is_active, "
            "CASE WHEN source_query IS NOT NULL AND source_query NOT LIKE 'TODO%' "
            "THEN 'OK' ELSE 'TODO' END AS query_status "
            "FROM ETL_Tables_Config ORDER BY sort_order, table_name",
            use_cache=False
        )
    except Exception as e:
        logger.warning(f"Erreur lecture ETL_Tables_Config: {e}")
        return []


def reset_sync_control(dwh_code: str, target_table: str = None) -> Dict[str, Any]:
    """
    Reset SyncControl pour forcer un full sync.
    Si target_table est fourni, reset seulement cette table.
    Sinon, reset toutes les entrees.
    """
    try:
        if target_table:
            rows = execute_dwh_write(
                dwh_code,
                "UPDATE SyncControl SET LastSyncDate = NULL WHERE TableName LIKE ?",
                (f"%{target_table}",)
            )
        else:
            rows = execute_dwh_write(
                dwh_code,
                "UPDATE SyncControl SET LastSyncDate = NULL"
            )
        return {"success": True, "rows_reset": rows}
    except Exception as e:
        return {"success": False, "message": str(e)}


def cleanup_etl_logs(dwh_code: str, retention_days: int = 0) -> Dict[str, Any]:
    """
    Purge les logs ETL via SP_ETL_Cleanup_Logs.
    retention_days=0 supprime TOUS les logs.
    """
    try:
        conn = _get_raw_connection(dwh_code)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "EXEC dbo.SP_ETL_Cleanup_Logs @RetentionDays = ?",
                (retention_days,)
            )
            messages = []
            if hasattr(cursor, 'messages') and cursor.messages:
                for _, msg in cursor.messages:
                    messages.append(msg)
                cursor.messages.clear()
            while cursor.nextset():
                pass
            logger.info(f"Cleanup logs {dwh_code} (retention={retention_days}j): {messages}")
            return {"success": True, "messages": messages}
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Erreur cleanup logs {dwh_code}: {e}")
        return {"success": False, "message": str(e)}
