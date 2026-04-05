"""
Sage View Config — Store en base de données
============================================
Gère la persistance des mappings Sage Direct dans APP_Sage_View_Config.
Remplace/complète le fichier config.py statique.

Les mappings peuvent être édités via l'interface admin
(/api/admin/sage-config).
"""

import logging
from typing import Dict, Any, List, Optional
from threading import RLock

from ..database_unified import execute_central, write_central
from .config import SAGE_VIEW_CONFIG as _STATIC_CONFIG

logger = logging.getLogger(__name__)

# Cache en mémoire (invalidé après chaque modif)
_cache: Optional[Dict[str, Dict[str, Any]]] = None
_cache_lock = RLock()


def init_sage_config_table():
    """Crée la table APP_Sage_View_Config si elle n'existe pas + seed initial."""
    try:
        write_central("""
            IF NOT EXISTS (
                SELECT 1 FROM sysobjects
                WHERE name='APP_Sage_View_Config' AND xtype='U'
            )
            CREATE TABLE APP_Sage_View_Config (
                id              INT IDENTITY(1,1) PRIMARY KEY,
                table_name      NVARCHAR(100) NOT NULL UNIQUE,
                sage_sql        NVARCHAR(MAX) NOT NULL,
                is_stub         BIT NOT NULL DEFAULT 0,
                actif           BIT NOT NULL DEFAULT 1,
                description     NVARCHAR(500) NULL,
                created_at      DATETIME NOT NULL DEFAULT GETDATE(),
                updated_at      DATETIME NOT NULL DEFAULT GETDATE()
            )
        """)

        # Seed initial : importer config.py si la table est vide
        existing = execute_central(
            "SELECT COUNT(*) AS nb FROM APP_Sage_View_Config",
            use_cache=False,
        )
        count = existing[0]["nb"] if existing else 0
        if count == 0:
            logger.info("[SAGE CONFIG] Seed initial depuis config.py")
            for table_name, cfg in _STATIC_CONFIG.items():
                write_central(
                    """
                    INSERT INTO APP_Sage_View_Config
                        (table_name, sage_sql, is_stub, actif)
                    VALUES (?, ?, ?, 1)
                    """,
                    (
                        table_name,
                        cfg.get("sage_sql", "").strip(),
                        1 if cfg.get("stub") else 0,
                    ),
                )
            logger.info(
                f"[SAGE CONFIG] {len(_STATIC_CONFIG)} mappings initialisés"
            )
        return True
    except Exception as e:
        logger.error(f"[SAGE CONFIG] Erreur init table: {e}")
        return False


def invalidate_cache():
    """Vide le cache mémoire (à appeler après chaque modif)."""
    global _cache
    with _cache_lock:
        _cache = None


def get_all_mappings() -> Dict[str, Dict[str, Any]]:
    """
    Retourne tous les mappings actifs depuis la BD.
    Utilise un cache mémoire pour éviter les requêtes répétées.
    """
    global _cache
    with _cache_lock:
        if _cache is not None:
            return _cache

        try:
            rows = execute_central(
                """
                SELECT table_name, sage_sql, is_stub, actif, description
                FROM APP_Sage_View_Config
                WHERE actif = 1
                """,
                use_cache=False,
            )
            result = {}
            for row in rows:
                entry = {"sage_sql": row["sage_sql"]}
                if row.get("is_stub"):
                    entry["stub"] = True
                result[row["table_name"]] = entry
            _cache = result
            return result
        except Exception as e:
            logger.error(
                f"[SAGE CONFIG] Erreur lecture BD, fallback config.py: {e}"
            )
            # Fallback sur config.py statique en cas de problème BD
            return _STATIC_CONFIG


def get_known_tables() -> set:
    """Retourne l'ensemble des noms de tables connues (actives)."""
    return set(get_all_mappings().keys())


def list_all(include_inactive: bool = True) -> List[Dict[str, Any]]:
    """Liste complète pour l'admin UI (inclus inactifs)."""
    where = "" if include_inactive else "WHERE actif = 1"
    return execute_central(
        f"""
        SELECT id, table_name, sage_sql, is_stub, actif, description,
               created_at, updated_at
        FROM APP_Sage_View_Config
        {where}
        ORDER BY table_name
        """,
        use_cache=False,
    )


def get_one(mapping_id: int) -> Optional[Dict[str, Any]]:
    """Récupère un mapping par son ID."""
    rows = execute_central(
        """
        SELECT id, table_name, sage_sql, is_stub, actif, description,
               created_at, updated_at
        FROM APP_Sage_View_Config
        WHERE id = ?
        """,
        (mapping_id,),
        use_cache=False,
    )
    return rows[0] if rows else None


def create_mapping(
    table_name: str,
    sage_sql: str,
    is_stub: bool = False,
    description: Optional[str] = None,
) -> int:
    """Crée un nouveau mapping. Retourne l'ID inséré."""
    write_central(
        """
        INSERT INTO APP_Sage_View_Config
            (table_name, sage_sql, is_stub, actif, description)
        VALUES (?, ?, ?, 1, ?)
        """,
        (table_name, sage_sql, 1 if is_stub else 0, description),
    )
    rows = execute_central(
        "SELECT id FROM APP_Sage_View_Config WHERE table_name = ?",
        (table_name,),
        use_cache=False,
    )
    invalidate_cache()
    return rows[0]["id"] if rows else 0


def update_mapping(
    mapping_id: int,
    table_name: Optional[str] = None,
    sage_sql: Optional[str] = None,
    is_stub: Optional[bool] = None,
    actif: Optional[bool] = None,
    description: Optional[str] = None,
) -> bool:
    """Met à jour un mapping existant."""
    updates = []
    params = []
    if table_name is not None:
        updates.append("table_name = ?")
        params.append(table_name)
    if sage_sql is not None:
        updates.append("sage_sql = ?")
        params.append(sage_sql)
    if is_stub is not None:
        updates.append("is_stub = ?")
        params.append(1 if is_stub else 0)
    if actif is not None:
        updates.append("actif = ?")
        params.append(1 if actif else 0)
    if description is not None:
        updates.append("description = ?")
        params.append(description)

    if not updates:
        return False

    updates.append("updated_at = GETDATE()")
    params.append(mapping_id)

    write_central(
        f"UPDATE APP_Sage_View_Config SET {', '.join(updates)} WHERE id = ?",
        tuple(params),
    )
    invalidate_cache()
    return True


def delete_mapping(mapping_id: int) -> bool:
    """Supprime (hard delete) un mapping."""
    write_central(
        "DELETE FROM APP_Sage_View_Config WHERE id = ?",
        (mapping_id,),
    )
    invalidate_cache()
    return True


def reset_to_static_config() -> int:
    """
    Réinitialise la table depuis config.py (remplace tous les mappings).
    Retourne le nombre de mappings restaurés.
    """
    write_central("DELETE FROM APP_Sage_View_Config")
    for table_name, cfg in _STATIC_CONFIG.items():
        write_central(
            """
            INSERT INTO APP_Sage_View_Config
                (table_name, sage_sql, is_stub, actif)
            VALUES (?, ?, ?, 1)
            """,
            (
                table_name,
                cfg.get("sage_sql", "").strip(),
                1 if cfg.get("stub") else 0,
            ),
        )
    invalidate_cache()
    return len(_STATIC_CONFIG)
