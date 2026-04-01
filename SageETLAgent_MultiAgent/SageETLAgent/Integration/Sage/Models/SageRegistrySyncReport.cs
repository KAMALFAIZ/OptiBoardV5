using System;
using System.Collections.Generic;
using System.Linq;

namespace SageETLAgent.Integration.Sage.Models
{
    /// <summary>
    /// Rapport de synchronisation registre Sage.
    /// Retourné par SageIntegration.Sync() après exécution.
    /// </summary>
    public class SageRegistrySyncReport
    {
        /// <summary>
        /// Date/heure de début de la synchronisation.
        /// </summary>
        public DateTime StartedAt { get; set; } = DateTime.Now;

        /// <summary>
        /// Date/heure de fin de la synchronisation.
        /// </summary>
        public DateTime? FinishedAt { get; set; }

        /// <summary>
        /// Durée totale de la synchronisation.
        /// </summary>
        public TimeSpan Duration => FinishedAt.HasValue
            ? FinishedAt.Value - StartedAt
            : TimeSpan.Zero;

        /// <summary>
        /// True si au moins un module a été synchronisé sans erreur.
        /// </summary>
        public bool IsSuccess => ModuleResults.Any() && ModuleResults.All(r => r.Exception == null);

        /// <summary>
        /// Nombre total de programmes externes enregistrés dans le registre.
        /// </summary>
        public int TotalProgramsRegistered => ModuleResults.Sum(r => r.ProgramsRegistered);

        /// <summary>
        /// Résultats par module Sage détecté.
        /// </summary>
        public List<SageModuleSyncResult> ModuleResults { get; set; } = new();

        /// <summary>
        /// True si Sage était en cours d'exécution au moment de la sync (warning).
        /// </summary>
        public bool SageWasRunning { get; set; }

        public override string ToString() =>
            $"SageSync [{(IsSuccess ? "OK" : "FAIL")}] " +
            $"{ModuleResults.Count} module(s) | " +
            $"{TotalProgramsRegistered} programme(s) | " +
            $"{Duration.TotalSeconds:F1}s";
    }

    /// <summary>
    /// Résultat de synchronisation pour un module Sage (une version installée).
    /// </summary>
    public class SageModuleSyncResult
    {
        /// <summary>
        /// Module Sage concerné (CIAL, CPTA, etc.).
        /// </summary>
        public SageModule Module { get; set; }

        /// <summary>
        /// Chemin de la clé registre de cette version Sage.
        /// Ex : software\Sage\Gestion commerciale 100\
        /// </summary>
        public string RegistryPath { get; set; } = "";

        /// <summary>
        /// True si la synchronisation de ce module a réussi.
        /// </summary>
        public bool Success { get; set; }

        /// <summary>
        /// Nombre de programmes externes enregistrés pour ce module.
        /// </summary>
        public int ProgramsRegistered { get; set; }

        /// <summary>
        /// Message d'erreur en cas d'échec (null si succès).
        /// </summary>
        public string? ErrorMessage { get; set; }

        /// <summary>
        /// Exception capturée en cas d'échec (null si succès).
        /// </summary>
        public Exception? Exception { get; set; }

        public override string ToString() =>
            $"{SageModuleInfo.ToLabel(Module)} — " +
            (Success
                ? $"{ProgramsRegistered} programme(s) enregistré(s)"
                : $"ERREUR: {ErrorMessage}");
    }
}
