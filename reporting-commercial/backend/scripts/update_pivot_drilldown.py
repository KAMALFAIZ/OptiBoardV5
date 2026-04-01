"""
=============================================================================
  UPDATE - Source Drilldown (détail lignes) sur les pivots existants

  Problème résolu: les pivots n'avaient pas de drilldown_data_source_code
  configuré → clic sur une cellule utilisait la datasource principale
  (agrégée) au lieu d'une source ligne par ligne.

  Ce script:
  1. Met à jour DS_VTE_DETAIL_COMPLET avec les champs enrichis nécessaires
     aux drilldowns (Region, Ville, Code Commercial, Nom Mois, aliases propres)
  2. Assigne drilldown_data_source_code = 'DS_VTE_DETAIL_COMPLET'
     sur tous les pivots APP_Pivots_V2

  Exécution: python scripts/update_pivot_drilldown.py
=============================================================================
"""
import pyodbc
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

conn_str = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019"
conn = pyodbc.connect(conn_str, autocommit=True)
cursor = conn.cursor()

# ============================================================================
#  COMMON SQL FRAGMENTS
# ============================================================================
BASE_JOIN = """FROM [Lignes_des_ventes] li
INNER JOIN [Entête_des_ventes] en
    ON li.[societe] = en.[societe]
    AND li.[Type Document] = en.[Type Document]
    AND li.[N° Pièce] = en.[N° pièce]"""

DATE_FILTER = "li.[Date BL] BETWEEN @dateDebut AND @dateFin"
SOCIETE_FILTER = "(@societe IS NULL OR li.[societe] = @societe)"
COMMERCIAL_FILTER = "(@commercial IS NULL OR en.[Nom représentant] = @commercial)"
WHERE_ALL = f"WHERE {DATE_FILTER} AND {SOCIETE_FILTER} AND {COMMERCIAL_FILTER}"

# ============================================================================
#  1. MISE À JOUR DE DS_VTE_DETAIL_COMPLET
#     Ajout: Code Commercial, Nom Mois, Region, Ville, aliases propres
# ============================================================================
DETAIL_COMPLET_QUERY = f"""SELECT
    li.societe AS Societe,
    li.[Type Document],
    li.[N° Pièce] AS [Num Piece],
    li.[Date document] AS [Date Document],
    li.[Date BL],
    FORMAT(li.[Date BL], 'MMMM', 'fr-FR') AS [Nom Mois],
    li.[Code client] AS [Code Client],
    li.[Intitulé client] AS Client,
    en.[Code représentant] AS [Code Commercial],
    en.[Nom représentant] AS Commercial,
    en.Souche,
    en.Statut,
    li.[Code article] AS [Code Article],
    li.[Désignation ligne] AS Designation,
    li.[Catalogue 1] AS Famille,
    li.[Catalogue 2] AS [Sous Famille],
    li.Quantité AS Quantite,
    li.[Prix unitaire] AS [Prix Unitaire],
    li.[Montant HT Net] AS [Montant HT],
    li.[Montant TTC Net] AS [Montant TTC],
    li.[Prix de revient] AS [Prix Revient],
    li.[Montant HT Net] - li.Quantité * li.[Prix de revient] AS Marge,
    li.[Poids net] AS [Poids Net],
    li.[Code dépôt] AS [Code Depot],
    li.[Intitulé dépôt] AS Depot,
    ISNULL(cl.[Région], '') AS [Region],
    ISNULL(cl.[Ville], '') AS [Ville],
    li.[Valorise CA],
    li.[Remise 1],
    li.[N° Pièce BL] AS [Num BL],
    li.[N° Pièce BC] AS [Num BC],
    en.[Entête 1],
    en.[Entête 2],
    en.[Entête 3],
    en.[Entête 4],
    en.Etat,
    en.Devise,
    en.Expédition,
    li.[Intitulé affaire],
    en.Référence,
    en.Cours,
    en.[N° Compte Payeur],
    en.[Intitulé tiers payeur] AS [Tiers Payeur],
    en.[Catégorie Comptable] AS [Categorie Comptable],
    li.[Catalogue 3],
    li.[Catalogue 4],
    li.[Gamme 1],
    li.[Gamme 2],
    li.[Poids brut],
    li.[N° Série/Lot],
    li.Taxe1,
    li.Taxe2,
    li.[Type taxe 1],
    li.[Type taxe 2],
    li.[PU Devise],
    li.[Frais d'approche],
    li.[Type de la remise 1]
{BASE_JOIN}
LEFT JOIN [Clients] cl ON li.[Code client] = cl.[Code client] AND li.[societe] = cl.[societe]
{WHERE_ALL}
ORDER BY [Date Document] DESC, [Num Piece]"""

print("=" * 65)
print("ÉTAPE 1 — Mise à jour DS_VTE_DETAIL_COMPLET")
print("=" * 65)

cursor.execute(
    "UPDATE APP_DataSources_Templates SET query_template = ? WHERE code = 'DS_VTE_DETAIL_COMPLET'",
    (DETAIL_COMPLET_QUERY,)
)
if cursor.rowcount > 0:
    print("  ✓ DS_VTE_DETAIL_COMPLET mis à jour")
    print("    Nouveaux champs: Code Commercial, Nom Mois, Region, Ville,")
    print("                    Tiers Payeur (alias), Categorie Comptable (alias)")
else:
    print("  ✗ DS_VTE_DETAIL_COMPLET non trouvé en base")

# ============================================================================
#  2. ASSIGNER LE DRILLDOWN SUR TOUS LES PIVOTS APP_Pivots_V2
# ============================================================================
print()
print("=" * 65)
print("ÉTAPE 2 — Assignation drilldown sur APP_Pivots_V2")
print("=" * 65)

# Mapping: datasource principale → datasource drilldown
# DS_VTE_DETAIL_COMPLET couvre tous les cas grâce aux champs ajoutés à l'étape 1
DRILLDOWN_MAPPING = {
    # CA agrégés par dimension → détail factures
    "DS_VTE_CA_CLIENT":          "DS_VTE_DETAIL_COMPLET",
    "DS_VTE_CA_ARTICLE":         "DS_VTE_DETAIL_COMPLET",
    "DS_VTE_CA_COMMERCIAL":      "DS_VTE_DETAIL_COMPLET",
    "DS_VTE_CA_REGION":          "DS_VTE_DETAIL_COMPLET",
    "DS_VTE_CA_FAMILLE":         "DS_VTE_DETAIL_COMPLET",
    "DS_VTE_CA_MENSUEL":         "DS_VTE_DETAIL_COMPLET",
    "DS_VTE_CA_MODE_REGLEMENT":  "DS_VTE_DETAIL_COMPLET",
    "DS_VTE_CA_DEPOT":           "DS_VTE_DETAIL_COMPLET",
    "DS_VTE_CA_AFFAIRE":         "DS_VTE_DETAIL_COMPLET",
    # Analyses → détail factures
    "DS_VTE_MARGES":             "DS_VTE_DETAIL_COMPLET",
    "DS_VTE_REMISES":            "DS_VTE_DETAIL_COMPLET",
    "DS_VTE_PANIER_MOYEN":       "DS_VTE_DETAIL_COMPLET",
    "DS_VTE_ANALYSE_PRIX":       "DS_VTE_DETAIL_COMPLET",
    "DS_VTE_RENTABILITE_CLIENT": "DS_VTE_DETAIL_COMPLET",
    "DS_VTE_SAISONNALITE":       "DS_VTE_DETAIL_COMPLET",
    "DS_VTE_COMPARATIF":         "DS_VTE_DETAIL_COMPLET",
    "DS_VTE_TOP_CLIENTS":        "DS_VTE_DETAIL_COMPLET",
    "DS_VTE_TOP_ARTICLES":       "DS_VTE_DETAIL_COMPLET",
    "DS_VTE_FIDELITE":           "DS_VTE_DETAIL_COMPLET",
    "DS_VTE_CHURN":              "DS_VTE_DETAIL_COMPLET",
}

# Récupérer tous les pivots de APP_Pivots_V2
cursor.execute("SELECT id, nom, data_source_code FROM APP_Pivots_V2 ORDER BY nom")
pivots = cursor.fetchall()

if not pivots:
    print("  Aucun pivot trouvé dans APP_Pivots_V2")
else:
    updated = 0
    skipped = 0
    for row in pivots:
        pid, nom, ds_code = row[0], row[1], row[2]
        drill_code = DRILLDOWN_MAPPING.get(ds_code, "DS_VTE_DETAIL_COMPLET")

        cursor.execute(
            "UPDATE APP_Pivots_V2 SET drilldown_data_source_code = ? WHERE id = ?",
            (drill_code, pid)
        )
        if cursor.rowcount > 0:
            print(f"  ✓ [{pid:3d}] {nom}")
            print(f"         {ds_code} → drilldown: {drill_code}")
            updated += 1
        else:
            skipped += 1

    print()
    print(f"  {updated} pivots mis à jour, {skipped} ignorés.")

print()
print("Terminé.")
print("Les pivots affichent maintenant le détail ligne par ligne au drilldown.")
