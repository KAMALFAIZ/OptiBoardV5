@echo off
REM ======================================================================
REM  OptiBoard - Installe la tache planifiee de sauvegarde quotidienne
REM
REM  Cree la tache "OptiBoard-Backup" : tous les jours a 02:00, lance
REM  backup_dbs.ps1 (sauvegarde de toutes les bases OptiBoard_* avec
REM  retention 30 jours). Le script .ps1 doit etre dans le meme dossier.
REM ======================================================================

REM Auto-elevation
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Demande d'elevation administrateur...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b 0
)

set "SCRIPT=%~dp0backup_dbs.ps1"
set "TASK=OptiBoard-Backup"

echo.
echo ======================================================================
echo   OptiBoard - Installation de la sauvegarde quotidienne
echo ======================================================================
echo   Tache    : %TASK%
echo   Script   : %SCRIPT%
echo   Horaire  : tous les jours a 02:00
echo ======================================================================
echo.

if not exist "%SCRIPT%" (
    echo [ERREUR] backup_dbs.ps1 introuvable dans %~dp0
    pause
    exit /b 1
)

schtasks /Create /TN "%TASK%" ^
    /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -File \"%SCRIPT%\"" ^
    /SC DAILY /ST 02:00 /RU SYSTEM /RL HIGHEST /F

if errorlevel 1 (
    echo [ERREUR] Creation de la tache echouee.
    pause
    exit /b 1
)

echo.
echo [OK] Tache planifiee creee.
echo.
echo Pour tester immediatement :  schtasks /Run /TN "%TASK%"
echo Journal des sauvegardes   :  C:\OptiBoard\backups\backup_log.txt
echo.
pause
exit /b 0
