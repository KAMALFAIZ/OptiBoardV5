"""
DEPRECIE: Ce module est remplace par tenant_context.py
=======================================================
Redirige vers TenantContextMiddleware pour compatibilite.
"""

import warnings
from .tenant_context import TenantContextMiddleware

# Alias pour compatibilite
ClientContextMiddleware = TenantContextMiddleware

warnings.warn(
    "Le module client_context est deprecie. Utiliser tenant_context.TenantContextMiddleware.",
    DeprecationWarning,
    stacklevel=2
)
