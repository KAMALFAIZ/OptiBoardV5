"""Point d'entrée KAsoft Automation Hub — FastAPI port 8085."""
import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import uvicorn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

from app.config import get_settings
from app.database import init_tables
from app.routes import webhook, contacts, tickets, templates, campaigns, workflows, products, channels, analytics
from app.services.scheduler_service import start_scheduler, stop_scheduler, get_status

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    description="Service central d'automatisation Marketing & SAV — KAsoft",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", "http://localhost:3006",
        "http://127.0.0.1:3000", "http://127.0.0.1:3006",
        "http://localhost:5173", "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Routers
app.include_router(webhook.router)
app.include_router(contacts.router)
app.include_router(tickets.router)
app.include_router(templates.router)
app.include_router(campaigns.router)
app.include_router(workflows.router)
app.include_router(products.router)
app.include_router(channels.router)
app.include_router(analytics.router)


@app.on_event("startup")
async def startup():
    logging.info("[HUB] Démarrage KAsoft Automation Hub...")
    init_tables()
    logging.info("[HUB] Tables initialisées")
    start_scheduler()
    logging.info("[HUB] Scheduler démarré")


@app.on_event("shutdown")
async def shutdown():
    stop_scheduler()


@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "status": "running",
        "docs": "/api/docs",
    }


@app.get("/api/health")
async def health():
    from app.database import execute
    try:
        execute("SELECT 1")
        db_ok = True
    except Exception:
        db_ok = False
    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "error",
        "scheduler": get_status(),
    }


if __name__ == "__main__":
    uvicorn.run(
        "run:app",
        host="127.0.0.1",
        port=settings.PORT,
        reload=settings.DEBUG,
    )
