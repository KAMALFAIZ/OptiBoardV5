# ======================================================================
#  OptiBoard - Deploiement backend protege (dist_client -> C:\OptiBoard\backend)
#  Arret service -> sauvegarde -> copie (preserve .env) -> redemarrage -> verif
#  Lance-moi via DEPLOY_BACKEND.bat (auto-eleve) ou depuis un shell admin.
# ======================================================================
param(
    # -NoPause : ne pas attendre de touche a la fin (execution automatisee/elevee).
    [switch]$NoPause
)
$ErrorActionPreference = 'Stop'

$src = 'D:\kasoft-platform\OptiBoard\reporting-commercial\backend\dist_client'
$dst = 'C:\OptiBoard\backend'
$svcName = 'OptiBoard-Backend'
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$bak = "C:\OptiBoard\backend_bak_$stamp"

function Say($m) { Write-Host $m -ForegroundColor Cyan }

# --- Verif prerequis ---
if (-not (Test-Path "$src\app\routes\etl_agents.pyc")) { throw "Source introuvable: $src (as-tu lance build_protected ?)" }
if (-not (Test-Path "$dst\.env")) { throw "Cible suspecte: $dst\.env absent (mauvais dossier ?)" }

Say "1) Arret du service $svcName ..."
Stop-Service $svcName -Force
(Get-Service $svcName).WaitForStatus('Stopped', '00:00:40')
Start-Sleep -Seconds 3   # laisser python liberer les .pyd charges

Say "2) Sauvegarde -> $bak"
Copy-Item $dst $bak -Recurse -Force
if (-not (Test-Path "$bak\.env")) { throw "Sauvegarde incomplete (.env manquant)" }

Say "3) Copie dist_client -> backend (preserve .env, sans suppression)"
# robocopy /E : copie recursive, ecrase les fichiers existants, n'efface rien.
# .env n'est PAS dans la source => jamais touche.
robocopy $src $dst /E /R:2 /W:2 /NFL /NDL /NJH /NJS /NP | Out-Null
$rc = $LASTEXITCODE
if ($rc -ge 8) { throw "robocopy a echoue (code $rc)" }
Say "   robocopy code $rc (0-7 = OK)"
if (-not (Test-Path "$dst\.env")) { throw "ANOMALIE: .env a disparu apres copie !" }

Say "4) Redemarrage du service ..."
Start-Service $svcName
(Get-Service $svcName).WaitForStatus('Running', '00:00:40')
Start-Sleep -Seconds 4

Say "5) Verification ..."
try {
    $st = (Invoke-WebRequest 'http://127.0.0.1:8084/api/setup/status' -UseBasicParsing -TimeoutSec 10).StatusCode
    Say "   /api/setup/status -> HTTP $st"
} catch { Write-Host "   setup/status: $($_.Exception.Message)" -ForegroundColor Yellow }

# Nouvel endpoint : doit renvoyer 401 (present) et non plus 404
$code = $null
try {
    Invoke-WebRequest 'http://127.0.0.1:8084/api/agents/for-dwh' -Headers @{'X-DWH-Code'='AMM'} -UseBasicParsing -TimeoutSec 10 | Out-Null
} catch { $code = $_.Exception.Response.StatusCode.value__ }
if ($code -eq 401) {
    Write-Host "   /api/agents/for-dwh -> 401 (route DEPLOYEE, auth cle exigee) : OK" -ForegroundColor Green
} elseif ($code -eq 404) {
    Write-Host "   /api/agents/for-dwh -> 404 : route ABSENTE (deploiement non pris en compte)" -ForegroundColor Red
} else {
    Write-Host "   /api/agents/for-dwh -> reponse $code" -ForegroundColor Yellow
}

# Enrolement par jeton : POST avec un corps vide => 422 (route presente, validation
# Pydantic refusee) et non 404. On evite volontairement un jeton bidon, qui
# declencherait la creation de la table APP_ETL_Enroll_Tokens pendant une simple verif.
$code2 = $null
try {
    Invoke-WebRequest 'http://127.0.0.1:8084/api/agents/enroll' -Method POST `
        -Body '{}' -ContentType 'application/json' -UseBasicParsing -TimeoutSec 10 | Out-Null
} catch { $code2 = $_.Exception.Response.StatusCode.value__ }
if ($code2 -eq 422) {
    Write-Host "   /api/agents/enroll  -> 422 (route DEPLOYEE, jeton exige) : OK" -ForegroundColor Green
} elseif ($code2 -eq 404) {
    Write-Host "   /api/agents/enroll  -> 404 : route ABSENTE (enrolement non deploye)" -ForegroundColor Red
} else {
    Write-Host "   /api/agents/enroll  -> reponse $code2" -ForegroundColor Yellow
}

Say ""
Say "Termine. Sauvegarde: $bak"
Say "En cas de souci: Stop-Service $svcName ; supprimer $dst ; renommer $bak en $dst ; Start-Service $svcName"
# Pause uniquement en session interactive : en execution automatisee (CI, agent,
# PowerShell -NonInteractive) ReadKey echoue ou bloque le script indefiniment.
if (-not $NoPause -and [Environment]::UserInteractive -and -not [Console]::IsInputRedirected) {
    Write-Host "`nAppuyez sur une touche pour fermer..." -ForegroundColor DarkGray
    try { [void][System.Console]::ReadKey($true) } catch { }
}
