"""
Gestion des DWH Clients — Architecture Multi-Tenant
=====================================================
Routes d'administration dédiées :
  - CRUD des clients DWH (APP_DWH)
  - Sources Sage (APP_DWH_Sources)
  - Configuration SMTP
  - Bases client OptiBoard_XXX (création, sync, reset, statut)
  - Migration globale

Règles d'architecture implémentées :
  Règle 1 — is_customized : les lignes marquées is_customized=1 dans
            une base client ne sont JAMAIS écrasées lors d'un sync Master.
  Règle 2 — APP_Users dans chaque OptiBoard_cltxx : les utilisateurs
            d'un client sont stockés directement dans leur base client.
  Règle 3 — Même serveur / même port : le TenantContextMiddleware gère
            l'isolation par X-DWH-Code quel que soit le serveur physique.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import pyodbc
from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel

from ..database_unified import (
    client_manager,
    execute_query,
    execute_central,
    write_central,
    get_db_cursor,
    get_central_connection,
)

logger = logging.getLogger("DWHAdmin")

router = APIRouter(prefix="/api", tags=["dwh-admin"])

# Bases protegees contre la suppression / reset
PROTECTED_DWH_CODES = {"KA"}  # Kasoft-Démo : client de démonstration protégé


# =============================================================================
# SCHEMAS PYDANTIC
# =============================================================================

class DWHCreate(BaseModel):
    code: str
    nom: str
    raison_sociale: Optional[str] = None
    adresse: Optional[str] = None
    ville: Optional[str] = None
    pays: str = "Maroc"
    telephone: Optional[str] = None
    email: Optional[str] = None
    logo_url: Optional[str] = None
    # Connexion base DWH métier (Sage)
    serveur_dwh: str
    base_dwh: str
    user_dwh: str
    password_dwh: str
    # Connexion base OptiBoard client (peut différer du DWH)
    serveur_optiboard: Optional[str] = None
    base_optiboard: Optional[str] = None
    user_optiboard: Optional[str] = None
    password_optiboard: Optional[str] = None
    actif: bool = True


class DWHUpdate(BaseModel):
    nom: Optional[str] = None
    raison_sociale: Optional[str] = None
    adresse: Optional[str] = None
    ville: Optional[str] = None
    pays: Optional[str] = None
    telephone: Optional[str] = None
    email: Optional[str] = None
    logo_url: Optional[str] = None
    # Connexion base DWH métier
    serveur_dwh: Optional[str] = None
    base_dwh: Optional[str] = None
    user_dwh: Optional[str] = None
    password_dwh: Optional[str] = None       # None = ne pas changer
    # Connexion base OptiBoard client
    serveur_optiboard: Optional[str] = None
    base_optiboard: Optional[str] = None
    user_optiboard: Optional[str] = None
    password_optiboard: Optional[str] = None  # None = ne pas changer
    actif: Optional[bool] = None


class SMTPConfig(BaseModel):
    smtp_server: str
    smtp_port: int = 587
    smtp_username: str
    smtp_password: str
    from_email: str
    from_name: str
    use_tls: bool = True


class TestConnectionRequest(BaseModel):
    serveur: str
    base: str
    user: str
    password: str


class SyncDataRequest(BaseModel):
    tables: Optional[List[str]] = None
    mode: str = "upsert"  # upsert (respecte is_customized) | replace (force tout)


class ResetClientDBRequest(BaseModel):
    confirm: bool
    keep_user_data: bool = True


# =============================================================================
# SQL — TABLES DE LA BASE CLIENT OptiBoard_XXX
# =============================================================================
# Règle 1 : is_customized BIT DEFAULT 0 sur toutes les tables de config.
#            Quand un client personnalise une ligne, il passe is_customized=1
#            → protégée des syncs Master ultérieurs.
# Règle 2 : APP_Users est présente dans chaque base client.

CLIENT_OPTIBOARD_TABLES_SQL = """
-- =========================================================
-- PERMISSIONS UTILISATEURS
-- =========================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_UserPages' AND xtype='U')
CREATE TABLE APP_UserPages (
    id         INT IDENTITY(1,1) PRIMARY KEY,
    user_id    INT NOT NULL,
    page_code  VARCHAR(50) NOT NULL
);

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_UserMenus' AND xtype='U')
CREATE TABLE APP_UserMenus (
    id         INT IDENTITY(1,1) PRIMARY KEY,
    user_id    INT NOT NULL,
    menu_id    INT NOT NULL,
    can_view   BIT DEFAULT 1,
    can_export BIT DEFAULT 1
);

-- =========================================================
-- RÈGLE 2 — Utilisateurs propres à chaque base client
-- =========================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Users' AND xtype='U')
CREATE TABLE APP_Users (
    id                    INT IDENTITY(1,1) PRIMARY KEY,
    username              VARCHAR(100) UNIQUE NOT NULL,
    password_hash         VARCHAR(200) NULL,           -- NULL = premier login, mot de passe pas encore defini
    nom                   NVARCHAR(200),
    prenom                NVARCHAR(100),
    email                 VARCHAR(200),
    role_dwh              VARCHAR(50) DEFAULT 'user',  -- admin_client | user | viewer
    actif                 BIT DEFAULT 1,
    must_change_password  BIT DEFAULT 0,               -- 1 = premier login, forcer creation mot de passe
    derniere_connexion    DATETIME NULL,
    date_creation         DATETIME DEFAULT GETDATE()
);

-- =========================================================
-- CONFIG APPLICATION (Règle 1 — is_customized)
-- =========================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Dashboards' AND xtype='U')
CREATE TABLE APP_Dashboards (
    id                INT IDENTITY(1,1) PRIMARY KEY,
    nom               NVARCHAR(200) NOT NULL,
    code              VARCHAR(100) NULL,
    description       NVARCHAR(500),
    config            NVARCHAR(MAX),
    widgets           NVARCHAR(MAX),
    is_public         BIT DEFAULT 0,
    is_custom         BIT DEFAULT 0,
    is_customized     BIT DEFAULT 0,   -- Règle 1 : 1 = protégé du sync Master
    created_by        INT NULL,
    actif             BIT DEFAULT 1,
    date_creation     DATETIME DEFAULT GETDATE(),
    date_modification DATETIME DEFAULT GETDATE()
);

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_DataSources' AND xtype='U')
CREATE TABLE APP_DataSources (
    id                INT IDENTITY(1,1) PRIMARY KEY,
    nom               NVARCHAR(200) NOT NULL,
    code              VARCHAR(100) NULL,
    type              VARCHAR(50) NOT NULL DEFAULT 'query',
    query_template    NVARCHAR(MAX),
    parameters        NVARCHAR(MAX),
    description       NVARCHAR(500),
    is_custom         BIT DEFAULT 0,
    is_customized     BIT DEFAULT 0,   -- Règle 1
    date_creation     DATETIME DEFAULT GETDATE()
);

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_GridViews' AND xtype='U')
CREATE TABLE APP_GridViews (
    id                INT IDENTITY(1,1) PRIMARY KEY,
    nom               NVARCHAR(200) NOT NULL,
    code              VARCHAR(100) NULL,
    description       NVARCHAR(500),
    query_template    NVARCHAR(MAX),
    columns_config    NVARCHAR(MAX),
    parameters        NVARCHAR(MAX),
    features          NVARCHAR(MAX),
    is_custom         BIT DEFAULT 0,
    is_customized     BIT DEFAULT 0,   -- Règle 1
    actif             BIT DEFAULT 1,
    date_creation     DATETIME DEFAULT GETDATE(),
    date_modification DATETIME DEFAULT GETDATE()
);

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_GridView_User_Prefs' AND xtype='U')
CREATE TABLE APP_GridView_User_Prefs (
    id                INT IDENTITY(1,1) PRIMARY KEY,
    gridview_id       INT NOT NULL,
    user_id           INT NOT NULL,
    columns_config    NVARCHAR(MAX),
    date_modification DATETIME DEFAULT GETDATE(),
    CONSTRAINT UQ_GridView_User UNIQUE (gridview_id, user_id)
);

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Pivots' AND xtype='U')
CREATE TABLE APP_Pivots (
    id                INT IDENTITY(1,1) PRIMARY KEY,
    nom               NVARCHAR(200) NOT NULL,
    description       NVARCHAR(500),
    query_template    NVARCHAR(MAX),
    pivot_config      NVARCHAR(MAX),
    parameters        NVARCHAR(MAX),
    actif             BIT DEFAULT 1,
    date_creation     DATETIME DEFAULT GETDATE(),
    date_modification DATETIME DEFAULT GETDATE()
);

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Pivots_V2' AND xtype='U')
CREATE TABLE APP_Pivots_V2 (
    id                     INT IDENTITY(1,1) PRIMARY KEY,
    nom                    NVARCHAR(200) NOT NULL,
    code                   VARCHAR(100) NULL,
    description            NVARCHAR(500),
    data_source_id         INT NULL,
    data_source_code       VARCHAR(100),
    rows_config            NVARCHAR(MAX),
    columns_config         NVARCHAR(MAX),
    filters_config         NVARCHAR(MAX),
    values_config          NVARCHAR(MAX),
    show_grand_totals      BIT DEFAULT 1,
    show_subtotals         BIT DEFAULT 0,
    show_row_percent       BIT DEFAULT 0,
    show_col_percent       BIT DEFAULT 0,
    show_total_percent     BIT DEFAULT 0,
    comparison_mode        NVARCHAR(50),
    formatting_rules       NVARCHAR(MAX),
    source_params          NVARCHAR(MAX),
    is_public              BIT DEFAULT 0,
    is_custom              BIT DEFAULT 0,
    is_customized          BIT DEFAULT 0,   -- Règle 1
    created_by             INT NULL,
    created_at             DATETIME DEFAULT GETDATE(),
    updated_at             DATETIME DEFAULT GETDATE(),
    grand_total_position   NVARCHAR(20) DEFAULT 'bottom',
    subtotal_position      NVARCHAR(20) DEFAULT 'bottom',
    show_summary_row       BIT DEFAULT 0,
    summary_functions      NVARCHAR(MAX),
    window_calculations    NVARCHAR(MAX)
);

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Pivot_User_Prefs' AND xtype='U')
CREATE TABLE APP_Pivot_User_Prefs (
    id                INT IDENTITY(1,1) PRIMARY KEY,
    pivot_id          INT NOT NULL,
    user_id           INT NOT NULL,
    custom_config     NVARCHAR(MAX),
    date_modification DATETIME DEFAULT GETDATE(),
    CONSTRAINT UQ_Pivot_User UNIQUE (pivot_id, user_id)
);

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Menus' AND xtype='U')
CREATE TABLE APP_Menus (
    id            INT IDENTITY(1,1) PRIMARY KEY,
    nom           NVARCHAR(100) NOT NULL,
    code          VARCHAR(100),
    icon          VARCHAR(50),
    url           VARCHAR(200),
    parent_id     INT NULL,
    ordre         INT DEFAULT 0,
    type          VARCHAR(20) DEFAULT 'link',
    target_id     INT NULL,
    actif         BIT DEFAULT 1,
    is_custom     BIT DEFAULT 0,
    is_customized BIT DEFAULT 0,   -- Règle 1
    roles         NVARCHAR(200),
    date_creation DATETIME DEFAULT GETDATE()
);

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_EmailConfig' AND xtype='U')
CREATE TABLE APP_EmailConfig (
    id                INT IDENTITY(1,1) PRIMARY KEY,
    smtp_server       VARCHAR(200),
    smtp_port         INT DEFAULT 587,
    smtp_username     VARCHAR(200),
    smtp_password     VARCHAR(200),
    from_email        VARCHAR(200),
    from_name         NVARCHAR(100),
    use_ssl           BIT DEFAULT 0,
    use_tls           BIT DEFAULT 1,
    actif             BIT DEFAULT 1,
    date_modification DATETIME DEFAULT GETDATE()
);

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Settings' AND xtype='U')
CREATE TABLE APP_Settings (
    id                INT IDENTITY(1,1) PRIMARY KEY,
    setting_key       VARCHAR(100) NOT NULL,
    setting_value     NVARCHAR(MAX),
    setting_type      VARCHAR(20) DEFAULT 'string',
    description       NVARCHAR(500),
    date_modification DATETIME DEFAULT GETDATE()
);

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ReportSchedules' AND xtype='U')
CREATE TABLE APP_ReportSchedules (
    id             INT IDENTITY(1,1) PRIMARY KEY,
    nom            NVARCHAR(255) NOT NULL,
    description    NVARCHAR(MAX),
    report_type    NVARCHAR(50) NOT NULL,
    report_id      INT,
    export_format  NVARCHAR(20) DEFAULT 'excel',
    frequency      NVARCHAR(20) NOT NULL,
    schedule_time  NVARCHAR(10) DEFAULT '08:00',
    schedule_day   INT,
    recipients     NVARCHAR(MAX) NOT NULL,
    cc_recipients  NVARCHAR(MAX),
    filters        NVARCHAR(MAX),
    is_active      BIT DEFAULT 1,
    last_run       DATETIME,
    next_run       DATETIME,
    created_by     INT,
    created_at     DATETIME DEFAULT GETDATE(),
    updated_at     DATETIME DEFAULT GETDATE()
);

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ReportHistory' AND xtype='U')
CREATE TABLE APP_ReportHistory (
    id           INT IDENTITY(1,1) PRIMARY KEY,
    schedule_id  INT,
    report_name  NVARCHAR(255),
    recipients   NVARCHAR(MAX),
    status       NVARCHAR(20) NOT NULL,
    error_message NVARCHAR(MAX),
    file_path    NVARCHAR(500),
    file_size    INT,
    sent_at      DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (schedule_id) REFERENCES APP_ReportSchedules(id) ON DELETE SET NULL
);

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_AuditLog' AND xtype='U')
CREATE TABLE APP_AuditLog (
    id          BIGINT IDENTITY(1,1) PRIMARY KEY,
    user_id     INT NULL,
    action      VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50),
    entity_id   INT NULL,
    details     NVARCHAR(MAX),
    ip_address  VARCHAR(50),
    user_agent  NVARCHAR(500),
    date_action DATETIME DEFAULT GETDATE()
);

-- =========================================================
-- MIGRATIONS — colonnes manquantes sur bases existantes
-- =========================================================
-- Règle 1 : ajouter is_customized aux tables existantes
IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_GridViews') AND name='is_customized')
    ALTER TABLE APP_GridViews ADD is_customized BIT DEFAULT 0;
IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_Pivots_V2') AND name='is_customized')
    ALTER TABLE APP_Pivots_V2 ADD is_customized BIT DEFAULT 0;
IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_Dashboards') AND name='is_customized')
    ALTER TABLE APP_Dashboards ADD is_customized BIT DEFAULT 0;
IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_DataSources') AND name='is_customized')
    ALTER TABLE APP_DataSources ADD is_customized BIT DEFAULT 0;
IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_Menus') AND name='is_customized')
    ALTER TABLE APP_Menus ADD is_customized BIT DEFAULT 0;

-- code sur les tables qui ne l'ont pas encore
IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_GridViews') AND name='code')
    ALTER TABLE APP_GridViews ADD code VARCHAR(100) NULL;
IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_Pivots_V2') AND name='code')
    ALTER TABLE APP_Pivots_V2 ADD code VARCHAR(100) NULL;
IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_Dashboards') AND name='code')
    ALTER TABLE APP_Dashboards ADD code VARCHAR(100) NULL;
IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('APP_DataSources') AND name='code')
    ALTER TABLE APP_DataSources ADD code VARCHAR(100) NULL;

-- Règle 2 : ajouter APP_Users si absente
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Users' AND xtype='U')
CREATE TABLE APP_Users (
    id                  INT IDENTITY(1,1) PRIMARY KEY,
    username            VARCHAR(100) UNIQUE NOT NULL,
    password_hash       VARCHAR(200) NOT NULL,
    nom                 NVARCHAR(200),
    prenom              NVARCHAR(100),
    email               VARCHAR(200),
    role_dwh            VARCHAR(50) DEFAULT 'user',
    actif               BIT DEFAULT 1,
    derniere_connexion  DATETIME NULL,
    date_creation       DATETIME DEFAULT GETDATE()
);

-- =========================================================
-- ETL TABLES CLIENT — tables propres (non publiees par KASOFT)
-- =========================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Tables_Config' AND xtype='U')
CREATE TABLE APP_ETL_Tables_Config (
    id                  INT IDENTITY(1,1) PRIMARY KEY,
    code                VARCHAR(100) NOT NULL UNIQUE,
    table_name          NVARCHAR(100) NOT NULL,
    target_table        NVARCHAR(100) NOT NULL,
    source_query        NVARCHAR(MAX) NOT NULL,
    primary_key_columns NVARCHAR(500) NOT NULL,
    sync_type           VARCHAR(20)   DEFAULT 'incremental',
    timestamp_column    NVARCHAR(100) DEFAULT 'cbModification',
    interval_minutes    INT           DEFAULT 5,
    priority            VARCHAR(20)   DEFAULT 'normal',
    delete_detection    BIT           DEFAULT 0,
    description         NVARCHAR(500) NULL,
    version             INT           DEFAULT 1,
    actif               BIT           DEFAULT 1,
    date_creation       DATETIME      DEFAULT GETDATE(),
    date_modification   DATETIME      NULL
);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='IX_CLIENT_ETL_Tables_Config_code')
    CREATE INDEX IX_CLIENT_ETL_Tables_Config_code ON APP_ETL_Tables_Config(code);

-- =========================================================
-- ETL TABLES PUBLIEES PAR KASOFT (read-only, copie du central)
-- =========================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Tables_Published' AND xtype='U')
CREATE TABLE APP_ETL_Tables_Published (
    id                  INT IDENTITY(1,1) PRIMARY KEY,
    code                VARCHAR(100) UNIQUE NOT NULL,
    table_name          VARCHAR(200) NOT NULL,
    target_table        VARCHAR(200) NOT NULL,
    source_query        NVARCHAR(MAX),
    primary_key_columns NVARCHAR(500),
    sync_type           VARCHAR(50)  DEFAULT 'incremental',
    timestamp_column    VARCHAR(100) DEFAULT 'cbModification',
    interval_minutes    INT          DEFAULT 5,
    priority            VARCHAR(20)  DEFAULT 'normal',
    delete_detection    BIT          DEFAULT 0,
    description         NVARCHAR(500),
    version_centrale    INT          DEFAULT 1,
    is_enabled          BIT          DEFAULT 1,
    date_publication    DATETIME     DEFAULT GETDATE(),
    date_modification   DATETIME     DEFAULT GETDATE()
);

-- =========================================================
-- AGENTS ETL CLIENT (config complete + credentials Sage)
-- =========================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Agents' AND xtype='U')
CREATE TABLE APP_ETL_Agents (
    id                          INT IDENTITY(1,1) PRIMARY KEY,
    agent_id                    VARCHAR(100) UNIQUE NOT NULL,
    nom                         NVARCHAR(200) NOT NULL,
    description                 NVARCHAR(500) NULL,
    -- Connexion Sage (credentials stockes cote client uniquement)
    sage_server                 VARCHAR(200) NULL,
    sage_database               VARCHAR(100) NULL,
    sage_username               VARCHAR(100) NULL,
    sage_password               VARCHAR(200) NULL,
    code_societe                VARCHAR(100) NULL,   -- DB_Id dans le DWH
    nom_societe                 NVARCHAR(200) NULL,  -- societe dans le DWH
    -- Configuration synchronisation
    sync_interval_secondes      INT  DEFAULT 300,
    heartbeat_interval_secondes INT  DEFAULT 30,
    batch_size                  INT  DEFAULT 10000,
    -- Options
    is_active                   BIT  DEFAULT 1,
    auto_start                  BIT  DEFAULT 1,
    -- Statut local
    statut                      VARCHAR(20) DEFAULT 'inactif',
    last_heartbeat              DATETIME NULL,
    last_sync                   DATETIME NULL,
    last_sync_statut            VARCHAR(20) NULL,
    consecutive_failures        INT  DEFAULT 0,
    total_syncs                 INT  DEFAULT 0,
    total_lignes_sync           BIGINT DEFAULT 0,
    -- Infos machine
    hostname                    VARCHAR(200) NULL,
    ip_address                  VARCHAR(50)  NULL,
    os_info                     VARCHAR(200) NULL,
    agent_version               VARCHAR(50)  NULL,
    -- Auth portail local
    api_key_hash                VARCHAR(64)  NULL,
    api_key_prefix              VARCHAR(20)  NULL,
    created_at                  DATETIME DEFAULT GETDATE(),
    updated_at                  DATETIME DEFAULT GETDATE()
);

-- Index
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='IX_CLIENT_AuditLog_date')
    CREATE INDEX IX_CLIENT_AuditLog_date ON APP_AuditLog(date_action);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='IX_CLIENT_UserPages_user')
    CREATE INDEX IX_CLIENT_UserPages_user ON APP_UserPages(user_id);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='IX_CLIENT_Users_username')
    CREATE INDEX IX_CLIENT_Users_username ON APP_Users(username);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='IX_CLIENT_ETL_Agents_agent_id')
    CREATE INDEX IX_CLIENT_ETL_Agents_agent_id ON APP_ETL_Agents(agent_id);
"""

# Tables attendues dans chaque base client
EXPECTED_CLIENT_TABLES = [
    "APP_Users", "APP_UserPages", "APP_UserMenus",
    "APP_Dashboards", "APP_DataSources",
    "APP_GridViews", "APP_GridView_User_Prefs",
    "APP_Pivots", "APP_Pivots_V2", "APP_Pivot_User_Prefs",
    "APP_Menus", "APP_EmailConfig", "APP_Settings",
    "APP_ReportSchedules", "APP_ReportHistory", "APP_AuditLog",
    "APP_ETL_Tables_Config", "APP_ETL_Tables_Published",
    "APP_ETL_Agents",
]

# =============================================================================
# CONFIG DE SYNCHRONISATION MASTER → CLIENT
# =============================================================================
# upsert_key  : colonne clé pour identifier une ligne existante (UPSERT)
#               None = pas d'upsert (DELETE + INSERT pour ces tables)
# update_cols : colonnes à mettre à jour si la ligne existe déjà
# filter      : filtrage des données côté Master
#                 None       = toutes les lignes
#                 'dwh_code' = filtrées par dwh_code
#                 'user_ids' = filtrées par user_ids du DWH

SYNCABLE_TABLES_CONFIG = {
    # ----- Tables avec upsert par `code` (Règle 1 respectée) -----
    "APP_Menus": {
        "upsert_key": "code",
        # parent_code calculé via self-join — parent_id sera remappé après sync
        "select": """SELECT m.nom, m.code, m.icon, m.url,
                            p.code AS parent_code,
                            m.ordre, m.type, m.target_id, m.actif, m.is_custom, m.roles, m.date_creation
                     FROM APP_Menus m
                     LEFT JOIN APP_Menus p ON p.id = m.parent_id
                     WHERE m.code IS NOT NULL
                     ORDER BY CASE WHEN m.parent_id IS NULL THEN 0 ELSE 1 END, m.ordre""",
        "insert": "INSERT INTO APP_Menus (nom, code, icon, url, parent_code, ordre, type, target_id, actif, is_custom, roles, date_creation, parent_id, is_customized) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,NULL,0)",
        "update": "UPDATE APP_Menus SET nom=?, icon=?, url=?, parent_code=?, ordre=?, type=?, target_id=?, actif=?, is_custom=?, roles=? WHERE code=? AND is_customized=0",
        "update_params": ["nom", "icon", "url", "parent_code", "ordre", "type", "target_id", "actif", "is_custom", "roles"],
        "filter": None,
        "post_remap_parent_id": True,   # flag → remap parent_id après sync
    },
    "APP_GridViews": {
        "upsert_key": "code",
        "select": "SELECT nom, code, description, query_template, columns_config, parameters, features, is_custom, actif, date_creation, date_modification FROM APP_GridViews WHERE code IS NOT NULL",
        "insert": "INSERT INTO APP_GridViews (nom, code, description, query_template, columns_config, parameters, features, is_custom, actif, date_creation, date_modification, is_customized) VALUES (?,?,?,?,?,?,?,?,?,?,?,0)",
        "update": "UPDATE APP_GridViews SET nom=?, description=?, query_template=?, columns_config=?, parameters=?, features=?, is_custom=?, actif=? WHERE code=? AND is_customized=0",
        "update_params": ["nom", "description", "query_template", "columns_config", "parameters", "features", "is_custom", "actif"],
        "filter": None,
    },
    "APP_Pivots_V2": {
        "upsert_key": "code",
        "select": "SELECT nom, code, description, data_source_code, rows_config, columns_config, filters_config, values_config, show_grand_totals, show_subtotals, is_custom, created_by FROM APP_Pivots_V2 WHERE code IS NOT NULL",
        "insert": "INSERT INTO APP_Pivots_V2 (nom, code, description, data_source_code, rows_config, columns_config, filters_config, values_config, show_grand_totals, show_subtotals, is_custom, created_by, is_customized) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,0)",
        "update": "UPDATE APP_Pivots_V2 SET nom=?, description=?, data_source_code=?, rows_config=?, columns_config=?, filters_config=?, values_config=?, show_grand_totals=?, show_subtotals=?, is_custom=? WHERE code=? AND is_customized=0",
        "update_params": ["nom", "description", "data_source_code", "rows_config", "columns_config", "filters_config", "values_config", "show_grand_totals", "show_subtotals", "is_custom"],
        "filter": None,
    },
    "APP_Dashboards": {
        "upsert_key": "code",
        "select": "SELECT nom, code, description, config, widgets, is_public, is_custom, created_by, actif, date_creation, date_modification FROM APP_Dashboards WHERE code IS NOT NULL",
        "insert": "INSERT INTO APP_Dashboards (nom, code, description, config, widgets, is_public, is_custom, created_by, actif, date_creation, date_modification, is_customized) VALUES (?,?,?,?,?,?,?,?,?,?,?,0)",
        "update": "UPDATE APP_Dashboards SET nom=?, description=?, config=?, widgets=?, is_public=?, is_custom=?, actif=? WHERE code=? AND is_customized=0",
        "update_params": ["nom", "description", "config", "widgets", "is_public", "is_custom", "actif"],
        "filter": None,
    },
    "APP_DataSources": {
        "upsert_key": "code",
        "select": "SELECT nom, code, type, query_template, parameters, description, is_custom, date_creation FROM APP_DataSources WHERE code IS NOT NULL",
        "insert": "INSERT INTO APP_DataSources (nom, code, type, query_template, parameters, description, is_custom, date_creation, is_customized) VALUES (?,?,?,?,?,?,?,?,0)",
        "update": "UPDATE APP_DataSources SET nom=?, type=?, query_template=?, parameters=?, description=?, is_custom=? WHERE code=? AND is_customized=0",
        "update_params": ["nom", "type", "query_template", "parameters", "description", "is_custom"],
        "filter": None,
    },
    # ----- Tables sans upsert (DELETE + INSERT — pas de personnalisation) -----
    "APP_EmailConfig": {
        "upsert_key": None,
        "select": "SELECT smtp_server, smtp_port, smtp_username, smtp_password, from_email, from_name, use_ssl, use_tls, actif FROM APP_EmailConfig WHERE dwh_code = ? OR dwh_code IS NULL",
        "insert": "INSERT INTO APP_EmailConfig (smtp_server, smtp_port, smtp_username, smtp_password, from_email, from_name, use_ssl, use_tls, actif) VALUES (?,?,?,?,?,?,?,?,?)",
        "filter": "dwh_code",
    },
    "APP_Settings": {
        "upsert_key": None,
        "select": "SELECT setting_key, setting_value, setting_type, description FROM APP_Settings WHERE dwh_code = ? OR dwh_code IS NULL",
        "insert": "INSERT INTO APP_Settings (setting_key, setting_value, setting_type, description) VALUES (?,?,?,?)",
        "filter": "dwh_code",
    },
    "APP_ReportSchedules": {
        "upsert_key": None,
        "select": "SELECT nom, description, report_type, report_id, export_format, frequency, schedule_time, schedule_day, recipients, cc_recipients, filters, is_active, last_run, next_run, created_by, created_at, updated_at FROM APP_ReportSchedules",
        "insert": "INSERT INTO APP_ReportSchedules (nom, description, report_type, report_id, export_format, frequency, schedule_time, schedule_day, recipients, cc_recipients, filters, is_active, last_run, next_run, created_by, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        "filter": None,
    },
    "APP_UserPages": {
        "upsert_key": None,
        "select": "SELECT user_id, page_code FROM APP_UserPages WHERE user_id IN ({user_ids})",
        "insert": "INSERT INTO APP_UserPages (user_id, page_code) VALUES (?,?)",
        "filter": "user_ids",
    },
    "APP_UserMenus": {
        "upsert_key": None,
        "select": "SELECT user_id, menu_id, can_view, can_export FROM APP_UserMenus WHERE user_id IN ({user_ids})",
        "insert": "INSERT INTO APP_UserMenus (user_id, menu_id, can_view, can_export) VALUES (?,?,?,?)",
        "filter": "user_ids",
    },
}


# =============================================================================
# HELPERS — CONNEXION
# =============================================================================

def _build_conn_str(server: str, database: str, user: str, password: str) -> str:
    return (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={server};DATABASE={database};"
        f"UID={user};PWD={password};"
        "TrustServerCertificate=yes;"
    )


def _check_db_exists(server: str, database: str, user: str, password: str) -> bool:
    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={server};DATABASE=master;"
        f"UID={user};PWD={password};"
        "TrustServerCertificate=yes;"
    )
    with pyodbc.connect(conn_str, timeout=10) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DB_ID(?)", (database,))
        return cursor.fetchone()[0] is not None


def _get_client_db_name(dwh_code: str) -> str:
    """Retourne le nom de la base OptiBoard pour ce client (depuis APP_ClientDB ou APP_DWH.base_optiboard)."""
    rows = execute_query(
        "SELECT db_name FROM APP_ClientDB WHERE dwh_code = ?",
        (dwh_code,), use_cache=False
    )
    if rows:
        return rows[0]["db_name"]
    # Fallback : base_optiboard configurée dans APP_DWH
    rows2 = execute_query(
        "SELECT base_optiboard FROM APP_DWH WHERE code = ?",
        (dwh_code,), use_cache=False
    )
    if rows2 and rows2[0].get("base_optiboard"):
        return rows2[0]["base_optiboard"]
    return f"OptiBoard_clt{dwh_code}"


def _get_optiboard_conn_str(dwh_code: str) -> str:
    """
    Retourne la chaîne de connexion à la base OptiBoard_{code} du client.
    Priorité : serveur_optiboard/user_optiboard/password_optiboard dans APP_DWH.
    Fallback  : serveur CENTRAL (ancienne architecture).
    """
    rows = execute_query(
        "SELECT serveur_optiboard, base_optiboard, user_optiboard, password_optiboard,"
        "       serveur_dwh, user_dwh, password_dwh"
        " FROM APP_DWH WHERE code = ?",
        (dwh_code,), use_cache=False
    )
    if not rows:
        from ..config_multitenant import get_central_settings
        c = get_central_settings()
        db_name = _get_client_db_name(dwh_code)
        return _build_conn_str(c._effective_server, db_name, c._effective_user, c._effective_password)

    r = rows[0]
    db_name = _get_client_db_name(dwh_code)
    server   = r.get("serveur_optiboard") or r.get("serveur_dwh") or ""
    user     = r.get("user_optiboard")    or r.get("user_dwh")    or ""
    password = r.get("password_optiboard") or r.get("password_dwh") or ""
    # Si les champs optiboard sont vides, on cherche dans la config centrale
    if not server or not user:
        from ..config_multitenant import get_central_settings
        c = get_central_settings()
        server   = server   or c._effective_server
        user     = user     or c._effective_user
        password = password or c._effective_password
    return _build_conn_str(server, db_name, user, password)


def _get_dwh_or_404(code: str) -> Dict[str, Any]:
    rows = execute_query(
        "SELECT code, nom, serveur_dwh, user_dwh, password_dwh FROM APP_DWH WHERE code = ?",
        (code,), use_cache=False
    )
    if not rows:
        raise HTTPException(status_code=404, detail=f"DWH '{code}' introuvable")
    return rows[0]


# =============================================================================
# HELPERS — MENUS PAR DÉFAUT
# =============================================================================

# Arborescence de menus par défaut (type=folder uniquement, sans target_id)
# Créée automatiquement lors de l'initialisation d'une nouvelle base client.
_DEFAULT_MENU_TREE = [
    # (nom, code, icon, ordre, sous_menus)
    ("Ventes",          "ventes",        "ShoppingCart",       1, [
        ("Chiffre d'Affaires",  "ventes-ca",          "BarChart3",       1),
        ("Analyses Ventes",     "ventes-analyses",    "TrendingUp",      2),
        ("Echeancier Ventes",   "ventes-echeancier",  "Clock",           3),
    ]),
    ("Achats",          "achats",        "Truck",              2, [
        ("Synthese Achats",     "achats-synthese",    "FileSpreadsheet", 1),
        ("Analyses Achats",     "achats-analyses",    "BarChart2",       2),
    ]),
    ("Stocks",          "stocks",        "Package",            3, [
        ("Mouvements Stocks",   "stocks-mouvements",  "ArrowRightLeft",  1),
        ("Valorisation Stocks", "stocks-valeur",      "DollarSign",      2),
    ]),
    ("Recouvrement",    "recouvrement",  "Wallet",             4, [
        ("Encours Clients",     "recouv-encours",     "CreditCard",      1),
        ("Balance Agee",        "recouv-balance",     "Clock",           2),
    ]),
    ("Comptabilite",    "comptabilite",  "CircleDollarSign",   5, [
        ("Bilan",               "compta-bilan",       "Scale",           1),
        ("CPC",                 "compta-cpc",         "TrendingUp",      2),
        ("Analytique",          "compta-analytique",  "PieChart",        3),
    ]),
    ("Tableaux de Bord","dashboards",    "LayoutDashboard",    6, []),
]


def _init_default_menus(cursor) -> int:
    """
    Insère l'arborescence de menus par défaut dans APP_Menus si la table est vide.
    Retourne le nombre de menus créés (0 si des menus existaient déjà).
    N'utilise que la table APP_Menus existante — aucune création de table.
    """
    cursor.execute("SELECT COUNT(*) FROM APP_Menus")
    if cursor.fetchone()[0] > 0:
        return 0

    created = 0
    for nom, code, icon, ordre, children in _DEFAULT_MENU_TREE:
        cursor.execute(
            "INSERT INTO APP_Menus (nom, code, icon, type, ordre, actif, is_custom) "
            "VALUES (?, ?, ?, 'folder', ?, 1, 0)",
            (nom, code, icon, ordre)
        )
        cursor.execute("SELECT @@IDENTITY")
        parent_id = int(cursor.fetchone()[0])
        created += 1

        for c_nom, c_code, c_icon, c_ordre in children:
            cursor.execute(
                "INSERT INTO APP_Menus (nom, code, icon, type, parent_id, ordre, actif, is_custom) "
                "VALUES (?, ?, ?, 'folder', ?, ?, 1, 0)",
                (c_nom, c_code, c_icon, parent_id, c_ordre)
            )
            created += 1

    return created


# =============================================================================
# HELPERS — CRÉATION BASE
# =============================================================================

def _create_dwh_database(server: str, database: str, user: str, password: str) -> Dict[str, Any]:
    """Crée la base DWH Métier vide (les tables sont créées par l'agent ETL)."""
    conn_master_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={server};DATABASE=master;"
        f"UID={user};PWD={password};TrustServerCertificate=yes;"
    )
    with pyodbc.connect(conn_master_str, timeout=30) as conn:
        conn.autocommit = True
        cursor = conn.cursor()
        cursor.execute("SELECT DB_ID(?)", (database,))
        if cursor.fetchone()[0] is not None:
            return {"created": False, "message": f"La base '{database}' existe déjà", "tables_count": 0}
        cursor.execute(f"CREATE DATABASE [{database}]")

    logger.info(f"[DWH-CREATE] Base '{database}' créée (vide) sur {server}")
    return {"created": True, "message": f"Base '{database}' créée", "tables_count": 0}


def _create_client_optiboard_db(dwh_code: str, server: str = None, user: str = None, password: str = None) -> Dict[str, Any]:
    """
    Crée la base OptiBoard du client sur le serveur configuré dans APP_DWH.serveur_optiboard.
    Si non configuré, utilise le serveur central en fallback.
    """
    rows = execute_query(
        "SELECT serveur_optiboard, base_optiboard, user_optiboard, password_optiboard,"
        "       serveur_dwh, user_dwh, password_dwh"
        " FROM APP_DWH WHERE code = ?",
        (dwh_code,), use_cache=False
    )
    if rows:
        r = rows[0]
        server   = r.get("serveur_optiboard") or r.get("serveur_dwh") or server or ""
        user     = r.get("user_optiboard")    or r.get("user_dwh")    or user or ""
        password = r.get("password_optiboard") or r.get("password_dwh") or password or ""
        db_name  = r.get("base_optiboard") or f"OptiBoard_clt{dwh_code}"
    else:
        db_name = f"OptiBoard_clt{dwh_code}"

    # Fallback serveur central si toujours vide
    if not server or not user:
        from ..config_multitenant import get_central_settings
        central = get_central_settings()
        server   = server   or central._effective_server
        user     = user     or central._effective_user
        password = password or central._effective_password

    driver = "{ODBC Driver 17 for SQL Server}"

    # 1 — Créer la base si absente
    try:
        if not _check_db_exists(server, db_name, user, password):
            with pyodbc.connect(
                f"DRIVER={driver};SERVER={server};DATABASE=master;UID={user};PWD={password};TrustServerCertificate=yes;",
                timeout=30
            ) as conn:
                conn.autocommit = True
                conn.cursor().execute(f"CREATE DATABASE [{db_name}]")
            logger.info(f"[CLIENT-DB] Base '{db_name}' créée sur {server}")
    except Exception as e:
        logger.error(f"[CLIENT-DB] Erreur création base {db_name}: {e}")
        return {"created": False, "db_name": db_name, "error": str(e)}

    # 2 — Créer les tables (CLIENT_OPTIBOARD_TABLES_SQL)
    tables_created = 0
    try:
        with pyodbc.connect(_build_conn_str(server, db_name, user, password), timeout=30) as conn:
            conn.autocommit = True
            cursor = conn.cursor()
            for stmt in CLIENT_OPTIBOARD_TABLES_SQL.split(";"):
                lines = [l for l in stmt.strip().split("\n") if l.strip() and not l.strip().startswith("--")]
                clean = "\n".join(lines).strip()
                if not clean:
                    continue
                try:
                    cursor.execute(clean)
                    if "CREATE TABLE" in clean.upper():
                        tables_created += 1
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        logger.debug(f"[CLIENT-DB] stmt warning: {str(e)[:80]}")
    except Exception as e:
        logger.error(f"[CLIENT-DB] Erreur création tables {db_name}: {e}")
        return {"created": True, "db_name": db_name, "tables_count": 0, "error": str(e)}

    # 3 — Enregistrer dans APP_ClientDB (centrale) avec les credentials optiboard
    #     db_server/db_user/db_password NULL = utiliser credentials centraux
    #     On les stocke UNIQUEMENT si différents des valeurs centrales
    from ..config_multitenant import get_central_settings as _cs
    _central = _cs()
    _ob_server   = server   if server   != _central._effective_server   else None
    _ob_user     = user     if user     != _central._effective_user     else None
    _ob_password = password if password != _central._effective_password else None

    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM APP_ClientDB WHERE dwh_code = ?", (dwh_code,))
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    "INSERT INTO APP_ClientDB (dwh_code, db_name, db_server, db_user, db_password)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (dwh_code, db_name, _ob_server, _ob_user, _ob_password)
                )
            else:
                # Mettre à jour db_name et credentials si la base a été reconfigurée
                cursor.execute(
                    "UPDATE APP_ClientDB SET db_name=?, db_server=?, db_user=?, db_password=?"
                    " WHERE dwh_code=?",
                    (db_name, _ob_server, _ob_user, _ob_password, dwh_code)
                )
    except Exception as e:
        logger.warning(f"[CLIENT-DB] Impossible d'enregistrer dans APP_ClientDB: {e}")
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ClientDB' AND xtype='U')
                    CREATE TABLE APP_ClientDB (
                        id            INT IDENTITY(1,1) PRIMARY KEY,
                        dwh_code      VARCHAR(50)   UNIQUE NOT NULL,
                        db_name       NVARCHAR(100) NOT NULL,
                        db_server     NVARCHAR(200) NULL,
                        db_user       NVARCHAR(100) NULL,
                        db_password   NVARCHAR(200) NULL,
                        actif         BIT DEFAULT 1,
                        date_creation DATETIME DEFAULT GETDATE()
                    )
                """)
            with get_db_cursor() as cursor:
                cursor.execute(
                    "INSERT INTO APP_ClientDB (dwh_code, db_name, db_server, db_user, db_password)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (dwh_code, db_name, _ob_server, _ob_user, _ob_password)
                )
        except Exception as e2:
            logger.error(f"[CLIENT-DB] Echec total APP_ClientDB: {e2}")

    # 4 — Migration données Master → client + menus par défaut si aucun migré
    try:
        with pyodbc.connect(_build_conn_str(server, db_name, user, password), timeout=30) as conn:
            _migrate_data_to_client(dwh_code, conn)
            # Seed menus par défaut uniquement si aucun menu n'a été migré
            cur = conn.cursor()
            n = _init_default_menus(cur)
            if n > 0:
                conn.commit()
                logger.info(f"[CLIENT-DB] {n} menus par défaut créés pour {dwh_code}")
    except Exception as e:
        logger.warning(f"[CLIENT-DB] Erreur migration données pour {dwh_code}: {e}")

    # 5 — Vider le cache
    try:
        client_manager.clear_cache(dwh_code)
    except Exception:
        pass

    return {"created": True, "db_name": db_name, "tables_count": tables_created}


# =============================================================================
# HELPER — SYNC MASTER → CLIENT
# =============================================================================

def _migrate_data_to_client(dwh_code: str, client_conn) -> None:
    """
    Migration initiale : copie les données Master vers la base client.
    Toutes les lignes copiées ont is_customized=0 (non protégées).
    """
    master_conn = get_central_connection()
    mc = master_conn.cursor()
    cc = client_conn.cursor()

    # User IDs liés à ce DWH
    mc.execute("SELECT user_id FROM APP_UserDWH WHERE dwh_code = ?", (dwh_code,))
    user_ids = [r[0] for r in mc.fetchall()]
    ph = ",".join(["?"] * len(user_ids)) if user_ids else "0"

    def _try_copy(select_sql, insert_sql, params=None):
        try:
            mc.execute(select_sql, params or [])
            for row in mc.fetchall():
                try:
                    cc.execute(insert_sql, row)
                except Exception:
                    pass
            client_conn.commit()
        except Exception as e:
            logger.debug(f"[MIGRATE] {select_sql[:60]}: {e}")
            client_conn.rollback()

    # ── Menus : copie avec remapping parent_id (les IDs IDENTITY divergent entre bases) ──
    try:
        mc.execute(
            # CTE récursif pour trier par profondeur : parents toujours avant enfants
            """
            WITH Hierarchy AS (
                SELECT id, 0 AS depth FROM APP_Menus WHERE parent_id IS NULL
                UNION ALL
                SELECT m.id, h.depth + 1
                FROM APP_Menus m JOIN Hierarchy h ON m.parent_id = h.id
            )
            SELECT m.id, m.nom, m.code, m.icon, m.url, m.parent_id, m.ordre,
                   m.type, m.target_id, m.actif, m.is_custom, m.roles, m.date_creation
            FROM APP_Menus m
            JOIN Hierarchy h ON m.id = h.id
            ORDER BY h.depth, m.ordre
            """
        )
        menus = mc.fetchall()
        id_map = {}  # old_id → new_id
        for row in menus:
            old_id, nom, code, icon, url, old_parent_id, ordre, mtype, target_id, actif, is_custom, roles, date_creation = row
            new_parent_id = id_map.get(old_parent_id) if old_parent_id else None
            try:
                cc.execute(
                    "INSERT INTO APP_Menus (nom, code, icon, url, parent_id, ordre, type, target_id, actif, is_custom, roles, date_creation, is_customized) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,0)",
                    (nom, code, icon, url, new_parent_id, ordre, mtype, target_id, actif, is_custom, roles, date_creation)
                )
                cc.execute("SELECT @@IDENTITY")
                new_id = int(cc.fetchone()[0])
                id_map[old_id] = new_id
            except Exception:
                pass
        client_conn.commit()
    except Exception as e:
        logger.debug(f"[MIGRATE] APP_Menus: {e}")
        client_conn.rollback()
    _try_copy(
        "SELECT nom, code, description, query_template, columns_config, parameters, features, is_custom, actif, date_creation, date_modification FROM APP_GridViews",
        "INSERT INTO APP_GridViews (nom, code, description, query_template, columns_config, parameters, features, is_custom, actif, date_creation, date_modification, is_customized) VALUES (?,?,?,?,?,?,?,?,?,?,?,0)",
    )
    _try_copy(
        "SELECT nom, code, description, data_source_code, rows_config, columns_config, filters_config, values_config, show_grand_totals, show_subtotals, is_custom, created_by FROM APP_Pivots_V2",
        "INSERT INTO APP_Pivots_V2 (nom, code, description, data_source_code, rows_config, columns_config, filters_config, values_config, show_grand_totals, show_subtotals, is_custom, created_by, is_customized) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,0)",
    )
    _try_copy(
        "SELECT nom, code, description, config, widgets, is_public, is_custom, created_by, actif, date_creation, date_modification FROM APP_Dashboards",
        "INSERT INTO APP_Dashboards (nom, code, description, config, widgets, is_public, is_custom, created_by, actif, date_creation, date_modification, is_customized) VALUES (?,?,?,?,?,?,?,?,?,?,?,0)",
    )
    _try_copy(
        "SELECT nom, code, type, query_template, parameters, description, is_custom, date_creation FROM APP_DataSources",
        "INSERT INTO APP_DataSources (nom, code, type, query_template, parameters, description, is_custom, date_creation, is_customized) VALUES (?,?,?,?,?,?,?,?,0)",
    )
    _try_copy(
        "SELECT smtp_server, smtp_port, smtp_username, smtp_password, from_email, from_name, use_ssl, use_tls, actif FROM APP_EmailConfig WHERE dwh_code = ? OR dwh_code IS NULL",
        "INSERT INTO APP_EmailConfig (smtp_server, smtp_port, smtp_username, smtp_password, from_email, from_name, use_ssl, use_tls, actif) VALUES (?,?,?,?,?,?,?,?,?)",
        (dwh_code,),
    )
    _try_copy(
        "SELECT setting_key, setting_value, setting_type, description FROM APP_Settings WHERE dwh_code = ? OR dwh_code IS NULL",
        "INSERT INTO APP_Settings (setting_key, setting_value, setting_type, description) VALUES (?,?,?,?)",
        (dwh_code,),
    )
    _try_copy(
        "SELECT nom, description, report_type, report_id, export_format, frequency, schedule_time, schedule_day, recipients, cc_recipients, filters, is_active, last_run, next_run, created_by, created_at, updated_at FROM APP_ReportSchedules",
        "INSERT INTO APP_ReportSchedules (nom, description, report_type, report_id, export_format, frequency, schedule_time, schedule_day, recipients, cc_recipients, filters, is_active, last_run, next_run, created_by, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
    )
    if user_ids:
        _try_copy(
            f"SELECT user_id, page_code FROM APP_UserPages WHERE user_id IN ({ph})",
            "INSERT INTO APP_UserPages (user_id, page_code) VALUES (?,?)",
            user_ids,
        )
        _try_copy(
            f"SELECT user_id, menu_id, can_view, can_export FROM APP_UserMenus WHERE user_id IN ({ph})",
            "INSERT INTO APP_UserMenus (user_id, menu_id, can_view, can_export) VALUES (?,?,?,?)",
            user_ids,
        )

    # ── Créer l'admin local sans mot de passe (premier login obligatoire) ──────
    try:
        cc.execute(
            "IF NOT EXISTS (SELECT 1 FROM APP_Users WHERE username = 'admin') "
            "INSERT INTO APP_Users (username, password_hash, nom, role_dwh, actif, must_change_password) "
            "VALUES ('admin', NULL, 'Administrateur', 'admin_client', 1, 1)"
        )
        client_conn.commit()
        logger.info(f"[MIGRATE] Admin local cree pour {dwh_code} (premier login requis)")
    except Exception as e:
        logger.warning(f"[MIGRATE] Erreur creation admin local pour {dwh_code}: {e}")

    mc.close()
    master_conn.close()


def _sync_data_to_client(code: str, tables_filter: Optional[List[str]], mode: str) -> Dict[str, Any]:
    """
    Synchronise les données Master → OptiBoard_{code}.

    mode='upsert' (défaut) :
      - Tables avec upsert_key (code) : UPSERT en respectant is_customized=1
        → les lignes is_customized=1 ne sont JAMAIS modifiées (Règle 1)
      - Tables sans upsert_key        : DELETE + INSERT (config non personnalisable)

    mode='replace' :
      - Force DELETE + INSERT sur toutes les tables (ignore is_customized)
      - Réservé à l'admin pour reset complet.
    """
    _get_dwh_or_404(code)
    db_name = _get_client_db_name(code)
    conn_str = _get_optiboard_conn_str(code)

    client_conn = pyodbc.connect(conn_str, timeout=30)
    master_conn = get_central_connection()
    mc = master_conn.cursor()
    cc = client_conn.cursor()

    # User IDs liés au DWH
    mc.execute("SELECT user_id FROM APP_UserDWH WHERE dwh_code = ?", (code,))
    user_ids = [r[0] for r in mc.fetchall()]
    ph = ",".join(["?"] * len(user_ids)) if user_ids else "0"

    target_tables = tables_filter if tables_filter else list(SYNCABLE_TABLES_CONFIG.keys())
    details: Dict[str, Any] = {}

    for table_name in target_tables:
        cfg = SYNCABLE_TABLES_CONFIG.get(table_name)
        if not cfg:
            details[table_name] = {"status": "skipped", "message": "Table non synchronisable"}
            continue

        if cfg["filter"] == "user_ids" and not user_ids:
            details[table_name] = {"status": "ok", "rows_synced": 0, "message": "Aucun utilisateur lié"}
            continue

        try:
            # --- Récupérer les données depuis Master ---
            select_sql = cfg["select"]
            params: Any = None
            if cfg["filter"] == "dwh_code":
                params = (code,)
            elif cfg["filter"] == "user_ids":
                select_sql = select_sql.replace("{user_ids}", ph)
                params = user_ids

            mc.execute(select_sql, params or [])
            rows = mc.fetchall()
            col_names = [desc[0] for desc in mc.description]

            upsert_key = cfg.get("upsert_key")
            inserted = updated = skipped = 0

            # === UPSERT (tables avec upsert_key ET mode != 'replace') ===
            if upsert_key and mode != "replace":
                key_idx = col_names.index(upsert_key) if upsert_key in col_names else None
                for row in rows:
                    if key_idx is None:
                        continue
                    key_val = row[key_idx]
                    if key_val is None:
                        continue

                    cc.execute(
                        f"SELECT is_customized FROM [{table_name}] WHERE {upsert_key} = ?",
                        (key_val,)
                    )
                    existing = cc.fetchone()

                    if existing is None:
                        # INSERT avec is_customized=0
                        try:
                            cc.execute(cfg["insert"], row)
                            inserted += 1
                        except Exception:
                            pass
                    elif existing[0] == 1:
                        # Ligne personnalisée — on ne touche pas (Règle 1)
                        skipped += 1
                    else:
                        # UPDATE (is_customized=0)
                        try:
                            update_params_names = cfg.get("update_params", [])
                            row_dict = dict(zip(col_names, row))
                            update_vals = [row_dict[c] for c in update_params_names] + [key_val]
                            cc.execute(cfg["update"], update_vals)
                            updated += 1
                        except Exception:
                            pass

            # === DELETE + INSERT (tables sans upsert_key ou mode='replace') ===
            else:
                cc.execute(f"DELETE FROM [{table_name}]")
                for row in rows:
                    try:
                        cc.execute(cfg["insert"], row)
                        inserted += 1
                    except Exception:
                        pass

            client_conn.commit()

            # ── Remap parent_id depuis parent_code (menus uniquement) ──
            if cfg.get("post_remap_parent_id"):
                try:
                    cc.execute("""
                        UPDATE child
                        SET    child.parent_id = parent.id
                        FROM   APP_Menus child
                        JOIN   APP_Menus parent ON parent.code = child.parent_code
                        WHERE  child.parent_code IS NOT NULL AND child.parent_code != ''
                    """)
                    client_conn.commit()
                except Exception as e_remap:
                    logger.warning(f"[SYNC] Remap parent_id APP_Menus: {e_remap}")

            details[table_name] = {
                "status": "ok",
                "rows_synced": inserted + updated,
                "inserted": inserted,
                "updated": updated,
                "skipped_customized": skipped,
            }

        except Exception as e:
            details[table_name] = {"status": "error", "error": str(e)[:200]}
            try:
                client_conn.rollback()
            except Exception:
                pass

    mc.close()
    master_conn.close()
    cc.close()
    client_conn.close()

    try:
        client_manager.clear_cache(code)
    except Exception:
        pass

    ok_count = sum(1 for v in details.values() if v.get("status") == "ok")
    return {
        "success": True,
        "dwh_code": code,
        "db_name": db_name,
        "mode": mode,
        "tables_synced": ok_count,
        "tables_failed": len(details) - ok_count,
        "details": details,
    }


def _reset_client_db(code: str, keep_user_data: bool) -> Dict[str, Any]:
    """Réinitialise la base client OptiBoard_{code}."""
    _get_dwh_or_404(code)
    db_name = _get_client_db_name(code)
    conn_str = _get_optiboard_conn_str(code)

    tables_to_drop = [
        "APP_ReportHistory", "APP_AuditLog",
        "APP_Pivot_User_Prefs", "APP_GridView_User_Prefs",
        "APP_Pivots_V2", "APP_Pivots", "APP_GridViews",
        "APP_Dashboards", "APP_DataSources", "APP_Menus",
        "APP_EmailConfig", "APP_Settings", "APP_ReportSchedules",
    ]
    if not keep_user_data:
        tables_to_drop += ["APP_UserPages", "APP_UserMenus", "APP_Users"]

    with pyodbc.connect(conn_str, timeout=30, autocommit=True) as conn:
        cursor = conn.cursor()
        dropped = 0
        for table in tables_to_drop:
            try:
                cursor.execute(f"IF OBJECT_ID('{table}', 'U') IS NOT NULL DROP TABLE [{table}]")
                dropped += 1
            except Exception:
                pass

        tables_created = 0
        for stmt in CLIENT_OPTIBOARD_TABLES_SQL.split(";"):
            lines = [l for l in stmt.strip().split("\n") if l.strip() and not l.strip().startswith("--")]
            clean = "\n".join(lines).strip()
            if not clean:
                continue
            try:
                cursor.execute(clean)
                if "CREATE TABLE" in clean.upper():
                    tables_created += 1
            except Exception:
                pass

        conn.autocommit = False
        try:
            _migrate_data_to_client(code, conn)
            conn.commit()
        except Exception:
            pass

    try:
        client_manager.clear_cache(code)
    except Exception:
        pass

    return {
        "success": True,
        "message": f"Base {db_name} réinitialisée",
        "tables_dropped": dropped,
        "tables_created": tables_created,
    }


def _list_client_databases() -> Dict[str, Any]:
    """Liste toutes les bases client OptiBoard_XXX avec statut de connexion."""
    dwh_list = execute_query(
        """SELECT d.code, d.nom,
                  d.serveur_optiboard, d.base_optiboard, d.user_optiboard, d.password_optiboard,
                  d.serveur_dwh, d.user_dwh, d.password_dwh,
                  c.db_name AS client_db_name
           FROM APP_DWH d
           LEFT JOIN APP_ClientDB c ON d.code = c.dwh_code
           WHERE d.actif = 1 ORDER BY d.nom""",
        use_cache=False,
    )

    results, healthy, unhealthy, pending = [], 0, 0, 0

    for dwh in dwh_list:
        # Nom de la base : APP_ClientDB > base_optiboard > défaut
        db_name = (dwh.get("client_db_name")
                   or dwh.get("base_optiboard")
                   or f"OptiBoard_clt{dwh['code']}")
        has_client_db = dwh.get("client_db_name") is not None
        # Credentials OptiBoard (priorité optiboard > dwh)
        ob_server   = dwh.get("serveur_optiboard") or dwh.get("serveur_dwh") or ""
        ob_user     = dwh.get("user_optiboard")    or dwh.get("user_dwh")    or ""
        ob_password = dwh.get("password_optiboard") or dwh.get("password_dwh") or ""
        info = {
            "dwh_code": dwh["code"], "dwh_nom": dwh["nom"],
            "db_name": db_name, "server": ob_server,
            "has_client_db": has_client_db,
            "connection_status": "not_configured",
            "tables_count": 0, "total_rows": 0, "size_mb": 0,
            "tables": [], "error": None,
        }
        if not has_client_db:
            pending += 1
            results.append(info)
            continue
        try:
            with pyodbc.connect(_build_conn_str(ob_server, db_name, ob_user, ob_password), timeout=5) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT t.name, p.rows FROM sys.tables t INNER JOIN sys.partitions p ON t.object_id=p.object_id AND p.index_id IN(0,1) WHERE t.is_ms_shipped=0 ORDER BY t.name")
                tables = [{"name": r[0], "rows": r[1]} for r in cursor.fetchall()]
                cursor.execute("SELECT SUM(CAST(size AS BIGINT))*8/1024.0 FROM sys.database_files")
                size = cursor.fetchone()[0] or 0
            info.update({
                "connection_status": "ok", "tables": tables,
                "tables_count": len(tables), "total_rows": sum(t["rows"] for t in tables),
                "size_mb": round(float(size), 2),
            })
            healthy += 1
        except Exception as e:
            info.update({"connection_status": "error", "error": str(e)[:200]})
            unhealthy += 1
        results.append(info)

    return {"success": True, "total": len(results), "healthy": healthy, "unhealthy": unhealthy, "pending_migration": pending, "data": results}


def _get_client_db_status(code: str) -> Dict[str, Any]:
    """Détail complet du statut d'une base client."""
    dwh = _get_dwh_or_404(code)
    db_name = _get_client_db_name(code)
    conn_str = _get_optiboard_conn_str(code)

    with pyodbc.connect(conn_str, timeout=10) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT t.name, p.rows, t.create_date, t.modify_date FROM sys.tables t INNER JOIN sys.partitions p ON t.object_id=p.object_id AND p.index_id IN(0,1) WHERE t.is_ms_shipped=0 ORDER BY t.name")
        tables = [{"name": r[0], "rows": r[1], "created": str(r[2])[:19] if r[2] else None, "modified": str(r[3])[:19] if r[3] else None} for r in cursor.fetchall()]
        cursor.execute("SELECT type_desc, SUM(CAST(size AS BIGINT))*8/1024.0 FROM sys.database_files GROUP BY type_desc")
        sizes = {r[0]: round(float(r[1]), 2) for r in cursor.fetchall()}
        cursor.execute("SELECT @@VERSION")
        version = cursor.fetchone()[0].split("\n")[0]

    existing = {t["name"] for t in tables}
    missing = [t for t in EXPECTED_CLIENT_TABLES if t not in existing]

    # Vérifier les colonnes is_customized sur les tables synchables
    customized_counts: Dict[str, int] = {}
    try:
        with pyodbc.connect(conn_str, timeout=10) as conn:
            cursor = conn.cursor()
            for tbl in ["APP_Menus", "APP_GridViews", "APP_Pivots_V2", "APP_Dashboards", "APP_DataSources"]:
                if tbl in existing:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM [{tbl}] WHERE is_customized = 1")
                        customized_counts[tbl] = cursor.fetchone()[0]
                    except Exception:
                        pass
    except Exception:
        pass

    return {
        "success": True,
        "dwh_code": code, "dwh_nom": dwh["nom"], "db_name": db_name,
        "server_version": version,
        "tables_count": len(tables),
        "total_rows": sum(t["rows"] for t in tables),
        "size_data_mb": sizes.get("ROWS", 0),
        "size_log_mb": sizes.get("LOG", 0),
        "tables": tables,
        "expected_tables": EXPECTED_CLIENT_TABLES,
        "missing_tables": missing,
        "all_tables_present": len(missing) == 0,
        "customized_counts": customized_counts,  # Règle 1 — audit
    }


def _run_migrate_all_clients() -> Dict[str, Any]:
    dwh_list = execute_query("SELECT code, nom, serveur_dwh, user_dwh, password_dwh FROM APP_DWH WHERE actif=1 ORDER BY nom", use_cache=False)
    if not dwh_list:
        return {"success": True, "message": "Aucun DWH actif", "results": []}

    try:
        existing = {r["dwh_code"] for r in execute_query("SELECT dwh_code FROM APP_ClientDB WHERE actif=1", use_cache=False)}
    except Exception:
        existing = set()

    results = []
    for dwh in dwh_list:
        code = dwh["code"]
        if code in existing:
            results.append({"dwh_code": code, "nom": dwh["nom"], "status": "exists", "message": f"OptiBoard_{code} déjà configuré"})
            continue
        s, u, p = dwh.get("serveur_dwh"), dwh.get("user_dwh"), dwh.get("password_dwh")
        if not all([s, u, p]):
            results.append({"dwh_code": code, "nom": dwh["nom"], "status": "skipped", "message": "Paramètres connexion incomplets"})
            continue
        try:
            r = _create_client_optiboard_db(code, s, u, p)
            results.append({"dwh_code": code, "nom": dwh["nom"], "status": "created" if r.get("created") else "error", "db_name": r.get("db_name"), "tables_count": r.get("tables_count", 0)})
        except Exception as e:
            results.append({"dwh_code": code, "nom": dwh["nom"], "status": "error", "message": str(e)})

    created = sum(1 for r in results if r["status"] == "created")
    already = sum(1 for r in results if r["status"] == "exists")
    return {"success": True, "message": f"{created} base(s) créée(s), {already} déjà existante(s)", "total": len(dwh_list), "created": created, "existing": already, "results": results}


def _patch_missing_tables(dwh_code: str) -> Dict[str, Any]:
    """
    Ajoute les tables manquantes dans la base client OptiBoard_{code}.
    Utilise CLIENT_OPTIBOARD_TABLES_SQL (idempotent — IF NOT EXISTS).
    """
    conn_str = _get_optiboard_conn_str(dwh_code)
    tables_created = 0
    errors = []
    try:
        with pyodbc.connect(conn_str, timeout=30) as conn:
            conn.autocommit = True
            cursor = conn.cursor()
            for stmt in CLIENT_OPTIBOARD_TABLES_SQL.split(";"):
                lines = [l for l in stmt.strip().split("\n") if l.strip() and not l.strip().startswith("--")]
                clean = "\n".join(lines).strip()
                if not clean:
                    continue
                try:
                    cursor.execute(clean)
                    if "CREATE TABLE" in clean.upper():
                        tables_created += 1
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        errors.append(str(e)[:120])
    except Exception as e:
        return {"success": False, "error": str(e)}

    return {"success": True, "tables_created": tables_created, "errors": errors[:5]}


# =============================================================================
# ROUTES — CRUD DWH
# =============================================================================

@router.get("/dwh-admin/list")
async def dwh_admin_list():
    """Liste tous les DWH clients."""
    try:
        dwh_list = execute_query(
            "SELECT id, code, nom, raison_sociale, adresse, ville, pays, telephone, email, logo_url,"
            " serveur_dwh, base_dwh, user_dwh, actif, date_creation,"
            " serveur_optiboard, base_optiboard, user_optiboard, ISNULL(is_demo,0) AS is_demo"
            " FROM APP_DWH ORDER BY nom",
            use_cache=False,
        )
        # Compter les sources en une seule requête (évite le N+1)
        sources_map: Dict[str, int] = {}
        try:
            rows = execute_query("SELECT dwh_code, COUNT(*) AS cnt FROM APP_DWH_Sources GROUP BY dwh_code", use_cache=False)
            sources_map = {r["dwh_code"]: r["cnt"] for r in rows}
        except Exception:
            pass
        for dwh in dwh_list:
            dwh["sources_count"] = sources_map.get(dwh["code"], 0)
        return {"success": True, "data": dwh_list}
    except Exception as e:
        logger.error(f"dwh_admin_list: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dwh-admin/client-databases")
async def dwh_admin_client_databases():
    """Liste toutes les bases client OptiBoard_XXX avec statut."""
    try:
        return await asyncio.to_thread(_list_client_databases)
    except Exception as e:
        logger.error(f"dwh_admin_client_databases: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dwh-admin/{code}/client-db-status")
async def dwh_admin_client_db_status(code: str):
    """Détail du statut d'une base client."""
    try:
        return await asyncio.to_thread(_get_client_db_status, code)
    except Exception as e:
        logger.error(f"dwh_admin_client_db_status({code}): {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dwh-admin/{code}")
async def dwh_admin_get(code: str):
    """Récupère les détails d'un DWH."""
    try:
        rows = execute_query(
            "SELECT id, code, nom, raison_sociale, adresse, ville, pays, telephone, email, logo_url,"
            " serveur_dwh, base_dwh, user_dwh, actif, date_creation,"
            " serveur_optiboard, base_optiboard, user_optiboard"
            " FROM APP_DWH WHERE code = ?",
            (code,), use_cache=False,
        )
        if not rows:
            raise HTTPException(status_code=404, detail="DWH introuvable")
        return {"success": True, "data": rows[0]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dwh-admin")
async def dwh_admin_create(dwh: DWHCreate):
    """Crée un nouveau DWH. Auto-crée la base DWH + la base client si absentes."""
    try:
        db_init_result = None
        if all([dwh.serveur_dwh, dwh.base_dwh, dwh.user_dwh, dwh.password_dwh]):
            try:
                if not _check_db_exists(dwh.serveur_dwh, dwh.base_dwh, dwh.user_dwh, dwh.password_dwh):
                    db_init_result = await asyncio.to_thread(_create_dwh_database, dwh.serveur_dwh, dwh.base_dwh, dwh.user_dwh, dwh.password_dwh)
            except Exception as e:
                logger.warning(f"Auto-création base DWH impossible: {e}")

        with get_db_cursor() as cursor:
            cursor.execute(
                "INSERT INTO APP_DWH"
                " (code, nom, raison_sociale, adresse, ville, pays, telephone, email, logo_url,"
                "  serveur_dwh, base_dwh, user_dwh, password_dwh,"
                "  serveur_optiboard, base_optiboard, user_optiboard, password_optiboard, actif)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (dwh.code, dwh.nom, dwh.raison_sociale, dwh.adresse, dwh.ville, dwh.pays,
                 dwh.telephone, dwh.email, dwh.logo_url,
                 dwh.serveur_dwh, dwh.base_dwh, dwh.user_dwh, dwh.password_dwh,
                 dwh.serveur_optiboard, dwh.base_optiboard, dwh.user_optiboard, dwh.password_optiboard,
                 1 if dwh.actif else 0),
            )

        client_db_result = None
        try:
            client_db_result = await asyncio.to_thread(_create_client_optiboard_db, dwh.code)
        except Exception as e:
            logger.warning(f"Auto-création base client impossible pour {dwh.code}: {e}")

        message = "DWH créé avec succès"
        if db_init_result and db_init_result.get("created"):
            message += f". Base '{dwh.base_dwh}' créée"
        if client_db_result and client_db_result.get("created"):
            message += f". Base client '{client_db_result.get('db_name')}' créée"

        return {
            "success": True, "message": message,
            "db_created": db_init_result.get("created", False) if db_init_result else False,
            "tables_count": db_init_result.get("tables_count", 0) if db_init_result else 0,
            "client_db_created": client_db_result.get("created", False) if client_db_result else False,
        }
    except Exception as e:
        logger.error(f"dwh_admin_create: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/dwh-admin/{code}")
async def dwh_admin_update(code: str, dwh: DWHUpdate):
    """Met à jour un DWH (password non modifié si absent)."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """UPDATE APP_DWH SET
                    nom=?, raison_sociale=?, adresse=?, ville=?, pays=?,
                    telephone=?, email=?, logo_url=?, serveur_dwh=?,
                    base_dwh=?, user_dwh=?,
                    password_dwh=COALESCE(NULLIF(?, ''), password_dwh),
                    serveur_optiboard=?, base_optiboard=?, user_optiboard=?,
                    password_optiboard=COALESCE(NULLIF(?, ''), password_optiboard),
                    actif=?, date_modification=GETDATE()
                   WHERE code=?""",
                (dwh.nom, dwh.raison_sociale, dwh.adresse, dwh.ville, dwh.pays,
                 dwh.telephone, dwh.email, dwh.logo_url, dwh.serveur_dwh,
                 dwh.base_dwh, dwh.user_dwh, dwh.password_dwh,
                 dwh.serveur_optiboard, dwh.base_optiboard, dwh.user_optiboard, dwh.password_optiboard,
                 1 if dwh.actif else 0, code),
            )
        return {"success": True, "message": "DWH mis à jour"}
    except Exception as e:
        logger.error(f"dwh_admin_update({code}): {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _drop_db(serveur: str, db_name: str, user: str, password: str) -> dict:
    """DROP d'une base SQL Server si elle existe."""
    if not db_name or not serveur:
        return {"dropped": False, "db": db_name, "reason": "infos manquantes"}
    try:
        conn_str = _build_conn_str(serveur, "master", user, password)
        conn = pyodbc.connect(conn_str, timeout=15)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM sys.databases WHERE name = ?", (db_name,))
        if cur.fetchone()[0] == 0:
            conn.close()
            return {"dropped": False, "db": db_name, "reason": "n'existe pas"}
        cur.execute(f"ALTER DATABASE [{db_name}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE")
        cur.execute(f"DROP DATABASE [{db_name}]")
        conn.close()
        logger.info(f"[DROP-DB] '{db_name}' supprimée sur {serveur}")
        return {"dropped": True, "db": db_name}
    except Exception as e:
        logger.warning(f"[DROP-DB] Impossible de supprimer '{db_name}': {e}")
        return {"dropped": False, "db": db_name, "error": str(e)}


@router.delete("/dwh-admin/{code}")
async def dwh_admin_delete(code: str):
    """Supprime un DWH du registre central + DROP automatique des bases SQL Server."""
    if code.upper() in PROTECTED_DWH_CODES:
        raise HTTPException(status_code=403, detail=f"La base '{code}' est protégée et ne peut pas être supprimée")
    try:
        drop_results = []

        with get_db_cursor() as cursor:
            # Lire les infos de connexion AVANT suppression
            cursor.execute("""
                SELECT serveur_dwh, base_dwh, user_dwh, password_dwh,
                       serveur_optiboard, base_optiboard, user_optiboard, password_optiboard
                FROM APP_DWH WHERE code = ?
            """, (code,))
            row = cursor.fetchone()
            if row:
                dwh_srv  = row[0] or ''
                dwh_base = row[1] or f"DWH_{code}"
                dwh_user = row[2] or ''
                dwh_pwd  = row[3] or ''
                ob_srv   = row[4] or dwh_srv
                ob_base  = row[5] or f"OptiBoard_clt{code}"
                ob_user  = row[6] or dwh_user
                ob_pwd   = row[7] or dwh_pwd

                # DROP automatique des deux bases
                drop_results.append(_drop_db(dwh_srv, dwh_base, dwh_user, dwh_pwd))
                drop_results.append(_drop_db(ob_srv,  ob_base,  ob_user,  ob_pwd))

            # Cascade sur les tables liées
            for tbl in ["APP_ETL_Agents_Monitoring", "APP_DWH_Sources", "APP_ETL_Agent_Tables", "APP_ClientDB"]:
                try:
                    cursor.execute(f"DELETE FROM {tbl} WHERE dwh_code = ?", (code,))
                except Exception:
                    pass

            cursor.execute("DELETE FROM APP_DWH WHERE code=?", (code,))

        dropped = [r["db"] for r in drop_results if r.get("dropped")]
        skipped = [r["db"] for r in drop_results if not r.get("dropped")]
        msg = f"DWH '{code}' supprimé"
        if dropped: msg += f" | Bases supprimées: {', '.join(dropped)}"
        if skipped: msg += f" | Non supprimées: {', '.join(skipped)}"

        return {"success": True, "message": msg, "drop_results": drop_results}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"dwh_admin_delete({code}): {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ROUTES — SYNC DÉMO
# =============================================================================

@router.post("/admin/dwh/{code}/sync-demo")
async def sync_demo_dwh(code: str):
    """
    Réinitialise / synchronise les données de démonstration d'un DWH démo.
    Réservé aux DWH marqués is_demo=1. Seul le superadmin peut appeler cet endpoint.
    """
    # Vérifier que le DWH existe et est bien marqué démo
    rows = execute_central("SELECT code, nom, is_demo FROM APP_DWH WHERE code = ?", (code.upper(),), use_cache=False)
    if not rows:
        raise HTTPException(status_code=404, detail=f"DWH '{code}' introuvable")
    if not rows[0].get("is_demo"):
        raise HTTPException(status_code=403, detail=f"Le DWH '{code}' n'est pas marqué comme démo")

    results = {}

    # 1. Seed historique alertes démo (centrale)
    try:
        from .alerts import seed_demo_history
        r = await seed_demo_history()
        results["alerts"] = r
    except Exception as e:
        results["alerts"] = {"error": str(e)}

    # 2. Seed abonnements démo (centrale)
    try:
        from .subscriptions import seed_demo_subscriptions
        r = await seed_demo_subscriptions()
        results["subscriptions"] = r
    except Exception as e:
        results["subscriptions"] = {"error": str(e)}

    # 3. Seed templates alertes maître (centrale)
    try:
        from .alert_templates import seed_demo_templates
        r = await seed_demo_templates()
        results["alert_templates"] = r
    except Exception as e:
        results["alert_templates"] = {"error": str(e)}

    return {
        "success": True,
        "message": f"Données démo synchronisées pour le DWH '{code}'",
        "details": results,
        "synced_at": __import__('datetime').datetime.now().isoformat()
    }


@router.get("/admin/dwh/demo-list")
async def list_demo_dwhs():
    """Liste les DWH marqués is_demo — pour l'interface superadmin."""
    rows = execute_central(
        "SELECT code, nom, actif, is_demo FROM APP_DWH WHERE is_demo = 1 ORDER BY nom",
        use_cache=False
    )
    return {"success": True, "data": rows}


# =============================================================================
# ROUTES — TEST CONNEXION
# =============================================================================

@router.post("/dwh-admin/test-connection")
async def dwh_admin_test_connection(req: TestConnectionRequest):
    """Teste une connexion SQL Server (serveur + base + credentials)."""
    try:
        if not _check_db_exists(req.serveur, req.base, req.user, req.password):
            return {"success": True, "db_exists": False, "message": f"Serveur accessible — la base '{req.base}' sera créée automatiquement"}
        conn_str = _build_conn_str(req.serveur, req.base, req.user, req.password)
        with pyodbc.connect(conn_str, timeout=10) as conn:
            version = conn.cursor().execute("SELECT @@VERSION").fetchone()[0].split("\n")[0]
        return {"success": True, "db_exists": True, "message": f"Connexion OK: {version}"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.post("/dwh-admin/{code}/test")
async def dwh_admin_test_existing(code: str):
    """Teste la connexion d'un DWH déjà enregistré."""
    try:
        dwh = _get_dwh_or_404(code)
        conn_str = _build_conn_str(dwh["serveur_dwh"] or "", dwh.get("base_dwh", "master"), dwh["user_dwh"] or "", dwh["password_dwh"] or "")
        with pyodbc.connect(conn_str, timeout=10) as conn:
            version = conn.cursor().execute("SELECT @@VERSION").fetchone()[0].split("\n")[0]
        return {"success": True, "message": f"Connexion OK: {version}"}
    except Exception as e:
        return {"success": False, "message": str(e)}


# =============================================================================
# ROUTES — SMTP
# =============================================================================

@router.get("/dwh-admin/{code}/smtp")
async def dwh_admin_get_smtp(code: str):
    """Récupère la configuration SMTP d'un DWH (depuis sa base client)."""
    try:
        if client_manager.has_client_db(code):
            from ..database_unified import execute_client
            rows = execute_client(
                code,
                "SELECT smtp_server, smtp_port, smtp_username, smtp_password, from_email, from_name, use_tls FROM APP_EmailConfig WHERE actif=1",
                use_cache=False,
            )
        else:
            rows = execute_query(
                "SELECT smtp_server, smtp_port, smtp_username, smtp_password, from_email, from_name, use_tls FROM APP_EmailConfig WHERE dwh_code=?",
                (code,), use_cache=False,
            )
        return {"success": True, "data": rows[0] if rows else None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dwh-admin/{code}/smtp")
async def dwh_admin_save_smtp(code: str, smtp: SMTPConfig):
    """Sauvegarde la configuration SMTP dans la base client."""
    try:
        if client_manager.has_client_db(code):
            from ..database_unified import write_client
            write_client(
                code,
                "DELETE FROM APP_EmailConfig; INSERT INTO APP_EmailConfig (smtp_server, smtp_port, smtp_username, smtp_password, from_email, from_name, use_tls, actif) VALUES (?,?,?,?,?,?,?,1)",
                (smtp.smtp_server, smtp.smtp_port, smtp.smtp_username, smtp.smtp_password, smtp.from_email, smtp.from_name, 1 if smtp.use_tls else 0),
            )
        else:
            with get_db_cursor() as cursor:
                cursor.execute("DELETE FROM APP_EmailConfig WHERE dwh_code=?", (code,))
                cursor.execute(
                    "INSERT INTO APP_EmailConfig (dwh_code, smtp_server, smtp_port, smtp_username, smtp_password, from_email, from_name, use_tls, actif) VALUES (?,?,?,?,?,?,?,?,1)",
                    (code, smtp.smtp_server, smtp.smtp_port, smtp.smtp_username, smtp.smtp_password, smtp.from_email, smtp.from_name, 1 if smtp.use_tls else 0),
                )
        return {"success": True, "message": "Configuration SMTP sauvegardée"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dwh-admin/{code}/smtp/test")
async def dwh_admin_test_smtp(code: str, smtp: SMTPConfig):
    """Envoie un email de test."""
    import smtplib
    from email.mime.text import MIMEText
    try:
        msg = MIMEText("Test SMTP depuis OptiBoard")
        msg["Subject"] = "Test SMTP — OptiBoard"
        msg["From"] = smtp.from_email
        msg["To"] = smtp.from_email
        with smtplib.SMTP(smtp.smtp_server, smtp.smtp_port, timeout=15) as server:
            if smtp.use_tls:
                server.starttls()
            if smtp.smtp_username:
                server.login(smtp.smtp_username, smtp.smtp_password)
            server.send_message(msg)
        return {"success": True, "message": "Email de test envoyé"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# ROUTES — SOURCES SAGE
# =============================================================================

@router.get("/dwh-admin/{code}/sources")
async def dwh_admin_list_sources(code: str):
    """Liste les sources Sage d'un DWH."""
    try:
        rows = execute_query(
            "SELECT id, dwh_code, code_societe, nom_societe, serveur_sage, base_sage, user_sage, etl_enabled, etl_mode, etl_schedule, last_sync, last_sync_status, actif FROM APP_DWH_Sources WHERE dwh_code=? ORDER BY nom_societe",
            (code,), use_cache=False,
        )
        return {"success": True, "data": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dwh-admin/{code}/sources")
async def dwh_admin_add_source(code: str, source: Dict[str, Any] = Body(...)):
    """Ajoute une source Sage à un DWH."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                "INSERT INTO APP_DWH_Sources (dwh_code, code_societe, nom_societe, serveur_sage, base_sage, user_sage, password_sage, etl_enabled, etl_mode, etl_schedule) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (code, source.get("code_societe"), source.get("nom_societe"), source.get("serveur_sage"), source.get("base_sage"), source.get("user_sage"), source.get("password_sage"), 1 if source.get("etl_enabled", True) else 0, source.get("etl_mode", "incremental"), source.get("etl_schedule", "*/15 * * * *")),
            )
        return {"success": True, "message": "Source ajoutée"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/dwh-admin/{code}/sources/{source_code}")
async def dwh_admin_delete_source(code: str, source_code: str):
    """Supprime une source Sage."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("DELETE FROM APP_DWH_Sources WHERE dwh_code=? AND code_societe=?", (code, source_code))
        return {"success": True, "message": "Source supprimée"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ROUTES — GESTION BASES CLIENT
# =============================================================================

@router.post("/dwh-admin/{code}/patch-tables")
async def dwh_admin_patch_tables(code: str):
    """
    Ajoute les tables manquantes dans la base client OptiBoard_{code}.
    Opération idempotente — sans risque sur une base existante.
    Utile pour appliquer les nouvelles tables après mise à jour (ex: APP_ETL_Agents).
    """
    try:
        result = await asyncio.to_thread(_patch_missing_tables, code)
        return {"success": result["success"], "dwh_code": code, **result}
    except Exception as e:
        logger.error(f"dwh_admin_patch_tables({code}): {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dwh-admin/patch-all-tables")
async def dwh_admin_patch_all_tables():
    """
    Ajoute les tables manquantes dans TOUTES les bases client actives.
    Idempotent — sans risque sur les bases existantes.
    """
    try:
        dwh_list = execute_query(
            "SELECT d.code, d.nom FROM APP_DWH d INNER JOIN APP_ClientDB c ON c.dwh_code=d.code WHERE d.actif=1",
            use_cache=False
        )
        results = []
        for dwh in dwh_list:
            code = dwh["code"]
            try:
                r = await asyncio.to_thread(_patch_missing_tables, code)
                results.append({"dwh_code": code, "nom": dwh["nom"], **r})
            except Exception as e:
                results.append({"dwh_code": code, "nom": dwh["nom"], "success": False, "error": str(e)})
        ok = sum(1 for r in results if r.get("success"))
        return {"success": True, "total": len(results), "ok": ok, "results": results}
    except Exception as e:
        logger.error(f"dwh_admin_patch_all_tables: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dwh-admin/migrate-all")
async def dwh_admin_migrate_all():
    """Crée les bases OptiBoard_XXX pour tous les clients qui n'en ont pas."""
    try:
        return await asyncio.to_thread(_run_migrate_all_clients)
    except Exception as e:
        logger.error(f"dwh_admin_migrate_all: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dwh-admin/{code}/create-client-db")
async def dwh_admin_create_client_db(code: str):
    """Crée la base OptiBoard_clt{code} pour un client."""
    try:
        from ..config_multitenant import get_central_settings
        central = get_central_settings()

        # Lire le nom réel de la base depuis APP_DWH.base_optiboard
        # (peut être personnalisé, ex: OptiBoard_cltFO au lieu de OptiBoard_FO)
        rows_dwh = execute_query(
            "SELECT serveur_optiboard, base_optiboard, user_optiboard, password_optiboard,"
            "       serveur_dwh, user_dwh, password_dwh"
            " FROM APP_DWH WHERE code = ?",
            (code,), use_cache=False
        )
        if rows_dwh:
            r = rows_dwh[0]
            ob_server   = r.get("serveur_optiboard") or r.get("serveur_dwh") or central._effective_server
            ob_user     = r.get("user_optiboard")    or r.get("user_dwh")    or central._effective_user
            ob_password = r.get("password_optiboard") or r.get("password_dwh") or central._effective_password
            db_name     = r.get("base_optiboard") or f"OptiBoard_clt{code}"
        else:
            ob_server   = central._effective_server
            ob_user     = central._effective_user
            ob_password = central._effective_password
            db_name     = f"OptiBoard_clt{code}"

        # Vérifier l'existence RÉELLE de la base (pas seulement APP_ClientDB)
        db_really_exists = _check_db_exists(ob_server, db_name, ob_user, ob_password)
        if db_really_exists:
            # S'assurer que APP_ClientDB a bien l'entrée (peut être absente si DB créée manuellement)
            with get_db_cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM APP_ClientDB WHERE dwh_code=?", (code,))
                if cursor.fetchone()[0] == 0:
                    cursor.execute(
                        "INSERT INTO APP_ClientDB (dwh_code, db_name) VALUES (?, ?)",
                        (code, db_name)
                    )
            client_manager.clear_cache(code)
            return {"success": True, "message": f"'{db_name}' existe déjà", "already_exists": True, "db_name": db_name}
        # Si APP_ClientDB a un enregistrement orphelin, le supprimer pour permettre la recréation
        with get_db_cursor() as cursor:
            cursor.execute("DELETE FROM APP_ClientDB WHERE dwh_code=?", (code,))
        dwh = _get_dwh_or_404(code)
        result = await asyncio.to_thread(_create_client_optiboard_db, code)
        return {"success": True, **result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"dwh_admin_create_client_db({code}): {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dwh-admin/{code}/sync-data")
async def dwh_admin_sync_data(code: str, req: SyncDataRequest):
    """
    Synchronise les données partagées Master → OptiBoard_{code}.

    Mode 'upsert' (défaut) : respecte is_customized=1 (Règle 1).
    Mode 'replace'         : force tout (admin only).
    """
    try:
        return await asyncio.to_thread(_sync_data_to_client, code, req.tables, req.mode)
    except Exception as e:
        logger.error(f"dwh_admin_sync_data({code}): {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dwh-admin/{code}/reset-client-db")
async def dwh_admin_reset_client_db(code: str, req: ResetClientDBRequest):
    """Réinitialise la base client OptiBoard_{code}. Requiert confirm=true."""
    if code.upper() in PROTECTED_DWH_CODES:
        raise HTTPException(status_code=403, detail=f"La base '{code}' est protégée et ne peut pas être réinitialisée")
    if not req.confirm:
        raise HTTPException(status_code=400, detail="Confirmation requise (confirm=true)")
    try:
        return await asyncio.to_thread(_reset_client_db, code, req.keep_user_data)
    except Exception as e:
        logger.error(f"dwh_admin_reset_client_db({code}): {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ROUTE — INITIALISATION MENUS PAR DÉFAUT
# =============================================================================

@router.post("/dwh-admin/{code}/init-menus")
async def dwh_admin_init_menus(code: str):
    """
    Insère les menus et sous-menus par défaut dans la base client OptiBoard_{code}.
    N'agit que si APP_Menus est vide — aucune table créée.
    """
    try:
        conn_str = _get_optiboard_conn_str(code)
        with pyodbc.connect(conn_str, timeout=30) as conn:
            cursor = conn.cursor()
            n = _init_default_menus(cursor)
            if n > 0:
                conn.commit()
                return {"success": True, "message": f"{n} menus créés avec succès", "count": n}
            return {"success": True, "message": "Des menus existent déjà — aucune modification", "count": 0}
    except Exception as e:
        logger.error(f"dwh_admin_init_menus({code}): {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# ROUTE — MARQUER UNE LIGNE COMME PERSONNALISÉE (Règle 1)
# =============================================================================

class MarkCustomizedRequest(BaseModel):
    table: str
    code: str
    is_customized: bool = True


CUSTOMIZABLE_TABLES = {"APP_Menus", "APP_GridViews", "APP_Pivots_V2", "APP_Dashboards", "APP_DataSources"}


@router.post("/dwh-admin/{dwh_code}/mark-customized")
async def dwh_admin_mark_customized(dwh_code: str, req: MarkCustomizedRequest):
    """
    Marque/démarque une ligne comme personnalisée (is_customized).
    Une ligne is_customized=1 ne sera jamais écrasée par les syncs Master.
    """
    if req.table not in CUSTOMIZABLE_TABLES:
        raise HTTPException(status_code=400, detail=f"Table '{req.table}' non personnalisable")
    try:
        from ..database_unified import write_client
        write_client(
            dwh_code,
            f"UPDATE [{req.table}] SET is_customized=? WHERE code=?",
            (1 if req.is_customized else 0, req.code),
        )
        action = "protégée" if req.is_customized else "déprotégée"
        return {"success": True, "message": f"Ligne '{req.code}' dans {req.table} {action} du sync Master"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ROUTE — TÉLÉCHARGER LE SCRIPT SQL D'INITIALISATION OptiBoard CLIENT
# =============================================================================

@router.get("/dwh-admin/{code}/optiboard-sql-script")
async def dwh_admin_optiboard_sql_script(code: str):
    """
    Génère et retourne le script SQL complet pour créer manuellement
    la base OptiBoard du client (CREATE DATABASE + toutes les tables).
    Utile pour les déploiements sur serveur client sans accès réseau direct.
    """
    from fastapi.responses import PlainTextResponse

    rows = execute_query(
        "SELECT base_optiboard FROM APP_DWH WHERE code = ?",
        (code,), use_cache=False
    )
    db_name = (rows[0].get("base_optiboard") if rows else None) or f"OptiBoard_clt{code}"

    script = f"""-- =============================================================
-- Script d'initialisation OptiBoard — Client {code}
-- Base : {db_name}
-- Généré le : {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}
-- =============================================================

-- Étape 1 : Créer la base (à exécuter sur master)
-- IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = N'{db_name}')
--     CREATE DATABASE [{db_name}]
-- GO

USE [{db_name}]
GO

-- Étape 2 : Créer les tables applicatives
{CLIENT_OPTIBOARD_TABLES_SQL}
"""
    filename = f"init_{db_name}.sql"
    return PlainTextResponse(
        content=script,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


# =============================================================================
# ROUTE — RÉPARATION BASE CLIENT (fix typo, reconfiguration)
# =============================================================================

class RepairClientDBRequest(BaseModel):
    base_optiboard: Optional[str] = None       # nouveau nom de la base (ex: OptiBoard_cltFO)
    serveur_optiboard: Optional[str] = None    # serveur cible (ex: kasoft.selfip.net)
    user_optiboard: Optional[str] = None       # utilisateur SQL (ex: sa)
    password_optiboard: Optional[str] = None   # mot de passe SQL
    recreate: bool = False                     # si True, supprime APP_ClientDB et recrée la base


@router.post("/dwh-admin/{code}/repair-client-db")
async def dwh_admin_repair_client_db(code: str, req: RepairClientDBRequest):
    """
    Répare la configuration de la base client pour un DWH donné.

    Cas d'usage typique :
    - Typo dans base_optiboard (ex: OptiBoard_citFO au lieu de OptiBoard_cltFO)
    - Changement de serveur ou de credentials OptiBoard
    - Entrée orpheline dans APP_ClientDB

    Paramètres:
    - base_optiboard : nouveau nom de la base (laissez vide pour auto: OptiBoard_clt{code})
    - serveur_optiboard / user_optiboard / password_optiboard : nouveaux credentials
    - recreate : si True, supprime APP_ClientDB et déclenche la re-création de la base
    """
    try:
        repairs = []

        # ── Calcul du nom correct si non fourni ──────────────────────────────
        new_base = (req.base_optiboard or f"OptiBoard_clt{code}").strip()

        # ── Lire l'état actuel dans APP_DWH ──────────────────────────────────
        rows = execute_query(
            "SELECT base_optiboard, serveur_optiboard, user_optiboard FROM APP_DWH WHERE code = ?",
            (code,), use_cache=False
        )
        if not rows:
            raise HTTPException(status_code=404, detail=f"DWH '{code}' introuvable dans APP_DWH")

        current = rows[0]

        # ── Mise à jour APP_DWH ───────────────────────────────────────────────
        updates = {}
        if new_base and new_base != current.get("base_optiboard"):
            updates["base_optiboard"] = new_base
        if req.serveur_optiboard is not None:
            updates["serveur_optiboard"] = req.serveur_optiboard or None
        if req.user_optiboard is not None:
            updates["user_optiboard"] = req.user_optiboard or None
        if req.password_optiboard is not None:
            updates["password_optiboard"] = req.password_optiboard or None

        if updates:
            set_clauses = ", ".join(f"{k}=?" for k in updates)
            vals = list(updates.values()) + [code]
            with get_db_cursor() as cursor:
                cursor.execute(f"UPDATE APP_DWH SET {set_clauses} WHERE code=?", vals)
            repairs.append(f"APP_DWH mis à jour : {updates}")

        # ── Supprimer l'entrée APP_ClientDB orpheline ─────────────────────────
        if req.recreate:
            with get_db_cursor() as cursor:
                cursor.execute("DELETE FROM APP_ClientDB WHERE dwh_code=?", (code,))
            repairs.append("APP_ClientDB nettoyée (entrée orpheline supprimée)")

        # ── Vider le cache mémoire ────────────────────────────────────────────
        client_manager.clear_cache(code)
        repairs.append("Cache mémoire vidé")

        # ── Recréer la base si demandé ────────────────────────────────────────
        client_db_result = None
        if req.recreate:
            try:
                client_db_result = await asyncio.to_thread(_create_client_optiboard_db, code)
                repairs.append(f"Base client recréée : {client_db_result.get('db_name', new_base)}")
            except Exception as e:
                repairs.append(f"Erreur recréation base: {e}")

        return {
            "success": True,
            "code": code,
            "new_base_optiboard": new_base,
            "repairs": repairs,
            "client_db_result": client_db_result,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"dwh_admin_repair_client_db({code}): {e}")
        raise HTTPException(status_code=500, detail=str(e))
