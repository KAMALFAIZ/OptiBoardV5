# -*- coding: utf-8 -*-
import pyodbc, re
conn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019', timeout=10)
c = conn.cursor()

# Find DS with [CMUP] * something without ISNULL
c.execute("SELECT code, query_template FROM APP_DataSources_Templates WHERE actif = 1 AND query_template LIKE '%CMUP%' ORDER BY code")
missing = []
for code, q in c.fetchall():
    # Check if there's [CMUP] * or * [CMUP] without ISNULL
    # Pattern: NOT preceded by ISNULL( ... [CMUP]
    if re.search(r'(?<!ISNULL\()(?:\w+\.)?\[CMUP\]\s*\*', q, re.IGNORECASE):
        missing.append(code)
    elif re.search(r'\*\s*(?:\w+\.)?\[CMUP\](?!\s*,\s*0\))', q, re.IGNORECASE):
        missing.append(code)
    # Also check subtraction pattern without ISNULL: Montant - [CMUP] * Qte
    elif re.search(r'-\s*(?:\w+\.)?\[CMUP\]', q, re.IGNORECASE) and 'isnull' not in q.lower().split('prix de revient')[0][-30:]:
        missing.append(code)

if missing:
    print(f"DS with [CMUP] in calculation without ISNULL: {len(missing)}")
    for code in missing:
        print(f"  {code}")
else:
    print("All [CMUP] calculations properly wrapped with ISNULL!")

# Also verify no more @Valorisation
c.execute("SELECT code FROM APP_DataSources_Templates WHERE actif = 1 AND query_template LIKE '%@Valorisation%'")
val = c.fetchall()
if val:
    print(f"\nStill have @Valorisation: {[r[0] for r in val]}")
else:
    print("\nNo more @Valorisation - all fixed!")

conn.close()
