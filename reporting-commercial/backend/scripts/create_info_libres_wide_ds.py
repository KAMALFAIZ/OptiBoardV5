# -*- coding: utf-8 -*-
"""
DataSources d'exploitation des INFOS LIBRES au format COLONNES (approche #2).
=============================================================================
Joignent les tables de base aux tables larges IL_* (1 ligne/entite, 1 colonne/champ),
via `il.*` -> les champs libres apparaissent comme de VRAIES colonnes dans les builders
(pas de pivot manuel), sans l'EAV (garde en parallele).

Jointures :
  Articles          x IL_Articles          sur [Code interne] = entity_key
  Entête_des_ventes x IL_Entetes_Documents sur [N° interne]   = entity_key
  Clients/Fourniss. x IL_Tiers             via Info_Libres_Cle_Tiers
  Lignes_des_ventes x IL_Lignes_Documents  via Info_Libres_Cle_Lignes

Prerequis (sinon les requetes renvoient une erreur "objet invalide") :
  - agent rebuild (extracteur __INFO_LIBRES_WIDE__) deploye + cycle passe
  - tables IL_* + Info_Libres_Cle_* materialisees

Idempotent. Cible : base centrale OptiBoard_SaaS (APP_DataSources_Templates).
Usage : python scripts/create_info_libres_wide_ds.py
"""
import sys, os, json, warnings

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings("ignore")
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

from app.database_unified import execute_central, write_central  # noqa: E402

CATEGORY = "Informations libres (colonnes)"
PARAM_SOCIETE = json.dumps(
    [{"name": "societe", "type": "select", "label": "Société", "required": False, "default": None}],
    ensure_ascii=False)

Q_ARTICLES = """SELECT
    a.[societe]             AS [Societe],
    a.[Code Article]        AS [Code Article],
    a.[Désignation Article] AS [Designation],
    a.[Code Famille]        AS [Code Famille],
    a.[Intitulé famille]    AS [Famille],
    il.*
FROM [Articles] a
LEFT JOIN [IL_Articles] il
       ON il.[entity_key] = CAST(a.[Code interne] AS NVARCHAR(50))
      AND il.[societe]    = a.[societe]
WHERE (@societe IS NULL OR a.[societe] = @societe)"""

Q_VENTES = """SELECT
    en.[societe]         AS [Societe],
    en.[N° pièce]        AS [Num Piece],
    en.[Date]            AS [Date],
    en.[Type Document]   AS [Type Document],
    en.[Code client]     AS [Code Client],
    en.[Intitulé client] AS [Client],
    il.*
FROM [Entête_des_ventes] en
LEFT JOIN [IL_Entetes_Documents] il
       ON il.[entity_key] = CAST(en.[N° interne] AS NVARCHAR(50))
      AND il.[societe]    = en.[societe]
WHERE (@societe IS NULL OR en.[societe] = @societe)"""

Q_CLIENTS = """SELECT
    cl.[societe]     AS [Societe],
    cl.[Code client] AS [Code Client],
    cl.[Intitulé]    AS [Client],
    il.*
FROM [Clients] cl
LEFT JOIN [Info_Libres_Cle_Tiers] k
       ON k.[societe] = cl.[societe] AND k.[Code tiers] = cl.[Code client]
LEFT JOIN [IL_Tiers] il
       ON il.[entity_key] = k.[Clé Sage] AND il.[societe] = cl.[societe]
WHERE (@societe IS NULL OR cl.[societe] = @societe)"""

Q_FOURNISSEURS = """SELECT
    fo.[societe]          AS [Societe],
    fo.[Code fournisseur] AS [Code Fournisseur],
    fo.[Intitulé]         AS [Fournisseur],
    il.*
FROM [Fournisseurs] fo
LEFT JOIN [Info_Libres_Cle_Tiers] k
       ON k.[societe] = fo.[societe] AND k.[Code tiers] = fo.[Code fournisseur]
LEFT JOIN [IL_Tiers] il
       ON il.[entity_key] = k.[Clé Sage] AND il.[societe] = fo.[societe]
WHERE (@societe IS NULL OR fo.[societe] = @societe)"""

Q_LIGNES_VENTES = """SELECT
    li.[societe]       AS [Societe],
    li.[N° Pièce]      AS [Num Piece],
    li.[Date BL]       AS [Date BL],
    li.[Code client]   AS [Code Client],
    li.[Code article]  AS [Code Article],
    li.[Désignation ligne] AS [Designation],
    li.[Quantité]      AS [Quantite],
    li.[Montant HT Net] AS [Montant HT],
    il.*
FROM [Lignes_des_ventes] li
LEFT JOIN [Info_Libres_Cle_Lignes] k
       ON k.[societe] = li.[societe] AND k.[N° interne] = CAST(li.[N° interne] AS NVARCHAR(50))
LEFT JOIN [IL_Lignes_Documents] il
       ON il.[entity_key] = k.[Clé Sage] AND il.[societe] = li.[societe]
WHERE (@societe IS NULL OR li.[societe] = @societe)"""

DATASOURCES = [
    ("DS_IL_ARTICLES", "Infos libres colonnes — Articles",
     "Articles + champs libres en colonnes (jointure directe).", Q_ARTICLES),
    ("DS_IL_VENTES", "Infos libres colonnes — Documents de ventes",
     "Entêtes ventes + champs libres en colonnes.", Q_VENTES),
    ("DS_IL_CLIENTS", "Infos libres colonnes — Clients",
     "Clients + champs libres en colonnes (via clé tiers).", Q_CLIENTS),
    ("DS_IL_FOURNISSEURS", "Infos libres colonnes — Fournisseurs",
     "Fournisseurs + champs libres en colonnes (via clé tiers).", Q_FOURNISSEURS),
    ("DS_IL_LIGNES_VENTES", "Infos libres colonnes — Lignes de ventes",
     "Lignes de ventes + champs libres en colonnes (via clé lignes).", Q_LIGNES_VENTES),
]


def upsert(code, nom, desc, qt):
    if execute_central("SELECT COUNT(*) n FROM APP_DataSources_Templates WHERE code=?", (code,), use_cache=False)[0]["n"]:
        write_central(
            """UPDATE APP_DataSources_Templates
                  SET nom=?, description=?, query_template=?, parameters=?, category=?, type='query', actif=1
                WHERE code=?""",
            (nom, desc, qt, PARAM_SOCIETE, CATEGORY, code))
        print(f"  ~ MAJ  {code}")
    else:
        write_central(
            """INSERT INTO APP_DataSources_Templates
                   (code, nom, type, category, description, query_template, parameters, is_system, actif)
                   VALUES (?, ?, 'query', ?, ?, ?, ?, 0, 1)""",
            (code, nom, CATEGORY, desc, qt, PARAM_SOCIETE))
        print(f"  + NEW  {code}")


def main():
    print("=" * 70)
    print("  DataSources INFOS LIBRES — format COLONNES (approche #2)")
    print("=" * 70)
    for code, nom, desc, qt in DATASOURCES:
        try: upsert(code, nom, desc, qt)
        except Exception as e: print(f"  ! ERREUR {code}: {e}")
    print("-" * 70)
    print(f"  {len(DATASOURCES)} datasources — catégorie « {CATEGORY} »")
    print("  (actives une fois les tables IL_* matérialisées par l'agent à jour)")
    print("=" * 70)


if __name__ == "__main__":
    main()
