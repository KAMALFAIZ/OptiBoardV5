# ======================================================================
#  OptiBoard - Deploiement du correctif pivot V2 sur le serveur AMM
#  A EXECUTER SUR LE SERVEUR AMM, dans un PowerShell ADMINISTRATEUR,
#  depuis le dossier qui contient ce script (a cote de backend\ et frontend\).
#
#  Fait : arret service -> sauvegardes horodatees -> copie backend + frontend
#         -> redemarrage -> verification HTTP.
#  Ne touche JAMAIS au .env (absent de la source).
# ======================================================================
param(
    [string]$InstallDir   = 'C:\OptiBoard',
    [string]$FrontendDir  = '',            # auto-detecte si vide
    [string]$ServiceName  = 'OptiBoard-Backend',
    [int]   $Port         = 8084
)
$ErrorActionPreference = 'Stop'
function Say($m){ Write-Host $m -ForegroundColor Cyan }
function Ok ($m){ Write-Host $m -ForegroundColor Green }

$here    = Split-Path -Parent $MyInvocation.MyCommand.Path
$srcBack = Join-Path $here 'backend'
$srcFront= Join-Path $here 'frontend'
$dstBack = Join-Path $InstallDir 'backend'
$stamp   = Get-Date -Format 'yyyyMMdd_HHmmss'

# --- Prerequis ---
if (-not (Test-Path "$srcBack\app\routes\pivot_v2.pyc")) { throw "Source backend incomplete : $srcBack" }
if (-not (Test-Path "$srcFront\index.html"))             { throw "Source frontend incomplete : $srcFront" }
if (-not (Test-Path "$dstBack\.env"))                    { throw "Cible suspecte : $dstBack\.env absent (mauvais InstallDir ?)" }

# --- Cible frontend : auto-detection ---
if (-not $FrontendDir) {
    $candidats = @( (Join-Path $InstallDir 'frontend'), 'C:\inetpub\wwwroot\optiboard' )
    $FrontendDir = $candidats | Where-Object { Test-Path (Join-Path $_ 'index.html') } | Select-Object -First 1
    if (-not $FrontendDir) { throw "Dossier frontend introuvable. Relance avec -FrontendDir <chemin>" }
}
Say "Backend  : $dstBack"
Say "Frontend : $FrontendDir"
Write-Host ""

# --- 1) Arret service ---
Say "1) Arret du service $ServiceName ..."
Stop-Service $ServiceName -Force
(Get-Service $ServiceName).WaitForStatus('Stopped','00:00:40')
Start-Sleep -Seconds 3   # laisser python liberer les .pyd charges

# --- 2) Sauvegardes ---
$bakBack  = "${dstBack}_bak_$stamp"
$bakFront = "${FrontendDir}_bak_$stamp"
Say "2) Sauvegardes"
Copy-Item $dstBack $bakBack -Recurse -Force
if (-not (Test-Path "$bakBack\.env")) { throw "Sauvegarde backend incomplete (.env manquant)" }
Write-Host "   $bakBack"
Copy-Item $FrontendDir $bakFront -Recurse -Force
if (-not (Test-Path "$bakFront\index.html")) { throw "Sauvegarde frontend incomplete" }
Write-Host "   $bakFront"

# --- 3) Copies (robocopy /E : ecrase, n'efface rien ; .env jamais touche) ---
Say "3) Copie backend"
robocopy $srcBack $dstBack /E /R:2 /W:2 /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy backend a echoue (code $LASTEXITCODE)" }
if (-not (Test-Path "$dstBack\.env")) { throw "ANOMALIE : .env a disparu !" }
# Une source .py residuelle masquerait le bytecode compile
if (Test-Path "$dstBack\app\routes\pivot_v2.py") { Remove-Item "$dstBack\app\routes\pivot_v2.py" -Force }

Say "4) Copie frontend"
robocopy $srcFront $FrontendDir /E /R:2 /W:2 /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy frontend a echoue (code $LASTEXITCODE)" }

# --- 5) Redemarrage ---
Say "5) Redemarrage du service ..."
Start-Service $ServiceName
(Get-Service $ServiceName).WaitForStatus('Running','00:00:40')

# --- 6) Verification (uvicorn met quelques secondes a ecouter) ---
Say "6) Verification ..."
$status = $null
for ($i=1; $i -le 12; $i++) {
    Start-Sleep -Seconds 3
    try { $status = (Invoke-WebRequest "http://127.0.0.1:$Port/api/setup/status" -UseBasicParsing -TimeoutSec 8).StatusCode; break } catch { }
}
if ($status -eq 200) { Ok "   /api/setup/status -> HTTP 200" }
else { Write-Host "   /api/setup/status NE REPOND PAS - voir $InstallDir\logs\backend.error.log" -ForegroundColor Red }

# Marqueurs du correctif dans les fichiers reellement deployes
$bo = Select-String -Path "$dstBack\app\routes\pivot_v2.pyc" -Pattern 'custom_config vide ignoree' -Quiet
$fe = Get-ChildItem (Join-Path $FrontendDir 'assets') -Filter '*.js' |
      Where-Object { Select-String -Path $_.FullName -Pattern 'Ajoutez au moins un champ en Zone Ligne' -Quiet -Encoding utf8 }
if ($bo) { Ok "   correctif backend  : present" }  else { Write-Host "   correctif backend  : ABSENT" -ForegroundColor Red }
if ($fe) { Ok "   correctif frontend : present ($($fe[0].Name))" } else { Write-Host "   correctif frontend : ABSENT" -ForegroundColor Red }

Write-Host ""
Ok "DEPLOIEMENT TERMINE"
Write-Host "Rollback backend  : Stop-Service $ServiceName ; supprimer $dstBack ; renommer $bakBack en backend ; Start-Service $ServiceName"
Write-Host "Rollback frontend : supprimer $FrontendDir ; renommer $bakFront"
Write-Host ""
Write-Host "Cote navigateur : Ctrl+F5 sur https://amm.kasoft.ma (cache Cloudflare a purger si besoin)."
