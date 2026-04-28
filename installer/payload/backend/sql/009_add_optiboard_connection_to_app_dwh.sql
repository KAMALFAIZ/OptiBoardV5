-- =============================================================
-- Migration 009 — Connexion OptiBoard per-client dans APP_DWH
-- =============================================================
-- Nouvelle architecture : chaque client peut avoir sa propre
-- base OptiBoard sur un serveur différent du DWH Sage.
--
-- Champs ajoutés :
--   serveur_optiboard   : serveur SQL de la base OptiBoard client
--   base_optiboard      : nom de la base (ex: OptiBoard_cltKAZ1)
--   user_optiboard      : login SQL
--   password_optiboard  : mot de passe SQL
--
-- Si vides → fallback sur le serveur central (ancienne architecture)
-- =============================================================

IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('APP_DWH') AND name = 'serveur_optiboard'
)
    ALTER TABLE APP_DWH ADD serveur_optiboard NVARCHAR(200) NULL;

IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('APP_DWH') AND name = 'base_optiboard'
)
    ALTER TABLE APP_DWH ADD base_optiboard NVARCHAR(200) NULL;

IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('APP_DWH') AND name = 'user_optiboard'
)
    ALTER TABLE APP_DWH ADD user_optiboard NVARCHAR(100) NULL;

IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('APP_DWH') AND name = 'password_optiboard'
)
    ALTER TABLE APP_DWH ADD password_optiboard NVARCHAR(200) NULL;

-- Remplir base_optiboard pour les clients existants
-- (hérite de OptiBoard_{code} si non renseigné)
UPDATE APP_DWH
SET base_optiboard = CONCAT('OptiBoard_', code)
WHERE base_optiboard IS NULL OR base_optiboard = '';

-- ─────────────────────────────────────────────────────
-- Mettre à jour APP_ClientDB pour synchroniser db_name
-- avec base_optiboard et propager les credentials
-- ─────────────────────────────────────────────────────
UPDATE c
SET c.db_name     = d.base_optiboard,
    c.db_server   = NULLIF(d.serveur_optiboard, ''),
    c.db_user     = NULLIF(d.user_optiboard,    ''),
    c.db_password = NULLIF(d.password_optiboard,'')
FROM APP_ClientDB c
INNER JOIN APP_DWH d ON d.code = c.dwh_code
WHERE d.base_optiboard IS NOT NULL
  AND d.base_optiboard != '';

PRINT 'Migration 009 : colonnes optiboard ajoutées à APP_DWH + APP_ClientDB synchronisé';
