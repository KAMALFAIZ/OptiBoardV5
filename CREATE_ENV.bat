@echo off
chcp 1252 >nul
title OptiBoard - Creation fichier .env
setlocal enabledelayedexpansion

echo.
echo  ============================================================
echo   OptiBoard - Creation du fichier .env
echo  ============================================================
echo.

:: -- Verification droits Administrateur
net session >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo  [ERREUR] Lance ce fichier en tant qu'Administrateur !
    pause
    exit /b 1
)

if exist "C:\optiboard\.env" (
    echo  [WARN] Un fichier .env existe deja dans C:\optiboard\
    echo.
    set /p OVERWRITE="  Ecraser l'existant ? (o/n) : "
    if /i "!OVERWRITE!" neq "o" goto FIN
    echo.
)

echo  Renseignez les valeurs ci-dessous.
echo  Appuyez sur ENTREE pour valider chaque champ.
echo.

:: ── SQL Server ────────────────────────────────────────────
echo  == Base de donnees SQL Server ==
echo.
set /p DB_SERVER="  IP ou nom du serveur SQL (ex: 192.168.1.10) : "
set /p DB_NAME="  Nom de la base de donnees             (ex: GROUPE_ALBOUGHAZE) : "
set /p DB_USER="  Utilisateur SQL                        (ex: sa) : "
set /p DB_PASSWORD="  Mot de passe SQL                       : "
echo.

:: ── Application ───────────────────────────────────────────
echo  == Application ==
echo.
set /p ALLOWED_ORIGINS="  URL du site (ex: http://192.168.1.20 ou https://monsite.com) : "

:: Generer une SECRET_KEY aleatoire
for /f "delims=" %%K in ('powershell -NoProfile -Command "[System.Web.Security.Membership]::GeneratePassword(64,8)" 2^>nul') do set "SECRET_KEY=%%K"
if "!SECRET_KEY!"=="" (
    for /f "delims=" %%K in ('powershell -NoProfile -Command "-join ((48..57)+(65..90)+(97..122) | Get-Random -Count 64 | ForEach-Object {[char]$_})"') do set "SECRET_KEY=%%K"
)
echo  [OK] SECRET_KEY generee automatiquement

echo.

:: ── Ecriture du fichier ───────────────────────────────────
if not exist "C:\optiboard" mkdir "C:\optiboard"

(
echo # OptiBoard v5 - Variables d'environnement Production
echo # Genere par CREATE_ENV.bat
echo.
echo # -- Base de donnees SQL Server
echo DB_SERVER=!DB_SERVER!
echo DB_NAME=!DB_NAME!
echo DB_USER=!DB_USER!
echo DB_PASSWORD=!DB_PASSWORD!
echo DB_DRIVER=ODBC Driver 17 for SQL Server
echo.
echo # -- Application
echo SECRET_KEY=!SECRET_KEY!
echo DEBUG=False
echo CACHE_TTL=300
echo MAX_ROWS=10000
echo QUERY_TIMEOUT=30
echo ALLOWED_ORIGINS=!ALLOWED_ORIGINS!
echo.
echo # -- GitHub
echo GITHUB_OWNER=kamalfaiz
) > "C:\optiboard\.env"

echo.
echo  ============================================================
echo   Fichier .env cree dans C:\optiboard\.env
echo  ============================================================
echo.
echo  Contenu enregistre :
echo.
type "C:\optiboard\.env"
echo.
echo  Vous pouvez editer manuellement : notepad C:\optiboard\.env
echo.
echo  PROCHAINE ETAPE : Lancer DOCKER_SETUP.bat -^> option [3] Deployer
echo.

:FIN
pause
endlocal
exit /b 0
