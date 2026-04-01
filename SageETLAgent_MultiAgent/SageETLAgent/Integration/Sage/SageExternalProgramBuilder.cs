using System;
using System.Collections.Generic;
using System.IO;
using SageETLAgent.Integration.Sage.Models;
using SageETLAgent.Logging;
using SageETLAgent.Models;

namespace SageETLAgent.Integration.Sage
{
    /// <summary>
    /// Construit la liste des entrées "Programmes externes" Sage
    /// à partir de la liste des AgentProfiles actifs.
    ///
    /// Correspondance avec l'ancien code :
    ///   AgentProfile      ←→  BarItem (visibleInSage = 1)
    ///   AgentProfile.Name ←→  item.caption
    ///   AgentProfile.AgentId ←→  item.id (passé en paramètre)
    /// </summary>
    public class SageExternalProgramBuilder
    {
        private readonly SyncLogger _logger = SyncLogger.Instance;
        private readonly string _appName;
        private readonly string _executableName;
        private readonly Random _random;

        /// <summary>
        /// Initialise le builder.
        /// </summary>
        /// <param name="appName">Nom de l'application (ex: "SageETLAgent").</param>
        /// <param name="executableName">Nom du fichier .exe (ex: "SageETLAgent_Desktop.exe").</param>
        /// <param name="random">Instance Random partagée (pour éviter les collisions d'ID).</param>
        public SageExternalProgramBuilder(string appName, string executableName, Random random)
        {
            _appName = appName;
            _executableName = executableName;
            _random = random;
        }

        /// <summary>
        /// Construit les entrées programmes externes pour une liste d'agents.
        /// Seuls les agents actifs (IsEnabled = true, IsActive = true) sont inclus.
        /// </summary>
        /// <param name="agents">Liste des AgentProfiles à enregistrer dans Sage.</param>
        /// <returns>
        /// Dictionnaire { id_registre → SageExternalProgramEntry }.
        /// L'ID est un entier aléatoire unique (10000–99999) utilisé comme clé registre.
        /// </returns>
        public Dictionary<int, SageExternalProgramEntry> Build(IEnumerable<AgentProfile> agents)
        {
            var result = new Dictionary<int, SageExternalProgramEntry>();
            var executablePath = ResolveExecutablePath();

            foreach (var agent in agents)
            {
                if (string.IsNullOrWhiteSpace(agent.Name)) continue;

                var id = GenerateUniqueId(result);

                var entry = new SageExternalProgramEntry
                {
                    Id             = id,
                    Caption        = agent.Name,
                    SourceAgentId  = agent.AgentId,

                    // Format paramètre Sage :
                    // {AgentId} $(Dossier.InitialCatalog)
                    // La macro Sage injecte le nom de la base de données active au lancement.
                    Parameters     = $"{agent.AgentId} $(Dossier.InitialCatalog)",

                    ExecutablePath = executablePath,

                    // Valeurs fixes attendues par Sage ERP
                    SageType       = 1718185061,   // Magic value Sage "programme externe"
                    Context        = 2000,
                    WaitForExit    = 0,
                    CloseDossier   = 0
                };

                result.Add(id, entry);

                _logger.Log(LogLevel.DEBUG, LogCategory.GENERAL,
                    $"[SageBuilder] Entrée créée : [{id}] {agent.Name} → {agent.AgentId}");
            }

            _logger.Log(LogLevel.INFO, LogCategory.GENERAL,
                $"[SageBuilder] {result.Count} programme(s) externe(s) préparé(s).");

            return result;
        }

        // ─────────────────────────────────────────────────────────────────────
        // Privé
        // ─────────────────────────────────────────────────────────────────────

        // ─────────────────────────────────────────────────────────────────────
        // Surcharge : items de menu OptiBoard
        // ─────────────────────────────────────────────────────────────────────

        /// <summary>
        /// Construit les entrées depuis les items de menu OptiBoard.
        /// Chaque item feuille (type ≠ folder) devient un "Lien Internet" Sage.
        /// </summary>
        /// <param name="items">Items de menu filtrés (actif + IsLeaf).</param>
        /// <param name="serverUrl">URL de base du serveur OptiBoard (ex: http://localhost:3003).</param>
        public Dictionary<int, SageExternalProgramEntry> BuildFromMenu(IEnumerable<OptiMenuItem> items, string serverUrl = "")
        {
            var result  = new Dictionary<int, SageExternalProgramEntry>();
            var baseUrl = serverUrl.TrimEnd('/');

            foreach (var item in items)
            {
                if (!item.Actif || !item.IsLeaf) continue;
                if (string.IsNullOrWhiteSpace(item.Nom)) continue;

                var id  = GenerateUniqueId(result);
                var url = BuildItemUrl(baseUrl, item);

                result.Add(id, new SageExternalProgramEntry
                {
                    Id            = id,
                    Caption       = item.Nom,
                    SourceAgentId = item.Code,
                    Url           = url,
                    SageType      = unchecked((int)0x756c6e6b),  // Lien Internet ("ulnk")
                    Context       = 2000,
                    WaitForExit   = 0,
                    CloseDossier  = 0
                });

                _logger.Log(LogLevel.DEBUG, LogCategory.GENERAL,
                    $"[SageBuilder] Menu → [{id}] {item.Nom} → {url}");
            }

            _logger.Log(LogLevel.INFO, LogCategory.GENERAL,
                $"[SageBuilder] {result.Count} item(s) de menu préparés.");

            return result;
        }

        /// <summary>
        /// Construit l'URL OptiBoard pour un item de menu.
        /// Ex: pivot → {baseUrl}/pivot-v2/{id}
        /// </summary>
        private static string BuildItemUrl(string baseUrl, OptiMenuItem item)
        {
            // Code = URL absolue
            if (item.Code.StartsWith("http://", StringComparison.OrdinalIgnoreCase) ||
                item.Code.StartsWith("https://", StringComparison.OrdinalIgnoreCase))
                return item.Code;

            // Code = chemin relatif
            if (item.Code.StartsWith("/"))
                return baseUrl + item.Code;

            // Construire selon le type
            var typePath = item.Type.ToLowerInvariant() switch
            {
                "pivot"     => $"pivot-v2/{item.Id}",
                "gridview"  => $"gridview-v2/{item.Id}",
                "dashboard" => $"dashboard/{item.Id}",
                "page"      => $"page/{item.Id}",
                _           => $"{item.Type}/{item.Id}"
            };

            return $"{baseUrl}/{typePath}";
        }

        /// <summary>
        /// Génère un ID entier unique dans la plage 10000–99999.
        /// Boucle jusqu'à trouver un ID absent du dictionnaire existant.
        /// </summary>
        private int GenerateUniqueId(Dictionary<int, SageExternalProgramEntry> existing)
        {
            int id;
            var attempts = 0;
            const int maxAttempts = 1000;

            do
            {
                id = _random.Next(10000, 99999);
                attempts++;

                if (attempts >= maxAttempts)
                    throw new InvalidOperationException(
                        "[SageBuilder] Impossible de générer un ID unique après " +
                        $"{maxAttempts} tentatives — espace d'ID saturé.");
            }
            while (existing.ContainsKey(id));

            return id;
        }

        /// <summary>
        /// Résout le chemin absolu vers l'exécutable en utilisant AppContext.BaseDirectory.
        /// Plus stable que Directory.GetCurrentDirectory() qui peut varier selon le répertoire de travail.
        /// </summary>
        private string ResolveExecutablePath()
        {
            var path = Path.Combine(AppContext.BaseDirectory, _executableName);

            if (!File.Exists(path))
                _logger.Log(LogLevel.WARN, LogCategory.GENERAL,
                    $"[SageBuilder] Exécutable introuvable : {path}");

            return path;
        }
    }
}
