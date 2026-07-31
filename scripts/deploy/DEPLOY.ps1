# ============================================================
# OptiBoard - Script de déploiement après git pull
# ============================================================
# Usage : Lancer après "git pull" dans B:\Kasoft-Platform\OptiBoardV5
#   powershell -ExecutionPolicy Bypass -File C:\optiboard\DEPLOY.ps1
#
# Options :
#   -BackendOnly   : ne déploie que le backend (skip build frontend)
#   -FrontendOnly  : ne déploie que le frontend (skip backend)
# ============================================================

param(
    [switch]$BackendOnly,
    [switch]$FrontendOnly
)

$ErrorActionPreference = 'Continue'

$SRC = "B:\Kasoft-Platform\OptiBoardV5\reporting-commercial"
$DST_BACKEND = "C:\optiboard\backend"
$DST_FRONTEND = "C:\inetpub\optiboard"
# Port de CETTE instance uniquement (tache planifiee OptiBoard-Backend).
# Les autres instances de la machine (8084 = amm/optiboard.kasoft.ma, license-server...)
# ne doivent jamais etre touchees par ce script.
$BACKEND_PORT = 8080

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  OptiBoard Deployment" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Source   : $SRC"
Write-Host "Backend  : $DST_BACKEND"
Write-Host "Frontend : $DST_FRONTEND"
Write-Host ""

# ---------- BACKEND ----------
if (-not $FrontendOnly) {
    Write-Host "[1/4] Backup .env" -ForegroundColor Yellow
    $envBackup = Get-Content "$DST_BACKEND\.env" -Raw -ErrorAction SilentlyContinue
    if (-not $envBackup) {
        Write-Host "  ATTENTION: .env introuvable!" -ForegroundColor Red
    } else {
        Write-Host "  OK ($($envBackup.Length) chars)" -ForegroundColor Green
    }

    Write-Host "[2/4] Stop backend" -ForegroundColor Yellow
    # NE JAMAIS faire "Get-Process python | Stop-Process" : cette machine heberge
    # d'autres backends Python (notamment OptiBoard-Backend-8084 qui sert
    # amm.kasoft.ma / optiboard.kasoft.ma, plus le license-server). On ne tue que
    # le processus qui ecoute sur NOTRE port, et ses enfants (workers uvicorn).
    schtasks /end /tn "OptiBoard-Backend" 2>&1 | Out-Null
    Start-Sleep -Seconds 2

    $ownPids = @(Get-NetTCPConnection -LocalPort $BACKEND_PORT -State Listen -ErrorAction SilentlyContinue |
                 Select-Object -ExpandProperty OwningProcess -Unique)
    if ($ownPids.Count -eq 0) {
        Write-Host "  Aucun processus en ecoute sur $BACKEND_PORT (deja arrete)" -ForegroundColor Gray
    }
    foreach ($ppid in $ownPids) {
        $proc = Get-Process -Id $ppid -ErrorAction SilentlyContinue
        if (-not $proc) { continue }
        if ($proc.ProcessName -notmatch '^(python|pythonw)$') {
            Write-Host "  Port $BACKEND_PORT tenu par $($proc.ProcessName) (PID $ppid) - non tue par securite" -ForegroundColor Red
            continue
        }
        # Enfants d'abord (uvicorn --workers N via multiprocessing), puis le parent
        Get-CimInstance Win32_Process -Filter "ParentProcessId=$ppid" -ErrorAction SilentlyContinue |
            ForEach-Object { try { Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop } catch {} }
        try { Stop-Process -Id $ppid -Force -ErrorAction Stop; Write-Host "  python PID $ppid arrete" -ForegroundColor Gray } catch {}
    }
    Start-Sleep -Seconds 2

    if (Get-NetTCPConnection -LocalPort $BACKEND_PORT -State Listen -ErrorAction SilentlyContinue) {
        Write-Host "  ATTENTION: port $BACKEND_PORT toujours occupe" -ForegroundColor Red
    } else {
        Write-Host "  OK" -ForegroundColor Green
    }

    Write-Host "[3/4] Copie backend" -ForegroundColor Yellow
    robocopy "$SRC\backend" "$DST_BACKEND" /E `
        /XD __pycache__ .venv venv logs etl_data .git `
        /XF .env *.log `
        /NFL /NDL /NP | Out-Null
    Write-Host "  OK (robocopy exit $LASTEXITCODE)" -ForegroundColor Green

    if ($envBackup) {
        Set-Content -Path "$DST_BACKEND\.env" -Value $envBackup -NoNewline
        Write-Host "  .env restauré" -ForegroundColor Green
    }

    Write-Host "[4/4] Start backend" -ForegroundColor Yellow
    schtasks /run /tn "OptiBoard-Backend" | Out-Null
    Write-Host "  OK (démarrage en cours, ~10s)" -ForegroundColor Green
}

# ---------- FRONTEND ----------
if (-not $BackendOnly) {
    Write-Host "`n[Frontend 1/2] Build" -ForegroundColor Yellow
    Push-Location "$SRC\frontend"

    # npm install seulement si package.json a changé
    if (-not (Test-Path "node_modules") -or
        ((Get-Item "package.json").LastWriteTime -gt (Get-Item "node_modules" -ErrorAction SilentlyContinue).LastWriteTime)) {
        Write-Host "  npm install..." -ForegroundColor Gray
        & npm install --silent 2>&1 | Out-Null
    }

    Write-Host "  npm run build..." -ForegroundColor Gray
    & npm run build 2>&1 | Out-Null
    $buildOk = Test-Path "$SRC\frontend\dist\index.html"
    Pop-Location

    if (-not $buildOk) {
        Write-Host "  BUILD FAILED" -ForegroundColor Red
        exit 1
    }
    Write-Host "  OK" -ForegroundColor Green

    Write-Host "[Frontend 2/2] Deploy dist -> $DST_FRONTEND" -ForegroundColor Yellow
    robocopy "$SRC\frontend\dist" "$DST_FRONTEND" /MIR /NFL /NDL /NP | Out-Null
    Write-Host "  OK (robocopy exit $LASTEXITCODE)" -ForegroundColor Green
}

# ---------- TESTS ----------
if (-not $FrontendOnly) {
    Write-Host "`nAttente démarrage backend..." -ForegroundColor Gray
    Start-Sleep -Seconds 12
}

Write-Host "`n=== Tests ===" -ForegroundColor Cyan
try {
    # NB: le backend ne sert pas de statiques (le HTML vient d'IIS/nginx),
    # donc on teste l'API et non la racine "/" qui repond 404 par design.
    $r = Invoke-WebRequest -Uri "http://localhost:$BACKEND_PORT/api/health" -UseBasicParsing -TimeoutSec 15
    Write-Host "  Backend /api/health : $($r.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "  Backend /api/health : FAILED ($($_.Exception.Message))" -ForegroundColor Red
}

try {
    $r = Invoke-WebRequest -Uri "http://localhost:$BACKEND_PORT/api/license/status" -UseBasicParsing -TimeoutSec 10
    $j = $r.Content | ConvertFrom-Json
    Write-Host "  License        : $($j.license.plan) ($($j.license.days_remaining) jours)" -ForegroundColor Green
} catch {
    Write-Host "  License        : FAILED" -ForegroundColor Red
}

try {
    $r = Invoke-WebRequest -Uri 'https://optiboard.kasoft.ma/?client=fo' -UseBasicParsing -TimeoutSec 15
    $isHtml = $r.Headers['Content-Type'] -match 'html'
    $color = if ($isHtml) {'Green'} else {'Red'}
    Write-Host "  Public URL     : $($r.StatusCode), $($r.Content.Length) chars, HTML=$isHtml" -ForegroundColor $color
} catch {
    Write-Host "  Public URL     : FAILED" -ForegroundColor Red
}

Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "  Déploiement terminé" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
