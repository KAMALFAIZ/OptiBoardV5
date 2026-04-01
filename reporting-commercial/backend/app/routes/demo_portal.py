"""
Portail Demo AgentETL v2
========================
Permet a un prospect de :
1. S'inscrire via un formulaire public
2. Recevoir un lien de confirmation par email
3. Telecharger l'AgentETL pre-configure avec son token
4. Synchroniser ses donnees Sage (Jan + Fev 2026 uniquement)
5. Acceder a OptiBoard en mode demo pendant 7 jours

Routes publiques (sans auth) :
  POST /api/demo/register          → inscription prospect
  GET  /api/demo/confirm/{token}   → confirmation email

Routes AgentETL (auth par X-Demo-Token) :
  POST /api/demo/{token}/heartbeat → signal de vie de l'agent
  GET  /api/demo/{token}/tables    → liste des tables a synchroniser
  POST /api/demo/{token}/push-data → reception des donnees

Routes frontend :
  GET  /api/demo/{token}/status    → etat de la session
"""

import os
import io
import zipfile
import secrets
import hashlib
import logging
import pyodbc
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path

from fastapi import APIRouter, HTTPException, Header, BackgroundTasks
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, EmailStr

from app.database_unified import (
    execute_central as execute_query,
    central_cursor as get_db_cursor,
    write_central,
)
from app.services.email_service import send_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/demo", tags=["Demo Portal"])

DEMO_DURATION_DAYS = 7
APP_URL = os.getenv("APP_URL", "http://localhost:8083")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3003")

# ── Base dédiée demo ──────────────────────────────────────────────────────────
DEMO_DB_NAME = "OptiBoard_Demo"
_DB_SERVER   = os.getenv("DB_SERVER",   "kasoft.selfip.net")
_DB_USER     = os.getenv("DB_USER",     "sa")
_DB_PASSWORD = os.getenv("DB_PASSWORD", "SQL@2019")
_DB_DRIVER   = os.getenv("DB_DRIVER",   "{ODBC Driver 17 for SQL Server}")


def _ensure_demo_db():
    """Crée la base OptiBoard_Demo si elle n'existe pas."""
    conn_str = (f"DRIVER={_DB_DRIVER};SERVER={_DB_SERVER};DATABASE=master;"
                f"UID={_DB_USER};PWD={_DB_PASSWORD};TrustServerCertificate=yes")
    try:
        conn = pyodbc.connect(conn_str, autocommit=True, timeout=30)
        conn.execute(
            f"IF NOT EXISTS (SELECT 1 FROM sys.databases WHERE name = N'{DEMO_DB_NAME}') "
            f"CREATE DATABASE [{DEMO_DB_NAME}]"
        )
        conn.close()
        logger.info(f"Base {DEMO_DB_NAME} vérifiée/créée")
    except Exception as e:
        logger.warning(f"_ensure_demo_db: {e}")


@contextmanager
def _demo_db_cursor():
    """Context manager pour un cursor vers OptiBoard_Demo."""
    conn_str = (f"DRIVER={_DB_DRIVER};SERVER={_DB_SERVER};DATABASE={DEMO_DB_NAME};"
                f"UID={_DB_USER};PWD={_DB_PASSWORD};TrustServerCertificate=yes")
    conn = pyodbc.connect(conn_str, timeout=120)
    cursor = conn.cursor()
    try:
        yield cursor
    finally:
        try:
            conn.close()
        except Exception:
            pass


# Tables DWH_KA à cloner : (table_source, colonne_date_ou_None)
# Les tables cibles gardent le MÊME nom que la source (pas de préfixe)
KA_TABLES_CONFIG = [
    ("Entête_des_ventes",      "Date"),
    ("Lignes_des_ventes",      "Date"),
    ("Entête_des_achats",      "Date"),
    ("Lignes_des_achats",      "Date"),
    ("Paiements_Fournisseurs", "Date"),
    ("Ecritures_Comptables",   "Date d'écriture"),
    ("Réglements_Clients",     "Date"),
    ("Clients",                None),
    ("Articles",               None),
    ("Fournisseurs",           None),
    ("Etat_Stock",             None),
    ("Plan_Comptable",         None),
    ("Collaborateurs",         None),
]


def _demo_db_name(short: str) -> str:
    """Retourne le nom de la base dédiée à une session demo."""
    return f"OptiBoard_Demo_{short}"


def _clone_ka_to_demo(short: str, token: str):
    """
    Crée OptiBoard_Demo_{short} et clone toutes les tables DWH_KA avec
    leurs noms originaux (sans préfixe). Filtre 2025-2026 pour les tables
    transactionnelles. Les requêtes SQL des DataSources_Templates fonctionnent
    directement car elles utilisent les mêmes noms de tables que DWH_KA.
    """
    # Marquer le démarrage de la copie
    try:
        write_central(
            "UPDATE APP_Demo_Sessions SET sync_started = 1 WHERE token = ?",
            (token,)
        )
    except Exception:
        pass

    ka_rows = execute_query(
        "SELECT base_dwh FROM APP_DWH WHERE code = 'KA'",
        use_cache=False
    )
    if not ka_rows:
        raise RuntimeError("DWH KA introuvable dans APP_DWH")
    ka_db = ka_rows[0]["base_dwh"]
    dest_db = _demo_db_name(short)

    # Créer la base dédiée
    master_str = (f"DRIVER={_DB_DRIVER};SERVER={_DB_SERVER};DATABASE=master;"
                  f"UID={_DB_USER};PWD={_DB_PASSWORD};TrustServerCertificate=yes")
    mc = pyodbc.connect(master_str, autocommit=True, timeout=30)
    mc.execute(
        f"IF NOT EXISTS (SELECT 1 FROM sys.databases WHERE name=N'{dest_db}') "
        f"CREATE DATABASE [{dest_db}]"
    )
    mc.close()

    rows_total  = 0
    tables_done = 0

    conn_str = (f"DRIVER={_DB_DRIVER};SERVER={_DB_SERVER};DATABASE={dest_db};"
                f"UID={_DB_USER};PWD={_DB_PASSWORD};TrustServerCertificate=yes")
    conn = pyodbc.connect(conn_str, autocommit=True, timeout=300)
    cursor = conn.cursor()

    for source_name, date_col in KA_TABLES_CONFIG:
        try:
            cursor.execute(
                f"IF OBJECT_ID(N'[{source_name}]', N'U') IS NOT NULL "
                f"DROP TABLE [{source_name}]"
            )
            where = f"WHERE YEAR([{date_col}]) IN (2025, 2026)" if date_col else ""
            cursor.execute(
                f"SELECT * INTO [{source_name}] "
                f"FROM [{ka_db}].[dbo].[{source_name}] {where}"
            )
            cursor.execute(f"SELECT COUNT(*) FROM [{source_name}]")
            cnt = cursor.fetchone()[0]
            rows_total  += cnt
            tables_done += 1
            logger.info(f"clone_ka: {source_name} → {dest_db} ({cnt} lignes)")
        except Exception as e:
            logger.error(f"clone_ka: erreur table '{source_name}': {e}")

    conn.close()

    write_central(
        """UPDATE APP_Demo_Sessions
           SET sync_completed = 1, sync_started = 1,
               tables_synced = ?, rows_total = ?
           WHERE token = ?""",
        (tables_done, rows_total, token)
    )
    logger.info(f"clone_ka terminé pour {token[:8]} — {tables_done} tables, {rows_total} lignes")

# Tables Sage a synchroniser en mode demo
# (identique aux tables standard de l'AgentETL)
DEMO_TABLES_CONFIG = [
    {
        "name": "F_DOCENTETE",
        "table_name": "F_DOCENTETE",
        "target_table": "F_DOCENTETE",
        "source_query": "SELECT * FROM F_DOCENTETE",
        "primary_key_columns": "DO_Piece",
        "sync_type": "full",
        "timestamp_column": "cbModification",
        "priority": "high",
        "is_enabled": True,
        "batch_size": 10000,
    },
    {
        "name": "F_DOCLIGNE",
        "table_name": "F_DOCLIGNE",
        "target_table": "F_DOCLIGNE",
        "source_query": "SELECT * FROM F_DOCLIGNE",
        "primary_key_columns": "DL_Ligne",
        "sync_type": "full",
        "timestamp_column": "cbModification",
        "priority": "high",
        "is_enabled": True,
        "batch_size": 10000,
    },
    {
        "name": "F_COMPTET",
        "table_name": "F_COMPTET",
        "target_table": "F_COMPTET",
        "source_query": "SELECT * FROM F_COMPTET",
        "primary_key_columns": "CT_Num",
        "sync_type": "full",
        "timestamp_column": "cbModification",
        "priority": "normal",
        "is_enabled": True,
        "batch_size": 5000,
    },
    {
        "name": "F_ARTICLE",
        "table_name": "F_ARTICLE",
        "target_table": "F_ARTICLE",
        "source_query": "SELECT * FROM F_ARTICLE",
        "primary_key_columns": "AR_Ref",
        "sync_type": "full",
        "timestamp_column": "cbModification",
        "priority": "normal",
        "is_enabled": True,
        "batch_size": 5000,
    },
    {
        "name": "F_REGLER",
        "table_name": "F_REGLER",
        "target_table": "F_REGLER",
        "source_query": "SELECT * FROM F_REGLER",
        "primary_key_columns": "RG_No",
        "sync_type": "full",
        "timestamp_column": "cbModification",
        "priority": "normal",
        "is_enabled": True,
        "batch_size": 5000,
    },
]


# ============================================================
# Modeles Pydantic
# ============================================================

class DemoRegisterRequest(BaseModel):
    nom: str
    prenom: str
    societe: str
    email: EmailStr
    secteur: Optional[str] = None
    telephone: Optional[str] = None
    demo_mode: Optional[str] = "agent_etl"   # "clone_ka" | "agent_etl"


class PushDataDemoRequest(BaseModel):
    table_name: str
    target_table: str
    societe_code: str
    primary_key: List[str]
    columns: List[str]
    rows_count: int
    data: List[Dict[str, Any]]
    batch_id: Optional[str] = None
    sync_timestamp_start: Optional[str] = None
    sync_timestamp_end: Optional[str] = None
    demo_token: Optional[str] = None
    demo_date_debut: Optional[str] = None
    demo_date_fin: Optional[str] = None


class HeartbeatDemoRequest(BaseModel):
    status: str = "active"
    current_task: Optional[str] = None
    hostname: Optional[str] = None
    ip_address: Optional[str] = None
    agent_version: Optional[str] = None


class DemoConfigureRequest(BaseModel):
    sage_server:   str = "localhost"
    sage_database: str
    sage_username: Optional[str] = ""
    sage_password: Optional[str] = ""


class DemoTestConnectionRequest(BaseModel):
    sage_server:   str = "localhost"
    sage_database: str
    sage_username: Optional[str] = ""
    sage_password: Optional[str] = ""


# ============================================================
# Init tables
# ============================================================

def init_demo_tables():
    """Cree les tables necessaires au portail demo si elles n'existent pas."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES
                               WHERE TABLE_NAME = 'APP_Demo_Sessions')
                CREATE TABLE APP_Demo_Sessions (
                    id              INT IDENTITY(1,1) PRIMARY KEY,
                    token           VARCHAR(64)      NOT NULL UNIQUE,
                    email           NVARCHAR(255)    NOT NULL,
                    nom             NVARCHAR(200)    NOT NULL,
                    prenom          NVARCHAR(200)    NOT NULL,
                    societe         NVARCHAR(200)    NOT NULL,
                    secteur         NVARCHAR(100)    NULL,
                    telephone       NVARCHAR(50)     NULL,
                    confirmed       BIT              NOT NULL DEFAULT 0,
                    created_at      DATETIME         NOT NULL DEFAULT GETDATE(),
                    confirmed_at    DATETIME         NULL,
                    expires_at      DATETIME         NOT NULL,
                    last_seen       DATETIME         NULL,
                    sync_started    BIT              NOT NULL DEFAULT 0,
                    sync_completed  BIT              NOT NULL DEFAULT 0,
                    tables_synced   INT              NOT NULL DEFAULT 0,
                    rows_total      INT              NOT NULL DEFAULT 0,
                    revoked         BIT              NOT NULL DEFAULT 0,
                    sage_server     NVARCHAR(200)    NULL,
                    sage_database   NVARCHAR(200)    NULL,
                    sage_username   NVARCHAR(200)    NULL,
                    sage_password   NVARCHAR(200)    NULL
                )
            """)
            cursor.commit()
            # Ajouter colonnes manquantes si table existait déjà (dans le même cursor)
            for col, typ in [
                ("sage_server",    "NVARCHAR(200) NULL"),
                ("sage_database",  "NVARCHAR(200) NULL"),
                ("sage_username",  "NVARCHAR(200) NULL"),
                ("sage_password",  "NVARCHAR(200) NULL"),
                ("demo_user_id",   "INT NULL"),
                ("demo_dwh_code",  "VARCHAR(50) NULL"),
                ("demo_mode",      "VARCHAR(20) NULL DEFAULT 'agent_etl'"),
            ]:
                try:
                    cursor.execute(
                        f"IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS "
                        f"WHERE TABLE_NAME='APP_Demo_Sessions' AND COLUMN_NAME='{col}') "
                        f"ALTER TABLE APP_Demo_Sessions ADD [{col}] {typ}"
                    )
                    cursor.commit()
                except Exception:
                    pass
        logger.info("APP_Demo_Sessions: table verifiee/creee")
    except Exception as e:
        logger.warning(f"init_demo_tables: {e}")


try:
    init_demo_tables()
except Exception:
    pass

try:
    _ensure_demo_db()
except Exception:
    pass


# ============================================================
# Utilitaires
# ============================================================

def _generate_token() -> str:
    return secrets.token_urlsafe(32)


def _table_prefix(token: str) -> str:
    """Retourne le prefixe des tables demo pour ce token."""
    short = hashlib.sha256(token.encode()).hexdigest()[:12].upper()
    return f"DEMO_{short}_"


def _verify_demo_token(token: str) -> Dict:
    """
    Verifie qu'un token demo est valide, confirme et non expire.
    Retourne la session ou leve HTTPException.
    """
    rows = execute_query(
        """
        SELECT * FROM APP_Demo_Sessions
        WHERE token = ? AND confirmed = 1 AND revoked = 0
              AND expires_at > GETDATE()
        """,
        (token,),
        use_cache=False
    )
    if not rows:
        raise HTTPException(status_code=401, detail="Token demo invalide ou expire")
    return rows[0]


def _get_table_prefix_for_token(token: str) -> str:
    _verify_demo_token(token)
    return _table_prefix(token)


# ============================================================
# Routes publiques (inscription + confirmation)
# ============================================================

@router.post("/register")
async def demo_register(
    body: DemoRegisterRequest,
    background_tasks: BackgroundTasks
):
    """
    Inscrit un prospect et envoie un email de confirmation.
    """
    try:
        # Verifier si email deja inscrit et non expire
        existing = execute_query(
            "SELECT token, confirmed FROM APP_Demo_Sessions WHERE email = ? AND expires_at > GETDATE() AND revoked = 0",
            (body.email,),
            use_cache=False
        )
        if existing:
            # Renvoyer l'email si pas encore confirme
            if not existing[0]["confirmed"]:
                background_tasks.add_task(
                    _send_confirmation_email,
                    body.email, body.nom, existing[0]["token"]
                )
                return {"success": True, "message": "Email de confirmation renvoyé"}
            return {"success": False, "already_active": True, "message": "Votre session demo est toujours active"}

        token = _generate_token()
        expires_at = datetime.utcnow() + timedelta(days=DEMO_DURATION_DAYS)

        demo_mode = body.demo_mode if body.demo_mode in ("clone_ka", "agent_etl") else "agent_etl"
        write_central(
            """
            INSERT INTO APP_Demo_Sessions
                (token, email, nom, prenom, societe, secteur, telephone, expires_at, demo_mode)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (token, body.email, body.nom, body.prenom,
             body.societe, body.secteur, body.telephone, expires_at, demo_mode)
        )

        background_tasks.add_task(
            _send_confirmation_email, body.email, body.nom, token
        )

        return {
            "success": True,
            "message": "Inscription réussie. Vérifiez votre email pour confirmer et télécharger l'AgentETL."
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"demo_register error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{token}/configure")
async def demo_configure(token: str, cfg: DemoConfigureRequest):
    """Configure la base Sage pour la session démo (avant le premier sync)."""
    rows = execute_query(
        "SELECT 1 FROM APP_Demo_Sessions WHERE token = ? AND revoked = 0",
        (token,), use_cache=False
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Session introuvable")
    write_central(
        """UPDATE APP_Demo_Sessions SET
             sage_server = ?, sage_database = ?,
             sage_username = ?, sage_password = ?
           WHERE token = ?""",
        (cfg.sage_server, cfg.sage_database, cfg.sage_username or "", cfg.sage_password or "", token)
    )
    logger.info(f"Session {token[:8]} configurée: DB={cfg.sage_database} sur {cfg.sage_server}")
    return {"success": True, "message": "Configuration enregistrée"}


@router.post("/{token}/test-connection")
async def demo_test_connection(token: str, cfg: DemoTestConnectionRequest):
    """
    Teste la connexion à la base Sage fournie.
    Retourne succès + nb de tables trouvées, ou un message d'erreur précis.
    """
    rows = execute_query(
        "SELECT 1 FROM APP_Demo_Sessions WHERE token = ? AND revoked = 0",
        (token,), use_cache=False
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Session introuvable")

    import pyodbc

    # Construire la chaîne de connexion
    driver = "{ODBC Driver 17 for SQL Server}"
    if cfg.sage_username and cfg.sage_username.strip():
        conn_str = (
            f"DRIVER={driver};"
            f"SERVER={cfg.sage_server.strip()};"
            f"DATABASE={cfg.sage_database.strip()};"
            f"UID={cfg.sage_username.strip()};"
            f"PWD={cfg.sage_password or ''};"
            f"Connect Timeout=8;"
        )
    else:
        conn_str = (
            f"DRIVER={driver};"
            f"SERVER={cfg.sage_server.strip()};"
            f"DATABASE={cfg.sage_database.strip()};"
            f"Trusted_Connection=yes;"
            f"Connect Timeout=8;"
        )

    try:
        conn = pyodbc.connect(conn_str, timeout=8)
        cursor = conn.cursor()
        # Compter les tables utilisateur
        cursor.execute(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'"
        )
        table_count = cursor.fetchone()[0]
        # Vérifier quelques tables Sage clés
        sage_tables_found = []
        for t in ["F_DOCENTETE", "F_DOCLIGNE", "F_COMPTET", "F_ARTICLE"]:
            cursor.execute(
                "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = ?", (t,)
            )
            if cursor.fetchone()[0] > 0:
                sage_tables_found.append(t)
        cursor.close()
        conn.close()

        if not sage_tables_found:
            return {
                "success": False,
                "message": f"Connexion OK mais aucune table Sage trouvée dans '{cfg.sage_database}' ({table_count} tables au total). Vérifiez le nom de la base.",
                "table_count": table_count,
                "sage_tables": [],
            }

        return {
            "success": True,
            "message": f"Connexion réussie — {len(sage_tables_found)} tables Sage trouvées ({', '.join(sage_tables_found)})",
            "table_count": table_count,
            "sage_tables": sage_tables_found,
        }

    except pyodbc.OperationalError as e:
        err = str(e)
        if "Login failed" in err or "Echec" in err or "Échec" in err or "18456" in err:
            msg = f"Échec d'authentification — vérifiez l'utilisateur et le mot de passe SQL"
        elif "Cannot open database" in err or "Impossible d'ouvrir" in err:
            msg = f"Base '{cfg.sage_database}' introuvable sur '{cfg.sage_server}'"
        elif "network-related" in err.lower() or "réseau" in err.lower() or "timeout" in err.lower():
            msg = f"Impossible d'atteindre '{cfg.sage_server}' — vérifiez le nom du serveur et le réseau"
        else:
            msg = f"Erreur de connexion : {err[:200]}"
        logger.warning(f"test-connection [{token[:8]}] échec: {err}")
        return {"success": False, "message": msg, "table_count": 0, "sage_tables": []}

    except Exception as e:
        logger.error(f"test-connection [{token[:8]}] erreur inattendue: {e}")
        return {"success": False, "message": f"Erreur : {str(e)[:200]}", "table_count": 0, "sage_tables": []}


@router.get("/confirm/{token}", response_class=HTMLResponse)
async def demo_confirm(token: str, background_tasks: BackgroundTasks):
    """
    Confirme l'email et retourne la page de telechargement de l'AgentETL.
    """
    try:
        rows = execute_query(
            "SELECT * FROM APP_Demo_Sessions WHERE token = ? AND revoked = 0",
            (token,),
            use_cache=False
        )
        if not rows:
            return HTMLResponse(_html_error("Lien invalide ou expiré."), status_code=404)

        session = rows[0]

        if session["expires_at"] < datetime.utcnow():
            return HTMLResponse(_html_error("Ce lien a expiré."), status_code=410)

        # Marquer comme confirme
        if not session["confirmed"]:
            write_central(
                "UPDATE APP_Demo_Sessions SET confirmed = 1, confirmed_at = GETDATE() WHERE token = ?",
                (token,)
            )

        # Envoyer email + démarrer clone selon le mode
        demo_mode = session.get("demo_mode") or "agent_etl"
        if demo_mode == "clone_ka":
            background_tasks.add_task(
                _send_launch_email, session["email"], session["nom"], token
            )
            # Démarrer la copie KA en tâche de fond si pas encore démarrée
            if not session.get("sync_started") and not session.get("sync_completed"):
                short = hashlib.sha256(token.encode()).hexdigest()[:12].upper()
                background_tasks.add_task(_clone_ka_to_demo, short, token)
        else:
            background_tasks.add_task(
                _send_download_email, session["email"], session["nom"], token
            )

        return HTMLResponse(_html_confirmation(session["nom"], token, demo_mode))

    except Exception as e:
        logger.error(f"demo_confirm error: {e}")
        return HTMLResponse(_html_error("Une erreur est survenue."), status_code=500)


# ============================================================
# Téléchargement SageETLAgent_MultiAgent pré-configuré
# ============================================================

# Dossier publish du SageETLAgent_MultiAgent (.NET 8)
_AGENT_PUBLISH = Path(__file__).parent.parent.parent.parent.parent / "SageETLAgent_MultiAgent" / "publish"
# ZIP de base pré-construit (sans appsettings.json)
_AGENT_BASE_ZIP = Path(__file__).parent.parent.parent / "static" / "SageETLAgent_base.zip"


@router.get("/{token}/download")
async def demo_download(token: str):
    """
    Génère un ZIP contenant tout le dossier publish de SageETLAgent_MultiAgent
    avec un appsettings.json pré-configuré pour la session démo du prospect.
    """
    # Valider la session
    rows = execute_query(
        "SELECT * FROM APP_Demo_Sessions WHERE token = ? AND revoked = 0",
        (token,), use_cache=False
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Session introuvable ou révoquée")

    session = rows[0]
    if not session["confirmed"]:
        raise HTTPException(status_code=403, detail="Email non confirmé")
    if session["expires_at"] < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Session expirée")

    if not _AGENT_BASE_ZIP.exists():
        logger.error(f"ZIP de base introuvable : {_AGENT_BASE_ZIP}")
        raise HTTPException(status_code=503, detail="Agent non disponible, contactez votre commercial")

    # appsettings.json pré-configuré pour ce token démo
    import json as _json
    appsettings = {
        "SageEtl": {
            "ServerUrl": APP_URL,
            "DwhCode": token,
            "AgentFilter": "",
            "DemoMode": True,
            "DemoToken": token,
            "DemoDateDebut": "2026-01-01",
            "DemoDateFin": "2026-02-28"
        },
        "Logging": {
            "LogLevel": {
                "Default": "Information",
                "Microsoft": "Warning"
            }
        }
    }
    appsettings_bytes = _json.dumps(appsettings, indent=2, ensure_ascii=False).encode("utf-8")

    # Guide d'installation rapide
    expires_str = session['expires_at'].strftime('%d/%m/%Y') if session['expires_at'] else 'N/A'
    guide = (
        f"SageETLAgent -- Guide demo OptiBoard\n"
        f"=====================================\n"
        f"Genere le : {datetime.utcnow().strftime('%d/%m/%Y %H:%M')} UTC\n"
        f"Prospect  : {session['prenom']} {session['nom']} ({session['societe']})\n"
        f"Token     : {token}\n"
        f"Expire le : {expires_str}\n\n"
        f"INSTALLATION RAPIDE\n"
        f"-------------------\n"
        f"1. Decompressez ce ZIP dans un dossier (ex: C:\\OptiBoard_Demo)\n"
        f"2. Le fichier appsettings.json est deja pre-configure avec votre token\n"
        f"3. Lancez SageETLAgent.exe\n"
        f"4. La synchronisation Jan-Fev 2026 demarre automatiquement\n"
        f"5. Accedez a votre tableau de bord : {FRONTEND_URL}/demo/{token}\n\n"
        f"SUPPORT\n"
        f"-------\n"
        f"En cas de probleme : contactez votre commercial KASoft\n"
    )

    # Copier le ZIP de base en mémoire et injecter appsettings.json + guide
    logger.info(f"Préparation ZIP demo pour token {token[:8]}...")
    buf = io.BytesIO(_AGENT_BASE_ZIP.read_bytes())

    with zipfile.ZipFile(buf, "a", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("appsettings.json", appsettings_bytes)
        zf.writestr("LISEZMOI.txt", guide.encode("utf-8"))

    buf.seek(0)
    size_mb = buf.getbuffer().nbytes / 1024 / 1024
    logger.info(f"ZIP demo pret pour {token[:8]}: {size_mb:.1f} MB")

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="OptiBoard_SageETLAgent_Demo.zip"'
        }
    )


# ============================================================
# Routes AgentETL (auth X-Demo-Token)
# ============================================================

@router.get("/{token}/tables")
async def demo_get_tables(
    token: str,
    x_demo_token: Optional[str] = Header(None, alias="X-Demo-Token")
):
    """Retourne la liste des tables a synchroniser pour cette session demo."""
    _verify_demo_token(token)
    prefix = _table_prefix(token)

    # Injecter le prefixe dans les target_table
    tables = []
    for t in DEMO_TABLES_CONFIG:
        tc = dict(t)
        tc["target_table"] = f"{prefix}{t['target_table']}"
        tables.append(tc)

    return {"tables": tables}


@router.post("/{token}/heartbeat")
async def demo_heartbeat(token: str, body: HeartbeatDemoRequest):
    """Enregistre le signal de vie de l'AgentETL demo."""
    _verify_demo_token(token)
    try:
        write_central(
            "UPDATE APP_Demo_Sessions SET last_seen = GETDATE(), sync_started = 1 WHERE token = ?",
            (token,)
        )
        return {"success": True, "commands": []}
    except Exception as e:
        logger.error(f"demo_heartbeat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{token}/push-data")
async def demo_push_data(token: str, push: PushDataDemoRequest):
    """
    Recoit un batch de donnees depuis l'AgentETL demo.
    Stocke dans les tables DEMO_{hash}_{table_name} de la base centrale.
    """
    session = _verify_demo_token(token)
    prefix = _table_prefix(token)

    # Securite : rejeter les donnees hors plage Jan-Fev
    date_debut = push.demo_date_debut or "2026-01-01"
    date_fin = push.demo_date_fin or "2026-02-28"

    if not push.data:
        return {"success": True, "rows_inserted": 0, "rows_updated": 0}

    target_table = f"{prefix}{push.target_table}"

    try:
        result = await _load_demo_data(
            target_table=target_table,
            data=push.data,
            columns=push.columns,
            primary_key=push.primary_key,
            societe_code=push.societe_code,
        )

        # Mettre a jour les stats
        write_central(
            """
            UPDATE APP_Demo_Sessions
            SET tables_synced = tables_synced + 1,
                rows_total    = rows_total + ?,
                last_seen     = GETDATE()
            WHERE token = ?
            """,
            (len(push.data), token)
        )

        return {
            "success": True,
            "rows_inserted": result.get("inserted", 0),
            "rows_updated": result.get("updated", 0),
        }

    except Exception as e:
        logger.error(f"demo_push_data error [{target_table}]: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Route tableau de bord démo
# ============================================================

@router.get("/{token}/dashboard")
async def demo_dashboard(token: str):
    """
    Retourne les KPIs et données pour le tableau de bord démo.
    Interroge directement les tables DEMO_{hash}_ dans la base centrale.
    """
    rows = execute_query(
        "SELECT * FROM APP_Demo_Sessions WHERE token = ? AND revoked = 0 AND confirmed = 1",
        (token,), use_cache=False
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Session introuvable")
    session = rows[0]
    if session["expires_at"] < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Session expirée")
    if not session.get("sync_completed"):
        raise HTTPException(status_code=425, detail="Synchronisation non terminée")

    prefix = _table_prefix(token)
    tbl_doc  = f"[{prefix}F_DOCENTETE]"
    tbl_line = f"[{prefix}F_DOCLIGNE]"
    tbl_cpt  = f"[{prefix}F_COMPTET]"
    tbl_art  = f"[{prefix}F_ARTICLE]"

    try:
        # ── CA mensuel (F_DOCLIGNE × F_DOCENTETE) ─────────────────────────────
        ca_mensuel = execute_query(f"""
            SELECT
                LEFT(CONVERT(VARCHAR, d.DO_Date, 23), 7) AS mois,
                SUM(CASE WHEN d.DO_Type IN (1,2,3,6,7) THEN l.DL_MontantTTC ELSE -l.DL_MontantTTC END) AS ca
            FROM {tbl_line} l
            JOIN {tbl_doc} d ON l.DO_Piece = d.DO_Piece
            WHERE d.DO_Type IN (1,2,3,6,7,14,15)
              AND d.DO_Date >= '2026-01-01' AND d.DO_Date < '2026-03-01'
            GROUP BY LEFT(CONVERT(VARCHAR, d.DO_Date, 23), 7)
            ORDER BY mois
        """, use_cache=False)

        # ── Top 10 clients ─────────────────────────────────────────────────────
        top_clients = execute_query(f"""
            SELECT TOP 10
                d.DO_Tiers AS code,
                ISNULL(c.CT_Intitule, d.DO_Tiers) AS nom,
                SUM(CASE WHEN d.DO_Type IN (1,2,3,6,7) THEN l.DL_MontantTTC ELSE -l.DL_MontantTTC END) AS ca
            FROM {tbl_line} l
            JOIN {tbl_doc} d ON l.DO_Piece = d.DO_Piece
            LEFT JOIN {tbl_cpt} c ON c.CT_Num = d.DO_Tiers
            WHERE d.DO_Type IN (1,2,3,6,7)
              AND d.DO_Date >= '2026-01-01' AND d.DO_Date < '2026-03-01'
            GROUP BY d.DO_Tiers, c.CT_Intitule
            ORDER BY ca DESC
        """, use_cache=False)

        # ── Top 10 articles ────────────────────────────────────────────────────
        top_articles = execute_query(f"""
            SELECT TOP 10
                l.AR_Ref AS ref,
                ISNULL(a.AR_Design, l.AR_Ref) AS designation,
                SUM(l.DL_Qte) AS qte,
                SUM(CASE WHEN d.DO_Type IN (1,2,3,6,7) THEN l.DL_MontantTTC ELSE -l.DL_MontantTTC END) AS ca
            FROM {tbl_line} l
            JOIN {tbl_doc} d ON l.DO_Piece = d.DO_Piece
            LEFT JOIN {tbl_art} a ON a.AR_Ref = l.AR_Ref
            WHERE d.DO_Type IN (1,2,3,6,7)
              AND d.DO_Date >= '2026-01-01' AND d.DO_Date < '2026-03-01'
              AND l.AR_Ref IS NOT NULL AND l.AR_Ref != ''
            GROUP BY l.AR_Ref, a.AR_Design
            ORDER BY ca DESC
        """, use_cache=False)

        # ── KPIs globaux ───────────────────────────────────────────────────────
        kpis = execute_query(f"""
            SELECT
                SUM(CASE WHEN d.DO_Type IN (1,2,3,6,7) THEN l.DL_MontantTTC ELSE -l.DL_MontantTTC END) AS ca_total,
                COUNT(DISTINCT d.DO_Piece) AS nb_factures,
                COUNT(DISTINCT d.DO_Tiers) AS nb_clients,
                COUNT(DISTINCT l.AR_Ref) AS nb_articles
            FROM {tbl_line} l
            JOIN {tbl_doc} d ON l.DO_Piece = d.DO_Piece
            WHERE d.DO_Type IN (1,2,3,6,7)
              AND d.DO_Date >= '2026-01-01' AND d.DO_Date < '2026-03-01'
        """, use_cache=False)

        kpi = kpis[0] if kpis else {}

        return {
            "success": True,
            "societe": session.get("societe"),
            "kpis": {
                "ca_total":    float(kpi.get("ca_total") or 0),
                "nb_factures": int(kpi.get("nb_factures") or 0),
                "nb_clients":  int(kpi.get("nb_clients") or 0),
                "nb_articles": int(kpi.get("nb_articles") or 0),
            },
            "ca_mensuel":   [{"mois": r["mois"], "ca": float(r["ca"] or 0)} for r in ca_mensuel],
            "top_clients":  [{"code": r["code"], "nom": r["nom"], "ca": float(r["ca"] or 0)} for r in top_clients],
            "top_articles": [{"ref": r["ref"], "designation": r["designation"], "qte": float(r["qte"] or 0), "ca": float(r["ca"] or 0)} for r in top_articles],
        }
    except Exception as e:
        logger.error(f"demo_dashboard error [{token[:8]}]: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Route frontend : statut de la session
# ============================================================

@router.get("/{token}/status")
async def demo_status(token: str):
    """Retourne l'etat de la session demo (pour le frontend)."""
    rows = execute_query(
        """
        SELECT token, nom, prenom, societe, confirmed, sync_started, sync_completed,
               tables_synced, rows_total, created_at, expires_at, last_seen, revoked,
               demo_mode
        FROM APP_Demo_Sessions WHERE token = ?
        """,
        (token,),
        use_cache=False
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Session demo introuvable")

    s = rows[0]
    now = datetime.utcnow()
    expires = s["expires_at"]
    is_expired = expires < now if expires else True

    return {
        "success": True,
        "token": s["token"],
        "nom": s["nom"],
        "prenom": s["prenom"],
        "societe": s["societe"],
        "confirmed": bool(s["confirmed"]),
        "sync_started": bool(s["sync_started"]),
        "sync_completed": bool(s["sync_completed"]),
        "tables_synced": s["tables_synced"],
        "rows_total": s["rows_total"],
        "expires_at": expires.isoformat() if expires else None,
        "is_expired": is_expired,
        "revoked": bool(s["revoked"]),
        "last_seen": s["last_seen"].isoformat() if s["last_seen"] else None,
        "demo_mode":     s.get("demo_mode") or "agent_etl",
        "optiboard_url": f"{FRONTEND_URL}/demo/{token}/launch" if bool(s["sync_completed"]) and not is_expired else None,
        "board_url":     f"{FRONTEND_URL}/demo/{token}/board"  if bool(s["sync_completed"]) and not is_expired else None,
    }


# ============================================================
# Routes provision + auto-login (acces a l'app complete)
# ============================================================

@router.post("/{token}/provision")
async def demo_provision(token: str):
    """
    Cree (si besoin) un compte utilisateur + DWH demo pour ce token.
    Idempotent : appels multiples retournent le meme compte.
    """
    rows = execute_query(
        "SELECT * FROM APP_Demo_Sessions WHERE token = ? AND revoked = 0 AND confirmed = 1",
        (token,), use_cache=False
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Session introuvable ou non confirmee")
    session = rows[0]

    demo_mode = session.get("demo_mode") or "agent_etl"

    # Mode agent_etl : la sync doit être terminée
    if demo_mode == "agent_etl" and not session.get("sync_completed"):
        raise HTTPException(status_code=425, detail="Synchronisation non terminee — reessayez apres la sync")

    # Deja provisionne ? S'assurer que le role est correct (migration)
    if session.get("demo_user_id") and session.get("demo_dwh_code"):
        try:
            write_central(
                "UPDATE APP_Users SET role_global = 'admin_client' WHERE id = ? AND role_global != 'admin_client'",
                (session["demo_user_id"],)
            )
        except Exception:
            pass
        return {
            "success": True,
            "already_provisioned": True,
            "demo_user_id": session["demo_user_id"],
            "demo_dwh_code": session["demo_dwh_code"],
        }

    # Calculer codes uniques a partir du hash du token
    short = hashlib.sha256(token.encode()).hexdigest()[:12].upper()
    dwh_code = f"DEMO_{short}"          # ex: DEMO_A912AED3C125
    username  = f"demo_{short.lower()}" # ex: demo_a912aed3c125

    company = session.get("societe") or "Demo"
    email   = session.get("email")   or ""

    # --- 1. Creer le DWH dans APP_DWH ---
    # clone_ka → base dédiée OptiBoard_Demo_{short}
    # agent_etl → base partagée OptiBoard_Demo
    if demo_mode == "clone_ka":
        dwh_base_db = _demo_db_name(short)
    else:
        dwh_base_db = DEMO_DB_NAME

    existing_dwh = execute_query("SELECT 1 FROM APP_DWH WHERE code = ?", (dwh_code,), use_cache=False)
    if not existing_dwh:
        try:
            write_central(
                """
                INSERT INTO APP_DWH
                    (code, nom, raison_sociale, serveur_dwh, base_dwh, user_dwh, password_dwh, actif)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (dwh_code, company, company, _DB_SERVER, dwh_base_db, _DB_USER, _DB_PASSWORD)
            )
        except Exception as e:
            logger.warning(f"demo_provision: insert APP_DWH error: {e}")

    # --- 2. Creer l'utilisateur dans APP_Users ---
    # Hash du mot de passe = sha256(token) — on n'expose pas le mdp, l'acces se fait par auto-login
    pwd_hash = hashlib.sha256(token.encode()).hexdigest()
    existing_user = execute_query("SELECT 1 FROM APP_Users WHERE username = ?", (username,), use_cache=False)
    if not existing_user:
        try:
            write_central(
                """
                INSERT INTO APP_Users
                    (username, password_hash, nom, prenom, email, role_global, actif)
                VALUES (?, ?, ?, ?, ?, 'admin_client', 1)
                """,
                (username, pwd_hash, company, "Demo", email)
            )
        except Exception as e:
            logger.warning(f"demo_provision: insert APP_Users error: {e}")

    # Recuperer l'id utilisateur
    u_rows = execute_query(
        "SELECT id FROM APP_Users WHERE username = ?", (username,), use_cache=False
    )
    if not u_rows:
        raise HTTPException(status_code=500, detail="Erreur creation compte demo")
    user_id = u_rows[0]["id"]

    # --- 3. Lier l'utilisateur au DWH ---
    existing_link = execute_query(
        "SELECT 1 FROM APP_UserDWH WHERE user_id = ? AND dwh_code = ?",
        (user_id, dwh_code), use_cache=False
    )
    if not existing_link:
        try:
            write_central(
                "INSERT INTO APP_UserDWH (user_id, dwh_code, role_dwh, is_default) VALUES (?, ?, 'admin_client', 1)",
                (user_id, dwh_code)
            )
        except Exception as e:
            logger.warning(f"demo_provision: insert APP_UserDWH error: {e}")

    # --- 4. Inserer les pages accessibles ---
    demo_pages = [
        "dashboard", "admin", "etl_admin", "client_users",
        "client_dwh", "dwh_management", "themes",
    ]
    for page in demo_pages:
        existing_page = execute_query(
            "SELECT 1 FROM APP_UserPages WHERE user_id = ? AND page_code = ?",
            (user_id, page), use_cache=False
        )
        if not existing_page:
            try:
                write_central(
                    "INSERT INTO APP_UserPages (user_id, page_code) VALUES (?, ?)",
                    (user_id, page)
                )
            except Exception:
                pass

    # --- 5. Sauvegarder dans la session ---
    try:
        write_central(
            "UPDATE APP_Demo_Sessions SET demo_user_id = ?, demo_dwh_code = ? WHERE token = ?",
            (user_id, dwh_code, token)
        )
    except Exception as e:
        logger.warning(f"demo_provision: update session error: {e}")

    # --- 6. Clone DWH_KA si mode clone_ka (uniquement si pas encore démarré) ---
    # Normalement déjà lancé comme tâche de fond depuis la route /confirm
    if demo_mode == "clone_ka" and not session.get("sync_started") and not session.get("sync_completed"):
        try:
            import threading
            t = threading.Thread(target=_clone_ka_to_demo, args=(short, token), daemon=True)
            t.start()
        except Exception as e:
            logger.error(f"demo_provision: clone_ka start failed: {e}")

    logger.info(f"demo_provision: user '{username}' / DWH '{dwh_code}' crees pour {token[:8]}...")
    return {
        "success": True,
        "already_provisioned": False,
        "demo_user_id": user_id,
        "demo_dwh_code": dwh_code,
    }


@router.post("/{token}/auto-login")
async def demo_auto_login(token: str):
    """
    Authentifie automatiquement l'utilisateur demo et retourne un contexte
    de session compatible avec le localStorage de l'app OptiBoard.
    Provisionne le compte si ce n'est pas encore fait.
    """
    rows = execute_query(
        "SELECT * FROM APP_Demo_Sessions WHERE token = ? AND revoked = 0 AND confirmed = 1",
        (token,), use_cache=False
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Session introuvable ou non confirmee")
    session = rows[0]

    # Provisionner si necessaire
    if not session.get("demo_user_id") or not session.get("demo_dwh_code"):
        if not session.get("sync_completed"):
            raise HTTPException(status_code=425, detail="Synchronisation non terminee")
        prov = await demo_provision(token)
        # Recharger la session
        rows = execute_query(
            "SELECT * FROM APP_Demo_Sessions WHERE token = ?", (token,), use_cache=False
        )
        session = rows[0]

    user_id  = session["demo_user_id"]
    dwh_code = session["demo_dwh_code"]

    # Charger l'utilisateur
    u_rows = execute_query(
        "SELECT id, username, nom, prenom, email, role_global FROM APP_Users WHERE id = ? AND actif = 1",
        (user_id,), use_cache=False
    )
    if not u_rows:
        raise HTTPException(status_code=404, detail="Compte demo introuvable — re-provisionnez")
    u = u_rows[0]

    # Charger les infos DWH
    dwh_rows = execute_query(
        "SELECT code, nom, raison_sociale, logo_url FROM APP_DWH WHERE code = ?",
        (dwh_code,), use_cache=False
    )
    dwh_info = dwh_rows[0] if dwh_rows else {"code": dwh_code, "nom": session.get("societe") or "Demo"}

    # Mettre a jour derniere connexion
    try:
        write_central("UPDATE APP_Users SET derniere_connexion = GETDATE() WHERE id = ?", (user_id,))
    except Exception:
        pass

    # Pages accessibles pour le demo
    demo_pages = [
        "dashboard", "admin", "etl_admin", "client_users",
        "client_dwh", "dwh_management", "themes",
    ]

    session_token = secrets.token_hex(32)

    return {
        "success":  True,
        "token":    session_token,
        "has_client_db": False,
        "user": {
            "id":               u["id"],
            "username":         u["username"],
            "nom":              u.get("nom")    or session.get("societe") or "",
            "prenom":           u.get("prenom") or "Demo",
            "email":            u.get("email")  or "",
            "role":             "admin_client",
            "role_global":      "admin_client",
            "role_dwh":         "admin_client",
            "pages_autorisees": demo_pages,
            "societes":         [],
            "societes_list":    [],
            "dwh_code":         dwh_code,
            "from_client_db":   False,
        },
        "current_dwh": {
            "code":            dwh_info.get("code") or dwh_code,
            "nom":             dwh_info.get("nom")  or session.get("societe") or "Demo",
            "raison_sociale":  dwh_info.get("raison_sociale") or "",
            "logo_url":        dwh_info.get("logo_url") or "",
        },
    }


# ============================================================
# Route admin
# ============================================================

@router.get("/admin/sessions")
async def demo_admin_sessions(
    x_user_role: Optional[str] = Header(None, alias="X-User-Role")
):
    """Liste toutes les sessions demo (superadmin uniquement)."""
    if x_user_role != "superadmin":
        raise HTTPException(status_code=403, detail="Acces refuse")
    rows = execute_query(
        """
        SELECT token, email, nom, prenom, societe, secteur,
               confirmed, sync_started, sync_completed,
               tables_synced, rows_total,
               created_at, expires_at, last_seen, revoked
        FROM APP_Demo_Sessions
        ORDER BY created_at DESC
        """,
        use_cache=False
    )
    return {"success": True, "data": rows, "count": len(rows)}


@router.delete("/admin/sessions/{token}")
async def demo_revoke_session(
    token: str,
    x_user_role: Optional[str] = Header(None, alias="X-User-Role")
):
    """Revoque une session demo (superadmin uniquement)."""
    if x_user_role != "superadmin":
        raise HTTPException(status_code=403, detail="Acces refuse")
    write_central(
        "UPDATE APP_Demo_Sessions SET revoked = 1 WHERE token = ?",
        (token,)
    )
    return {"success": True, "message": "Session revoquee"}


@router.post("/admin/sessions/{token}/extend")
async def demo_extend_session(
    token: str,
    x_user_role: Optional[str] = Header(None, alias="X-User-Role")
):
    """Prolonge une session de 7 jours supplementaires (superadmin uniquement)."""
    if x_user_role != "superadmin":
        raise HTTPException(status_code=403, detail="Acces refuse")
    write_central(
        "UPDATE APP_Demo_Sessions SET expires_at = DATEADD(DAY, 7, expires_at) WHERE token = ?",
        (token,)
    )
    return {"success": True, "message": "Session prolongee de 7 jours"}


# ============================================================
# Chargement des donnees demo dans la base centrale
# ============================================================

async def _load_demo_data(
    target_table: str,
    data: List[Dict[str, Any]],
    columns: List[str],
    primary_key: List[str],
    societe_code: str,
) -> Dict[str, int]:
    """
    Charge les donnees demo dans la base centrale (tables prefixees DEMO_xxx_).
    Meme logique que _load_data_to_dwh mais utilise la connexion centrale.
    """
    if not data:
        return {"inserted": 0, "updated": 0}

    # Ajouter la colonne societe
    if "societe" not in columns:
        columns = ["societe"] + list(columns)
        for row in data:
            row["societe"] = societe_code

    if primary_key and "societe" not in primary_key:
        primary_key = ["societe"] + list(primary_key)

    inserted = 0
    updated = 0

    with _demo_db_cursor() as cursor:
        # Creer la table si elle n'existe pas
        cursor.execute(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = ?",
            (target_table,)
        )
        table_exists = cursor.fetchone()[0] > 0

        if not table_exists:
            sample = data[0]
            col_defs = []
            for col in columns:
                val = sample.get(col)
                if val is None:
                    sql_type = "NVARCHAR(500) NULL"
                elif isinstance(val, bool):
                    sql_type = "BIT NULL"
                elif isinstance(val, int):
                    sql_type = "BIGINT NULL"
                elif isinstance(val, float):
                    sql_type = "FLOAT NULL"
                else:
                    str_val = str(val) if val is not None else ""
                    if len(str_val) > 4000:
                        sql_type = "NVARCHAR(MAX) NULL"
                    elif len(str_val) > 500:
                        sql_type = "NVARCHAR(4000) NULL"
                    elif len(str_val) > 100:
                        sql_type = "NVARCHAR(500) NULL"
                    else:
                        sql_type = "NVARCHAR(255) NULL"
                col_defs.append(f"[{col}] {sql_type}")

            pk_constraint = ""
            if primary_key:
                pk_cols = ", ".join([f"[{pk}]" for pk in primary_key])
                safe_name = target_table.replace(" ", "_").replace("-", "_")
                pk_constraint = f", CONSTRAINT PK_{safe_name} PRIMARY KEY ({pk_cols})"

            create_sql = f"CREATE TABLE [{target_table}] ({', '.join(col_defs)}{pk_constraint})"
            try:
                cursor.execute(create_sql)
                cursor.commit()
            except Exception:
                create_sql_no_pk = f"CREATE TABLE [{target_table}] ({', '.join(col_defs)})"
                cursor.execute(create_sql_no_pk)
                cursor.commit()

        columns_str = ", ".join([f"[{c}]" for c in columns])
        placeholders = ", ".join(["?" for _ in columns])

        if primary_key:
            # Temp table + MERGE
            temp_table = f"#tmp_{target_table[-30:].replace(' ', '_')}"
            temp_cols = ", ".join([f"[{c}] NVARCHAR(MAX)" for c in columns])
            cursor.execute(f"CREATE TABLE {temp_table} ({temp_cols})")

            rows_values = []
            for row in data:
                rows_values.append(tuple(
                    str(row.get(c)) if row.get(c) is not None else None
                    for c in columns
                ))
            cursor.fast_executemany = True
            cursor.executemany(
                f"INSERT INTO {temp_table} ({columns_str}) VALUES ({placeholders})",
                rows_values
            )

            on_clause = " AND ".join(
                [f"target.[{pk}] = source.[{pk}]" for pk in primary_key]
            )
            update_cols = [c for c in columns if c not in primary_key]
            update_clause = ", ".join([f"target.[{c}] = source.[{c}]" for c in update_cols]) if update_cols else "target.[societe] = target.[societe]"

            merge_sql = f"""
                MERGE [{target_table}] AS target
                USING {temp_table} AS source ON ({on_clause})
                WHEN MATCHED THEN UPDATE SET {update_clause}
                WHEN NOT MATCHED THEN INSERT ({columns_str}) VALUES ({', '.join([f'source.[{c}]' for c in columns])});
            """
            cursor.execute(merge_sql)
            # Compter les lignes affectees
            inserted = len(data)
            cursor.commit()
        else:
            rows_values = []
            for row in data:
                rows_values.append(tuple(
                    str(row.get(c)) if row.get(c) is not None else None
                    for c in columns
                ))
            cursor.fast_executemany = True
            cursor.executemany(
                f"INSERT INTO [{target_table}] ({columns_str}) VALUES ({placeholders})",
                rows_values
            )
            inserted = len(data)
            cursor.commit()

    return {"inserted": inserted, "updated": updated}


# ============================================================
# Emails
# ============================================================

def _send_confirmation_email(email: str, nom: str, token: str):
    """Envoie l'email de confirmation d'inscription."""
    confirm_url = f"{APP_URL}/api/demo/confirm/{token}"
    result = send_email(
        to_emails=[email],
        subject="Confirmez votre accès démo OptiBoard",
        body_html=f"""
        <p>Bonjour {nom},</p>
        <p>Merci pour votre inscription à la démo OptiBoard.</p>
        <p>Cliquez sur le bouton ci-dessous pour confirmer votre email et
           accéder au téléchargement de l'AgentETL :</p>
        <p><a href="{confirm_url}" style="background:#2563eb;color:#fff;
           padding:12px 24px;border-radius:6px;text-decoration:none;display:inline-block;">
           Confirmer et télécharger l'AgentETL
        </a></p>
        <p>Ce lien est valable {DEMO_DURATION_DAYS} jours.</p>
        <p>L'équipe OptiBoard</p>
        """
    )
    if not result.get("success"):
        logger.error(f"Erreur envoi email confirmation [{email}]: {result.get('error')}")
    else:
        logger.info(f"Email confirmation envoyé à {email}")


def _send_launch_email(email: str, nom: str, token: str):
    """Envoie le lien d'accès direct pour le mode clone_ka (pas d'AgentETL)."""
    launch_url = f"{FRONTEND_URL}/demo/{token}/launch"
    result = send_email(
        to_emails=[email],
        subject="Accédez à votre démo OptiBoard — Données prêtes",
        body_html=f"""
        <p>Bonjour {nom},</p>
        <p>Votre espace démo OptiBoard est prêt avec des données de démonstration réelles (2025–2026).</p>
        <p><a href="{launch_url}" style="background:#2563eb;color:#fff;
           padding:12px 24px;border-radius:6px;text-decoration:none;display:inline-block;">
           Accéder à OptiBoard
        </a></p>
        <p>Votre accès est valable {DEMO_DURATION_DAYS} jours.</p>
        <p>L'équipe OptiBoard</p>
        """
    )
    if not result.get("success"):
        logger.error(f"Erreur envoi launch email [{email}]: {result.get('error')}")
    else:
        logger.info(f"Launch email envoyé à {email}")


def _send_download_email(email: str, nom: str, token: str):
    """Envoie l'email avec lien acces OptiBoard apres sync."""
    access_url = f"{FRONTEND_URL}/demo/{token}"
    result = send_email(
        to_emails=[email],
        subject="Vos données sont prêtes — Accédez à OptiBoard",
        body_html=f"""
        <p>Bonjour {nom},</p>
        <p>La synchronisation de vos données est terminée !</p>
        <p>Accédez à votre tableau de bord OptiBoard :</p>
        <p><a href="{access_url}" style="background:#16a34a;color:#fff;
           padding:12px 24px;border-radius:6px;text-decoration:none;display:inline-block;">
           Accéder à mon OptiBoard
        </a></p>
        <p>Votre accès est valable {DEMO_DURATION_DAYS} jours.</p>
        <p>L'équipe OptiBoard</p>
        """
    )
    if not result.get("success"):
        logger.error(f"Erreur envoi email access [{email}]: {result.get('error')}")


# ============================================================
# Pages HTML simples
# ============================================================

def _html_confirmation(nom: str, token: str, demo_mode: str = "agent_etl") -> str:
    if demo_mode == "clone_ka":
        redirect_url  = f"{FRONTEND_URL}/demo/{token}"
        redirect_label = "Suivre la préparation"
        msg = "Votre espace démo est en cours de préparation avec des données réelles 2025–2026."
    else:
        redirect_url  = f"{FRONTEND_URL}/demo/{token}"
        redirect_label = "Suivre l'état de ma démo"
        msg = "Un email avec le lien de téléchargement de l'AgentETL vient d'être envoyé."
    return f"""
    <!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8">
    <title>Demo OptiBoard — Confirmé</title>
    <meta http-equiv="refresh" content="3;url={redirect_url}">
    <style>body{{font-family:sans-serif;max-width:600px;margin:60px auto;text-align:center}}
    .btn{{background:#2563eb;color:#fff;padding:14px 28px;border-radius:8px;
          text-decoration:none;display:inline-block;margin-top:20px;font-size:16px}}</style>
    </head><body>
    <h2>Email confirmé !</h2>
    <p>Bonjour <strong>{nom}</strong>, votre accès démo OptiBoard est activé.</p>
    <p>{msg}</p>
    <p style="color:#6b7280;font-size:13px">Redirection automatique dans 3 secondes...</p>
    <a class="btn" href="{redirect_url}">{redirect_label}</a>
    </body></html>
    """


def _html_error(message: str) -> str:
    return f"""
    <!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8">
    <title>Erreur</title>
    <style>body{{font-family:sans-serif;max-width:600px;margin:60px auto;text-align:center}}
    .msg{{color:#dc2626;font-size:18px;margin-top:20px}}</style>
    </head><body>
    <h2>Accès démo</h2>
    <p class="msg">{message}</p>
    <p><a href="/">Retour à l'accueil</a></p>
    </body></html>
    """
