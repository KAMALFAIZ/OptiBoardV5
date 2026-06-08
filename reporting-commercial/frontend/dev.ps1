# dev.ps1 — Démarre le backend si nécessaire, puis Vite
# Usage : .\dev.ps1

$BACKEND_URL = "http://127.0.0.1:8084/api/setup/status"
$BACKEND_DIR = "$PSScriptRoot\..\backend"
$MAX_WAIT    = 30   # secondes max pour attendre le backend

Write-Host "`n=== OptiBoard Dev Launcher ===" -ForegroundColor Cyan

# 1. Vérifier si le backend répond déjà
function Test-Backend {
    try {
        $r = Invoke-WebRequest -Uri $BACKEND_URL -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
        return $r.StatusCode -eq 200
    } catch { return $false }
}

if (Test-Backend) {
    Write-Host "✓ Backend déjà actif sur :8084" -ForegroundColor Green
} else {
    Write-Host "⚡ Backend non disponible — démarrage..." -ForegroundColor Yellow

    # Tuer les éventuels processus zombies sur 8084
    $pids = @(netstat -ano | Select-String ":8084 " | ForEach-Object {
        ($_ -split '\s+' | Where-Object { $_ -match '^\d+$' } | Select-Object -Last 1)
    } | Sort-Object -Unique)
    foreach ($p in $pids) {
        try { Stop-Process -Id ([int]$p) -Force -ErrorAction SilentlyContinue } catch {}
    }
    Start-Sleep 1

    # Lancer le backend Python en tâche de fond
    $pythonExe = "python"
    # Essayer d'abord le Python embedded de l'installeur
    $embeddedPy = "C:\OptiBoard\python\python.exe"
    if (Test-Path $embeddedPy) { $pythonExe = $embeddedPy }

    Write-Host "  Lancement : $pythonExe run.py" -ForegroundColor Gray
    $backendJob = Start-Process -FilePath $pythonExe `
        -ArgumentList "run.py" `
        -WorkingDirectory $BACKEND_DIR `
        -PassThru -WindowStyle Minimized

    # Attendre que le backend réponde
    $waited = 0
    while ($waited -lt $MAX_WAIT) {
        Start-Sleep 1
        $waited++
        Write-Host "  Attente backend... ($waited/$MAX_WAIT s)" -ForegroundColor Gray -NoNewline
        Write-Host "`r" -NoNewline
        if (Test-Backend) { break }
    }

    if (Test-Backend) {
        Write-Host "`n✓ Backend prêt sur :8084 (PID $($backendJob.Id))" -ForegroundColor Green
    } else {
        Write-Host "`n✗ Backend toujours indisponible après ${MAX_WAIT}s — Vite démarrera quand même" -ForegroundColor Red
        Write-Host "  Vérifiez les logs : $BACKEND_DIR\logs\" -ForegroundColor Red
    }
}

# 2. Démarrer Vite
Write-Host "`n🚀 Démarrage Vite..." -ForegroundColor Cyan
Set-Location $PSScriptRoot
npx vite
