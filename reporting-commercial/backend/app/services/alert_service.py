"""Service d'évaluation des alertes KPI et envoi de notifications"""
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# KPIs supportés et leur méthode de récupération
SUPPORTED_METRICS = {
    "dso": {
        "label": "DSO (Jours de créances)",
        "unit": "jours",
        "higher_is_worse": True,
    },
    "taux_creances": {
        "label": "Taux créances douteuses",
        "unit": "%",
        "higher_is_worse": True,
    },
    "stock_rotation": {
        "label": "Rotation des stocks",
        "unit": "x",
        "higher_is_worse": False,
    },
    "encours_total": {
        "label": "Encours clients total",
        "unit": "MAD",
        "higher_is_worse": True,
    },
    "ca_mensuel": {
        "label": "CA mensuel",
        "unit": "MAD",
        "higher_is_worse": False,
    },
    "ca_evolution_pct": {
        "label": "Evolution CA (%)",
        "unit": "%",
        "higher_is_worse": False,
    },
    "impaye_total": {
        "label": "Total impayés",
        "unit": "MAD",
        "higher_is_worse": True,
    },
}

OPERATORS = {
    "gt": ">",
    "lt": "<",
    "gte": ">=",
    "lte": "<=",
    "eq": "=",
}


def evaluate_condition(value: float, operator: str, threshold: float) -> bool:
    """Évalue si une condition est vraie."""
    if operator == "gt":
        return value > threshold
    elif operator == "lt":
        return value < threshold
    elif operator == "gte":
        return value >= threshold
    elif operator == "lte":
        return value <= threshold
    elif operator == "eq":
        return abs(value - threshold) < 0.001
    return False


def _fetch_kpi_value(metric_type: str, execute_dwh) -> Optional[float]:
    """Récupère la valeur actuelle d'un KPI depuis la base DWH."""
    try:
        if metric_type == "dso":
            rows = execute_dwh("""
                SELECT TOP 1
                    CASE WHEN SUM(ca_annuel) > 0
                         THEN (SUM(encours) / SUM(ca_annuel)) * 365
                         ELSE 0 END AS dso
                FROM (
                    SELECT
                        SUM(ISNULL(Solde_Cloture, 0)) AS encours,
                        (SELECT ISNULL(SUM(ISNULL(Montant_HT,0)),0) FROM DashBoard_CA
                         WHERE YEAR(Date_Document) = YEAR(GETDATE())) AS ca_annuel
                    FROM BalanceAgee
                ) t
            """, use_cache=False)
            return float(rows[0]["dso"]) if rows and rows[0]["dso"] is not None else None

        elif metric_type == "taux_creances":
            rows = execute_dwh("""
                SELECT
                    CASE WHEN SUM(ISNULL(Solde_Cloture,0)) > 0
                         THEN (SUM(ISNULL([+120],0)) / SUM(ISNULL(Solde_Cloture,0))) * 100
                         ELSE 0 END AS taux
                FROM BalanceAgee
            """, use_cache=False)
            return float(rows[0]["taux"]) if rows and rows[0]["taux"] is not None else None

        elif metric_type == "stock_rotation":
            rows = execute_dwh("""
                SELECT
                    CASE WHEN AVG(ISNULL(Stock_Valorise,0)) > 0
                         THEN (SELECT ISNULL(SUM(ISNULL(Montant_HT,0)),0)
                               FROM DashBoard_CA WHERE YEAR(Date_Document) = YEAR(GETDATE()))
                              / AVG(ISNULL(Stock_Valorise,0))
                         ELSE 0 END AS rotation
                FROM Mouvement_Stock
                WHERE YEAR(Date_Mouvement) = YEAR(GETDATE())
            """, use_cache=False)
            return float(rows[0]["rotation"]) if rows and rows[0]["rotation"] is not None else None

        elif metric_type == "encours_total":
            rows = execute_dwh("""
                SELECT ISNULL(SUM(ISNULL(Solde_Cloture,0)),0) AS total
                FROM BalanceAgee
            """, use_cache=False)
            return float(rows[0]["total"]) if rows and rows[0]["total"] is not None else None

        elif metric_type == "ca_mensuel":
            rows = execute_dwh("""
                SELECT ISNULL(SUM(ISNULL(Montant_HT,0)),0) AS ca
                FROM DashBoard_CA
                WHERE YEAR(Date_Document) = YEAR(GETDATE())
                  AND MONTH(Date_Document) = MONTH(GETDATE())
            """, use_cache=False)
            return float(rows[0]["ca"]) if rows and rows[0]["ca"] is not None else None

        elif metric_type == "ca_evolution_pct":
            rows = execute_dwh("""
                SELECT
                    ISNULL(SUM(CASE WHEN YEAR(Date_Document) = YEAR(GETDATE())
                                        AND MONTH(Date_Document) = MONTH(GETDATE())
                               THEN Montant_HT ELSE 0 END), 0) AS ca_current,
                    ISNULL(SUM(CASE WHEN YEAR(Date_Document) = YEAR(GETDATE()) - 1
                                        AND MONTH(Date_Document) = MONTH(GETDATE())
                               THEN Montant_HT ELSE 0 END), 0) AS ca_prev
                FROM DashBoard_CA
            """, use_cache=False)
            if rows:
                ca_curr = float(rows[0]["ca_current"] or 0)
                ca_prev = float(rows[0]["ca_prev"] or 0)
                if ca_prev > 0:
                    return ((ca_curr - ca_prev) / ca_prev) * 100
            return None

        elif metric_type == "impaye_total":
            rows = execute_dwh("""
                SELECT ISNULL(SUM(ISNULL(Solde_Cloture,0)),0) AS total
                FROM BalanceAgee
                WHERE Solde_Cloture > 0
            """, use_cache=False)
            return float(rows[0]["total"]) if rows and rows[0]["total"] is not None else None

    except Exception as e:
        print(f"[ALERT_SERVICE] Erreur fetch KPI '{metric_type}': {e}")
        return None


def _was_recently_triggered(rule_id: int, cooldown_hours: int, execute_client) -> bool:
    """Vérifie si une alerte a déjà été déclenchée récemment (cooldown)."""
    try:
        rows = execute_client("""
            SELECT TOP 1 triggered_at
            FROM APP_KPI_AlertHistory
            WHERE rule_id = ?
              AND triggered_at >= DATEADD(hour, ?, GETDATE())
            ORDER BY triggered_at DESC
        """, (rule_id, -cooldown_hours), use_cache=False)
        return len(rows) > 0
    except Exception:
        return False


def _send_alert_email(rule: Dict, value: float, execute_client):
    """Envoie un email de notification pour une alerte déclenchée."""
    try:
        from .email_service import send_email, get_email_template
        recipients = json.loads(rule.get("notify_emails") or "[]")
        if not recipients:
            return

        metric_info = SUPPORTED_METRICS.get(rule["metric_type"], {})
        unit = metric_info.get("unit", "")
        niveau = rule["niveau"]
        niveau_color = {"critical": "#dc2626", "warning": "#d97706", "info": "#2563eb"}.get(niveau, "#6b7280")
        niveau_label = {"critical": "CRITIQUE", "warning": "ATTENTION", "info": "INFO"}.get(niveau, niveau.upper())

        html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8">
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #333; }}
  .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
  .header {{ background: linear-gradient(135deg, #059669, #047857); color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
  .alert-badge {{ display: inline-block; background: {niveau_color}; color: white; padding: 4px 12px; border-radius: 12px; font-weight: bold; font-size: 13px; }}
  .content {{ background: #f9fafb; padding: 20px; border: 1px solid #e5e7eb; }}
  .kpi-box {{ background: white; border-left: 4px solid {niveau_color}; padding: 16px; border-radius: 4px; margin: 12px 0; }}
  .kpi-value {{ font-size: 28px; font-weight: bold; color: {niveau_color}; }}
  .footer {{ background: #f3f4f6; padding: 12px; text-align: center; font-size: 12px; color: #6b7280; border-radius: 0 0 8px 8px; }}
</style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h2 style="margin:0;">OptiBoard — Alerte KPI</h2>
      <p style="margin:4px 0 0;opacity:.9;">Surveillance automatique des indicateurs</p>
    </div>
    <div class="content">
      <p>Une alerte a été déclenchée sur votre tableau de bord :</p>
      <span class="alert-badge">{niveau_label}</span>
      <div class="kpi-box">
        <p style="margin:0 0 6px;font-weight:600;font-size:15px;">{rule['nom']}</p>
        <div class="kpi-value">{value:,.2f} {unit}</div>
        <p style="margin:6px 0 0;color:#6b7280;font-size:13px;">
          Règle : {metric_info.get('label', rule['metric_type'])} {OPERATORS.get(rule['operator'], rule['operator'])} {rule['threshold_value']} {unit}
        </p>
      </div>
      <p style="color:#6b7280;font-size:13px;">Déclenché le {datetime.now().strftime('%d/%m/%Y à %H:%M')}</p>
    </div>
    <div class="footer">OptiBoard — KAsoft Reporting • Ce message est généré automatiquement.</div>
  </div>
</body>
</html>"""

        send_email(
            to_emails=recipients,
            subject=f"[{niveau_label}] Alerte KPI : {rule['nom']} — {value:,.2f} {unit}",
            body_html=html
        )
    except Exception as e:
        print(f"[ALERT_SERVICE] Erreur envoi email alerte: {e}")


def evaluate_all_alerts(execute_client, execute_dwh):
    """
    Évalue toutes les règles d'alerte actives et enregistre les déclenchements.
    Appelé par le scheduler périodiquement.
    """
    from ..database_unified import client_cursor as get_db_cursor

    try:
        rules = execute_client(
            "SELECT * FROM APP_KPI_AlertRules WHERE is_active = 1",
            use_cache=False
        )
    except Exception as e:
        print(f"[ALERT_SERVICE] Impossible de charger les règles: {e}")
        return {"triggered": 0, "errors": 1}

    triggered = 0
    errors = 0

    for rule in rules:
        try:
            value = _fetch_kpi_value(rule["metric_type"], execute_dwh)
            if value is None:
                continue

            # Mettre à jour last_checked
            try:
                with get_db_cursor() as cur:
                    cur.execute(
                        "UPDATE APP_KPI_AlertRules SET last_checked = GETDATE() WHERE id = ?",
                        (rule["id"],)
                    )
            except Exception:
                pass

            if not evaluate_condition(value, rule["operator"], float(rule["threshold_value"])):
                continue

            # Cooldown : ne pas re-déclencher dans les N heures
            cooldown = int(rule.get("cooldown_hours") or 4)
            if _was_recently_triggered(rule["id"], cooldown, execute_client):
                continue

            # Enregistrer dans l'historique
            metric_info = SUPPORTED_METRICS.get(rule["metric_type"], {})
            message = (
                f"{metric_info.get('label', rule['metric_type'])} = "
                f"{value:,.2f} {metric_info.get('unit','')} "
                f"(seuil: {OPERATORS.get(rule['operator'],'')} {rule['threshold_value']})"
            )

            try:
                with get_db_cursor() as cur:
                    cur.execute("""
                        INSERT INTO APP_KPI_AlertHistory
                            (rule_id, metric_value, niveau, message, triggered_at)
                        VALUES (?, ?, ?, ?, GETDATE())
                    """, (rule["id"], value, rule["niveau"], message))

                    cur.execute(
                        "UPDATE APP_KPI_AlertRules SET last_triggered = GETDATE() WHERE id = ?",
                        (rule["id"],)
                    )
            except Exception as e:
                print(f"[ALERT_SERVICE] Erreur enregistrement historique règle {rule['id']}: {e}")
                errors += 1
                continue

            # Envoyer email si configuré
            _send_alert_email(rule, value, execute_client)

            triggered += 1
            print(f"[ALERT_SERVICE] Alerte déclenchée: '{rule['nom']}' — {message}")

        except Exception as e:
            print(f"[ALERT_SERVICE] Erreur évaluation règle {rule.get('id')}: {e}")
            errors += 1

    print(f"[ALERT_SERVICE] Évaluation terminée: {triggered} déclenchée(s), {errors} erreur(s)")
    return {"triggered": triggered, "errors": errors}


def get_active_alerts_count(execute_client) -> int:
    """Retourne le nombre d'alertes non acquittées des dernières 24h (pour la cloche)."""
    try:
        rows = execute_client("""
            SELECT COUNT(*) AS cnt
            FROM APP_KPI_AlertHistory
            WHERE is_acknowledged = 0
              AND triggered_at >= DATEADD(hour, -24, GETDATE())
        """, use_cache=False)
        return int(rows[0]["cnt"]) if rows else 0
    except Exception:
        return 0
