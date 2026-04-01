"""Service SIMPLIFIE de résolution des paramètres pour les DataSources"""

from datetime import datetime, date
from typing import Dict, Any, List
import re


# =============================================================================
# CONFIGURATION DES TYPES DE PARAMÈTRES
# =============================================================================

# Types de paramètres disponibles
PARAMETER_TYPES = [
    {"value": "date", "label": "Date"},
    {"value": "string", "label": "Texte"},
    {"value": "number", "label": "Entier"},
    {"value": "float", "label": "Décimal"},
    {"value": "boolean", "label": "Booléen"},
    {"value": "select", "label": "Liste déroulante"},
    {"value": "multiselect", "label": "Liste multi-sélection"},
]

# Sources de valeurs pour les paramètres
PARAMETER_SOURCES = [
    {"value": "global", "label": "Filtre Global"},
    {"value": "user", "label": "Saisie Utilisateur"},
    {"value": "fixed", "label": "Valeur Fixe"},
    {"value": "query", "label": "Requête SQL"},
]

# Clés globales disponibles (filtres partagés dans l'application)
AVAILABLE_GLOBAL_KEYS = [
    {"value": "dateDebut", "label": "Date de début"},
    {"value": "dateFin", "label": "Date de fin"},
    {"value": "annee", "label": "Année"},
    {"value": "societe", "label": "Société"},
    {"value": "commercial", "label": "Commercial"},
    {"value": "gamme", "label": "Gamme"},
    {"value": "zone", "label": "Zone"},
]

# Macros de dates disponibles
AVAILABLE_MACROS = [
    {"value": "TODAY", "label": "Aujourd'hui"},
    {"value": "YESTERDAY", "label": "Hier"},
    {"value": "FIRST_DAY_MONTH", "label": "1er jour du mois"},
    {"value": "LAST_DAY_MONTH", "label": "Dernier jour du mois"},
    {"value": "FIRST_DAY_YEAR", "label": "1er jour de l'année"},
    {"value": "LAST_DAY_YEAR", "label": "Dernier jour de l'année"},
    {"value": "FIRST_DAY_LAST_MONTH", "label": "1er jour du mois précédent"},
    {"value": "LAST_DAY_LAST_MONTH", "label": "Dernier jour du mois précédent"},
    {"value": "FIRST_DAY_LAST_YEAR", "label": "1er jour de l'année précédente"},
    {"value": "LAST_DAY_LAST_YEAR", "label": "Dernier jour de l'année précédente"},
]


# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

def extract_parameters_from_query(query: str) -> List[Dict[str, Any]]:
    """
    Extrait les paramètres (@param) d'une requête SQL et suggère leur configuration.

    Args:
        query: Requête SQL contenant des @param

    Returns:
        Liste de suggestions de paramètres avec type et source auto-détectés
    """
    pattern = r'@(\w+)'
    matches = set(re.findall(pattern, query))

    suggestions = []
    for param_name in matches:
        param_lower = param_name.lower()

        # Auto-détection du type et de la source
        param_config = {
            "name": param_name,
            "label": param_name.replace("_", " ").title(),
            "required": True,
            "source": "user",
            "global_key": None,
            "default": None
        }

        # Détection du type basée sur le nom
        if "date" in param_lower or param_lower in ["du", "au", "debut", "fin"]:
            param_config["type"] = "date"
            # Vérifier si c'est un filtre global connu
            if param_lower in ["datedebut", "datefin", "date_debut", "date_fin"]:
                param_config["source"] = "global"
                param_config["global_key"] = "dateDebut" if "debut" in param_lower else "dateFin"
        elif any(x in param_lower for x in ["montant", "prix", "total", "ca", "marge", "cout"]):
            param_config["type"] = "float"
        elif any(x in param_lower for x in ["id", "annee", "mois", "jour", "quantite", "qte", "nb", "nombre"]):
            param_config["type"] = "number"
        elif any(x in param_lower for x in ["actif", "valide", "is_", "has_"]):
            param_config["type"] = "boolean"
        else:
            param_config["type"] = "string"

        # Détection des filtres globaux connus
        if param_lower in ["societe", "société"]:
            param_config["source"] = "global"
            param_config["global_key"] = "societe"
        elif param_lower in ["commercial", "representant"]:
            param_config["source"] = "global"
            param_config["global_key"] = "commercial"
        elif param_lower in ["gamme", "catalogue"]:
            param_config["source"] = "global"
            param_config["global_key"] = "gamme"
        elif param_lower == "annee":
            param_config["source"] = "global"
            param_config["global_key"] = "annee"
            param_config["type"] = "number"

        suggestions.append(param_config)

    return suggestions


def get_default_context() -> Dict[str, Any]:
    """Retourne un contexte par défaut avec les dates des 2 dernières années"""
    today = date.today()
    return {
        "dateDebut": f"{today.year - 5}-01-01",
        "dateFin": today.isoformat(),
        "annee": today.year,
        "societe": None,
        "commercial": None,
        "gamme": None,
        "zone": None
    }


def _is_date_string(value: str) -> bool:
    """Vérifie si une string ressemble à une date (YYYY-MM-DD ou DD/MM/YYYY)"""
    # Format ISO: 2024-01-15 ou 2024-01-15T...
    if re.match(r'^\d{4}-\d{2}-\d{2}', value):
        return True
    # Format FR: 15/01/2024
    if re.match(r'^\d{2}/\d{2}/\d{4}$', value):
        return True
    return False


def _to_sql_safe_date(value: str) -> str:
    """
    Convertit une date string en format SQL Server non-ambigu YYYYMMDD.
    Ce format fonctionne indépendamment du DATEFORMAT ou de la langue du serveur.
    """
    # Format ISO: 2024-01-15 ou 2024-01-15T10:30:00
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})', value)
    if m:
        return f"'{m.group(1)}{m.group(2)}{m.group(3)}'"

    # Format FR: 15/01/2024
    m = re.match(r'^(\d{2})/(\d{2})/(\d{4})$', value)
    if m:
        return f"'{m.group(3)}{m.group(2)}{m.group(1)}'"

    # Fallback — retourner tel quel entre quotes
    escaped = value.replace("'", "''")
    return f"'{escaped}'"


def inject_params(query: str, context: Dict[str, Any] = None) -> str:
    """
    Injecte les paramètres dans une requête SQL de manière simple et directe.

    Remplace les @param par leurs valeurs du contexte.
    Si un paramètre n'est pas dans le contexte, utilise une valeur par défaut.

    Les dates sont converties au format YYYYMMDD (sans tirets) qui est le seul
    format non-ambigu pour SQL Server, indépendamment du DATEFORMAT configuré.

    Args:
        query: Requête SQL avec des @param
        context: Dictionnaire des paramètres {nom: valeur}

    Returns:
        Requête SQL avec les paramètres substitués
    """
    if context is None:
        context = {}

    # Fusionner avec les valeurs par défaut
    defaults = get_default_context()
    params = {**defaults, **context}

    result = query

    # Trouver tous les @param dans la requête
    pattern = r'@(\w+)'
    matches = re.findall(pattern, query)

    # Substituer chaque paramètre trouvé
    for param_name in matches:
        placeholder = f"@{param_name}"

        # Chercher la valeur (case insensitive)
        value = None
        for key, val in params.items():
            if key.lower() == param_name.lower():
                value = val
                break

        # Formater la valeur pour SQL
        if value is None:
            sql_value = "NULL"
        elif isinstance(value, bool):
            sql_value = "1" if value else "0"
        elif isinstance(value, (int, float)):
            sql_value = str(value)
        elif isinstance(value, (date, datetime)):
            # Format YYYYMMDD — non-ambigu pour SQL Server
            sql_value = f"'{value.strftime('%Y%m%d')}'"
        elif isinstance(value, list):
            # Liste de valeurs (multiselect) - convertir en chaîne séparée par virgules
            if len(value) == 0:
                sql_value = "NULL"
            else:
                # Échapper chaque valeur et joindre avec des virgules
                escaped_values = [str(v).replace("'", "''") for v in value]
                sql_value = f"'{','.join(escaped_values)}'"
        else:
            # String - vérifier si c'est une date (ex: "2024-01-15")
            str_value = str(value)
            if _is_date_string(str_value):
                sql_value = _to_sql_safe_date(str_value)
            else:
                # String normale - échapper les quotes
                escaped = str_value.replace("'", "''")
                sql_value = f"'{escaped}'"

        result = result.replace(placeholder, sql_value)

    return result


def build_where_clause(context: Dict[str, Any] = None, table_alias: str = "") -> str:
    """
    Construit une clause WHERE basée sur le contexte des filtres.

    Args:
        context: Dictionnaire des filtres
        table_alias: Alias de la table (ex: "ca." pour "ca.[Date BL]")

    Returns:
        Clause WHERE (sans le mot WHERE)
    """
    if context is None:
        context = {}

    conditions = []
    prefix = f"{table_alias}." if table_alias else ""

    # Filtre par dates — format YYYYMMDD non-ambigu pour SQL Server
    if context.get("dateDebut") and context.get("dateFin"):
        safe_debut = _to_sql_safe_date(str(context['dateDebut']))
        safe_fin = _to_sql_safe_date(str(context['dateFin']))
        conditions.append(
            f"{prefix}[Date BL] BETWEEN {safe_debut} AND {safe_fin}"
        )

    # Filtre par société
    if context.get("societe"):
        societe = str(context["societe"]).replace("'", "''")
        conditions.append(f"{prefix}[Société] = '{societe}'")

    # Filtre par commercial
    if context.get("commercial"):
        commercial = str(context["commercial"]).replace("'", "''")
        conditions.append(f"{prefix}[Représentant] = '{commercial}'")

    # Filtre par gamme
    if context.get("gamme"):
        gamme = str(context["gamme"]).replace("'", "''")
        conditions.append(f"{prefix}[Catalogue 1] = '{gamme}'")

    # Filtre par zone
    if context.get("zone"):
        zone = str(context["zone"]).replace("'", "''")
        conditions.append(f"{prefix}[Souche] = '{zone}'")

    return " AND ".join(conditions) if conditions else "1=1"


# Aliases pour compatibilité
def resolve_parameters(param_definitions, context):
    """Fonction de compatibilité - retourne simplement le contexte fusionné avec les défauts"""
    defaults = get_default_context()
    return {**defaults, **(context or {})}


def substitute_params(query: str, params: Dict[str, Any]) -> str:
    """Alias pour inject_params"""
    return inject_params(query, params)
