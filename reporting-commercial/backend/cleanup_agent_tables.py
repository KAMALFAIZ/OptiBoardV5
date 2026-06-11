"""
Nettoyage APP_ETL_Agent_Tables :
  - Garder UNIQUEMENT l'agent KA (demo)
  - Supprimer AMM, GO et les agents orphelins
  - Les vrais clients lisent depuis APP_ETL_Tables_Published (chiffré)
"""
import pyodbc

CONN = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019;TrustServerCertificate=yes;'
KA_AGENT_ID = '2e7cd44d-c2ed-4e0e-87e8-a84906723750'

conn = pyodbc.connect(CONN, timeout=15)
cur = conn.cursor()

# Etat avant
cur.execute("SELECT COUNT(*) FROM APP_ETL_Agent_Tables")
total_before = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM APP_ETL_Agent_Tables WHERE agent_id = ?", (KA_AGENT_ID,))
ka_count = cur.fetchone()[0]

print("=" * 60)
print("  NETTOYAGE APP_ETL_Agent_Tables")
print("=" * 60)
print(f"\nAVANT : {total_before} lignes total, {ka_count} lignes KA")

# Lister ce qu'on va supprimer
cur.execute("""
    SELECT t.agent_id, ISNULL(m.dwh_code, '?'), COUNT(*)
    FROM APP_ETL_Agent_Tables t
    LEFT JOIN APP_ETL_Agents_Monitoring m ON t.agent_id = m.agent_id
    WHERE t.agent_id != ?
    GROUP BY t.agent_id, m.dwh_code
""", (KA_AGENT_ID,))

print("\nAgents a supprimer :")
for r in cur.fetchall():
    print(f"  [{r[1]}] {r[0]} — {r[2]} lignes")

# Supprimer
cur.execute("DELETE FROM APP_ETL_Agent_Tables WHERE agent_id != ?", (KA_AGENT_ID,))
deleted = cur.rowcount
conn.commit()

# Etat apres
cur.execute("SELECT COUNT(*) FROM APP_ETL_Agent_Tables")
total_after = cur.fetchone()[0]

print(f"\nSupprime : {deleted} lignes")
print(f"APRES  : {total_after} lignes (KA uniquement)")

# Verification
cur.execute("SELECT DISTINCT agent_id FROM APP_ETL_Agent_Tables")
remaining = [r[0] for r in cur.fetchall()]
print(f"Agents restants : {remaining}")

conn.close()
print("\nOK")
