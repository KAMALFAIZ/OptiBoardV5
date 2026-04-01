# OptiBoard v5 - Setup Production Windows Server (sans Docker)
# Executer UNE SEULE FOIS en PowerShell ADMINISTRATEUR sur le serveur
# Prerequis : Python 3.11, Node 20, IIS actifs

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host " OptiBoard - Setup Production        " -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan

# 1. Creer les dossiers
New-Item -ItemType Directory -Path "C:\optiboard\backend"  -Force | Out-Null
New-Item -ItemType Directory -Path "C:\optiboard\logs"     -Force | Out-Null
New-Item -ItemType Directory -Path "C:\inetpub\wwwroot\optiboard" -Force | Out-Null
Write-Host "[OK] Dossiers crees" -ForegroundColor Green

# 2. Copier le backend depuis le repo clone
$repoPath = "C:\optiboard-setup\reporting-commercial\backend"
if (Test-Path $repoPath) {
    Copy-Item -Path "$repoPath\*" -Destination "C:\optiboard\backend" -Recurse -Force
    Write-Host "[OK] Backend copie" -ForegroundColor Green
}

# 3. Installer les dependances Python
Write-Host "[...] Installation dependances Python..." -ForegroundColor Yellow
cd "C:\optiboard\backend"
python -m pip install --upgrade pip
pip install -r requirements.txt
Write-Host "[OK] Dependances Python installees" -ForegroundColor Green

# 4. Creer le fichier .env
if (-not (Test-Path "C:\optiboard\backend\.env")) {
    $envContent = @"
DB_SERVER=localhost
DB_NAME=GROUPE_ALBOUGHAZE
DB_USER=sa
DB_PASSWORD=CHANGE_MOI
DB_DRIVER=ODBC Driver 17 for SQL Server
DEBUG=False
CACHE_TTL=300
MAX_ROWS=10000
QUERY_TIMEOUT=30
SECRET_KEY=CHANGE_MOI_LONGUE_CLE_ALEATOIRE
ALLOWED_ORIGINS=http://kasoft.selfip.net
"@
    $envContent | Out-File -FilePath "C:\optiboard\backend\.env" -Encoding UTF8
    Write-Host ""
    Write-Host "[!!] IMPORTANT : Edite C:\optiboard\backend\.env avec tes vraies valeurs !" -ForegroundColor Red
    Write-Host "     notepad C:\optiboard\backend\.env"
}

# 5. Creer le script de demarrage backend
$startScript = @"
@echo off
cd /d C:\optiboard\backend
python -m uvicorn run:app --host 0.0.0.0 --port 8080 --workers 2 >> C:\optiboard\logs\backend.log 2>&1
"@
$startScript | Out-File -FilePath "C:\optiboard\start-backend.bat" -Encoding ASCII
Write-Host "[OK] Script demarrage cree" -ForegroundColor Green

# 6. Enregistrer le backend comme tache planifiee Windows
$taskName = "OptiBoard-Backend"
$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

$action = New-ScheduledTaskAction `
    -Execute "C:\optiboard\start-backend.bat" `
    -WorkingDirectory "C:\optiboard\backend"

$trigger = New-ScheduledTaskTrigger -AtStartup

$principal = New-ScheduledTaskPrincipal `
    -UserId "NT AUTHORITY\SYSTEM" `
    -LogonType ServiceAccount `
    -RunLevel Highest

$settings = New-ScheduledTaskSettingsSet `
    -RestartCount 5 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0)

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Force | Out-Null

Start-ScheduledTask -TaskName $taskName
Write-Host "[OK] Backend demarre comme service" -ForegroundColor Green

# 7. Configurer IIS pour servir le frontend
Write-Host "[...] Configuration IIS..." -ForegroundColor Yellow

Import-Module WebAdministration -ErrorAction SilentlyContinue

# Installer URL Rewrite si absent
$rewriteModule = Get-WebConfiguration "system.webServer/rewrite" -ErrorAction SilentlyContinue
if (-not $rewriteModule) {
    Write-Host "[!] IIS URL Rewrite module requis." -ForegroundColor Yellow
    Write-Host "    Telecharge depuis : https://www.iis.net/downloads/microsoft/url-rewrite"
}

# Creer le site IIS OptiBoard
$siteName = "OptiBoard"
$existingSite = Get-Website -Name $siteName -ErrorAction SilentlyContinue
if ($existingSite) {
    Remove-Website -Name $siteName
}

New-Website -Name $siteName `
    -Port 80 `
    -PhysicalPath "C:\inetpub\wwwroot\optiboard" `
    -Force | Out-Null

Start-Website -Name $siteName
Write-Host "[OK] Site IIS OptiBoard cree sur port 80" -ForegroundColor Green

Write-Host ""
Write-Host "=====================================" -ForegroundColor Green
Write-Host " Setup termine !"                      -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green
Write-Host ""
Write-Host "IMPORTANT - Faire maintenant :"
Write-Host "  1. notepad C:\optiboard\backend\.env"
Write-Host "     -> Remplir DB_SERVER, DB_PASSWORD, SECRET_KEY"
Write-Host ""
Write-Host "  2. Verifier le backend repond :"
Write-Host "     Invoke-WebRequest http://localhost:8080/api/docs"
Write-Host ""
Write-Host "  3. Depuis ton PC local, faire un push sur main"
Write-Host "     -> Le deploiement se fera automatiquement !"
Write-Host ""
