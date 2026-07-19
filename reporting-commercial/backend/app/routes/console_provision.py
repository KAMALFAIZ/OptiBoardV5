"""
Module Console Provisioning
===========================
Endpoint appelé par la console KASOFT pour PROVISIONNER une nouvelle instance
client (DWH) à distance, sans passer par l'admin OptiBoard.

    POST /api/console/provision-instance   (header obligatoire : X-Console-Token)
    GET  /api/console/instances            (header obligatoire : X-Console-Token)

Auth : même secret partagé `CONSOLE_TOKEN` que /api/console/instance-stats
       (via console_stats._check_token). 404 si non configuré, 401 si invalide.
       La route est exemptée du plancher de session (tenant_context.EXEMPT_PREFIXES
       contient déjà "/api/console") — l'authentification se fait ICI, par token.

Le provisioning compose les deux helpers canoniques existants (aucune duplication
de la logique métier de création d'instance) :
  1. setup._create_first_local_dwh()      → APP_DWH (centrale) + admin client
     (bcrypt) + APP_UserDWH (superadmin/admin) + APP_ClientDB (routage) +
     source Sage optionnelle (APP_ETL_Agents + APP_DWH_Sources).
  2. dwh_admin._create_client_optiboard_db() → complète la base OptiBoard_<CODE>
     avec TOUTES les tables client + migration des données Master + menus par défaut.

Sécurité : le `code` est interpolé dans `CREATE DATABASE [OptiBoard_{code}]`.
Il est donc validé STRICTEMENT (^[A-Z0-9_]{1,40}$) avant tout usage — une valeur
comme `x]; DROP DATABASE` est rejetée en 400.

La déprovision (DROP des bases) n'est VOLONTAIREMENT pas exposée ici : trop
destructrice pour un appel réseau. Elle reste manuelle via l'admin OptiBoard.
"""
import asyncio
import logging
import re
import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from ..database_unified import execute_central
from .console_stats import _check_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/console", tags=["Console KASOFT"])

# Le code devient un identifiant SQL bracketé (CREATE DATABASE [OptiBoard_<CODE>]).
# On n'autorise QUE des caractères sûrs — pas d'espace, crochet, point-virgule, quote.
# Le tiret est accepté (codes console type "client-az" ; sûr dans un identifiant
# SQL bracketé et préservé par le routage sous-domaine, cf. _subdomain_dwh_code).
_CODE_RE = re.compile(r"^[A-Z0-9_-]{1,40}$")


class ProvisionRequest(BaseModel):
    """Payload de provisioning d'une instance client, émis par la console."""
    # Identité du client
    code: str
    nom: str
    raison_sociale: Optional[str] = None
    email: Optional[str] = None
    telephone: Optional[str] = None
    ville: Optional[str] = None
    pays: Optional[str] = None
    # Administrateur client (créé dans OptiBoard_<CODE>.APP_Users)
    admin_username: str
    admin_password: Optional[str] = None   # None → généré et renvoyé une seule fois
    admin_email: Optional[str] = None
    admin_nom: Optional[str] = None
    admin_prenom: Optional[str] = None
    # Serveur SQL cible (défaut : serveur central de cette installation)
    sql_server: Optional[str] = None
    sql_user: Optional[str] = None
    sql_password: Optional[str] = None
    # Source Sage optionnelle
    create_sage_source: bool = False
    sage_server: Optional[str] = None
    sage_database: Optional[str] = None
    sage_username: Optional[str] = None
    sage_password: Optional[str] = None
    sage_societe_code: Optional[str] = None
    sage_societe_nom: Optional[str] = None
    # Si le code existe déjà : refuser (défaut) ou réappliquer (upsert admin/config)
    overwrite: bool = False


class DeprovisionRequest(BaseModel):
    """Payload de déprovision d'une instance client, émis par la console."""
    code: str
    backup: bool = True     # sauvegarde .bak SQL Server AVANT le DROP (filet de sécurité)
    force: bool = False     # DROP même si la sauvegarde échoue (DANGEREUX — perte définitive)


def _normalize_code(raw: str) -> str:
    """Normalise puis valide le code DWH (fail-closed sur tout caractère non sûr)."""
    code = (raw or "").strip().upper().replace(" ", "_")
    if not _CODE_RE.match(code):
        raise HTTPException(
            status_code=400,
            detail="Code invalide : lettres, chiffres, '_' et '-' uniquement (max 40).",
        )
    return code


def _dwh_exists(code: str) -> bool:
    try:
        rows = execute_central("SELECT id FROM APP_DWH WHERE code = ?", (code,), use_cache=False)
        return bool(rows)
    except Exception as e:
        logger.warning(f"provision _dwh_exists({code}): {e}")
        return False


def _provision(req: ProvisionRequest, code: str, admin_password: str, sage_on: bool) -> dict:
    """Exécute le provisioning (bloquant) — appelé via asyncio.to_thread."""
    from ..config_multitenant import get_central_settings
    from .setup import _create_first_local_dwh
    from .dwh_admin import _create_client_optiboard_db

    central = get_central_settings()
    server = req.sql_server or central._effective_server
    user = req.sql_user or central._effective_user
    password = req.sql_password or central._effective_password
    driver = "{ODBC Driver 17 for SQL Server}"

    # 1 — DWH + admin client + UserDWH + APP_ClientDB + source Sage
    base = _create_first_local_dwh(
        code=code,
        nom=req.nom,
        server=server, user=user, password=password, driver=driver,
        admin_username=req.admin_username,
        admin_password=admin_password,
        admin_email=req.admin_email,
        admin_nom=req.admin_nom,
        admin_prenom=req.admin_prenom,
        sage_server=req.sage_server if sage_on else None,
        sage_database=req.sage_database if sage_on else None,
        sage_username=req.sage_username if sage_on else None,
        sage_password=req.sage_password if sage_on else None,
        sage_societe_code=req.sage_societe_code if sage_on else None,
        sage_societe_nom=req.sage_societe_nom if sage_on else None,
    )

    # 2 — Compléter la base client (toutes les tables + données Master + menus)
    try:
        dbres = _create_client_optiboard_db(code)
    except Exception as e:
        logger.error(f"provision _create_client_optiboard_db({code}): {e}")
        dbres = {"created": False, "error": str(e), "tables_count": 0}

    # 3 — Enrichir la ligne APP_DWH avec les métadonnées optionnelles (best-effort)
    _enrich_dwh_metadata(req, code)

    warnings = list(base.get("errors") or [])
    if dbres.get("error"):
        warnings.append(f"client-db: {dbres['error']}")

    return {
        "db_name": base.get("db_name") or f"OptiBoard_{code}",
        "db_created": bool(base.get("db_created")),
        "dwh_registered": bool(base.get("dwh_inserted")),
        "users_linked": base.get("users_linked", 0),
        "tables_count": dbres.get("tables_count", 0),
        "admin_created": bool(base.get("admin_client_created")),
        "admin_username": base.get("admin_client_username") or req.admin_username.strip().lower(),
        "sage_source_inserted": bool(base.get("sage_source_inserted")),
        "sage_societe_code": base.get("sage_societe_code"),
        "warnings": warnings,
    }


def _enrich_dwh_metadata(req: ProvisionRequest, code: str) -> None:
    """Met à jour APP_DWH avec les champs non gérés par _create_first_local_dwh."""
    fields = {
        "raison_sociale": req.raison_sociale,
        "email": req.email,
        "telephone": req.telephone,
        "ville": req.ville,
        "pays": req.pays,
    }
    sets = {k: v for k, v in fields.items() if v}
    if not sets:
        return
    try:
        from ..database_unified import central_cursor
        assignments = ", ".join(f"{k} = ?" for k in sets)
        params = list(sets.values()) + [code]
        with central_cursor() as cur:
            cur.execute(f"UPDATE APP_DWH SET {assignments} WHERE code = ?", params)
    except Exception as e:
        logger.warning(f"provision _enrich_dwh_metadata({code}): {e}")


@router.post("/provision-instance")
async def provision_instance(
    req: ProvisionRequest,
    x_console_token: Optional[str] = Header(None, alias="X-Console-Token"),
):
    """Provisionne une instance client complète depuis la console KASOFT."""
    _check_token(x_console_token)

    code = _normalize_code(req.code)

    if not (req.admin_username or "").strip():
        raise HTTPException(status_code=400, detail="admin_username requis.")

    if _dwh_exists(code) and not req.overwrite:
        raise HTTPException(
            status_code=409,
            detail=f"Instance '{code}' déjà provisionnée. Utiliser overwrite=true pour réappliquer.",
        )

    # Mot de passe admin : fourni par la console, sinon généré (renvoyé une seule fois).
    generated = not (req.admin_password or "").strip()
    admin_password = req.admin_password if not generated else secrets.token_urlsafe(9)

    sage_on = req.create_sage_source and bool(req.sage_server and req.sage_database)

    try:
        result = await asyncio.to_thread(_provision, req, code, admin_password, sage_on)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"provision_instance({code}): {e}")
        raise HTTPException(status_code=500, detail=f"Échec du provisioning: {e}")

    logger.info(
        f"[CONSOLE-PROVISION] Instance '{code}' provisionnée "
        f"(db_created={result['db_created']}, admin={result['admin_username']}, "
        f"tables={result['tables_count']}, sage={result['sage_source_inserted']})"
    )

    admin_block = {"username": result["admin_username"], "created": result["admin_created"]}
    if generated:
        # Renvoyé UNE seule fois — la console est responsable de sa transmission sécurisée.
        admin_block["password"] = admin_password
        admin_block["password_generated"] = True

    return {
        "success": True,
        "code": code,
        "db_name": result["db_name"],
        "db_created": result["db_created"],
        "dwh_registered": result["dwh_registered"],
        "tables_count": result["tables_count"],
        "users_linked": result["users_linked"],
        "admin": admin_block,
        "sage_source": (
            {"inserted": result["sage_source_inserted"], "societe_code": result["sage_societe_code"]}
            if sage_on else None
        ),
        "warnings": result["warnings"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/deprovision-instance")
async def deprovision_instance(
    req: DeprovisionRequest,
    x_console_token: Optional[str] = Header(None, alias="X-Console-Token"),
):
    """
    Déprovisionne une instance client OptiBoard depuis la console KASOFT.

    Symétrique de /provision-instance. Enchaîne (via la logique canonique de
    dwh_admin.dwh_admin_delete) :
      1. sauvegarde .bak vérifiée de chaque base SQL Server (sauf backup=false) ;
      2. DROP des bases (DWH_ + OptiBoard_) ;
      3. retrait de l'instance du registre APP_DWH + tables liées.

    Idempotent : si le code est déjà absent, renvoie success/already_absent=true
    (la console peut re-tenter sans erreur).

    Sécurité : la sauvegarde est créée AVANT tout DROP. Si elle échoue et force=false,
    la suppression est ANNULÉE côté OptiBoard (aucune donnée perdue) et l'appel renvoie
    500 — la console doit alors bloquer le retrait de sa fiche. Le code 'KA'
    (Kasoft-Démo) reste protégé (403).
    """
    _check_token(x_console_token)
    code = _normalize_code(req.code)

    if not _dwh_exists(code):
        return {
            "success": True,
            "code": code,
            "already_absent": True,
            "message": f"Instance '{code}' déjà absente d'OptiBoard — rien à supprimer.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # Réutilise la logique canonique de suppression (sauvegarde → DROP → registre).
    from .dwh_admin import dwh_admin_delete

    try:
        result = await asyncio.to_thread(
            dwh_admin_delete, code, True, req.backup, req.force
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"deprovision_instance({code}): {e}")
        raise HTTPException(status_code=500, detail=f"Échec de la déprovision: {e}")

    backup_results = result.get("backup_results") or []
    drop_results = result.get("drop_results") or []
    logger.info(
        f"[CONSOLE-DEPROVISION] Instance '{code}' déprovisionnée "
        f"(sauvegardes={sum(1 for b in backup_results if b.get('backed_up'))}, "
        f"bases droppées={sum(1 for d in drop_results if d.get('dropped'))})"
    )
    return {
        "success": True,
        "code": code,
        "message": result.get("message"),
        "backup_results": backup_results,
        "drop_results": drop_results,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


class BackupRequest(BaseModel):
    """Payload de sauvegarde à la demande d'une instance client, émis par la console."""
    code: str


@router.post("/backup-instance")
async def backup_instance(
    req: BackupRequest,
    x_console_token: Optional[str] = Header(None, alias="X-Console-Token"),
):
    """
    Sauvegarde .bak des bases SQL Server d'une instance client (DWH_ + OptiBoard_),
    SANS aucune suppression. Appelé par le bouton « Sauvegarder » de la console
    (et « Tout sauvegarder ») pour les clients produit=optiboard.

    Réutilise la logique canonique dwh_admin.dwh_admin_backup (BACKUP DATABASE vérifié
    par RESTORE VERIFYONLY, dossier serveur OptiBoard\\manual).
    """
    _check_token(x_console_token)
    code = _normalize_code(req.code)

    if not _dwh_exists(code):
        return {
            "success": True,
            "code": code,
            "already_absent": True,
            "message": f"Instance '{code}' absente d'OptiBoard — rien à sauvegarder.",
            "backup_results": [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    from .dwh_admin import dwh_admin_backup

    try:
        result = await asyncio.to_thread(dwh_admin_backup, code)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"backup_instance({code}): {e}")
        raise HTTPException(status_code=500, detail=f"Échec de la sauvegarde: {e}")

    backup_results = result.get("backup_results") or []
    logger.info(
        f"[CONSOLE-BACKUP] Instance '{code}' sauvegardée "
        f"(bases={sum(1 for b in backup_results if b.get('backed_up'))})"
    )
    if not result.get("success"):
        # Sauvegarde d'une base existante échouée → 500 pour que la console signale l'échec.
        raise HTTPException(status_code=500, detail=result.get("message") or "Sauvegarde SQL échouée.")

    return {
        "success": True,
        "code": code,
        "message": result.get("message"),
        "backup_results": backup_results,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/instances")
def list_instances(x_console_token: Optional[str] = Header(None, alias="X-Console-Token")):
    """Liste les instances client provisionnées (réconciliation côté console)."""
    _check_token(x_console_token)
    try:
        rows = execute_central(
            "SELECT d.code, d.nom, d.raison_sociale, d.actif,"
            "       COALESCE(cdb.db_name, CONCAT('OptiBoard_', d.code)) AS db_name,"
            "       d.date_creation"
            " FROM APP_DWH d"
            " LEFT JOIN APP_ClientDB cdb ON cdb.dwh_code = d.code"
            " ORDER BY d.date_creation DESC",
            use_cache=False,
        )
    except Exception as e:
        logger.error(f"list_instances: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    instances = [
        {
            "code": r.get("code"),
            "nom": r.get("nom"),
            "raisonSociale": r.get("raison_sociale"),
            "dbName": r.get("db_name"),
            "active": bool(r.get("actif")),
            "createdAt": r["date_creation"].isoformat() if r.get("date_creation") else None,
        }
        for r in (rows or [])
    ]
    return {"instances": instances, "count": len(instances)}
