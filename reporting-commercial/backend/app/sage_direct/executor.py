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
from . import db_store

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
    Matching insensible à la casse.
    """
    found = set()
    # Map case-insensitive name -> nom exact (PascalCase) du config
    known_tables = db_store.get_known_tables()
    known_lower = {t.lower(): t for t in known_tables}

    # Pattern 1: [dbo].[TableName] ou [schema].[TableName]
    for match in re.finditer(r'\[[^\]]+\]\.\[([^\]]+)\]', query):
        name = match.group(1).lower()
        if name in known_lower:
            found.add(known_lower[name])

    # Pattern 2: FROM/JOIN TableName (avec ou sans crochets)
    for match in re.finditer(r'(?:FROM|JOIN)\s+\[?(\w+)\]?', query, re.IGNORECASE):
        name = match.group(1).lower()
        if name in known_lower:
            found.add(known_lower[name])

    return list(found)


def _build_cte(table_name: str, societes: List[Dict[str, Any]]) -> str:
    """
    Construit une CTE UNION ALL pour une table donnée,
    en combinant toutes les sociétés sur le même serveur.
    """
    config = db_store.get_all_mappings().get(table_name)
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
    - Remplace [schema].[TableName] (toutes casses) par TableName (nom CTE)
    - Remplace FROM/JOIN TableName (avec ou sans crochets)
    - Gère le cas où la requête commence déjà par WITH
    """
    rewritten = query
    for table in tables:
        # Remplacer [schema].[TableName] insensible à la casse
        rewritten = re.sub(
            rf'\[[^\]]+\]\.\[{re.escape(table)}\]',
            table,
            rewritten,
            flags=re.IGNORECASE,
        )
        # Remplacer [TableName] tout seul (insensible casse)
        rewritten = re.sub(
            rf'(?<![\w\.])\[{re.escape(table)}\](?!\.)',
            table,
            rewritten,
            flags=re.IGNORECASE,
        )
        # Remplacer TableName sans crochets après FROM/JOIN
        rewritten = re.sub(
            rf'((?:FROM|JOIN)\s+){re.escape(table)}\b',
            rf'\1{table}',
            rewritten,
            flags=re.IGNORECASE,
        )

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

    # DEBUG fichier
    def _dbg(msg):
        try:
            with open("D:/kasoft-platform/OptiBoard/reporting-commercial/backend/sage_debug.log", "a", encoding="utf-8") as _f:
                _f.write(f"[EXECUTOR] {msg}\n")
        except Exception:
            pass
    _dbg(f"START dwh_code={code}")
    _dbg(f"query[:400]={query[:400]}")

    # 1. Détecter les tables utilisées
    tables = _detect_tables(query)
    _dbg(f"detected tables={tables}")
    if not tables:
        logger.warning(
            f"[SAGE DIRECT] Aucune table DWH détectée dans la requête, "
            f"impossible de router vers Sage"
        )
        return []

    # Détecter les tables référencées mais NON mappées (qui feraient échouer la requête sur Sage)
    # On ne cherche QU'après FROM/JOIN pour éviter les faux positifs (colonnes [Table].[Col])
    referenced_all = set()
    # Pattern 1: FROM/JOIN [schema].[table]  -> group(2) = table
    for m in re.finditer(r'(?:FROM|JOIN)\s+\[([^\]]+)\]\.\[([^\]]+)\]', query, re.IGNORECASE):
        referenced_all.add(m.group(2))
    # Pattern 2: FROM/JOIN [table_avec_espaces_ou_special]
    for m in re.finditer(r'(?:FROM|JOIN)\s+\[([^\]]+)\]', query, re.IGNORECASE):
        name = m.group(1)
        if '.' not in name:  # déjà traité par pattern 1
            referenced_all.add(name)
    # Pattern 3: FROM/JOIN word_simple (sans crochets)
    for m in re.finditer(r'(?:FROM|JOIN)\s+(\w+)\b', query, re.IGNORECASE):
        referenced_all.add(m.group(1))
    known_lower = {t.lower(): t for t in db_store.get_known_tables()}
    unmapped = []
    for ref in referenced_all:
        if ref.lower() in known_lower:
            continue
        # Ignorer les tables Sage natives (F_xxx, P_xxx, T_xxx) et aliases courts
        if re.match(r'^(F_|P_|T_|CT_|#)', ref, re.IGNORECASE):
            continue
        if len(ref) <= 2:  # alias SQL (li, en, etc.)
            continue
        # Ignorer mots-clés SQL courants
        if ref.upper() in ('SELECT', 'WHERE', 'INNER', 'LEFT', 'RIGHT', 'OUTER',
                           'ON', 'AND', 'OR', 'AS', 'GROUP', 'ORDER', 'BY', 'HAVING'):
            continue
        # Table style DWH (PascalCase ou avec _) non trouvée dans les mappings
        if '_' in ref or (ref and ref[0].isupper()):
            unmapped.append(ref)
    if unmapped:
        _dbg(f"unmapped tables detected: {unmapped}")
        raise RuntimeError(
            f"Tables référencées mais non mappées en Sage Direct: {', '.join(unmapped)}. "
            f"Ajoutez un mapping dans la configuration Sage pour activer cette requête."
        )

    # Vérifier si toutes les tables sont des stubs
    _mappings = db_store.get_all_mappings()
    all_stubs = all(
        _mappings.get(t, {}).get('stub', False) for t in tables
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

    _dbg(f"final_sql FULL=\n{final_sql}")
    _dbg(f"params={params}")

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

        # Debug: si 0 rows, faire un diagnostic automatique
        if len(results) == 0:
            _dbg("=== DIAGNOSTIC 0 rows ===")
            try:
                # Test 1: combien de factures existent dans Sage (ignore filtres)?
                diag_sql = f"""SELECT COUNT(*) as nb FROM [{same_server[0]['base_sage']}].[dbo].[F_DOCLIGNE] WHERE DO_Domaine=0 AND DO_Type IN (6,7)"""
                cursor.execute(diag_sql)
                nb_fact = cursor.fetchone()[0]
                _dbg(f"Nb lignes de factures (DO_Type 6/7) dans Sage: {nb_fact}")
                # Test 2: min/max dates documents
                diag_sql2 = f"""SELECT MIN(DO_Date) as min_dt, MAX(DO_Date) as max_dt FROM [{same_server[0]['base_sage']}].[dbo].[F_DOCENTETE] WHERE DO_Domaine=0 AND DO_Type IN (6,7)"""
                cursor.execute(diag_sql2)
                row = cursor.fetchone()
                _dbg(f"Dates factures: min={row[0]} max={row[1]}")
            except Exception as diag_err:
                _dbg(f"diagnostic error: {diag_err}")

        logger.info(
            f"[SAGE DIRECT] OK — {len(results)} rows, "
            f"tables={tables}, societes={[s['code_societe'] for s in same_server]}"
        )
        _dbg(f"OK rows={len(results)} columns={columns}")
        return results

    except Exception as e:
        logger.error(f"[SAGE DIRECT] Erreur exécution: {e}")
        _dbg(f"EXCEPTION: {e}")
        logger.debug(f"[SAGE DIRECT] SQL:\n{final_sql[:500]}...")
        raise
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
