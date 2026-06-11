"""
Ajoute au menu :
  - Fiche Client       → sous "Analyse Clients"        (code: clients)
  - Fiche Fournisseur  → sous "Achats & Fournisseurs"  (code: achats)
  - Dettes Fournisseurs→ sous "Recouvrement & Trésorerie" (code: recouvrement)

Usage : python add_fiches_menus.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database_unified import execute_app as execute_query, app_cursor as get_db_cursor

# ---------------------------------------------------------------------------
# Menus à insérer : (code_parent, code_menu, nom, icon, type, url, ordre)
# ---------------------------------------------------------------------------
NOUVEAUX_MENUS = [
    {
        "parent_code":  "clients",
        "code":         "cli-fiche-client",
        "nom":          "Fiche Client",
        "icon":         "UserCheck",
        "type":         "fiche-client",
        "url":          None,
        "ordre":        14,
    },
    {
        "parent_code":  "achats",
        "code":         "ach-fiche-fournisseur",
        "nom":          "Fiche Fournisseur",
        "icon":         "Building2",
        "type":         "fiche-fournisseur",
        "url":          None,
        "ordre":        13,
    },
    {
        "parent_code":  "recouvrement",
        "code":         "rec-dettes-fournisseurs",
        "nom":          "Dettes Fournisseurs",
        "icon":         "TrendingDown",
        "type":         "page",
        "url":          "/dettes-fournisseurs",
        "ordre":        11,
    },
]


def get_parent_id(code: str) -> int | None:
    """Cherche l'id d'un menu par son code."""
    rows = execute_query(
        "SELECT id FROM APP_Menus WHERE code = ?",
        (code,),
        use_cache=False,
    )
    return rows[0]["id"] if rows else None


def menu_exists(code: str) -> bool:
    rows = execute_query(
        "SELECT id FROM APP_Menus WHERE code = ?",
        (code,),
        use_cache=False,
    )
    return len(rows) > 0


def insert_menu(parent_id, nom, code, icon, mtype, url, ordre) -> int:
    with get_db_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO APP_Menus (parent_id, nom, code, icon, type, url, ordre, actif, is_custom)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1)
            """,
            (parent_id, nom, code, icon, mtype, url, ordre),
        )
        cursor.execute("SELECT @@IDENTITY AS id")
        return cursor.fetchone()[0]


def main():
    print("=== Ajout des menus Fiche Client / Fiche Fournisseur / Dettes Fournisseurs ===\n")

    ok = 0
    skip = 0
    err = 0

    for m in NOUVEAUX_MENUS:
        code = m["code"]
        nom  = m["nom"]

        # Vérifier si déjà présent
        if menu_exists(code):
            print(f"  [SKIP] '{nom}' (code={code}) existe déjà")
            skip += 1
            continue

        # Trouver le parent
        parent_id = get_parent_id(m["parent_code"])
        if parent_id is None:
            print(f"  [ERREUR] Parent introuvable : code='{m['parent_code']}' pour '{nom}'")
            err += 1
            continue

        try:
            new_id = insert_menu(
                parent_id = parent_id,
                nom   = nom,
                code  = code,
                icon  = m["icon"],
                mtype = m["type"],
                url   = m["url"],
                ordre = m["ordre"],
            )
            print(f"  [OK] '{nom}' créé (id={new_id}, parent_id={parent_id}, type={m['type']})")
            ok += 1
        except Exception as e:
            print(f"  [ERREUR] '{nom}' : {e}")
            err += 1

    print(f"\n=== Résultat : {ok} créés, {skip} ignorés, {err} erreurs ===")


if __name__ == "__main__":
    main()
