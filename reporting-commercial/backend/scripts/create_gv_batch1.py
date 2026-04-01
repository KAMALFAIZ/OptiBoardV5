import sys, json, os
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from app.database import execute_query, get_db_cursor

FEAT = json.dumps({"show_search":True,"show_column_filters":True,"show_grouping":True,"show_column_toggle":True,"show_export":True,"show_pagination":True,"show_page_size":True,"allow_sorting":True})

def create_gv(nom, desc, code, cols, sort, ps, st, tc):
    ex = execute_query("SELECT id FROM APP_GridViews WHERE data_source_code = ?", (code,), use_cache=False)
    if ex:
        return ex[0]["id"], False
    with get_db_cursor() as c:
        c.execute("INSERT INTO APP_GridViews (nom,description,data_source_code,columns_config,default_sort,page_size,show_totals,total_columns,row_styles,features,is_public,created_by) VALUES (?,?,?,?,?,?,?,?,?,?,1,1)",
            (nom, desc, code, json.dumps(cols), json.dumps(sort), ps, st, json.dumps(tc), "[]", FEAT))
        c.execute("SELECT @@IDENTITY AS id")
        return int(c.fetchone()[0]), True

def update_menu(code, gid):
    with get_db_cursor() as c:
        c.execute("UPDATE APP_Menus SET target_id=? WHERE code=? AND type=?", (gid, code, "gridview"))
        return c.rowcount

GRIDVIEWS = [
    {"nom": "Factures", "desc": "Liste des factures de vente", "code": "DS_FACTURES",
     "cols": [
         {"field":"Societe","header":"Societe","width":100,"sortable":True,"visible":True},
         {"field":"Num Facture","header":"N Facture","width":120,"sortable":True,"visible":True},
         {"field":"Date Facture","header":"Date","width":100,"format":"date","sortable":True,"visible":True},
         {"field":"Code Client","header":"Code Client","width":100,"sortable":True,"visible":True},
         {"field":"Client","header":"Client","width":200,"sortable":True,"visible":True},
         {"field":"Code Article","header":"Code Article","width":120,"sortable":True,"visible":True},
         {"field":"Designation","header":"Designation","width":200,"sortable":True,"visible":True},
         {"field":"Qte","header":"Qte","width":80,"format":"number","align":"right","sortable":True,"visible":True},
         {"field":"PU HT","header":"PU HT","width":100,"format":"currency","align":"right","sortable":True,"visible":True},
         {"field":"Montant HT","header":"Montant HT","width":120,"format":"currency","align":"right","sortable":True,"visible":True},
         {"field":"Montant TTC","header":"Montant TTC","width":120,"format":"currency","align":"right","sortable":True,"visible":True},
         {"field":"Marge","header":"Marge","width":100,"format":"currency","align":"right","sortable":True,"visible":True},
     ],
     "sort": {"field":"Date Facture","direction":"desc"}, "ps": 50, "st": True, "tc": ["Montant HT","Montant TTC","Marge","Qte"]},

    {"nom": "Bons de Livraison", "desc": "Liste des bons de livraison", "code": "DS_BONS_LIVRAISON",
     "cols": [
         {"field":"Societe","header":"Societe","width":100,"sortable":True,"visible":True},
         {"field":"Num BL","header":"N BL","width":120,"sortable":True,"visible":True},
         {"field":"Date BL","header":"Date BL","width":100,"format":"date","sortable":True,"visible":True},
         {"field":"Num BC","header":"N BC","width":120,"sortable":True,"visible":True},
         {"field":"Code Client","header":"Code Client","width":100,"sortable":True,"visible":True},
         {"field":"Client","header":"Client","width":200,"sortable":True,"visible":True},
         {"field":"Code Article","header":"Code Article","width":120,"sortable":True,"visible":True},
         {"field":"Designation","header":"Designation","width":200,"sortable":True,"visible":True},
         {"field":"Qte BL","header":"Qte BL","width":80,"format":"number","align":"right","sortable":True,"visible":True},
         {"field":"Montant HT","header":"Montant HT","width":120,"format":"currency","align":"right","sortable":True,"visible":True},
         {"field":"Depot","header":"Depot","width":150,"sortable":True,"visible":True},
     ],
     "sort": {"field":"Date BL","direction":"desc"}, "ps": 50, "st": True, "tc": ["Montant HT","Qte BL"]},

    {"nom": "Bons de Commande", "desc": "Bons de commande clients", "code": "DS_BONS_COMMANDE",
     "cols": [
         {"field":"Societe","header":"Societe","width":100,"sortable":True,"visible":True},
         {"field":"Num BC","header":"N BC","width":120,"sortable":True,"visible":True},
         {"field":"Date BC","header":"Date BC","width":100,"format":"date","sortable":True,"visible":True},
         {"field":"Code Client","header":"Code Client","width":100,"sortable":True,"visible":True},
         {"field":"Client","header":"Client","width":200,"sortable":True,"visible":True},
         {"field":"Code Article","header":"Code Article","width":120,"sortable":True,"visible":True},
         {"field":"Designation","header":"Designation","width":200,"sortable":True,"visible":True},
         {"field":"Qte Commandee","header":"Qte Cmd","width":80,"format":"number","align":"right","sortable":True,"visible":True},
         {"field":"Qte Livree","header":"Qte Livree","width":80,"format":"number","align":"right","sortable":True,"visible":True},
         {"field":"Reste A Livrer","header":"Reste","width":80,"format":"number","align":"right","sortable":True,"visible":True},
         {"field":"Montant HT","header":"Montant HT","width":120,"format":"currency","align":"right","sortable":True,"visible":True},
         {"field":"Date Livraison Prevue","header":"Livraison Prevue","width":120,"format":"date","sortable":True,"visible":True},
     ],
     "sort": {"field":"Date BC","direction":"desc"}, "ps": 50, "st": True, "tc": ["Montant HT","Qte Commandee","Reste A Livrer"]},

    {"nom": "Devis", "desc": "Liste des devis", "code": "DS_DEVIS",
     "cols": [
         {"field":"Societe","header":"Societe","width":100,"sortable":True,"visible":True},
         {"field":"Num Devis","header":"N Devis","width":120,"sortable":True,"visible":True},
         {"field":"Date Devis","header":"Date","width":100,"format":"date","sortable":True,"visible":True},
         {"field":"Code Client","header":"Code Client","width":100,"sortable":True,"visible":True},
         {"field":"Client","header":"Client","width":200,"sortable":True,"visible":True},
         {"field":"Code Article","header":"Code Article","width":120,"sortable":True,"visible":True},
         {"field":"Designation","header":"Designation","width":200,"sortable":True,"visible":True},
         {"field":"Qte","header":"Qte","width":80,"format":"number","align":"right","sortable":True,"visible":True},
         {"field":"PU HT","header":"PU HT","width":100,"format":"currency","align":"right","sortable":True,"visible":True},
         {"field":"Montant HT","header":"Montant HT","width":120,"format":"currency","align":"right","sortable":True,"visible":True},
         {"field":"Montant TTC","header":"Montant TTC","width":120,"format":"currency","align":"right","sortable":True,"visible":True},
     ],
     "sort": {"field":"Date Devis","direction":"desc"}, "ps": 50, "st": True, "tc": ["Montant HT","Montant TTC","Qte"]},

    {"nom": "Avoirs", "desc": "Liste des avoirs", "code": "DS_AVOIRS",
     "cols": [
         {"field":"Societe","header":"Societe","width":100,"sortable":True,"visible":True},
         {"field":"Type Document","header":"Type","width":100,"sortable":True,"visible":True},
         {"field":"Num Avoir","header":"N Avoir","width":120,"sortable":True,"visible":True},
         {"field":"Date Avoir","header":"Date","width":100,"format":"date","sortable":True,"visible":True},
         {"field":"Code Client","header":"Code Client","width":100,"sortable":True,"visible":True},
         {"field":"Client","header":"Client","width":200,"sortable":True,"visible":True},
         {"field":"Code Article","header":"Code Article","width":120,"sortable":True,"visible":True},
         {"field":"Designation","header":"Designation","width":200,"sortable":True,"visible":True},
         {"field":"Qte","header":"Qte","width":80,"format":"number","align":"right","sortable":True,"visible":True},
         {"field":"Montant HT","header":"Montant HT","width":120,"format":"currency","align":"right","sortable":True,"visible":True},
         {"field":"Montant TTC","header":"Montant TTC","width":120,"format":"currency","align":"right","sortable":True,"visible":True},
     ],
     "sort": {"field":"Date Avoir","direction":"desc"}, "ps": 50, "st": True, "tc": ["Montant HT","Montant TTC","Qte"]},

    {"nom": "Preparations Livraison", "desc": "Preparations de livraison", "code": "DS_PREPARATIONS_LIVRAISON",
     "cols": [
         {"field":"Societe","header":"Societe","width":100,"sortable":True,"visible":True},
         {"field":"Num PL","header":"N PL","width":120,"sortable":True,"visible":True},
         {"field":"Date PL","header":"Date PL","width":100,"format":"date","sortable":True,"visible":True},
         {"field":"Num BC","header":"N BC","width":120,"sortable":True,"visible":True},
         {"field":"Code Client","header":"Code Client","width":100,"sortable":True,"visible":True},
         {"field":"Client","header":"Client","width":200,"sortable":True,"visible":True},
         {"field":"Code Article","header":"Code Article","width":120,"sortable":True,"visible":True},
         {"field":"Designation","header":"Designation","width":200,"sortable":True,"visible":True},
         {"field":"Qte PL","header":"Qte PL","width":80,"format":"number","align":"right","sortable":True,"visible":True},
         {"field":"Montant HT","header":"Montant HT","width":120,"format":"currency","align":"right","sortable":True,"visible":True},
         {"field":"Depot","header":"Depot","width":150,"sortable":True,"visible":True},
     ],
     "sort": {"field":"Date PL","direction":"desc"}, "ps": 50, "st": True, "tc": ["Montant HT","Qte PL"]},

    {"nom": "Ventes par Type Document", "desc": "Synthese par type de document", "code": "DS_VENTES_PAR_TYPE_DOC",
     "cols": [
         {"field":"Type Document","header":"Type Document","width":150,"sortable":True,"visible":True},
         {"field":"Societe","header":"Societe","width":100,"sortable":True,"visible":True},
         {"field":"Nb Documents","header":"Nb Docs","width":100,"format":"number","align":"right","sortable":True,"visible":True},
         {"field":"Nb Lignes","header":"Nb Lignes","width":100,"format":"number","align":"right","sortable":True,"visible":True},
         {"field":"Montant HT","header":"Montant HT","width":120,"format":"currency","align":"right","sortable":True,"visible":True},
         {"field":"Montant TTC","header":"Montant TTC","width":120,"format":"currency","align":"right","sortable":True,"visible":True},
         {"field":"Nb Clients","header":"Nb Clients","width":100,"format":"number","align":"right","sortable":True,"visible":True},
     ],
     "sort": {"field":"Montant HT","direction":"desc"}, "ps": 25, "st": True, "tc": ["Montant HT","Montant TTC","Nb Documents"]},

    {"nom": "Ventes Detail Complet", "desc": "Detail complet de toutes les ventes", "code": "DS_VENTES_DETAIL",
     "cols": [
         {"field":"Societe","header":"Societe","width":100,"sortable":True,"visible":True},
         {"field":"Type Document","header":"Type","width":100,"sortable":True,"visible":True},
         {"field":"Num Piece","header":"N Piece","width":120,"sortable":True,"visible":True},
         {"field":"Date","header":"Date","width":100,"format":"date","sortable":True,"visible":True},
         {"field":"Code Client","header":"Code Client","width":100,"sortable":True,"visible":True},
         {"field":"Client","header":"Client","width":180,"sortable":True,"visible":True},
         {"field":"Code Article","header":"Code Article","width":120,"sortable":True,"visible":True},
         {"field":"Designation","header":"Designation","width":200,"sortable":True,"visible":True},
         {"field":"Qte","header":"Qte","width":70,"format":"number","align":"right","sortable":True,"visible":True},
         {"field":"Montant HT","header":"MT HT","width":110,"format":"currency","align":"right","sortable":True,"visible":True},
         {"field":"Montant TTC","header":"MT TTC","width":110,"format":"currency","align":"right","sortable":True,"visible":True},
         {"field":"Marge","header":"Marge","width":100,"format":"currency","align":"right","sortable":True,"visible":True},
     ],
     "sort": {"field":"Date","direction":"desc"}, "ps": 100, "st": True, "tc": ["Montant HT","Montant TTC","Marge","Qte"]},

    {"nom": "Top Clients", "desc": "Classement des meilleurs clients par CA", "code": "DS_TOP_CLIENTS",
     "cols": [
         {"field":"Code Client","header":"Code","width":100,"sortable":True,"visible":True},
         {"field":"Client","header":"Client","width":200,"sortable":True,"visible":True},
         {"field":"Societe","header":"Societe","width":100,"sortable":True,"visible":True},
         {"field":"CA HT","header":"CA HT","width":120,"format":"currency","align":"right","sortable":True,"visible":True},
         {"field":"Marge","header":"Marge","width":120,"format":"currency","align":"right","sortable":True,"visible":True},
         {"field":"Taux Marge %","header":"Taux Marge","width":100,"format":"percent","align":"right","sortable":True,"visible":True},
         {"field":"Nb Factures","header":"Nb Fact.","width":90,"format":"number","align":"right","sortable":True,"visible":True},
         {"field":"Premiere Vente","header":"1ere Vente","width":100,"format":"date","sortable":True,"visible":True},
         {"field":"Derniere Vente","header":"Derniere Vente","width":110,"format":"date","sortable":True,"visible":True},
     ],
     "sort": {"field":"CA HT","direction":"desc"}, "ps": 50, "st": True, "tc": ["CA HT","Marge"]},

    {"nom": "Top Articles", "desc": "Classement des articles les plus vendus", "code": "DS_TOP_ARTICLES",
     "cols": [
         {"field":"Code Article","header":"Code","width":120,"sortable":True,"visible":True},
         {"field":"Designation","header":"Designation","width":250,"sortable":True,"visible":True},
         {"field":"Catalogue","header":"Catalogue","width":120,"sortable":True,"visible":True},
         {"field":"Qte Vendue","header":"Qte","width":80,"format":"number","align":"right","sortable":True,"visible":True},
         {"field":"CA HT","header":"CA HT","width":120,"format":"currency","align":"right","sortable":True,"visible":True},
         {"field":"Marge","header":"Marge","width":120,"format":"currency","align":"right","sortable":True,"visible":True},
         {"field":"Taux Marge %","header":"Taux Marge","width":100,"format":"percent","align":"right","sortable":True,"visible":True},
         {"field":"Nb Clients","header":"Nb Clients","width":90,"format":"number","align":"right","sortable":True,"visible":True},
     ],
     "sort": {"field":"CA HT","direction":"desc"}, "ps": 50, "st": True, "tc": ["CA HT","Marge","Qte Vendue"]},

    {"nom": "Commandes en Cours", "desc": "Commandes non entierement livrees", "code": "DS_COMMANDES_EN_COURS",
     "cols": [
         {"field":"Societe","header":"Societe","width":100,"sortable":True,"visible":True},
         {"field":"Num BC","header":"N BC","width":120,"sortable":True,"visible":True},
         {"field":"Date BC","header":"Date BC","width":100,"format":"date","sortable":True,"visible":True},
         {"field":"Code Client","header":"Code Client","width":100,"sortable":True,"visible":True},
         {"field":"Client","header":"Client","width":200,"sortable":True,"visible":True},
         {"field":"Code Article","header":"Code Article","width":120,"sortable":True,"visible":True},
         {"field":"Designation","header":"Designation","width":200,"sortable":True,"visible":True},
         {"field":"Qte Commandee","header":"Qte Cmd","width":80,"format":"number","align":"right","sortable":True,"visible":True},
         {"field":"Reste A Livrer","header":"Reste","width":80,"format":"number","align":"right","sortable":True,"visible":True},
         {"field":"Montant Reste","header":"MT Reste","width":120,"format":"currency","align":"right","sortable":True,"visible":True},
         {"field":"Date Livraison Prevue","header":"Livraison Prevue","width":120,"format":"date","sortable":True,"visible":True},
         {"field":"Age Commande Jours","header":"Age (j)","width":80,"format":"number","align":"right","sortable":True,"visible":True},
     ],
     "sort": {"field":"Age Commande Jours","direction":"desc"}, "ps": 50, "st": True, "tc": ["Montant Reste","Qte Commandee","Reste A Livrer"]},
]

print("Creating GridViews...")
created = 0
updated = 0

for gv in GRIDVIEWS:
    gid, is_new = create_gv(gv["nom"], gv["desc"], gv["code"], gv["cols"], gv["sort"], gv["ps"], gv["st"], gv["tc"])
    n = update_menu(gv["code"], gid)
    status = "CREATED" if is_new else "EXISTS"
    created += (1 if is_new else 0)
    updated += n
    print(f"  [{status}] {gv['nom']} (ID={gid}) menu_updated={n}")

print(f"\nDone: {created} created, {updated} menus updated")
