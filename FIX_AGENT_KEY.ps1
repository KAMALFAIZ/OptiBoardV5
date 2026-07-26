<#
.SYNOPSIS
    Repare la cle API d'un agent ETL directement dans la base CLIENT OptiBoard_<CODE>.

.DESCRIPTION
    Corrige le 401 "Agent non autorise" quand :
      - la cle regeneree via la console a ete ecrite dans la mauvaise base
        (bug historique regenerate-key -> base centrale au lieu de la base client), ou
      - l'agent est desactive (is_active=0) alors que verify_agent exige is_active=1.

    Le script :
      1. Genere une nouvelle cle API (format token_urlsafe, comme le backend).
      2. Calcule son hash SHA256 (accepte par verify_api_key_hash meme sous HMAC :
         fallback SHA256 pour les cles pre-HMAC).
      3. UPDATE l'agent dans [OptiBoard_<CODE>].APP_ETL_Agents (api_key_hash +
         api_key_prefix + is_active=1). Si l'agent n'existe pas dans la base client
         (present uniquement en monitoring central), il est INSERE.
      4. Affiche la cle en clair a coller dans appsettings.json (ApiKey) / GUI (Cle).

.EXAMPLE
    .\FIX_AGENT_KEY.ps1 -SqlServer "localhost" -SqlUser sa -SqlPassword "MotDePasse" `
        -DwhCode ALEAFOOD -AgentId 4ab86377-b5a3-4892-b224-be64d5cb088b -AgentName "Alea Food"
#>
param(
    [Parameter(Mandatory=$true)] [string]$SqlServer,
    [Parameter(Mandatory=$true)] [string]$SqlUser,
    [Parameter(Mandatory=$true)] [string]$SqlPassword,
    [Parameter(Mandatory=$true)] [string]$DwhCode,
    [Parameter(Mandatory=$true)] [string]$AgentId,
    [string]$AgentName = "Agent ETL"
)

$ErrorActionPreference = "Stop"
$dbName = "OptiBoard_$DwhCode"

# ── 1. Generer une cle API (32 octets -> base64url, ~43 chars, comme secrets.token_urlsafe(32)) ──
$rb = New-Object byte[] 32
[System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($rb)
$apiKey = [Convert]::ToBase64String($rb).TrimEnd('=').Replace('+','-').Replace('/','_')

# ── 2. Hash SHA256 (hex minuscule, 64 chars = VARCHAR(64)) ──
$sha = [System.Security.Cryptography.SHA256]::Create()
$hashBytes = $sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($apiKey))
$apiKeyHash = ($hashBytes | ForEach-Object { $_.ToString('x2') }) -join ''
$apiKeyPrefix = $apiKey.Substring(0,7) + "..."

# ── 3. Connexion SQL + UPSERT dans la base client ──
$connStr = "Server=$SqlServer;Database=$dbName;User Id=$SqlUser;Password=$SqlPassword;TrustServerCertificate=True;Connect Timeout=15"
$conn = New-Object System.Data.SqlClient.SqlConnection $connStr
$conn.Open()
Write-Host "Connecte a [$dbName] sur $SqlServer" -ForegroundColor Green

try {
    # UPDATE d'abord
    $cmd = $conn.CreateCommand()
    $cmd.CommandText = @"
UPDATE APP_ETL_Agents
   SET api_key_hash = @h, api_key_prefix = @p, is_active = 1, updated_at = GETDATE()
 WHERE agent_id = @a
"@
    [void]$cmd.Parameters.AddWithValue("@h", $apiKeyHash)
    [void]$cmd.Parameters.AddWithValue("@p", $apiKeyPrefix)
    [void]$cmd.Parameters.AddWithValue("@a", $AgentId)
    $rows = $cmd.ExecuteNonQuery()

    if ($rows -eq 0) {
        Write-Host "Agent absent de la base client -> INSERT" -ForegroundColor Yellow
        $ins = $conn.CreateCommand()
        $ins.CommandText = @"
INSERT INTO APP_ETL_Agents
    (agent_id, nom, api_key_hash, api_key_prefix, is_active, auto_start, statut, created_at, updated_at)
VALUES (@a, @n, @h, @p, 1, 1, 'inactif', GETDATE(), GETDATE())
"@
        [void]$ins.Parameters.AddWithValue("@a", $AgentId)
        [void]$ins.Parameters.AddWithValue("@n", $AgentName)
        [void]$ins.Parameters.AddWithValue("@h", $apiKeyHash)
        [void]$ins.Parameters.AddWithValue("@p", $apiKeyPrefix)
        [void]$ins.ExecuteNonQuery()
        Write-Host "Agent insere dans [$dbName].APP_ETL_Agents" -ForegroundColor Green
    } else {
        Write-Host "Agent mis a jour (cle + is_active=1) dans [$dbName].APP_ETL_Agents" -ForegroundColor Green
    }
}
finally {
    $conn.Close()
}

# ── 4. Afficher la cle a coller ──
Write-Host ""
Write-Host "================ CLE API (a coller) ================" -ForegroundColor Cyan
Write-Host "AgentId : $AgentId"
Write-Host "ApiKey  : $apiKey"
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "-> Colle ApiKey dans appsettings.json (ApiKey) OU dans le champ 'Cle' de la GUI, puis recharge." -ForegroundColor Yellow
