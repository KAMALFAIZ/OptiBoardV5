"""
=============================================================================
  UPDATE ONLY — Patch les 6 templates Ventes corrigés (filtre date par doc).

  À utiliser quand APP_DataSources_Templates contient déjà les templates
  (le script create_ventes_reports.py ayant été lancé une première fois).

  Réimporte les définitions depuis create_ventes_reports.py via une astuce :
  on exécute le module dans un namespace isolé, on récupère la liste
  `templates`, et on UPDATE uniquement les codes ciblés.

  Idempotent : peut être relancé sans effet de bord.
=============================================================================
"""
import os
import sys
import importlib.util
import pyodbc

# Codes corrigés dans cette passe (date par document).
CODES_TO_UPDATE = {
    "DS_VTE_FACTURES",
    "DS_VTE_BC",
    "DS_VTE_DEVIS",
    "DS_VTE_AVOIRS",
    "DS_VTE_RETOURS",
    "DS_VTE_PL",
}

# Recharger les définitions depuis le script principal SANS exécuter
# son bloc DB (INSERT). On charge le fichier comme un texte et extrait
# uniquement la liste `templates`.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(SCRIPT_DIR, "create_ventes_reports.py")

with open(SOURCE, encoding="utf-8") as f:
    src = f.read()

# Coupe avant l'INSERT pour éviter d'ouvrir une connexion / insérer.
cutoff = src.find("#  INSERT ALL TEMPLATES INTO DATABASE")
if cutoff == -1:
    raise SystemExit("Marqueur d'insertion introuvable dans create_ventes_reports.py")
header = src[:cutoff]

# Stub pyodbc pour neutraliser la connexion ouverte en haut du fichier.
class _StubCursor:
    def execute(self, *a, **k): pass
    def fetchone(self): return (0,)
    def close(self): pass
class _StubConn:
    def cursor(self): return _StubCursor()
    def close(self): pass
import types
fake_pyodbc = types.SimpleNamespace(
    connect=lambda *a, **k: _StubConn(),
    IntegrityError=Exception,
)
ns = {"pyodbc": fake_pyodbc, "json": __import__("json"), "__name__": "ventes_defs"}
exec(compile(header, SOURCE, "exec"), ns)

templates = ns["templates"]
to_apply = [(c, n, q) for (c, n, q) in templates if c in CODES_TO_UPDATE]
missing = CODES_TO_UPDATE - {c for c, _, _ in to_apply}
if missing:
    raise SystemExit(f"Codes introuvables dans templates: {missing}")

# Connexion réelle pour l'UPDATE.
CONN_STR = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019"
conn = pyodbc.connect(CONN_STR, autocommit=True)
cur = conn.cursor()

print(f"Mise a jour de {len(to_apply)} templates...\n")
for code, nom, query in to_apply:
    cur.execute(
        "UPDATE APP_DataSources_Templates "
        "SET nom = ?, query_template = ?, type = 'SQL', actif = 1 "
        "WHERE code = ?",
        (nom, query, code),
    )
    print(f"  {code:25s}  {cur.rowcount} ligne(s)")

cur.close()
conn.close()
print("\nTermine.")
