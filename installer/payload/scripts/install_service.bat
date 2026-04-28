@echo off
REM ======================================================================
REM  OptiBoard - Installation du service Windows via NSSM
REM  Lance: python\python.exe backend\run_service.py
REM  Parametre optionnel: %1 = repertoire d'installation (defaut: dossier du script)
REM ======================================================================

set "APP_DIR=%~dp0"
if not "%~1"=="" set "APP_DIR=%~1\"

REM Version SANS slash final - critique pour NSSM AppDirectory
REM Sinon le \" final est interprete comme un guillemet echappe par cmd
REM et NSSM enregistre la valeur avec un guillemet superflu (ex: C:\OptiBoard")
set "APP_DIR_NS=%APP_DIR%"
if "%APP_DIR_NS:~-1%"=="\" set "APP_DIR_NS=%APP_DIR_NS:~0,-1%"

set "PYEXE=%APP_DIR%python\python.exe"
set "SCRIPT=%APP_DIR%backend\run_service.py"
set "NSSM=%APP_DIR%nssm.exe"
set "SVC=OptiBoard-Backend"
set "LOGS=%APP_DIR%logs"

if not exist "%PYEXE%" (
    echo [ERREUR] Python introuvable: %PYEXE%
    exit /b 1
)
if not exist "%NSSM%" (
    echo [ERREUR] NSSM introuvable: %NSSM%
    exit /b 1
)
if not exist "%SCRIPT%" (
    echo [ERREUR] run_service.py introuvable: %SCRIPT%
    exit /b 1
)

REM Creer le dossier logs
if not exist "%LOGS%" mkdir "%LOGS%"

REM Stopper et supprimer le service existant
sc query %SVC% >nul 2>&1
if %errorlevel%==0 (
    "%NSSM%" stop %SVC% confirm >nul 2>&1
    "%NSSM%" remove %SVC% confirm >nul 2>&1
    timeout /t 2 /nobreak >nul
)

REM Installer le service sur python.exe + run_service.py
"%NSSM%" install %SVC% "%PYEXE%" "%SCRIPT%"
"%NSSM%" set %SVC% AppDirectory "%APP_DIR_NS%"
"%NSSM%" set %SVC% AppStdout "%LOGS%\backend.log"
"%NSSM%" set %SVC% AppStderr "%LOGS%\backend.error.log"
"%NSSM%" set %SVC% AppRotateFiles 1
"%NSSM%" set %SVC% AppRotateBytes 10485760
"%NSSM%" set %SVC% AppRestartDelay 5000
"%NSSM%" set %SVC% Start SERVICE_AUTO_START
"%NSSM%" set %SVC% DisplayName "OptiBoard Backend"
"%NSSM%" set %SVC% Description "Backend FastAPI OptiBoard - sert l API sur le port 8084"
"%NSSM%" set %SVC% AppEnvironmentExtra "OPTIBOARD_FRONTEND_DIR=%APP_DIR%frontend" "OPTIBOARD_SERVICE=1" "PYTHONUNBUFFERED=1"

REM Demarrer le service
"%NSSM%" start %SVC%

echo [OptiBoard] Service installe et demarre sur http://localhost:8084
exit /b 0
