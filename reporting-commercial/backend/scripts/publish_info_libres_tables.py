# -*- coding: utf-8 -*-
"""
Publie les tables INFORMATIONS LIBRES vers le vrai pipeline agent.
==================================================================
Le pipeline opératif des agents ETL est :
    APP_ETL_Tables_Config (central, master)  --publish-->  APP_ETL_Tables_Published (base client)
et l'agent lit UNIQUEMENT `APP_ETL_Tables_Published` (source_query chiffrée $enc1$).

Ce script (idempotent) :
  1. Ajoute au master `APP_ETL_Tables_Config` les 2 tables manquantes :
       - Info_Libres_Valeurs   (EAV, extracteur __INFO_LIBRES_VALUES__)
       - Info_Libres_Cle_Tiers (CT_Num <-> cbMarq de F_COMPTET, additif)
     (Info_Libres — le catalogue — y est déjà.)
  2. Publie ces tables dans `APP_ETL_Tables_Published` des bases clientes ciblées,
     en clonant exactement le format de la ligne `Info_Libres` déjà publiée.

source_query stockée chiffrée via `enc_query` (comme tout le reste). L'agent la
déchiffre et reconnaît le sentinel `__INFO_LIBRES_VALUES__` (extracteur EAV).

Usage :
    python scripts/publish_info_libres_tables.py                 # clients live par défaut
    python scripts/publish_info_libres_tables.py OptiBoard_X ... # bases explicites
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

Q_TIERS = (
    "SELECT CT_Num AS [Code tiers], "
    "CAST(cbMarq AS NVARCHAR(50)) AS [Clé Sage], "
    "CASE CT_Type WHEN 0 THEN 'Client' WHEN 1 THEN 'Fournisseur' ELSE 'Autre' END AS [Type tiers] "
    "FROM F_COMPTET"
)

# Correspondance ligne de document : [N° interne]=DL_No (porte par Lignes_des_*) <-> cbMarq
# (cle des infos libres F_DOCLIGNE). SQL normal -> tout agent la synchronise (pas de rebuild).
# Permet de joindre Lignes_des_* a la table large IL_Lignes_Documents sans toucher aux
# extractions financieres des lignes.
Q_LIGNES = (
    "SELECT CAST(DL_No AS NVARCHAR(50)) AS [N° interne], "
    "CAST(cbMarq AS NVARCHAR(50)) AS [Clé Sage] "
    "FROM F_DOCLIGNE"
)

# code, table_name, target_table, clear_source_query, primary_key_columns(JSON)
TABLES = [
    ("Info_Libres_Valeurs", "Valeurs informations libres", "Info_Libres_Valeurs",
     "__INFO_LIBRES_VALUES__", '["CB_File","entity_key","CB_Name"]'),
    ("Info_Libres_Cle_Tiers", "Correspondance clé tiers", "Info_Libres_Cle_Tiers",
     Q_TIERS, "[]"),
    ("Info_Libres_Cle_Lignes", "Correspondance clé lignes", "Info_Libres_Cle_Lignes",
     Q_LIGNES, '["N° interne"]'),
]

# Bases clientes des agents actuellement vivants (défaut)
DEFAULT_CLIENT_DBS = ["OptiBoard_ALEAFOOD", "OptiBoard_cltAMM"]


def add_to_master(code, table_name, target, clear_sq, pk):
    exists = execute_central(
        "SELECT COUNT(*) n FROM OptiBoard_SaaS.dbo.APP_ETL_Tables_Config WHERE code = ?",
        (code,), use_cache=False)[0]["n"]
    if exists:
        print(f"  = master  {code:<22} déjà présent")
        return
    write_central(
        """INSERT INTO OptiBoard_SaaS.dbo.APP_ETL_Tables_Config
             (code, table_name, target_table, source_query, primary_key_columns,
              sync_type, timestamp_column, interval_minutes, priority, delete_detection,
              description, version, actif, date_creation, date_modification)
           VALUES (?, ?, ?, ?, ?, 'full', 'cbModification', 5, 'high', 0, '', 1, 1, GETDATE(), GETDATE())""",
        (code, table_name, target, enc_query(clear_sq), pk))
    print(f"  + master  {code:<22} ajouté")


def publish_to_client(db, code, table_name, target, clear_sq, pk):
    exists = execute_central(
        f"SELECT COUNT(*) n FROM [{db}].dbo.APP_ETL_Tables_Published WHERE code = ?",
        (code,), use_cache=False)[0]["n"]
    if exists:
        print(f"    = {db:<20} {code:<22} déjà publié")
        return
    write_central(
        f"""INSERT INTO [{db}].dbo.APP_ETL_Tables_Published
              (code, table_name, target_table, source_query, primary_key_columns,
               sync_type, timestamp_column, interval_minutes, priority, delete_detection,
               description, version_centrale, is_enabled, date_publication, date_modification)
            VALUES (?, ?, ?, ?, ?, 'full', 'cbModification', 5, 'high', 0, '', 1, 1, GETDATE(), GETDATE())""",
        (code, table_name, target, enc_query(clear_sq), pk))
    print(f"    + {db:<20} {code:<22} publié")


def main():
    client_dbs = sys.argv[1:] or DEFAULT_CLIENT_DBS
    print("=" * 70)
    print("  Publication tables INFOS LIBRES -> pipeline agent (Published)")
    print("=" * 70)
    print("\n[1] Master APP_ETL_Tables_Config :")
    for code, tn, target, sq, pk in TABLES:
        add_to_master(code, tn, target, sq, pk)
    print(f"\n[2] Publication vers {len(client_dbs)} base(s) cliente(s) : {', '.join(client_dbs)}")
    for db in client_dbs:
        # sécurité : ne publier que si la table Published existe déjà (client provisionné)
        has = execute_central(
            f"SELECT COUNT(*) n FROM [{db}].sys.tables WHERE name='APP_ETL_Tables_Published'",
            use_cache=False)[0]["n"]
        if not has:
            print(f"    ! {db}: pas de table Published (ignoré)")
            continue
        for code, tn, target, sq, pk in TABLES:
            publish_to_client(db, code, tn, target, sq, pk)
    print("-" * 70)
    print("  Terminé. Les agents liront ces tables à leur prochain cycle (~5 min).")
    print("=" * 70)


if __name__ == "__main__":
    main()
