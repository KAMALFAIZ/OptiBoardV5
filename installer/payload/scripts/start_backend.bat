@echo off
REM ======================================================================
REM  OptiBoard - Lancement manuel du backend (mode console, sans service)
REM ======================================================================
cd /d "%~dp0backend"

set "OPTIBOARD_FRONTEND_DIR=%~dp0frontend"
set "PYTHONUNBUFFERED=1"

echo.
echo ======================================================================
echo   OptiBoard Backend - Demarrage (mode console)
echo ======================================================================
echo.
echo   URL    : http://localhost:8084
echo   Stop   : CTRL+C ou fermer cette fenetre
echo.

"%~dp0python\python.exe" run_service.py 2>&1

pause
