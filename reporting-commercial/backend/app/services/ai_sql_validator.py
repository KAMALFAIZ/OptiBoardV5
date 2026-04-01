"""
Validateur SQL strict pour les requetes generees par l'IA.
Reutilise le pattern de validation de admin_sql.py avec des regles supplementaires.
Supporte les CTEs (WITH ... AS (...) SELECT ...).
"""
import re
from typing import Tuple

# Mots-cles DML/DDL interdits
FORBIDDEN_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
    "TRUNCATE", "EXEC", "EXECUTE", "MERGE", "GRANT", "REVOKE",
    "OPENROWSET", "OPENDATASOURCE", "BULK",
    "WAITFOR", "SHUTDOWN", "KILL",
]

# Prefixes de procedures systeme interdits
FORBIDDEN_PREFIXES = ["xp_", "sp_"]

# Pattern pour detecter les commentaires SQL
COMMENT_PATTERN = re.compile(r'(--[^\n]*|/\*.*?\*/)', re.DOTALL)


def validate_ai_sql(query: str, max_rows: int = 500) -> Tuple[bool, str, str]:
    """
    Valide et securise une requete SQL generee par l'IA.
    Supporte les requetes SELECT simples et les CTEs (WITH ... AS ... SELECT ...).

    Returns:
        (is_valid, sanitized_query, error_message)
    """
    if not query or not query.strip():
        return False, "", "La requete SQL est vide"

    # Supprimer les commentaires SQL
    cleaned = COMMENT_PATTERN.sub(" ", query).strip()

    # Doit commencer par SELECT ou WITH (CTE)
    query_upper = cleaned.upper().strip()
    if not query_upper.startswith("SELECT") and not query_upper.startswith("WITH"):
        return False, "", "Seules les requetes SELECT sont autorisees"

    # Si CTE (WITH), verifier qu'il y a un SELECT final (pas un INSERT/UPDATE/DELETE apres le CTE)
    if query_upper.startswith("WITH"):
        # Trouver le dernier SELECT principal (hors des sous-requetes du CTE)
        # Approche simple : verifier qu'aucun mot-cle DML n'apparait en dehors du CTE
        # Le check des FORBIDDEN_KEYWORDS plus bas couvre ce cas
        # Verifier aussi qu'il y a au moins un SELECT dans la requete
        if "SELECT" not in query_upper:
            return False, "", "Requete CTE invalide: aucun SELECT final detecte"

    # Verifier les mots-cles interdits (word-boundary)
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf'\b{re.escape(keyword)}\b', query_upper):
            return False, "", f"Mot-cle interdit detecte: {keyword}"

    # Verifier les prefixes de procedures systeme
    for prefix in FORBIDDEN_PREFIXES:
        if prefix.upper() in query_upper:
            return False, "", f"Appel de procedure systeme interdit: {prefix}"

    # Bloquer les points-virgules (empecher les requetes multiples)
    if ";" in cleaned:
        return False, "", "Les requetes multiples (;) ne sont pas autorisees"

    # Ajouter TOP si absent dans le SELECT final
    if "TOP" not in query_upper:
        if query_upper.startswith("WITH"):
            # CTE : injecter TOP dans le dernier SELECT principal (celui apres la derniere parenthese fermante)
            # Trouver le SELECT final qui n'est pas dans un CTE body
            # On cherche le dernier "SELECT" qui suit un ")" ou qui est le SELECT principal
            # Approche robuste : trouver la position du dernier SELECT au premier niveau
            last_select = _find_final_select(cleaned)
            if last_select >= 0:
                cleaned = (
                    cleaned[:last_select]
                    + re.sub(
                        r'(?i)^SELECT\s+',
                        f'SELECT TOP {max_rows} ',
                        cleaned[last_select:],
                        count=1
                    )
                )
        else:
            # SELECT simple : injecter TOP au debut
            cleaned = re.sub(
                r'^SELECT\s+',
                f'SELECT TOP {max_rows} ',
                cleaned,
                count=1,
                flags=re.IGNORECASE
            )

    # Verifier la longueur (CTEs peuvent etre plus longues)
    if len(cleaned) > 10000:
        return False, "", "Requete trop longue (max 10000 caracteres)"

    return True, cleaned, ""


def _find_final_select(sql: str) -> int:
    """
    Trouve la position du SELECT final dans une requete CTE.
    Parcourt la requete en comptant les parentheses pour ignorer les SELECT
    qui sont dans les corps des CTEs (entre parentheses).
    Retourne l'index du dernier SELECT au niveau 0 de parentheses.
    """
    depth = 0
    last_select_pos = -1
    upper = sql.upper()
    i = 0
    while i < len(sql):
        if sql[i] == '(':
            depth += 1
        elif sql[i] == ')':
            depth -= 1
        elif depth == 0 and upper[i:i+6] == 'SELECT':
            # Verifier que c'est un mot complet (pas "SELECTEUR" etc.)
            before_ok = (i == 0 or not upper[i-1].isalpha())
            after_ok = (i + 6 >= len(sql) or not upper[i+6].isalpha())
            if before_ok and after_ok:
                last_select_pos = i
        i += 1
    return last_select_pos
