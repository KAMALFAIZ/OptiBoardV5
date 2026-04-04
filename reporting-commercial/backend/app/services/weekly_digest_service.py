"""
Service de digest hebdomadaire IA — OptiBoard.

Chaque lundi à 8h00, génère un résumé exécutif narratif (AI Summary)
des KPIs de la semaine écoulée et l'envoie par email aux utilisateurs
ayant le rôle 'direction' ou 'admin'.

Flux :
    send_all_digests()
        └─ pour chaque DWH actif → send_weekly_digest(dwh_code)
                └─ get_direction_users()   → destinataires
                └─ get_weekly_kpis()       → données brutes semaine N-1
                └─ generate_executive_summary() → narration IA
                └─ build_digest_html()     → corps email HTML
                └─ send_email()            → livraison SMTP
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Rôles qui reçoivent le digest
_DIGEST_ROLES = {"direction", "admin", "superadmin"}


# ─── Destinataires ────────────────────────────────────────────────────────────

def get_direction_users(dwh_code: str) -> List[Dict[str, Any]]:
    """
    Retourne les utilisateurs actifs ayant un rôle 'direction' ou 'admin'
    dans la base client, avec leur email.
    """
    from ..database_unified import execute_client
    try:
        rows = execute_client(
            """SELECT nom, prenom, email, role_dwh
               FROM APP_Users
               WHERE actif = 1
                 AND email IS NOT NULL
                 AND email <> ''
                 AND role_dwh IN ('direction', 'admin', 'superadmin')""",
            dwh_code=dwh_code,
            use_cache=False,
        )
        return rows or []
    except Exception as e:
        logger.warning(f"[DIGEST] get_direction_users({dwh_code}): {e}")
        return []


# ─── KPIs de la semaine ───────────────────────────────────────────────────────

def get_weekly_kpis(dwh_code: str) -> Dict[str, Any]:
    """
    Charge les KPIs synthétiques de la semaine écoulée (lundi→dimanche).
    Retourne un dict structuré utilisable par l'AI summary.
    """
    from ..database_unified import execute_dwh

    today = datetime.now().date()
    # Semaine écoulée : lundi → dimanche de S-1
    days_since_monday = today.weekday()          # 0=lun
    last_monday = today - timedelta(days=days_since_monday + 7)
    last_sunday = last_monday + timedelta(days=6)

    date_debut = last_monday.strftime("%Y-%m-%d")
    date_fin   = last_sunday.strftime("%Y-%m-%d")

    kpis: Dict[str, Any] = {
        "periode": f"{last_monday.strftime('%d/%m/%Y')} → {last_sunday.strftime('%d/%m/%Y')}",
        "date_debut": date_debut,
        "date_fin": date_fin,
    }

    # ── CA de la semaine ──────────────────────────────────────────────────────
    try:
        rows = execute_dwh(
            """SELECT
                 ISNULL(SUM(MontantHT), 0)   AS ca_ht,
                 ISNULL(SUM(MontantTTC), 0)  AS ca_ttc,
                 COUNT(DISTINCT NumeroPiece)  AS nb_factures
               FROM VTE_Factures
               WHERE DatePiece BETWEEN ? AND ?
                 AND TypePiece IN ('FA', 'FD')""",
            (date_debut, date_fin),
            dwh_code=dwh_code,
            use_cache=False,
        )
        if rows:
            kpis["ca_ht"]       = float(rows[0].get("ca_ht") or 0)
            kpis["ca_ttc"]      = float(rows[0].get("ca_ttc") or 0)
            kpis["nb_factures"] = int(rows[0].get("nb_factures") or 0)
    except Exception as e:
        logger.debug(f"[DIGEST] CA semaine: {e}")
        kpis["ca_ht"] = kpis["ca_ttc"] = kpis["nb_factures"] = None

    # ── Encours clients (total impayés à ce jour) ─────────────────────────────
    try:
        rows = execute_dwh(
            """SELECT ISNULL(SUM(Solde), 0) AS total_encours,
                      COUNT(DISTINCT CodeClient) AS nb_clients_encours
               FROM REC_BalanceAgee
               WHERE Solde > 0""",
            dwh_code=dwh_code,
            use_cache=False,
        )
        if rows:
            kpis["total_encours"]      = float(rows[0].get("total_encours") or 0)
            kpis["nb_clients_encours"] = int(rows[0].get("nb_clients_encours") or 0)
    except Exception as e:
        logger.debug(f"[DIGEST] Encours: {e}")
        kpis["total_encours"] = kpis["nb_clients_encours"] = None

    # ── Clients en retard > 60j ───────────────────────────────────────────────
    try:
        rows = execute_dwh(
            """SELECT COUNT(DISTINCT CodeClient) AS nb_retard_60j,
                      ISNULL(SUM(Solde), 0)      AS montant_retard_60j
               FROM REC_BalanceAgee
               WHERE NbJoursRetard > 60 AND Solde > 0""",
            dwh_code=dwh_code,
            use_cache=False,
        )
        if rows:
            kpis["nb_retard_60j"]      = int(rows[0].get("nb_retard_60j") or 0)
            kpis["montant_retard_60j"] = float(rows[0].get("montant_retard_60j") or 0)
    except Exception as e:
        logger.debug(f"[DIGEST] Retard 60j: {e}")
        kpis["nb_retard_60j"] = kpis["montant_retard_60j"] = None

    return kpis


# ─── Template HTML email ──────────────────────────────────────────────────────

def build_digest_html(
    kpis: Dict[str, Any],
    summary: Dict[str, Any],
    dwh_code: str,
) -> str:
    """
    Construit le corps HTML de l'email digest hebdomadaire.
    Combine les KPIs bruts et les sections narratives de l'AI summary.
    """
    periode = kpis.get("periode", "")

    # ── KPI cards ─────────────────────────────────────────────────────────────
    def fmt_currency(v):
        if v is None:
            return "N/A"
        return f"{v:,.2f} €".replace(",", " ")

    def fmt_int(v):
        return "N/A" if v is None else str(v)

    kpi_cards = f"""
    <div style="display:flex;gap:12px;flex-wrap:wrap;margin:20px 0;">
      <div style="flex:1;min-width:160px;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:16px;text-align:center;">
        <div style="font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:1px;">CA HT semaine</div>
        <div style="font-size:22px;font-weight:700;color:#059669;margin-top:6px;">{fmt_currency(kpis.get('ca_ht'))}</div>
        <div style="font-size:12px;color:#6b7280;margin-top:4px;">{fmt_int(kpis.get('nb_factures'))} facture(s)</div>
      </div>
      <div style="flex:1;min-width:160px;background:#fff7ed;border:1px solid #fed7aa;border-radius:8px;padding:16px;text-align:center;">
        <div style="font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:1px;">Encours total</div>
        <div style="font-size:22px;font-weight:700;color:#ea580c;margin-top:6px;">{fmt_currency(kpis.get('total_encours'))}</div>
        <div style="font-size:12px;color:#6b7280;margin-top:4px;">{fmt_int(kpis.get('nb_clients_encours'))} client(s)</div>
      </div>
      <div style="flex:1;min-width:160px;background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:16px;text-align:center;">
        <div style="font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:1px;">Retard &gt; 60j</div>
        <div style="font-size:22px;font-weight:700;color:#dc2626;margin-top:6px;">{fmt_currency(kpis.get('montant_retard_60j'))}</div>
        <div style="font-size:12px;color:#6b7280;margin-top:4px;">{fmt_int(kpis.get('nb_retard_60j'))} client(s)</div>
      </div>
    </div>
    """

    # ── Sections narratives IA ─────────────────────────────────────────────────
    sections_html = ""
    for section in summary.get("sections", []):
        titre  = section.get("titre", "")
        contenu = section.get("contenu", "")
        sections_html += f"""
        <div style="margin:16px 0;padding:16px;background:#f9fafb;border-left:4px solid #059669;border-radius:0 8px 8px 0;">
          <div style="font-weight:600;color:#111827;margin-bottom:8px;">{titre}</div>
          <div style="color:#374151;line-height:1.6;font-size:14px;">{contenu}</div>
        </div>"""

    # ── KPIs clés IA ──────────────────────────────────────────────────────────
    kpis_cles_html = ""
    for kpi in summary.get("kpis_cles", [])[:5]:
        label         = kpi.get("label", "")
        valeur        = kpi.get("valeur", "")
        interpretation = kpi.get("interpretation", "")
        kpis_cles_html += f"""
        <tr>
          <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;font-weight:500;color:#111827;">{label}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;color:#059669;font-weight:600;">{valeur}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-size:13px;">{interpretation}</td>
        </tr>"""

    kpis_table = f"""
    <table style="width:100%;border-collapse:collapse;margin-top:16px;background:#fff;border-radius:8px;overflow:hidden;border:1px solid #e5e7eb;">
      <thead>
        <tr style="background:#f3f4f6;">
          <th style="padding:10px 12px;text-align:left;font-size:12px;color:#6b7280;font-weight:600;text-transform:uppercase;">Indicateur</th>
          <th style="padding:10px 12px;text-align:left;font-size:12px;color:#6b7280;font-weight:600;text-transform:uppercase;">Valeur</th>
          <th style="padding:10px 12px;text-align:left;font-size:12px;color:#6b7280;font-weight:600;text-transform:uppercase;">Analyse</th>
        </tr>
      </thead>
      <tbody>{kpis_cles_html}</tbody>
    </table>""" if kpis_cles_html else ""

    generated_at = datetime.now().strftime("%d/%m/%Y à %H:%M")
    provider = summary.get("provider", "IA")

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body style="margin:0;padding:0;font-family:'Segoe UI',Arial,sans-serif;background:#f3f4f6;">
  <div style="max-width:680px;margin:32px auto;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">

    <!-- Header -->
    <div style="background:linear-gradient(135deg,#059669 0%,#047857 100%);padding:28px 32px;">
      <div style="color:white;font-size:22px;font-weight:700;">OptiBoard</div>
      <div style="color:rgba(255,255,255,0.85);font-size:14px;margin-top:4px;">Résumé exécutif hebdomadaire — {periode}</div>
    </div>

    <!-- Body -->
    <div style="padding:28px 32px;">
      <h2 style="margin:0 0 4px 0;font-size:18px;color:#111827;">{summary.get('titre', 'Résumé de la semaine')}</h2>
      <div style="color:#9ca3af;font-size:13px;margin-bottom:20px;">Généré le {generated_at} par {provider}</div>

      <!-- KPI cards -->
      {kpi_cards}

      <!-- Sections IA -->
      {sections_html}

      <!-- Table KPIs clés -->
      {kpis_table}
    </div>

    <!-- Footer -->
    <div style="background:#f9fafb;padding:16px 32px;text-align:center;border-top:1px solid #e5e7eb;">
      <p style="margin:0;font-size:12px;color:#9ca3af;">
        Ce message est généré automatiquement par OptiBoard chaque lundi à 8h00.<br>
        Pour vous désabonner, contactez votre administrateur.
      </p>
    </div>
  </div>
</body>
</html>"""


# ─── Orchestrateur principal ──────────────────────────────────────────────────

async def send_weekly_digest(dwh_code: str) -> Dict[str, Any]:
    """
    Génère et envoie le digest hebdomadaire pour un DWH donné.
    Retourne un dict de résultat (success, nb_sent, errors).
    """
    from .ai_summary_service import generate_executive_summary
    from .email_service import send_email

    result = {"dwh_code": dwh_code, "success": False, "nb_sent": 0, "errors": []}

    # 1. Destinataires
    users = get_direction_users(dwh_code)
    if not users:
        result["errors"].append("Aucun utilisateur 'direction' ou 'admin' avec email trouvé")
        logger.info(f"[DIGEST] {dwh_code} — aucun destinataire, skip")
        return result

    emails = [u["email"] for u in users if u.get("email")]
    if not emails:
        result["errors"].append("Emails vides pour les utilisateurs direction")
        return result

    # 2. KPIs de la semaine
    kpis = get_weekly_kpis(dwh_code)

    # 3. Données synthétiques pour l'AI summary (format attendu par generate_executive_summary)
    kpis_as_rows = [kpis]
    columns_info = [
        {"field": "ca_ht",              "header": "CA HT semaine (€)"},
        {"field": "ca_ttc",             "header": "CA TTC semaine (€)"},
        {"field": "nb_factures",        "header": "Nombre de factures"},
        {"field": "total_encours",      "header": "Encours total (€)"},
        {"field": "nb_clients_encours", "header": "Clients avec encours"},
        {"field": "nb_retard_60j",      "header": "Clients retard >60j"},
        {"field": "montant_retard_60j", "header": "Montant retard >60j (€)"},
    ]

    periode = kpis.get("periode", "")
    summary = await generate_executive_summary(
        report_type="dashboard",
        report_id=0,
        report_nom="Digest hebdomadaire",
        data=kpis_as_rows,
        columns_info=columns_info,
        period=periode,
        entity=dwh_code,
        context="Résumé exécutif hebdomadaire — CA, encours clients et recouvrement",
        force_refresh=True,
    )

    if not summary.get("success"):
        # Digest sans narration IA : envoi uniquement avec les KPIs bruts
        logger.warning(f"[DIGEST] {dwh_code} — AI summary indisponible : {summary.get('error')}")
        summary = {"titre": "Résumé hebdomadaire", "sections": [], "kpis_cles": [], "provider": "N/A"}

    # 4. Construire le HTML
    html = build_digest_html(kpis, summary, dwh_code)

    # 5. Envoyer
    subject = f"[OptiBoard] Résumé hebdomadaire — {periode}"
    send_result = send_email(
        to_emails=emails,
        subject=subject,
        body_html=html,
    )

    if send_result.get("success"):
        result["success"] = True
        result["nb_sent"] = len(emails)
        logger.info(f"[DIGEST] {dwh_code} — envoyé à {len(emails)} destinataire(s)")
    else:
        result["errors"].append(send_result.get("error", "Erreur SMTP inconnue"))
        logger.error(f"[DIGEST] {dwh_code} — erreur envoi: {send_result.get('error')}")

    return result


async def send_all_digests() -> Dict[str, Any]:
    """
    Boucle sur tous les DWH actifs (non-demo) et envoie le digest.
    Appelée par le scheduler chaque lundi à 8h00.
    """
    from ..database_unified import execute_central

    global_result = {"total_dwh": 0, "success": 0, "failed": 0, "details": []}

    try:
        dwh_list = execute_central(
            "SELECT code FROM APP_DWH WHERE actif = 1 AND ISNULL(is_demo, 0) = 0",
            use_cache=False,
        )
    except Exception as e:
        logger.error(f"[DIGEST] Impossible de charger la liste DWH: {e}")
        return global_result

    global_result["total_dwh"] = len(dwh_list)

    for row in dwh_list:
        dwh_code = row.get("code", "")
        if not dwh_code:
            continue
        try:
            res = await send_weekly_digest(dwh_code)
            global_result["details"].append(res)
            if res["success"]:
                global_result["success"] += 1
            else:
                global_result["failed"] += 1
        except Exception as e:
            logger.error(f"[DIGEST] Erreur DWH {dwh_code}: {e}")
            global_result["failed"] += 1
            global_result["details"].append({"dwh_code": dwh_code, "success": False, "errors": [str(e)]})

    logger.info(f"[DIGEST] Terminé — {global_result['success']}/{global_result['total_dwh']} DWH envoyés")
    return global_result
