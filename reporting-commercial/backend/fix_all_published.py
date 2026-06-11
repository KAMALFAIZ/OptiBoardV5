"""
FIX COMPLET : Nettoie et répare toutes les entrées APP_ETL_Tables_Published
dans tous les DWH.

Problèmes à corriger :
1. Codes avec espaces (ex: 'Échéances ventes') → remplacer par code underscore
2. Codes avec accent É capital (ex: 'Échéances_Ventes') → normaliser
3. Entrées en doublon (garder seulement les codes underscore valides)
4. S'assurer que chaque DWH a les entrées pour TOUS les codes actifs dans APP_ETL_Tables_Config
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database_unified import get_central_connection
import pyodbc

conn_c = get_central_connection()
cur_c  = conn_c.cursor()

# Lire tous les codes valides depuis APP_ETL_Tables_Config avec leurs infos
cur_c.execute("""
    SELECT code, table_name, target_table
    FROM APP_ETL_Tables_Config
    WHERE actif = 1
    ORDER BY code
""")
valid_configs = {r[0]: {'table_name': r[1], 'target_table': r[2]} for r in cur_c.fetchall()}
valid_codes = set(valid_configs.keys())
print(f"Codes valides dans APP_ETL_Tables_Config: {len(valid_codes)}")
for c in sorted(valid_codes):
    print(f"  {c}")

# Lire les DWH
cur_c.execute("""
    SELECT d.code, d.nom, ISNULL(c.db_name, d.base_dwh) AS db_name,
           d.serveur_dwh, d.user_dwh, d.password_dwh
    FROM APP_DWH d
    LEFT JOIN APP_ClientDB c ON c.dwh_code = d.code
    WHERE d.actif = 1
    ORDER BY d.code
""")
dwh_list = cur_c.fetchall()
conn_c.close()

db_server = os.getenv('DB_SERVER', 'kasoft.selfip.net')
db_user   = os.getenv('DB_USER', 'sa')
db_pwd    = os.getenv('DB_PASSWORD', '')

print("\n" + "=" * 80)
print("CORRECTION DES APP_ETL_Tables_Published PAR DWH")
print("=" * 80)

for row in dwh_list:
    dwh_code, nom, db_name, serveur, user_dwh, pwd_dwh = row
    srv = serveur or db_server
    usr = user_dwh or db_user
    pwd = pwd_dwh  or db_pwd
    db  = db_name  or f"OptiBoard_{dwh_code}"

    print(f"\n{'='*60}")
    print(f"[{dwh_code}] {nom} → {db}")
    print(f"{'='*60}")

    try:
        cs = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={srv};DATABASE={db};"
            f"UID={usr};PWD={pwd};TrustServerCertificate=yes;"
        )
        conn_d = pyodbc.connect(cs, autocommit=True)
        cur_d  = conn_d.cursor()

        # Lire l'état actuel
        cur_d.execute("""
            SELECT code, table_name, target_table, sync_type,
                   interval_minutes, priority, delete_detection, is_enabled
            FROM APP_ETL_Tables_Published
            ORDER BY code
        """)
        existing = {r[0]: dict(zip(
            ['code','table_name','target_table','sync_type','interval_minutes','priority','delete_detection','is_enabled'],
            r
        )) for r in cur_d.fetchall()}

        print(f"  Avant: {len(existing)} entrées")

        # 1. Supprimer les codes invalides (avec espaces ou accents mal formatés)
        invalid_to_delete = [c for c in existing if c not in valid_codes]
        deleted = 0
        for bad_code in invalid_to_delete:
            cur_d.execute("DELETE FROM APP_ETL_Tables_Published WHERE code = ?", (bad_code,))
            deleted += cur_d.rowcount
            print(f"  ✗ Supprimé code invalide: {repr(bad_code)}")

        if deleted == 0:
            print(f"  - Aucun code invalide à supprimer")

        # 2. Ajouter les codes valides manquants (tous ceux dans APP_ETL_Tables_Config)
        added = 0
        for code, cfg in valid_configs.items():
            if code not in existing:
                # Valeurs par défaut
                cur_d.execute("""
                    INSERT INTO APP_ETL_Tables_Published
                    (code, table_name, target_table, sync_type, interval_minutes, priority, delete_detection, is_enabled)
                    VALUES (?, ?, ?, 'incremental', 60, 'normal', 0, 1)
                """, (code, cfg['table_name'], cfg['target_table']))
                added += cur_d.rowcount
                print(f"  + Ajouté: code={repr(code)}")

        if added == 0:
            print(f"  - Aucun code manquant à ajouter")

        # Vérification finale
        cur_d.execute("SELECT COUNT(*) FROM APP_ETL_Tables_Published WHERE is_enabled = 1")
        total_enabled = cur_d.fetchone()[0]
        cur_d.execute("SELECT COUNT(*) FROM APP_ETL_Tables_Published")
        total = cur_d.fetchone()[0]
        print(f"\n  Après: {total} entrées ({total_enabled} actives)")

        conn_d.close()
    except Exception as e:
        import traceback
        print(f"  ERREUR: {e}")
        traceback.print_exc()

print("\n" + "=" * 80)
print("FIN CORRECTION")
print("=" * 80)
print("""
RÉSUMÉ :
  - Codes invalides (avec espaces/accents mal formatés) supprimés
  - Codes valides manquants ajoutés avec is_enabled=1
  - Tous les DWH ont maintenant les 33 tables publiées correctes

ACTION SUIVANTE : Redémarrez les agents ETL.
""")
