@echo off
REM ======================================================================
REM  OptiBoard - Lanceur intelligent
REM
REM  - Demarre le service si arrete
REM  - Attend que l'API reponde (max 90 tentatives)
REM  - Apres 3 echecs HTTP, si service encore en cours -> mode setup probable
REM    -> ouvre le navigateur immediatement (wizard de setup)
REM  - Ouvre http://127.0.0.1:8084 dans le navigateur par defaut
REM ======================================================================

setlocal EnableExtensions EnableDelayedExpansion

set "APP_DIR=%~dp0"
REM Supprimer backslash final
if "!APP_DIR:~-1!"=="\" set "APP_DIR=!APP_DIR:~0,-1!"

set "SVC=OptiBoard-Backend"
set "NSSM=%APP_DIR%\nssm.exe"
set "URL=http://127.0.0.1:8084"
set "API_URL=%URL%/api/setup/status"
set "MAX_TRIES=90"
set "SETUP_TRIES=3"
set "POLL_SEC=3"

echo.
echo ======================================================================
echo   OptiBoard - Demarrage
echo ======================================================================
echo.

REM ---- Verifier si le service existe ------------------------------------
sc query %SVC% >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Le service '%SVC%' n'est pas installe.
    echo Veuillez lancer install_service.bat en tant qu'administrateur.
    echo.
    pause
    exit /b 1
)

REM ---- Demarrer le service si arrete ------------------------------------
sc query %SVC% | findstr /C:"STOPPED" >nul 2>&1
if %errorlevel% equ 0 (
    echo [1/2] Demarrage du service %SVC%...
    if exist "%NSSM%" (
        "%NSSM%" start %SVC% >nul 2>&1
    ) else (
        sc start %SVC% >nul 2>&1
    )
    timeout /t 2 /nobreak >nul
) else (
    echo [1/2] Service deja en cours.
)

REM ---- Attendre que l'API reponde ----------------------------------------
echo [2/2] Attente de l'API (max %MAX_TRIES% tentatives, %POLL_SEC%s/tentative)...
echo       URL : %API_URL%
echo.

set /a TRIES=0

:poll_loop
    set /a TRIES+=1

    REM Tester l'API avec PowerShell (timeout court)
    powershell -NoProfile -Command ^
        "$r = $null; try { $r = Invoke-WebRequest -Uri '%API_URL%' -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop; exit 0 } catch { exit 1 }" ^
        >nul 2>&1

    if %errorlevel% equ 0 (
        echo   API repond apres %TRIES% tentative(s). Ouverture du navigateur...
        goto :open_browser
    )

    REM Apres SETUP_TRIES echecs, si service pas STOPPED -> mode setup
    if !TRIES! equ !SETUP_TRIES! (
        sc query %SVC% 2>nul | findstr /C:"STOPPED" >nul 2>&1
        if errorlevel 1 (
            echo   Service actif mais API ne repond pas encore.
            echo   Mode SETUP probable (base non configuree).
            echo   Ouverture du navigateur pour le wizard de setup...
            goto :open_browser
        )
    )

    if !TRIES! geq %MAX_TRIES% (
        echo   Delai maximal depasse (%MAX_TRIES% tentatives).
        echo   Ouverture du navigateur malgre tout...
        goto :open_browser
    )

    set /a REMAINING=%MAX_TRIES%-%TRIES%
    echo   Tentative !TRIES!/%MAX_TRIES% - attente %POLL_SEC%s... (!REMAINING! restantes)
    timeout /t %POLL_SEC% /nobreak >nul
    goto :poll_loop

:open_browser
echo.
echo ======================================================================
echo   Ouverture de : %URL%
echo ======================================================================
start "" "%URL%"
echo.
endlocal
exit /b 0
