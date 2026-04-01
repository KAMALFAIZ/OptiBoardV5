"""Vérification directe via pyodbc"""
import pyodbc

C_SERVER = "kasoft.selfip.net"
C_USER   = "sa"
C_PASS   = "SQL@2019"

def conn_str(server, db, user, pwd):
    return (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={server};DATABASE={db};UID={user};PWD={pwd};"
        f"TrustServerCertificate=yes;Connection Timeout=15;"
    )

# Base centrale
print("=== Tables APP_ETL dans OptiBoard_SaaS ===")
try:
    cn = pyodbc.connect(conn_str(C_SERVER, "OptiBoard_SaaS", C_USER, C_PASS))
    cur = cn.cursor()
    cur.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME LIKE 'APP_ETL%' ORDER BY TABLE_NAME")
    for r in cur.fetchall():
        print(" -", r[0])

    # Colonnes APP_ClientDB
    print()
    print("=== Colonnes de APP_ClientDB ===")
    cur.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='APP_ClientDB' ORDER BY ORDINAL_POSITION")
    for r in cur.fetchall():
        print(" -", r[0])

    # Contenu APP_ClientDB
    print()
    print("=== Contenu APP_ClientDB ===")
    cur.execute("SELECT * FROM APP_ClientDB")
    cols = [c[0] for c in cur.description]
    print("  Colonnes:", cols)
    for r in cur.fetchall():
        print(" ", dict(zip(cols, r)))

    cn.close()
except Exception as e:
    print(f"ERREUR centrale: {e}")

# Base client ESSA - connexion directe sans APP_ClientDB
print()
print("=== Tables APP_ETL dans OptiBoard_ESSA (connexion directe) ===")
try:
    cn2 = pyodbc.connect(conn_str(C_SERVER, "OptiBoard_ESSA", C_USER, C_PASS))
    cur2 = cn2.cursor()
    cur2.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME LIKE 'APP_ETL%' ORDER BY TABLE_NAME")
    rows = cur2.fetchall()
    if rows:
        for r in rows:
            print(" -", r[0])
    else:
        print("  AUCUNE TABLE APP_ETL dans OptiBoard_ESSA !")

    print()
    print("=== Contenu APP_ETL_Agents dans OptiBoard_ESSA ===")
    cur2.execute("SELECT agent_id, nom, is_active, statut FROM APP_ETL_Agents")
    for r in cur2.fetchall():
        print(" ", r)
    cn2.close()
except Exception as e:
    print(f"ERREUR ESSA: {e}")
