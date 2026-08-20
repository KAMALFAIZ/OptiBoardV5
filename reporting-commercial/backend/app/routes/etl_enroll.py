"""
Enrôlement des agents ETL par jeton à usage unique
====================================================

Remplace le provisionnement manuel (copier-coller de l'AgentId + de l'ApiKey,
script FIX_AGENT_KEY.ps1) par un échange sécurisé :

  1. L'admin émet un JETON D'ENRÔLEMENT lié à (dwh_code, agent_id), à durée de
     vie courte et à usage unique :
        POST /api/admin/etl/agents/{agent_id}/enroll-token   (require_admin)

  2. L'agent, au premier démarrage, échange ce jeton contre ses identifiants :
        POST /api/agents/enroll   { "token": "..." }
     -> régénère l'ApiKey de l'agent (la clé n'est exposée QU'À CET INSTANT),
        marque le jeton consommé, et renvoie { agent_id, api_key, dwh_code }.

Le jeton n'est jamais stocké en clair (seul son SHA-256 l'est). La route d'échange
vit sous le préfixe exempt `/api/agents/` (SESSION_OPTIONAL) : elle s'authentifie
par le jeton lui-même, pas par une session.

Additif : aucune route existante n'est modifiée. Le flux legacy (clé collée à la
main) reste fonctionnel tant que les agents déployés n'ont pas basculé.
"""

import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel

from app.database_unified import execute_central, write_central, client_cursor
from app.security import require_admin
# Réutilise la génération / le hachage de clé de l'implémentation agents (source unique).
from app.routes.etl_agents import generate_api_key, hash_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["ETL Enroll"])

# Durée de vie par défaut d'un jeton d'enrôlement (minutes).
ENROLL_TOKEN_TTL_MINUTES = 60 * 24  # 24 h


def _hash_token(token: str) -> str:
    """SHA-256 du jeton — seul le hash est persisté."""
    return hashlib.sha256(token.encode()).hexdigest()


def _ensure_enroll_table() -> None:
    """Crée APP_ETL_Enroll_Tokens dans la base centrale si absente (idempotent)."""
    write_central(
        """
        IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES
                       WHERE TABLE_NAME = 'APP_ETL_Enroll_Tokens')
        CREATE TABLE APP_ETL_Enroll_Tokens (
            token_hash   CHAR(64)      NOT NULL PRIMARY KEY,
            token_prefix VARCHAR(12)   NULL,
            dwh_code     NVARCHAR(40)  NOT NULL,
            agent_id     NVARCHAR(64)  NOT NULL,
            expires_at   DATETIME      NOT NULL,
            used_at      DATETIME      NULL,
            created_at   DATETIME      NOT NULL DEFAULT GETDATE(),
            created_by   NVARCHAR(120) NULL
        )
        """
    )


def mint_enroll_token(dwh_code: str, agent_id: str, ttl_minutes: Optional[int] = None) -> dict:
    """
    Crée et persiste un jeton d'enrôlement à usage unique. Renvoie le jeton en
    clair (à ne montrer qu'une fois) + son expiration. Fonction partagée entre la
    route admin et le téléchargement du fichier de config agent (dwh_admin).
    """
    _ensure_enroll_table()
    ttl = ttl_minutes if (ttl_minutes and ttl_minutes > 0) else ENROLL_TOKEN_TTL_MINUTES
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(minutes=ttl)
    write_central(
        """
        INSERT INTO APP_ETL_Enroll_Tokens
            (token_hash, token_prefix, dwh_code, agent_id, expires_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (_hash_token(token), token[:8], dwh_code, agent_id, expires_at),
    )
    logger.info(f"[ENROLL] Jeton émis pour agent={agent_id} dwh={dwh_code} ttl={ttl}min")
    return {"enroll_token": token, "expires_at": expires_at.isoformat() + "Z"}


class EnrollRequest(BaseModel):
    token: str


@router.post("/admin/etl/agents/{agent_id}/enroll-token", dependencies=[Depends(require_admin)])
def issue_enroll_token(
    agent_id: str,
    x_dwh_code: str = Header(..., alias="X-DWH-Code"),
    ttl_minutes: Optional[int] = None,
):
    """
    [ADMIN] Émet un jeton d'enrôlement à usage unique pour un agent existant.

    À remettre au client (ou à embarquer dans le fichier de config agent). Le jeton
    n'est affiché qu'une seule fois. Ne renvoie JAMAIS l'ApiKey : l'agent l'obtient
    en échangeant le jeton via /api/agents/enroll.
    """
    _ensure_enroll_table()

    # L'agent doit exister dans la base client du DWH (source de vérité).
    try:
        with client_cursor(x_dwh_code) as cur:
            cur.execute("SELECT agent_id FROM APP_ETL_Agents WHERE agent_id = ?", (agent_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Agent introuvable dans la base client")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ENROLL] Vérification agent échouée: {e}")
        raise HTTPException(status_code=502, detail="Base client inaccessible")

    minted = mint_enroll_token(x_dwh_code, agent_id, ttl_minutes)

    return {
        "success": True,
        "enroll_token": minted["enroll_token"],
        "agent_id": agent_id,
        "dwh_code": x_dwh_code,
        "expires_at": minted["expires_at"],
        "warning": "Jeton à usage unique — copiez-le maintenant, il ne sera plus affiché.",
    }


@router.post("/agents/enroll")
def enroll_agent(req: EnrollRequest):
    """
    [AGENT] Échange un jeton d'enrôlement contre les identifiants définitifs.

    Régénère l'ApiKey de l'agent lié au jeton (la clé n'est renvoyée qu'ici),
    consomme le jeton, et renvoie { agent_id, api_key, dwh_code }.
    Route non authentifiée par session : le jeton EST l'authentification.
    """
    _ensure_enroll_table()
    token_hash = _hash_token(req.token)

    rows = execute_central(
        """
        SELECT dwh_code, agent_id, expires_at, used_at
        FROM APP_ETL_Enroll_Tokens WHERE token_hash = ?
        """,
        (token_hash,), use_cache=False,
    )
    if not rows:
        raise HTTPException(status_code=401, detail="Jeton d'enrôlement invalide")

    rec = rows[0]
    if rec["used_at"] is not None:
        raise HTTPException(status_code=409, detail="Jeton déjà utilisé")
    if rec["expires_at"] < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Jeton expiré")

    dwh_code = rec["dwh_code"]
    agent_id = rec["agent_id"]

    # Nouvelle clé : le hash part en base client, la clé claire ne vit que dans la réponse.
    api_key = generate_api_key()
    api_key_hash = hash_api_key(api_key)
    api_key_prefix = api_key[:7] + "..."

    try:
        with client_cursor(dwh_code) as cur:
            cur.execute(
                """
                UPDATE APP_ETL_Agents
                SET api_key_hash = ?, api_key_prefix = ?, is_active = 1, updated_at = GETDATE()
                WHERE agent_id = ?
                """,
                (api_key_hash, api_key_prefix, agent_id),
            )
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Agent introuvable pour ce jeton")
            cur.commit()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ENROLL] Écriture clé échouée agent={agent_id}: {e}")
        raise HTTPException(status_code=502, detail="Base client inaccessible")

    # Consommer le jeton (idempotence : garde-fou WHERE used_at IS NULL).
    write_central(
        "UPDATE APP_ETL_Enroll_Tokens SET used_at = GETDATE() WHERE token_hash = ? AND used_at IS NULL",
        (token_hash,),
    )
    logger.info(f"[ENROLL] Agent enrôlé agent={agent_id} dwh={dwh_code}")

    return {
        "success": True,
        "agent_id": agent_id,
        "api_key": api_key,
        "dwh_code": dwh_code,
    }
