# -*- coding: utf-8 -*-
"""
Enrichit DS_COMPARATIF_ANNUEL et ajoute DS_COMPARATIF_ANNUEL_PIVOT + DS_COMPARATIF_MENSUEL.

Appel : python fix_ds_comparatif_annuel.py
Utilise les settings du backend (.env) pour la connexion.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database_unified import get_central_connection

QUERY_COMPARATIF_ANNUEL = """\
SELECT
    YEAR([Date]) AS [Annee],
    SUM([Montant HT Net]) AS [CA HT],
    SUM([Montant TTC Net]) AS [CA TTC],
    SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantit\xe9]) AS [Marge],
    CASE WHEN SUM([Montant HT Net]) > 0
        THEN ROUND(SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantit\xe9]) * 100.0 / SUM([Montant HT Net]), 2)
        ELSE 0 END AS [Marge %],
    COUNT(DISTINCT [Code client]) AS [Nb Clients],
    COUNT(DISTINCT [N\xb0 Pi\xe8ce]) AS [Nb Documents],
    COUNT(*) AS [Nb Lignes],
    SUM([Quantit\xe9]) AS [Qte Totale],
    ROUND(SUM(ISNULL([Poids net], 0)), 2) AS [Poids Net Total],
    CASE WHEN COUNT(DISTINCT [N\xb0 Pi\xe8ce]) > 0
        THEN ROUND(SUM([Montant HT Net]) / COUNT(DISTINCT [N\xb0 Pi\xe8ce]), 2)
        ELSE 0 END AS [Ticket Moyen HT],
    CASE WHEN COUNT(DISTINCT [Code client]) > 0
        THEN ROUND(SUM([Montant HT Net]) / COUNT(DISTINCT [Code client]), 2)
        ELSE 0 END AS [CA Moy par Client],
    ROUND(CAST(COUNT(*) AS FLOAT) / NULLIF(COUNT(DISTINCT [N\xb0 Pi\xe8ce]), 0), 1) AS [Lignes Moy par Doc],
    ROUND(SUM([Prix unitaire] * [Quantit\xe9]) - SUM([Montant HT Net]), 2) AS [Remise HT],
    CASE WHEN SUM([Prix unitaire] * [Quantit\xe9]) > 0
        THEN ROUND((SUM([Prix unitaire] * [Quantit\xe9]) - SUM([Montant HT Net])) * 100.0 / SUM([Prix unitaire] * [Quantit\xe9]), 2)
        ELSE 0 END AS [Taux Remise %]
FROM [Lignes_des_ventes]
WHERE [Valorise CA] = 'Oui'
  AND (@societe IS NULL OR [societe] = @societe)
  AND YEAR([Date]) IN (YEAR(@dateFin), YEAR(@dateFin) - 1)
  AND MONTH([Date]) BETWEEN MONTH(@dateDebut) AND MONTH(@dateFin)
GROUP BY YEAR([Date])
ORDER BY [Annee]"""

QUERY_COMPARATIF_PIVOT = """\
WITH Base AS (
    SELECT
        YEAR([Date]) AS annee,
        SUM([Montant HT Net])                                    AS ca_ht,
        SUM([Montant TTC Net])                                   AS ca_ttc,
        SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantit\xe9])  AS marge,
        COUNT(DISTINCT [Code client])                             AS nb_clients,
        COUNT(DISTINCT [N\xb0 Pi\xe8ce])                               AS nb_docs,
        COUNT(*)                                                  AS nb_lignes,
        SUM([Quantit\xe9])                                           AS qte_totale,
        SUM([Prix unitaire] * [Quantit\xe9])                        AS ca_brut,
        ROUND(SUM(ISNULL([Poids net], 0)), 2)                    AS poids_net
    FROM [Lignes_des_ventes]
    WHERE [Valorise CA] = 'Oui'
      AND (@societe IS NULL OR [societe] = @societe)
      AND YEAR([Date]) IN (YEAR(@dateFin), YEAR(@dateFin) - 1)
      AND MONTH([Date]) BETWEEN MONTH(@dateDebut) AND MONTH(@dateFin)
    GROUP BY YEAR([Date])
),
N  AS (SELECT * FROM Base WHERE annee = YEAR(@dateFin)),
N1 AS (SELECT * FROM Base WHERE annee = YEAR(@dateFin) - 1)
SELECT
    YEAR(@dateFin)     AS [Annee N],
    YEAR(@dateFin) - 1 AS [Annee N-1],
    ISNULL(n.ca_ht, 0)                                                          AS [CA HT N],
    ISNULL(n1.ca_ht, 0)                                                         AS [CA HT N-1],
    ROUND(ISNULL(n.ca_ht, 0) - ISNULL(n1.ca_ht, 0), 2)                         AS [Ecart CA HT],
    CASE WHEN ISNULL(n1.ca_ht, 0) > 0
         THEN ROUND((ISNULL(n.ca_ht, 0) - ISNULL(n1.ca_ht, 0)) * 100.0 / ISNULL(n1.ca_ht, 0), 2)
         ELSE NULL END                                                           AS [Evol CA %],
    ISNULL(n.ca_ttc, 0)                                                         AS [CA TTC N],
    ISNULL(n1.ca_ttc, 0)                                                        AS [CA TTC N-1],
    ISNULL(n.marge, 0)                                                          AS [Marge N],
    ISNULL(n1.marge, 0)                                                         AS [Marge N-1],
    ROUND(ISNULL(n.marge, 0) - ISNULL(n1.marge, 0), 2)                         AS [Ecart Marge],
    CASE WHEN ISNULL(n1.marge, 0) <> 0
         THEN ROUND((ISNULL(n.marge, 0) - ISNULL(n1.marge, 0)) * 100.0 / ABS(ISNULL(n1.marge, 0)), 2)
         ELSE NULL END                                                           AS [Evol Marge %],
    CASE WHEN ISNULL(n.ca_ht, 0)  > 0 THEN ROUND(ISNULL(n.marge, 0)  * 100.0 / n.ca_ht,  2) ELSE 0 END AS [Marge % N],
    CASE WHEN ISNULL(n1.ca_ht, 0) > 0 THEN ROUND(ISNULL(n1.marge, 0) * 100.0 / n1.ca_ht, 2) ELSE 0 END AS [Marge % N-1],
    CASE WHEN ISNULL(n.ca_ht, 0)  > 0 THEN ROUND(ISNULL(n.marge, 0)  * 100.0 / n.ca_ht,  2) ELSE 0 END
      - CASE WHEN ISNULL(n1.ca_ht, 0) > 0 THEN ROUND(ISNULL(n1.marge, 0) * 100.0 / n1.ca_ht, 2) ELSE 0 END AS [Ecart Marge %],
    ISNULL(n.nb_clients, 0)                                                     AS [Nb Clients N],
    ISNULL(n1.nb_clients, 0)                                                    AS [Nb Clients N-1],
    ISNULL(n.nb_clients, 0) - ISNULL(n1.nb_clients, 0)                         AS [Ecart Clients],
    CASE WHEN ISNULL(n1.nb_clients, 0) > 0
         THEN ROUND(CAST(ISNULL(n.nb_clients, 0) - ISNULL(n1.nb_clients, 0) AS FLOAT) * 100.0 / ISNULL(n1.nb_clients, 0), 2)
         ELSE NULL END                                                           AS [Evol Clients %],
    ISNULL(n.nb_docs, 0)                                                        AS [Nb Documents N],
    ISNULL(n1.nb_docs, 0)                                                       AS [Nb Documents N-1],
    ISNULL(n.nb_docs, 0) - ISNULL(n1.nb_docs, 0)                               AS [Ecart Documents],
    ISNULL(n.nb_lignes, 0)                                                      AS [Nb Lignes N],
    ISNULL(n1.nb_lignes, 0)                                                     AS [Nb Lignes N-1],
    ISNULL(n.qte_totale, 0)                                                     AS [Qte Totale N],
    ISNULL(n1.qte_totale, 0)                                                    AS [Qte Totale N-1],
    ROUND(ISNULL(n.qte_totale, 0) - ISNULL(n1.qte_totale, 0), 2)               AS [Ecart Qte],
    CASE WHEN ISNULL(n.nb_docs, 0)  > 0 THEN ROUND(ISNULL(n.ca_ht, 0)  / n.nb_docs,  2) ELSE 0 END  AS [Ticket Moyen N],
    CASE WHEN ISNULL(n1.nb_docs, 0) > 0 THEN ROUND(ISNULL(n1.ca_ht, 0) / n1.nb_docs, 2) ELSE 0 END  AS [Ticket Moyen N-1],
    CASE WHEN ISNULL(n.nb_clients, 0)  > 0 THEN ROUND(ISNULL(n.ca_ht, 0)  / n.nb_clients,  2) ELSE 0 END AS [CA Moy Client N],
    CASE WHEN ISNULL(n1.nb_clients, 0) > 0 THEN ROUND(ISNULL(n1.ca_ht, 0) / n1.nb_clients, 2) ELSE 0 END AS [CA Moy Client N-1],
    ROUND(ISNULL(n.ca_brut, 0)  - ISNULL(n.ca_ht, 0),  2)                     AS [Remise HT N],
    ROUND(ISNULL(n1.ca_brut, 0) - ISNULL(n1.ca_ht, 0), 2)                     AS [Remise HT N-1],
    CASE WHEN ISNULL(n.ca_brut, 0)  > 0
         THEN ROUND((ISNULL(n.ca_brut, 0)  - ISNULL(n.ca_ht, 0))  * 100.0 / ISNULL(n.ca_brut, 0),  2) ELSE 0 END AS [Taux Remise % N],
    CASE WHEN ISNULL(n1.ca_brut, 0) > 0
         THEN ROUND((ISNULL(n1.ca_brut, 0) - ISNULL(n1.ca_ht, 0)) * 100.0 / ISNULL(n1.ca_brut, 0), 2) ELSE 0 END AS [Taux Remise % N-1],
    ISNULL(n.poids_net,  0) AS [Poids Net N],
    ISNULL(n1.poids_net, 0) AS [Poids Net N-1]
FROM (SELECT 1 AS dummy) d
LEFT JOIN N  ON 1 = 1
LEFT JOIN N1 ON 1 = 1"""

QUERY_COMPARATIF_MENSUEL = """\
WITH Mois AS (
    SELECT
        MONTH([Date]) AS mois_num,
        CASE MONTH([Date])
            WHEN 1  THEN 'Janvier'   WHEN 2  THEN 'Fevrier'
            WHEN 3  THEN 'Mars'      WHEN 4  THEN 'Avril'
            WHEN 5  THEN 'Mai'       WHEN 6  THEN 'Juin'
            WHEN 7  THEN 'Juillet'   WHEN 8  THEN 'Aout'
            WHEN 9  THEN 'Septembre' WHEN 10 THEN 'Octobre'
            WHEN 11 THEN 'Novembre'  WHEN 12 THEN 'Decembre'
        END AS mois_label,
        SUM(CASE WHEN YEAR([Date]) = YEAR(@dateFin)     THEN [Montant HT Net] ELSE 0 END) AS ca_n,
        SUM(CASE WHEN YEAR([Date]) = YEAR(@dateFin) - 1 THEN [Montant HT Net] ELSE 0 END) AS ca_n1,
        SUM(CASE WHEN YEAR([Date]) = YEAR(@dateFin)
            THEN [Montant HT Net] - ISNULL([CMUP], 0) * [Quantit\xe9] ELSE 0 END) AS marge_n,
        SUM(CASE WHEN YEAR([Date]) = YEAR(@dateFin) - 1
            THEN [Montant HT Net] - ISNULL([CMUP], 0) * [Quantit\xe9] ELSE 0 END) AS marge_n1,
        COUNT(DISTINCT CASE WHEN YEAR([Date]) = YEAR(@dateFin)     THEN [Code client] END) AS nb_clients_n,
        COUNT(DISTINCT CASE WHEN YEAR([Date]) = YEAR(@dateFin) - 1 THEN [Code client] END) AS nb_clients_n1,
        COUNT(DISTINCT CASE WHEN YEAR([Date]) = YEAR(@dateFin)     THEN [N\xb0 Pi\xe8ce] END)    AS nb_docs_n,
        COUNT(DISTINCT CASE WHEN YEAR([Date]) = YEAR(@dateFin) - 1 THEN [N\xb0 Pi\xe8ce] END)    AS nb_docs_n1,
        SUM(CASE WHEN YEAR([Date]) = YEAR(@dateFin)     THEN [Quantit\xe9] ELSE 0 END) AS qte_n,
        SUM(CASE WHEN YEAR([Date]) = YEAR(@dateFin) - 1 THEN [Quantit\xe9] ELSE 0 END) AS qte_n1
    FROM [Lignes_des_ventes]
    WHERE [Valorise CA] = 'Oui'
      AND (@societe IS NULL OR [societe] = @societe)
      AND YEAR([Date]) IN (YEAR(@dateFin), YEAR(@dateFin) - 1)
      AND MONTH([Date]) BETWEEN MONTH(@dateDebut) AND MONTH(@dateFin)
    GROUP BY MONTH([Date])
)
SELECT
    mois_num                                                                          AS [Mois],
    mois_label                                                                        AS [Mois Label],
    YEAR(@dateFin)                                                                    AS [Annee N],
    YEAR(@dateFin) - 1                                                                AS [Annee N-1],
    ca_n                                                                              AS [CA HT N],
    ca_n1                                                                             AS [CA HT N-1],
    ROUND(ca_n - ca_n1, 2)                                                            AS [Ecart CA],
    CASE WHEN ca_n1 > 0 THEN ROUND((ca_n - ca_n1) * 100.0 / ca_n1, 2) ELSE NULL END  AS [Evol CA %],
    marge_n                                                                           AS [Marge N],
    marge_n1                                                                          AS [Marge N-1],
    ROUND(marge_n - marge_n1, 2)                                                      AS [Ecart Marge],
    CASE WHEN ca_n  > 0 THEN ROUND(marge_n  * 100.0 / ca_n,  2) ELSE 0 END           AS [Marge % N],
    CASE WHEN ca_n1 > 0 THEN ROUND(marge_n1 * 100.0 / ca_n1, 2) ELSE 0 END           AS [Marge % N-1],
    nb_clients_n                                                                      AS [Nb Clients N],
    nb_clients_n1                                                                     AS [Nb Clients N-1],
    nb_clients_n - nb_clients_n1                                                      AS [Ecart Clients],
    nb_docs_n                                                                         AS [Nb Documents N],
    nb_docs_n1                                                                        AS [Nb Documents N-1],
    nb_docs_n - nb_docs_n1                                                            AS [Ecart Documents],
    qte_n                                                                             AS [Qte N],
    qte_n1                                                                            AS [Qte N-1],
    ROUND(qte_n - qte_n1, 2)                                                          AS [Ecart Qte],
    CASE WHEN nb_docs_n  > 0 THEN ROUND(ca_n  / nb_docs_n,  2) ELSE 0 END            AS [Ticket Moyen N],
    CASE WHEN nb_docs_n1 > 0 THEN ROUND(ca_n1 / nb_docs_n1, 2) ELSE 0 END            AS [Ticket Moyen N-1],
    CASE WHEN nb_clients_n  > 0 THEN ROUND(ca_n  / nb_clients_n,  2) ELSE 0 END      AS [CA Moy Client N],
    CASE WHEN nb_clients_n1 > 0 THEN ROUND(ca_n1 / nb_clients_n1, 2) ELSE 0 END      AS [CA Moy Client N-1]
FROM Mois
ORDER BY mois_num"""

PARAMS_STD = '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'

UPDATES = [
    {
        "code": "DS_COMPARATIF_ANNUEL",
        "nom": "Comparatif Annuel N/N-1",
        "description": "Comparaison du CA, marge, volume, ticket moyen et remise entre l'annee en cours et l'annee precedente (2 lignes)",
        "query": QUERY_COMPARATIF_ANNUEL,
        "params": PARAMS_STD,
    },
]

INSERTS = [
    {
        "code": "DS_COMPARATIF_ANNUEL_PIVOT",
        "nom": "Comparatif Annuel Pivot N/N-1",
        "category": "Tableau de Bord",
        "description": "Tous les KPIs N vs N-1 sur une seule ligne avec ecarts et evolutions",
        "query": QUERY_COMPARATIF_PIVOT,
    },
    {
        "code": "DS_COMPARATIF_MENSUEL",
        "nom": "Comparatif Mensuel N/N-1",
        "category": "Tableau de Bord",
        "description": "Comparaison mois par mois N vs N-1 : CA, marge, clients, documents, ticket moyen",
        "query": QUERY_COMPARATIF_MENSUEL,
    },
]


def run():
    conn = get_central_connection()
    conn.autocommit = True
    cur = conn.cursor()

    for u in UPDATES:
        cur.execute(
            "UPDATE APP_DataSources_Templates SET nom=?, description=?, query_template=?, parameters=? WHERE code=?",
            (u["nom"], u["description"], u["query"], u.get("params", PARAMS_STD), u["code"])
        )
        print(f"UPDATE {u['code']} -> {cur.rowcount} ligne(s)")

    for ins in INSERTS:
        cur.execute("SELECT COUNT(*) FROM APP_DataSources_Templates WHERE code=?", (ins["code"],))
        exists = cur.fetchone()[0]
        if exists:
            cur.execute(
                "UPDATE APP_DataSources_Templates SET nom=?, description=?, query_template=?, parameters=? WHERE code=?",
                (ins["nom"], ins["description"], ins["query"], PARAMS_STD, ins["code"])
            )
            print(f"UPDATE (exists) {ins['code']} -> {cur.rowcount} ligne(s)")
        else:
            cur.execute(
                """INSERT INTO APP_DataSources_Templates
                   (code, nom, type, category, description, query_template, parameters, is_system, actif, date_creation)
                   VALUES (?, ?, 'query', ?, ?, ?, ?, 0, 1, GETDATE())""",
                (ins["code"], ins["nom"], ins["category"], ins["description"], ins["query"], PARAMS_STD)
            )
            print(f"INSERT {ins['code']} -> OK")

    conn.close()
    print("\nTermine.")


if __name__ == "__main__":
    run()
