"""
Copie les vues comptabilité (dashboards, pivots, gridviews) depuis la DB centrale
vers les DBs clients qui ne les ont pas encore.
Utilise SET IDENTITY_INSERT ON pour forcer les mêmes IDs.
Gère les différences de schéma entre centrale et clients.
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
os.chdir(os.path.join(os.path.dirname(__file__), 'backend'))

from app.database_unified import execute_central, execute_client, client_manager
import pyodbc

def client_conn(dwh_code):
    return client_manager.get_connection(dwh_code)

def get_table_columns(cursor, table_name):
    """Retourne la liste des colonnes existantes dans une table."""
    cursor.execute(
        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = ? ORDER BY ORDINAL_POSITION",
        (table_name,)
    )
    return [row[0] for row in cursor.fetchall()]

def copy_to_client(dwh_code, table, id_col, ids_to_copy):
    """Copie les lignes spécifiées de la DB centrale vers la DB client.
    Adapte le schéma aux colonnes disponibles dans la DB client."""
    if not ids_to_copy:
        return

    # Fetch rows from central
    ph = ','.join('?' * len(ids_to_copy))
    rows = execute_central(f"SELECT * FROM {table} WHERE {id_col} IN ({ph})", tuple(ids_to_copy), use_cache=False)
    if not rows:
        print(f"  [{dwh_code}] {table}: aucune ligne en central pour {ids_to_copy}")
        return

    # Check which IDs are already in client
    try:
        existing = execute_client(f"SELECT {id_col} FROM {table} WHERE {id_col} IN ({ph})",
                                   tuple(ids_to_copy), dwh_code=dwh_code, use_cache=False)
        existing_ids = {r[id_col] for r in (existing or [])}
    except Exception:
        existing_ids = set()

    to_insert = [r for r in rows if r[id_col] not in existing_ids]
    if not to_insert:
        print(f"  [{dwh_code}] {table}: déjà présent {ids_to_copy}")
        return

    conn = client_conn(dwh_code)
    cursor = conn.cursor()
    try:
        # Check table exists
        cursor.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = ?", (table,))
        if cursor.fetchone()[0] == 0:
            print(f"  [{dwh_code}] {table}: table inexistante, skip")
            return

        # Get available columns in client DB
        client_cols = get_table_columns(cursor, table)
        client_cols_lower = {c.lower(): c for c in client_cols}

        cursor.execute(f"SET IDENTITY_INSERT {table} ON")

        for row in to_insert:
            # Only use columns that exist in client DB
            filtered = {}
            for k, v in row.items():
                col_lower = k.lower()
                if col_lower in client_cols_lower:
                    real_col = client_cols_lower[col_lower]
                    # Serialize JSON fields
                    if isinstance(v, (dict, list)):
                        v = json.dumps(v)
                    filtered[real_col] = v

            if id_col not in filtered:
                print(f"  [{dwh_code}] {table}: colonne id '{id_col}' manquante, skip")
                continue

            cols = list(filtered.keys())
            vals = list(filtered.values())
            col_str = ','.join(f'[{c}]' for c in cols)
            ph_ins = ','.join('?' * len(cols))
            cursor.execute(f"INSERT INTO {table} ({col_str}) VALUES ({ph_ins})", vals)
            print(f"  [{dwh_code}] {table}: inséré id={row[id_col]} nom={row.get('nom','?')}")

        cursor.execute(f"SET IDENTITY_INSERT {table} OFF")
        conn.commit()
        print(f"  [{dwh_code}] {table}: OK ({len(to_insert)} ligne(s))")

    except Exception as e:
        try:
            conn.rollback()
        except:
            pass
        print(f"  [{dwh_code}] {table}: ERREUR: {e}")
    finally:
        cursor.close()
        conn.close()

# Get all active DWHs with client DBs
dwhs = execute_central("SELECT code, nom FROM APP_DWH WHERE actif=1 ORDER BY code", use_cache=False)
print(f"DWHs actifs: {[d['code'] for d in dwhs]}\n")

for dwh in dwhs:
    code = dwh['code']
    if not client_manager.has_client_db(code):
        print(f"[{code}] pas de DB client, skip")
        continue

    print(f"=== Client {code} ({dwh['nom']}) ===")

    # Copy dashboards 175, 176
    copy_to_client(code, 'APP_Dashboards', 'id', [175, 176])

    # Copy pivots 111-116
    copy_to_client(code, 'APP_Pivots_V2', 'id', list(range(111, 117)))

    # Copy gridviews 331-337
    copy_to_client(code, 'APP_GridViews', 'id', list(range(331, 338)))

    print()

print("Done! Vérification finale...")

# Verify
for dwh in dwhs:
    code = dwh['code']
    if not client_manager.has_client_db(code):
        continue
    try:
        ph6 = ','.join(['?']*2)
        d = execute_client(f"SELECT COUNT(*) as cnt FROM APP_Dashboards WHERE id IN ({ph6})", (175,176), dwh_code=code, use_cache=False)
        p = execute_client("SELECT COUNT(*) as cnt FROM APP_Pivots_V2 WHERE id BETWEEN 111 AND 116", dwh_code=code, use_cache=False)
        g = execute_client("SELECT COUNT(*) as cnt FROM APP_GridViews WHERE id BETWEEN 331 AND 337", dwh_code=code, use_cache=False)
        print(f"  [{code}] dashboards={d[0]['cnt']}/2, pivots={p[0]['cnt']}/6, gridviews={g[0]['cnt']}/7")
    except Exception as e:
        print(f"  [{code}] vérification error: {e}")
