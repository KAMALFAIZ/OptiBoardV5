"""Standalone Windows client entry point — API FastAPI + frontend React."""
import sys
import os
import threading
import webbrowser

# Resolve base directory (frozen PyInstaller or source)
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FRONTEND_DIST = os.path.join(BASE_DIR, 'frontend_dist')
PORT = int(os.environ.get('OPTIBOARD_PORT', '8084'))

# Import the main FastAPI app (registers all API routes)
from run import app  # noqa: E402

# Mount React frontend if the dist folder is present
if os.path.isdir(FRONTEND_DIST):
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse
    from fastapi.routing import APIRoute

    # Remove the JSON root defined in run.py so React SPA can own "/"
    app.router.routes = [
        r for r in app.router.routes
        if not (isinstance(r, APIRoute) and r.path == '/' and 'GET' in r.methods)
    ]

    # Mount Vite asset bundle
    assets_dir = os.path.join(FRONTEND_DIST, 'assets')
    if os.path.isdir(assets_dir):
        app.mount('/assets', StaticFiles(directory=assets_dir), name='frontend-assets')

    @app.get('/', include_in_schema=False)
    async def _root():
        return FileResponse(os.path.join(FRONTEND_DIST, 'index.html'))

    @app.get('/{full_path:path}', include_in_schema=False)
    async def _spa(full_path: str):
        """Serve React SPA for all non-API paths."""
        candidate = os.path.join(FRONTEND_DIST, full_path)
        if os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(os.path.join(FRONTEND_DIST, 'index.html'))


def _open_browser():
    import time
    time.sleep(2.5)
    webbrowser.open(f'http://localhost:{PORT}')


if __name__ == '__main__':
    import uvicorn
    threading.Thread(target=_open_browser, daemon=True).start()
    uvicorn.run(app, host='127.0.0.1', port=PORT, log_level='info')
