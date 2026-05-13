# -*- coding: utf-8 -*-
"""
Creer les 3 rapports manquants de Performance Commerciale :
  R4. DS_OBJECTIFS_VS_REALISE + GV  "Objectifs vs Realise par Commercial"
  R5. DS_REMISE_PAR_COMMERCIAL + Pivot "Analyse Remise par Commercial"
  R6. Dashboard "Alertes Objectifs Non Atteints"
"""
import sys, os, warnings, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings('ignore')
from app.database_unified import execute_central

# ───── Utilitaire : echapper les apostrophes pour SQL ─────────────────────
def sql_str(s):
    return s.replace("'", "''")

# ───── Verifier IDs disponibles ───────────────────────────────────────────
gv_max  = execute_central("SELECT MAX(id) AS m FROM APP_GridViews")[0]['m']
pv_max  = execute_central("SELECT MAX(id) AS m FROM APP_Pivots_V2")[0]['m']
db_max  = execute_central("SELECT MAX(id) AS m FROM APP_Dashboards")[0]['m']
print(f"MAX IDs : GV={gv_max}, Pivot={pv_max}, Dashboard={db_max}")

# Verifier IDENTITY
def is_identity(table, col='id'):
    r = execute_central(f"SELECT COLUMNPROPERTY(OBJECT_ID('{table}'), '{col}', 'IsIdentity') AS v")
    return r[0]['v'] == 1 if r else False

gv_ident = is_identity('APP_GridViews')
pv_ident = is_identity('APP_Pivots_V2')
db_ident = is_identity('APP_Dashboards')
print(f"IDENTITY : GV={gv_ident}, Pivot={pv_ident}, Dashboard={db_ident}")

# Verifier si datasource existe deja
def ds_exists(code):
    r = execute_central(f"SELECT COUNT(1) AS n FROM APP_DataSources_Templates WHERE code='{code}'")
    return r[0]['n'] > 0

def gv_exists(code):
    r = execute_central(f"SELECT COUNT(1) AS n FROM APP_GridViews WHERE code='{code}'")
    return r[0]['n'] > 0

def pv_exists(code):
    r = execute_central(f"SELECT COUNT(1) AS n FROM APP_Pivots_V2 WHERE code='{code}'")
    return r[0]['n'] > 0

def db_exists(code):
    r = execute_central(f"SELECT COUNT(1) AS n FROM APP_Dashboards WHERE code='{code}'")
    return r[0]['n'] > 0

# ══════════════════════════════════════════════════════════════════
# RAPPORT 4 : Objectifs vs Realise par Commercial
# ══════════════════════════════════════════════════════════════════
print("\n=== R4 : Objectifs vs Realise par Commercial ===")

DS4_CODE = 'DS_OBJECTIFS_VS_REALISE'
GV4_CODE = 'GV_OBJECTIFS_VS_REALISE'

DS4_QUERY = sql_str("""SELECT
    ISNULL(CAST(en.[Code representant] AS NVARCHAR(50)), 'N/A') AS [Code Commercial],
    ISNULL(en.[Nom representant], 'Non assigne') AS [Commercial],
    li.[societe] AS [Societe],
    YEAR(li.[Date BL]) AS [Annee],
    COUNT(DISTINCT li.[Code client]) AS [Nb Clients],
    COUNT(DISTINCT li.[N Piece]) AS [Nb Documents],
    SUM(li.[Montant HT Net]) AS [CA Realise HT],
    SUM(ISNULL(li.[Marge], 0)) AS [Marge Realisee],
    ISNULL((
        SELECT SUM(o.objectif_ca) FROM APP_Objectifs o
        WHERE o.annee = YEAR(li.[Date BL]) AND o.societe = li.[societe]
          AND o.mois BETWEEN MONTH(@dateDebut) AND MONTH(@dateFin)
    ), 0) AS [Objectif CA Periode],
    CASE
        WHEN ISNULL((
            SELECT SUM(o.objectif_ca) FROM APP_Objectifs o
            WHERE o.annee = YEAR(li.[Date BL]) AND o.societe = li.[societe]
              AND o.mois BETWEEN MONTH(@dateDebut) AND MONTH(@dateFin)
        ), 0) > 0
        THEN CAST(
            SUM(li.[Montant HT Net]) /
            (SELECT SUM(o.objectif_ca) FROM APP_Objectifs o
             WHERE o.annee = YEAR(li.[Date BL]) AND o.societe = li.[societe]
               AND o.mois BETWEEN MONTH(@dateDebut) AND MONTH(@dateFin)
            ) * 100 AS DECIMAL(10, 2))
        ELSE NULL
    END AS [Taux Realisation (%)]
FROM [Lignes_des_ventes] li
INNER JOIN [Entete_des_ventes] en
    ON li.[societe] = en.[societe]
    AND li.[Type Document] = en.[Type Document]
    AND li.[N Piece] = en.[N piece]
WHERE li.[Valorise CA] = 'Oui'
  AND li.[Date BL] BETWEEN @dateDebut AND @dateFin
  AND (@societe IS NULL OR li.[societe] = @societe)
GROUP BY en.[Code representant], en.[Nom representant], li.[societe], YEAR(li.[Date BL])
ORDER BY [CA Realise HT] DESC""")

GV4_COLS = json.dumps([
    {"field": "Code Commercial",    "header": "Code",              "visible": True,  "width": 80,  "type": "text"},
    {"field": "Commercial",         "header": "Commercial",        "visible": True,  "width": 150, "type": "text"},
    {"field": "Societe",            "header": "Societe",           "visible": True,  "width": 100, "type": "text"},
    {"field": "Annee",              "header": "Annee",             "visible": True,  "width": 70,  "type": "number"},
    {"field": "Nb Clients",         "header": "Nb Clients",        "visible": True,  "width": 90,  "type": "number"},
    {"field": "Nb Documents",       "header": "Nb Docs",           "visible": True,  "width": 80,  "type": "number"},
    {"field": "CA Realise HT",      "header": "CA Realise HT",     "visible": True,  "width": 130, "type": "number"},
    {"field": "Marge Realisee",     "header": "Marge Realisee",    "visible": True,  "width": 120, "type": "number"},
    {"field": "Objectif CA Periode","header": "Objectif CA",       "visible": True,  "width": 120, "type": "number"},
    {"field": "Taux Realisation (%)","header": "Taux Real. (%)",   "visible": True,  "width": 110, "type": "number"},
], ensure_ascii=False)

# Creer DS4
if ds_exists(DS4_CODE):
    print(f"  DS {DS4_CODE} existe deja -> mise a jour")
    execute_central(f"""
        UPDATE APP_DataSources_Templates
        SET nom='Objectifs vs Realise par Commercial',
            query_template='{DS4_QUERY}'
        WHERE code='{DS4_CODE}'
    """)
else:
    execute_central(f"""
        INSERT INTO APP_DataSources_Templates (code, nom, query_template, actif)
        VALUES ('{DS4_CODE}',
                'Objectifs vs Realise par Commercial',
                '{DS4_QUERY}', 1)
    """)
    print(f"  DS {DS4_CODE} cree")

# Creer GV4
GV4_COLS_SQL = sql_str(GV4_COLS)
if gv_exists(GV4_CODE):
    print(f"  GV {GV4_CODE} existe deja -> mise a jour")
    execute_central(f"""
        UPDATE APP_GridViews
        SET nom='Objectifs vs Realise par Commercial',
            data_source_code='{DS4_CODE}',
            columns_config='{GV4_COLS_SQL}',
            actif=1
        WHERE code='{GV4_CODE}'
    """)
else:
    execute_central(f"""
        INSERT INTO APP_GridViews (nom, data_source_code, columns_config, actif, code)
        VALUES ('Objectifs vs Realise par Commercial',
                '{DS4_CODE}', '{GV4_COLS_SQL}', 1, '{GV4_CODE}')
    """)
    print(f"  GV {GV4_CODE} cree")

gv4_id = execute_central(f"SELECT id FROM APP_GridViews WHERE code='{GV4_CODE}'")[0]['id']
print(f"  GV ID = {gv4_id}")

# Ajouter au menu Performance Commerciale (ordre 10)
existing_menu = execute_central(f"SELECT id FROM APP_Menus WHERE target_id={gv4_id} AND parent_id=1221")
if not existing_menu:
    execute_central(f"""
        INSERT INTO APP_Menus (nom, type, target_id, parent_id, ordre, code, actif)
        VALUES ('Objectifs vs Realise', 'gridview', {gv4_id}, 1221, 10,
                'PERF_OBJ_REALISE', 1)
    """)
    print(f"  Menu ajoute -> Performance Commerciale ordre=10")

# ══════════════════════════════════════════════════════════════════
# RAPPORT 5 : Pivot Analyse Remise par Commercial
# ══════════════════════════════════════════════════════════════════
print("\n=== R5 : Pivot Analyse Remise par Commercial ===")

DS5_CODE = 'DS_REMISE_PAR_COMMERCIAL'
PV5_CODE = 'PV_remise_par_commercial'

DS5_QUERY = sql_str("""SELECT
    ISNULL(en.[Nom representant], 'Non assigne') AS [Commercial],
    ISNULL(CAST(en.[Code representant] AS NVARCHAR(50)), 'N/A') AS [Code Commercial],
    li.[societe] AS [Societe],
    li.[Code client] AS [Code Client],
    li.[Intitule client] AS [Client],
    li.[Code article] AS [Code Article],
    li.[Designation ligne] AS [Designation],
    ISNULL(li.[Remise 1], 0) AS [Remise 1 (%)],
    ISNULL(li.[Remise 2], 0) AS [Remise 2 (%)],
    SUM(li.[Quantite]) AS [Quantite],
    SUM(li.[Montant HT Net]) AS [CA HT],
    SUM(li.[Quantite] * li.[Prix unitaire]) AS [Montant Brut HT],
    SUM(li.[Quantite] * li.[Prix unitaire]) - SUM(li.[Montant HT Net]) AS [Montant Remise],
    CASE WHEN SUM(li.[Quantite] * li.[Prix unitaire]) > 0
         THEN CAST(
             (SUM(li.[Quantite] * li.[Prix unitaire]) - SUM(li.[Montant HT Net]))
             / SUM(li.[Quantite] * li.[Prix unitaire]) * 100 AS DECIMAL(10,2))
         ELSE 0 END AS [Taux Remise (%)]
FROM [Lignes_des_ventes] li
INNER JOIN [Entete_des_ventes] en
    ON li.[societe] = en.[societe]
    AND li.[Type Document] = en.[Type Document]
    AND li.[N Piece] = en.[N piece]
WHERE li.[Valorise CA] = 'Oui'
  AND li.[Date BL] BETWEEN @dateDebut AND @dateFin
  AND (@societe IS NULL OR li.[societe] = @societe)
GROUP BY
    en.[Nom representant], en.[Code representant],
    li.[societe], li.[Code client], li.[Intitule client],
    li.[Code article], li.[Designation ligne],
    li.[Remise 1], li.[Remise 2]
HAVING SUM(li.[Quantite] * li.[Prix unitaire]) - SUM(li.[Montant HT Net]) > 0
ORDER BY [Montant Remise] DESC""")

PV5_ROWS    = json.dumps([{"field": "Commercial", "label": "Commercial", "type": "text"}], ensure_ascii=False)
PV5_COLS    = json.dumps([{"field": "Societe", "label": "Societe", "type": "text"}], ensure_ascii=False)
PV5_FILTERS = json.dumps([{"field": "Societe", "type": "select", "default": None}], ensure_ascii=False)
PV5_VALUES  = json.dumps([
    {"field": "CA HT",           "label": "CA HT",           "aggregation": "SUM", "format": "number", "decimals": 0, "show_in_totals": True},
    {"field": "Montant Brut HT", "label": "Brut HT",         "aggregation": "SUM", "format": "number", "decimals": 0, "show_in_totals": True},
    {"field": "Montant Remise",  "label": "Montant Remise",  "aggregation": "SUM", "format": "number", "decimals": 0, "show_in_totals": True},
    {"field": "Taux Remise (%)", "label": "Taux Remise (%)", "aggregation": "AVG", "format": "number", "decimals": 2, "show_in_totals": False},
], ensure_ascii=False)

# Creer DS5
DS5_QUERY_SQL = sql_str(DS5_QUERY)
if ds_exists(DS5_CODE):
    print(f"  DS {DS5_CODE} existe deja -> mise a jour")
    execute_central(f"""
        UPDATE APP_DataSources_Templates
        SET nom='Remises par Commercial',
            query_template='{DS5_QUERY_SQL}'
        WHERE code='{DS5_CODE}'
    """)
else:
    execute_central(f"""
        INSERT INTO APP_DataSources_Templates (code, nom, query_template, actif)
        VALUES ('{DS5_CODE}', 'Remises par Commercial', '{DS5_QUERY_SQL}', 1)
    """)
    print(f"  DS {DS5_CODE} cree")

# Creer Pivot 5
PV5_ROWS_SQL    = sql_str(PV5_ROWS)
PV5_COLS_SQL    = sql_str(PV5_COLS)
PV5_FILTERS_SQL = sql_str(PV5_FILTERS)
PV5_VALUES_SQL  = sql_str(PV5_VALUES)

if pv_exists(PV5_CODE):
    print(f"  Pivot {PV5_CODE} existe deja -> mise a jour")
    execute_central(f"""
        UPDATE APP_Pivots_V2
        SET nom='Analyse Remise par Commercial',
            data_source_code='{DS5_CODE}',
            rows_config='{PV5_ROWS_SQL}',
            columns_config='{PV5_COLS_SQL}',
            filters_config='{PV5_FILTERS_SQL}',
            values_config='{PV5_VALUES_SQL}',
            show_grand_totals=1, show_subtotals=1, is_public=1
        WHERE code='{PV5_CODE}'
    """)
else:
    execute_central(f"""
        INSERT INTO APP_Pivots_V2 (
            nom, description, data_source_code,
            rows_config, columns_config, filters_config, values_config,
            show_grand_totals, show_subtotals, is_public,
            grand_total_position, subtotal_position, code,
            created_at, updated_at
        ) VALUES (
            'Analyse Remise par Commercial',
            'Analyse des remises accordees par commercial et type article',
            '{DS5_CODE}',
            '{PV5_ROWS_SQL}', '{PV5_COLS_SQL}', '{PV5_FILTERS_SQL}', '{PV5_VALUES_SQL}',
            1, 1, 1,
            'bottom', 'bottom', '{PV5_CODE}',
            GETDATE(), GETDATE()
        )
    """)
    print(f"  Pivot {PV5_CODE} cree")

pv5_id = execute_central(f"SELECT id FROM APP_Pivots_V2 WHERE code='{PV5_CODE}'")[0]['id']
print(f"  Pivot ID = {pv5_id}")

# Ajouter au menu (ordre 11)
existing_pv_menu = execute_central(f"SELECT id FROM APP_Menus WHERE target_id={pv5_id} AND parent_id=1221 AND type='pivot'")
if not existing_pv_menu:
    execute_central(f"""
        INSERT INTO APP_Menus (nom, type, target_id, parent_id, ordre, code, actif)
        VALUES ('Analyse Remise (Pivot)', 'pivot', {pv5_id}, 1221, 11,
                'PERF_PIVOT_REMISE', 1)
    """)
    print(f"  Menu pivot ajoute -> Performance Commerciale ordre=11")

# ══════════════════════════════════════════════════════════════════
# RAPPORT 6 : Dashboard Alertes Objectifs Non Atteints
# ══════════════════════════════════════════════════════════════════
print("\n=== R6 : Dashboard Alertes Objectifs Non Atteints ===")

DB6_CODE = 'DB_ALERTES_OBJECTIFS'

DB6_WIDGETS = json.dumps([
    # Ligne 1 : KPIs
    {"id": "k1", "type": "kpi", "title": "CA Realise HT",
     "x": 0, "y": 0, "w": 3, "h": 3,
     "config": {"dataSourceCode": "DS_KPI_RESUME", "dataSourceOrigin": "template",
                "value_field": "CA", "aggregation": "SUM",
                "prefix": "", "suffix": "DH", "kpi_color": "#3b82f6"}},
    {"id": "k2", "type": "kpi", "title": "Nb Commerciaux Actifs",
     "x": 3, "y": 0, "w": 3, "h": 3,
     "config": {"dataSourceCode": "DS_VENTES_PAR_COMMERCIAL", "dataSourceOrigin": "template",
                "value_field": "Commercial", "aggregation": "COUNT_DISTINCT",
                "prefix": "", "suffix": "", "kpi_color": "#8b5cf6"}},
    {"id": "k3", "type": "kpi", "title": "Marge Moyenne",
     "x": 6, "y": 0, "w": 3, "h": 3,
     "config": {"dataSourceCode": "DS_KPI_RESUME", "dataSourceOrigin": "template",
                "value_field": "Taux Marge", "aggregation": "AVG",
                "prefix": "", "suffix": "%", "kpi_color": "#10b981"}},
    {"id": "k4", "type": "kpi", "title": "CA Moyen / Commercial",
     "x": 9, "y": 0, "w": 3, "h": 3,
     "config": {"dataSourceCode": "DS_VENTES_PAR_COMMERCIAL", "dataSourceOrigin": "template",
                "value_field": "CA HT", "aggregation": "AVG",
                "prefix": "", "suffix": "DH", "kpi_color": "#f59e0b"}},
    # Ligne 2 : Graphique CA par commercial
    {"id": "ch1", "type": "chart", "title": "CA par Commercial",
     "x": 0, "y": 3, "w": 6, "h": 8,
     "config": {"dataSourceCode": "DS_VENTES_PAR_COMMERCIAL", "dataSourceOrigin": "template",
                "chart_type": "bar",
                "x_field": "Commercial", "y_field": "CA HT",
                "color": "#3b82f6", "show_legend": True}},
    # Ligne 2 droite : Taux Remise par commercial
    {"id": "ch2", "type": "chart", "title": "Marge par Commercial",
     "x": 6, "y": 3, "w": 6, "h": 8,
     "config": {"dataSourceCode": "DS_VENTES_PAR_COMMERCIAL", "dataSourceOrigin": "template",
                "chart_type": "bar",
                "x_field": "Commercial", "y_field": "Marge Brute",
                "color": "#10b981", "show_legend": True}},
    # Ligne 3 : Tableau performance par commercial
    {"id": "t1", "type": "gridview", "title": "Detail Performance par Commercial",
     "x": 0, "y": 11, "w": 12, "h": 9,
     "config": {"gridViewId": gv4_id, "show_toolbar": True}},
], ensure_ascii=False)

DB6_WIDGETS_SQL = sql_str(DB6_WIDGETS)

if db_exists(DB6_CODE):
    print(f"  Dashboard {DB6_CODE} existe deja -> mise a jour")
    execute_central(f"""
        UPDATE APP_Dashboards
        SET nom='Alertes Objectifs Non Atteints',
            description='Suivi des objectifs commerciaux - performance vs realise',
            widgets='{DB6_WIDGETS_SQL}',
            actif=1
        WHERE code='{DB6_CODE}'
    """)
else:
    execute_central(f"""
        INSERT INTO APP_Dashboards (
            nom, description, widgets, is_public, actif,
            date_creation, date_modification, code
        ) VALUES (
            'Alertes Objectifs Non Atteints',
            'Suivi des objectifs commerciaux - performance vs realise',
            '{DB6_WIDGETS_SQL}',
            1, 1, GETDATE(), GETDATE(), '{DB6_CODE}'
        )
    """)
    print(f"  Dashboard {DB6_CODE} cree")

db6_id = execute_central(f"SELECT id FROM APP_Dashboards WHERE code='{DB6_CODE}'")[0]['id']
print(f"  Dashboard ID = {db6_id}")

# Ajouter au menu (ordre 12)
existing_db_menu = execute_central(f"SELECT id FROM APP_Menus WHERE target_id={db6_id} AND parent_id=1221 AND type='dashboard'")
if not existing_db_menu:
    execute_central(f"""
        INSERT INTO APP_Menus (nom, type, target_id, parent_id, ordre, code, actif)
        VALUES ('Alertes Objectifs', 'dashboard', {db6_id}, 1221, 12,
                'PERF_DB_ALERTES', 1)
    """)
    print(f"  Menu dashboard ajoute -> Performance Commerciale ordre=12")

# ══════════════════════════════════════════════════════════════════
# RESULTAT FINAL
# ══════════════════════════════════════════════════════════════════
print("\n=== RESULTAT FINAL — Performance Commerciale (parent_id=1221) ===")
items = execute_central(
    "SELECT id, nom, type, target_id, ordre FROM APP_Menus WHERE parent_id=1221 ORDER BY ordre"
)
for r in items:
    print(f"  [id={r['id']}] ordre={r['ordre']:2} | type='{r['type']}'  target={r['target_id']:4} | {r['nom']}")

print(f"\nTotal : {len(items)} elements dans Performance Commerciale")
