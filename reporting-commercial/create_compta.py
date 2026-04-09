import requests, json

BASE = "http://localhost:8084/api"
H = {"Content-Type": "application/json", "X-DWH-Code": "FO"}
APP = "comptabilite"

created = {"grids": [], "pivots": [], "dashboards": []}
errors = []

def post(path, data):
    r = requests.post(f"{BASE}{path}", json=data, headers=H)
    return r.json()

# ─────────────────── DATAGRIDS ───────────────────

GRIDS = [
  {
    "nom": "Grand Livre General",
    "description": "Toutes les ecritures comptables detaillees par compte et date",
    "data_source_code": "DS_CPT_GRAND_LIVRE",
    "page_size": 50,
    "is_public": True,
    "application": APP,
    "show_totals": True,
    "total_columns": ["Debit", "Credit", "Solde"],
    "default_sort": {"field": "Compte", "direction": "asc"},
    "columns": [
      {"field":"Date","label":"Date","type":"date","width":100,"visible":True},
      {"field":"Compte","label":"Compte","type":"text","width":110,"visible":True},
      {"field":"Intitule Compte","label":"Intitule","type":"text","width":200,"visible":True},
      {"field":"Code Journal","label":"Journal","type":"text","width":80,"visible":True},
      {"field":"Journal","label":"Libelle Journal","type":"text","width":150,"visible":False},
      {"field":"Num Piece","label":"Piece","type":"text","width":100,"visible":True},
      {"field":"Tiers","label":"Tiers","type":"text","width":160,"visible":True},
      {"field":"Libelle","label":"Libelle","type":"text","width":200,"visible":True},
      {"field":"Debit","label":"Debit","type":"number","width":120,"visible":True,"format":"currency"},
      {"field":"Credit","label":"Credit","type":"number","width":120,"visible":True,"format":"currency"},
      {"field":"Solde","label":"Solde","type":"number","width":120,"visible":True,"format":"currency"},
      {"field":"Nature Compte","label":"Nature","type":"text","width":100,"visible":False},
      {"field":"Exercice","label":"Exercice","type":"text","width":80,"visible":False},
      {"field":"Societe","label":"Societe","type":"text","width":80,"visible":False},
    ]
  },
  {
    "nom": "Balance Generale",
    "description": "Totaux debit/credit et solde par compte comptable",
    "data_source_code": "DS_CPT_BALANCE",
    "page_size": 50,
    "is_public": True,
    "application": APP,
    "show_totals": True,
    "total_columns": ["Total Debit", "Total Credit", "Solde"],
    "default_sort": {"field": "Compte", "direction": "asc"},
    "columns": [
      {"field":"Compte","label":"Compte","type":"text","width":110,"visible":True},
      {"field":"Intitule Compte","label":"Intitule","type":"text","width":220,"visible":True},
      {"field":"Nature Compte","label":"Nature","type":"text","width":110,"visible":True},
      {"field":"Total Debit","label":"Total Debit","type":"number","width":130,"visible":True,"format":"currency"},
      {"field":"Total Credit","label":"Total Credit","type":"number","width":130,"visible":True,"format":"currency"},
      {"field":"Solde","label":"Solde","type":"number","width":130,"visible":True,"format":"currency"},
      {"field":"Nb Ecritures","label":"Nb Ecritures","type":"number","width":90,"visible":True},
      {"field":"Societe","label":"Societe","type":"text","width":80,"visible":False},
    ]
  },
  {
    "nom": "Journal des Ecritures",
    "description": "Ecritures comptables ordonnees par journal et date",
    "data_source_code": "DS_CPT_JOURNAL",
    "page_size": 50,
    "is_public": True,
    "application": APP,
    "show_totals": True,
    "total_columns": ["Debit", "Credit"],
    "default_sort": {"field": "Date", "direction": "desc"},
    "columns": [
      {"field":"Date","label":"Date","type":"date","width":100,"visible":True},
      {"field":"Code Journal","label":"Journal","type":"text","width":80,"visible":True},
      {"field":"Journal","label":"Libelle Journal","type":"text","width":150,"visible":True},
      {"field":"Num Piece","label":"Piece","type":"text","width":100,"visible":True},
      {"field":"Compte","label":"Compte","type":"text","width":110,"visible":True},
      {"field":"Intitule Compte","label":"Intitule","type":"text","width":180,"visible":True},
      {"field":"Tiers","label":"Tiers","type":"text","width":160,"visible":True},
      {"field":"Libelle","label":"Libelle","type":"text","width":200,"visible":True},
      {"field":"Debit","label":"Debit","type":"number","width":120,"visible":True,"format":"currency"},
      {"field":"Credit","label":"Credit","type":"number","width":120,"visible":True,"format":"currency"},
      {"field":"Type Ecriture","label":"Type","type":"text","width":100,"visible":False},
      {"field":"Societe","label":"Societe","type":"text","width":80,"visible":False},
    ]
  },
  {
    "nom": "Balance Tiers",
    "description": "Soldes clients et fournisseurs avec totaux debit/credit",
    "data_source_code": "DS_CPT_BALANCE_TIERS",
    "page_size": 50,
    "is_public": True,
    "application": APP,
    "show_totals": True,
    "total_columns": ["Total Debit", "Total Credit", "Solde"],
    "default_sort": {"field": "Solde", "direction": "desc"},
    "columns": [
      {"field":"Compte Tiers","label":"Code Tiers","type":"text","width":110,"visible":True},
      {"field":"Tiers","label":"Tiers","type":"text","width":220,"visible":True},
      {"field":"Type tiers","label":"Type","type":"text","width":100,"visible":True},
      {"field":"Nature Compte","label":"Nature","type":"text","width":100,"visible":True},
      {"field":"Total Debit","label":"Total Debit","type":"number","width":130,"visible":True,"format":"currency"},
      {"field":"Total Credit","label":"Total Credit","type":"number","width":130,"visible":True,"format":"currency"},
      {"field":"Solde","label":"Solde","type":"number","width":130,"visible":True,"format":"currency"},
      {"field":"Nb Ecritures","label":"Nb Ecritures","type":"number","width":90,"visible":True},
      {"field":"Societe","label":"Societe","type":"text","width":80,"visible":False},
    ]
  },
  {
    "nom": "Echeancier Clients",
    "description": "Factures clients avec dates d echeance et statut de lettrage",
    "data_source_code": "DS_CPT_ECHEANCES_CLIENTS",
    "page_size": 50,
    "is_public": True,
    "application": APP,
    "show_totals": True,
    "total_columns": ["Debit", "Credit", "Solde"],
    "default_sort": {"field": "Date Echeance", "direction": "asc"},
    "columns": [
      {"field":"Date Echeance","label":"Echeance","type":"date","width":100,"visible":True},
      {"field":"Compte Tiers","label":"Code Client","type":"text","width":110,"visible":True},
      {"field":"Client","label":"Client","type":"text","width":200,"visible":True},
      {"field":"Num Piece","label":"Piece","type":"text","width":100,"visible":True},
      {"field":"Num Facture","label":"Facture","type":"text","width":100,"visible":True},
      {"field":"Libelle","label":"Libelle","type":"text","width":180,"visible":True},
      {"field":"Debit","label":"Debit","type":"number","width":120,"visible":True,"format":"currency"},
      {"field":"Credit","label":"Credit","type":"number","width":120,"visible":True,"format":"currency"},
      {"field":"Solde","label":"Solde","type":"number","width":120,"visible":True,"format":"currency"},
      {"field":"Lettrage","label":"Lettre","type":"text","width":70,"visible":True},
      {"field":"Mode Reglement","label":"Mode Regl.","type":"text","width":110,"visible":True},
      {"field":"Date Ecriture","label":"Date Ecrit.","type":"date","width":100,"visible":False},
    ]
  },
  {
    "nom": "Echeancier Fournisseurs",
    "description": "Factures fournisseurs avec dates d echeance et statut de lettrage",
    "data_source_code": "DS_CPT_ECHEANCES_FOURN",
    "page_size": 50,
    "is_public": True,
    "application": APP,
    "show_totals": True,
    "total_columns": ["Debit", "Credit", "Solde"],
    "default_sort": {"field": "Date Echeance", "direction": "asc"},
    "columns": [
      {"field":"Date Echeance","label":"Echeance","type":"date","width":100,"visible":True},
      {"field":"Compte Tiers","label":"Code Fourn.","type":"text","width":110,"visible":True},
      {"field":"Fournisseur","label":"Fournisseur","type":"text","width":200,"visible":True},
      {"field":"Num Piece","label":"Piece","type":"text","width":100,"visible":True},
      {"field":"Num Facture","label":"Facture","type":"text","width":100,"visible":True},
      {"field":"Libelle","label":"Libelle","type":"text","width":180,"visible":True},
      {"field":"Debit","label":"Debit","type":"number","width":120,"visible":True,"format":"currency"},
      {"field":"Credit","label":"Credit","type":"number","width":120,"visible":True,"format":"currency"},
      {"field":"Solde","label":"Solde","type":"number","width":120,"visible":True,"format":"currency"},
      {"field":"Lettrage","label":"Lettre","type":"text","width":70,"visible":True},
      {"field":"Mode Reglement","label":"Mode Regl.","type":"text","width":110,"visible":True},
      {"field":"Date Ecriture","label":"Date Ecrit.","type":"date","width":100,"visible":False},
    ]
  },
  {
    "nom": "Detail des Charges",
    "description": "Comptes de charges (classe 6) avec montants cumules sur la periode",
    "data_source_code": "DS_CPT_CHARGES",
    "page_size": 50,
    "is_public": True,
    "application": APP,
    "show_totals": True,
    "total_columns": ["Total Debit", "Total Credit", "Montant Charge"],
    "default_sort": {"field": "Montant Charge", "direction": "desc"},
    "columns": [
      {"field":"Compte","label":"Compte","type":"text","width":110,"visible":True},
      {"field":"Intitule Compte","label":"Intitule","type":"text","width":240,"visible":True},
      {"field":"Total Debit","label":"Total Debit","type":"number","width":130,"visible":True,"format":"currency"},
      {"field":"Total Credit","label":"Total Credit","type":"number","width":130,"visible":False,"format":"currency"},
      {"field":"Montant Charge","label":"Montant Charge","type":"number","width":140,"visible":True,"format":"currency"},
      {"field":"Nb Ecritures","label":"Nb Ecritures","type":"number","width":90,"visible":True},
      {"field":"Societe","label":"Societe","type":"text","width":80,"visible":False},
    ]
  },
]

print("=== CREATION DES DATAGRIDS ===")
for g in GRIDS:
    r = post("/gridview/grids", g)
    if r.get("success") or r.get("id"):
        gid = r.get("id") or r.get("data", {}).get("id", "?")
        created["grids"].append({"nom": g["nom"], "id": gid})
        print(f"  ok Grid: {g['nom']} (id={gid})")
    else:
        errors.append(f"Grid '{g['nom']}': {r}")
        print(f"  ERREUR Grid: {g['nom']} -> {r}")

# ─────────────────── PIVOTS ───────────────────

PIVOTS = [
  {
    "nom": "Resultat par Nature de Compte",
    "description": "Croisement Nature (Charge/Produit) x Periode - solde et evolution",
    "data_source_code": "DS_CPT_RESULTAT_NATURE",
    "is_public": True,
    "application": APP,
    "show_grand_totals": True,
    "show_subtotals": True,
    "show_col_percent": True,
    "rows_config": [
      {"field":"Nature Compte","label":"Nature","type":"text"},
      {"field":"Classe","label":"Classe","type":"text"},
    ],
    "columns_config": [
      {"field":"Annee","label":"Annee","type":"text"},
      {"field":"Mois","label":"Mois","type":"number"},
    ],
    "filters_config": [
      {"field":"Societe","type":"select"},
    ],
    "values_config": [
      {"field":"Solde","aggregation":"SUM","label":"Solde","format":"currency","decimals":2},
      {"field":"Debit","aggregation":"SUM","label":"Debit","format":"currency","decimals":2},
      {"field":"Credit","aggregation":"SUM","label":"Credit","format":"currency","decimals":2},
    ],
    "formatting_rules": [
      {"field":"Solde","type":"negative_red"},
    ],
  },
  {
    "nom": "Balance par Journal",
    "description": "Activite comptable par journal x periode (debit, credit, nb ecritures)",
    "data_source_code": "DS_CPT_BALANCE_JOURNAL",
    "is_public": True,
    "application": APP,
    "show_grand_totals": True,
    "show_subtotals": True,
    "rows_config": [
      {"field":"Type Journal","label":"Type","type":"text"},
      {"field":"Code Journal","label":"Code","type":"text"},
      {"field":"Journal","label":"Journal","type":"text"},
    ],
    "columns_config": [
      {"field":"Annee","label":"Annee","type":"text"},
      {"field":"Mois","label":"Mois","type":"number"},
    ],
    "filters_config": [
      {"field":"Societe","type":"select"},
    ],
    "values_config": [
      {"field":"Debit","aggregation":"SUM","label":"Debit","format":"currency","decimals":2},
      {"field":"Credit","aggregation":"SUM","label":"Credit","format":"currency","decimals":2},
      {"field":"Nb Ecritures","aggregation":"SUM","label":"Nb Ecritures","format":"number","decimals":0},
    ],
    "formatting_rules": [
      {"field":"Debit","type":"data_bars","config":{"color":"#3b82f6"}},
    ],
  },
  {
    "nom": "Balance par Classe Comptable",
    "description": "Soldes par classe de compte (1-Capitaux a 7-Produits) x periode",
    "data_source_code": "DS_CPT_BALANCE_CLASSE",
    "is_public": True,
    "application": APP,
    "show_grand_totals": True,
    "show_subtotals": True,
    "show_row_percent": True,
    "rows_config": [
      {"field":"Classe","label":"Classe","type":"text"},
      {"field":"Libelle Classe","label":"Libelle","type":"text"},
    ],
    "columns_config": [
      {"field":"Annee","label":"Annee","type":"text"},
      {"field":"Mois","label":"Mois","type":"number"},
    ],
    "filters_config": [
      {"field":"Societe","type":"select"},
    ],
    "values_config": [
      {"field":"Debit","aggregation":"SUM","label":"Debit","format":"currency","decimals":2},
      {"field":"Credit","aggregation":"SUM","label":"Credit","format":"currency","decimals":2},
      {"field":"Solde","aggregation":"SUM","label":"Solde","format":"currency","decimals":2},
      {"field":"Nb Ecritures","aggregation":"SUM","label":"Nb Ecritures","format":"number","decimals":0},
    ],
    "formatting_rules": [
      {"field":"Solde","type":"negative_red"},
      {"field":"Debit","type":"heatmap","config":{"colors":["#eff6ff","#1d4ed8"]}},
    ],
  },
  {
    "nom": "Tresorerie par Banque",
    "description": "Encaissements et decaissements par compte bancaire x periode",
    "data_source_code": "DS_CPT_TRESO_BANQUE",
    "is_public": True,
    "application": APP,
    "show_grand_totals": True,
    "show_subtotals": True,
    "rows_config": [
      {"field":"Code Journal","label":"Code Banque","type":"text"},
      {"field":"Banque","label":"Banque","type":"text"},
    ],
    "columns_config": [
      {"field":"Annee","label":"Annee","type":"text"},
      {"field":"Mois","label":"Mois","type":"number"},
    ],
    "filters_config": [
      {"field":"Societe","type":"select"},
    ],
    "values_config": [
      {"field":"Encaissements","aggregation":"SUM","label":"Encaissements","format":"currency","decimals":2},
      {"field":"Decaissements","aggregation":"SUM","label":"Decaissements","format":"currency","decimals":2},
      {"field":"Solde","aggregation":"SUM","label":"Solde","format":"currency","decimals":2},
      {"field":"Nb Operations","aggregation":"SUM","label":"Nb Oper.","format":"number","decimals":0},
    ],
    "formatting_rules": [
      {"field":"Solde","type":"negative_red"},
    ],
  },
  {
    "nom": "Soldes Clients par Periode",
    "description": "Debit, credit et solde par client x mois (suivi des creances)",
    "data_source_code": "DS_CPT_SOLDES_CLIENTS",
    "is_public": True,
    "application": APP,
    "show_grand_totals": True,
    "show_subtotals": True,
    "rows_config": [
      {"field":"Compte Tiers","label":"Code Client","type":"text"},
      {"field":"Client","label":"Client","type":"text"},
    ],
    "columns_config": [
      {"field":"Annee","label":"Annee","type":"text"},
      {"field":"Mois","label":"Mois","type":"number"},
    ],
    "filters_config": [
      {"field":"Societe","type":"select"},
    ],
    "values_config": [
      {"field":"Debit","aggregation":"SUM","label":"Debit","format":"currency","decimals":2},
      {"field":"Credit","aggregation":"SUM","label":"Credit","format":"currency","decimals":2},
      {"field":"Solde","aggregation":"SUM","label":"Solde","format":"currency","decimals":2},
      {"field":"Nb Ecritures","aggregation":"SUM","label":"Nb Ecritures","format":"number","decimals":0},
    ],
    "formatting_rules": [
      {"field":"Solde","type":"data_bars","config":{"color":"#f59e0b"}},
    ],
  },
  {
    "nom": "Soldes Fournisseurs par Periode",
    "description": "Debit, credit et solde par fournisseur x mois (suivi des dettes)",
    "data_source_code": "DS_CPT_SOLDES_FOURN",
    "is_public": True,
    "application": APP,
    "show_grand_totals": True,
    "show_subtotals": True,
    "rows_config": [
      {"field":"Compte Tiers","label":"Code Fourn.","type":"text"},
      {"field":"Fournisseur","label":"Fournisseur","type":"text"},
    ],
    "columns_config": [
      {"field":"Annee","label":"Annee","type":"text"},
      {"field":"Mois","label":"Mois","type":"number"},
    ],
    "filters_config": [
      {"field":"Societe","type":"select"},
    ],
    "values_config": [
      {"field":"Debit","aggregation":"SUM","label":"Debit","format":"currency","decimals":2},
      {"field":"Credit","aggregation":"SUM","label":"Credit","format":"currency","decimals":2},
      {"field":"Solde","aggregation":"SUM","label":"Solde","format":"currency","decimals":2},
      {"field":"Nb Ecritures","aggregation":"SUM","label":"Nb Ecritures","format":"number","decimals":0},
    ],
    "formatting_rules": [
      {"field":"Solde","type":"data_bars","config":{"color":"#ef4444"}},
    ],
  },
]

print("\n=== CREATION DES PIVOTS ===")
for p in PIVOTS:
    r = post("/v2/pivots", p)
    if r.get("success") or r.get("id"):
        pid = r.get("id") or r.get("data", {}).get("id", "?")
        created["pivots"].append({"nom": p["nom"], "id": pid})
        print(f"  ok Pivot: {p['nom']} (id={pid})")
    else:
        errors.append(f"Pivot '{p['nom']}': {r}")
        print(f"  ERREUR Pivot: {p['nom']} -> {r}")

# ─────────────────── DASHBOARDS ───────────────────

DASHBOARDS = [
  {
    "nom": "Tableau de Bord Comptabilite",
    "description": "Vue synthetique : KPIs, evolution mensuelle, charges vs produits, repartition",
    "is_public": True,
    "application": APP,
    "widgets": [
      {"id":"w_cpt_kpi1","type":"kpi","title":"Total Produits","x":0,"y":0,"w":3,"h":3,
       "config":{"dataSourceCode":"DS_CPT_KPI_GLOBAL","dataSourceOrigin":"template",
                 "value_field":"Total Produits","format":"currency","color":"emerald","icon":"TrendingUp"}},
      {"id":"w_cpt_kpi2","type":"kpi","title":"Total Charges","x":3,"y":0,"w":3,"h":3,
       "config":{"dataSourceCode":"DS_CPT_KPI_GLOBAL","dataSourceOrigin":"template",
                 "value_field":"Total Charges","format":"currency","color":"rose","icon":"TrendingDown"}},
      {"id":"w_cpt_kpi3","type":"kpi","title":"Resultat Net","x":6,"y":0,"w":3,"h":3,
       "config":{"dataSourceCode":"DS_CPT_KPI_GLOBAL","dataSourceOrigin":"template",
                 "value_field":"Resultat","format":"currency","color":"blue","icon":"Activity"}},
      {"id":"w_cpt_kpi4","type":"kpi","title":"Nb Ecritures","x":9,"y":0,"w":3,"h":3,
       "config":{"dataSourceCode":"DS_CPT_KPI_GLOBAL","dataSourceOrigin":"template",
                 "value_field":"Nb Ecritures","format":"number","color":"violet","icon":"Layers"}},
      {"id":"w_cpt_evol","type":"chart_line","title":"Evolution Mensuelle - Debit / Credit","x":0,"y":3,"w":8,"h":7,
       "config":{"dataSourceCode":"DS_CPT_EVOLUTION_MENSUELLE","dataSourceOrigin":"template",
                 "x_field":"Periode","value_field":"Total Debit","colors":["#3b82f6","#10b981","#f59e0b"]}},
      {"id":"w_cpt_nature_pie","type":"chart_pie","title":"Repartition par Nature","x":8,"y":3,"w":4,"h":7,
       "config":{"dataSourceCode":"DS_CPT_REPARTITION_NATURE","dataSourceOrigin":"template",
                 "x_field":"Nature Compte","value_field":"Solde Abs","aggregation":"SUM"}},
      {"id":"w_cpt_cp","type":"chart_bar","title":"Charges vs Produits par Mois","x":0,"y":10,"w":8,"h":7,
       "config":{"dataSourceCode":"DS_CPT_CHARGES_PRODUITS_MENS","dataSourceOrigin":"template",
                 "x_field":"Periode","value_field":"Charges","colors":["#ef4444","#10b981","#3b82f6"]}},
      {"id":"w_cpt_jrn_pie","type":"chart_pie","title":"Repartition par Type Journal","x":8,"y":10,"w":4,"h":7,
       "config":{"dataSourceCode":"DS_CPT_REPARTITION_JOURNAL","dataSourceOrigin":"template",
                 "x_field":"Type Journal","value_field":"Debit","aggregation":"SUM"}},
      {"id":"w_cpt_top_cli","type":"table","title":"Top 20 Clients - Soldes","x":0,"y":17,"w":6,"h":7,
       "config":{"dataSourceCode":"DS_CPT_TOP_CLIENTS","dataSourceOrigin":"template",
                 "sort_field":"Solde","sort_direction":"desc","limit_rows":20}},
      {"id":"w_cpt_top_fourn","type":"table","title":"Top 20 Fournisseurs - Soldes","x":6,"y":17,"w":6,"h":7,
       "config":{"dataSourceCode":"DS_CPT_TOP_FOURNISSEURS","dataSourceOrigin":"template",
                 "sort_field":"Solde","sort_direction":"desc","limit_rows":20}},
    ]
  },
  {
    "nom": "Tableau de Bord Tresorerie",
    "description": "Flux de tresorerie, soldes banques, encaissements et decaissements",
    "is_public": True,
    "application": APP,
    "widgets": [
      {"id":"w_treso_kpi1","type":"kpi","title":"Total Debit","x":0,"y":0,"w":3,"h":3,
       "config":{"dataSourceCode":"DS_CPT_KPI_GLOBAL","dataSourceOrigin":"template",
                 "value_field":"Total Debit","format":"currency","color":"blue","icon":"TrendingUp"}},
      {"id":"w_treso_kpi2","type":"kpi","title":"Total Credit","x":3,"y":0,"w":3,"h":3,
       "config":{"dataSourceCode":"DS_CPT_KPI_GLOBAL","dataSourceOrigin":"template",
                 "value_field":"Total Credit","format":"currency","color":"emerald","icon":"TrendingUp"}},
      {"id":"w_treso_kpi3","type":"kpi","title":"Resultat Net","x":6,"y":0,"w":3,"h":3,
       "config":{"dataSourceCode":"DS_CPT_KPI_GLOBAL","dataSourceOrigin":"template",
                 "value_field":"Resultat","format":"currency","color":"amber","icon":"Activity"}},
      {"id":"w_treso_kpi4","type":"kpi","title":"Nb Journaux","x":9,"y":0,"w":3,"h":3,
       "config":{"dataSourceCode":"DS_CPT_KPI_GLOBAL","dataSourceOrigin":"template",
                 "value_field":"Nb Journaux","format":"number","color":"violet","icon":"BookOpen"}},
      {"id":"w_treso_flux","type":"chart_area","title":"Flux de Tresorerie Mensuel","x":0,"y":3,"w":8,"h":7,
       "config":{"dataSourceCode":"DS_CPT_FLUX_TRESORERIE","dataSourceOrigin":"template",
                 "x_field":"Periode","value_field":"Flux Net","colors":["#3b82f6","#10b981","#f59e0b"]}},
      {"id":"w_treso_enc_dec","type":"chart_pie","title":"Encaissements vs Decaissements","x":8,"y":3,"w":4,"h":7,
       "config":{"dataSourceCode":"DS_CPT_FLUX_TRESORERIE","dataSourceOrigin":"template",
                 "x_field":"Periode","value_field":"Encaissements","aggregation":"SUM",
                 "colors":["#10b981","#ef4444"]}},
      {"id":"w_treso_bar","type":"chart_bar","title":"Encaissements / Decaissements par Mois","x":0,"y":10,"w":8,"h":7,
       "config":{"dataSourceCode":"DS_CPT_FLUX_TRESORERIE","dataSourceOrigin":"template",
                 "x_field":"Periode","value_field":"Encaissements","colors":["#10b981","#ef4444"]}},
      {"id":"w_treso_banque","type":"chart_bar","title":"Solde par Banque","x":8,"y":10,"w":4,"h":7,
       "config":{"dataSourceCode":"DS_CPT_TRESO_BANQUE","dataSourceOrigin":"template",
                 "x_field":"Banque","value_field":"Solde","aggregation":"SUM",
                 "colors":["#3b82f6"]}},
      {"id":"w_treso_detail","type":"table","title":"Detail des Operations de Tresorerie","x":0,"y":17,"w":12,"h":7,
       "config":{"dataSourceCode":"DS_CPT_TRESO_BANQUE","dataSourceOrigin":"template",
                 "sort_field":"Solde","sort_direction":"desc"}},
    ]
  },
]

print("\n=== CREATION DES DASHBOARDS ===")
for d in DASHBOARDS:
    r = post("/builder/dashboards", d)
    if r.get("success") or r.get("id"):
        did = r.get("id") or r.get("data", {}).get("id", "?")
        created["dashboards"].append({"nom": d["nom"], "id": did})
        print(f"  ok Dashboard: {d['nom']} (id={did})")
    else:
        errors.append(f"Dashboard '{d['nom']}': {r}")
        print(f"  ERREUR Dashboard: {d['nom']} -> {r}")

print("\n" + "="*60)
print(f"RESUME: {len(created['grids'])} grids, {len(created['pivots'])} pivots, {len(created['dashboards'])} dashboards")
if errors:
    print(f"ERREURS ({len(errors)}):")
    for e in errors: print(f"  - {e}")
print(json.dumps(created, indent=2, ensure_ascii=False))
