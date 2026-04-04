"""Diagnostique et corrige le target_id de 'Liste des articles'"""
import pyodbc
from pathlib import Path

env = {}
for line in (Path(__file__).parent / ".env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()

def conn(db):
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={env['DB_SERVER']};DATABASE={db};"
        f"UID={env['DB_USER']};PWD={env['DB_PASSWORD']};TrustServerCertificate=yes;", timeout=15)

print("\n=== Diagnostic 'Liste des articles' ===\n")

# ── Centrale : infos du menu ──────────────────────────────────────────────────
central = conn("OptiBoard_SaaS")
cur_c = central.cursor()

print("[CENTRALE] Menu 'Liste des articles' :")
cur_c.execute("""
    SELECT m.id, m.nom, m.code, m.type, m.target_id,
           CASE m.type
               WHEN 'gridview'  THEN (SELECT nom FROM APP_GridViews WHERE id = m.target_id)
               WHEN 'pivot-v2'  THEN (SELECT nom FROM APP_Pivots_V2  WHERE id = m.target_id)
               WHEN 'pivot'     THEN (SELECT nom FROM APP_Pivots_V2  WHERE id = m.target_id)
               WHEN 'dashboard' THEN (SELECT nom FROM APP_Dashboards WHERE id = m.target_id)
           END as target_nom
    FROM APP_Menus m
    WHERE m.nom LIKE '%Liste%article%'
""")
rows = cur_c.fetchall()
for r in rows:
    print(f"  id={r[0]} | code={r[2]} | type={r[3]} | target_id={r[4]} | target_nom={r[5]}")

# Trouver le code du rapport dans la centrale
cur_c.execute("""
    SELECT r.code, r.nom, r.id
    FROM APP_GridViews r
    WHERE r.id = (SELECT target_id FROM APP_Menus WHERE nom LIKE '%Liste%article%')
""")
report_central = cur_c.fetchone()
if report_central:
    print(f"\n  Rapport dans centrale : code='{report_central[0]}' | nom='{report_central[1]}' | id={report_central[2]}")
    report_code = report_central[0]
    report_type = 'gridview'
else:
    # Essayer pivot-v2
    cur_c.execute("""
        SELECT r.code, r.nom, r.id
        FROM APP_Pivots_V2 r
        WHERE r.id = (SELECT target_id FROM APP_Menus WHERE nom LIKE '%Liste%article%')
    """)
    report_central = cur_c.fetchone()
    if report_central:
        print(f"\n  Rapport dans centrale (pivot) : code='{report_central[0]}' | nom='{report_central[1]}' | id={report_central[2]}")
        report_code = report_central[0]
        report_type = 'pivot-v2'
    else:
        print("  Rapport non trouve dans centrale !")
        report_code = None
        report_type = None

central.close()

if not report_code:
    print("\nImpossible de corriger : rapport absent de la centrale.")
    exit(1)

# ── Client KA : verifier et corriger ─────────────────────────────────────────
client = conn("OptiBoard_cltKA")
client.autocommit = False
cur = client.cursor()

print(f"\n[CLIENT KA] Recherche rapport code='{report_code}' (type={report_type})...")
table = 'APP_GridViews' if report_type == 'gridview' else 'APP_Pivots_V2'
cur.execute(f"SELECT id, nom FROM {table} WHERE code = ?", (report_code,))
r = cur.fetchone()

if r:
    client_report_id = r[0]
    print(f"  Trouve : id={client_report_id} | nom='{r[1]}'")

    # Corriger le target_id du menu
    cur.execute("""
        UPDATE APP_Menus SET target_id = ?
        WHERE nom LIKE '%Liste%article%'
    """, (client_report_id,))
    print(f"  target_id corrige -> {client_report_id} ({cur.rowcount} menu(s) mis a jour)")
    client.commit()
else:
    print(f"  RAPPORT ABSENT du client KA (code='{report_code}')")
    # Chercher par nom
    cur.execute(f"SELECT id, nom, code FROM {table} WHERE nom LIKE '%article%'")
    suggestions = cur.fetchall()
    if suggestions:
        print(f"\n  Rapports similaires dans le client :")
        for s in suggestions:
            print(f"    id={s[0]} | nom='{s[1]}' | code='{s[2]}'")
        # Prendre le premier
        best = suggestions[0]
        cur.execute("UPDATE APP_Menus SET target_id = ? WHERE nom LIKE '%Liste%article%'", (best[0],))
        print(f"\n  Correction automatique -> target_id={best[0]} '{best[1]}'")
        client.commit()
    else:
        print(f"\n  AUCUN rapport 'articles' dans le client !")
        print(f"  -> Publiez d'abord le GridView 'Liste des articles' depuis Menus Maitre.")

client.close()
print("\n=== Termine ===")
