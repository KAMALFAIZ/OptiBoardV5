# -*- coding: utf-8 -*-
"""
Fix dashboard 218 :
1. Corrige le widget l1 (y_field/y_field_2 sans accent pour matcher SQL)
2. Enrichit DS_TB_CA_NvsN1_MOIS avec Marge N/N-1, Nb Clients, Ecart, Evol %
3. Ajoute des widgets KPI cards et Marge au dashboard
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database_unified import get_central_connection

conn = get_central_connection()
conn.autocommit = True
cur = conn.cursor()

# ── 1. Enrichir DS_TB_CA_NvsN1_MOIS ────────────────────────────────────────
NEW_QUERY = """\
SELECT
    MONTH([Date BL]) AS [Mois],
    DATENAME(MONTH, DATEFROMPARTS(2000, MONTH([Date BL]), 1)) AS [Mois Label],
    SUM(CASE WHEN YEAR([Date BL]) = YEAR(@dateFin)     THEN [Montant HT Net] ELSE 0 END) AS [CA Annee N],
    SUM(CASE WHEN YEAR([Date BL]) = YEAR(@dateFin) - 1 THEN [Montant HT Net] ELSE 0 END) AS [CA Annee N-1],
    ROUND(
        SUM(CASE WHEN YEAR([Date BL]) = YEAR(@dateFin)     THEN [Montant HT Net] ELSE 0 END)
      - SUM(CASE WHEN YEAR([Date BL]) = YEAR(@dateFin) - 1 THEN [Montant HT Net] ELSE 0 END), 2
    ) AS [Ecart CA],
    CASE WHEN SUM(CASE WHEN YEAR([Date BL]) = YEAR(@dateFin) - 1 THEN [Montant HT Net] ELSE 0 END) > 0
         THEN ROUND(
             (SUM(CASE WHEN YEAR([Date BL]) = YEAR(@dateFin) THEN [Montant HT Net] ELSE 0 END)
            - SUM(CASE WHEN YEAR([Date BL]) = YEAR(@dateFin) - 1 THEN [Montant HT Net] ELSE 0 END))
            * 100.0
            / SUM(CASE WHEN YEAR([Date BL]) = YEAR(@dateFin) - 1 THEN [Montant HT Net] ELSE 0 END), 2)
         ELSE NULL END AS [Evol CA %],
    SUM(CASE WHEN YEAR([Date BL]) = YEAR(@dateFin)
        THEN [Montant HT Net] - ISNULL([CMUP], 0) * [Quantit\xe9] ELSE 0 END) AS [Marge N],
    SUM(CASE WHEN YEAR([Date BL]) = YEAR(@dateFin) - 1
        THEN [Montant HT Net] - ISNULL([CMUP], 0) * [Quantit\xe9] ELSE 0 END) AS [Marge N-1],
    CASE WHEN SUM(CASE WHEN YEAR([Date BL]) = YEAR(@dateFin) THEN [Montant HT Net] ELSE 0 END) > 0
         THEN ROUND(
             SUM(CASE WHEN YEAR([Date BL]) = YEAR(@dateFin)
                 THEN [Montant HT Net] - ISNULL([CMUP], 0) * [Quantit\xe9] ELSE 0 END) * 100.0
           / SUM(CASE WHEN YEAR([Date BL]) = YEAR(@dateFin) THEN [Montant HT Net] ELSE 0 END), 2)
         ELSE 0 END AS [Marge % N],
    CASE WHEN SUM(CASE WHEN YEAR([Date BL]) = YEAR(@dateFin) - 1 THEN [Montant HT Net] ELSE 0 END) > 0
         THEN ROUND(
             SUM(CASE WHEN YEAR([Date BL]) = YEAR(@dateFin) - 1
                 THEN [Montant HT Net] - ISNULL([CMUP], 0) * [Quantit\xe9] ELSE 0 END) * 100.0
           / SUM(CASE WHEN YEAR([Date BL]) = YEAR(@dateFin) - 1 THEN [Montant HT Net] ELSE 0 END), 2)
         ELSE 0 END AS [Marge % N-1],
    COUNT(DISTINCT CASE WHEN YEAR([Date BL]) = YEAR(@dateFin)     THEN [Code client] END) AS [Nb Clients N],
    COUNT(DISTINCT CASE WHEN YEAR([Date BL]) = YEAR(@dateFin) - 1 THEN [Code client] END) AS [Nb Clients N-1],
    COUNT(DISTINCT CASE WHEN YEAR([Date BL]) = YEAR(@dateFin)     THEN [N\xb0 Pi\xe8ce] END) AS [Nb Docs N],
    COUNT(DISTINCT CASE WHEN YEAR([Date BL]) = YEAR(@dateFin) - 1 THEN [N\xb0 Pi\xe8ce] END) AS [Nb Docs N-1]
FROM [Lignes_des_ventes]
WHERE [Valorise CA] = 'Oui'
  AND YEAR([Date BL]) IN (YEAR(@dateFin), YEAR(@dateFin) - 1)
  AND (@societe IS NULL OR [societe] = @societe)
GROUP BY MONTH([Date BL]), DATENAME(MONTH, DATEFROMPARTS(2000, MONTH([Date BL]), 1))
ORDER BY [Mois]"""

cur.execute(
    "UPDATE APP_DataSources_Templates SET query_template = ? WHERE code = 'DS_TB_CA_NvsN1_MOIS'",
    (NEW_QUERY,)
)
print(f"DS_TB_CA_NvsN1_MOIS enrichi : {cur.rowcount} ligne(s)")

# ── 2. Corriger + enrichir les widgets du dashboard 218 ────────────────────
NEW_WIDGETS = [
    # Tableau comparatif (inchangé, juste mis à jour pour clarté)
    {
        "id": "t1",
        "type": "table",
        "title": "Comparatif Annuel — Détail",
        "x": 0, "y": 0, "w": 12, "h": 5,
        "config": {
            "dataSourceCode": "DS_COMPARATIF_ANNUEL",
            "dataSourceOrigin": "template",
            "drilldownDsCode": "DS_CA_DETAIL_COMPLET",
            "drilldownDsOrigin": "template"
        }
    },
    # Graphique CA N vs N-1 mensuel (corrigé + colonnes enrichies)
    {
        "id": "l1",
        "type": "chart_line",
        "title": "Comparatif CA N vs N-1 par Mois",
        "x": 0, "y": 5, "w": 8, "h": 4,
        "config": {
            "dataSourceCode": "DS_TB_CA_NvsN1_MOIS",
            "dataSourceOrigin": "template",
            "x_field": "Mois Label",
            "y_field": "CA Annee N",
            "y_field_2": "CA Annee N-1",
            "y_label": "N",
            "y_label_2": "N-1",
            "color": "#2563eb",
            "color_2": "#94a3b8",
            "show_grid": True,
            "show_legend": True,
            "drilldownDsCode": "DS_CA_DETAIL_COMPLET",
            "drilldownDsOrigin": "template"
        }
    },
    # Graphique Évol CA % par mois (nouveau)
    {
        "id": "b1",
        "type": "chart_bar",
        "title": "Évolution CA % par Mois (N/N-1)",
        "x": 8, "y": 5, "w": 4, "h": 4,
        "config": {
            "dataSourceCode": "DS_TB_CA_NvsN1_MOIS",
            "dataSourceOrigin": "template",
            "x_field": "Mois Label",
            "y_field": "Evol CA %",
            "y_label": "Évol CA %",
            "color": "#10b981",
            "show_grid": True,
            "show_legend": False
        }
    },
    # Graphique Marge N vs N-1 mensuel (nouveau)
    {
        "id": "l2",
        "type": "chart_line",
        "title": "Comparatif Marge N vs N-1 par Mois",
        "x": 0, "y": 9, "w": 8, "h": 4,
        "config": {
            "dataSourceCode": "DS_TB_CA_NvsN1_MOIS",
            "dataSourceOrigin": "template",
            "x_field": "Mois Label",
            "y_field": "Marge N",
            "y_field_2": "Marge N-1",
            "y_label": "Marge N",
            "y_label_2": "Marge N-1",
            "color": "#f59e0b",
            "color_2": "#d1d5db",
            "show_grid": True,
            "show_legend": True
        }
    },
    # Graphique Taux de marge % mensuel (nouveau)
    {
        "id": "l3",
        "type": "chart_line",
        "title": "Taux de Marge % — N vs N-1",
        "x": 8, "y": 9, "w": 4, "h": 4,
        "config": {
            "dataSourceCode": "DS_TB_CA_NvsN1_MOIS",
            "dataSourceOrigin": "template",
            "x_field": "Mois Label",
            "y_field": "Marge % N",
            "y_field_2": "Marge % N-1",
            "y_label": "Marge % N",
            "y_label_2": "Marge % N-1",
            "color": "#8b5cf6",
            "color_2": "#c4b5fd",
            "show_grid": True,
            "show_legend": True
        }
    },
    # Graphique Nb Clients mensuel (nouveau)
    {
        "id": "l4",
        "type": "chart_line",
        "title": "Clients Actifs par Mois — N vs N-1",
        "x": 0, "y": 13, "w": 6, "h": 4,
        "config": {
            "dataSourceCode": "DS_TB_CA_NvsN1_MOIS",
            "dataSourceOrigin": "template",
            "x_field": "Mois Label",
            "y_field": "Nb Clients N",
            "y_field_2": "Nb Clients N-1",
            "y_label": "Clients N",
            "y_label_2": "Clients N-1",
            "color": "#0ea5e9",
            "color_2": "#bae6fd",
            "show_grid": True,
            "show_legend": True
        }
    },
    # Graphique Nb Docs mensuel (nouveau)
    {
        "id": "l5",
        "type": "chart_line",
        "title": "Nb Documents par Mois — N vs N-1",
        "x": 6, "y": 13, "w": 6, "h": 4,
        "config": {
            "dataSourceCode": "DS_TB_CA_NvsN1_MOIS",
            "dataSourceOrigin": "template",
            "x_field": "Mois Label",
            "y_field": "Nb Docs N",
            "y_field_2": "Nb Docs N-1",
            "y_label": "Docs N",
            "y_label_2": "Docs N-1",
            "color": "#ef4444",
            "color_2": "#fca5a5",
            "show_grid": True,
            "show_legend": True
        }
    },
]

cur.execute(
    "UPDATE APP_Dashboards SET widgets = ? WHERE id = 218",
    (json.dumps(NEW_WIDGETS, ensure_ascii=False),)
)
print(f"Dashboard 218 mis a jour : {cur.rowcount} ligne(s) — {len(NEW_WIDGETS)} widgets")

conn.close()
print("\nTermine.")
