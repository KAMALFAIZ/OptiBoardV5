"""
DEPRECIE: Ce module est remplace par database_unified.py
==========================================================
Toutes les fonctions sont des shims qui redirigent vers database_unified.

Migration:
- execute_central_query()  → execute_central()
- execute_central_write()  → write_central()
- execute_dwh_query()      → execute_dwh(query, params, dwh_code=code)
- execute_dwh_write()      → write_dwh(query, params, dwh_code=code)
- execute_client_query()   → execute_client(query, params, dwh_code=code)
- execute_client_write()   → write_client(query, params, dwh_code=code)
- execute_app_query()      → execute_app(query, params, dwh_code=code)
- execute_app_write()      → write_app(query, params, dwh_code=code)
"""

import warnings

# Re-exporter tout depuis database_unified pour compatibilite
from .database_unified import (
    # Exceptions
    DatabaseNotConfiguredError,
    DWHNotFoundError,
    ClientDBNotFoundError,
    TenantContextError,

    # Connexions
    get_central_connection,
    central_cursor,
    dwh_cursor,
    client_cursor,
    app_cursor,

    # Requetes centrales (shims)
    execute_central_query,
    execute_central_write,
    test_central_connection,

    # Requetes DWH (shims)
    execute_dwh_query,
    execute_dwh_write,
    execute_dwh_query_df,
    test_dwh_connection,

    # Requetes client (shims)
    execute_client_query,
    execute_client_write,

    # Requetes app (shims)
    execute_app_query,
    execute_app_write,

    # Requetes contextuelles (shim)
    execute_query_with_context,
    build_societe_filter,

    # Managers
    DWHConnectionPool,
    dwh_pool,
    ClientConnectionManager,
    client_manager,

    # Utilitaires
    get_user_dwh_list,
    get_user_societes,
    get_all_dwh_societes,
    get_dwh_info,
    create_user_context,

    # Config
    UserContext,
)

# Re-exporter get_connection et execute_query pour la compat totale
from .database_unified import (
    get_connection,
    get_db_cursor,
    execute_query,
)

warnings.warn(
    "Le module app.database_multitenant est deprecie. Importer depuis app.database_unified.",
    DeprecationWarning,
    stacklevel=2
)
