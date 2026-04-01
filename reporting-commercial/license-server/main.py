"""
============================================================
  OptiBoard License Server
  Serveur central de gestion des licences

  CE SERVEUR EST HEBERGE CHEZ VOUS (kasoft.net)
  Il gere: generation, validation, activation,
           revocation et suivi des licences clients.
============================================================
"""
import logging
import sys
import hashlib
import hmac
import json
import base64
import time
from datetime import datetime, timedelta

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
from collections import defaultdict

from config import get_settings
from database import get_connection, init_database

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title="OptiBoard License Server",
    description="Serveur de gestion des licences OptiBoard",
    version="1.0.0",
    docs_url="/docs"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "X-Admin-Key"],
)


# ============================================================
# Auth — Protection des routes d'administration
# ============================================================
def require_admin_key(x_admin_key: Optional[str] = Header(None)):
    """Dependency FastAPI : verifie la cle admin dans le header X-Admin-Key"""
    if not x_admin_key or x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Cle admin invalide ou absente. Fournissez X-Admin-Key."
        )


# ============================================================
# Rate Limiter — Protection de /api/license/validate
# ============================================================
_validate_hits: dict = defaultdict(list)   # ip -> [timestamp, ...]
VALIDATE_RATE_LIMIT = 30                   # max appels par fenetre
VALIDATE_RATE_WINDOW = 60                  # fenetre en secondes


def check_validate_rate_limit(request: Request):
    """Dependency : limite les appels a validate par IP (30/min)"""
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    window_start = now - VALIDATE_RATE_WINDOW

    # Nettoyer les anciennes entrees
    _validate_hits[ip] = [t for t in _validate_hits[ip] if t > window_start]

    if len(_validate_hits[ip]) >= VALIDATE_RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Trop de requetes. Limite: {VALIDATE_RATE_LIMIT} appels/{VALIDATE_RATE_WINDOW}s"
        )
    _validate_hits[ip].append(now)


# ============================================================
# Schemas
# ============================================================
class CreateClientRequest(BaseModel):
    code: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    contact_name: Optional[str] = None
    notes: Optional[str] = None


class GenerateLicenseRequest(BaseModel):
    client_id: int
    plan: str = "standard"
    max_users: int = 5
    max_dwh: int = 1
    features: List[str] = ["dashboard", "ventes", "stocks", "recouvrement"]
    expiry_days: int = 365
    machine_id: Optional[str] = None  # None = pas lie a une machine, "*" = toute machine
    deployment_mode: str = "on-premise"  # "on-premise" ou "saas"


class ValidateLicenseRequest(BaseModel):
    license_key: str
    machine_id: str
    app_version: Optional[str] = "1.0.0"
    hostname: Optional[str] = None


class DeactivateLicenseRequest(BaseModel):
    license_key: str
    machine_id: str


class UpdateLicenseStatusRequest(BaseModel):
    status: str  # valid, suspended, revoked


class RenewLicenseRequest(BaseModel):
    expiry_days: int = 365


# ============================================================
# Helpers
# ============================================================
def _generate_license_key(payload: dict) -> str:
    """Genere une cle de licence signee avec HMAC-SHA256"""
    payload_json = json.dumps(payload, separators=(',', ':'))
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode()

    signature = hmac.new(
        settings.LICENSE_SIGNING_SECRET.encode(),
        payload_b64.encode(),
        hashlib.sha256
    ).hexdigest()

    return f"{payload_b64}.{signature}"


def _verify_license_signature(license_key: str) -> bool:
    """Verifie la signature d'une licence"""
    try:
        parts = license_key.split(".")
        if len(parts) != 2:
            return False
        payload_b64, provided_sig = parts
        expected_sig = hmac.new(
            settings.LICENSE_SIGNING_SECRET.encode(),
            payload_b64.encode(),
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(provided_sig, expected_sig)
    except Exception:
        return False


def _decode_payload(license_key: str) -> Optional[dict]:
    """Decode le payload d'une licence"""
    try:
        payload_b64 = license_key.split(".")[0]
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        return json.loads(base64.urlsafe_b64decode(payload_b64).decode())
    except Exception:
        return None


def _log_validation(license_id, action, machine_id, ip_address, hostname, app_version, status, message):
    """Enregistre un log de validation"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO LIC_Validation_Log
            (license_id, action, machine_id, ip_address, hostname, app_version, status, message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (license_id, action, machine_id, ip_address, hostname, app_version, status, message))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error logging: {e}")


# ============================================================
# ENDPOINTS: Gestion des Clients
# ============================================================
@app.get("/api/clients", dependencies=[Depends(require_admin_key)])
async def list_clients():
    """Liste tous les clients"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.*,
               (SELECT COUNT(*) FROM LIC_Licenses WHERE client_id = c.id AND actif = 1) as license_count
        FROM LIC_Clients c
        WHERE c.actif = 1
        ORDER BY c.name
    """)
    columns = [col[0] for col in cursor.description]
    clients = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()
    return {"success": True, "data": clients}


@app.post("/api/clients", dependencies=[Depends(require_admin_key)])
async def create_client(req: CreateClientRequest):
    """Cree un nouveau client"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO LIC_Clients (code, name, email, phone, address, contact_name, notes)
            OUTPUT INSERTED.id
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (req.code, req.name, req.email, req.phone, req.address, req.contact_name, req.notes))
        client_id = cursor.fetchone()[0]
        conn.commit()
        return {"success": True, "client_id": client_id, "message": f"Client {req.name} cree"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()


@app.get("/api/clients/{client_id}", dependencies=[Depends(require_admin_key)])
async def get_client(client_id: int):
    """Details d'un client avec ses licences"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM LIC_Clients WHERE id = ?", (client_id,))
    columns = [col[0] for col in cursor.description]
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Client non trouve")

    client = dict(zip(columns, row))

    # Ses licences
    cursor.execute("""
        SELECT id, [plan], max_users, max_dwh, features, machine_id,
               expiry_date, status, activated_at, last_check, check_count,
               hostname, ip_address, app_version, date_creation
        FROM LIC_Licenses
        WHERE client_id = ? AND actif = 1
        ORDER BY date_creation DESC
    """, (client_id,))
    lic_columns = [col[0] for col in cursor.description]
    licenses = [dict(zip(lic_columns, r)) for r in cursor.fetchall()]
    conn.close()

    client["licenses"] = licenses
    return {"success": True, "data": client}


@app.delete("/api/clients/{client_id}", dependencies=[Depends(require_admin_key)])
async def delete_client(client_id: int):
    """Desactive un client (soft delete)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE LIC_Clients SET actif = 0 WHERE id = ?", (client_id,))
    cursor.execute("UPDATE LIC_Licenses SET actif = 0, status = 'revoked' WHERE client_id = ?", (client_id,))
    conn.commit()
    conn.close()
    return {"success": True, "message": "Client desactive et licences revoquees"}


# ============================================================
# ENDPOINTS: Generation et Gestion des Licences
# ============================================================
@app.post("/api/licenses/generate", dependencies=[Depends(require_admin_key)])
async def generate_license(req: GenerateLicenseRequest):
    """
    Genere une nouvelle licence pour un client.
    C'EST L'ENDPOINT PRINCIPAL pour creer des licences.
    """
    # Verifier le client
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM LIC_Clients WHERE id = ? AND actif = 1", (req.client_id,))
    client_row = cursor.fetchone()
    if not client_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Client non trouve")

    columns = [col[0] for col in cursor.description]
    client = dict(zip(columns, client_row))

    # Calculer la date d'expiration
    expiry_date = datetime.now() + timedelta(days=req.expiry_days)

    # Pour le mode SaaS, le machine_id est toujours "*" (pas de binding machine)
    effective_machine_id = "*" if req.deployment_mode == "saas" else (req.machine_id or "*")

    # Creer le payload de la licence
    payload = {
        "org": client["name"],
        "mid": effective_machine_id,
        "plan": req.plan,
        "max_u": req.max_users,
        "max_d": req.max_dwh,
        "feat": req.features,
        "exp": expiry_date.strftime("%Y-%m-%d"),
        "iat": int(time.time()),
        "mode": req.deployment_mode  # "on-premise" ou "saas"
    }

    # Signer la licence
    license_key = _generate_license_key(payload)

    # Sauvegarder en base
    try:
        cursor.execute("""
            INSERT INTO LIC_Licenses
            (license_key, client_id, [plan], max_users, max_dwh, features, machine_id, expiry_date, status, deployment_mode)
            OUTPUT INSERTED.id
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'valid', ?)
        """, (
            license_key, req.client_id, req.plan, req.max_users, req.max_dwh,
            json.dumps(req.features), effective_machine_id,
            expiry_date.strftime("%Y-%m-%d %H:%M:%S"), req.deployment_mode
        ))
        license_id = cursor.fetchone()[0]
        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))

    _log_validation(license_id, "generate", req.machine_id, None, None, None, "valid",
                    f"Licence generee pour {client['name']}")

    conn.close()

    mode_label = "SaaS" if req.deployment_mode == "saas" else "On-Premise"
    return {
        "success": True,
        "license_id": license_id,
        "license_key": license_key,
        "client": client["name"],
        "plan": req.plan,
        "deployment_mode": req.deployment_mode,
        "expiry_date": expiry_date.strftime("%Y-%m-%d"),
        "message": f"Licence {mode_label} generee pour {client['name']} - Expire le {expiry_date.strftime('%d/%m/%Y')}"
    }


@app.get("/api/licenses", dependencies=[Depends(require_admin_key)])
async def list_licenses():
    """Liste toutes les licences avec infos client"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT l.id, l.[plan], l.max_users, l.max_dwh, l.features,
               l.machine_id, l.expiry_date, l.status, l.activated_at,
               l.last_check, l.check_count, l.hostname, l.ip_address,
               l.app_version, l.date_creation, l.deployment_mode,
               c.code as client_code, c.name as client_name, c.email as client_email
        FROM LIC_Licenses l
        JOIN LIC_Clients c ON l.client_id = c.id
        WHERE l.actif = 1
        ORDER BY l.date_creation DESC
    """)
    columns = [col[0] for col in cursor.description]
    licenses = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()
    return {"success": True, "data": licenses}


@app.get("/api/licenses/{license_id}", dependencies=[Depends(require_admin_key)])
async def get_license(license_id: int):
    """Details d'une licence"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT l.*, c.code as client_code, c.name as client_name, c.email as client_email
        FROM LIC_Licenses l
        JOIN LIC_Clients c ON l.client_id = c.id
        WHERE l.id = ? AND l.actif = 1
    """, (license_id,))
    columns = [col[0] for col in cursor.description]
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Licence non trouvee")

    license_data = dict(zip(columns, row))

    # Derniers logs
    cursor.execute("""
        SELECT TOP 20 * FROM LIC_Validation_Log
        WHERE license_id = ?
        ORDER BY date_action DESC
    """, (license_id,))
    log_cols = [col[0] for col in cursor.description]
    logs = [dict(zip(log_cols, r)) for r in cursor.fetchall()]
    conn.close()

    license_data["logs"] = logs
    return {"success": True, "data": license_data}


@app.put("/api/licenses/{license_id}/status", dependencies=[Depends(require_admin_key)])
async def update_license_status(license_id: int, req: UpdateLicenseStatusRequest):
    """
    Change le statut d'une licence (activer, suspendre, revoquer).
    C'EST ICI QUE VOUS DESACTIVEZ UNE LICENCE A DISTANCE.
    """
    valid_statuses = ["valid", "suspended", "revoked"]
    if req.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Statut invalide. Valides: {valid_statuses}")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE LIC_Licenses
        SET status = ?, date_modification = GETDATE()
        WHERE id = ? AND actif = 1
    """, (req.status, license_id))
    conn.commit()

    _log_validation(license_id, f"status_{req.status}", None, None, None, None, req.status,
                    f"Statut change a {req.status}")

    conn.close()

    status_messages = {
        "valid": "Licence activee",
        "suspended": "Licence suspendue - le client ne pourra plus utiliser l'application",
        "revoked": "Licence revoquee definitivement"
    }
    return {"success": True, "message": status_messages[req.status]}


@app.put("/api/licenses/{license_id}/renew", dependencies=[Depends(require_admin_key)])
async def renew_license(license_id: int, req: RenewLicenseRequest):
    """Renouvelle une licence en prolongeant la date d'expiration"""
    conn = get_connection()
    cursor = conn.cursor()

    # Recuperer la licence actuelle
    cursor.execute("SELECT * FROM LIC_Licenses WHERE id = ? AND actif = 1", (license_id,))
    columns = [col[0] for col in cursor.description]
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Licence non trouvee")

    old_license = dict(zip(columns, row))
    old_payload = _decode_payload(old_license["license_key"])
    if not old_payload:
        conn.close()
        raise HTTPException(status_code=500, detail="Erreur decodage licence existante")

    # Nouvelle date d'expiration
    new_expiry = datetime.now() + timedelta(days=req.expiry_days)

    # Regenerer la licence avec la nouvelle date
    old_payload["exp"] = new_expiry.strftime("%Y-%m-%d")
    old_payload["iat"] = int(time.time())
    new_key = _generate_license_key(old_payload)

    # Mettre a jour en base
    cursor.execute("""
        UPDATE LIC_Licenses
        SET license_key = ?, expiry_date = ?, status = 'valid', date_modification = GETDATE()
        WHERE id = ?
    """, (new_key, new_expiry.strftime("%Y-%m-%d %H:%M:%S"), license_id))
    conn.commit()

    _log_validation(license_id, "renew", None, None, None, None, "valid",
                    f"Renouvelee jusqu'au {new_expiry.strftime('%d/%m/%Y')}")

    conn.close()

    return {
        "success": True,
        "new_license_key": new_key,
        "expiry_date": new_expiry.strftime("%Y-%m-%d"),
        "message": f"Licence renouvelee jusqu'au {new_expiry.strftime('%d/%m/%Y')}"
    }


# ============================================================
# ENDPOINTS: Validation (appele par les installations clients)
# ============================================================
@app.post("/api/license/validate", dependencies=[Depends(check_validate_rate_limit)])
async def validate_license(req: ValidateLicenseRequest, request: Request):
    """
    Endpoint appele par chaque installation OptiBoard pour valider sa licence.
    C'est le point de controle principal.
    """
    client_ip = request.client.host if request.client else "unknown"

    # 1. Verifier la signature
    if not _verify_license_signature(req.license_key):
        _log_validation(None, "validate", req.machine_id, client_ip, req.hostname,
                       req.app_version, "invalid", "Signature invalide")
        return {"valid": False, "status": "invalid", "message": "Signature de licence invalide"}

    # 2. Chercher la licence en base
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT l.*, c.name as client_name
        FROM LIC_Licenses l
        JOIN LIC_Clients c ON l.client_id = c.id
        WHERE l.license_key = ? AND l.actif = 1
    """, (req.license_key,))
    columns = [col[0] for col in cursor.description]
    row = cursor.fetchone()

    if not row:
        conn.close()
        _log_validation(None, "validate", req.machine_id, client_ip, req.hostname,
                       req.app_version, "not_found", "Licence non trouvee en base")
        return {"valid": False, "status": "not_found", "message": "Licence non enregistree"}

    lic = dict(zip(columns, row))

    # 3. Verifier le statut
    if lic["status"] == "revoked":
        _log_validation(lic["id"], "validate", req.machine_id, client_ip, req.hostname,
                       req.app_version, "revoked", "Licence revoquee")
        conn.close()
        return {"valid": False, "status": "revoked", "message": "Licence revoquee"}

    if lic["status"] == "suspended":
        _log_validation(lic["id"], "validate", req.machine_id, client_ip, req.hostname,
                       req.app_version, "suspended", "Licence suspendue")
        conn.close()
        return {"valid": False, "status": "suspended", "message": "Licence suspendue"}

    # 4. Verifier l'expiration
    if lic["expiry_date"] and lic["expiry_date"] < datetime.now():
        cursor.execute("UPDATE LIC_Licenses SET status = 'expired' WHERE id = ?", (lic["id"],))
        conn.commit()
        _log_validation(lic["id"], "validate", req.machine_id, client_ip, req.hostname,
                       req.app_version, "expired", "Licence expiree")
        conn.close()
        return {"valid": False, "status": "expired", "message": "Licence expiree"}

    # 5. Verifier le machine_id (si lie a une machine)
    is_saas = lic.get("deployment_mode", "on-premise") == "saas"

    if is_saas:
        # Mode SaaS: pas de verification machine, mais enregistrer la premiere activation
        if not lic["activated_at"]:
            cursor.execute("""
                UPDATE LIC_Licenses
                SET activated_at = GETDATE(), hostname = ?, ip_address = ?
                WHERE id = ?
            """, (req.hostname, client_ip, lic["id"]))
    elif lic["machine_id"] and lic["machine_id"] != "*":
        # Mode On-Premise: verifier la correspondance machine
        if lic["machine_id"] != req.machine_id:
            _log_validation(lic["id"], "validate", req.machine_id, client_ip, req.hostname,
                           req.app_version, "machine_mismatch",
                           f"Machine attendue: {lic['machine_id']}, recue: {req.machine_id}")
            conn.close()
            return {"valid": False, "status": "machine_mismatch",
                    "message": "Cette licence est liee a une autre machine"}
    else:
        # Premiere activation On-Premise: lier a cette machine
        if not lic["activated_at"]:
            cursor.execute("""
                UPDATE LIC_Licenses
                SET machine_id = ?, activated_at = GETDATE(), hostname = ?, ip_address = ?
                WHERE id = ?
            """, (req.machine_id, req.hostname, client_ip, lic["id"]))

    # 6. Mettre a jour le dernier check
    cursor.execute("""
        UPDATE LIC_Licenses
        SET last_check = GETDATE(), check_count = check_count + 1,
            hostname = ?, ip_address = ?, app_version = ?,
            date_modification = GETDATE()
        WHERE id = ?
    """, (req.hostname, client_ip, req.app_version, lic["id"]))
    conn.commit()

    _log_validation(lic["id"], "validate", req.machine_id, client_ip, req.hostname,
                   req.app_version, "valid", "Validation reussie")

    conn.close()

    days_remaining = (lic["expiry_date"] - datetime.now()).days if lic["expiry_date"] else 0

    return {
        "valid": True,
        "status": "valid",
        "organization": lic.get("client_name", ""),
        "plan": lic["plan"],
        "deployment_mode": lic.get("deployment_mode", "on-premise"),
        "days_remaining": days_remaining,
        "message": "Licence valide"
    }


@app.post("/api/license/deactivate")
async def deactivate_license(req: DeactivateLicenseRequest, request: Request):
    """Delie une licence d'une machine (pour transfert)"""
    client_ip = request.client.host if request.client else "unknown"

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE LIC_Licenses
        SET machine_id = '*', activated_at = NULL, hostname = NULL, ip_address = NULL
        WHERE license_key = ? AND machine_id = ? AND actif = 1
    """, (req.license_key, req.machine_id))
    affected = cursor.rowcount
    conn.commit()

    if affected > 0:
        _log_validation(None, "deactivate", req.machine_id, client_ip, None, None, "deactivated",
                       "Machine deliee")

    conn.close()
    return {"success": affected > 0, "message": "Machine deliee" if affected > 0 else "Licence non trouvee"}


# ============================================================
# ENDPOINTS: Dashboard / Statistiques
# ============================================================
@app.get("/api/dashboard", dependencies=[Depends(require_admin_key)])
async def dashboard_stats():
    """Statistiques globales pour le panel admin"""
    conn = get_connection()
    cursor = conn.cursor()

    stats = {}

    cursor.execute("SELECT COUNT(*) FROM LIC_Clients WHERE actif = 1")
    stats["total_clients"] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM LIC_Licenses WHERE actif = 1")
    stats["total_licenses"] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM LIC_Licenses WHERE status = 'valid' AND actif = 1")
    stats["active_licenses"] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM LIC_Licenses WHERE status = 'expired' AND actif = 1")
    stats["expired_licenses"] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM LIC_Licenses WHERE status = 'suspended' AND actif = 1")
    stats["suspended_licenses"] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM LIC_Licenses WHERE status = 'revoked' AND actif = 1")
    stats["revoked_licenses"] = cursor.fetchone()[0]

    # Licences expirant dans 30 jours
    cursor.execute("""
        SELECT COUNT(*) FROM LIC_Licenses
        WHERE expiry_date BETWEEN GETDATE() AND DATEADD(day, 30, GETDATE())
        AND status = 'valid' AND actif = 1
    """)
    stats["expiring_soon"] = cursor.fetchone()[0]

    # Derniers checks
    cursor.execute("""
        SELECT TOP 10 l.id, c.name as client_name, l.[plan], l.last_check,
               l.hostname, l.ip_address, l.status, l.deployment_mode
        FROM LIC_Licenses l
        JOIN LIC_Clients c ON l.client_id = c.id
        WHERE l.last_check IS NOT NULL AND l.actif = 1
        ORDER BY l.last_check DESC
    """)
    columns = [col[0] for col in cursor.description]
    stats["recent_checks"] = [dict(zip(columns, r)) for r in cursor.fetchall()]

    conn.close()
    return {"success": True, "data": stats}


@app.get("/api/logs", dependencies=[Depends(require_admin_key)])
async def get_logs(limit: int = 50):
    """Derniers logs de validation"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT TOP {min(limit, 500)} * FROM LIC_Validation_Log
        ORDER BY date_action DESC
    """)
    columns = [col[0] for col in cursor.description]
    logs = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()
    return {"success": True, "data": logs}


# ============================================================
# Health
# ============================================================
@app.get("/api/health")
async def health():
    try:
        conn = get_connection()
        conn.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": str(e)}


# ============================================================
# Startup
# ============================================================
@app.on_event("startup")
async def startup():
    logger.info("[LICENSE SERVER] Starting OptiBoard License Server...")
    try:
        init_database()
        logger.info("[LICENSE SERVER] Database initialized successfully")
    except Exception as e:
        logger.error(f"[LICENSE SERVER] Database initialization failed: {e}")


# ============================================================
# Admin Panel Frontend (servir les fichiers statiques buildes)
# ============================================================
ADMIN_DIST = Path(__file__).parent / "admin-panel" / "dist"

if ADMIN_DIST.exists():
    # Servir les assets statiques (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=str(ADMIN_DIST / "assets")), name="static-assets")

    # Catch-all: servir index.html pour le SPA routing
    @app.get("/{full_path:path}")
    async def serve_admin(full_path: str):
        # Ne pas intercepter les routes API
        if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("redoc"):
            raise HTTPException(status_code=404)
        file_path = ADMIN_DIST / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(ADMIN_DIST / "index.html"))
else:
    @app.get("/")
    async def root():
        return {
            "application": "OptiBoard License Server",
            "version": "1.0.0",
            "status": "running",
            "admin_panel": "Non build. Executez: cd admin-panel && npm install && npm run build"
        }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG
    )
