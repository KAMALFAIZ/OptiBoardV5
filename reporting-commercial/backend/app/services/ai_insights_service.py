"""
Service de génération d'insights IA automatiques pour les rapports OptiBoard.
Analyse les données d'un rapport et génère des observations intelligentes
(tendances, anomalies, performances, recommandations).
"""
import json
import hashlib
import time
import decimal
import datetime
import logging
from typing import List, Dict, Any, Optional

from .ai_provider import get_ai_provider, AIMessage, AIProviderError

logger = logging.getLogger(__name__)

# Cache en mémoire : clé = (report_type, report_id, data_hash) → { insights, generated_at }
_insights_cache: Dict[str, Dict] = {}
CACHE_TTL_SECONDS = 1800  # 30 minutes


def _json_serial(obj):
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _hash_data(data: Any) -> str:
    raw = json.dumps(data, default=_json_serial, sort_keys=True)
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def _summarize_data(data: List[Dict], columns_info: List[Dict], max_rows: int = 200) -> Dict:
    """
    Prépare un résumé statistique des données pour l'IA.
    Envoie des stats agrégées plutôt que les données brutes pour économiser les tokens.
    """
    if not data:
        return {"row_count": 0, "columns": [], "sample": []}

    sample = data[:max_rows]
    col_stats = []

    # Détecter les types et calculer les stats par colonne
    for col in (columns_info or []):
        field = col.get("field") or col.get("header", "")
        if not field:
            continue

        values = [row.get(field) for row in sample if row.get(field) is not None]
        if not values:
            col_stats.append({"field": field, "header": col.get("header", field), "type": "vide"})
            continue

        # Détecter si numérique
        numeric_vals = []
        for v in values:
            try:
                numeric_vals.append(float(v))
            except (TypeError, ValueError):
                pass

        if len(numeric_vals) >= len(values) * 0.7:
            # Colonne numérique
            total = sum(numeric_vals)
            mn = min(numeric_vals)
            mx = max(numeric_vals)
            avg = total / len(numeric_vals)
            col_stats.append({
                "field": field,
                "header": col.get("header", field),
                "type": "numerique",
                "total": round(total, 2),
                "min": round(mn, 2),
                "max": round(mx, 2),
                "moyenne": round(avg, 2),
                "nb_valeurs": len(numeric_vals)
            })
        else:
            # Colonne catégorielle
            str_vals = [str(v) for v in values if v is not None]
            unique = list(set(str_vals))
            # Top 5 valeurs les plus fréquentes
            from collections import Counter
            top5 = Counter(str_vals).most_common(5)
            col_stats.append({
                "field": field,
                "header": col.get("header", field),
                "type": "categoriel",
                "nb_valeurs_uniques": len(unique),
                "nb_total": len(str_vals),
                "top_valeurs": [{"valeur": v, "count": c} for v, c in top5]
            })

    return {
        "nb_lignes_total": len(data),
        "nb_lignes_analysees": len(sample),
        "statistiques_colonnes": col_stats
    }


def _build_prompt(report_nom: str, report_type: str, summary: Dict, context: Optional[str] = None) -> str:
    """Construit le prompt envoyé à l'IA."""
    type_labels = {"gridview": "tableau de données", "dashboard": "tableau de bord", "pivot": "rapport croisé"}
    type_label = type_labels.get(report_type, "rapport")

    summary_json = json.dumps(summary, ensure_ascii=False, indent=2, default=_json_serial)

    ctx_section = f"\nContexte métier supplémentaire: {context}\n" if context else ""

    return f"""Tu es un analyste BI expert. Analyse les données statistiques du {type_label} "{report_nom}" et génère des insights business pertinents.

{ctx_section}
Données statistiques:
{summary_json}

Génère entre 4 et 7 insights courts et actionnables. Utilise ce format JSON strict:
{{
  "insights": [
    {{"type": "tendance", "texte": "..."}},
    {{"type": "alerte", "texte": "..."}},
    {{"type": "performance", "texte": "..."}},
    {{"type": "conseil", "texte": "..."}}
  ]
}}

Types disponibles: "tendance", "alerte", "performance", "conseil", "anomalie", "comparaison"
Règles:
- Insights en français, concis (max 120 caractères chacun)
- Basés uniquement sur les données fournies
- Orientés décision métier
- Retourne UNIQUEMENT le JSON, sans markdown ni texte autour"""


async def generate_insights(
    report_type: str,
    report_id: int,
    report_nom: str,
    data: List[Dict],
    columns_info: List[Dict],
    context: Optional[str] = None,
    force_refresh: bool = False
) -> Dict:
    """
    Génère des insights IA pour un rapport.
    Utilise le cache si disponible (TTL 30 min).
    """
    cache_key = f"{report_type}:{report_id}:{_hash_data(data[:50])}"

    # Vérifier le cache
    if not force_refresh and cache_key in _insights_cache:
        cached = _insights_cache[cache_key]
        age = time.time() - cached["generated_at"]
        if age < CACHE_TTL_SECONDS:
            return {**cached, "from_cache": True, "cache_age_minutes": round(age / 60, 1)}

    # Obtenir le provider IA
    try:
        provider = get_ai_provider()
        if provider is None:
            return {"success": False, "error": "IA non configurée", "insights": []}
    except AIProviderError as e:
        return {"success": False, "error": str(e), "insights": []}

    # Préparer les données
    summary = _summarize_data(data, columns_info)

    if summary["nb_lignes_total"] == 0:
        return {"success": False, "error": "Aucune donnée à analyser", "insights": []}

    prompt = _build_prompt(report_nom, report_type, summary, context)

    # Appel IA
    try:
        messages = [AIMessage(role="user", content=prompt)]
        response_text = await provider.chat(messages)

        # Parser le JSON retourné
        # Nettoyer le markdown si présent
        text = response_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

        parsed = json.loads(text)
        insights = parsed.get("insights", [])

        result = {
            "success": True,
            "insights": insights,
            "provider": provider.get_provider_name(),
            "generated_at": time.time(),
            "nb_lignes_analysees": summary["nb_lignes_analysees"],
            "from_cache": False
        }

        # Mettre en cache
        _insights_cache[cache_key] = result

        return result

    except json.JSONDecodeError as e:
        logger.error(f"[AI_INSIGHTS] JSON parse error: {e}\nResponse: {response_text[:200]}")
        return {"success": False, "error": "Format de réponse IA invalide", "insights": []}
    except AIProviderError as e:
        logger.error(f"[AI_INSIGHTS] Provider error: {e}")
        return {"success": False, "error": str(e), "insights": []}
    except Exception as e:
        logger.error(f"[AI_INSIGHTS] Unexpected error: {e}")
        return {"success": False, "error": "Erreur lors de la génération des insights", "insights": []}


def invalidate_cache(report_type: str, report_id: int):
    """Invalide le cache pour un rapport spécifique."""
    keys_to_delete = [k for k in _insights_cache if k.startswith(f"{report_type}:{report_id}:")]
    for k in keys_to_delete:
        del _insights_cache[k]
