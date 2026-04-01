"""
Client Package — Generation du package d'installation pour clients autonomes
=============================================================================
Genere un fichier ZIP contenant :
  - config.json  : configuration de connexion (base client, agents)
  - install.ps1  : script PowerShell d'installation Windows
  - README.txt   : instructions d'installation

Le client autonome telecharge ce package, l'execute sur son serveur local,
et son installation OptiBoard devient 100% independante du serveur central.
Il se reconnectera uniquement via le Module MAJ (/api/updates) pour les updates.
"""
import io
import json
import zipfile
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import StreamingResponse

from ..database_unified import execute_central

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/client-package", tags=["Client Package"])


def _require_dwh(dwh_code: Optional[str]) -> str:
    if not dwh_code:
        raise HTTPException(status_code=400, detail="X-DWH-Code header requis")
    return dwh_code


# ============================================================
# GET /api/client-package/download
# Genere et telecharge le bundle ZIP d'installation
# ============================================================

@router.get("/download")
async def download_client_package(
    dwh_code: Optional[str] = Header(None, alias="X-DWH-Code"),
):
    """
    Genere un package ZIP pour l'installation du client autonome.
    Inclus: config.json, install.ps1, README.txt
    """
    code = _require_dwh(dwh_code)

    # Recuperer les infos du client
    try:
        rows = execute_central(
            """SELECT code, nom, raison_sociale, type_client,
                      client_db_server, client_db_name, client_db_user
               FROM APP_DWH WHERE code=? AND actif=1""",
            (code,),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not rows:
        raise HTTPException(status_code=404, detail=f"Client '{code}' introuvable")

    info = rows[0]
    client_nom  = info.get("nom") or info[1] or code
    client_code = code

    # ── config.json ──────────────────────────────────────────
    config = {
        "client_code":    client_code,
        "client_nom":     client_nom,
        "type_client":    "autonome",
        "generated_at":   datetime.now().isoformat(),
        "optiboard": {
            "db_server":   info.get("client_db_server") or info[4] or "localhost",
            "db_name":     info.get("client_db_name")   or info[5] or f"OptiBoard_{client_code}",
            "db_user":     info.get("client_db_user")   or info[6] or "sa",
            "db_password": "<<REMPLIR>>",
            "api_port":    8000,
            "frontend_port": 3000,
        },
        "update_server": {
            "url":          "https://kasoft.selfip.net",
            "check_interval_hours": 24,
        },
        "notes": [
            "1. Remplissez db_password avec le mot de passe SQL Server",
            "2. Lancez install.ps1 en tant qu'administrateur",
            "3. Configurez les agents ETL via le portail local",
        ]
    }
    config_json = json.dumps(config, indent=2, ensure_ascii=False)

    # ── install.ps1 ──────────────────────────────────────────
    install_ps1 = f"""# ============================================================
# OptiBoard — Script d'installation client autonome
# Client : {client_nom} ({client_code})
# Genere : {datetime.now().strftime('%Y-%m-%d %H:%M')}
# ============================================================
# Lancer en tant qu'Administrateur : Right-click > Run as Administrator
# ============================================================

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " INSTALLATION OPTIBOARD CLIENT AUTONOME" -ForegroundColor Cyan
Write-Host " Client : {client_nom} ({client_code})" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Verifier Python
Write-Host ""
Write-Host "[1/5] Verification Python..." -ForegroundColor Yellow
try {{
    $pythonVersion = python --version 2>&1
    Write-Host "     OK : $pythonVersion" -ForegroundColor Green
}} catch {{
    Write-Host "     ERREUR : Python non trouve. Installez Python 3.9+ depuis python.org" -ForegroundColor Red
    exit 1
}}

# Installer dependances
Write-Host "[2/5] Installation des dependances Python..." -ForegroundColor Yellow
Set-Location "$ScriptDir\\backend"
pip install -r requirements.txt --quiet
Write-Host "     OK" -ForegroundColor Green

# Configurer .env
Write-Host "[3/5] Configuration..." -ForegroundColor Yellow
$configFile = "$ScriptDir\\config.json"
$config = Get-Content $configFile | ConvertFrom-Json
$dbServer   = $config.optiboard.db_server
$dbName     = $config.optiboard.db_name
$dbUser     = $config.optiboard.db_user
$dbPassword = $config.optiboard.db_password

$envContent = @"
# OptiBoard Configuration — {client_nom}
DB_SERVER=$dbServer
DB_NAME=$dbName
DB_USER=$dbUser
DB_PASSWORD=$dbPassword
APP_NAME=OptiBoard - {client_nom}
DEBUG=false
CLIENT_CODE={client_code}
TYPE_CLIENT=autonome
"@
$envContent | Out-File -Encoding utf8 "$ScriptDir\\backend\\.env"
Write-Host "     OK : .env configure" -ForegroundColor Green

# Creer la base de donnees si necessaire
Write-Host "[4/5] Verification de la base de donnees..." -ForegroundColor Yellow
Write-Host "     Assurez-vous que SQL Server est demarre" -ForegroundColor Cyan
Write-Host "     Base : $dbName sur $dbServer" -ForegroundColor Cyan

# Demarrer le service
Write-Host "[5/5] Demarrage du service OptiBoard..." -ForegroundColor Yellow
$serviceName = "OptiBoard_{client_code}"

# Creer un service Windows avec NSSM (si disponible) ou utiliser une tache planifiee
$nssmPath = "$ScriptDir\\tools\\nssm.exe"
if (Test-Path $nssmPath) {{
    & $nssmPath install $serviceName python "$ScriptDir\\backend\\run.py"
    & $nssmPath set $serviceName AppDirectory "$ScriptDir\\backend"
    & $nssmPath start $serviceName
    Write-Host "     OK : Service '$serviceName' installe et demarre" -ForegroundColor Green
}} else {{
    # Lancement direct en arriere-plan
    Start-Process python -ArgumentList "$ScriptDir\\backend\\run.py" -WorkingDirectory "$ScriptDir\\backend" -WindowStyle Hidden
    Write-Host "     OK : OptiBoard demarre en arriere-plan" -ForegroundColor Green
    Write-Host "     Pour un service permanent, installez NSSM : https://nssm.cc" -ForegroundColor Cyan
}}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host " INSTALLATION TERMINEE" -ForegroundColor Green
Write-Host "------------------------------------------------------------" -ForegroundColor Green
Write-Host " Portail local : http://localhost:{config.get('optiboard', {{}}).get('api_port', 8000)}" -ForegroundColor White
Write-Host " Interface     : http://localhost:{config.get('optiboard', {{}}).get('frontend_port', 3000)}" -ForegroundColor White
Write-Host " Documentation : README.txt" -ForegroundColor White
Write-Host "============================================================" -ForegroundColor Green
"""

    # ── README.txt ───────────────────────────────────────────
    readme = f"""OptiBoard — Installation Client Autonome
==========================================
Client : {client_nom} ({client_code})
Genere : {datetime.now().strftime('%Y-%m-%d %H:%M')}

PREREQUIS
---------
- Windows Server 2016+ ou Windows 10/11
- Python 3.9 ou superieur (https://python.org)
- SQL Server 2016+ (ou SQL Server Express)
- 4 GB RAM minimum, 20 GB espace disque

INSTALLATION
------------
1. Extraire ce ZIP dans un dossier permanent (ex: C:\\OptiBoard)
2. Editer config.json et remplir db_password avec le mot de passe SQL
3. Clic droit sur install.ps1 > "Executer avec PowerShell en tant qu'administrateur"
4. Patienter pendant l'installation (~2-5 minutes)
5. Acceder au portail : http://localhost:8000

PREMIERE CONNEXION
------------------
- URL     : http://localhost:8000
- Login   : admin
- Mdp     : admin123 (A CHANGER immediatement)

CONFIGURATION DES AGENTS ETL
------------------------------
1. Aller dans Configuration > Agents ETL
2. Creer un agent pour chaque connexion Sage
3. Renseigner : serveur Sage, base, identifiants
4. Selectionner les tables a synchroniser
5. Demarrer l'agent

MISES A JOUR
------------
Votre installation est autonome. Pour recevoir les mises a jour KASOFT :
1. Connecter temporairement le serveur a internet
2. Aller dans le portail > Gestionnaire de mises a jour
3. Cliquer "Verifier les mises a jour" puis "Tout mettre a jour"
4. Deconnecter internet

SUPPORT
-------
Email : support@kasoft.ma
Site  : https://kasoft.ma
"""

    # ── Creer le ZIP en memoire ───────────────────────────────
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("config.json",  config_json)
        zf.writestr("install.ps1",  install_ps1)
        zf.writestr("README.txt",   readme)

    zip_buffer.seek(0)
    filename = f"OptiBoard_install_{client_code}_{datetime.now().strftime('%Y%m%d')}.zip"

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ============================================================
# GET /api/client-package/config
# Retourne uniquement le config.json (sans ZIP)
# ============================================================

@router.get("/config")
async def get_client_config(
    dwh_code: Optional[str] = Header(None, alias="X-DWH-Code"),
):
    """Retourne la configuration du client (sans credentials sensibles)."""
    code = _require_dwh(dwh_code)
    try:
        rows = execute_central(
            "SELECT code, nom, type_client, client_db_server, client_db_name FROM APP_DWH WHERE code=? AND actif=1",
            (code,),
        )
        if not rows:
            raise HTTPException(status_code=404, detail=f"Client '{code}' introuvable")
        r = rows[0]
        return {
            "success": True,
            "data": {
                "code":        r.get("code")        or r[0],
                "nom":         r.get("nom")         or r[1],
                "type_client": r.get("type_client") or r[2],
                "db_server":   r.get("client_db_server") or r[3] or "localhost",
                "db_name":     r.get("client_db_name")   or r[4] or f"OptiBoard_{code}",
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
