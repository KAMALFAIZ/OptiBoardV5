@echo off
chcp 65001 >nul
title OptiBoard - Demarrage (backend + frontend)

REM ============================================================================
REM  OptiBoard - Lanceur de developpement
REM  Ouvre le backend (python run.py) et le frontend (npm run dev) chacun dans
REM  sa propre fenetre, puis ouvre le navigateur.
REM  Chemins deduits automatiquement de l'emplacement de ce .bat (%~dp0).
REM ============================================================================

set "ROOT=%~dp0"
set "BACKEND=%ROOT%reporting-commercial\backend"
set "FRONTEND=%ROOT%reporting-commercial\frontend"
set "PORT_BACKEND=8084"
set "PORT_FRONTEND=3003"

echo.
echo  ==========================================
echo        OptiBoard - Lancement Dev
echo  ==========================================
echo.

REM -- 1. Backend -------------------------------------------------------------
echo [1/3] Backend...
powershell -NoProfile -Command "try { Invoke-WebRequest -Uri 'http://127.0.0.1:%PORT_BACKEND%/api/setup/status' -TimeoutSec 3 -UseBasicParsing | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if %errorlevel% == 0 (
    echo      Deja actif sur le port %PORT_BACKEND% ^(service NSSM ou instance en cours^) - rien a faire.
) else (
    echo      Demarrage dans une nouvelle fenetre ^(python run.py^)...
    start "OptiBoard Backend" /D "%BACKEND%" cmd /k "python run.py"
)

REM -- 2. Frontend ------------------------------------------------------------
echo [2/3] Frontend Vite...
start "OptiBoard Frontend" /D "%FRONTEND%" cmd /k "npm run dev"

REM -- 3. Navigateur ----------------------------------------------------------
echo [3/3] Ouverture du navigateur ^(dans 6s, le temps que Vite demarre^)...
timeout /t 6 /nobreak >nul
start "" "http://localhost:%PORT_FRONTEND%"

echo.
echo  Projet lance !
echo    Frontend : http://localhost:%PORT_FRONTEND%
echo    Backend  : http://127.0.0.1:%PORT_BACKEND%
echo.
echo  Fermez les fenetres "OptiBoard Backend" / "OptiBoard Frontend" pour arreter.
echo.
pause
