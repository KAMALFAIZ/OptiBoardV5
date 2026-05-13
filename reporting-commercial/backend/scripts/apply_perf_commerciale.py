"""
Réorganisation Performance Commerciale — Exécution complète.

ÉTAPE 1 : Supprimer doublons (1226=GV439, 1227=GV438 déjà dans CA)
ÉTAPE 2 : Déplacer 1223 -> CA (1185), 1224+1225 -> Documents Commerciaux (1196)
ÉTAPE 3 : Renuméroter les items restants dans Performance Commerciale
ÉTAPE 4 : Insérer les 6 assets existants dans Performance Commerciale
"""
import sys, os, warnings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings('ignore')
from app.database_unified import execute_central

# ── Vérifier si APP_Menus a une colonne IDENTITY ──────────────────────────
print("=== Vérification colonne identité APP_Menus ===")
id_check = execute_central("""
    SELECT COLUMNPROPERTY(OBJECT_ID('APP_Menus'), 'id', 'IsIdentity') AS is_identity
""")
is_identity = id_check[0]['is_identity'] if id_check else 0
print(f"  id est IDENTITY = {is_identity}")

max_id = execute_central("SELECT MAX(id) AS max_id FROM APP_Menus")[0]['max_id']
print(f"  MAX id actuel = {max_id}")

# ── ÉTAPE 1 : Supprimer les doublons ──────────────────────────────────────
print("\n=== ÉTAPE 1 — Suppression des doublons dans Performance Commerciale ===")

# 1226 (GV=439 CA par Zone Geo) -> déjà en 1190 dans CA
# 1227 (GV=438 CA par Canal) -> déjà en 1189 dans CA
for del_id in [1226, 1227]:
    row = execute_central(f"SELECT id, nom, target_id FROM APP_Menus WHERE id={del_id}")
    if row:
        print(f"  Suppression id={del_id} '{row[0]['nom']}' (GV={row[0]['target_id']}) — doublon dans CA")
        execute_central(f"DELETE FROM APP_Menus WHERE id={del_id}")
    else:
        print(f"  id={del_id} introuvable (déjà supprimé ?)")

# ── ÉTAPE 2 : Déplacer les items mal placés ───────────────────────────────
print("\n=== ÉTAPE 2 — Déplacement vers bonnes sections ===")

# MAX ordre dans CA (1185)
ca_max = execute_central("SELECT MAX(ordre) AS mo FROM APP_Menus WHERE parent_id=1185")[0]['mo'] or 0
# 1223 -> CA (1185) : CA Commercial/Mois
execute_central(f"""
    UPDATE APP_Menus SET parent_id=1185, ordre={ca_max+1}
    WHERE id=1223
""")
row = execute_central("SELECT nom, target_id FROM APP_Menus WHERE id=1223")
print(f"  id=1223 '{row[0]['nom']}' (GV={row[0]['target_id']}) -> CA (1185) ordre={ca_max+1}")

# MAX ordre dans Documents Commerciaux (1196)
doc_max = execute_central("SELECT MAX(ordre) AS mo FROM APP_Menus WHERE parent_id=1196")[0]['mo'] or 0
# 1224 -> Documents Commerciaux (1196) : Commandes en Cours
execute_central(f"""
    UPDATE APP_Menus SET parent_id=1196, ordre={doc_max+1}
    WHERE id=1224
""")
row = execute_central("SELECT nom, target_id FROM APP_Menus WHERE id=1224")
print(f"  id=1224 '{row[0]['nom']}' (GV={row[0]['target_id']}) -> Documents Commerciaux (1196) ordre={doc_max+1}")

# 1225 -> Documents Commerciaux (1196) : Taux Transformation Devis
doc_max2 = execute_central("SELECT MAX(ordre) AS mo FROM APP_Menus WHERE parent_id=1196")[0]['mo'] or 0
execute_central(f"""
    UPDATE APP_Menus SET parent_id=1196, ordre={doc_max2+1}
    WHERE id=1225
""")
row = execute_central("SELECT nom, target_id FROM APP_Menus WHERE id=1225")
print(f"  id=1225 '{row[0]['nom']}' (GV={row[0]['target_id']}) -> Documents Commerciaux (1196) ordre={doc_max2+1}")

# ── ÉTAPE 3 : Renuméroter les items restants dans Performance Commerciale ──
print("\n=== ÉTAPE 3 — Renumérotation des items restants (parent_id=1221) ===")
# Items restants : 1222 (GV=440), 1228 (GV=469), 1229 (GV=454)
# Nouvel ordre souhaité:
#   1. GV=387  Performance par Commercial (à créer en étape 4)
#   2. GV=454  Ranking Commerciaux (id=1229)
#   3. GV=440  CA par Commercial (id=1222)
#   4. GV=469  Echeances par Commercial (id=1228)
#   5-9 : nouveaux items

reorder = [
    (1229, 2),  # Ranking Commerciaux
    (1222, 3),  # CA par Commercial
    (1228, 4),  # Echeances par Commercial
]
for mid, new_ordre in reorder:
    execute_central(f"UPDATE APP_Menus SET ordre={new_ordre} WHERE id={mid}")
    row = execute_central(f"SELECT nom FROM APP_Menus WHERE id={mid}")
    print(f"  id={mid} '{row[0]['nom']}' -> ordre={new_ordre}")

# ── ÉTAPE 4 : Insérer les 6 assets existants ──────────────────────────────
print("\n=== ÉTAPE 4 — Insertion des 6 assets dans Performance Commerciale ===")

new_items = [
    # (nom, type, target_id, ordre)
    ("Performance par Commercial",              "gridview",  387, 1),
    ("CA par Commercial (Pivot)",               "pivot",     128, 5),
    ("Performance Commercial (Pivot)",          "pivot",     140, 6),
    ("Rentabilite Annuelle/Trimestrielle (Pivot)", "pivot",  118, 7),
    ("TB Commercial",                           "dashboard", 168, 8),
    ("TB Responsable Commercial",               "dashboard", 169, 9),
]

if is_identity:
    # Laisser SQL générer l'ID
    for nom, typ, tid, ord_ in new_items:
        execute_central(f"""
            INSERT INTO APP_Menus (nom, type, target_id, parent_id, ordre, code, actif)
            VALUES ('{nom}', '{typ}', {tid}, 1221, {ord_},
                    'PERF_{typ.upper()}_{tid}', 1)
        """)
        print(f"  Inséré '{nom}' (type={typ}, target={tid}, ordre={ord_})")
else:
    # ID manuel
    next_id = max_id + 1
    for nom, typ, tid, ord_ in new_items:
        execute_central(f"""
            INSERT INTO APP_Menus (id, nom, type, target_id, parent_id, ordre, code, actif)
            VALUES ({next_id}, '{nom}', '{typ}', {tid}, 1221, {ord_},
                    'PERF_{typ.upper()}_{tid}', 1)
        """)
        print(f"  Inséré id={next_id} '{nom}' (type={typ}, target={tid}, ordre={ord_})")
        next_id += 1

# ── Vérification finale ───────────────────────────────────────────────────
print("\n=== RÉSULTAT FINAL — Performance Commerciale (parent_id=1221) ===")
items = execute_central(
    "SELECT id, nom, type, target_id, ordre FROM APP_Menus WHERE parent_id=1221 ORDER BY ordre"
)
for r in items:
    print(f"  [id={r['id']}] ordre={r['ordre']} | type='{r['type']}' target={r['target_id']} | {r['nom']}")

print("\n=== RÉSULTAT FINAL — CA (parent_id=1185) ===")
ca_items = execute_central(
    "SELECT id, nom, type, target_id, ordre FROM APP_Menus WHERE parent_id=1185 ORDER BY ordre"
)
for r in ca_items:
    print(f"  [id={r['id']}] ordre={r['ordre']} | GV={r['target_id']} | {r['nom']}")

print("\n=== RÉSULTAT FINAL — Documents Commerciaux (parent_id=1196) ===")
doc_items = execute_central(
    "SELECT id, nom, type, target_id, ordre FROM APP_Menus WHERE parent_id=1196 ORDER BY ordre"
)
for r in doc_items:
    print(f"  [id={r['id']}] ordre={r['ordre']} | GV={r['target_id']} | {r['nom']}")
