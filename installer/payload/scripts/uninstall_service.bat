@echo off
REM ======================================================================
REM  OptiBoard - Desinstaller le service Windows
REM
REM  Usage : uninstall_service.bat [chemin_installation]
REM ======================================================================

REM Auto-elevation
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Elevation administrateur requise...
    powershell -Command "Start-Process '%~f0' -ArgumentList '%~1' -Verb RunAs -Wait"
    exit /b 0
)

setlocal

if "%~1"=="" (
    set "APP_DIR=C:\OptiBoard"
) else (
    set "APP_DIR=%~1"
)

set "SVC=OptiBoard-Backend"
set "NSSM=%APP_DIR%\nssm.exe"

echo.
echo ======================================================================
echo   OptiBoard - Desinstallation du service Windows
echo ======================================================================

if not exist "%NSSM%" (
    REM Tenter avec sc.exe si nssm manquant
    echo [INFO] nssm.exe absent, utilisation de sc.exe...
    sc stop %SVC% >nul 2>&1
    timeout /t 3 /nobreak >nul
    sc delete %SVC% >nul 2>&1
    goto :done
)

echo [1/3] Arret du service...
"%NSSM%" stop %SVC% confirm >nul 2>&1
sc stop %SVC% >nul 2>&1
timeout /t 4 /nobreak >nul

echo [2/3] Suppression du service...
"%NSSM%" remove %SVC% confirm

echo [3/3] Verification...
sc query %SVC% >nul 2>&1
if errorlevel 1 (
    echo   Service supprime avec succes.
) else (
    echo   ATTENTION: Le service existe encore. Redemarrez Windows pour finaliser.
)

:done
echo.
echo ======================================================================
echo   Desinstallation du service terminee.
echo ======================================================================
echo.
endlocal
exit /b 0
