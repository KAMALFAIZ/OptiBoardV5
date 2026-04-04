"""
OptiBoard Deck IA — Générateur de présentations interactives basé sur les données réelles.
Chaque slide = données DWH + narration IA + recommandation + visualisation.
"""
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json, logging, decimal
from datetime import datetime, date

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ai/deck", tags=["AI Deck Builder"])

from ..database_unified import execute_central as execute_query


# ─────────────────────────────────────────────────────────────────────────────
# DB INIT
# ─────────────────────────────────────────────────────────────────────────────

def init_deck_tables():
    from ..database_unified import write_central as _wc
    _wc("""
        IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name='APP_AI_Decks')
        CREATE TABLE APP_AI_Decks (
            id           INT IDENTITY(1,1) PRIMARY KEY,
            user_id      INT NULL,
            dwh_code     NVARCHAR(50) NULL,
            title        NVARCHAR(500) NOT NULL DEFAULT 'Sans titre',
            user_request NTEXT NULL,
            slides_json  NTEXT NULL,
            status       NVARCHAR(20) DEFAULT 'draft',
            created_at   DATETIME DEFAULT GETDATE(),
            updated_at   DATETIME DEFAULT GETDATE()
        )
    """)


# ─────────────────────────────────────────────────────────────────────────────
# MODÈLES
# ─────────────────────────────────────────────────────────────────────────────

class PlanRequest(BaseModel):
    user_request: str

class SaveDeckRequest(BaseModel):
    title: str
    user_request: str
    slides: List[Dict[str, Any]] = []

class UpdateDeckRequest(BaseModel):
    slides: Optional[List[Dict[str, Any]]] = None
    title:  Optional[str] = None

class SlideChatRequest(BaseModel):
    message: str
    chat_history: List[Dict[str, str]] = []


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _json_serial(o):
    if isinstance(o, decimal.Decimal): return float(o)
    if isinstance(o, (datetime, date)): return str(o)
    return str(o)


def _get_datasources() -> List[Dict]:
    try:
        return execute_query(
            "SELECT TOP 30 id, code, nom, description FROM APP_DataSources_Templates WHERE actif=1 ORDER BY nom",
            use_cache=True
        ) or []
    except Exception as e:
        logger.warning(f"Datasource list error: {e}")
        return []


def _fetch_data(datasource_id: int, dwh_code: Optional[str], max_rows: int = 150) -> tuple:
    """Exécute la query d'un datasource, retourne (data, columns)."""
    try:
        from ..services.datasource_resolver import datasource_resolver
        from ..services.parameter_resolver import inject_params

        ds    = datasource_resolver.resolve_by_id(datasource_id, dwh_code)
        query = inject_params(ds.query_template, {})

        # Limiter sans casser la requête
        q_upper = query.upper().strip()
        if 'TOP ' not in q_upper and 'LIMIT ' not in q_upper:
            idx = query.upper().index('SELECT') + 6
            query = query[:idx] + f' TOP {max_rows} ' + query[idx:]

        if dwh_code and ds.origin.value == 'template':
            from ..database_unified import DWHConnectionManager
            data = DWHConnectionManager.execute_dwh_query(dwh_code, query, use_cache=False)
        else:
            data = execute_query(query, use_cache=False)

        cols = list(data[0].keys()) if data else []
        return data, cols
    except Exception as e:
        logger.warning(f"Datasource {datasource_id} fetch error: {e}")
        return [], []


# ─────────────────────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/plan")
async def generate_plan(
    req: PlanRequest,
    dwh_code:    Optional[str] = Header(None, alias="X-DWH-Code"),
    user_id_hdr: Optional[str] = Header(None, alias="X-User-Id"),
):
    """Génère un plan de slides à partir de la demande libre de l'utilisateur."""
    from ..services.ai_provider import get_ai_provider, AIMessage

    provider = get_ai_provider()
    if not provider:
        raise HTTPException(503, "IA non configurée. Ajoutez une clé API dans les paramètres.")

    datasources = _get_datasources()
    ds_text = "\n".join(
        f"  - ID {d['id']}: {d['nom']}" + (f" ({d['description']})" if d.get('description') else "")
        for d in datasources
    ) or "  Aucune source configurée"

    prompt = f"""Tu es un expert analyste de données commerciales.
L'utilisateur demande : "{req.user_request}"

Sources de données disponibles :
{ds_text}

Génère un plan de 6 à 8 slides professionnels adaptés à la demande.
Réponds UNIQUEMENT avec ce JSON valide, rien d'autre :
{{
  "deck_title": "Titre professionnel et accrocheur",
  "slides": [
    {{
      "title": "Titre court et percutant",
      "description": "Ce que ce slide montre (1 phrase)",
      "datasource_id": <entier depuis la liste ci-dessus, ou null>,
      "viz_type": "chart",
      "chart_type": "bar",
      "focus": "Angle spécifique d'analyse (ex: top 10 clients, évolution mensuelle...)"
    }}
  ]
}}

Règles :
- Slide 1 : synthèse exécutive — KPIs clés (viz_type: "chart", chart_type: "bar")
- Dernier slide : recommandations & prochaines étapes (viz_type: "none", datasource_id: null)
- viz_type possibles : "chart" | "grid" | "pivot" | "none"
- chart_type possibles : "bar" | "line" | "area" | "pie" (null si viz_type != "chart")
- Varie les types de viz pour une présentation équilibrée et dynamique
- Utilise uniquement les IDs de datasource listés ci-dessus"""

    try:
        raw = await provider.chat([
            AIMessage("system", "Tu génères uniquement du JSON valide, sans texte avant ni après."),
            AIMessage("user", prompt)
        ])
        raw = raw.strip()
        if "```json" in raw: raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:   raw = raw.split("```")[1].split("```")[0].strip()

        plan = json.loads(raw)
        # Normaliser les slides
        for i, sl in enumerate(plan.get("slides", [])):
            sl.setdefault("status", "pending")
            sl.setdefault("locked", False)
            sl.setdefault("narration", "")
            sl.setdefault("recommendation", "")
            sl.setdefault("data", [])
            sl.setdefault("columns", [])
            sl.setdefault("chat", [])
            sl.setdefault("notes", "")

        return {"success": True, "plan": plan}
    except json.JSONDecodeError as e:
        raise HTTPException(500, f"L'IA n'a pas retourné de JSON valide: {e}")
    except Exception as e:
        raise HTTPException(500, f"Erreur génération plan: {e}")


@router.post("")
async def create_deck(
    req: SaveDeckRequest,
    dwh_code:    Optional[str] = Header(None, alias="X-DWH-Code"),
    user_id_hdr: Optional[str] = Header(None, alias="X-User-Id"),
):
    """Sauvegarde un nouveau deck en base."""
    from ..database_unified import write_central as _wc
    uid = int(user_id_hdr) if user_id_hdr else None
    _wc(
        "INSERT INTO APP_AI_Decks (user_id, dwh_code, title, user_request, slides_json) VALUES (?,?,?,?,?)",
        (uid, dwh_code, req.title, req.user_request,
         json.dumps(req.slides, ensure_ascii=False, default=_json_serial))
    )
    rows = execute_query("SELECT TOP 1 id FROM APP_AI_Decks ORDER BY id DESC", use_cache=False)
    return {"success": True, "deck_id": rows[0]['id'] if rows else None}


@router.get("")
async def list_decks(
    user_id_hdr: Optional[str] = Header(None, alias="X-User-Id"),
):
    uid = int(user_id_hdr) if user_id_hdr else None
    rows = execute_query(
        "SELECT id, title, user_request, status, created_at FROM APP_AI_Decks "
        "WHERE user_id=? OR user_id IS NULL ORDER BY created_at DESC",
        (uid,), use_cache=False
    )
    return {"success": True, "decks": rows or []}


@router.get("/{deck_id}")
async def get_deck(deck_id: int):
    rows = execute_query("SELECT * FROM APP_AI_Decks WHERE id=?", (deck_id,), use_cache=False)
    if not rows:
        raise HTTPException(404, "Deck non trouvé")
    deck = dict(rows[0])
    deck['slides'] = json.loads(deck.get('slides_json') or '[]')
    deck.pop('slides_json', None)
    return {"success": True, "deck": deck}


@router.put("/{deck_id}")
async def update_deck(deck_id: int, req: UpdateDeckRequest):
    from ..database_unified import write_central as _wc
    parts, params = ["updated_at=GETDATE()"], []
    if req.slides is not None:
        parts.append("slides_json=?")
        params.append(json.dumps(req.slides, ensure_ascii=False, default=_json_serial))
    if req.title:
        parts.append("title=?"); params.append(req.title)
    params.append(deck_id)
    _wc(f"UPDATE APP_AI_Decks SET {', '.join(parts)} WHERE id=?", tuple(params))
    return {"success": True}


@router.post("/{deck_id}/slide/{slide_idx}/generate")
async def generate_slide(
    deck_id:   int,
    slide_idx: int,
    dwh_code:  Optional[str] = Header(None, alias="X-DWH-Code"),
):
    """Génère narration + recommandation pour un slide avec les données réelles du DWH."""
    from ..services.ai_provider import get_ai_provider, AIMessage

    rows = execute_query("SELECT * FROM APP_AI_Decks WHERE id=?", (deck_id,), use_cache=False)
    if not rows: raise HTTPException(404, "Deck non trouvé")

    deck  = rows[0]
    slides = json.loads(deck.get('slides_json') or '[]')
    if slide_idx >= len(slides): raise HTTPException(404, "Slide non trouvé")

    slide        = dict(slides[slide_idx])
    effective_dwh = dwh_code or deck.get('dwh_code')

    # ── Récupérer les données ──────────────────────────────────────────────
    data, columns = [], []
    if slide.get('datasource_id'):
        data, columns = _fetch_data(int(slide['datasource_id']), effective_dwh)

    slide['data']    = data
    slide['columns'] = columns

    # ── Générer narration + recommandation ────────────────────────────────
    provider = get_ai_provider()
    if provider and data:
        sample = json.dumps(data[:10], default=_json_serial, ensure_ascii=False)
        numeric_cols = [k for k, v in data[0].items()
                        if isinstance(v, (int, float, decimal.Decimal)) and not isinstance(v, bool)]
        text_cols    = [k for k in data[0].keys() if k not in numeric_cols]

        prompt = f"""Tu es un expert en analyse de données commerciales.

Slide : "{slide['title']}"
Focus : {slide.get('focus', '')}
Données réelles ({len(data)} lignes) — échantillon :
{sample}

Colonnes catégorielles : {text_cols}
Colonnes numériques : {numeric_cols}

Génère en JSON :
{{
  "narration": "Analyse narrative de 3 à 5 phrases professionnelles. Cite des chiffres précis. Identifie les tendances, les écarts et les faits saillants.",
  "recommendation": "1 à 2 recommandations concrètes et actionnables avec des indicateurs mesurables. Commence par un verbe d'action (Ex: Renforcer..., Prioriser..., Allouer...)."
}}"""

        try:
            raw = await provider.chat([
                AIMessage("system", "Tu génères uniquement du JSON valide."),
                AIMessage("user", prompt)
            ])
            raw = raw.strip()
            if "```json" in raw: raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:   raw = raw.split("```")[1].split("```")[0].strip()
            ai_content = json.loads(raw)
            slide['narration']      = ai_content.get('narration', '')
            slide['recommendation'] = ai_content.get('recommendation', '')
        except Exception as e:
            logger.warning(f"AI narration error slide {slide_idx}: {e}")
            slide['narration']      = f"Ce slide présente {len(data)} entrées sur {len(columns)} indicateurs."
            slide['recommendation'] = "Analyser les données pour identifier les leviers d'optimisation."
    elif not data and slide.get('viz_type') == 'none':
        # Slide sans données (ex: recommandations finales)
        if provider:
            try:
                deck_title = deck.get('title', '')
                all_slides_summary = " | ".join(
                    s.get('title','') for s in slides if s.get('title')
                )
                prompt2 = f"""Tu es un expert en stratégie commerciale.
Présentation : "{deck_title}"
Slides de la présentation : {all_slides_summary}

Slide actuel : "{slide['title']}" — {slide.get('description', '')}

Génère en JSON :
{{
  "narration": "Introduction ou contexte de ce slide (2-3 phrases synthétiques).",
  "recommendation": "3 recommandations prioritaires et actionnables basées sur l'ensemble de la présentation."
}}"""
                raw = await provider.chat([
                    AIMessage("system", "Tu génères uniquement du JSON valide."),
                    AIMessage("user", prompt2)
                ])
                raw = raw.strip()
                if "```json" in raw: raw = raw.split("```json")[1].split("```")[0].strip()
                elif "```" in raw:   raw = raw.split("```")[1].split("```")[0].strip()
                ai2 = json.loads(raw)
                slide['narration']      = ai2.get('narration', '')
                slide['recommendation'] = ai2.get('recommendation', '')
            except Exception:
                slide['narration']      = slide.get('description', '')
                slide['recommendation'] = "Définir les prochaines étapes et les responsabilités."
    else:
        slide['narration']      = slide.get('description', '')
        slide['recommendation'] = "Données non disponibles — vérifier la configuration de la source."

    slide['status'] = 'ready'
    slides[slide_idx] = slide

    from ..database_unified import write_central as _wc
    _wc("UPDATE APP_AI_Decks SET slides_json=?, updated_at=GETDATE() WHERE id=?",
        (json.dumps(slides, ensure_ascii=False, default=_json_serial), deck_id))

    return {"success": True, "slide": slide}


@router.post("/{deck_id}/slide/{slide_idx}/chat")
async def slide_chat(
    deck_id:   int,
    slide_idx: int,
    req:       SlideChatRequest,
    dwh_code:  Optional[str] = Header(None, alias="X-DWH-Code"),
):
    """Chat interactif pour affiner un slide spécifique."""
    from ..services.ai_provider import get_ai_provider, AIMessage

    rows = execute_query("SELECT * FROM APP_AI_Decks WHERE id=?", (deck_id,), use_cache=False)
    if not rows: raise HTTPException(404, "Deck non trouvé")

    slides = json.loads(rows[0].get('slides_json') or '[]')
    if slide_idx >= len(slides): raise HTTPException(404, "Slide non trouvé")

    slide    = dict(slides[slide_idx])
    data     = slide.get('data', [])
    cols     = list(data[0].keys()) if data else []
    num_cols = [k for k in cols if data and isinstance(data[0][k], (int, float, decimal.Decimal))]

    provider = get_ai_provider()
    if not provider: raise HTTPException(503, "IA non configurée.")

    system_ctx = f"""Tu es un assistant expert qui aide à affiner un slide de présentation.

CONTEXTE DU SLIDE :
Titre : {slide['title']}
Narration : {slide.get('narration', '')}
Recommandation : {slide.get('recommendation', '')}
Visualisation : {slide.get('viz_type', 'none')} / {slide.get('chart_type', '')}
Données : {len(data)} lignes — Colonnes : {cols}
Colonnes numériques : {num_cols}

L'utilisateur peut demander : modifier la narration, changer le type de viz, expliquer les données,
filtrer/grouper, changer le type de graphique, simplifier le texte, etc.

Réponds TOUJOURS en JSON strict :
{{
  "reply": "Réponse courte et directe (1-2 phrases)",
  "narration": "narration complète mise à jour, ou null si inchangée",
  "recommendation": "recommandation mise à jour, ou null si inchangée",
  "viz_type": "chart|grid|pivot|none si changé, sinon null",
  "chart_type": "bar|line|area|pie si changé, sinon null"
}}"""

    messages = [AIMessage("system", system_ctx)]
    for m in req.chat_history[-8:]:
        messages.append(AIMessage(m.get('role', 'user'), m.get('content', '')))
    messages.append(AIMessage("user", req.message))

    try:
        raw = await provider.chat(messages)
        raw = raw.strip()
        if "```json" in raw: raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:   raw = raw.split("```")[1].split("```")[0].strip()
        result = json.loads(raw)

        updated = False
        for field, target in [('narration','narration'),('recommendation','recommendation'),
                               ('viz_type','viz_type'),('chart_type','chart_type')]:
            if result.get(field):
                slide[target] = result[field]; updated = True

        if updated:
            slides[slide_idx] = slide
            from ..database_unified import write_central as _wc
            _wc("UPDATE APP_AI_Decks SET slides_json=?, updated_at=GETDATE() WHERE id=?",
                (json.dumps(slides, ensure_ascii=False, default=_json_serial), deck_id))

        return {"success": True, "reply": result.get('reply',''), "slide": slide if updated else None}
    except Exception as e:
        raise HTTPException(500, f"Erreur chat: {e}")


@router.delete("/{deck_id}")
async def delete_deck(deck_id: int):
    from ..database_unified import write_central as _wc
    _wc("DELETE FROM APP_AI_Decks WHERE id=?", (deck_id,))
    return {"success": True}
