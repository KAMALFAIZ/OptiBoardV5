# -*- coding: utf-8 -*-
"""
Corriger les queries DS4 et DS5 :
- Utiliser les vrais noms de colonnes Sage (avec accents/degres)
- DS4 : remplacer jointure APP_Objectifs (cross-DB) par comparaison N vs N-1
- DS5 : corriger noms colonnes Sage (Entete, N Piece, Quantite, etc.)
"""
import sys, os, warnings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings('ignore')
from app.database_unified import execute_central

# ── DS4 : Objectifs vs Realise -> devient Comparaison N vs N-1 par commercial
# Justification : APP_Objectifs est dans la DB centrale, non accessible depuis Sage
# Solution plus robuste : comparer CA annee courante vs annee precedente
DS4_QUERY = """SELECT
    ISNULL(CAST(en.[Code représentant] AS NVARCHAR(50)), 'N/A') AS [Code Commercial],
    ISNULL(en.[Nom représentant], 'Non assigné') AS [Commercial],
    li.[societe] AS [Societe],
    YEAR(li.[Date BL]) AS [Annee],
    COUNT(DISTINCT li.[Code client]) AS [Nb Clients],
    COUNT(DISTINCT li.[N° Pièce]) AS [Nb Documents],
    SUM(CASE WHEN YEAR(li.[Date BL]) = YEAR(@dateFin) THEN li.[Montant HT Net] ELSE 0 END) AS [CA Realise HT],
    SUM(CASE WHEN YEAR(li.[Date BL]) = YEAR(@dateFin) THEN ISNULL(li.[Marge], 0) ELSE 0 END) AS [Marge Realisee],
    SUM(CASE WHEN YEAR(li.[Date BL]) = YEAR(@dateFin) - 1 THEN li.[Montant HT Net] ELSE 0 END) AS [CA N-1 HT],
    SUM(CASE WHEN YEAR(li.[Date BL]) = YEAR(@dateFin) THEN li.[Montant HT Net] ELSE 0 END)
    - SUM(CASE WHEN YEAR(li.[Date BL]) = YEAR(@dateFin) - 1 THEN li.[Montant HT Net] ELSE 0 END) AS [Ecart CA],
    CASE
        WHEN SUM(CASE WHEN YEAR(li.[Date BL]) = YEAR(@dateFin) - 1 THEN li.[Montant HT Net] ELSE 0 END) > 0
        THEN CAST(
            (SUM(CASE WHEN YEAR(li.[Date BL]) = YEAR(@dateFin) THEN li.[Montant HT Net] ELSE 0 END)
             / SUM(CASE WHEN YEAR(li.[Date BL]) = YEAR(@dateFin) - 1 THEN li.[Montant HT Net] ELSE 0 END) - 1) * 100
            AS DECIMAL(10, 2))
        ELSE NULL
    END AS [Evolution (%)]
FROM [Lignes_des_ventes] li
INNER JOIN [Entête_des_ventes] en
    ON li.[societe] = en.[societe]
    AND li.[Type Document] = en.[Type Document]
    AND li.[N° Pièce] = en.[N° pièce]
WHERE li.[Valorise CA] = 'Oui'
  AND (
      (YEAR(li.[Date BL]) = YEAR(@dateFin)     AND li.[Date BL] BETWEEN @dateDebut AND @dateFin)
      OR
      (YEAR(li.[Date BL]) = YEAR(@dateFin) - 1 AND li.[Date BL] BETWEEN
          DATEADD(YEAR, -1, @dateDebut) AND DATEADD(YEAR, -1, @dateFin))
  )
  AND (@societe IS NULL OR li.[societe] = @societe)
GROUP BY en.[Code représentant], en.[Nom représentant], li.[societe], YEAR(li.[Date BL])
ORDER BY [CA Realise HT] DESC"""

# ── DS5 : Remise par Commercial -> corriger noms colonnes Sage
DS5_QUERY = """SELECT
    ISNULL(en.[Nom représentant], 'Non assigné') AS [Commercial],
    ISNULL(CAST(en.[Code représentant] AS NVARCHAR(50)), 'N/A') AS [Code Commercial],
    li.[societe] AS [Societe],
    li.[Code client] AS [Code Client],
    li.[Intitulé client] AS [Client],
    li.[Code article] AS [Code Article],
    li.[Désignation ligne] AS [Designation],
    ISNULL(li.[Remise 1], 0) AS [Remise 1 (%)],
    ISNULL(li.[Remise 2], 0) AS [Remise 2 (%)],
    SUM(li.[Quantité]) AS [Quantite],
    SUM(li.[Montant HT Net]) AS [CA HT],
    SUM(li.[Quantité] * li.[Prix unitaire]) AS [Montant Brut HT],
    SUM(li.[Quantité] * li.[Prix unitaire]) - SUM(li.[Montant HT Net]) AS [Montant Remise],
    CASE WHEN SUM(li.[Quantité] * li.[Prix unitaire]) > 0
         THEN CAST(
             (SUM(li.[Quantité] * li.[Prix unitaire]) - SUM(li.[Montant HT Net]))
             / SUM(li.[Quantité] * li.[Prix unitaire]) * 100 AS DECIMAL(10,2))
         ELSE 0 END AS [Taux Remise (%)]
FROM [Lignes_des_ventes] li
INNER JOIN [Entête_des_ventes] en
    ON li.[societe] = en.[societe]
    AND li.[Type Document] = en.[Type Document]
    AND li.[N° Pièce] = en.[N° pièce]
WHERE li.[Valorise CA] = 'Oui'
  AND li.[Date BL] BETWEEN @dateDebut AND @dateFin
  AND (@societe IS NULL OR li.[societe] = @societe)
GROUP BY
    en.[Nom représentant], en.[Code représentant],
    li.[societe], li.[Code client], li.[Intitulé client],
    li.[Code article], li.[Désignation ligne],
    li.[Remise 1], li.[Remise 2]
HAVING SUM(li.[Quantité] * li.[Prix unitaire]) - SUM(li.[Montant HT Net]) > 0
ORDER BY [Montant Remise] DESC"""

# Mise a jour DS4
def sql_str(s):
    return s.replace("'", "''")

execute_central(f"""
    UPDATE APP_DataSources_Templates
    SET nom = 'CA par Commercial N vs N-1',
        query_template = '{sql_str(DS4_QUERY)}'
    WHERE code = 'DS_OBJECTIFS_VS_REALISE'
""")
print("DS4 DS_OBJECTIFS_VS_REALISE mis a jour (N vs N-1)")

# Mise a jour des noms de colonnes GV4 (ajouter Ecart CA et Evolution)
import json
GV4_COLS = json.dumps([
    {"field": "Code Commercial",  "header": "Code",           "visible": True,  "width": 80,  "type": "text"},
    {"field": "Commercial",       "header": "Commercial",     "visible": True,  "width": 150, "type": "text"},
    {"field": "Societe",          "header": "Societe",        "visible": True,  "width": 100, "type": "text"},
    {"field": "Annee",            "header": "Annee",          "visible": True,  "width": 70,  "type": "number"},
    {"field": "Nb Clients",       "header": "Nb Clients",     "visible": True,  "width": 90,  "type": "number"},
    {"field": "Nb Documents",     "header": "Nb Docs",        "visible": True,  "width": 80,  "type": "number"},
    {"field": "CA Realise HT",    "header": "CA N (HT)",      "visible": True,  "width": 130, "type": "number"},
    {"field": "Marge Realisee",   "header": "Marge N",        "visible": True,  "width": 110, "type": "number"},
    {"field": "CA N-1 HT",        "header": "CA N-1 (HT)",    "visible": True,  "width": 120, "type": "number"},
    {"field": "Ecart CA",         "header": "Ecart CA",       "visible": True,  "width": 110, "type": "number"},
    {"field": "Evolution (%)",    "header": "Evol. (%)",      "visible": True,  "width": 90,  "type": "number"},
], ensure_ascii=False)

execute_central(f"""
    UPDATE APP_GridViews
    SET columns_config = '{sql_str(GV4_COLS)}'
    WHERE code = 'GV_OBJECTIFS_VS_REALISE'
""")
print("GV4 colonnes mises a jour (N vs N-1)")

# Aussi mettre a jour le nom du menu
execute_central("UPDATE APP_Menus SET nom='CA N vs N-1 par Commercial' WHERE code='PERF_OBJ_REALISE'")
print("Menu R4 renomme -> CA N vs N-1 par Commercial")

# Mise a jour DS5
execute_central(f"""
    UPDATE APP_DataSources_Templates
    SET query_template = '{sql_str(DS5_QUERY)}'
    WHERE code = 'DS_REMISE_PAR_COMMERCIAL'
""")
print("DS5 DS_REMISE_PAR_COMMERCIAL mis a jour (noms colonnes corriges)")

# Verifier les updates
print("\n=== Verification ===")
for code in ['DS_OBJECTIFS_VS_REALISE', 'DS_REMISE_PAR_COMMERCIAL']:
    r = execute_central(f"SELECT code, nom, LEN(query_template) AS qlen FROM APP_DataSources_Templates WHERE code='{code}'")
    if r:
        print(f"  {r[0]['code']:35} | {r[0]['nom']} | query={r[0]['qlen']} chars")

print("\nOK - corrections appliquees")
