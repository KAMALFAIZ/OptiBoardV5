# -*- coding: utf-8 -*-
"""Test marge columns on DWH_KA"""
import pyodbc, re

saas = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019', timeout=10)
dwh = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=DWH_KA;UID=sa;PWD=SQL@2019', timeout=60)
sc = saas.cursor()
dc = dwh.cursor()

test_codes = [
    'DS_ACH_ABC_FOURNISSEURS', 'DS_ACH_CA_PAR_ARTICLE',
    'DS_ACHATS_GLOBAL', 'DS_ACHATS_PAR_FOURNISSEUR',
    'DS_TOP_ARTICLES_ACHATS', 'DS_TOP_FOURNISSEURS',
    'DS_SEGMENTATION_ABC', 'DS_TOP10_ARTICLES',
    'DS_VTE_CA_MODE_REGLEMENT', 'DS_VTE_SAISONNALITE',
]

for code in test_codes:
    sc.execute("SELECT query_template FROM APP_DataSources_Templates WHERE code = ?", (code,))
    row = sc.fetchone()
    if not row:
        continue
    q = row[0]
    # Inject params
    q = q.replace('@dateDebut', "'20250101'").replace('@dateFin', "'20260501'")
    q = re.sub(r'@\w+', 'NULL', q)
    q_clean = re.sub(r'\s+ORDER\s+BY\s+[\s\S]+$', '', q, flags=re.IGNORECASE)

    if q_clean.strip().upper().startswith('WITH'):
        print(f"SKIP {code} (CTE)")
        continue

    try:
        dc.execute(f"SELECT TOP 1 * FROM ({q_clean}) AS t")
        r = dc.fetchone()
        cols = [d[0] for d in dc.description]
        has_marge = any('Marge' in c or 'Cout' in c for c in cols)
        print(f"OK   {code} -> {len(cols)} cols, marge={has_marge}")
    except Exception as e:
        print(f"FAIL {code} -> {str(e)[:100]}")

saas.close()
dwh.close()

saas.close()
dwh.close()
