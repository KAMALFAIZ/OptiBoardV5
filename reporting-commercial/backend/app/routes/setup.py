"""Routes pour la configuration initiale de l'application - Multi-Tenant"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import pyodbc
import hashlib
from pathlib import Path

router = APIRouter(prefix="/api/setup", tags=["setup"])

# Chemin vers les scripts SQL
SQL_SCRIPTS_PATH = Path(__file__).parent.parent.parent / "sql"


class AIConfigRequest(BaseModel):
    """Schema pour la configuration du module IA"""
    AI_PROVIDER: str = ""
    AI_MODEL: str = ""
    AI_API_KEY: str = ""
    AI_OLLAMA_URL: str = "http://localhost:11434"
    AI_MAX_TOKENS: int = 4096
    AI_TEMPERATURE: float = 0.2
    AI_ENABLED: bool = False
    AI_RATE_LIMIT_PER_MINUTE: int = 20


class DatabaseConfig(BaseModel):
    """Schema pour la configuration de la base de donnees centrale"""
    server: str
    database: str = "OptiBoard_SaaS"  # Base centrale par defaut
    username: str
    password: str
    driver: str = "{ODBC Driver 17 for SQL Server}"
    app_name: Optional[str] = "OptiBoard"
    # Option pour creer un premier DWH client
    create_first_dwh: bool = False
    first_dwh_code: Optional[str] = None
    first_dwh_name: Optional[str] = None


class TestConnectionRequest(BaseModel):
    """Schema pour tester une connexion"""
    server: str
    database: str
    username: str
    password: str
    driver: str = "{ODBC Driver 17 for SQL Server}"


@router.get("/ai-config")
async def get_ai_config():
    """Retourne la configuration IA actuelle (cle API masquee)."""
    from ..config import reload_settings
    s = reload_settings()  # Toujours relire le .env
    return {
        "success": True,
        "config": {
            "AI_PROVIDER": s.AI_PROVIDER,
            "AI_MODEL": s.AI_MODEL,
            "AI_API_KEY": "***" if s.AI_API_KEY else "",
            "AI_OLLAMA_URL": s.AI_OLLAMA_URL,
            "AI_MAX_TOKENS": s.AI_MAX_TOKENS,
            "AI_TEMPERATURE": s.AI_TEMPERATURE,
            "AI_ENABLED": s.AI_ENABLED,
            "AI_RATE_LIMIT_PER_MINUTE": s.AI_RATE_LIMIT_PER_MINUTE,
        }
    }


@router.post("/ai-config")
async def save_ai_config(config: AIConfigRequest):
    """Sauvegarde la configuration IA dans le .env."""
    from ..config import save_env_config, reload_settings
    config_dict = config.model_dump()
    # Convertir le bool en string pour le .env
    config_dict["AI_ENABLED"] = str(config_dict["AI_ENABLED"])
    # Ne pas ecraser la cle API si masquee
    if not config_dict.get("AI_API_KEY") or config_dict["AI_API_KEY"] == "***":
        config_dict.pop("AI_API_KEY", None)
    save_env_config(config_dict)
    reload_settings()
    return {"success": True, "message": "Configuration IA sauvegardee"}


@router.get("/status")
async def get_setup_status():
    """
    Verifie si l'application est configuree.
    Retourne le statut de configuration pour rediriger vers le setup si necessaire.
    """
    from ..config import reload_settings

    # Toujours recharger pour avoir les valeurs actuelles du fichier .env
    settings = reload_settings()

    return {
        "configured": settings.is_configured,
        "app_name": settings.APP_NAME,
        "server": settings.DB_SERVER if settings.is_configured else None,
        "database": settings.DB_NAME if settings.is_configured else None,
        "username": settings.DB_USER if settings.is_configured else None,
        "password": settings.DB_PASSWORD if settings.is_configured else None
    }


@router.post("/test-connection")
async def test_connection(config: TestConnectionRequest):
    """
    Teste une connexion a la base de donnees sans la sauvegarder.
    Teste d'abord les identifiants (sans base), puis verifie si la base existe.
    """
    try:
        # ETAPE 1: Tester la connexion au serveur SANS specifier de base
        # Cela permet de valider le serveur et les identifiants
        conn_str_server = (
            f"DRIVER={config.driver};"
            f"SERVER={config.server};"
            f"UID={config.username};"
            f"PWD={config.password};"
            f"TrustServerCertificate=yes"
        )

        try:
            conn = pyodbc.connect(conn_str_server, timeout=10)
        except pyodbc.Error as e:
            error_msg = str(e)
            if "Login failed" in error_msg:
                if "18456" in error_msg:
                    return {
                        "success": False,
                        "error": "Echec d'authentification SQL Server. Verifiez: 1) Le mot de passe est correct, 2) L'authentification SQL Server est activee (pas seulement Windows Auth), 3) Le compte 'sa' est actif"
                    }
                return {"success": False, "error": "Identifiants incorrects (login/password)"}
            elif "server was not found" in error_msg or "Network" in error_msg:
                return {"success": False, "error": f"Serveur '{config.server}' inaccessible. Verifiez le nom/IP et que SQL Server est demarre."}
            elif "ODBC Driver" in error_msg:
                return {"success": False, "error": "Driver ODBC 17 non installe. Telechargez-le depuis Microsoft."}
            elif "TCP Provider" in error_msg:
                return {"success": False, "error": "Connexion TCP impossible. Verifiez que SQL Server accepte les connexions TCP/IP."}
            else:
                return {"success": False, "error": f"Erreur serveur: {error_msg}"}

        cursor = conn.cursor()

        # Recuperer la version du serveur
        cursor.execute("SELECT @@VERSION AS version")
        version_row = cursor.fetchone()
        server_version = version_row[0] if version_row else "Unknown"

        # ETAPE 2: Verifier si la base de donnees existe
        cursor.execute("""
            SELECT name FROM sys.databases
            WHERE name = ?
        """, (config.database,))
        db_exists = cursor.fetchone() is not None

        cursor.close()
        conn.close()

        if not db_exists:
            # La base n'existe pas - on propose de la creer
            return {
                "success": True,
                "message": "Connexion au serveur reussie",
                "database_exists": False,
                "server_info": {
                    "version": server_version[:100] + "..." if len(server_version) > 100 else server_version,
                    "connected": True
                },
                "warning": f"La base '{config.database}' n'existe pas. Elle sera creee automatiquement."
            }

        # ETAPE 3: Se connecter a la base pour compter les tables
        conn_str_db = (
            f"DRIVER={config.driver};"
            f"SERVER={config.server};"
            f"DATABASE={config.database};"
            f"UID={config.username};"
            f"PWD={config.password};"
            f"TrustServerCertificate=yes"
        )

        conn = pyodbc.connect(conn_str_db, timeout=10)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_TYPE = 'BASE TABLE'
        """)
        table_count = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        return {
            "success": True,
            "message": "Connexion reussie",
            "database_exists": True,
            "server_info": {
                "version": server_version[:100] + "..." if len(server_version) > 100 else server_version,
                "table_count": table_count,
                "connected": True
            }
        }

    except pyodbc.Error as e:
        error_msg = str(e)
        return {"success": False, "error": f"Erreur: {error_msg}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/configure")
async def configure_database(config: DatabaseConfig):
    """
    Sauvegarde la configuration de la base de donnees.
    Cree la base si elle n'existe pas.
    """
    from ..config import save_env_config, reload_settings

    try:
        # D'abord tester la connexion
        test_result = await test_connection(TestConnectionRequest(
            server=config.server,
            database=config.database,
            username=config.username,
            password=config.password,
            driver=config.driver
        ))

        if not test_result["success"]:
            raise HTTPException(
                status_code=400,
                detail=f"Impossible de se connecter: {test_result.get('error', 'Erreur inconnue')}"
            )

        # Si la base n'existe pas, la creer
        if test_result.get("database_exists") == False:
            try:
                conn_str = (
                    f"DRIVER={config.driver};"
                    f"SERVER={config.server};"
                    f"UID={config.username};"
                    f"PWD={config.password};"
                    f"TrustServerCertificate=yes"
                )
                conn = pyodbc.connect(conn_str, autocommit=True)
                cursor = conn.cursor()
                cursor.execute(f"CREATE DATABASE [{config.database}]")
                cursor.close()
                conn.close()
                print(f"[SETUP] Base de donnees '{config.database}' creee avec succes")
            except Exception as create_error:
                raise HTTPException(
                    status_code=400,
                    detail=f"Impossible de creer la base '{config.database}': {str(create_error)}"
                )

        # Sauvegarder la configuration
        env_config = {
            "DB_SERVER": config.server,
            "DB_NAME": config.database,
            "DB_USER": config.username,
            "DB_PASSWORD": config.password,
            "DB_DRIVER": config.driver,
            "APP_NAME": config.app_name or "OptiBoard - Reporting Commercial"
        }

        save_env_config(env_config)

        # Recharger les settings (config.py ET config_multitenant.py — deux caches independants)
        settings = reload_settings()
        from ..config_multitenant import reload_central_settings
        reload_central_settings()

        # Initialiser TOUTES les tables APP automatiquement
        init_result = await init_all_tables()

        return {
            "success": True,
            "message": "Configuration sauvegardee et tables initialisees",
            "configured": settings.is_configured,
            "app_name": settings.APP_NAME,
            "tables_created": init_result.get("created_tables", []),
            "admin_credentials": init_result.get("admin_credentials")
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/app-name")
async def get_app_name():
    """Recupere le nom de l'application depuis APP_Settings en base"""
    from ..database_unified import execute_central
    try:
        result = execute_central(
            "SELECT setting_value FROM APP_Settings WHERE setting_key = 'app_name' AND dwh_code IS NULL",
            use_cache=False
        )
        name = result[0]['setting_value'] if result else None
        # Fallback sur le .env si pas en base
        if not name:
            from ..config import get_settings
            name = get_settings().APP_NAME
        return {"success": True, "app_name": name}
    except Exception as e:
        # Fallback sur le .env en cas d'erreur
        from ..config import get_settings
        return {"success": True, "app_name": get_settings().APP_NAME}


class UpdateAppNameRequest(BaseModel):
    app_name: str = "OptiBoard - Reporting Commercial"


@router.put("/app-name")
async def update_app_name_db(req: UpdateAppNameRequest):
    """Sauvegarde le nom de l'application dans APP_Settings en base (pas .env)"""
    from ..database_unified import central_cursor as get_db_cursor
    new_name = req.app_name or "OptiBoard - Reporting Commercial"
    try:
        with get_db_cursor() as cursor:
            # Verifier si le setting existe
            cursor.execute("SELECT COUNT(*) FROM APP_Settings WHERE setting_key = 'app_name' AND dwh_code IS NULL")
            count = cursor.fetchone()[0]
            if count > 0:
                cursor.execute(
                    "UPDATE APP_Settings SET setting_value = ?, date_modification = GETDATE() WHERE setting_key = 'app_name' AND dwh_code IS NULL",
                    (new_name,)
                )
            else:
                cursor.execute(
                    "INSERT INTO APP_Settings (dwh_code, setting_key, setting_value, setting_type, description) VALUES (NULL, 'app_name', ?, 'string', 'Nom de l application')",
                    (new_name,)
                )
        return {"success": True, "app_name": new_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/databases")
async def list_databases(server: str, username: str, password: str, driver: str = "{ODBC Driver 17 for SQL Server}"):
    """
    Liste les bases de donnees disponibles sur un serveur.
    Utile pour proposer une liste deroulante a l'utilisateur.
    """
    try:
        # Connexion au serveur sans specifier de base
        conn_str = (
            f"DRIVER={driver};"
            f"SERVER={server};"
            f"UID={username};"
            f"PWD={password};"
            f"TrustServerCertificate=yes"
        )

        conn = pyodbc.connect(conn_str, timeout=10)
        cursor = conn.cursor()

        # Lister les bases de donnees
        cursor.execute("""
            SELECT name FROM sys.databases
            WHERE name NOT IN ('master', 'tempdb', 'model', 'msdb')
            AND state_desc = 'ONLINE'
            ORDER BY name
        """)

        databases = [row[0] for row in cursor.fetchall()]

        cursor.close()
        conn.close()

        return {
            "success": True,
            "databases": databases
        }

    except Exception as e:
        return {"success": False, "error": str(e), "databases": []}


@router.post("/init-tables")
async def initialize_tables():
    """
    Initialise les tables systeme (APP_Users, APP_DWH, etc.)
    A appeler apres la configuration initiale.
    """
    from ..config import get_settings

    settings = get_settings()
    if not settings.is_configured:
        raise HTTPException(status_code=400, detail="Application non configuree")

    try:
        from .users import init_tables
        success = init_tables()

        if success:
            return {"success": True, "message": "Tables systeme initialisees"}
        else:
            return {"success": False, "error": "Erreur lors de l'initialisation"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/check-tables")
async def check_system_tables():
    """
    Verifie si les tables systeme existent.
    """
    from ..config import reload_settings
    from ..database_unified import execute_central

    # Recharger pour avoir les valeurs actuelles
    settings = reload_settings()
    if not settings.is_configured:
        return {"configured": False, "tables": {}}

    try:
        # Verifier chaque table systeme
        tables_to_check = [
            "APP_Users",
            "APP_Societes",
            "APP_UserSocietes",
            "APP_UserPages",
            "APP_DWH",
            "APP_UserDWH",
            "APP_Dashboards",
            "APP_DataSources",
            "APP_GridViews",
            "APP_Pivots",
            "APP_Menus",
            "APP_ReportSchedules",
            "APP_EmailConfig"
        ]

        tables_status = {}
        for table in tables_to_check:
            result = execute_central(
                f"SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = ?",
                (table,),
                use_cache=False
            )
            tables_status[table] = result[0]['cnt'] > 0 if result else False

        return {
            "configured": True,
            "tables": tables_status,
            "all_tables_exist": all(tables_status.values())
        }

    except Exception as e:
        return {"configured": True, "error": str(e), "tables": {}}


@router.post("/init-all-tables")
async def init_all_tables():
    """
    Initialise TOUTES les tables APP dans la base centrale OptiBoard_SaaS.
    Utilise le nouveau schema multi-tenant.
    """
    from ..config import reload_settings

    settings = reload_settings()
    if not settings.is_configured:
        raise HTTPException(status_code=400, detail="Application non configuree")

    return await init_central_database_tables()


async def init_central_database_tables():
    """
    Cree toutes les tables de la base centrale OptiBoard_SaaS.
    Architecture multi-tenant complete.
    """
    from ..config import reload_settings
    from contextlib import contextmanager

    # Forcer le rechargement des settings
    settings = reload_settings()

    @contextmanager
    def get_fresh_cursor():
        """Obtenir un cursor avec connexion fraiche"""
        conn_str = (
            f"DRIVER={settings.DB_DRIVER};"
            f"SERVER={settings.DB_SERVER};"
            f"DATABASE={settings.DB_NAME};"
            f"UID={settings.DB_USER};"
            f"PWD={settings.DB_PASSWORD};"
            f"TrustServerCertificate=yes"
        )
        conn = pyodbc.connect(conn_str, timeout=30)
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()

    created_tables = []
    errors = []

    try:
        with get_fresh_cursor() as cursor:
            # =====================================================
            # SECTION 1: GESTION DES CLIENTS (DWH)
            # =====================================================

            # APP_DWH - Table principale des clients
            try:
                cursor.execute("""
                    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_DWH' AND xtype='U')
                    CREATE TABLE APP_DWH (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        code VARCHAR(50) UNIQUE NOT NULL,
                        nom NVARCHAR(200) NOT NULL,
                        raison_sociale NVARCHAR(300),
                        adresse NVARCHAR(500),
                        ville NVARCHAR(100),
                        pays NVARCHAR(100) DEFAULT 'Maroc',
                        telephone VARCHAR(50),
                        email VARCHAR(200),
                        logo_url NVARCHAR(500),
                        serveur_dwh VARCHAR(200) NOT NULL,
                        base_dwh VARCHAR(100) NOT NULL,
                        user_dwh VARCHAR(100) NOT NULL,
                        password_dwh VARCHAR(200) NOT NULL,
                        actif BIT DEFAULT 1,
                        date_creation DATETIME DEFAULT GETDATE(),
                        date_modification DATETIME DEFAULT GETDATE(),
                        created_by INT NULL
                    )
                """)
                created_tables.append("APP_DWH")
            except Exception as e:
                errors.append(f"APP_DWH: {str(e)}")

            # APP_DWH_Sources - Bases Sage par DWH
            try:
                cursor.execute("""
                    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_DWH_Sources' AND xtype='U')
                    CREATE TABLE APP_DWH_Sources (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        dwh_code VARCHAR(50) NOT NULL,
                        code_societe VARCHAR(50) NOT NULL,
                        nom_societe NVARCHAR(200) NOT NULL,
                        serveur_sage VARCHAR(200) NOT NULL,
                        base_sage VARCHAR(100) NOT NULL,
                        user_sage VARCHAR(100) NOT NULL,
                        password_sage VARCHAR(200) NOT NULL,
                        etl_enabled BIT DEFAULT 1,
                        etl_mode VARCHAR(20) DEFAULT 'incremental',
                        etl_schedule VARCHAR(50) DEFAULT '*/15 * * * *',
                        last_sync DATETIME NULL,
                        last_sync_status VARCHAR(20) NULL,
                        last_sync_message NVARCHAR(MAX) NULL,
                        actif BIT DEFAULT 1,
                        date_creation DATETIME DEFAULT GETDATE(),
                        CONSTRAINT UQ_DWH_Source UNIQUE (dwh_code, code_societe)
                    )
                """)
                created_tables.append("APP_DWH_Sources")
            except Exception as e:
                errors.append(f"APP_DWH_Sources: {str(e)}")

            # =====================================================
            # SECTION 2: GESTION DES UTILISATEURS
            # =====================================================

            # APP_Users
            try:
                cursor.execute("""
                    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Users' AND xtype='U')
                    CREATE TABLE APP_Users (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        username VARCHAR(50) UNIQUE NOT NULL,
                        password_hash VARCHAR(64) NOT NULL,
                        nom NVARCHAR(100) NOT NULL,
                        prenom NVARCHAR(100) NOT NULL,
                        email VARCHAR(200),
                        telephone VARCHAR(50),
                        fonction NVARCHAR(100),
                        role_global VARCHAR(20) DEFAULT 'user',
                        actif BIT DEFAULT 1,
                        date_creation DATETIME DEFAULT GETDATE(),
                        derniere_connexion DATETIME,
                        avatar_url NVARCHAR(500)
                    )
                """)
                created_tables.append("APP_Users")
            except Exception as e:
                errors.append(f"APP_Users: {str(e)}")

            # APP_UserDWH - Niveau 1: Acces DWH
            try:
                cursor.execute("""
                    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_UserDWH' AND xtype='U')
                    CREATE TABLE APP_UserDWH (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        user_id INT NOT NULL,
                        dwh_code VARCHAR(50) NOT NULL,
                        role_dwh VARCHAR(30) DEFAULT 'user',
                        is_default BIT DEFAULT 0,
                        date_creation DATETIME DEFAULT GETDATE(),
                        CONSTRAINT UQ_UserDWH UNIQUE (user_id, dwh_code)
                    )
                """)
                created_tables.append("APP_UserDWH")
            except Exception as e:
                errors.append(f"APP_UserDWH: {str(e)}")

            # APP_UserSocietes - Niveau 2: Acces Societes
            try:
                cursor.execute("""
                    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_UserSocietes' AND xtype='U')
                    CREATE TABLE APP_UserSocietes (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        user_id INT NOT NULL,
                        dwh_code VARCHAR(50) NOT NULL,
                        societe_code VARCHAR(50) NOT NULL,
                        can_view BIT DEFAULT 1,
                        can_export BIT DEFAULT 1,
                        can_edit BIT DEFAULT 0,
                        date_creation DATETIME DEFAULT GETDATE(),
                        CONSTRAINT UQ_UserSociete UNIQUE (user_id, dwh_code, societe_code)
                    )
                """)
                created_tables.append("APP_UserSocietes")
            except Exception as e:
                errors.append(f"APP_UserSocietes: {str(e)}")

            # APP_UserPages
            try:
                cursor.execute("""
                    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_UserPages' AND xtype='U')
                    CREATE TABLE APP_UserPages (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        user_id INT NOT NULL,
                        page_code VARCHAR(50) NOT NULL
                    )
                """)
                created_tables.append("APP_UserPages")
            except Exception as e:
                errors.append(f"APP_UserPages: {str(e)}")

            # APP_UserMenus
            try:
                cursor.execute("""
                    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_UserMenus' AND xtype='U')
                    CREATE TABLE APP_UserMenus (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        user_id INT NOT NULL,
                        menu_id INT NOT NULL,
                        can_view BIT DEFAULT 1,
                        can_export BIT DEFAULT 1
                    )
                """)
                created_tables.append("APP_UserMenus")
            except Exception as e:
                errors.append(f"APP_UserMenus: {str(e)}")

            # =====================================================
            # SECTION 3: TEMPLATES GLOBAUX
            # =====================================================

            # APP_DataSources_Templates
            try:
                cursor.execute("""
                    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_DataSources_Templates' AND xtype='U')
                    CREATE TABLE APP_DataSources_Templates (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        nom NVARCHAR(200) NOT NULL,
                        code VARCHAR(100) UNIQUE NOT NULL,
                        type VARCHAR(50) NOT NULL DEFAULT 'query',
                        category VARCHAR(50),
                        description NVARCHAR(500),
                        query_template NVARCHAR(MAX),
                        parameters NVARCHAR(MAX),
                        is_system BIT DEFAULT 1,
                        actif BIT DEFAULT 1,
                        date_creation DATETIME DEFAULT GETDATE()
                    )
                """)
                created_tables.append("APP_DataSources_Templates")
            except Exception as e:
                errors.append(f"APP_DataSources_Templates: {str(e)}")

            # APP_Dashboards_Templates
            try:
                cursor.execute("""
                    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Dashboards_Templates' AND xtype='U')
                    CREATE TABLE APP_Dashboards_Templates (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        nom NVARCHAR(200) NOT NULL,
                        code VARCHAR(100) UNIQUE NOT NULL,
                        description NVARCHAR(500),
                        config NVARCHAR(MAX),
                        widgets NVARCHAR(MAX),
                        category VARCHAR(50),
                        is_system BIT DEFAULT 1,
                        actif BIT DEFAULT 1,
                        date_creation DATETIME DEFAULT GETDATE()
                    )
                """)
                created_tables.append("APP_Dashboards_Templates")
            except Exception as e:
                errors.append(f"APP_Dashboards_Templates: {str(e)}")

            # APP_Menus_Templates
            try:
                cursor.execute("""
                    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Menus_Templates' AND xtype='U')
                    CREATE TABLE APP_Menus_Templates (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        nom NVARCHAR(100) NOT NULL,
                        code VARCHAR(100) NOT NULL,
                        icon VARCHAR(50),
                        url VARCHAR(200),
                        parent_code VARCHAR(100) NULL,
                        ordre INT DEFAULT 0,
                        type VARCHAR(20) DEFAULT 'link',
                        target_type VARCHAR(50) NULL,
                        target_code VARCHAR(100) NULL,
                        is_system BIT DEFAULT 1,
                        actif BIT DEFAULT 1,
                        date_creation DATETIME DEFAULT GETDATE()
                    )
                """)
                created_tables.append("APP_Menus_Templates")
            except Exception as e:
                errors.append(f"APP_Menus_Templates: {str(e)}")

            # =====================================================
            # SECTION 4: TABLES COMPATIBILITE (ancien schema)
            # =====================================================

            # APP_Societes (compatibilite)
            try:
                cursor.execute("""
                    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Societes' AND xtype='U')
                    CREATE TABLE APP_Societes (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        code VARCHAR(50) UNIQUE NOT NULL,
                        nom NVARCHAR(200) NOT NULL,
                        base_donnees VARCHAR(100) NOT NULL,
                        serveur VARCHAR(100),
                        actif BIT DEFAULT 1,
                        date_creation DATETIME DEFAULT GETDATE()
                    )
                """)
                created_tables.append("APP_Societes")
            except Exception as e:
                errors.append(f"APP_Societes: {str(e)}")

            # APP_Dashboards
            try:
                cursor.execute("""
                    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Dashboards' AND xtype='U')
                    CREATE TABLE APP_Dashboards (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        nom NVARCHAR(200) NOT NULL,
                        code VARCHAR(100) NULL,
                        description NVARCHAR(500),
                        config NVARCHAR(MAX),
                        widgets NVARCHAR(MAX),
                        is_public BIT DEFAULT 0,
                        created_by INT NULL,
                        actif BIT DEFAULT 1,
                        date_creation DATETIME DEFAULT GETDATE(),
                        date_modification DATETIME DEFAULT GETDATE()
                    )
                """)
                created_tables.append("APP_Dashboards")
            except Exception as e:
                errors.append(f"APP_Dashboards: {str(e)}")

            # APP_DataSources
            try:
                cursor.execute("""
                    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_DataSources' AND xtype='U')
                    CREATE TABLE APP_DataSources (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        nom NVARCHAR(200) NOT NULL,
                        code VARCHAR(100) NULL,
                        type VARCHAR(50) NOT NULL DEFAULT 'query',
                        query_template NVARCHAR(MAX),
                        parameters NVARCHAR(MAX),
                        description NVARCHAR(500),
                        date_creation DATETIME DEFAULT GETDATE()
                    )
                """)
                created_tables.append("APP_DataSources")
            except Exception as e:
                errors.append(f"APP_DataSources: {str(e)}")

            # APP_GridViews
            try:
                cursor.execute("""
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
                        actif BIT DEFAULT 1,
                        date_creation DATETIME DEFAULT GETDATE(),
                        date_modification DATETIME DEFAULT GETDATE()
                    )
                """)
                created_tables.append("APP_GridViews")
            except Exception as e:
                errors.append(f"APP_GridViews: {str(e)}")

            # APP_Pivots
            try:
                cursor.execute("""
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
                    )
                """)
                created_tables.append("APP_Pivots")
            except Exception as e:
                errors.append(f"APP_Pivots: {str(e)}")

            # APP_Menus
            try:
                cursor.execute("""
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
                        roles NVARCHAR(200),
                        date_creation DATETIME DEFAULT GETDATE()
                    )
                """)
                created_tables.append("APP_Menus")
            except Exception as e:
                errors.append(f"APP_Menus: {str(e)}")

            # APP_ReportSchedules
            try:
                cursor.execute("""
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
                    )
                """)
                created_tables.append("APP_ReportSchedules")
            except Exception as e:
                errors.append(f"APP_ReportSchedules: {str(e)}")

            # APP_ReportHistory
            try:
                cursor.execute("""
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
                    )
                """)
                created_tables.append("APP_ReportHistory")
            except Exception as e:
                errors.append(f"APP_ReportHistory: {str(e)}")

            # APP_EmailConfig
            try:
                cursor.execute("""
                    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_EmailConfig' AND xtype='U')
                    CREATE TABLE APP_EmailConfig (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        dwh_code VARCHAR(50) NULL,
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
                    )
                """)
                created_tables.append("APP_EmailConfig")
            except Exception as e:
                errors.append(f"APP_EmailConfig: {str(e)}")

            # APP_WidgetTemplates
            try:
                cursor.execute("""
                    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_WidgetTemplates' AND xtype='U')
                    CREATE TABLE APP_WidgetTemplates (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        nom NVARCHAR(200) NOT NULL,
                        code VARCHAR(100),
                        type VARCHAR(50) NOT NULL,
                        config NVARCHAR(MAX),
                        preview_image NVARCHAR(500),
                        description NVARCHAR(500),
                        category VARCHAR(50),
                        is_system BIT DEFAULT 1,
                        actif BIT DEFAULT 1,
                        date_creation DATETIME DEFAULT GETDATE()
                    )
                """)
                created_tables.append("APP_WidgetTemplates")
            except Exception as e:
                errors.append(f"APP_WidgetTemplates: {str(e)}")

            # APP_Settings
            try:
                cursor.execute("""
                    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Settings' AND xtype='U')
                    CREATE TABLE APP_Settings (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        dwh_code VARCHAR(50) NULL,
                        setting_key VARCHAR(100) NOT NULL,
                        setting_value NVARCHAR(MAX),
                        setting_type VARCHAR(20) DEFAULT 'string',
                        description NVARCHAR(500),
                        date_modification DATETIME DEFAULT GETDATE()
                    )
                """)
                created_tables.append("APP_Settings")
            except Exception as e:
                errors.append(f"APP_Settings: {str(e)}")

            # APP_AuditLog
            try:
                cursor.execute("""
                    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_AuditLog' AND xtype='U')
                    CREATE TABLE APP_AuditLog (
                        id BIGINT IDENTITY(1,1) PRIMARY KEY,
                        user_id INT NULL,
                        dwh_code VARCHAR(50) NULL,
                        action VARCHAR(50) NOT NULL,
                        entity_type VARCHAR(50),
                        entity_id INT NULL,
                        details NVARCHAR(MAX),
                        ip_address VARCHAR(50),
                        user_agent NVARCHAR(500),
                        date_action DATETIME DEFAULT GETDATE()
                    )
                """)
                created_tables.append("APP_AuditLog")
            except Exception as e:
                errors.append(f"APP_AuditLog: {str(e)}")

            # APP_ClientDB - Routage multi-tenant (client -> base OptiBoard_XXX)
            try:
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
                created_tables.append("APP_ClientDB")
            except Exception as e:
                errors.append(f"APP_ClientDB: {str(e)}")

            # APP_Pivots_V2
            try:
                cursor.execute("""
                    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Pivots_V2' AND xtype='U')
                    CREATE TABLE APP_Pivots_V2 (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        nom NVARCHAR(200) NOT NULL,
                        description NVARCHAR(500),
                        datasource_code VARCHAR(100),
                        pivot_config NVARCHAR(MAX),
                        filters_config NVARCHAR(MAX),
                        display_config NVARCHAR(MAX),
                        created_by INT NULL,
                        is_public BIT DEFAULT 0,
                        actif BIT DEFAULT 1,
                        date_creation DATETIME DEFAULT GETDATE(),
                        date_modification DATETIME DEFAULT GETDATE()
                    )
                """)
                created_tables.append("APP_Pivots_V2")
            except Exception as e:
                errors.append(f"APP_Pivots_V2: {str(e)}")

            # APP_GridView_User_Prefs
            try:
                cursor.execute("""
                    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_GridView_User_Prefs' AND xtype='U')
                    CREATE TABLE APP_GridView_User_Prefs (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        gridview_id INT NOT NULL,
                        user_id INT NOT NULL,
                        columns_order NVARCHAR(MAX),
                        columns_visible NVARCHAR(MAX),
                        filters NVARCHAR(MAX),
                        sort_config NVARCHAR(MAX),
                        date_modification DATETIME DEFAULT GETDATE(),
                        CONSTRAINT UQ_GridView_User UNIQUE (gridview_id, user_id)
                    )
                """)
                created_tables.append("APP_GridView_User_Prefs")
            except Exception as e:
                errors.append(f"APP_GridView_User_Prefs: {str(e)}")

            # APP_Pivot_User_Prefs
            try:
                cursor.execute("""
                    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Pivot_User_Prefs' AND xtype='U')
                    CREATE TABLE APP_Pivot_User_Prefs (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        pivot_id INT NOT NULL,
                        user_id INT NOT NULL,
                        config NVARCHAR(MAX),
                        date_modification DATETIME DEFAULT GETDATE(),
                        CONSTRAINT UQ_Pivot_User UNIQUE (pivot_id, user_id)
                    )
                """)
                created_tables.append("APP_Pivot_User_Prefs")
            except Exception as e:
                errors.append(f"APP_Pivot_User_Prefs: {str(e)}")

            # APP_GridViews_Templates
            try:
                cursor.execute("""
                    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_GridViews_Templates' AND xtype='U')
                    CREATE TABLE APP_GridViews_Templates (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        nom NVARCHAR(200) NOT NULL,
                        code VARCHAR(100) UNIQUE NOT NULL,
                        description NVARCHAR(500),
                        query_template NVARCHAR(MAX),
                        columns_config NVARCHAR(MAX),
                        parameters NVARCHAR(MAX),
                        features NVARCHAR(MAX),
                        category VARCHAR(50),
                        is_system BIT DEFAULT 1,
                        actif BIT DEFAULT 1,
                        date_creation DATETIME DEFAULT GETDATE()
                    )
                """)
                created_tables.append("APP_GridViews_Templates")
            except Exception as e:
                errors.append(f"APP_GridViews_Templates: {str(e)}")

            # =====================================================
            # SECTION 4b: MIGRATION - Ajouter code aux tables MASTER existantes
            # =====================================================
            try:
                alter_statements = [
                    "IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_GridViews') AND name='code') ALTER TABLE APP_GridViews ADD code VARCHAR(100) NULL",
                    "IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_Pivots_V2') AND name='code') ALTER TABLE APP_Pivots_V2 ADD code VARCHAR(100) NULL",
                    "IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_Dashboards') AND name='code') ALTER TABLE APP_Dashboards ADD code VARCHAR(100) NULL",
                    "IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_DataSources') AND name='code') ALTER TABLE APP_DataSources ADD code VARCHAR(100) NULL",
                ]
                for stmt in alter_statements:
                    try:
                        cursor.execute(stmt)
                    except Exception:
                        pass
                created_tables.append("Master code columns migration")
            except Exception as e:
                errors.append(f"Master code migration: {str(e)}")

            # =====================================================
            # SECTION 5: INDEX
            # =====================================================
            try:
                cursor.execute("""
                    IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_APP_DWH_code')
                        CREATE INDEX IX_APP_DWH_code ON APP_DWH(code);
                    IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_APP_DWH_Sources_dwh')
                        CREATE INDEX IX_APP_DWH_Sources_dwh ON APP_DWH_Sources(dwh_code);
                    IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_APP_UserDWH_user')
                        CREATE INDEX IX_APP_UserDWH_user ON APP_UserDWH(user_id);
                    IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_APP_UserSocietes_user')
                        CREATE INDEX IX_APP_UserSocietes_user ON APP_UserSocietes(user_id);
                    IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_APP_AuditLog_date')
                        CREATE INDEX IX_APP_AuditLog_date ON APP_AuditLog(date_action);
                    IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_APP_ClientDB_dwh')
                        CREATE INDEX IX_APP_ClientDB_dwh ON APP_ClientDB(dwh_code);
                """)
                created_tables.append("Index created")
            except Exception as e:
                errors.append(f"Index: {str(e)}")

            # =====================================================
            # SECTION 6: SUPERADMIN PAR DEFAUT
            # =====================================================
            try:
                cursor.execute("SELECT COUNT(*) FROM APP_Users WHERE username = 'superadmin'")
                if cursor.fetchone()[0] == 0:
                    # Password: admin (SHA256)
                    cursor.execute("""
                        INSERT INTO APP_Users (username, password_hash, nom, prenom, email, role_global, actif)
                        VALUES ('superadmin', '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918',
                                'Super', 'Admin', 'superadmin@optiboard.local', 'superadmin', 1)
                    """)
                    cursor.execute("SELECT @@IDENTITY")
                    admin_id = cursor.fetchone()[0]

                    # Acces a toutes les pages
                    pages = ['dashboard', 'ventes', 'stocks', 'recouvrement', 'admin', 'users',
                             'dwh_management', 'etl_admin', 'settings']
                    for page in pages:
                        cursor.execute(
                            "INSERT INTO APP_UserPages (user_id, page_code) VALUES (?, ?)",
                            (admin_id, page)
                        )
                    created_tables.append("SuperAdmin user created")
            except Exception as e:
                errors.append(f"SuperAdmin: {str(e)}")

            # Admin standard aussi (compatibilite)
            try:
                cursor.execute("SELECT COUNT(*) FROM APP_Users WHERE username = 'admin'")
                if cursor.fetchone()[0] == 0:
                    cursor.execute("""
                        INSERT INTO APP_Users (username, password_hash, nom, prenom, email, role_global, actif)
                        VALUES ('admin', '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918',
                                'Administrateur', 'System', 'admin@optiboard.local', 'admin', 1)
                    """)
                    cursor.execute("SELECT @@IDENTITY")
                    admin_id = cursor.fetchone()[0]

                    pages = ['dashboard', 'ventes', 'stocks', 'recouvrement', 'admin', 'users']
                    for page in pages:
                        cursor.execute(
                            "INSERT INTO APP_UserPages (user_id, page_code) VALUES (?, ?)",
                            (admin_id, page)
                        )
                    created_tables.append("Admin user created")
            except Exception as e:
                errors.append(f"Admin: {str(e)}")

            # =====================================================
            # SECTION 7: SETTINGS PAR DEFAUT
            # =====================================================
            try:
                cursor.execute("SELECT COUNT(*) FROM APP_Settings WHERE setting_key = 'app_name'")
                if cursor.fetchone()[0] == 0:
                    settings_data = [
                        ('app_name', 'OptiBoard', 'string', 'Nom de l application'),
                        ('cache_ttl', '300', 'int', 'Duree du cache en secondes'),
                        ('max_rows', '10000', 'int', 'Nombre max de lignes par requete'),
                        ('query_timeout', '30', 'int', 'Timeout des requetes en secondes'),
                    ]
                    for key, value, stype, desc in settings_data:
                        cursor.execute("""
                            INSERT INTO APP_Settings (dwh_code, setting_key, setting_value, setting_type, description)
                            VALUES (NULL, ?, ?, ?, ?)
                        """, (key, value, stype, desc))
                    created_tables.append("Default settings created")
            except Exception as e:
                errors.append(f"Settings: {str(e)}")

        return {
            "success": True,
            "message": "Base centrale OptiBoard_SaaS initialisee avec succes",
            "created_tables": created_tables,
            "errors": errors if errors else None,
            "admin_credentials": {
                "superadmin": {"username": "superadmin", "password": "admin"},
                "admin": {"username": "admin", "password": "admin"}
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# STANDALONE - Wizard de première connexion
# ============================================================

class CreateAdminRequest(BaseModel):
    username: str
    password: str
    nom: Optional[str] = ""
    prenom: Optional[str] = ""
    email: Optional[str] = ""


@router.get("/standalone-status")
async def get_standalone_status():
    """
    Retourne le statut du mode standalone et si le wizard est complété.
    Utilisé par le frontend pour rediriger vers /setup au 1er démarrage.
    """
    from ..config import get_settings
    from ..database_unified import execute_central

    settings = get_settings()
    if not settings.is_standalone:
        return {"standalone": False, "setup_completed": True}

    try:
        rows = execute_central(
            "SELECT setting_value FROM APP_Settings WHERE setting_key = 'setup_completed'",
            use_cache=False
        )
        completed = rows[0]["setting_value"] == "1" if rows else False
        admin_exists = False
        if completed:
            count = execute_central("SELECT COUNT(*) AS cnt FROM APP_Users", use_cache=False)
            admin_exists = (count[0]["cnt"] > 0) if count else False
        return {
            "standalone": True,
            "setup_completed": completed and admin_exists,
            "dwh_code": settings.DWH_CODE,
        }
    except Exception as e:
        return {"standalone": True, "setup_completed": False, "error": str(e)}


@router.post("/create-admin")
async def create_admin(req: CreateAdminRequest):
    """
    Crée le premier compte administrateur (standalone uniquement).
    Accessible sans auth — protégé par vérification setup_completed=0.
    """
    from ..config import get_settings
    from ..database_unified import execute_central, write_central

    settings = get_settings()

    try:
        rows = execute_central(
            "SELECT setting_value FROM APP_Settings WHERE setting_key = 'setup_completed'",
            use_cache=False
        )
        if rows and rows[0]["setting_value"] == "1":
            raise HTTPException(
                status_code=403,
                detail="Setup déjà complété. Utilisez la gestion des utilisateurs."
            )
    except HTTPException:
        raise
    except Exception:
        pass

    if not req.username or len(req.username) < 3:
        raise HTTPException(status_code=400, detail="Nom d'utilisateur trop court (min 3 caractères)")
    if not req.password or len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Mot de passe trop court (min 6 caractères)")

    try:
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        password_hash = pwd_context.hash(req.password)
    except ImportError:
        password_hash = hashlib.sha256(req.password.encode()).hexdigest()

    try:
        existing = execute_central(
            "SELECT COUNT(*) AS cnt FROM APP_Users WHERE username = ?",
            (req.username,), use_cache=False
        )
        if existing and existing[0]["cnt"] > 0:
            raise HTTPException(status_code=409, detail=f"Utilisateur '{req.username}' déjà existant")

        write_central(
            """INSERT INTO APP_Users
               (username, password_hash, nom, prenom, email, role_dwh, actif, must_change_password)
               VALUES (?, ?, ?, ?, ?, 'admin', 1, 0)""",
            (req.username, password_hash, req.nom or "", req.prenom or "", req.email or "")
        )
        write_central(
            "UPDATE APP_Settings SET setting_value='1', date_modification=GETDATE() WHERE setting_key='setup_completed'"
        )
        return {
            "success": True,
            "message": f"Administrateur '{req.username}' créé avec succès.",
            "username": req.username,
            "role": "admin"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
