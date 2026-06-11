"""
Désactive Echeances_Achats et Echeances_Ventes dans APP_ETL_Tables_Published
pour le DWH AMM (F_ECHEANCES absente dans leur Sage).
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database_unified import get_central_connection
import pyodbc

conn = get_central_connection()
cur  = conn.cursor()

# Récupérer connexion DWH AMM
cur.execute("""
    SELECT ISNULL(c.db_name, d.base_dwh) AS db_name,
           d.serveur_dwh, d.user_dwh, d.password_dwh
    FROM APP_DWH d
    LEFT JOIN APP_ClientDB c ON c.dwh_code = d.code
    WHERE d.code = 'AMM' AND d.actif = 1
""")
row = cur.fetchone()
conn.close()

if not row:
    print("DWH AMM non trouvé!")
    exit()

db_name, serveur, user_dwh, pwd_dwh = row
srv = serveur or os.getenv('DB_SERVER', 'kasoft.selfip.net')
usr = user_dwh or os.getenv('DB_USER', 'sa')
pwd = pwd_dwh  or os.getenv('DB_PASSWORD', '')
db  = db_name  or 'OptiBoard_cltAMM'

print(f"DWH AMM → {srv}/{db}")

cs = (f"DRIVER={{ODBC Driver 17 for SQL Server}};"
      f"SERVER={srv};DATABASE={db};"
      f"UID={usr};PWD={pwd};TrustServerCertificate=yes;")
conn_d = pyodbc.connect(cs, autocommit=True)
cur_d  = conn_d.cursor()

# Vérifier l'état actuel
print("\nÉtat actuel des Echeances pour AMM:")
cur_d.execute("""
    SELECT code, is_enabled FROM APP_ETL_Tables_Published
    WHERE code IN ('Echeances_Achats', 'Echeances_Ventes')
""")
for r in cur_d.fetchall():
    print(f"  {r[0]}: is_enabled={r[1]}")

# Désactiver
for code in ['Echeances_Achats', 'Echeances_Ventes']:
    cur_d.execute("UPDATE APP_ETL_Tables_Published SET is_enabled=0 WHERE code=?", (code,))
    if cur_d.rowcount > 0:
        print(f"  ✓ {code} désactivé")
    else:
        print(f"  - {code} non trouvé dans APP_ETL_Tables_Published")

conn_d.close()

print("""
NOTE : Si ATLASMULTIMATERIAL utilise les échéances Sage,
il faut identifier la vraie table dans leur base Sage :
  - F_ECHEANCES (Sage 100 standard)
  - F_REGTECH (certaines versions)
  - Ou calculée depuis F_DOCENTETE
Contactez le responsable Sage AMM pour confirmer.
""")
print("FIX TERMINÉ")
