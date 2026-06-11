import pyodbc
conn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019;TrustServerCertificate=yes;', timeout=15)
cur = conn.cursor()

cur.execute("""
    SELECT t.agent_id,
           ISNULL(m.dwh_code, '?') AS dwh_code,
           ISNULL(m.nom, '?') AS nom,
           COUNT(*) AS nb_tables,
           SUM(CASE WHEN t.is_enabled = 1 THEN 1 ELSE 0 END) AS enabled,
           SUM(CASE WHEN ISNULL(t.is_inherited,0) = 1 THEN 1 ELSE 0 END) AS inherited,
           SUM(CASE WHEN ISNULL(t.is_customized,0) = 1 THEN 1 ELSE 0 END) AS customized
    FROM APP_ETL_Agent_Tables t
    LEFT JOIN APP_ETL_Agents_Monitoring m ON t.agent_id = m.agent_id
    GROUP BY t.agent_id, m.dwh_code, m.nom
    ORDER BY m.dwh_code
""")

header = "DWH    Nom                       Tables  Enabled Inherited Custom  Agent_ID"
print(header)
print("-" * len(header))
for r in cur.fetchall():
    print(f"{r[1]:<7}{r[2]:<26}{r[3]:<8}{r[4]:<8}{r[5]:<10}{r[6]:<8}{r[0]}")

cur.execute("SELECT COUNT(*) FROM APP_ETL_Agent_Tables")
print(f"\nTOTAL: {cur.fetchone()[0]} lignes dans APP_ETL_Agent_Tables")
conn.close()
