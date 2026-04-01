"""Main entry point for the FastAPI application"""  # reload trigger 7
import logging
import os
import sys

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

from app.config import get_settings
from app.database_unified import test_central_connection as test_connection, DatabaseNotConfiguredError
from app.middleware.tenant_context import TenantContextMiddleware
from app.routes import (
    dashboard, ventes, ventes_detail, stocks, recouvrement,
    admin_sql, export, users, dashboard_builder, gridview_builder,
    menus, report_scheduler, setup, etl_agents,
    liste_ventes, analyse_ca_creances, pic_2026,
    datasource_templates, sql_jobs, pivot_v2,
    license, ai_assistant, master_publish, ai_learning, ai_prompts,
    dwh_admin, auth_multitenant,          # Modules architecturaux
    client_portal,                        # Portail client (admin_client)
)
from app.routes.etl_tables import router as etl_tables_router       # ETL Tables publication
from app.routes.etl_colonnes import router as etl_colonnes_router   # ETL Colonnes catalogue + choix client
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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# Include routers
# ── Nouveaux routers (enregistrés EN PREMIER pour prendre priorité) ──────────
app.include_router(dwh_admin.router)        # Règles 1/2/3 — DWH clients
app.include_router(auth_multitenant.router) # Auth multi-tenant
app.include_router(client_portal.router)    # Portail client (admin_client)
# ── Routers existants ────────────────────────────────────────────────────────
app.include_router(dashboard.router)
app.include_router(ventes.router)
app.include_router(ventes_detail.router)
app.include_router(stocks.router)
app.include_router(recouvrement.router)
app.include_router(admin_sql.router)
app.include_router(export.router)
app.include_router(users.router)
app.include_router(dashboard_builder.router)
app.include_router(gridview_builder.router)
app.include_router(menus.router)
app.include_router(report_scheduler.router)
app.include_router(setup.router)
app.include_router(etl_agents.router)
app.include_router(liste_ventes.router)
app.include_router(analyse_ca_creances.router)
app.include_router(pic_2026.router)
app.include_router(datasource_templates.router)
app.include_router(sql_jobs.router)
app.include_router(pivot_v2.router)
app.include_router(license.router)
app.include_router(ai_assistant.router)
app.include_router(ai_learning.router)
app.include_router(ai_prompts.router)
app.include_router(master_publish.router)
app.include_router(etl_tables_router)       # ETL Tables : publication central → clients
app.include_router(etl_colonnes_router)     # ETL Colonnes : catalogue central + choix client
app.include_router(client_users_router)     # Users & UserDWH locaux client
app.include_router(update_manager_router)   # Module MAJ : check/pull updates depuis central
app.include_router(roles_router)            # Gestion rôles & permissions
app.include_router(client_package_router)   # Package installation client autonome
app.include_router(env_manager_router)      # Gestion .env via UI admin
app.include_router(alerts_router)           # Alertes KPI
app.include_router(subscriptions_router)       # Abonnements rapports
app.include_router(admin_subscriptions_router) # Admin abonnements + logs livraison
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
}


# Middleware de verification de licence
@app.middleware("http")
async def license_check_middleware(request: Request, call_next):
    """Verifie la licence avant chaque requete (sauf routes exemptees)"""
    # ── DEV MODE: licence desactivee pendant le developpement ──
    # TODO: Reactiver avant la mise en production
    if settings.DEBUG:
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
        print("[STARTUP] Application non configuree - Acces a /api/setup/status pour configurer")
        print("[STARTUP] Les autres modules seront initialises apres configuration")
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
                print(f"[STARTUP] Licence valide - {license_status.organization} ({license_status.plan})")
                if license_status.grace_mode:
                    print(f"[STARTUP] MODE GRACE - {license_status.grace_days_remaining} jours restants")
                if license_status.days_remaining <= 30:
                    print(f"[STARTUP] ATTENTION: Licence expire dans {license_status.days_remaining} jours")
            else:
                print(f"[STARTUP] LICENCE INVALIDE: {license_status.message}")
        else:
            print("[STARTUP] Aucune licence configuree - Activez une licence via /api/license/activate")
    except Exception as e:
        print(f"[STARTUP] Erreur validation licence: {e}")

    try:
        init_gridview_tables()
        print("[STARTUP] GridView tables initialized successfully")
    except Exception as e:
        print(f"[STARTUP] Error initializing gridview tables: {e}")

    try:
        init_pivot_v2_tables()
        print("[STARTUP] Pivot V2 tables initialized successfully")
    except Exception as e:
        print(f"[STARTUP] Error initializing Pivot V2 tables: {e}")

    try:
        init_scheduler_tables()
        print("[STARTUP] Report scheduler tables initialized successfully")
        start_scheduler()
        print("[STARTUP] Report scheduler started successfully")
    except Exception as e:
        print(f"[STARTUP] Error initializing scheduler tables: {e}")

    try:
        init_query_library_table()
        init_prompts_table()
        print("[STARTUP] AI Query Library table initialized successfully")
    except Exception as e:
        print(f"[STARTUP] Error initializing AI Query Library table: {e}")

    try:
        init_alert_tables()
        print("[STARTUP] KPI Alert tables initialized successfully")
    except Exception as e:
        print(f"[STARTUP] Error initializing KPI Alert tables: {e}")

    try:
        init_subscription_tables()
        init_delivery_logs_table()
        print("[STARTUP] Subscription tables initialized successfully")
    except Exception as e:
        print(f"[STARTUP] Error initializing Subscription tables: {e}")

    try:
        init_drillthrough_tables()
        print("[STARTUP] DrillThrough tables initialized successfully")
    except Exception as e:
        print(f"[STARTUP] Error initializing DrillThrough tables: {e}")

    try:
        init_favorites_tables()
        print("[STARTUP] Favorites tables initialized successfully")
    except Exception as e:
        print(f"[STARTUP] Error initializing Favorites tables: {e}")

    # Migration schema ETL_Tables_Config (ajout colonnes manquantes)
    try:
        from etl.config.table_config import _ensure_table_exists
        _ensure_table_exists()
        print("[STARTUP] ETL schema migration completed")
    except Exception as e:
        print(f"[STARTUP] ETL migration error: {e}")

    # Migration APP_DWH : ajout colonne is_demo
    try:
        from app.database_unified import write_central as _wc
        _wc("IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_DWH') AND name='is_demo') ALTER TABLE APP_DWH ADD is_demo BIT NOT NULL DEFAULT 0")
        _wc("UPDATE APP_DWH SET is_demo=1 WHERE code IN ('KA') AND is_demo=0")
        print("[STARTUP] APP_DWH.is_demo migration OK")
    except Exception as e:
        print(f"[STARTUP] APP_DWH migration error: {e}")



@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "application": settings.APP_NAME,
        "version": "1.0.0",
        "status": "running",
        "documentation": "/api/docs"
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    from app.config import reload_settings
    # Recharger les settings pour avoir les valeurs actuelles du .env
    reload_settings()
    db_status = test_connection()
    cache_stats = query_cache.get_stats()
    return {
        "status": "healthy" if db_status else "unhealthy",
        "database": "connected" if db_status else "disconnected",
        "cache": cache_stats
    }


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
            result = execute_query("SELECT DISTINCT [Société] FROM [GROUPE_ALBOUGHAZE].[dbo].[DashBoard_CA] WHERE [Société] IS NOT NULL")
            for r in result:
                val = r.get('Société')
                if val and val.strip():
                    societes_set.add(val.strip())
        except:
            pass

        # Sociétés depuis BalanceAgee
        try:
            result = execute_query("SELECT DISTINCT [SOCIETE] FROM [GROUPE_ALBOUGHAZE].[dbo].[BalanceAgee] WHERE [SOCIETE] IS NOT NULL")
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


if __name__ == "__main__":
    uvicorn.run(
        "run:app",
        host="0.0.0.0",
        port=8083,
        reload=settings.DEBUG
    )
