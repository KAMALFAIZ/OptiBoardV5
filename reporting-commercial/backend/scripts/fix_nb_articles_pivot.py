"""
Fix DS_DIR_EVOLUTION_CA_12M et DS_VTE_CA_MENSUEL :
Ajoute COUNT(DISTINCT [Code article]) AS [Nb Articles] dans leur query_template.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database_unified import execute_central as execute_query, central_cursor as get_cursor

CODES_TO_FIX = ["DS_DIR_EVOLUTION_CA_12M", "DS_VTE_CA_MENSUEL"]

def add_nb_articles(code):
    rows = execute_query(
        "SELECT id, query_template FROM APP_DataSources_Templates WHERE code = ?",
        (code,), use_cache=False
    )
    if not rows:
        print(f"  [NOT FOUND] {code}")
        return

    tmpl = rows[0]["query_template"]
    if "[Nb Articles]" in tmpl or "Nb Articles" in tmpl:
        print(f"  [ALREADY OK] {code} contient déjà Nb Articles")
        return

    # Insérer COUNT(DISTINCT [Code article]) AS [Nb Articles] juste après Nb Documents
    # ou avant COUNT(DISTINCT [Code client]) si Nb Documents absent
    if "Nb Documents" in tmpl:
        old = "COUNT(DISTINCT li.[N° Pièce]) AS [Nb Documents],"
        new = "COUNT(DISTINCT li.[N° Pièce]) AS [Nb Documents],\n    COUNT(DISTINCT li.[Code article]) AS [Nb Articles],"
        if old not in tmpl:
            # Sans virgule trailing (dernier champ avant FROM)
            old = "COUNT(DISTINCT li.[N° Pièce]) AS [Nb Documents]"
            new = "COUNT(DISTINCT li.[N° Pièce]) AS [Nb Documents],\n    COUNT(DISTINCT li.[Code article]) AS [Nb Articles]"
        updated = tmpl.replace(old, new, 1)
    elif "Nb Clients" in tmpl:
        old = "COUNT(DISTINCT li.[Code client]) AS [Nb Clients],"
        new = "COUNT(DISTINCT li.[Code article]) AS [Nb Articles],\n    COUNT(DISTINCT li.[Code client]) AS [Nb Clients],"
        if old not in tmpl:
            old = "COUNT(DISTINCT li.[Code client]) AS [Nb Clients]"
            new = "COUNT(DISTINCT li.[Code article]) AS [Nb Articles],\n    COUNT(DISTINCT li.[Code client]) AS [Nb Clients]"
        updated = tmpl.replace(old, new, 1)
    else:
        print(f"  [SKIP] {code} - pattern d'insertion non trouvé")
        return

    if updated == tmpl:
        print(f"  [SKIP] {code} - aucun remplacement effectué (vérifier manuellement)")
        return

    with get_cursor() as cursor:
        cursor.execute(
            "UPDATE APP_DataSources_Templates SET query_template = ? WHERE code = ?",
            (updated, code)
        )
    print(f"  [FIXED] {code} - Nb Articles ajouté")

print("=" * 60)
print("Fix Nb Articles dans datasources")
print("=" * 60)
for code in CODES_TO_FIX:
    add_nb_articles(code)
print("\nDone. Rechargez le pivot dans le navigateur.")
