-- ============================================================================
-- Pivot Builder V2 - Schema SQL
-- Tables: APP_Pivots_V2, APP_Pivot_User_Prefs
-- ============================================================================

-- Table principale des configurations pivots
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'APP_Pivots_V2')
BEGIN
    CREATE TABLE APP_Pivots_V2 (
        id INT IDENTITY(1,1) PRIMARY KEY,
        nom NVARCHAR(200) NOT NULL,
        description NVARCHAR(500),
        data_source_id INT,
        data_source_code VARCHAR(100),

        -- Configuration axes (JSON)
        rows_config NVARCHAR(MAX),
        columns_config NVARCHAR(MAX),
        filters_config NVARCHAR(MAX),

        -- Configuration valeurs (JSON)
        values_config NVARCHAR(MAX),

        -- Options
        show_grand_totals BIT DEFAULT 1,
        show_subtotals BIT DEFAULT 1,
        show_row_percent BIT DEFAULT 0,
        show_col_percent BIT DEFAULT 0,
        show_total_percent BIT DEFAULT 0,
        comparison_mode VARCHAR(20) NULL,

        -- Formatage conditionnel (JSON)
        formatting_rules NVARCHAR(MAX),

        -- Parametres source detectes (JSON)
        source_params NVARCHAR(MAX),

        -- Metadata
        is_public BIT DEFAULT 0,
        created_by INT,
        created_at DATETIME DEFAULT GETDATE(),
        updated_at DATETIME DEFAULT GETDATE()
    );
    PRINT 'Table APP_Pivots_V2 creee avec succes';
END;

-- Table des preferences utilisateur par pivot
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'APP_Pivot_User_Prefs')
BEGIN
    CREATE TABLE APP_Pivot_User_Prefs (
        id INT IDENTITY(1,1) PRIMARY KEY,
        pivot_id INT NOT NULL,
        user_id INT NOT NULL,

        -- Config utilisateur sauvee (JSON) - overrides visuels
        custom_config NVARCHAR(MAX),

        -- Etat UI (JSON)
        ui_state NVARCHAR(MAX),

        updated_at DATETIME DEFAULT GETDATE(),

        CONSTRAINT FK_PivotPrefs_Pivot FOREIGN KEY (pivot_id)
            REFERENCES APP_Pivots_V2(id) ON DELETE CASCADE,
        CONSTRAINT UQ_PivotPrefs UNIQUE (pivot_id, user_id)
    );
    PRINT 'Table APP_Pivot_User_Prefs creee avec succes';
END;
