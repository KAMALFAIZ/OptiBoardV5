"""Main entry point for the FastAPI application"""  # reload trigger 7
import logging
import os
import sys
import uuid

from fastapi import FastAPI, Request, Depends
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# Frontend SPA dist directory (built React app)
# run.py is at <install>\backend\run.py -> parent is <install> -> frontend/
_backend_dir = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIST = os.path.join(os.path.dirname(_backend_dir), "frontend")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

from app.config import get_settings
from app.database_unified import test_central_connection as test_connection, DatabaseNotConfiguredError
from app.middleware.tenant_context import TenantContextMiddleware
from app.security import require_admin, require_superadmin   # Gardes d'autorisation par rôle
from app.routes import (
    dashboard, ventes, ventes_detail, stocks, recouvrement,
    admin_sql, export, users, dashboard_builder, gridview_builder,
    menus, report_scheduler, setup, etl_agents, etl_enroll,
    liste_ventes, analyse_ca_creances, pic_2026,
    datasource_templates, sql_jobs, pivot_v2,
    license, ai_assistant, master_publish, ai_learning, ai_prompts,
    dwh_admin, auth_multitenant,          # Modules architecturaux
    client_portal,                        # Portail client (admin_client)
)
from app.routes.etl_tables import router as etl_tables_router       # ETL Tables publication
from app.routes.client_users import router as client_users_router   # Users & UserDWH locaux
from app.routes.update_manager import router as update_manager_router  # Module MAJ clients
from app.routes.client_package import router as client_package_router  # Package installation client
from app.routes.env_manager import router as env_manager_router         # Gestion .env via UI
from app.routes.roles import router as roles_router                     # Gestion des rôles utilisateurs
from app.routes.alerts import router as alerts_router, init_alert_tables           # Alertes KPI
from app.routes.subscriptions import router as subscriptions_router, init_subscription_tables  # Abonnements
from app.routes.admin_subscriptions import router as admin_subscriptions_router, init_delivery_logs_table  # Admin abonnements
from app.routes.drillthrough import router as drillthrough_router, init_drillthrough_tables    # Drill-through
from app.routes.favorites import router as favorites_router, init_favorites_tables             # Favoris & Récents
from app.routes.ai_insights import router as ai_insights_router                                # AI Insights automatiques
from app.routes.ai_summary import router as ai_summary_router                                  # AI Résumé Exécutif
from app.routes.anomalies import router as anomalies_router                                    # Détection anomalies
from app.routes.forecasting import router as forecasting_router                                # Forecasting
from app.routes.alert_templates import router as alert_templates_router                        # Templates alertes maître
from app.routes.fiche_client import router as fiche_client_router                              # Fiche Client 360°
from app.routes.fiche_fournisseur import router as fiche_fournisseur_router                    # Fiche Fournisseur 360°
from app.routes.demo_portal import router as demo_portal_router                                 # Portail Demo AgentETL
from app.routes.comptabilite import router as comptabilite_router                               # Module Comptabilité
from app.routes.dettes_fournisseurs import router as dettes_fournisseurs_router                  # Dettes Fournisseurs
from app.routes.sage_direct import router as sage_direct_router                                 # Accès direct Sage (lecture seule)
from app.routes.weekly_digest import router as weekly_digest_router                             # Digest IA hebdomadaire
from app.routes.two_factor import router as two_factor_router                                   # 2FA TOTP
from app.routes.ai_presentation import router as ai_presentation_router                         # Générateur IA de documents
from app.routes.ai_deck import router as ai_deck_router, init_deck_tables                        # Deck IA interactif
from app.routes.sage_config_admin import router as sage_config_admin_router                       # Admin Sage Direct config
from app.routes.spreadsheet_builder import router as spreadsheet_builder_router, init_spreadsheet_tables  # Spreadsheet Builder (FortuneSheet)
from app.routes.whatsapp_bot import router as whatsapp_bot_router, init_whatsapp_tables              # WhatsApp Business Cloud API (Meta)
from app.routes.comptabilite_analytique import router as comptabilite_analytique_router              # Comptabilité Analytique (Phase 4)
from app.routes.budget import router as budget_router                                                # Budget vs Réalisé + Masse Salariale (Phase 5)
from app.services.cache import query_cache
from app.services.license_service import validate_license, get_cached_license_status, set_cached_license_status
from app.routes.gridview_builder import init_gridview_tables
from app.routes.report_scheduler import init_scheduler_tables
from app.routes.pivot_v2 import init_pivot_v2_tables
from app.services.ai_query_library import init_query_library_table
from app.services.ai_prompt_manager import init_prompts_table
from app.services.scheduler_service import start_scheduler, stop_scheduler, get_scheduler_status

settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Application de Reporting Commercial de Fin d'Année - KAsoft",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002", "http://localhost:3003", "http://localhost:3004", "http://localhost:3005", "http://localhost:5173", "http://127.0.0.1:3000", "http://127.0.0.1:3001", "http://127.0.0.1:3002", "http://127.0.0.1:3003", "http://127.0.0.1:3004", "http://127.0.0.1:3005", "http://127.0.0.1:5173", "http://localhost:8084", "http://127.0.0.1:8084"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Compression gzip des réponses > 1 Ko (gain 60-80% bande passante)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Middleware de routage tenant (async-safe via contextvars)
app.add_middleware(TenantContextMiddleware)

# Exception handler pour base non configuree
@app.exception_handler(DatabaseNotConfiguredError)
async def database_not_configured_handler(request: Request, exc: DatabaseNotConfiguredError):
    """Gere les erreurs quand la base n'est pas configuree"""
    return JSONResponse(
        status_code=503,
        content={
            "success": False,
            "error": "database_not_configured",
            "message": str(exc),
            "action": "Veuillez configurer l'application via /api/setup/configure"
        }
    )

# ── Gestion globale des erreurs ──────────────────────────────────────────────
# Les details techniques (erreurs SQL, schema, stack traces) ne partent jamais
# au client : ils sont logges cote serveur avec une reference courte que
# l'utilisateur peut communiquer au support. Les 4xx (messages volontaires)
# passent inchanges.

def _is_dev_mode() -> bool:
    return str(getattr(settings, "APP_ENV", "") or "").lower() == "development"

@app.exception_handler(StarletteHTTPException)
async def http_exception_sanitizer(request: Request, exc: StarletteHTTPException):
    if exc.status_code >= 500:
        ref = uuid.uuid4().hex[:8]
        logger.error("[ERR %s] %s %s -> %s: %s", ref, request.method, request.url.path,
                     exc.status_code, exc.detail)
        content = {"success": False, "detail": f"Erreur interne du serveur (ref: {ref})", "ref": ref}
        if _is_dev_mode():
            content["debug_detail"] = str(exc.detail)
        return JSONResponse(status_code=exc.status_code, content=content)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None) or None,
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    ref = uuid.uuid4().hex[:8]
    logger.exception("[ERR %s] Exception non geree %s %s: %s", ref, request.method,
                     request.url.path, exc)
    content = {"success": False, "detail": f"Erreur interne du serveur (ref: {ref})", "ref": ref}
    if _is_dev_mode():
        content["debug_detail"] = str(exc)
    return JSONResponse(status_code=500, content=content)

# Include routers
# ── Nouveaux routers (enregistrés EN PREMIER pour prendre priorité) ──────────
app.include_router(dwh_admin.router, dependencies=[Depends(require_superadmin)])        # Règles 1/2/3 — DWH clients (superadmin)
app.include_router(auth_multitenant.router) # Auth multi-tenant
app.include_router(client_portal.router)    # Portail client (admin_client)
# ── Routers existants ────────────────────────────────────────────────────────
app.include_router(dashboard.router)
app.include_router(ventes.router)
app.include_router(ventes_detail.router)
app.include_router(stocks.router)
app.include_router(recouvrement.router)
app.include_router(admin_sql.router, dependencies=[Depends(require_superadmin)])  # SQL admin (superadmin)
app.include_router(export.router)
app.include_router(users.router)
app.include_router(dashboard_builder.router)
app.include_router(gridview_builder.router)
app.include_router(menus.router)
app.include_router(report_scheduler.router)
app.include_router(setup.router)
app.include_router(etl_agents.router)
app.include_router(etl_enroll.router)       # Enrôlement agents par jeton à usage unique
app.include_router(liste_ventes.router)
app.include_router(analyse_ca_creances.router)
app.include_router(pic_2026.router)
app.include_router(datasource_templates.router)
app.include_router(sql_jobs.router, dependencies=[Depends(require_superadmin)])  # ETL/SQL jobs (superadmin)
app.include_router(pivot_v2.router)
app.include_router(license.router)
from app.routes.console_stats import router as console_stats_router
app.include_router(console_stats_router)    # Monitoring console KASOFT (X-Console-Token)
from app.routes.console_provision import router as console_provision_router
app.include_router(console_provision_router)  # Provisioning instances client depuis la console (X-Console-Token)
app.include_router(ai_assistant.router)
app.include_router(ai_learning.router)
app.include_router(ai_prompts.router)
app.include_router(master_publish.router, dependencies=[Depends(require_superadmin)])  # Publication catalogue (superadmin)
app.include_router(etl_tables_router)       # ETL Tables : publication central → clients
app.include_router(client_users_router, dependencies=[Depends(require_admin)])     # Users & UserDWH locaux client (admin)
app.include_router(update_manager_router)   # Module MAJ : check/pull updates depuis central
app.include_router(roles_router)            # Gestion rôles & permissions
app.include_router(client_package_router)   # Package installation client autonome
app.include_router(env_manager_router, dependencies=[Depends(require_superadmin)])      # Gestion .env via UI admin (superadmin)
app.include_router(alerts_router)           # Alertes KPI
app.include_router(subscriptions_router)       # Abonnements rapports
app.include_router(admin_subscriptions_router, dependencies=[Depends(require_superadmin)]) # Admin abonnements (superadmin)
app.include_router(drillthrough_router)     # Drill-through inter-rapports
app.include_router(favorites_router)        # Favoris & Récents utilisateur
app.include_router(ai_insights_router)      # AI Insights automatiques
app.include_router(ai_summary_router)       # AI Résumé Exécutif
app.include_router(anomalies_router)        # Détection anomalies statistiques
app.include_router(forecasting_router)      # Forecasting (régression + Holt)
app.include_router(alert_templates_router)  # Templates alertes KPI (base maître)
app.include_router(fiche_client_router)         # Fiche Client 360°
app.include_router(fiche_fournisseur_router)    # Fiche Fournisseur 360°
app.include_router(demo_portal_router)          # Portail Demo AgentETL
app.include_router(comptabilite_router)         # Module Comptabilité
app.include_router(dettes_fournisseurs_router)  # Dettes Fournisseurs
app.include_router(sage_direct_router)          # Accès direct Sage (lecture seule, sans ETL)
app.include_router(weekly_digest_router)        # Digest IA hebdomadaire (direction)
app.include_router(two_factor_router)          # 2FA TOTP (admins)
app.include_router(ai_presentation_router)    # Générateur IA de documents (PPTX/Excel)
app.include_router(ai_deck_router)            # Deck IA interactif (plan + données DWH + narration)
app.include_router(sage_config_admin_router, dependencies=[Depends(require_superadmin)])   # Admin Sage Direct mappings (superadmin)
app.include_router(spreadsheet_builder_router) # Spreadsheet Builder (FortuneSheet)
app.include_router(whatsapp_bot_router)        # WhatsApp Business Cloud API (Meta)
app.include_router(comptabilite_analytique_router)  # Comptabilité Analytique (Phase 4)
app.include_router(budget_router)              # Budget vs Réalisé + Masse Salariale (Phase 5)

# Routes exemptees de la verification de licence
LICENSE_EXEMPT_PATHS = {
    "/", "/api/docs", "/api/redoc", "/api/openapi.json",
    "/api/health", "/api/setup/status", "/api/setup/test-connection",
    "/api/setup/configure", "/api/setup/databases",
    "/api/license/status", "/api/license/activate",
    "/api/license/machine-id",
    "/api/env/config", "/api/env/schema", "/api/env/test-db",
    "/api/env/test-license-server", "/api/env/restart", "/api/env/test-smtp",
    # Portail demo : routes publiques + AgentETL exemptees de licence
    "/api/demo/register",
    # Digest IA : trigger admin (pas besoin de vérif licence côté scheduler)
    "/api/admin/digest/status",
    # WhatsApp webhook (public — Meta doit pouvoir y accéder)
    "/api/whatsapp/webhook",
}


# Middleware de verification de licence
@app.middleware("http")
async def license_check_middleware(request: Request, call_next):
    """Verifie la licence avant chaque requete (sauf routes exemptees)"""
    # En mode développement uniquement, la vérification licence est désactivée.
    # En production (APP_ENV=production), la vérification est TOUJOURS active.
    if not settings.is_production:
        return await call_next(request)

    path = request.url.path

    # Routes exemptees
    if path in LICENSE_EXEMPT_PATHS or path.startswith("/api/docs") or path.startswith("/api/redoc") or path.startswith("/api/demo"):
        return await call_next(request)

    # Verifier si la licence est configuree
    current_settings = get_settings()
    if not current_settings.LICENSE_KEY:
        # Pas de licence = bloquer les routes metier
        if path.startswith("/api/") and path not in LICENSE_EXEMPT_PATHS:
            return JSONResponse(
                status_code=403,
                content={
                    "success": False,
                    "error": "license_required",
                    "message": "Une licence valide est requise pour utiliser cette application"
                }
            )

    # Verifier le cache de licence
    cached = get_cached_license_status()
    if cached and not cached.valid:
        if path.startswith("/api/") and path not in LICENSE_EXEMPT_PATHS:
            return JSONResponse(
                status_code=403,
                content={
                    "success": False,
                    "error": "license_invalid",
                    "message": cached.message,
                    "status": cached.status
                }
            )

    return await call_next(request)


# Initialize gridview tables (ensure features column exists)
@app.on_event("startup")
async def startup_event():
    """Initialize database tables on startup"""
    # Verifier si l'application est configuree
    if not settings.is_configured:
        logger.warning("[STARTUP] Application non configuree — accès à /api/setup/status pour configurer")
        logger.warning("[STARTUP] Les autres modules seront initialisés après configuration")
        return

    # Validation de licence au demarrage
    try:
        if settings.LICENSE_KEY:
            license_status = validate_license(
                license_key=settings.LICENSE_KEY,
                server_url=settings.LICENSE_SERVER_URL,
                grace_days=settings.LICENSE_GRACE_DAYS
            )
            set_cached_license_status(license_status)
            if license_status.valid:
                logger.info(f"[STARTUP] Licence valide — {license_status.organization} ({license_status.plan})")
                if license_status.grace_mode:
                    logger.warning(f"[STARTUP] MODE GRACE — {license_status.grace_days_remaining} jours restants")
                if license_status.days_remaining <= 30:
                    logger.warning(f"[STARTUP] Licence expire dans {license_status.days_remaining} jours")
            else:
                logger.error(f"[STARTUP] LICENCE INVALIDE: {license_status.message}")
        else:
            logger.warning("[STARTUP] Aucune licence configurée — activez une licence via /api/license/activate")
    except Exception as e:
        logger.error(f"[STARTUP] Erreur validation licence: {e}")

    try:
        init_gridview_tables()
        logger.info("[STARTUP] GridView tables OK")
    except Exception as e:
        logger.error(f"[STARTUP] GridView tables error: {e}")

    try:
        from app.sage_direct.db_store import init_sage_config_table
        init_sage_config_table()
        logger.info("[STARTUP] Sage View Config table OK")
    except Exception as e:
        logger.error(f"[STARTUP] Sage View Config table error: {e}")

    try:
        init_pivot_v2_tables()
        logger.info("[STARTUP] Pivot V2 tables OK")
    except Exception as e:
        logger.error(f"[STARTUP] Pivot V2 tables error: {e}")

    try:
        init_spreadsheet_tables()
        logger.info("[STARTUP] Spreadsheet tables OK")
    except Exception as e:
        logger.error(f"[STARTUP] Spreadsheet tables error: {e}")

    try:
        init_scheduler_tables()
        start_scheduler()
        logger.info("[STARTUP] Scheduler tables + scheduler OK")
    except Exception as e:
        logger.error(f"[STARTUP] Scheduler error: {e}")

    try:
        init_query_library_table()
        init_prompts_table()
        logger.info("[STARTUP] AI Query Library tables OK")
    except Exception as e:
        logger.error(f"[STARTUP] AI Query Library tables error: {e}")

    try:
        init_alert_tables()
        logger.info("[STARTUP] KPI Alert tables OK")
    except Exception as e:
        logger.error(f"[STARTUP] KPI Alert tables error: {e}")

    try:
        init_subscription_tables()
        init_delivery_logs_table()
        logger.info("[STARTUP] Subscription tables OK")
    except Exception as e:
        logger.error(f"[STARTUP] Subscription tables error: {e}")

    try:
        init_drillthrough_tables()
        logger.info("[STARTUP] DrillThrough tables OK")
    except Exception as e:
        logger.error(f"[STARTUP] DrillThrough tables error: {e}")

    try:
        init_favorites_tables()
        logger.info("[STARTUP] Favorites tables OK")
    except Exception as e:
        logger.error(f"[STARTUP] Favorites tables error: {e}")

    try:
        init_deck_tables()
        logger.info("[STARTUP] AI Deck tables OK")
    except Exception as e:
        logger.error(f"[STARTUP] AI Deck tables error: {e}")

    try:
        init_whatsapp_tables()
        logger.info("[STARTUP] WhatsApp tables OK")
    except Exception as e:
        logger.error(f"[STARTUP] WhatsApp tables error: {e}")

    # Migration schema ETL_Tables_Config (ajout colonnes manquantes)
    try:
        from etl.config.table_config import _ensure_table_exists
        _ensure_table_exists()
        logger.info("[STARTUP] ETL schema migration OK")
    except Exception as e:
        logger.error(f"[STARTUP] ETL migration error: {e}")

    # Migration APP_DWH : ajout colonne is_demo
    try:
        from app.database_unified import write_central as _wc
        _wc("IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_DWH') AND name='is_demo') ALTER TABLE APP_DWH ADD is_demo BIT NOT NULL DEFAULT 0")
        _wc("UPDATE APP_DWH SET is_demo=1 WHERE code IN ('KA') AND is_demo=0")
        logger.info("[STARTUP] APP_DWH.is_demo migration OK")
    except Exception as e:
        logger.error(f"[STARTUP] APP_DWH migration error: {e}")

    # Migration APP_DWH : colonnes tunnel SSH
    try:
        from app.database_unified import write_central as _wc_ssh
        for col, ddl in [
            ("ssh_enabled",     "BIT NOT NULL DEFAULT 0"),
            ("ssh_host",        "VARCHAR(200) NULL"),
            ("ssh_port",        "INT NOT NULL DEFAULT 22"),
            ("ssh_user",        "VARCHAR(100) NULL"),
            ("ssh_private_key", "NVARCHAR(MAX) NULL"),
        ]:
            _wc_ssh(
                f"IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_DWH') AND name='{col}')"
                f" ALTER TABLE APP_DWH ADD {col} {ddl}"
            )
        logger.info("[STARTUP] APP_DWH SSH columns migration OK")
    except Exception as e:
        logger.error(f"[STARTUP] APP_DWH SSH migration error: {e}")

    # Migration APP_Users (central + client DBs) : ajout colonnes 2FA
    try:
        from app.database_unified import write_central as _wc2
        _wc2("IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_Users') AND name='totp_secret') ALTER TABLE APP_Users ADD totp_secret NVARCHAR(64) NULL")
        _wc2("IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_Users') AND name='totp_enabled') ALTER TABLE APP_Users ADD totp_enabled BIT NOT NULL DEFAULT 0")
        logger.info("[STARTUP] APP_Users 2FA columns migration OK (central)")
    except Exception as e:
        logger.error(f"[STARTUP] 2FA migration central error: {e}")

    # Migration APP_Users (client DB) : ajout colonne onboarding_done
    try:
        from app.database_unified import execute_central as _ec, write_client as _wk
        dwh_list = _ec("SELECT code FROM APP_DWH WHERE actif = 1", use_cache=False)
        for _dwh in dwh_list:
            _code = _dwh.get("code", "")
            if not _code:
                continue
            try:
                _wk(
                    "IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_Users') AND name='onboarding_done') "
                    "ALTER TABLE APP_Users ADD onboarding_done BIT NOT NULL DEFAULT 0",
                    dwh_code=_code,
                )
            except Exception:
                pass
        logger.info("[STARTUP] APP_Users.onboarding_done migration OK")
    except Exception as e:
        logger.error(f"[STARTUP] onboarding_done migration error: {e}")

    # Migration APP_Sessions : table des sessions serveur (token, expiry, révocation).
    # Schéma identique à setup.py::init_all_tables() (installs neufs via /configure) ;
    # ici pour les installs déjà configurées AVANT l'ajout de cette table.
    try:
        from app.database_unified import write_central as _wc_sess
        _wc_sess("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Sessions' AND xtype='U')
            CREATE TABLE APP_Sessions (
                id            INT IDENTITY(1,1) PRIMARY KEY,
                token         VARCHAR(64) NOT NULL,
                user_id       INT NOT NULL,
                dwh_code      NVARCHAR(50) NULL,
                created_at    DATETIME NOT NULL DEFAULT GETDATE(),
                expires_at    DATETIME NOT NULL,
                last_activity DATETIME NOT NULL DEFAULT GETDATE(),
                ip_address    VARCHAR(45) NULL,
                is_active     BIT NOT NULL DEFAULT 1
            )
        """)
        _wc_sess("""
            IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='IX_APP_Sessions_token')
                CREATE UNIQUE INDEX IX_APP_Sessions_token ON APP_Sessions(token)
        """)
        _wc_sess("""
            IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='IX_APP_Sessions_user')
                CREATE INDEX IX_APP_Sessions_user ON APP_Sessions(user_id, is_active)
        """)
        logger.info("[STARTUP] APP_Sessions table OK")
    except Exception as e:
        logger.error(f"[STARTUP] APP_Sessions migration error: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Arrêt propre : tunnels SSH + scheduler."""
    try:
        stop_scheduler()
    except Exception:
        pass
    try:
        from app.services.ssh_tunnel_service import stop_all
        stop_all()
        logger.info("[SHUTDOWN] Tunnels SSH arrêtés")
    except Exception as e:
        logger.error(f"[SHUTDOWN] Erreur arrêt tunnels SSH: {e}")


@app.get("/api")
async def api_root():
    """API root endpoint"""
    return {
        "application": settings.APP_NAME,
        "version": "1.0.0",
        "status": "running",
        "documentation": "/api/docs"
    }


@app.get("/api/health")
async def health_check():
    """Health check : base centrale, ETL delay, cache stats."""
    from app.config import reload_settings
    from datetime import datetime
    reload_settings()

    checks: dict = {}

    # Connexion base centrale
    db_ok = test_connection()
    checks["db_centrale"] = "ok" if db_ok else "error"

    # Délai ETL (dernière sync réussie)
    if db_ok:
        try:
            from app.database_unified import execute_central
            rows = execute_central(
                "SELECT MAX(last_run) AS last_run FROM APP_ETL_Agents WHERE last_status='success'",
                use_cache=False,
            )
            last_run = rows[0].get("last_run") if rows else None
            if last_run:
                delay_h = int((datetime.now() - last_run).total_seconds() // 3600)
                checks["etl_delay_hours"] = delay_h
                checks["etl_status"] = "ok" if delay_h < 24 else "warning"
            else:
                checks["etl_delay_hours"] = None
                checks["etl_status"] = "warning"
        except Exception as e:
            checks["etl_status"] = "error"
            checks["etl_error"] = str(e)

    # Statistiques cache
    checks["cache"] = query_cache.get_stats()

    # Statut global : degraded si au moins une valeur est "error"
    non_cache = {k: v for k, v in checks.items() if k != "cache"}
    all_ok = all(v in ("ok", "warning") for v in non_cache.values() if isinstance(v, str))
    status = "ok" if all_ok else "degraded"

    return {"status": status, **checks}


@app.get("/api/cache/stats")
async def cache_stats():
    """Cache statistics endpoint"""
    return {
        "success": True,
        "stats": query_cache.get_stats()
    }


@app.get("/api/scheduler/status")
async def scheduler_status():
    """Scheduler status endpoint"""
    return {
        "success": True,
        "scheduler": get_scheduler_status()
    }


@app.post("/api/cache/clear")
async def clear_cache():
    """Clear the query cache"""
    count = query_cache.invalidate()
    return {
        "success": True,
        "message": f"Cache vidé: {count} entrées supprimées"
    }


@app.get("/api/info")
async def app_info():
    """Application info"""
    return {
        "name": settings.APP_NAME,
        "database": settings.DB_NAME,
        "server": settings.DB_SERVER,
        "modules": [
            "Dashboard",
            "Ventes",
            "Stocks",
            "Recouvrement",
            "Admin SQL",
            "Export"
        ]
    }


@app.get("/api/societes")
async def get_societes():
    """Get list of available societes from all tables"""
    from app.database_unified import execute_app as execute_query
    try:
        societes_set = set()

        # Sociétés depuis DashBoard_CA
        try:
            result = execute_query("SELECT DISTINCT [Société] FROM [dbo].[DashBoard_CA] WHERE [Société] IS NOT NULL")
            for r in result:
                val = r.get('Société')
                if val and val.strip():
                    societes_set.add(val.strip())
        except:
            pass

        # Sociétés depuis BalanceAgee
        try:
            result = execute_query("SELECT DISTINCT [SOCIETE] FROM [dbo].[BalanceAgee] WHERE [SOCIETE] IS NOT NULL")
            for r in result:
                val = r.get('SOCIETE')
                if val and val.strip():
                    societes_set.add(val.strip())
        except:
            pass

        societes = sorted(list(societes_set))
        return {
            "success": True,
            "data": societes
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": []
        }


# ─── Service du frontend SPA (React) ──────────────────────────────────────────
# Doit être enregistré APRÈS toutes les routes API pour ne pas les masquer
if os.path.isdir(FRONTEND_DIST):
    _assets_dir = os.path.join(FRONTEND_DIST, "assets")
    if os.path.isdir(_assets_dir):
        app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Ne pas intercepter les routes API/docs
        if full_path.startswith("api/") or full_path.startswith("api"):
            return JSONResponse(status_code=404, content={"detail": "Not Found"})

        # Fichier statique direct (favicon.svg, etc.)
        candidate = os.path.join(FRONTEND_DIST, full_path)
        if full_path and os.path.isfile(candidate):
            return FileResponse(candidate)

        # Fallback : index.html (SPA routing client-side)
        index = os.path.join(FRONTEND_DIST, "index.html")
        if os.path.isfile(index):
            return FileResponse(index)
        return JSONResponse(status_code=404, content={"detail": "Frontend not built"})

    logging.getLogger(__name__).info(f"[STARTUP] Frontend SPA servi depuis: {FRONTEND_DIST}")
else:
    logging.getLogger(__name__).warning(f"[STARTUP] Dossier frontend introuvable: {FRONTEND_DIST}")


if __name__ == "__main__":
    uvicorn.run(
        "run:app",
        host="127.0.0.1",
        port=int(os.environ.get("BACKEND_PORT", 8084)),
        reload=settings.DEBUG
    )
