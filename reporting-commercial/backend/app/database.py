"""
DEPRECIE: Ce module est remplace par database_unified.py
==========================================================
Toutes les fonctions sont des shims qui redirigent vers database_unified.

Migration:
- execute_query()         → execute_app() ou execute_central()
- execute_master_query()  → execute_central()
- get_connection()        → get_central_connection()
- get_master_connection() → get_central_connection()
- get_db_cursor()         → app_cursor() ou central_cursor()
- get_master_cursor()     → central_cursor()
- DWHConnectionManager    → DWHConnectionManager (meme nom)
- test_connection()       → test_central_connection()
"""

import warnings

# Re-exporter tout depuis database_unified pour compatibilite
from .database_unified import (
    # Exceptions
    DatabaseNotConfiguredError,
    DWHNotFoundError,

    # Contexte tenant (ancienne API)
    set_current_dwh_code,
    get_current_dwh_code,

    # Connexions (shims deprecies)
    get_connection,
    get_master_connection,

    # Cursors (shims deprecies)
    get_db_cursor,
    get_master_cursor,

    # Requetes (shims deprecies)
    execute_query,
    execute_master_query,
    execute_query_df,
    test_connection,

    # DWH Manager (compatibilite)
    DWHConnectionManager,
    dwh_manager,
)

warnings.warn(
    "Le module app.database est deprecie. Importer depuis app.database_unified.",
    DeprecationWarning,
    stacklevel=2
)
