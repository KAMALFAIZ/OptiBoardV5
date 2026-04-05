"""Couche base de données KAsoft Hub (SQL Server via pyodbc)"""
import logging
import pyodbc
from typing import Any, Optional
from .config import get_settings

logger = logging.getLogger(__name__)

_conn: Optional[pyodbc.Connection] = None


def _get_connection() -> pyodbc.Connection:
    global _conn
    settings = get_settings()
    try:
        if _conn:
            _conn.cursor().execute("SELECT 1")
            return _conn
    except Exception:
        _conn = None

    _conn = pyodbc.connect(settings.connection_string, autocommit=False)
    return _conn


def execute(query: str, params: tuple = (), use_cache: bool = False) -> list[dict]:
    """Exécute une requête SELECT, retourne une liste de dicts."""
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        logger.error(f"[DB] execute error: {e} | query: {query[:120]}")
        raise


def write(query: str, params: tuple = ()) -> int:
    """Exécute INSERT/UPDATE/DELETE, retourne rowcount."""
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor.rowcount
    except Exception as e:
        conn.rollback()
        logger.error(f"[DB] write error: {e} | query: {query[:120]}")
        raise


def write_returning_id(query: str, params: tuple = ()) -> Optional[int]:
    """INSERT avec récupération de l'ID généré (SCOPE_IDENTITY)."""
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query + "; SELECT SCOPE_IDENTITY()", params)
        cursor.nextset()
        row = cursor.fetchone()
        conn.commit()
        return int(row[0]) if row and row[0] else None
    except Exception as e:
        conn.rollback()
        logger.error(f"[DB] write_returning_id error: {e}")
        raise


def init_tables():
    """Crée toutes les tables HUB_* si elles n'existent pas."""
    statements = [
        # Produits
        """
        IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name='HUB_Products')
        CREATE TABLE HUB_Products (
            id          INT IDENTITY(1,1) PRIMARY KEY,
            code        NVARCHAR(30)  NOT NULL UNIQUE,
            nom         NVARCHAR(100) NOT NULL,
            description NVARCHAR(500) NULL,
            webhook_secret NVARCHAR(100) NOT NULL,
            couleur     NVARCHAR(20)  NOT NULL DEFAULT '#3B82F6',
            actif       BIT           NOT NULL DEFAULT 1,
            created_at  DATETIME      NOT NULL DEFAULT GETDATE()
        )
        """,
        # Seed produits par défaut
        """
        IF NOT EXISTS (SELECT 1 FROM HUB_Products WHERE code='OPTIBOARD')
        INSERT INTO HUB_Products (code, nom, description, webhook_secret, couleur)
        VALUES
          ('OPTIBOARD',     'OptiBoard',      'BI & Reporting Commercial', NEWID(), '#059669'),
          ('OPTIBTP',       'OptiBTP',        'Gestion BTP',               NEWID(), '#F59E0B'),
          ('OPTICRM',       'OptiCRM',        'CRM & Relation Client',     NEWID(), '#3B82F6'),
          ('OPTIPROMIMMO',  'OptiPromImmo',   'Promotion Immobilière',     NEWID(), '#8B5CF6')
        """,
        # Contacts unifiés
        """
        IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name='HUB_Contacts')
        CREATE TABLE HUB_Contacts (
            id              INT IDENTITY(1,1) PRIMARY KEY,
            product_code    NVARCHAR(30)  NOT NULL,
            external_id     NVARCHAR(100) NULL,
            nom             NVARCHAR(100) NOT NULL,
            prenom          NVARCHAR(100) NULL,
            email           NVARCHAR(200) NULL,
            telephone       NVARCHAR(30)  NULL,
            whatsapp        NVARCHAR(30)  NULL,
            telegram_chat_id NVARCHAR(50) NULL,
            societe         NVARCHAR(200) NULL,
            poste           NVARCHAR(100) NULL,
            segment         NVARCHAR(20)  NOT NULL DEFAULT 'prospect',
            source          NVARCHAR(30)  NOT NULL DEFAULT 'manual',
            tags            NVARCHAR(500) NULL,
            notes           NVARCHAR(MAX) NULL,
            actif           BIT           NOT NULL DEFAULT 1,
            created_at      DATETIME      NOT NULL DEFAULT GETDATE(),
            updated_at      DATETIME      NOT NULL DEFAULT GETDATE()
        )
        """,
        # Templates messages
        """
        IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name='HUB_Templates')
        CREATE TABLE HUB_Templates (
            id           INT IDENTITY(1,1) PRIMARY KEY,
            product_code NVARCHAR(30)  NOT NULL DEFAULT 'ALL',
            nom          NVARCHAR(100) NOT NULL,
            channel      NVARCHAR(20)  NOT NULL,
            sujet        NVARCHAR(200) NULL,
            contenu      NVARCHAR(MAX) NOT NULL,
            variables    NVARCHAR(500) NULL,
            created_at   DATETIME      NOT NULL DEFAULT GETDATE(),
            updated_at   DATETIME      NOT NULL DEFAULT GETDATE()
        )
        """,
        # Campagnes marketing
        """
        IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name='HUB_Campaigns')
        CREATE TABLE HUB_Campaigns (
            id           INT IDENTITY(1,1) PRIMARY KEY,
            product_code NVARCHAR(30)  NOT NULL DEFAULT 'ALL',
            nom          NVARCHAR(100) NOT NULL,
            type_camp    NVARCHAR(30)  NOT NULL DEFAULT 'nurturing',
            channel      NVARCHAR(20)  NOT NULL DEFAULT 'multi',
            description  NVARCHAR(500) NULL,
            statut       NVARCHAR(20)  NOT NULL DEFAULT 'draft',
            segment_cible NVARCHAR(20) NULL,
            created_at   DATETIME      NOT NULL DEFAULT GETDATE(),
            updated_at   DATETIME      NOT NULL DEFAULT GETDATE()
        )
        """,
        # Étapes campagnes
        """
        IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name='HUB_CampaignSteps')
        CREATE TABLE HUB_CampaignSteps (
            id           INT IDENTITY(1,1) PRIMARY KEY,
            campaign_id  INT           NOT NULL,
            step_order   INT           NOT NULL DEFAULT 1,
            delay_days   INT           NOT NULL DEFAULT 0,
            channel      NVARCHAR(20)  NOT NULL,
            template_id  INT           NULL,
            condition_type NVARCHAR(30) NOT NULL DEFAULT 'always',
            actif        BIT           NOT NULL DEFAULT 1
        )
        """,
        # Enrollments contacts dans campagnes
        """
        IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name='HUB_CampaignEnrollments')
        CREATE TABLE HUB_CampaignEnrollments (
            id           INT IDENTITY(1,1) PRIMARY KEY,
            campaign_id  INT           NOT NULL,
            contact_id   INT           NOT NULL,
            current_step INT           NOT NULL DEFAULT 0,
            next_send_at DATETIME      NULL,
            statut       NVARCHAR(20)  NOT NULL DEFAULT 'active',
            enrolled_at  DATETIME      NOT NULL DEFAULT GETDATE(),
            completed_at DATETIME      NULL
        )
        """,
        # Tickets SAV
        """
        IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name='HUB_Tickets')
        CREATE TABLE HUB_Tickets (
            id              INT IDENTITY(1,1) PRIMARY KEY,
            product_code    NVARCHAR(30)  NOT NULL,
            contact_id      INT           NULL,
            numero          NVARCHAR(20)  NOT NULL UNIQUE,
            sujet           NVARCHAR(300) NOT NULL,
            description     NVARCHAR(MAX) NULL,
            priorite        NVARCHAR(20)  NOT NULL DEFAULT 'medium',
            statut          NVARCHAR(20)  NOT NULL DEFAULT 'open',
            canal_ouverture NVARCHAR(20)  NOT NULL DEFAULT 'manual',
            assigned_to     NVARCHAR(100) NULL,
            sla_hours       INT           NOT NULL DEFAULT 24,
            created_at      DATETIME      NOT NULL DEFAULT GETDATE(),
            updated_at      DATETIME      NOT NULL DEFAULT GETDATE(),
            resolved_at     DATETIME      NULL
        )
        """,
        # Messages tickets
        """
        IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name='HUB_TicketMessages')
        CREATE TABLE HUB_TicketMessages (
            id         INT IDENTITY(1,1) PRIMARY KEY,
            ticket_id  INT           NOT NULL,
            direction  NVARCHAR(5)   NOT NULL DEFAULT 'out',
            channel    NVARCHAR(20)  NOT NULL DEFAULT 'manual',
            contenu    NVARCHAR(MAX) NOT NULL,
            sent_by    NVARCHAR(50)  NOT NULL DEFAULT 'agent',
            sent_at    DATETIME      NOT NULL DEFAULT GETDATE()
        )
        """,
        # Workflows automation
        """
        IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name='HUB_Workflows')
        CREATE TABLE HUB_Workflows (
            id                  INT IDENTITY(1,1) PRIMARY KEY,
            product_code        NVARCHAR(30)  NOT NULL DEFAULT 'ALL',
            nom                 NVARCHAR(100) NOT NULL,
            trigger_event       NVARCHAR(50)  NOT NULL,
            trigger_condition   NVARCHAR(MAX) NULL,
            actions             NVARCHAR(MAX) NOT NULL,
            is_active           BIT           NOT NULL DEFAULT 1,
            executions_count    INT           NOT NULL DEFAULT 0,
            created_at          DATETIME      NOT NULL DEFAULT GETDATE(),
            updated_at          DATETIME      NOT NULL DEFAULT GETDATE()
        )
        """,
        # Événements entrants (webhooks)
        """
        IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name='HUB_Events')
        CREATE TABLE HUB_Events (
            id           INT IDENTITY(1,1) PRIMARY KEY,
            product_code NVARCHAR(30)  NOT NULL,
            event_type   NVARCHAR(50)  NOT NULL,
            payload      NVARCHAR(MAX) NOT NULL,
            processed    BIT           NOT NULL DEFAULT 0,
            error_msg    NVARCHAR(500) NULL,
            created_at   DATETIME      NOT NULL DEFAULT GETDATE(),
            processed_at DATETIME      NULL
        )
        """,
        # Log des envois
        """
        IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name='HUB_DeliveryLog')
        CREATE TABLE HUB_DeliveryLog (
            id           INT IDENTITY(1,1) PRIMARY KEY,
            contact_id   INT           NULL,
            ticket_id    INT           NULL,
            channel      NVARCHAR(20)  NOT NULL,
            template_id  INT           NULL,
            recipient    NVARCHAR(200) NOT NULL,
            statut       NVARCHAR(20)  NOT NULL DEFAULT 'pending',
            error_msg    NVARCHAR(500) NULL,
            sent_at      DATETIME      NOT NULL DEFAULT GETDATE()
        )
        """,
        # Config canaux (Telegram/WhatsApp/Email)
        """
        IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name='HUB_ChannelConfig')
        CREATE TABLE HUB_ChannelConfig (
            id                   INT IDENTITY(1,1) PRIMARY KEY,
            telegram_bot_token   NVARCHAR(200) NULL,
            twilio_account_sid   NVARCHAR(100) NULL,
            twilio_auth_token    NVARCHAR(100) NULL,
            twilio_whatsapp_from NVARCHAR(30)  NULL,
            smtp_host            NVARCHAR(100) NULL,
            smtp_port            INT           NULL DEFAULT 587,
            smtp_user            NVARCHAR(200) NULL,
            smtp_password        NVARCHAR(200) NULL,
            smtp_from_name       NVARCHAR(100) NULL,
            smtp_use_ssl         BIT           NOT NULL DEFAULT 0,
            smtp_use_tls         BIT           NOT NULL DEFAULT 1,
            updated_at           DATETIME      NOT NULL DEFAULT GETDATE()
        )
        """,
        """
        IF NOT EXISTS (SELECT 1 FROM HUB_ChannelConfig WHERE id=1)
        INSERT INTO HUB_ChannelConfig DEFAULT VALUES
        """,
    ]
    for sql in statements:
        try:
            write(sql)
        except Exception as e:
            logger.error(f"[DB] init_tables error: {e}")
