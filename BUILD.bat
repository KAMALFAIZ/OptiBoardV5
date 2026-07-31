@echo off
chcp 65001 >nul 2>&1
title OptiBoard V5 - Build et Deploiement
color 0A

echo ============================================================
echo    OptiBoard V5 - Build et Deploiement
echo    B:\Kasoft-Platform\OptiBoardV5
echo ============================================================
echo.

set FRONTEND=B:\Kasoft-Platform\OptiBoardV5\reporting-commercial\frontend
set BACKEND=B:\Kasoft-Platform\OptiBoardV5\reporting-commercial\backend
set PYTHON=C:\Program Files\Python311\python.exe
set NGINX=C:\nginx\nginx.exe

REM ── FRONTEND BUILD ──────────────────────────────────────────
echo [1/3] Build Frontend React...
cd /d "%FRONTEND%"
call npm run build
if %errorLevel% neq 0 (
    echo [ERREUR] Build frontend echoue !
    pause
    exit /b 1
)
echo [OK] Frontend buildé dans %FRONTEND%\dist\
echo.

REM ── NGINX RELOAD ────────────────────────────────────────────
echo [2/3] Rechargement Nginx...
cd /d "C:\nginx"
"%NGINX%" -s reload
echo [OK] Nginx rechargé.
echo.

REM ── BACKEND RESTART ─────────────────────────────────────────
echo [3/3] Redémarrage Backend Python...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr "0.0.0.0:8084" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 2 /nobreak >nul

start /B "" "%PYTHON%" "%BACKEND%\run.py"
timeout /t 8 /nobreak >nul
echo [OK] Backend redémarré sur le port 8084.
echo.

REM ── VERIFICATION ────────────────────────────────────────────
echo ============================================================
echo    Verification...
echo ============================================================
curl -s -o nul -w "Frontend (nginx:8085) : %%{http_code}\n" http://localhost:8085/
curl -s -o nul -w "Backend  (api:8084)   : %%{http_code}\n" http://localhost:8084/api/health
echo.
echo ============================================================
echo    Deploiement termine ! https://optiboard.kasoft.ma/
echo ============================================================
pause
