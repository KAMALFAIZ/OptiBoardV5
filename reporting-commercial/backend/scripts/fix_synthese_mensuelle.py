# -*- coding: utf-8 -*-
"""
Implémente DS_DIR_SYNTHESE_MENSUELLE et corrige la config pivot 121.
Colonnes: Période, CA HT Mois, CA HT N-1, Ecart CA vs N-1, Evol CA % vs N-1,
          Marge Brute Mois, Taux Marge %, Achats HT Mois, Nb Commandes Achats,
          Solde Tresorerie, Nb Echeances Depassees, Valeur Stock, Nb Ruptures, Nb Stocks Negatifs
"""
import pyodbc, json, sys

SAAS = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019'
DRY_RUN = '--dry-run' in sys.argv

# =============================================================
# NOUVELLE QUERY DATASOURCE
# =============================================================
NEW_QUERY = """;WITH
Ventes AS (
    SELECT
        FORMAT([Date BL], 'yyyy-MM') AS [Periode],
        SUM([Montant HT Net]) AS [CA_HT],
        SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) AS [Marge_HT]
    FROM Lignes_des_ventes
    WHERE [Valorise CA] = 'Oui'
      AND [Date BL] BETWEEN @dateDebut AND @dateFin
      AND (@societe IS NULL OR [societe] = @societe)
    GROUP BY FORMAT([Date BL], 'yyyy-MM')
),
Ventes_N1 AS (
    SELECT
        FORMAT(DATEADD(YEAR, 1, [Date BL]), 'yyyy-MM') AS [Periode],
        SUM([Montant HT Net]) AS [CA_HT_N1]
    FROM Lignes_des_ventes
    WHERE [Valorise CA] = 'Oui'
      AND DATEADD(YEAR, 1, [Date BL]) BETWEEN @dateDebut AND @dateFin
      AND (@societe IS NULL OR [societe] = @societe)
    GROUP BY FORMAT(DATEADD(YEAR, 1, [Date BL]), 'yyyy-MM')
),
Achats AS (
    SELECT
        FORMAT([Date], 'yyyy-MM') AS [Periode],
        SUM([Montant HT Net]) AS [Achats_HT],
        COUNT(DISTINCT [N° Pièce]) AS [Nb_Cmds]
    FROM Lignes_des_achats
    WHERE [Valorise CA] = 'Oui'
      AND [Date] BETWEEN @dateDebut AND @dateFin
      AND (@societe IS NULL OR [societe] = @societe)
    GROUP BY FORMAT([Date], 'yyyy-MM')
)
SELECT
    v.[Periode] AS [Période],
    ROUND(v.[CA_HT], 2) AS [CA HT Mois],
    ROUND(ISNULL(n.[CA_HT_N1], 0), 2) AS [CA HT N-1],
    ROUND(v.[CA_HT] - ISNULL(n.[CA_HT_N1], 0), 2) AS [Ecart CA vs N-1],
    CASE WHEN ISNULL(n.[CA_HT_N1], 0) > 0
        THEN ROUND((v.[CA_HT] - n.[CA_HT_N1]) * 100.0 / n.[CA_HT_N1], 2)
        ELSE 0 END AS [Evol CA % vs N-1],
    ROUND(v.[Marge_HT], 2) AS [Marge Brute Mois],
    CASE WHEN v.[CA_HT] > 0
        THEN ROUND(v.[Marge_HT] * 100.0 / v.[CA_HT], 2)
        ELSE 0 END AS [Taux Marge %],
    ROUND(ISNULL(a.[Achats_HT], 0), 2) AS [Achats HT Mois],
    ISNULL(a.[Nb_Cmds], 0) AS [Nb Commandes Achats],
    ROUND(ISNULL((
        SELECT SUM([Montant HT Net])
        FROM Lignes_des_ventes lv2
        WHERE lv2.[Valorise CA] = 'Oui'
          AND FORMAT(lv2.[Date BL], 'yyyy-MM') = v.[Periode]
          AND (@societe IS NULL OR lv2.[societe] = @societe)
    ) - ISNULL((
        SELECT SUM([Montant HT Net])
        FROM Lignes_des_achats la2
        WHERE la2.[Valorise CA] = 'Oui'
          AND FORMAT(la2.[Date], 'yyyy-MM') = v.[Periode]
          AND (@societe IS NULL OR la2.[societe] = @societe)
    ), 0), 0), 2) AS [Solde Tresorerie],
    (SELECT COUNT(*)
     FROM Echéances_Ventes ev
     WHERE ev.[Montant échéance] > ISNULL(ev.[Montant du règlement], 0)
       AND ev.[Date d'échéance] <= EOMONTH(CAST(v.[Periode] + '-01' AS DATE))
       AND (@societe IS NULL OR ev.[societe] = @societe)
    ) AS [Nb Echeances Depassees],
    ROUND((
        SELECT ISNULL(SUM([Valeur du stock (montant)]), 0)
        FROM Etat_Stock es
        WHERE (@societe IS NULL OR es.[societe] = @societe)
    ), 2) AS [Valeur Stock],
    (SELECT COUNT(*)
     FROM Etat_Stock es2
     WHERE es2.[Quantité en stock] <= 0
       AND es2.[Quantité minimale] > 0
       AND (@societe IS NULL OR es2.[societe] = @societe)
    ) AS [Nb Ruptures],
    (SELECT COUNT(*)
     FROM Etat_Stock es3
     WHERE es3.[Quantité en stock] < 0
       AND (@societe IS NULL OR es3.[societe] = @societe)
    ) AS [Nb Stocks Negatifs]
FROM Ventes v
LEFT JOIN Ventes_N1 n ON v.[Periode] = n.[Periode]
LEFT JOIN Achats a ON v.[Periode] = a.[Periode]
ORDER BY v.[Periode]"""

# =============================================================
# NOUVELLE CONFIG PIVOT
# =============================================================
NEW_ROWS_CONFIG = json.dumps([
    {"field": "Période", "label": "Mois", "type": "text"}
], ensure_ascii=False)

NEW_VALUES_CONFIG = json.dumps([
    {"field": "CA HT Mois", "label": "CA HT Mois", "aggregation": "SUM", "format": "currency", "decimals": 2, "show_in_totals": True},
    {"field": "CA HT N-1", "label": "CA HT N-1", "aggregation": "SUM", "format": "currency", "decimals": 2, "show_in_totals": True},
    {"field": "Ecart CA vs N-1", "label": "Ecart CA Vs N-1", "aggregation": "SUM", "format": "currency", "decimals": 2, "show_in_totals": True},
    {"field": "Evol CA % vs N-1", "label": "Evol CA % Vs N-1", "aggregation": "AVG", "format": "percent", "decimals": 2, "show_in_totals": True},
    {"field": "Marge Brute Mois", "label": "Marge Brute Mois", "aggregation": "SUM", "format": "currency", "decimals": 2, "show_in_totals": True},
    {"field": "Taux Marge %", "label": "Taux Marge %", "aggregation": "AVG", "format": "percent", "decimals": 2, "show_in_totals": True},
    {"field": "Achats HT Mois", "label": "Achats HT Mois", "aggregation": "SUM", "format": "currency", "decimals": 2, "show_in_totals": True},
    {"field": "Nb Commandes Achats", "label": "Nb Commandes Achats", "aggregation": "SUM", "format": "number", "decimals": 0, "show_in_totals": True},
    {"field": "Solde Tresorerie", "label": "Solde Trésorerie", "aggregation": "SUM", "format": "currency", "decimals": 2, "show_in_totals": True},
    {"field": "Nb Echeances Depassees", "label": "Nb Échéances Dépassées", "aggregation": "MAX", "format": "number", "decimals": 0, "show_in_totals": True},
    {"field": "Valeur Stock", "label": "Valeur Stock", "aggregation": "AVG", "format": "currency", "decimals": 2, "show_in_totals": True},
    {"field": "Nb Ruptures", "label": "Nb Ruptures", "aggregation": "MAX", "format": "number", "decimals": 0, "show_in_totals": True},
    {"field": "Nb Stocks Negatifs", "label": "Nb Stocks Négatifs", "aggregation": "MAX", "format": "number", "decimals": 0, "show_in_totals": True},
], ensure_ascii=False)

def main():
    conn = pyodbc.connect(SAAS, timeout=30)
    c = conn.cursor()

    # Update datasource
    c.execute("SELECT id FROM APP_DataSources_Templates WHERE code = 'DS_DIR_SYNTHESE_MENSUELLE'")
    row = c.fetchone()
    if row:
        if DRY_RUN:
            print(f"[DRY-RUN] Would update DS_DIR_SYNTHESE_MENSUELLE (id={row[0]})")
        else:
            c.execute("UPDATE APP_DataSources_Templates SET query_template = ? WHERE id = ?", (NEW_QUERY, row[0]))
            print(f"Updated DS_DIR_SYNTHESE_MENSUELLE (id={row[0]})")
    else:
        print("ERROR: DS_DIR_SYNTHESE_MENSUELLE not found!")

    # Update pivot 121
    c.execute("SELECT id, rows_config, values_config FROM APP_Pivots_V2 WHERE id = 121")
    pivot = c.fetchone()
    if pivot:
        if DRY_RUN:
            print(f"[DRY-RUN] Would update pivot 121 rows_config and values_config")
        else:
            c.execute(
                "UPDATE APP_Pivots_V2 SET rows_config = ?, values_config = ? WHERE id = 121",
                (NEW_ROWS_CONFIG, NEW_VALUES_CONFIG)
            )
            print(f"Updated pivot 121 rows_config and values_config")
    else:
        print("ERROR: pivot 121 not found!")

    if not DRY_RUN:
        conn.commit()
        print("\nCommit OK!")
    else:
        print("\n>>> Relancer sans --dry-run pour appliquer")

    conn.close()

if __name__ == "__main__":
    main()
