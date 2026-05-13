# -*- coding: utf-8 -*-
"""
Configure les 9 widgets du dashboard 166 "Vue Commerciale"
avec les bonnes datasources (template-based) au lieu du mode sql inline.
"""
import pyodbc, json

conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;'
    'UID=sa;PWD=SQL@2019;TrustServerCertificate=yes'
)
cur = conn.cursor()

# ================================================================
# ETAPE 1 : Mettre a jour DS_KPI_RESUME pour ajouter TauxMarge
#           et NbArticlesVendus (wrap de la requete existante)
# ================================================================
print("=== Mise a jour DS_KPI_RESUME ===")

# Lire la requete existante
cur.execute("SELECT query_template FROM APP_DataSources_Templates WHERE code='DS_KPI_RESUME'")
row = cur.fetchone()
original_query = row[0].strip()
print(f"  Longueur originale: {len(original_query)} chars")

# Verifier si deja mis a jour
if 'TauxMarge' in original_query:
    print("  -> Deja mis a jour, pas de changement")
else:
    # Construire la version etendue - la requete NbArticlesVendus utilise les memes params
    # Le @dateDebut, @dateFin, @societe seront passes normalement
    new_kpi_query = """SELECT kpi.*,
    CASE WHEN kpi.CA > 0 THEN ROUND(100.0 * kpi.Marge / kpi.CA, 2) ELSE 0.0 END AS TauxMarge,
    (SELECT COUNT(DISTINCT [Code article])
     FROM [Lignes_des_ventes]
     WHERE [Valorise CA] = 'Oui'
       AND [Date BL] BETWEEN @dateDebut AND @dateFin
       AND (@societe IS NULL OR [societe] = @societe)) AS NbArticlesVendus
FROM (
""" + original_query + """
) AS kpi"""

    cur.execute("UPDATE APP_DataSources_Templates SET query_template=? WHERE code='DS_KPI_RESUME'", new_kpi_query)
    print(f"  -> DS_KPI_RESUME mis a jour ({cur.rowcount} ligne, {len(new_kpi_query)} chars)")

# ================================================================
# ETAPE 2 : Configurer les 9 widgets du dashboard 166
# ================================================================
print("\n=== Configuration widgets dashboard 166 ===")

# Lire les widgets actuels
cur.execute("SELECT widgets FROM APP_Dashboards WHERE id=166")
row = cur.fetchone()
widgets = json.loads(row[0])
print(f"  {len(widgets)} widgets trouves")

# Definitions des nouvelles configs par widget ID
# Note: les noms de champs DOIVENT correspondre aux alias AS des requetes DS
NEW_CONFIGS = {
    'w_1': {
        # KPI CA Total - DS_KPI_RESUME retourne CA (chiffre d'affaires)
        'dataSourceCode': 'DS_KPI_RESUME',
        'dataSourceOrigin': 'template',
        'value_field': 'CA',
        'aggregation': 'SUM',
        'format': 'currency',
        'kpi_color': '#3b82f6',
        'new_title': 'CA Total'
    },
    'w_2': {
        # KPI Marge Totale - DS_KPI_RESUME retourne Marge
        'dataSourceCode': 'DS_KPI_RESUME',
        'dataSourceOrigin': 'template',
        'value_field': 'Marge',
        'aggregation': 'SUM',
        'format': 'currency',
        'kpi_color': '#10b981',
        'new_title': 'Marge Totale'
    },
    'w_3': {
        # KPI Taux de Marge - TauxMarge ajoute ci-dessus
        'dataSourceCode': 'DS_KPI_RESUME',
        'dataSourceOrigin': 'template',
        'value_field': 'TauxMarge',
        'aggregation': 'AVG',
        'format': 'percent',
        'kpi_color': '#8b5cf6',
        'new_title': 'Taux de Marge'
    },
    'w_4': {
        # KPI Nombre Articles Vendus - NbArticlesVendus ajoute ci-dessus
        'dataSourceCode': 'DS_KPI_RESUME',
        'dataSourceOrigin': 'template',
        'value_field': 'NbArticlesVendus',
        'aggregation': 'SUM',
        'format': 'number',
        'kpi_color': '#f59e0b',
        'new_title': "Nb Articles Vendus"
    },
    'w_5': {
        # chart_bar Top 10 Articles par CA
        # DS_CA_AGREGE_ARTICLE retourne : [Code article], [Designation Article], CA, Marge, ...
        'dataSourceCode': 'DS_CA_AGREGE_ARTICLE',
        'dataSourceOrigin': 'template',
        'x_field': u'Désignation Article',   # "Désignation Article"
        'y_field': 'CA',
        'sort_field': 'CA',
        'sort_direction': 'desc',
        'limit_rows': 10,
        'chart_type': 'bar',
        'new_title': 'Top 10 Articles par CA'
    },
    'w_6': {
        # chart_pie Repartition CA par Catalogue
        # DS_VENTES_PAR_CATALOGUE retourne : Catalogue, CA HT, Marge, Marge %, Nb Clients...
        'dataSourceCode': 'DS_VENTES_PAR_CATALOGUE',
        'dataSourceOrigin': 'template',
        'label_field': 'Catalogue',
        'value_field': 'CA HT',
        'sort_field': 'CA HT',
        'sort_direction': 'desc',
        'limit_rows': 10,
        'chart_type': 'pie',
        'new_title': u'Répartition CA par Catalogue'  # "Répartition CA par Catalogue"
    },
    'w_7': {
        # chart_stacked_bar CA et Marge par Catalogue
        'dataSourceCode': 'DS_VENTES_PAR_CATALOGUE',
        'dataSourceOrigin': 'template',
        'x_field': 'Catalogue',
        'y_fields': ['CA HT', 'Marge'],
        'sort_field': 'CA HT',
        'sort_direction': 'desc',
        'chart_type': 'stacked_bar',
        'new_title': 'CA et Marge par Catalogue'
    },
    'w_8': {
        # table Top 10 Vendeurs
        # DS_CA_AGREGE_REPRESENTANT retourne : Representant (alias de "Nom representant"), CA, Marge, Marge %, ...
        'dataSourceCode': 'DS_CA_AGREGE_REPRESENTANT',
        'dataSourceOrigin': 'template',
        'sort_field': 'CA',
        'sort_direction': 'desc',
        'limit_rows': 10,
        'columns': [
            {'key': u'Représentant', 'label': 'Vendeur'},              # "Représentant"
            {'key': 'CA', 'label': 'CA HT', 'format': 'currency'},
            {'key': 'Marge', 'label': 'Marge', 'format': 'currency'},
            {'key': u'Marge %', 'label': 'Tx Marge', 'format': 'percent'},  # "Marge %"
            {'key': 'Nb Documents', 'label': 'Nb Ventes'},
            {'key': 'Nb Clients', 'label': 'Nb Clients'}
        ],
        'pageSize': 10,
        'new_title': 'Top Vendeurs - Performance'
    },
    'w_9': {
        # table Detail Articles
        'dataSourceCode': 'DS_CA_AGREGE_ARTICLE',
        'dataSourceOrigin': 'template',
        'sort_field': 'CA',
        'sort_direction': 'desc',
        'limit_rows': 20,
        'columns': [
            {'key': 'Code article', 'label': 'Code'},
            {'key': u'Désignation Article', 'label': u'Désignation'},  # "Désignation Article"
            {'key': 'CA', 'label': 'CA HT', 'format': 'currency'},
            {'key': 'Marge', 'label': 'Marge', 'format': 'currency'},
            {'key': u'Marge %', 'label': 'Tx Marge', 'format': 'percent'},  # "Marge %"
            {'key': 'Qte Vendue', 'label': u'Qté'}                           # "Qté"
        ],
        'pageSize': 10,
        'new_title': u'Détail Articles - CA et Marge'  # "Détail Articles"
    }
}

# Appliquer les nouvelles configs
updated = 0
for w in widgets:
    wid = w.get('id')
    if wid in NEW_CONFIGS:
        cfg_def = NEW_CONFIGS[wid].copy()
        new_title = cfg_def.pop('new_title', None)
        w['config'] = cfg_def
        if new_title:
            w['title'] = new_title
        print(f"  [{wid}] {str(w.get('type','')):20} '{w.get('title')}' -> {cfg_def.get('dataSourceCode')}")
        updated += 1

print(f"\n  {updated}/{len(widgets)} widgets mis a jour")

# Sauvegarder
new_json = json.dumps(widgets, ensure_ascii=False)
cur.execute("UPDATE APP_Dashboards SET widgets=? WHERE id=166", new_json)
print(f"  -> Dashboard 166 sauvegarde ({cur.rowcount} ligne)")

conn.commit()
conn.close()
print("\nTermine.")
