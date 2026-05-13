# -*- coding: utf-8 -*-
"""
Crée DS_VTE_CA_COMPLET : datasource détail (1 ligne par vente) avec
TOUS les champs Sage disponibles. Migre ensuite les 8 pivots CA vers
ce datasource sans toucher à leurs zones (rows/values/filters/columns).
"""
import pyodbc
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=kasoft.selfip.net;"
    "DATABASE=OptiBoard_SaaS;"
    "UID=sa;PWD=SQL@2019;"
    "TrustServerCertificate=yes"
)

conn = pyodbc.connect(CONN_STR, autocommit=True)
cursor = conn.cursor()

# ─────────────────────────────────────────────────────────────────
#  Datasource détail CA — tous les champs disponibles
# ─────────────────────────────────────────────────────────────────
CA_COMPLET_QUERY = """SELECT
    -- Contexte / Période
    li.societe AS [Societe],
    YEAR(li.[Date BL]) AS [Annee],
    MONTH(li.[Date BL]) AS [Mois],
    FORMAT(li.[Date BL], 'yyyy-MM') AS [Periode],
    -- Document
    li.[Type Document],
    en.Souche,
    en.Statut,
    li.[N° Pièce] AS [Num Piece],
    li.[Date BL] AS [Date],
    li.[Date document] AS [Date Document],
    -- Client
    li.[Code client] AS [Code Client],
    li.[Intitulé client] AS [Client],
    -- Commercial
    en.[Code représentant] AS [Code Commercial],
    en.[Nom représentant] AS [Commercial],
    -- Article
    li.[Code article] AS [Code Article],
    li.[Désignation ligne] AS [Designation],
    -- Famille / Catalogue
    li.[Catalogue 1] AS [Famille],
    li.[Catalogue 2] AS [Sous Famille],
    li.[Catalogue 3] AS [Catalogue 3],
    li.[Catalogue 4] AS [Catalogue 4],
    li.[Gamme 1] AS [Gamme 1],
    li.[Gamme 2] AS [Gamme 2],
    -- Dépôt
    li.[Code dépôt] AS [Code Depot],
    li.[Intitulé dépôt] AS [Depot],
    -- Affaire
    li.[Code d'affaire] AS [Code Affaire],
    li.[Intitulé affaire] AS [Affaire],
    -- Géographie (via table Clients)
    ISNULL(cl.[Région], 'Non renseigné') AS [Region],
    ISNULL(cl.[Ville], 'Non renseigné') AS [Ville],
    ISNULL(cl.[Catégorie tarifaire], '') AS [Categorie Tarifaire],
    -- En-têtes libres
    en.[Entête 1] AS [Entete 1],
    en.[Entête 2] AS [Entete 2],
    en.[Entête 3] AS [Entete 3],
    en.[Entête 4] AS [Entete 4],
    -- Tiers / Comptable
    en.[Intitulé tiers payeur] AS [Tiers Payeur],
    en.[Catégorie Comptable] AS [Categorie Comptable],
    -- Mesures (nommées pour correspondre aux zones des 8 pivots CA)
    li.[Quantité] AS [Quantite],
    li.[Quantité] AS [Quantite Totale],
    li.[Quantité] AS [Quantite Vendue],
    li.[Prix unitaire] AS [Prix Moyen],
    ISNULL(li.[Poids net], 0) AS [Poids Net Total],
    li.[Montant HT Net] AS [CA HT],
    li.[Montant TTC Net] AS [CA TTC],
    li.[Quantité] * ISNULL(li.[CMUP], 0) AS [Cout Revient],
    li.[Montant HT Net] - li.[Quantité] * ISNULL(li.[CMUP], 0) AS [Marge Brute],
    CASE WHEN li.[Montant HT Net] <> 0
        THEN ROUND(100.0 * (li.[Montant HT Net] - li.[Quantité] * ISNULL(li.[CMUP], 0)) / li.[Montant HT Net], 2)
        ELSE 0 END AS [Taux Marge %],
    -- Nb (1 par ligne — SUM = nb lignes, DISTINCTCOUNT sur Num Piece / Code Client / Code Article)
    1 AS [Nb Documents],
    1 AS [Nb Clients],
    1 AS [Nb Articles]
FROM [Lignes_des_ventes] li
INNER JOIN [Entête_des_ventes] en
    ON li.[societe] = en.[societe]
    AND li.[Type Document] = en.[Type Document]
    AND li.[N° Pièce] = en.[N° pièce]
LEFT JOIN [Clients] cl
    ON li.[Code client] = cl.[Code client]
    AND li.[societe] = cl.[societe]
WHERE li.[Valorise CA] = 'Oui'
  AND li.[Date BL] BETWEEN @dateDebut AND @dateFin
  AND (@societe IS NULL OR li.[societe] = @societe)
  AND (@commercial IS NULL OR en.[Nom représentant] = @commercial)
ORDER BY li.[Date BL] DESC, li.[N° Pièce]"""

CA_COMPLET_PARAMS = json.dumps([
    {"name": "dateDebut",   "type": "date",   "label": "Date début",  "required": True,  "default": "FIRST_DAY_YEAR"},
    {"name": "dateFin",     "type": "date",   "label": "Date fin",    "required": True,  "default": "TODAY"},
    {"name": "societe",     "type": "select", "label": "Société",     "required": False, "default": None},
    {"name": "commercial",  "type": "select", "label": "Commercial",  "required": False, "default": None},
], ensure_ascii=False)

print("=" * 70)
print("  CRÉATION DS_VTE_CA_COMPLET")
print("=" * 70)

existing = cursor.execute(
    "SELECT id FROM APP_DataSources_Templates WHERE code = ?",
    ("DS_VTE_CA_COMPLET",)
).fetchone()

if existing:
    cursor.execute(
        """UPDATE APP_DataSources_Templates
           SET nom=?, description=?, query_template=?, parameters=?, updated_at=GETDATE()
           WHERE code=?""",
        (
            "CA Complet (détail lignes)",
            "Datasource détail CA — 1 ligne par vente, tous les champs Sage disponibles",
            CA_COMPLET_QUERY,
            CA_COMPLET_PARAMS,
            "DS_VTE_CA_COMPLET"
        )
    )
    print(f"  UPDATE DS_VTE_CA_COMPLET (id={existing[0]})")
else:
    cursor.execute(
        """INSERT INTO APP_DataSources_Templates
           (code, nom, type, category, description, query_template, parameters, is_system, actif, date_creation)
           VALUES (?, ?, 'query', 'ventes', ?, ?, ?, 0, 1, GETDATE())""",
        (
            "DS_VTE_CA_COMPLET",
            "CA Complet (détail lignes)",
            "Datasource détail CA — 1 ligne par vente, tous les champs Sage disponibles",
            CA_COMPLET_QUERY,
            CA_COMPLET_PARAMS,
        )
    )
    new_id = cursor.execute("SELECT @@IDENTITY").fetchone()[0]
    print(f"  INSERT DS_VTE_CA_COMPLET (id={int(new_id)})")

# ─────────────────────────────────────────────────────────────────
#  Migrer les 8 pivots CA vers DS_VTE_CA_COMPLET
# ─────────────────────────────────────────────────────────────────
CA_PIVOT_NAMES = [
    "CA par Client",
    "CA par Article",
    "CA par Famille",
    "CA par Catalogue",
    "CA par Période",
    "CA par Région",
    "CA par Dépôt",
    "CA par Affaire",
]

OLD_DS_CODES = [
    "DS_VTE_CA_CLIENT",
    "DS_VTE_CA_ARTICLE",
    "DS_VTE_CA_FAMILLE",
    "DS_VTE_CA_CATALOGUE",
    "DS_VTE_CA_MENSUEL",
    "DS_VTE_CA_REGION",
    "DS_VTE_CA_DEPOT",
    "DS_VTE_CA_AFFAIRE",
]

print()
print("=" * 70)
print("  MIGRATION DES 8 PIVOTS CA → DS_VTE_CA_COMPLET")
print("=" * 70)

updated = 0
for nom in CA_PIVOT_NAMES:
    row = cursor.execute(
        "SELECT id, data_source_code FROM APP_Pivots_V2 WHERE nom = ?",
        (nom,)
    ).fetchone()
    if row:
        pivot_id, old_code = row
        cursor.execute(
            "UPDATE APP_Pivots_V2 SET data_source_code = ?, updated_at = GETDATE() WHERE id = ?",
            ("DS_VTE_CA_COMPLET", pivot_id)
        )
        print(f"  [{pivot_id}] {nom:<30} {old_code} → DS_VTE_CA_COMPLET")
        updated += 1
    else:
        print(f"  [?] {nom:<30} NON TROUVÉ")

print()
print(f"  {updated} / {len(CA_PIVOT_NAMES)} pivots migrés")
print()

# ─────────────────────────────────────────────────────────────────
#  Vérification finale
# ─────────────────────────────────────────────────────────────────
print("=" * 70)
print("  VÉRIFICATION")
print("=" * 70)
pivots = cursor.execute("""
    SELECT id, nom, data_source_code
    FROM APP_Pivots_V2
    WHERE nom IN (
        'CA par Client','CA par Article','CA par Famille','CA par Catalogue',
        'CA par Période','CA par Région','CA par Dépôt','CA par Affaire'
    )
    ORDER BY id
""").fetchall()
for p in pivots:
    ok = "✓" if p[2] == "DS_VTE_CA_COMPLET" else "✗"
    print(f"  {ok} [{p[0]}] {p[1]:<30} {p[2]}")

cursor.close()
conn.close()
print()
print("  Terminé.")
