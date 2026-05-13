# -*- coding: utf-8 -*-
"""Fix the 2 remaining datasources with @Valorisation references."""
import pyodbc
import re

CONN_STR = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019"

def fix_query(query):
    # Replace @Valorisation AS [Type Valorisation] with literal
    fixed = re.sub(
        r"@Valorisation\s+AS\s+\[Type Valorisation\]",
        "'CMUP' AS [Type Valorisation]",
        query,
        flags=re.IGNORECASE
    )
    # Remove ms.* columns (no JOIN to Mouvement_stock)
    fixed = re.sub(
        r",?\s*ISNULL\(ms\.\[[^\]]+\],\s*0\)\s+AS\s+\[[^\]]+\]\s*",
        "",
        fixed,
        flags=re.IGNORECASE
    )
    # Clean up double ISNULL: ISNULL(ISNULL(x, 0), 0) -> ISNULL(x, 0)
    fixed = re.sub(
        r"ISNULL\(\s*ISNULL\(([^)]+,\s*0)\),\s*0\)",
        r"ISNULL(\1)",
        fixed
    )
    return fixed

def main():
    conn = pyodbc.connect(CONN_STR, timeout=30)
    cursor = conn.cursor()

    cursor.execute("SELECT id, code, query_template FROM APP_DataSources_Templates WHERE code IN ('DS_CA_MARGE_DYNAMIQUE', 'DS_COM_MARGE_PAR_LIGNE') AND actif = 1")
    rows = cursor.fetchall()

    for ds_id, code, query in rows:
        new_query = fix_query(query)
        if new_query != query:
            cursor.execute("UPDATE APP_DataSources_Templates SET query_template = ? WHERE id = ?", (new_query, ds_id))
            print(f"Fixed {code} (id={ds_id})")
        else:
            print(f"No change needed: {code}")

    conn.commit()
    print("\nDone!")
    conn.close()

if __name__ == "__main__":
    main()
