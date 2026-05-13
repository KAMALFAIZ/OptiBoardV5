"""Fix accents manquants dans APP_Menus (base centrale)"""
import pyodbc, sys
from pathlib import Path

env = {}
for line in (Path(__file__).parent / ".env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()

SRV = env['DB_SERVER']
USR = env['DB_USER']
PWD = env['DB_PASSWORD']
DB  = env.get('DB_NAME', 'OptiBoard_SaaS')

FIXES = {
    "CA par Periode":               "CA par Période",
    "CA par Zone Geo":              "CA par Zone Géo",
    "CA par Depot":                 "CA par Dépôt",
    "CA par Categorie Tarifaire":   "CA par Catégorie Tarifaire",
    "Delais par Etape":             "Délais par Étape",
    "Marges & Rentabilite":         "Marges & Rentabilité",
    "Echeances par Commercial":     "Échéances par Commercial",
    "Tendances & Saisonnalite":     "Tendances & Saisonnalité",
    "Recouvrement & Tresorerie":    "Recouvrement & Trésorerie",
    "Balance Agee":                 "Balance Âgée",
    "Creances Douteuses":           "Créances Douteuses",
    "Echeances Non Reglees":        "Échéances Non Réglées",
    "Reglements par Periode":       "Règlements par Période",
    "Reglements par Mode":          "Règlements par Mode",
    "Factures Non Reglees":         "Factures Non Réglées",
    "Prevision Encaissements":      "Prévision Encaissements",
    "Stock par Depot":              "Stock par Dépôt",
    "Valorisation Multi-methodes":  "Valorisation Multi-méthodes",
    "Articles Proches Peremption":  "Articles Proches Péremption",
    "Transferts Inter-Depots":      "Transferts Inter-Dépôts",
    "Echeances Achats":             "Échéances Achats",
    "Preparations Livraison":       "Préparations Livraison",
    "BL Non Factures":              "BL Non Facturés",
}

conn_str = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={SRV};DATABASE={DB};UID={USR};PWD={PWD};"
    "TrustServerCertificate=yes;"
)

try:
    conn = pyodbc.connect(conn_str, autocommit=False)
    cursor = conn.cursor()
    total = 0
    for old, new in FIXES.items():
        cursor.execute("UPDATE APP_Menus SET nom = ? WHERE nom = ?", new, old)
        n = cursor.rowcount
        if n:
            print(f"  OK '{old}' -> '{new}' ({n} ligne(s))")
            total += n
        else:
            print(f"  -- '{old}' : deja correct ou absent")
    conn.commit()
    print(f"\n[OK] {total} menu(s) mis a jour.")
except Exception as e:
    print(f"❌ Erreur : {e}", file=sys.stderr)
    sys.exit(1)
finally:
    try: conn.close()
    except: pass
