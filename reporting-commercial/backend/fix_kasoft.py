"""
Fix KASOFT : corriger db_name + desactiver le client
"""
import pyodbc, sys

SERVER   = "kasoft.selfip.net"
DATABASE = "OptiBoard_SaaS"
USER     = "sa"
PASSWORD = "SQL@2019"
DRIVER   = "{ODBC Driver 17 for SQL Server}"

conn_str = (
    f"DRIVER={DRIVER};SERVER={SERVER};DATABASE={DATABASE};"
    f"UID={USER};PWD={PASSWORD};TrustServerCertificate=yes;"
)

def run(cursor, label, sql, params=()):
    try:
        cursor.execute(sql, params)
        rows = cursor.rowcount
        print(f"[OK] {label} — {rows} ligne(s) affectee(s)")
    except Exception as e:
        print(f"[ERR] {label} : {e}")

def main():
    print(f"Connexion a {SERVER}/{DATABASE}...")
    conn = pyodbc.connect(conn_str, timeout=15)
    conn.autocommit = True
    cursor = conn.cursor()
    print("Connecte\n")

    # 1) Corriger le nom de la base OptiBoard dans APP_ClientDB
    run(cursor,
        "Fix db_name OptiBoard_KASOFT -> OptiBoard_cltKASOFT",
        "UPDATE APP_ClientDB SET db_name = 'OptiBoard_cltKASOFT' WHERE dwh_code = 'KASOFT' AND db_name = 'OptiBoard_KASOFT'"
    )

    # 2) Desactiver KASOFT dans APP_DWH (actif = 0)
    run(cursor,
        "Desactiver KASOFT dans APP_DWH",
        "UPDATE APP_DWH SET actif = 0 WHERE code = 'KASOFT'"
    )

    # 3) Verification
    cursor.execute("SELECT code, nom, actif FROM APP_DWH WHERE code = 'KASOFT'")
    row = cursor.fetchone()
    if row:
        print(f"\nAPP_DWH KASOFT : actif = {row[2]} (0=desactive, 1=actif)")
    else:
        print("\n[ERR] KASOFT introuvable dans APP_DWH")

    cursor.execute("SELECT db_name, db_server FROM APP_ClientDB WHERE dwh_code = 'KASOFT'")
    row = cursor.fetchone()
    if row:
        print(f"APP_ClientDB KASOFT : db_name = {row[0]}, db_server = {row[1]}")
    else:
        print("APP_ClientDB KASOFT : aucun enregistrement")

    conn.close()
    print("\nTermine.")

if __name__ == "__main__":
    main()
