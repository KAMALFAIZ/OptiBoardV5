"""
Templates d'alertes KPI — Base Maître
======================================
Gestion des modèles d'alertes dans la base centrale OptiBoard_SaaS.
Publication vers toutes les bases clients OptiBoard_XXX.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
import json
from datetime import datetime

from ..database_unified import (
    execute_central,
    write_central,
    execute_client,
    write_client,
)

router = APIRouter(prefix="/api/alerts/templates", tags=["alert-templates"])


# ==================== SCHEMAS ====================

class TemplateCreate(BaseModel):
    nom: str
    description: Optional[str] = None
    metric_type: str
    operator: str
    threshold_value: float
    niveau: str = "warning"
    notify_emails: Optional[List[str]] = None
    cooldown_hours: int = 4
    categorie: Optional[str] = "Finance"


class TemplateUpdate(BaseModel):
    nom: Optional[str] = None
    description: Optional[str] = None
    metric_type: Optional[str] = None
    operator: Optional[str] = None
    threshold_value: Optional[float] = None
    niveau: Optional[str] = None
    notify_emails: Optional[List[str]] = None
    cooldown_hours: Optional[int] = None
    categorie: Optional[str] = None


class PublishRequest(BaseModel):
    template_ids: Optional[List[int]] = None   # None = tous les templates actifs
    dwh_codes: Optional[List[str]] = None       # None = tous les clients actifs
    overwrite: bool = False                     # Ecraser si la règle existe déjà


# ==================== INIT TABLE ====================

def _init_templates_table():
    """Crée la table APP_KPI_AlertTemplates dans la base centrale si absente."""
    write_central("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'APP_KPI_AlertTemplates')
        CREATE TABLE APP_KPI_AlertTemplates (
            id               INT IDENTITY(1,1) PRIMARY KEY,
            nom              NVARCHAR(255)  NOT NULL,
            description      NVARCHAR(MAX),
            metric_type      NVARCHAR(100)  NOT NULL,
            operator         NVARCHAR(10)   NOT NULL,
            threshold_value  FLOAT          NOT NULL,
            niveau           NVARCHAR(20)   NOT NULL DEFAULT 'warning',
            notify_emails    NVARCHAR(MAX),
            cooldown_hours   INT            NOT NULL DEFAULT 4,
            categorie        NVARCHAR(100)  DEFAULT 'Finance',
            is_active        BIT            NOT NULL DEFAULT 1,
            published_count  INT            NOT NULL DEFAULT 0,
            last_published   DATETIME,
            created_at       DATETIME       DEFAULT GETDATE(),
            updated_at       DATETIME       DEFAULT GETDATE()
        )
    """)


def _ensure_client_alert_tables(dwh_code: str):
    """Crée APP_KPI_AlertRules + APP_KPI_AlertHistory dans la base client si absentes."""
    tables = [
        """
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'APP_KPI_AlertRules')
        CREATE TABLE APP_KPI_AlertRules (
            id              INT IDENTITY(1,1) PRIMARY KEY,
            nom             NVARCHAR(255)  NOT NULL,
            description     NVARCHAR(MAX),
            metric_type     NVARCHAR(100)  NOT NULL,
            operator        NVARCHAR(10)   NOT NULL,
            threshold_value FLOAT          NOT NULL,
            niveau          NVARCHAR(20)   NOT NULL DEFAULT 'warning',
            notify_emails   NVARCHAR(MAX),
            cooldown_hours  INT            NOT NULL DEFAULT 4,
            is_active       BIT            NOT NULL DEFAULT 1,
            last_checked    DATETIME,
            last_triggered  DATETIME,
            template_id     INT,
            created_at      DATETIME       DEFAULT GETDATE(),
            updated_at      DATETIME       DEFAULT GETDATE()
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
            acknowledged_at  DATETIME
        )
        """,
    ]
    for sql in tables:
        write_client(sql, dwh_code=dwh_code)


# ==================== CRUD TEMPLATES ====================

@router.get("")
async def list_templates():
    """Liste tous les templates d'alertes de la base maître."""
    try:
        _init_templates_table()
        rows = execute_central("""
            SELECT * FROM APP_KPI_AlertTemplates
            ORDER BY categorie, niveau DESC, nom
        """, use_cache=False)
        for r in rows:
            if r.get("notify_emails"):
                r["notify_emails"] = json.loads(r["notify_emails"])
            else:
                r["notify_emails"] = []
        return {"success": True, "data": rows}
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}


@router.post("")
async def create_template(t: TemplateCreate):
    """Crée un nouveau template dans la base maître."""
    try:
        _init_templates_table()
        write_central("""
            INSERT INTO APP_KPI_AlertTemplates
                (nom, description, metric_type, operator, threshold_value, niveau,
                 notify_emails, cooldown_hours, categorie)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            t.nom, t.description, t.metric_type, t.operator,
            t.threshold_value, t.niveau,
            json.dumps(t.notify_emails or []),
            t.cooldown_hours, t.categorie or "Finance"
        ))
        rows = execute_central(
            "SELECT TOP 1 id FROM APP_KPI_AlertTemplates ORDER BY id DESC",
            use_cache=False
        )
        return {"success": True, "id": rows[0]["id"] if rows else None, "message": "Template créé"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.put("/{template_id}")
async def update_template(template_id: int, t: TemplateUpdate):
    """Met à jour un template."""
    try:
        updates, params = [], []
        mapping = {
            "nom": t.nom, "description": t.description,
            "metric_type": t.metric_type, "operator": t.operator,
            "threshold_value": t.threshold_value, "niveau": t.niveau,
            "cooldown_hours": t.cooldown_hours, "categorie": t.categorie,
        }
        for col, val in mapping.items():
            if val is not None:
                updates.append(f"{col} = ?")
                params.append(val)
        if t.notify_emails is not None:
            updates.append("notify_emails = ?")
            params.append(json.dumps(t.notify_emails))
        if not updates:
            return {"success": False, "error": "Aucune modification"}
        updates.append("updated_at = GETDATE()")
        params.append(template_id)
        write_central(
            f"UPDATE APP_KPI_AlertTemplates SET {', '.join(updates)} WHERE id = ?",
            tuple(params)
        )
        return {"success": True, "message": "Template mis à jour"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.delete("/{template_id}")
async def delete_template(template_id: int):
    """Supprime un template."""
    try:
        write_central("DELETE FROM APP_KPI_AlertTemplates WHERE id = ?", (template_id,))
        return {"success": True, "message": "Template supprimé"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== PUBLICATION ====================

@router.post("/publish")
async def publish_templates(req: PublishRequest):
    """
    Publie les templates sélectionnés vers toutes les bases clients actives.
    Crée APP_KPI_AlertRules dans chaque OptiBoard_XXX client.
    """
    try:
        _init_templates_table()

        # 1. Récupérer les templates à publier
        if req.template_ids:
            placeholders = ",".join(["?" for _ in req.template_ids])
            templates = execute_central(
                f"SELECT * FROM APP_KPI_AlertTemplates WHERE id IN ({placeholders}) AND is_active = 1",
                tuple(req.template_ids), use_cache=False
            )
        else:
            templates = execute_central(
                "SELECT * FROM APP_KPI_AlertTemplates WHERE is_active = 1",
                use_cache=False
            )

        if not templates:
            return {"success": False, "error": "Aucun template actif sélectionné"}

        # 2. Récupérer les clients DWH cibles
        if req.dwh_codes:
            placeholders = ",".join(["?" for _ in req.dwh_codes])
            clients = execute_central(
                f"SELECT code, nom FROM APP_DWH WHERE actif = 1 AND code IN ({placeholders})",
                tuple(req.dwh_codes), use_cache=False
            )
        else:
            clients = execute_central(
                "SELECT code, nom FROM APP_DWH WHERE actif = 1 ORDER BY nom",
                use_cache=False
            )

        if not clients:
            return {"success": False, "error": "Aucun client actif trouvé"}

        # 3. Publication vers chaque client
        results = []
        total_created = 0
        total_skipped = 0
        total_errors = 0

        for client in clients:
            dwh_code = client["code"]
            client_results = {"client": dwh_code, "nom": client.get("nom", dwh_code),
                              "created": 0, "skipped": 0, "errors": []}
            try:
                # Créer les tables si elles n'existent pas
                _ensure_client_alert_tables(dwh_code)

                for tmpl in templates:
                    emails_json = json.dumps(
                        json.loads(tmpl["notify_emails"]) if tmpl.get("notify_emails") else []
                    )
                    try:
                        # Vérifier si une règle avec le même nom existe déjà
                        existing = execute_client(
                            "SELECT id FROM APP_KPI_AlertRules WHERE nom = ? AND metric_type = ?",
                            (tmpl["nom"], tmpl["metric_type"]),
                            dwh_code=dwh_code, use_cache=False
                        )

                        if existing and not req.overwrite:
                            client_results["skipped"] += 1
                            total_skipped += 1
                            continue

                        if existing and req.overwrite:
                            # Mise à jour de la règle existante
                            write_client("""
                                UPDATE APP_KPI_AlertRules
                                SET description = ?, operator = ?, threshold_value = ?,
                                    niveau = ?, notify_emails = ?, cooldown_hours = ?,
                                    template_id = ?, updated_at = GETDATE()
                                WHERE id = ?
                            """, (
                                tmpl.get("description"), tmpl["operator"],
                                tmpl["threshold_value"], tmpl["niveau"],
                                emails_json, tmpl["cooldown_hours"],
                                tmpl["id"], existing[0]["id"]
                            ), dwh_code=dwh_code)
                        else:
                            # Insertion nouvelle règle
                            write_client("""
                                INSERT INTO APP_KPI_AlertRules
                                    (nom, description, metric_type, operator, threshold_value,
                                     niveau, notify_emails, cooldown_hours, template_id)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                tmpl["nom"], tmpl.get("description"),
                                tmpl["metric_type"], tmpl["operator"],
                                tmpl["threshold_value"], tmpl["niveau"],
                                emails_json, tmpl["cooldown_hours"], tmpl["id"]
                            ), dwh_code=dwh_code)

                        client_results["created"] += 1
                        total_created += 1
                    except Exception as e_rule:
                        client_results["errors"].append(str(e_rule)[:100])
                        total_errors += 1

            except Exception as e_client:
                client_results["errors"].append(f"Connexion client: {str(e_client)[:100]}")
                total_errors += 1

            results.append(client_results)

        # 4. Mettre à jour les compteurs dans les templates
        for tmpl in templates:
            write_central("""
                UPDATE APP_KPI_AlertTemplates
                SET published_count = published_count + ?,
                    last_published = GETDATE(),
                    updated_at = GETDATE()
                WHERE id = ?
            """, (len(clients), tmpl["id"]))

        return {
            "success": True,
            "message": f"{total_created} règle(s) créée(s) sur {len(clients)} client(s)",
            "total_created": total_created,
            "total_skipped": total_skipped,
            "total_errors": total_errors,
            "clients_count": len(clients),
            "templates_count": len(templates),
            "details": results,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== SEED TEMPLATES DEMO ====================

@router.post("/seed-demo")
async def seed_demo_templates():
    """Charge les templates standards dans la base maître."""
    try:
        _init_templates_table()

        # Vider les templates existants
        write_central("DELETE FROM APP_KPI_AlertTemplates")

        templates = [
            # ── Recouvrement ──────────────────────────────────────────────
            ("DSO Critique (>90 j)", "Jours de Solde Débiteur critique — risque trésorerie majeur",
             "dso", "gt", 90, "critical", ["direction@client.ma"], 6, "Recouvrement"),
            ("DSO Élevé (>60 j)", "Surveiller si le DSO dépasse 60 jours",
             "dso", "gt", 60, "warning", ["finance@client.ma"], 12, "Recouvrement"),
            ("Impayés Critiques (>1M MAD)", "Montant des impayés supérieur à 1 000 000 MAD",
             "impayes", "gt", 1000000, "critical", ["direction@client.ma"], 4, "Recouvrement"),
            ("Impayés Élevés (>500k MAD)", "Surveiller si les impayés dépassent 500 000 MAD",
             "impayes", "gt", 500000, "warning", ["finance@client.ma"], 8, "Recouvrement"),
            ("Taux Créances Douteuses Critique (>20%)", "Taux de créances douteuses supérieur à 20%",
             "taux_creances", "gt", 20, "critical", ["direction@client.ma", "recouvrement@client.ma"], 4, "Recouvrement"),
            ("Taux Créances Douteuses Élevé (>15%)", "Taux de créances douteuses supérieur à 15%",
             "taux_creances", "gt", 15, "warning", ["recouvrement@client.ma"], 8, "Recouvrement"),
            ("Taux de Recouvrement Faible (<70%)", "Taux de recouvrement mensuel inférieur à 70%",
             "taux_recouvrement", "lt", 70, "warning", ["recouvrement@client.ma"], 24, "Recouvrement"),
            # ── Encours ───────────────────────────────────────────────────
            ("Encours Clients Critique (>5M MAD)", "Encours total clients supérieur à 5 000 000 MAD",
             "encours_clients", "gt", 5000000, "critical", ["direction@client.ma", "credit@client.ma"], 6, "Encours"),
            ("Encours Clients Élevé (>3M MAD)", "Encours total clients supérieur à 3 000 000 MAD",
             "encours_clients", "gt", 3000000, "warning", ["finance@client.ma"], 12, "Encours"),
            ("Délai Paiement Moyen Dégradé (>45 j)", "Délai de paiement moyen supérieur à 45 jours",
             "delai_paiement", "gt", 45, "warning", ["recouvrement@client.ma"], 24, "Encours"),
            # ── Commercial ────────────────────────────────────────────────
            ("Évolution CA Négative (<-10%)", "Baisse de chiffre d'affaires supérieure à 10%",
             "evolution_ca", "lt", -10, "warning", ["direction@client.ma", "commercial@client.ma"], 24, "Commercial"),
            ("Nouvelles Créances >30 j (>200k MAD)", "Nouvelles créances de plus de 30 jours dépassent 200 000 MAD",
             "nouvelles_creances", "gt", 200000, "info", ["recouvrement@client.ma"], 48, "Commercial"),
        ]

        inserted = 0
        for nom, desc, metric, op, seuil, niveau, emails, cooldown, cat in templates:
            write_central("""
                INSERT INTO APP_KPI_AlertTemplates
                    (nom, description, metric_type, operator, threshold_value,
                     niveau, notify_emails, cooldown_hours, categorie)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (nom, desc, metric, op, seuil, niveau, json.dumps(emails), cooldown, cat))
            inserted += 1

        return {"success": True, "inserted": inserted, "message": f"{inserted} templates chargés"}
    except Exception as e:
        return {"success": False, "error": str(e)}
