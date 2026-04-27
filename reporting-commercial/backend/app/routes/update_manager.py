"""
Module MAJ (Update Manager)
============================
Permet aux clients (connectes ou autonomes) de verifier et appliquer
les mises a jour publiees par le central KASOFT.

Flux :
  Central (OptiBoard_SaaS) publie → APP_Update_History du client enregistre
  Client  demande /check          → liste des MAJ disponibles vs installees
  Client  demande /pull           → tire et applique les MAJ manquantes

Source du catalogue maitre :
  - Si MASTER_API_URL configuré dans .env → fetch HTTP vers serveur central distant
  - Sinon → fallback sur la base centrale LOCALE (OptiBoard_SaaS)

Clients autonomes : se connectent ponctuellement via ce module uniquement.
Clients connectes : MAJ automatiques + possibilite manuelle ici.
"""
import logging
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

import urllib.request
import urllib.error
import urllib.parse

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from ..config import get_settings
from ..database_unified import (
    execute_central, write_central, central_cursor,
    execute_client, write_client, client_cursor,
)


# ============================================================
# Master remote fetch helpers
# ============================================================

def _master_remote_enabled() -> bool:
    """True si MASTER_API_URL est configurée → on tire depuis HTTP distant."""
    s = get_settings()
    return bool((getattr(s, "MASTER_API_URL", "") or "").strip())


def _master_fetch(path: str) -> Dict[str, Any]:
    """
    GET HTTP sur le serveur master distant. Renvoie le JSON parsé.
    Lève HTTPException 502/504 en cas d'échec réseau.
    """
    s = get_settings()
    base_url = (s.MASTER_API_URL or "").rstrip("/")
    api_key  = (s.MASTER_API_KEY or "").strip()
    timeout  = int(getattr(s, "MASTER_TIMEOUT", 30) or 30)

    if not base_url:
        raise HTTPException(status_code=400, detail="MASTER_API_URL non configuré")

    url = f"{base_url}{path}"
    req = urllib.request.Request(url, method="GET")
    if api_key:
        req.add_header("X-Master-Api-Key", api_key)
    req.add_header("Accept", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read().decode("utf-8")
            return json.loads(data)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore") if e.fp else ""
        raise HTTPException(
            status_code=502,
            detail=f"Master {url} → HTTP {e.code} : {body[:200]}"
        )
    except (urllib.error.URLError, TimeoutError) as e:
        raise HTTPException(status_code=504, detail=f"Master {url} injoignable : {e}")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=502, detail=f"Master {url} → JSON invalide : {e}")


def _master_get_items(entity: str) -> List[Dict[str, Any]]:
    """
    Récupère la liste d'items pour une entité depuis le master distant.
    entity ∈ {'menus', 'dashboards', 'gridviews', 'pivots', 'datasources'}
    """
    payload = _master_fetch(f"/api/master/{entity}")
    return payload.get("items", []) or []

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/updates", tags=["Update Manager"])


# ============================================================
# Helpers
# ============================================================

def _require_dwh(dwh_code: Optional[str]) -> str:
    if not dwh_code:
        raise HTTPException(status_code=400, detail="X-DWH-Code header requis")
    return dwh_code


# ============================================================
# Master config endpoints (test/update connexion serveur central)
# ============================================================

class MasterConfigPayload(BaseModel):
    MASTER_API_URL: str = ""
    MASTER_API_KEY: str = ""
    MASTER_TIMEOUT: int = 30


class MasterTestPayload(BaseModel):
    """Test connexion ad-hoc sans sauvegarder dans .env."""
    url: str
    api_key: str = ""
    timeout: int = 15


@router.get("/master/config")
async def get_master_config():
    """Renvoie la config master courante (clé masquée)."""
    s = get_settings()
    return {
        "MASTER_API_URL": s.MASTER_API_URL,
        "MASTER_API_KEY": "***" if s.MASTER_API_KEY else "",
        "MASTER_TIMEOUT": getattr(s, "MASTER_TIMEOUT", 30),
        "enabled": _master_remote_enabled(),
    }


@router.post("/master/config")
async def save_master_config(cfg: MasterConfigPayload):
    """Sauvegarde MASTER_API_URL/KEY/TIMEOUT dans .env et recharge les settings."""
    from ..config import save_env_config, reload_settings
    payload = {
        "MASTER_API_URL": cfg.MASTER_API_URL.strip().rstrip("/"),
        "MASTER_TIMEOUT": str(int(cfg.MASTER_TIMEOUT or 30)),
    }
    # Ne pas écraser la clé si masquée par "***"
    if cfg.MASTER_API_KEY and cfg.MASTER_API_KEY != "***":
        payload["MASTER_API_KEY"] = cfg.MASTER_API_KEY.strip()
    save_env_config(payload)
    s = reload_settings()
    return {
        "success": True,
        "MASTER_API_URL": s.MASTER_API_URL,
        "enabled": _master_remote_enabled(),
    }


@router.post("/master/test")
async def test_master_connection(cfg: MasterTestPayload):
    """
    Teste une URL/clé master sans la sauvegarder.
    Appelle GET /api/master/info sur l'URL fournie.
    """
    base = (cfg.url or "").strip().rstrip("/")
    if not base:
        raise HTTPException(status_code=400, detail="URL master requise")

    api_key = (cfg.api_key or "").strip()
    # Si la clé est masquée → utiliser celle du .env
    if api_key == "***":
        api_key = (get_settings().MASTER_API_KEY or "").strip()

    url = f"{base}/api/master/info"
    req = urllib.request.Request(url, method="GET")
    if api_key:
        req.add_header("X-Master-Api-Key", api_key)
    req.add_header("Accept", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=int(cfg.timeout or 15)) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return {
            "success": True,
            "url": url,
            "version": data.get("version"),
            "counts":  data.get("counts", {}),
            "total":   data.get("total", 0),
        }
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore") if e.fp else ""
        if e.code == 503:
            return {"success": False, "error": "Master désactivé sur ce serveur (MASTER_API_KEY non configuré côté serveur)"}
        if e.code in (401, 403):
            return {"success": False, "error": f"Clé API invalide ou manquante (HTTP {e.code})"}
        return {"success": False, "error": f"HTTP {e.code} : {body[:200]}"}
    except (urllib.error.URLError, TimeoutError) as e:
        return {"success": False, "error": f"Serveur injoignable : {e}"}
    except json.JSONDecodeError:
        return {"success": False, "error": "Réponse non-JSON (URL incorrecte ?)"}


def _get_client_last_update(dwh_code: str, type_entite: str) -> Optional[datetime]:
    """Retourne la date de la derniere MAJ installee pour un type d'entite."""
    try:
        rows = execute_client(
            "SELECT MAX(date_installation) FROM APP_Update_History WHERE type_entite=? AND statut='succes'",
            (type_entite,),
            dwh_code=dwh_code,
        )
        if rows and rows[0][0]:
            return rows[0][0]
    except Exception:
        pass
    return None


# ============================================================
# GET /api/updates/check
# Compare le catalogue central avec les MAJ installees chez le client
# ============================================================

@router.get("/check")
async def check_updates(
    dwh_code: Optional[str] = Header(None, alias="X-DWH-Code"),
):
    """
    Verifie si des mises a jour sont disponibles depuis le central.
    Retourne le nombre de MAJ en attente par categorie.
    """
    code = _require_dwh(dwh_code)

    result = {
        "etl_tables": {"pending": 0, "items": [], "last_applied": None},
        "dashboards": {"pending": 0, "items": [], "last_applied": None},
        "gridviews":  {"pending": 0, "items": [], "last_applied": None},
        "pivots":     {"pending": 0, "items": [], "last_applied": None},
        "menus":      {"pending": 0, "items": [], "last_applied": None},
    }

    # --- ETL Tables ---
    try:
        last_etl = _get_client_last_update(code, "etl_table")
        result["etl_tables"]["last_applied"] = last_etl.isoformat() if last_etl else None

        # Tables dans le catalogue central
        central_tables = execute_central(
            "SELECT code, nom, updated_at FROM APP_ETL_Tables_Config WHERE actif=1",
        )
        # Tables deja installees chez le client
        installed = {
            r["code_entite"]: r["version_installee"]
            for r in (execute_client(
                "SELECT code_entite, version_installee FROM APP_Update_History WHERE type_entite='etl_table' AND statut='succes'",
                dwh_code=code,
            ) or [])
        }

        for t in (central_tables or []):
            t_code = t.get("code") or t[0]
            t_nom  = t.get("nom")  or t[1]
            if t_code not in installed:
                result["etl_tables"]["items"].append({"code": t_code, "nom": t_nom, "statut": "non_installe"})
                result["etl_tables"]["pending"] += 1
    except Exception as e:
        logger.warning(f"check_updates ETL tables: {e}")

    remote = _master_remote_enabled()

    # --- Dashboards ---
    try:
        last_dash = _get_client_last_update(code, "dashboard")
        result["dashboards"]["last_applied"] = last_dash.isoformat() if last_dash else None

        if remote:
            central_dash = _master_get_items("dashboards")
        else:
            central_dash = execute_central(
                "SELECT code, nom, date_modification FROM APP_Dashboards WHERE actif=1",
            )
        installed_dash = {
            r["code_entite"]
            for r in (execute_client(
                "SELECT code_entite FROM APP_Update_History WHERE type_entite='dashboard' AND statut='succes'",
                dwh_code=code,
            ) or [])
        }
        for d in (central_dash or []):
            d_code = d.get("code") or d[0]
            d_nom  = d.get("nom")  or d[1]
            if d_code not in installed_dash:
                result["dashboards"]["items"].append({"code": d_code, "nom": d_nom, "statut": "non_installe"})
                result["dashboards"]["pending"] += 1
    except Exception as e:
        logger.warning(f"check_updates dashboards: {e}")

    # --- GridViews ---
    try:
        last_gv = _get_client_last_update(code, "gridview")
        result["gridviews"]["last_applied"] = last_gv.isoformat() if last_gv else None

        if remote:
            central_gv = _master_get_items("gridviews")
        else:
            central_gv = execute_central(
                "SELECT code, nom, date_modification FROM APP_GridViews WHERE actif=1",
            )
        installed_gv = {
            r["code_entite"]
            for r in (execute_client(
                "SELECT code_entite FROM APP_Update_History WHERE type_entite='gridview' AND statut='succes'",
                dwh_code=code,
            ) or [])
        }
        for g in (central_gv or []):
            g_code = g.get("code") or g[0]
            g_nom  = g.get("nom")  or g[1]
            if g_code not in installed_gv:
                result["gridviews"]["items"].append({"code": g_code, "nom": g_nom, "statut": "non_installe"})
                result["gridviews"]["pending"] += 1
    except Exception as e:
        logger.warning(f"check_updates gridviews: {e}")

    # --- Menus ---
    try:
        last_menu = _get_client_last_update(code, "menu")
        result["menus"]["last_applied"] = last_menu.isoformat() if last_menu else None

        if remote:
            central_menus = _master_get_items("menus")
        else:
            central_menus = execute_central(
                "SELECT code, nom, date_modification FROM APP_Menus WHERE actif=1",
            )
        installed_menus = {
            r["code_entite"]
            for r in (execute_client(
                "SELECT code_entite FROM APP_Update_History WHERE type_entite='menu' AND statut='succes'",
                dwh_code=code,
            ) or [])
        }
        for m in (central_menus or []):
            m_code = m.get("code") or m[0]
            m_nom  = m.get("nom")  or m[1]
            if m_code not in installed_menus:
                result["menus"]["items"].append({"code": m_code, "nom": m_nom, "statut": "non_installe"})
                result["menus"]["pending"] += 1
    except Exception as e:
        logger.warning(f"check_updates menus: {e}")

    total_pending = sum(v["pending"] for v in result.values())
    return {
        "success": True,
        "total_pending": total_pending,
        "categories": result,
        "source": "remote_http" if remote else "local_central_db",
        "checked_at": datetime.now().isoformat(),
    }


# ============================================================
# POST /api/updates/pull/etl
# Tire les tables ETL du catalogue central vers la base client
# ============================================================

@router.post("/pull/etl")
async def pull_etl_updates(
    dwh_code: Optional[str] = Header(None, alias="X-DWH-Code"),
):
    """Applique les mises a jour des tables ETL depuis le catalogue central."""
    code = _require_dwh(dwh_code)

    try:
        # Tables catalogue central
        central_tables = execute_central(
            """SELECT code, nom, table_name, target_table, source_query,
                      primary_key_columns, sync_type, timestamp_column,
                      interval_minutes, priority, delete_detection, description
               FROM APP_ETL_Tables_Config WHERE actif=1""",
        )
        if not central_tables:
            return {"success": True, "applied": 0, "message": "Aucune table dans le catalogue central"}

        # Tables deja publiees chez le client
        existing = {
            r["code"]: r
            for r in (execute_client(
                "SELECT code, version FROM APP_ETL_Tables_Published",
                dwh_code=code,
            ) or [])
        }

        applied = 0
        errors  = []

        for t in central_tables:
            t_code = t.get("code") or t[0]
            try:
                # Upsert dans APP_ETL_Tables_Published
                write_client(
                    """IF EXISTS (SELECT 1 FROM APP_ETL_Tables_Published WHERE code=?)
                         UPDATE APP_ETL_Tables_Published SET
                           nom=?, table_name=?, target_table=?, source_query=?,
                           primary_key_columns=?, sync_type=?, timestamp_column=?,
                           interval_minutes=?, priority=?, delete_detection=?,
                           description=?, date_modification=GETDATE()
                         WHERE code=?
                       ELSE
                         INSERT INTO APP_ETL_Tables_Published
                           (code, nom, table_name, target_table, source_query,
                            primary_key_columns, sync_type, timestamp_column,
                            interval_minutes, priority, delete_detection, description)
                         VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        # UPDATE params
                        t_code,
                        t.get("nom") or t[1], t.get("table_name") or t[2],
                        t.get("target_table") or t[3], t.get("source_query") or t[4],
                        t.get("primary_key_columns") or t[5], t.get("sync_type") or t[6],
                        t.get("timestamp_column") or t[7], t.get("interval_minutes") or t[8],
                        t.get("priority") or t[9], t.get("delete_detection") or t[10],
                        t.get("description") or t[11], t_code,
                        # INSERT params
                        t_code,
                        t.get("nom") or t[1], t.get("table_name") or t[2],
                        t.get("target_table") or t[3], t.get("source_query") or t[4],
                        t.get("primary_key_columns") or t[5], t.get("sync_type") or t[6],
                        t.get("timestamp_column") or t[7], t.get("interval_minutes") or t[8],
                        t.get("priority") or t[9], t.get("delete_detection") or t[10],
                        t.get("description") or t[11],
                    ),
                    dwh_code=code,
                )

                # Enregistrer dans APP_Update_History
                prev_version = existing.get(t_code, {}).get("version") if isinstance(existing.get(t_code), dict) else None
                write_client(
                    """INSERT INTO APP_Update_History
                         (type_entite, code_entite, nom_entite, version_precedente, version_installee, statut)
                       VALUES ('etl_table', ?, ?, ?, 1, 'succes')""",
                    (t_code, t.get("nom") or t[1], prev_version),
                    dwh_code=code,
                )
                applied += 1
            except Exception as e:
                logger.error(f"pull_etl {t_code}: {e}")
                errors.append({"code": t_code, "error": str(e)})

        return {
            "success": True,
            "applied": applied,
            "errors": errors,
            "message": f"{applied} table(s) ETL mises a jour",
        }

    except Exception as e:
        logger.error(f"pull_etl_updates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# POST /api/updates/pull/builder
# Tire les elements Builder (dashboards, gridviews, pivots, menus)
# depuis le central vers la base client
# ============================================================

@router.post("/pull/builder")
async def pull_builder_updates(
    dwh_code: Optional[str] = Header(None, alias="X-DWH-Code"),
):
    """
    Applique les mises a jour Builder depuis le central.

    Source :
      - MASTER_API_URL configuré → fetch HTTP /api/master/*
      - sinon → lecture base centrale locale OptiBoard_SaaS
    """
    code = _require_dwh(dwh_code)
    remote = _master_remote_enabled()

    applied = 0
    errors  = []
    source  = "remote_http" if remote else "local_central_db"

    # --- Dashboards ---
    try:
        if remote:
            central_dashes = _master_get_items("dashboards")
        else:
            central_dashes = execute_central(
                "SELECT code, nom, description, config, widgets, is_public FROM APP_Dashboards WHERE actif=1",
            )
        for d in (central_dashes or []):
            d_code = d.get("code") or d[0]
            try:
                write_client(
                    """IF EXISTS (SELECT 1 FROM APP_Dashboards WHERE code=? AND is_customized=0)
                         UPDATE APP_Dashboards SET nom=?, description=?, config=?, widgets=?, is_public=?, date_modification=GETDATE()
                         WHERE code=? AND is_customized=0
                       ELSE IF NOT EXISTS (SELECT 1 FROM APP_Dashboards WHERE code=?)
                         INSERT INTO APP_Dashboards (code, nom, description, config, widgets, is_public)
                         VALUES (?,?,?,?,?,?)""",
                    (
                        d_code, d.get("nom") or d[1], d.get("description") or d[2],
                        d.get("config") or d[3], d.get("widgets") or d[4], d.get("is_public") or d[5],
                        d_code, d_code,
                        d_code, d.get("nom") or d[1], d.get("description") or d[2],
                        d.get("config") or d[3], d.get("widgets") or d[4], d.get("is_public") or d[5],
                    ),
                    dwh_code=code,
                )
                write_client(
                    "INSERT INTO APP_Update_History (type_entite, code_entite, nom_entite, version_installee, statut) VALUES ('dashboard',?,?,1,'succes')",
                    (d_code, d.get("nom") or d[1]),
                    dwh_code=code,
                )
                applied += 1
            except Exception as e:
                errors.append({"type": "dashboard", "code": d_code, "error": str(e)})
    except Exception as e:
        logger.warning(f"pull_builder dashboards: {e}")

    # --- Menus ---
    try:
        if remote:
            central_menus = _master_get_items("menus")
        else:
            central_menus = execute_central(
                "SELECT code, nom, parent_code, ordre, page_code, icone, actif FROM APP_Menus WHERE actif=1",
            )
        for m in (central_menus or []):
            m_code = m.get("code") or m[0]
            try:
                write_client(
                    """IF NOT EXISTS (SELECT 1 FROM APP_Menus WHERE code=?)
                         INSERT INTO APP_Menus (code, nom, parent_code, ordre, page_code, icone, actif)
                         VALUES (?,?,?,?,?,?,?)""",
                    (
                        m_code,
                        m_code, m.get("nom") or m[1], m.get("parent_code") or m[2],
                        m.get("ordre") or m[3], m.get("page_code") or m[4],
                        m.get("icone") or m[5], m.get("actif") or m[6],
                    ),
                    dwh_code=code,
                )
                write_client(
                    "INSERT INTO APP_Update_History (type_entite, code_entite, nom_entite, version_installee, statut) VALUES ('menu',?,?,1,'succes')",
                    (m_code, m.get("nom") or m[1]),
                    dwh_code=code,
                )
                applied += 1
            except Exception as e:
                errors.append({"type": "menu", "code": m_code, "error": str(e)})
    except Exception as e:
        logger.warning(f"pull_builder menus: {e}")

    return {
        "success": True,
        "applied": applied,
        "errors": errors,
        "source":  source,
        "message": f"{applied} element(s) Builder mis a jour ({source})",
    }


# ============================================================
# POST /api/updates/pull/all
# Tire toutes les MAJ disponibles (ETL + Builder)
# ============================================================

@router.post("/pull/all")
async def pull_all_updates(
    dwh_code: Optional[str] = Header(None, alias="X-DWH-Code"),
):
    """Applique toutes les mises a jour disponibles (ETL + Builder)."""
    code = _require_dwh(dwh_code)

    etl_result     = await pull_etl_updates(dwh_code=code)
    builder_result = await pull_builder_updates(dwh_code=code)

    total = etl_result.get("applied", 0) + builder_result.get("applied", 0)
    errors = etl_result.get("errors", []) + builder_result.get("errors", [])

    return {
        "success": True,
        "total_applied": total,
        "etl_applied": etl_result.get("applied", 0),
        "builder_applied": builder_result.get("applied", 0),
        "errors": errors,
        "message": f"MAJ complete : {total} element(s) mis a jour",
        "applied_at": datetime.now().isoformat(),
    }


# ============================================================
# GET /api/updates/history
# Historique des MAJ appliquees chez le client
# ============================================================

@router.get("/history")
async def get_update_history(
    dwh_code: Optional[str] = Header(None, alias="X-DWH-Code"),
    type_entite: Optional[str] = None,
    limit: int = 100,
):
    """Retourne l'historique des MAJ appliquees dans la base client."""
    code = _require_dwh(dwh_code)

    try:
        sql = """
            SELECT TOP (?) id, type_entite, code_entite, nom_entite,
                   version_precedente, version_installee, statut,
                   message_erreur, date_installation
            FROM APP_Update_History
        """
        params: list = [limit]

        if type_entite:
            sql += " WHERE type_entite = ?"
            params.append(type_entite)

        sql += " ORDER BY date_installation DESC"

        rows = execute_client(sql, tuple(params), dwh_code=code)

        data = []
        for r in (rows or []):
            data.append({
                "id":                 r[0],
                "type_entite":        r[1],
                "code_entite":        r[2],
                "nom_entite":         r[3],
                "version_precedente": r[4],
                "version_installee":  r[5],
                "statut":             r[6],
                "message_erreur":     r[7],
                "date_installation":  r[8].isoformat() if r[8] else None,
            })

        return {"success": True, "data": data, "total": len(data)}

    except Exception as e:
        logger.error(f"get_update_history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
