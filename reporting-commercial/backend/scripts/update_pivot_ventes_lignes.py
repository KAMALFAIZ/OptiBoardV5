"""
Script de mise à jour : DS_PIVOT_VENTES_LIGNES
===============================================
1. Insère/met à jour le datasource DS_PIVOT_VENTES_LIGNES dans APP_DataSources_Templates
2. Met à jour le pivot "Pivot CA Global" (id 221 ou par nom) pour utiliser
   ce nouveau datasource riche (~50 champs disponibles)

Exécution :
    python backend/scripts/update_pivot_ventes_lignes.py
"""

import sys, os, json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.database_unified import execute_central as execute_query, central_cursor as get_cursor


# =============================================================================
# QUERY TEMPLATE
# =============================================================================

QUERY_TEMPLATE = """
            SELECT
                -- SOCIÉTÉ
                li.[societe]                                                AS [Société],

                -- DIMENSIONS TEMPORELLES
                li.[Date BL]                                                AS [Date BL],
                li.[Date document]                                          AS [Date Document],
                YEAR(li.[Date BL])                                          AS [Année],
                MONTH(li.[Date BL])                                         AS [Mois Num],
                FORMAT(li.[Date BL], 'MMMM', 'fr-FR')                      AS [Mois],
                DATEPART(QUARTER, li.[Date BL])                             AS [Trimestre Num],
                'T' + CAST(DATEPART(QUARTER, li.[Date BL]) AS VARCHAR)     AS [Trimestre],
                FORMAT(li.[Date BL], 'yyyy-MM')                             AS [Période],
                FORMAT(li.[Date BL], 'yyyy') + ' T'
                    + CAST(DATEPART(QUARTER, li.[Date BL]) AS VARCHAR)      AS [Trim Année],
                FORMAT(li.[Date BL], 'yyyy')
                    + CASE WHEN MONTH(li.[Date BL]) <= 6 THEN ' S1' ELSE ' S2' END
                                                                            AS [Semestre],

                -- DIMENSIONS CLIENT
                li.[Code client]                                            AS [Code Client],
                li.[Intitulé client]                                        AS [Client],
                ISNULL(cl.[Région], '')                                     AS [Région],
                ISNULL(cl.[Ville], '')                                      AS [Ville],
                ISNULL(cl.[Pays], '')                                       AS [Pays],
                ISNULL(cl.[Classement], '')                                 AS [Classement Client],
                ISNULL(cl.[Catégorie tarifaire], '')                        AS [Catégorie Tarifaire],

                -- DIMENSIONS COMMERCIAL
                ISNULL(CAST(en.[Code représentant] AS VARCHAR), '')         AS [Code Commercial],
                ISNULL(en.[Nom représentant], 'Non affecté')               AS [Commercial],

                -- DIMENSIONS ARTICLE
                li.[Code article]                                            AS [Code Article],
                li.[Désignation ligne]                                       AS [Désignation],
                ISNULL(li.[Catalogue 1], '')                                 AS [Famille],
                ISNULL(li.[Catalogue 2], '')                                 AS [Sous Famille],
                ISNULL(li.[Catalogue 3], '')                                 AS [Catalogue 3],
                ISNULL(li.[Catalogue 4], '')                                 AS [Catalogue 4],
                ISNULL(li.[Gamme 1], '')                                     AS [Gamme 1],
                ISNULL(li.[Gamme 2], '')                                     AS [Gamme 2],

                -- DIMENSIONS DOCUMENT
                li.[Type Document],
                li.[N° Pièce]                                                AS [Num Pièce],
                ISNULL(en.[Statut], '')                                      AS [Statut Document],
                ISNULL(en.[Souche], '')                                      AS [Souche],
                ISNULL(en.[Catégorie Comptable], '')                         AS [Catégorie Comptable],
                ISNULL(en.[Intitulé tiers payeur], '')                       AS [Tiers Payeur],
                ISNULL(en.[Expédition], '')                                  AS [Expédition],

                -- DIMENSIONS DÉPÔT
                ISNULL(CAST(li.[Code dépôt] AS VARCHAR), '')                 AS [Code Dépôt],
                ISNULL(li.[Intitulé dépôt], '')                              AS [Dépôt],

                -- DIMENSIONS AFFAIRE / LOT
                ISNULL(li.[Code d'affaire], '')                              AS [Code Affaire],
                ISNULL(li.[Intitulé affaire], '')                            AS [Affaire],
                ISNULL(li.[N° Série/Lot], '')                                AS [Lot Série],

                -- MESURES BRUTES
                li.[Montant HT Net]                                          AS [CA HT],
                li.[Montant TTC Net]                                         AS [CA TTC],
                li.[Quantité]                                                AS [Quantité],
                li.[Prix unitaire]                                           AS [Prix Unitaire HT],
                ISNULL(li.[CMUP], 0)                                         AS [Coût Revient Unit],
                li.[Quantité] * ISNULL(li.[CMUP], 0)                        AS [Coût Revient],
                li.[Montant HT Net] - li.[Quantité] * ISNULL(li.[CMUP], 0)  AS [Marge],
                ISNULL(li.[Poids net], 0)                                    AS [Poids Net],
                ISNULL(li.[Poids brut], 0)                                   AS [Poids Brut],
                ISNULL(li.[Remise 1], 0)                                     AS [Remise 1 %],
                ISNULL(li.[Frais d'approche], 0)                             AS [Frais Approche],
                1                                                            AS [Nb Lignes]

            FROM [Lignes_des_ventes] li
            INNER JOIN [Entête_des_ventes] en
                ON li.[DB_Id]        = en.[DB_Id]
               AND li.[Type Document] = en.[Type Document]
               AND li.[N° Pièce]     = en.[N° pièce]
            LEFT JOIN [Clients] cl
                ON li.[DB_Id]      = cl.[DB_Id]
               AND li.[Code client] = cl.[Code client]
            WHERE li.[Valorise CA] = 'Oui'
              AND (@societe IS NULL OR li.[societe] = @societe)
              AND li.[Date BL] BETWEEN @dateDebut AND @dateFin
              AND (@commercial IS NULL OR en.[Nom représentant] = @commercial)
""".strip()

PARAMETERS = json.dumps([
    {"name": "dateDebut",  "type": "date",   "source": "global"},
    {"name": "dateFin",    "type": "date",   "source": "global"},
    {"name": "societe",    "type": "select", "source": "query",
     "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom",
     "required": False, "allow_null": True, "null_label": "(Toutes)"},
    {"name": "commercial", "type": "select", "source": "query",
     "query": "SELECT DISTINCT [Nom représentant] AS value, [Nom représentant] AS label FROM [Entête_des_ventes] WHERE [Nom représentant] IS NOT NULL AND [Nom représentant] <> '' ORDER BY [Nom représentant]",
     "required": False, "allow_null": True, "null_label": "(Tous)"},
], ensure_ascii=False)

DS_CODE = "DS_PIVOT_VENTES_LIGNES"
DS_NOM  = "Ventes – Lignes Détail (Pivot)"
DS_CAT  = "Ventes"
DS_DESC = ("Datasource ligne-par-ligne pour pivot builder : toutes les dimensions "
           "(Client, Commercial, Article, Famille, Dépôt, Région, Période…) et mesures brutes "
           "(CA HT, TTC, Marge, Quantité, Poids…). ~50 champs disponibles.")


# =============================================================================
# CONFIG PIVOT MISE À JOUR
# (à appliquer sur "Pivot CA Global" ou tout pivot qui utilisait DS_VENTES_GLOBAL)
# =============================================================================

NEW_PIVOT_VALUES = json.dumps([
    {"field": "CA HT",       "aggregation": "SUM",         "format": "currency", "label": "CA HT"},
    {"field": "CA TTC",      "aggregation": "SUM",         "format": "currency", "label": "CA TTC"},
    {"field": "Marge",       "aggregation": "SUM",         "format": "currency", "label": "Marge Brute"},
    {"field": "Quantité",    "aggregation": "SUM",                               "label": "Qté Totale"},
    {"field": "Code Client", "aggregation": "DISTINCTCOUNT",                     "label": "Nb Clients"},
    {"field": "Num Pièce",   "aggregation": "DISTINCTCOUNT",                     "label": "Nb Documents"},
    {"field": "Nb Lignes",   "aggregation": "SUM",                               "label": "Nb Lignes"},
    {"field": "Coût Revient","aggregation": "SUM",         "format": "currency", "label": "Coût Revient"},
], ensure_ascii=False)

NEW_PIVOT_ROWS    = json.dumps([{"field": "Société"}],   ensure_ascii=False)
NEW_PIVOT_COLUMNS = json.dumps([],                       ensure_ascii=False)
NEW_PIVOT_FILTERS = json.dumps([],                       ensure_ascii=False)


# =============================================================================
# MAIN
# =============================================================================

def run():
    print("=" * 70)
    print("Mise à jour : DS_PIVOT_VENTES_LIGNES")
    print("=" * 70)

    # 1. Upsert datasource template
    with get_cursor() as cur:
        cur.execute(
            "SELECT id FROM APP_DataSources_Templates WHERE code = ?", (DS_CODE,)
        )
        row = cur.fetchone()

        if row:
            cur.execute("""
                UPDATE APP_DataSources_Templates
                SET nom = ?, category = ?, description = ?,
                    query_template = ?, parameters = ?, actif = 1
                WHERE code = ?
            """, (DS_NOM, DS_CAT, DS_DESC, QUERY_TEMPLATE, PARAMETERS, DS_CODE))
            print(f"[UPDATE] Template {DS_CODE} mis à jour (id={row[0]})")
        else:
            cur.execute("""
                INSERT INTO APP_DataSources_Templates
                (code, nom, type, category, description, query_template, parameters, is_system, actif)
                VALUES (?, ?, 'query', ?, ?, ?, ?, 0, 1)
            """, (DS_CODE, DS_NOM, DS_CAT, DS_DESC, QUERY_TEMPLATE, PARAMETERS))
            print(f"[CREATE] Template {DS_CODE} créé")

    # 2. Mettre à jour le pivot "Pivot CA Global" (id=221 ou par nom)
    pivots = execute_query(
        "SELECT id, nom, data_source_code FROM APP_Pivots_V2 WHERE nom = 'Pivot CA Global' OR id = 221",
        use_cache=False
    )

    if not pivots:
        print("\n[INFO] Pivot 'Pivot CA Global' (id=221) non trouvé — seul le template a été créé.")
        print("       Changez manuellement la source de données du pivot vers DS_PIVOT_VENTES_LIGNES.")
        return

    for pivot in pivots:
        pid = pivot["id"]
        pnom = pivot["nom"]
        old_ds = pivot["data_source_code"]
        print(f"\n[PIVOT] id={pid} '{pnom}' (ancienne source: {old_ds})")

        with get_cursor() as cur:
            cur.execute("""
                UPDATE APP_Pivots_V2
                SET data_source_code = ?,
                    rows_config      = ?,
                    columns_config   = ?,
                    values_config    = ?,
                    filters_config   = ?,
                    updated_at       = GETDATE()
                WHERE id = ?
            """, (
                DS_CODE,
                NEW_PIVOT_ROWS,
                NEW_PIVOT_COLUMNS,
                NEW_PIVOT_VALUES,
                NEW_PIVOT_FILTERS,
                pid
            ))
        print(f"  → source: {DS_CODE}")
        print(f"  → Zone Ligne : Société")
        print(f"  → Zone Données : CA HT, CA TTC, Marge, Quantité, Nb Clients (DISTINCTCOUNT), Nb Documents (DISTINCTCOUNT), Nb Lignes, Coût Revient")

    print("\n✓ Terminé — rechargez le pivot dans le navigateur.")


if __name__ == "__main__":
    run()
