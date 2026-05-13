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
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

GRAPH_API_BASE        = "https://graph.facebook.com"
DIALOG360_BASE        = "https://waba-v2.360dialog.io"
DIALOG360_SANDBOX_BASE = "https://waba-sandbox.360dialog.io"


# ─── HTTP helpers ───────────────────────────────────────────────────────────────

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


# ─── Envoi de messages ──────────────────────────────────────────────────────────

def _graph_request(
    method: str,
    url: str,
    access_token: str,
    data: Optional[dict] = None,
    timeout: int = 15,
) -> dict:
    """Requête HTTP vers le Graph API Meta (compatibilité interne)."""
    return _http_request(method, url, _meta_headers(access_token), data, timeout)


def send_text_message(
    phone_number_id: str,
    access_token: str,
    to: str,
    text: str,
    api_version: str = "v21.0",
) -> dict:
    """Envoie un message texte (auto-détecte le provider via .env)."""
    provider, base, headers, pid = _get_provider_config()

    if provider == "360dialog":
        # 360dialog : POST /v1/messages
        url = f"{base}/v1/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
        result = _http_request("POST", url, headers, payload)
        # 360dialog renvoie {"messages": [{"id": "..."}]}
        if "messages" in result:
            return {"success": True, "message_id": result["messages"][0].get("id", "")}
        return {"success": False, "error": result.get("error", {}).get("message", "Erreur 360dialog")}

    # Meta Cloud API (comportement original)
    url = f"{GRAPH_API_BASE}/{api_version}/{phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"preview_url": False, "body": text},
    }
    result = _graph_request("POST", url, access_token, payload)
    if "messages" in result:
        msg_id = result["messages"][0].get("id", "")
        logger.info(f"WhatsApp message sent to {to}: {msg_id}")
        return {"success": True, "message_id": msg_id}
    return {"success": False, "error": result.get("error", {}).get("message", "Unknown error")}


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


# ─── Validation webhook ────────────────────────────────────────────────────────

def verify_webhook_signature(payload_bytes: bytes, signature_header: str, app_secret: str) -> bool:
    """Valide la signature X-Hub-Signature-256 du webhook Meta."""
    if not signature_header or not app_secret:
        return False
    expected = "sha256=" + hmac.new(
        app_secret.encode(), payload_bytes, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def extract_messages(webhook_body: dict) -> List[Dict[str, Any]]:
    """Extrait les messages entrants du payload webhook Meta.

    Retourne une liste de dicts : {from, message_id, timestamp, type, text, ...}
    """
    messages = []
    for entry in webhook_body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            if value.get("messaging_product") != "whatsapp":
                continue
            contacts = {c["wa_id"]: c.get("profile", {}).get("name", "") for c in value.get("contacts", [])}
            for msg in value.get("messages", []):
                parsed = {
                    "from": msg.get("from", ""),
                    "name": contacts.get(msg.get("from", ""), ""),
                    "message_id": msg.get("id", ""),
                    "timestamp": msg.get("timestamp", ""),
                    "type": msg.get("type", ""),
                }
                if msg.get("type") == "text":
                    parsed["text"] = msg.get("text", {}).get("body", "")
                elif msg.get("type") == "interactive":
                    interactive = msg.get("interactive", {})
                    itype = interactive.get("type", "")
                    if itype == "button_reply":
                        parsed["text"] = interactive.get("button_reply", {}).get("id", "")
                    elif itype == "list_reply":
                        parsed["text"] = interactive.get("list_reply", {}).get("id", "")
                else:
                    parsed["text"] = f"[{msg.get('type', 'unknown')}]"
                messages.append(parsed)
    return messages


# ─── Bot logic : NLP + traitement des commandes ──────────────────────────────

import re
import unicodedata

COMMANDS = {
    "ca": "Chiffre d'affaires (ex: *ca*, *ca 05/2025*, *CA mai 2025*)",
    "ca CLIENT": "CA d'un client (ex: *ca BENTAYEB 2025*, *ventes Touhama*)",
    "factures CLIENT": "Factures d'un client (ex: *factures BENTAYEB 2025*)",
    "top5": "Top 5 clients par CA (ex: *top5*, *meilleurs clients*)",
    "stock": "Articles en stock critique (ex: *stock*, *rupture*)",
    "impayes": "Créances impayées (ex: *impayes*, *balance âgée*)",
    "aide": "Liste des commandes disponibles",
}

HELP_TEXT = (
    "*OptiBoard Bot* 📊 — Commandes disponibles :\n\n"
    + "\n".join(f"  *{cmd}* — {desc}" for cmd, desc in COMMANDS.items())
    + "\n\n_Exemples :_\n"
    "  _ca, ca 05/2025, ca BENTAYEB 2025_\n"
    "  _factures Touhama, top5, stock, impayes_"
)

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
    # Supprimer les accents
    text = ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )
    return text


def _extract_date_from_text(text: str):
    """Extrait (année, mois) depuis du texte libre.

    Exemples supportés :
      "ca 05/2025", "CA mai 2025", "CA PAR mois 2026", "ca mois en cours",
      "chiffre d affaires mai", "ventes 2025", "ca 05-2025"
    Retourne (year, month) ou (year, None) ou (None, None).
    """
    now = datetime.now()
    t = _normalize(text)

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
            # Chercher une année proche
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
    "top", "top5", "meilleur", "meilleurs", "classement", "palmares",
    "premier", "premiers", "client", "clients",
    "stock", "stocks", "rupture", "inventaire", "critique", "manque", "quantite",
    "impaye", "impayes", "creance", "creances", "balance", "agee", "age",
    "dette", "dettes", "recouvrement", "recouvr",
    "aide", "help", "menu", "commande", "commandes",
    # Fillers
    "la", "le", "les", "un", "une", "des", "de", "du", "d", "l",
    "a", "au", "aux", "en", "et", "ou", "par", "pour", "avec", "dans",
    "sur", "ce", "cette", "ces", "mon", "ma", "mes", "son", "sa", "ses",
    "quel", "quelle", "quels", "quelles", "qui", "que", "quoi",
    "est", "sont", "fait", "faire", "donne", "donner", "moi",
    "combien", "quel", "nombre",
}


def _extract_client_name(original_text: str) -> Optional[str]:
    """Extrait un nom de client depuis le texte original.

    Stratégie :
    1. Cherche les mots en MAJUSCULES (≥2 lettres) → très probable nom client
    2. Sinon, après retrait des mots-clés connus, ce qui reste est le nom
    Retourne None si aucun nom détecté.
    """
    # ── Stratégie 1 : mots tout en majuscules (ex: "BENTAYEB", "GOULAMI") ──
    upper_words = re.findall(r'\b([A-ZÀ-ÖÙ-Ü]{2,})\b', original_text)
    # Filtrer les mots-clés en majuscules (CA, TTC, MAD, HT...)
    upper_stop = {"CA", "TTC", "HT", "MAD", "TOP", "FAC", "BL", "DWH"}
    upper_candidates = [w for w in upper_words if w not in upper_stop]
    if upper_candidates:
        return " ".join(upper_candidates)

    # ── Stratégie 2 : mots capitalisés non-clés (ex: "Bentayeb", "Touhama") ──
    capitalized = re.findall(r'\b([A-ZÀ-ÖÙ-Ü][a-zà-öù-ü]{2,})\b', original_text)
    cap_stop = {"Jan", "Fev", "Mar", "Avr", "Mai", "Jun", "Jul", "Aou",
                "Sep", "Oct", "Nov", "Dec", "Janvier", "Fevrier", "Mars",
                "Avril", "Juin", "Juillet", "Septembre", "Octobre",
                "Novembre", "Decembre", "Les", "Des", "Pour", "Dans",
                "Sur", "Mon", "Ton", "Son", "Une", "Qui", "Que",
                "Quel", "Quelle", "Stock", "Vente", "Ventes",
                "Chiffre", "Facture", "Factures", "Liste", "Montant",
                "Total", "Client", "Clients", "Top", "Balance",
                "Aide", "Menu", "Bonjour", "Salut"}
    cap_candidates = [w for w in capitalized if w not in cap_stop]
    if cap_candidates:
        return " ".join(cap_candidates)

    # ── Stratégie 3 : retirer tous les mots-clés, garder le reste ──
    t = _normalize(original_text)
    # Retirer les dates
    t = re.sub(r'\b\d{1,2}[/\-]\d{4}\b', '', t)
    t = re.sub(r'\b\d{4}\b', '', t)
    for mois in MOIS_FR:
        t = t.replace(mois, '')
    # Retirer les stop words
    words = t.split()
    remaining = [w for w in words if w not in _STOP_WORDS and len(w) >= 2]
    if remaining:
        candidate = " ".join(remaining)
        # Ignorer si c'est juste des chiffres ou trop court
        if len(candidate) >= 2 and not candidate.isdigit():
            return candidate

    return None


def _intent_ca(t: str) -> bool:
    kw = ["ca", "chiffre", "vente", "ventes", "chiff", "c.a", "revenue", "revenu"]
    return any(k in t for k in kw)


def _intent_factures(t: str) -> bool:
    """Détecte une demande de factures (liste, montant, détail)."""
    kw = ["facture", "factures", "fac"]
    return any(k in t for k in kw)


def _intent_top(t: str) -> bool:
    kw = ["top", "meilleur", "classement", "palmar", "premier"]
    # NB: "client" retiré d'ici — sinon "factures client X" matche top
    return any(k in t for k in kw)


def _intent_stock(t: str) -> bool:
    kw = ["stock", "rupture", "inventaire", "critique", "manque", "quantite"]
    return any(k in t for k in kw)


def _intent_impayes(t: str) -> bool:
    # NB: "facture" retiré — traité par _intent_factures
    kw = ["impaye", "impayes", "creance", "balance agee", "balance age",
          "dette", "recouvr", "echeance", "echue"]
    return any(k in t for k in kw)


def _intent_aide(t: str) -> bool:
    kw = ["aide", "help", "menu", "start", "bonjour", "salut", "hi", "hello",
          "commande", "quoi", "que peux", "que sais"]
    return any(k in t for k in kw)


def process_bot_command(text: str, dwh_code: str) -> str:
    """Traite un message en langage naturel et retourne la réponse.

    Priorité des intents :
    1. Aide (si pas d'autre intent)
    2. Factures d'un client spécifique
    3. CA d'un client spécifique  (ca + nom client)
    4. CA global
    5. Top clients
    6. Stock critique
    7. Impayés / balance âgée
    """
    t = _normalize(text)
    client_name = _extract_client_name(text)
    year, month = _extract_date_from_text(t)

    # ── Aide / salutations (seulement si pas d'autre intent clair) ──
    if _intent_aide(t) and not any([
        _intent_ca(t), _intent_stock(t), _intent_impayes(t),
        _intent_factures(t), _intent_top(t), client_name
    ]):
        return HELP_TEXT

    # ── Factures d'un client (priorité haute) ──
    if _intent_factures(t) and client_name:
        return _cmd_factures_client(dwh_code, client_name, year=year, month=month)

    # ── Factures sans client → résumé global factures ──
    if _intent_factures(t) and not _intent_impayes(t):
        if client_name:
            return _cmd_factures_client(dwh_code, client_name, year=year, month=month)
        # Pas de client → traiter comme CA
        return _cmd_ca(dwh_code, year=year, month=month)

    # ── CA d'un client spécifique (ca + nom client) ──
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

    # ── Client seul (sans intent clair) → CA du client ──
    if client_name:
        return _cmd_ca_client(dwh_code, client_name, year=year, month=month)

    return (
        f"Je n'ai pas compris *\"{text}\"*\n\n"
        "Essayez :\n"
        "  *ca* — Chiffre d'affaires\n"
        "  *ca BENTAYEB 2025* — CA d'un client\n"
        "  *factures Touhama* — Factures d'un client\n"
        "  *top5*, *stock*, *impayes*\n"
        "Ou envoyez *aide* pour la liste complète."
    )


def _cmd_ca(dwh_code: str, year: int = None, month: int = None) -> str:
    from app.database_unified import execute_dwh
    try:
        now = datetime.now()
        y = year or now.year
        m = month or now.month

        # Si année seulement (pas de mois) → CA annuel
        if year and not month:
            rows = execute_dwh(
                """
                SELECT
                    SUM([Montant HT Net]) AS ca_ht,
                    SUM([Montant TTC Net]) AS ca_ttc,
                    COUNT(DISTINCT [Code client]) AS nb_clients,
                    COUNT(*) AS nb_lignes
                FROM [dbo].[Lignes_des_ventes]
                WHERE [Valorise CA] = 'oui' AND YEAR([Date BL]) = ?
                """,
                (y,), dwh_code=dwh_code, use_cache=True,
            )
            label = f"Année {y}"
        else:
            rows = execute_dwh(
                """
                SELECT
                    SUM([Montant HT Net]) AS ca_ht,
                    SUM([Montant TTC Net]) AS ca_ttc,
                    COUNT(DISTINCT [Code client]) AS nb_clients,
                    COUNT(*) AS nb_lignes
                FROM [dbo].[Lignes_des_ventes]
                WHERE [Valorise CA] = 'oui'
                  AND YEAR([Date BL]) = ? AND MONTH([Date BL]) = ?
                """,
                (y, m), dwh_code=dwh_code, use_cache=True,
            )
            noms = ["", "Jan", "Fév", "Mar", "Avr", "Mai", "Jun",
                    "Jul", "Aoû", "Sep", "Oct", "Nov", "Déc"]
            label = f"{noms[m]} {y}"

        if not rows or rows[0].get("ca_ht") is None:
            return f"Aucune vente enregistrée pour {label}."
        r = rows[0]
        ca_ht  = r["ca_ht"]  or 0
        ca_ttc = r["ca_ttc"] or 0
        nb_cl  = r["nb_clients"] or 0
        return (
            f"📊 *CA {label}*\n\n"
            f"  💵 CA HT  : *{ca_ht:,.0f} MAD*\n"
            f"  💶 CA TTC : *{ca_ttc:,.0f} MAD*\n"
            f"  👥 Clients actifs : {nb_cl}"
        )
    except Exception as e:
        logger.error(f"WhatsApp bot CA error: {e}")
        return "Erreur lors de la récupération du CA."


def _cmd_ca_client(dwh_code: str, client_name: str, year: int = None, month: int = None) -> str:
    """Retourne le CA d'un client spécifique (recherche par nom LIKE)."""
    from app.database_unified import execute_dwh
    try:
        now = datetime.now()
        y = year or now.year
        m = month or now.month
        noms = ["", "Jan", "Fév", "Mar", "Avr", "Mai", "Jun",
                "Jul", "Aoû", "Sep", "Oct", "Nov", "Déc"]
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
            label = f"{noms[m]} {y}"

        if not rows:
            return (
                f"Aucune vente trouvée pour *{client_name}* en {label}.\n"
                f"_Vérifiez le nom du client._"
            )

        # Si plusieurs clients matchent, les lister
        if len(rows) > 1:
            lines = [f"📊 *CA {label} — \"{client_name}\"*\n"]
            total_ht = 0
            for r in rows[:10]:
                ca_ht = float(r['ca_ht'] or 0)
                total_ht += ca_ht
                lines.append(f"  👤 {r['client']}\n     *{ca_ht:,.0f} MAD* HT ({r['nb_factures']} pièces)")
            if len(rows) > 10:
                lines.append(f"  _… et {len(rows) - 10} autres clients_")
            lines.append(f"\n  💰 Total : *{total_ht:,.0f} MAD* HT")
            return "\n".join(lines)

        r = rows[0]
        ca_ht  = float(r['ca_ht']  or 0)
        ca_ttc = float(r['ca_ttc'] or 0)
        return (
            f"📊 *CA {r['client']} — {label}*\n\n"
            f"  💵 CA HT  : *{ca_ht:,.0f} MAD*\n"
            f"  💶 CA TTC : *{ca_ttc:,.0f} MAD*\n"
            f"  📄 Pièces : {r['nb_factures']} ({r['nb_lignes']} lignes)"
        )
    except Exception as e:
        logger.error(f"WhatsApp bot CA client error: {e}")
        return f"Erreur lors de la récupération du CA de {client_name}."


def _cmd_factures_client(dwh_code: str, client_name: str, year: int = None, month: int = None) -> str:
    """Retourne la liste des factures d'un client spécifique."""
    from app.database_unified import execute_dwh
    try:
        now = datetime.now()
        y = year or now.year
        like = f"%{client_name}%"
        noms = ["", "Jan", "Fév", "Mar", "Avr", "Mai", "Jun",
                "Jul", "Aoû", "Sep", "Oct", "Nov", "Déc"]

        if year and not month:
            rows = execute_dwh(
                """
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
                  AND YEAR([Date BL]) = ?
                GROUP BY [N° Pièce], [Intitulé client], [Date BL], [Type Document]
                ORDER BY [Date BL] DESC
                """,
                (like, y), dwh_code=dwh_code, use_cache=True,
            )
            label = f"Année {y}"
        elif month:
            rows = execute_dwh(
                """
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
                  AND YEAR([Date BL]) = ? AND MONTH([Date BL]) = ?
                GROUP BY [N° Pièce], [Intitulé client], [Date BL], [Type Document]
                ORDER BY [Date BL] DESC
                """,
                (like, y, month), dwh_code=dwh_code, use_cache=True,
            )
            label = f"{noms[month]} {y}"
        else:
            rows = execute_dwh(
                """
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
                  AND YEAR([Date BL]) = ?
                GROUP BY [N° Pièce], [Intitulé client], [Date BL], [Type Document]
                ORDER BY [Date BL] DESC
                """,
                (like, y), dwh_code=dwh_code, use_cache=True,
            )
            label = f"Année {y}"

        if not rows:
            return (
                f"Aucune facture trouvée pour *{client_name}* en {label}.\n"
                f"_Vérifiez le nom du client._"
            )

        # Calculer le total
        total_ht = sum(float(r['montant_ht'] or 0) for r in rows)
        total_ttc = sum(float(r['montant_ttc'] or 0) for r in rows)
        client_display = rows[0]['client']

        lines = [f"📄 *Factures {client_display} — {label}*\n"]
        for r in rows:
            dt = r['date_bl']
            date_str = dt.strftime("%d/%m/%Y") if hasattr(dt, 'strftime') else str(dt)[:10]
            ht = float(r['montant_ht'] or 0)
            lines.append(
                f"  📋 *{r['piece']}* ({r['type_doc']})\n"
                f"     {date_str} — *{ht:,.0f} MAD* HT"
            )

        lines.append(f"\n  💰 Total ({len(rows)} pièces) : *{total_ht:,.0f} MAD* HT / *{total_ttc:,.0f} MAD* TTC")
        if len(rows) == 15:
            lines.append("  _… liste limitée aux 15 plus récentes_")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"WhatsApp bot factures client error: {e}")
        return f"Erreur lors de la récupération des factures de {client_name}."


def _cmd_top5(dwh_code: str, year: int = None, month: int = None) -> str:
    from app.database_unified import execute_dwh
    try:
        now = datetime.now()
        y = year or now.year
        m = month or now.month
        noms = ["", "Jan", "Fév", "Mar", "Avr", "Mai", "Jun",
                "Jul", "Aoû", "Sep", "Oct", "Nov", "Déc"]

        if year and not month:
            rows = execute_dwh(
                """
                SELECT TOP 5 [Intitulé client] AS client, SUM([Montant HT Net]) AS ca
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
                SELECT TOP 5 [Intitulé client] AS client, SUM([Montant HT Net]) AS ca
                FROM [dbo].[Lignes_des_ventes]
                WHERE [Valorise CA] = 'oui'
                  AND YEAR([Date BL]) = ? AND MONTH([Date BL]) = ?
                GROUP BY [Intitulé client] ORDER BY ca DESC
                """,
                (y, m), dwh_code=dwh_code, use_cache=True,
            )
            label = f"{noms[m]} {y}"

        if not rows:
            return f"Aucune donnée client pour {label}."
        lines = [f"*🏆 Top 5 Clients — {label}*\n"]
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        for i, r in enumerate(rows):
            lines.append(f"  {medals[i]} {r['client']}\n     *{r['ca']:,.0f} MAD*")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"WhatsApp bot top5 error: {e}")
        return "Erreur lors de la récupération du top clients."


def _cmd_stock_critique(dwh_code: str) -> str:
    from app.database_unified import execute_dwh
    try:
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
            dwh_code=dwh_code,
            use_cache=True,
        )
        if not rows:
            return "Aucun article en stock critique. ✅"
        lines = ["*⚠️ Articles en stock critique :*\n"]
        for r in rows:
            qte   = r['qte']   or 0
            seuil = r['seuil'] or 0
            lines.append(f"  📦 {r['ref']} — {r['designation']}\n     Stock: {qte} / Seuil: {seuil}")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"WhatsApp bot stock error: {e}")
        return "Erreur lors de la récupération des stocks."


def _cmd_impayes(dwh_code: str) -> str:
    """Retourne le résumé des créances échues non réglées depuis Écheances_Ventes."""
    from app.database_unified import execute_dwh
    # Nom exact de la table (é = U+00E9, accent Sage 100)
    table = "Echéances_Ventes"
    try:
        rows = execute_dwh(
            f"""
            SELECT
                COUNT(*) AS nb,
                COUNT(DISTINCT [Code client]) AS nb_clients,
                SUM([Montant échéance] - [Montant du règlement]) AS total_du,
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
            return "Aucune créance échue non réglée. ✅"
        r = rows[0]
        total    = float(r['total_du']  or 0)
        plus_90j = float(r['plus_90j']  or 0)
        nb_cl    = r['nb_clients'] or 0
        return (
            "*💰 Créances échues non réglées*\n\n"
            f"  📋 Échéances : {r['nb']}\n"
            f"  👥 Clients : {nb_cl}\n"
            f"  💵 Total dû TTC : *{total:,.0f} MAD*\n"
            f"  ⏰ Dont > 90 jours : *{plus_90j:,.0f} MAD*"
        )
    except Exception as e:
        logger.error(f"WhatsApp bot impayés error: {e}")
        return (
            "⚠️ Données impayées temporairement indisponibles.\n"
            "_Réessayez dans quelques instants._"
        )


# ─── Test de connexion ──────────────────────────────────────────────────────────

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


# ─── Compatibilité avec l'ancien service (Twilio) ───────────────────────────

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
    # Fallback Twilio (ancien comportement)
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
