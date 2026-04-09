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
)
import json
import logging
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

router = APIRouter(prefix="/api/menus", tags=["menus"])


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


# ==================== MENUS CRUD ====================

@router.get("/")
async def get_all_menus():
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


@router.get("/flat")
async def get_menus_flat():
    """Recupere tous les menus en liste plate"""
    try:
        results = execute_query(
            """SELECT m.*, m.actif as is_active,
                      p.nom as parent_name,
                      CASE
                        WHEN m.type = 'pivot' THEN (SELECT nom FROM APP_Pivots WHERE id = m.target_id)
                        WHEN m.type = 'pivot-v2' THEN (SELECT nom FROM APP_Pivots_V2 WHERE id = m.target_id)
                        WHEN m.type = 'gridview' THEN (SELECT nom FROM APP_GridViews WHERE id = m.target_id)
                        WHEN m.type = 'dashboard' THEN (SELECT nom FROM APP_Dashboards WHERE id = m.target_id)
                        ELSE NULL
                      END as target_name,
               FROM APP_Menus m
               LEFT JOIN APP_Menus p ON m.parent_id = p.id
               ORDER BY m.ordre, m.nom""",
            use_cache=False
        )
        return {"success": True, "data": results}
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}


@router.get("/user/{user_id}")
async def get_user_menus(user_id: int, x_dwh_code: Optional[str] = Header(None)):
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
async def create_menu(menu: MenuCreate):
    """Cree un nouveau menu (cote client : is_custom=1, is_customized=1)"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """INSERT INTO APP_Menus (parent_id, nom, code, icon, type, target_id, url, ordre, actif, is_custom)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                (menu.parent_id, menu.nom, menu.code, menu.icon, menu.type,
                 menu.target_id, menu.url, menu.ordre, menu.is_active)
            )

            cursor.execute("SELECT @@IDENTITY AS id")
            new_id = cursor.fetchone()[0]

        return {"success": True, "id": new_id, "message": "Menu cree avec succes"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.put("/{menu_id}")
async def update_menu(menu_id: int, menu: MenuUpdate):
    """Met a jour un menu"""
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

        with get_db_cursor() as cursor:
            cursor.execute(f"UPDATE APP_Menus SET {', '.join(updates)} WHERE id = ?", params)

        return {"success": True, "message": "Menu mis a jour"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.delete("/{menu_id}")
async def delete_menu(menu_id: int):
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

        return {"success": True, "message": "Menu supprime"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== DROITS UTILISATEURS ====================

@router.get("/access/{user_id}")
async def get_user_access(user_id: int):
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
async def set_user_access(access: UserMenuAccess):
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
async def set_bulk_user_access(access: BulkUserMenuAccess):
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
async def remove_user_access(user_id: int, menu_id: int):
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
async def get_available_targets(type: str):
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
async def init_sample_menus():
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
async def get_master_menus():
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
async def get_master_menus_flat():
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
async def get_master_available_targets(type: str):
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
async def create_master_menu(menu: MenuCreate):
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
async def update_master_menu(menu_id: int, menu: MenuUpdate):
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
async def delete_master_menu(menu_id: int):
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
