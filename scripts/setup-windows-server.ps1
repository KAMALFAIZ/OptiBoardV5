# ============================================================
# OptiBoard v5 — Setup Windows Server pour déploiement
# Exécuter en PowerShell ADMINISTRATEUR sur le serveur Windows
# ============================================================

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host " OptiBoard — Setup Windows Server    " -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan

# ── 1. Installer Git ────────────────────────────────────────
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "→ Installation Git..." -ForegroundColor Yellow
    winget install --id Git.Git -e --source winget --silent
    $env:PATH += ";C:\Program Files\Git\bin"
    Write-Host "✅ Git installé" -ForegroundColor Green
} else {
    Write-Host "✅ Git déjà installé" -ForegroundColor Green
}

# ── 2. Installer Docker Desktop ──────────────────────────────
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "→ Installation Docker Desktop..." -ForegroundColor Yellow
    Write-Host "⚠️  Télécharge et installe Docker Desktop manuellement depuis :"
    Write-Host "   https://www.docker.com/products/docker-desktop/"
    Write-Host "   Puis relance ce script."
    Write-Host ""
    Write-Host "   Ou via winget :"
    Write-Host "   winget install Docker.DockerDesktop"
    pause
} else {
    Write-Host "✅ Docker déjà installé" -ForegroundColor Green
}

# ── 3. Créer le dossier de déploiement ──────────────────────
$appDir = "C:\optiboard"
if (-not (Test-Path $appDir)) {
    New-Item -ItemType Directory -Path $appDir | Out-Null
    Write-Host "✅ Dossier créé : $appDir" -ForegroundColor Green
}

# ── 4. Cloner le repo GitHub ─────────────────────────────────
if (-not (Test-Path "$appDir\.git")) {
    Write-Host "→ Clonage du repo OptiBoard..." -ForegroundColor Yellow
    git clone https://github.com/KAMALFAIZ/OptiBoardV5.git $appDir
    Write-Host "✅ Repo cloné dans $appDir" -ForegroundColor Green
} else {
    Write-Host "✅ Repo déjà présent" -ForegroundColor Green
}

# ── 5. Créer le fichier .env ─────────────────────────────────
if (-not (Test-Path "$appDir\.env")) {
    Copy-Item "$appDir\.env.production.example" "$appDir\.env"
    Write-Host ""
    Write-Host "⚠️  IMPORTANT : Édite le fichier .env avec tes vraies valeurs !" -ForegroundColor Red
    Write-Host "   notepad $appDir\.env"
}

# ── 6. Installer le GitHub Actions Self-hosted Runner ────────
Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host " Installation du GitHub Actions Runner" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan

$runnerDir = "C:\actions-runner"
if (-not (Test-Path $runnerDir)) {
    New-Item -ItemType Directory -Path $runnerDir | Out-Null
}

Set-Location $runnerDir

# Télécharger le runner
$runnerVersion = "2.323.0"
$runnerUrl = "https://github.com/actions/runner/releases/download/v$runnerVersion/actions-runner-win-x64-$runnerVersion.zip"
Write-Host "→ Téléchargement du runner GitHub Actions v$runnerVersion..." -ForegroundColor Yellow
Invoke-WebRequest -Uri $runnerUrl -OutFile "actions-runner.zip"
Expand-Archive -Path "actions-runner.zip" -DestinationPath $runnerDir -Force
Remove-Item "actions-runner.zip"
Write-Host "✅ Runner téléchargé" -ForegroundColor Green

Write-Host ""
Write-Host "=====================================" -ForegroundColor Green
Write-Host " Setup terminé !"                      -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green
Write-Host ""
Write-Host "ETAPE SUIVANTE — Configurer le runner :" -ForegroundColor Yellow
Write-Host ""
Write-Host "  1. Va sur GitHub → KAMALFAIZ/OptiBoardV5"
Write-Host "     → Settings → Actions → Runners → New self-hosted runner"
Write-Host "     → Windows x64 → copie la commande 'config'"
Write-Host ""
Write-Host "  2. Dans PowerShell Admin, depuis C:\actions-runner :"
Write-Host "     .\config.cmd --url https://github.com/KAMALFAIZ/OptiBoardV5 --token TON_TOKEN_ICI"
Write-Host ""
Write-Host "  3. Installer comme service Windows (démarre automatiquement) :"
Write-Host "     .\svc.cmd install"
Write-Host "     .\svc.cmd start"
Write-Host ""
Write-Host "  4. Éditer C:\optiboard\.env avec tes valeurs de base de données"
Write-Host ""
