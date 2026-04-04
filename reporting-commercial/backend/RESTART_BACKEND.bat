@echo off
REM ==========================================
REM Redemarrage du Backend OptiBoard (port 8084)
REM ==========================================

echo.
echo ============================================
echo   Redemarrage Backend OptiBoard
echo ============================================
echo.

cd /d "D:\OptiBoard v5\reporting-commercial\backend"

REM Arreter tous les processus Python sur le port 8084
echo [1/3] Arret des processus existants sur port 8084...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8084 ^| findstr LISTENING') do (
    echo       Arret du processus PID: %%a
    taskkill /F /PID %%a 2>nul
)

REM Arreter aussi les anciens processus sur 8083 si present
echo       Nettoyage ancien port 8083...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8083 ^| findstr LISTENING') do (
    echo       Arret ancien processus PID: %%a
    taskkill /F /PID %%a 2>nul
)

REM Attendre
timeout /t 2 /nobreak >nul

REM Activer l'environnement virtuel si existant
echo [2/3] Activation environnement...
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM Demarrer le backend sur port 8084
echo [3/3] Demarrage du backend sur port 8084...
echo.

start "OptiBoard Backend 8084" cmd /k "cd /d "D:\OptiBoard v5\reporting-commercial\backend" && python run.py"

echo.
echo ============================================
echo   Backend demarre sur http://localhost:8084
echo ============================================
echo.
pause
