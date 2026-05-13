# -*- coding: utf-8 -*-
"""
Script de correction de TOUTES les datasources erronées.
Corrige :
1. Ventes CA : [Date] → [Date BL] (tables Lignes_des_ventes)
2. Achats CA : [Date] → [Date BL] + ajout [Valorise CA] = 'Oui' (tables Lignes_des_achats)
3. Listes documents : [Date] → [Date document]
4. NE TOUCHE PAS : Paiements/Règlements (PAF/RGC) qui utilisent [Date] correctement

Usage: python fix_all_datasources.py [--dry-run]
"""

import pyodbc
import re
import sys

CONN_STR = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019"

DRY_RUN = "--dry-run" in sys.argv

# Tables where [Date] is the correct field (don't touch)
TABLES_WITH_CORRECT_DATE = [
    'paiements_fournisseurs',
    'réglements_clients',
    'reglements_clients',
    'ecritures_comptables',
    'etat_stock',
    'échéances_ventes',
    'echeances_ventes',
    'echeances_achats',
    'échéances_achats',
]


def classify_datasource(code, query):
    """Classifie une datasource pour déterminer la correction à appliquer."""
    ql = query.lower()

    # Skip if no [Date] BETWEEN pattern
    if not re.search(r'\[date\]\s*between', ql):
        return None, None

    # Skip if table uses [Date] correctly
    for table in TABLES_WITH_CORRECT_DATE:
        if table in ql:
            return None, None

    # Detect table type
    is_lignes_ventes = 'lignes_des_ventes' in ql
    is_lignes_achats = 'lignes_des_achats' in ql
    is_entete_achats = 'entête_des_achats' in ql or 'entete_des_achats' in ql

    # Document lists: have [Type Document] filter for BL/Facture/BC/Devis
    is_doc_list = bool(re.search(r"\[type\s*document\]", ql)) and any(
        t in ql for t in ["'bon de livraison'", "'facture'", "'bon de commande'", "'devis'",
                          "'facture comptabilis"]
    )

    # CA queries: have SUM(Montant HT) or [Valorise CA]
    is_ca = 'valorise ca' in ql or ('montant ht' in ql and 'sum(' in ql)

    # IMPORTANT: [Date document] only exists in Lignes_des_ventes, NOT in Lignes_des_achats
    # For achats doc lists, [Date] is the correct date field (it IS the document date)

    # Special: if query already uses [Date document] in SELECT, it's a doc list
    has_date_document_ref = 'date document' in ql and 'date document] between' not in ql

    # Special: Devis/BC/Preparation queries are document-based, not CA-based (no Date BL)
    is_devis_or_bc_only = (
        ("'devis'" in ql or "'bon de commande'" in ql or "paration de livraison" in ql)
        and "'bon de livraison'" not in ql
        and "'facture'" not in ql
        and 'valorise ca' not in ql
    )

    if is_doc_list and not is_ca:
        if is_lignes_achats or is_entete_achats:
            return None, None
        return 'doc_list', None
    elif has_date_document_ref and is_lignes_ventes:
        # References [Date document] but filters on [Date] — should be [Date document]
        return 'doc_list', None
    elif is_devis_or_bc_only and is_lignes_ventes:
        # Devis/BC queries (even with SUM) — these have no Date BL
        return 'doc_list', None
    elif is_lignes_achats or is_entete_achats:
        needs_valorise = 'valorise ca' not in ql and is_ca
        return 'achats_ca', needs_valorise
    elif 'ach' in code.lower() and not is_lignes_ventes:
        needs_valorise = 'valorise ca' not in ql and is_ca
        return 'achats_ca', needs_valorise
    elif is_lignes_ventes or is_ca:
        return 'ventes_ca', None
    elif is_doc_list:
        return 'doc_list', None
    else:
        if 'ach' in code.lower():
            return 'achats_ca', 'valorise ca' not in ql
        else:
            return 'ventes_ca', None


def fix_date_ventes_ca(query):
    """Replace [Date] BETWEEN with [Date BL] BETWEEN for ventes CA queries."""
    # Handle aliased: alias.[Date] BETWEEN
    fixed = re.sub(
        r'(\w+\.)\[Date\](\s*BETWEEN)',
        r'\1[Date BL]\2',
        query,
        flags=re.IGNORECASE
    )
    # Handle non-aliased: [Date] BETWEEN
    fixed = re.sub(
        r'(?<!\w\.)\[Date\](\s*BETWEEN)',
        r'[Date BL]\1',
        fixed,
        flags=re.IGNORECASE
    )
    return fixed


def fix_date_doc_list(query):
    """Replace [Date] BETWEEN with [Date document] BETWEEN for document lists."""
    # Handle aliased
    fixed = re.sub(
        r'(\w+\.)\[Date\](\s*BETWEEN)',
        r'\1[Date document]\2',
        query,
        flags=re.IGNORECASE
    )
    # Handle non-aliased
    fixed = re.sub(
        r'(?<!\w\.)\[Date\](\s*BETWEEN)',
        r'[Date document]\1',
        fixed,
        flags=re.IGNORECASE
    )
    return fixed


def fix_date_achats_ca(query, needs_valorise):
    """Replace [Date] with [Date BL] and add [Valorise CA] if missing."""
    # Fix date
    fixed = re.sub(
        r'(\w+\.)\[Date\](\s*BETWEEN)',
        r'\1[Date BL]\2',
        query,
        flags=re.IGNORECASE
    )
    fixed = re.sub(
        r'(?<!\w\.)\[Date\](\s*BETWEEN)',
        r'[Date BL]\1',
        fixed,
        flags=re.IGNORECASE
    )

    # Add [Valorise CA] = 'Oui' if missing
    if needs_valorise:
        # Insert after WHERE clause
        # Pattern: WHERE ... first condition
        # Add [Valorise CA] = 'Oui' AND after WHERE
        where_match = re.search(r'(WHERE\s+)', fixed, re.IGNORECASE)
        if where_match:
            # Check if there's an alias before the columns
            # Find what alias is used (e.g., l., li., etc.)
            alias_match = re.search(r'FROM\s+\[?Lignes_des_achats\]?\s+(\w+)', fixed, re.IGNORECASE)
            if not alias_match:
                alias_match = re.search(r'FROM\s+\[?Entête_des_achats\]?\s+(\w+)', fixed, re.IGNORECASE)

            if alias_match:
                alias = alias_match.group(1)
                valorise_clause = f"{alias}.[Valorise CA] = 'Oui' AND "
            else:
                valorise_clause = "[Valorise CA] = 'Oui' AND "

            pos = where_match.end()
            fixed = fixed[:pos] + valorise_clause + fixed[pos:]

    return fixed


def main():
    conn = pyodbc.connect(CONN_STR, timeout=30)
    cursor = conn.cursor()

    cursor.execute("SELECT id, code, nom, query_template FROM APP_DataSources_Templates WHERE actif = 1 ORDER BY code")
    rows = cursor.fetchall()

    print(f"Total datasources actives: {len(rows)}")
    if DRY_RUN:
        print("=== MODE DRY-RUN (aucune modification) ===\n")

    fixes = {"ventes_ca": 0, "achats_ca": 0, "doc_list": 0, "valorise_added": 0}
    errors = []

    for ds_id, code, nom, query in rows:
        if not query:
            continue

        category, extra = classify_datasource(code, query)
        if category is None:
            continue

        original = query

        if category == 'ventes_ca':
            fixed = fix_date_ventes_ca(query)
            fixes["ventes_ca"] += 1
        elif category == 'doc_list':
            fixed = fix_date_doc_list(query)
            fixes["doc_list"] += 1
        elif category == 'achats_ca':
            fixed = fix_date_achats_ca(query, extra)
            fixes["achats_ca"] += 1
            if extra:
                fixes["valorise_added"] += 1
        else:
            continue

        if fixed == original:
            continue

        if DRY_RUN:
            # Show what would change
            print(f"[{category}] {code}")
            # Show date line changes
            orig_lines = original.split('\n')
            fixed_lines = fixed.split('\n')
            for i, (ol, fl) in enumerate(zip(orig_lines, fixed_lines)):
                if ol != fl:
                    print(f"  - {ol.strip()}")
                    print(f"  + {fl.strip()}")
            if len(fixed_lines) > len(orig_lines):
                for fl in fixed_lines[len(orig_lines):]:
                    print(f"  + {fl.strip()}")
            print()
        else:
            try:
                cursor.execute(
                    "UPDATE APP_DataSources_Templates SET query_template = ? WHERE id = ?",
                    (fixed, ds_id)
                )
            except Exception as e:
                errors.append((code, str(e)))

    if not DRY_RUN:
        conn.commit()

    print(f"\n{'='*50}")
    print(f"RESUME:")
    print(f"  Ventes CA ([Date] -> [Date BL]):       {fixes['ventes_ca']}")
    print(f"  Achats CA ([Date] -> [Date BL]):       {fixes['achats_ca']}")
    print(f"  Documents ([Date] -> [Date document]): {fixes['doc_list']}")
    print(f"  [Valorise CA] ajoute:                  {fixes['valorise_added']}")
    print(f"  TOTAL corrigees:                       {fixes['ventes_ca'] + fixes['achats_ca'] + fixes['doc_list']}")

    if errors:
        print(f"\n  ERREURS: {len(errors)}")
        for code, err in errors:
            print(f"    {code}: {err}")

    if DRY_RUN:
        print(f"\n>>> Relancer sans --dry-run pour appliquer les corrections")
    else:
        print(f"\n>>> Corrections appliquées en base avec succès!")

    conn.close()


if __name__ == "__main__":
    main()
