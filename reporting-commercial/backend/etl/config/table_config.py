"""
Gestionnaire de configuration des tables ETL
Stockage en base SQL - Table ETL_Tables_Config
Synchronisation automatique avec APP_ETL_Agent_Tables et YAML
"""
import json
import logging
import yaml
from typing import Optional, List, Dict, Any
from functools import lru_cache
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Chemin du fichier YAML de configuration
YAML_CONFIG_PATH = Path(__file__).parent / "sync_tables.yaml"

# Configuration par defaut
DEFAULT_GLOBAL_CONFIG = {
    "timestamp_column": "cbModification",
    "creation_column": "cbCreation",
    "sync_interval_seconds": 300,
    "batch_size": 10000,
    "staging_threshold": 100000,
    "source_label_column": "Societe"
}


def _get_connection():
    """Obtient une connexion a la base de donnees principale."""
    from app.database import get_connection
    return get_connection()


def _ensure_table_exists():
    """Cree la table ETL_Tables_Config si elle n'existe pas, et migre le schema si necessaire."""
    create_table_sql = """
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='ETL_Tables_Config' AND xtype='U')
    CREATE TABLE ETL_Tables_Config (
        id INT IDENTITY(1,1) PRIMARY KEY,
        name NVARCHAR(100) NOT NULL UNIQUE,
        source_table NVARCHAR(200),
        source_query NVARCHAR(MAX),
        target_table NVARCHAR(200) NOT NULL DEFAULT '',
        primary_key NVARCHAR(500),
        sync_type NVARCHAR(50) DEFAULT 'full',
        timestamp_column NVARCHAR(100),
        priority NVARCHAR(20) DEFAULT 'normal',
        batch_size INT DEFAULT 10000,
        description NVARCHAR(500),
        enabled BIT DEFAULT 1,
        sort_order INT DEFAULT 0,
        interval_minutes INT DEFAULT 5,
        delete_detection BIT DEFAULT 0,
        created_at DATETIME DEFAULT GETDATE(),
        updated_at DATETIME DEFAULT GETDATE()
    )
    """

    create_global_table_sql = """
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='ETL_Global_Config' AND xtype='U')
    CREATE TABLE ETL_Global_Config (
        id INT IDENTITY(1,1) PRIMARY KEY,
        config_key NVARCHAR(100) NOT NULL UNIQUE,
        config_value NVARCHAR(500) NOT NULL,
        updated_at DATETIME DEFAULT GETDATE()
    )
    """

    # Migrations : ajouter les colonnes manquantes si la table existe deja avec un vieux schema
    migration_sqls = [
        ("name",             "IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('ETL_Tables_Config') AND name='name') ALTER TABLE ETL_Tables_Config ADD name NVARCHAR(100)"),
        ("source_table",     "IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('ETL_Tables_Config') AND name='source_table') ALTER TABLE ETL_Tables_Config ADD source_table NVARCHAR(200)"),
        ("primary_key",      "IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('ETL_Tables_Config') AND name='primary_key') ALTER TABLE ETL_Tables_Config ADD primary_key NVARCHAR(500)"),
        ("batch_size",       "IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('ETL_Tables_Config') AND name='batch_size') ALTER TABLE ETL_Tables_Config ADD batch_size INT DEFAULT 10000"),
        ("description",      "IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('ETL_Tables_Config') AND name='description') ALTER TABLE ETL_Tables_Config ADD description NVARCHAR(500)"),
        ("enabled",          "IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('ETL_Tables_Config') AND name='enabled') ALTER TABLE ETL_Tables_Config ADD enabled BIT DEFAULT 1"),
        ("sort_order",       "IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('ETL_Tables_Config') AND name='sort_order') ALTER TABLE ETL_Tables_Config ADD sort_order INT DEFAULT 0"),
        ("interval_minutes", "IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('ETL_Tables_Config') AND name='interval_minutes') ALTER TABLE ETL_Tables_Config ADD interval_minutes INT DEFAULT 5"),
        ("delete_detection", "IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('ETL_Tables_Config') AND name='delete_detection') ALTER TABLE ETL_Tables_Config ADD delete_detection BIT DEFAULT 0"),
    ]

    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute(create_table_sql)
        cursor.execute(create_global_table_sql)
        conn.commit()

        # Appliquer les migrations de schema
        for col_name, migration_sql in migration_sqls:
            try:
                cursor.execute(migration_sql)
                conn.commit()
            except Exception as e:
                logger.warning(f"Migration colonne '{col_name}': {e}")

        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(f"Erreur creation table ETL_Tables_Config: {e}")


def _init_default_global_config():
    """Initialise la configuration globale par defaut si vide."""
    try:
        conn = _get_connection()
        cursor = conn.cursor()

        # Verifier si config existe
        cursor.execute("SELECT COUNT(*) FROM ETL_Global_Config")
        count = cursor.fetchone()[0]

        if count == 0:
            # Inserer config par defaut
            for key, value in DEFAULT_GLOBAL_CONFIG.items():
                cursor.execute(
                    "INSERT INTO ETL_Global_Config (config_key, config_value) VALUES (?, ?)",
                    (key, str(value))
                )
            conn.commit()

        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(f"Erreur init config globale: {e}")


def _table_row_to_dict(row, columns) -> Dict[str, Any]:
    """Convertit une ligne SQL en dictionnaire de configuration table."""
    data = dict(zip(columns, row))

    # Parser primary_key comme liste
    pk = data.get('primary_key', '')
    if pk:
        data['primary_key'] = [k.strip() for k in pk.split(',')]
    else:
        data['primary_key'] = []

    # Construire structure source/target pour compatibilite
    result = {
        'name': data['name'],
        'source': {},
        'target': {
            'table': data['target_table'],
            'primary_key': data['primary_key']
        },
        'sync_type': data.get('sync_type', 'full'),
        'priority': data.get('priority', 'normal'),
        'enabled': bool(data.get('enabled', True)),
        'description': data.get('description', ''),
        'batch_size': data.get('batch_size', 10000),
        'sort_order': data.get('sort_order', 0),
        'interval_minutes': data.get('interval_minutes', 5),
        'delete_detection': bool(data.get('delete_detection', False))
    }

    # Source: query ou table
    if data.get('source_query'):
        result['source']['query'] = data['source_query']
    elif data.get('source_table'):
        result['source']['table'] = data['source_table']

    # Timestamp column pour incremental
    if data.get('timestamp_column'):
        result['timestamp_column'] = data['timestamp_column']

    return result


@lru_cache(maxsize=1)
def get_global_config() -> Dict[str, Any]:
    """
    Retourne la configuration globale (avec cache).

    Returns:
        Dict de configuration globale
    """
    _ensure_table_exists()
    _init_default_global_config()

    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT config_key, config_value FROM ETL_Global_Config")

        config = {}
        for row in cursor.fetchall():
            key, value = row
            # Convertir les valeurs numeriques
            if value.isdigit():
                config[key] = int(value)
            else:
                config[key] = value

        cursor.close()
        conn.close()

        return config if config else DEFAULT_GLOBAL_CONFIG.copy()
    except Exception as e:
        logger.error(f"Erreur lecture config globale: {e}")
        return DEFAULT_GLOBAL_CONFIG.copy()


@lru_cache(maxsize=1)
def get_tables() -> List[Dict[str, Any]]:
    """
    Retourne la liste des tables configurees (avec cache).
    Si la table SQL est vide, charge depuis le fichier YAML.

    Returns:
        Liste des configurations de tables
    """
    _ensure_table_exists()

    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ISNULL(name, table_name) as name,
                   ISNULL(source_table, table_name) as source_table,
                   source_query, target_table, primary_key,
                   sync_type, timestamp_column, priority, batch_size, description, enabled,
                   ISNULL(sort_order, 0) as sort_order,
                   ISNULL(interval_minutes, 5) as interval_minutes,
                   ISNULL(delete_detection, 0) as delete_detection
            FROM ETL_Tables_Config
            ORDER BY ISNULL(sort_order, 999), ISNULL(name, table_name)
        """)

        columns = ['name', 'source_table', 'source_query', 'target_table', 'primary_key',
                   'sync_type', 'timestamp_column', 'priority', 'batch_size', 'description', 'enabled', 'sort_order',
                   'interval_minutes', 'delete_detection']

        tables = []
        for row in cursor.fetchall():
            tables.append(_table_row_to_dict(row, columns))

        cursor.close()
        conn.close()

        # Si pas de tables en SQL, charger depuis YAML
        if not tables:
            logger.info("Table SQL vide, chargement depuis YAML")
            tables = _load_tables_from_yaml()

        return tables
    except Exception as e:
        logger.error(f"Erreur lecture tables ETL: {e}")
        # Fallback vers YAML en cas d'erreur
        return _load_tables_from_yaml()


def _load_tables_from_yaml() -> List[Dict[str, Any]]:
    """
    Charge les tables depuis le fichier YAML.

    Returns:
        Liste des configurations de tables
    """
    if not YAML_CONFIG_PATH.exists():
        logger.warning(f"Fichier YAML non trouve: {YAML_CONFIG_PATH}")
        return []

    try:
        with open(YAML_CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        if not config or 'tables' not in config:
            return []

        tables = []
        for table in config.get('tables', []):
            # Normaliser la structure
            source = table.get('source', {})
            target = table.get('target', {})

            # S'assurer que primary_key est une liste
            pk = target.get('primary_key', [])
            if pk is None:
                pk = []
            elif isinstance(pk, str):
                pk = [k.strip() for k in pk.split(',')]

            normalized = {
                'name': table.get('name', ''),
                'source': source,
                'target': {
                    'table': target.get('table', ''),
                    'primary_key': pk
                },
                'sync_type': table.get('sync_type', 'full'),
                'priority': table.get('priority', 'normal'),
                'enabled': table.get('enabled', True),
                'description': table.get('description', ''),
                'batch_size': table.get('batch_size', 10000),
                'sort_order': table.get('sort_order', 0),
                'interval_minutes': table.get('interval_minutes', 5),
                'delete_detection': table.get('delete_detection', False)
            }

            if table.get('timestamp_column'):
                normalized['timestamp_column'] = table['timestamp_column']

            tables.append(normalized)

        # Trier par sort_order
        tables.sort(key=lambda x: (x.get('sort_order', 999), x.get('name', '')))

        logger.info(f"Charge {len(tables)} tables depuis YAML")
        return tables

    except Exception as e:
        logger.error(f"Erreur chargement YAML: {e}")
        return []


def import_yaml_to_sql() -> Dict[str, Any]:
    """
    Importe toutes les tables du fichier YAML vers la table SQL ETL_Tables_Config.
    Utile pour migrer d'une config YAML vers une config SQL.

    Returns:
        Dict avec le resultat: {'success': bool, 'imported': int, 'skipped': int, 'errors': int}
    """
    _ensure_table_exists()

    result = {'success': True, 'imported': 0, 'skipped': 0, 'errors': 0, 'details': []}

    yaml_tables = _load_tables_from_yaml()
    if not yaml_tables:
        result['details'].append("Aucune table dans le fichier YAML")
        return result

    for table in yaml_tables:
        try:
            name = table.get('name')
            if not name:
                result['errors'] += 1
                continue

            # Verifier si existe deja en SQL
            conn = _get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM ETL_Tables_Config WHERE name = ?", (name,))
            exists = cursor.fetchone()[0] > 0

            if exists:
                result['skipped'] += 1
                result['details'].append(f"Table '{name}' existe deja - ignoree")
                cursor.close()
                conn.close()
                continue

            # Extraire les valeurs
            source = table.get('source', {})
            target = table.get('target', {})
            source_query = source.get('query', '')
            target_table = target.get('table', name)
            pk = target.get('primary_key', [])
            pk_str = ','.join(pk) if isinstance(pk, list) else str(pk or '')

            cursor.execute("""
                INSERT INTO ETL_Tables_Config (
                    name, source_query, target_table, primary_key,
                    sync_type, timestamp_column, priority, batch_size,
                    description, enabled, sort_order, interval_minutes, delete_detection
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                name,
                source_query,
                target_table,
                pk_str,
                table.get('sync_type', 'full'),
                table.get('timestamp_column', ''),
                table.get('priority', 'normal'),
                table.get('batch_size', 10000),
                table.get('description', ''),
                1 if table.get('enabled', True) else 0,
                table.get('sort_order', 0),
                table.get('interval_minutes', 5),
                1 if table.get('delete_detection', False) else 0
            ))
            conn.commit()
            cursor.close()
            conn.close()

            result['imported'] += 1
            result['details'].append(f"Table '{name}' importee")

        except Exception as e:
            result['errors'] += 1
            result['details'].append(f"Erreur pour '{table.get('name', '?')}': {str(e)}")
            logger.error(f"Erreur import table {table.get('name')}: {e}")

    if result['errors'] > 0:
        result['success'] = False

    # Invalider le cache
    invalidate_cache()

    logger.info(f"Import YAML->SQL: {result['imported']} importees, {result['skipped']} ignorees, {result['errors']} erreurs")
    return result


def get_table_by_name(name: str) -> Optional[Dict[str, Any]]:
    """
    Recupere une table par son nom.
    Cherche d'abord dans SQL, puis dans YAML si non trouve.

    Args:
        name: Nom de la table

    Returns:
        Configuration de la table ou None
    """
    _ensure_table_exists()

    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ISNULL(name, table_name) as name,
                   ISNULL(source_table, table_name) as source_table,
                   source_query, target_table, primary_key,
                   sync_type, timestamp_column, priority, batch_size, description, enabled,
                   ISNULL(sort_order, 0) as sort_order,
                   ISNULL(interval_minutes, 5) as interval_minutes,
                   ISNULL(delete_detection, 0) as delete_detection
            FROM ETL_Tables_Config
            WHERE ISNULL(name, table_name) = ?
        """, (name,))

        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if row:
            columns = ['name', 'source_table', 'source_query', 'target_table', 'primary_key',
                       'sync_type', 'timestamp_column', 'priority', 'batch_size', 'description', 'enabled', 'sort_order',
                       'interval_minutes', 'delete_detection']
            return _table_row_to_dict(row, columns)

        # Si non trouve en SQL, chercher dans YAML
        tables = _load_tables_from_yaml()
        for table in tables:
            if table.get('name') == name:
                return table

        return None
    except Exception as e:
        logger.error(f"Erreur lecture table {name}: {e}")
        # Fallback vers YAML
        tables = _load_tables_from_yaml()
        for table in tables:
            if table.get('name') == name:
                return table
        return None


def add_table(table_config: Dict[str, Any]) -> bool:
    """
    Ajoute une table a la configuration.

    Args:
        table_config: Configuration de la table

    Returns:
        True si ajoutee, False si existe deja
    """
    _ensure_table_exists()

    name = table_config.get('name')
    if not name:
        return False

    # Extraire les valeurs (supporte les deux formats: plat ou nested)
    source = table_config.get('source', {})
    target = table_config.get('target', {})

    source_table = source.get('table') or table_config.get('source_table')
    source_query = source.get('query') or table_config.get('source_query') or table_config.get('query')
    target_table = target.get('table') or table_config.get('target_table') or name

    # Primary key: peut etre liste ou string
    pk = target.get('primary_key') or table_config.get('primary_key', [])
    if isinstance(pk, list):
        primary_key = ','.join(pk)
    else:
        primary_key = pk

    sync_type = table_config.get('sync_type', 'full')
    timestamp_column = table_config.get('timestamp_column') or table_config.get('incremental_column')
    priority = table_config.get('priority', 'normal')
    batch_size = table_config.get('batch_size', 10000)
    description = table_config.get('description', '')
    enabled = table_config.get('enabled', True)
    sort_order = table_config.get('sort_order', 0)
    interval_minutes = table_config.get('interval_minutes', 5)
    delete_detection = table_config.get('delete_detection', False)

    try:
        conn = _get_connection()
        cursor = conn.cursor()

        # Verifier si existe deja (sur name ET table_name pour compatibilite schema)
        cursor.execute(
            "SELECT COUNT(*) FROM ETL_Tables_Config WHERE name = ? OR table_name = ?",
            (name, name)
        )
        if cursor.fetchone()[0] > 0:
            cursor.close()
            conn.close()
            return False

        cursor.execute("""
            INSERT INTO ETL_Tables_Config
            (table_name, name, source_table, source_query, target_table, primary_key,
             sync_type, timestamp_column, priority, batch_size, description, enabled, sort_order,
             interval_minutes, delete_detection)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, name, source_table, source_query, target_table, primary_key,
              sync_type, timestamp_column, priority, batch_size, description, 1 if enabled else 0, sort_order,
              interval_minutes, 1 if delete_detection else 0))

        conn.commit()
        cursor.close()
        conn.close()

        # Invalider le cache
        invalidate_cache()

        # Synchroniser avec les tables agents et le YAML
        sync_table_to_agents(name, table_config)
        sync_to_yaml()

        return True
    except Exception as e:
        logger.error(f"Erreur ajout table {name}: {e}")
        return False


def update_table(name: str, updates: Dict[str, Any]) -> bool:
    """
    Met a jour une table existante.
    Si la table n'existe pas en SQL mais existe dans YAML, elle est d'abord migree.

    Args:
        name: Nom de la table
        updates: Champs a mettre a jour

    Returns:
        True si mise a jour, False si non trouvee
    """
    _ensure_table_exists()

    try:
        conn = _get_connection()
        cursor = conn.cursor()

        # Verifier si existe en SQL
        cursor.execute("SELECT COUNT(*) FROM ETL_Tables_Config WHERE name = ?", (name,))
        if cursor.fetchone()[0] == 0:
            # Table pas en SQL, verifier si existe dans YAML
            yaml_table = None
            tables = _load_tables_from_yaml()
            for t in tables:
                if t.get('name') == name:
                    yaml_table = t
                    break

            if yaml_table:
                # Migrer la table YAML vers SQL d'abord
                cursor.close()
                conn.close()
                logger.info(f"Migration table '{name}' depuis YAML vers SQL")
                if not add_table(yaml_table):
                    logger.error(f"Echec migration table '{name}'")
                    return False
                # Rouvrir connexion pour l'update
                conn = _get_connection()
                cursor = conn.cursor()
            else:
                cursor.close()
                conn.close()
                return False

        # Construire la requete UPDATE dynamiquement
        set_clauses = []
        params = []

        field_mapping = {
            'source_table': 'source_table',
            'source_query': 'source_query',
            'query': 'source_query',
            'target_table': 'target_table',
            'sync_type': 'sync_type',
            'timestamp_column': 'timestamp_column',
            'incremental_column': 'timestamp_column',
            'priority': 'priority',
            'batch_size': 'batch_size',
            'description': 'description',
            'enabled': 'enabled',
            'sort_order': 'sort_order',
            'interval_minutes': 'interval_minutes',
            'delete_detection': 'delete_detection'
        }

        for key, value in updates.items():
            if value is not None and key in field_mapping:
                db_field = field_mapping[key]

                if key in ('enabled', 'delete_detection'):
                    value = 1 if value else 0
                elif key == 'primary_key':
                    if isinstance(value, list):
                        value = ','.join(value)

                set_clauses.append(f"{db_field} = ?")
                params.append(value)

        # Gerer primary_key separement
        if 'primary_key' in updates:
            pk = updates['primary_key']
            if isinstance(pk, list):
                pk = ','.join(pk)
            set_clauses.append("primary_key = ?")
            params.append(pk)

        if not set_clauses:
            cursor.close()
            conn.close()
            return True

        set_clauses.append("updated_at = GETDATE()")
        params.append(name)

        query = f"UPDATE ETL_Tables_Config SET {', '.join(set_clauses)} WHERE name = ?"
        cursor.execute(query, params)

        conn.commit()
        cursor.close()
        conn.close()

        # Invalider le cache
        invalidate_cache()

        # Recuperer la config complete et synchroniser
        updated_config = get_table_by_name(name)
        if updated_config:
            sync_table_to_agents(name, updated_config)
            sync_to_yaml()

        return True
    except Exception as e:
        logger.error(f"Erreur mise a jour table {name}: {e}")
        return False


def delete_table(name: str) -> bool:
    """
    Supprime une table de la configuration (SQL et/ou YAML).

    Args:
        name: Nom de la table

    Returns:
        True si supprimee, False si non trouvee
    """
    _ensure_table_exists()
    deleted_from_sql = False
    deleted_from_yaml = False

    try:
        conn = _get_connection()
        cursor = conn.cursor()

        # Log pour debug
        logger.info(f"Tentative de suppression de la table: '{name}'")

        # Verifier d'abord si la table existe en SQL
        cursor.execute("SELECT name FROM ETL_Tables_Config WHERE name = ?", (name,))
        existing = cursor.fetchone()

        if existing:
            cursor.execute("DELETE FROM ETL_Tables_Config WHERE name = ?", (name,))
            deleted_from_sql = cursor.rowcount > 0
            conn.commit()
            logger.info(f"Table '{name}' supprimee de SQL")
        else:
            logger.info(f"Table '{name}' non trouvee dans ETL_Tables_Config SQL")

        cursor.close()
        conn.close()

        # Supprimer aussi du fichier YAML
        deleted_from_yaml = _delete_table_from_yaml(name)

        if deleted_from_sql or deleted_from_yaml:
            logger.info(f"Table '{name}' supprimee (SQL: {deleted_from_sql}, YAML: {deleted_from_yaml})")
            invalidate_cache()
            # Supprimer aussi des tables agents
            remove_table_from_agents(name)
            return True

        logger.warning(f"Table '{name}' non trouvee ni en SQL ni en YAML")
        return False
    except Exception as e:
        logger.error(f"Erreur suppression table {name}: {e}")
        return False


def _delete_table_from_yaml(name: str) -> bool:
    """
    Supprime une table specifique du fichier YAML.

    Args:
        name: Nom de la table a supprimer

    Returns:
        True si supprimee, False sinon
    """
    try:
        if not YAML_CONFIG_PATH.exists():
            return False

        with open(YAML_CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}

        tables = config.get('tables', [])
        original_count = len(tables)

        # Filtrer pour enlever la table
        config['tables'] = [t for t in tables if t.get('name') != name]

        if len(config['tables']) < original_count:
            # Reecrire le fichier
            with open(YAML_CONFIG_PATH, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            logger.info(f"Table '{name}' supprimee du fichier YAML")
            return True

        return False
    except Exception as e:
        logger.error(f"Erreur suppression table {name} du YAML: {e}")
        return False


def toggle_table(name: str) -> Optional[bool]:
    """
    Active/Desactive une table (SQL ou YAML).

    Args:
        name: Nom de la table

    Returns:
        Nouvel etat enabled, ou None si non trouvee
    """
    _ensure_table_exists()

    try:
        conn = _get_connection()
        cursor = conn.cursor()

        # Recuperer l'etat actuel depuis SQL
        cursor.execute("SELECT enabled FROM ETL_Tables_Config WHERE name = ?", (name,))
        row = cursor.fetchone()

        if row:
            # Table existe en SQL
            new_enabled = 0 if row[0] else 1
            cursor.execute(
                "UPDATE ETL_Tables_Config SET enabled = ?, updated_at = GETDATE() WHERE name = ?",
                (new_enabled, name)
            )
            conn.commit()
            cursor.close()
            conn.close()

            invalidate_cache()
            toggle_table_in_agents(name, bool(new_enabled))
            sync_to_yaml()
            return bool(new_enabled)

        cursor.close()
        conn.close()

        # Table pas en SQL, chercher dans YAML
        new_state = _toggle_table_in_yaml(name)
        if new_state is not None:
            invalidate_cache()
            toggle_table_in_agents(name, new_state)
            return new_state

        return None
    except Exception as e:
        logger.error(f"Erreur toggle table {name}: {e}")
        return None


def _toggle_table_in_yaml(name: str) -> Optional[bool]:
    """
    Active/Desactive une table dans le fichier YAML.

    Args:
        name: Nom de la table

    Returns:
        Nouvel etat enabled, ou None si non trouvee
    """
    try:
        if not YAML_CONFIG_PATH.exists():
            return None

        with open(YAML_CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}

        tables = config.get('tables', [])
        found = False
        new_state = None

        for table in tables:
            if table.get('name') == name:
                current_state = table.get('enabled', True)
                new_state = not current_state
                table['enabled'] = new_state
                found = True
                break

        if found:
            with open(YAML_CONFIG_PATH, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            logger.info(f"Table '{name}' {'activee' if new_state else 'desactivee'} dans YAML")
            return new_state

        return None
    except Exception as e:
        logger.error(f"Erreur toggle table {name} dans YAML: {e}")
        return None


def update_global_config(updates: Dict[str, Any]):
    """
    Met a jour la configuration globale.

    Args:
        updates: Champs a mettre a jour
    """
    _ensure_table_exists()
    _init_default_global_config()

    try:
        conn = _get_connection()
        cursor = conn.cursor()

        for key, value in updates.items():
            if value is not None:
                cursor.execute("""
                    UPDATE ETL_Global_Config
                    SET config_value = ?, updated_at = GETDATE()
                    WHERE config_key = ?
                """, (str(value), key))

                # Si pas de ligne affectee, inserer
                if cursor.rowcount == 0:
                    cursor.execute(
                        "INSERT INTO ETL_Global_Config (config_key, config_value) VALUES (?, ?)",
                        (key, str(value))
                    )

        conn.commit()
        cursor.close()
        conn.close()

        invalidate_cache()
    except Exception as e:
        logger.error(f"Erreur mise a jour config globale: {e}")


def get_enabled_tables() -> List[Dict[str, Any]]:
    """
    Retourne uniquement les tables activees.

    Returns:
        Liste des tables avec enabled=True
    """
    tables = get_tables()
    return [t for t in tables if t.get('enabled', True)]


def invalidate_cache():
    """Invalide le cache des fonctions."""
    get_global_config.cache_clear()
    get_tables.cache_clear()


# ============================================================
# Fonctions de synchronisation avec APP_ETL_Agent_Tables
# ============================================================

def _get_all_agents() -> List[str]:
    """Recupere tous les agent_id actifs."""
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT agent_id FROM APP_ETL_Agents WHERE is_active = 1")
        agents = [str(row[0]) for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return agents
    except Exception as e:
        logger.error(f"Erreur recuperation agents: {e}")
        return []


def sync_table_to_agents(table_name: str, table_config: Dict[str, Any]):
    """
    Synchronise une table vers tous les agents actifs (APP_ETL_Agent_Tables).

    Args:
        table_name: Nom de la table
        table_config: Configuration de la table
    """
    agents = _get_all_agents()
    if not agents:
        logger.info("Aucun agent actif pour synchroniser")
        return

    # Extraire les valeurs de la config
    source = table_config.get('source', {})
    target = table_config.get('target', {})

    source_query = source.get('query') or table_config.get('source_query') or ''
    target_table = target.get('table') or table_config.get('target_table') or table_name

    pk = target.get('primary_key') or table_config.get('primary_key', [])
    if isinstance(pk, list):
        primary_key = ','.join(pk)
    else:
        primary_key = pk

    sync_type = table_config.get('sync_type', 'full')
    timestamp_column = table_config.get('timestamp_column', '')
    priority = table_config.get('priority', 'normal')
    enabled = 1 if table_config.get('enabled', True) else 0
    interval_minutes = table_config.get('interval_minutes', 5)
    delete_detection = 1 if table_config.get('delete_detection', False) else 0

    try:
        conn = _get_connection()
        cursor = conn.cursor()

        for agent_id in agents:
            # Verifier si existe deja pour cet agent
            cursor.execute(
                "SELECT id FROM APP_ETL_Agent_Tables WHERE agent_id = ? AND table_name = ?",
                (agent_id, table_name)
            )
            existing = cursor.fetchone()

            if existing:
                # Mettre a jour
                cursor.execute("""
                    UPDATE APP_ETL_Agent_Tables
                    SET source_query = ?, target_table = ?, primary_key_columns = ?,
                        sync_type = ?, timestamp_column = ?, priority = ?,
                        is_enabled = ?, interval_minutes = ?, delete_detection = ?,
                        updated_at = GETDATE()
                    WHERE agent_id = ? AND table_name = ?
                """, (source_query, target_table, primary_key, sync_type,
                      timestamp_column, priority, enabled, interval_minutes, delete_detection,
                      agent_id, table_name))
            else:
                # Inserer
                cursor.execute("""
                    INSERT INTO APP_ETL_Agent_Tables
                    (agent_id, table_name, source_query, target_table, primary_key_columns,
                     sync_type, timestamp_column, priority, is_enabled, interval_minutes,
                     delete_detection, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE())
                """, (agent_id, table_name, source_query, target_table, primary_key,
                      sync_type, timestamp_column, priority, enabled, interval_minutes,
                      delete_detection))

        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"Table '{table_name}' synchronisee vers {len(agents)} agents")
    except Exception as e:
        logger.error(f"Erreur synchronisation table {table_name} vers agents: {e}")


def remove_table_from_agents(table_name: str):
    """
    Supprime une table de tous les agents (APP_ETL_Agent_Tables).

    Args:
        table_name: Nom de la table a supprimer
    """
    try:
        conn = _get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM APP_ETL_Agent_Tables WHERE table_name = ?",
            (table_name,)
        )
        deleted = cursor.rowcount

        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"Table '{table_name}' supprimee de {deleted} enregistrements agents")
    except Exception as e:
        logger.error(f"Erreur suppression table {table_name} des agents: {e}")


def toggle_table_in_agents(table_name: str, enabled: bool):
    """
    Active/Desactive une table pour tous les agents.

    Args:
        table_name: Nom de la table
        enabled: Nouvel etat
    """
    try:
        conn = _get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE APP_ETL_Agent_Tables SET is_enabled = ?, updated_at = GETDATE() WHERE table_name = ?",
            (1 if enabled else 0, table_name)
        )
        updated = cursor.rowcount

        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"Table '{table_name}' {'activee' if enabled else 'desactivee'} pour {updated} agents")
    except Exception as e:
        logger.error(f"Erreur toggle table {table_name} dans agents: {e}")


# ============================================================
# Fonctions de synchronisation avec le fichier YAML
# ============================================================

def sync_to_yaml():
    """
    Exporte toute la configuration ETL vers le fichier YAML.
    DESACTIVE: Ne pas ecraser le YAML quand il est la source principale.
    """
    # Verifier si on est en mode YAML (table SQL vide)
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM ETL_Tables_Config")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()

        # Si moins de 5 tables en SQL, ne pas ecraser le YAML
        # (le YAML est probablement la source principale)
        if count < 5:
            logger.debug("sync_to_yaml ignore: mode YAML actif (peu de tables en SQL)")
            return
    except Exception:
        logger.debug("sync_to_yaml ignore: erreur verification SQL")
        return

    try:
        global_config = get_global_config()
        tables = get_tables()

        # Construire la structure YAML
        yaml_config = {
            'global': global_config,
            'tables': []
        }

        for table in tables:
            yaml_table = {
                'name': table['name'],
                'source': table.get('source', {}),
                'target': table.get('target', {}),
                'sync_type': table.get('sync_type', 'full'),
                'priority': table.get('priority', 'normal'),
                'enabled': table.get('enabled', True),
                'sort_order': table.get('sort_order', 0)
            }

            if table.get('timestamp_column'):
                yaml_table['timestamp_column'] = table['timestamp_column']
            if table.get('description'):
                yaml_table['description'] = table['description']
            if table.get('batch_size'):
                yaml_table['batch_size'] = table['batch_size']

            yaml_config['tables'].append(yaml_table)

        # Ecrire le fichier YAML
        with open(YAML_CONFIG_PATH, 'w', encoding='utf-8') as f:
            yaml.dump(yaml_config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        logger.info(f"Configuration ETL exportee vers {YAML_CONFIG_PATH}")
    except Exception as e:
        logger.error(f"Erreur export YAML: {e}")


def clear_yaml_tables():
    """
    Vide le fichier YAML des tables (garde la config globale).
    Utilise lors de la suppression de toutes les tables pour eviter le rechargement.
    """
    try:
        if not YAML_CONFIG_PATH.exists():
            logger.info("Fichier YAML n'existe pas, rien a vider")
            return

        # Lire le contenu actuel
        with open(YAML_CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}

        # Vider les tables mais garder la config globale
        config['tables'] = []

        # Reecrire le fichier
        with open(YAML_CONFIG_PATH, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        logger.info(f"Tables supprimees du fichier YAML: {YAML_CONFIG_PATH}")
    except Exception as e:
        logger.error(f"Erreur vidage YAML: {e}")
        raise


def migrate_from_yaml(archive_yaml: bool = False) -> Dict[str, Any]:
    """
    Migre les donnees du fichier YAML vers SQL.
    Peut etre executee plusieurs fois - les tables existantes sont ignorees.

    Args:
        archive_yaml: Si True, renomme le YAML apres migration

    Returns:
        Dict avec les stats de migration
    """
    yaml_file = YAML_CONFIG_PATH

    if not yaml_file.exists():
        logger.info("Pas de fichier YAML a migrer")
        return {"success": False, "error": "Fichier YAML non trouve", "migrated": 0, "skipped": 0}

    try:
        with open(yaml_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        if not config:
            return {"success": False, "error": "Fichier YAML vide", "migrated": 0, "skipped": 0}

        # Migrer config globale
        global_config = config.get('global', {})
        if global_config:
            update_global_config(global_config)

        # Migrer tables
        tables = config.get('tables', [])
        migrated = 0
        skipped = 0
        errors = []

        for table in tables:
            # Inclure tous les champs necessaires
            table_config = {
                'name': table.get('name'),
                'source': table.get('source', {}),
                'target': table.get('target', {}),
                'sync_type': table.get('sync_type', 'full'),
                'timestamp_column': table.get('timestamp_column'),
                'priority': table.get('priority', 'normal'),
                'enabled': table.get('enabled', True),
                'description': table.get('description', ''),
                'batch_size': table.get('batch_size', 10000),
                'sort_order': table.get('sort_order', 0)
            }

            if add_table(table_config):
                migrated += 1
                logger.info(f"Table migree: {table.get('name')}")
            else:
                skipped += 1
                logger.debug(f"Table ignoree (deja existante): {table.get('name')}")

        logger.info(f"Migration terminee: {migrated} tables migrees, {skipped} ignorees")

        # Optionnel: renommer le fichier YAML pour archivage
        if archive_yaml and migrated > 0:
            backup_file = yaml_file.with_suffix('.yaml.backup')
            yaml_file.rename(backup_file)
            logger.info(f"Fichier YAML archive: {backup_file}")

        # Invalider le cache
        invalidate_cache()

        return {
            "success": True,
            "migrated": migrated,
            "skipped": skipped,
            "total": len(tables),
            "errors": errors
        }

    except Exception as e:
        logger.error(f"Erreur migration YAML vers SQL: {e}")
        return {"success": False, "error": str(e), "migrated": 0, "skipped": 0}
