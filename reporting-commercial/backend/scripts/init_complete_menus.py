# -*- coding: utf-8 -*-
"""
=============================================================================
  INIT COMPLETE MENUS — OptiBoard
  Reconstruit l'arbre de navigation complet : 11 sections
  Mapping vers les DataSource Templates existants (240+)
  + creation des templates manquants

  Sections :
    1. Tableau de Bord
    2. Chiffre d'Affaires
    3. Documents Commerciaux
    4. Marges & Rentabilite
    5. Analyse Clients
    6. Performance Commerciale
    7. Tendances & Saisonnalite
    8. Recouvrement & Tresorerie
    9. Stock & Approvisionnement
   10. Achats & Fournisseurs
   11. Service & Logistique
=============================================================================
"""
import pyodbc
import json

CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=kasoft.selfip.net;"
    "DATABASE=OptiBoard_SaaS;"
    "UID=sa;PWD=SQL@2019;"
    "TrustServerCertificate=yes"
)

conn = pyodbc.connect(CONN_STR, autocommit=True)
cursor = conn.cursor()

# =====================================================================
#  COMMON SQL FRAGMENTS (Ventes)
# =====================================================================
BASE_JOIN_VTE = """FROM [Lignes_des_ventes] li
INNER JOIN [Entête_des_ventes] en
    ON li.[societe] = en.[societe]
    AND li.[Type Document] = en.[Type Document]
    AND li.[N° Pièce] = en.[N° pièce]"""

BASE_JOIN_VTE_CL = BASE_JOIN_VTE + """
LEFT JOIN [Clients] cl ON li.[Code client] = cl.[Code client] AND li.[societe] = cl.[societe]"""

BASE_JOIN_VTE_ART = BASE_JOIN_VTE + """
LEFT JOIN [Articles] art ON li.[Code article] = art.[Code Article] AND li.[societe] = art.[societe]"""

BASE_JOIN_VTE_CL_ART = BASE_JOIN_VTE + """
LEFT JOIN [Clients] cl ON li.[Code client] = cl.[Code client] AND li.[societe] = cl.[societe]
LEFT JOIN [Articles] art ON li.[Code article] = art.[Code Article] AND li.[societe] = art.[societe]"""

CA_FILTER = "li.[Valorise CA] = 'Oui'"
DATE_BL = "li.[Date BL] BETWEEN @dateDebut AND @dateFin"
SOC = "(@societe IS NULL OR li.[societe] = @societe)"
COM = "(@commercial IS NULL OR en.[Nom représentant] = @commercial)"

WHERE_CA = f"WHERE {CA_FILTER} AND {DATE_BL} AND {SOC} AND {COM}"
WHERE_ALL = f"WHERE {DATE_BL} AND {SOC} AND {COM}"

# =====================================================================
#  COMMON SQL FRAGMENTS (Stock)
# =====================================================================
TBL_STOCK = "[Mouvement_stock]"
SOC_STK = "(@societe IS NULL OR ms.societe = @societe)"
DATE_STK = "ms.[Date Mouvement] BETWEEN @dateDebut AND @dateFin"

# =====================================================================
#  COMMON SQL FRAGMENTS (Recouvrement)
# =====================================================================
TBL_EV = "[Echéances_Ventes]"
SOC_EV = "(@societe IS NULL OR ev.societe = @societe)"

REG_SUBQUERY_DATE = (
    "LEFT JOIN (SELECT [Id échéance], societe, "
    "SUM([Montant régler]) AS MontantRegle "
    "FROM Imputation_Factures_Ventes "
    "WHERE [Date règlement] <= @dateFin "
    "GROUP BY [Id échéance], societe) reg "
    "ON ev.[N° interne] = reg.[Id échéance] AND ev.societe = reg.societe "
)

# =====================================================================
#  COMMON PARAMETERS JSON
# =====================================================================
PARAMS_DATE_SOC_COM = json.dumps([
    {"name": "dateDebut", "type": "date", "label": "Date début", "required": True, "default": "FIRST_DAY_YEAR"},
    {"name": "dateFin", "type": "date", "label": "Date fin", "required": True, "default": "TODAY"},
    {"name": "societe", "type": "select", "label": "Société", "required": False,
     "source": "query", "query": "SELECT DISTINCT societe as value, societe as label FROM Lignes_des_ventes ORDER BY societe",
     "allow_null": True, "null_label": "(Toutes)"},
    {"name": "commercial", "type": "text", "label": "Commercial", "required": False}
], ensure_ascii=False)

PARAMS_DATE_SOC = json.dumps([
    {"name": "dateDebut", "type": "date", "label": "Date début", "required": True, "default": "FIRST_DAY_YEAR"},
    {"name": "dateFin", "type": "date", "label": "Date fin", "required": True, "default": "TODAY"},
    {"name": "societe", "type": "select", "label": "Société", "required": False,
     "source": "query", "query": "SELECT DISTINCT societe as value, societe as label FROM Lignes_des_ventes ORDER BY societe",
     "allow_null": True, "null_label": "(Toutes)"}
], ensure_ascii=False)

PARAMS_SOC_ONLY = json.dumps([
    {"name": "societe", "type": "select", "label": "Société", "required": False,
     "source": "query", "query": "SELECT DISTINCT societe as value, societe as label FROM Lignes_des_ventes ORDER BY societe",
     "allow_null": True, "null_label": "(Toutes)"}
], ensure_ascii=False)


# =====================================================================
#  HELPER: UPSERT datasource template
# =====================================================================
def upsert_ds(code, nom, query, params=None, category=""):
    if params is None:
        params = PARAMS_DATE_SOC_COM
    cursor.execute("SELECT id FROM APP_DataSources_Templates WHERE code = ?", (code,))
    row = cursor.fetchone()
    if row:
        cursor.execute("""
            UPDATE APP_DataSources_Templates
            SET nom=?, query_template=?, parameters=?, category=?, type='SQL', actif=1
            WHERE code=?
        """, (nom, query, params, category, code))
        return row[0]
    else:
        cursor.execute("""
            INSERT INTO APP_DataSources_Templates (code, nom, query_template, parameters, category, type, actif)
            OUTPUT INSERTED.id VALUES (?, ?, ?, ?, ?, 'SQL', 1)
        """, (code, nom, query, params, category))
        return cursor.fetchone()[0]


# =====================================================================
#  HELPER: UPSERT gridview
# =====================================================================
def upsert_gv(nom, ds_code, columns, description=""):
    cols_json = json.dumps(columns, ensure_ascii=False)
    cursor.execute("SELECT id FROM APP_GridViews WHERE data_source_code = ?", (ds_code,))
    row = cursor.fetchone()
    if row:
        cursor.execute("""
            UPDATE APP_GridViews
            SET nom=?, description=?, columns_config=?, page_size=50, actif=1, show_totals=1
            WHERE id=?
        """, (nom, description, cols_json, row[0]))
        return row[0]
    else:
        cursor.execute("""
            INSERT INTO APP_GridViews (nom, description, columns_config, data_source_code, page_size, actif, is_public, show_totals)
            OUTPUT INSERTED.id VALUES (?, ?, ?, ?, 50, 1, 0, 1)
        """, (nom, description, cols_json, ds_code))
        return cursor.fetchone()[0]


# =====================================================================
#  HELPER: UPSERT pivot
# =====================================================================
def upsert_pivot(nom, ds_code, rows, columns, values, filters=None, description=""):
    cursor.execute("SELECT id FROM APP_Pivots_V2 WHERE data_source_code = ? AND nom = ?", (ds_code, nom))
    row = cursor.fetchone()
    rows_j = json.dumps(rows, ensure_ascii=False)
    cols_j = json.dumps(columns, ensure_ascii=False)
    vals_j = json.dumps(values, ensure_ascii=False)
    filt_j = json.dumps(filters or [], ensure_ascii=False)
    if row:
        cursor.execute("""
            UPDATE APP_Pivots_V2
            SET rows_config=?, columns_config=?, values_config=?, filters_config=?, description=?
            WHERE id=?
        """, (rows_j, cols_j, vals_j, filt_j, description, row[0]))
        return row[0]
    else:
        cursor.execute("""
            INSERT INTO APP_Pivots_V2 (nom, description, data_source_code, rows_config, columns_config, values_config, filters_config, is_public, created_by)
            OUTPUT INSERTED.id VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1)
        """, (nom, description, ds_code, rows_j, cols_j, vals_j, filt_j))
        return cursor.fetchone()[0]


# =====================================================================
#  COLUMN SHORTHAND HELPERS
# =====================================================================
def col(field, header=None, width=120, typ=None, fmt=None):
    c = {"field": field, "header": header or field, "width": width}
    if typ:
        c["type"] = typ
    if fmt:
        c["format"] = fmt
    return c

def col_txt(field, header=None, w=120):
    return col(field, header, w)

def col_num(field, header=None, w=110):
    return col(field, header, w, "number", "#,##0.00")

def col_int(field, header=None, w=90):
    return col(field, header, w, "number")

def col_pct(field, header=None, w=90):
    return col(field, header, w, "number", "#,##0.00")

def col_date(field, header=None, w=110):
    return col(field, header, w, "date")

def val_sum(field, alias=None, label=None, fmt="currency"):
    return {"field": field, "aggregation": "SUM", "alias": alias or f"SUM_{field.replace(' ', '_')}", "format": fmt, "label": label or field}

def val_avg(field, alias=None, label=None, fmt="currency"):
    return {"field": field, "aggregation": "AVG", "alias": alias or f"AVG_{field.replace(' ', '_')}", "format": fmt, "label": label or field}

def val_cnt(field, alias=None, label=None):
    return {"field": field, "aggregation": "COUNT", "alias": alias or f"CNT_{field.replace(' ', '_')}", "format": "number", "label": label or f"Nb {field}"}

def val_dcnt(field, alias=None, label=None):
    return {"field": field, "aggregation": "DISTINCTCOUNT", "alias": alias or f"DCNT_{field.replace(' ', '_')}", "format": "number", "label": label or f"Nb {field}"}


# #####################################################################
#
#  MISSING DATASOURCE TEMPLATES
#  (ceux qui n'existent pas encore dans les scripts existants)
#
# #####################################################################
print("=" * 60)
print("  PHASE 1 : Creation des DataSource Templates manquants")
print("=" * 60)

# --- DS_VTE_KPI_GLOBAL : KPIs Globaux pour Tableau de Bord ---
upsert_ds("DS_VTE_KPI_GLOBAL", "KPIs Globaux", f"""SELECT
    li.societe AS [Societe],
    COUNT(DISTINCT li.[Code client]) AS [Nb Clients Actifs],
    COUNT(DISTINCT li.[Code article]) AS [Nb Articles Vendus],
    COUNT(DISTINCT li.[N° Pièce]) AS [Nb Documents],
    SUM(li.[Quantité]) AS [Quantite Totale],
    SUM(li.[Montant HT Net]) AS [CA HT],
    SUM(li.[Montant TTC Net]) AS [CA TTC],
    SUM(li.[Quantité] * li.[CMUP]) AS [Cout Revient],
    SUM(li.[Montant HT Net]) - SUM(li.[Quantité] * li.[CMUP]) AS [Marge Brute],
    CASE WHEN SUM(li.[Montant HT Net]) <> 0
        THEN ROUND(100.0 * (SUM(li.[Montant HT Net]) - SUM(li.[Quantité] * li.[CMUP])) / SUM(li.[Montant HT Net]), 2)
        ELSE 0 END AS [Taux Marge %],
    CASE WHEN COUNT(DISTINCT li.[N° Pièce]) > 0
        THEN ROUND(SUM(li.[Montant HT Net]) / COUNT(DISTINCT li.[N° Pièce]), 2)
        ELSE 0 END AS [Panier Moyen],
    SUM(li.[Poids net]) AS [Poids Total Kg]
{BASE_JOIN_VTE}
{WHERE_CA}
GROUP BY li.societe""", category="tableau_de_bord")
print("  + DS_VTE_KPI_GLOBAL")

# --- DS_VTE_MARGE_CLIENT : Marge detaillee par Client ---
upsert_ds("DS_VTE_MARGE_CLIENT", "Marge par Client", f"""SELECT
    li.[Code client] AS [Code Client],
    li.[Intitulé client] AS [Client],
    ISNULL(cl.[Catégorie tarifaire], '') AS [Categorie Tarifaire],
    ISNULL(cl.[Région], '') AS [Region],
    ISNULL(cl.[Ville], '') AS [Ville],
    en.[Nom représentant] AS [Commercial],
    li.societe AS [Societe],
    COUNT(DISTINCT li.[N° Pièce]) AS [Nb Documents],
    COUNT(DISTINCT li.[Code article]) AS [Nb Articles],
    SUM(li.[Quantité]) AS [Quantite],
    SUM(li.[Montant HT Net]) AS [CA HT],
    SUM(li.[Montant TTC Net]) AS [CA TTC],
    SUM(li.[Quantité] * li.[CMUP]) AS [Cout Revient],
    SUM(li.[Montant HT Net]) - SUM(li.[Quantité] * li.[CMUP]) AS [Marge Brute],
    CASE WHEN SUM(li.[Montant HT Net]) <> 0
        THEN ROUND(100.0 * (SUM(li.[Montant HT Net]) - SUM(li.[Quantité] * li.[CMUP])) / SUM(li.[Montant HT Net]), 2)
        ELSE 0 END AS [Taux Marge %],
    AVG(li.[Prix unitaire]) AS [Prix Moyen Vente],
    AVG(li.[CMUP]) AS [Prix Moyen Revient],
    SUM(li.[Poids net]) AS [Poids Total]
{BASE_JOIN_VTE_CL}
{WHERE_CA}
GROUP BY li.[Code client], li.[Intitulé client], cl.[Catégorie tarifaire], cl.[Région], cl.[Ville],
         en.[Nom représentant], li.societe
ORDER BY [Marge Brute] DESC""", category="marges")
print("  + DS_VTE_MARGE_CLIENT")

# --- DS_VTE_MARGE_ARTICLE : Marge detaillee par Article ---
upsert_ds("DS_VTE_MARGE_ARTICLE", "Marge par Article", f"""SELECT
    li.[Code article] AS [Code Article],
    li.[Désignation ligne] AS [Designation],
    li.[Catalogue 1] AS [Famille],
    li.[Catalogue 2] AS [Sous Famille],
    li.[Catalogue 3] AS [Catalogue 3],
    li.[Catalogue 4] AS [Catalogue 4],
    li.societe AS [Societe],
    COUNT(DISTINCT li.[Code client]) AS [Nb Clients],
    SUM(li.[Quantité]) AS [Quantite Vendue],
    SUM(li.[Montant HT Net]) AS [CA HT],
    SUM(li.[Quantité] * li.[CMUP]) AS [Cout Revient],
    SUM(li.[Montant HT Net]) - SUM(li.[Quantité] * li.[CMUP]) AS [Marge Brute],
    CASE WHEN SUM(li.[Montant HT Net]) <> 0
        THEN ROUND(100.0 * (SUM(li.[Montant HT Net]) - SUM(li.[Quantité] * li.[CMUP])) / SUM(li.[Montant HT Net]), 2)
        ELSE 0 END AS [Taux Marge %],
    MIN(li.[Prix unitaire]) AS [Prix Min],
    MAX(li.[Prix unitaire]) AS [Prix Max],
    AVG(li.[Prix unitaire]) AS [Prix Moyen Vente],
    AVG(li.[CMUP]) AS [Cout Revient Moyen]
{BASE_JOIN_VTE}
{WHERE_CA}
GROUP BY li.[Code article], li.[Désignation ligne], li.[Catalogue 1], li.[Catalogue 2],
         li.[Catalogue 3], li.[Catalogue 4], li.societe
ORDER BY [Marge Brute] DESC""", category="marges")
print("  + DS_VTE_MARGE_ARTICLE")

# --- DS_VTE_MARGE_CATALOGUE : Marge par Catalogue ---
upsert_ds("DS_VTE_MARGE_CATALOGUE", "Marge par Catalogue", f"""SELECT
    ISNULL(li.[Catalogue 1], 'Non classé') AS [Catalogue 1],
    ISNULL(li.[Catalogue 2], '') AS [Catalogue 2],
    ISNULL(li.[Catalogue 3], '') AS [Catalogue 3],
    ISNULL(li.[Catalogue 4], '') AS [Catalogue 4],
    li.societe AS [Societe],
    COUNT(DISTINCT li.[Code article]) AS [Nb Articles],
    COUNT(DISTINCT li.[Code client]) AS [Nb Clients],
    SUM(li.[Quantité]) AS [Quantite],
    SUM(li.[Montant HT Net]) AS [CA HT],
    SUM(li.[Quantité] * li.[CMUP]) AS [Cout Revient],
    SUM(li.[Montant HT Net]) - SUM(li.[Quantité] * li.[CMUP]) AS [Marge Brute],
    CASE WHEN SUM(li.[Montant HT Net]) <> 0
        THEN ROUND(100.0 * (SUM(li.[Montant HT Net]) - SUM(li.[Quantité] * li.[CMUP])) / SUM(li.[Montant HT Net]), 2)
        ELSE 0 END AS [Taux Marge %]
{BASE_JOIN_VTE}
{WHERE_CA}
GROUP BY li.[Catalogue 1], li.[Catalogue 2], li.[Catalogue 3], li.[Catalogue 4], li.societe
ORDER BY [CA HT] DESC""", category="marges")
print("  + DS_VTE_MARGE_CATALOGUE")

# --- DS_VTE_MARGE_FAMILLE : Marge par Famille ---
upsert_ds("DS_VTE_MARGE_FAMILLE", "Marge par Famille", f"""SELECT
    ISNULL(li.[Catalogue 1], 'Non classé') AS [Famille],
    li.societe AS [Societe],
    COUNT(DISTINCT li.[Code article]) AS [Nb Articles],
    COUNT(DISTINCT li.[Code client]) AS [Nb Clients],
    SUM(li.[Quantité]) AS [Quantite],
    SUM(li.[Poids net]) AS [Poids Total],
    SUM(li.[Montant HT Net]) AS [CA HT],
    SUM(li.[Montant TTC Net]) AS [CA TTC],
    SUM(li.[Quantité] * li.[CMUP]) AS [Cout Revient],
    SUM(li.[Montant HT Net]) - SUM(li.[Quantité] * li.[CMUP]) AS [Marge Brute],
    CASE WHEN SUM(li.[Montant HT Net]) <> 0
        THEN ROUND(100.0 * (SUM(li.[Montant HT Net]) - SUM(li.[Quantité] * li.[CMUP])) / SUM(li.[Montant HT Net]), 2)
        ELSE 0 END AS [Taux Marge %],
    AVG(li.[Prix unitaire]) AS [PV Moyen],
    AVG(li.[CMUP]) AS [PR Moyen]
{BASE_JOIN_VTE}
{WHERE_CA}
GROUP BY li.[Catalogue 1], li.societe
ORDER BY [Marge Brute] DESC""", category="marges")
print("  + DS_VTE_MARGE_FAMILLE")

# --- DS_VTE_MARGE_COMMERCIAL : Marge par Commercial ---
upsert_ds("DS_VTE_MARGE_COMMERCIAL", "Marge par Commercial", f"""SELECT
    en.[Code représentant] AS [Code Commercial],
    ISNULL(en.[Nom représentant], 'Non affecté') AS [Commercial],
    li.societe AS [Societe],
    COUNT(DISTINCT li.[Code client]) AS [Nb Clients],
    COUNT(DISTINCT li.[Code article]) AS [Nb Articles],
    COUNT(DISTINCT li.[N° Pièce]) AS [Nb Documents],
    SUM(li.[Quantité]) AS [Quantite],
    SUM(li.[Montant HT Net]) AS [CA HT],
    SUM(li.[Montant TTC Net]) AS [CA TTC],
    SUM(li.[Quantité] * li.[CMUP]) AS [Cout Revient],
    SUM(li.[Montant HT Net]) - SUM(li.[Quantité] * li.[CMUP]) AS [Marge Brute],
    CASE WHEN SUM(li.[Montant HT Net]) <> 0
        THEN ROUND(100.0 * (SUM(li.[Montant HT Net]) - SUM(li.[Quantité] * li.[CMUP])) / SUM(li.[Montant HT Net]), 2)
        ELSE 0 END AS [Taux Marge %]
{BASE_JOIN_VTE}
{WHERE_CA}
GROUP BY en.[Code représentant], en.[Nom représentant], li.societe
ORDER BY [Marge Brute] DESC""", category="marges")
print("  + DS_VTE_MARGE_COMMERCIAL")

# --- DS_VTE_MARGE_EVOLUTION : Evolution mensuelle Marge ---
upsert_ds("DS_VTE_MARGE_EVOLUTION", "Evolution Mensuelle Marge", f"""SELECT
    YEAR(li.[Date BL]) AS [Annee],
    MONTH(li.[Date BL]) AS [Mois],
    FORMAT(li.[Date BL], 'yyyy-MM') AS [Periode],
    li.societe AS [Societe],
    SUM(li.[Montant HT Net]) AS [CA HT],
    SUM(li.[Montant TTC Net]) AS [CA TTC],
    SUM(li.[Quantité] * li.[CMUP]) AS [Cout Revient],
    SUM(li.[Montant HT Net]) - SUM(li.[Quantité] * li.[CMUP]) AS [Marge Brute],
    CASE WHEN SUM(li.[Montant HT Net]) <> 0
        THEN ROUND(100.0 * (SUM(li.[Montant HT Net]) - SUM(li.[Quantité] * li.[CMUP])) / SUM(li.[Montant HT Net]), 2)
        ELSE 0 END AS [Taux Marge %],
    COUNT(DISTINCT li.[Code client]) AS [Nb Clients],
    COUNT(DISTINCT li.[Code article]) AS [Nb Articles]
{BASE_JOIN_VTE}
{WHERE_CA}
GROUP BY YEAR(li.[Date BL]), MONTH(li.[Date BL]), FORMAT(li.[Date BL], 'yyyy-MM'), li.societe
ORDER BY [Annee] DESC, [Mois] DESC""", category="marges")
print("  + DS_VTE_MARGE_EVOLUTION")

# --- DS_VTE_NOUVEAUX_CLIENTS : Nouveaux clients de la periode ---
upsert_ds("DS_VTE_NOUVEAUX_CLIENTS", "Nouveaux Clients", f"""WITH PremierAchat AS (
    SELECT li2.[Code client], li2.societe, MIN(li2.[Date BL]) AS [Date Premier Achat]
    FROM [Lignes_des_ventes] li2
    WHERE li2.[Valorise CA] = 'Oui'
    GROUP BY li2.[Code client], li2.societe
)
SELECT
    li.[Code client] AS [Code Client],
    li.[Intitulé client] AS [Client],
    pa.[Date Premier Achat],
    ISNULL(cl.[Catégorie tarifaire], '') AS [Categorie Tarifaire],
    ISNULL(cl.[Région], '') AS [Region],
    ISNULL(cl.[Ville], '') AS [Ville],
    en.[Nom représentant] AS [Commercial],
    li.societe AS [Societe],
    COUNT(DISTINCT li.[N° Pièce]) AS [Nb Documents],
    SUM(li.[Quantité]) AS [Quantite],
    SUM(li.[Montant HT Net]) AS [CA HT],
    SUM(li.[Montant TTC Net]) AS [CA TTC],
    SUM(li.[Montant HT Net]) - SUM(li.[Quantité] * li.[CMUP]) AS [Marge Brute],
    CASE WHEN SUM(li.[Montant HT Net]) <> 0
        THEN ROUND(100.0 * (SUM(li.[Montant HT Net]) - SUM(li.[Quantité] * li.[CMUP])) / SUM(li.[Montant HT Net]), 2)
        ELSE 0 END AS [Taux Marge %]
{BASE_JOIN_VTE_CL}
INNER JOIN PremierAchat pa ON li.[Code client] = pa.[Code client] AND li.societe = pa.societe
WHERE {CA_FILTER} AND {DATE_BL} AND {SOC} AND {COM}
  AND pa.[Date Premier Achat] BETWEEN @dateDebut AND @dateFin
GROUP BY li.[Code client], li.[Intitulé client], pa.[Date Premier Achat],
         cl.[Catégorie tarifaire], cl.[Région], cl.[Ville], en.[Nom représentant], li.societe
ORDER BY [CA HT] DESC""", category="analyse_clients")
print("  + DS_VTE_NOUVEAUX_CLIENTS")

# --- DS_VTE_CA_CATALOGUE : CA par Catalogue (4 niveaux) ---
upsert_ds("DS_VTE_CA_CATALOGUE", "CA par Catalogue", f"""SELECT
    ISNULL(li.[Catalogue 1], 'Non classé') AS [Catalogue 1],
    ISNULL(li.[Catalogue 2], '') AS [Catalogue 2],
    ISNULL(li.[Catalogue 3], '') AS [Catalogue 3],
    ISNULL(li.[Catalogue 4], '') AS [Catalogue 4],
    li.societe AS [Societe],
    COUNT(DISTINCT li.[Code article]) AS [Nb Articles],
    COUNT(DISTINCT li.[Code client]) AS [Nb Clients],
    SUM(li.[Quantité]) AS [Quantite],
    SUM(li.[Montant HT Net]) AS [CA HT],
    SUM(li.[Montant TTC Net]) AS [CA TTC],
    SUM(li.[Montant HT Net]) - SUM(li.[Quantité] * li.[CMUP]) AS [Marge Brute],
    CASE WHEN SUM(li.[Montant HT Net]) <> 0
        THEN ROUND(100.0 * (SUM(li.[Montant HT Net]) - SUM(li.[Quantité] * li.[CMUP])) / SUM(li.[Montant HT Net]), 2)
        ELSE 0 END AS [Taux Marge %]
{BASE_JOIN_VTE}
{WHERE_CA}
GROUP BY li.[Catalogue 1], li.[Catalogue 2], li.[Catalogue 3], li.[Catalogue 4], li.societe
ORDER BY [CA HT] DESC""", category="chiffre_affaires")
print("  + DS_VTE_CA_CATALOGUE")

# --- DS_VTE_PERF_RANKING : Ranking Commercial (Performance) ---
upsert_ds("DS_VTE_PERF_RANKING", "Ranking Commerciaux", f"""SELECT
    en.[Code représentant] AS [Code Commercial],
    ISNULL(en.[Nom représentant], 'Non affecté') AS [Commercial],
    li.societe AS [Societe],
    COUNT(DISTINCT li.[Code client]) AS [Nb Clients],
    COUNT(DISTINCT li.[N° Pièce]) AS [Nb Documents],
    SUM(li.[Quantité]) AS [Quantite],
    SUM(li.[Montant HT Net]) AS [CA HT],
    SUM(li.[Montant TTC Net]) AS [CA TTC],
    SUM(li.[Montant HT Net]) - SUM(li.[Quantité] * li.[CMUP]) AS [Marge Brute],
    CASE WHEN SUM(li.[Montant HT Net]) <> 0
        THEN ROUND(100.0 * (SUM(li.[Montant HT Net]) - SUM(li.[Quantité] * li.[CMUP])) / SUM(li.[Montant HT Net]), 2)
        ELSE 0 END AS [Taux Marge %],
    RANK() OVER (ORDER BY SUM(li.[Montant HT Net]) DESC) AS [Rang CA],
    RANK() OVER (ORDER BY SUM(li.[Montant HT Net]) - SUM(li.[Quantité] * li.[CMUP]) DESC) AS [Rang Marge],
    RANK() OVER (ORDER BY COUNT(DISTINCT li.[Code client]) DESC) AS [Rang Clients]
{BASE_JOIN_VTE}
{WHERE_CA}
GROUP BY en.[Code représentant], en.[Nom représentant], li.societe
ORDER BY [CA HT] DESC""", category="performance")
print("  + DS_VTE_PERF_RANKING")

# --- DS_VTE_CA_COMMERCIAL_NvsN1 : Commercial N vs N-1 ---
upsert_ds("DS_VTE_CA_COM_NvsN1", "CA Commercial N vs N-1", f"""SELECT
    en.[Code représentant] AS [Code Commercial],
    ISNULL(en.[Nom représentant], 'Non affecté') AS [Commercial],
    li.societe AS [Societe],
    SUM(CASE WHEN YEAR(li.[Date BL]) = YEAR(GETDATE()) THEN li.[Montant HT Net] ELSE 0 END) AS [CA N],
    SUM(CASE WHEN YEAR(li.[Date BL]) = YEAR(GETDATE()) - 1 THEN li.[Montant HT Net] ELSE 0 END) AS [CA N-1],
    SUM(CASE WHEN YEAR(li.[Date BL]) = YEAR(GETDATE()) THEN li.[Montant HT Net] ELSE 0 END)
    - SUM(CASE WHEN YEAR(li.[Date BL]) = YEAR(GETDATE()) - 1 THEN li.[Montant HT Net] ELSE 0 END) AS [Ecart],
    CASE WHEN SUM(CASE WHEN YEAR(li.[Date BL]) = YEAR(GETDATE()) - 1 THEN li.[Montant HT Net] ELSE 0 END) <> 0
        THEN ROUND(100.0 * (SUM(CASE WHEN YEAR(li.[Date BL]) = YEAR(GETDATE()) THEN li.[Montant HT Net] ELSE 0 END)
            - SUM(CASE WHEN YEAR(li.[Date BL]) = YEAR(GETDATE()) - 1 THEN li.[Montant HT Net] ELSE 0 END))
            / ABS(SUM(CASE WHEN YEAR(li.[Date BL]) = YEAR(GETDATE()) - 1 THEN li.[Montant HT Net] ELSE 0 END)), 2)
        ELSE 0 END AS [Evolution %],
    COUNT(DISTINCT CASE WHEN YEAR(li.[Date BL]) = YEAR(GETDATE()) THEN li.[Code client] END) AS [Nb Clients N],
    COUNT(DISTINCT CASE WHEN YEAR(li.[Date BL]) = YEAR(GETDATE()) - 1 THEN li.[Code client] END) AS [Nb Clients N-1]
{BASE_JOIN_VTE}
WHERE {CA_FILTER} AND YEAR(li.[Date BL]) IN (YEAR(GETDATE()), YEAR(GETDATE()) - 1) AND {SOC}
GROUP BY en.[Code représentant], en.[Nom représentant], li.societe
ORDER BY [CA N] DESC""", params=PARAMS_SOC_ONLY, category="performance")
print("  + DS_VTE_CA_COM_NvsN1")

# --- DS_VTE_CA_ARTICLE_MENSUEL : CA Article par Mois (Tendances) ---
upsert_ds("DS_VTE_CA_ARTICLE_MENSUEL", "CA Article Mensuel", f"""SELECT
    FORMAT(li.[Date BL], 'yyyy-MM') AS [Periode],
    YEAR(li.[Date BL]) AS [Annee],
    MONTH(li.[Date BL]) AS [Mois],
    li.[Code article] AS [Code Article],
    li.[Désignation ligne] AS [Designation],
    li.[Catalogue 1] AS [Famille],
    li.societe AS [Societe],
    SUM(li.[Quantité]) AS [Quantite],
    SUM(li.[Montant HT Net]) AS [CA HT],
    SUM(li.[Montant HT Net]) - SUM(li.[Quantité] * li.[CMUP]) AS [Marge Brute]
{BASE_JOIN_VTE}
{WHERE_CA}
GROUP BY FORMAT(li.[Date BL], 'yyyy-MM'), YEAR(li.[Date BL]), MONTH(li.[Date BL]),
         li.[Code article], li.[Désignation ligne], li.[Catalogue 1], li.societe
ORDER BY [Code Article], [Annee], [Mois]""", category="tendances")
print("  + DS_VTE_CA_ARTICLE_MENSUEL")

# --- DS_VTE_CA_CATALOGUE_MENSUEL : CA Catalogue par Mois ---
upsert_ds("DS_VTE_CA_CATALOGUE_MENSUEL", "CA Catalogue Mensuel", f"""SELECT
    FORMAT(li.[Date BL], 'yyyy-MM') AS [Periode],
    YEAR(li.[Date BL]) AS [Annee],
    MONTH(li.[Date BL]) AS [Mois],
    ISNULL(li.[Catalogue 1], 'Non classé') AS [Famille],
    li.societe AS [Societe],
    SUM(li.[Quantité]) AS [Quantite],
    SUM(li.[Montant HT Net]) AS [CA HT],
    SUM(li.[Montant HT Net]) - SUM(li.[Quantité] * li.[CMUP]) AS [Marge Brute]
{BASE_JOIN_VTE}
{WHERE_CA}
GROUP BY FORMAT(li.[Date BL], 'yyyy-MM'), YEAR(li.[Date BL]), MONTH(li.[Date BL]),
         li.[Catalogue 1], li.societe
ORDER BY [Famille], [Annee], [Mois]""", category="tendances")
print("  + DS_VTE_CA_CATALOGUE_MENSUEL")

# --- DS_VTE_CA_FAMILLE_MENSUEL : CA Famille par Mois ---
upsert_ds("DS_VTE_CA_FAMILLE_MENSUEL", "CA Famille Mensuel", f"""SELECT
    FORMAT(li.[Date BL], 'yyyy-MM') AS [Periode],
    YEAR(li.[Date BL]) AS [Annee],
    MONTH(li.[Date BL]) AS [Mois],
    ISNULL(li.[Catalogue 1], 'Non classé') AS [Famille],
    li.societe AS [Societe],
    COUNT(DISTINCT li.[Code article]) AS [Nb Articles],
    COUNT(DISTINCT li.[Code client]) AS [Nb Clients],
    SUM(li.[Quantité]) AS [Quantite],
    SUM(li.[Montant HT Net]) AS [CA HT],
    SUM(li.[Montant TTC Net]) AS [CA TTC],
    SUM(li.[Montant HT Net]) - SUM(li.[Quantité] * li.[CMUP]) AS [Marge Brute]
{BASE_JOIN_VTE}
{WHERE_CA}
GROUP BY FORMAT(li.[Date BL], 'yyyy-MM'), YEAR(li.[Date BL]), MONTH(li.[Date BL]),
         li.[Catalogue 1], li.societe
ORDER BY [Annee] DESC, [Mois] DESC""", category="tendances")
print("  + DS_VTE_CA_FAMILLE_MENSUEL")

# --- DS_VTE_BL_NON_FACTURES : BL Non Factures (Service & Logistique) ---
upsert_ds("DS_VTE_BL_NON_FACTURES", "BL Non Facturés", f"""SELECT
    li.societe AS [Societe],
    li.[N° Pièce BL] AS [Num BL],
    li.[Date BL],
    li.[Code client] AS [Code Client],
    li.[Intitulé client] AS [Client],
    en.[Nom représentant] AS [Commercial],
    li.[Code article] AS [Code Article],
    li.[Désignation ligne] AS [Designation],
    li.[Quantité BL] AS [Quantite BL],
    li.[Montant HT Net] AS [Montant HT],
    li.[Code dépôt] AS [Code Depot],
    li.[Intitulé dépôt] AS [Depot],
    DATEDIFF(DAY, li.[Date BL], GETDATE()) AS [Age Jours]
{BASE_JOIN_VTE}
WHERE li.[N° Pièce BL] <> ''
  AND NOT EXISTS (
      SELECT 1 FROM [Lignes_des_ventes] f
      WHERE f.[N° Pièce BL] = li.[N° Pièce BL]
        AND f.societe = li.societe
        AND f.[Type Document] IN ('Facture', 'Facture comptabilisée')
  )
  AND {DATE_BL} AND {SOC}
ORDER BY li.[Date BL] DESC""", params=PARAMS_DATE_SOC, category="logistique")
print("  + DS_VTE_BL_NON_FACTURES")

# --- DS_STK_BONS_RECEPTION : Bons de Reception (Service & Logistique) ---
upsert_ds("DS_STK_BONS_RECEPTION", "Bons de Réception", f"""SELECT
    ms.[societe] AS [Societe],
    ms.[N° Pièce] AS [Num Piece],
    ms.[Date Mouvement] AS [Date Reception],
    ms.[Code article] AS [Code Article],
    ms.[Désignation] AS [Designation],
    ms.[Code famille] AS [Code Famille],
    ms.[Intitulé famille] AS [Famille],
    ms.[Catalogue 1], ms.[Catalogue 2],
    ms.[Quantité] AS [Quantite],
    ms.[Prix unitaire] AS [PU],
    ms.[CMUP],
    ms.[Montant Stock],
    ms.[Dépôt], ms.[Code Dépôt],
    ms.[Code tiers] AS [Code Fournisseur],
    ms.[Intitulé tiers] AS [Fournisseur],
    ms.[N° Série / Lot] AS [Lot Serie],
    ms.[Gamme 1], ms.[Gamme 2]
FROM {TBL_STOCK} ms
WHERE ms.[Domaine mouvement] = 'Achat'
  AND ms.[Sens de mouvement] = '1'
  AND {DATE_STK} AND {SOC_STK}
ORDER BY ms.[Date Mouvement] DESC""", params=PARAMS_DATE_SOC, category="logistique")
print("  + DS_STK_BONS_RECEPTION")

# --- DS_VTE_RETOURS_AVOIRS : Retours & Avoirs (Service & Logistique) ---
upsert_ds("DS_VTE_RETOURS_AVOIRS", "Retours & Avoirs", f"""SELECT
    li.societe AS [Societe],
    li.[Type Document],
    li.[N° Pièce] AS [Num Piece],
    li.[Date document] AS [Date Document],
    li.[Code client] AS [Code Client],
    li.[Intitulé client] AS [Client],
    en.[Nom représentant] AS [Commercial],
    li.[Code article] AS [Code Article],
    li.[Désignation ligne] AS [Designation],
    li.[Catalogue 1] AS [Famille],
    li.[Quantité] AS [Quantite],
    li.[Prix unitaire] AS [PU HT],
    li.[Montant HT Net] AS [Montant HT],
    li.[Montant TTC Net] AS [Montant TTC],
    li.[Code dépôt] AS [Code Depot],
    li.[Intitulé dépôt] AS [Depot],
    li.[N° Série/Lot] AS [Lot Serie]
{BASE_JOIN_VTE}
WHERE li.[Type Document] IN ('Bon de retour', 'Facture de retour', 'Facture de retour comptabilisée',
                             'Facture avoir', 'Facture avoir comptabilisée')
  AND TRY_CAST(li.[Date document] AS DATE) BETWEEN CAST(@dateDebut AS DATE) AND CAST(@dateFin AS DATE)
  AND {SOC} AND {COM}
ORDER BY li.[Date document] DESC""", category="logistique")
print("  + DS_VTE_RETOURS_AVOIRS")


# #####################################################################
#
#  PHASE 2 : CREATION DES GRIDVIEWS POUR LES NOUVEAUX TEMPLATES
#
# #####################################################################
print("\n" + "=" * 60)
print("  PHASE 2 : GridViews pour templates manquants")
print("=" * 60)

upsert_gv("KPIs Globaux", "DS_VTE_KPI_GLOBAL", [
    col_txt("Societe", w=90),
    col_int("Nb Clients Actifs", "Nb Clients"),
    col_int("Nb Articles Vendus", "Nb Articles"),
    col_int("Nb Documents", "Nb Docs"),
    col_int("Quantite Totale", "Quantite"),
    col_num("CA HT"), col_num("CA TTC"),
    col_num("Cout Revient"),
    col_num("Marge Brute"),
    col_pct("Taux Marge %", "Marge %"),
    col_num("Panier Moyen"),
    col_num("Poids Total Kg", "Poids Kg"),
], "Tableau de Bord - KPIs")
print("  + GV KPIs Globaux")

upsert_gv("Marge par Client", "DS_VTE_MARGE_CLIENT", [
    col_txt("Code Client", w=100), col_txt("Client", w=200),
    col_txt("Categorie Tarifaire", w=130), col_txt("Region", w=120), col_txt("Ville", w=120),
    col_txt("Commercial", w=140), col_txt("Societe", w=90),
    col_int("Nb Documents", "Nb Docs"), col_int("Nb Articles"),
    col_int("Quantite", "Qte"),
    col_num("CA HT"), col_num("CA TTC"), col_num("Cout Revient"),
    col_num("Marge Brute"), col_pct("Taux Marge %", "Marge %"),
    col_num("Prix Moyen Vente", "PV Moy"), col_num("Prix Moyen Revient", "PR Moy"),
    col_num("Poids Total", "Poids"),
], "Marges - par Client")
print("  + GV Marge par Client")

upsert_gv("Marge par Article", "DS_VTE_MARGE_ARTICLE", [
    col_txt("Code Article", w=110), col_txt("Designation", w=200),
    col_txt("Famille", w=120), col_txt("Sous Famille", w=120),
    col_txt("Catalogue 3", w=100), col_txt("Catalogue 4", w=100),
    col_txt("Societe", w=90),
    col_int("Nb Clients"),
    col_int("Quantite Vendue", "Qte"),
    col_num("CA HT"), col_num("Cout Revient"),
    col_num("Marge Brute"), col_pct("Taux Marge %", "Marge %"),
    col_num("Prix Min"), col_num("Prix Max"),
    col_num("Prix Moyen Vente", "PV Moy"), col_num("Cout Revient Moyen", "PR Moy"),
], "Marges - par Article")
print("  + GV Marge par Article")

upsert_gv("Marge par Catalogue", "DS_VTE_MARGE_CATALOGUE", [
    col_txt("Catalogue 1", w=150), col_txt("Catalogue 2", w=130),
    col_txt("Catalogue 3", w=100), col_txt("Catalogue 4", w=100),
    col_txt("Societe", w=90),
    col_int("Nb Articles"), col_int("Nb Clients"),
    col_int("Quantite", "Qte"),
    col_num("CA HT"), col_num("Cout Revient"),
    col_num("Marge Brute"), col_pct("Taux Marge %", "Marge %"),
], "Marges - par Catalogue")
print("  + GV Marge par Catalogue")

upsert_gv("Marge par Famille", "DS_VTE_MARGE_FAMILLE", [
    col_txt("Famille", w=180), col_txt("Societe", w=90),
    col_int("Nb Articles"), col_int("Nb Clients"),
    col_int("Quantite", "Qte"), col_num("Poids Total", "Poids"),
    col_num("CA HT"), col_num("CA TTC"), col_num("Cout Revient"),
    col_num("Marge Brute"), col_pct("Taux Marge %", "Marge %"),
    col_num("PV Moyen"), col_num("PR Moyen"),
], "Marges - par Famille")
print("  + GV Marge par Famille")

upsert_gv("Marge par Commercial", "DS_VTE_MARGE_COMMERCIAL", [
    col_txt("Code Commercial", w=80), col_txt("Commercial", w=180),
    col_txt("Societe", w=90),
    col_int("Nb Clients"), col_int("Nb Articles"), col_int("Nb Documents", "Nb Docs"),
    col_int("Quantite", "Qte"),
    col_num("CA HT"), col_num("CA TTC"), col_num("Cout Revient"),
    col_num("Marge Brute"), col_pct("Taux Marge %", "Marge %"),
], "Marges - par Commercial")
print("  + GV Marge par Commercial")

upsert_gv("Evolution Mensuelle Marge", "DS_VTE_MARGE_EVOLUTION", [
    col_int("Annee", w=70), col_int("Mois", w=60),
    col_txt("Periode", w=100), col_txt("Societe", w=90),
    col_num("CA HT"), col_num("CA TTC"), col_num("Cout Revient"),
    col_num("Marge Brute"), col_pct("Taux Marge %", "Marge %"),
    col_int("Nb Clients"), col_int("Nb Articles"),
], "Marges - Evolution Mensuelle")
print("  + GV Evolution Marge")

upsert_gv("Nouveaux Clients", "DS_VTE_NOUVEAUX_CLIENTS", [
    col_txt("Code Client", w=100), col_txt("Client", w=200),
    col_date("Date Premier Achat", "1er Achat"),
    col_txt("Categorie Tarifaire", w=130), col_txt("Region", w=120), col_txt("Ville", w=120),
    col_txt("Commercial", w=140), col_txt("Societe", w=90),
    col_int("Nb Documents", "Nb Docs"),
    col_int("Quantite", "Qte"),
    col_num("CA HT"), col_num("CA TTC"),
    col_num("Marge Brute"), col_pct("Taux Marge %", "Marge %"),
], "Analyse Clients - Nouveaux")
print("  + GV Nouveaux Clients")

upsert_gv("CA par Catalogue", "DS_VTE_CA_CATALOGUE", [
    col_txt("Catalogue 1", w=150), col_txt("Catalogue 2", w=130),
    col_txt("Catalogue 3", w=100), col_txt("Catalogue 4", w=100),
    col_txt("Societe", w=90),
    col_int("Nb Articles"), col_int("Nb Clients"),
    col_int("Quantite", "Qte"),
    col_num("CA HT"), col_num("CA TTC"),
    col_num("Marge Brute"), col_pct("Taux Marge %", "Marge %"),
], "Chiffre d'Affaires - par Catalogue")
print("  + GV CA par Catalogue")

upsert_gv("Ranking Commerciaux", "DS_VTE_PERF_RANKING", [
    col_int("Rang CA", w=60), col_int("Rang Marge", w=70), col_int("Rang Clients", w=70),
    col_txt("Code Commercial", w=80), col_txt("Commercial", w=180),
    col_txt("Societe", w=90),
    col_int("Nb Clients"), col_int("Nb Documents", "Nb Docs"),
    col_int("Quantite", "Qte"),
    col_num("CA HT"), col_num("CA TTC"),
    col_num("Marge Brute"), col_pct("Taux Marge %", "Marge %"),
], "Performance - Ranking")
print("  + GV Ranking Commerciaux")

upsert_gv("CA Commercial N vs N-1", "DS_VTE_CA_COM_NvsN1", [
    col_txt("Code Commercial", w=80), col_txt("Commercial", w=180),
    col_txt("Societe", w=90),
    col_num("CA N"), col_num("CA N-1"),
    col_num("Ecart"), col_pct("Evolution %", "Evol %"),
    col_int("Nb Clients N"), col_int("Nb Clients N-1"),
], "Performance - Comparatif Commercial N/N-1")
print("  + GV CA Commercial N vs N-1")

upsert_gv("CA Article Mensuel", "DS_VTE_CA_ARTICLE_MENSUEL", [
    col_txt("Periode", w=100), col_int("Annee", w=70), col_int("Mois", w=60),
    col_txt("Code Article", w=110), col_txt("Designation", w=200),
    col_txt("Famille", w=120), col_txt("Societe", w=90),
    col_int("Quantite", "Qte"),
    col_num("CA HT"), col_num("Marge Brute"),
], "Tendances - CA Article Mensuel")
print("  + GV CA Article Mensuel")

upsert_gv("CA Catalogue Mensuel", "DS_VTE_CA_CATALOGUE_MENSUEL", [
    col_txt("Periode", w=100), col_int("Annee", w=70), col_int("Mois", w=60),
    col_txt("Famille", w=150), col_txt("Societe", w=90),
    col_int("Quantite", "Qte"),
    col_num("CA HT"), col_num("Marge Brute"),
], "Tendances - CA Catalogue Mensuel")
print("  + GV CA Catalogue Mensuel")

upsert_gv("CA Famille Mensuel", "DS_VTE_CA_FAMILLE_MENSUEL", [
    col_txt("Periode", w=100), col_int("Annee", w=70), col_int("Mois", w=60),
    col_txt("Famille", w=180), col_txt("Societe", w=90),
    col_int("Nb Articles"), col_int("Nb Clients"),
    col_int("Quantite", "Qte"),
    col_num("CA HT"), col_num("CA TTC"), col_num("Marge Brute"),
], "Tendances - CA Famille Mensuel")
print("  + GV CA Famille Mensuel")

upsert_gv("BL Non Facturés", "DS_VTE_BL_NON_FACTURES", [
    col_txt("Societe", w=90), col_txt("Num BL", w=120),
    col_date("Date BL"), col_txt("Code Client", w=100), col_txt("Client", w=200),
    col_txt("Commercial", w=140),
    col_txt("Code Article", w=110), col_txt("Designation", w=200),
    col_int("Quantite BL", "Qte BL"),
    col_num("Montant HT"), col_txt("Depot", w=140),
    col_int("Age Jours", "Age (j)"),
], "Service & Logistique - BL Non Facturés")
print("  + GV BL Non Facturés")

upsert_gv("Bons de Réception", "DS_STK_BONS_RECEPTION", [
    col_txt("Societe", w=90), col_txt("Num Piece", w=120),
    col_date("Date Reception"),
    col_txt("Code Article", w=110), col_txt("Designation", w=200),
    col_txt("Famille", w=120), col_txt("Catalogue 1", w=100), col_txt("Catalogue 2", w=100),
    col_int("Quantite", "Qte"), col_num("PU"), col_num("CMUP"),
    col_num("Montant Stock"),
    col_txt("Dépôt", w=140),
    col_txt("Code Fournisseur", w=110), col_txt("Fournisseur", w=200),
    col_txt("Lot Serie", w=120), col_txt("Gamme 1", w=100), col_txt("Gamme 2", w=100),
], "Service & Logistique - Bons de Réception")
print("  + GV Bons de Réception")

upsert_gv("Retours & Avoirs", "DS_VTE_RETOURS_AVOIRS", [
    col_txt("Societe", w=90), col_txt("Type Document", w=180),
    col_txt("Num Piece", w=120), col_date("Date Document"),
    col_txt("Code Client", w=100), col_txt("Client", w=200),
    col_txt("Commercial", w=140),
    col_txt("Code Article", w=110), col_txt("Designation", w=200),
    col_txt("Famille", w=120),
    col_int("Quantite", "Qte"), col_num("PU HT"),
    col_num("Montant HT"), col_num("Montant TTC"),
    col_txt("Depot", w=140), col_txt("Lot Serie", w=120),
], "Service & Logistique - Retours & Avoirs")
print("  + GV Retours & Avoirs")

# --- GridViews manquantes pour Achats (existent en Pivot, besoin GV aussi) ---
upsert_gv("Achats par Fournisseur", "DS_ACH_PAR_FOURNISSEUR", [
    col_txt("Code fournisseur", w=110), col_txt("Intitulé fournisseur", "Fournisseur", w=200),
    col_int("Nb Documents"), col_int("Nb Articles"),
    col_int("Quantité", "Qte"), col_num("Montant HT"), col_num("Montant TTC"),
], "Achats - par Fournisseur")
print("  + GV Achats par Fournisseur")

upsert_gv("Achats par Article", "DS_ACH_PAR_ARTICLE", [
    col_txt("Code article", w=110), col_txt("Désignation", w=200),
    col_txt("Famille", w=120), col_txt("Sous-Famille", w=120), col_txt("Gamme", w=100),
    col_int("Nb Fournisseurs"), col_int("Quantité", "Qte"),
    col_num("Montant HT"),
], "Achats - par Article")
print("  + GV Achats par Article")

upsert_gv("Achats par Famille", "DS_ACH_PAR_FAMILLE", [
    col_txt("Famille", w=150), col_txt("Sous-Famille", w=130),
    col_int("Nb Articles"), col_int("Nb Fournisseurs"),
    col_int("Quantité", "Qte"), col_num("Montant HT"), col_num("Montant TTC"),
], "Achats - par Famille")
print("  + GV Achats par Famille")

upsert_gv("Top Fournisseurs", "DS_ACH_TOP20_FOURNISSEURS", [
    col_txt("Code fournisseur", w=110), col_txt("Intitulé fournisseur", "Fournisseur", w=200),
    col_int("Nb Factures"), col_int("Quantité", "Qte"),
    col_num("Montant HT"), col_num("Montant TTC"),
], "Achats - Top Fournisseurs")
print("  + GV Top Fournisseurs")

upsert_gv("Evolution Achats Mensuelle", "DS_ACH_EVOLUTION_MENSUELLE", [
    col_int("Année", w=70), col_int("Mois", w=60), col_txt("Période", w=100),
    col_int("Nb Fournisseurs"), col_int("Nb Documents"),
    col_int("Quantité", "Qte"), col_num("Montant HT"), col_num("Montant TTC"),
], "Achats - Evolution Mensuelle")
print("  + GV Evolution Achats Mensuelle")

# --- GridView manquante pour Stock Rotation ---
upsert_gv("Rotation des Stocks", "DS_STK_ROTATION", [
    col_txt("Code article", w=110), col_txt("Designation", w=200),
    col_txt("Code famille", w=100), col_txt("Famille", w=150),
    col_int("Qte Stock"), col_num("Valeur Stock"),
    col_int("Qte Sortie Periode"), col_num("Taux Rotation"),
], "Stock - Rotation")
print("  + GV Rotation des Stocks")


# #####################################################################
#
#  PHASE 2b : CREATION DES PIVOTS MANQUANTS
#
# #####################################################################
print("\n" + "=" * 60)
print("  PHASE 2b : Pivots manquants pour l'arbre de navigation")
print("=" * 60)

upsert_pivot("Comparatif N/N-1/N-2", "DS_VTE_COMPARATIF",
    rows=[{"field": "Societe"}],
    columns=[{"field": "Annee"}],
    values=[val_sum("CA HT"), val_sum("CA TTC"), val_sum("Marge Brute")])
print("  + Pivot Comparatif N/N-1/N-2")

upsert_pivot("Evolution CA 12 mois", "DS_VTE_CA_MENSUEL",
    rows=[{"field": "Periode"}],
    columns=[],
    values=[val_sum("CA HT"), val_sum("CA TTC"), val_cnt("Num Piece", label="Nb Docs")])
print("  + Pivot Evolution CA 12 mois")

upsert_pivot("Synthese Mensuelle Direction", "DS_VTE_CA_MENSUEL",
    rows=[{"field": "Mois"}],
    columns=[{"field": "Annee"}],
    values=[val_sum("CA HT"), val_sum("CA TTC")])
print("  + Pivot Synthese Mensuelle Direction")

upsert_pivot("Analyse Marges", "DS_VTE_MARGES",
    rows=[{"field": "Commercial"}, {"field": "Client"}],
    columns=[],
    values=[val_sum("CA HT"), val_sum("Marge Brute"), val_avg("Taux Marge %")])
print("  + Pivot Analyse Marges")

upsert_pivot("Rentabilite Annuelle", "DS_VTE_MARGE_EVOLUTION",
    rows=[{"field": "Annee"}],
    columns=[],
    values=[val_sum("CA HT"), val_sum("Cout Revient"), val_sum("Marge Brute"), val_avg("Taux Marge %")])
print("  + Pivot Rentabilite Annuelle")

upsert_pivot("Rentabilite Mensuelle", "DS_VTE_MARGE_EVOLUTION",
    rows=[{"field": "Periode"}],
    columns=[{"field": "Annee"}],
    values=[val_sum("CA HT"), val_sum("Marge Brute"), val_avg("Taux Marge %")])
print("  + Pivot Rentabilite Mensuelle")

upsert_pivot("Rentabilite Client", "DS_VTE_RENTABILITE_CLIENT",
    rows=[{"field": "Client"}],
    columns=[],
    values=[val_sum("CA HT"), val_sum("Marge Brute"), val_avg("Taux Marge %")])
print("  + Pivot Rentabilite Client")

upsert_pivot("ABC Clients", "DS_REC_PIVOT_TAUX_CLIENT",
    rows=[{"field": "Client"}],
    columns=[],
    values=[val_sum("Montant Facture"), val_sum("Montant Regle"), val_avg("Taux Recouvrement")])
print("  + Pivot ABC Clients")

upsert_pivot("CA Client", "DS_VTE_CA_CLIENT",
    rows=[{"field": "Client"}, {"field": "Region"}],
    columns=[],
    values=[val_sum("CA HT"), val_sum("CA TTC"), val_cnt("Code Article", label="Nb Articles")])
print("  + Pivot CA Client")

upsert_pivot("Comparatif Client", "DS_VTE_COMPARATIF",
    rows=[{"field": "Client"}],
    columns=[{"field": "Annee"}],
    values=[val_sum("CA HT"), val_sum("Marge Brute")])
print("  + Pivot Comparatif Client")

upsert_pivot("Fidelite Client", "DS_VTE_FIDELITE",
    rows=[{"field": "Client"}],
    columns=[],
    values=[val_sum("CA HT"), val_cnt("Num Piece", label="Nb Commandes")])
print("  + Pivot Fidelite Client")

upsert_pivot("RFM Clients", "DS_VTE_RFM",
    rows=[{"field": "Segment RFM"}, {"field": "Client"}],
    columns=[],
    values=[val_sum("CA HT"), val_avg("Score R"), val_avg("Score F"), val_avg("Score M")])
print("  + Pivot RFM Clients")

upsert_pivot("Panier Moyen Clients", "DS_VTE_PANIER_MOYEN",
    rows=[{"field": "Client"}],
    columns=[],
    values=[val_avg("Panier Moyen"), val_sum("CA HT"), val_cnt("Num Piece", label="Nb Commandes")])
print("  + Pivot Panier Moyen Clients")

upsert_pivot("CA Commercial", "DS_VTE_CA_COMMERCIAL",
    rows=[{"field": "Commercial"}],
    columns=[],
    values=[val_sum("CA HT"), val_sum("CA TTC"), val_dcnt("Code Client", label="Nb Clients")])
print("  + Pivot CA Commercial")

upsert_pivot("Performance Commercial", "DS_VTE_PERF_RANKING",
    rows=[{"field": "Commercial"}],
    columns=[],
    values=[val_sum("CA HT"), val_sum("Marge Brute"), val_dcnt("Code Client", label="Nb Clients")])
print("  + Pivot Performance Commercial")

upsert_pivot("Rentabilite Commerciale", "DS_VTE_MARGE_COMMERCIAL",
    rows=[{"field": "Commercial"}],
    columns=[],
    values=[val_sum("CA HT"), val_sum("Cout Revient"), val_sum("Marge Brute"), val_avg("Taux Marge %")])
print("  + Pivot Rentabilite Commerciale")

upsert_pivot("Analyse Remises", "DS_VTE_REMISES",
    rows=[{"field": "Commercial"}, {"field": "Client"}],
    columns=[],
    values=[val_sum("Montant Remise"), val_avg("Taux Remise %"), val_sum("CA HT")])
print("  + Pivot Analyse Remises")

upsert_pivot("Saisonnalite CA", "DS_VTE_SAISONNALITE",
    rows=[{"field": "Mois"}],
    columns=[{"field": "Annee"}],
    values=[val_sum("CA HT"), val_sum("Quantite")])
print("  + Pivot Saisonnalite CA")

upsert_pivot("Saisonnalite Ventes", "DS_VTE_CA_MENSUEL",
    rows=[{"field": "Mois"}],
    columns=[{"field": "Annee"}],
    values=[val_sum("CA HT"), val_sum("CA TTC"), val_cnt("Num Piece", label="Nb Docs")])
print("  + Pivot Saisonnalite Ventes")

upsert_pivot("Analyse Prix de Vente", "DS_VTE_ANALYSE_PRIX",
    rows=[{"field": "Designation"}, {"field": "Famille"}],
    columns=[],
    values=[val_avg("Prix unitaire"), val_avg("CMUP"), val_sum("CA HT")])
print("  + Pivot Analyse Prix de Vente")

# --- Pivots Stock manquants ---
upsert_pivot("ABC Stock", "DS_STK_ABC",
    rows=[{"field": "Classe ABC"}, {"field": "Designation"}],
    columns=[],
    values=[val_sum("Valeur Stock"), val_sum("Qte Stock")])
print("  + Pivot ABC Stock")

upsert_pivot("Rotation Stock", "DS_STK_ROTATION",
    rows=[{"field": "Famille"}, {"field": "Designation"}],
    columns=[],
    values=[val_sum("Qte Stock"), val_sum("Qte Sortie Periode"), val_avg("Taux Rotation")])
print("  + Pivot Rotation Stock")

upsert_pivot("Cout Possession", "DS_STK_COUT_POSSESSION",
    rows=[{"field": "Famille"}, {"field": "Catalogue"}],
    columns=[],
    values=[val_sum("Valeur Stock"), val_sum("Qte Stock"), val_avg("Cout Possession %")])
print("  + Pivot Cout Possession")

upsert_pivot("Couverture Stock", "DS_STK_COUVERTURE",
    rows=[{"field": "Famille"}],
    columns=[],
    values=[val_sum("Qte Stock"), val_sum("Consommation Mensuelle"), val_avg("Couverture Jours")])
print("  + Pivot Couverture Stock")

upsert_pivot("Evolution Stock Mensuelle", "DS_STK_EVOLUTION_MENSUELLE",
    rows=[{"field": "Periode"}],
    columns=[],
    values=[val_sum("Qte Entree"), val_sum("Qte Sortie"), val_sum("Valeur Entree"), val_sum("Valeur Sortie")])
print("  + Pivot Evolution Stock Mensuelle")

upsert_pivot("Matrice ABC-XYZ", "DS_STK_ABC_XYZ",
    rows=[{"field": "Classe ABC"}, {"field": "Classe XYZ"}],
    columns=[],
    values=[val_sum("Valeur Stock"), val_sum("Qte Stock"), val_cnt("Code article", label="Nb Articles")])
print("  + Pivot Matrice ABC-XYZ")

# --- Pivots Achats manquants ---
upsert_pivot("ABC Fournisseurs", "DS_ACH_TOP20_FOURNISSEURS",
    rows=[{"field": "Intitulé fournisseur"}],
    columns=[],
    values=[val_sum("Montant HT"), val_sum("Montant TTC"), val_cnt("Nb Factures")])
print("  + Pivot ABC Fournisseurs")

upsert_pivot("Achats par Periode", "DS_ACH_EVOLUTION_MENSUELLE",
    rows=[{"field": "Période"}],
    columns=[],
    values=[val_sum("Montant HT"), val_sum("Montant TTC"), val_sum("Quantité")])
print("  + Pivot Achats par Periode")

upsert_pivot("Evolution Prix Achats", "DS_ACH_COMPARATIF_PRIX",
    rows=[{"field": "Code article"}],
    columns=[],
    values=[val_avg("Prix Moyen"), val_avg("Prix Min"), val_avg("Prix Max")])
print("  + Pivot Evolution Prix Achats")


# #####################################################################
#
#  PHASE 3 : CONSTRUCTION DE L'ARBRE DE NAVIGATION (11 SECTIONS)
#
# #####################################################################
print("\n" + "=" * 60)
print("  PHASE 3 : Construction de l'arbre de menus (11 sections)")
print("=" * 60)

def get_gv_id(ds_code):
    cursor.execute("SELECT id FROM APP_GridViews WHERE data_source_code = ?", (ds_code,))
    row = cursor.fetchone()
    return row[0] if row else None

def get_pivot_id(ds_code, nom=None):
    if nom:
        cursor.execute("SELECT id FROM APP_Pivots_V2 WHERE data_source_code = ? AND nom = ?", (ds_code, nom))
    else:
        cursor.execute("SELECT id FROM APP_Pivots_V2 WHERE data_source_code = ?", (ds_code,))
    row = cursor.fetchone()
    return row[0] if row else None

def get_dash_id(nom):
    cursor.execute("SELECT id FROM APP_Dashboards WHERE nom = ?", (nom,))
    row = cursor.fetchone()
    return row[0] if row else None

def create_menu(nom, typ, parent_id, ordre, target_id=None, icon=None):
    cursor.execute("""
        INSERT INTO APP_Menus (nom, type, parent_id, ordre, target_id, icon, actif)
        OUTPUT INSERTED.id VALUES (?, ?, ?, ?, ?, ?, 1)
    """, (nom, typ, parent_id, ordre, target_id, icon))
    return cursor.fetchone()[0]

def add_grid(nom, ds_code, parent_id, ordre, icon=None):
    gv_id = get_gv_id(ds_code)
    if gv_id:
        return create_menu(nom, 'gridview', parent_id, ordre, gv_id, icon)
    else:
        print(f"    WARN: pas de GridView pour {ds_code} -> menu skip")
        return None

def add_pivot(nom, ds_code, parent_id, ordre, pivot_nom=None, icon=None):
    pid = get_pivot_id(ds_code, pivot_nom)
    if pid:
        return create_menu(nom, 'pivot', parent_id, ordre, pid, icon)
    else:
        print(f"    WARN: pas de Pivot pour {ds_code} -> menu skip")
        return None

def add_dash(nom, dash_nom, parent_id, ordre, icon=None):
    did = get_dash_id(dash_nom)
    if did:
        return create_menu(nom, 'dashboard', parent_id, ordre, did, icon)
    else:
        print(f"    WARN: pas de Dashboard '{dash_nom}' -> menu skip")
        return None


# --- Nettoyage des menus existants ---
cursor.execute("DELETE FROM APP_Menus")
print("  Menus existants supprimes.")

n_ok = 0
n_skip = 0

def _add_grid(nom, ds_code, parent_id, ordre, icon=None):
    global n_ok, n_skip
    r = add_grid(nom, ds_code, parent_id, ordre, icon)
    if r: n_ok += 1
    else: n_skip += 1
    return r

def _add_pivot(nom, ds_code, parent_id, ordre, pivot_nom=None, icon=None):
    global n_ok, n_skip
    r = add_pivot(nom, ds_code, parent_id, ordre, pivot_nom, icon)
    if r: n_ok += 1
    else: n_skip += 1
    return r

def _add_dash(nom, dash_nom, parent_id, ordre, icon=None):
    global n_ok, n_skip
    r = add_dash(nom, dash_nom, parent_id, ordre, icon)
    if r: n_ok += 1
    else: n_skip += 1
    return r

# =====================================================================
#  SECTION 1 : Tableau de Bord
#  [GRID] KPIs Globaux / Comparatif Annuel / Top 10 Clients / Top 10 Articles
#  [DASH] Comparatif N/N-1
#  [PIVOT] Comparatif N/N-1/N-2 / Evolution CA 12 mois / Synthese Mensuelle
#  [DASH] TB Global / Vue Commerciale
# =====================================================================
s1 = create_menu("Tableau de Bord", "folder", None, 1, icon="LayoutDashboard")
print(f"\n  [1] Tableau de Bord (id={s1})")
o = 1
_add_grid("KPIs Globaux",        "DS_VTE_KPI_GLOBAL",   s1, o); o += 1
_add_grid("Comparatif Annuel",   "DS_VTE_COMPARATIF",   s1, o); o += 1
_add_grid("Top 10 Clients",      "DS_VTE_TOP_CLIENTS",  s1, o); o += 1
_add_grid("Top 10 Articles",     "DS_VTE_TOP_ARTICLES", s1, o); o += 1
_add_dash("Comparatif N / N-1",  "Comparatif N / N-1",  s1, o); o += 1
_add_pivot("Comparatif N/N-1/N-2", "DS_VTE_COMPARATIF", s1, o, "Comparatif N/N-1/N-2"); o += 1
_add_pivot("Evolution CA 12 mois", "DS_VTE_CA_MENSUEL",  s1, o, "Evolution CA 12 mois"); o += 1
_add_pivot("Synthese Mensuelle Direction", "DS_VTE_CA_MENSUEL", s1, o, "Synthese Mensuelle Direction"); o += 1
_add_dash("Tableau de Bord Global",  "Tableau de Bord",  s1, o); o += 1
_add_dash("Vue Commerciale",     "Top 20 Clients",       s1, o); o += 1

# =====================================================================
#  SECTION 2 : Chiffre d'Affaires
#  [GRID] CA par Affaire/Article/Client/Depot/Famille/Catalogue/Periode/Region
#  [DASH] Comparatif N/N-1 / Evolution CA Mensuelle
# =====================================================================
s2 = create_menu("Chiffre d'Affaires", "folder", None, 2, icon="TrendingUp")
print(f"  [2] Chiffre d'Affaires (id={s2})")
o = 1
_add_grid("CA par Affaire",      "DS_VTE_CA_AFFAIRE",   s2, o); o += 1
_add_grid("CA par Article",      "DS_VTE_CA_ARTICLE",   s2, o); o += 1
_add_grid("CA par Client",       "DS_VTE_CA_CLIENT",    s2, o); o += 1
_add_grid("CA par Depot",        "DS_VTE_CA_DEPOT",     s2, o); o += 1
_add_grid("CA par Famille",      "DS_VTE_CA_FAMILLE",   s2, o); o += 1
_add_grid("CA par Catalogue",    "DS_VTE_CA_CATALOGUE", s2, o); o += 1
_add_grid("CA par Periode",      "DS_VTE_CA_MENSUEL",   s2, o); o += 1
_add_grid("CA par Region",       "DS_VTE_CA_REGION",    s2, o); o += 1
_add_dash("Comparatif N/N-1",    "Comparatif N / N-1",  s2, o); o += 1
_add_dash("Evolution CA Mensuelle", "Evolution CA Mensuelle", s2, o); o += 1

# =====================================================================
#  SECTION 3 : Documents Commerciaux
#  [GRID] Factures / BL / BC / Devis / Avoirs / Commandes
#  [GRID] Taux Transformation Devis
#  [DASH] Analyse des Retours / Performance des Devis
# =====================================================================
s3 = create_menu("Documents Commerciaux", "folder", None, 3, icon="FileText")
print(f"  [3] Documents Commerciaux (id={s3})")
o = 1
_add_grid("Factures",            "DS_VTE_FACTURES",     s3, o); o += 1
_add_grid("Bons de Livraison",   "DS_VTE_BL",           s3, o); o += 1
_add_grid("Bons de Commande",    "DS_VTE_BC",           s3, o); o += 1
_add_grid("Devis",               "DS_VTE_DEVIS",        s3, o); o += 1
_add_grid("Avoirs",              "DS_VTE_AVOIRS",       s3, o); o += 1
_add_grid("Commandes en Cours",  "DS_VTE_CMD_EN_COURS", s3, o); o += 1
_add_grid("Taux Transformation Devis", "DS_VTE_PERF_DEVIS", s3, o); o += 1
_add_dash("Analyse des Retours", "Analyse des Retours", s3, o); o += 1
_add_dash("Performance des Devis", "Performance des Devis", s3, o); o += 1

# =====================================================================
#  SECTION 4 : Marges & Rentabilite
#  [GRID] Marge Globale/Client/Article/Catalogue/Famille/Commercial
#  [GRID] Evolution Mensuelle / Detail Complet
#  [PIVOT] Marges / Marge Ligne / Rentabilite Annuelle/Mensuelle/Client
#  [DASH] TB Direction Generale / Vue Commerciale CA & Marge
# =====================================================================
s4 = create_menu("Marges & Rentabilite", "folder", None, 4, icon="PieChart")
print(f"  [4] Marges & Rentabilite (id={s4})")
o = 1
_add_grid("Marge Globale",       "DS_VTE_MARGES",          s4, o); o += 1
_add_grid("Marge par Client",    "DS_VTE_MARGE_CLIENT",    s4, o); o += 1
_add_grid("Marge par Article",   "DS_VTE_MARGE_ARTICLE",   s4, o); o += 1
_add_grid("Marge par Catalogue", "DS_VTE_MARGE_CATALOGUE", s4, o); o += 1
_add_grid("Marge par Famille",   "DS_VTE_MARGE_FAMILLE",   s4, o); o += 1
_add_grid("Marge par Commercial","DS_VTE_MARGE_COMMERCIAL",s4, o); o += 1
_add_grid("Evolution Mensuelle", "DS_VTE_MARGE_EVOLUTION", s4, o); o += 1
_add_grid("Detail Complet",      "DS_VTE_DETAIL_COMPLET",  s4, o); o += 1
_add_pivot("Analyse Marges",     "DS_VTE_MARGES",          s4, o, "Analyse Marges"); o += 1
_add_pivot("Marge par Ligne",    "DS_VTE_MARGES",          s4, o, "Analyse Marges"); o += 1
_add_pivot("Rentabilite Annuelle",  "DS_VTE_MARGE_EVOLUTION", s4, o, "Rentabilite Annuelle"); o += 1
_add_pivot("Rentabilite Mensuelle", "DS_VTE_MARGE_EVOLUTION", s4, o, "Rentabilite Mensuelle"); o += 1
_add_pivot("Rentabilite Client",    "DS_VTE_RENTABILITE_CLIENT", s4, o, "Rentabilite Client"); o += 1
_add_dash("TB Direction Generale",  "Tableau de Bord",     s4, o); o += 1
_add_dash("Vue Commerciale CA & Marge", "Top 20 Articles", s4, o); o += 1

# =====================================================================
#  SECTION 5 : Analyse Clients
#  [GRID] Top Clients / Panier Moyen / Nouveaux / Perdus / Segmentation ABC
#  [GRID] Encours / Historique Reglements / Detail Ventes
#  [PIVOT] ABC Clients / CA Client / Comparatif / Fidelite / RFM / Panier
#  [DASH] RFM / Churn / Fidelite / Top 20 Clients
# =====================================================================
s5 = create_menu("Analyse Clients", "folder", None, 5, icon="Users")
print(f"  [5] Analyse Clients (id={s5})")
o = 1
_add_grid("Top Clients",          "DS_VTE_TOP_CLIENTS",     s5, o); o += 1
_add_grid("Panier Moyen",         "DS_VTE_PANIER_MOYEN",    s5, o); o += 1
_add_grid("Nouveaux Clients",     "DS_VTE_NOUVEAUX_CLIENTS",s5, o); o += 1
_add_grid("Clients Perdus",       "DS_VTE_CLIENTS_INACTIFS", s5, o); o += 1
_add_grid("Segmentation ABC",     "DS_VTE_RFM",             s5, o); o += 1
_add_grid("Encours Clients",      "DS_REC_IMPAYES",         s5, o); o += 1
_add_grid("Historique Reglements", "DS_REC_HISTORIQUE_CLIENT", s5, o); o += 1
_add_grid("Detail Ventes Client",  "DS_VTE_DETAIL_COMPLET", s5, o); o += 1
_add_pivot("ABC Clients",          "DS_REC_PIVOT_TAUX_CLIENT", s5, o, "ABC Clients"); o += 1
_add_pivot("CA Client",            "DS_VTE_CA_CLIENT",      s5, o, "CA Client"); o += 1
_add_pivot("Comparatif Client",    "DS_VTE_COMPARATIF",     s5, o, "Comparatif Client"); o += 1
_add_pivot("Fidelite Client",      "DS_VTE_FIDELITE",       s5, o, "Fidelite Client"); o += 1
_add_pivot("RFM",                  "DS_VTE_RFM",            s5, o, "RFM Clients"); o += 1
_add_pivot("Panier Moyen",         "DS_VTE_PANIER_MOYEN",   s5, o, "Panier Moyen Clients"); o += 1
_add_dash("Analyse RFM",           "Analyse RFM Clients",   s5, o); o += 1
_add_dash("Churn Clients",         "Clients a Risque de Churn", s5, o); o += 1
_add_dash("Fidelite Clients",      "Fidelite Clients",      s5, o); o += 1
_add_dash("Top 20 Clients",        "Top 20 Clients",        s5, o); o += 1

# =====================================================================
#  SECTION 6 : Performance Commerciale
#  [GRID] Performance / Ranking / CA par Commercial / Echeances / CA N vs N-1
#  [PIVOT] CA Commercial / Performance / Rentabilite / Analyse Remise
#  [DASH] TB Commercial / TB Resp. Commercial / Alertes Objectifs
# =====================================================================
s6 = create_menu("Performance Commerciale", "folder", None, 6, icon="Target")
print(f"  [6] Performance Commerciale (id={s6})")
o = 1
_add_grid("Performance par Commercial", "DS_VTE_CA_COMMERCIAL",   s6, o); o += 1
_add_grid("Ranking Commerciaux",        "DS_VTE_PERF_RANKING",    s6, o); o += 1
_add_grid("CA par Commercial",          "DS_VTE_CA_COMMERCIAL",   s6, o); o += 1
_add_grid("Echeances",                  "DS_REC_SUIVI_ECHEANCES", s6, o); o += 1
_add_grid("CA N vs N-1",               "DS_VTE_CA_COM_NvsN1",    s6, o); o += 1
_add_pivot("CA Commercial",            "DS_VTE_CA_COMMERCIAL",    s6, o, "CA Commercial"); o += 1
_add_pivot("Performance Commercial",   "DS_VTE_PERF_RANKING",     s6, o, "Performance Commercial"); o += 1
_add_pivot("Rentabilite Commerciale",   "DS_VTE_MARGE_COMMERCIAL", s6, o, "Rentabilite Commerciale"); o += 1
_add_pivot("Analyse Remises",          "DS_VTE_REMISES",          s6, o, "Analyse Remises"); o += 1
_add_dash("TB Commercial",             "Tableau de Bord",         s6, o); o += 1
_add_dash("TB Resp. Commercial",       "Alertes Objectifs Non Atteints", s6, o); o += 1
_add_dash("Alertes Objectifs",         "Alertes Objectifs Non Atteints", s6, o); o += 1

# =====================================================================
#  SECTION 7 : Tendances & Saisonnalite
#  [GRID] Evolution CA / Comparatif / CA Article/Catalogue/Famille Mois
#  [PIVOT] Saisonnalite CA / Saisonnalite Ventes
#  [DASH] Comparatif N/N-1 / Saisonnalite
# =====================================================================
s7 = create_menu("Tendances & Saisonnalite", "folder", None, 7, icon="Calendar")
print(f"  [7] Tendances & Saisonnalite (id={s7})")
o = 1
_add_grid("Evolution CA Mensuelle",   "DS_VTE_CA_MENSUEL",          s7, o); o += 1
_add_grid("Comparatif N / N-1",       "DS_VTE_COMPARATIF",          s7, o); o += 1
_add_grid("CA Article Mensuel",       "DS_VTE_CA_ARTICLE_MENSUEL",  s7, o); o += 1
_add_grid("CA Catalogue Mensuel",     "DS_VTE_CA_CATALOGUE_MENSUEL",s7, o); o += 1
_add_grid("CA Famille Mensuel",       "DS_VTE_CA_FAMILLE_MENSUEL",  s7, o); o += 1
_add_pivot("Saisonnalite CA",         "DS_VTE_SAISONNALITE",        s7, o, "Saisonnalite CA"); o += 1
_add_pivot("Saisonnalite Ventes",     "DS_VTE_CA_MENSUEL",          s7, o, "Saisonnalite Ventes"); o += 1
_add_dash("Comparatif N/N-1",         "Comparatif N / N-1",         s7, o); o += 1
_add_dash("Saisonnalite",             "Saisonnalite des Ventes (Dashboard)", s7, o); o += 1

# =====================================================================
#  SECTION 8 : Recouvrement & Tresorerie
#  [GRID] Balance Agee / DSO / Creances / Echeances / Reglements / Factures
#  [PIVOT] Creances Tranche / Evolution / Reglements / Taux Recouvrement
#  [DASH] Evolution / Risque Clients / Synthese / TB Recouvrement / Top Debiteurs
# =====================================================================
s8 = create_menu("Recouvrement & Tresorerie", "folder", None, 8, icon="Wallet")
print(f"  [8] Recouvrement & Tresorerie (id={s8})")
o = 1
_add_grid("Balance Agee",              "DS_REC_BALANCE_AGEE",       s8, o); o += 1
_add_grid("Delai Moyen Paiement (DSO)","DS_REC_DELAI_PAIEMENT",    s8, o); o += 1
_add_grid("Creances Impayees",         "DS_REC_IMPAYES",            s8, o); o += 1
_add_grid("Echeances Clients",         "DS_REC_ECHEANCES_DETAIL",   s8, o); o += 1
_add_grid("Reglements Recus",          "DS_REC_REGLEMENTS",         s8, o); o += 1
_add_grid("Factures Echues Non Reglees","DS_REC_ECHUES_NON_REGLEES",s8, o); o += 1
_add_pivot("Creances par Tranche",     "DS_REC_PIVOT_BALANCE_AGEE", s8, o); o += 1
_add_pivot("Evolution Mensuelle",      "DS_REC_PIVOT_EVOLUTION",    s8, o); o += 1
_add_pivot("Reglements par Mode",      "DS_REC_PIVOT_MODE_REGLEMENT", s8, o); o += 1
_add_pivot("Taux Recouvrement",        "DS_REC_PIVOT_TAUX_CLIENT",  s8, o); o += 1
_add_dash("Evolution Recouvrement",    "Evolution Mensuelle Recouvrement", s8, o); o += 1
_add_dash("Risque Clients",            "Niveau de Risque Clients",  s8, o); o += 1
_add_dash("Synthese Recouvrement",     "Synthèse Annuelle Recouvrement", s8, o); o += 1
_add_dash("TB Recouvrement",           "TB Recouvrement Global",    s8, o); o += 1
_add_dash("Top Debiteurs",             "Top 20 Débiteurs",          s8, o); o += 1

# =====================================================================
#  SECTION 9 : Stock & Approvisionnement
#  [GRID] Stock Actuel / Mouvements / Entrees / Sorties / Depot / Rotation / Dormant
#  [PIVOT] ABC / Cout Possession / Couverture / Evolution / ABC-XYZ / Rotation / Valorisation
#  [DASH] ABC Stock / ABC-XYZ / Cout Possession / Couverture / Prevision Rupture / Rotation
# =====================================================================
s9 = create_menu("Stock & Approvisionnement", "folder", None, 9, icon="Package")
print(f"  [9] Stock & Approvisionnement (id={s9})")
o = 1
_add_grid("Stock Actuel",          "DS_STK_ETAT_ACTUEL",  s9, o); o += 1
_add_grid("Mouvements de Stock",   "DS_STK_MOUVEMENTS",   s9, o); o += 1
_add_grid("Entrees de Stock",      "DS_STK_ENTREES",      s9, o); o += 1
_add_grid("Sorties de Stock",      "DS_STK_SORTIES",      s9, o); o += 1
_add_grid("Stock par Depot",       "DS_STK_PAR_DEPOT",    s9, o); o += 1
_add_grid("Rotation des Stocks",   "DS_STK_ROTATION",     s9, o); o += 1
_add_grid("Stock Dormant",         "DS_STK_DORMANT",      s9, o); o += 1
_add_pivot("ABC Stock",            "DS_STK_ABC",           s9, o, "ABC Stock"); o += 1
_add_pivot("Cout de Possession",   "DS_STK_COUT_POSSESSION", s9, o, "Cout Possession"); o += 1
_add_pivot("Couverture de Stock",  "DS_STK_COUVERTURE",   s9, o, "Couverture Stock"); o += 1
_add_pivot("Evolution Stock",      "DS_STK_EVOLUTION_MENSUELLE", s9, o, "Evolution Stock Mensuelle"); o += 1
_add_pivot("Matrice ABC-XYZ",      "DS_STK_ABC_XYZ",      s9, o, "Matrice ABC-XYZ"); o += 1
_add_pivot("Rotation Stock",       "DS_STK_ROTATION",     s9, o, "Rotation Stock"); o += 1
_add_pivot("Valorisation",         "DS_STK_VALORISATION", s9, o); o += 1
_add_dash("Analyse ABC Stock",     "Analyse ABC Stock",         s9, o); o += 1
_add_dash("Classification ABC/XYZ","Classification ABC/XYZ",    s9, o); o += 1
_add_dash("Cout de Possession",    "Coût de Possession du Stock", s9, o); o += 1
_add_dash("Couverture de Stock",   "Couverture de Stock",       s9, o); o += 1
_add_dash("Prevision de Rupture",  "Prévision de Rupture",      s9, o); o += 1
_add_dash("Rotation des Stocks",   "Rotation des Stocks",       s9, o); o += 1

# =====================================================================
#  SECTION 10 : Achats & Fournisseurs
#  [GRID] Achats Global/Fourn./Article/Famille / Factures / Commandes / Top Fourn. / Echeances
#  [PIVOT] ABC Fourn. / Achats Article/Famille/Fourn./Periode / Evolution Prix
#  [DASH] Delais Livraison / Dependance / Evolution Achats / Scoring / Top 20 Fourn.
# =====================================================================
s10 = create_menu("Achats & Fournisseurs", "folder", None, 10, icon="ShoppingCart")
print(f"  [10] Achats & Fournisseurs (id={s10})")
o = 1
_add_grid("Achats Global",          "DS_ACH_FACTURES",           s10, o); o += 1
_add_grid("Achats par Fournisseur", "DS_ACH_PAR_FOURNISSEUR",   s10, o); o += 1
_add_grid("Achats par Article",     "DS_ACH_PAR_ARTICLE",       s10, o); o += 1
_add_grid("Achats par Famille",     "DS_ACH_PAR_FAMILLE",       s10, o); o += 1
_add_grid("Factures Fournisseurs",  "DS_ACH_FACTURES",          s10, o); o += 1
_add_grid("Commandes Fournisseurs", "DS_ACH_COMMANDES_EN_COURS",s10, o); o += 1
_add_grid("Top Fournisseurs",       "DS_ACH_TOP20_FOURNISSEURS",s10, o); o += 1
_add_grid("Echeances Fournisseurs", "DS_DET_ECHEANCES_DETAIL",  s10, o); o += 1
_add_pivot("ABC Fournisseurs",      "DS_ACH_TOP20_FOURNISSEURS",s10, o, "ABC Fournisseurs"); o += 1
_add_pivot("Achats par Article",    "DS_ACH_PAR_ARTICLE",       s10, o); o += 1
_add_pivot("Achats par Famille",    "DS_ACH_PAR_FAMILLE",       s10, o); o += 1
_add_pivot("Achats par Fournisseur","DS_ACH_PAR_FOURNISSEUR",   s10, o); o += 1
_add_pivot("Achats par Periode",    "DS_ACH_EVOLUTION_MENSUELLE",s10, o, "Achats par Periode"); o += 1
_add_pivot("Evolution Prix",        "DS_ACH_COMPARATIF_PRIX",   s10, o, "Evolution Prix Achats"); o += 1
_add_dash("Delais Livraison Fourn.", "Analyse Délais Livraison Fournisseurs", s10, o); o += 1
_add_dash("Dependance Fournisseur",  "Dépendance Fournisseur",   s10, o); o += 1
_add_dash("Evolution Achats",        "Evolution Achats Mensuelle",s10, o); o += 1
_add_dash("Scoring Fournisseurs",    "Scoring Fournisseurs",     s10, o); o += 1
_add_dash("Top 20 Fournisseurs",     "Top 20 Fournisseurs",      s10, o); o += 1

# =====================================================================
#  SECTION 11 : Service & Logistique
#  [GRID] Preparations / BL Non Factures / Bons Reception / Retours & Avoirs
#  [PIVOT] Analyse Prix de Vente
#  [DASH] Retours / Delai Livraison / Flux Stock / Lead Time / Productivite / Taux Service
# =====================================================================
s11 = create_menu("Service & Logistique", "folder", None, 11, icon="Truck")
print(f"  [11] Service & Logistique (id={s11})")
o = 1
_add_grid("Preparations Livraison",  "DS_VTE_PL",               s11, o); o += 1
_add_grid("BL Non Factures",         "DS_VTE_BL_NON_FACTURES",  s11, o); o += 1
_add_grid("Bons de Reception",       "DS_STK_BONS_RECEPTION",   s11, o); o += 1
_add_grid("Retours & Avoirs",        "DS_VTE_RETOURS_AVOIRS",   s11, o); o += 1
_add_pivot("Analyse Prix de Vente",  "DS_VTE_ANALYSE_PRIX",     s11, o, "Analyse Prix de Vente"); o += 1
_add_dash("Analyse des Retours",     "Analyse des Retours",     s11, o); o += 1
_add_dash("Delai de Livraison",      "Délai Moyen de Livraison",s11, o); o += 1
_add_dash("Flux Stock par Depot",    "Flux de Stock par Dépôt",  s11, o); o += 1
_add_dash("Lead Time",               "Lead Time vs Stock Sécurité", s11, o); o += 1
_add_dash("Productivite Logistique", "Productivité Logistique",  s11, o); o += 1
_add_dash("Taux de Service Client",  "Taux de Service Client",   s11, o); o += 1


# #####################################################################
#
#  PHASE 4 : RESUME
#
# #####################################################################
cursor.execute("SELECT COUNT(*) FROM APP_DataSources_Templates WHERE actif = 1")
ds_count = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM APP_GridViews WHERE actif = 1")
gv_count = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM APP_Pivots_V2")
pv_count = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM APP_Dashboards")
dash_count = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM APP_Menus WHERE actif = 1")
menu_count = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM APP_Menus WHERE type = 'folder'")
folder_count = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM APP_Menus WHERE type = 'gridview'")
gv_menu_count = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM APP_Menus WHERE type = 'pivot'")
pv_menu_count = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM APP_Menus WHERE type = 'dashboard'")
dash_menu_count = cursor.fetchone()[0]

print(f"""
{'=' * 60}
  RESUME FINAL
{'=' * 60}
  DataSource Templates actifs : {ds_count}
  GridViews actifs            : {gv_count}
  Pivots V2                   : {pv_count}
  Dashboards                  : {dash_count}
  Menus totaux                : {menu_count}
    - Dossiers                : {folder_count}
    - GridViews               : {gv_menu_count}
    - Pivots                  : {pv_menu_count}
    - Dashboards              : {dash_menu_count}
  Items OK                    : {n_ok}
  Items SKIP (manquants)      : {n_skip}
{'=' * 60}
""")

cursor.close()
conn.close()
