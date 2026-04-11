# ============================================================
#  OptiBoard - Setup OpenSSH Server (cote OptiBoard)
#  Lance en tant qu'Administrateur
# ============================================================

$ErrorActionPreference = "Stop"

function Write-Step { param($n, $msg) Write-Host "`n[$n] $msg" -ForegroundColor Cyan }
function Write-OK   { param($msg) Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Err  { param($msg) Write-Host "  [!!] $msg" -ForegroundColor Red }
function Write-Info { param($msg) Write-Host "  [..] $msg" -ForegroundColor Yellow }

Write-Host ""
Write-Host "============================================================" -ForegroundColor Blue
Write-Host "  OptiBoard - Installation OpenSSH Server (Cote OptiBoard)" -ForegroundColor Blue
Write-Host "============================================================" -ForegroundColor Blue

# ── ETAPE 1 : Installer OpenSSH Server ──────────────────────
Write-Step "1/5" "Installation OpenSSH Server..."
$cap = Get-WindowsCapability -Online -Name OpenSSH.Server*
if ($cap.State -eq "Installed") {
    Write-OK "OpenSSH Server deja installe"
} else {
    Write-Info "Installation en cours (peut prendre 1-2 minutes)..."
    Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0 | Out-Null
    Write-OK "OpenSSH Server installe"
}

# ── ETAPE 2 : Demarrer sshd ─────────────────────────────────
Write-Step "2/5" "Demarrage service sshd..."
Start-Service sshd
Set-Service sshd -StartupType Automatic
Write-OK "sshd demarre et configure en demarrage automatique"

# ── ETAPE 3 : Pare-feu ──────────────────────────────────────
Write-Step "3/5" "Configuration pare-feu (port 22)..."
$rule = Get-NetFirewallRule -Name "sshd_optiboard" -ErrorAction SilentlyContinue
if (-not $rule) {
    New-NetFirewallRule -Name "sshd_optiboard" -DisplayName "OpenSSH Server OptiBoard" `
        -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22 | Out-Null
    Write-OK "Regle pare-feu creee (port 22 TCP)"
} else {
    Write-OK "Regle pare-feu deja presente"
}

# ── ETAPE 4 : Creer utilisateur sageRelay ───────────────────
Write-Step "4/5" "Creation utilisateur sageRelay..."
$userExists = Get-LocalUser -Name "sageRelay" -ErrorAction SilentlyContinue
if (-not $userExists) {
    $pass = ConvertTo-SecureString "SageRelay2026!KA" -AsPlainText -Force
    New-LocalUser -Name "sageRelay" -Password $pass -Description "Sage reverse tunnel relay user" | Out-Null
    Set-LocalUser -Name "sageRelay" -PasswordNeverExpires $true
    net user sageRelay /passwordchg:no | Out-Null
    Write-OK "Utilisateur sageRelay cree"
} else {
    Write-OK "Utilisateur sageRelay existe deja"
}

# ── ETAPE 5 : Preparer authorized_keys ──────────────────────
Write-Step "5/5" "Preparation du dossier authorized_keys..."
$sshDir = "C:\Users\sageRelay\.ssh"
if (-not (Test-Path $sshDir)) {
    New-Item -ItemType Directory -Path $sshDir -Force | Out-Null
}
$authKeys = Join-Path $sshDir "authorized_keys"
if (-not (Test-Path $authKeys)) {
    New-Item -ItemType File -Path $authKeys -Force | Out-Null
}

# Permissions correctes sur .ssh
$acl = Get-Acl $sshDir
$acl.SetAccessRuleProtection($true, $false)
$acl.Access | ForEach-Object { $acl.RemoveAccessRule($_) | Out-Null }
$user = "sageRelay"
$rule = New-Object System.Security.AccessControl.FileSystemAccessRule($user, "FullControl", "ContainerInherit,ObjectInherit", "None", "Allow")
$acl.AddAccessRule($rule)
$admins = "BUILTIN\Administrators"
$rule2 = New-Object System.Security.AccessControl.FileSystemAccessRule($admins, "FullControl", "ContainerInherit,ObjectInherit", "None", "Allow")
$acl.AddAccessRule($rule2)
Set-Acl -Path $sshDir -AclObject $acl

Write-OK "Dossier .ssh prepare : $sshDir"

# ── ETAPE 6 : Configurer GatewayPorts dans sshd_config ──────
Write-Info "Configuration GatewayPorts dans sshd_config..."
$sshdConfig = "$env:ProgramData\ssh\sshd_config"
$content = Get-Content $sshdConfig -Raw

if ($content -notmatch "GatewayPorts yes") {
    # Supprimer ancienne valeur si presente
    $content = $content -replace "#?GatewayPorts.*", ""
    $content = $content.TrimEnd() + "`nGatewayPorts yes`n"
    Set-Content $sshdConfig $content -Encoding UTF8
    Write-OK "GatewayPorts yes ajoute dans sshd_config"
} else {
    Write-OK "GatewayPorts deja configure"
}

# Redemarrer sshd pour prendre en compte sshd_config
Restart-Service sshd
Write-OK "sshd redémarre"

# ── RESUME ──────────────────────────────────────────────────
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  OPTIBOARD PRET - Recap" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Utilisateur SSH      : sageRelay" -ForegroundColor White
Write-Host "  Dossier cle publique : C:\Users\sageRelay\.ssh\authorized_keys" -ForegroundColor White
Write-Host "  Port ecoute          : 22" -ForegroundColor White
Write-Host ""
Write-Host "  PROCHAINE ETAPE :" -ForegroundColor Yellow
Write-Host "  1. Copier le fichier optiboard_relay_key.pub (genere sur Sage)" -ForegroundColor Yellow
Write-Host "     dans : C:\Users\sageRelay\.ssh\authorized_keys" -ForegroundColor Yellow
Write-Host "  2. L'IP/hostname OptiBoard que Sage utilisera pour se connecter" -ForegroundColor Yellow
Write-Host ""
$ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -ne "127.0.0.1" } | Select-Object -First 1).IPAddress
Write-Host "  IP OptiBoard detectee : $ip" -ForegroundColor Cyan
Write-Host ""
Read-Host "Entree pour quitter"
