# -*- coding: utf-8 -*-
"""
Crée les Pivots V2 pour la section Chiffre d'Affaires (8 rapports).
Chaque pivot a le maximum de champs disponibles dans le datasource.
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


def make_rows(fields):
    return [{"field": f} for f in fields]

def make_filters(fields):
    return [{"field": f} for f in fields]

def make_value(field, agg="SUM", label=None, fmt="currency"):
    alias = f"{agg}_{field.replace(' ', '_')}"
    return {"field": field, "aggregation": agg, "alias": alias, "format": fmt, "label": label or field}

def upsert_pivot(nom, description, ds_code, rows_fields, cols_fields, values_fields, filters_fields=None):
    """Crée ou met à jour un Pivot V2."""
    rows_json    = json.dumps(make_rows(rows_fields),         ensure_ascii=False)
    cols_json    = json.dumps([{"field": f} for f in cols_fields] if cols_fields else [], ensure_ascii=False)
    values_json  = json.dumps(values_fields,                   ensure_ascii=False)
    filters_json = json.dumps(make_filters(filters_fields or []), ensure_ascii=False)

    existing = cursor.execute(
        "SELECT id FROM APP_Pivots_V2 WHERE nom = ? AND data_source_code = ?",
        (nom, ds_code)
    ).fetchone()

    if existing:
        cursor.execute(
            """UPDATE APP_Pivots_V2
               SET description=?, rows_config=?, columns_config=?,
                   values_config=?, filters_config=?, updated_at=GETDATE()
               WHERE id=?""",
            (description, rows_json, cols_json, values_json, filters_json, existing[0])
        )
        print(f"  UPDATE [{existing[0]}] {nom}")
        return existing[0]
    else:
        cursor.execute(
            """INSERT INTO APP_Pivots_V2
               (nom, description, data_source_code,
                rows_config, columns_config, values_config, filters_config,
                show_grand_totals, show_subtotals, is_public, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1, 1, GETDATE(), GETDATE())""",
            (nom, description, ds_code, rows_json, cols_json, values_json, filters_json)
        )
        new_id = cursor.execute("SELECT @@IDENTITY").fetchone()[0]
        print(f"  INSERT [{int(new_id)}] {nom}")
        return int(new_id)


print("=" * 65)
print("  CRÉATION PIVOTS V2 — SECTION CHIFFRE D'AFFAIRES")
print("=" * 65)

# ─────────────────────────────────────────────────────────────────
# 1. CA par Client
# ─────────────────────────────────────────────────────────────────
V = make_value
upsert_pivot(
    nom="CA par Client",
    description="Chiffre d'affaires, marge et quantités par client",
    ds_code="DS_VTE_CA_CLIENT",
    rows_fields=["Code Client", "Client"],
    cols_fields=[],
    values_fields=[
        V("CA HT",          "SUM", "CA HT",        "currency"),
        V("CA TTC",         "SUM", "CA TTC",        "currency"),
        V("Cout Revient",   "SUM", "Coût Revient",  "currency"),
        V("Marge Brute",    "SUM", "Marge Brute",   "currency"),
        V("Taux Marge %",   "AVG", "Taux Marge %",  "percent"),
        V("Quantite Totale","SUM", "Quantité",      "number"),
        V("Nb Documents",   "SUM", "Nb Docs",       "number"),
    ],
    filters_fields=["Societe", "Commercial"]
)

# ─────────────────────────────────────────────────────────────────
# 2. CA par Article
# ─────────────────────────────────────────────────────────────────
upsert_pivot(
    nom="CA par Article",
    description="Chiffre d'affaires, quantités et marge par article",
    ds_code="DS_VTE_CA_ARTICLE",
    rows_fields=["Famille", "Code Article", "Designation"],
    cols_fields=[],
    values_fields=[
        V("CA HT",           "SUM", "CA HT",        "currency"),
        V("CA TTC",          "SUM", "CA TTC",        "currency"),
        V("Marge Brute",     "SUM", "Marge Brute",   "currency"),
        V("Taux Marge %",    "AVG", "Taux Marge %",  "percent"),
        V("Quantite Vendue", "SUM", "Qté Vendue",    "number"),
        V("Nb Clients",      "SUM", "Nb Clients",    "number"),
        V("Prix Moyen",      "AVG", "Prix Moyen",    "currency"),
    ],
    filters_fields=["Societe", "Famille"]
)

# ─────────────────────────────────────────────────────────────────
# 3. CA par Famille
# ─────────────────────────────────────────────────────────────────
upsert_pivot(
    nom="CA par Famille",
    description="Chiffre d'affaires et marge par famille et sous-famille",
    ds_code="DS_VTE_CA_FAMILLE",
    rows_fields=["Famille", "Sous Famille"],
    cols_fields=[],
    values_fields=[
        V("CA HT",       "SUM", "CA HT",        "currency"),
        V("CA TTC",      "SUM", "CA TTC",        "currency"),
        V("Marge Brute", "SUM", "Marge Brute",   "currency"),
        V("Taux Marge %","AVG", "Taux Marge %",  "percent"),
        V("Quantite",    "SUM", "Quantité",      "number"),
        V("Nb Articles", "SUM", "Nb Articles",   "number"),
        V("Nb Clients",  "SUM", "Nb Clients",    "number"),
    ],
    filters_fields=["Societe"]
)

# ─────────────────────────────────────────────────────────────────
# 4. CA par Catalogue
# ─────────────────────────────────────────────────────────────────
upsert_pivot(
    nom="CA par Catalogue",
    description="Chiffre d'affaires par niveaux de catalogue (1-4)",
    ds_code="DS_VTE_CA_CATALOGUE",
    rows_fields=["Catalogue 1", "Catalogue 2", "Catalogue 3", "Catalogue 4"],
    cols_fields=[],
    values_fields=[
        V("CA HT",       "SUM", "CA HT",        "currency"),
        V("CA TTC",      "SUM", "CA TTC",        "currency"),
        V("Marge Brute", "SUM", "Marge Brute",   "currency"),
        V("Taux Marge %","AVG", "Taux Marge %",  "percent"),
        V("Quantite",    "SUM", "Quantité",      "number"),
        V("Nb Articles", "SUM", "Nb Articles",   "number"),
        V("Nb Clients",  "SUM", "Nb Clients",    "number"),
    ],
    filters_fields=["Societe"]
)

# ─────────────────────────────────────────────────────────────────
# 5. CA par Période (Mensuel)
# ─────────────────────────────────────────────────────────────────
upsert_pivot(
    nom="CA par Période",
    description="Évolution mensuelle du CA et des marges par année/mois",
    ds_code="DS_VTE_CA_MENSUEL",
    rows_fields=["Annee", "Mois"],
    cols_fields=[],
    values_fields=[
        V("CA HT",       "SUM", "CA HT",        "currency"),
        V("CA TTC",      "SUM", "CA TTC",        "currency"),
        V("Cout Revient","SUM", "Coût Revient",  "currency"),
        V("Marge Brute", "SUM", "Marge Brute",   "currency"),
        V("Taux Marge %","AVG", "Taux Marge %",  "percent"),
        V("Quantite",    "SUM", "Quantité",      "number"),
        V("Nb Clients",  "SUM", "Nb Clients",    "number"),
        V("Nb Documents","SUM", "Nb Docs",       "number"),
        V("Nb Articles", "SUM", "Nb Articles",   "number"),
    ],
    filters_fields=["Societe"]
)

# ─────────────────────────────────────────────────────────────────
# 6. CA par Région
# ─────────────────────────────────────────────────────────────────
upsert_pivot(
    nom="CA par Région",
    description="Chiffre d'affaires par région et ville",
    ds_code="DS_VTE_CA_REGION",
    rows_fields=["Region", "Ville"],
    cols_fields=[],
    values_fields=[
        V("CA HT",       "SUM", "CA HT",        "currency"),
        V("CA TTC",      "SUM", "CA TTC",        "currency"),
        V("Marge Brute", "SUM", "Marge Brute",   "currency"),
        V("Taux Marge %","AVG", "Taux Marge %",  "percent"),
        V("Nb Clients",  "SUM", "Nb Clients",    "number"),
    ],
    filters_fields=["Societe"]
)

# ─────────────────────────────────────────────────────────────────
# 7. CA par Dépôt
# ─────────────────────────────────────────────────────────────────
upsert_pivot(
    nom="CA par Dépôt",
    description="Chiffre d'affaires, quantités et poids par dépôt",
    ds_code="DS_VTE_CA_DEPOT",
    rows_fields=["Code Depot", "Depot"],
    cols_fields=[],
    values_fields=[
        V("CA HT",          "SUM", "CA HT",          "currency"),
        V("Marge Brute",    "SUM", "Marge Brute",    "currency"),
        V("Quantite",       "SUM", "Quantité",       "number"),
        V("Poids Net Total","SUM", "Poids Net (kg)", "number"),
        V("Nb Clients",     "SUM", "Nb Clients",     "number"),
        V("Nb Articles",    "SUM", "Nb Articles",    "number"),
    ],
    filters_fields=["Societe"]
)

# ─────────────────────────────────────────────────────────────────
# 8. CA par Affaire
# ─────────────────────────────────────────────────────────────────
upsert_pivot(
    nom="CA par Affaire",
    description="Chiffre d'affaires et marge par affaire",
    ds_code="DS_VTE_CA_AFFAIRE",
    rows_fields=["Code Affaire", "Affaire"],
    cols_fields=[],
    values_fields=[
        V("CA HT",       "SUM", "CA HT",        "currency"),
        V("Marge Brute", "SUM", "Marge Brute",   "currency"),
        V("Taux Marge %","AVG", "Taux Marge %",  "percent"),
        V("Nb Clients",  "SUM", "Nb Clients",    "number"),
        V("Nb Documents","SUM", "Nb Docs",       "number"),
    ],
    filters_fields=["Societe"]
)

print()
print("=" * 65)
print("  Vérification des IDs créés")
print("=" * 65)
pivots = cursor.execute("""
    SELECT id, nom, data_source_code
    FROM APP_Pivots_V2
    WHERE data_source_code IN (
        'DS_VTE_CA_CLIENT','DS_VTE_CA_ARTICLE','DS_VTE_CA_FAMILLE',
        'DS_VTE_CA_CATALOGUE','DS_VTE_CA_MENSUEL','DS_VTE_CA_REGION',
        'DS_VTE_CA_DEPOT','DS_VTE_CA_AFFAIRE'
    )
    ORDER BY id
""").fetchall()

for p in pivots:
    print(f"  [{p[0]}] {p[1]:<30} {p[2]}")

cursor.close()
conn.close()
