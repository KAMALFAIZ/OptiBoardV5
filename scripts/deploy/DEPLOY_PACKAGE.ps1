# ======================================================================
#  OptiBoard - Deploiement d'un PAQUET pre-construit (backend + frontend)
#
#  A distinguer de DEPLOY.ps1 (meme dossier) : celui-la construit depuis un
#  depot present sur le serveur ; celui-ci deploie un paquet deja compile
#  ailleurs (dist_client + dist Vite) et copie tel quel. C'est la voie a
#  utiliser quand le serveur n'a ni sources ni chaine de build.
#
#  Paquet attendu A COTE de ce script :
#      backend\                       <- reporting-commercial/backend/dist_client
#      frontend\                      <- reporting-commercial/frontend/dist
#      encrypt_etl_agent_secrets.py   <- migration des secrets (facultatif)
#      agent\binpublish_new\          <- publish agent (FACULTATIF)
#
#  Le publish de l'agent alimente le bouton 'Agent Sage' de la console. S'il est
#  dans le paquet, il est copie vers <InstallDir>\agent\binpublish_new ; sinon
#  le script verifie seulement ce qui est deja sur le serveur. Sans publish (ni
#  OPTIBOARD_AGENT_DIR dans le .env), le telechargement repond 404 en listant
#  les chemins essayes.
#
#  A EXECUTER SUR LE SERVEUR, dans un PowerShell ADMINISTRATEUR, depuis le
#  dossier du paquet.
#
#  Fait : arret service -> sauvegardes horodatees -> copie -> redemarrage
#         -> verifications HTTP. Ne touche JAMAIS au .env (absent de la source).
#
#  Si le paquet embarque un changement de stockage des secrets, la migration se
#  lance APRES ce script, jamais avant (le backend deploye lit clair ET chiffre ;
#  l'ordre inverse enverrait un blob aux agents) :
#      python scripts\encrypt_etl_agent_secrets.py            # simulation
#      python scripts\encrypt_etl_agent_secrets.py --apply    # ecriture
# ======================================================================
param(
    [string]$InstallDir  = 'C:\OptiBoard',
    [string]$FrontendDir = '',              # auto-detecte si vide
    [string]$ServiceName = 'OptiBoard-Backend',
    [int]   $Port        = 8084,
    [switch]$SkipFrontend,
    [switch]$NoPause
)
$ErrorActionPreference = 'Stop'
function Say ($m) { Write-Host $m -ForegroundColor Cyan }
function Ok  ($m) { Write-Host $m -ForegroundColor Green }
function Warn($m) { Write-Host $m -ForegroundColor Yellow }

$here     = Split-Path -Parent $MyInvocation.MyCommand.Path
$srcBack  = Join-Path $here 'backend'
$srcFront = Join-Path $here 'frontend'
$srcAgent = Join-Path $here 'agent\binpublish_new'
$dstBack  = Join-Path $InstallDir 'backend'
$stamp    = Get-Date -Format 'yyyyMMdd_HHmmss'
$bakBack  = Join-Path $InstallDir "backend_bak_$stamp"

# --- Prerequis : source plausible ET bonne cible ---
if (-not (Test-Path "$srcBack\app")) {
    throw "Source backend incomplete : $srcBack (dossier app\ absent)"
}
if (-not (Test-Path "$dstBack\.env")) {
    throw "Cible suspecte : $dstBack\.env absent (mauvais -InstallDir ?)"
}

# --- Cible frontend : auto-detection (meme logique que deploy_AMM) ---
if (-not $SkipFrontend) {
    if (-not (Test-Path "$srcFront\index.html")) { throw "Source frontend incomplete : $srcFront" }
    if (-not $FrontendDir) {
        # Plusieurs dispositions existent selon les installations. 'C:\inetpub\optiboard'
        # est celle utilisee par DEPLOY.ps1 : l'oublier fait deployer dans un dossier
        # qui n'est pas celui servi, avec un backend a jour et un frontend fige.
        $candidats = @(
            (Join-Path $InstallDir 'frontend'),
            'C:\inetpub\optiboard',
            'C:\inetpub\wwwroot\optiboard'
        )
        $trouves = @($candidats | Where-Object { Test-Path (Join-Path $_ 'index.html') })
        $FrontendDir = $trouves | Select-Object -First 1
        if (-not $FrontendDir) {
            throw "Dossier frontend introuvable. Relancez avec -FrontendDir <chemin> ou -SkipFrontend"
        }
        if ($trouves.Count -gt 1) {
            Warn "Plusieurs dossiers frontend candidats : $($trouves -join ', ')"
            Warn "Retenu : $FrontendDir — verifiez que c'est bien celui servi par le serveur web,"
            Warn "sinon relancez avec -FrontendDir <chemin>."
        }
    }
}

Say "Backend  : $srcBack -> $dstBack"
if ($SkipFrontend) { Warn "Frontend : ignore (-SkipFrontend)" } else { Say "Frontend : $srcFront -> $FrontendDir" }
Write-Host ""

Say "1) Arret du service $ServiceName ..."
Stop-Service $ServiceName -Force
(Get-Service $ServiceName).WaitForStatus('Stopped', '00:00:40')
Start-Sleep -Seconds 3   # laisser python liberer les .pyd charges

Say "2) Sauvegarde backend -> $bakBack"
Copy-Item $dstBack $bakBack -Recurse -Force
if (-not (Test-Path "$bakBack\.env")) { throw "Sauvegarde incomplete (.env manquant)" }

Say "3) Copie backend (preserve .env, sans suppression)"
robocopy $srcBack $dstBack /E /R:2 /W:2 /NFL /NDL /NJH /NJS /NP | Out-Null
$rc = $LASTEXITCODE
if ($rc -ge 8) { throw "robocopy backend a echoue (code $rc)" }
Say "   robocopy code $rc (0-7 = OK)"
if (-not (Test-Path "$dstBack\.env")) { throw "ANOMALIE: .env a disparu apres copie !" }

if (-not $SkipFrontend) {
    $bakFront = "$FrontendDir" + "_bak_$stamp"
    Say "4) Sauvegarde frontend -> $bakFront puis copie"
    Copy-Item $FrontendDir $bakFront -Recurse -Force
    robocopy $srcFront $FrontendDir /E /R:2 /W:2 /NFL /NDL /NJH /NJS /NP | Out-Null
    $rcf = $LASTEXITCODE
    if ($rcf -ge 8) { throw "robocopy frontend a echoue (code $rcf)" }
    Say "   robocopy code $rcf (0-7 = OK)"
}

# --- Publish agent : copie seulement s'il est fourni dans le paquet ---
if (Test-Path "$srcAgent\SageETLAgent.exe") {
    $dstAgent = Join-Path $InstallDir 'agent\binpublish_new'
    Say "5) Copie du publish agent -> $dstAgent"
    New-Item -ItemType Directory -Force -Path $dstAgent | Out-Null
    robocopy $srcAgent $dstAgent /E /R:2 /W:2 /NFL /NDL /NJH /NJS /NP | Out-Null
    $rca = $LASTEXITCODE
    if ($rca -ge 8) { throw "robocopy agent a echoue (code $rca)" }
    Say "   robocopy code $rca (0-7 = OK)"
} else {
    Say "5) Publish agent absent du paquet - rien a copier"
}

# Le zip servi par la console est un cache : le purger apres toute mise a jour
# du publish, sinon l'ancienne version continue d'etre distribuee.
$staleZip = Join-Path $InstallDir 'agent\SageETLAgent.zip'
if (Test-Path $staleZip) {
    Remove-Item $staleZip -Force
    Say "   zip agent en cache supprime (regenere au 1er telechargement)"
}

Say "6) Redemarrage du service ..."
Start-Service $ServiceName
(Get-Service $ServiceName).WaitForStatus('Running', '00:00:40')
Start-Sleep -Seconds 4

Say "7) Verifications ..."
try {
    $st = (Invoke-WebRequest "http://127.0.0.1:$Port/api/setup/status" -UseBasicParsing -TimeoutSec 10).StatusCode
    Ok "   /api/setup/status -> HTTP $st"
} catch {
    Warn "   setup/status : $($_.Exception.Message)"
}

# /api/agents/enroll doit repondre 401 sur un jeton bidon (route presente).
$code = $null
try {
    Invoke-WebRequest "http://127.0.0.1:$Port/api/agents/enroll" -Method POST `
        -ContentType 'application/json' -Body '{"token":"probe"}' `
        -UseBasicParsing -TimeoutSec 10 | Out-Null
} catch { $code = $_.Exception.Response.StatusCode.value__ }
if     ($code -eq 401) { Ok   "   /api/agents/enroll -> 401 (route presente) : OK" }
elseif ($code -eq 404) { Warn "   /api/agents/enroll -> 404 : enrolement ABSENT du build deploye" }
else                   { Warn "   /api/agents/enroll -> $code (inattendu)" }

$agentPublish = Join-Path $InstallDir 'agent\binpublish_new\SageETLAgent.exe'
if (Test-Path $agentPublish) {
    Ok "   publish agent present : $agentPublish"
} else {
    Warn "   publish agent absent : deposez-le dans $InstallDir\agent\binpublish_new"
    Warn "   (ou pointez OPTIBOARD_AGENT_DIR vers son dossier), sinon 'Agent Sage' -> 404"
}

# Le frontend deploye doit etre celui reellement servi : si le serveur web pointe
# vers un autre dossier, le backend est a jour mais l'interface reste figee.
if (-not $SkipFrontend) {
    try {
        $localIndex = Get-Content (Join-Path $FrontendDir 'index.html') -Raw
        $served     = (Invoke-WebRequest "http://127.0.0.1:$Port/" -UseBasicParsing -TimeoutSec 10).Content
        $rx         = '(?:src|href)="[^"]*assets/(index-[^"]+\.js)"'
        $localJs    = [regex]::Match($localIndex, $rx).Groups[1].Value
        $servedJs   = [regex]::Match($served,     $rx).Groups[1].Value
        if ($localJs -and $servedJs -and $localJs -eq $servedJs) {
            Ok "   frontend servi = frontend deploye ($localJs)"
        } elseif ($servedJs) {
            Warn "   frontend servi ($servedJs) != deploye ($localJs)"
            Warn "   Le serveur web sert un AUTRE dossier : relancez avec -FrontendDir <chemin servi>"
        }
    } catch {
        Warn "   controle du frontend servi impossible : $($_.Exception.Message)"
    }
}

Write-Host ""
Ok "Deploiement termine. Sauvegarde backend : $bakBack"

if (-not $NoPause) { Read-Host "Appuyez sur Entree pour fermer" }
