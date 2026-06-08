@echo off
REM ======================================================================
REM  OptiBoard - Installer le service Windows via NSSM
REM
REM  Usage : install_service.bat [chemin_installation]
REM  Ex    : install_service.bat "C:\OptiBoard"
REM
REM  Si le parametre est absent, utilise C:\OptiBoard par defaut.
REM ======================================================================

REM Auto-elevation
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Elevation administrateur requise...
    powershell -Command "Start-Process '%~f0' -ArgumentList '%~1' -Verb RunAs -Wait"
    exit /b 0
)

setlocal EnableExtensions EnableDelayedExpansion

REM Chemin d'installation (parametre ou defaut)
if "%~1"=="" (
    set "APP_DIR=C:\OptiBoard"
) else (
    set "APP_DIR=%~1"
    REM Supprimer le backslash final si present (evite le bug trailing quote NSSM)
    if "!APP_DIR:~-1!"=="\" set "APP_DIR=!APP_DIR:~0,-1!"
)

set "SVC=OptiBoard-Backend"
set "NSSM=%APP_DIR%\nssm.exe"
set "PYTHON=%APP_DIR%\python\python.exe"
set "SCRIPT=%APP_DIR%\backend\run.py"
set "LOGS=%APP_DIR%\logs"

echo.
echo ======================================================================
echo   OptiBoard - Installation du service Windows
echo ======================================================================
echo   Dossier    : %APP_DIR%
echo   Service    : %SVC%
echo   Python     : %PYTHON%
echo   Script     : %SCRIPT%
echo ======================================================================
echo.

REM Verifications
if not exist "%NSSM%" (
    echo [ERREUR] nssm.exe introuvable : %NSSM%
    pause
    exit /b 1
)
if not exist "%PYTHON%" (
    echo [ERREUR] python.exe introuvable : %PYTHON%
    pause
    exit /b 1
)
if not exist "%SCRIPT%" (
    echo [ERREUR] run.py introuvable : %SCRIPT%
    pause
    exit /b 1
)

REM Creer le repertoire logs
if not exist "%LOGS%" mkdir "%LOGS%"

REM Supprimer le service existant si present
sc query %SVC% >nul 2>&1
if %errorlevel% equ 0 (
    echo [1/8] Service existant detecte - arret et suppression...
    "%NSSM%" stop %SVC% confirm >nul 2>&1
    sc stop %SVC% >nul 2>&1
    timeout /t 3 /nobreak >nul
    "%NSSM%" remove %SVC% confirm
    timeout /t 2 /nobreak >nul
) else (
    echo [1/8] Aucun service existant.
)

REM Installer le service
echo [2/8] Installation du service...
"%NSSM%" install %SVC% "%PYTHON%" "%SCRIPT%"
if errorlevel 1 (
    echo [ERREUR] Installation service echouee
    pause
    exit /b 1
)

REM --- CRITIQUE : AppDirectory sans backslash final (evite le bug trailing quote)
echo [3/8] Configuration AppDirectory...
set "BACK_DIR=%APP_DIR%\backend"
"%NSSM%" set %SVC% AppDirectory "%BACK_DIR%"

echo [4/8] Configuration affichage et description...
"%NSSM%" set %SVC% DisplayName "OptiBoard Backend"
"%NSSM%" set %SVC% Description "Serveur API OptiBoard (FastAPI/Uvicorn) - KAsoft"

echo [5/8] Demarrage automatique...
"%NSSM%" set %SVC% Start SERVICE_AUTO_START

echo [6/8] Configuration des logs...
"%NSSM%" set %SVC% AppStdout "%LOGS%\backend.log"
"%NSSM%" set %SVC% AppStderr "%LOGS%\backend.error.log"
"%NSSM%" set %SVC% AppStdoutCreationDisposition 4
"%NSSM%" set %SVC% AppStderrCreationDisposition 4
"%NSSM%" set %SVC% AppRotateFiles 1
"%NSSM%" set %SVC% AppRotateBytes 10485760
"%NSSM%" set %SVC% AppRotateOnline 1

echo [7/8] Variables d'environnement...
"%NSSM%" set %SVC% AppEnvironmentExtra "PYTHONPATH=%APP_DIR%\backend" "PYTHONDONTWRITEBYTECODE=1"

echo [8/8] Demarrage du service...
"%NSSM%" start %SVC%
timeout /t 4 /nobreak >nul

echo.
echo ======================================================================
echo   Service installe. Statut :
echo ======================================================================
sc query %SVC% | findstr /i "STATE"
echo.
echo   Interface : http://127.0.0.1:8084
echo   Logs      : %LOGS%\backend.log
echo ======================================================================
echo.
endlocal
exit /b 0
