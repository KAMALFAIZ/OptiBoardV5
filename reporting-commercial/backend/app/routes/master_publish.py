"""
Master Publish API - Publication d'entites MASTER vers les bases clients
========================================================================
Endpoints pour la gestion centralisee et la publication des entites
(GridViews, Pivots, Dashboards, DataSources, Menus) depuis MASTER
vers les bases OptiBoard_XXX des clients.
"""

import asyncio
import logging
import re
import hashlib
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..database_unified import execute_central as execute_master_query, central_cursor as get_master_cursor
from ..config import get_settings

logger = logging.getLogger("MasterPublish")

router = APIRouter(prefix="/api/master", tags=["master-publish"])

settings = get_settings()


# =============================================================================
# CONFIGURATION
# =============================================================================

# Mapping type -> table MASTER (Templates dans central) -> table CLIENT (destination)
# Source : tables _Templates dans OptiBoard_SaaS (central)
# Destination : tables APP_* dans OptiBoard_cltXXX (client)
ENTITY_CONFIG = {
    'gridviews': {
        'table': 'APP_GridViews_Templates',      # source : central
        'target_table': 'APP_GridViews',          # destination : client
        'columns': 'id, nom, code, description, query_template, columns_config, parameters, features, actif, date_creation, date_modification',
        'upsert_columns': 'nom, code, description, query_template, columns_config, parameters, features, actif, date_creation, date_modification',
        'date_col': 'date_modification',
        'label': 'GridView'
    },
    'pivots': {
        'table': 'APP_Pivots_Templates',          # source : central
        'target_table': 'APP_Pivots_V2',          # destination : client
        'columns': 'id, nom, code, description, data_source_code, rows_config, columns_config, filters_config, values_config, formatting_rules, source_params, actif, date_creation, date_modification',
        'upsert_columns': 'nom, code, description, data_source_code, rows_config, columns_config, filters_config, values_config, formatting_rules, source_params, actif, date_creation, date_modification',
        'date_col': 'date_modification',
        'label': 'Pivot'
    },
    'dashboards': {
        'table': 'APP_Dashboards_Templates',      # source : central
        'target_table': 'APP_Dashboards',         # destination : client
        'columns': 'id, nom, code, description, config, widgets, is_public, actif, date_creation, date_modification',
        'upsert_columns': 'nom, code, description, config, widgets, is_public, actif, date_creation, date_modification',
        'date_col': 'date_modification',
        'label': 'Dashboard'
    },
    'datasources': {
        'table': 'APP_DataSources_Templates',     # source : central
        'target_table': 'APP_DataSources',        # destination : client
        'columns': 'id, nom, code, type, query_template, parameters, description, date_creation',
        'upsert_columns': 'nom, code, type, query_template, parameters, description, date_creation',
        'date_col': 'date_creation',
        'label': 'DataSource'
    },
    'menus': {
        'table': 'APP_Menus_Templates',           # source : central
        'target_table': 'APP_Menus',              # destination : client
        'columns': 'id, nom, code, icon, url, parent_code, ordre, type, target_id, actif, roles, date_creation',
        'upsert_columns': 'nom, code, icon, url, parent_code, ordre, type, target_id, actif, roles, date_creation',
        'date_col': 'date_creation',
        'label': 'Menu'
    }
}


# =============================================================================
# PYDANTIC SCHEMAS
# =============================================================================

class PublishEntity(BaseModel):
    type: str  # gridviews, pivots, dashboards, datasources, menus
    codes: List[str]

class PublishRequest(BaseModel):
    entities: List[PublishEntity]
    clients: List[str]  # DWH codes (ES, FOODIS, etc.)
    mode: str = "upsert"  # upsert = INSERT ou UPDATE par code

class PublishAllRequest(BaseModel):
    clients: Optional[List[str]] = None  # None = tous
    entity_types: Optional[List[str]] = None  # None = tous les types



# =============================================================================
# HELPERS
# =============================================================================

def _is_local_server(server: str) -> bool:
    if not server: return False
    s = server.strip().lower()
    return s in ('.', 'localhost', '(local)', '127.0.0.1') or \
           s.startswith('tcp:localhost') or s.startswith('tcp:127.0.0.1') or \
           s.startswith('.\\') or s.startswith('localhost\\')

def _build_conn_str(server: str, database: str, user: str, password: str) -> str:
    """Construit une connection string SQL Server.
    Utilise SQL Auth si credentials fournis, sinon Windows Auth pour les serveurs locaux.
    """
    if user and password:
        auth = f"UID={user};PWD={password}"
    elif _is_local_server(server):
        auth = "Integrated Security=yes;Trusted_Connection=yes"
    else:
        auth = f"UID={user};PWD={password}"
    return (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={server};DATABASE={database};"
        f"{auth};TrustServerCertificate=yes;"
    )


def _get_client_connection_info() -> List[Dict[str, Any]]:
    """Recupere les infos de connexion OptiBoard de tous les clients depuis MASTER.
    Priorite : colonnes optiboard de APP_DWH > APP_ClientDB > colonnes DWH generiques.
    """
    try:
        rows = execute_master_query(
            """SELECT d.code, d.nom,
                      d.serveur_dwh, d.user_dwh, d.password_dwh,
                      d.serveur_optiboard, d.user_optiboard, d.password_optiboard, d.base_optiboard,
                      c.db_name, c.db_server, c.db_user, c.db_password
               FROM APP_DWH d
               LEFT JOIN APP_ClientDB c ON d.code = c.dwh_code
               WHERE d.actif = 1
               ORDER BY d.nom""",
            use_cache=False
        )
        result = []
        for r in rows:
            # Nom de la base : base_optiboard > APP_ClientDB.db_name > defaut
            db_name = (r.get('base_optiboard') or r.get('db_name')
                       or f"OptiBoard_clt{r['code']}")
            # Serveur : serveur_optiboard > APP_ClientDB.db_server > serveur_dwh
            db_server = (r.get('serveur_optiboard') or r.get('db_server')
                         or r.get('serveur_dwh'))
            # Utilisateur : user_optiboard > APP_ClientDB.db_user > user_dwh
            db_user = (r.get('user_optiboard') or r.get('db_user')
                       or r.get('user_dwh'))
            # Mot de passe : password_optiboard > APP_ClientDB.db_password > password_dwh
            db_password = (r.get('password_optiboard') or r.get('db_password')
                           or r.get('password_dwh'))
            result.append({
                'code': r['code'],
                'nom': r['nom'],
                'db_name': db_name,
                'db_server': db_server,
                'db_user': db_user,
                'db_password': db_password,
            })
        return result
    except Exception as e:
        logger.error(f"Erreur recuperation clients: {e}")
        return []


def _test_client_connection(client_info: Dict) -> bool:
    """Teste la connexion a une base client"""
    import pyodbc
    try:
        conn_str = _build_conn_str(
            client_info['db_server'], client_info['db_name'],
            client_info['db_user'], client_info['db_password']
        )
        conn = pyodbc.connect(conn_str, timeout=5)
        conn.close()
        return True
    except Exception:
        return False


# Colonnes ajoutees progressivement au schema — auto-migration avant publication
_MIGRATION_COLUMNS: Dict[str, List[tuple]] = {
    'menus': [
        ('target_id',     'INT NULL'),
        ('roles',         'NVARCHAR(MAX) NULL'),
        ('parent_code',   'VARCHAR(100) NULL'),   # code texte du parent (source hierarchie)
        ('parent_id',     'INT NULL'),             # FK resolue apres insertion
        ('is_custom',     'BIT NOT NULL DEFAULT 0'),
        ('is_customized', 'BIT NOT NULL DEFAULT 0'),
    ],
    'gridviews': [
        ('is_custom',     'BIT NOT NULL DEFAULT 0'),
        ('is_customized', 'BIT NOT NULL DEFAULT 0'),
    ],
    'pivots': [
        ('is_custom',     'BIT NOT NULL DEFAULT 0'),
        ('is_customized', 'BIT NOT NULL DEFAULT 0'),
    ],
    'dashboards': [
        ('is_custom',     'BIT NOT NULL DEFAULT 0'),
        ('is_customized', 'BIT NOT NULL DEFAULT 0'),
    ],
}


def _ensure_client_table_columns(cursor, table_name: str, entity_type: str) -> None:
    """Auto-migration: ajoute les colonnes manquantes dans la table client.
    Appele avec conn.autocommit=True pour que chaque ALTER TABLE soit atomique.
    """
    cols = _MIGRATION_COLUMNS.get(entity_type, [])
    for col_name, col_def in cols:
        try:
            cursor.execute(
                "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_NAME=? AND COLUMN_NAME=?",
                (table_name, col_name)
            )
            exists = cursor.fetchone()[0]
            if not exists:
                cursor.execute(f"ALTER TABLE {table_name} ADD {col_name} {col_def}")
                logger.info(f"[Migration] {table_name}.{col_name} ajoute ({col_def})")
        except Exception as e:
            logger.warning(f"[Migration] {table_name}.{col_name}: {e}")


def _publish_entities_to_client(
    entity_type: str,
    codes: List[str],
    client_info: Dict,
    mode: str = "upsert"
) -> Dict[str, Any]:
    """
    Publie des entites MASTER vers une base client (sync).
    Optimise : 1 SELECT batch pour les existants, puis batch INSERT/UPDATE.
    """
    import pyodbc

    config = ENTITY_CONFIG.get(entity_type)
    if not config:
        return {"success": False, "error": f"Type inconnu: {entity_type}"}

    # Source = table centrale (_Templates), destination = table client
    table = config['table']
    target_table = config.get('target_table', config['table'])
    upsert_cols = [c.strip() for c in config['upsert_columns'].split(',')]

    results = {"published": 0, "updated": 0, "skipped": 0, "failed": 0, "errors": []}

    try:
        # ── 1) Lire toutes les entites depuis MASTER en un seul SELECT ────
        # Pour les menus : lire depuis APP_Menus (central, avec parent_id)
        # et calculer parent_code via self-join pour garder la hierarchie.
        BATCH_SIZE = 500
        master_rows = []
        if entity_type == 'menus':
            # ── MENUS: source = APP_Menus (central, avec parent_id entier) ──
            # La hierarchie est stockee via parent_id dans la base centrale.
            # On calcule parent_code (code texte du parent) par self-join
            # pour pouvoir l'inserer dans la base client, puis remapper parent_id.
            # NOTE: APP_Menus (central) peut ne pas avoir de colonne date_creation
            #       → on utilise GETDATE() comme valeur de substitution defensive.
            all_menu_rows = execute_master_query(
                """SELECT m.nom,
                          m.code,
                          m.icon,
                          m.url,
                          p.code        AS parent_code,
                          m.ordre,
                          m.type,
                          m.target_id,
                          m.actif,
                          NULL          AS roles,
                          GETDATE()     AS date_creation
                   FROM APP_Menus m
                   LEFT JOIN APP_Menus p ON p.id = m.parent_id
                   WHERE m.code IS NOT NULL AND m.code != ''
                   ORDER BY m.ordre, m.nom""",
                use_cache=False
            )
            # Filtrer sur les codes demandes par le frontend
            codes_set = set(codes)
            master_rows = [r for r in all_menu_rows if r.get('code') in codes_set]
            logger.info(f"[MENUS] {len(all_menu_rows)} menus lus depuis APP_Menus central, "
                        f"{len(master_rows)} filtres sur {len(codes)} codes demandes")
        else:
            for i in range(0, len(codes), BATCH_SIZE):
                batch = codes[i:i + BATCH_SIZE]
                placeholders = ','.join(['?' for _ in batch])
                rows = execute_master_query(
                    f"SELECT {config['upsert_columns']} FROM {table} WHERE code IN ({placeholders})",
                    tuple(batch),
                    use_cache=False
                )
                master_rows.extend(rows)

        if not master_rows:
            return {"success": True, "published": 0, "updated": 0, "failed": 0,
                    "errors": ["Aucune entite trouvee dans MASTER avec ces codes"]}

        # ── 2) Connexion a la base client ─────────────────────────────────
        conn_str = _build_conn_str(
            client_info['db_server'], client_info['db_name'],
            client_info['db_user'], client_info['db_password']
        )
        conn = pyodbc.connect(conn_str, timeout=30)
        conn.autocommit = True   # True pour DDL (migration schema)
        cursor = conn.cursor()

        # ── 2b) Auto-migration: ajouter les colonnes manquantes ───────────
        _ensure_client_table_columns(cursor, target_table, entity_type)

        conn.autocommit = False  # Transaction pour DML

        # ── 3) Lire TOUS les codes existants + is_customized en 1 requete ─
        existing_map = {}  # code -> is_customized
        try:
            cursor.execute(f"SELECT code, ISNULL(is_customized, 0) FROM {target_table} WHERE code IS NOT NULL")
            for row in cursor.fetchall():
                existing_map[row[0]] = row[1]
        except Exception as e:
            logger.warning(f"Lecture existants {table}: {e}")

        # ── 4) Separer INSERT vs UPDATE vs SKIP ──────────────────────────
        to_insert = []
        to_update = []

        for row in master_rows:
            code = row.get('code')
            if not code:
                results['failed'] += 1
                continue

            if code in existing_map:
                if existing_map[code] == 1:
                    results['skipped'] += 1  # Regle 1 : protege
                else:
                    to_update.append(row)
            else:
                to_insert.append(row)

        # ── 5) Batch INSERT ───────────────────────────────────────────────
        if to_insert:
            insert_col_list = upsert_cols + ['is_custom', 'is_customized']
            col_names = ','.join(insert_col_list)
            ph = ','.join(['?' for _ in insert_col_list])
            insert_sql = f"INSERT INTO {target_table} ({col_names}) VALUES ({ph})"

            for row in to_insert:
                try:
                    values = [row.get(col) for col in upsert_cols] + [0, 0]
                    cursor.execute(insert_sql, tuple(values))
                    results['published'] += 1
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append(f"INSERT {row.get('code')}: {str(e)[:80]}")

        # ── 6) Batch UPDATE ───────────────────────────────────────────────
        if to_update:
            update_cols_no_code = [c for c in upsert_cols if c != 'code']
            set_clause = ', '.join([f"{col} = ?" for col in update_cols_no_code])
            update_sql = f"UPDATE {target_table} SET {set_clause} WHERE code = ? AND ISNULL(is_customized, 0) = 0"

            for row in to_update:
                try:
                    values = [row.get(col) for col in update_cols_no_code]
                    values.append(row.get('code'))
                    cursor.execute(update_sql, tuple(values))
                    results['updated'] += 1
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append(f"UPDATE {row.get('code')}: {str(e)[:80]}")

        # ── 7) MENUS: Remapper parent_id depuis parent_code (self-join client) ─
        # Apres insertion de TOUS les menus (avec parent_code), on calcule
        # parent_id en faisant: parent_id = id du menu dont code = parent_code.
        # Cela reconstruit toute l'arborescence dans le client.
        if entity_type == 'menus':
            try:
                # Committer les INSERT/UPDATE avant le remap (visibilite des nouvelles lignes)
                conn.commit()
                conn.autocommit = False

                # ── Reinitialiser tous les parent_id ──────────────────────────
                cursor.execute(
                    "UPDATE APP_Menus SET parent_id = NULL"
                )
                logger.info(f"[MENUS REMAP] parent_id reinitialise pour tous les menus")

                # ── Self-join: parent_id = id du parent dont code = parent_code ─
                cursor.execute("""
                    UPDATE  child
                    SET     child.parent_id = parent.id
                    FROM    APP_Menus child
                    JOIN    APP_Menus parent
                            ON  parent.code = child.parent_code
                    WHERE   child.parent_code IS NOT NULL
                    AND     child.parent_code != ''
                """)
                remapped = cursor.rowcount
                logger.info(f"[MENUS REMAP] {remapped} menus avec parent_id resolu "
                            f"(code→id) → client {client_info['code']}")

                # Verification rapide
                cursor.execute(
                    "SELECT COUNT(*) FROM APP_Menus WHERE parent_code IS NOT NULL "
                    "AND parent_code != '' AND parent_id IS NULL"
                )
                orphelins = cursor.fetchone()[0]
                if orphelins > 0:
                    logger.warning(f"[MENUS REMAP] {orphelins} menus avec parent_code mais parent_id=NULL "
                                   f"(parent peut-etre non publie)")

                conn.commit()
                conn.autocommit = False
                logger.info(f"[MENUS REMAP] Commit OK — hierarchie reconstruite")
            except Exception as e:
                logger.warning(f"[MENUS REMAP] Erreur: {e}")
                results['errors'].append(f"Remapping parent_id: {str(e)[:150]}")

        # Enregistrer dans APP_Update_History pour chaque entite publiee/mise a jour
        try:
            for row in to_insert + to_update:
                code = row.get('code')
                nom = row.get('nom', '')
                conn2 = pyodbc.connect(conn_str, timeout=10)
                cur2 = conn2.cursor()
                try:
                    cur2.execute(
                        """IF EXISTS (SELECT 1 FROM sysobjects WHERE name='APP_Update_History' AND xtype='U')
                           INSERT INTO APP_Update_History
                             (type_entite, code_entite, nom_entite,
                              version_precedente, version_installee, statut, date_installation)
                           VALUES (?, ?, ?, NULL, 1, 'succes', GETDATE())""",
                        (entity_type.rstrip('s'), code, nom)
                    )
                    conn2.commit()
                except Exception:
                    pass
                finally:
                    conn2.close()
        except Exception:
            pass  # Non bloquant

        conn.commit()
        conn.close()
        results['success'] = True

    except Exception as e:
        results['success'] = False
        results['errors'].append(f"Connexion client: {str(e)}")

    return results


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/entities")
async def list_master_entities():
    """Liste toutes les entites MASTER publiables, groupees par type"""
    try:
        def _fetch():
            result = {}
            for entity_type, config in ENTITY_CONFIG.items():
                # Menus: source reelle = APP_Menus (central), pas APP_Menus_Templates
                table = 'APP_Menus' if entity_type == 'menus' else config['table']
                date_col = config['date_col']
                try:
                    if entity_type == 'menus':
                        rows = execute_master_query(
                            "SELECT id, nom, code, GETDATE() as date_modification "
                            "FROM APP_Menus ORDER BY nom",
                            use_cache=False
                        )
                    else:
                        rows = execute_master_query(
                            f"SELECT id, nom, code, {date_col} as date_modification "
                            f"FROM {table} ORDER BY nom",
                            use_cache=False
                        )
                    # Convertir les dates en string
                    for r in rows:
                        if r.get('date_modification') and hasattr(r['date_modification'], 'isoformat'):
                            r['date_modification'] = r['date_modification'].isoformat()
                    result[entity_type] = {
                        'label': config['label'],
                        'count': len(rows),
                        'with_code': len([r for r in rows if r.get('code')]),
                        'items': rows
                    }
                except Exception as e:
                    logger.warning(f"Erreur lecture {table}: {e}")
                    result[entity_type] = {'label': config['label'], 'count': 0, 'with_code': 0, 'items': []}
            return result

        data = await asyncio.to_thread(_fetch)

        # Stats globales
        total = sum(d['count'] for d in data.values())
        with_code = sum(d['with_code'] for d in data.values())

        return {
            "success": True,
            "total": total,
            "with_code": with_code,
            "data": data
        }
    except Exception as e:
        logger.error(f"Erreur list entities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clients")
async def list_publish_clients():
    """Liste les clients disponibles pour publication"""
    try:
        def _fetch():
            clients = _get_client_connection_info()
            for c in clients:
                c['connected'] = _test_client_connection(c)
                # Ne pas exposer les mots de passe
                c.pop('db_password', None)
                c.pop('db_user', None)
            return clients

        clients = await asyncio.to_thread(_fetch)
        return {
            "success": True,
            "total": len(clients),
            "connected": len([c for c in clients if c.get('connected')]),
            "data": clients
        }
    except Exception as e:
        logger.error(f"Erreur list clients: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sync-status")
async def get_sync_status(entity_type: str, code: str):
    """Compare le statut d'une entite MASTER vs toutes les bases client"""
    try:
        config = ENTITY_CONFIG.get(entity_type)
        if not config:
            raise HTTPException(status_code=400, detail=f"Type inconnu: {entity_type}")

        def _fetch():
            import pyodbc

            table = config['table']
            date_col = config['date_col']

            # Lire l'entite MASTER
            master_rows = execute_master_query(
                f"SELECT id, nom, code, {date_col} as date_modification FROM {table} WHERE code = ?",
                (code,),
                use_cache=False
            )
            if not master_rows:
                return None

            entity = master_rows[0]
            if entity.get('date_modification') and hasattr(entity['date_modification'], 'isoformat'):
                entity['date_modification'] = entity['date_modification'].isoformat()

            # Comparer avec chaque client
            clients = _get_client_connection_info()
            client_statuses = []

            for client in clients:
                status_info = {
                    'code': client['code'],
                    'nom': client['nom'],
                    'status': 'unknown',
                    'client_date': None
                }
                try:
                    conn_str = _build_conn_str(
                        client['db_server'], client['db_name'],
                        client['db_user'], client['db_password']
                    )
                    conn = pyodbc.connect(conn_str, timeout=5)
                    cursor = conn.cursor()

                    cursor.execute(
                        f"SELECT {date_col} FROM {table} WHERE code = ?",
                        (code,)
                    )
                    row = cursor.fetchone()
                    conn.close()

                    if not row:
                        status_info['status'] = 'missing'
                    else:
                        client_date = row[0]
                        master_date = master_rows[0].get(date_col)
                        # Determiner le statut par comparaison de dates
                        try:
                            if client_date and master_date:
                                # Convertir en datetime si necessaire
                                if isinstance(master_date, str):
                                    master_date = datetime.fromisoformat(master_date)
                                if isinstance(client_date, str):
                                    client_date = datetime.fromisoformat(client_date)
                                status_info['status'] = 'synced' if client_date >= master_date else 'outdated'
                            else:
                                status_info['status'] = 'synced'
                        except Exception:
                            status_info['status'] = 'synced'
                        if client_date and hasattr(client_date, 'isoformat'):
                            status_info['client_date'] = client_date.isoformat()

                except Exception as e:
                    status_info['status'] = 'error'
                    status_info['error'] = str(e)

                client_statuses.append(status_info)

            return {
                'entity': entity,
                'clients': client_statuses
            }

        data = await asyncio.to_thread(_fetch)
        if data is None:
            raise HTTPException(status_code=404, detail=f"Entite avec code '{code}' non trouvee")

        return {"success": True, "data": data}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur sync-status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/publish")
async def publish_entities(request: PublishRequest):
    """Publie des entites selectionnees vers des clients selectionnes"""
    try:
        def _execute():
            clients = _get_client_connection_info()
            # Filtrer les clients demandes
            target_clients = [c for c in clients if c['code'] in request.clients]
            if not target_clients:
                return {"success": False, "error": "Aucun client valide trouve"}

            results = {
                "total_published": 0,
                "total_updated": 0,
                "total_failed": 0,
                "details": []
            }

            for entity_group in request.entities:
                entity_type = entity_group.type
                codes = entity_group.codes

                for client in target_clients:
                    result = _publish_entities_to_client(
                        entity_type, codes, client, request.mode
                    )
                    detail = {
                        "entity_type": entity_type,
                        "client_code": client['code'],
                        "client_nom": client['nom'],
                        "published": result.get('published', 0),
                        "updated": result.get('updated', 0),
                        "failed": result.get('failed', 0),
                        "errors": result.get('errors', [])
                    }
                    results['details'].append(detail)
                    results['total_published'] += detail['published']
                    results['total_updated'] += detail['updated']
                    results['total_failed'] += detail['failed']

            results['success'] = results['total_failed'] == 0
            return results

        data = await asyncio.to_thread(_execute)
        return data

    except Exception as e:
        logger.error(f"Erreur publish: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/publish-all")
async def publish_all_entities(request: PublishAllRequest):
    """Publie toutes les entites MASTER vers les clients"""
    try:
        def _execute():
            # Determiner les types a publier
            types_to_publish = request.entity_types or list(ENTITY_CONFIG.keys())

            # Recuperer tous les codes par type
            entities_to_publish = []
            for entity_type in types_to_publish:
                config = ENTITY_CONFIG.get(entity_type)
                if not config:
                    continue
                try:
                    # Menus: lire depuis APP_Menus (centrale), pas APP_Menus_Templates
                    src_table = 'APP_Menus' if entity_type == 'menus' else config['table']
                    rows = execute_master_query(
                        f"SELECT code FROM {src_table} WHERE code IS NOT NULL AND code != ''",
                        use_cache=False
                    )
                    codes = [r['code'] for r in rows if r.get('code')]
                    if codes:
                        entities_to_publish.append(PublishEntity(type=entity_type, codes=codes))
                except Exception as e:
                    logger.warning(f"Table {config['table']} inaccessible, ignoree: {e}")

            if not entities_to_publish:
                return {"success": True, "message": "Aucune entite avec code a publier",
                        "total_published": 0, "total_updated": 0, "total_failed": 0, "details": []}

            # Recuperer les clients
            clients = _get_client_connection_info()
            if request.clients:
                clients = [c for c in clients if c['code'] in request.clients]

            if not clients:
                return {"success": False, "error": "Aucun client disponible"}

            results = {
                "total_published": 0,
                "total_updated": 0,
                "total_failed": 0,
                "details": []
            }

            for entity_group in entities_to_publish:
                for client in clients:
                    result = _publish_entities_to_client(
                        entity_group.type, entity_group.codes, client, "upsert"
                    )
                    detail = {
                        "entity_type": entity_group.type,
                        "client_code": client['code'],
                        "client_nom": client['nom'],
                        "published": result.get('published', 0),
                        "updated": result.get('updated', 0),
                        "failed": result.get('failed', 0),
                        "errors": result.get('errors', [])
                    }
                    results['details'].append(detail)
                    results['total_published'] += detail['published']
                    results['total_updated'] += detail['updated']
                    results['total_failed'] += detail['failed']

            results['success'] = True
            return results

        data = await asyncio.to_thread(_execute)
        return data

    except Exception as e:
        logger.error(f"Erreur publish-all: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-codes")
async def generate_codes_for_existing():
    """Genere des codes uniques pour toutes les entites MASTER qui n'en ont pas"""
    try:
        def _execute():
            import pyodbc

            prefix_map = {
                'gridviews': 'GV',
                'pivots': 'PV',
                'dashboards': 'DB',
                'datasources': 'DS',
                'menus': 'MN'
            }

            results = {}
            total_updated = 0

            for entity_type, config in ENTITY_CONFIG.items():
                table = config['table']
                prefix = prefix_map.get(entity_type, 'XX')

                # Lire les entites sans code
                rows = execute_master_query(
                    f"SELECT id, nom FROM {table} WHERE code IS NULL OR code = ''",
                    use_cache=False
                )

                if not rows:
                    results[entity_type] = 0
                    continue

                # Generer et mettre a jour les codes
                updated = 0
                with get_master_cursor() as cursor:
                    for row in rows:
                        nom = row.get('nom', 'unknown')
                        slug = re.sub(r'[^a-z0-9]+', '_', nom.lower().strip())[:40].strip('_')
                        suffix = hashlib.md5(f"{nom}{row['id']}{time.time()}".encode()).hexdigest()[:4]
                        code = f"{prefix}_{slug}_{suffix}"

                        try:
                            cursor.execute(
                                f"UPDATE {table} SET code = ? WHERE id = ? AND (code IS NULL OR code = '')",
                                (code, row['id'])
                            )
                            updated += 1
                        except Exception as e:
                            logger.warning(f"Erreur code {table} id={row['id']}: {e}")

                results[entity_type] = updated
                total_updated += updated

            return {
                "success": True,
                "total_updated": total_updated,
                "details": results
            }

        data = await asyncio.to_thread(_execute)
        return data

    except Exception as e:
        logger.error(f"Erreur generate-codes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/menus-sync-status")
async def get_menus_sync_status():
    """
    Compare les menus MAITRE vs chaque base client.
    Retourne pour chaque client : nb total, nb synced, nb customized, nb missing.
    """
    try:
        def _fetch():
            import pyodbc

            # 1. Lire les menus MAITRE (avec code)
            master_menus = execute_master_query(
                "SELECT id, nom, code FROM APP_Menus WHERE code IS NOT NULL AND code != '' ORDER BY ordre, nom",
                use_cache=False
            )
            master_codes = {m['code'] for m in master_menus}

            # 2. Pour chaque client, comparer
            clients = _get_client_connection_info()
            client_statuses = []

            for client in clients:
                status_info = {
                    'code': client['code'],
                    'nom': client['nom'],
                    'master_count': len(master_codes),
                    'client_total': 0,
                    'synced': 0,
                    'customized': 0,
                    'missing': 0,
                    'client_only': 0,
                    'status': 'unknown',
                    'error': None,
                }
                try:
                    conn_str = _build_conn_str(
                        client['db_server'], client['db_name'],
                        client['db_user'], client['db_password']
                    )
                    conn = pyodbc.connect(conn_str, timeout=5)
                    cursor = conn.cursor()

                    # Lire les menus du client
                    cursor.execute(
                        "SELECT code, ISNULL(is_customized, 0) as is_customized "
                        "FROM APP_Menus WHERE code IS NOT NULL AND code != ''"
                    )
                    client_rows = cursor.fetchall()
                    client_menu_map = {r[0]: r[1] for r in client_rows}

                    # Compter le total des menus client (y compris sans code)
                    cursor.execute("SELECT COUNT(*) FROM APP_Menus")
                    status_info['client_total'] = cursor.fetchone()[0]

                    conn.close()

                    # Comparer
                    for code in master_codes:
                        if code in client_menu_map:
                            if client_menu_map[code] == 1:
                                status_info['customized'] += 1
                            else:
                                status_info['synced'] += 1
                        else:
                            status_info['missing'] += 1

                    # Menus client sans equivalent maitre
                    status_info['client_only'] = len(
                        [c for c in client_menu_map if c not in master_codes]
                    )

                    # Determiner le statut global
                    if status_info['missing'] == 0 and status_info['customized'] == 0:
                        status_info['status'] = 'synced'
                    elif status_info['missing'] == 0:
                        status_info['status'] = 'partial'
                    else:
                        status_info['status'] = 'outdated'

                except Exception as e:
                    status_info['status'] = 'error'
                    status_info['error'] = str(e)[:200]

                client_statuses.append(status_info)

            return {
                'master_menus': master_menus,
                'master_count': len(master_codes),
                'clients': client_statuses,
            }

        data = await asyncio.to_thread(_fetch)
        return {"success": True, "data": data}

    except Exception as e:
        logger.error(f"Erreur menus-sync-status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
