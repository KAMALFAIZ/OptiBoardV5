# -*- coding: utf-8 -*-
"""
Ajoute Cout Revient, Marge Brute, Taux Marge % aux datasources CA qui ne les ont pas.
Cible : datasources avec SUM([Montant HT Net]) sur Lignes_des_ventes ou Lignes_des_achats.

Usage: python fix_add_marge.py [--dry-run]
"""

import pyodbc
import re
import sys

CONN_STR = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019"
DRY_RUN = "--dry-run" in sys.argv

# Datasources to SKIP (special logic, already correct, or don't need marge)
SKIP_CODES = {
    # Devis/BC/Taux — no CMUP for these document types
    'DS_TAUX_TRANSFORMATION',
    'DS_VTE_PERF_DEVIS',
    'DS_VTE_TAUX_SERVICE',
    # Already have marge with different naming
    'DS_VENTES_GLOBAL',
    'DS_VENTES_PAR_CLIENT',
    'DS_VENTES_PAR_ARTICLE',
    'DS_VENTES_PAR_COMMERCIAL',
    'DS_VENTES_PAR_CATALOGUE',
    'DS_VENTES_PAR_MOIS',
    'DS_VENTES_PAR_DEPOT',
    'DS_VENTES_PAR_CANAL',
    'DS_VENTES_PAR_AFFAIRE',
    'DS_VENTES_DETAIL',
    # Client analysis — don't aggregate marge meaningfully
    'DS_CLIENTS_NOUVEAUX',
    'DS_CLIENTS_PERDUS',
    'DS_VTE_CHURN',
    'DS_VTE_CLIENTS_INACTIFS',
    'DS_VTE_FIDELITE',
    'DS_COM_FIDELITE',
    'DS_COM_RFM',
    'DS_VTE_RFM',
}


def needs_marge(code, query):
    """Determine if datasource needs marge columns added."""
    if code in SKIP_CODES:
        return False
    ql = query.lower()
    # Must have SUM of Montant HT
    if 'sum(' not in ql or 'montant ht' not in ql:
        return False
    # Must be from a table with CMUP
    if 'lignes_des_ventes' not in ql and 'lignes_des_achats' not in ql:
        return False
    # Must NOT already have marge
    if 'marge' in ql or 'cout revient' in ql or 'prix de revient' in ql:
        return False
    return True


def detect_alias(query):
    """Detect the main table alias by looking at column prefixes in the SELECT."""
    # Strategy: look at what prefix is used in SUM(...[Montant HT Net])
    m = re.search(r'SUM\(\s*(\w+)\.\[Montant HT', query, re.IGNORECASE)
    if m:
        return m.group(1) + "."

    # Fallback: look at FROM Lignes_des_* alias (main, not in subquery)
    # The main FROM is typically after the last closing ) in the SELECT list or standalone
    lines = query.split('\n')
    for line in lines:
        m = re.match(r'\s*FROM\s+\[?Lignes_des_(?:ventes|achats)\]?\s+(\w+)', line, re.IGNORECASE)
        if m and m.group(1).lower() not in ('where', 'inner', 'left', 'on'):
            return m.group(1) + "."

    return ""


def find_last_sum_line(query):
    """Find the position after the last SUM(...) AS [...] line in SELECT."""
    lines = query.split('\n')
    last_sum_idx = -1
    for i, line in enumerate(lines):
        if re.search(r'SUM\(|COUNT\(|AVG\(|MIN\(|MAX\(', line, re.IGNORECASE):
            if 'AS [' in line or 'AS [' in line.replace('as [', 'AS ['):
                last_sum_idx = i

    # Also look for the last aggregate column (could be COUNT DISTINCT, etc.)
    for i, line in enumerate(lines):
        ll = line.lower()
        if ('as [' in ll or 'as [' in ll) and ('sum(' in ll or 'count(' in ll or 'avg(' in ll):
            last_sum_idx = max(last_sum_idx, i)

    return last_sum_idx


def add_marge_columns(query, alias):
    """Insert marge columns after the last aggregate column in SELECT."""
    lines = query.split('\n')
    last_agg_idx = find_last_sum_line(query)

    if last_agg_idx == -1:
        return None  # Can't find where to insert

    # Determine the quantite field name
    # Check if query uses [Quantite] or [Quantité]
    if '[Quantit\xe9]' in query:
        qte_field = '[Quantit\xe9]'
    elif '[Quantite]' in query:
        qte_field = '[Quantite]'
    else:
        qte_field = '[Quantit\xe9]'

    # Build marge columns with proper alias
    a = alias  # e.g., "li." or ""

    marge_lines = [
        f"                SUM(ISNULL({a}[CMUP], 0) * {a}{qte_field}) AS [Cout Revient],",
        f"                SUM({a}[Montant HT Net]) - SUM(ISNULL({a}[CMUP], 0) * {a}{qte_field}) AS [Marge Brute],",
        f"                CASE WHEN SUM({a}[Montant HT Net]) <> 0",
        f"                    THEN ROUND((SUM({a}[Montant HT Net]) - SUM(ISNULL({a}[CMUP], 0) * {a}{qte_field})) * 100.0 / SUM({a}[Montant HT Net]), 2)",
        f"                    ELSE 0 END AS [Taux Marge %],",
    ]

    # Detect indentation from the last aggregate line
    last_line = lines[last_agg_idx]
    indent_match = re.match(r'^(\s*)', last_line)
    indent = indent_match.group(1) if indent_match else "                "

    # Re-indent marge lines
    marge_lines = [indent + line.strip() for line in marge_lines]

    # Ensure the last aggregate line ends with a comma
    if not lines[last_agg_idx].rstrip().endswith(','):
        lines[last_agg_idx] = lines[last_agg_idx].rstrip() + ','

    # Insert marge lines after last aggregate
    for i, ml in enumerate(marge_lines):
        lines.insert(last_agg_idx + 1 + i, ml)

    # The last marge line has a trailing comma — check if the next line after insertion
    # is FROM or GROUP BY (no comma needed on last inserted line)
    next_line_idx = last_agg_idx + 1 + len(marge_lines)
    if next_line_idx < len(lines):
        next_line = lines[next_line_idx].strip().lower()
        if next_line.startswith('from') or next_line.startswith('group') or next_line == '':
            # Remove trailing comma from last marge line
            lines[next_line_idx - 1] = lines[next_line_idx - 1].rstrip().rstrip(',')

    return '\n'.join(lines)


def main():
    conn = pyodbc.connect(CONN_STR, timeout=30)
    cursor = conn.cursor()

    cursor.execute("SELECT id, code, nom, query_template FROM APP_DataSources_Templates WHERE actif = 1 ORDER BY code")
    rows = cursor.fetchall()

    print(f"Total datasources: {len(rows)}")
    if DRY_RUN:
        print("=== MODE DRY-RUN ===\n")

    fixed = 0
    skipped = 0
    errors = []

    for ds_id, code, nom, query in rows:
        if not query:
            continue
        if not needs_marge(code, query):
            continue

        alias = detect_alias(query)
        result = add_marge_columns(query, alias)

        if result is None:
            skipped += 1
            continue

        if DRY_RUN:
            print(f"[+] {code} (alias='{alias}')")
            orig_lines = set(query.split('\n'))
            for line in result.split('\n'):
                if line not in orig_lines:
                    print(f"    + {line.strip()}")
            print()
            fixed += 1
        else:
            try:
                cursor.execute(
                    "UPDATE APP_DataSources_Templates SET query_template = ? WHERE id = ?",
                    (result, ds_id)
                )
                fixed += 1
            except Exception as e:
                errors.append((code, str(e)[:100]))

    if not DRY_RUN:
        conn.commit()

    print(f"\n{'='*50}")
    print(f"RESUME: {fixed} datasources enrichies avec Cout Revient / Marge Brute / Taux Marge %")
    if skipped:
        print(f"  {skipped} skipped (impossible de localiser le point d'insertion)")
    if errors:
        print(f"  {len(errors)} erreurs:")
        for code, err in errors:
            print(f"    {code}: {err}")

    if DRY_RUN:
        print("\n>>> Relancer sans --dry-run pour appliquer")
    else:
        print("\n>>> Corrections appliquees!")

    conn.close()


if __name__ == "__main__":
    main()
