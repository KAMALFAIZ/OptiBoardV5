# ======================================================================
#  OptiBoard - Sauvegarde des bases SQL Server
#
#  Sauvegarde la base centrale (OptiBoard_SaaS) + toutes les bases
#  clients (OptiBoard_<CODE>) avec verification (RESTORE VERIFYONLY)
#  et retention glissante.
#
#  Usage :
#    .\backup_dbs.ps1                          # lit C:\OptiBoard\backend\.env
#    .\backup_dbs.ps1 -BackupDir "D:\Backups" -RetentionDays 14
#    .\backup_dbs.ps1 -Server "SRV\SQL" -User sa -Password xxx
#    .\backup_dbs.ps1 -Pattern "OptiBoard_SG"  # une seule base
#
#  IMPORTANT : BACKUP DATABASE ecrit sur le disque DU SERVEUR SQL.
#  - SQL Server local  : -BackupDir est utilise tel quel (defaut C:\OptiBoard\backups).
#  - SQL Server distant: si -BackupDir n'est pas fourni, le script utilise
#    automatiquement le dossier de backup par defaut du serveur ; sinon le
#    chemin fourni doit etre valide SUR LE SERVEUR (xp_create_subdir tente
#    de le creer). La retention est alors geree cote serveur (xp_delete_file).
#
#  Planification : utiliser INSTALL_BACKUP_TASK.bat (tache quotidienne 02:00).
# ======================================================================
param(
    [string]$EnvFile       = "C:\OptiBoard\backend\.env",
    [string]$BackupDir     = "C:\OptiBoard\backups",
    [int]$RetentionDays    = 30,
    [string]$Server        = "",
    [string]$User          = "",
    [string]$Password      = "",
    [string]$Pattern       = "OptiBoard%"
)

$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------
# Lecture du .env (DB_SERVER, DB_PORT, DB_USER, DB_PASSWORD)
# ---------------------------------------------------------------------
function Read-EnvFile([string]$path) {
    $vars = @{}
    if (Test-Path $path) {
        foreach ($line in Get-Content $path) {
            if ($line -match '^\s*([A-Za-z0-9_]+)\s*=\s*(.*?)\s*$') {
                $vars[$matches[1]] = $matches[2]
            }
        }
    }
    return $vars
}

$envVars = Read-EnvFile $EnvFile
if (-not $Server)   { $Server   = $envVars["DB_SERVER"] }
if (-not $User)     { $User     = $envVars["DB_USER"] }
if (-not $Password) { $Password = $envVars["DB_PASSWORD"] }
$Port = $envVars["DB_PORT"]
if ($Port -and $Port -ne "1433" -and $Server -notmatch ",") { $Server = "$Server,$Port" }

if (-not $Server -or -not $User -or -not $Password) {
    Write-Host "[ERREUR] Connexion SQL incomplete. Fournir -Server/-User/-Password ou un .env valide ($EnvFile)." -ForegroundColor Red
    exit 1
}

# ---------------------------------------------------------------------
# Journalisation (fichier local, meme si les .bak sont cote serveur)
# ---------------------------------------------------------------------
$script:logFile = $null
function Log([string]$msg, [string]$color = "Gray") {
    $line = "{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg
    Write-Host $line -ForegroundColor $color
    if ($script:logFile) { Add-Content -Path $script:logFile -Value $line -Encoding utf8 }
}

# ---------------------------------------------------------------------
# Connexion SQL (System.Data.SqlClient : present sur tout Windows)
# ---------------------------------------------------------------------
$connStr = "Server=$Server;Database=master;User Id=$User;Password=$Password;Connection Timeout=15"
$conn = New-Object System.Data.SqlClient.SqlConnection($connStr)
try {
    $conn.Open()
} catch {
    Write-Host "[ERREUR] Connexion impossible a $Server : $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

function Invoke-Sql([string]$sql, [int]$timeoutSec = 3600) {
    $cmd = $conn.CreateCommand()
    $cmd.CommandText = $sql
    $cmd.CommandTimeout = $timeoutSec
    [void]$cmd.ExecuteNonQuery()
}

function Invoke-SqlScalar([string]$sql) {
    $cmd = $conn.CreateCommand()
    $cmd.CommandText = $sql
    $cmd.CommandTimeout = 60
    return $cmd.ExecuteScalar()
}

function Invoke-SqlScalarList([string]$sql) {
    $cmd = $conn.CreateCommand()
    $cmd.CommandText = $sql
    $reader = $cmd.ExecuteReader()
    $list = @()
    while ($reader.Read()) { $list += $reader.GetString(0) }
    $reader.Close()
    return $list
}

# ---------------------------------------------------------------------
# Resolution du dossier de sauvegarde
#   - serveur distant + -BackupDir non fourni -> dossier par defaut du serveur
#   - xp_create_subdir (best effort) pour garantir l'existence cote serveur
# ---------------------------------------------------------------------
$serverHost = ($Server -split "[\\,]")[0]
$isRemote = $serverHost -notin @("localhost", "127.0.0.1", ".", "(local)", $env:COMPUTERNAME)

if ($isRemote -and -not $PSBoundParameters.ContainsKey("BackupDir")) {
    $serverDefault = Invoke-SqlScalar "SELECT CAST(SERVERPROPERTY('InstanceDefaultBackupPath') AS NVARCHAR(500))"
    if (-not $serverDefault -or $serverDefault -is [System.DBNull]) {
        try {
            $cmd = $conn.CreateCommand()
            $cmd.CommandText = "EXEC master.dbo.xp_instance_regread N'HKEY_LOCAL_MACHINE', N'Software\Microsoft\MSSQLServer\MSSQLServer', N'BackupDirectory'"
            $reader = $cmd.ExecuteReader()
            if ($reader.Read()) { $serverDefault = $reader["Data"] }
            $reader.Close()
        } catch {}
    }
    if ($serverDefault -and $serverDefault -isnot [System.DBNull]) {
        $BackupDir = ([string]$serverDefault).TrimEnd("\") + "\OptiBoard"
    } else {
        Write-Host "[ERREUR] Serveur distant ($serverHost) : impossible de determiner son dossier de backup par defaut. Fournir -BackupDir avec un chemin valide SUR le serveur." -ForegroundColor Red
        $conn.Close()
        exit 1
    }
}
$BackupDir = $BackupDir.TrimEnd("\")

# Creation du dossier cote serveur (s'execute avec le compte de service SQL)
try { Invoke-Sql "EXEC master.dbo.xp_create_subdir N'$BackupDir'" 60 } catch {}

# Fichier de log : dans BackupDir s'il est accessible localement, sinon a cote du script
$logDir = $BackupDir
if (-not (Test-Path $logDir)) {
    try { New-Item -ItemType Directory -Force $logDir -ErrorAction Stop | Out-Null } catch { $logDir = $PSScriptRoot }
}
if (-not (Test-Path $logDir)) { $logDir = $env:TEMP }
$script:logFile = Join-Path $logDir "backup_log.txt"

Log "===== Demarrage sauvegarde OptiBoard (serveur: $Server) =====" "Cyan"
Log "Dossier de sauvegarde : $BackupDir $(if ($isRemote) { '(sur le serveur SQL)' })"

# ---------------------------------------------------------------------
# Liste des bases a sauvegarder
# ---------------------------------------------------------------------
$dbs = Invoke-SqlScalarList "SELECT name FROM sys.databases WHERE name LIKE '$Pattern' AND state_desc = 'ONLINE' ORDER BY name"
if ($dbs.Count -eq 0) {
    Log "[ATTENTION] Aucune base ne correspond au motif '$Pattern'." "Yellow"
    $conn.Close()
    exit 1
}
Log ("Bases a sauvegarder ({0}) : {1}" -f $dbs.Count, ($dbs -join ", "))

# ---------------------------------------------------------------------
# Sauvegarde + verification de chaque base
# ---------------------------------------------------------------------
$stamp  = Get-Date -Format "yyyyMMdd_HHmmss"
$failed = @()

foreach ($db in $dbs) {
    $bakPath = "$BackupDir\$db`_$stamp.bak"
    $opts    = "WITH INIT, CHECKSUM, STATS = 25"
    try {
        try {
            # COMPRESSION non supportee sur SQL Express : repli automatique
            Invoke-Sql "BACKUP DATABASE [$db] TO DISK = N'$bakPath' $opts, COMPRESSION"
        } catch {
            if ($_.Exception.Message -match "COMPRESSION|compression") {
                Invoke-Sql "BACKUP DATABASE [$db] TO DISK = N'$bakPath' $opts"
            } else { throw }
        }
        Invoke-Sql "RESTORE VERIFYONLY FROM DISK = N'$bakPath' WITH CHECKSUM"
        $sizeMb = ""
        if (Test-Path $bakPath) { $sizeMb = " ({0:N1} MB)" -f ((Get-Item $bakPath).Length / 1MB) }
        Log "[OK] $db -> $bakPath$sizeMb" "Green"
    } catch {
        $failed += $db
        Log "[ECHEC] $db : $($_.Exception.Message)" "Red"
    }
}

# ---------------------------------------------------------------------
# Retention : suppression des .bak plus vieux que N jours
#   - dossier accessible localement -> suppression directe
#   - sinon -> xp_delete_file cote serveur (procedure des plans de maintenance)
# ---------------------------------------------------------------------
$limit = (Get-Date).AddDays(-$RetentionDays)
if (Test-Path $BackupDir) {
    $old = Get-ChildItem $BackupDir -Filter "*.bak" -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -lt $limit }
    foreach ($f in $old) {
        Remove-Item $f.FullName -Force -Confirm:$false
        Log "[RETENTION] Supprime : $($f.Name) (> $RetentionDays jours)"
    }
} else {
    try {
        $limitStr = $limit.ToString("yyyy-MM-ddTHH:mm:ss")
        Invoke-Sql "EXEC master.dbo.xp_delete_file 0, N'$BackupDir', N'bak', N'$limitStr', 0" 600
        Log "[RETENTION] Nettoyage cote serveur applique (> $RetentionDays jours)"
    } catch {
        Log "[ATTENTION] Retention cote serveur impossible : purger $BackupDir manuellement sur le serveur. ($($_.Exception.Message))" "Yellow"
    }
}

$conn.Close()

# ---------------------------------------------------------------------
# Bilan
# ---------------------------------------------------------------------
if ($failed.Count -gt 0) {
    Log ("===== TERMINE AVEC ERREURS : {0}/{1} bases en echec ({2}) =====" -f $failed.Count, $dbs.Count, ($failed -join ", ")) "Red"
    exit 1
}
Log ("===== TERMINE : {0}/{0} bases sauvegardees avec succes =====" -f $dbs.Count) "Green"
exit 0
