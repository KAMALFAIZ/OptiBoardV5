-- ============================================================
-- OptiBoard Client Autonome - Initialisation v1.0.0
-- Variables sqlcmd :
--   $(APP_DB_NAME)  : nom base application  (ex: OptiBoard_Client)
--   $(DWH_DB_NAME)  : nom base DWH          (ex: DWH_Client)
--   $(DWH_CODE)     : code client           (ex: CLIENT01)
-- ============================================================

PRINT '>>> Création base application : $(APP_DB_NAME)'
GO
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = '$(APP_DB_NAME)')
BEGIN
    CREATE DATABASE [$(APP_DB_NAME)];
    PRINT '    [OK] Base créée.';
END
ELSE
    PRINT '    [INFO] Base déjà existante.';
GO

PRINT '>>> Création base DWH : $(DWH_DB_NAME)'
GO
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = '$(DWH_DB_NAME)')
BEGIN
    CREATE DATABASE [$(DWH_DB_NAME)];
    PRINT '    [OK] Base DWH créée.';
END
ELSE
    PRINT '    [INFO] Base DWH déjà existante.';
GO

-- ============================================================
-- Basculer sur la base application
-- ============================================================
USE [$(APP_DB_NAME)];
GO

-- ============================================================
-- TABLE : APP_Users
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Users' AND xtype='U')
BEGIN
    CREATE TABLE APP_Users (
        id                    INT IDENTITY(1,1) PRIMARY KEY,
        username              VARCHAR(100)   NOT NULL,
        password_hash         VARCHAR(200)   NULL,
        nom                   NVARCHAR(200)  NULL,
        prenom                NVARCHAR(100)  NULL,
        email                 VARCHAR(200)   NULL,
        role_dwh              VARCHAR(50)    NOT NULL DEFAULT 'user',
        actif                 BIT            NOT NULL DEFAULT 1,
        must_change_password  BIT            NOT NULL DEFAULT 0,
        derniere_connexion    DATETIME       NULL,
        date_creation         DATETIME       NOT NULL DEFAULT GETDATE(),
        CONSTRAINT UQ_Users_username UNIQUE (username)
    );
    PRINT '    [OK] APP_Users créée.';
END
GO

-- ============================================================
-- TABLE : APP_DWH  (registre DWH - utilisé par execute_central)
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_DWH' AND xtype='U')
BEGIN
    CREATE TABLE APP_DWH (
        code                  VARCHAR(50)    NOT NULL PRIMARY KEY,
        nom                   NVARCHAR(200)  NOT NULL,
        raison_sociale        NVARCHAR(200)  NULL,
        serveur_dwh           VARCHAR(200)   NULL,
        base_dwh              VARCHAR(100)   NULL,
        user_dwh              VARCHAR(100)   NULL,
        password_dwh          VARCHAR(200)   NULL,
        serveur_optiboard     VARCHAR(200)   NULL,
        base_optiboard        VARCHAR(100)   NULL,
        user_optiboard        VARCHAR(100)   NULL,
        password_optiboard    VARCHAR(200)   NULL,
        actif                 BIT            NOT NULL DEFAULT 1,
        date_creation         DATETIME       NOT NULL DEFAULT GETDATE()
    );
    PRINT '    [OK] APP_DWH créée.';
END
GO

-- ============================================================
-- TABLE : APP_ClientDB  (registre base client - utilisé par execute_client)
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ClientDB' AND xtype='U')
BEGIN
    CREATE TABLE APP_ClientDB (
        id                INT IDENTITY(1,1) PRIMARY KEY,
        dwh_code          VARCHAR(50)    NOT NULL,
        db_name           NVARCHAR(100)  NOT NULL,
        db_server         NVARCHAR(200)  NULL,
        db_user           NVARCHAR(100)  NULL,
        db_password       NVARCHAR(200)  NULL,
        actif             BIT            NOT NULL DEFAULT 1,
        date_creation     DATETIME       NOT NULL DEFAULT GETDATE(),
        CONSTRAINT UQ_ClientDB_code UNIQUE (dwh_code)
    );
    PRINT '    [OK] APP_ClientDB créée.';
END
GO

-- ============================================================
-- TABLE : APP_UserPages
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_UserPages' AND xtype='U')
BEGIN
    CREATE TABLE APP_UserPages (
        id         INT IDENTITY(1,1) PRIMARY KEY,
        user_id    INT          NOT NULL,
        page_code  VARCHAR(50)  NOT NULL
    );
    PRINT '    [OK] APP_UserPages créée.';
END
GO

-- ============================================================
-- TABLE : APP_UserMenus
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_UserMenus' AND xtype='U')
BEGIN
    CREATE TABLE APP_UserMenus (
        id          INT IDENTITY(1,1) PRIMARY KEY,
        user_id     INT  NOT NULL,
        menu_id     INT  NOT NULL,
        can_view    BIT  NOT NULL DEFAULT 1,
        can_export  BIT  NOT NULL DEFAULT 1
    );
    PRINT '    [OK] APP_UserMenus créée.';
END
GO

-- ============================================================
-- TABLE : APP_Dashboards
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Dashboards' AND xtype='U')
BEGIN
    CREATE TABLE APP_Dashboards (
        id                INT IDENTITY(1,1) PRIMARY KEY,
        nom               NVARCHAR(200)  NOT NULL,
        code              VARCHAR(100)   NULL,
        description       NVARCHAR(500)  NULL,
        config            NVARCHAR(MAX)  NULL,
        widgets           NVARCHAR(MAX)  NULL,
        is_public         BIT            NOT NULL DEFAULT 0,
        is_custom         BIT            NOT NULL DEFAULT 0,
        is_customized     BIT            NOT NULL DEFAULT 0,
        created_by        INT            NULL,
        actif             BIT            NOT NULL DEFAULT 1,
        date_creation     DATETIME       NOT NULL DEFAULT GETDATE(),
        date_modification DATETIME       NOT NULL DEFAULT GETDATE()
    );
    PRINT '    [OK] APP_Dashboards créée.';
END
GO

-- ============================================================
-- TABLE : APP_DataSources
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_DataSources' AND xtype='U')
BEGIN
    CREATE TABLE APP_DataSources (
        id                INT IDENTITY(1,1) PRIMARY KEY,
        nom               NVARCHAR(200)  NOT NULL,
        code              VARCHAR(100)   NULL,
        type              VARCHAR(50)    NOT NULL DEFAULT 'query',
        query_template    NVARCHAR(MAX)  NULL,
        parameters        NVARCHAR(MAX)  NULL,
        description       NVARCHAR(500)  NULL,
        is_custom         BIT            NOT NULL DEFAULT 0,
        is_customized     BIT            NOT NULL DEFAULT 0,
        date_creation     DATETIME       NOT NULL DEFAULT GETDATE()
    );
    PRINT '    [OK] APP_DataSources créée.';
END
GO

-- ============================================================
-- TABLE : APP_GridViews
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_GridViews' AND xtype='U')
BEGIN
    CREATE TABLE APP_GridViews (
        id                INT IDENTITY(1,1) PRIMARY KEY,
        nom               NVARCHAR(200)  NOT NULL,
        code              VARCHAR(100)   NULL,
        description       NVARCHAR(500)  NULL,
        query_template    NVARCHAR(MAX)  NULL,
        columns_config    NVARCHAR(MAX)  NULL,
        parameters        NVARCHAR(MAX)  NULL,
        features          NVARCHAR(MAX)  NULL,
        is_custom         BIT            NOT NULL DEFAULT 0,
        is_customized     BIT            NOT NULL DEFAULT 0,
        actif             BIT            NOT NULL DEFAULT 1,
        date_creation     DATETIME       NOT NULL DEFAULT GETDATE(),
        date_modification DATETIME       NOT NULL DEFAULT GETDATE()
    );
    PRINT '    [OK] APP_GridViews créée.';
END
GO

-- ============================================================
-- TABLE : APP_GridView_User_Prefs
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_GridView_User_Prefs' AND xtype='U')
BEGIN
    CREATE TABLE APP_GridView_User_Prefs (
        id                INT IDENTITY(1,1) PRIMARY KEY,
        gridview_id       INT            NOT NULL,
        user_id           INT            NOT NULL,
        columns_config    NVARCHAR(MAX)  NULL,
        date_modification DATETIME       NOT NULL DEFAULT GETDATE(),
        CONSTRAINT UQ_GridView_User UNIQUE (gridview_id, user_id)
    );
    PRINT '    [OK] APP_GridView_User_Prefs créée.';
END
GO

-- ============================================================
-- TABLE : APP_Pivots_V2
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Pivots_V2' AND xtype='U')
BEGIN
    CREATE TABLE APP_Pivots_V2 (
        id                     INT IDENTITY(1,1) PRIMARY KEY,
        nom                    NVARCHAR(200)  NOT NULL,
        code                   VARCHAR(100)   NULL,
        description            NVARCHAR(500)  NULL,
        data_source_id         INT            NULL,
        data_source_code       VARCHAR(100)   NULL,
        rows_config            NVARCHAR(MAX)  NULL,
        columns_config         NVARCHAR(MAX)  NULL,
        filters_config         NVARCHAR(MAX)  NULL,
        values_config          NVARCHAR(MAX)  NULL,
        show_grand_totals      BIT            NOT NULL DEFAULT 1,
        show_subtotals         BIT            NOT NULL DEFAULT 0,
        show_row_percent       BIT            NOT NULL DEFAULT 0,
        show_col_percent       BIT            NOT NULL DEFAULT 0,
        show_total_percent     BIT            NOT NULL DEFAULT 0,
        comparison_mode        NVARCHAR(50)   NULL,
        formatting_rules       NVARCHAR(MAX)  NULL,
        source_params          NVARCHAR(MAX)  NULL,
        is_public              BIT            NOT NULL DEFAULT 0,
        is_custom              BIT            NOT NULL DEFAULT 0,
        is_customized          BIT            NOT NULL DEFAULT 0,
        created_by             INT            NULL,
        grand_total_position   NVARCHAR(20)   NOT NULL DEFAULT 'bottom',
        subtotal_position      NVARCHAR(20)   NOT NULL DEFAULT 'bottom',
        show_summary_row       BIT            NOT NULL DEFAULT 0,
        summary_functions      NVARCHAR(MAX)  NULL,
        window_calculations    NVARCHAR(MAX)  NULL,
        created_at             DATETIME       NOT NULL DEFAULT GETDATE(),
        updated_at             DATETIME       NOT NULL DEFAULT GETDATE()
    );
    PRINT '    [OK] APP_Pivots_V2 créée.';
END
GO

-- ============================================================
-- TABLE : APP_Pivot_User_Prefs
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Pivot_User_Prefs' AND xtype='U')
BEGIN
    CREATE TABLE APP_Pivot_User_Prefs (
        id                INT IDENTITY(1,1) PRIMARY KEY,
        pivot_id          INT            NOT NULL,
        user_id           INT            NOT NULL,
        custom_config     NVARCHAR(MAX)  NULL,
        date_modification DATETIME       NOT NULL DEFAULT GETDATE(),
        CONSTRAINT UQ_Pivot_User UNIQUE (pivot_id, user_id)
    );
    PRINT '    [OK] APP_Pivot_User_Prefs créée.';
END
GO

-- ============================================================
-- TABLE : APP_Menus
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Menus' AND xtype='U')
BEGIN
    CREATE TABLE APP_Menus (
        id            INT IDENTITY(1,1) PRIMARY KEY,
        nom           NVARCHAR(100)  NOT NULL,
        code          VARCHAR(100)   NULL,
        icon          VARCHAR(50)    NULL,
        url           VARCHAR(200)   NULL,
        parent_id     INT            NULL,
        ordre         INT            NOT NULL DEFAULT 0,
        type          VARCHAR(20)    NOT NULL DEFAULT 'link',
        target_id     INT            NULL,
        actif         BIT            NOT NULL DEFAULT 1,
        is_custom     BIT            NOT NULL DEFAULT 0,
        is_customized BIT            NOT NULL DEFAULT 0,
        roles         NVARCHAR(200)  NULL,
        date_creation DATETIME       NOT NULL DEFAULT GETDATE()
    );
    PRINT '    [OK] APP_Menus créée.';
END
GO

-- ============================================================
-- TABLE : APP_Settings
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Settings' AND xtype='U')
BEGIN
    CREATE TABLE APP_Settings (
        id                INT IDENTITY(1,1) PRIMARY KEY,
        setting_key       VARCHAR(100)   NOT NULL,
        setting_value     NVARCHAR(MAX)  NULL,
        setting_type      VARCHAR(20)    NOT NULL DEFAULT 'string',
        description       NVARCHAR(500)  NULL,
        date_modification DATETIME       NOT NULL DEFAULT GETDATE(),
        CONSTRAINT UQ_Settings_key UNIQUE (setting_key)
    );
    PRINT '    [OK] APP_Settings créée.';
END
GO

-- ============================================================
-- TABLE : APP_EmailConfig
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_EmailConfig' AND xtype='U')
BEGIN
    CREATE TABLE APP_EmailConfig (
        id                INT IDENTITY(1,1) PRIMARY KEY,
        smtp_server       VARCHAR(200)  NULL,
        smtp_port         INT           NOT NULL DEFAULT 587,
        smtp_username     VARCHAR(200)  NULL,
        smtp_password     VARCHAR(200)  NULL,
        from_email        VARCHAR(200)  NULL,
        from_name         NVARCHAR(100) NULL,
        use_ssl           BIT           NOT NULL DEFAULT 0,
        use_tls           BIT           NOT NULL DEFAULT 1,
        actif             BIT           NOT NULL DEFAULT 1,
        date_modification DATETIME      NOT NULL DEFAULT GETDATE()
    );
    PRINT '    [OK] APP_EmailConfig créée.';
END
GO

-- ============================================================
-- TABLE : APP_ReportSchedules
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ReportSchedules' AND xtype='U')
BEGIN
    CREATE TABLE APP_ReportSchedules (
        id            INT IDENTITY(1,1) PRIMARY KEY,
        nom           NVARCHAR(255)  NOT NULL,
        description   NVARCHAR(MAX)  NULL,
        report_type   NVARCHAR(50)   NOT NULL,
        report_id     INT            NULL,
        export_format NVARCHAR(20)   NOT NULL DEFAULT 'excel',
        frequency     NVARCHAR(20)   NOT NULL,
        schedule_time NVARCHAR(10)   NOT NULL DEFAULT '08:00',
        schedule_day  INT            NULL,
        recipients    NVARCHAR(MAX)  NOT NULL,
        cc_recipients NVARCHAR(MAX)  NULL,
        filters       NVARCHAR(MAX)  NULL,
        is_active     BIT            NOT NULL DEFAULT 1,
        last_run      DATETIME       NULL,
        next_run      DATETIME       NULL,
        created_by    INT            NULL,
        created_at    DATETIME       NOT NULL DEFAULT GETDATE(),
        updated_at    DATETIME       NOT NULL DEFAULT GETDATE()
    );
    PRINT '    [OK] APP_ReportSchedules créée.';
END
GO

-- ============================================================
-- TABLE : APP_ReportHistory
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ReportHistory' AND xtype='U')
BEGIN
    CREATE TABLE APP_ReportHistory (
        id            INT IDENTITY(1,1) PRIMARY KEY,
        schedule_id   INT            NULL,
        report_name   NVARCHAR(255)  NULL,
        recipients    NVARCHAR(MAX)  NULL,
        status        NVARCHAR(20)   NOT NULL,
        error_message NVARCHAR(MAX)  NULL,
        file_path     NVARCHAR(500)  NULL,
        file_size     INT            NULL,
        sent_at       DATETIME       NOT NULL DEFAULT GETDATE(),
        CONSTRAINT FK_ReportHistory_Schedule
            FOREIGN KEY (schedule_id) REFERENCES APP_ReportSchedules(id) ON DELETE SET NULL
    );
    PRINT '    [OK] APP_ReportHistory créée.';
END
GO

-- ============================================================
-- TABLE : APP_AuditLog
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_AuditLog' AND xtype='U')
BEGIN
    CREATE TABLE APP_AuditLog (
        id           BIGINT IDENTITY(1,1) PRIMARY KEY,
        user_id      INT            NULL,
        action       VARCHAR(50)    NOT NULL,
        entity_type  VARCHAR(50)    NULL,
        entity_id    INT            NULL,
        details      NVARCHAR(MAX)  NULL,
        ip_address   VARCHAR(50)    NULL,
        user_agent   NVARCHAR(500)  NULL,
        date_action  DATETIME       NOT NULL DEFAULT GETDATE()
    );
    PRINT '    [OK] APP_AuditLog créée.';
END
GO

-- ============================================================
-- TABLE : APP_ETL_Agents
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Agents' AND xtype='U')
BEGIN
    CREATE TABLE APP_ETL_Agents (
        id                          INT IDENTITY(1,1) PRIMARY KEY,
        agent_id                    VARCHAR(100)   NOT NULL,
        nom                         NVARCHAR(200)  NOT NULL,
        description                 NVARCHAR(500)  NULL,
        sage_server                 VARCHAR(200)   NULL,
        sage_database               VARCHAR(100)   NULL,
        sage_username               VARCHAR(100)   NULL,
        sage_password               VARCHAR(200)   NULL,
        sync_interval_secondes      INT            NOT NULL DEFAULT 300,
        heartbeat_interval_secondes INT            NOT NULL DEFAULT 30,
        batch_size                  INT            NOT NULL DEFAULT 10000,
        is_active                   BIT            NOT NULL DEFAULT 1,
        auto_start                  BIT            NOT NULL DEFAULT 1,
        statut                      VARCHAR(20)    NOT NULL DEFAULT 'inactif',
        last_heartbeat              DATETIME       NULL,
        last_sync                   DATETIME       NULL,
        last_sync_statut            VARCHAR(20)    NULL,
        consecutive_failures        INT            NOT NULL DEFAULT 0,
        total_syncs                 INT            NOT NULL DEFAULT 0,
        total_lignes_sync           BIGINT         NOT NULL DEFAULT 0,
        hostname                    VARCHAR(200)   NULL,
        ip_address                  VARCHAR(50)    NULL,
        os_info                     VARCHAR(200)   NULL,
        agent_version               VARCHAR(50)    NULL,
        api_key_hash                VARCHAR(64)    NULL,
        api_key_prefix              VARCHAR(20)    NULL,
        created_at                  DATETIME       NOT NULL DEFAULT GETDATE(),
        updated_at                  DATETIME       NOT NULL DEFAULT GETDATE(),
        CONSTRAINT UQ_ETL_Agents_id UNIQUE (agent_id)
    );
    PRINT '    [OK] APP_ETL_Agents créée.';
END
GO

-- ============================================================
-- TABLE : APP_ETL_Agent_Tables
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Agent_Tables' AND xtype='U')
BEGIN
    CREATE TABLE APP_ETL_Agent_Tables (
        id                  INT IDENTITY(1,1) PRIMARY KEY,
        agent_id            VARCHAR(100)   NOT NULL,
        table_name          VARCHAR(100)   NOT NULL,
        source_query        NVARCHAR(MAX)  NULL,
        target_table        VARCHAR(100)   NULL,
        societe_code        VARCHAR(100)   NULL,
        primary_key_columns NVARCHAR(500)  NULL,
        sync_type           VARCHAR(50)    NOT NULL DEFAULT 'incremental',
        timestamp_column    VARCHAR(100)   NULL,
        priority            VARCHAR(20)    NOT NULL DEFAULT 'normal',
        is_enabled          BIT            NOT NULL DEFAULT 1,
        interval_minutes    INT            NOT NULL DEFAULT 5,
        delete_detection    BIT            NOT NULL DEFAULT 0,
        description         NVARCHAR(500)  NULL,
        is_inherited        BIT            NOT NULL DEFAULT 0,
        is_customized       BIT            NOT NULL DEFAULT 0,
        last_sync           DATETIME       NULL,
        last_sync_status    VARCHAR(50)    NULL,
        last_sync_rows      INT            NULL,
        last_error          NVARCHAR(MAX)  NULL,
        created_at          DATETIME       NOT NULL DEFAULT GETDATE(),
        updated_at          DATETIME       NULL
    );
    PRINT '    [OK] APP_ETL_Agent_Tables créée.';
END
GO

-- ============================================================
-- TABLE : APP_ETL_Agent_Sync_Log
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Agent_Sync_Log' AND xtype='U')
BEGIN
    CREATE TABLE APP_ETL_Agent_Sync_Log (
        id               INT IDENTITY(1,1) PRIMARY KEY,
        agent_id         VARCHAR(100)   NULL,
        table_id         INT            NULL,
        table_name       VARCHAR(100)   NULL,
        start_time       DATETIME       NULL,
        end_time         DATETIME       NULL,
        rows_extracted   INT            NULL,
        rows_inserted    INT            NULL,
        rows_updated     INT            NULL,
        rows_deleted     INT            NULL,
        rows_failed      INT            NULL,
        status           VARCHAR(50)    NULL,
        error_message    NVARCHAR(MAX)  NULL,
        duration_seconds INT            NULL,
        batch_id         VARCHAR(100)   NULL
    );
    PRINT '    [OK] APP_ETL_Agent_Sync_Log créée.';
END
GO

-- ============================================================
-- TABLE : APP_ETL_Agent_Commands
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Agent_Commands' AND xtype='U')
BEGIN
    CREATE TABLE APP_ETL_Agent_Commands (
        id           INT IDENTITY(1,1) PRIMARY KEY,
        agent_id     VARCHAR(100)   NOT NULL,
        command_type VARCHAR(50)    NOT NULL,
        command_data NVARCHAR(MAX)  NULL,
        priority     INT            NOT NULL DEFAULT 1,
        status       VARCHAR(20)    NOT NULL DEFAULT 'pending',
        created_at   DATETIME       NOT NULL DEFAULT GETDATE(),
        expires_at   DATETIME       NULL,
        executed_at  DATETIME       NULL,
        result       NVARCHAR(MAX)  NULL
    );
    PRINT '    [OK] APP_ETL_Agent_Commands créée.';
END
GO

-- ============================================================
-- TABLE : APP_ETL_Tables_Config
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Tables_Config' AND xtype='U')
BEGIN
    CREATE TABLE APP_ETL_Tables_Config (
        id                  INT IDENTITY(1,1) PRIMARY KEY,
        code                VARCHAR(100)   NOT NULL,
        table_name          NVARCHAR(100)  NOT NULL,
        target_table        NVARCHAR(100)  NOT NULL,
        source_query        NVARCHAR(MAX)  NOT NULL,
        primary_key_columns NVARCHAR(500)  NOT NULL,
        sync_type           VARCHAR(20)    NOT NULL DEFAULT 'incremental',
        timestamp_column    NVARCHAR(100)  NOT NULL DEFAULT 'cbModification',
        interval_minutes    INT            NOT NULL DEFAULT 5,
        priority            VARCHAR(20)    NOT NULL DEFAULT 'normal',
        delete_detection    BIT            NOT NULL DEFAULT 0,
        description         NVARCHAR(500)  NULL,
        version             INT            NOT NULL DEFAULT 1,
        actif               BIT            NOT NULL DEFAULT 1,
        date_creation       DATETIME       NOT NULL DEFAULT GETDATE(),
        date_modification   DATETIME       NULL,
        CONSTRAINT UQ_ETL_Tables_code UNIQUE (code)
    );
    PRINT '    [OK] APP_ETL_Tables_Config créée.';
END
GO

-- ============================================================
-- TABLE : APP_ETL_Tables_Published
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_ETL_Tables_Published' AND xtype='U')
BEGIN
    CREATE TABLE APP_ETL_Tables_Published (
        id                INT IDENTITY(1,1) PRIMARY KEY,
        code              VARCHAR(100)   NOT NULL,
        table_name        VARCHAR(200)   NOT NULL,
        target_table      VARCHAR(200)   NOT NULL,
        source_query      NVARCHAR(MAX)  NULL,
        primary_key_columns NVARCHAR(500) NULL,
        sync_type         VARCHAR(50)    NOT NULL DEFAULT 'incremental',
        timestamp_column  VARCHAR(100)   NOT NULL DEFAULT 'cbModification',
        interval_minutes  INT            NOT NULL DEFAULT 5,
        priority          VARCHAR(20)    NOT NULL DEFAULT 'normal',
        delete_detection  BIT            NOT NULL DEFAULT 0,
        description       NVARCHAR(500)  NULL,
        version_centrale  INT            NOT NULL DEFAULT 1,
        is_enabled        BIT            NOT NULL DEFAULT 1,
        date_publication  DATETIME       NOT NULL DEFAULT GETDATE(),
        date_modification DATETIME       NOT NULL DEFAULT GETDATE(),
        CONSTRAINT UQ_ETL_Published_code UNIQUE (code)
    );
    PRINT '    [OK] APP_ETL_Tables_Published créée.';
END
GO

-- ============================================================
-- TABLE : APP_Update_History
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Update_History' AND xtype='U')
BEGIN
    CREATE TABLE APP_Update_History (
        id                  INT IDENTITY(1,1) PRIMARY KEY,
        type_entite         VARCHAR(50)    NOT NULL,
        code_entite         VARCHAR(100)   NULL,
        nom_entite          NVARCHAR(200)  NULL,
        version_precedente  INT            NULL,
        version_installee   INT            NOT NULL DEFAULT 1,
        statut              VARCHAR(20)    NOT NULL DEFAULT 'succes',
        message_erreur      NVARCHAR(MAX)  NULL,
        date_installation   DATETIME       NOT NULL DEFAULT GETDATE()
    );
    PRINT '    [OK] APP_Update_History créée.';
END
GO

-- ============================================================
-- TABLE : APP_DB_Version  (registre des migrations)
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_DB_Version' AND xtype='U')
BEGIN
    CREATE TABLE APP_DB_Version (
        id           INT IDENTITY(1,1) PRIMARY KEY,
        version      VARCHAR(20)    NOT NULL,
        script_name  VARCHAR(200)   NULL,
        applied_at   DATETIME       NOT NULL DEFAULT GETDATE(),
        description  NVARCHAR(500)  NULL
    );
    PRINT '    [OK] APP_DB_Version créée.';
END
GO

-- ============================================================
-- DONNÉES INITIALES
-- ============================================================

-- Enregistrer la version installée
IF NOT EXISTS (SELECT 1 FROM APP_DB_Version WHERE version = '1.0.0')
BEGIN
    INSERT INTO APP_DB_Version (version, script_name, description)
    VALUES ('1.0.0', 'V1.0.0__init.sql', 'Installation initiale OptiBoard Client Autonome');
    PRINT '    [OK] Version 1.0.0 enregistrée.';
END
GO

-- Paramètre : mode standalone
IF NOT EXISTS (SELECT 1 FROM APP_Settings WHERE setting_key = 'standalone_mode')
BEGIN
    INSERT INTO APP_Settings (setting_key, setting_value, setting_type, description)
    VALUES ('standalone_mode', '1', 'bool', 'Mode client autonome sans connexion au master KASOFT');
    PRINT '    [OK] Paramètre standalone_mode inséré.';
END
GO

IF NOT EXISTS (SELECT 1 FROM APP_Settings WHERE setting_key = 'setup_completed')
BEGIN
    INSERT INTO APP_Settings (setting_key, setting_value, setting_type, description)
    VALUES ('setup_completed', '0', 'bool', 'Wizard de configuration initial effectué');
    PRINT '    [OK] Paramètre setup_completed inséré.';
END
GO

-- Registre DWH local (pointe vers DWH_Client sur le même serveur SQL)
IF NOT EXISTS (SELECT 1 FROM APP_DWH WHERE code = '$(DWH_CODE)')
BEGIN
    INSERT INTO APP_DWH (
        code, nom, serveur_dwh, base_dwh, user_dwh, password_dwh,
        serveur_optiboard, base_optiboard, actif
    )
    VALUES (
        '$(DWH_CODE)', 'Client Autonome',
        'sqlserver', '$(DWH_DB_NAME)', 'sa', '',
        'sqlserver', '$(APP_DB_NAME)', 1
    );
    PRINT '    [OK] APP_DWH initialisé pour $(DWH_CODE).';
END
GO

-- Registre base client (pointe vers la base locale)
IF NOT EXISTS (SELECT 1 FROM APP_ClientDB WHERE dwh_code = '$(DWH_CODE)')
BEGIN
    INSERT INTO APP_ClientDB (dwh_code, db_name, db_server, db_user, actif)
    VALUES ('$(DWH_CODE)', '$(APP_DB_NAME)', 'sqlserver', 'sa', 1);
    PRINT '    [OK] APP_ClientDB initialisé pour $(DWH_CODE).';
END
GO

PRINT ''
PRINT '============================================'
PRINT ' OptiBoard Client - Initialisation terminée'
PRINT ' Base app  : $(APP_DB_NAME)'
PRINT ' Base DWH  : $(DWH_DB_NAME)'
PRINT ' Code DWH  : $(DWH_CODE)'
PRINT '============================================'
GO
