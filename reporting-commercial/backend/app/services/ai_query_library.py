"""
Service de Query Library pour l'apprentissage de l'agent IA.
Stocke les requêtes validées et effectue une recherche par similarité textuelle.
"""
import re
import logging
from typing import List, Dict, Optional
from ..database_unified import execute_central, write_central, central_cursor

logger = logging.getLogger(__name__)

_CREATE_TABLE_SQL = """
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_AI_QueryLibrary' AND xtype='U')
CREATE TABLE APP_AI_QueryLibrary (
    id INT IDENTITY(1,1) PRIMARY KEY,
    question_text NVARCHAR(1000) NOT NULL,
    sql_query NVARCHAR(MAX) NOT NULL,
    dwh_code VARCHAR(100) NULL,
    validated_by VARCHAR(200) NULL,
    is_validated BIT NOT NULL DEFAULT 1,
    success_count INT NOT NULL DEFAULT 1,
    feedback_positive INT NOT NULL DEFAULT 0,
    feedback_negative INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT GETDATE(),
    updated_at DATETIME NOT NULL DEFAULT GETDATE()
)
"""


def init_query_library_table():
    """Crée la table APP_AI_QueryLibrary si elle n'existe pas."""
    try:
        with central_cursor() as cursor:
            cursor.execute(_CREATE_TABLE_SQL)
        logger.info("APP_AI_QueryLibrary table ready")
    except Exception as e:
        logger.error(f"Failed to init APP_AI_QueryLibrary: {e}")


_FR_STOPWORDS = {
    'quel', 'quelle', 'quels', 'quelles', 'est', 'sont', 'les', 'des',
    'par', 'sur', 'avec', 'pour', 'dans', 'une', 'qui', 'que', 'quoi',
    'tout', 'tous', 'cette', 'ces', 'moi', 'toi', 'lui', 'leur', 'leurs',
    'mon', 'ton', 'son', 'nos', 'vos', 'ses', 'mes', 'tes', 'aux', 'mais',
    'avez', 'avoir', 'etes', 'fait', 'faire', 'donne', 'donner', 'aussi',
    'comme', 'plus', 'moins', 'tres', 'bien', 'mal', 'non', 'oui', 'pas',
    'entre', 'depuis', 'pendant', 'avant', 'apres', 'sous', 'hors',
    'show', 'give', 'get', 'list', 'find', 'top', 'all',
}

def _tokenize(text: str) -> set:
    """Tokenise un texte en mots-clés (lowercase, min 3 chars, sans stopwords FR)."""
    tokens = set(re.findall(r'\b\w{3,}\b', text.lower()))
    return tokens - _FR_STOPWORDS


def _similarity_score(q1: str, q2: str) -> float:
    """Jaccard similarity entre deux textes."""
    t1 = _tokenize(q1)
    t2 = _tokenize(q2)
    if not t1 or not t2:
        return 0.0
    intersection = len(t1 & t2)
    union = len(t1 | t2)
    return intersection / union if union > 0 else 0.0


def add_to_library(
    question_text: str,
    sql_query: str,
    dwh_code: str = None,
    validated_by: str = None,
    is_validated: bool = True
) -> Optional[int]:
    """Ajoute une requête à la library. Retourne l'id inséré ou None."""
    try:
        existing = execute_central(
            "SELECT id FROM APP_AI_QueryLibrary WHERE question_text = ?",
            (question_text,), use_cache=False
        )
        if existing:
            write_central(
                "UPDATE APP_AI_QueryLibrary SET success_count = success_count + 1, updated_at = GETDATE() WHERE id = ?",
                (existing[0]['id'],)
            )
            return existing[0]['id']

        with central_cursor() as cursor:
            cursor.execute(
                """INSERT INTO APP_AI_QueryLibrary (question_text, sql_query, dwh_code, validated_by, is_validated)
                   OUTPUT INSERTED.id
                   VALUES (?, ?, ?, ?, ?)""",
                (question_text, sql_query, dwh_code, validated_by, 1 if is_validated else 0)
            )
            row = cursor.fetchone()
            return row[0] if row else None
    except Exception as e:
        logger.error(f"Failed to add to query library: {e}")
        return None


def record_feedback(
    question_text: str,
    sql_query: str,
    rating: str,
    dwh_code: str = None,
    user_id: int = None
) -> bool:
    """Enregistre un feedback utilisateur (positive/negative)."""
    try:
        existing = execute_central(
            "SELECT id FROM APP_AI_QueryLibrary WHERE question_text = ?",
            (question_text,), use_cache=False
        )
        if rating == 'positive':
            if existing:
                write_central(
                    """UPDATE APP_AI_QueryLibrary
                       SET feedback_positive = feedback_positive + 1,
                           success_count = success_count + 1,
                           is_validated = 1,
                           updated_at = GETDATE()
                       WHERE id = ?""",
                    (existing[0]['id'],)
                )
            else:
                add_to_library(
                    question_text, sql_query, dwh_code,
                    f"user_{user_id}" if user_id else "user_feedback", True
                )
        else:  # negative
            if existing:
                write_central(
                    """UPDATE APP_AI_QueryLibrary
                       SET feedback_negative = feedback_negative + 1,
                           updated_at = GETDATE()
                       WHERE id = ?""",
                    (existing[0]['id'],)
                )
        return True
    except Exception as e:
        logger.error(f"Failed to record feedback: {e}")
        return False


def find_similar_queries(
    question: str,
    dwh_code: str = None,
    top_k: int = 3,
    min_score: float = 0.15
) -> List[Dict]:
    """Trouve les requêtes les plus similaires (RAG)."""
    try:
        rows = execute_central(
            """SELECT question_text, sql_query, success_count, feedback_positive
               FROM APP_AI_QueryLibrary
               WHERE is_validated = 1
               ORDER BY success_count DESC, feedback_positive DESC""",
            use_cache=True, cache_ttl=60
        )
        scored = []
        for row in rows:
            score = _similarity_score(question, row['question_text'])
            if score >= min_score:
                scored.append({
                    'question_text': row['question_text'],
                    'sql_query': row['sql_query'],
                    'success_count': row['success_count'],
                    'score': round(score, 2)
                })
        scored.sort(key=lambda x: (-x['score'], -x['success_count']))
        return scored[:top_k]
    except Exception as e:
        logger.warning(f"Failed to find similar queries: {e}")
        return []


def get_library(limit: int = 200) -> List[Dict]:
    """Retourne toutes les entrées de la library."""
    try:
        return execute_central(
            f"""SELECT TOP ({limit}) id, question_text, sql_query, dwh_code, validated_by,
                   is_validated, success_count, feedback_positive, feedback_negative,
                   created_at, updated_at
               FROM APP_AI_QueryLibrary
               ORDER BY success_count DESC, created_at DESC""",
            use_cache=False
        )
    except Exception as e:
        logger.error(f"Failed to get library: {e}")
        return []


def validate_library_entry(entry_id: int, validated_by: str = None) -> bool:
    try:
        write_central(
            "UPDATE APP_AI_QueryLibrary SET is_validated = 1, validated_by = ?, updated_at = GETDATE() WHERE id = ?",
            (validated_by, entry_id)
        )
        return True
    except Exception as e:
        logger.error(f"Failed to validate entry {entry_id}: {e}")
        return False


def reject_library_entry(entry_id: int) -> bool:
    try:
        write_central(
            "UPDATE APP_AI_QueryLibrary SET is_validated = 0, updated_at = GETDATE() WHERE id = ?",
            (entry_id,)
        )
        return True
    except Exception as e:
        logger.error(f"Failed to reject entry {entry_id}: {e}")
        return False


def delete_library_entry(entry_id: int) -> bool:
    try:
        write_central("DELETE FROM APP_AI_QueryLibrary WHERE id = ?", (entry_id,))
        return True
    except Exception as e:
        logger.error(f"Failed to delete entry {entry_id}: {e}")
        return False


def update_library_entry(
    entry_id: int,
    question_text: str = None,
    sql_query: str = None
) -> bool:
    try:
        updates, params = [], []
        if question_text:
            updates.append("question_text = ?")
            params.append(question_text)
        if sql_query:
            updates.append("sql_query = ?")
            params.append(sql_query)
        if not updates:
            return False
        updates.append("updated_at = GETDATE()")
        params.append(entry_id)
        write_central(
            f"UPDATE APP_AI_QueryLibrary SET {', '.join(updates)} WHERE id = ?",
            tuple(params)
        )
        return True
    except Exception as e:
        logger.error(f"Failed to update entry {entry_id}: {e}")
        return False


# ── Exemples de seed (15 requêtes de référence) ─────────────────────────────

_SEED_EXAMPLES = [
    (
        "Quel est le CA du mois en cours ?",
        """SELECT
    SUM([Montant HT Net]) AS [CA HT],
    SUM([Montant TTC Net]) AS [CA TTC],
    COUNT(DISTINCT [Code client]) AS [Nb Clients],
    COUNT(DISTINCT [N° Pièce]) AS [Nb Documents]
FROM Lignes_des_ventes
WHERE [Valorise CA] = 'Oui'
  AND [Date] >= DATEADD(MONTH, DATEDIFF(MONTH, 0, GETDATE()), 0)
  AND [Date] < DATEADD(MONTH, DATEDIFF(MONTH, 0, GETDATE()) + 1, 0)"""
    ),
    (
        "Top 10 clients par chiffre d'affaires cette année",
        """SELECT TOP 10
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
ORDER BY [CA HT] DESC"""
    ),
    (
        "Evolution du CA sur les 6 derniers mois",
        """SELECT
    FORMAT([Date], 'yyyy-MM') AS [Periode],
    SUM([Montant HT Net]) AS [CA HT],
    SUM([Montant HT Net] - [Prix de revient] * [Quantité]) AS [Marge],
    COUNT(DISTINCT [Code client]) AS [Nb Clients]
FROM Lignes_des_ventes
WHERE [Valorise CA] = 'Oui'
  AND [Date] >= DATEADD(MONTH, -6, DATEADD(MONTH, DATEDIFF(MONTH, 0, GETDATE()), 0))
  AND [Date] < DATEADD(MONTH, DATEDIFF(MONTH, 0, GETDATE()) + 1, 0)
GROUP BY FORMAT([Date], 'yyyy-MM')
ORDER BY [Periode]"""
    ),
    (
        "Articles les plus vendus avec marge",
        """SELECT TOP 20
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
ORDER BY [CA HT] DESC"""
    ),
    (
        "Articles en stock dormant sans mouvement depuis 180 jours",
        """WITH DernierMvt AS (
    SELECT
        [Code article], [Référence], [Désignation], [Intitulé famille], [societe],
        MAX([Date Mouvement]) AS dernier_mvt,
        SUM(CASE WHEN [Sens de mouvement] = 'Entrée' THEN [Quantité] ELSE -[Quantité] END) AS stock_qte,
        MAX([CMUP]) AS cmup
    FROM Mouvement_stock
    GROUP BY [Code article], [Référence], [Désignation], [Intitulé famille], [societe]
)
SELECT TOP 50
    [Code article], [Désignation], [Intitulé famille] AS [Famille],
    stock_qte AS [Stock Qte], cmup AS [CMUP],
    stock_qte * cmup AS [Valeur Stock],
    dernier_mvt AS [Dernier Mouvement],
    DATEDIFF(DAY, dernier_mvt, GETDATE()) AS [Jours Sans Mvt]
FROM DernierMvt
WHERE stock_qte > 0
  AND DATEDIFF(DAY, dernier_mvt, GETDATE()) > 180
ORDER BY stock_qte * cmup DESC"""
    ),
    (
        "Etat du stock par dépôt",
        """SELECT
    [Code dépôt] AS [Depot],
    COUNT(DISTINCT [Code article]) AS [Nb Articles],
    SUM([Quantité en stock]) AS [Qte Totale],
    SUM([Valeur du stock (montant)]) AS [Valeur Totale],
    SUM(CASE WHEN [Quantité en stock] <= 0 THEN 1 ELSE 0 END) AS [Nb En Rupture]
FROM Etat_Stock
GROUP BY [Code dépôt]
ORDER BY [Valeur Totale] DESC"""
    ),
    (
        "Créances non réglées avec retard de paiement",
        """SELECT TOP 50
    [Code client], [Intitulé client] AS [Client],
    [N° Pièce] AS [Piece],
    [Date d'échéance] AS [Echeance],
    [Montant échéance] AS [Montant],
    ISNULL([Montant du règlement], 0) AS [Regle],
    [Montant échéance] - ISNULL([Montant du règlement], 0) AS [Reste A Regler],
    DATEDIFF(DAY, [Date d'échéance], GETDATE()) AS [Jours Retard]
FROM Echéances_Ventes
WHERE [Montant échéance] > ISNULL([Montant du règlement], 0)
ORDER BY [Montant échéance] - ISNULL([Montant du règlement], 0) DESC"""
    ),
    (
        "Balance âgée des créances par client",
        """SELECT
    [Code client], [Intitulé client] AS [Client],
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
ORDER BY [Total Creance] DESC"""
    ),
    (
        "Comparaison CA année N vs N-1 par client",
        """WITH CA_N AS (
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
    n.[Code client], n.[Intitulé client] AS [Client],
    ISNULL(n.[CA_Annee_N], 0) AS [CA Annee N],
    ISNULL(n1.[CA_Annee_N1], 0) AS [CA Annee N-1],
    ISNULL(n.[CA_Annee_N], 0) - ISNULL(n1.[CA_Annee_N1], 0) AS [Ecart],
    CASE WHEN ISNULL(n1.[CA_Annee_N1], 0) > 0
        THEN ROUND((ISNULL(n.[CA_Annee_N], 0) - n1.[CA_Annee_N1]) * 100.0 / n1.[CA_Annee_N1], 2)
        ELSE NULL END AS [Evolution %]
FROM CA_N n
LEFT JOIN CA_N1 n1 ON n.[Code client] = n1.[Code client]
ORDER BY [CA Annee N] DESC"""
    ),
    (
        "Marge par catalogue de produits",
        """SELECT
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
ORDER BY [CA HT] DESC"""
    ),
    (
        "CA par commercial et collaborateur",
        """SELECT
    [Code collaborateur],
    [Nom collaborateur] AS [Nom],
    [Prénom collaborateur] AS [Prenom],
    SUM([Montant HT Net]) AS [CA HT],
    SUM([Montant HT Net] - [Prix de revient] * [Quantité]) AS [Marge],
    CASE WHEN SUM([Montant HT Net]) > 0
        THEN ROUND(SUM([Montant HT Net] - [Prix de revient] * [Quantité]) * 100.0 / SUM([Montant HT Net]), 2)
        ELSE 0 END AS [Taux Marge %],
    COUNT(DISTINCT [Code client]) AS [Nb Clients],
    COUNT(DISTINCT [N° Pièce]) AS [Nb Documents]
FROM Lignes_des_ventes
WHERE [Valorise CA] = 'Oui'
  AND YEAR([Date]) = YEAR(GETDATE())
GROUP BY [Code collaborateur], [Nom collaborateur], [Prénom collaborateur]
ORDER BY [CA HT] DESC"""
    ),
    (
        "Articles en rupture de stock",
        """SELECT
    [Code article],
    [Désignation article],
    [Code dépôt],
    [Quantité en stock],
    [Quantité minimale],
    [Valeur du stock (montant)]
FROM Etat_Stock
WHERE [Quantité en stock] <= 0
   OR [Quantité en stock] < [Quantité minimale]
ORDER BY [Quantité en stock] ASC"""
    ),
    (
        "DSO délai moyen de paiement clients",
        """SELECT
    [Code client],
    [Intitulé client] AS [Client],
    COUNT([N° Pièce]) AS [Nb Echeances],
    SUM([Montant échéance]) AS [Total Echeances],
    SUM(ISNULL([Montant du règlement], 0)) AS [Total Regle],
    SUM([Montant échéance] - ISNULL([Montant du règlement], 0)) AS [En Cours],
    AVG(DATEDIFF(DAY, [Date document], [Date d'échéance])) AS [DSO Moyen Jours]
FROM Echéances_Ventes
WHERE [Date document] IS NOT NULL
GROUP BY [Code client], [Intitulé client]
HAVING SUM([Montant échéance]) > 0
ORDER BY [En Cours] DESC"""
    ),
    (
        "Taux de marge par client cette année",
        """SELECT TOP 20
    [Code client],
    [Intitulé client] AS [Client],
    SUM([Montant HT Net]) AS [CA HT],
    SUM([Montant HT Net] - [Prix de revient] * [Quantité]) AS [Marge Brute],
    CASE WHEN SUM([Montant HT Net]) > 0
        THEN ROUND(SUM([Montant HT Net] - [Prix de revient] * [Quantité]) * 100.0 / SUM([Montant HT Net]), 2)
        ELSE 0 END AS [Taux Marge %]
FROM Lignes_des_ventes
WHERE [Valorise CA] = 'Oui'
  AND YEAR([Date]) = YEAR(GETDATE())
GROUP BY [Code client], [Intitulé client]
HAVING SUM([Montant HT Net]) > 0
ORDER BY [Taux Marge %] DESC"""
    ),
    (
        "Mouvements de stock du mois en cours",
        """SELECT TOP 100
    [Code article], [Désignation], [Intitulé famille] AS [Famille],
    [Date Mouvement], [Sens de mouvement] AS [Sens],
    [Quantité], [CMUP],
    [Quantité] * [CMUP] AS [Valeur],
    [Code Dépôt] AS [Depot],
    [N° Pièce] AS [Piece]
FROM Mouvement_stock
WHERE [Date Mouvement] >= DATEADD(MONTH, DATEDIFF(MONTH, 0, GETDATE()), 0)
  AND [Date Mouvement] < DATEADD(MONTH, DATEDIFF(MONTH, 0, GETDATE()) + 1, 0)
ORDER BY [Date Mouvement] DESC"""
    ),
]


def seed_library(validated_by: str = "system_seed") -> int:
    """
    Initialise la Query Library avec les 15 exemples de référence.
    Retourne le nombre d'exemples insérés (ignore les doublons).
    """
    inserted = 0
    for question, sql in _SEED_EXAMPLES:
        try:
            existing = execute_central(
                "SELECT id FROM APP_AI_QueryLibrary WHERE question_text = ?",
                (question,), use_cache=False
            )
            if existing:
                continue  # skip duplicate
            with central_cursor() as cursor:
                cursor.execute(
                    """INSERT INTO APP_AI_QueryLibrary
                       (question_text, sql_query, validated_by, is_validated, success_count)
                       VALUES (?, ?, ?, 1, 5)""",
                    (question, sql, validated_by)
                )
            inserted += 1
        except Exception as e:
            logger.warning(f"Seed insert failed for '{question[:40]}': {e}")
    logger.info(f"Library seeded: {inserted} new examples added")
    return inserted


def get_library_stats() -> Dict:
    """Statistiques globales de la library."""
    try:
        rows = execute_central(
            """SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN is_validated=1 THEN 1 ELSE 0 END) AS validated,
                SUM(feedback_positive) AS total_positive,
                SUM(feedback_negative) AS total_negative,
                SUM(success_count) AS total_uses
               FROM APP_AI_QueryLibrary""",
            use_cache=False
        )
        return rows[0] if rows else {}
    except Exception as e:
        logger.error(f"Failed to get library stats: {e}")
        return {}
