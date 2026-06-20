# ======================================================================
#  OptiBoard - Restauration d'une base depuis un fichier .bak
#
#  Usage :
#    .\restore_db.ps1 -BakFile "C:\OptiBoard\backups\OptiBoard_SG_20260611_020000.bak" -Database OptiBoard_SG
#    .\restore_db.ps1 -BakFile "...bak" -Database OptiBoard_SG_TEST   # restaure sous un autre nom
#    .\restore_db.ps1 -BakFile "...bak" -Database OptiBoard_SG -Force # sans confirmation
#
#  ATTENTION : ecrase la base cible si elle existe (WITH REPLACE).
#  Le fichier .bak doit etre accessible DEPUIS le serveur SQL.
# ======================================================================
param(
    [Parameter(Mandatory = $true)][string]$BakFile,
    [Parameter(Mandatory = $true)][string]$Database,
    [string]$EnvFile  = "C:\OptiBoard\backend\.env",
    [string]$Server   = "",
    [string]$User     = "",
    [string]$Password = "",
    [switch]$Force
)

$ErrorActionPreference = "Stop"

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
    Write-Host "[ERREUR] Connexion SQL incomplete. Fournir -Server/-User/-Password ou un .env valide." -ForegroundColor Red
    exit 1
}

# Confirmation (la restauration ECRASE la base cible)
if (-not $Force) {
    Write-Host ""
    Write-Host "  La base [$Database] sur [$Server] va etre ECRASEE par :" -ForegroundColor Yellow
    Write-Host "  $BakFile" -ForegroundColor Yellow
    $answer = Read-Host "  Confirmer la restauration ? (oui/non)"
    if ($answer -ne "oui") {
        Write-Host "Restauration annulee."
        exit 0
    }
}

$connStr = "Server=$Server;Database=master;User Id=$User;Password=$Password;Connection Timeout=15"
$conn = New-Object System.Data.SqlClient.SqlConnection($connStr)
$conn.Open()

function Invoke-Sql([string]$sql, [int]$timeoutSec = 7200) {
    $cmd = $conn.CreateCommand()
    $cmd.CommandText = $sql
    $cmd.CommandTimeout = $timeoutSec
    [void]$cmd.ExecuteNonQuery()
}

try {
    # 1. Lire la liste des fichiers logiques du .bak pour construire les MOVE
    #    (necessaire si on restaure sous un autre nom ou sur une autre instance)
    $cmd = $conn.CreateCommand()
    $cmd.CommandText = "RESTORE FILELISTONLY FROM DISK = N'$BakFile'"
    $cmd.CommandTimeout = 600
    $reader = $cmd.ExecuteReader()
    $files = @()
    while ($reader.Read()) {
        $files += [pscustomobject]@{
            LogicalName = $reader["LogicalName"]
            Type        = $reader["Type"]
        }
    }
    $reader.Close()

    $cmd = $conn.CreateCommand()
    $cmd.CommandText = "SELECT CAST(SERVERPROPERTY('InstanceDefaultDataPath') AS NVARCHAR(500)), CAST(SERVERPROPERTY('InstanceDefaultLogPath') AS NVARCHAR(500))"
    $reader = $cmd.ExecuteReader()
    [void]$reader.Read()
    $dataPath = $reader.GetString(0)
    $logPath  = $reader.GetString(1)
    $reader.Close()

    $moves = @()
    $i = 0
    foreach ($f in $files) {
        if ($f.Type -eq "L") {
            $moves += "MOVE N'$($f.LogicalName)' TO N'$logPath$Database`_log$i.ldf'"
        } else {
            $moves += "MOVE N'$($f.LogicalName)' TO N'$dataPath$Database`_data$i.mdf'"
        }
        $i++
    }
    $moveClause = $moves -join ", "

    # 2. Passer la base en SINGLE_USER si elle existe (deconnecte les sessions)
    Invoke-Sql @"
IF DB_ID(N'$Database') IS NOT NULL
    ALTER DATABASE [$Database] SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
"@ 300

    # 3. Restaurer
    Write-Host "[INFO] Restauration de [$Database] en cours..." -ForegroundColor Cyan
    Invoke-Sql "RESTORE DATABASE [$Database] FROM DISK = N'$BakFile' WITH REPLACE, $moveClause, STATS = 25"

    # 4. Reouvrir l'acces
    Invoke-Sql "ALTER DATABASE [$Database] SET MULTI_USER" 300

    Write-Host "[OK] Base [$Database] restauree avec succes depuis $BakFile" -ForegroundColor Green
} catch {
    Write-Host "[ECHEC] Restauration : $($_.Exception.Message)" -ForegroundColor Red
    # Tentative de reouverture de l'acces si la base existe encore
    try { Invoke-Sql "IF DB_ID(N'$Database') IS NOT NULL ALTER DATABASE [$Database] SET MULTI_USER" 60 } catch {}
    $conn.Close()
    exit 1
}

$conn.Close()
exit 0
