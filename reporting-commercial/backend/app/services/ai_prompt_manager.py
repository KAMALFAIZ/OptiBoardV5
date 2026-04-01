"""
Gestionnaire de prompts IA dynamiques.
Stocke les prompts personnalisés dans APP_AI_Prompts (central DB).
Fallback sur les valeurs hardcodées si aucune customisation n'existe.
"""
import logging
from typing import Optional, Dict
from ..database_unified import execute_central, write_central, central_cursor

logger = logging.getLogger(__name__)

_CREATE_TABLE_SQL = """
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_AI_Prompts' AND xtype='U')
CREATE TABLE APP_AI_Prompts (
    id INT IDENTITY(1,1) PRIMARY KEY,
    code VARCHAR(100) NOT NULL UNIQUE,
    nom NVARCHAR(200) NOT NULL,
    contenu NVARCHAR(MAX) NOT NULL,
    description NVARCHAR(500) NULL,
    actif BIT NOT NULL DEFAULT 1,
    updated_by VARCHAR(200) NULL,
    created_at DATETIME NOT NULL DEFAULT GETDATE(),
    updated_at DATETIME NOT NULL DEFAULT GETDATE()
)
"""

# ── Prompts par défaut (fallback si non personnalisé) ────────────────────────

_DEFAULTS: Dict[str, Dict] = {
    "business_context": {
        "nom": "Contexte Métier",
        "description": "Présentation générale de l'assistant et du contexte business",
        "contenu": (
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
    },
    "sql_rules": {
        "nom": "Règles SQL Strictes",
        "description": "Règles obligatoires pour la génération SQL (colonnes, formules, filtres)",
        "contenu": (
            "=== REGLES STRICTES POUR LA GENERATION SQL ===\n"
            "1. Utilise UNIQUEMENT les noms de colonnes listes dans la section 'Colonnes:' du SCHEMA ci-dessus. "
            "N'invente JAMAIS un nom de colonne. Si un exemple SQL utilise une colonne qui n'apparait pas "
            "dans le schema, adapte l'exemple en utilisant la colonne equivalente du schema.\n"
            "2. Pour tout calcul de CA/ventes/revenus: TOUJOURS ajouter WHERE [Valorise CA] = 'Oui'.\n"
            "3. Pour filtrer par date sur Lignes_des_ventes: utiliser la colonne [Date] "
            "(PAS [Date BL], PAS [Date Facture], PAS [DatePiece]).\n"
            "4. Formule marge: [Montant HT Net] - [Prix de revient] * [Quantite].\n"
            "5. Formule reste a regler: [Montant echeance] - ISNULL([Montant du reglement], 0).\n"
            "6. Utiliser ISNULL() pour les colonnes nullable.\n"
            "7. Noms de tables SANS prefixe: FROM Lignes_des_ventes (JAMAIS [BASE].[dbo].[Table]).\n"
            "8. Format T-SQL (SQL Server): utiliser TOP (pas LIMIT), GETDATE(), DATEADD, DATEDIFF, FORMAT.\n"
            "9. Limiter les resultats avec TOP 500 maximum.\n"
            "10. Entourer le SQL avec ```sql et ```. Une seule requete par reponse.\n"
            "\n"
            "REGLES GENERALES:\n"
            "- Reponds TOUJOURS en francais\n"
            "- Pour les montants, precise l'unite (DH)\n"
            "- Si une question est ambigue, demande des clarifications\n"
            "- Utilise les noms de colonnes exacts entre crochets ([Nom Colonne])\n"
            "- Inspire-toi des EXEMPLES SQL ci-dessus pour la structure des requetes"
        )
    },
    "mode_chat": {
        "nom": "Mode Analyse (Chat)",
        "description": "Instructions spécifiques au mode analyse/chat général",
        "contenu": (
            "MODE ANALYSE:\n"
            "Tu analyses les donnees de reporting commercial et reponds aux questions metier.\n"
            "Si la question necessite des donnees specifiques, genere une requete SQL\n"
            "pour les recuperer et analyse les resultats.\n"
            "Formate tes reponses de facon claire avec des listes et des chiffres cles."
        )
    },
    "mode_sql": {
        "nom": "Mode SQL Assistant",
        "description": "Instructions spécifiques au mode SQL",
        "contenu": (
            "MODE SQL ASSISTANT:\n"
            "Tu aides a construire des requetes SQL pour analyser les donnees.\n"
            "Genere TOUJOURS une requete SQL valide pour la question posee.\n"
            "Explique brievement ce que fait la requete avant de la proposer."
        )
    },
    "mode_help": {
        "nom": "Mode Aide Contextuelle",
        "description": "Instructions spécifiques au mode aide/documentation",
        "contenu": (
            "MODE AIDE CONTEXTUELLE:\n"
            "Tu expliques comment utiliser OptiBoard et interpretes les donnees.\n"
            "Fournis des conseils pratiques sur l'analyse des ventes, stocks et recouvrement.\n"
            "Ne genere pas de SQL sauf si explicitement demande."
        )
    },
    "custom_instructions": {
        "nom": "Instructions Personnalisées",
        "description": "Instructions supplémentaires spécifiques à votre organisation (optionnel)",
        "contenu": ""
    },
}

# Cache en mémoire (60s TTL) pour éviter les lectures DB à chaque appel
_cache: Dict[str, str] = {}
_cache_ts: Dict[str, float] = {}
_CACHE_TTL = 60.0


def init_prompts_table():
    """Crée la table APP_AI_Prompts si elle n'existe pas."""
    try:
        with central_cursor() as cursor:
            cursor.execute(_CREATE_TABLE_SQL)
        logger.info("APP_AI_Prompts table ready")
    except Exception as e:
        logger.error(f"Failed to init APP_AI_Prompts: {e}")


def get_prompt(code: str) -> str:
    """
    Retourne le contenu du prompt pour le code donné.
    Cherche d'abord en DB, fallback sur la valeur hardcodée.
    """
    import time
    now = time.time()

    # Cache hit
    if code in _cache and now - _cache_ts.get(code, 0) < _CACHE_TTL:
        return _cache[code]

    # DB lookup
    try:
        rows = execute_central(
            "SELECT contenu FROM APP_AI_Prompts WHERE code = ? AND actif = 1",
            (code,), use_cache=False
        )
        if rows:
            value = rows[0]['contenu']
            _cache[code] = value
            _cache_ts[code] = now
            return value
    except Exception as e:
        logger.warning(f"Prompt DB lookup failed for '{code}': {e}")

    # Fallback hardcodé
    default = _DEFAULTS.get(code, {}).get("contenu", "")
    _cache[code] = default
    _cache_ts[code] = now
    return default


def save_prompt(code: str, contenu: str, updated_by: str = None) -> bool:
    """Sauvegarde ou met à jour un prompt en DB."""
    try:
        existing = execute_central(
            "SELECT id FROM APP_AI_Prompts WHERE code = ?",
            (code,), use_cache=False
        )
        nom = _DEFAULTS.get(code, {}).get("nom", code)
        description = _DEFAULTS.get(code, {}).get("description", "")

        if existing:
            write_central(
                "UPDATE APP_AI_Prompts SET contenu = ?, updated_by = ?, updated_at = GETDATE() WHERE code = ?",
                (contenu, updated_by, code)
            )
        else:
            write_central(
                """INSERT INTO APP_AI_Prompts (code, nom, contenu, description, updated_by)
                   VALUES (?, ?, ?, ?, ?)""",
                (code, nom, contenu, description, updated_by)
            )
        # Invalider le cache
        _cache.pop(code, None)
        _cache_ts.pop(code, None)
        return True
    except Exception as e:
        logger.error(f"Failed to save prompt '{code}': {e}")
        return False


def reset_prompt(code: str) -> bool:
    """Remet le prompt à sa valeur par défaut (supprime la customisation DB)."""
    try:
        write_central("DELETE FROM APP_AI_Prompts WHERE code = ?", (code,))
        _cache.pop(code, None)
        _cache_ts.pop(code, None)
        return True
    except Exception as e:
        logger.error(f"Failed to reset prompt '{code}': {e}")
        return False


def get_all_prompts() -> list:
    """Retourne toutes les sections de prompts avec leur statut (DB ou défaut)."""
    result = []
    try:
        db_rows = execute_central(
            "SELECT code, contenu, updated_by, updated_at FROM APP_AI_Prompts WHERE actif = 1",
            use_cache=False
        )
        db_map = {r['code']: r for r in db_rows}
    except Exception:
        db_map = {}

    for code, meta in _DEFAULTS.items():
        db_entry = db_map.get(code)
        result.append({
            "code": code,
            "nom": meta["nom"],
            "description": meta["description"],
            "contenu": db_entry['contenu'] if db_entry else meta["contenu"],
            "default_contenu": meta["contenu"],
            "is_customized": code in db_map,
            "updated_by": db_entry['updated_by'] if db_entry else None,
            "updated_at": db_entry['updated_at'].isoformat() if db_entry and db_entry['updated_at'] else None,
        })
    return result
