"""
Client Portal — Endpoints pour les admin_client
Gestion DWH (info + sources Sage), SMTP et licence propre au client.
Tous les endpoints requièrent le header X-DWH-Code.
"""
import asyncio
import logging
import smtplib
from email.mime.text import MIMEText
from typing import Optional

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from ..database_unified import execute_central, write_central, execute_client, write_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/client", tags=["client-portal"])


# ============================================================
# Schemas
# ============================================================

class ClientSourceCreate(BaseModel):
    code_societe: str
    nom_societe: str
    etl_enabled: bool = True
    etl_mode: str = "incremental"
    etl_schedule: str = "*/15 * * * *"
    # Champs credentials conservés pour rétrocompatibilité — ignorés (v2 architecture).
    # Les credentials Sage doivent être configurés dans l'agent ETL (APP_ETL_Agents).
    serveur_sage: Optional[str] = None
    base_sage: Optional[str] = None
    user_sage: Optional[str] = None
    password_sage: Optional[str] = None


class ClientSourceUpdate(BaseModel):
    nom_societe: Optional[str] = None
    etl_enabled: Optional[bool] = None
    etl_mode: Optional[str] = None
    etl_schedule: Optional[str] = None
    # Champs credentials conservés pour rétrocompatibilité — ignorés (v2 architecture).
    # Les credentials Sage doivent être mis à jour via l'agent ETL correspondant.
    serveur_sage: Optional[str] = None
    base_sage: Optional[str] = None
    user_sage: Optional[str] = None
    password_sage: Optional[str] = None


class ClientSmtpConfig(BaseModel):
    smtp_server: str
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    from_email: str
    from_name: str = ""
    use_tls: bool = True


class SmtpTestRequest(BaseModel):
    test_email: str


def _require_dwh(dwh_code: Optional[str]) -> str:
    if not dwh_code:
        raise HTTPException(status_code=400, detail="X-DWH-Code header requis")
    return dwh_code


# ============================================================
# DWH Info (lecture seule — sans credentials serveur)
# ============================================================

@router.get("/dwh-info")
async def get_client_dwh_info(
    dwh_code: Optional[str] = Header(None, alias="X-DWH-Code")
):
    """Retourne les informations publiques du DWH client (sans passwords)."""
    code = _require_dwh(dwh_code)
    try:
        def _fetch():
            return execute_central(
                "SELECT code, nom, raison_sociale, adresse, ville, pays, "
                "telephone, email, logo_url, actif "
                "FROM APP_DWH WHERE code = ?",
                (code,),
                use_cache=False,
            )
        rows = await asyncio.to_thread(_fetch)
        if not rows:
            raise HTTPException(status_code=404, detail=f"DWH '{code}' introuvable")
        return {"success": True, "data": rows[0]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CLIENT PORTAL] get_client_dwh_info error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Dernière synchronisation (affichée au démarrage de l'application)
# ============================================================

@router.get("/last-sync")
async def get_client_last_sync(
    dwh_code: Optional[str] = Header(None, alias="X-DWH-Code")
):
    """Dernière synchronisation ETL connue pour le DWH courant.

    Lecture seule, accessible à tout utilisateur authentifié du tenant
    (le middleware d'auth impose déjà une session valide et le tenant).
    Source primaire : APP_ETL_Agents (base client). Repli : APP_ETL_Agent_Tables
    (base client), puis APP_DWH_Sources (base centrale) si l'agent n'a jamais
    remonté de heartbeat. Ne renvoie AUCUN credential.
    """
    code = _require_dwh(dwh_code)

    def _fetch():
        data = {
            "last_sync": None,
            "status": None,
            "agent_name": None,
            "tables_synced": 0,
            "rows_synced": 0,
            "source": None,
            "last_heartbeat": None,
            "agent_status": None,
        }

        # 1) Agent ETL (base client)
        try:
            rows = execute_client(
                "SELECT TOP 1 nom, last_sync, last_sync_statut, total_lignes_sync, "
                "last_heartbeat, statut "
                "FROM APP_ETL_Agents "
                "ORDER BY CASE WHEN last_sync IS NULL THEN 1 ELSE 0 END, "
                "last_sync DESC, last_heartbeat DESC",
                dwh_code=code, use_cache=False,
            )
            if rows:
                r = rows[0]
                data.update({
                    "last_sync": r.get("last_sync"),
                    "status": r.get("last_sync_statut"),
                    "agent_name": r.get("nom"),
                    "rows_synced": r.get("total_lignes_sync") or 0,
                    "last_heartbeat": r.get("last_heartbeat"),
                    "agent_status": r.get("statut"),
                    "source": "agent" if r.get("last_sync") else None,
                })
        except Exception as e:
            logger.debug(f"[CLIENT PORTAL] last-sync agents ({code}): {e}")

        # 2) Détail par table (base client) — complète/prend le relais
        try:
            rows = execute_client(
                "SELECT MAX(last_sync) AS max_sync, COUNT(*) AS nb, "
                "SUM(CASE WHEN last_sync_status = 'error' THEN 1 ELSE 0 END) AS nb_err "
                "FROM APP_ETL_Agent_Tables WHERE last_sync IS NOT NULL",
                dwh_code=code, use_cache=False,
            )
            if rows and rows[0].get("max_sync"):
                r = rows[0]
                data["tables_synced"] = r.get("nb") or 0
                if not data["last_sync"] or r["max_sync"] > data["last_sync"]:
                    data["last_sync"] = r["max_sync"]
                    data["source"] = "tables"
                if not data["status"]:
                    data["status"] = "error" if (r.get("nb_err") or 0) > 0 else "success"
        except Exception as e:
            logger.debug(f"[CLIENT PORTAL] last-sync tables ({code}): {e}")

        # 3) Repli base centrale (sources déclarées)
        if not data["last_sync"]:
            try:
                rows = execute_central(
                    "SELECT TOP 1 nom_societe, last_sync, last_sync_status "
                    "FROM APP_DWH_Sources WHERE dwh_code = ? AND last_sync IS NOT NULL "
                    "ORDER BY last_sync DESC",
                    (code,), use_cache=False,
                )
                if rows:
                    r = rows[0]
                    data.update({
                        "last_sync": r.get("last_sync"),
                        "status": r.get("last_sync_status"),
                        "agent_name": r.get("nom_societe"),
                        "source": "source",
                    })
            except Exception as e:
                logger.debug(f"[CLIENT PORTAL] last-sync sources ({code}): {e}")

        return data

    try:
        data = await asyncio.to_thread(_fetch)
        from datetime import datetime, date
        for key in ("last_sync", "last_heartbeat"):
            v = data.get(key)
            if isinstance(v, (datetime, date)):
                data[key] = v.isoformat()
                if isinstance(v, datetime):
                    age = max(0, int((datetime.now() - v).total_seconds()))
                    data["age_seconds" if key == "last_sync" else "heartbeat_age_seconds"] = age
        return {"success": True, "data": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CLIENT PORTAL] get_client_last_sync error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Sources Sage (APP_DWH_Sources — base centrale)
# ============================================================

@router.get("/dwh-sources")
async def get_client_dwh_sources(
    dwh_code: Optional[str] = Header(None, alias="X-DWH-Code")
):
    """Liste les sources Sage du DWH client (metadata uniquement — pas de credentials)."""
    code = _require_dwh(dwh_code)
    try:
        def _fetch():
            return execute_central(
                "SELECT code_societe, nom_societe, agent_id, "
                "etl_enabled, etl_mode, etl_schedule, last_sync, last_sync_status, actif "
                "FROM APP_DWH_Sources WHERE dwh_code = ? ORDER BY code_societe",
                (code,),
                use_cache=False,
            )
        rows = await asyncio.to_thread(_fetch)
        # Sérialiser les dates
        from datetime import datetime, date
        def _ser(r):
            return {k: (v.isoformat() if isinstance(v, (datetime, date)) else v) for k, v in r.items()}
        return {"success": True, "data": [_ser(r) for r in rows]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CLIENT PORTAL] get_client_dwh_sources error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dwh-sources")
async def create_client_dwh_source(
    data: ClientSourceCreate,
    dwh_code: Optional[str] = Header(None, alias="X-DWH-Code")
):
    """Ajoute une source Sage (entrée monitoring) pour le DWH client.
    Les credentials Sage doivent être configurés dans l'agent ETL (APP_ETL_Agents).
    """
    code = _require_dwh(dwh_code)
    if data.serveur_sage or data.base_sage or data.user_sage or data.password_sage:
        logger.warning(
            f"[CLIENT PORTAL] POST /dwh-sources {code}/{data.code_societe}: "
            "champs credentials reçus mais ignorés (v2 arch — configurer via agent ETL)"
        )
    try:
        def _insert():
            # Vérifier si la source existe déjà
            existing = execute_central(
                "SELECT code_societe FROM APP_DWH_Sources WHERE dwh_code=? AND code_societe=?",
                (code, data.code_societe),
                use_cache=False,
            )
            if existing:
                raise ValueError(f"Source '{data.code_societe}' existe déjà pour ce DWH")
            write_central(
                "INSERT INTO APP_DWH_Sources "
                "(dwh_code, code_societe, nom_societe, etl_enabled, etl_mode, etl_schedule) "
                "VALUES (?,?,?,?,?,?)",
                (code, data.code_societe, data.nom_societe,
                 1 if data.etl_enabled else 0, data.etl_mode, data.etl_schedule),
            )
        await asyncio.to_thread(_insert)
        return {"success": True, "message": f"Source '{data.code_societe}' ajoutée"}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CLIENT PORTAL] create_client_dwh_source error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/dwh-sources/{code_societe}")
async def update_client_dwh_source(
    code_societe: str,
    data: ClientSourceUpdate,
    dwh_code: Optional[str] = Header(None, alias="X-DWH-Code")
):
    """Met à jour une source Sage du DWH client (metadata uniquement).
    Les credentials Sage doivent être mis à jour via l'agent ETL correspondant.
    """
    code = _require_dwh(dwh_code)
    if data.serveur_sage or data.base_sage or data.user_sage or data.password_sage:
        logger.warning(
            f"[CLIENT PORTAL] PUT /dwh-sources/{code_societe}: "
            "champs credentials reçus mais ignorés (v2 arch — mettre à jour via agent ETL)"
        )
    try:
        def _update():
            # Construire dynamiquement les champs à mettre à jour (metadata uniquement)
            fields, vals = [], []
            if data.nom_societe is not None: fields.append("nom_societe=?"); vals.append(data.nom_societe)
            if data.etl_enabled is not None: fields.append("etl_enabled=?"); vals.append(1 if data.etl_enabled else 0)
            if data.etl_mode    is not None: fields.append("etl_mode=?");    vals.append(data.etl_mode)
            if data.etl_schedule is not None: fields.append("etl_schedule=?"); vals.append(data.etl_schedule)
            if not fields:
                raise ValueError("Aucun champ à mettre à jour")
            vals += [code, code_societe]
            write_central(
                f"UPDATE APP_DWH_Sources SET {', '.join(fields)} WHERE dwh_code=? AND code_societe=?",
                tuple(vals),
            )
        await asyncio.to_thread(_update)
        return {"success": True, "message": f"Source '{code_societe}' mise à jour"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CLIENT PORTAL] update_client_dwh_source error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/dwh-sources/{code_societe}")
async def delete_client_dwh_source(
    code_societe: str,
    dwh_code: Optional[str] = Header(None, alias="X-DWH-Code")
):
    """Supprime une source Sage du DWH client."""
    code = _require_dwh(dwh_code)
    try:
        def _delete():
            write_central(
                "DELETE FROM APP_DWH_Sources WHERE dwh_code=? AND code_societe=?",
                (code, code_societe),
            )
        await asyncio.to_thread(_delete)
        return {"success": True, "message": f"Source '{code_societe}' supprimée"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CLIENT PORTAL] delete_client_dwh_source error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# SMTP (APP_EmailConfig — base client OptiBoard_XXX)
# ============================================================

@router.get("/smtp")
async def get_client_smtp(
    dwh_code: Optional[str] = Header(None, alias="X-DWH-Code")
):
    """Retourne la config SMTP du client."""
    code = _require_dwh(dwh_code)
    try:
        def _fetch():
            return execute_client(
                "SELECT smtp_server, smtp_port, smtp_username, smtp_password, "
                "from_email, from_name, use_tls "
                "FROM APP_EmailConfig WHERE actif=1",
                dwh_code=code,
                use_cache=False,
            )
        rows = await asyncio.to_thread(_fetch)
        return {"success": True, "data": rows[0] if rows else None}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CLIENT PORTAL] get_client_smtp error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/smtp")
async def save_client_smtp(
    smtp: ClientSmtpConfig,
    dwh_code: Optional[str] = Header(None, alias="X-DWH-Code")
):
    """Sauvegarde la config SMTP du client (remplace l'existante)."""
    code = _require_dwh(dwh_code)
    try:
        def _save():
            write_client(
                "DELETE FROM APP_EmailConfig; "
                "INSERT INTO APP_EmailConfig "
                "(smtp_server, smtp_port, smtp_username, smtp_password, "
                "from_email, from_name, use_tls, actif) "
                "VALUES (?,?,?,?,?,?,?,1)",
                (smtp.smtp_server, smtp.smtp_port, smtp.smtp_username,
                 smtp.smtp_password, smtp.from_email, smtp.from_name,
                 1 if smtp.use_tls else 0),
                dwh_code=code,
            )
        await asyncio.to_thread(_save)
        return {"success": True, "message": "Configuration SMTP sauvegardée"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CLIENT PORTAL] save_client_smtp error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/smtp/test")
async def test_client_smtp(
    request: SmtpTestRequest,
    dwh_code: Optional[str] = Header(None, alias="X-DWH-Code")
):
    """Envoie un email de test via la config SMTP du client."""
    code = _require_dwh(dwh_code)
    try:
        def _test():
            rows = execute_client(
                "SELECT smtp_server, smtp_port, smtp_username, smtp_password, "
                "from_email, from_name, use_tls "
                "FROM APP_EmailConfig WHERE actif=1",
                dwh_code=code,
                use_cache=False,
            )
            if not rows:
                raise ValueError("Aucune configuration SMTP trouvée. Configurez d'abord le SMTP.")
            cfg = rows[0]
            msg = MIMEText("Ceci est un email de test depuis OptiBoard Client Portal.")
            msg["Subject"] = "Test SMTP — OptiBoard"
            msg["From"] = cfg["from_email"]
            msg["To"] = request.test_email
            with smtplib.SMTP(cfg["smtp_server"], cfg["smtp_port"], timeout=15) as server:
                if cfg["use_tls"]:
                    server.starttls()
                if cfg.get("smtp_username"):
                    server.login(cfg["smtp_username"], cfg["smtp_password"])
                server.send_message(msg)

        await asyncio.to_thread(_test)
        return {"success": True, "message": f"Email de test envoyé à {request.test_email}"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except smtplib.SMTPException as e:
        raise HTTPException(status_code=400, detail=f"Erreur SMTP: {str(e)}")
    except Exception as e:
        logger.error(f"[CLIENT PORTAL] test_client_smtp error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


