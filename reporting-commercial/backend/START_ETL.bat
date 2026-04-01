@echo off
title ETL Multi-Tenant - OptiBoard
cd /d %~dp0

echo ========================================
echo    ETL Multi-Tenant - OptiBoard
echo ========================================
echo.

REM Verifier si le venv existe
if exist venv\Scripts\activate.bat (
    echo Activation de l'environnement virtuel...
    call venv\Scripts\activate.bat
) else (
    echo [ATTENTION] Environnement virtuel non trouve
    echo Utilisation de Python systeme
)

echo.
echo Modes disponibles:
echo   1. daemon  - Execution continue (recommande)
echo   2. once    - Synchronisation unique
echo   3. test    - Test de configuration
echo   4. source  - Sync une source specifique
echo.

set /p MODE="Choisir le mode (1-4) [1]: "
if "%MODE%"=="" set MODE=1

if "%MODE%"=="1" (
    echo.
    echo Demarrage en mode DAEMON...
    echo Appuyez sur Ctrl+C pour arreter
    echo.
    python etl\run_multitenant.py --mode daemon --log-level INFO
)

if "%MODE%"=="2" (
    echo.
    echo Execution unique...
    python etl\run_multitenant.py --mode once --log-level INFO
    pause
)

if "%MODE%"=="3" (
    echo.
    echo Test de configuration...
    python etl\run_multitenant.py --mode test --log-level INFO
    pause
)

if "%MODE%"=="4" (
    set /p SOURCE="Nom de la source: "
    echo.
    echo Synchronisation de la source %SOURCE%...
    python etl\run_multitenant.py --mode source --source %SOURCE% --log-level INFO
    pause
)

pause
