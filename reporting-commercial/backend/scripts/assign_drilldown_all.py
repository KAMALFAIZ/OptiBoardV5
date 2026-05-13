"""
=============================================================================
  ASSIGN DRILLDOWN — Datasources detail maximales pour TOUS pivots & dashboards

  Ce script assigne automatiquement la datasource drilldown la plus detaillee
  (ligne par ligne) a chaque pivot et widget dashboard, selon la categorie
  de la datasource principale.

  Mapping par categorie:
    Ventes         → DS_CA_DETAIL_COMPLET     (57 colonnes, 4 jointures)
    Achats         → DS_ACHATS_DETAIL         (33 colonnes, 3 jointures)
    Stocks         → DS_MVT_DETAIL            (22 colonnes, mouvements)
    Comptabilite   → DS_ECRITURES_DETAIL      (18 colonnes, ecritures)
    Recouvrement   → DS_ECHEANCES_NON_REGLEES (16 colonnes, echeances)
    Analyse/Other  → datasource principale (deja detaillee)

  Execution: python scripts/assign_drilldown_all.py
=============================================================================
"""
import json
import pyodbc
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ============================================================================
#  CONFIG
# ============================================================================
CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=kasoft.selfip.net;"
    "DATABASE=OptiBoard_SaaS;"
    "UID=sa;PWD=SQL@2019"
)

# Categorie de la datasource principale → datasource drilldown detail
CATEGORY_TO_DRILLDOWN = {
    "Ventes":                  "DS_CA_DETAIL_COMPLET",
    "Chiffre d Affaires":      "DS_CA_DETAIL_COMPLET",
    "Marges":                  "DS_CA_DETAIL_COMPLET",
    "Performance Commerciale": "DS_CA_DETAIL_COMPLET",
    "Analyse Clients":         "DS_CA_DETAIL_COMPLET",
    "Pivot V2":                "DS_CA_DETAIL_COMPLET",
    "Achats":                  "DS_ACHATS_DETAIL",
    "Stocks":                  "DS_MVT_DETAIL",
    "Comptabilite":            "DS_ECRITURES_DETAIL",
    "Recouvrement":            "DS_ECHEANCES_NON_REGLEES",
    "dashboard":               "DS_CA_DETAIL_COMPLET",
    "Tableau de Bord":         "DS_CA_DETAIL_COMPLET",
    "Logistique":              "DS_CA_DETAIL_COMPLET",
    "Documents":               "DS_CA_DETAIL_COMPLET",
}

# Mapping direct datasource_code → drilldown (surcharge prioritaire)
DS_CODE_TO_DRILLDOWN = {
    # Ventes agrégés → detail complet
    "DS_VTE_CA_CLIENT":          "DS_CA_DETAIL_COMPLET",
    "DS_VTE_CA_ARTICLE":         "DS_CA_DETAIL_COMPLET",
    "DS_VTE_CA_COMMERCIAL":      "DS_CA_DETAIL_COMPLET",
    "DS_VTE_CA_REGION":          "DS_CA_DETAIL_COMPLET",
    "DS_VTE_CA_FAMILLE":         "DS_CA_DETAIL_COMPLET",
    "DS_VTE_CA_MENSUEL":         "DS_CA_DETAIL_COMPLET",
    "DS_VTE_CA_MODE_REGLEMENT":  "DS_CA_DETAIL_COMPLET",
    "DS_VTE_CA_DEPOT":           "DS_CA_DETAIL_COMPLET",
    "DS_VTE_CA_AFFAIRE":         "DS_CA_DETAIL_COMPLET",
    "DS_VTE_MARGES":             "DS_CA_DETAIL_COMPLET",
    "DS_VTE_REMISES":            "DS_CA_DETAIL_COMPLET",
    "DS_VTE_PANIER_MOYEN":       "DS_CA_DETAIL_COMPLET",
    "DS_VTE_ANALYSE_PRIX":       "DS_CA_DETAIL_COMPLET",
    "DS_VTE_RENTABILITE_CLIENT": "DS_CA_DETAIL_COMPLET",
    "DS_VTE_SAISONNALITE":       "DS_CA_DETAIL_COMPLET",
    "DS_VTE_COMPARATIF":         "DS_CA_DETAIL_COMPLET",
    "DS_VTE_TOP_CLIENTS":        "DS_CA_DETAIL_COMPLET",
    "DS_VTE_TOP_ARTICLES":       "DS_CA_DETAIL_COMPLET",
    "DS_VTE_FIDELITE":           "DS_CA_DETAIL_COMPLET",
    "DS_VTE_CHURN":              "DS_CA_DETAIL_COMPLET",
    "DS_VENTES_GLOBAL":          "DS_CA_DETAIL_COMPLET",
    "DS_VENTES_PAR_CLIENT":      "DS_CA_DETAIL_COMPLET",
    "DS_VENTES_PAR_ARTICLE":     "DS_CA_DETAIL_COMPLET",
    "DS_VENTES_PAR_COMMERCIAL":  "DS_CA_DETAIL_COMPLET",
    "DS_VENTES_PAR_MOIS":        "DS_CA_DETAIL_COMPLET",
    "DS_VENTES_PAR_DEPOT":       "DS_CA_DETAIL_COMPLET",
    "DS_VENTES_PAR_GAMME":       "DS_CA_DETAIL_COMPLET",
    "DS_VENTES_PAR_ZONE":        "DS_CA_DETAIL_COMPLET",
    "DS_VENTES_PAR_CATALOGUE":   "DS_CA_DETAIL_COMPLET",
    "DS_VENTES_PAR_TYPE_DOC":    "DS_CA_DETAIL_COMPLET",
    "DS_VENTES_PAR_AFFAIRE":     "DS_CA_DETAIL_COMPLET",
    "DS_VENTES_PAR_CANAL":       "DS_CA_DETAIL_COMPLET",
    "DS_VENTES_PAR_CATEGORIE_TARIF": "DS_CA_DETAIL_COMPLET",
    "DS_VENTES_CLIENT_MOIS":     "DS_CA_DETAIL_COMPLET",
    "DS_VENTES_ARTICLE_MOIS":    "DS_CA_DETAIL_COMPLET",
    "DS_VENTES_COMMERCIAL_MOIS": "DS_CA_DETAIL_COMPLET",
    "DS_VENTES_FAMILLE_MOIS":    "DS_CA_DETAIL_COMPLET",
    "DS_VENTES_GAMME_MOIS":      "DS_CA_DETAIL_COMPLET",
    "DS_VENTES_CATALOGUE_MOIS":  "DS_CA_DETAIL_COMPLET",
    "DS_CA_AGREGE_CLIENT":       "DS_CA_DETAIL_COMPLET",
    "DS_CA_AGREGE_ARTICLE":      "DS_CA_DETAIL_COMPLET",
    "DS_CA_AGREGE_CATALOGUE":    "DS_CA_DETAIL_COMPLET",
    "DS_CA_AGREGE_REPRESENTANT": "DS_CA_DETAIL_COMPLET",
    "DS_CA_PAR_MOIS_DYNAMIQUE":  "DS_CA_DETAIL_COMPLET",
    "DS_CA_MARGE_DYNAMIQUE":     "DS_CA_DETAIL_COMPLET",
    "DS_CONTRIBUTION_MARGINALE": "DS_CA_DETAIL_COMPLET",
    "DS_TOP_CLIENTS":            "DS_CA_DETAIL_COMPLET",
    "DS_TOP_ARTICLES":           "DS_CA_DETAIL_COMPLET",
    "DS_TOP10_CLIENTS":          "DS_CA_DETAIL_COMPLET",
    "DS_TOP10_ARTICLES":         "DS_CA_DETAIL_COMPLET",
    "DS_KPI_RESUME":             "DS_CA_DETAIL_COMPLET",
    "DS_COMPARATIF_ANNUEL":      "DS_CA_DETAIL_COMPLET",
    "DS_FACTURES":               "DS_CA_DETAIL_COMPLET",
    "DS_AVOIRS":                 "DS_CA_DETAIL_COMPLET",
    "DS_BONS_COMMANDE":          "DS_CA_DETAIL_COMPLET",
    "DS_BONS_LIVRAISON":         "DS_CA_DETAIL_COMPLET",
    "DS_COMMANDES_EN_COURS":     "DS_CA_DETAIL_COMPLET",
    "DS_PREPARATIONS_LIVRAISON": "DS_CA_DETAIL_COMPLET",
    "DS_DEVIS":                  "DS_CA_DETAIL_COMPLET",
    "DS_MARGE_NEGATIVE":         "DS_CA_DETAIL_COMPLET",
    "DS_MARGE_PAR_GAMME":        "DS_CA_DETAIL_COMPLET",
    "DS_PIVOT_VENTES_CA":        "DS_CA_DETAIL_COMPLET",
    "DS_PIVOT_VENTES_LIGNES":    "DS_CA_DETAIL_COMPLET",
    "DS_PIVOT_LIGNES_VENTES":    "DS_CA_DETAIL_COMPLET",
    "DS_BL_NON_FACTURES":        "DS_CA_DETAIL_COMPLET",
    "DS_DOCUMENTS_ANOMALIE":     "DS_CA_DETAIL_COMPLET",
    "DS_SEGMENTATION_ABC":       "DS_CA_DETAIL_COMPLET",
    "DS_CLIENTS_NOUVEAUX":       "DS_CA_DETAIL_COMPLET",
    "DS_CLIENTS_PERDUS":         "DS_CA_DETAIL_COMPLET",
    "DS_MATRICE_CLIENT_ARTICLE": "DS_CA_DETAIL_COMPLET",
    "DS_PANIER_MOYEN_CLIENT":    "DS_CA_DETAIL_COMPLET",
    "DS_EVOLUTION_ABC":          "DS_CA_DETAIL_COMPLET",
    "DS_CONCENTRATION_RISQUE":   "DS_CA_DETAIL_COMPLET",
    "DS_PIPELINE_COMMERCIAL":    "DS_CA_DETAIL_COMPLET",
    "DS_PORTEFEUILLE_COMMERCIAL":"DS_CA_DETAIL_COMPLET",
    "DS_TAUX_TRANSFORMATION":    "DS_CA_DETAIL_COMPLET",
    "DS_DELAIS_ETAPES":          "DS_CA_DETAIL_COMPLET",
    # Achats agrégés → detail achats
    "DS_ACHATS_GLOBAL":          "DS_ACHATS_DETAIL",
    "DS_ACHATS_PAR_FOURNISSEUR": "DS_ACHATS_DETAIL",
    "DS_ACHATS_PAR_ARTICLE":     "DS_ACHATS_DETAIL",
    "DS_ACHATS_PAR_FAMILLE":     "DS_ACHATS_DETAIL",
    "DS_ACHATS_PAR_MOIS":        "DS_ACHATS_DETAIL",
    "DS_ACHATS_PAR_TYPE_DOC":    "DS_ACHATS_DETAIL",
    "DS_ACHATS_PAR_CATALOGUE":   "DS_ACHATS_DETAIL",
    "DS_ACHATS_PAR_ACHETEUR":    "DS_ACHATS_DETAIL",
    "DS_ACHATS_PAR_AFFAIRE":     "DS_ACHATS_DETAIL",
    "DS_ACHATS_VS_VENTES":       "DS_ACHATS_DETAIL",
    "DS_TOP_FOURNISSEURS":       "DS_ACHATS_DETAIL",
    "DS_TOP_ARTICLES_ACHATS":    "DS_ACHATS_DETAIL",
    "DS_FACTURES_ACHATS":        "DS_ACHATS_DETAIL",
    "DS_AVOIRS_ACHATS":          "DS_ACHATS_DETAIL",
    "DS_BONS_RECEPTION":         "DS_ACHATS_DETAIL",
    "DS_COMMANDES_ACHATS":       "DS_ACHATS_DETAIL",
    "DS_COMMANDES_ACHATS_EN_COURS": "DS_ACHATS_DETAIL",
    "DS_COMPARAISON_FOURNISSEURS":  "DS_ACHATS_DETAIL",
    "DS_EVOLUTION_PRIX_ACHATS":     "DS_ACHATS_DETAIL",
    "DS_HISTORIQUE_PRIX_FOURNISSEUR": "DS_ACHATS_DETAIL",
    "DS_ECHEANCES_ACHATS":          "DS_ACHATS_DETAIL",
    # Stocks agrégés → detail mouvements
    "DS_MVT_STOCK_GLOBAL":       "DS_MVT_DETAIL",
    "DS_MVT_PAR_ARTICLE":        "DS_MVT_DETAIL",
    "DS_MVT_PAR_DEPOT":          "DS_MVT_DETAIL",
    "DS_MVT_PAR_TYPE":           "DS_MVT_DETAIL",
    "DS_MVT_PAR_FAMILLE":        "DS_MVT_DETAIL",
    "DS_MVT_PAR_MOIS":           "DS_MVT_DETAIL",
    "DS_MVT_PAR_DOMAINE":        "DS_MVT_DETAIL",
    "DS_MVT_PAR_LOT":            "DS_MVT_DETAIL",
    "DS_MVT_CATALOGUE":          "DS_MVT_DETAIL",
    "DS_MVT_ENTREES":            "DS_MVT_DETAIL",
    "DS_MVT_SORTIES":            "DS_MVT_DETAIL",
    "DS_MVT_INTER_DEPOTS":       "DS_MVT_DETAIL",
    "DS_MVT_INTERNES":           "DS_MVT_DETAIL",
    "DS_MVT_ACHATS":             "DS_MVT_DETAIL",
    "DS_MVT_VENTES":             "DS_MVT_DETAIL",
    "DS_STOCK_ACTUEL":           "DS_MVT_DETAIL",
    "DS_STOCK_PAR_DEPOT":        "DS_MVT_DETAIL",
    "DS_STOCK_VALORISATION":     "DS_MVT_DETAIL",
    "DS_STOCK_ROTATION":         "DS_MVT_DETAIL",
    "DS_STOCK_DORMANT":          "DS_MVT_DETAIL",
    "DS_STOCK_COUVERTURE":       "DS_MVT_DETAIL",
    "DS_STOCK_PEREMPTION":       "DS_MVT_DETAIL",
    "DS_TOP_ARTICLES_MVT":       "DS_MVT_DETAIL",
    "DS_ARTICLES_COMPOSES":      "DS_MVT_DETAIL",
    # Comptabilité agrégée → detail ecritures
    "DS_ECRITURES_GLOBAL":       "DS_ECRITURES_DETAIL",
    "DS_ECRITURES_PAR_JOURNAL":  "DS_ECRITURES_DETAIL",
    "DS_ECRITURES_PAR_COMPTE":   "DS_ECRITURES_DETAIL",
    "DS_ECRITURES_PAR_TIERS":    "DS_ECRITURES_DETAIL",
    "DS_ECRITURES_PAR_MOIS":     "DS_ECRITURES_DETAIL",
    "DS_BALANCE_GENERALE":       "DS_ECRITURES_DETAIL",
    "DS_GRAND_LIVRE":            "DS_ECRITURES_DETAIL",
    "DS_LETTRAGE":               "DS_ECRITURES_DETAIL",
    "DS_CPC_GLOBAL":             "DS_ECRITURES_DETAIL",
    "DS_CPC_PAR_MOIS":           "DS_ECRITURES_DETAIL",
    "DS_CPC_CHARGES":            "DS_ECRITURES_DETAIL",
    "DS_CPC_PRODUITS":           "DS_ECRITURES_DETAIL",
    "DS_BILAN_ACTIF":            "DS_ECRITURES_DETAIL",
    "DS_BILAN_PASSIF":           "DS_ECRITURES_DETAIL",
    "DS_BILAN_SYNTHETIQUE":      "DS_ECRITURES_DETAIL",
    "DS_ACTIF_IMMOBILISE":       "DS_ECRITURES_DETAIL",
    "DS_ACTIF_CIRCULANT":        "DS_ECRITURES_DETAIL",
    "DS_CAPITAUX_PROPRES":       "DS_ECRITURES_DETAIL",
    "DS_DETTES":                 "DS_ECRITURES_DETAIL",
    "DS_TRESORERIE":             "DS_ECRITURES_DETAIL",
    "DS_TRESORERIE_PAR_MOIS":    "DS_ECRITURES_DETAIL",
    "DS_ECHEANCES_COMPTABLES":   "DS_ECRITURES_DETAIL",
    "DS_ANALYTIQUE_GLOBAL":      "DS_ANALYTIQUE_DETAIL",
    "DS_ANALYTIQUE_PAR_PLAN":    "DS_ANALYTIQUE_DETAIL",
    # Recouvrement agrégé → detail echeances
    "DS_BALANCE_AGEE":           "DS_ECHEANCES_NON_REGLEES",
    "DS_ECHEANCES_PAR_CLIENT":   "DS_ECHEANCES_NON_REGLEES",
    "DS_ECHEANCES_PAR_COMMERCIAL": "DS_ECHEANCES_NON_REGLEES",
    "DS_ECHEANCES_PAR_MODE":     "DS_ECHEANCES_NON_REGLEES",
    "DS_ECHEANCES_A_ECHOIR":     "DS_ECHEANCES_NON_REGLEES",
    "DS_KPI_RECOUVREMENT":       "DS_ECHEANCES_NON_REGLEES",
    "DS_DSO":                    "DS_ECHEANCES_NON_REGLEES",
    "DS_COMPORTEMENT_PAIEMENT":  "DS_ECHEANCES_NON_REGLEES",
    "DS_FACTURES_NON_REGLEES":   "DS_ECHEANCES_NON_REGLEES",
    "DS_CREANCES_DOUTEUSES":     "DS_ECHEANCES_NON_REGLEES",
    "DS_PREVISION_ENCAISSEMENTS":"DS_ECHEANCES_NON_REGLEES",
    "DS_REGLEMENTS_PAR_CLIENT":  "DS_ECHEANCES_NON_REGLEES",
    "DS_REGLEMENTS_PAR_MODE":    "DS_ECHEANCES_NON_REGLEES",
    "DS_REGLEMENTS_PAR_PERIODE": "DS_ECHEANCES_NON_REGLEES",
}

# Datasources deja detaillees (ne pas surcharger)
DETAIL_DS_CODES = {
    "DS_CA_DETAIL_COMPLET", "DS_VENTES_DETAIL", "DS_ACHATS_DETAIL",
    "DS_MVT_DETAIL", "DS_ECRITURES_DETAIL", "DS_ANALYTIQUE_DETAIL",
    "DS_ECHEANCES_NON_REGLEES", "DS_PIVOT_VENTES_LIGNES",
    "DS_PIVOT_LIGNES_VENTES",
}

# Fallback par prefixe quand la datasource n'est pas dans le template
PREFIX_TO_DRILLDOWN = [
    ("DS_ACH_",  "DS_ACHATS_DETAIL"),
    ("DS_STK_",  "DS_MVT_DETAIL"),
    ("DS_REC_",  "DS_ECHEANCES_NON_REGLEES"),
    ("DS_DET_",  "DS_ECHEANCES_NON_REGLEES"),
    ("DS_CPT_",  "DS_ECRITURES_DETAIL"),
    ("DS_ECR_",  "DS_ECRITURES_DETAIL"),
    ("DS_ANA_",  "DS_ANALYTIQUE_DETAIL"),
    ("DS_VTE_",  "DS_CA_DETAIL_COMPLET"),
    ("DS_TB_SYNTHESE_ACHATS",     "DS_ACHATS_DETAIL"),
    ("DS_TB_ACHATS",              "DS_ACHATS_DETAIL"),
    ("DS_TB_TOP_FOURNISSEURS",    "DS_ACHATS_DETAIL"),
    ("DS_TB_SYNTHESE_DETTES",     "DS_ACHATS_DETAIL"),
    ("DS_TB_SYNTHESE_STOCK",      "DS_MVT_DETAIL"),
    ("DS_TB_STOCK",               "DS_MVT_DETAIL"),
    ("DS_TB_MVT",                 "DS_MVT_DETAIL"),
    ("DS_TB_SYNTHESE_RECOUVREMENT", "DS_ECHEANCES_NON_REGLEES"),
    ("DS_TB_ENCAISSEMENTS",       "DS_ECHEANCES_NON_REGLEES"),
    ("DS_TB_BALANCE_AGEE",        "DS_ECHEANCES_NON_REGLEES"),
    ("DS_TB_TOP_DEBITEURS",       "DS_ECHEANCES_NON_REGLEES"),
]


def resolve_drilldown(ds_code, category=None):
    """Determine la meilleure datasource drilldown pour un code donne."""
    if ds_code in DETAIL_DS_CODES:
        return None
    if ds_code in DS_CODE_TO_DRILLDOWN:
        return DS_CODE_TO_DRILLDOWN[ds_code]
    if category and category in CATEGORY_TO_DRILLDOWN:
        return CATEGORY_TO_DRILLDOWN[category]
    for prefix, drill in PREFIX_TO_DRILLDOWN:
        if ds_code.startswith(prefix):
            return drill
    return "DS_CA_DETAIL_COMPLET"


# ============================================================================
#  MAIN
# ============================================================================
def main():
    conn = pyodbc.connect(CONN_STR, autocommit=True)
    cursor = conn.cursor()

    # Charger la categorie de chaque datasource template
    cursor.execute(
        "SELECT code, category FROM APP_DataSources_Templates WHERE actif = 1"
    )
    ds_categories = {row[0]: row[1] for row in cursor.fetchall()}

    # ========================================================================
    #  ETAPE 1 : APP_Pivots_V2  →  drilldown_data_source_code
    # ========================================================================
    print("=" * 70)
    print("ETAPE 1 — Assignation drilldown sur APP_Pivots_V2")
    print("=" * 70)

    cursor.execute(
        "SELECT id, nom, data_source_code, drilldown_data_source_code "
        "FROM APP_Pivots_V2 ORDER BY id"
    )
    pivots = cursor.fetchall()

    pivot_updated = 0
    pivot_skipped = 0
    for row in pivots:
        pid, nom, ds_code, current_drill = row
        category = ds_categories.get(ds_code, "")
        drill_code = resolve_drilldown(ds_code, category)

        if not drill_code:
            print(f"  - [{pid:3d}] {nom} — deja detaillee ({ds_code})")
            pivot_skipped += 1
            continue

        if current_drill == drill_code:
            print(f"  = [{pid:3d}] {nom} — deja configure ({drill_code})")
            pivot_skipped += 1
            continue

        cursor.execute(
            "UPDATE APP_Pivots_V2 SET drilldown_data_source_code = ? WHERE id = ?",
            (drill_code, pid),
        )
        old = current_drill or "(aucun)"
        print(f"  + [{pid:3d}] {nom}")
        print(f"         {ds_code} → drilldown: {old} → {drill_code}")
        pivot_updated += 1

    print(f"\n  Pivots: {pivot_updated} mis a jour, {pivot_skipped} inchanges.\n")

    # ========================================================================
    #  ETAPE 2 : APP_Dashboards → widgets[].config.drilldownDsCode
    # ========================================================================
    print("=" * 70)
    print("ETAPE 2 — Assignation drilldown sur widgets Dashboard")
    print("=" * 70)

    cursor.execute("SELECT id, nom, widgets FROM APP_Dashboards ORDER BY id")
    dashboards = cursor.fetchall()

    dash_updated = 0
    dash_skipped = 0
    widgets_updated = 0

    for row in dashboards:
        did, dnom, widgets_json = row
        try:
            widgets = json.loads(widgets_json) if widgets_json else []
        except (json.JSONDecodeError, TypeError):
            print(f"  ! [{did:3d}] {dnom} — JSON widgets invalide, ignore")
            dash_skipped += 1
            continue

        if not widgets:
            dash_skipped += 1
            continue

        changed = False
        for w in widgets:
            cfg = w.get("config", {})
            if not cfg:
                continue

            ds_code = cfg.get("dataSourceCode")
            if not ds_code:
                continue

            current_drill = cfg.get("drilldownDsCode")
            category = ds_categories.get(ds_code, "")
            drill_code = resolve_drilldown(ds_code, category)

            if not drill_code:
                continue
            if current_drill == drill_code:
                continue

            cfg["drilldownDsCode"] = drill_code
            cfg["drilldownDsOrigin"] = "template"
            w["config"] = cfg
            changed = True
            widgets_updated += 1
            wname = w.get("title", w.get("id", "?"))
            print(f"  + [{did:3d}] {dnom} / widget '{wname}'")
            print(f"         {ds_code} → drilldown: {current_drill or '(aucun)'} → {drill_code}")

        if changed:
            cursor.execute(
                "UPDATE APP_Dashboards SET widgets = ? WHERE id = ?",
                (json.dumps(widgets, ensure_ascii=False), did),
            )
            dash_updated += 1
        else:
            dash_skipped += 1

    print(
        f"\n  Dashboards: {dash_updated} mis a jour ({widgets_updated} widgets), "
        f"{dash_skipped} inchanges.\n"
    )

    # ========================================================================
    #  RESUME
    # ========================================================================
    print("=" * 70)
    print("RESUME")
    print("=" * 70)
    print(f"  Pivots:     {pivot_updated} mis a jour")
    print(f"  Dashboards: {dash_updated} mis a jour ({widgets_updated} widgets)")
    print()
    print("Mapping drilldown par categorie:")
    for cat, ds in sorted(CATEGORY_TO_DRILLDOWN.items()):
        print(f"  {cat:30s} → {ds}")
    print()
    print("Termine.")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
