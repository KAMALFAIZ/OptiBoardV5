"""
Sage Direct Executor
=====================
Exécute les requêtes rapport directement sur les bases Sage
en utilisant des CTEs qui reproduisent les vues DWH.

Aucune écriture — connexion fermée après chaque requête.
"""

import re
import logging
import pyodbc
from datetime import date, datetime
from typing import Optional, List, Dict, Any, Tuple

from ..database_unified import execute_central, require_dwh_code
from .config import SAGE_VIEW_CONFIG, KNOWN_TABLES

logger = logging.getLogger(__name__)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_sage_societes(dwh_code: str) -> List[Dict[str, Any]]:
    """Récupère toutes les sociétés Sage actives pour ce DWH."""
    return execute_central(
        """
        SELECT code_societe, nom_societe, serveur_sage, base_sage,
               user_sage, password_sage
        FROM APP_DWH_Sources
        WHERE dwh_code = ? AND actif = 1
          AND serveur_sage IS NOT NULL AND serveur_sage <> ''
          AND base_sage IS NOT NULL AND base_sage <> ''
        ORDER BY code_societe
        """,
        (dwh_code,),
        use_cache=False,
    )


def _open_sage_connection(societe: Dict[str, Any]) -> pyodbc.Connection:
    """Ouvre une connexion vers le serveur Sage d'une société."""
    user = (societe.get('user_sage') or '').strip()
    pwd = (societe.get('password_sage') or '').strip()

    if user:
        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={societe['serveur_sage']};"
            f"DATABASE={societe['base_sage']};"
            f"UID={user};PWD={pwd};"
            f"TrustServerCertificate=yes;Connection Timeout=15;"
        )
    else:
        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={societe['serveur_sage']};"
            f"DATABASE={societe['base_sage']};"
            f"Trusted_Connection=yes;"
            f"TrustServerCertificate=yes;Connection Timeout=15;"
        )
    return pyodbc.connect(conn_str)


def _detect_tables(query: str) -> List[str]:
    """
    Détecte les tables DWH référencées dans la requête SQL.
    Cherche les patterns [dbo].[TableName] et FROM TableName.
    """
    found = set()

    # Pattern 1: [dbo].[TableName]
    for match in re.finditer(r'\[dbo\]\.\[([^\]]+)\]', query):
        name = match.group(1)
        if name in KNOWN_TABLES:
            found.add(name)

    # Pattern 2: FROM/JOIN TableName (sans [dbo])
    for match in re.finditer(r'(?:FROM|JOIN)\s+(\w+)', query, re.IGNORECASE):
        name = match.group(1)
        if name in KNOWN_TABLES:
            found.add(name)

    return list(found)


def _build_cte(table_name: str, societes: List[Dict[str, Any]]) -> str:
    """
    Construit une CTE UNION ALL pour une table donnée,
    en combinant toutes les sociétés sur le même serveur.
    """
    config = SAGE_VIEW_CONFIG.get(table_name)
    if not config:
        return ""

    sage_sql_template = config["sage_sql"]
    parts = []

    for societe in societes:
        part = sage_sql_template.format(
            db=societe['base_sage'],
            societe=societe['code_societe'],
        )
        parts.append(part)

    return f"{table_name} AS (\n" + "\nUNION ALL\n".join(parts) + "\n)"


def _rewrite_query(query: str, tables: List[str]) -> str:
    """
    Réécrit la requête SQL :
    - Remplace [dbo].[TableName] par TableName (nom CTE)
    - Gère le cas où la requête commence déjà par WITH
    """
    rewritten = query
    for table in tables:
        # Remplacer [dbo].[TableName] par le nom CTE
        rewritten = rewritten.replace(f'[dbo].[{table}]', table)

    return rewritten


def _serialize_value(val):
    """Convertit les types non-JSON en types sérialisables."""
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    if isinstance(val, bytes):
        return val.hex()
    return val


# ─── Exécuteur principal ──────────────────────────────────────────────────────

def execute_sage_direct(
    query: str,
    params: Optional[tuple] = None,
    dwh_code: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Exécute une requête rapport directement sur Sage.

    1. Détecte les tables DWH dans la requête
    2. Construit des CTEs Sage équivalentes (UNION ALL multi-sociétés)
    3. Réécrit la requête pour utiliser les CTEs
    4. Exécute sur une connexion Sage temporaire
    5. Retourne les résultats au même format que execute_app()

    Si aucune table DWH n'est détectée, retourne une liste vide.
    """
    code = dwh_code or require_dwh_code()

    # 1. Détecter les tables utilisées
    tables = _detect_tables(query)
    if not tables:
        logger.warning(
            f"[SAGE DIRECT] Aucune table DWH détectée dans la requête, "
            f"impossible de router vers Sage"
        )
        return []

    # Vérifier si toutes les tables sont des stubs
    all_stubs = all(
        SAGE_VIEW_CONFIG.get(t, {}).get('stub', False) for t in tables
    )
    if all_stubs:
        logger.info(
            f"[SAGE DIRECT] Tables {tables} non supportées en mode Sage Direct"
        )
        return []

    # 2. Récupérer les sociétés Sage
    societes = _get_sage_societes(code)
    if not societes:
        logger.error(f"[SAGE DIRECT] Aucune source Sage active pour DWH '{code}'")
        return []

    # 3. Grouper par serveur (pour le UNION ALL cross-database)
    # Phase 1 : on utilise le premier serveur uniquement
    primary_server = societes[0]['serveur_sage']
    same_server = [s for s in societes if s['serveur_sage'] == primary_server]

    if len(same_server) < len(societes):
        logger.warning(
            f"[SAGE DIRECT] {len(societes) - len(same_server)} sociétés sur "
            f"d'autres serveurs ignorées (multi-serveur non supporté en Phase 1)"
        )

    # 4. Construire les CTEs
    cte_parts = []
    for table in tables:
        cte = _build_cte(table, same_server)
        if cte:
            cte_parts.append(cte)

    if not cte_parts:
        return []

    # 5. Réécrire la requête
    rewritten = _rewrite_query(query, tables)

    # Gérer le cas CTE existant dans la requête originale
    stripped = rewritten.strip()
    if stripped.upper().startswith('WITH '):
        # La requête a déjà un WITH — on enlève le WITH et on chaîne
        rewritten = stripped[4:].strip()  # enlever "WITH"
        final_sql = "WITH " + ",\n".join(cte_parts) + ",\n" + rewritten
    else:
        final_sql = "WITH " + ",\n".join(cte_parts) + "\n" + rewritten

    # Préfixe SQL (même que DWH)
    prefix = "SET DATEFORMAT YMD; SET ANSI_WARNINGS OFF; SET ARITHABORT OFF;\n"
    final_sql = prefix + final_sql

    # 6. Exécuter sur le serveur Sage
    conn = None
    try:
        conn = _open_sage_connection(same_server[0])
        cursor = conn.cursor()

        if params:
            cursor.execute(final_sql, params)
        else:
            cursor.execute(final_sql)

        if cursor.description is None:
            return []

        columns = [col[0] for col in cursor.description]
        results = []
        for row in cursor.fetchall():
            d = {}
            for col_name, val in zip(columns, row):
                d[col_name] = _serialize_value(val)
            results.append(d)

        logger.info(
            f"[SAGE DIRECT] OK — {len(results)} rows, "
            f"tables={tables}, societes={[s['code_societe'] for s in same_server]}"
        )
        return results

    except Exception as e:
        logger.error(f"[SAGE DIRECT] Erreur exécution: {e}")
        logger.debug(f"[SAGE DIRECT] SQL:\n{final_sql[:500]}...")
        raise
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
