using System;
using System.Collections.Generic;
using Microsoft.Win32;
using SageETLAgent.Integration.Sage.Models;
using SageETLAgent.Logging;

namespace SageETLAgent.Integration.Sage
{
    /// <summary>
    /// Encapsule toutes les opérations de lecture/écriture dans le registre Sage.
    /// Chemin racine : HKEY_CURRENT_USER\software\Sage\{version}\{sageVersion}\Personnalisation\
    /// </summary>
    public class SageRegistryService
    {
        private readonly SyncLogger _logger = SyncLogger.Instance;
        private readonly string _appName;
        private readonly string _sageRegistryRoot;

        // Types Sage — voir WriteExternalProgram

        public SageRegistryService(string appName, string sageRegistryRoot = @"software\Sage\")
        {
            _appName = appName;
            _sageRegistryRoot = sageRegistryRoot;
        }

        // ─────────────────────────────────────────────────────────────────────
        // LECTURE
        // ─────────────────────────────────────────────────────────────────────

        /// <summary>
        /// Retourne toutes les versions Sage installées avec leur module détecté.
        /// Ignore les sous-clés qui ne correspondent à aucun module connu.
        /// </summary>
        /// <summary>
        /// Retourne toutes les combinaisons module + sous-version disponibles dans le registre.
        /// Ex : ("Gestion commerciale 100c — 12.11", path, module, "12.11")
        /// </summary>
        public List<SageVersionItem> GetInstalledVersionsWithSubVersions()
        {
            var result = new List<SageVersionItem>();

            using var sageRoot = Registry.CurrentUser.OpenSubKey(_sageRegistryRoot);
            if (sageRoot == null) return result;

            foreach (var vk in sageRoot.GetSubKeyNames())
            {
                var module = SageModuleInfo.FromRegistryKey(vk);
                if (module == null) continue;

                var versionPath = $@"{_sageRegistryRoot}{vk}\";
                using var versionKey = Registry.CurrentUser.OpenSubKey(versionPath);
                if (versionKey == null) continue;

                foreach (var sk in versionKey.GetSubKeyNames())
                {
                    if (!Version.TryParse(sk, out _)) continue;

                    using var sub = versionKey.OpenSubKey(sk);
                    if (sub == null) continue;

                    var hasPers = Array.Exists(sub.GetSubKeyNames(),
                        n => n.Equals("Personnalisation", StringComparison.OrdinalIgnoreCase));
                    if (!hasPers) continue;

                    result.Add(new SageVersionItem
                    {
                        Label       = $"{vk} — {sk}",
                        VersionPath = versionPath,
                        Module      = module.Value,
                        SubVersion  = sk
                    });
                }
            }

            // Trier par module puis sous-version décroissante
            result.Sort((a, b) =>
            {
                var c = string.Compare(a.VersionPath, b.VersionPath, StringComparison.Ordinal);
                if (c != 0) return c;
                Version.TryParse(a.SubVersion, out var va);
                Version.TryParse(b.SubVersion, out var vb);
                return vb?.CompareTo(va) ?? 0;
            });

            return result;
        }

        public List<(string VersionPath, string VersionKey, SageModule Module)> GetInstalledVersions()
        {
            var result = new List<(string, string, SageModule)>();

            using var sageRoot = Registry.CurrentUser.OpenSubKey(_sageRegistryRoot);
            if (sageRoot == null)
            {
                _logger.Log(LogLevel.WARN, LogCategory.GENERAL,
                    $"[SageRegistry] Clé Sage introuvable : {_sageRegistryRoot}");
                return result;
            }

            var versionKeys = sageRoot.GetSubKeyNames();
            foreach (var vk in versionKeys)
            {
                var module = SageModuleInfo.FromRegistryKey(vk);
                if (module == null) continue;

                result.Add(($@"{_sageRegistryRoot}{vk}\", vk, module.Value));
                _logger.Log(LogLevel.DEBUG, LogCategory.GENERAL,
                    $"[SageRegistry] Version détectée : {vk} → {module.Value}");
            }

            return result;
        }

        /// <summary>
        /// Cherche la sous-version active (ex: "12.11") sous la version principale.
        /// Retourne la sous-clé qui contient un dossier "Personnalisation",
        /// en priorité sur la version la plus élevée si plusieurs candidats existent.
        /// </summary>
        public string? GetSageSubVersion(string versionPath)
        {
            using var key = Registry.CurrentUser.OpenSubKey(versionPath);
            if (key == null) return null;

            var subKeys = key.GetSubKeyNames();
            string? best = null;
            Version? bestVersion = null;

            foreach (var sk in subKeys)
            {
                // Ignorer les clés non-numériques (ex: "Personnalisation")
                if (!Version.TryParse(sk, out var v)) continue;

                // Vérifier que cette sous-version contient bien "Personnalisation"
                using var sub = key.OpenSubKey(sk);
                if (sub == null) continue;

                var hasPersо = Array.Exists(
                    sub.GetSubKeyNames(),
                    n => n.Equals("Personnalisation", StringComparison.OrdinalIgnoreCase));

                if (!hasPersо) continue;

                // Garder la version la plus élevée
                if (bestVersion == null || v > bestVersion)
                {
                    best = sk;
                    bestVersion = v;
                }
            }

            if (best != null)
                _logger.Log(LogLevel.DEBUG, LogCategory.GENERAL,
                    $"[SageRegistry] Sous-version active détectée : {best} ({versionPath})");

            return best;
        }

        /// <summary>
        /// Cherche la sous-clé de menu Sage qui contient déjà une entrée nommée <paramref name="appName"/>.
        /// Retourne la RegistryKey ouverte en lecture/écriture, ou null si introuvable.
        /// </summary>
        public RegistryKey? FindAppMenuKey(string versionPath, string sageSubVersion)
        {
            var menusPath = $@"{versionPath}{sageSubVersion}\Personnalisation\Menus\";
            using var menus = Registry.CurrentUser.OpenSubKey(menusPath);
            if (menus == null) return null;

            foreach (var menuName in menus.GetSubKeyNames())
            {
                var menuKeyPath = $@"{menusPath}{menuName}\";
                var menuKey = Registry.CurrentUser.OpenSubKey(
                    menuKeyPath,
                    RegistryKeyPermissionCheck.ReadWriteSubTree);

                if (menuKey == null) continue;

                // Chercher une valeur dont le contenu == _appName
                foreach (var valueName in menuKey.GetValueNames())
                {
                    if (valueName.Equals("Id", StringComparison.OrdinalIgnoreCase)
                     || valueName.Equals("guid", StringComparison.OrdinalIgnoreCase))
                        continue;

                    if (menuKey.GetValue(valueName)?.ToString() == _appName)
                        return menuKey;   // Trouvée — caller est responsable du Dispose
                }

                menuKey.Dispose();
            }

            return null;
        }

        // ─────────────────────────────────────────────────────────────────────
        // NETTOYAGE
        // ─────────────────────────────────────────────────────────────────────

        /// <summary>
        /// Supprime toutes les sous-clés d'une RegistryKey (nettoyage avant réécriture).
        /// </summary>
        public void CleanSubKeys(RegistryKey key)
        {
            var subKeys = key.GetSubKeyNames();
            foreach (var sk in subKeys)
            {
                try
                {
                    key.DeleteSubKeyTree(sk, throwOnMissingSubKey: false);
                }
                catch (Exception ex)
                {
                    _logger.Log(LogLevel.WARN, LogCategory.GENERAL,
                        $"[SageRegistry] Impossible de supprimer la sous-clé '{sk}' : {ex.Message}");
                }
            }
        }

        /// <summary>
        /// Ouvre ou crée la clé "Programmes externes" pour une version Sage.
        /// Retourne null en cas d'échec d'accès.
        /// </summary>
        public RegistryKey? OpenOrCreateExternalProgramsKey(string versionPath, string sageSubVersion)
        {
            var path = $@"{versionPath}{sageSubVersion}\Personnalisation\Programmes externes\";
            return Registry.CurrentUser.OpenSubKey(path, RegistryKeyPermissionCheck.ReadWriteSubTree)
                ?? Registry.CurrentUser.CreateSubKey(path, RegistryKeyPermissionCheck.ReadWriteSubTree);
        }

        // ─────────────────────────────────────────────────────────────────────
        // ÉCRITURE
        // ─────────────────────────────────────────────────────────────────────

        /// <summary>
        /// Écrit une entrée de programme externe dans le registre Sage.
        /// Crée une sous-clé nommée par l'ID numérique de l'entrée.
        /// </summary>
        /// <returns>True si l'écriture a réussi.</returns>
        public bool WriteExternalProgram(RegistryKey parent, SageExternalProgramEntry entry)
        {
            try
            {
                using var key = parent.CreateSubKey(
                    entry.Id.ToString(),
                    RegistryKeyPermissionCheck.ReadWriteSubTree);

                if (key == null) return false;

                bool isUrlType = !string.IsNullOrEmpty(entry.Url);

                // Types Sage (REG_DWORD) — valeurs ASCII big-endian :
                //   0x756c6e6b ("ulnk") = Lien Internet
                //   0x66696c65 ("file") = Programme externe
                const uint TypeLienInternet    = 0x756c6e6b;
                const uint TypeProgrammeExterne = 0x66696c65;
                uint sageType = isUrlType ? TypeLienInternet : TypeProgrammeExterne;

                key.SetValue("Attente",           (int)entry.WaitForExit,  RegistryValueKind.DWord);
                key.SetValue("Contexte",          (int)entry.Context,      RegistryValueKind.DWord);
                key.SetValue("Fermeture société", (int)entry.CloseDossier, RegistryValueKind.DWord);
                key.SetValue("Nom",               entry.Caption,           RegistryValueKind.String);
                key.SetValue("Type",              (int)sageType,           RegistryValueKind.DWord);

                if (isUrlType)
                {
                    // Lien Internet : clé "Url" uniquement
                    key.DeleteValue("Paramètres", throwOnMissingValue: false);
                    key.DeleteValue("Path",       throwOnMissingValue: false);
                    key.SetValue("Url", entry.Url, RegistryValueKind.String);
                }
                else
                {
                    // Programme externe : clé "Path" + "Paramètres"
                    key.DeleteValue("Url", throwOnMissingValue: false);
                    key.SetValue("Paramètres", entry.Parameters,     RegistryValueKind.String);
                    key.SetValue("Path",        entry.ExecutablePath, RegistryValueKind.String);
                }

                _logger.Log(LogLevel.DEBUG, LogCategory.GENERAL,
                    $"[SageRegistry] Programme externe écrit : [{entry.Id}] {entry.Caption}");

                return true;
            }
            catch (Exception ex)
            {
                _logger.Log(LogLevel.ERROR, LogCategory.GENERAL,
                    $"[SageRegistry] Échec écriture programme '{entry.Caption}' : {ex.Message}");
                return false;
            }
        }
    }
}
