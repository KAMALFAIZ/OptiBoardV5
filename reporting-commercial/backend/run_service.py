"""Entry point pour le service Windows et le lancement autonome client.

Lance l'API FastAPI et sert le frontend React depuis le meme processus.
Frontend detecte via OPTIBOARD_FRONTEND_DIR ou ../frontend relatif au script.
"""
import os
import sys

# ── Chemin frontend ──────────────────────────────────────────────────────────
_here = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIST = os.environ.get(
    'OPTIBOARD_FRONTEND_DIR',
    os.path.join(_here, '..', 'frontend'),
)
FRONTEND_DIST = os.path.normpath(FRONTEND_DIST)

# ── Charger l'app FastAPI (enregistre tous les routers API) ─────────────────
from run import app  # noqa: E402

# ── Monter le frontend React si disponible ───────────────────────────────────
if os.path.isdir(FRONTEND_DIST):
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse
    from fastapi.routing import APIRoute

    # Retirer le root JSON de run.py pour que "/" serve index.html
    app.router.routes = [
        r for r in app.router.routes
        if not (isinstance(r, APIRoute) and r.path == '/' and 'GET' in r.methods)
    ]

    assets_dir = os.path.join(FRONTEND_DIST, 'assets')
    if os.path.isdir(assets_dir):
        app.mount('/assets', StaticFiles(directory=assets_dir), name='frontend-assets')

    @app.get('/', include_in_schema=False)
    async def _root():
        return FileResponse(os.path.join(FRONTEND_DIST, 'index.html'))

    @app.get('/{full_path:path}', include_in_schema=False)
    async def _spa(full_path: str):
        candidate = os.path.join(FRONTEND_DIST, full_path)
        if os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(os.path.join(FRONTEND_DIST, 'index.html'))

# ── Lancement ────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    import uvicorn
    port = int(os.environ.get('API_PORT', os.environ.get('OPTIBOARD_PORT', '8084')))
    host = os.environ.get('API_HOST', '127.0.0.1')
    uvicorn.run(app, host=host, port=port, log_level='info')
