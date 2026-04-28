@echo off
REM ======================================================================
REM  OptiBoard - Fix one-shot du service (bug NSSM AppDirectory)
REM  Auto-eleve via PowerShell si pas deja en admin
REM ======================================================================

REM Auto-elevation
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Demande d'elevation administrateur...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b 0
)

echo.
echo ======================================================================
echo   OptiBoard - Reparation du service Windows
echo ======================================================================
echo.

set "APP_DIR=C:\OptiBoard"
set "NSSM=%APP_DIR%\nssm.exe"
set "SVC=OptiBoard-Backend"

if not exist "%NSSM%" (
    echo [ERREUR] %NSSM% introuvable.
    pause
    exit /b 1
)

echo [1/4] Arret du service...
"%NSSM%" stop %SVC% confirm >nul 2>&1
sc stop %SVC% >nul 2>&1
timeout /t 2 /nobreak >nul

echo [2/4] Correction AppDirectory (suppression du guillemet final)...
"%NSSM%" set %SVC% AppDirectory "%APP_DIR%"
if errorlevel 1 (
    echo [ERREUR] Impossible de corriger AppDirectory.
    pause
    exit /b 1
)

echo [3/4] Verification...
"%NSSM%" get %SVC% AppDirectory

echo [4/4] Demarrage du service...
"%NSSM%" start %SVC%
timeout /t 3 /nobreak >nul

echo.
echo ======================================================================
echo   FAIT. Statut du service:
echo ======================================================================
sc query %SVC% | findstr "STATE"
echo.
echo Ouvrez http://127.0.0.1:8084 dans votre navigateur.
echo La page de configuration apparaitra si .env n est pas configure.
echo.
pause
