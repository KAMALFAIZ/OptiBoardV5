"""Corrige les templates SQL des datasources Achats pour le DWH
- Remplace DB_Id joins par les bonnes colonnes de jointure
- Remplace [Désignation Article] par [Désignation] dans Lignes_des_achats
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import execute_query, get_db_cursor


# Templates avec jointures Fournisseurs via DB_Id
# Fix: l.[DB_Id] = f.[DB_Id] AND l.[Code fournisseur] = f.[Code fournisseur]
#  ->  l.[Code fournisseur] = f.[Code fournisseur] AND l.[societe] = f.[societe]

# Templates avec jointures Articles via DB_Id
# Fix: l.[DB_Id] = a.[DB_Id] AND l.[Code article] = a.[Code Article]
#  ->  l.[Code article] = a.[Code Article] AND l.[societe] = a.[societe]

# Templates avec jointures Entête via DB_Id
# Fix: l.[DB_Id] = e.[DB_Id] AND l.[Type Document] = e.[Type Document]
#  ->  l.[societe] = e.[societe] AND l.[Type Document] = e.[Type Document]

# Templates avec [Désignation Article] dans l. (Lignes_des_achats)
# Fix: l.[Désignation Article] -> l.[Désignation]

FIXES = {
    # --- Fournisseurs JOIN fixes ---
    "DS_ACHATS_PAR_FOURNISSEUR": [
        ("l.[DB_Id] = f.[DB_Id] AND l.[Code fournisseur] = f.[Code fournisseur]",
         "l.[Code fournisseur] = f.[Code fournisseur] AND l.[societe] = f.[societe]"),
    ],
    "DS_ACHATS_PAR_FAMILLE": [
        ("l.[DB_Id] = a.[DB_Id] AND l.[Code article] = a.[Code Article]",
         "l.[Code article] = a.[Code Article] AND l.[societe] = a.[societe]"),
    ],
    "DS_ACHATS_PAR_CATALOGUE": [
        ("l.[DB_Id] = a.[DB_Id] AND l.[Code article] = a.[Code Article]",
         "l.[Code article] = a.[Code Article] AND l.[societe] = a.[societe]"),
    ],
    "DS_ACHATS_PAR_ACHETEUR": [
        ("l.[DB_Id] = f.[DB_Id] AND l.[Code fournisseur] = f.[Code fournisseur]",
         "l.[Code fournisseur] = f.[Code fournisseur] AND l.[societe] = f.[societe]"),
    ],
    "DS_TOP_FOURNISSEURS": [
        ("l.[DB_Id] = f.[DB_Id] AND l.[Code fournisseur] = f.[Code fournisseur]",
         "l.[Code fournisseur] = f.[Code fournisseur] AND l.[societe] = f.[societe]"),
    ],

    # --- Articles JOIN fixes + Designation fix ---
    "DS_ACHATS_PAR_ARTICLE": [
        ("l.[DB_Id] = a.[DB_Id] AND l.[Code article] = a.[Code Article]",
         "l.[Code article] = a.[Code Article] AND l.[societe] = a.[societe]"),
    ],
    "DS_TOP_ARTICLES_ACHATS": [
        ("l.[DB_Id] = a.[DB_Id] AND l.[Code article] = a.[Code Article]",
         "l.[Code article] = a.[Code Article] AND l.[societe] = a.[societe]"),
    ],
    "DS_EVOLUTION_PRIX_ACHATS": [
        ("l.[DB_Id] = a.[DB_Id] AND l.[Code article] = a.[Code Article]",
         "l.[Code article] = a.[Code Article] AND l.[societe] = a.[societe]"),
    ],
    "DS_COMPARAISON_FOURNISSEURS": [
        ("l.[DB_Id] = a.[DB_Id] AND l.[Code article] = a.[Code Article]",
         "l.[Code article] = a.[Code Article] AND l.[societe] = a.[societe]"),
    ],

    # --- Entete JOIN fixes + Designation fix ---
    "DS_COMMANDES_ACHATS": [
        ("l.[DB_Id] = e.[DB_Id] AND l.[Type Document] = e.[Type Document]",
         "l.[societe] = e.[societe] AND l.[Type Document] = e.[Type Document]"),
    ],
    "DS_COMMANDES_ACHATS_EN_COURS": [
        ("l.[DB_Id] = e.[DB_Id] AND l.[Type Document] = e.[Type Document]",
         "l.[societe] = e.[societe] AND l.[Type Document] = e.[Type Document]"),
    ],
}

# Templates qui utilisent l.[Désignation Article] au lieu de l.[Désignation]
DESIGNATION_FIX_CODES = [
    "DS_FACTURES_ACHATS",
    "DS_BONS_RECEPTION",
    "DS_COMMANDES_ACHATS",
    "DS_AVOIRS_ACHATS",
    "DS_COMMANDES_ACHATS_EN_COURS",
]


def fix_templates():
    with get_db_cursor() as cursor:
        # Fix JOIN conditions
        for code, replacements in FIXES.items():
            row = execute_query(
                "SELECT id, query_template FROM APP_DataSources_Templates WHERE code = ?",
                (code,), use_cache=False
            )
            if not row:
                print(f"  SKIP: {code} - template not found")
                continue

            template_id = row[0]["id"]
            query = row[0]["query_template"]
            modified = False

            for old, new in replacements:
                if old in query:
                    query = query.replace(old, new)
                    modified = True

            if modified:
                cursor.execute(
                    "UPDATE APP_DataSources_Templates SET query_template = ? WHERE id = ?",
                    (query, template_id)
                )
                print(f"  OK: {code} (id={template_id}) - JOIN fix applied")
            else:
                print(f"  SKIP: {code} (id={template_id}) - no changes needed")

        # Fix Designation Article -> Designation in Lignes_des_achats
        for code in DESIGNATION_FIX_CODES:
            row = execute_query(
                "SELECT id, query_template FROM APP_DataSources_Templates WHERE code = ?",
                (code,), use_cache=False
            )
            if not row:
                print(f"  SKIP: {code} - template not found")
                continue

            template_id = row[0]["id"]
            query = row[0]["query_template"]

            # Replace l.[Désignation Article] with l.[Désignation]
            old_col = "l.[\u00c4\u2202signation Article]"  # This won't work due to encoding
            # Just use the actual bytes - look for "signation Article" pattern
            if "signation Article]" in query:
                query = query.replace("signation Article]", "signation]")
                cursor.execute(
                    "UPDATE APP_DataSources_Templates SET query_template = ? WHERE id = ?",
                    (query, template_id)
                )
                print(f"  OK: {code} (id={template_id}) - Designation fix applied")
            else:
                print(f"  SKIP: {code} (id={template_id}) - no Designation change needed")

        # Also fix templates that have both issues (Articles JOIN + Designation in select referencing articles table)
        # For DS_ACHATS_PAR_ARTICLE, DS_TOP_ARTICLES_ACHATS, etc., the Designation comes from a.[Désignation Article]
        # which IS correct (Articles table has that column), so no fix needed there


if __name__ == "__main__":
    print("Fixing Achats datasource templates...")
    print()
    fix_templates()
    print()
    print("Done!")
