-- =====================================================
-- Script de creation des tables DWH pour OptiBoard_SaaS
-- Architecture 2: Multi-DWH avec acces par utilisateur
-- =====================================================

-- Table APP_DWH: Liste des Data Warehouses disponibles
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_DWH' AND xtype='U')
CREATE TABLE APP_DWH (
    id INT IDENTITY(1,1) PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,           -- Code unique du DWH (ex: DWH_CLIENT1)
    nom NVARCHAR(200) NOT NULL,                 -- Nom affiche (ex: "Client ABC - Production")
    serveur VARCHAR(200) NOT NULL,              -- Serveur SQL (ex: "192.168.1.100" ou "server.domain.com")
    base_donnees VARCHAR(100) NOT NULL,         -- Nom de la base de donnees
    username VARCHAR(100) NOT NULL,             -- Utilisateur SQL
    password VARCHAR(200) NOT NULL,             -- Mot de passe SQL
    description NVARCHAR(500),                  -- Description optionnelle
    actif BIT DEFAULT 1,                        -- DWH actif ou non
    date_creation DATETIME DEFAULT GETDATE()
);
GO

-- Table APP_UserDWH: Liaison entre utilisateurs et DWH accessibles
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_UserDWH' AND xtype='U')
CREATE TABLE APP_UserDWH (
    id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NOT NULL,                       -- ID de l'utilisateur
    dwh_code VARCHAR(50) NOT NULL,              -- Code du DWH
    FOREIGN KEY (user_id) REFERENCES APP_Users(id) ON DELETE CASCADE
);
GO

-- Index pour optimiser les requetes
CREATE INDEX IX_APP_UserDWH_user_id ON APP_UserDWH(user_id);
CREATE INDEX IX_APP_UserDWH_dwh_code ON APP_UserDWH(dwh_code);
CREATE INDEX IX_APP_DWH_code ON APP_DWH(code);
CREATE INDEX IX_APP_DWH_actif ON APP_DWH(actif);
GO

-- =====================================================
-- Donnees d'exemple (a adapter selon vos besoins)
-- =====================================================

-- Exemple: Creer 2 DWH
/*
INSERT INTO APP_DWH (code, nom, serveur, base_donnees, username, password, description)
VALUES
    ('DWH_CLIENT1', 'Client ABC - Production', 'kasoft.selfip.net', 'DWH_ABC', 'sa', 'SQL@2019', 'Data Warehouse du client ABC'),
    ('DWH_CLIENT2', 'Client XYZ - Production', 'localhost', 'DWH_XYZ', 'sa', 'SQL@2019', 'Data Warehouse du client XYZ');

-- Exemple: Assigner les DWH a un utilisateur (user_id = 1)
INSERT INTO APP_UserDWH (user_id, dwh_code)
VALUES
    (1, 'DWH_CLIENT1'),
    (1, 'DWH_CLIENT2');
*/

-- =====================================================
-- Vue pour voir les DWH par utilisateur
-- =====================================================
IF OBJECT_ID('VW_UserDWH', 'V') IS NOT NULL DROP VIEW VW_UserDWH;
GO

CREATE VIEW VW_UserDWH AS
SELECT
    u.id AS user_id,
    u.username,
    u.nom AS user_nom,
    u.prenom AS user_prenom,
    d.code AS dwh_code,
    d.nom AS dwh_nom,
    d.serveur,
    d.base_donnees,
    d.description,
    d.actif
FROM APP_Users u
INNER JOIN APP_UserDWH ud ON u.id = ud.user_id
INNER JOIN APP_DWH d ON ud.dwh_code = d.code
WHERE u.actif = 1 AND d.actif = 1;
GO

PRINT 'Tables DWH creees avec succes!';
