-- ======================================================================
--  Corrige le routage des bases CLIENT pointant sur une adresse loopback
--  A executer sur la base CENTRALE (OptiBoard_SaaS).
-- ======================================================================
--
--  PROBLEME
--  --------
--  APP_ClientDB.db_server contient '127.0.0.1' (ou 'localhost') pour certains
--  DWH. Le backend central resout alors la base client sur SA PROPRE boucle
--  locale au lieu du serveur ou la base existe reellement, d'ou :
--
--     Login failed for user 'sa'. (18456)
--     Cannot open database "OptiBoard_<CODE>" requested by the login. (4060)
--
--  Consequences observees (DWH ALEAFOOD) :
--    - login des utilisateurs du tenant impossible ;
--    - [MENUS] _read_menus error dwh=ALEAFOOD dans backend.log ;
--    - verify_agent() ne peut pas lire APP_ETL_Agents => tout agent ETL du
--      tenant est rejete en 401, et aucun enrolement n'est possible.
--
--  CORRECTIF
--  ---------
--  db_server = NULL  => la base client herite du serveur CENTRAL effectif.
--  C'est la convention deja utilisee par le DWH AMM, qui fonctionne.
--  (Le DWH KA utilise la variante equivalente : nom d'hote central explicite.)
--
--  Ne PAS utiliser ce script si la base client est reellement hebergee sur un
--  serveur distinct : renseigner alors le nom d'hote routable de ce serveur.
-- ======================================================================

USE OptiBoard_SaaS;
GO

-- 1) Etat avant (a conserver pour rollback)
SELECT dwh_code, db_name, db_server, db_user, actif
FROM APP_ClientDB
WHERE db_server IN ('127.0.0.1', 'localhost', '::1', '(local)');
GO

-- 2) Correctif — decommenter apres avoir verifie la liste ci-dessus.
--    Verifier d'abord que chaque base concernee existe bien sur le serveur
--    central :  SELECT name FROM sys.databases WHERE name LIKE 'OptiBoard[_]%';

-- UPDATE APP_ClientDB
--    SET db_server = NULL
--  WHERE db_server IN ('127.0.0.1', 'localhost', '::1', '(local)');
-- GO

-- Variante ciblee sur un seul tenant :
-- UPDATE APP_ClientDB SET db_server = NULL WHERE dwh_code = 'ALEAFOOD';
-- GO

-- 3) Controle apres correctif
-- SELECT dwh_code, db_name, db_server FROM APP_ClientDB ORDER BY dwh_code;
-- GO

-- ----------------------------------------------------------------------
-- ROLLBACK (remettre la valeur d'origine relevee a l'etape 1)
--   UPDATE APP_ClientDB SET db_server = '127.0.0.1' WHERE dwh_code = 'ALEAFOOD';
-- ----------------------------------------------------------------------
--
-- APRES CORRECTIF : redemarrer le backend (ou invalider le cache de
-- connexions clientes) pour que le nouveau routage soit pris en compte.
