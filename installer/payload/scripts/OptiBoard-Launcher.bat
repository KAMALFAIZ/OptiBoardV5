@echo off
REM ======================================================================
REM  OptiBoard Launcher - attend que le backend soit UP avant d'ouvrir
REM  le navigateur (max 5 minutes - initialisation SQL peut etre lente).
REM ======================================================================
setlocal EnableExtensions EnableDelayedExpansion

set "APP_DIR=%~dp0"
set "URL=http://127.0.0.1:8084"
set "PORT=8084"
set "SVC=OptiBoard-Backend"
set "NSSM=%APP_DIR%nssm.exe"
set "PYEXE=%APP_DIR%python\python.exe"
set "SCRIPT=%APP_DIR%backend\run_service.py"
set "MAX_TRIES=90"
set "SETUP_TRIES=3"

REM --- 1) Le port repond deja ? Ouvrir direct ---
call :check_port && goto :open_browser

REM --- 2) Service installe ? Le demarrer ---
sc query %SVC% >nul 2>&1
if %errorlevel%==0 (
    echo [OptiBoard] Demarrage du service %SVC%...
    net start %SVC% >nul 2>&1
    if errorlevel 1 (
        if exist "%NSSM%" "%NSSM%" restart %SVC% >nul 2>&1
    )
) else (
    REM Pas de service - lancer python directement en console
    echo [OptiBoard] Lancement direct via Python embedded...
    if exist "%PYEXE%" (
        set "OPTIBOARD_FRONTEND_DIR=%APP_DIR%frontend"
        set "PYTHONUNBUFFERED=1"
        start "OptiBoard" /min "%PYEXE%" "%SCRIPT%"
    ) else (
        echo ERREUR: python\python.exe introuvable dans %APP_DIR%
        pause
        exit /b 1
    )
)

REM --- 3) Attendre que le port reponde (max ~5 minutes) ---
echo [OptiBoard] Demarrage en cours - initialisation SQL Server...
echo [OptiBoard] Patience, cela peut prendre jusqu a 2 minutes au 1er demarrage.
echo.
set /a TRIES=0
:wait_loop
set /a TRIES+=1
<nul set /p "=  [!TRIES!/!MAX_TRIES!] En attente... "
>nul ping -n 3 127.0.0.1
call :check_port && (echo OK & goto :open_browser) || echo -

REM Apres SETUP_TRIES tentatives : si le service tourne encore, ouvrir
REM le navigateur directement (le backend demarre en mode setup si .env vide)
if !TRIES!==!SETUP_TRIES! (
    sc query %SVC% 2>nul | findstr /C:"STOPPED" >nul 2>&1
    if errorlevel 1 (
        echo.
        echo [OptiBoard] Service en cours de demarrage - ouverture du navigateur...
        echo [OptiBoard] Si la page de configuration s'affiche, renseignez vos parametres SQL.
        goto :open_browser
    )
)

REM A mi-chemin: verifier que le service n'est pas crash
if !TRIES!==20 (
    sc query %SVC% 2>nul | findstr /C:"STOPPED" >nul 2>&1
    if not errorlevel 1 (
        echo.
        echo [OptiBoard] Service STOPPE - crash au demarrage. Voir logs.
        goto :diag_menu
    )
)
if !TRIES! LSS !MAX_TRIES! goto :wait_loop

:diag_menu
echo.
echo ======================================================================
echo  OptiBoard ne repond pas sur %URL%
echo ======================================================================
echo.
echo  Causes probables :
echo   1. SQL Server inaccessible (normal si .env non configure)
echo      Editez: %APP_DIR%.env
echo      Cle: DB_SERVER, DB_NAME, DB_USER, DB_PASSWORD
echo.
echo   2. Consultez les logs: %APP_DIR%logs\backend.log
echo.
echo  Actions :
echo   1. Ouvrir les logs
echo   2. Editer le fichier .env
echo   3. Relancer le service et reessayer
echo   4. Ouvrir le navigateur quand meme
echo   5. Quitter
echo.
choice /c 12345 /n /m "Votre choix [1-5]: "
if errorlevel 5 exit /b 1
if errorlevel 4 goto :open_browser
if errorlevel 3 (
    if exist "%NSSM%" "%NSSM%" restart %SVC% >nul 2>&1
    set /a TRIES=0
    goto :wait_loop
)
if errorlevel 2 (
    start "" notepad "%APP_DIR%.env"
    exit /b 0
)
if errorlevel 1 (
    if exist "%APP_DIR%logs\backend.log" (
        start "" notepad "%APP_DIR%logs\backend.log"
    ) else (
        echo Aucun log trouve.
        pause
    )
)
exit /b 1

:open_browser
echo.
echo [OptiBoard] Ouverture du navigateur sur %URL%
start "" "%URL%"
exit /b 0

:check_port
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "try { $r = Invoke-WebRequest -Uri '%URL%' -UseBasicParsing -TimeoutSec 2 -MaximumRedirection 0 -ErrorAction Stop; exit 0 } catch { if ($_.Exception.Response) { exit 0 } else { exit 1 } }" >nul 2>&1
exit /b %errorlevel%
