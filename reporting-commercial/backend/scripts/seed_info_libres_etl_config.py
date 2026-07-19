# -*- coding: utf-8 -*-
"""
Active la synchronisation des INFORMATIONS LIBRES Sage dans la config ETL centrale.
===================================================================================
Insère (idempotent) les lignes de configuration ETL nécessaires dans
OptiBoard_SaaS.dbo.ETL_Tables_Config :

  1. Informations libres          -> Info_Libres            (définitions, depuis cbSysLibre)
  2. Valeurs informations libres  -> Info_Libres_Valeurs    (EAV, extracteur __INFO_LIBRES_VALUES__)
  3. Correspondance clé tiers     -> Info_Libres_Cle_Tiers  (CT_Num <-> cbMarq de F_COMPTET) [ADDITIF]

Ces lignes activent, côté agent ETL (code déjà présent), la matérialisation des
tables DWH exploitées par les datasources DS_INFO_LIBRES_* (voir create_info_libres_ds.py
et docs/INFORMATIONS_LIBRES_SAGE.md).

Purement additif : ne modifie AUCUNE ligne existante, ne touche AUCUNE extraction
financière. Réversible (désactiver = enabled=0 / is_active=0, ou supprimer la ligne).
Idempotent : ré-exécutable (ignore une ligne déjà présente par target_table).

Usage : python scripts/seed_info_libres_etl_config.py
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

Q_TIERS = (
    "SELECT CT_Num AS [Code tiers], "
    "CAST(cbMarq AS NVARCHAR(50)) AS [Clé Sage], "
    "CASE CT_Type WHEN 0 THEN 'Client' WHEN 1 THEN 'Fournisseur' ELSE 'Autre' END AS [Type tiers] "
    "FROM F_COMPTET"
)

# (name, source_query, target_table, primary_key, sort_order, batch_size)
ROWS = [
    ("Informations libres", "SELECT [CB_File], [CB_Name] FROM [cbSysLibre]", "Info_Libres", "", 30, 10000),
    ("Valeurs informations libres", "__INFO_LIBRES_VALUES__", "Info_Libres_Valeurs", "CB_File,entity_key,CB_Name", 31, 50000),
    ("Correspondance clé tiers", Q_TIERS, "Info_Libres_Cle_Tiers", "", 32, 50000),
]

INSERT_SQL = """
INSERT INTO OptiBoard_SaaS.dbo.ETL_Tables_Config
    (table_name, name, source_query, target_table, primary_key,
     filter_column, sync_type, timestamp_column, priority, sort_order,
     delete_orphans, is_active, enabled, batch_size, interval_minutes, delete_detection)
VALUES
    (?, ?, ?, ?, ?, 'DB', 'full', NULL, 'normal', ?, 0, 1, 1, ?, 60, 0)
"""


def target_exists(target_table):
    r = execute_central(
        "SELECT COUNT(*) AS n FROM OptiBoard_SaaS.dbo.ETL_Tables_Config WHERE target_table = ?",
        (target_table,),
        use_cache=False,
    )
    return (r[0]["n"] or 0) > 0


def main():
    print("=" * 70)
    print("  Activation config ETL — INFORMATIONS LIBRES (central)")
    print("=" * 70)
    inserted = skipped = 0
    for name, query, target, pk, order, batch in ROWS:
        if target_exists(target):
            print(f"  = {target:<24} déjà présent (ignoré)")
            skipped += 1
            continue
        write_central(INSERT_SQL, (name, name, query, target, pk, order, batch))
        print(f"  + {target:<24} ajouté  (sort_order={order}, full, enabled)")
        inserted += 1
    print("-" * 70)
    print(f"  {inserted} ajouté(s), {skipped} ignoré(s)")
    print("  L'agent ETL matérialisera ces tables à son prochain cycle.")
    print("=" * 70)


if __name__ == "__main__":
    main()
