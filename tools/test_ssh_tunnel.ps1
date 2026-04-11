# =====================================================
#  OptiBoard - Test Tunnel SSH vers Serveur Sage
# =====================================================

function Write-OK($m)   { Write-Host "  [OK] $m" -ForegroundColor Green }
function Write-Err($m)  { Write-Host "  [!!] $m" -ForegroundColor Red }
function Write-Info($m) { Write-Host "  [..] $m" -ForegroundColor Yellow }
function Write-Step($m) { Write-Host "`n[$m]" -ForegroundColor Cyan }

Clear-Host
Write-Host "=====================================================" -ForegroundColor Blue
Write-Host "  OptiBoard - Test Tunnel SSH" -ForegroundColor White
Write-Host "=====================================================" -ForegroundColor Blue

# ── Saisie parametres ────────────────────────────────────────────────────────
Write-Host ""
# Chercher la cle privee automatiquement dans le meme dossier
$KeyPath = Join-Path $PSScriptRoot "sage_tunnel_key"
if (-not (Test-Path $KeyPath)) {
    Write-Host "  Cle privee non trouvee dans : $PSScriptRoot" -ForegroundColor Yellow
    Write-Host "  Taper le chemin complet vers le FICHIER cle (pas le dossier)" -ForegroundColor Gray
    Write-Host "  Exemple : C:\Users\Admin\sage_tunnel_key" -ForegroundColor Gray
    $KeyPath = Read-Host "  Chemin"
}

# Si l'utilisateur a entre un dossier, chercher la cle dedans
if (Test-Path $KeyPath -PathType Container) {
    $searchDir = $KeyPath
    # 1. Chercher sage_tunnel_key exactement
    $candidate = Join-Path $searchDir "sage_tunnel_key"
    if (Test-Path $candidate) {
        $KeyPath = $candidate
        Write-Info "Fichier trouve : $KeyPath"
    } else {
        # 2. Chercher tout fichier commencant par sage_tunnel (sauf .pub et authorized_keys)
        $found = Get-ChildItem -Path $searchDir -File | Where-Object {
            $_.Name -like "sage_tunnel*" -and $_.Extension -ne ".pub" -and $_.Name -ne "authorized_keys"
        } | Select-Object -First 1

        if ($found) {
            $KeyPath = $found.FullName
            Write-Info "Cle privee trouvee : $KeyPath"
        } else {
            # 3. Lister tous les fichiers et expliquer
            Write-Host ""
            Write-Host "  [!!] Cle privee 'sage_tunnel_key' introuvable dans : $searchDir" -ForegroundColor Red
            Write-Host ""
            Write-Host "  IMPORTANT : La cle privee 'sage_tunnel_key' est sur la machine OptiBoard," -ForegroundColor Yellow
            Write-Host "  PAS sur le serveur Sage. Ce script doit etre lance depuis OptiBoard" -ForegroundColor Yellow
            Write-Host "  ou depuis un PC qui possede le fichier sage_tunnel_key." -ForegroundColor Yellow
            Write-Host ""
            Write-Host "  Fichiers dans $searchDir :" -ForegroundColor Gray
            $files = Get-ChildItem -Path $searchDir -File -ErrorAction SilentlyContinue
            if (-not $files -or $files.Count -eq 0) {
                Write-Host "     (dossier vide)" -ForegroundColor Gray
            } else {
                $files | ForEach-Object {
                    $note = if ($_.Name -eq "authorized_keys") { "  <- cle PUBLIQUE (pas la bonne)" } else { "" }
                    Write-Host "     - $($_.Name)$note" -ForegroundColor White
                }
            }
            Write-Host ""
            Write-Host "  Si 'sage_tunnel_key' est dans un autre dossier, taper son chemin complet :" -ForegroundColor Gray
            Write-Host "  Exemple : C:\Users\Admin\Downloads\sage_tunnel_key" -ForegroundColor Gray
            $altPath = Read-Host "  Chemin complet (ou Entree pour quitter)"
            if ([string]::IsNullOrWhiteSpace($altPath)) {
                Read-Host "Entree pour quitter"; exit 1
            }
            if (-not (Test-Path $altPath -PathType Leaf)) {
                Write-Err "Fichier introuvable : $altPath"
                Read-Host "Entree pour quitter"; exit 1
            }
            $KeyPath = $altPath
            Write-Info "Fichier selectionne : $KeyPath"
        }
    }
}

if (-not (Test-Path $KeyPath)) {
    Write-Err "Fichier introuvable : $KeyPath"
    Read-Host "Entree pour quitter"; exit 1
}

# ── Corriger les permissions de la cle privee (obligatoire Windows SSH) ──────
Write-Info "Correction des permissions de la cle privee..."
try {
    $acl = Get-Acl $KeyPath
    # Supprimer l'heritage et toutes les regles existantes
    $acl.SetAccessRuleProtection($true, $false)
    $acl.Access | ForEach-Object { $acl.RemoveAccessRule($_) | Out-Null }
    # Ajouter uniquement l'utilisateur courant en lecture
    $user = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    $rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
        $user, "Read,Synchronize", "Allow")
    $acl.AddAccessRule($rule)
    Set-Acl -Path $KeyPath -AclObject $acl
    Write-OK "Permissions cle privee corrigees (lecture seule : $user)."
} catch {
    Write-Info "Avertissement permissions : $_ (on continue)"
}

Write-OK "Cle privee : $KeyPath"

$SageIP = Read-Host "IP du serveur Sage (ex: 192.168.1.10)"
if ([string]::IsNullOrWhiteSpace($SageIP)) {
    Write-Err "IP obligatoire."; Read-Host "Entree pour quitter"; exit 1
}

$LocalPort = Read-Host "Port local tunnel (Entree = 14433)"
if ([string]::IsNullOrWhiteSpace($LocalPort)) { $LocalPort = "14433" }

$SqlUser = Read-Host "Utilisateur SQL Server (ex: sa)"
if ([string]::IsNullOrWhiteSpace($SqlUser)) { $SqlUser = "sa" }

$SqlPass = Read-Host "Mot de passe SQL Server" -AsSecureString
$SqlPassPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SqlPass))

$SqlDb = Read-Host "Base de donnees SQL (Entree = master)"
if ([string]::IsNullOrWhiteSpace($SqlDb)) { $SqlDb = "master" }

# ── TEST 1 : SSH joignable ───────────────────────────────────────────────────
Write-Step "TEST 1/4 - Connexion SSH port 22"
try {
    $tcp = New-Object System.Net.Sockets.TcpClient
    $conn = $tcp.BeginConnect($SageIP, 22, $null, $null)
    $ok   = $conn.AsyncWaitHandle.WaitOne(3000, $false)
    $tcp.Close()
    if ($ok) {
        Write-OK "Port 22 accessible sur $SageIP"
    } else {
        Write-Err "Port 22 inaccessible sur $SageIP"
        Write-Host "     -> Verifier pare-feu et sshd sur le serveur Sage" -ForegroundColor Gray
        Read-Host "Entree pour quitter"; exit 1
    }
} catch {
    Write-Err "Erreur reseau : $_"
    Read-Host "Entree pour quitter"; exit 1
}

# ── TEST 2 : Authentification SSH ────────────────────────────────────────────
Write-Step "TEST 2/4 - Authentification SSH avec la cle privee"
Write-Info "Test de connexion SSH (5 secondes max)..."

$sshArgs = @(
    "-i", $KeyPath,
    "-o", "StrictHostKeyChecking=no",
    "-o", "ConnectTimeout=5",
    "-o", "BatchMode=yes",
    "sageTunnelUser@$SageIP",
    "echo SSH_OK"
)

$result = & ssh @sshArgs 2>&1
if ($LASTEXITCODE -eq 0 -or $result -match "SSH_OK|sftp") {
    Write-OK "Authentification SSH reussie."
} else {
    # Sur un serveur avec ForceCommand=internal-sftp, on attend une erreur sftp = auth OK
    $resultStr = "$result"
    if ($resultStr -match "sftp|subsystem|request") {
        Write-OK "Authentification SSH reussie (serveur restreint sftp - normal)."
    } else {
        Write-Err "Echec authentification SSH."
        Write-Host "     Details : $result" -ForegroundColor Gray
        Write-Host "     -> Verifier authorized_keys et permissions NTFS sur le serveur Sage" -ForegroundColor Gray
        Read-Host "Entree pour quitter"; exit 1
    }
}

# ── TEST 3 : Demarrer le tunnel ──────────────────────────────────────────────
Write-Step "TEST 3/4 - Demarrage tunnel SSH (port local $LocalPort -> SQL :1433)"
Write-Info "Ouverture du tunnel en arriere-plan..."

$tunnelArgs = "-i `"$KeyPath`" -o StrictHostKeyChecking=no -o ConnectTimeout=5 -N -L ${LocalPort}:localhost:1433 sageTunnelUser@$SageIP"
$tunnelProc = Start-Process ssh -ArgumentList $tunnelArgs -PassThru -WindowStyle Hidden
Start-Sleep 3

if ($tunnelProc.HasExited) {
    Write-Err "Le tunnel SSH a echoue (processus termine immediatement)."
    Write-Host "     -> Verifier AllowTcpForwarding dans sshd_config" -ForegroundColor Gray
    Read-Host "Entree pour quitter"; exit 1
}

# Verifier que le port local est ouvert
$tcpLocal = New-Object System.Net.Sockets.TcpClient
$connLocal = $tcpLocal.BeginConnect("127.0.0.1", [int]$LocalPort, $null, $null)
$okLocal   = $connLocal.AsyncWaitHandle.WaitOne(3000, $false)
$tcpLocal.Close()

if ($okLocal) {
    Write-OK "Tunnel actif : 127.0.0.1:$LocalPort -> $SageIP:1433"
} else {
    Write-Err "Port local $LocalPort non accessible (tunnel non etabli)."
    $tunnelProc | Stop-Process -Force -ErrorAction SilentlyContinue
    Read-Host "Entree pour quitter"; exit 1
}

# ── TEST 4 : Connexion SQL Server ────────────────────────────────────────────
Write-Step "TEST 4/4 - Connexion SQL Server via le tunnel"
Write-Info "Test connexion SQL sur 127.0.0.1,$LocalPort..."

$sqlCmd = "sqlcmd"
$sqlExists = Get-Command sqlcmd -ErrorAction SilentlyContinue
if (-not $sqlExists) {
    Write-Info "sqlcmd non trouve - test SQL ignore."
    Write-Host "     Installer SQL Server Command Line Tools si necessaire." -ForegroundColor Gray
} else {
    $sqlResult = & sqlcmd -S "127.0.0.1,$LocalPort" -U $SqlUser -P $SqlPassPlain `
        -d $SqlDb -Q "SELECT 'SQL_OK' AS Statut, @@VERSION AS Version" `
        -l 5 2>&1
    if ($LASTEXITCODE -eq 0 -or "$sqlResult" -match "SQL_OK") {
        Write-OK "Connexion SQL Server reussie via tunnel !"
        Write-Host ""
        Write-Host ($sqlResult | Out-String).Trim() -ForegroundColor White
    } else {
        Write-Err "Echec connexion SQL Server."
        Write-Host "     Details : $sqlResult" -ForegroundColor Gray
        Write-Host "     -> Verifier user/password SQL et que SQL Server ecoute sur localhost,1433" -ForegroundColor Gray
    }
}

# ── Fermer le tunnel test ─────────────────────────────────────────────────────
Write-Host ""
Write-Info "Fermeture du tunnel test..."
$tunnelProc | Stop-Process -Force -ErrorAction SilentlyContinue
Write-OK "Tunnel test ferme."

# ── RESULTAT FINAL ────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "=====================================================" -ForegroundColor Green
Write-Host "  TESTS TERMINES - Configurer maintenant OptiBoard" -ForegroundColor Green
Write-Host "=====================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Dans OptiBoard > Gestion DWH > Modifier :" -ForegroundColor Cyan
Write-Host "    Hote SSH    : $SageIP" -ForegroundColor Yellow
Write-Host "    Port SSH    : 22" -ForegroundColor White
Write-Host "    Utilisateur : sageTunnelUser" -ForegroundColor White
Write-Host "    Cle privee  : contenu de sage_tunnel_key" -ForegroundColor White
Write-Host "    Serveur SQL : .  (un seul point)" -ForegroundColor White
Write-Host ""

Read-Host "Appuyer sur Entree pour fermer"
