# ============================================================
#  Sage Server - Setup Tunnel SSH Inverse vers OptiBoard
#  Lance en tant qu'Administrateur sur le SERVEUR SAGE
# ============================================================

$ErrorActionPreference = "Stop"

function Write-Step { param($n, $msg) Write-Host "`n[$n] $msg" -ForegroundColor Cyan }
function Write-OK   { param($msg) Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Err  { param($msg) Write-Host "  [!!] $msg" -ForegroundColor Red }
function Write-Info { param($msg) Write-Host "  [..] $msg" -ForegroundColor Yellow }

Write-Host ""
Write-Host "============================================================" -ForegroundColor Blue
Write-Host "  Sage Server - Configuration Tunnel SSH Inverse" -ForegroundColor Blue
Write-Host "============================================================" -ForegroundColor Blue
Write-Host ""
Write-Host "  Ce script configure le serveur Sage pour qu'il se connecte" -ForegroundColor Gray
Write-Host "  AUTOMATIQUEMENT a OptiBoard et maintienne le tunnel ouvert." -ForegroundColor Gray
Write-Host ""

# ── SAISIE IP OPTIBOARD ──────────────────────────────────────
Write-Host "  Entrer l'IP ou le nom de domaine de la machine OptiBoard" -ForegroundColor Yellow
Write-Host "  (l'adresse que ce serveur Sage peut joindre)" -ForegroundColor Gray
$OPTIBOARD_HOST = Read-Host "  IP/Hostname OptiBoard"
if ([string]::IsNullOrWhiteSpace($OPTIBOARD_HOST)) {
    Write-Err "Adresse OptiBoard requise."; Read-Host "Entree pour quitter"; exit 1
}

$PORT_LOCAL  = 14433   # Port sur OptiBoard qui redirige vers SQL Server Sage
$PORT_SQL    = 1433    # Port SQL Server sur Sage (local)
$SSH_USER    = "sageRelay"
$KEY_DIR     = "C:\tools\ssh"
$KEY_NAME    = "optiboard_relay_key"
$KEY_PATH    = Join-Path $KEY_DIR $KEY_NAME
$KEY_PUB     = "$KEY_PATH.pub"

# ── ETAPE 1 : Creer dossier cles ────────────────────────────
Write-Step "1/5" "Preparation dossier cles SSH..."
if (-not (Test-Path $KEY_DIR)) {
    New-Item -ItemType Directory -Path $KEY_DIR -Force | Out-Null
}
Write-OK "Dossier : $KEY_DIR"

# ── ETAPE 2 : Generer cle SSH pour Sage -> OptiBoard ────────
Write-Step "2/5" "Generation cle SSH Sage -> OptiBoard..."
if (Test-Path $KEY_PATH) {
    Write-OK "Cle deja existante : $KEY_PATH"
} else {
    # Utiliser ssh-keygen (inclus avec OpenSSH client Windows)
    & ssh-keygen -t ed25519 -f $KEY_PATH -N '""' -C "sage-to-optiboard-relay" 2>&1 | Out-Null
    if (-not (Test-Path $KEY_PATH)) {
        Write-Err "Echec generation cle. Verifier que OpenSSH Client est installe."
        Write-Info "Installer : Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0"
        Read-Host "Entree pour quitter"; exit 1
    }
    Write-OK "Cle generee : $KEY_PATH"
}

# Afficher la cle publique a copier sur OptiBoard
Write-Host ""
Write-Host "  ┌─────────────────────────────────────────────────────────┐" -ForegroundColor Yellow
Write-Host "  │  CLE PUBLIQUE - A copier dans OptiBoard authorized_keys │" -ForegroundColor Yellow
Write-Host "  └─────────────────────────────────────────────────────────┘" -ForegroundColor Yellow
$pubKey = Get-Content $KEY_PUB -Raw
Write-Host ""
Write-Host $pubKey.Trim() -ForegroundColor White
Write-Host ""
Write-Host "  Copier cette cle dans : C:\Users\sageRelay\.ssh\authorized_keys" -ForegroundColor Cyan
Write-Host "  (sur la machine OptiBoard)" -ForegroundColor Cyan
Write-Host ""
Read-Host "  Appuyer sur Entree une fois la cle copiee sur OptiBoard"

# ── ETAPE 3 : Tester la connexion SSH ───────────────────────
Write-Step "3/5" "Test connexion SSH vers OptiBoard ($OPTIBOARD_HOST)..."
Write-Info "Test TCP port 22..."
$tcp = Test-NetConnection -ComputerName $OPTIBOARD_HOST -Port 22 -WarningAction SilentlyContinue
if (-not $tcp.TcpTestSucceeded) {
    Write-Err "Port 22 inaccessible sur $OPTIBOARD_HOST"
    Write-Host "  -> Verifier que setup_optiboard_sshd.bat a ete lance sur OptiBoard" -ForegroundColor Gray
    Read-Host "Entree pour quitter"; exit 1
}
Write-OK "Port 22 accessible sur $OPTIBOARD_HOST"

# ── ETAPE 4 : Corriger permissions cle privee ───────────────
Write-Step "4/5" "Correction permissions cle privee..."
$acl = Get-Acl $KEY_PATH
$acl.SetAccessRuleProtection($true, $false)
$acl.Access | ForEach-Object { $acl.RemoveAccessRule($_) | Out-Null }
$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$rule = New-Object System.Security.AccessControl.FileSystemAccessRule($currentUser, "Read,Synchronize", "Allow")
$acl.AddAccessRule($rule)
Set-Acl -Path $KEY_PATH -AclObject $acl
Write-OK "Permissions corrigees (lecture seule pour $currentUser)"

# ── ETAPE 5 : Tache planifiee (tunnel persistant) ───────────
Write-Step "5/5" "Creation tache planifiee (tunnel permanent)..."

$keepTunnelScript = @"
# Script de maintien du tunnel SSH inverse
# Sage -> OptiBoard : port $PORT_LOCAL sur OptiBoard -> SQL Server local :$PORT_SQL

`$KeyPath      = '$KEY_PATH'
`$OptiboardHost = '$OPTIBOARD_HOST'
`$SshUser      = '$SSH_USER'
`$PortLocal    = $PORT_LOCAL
`$PortSQL      = $PORT_SQL

Write-Host "[$(Get-Date)] Demarrage tunnel SSH inverse..." -ForegroundColor Cyan

while (`$true) {
    try {
        Write-Host "[$(Get-Date)] Connexion SSH -> `$OptiboardHost..." -ForegroundColor Yellow
        & ssh -i `$KeyPath ``
              -R "`${PortLocal}:localhost:`${PortSQL}" ``
              -o "StrictHostKeyChecking=no" ``
              -o "ServerAliveInterval=30" ``
              -o "ServerAliveCountMax=3" ``
              -o "ExitOnForwardFailure=yes" ``
              -N "`${SshUser}@`${OptiboardHost}"
        Write-Host "[$(Get-Date)] Tunnel deconnecte. Reconnexion dans 10s..." -ForegroundColor Red
    } catch {
        Write-Host "[$(Get-Date)] Erreur: `$_. Reconnexion dans 10s..." -ForegroundColor Red
    }
    Start-Sleep -Seconds 10
}
"@

$keepTunnelPath = "C:\tools\ssh\keep_reverse_tunnel.ps1"
Set-Content $keepTunnelPath $keepTunnelScript -Encoding UTF8
Write-OK "Script tunnel cree : $keepTunnelPath"

# Supprimer ancienne tache si existe
$taskName = "SageReverseSSHTunnel"
$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Info "Ancienne tache supprimee"
}

$action   = New-ScheduledTaskAction -Execute "powershell.exe" `
            -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$keepTunnelPath`""
$trigger  = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 10 -RestartInterval (New-TimeSpan -Minutes 1)
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Force | Out-Null

# Demarrer immediatement
Start-ScheduledTask -TaskName $taskName
Write-OK "Tache planifiee creee et demarree : $taskName"

# ── RESUME FINAL ─────────────────────────────────────────────
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  TUNNEL INVERSE CONFIGURE" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Sage se connecte vers : $OPTIBOARD_HOST (port 22)" -ForegroundColor White
Write-Host "  Tunnel : OptiBoard:$PORT_LOCAL -> Sage:$PORT_SQL (SQL Server)" -ForegroundColor White
Write-Host "  Tache planifiee : $taskName (demarre au boot)" -ForegroundColor White
Write-Host ""
Write-Host "  COTE OPTIBOARD - Config DWH FOODIS :" -ForegroundColor Yellow
Write-Host "  - SSH : desactiver (le tunnel est gere par Sage)" -ForegroundColor Yellow
Write-Host "  - Serveur SQL : 127.0.0.1" -ForegroundColor Yellow
Write-Host "  - Port SQL    : $PORT_LOCAL" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Pour verifier que le tunnel est actif depuis OptiBoard :" -ForegroundColor Cyan
Write-Host "  Test-NetConnection -ComputerName 127.0.0.1 -Port $PORT_LOCAL" -ForegroundColor Cyan
Write-Host ""
Read-Host "Entree pour quitter"
