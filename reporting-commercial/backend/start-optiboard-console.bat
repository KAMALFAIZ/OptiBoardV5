@echo off
REM Lanceur OptiBoard pour la supervision par la console KASOFT (port 8084).
REM Le CONSOLE_TOKEN est lu depuis .env (pas besoin de le passer ici).
cd /d "D:\kasoft-platform\OptiBoard\reporting-commercial\backend"
python -m uvicorn run:app --host 127.0.0.1 --port 8084
