"""Routes pour la gestion des menus et droits d'acces"""
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from ..database_unified import (
    execute_app as execute_query,
    app_cursor as get_db_cursor,
    execute_central,
    central_cursor as get_central_cursor,
    execute_client,
    client_manager,
    current_dwh_code,
)
import json
import logging
import re
import unicodedata
from datetime import datetime

logger = logging.getLogger(__name__)

# Mapping type menu → type rapport dans APP_Role_Reports
_MENU_TO_REPORT_TYPE = {
    'gridview':  'gridview',
    'dashboard': 'dashboard',
    'pivot':     'pivot',
    'pivot-v2':  'pivot',
}
_STRUCTURAL_TYPES = {'folder', 'url', 'page', 'separator', None, ''}

# Table portant la cible, par type de menu (pour detecter les menus orphelins)
_MENU_TARGET_TABLE = {
    'pivot':     'APP_Pivots',
    'pivot-v2':  'APP_Pivots_V2',
    'gridview':  'APP_GridViews',
    'dashboard': 'APP_Dashboards',
}

router = APIRouter(prefix="/api/menus", tags=["menus"])


# =====================================================
# SCHEMA APP_Menus — normalisation idempotente
# =====================================================
# Le schema d'APP_Menus differe selon le script qui a cree la base
# (setup.py, dwh_admin.py, 002_client_schema.sql, init_all_tables.sql) :
# certaines bases n'ont ni `is_custom`, ni `parent_id`, ni `code`.
# Les INSERT/UPDATE etaient donc rejetes ("Invalid column name") en silence.
# On aligne le schema une fois par base, et on construit malgre tout les
# requetes a partir des colonnes REELLEMENT presentes (cas ou l'ALTER echoue
# faute de droits).

_MENU_COLUMNS_DDL = [
    ("code",          "VARCHAR(100) NULL"),
    ("parent_id",     "INT NULL"),
    ("parent_code",   "VARCHAR(100) NULL"),
    ("icon",          "VARCHAR(50) NULL"),
    ("url",           "VARCHAR(500) NULL"),
    ("type",          "VARCHAR(50) NULL"),
    ("target_id",     "INT NULL"),
    ("ordre",         "INT NULL"),
    ("actif",         "BIT NOT NULL DEFAULT 1"),
    ("is_custom",     "BIT NOT NULL DEFAULT 0"),
    ("is_customized", "BIT NOT NULL DEFAULT 0"),
]

_schema_checked: set = set()


def _db_name(cursor) -> str:
    try:
        cursor.execute("SELECT DB_NAME()")
        row = cursor.fetchone()
        return row[0] if row else "?"
    except Exception:
        return "?"


def _menu_columns(cursor) -> set:
    """Colonnes reellement presentes dans APP_Menus (base courante)."""
    cursor.execute(
        "SELECT LOWER(COLUMN_NAME) FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_NAME = 'APP_Menus'"
    )
    return {r[0] for r in cursor.fetchall()}


def _ensure_menu_schema(cursor) -> set:
    """Ajoute les colonnes manquantes d'APP_Menus. Retourne les colonnes finales."""
    db = _db_name(cursor)
    cols = _menu_columns(cursor)
    if db in _schema_checked:
        return cols

    for name, ddl in _MENU_COLUMNS_DDL:
        if name in cols:
            continue
        try:
            cursor.execute(f"ALTER TABLE APP_Menus ADD {name} {ddl}")
            cols.add(name)
            logger.info(f"[MENUS] {db}.APP_Menus : colonne '{name}' ajoutee")
        except Exception as e:
            logger.warning(f"[MENUS] {db}.APP_Menus : ajout '{name}' impossible ({e})")

    _schema_checked.add(db)
    return cols


def normalize_menu_code(raw: str) -> str:
    """Code de menu canonique : sans accent, minuscule, [a-z0-9-]."""
    if not raw:
        return ""
    txt = unicodedata.normalize("NFD", str(raw))
    txt = "".join(c for c in txt if unicodedata.category(c) != "Mn")
    txt = txt.lower()
    txt = re.sub(r"[^a-z0-9]+", "-", txt)
    return txt.strip("-")[:100]


# Schemas Pydantic
class MenuCreate(BaseModel):
    parent_id: Optional[int] = None
    nom: str
    code: str
    icon: Optional[str] = None
    type: str = "folder"  # folder, pivot, gridview, dashboard, page
    target_id: Optional[int] = None
    url: Optional[str] = None
    ordre: int = 0
    is_active: bool = True
    # Donne l'acces au rapport cible a tous les roles non-admin + aux
    # utilisateurs "legacy" (sans role). Sans cela, un menu fraichement
    # attache n'est visible que des administrateurs.
    grant_all_roles: bool = False


class MenuUpdate(BaseModel):
    parent_id: Optional[int] = None
    nom: Optional[str] = None
    code: Optional[str] = None
    icon: Optional[str] = None
    type: Optional[str] = None
    target_id: Optional[int] = None
    url: Optional[str] = None
    ordre: Optional[int] = None
    is_active: Optional[bool] = None


class UserMenuAccess(BaseModel):
    user_id: int
    menu_id: int
    can_view: bool = True
    can_export: bool = False


class BulkUserMenuAccess(BaseModel):
    user_id: int
    menu_ids: List[int]
    can_export: bool = False


class ReportAccessGrant(BaseModel):
    report_type: str                      # gridview | pivot | dashboard
    report_id: int
    role_ids: Optional[List[int]] = None  # None + all_roles=True → tous les roles
    all_roles: bool = False
    can_export: bool = False
    menu_id: Optional[int] = None         # pour les utilisateurs "legacy" (APP_UserMenus)


# =====================================================
# DROITS SUR UN RAPPORT (APP_Role_Reports / APP_UserMenus)
# =====================================================

def _client_ctx(dwh_code: Optional[str] = None) -> Optional[str]:
    """Code DWH courant si une base client existe reellement."""
    code = dwh_code or current_dwh_code.get()
    if code and client_manager.has_client_db(code):
        return code
    return None


def grant_report_access(
    report_type: str,
    report_id: int,
    role_ids: Optional[List[int]] = None,
    all_roles: bool = False,
    can_export: bool = False,
    menu_id: Optional[int] = None,
    dwh_code: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Rend un rapport visible hors administrateurs.

    - Mode roles    : upsert dans APP_Role_Reports (can_view=1).
    - Mode 'legacy' : APP_UserMenus pour les utilisateurs sans aucun role.
    Best effort : une base sans table de roles ne fait pas echouer l'appel.
    """
    result = {"roles_granted": 0, "users_granted": 0}
    rtype = _MENU_TO_REPORT_TYPE.get(report_type, report_type)
    if not rtype or not report_id:
        return result

    with get_db_cursor() as cursor:
        # ── 1. APP_Role_Reports ──────────────────────────────────────────
        try:
            if all_roles or not role_ids:
                cursor.execute(
                    "SELECT id FROM APP_Roles WHERE actif = 1 AND ISNULL(is_admin, 0) = 0"
                )
                targets = [r[0] for r in cursor.fetchall()]
            else:
                targets = list(role_ids)

            for rid in targets:
                cursor.execute(
                    """IF NOT EXISTS (SELECT 1 FROM APP_Role_Reports
                                      WHERE role_id = ? AND report_type = ? AND report_id = ?)
                           INSERT INTO APP_Role_Reports (role_id, report_type, report_id, can_view, can_export)
                           VALUES (?, ?, ?, 1, ?)
                       ELSE
                           UPDATE APP_Role_Reports SET can_view = 1,
                                  can_export = CASE WHEN ? = 1 THEN 1 ELSE can_export END
                           WHERE role_id = ? AND report_type = ? AND report_id = ?""",
                    (rid, rtype, report_id,
                     rid, rtype, report_id, 1 if can_export else 0,
                     1 if can_export else 0, rid, rtype, report_id)
                )
                result["roles_granted"] += 1
        except Exception as e:
            logger.warning(f"[MENUS] grant_report_access roles: {e}")

        # ── 2. APP_UserMenus (utilisateurs sans role = ancien systeme) ───
        if menu_id:
            try:
                cursor.execute(
                    """SELECT u.id FROM APP_Users u
                       WHERE NOT EXISTS (SELECT 1 FROM APP_User_Roles ur WHERE ur.user_id = u.id)"""
                )
                legacy_users = [r[0] for r in cursor.fetchall()]
            except Exception:
                # Pas de table de roles → tous les utilisateurs sont "legacy"
                try:
                    cursor.execute("SELECT id FROM APP_Users")
                    legacy_users = [r[0] for r in cursor.fetchall()]
                except Exception as e:
                    logger.warning(f"[MENUS] grant_report_access users: {e}")
                    legacy_users = []

            for uid in legacy_users:
                try:
                    cursor.execute(
                        """IF NOT EXISTS (SELECT 1 FROM APP_UserMenus WHERE user_id = ? AND menu_id = ?)
                               INSERT INTO APP_UserMenus (user_id, menu_id, can_view, can_export)
                               VALUES (?, ?, 1, ?)
                           ELSE
                               UPDATE APP_UserMenus SET can_view = 1 WHERE user_id = ? AND menu_id = ?""",
                        (uid, menu_id, uid, menu_id, 1 if can_export else 0, uid, menu_id)
                    )
                    result["users_granted"] += 1
                except Exception as e:
                    logger.warning(f"[MENUS] grant_report_access user {uid}: {e}")

    return result


def _existing_target_ids(menu_type: str) -> Optional[set]:
    """
    Ids valides pour un type de menu, base client ET base centrale reunies.

    ATTENTION : les ids de rapports DIFFERENT entre la centrale et la base
    client (re-insertion avec IDENTITY propre), et `_pv_read` resout un id
    central vers la ligne client par code/nom. Un menu dont le target_id
    n'existe pas cote client n'est donc PAS orphelin s'il existe cote central.
    Retourne None si l'inventaire n'a pas pu etre etabli (→ ne rien nettoyer).
    """
    table = _MENU_TARGET_TABLE.get(menu_type)
    if not table:
        return None

    ids, seen_any = set(), False
    for reader in (lambda q: execute_query(q, use_cache=False),
                   lambda q: execute_central(q, use_cache=False)):
        try:
            rows = reader(f"SELECT id FROM {table}")
            ids.update(r['id'] for r in (rows or []))
            seen_any = True
        except Exception as e:
            logger.debug(f"[MENUS] _existing_target_ids({menu_type}): {e}")

    return ids if seen_any else None


def cleanup_menus_for_report(menu_type: str, report_id: int) -> Dict[str, Any]:
    """
    Nettoie les menus qui pointaient vers un rapport supprime.

    `menu_type` est le type de MENU exact ('pivot-v2', 'gridview', 'dashboard',
    'pivot') : les ids se recoupent d'une table de rapports a l'autre, on ne
    doit donc jamais elargir aux types voisins.

    - menu sans enfant  → supprime (+ droits APP_UserMenus)
    - menu avec enfants → conserve, transforme en dossier (target_id = NULL)
    Appele par les routes de suppression de pivot / gridview / dashboard.
    """
    stats = {"deleted": 0, "converted": 0, "skipped": False}
    if not report_id or not menu_type:
        return stats

    # Garde-fou : ne toucher aux menus que si la cible a REELLEMENT disparu
    # des deux bases. Une suppression qui n'a rien supprime (id central
    # applique a la base client) ne doit pas emporter les menus.
    existing = _existing_target_ids(menu_type)
    if existing is None or report_id in existing:
        stats["skipped"] = True
        return stats

    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT id FROM APP_Menus WHERE target_id = ? AND type = ?",
                (report_id, menu_type)
            )
            menu_ids = [r[0] for r in cursor.fetchall()]

            for mid in menu_ids:
                cursor.execute("SELECT COUNT(*) FROM APP_Menus WHERE parent_id = ?", (mid,))
                has_children = (cursor.fetchone()[0] or 0) > 0
                if has_children:
                    cursor.execute(
                        "UPDATE APP_Menus SET target_id = NULL, type = 'folder' WHERE id = ?",
                        (mid,)
                    )
                    stats["converted"] += 1
                else:
                    try:
                        cursor.execute("DELETE FROM APP_UserMenus WHERE menu_id = ?", (mid,))
                    except Exception:
                        pass
                    cursor.execute("DELETE FROM APP_Menus WHERE id = ?", (mid,))
                    stats["deleted"] += 1

        if stats["deleted"] or stats["converted"]:
            logger.info(
                f"[MENUS] Nettoyage {menu_type}#{report_id} : "
                f"{stats['deleted']} menu(s) supprime(s), {stats['converted']} converti(s) en dossier"
            )
    except Exception as e:
        logger.error(f"[MENUS] cleanup_menus_for_report({menu_type},{report_id}): {e}")

    return stats


# ==================== MENUS CRUD ====================

@router.get("/")
def get_all_menus():
    """Recupere tous les menus en structure arborescente"""
    try:
        results = execute_query(
            """SELECT m.*, m.actif as is_active,
                      CASE
                        WHEN m.type = 'pivot' THEN (SELECT nom FROM APP_Pivots WHERE id = m.target_id)
                        WHEN m.type = 'pivot-v2' THEN (SELECT nom FROM APP_Pivots_V2 WHERE id = m.target_id)
                        WHEN m.type = 'gridview' THEN (SELECT nom FROM APP_GridViews WHERE id = m.target_id)
                        WHEN m.type = 'dashboard' THEN (SELECT nom FROM APP_Dashboards WHERE id = m.target_id)
                        ELSE NULL
                      END as target_name
               FROM APP_Menus m
               ORDER BY m.ordre, m.nom""",
            use_cache=False
        )

        # Construire l'arbre
        menu_map = {m['id']: {**m, 'children': []} for m in results}
        root_menus = []

        for menu in results:
            menu_item = menu_map[menu['id']]
            if menu['parent_id'] is None:
                root_menus.append(menu_item)
            else:
                parent = menu_map.get(menu['parent_id'])
                if parent:
                    parent['children'].append(menu_item)

        return {"success": True, "data": root_menus}
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}


_FLAT_QUERY = """SELECT m.*, m.actif as is_active,
                      p.nom as parent_name,
                      CASE
                        WHEN m.type = 'pivot' THEN (SELECT nom FROM APP_Pivots WHERE id = m.target_id)
                        WHEN m.type = 'pivot-v2' THEN (SELECT nom FROM APP_Pivots_V2 WHERE id = m.target_id)
                        WHEN m.type = 'gridview' THEN (SELECT nom FROM APP_GridViews WHERE id = m.target_id)
                        WHEN m.type = 'dashboard' THEN (SELECT nom FROM APP_Dashboards WHERE id = m.target_id)
                        ELSE NULL
                      END as target_name
               FROM APP_Menus m
               LEFT JOIN APP_Menus p ON m.parent_id = p.id
               ORDER BY m.ordre, m.nom"""


@router.get("/flat")
def get_menus_flat(include_central: bool = False):
    """
    Recupere tous les menus en liste plate.

    include_central=1 ajoute les menus de la base CENTRALE non redefinis
    cote client (marques source='central', editable=False). Le menu reellement
    affiche a l'utilisateur (/menus/user/{id}) fusionne les deux bases : sans
    cette option, un rapport deja attache via un menu central apparait comme
    "non attache" et l'utilisateur cree un doublon.
    """
    try:
        results = execute_query(_FLAT_QUERY, use_cache=False)
        for m in results:
            m['source'] = 'client'
            m['editable'] = True
            m['uid'] = f"client:{m.get('id')}"

        # Sans base client, execute_app a DEJA lu la centrale → ne pas doubler
        if include_central and _client_ctx():
            client_codes = {m.get('code') for m in results if m.get('code')}
            try:
                central_rows = execute_central(_FLAT_QUERY, use_cache=False)
            except Exception as e:
                logger.warning(f"[MENUS] /flat include_central: {e}")
                central_rows = []
            for m in central_rows:
                if m.get('code') and m.get('code') in client_codes:
                    continue  # redefini cote client → deja dans la liste
                m = dict(m)
                m['source'] = 'central'
                m['editable'] = False
                m['uid'] = f"central:{m.get('id')}"
                results.append(m)

        return {"success": True, "data": results}
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}


@router.get("/user/{user_id}")
def get_user_menus(user_id: int, x_dwh_code: Optional[str] = Header(None)):
    """Recupere les menus accessibles par un utilisateur (respecte les roles APP_User_Roles)"""
    try:
        # ── 1. Determiner si l'utilisateur est admin ─────────────────────────
        # IMPORTANT : interroger la base CLIENT en priorité.
        # La base centrale peut avoir un user avec le même id mais un rôle différent.
        user = []

        # 1a. Base CLIENT (role_dwh) — prioritaire si DWH connu
        if x_dwh_code:
            try:
                user = execute_client(
                    "SELECT role_dwh as role FROM APP_Users WHERE id = ?",
                    (user_id,), dwh_code=x_dwh_code, use_cache=False
                )
            except Exception:
                pass

        # 1b. Fallback : base centrale (role_global) — pour superadmin sans base client
        if not user:
            try:
                user = execute_central(
                    "SELECT role_global as role FROM APP_Users WHERE id = ?",
                    (user_id,), use_cache=False
                )
            except Exception:
                pass

        # 1c. Dernier fallback : execute_app (central ou client selon contexte)
        if not user:
            try:
                user = execute_query(
                    "SELECT role_dwh as role FROM APP_Users WHERE id = ?",
                    (user_id,), use_cache=False
                )
            except Exception:
                pass

        if not user:
            raise HTTPException(status_code=404, detail="Utilisateur non trouve")

        is_admin = user[0].get('role', '') in ('admin', 'superadmin', 'admin_client')

        # ── 2. Verifier les roles specifiques (APP_User_Roles) ───────────────
        # allowed_reports = None  →  pas de roles specifiques (fallback APP_UserMenus)
        # allowed_reports = {}    →  roles presents, dict vide = aucun acces
        # allowed_reports = {'gridview': {1,2}, 'pivot': {3}} = acces restreint
        allowed_reports = None   # None = non initialise

        if not is_admin:
            try:
                # APP_User_Roles et APP_Role_Reports sont dans la base CLIENT
                role_rows = execute_client(
                    """SELECT r.id, r.is_admin
                       FROM APP_User_Roles ur
                       JOIN APP_Roles r ON r.id = ur.role_id
                       WHERE ur.user_id = ? AND r.actif = 1""",
                    (user_id,), dwh_code=x_dwh_code, use_cache=False
                )
                if role_rows:
                    # Si l'un des roles est admin → acces total
                    if any(bool(r['is_admin']) for r in role_rows):
                        is_admin = True
                    else:
                        # Construire la liste des rapports autorises (can_view=1)
                        role_ids = [r['id'] for r in role_rows]
                        ph = ','.join('?' * len(role_ids))
                        report_rows = execute_client(
                            f"""SELECT report_type, report_id,
                                       MAX(CAST(can_view AS INT)) AS can_view
                                FROM APP_Role_Reports
                                WHERE role_id IN ({ph})
                                GROUP BY report_type, report_id""",
                            tuple(role_ids), dwh_code=x_dwh_code, use_cache=False
                        )
                        allowed_reports = {}
                        for row in (report_rows or []):
                            if bool(row['can_view']):
                                rtype = row['report_type']
                                if rtype not in allowed_reports:
                                    allowed_reports[rtype] = set()
                                allowed_reports[rtype].add(row['report_id'])
            except Exception as role_err:
                logger.error(f"[MENUS] Erreur check roles user_id={user_id} dwh={x_dwh_code}: {role_err}", exc_info=True)
                # Si APP_User_Roles absent → fallback normal

        # ── 3. Requete menus selon le profil ────────────────────────────────
        TARGET_NAME_SQL = """CASE
            WHEN m.type = 'pivot'     THEN (SELECT nom FROM APP_Pivots    WHERE id = m.target_id)
            WHEN m.type = 'pivot-v2'  THEN (SELECT nom FROM APP_Pivots_V2 WHERE id = m.target_id)
            WHEN m.type = 'gridview'  THEN (SELECT nom FROM APP_GridViews WHERE id = m.target_id)
            WHEN m.type = 'dashboard' THEN (SELECT nom FROM APP_Dashboards WHERE id = m.target_id)
            ELSE NULL
        END as target_name"""

        def _merge_menus(central_rows, client_rows):
            """
            Merge central + client menus.
            - Le client remplace le central si même code ou même id.
            - Les menus centraux non présents en client sont ajoutés.
              Si le parent central est overridé côté client (même code), on tente
              de remapper parent_id — SAUF si le parent client a déjà un enfant
              de même (nom, type), pour éviter les doublons.
            """
            client_by_code = {m['code']: m for m in client_rows if m.get('code')}
            client_ids     = {m['id'] for m in client_rows}
            client_codes   = set(client_by_code.keys())

            # Table central id → code (pour remonter le parent)
            central_id_to_code = {m['id']: m.get('code') for m in central_rows}

            # Index des enfants côté client : {parent_id: set((nom, type))}
            # Permet de détecter les doublons après remap du parent
            client_children = {}
            for m in client_rows:
                pid = m.get('parent_id')
                if pid is not None:
                    key = (m.get('nom', '').strip(), m.get('type', ''))
                    client_children.setdefault(pid, set()).add(key)

            extra_central = []
            for m in central_rows:
                m_code = m.get('code')
                m_id   = m.get('id')
                if m_code in client_codes or m_id in client_ids:
                    continue  # déjà présent côté client

                m = dict(m)  # copie pour ne pas muter l'original
                parent_id = m.get('parent_id')
                if parent_id is not None and parent_id not in client_ids:
                    # Tenter de remapper vers l'équivalent client via code du parent
                    parent_code = (m.get('parent_code')
                                   or central_id_to_code.get(parent_id))
                    if parent_code and parent_code in client_by_code:
                        new_parent_id = client_by_code[parent_code]['id']
                        # Vérifier doublon : le parent client a-t-il déjà un enfant identique ?
                        key = (m.get('nom', '').strip(), m.get('type', ''))
                        if key in client_children.get(new_parent_id, set()):
                            continue  # doublon → ignorer ce menu central
                        m['parent_id']   = new_parent_id
                        m['parent_code'] = parent_code

                extra_central.append(m)

            return client_rows + extra_central

        def _read_menus(query, params=(), dwh_code=None):
            """Lit les menus depuis client ET central, puis merge."""
            central_rows = execute_central(query, params or None, use_cache=False)
            if dwh_code and client_manager.has_client_db(dwh_code):
                try:
                    client_rows = execute_client(query, params or None,
                                                 dwh_code=dwh_code, use_cache=False)
                    return _merge_menus(central_rows, client_rows)
                except Exception as e:
                    logger.error(f"[MENUS] _read_menus error dwh={dwh_code}: {e}", exc_info=True)
            return central_rows

        try:
            if is_admin:
                # Admin → tout (menus inactifs compris)
                results = _read_menus(
                    f"""SELECT m.*, m.actif as is_active, 1 as can_view, 1 as can_export,
                               {TARGET_NAME_SQL}
                        FROM APP_Menus m
                        ORDER BY m.ordre, m.nom""",
                    dwh_code=x_dwh_code
                )

            elif allowed_reports is not None:
                # Roles specifiques → charger tous les menus actifs, filtrer en Python
                all_menus = _read_menus(
                    f"""SELECT m.*, m.actif as is_active, 1 as can_view, 1 as can_export,
                               {TARGET_NAME_SQL}
                        FROM APP_Menus m
                        WHERE m.actif = 1
                        ORDER BY m.ordre, m.nom""",
                    dwh_code=x_dwh_code
                )
                results = []
                for m in (all_menus or []):
                    mtype = m.get('type') or ''
                    if mtype in _STRUCTURAL_TYPES:
                        results.append(m)   # dossiers / urls toujours inclus (elagages apres)
                        continue
                    report_type = _MENU_TO_REPORT_TYPE.get(mtype)
                    if report_type and m.get('target_id') in (allowed_reports.get(report_type) or set()):
                        results.append(m)

            else:
                # Pas de roles specifiques → acces via APP_UserMenus (ancien systeme)
                # Pour ce cas, on lit d'abord depuis execute_app (comportement original)
                # puis on complète avec les menus centraux actifs non présents en client
                client_um = execute_query(
                    f"""SELECT m.*, m.actif as is_active, um.can_view, um.can_export,
                               {TARGET_NAME_SQL}
                        FROM APP_Menus m
                        INNER JOIN APP_UserMenus um ON m.id = um.menu_id
                        WHERE um.user_id = ? AND um.can_view = 1 AND m.actif = 1
                        ORDER BY m.ordre, m.nom""",
                    (user_id,), dwh_code=x_dwh_code, use_cache=False
                )
                central_um = execute_central(
                    f"""SELECT m.*, m.actif as is_active, 1 as can_view, 1 as can_export,
                               {TARGET_NAME_SQL}
                        FROM APP_Menus m
                        WHERE m.actif = 1
                        ORDER BY m.ordre, m.nom""",
                    use_cache=False
                )
                results = _merge_menus(central_um, client_um or [])
        except Exception:
            results = []

        # ── 4. Construire l'arbre ────────────────────────────────────────────
        menu_map = {m['id']: {**m, 'children': []} for m in results}
        # Index par code pour retrouver un parent via parent_code
        # (menus centraux peuvent avoir parent_id différent du client)
        code_map = {m['code']: menu_map[m['id']] for m in results if m.get('code')}
        root_menus = []
        for menu in results:
            menu_item = menu_map[menu['id']]
            if menu.get('parent_id') is None and not menu.get('parent_code'):
                root_menus.append(menu_item)
            else:
                # Chercher parent par parent_id d'abord, puis par parent_code (cross-DB)
                parent = menu_map.get(menu.get('parent_id'))
                if not parent and menu.get('parent_code'):
                    parent = code_map.get(menu.get('parent_code'))
                if parent:
                    parent['children'].append(menu_item)
                elif menu.get('parent_id') is None:
                    root_menus.append(menu_item)

        # ── 5. Elaguer les dossiers vides (mode roles specifiques uniquement) ─
        if allowed_reports is not None and not is_admin:
            def prune(menus):
                out = []
                for m in menus:
                    if (m.get('type') or '') in ('folder', ''):
                        m['children'] = prune(m['children'])
                        if m['children']:
                            out.append(m)
                    else:
                        out.append(m)
                return out
            root_menus = prune(root_menus)

        return {"success": True, "data": root_menus, "is_admin": is_admin}
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}


@router.post("/")
def create_menu(menu: MenuCreate):
    """Cree un nouveau menu (cote client : is_custom=1, is_customized=1)"""
    try:
        code = normalize_menu_code(menu.code)
        if not code:
            raise HTTPException(status_code=400, detail="Code de menu invalide ou vide")
        nom = (menu.nom or "").strip()
        if not nom:
            raise HTTPException(status_code=400, detail="Le nom du menu est obligatoire")

        with get_db_cursor() as cursor:
            cols = _ensure_menu_schema(cursor)

            # ── Unicite du code ──────────────────────────────────────────
            # `code` est UNIQUE sur certains schemas : un doublon faisait
            # echouer l'INSERT en silence. Ailleurs il creait un doublon qui
            # masquait le menu central de meme code lors du merge.
            if "code" in cols:
                cursor.execute(
                    "SELECT TOP 1 id, nom, type, target_id FROM APP_Menus WHERE code = ?",
                    (code,)
                )
                clash = cursor.fetchone()
                if clash:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Le code '{code}' est deja utilise par le menu \"{clash[1]}\". "
                               f"Choisissez un autre code."
                    )

            # ── Ordre : derniere position dans la fratrie ────────────────
            ordre = menu.ordre
            if "ordre" in cols and not ordre:
                if menu.parent_id:
                    cursor.execute(
                        "SELECT ISNULL(MAX(ordre), 0) + 1 FROM APP_Menus WHERE parent_id = ?",
                        (menu.parent_id,)
                    )
                else:
                    cursor.execute(
                        "SELECT ISNULL(MAX(ordre), 0) + 1 FROM APP_Menus WHERE parent_id IS NULL"
                    )
                row = cursor.fetchone()
                ordre = row[0] if row else 0

            # ── INSERT construit sur les colonnes REELLES ───────────────
            values = {
                "nom":           nom,
                "code":          code,
                "icon":          menu.icon,
                "type":          menu.type,
                "target_id":     menu.target_id,
                "url":           menu.url,
                "parent_id":     menu.parent_id,
                "ordre":         ordre,
                "actif":         menu.is_active,
                "is_custom":     1,
                "is_customized": 1,
            }
            usable = {k: v for k, v in values.items() if k in cols}
            if "nom" not in usable:
                raise HTTPException(status_code=500,
                                    detail="Table APP_Menus incompatible (colonne 'nom' absente)")

            names = ", ".join(usable.keys())
            marks = ", ".join("?" * len(usable))
            cursor.execute(
                f"INSERT INTO APP_Menus ({names}) VALUES ({marks})",
                tuple(usable.values())
            )

            cursor.execute("SELECT @@IDENTITY AS id")
            new_id = cursor.fetchone()[0]
            new_id = int(new_id) if new_id is not None else None

            ignored = [k for k in values if k not in cols]

        # ── Droits : sans cela le menu n'est visible que des admins ─────
        access = None
        report_type = _MENU_TO_REPORT_TYPE.get(menu.type)
        if menu.grant_all_roles and report_type and menu.target_id:
            access = grant_report_access(
                report_type, menu.target_id, all_roles=True, menu_id=new_id
            )

        return {
            "success": True,
            "id": new_id,
            "code": code,
            "ignored_columns": ignored,
            "access": access,
            "message": "Menu cree avec succes",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[MENUS] create_menu: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@router.put("/{menu_id}")
def update_menu(menu_id: int, menu: MenuUpdate):
    """
    Met a jour un menu.

    Seuls les champs REELLEMENT transmis sont appliques (model_fields_set) :
    `parent_id: null` remonte donc le menu a la racine, et `target_id: null`
    le detache — ce qui etait impossible auparavant (tout None etait ignore).
    """
    try:
        sent = menu.model_dump(exclude_unset=True)
        if not sent:
            return {"success": False, "error": "Aucune modification"}

        # nom du champ payload → colonne SQL
        field_to_col = {
            "parent_id": "parent_id", "nom": "nom", "code": "code", "icon": "icon",
            "type": "type", "target_id": "target_id", "url": "url",
            "ordre": "ordre", "is_active": "actif",
        }

        with get_db_cursor() as cursor:
            cols = _ensure_menu_schema(cursor)

            updates, params = [], []
            for field, value in sent.items():
                col = field_to_col.get(field)
                if not col or col not in cols:
                    continue
                if field == "code":
                    value = normalize_menu_code(value) or None
                    if value:
                        cursor.execute(
                            "SELECT TOP 1 nom FROM APP_Menus WHERE code = ? AND id <> ?",
                            (value, menu_id)
                        )
                        clash = cursor.fetchone()
                        if clash:
                            raise HTTPException(
                                status_code=409,
                                detail=f"Le code '{value}' est deja utilise par le menu \"{clash[0]}\"."
                            )
                elif field in ("parent_id", "target_id") and value is not None:
                    # 0 a toujours servi de sentinelle "aucun"
                    value = value if value > 0 else None
                if field == "parent_id" and value == menu_id:
                    raise HTTPException(status_code=400,
                                        detail="Un menu ne peut pas etre son propre parent")
                updates.append(f"{col} = ?")
                params.append(value)

            if not updates:
                return {"success": False, "error": "Aucune modification applicable"}

            # Un menu modifie cote client ne doit plus etre ecrase par le master
            if "is_customized" in cols:
                updates.append("is_customized = 1")

            params.append(menu_id)
            cursor.execute(
                f"UPDATE APP_Menus SET {', '.join(updates)} WHERE id = ?", params
            )
            affected = cursor.rowcount

        if affected == 0:
            raise HTTPException(status_code=404, detail=f"Menu {menu_id} introuvable")

        return {"success": True, "message": "Menu mis a jour"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[MENUS] update_menu({menu_id}): {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@router.delete("/all-reports")
def delete_all_reports():
    """Supprime tous les rapports (GridViews, Pivots V2, Dashboards, Spreadsheets) de la base centrale"""
    try:
        counts = {}
        with get_central_cursor() as cursor:
            for table in ["APP_GridViews", "APP_Pivots_V2", "APP_Dashboards", "APP_Spreadsheets"]:
                cursor.execute(f"SELECT COUNT(*) AS cnt FROM {table}")
                row = cursor.fetchone()
                counts[table] = row[0] if row else 0
            for table in ["APP_GridViews", "APP_Pivots_V2", "APP_Dashboards", "APP_Spreadsheets"]:
                cursor.execute(f"DELETE FROM {table}")
        return {
            "success": True,
            "deleted": counts,
            "message": f"Rapports supprimés : {sum(counts.values())} au total"
        }
    except Exception as e:
        logger.error(f"Erreur delete_all_reports: {e}")
        return {"success": False, "error": str(e)}


@router.delete("/{menu_id}")
def delete_menu(menu_id: int):
    """Supprime un menu"""
    try:
        # Verifier s'il y a des enfants
        children_check = execute_query(
            "SELECT COUNT(*) as cnt FROM APP_Menus WHERE parent_id = ?",
            (menu_id,),
            use_cache=False
        )
        if children_check and children_check[0]['cnt'] > 0:
            return {"success": False, "error": "Impossible de supprimer: ce menu a des sous-menus"}

        with get_db_cursor() as cursor:
            # Supprimer les droits associes
            cursor.execute("DELETE FROM APP_UserMenus WHERE menu_id = ?", (menu_id,))

            # Supprimer le menu
            cursor.execute("DELETE FROM APP_Menus WHERE id = ?", (menu_id,))
            affected = cursor.rowcount

        if affected == 0:
            return {"success": False, "error": f"Menu {menu_id} introuvable"}

        return {"success": True, "message": "Menu supprime"}
    except Exception as e:
        logger.error(f"[MENUS] delete_menu({menu_id}): {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@router.post("/{menu_id}/detach")
def detach_menu(menu_id: int):
    """
    Detache un rapport de son menu SANS perdre l'entree de menu quand elle
    porte des sous-menus.

    - menu avec sous-menus → conserve, converti en dossier (target_id = NULL)
    - menu feuille         → supprime avec ses droits APP_UserMenus
    """
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT nom, type, target_id FROM APP_Menus WHERE id = ?", (menu_id,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail=f"Menu {menu_id} introuvable")
            nom = row[0]

            cursor.execute("SELECT COUNT(*) FROM APP_Menus WHERE parent_id = ?", (menu_id,))
            has_children = (cursor.fetchone()[0] or 0) > 0

            if has_children:
                cursor.execute(
                    "UPDATE APP_Menus SET target_id = NULL, type = 'folder' WHERE id = ?",
                    (menu_id,)
                )
                return {
                    "success": True, "mode": "converted",
                    "message": f"\"{nom}\" contient des sous-menus : conserve comme dossier, rapport detache",
                }

            try:
                cursor.execute("DELETE FROM APP_UserMenus WHERE menu_id = ?", (menu_id,))
            except Exception:
                pass
            cursor.execute("DELETE FROM APP_Menus WHERE id = ?", (menu_id,))
            return {
                "success": True, "mode": "deleted",
                "message": f"\"{nom}\" a ete retire du menu",
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[MENUS] detach_menu({menu_id}): {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# ==================== MENUS ORPHELINS ====================

@router.get("/orphans")
def list_orphan_menus():
    """
    Menus pointant vers un rapport qui n'existe plus (supprime sans nettoyage).
    Au clic, ces entrees ouvrent un ecran vide.

    Un menu dont la cible existe cote CENTRAL mais pas cote client n'est pas
    orphelin : les ids different d'une base a l'autre et sont resolus par
    code/nom a la lecture.
    """
    try:
        orphans = []
        for mtype in _MENU_TARGET_TABLE:
            existing = _existing_target_ids(mtype)
            if existing is None:
                continue  # inventaire indisponible → on ne conclut rien
            try:
                rows = execute_query(
                    """SELECT m.id, m.nom, m.code, m.type, m.target_id, m.actif as is_active
                       FROM APP_Menus m
                       WHERE m.type = ? AND m.target_id IS NOT NULL""",
                    (mtype,), use_cache=False
                )
            except Exception as e:
                logger.warning(f"[MENUS] orphans {mtype}: {e}")
                continue
            orphans.extend(r for r in (rows or []) if r['target_id'] not in existing)
        return {"success": True, "data": orphans, "count": len(orphans)}
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}


@router.post("/orphans/cleanup")
def cleanup_orphan_menus():
    """Supprime (ou convertit en dossier) tous les menus orphelins."""
    try:
        listing = list_orphan_menus()
        if not listing.get("success"):
            return listing

        stats = {"deleted": 0, "converted": 0, "menus": []}
        with get_db_cursor() as cursor:
            for m in listing.get("data", []):
                mid = m["id"]
                cursor.execute("SELECT COUNT(*) FROM APP_Menus WHERE parent_id = ?", (mid,))
                if (cursor.fetchone()[0] or 0) > 0:
                    cursor.execute(
                        "UPDATE APP_Menus SET target_id = NULL, type = 'folder' WHERE id = ?",
                        (mid,)
                    )
                    stats["converted"] += 1
                else:
                    try:
                        cursor.execute("DELETE FROM APP_UserMenus WHERE menu_id = ?", (mid,))
                    except Exception:
                        pass
                    cursor.execute("DELETE FROM APP_Menus WHERE id = ?", (mid,))
                    stats["deleted"] += 1
                stats["menus"].append(m.get("nom"))

        return {
            "success": True, **stats,
            "message": f"{stats['deleted']} menu(s) orphelin(s) supprime(s), "
                       f"{stats['converted']} converti(s) en dossier",
        }
    except Exception as e:
        logger.error(f"[MENUS] cleanup_orphan_menus: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# ==================== DROITS SUR UN RAPPORT ====================

@router.get("/report-access/{report_type}/{report_id}")
def get_report_access(report_type: str, report_id: int):
    """
    Qui voit ce rapport ? Permet d'avertir l'admin qu'un rapport fraichement
    attache a un menu reste invisible pour les utilisateurs non-admin.
    """
    try:
        rtype = _MENU_TO_REPORT_TYPE.get(report_type, report_type)
        roles, granted = [], []
        try:
            roles = execute_query(
                "SELECT id, nom, is_admin FROM APP_Roles WHERE actif = 1",
                use_cache=False
            ) or []
            granted = execute_query(
                """SELECT role_id FROM APP_Role_Reports
                   WHERE report_type = ? AND report_id = ? AND can_view = 1""",
                (rtype, report_id), use_cache=False
            ) or []
        except Exception as e:
            logger.warning(f"[MENUS] get_report_access: {e}")

        granted_ids = {r['role_id'] for r in granted}
        data = [
            {
                "id": r['id'], "nom": r['nom'],
                "is_admin": bool(r.get('is_admin')),
                "can_view": bool(r.get('is_admin')) or r['id'] in granted_ids,
            }
            for r in roles
        ]
        non_admin = [r for r in data if not r["is_admin"]]
        return {
            "success": True,
            "data": data,
            "roles_total": len(non_admin),
            "roles_granted": len([r for r in non_admin if r["can_view"]]),
            "admin_only": len(non_admin) > 0 and not any(r["can_view"] for r in non_admin),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}


@router.post("/report-access")
def set_report_access(grant: ReportAccessGrant):
    """Donne l'acces en lecture a un rapport (roles + utilisateurs sans role)."""
    try:
        res = grant_report_access(
            grant.report_type, grant.report_id,
            role_ids=grant.role_ids, all_roles=grant.all_roles,
            can_export=grant.can_export, menu_id=grant.menu_id,
        )
        return {
            "success": True, **res,
            "message": f"{res['roles_granted']} role(s) et {res['users_granted']} utilisateur(s) autorises",
        }
    except Exception as e:
        logger.error(f"[MENUS] set_report_access: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# ==================== DROITS UTILISATEURS ====================

@router.get("/access/{user_id}")
def get_user_access(user_id: int):
    """Recupere les droits d'acces d'un utilisateur"""
    try:
        results = execute_query(
            """SELECT um.*, m.nom as menu_name, m.code as menu_code
               FROM APP_UserMenus um
               INNER JOIN APP_Menus m ON um.menu_id = m.id
               WHERE um.user_id = ?
               ORDER BY m.ordre""",
            (user_id,),
            use_cache=False
        )
        return {"success": True, "data": results}
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}


@router.post("/access")
def set_user_access(access: UserMenuAccess):
    """Definit l'acces d'un utilisateur a un menu"""
    try:
        with get_db_cursor() as cursor:
            # Upsert
            cursor.execute(
                """MERGE APP_UserMenus AS target
                   USING (SELECT ? as user_id, ? as menu_id) AS source
                   ON target.user_id = source.user_id AND target.menu_id = source.menu_id
                   WHEN MATCHED THEN
                       UPDATE SET can_view = ?, can_export = ?
                   WHEN NOT MATCHED THEN
                       INSERT (user_id, menu_id, can_view, can_export)
                       VALUES (?, ?, ?, ?);""",
                (access.user_id, access.menu_id, access.can_view, access.can_export,
                 access.user_id, access.menu_id, access.can_view, access.can_export)
            )

        return {"success": True, "message": "Acces mis a jour"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/access/bulk")
def set_bulk_user_access(access: BulkUserMenuAccess):
    """Definit les acces d'un utilisateur a plusieurs menus"""
    try:
        with get_db_cursor() as cursor:
            # Supprimer les anciens droits
            cursor.execute("DELETE FROM APP_UserMenus WHERE user_id = ?", (access.user_id,))

            # Ajouter les nouveaux droits
            for menu_id in access.menu_ids:
                cursor.execute(
                    """INSERT INTO APP_UserMenus (user_id, menu_id, can_view, can_export)
                       VALUES (?, ?, 1, ?)""",
                    (access.user_id, menu_id, access.can_export)
                )

        return {"success": True, "message": f"{len(access.menu_ids)} acces configures"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.delete("/access/{user_id}/{menu_id}")
def remove_user_access(user_id: int, menu_id: int):
    """Supprime l'acces d'un utilisateur a un menu"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                "DELETE FROM APP_UserMenus WHERE user_id = ? AND menu_id = ?",
                (user_id, menu_id)
            )

        return {"success": True, "message": "Acces supprime"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== HELPERS ====================

@router.get("/targets/{type}")
def get_available_targets(type: str):
    """Recupere les cibles disponibles pour un type de menu"""
    try:
        if type == "pivot":
            results = execute_query(
                "SELECT id, nom as name FROM APP_Pivots ORDER BY nom",
                use_cache=False
            )
        elif type == "pivot-v2":
            results = execute_query(
                "SELECT id, nom as name FROM APP_Pivots_V2 ORDER BY nom",
                use_cache=False
            )
        elif type == "gridview":
            results = execute_query(
                "SELECT id, nom as name FROM APP_GridViews ORDER BY nom",
                use_cache=False
            )
        elif type == "dashboard":
            results = execute_query(
                "SELECT id, nom as name FROM APP_Dashboards ORDER BY nom",
                use_cache=False
            )
        else:
            results = []

        return {"success": True, "data": results}
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}


@router.post("/init-sample")
def init_sample_menus():
    """Initialise des menus exemple"""
    try:
        # Verifier si des menus existent deja
        count_check = execute_query("SELECT COUNT(*) as cnt FROM APP_Menus", use_cache=False)
        if count_check and count_check[0]['cnt'] > 0:
            return {"success": False, "error": "Des menus existent deja"}

        # Creer des menus exemple
        sample_menus = [
            # Racines
            (None, 'Cycle Ventes', 'cycle-ventes', 'ShoppingCart', 'folder', None, None, 1),
            (None, 'Analyse des Ventes', 'analyse-ventes', 'BarChart3', 'folder', None, None, 2),
            (None, 'Recouvrement', 'recouvrement', 'Wallet', 'folder', None, None, 3),
            (None, 'Stocks', 'stocks', 'Package', 'folder', None, None, 4),
            (None, 'Tableaux de Bord', 'dashboards', 'LayoutDashboard', 'folder', None, None, 5),
        ]

        with get_db_cursor() as cursor:
            for menu in sample_menus:
                cursor.execute(
                    """INSERT INTO APP_Menus (parent_id, nom, code, icon, type, target_id, url, ordre)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    menu
                )

        return {"success": True, "message": "Menus exemple crees"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== MENUS MAITRE (Base Centrale) ====================

@router.get("/master")
def get_master_menus():
    """Recupere tous les menus MAITRE en structure arborescente (base centrale)"""
    try:
        results = execute_central(
            """SELECT m.*, m.actif as is_active
               FROM APP_Menus m
               ORDER BY m.ordre, m.nom""",
            use_cache=False
        )

        # Construire l'arbre
        menu_map = {m['id']: {**m, 'children': []} for m in results}
        root_menus = []

        for menu in results:
            menu_item = menu_map[menu['id']]
            if menu['parent_id'] is None:
                root_menus.append(menu_item)
            else:
                parent = menu_map.get(menu['parent_id'])
                if parent:
                    parent['children'].append(menu_item)

        return {"success": True, "data": root_menus}
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}


@router.get("/master/flat")
def get_master_menus_flat():
    """Recupere tous les menus MAITRE en liste plate (base centrale)"""
    try:
        results = execute_central(
            """SELECT m.*, m.actif as is_active,
                      p.nom as parent_name
               FROM APP_Menus m
               LEFT JOIN APP_Menus p ON m.parent_id = p.id
               ORDER BY m.ordre, m.nom""",
            use_cache=False
        )
        return {"success": True, "data": results}
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}


@router.get("/master/targets/{type}")
def get_master_available_targets(type: str):
    """Recupere les cibles disponibles dans la base MAITRE pour un type de menu"""
    try:
        if type == "pivot":
            results = execute_central(
                "SELECT id, nom as name, code FROM APP_Pivots ORDER BY nom",
                use_cache=False
            )
        elif type == "pivot-v2":
            results = execute_central(
                "SELECT id, nom as name, code FROM APP_Pivots_V2 ORDER BY nom",
                use_cache=False
            )
        elif type == "gridview":
            results = execute_central(
                "SELECT id, nom as name, code FROM APP_GridViews ORDER BY nom",
                use_cache=False
            )
        elif type == "dashboard":
            results = execute_central(
                "SELECT id, nom as name, code FROM APP_Dashboards ORDER BY nom",
                use_cache=False
            )
        else:
            results = []

        return {"success": True, "data": results}
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}


@router.post("/master")
def create_master_menu(menu: MenuCreate):
    """Cree un nouveau menu dans la base MAITRE (centrale)"""
    try:
        with get_central_cursor() as cursor:
            cursor.execute(
                """INSERT INTO APP_Menus (parent_id, nom, code, icon, type, target_id, url, ordre, actif)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (menu.parent_id, menu.nom, menu.code, menu.icon, menu.type,
                 menu.target_id, menu.url, menu.ordre, menu.is_active)
            )

            cursor.execute("SELECT @@IDENTITY AS id")
            new_id = cursor.fetchone()[0]

        return {"success": True, "id": new_id, "message": "Menu maitre cree avec succes"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.put("/master/{menu_id}")
def update_master_menu(menu_id: int, menu: MenuUpdate):
    """Met a jour un menu dans la base MAITRE (centrale)"""
    try:
        updates = []
        params = []

        if menu.parent_id is not None:
            updates.append("parent_id = ?")
            params.append(menu.parent_id if menu.parent_id > 0 else None)
        if menu.nom is not None:
            updates.append("nom = ?")
            params.append(menu.nom)
        if menu.code is not None:
            updates.append("code = ?")
            params.append(menu.code)
        if menu.icon is not None:
            updates.append("icon = ?")
            params.append(menu.icon)
        if menu.type is not None:
            updates.append("type = ?")
            params.append(menu.type)
        if menu.target_id is not None:
            updates.append("target_id = ?")
            params.append(menu.target_id if menu.target_id > 0 else None)
        if menu.url is not None:
            updates.append("url = ?")
            params.append(menu.url)
        if menu.ordre is not None:
            updates.append("ordre = ?")
            params.append(menu.ordre)
        if menu.is_active is not None:
            updates.append("actif = ?")
            params.append(menu.is_active)

        if not updates:
            return {"success": False, "error": "Aucune modification"}

        params.append(menu_id)

        with get_central_cursor() as cursor:
            cursor.execute(f"UPDATE APP_Menus SET {', '.join(updates)} WHERE id = ?", params)

        return {"success": True, "message": "Menu maitre mis a jour"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.delete("/master/{menu_id}")
def delete_master_menu(menu_id: int):
    """Supprime un menu de la base MAITRE (centrale)"""
    try:
        # Verifier s'il y a des enfants
        children_check = execute_central(
            "SELECT COUNT(*) as cnt FROM APP_Menus WHERE parent_id = ?",
            (menu_id,),
            use_cache=False
        )
        if children_check and children_check[0]['cnt'] > 0:
            return {"success": False, "error": "Impossible de supprimer: ce menu a des sous-menus"}

        with get_central_cursor() as cursor:
            cursor.execute("DELETE FROM APP_Menus WHERE id = ?", (menu_id,))

        return {"success": True, "message": "Menu maitre supprime"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# Corrections d'accents manquants dans les noms de menus déjà en base
_ACCENT_FIXES = {
    "CA par Periode":               "CA par Période",
    "CA par Zone Geo":              "CA par Zone Géo",
    "CA par Depot":                 "CA par Dépôt",
    "CA par Categorie Tarifaire":   "CA par Catégorie Tarifaire",
    "Delais par Etape":             "Délais par Étape",
    "Marges & Rentabilite":         "Marges & Rentabilité",
    "Echeances par Commercial":     "Échéances par Commercial",
    "Tendances & Saisonnalite":     "Tendances & Saisonnalité",
    "Recouvrement & Tresorerie":    "Recouvrement & Trésorerie",
    "Balance Agee":                 "Balance Âgée",
    "Creances Douteuses":           "Créances Douteuses",
    "Echeances Non Reglees":        "Échéances Non Réglées",
    "Reglements par Periode":       "Règlements par Période",
    "Reglements par Mode":          "Règlements par Mode",
    "Factures Non Reglees":         "Factures Non Réglées",
    "Prevision Encaissements":      "Prévision Encaissements",
    "Stock par Depot":              "Stock par Dépôt",
    "Valorisation Multi-methodes":  "Valorisation Multi-méthodes",
    "Articles Proches Peremption":  "Articles Proches Péremption",
    "Transferts Inter-Depots":      "Transferts Inter-Dépôts",
    "Echeances Achats":             "Échéances Achats",
    "Preparations Livraison":       "Préparations Livraison",
    "BL Non Factures":              "BL Non Facturés",
}


@router.post("/fix-accents")
def fix_menu_accents():
    """Corrige les accents manquants dans les noms de menus existants en base"""
    try:
        updated = 0
        skipped = 0
        with get_db_cursor() as cursor:
            for old_nom, new_nom in _ACCENT_FIXES.items():
                cursor.execute(
                    "UPDATE APP_Menus SET nom = ? WHERE nom = ?",
                    (new_nom, old_nom)
                )
                rows = cursor.rowcount
                if rows > 0:
                    updated += rows
                    logger.info(f"  fix-accents: '{old_nom}' → '{new_nom}' ({rows} ligne(s))")
                else:
                    skipped += 1

        return {
            "success": True,
            "updated": updated,
            "skipped": skipped,
            "message": f"{updated} menu(s) mis à jour, {skipped} déjà corrects ou absents"
        }
    except Exception as e:
        logger.error(f"fix-accents error: {e}")
        return {"success": False, "error": str(e)}
