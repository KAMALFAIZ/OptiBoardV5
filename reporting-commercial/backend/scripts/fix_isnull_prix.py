# -*- coding: utf-8 -*-
"""
Ajoute ISNULL([CMUP], 0) partout ou [CMUP] est utilise
dans un calcul (multiplication, soustraction) sans ISNULL.

Usage: python fix_isnull_prix.py [--dry-run]
"""
import pyodbc
import re
import sys

CONN_STR = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019"
DRY_RUN = "--dry-run" in sys.argv


def fix_prix_revient_isnull(query):
    """Wrap all [CMUP] in ISNULL(..., 0) when used in calculations."""

    # Pattern 1: alias.[CMUP] * something (not already in ISNULL)
    fixed = re.sub(
        r'(?<!ISNULL\()(\w+\.\[CMUP\])(\s*\*)',
        r'ISNULL(\1, 0)\2',
        query
    )

    # Pattern 2: something * alias.[CMUP] (not already in ISNULL)
    fixed = re.sub(
        r'(\*\s*)(?<!ISNULL\()(\w+\.\[CMUP\])(?!\s*,\s*0\))',
        r'\1ISNULL(\2, 0)',
        fixed
    )

    # Pattern 3: non-aliased [CMUP] * something
    fixed = re.sub(
        r'(?<!ISNULL\()(?<!\w\.)(\[CMUP\])(\s*\*)',
        r'ISNULL(\1, 0)\2',
        fixed
    )

    # Pattern 4: something * [CMUP] non-aliased
    fixed = re.sub(
        r'(\*\s*)(?<!ISNULL\()(?<!\w\.)(\[CMUP\])(?!\s*,\s*0\))',
        r'\1ISNULL(\2, 0)',
        fixed
    )

    # Pattern 5: - [CMUP] (subtraction without multiplication)
    # e.g., [Montant HT Net] - [CMUP] → need ISNULL
    fixed = re.sub(
        r'(-\s*)(?<!ISNULL\()(\w+\.\[CMUP\])(?!\s*[\*,])',
        r'\1ISNULL(\2, 0)',
        fixed
    )
    fixed = re.sub(
        r'(-\s*)(?<!ISNULL\()(?<!\w\.)(\[CMUP\])(?!\s*[\*,])',
        r'\1ISNULL(\2, 0)',
        fixed
    )

    return fixed


def main():
    conn = pyodbc.connect(CONN_STR, timeout=30)
    cursor = conn.cursor()

    cursor.execute("SELECT id, code, query_template FROM APP_DataSources_Templates WHERE actif = 1 AND query_template LIKE '%CMUP%' ORDER BY code")
    rows = cursor.fetchall()

    fixed_count = 0
    for ds_id, code, query in rows:
        if not query:
            continue

        new_query = fix_prix_revient_isnull(query)

        if new_query != query:
            fixed_count += 1
            if DRY_RUN:
                print(f"[FIX] {code}")
                # Show changed lines
                for ol, nl in zip(query.split('\n'), new_query.split('\n')):
                    if ol != nl:
                        print(f"  - {ol.strip()[:120]}")
                        print(f"  + {nl.strip()[:120]}")
                print()
            else:
                cursor.execute(
                    "UPDATE APP_DataSources_Templates SET query_template = ? WHERE id = ?",
                    (new_query, ds_id)
                )

    if not DRY_RUN:
        conn.commit()

    print(f"\n{'='*50}")
    print(f"TOTAL: {fixed_count} datasources corrigees (ISNULL sur [CMUP])")
    if DRY_RUN:
        print(">>> Relancer sans --dry-run pour appliquer")
    else:
        print(">>> Corrections appliquees!")

    conn.close()


if __name__ == "__main__":
    main()
