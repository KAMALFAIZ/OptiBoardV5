-- =====================================================================
-- 06_setup_linked_server.sql
-- Configuration Linked Server sur le serveur Sage → pointe vers DWH
-- =====================================================================
-- ARCHITECTURE 3 BASES :
--   OptiBoard_xxxx (config)  →  DWH_yyyy (cible)  ←  Sage 1..N (sources)
--
-- DIRECTION DU LINKED SERVER :
--   Le Linked Server est cree SUR le serveur Sage
--   et POINTE VERS le serveur DWH distant.
--   sp_Sync_Generic (sur Sage) peut ainsi ecrire dans le DWH via le LS.
--
-- EXECUTION :
--   Ce script est execute sur le SERVEUR SAGE (pas le DWH).
--   Le backend se connecte au serveur Sage pour l'executer.
--
-- PARAMETRES :
--   {LINKED_SERVER_NAME} = Nom du LS (ex: DWH_ESSAIDI26)
--   {DWH_SERVER_IP}      = IP/hostname du serveur DWH distant
--   {DWH_USER}           = Utilisateur SQL du DWH
--   {DWH_PWD}            = Mot de passe SQL du DWH
-- =====================================================================

-- ═══════════════════════════════════════════════════════════════
-- VARIABLES A PERSONNALISER
-- ═══════════════════════════════════════════════════════════════
DECLARE @LinkedServerName VARCHAR(200) = '{LINKED_SERVER_NAME}';  -- Nom du Linked Server (ex: DWH_ESSAIDI26)
DECLARE @DwhServerIP      VARCHAR(200) = '{DWH_SERVER_IP}';       -- IP ou hostname du serveur DWH
DECLARE @DwhUser          VARCHAR(100) = '{DWH_USER}';            -- Utilisateur SQL du DWH
DECLARE @DwhPassword      VARCHAR(200) = '{DWH_PWD}';             -- Mot de passe du DWH

-- ═══════════════════════════════════════════════════════════════
-- 1. SUPPRIMER LE LINKED SERVER S'IL EXISTE
-- ═══════════════════════════════════════════════════════════════
IF EXISTS (SELECT * FROM sys.servers WHERE name = @LinkedServerName)
BEGIN
    EXEC sp_dropserver @server = @LinkedServerName, @droplogins = 'droplogins';
    PRINT '-> Ancien Linked Server "' + @LinkedServerName + '" supprime';
END

-- ═══════════════════════════════════════════════════════════════
-- 2. CREER LE LINKED SERVER (sur Sage, pointe vers DWH)
-- ═══════════════════════════════════════════════════════════════
EXEC sp_addlinkedserver
    @server     = @LinkedServerName,
    @srvproduct = '',
    @provider   = 'SQLNCLI11',
    @datasrc    = @DwhServerIP;

PRINT 'V Linked Server "' + @LinkedServerName + '" cree -> ' + @DwhServerIP;

-- ═══════════════════════════════════════════════════════════════
-- 3. CONFIGURER LES IDENTIFIANTS
-- ═══════════════════════════════════════════════════════════════
EXEC sp_addlinkedsrvlogin
    @rmtsrvname  = @LinkedServerName,
    @useself     = 'FALSE',
    @rmtuser     = @DwhUser,
    @rmtpassword = @DwhPassword;

PRINT 'V Identifiants configures pour "' + @LinkedServerName + '"';

-- ═══════════════════════════════════════════════════════════════
-- 4. ACTIVER RPC (Remote Procedure Call)
-- ═══════════════════════════════════════════════════════════════
EXEC sp_serveroption @LinkedServerName, 'rpc',     'true';
EXEC sp_serveroption @LinkedServerName, 'rpc out', 'true';

PRINT 'V RPC active pour "' + @LinkedServerName + '"';

-- ═══════════════════════════════════════════════════════════════
-- 5. OPTIONS DE PERFORMANCE
-- ═══════════════════════════════════════════════════════════════
EXEC sp_serveroption @LinkedServerName, 'remote proc transaction promotion', 'false';
EXEC sp_serveroption @LinkedServerName, 'connect timeout', '30';
EXEC sp_serveroption @LinkedServerName, 'query timeout', '600';
EXEC sp_serveroption @LinkedServerName, 'collation compatible', 'false';
EXEC sp_serveroption @LinkedServerName, 'use remote collation', 'true';

PRINT 'V Options de performance configurees';

-- ═══════════════════════════════════════════════════════════════
-- 6. TEST DE CONNEXION
-- ═══════════════════════════════════════════════════════════════
BEGIN TRY
    DECLARE @TestSQL NVARCHAR(MAX) = N'SELECT TOP 1 1 FROM '
        + QUOTENAME(@LinkedServerName) + '.master.dbo.sysobjects';
    EXEC sp_executesql @TestSQL;
    PRINT 'V Test de connexion reussi pour "' + @LinkedServerName + '"';
END TRY
BEGIN CATCH
    PRINT 'X ERREUR de connexion: ' + ERROR_MESSAGE();
    PRINT '  Verifiez: IP, port 1433, firewall, identifiants SQL';
END CATCH

PRINT '';
PRINT '══════════════════════════════════════════════════════════════';
PRINT ' LINKED SERVER CONFIGURE AVEC SUCCES';
PRINT '';
PRINT ' Direction:  Serveur Sage  -->  DWH distant';
PRINT ' Nom:        ' + @LinkedServerName;
PRINT ' Cible DWH:  ' + @DwhServerIP;
PRINT ' Provider:   SQLNCLI11';
PRINT '';
PRINT ' Le serveur Sage peut maintenant acceder au DWH via :';
PRINT '   [' + @LinkedServerName + '].[DWH_xxx].dbo.[TABLE]';
PRINT '══════════════════════════════════════════════════════════════';
