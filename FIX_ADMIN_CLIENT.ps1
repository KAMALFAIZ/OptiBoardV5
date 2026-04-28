# ======================================================================
#  OptiBoard - Fix admin client manquant dans la base client
#  Cree APP_Users dans OptiBoard_<CODE> et y insere l'admin avec son hash
# ======================================================================
param(
    [string]$Server      = ".",
    [string]$SqlUser     = "sa",
    [string]$SqlPassword = "SQL@2019",
    [string]$DwhCode     = "SG",
    [string]$AdminUser   = "admin_sg",
    [string]$AdminPwd    = "12345678",
    [string]$AdminEmail  = "admin@monentreprise.local",
    [string]$AdminNom    = "Administrateur",
    [string]$AdminPrenom = "Client"
)

$ErrorActionPreference = "Stop"
$ClientDb = "OptiBoard_$DwhCode"

# Hash SHA256 (meme algo que auth_multitenant._hash_password)
$sha = [System.Security.Cryptography.SHA256]::Create()
$bytes = [System.Text.Encoding]::UTF8.GetBytes($AdminPwd)
$AdminHash = -join ($sha.ComputeHash($bytes) | ForEach-Object { $_.ToString("x2") })

Write-Host "=== Fix admin client ===" -ForegroundColor Cyan
Write-Host "Base client : $ClientDb" -ForegroundColor Yellow
Write-Host "Admin       : $AdminUser" -ForegroundColor Yellow
Write-Host "Hash SHA256 : $($AdminHash.Substring(0,16))..." -ForegroundColor Yellow

function Invoke-Sql([string]$db, [string]$sql) {
    $conn = New-Object System.Data.SqlClient.SqlConnection(
        "Server=$Server;Database=$db;User Id=$SqlUser;Password=$SqlPassword;TrustServerCertificate=True;")
    $conn.Open()
    try {
        $cmd = $conn.CreateCommand()
        $cmd.CommandText = $sql
        return $cmd.ExecuteNonQuery()
    } finally { $conn.Close() }
}

function Invoke-SqlScalar([string]$db, [string]$sql) {
    $conn = New-Object System.Data.SqlClient.SqlConnection(
        "Server=$Server;Database=$db;User Id=$SqlUser;Password=$SqlPassword;TrustServerCertificate=True;")
    $conn.Open()
    try {
        $cmd = $conn.CreateCommand()
        $cmd.CommandText = $sql
        return $cmd.ExecuteScalar()
    } finally { $conn.Close() }
}

# 1. Verifier que la base client existe
$exists = Invoke-SqlScalar "master" "SELECT DB_ID('$ClientDb')"
if ($null -eq $exists -or $exists -eq [System.DBNull]::Value) {
    Write-Host "[1/4] Creation de la base $ClientDb..." -ForegroundColor Yellow
    Invoke-Sql "master" "CREATE DATABASE [$ClientDb]" | Out-Null
} else {
    Write-Host "[1/4] Base $ClientDb existe deja (id=$exists)" -ForegroundColor Green
}

# 2. Creer APP_Users si absente (schema multi-tenant client)
Write-Host "[2/4] Creation/verification table APP_Users..." -ForegroundColor Yellow
Invoke-Sql $ClientDb @"
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Users' AND xtype='U')
CREATE TABLE APP_Users (
    id                    INT IDENTITY(1,1) PRIMARY KEY,
    username              VARCHAR(100) UNIQUE NOT NULL,
    password_hash         VARCHAR(200) NULL,
    nom                   NVARCHAR(200),
    prenom                NVARCHAR(100),
    email                 VARCHAR(200),
    role_dwh              VARCHAR(50) DEFAULT 'user',
    actif                 BIT DEFAULT 1,
    must_change_password  BIT DEFAULT 0,
    derniere_connexion    DATETIME NULL,
    date_creation         DATETIME DEFAULT GETDATE()
)
"@ | Out-Null

# 3. Inserer / mettre a jour l'admin
Write-Host "[3/4] Insertion / MAJ de $AdminUser..." -ForegroundColor Yellow
Invoke-Sql $ClientDb @"
IF EXISTS (SELECT 1 FROM APP_Users WHERE username = '$AdminUser')
    UPDATE APP_Users SET password_hash = '$AdminHash', actif = 1, role_dwh = 'admin_client',
        nom = N'$AdminNom', prenom = N'$AdminPrenom', email = '$AdminEmail',
        must_change_password = 0
    WHERE username = '$AdminUser'
ELSE
    INSERT INTO APP_Users (username, password_hash, nom, prenom, email, role_dwh, actif, must_change_password)
    VALUES ('$AdminUser', '$AdminHash', N'$AdminNom', N'$AdminPrenom', '$AdminEmail', 'admin_client', 1, 0)
"@ | Out-Null

# 4. Enregistrer la base client dans APP_ClientDB centrale (pour le routage)
Write-Host "[4/4] Enregistrement dans APP_ClientDB centrale..." -ForegroundColor Yellow
Invoke-Sql "OptiBoard_SaaS" @"
IF NOT EXISTS (SELECT 1 FROM APP_ClientDB WHERE dwh_code = '$DwhCode')
    INSERT INTO APP_ClientDB (dwh_code, db_name, actif) VALUES ('$DwhCode', '$ClientDb', 1)
"@ | Out-Null

Write-Host ""
Write-Host "=== TERMINE ===" -ForegroundColor Green
Write-Host "Connectez-vous avec :" -ForegroundColor Cyan
Write-Host "  URL  : http://127.0.0.1:8084/?client=$($DwhCode.ToLower())"
Write-Host "  User : $AdminUser"
Write-Host "  Pwd  : $AdminPwd"
Write-Host ""
Write-Host "Si le login echoue toujours, redemarrez le service :"
Write-Host "  nssm restart OptiBoard-Backend" -ForegroundColor Yellow
