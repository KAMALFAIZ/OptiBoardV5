# -*- coding: utf-8 -*-
"""
Publie les tables INFOS LIBRES au format LARGE (colonnes) — approche #2.
========================================================================
Au lieu de l'EAV (`Info_Libres_Valeurs`, 1 ligne/champ), on materialise une table
par entite Sage, au format large : 1 ligne par entite (cbMarq), 1 colonne par champ
libre. L'agent utilise l'extracteur `__INFO_LIBRES_WIDE__:<CB_File>`
(SageExtractor.ExtractInfoLibresWideAsync — SELECT sans UNPIVOT).

Ce script (idempotent) :
  1. Ajoute au master `APP_ETL_Tables_Config` une ligne par table large.
  2. Publie ces lignes dans `APP_ETL_Tables_Published` des bases clientes ciblees.

L'EAV est CONSERVE en parallele (choix valide). Les tables larges sont auto-creees
par l'agent au 1er sync (colonnes dynamiques selon cbSysLibre + DB_Id + societe).

Usage :
    python scripts/publish_info_libres_wide.py                  # clients live par defaut
    python scripts/publish_info_libres_wide.py OptiBoard_X ...  # bases explicites
"""
import sys
import os
import warnings

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings("ignore")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from app.database_unified import execute_central, write_central  # noqa: E402
from app.services.query_crypto import enc_query  # noqa: E402

# (code, table_name, target_table, CB_File)
# code == target_table (convention APP_ETL_Tables_*). source = sentinel __INFO_LIBRES_WIDE__:<CB_File>
TABLES = [
    ("IL_Articles",            "Infos libres - Articles (large)",            "F_ARTICLE"),
    ("IL_Tiers",               "Infos libres - Tiers (large)",              "F_COMPTET"),
    ("IL_Entetes_Documents",   "Infos libres - Entetes documents (large)",  "F_DOCENTETE"),
    ("IL_Lignes_Documents",    "Infos libres - Lignes documents (large)",   "F_DOCLIGNE"),
    ("IL_Ecritures",           "Infos libres - Ecritures (large)",          "F_ECRITUREC"),
    ("IL_Comptes_Generaux",    "Infos libres - Comptes generaux (large)",   "F_COMPTEG"),
    ("IL_Comptes_Analytiques", "Infos libres - Comptes analytiques (large)","F_COMPTEA"),
]

# IMPORTANT : ne PAS publier vers un client dont l'agent n'est pas encore a jour.
# Un agent ancien qui recoit `__INFO_LIBRES_WIDE__:...` le lance comme du SQL -> erreur
# par table a chaque cycle. La publication cliente est donc OPT-IN (bases passees en args),
# a lancer UNIQUEMENT apres avoir deploye l'agent rebuild sur la machine du client.
PK = "entity_key"


def add_to_master(code, table_name, cbfile):
    if execute_central("SELECT COUNT(*) n FROM OptiBoard_SaaS.dbo.APP_ETL_Tables_Config WHERE code=?",
                       (code,), use_cache=False)[0]["n"]:
        print(f"  = master  {code:<24} déjà présent")
        return
    write_central(
        """INSERT INTO OptiBoard_SaaS.dbo.APP_ETL_Tables_Config
             (code, table_name, target_table, source_query, primary_key_columns,
              sync_type, timestamp_column, interval_minutes, priority, delete_detection,
              description, version, actif, date_creation, date_modification)
           VALUES (?, ?, ?, ?, ?, 'full', 'cbModification', 5, 'normal', 0, '', 1, 1, GETDATE(), GETDATE())""",
        (code, table_name, code, enc_query(f"__INFO_LIBRES_WIDE__:{cbfile}"), PK))
    print(f"  + master  {code:<24} ajouté  (<- {cbfile})")


def publish_to_client(db, code, table_name, cbfile):
    if execute_central(f"SELECT COUNT(*) n FROM [{db}].dbo.APP_ETL_Tables_Published WHERE code=?",
                       (code,), use_cache=False)[0]["n"]:
        print(f"    = {db:<20} {code:<24} déjà publié")
        return
    write_central(
        f"""INSERT INTO [{db}].dbo.APP_ETL_Tables_Published
              (code, table_name, target_table, source_query, primary_key_columns,
               sync_type, timestamp_column, interval_minutes, priority, delete_detection,
               description, version_centrale, is_enabled, date_publication, date_modification)
            VALUES (?, ?, ?, ?, ?, 'full', 'cbModification', 5, 'normal', 0, '', 1, 1, GETDATE(), GETDATE())""",
        (code, table_name, code, enc_query(f"__INFO_LIBRES_WIDE__:{cbfile}"), PK))
    print(f"    + {db:<20} {code:<24} publié")


def main():
    client_dbs = sys.argv[1:]  # opt-in : publier UNIQUEMENT vers les bases passees en args
    print("=" * 72)
    print("  Publication tables INFOS LIBRES LARGES (approche #2) -> pipeline agent")
    print("=" * 72)
    print("\n[1] Master APP_ETL_Tables_Config :")
    for code, tn, cb in TABLES:
        add_to_master(code, tn, cb)
    if not client_dbs:
        print("\n[2] Aucune base cliente en argument -> master uniquement.")
        print("    Publier vers un client APRES avoir deploye l'agent rebuild :")
        print("      python scripts/publish_info_libres_wide.py OptiBoard_<CODE>")
        print("=" * 72)
        return
    print(f"\n[2] Publication vers {len(client_dbs)} base(s) : {', '.join(client_dbs)}")
    for db in client_dbs:
        has = execute_central(f"SELECT COUNT(*) n FROM [{db}].sys.tables WHERE name='APP_ETL_Tables_Published'",
                              use_cache=False)[0]["n"]
        if not has:
            print(f"    ! {db}: pas de table Published (ignoré)")
            continue
        for code, tn, cb in TABLES:
            publish_to_client(db, code, tn, cb)
    print("-" * 72)
    print("  Terminé. Nécessite l'agent rebuild (extracteur __INFO_LIBRES_WIDE__).")
    print("  Les tables IL_* se matérialiseront au prochain cycle de l'agent à jour.")
    print("=" * 72)


if __name__ == "__main__":
    main()
