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
    serveur_sage: str = "."   # défaut = serveur local (client autonome)
    base_sage: str
    user_sage: str = ""
    password_sage: str = ""
    etl_enabled: bool = True
    etl_mode: str = "incremental"
    etl_schedule: str = "*/15 * * * *"


class ClientSourceUpdate(BaseModel):
    nom_societe: Optional[str] = None
    serveur_sage: Optional[str] = None
    base_sage: Optional[str] = None
    user_sage: Optional[str] = None
    password_sage: Optional[str] = None
    etl_enabled: Optional[bool] = None
    etl_mode: Optional[str] = None
    etl_schedule: Optional[str] = None


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
# Sources Sage (APP_DWH_Sources — base centrale)
# ============================================================

@router.get("/dwh-sources")
async def get_client_dwh_sources(
    dwh_code: Optional[str] = Header(None, alias="X-DWH-Code")
):
    """Liste les sources Sage du DWH client."""
    code = _require_dwh(dwh_code)
    try:
        def _fetch():
            return execute_central(
                "SELECT code_societe, nom_societe, serveur_sage, base_sage, "
                "user_sage, etl_enabled, etl_mode, etl_schedule, last_sync, last_sync_status, actif "
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
    """Ajoute une source Sage pour le DWH client."""
    code = _require_dwh(dwh_code)
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
                "(dwh_code, code_societe, nom_societe, serveur_sage, base_sage, "
                "user_sage, password_sage, etl_enabled, etl_mode, etl_schedule) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (code, data.code_societe, data.nom_societe,
                 data.serveur_sage, data.base_sage, data.user_sage, data.password_sage,
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
    """Met à jour une source Sage du DWH client."""
    code = _require_dwh(dwh_code)
    try:
        def _update():
            # Construire dynamiquement les champs à mettre à jour
            fields, vals = [], []
            if data.nom_societe   is not None: fields.append("nom_societe=?");   vals.append(data.nom_societe)
            if data.serveur_sage  is not None: fields.append("serveur_sage=?");  vals.append(data.serveur_sage)
            if data.base_sage     is not None: fields.append("base_sage=?");     vals.append(data.base_sage)
            if data.user_sage     is not None: fields.append("user_sage=?");     vals.append(data.user_sage)
            if data.password_sage is not None and data.password_sage != "":
                fields.append("password_sage=?"); vals.append(data.password_sage)
            if data.etl_enabled   is not None: fields.append("etl_enabled=?");  vals.append(1 if data.etl_enabled else 0)
            if data.etl_mode      is not None: fields.append("etl_mode=?");      vals.append(data.etl_mode)
            if data.etl_schedule  is not None: fields.append("etl_schedule=?");  vals.append(data.etl_schedule)
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


