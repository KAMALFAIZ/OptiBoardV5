using System;
using System.Windows.Forms;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using SageETLAgent.Forms;
using SageETLAgent.Logging;
using SageETLAgent.Services;

namespace SageETLAgent
{
    internal static class Program
    {
        /// <summary>
        /// Point d'entree principal de l'application.
        /// Sans arguments → mode GUI (WinForms)
        /// --service → mode Service Windows (headless)
        /// </summary>
        [STAThread]
        static void Main(string[] args)
        {
            bool isServiceMode = args.Length > 0 &&
                args[0].Equals("--service", StringComparison.OrdinalIgnoreCase);

            if (isServiceMode)
                RunAsService(args);
            else
                RunAsWinForms(args);
        }

        /// <summary>
        /// Mode Service Windows : headless, utilise Generic Host + BackgroundService
        /// </summary>
        static void RunAsService(string[] args)
        {
            SyncLogger.Instance.Info(LogCategory.GENERAL,
                "=== SageETLAgent demarre en mode SERVICE ===");

            var builder = Host.CreateApplicationBuilder(args);

            builder.Services.AddWindowsService(options =>
            {
                options.ServiceName = "SageETLAgent";
            });

            builder.Services.AddHostedService<SageEtlWorker>();

            var host = builder.Build();
            host.Run();
        }

        /// <summary>
        /// Mode WinForms : interface graphique (comportement actuel inchange)
        /// </summary>
        static void RunAsWinForms(string[] args)
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.SetHighDpiMode(HighDpiMode.SystemAware);

            // Gestionnaire d'exceptions globales
            Application.ThreadException += (s, e) =>
            {
                SyncLogger.Instance.Error(
                    LogCategory.GENERAL,
                    $"Exception thread UI: {e.Exception.Message}",
                    ex: e.Exception);

                MessageBox.Show(
                    $"Erreur inattendue:\n{e.Exception.Message}",
                    "Erreur",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error
                );
            };

            AppDomain.CurrentDomain.UnhandledException += (s, e) =>
            {
                if (e.ExceptionObject is Exception ex)
                {
                    SyncLogger.Instance.Error(
                        LogCategory.GENERAL,
                        $"Exception critique non geree: {ex.Message}",
                        ex: ex);

                    MessageBox.Show(
                        $"Erreur critique:\n{ex.Message}",
                        "Erreur Critique",
                        MessageBoxButtons.OK,
                        MessageBoxIcon.Error
                    );
                }
            };

            // Lancer l'application GUI
            SyncLogger.Instance.Info(LogCategory.GENERAL,
                "=== SageETLAgent demarre en mode GUI ===");
            Application.Run(new MultiAgentForm());
        }
    }
}
