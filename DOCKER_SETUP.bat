@echo off
chcp 1252 >nul
title OptiBoard - Docker Manager (Windows Server 2022)
setlocal enabledelayedexpansion

:: ============================================================
::  OptiBoard - Docker Manager v3
::  Windows Server 2022  |  Images Linux via GHCR
::  Clic droit -> Executer en tant qu'administrateur
:: ============================================================

echo.
echo  ============================================================
echo   OptiBoard - Docker Manager  ^|  Windows Server 2022
echo  ============================================================
echo.

:: -- Verification droits Administrateur ----------------------
net session >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo  [ERREUR] Droits administrateur requis.
    echo  Clic droit sur DOCKER_SETUP.bat -^> Executer en tant qu'administrateur
    echo.
    pause & exit /b 1
)
echo  [OK] Administrateur confirme
echo.

:: -- Menu ----------------------------------------------------
echo  [1] Installer Docker         (Docker Engine + Compose)
echo  [2] Verifier l'installation  (diagnostic complet)
echo  [3] Creer le fichier .env    (parametres base de donnees)
echo  [4] Deployer OptiBoard       (pull GHCR + docker compose up)
echo  [4W] Deployer via WSL2       (si Hyper-V indisponible - VM)
echo  [5] Etat des conteneurs      (docker compose ps)
echo  [6] Voir les logs            (docker compose logs)
echo  [7] Arreter OptiBoard        (docker compose down)
echo  [8] Quitter
echo.
set /p CHOIX="  Votre choix [1-8] : "
echo.

if /i "%CHOIX%"=="1"  goto INSTALL
if /i "%CHOIX%"=="2"  goto VERIFY
if /i "%CHOIX%"=="3"  goto CREATE_ENV
if /i "%CHOIX%"=="4"  goto DEPLOY
if /i "%CHOIX%"=="4w" goto DEPLOY_WSL
if /i "%CHOIX%"=="5"  goto STATUS
if /i "%CHOIX%"=="6"  goto LOGS
if /i "%CHOIX%"=="7"  goto STOP
if /i "%CHOIX%"=="8"  goto FIN
echo  [!] Choix invalide. & goto FIN

:: ============================================================
:INSTALL
:: ============================================================
echo  == 1/5  Features Windows ===================================
echo.
powershell -NoProfile -Command "Install-WindowsFeature -Name Containers -IncludeAllSubFeature" >nul 2>&1
echo  [OK] Containers
powershell -NoProfile -Command "Install-WindowsFeature -Name Hyper-V -IncludeManagementTools" >nul 2>&1
echo  [OK] Hyper-V
powershell -NoProfile -Command "Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux -NoRestart" >nul 2>&1
powershell -NoProfile -Command "Enable-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform -NoRestart" >nul 2>&1
echo  [OK] WSL2

echo.
echo  == 2/5  Docker Engine ======================================
echo.
docker --version >nul 2>&1
if %ERRORLEVEL% equ 0 (
    for /f "delims=" %%v in ('docker --version') do echo  [OK] Docker deja installe : %%v
    goto COMPOSE_INSTALL
)

set "DOCKER_VER=27.3.1"
set "DOCKER_ZIP=C:\docker-engine.zip"
echo  [*] Telechargement Docker Engine %DOCKER_VER%...
powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://download.docker.com/win/static/stable/x86_64/docker-%DOCKER_VER%.zip' -OutFile '%DOCKER_ZIP%' -UseBasicParsing"
if %ERRORLEVEL% neq 0 ( echo  [ERREUR] Echec telechargement & pause & exit /b 1 )

echo  [*] Extraction...
powershell -NoProfile -Command "Expand-Archive -Path '%DOCKER_ZIP%' -DestinationPath 'C:\Program Files' -Force"
del /f /q "%DOCKER_ZIP%" >nul 2>&1
echo  [OK] Extrait dans C:\Program Files\Docker

echo  [*] Ajout au PATH systeme...
powershell -NoProfile -Command "[Environment]::SetEnvironmentVariable('Path', $env:Path + ';C:\Program Files\Docker', [System.EnvironmentVariableTarget]::Machine)"
set "PATH=%PATH%;C:\Program Files\Docker"

echo  [*] Enregistrement service dockerd...
"C:\Program Files\Docker\dockerd.exe" --register-service
if %ERRORLEVEL% neq 0 ( echo  [ERREUR] Echec enregistrement service & pause & exit /b 1 )

net start Docker >nul 2>&1
sc config Docker start= auto >nul 2>&1
timeout /t 5 /nobreak >nul
echo  [OK] Service Docker demarre (demarrage automatique)

:COMPOSE_INSTALL
echo.
echo  == 3/5  Docker Compose =====================================
echo.
docker compose version >nul 2>&1
if %ERRORLEVEL% equ 0 (
    for /f "delims=" %%v in ('docker compose version') do echo  [OK] %%v
    goto DAEMON_CONFIG
)
set "COMPOSE_DIR=%ProgramFiles%\Docker\cli-plugins"
if not exist "%COMPOSE_DIR%" mkdir "%COMPOSE_DIR%"
echo  [*] Telechargement Docker Compose v2.27.1...
powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://github.com/docker/compose/releases/download/v2.27.1/docker-compose-windows-x86_64.exe' -OutFile '%COMPOSE_DIR%\docker-compose.exe' -UseBasicParsing"
if %ERRORLEVEL% neq 0 ( echo  [ERREUR] Echec telechargement Compose & pause & exit /b 1 )
echo  [OK] Docker Compose v2.27.1 installe

:DAEMON_CONFIG
echo.
echo  == 4/5  Configuration daemon ================================
echo.
set "DAEMON_DIR=%ProgramData%\Docker\config"
if not exist "%DAEMON_DIR%" mkdir "%DAEMON_DIR%"
powershell -NoProfile -Command "$c='{\"experimental\":true,\"features\":{\"buildkit\":true},\"log-driver\":\"json-file\",\"log-opts\":{\"max-size\":\"10m\",\"max-file\":\"3\"}}'; Set-Content -Path '%DAEMON_DIR%\daemon.json' -Value $c -Encoding UTF8"
echo  [OK] daemon.json configure
net stop Docker >nul 2>&1 & timeout /t 3 /nobreak >nul
net start Docker >nul 2>&1 & timeout /t 5 /nobreak >nul
echo  [OK] Service Docker redemarre

echo.
echo  == 5/5  Dossier OptiBoard ==================================
echo.
if not exist "C:\optiboard"           mkdir "C:\optiboard"
if not exist "C:\optiboard\nginx\ssl" mkdir "C:\optiboard\nginx\ssl"
if not exist "C:\optiboard\logs"      mkdir "C:\optiboard\logs"
echo  [OK] C:\optiboard cree

set "SRC=%~dp0"
if exist "%SRC%docker-compose.prod.yml" (
    copy /y "%SRC%docker-compose.prod.yml" "C:\optiboard\" >nul
    echo  [OK] docker-compose.prod.yml copie
)
if exist "%SRC%nginx\nginx.prod.conf" (
    copy /y "%SRC%nginx\nginx.prod.conf" "C:\optiboard\nginx\" >nul
    echo  [OK] nginx.prod.conf copie
)

docker version >nul 2>&1
if %ERRORLEVEL% equ 0 ( echo  [OK] Docker repond ) else ( echo  [WARN] Docker muet - redemarrage Windows peut etre necessaire )

echo.
echo  ============================================================
echo   Installation terminee !
echo  ============================================================
echo.
echo  Etapes suivantes :
echo  [3] Creer le .env   ->  parametres SQL Server
echo  [4] Deployer        ->  demarrer OptiBoard
echo.
set /p RB="  Redemarrer Windows maintenant ? (o/n) : "
if /i "!RB!"=="o" shutdown /r /t 10 /c "Redemarrage Docker"
goto FIN

:: ============================================================
:VERIFY
:: ============================================================
echo  == Diagnostic =============================================
echo.
set ERRORS=0

echo  [1/7] Feature Containers...
powershell -NoProfile -Command "try { if ((Get-WindowsFeature -Name Containers).Installed) { Write-Host '  [OK] Installe' } else { Write-Host '  [KO] Non installe' } } catch { Write-Host '  [INFO] Non disponible' }" 2>nul

echo  [2/7] Hyper-V (requis pour conteneurs Linux)...
powershell -NoProfile -Command "try { if ((Get-WindowsFeature -Name Hyper-V).Installed) { $svc=(Get-Service vmms -EA SilentlyContinue).Status; if ($svc -eq 'Running') { Write-Host '  [OK] Installe et actif' } else { Write-Host '  [WARN] Installe mais inactif - redemarrage requis' } } else { Write-Host '  [KO] Non installe - Linux containers impossible' } } catch { Write-Host '  [INFO] Verification impossible' }" 2>nul
set /a ERRORS+=0

echo  [3/7] Service Docker...
sc query Docker >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo  [KO] Service introuvable - lancez option [1]
    set /a ERRORS+=1
) else (
    sc query Docker | findstr "RUNNING" >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        echo  [OK] En cours d'execution
    ) else (
        echo  [KO] Service arrete - tentative demarrage...
        net start Docker >nul 2>&1
        set /a ERRORS+=1
    )
)

echo  [4/7] Docker Engine...
docker version >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo  [OK] Docker repond
) else (
    echo  [KO] Docker ne repond pas
    set /a ERRORS+=1
)

echo  [5/7] Docker Compose...
docker compose version >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo  [OK] Docker Compose present
) else (
    echo  [KO] Docker Compose introuvable
    set /a ERRORS+=1
)

echo  [6/7] docker-compose.prod.yml...
if exist "C:\optiboard\docker-compose.prod.yml" (
    echo  [OK] Present dans C:\optiboard\
) else (
    echo  [KO] Absent - lancez option [1]
    set /a ERRORS+=1
)

echo  [7/7] Fichier .env...
if exist "C:\optiboard\.env" (
    echo  [OK] Present dans C:\optiboard\
) else (
    echo  [KO] Absent - lancez option [3]
    set /a ERRORS+=1
)

echo.
echo  ------------------------------------------------------------
if !ERRORS! equ 0 (
    echo   BILAN : Tout est OK  -  Pret pour [4] Deployer
) else (
    echo   BILAN : !ERRORS! probleme(s) detecte(s)
)
echo  ------------------------------------------------------------
echo.
pause & goto FIN

:: ============================================================
:CREATE_ENV
:: ============================================================
echo  == Creation .env ==========================================
echo.

if exist "C:\optiboard\.env" (
    echo  [WARN] C:\optiboard\.env existe deja.
    set /p OVR="  Ecraser ? (o/n) : "
    if /i "!OVR!" neq "o" goto FIN
    echo.
)

echo  -- SQL Server --
set /p DB_SERVER="  Serveur SQL     (ex: 192.168.1.10 ou SRV\SQLEXPRESS) : "
set /p DB_NAME="  Base de donnees (ex: GROUPE_ALBOUGHAZE)               : "
set /p DB_USER="  Utilisateur     (ex: sa)                               : "
set /p DB_PASSWORD="  Mot de passe                                          : "
echo.
echo  -- Application --
set /p RAW_URL="  URL du serveur  (ex: 192.168.1.20 ou monsite.com)     : "

:: Ajouter http:// si absent
echo !RAW_URL! | findstr /i "^http" >nul 2>&1
if %ERRORLEVEL% neq 0 ( set "ALLOWED_ORIGINS=http://!RAW_URL!" ) else ( set "ALLOWED_ORIGINS=!RAW_URL!" )
echo  [OK] URL : !ALLOWED_ORIGINS!
echo.

echo  [*] Generation SECRET_KEY (64 caracteres)...
for /f "delims=" %%K in ('powershell -NoProfile -Command "-join ((48..57)+(65..90)+(97..122) | Get-Random -Count 64 | ForEach-Object {[char]$_})"') do set "SECRET_KEY=%%K"
echo  [OK] SECRET_KEY generee

if not exist "C:\optiboard" mkdir "C:\optiboard"

(
echo # OptiBoard v5 - Configuration Production
echo # Genere le %DATE% par DOCKER_SETUP.bat
echo.
echo # -- SQL Server
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
echo  Fichier cree :
echo  ----------------------------------------
type "C:\optiboard\.env"
echo  ----------------------------------------
echo.
echo  Pour modifier : notepad C:\optiboard\.env
echo  Etape suivante : option [4] Deployer
echo.
pause & goto FIN

:: ============================================================
:DEPLOY
:: ============================================================
echo  == Deploiement OptiBoard ===================================
echo.

:: -- Verifier Hyper-V actif, sinon basculer sur WSL2 automatiquement
echo  [*] Verification Hyper-V...
powershell -NoProfile -Command "(Get-Service vmms -ErrorAction SilentlyContinue).Status" 2>nul | findstr "Running" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo  [INFO] Hyper-V absent - bascule automatique sur WSL2
    echo.
    goto DEPLOY_WSL
)
echo  [OK] Hyper-V actif
echo.

:: -- Copier docker-compose.prod.yml si present a cote du .bat
set "SRC=%~dp0"
if exist "%SRC%docker-compose.prod.yml" (
    copy /y "%SRC%docker-compose.prod.yml" "C:\optiboard\" >nul
    echo  [OK] docker-compose.prod.yml mis a jour
)

if not exist "C:\optiboard\docker-compose.prod.yml" (
    echo  [ERREUR] docker-compose.prod.yml introuvable dans C:\optiboard\
    echo  Placez docker-compose.prod.yml dans le meme dossier que ce .bat
    pause & goto FIN
)
if not exist "C:\optiboard\.env" (
    echo  [ERREUR] .env introuvable dans C:\optiboard\
    set /p GE="  Creer le .env maintenant ? (o/n) : "
    if /i "!GE!"=="o" goto CREATE_ENV
    goto FIN
)

:: -- Login GHCR (skip si deja connecte)
echo  -- Connexion GitHub Container Registry --
echo.
docker pull ghcr.io/kamalfaiz/optiboard-backend:latest >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo  [OK] Deja connecte a ghcr.io
) else (
    echo  Token GitHub PAT requis (permission : read:packages)
    echo  Creer : https://github.com/settings/tokens/new  -^>  cocher read:packages
    echo.
    set /p GHCR_TOKEN="  Token PAT (ghp_...) : "
    echo !GHCR_TOKEN! | docker login ghcr.io -u kamalfaiz --password-stdin
    if !ERRORLEVEL! neq 0 (
        echo.
        echo  [ERREUR] Login GHCR echoue. Verifiez le token.
        pause & goto FIN
    )
    echo  [OK] Connecte a ghcr.io
)
echo.

:: -- Demarrer le service Docker si arrete
echo  [*] Demarrage service Docker...
sc query Docker >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo  [INFO] Service Docker introuvable - re-enregistrement...
    "C:\Program Files\Docker\dockerd.exe" --register-service >nul 2>&1
    sc config Docker start= auto >nul 2>&1
)
net start Docker >nul 2>&1
timeout /t 8 /nobreak >nul

docker version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo  [ERREUR] Docker daemon ne repond pas.
    echo  Essayez : net start Docker  puis relancez option [4]
    pause & goto FIN
)
echo  [OK] Docker daemon actif

:: -- Platform Linux (obligatoire sur Windows Server)
set DOCKER_DEFAULT_PLATFORM=linux/amd64

:: -- Pull images
cd /d "C:\optiboard"
echo  [*] Telechargement des images (linux/amd64)...
docker compose -f docker-compose.prod.yml pull
if %ERRORLEVEL% neq 0 (
    echo  [ERREUR] Impossible de telecharger les images.
    echo  Verifiez le token GHCR et la connexion internet.
    pause & goto FIN
)
echo.

:: -- Demarrage
echo  [*] Demarrage des conteneurs...
docker compose -f docker-compose.prod.yml up -d
echo.

:: -- Etat
echo  -- Etat des conteneurs --
docker compose -f docker-compose.prod.yml ps
echo.
echo  [OK] OptiBoard demarre
echo  Frontend : http://localhost
echo  API docs : http://localhost:8080/api/docs
echo.
pause & goto FIN

:: ============================================================
:DEPLOY_WSL
:: ============================================================
echo  == Deploiement via WSL2 (sans Hyper-V) ====================
echo.
echo  Cette methode installe Docker DANS Ubuntu (WSL2)
echo  et lance OptiBoard depuis Linux - pas besoin d'Hyper-V.
echo.

:: -- Verifier WSL disponible
wsl --status >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo  [ERREUR] WSL non disponible sur ce serveur.
    echo  Verifiez que VirtualMachinePlatform est active (option [1]).
    pause & goto FIN
)

:: -- Verifier Ubuntu installe
wsl -d Ubuntu -- echo ok >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo  [*] Installation Ubuntu dans WSL2...
    wsl --install -d Ubuntu --no-launch
    echo.
    echo  [!!] Ubuntu installe. Redemarrage requis.
    echo  Relancez DOCKER_SETUP.bat apres le redemarrage -^> option [4W].
    set /p RB2="  Redemarrer maintenant ? (o/n) : "
    if /i "!RB2!"=="o" shutdown /r /t 10 /c "WSL2 Ubuntu installation"
    pause & goto FIN
)
echo  [OK] Ubuntu WSL2 disponible

:: -- Installer Docker dans Ubuntu si absent
echo  [*] Verification Docker dans Ubuntu...
wsl -d Ubuntu -- docker version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo  [*] Installation Docker Engine dans Ubuntu...
    wsl -d Ubuntu -- bash -c "curl -fsSL https://get.docker.com | sh"
    wsl -d Ubuntu -- bash -c "sudo usermod -aG docker $USER"
    echo  [OK] Docker installe dans Ubuntu
)
wsl -d Ubuntu -- sudo service docker start >nul 2>&1
echo  [OK] Service Docker demarre dans Ubuntu

:: -- Copier les fichiers dans WSL2
echo  [*] Copie des fichiers vers Ubuntu...
set "SRC=%~dp0"
wsl -d Ubuntu -- mkdir -p /opt/optiboard/nginx/ssl
wsl -d Ubuntu -- cp /mnt/c/optiboard/.env /opt/optiboard/.env 2>nul
wsl -d Ubuntu -- bash -c "cp /mnt/$(echo %SRC:\=/%| sed 's/://g' | tr '[:upper:]' '[:lower:]')docker-compose.prod.yml /opt/optiboard/" 2>nul
if exist "C:\optiboard\docker-compose.prod.yml" (
    powershell -NoProfile -Command "wsl -d Ubuntu -- bash -c 'cp /mnt/c/optiboard/docker-compose.prod.yml /opt/optiboard/'"
    echo  [OK] docker-compose.prod.yml copie
)
if exist "C:\optiboard\.env" (
    powershell -NoProfile -Command "wsl -d Ubuntu -- bash -c 'cp /mnt/c/optiboard/.env /opt/optiboard/'"
    echo  [OK] .env copie
)

:: -- Login GHCR depuis Ubuntu
echo.
echo  Token GitHub PAT (read:packages) :
set /p GHCR_TOKEN="  Token PAT (ghp_...) : "
wsl -d Ubuntu -- bash -c "echo '%GHCR_TOKEN%' | docker login ghcr.io -u kamalfaiz --password-stdin"
if %ERRORLEVEL% neq 0 ( echo  [ERREUR] Login GHCR echoue & pause & goto FIN )
echo  [OK] Connecte a ghcr.io

:: -- Pull et deploy depuis Ubuntu
echo.
echo  [*] Telechargement et demarrage depuis Ubuntu...
wsl -d Ubuntu -- bash -c "cd /opt/optiboard && docker compose -f docker-compose.prod.yml pull && docker compose -f docker-compose.prod.yml up -d"
if %ERRORLEVEL% neq 0 ( echo  [ERREUR] Echec deploiement & pause & goto FIN )

echo.
wsl -d Ubuntu -- bash -c "cd /opt/optiboard && docker compose -f docker-compose.prod.yml ps"
echo.
echo  [OK] OptiBoard demarre via WSL2
echo  Frontend : http://localhost
echo  API docs : http://localhost:8080/api/docs
echo.
pause & goto FIN

:: ============================================================
:STATUS
:: ============================================================
echo  == Etat des conteneurs ====================================
echo.
cd /d "C:\optiboard" 2>nul
docker compose -f docker-compose.prod.yml ps
echo.
pause & goto FIN

:: ============================================================
:LOGS
:: ============================================================
echo  == Logs en direct (Ctrl+C pour quitter) ===================
echo.
cd /d "C:\optiboard" 2>nul
docker compose -f docker-compose.prod.yml logs -f --tail=50
echo.
pause & goto FIN

:: ============================================================
:STOP
:: ============================================================
echo  == Arret OptiBoard =========================================
echo.
set /p CONF="  Confirmer l'arret de tous les conteneurs ? (o/n) : "
if /i "!CONF!"=="o" (
    cd /d "C:\optiboard" 2>nul
    docker compose -f docker-compose.prod.yml down
    echo  [OK] Conteneurs arretes
)
echo.
pause & goto FIN

:: ============================================================
:FIN
echo.
echo  Appuyez sur une touche pour fermer...
pause >nul
endlocal
exit /b 0
