# =====================================================
#  OptiBoard - Configuration SSH Serveur Sage Windows
#  Lancer via setup_ssh_sage.bat (en Administrateur)
# =====================================================

$ErrorActionPreference = "Stop"

function Write-Step($msg) { Write-Host "`n[$msg]" -ForegroundColor Cyan }
function Write-OK($msg)   { Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Info($msg) { Write-Host "  [..] $msg" -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host "  [!!] $msg" -ForegroundColor Red }

Clear-Host
Write-Host "=====================================================" -ForegroundColor Blue
Write-Host "  OptiBoard - Configuration SSH Serveur Sage Windows" -ForegroundColor White
Write-Host "=====================================================" -ForegroundColor Blue

# ── Verifier administrateur ──────────────────────────────────────────────────
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]"Administrator")
if (-not $isAdmin) {
    Write-Err "Ce script doit etre execute en tant qu'Administrateur."
    Write-Err "Clic droit sur setup_ssh_sage.bat > Executer en tant qu'administrateur"
    Read-Host "`nAppuyer sur Entree pour quitter"
    exit 1
}
Write-OK "Droits Administrateur confirmes."

# ── Lecture cle publique depuis fichier ──────────────────────────────────────
Write-Host "`n-----------------------------------------------------" -ForegroundColor Gray
Write-Host "  Recherche de sage_tunnel_key.pub..." -ForegroundColor White
Write-Host "-----------------------------------------------------" -ForegroundColor Gray

# Chercher .pub dans le meme dossier que le script
$PubKeyPath = Join-Path $PSScriptRoot "sage_tunnel_key.pub"

if (Test-Path $PubKeyPath) {
    $PublicKey = (Get-Content $PubKeyPath -Raw).Trim()
    Write-OK "Cle publique lue depuis : $PubKeyPath"
} else {
    Write-Host "  Fichier sage_tunnel_key.pub non trouve dans : $PSScriptRoot" -ForegroundColor Yellow
    Write-Host "  Copier sage_tunnel_key.pub dans le meme dossier que ce script" -ForegroundColor Gray
    Write-Host "  OU taper le chemin complet du fichier .pub :" -ForegroundColor Gray
    $PubKeyPath = Read-Host "  Chemin du fichier .pub"
    if (-not (Test-Path $PubKeyPath)) {
        Write-Err "Fichier introuvable. Abandon."
        Read-Host "Entree pour quitter"; exit 1
    }
    $PublicKey = (Get-Content $PubKeyPath -Raw).Trim()
    Write-OK "Cle publique lue depuis : $PubKeyPath"
}

if ([string]::IsNullOrWhiteSpace($PublicKey)) {
    Write-Err "Cle publique vide. Abandon."
    Read-Host "Entree pour quitter"; exit 1
}

# ── Saisie mot de passe ──────────────────────────────────────────────────────
Write-Host "`n  Mot de passe pour le compte Windows 'sageTunnelUser'" -ForegroundColor Gray
Write-Host "  (non utilise pour SSH - obligatoire pour Windows)" -ForegroundColor Gray
$SecurePass = Read-Host "  Mot de passe" -AsSecureString
if ($SecurePass.Length -eq 0) {
    $SecurePass = ConvertTo-SecureString "Optiboard#Tunnel2024!" -AsPlainText -Force
    Write-Info "Mot de passe par defaut utilise."
}

# ── ETAPE 1 : OpenSSH Server ─────────────────────────────────────────────────
Write-Step "1/6 - Installation OpenSSH Server"
try {
    $cap = Get-WindowsCapability -Online | Where-Object { $_.Name -like "OpenSSH.Server*" }
    if ($cap.State -eq "Installed") {
        Write-OK "OpenSSH Server deja installe."
    } else {
        Write-Info "Installation en cours (peut prendre 1-2 minutes)..."
        Add-WindowsCapability -Online -Name "OpenSSH.Server~~~~0.0.1.0" | Out-Null
        Write-OK "OpenSSH Server installe."
    }
} catch {
    Write-Err "Echec installation OpenSSH Server : $_"
    Read-Host "Entree pour quitter"; exit 1
}

# ── ETAPE 2 : Demarrer sshd ──────────────────────────────────────────────────
Write-Step "2/6 - Demarrage service sshd"
try {
    Set-Service -Name sshd -StartupType Automatic
    Start-Service sshd
    Start-Sleep 2
    if ((Get-Service sshd).Status -eq "Running") {
        Write-OK "sshd demarre et configure en demarrage automatique."
    } else {
        throw "sshd ne tourne pas."
    }
} catch {
    Write-Err "Echec demarrage sshd : $_"
    Read-Host "Entree pour quitter"; exit 1
}

# ── ETAPE 3 : Pare-feu ───────────────────────────────────────────────────────
Write-Step "3/6 - Pare-feu Windows (port 22)"
try {
    $rule = Get-NetFirewallRule -Name "OpenSSH-Server-In-TCP" -ErrorAction SilentlyContinue
    if ($rule) {
        Write-OK "Regle pare-feu SSH deja presente."
    } else {
        New-NetFirewallRule -Name "OpenSSH-Server-In-TCP" `
            -DisplayName "OpenSSH Server - OptiBoard Tunnel" `
            -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22 | Out-Null
        Write-OK "Regle pare-feu creee (port 22 TCP entrant)."
    }
} catch {
    Write-Err "Pare-feu : $_"
}

# ── ETAPE 4 : Creer utilisateur ──────────────────────────────────────────────
Write-Step "4/6 - Compte Windows 'sageTunnelUser'"
try {
    $existing = Get-LocalUser -Name "sageTunnelUser" -ErrorAction SilentlyContinue
    if ($existing) {
        Write-OK "Utilisateur sageTunnelUser existe deja."
    } else {
        # Creer le compte sans les options booléennes (compatibilite Windows Server)
        New-LocalUser -Name "sageTunnelUser" -Password $SecurePass `
            -Description "OptiBoard SSH Tunnel - acces restreint" | Out-Null
        # Appliquer les options séparément
        Set-LocalUser -Name "sageTunnelUser" -PasswordNeverExpires $true
        # Desactiver le changement de mot de passe via net user
        net user sageTunnelUser /passwordchg:no | Out-Null
        Write-OK "Utilisateur sageTunnelUser cree."
    }
} catch {
    Write-Err "Creation utilisateur : $_"
    Read-Host "Entree pour quitter"; exit 1
}

# ── ETAPE 5 : Cle publique ───────────────────────────────────────────────────
Write-Step "5/6 - Deploiement cle publique SSH"
try {
    $sshDir  = "C:\Users\sageTunnelUser\.ssh"
    $authKey = "$sshDir\authorized_keys"

    if (-not (Test-Path $sshDir)) { New-Item -ItemType Directory -Path $sshDir -Force | Out-Null }

    Set-Content -Path $authKey -Value $PublicKey -Encoding UTF8 -Force

    # Permissions NTFS strictes (obligatoire OpenSSH Windows)
    icacls $authKey /inheritance:r | Out-Null
    icacls $authKey /grant "sageTunnelUser:(R)" | Out-Null
    icacls $authKey /grant "SYSTEM:(F)" | Out-Null
    icacls $authKey /grant "Administrators:(F)" | Out-Null

    Write-OK "Cle publique deployee : $authKey"
    Write-OK "Permissions NTFS appliquees."
} catch {
    Write-Err "Deploiement cle : $_"
    Read-Host "Entree pour quitter"; exit 1
}

# ── ETAPE 6 : sshd_config ────────────────────────────────────────────────────
Write-Step "6/6 - Configuration sshd_config"
try {
    $sshdConfig = "C:\ProgramData\ssh\sshd_config"
    $content    = Get-Content $sshdConfig -Raw

    if ($content -match "Match User sageTunnelUser") {
        Write-OK "Bloc 'Match User sageTunnelUser' deja present."
    } else {
        $block = @"

# OptiBoard SSH Tunnel - restriction utilisateur
Match User sageTunnelUser
    AllowTcpForwarding yes
    X11Forwarding no
    PermitTTY no
    ForceCommand internal-sftp
    PasswordAuthentication no
"@
        Add-Content -Path $sshdConfig -Value $block -Encoding UTF8
        Write-OK "Bloc restriction ajoute dans sshd_config."
    }

    # Redemarrer sshd
    Restart-Service sshd
    Start-Sleep 2
    if ((Get-Service sshd).Status -eq "Running") {
        Write-OK "sshd redemarre avec la nouvelle configuration."
    } else {
        throw "sshd ne tourne pas apres redemarrage."
    }
} catch {
    Write-Err "sshd_config : $_"
    Read-Host "Entree pour quitter"; exit 1
}

# ── SUCCES ───────────────────────────────────────────────────────────────────
$ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike "127.*" } | Select-Object -First 1).IPAddress

Write-Host "`n=====================================================" -ForegroundColor Green
Write-Host "  [OK] CONFIGURATION TERMINEE AVEC SUCCES" -ForegroundColor Green
Write-Host "=====================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  OpenSSH Server  : Installe et actif" -ForegroundColor White
Write-Host "  Pare-feu        : Port 22 TCP ouvert" -ForegroundColor White
Write-Host "  Utilisateur     : sageTunnelUser" -ForegroundColor White
Write-Host "  Cle publique    : C:\Users\sageTunnelUser\.ssh\authorized_keys" -ForegroundColor White
Write-Host "  sshd_config     : Restriction Match User appliquee" -ForegroundColor White
Write-Host ""
Write-Host "  Dans OptiBoard > Gestion DWH > Modifier :" -ForegroundColor Cyan
Write-Host "    Hote SSH    : $ip" -ForegroundColor Yellow
Write-Host "    Port SSH    : 22" -ForegroundColor White
Write-Host "    Utilisateur : sageTunnelUser" -ForegroundColor White
Write-Host "    Cle privee  : contenu de sage_tunnel_key" -ForegroundColor White
Write-Host "    Serveur SQL : .  (un seul point)" -ForegroundColor White
Write-Host ""

Read-Host "Appuyer sur Entree pour fermer"
