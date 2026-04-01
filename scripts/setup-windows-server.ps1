# OptiBoard v5 - Setup Windows Server
# Executer en PowerShell ADMINISTRATEUR sur le serveur Windows

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host " OptiBoard - Setup Windows Server    " -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan

# 1. Verifier Git
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "[!] Git non trouve. Installation via winget..." -ForegroundColor Yellow
    winget install --id Git.Git -e --source winget --silent
    $env:PATH += ";C:\Program Files\Git\bin"
    Write-Host "[OK] Git installe" -ForegroundColor Green
} else {
    Write-Host "[OK] Git deja installe" -ForegroundColor Green
}

# 2. Verifier Docker
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host ""
    Write-Host "[!] Docker non trouve." -ForegroundColor Red
    Write-Host "    Installe Docker Desktop depuis : https://www.docker.com/products/docker-desktop/"
    Write-Host "    Ou lance : winget install Docker.DockerDesktop"
    Write-Host "    Puis relance ce script."
    pause
    exit 1
} else {
    Write-Host "[OK] Docker deja installe" -ForegroundColor Green
}

# 3. Creer le dossier de deploiement
$appDir = "C:\optiboard"
if (-not (Test-Path $appDir)) {
    New-Item -ItemType Directory -Path $appDir | Out-Null
    Write-Host "[OK] Dossier cree : $appDir" -ForegroundColor Green
} else {
    Write-Host "[OK] Dossier existe deja : $appDir" -ForegroundColor Green
}

# 4. Cloner ou mettre a jour le repo
if (-not (Test-Path "$appDir\.git")) {
    Write-Host "[...] Clonage du repo OptiBoard..." -ForegroundColor Yellow
    git clone https://github.com/KAMALFAIZ/OptiBoardV5.git $appDir
    Write-Host "[OK] Repo clone dans $appDir" -ForegroundColor Green
} else {
    Write-Host "[...] Mise a jour du repo..." -ForegroundColor Yellow
    Set-Location $appDir
    git pull origin main
    Write-Host "[OK] Repo mis a jour" -ForegroundColor Green
}

# 5. Creer le fichier .env si absent
if (-not (Test-Path "$appDir\.env")) {
    Copy-Item "$appDir\.env.production.example" "$appDir\.env"
    Write-Host ""
    Write-Host "[!!] IMPORTANT : Edite le fichier .env avec tes vraies valeurs !" -ForegroundColor Red
    Write-Host "     notepad $appDir\.env"
}

# 6. Telecharger le GitHub Actions Runner
Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host " Installation GitHub Actions Runner  " -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan

$runnerDir = "C:\actions-runner"
if (-not (Test-Path $runnerDir)) {
    New-Item -ItemType Directory -Path $runnerDir | Out-Null
}

if (-not (Test-Path "$runnerDir\run.cmd")) {
    $runnerVersion = "2.323.0"
    $runnerUrl = "https://github.com/actions/runner/releases/download/v$runnerVersion/actions-runner-win-x64-$runnerVersion.zip"
    $zipPath = "$runnerDir\runner.zip"

    Write-Host "[...] Telechargement runner v$runnerVersion..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $runnerUrl -OutFile $zipPath
    Write-Host "[...] Extraction..." -ForegroundColor Yellow
    Expand-Archive -Path $zipPath -DestinationPath $runnerDir -Force
    Remove-Item $zipPath
    Write-Host "[OK] Runner telecharge dans $runnerDir" -ForegroundColor Green
} else {
    Write-Host "[OK] Runner deja present" -ForegroundColor Green
}

Write-Host ""
Write-Host "=====================================" -ForegroundColor Green
Write-Host " Setup termine !"                      -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green
Write-Host ""
Write-Host "ETAPE SUIVANTE : Configurer le runner" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Va sur GitHub :"
Write-Host "   https://github.com/KAMALFAIZ/OptiBoardV5/settings/actions/runners/new"
Write-Host "   Choisis Windows x64 - copie le TOKEN de la commande config"
Write-Host ""
Write-Host "2. Dans PowerShell Admin, depuis C:\actions-runner :"
Write-Host "   cd C:\actions-runner"
Write-Host "   .\config.cmd --url https://github.com/KAMALFAIZ/OptiBoardV5 --token COLLE_TON_TOKEN_ICI"
Write-Host ""
Write-Host "3. Installer comme service Windows :"
Write-Host "   .\svc.cmd install"
Write-Host "   .\svc.cmd start"
Write-Host ""
Write-Host "4. Editer C:\optiboard\.env avec tes valeurs DB"
Write-Host "   notepad C:\optiboard\.env"
Write-Host ""
