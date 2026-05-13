# -*- coding: utf-8 -*-
"""
Corrige TOUTES les datasources avec des calculs de marge incorrects:
1. @Valorisation CASE → remplacer par ISNULL([CMUP], 0)
2. [CMUP] sans ISNULL → ajouter ISNULL
3. e.Date BETWEEN → l.[Date BL] BETWEEN dans les jointures

Usage: python fix_marge_all.py [--dry-run]
"""

import pyodbc
import re
import sys

CONN_STR = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019"
DRY_RUN = "--dry-run" in sys.argv


def fix_valorisation_case(query):
    """Replace CASE @Valorisation WHEN ... END with ISNULL(alias.[CMUP], 0)"""
    # Detect the alias used for Lignes_des_ventes
    m = re.search(r'SUM\(\s*(\w+)\.', query)
    alias = m.group(1) if m else "l"

    # Pattern: CASE @Valorisation WHEN 'CMUP' THEN ... ELSE 0 END
    # This can span multiple lines
    pattern = r"CASE\s+@Valorisation\s+WHEN\s+'CMUP'\s+THEN\s+\w+\.CMUP\s+WHEN\s+'CMUP'\s+THEN\s+\w+\.\[CMUP\].*?ELSE\s+0\s+END"
    replacement = f"ISNULL({alias}.[CMUP], 0)"
    fixed = re.sub(pattern, replacement, query, flags=re.IGNORECASE | re.DOTALL)

    # Also replace @ValorisationCA CASE
    # CASE WHEN @ValorisationCA = 'TTC' THEN l.[Montant TTC Net] ELSE l.[Montant HT Net] END
    pattern_ca = r"CASE\s+WHEN\s+@ValorisationCA\s*=\s*'TTC'\s+THEN\s+(\w+)\.\[Montant TTC Net\]\s+ELSE\s+\1\.\[Montant HT Net\]\s+END"
    fixed = re.sub(pattern_ca, rf"\1.[Montant HT Net]", fixed, flags=re.IGNORECASE)

    # Remove LEFT JOIN Mouvement_stock (no longer needed)
    fixed = re.sub(
        r'\s*LEFT\s+JOIN\s+Mouvement_stock\s+AS\s+\w+\s+ON\s+\w+\.societe\s*=\s*\w+\.societe\s+AND\s+\w+\.\[N.\s*interne\]\s*=\s*\w+\.\[N.\s*interne\]',
        '',
        fixed,
        flags=re.IGNORECASE
    )

    # Fix e.Date BETWEEN → l.[Date BL] BETWEEN
    fixed = re.sub(r'e\.Date\s+BETWEEN', f'{alias}.[Date BL] BETWEEN', fixed, flags=re.IGNORECASE)
    fixed = re.sub(r'e\.\[Date\]\s+BETWEEN', f'{alias}.[Date BL] BETWEEN', fixed, flags=re.IGNORECASE)

    return fixed


def fix_missing_isnull(query):
    """Add ISNULL around [CMUP] where missing"""
    # Pattern: alias.[CMUP] not preceded by ISNULL(
    # Replace: l.[CMUP] → ISNULL(l.[CMUP], 0)
    fixed = re.sub(
        r'(?<!ISNULL\()(\w+\.\[CMUP\])(?!\s*,\s*0\))',
        r'ISNULL(\1, 0)',
        query,
        flags=re.IGNORECASE
    )
    # Non-aliased version
    fixed = re.sub(
        r'(?<!ISNULL\()(?<!\w\.)(\[CMUP\])(?!\s*,\s*0\))',
        r'ISNULL(\1, 0)',
        fixed,
        flags=re.IGNORECASE
    )
    return fixed


def main():
    conn = pyodbc.connect(CONN_STR, timeout=30)
    cursor = conn.cursor()

    cursor.execute("SELECT id, code, query_template FROM APP_DataSources_Templates WHERE actif = 1 ORDER BY code")
    rows = cursor.fetchall()

    fixed_valorisation = 0
    fixed_isnull = 0

    for ds_id, code, query in rows:
        if not query:
            continue

        original = query
        modified = False

        # Fix 1: @Valorisation CASE
        if '@Valorisation' in query:
            query = fix_valorisation_case(query)
            if query != original:
                fixed_valorisation += 1
                modified = True

        # Fix 2: Missing ISNULL on CMUP (in calculation context)
        ql = query.lower()
        if 'prix de revient' in ql and 'isnull' not in ql.split('prix de revient')[0][-20:]:
            # Only fix in SUM/multiplication context
            if re.search(r'(?<!ISNULL\()\[CMUP\]\s*\*', query, re.IGNORECASE) or \
               re.search(r'\*\s*(?<!ISNULL\()\[CMUP\]', query, re.IGNORECASE) or \
               re.search(r'(?<!ISNULL\()\w+\.\[CMUP\]\s*\*', query, re.IGNORECASE):
                before = query
                query = fix_missing_isnull(query)
                if query != before:
                    fixed_isnull += 1
                    modified = True

        if modified:
            if DRY_RUN:
                print(f"[FIX] {code}")
                # Show changed lines
                orig_lines = original.split('\n')
                new_lines = query.split('\n')
                for i, (ol, nl) in enumerate(zip(orig_lines, new_lines)):
                    if ol != nl:
                        print(f"  - {ol.strip()[:120]}")
                        print(f"  + {nl.strip()[:120]}")
                if len(new_lines) != len(orig_lines):
                    print(f"  (lines: {len(orig_lines)} -> {len(new_lines)})")
                print()
            else:
                cursor.execute(
                    "UPDATE APP_DataSources_Templates SET query_template = ? WHERE id = ?",
                    (query, ds_id)
                )

    if not DRY_RUN:
        conn.commit()

    print(f"{'='*50}")
    print(f"RESUME:")
    print(f"  @Valorisation CASE corrige: {fixed_valorisation}")
    print(f"  ISNULL ajoute: {fixed_isnull}")
    print(f"  TOTAL: {fixed_valorisation + fixed_isnull}")

    if DRY_RUN:
        print("\n>>> Relancer sans --dry-run pour appliquer")
    else:
        print("\n>>> Corrections appliquees!")

    conn.close()


if __name__ == "__main__":
    main()
