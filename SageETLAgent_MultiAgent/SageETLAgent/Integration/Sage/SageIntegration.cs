using System;
using System.Collections.Generic;
using System.Linq;
using SageETLAgent.Integration.Sage.Models;
using SageETLAgent.Logging;
using SageETLAgent.Models;

namespace SageETLAgent.Integration.Sage
{
    /// <summary>
    /// Chef d'orchestre de l'intégration Sage.
    /// Synchronise les AgentProfiles actifs dans le registre Sage comme "Programmes externes".
    ///
    /// Flux :
    ///   1. Vérifie si Sage est ouvert (warning)
    ///   2. Détecte les versions Sage installées
    ///   3. Pour chaque version : nettoie + réécrit les programmes externes
    ///   4. Retourne un SageRegistrySyncReport
    ///
    /// Déclencheurs recommandés :
    ///   - Au démarrage de l'application (silencieux)
    ///   - Sur action manuelle (bouton paramètres)
    ///   - À la fermeture de Sage via SageProcessDetector.WatchForExit()
    /// </summary>
    public class SageIntegration
    {
        private readonly SyncLogger _logger = SyncLogger.Instance;

        private readonly SageRegistryService _registry;
        private readonly SageExternalProgramBuilder _builder;
        private readonly SageProcessDetector _detector;

        private readonly string _appName;

        /// <summary>
        /// Initialise l'intégration Sage.
        /// </summary>
        /// <param name="appName">Nom de l'application tel qu'affiché dans Sage (ex: "SageETLAgent").</param>
        /// <param name="executableName">Nom du .exe lancé depuis Sage (ex: "SageETLAgent_Desktop.exe").</param>
        /// <param name="sageRegistryRoot">Racine du registre Sage (défaut: software\Sage\).</param>
        public SageIntegration(
            string appName,
            string executableName,
            string sageRegistryRoot = @"software\Sage\")
        {
            _appName  = appName;
            _registry = new SageRegistryService(appName, sageRegistryRoot);
            _builder  = new SageExternalProgramBuilder(appName, executableName, new Random());
            _detector = new SageProcessDetector();
        }

        // ─────────────────────────────────────────────────────────────────────
        // API publique
        // ─────────────────────────────────────────────────────────────────────

        /// <summary>
        /// Retourne toutes les combinaisons module + sous-version pour la ComboBox UI.
        /// Ex : ("Gestion commerciale 100c — 12.11", path, module, "12.11")
        /// </summary>
        public List<SageVersionItem> GetInstalledVersions()
            => _registry.GetInstalledVersionsWithSubVersions();

        /// <summary>
        /// Lance la synchronisation immédiate.
        /// </summary>
        /// <param name="agents">Agents actifs à enregistrer comme programmes externes dans Sage.</param>
        /// <param name="targetVersionPath">Si renseigné, filtre sur ce chemin de version.</param>
        /// <param name="targetSubVersion">Si renseigné, force l'écriture dans cette sous-version (ex: "12.11").</param>
        /// <returns>Rapport de synchronisation.</returns>
        public SageRegistrySyncReport Sync(IEnumerable<AgentProfile> agents, string? targetVersionPath = null, string? targetSubVersion = null)
        {
            var report = new SageRegistrySyncReport { StartedAt = DateTime.Now };

            _logger.Log(LogLevel.INFO, LogCategory.GENERAL,
                $"[SageIntegration] Démarrage synchronisation registre Sage...");

            // 1. Avertissement si Sage est ouvert
            report.SageWasRunning = _detector.IsRunning();
            if (report.SageWasRunning)
            {
                _logger.Log(LogLevel.WARN, LogCategory.GENERAL,
                    "[SageIntegration] Sage est en cours d'exécution. " +
                    "La synchronisation continue mais les changements seront visibles au prochain redémarrage Sage.");
            }

            // 2. Construire les entrées depuis les agents
            var entries = _builder.Build(agents);

            if (entries.Count == 0)
                _logger.Log(LogLevel.WARN, LogCategory.GENERAL,
                    "[SageIntegration] Aucun agent à enregistrer — les anciennes entrées seront nettoyées.");

            // 3. Détecter les versions Sage installées
            var versions = _registry.GetInstalledVersions();

            if (versions.Count == 0)
            {
                _logger.Log(LogLevel.WARN, LogCategory.GENERAL,
                    "[SageIntegration] Aucune version Sage détectée dans le registre.");
                report.FinishedAt = DateTime.Now;
                return report;
            }

            // Filtrer sur la version choisie si précisée
            if (!string.IsNullOrEmpty(targetVersionPath))
                versions = versions.Where(v => v.VersionPath == targetVersionPath).ToList();

            _logger.Log(LogLevel.INFO, LogCategory.GENERAL,
                $"[SageIntegration] {versions.Count} version(s) ciblée(s).");

            // 4. Synchroniser chaque version
            foreach (var (versionPath, versionKey, module) in versions)
            {
                var moduleResult = SyncModule(versionPath, versionKey, module, entries, targetSubVersion);
                report.ModuleResults.Add(moduleResult);
            }

            report.FinishedAt = DateTime.Now;

            _logger.Log(
                report.IsSuccess ? LogLevel.INFO : LogLevel.ERROR,
                LogCategory.GENERAL,
                $"[SageIntegration] {report}");

            return report;
        }

        /// <summary>
        /// Synchronise les items de menu OptiBoard comme programmes externes Sage.
        /// </summary>
        public SageRegistrySyncReport SyncFromMenu(
            IEnumerable<OptiMenuItem> menuItems,
            string? targetVersionPath = null,
            string? targetSubVersion  = null,
            string  serverUrl         = "")
        {
            var report = new SageRegistrySyncReport { StartedAt = DateTime.Now };

            _logger.Log(LogLevel.INFO, LogCategory.GENERAL,
                "[SageIntegration] Démarrage sync menu OptiBoard → Sage...");

            report.SageWasRunning = _detector.IsRunning();
            if (report.SageWasRunning)
                _logger.Log(LogLevel.WARN, LogCategory.GENERAL,
                    "[SageIntegration] Sage ouvert — changements visibles au prochain redémarrage.");

            var entries = _builder.BuildFromMenu(menuItems, serverUrl);

            if (entries.Count == 0)
                _logger.Log(LogLevel.WARN, LogCategory.GENERAL,
                    "[SageIntegration] Aucun item de menu à enregistrer.");

            var versions = _registry.GetInstalledVersions();
            if (!string.IsNullOrEmpty(targetVersionPath))
                versions = versions.Where(v => v.VersionPath == targetVersionPath).ToList();

            foreach (var (versionPath, versionKey, module) in versions)
                report.ModuleResults.Add(SyncModule(versionPath, versionKey, module, entries, targetSubVersion));

            report.FinishedAt = DateTime.Now;
            _logger.Log(
                report.IsSuccess ? LogLevel.INFO : LogLevel.ERROR,
                LogCategory.GENERAL,
                $"[SageIntegration] {report}");

            return report;
        }

        /// <summary>
        /// Lance la synchronisation différée : attend la fermeture de Sage avant de synchroniser.
        /// Si Sage n'est pas ouvert, synchronise immédiatement.
        /// </summary>
        /// <param name="agents">Agents à enregistrer.</param>
        /// <param name="onComplete">Callback appelé avec le rapport une fois la sync terminée.</param>
        public void SyncWhenSageClosed(IEnumerable<AgentProfile> agents, Action<SageRegistrySyncReport>? onComplete = null)
        {
            _detector.WatchForExit(() =>
            {
                var report = Sync(agents);
                onComplete?.Invoke(report);
            });
        }

        // ─────────────────────────────────────────────────────────────────────
        // Privé
        // ─────────────────────────────────────────────────────────────────────

        private SageModuleSyncResult SyncModule(
            string versionPath,
            string versionKey,
            SageModule module,
            Dictionary<int, SageExternalProgramEntry> entries,
            string? forcedSubVersion = null)
        {
            var result = new SageModuleSyncResult
            {
                Module       = module,
                RegistryPath = versionPath
            };

            try
            {
                // Utiliser la sous-version forcée (choix utilisateur) ou auto-détecter
                var subVersion = !string.IsNullOrEmpty(forcedSubVersion)
                    ? forcedSubVersion
                    : _registry.GetSageSubVersion(versionPath);

                _logger.Log(LogLevel.INFO, LogCategory.GENERAL,
                    $"[SageIntegration] Synchronisation : {SageModuleInfo.ToLabel(module)} — {subVersion ?? "?"} ({versionPath})");

                if (subVersion == null)
                {
                    result.ErrorMessage = "Sous-version Sage introuvable dans le registre.";
                    _logger.Log(LogLevel.WARN, LogCategory.GENERAL,
                        $"[SageIntegration] {result.ErrorMessage} ({versionPath})");
                    return result;
                }

                // Ouvrir ou créer la clé "Programmes externes"
                using var externalPrograms = _registry.OpenOrCreateExternalProgramsKey(versionPath, subVersion);
                if (externalPrograms == null)
                {
                    result.ErrorMessage = "Impossible d'ouvrir/créer la clé 'Programmes externes'.";
                    _logger.Log(LogLevel.ERROR, LogCategory.GENERAL,
                        $"[SageIntegration] {result.ErrorMessage} ({versionPath})");
                    return result;
                }

                // Nettoyer les anciennes entrées avant réécriture
                _registry.CleanSubKeys(externalPrograms);

                // Écrire chaque programme externe
                var count = 0;
                foreach (var (_, entry) in entries)
                {
                    if (_registry.WriteExternalProgram(externalPrograms, entry))
                        count++;
                }

                result.ProgramsRegistered = count;
                result.Success            = true; // succès = opération sans exception, même si 0 programmes

                _logger.Log(LogLevel.INFO, LogCategory.GENERAL,
                    $"[SageIntegration] {SageModuleInfo.ToLabel(module)} : {count}/{entries.Count} programme(s) enregistré(s).");
            }
            catch (Exception ex)
            {
                result.Success      = false;
                result.ErrorMessage = ex.Message;
                result.Exception    = ex;

                _logger.Log(LogLevel.ERROR, LogCategory.GENERAL,
                    $"[SageIntegration] Erreur module {module} : {ex.Message}");
            }

            return result;
        }
    }
}
