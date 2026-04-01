"""
Service d'introspection du schema pour le module IA.
Fournit un schema simplifie, lisible par les LLM, des tables disponibles.
Les tables sont dans la base DWH de chaque client, accessible via execute_dwh_query.
Connexion directe au DWH : les noms de tables sont SANS prefixe de base de donnees.
"""
from typing import Dict, List, Optional
from ..database_unified import execute_dwh_query
import logging

logger = logging.getLogger(__name__)

# Tables autorisees pour l'IA (lecture seule)
# Ces tables existent directement dans chaque base DWH client
AUTHORIZED_TABLES = [
    "Lignes_des_ventes",    # Detail des ventes (CA, clients, articles)
    "Mouvement_stock",       # Mouvements de stock entrees/sorties
    "Etat_Stock",            # Etat du stock par article et depot
    "Echéances_Ventes",      # Echeances de paiement des ventes clients (si disponible)
]

# Descriptions metier detaillees pour guider le LLM (colonnes cles + formules + regles)
TABLE_DESCRIPTIONS = {
    "Lignes_des_ventes": (
        "Detail des lignes de ventes (factures, BL, avoirs). "
        "Colonnes cles: [Date] (date du document, type date — UTILISER POUR FILTRER PAR PERIODE), "
        "[Montant HT Net] (CA hors taxe), [Montant TTC Net] (CA TTC), "
        "[Prix de revient] (cout unitaire), [Quantité] (quantite vendue), "
        "[Code client], [Intitulé client], [Code article], [Désignation ligne], "
        "[N° Pièce] (numero de document), [Type Document] (Facture, BL, Avoir...), "
        "[Valorise CA] (varchar 'Oui'/'Non' — indique si la ligne compte dans le CA), "
        "[Catalogue 1] (gamme/famille produit), [Catalogue 2], [Gamme 1], [Gamme 2], "
        "[societe], [Code collaborateur], [Nom collaborateur], [Prénom collaborateur]. "
        "FORMULE MARGE: [Montant HT Net] - [Prix de revient] * [Quantité]. "
        "FORMULE TAUX MARGE: ROUND(SUM([Montant HT Net] - [Prix de revient] * [Quantité]) * 100.0 / NULLIF(SUM([Montant HT Net]), 0), 2). "
        "REGLE CA OBLIGATOIRE: TOUJOURS filtrer WHERE [Valorise CA] = 'Oui' pour tout calcul de CA/ventes/revenus. "
        "REGLE DATE: Utiliser [Date] (PAS [Date BL]) pour filtrer par periode. Ex: [Date] BETWEEN '2025-01-01' AND '2025-12-31'. "
        "FONCTIONS DATE UTILES: GETDATE() (aujourd'hui), DATEADD(MONTH, -1, GETDATE()), YEAR([Date]), MONTH([Date]), FORMAT([Date], 'yyyy-MM')."
    ),
    "Mouvement_stock": (
        "Mouvements de stock: entrees et sorties par article et depot. "
        "Colonnes cles: [Code article], [Référence], [Désignation], [Intitulé famille], "
        "[Date Mouvement] (date du mouvement), [Type Mouvement], "
        "[Sens de mouvement] (varchar 'Entrée' ou 'Sortie'), "
        "[Quantité], [CMUP] (cout moyen unitaire pondere), "
        "[Prix unitaire], [Prix de revient], [Montant Stock], "
        "[Code Dépôt], [Dépôt], [N° Pièce], [Domaine mouvement], [societe]. "
        "FORMULE STOCK CALCULE: SUM(CASE WHEN [Sens de mouvement] = 'Entrée' THEN [Quantité] ELSE -[Quantité] END). "
        "FORMULE VALEUR STOCK: stock_qte * [CMUP]. "
        "STOCK DORMANT: articles ou DATEDIFF(DAY, MAX([Date Mouvement]), GETDATE()) > 180 avec stock > 0."
    ),
    "Etat_Stock": (
        "Etat/photo du stock actuel par article et depot (pas d'historique). "
        "Colonnes cles: [Code article], [Désignation article], "
        "[Code dépôt], [Quantité en stock], [Valeur du stock (montant)], "
        "[Quantité minimale] (seuil min), [Quantité maximale] (seuil max), [societe]. "
        "RUPTURE DE STOCK: [Quantité en stock] <= 0 ou [Quantité en stock] < [Quantité minimale]. "
        "SURSTOCK: [Quantité en stock] > [Quantité maximale]."
    ),
    "Echéances_Ventes": (
        "Echeances de paiement des ventes clients (recouvrement/creances). "
        "Colonnes cles: [Code client], [Intitulé client], "
        "[Date d'échéance] (date echeance), [Date document], "
        "[Montant échéance] (montant initial de l'echeance), "
        "[Montant du règlement] (montant deja regle, peut etre NULL ou absent — verifier dans le schema), "
        "[Mode de réglement], [Code mode règlement], "
        "[N° Pièce], [Type Document], [societe]. "
        "IMPORTANT: Verifier les colonnes exactes dans le schema ci-dessus avant d'ecrire le SQL. "
        "Si la colonne [Régler] n'existe pas, utiliser [Montant du règlement]. "
        "FORMULE RESTE A REGLER: [Montant échéance] - ISNULL([Montant du règlement], 0). "
        "FILTRE CREANCES OUVERTES: WHERE [Montant échéance] > ISNULL([Montant du règlement], 0). "
        "JOURS DE RETARD: DATEDIFF(DAY, [Date d'échéance], GETDATE()). "
        "BALANCE AGEE (tranches): "
        "Non echu = DATEDIFF <= 0, "
        "0-30j = BETWEEN 1 AND 30, "
        "31-60j = BETWEEN 31 AND 60, "
        "61-90j = BETWEEN 61 AND 90, "
        "91-120j = BETWEEN 91 AND 120, "
        "+120j = > 120."
    ),
}


def get_schema_for_ai(dwh_code: str) -> str:
    """
    Retourne un schema textuel des tables autorisees pour les prompts IA.
    Format optimise pour les LLM (texte concis).
    Les tables sont dans la base DWH (connexion directe), sans prefixe de base.
    """
    schema_lines = [
        "=== SCHEMA BASE DE DONNEES (DWH CLIENT) ===",
        "Seules les tables suivantes sont disponibles (acces lecture seule).",
        "IMPORTANT: Les noms de tables sont SANS prefixe de base de donnees.",
        "Utilise directement le nom de la table (ex: FROM Lignes_des_ventes)",
        ""
    ]

    for table_name in AUTHORIZED_TABLES:
        description = TABLE_DESCRIPTIONS.get(table_name, "")
        columns = _get_table_columns(table_name, dwh_code)
        if not columns:
            # Table non disponible dans ce DWH, on la saute
            continue
        schema_lines.append(f"TABLE: {table_name}")
        schema_lines.append(f"  Description: {description}")
        col_list = ", ".join(
            [f"[{c['name']}] ({c['type']})" for c in columns[:35]]
        )
        schema_lines.append(f"  Colonnes: {col_list}")
        schema_lines.append("")

    schema_lines.append(
        "RAPPEL: Dans tes requetes SQL, utilise UNIQUEMENT le nom de la table "
        "SANS prefixe (ex: FROM Lignes_des_ventes, FROM Mouvement_stock). "
        "PAS de [BASE].[dbo].[Table].\n"
        "REGLE CA OBLIGATOIRE: Pour toute question sur le chiffre d'affaires, "
        "ventes, revenus ou CA, TOUJOURS ajouter WHERE [Valorise CA] = 'Oui' "
        "dans la requete sur Lignes_des_ventes. "
        "Ne PAS utiliser [Type Document] IN ('Facture', 'BL') comme substitut du CA."
    )

    return "\n".join(schema_lines)


def _get_table_columns(table_name: str, dwh_code: str) -> List[Dict]:
    """Recupere les colonnes d'une table via INFORMATION_SCHEMA sur le DWH."""
    try:
        query = """
            SELECT COLUMN_NAME as name, DATA_TYPE as type
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = ?
            ORDER BY ORDINAL_POSITION
        """
        results = execute_dwh_query(dwh_code, query, (table_name,), use_cache=True, cache_ttl=3600)
        return results
    except Exception as e:
        logger.warning(f"Schema introspection failed for {table_name} (DWH: {dwh_code}): {e}")
        return []


def get_business_context() -> str:
    """Retourne le contexte metier general pour les prompts systeme."""
    return (
        "Vous etes un assistant analytique pour OptiBoard, "
        "une plateforme de reporting commercial.\n"
        "L'application gere les donnees de ventes, stocks et recouvrement "
        "pour des societes du groupe.\n"
        "Monnaie: Dirham marocain (DH). Langue: Francais.\n"
        "Les dates sont au format YYYY-MM-DD dans la base de donnees.\n"
        "Les chiffres de CA sont en DH HT (hors taxe).\n"
        "Le DSO (Days Sales Outstanding) mesure le delai moyen de paiement clients.\n"
        "Utilisez le format SQL Server (T-SQL) pour les requetes.\n"
        "IMPORTANT: Les tables de donnees sont dans la base DWH du client. "
        "Utilisez les noms de tables SANS prefixe de base de donnees "
        "(ex: FROM Lignes_des_ventes, jamais FROM [BASE].[dbo].[Lignes_des_ventes])."
    )


def get_sql_examples() -> str:
    """
    Retourne des exemples SQL eprouves en production pour guider le LLM.
    Ces exemples utilisent les bons noms de colonnes, formules et filtres.
    Le LLM doit s'en inspirer pour generer des requetes fiables.
    """
    return """
=== EXEMPLES SQL DE REFERENCE (a adapter selon la question) ===

--- Exemple 1: CA global d'une periode ---
Question: "Quel est le CA du mois en cours ?"
SQL:
SELECT
    SUM([Montant HT Net]) AS [CA HT],
    SUM([Montant TTC Net]) AS [CA TTC],
    COUNT(DISTINCT [Code client]) AS [Nb Clients],
    COUNT(DISTINCT [N° Pièce]) AS [Nb Documents]
FROM Lignes_des_ventes
WHERE [Valorise CA] = 'Oui'
  AND [Date] >= DATEADD(MONTH, DATEDIFF(MONTH, 0, GETDATE()), 0)
  AND [Date] < DATEADD(MONTH, DATEDIFF(MONTH, 0, GETDATE()) + 1, 0)

--- Exemple 2: Top N clients par CA ---
Question: "Top 10 clients par chiffre d'affaires cette annee"
SQL:
SELECT TOP 10
    [Code client],
    [Intitulé client] AS [Client],
    SUM([Montant HT Net]) AS [CA HT],
    SUM([Montant HT Net] - [Prix de revient] * [Quantité]) AS [Marge],
    CASE WHEN SUM([Montant HT Net]) > 0
        THEN ROUND(SUM([Montant HT Net] - [Prix de revient] * [Quantité]) * 100.0 / SUM([Montant HT Net]), 2)
        ELSE 0 END AS [Taux Marge %],
    COUNT(DISTINCT [N° Pièce]) AS [Nb Factures]
FROM Lignes_des_ventes
WHERE [Valorise CA] = 'Oui'
  AND YEAR([Date]) = YEAR(GETDATE())
GROUP BY [Code client], [Intitulé client]
ORDER BY [CA HT] DESC

--- Exemple 3: CA par mois (evolution mensuelle) ---
Question: "Evolution du CA sur les 6 derniers mois"
SQL:
SELECT
    FORMAT([Date], 'yyyy-MM') AS [Periode],
    SUM([Montant HT Net]) AS [CA HT],
    SUM([Montant HT Net] - [Prix de revient] * [Quantité]) AS [Marge],
    COUNT(DISTINCT [Code client]) AS [Nb Clients]
FROM Lignes_des_ventes
WHERE [Valorise CA] = 'Oui'
  AND [Date] >= DATEADD(MONTH, -6, DATEADD(MONTH, DATEDIFF(MONTH, 0, GETDATE()), 0))
  AND [Date] < DATEADD(MONTH, DATEDIFF(MONTH, 0, GETDATE()) + 1, 0)
GROUP BY FORMAT([Date], 'yyyy-MM')
ORDER BY [Periode]

--- Exemple 4: CA par article avec marge ---
Question: "Articles les plus vendus avec marge"
SQL:
SELECT TOP 20
    [Code article],
    [Désignation ligne] AS [Designation],
    [Catalogue 1] AS [Catalogue],
    SUM([Quantité]) AS [Qte Vendue],
    SUM([Montant HT Net]) AS [CA HT],
    SUM([Montant HT Net] - [Prix de revient] * [Quantité]) AS [Marge],
    CASE WHEN SUM([Montant HT Net]) > 0
        THEN ROUND(SUM([Montant HT Net] - [Prix de revient] * [Quantité]) * 100.0 / SUM([Montant HT Net]), 2)
        ELSE 0 END AS [Taux Marge %]
FROM Lignes_des_ventes
WHERE [Valorise CA] = 'Oui'
  AND YEAR([Date]) = YEAR(GETDATE())
GROUP BY [Code article], [Désignation ligne], [Catalogue 1]
ORDER BY [CA HT] DESC

--- Exemple 5: Stock dormant (CTE) ---
Question: "Articles en stock dormant (sans mouvement depuis 180 jours)"
SQL:
WITH DernierMvt AS (
    SELECT
        [Code article],
        [Référence],
        [Désignation],
        [Intitulé famille],
        [societe],
        MAX([Date Mouvement]) AS dernier_mvt,
        SUM(CASE WHEN [Sens de mouvement] = 'Entrée' THEN [Quantité] ELSE -[Quantité] END) AS stock_qte,
        MAX([CMUP]) AS cmup
    FROM Mouvement_stock
    GROUP BY [Code article], [Référence], [Désignation], [Intitulé famille], [societe]
)
SELECT TOP 50
    [Code article],
    [Désignation],
    [Intitulé famille] AS [Famille],
    stock_qte AS [Stock Qte],
    cmup AS [CMUP],
    stock_qte * cmup AS [Valeur Stock],
    dernier_mvt AS [Dernier Mouvement],
    DATEDIFF(DAY, dernier_mvt, GETDATE()) AS [Jours Sans Mvt]
FROM DernierMvt
WHERE stock_qte > 0
  AND DATEDIFF(DAY, dernier_mvt, GETDATE()) > 180
ORDER BY stock_qte * cmup DESC

--- Exemple 6: Etat du stock par depot ---
Question: "Etat du stock par depot"
SQL:
SELECT
    [Code dépôt] AS [Depot],
    COUNT(DISTINCT [Code article]) AS [Nb Articles],
    SUM([Quantité en stock]) AS [Qte Totale],
    SUM([Valeur du stock (montant)]) AS [Valeur Totale],
    SUM(CASE WHEN [Quantité en stock] <= 0 THEN 1 ELSE 0 END) AS [Nb En Rupture]
FROM Etat_Stock
GROUP BY [Code dépôt]
ORDER BY [Valeur Totale] DESC

--- Exemple 7: Creances non reglees ---
Question: "Creances non reglees avec retard"
Note: Utiliser [Montant du règlement] si [Régler] n'existe pas dans le schema.
SQL:
SELECT TOP 50
    [Code client],
    [Intitulé client] AS [Client],
    [N° Pièce] AS [Piece],
    [Date d'échéance] AS [Echeance],
    [Montant échéance] AS [Montant],
    ISNULL([Montant du règlement], 0) AS [Regle],
    [Montant échéance] - ISNULL([Montant du règlement], 0) AS [Reste A Regler],
    DATEDIFF(DAY, [Date d'échéance], GETDATE()) AS [Jours Retard],
    [Mode de réglement] AS [Mode Reglement]
FROM Echéances_Ventes
WHERE [Montant échéance] > ISNULL([Montant du règlement], 0)
ORDER BY [Montant échéance] - ISNULL([Montant du règlement], 0) DESC

--- Exemple 8: Balance agee par client ---
Question: "Balance agee des creances par client"
Note: Utiliser [Montant du règlement] si [Régler] n'existe pas dans le schema.
SQL:
SELECT
    [Code client],
    [Intitulé client] AS [Client],
    SUM(CASE WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) <= 0
        THEN [Montant échéance] - ISNULL([Montant du règlement], 0) ELSE 0 END) AS [Non Echu],
    SUM(CASE WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) BETWEEN 1 AND 30
        THEN [Montant échéance] - ISNULL([Montant du règlement], 0) ELSE 0 END) AS [0-30j],
    SUM(CASE WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) BETWEEN 31 AND 60
        THEN [Montant échéance] - ISNULL([Montant du règlement], 0) ELSE 0 END) AS [31-60j],
    SUM(CASE WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) BETWEEN 61 AND 90
        THEN [Montant échéance] - ISNULL([Montant du règlement], 0) ELSE 0 END) AS [61-90j],
    SUM(CASE WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) > 90
        THEN [Montant échéance] - ISNULL([Montant du règlement], 0) ELSE 0 END) AS [+90j],
    SUM([Montant échéance] - ISNULL([Montant du règlement], 0)) AS [Total Creance]
FROM Echéances_Ventes
WHERE [Montant échéance] > ISNULL([Montant du règlement], 0)
GROUP BY [Code client], [Intitulé client]
ORDER BY [Total Creance] DESC

--- Exemple 9: Comparaison CA annee N vs N-1 (CTE) ---
Question: "Comparer le CA par client entre cette annee et l'annee derniere"
SQL:
WITH CA_N AS (
    SELECT [Code client], [Intitulé client],
           SUM([Montant HT Net]) AS [CA_Annee_N]
    FROM Lignes_des_ventes
    WHERE [Valorise CA] = 'Oui' AND YEAR([Date]) = YEAR(GETDATE())
    GROUP BY [Code client], [Intitulé client]
),
CA_N1 AS (
    SELECT [Code client],
           SUM([Montant HT Net]) AS [CA_Annee_N1]
    FROM Lignes_des_ventes
    WHERE [Valorise CA] = 'Oui' AND YEAR([Date]) = YEAR(GETDATE()) - 1
    GROUP BY [Code client]
)
SELECT TOP 20
    n.[Code client],
    n.[Intitulé client] AS [Client],
    ISNULL(n.[CA_Annee_N], 0) AS [CA Annee N],
    ISNULL(n1.[CA_Annee_N1], 0) AS [CA Annee N-1],
    ISNULL(n.[CA_Annee_N], 0) - ISNULL(n1.[CA_Annee_N1], 0) AS [Ecart],
    CASE WHEN ISNULL(n1.[CA_Annee_N1], 0) > 0
        THEN ROUND((ISNULL(n.[CA_Annee_N], 0) - n1.[CA_Annee_N1]) * 100.0 / n1.[CA_Annee_N1], 2)
        ELSE NULL END AS [Evolution %]
FROM CA_N n
LEFT JOIN CA_N1 n1 ON n.[Code client] = n1.[Code client]
ORDER BY [CA Annee N] DESC

--- Exemple 10: Marge par catalogue/famille ---
Question: "Marge par catalogue de produits"
SQL:
SELECT
    [Catalogue 1] AS [Catalogue],
    COUNT(DISTINCT [Code article]) AS [Nb Articles],
    SUM([Quantité]) AS [Qte Vendue],
    SUM([Montant HT Net]) AS [CA HT],
    SUM([Montant HT Net] - [Prix de revient] * [Quantité]) AS [Marge],
    CASE WHEN SUM([Montant HT Net]) > 0
        THEN ROUND(SUM([Montant HT Net] - [Prix de revient] * [Quantité]) * 100.0 / SUM([Montant HT Net]), 2)
        ELSE 0 END AS [Taux Marge %]
FROM Lignes_des_ventes
WHERE [Valorise CA] = 'Oui'
  AND YEAR([Date]) = YEAR(GETDATE())
GROUP BY [Catalogue 1]
ORDER BY [CA HT] DESC

=== FIN DES EXEMPLES ===
"""


def get_dynamic_examples(question: str, dwh_code: str = None) -> str:
    """
    Retourne des exemples SQL dynamiques depuis la Query Library,
    basés sur la similarité textuelle avec la question posée (RAG).
    """
    try:
        from .ai_query_library import find_similar_queries
        similar = find_similar_queries(question, dwh_code, top_k=3, min_score=0.15)
        if not similar:
            return ""
        lines = ["\n=== BASE DE CONNAISSANCE VALIDEE (exemples prioritaires) ==="]
        for i, entry in enumerate(similar, 1):
            lines.append(f"\n--- Exemple validé {i} (pertinence: {entry['score']:.0%}, utilisé {entry['success_count']}x) ---")
            lines.append(f"Question: \"{entry['question_text']}\"")
            lines.append(f"SQL validé:\n{entry['sql_query']}")
        lines.append("\n=== FIN BASE DE CONNAISSANCE ===\n")
        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"Dynamic examples failed: {e}")
        return ""
