"""Diagnostic menus client KA - trouve les vrais doublons"""
import pyodbc, sys
from pathlib import Path

env = {}
for line in (Path(__file__).parent / ".env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()

CS = (f"DRIVER={{ODBC Driver 17 for SQL Server}};"
      f"SERVER=kasoft.selfip.net;DATABASE=OptiBoard_cltKA;"
      f"UID={env['DB_USER']};PWD={env['DB_PASSWORD']};TrustServerCertificate=yes;")

conn = pyodbc.connect(CS, timeout=15)
cur  = conn.cursor()

print("\n=== TOTAL MENUS ===")
cur.execute("SELECT COUNT(*) FROM APP_Menus")
print(f"Total : {cur.fetchone()[0]}")

print("\n=== MENUS SANS CODE (code NULL ou vide) ===")
cur.execute("SELECT COUNT(*) FROM APP_Menus WHERE code IS NULL OR code=''")
print(f"Sans code : {cur.fetchone()[0]}")

print("\n=== MENUS SANS PARENT (parent_id NULL) = affichage racine ===")
cur.execute("SELECT COUNT(*) FROM APP_Menus WHERE parent_id IS NULL")
print(f"A la racine : {cur.fetchone()[0]}")

print("\n=== DOUBLONS PAR NOM (meme nom, plusieurs fois) ===")
cur.execute("""
    SELECT nom, COUNT(*) as nb,
           STRING_AGG(CAST(id AS VARCHAR), ',') as ids,
           STRING_AGG(ISNULL(code,'NULL'), ',') as codes,
           STRING_AGG(CAST(ISNULL(parent_id,-1) AS VARCHAR), ',') as parents
    FROM APP_Menus
    GROUP BY nom HAVING COUNT(*) > 1
    ORDER BY nb DESC
""")
rows = cur.fetchall()
if rows:
    print(f"  {len(rows)} noms en double :")
    for r in rows:
        print(f"  nom='{r[0]}' x{r[1]} | ids={r[2]} | codes={r[3]} | parents={r[4]}")
else:
    print("  Aucun doublon par nom")

print("\n=== DETAIL MENUS A LA RACINE (parent_id NULL) ===")
cur.execute("""
    SELECT id, nom, code, type, is_custom, is_customized, parent_code
    FROM APP_Menus
    WHERE parent_id IS NULL
    ORDER BY nom
""")
for r in cur.fetchall():
    print(f"  id={r[0]:4} nom='{r[1]}' code='{r[2]}' type={r[3]} custom={r[4]} customized={r[5]} parent_code={r[6]}")

conn.close()
