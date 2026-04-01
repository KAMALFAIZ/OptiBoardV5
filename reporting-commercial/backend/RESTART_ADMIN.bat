@echo off
REM ==========================================
REM Redemarrage Backend - NECESSITE ADMIN
REM ==========================================

REM Auto-elever en Admin si pas encore admin
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Elevation des droits d'administrateur requise...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo.
echo ============================================
echo   ARRET ET REDEMARRAGE DU BACKEND
echo   (Mode Administrateur)
echo ============================================
echo.

cd /d "D:\FinAnnee\reporting-commercial\backend"

echo [1/4] Arret du processus sur le port 8082...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8082 ^| findstr LISTENING') do (
    echo       Arret PID: %%a
    taskkill /F /PID %%a 2>nul
)

echo [2/4] Arret de tous les processus Python...
taskkill /F /IM python.exe 2>nul
taskkill /F /IM pythonw.exe 2>nul

echo [3/4] Attente liberation du port...
timeout /t 4 /nobreak >nul

REM Verifier que le port est libre
netstat -ano | findstr :8082 | findstr LISTENING >nul 2>&1
if not errorlevel 1 (
    echo ATTENTION: Le port 8082 est toujours occupe!
    echo Veuillez fermer manuellement le processus et relancer ce script.
    pause
    exit /b 1
)

echo [4/4] Demarrage du backend...
echo.

if exist "venv\Scripts\activate.bat" (
    start "OptiBoard Backend 8082" cmd /k "cd /d D:\FinAnnee\reporting-commercial\backend && call venv\Scripts\activate.bat && python run.py"
) else (
    start "OptiBoard Backend 8082" cmd /k "cd /d D:\FinAnnee\reporting-commercial\backend && python run.py"
)

echo.
echo ============================================
echo   Backend redémarre sur http://localhost:8082
echo ============================================
echo.
echo Attendez 5-10 secondes que le backend demarre
echo puis actualisez la page frontend.
echo.
pause
