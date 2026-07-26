# -*- coding: utf-8 -*-
"""
Enregistre les DataSource templates d'exploitation des INFORMATIONS LIBRES Sage.
=================================================================================
Objectif : rendre les informations libres (champs paramétrables Sage) exploitables
dans les builders (Dashboard / GridView / Pivot), en format « long » (une ligne par
champ), directement consommable par le Pivot builder.

Contexte technique (voir docs/INFORMATIONS_LIBRES_SAGE.md) :
- Les définitions vivent dans la table DWH `Info_Libres` (catalogue).
- Les valeurs vivent dans `Info_Libres_Valeurs` (EAV : CB_File, entity_key, CB_Name, CB_Value, societe).
- La jointure valeur -> entité se fait sur entity_key = cbMarq de la table Sage parente :
    * F_ARTICLE   -> Articles.[Code interne]          (clé présente)
    * F_DOCENTETE -> Entête_des_ventes.[N° interne]   (clé présente, domaine ventes)
    * F_COMPTET   -> via la table de correspondance Info_Libres_Cle_Tiers (clé additive)
- Le datasource « BRUT » expose l'EAV tel quel : il fonctionne pour TOUTES les entités
  (y compris achats / lignes) même sans clé de jointure.

Idempotent : ré-exécutable (UPDATE si le code existe déjà, INSERT sinon).
Cible : base centrale OptiBoard_SaaS (APP_DataSources_Templates).

Usage : python scripts/create_info_libres_ds.py
"""
import sys
import os
import json
import warnings

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings("ignore")

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from app.database_unified import execute_central, write_central  # noqa: E402

CATEGORY = "Informations libres"

# Paramètre société commun (optionnel) — injecté par le resolver comme les autres DS.
PARAM_SOCIETE = json.dumps(
    [{"name": "societe", "type": "select", "label": "Société", "required": False, "default": None}],
    ensure_ascii=False,
)
PARAM_NONE = json.dumps([], ensure_ascii=False)

# Paramètres pour la requête CA (période + société)
PARAM_CA = json.dumps(
    [
        {"name": "dateDebut", "type": "date", "label": "Date début", "required": True, "default": None},
        {"name": "dateFin", "type": "date", "label": "Date fin", "required": True, "default": None},
        {"name": "societe", "type": "select", "label": "Société", "required": False, "default": None},
    ],
    ensure_ascii=False,
)

# ---------------------------------------------------------------------------
# Définition des datasources (code, nom, description, query_template, parameters)
# ---------------------------------------------------------------------------

Q_CATALOGUE = """SELECT DISTINCT
    il.[CB_File] AS [Table Sage],
    CASE il.[CB_File]
        WHEN 'F_ARTICLE'   THEN 'Articles'
        WHEN 'F_COMPTET'   THEN 'Tiers (clients / fournisseurs)'
        WHEN 'F_DOCENTETE' THEN 'Entêtes de documents'
        WHEN 'F_DOCLIGNE'  THEN 'Lignes de documents'
        ELSE il.[CB_File]
    END AS [Entité],
    il.[CB_Name] AS [Champ libre]
FROM [Info_Libres] il
WHERE il.[CB_Name] IS NOT NULL AND il.[CB_Name] <> ''
ORDER BY [Table Sage], [Champ libre]"""

Q_BRUT = """SELECT
    v.[societe]    AS [Societe],
    v.[CB_File]    AS [Table Sage],
    v.[entity_key] AS [Clé entité],
    v.[CB_Name]    AS [Champ],
    v.[CB_Value]   AS [Valeur]
FROM [Info_Libres_Valeurs] v
WHERE (@societe IS NULL OR v.[societe] = @societe)
ORDER BY v.[CB_File], v.[CB_Name]"""

Q_ARTICLES = """SELECT
    a.[societe]              AS [Societe],
    a.[Code Article]         AS [Code Article],
    a.[Désignation Article]  AS [Designation],
    a.[Code Famille]         AS [Code Famille],
    a.[Intitulé famille]     AS [Famille],
    v.[CB_Name]              AS [Champ],
    v.[CB_Value]             AS [Valeur]
FROM [Articles] a
INNER JOIN [Info_Libres_Valeurs] v
        ON v.[CB_File]    = 'F_ARTICLE'
       AND v.[societe]    = a.[societe]
       AND v.[entity_key] = CAST(a.[Code interne] AS NVARCHAR(50))
WHERE (@societe IS NULL OR a.[societe] = @societe)
ORDER BY a.[Code Article], v.[CB_Name]"""

Q_VENTES = """SELECT
    en.[societe]          AS [Societe],
    en.[N° pièce]         AS [Num Piece],
    en.[Date]             AS [Date],
    en.[Type Document]    AS [Type Document],
    en.[Code client]      AS [Code Client],
    en.[Intitulé client]  AS [Client],
    v.[CB_Name]           AS [Champ],
    v.[CB_Value]          AS [Valeur]
FROM [Entête_des_ventes] en
INNER JOIN [Info_Libres_Valeurs] v
        ON v.[CB_File]    = 'F_DOCENTETE'
       AND v.[societe]    = en.[societe]
       AND v.[entity_key] = CAST(en.[N° interne] AS NVARCHAR(50))
WHERE (@societe IS NULL OR en.[societe] = @societe)
ORDER BY en.[Date] DESC, en.[N° pièce], v.[CB_Name]"""

# CA (ventes) ventilé par information libre d'entête de document (format long).
# Règles CA : [Valorise CA]='Oui', période sur [Date BL]. Jointure infos libres
# via F_DOCENTETE / entity_key = Entête_des_ventes.[N° interne] (= cbMarq).
Q_CA_INFOS_LIBRES = """SELECT
    il.[CB_Name]              AS [Information libre],
    il.[CB_Value]            AS [Valeur],
    SUM(l.[Montant HT Net])  AS [CA HT],
    COUNT(DISTINCT l.[N° Pièce]) AS [Nb Documents]
FROM [Lignes_des_ventes] l
INNER JOIN [Entête_des_ventes] e
        ON l.[N° Pièce] = e.[N° pièce]
       AND l.[societe]  = e.[societe]
INNER JOIN [Info_Libres_Valeurs] il
        ON il.[CB_File]    = 'F_DOCENTETE'
       AND il.[entity_key] = CAST(e.[N° interne] AS NVARCHAR(50))
       AND il.[societe]    = e.[societe]
WHERE l.[Valorise CA] = 'Oui'
  AND l.[Date BL] BETWEEN @dateDebut AND @dateFin
  AND (@societe IS NULL OR l.[societe] = @societe)
GROUP BY il.[CB_Name], il.[CB_Value]
ORDER BY il.[CB_Name], [CA HT] DESC"""

# Tiers : jointure en deux sauts via la table de correspondance Info_Libres_Cle_Tiers
# (Code tiers = CT_Num ; Clé Sage = cbMarq de F_COMPTET). Nécessite le sync additif
# « Correspondance clé tiers ». La table est pré-créée vide -> pas d'erreur avant le
# premier sync (résultat simplement vide).
Q_CLIENTS = """SELECT
    cl.[societe]     AS [Societe],
    cl.[Code client] AS [Code Client],
    cl.[Intitulé]    AS [Client],
    v.[CB_Name]      AS [Champ],
    v.[CB_Value]     AS [Valeur]
FROM [Clients] cl
INNER JOIN [Info_Libres_Cle_Tiers] k
        ON k.[societe]    = cl.[societe]
       AND k.[Code tiers] = cl.[Code client]
INNER JOIN [Info_Libres_Valeurs] v
        ON v.[CB_File]    = 'F_COMPTET'
       AND v.[societe]    = cl.[societe]
       AND v.[entity_key] = k.[Clé Sage]
WHERE (@societe IS NULL OR cl.[societe] = @societe)
ORDER BY cl.[Code client], v.[CB_Name]"""

Q_FOURNISSEURS = """SELECT
    fo.[societe]          AS [Societe],
    fo.[Code fournisseur] AS [Code Fournisseur],
    fo.[Intitulé]         AS [Fournisseur],
    v.[CB_Name]           AS [Champ],
    v.[CB_Value]          AS [Valeur]
FROM [Fournisseurs] fo
INNER JOIN [Info_Libres_Cle_Tiers] k
        ON k.[societe]    = fo.[societe]
       AND k.[Code tiers] = fo.[Code fournisseur]
INNER JOIN [Info_Libres_Valeurs] v
        ON v.[CB_File]    = 'F_COMPTET'
       AND v.[societe]    = fo.[societe]
       AND v.[entity_key] = k.[Clé Sage]
WHERE (@societe IS NULL OR fo.[societe] = @societe)
ORDER BY fo.[Code fournisseur], v.[CB_Name]"""

DATASOURCES = [
    (
        "DS_INFO_LIBRES_CATALOGUE",
        "Infos libres — Catalogue des champs",
        "Liste des champs libres définis dans Sage (table, entité, nom du champ).",
        Q_CATALOGUE,
        PARAM_NONE,
    ),
    (
        "DS_INFO_LIBRES_BRUT",
        "Infos libres — Valeurs brutes (EAV)",
        "Toutes les valeurs d'informations libres, tous types d'entités (format long). Fonctionne même sans clé de jointure.",
        Q_BRUT,
        PARAM_SOCIETE,
    ),
    (
        "DS_INFO_LIBRES_ARTICLES",
        "Infos libres — Articles",
        "Articles enrichis de leurs informations libres (une ligne par champ).",
        Q_ARTICLES,
        PARAM_SOCIETE,
    ),
    (
        "DS_INFO_LIBRES_VENTES",
        "Infos libres — Documents de ventes",
        "Entêtes de documents de ventes enrichis de leurs informations libres (une ligne par champ).",
        Q_VENTES,
        PARAM_SOCIETE,
    ),
    (
        "DS_INFO_LIBRES_CLIENTS",
        "Infos libres — Clients",
        "Clients enrichis de leurs informations libres (via correspondance clé tiers). Requiert le sync « Correspondance clé tiers ».",
        Q_CLIENTS,
        PARAM_SOCIETE,
    ),
    (
        "DS_INFO_LIBRES_FOURNISSEURS",
        "Infos libres — Fournisseurs",
        "Fournisseurs enrichis de leurs informations libres (via correspondance clé tiers). Requiert le sync « Correspondance clé tiers ».",
        Q_FOURNISSEURS,
        PARAM_SOCIETE,
    ),
    (
        "DS_CA_INFOS_LIBRES",
        "CA par information libre",
        "Chiffre d'affaires (ventes) ventilé par information libre d'entête de document (format long, F_DOCENTETE). Règles CA appliquées ([Valorise CA]='Oui', période sur [Date BL]).",
        Q_CA_INFOS_LIBRES,
        PARAM_CA,
    ),
]


def upsert(code, nom, description, query_template, parameters):
    existing = execute_central(
        "SELECT id FROM APP_DataSources_Templates WHERE code = ?",
        (code,),
        use_cache=False,
    )
    if existing:
        write_central(
            """UPDATE APP_DataSources_Templates
                  SET nom = ?, description = ?, query_template = ?, parameters = ?,
                      category = ?, type = 'query', actif = 1
                WHERE code = ?""",
            (nom, description, query_template, parameters, CATEGORY, code),
        )
        print(f"  ~ MAJ  {code}")
        return "updated"
    else:
        write_central(
            """INSERT INTO APP_DataSources_Templates
                   (code, nom, type, category, description, query_template, parameters, is_system, actif)
                   VALUES (?, ?, 'query', ?, ?, ?, ?, 0, 1)""",
            (code, nom, CATEGORY, description, query_template, parameters),
        )
        print(f"  + NEW  {code}")
        return "inserted"


def main():
    print("=" * 70)
    print("  DataSources d'exploitation des INFORMATIONS LIBRES Sage")
    print("=" * 70)
    inserted = updated = 0
    for code, nom, description, qt, params in DATASOURCES:
        try:
            res = upsert(code, nom, description, qt, params)
            if res == "inserted":
                inserted += 1
            else:
                updated += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  ! ERREUR {code} : {exc}")
    print("-" * 70)
    print(f"  {inserted} créé(s), {updated} mis à jour, {len(DATASOURCES)} au total")
    print("  Catégorie : " + CATEGORY)
    print("=" * 70)


if __name__ == "__main__":
    main()
