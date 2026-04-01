"""Routes pour la gestion des alertes KPI"""
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
import json
from datetime import datetime

from ..database_unified import execute_central as execute_query, write_central as write_client
from ..database_unified import execute_dwh
from ..services.alert_service import (
    evaluate_all_alerts,
    get_active_alerts_count,
    SUPPORTED_METRICS,
    OPERATORS,
)

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


# ==================== SCHEMAS ====================

class AlertRuleCreate(BaseModel):
    nom: str
    description: Optional[str] = None
    metric_type: str
    operator: str          # gt, lt, gte, lte, eq
    threshold_value: float
    niveau: str = "warning"  # info, warning, critical
    notify_emails: Optional[List[str]] = None
    cooldown_hours: int = 4
    is_active: bool = True


class AlertRuleUpdate(BaseModel):
    nom: Optional[str] = None
    description: Optional[str] = None
    metric_type: Optional[str] = None
    operator: Optional[str] = None
    threshold_value: Optional[float] = None
    niveau: Optional[str] = None
    notify_emails: Optional[List[str]] = None
    cooldown_hours: Optional[int] = None
    is_active: Optional[bool] = None


# ==================== INIT TABLES ====================

def init_alert_tables():
    """Crée les tables d'alertes si elles n'existent pas encore."""
    tables = [
        """
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'APP_KPI_AlertRules')
        CREATE TABLE APP_KPI_AlertRules (
            id              INT IDENTITY(1,1) PRIMARY KEY,
            nom             NVARCHAR(255)   NOT NULL,
            description     NVARCHAR(MAX),
            metric_type     NVARCHAR(100)   NOT NULL,
            operator        NVARCHAR(10)    NOT NULL,
            threshold_value FLOAT           NOT NULL,
            niveau          NVARCHAR(20)    NOT NULL DEFAULT 'warning',
            notify_emails   NVARCHAR(MAX),
            cooldown_hours  INT             NOT NULL DEFAULT 4,
            is_active       BIT             NOT NULL DEFAULT 1,
            last_checked    DATETIME,
            last_triggered  DATETIME,
            created_at      DATETIME        DEFAULT GETDATE(),
            updated_at      DATETIME        DEFAULT GETDATE()
        )
        """,
        """
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'APP_KPI_AlertHistory')
        CREATE TABLE APP_KPI_AlertHistory (
            id               INT IDENTITY(1,1) PRIMARY KEY,
            rule_id          INT,
            metric_value     FLOAT,
            niveau           NVARCHAR(20),
            message          NVARCHAR(MAX),
            triggered_at     DATETIME DEFAULT GETDATE(),
            is_acknowledged  BIT      NOT NULL DEFAULT 0,
            acknowledged_by  NVARCHAR(255),
            acknowledged_at  DATETIME,
            FOREIGN KEY (rule_id) REFERENCES APP_KPI_AlertRules(id) ON DELETE SET NULL
        )
        """,
    ]
    try:
        for sql in tables:
            write_client(sql)
        return True
    except Exception as e:
        print(f"[ALERTS] Erreur init tables: {e}")
        return False


# ==================== MÉTA ====================

@router.get("/metrics")
async def get_supported_metrics():
    """Liste les types de KPIs supportés pour les règles d'alerte."""
    metrics = [
        {"key": k, "label": v["label"], "unit": v["unit"], "higher_is_worse": v["higher_is_worse"]}
        for k, v in SUPPORTED_METRICS.items()
    ]
    operators = [{"key": k, "label": v} for k, v in OPERATORS.items()]
    return {"success": True, "metrics": metrics, "operators": operators}


# ==================== CRUD RÈGLES ====================

@router.get("/rules")
async def get_rules():
    """Retourne toutes les règles d'alerte."""
    try:
        init_alert_tables()
        rules = execute_query("""
            SELECT r.*,
                   (SELECT COUNT(*) FROM APP_KPI_AlertHistory WHERE rule_id = r.id) AS trigger_count,
                   (SELECT COUNT(*) FROM APP_KPI_AlertHistory
                    WHERE rule_id = r.id AND is_acknowledged = 0
                      AND triggered_at >= DATEADD(hour, -24, GETDATE())) AS unread_count
            FROM APP_KPI_AlertRules r
            ORDER BY r.is_active DESC, r.niveau DESC, r.nom
        """, use_cache=False)

        for r in rules:
            if r.get("notify_emails"):
                r["notify_emails"] = json.loads(r["notify_emails"])
            else:
                r["notify_emails"] = []

        return {"success": True, "data": rules}
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}


@router.get("/rules/{rule_id}")
async def get_rule(rule_id: int):
    """Retourne une règle par ID."""
    try:
        rows = execute_query(
            "SELECT * FROM APP_KPI_AlertRules WHERE id = ?",
            (rule_id,), use_cache=False
        )
        if not rows:
            return {"success": False, "error": "Règle non trouvée"}
        r = rows[0]
        r["notify_emails"] = json.loads(r["notify_emails"]) if r.get("notify_emails") else []
        return {"success": True, "data": r}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/rules")
async def create_rule(rule: AlertRuleCreate):
    """Crée une nouvelle règle d'alerte."""
    try:
        init_alert_tables()
        write_client("""
            INSERT INTO APP_KPI_AlertRules
                (nom, description, metric_type, operator, threshold_value, niveau,
                 notify_emails, cooldown_hours, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rule.nom, rule.description, rule.metric_type, rule.operator,
            rule.threshold_value, rule.niveau,
            json.dumps(rule.notify_emails or []),
            rule.cooldown_hours, 1 if rule.is_active else 0
        ))
        rows = execute_query(
            "SELECT TOP 1 id FROM APP_KPI_AlertRules ORDER BY id DESC",
            use_cache=False
        )
        new_id = rows[0]["id"] if rows else None
        return {"success": True, "id": new_id, "message": "Règle créée"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.put("/rules/{rule_id}")
async def update_rule(rule_id: int, rule: AlertRuleUpdate):
    """Met à jour une règle d'alerte."""
    try:
        updates = []
        params = []

        fields = {
            "nom": rule.nom,
            "description": rule.description,
            "metric_type": rule.metric_type,
            "operator": rule.operator,
            "threshold_value": rule.threshold_value,
            "niveau": rule.niveau,
            "cooldown_hours": rule.cooldown_hours,
            "is_active": rule.is_active,
        }
        for col, val in fields.items():
            if val is not None:
                updates.append(f"{col} = ?")
                params.append(val)

        if rule.notify_emails is not None:
            updates.append("notify_emails = ?")
            params.append(json.dumps(rule.notify_emails))

        if not updates:
            return {"success": False, "error": "Aucune modification"}

        updates.append("updated_at = GETDATE()")
        params.append(rule_id)

        write_client(f"UPDATE APP_KPI_AlertRules SET {', '.join(updates)} WHERE id = ?", tuple(params))
        return {"success": True, "message": "Règle mise à jour"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: int):
    """Supprime une règle et son historique."""
    try:
        write_client("DELETE FROM APP_KPI_AlertHistory WHERE rule_id = ?", (rule_id,))
        write_client("DELETE FROM APP_KPI_AlertRules WHERE id = ?", (rule_id,))
        return {"success": True, "message": "Règle supprimée"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/rules/{rule_id}/toggle")
async def toggle_rule(rule_id: int):
    """Active/désactive une règle."""
    try:
        write_client("""
            UPDATE APP_KPI_AlertRules
            SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END,
                updated_at = GETDATE()
            WHERE id = ?
        """, (rule_id,))
        rows = execute_query(
            "SELECT is_active FROM APP_KPI_AlertRules WHERE id = ?",
            (rule_id,), use_cache=False
        )
        return {"success": True, "is_active": rows[0]["is_active"] if rows else None}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== HISTORIQUE ====================

@router.get("/history")
async def get_history(limit: int = 100, rule_id: Optional[int] = None, unread_only: bool = False):
    """Retourne l'historique des alertes déclenchées."""
    try:
        query = """
            SELECT h.*, r.nom AS rule_nom, r.metric_type
            FROM APP_KPI_AlertHistory h
            LEFT JOIN APP_KPI_AlertRules r ON h.rule_id = r.id
            WHERE 1=1
        """
        params = []
        if rule_id:
            query += " AND h.rule_id = ?"
            params.append(rule_id)
        if unread_only:
            query += " AND h.is_acknowledged = 0"

        query += f" ORDER BY h.triggered_at DESC OFFSET 0 ROWS FETCH NEXT {limit} ROWS ONLY"

        rows = execute_query(query, tuple(params) if params else None, use_cache=False)
        return {"success": True, "data": rows}
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}


@router.post("/history/{history_id}/acknowledge")
async def acknowledge_alert(history_id: int, username: str = "user"):
    """Acquitte une alerte (marque comme lue)."""
    try:
        write_client("""
            UPDATE APP_KPI_AlertHistory
            SET is_acknowledged = 1,
                acknowledged_by = ?,
                acknowledged_at = GETDATE()
            WHERE id = ?
        """, (username, history_id))
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/history/acknowledge-all")
async def acknowledge_all(username: str = "user"):
    """Acquitte toutes les alertes non lues."""
    try:
        write_client("""
            UPDATE APP_KPI_AlertHistory
            SET is_acknowledged = 1,
                acknowledged_by = ?,
                acknowledged_at = GETDATE()
            WHERE is_acknowledged = 0
        """, (username,))
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== COMPTEUR (pour la cloche) ====================

@router.get("/count")
async def get_alert_count():
    """Retourne le nombre d'alertes non acquittées des 24 dernières heures."""
    try:
        init_alert_tables()
        count = get_active_alerts_count(execute_query)
        return {"success": True, "count": count}
    except Exception as e:
        return {"success": True, "count": 0}


# ==================== ÉVALUATION MANUELLE ====================

@router.post("/evaluate")
async def trigger_evaluation(background_tasks: BackgroundTasks):
    """Déclenche manuellement l'évaluation de toutes les règles actives."""
    background_tasks.add_task(_run_evaluation)
    return {"success": True, "message": "Évaluation lancée en arrière-plan"}


async def _run_evaluation():
    from ..database_unified import execute_client, execute_dwh as _execute_dwh
    result = evaluate_all_alerts(execute_client, _execute_dwh)
    print(f"[ALERTS] Évaluation manuelle: {result}")


# ==================== SEED DÉMO (dev/demo only) ====================

@router.post("/seed-demo")
async def seed_demo_history():
    """Injecte des données demo dans l'historique des alertes."""
    from datetime import datetime, timedelta
    import random

    random.seed(42)

    demo_entries = [
        (1,  97.3,    "critical", "DSO critique : 97.3 j (seuil 90 j) — action immédiate requise.",              0, 0),
        (1,  94.1,    "critical", "DSO critique : 94.1 j (seuil 90 j) — action immédiate requise.",              2, 0),
        (1,  91.8,    "critical", "DSO critique : 91.8 j (seuil 90 j) — action immédiate requise.",              5, 1),
        (2,  73.5,    "warning",  "DSO élevé : 73.5 j (seuil 60 j) — suivi recommandé.",                        0, 0),
        (2,  68.2,    "warning",  "DSO élevé : 68.2 j (seuil 60 j) — suivi recommandé.",                        3, 1),
        (3,  23.7,    "critical", "Taux créances douteuses : 23.7% (seuil 20%) — revue immédiate nécessaire.",   1, 0),
        (4,  18.4,    "warning",  "Taux créances douteuses : 18.4% (seuil 15%) — surveillance accrue requise.",  0, 0),
        (4,  16.9,    "warning",  "Taux créances douteuses : 16.9% (seuil 15%) — surveillance accrue requise.",  4, 1),
        (5,  1247500, "critical", "Impayés critiques : 1 247 500 MAD (seuil 1 000 000 MAD) — relance urgente.",  0, 0),
        (5,  1089300, "critical", "Impayés critiques : 1 089 300 MAD (seuil 1 000 000 MAD) — relance urgente.",  3, 1),
        (6,  724800,  "warning",  "Impayés élevés : 724 800 MAD (seuil 500 000 MAD) — plan de recouvrement.",    0, 0),
        (6,  612400,  "warning",  "Impayés élevés : 612 400 MAD (seuil 500 000 MAD) — plan de recouvrement.",    6, 1),
        (7,  5843200, "critical", "Encours clients critique : 5 843 200 MAD (seuil 5 000 000 MAD).",             1, 0),
        (8,  4120000, "warning",  "Encours clients élevé : 4 120 000 MAD (seuil 3 000 000 MAD).",                0, 0),
        (8,  3680000, "warning",  "Encours clients élevé : 3 680 000 MAD (seuil 3 000 000 MAD).",                7, 1),
        (11, -14.3,   "warning",  "Évolution CA négative : -14.3% (seuil -10%) — analyse commerciale requise.",  2, 0),
        (9,  48.2,    "warning",  "Délai paiement moyen : 48.2 j (seuil 45 j) — suivi recouvrement.",            1, 0),
        (10, 238000,  "info",     "Nouvelles créances > 30 j : 238 000 MAD (seuil 200 000 MAD).",               8, 1),
    ]

    try:
        # Purge historique demo existant
        write_client("DELETE FROM APP_KPI_AlertHistory WHERE rule_id BETWEEN 1 AND 12")

        inserted = 0
        for rule_id, metric_value, niveau, message, days_ago, is_ack in demo_entries:
            h = random.randint(8, 17)
            mn = random.randint(0, 59)
            # Utiliser DATEADD côté SQL pour éviter les problèmes de format datetime
            minutes_ago = days_ago * 1440 + (24 - h) * 60 + (60 - mn)
            ack_min_offset = random.randint(60, 240)

            if is_ack:
                write_client(
                    """INSERT INTO APP_KPI_AlertHistory
                       (rule_id, metric_value, niveau, message, triggered_at,
                        is_acknowledged, acknowledged_by, acknowledged_at)
                       VALUES (?, ?, ?, ?, DATEADD(minute, -?, GETDATE()), 1, ?,
                               DATEADD(minute, -(? - ?), GETDATE()))""",
                    (rule_id, metric_value, niveau, message, minutes_ago,
                     "admin", minutes_ago, ack_min_offset)
                )
            else:
                write_client(
                    """INSERT INTO APP_KPI_AlertHistory
                       (rule_id, metric_value, niveau, message, triggered_at, is_acknowledged)
                       VALUES (?, ?, ?, ?, DATEADD(minute, -?, GETDATE()), 0)""",
                    (rule_id, metric_value, niveau, message, minutes_ago)
                )
            inserted += 1

        # Mise à jour last_triggered sur chaque règle
        for rid in set(e[0] for e in demo_entries):
            write_client(
                """UPDATE APP_KPI_AlertRules
                   SET last_triggered = (
                       SELECT TOP 1 triggered_at FROM APP_KPI_AlertHistory
                       WHERE rule_id = ? ORDER BY triggered_at DESC
                   ),
                   last_checked = GETDATE()
                   WHERE id = ?""",
                (rid, rid)
            )

        rows = execute_query(
            "SELECT COUNT(*) AS cnt FROM APP_KPI_AlertHistory WHERE rule_id BETWEEN 1 AND 12",
            use_cache=False
        )
        unread = execute_query(
            "SELECT COUNT(*) AS cnt FROM APP_KPI_AlertHistory WHERE rule_id BETWEEN 1 AND 12 AND is_acknowledged = 0",
            use_cache=False
        )
        return {
            "success": True,
            "inserted": inserted,
            "total": rows[0]["cnt"] if rows else 0,
            "unread": unread[0]["cnt"] if unread else 0,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
