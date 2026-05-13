"""Service WhatsApp Business — Meta Cloud API + 360dialog BSP.

Supporte deux providers :
  - "meta"      : Meta Cloud API directe (graph.facebook.com)
  - "360dialog" : 360dialog BSP (waba-v2.360dialog.io) — 1 seule clé API

La sélection se fait via la variable WA_PROVIDER dans .env.
"""
import hashlib
import hmac
import json
import logging
import re
import unicodedata
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple

logger = logging.getLogger(__name__)

GRAPH_API_BASE         = "https://graph.facebook.com"
DIALOG360_BASE         = "https://waba-v2.360dialog.io"
DIALOG360_SANDBOX_BASE = "https://waba-sandbox.360dialog.io"


# ═══════════════════════════════════════════════════════════════════════════════
# HTTP helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _http_request(
    method: str,
    url: str,
    headers: dict,
    data: Optional[dict] = None,
    timeout: int = 15,
) -> dict:
    """Requête HTTP générique (utilisée par Meta et 360dialog)."""
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        logger.error(f"WhatsApp API {e.code}: {error_body}")
        return {"error": {"code": e.code, "message": error_body}}
    except Exception as e:
        logger.error(f"WhatsApp API error: {e}")
        return {"error": {"message": str(e)}}


def _meta_headers(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}


def _360dialog_headers(api_key: str) -> dict:
    return {"D360-API-KEY": api_key, "Content-Type": "application/json"}


def _get_provider_config():
    """Retourne (provider, base_url, headers, phone_number_id) selon le .env."""
    from app.config import get_settings
    s = get_settings()
    provider = getattr(s, "WA_PROVIDER", "meta").lower()
    if provider == "360dialog":
        api_key = getattr(s, "WA_360DIALOG_API_KEY", "")
        is_sandbox = getattr(s, "WA_360DIALOG_SANDBOX", True)
        base = DIALOG360_SANDBOX_BASE if is_sandbox else DIALOG360_BASE
        phone_id = getattr(s, "WA_PHONE_NUMBER_ID", "")
        return "360dialog", base, _360dialog_headers(api_key), phone_id
    else:
        token = s.WA_ACCESS_TOKEN
        phone_id = s.WA_PHONE_NUMBER_ID
        version = s.WA_API_VERSION
        base = f"{GRAPH_API_BASE}/{version}"
        return "meta", base, _meta_headers(token), phone_id


def _graph_request(
    method: str,
    url: str,
    access_token: str,
    data: Optional[dict] = None,
    timeout: int = 15,
) -> dict:
    """Requête HTTP vers le Graph API Meta (compatibilité interne)."""
    return _http_request(method, url, _meta_headers(access_token), data, timeout)


# ═══════════════════════════════════════════════════════════════════════════════
# Envoi de messages
# ═══════════════════════════════════════════════════════════════════════════════

def _send_wa_payload(to: str, payload: dict) -> dict:
    """Envoie un payload WhatsApp (text, interactive, etc.) via le provider configuré."""
    provider, base, headers, pid = _get_provider_config()
    payload["messaging_product"] = "whatsapp"
    payload["recipient_type"] = "individual"
    payload["to"] = to

    if provider == "360dialog":
        url = f"{base}/v1/messages"
        result = _http_request("POST", url, headers, payload)
    else:
        from app.config import get_settings
        s = get_settings()
        url = f"{GRAPH_API_BASE}/{s.WA_API_VERSION}/{pid}/messages"
        result = _http_request("POST", url, headers, payload)

    if "messages" in result:
        return {"success": True, "message_id": result["messages"][0].get("id", "")}
    return {"success": False, "error": result.get("error", {}).get("message", "Erreur envoi")}


def send_text_message(
    phone_number_id: str,
    access_token: str,
    to: str,
    text: str,
    api_version: str = "v21.0",
) -> dict:
    """Envoie un message texte (auto-détecte le provider via .env)."""
    return _send_wa_payload(to, {
        "type": "text",
        "text": {"preview_url": False, "body": text},
    })


def send_interactive_buttons(to: str, body: str, buttons: List[dict],
                              header: str = "", footer: str = "") -> dict:
    """Envoie un message interactif avec boutons de réponse rapide (max 3).

    buttons : [{"id": "btn_ca", "title": "CA du mois"}]
    """
    interactive: dict = {
        "type": "button",
        "body": {"text": body},
        "action": {
            "buttons": [
                {"type": "reply", "reply": {"id": b["id"], "title": b["title"][:20]}}
                for b in buttons[:3]
            ],
        },
    }
    if header:
        interactive["header"] = {"type": "text", "text": header}
    if footer:
        interactive["footer"] = {"text": footer}
    return _send_wa_payload(to, {"type": "interactive", "interactive": interactive})


def send_interactive_list(to: str, body: str, button_text: str,
                          sections: List[dict], header: str = "",
                          footer: str = "") -> dict:
    """Envoie un message interactif avec liste déroulante (max 10 items).

    sections : [{
        "title": "Section 1",
        "rows": [{"id": "row_1", "title": "Titre", "description": "Desc"}]
    }]
    """
    interactive: dict = {
        "type": "list",
        "body": {"text": body},
        "action": {
            "button": button_text[:20],
            "sections": sections,
        },
    }
    if header:
        interactive["header"] = {"type": "text", "text": header}
    if footer:
        interactive["footer"] = {"text": footer}
    return _send_wa_payload(to, {"type": "interactive", "interactive": interactive})


def send_template_message(
    phone_number_id: str,
    access_token: str,
    to: str,
    template_name: str,
    language_code: str = "fr",
    components: Optional[list] = None,
    api_version: str = "v21.0",
) -> dict:
    """Envoie un message template pré-approuvé via WhatsApp Cloud API."""
    url = f"{GRAPH_API_BASE}/{api_version}/{phone_number_id}/messages"
    template = {"name": template_name, "language": {"code": language_code}}
    if components:
        template["components"] = components
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": template,
    }
    result = _graph_request("POST", url, access_token, payload)
    if "messages" in result:
        return {"success": True, "message_id": result["messages"][0].get("id", "")}
    return {"success": False, "error": result.get("error", {}).get("message", "Unknown error")}


def send_document_message(
    phone_number_id: str,
    access_token: str,
    to: str,
    document_url: str,
    filename: str,
    caption: str = "",
    api_version: str = "v21.0",
) -> dict:
    """Envoie un document (PDF, Excel...) via WhatsApp Cloud API."""
    url = f"{GRAPH_API_BASE}/{api_version}/{phone_number_id}/messages"
    doc = {"link": document_url, "filename": filename}
    if caption:
        doc["caption"] = caption
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "document",
        "document": doc,
    }
    result = _graph_request("POST", url, access_token, payload)
    if "messages" in result:
        return {"success": True, "message_id": result["messages"][0].get("id", "")}
    return {"success": False, "error": result.get("error", {}).get("message", "Unknown error")}


def mark_as_read(
    phone_number_id: str,
    access_token: str,
    message_id: str,
    api_version: str = "v21.0",
) -> bool:
    """Marque un message reçu comme lu (double coche bleue)."""
    url = f"{GRAPH_API_BASE}/{api_version}/{phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
    }
    result = _graph_request("POST", url, access_token, payload)
    return result.get("success", False)


# ═══════════════════════════════════════════════════════════════════════════════
# Validation webhook
# ═══════════════════════════════════════════════════════════════════════════════

def verify_webhook_signature(payload_bytes: bytes, signature_header: str, app_secret: str) -> bool:
    """Valide la signature X-Hub-Signature-256 du webhook Meta."""
    if not signature_header or not app_secret:
        return False
    expected = "sha256=" + hmac.new(
        app_secret.encode(), payload_bytes, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def extract_messages(webhook_body: dict) -> List[Dict[str, Any]]:
    """Extrait les messages entrants du payload webhook Meta/360dialog.

    Retourne une liste de dicts : {from, message_id, timestamp, type, text, ...}
    """
    messages = []
    for entry in webhook_body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            if value.get("messaging_product") != "whatsapp":
                continue
            contacts = {
                c["wa_id"]: c.get("profile", {}).get("name", "")
                for c in value.get("contacts", [])
            }
            for msg in value.get("messages", []):
                parsed = {
                    "from": msg.get("from", ""),
                    "name": contacts.get(msg.get("from", ""), ""),
                    "message_id": msg.get("id", ""),
                    "timestamp": msg.get("timestamp", ""),
                    "type": msg.get("type", ""),
                }
                mtype = msg.get("type", "")
                if mtype == "text":
                    parsed["text"] = msg.get("text", {}).get("body", "")
                elif mtype == "interactive":
                    interactive = msg.get("interactive", {})
                    itype = interactive.get("type", "")
                    if itype == "button_reply":
                        parsed["text"] = interactive.get("button_reply", {}).get("id", "")
                        parsed["button_title"] = interactive.get("button_reply", {}).get("title", "")
                    elif itype == "list_reply":
                        parsed["text"] = interactive.get("list_reply", {}).get("id", "")
                        parsed["list_title"] = interactive.get("list_reply", {}).get("title", "")
                elif mtype in ("audio", "voice"):
                    parsed["text"] = "[audio]"
                elif mtype == "image":
                    parsed["text"] = "[image]"
                elif mtype == "document":
                    parsed["text"] = "[document]"
                elif mtype == "location":
                    parsed["text"] = "[location]"
                elif mtype == "sticker":
                    parsed["text"] = "[sticker]"
                else:
                    parsed["text"] = f"[{mtype}]"
                messages.append(parsed)
    return messages


# ═══════════════════════════════════════════════════════════════════════════════
# Formatage nombres
# ═══════════════════════════════════════════════════════════════════════════════

def _fmt(n, decimals: int = 0) -> str:
    """Formate un nombre à la française : 1 234 567,89 MAD."""
    if n is None:
        return "0"
    n = float(n)
    if decimals == 0:
        formatted = f"{n:,.0f}"
    else:
        formatted = f"{n:,.{decimals}f}"
    # Remplacer , par espace et . par , pour le format français
    formatted = formatted.replace(",", " ").replace(".", ",")
    return formatted


def _fmt_mad(n) -> str:
    """Formate un montant en MAD : 1 234 567 MAD."""
    return f"{_fmt(n)} MAD"


def _pct(current, previous) -> str:
    """Calcule et formate la variation en pourcentage."""
    if not previous or float(previous) == 0:
        return "—"
    current = float(current or 0)
    previous = float(previous or 0)
    pct = ((current - previous) / abs(previous)) * 100
    arrow = "📈" if pct > 0 else "📉" if pct < 0 else "➡️"
    sign = "+" if pct > 0 else ""
    return f"{arrow} {sign}{pct:.1f}%"


# Noms de mois courts et longs (index 1-12)
MOIS_COURT = ["", "Jan", "Fév", "Mar", "Avr", "Mai", "Jun",
              "Jul", "Aoû", "Sep", "Oct", "Nov", "Déc"]
MOIS_LONG  = ["", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
              "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]


# ═══════════════════════════════════════════════════════════════════════════════
# NLP — Normalisation + Extraction
# ═══════════════════════════════════════════════════════════════════════════════

MOIS_FR = {
    "janvier": 1, "février": 2, "fevrier": 2, "mars": 3,
    "avril": 4, "mai": 5, "juin": 6, "juillet": 7,
    "août": 8, "aout": 8, "septembre": 9, "octobre": 10,
    "novembre": 11, "décembre": 12, "decembre": 12,
    "jan": 1, "fev": 2, "mar": 3, "avr": 4,
    "jui": 6, "jul": 7, "aou": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _normalize(text: str) -> str:
    """Normalise le texte : minuscules, sans accents, sans ponctuation superflue."""
    text = text.lower().strip()
    text = ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )
    # Supprimer ponctuation sauf / et - (utiles pour dates)
    text = re.sub(r"[?!.,;:'\"]", "", text)
    return text


def _extract_date_from_text(text: str) -> Tuple[Optional[int], Optional[int]]:
    """Extrait (année, mois) depuis du texte libre.

    Exemples supportés :
      "ca 05/2025", "CA mai 2025", "ca mois en cours", "ventes 2025",
      "ca mois dernier", "ca hier", "ca aujourd'hui"
    Retourne (year, month) ou (year, None) ou (None, None).
    """
    now = datetime.now()
    t = _normalize(text)

    # Pattern "mois dernier" / "mois précédent"
    if any(k in t for k in ("mois dernier", "mois precedent", "mois passe")):
        if now.month == 1:
            return now.year - 1, 12
        return now.year, now.month - 1

    # Pattern "cette année" / "année en cours"
    if any(k in t for k in ("cette annee", "annee en cours", "annee courante")):
        return now.year, None

    # Pattern "année dernière" / "année précédente"
    if any(k in t for k in ("annee derniere", "annee precedente", "annee passee")):
        return now.year - 1, None

    # Pattern "aujourd'hui" / "ce jour"
    if any(k in t for k in ("aujourd", "ce jour", "today")):
        return now.year, now.month

    # Pattern MM/YYYY ou MM-YYYY
    m = re.search(r'\b(\d{1,2})[/\-](\d{4})\b', t)
    if m:
        return int(m.group(2)), int(m.group(1))

    # Pattern YYYY/MM
    m = re.search(r'\b(\d{4})[/\-](\d{1,2})\b', t)
    if m:
        return int(m.group(1)), int(m.group(2))

    # Pattern mois-texte + année
    for nom, num in MOIS_FR.items():
        if nom in t:
            yr = re.search(r'\b(20\d{2})\b', t)
            year = int(yr.group(1)) if yr else now.year
            return year, num

    # Juste une année
    m = re.search(r'\b(20\d{2})\b', t)
    if m:
        return int(m.group(1)), None

    # Mots-clés "mois en cours" / "ce mois"
    if any(k in t for k in ("mois en cours", "ce mois", "mois courant", "actuel")):
        return now.year, now.month

    return None, None


# ── Mots-clés non-client (à retirer pour extraire le nom de client) ──
_STOP_WORDS = {
    # Intent keywords
    "ca", "chiffre", "chiffres", "affaires", "affaire", "vente", "ventes",
    "revenu", "revenue", "revenues", "c.a", "chiff",
    "facture", "factures", "fac", "liste", "listes",
    "montant", "montants", "total", "totaux", "somme",
    "top", "top5", "top10", "meilleur", "meilleurs", "classement", "palmares",
    "premier", "premiers", "client", "clients", "fiche",
    "stock", "stocks", "rupture", "inventaire", "critique", "manque", "quantite",
    "impaye", "impayes", "creance", "creances", "balance", "agee", "age",
    "dette", "dettes", "recouvrement", "recouvr",
    "article", "articles", "produit", "produits", "ref", "reference",
    "comparatif", "comparaison", "evolution", "vs", "versus", "rapport",
    "aide", "help", "menu", "commande", "commandes",
    # Fillers
    "la", "le", "les", "un", "une", "des", "de", "du", "d", "l",
    "a", "au", "aux", "en", "et", "ou", "par", "pour", "avec", "dans",
    "sur", "ce", "cette", "ces", "mon", "ma", "mes", "son", "sa", "ses",
    "quel", "quelle", "quels", "quelles", "qui", "que", "quoi",
    "est", "sont", "fait", "faire", "donne", "donner", "donnes", "moi",
    "combien", "nombre", "cherche", "chercher", "trouve", "trouver",
    "voir", "affiche", "afficher", "montre", "montrer",
    "mois", "annee", "dernier", "derniere", "precedent", "actuel",
    "courant", "cours",
}


def _extract_client_name(original_text: str) -> Optional[str]:
    """Extrait un nom de client depuis le texte original.

    Stratégie :
    1. Cherche les mots en MAJUSCULES (>=2 lettres) -> très probable nom client
    2. Sinon, mots capitalisés non-clés (ex: "Bentayeb", "Touhama")
    3. Sinon, après retrait des mots-clés connus, ce qui reste est le nom
    Retourne None si aucun nom détecté.
    """
    # ── Stratégie 1 : mots tout en majuscules (ex: "BENTAYEB", "GOULAMI") ──
    upper_words = re.findall(r'\b([A-ZÀ-Ü]{2,})\b', original_text)
    upper_stop = {"CA", "TTC", "HT", "MAD", "TOP", "FAC", "BL", "DWH",
                  "VS", "PDF", "OK", "KO", "SMS"}
    upper_candidates = [w for w in upper_words if w not in upper_stop]
    if upper_candidates:
        return " ".join(upper_candidates)

    # ── Stratégie 2 : mots capitalisés non-clés (ex: "Bentayeb", "Touhama") ──
    capitalized = re.findall(r'\b([A-ZÀ-Ü][a-zà-ü]{2,})\b', original_text)
    cap_stop = {
        "Jan", "Fev", "Mar", "Avr", "Mai", "Jun", "Jul", "Aou",
        "Sep", "Oct", "Nov", "Dec", "Janvier", "Fevrier", "Mars",
        "Avril", "Juin", "Juillet", "Septembre", "Octobre",
        "Novembre", "Decembre", "Les", "Des", "Pour", "Dans",
        "Sur", "Mon", "Ton", "Son", "Une", "Qui", "Que",
        "Quel", "Quelle", "Stock", "Vente", "Ventes",
        "Chiffre", "Facture", "Factures", "Liste", "Montant",
        "Total", "Client", "Clients", "Top", "Balance",
        "Aide", "Menu", "Bonjour", "Salut", "Article",
        "Comparatif", "Rapport", "Fiche",
    }
    cap_candidates = [w for w in capitalized if w not in cap_stop]
    if cap_candidates:
        return " ".join(cap_candidates)

    # ── Stratégie 3 : retirer tous les mots-clés, garder le reste ──
    t = _normalize(original_text)
    t = re.sub(r'\b\d{1,2}[/\-]\d{4}\b', '', t)
    t = re.sub(r'\b\d{4}\b', '', t)
    for mois in MOIS_FR:
        t = t.replace(mois, '')
    words = t.split()
    remaining = [w for w in words if w not in _STOP_WORDS and len(w) >= 2]
    if remaining:
        candidate = " ".join(remaining)
        if len(candidate) >= 2 and not candidate.isdigit():
            return candidate

    return None


# ═══════════════════════════════════════════════════════════════════════════════
# NLP — Détection d'intent
# ═══════════════════════════════════════════════════════════════════════════════

def _intent_ca(t: str) -> bool:
    kw = ["ca ", " ca", "chiffre", "vente", "ventes", "chiff", "c.a", "revenue", "revenu"]
    return any(k in t for k in kw) or t.strip() == "ca"


def _intent_factures(t: str) -> bool:
    kw = ["facture", "factures", " fac ", "fac "]
    return any(k in t for k in kw) or t.strip().startswith("fac ")


def _intent_top(t: str) -> bool:
    kw = ["top", "meilleur", "classement", "palmar", "premier"]
    return any(k in t for k in kw)


def _intent_stock(t: str) -> bool:
    kw = ["stock", "rupture", "inventaire", "manque"]
    return any(k in t for k in kw)


def _intent_impayes(t: str) -> bool:
    kw = ["impaye", "impayes", "creance", "balance agee", "balance age",
          "dette", "recouvr", "echeance echue", "echeances"]
    return any(k in t for k in kw)


def _intent_article(t: str) -> bool:
    kw = ["article", "produit", "reference", "ref "]
    return any(k in t for k in kw)


def _intent_client(t: str) -> bool:
    """Intent 'fiche client' — différent de juste un nom de client."""
    kw = ["fiche client", "fiche du client", "info client", "detail client",
          "details client", "profil client"]
    return any(k in t for k in kw)


def _intent_comparatif(t: str) -> bool:
    kw = ["comparatif", "comparaison", "compare", "evolution", "vs ",
          "versus", "par rapport", "variation"]
    return any(k in t for k in kw)


def _intent_aide(t: str) -> bool:
    kw = ["aide", "help", "menu", "start", "bonjour", "salut", "hi", "hello",
          "commande", "que peux", "que sais"]
    return any(k in t for k in kw)


def _is_non_text_msg(t: str) -> bool:
    """Détecte les messages non-texte (audio, image, etc.)."""
    return t.startswith("[") and t.endswith("]") and t in (
        "[audio]", "[image]", "[document]", "[location]", "[sticker]", "[video]"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# NLP — Routeur principal
# ═══════════════════════════════════════════════════════════════════════════════

def process_bot_command(text: str, dwh_code: str, contact_name: str = "") -> str:
    """Traite un message en langage naturel et retourne la réponse.

    Priorité des intents :
    1. Messages non-texte (audio, image, etc.)
    2. Boutons interactifs (id commence par btn_)
    3. Aide / salutations
    4. Fiche client (fiche client X)
    5. Factures d'un client
    6. Recherche article
    7. Comparatif CA
    8. CA d'un client spécifique
    9. CA global
    10. Top clients
    11. Stock critique
    12. Impayés
    13. Nom de client seul → CA du client
    """
    # ── Messages non-texte ──
    if _is_non_text_msg(text):
        return (
            "Je ne peux traiter que les messages texte pour le moment. 📝\n\n"
            "Envoyez *aide* pour voir les commandes disponibles."
        )

    t = _normalize(text)

    # ── Réponses aux boutons interactifs ──
    if text.startswith("btn_"):
        return _handle_button_reply(text, dwh_code)

    client_name = _extract_client_name(text)
    year, month = _extract_date_from_text(t)

    # ── Aide / salutations ──
    if _intent_aide(t) and not any([
        _intent_ca(t), _intent_stock(t), _intent_impayes(t),
        _intent_factures(t), _intent_top(t), _intent_article(t),
        _intent_comparatif(t), client_name
    ]):
        return _cmd_aide(contact_name)

    # ── Fiche client complète ──
    if _intent_client(t) and client_name:
        return _cmd_fiche_client(dwh_code, client_name, year=year)

    # ── Factures d'un client ──
    if _intent_factures(t) and client_name:
        return _cmd_factures_client(dwh_code, client_name, year=year, month=month)
    if _intent_factures(t) and not _intent_impayes(t):
        return _cmd_ca(dwh_code, year=year, month=month)

    # ── Recherche article ──
    if _intent_article(t):
        article_name = client_name  # réutilise l'extraction de nom
        if article_name:
            return _cmd_article(dwh_code, article_name)
        return "Précisez le nom ou code de l'article.\nEx: *article BOIS BLANC*"

    # ── Comparatif CA ──
    if _intent_comparatif(t):
        return _cmd_comparatif(dwh_code, year=year, month=month)

    # ── CA d'un client ──
    if _intent_ca(t) and client_name:
        return _cmd_ca_client(dwh_code, client_name, year=year, month=month)

    # ── CA global ──
    if _intent_ca(t):
        return _cmd_ca(dwh_code, year=year, month=month)

    # ── Top clients ──
    if _intent_top(t):
        return _cmd_top5(dwh_code, year=year, month=month)

    # ── Stock critique ──
    if _intent_stock(t):
        return _cmd_stock_critique(dwh_code)

    # ── Impayés / balance âgée ──
    if _intent_impayes(t):
        return _cmd_impayes(dwh_code)

    # ── Nom de client seul → CA du client ──
    if client_name:
        return _cmd_ca_client(dwh_code, client_name, year=year, month=month)

    return (
        f"Je n'ai pas compris *\"{text}\"* 🤔\n\n"
        "Essayez :\n"
        "  📊 *ca* ou *ca 2025*\n"
        "  👤 *ca BENTAYEB 2025*\n"
        "  📄 *factures Touhama*\n"
        "  🔍 *article BOIS*\n"
        "  🏆 *top5* — 📦 *stock* — 💰 *impayes*\n"
        "  📈 *comparatif* — 👤 *fiche client X*\n\n"
        "Envoyez *aide* pour le menu complet."
    )


def _handle_button_reply(btn_id: str, dwh_code: str) -> str:
    """Traite la réponse à un bouton interactif."""
    now = datetime.now()
    handlers = {
        "btn_ca_mois":   lambda: _cmd_ca(dwh_code, year=now.year, month=now.month),
        "btn_ca_annee":  lambda: _cmd_ca(dwh_code, year=now.year, month=None),
        "btn_top5":      lambda: _cmd_top5(dwh_code, year=now.year, month=now.month),
        "btn_stock":     lambda: _cmd_stock_critique(dwh_code),
        "btn_impayes":   lambda: _cmd_impayes(dwh_code),
        "btn_comparatif": lambda: _cmd_comparatif(dwh_code),
        "btn_aide":      lambda: _cmd_aide(""),
    }
    handler = handlers.get(btn_id)
    if handler:
        return handler()
    return "Commande inconnue. Envoyez *aide* pour le menu."


# ═══════════════════════════════════════════════════════════════════════════════
# Commandes bot
# ═══════════════════════════════════════════════════════════════════════════════

def _cmd_aide(contact_name: str = "") -> str:
    """Menu d'aide avec liste des commandes."""
    greeting = f"Bonjour *{contact_name}* ! " if contact_name else ""
    return (
        f"{greeting}Bienvenue sur *OptiBoard Bot* 📊\n\n"
        "Voici ce que je peux faire :\n\n"
        "📊 *Chiffre d'affaires*\n"
        "  _ca, ca 2025, ca mai 2025_\n"
        "  _ca BENTAYEB 2025_\n\n"
        "📄 *Factures client*\n"
        "  _factures BENTAYEB 2025_\n"
        "  _montant factures Touhama_\n\n"
        "👤 *Fiche client*\n"
        "  _fiche client BENTAYEB_\n\n"
        "🔍 *Recherche article*\n"
        "  _article BOIS, article STD_\n\n"
        "📈 *Comparatif CA*\n"
        "  _comparatif, comparatif mai 2025_\n\n"
        "🏆 *Top 5 clients*\n"
        "  _top5, meilleurs clients 2025_\n\n"
        "📦 *Stock critique*\n"
        "  _stock, rupture_\n\n"
        "💰 *Impayés / Créances*\n"
        "  _impayes, balance agee_\n\n"
        "💡 _Astuce : utilisez le langage naturel !_\n"
        "_\"quel est le CA de mai 2025\"_\n"
        "_\"liste des factures BENTAYEB\"_\n"
        "_\"cherche article BOIS BLANC\"_"
    )


def _cmd_ca(dwh_code: str, year: int = None, month: int = None) -> str:
    """Chiffre d'affaires global (avec variation N-1)."""
    from app.database_unified import execute_dwh
    try:
        now = datetime.now()
        y = year or now.year
        m = month or now.month

        if year and not month:
            # CA annuel + comparatif N-1
            rows = execute_dwh(
                """
                SELECT
                    SUM([Montant HT Net]) AS ca_ht,
                    SUM([Montant TTC Net]) AS ca_ttc,
                    COUNT(DISTINCT [Code client]) AS nb_clients,
                    COUNT(DISTINCT [N° Pièce]) AS nb_pieces
                FROM [dbo].[Lignes_des_ventes]
                WHERE [Valorise CA] = 'oui' AND YEAR([Date BL]) = ?
                """,
                (y,), dwh_code=dwh_code, use_cache=True,
            )
            rows_prev = execute_dwh(
                """
                SELECT SUM([Montant HT Net]) AS ca_ht
                FROM [dbo].[Lignes_des_ventes]
                WHERE [Valorise CA] = 'oui' AND YEAR([Date BL]) = ?
                """,
                (y - 1,), dwh_code=dwh_code, use_cache=True,
            )
            label = f"Année {y}"
            prev_label = f"{y - 1}"
        else:
            rows = execute_dwh(
                """
                SELECT
                    SUM([Montant HT Net]) AS ca_ht,
                    SUM([Montant TTC Net]) AS ca_ttc,
                    COUNT(DISTINCT [Code client]) AS nb_clients,
                    COUNT(DISTINCT [N° Pièce]) AS nb_pieces
                FROM [dbo].[Lignes_des_ventes]
                WHERE [Valorise CA] = 'oui'
                  AND YEAR([Date BL]) = ? AND MONTH([Date BL]) = ?
                """,
                (y, m), dwh_code=dwh_code, use_cache=True,
            )
            # CA même mois N-1
            rows_prev = execute_dwh(
                """
                SELECT SUM([Montant HT Net]) AS ca_ht
                FROM [dbo].[Lignes_des_ventes]
                WHERE [Valorise CA] = 'oui'
                  AND YEAR([Date BL]) = ? AND MONTH([Date BL]) = ?
                """,
                (y - 1, m), dwh_code=dwh_code, use_cache=True,
            )
            label = f"{MOIS_COURT[m]} {y}"
            prev_label = f"{MOIS_COURT[m]} {y - 1}"

        if not rows or rows[0].get("ca_ht") is None:
            return f"Aucune vente enregistrée pour {label}."

        r = rows[0]
        ca_ht    = float(r["ca_ht"]  or 0)
        ca_ttc   = float(r["ca_ttc"] or 0)
        nb_cl    = r["nb_clients"] or 0
        nb_pcs   = r["nb_pieces"] or 0
        ca_prev  = float(rows_prev[0]["ca_ht"] or 0) if rows_prev and rows_prev[0].get("ca_ht") else 0
        variation = _pct(ca_ht, ca_prev) if ca_prev else ""

        lines = [f"📊 *CA {label}*\n"]
        lines.append(f"  💵 CA HT  : *{_fmt_mad(ca_ht)}*")
        lines.append(f"  💶 CA TTC : *{_fmt_mad(ca_ttc)}*")
        lines.append(f"  👥 Clients : {nb_cl}  |  📄 Pièces : {nb_pcs}")
        if variation:
            lines.append(f"\n  {variation} vs {prev_label} ({_fmt_mad(ca_prev)})")
        lines.append(f"\n_💡 Tapez *top5* ou *factures NomClient*_")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"WhatsApp bot CA error: {e}")
        return "⚠️ Erreur lors de la récupération du CA."


def _cmd_ca_client(dwh_code: str, client_name: str, year: int = None, month: int = None) -> str:
    """Retourne le CA d'un client spécifique."""
    from app.database_unified import execute_dwh
    try:
        now = datetime.now()
        y = year or now.year
        m = month or now.month
        like = f"%{client_name}%"

        if year and not month:
            rows = execute_dwh(
                """
                SELECT
                    [Intitulé client] AS client,
                    SUM([Montant HT Net]) AS ca_ht,
                    SUM([Montant TTC Net]) AS ca_ttc,
                    COUNT(DISTINCT [N° Pièce]) AS nb_factures,
                    COUNT(*) AS nb_lignes
                FROM [dbo].[Lignes_des_ventes]
                WHERE [Valorise CA] = 'oui'
                  AND [Intitulé client] LIKE ?
                  AND YEAR([Date BL]) = ?
                GROUP BY [Intitulé client]
                """,
                (like, y), dwh_code=dwh_code, use_cache=True,
            )
            label = f"Année {y}"
        else:
            rows = execute_dwh(
                """
                SELECT
                    [Intitulé client] AS client,
                    SUM([Montant HT Net]) AS ca_ht,
                    SUM([Montant TTC Net]) AS ca_ttc,
                    COUNT(DISTINCT [N° Pièce]) AS nb_factures,
                    COUNT(*) AS nb_lignes
                FROM [dbo].[Lignes_des_ventes]
                WHERE [Valorise CA] = 'oui'
                  AND [Intitulé client] LIKE ?
                  AND YEAR([Date BL]) = ? AND MONTH([Date BL]) = ?
                GROUP BY [Intitulé client]
                """,
                (like, y, m), dwh_code=dwh_code, use_cache=True,
            )
            label = f"{MOIS_COURT[m]} {y}"

        if not rows:
            return (
                f"Aucune vente pour *{client_name}* en {label}.\n"
                f"_Vérifiez l'orthographe du client._"
            )

        if len(rows) > 1:
            lines = [f"📊 *CA \"{client_name}\" — {label}*\n"]
            total_ht = 0
            for r in rows[:10]:
                ca_ht = float(r['ca_ht'] or 0)
                total_ht += ca_ht
                lines.append(f"  👤 *{r['client']}*\n     {_fmt_mad(ca_ht)} HT ({r['nb_factures']} pièces)")
            if len(rows) > 10:
                lines.append(f"  _… et {len(rows) - 10} autres_")
            lines.append(f"\n  💰 *Total : {_fmt_mad(total_ht)} HT*")
            return "\n".join(lines)

        r = rows[0]
        ca_ht  = float(r['ca_ht']  or 0)
        ca_ttc = float(r['ca_ttc'] or 0)
        return (
            f"📊 *{r['client']} — {label}*\n\n"
            f"  💵 CA HT  : *{_fmt_mad(ca_ht)}*\n"
            f"  💶 CA TTC : *{_fmt_mad(ca_ttc)}*\n"
            f"  📄 Pièces : {r['nb_factures']} ({r['nb_lignes']} lignes)\n\n"
            f"_💡 Tapez *factures {client_name}* pour le détail_"
        )
    except Exception as e:
        logger.error(f"WhatsApp bot CA client error: {e}")
        return f"⚠️ Erreur lors de la récupération du CA de {client_name}."


def _cmd_factures_client(dwh_code: str, client_name: str, year: int = None, month: int = None) -> str:
    """Liste les factures d'un client spécifique."""
    from app.database_unified import execute_dwh
    try:
        now = datetime.now()
        y = year or now.year
        like = f"%{client_name}%"

        date_filter = "AND YEAR([Date BL]) = ?"
        params: tuple = (like, y)
        if month:
            date_filter = "AND YEAR([Date BL]) = ? AND MONTH([Date BL]) = ?"
            params = (like, y, month)

        rows = execute_dwh(
            f"""
            SELECT TOP 15
                [N° Pièce] AS piece,
                [Intitulé client] AS client,
                [Date BL] AS date_bl,
                [Type Document] AS type_doc,
                SUM([Montant HT Net]) AS montant_ht,
                SUM([Montant TTC Net]) AS montant_ttc,
                COUNT(*) AS nb_lignes
            FROM [dbo].[Lignes_des_ventes]
            WHERE [Valorise CA] = 'oui'
              AND [Intitulé client] LIKE ?
              {date_filter}
            GROUP BY [N° Pièce], [Intitulé client], [Date BL], [Type Document]
            ORDER BY [Date BL] DESC
            """,
            params, dwh_code=dwh_code, use_cache=True,
        )

        if month:
            label = f"{MOIS_COURT[month]} {y}"
        else:
            label = f"Année {y}"

        if not rows:
            return (
                f"Aucune facture pour *{client_name}* en {label}.\n"
                f"_Vérifiez l'orthographe du client._"
            )

        total_ht  = sum(float(r['montant_ht'] or 0) for r in rows)
        total_ttc = sum(float(r['montant_ttc'] or 0) for r in rows)
        client_display = rows[0]['client']

        lines = [f"📄 *Factures {client_display}*\n📅 _{label}_\n"]

        # Grouper par type de document
        type_icons = {"Facture": "🧾", "Avoir": "↩️", "Bon de retour": "📤",
                      "Bon de livraison": "🚚", "Devis": "📝"}

        for r in rows:
            dt = r['date_bl']
            date_str = dt.strftime("%d/%m/%Y") if hasattr(dt, 'strftime') else str(dt)[:10]
            ht = float(r['montant_ht'] or 0)
            icon = type_icons.get(r['type_doc'], "📋")
            lines.append(
                f"  {icon} *{r['piece']}*\n"
                f"     {date_str} · {r['type_doc']} · *{_fmt_mad(ht)}*"
            )

        lines.append(f"\n{'─' * 28}")
        lines.append(f"💰 *Total ({len(rows)} pièces)*")
        lines.append(f"  HT : *{_fmt_mad(total_ht)}*")
        lines.append(f"  TTC : *{_fmt_mad(total_ttc)}*")
        if len(rows) == 15:
            lines.append("\n_⚠️ Limité aux 15 plus récentes_")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"WhatsApp bot factures client error: {e}")
        return f"⚠️ Erreur lors de la récupération des factures de {client_name}."


def _cmd_fiche_client(dwh_code: str, client_name: str, year: int = None) -> str:
    """Fiche synthétique d'un client : CA annuel, nb factures, dernière commande, top articles."""
    from app.database_unified import execute_dwh
    try:
        now = datetime.now()
        year = year or now.year
        like = f"%{client_name}%"

        # CA année demandée
        rows_ca = execute_dwh(
            """
            SELECT
                [Intitulé client] AS client,
                [Code client] AS code,
                SUM([Montant HT Net]) AS ca_ht,
                COUNT(DISTINCT [N° Pièce]) AS nb_pieces,
                MAX([Date BL]) AS derniere_vente
            FROM [dbo].[Lignes_des_ventes]
            WHERE [Valorise CA] = 'oui'
              AND [Intitulé client] LIKE ?
              AND YEAR([Date BL]) = ?
            GROUP BY [Intitulé client], [Code client]
            """,
            (like, year), dwh_code=dwh_code, use_cache=True,
        )
        if not rows_ca:
            return (
                f"Client *{client_name}* non trouvé en {year}.\n"
                "_Vérifiez l'orthographe._"
            )

        rc = rows_ca[0]
        client_display = rc['client']
        code = rc['code']
        ca_ht = float(rc['ca_ht'] or 0)
        nb_pcs = rc['nb_pieces'] or 0
        last_date = rc['derniere_vente']
        last_str = last_date.strftime("%d/%m/%Y") if hasattr(last_date, 'strftime') else "—"

        # CA année précédente pour comparaison
        rows_prev = execute_dwh(
            """
            SELECT SUM([Montant HT Net]) AS ca_ht
            FROM [dbo].[Lignes_des_ventes]
            WHERE [Valorise CA] = 'oui'
              AND [Code client] = ?
              AND YEAR([Date BL]) = ?
            """,
            (code, year - 1), dwh_code=dwh_code, use_cache=True,
        )
        ca_prev = float(rows_prev[0]["ca_ht"] or 0) if rows_prev and rows_prev[0].get("ca_ht") else 0

        # Top 3 articles du client
        rows_art = execute_dwh(
            """
            SELECT TOP 3
                [Désignation ligne] AS article,
                SUM([Montant HT Net]) AS ca
            FROM [dbo].[Lignes_des_ventes]
            WHERE [Valorise CA] = 'oui'
              AND [Code client] = ?
              AND YEAR([Date BL]) = ?
            GROUP BY [Désignation ligne]
            ORDER BY ca DESC
            """,
            (code, year), dwh_code=dwh_code, use_cache=True,
        )

        variation = _pct(ca_ht, ca_prev)
        lines = [
            f"👤 *Fiche Client*\n",
            f"  *{client_display}*",
            f"  Code : {code}\n",
            f"  📊 CA {year} : *{_fmt_mad(ca_ht)}*",
        ]
        if ca_prev:
            lines.append(f"  📊 CA {year - 1} : {_fmt_mad(ca_prev)}")
            lines.append(f"  {variation}")
        lines.append(f"  📄 Pièces : {nb_pcs}")
        lines.append(f"  📅 Dernière vente : {last_str}")

        if rows_art:
            lines.append(f"\n  🏷️ *Top articles {year} :*")
            for i, ra in enumerate(rows_art):
                lines.append(f"     {i+1}. {ra['article']}\n        {_fmt_mad(float(ra['ca'] or 0))}")

        lines.append(f"\n_💡 Tapez *factures {client_name} {year}*_")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"WhatsApp bot fiche client error: {e}")
        return f"⚠️ Erreur lors de la récupération de la fiche {client_name}."


def _cmd_article(dwh_code: str, search: str) -> str:
    """Recherche un article par code ou nom et affiche stock + ventes."""
    from app.database_unified import execute_dwh
    try:
        like = f"%{search}%"

        # Chercher dans Etat_Stock
        rows = execute_dwh(
            """
            SELECT TOP 8
                [Code article] AS code,
                [Désignation article] AS designation,
                [Quantité en stock] AS qte_stock,
                [Quantité minimale] AS seuil_min,
                [Quantité maximale] AS seuil_max
            FROM [dbo].[Etat_Stock]
            WHERE [Code article] LIKE ? OR [Désignation article] LIKE ?
            """,
            (like, like), dwh_code=dwh_code, use_cache=True,
        )

        if not rows:
            return (
                f"Aucun article trouvé pour *\"{search}\"*.\n"
                "_Essayez un autre mot-clé._"
            )

        lines = [f"🔍 *Recherche : \"{search}\"*\n"]
        for r in rows:
            qte  = float(r['qte_stock'] or 0)
            smin = float(r['seuil_min'] or 0)
            # Indicateur de stock
            if smin > 0 and qte < smin:
                stock_icon = "🔴"
            elif smin > 0 and qte < smin * 1.5:
                stock_icon = "🟡"
            else:
                stock_icon = "🟢"

            lines.append(
                f"  {stock_icon} *{r['code']}*\n"
                f"     {r['designation']}\n"
                f"     Stock : {_fmt(qte)} (seuil : {_fmt(smin)})"
            )

        if len(rows) == 8:
            lines.append("\n_⚠️ Résultats limités à 8. Affinez votre recherche._")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"WhatsApp bot article error: {e}")
        return f"⚠️ Erreur lors de la recherche d'article."


def _cmd_comparatif(dwh_code: str, year: int = None, month: int = None) -> str:
    """Comparatif CA mois en cours vs même mois N-1, ou année N vs N-1."""
    from app.database_unified import execute_dwh
    try:
        now = datetime.now()
        y = year or now.year
        m = month or now.month

        if year and not month:
            # Comparatif année complète N vs N-1
            rows = execute_dwh(
                """
                SELECT
                    YEAR([Date BL]) AS annee,
                    SUM([Montant HT Net]) AS ca_ht,
                    COUNT(DISTINCT [Code client]) AS nb_clients,
                    COUNT(DISTINCT [N° Pièce]) AS nb_pieces
                FROM [dbo].[Lignes_des_ventes]
                WHERE [Valorise CA] = 'oui'
                  AND YEAR([Date BL]) IN (?, ?)
                GROUP BY YEAR([Date BL])
                ORDER BY YEAR([Date BL])
                """,
                (y - 1, y), dwh_code=dwh_code, use_cache=True,
            )
            label_n  = f"Année {y}"
            label_n1 = f"Année {y - 1}"
        else:
            # Comparatif mois M, N vs N-1
            rows = execute_dwh(
                """
                SELECT
                    YEAR([Date BL]) AS annee,
                    SUM([Montant HT Net]) AS ca_ht,
                    COUNT(DISTINCT [Code client]) AS nb_clients,
                    COUNT(DISTINCT [N° Pièce]) AS nb_pieces
                FROM [dbo].[Lignes_des_ventes]
                WHERE [Valorise CA] = 'oui'
                  AND MONTH([Date BL]) = ?
                  AND YEAR([Date BL]) IN (?, ?)
                GROUP BY YEAR([Date BL])
                ORDER BY YEAR([Date BL])
                """,
                (m, y - 1, y), dwh_code=dwh_code, use_cache=True,
            )
            label_n  = f"{MOIS_LONG[m]} {y}"
            label_n1 = f"{MOIS_LONG[m]} {y - 1}"

        data = {r['annee']: r for r in rows}
        ca_n  = float(data.get(y, {}).get("ca_ht", 0) or 0)
        ca_n1 = float(data.get(y - 1, {}).get("ca_ht", 0) or 0)
        cl_n  = data.get(y, {}).get("nb_clients", 0) or 0
        cl_n1 = data.get(y - 1, {}).get("nb_clients", 0) or 0
        pc_n  = data.get(y, {}).get("nb_pieces", 0) or 0
        pc_n1 = data.get(y - 1, {}).get("nb_pieces", 0) or 0

        variation = _pct(ca_n, ca_n1)
        var_cl = _pct(cl_n, cl_n1)

        lines = [
            f"📈 *Comparatif CA*\n",
            f"  *{label_n1}*",
            f"  CA HT : {_fmt_mad(ca_n1)}",
            f"  Clients : {cl_n1} · Pièces : {pc_n1}\n",
            f"  *{label_n}*",
            f"  CA HT : *{_fmt_mad(ca_n)}*",
            f"  Clients : {cl_n} · Pièces : {pc_n}\n",
            f"{'─' * 28}",
            f"  {variation}",
            f"  Clients : {var_cl}",
        ]
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"WhatsApp bot comparatif error: {e}")
        return "⚠️ Erreur lors du calcul du comparatif."


def _cmd_top5(dwh_code: str, year: int = None, month: int = None) -> str:
    """Top 5 clients par CA."""
    from app.database_unified import execute_dwh
    try:
        now = datetime.now()
        y = year or now.year
        m = month or now.month

        if year and not month:
            rows = execute_dwh(
                """
                SELECT TOP 5
                    [Intitulé client] AS client,
                    SUM([Montant HT Net]) AS ca,
                    COUNT(DISTINCT [N° Pièce]) AS nb_pieces
                FROM [dbo].[Lignes_des_ventes]
                WHERE [Valorise CA] = 'oui' AND YEAR([Date BL]) = ?
                GROUP BY [Intitulé client] ORDER BY ca DESC
                """,
                (y,), dwh_code=dwh_code, use_cache=True,
            )
            label = f"Année {y}"
        else:
            rows = execute_dwh(
                """
                SELECT TOP 5
                    [Intitulé client] AS client,
                    SUM([Montant HT Net]) AS ca,
                    COUNT(DISTINCT [N° Pièce]) AS nb_pieces
                FROM [dbo].[Lignes_des_ventes]
                WHERE [Valorise CA] = 'oui'
                  AND YEAR([Date BL]) = ? AND MONTH([Date BL]) = ?
                GROUP BY [Intitulé client] ORDER BY ca DESC
                """,
                (y, m), dwh_code=dwh_code, use_cache=True,
            )
            label = f"{MOIS_COURT[m]} {y}"

        if not rows:
            return f"Aucune donnée client pour {label}."

        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        total = sum(float(r['ca'] or 0) for r in rows)

        lines = [f"🏆 *Top 5 Clients — {label}*\n"]
        for i, r in enumerate(rows):
            ca = float(r['ca'] or 0)
            share = (ca / total * 100) if total > 0 else 0
            lines.append(
                f"  {medals[i]} *{r['client']}*\n"
                f"     {_fmt_mad(ca)} ({share:.0f}%)"
            )
        lines.append(f"\n  💰 Total Top 5 : *{_fmt_mad(total)}*")
        lines.append(f"\n_💡 Tapez *factures NomClient* pour le détail_")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"WhatsApp bot top5 error: {e}")
        return "⚠️ Erreur lors de la récupération du top clients."


def _cmd_stock_critique(dwh_code: str) -> str:
    """Articles en stock critique (sous le seuil minimum)."""
    from app.database_unified import execute_dwh
    try:
        # Nombre total d'articles en alerte
        count_rows = execute_dwh(
            """
            SELECT COUNT(*) AS total
            FROM [dbo].[Etat_Stock]
            WHERE [Quantité en stock] < [Quantité minimale]
              AND [Quantité minimale] > 0
            """,
            dwh_code=dwh_code, use_cache=True,
        )
        total_alert = count_rows[0]["total"] if count_rows else 0

        rows = execute_dwh(
            """
            SELECT TOP 10
                [Code article] AS ref,
                [Désignation article] AS designation,
                [Quantité en stock] AS qte,
                [Quantité minimale] AS seuil
            FROM [dbo].[Etat_Stock]
            WHERE [Quantité en stock] < [Quantité minimale]
              AND [Quantité minimale] > 0
            ORDER BY ([Quantité en stock] - [Quantité minimale]) ASC
            """,
            dwh_code=dwh_code, use_cache=True,
        )
        if not rows:
            return "✅ Aucun article en stock critique."

        lines = [f"⚠️ *Stock critique* ({total_alert} articles en alerte)\n"]
        for r in rows:
            qte   = float(r['qte']   or 0)
            seuil = float(r['seuil'] or 0)
            deficit = seuil - qte
            bar = "🔴" if qte == 0 else "🟠"
            lines.append(
                f"  {bar} *{r['ref']}*\n"
                f"     {r['designation']}\n"
                f"     Stock : {_fmt(qte)} / Seuil : {_fmt(seuil)} (manque : {_fmt(deficit)})"
            )
        if total_alert > 10:
            lines.append(f"\n_⚠️ {total_alert - 10} autres articles en alerte_")
        lines.append(f"\n_💡 Tapez *article CODE* pour les détails_")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"WhatsApp bot stock error: {e}")
        return "⚠️ Erreur lors de la récupération des stocks."


def _cmd_impayes(dwh_code: str) -> str:
    """Créances échues non réglées depuis Écheances_Ventes."""
    from app.database_unified import execute_dwh
    table = "Echéances_Ventes"  # é = U+00E9
    try:
        rows = execute_dwh(
            f"""
            SELECT
                COUNT(*) AS nb,
                COUNT(DISTINCT [Code client]) AS nb_clients,
                SUM([Montant échéance] - [Montant du règlement]) AS total_du,
                SUM(CASE
                    WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) BETWEEN 0 AND 30
                    THEN ([Montant échéance] - [Montant du règlement])
                    ELSE 0 END) AS tranche_0_30,
                SUM(CASE
                    WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) BETWEEN 31 AND 60
                    THEN ([Montant échéance] - [Montant du règlement])
                    ELSE 0 END) AS tranche_31_60,
                SUM(CASE
                    WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) BETWEEN 61 AND 90
                    THEN ([Montant échéance] - [Montant du règlement])
                    ELSE 0 END) AS tranche_61_90,
                SUM(CASE
                    WHEN DATEDIFF(DAY, [Date d'échéance], GETDATE()) > 90
                    THEN ([Montant échéance] - [Montant du règlement])
                    ELSE 0 END) AS plus_90j
            FROM [dbo].[{table}]
            WHERE [Montant échéance] > [Montant du règlement]
              AND [Date d'échéance] < GETDATE()
            """,
            dwh_code=dwh_code,
            use_cache=True,
        )
        if not rows or rows[0].get("nb") == 0:
            return "✅ Aucune créance échue non réglée."

        r = rows[0]
        total    = float(r['total_du']    or 0)
        t_0_30   = float(r['tranche_0_30']  or 0)
        t_31_60  = float(r['tranche_31_60'] or 0)
        t_61_90  = float(r['tranche_61_90'] or 0)
        plus_90  = float(r['plus_90j']      or 0)
        nb_cl    = r['nb_clients'] or 0

        lines = [
            f"💰 *Créances échues non réglées*\n",
            f"  📋 Échéances : *{_fmt(r['nb'])}*",
            f"  👥 Clients : *{nb_cl}*",
            f"  💵 Total dû : *{_fmt_mad(total)}*\n",
            f"  ⏱️ *Répartition par ancienneté :*",
            f"     0-30j   : {_fmt_mad(t_0_30)}",
            f"     31-60j  : {_fmt_mad(t_31_60)}",
            f"     61-90j  : {_fmt_mad(t_61_90)}",
            f"     > 90j   : *{_fmt_mad(plus_90)}* 🔴",
        ]
        if total > 0:
            pct_90 = (plus_90 / total * 100) if total else 0
            lines.append(f"\n  ⚠️ {pct_90:.0f}% du total a plus de 90 jours")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"WhatsApp bot impayés error: {e}")
        return (
            "⚠️ Données impayées temporairement indisponibles.\n"
            "_Réessayez dans quelques instants._"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Fonctions de compatibilité
# ═══════════════════════════════════════════════════════════════════════════════

def test_whatsapp_connection(phone_number_id: str, access_token: str, api_version: str = "v21.0") -> dict:
    """Teste la connexion en récupérant les infos du numéro WhatsApp Business."""
    url = f"{GRAPH_API_BASE}/{api_version}/{phone_number_id}"
    result = _graph_request("GET", url, access_token)
    if "error" in result:
        return {"success": False, "error": result["error"].get("message", "Erreur inconnue")}
    return {
        "success": True,
        "phone_number": result.get("display_phone_number", ""),
        "quality_rating": result.get("quality_rating", ""),
        "verified_name": result.get("verified_name", ""),
    }


def build_whatsapp_message(
    report_name: str,
    freq_label: str,
    date_str: str,
    app_name: str = "OptiBoard",
) -> str:
    """Construit le texte du message WhatsApp (compatible ancien format)."""
    return (
        f"*{app_name}* — Rapport Automatique\n\n"
        f"Bonjour,\n\n"
        f"Votre rapport *{report_name}* est prêt.\n\n"
        f"Généré le {date_str}\n"
        f"Fréquence : {freq_label}\n\n"
        f"_Message automatique — {app_name}_"
    )


def send_whatsapp_message(
    account_sid: str,
    auth_token: str,
    from_number: str,
    to_number: str,
    body: str,
) -> bool:
    """Compatibilité Twilio : redirige vers Meta Cloud API si configuré."""
    from app.config import get_settings
    s = get_settings()
    if s.WA_PHONE_NUMBER_ID and s.WA_ACCESS_TOKEN:
        to_clean = to_number.replace("whatsapp:", "").replace("+", "")
        result = send_text_message(s.WA_PHONE_NUMBER_ID, s.WA_ACCESS_TOKEN, to_clean, body, s.WA_API_VERSION)
        return result.get("success", False)
    import base64
    if not all([account_sid, auth_token, from_number, to_number]):
        return False
    try:
        frm = from_number if from_number.startswith("whatsapp:") else f"whatsapp:{from_number}"
        to = to_number if to_number.startswith("whatsapp:") else f"whatsapp:{to_number}"
        credentials = base64.b64encode(f"{account_sid}:{auth_token}".encode()).decode()
        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
        payload = urllib.parse.urlencode({"From": frm, "To": to, "Body": body}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        }, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
            return bool(result.get("sid"))
    except Exception as e:
        logger.error(f"Twilio fallback error: {e}")
        return False
