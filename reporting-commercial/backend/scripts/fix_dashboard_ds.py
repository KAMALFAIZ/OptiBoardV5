# -*- coding: utf-8 -*-
"""
Corrige les 3 datasources du dashboard 166 (Vue Commerciale - CA, Marge & Vendeurs):
1. DS_KPI_RESUME : ajouter TauxMarge, NbArticlesVendus, fixer Marge (ISNULL)
2. DS_CA_AGREGE_REPRESENTANT : fixer marge (utiliser CMUP directement, pas @Valorisation)
3. DS_CA_AGREGE_ARTICLE : idem
"""

import pyodbc
import sys

CONN_STR = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019"
DRY_RUN = "--dry-run" in sys.argv


# =====================================================
# DS_KPI_RESUME - Fix complet
# =====================================================
DS_KPI_RESUME = """SELECT
    (SELECT ISNULL(SUM([Montant HT Net]), 0)
     FROM [Lignes_des_ventes]
     WHERE [Valorise CA] = 'Oui'
       AND [Date BL] BETWEEN @dateDebut AND @dateFin
       AND (@societe IS NULL OR [societe] = @societe)) AS CA,

    (SELECT ISNULL(SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]), 0)
     FROM [Lignes_des_ventes]
     WHERE [Valorise CA] = 'Oui'
       AND [Date BL] BETWEEN @dateDebut AND @dateFin
       AND (@societe IS NULL OR [societe] = @societe)) AS Marge,

    (SELECT CASE WHEN ISNULL(SUM([Montant HT Net]), 0) > 0
        THEN ROUND(
            SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) * 100.0
            / SUM([Montant HT Net]), 2)
        ELSE 0 END
     FROM [Lignes_des_ventes]
     WHERE [Valorise CA] = 'Oui'
       AND [Date BL] BETWEEN @dateDebut AND @dateFin
       AND (@societe IS NULL OR [societe] = @societe)) AS TauxMarge,

    (SELECT COUNT(DISTINCT [Code article])
     FROM [Lignes_des_ventes]
     WHERE [Valorise CA] = 'Oui'
       AND [Date BL] BETWEEN @dateDebut AND @dateFin
       AND (@societe IS NULL OR [societe] = @societe)) AS NbArticlesVendus,

    (SELECT ISNULL(SUM([Valeur du stock (montant)]), 0)
     FROM [Etat_Stock]
     WHERE (@societe IS NULL OR [societe] = @societe)) AS ValeurStock,

    (SELECT ISNULL(SUM([Montant échéance] - ISNULL([Montant du règlement], 0)), 0)
     FROM [Échéances_Ventes]
     WHERE [Montant échéance] > ISNULL([Montant du règlement], 0)
       AND (@societe IS NULL OR [societe] = @societe)) AS Encours,

    (SELECT ISNULL(SUM([Montant échéance] - ISNULL([Montant du règlement], 0)), 0)
     FROM [Échéances_Ventes]
     WHERE [Montant échéance] > ISNULL([Montant du règlement], 0)
       AND DATEDIFF(DAY, [Date d'échéance], GETDATE()) > 120
       AND (@societe IS NULL OR [societe] = @societe)) AS CreancesDouteuses,

    (SELECT COUNT(DISTINCT [Code client])
     FROM [Lignes_des_ventes]
     WHERE [Valorise CA] = 'Oui'
       AND [Date BL] BETWEEN @dateDebut AND @dateFin
       AND (@societe IS NULL OR [societe] = @societe)) AS NbClientsActifs"""


# =====================================================
# DS_CA_AGREGE_REPRESENTANT - Simplifié avec CMUP direct
# =====================================================
DS_CA_AGREGE_REPRESENTANT = """SELECT
    l.societe AS [Société],
    ISNULL(en.[Nom représentant], 'Non renseigné') AS [Représentant],
    COUNT(DISTINCT en.[Code client]) AS [Nb Clients],
    COUNT(DISTINCT en.[N° pièce]) AS [Nb Documents],
    SUM(l.[Quantité]) AS [Qte Vendue],
    SUM(l.[Montant HT Net]) AS [CA],
    SUM(ISNULL(l.[CMUP], 0) * l.[Quantité]) AS [Cout Revient],
    SUM(l.[Montant HT Net]) - SUM(ISNULL(l.[CMUP], 0) * l.[Quantité]) AS [Marge],
    CASE WHEN SUM(l.[Montant HT Net]) > 0
        THEN ROUND(
            (SUM(l.[Montant HT Net]) - SUM(ISNULL(l.[CMUP], 0) * l.[Quantité])) * 100.0
            / SUM(l.[Montant HT Net]), 2)
        ELSE 0 END AS [Marge %]
FROM [Lignes_des_ventes] l
INNER JOIN [Entête_des_ventes] en
    ON l.societe = en.societe AND l.[Type Document] = en.[Type Document] AND l.[N° Pièce] = en.[N° pièce]
WHERE l.[Valorise CA] = 'Oui'
  AND l.[Date BL] BETWEEN @dateDebut AND @dateFin
  AND (@societe IS NULL OR l.societe = @societe)
GROUP BY l.societe, en.[Nom représentant]
ORDER BY [CA] DESC"""


# =====================================================
# DS_CA_AGREGE_ARTICLE - Simplifié avec CMUP direct
# =====================================================
DS_CA_AGREGE_ARTICLE = """SELECT
    l.societe AS [Société],
    l.[Code article],
    ISNULL(a.[Désignation Article], l.[Désignation ligne]) AS [Désignation Article],
    a.[Code Famille],
    a.[Intitulé famille],
    a.[Catalogue 1],
    a.[Catalogue 2],
    COUNT(DISTINCT en.[Code client]) AS [Nb Clients],
    COUNT(DISTINCT en.[N° pièce]) AS [Nb Documents],
    SUM(l.[Quantité]) AS [Qte Vendue],
    SUM(l.[Montant HT Net]) AS [CA],
    SUM(ISNULL(l.[CMUP], 0) * l.[Quantité]) AS [Cout Revient],
    SUM(l.[Montant HT Net]) - SUM(ISNULL(l.[CMUP], 0) * l.[Quantité]) AS [Marge],
    CASE WHEN SUM(l.[Montant HT Net]) > 0
        THEN ROUND(
            (SUM(l.[Montant HT Net]) - SUM(ISNULL(l.[CMUP], 0) * l.[Quantité])) * 100.0
            / SUM(l.[Montant HT Net]), 2)
        ELSE 0 END AS [Marge %],
    AVG(l.[Prix unitaire]) AS [Prix Moyen Vente],
    AVG(ISNULL(l.[CMUP], 0)) AS [Coût Moyen]
FROM [Lignes_des_ventes] l
INNER JOIN [Entête_des_ventes] en
    ON l.societe = en.societe AND l.[Type Document] = en.[Type Document] AND l.[N° Pièce] = en.[N° pièce]
LEFT JOIN [Articles] a
    ON l.societe = a.societe AND l.[Code article] = a.[Code Article]
WHERE l.[Valorise CA] = 'Oui'
  AND l.[Date BL] BETWEEN @dateDebut AND @dateFin
  AND (@societe IS NULL OR l.societe = @societe)
GROUP BY l.societe, l.[Code article], a.[Désignation Article], l.[Désignation ligne],
         a.[Code Famille], a.[Intitulé famille], a.[Catalogue 1], a.[Catalogue 2]
ORDER BY [CA] DESC"""


def main():
    conn = pyodbc.connect(CONN_STR, timeout=30)
    cursor = conn.cursor()

    updates = {
        'DS_KPI_RESUME': DS_KPI_RESUME,
        'DS_CA_AGREGE_REPRESENTANT': DS_CA_AGREGE_REPRESENTANT,
        'DS_CA_AGREGE_ARTICLE': DS_CA_AGREGE_ARTICLE,
    }

    for code, new_query in updates.items():
        cursor.execute("SELECT id FROM APP_DataSources_Templates WHERE code = ?", (code,))
        row = cursor.fetchone()
        if row:
            if DRY_RUN:
                print(f"[DRY-RUN] Would update {code} (id={row[0]})")
            else:
                cursor.execute(
                    "UPDATE APP_DataSources_Templates SET query_template = ? WHERE id = ?",
                    (new_query, row[0])
                )
                print(f"Updated {code} (id={row[0]})")
        else:
            print(f"NOT FOUND: {code}")

    if not DRY_RUN:
        conn.commit()
        print("\nCommit OK!")
    else:
        print("\n>>> Relancer sans --dry-run pour appliquer")

    conn.close()


if __name__ == "__main__":
    main()
