"""
Service de génération de résumés exécutifs IA pour OptiBoard.
Produit un rapport narratif structuré (sections, paragraphes) à partir
des données d'un rapport — exportable en PDF/texte côté frontend.
"""
import json
import hashlib
import time
import decimal
import datetime
import logging
from typing import List, Dict, Any, Optional

from .ai_provider import get_ai_provider, AIMessage, AIProviderError
from .ai_insights_service import _summarize_data   # réutiliser le résumé statistique

logger = logging.getLogger(__name__)

# Cache 30 min
_summary_cache: Dict[str, Dict] = {}
CACHE_TTL = 1800


def _json_serial(obj):
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    raise TypeError(f"Not serializable: {type(obj).__name__}")


def _hash_data(data: Any) -> str:
    raw = json.dumps(data, default=_json_serial, sort_keys=True)
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def _build_summary_prompt(
    report_nom: str,
    report_type: str,
    summary: Dict,
    period: Optional[str],
    entity: Optional[str],
    context: Optional[str]
) -> str:
    type_labels = {
        "gridview": "tableau de données",
        "dashboard": "tableau de bord analytique",
        "pivot": "rapport croisé dynamique"
    }
    type_label = type_labels.get(report_type, "rapport")
    summary_json = json.dumps(summary, ensure_ascii=False, indent=2, default=_json_serial)

    period_line = f"Période analysée : {period}" if period else ""
    entity_line = f"Entité / périmètre : {entity}" if entity else ""
    context_line = f"Contexte métier : {context}" if context else ""

    meta_lines = "\n".join(filter(None, [period_line, entity_line, context_line]))
    meta_section = f"\nInformations contextuelles :\n{meta_lines}\n" if meta_lines else ""

    return f"""Tu es un analyste financier et BI senior. Génère un résumé exécutif professionnel pour le {type_label} "{report_nom}".

{meta_section}
Statistiques des données :
{summary_json}

Génère un résumé exécutif structuré au format JSON strict suivant :
{{
  "titre": "Résumé Exécutif — {report_nom}",
  "date_generation": "aujourd'hui",
  "sections": [
    {{
      "id": "synthese",
      "titre": "📋 Synthèse Globale",
      "contenu": "Paragraphe de 3-4 phrases résumant l'état général des données et les conclusions principales."
    }},
    {{
      "id": "tendances",
      "titre": "📈 Tendances & Performances",
      "contenu": "Paragraphe de 3-5 phrases décrivant les tendances observées, les colonnes numériques clés, évolutions notables."
    }},
    {{
      "id": "points_attention",
      "titre": "⚠️ Points d'Attention",
      "contenu": "Paragraphe de 2-3 phrases signalant anomalies, valeurs extrêmes, distributions inhabituelles ou risques détectés."
    }},
    {{
      "id": "recommandations",
      "titre": "💡 Recommandations",
      "contenu": "Paragraphe de 3-4 phrases proposant des actions concrètes basées sur les données. Orienté décision."
    }},
    {{
      "id": "conclusion",
      "titre": "✅ Conclusion",
      "contenu": "Paragraphe de 2-3 phrases de conclusion synthétique et prospective."
    }}
  ],
  "kpis_cles": [
    {{"label": "...", "valeur": "...", "interpretation": "..."}}
  ]
}}

Règles impératives :
- Réponse en français professionnel et concis
- Basé UNIQUEMENT sur les statistiques fournies, sans inventer de données
- Chaque section : 2 à 5 phrases, style rapport de direction
- kpis_cles : 3 à 5 indicateurs clés extraits des colonnes numériques
- Retourne UNIQUEMENT le JSON, sans markdown ni texte autour"""


async def generate_executive_summary(
    report_type: str,
    report_id: int,
    report_nom: str,
    data: List[Dict],
    columns_info: List[Dict],
    period: Optional[str] = None,
    entity: Optional[str] = None,
    context: Optional[str] = None,
    force_refresh: bool = False
) -> Dict:
    """
    Génère un résumé exécutif narratif structuré pour un rapport.
    """
    cache_key = f"summary:{report_type}:{report_id}:{_hash_data(data[:50])}"

    if not force_refresh and cache_key in _summary_cache:
        cached = _summary_cache[cache_key]
        age = time.time() - cached["generated_at"]
        if age < CACHE_TTL:
            return {**cached, "from_cache": True, "cache_age_minutes": round(age / 60, 1)}

    try:
        provider = get_ai_provider()
        if provider is None:
            return {"success": False, "error": "IA non configurée", "sections": []}
    except AIProviderError as e:
        return {"success": False, "error": str(e), "sections": []}

    summary = _summarize_data(data, columns_info)
    if summary["nb_lignes_total"] == 0:
        return {"success": False, "error": "Aucune donnée à analyser", "sections": []}

    prompt = _build_summary_prompt(report_nom, report_type, summary, period, entity, context)

    try:
        messages = [AIMessage(role="user", content=prompt)]
        response_text = await provider.chat(messages)

        # Nettoyer markdown éventuel
        text = response_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        parsed = json.loads(text)

        result = {
            "success": True,
            "titre": parsed.get("titre", f"Résumé Exécutif — {report_nom}"),
            "date_generation": datetime.datetime.now().strftime("%d/%m/%Y à %H:%M"),
            "sections": parsed.get("sections", []),
            "kpis_cles": parsed.get("kpis_cles", []),
            "provider": provider.get_provider_name(),
            "generated_at": time.time(),
            "nb_lignes_analysees": summary["nb_lignes_analysees"],
            "from_cache": False
        }

        _summary_cache[cache_key] = result
        return result

    except json.JSONDecodeError as e:
        logger.error(f"[AI_SUMMARY] JSON parse error: {e}")
        return {"success": False, "error": "Format de réponse IA invalide", "sections": []}
    except AIProviderError as e:
        logger.error(f"[AI_SUMMARY] Provider error: {e}")
        return {"success": False, "error": str(e), "sections": []}
    except Exception as e:
        logger.error(f"[AI_SUMMARY] Unexpected error: {e}")
        return {"success": False, "error": "Erreur lors de la génération du résumé", "sections": []}
