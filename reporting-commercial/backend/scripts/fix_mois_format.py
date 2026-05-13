# -*- coding: utf-8 -*-
"""
Mettre format='month' sur toutes les colonnes Mois (numeriques 1-12)
dans les columns_config des GridViews.
Les colonnes 'Periode' (format yyyy-MM) ne sont PAS modifiees.
"""
import sys, os, json, pyodbc
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;'
    'UID=sa;PWD=SQL@2019;TrustServerCertificate=yes'
)
conn.autocommit = True
cur = conn.cursor()

# Champs concernes : 'Mois' uniquement (Periode = yyyy-MM deja lisible)
MOIS_FIELDS = {'mois', 'month'}

cur.execute("SELECT id, nom, columns_config FROM APP_GridViews WHERE columns_config IS NOT NULL AND columns_config != ''")
rows = cur.fetchall()

updated = 0
for gid, nom, cols_raw in rows:
    try:
        cols = json.loads(cols_raw)
    except:
        continue

    changed = False
    for col in cols:
        field = (col.get('field') or col.get('dataField') or col.get('name') or '').strip()
        if field.lower() in MOIS_FIELDS:
            if col.get('format') != 'month':
                col['format'] = 'month'
                # Retirer type='number' pour eviter le filtre numerique sur un mois
                if col.get('type') == 'number':
                    col.pop('type', None)
                changed = True
                print(f"  GV {gid:4d}  {nom[:50]}  '{field}' -> format=month")

    if changed:
        new_json = json.dumps(cols, ensure_ascii=False)
        cur.execute("UPDATE APP_GridViews SET columns_config=? WHERE id=?", (new_json, gid))
        updated += 1

print(f"\nTotal GridViews mis a jour : {updated}")

# Verification
print("\nVerification:")
cur.execute("SELECT id, nom, columns_config FROM APP_GridViews WHERE columns_config LIKE '%\"month\"%'")
for gid, nom, cols_raw in cur.fetchall():
    cols = json.loads(cols_raw)
    for col in cols:
        if col.get('format') == 'month':
            print(f"  GV {gid:4d}  {nom[:50]}  field={col.get('field')!r}  format=month OK")

conn.close()
