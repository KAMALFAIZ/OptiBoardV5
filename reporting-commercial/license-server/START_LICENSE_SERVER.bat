@echo off
chcp 65001 >nul 2>&1
title OptiBoard - License Server
color 0B

echo ============================================
echo    OptiBoard - License Server v1.0
echo ============================================
echo.

:: Repertoire du script
cd /d "%~dp0"

:: -----------------------------------------------
:: 1. Verifier Python
:: -----------------------------------------------
echo [1/4] Verification de Python...
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERREUR] Python n'est pas installe ou pas dans le PATH.
    echo Telechargez Python depuis : https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do echo [OK] %%i

:: -----------------------------------------------
:: 2. Creer/Activer le virtual environment
:: -----------------------------------------------
echo.
echo [2/4] Preparation de l'environnement...

if not exist "venv" (
    echo [INFO] Creation du virtual environment...
    python -m venv venv
    if %errorLevel% neq 0 (
        echo [ERREUR] Impossible de creer le virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment cree.
)

:: Activer le venv
call venv\Scripts\activate.bat

:: -----------------------------------------------
:: 3. Installer les dependances
:: -----------------------------------------------
echo.
echo [3/4] Installation des dependances...
pip install -r requirements.txt -q
if %errorLevel% neq 0 (
    echo [ERREUR] Echec de l'installation des dependances.
    pause
    exit /b 1
)
echo [OK] Dependances installees.

:: -----------------------------------------------
:: 4. Verifier le fichier .env
:: -----------------------------------------------
echo.
echo [4/4] Verification de la configuration...

if not exist ".env" (
    echo [ATTENTION] Fichier .env non trouve !
    echo.
    echo Creation du fichier .env avec les valeurs par defaut...

    set "INPUT_DB_SERVER="
    set /p INPUT_DB_SERVER="  Serveur SQL Server [localhost] : "
    if "%INPUT_DB_SERVER%"=="" set "INPUT_DB_SERVER=localhost"

    set "INPUT_DB_NAME="
    set /p INPUT_DB_NAME="  Base de donnees [OptiBoard_Licenses] : "
    if "%INPUT_DB_NAME%"=="" set "INPUT_DB_NAME=OptiBoard_Licenses"

    set "INPUT_DB_USER="
    set /p INPUT_DB_USER="  Utilisateur SQL [sa] : "
    if "%INPUT_DB_USER%"=="" set "INPUT_DB_USER=sa"

    set "INPUT_DB_PASSWORD="
    set /p INPUT_DB_PASSWORD="  Mot de passe SQL : "

    set "INPUT_PORT="
    set /p INPUT_PORT="  Port du serveur [44100] : "
    if "%INPUT_PORT%"=="" set "INPUT_PORT=44100"

    echo # OptiBoard License Server Configuration > .env
    echo DB_SERVER=%INPUT_DB_SERVER% >> .env
    echo DB_NAME=%INPUT_DB_NAME% >> .env
    echo DB_USER=%INPUT_DB_USER% >> .env
    echo DB_PASSWORD=%INPUT_DB_PASSWORD% >> .env
    echo DB_DRIVER={ODBC Driver 17 for SQL Server} >> .env
    echo. >> .env
    echo LICENSE_SIGNING_SECRET=OptiBoard-LicKey-2026-KaSoft-SecretSign-HMAC256 >> .env
    echo. >> .env
    echo APP_NAME=OptiBoard License Server >> .env
    echo DEBUG=False >> .env
    echo PORT=%INPUT_PORT% >> .env

    echo [OK] Fichier .env cree.
) else (
    echo [OK] Fichier .env trouve.
)

:: -----------------------------------------------
:: Lire le port depuis .env
:: -----------------------------------------------
set "LICENSE_PORT=44100"
for /f "tokens=1,* delims==" %%a in ('findstr /i "^PORT=" .env') do (
    set "LICENSE_PORT=%%b"
)

:: -----------------------------------------------
:: Demarrage du serveur
:: -----------------------------------------------
echo.
echo ============================================
echo   License Server demarre !
echo ============================================
echo.
echo   URL      : http://localhost:%LICENSE_PORT%
echo   API Docs : http://localhost:%LICENSE_PORT%/docs
echo   Admin    : http://localhost:%LICENSE_PORT%/
echo.
echo   Appuyez sur Ctrl+C pour arreter.
echo ============================================
echo.

:: Ouvrir le navigateur
start "" http://localhost:%LICENSE_PORT%/docs

:: Demarrer uvicorn
python main.py

:: Si le serveur s'arrete
echo.
echo [INFO] Le serveur de licences s'est arrete.
pause
