<#
.SYNOPSIS
    Repare la cle API d'un agent ETL dans la VRAIE base client (resolution auto).

.DESCRIPTION
    Corrige le 401 "Agent non autorise". Contrairement a un UPDATE en dur, ce script
    resout d'abord, depuis la base CENTRALE, le serveur + nom + credentials de la base
    client (comme le fait le backend via APP_ClientDB / APP_DWH), PUIS ecrit la cle la.
    En multi-tenant, la base d'un DWH peut etre sur un autre serveur SQL / avoir un autre
    nom que OptiBoard_<CODE> : ecrire en dur risquait de cibler la mauvaise base -> 401.

    Etapes :
      1. Connexion CENTRALE (parametres -SqlServer/-SqlUser/-SqlPassword = base OptiBoard_SaaS).
      2. Resolution db_server/db_name/db_user/db_password du DWH
         (COALESCE APP_ClientDB > APP_DWH.*_optiboard > APP_DWH.*_dwh > creds centraux).
      3. Connexion a la base CLIENT resolue.
      4. UPSERT APP_ETL_Agents : api_key_hash (SHA256) + api_key_prefix + is_active=1.
      5. Affiche la cle a coller (ApiKey) + l'emplacement reellement cible.

.EXAMPLE
    .\FIX_AGENT_KEY.ps1 -SqlServer kasoft.selfip.net -SqlUser sa -SqlPassword "***" `
        -DwhCode ALEAFOOD -AgentId 4ab86377-b5a3-4892-b224-be64d5cb088b -AgentName "Alea Food"
#>
param(
    [Parameter(Mandatory=$true)] [string]$SqlServer,     # serveur CENTRAL (OptiBoard_SaaS)
    [Parameter(Mandatory=$true)] [string]$SqlUser,       # user CENTRAL (fallback client)
    [Parameter(Mandatory=$true)] [string]$SqlPassword,   # password CENTRAL (fallback client)
    [Parameter(Mandatory=$true)] [string]$DwhCode,
    [Parameter(Mandatory=$true)] [string]$AgentId,
    [string]$AgentName = "Agent ETL",
    [string]$CentralDb = "OptiBoard_SaaS"
)

$ErrorActionPreference = "Stop"

function New-SqlConn([string]$server,[string]$db,[string]$user,[string]$pwd) {
    $cs = "Server=$server;Database=$db;User Id=$user;Password=$pwd;TrustServerCertificate=True;Connect Timeout=20"
    $c = New-Object System.Data.SqlClient.SqlConnection $cs
    $c.Open(); return $c
}

# ── 1. Resolution de la base client depuis la CENTRALE ──
$central = New-SqlConn $SqlServer $CentralDb $SqlUser $SqlPassword
Write-Host "Connecte a la base centrale [$CentralDb] sur $SqlServer" -ForegroundColor Green
try {
    $q = $central.CreateCommand()
    $q.CommandText = @"
SELECT TOP 1
    c.db_name,
    COALESCE(c.db_server,   d.serveur_optiboard, d.serveur_dwh)  AS db_server,
    COALESCE(c.db_user,     d.user_optiboard,    d.user_dwh)     AS db_user,
    COALESCE(c.db_password, d.password_optiboard, d.password_dwh) AS db_password
FROM APP_ClientDB c
LEFT JOIN APP_DWH d ON d.code = c.dwh_code
WHERE UPPER(c.dwh_code) = UPPER(@code) AND c.actif = 1
"@
    [void]$q.Parameters.AddWithValue("@code", $DwhCode)
    $r = $q.ExecuteReader()
    if ($r.Read()) {
        $cliDb     = $r["db_name"]
        $cliServer = if ($r["db_server"] -is [DBNull]) { $null } else { $r["db_server"] }
        $cliUser   = if ($r["db_user"]   -is [DBNull]) { $null } else { $r["db_user"] }
        $cliPwd    = if ($r["db_password"] -is [DBNull]) { $null } else { $r["db_password"] }
    }
    $r.Close()
    if (-not $cliDb) {
        # Fallback APP_DWH.base_optiboard
        $q2 = $central.CreateCommand()
        $q2.CommandText = @"
SELECT TOP 1 base_optiboard AS db_name, serveur_optiboard AS db_server,
       COALESCE(user_optiboard,user_dwh) AS db_user,
       COALESCE(password_optiboard,password_dwh) AS db_password
FROM APP_DWH WHERE UPPER(code)=UPPER(@code) AND actif=1 AND base_optiboard IS NOT NULL AND base_optiboard<>''
"@
        [void]$q2.Parameters.AddWithValue("@code", $DwhCode)
        $r2 = $q2.ExecuteReader()
        if ($r2.Read()) {
            $cliDb=$r2["db_name"]; $cliServer=$r2["db_server"]; $cliUser=$r2["db_user"]; $cliPwd=$r2["db_password"]
        }
        $r2.Close()
    }
}
finally { $central.Close() }

if (-not $cliDb) { throw "DWH '$DwhCode' introuvable dans APP_ClientDB / APP_DWH (base centrale)." }

# Fallbacks vers les creds centraux si non definis par client
if (-not $cliServer) { $cliServer = $SqlServer }
if (-not $cliUser)   { $cliUser   = $SqlUser }
if (-not $cliPwd)    { $cliPwd    = $SqlPassword }

Write-Host ("Base client resolue : [{0}] sur {1} (user {2})" -f $cliDb, $cliServer, $cliUser) -ForegroundColor Cyan

# ── 2. Generer cle + hash SHA256 ──
$rb = New-Object byte[] 32
[System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($rb)
$apiKey = [Convert]::ToBase64String($rb).TrimEnd('=').Replace('+','-').Replace('/','_')
$sha = [System.Security.Cryptography.SHA256]::Create()
$apiKeyHash = ($sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($apiKey)) | ForEach-Object { $_.ToString('x2') }) -join ''
$apiKeyPrefix = $apiKey.Substring(0,7) + "..."

# ── 3. UPSERT dans la base client resolue ──
$conn = New-SqlConn $cliServer $cliDb $cliUser $cliPwd
try {
    $cmd = $conn.CreateCommand()
    $cmd.CommandText = "UPDATE APP_ETL_Agents SET api_key_hash=@h, api_key_prefix=@p, is_active=1, updated_at=GETDATE() WHERE agent_id=@a"
    [void]$cmd.Parameters.AddWithValue("@h",$apiKeyHash)
    [void]$cmd.Parameters.AddWithValue("@p",$apiKeyPrefix)
    [void]$cmd.Parameters.AddWithValue("@a",$AgentId)
    $rows = $cmd.ExecuteNonQuery()
    if ($rows -eq 0) {
        Write-Host "Agent absent -> INSERT dans [$cliDb].APP_ETL_Agents" -ForegroundColor Yellow
        $ins = $conn.CreateCommand()
        $ins.CommandText = "INSERT INTO APP_ETL_Agents (agent_id,nom,api_key_hash,api_key_prefix,is_active,auto_start,statut,created_at,updated_at) VALUES (@a,@n,@h,@p,1,1,'inactif',GETDATE(),GETDATE())"
        [void]$ins.Parameters.AddWithValue("@a",$AgentId)
        [void]$ins.Parameters.AddWithValue("@n",$AgentName)
        [void]$ins.Parameters.AddWithValue("@h",$apiKeyHash)
        [void]$ins.Parameters.AddWithValue("@p",$apiKeyPrefix)
        [void]$ins.ExecuteNonQuery()
        Write-Host "Agent insere." -ForegroundColor Green
    } else {
        Write-Host "Agent mis a jour (cle + is_active=1)." -ForegroundColor Green
    }

    # Verif lecture
    $chk = $conn.CreateCommand()
    $chk.CommandText = "SELECT agent_id,is_active,api_key_prefix,updated_at FROM APP_ETL_Agents WHERE agent_id=@a"
    [void]$chk.Parameters.AddWithValue("@a",$AgentId)
    $rc = $chk.ExecuteReader()
    if ($rc.Read()) {
        Write-Host ("Verif DB : is_active={0}, prefix={1}, updated={2}" -f $rc["is_active"],$rc["api_key_prefix"],$rc["updated_at"]) -ForegroundColor DarkCyan
    }
    $rc.Close()
}
finally { $conn.Close() }

# ── 4. Sortie ──
Write-Host ""
Write-Host "================ CLE API (a coller) ================" -ForegroundColor Cyan
Write-Host ("Emplacement : [{0}] @ {1}" -f $cliDb, $cliServer)
Write-Host "AgentId : $AgentId"
Write-Host "ApiKey  : $apiKey"
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "-> Colle ApiKey dans le champ 'Cle' (ou appsettings.json ApiKey), puis recharge." -ForegroundColor Yellow
