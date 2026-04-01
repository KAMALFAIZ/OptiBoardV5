"""
Service centralisé de vérification des permissions rapports — OptiBoard
========================================================================
Point d'entrée unique pour toute vérification d'accès à un rapport.

Logique métier (par ordre de priorité) :
  1. Pas de user_id fourni          → laisse passer (legacy / appel interne)
  2. Admin global (central)         → accès total
  3. Admin_client (base client)     → accès total
  4. Aucun rôle spécifique assigné  → accès libre (contrôlé côté menu uniquement)
  5. Rôle is_admin=1                → accès total
  6. APP_Role_Reports.can_view=1    → accès au rapport
  7. Sinon                          → HTTP 403

Utilisation :
    from ..services.permissions import enforce_report_access
    enforce_report_access(user_id, 'gridview', grid_id, dwh_code)
"""

from typing import Optional
from fastapi import HTTPException

from ..database_unified import execute_client, execute_central


# ─────────────────────────────────────────────────────────────────────────────
# Fonction interne — renvoie True/False sans lever d'exception
# ─────────────────────────────────────────────────────────────────────────────

def _resolve(user_id: int, report_type: str, report_id: int, dwh_code: Optional[str]) -> bool:
    """
    Retourne True si l'utilisateur est autorisé, False sinon.
    En cas d'erreur technique (table absente, connexion perdue), retourne True
    pour ne pas bloquer les utilisateurs lors d'une indisponibilité partielle.
    """

    # ── 1. Base CLIENT en priorité (role_dwh) ──────────────────────────────
    # IMPORTANT : interroger le CLIENT avant le CENTRAL.
    # La base centrale peut contenir un user avec le même id mais un rôle plus élevé.
    if dwh_code:
        try:
            row = execute_client(
                "SELECT role_dwh FROM APP_Users WHERE id = ?",
                (user_id,), dwh_code=dwh_code, use_cache=False
            )
            if row:
                role = row[0].get('role_dwh', '')
                if role == 'admin_client':
                    return True
                # User trouvé dans le client → on continue avec les rôles spécifiques
                # (ne pas tomber sur la vérification centrale)
            else:
                # User absent de la base client → peut être un admin central
                central_row = execute_central(
                    "SELECT role_global FROM APP_Users WHERE id = ?",
                    (user_id,), use_cache=False
                )
                if central_row and central_row[0].get('role_global') in ('admin', 'superadmin'):
                    return True
                return True  # Inconnu → fail-open
        except Exception:
            pass
    else:
        # Sans DWH → vérification centrale uniquement
        try:
            row = execute_central(
                "SELECT role_global FROM APP_Users WHERE id = ?",
                (user_id,), use_cache=False
            )
            if row and row[0].get('role_global') in ('admin', 'superadmin'):
                return True
        except Exception:
            pass
        return True  # Pas de DWH → fail-open

    # ── 3. Rôles spécifiques (APP_User_Roles) ──────────────────────────────
    try:
        roles = execute_client(
            """SELECT r.id, r.is_admin
               FROM APP_User_Roles ur
               JOIN APP_Roles r ON r.id = ur.role_id
               WHERE ur.user_id = ? AND r.actif = 1""",
            (user_id,), dwh_code=dwh_code, use_cache=False
        )
    except Exception:
        return True  # Table absente → mode legacy, pas de restriction

    # Aucun rôle assigné → accès libre (restriction uniquement via menus)
    if not roles:
        return True

    # Un rôle admin → accès total
    if any(bool(r['is_admin']) for r in roles):
        return True

    # ── 4. Vérification dans APP_Role_Reports ──────────────────────────────
    try:
        role_ids  = [r['id'] for r in roles]
        ph        = ','.join('?' * len(role_ids))
        perm = execute_client(
            f"""SELECT MAX(CAST(can_view AS INT)) AS can_view
                FROM APP_Role_Reports
                WHERE role_id IN ({ph})
                  AND report_type = ?
                  AND report_id   = ?""",
            (*role_ids, report_type, report_id),
            dwh_code=dwh_code, use_cache=False
        )
        return bool(perm and perm[0].get('can_view'))
    except Exception:
        return True  # En cas d'erreur technique → fail-open


# ─────────────────────────────────────────────────────────────────────────────
# API publique — à appeler dans les routes
# ─────────────────────────────────────────────────────────────────────────────

def enforce_report_access(
    user_id:     Optional[int],
    report_type: str,
    report_id:   int,
    dwh_code:    Optional[str] = None
) -> None:
    """
    Lève HTTP 403 si l'utilisateur n'est pas autorisé à voir ce rapport.
    Si user_id est None ou 0, la vérification est ignorée (appel interne).

    Args:
        user_id:     ID de l'utilisateur (depuis header X-User-Id)
        report_type: 'gridview' | 'pivot' | 'dashboard'
        report_id:   ID du rapport
        dwh_code:    Code DWH courant (depuis header X-DWH-Code)

    Raises:
        HTTPException 403 si accès refusé
    """
    if not user_id:
        return  # Pas d'identification → mode legacy, pas de blocage

    if not _resolve(user_id, report_type, report_id, dwh_code):
        raise HTTPException(
            status_code=403,
            detail=f"Accès refusé : vous n'avez pas la permission de consulter ce rapport."
        )
