@echo off
chcp 65001 >nul
title OptiBoard - Demarrage Dev

set "ROOT=D:\kasoft-platform\OptiBoard"
set "BACKEND=%ROOT%\reporting-commercial\backend"
set "FRONTEND=%ROOT%\reporting-commercial\frontend"
set "PORT_BACKEND=8084"
set "PORT_FRONTEND=3003"

echo.
echo  ==========================================
echo        OptiBoard - Lancement Dev
echo  ==========================================
echo.

REM -- 1. Tuer les anciens processus Vite/Node --------------------------------
echo [1/4] Nettoyage des processus existants...
taskkill /IM "node.exe" /F >nul 2>&1
timeout /t 1 /nobreak >nul
echo      OK.

REM -- 2. Verifier le backend (service NSSM) ----------------------------------
echo [2/4] Verification du backend...
powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:%PORT_BACKEND%/api/setup/status' -TimeoutSec 3 -UseBasicParsing; exit 0 } catch { exit 1 }" >nul 2>&1
if %errorlevel% == 0 (
    echo      Backend OK - port %PORT_BACKEND% actif.
) else (
    echo      Backend non detecte - tentative de demarrage service...
    sc start OptiBoard-Backend >nul 2>&1
    timeout /t 5 /nobreak >nul
    powershell -Command "try { Invoke-WebRequest -Uri 'http://127.0.0.1:%PORT_BACKEND%/api/setup/status' -TimeoutSec 3 -UseBasicParsing | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
    if %errorlevel% == 0 (
        echo      Backend demarre OK.
    ) else (
        echo      [WARN] Service inaccessible - lancement manuel...
        start "OptiBoard Backend" /D "%BACKEND%" cmd /k "python run.py"
        timeout /t 5 /nobreak >nul
    )
)

REM -- 3. Lancer le frontend Vite ---------------------------------------------
echo [3/4] Demarrage du frontend Vite...
start "OptiBoard Frontend" /D "%FRONTEND%" cmd /k "npm run dev"
timeout /t 4 /nobreak >nul

REM -- 4. Ouvrir le navigateur -----------------------------------------------
echo [4/4] Ouverture du navigateur...
start "" "http://localhost:%PORT_FRONTEND%"

echo.
echo  Projet lance !
echo    Frontend : http://localhost:%PORT_FRONTEND%
echo    Backend  : http://127.0.0.1:%PORT_BACKEND%
echo.
echo  Fermez la fenetre "OptiBoard Frontend" pour arreter Vite.
echo.
pause
