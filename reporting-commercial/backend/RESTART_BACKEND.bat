@echo off
REM ==========================================
REM Redemarrage du Backend OptiBoard
REM ==========================================

echo.
echo ============================================
echo   Redemarrage Backend OptiBoard
echo ============================================
echo.

cd /d "D:\FinAnnee\reporting-commercial\backend"

REM Arreter les processus Python existants sur le port 8080
echo [1/3] Arret des processus existants...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8080 ^| findstr LISTENING') do (
    echo       Arret du processus PID: %%a
    taskkill /F /PID %%a 2>nul
)

REM Tuer tous les processus python run.py
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *run.py*" 2>nul
taskkill /F /IM pythonw.exe 2>nul

REM Attendre un peu
timeout /t 3 /nobreak >nul

REM Verifier les fichiers corrigés
echo [2/3] Verification des corrections...
findstr /C:"_execute_query(" "app\services\agent_auth.py" >nul
if errorlevel 1 (
    echo       [ERREUR] agent_auth.py n'est pas corrige!
) else (
    echo       [OK] agent_auth.py corrige
)

findstr /C:"_execute_query(" "app\routes\agent_api.py" >nul
if errorlevel 1 (
    echo       [ERREUR] agent_api.py n'est pas corrige!
) else (
    echo       [OK] agent_api.py corrige
)

REM Demarrer le backend
echo [3/3] Demarrage du backend...
echo.

REM Activer l'environnement virtuel si existant
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM Demarrer avec Python directement dans une nouvelle fenetre
start "OptiBoard Backend" cmd /k "cd /d D:\FinAnnee\reporting-commercial\backend && python run.py"

echo.
echo ============================================
echo   Backend demarre!
echo ============================================
echo.
echo Le backend devrait etre accessible sur:
echo   http://localhost:8080
echo.
echo Pour tester l'agent: python test_agent_api.py
echo.
pause
