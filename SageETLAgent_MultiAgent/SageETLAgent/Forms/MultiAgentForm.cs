using System;
using System.Collections.Generic;
using System.Data.SqlClient;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using System.Windows.Forms;
using SageETLAgent.Integration.Sage;
using SageETLAgent.Logging;
using SageETLAgent.Models;
using SageETLAgent.Services;

namespace SageETLAgent.Forms
{
    public partial class MultiAgentForm : Form
    {
        private readonly ParallelSyncManager _syncManager;
        private List<AgentProfile> _agents = new();
        private string _serverUrl = "http://kasoft.selfip.net:50231";
        private string _dwhCode = "";

        // ── Theme Colors (Professional — tons clairs) ──
        private static readonly Color ThemePrimary      = Color.FromArgb(96, 165, 250);   // #60A5FA blue-400
        private static readonly Color ThemePrimaryDark   = Color.FromArgb(59, 130, 246);  // #3B82F6 blue-500
        private static readonly Color ThemePrimaryDarker = Color.FromArgb(30, 58, 138);   // #1E3A8A blue-900
        private static readonly Color ThemePrimaryLight  = Color.FromArgb(219, 234, 254); // #DBEAFE blue-100
        private static readonly Color ThemePrimary50     = Color.FromArgb(239, 246, 255); // #EFF6FF blue-50
        private static readonly Color ThemeSuccess       = Color.FromArgb(74, 222, 128);  // #4ADE80 green-400
        private static readonly Color ThemeSuccessLight  = Color.FromArgb(220, 252, 231); // #DCFCE7 green-100
        private static readonly Color ThemeDanger        = Color.FromArgb(248, 113, 113); // #F87171 red-400
        private static readonly Color ThemeDangerLight   = Color.FromArgb(254, 226, 226); // #FEE2E2 red-100
        private static readonly Color ThemeWarning       = Color.FromArgb(251, 146, 60);  // #FB923C orange-400
        private static readonly Color ThemeWarningLight  = Color.FromArgb(255, 237, 213); // #FFEDD5 orange-100
        private static readonly Color ThemeTextMuted     = Color.FromArgb(148, 163, 184); // #94A3B8 slate-400
        private static readonly Color ThemeTextDark      = Color.FromArgb(15, 23, 42);    // #0F172A slate-900
        private static readonly Color ThemeBg            = Color.FromArgb(248, 250, 252); // #F8FAFC slate-50
        private static readonly Color ThemeBgCard        = Color.White;
        private static readonly Color ThemeBorder        = Color.FromArgb(226, 232, 240); // #E2E8F0 slate-200
        private static readonly Color ThemeBorderLight   = Color.FromArgb(241, 245, 249); // #F1F5F9 slate-100

        // Services mode continu
        private readonly Dictionary<string, ContinuousSyncService> _continuousServices = new();

        // Controls
        private TextBox txtServerUrl = null!;
        private Button btnTestConnection = null!;
        private Button btnLoadAgents = null!;
        private DataGridView dgvAgents = null!;
        private Button btnSyncSelected = null!;
        private Button btnSyncAll = null!;
        private Button btnCancel = null!;
        private RichTextBox rtbLogs = null!;
        private Dictionary<string, ProgressBar> _progressBars = new();
        private Dictionary<string, Label> _progressLabels = new();
        private Panel pnlProgress = null!;
        private StatusStrip statusStrip = null!;
        private ToolStripStatusLabel lblStatus = null!;

        // Pointage
        private Button btnPointage = null!;

        // Sage Integration
        private Button btnSageSync = null!;
        private ComboBox cmbSageVersion = null!;

        // System Tray
        private NotifyIcon _trayIcon = null!;
        private ContextMenuStrip _trayMenu = null!;
        private bool _forceClose = false;

        // Mode continu controls
        private TextBox txtDwhCode = null!;
        private Button btnStartContinuous = null!;
        private Button btnStopContinuous = null!;
        private Button btnPause = null!;
        private Button btnResume = null!;
        private ComboBox cmbSyncMode = null!;
        private Label lblContinuousStatus = null!;
        private System.Windows.Forms.Timer heartbeatTimer = null!;
        private ToolTip _toolTip = null!;

        public MultiAgentForm()
        {
            LoadAppSettings();
            InitializeComponent();
            _syncManager = new ParallelSyncManager(_serverUrl);
            SetupEventHandlers();
            SetupHeartbeatTimer();
            LoadSageVersionsCombo();
        }

        private void LoadAppSettings()
        {
            try
            {
                var configPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "appsettings.json");
                if (File.Exists(configPath))
                {
                    var json = File.ReadAllText(configPath);
                    var root = Newtonsoft.Json.JsonConvert.DeserializeObject<SageETLAgent.Services.ServiceConfigRoot>(json);
                    if (root?.SageEtl != null)
                    {
                        if (!string.IsNullOrWhiteSpace(root.SageEtl.ServerUrl))
                            _serverUrl = root.SageEtl.ServerUrl;
                        _dwhCode = root.SageEtl.DwhCode ?? "";
                    }
                }
            }
            catch { /* Utilise les valeurs par defaut */ }
        }

        // ── Helper: create a styled button ──
        private Button CreateStyledButton(string text, int width, int height, Color bgColor, Color fgColor, bool isOutline = false)
        {
            var btn = new Button
            {
                Text = text,
                Width = width,
                Height = height,
                FlatStyle = FlatStyle.Flat,
                Cursor = Cursors.Hand,
                Font = new Font("Segoe UI", 8.5F, FontStyle.Regular),
            };

            if (isOutline)
            {
                btn.BackColor = ThemeBgCard;
                btn.ForeColor = bgColor;
                btn.FlatAppearance.BorderColor = ThemeBorder;
                btn.FlatAppearance.BorderSize = 1;
                btn.FlatAppearance.MouseOverBackColor = Color.FromArgb(30, bgColor);
            }
            else
            {
                btn.BackColor = bgColor;
                btn.ForeColor = fgColor;
                btn.FlatAppearance.BorderSize = 0;
                btn.FlatAppearance.MouseOverBackColor = ControlPaint.Dark(bgColor, 0.08f);
                btn.FlatAppearance.MouseDownBackColor = ControlPaint.Dark(bgColor, 0.15f);
            }
            return btn;
        }

        // ── Helper: icon-only button with tooltip ──
        private Button CreateIconButton(string icon, string tooltip, int size, Color bgColor, Color fgColor, bool isOutline = false)
        {
            var btn = CreateStyledButton(icon, size, size, bgColor, fgColor, isOutline);
            btn.Font = new Font("Segoe UI", 10F, FontStyle.Regular);
            btn.Padding = Padding.Empty;
            btn.TextAlign = ContentAlignment.MiddleCenter;
            _toolTip.SetToolTip(btn, tooltip);
            return btn;
        }

        // ── Helper: GroupBox with rounded border ──
        private GroupBox CreateSection(string title)
        {
            var grp = new GroupBox
            {
                Dock = DockStyle.Fill,
                Text = title,
                Font = new Font("Segoe UI", 8.5F, FontStyle.Bold),
                ForeColor = ThemePrimaryDarker,
                BackColor = ThemeBgCard,
                Margin = new Padding(0, 2, 0, 2),
                Padding = new Padding(6, 4, 6, 4)
            };
            return grp;
        }

        private static GraphicsPath CreateRoundedRect(Rectangle bounds, int radius)
        {
            var path = new GraphicsPath();
            var d = radius * 2;
            path.AddArc(bounds.X, bounds.Y, d, d, 180, 90);
            path.AddArc(bounds.Right - d, bounds.Y, d, d, 270, 90);
            path.AddArc(bounds.Right - d, bounds.Bottom - d, d, d, 0, 90);
            path.AddArc(bounds.X, bounds.Bottom - d, d, d, 90, 90);
            path.CloseFigure();
            return path;
        }

        private void InitializeComponent()
        {
            _toolTip = new ToolTip { InitialDelay = 300, ReshowDelay = 200, AutoPopDelay = 3000 };

            this.Text = "Agent ETL Sage - Multi-Agent v2.0";
            this.Size = new Size(1300, 900);
            this.StartPosition = FormStartPosition.CenterScreen;
            this.Font = new Font("Segoe UI", 9F);
            this.BackColor = ThemeBg;

            var mainPanel = new TableLayoutPanel
            {
                Dock = DockStyle.Fill,
                RowCount = 4,
                ColumnCount = 1,
                Padding = new Padding(8, 8, 8, 4),
                BackColor = ThemeBg
            };
            mainPanel.RowStyles.Add(new RowStyle(SizeType.Absolute, 100));
            mainPanel.RowStyles.Add(new RowStyle(SizeType.Percent, 35));
            mainPanel.RowStyles.Add(new RowStyle(SizeType.Absolute, 100));
            mainPanel.RowStyles.Add(new RowStyle(SizeType.Percent, 65));

            // ═══ Row 0: Configuration ═══
            var configGroup = CreateSection("\u2699  Configuration");
            var configInner = new TableLayoutPanel
            {
                Dock = DockStyle.Fill,
                RowCount = 2,
                ColumnCount = 1,
                Padding = new Padding(4, 2, 4, 0),
                BackColor = Color.Transparent
            };
            configInner.RowStyles.Add(new RowStyle(SizeType.Percent, 50));
            configInner.RowStyles.Add(new RowStyle(SizeType.Percent, 50));

            // Ligne 1: Serveur
            var serverPanel = new FlowLayoutPanel { Dock = DockStyle.Fill, FlowDirection = FlowDirection.LeftToRight, WrapContents = false, BackColor = Color.Transparent };
            serverPanel.Controls.Add(new Label { Text = "Serveur", AutoSize = true, Margin = new Padding(0, 5, 6, 0), Font = new Font("Segoe UI", 8.5F), ForeColor = ThemeTextMuted });
            txtServerUrl = new TextBox { Text = _serverUrl, Width = 280, Font = new Font("Segoe UI", 8.5F), BorderStyle = BorderStyle.FixedSingle };
            serverPanel.Controls.Add(txtServerUrl);
            btnTestConnection = CreateIconButton("\u26A1", "Tester la connexion", 28, ThemePrimary, Color.White, true);
            btnTestConnection.Margin = new Padding(8, 1, 3, 0);
            serverPanel.Controls.Add(btnTestConnection);
            btnLoadAgents = CreateIconButton("\u21BB", "Charger les agents", 28, ThemePrimary, Color.White);
            btnLoadAgents.Margin = new Padding(3, 1, 0, 0);
            serverPanel.Controls.Add(btnLoadAgents);
            serverPanel.Controls.Add(new Label { Text = "  DWH Code", AutoSize = true, Margin = new Padding(16, 5, 6, 0), Font = new Font("Segoe UI", 8.5F), ForeColor = ThemeTextMuted });
            txtDwhCode = new TextBox { Text = _dwhCode, Width = 120, Font = new Font("Segoe UI", 8.5F), BorderStyle = BorderStyle.FixedSingle };
            _toolTip.SetToolTip(txtDwhCode, "Code client DWH (ex: ESSA). Requis pour lire les agents avec credentials Sage.");
            serverPanel.Controls.Add(txtDwhCode);
            configInner.Controls.Add(serverPanel, 0, 0);

            // Ligne 2: Mode
            var modePanel = new FlowLayoutPanel { Dock = DockStyle.Fill, FlowDirection = FlowDirection.LeftToRight, WrapContents = false, BackColor = Color.Transparent };
            modePanel.Controls.Add(new Label { Text = "Mode", AutoSize = true, Margin = new Padding(0, 5, 6, 0), Font = new Font("Segoe UI", 8.5F), ForeColor = ThemeTextMuted });
            cmbSyncMode = new ComboBox { Width = 95, DropDownStyle = ComboBoxStyle.DropDownList, Margin = new Padding(0, 1, 6, 0), Font = new Font("Segoe UI", 8.5F) };
            cmbSyncMode.Items.AddRange(new[] { "Manuel", "Continu" });
            cmbSyncMode.SelectedIndex = 0;
            modePanel.Controls.Add(cmbSyncMode);
            btnStartContinuous = CreateIconButton("\u25B6", "Demarrer le mode continu", 28, ThemeSuccess, Color.White);
            btnStartContinuous.Margin = new Padding(6, 1, 3, 0); btnStartContinuous.Enabled = false;
            modePanel.Controls.Add(btnStartContinuous);
            btnStopContinuous = CreateIconButton("\u25A0", "Arreter le mode continu", 28, ThemeDanger, Color.White);
            btnStopContinuous.Margin = new Padding(3, 1, 3, 0); btnStopContinuous.Enabled = false;
            modePanel.Controls.Add(btnStopContinuous);
            btnPause = CreateIconButton("\u23F8", "Mettre en pause", 28, ThemeTextMuted, Color.White, true);
            btnPause.Margin = new Padding(6, 1, 3, 0); btnPause.Enabled = false;
            modePanel.Controls.Add(btnPause);
            btnResume = CreateIconButton("\u25B6", "Reprendre", 28, ThemeTextMuted, Color.White, true);
            btnResume.Margin = new Padding(3, 1, 6, 0); btnResume.Enabled = false;
            modePanel.Controls.Add(btnResume);
            lblContinuousStatus = new Label { Text = "", AutoSize = true, Margin = new Padding(10, 5, 0, 0), ForeColor = ThemeTextMuted, Font = new Font("Segoe UI", 8F) };
            modePanel.Controls.Add(lblContinuousStatus);

            modePanel.Controls.Add(new Label { Text = "  Sage", AutoSize = true, Margin = new Padding(16, 5, 4, 0), Font = new Font("Segoe UI", 8.5F), ForeColor = ThemeTextMuted });
            cmbSageVersion = new ComboBox { Width = 200, DropDownStyle = ComboBoxStyle.DropDownList, Margin = new Padding(0, 1, 0, 0), Font = new Font("Segoe UI", 8.5F) };
            cmbSageVersion.Items.Add("— Toutes les versions —");
            cmbSageVersion.SelectedIndex = 0;
            _toolTip.SetToolTip(cmbSageVersion, "Choisir la version Sage cible pour l'intégration registre");
            modePanel.Controls.Add(cmbSageVersion);

            configInner.Controls.Add(modePanel, 0, 1);
            configGroup.Controls.Add(configInner);
            mainPanel.Controls.Add(configGroup, 0, 0);

            // ═══ Row 1: Agents ═══
            var agentsGroup = CreateSection("\U0001F4CB  Agents Configures");

            dgvAgents = new DataGridView
            {
                Dock = DockStyle.Fill,
                AutoGenerateColumns = false,
                AllowUserToAddRows = false,
                AllowUserToDeleteRows = false,
                SelectionMode = DataGridViewSelectionMode.FullRowSelect,
                MultiSelect = true,
                ReadOnly = false,
                RowHeadersVisible = false,
                BackgroundColor = ThemePrimary50,
                GridColor = ThemePrimaryLight,
                BorderStyle = BorderStyle.None,
                CellBorderStyle = DataGridViewCellBorderStyle.Single,
                ColumnHeadersBorderStyle = DataGridViewHeaderBorderStyle.Single,
                EnableHeadersVisualStyles = false,
                ColumnHeadersHeight = 30,
                RowTemplate = { Height = 28 }
            };
            dgvAgents.ColumnHeadersDefaultCellStyle = new DataGridViewCellStyle
            {
                BackColor = ThemePrimaryLight,
                ForeColor = ThemePrimaryDark,
                Font = new Font("Segoe UI", 8F, FontStyle.Bold),
                Alignment = DataGridViewContentAlignment.MiddleLeft,
                Padding = new Padding(4, 0, 4, 0)
            };
            dgvAgents.DefaultCellStyle = new DataGridViewCellStyle
            {
                Font = new Font("Segoe UI", 8.5F),
                ForeColor = ThemeTextDark,
                BackColor = ThemeBgCard,
                SelectionBackColor = ThemePrimaryLight,
                SelectionForeColor = ThemePrimaryDark,
                Padding = new Padding(3, 0, 3, 0)
            };
            dgvAgents.AlternatingRowsDefaultCellStyle = new DataGridViewCellStyle
            {
                BackColor = Color.FromArgb(250, 251, 254),
                SelectionBackColor = ThemePrimaryLight,
                SelectionForeColor = ThemePrimaryDark
            };

            dgvAgents.Columns.Add(new DataGridViewCheckBoxColumn { Name = "colSelected", HeaderText = "", Width = 30, DataPropertyName = "IsSelected" });
            dgvAgents.Columns.Add(new DataGridViewTextBoxColumn { Name = "colName", HeaderText = "Nom Agent", Width = 130, DataPropertyName = "Name", ReadOnly = true });
            dgvAgents.Columns.Add(new DataGridViewTextBoxColumn { Name = "colDwhCode", HeaderText = "DWH", Width = 70, DataPropertyName = "DwhCode", ReadOnly = true });
            dgvAgents.Columns.Add(new DataGridViewTextBoxColumn { Name = "colSageDb", HeaderText = "Base Sage", Width = 130, DataPropertyName = "SageDatabase", ReadOnly = true });
            dgvAgents.Columns.Add(new DataGridViewTextBoxColumn { Name = "colStatus", HeaderText = "Statut", Width = 70, DataPropertyName = "Status", ReadOnly = true });
            dgvAgents.Columns.Add(new DataGridViewTextBoxColumn { Name = "colLastSync", HeaderText = "Derniere Sync", Width = 120, DataPropertyName = "LastSync", ReadOnly = true });
            dgvAgents.Columns.Add(new DataGridViewTextBoxColumn { Name = "colTotalRows", HeaderText = "Total Lignes", Width = 80, DataPropertyName = "TotalRowsSynced", ReadOnly = true });
            dgvAgents.Columns.Add(new DataGridViewButtonColumn { Name = "colSync", HeaderText = "", Text = "\u21C4", UseColumnTextForButtonValue = true, Width = 32, FlatStyle = FlatStyle.Flat });
            dgvAgents.Columns.Add(new DataGridViewButtonColumn { Name = "colContinuous", HeaderText = "", Text = "\u221E", UseColumnTextForButtonValue = true, Width = 32, FlatStyle = FlatStyle.Flat });
            dgvAgents.Columns.Add(new DataGridViewButtonColumn { Name = "colTestConn", HeaderText = "", Text = "\u26A1", UseColumnTextForButtonValue = true, Width = 32, FlatStyle = FlatStyle.Flat });
            dgvAgents.Columns.Add(new DataGridViewButtonColumn { Name = "colConfig", HeaderText = "", Text = "\u2699", UseColumnTextForButtonValue = true, Width = 32, FlatStyle = FlatStyle.Flat });
            dgvAgents.Columns.Add(new DataGridViewButtonColumn { Name = "colDelete", HeaderText = "", Text = "\u2716", UseColumnTextForButtonValue = true, Width = 32, FlatStyle = FlatStyle.Flat });

            dgvAgents.CellPainting += DgvAgents_CellPainting;
            dgvAgents.ShowCellToolTips = true;
            dgvAgents.CellMouseEnter += DgvAgents_CellMouseEnter;
            agentsGroup.Controls.Add(dgvAgents);
            mainPanel.Controls.Add(agentsGroup, 0, 1);

            // ═══ Row 2: Progression ═══
            var progressGroup = CreateSection("\u23F3  Progression");
            pnlProgress = new Panel { Dock = DockStyle.Fill, AutoScroll = true, Padding = new Padding(4), BackColor = Color.Transparent };
            progressGroup.Controls.Add(pnlProgress);
            mainPanel.Controls.Add(progressGroup, 0, 2);

            // ═══ Row 3: Logs + Buttons ═══
            var logsLayout = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 2, BackColor = Color.Transparent };
            logsLayout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
            logsLayout.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 55));

            var logsGroup = CreateSection("\U0001F4DD  Logs");
            rtbLogs = new RichTextBox
            {
                Dock = DockStyle.Fill,
                ReadOnly = true,
                Font = new Font("Consolas", 9F),
                BackColor = Color.FromArgb(24, 24, 27),
                ForeColor = Color.FromArgb(212, 212, 216),
                BorderStyle = BorderStyle.None
            };
            logsGroup.Controls.Add(rtbLogs);
            logsLayout.Controls.Add(logsGroup, 0, 0);

            SyncLogger.Instance.AttachRichTextBox(rtbLogs);

            // Buttons panel — icon-only with tooltips
            var buttonsPanel = new FlowLayoutPanel { Dock = DockStyle.Fill, FlowDirection = FlowDirection.TopDown, Padding = new Padding(6, 2, 0, 0), BackColor = Color.Transparent };

            btnSyncSelected = CreateIconButton("\u21C4", "Synchroniser la selection", 36, ThemePrimary, Color.White);
            btnSyncSelected.Margin = new Padding(0, 4, 0, 4);
            buttonsPanel.Controls.Add(btnSyncSelected);

            btnSyncAll = CreateIconButton("\u21C4", "Synchroniser TOUS les agents", 36, ThemeSuccess, Color.White);
            btnSyncAll.Margin = new Padding(0, 4, 0, 4);
            buttonsPanel.Controls.Add(btnSyncAll);

            btnCancel = CreateIconButton("\u2716", "Annuler la synchronisation", 36, ThemeDanger, Color.White);
            btnCancel.Margin = new Padding(0, 4, 0, 4);
            btnCancel.Enabled = false;
            buttonsPanel.Controls.Add(btnCancel);

            btnPointage = CreateIconButton("\u2714", "Lancer le pointage", 36, ThemeWarning, Color.White);
            btnPointage.Margin = new Padding(0, 12, 0, 4);
            buttonsPanel.Controls.Add(btnPointage);

            var btnClearLogs = CreateIconButton("\u2702", "Effacer les logs", 36, ThemeTextMuted, Color.White, true);
            btnClearLogs.Margin = new Padding(0, 12, 0, 4);
            btnClearLogs.Click += (s, e) => rtbLogs.Clear();
            buttonsPanel.Controls.Add(btnClearLogs);

            var btnScheduleTask = CreateIconButton("\uD83D\uDD52", "Tache planifiee au demarrage", 36, ThemePrimaryDark, Color.White);
            btnScheduleTask.Margin = new Padding(0, 4, 0, 4);
            btnScheduleTask.Click += (s, e) => ConfigureScheduledTask();
            buttonsPanel.Controls.Add(btnScheduleTask);

            btnSageSync = CreateIconButton("\uD83D\uDD17", "Integrer dans Sage (registre)", 36, Color.FromArgb(34, 197, 94), Color.White);
            btnSageSync.Margin = new Padding(0, 4, 0, 4);
            buttonsPanel.Controls.Add(btnSageSync);

            logsLayout.Controls.Add(buttonsPanel, 1, 0);
            mainPanel.Controls.Add(logsLayout, 0, 3);

            // Status bar
            statusStrip = new StatusStrip { BackColor = ThemeBgCard, SizingGrip = false };
            lblStatus = new ToolStripStatusLabel("Pret") { ForeColor = ThemeTextMuted, Font = new Font("Segoe UI", 8F) };
            statusStrip.Items.Add(lblStatus);

            this.Controls.Add(mainPanel);
            this.Controls.Add(statusStrip);

            // ═══ System Tray ═══
            _trayMenu = new ContextMenuStrip();
            _trayMenu.Items.Add("Afficher", null, (s, e) => RestoreFromTray());
            _trayMenu.Items.Add(new ToolStripSeparator());
            _trayMenu.Items.Add("Pointage", null, async (s, e) => { RestoreFromTray(); await RunPointageAsync(); });
            _trayMenu.Items.Add("Pause / Reprendre", null, (s, e) => TogglePauseFromTray());
            _trayMenu.Items.Add(new ToolStripSeparator());
            _trayMenu.Items.Add("Quitter", null, (s, e) => { _forceClose = true; Application.Exit(); });

            _trayIcon = new NotifyIcon
            {
                Icon = CreateTrayIcon(ThemeTextMuted, "S"),
                Text = "SageETL Agent - Pret",
                ContextMenuStrip = _trayMenu,
                Visible = true
            };
            _trayIcon.DoubleClick += (s, e) => RestoreFromTray();
        }

        // ── DataGridView button cell painting ──
        private void DgvAgents_CellPainting(object? sender, DataGridViewCellPaintingEventArgs e)
        {
            if (e.RowIndex < 0 || e.Graphics == null) return;

            var colName = dgvAgents.Columns[e.ColumnIndex].Name;
            Color btnBg;
            string icon;

            switch (colName)
            {
                case "colSync":       btnBg = ThemePrimary;     icon = "\u21C4"; break;  // ⇄
                case "colContinuous": btnBg = ThemePrimaryDark; icon = "\u221E"; break;  // ∞
                case "colTestConn":   btnBg = ThemeWarning;     icon = "\u26A1"; break;  // ⚡
                case "colConfig":     btnBg = ThemeTextMuted;   icon = "\u2699"; break;  // ⚙
                case "colDelete":     btnBg = ThemeDanger;      icon = "\u2716"; break;  // ✖
                default: return;
            }

            e.Handled = true;
            e.PaintBackground(e.ClipBounds, true);

            var cellRect = e.CellBounds;
            var btnRect = new Rectangle(cellRect.X + 3, cellRect.Y + 3, cellRect.Width - 6, cellRect.Height - 6);

            var g = e.Graphics; // DO NOT dispose - owned by DataGridView
            g.SmoothingMode = SmoothingMode.AntiAlias;
            using var path = CreateRoundedRect(btnRect, 6);
            using var fillBrush = new SolidBrush(btnBg);
            g.FillPath(fillBrush, path);

            using var font = new Font("Segoe UI", 10F);
            using var textBrush = new SolidBrush(Color.White);
            var textSize = g.MeasureString(icon, font);
            g.DrawString(icon, font, textBrush,
                btnRect.X + (btnRect.Width - textSize.Width) / 2,
                btnRect.Y + (btnRect.Height - textSize.Height) / 2);
        }

        // ── Tooltip on button columns ──
        private void DgvAgents_CellMouseEnter(object? sender, DataGridViewCellEventArgs e)
        {
            if (e.RowIndex < 0 || e.ColumnIndex < 0) return;
            var colName = dgvAgents.Columns[e.ColumnIndex].Name;
            dgvAgents.Rows[e.RowIndex].Cells[e.ColumnIndex].ToolTipText = colName switch
            {
                "colSync"       => "Synchroniser",
                "colContinuous" => "Mode continu",
                "colTestConn"   => "Tester les connexions",
                "colConfig"     => "Configuration",
                "colDelete"     => "Supprimer",
                _ => ""
            };
        }

        private void SetupEventHandlers()
        {
            btnTestConnection.Click += async (s, e) => await TestConnectionAsync();
            btnLoadAgents.Click += async (s, e) => await LoadAgentsAsync();
            btnSyncSelected.Click += async (s, e) => await SyncSelectedAsync();
            btnSyncAll.Click += async (s, e) => await SyncAllAsync();
            btnCancel.Click += (s, e) => _syncManager.Cancel();
            btnPointage.Click += async (s, e) => await RunPointageAsync();
            btnSageSync.Click += async (s, e) => await RunSageSyncAsync();

            // Mode continu
            cmbSyncMode.SelectedIndexChanged += (s, e) => UpdateModeUI();
            btnStartContinuous.Click += async (s, e) => await StartContinuousModeAsync();
            btnStopContinuous.Click += async (s, e) => await StopContinuousModeAsync();
            btnPause.Click += (s, e) => PauseContinuousMode();
            btnResume.Click += (s, e) => ResumeContinuousMode();

            dgvAgents.CellClick += DgvAgents_CellClick;
            dgvAgents.CellValueChanged += DgvAgents_CellValueChanged;

            // LogMessage n'est plus necessaire: les services logguent directement via SyncLogger
            _syncManager.ProgressChanged += SyncManager_ProgressChanged;
            _syncManager.AgentCompleted += SyncManager_AgentCompleted;
            _syncManager.AllCompleted += SyncManager_AllCompleted;

            this.Load += async (s, e) => await LoadAgentsAsync();
            this.FormClosing += OnFormClosing_Handler;
        }

        private void SetupHeartbeatTimer()
        {
            heartbeatTimer = new System.Windows.Forms.Timer
            {
                Interval = 1000 // 1 seconde
            };
            heartbeatTimer.Tick += HeartbeatTimer_Tick;
        }

        private void HeartbeatTimer_Tick(object? sender, EventArgs e)
        {
            UpdateContinuousStatusUI();
            UpdateTrayIcon();
        }

        private void UpdateModeUI()
        {
            bool isContinuousMode = cmbSyncMode.SelectedIndex == 1;

            // Manuel mode buttons
            btnSyncSelected.Enabled = !isContinuousMode;
            btnSyncAll.Enabled = !isContinuousMode;

            // Continu mode buttons
            btnStartContinuous.Enabled = isContinuousMode && _agents.Any(a => a.IsSelected);
            btnStopContinuous.Enabled = false;
            btnPause.Enabled = false;
            btnResume.Enabled = false;
        }

        #region System Tray

        private Icon CreateTrayIcon(Color color, string letter)
        {
            using var bmp = new Bitmap(16, 16);
            using var g = Graphics.FromImage(bmp);
            g.SmoothingMode = System.Drawing.Drawing2D.SmoothingMode.AntiAlias;
            using var brush = new SolidBrush(color);
            g.FillEllipse(brush, 1, 1, 14, 14);
            using var font = new Font("Segoe UI", 8f, FontStyle.Bold);
            var size = g.MeasureString(letter, font);
            g.DrawString(letter, font, Brushes.White,
                (16 - size.Width) / 2, (16 - size.Height) / 2);
            return Icon.FromHandle(bmp.GetHicon());
        }

        protected override void OnResize(EventArgs e)
        {
            base.OnResize(e);
            if (WindowState == FormWindowState.Minimized)
            {
                Hide();
                ShowInTaskbar = false;
            }
        }

        private void RestoreFromTray()
        {
            Show();
            ShowInTaskbar = true;
            WindowState = FormWindowState.Normal;
            Activate();
        }

        private void TogglePauseFromTray()
        {
            if (!_continuousServices.Any())
                return;

            bool anyPaused = _continuousServices.Values.Any(s => s.IsPaused);
            if (anyPaused)
                ResumeContinuousMode();
            else
                PauseContinuousMode();
        }

        private void UpdateTrayIcon()
        {
            if (_trayIcon == null) return;

            var activeCount = _continuousServices.Values.Count(s => s.IsRunning && !s.IsPaused);
            var pausedCount = _continuousServices.Values.Count(s => s.IsPaused);

            var oldIcon = _trayIcon.Icon;

            if (activeCount > 0 && pausedCount == 0)
            {
                _trayIcon.Icon = CreateTrayIcon(ThemeSuccess, "S");
                _trayIcon.Text = $"SageETL - Actif ({activeCount} service(s))";
            }
            else if (pausedCount > 0)
            {
                _trayIcon.Icon = CreateTrayIcon(ThemeWarning, "S");
                _trayIcon.Text = $"SageETL - Pause ({pausedCount}/{activeCount + pausedCount})";
            }
            else
            {
                _trayIcon.Icon = CreateTrayIcon(ThemeTextMuted, "S");
                _trayIcon.Text = "SageETL Agent - Pret";
            }

            if (oldIcon != null)
            {
                DestroyIcon(oldIcon.Handle);
            }
        }

        [System.Runtime.InteropServices.DllImport("user32.dll", CharSet = System.Runtime.InteropServices.CharSet.Auto)]
        private static extern bool DestroyIcon(IntPtr handle);

        #endregion

        #region Pointage

        private async Task RunPointageAsync()
        {
            var selected = _agents.Where(a => a.IsSelected).ToList();
            if (!selected.Any())
            {
                MessageBox.Show("Selectionnez au moins un agent", "Pointage", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }

            btnPointage.Enabled = false;
            lblStatus.Text = "Pointage en cours...";

            try
            {
                _serverUrl = txtServerUrl.Text.Trim();
                using var apiClient = new ApiClient(_serverUrl);
                var reconciliationService = new ReconciliationService();

                reconciliationService.ProgressChanged += (s, msg) =>
                {
                    if (InvokeRequired)
                        BeginInvoke(() => lblStatus.Text = msg);
                    else
                        lblStatus.Text = msg;
                };

                foreach (var agent in selected)
                {
                    AppendLog($"=== POINTAGE {agent.Name} ===");

                    // Charger les tables de l'agent
                    var tables = await apiClient.GetTablesAsync(agent.AgentId, agent.ApiKey);
                    if (!tables.Any())
                    {
                        AppendLog($"Aucune table configuree pour {agent.Name}");
                        continue;
                    }

                    var report = await reconciliationService.RunReconciliationAsync(agent, tables);

                    // Afficher le dialog de resultats
                    var resultForm = new PointageResultForm(report);
                    resultForm.ShowDialog(this);
                }
            }
            catch (Exception ex)
            {
                AppendLog($"ERREUR pointage: {ex.Message}");
                MessageBox.Show($"Erreur: {ex.Message}", "Erreur Pointage", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
            finally
            {
                btnPointage.Enabled = true;
                lblStatus.Text = "Pret";
            }
        }

        private void LoadSageVersionsCombo()
        {
            try
            {
                var integration = new SageIntegration("SageETLAgent", "SageETLAgent.exe");
                var versions = integration.GetInstalledVersions();

                cmbSageVersion.Items.Clear();
                cmbSageVersion.Items.Add("— Toutes les versions —");

                foreach (var v in versions)
                    cmbSageVersion.Items.Add(v);  // ToString() = Label

                // Sélectionner la première version réelle par défaut
                cmbSageVersion.SelectedIndex = versions.Count > 0 ? 1 : 0;
            }
            catch { /* Sage non installé */ }
        }

        private async Task RunSageSyncAsync()
        {
            btnSageSync.Enabled = false;
            lblStatus.Text = "Synchronisation Sage (registre)...";
            AppendLog("=== SAGE SYNC — Intégration registre ===");

            // Lire la version + sous-version sélectionnées
            string? targetPath = null;
            string? targetSubVersion = null;
            if (cmbSageVersion.SelectedIndex > 0
                && cmbSageVersion.SelectedItem is Integration.Sage.Models.SageVersionItem sel)
            {
                targetPath       = sel.VersionPath;
                targetSubVersion = sel.SubVersion;
                AppendLog($"  Cible : {sel.Label}");
            }

            try
            {
                // Charger les items de menu OptiBoard depuis le serveur
                var serverUrl = txtServerUrl.Text.Trim();
                var dwhCode   = txtDwhCode.Text.Trim();
                List<Integration.Sage.Models.OptiMenuItem> menuItems;

                try
                {
                    AppendLog($"  Chargement menu OptiBoard depuis {serverUrl} (DWH: {dwhCode})...");
                    using var apiClient = new ApiClient(serverUrl, dwhCode);
                    menuItems = await apiClient.GetMenuItemsAsync();
                    AppendLog($"  {menuItems.Count} item(s) de menu chargé(s) depuis le serveur.");
                }
                catch (Exception apiEx)
                {
                    AppendLog($"  ⚠ Serveur inaccessible ({apiEx.Message}) — synchronisation annulée.");
                    MessageBox.Show($"Impossible de joindre le serveur :\n{apiEx.Message}",
                        "Sage Sync", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                    return;
                }

                AppendLog($"  Items à enregistrer : {menuItems.Count}");

                var report = await Task.Run(() =>
                {
                    var integration = new SageIntegration(
                        appName:        "OptiBoard",
                        executableName: "SageETLAgent.exe");

                    return integration.SyncFromMenu(menuItems, targetPath, targetSubVersion, serverUrl);
                });

                AppendLog(report.ToString());

                foreach (var r in report.ModuleResults)
                    AppendLog($"  {r}");

                if (report.SageWasRunning)
                    AppendLog("  ⚠ Sage était ouvert — redémarrez Sage pour voir les changements.");

                var msg = report.IsSuccess
                    ? $"Synchronisation réussie.\n{report.TotalProgramsRegistered} programme(s) enregistré(s) dans {report.ModuleResults.Count} module(s) Sage."
                    : "Aucun module Sage détecté ou synchronisation échouée.\nVérifiez les logs.";

                MessageBox.Show(msg, "Sage Sync",
                    MessageBoxButtons.OK,
                    report.IsSuccess ? MessageBoxIcon.Information : MessageBoxIcon.Warning);
            }
            catch (Exception ex)
            {
                AppendLog($"ERREUR Sage Sync: {ex.Message}");
                MessageBox.Show($"Erreur: {ex.Message}", "Erreur Sage Sync", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
            finally
            {
                btnSageSync.Enabled = true;
                lblStatus.Text = "Pret";
            }
        }

        #endregion

        #region Mode Continu

        private async Task StartContinuousModeAsync()
        {
            var selected = _agents.Where(a => a.IsSelected).ToList();
            if (!selected.Any())
            {
                MessageBox.Show("Selectionnez au moins un agent", "Info", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }

            // Toujours relire l'URL du champ texte avant de demarrer
            _serverUrl = txtServerUrl.Text.Trim();

            AppendLog($"=== DEMARRAGE MODE CONTINU ({selected.Count} agent(s)) ===");

            foreach (var agent in selected)
            {
                if (_continuousServices.ContainsKey(agent.AgentId))
                    continue;

                var service = new ContinuousSyncService(_serverUrl, agent);
                // LogMessage/ErrorOccurred n'est plus necessaire: les services logguent directement via SyncLogger
                service.ProgressChanged += SyncManager_ProgressChanged;
                service.SyncCompleted += ContinuousService_SyncCompleted;
                service.HeartbeatSent += (s, e) => { }; // Update UI

                _continuousServices[agent.AgentId] = service;

                try
                {
                    await service.StartAsync();
                }
                catch (Exception ex)
                {
                    AppendLog($"Erreur demarrage {agent.Name}: {ex.Message}");
                }
            }

            UpdateContinuousButtons(true);
            heartbeatTimer.Start();
        }

        private async Task StopContinuousModeAsync()
        {
            AppendLog("=== ARRET MODE CONTINU ===");

            heartbeatTimer.Stop();

            foreach (var kvp in _continuousServices.ToList())
            {
                try
                {
                    await kvp.Value.StopAsync();
                    kvp.Value.Dispose();
                }
                catch (Exception ex)
                {
                    AppendLog($"Erreur arret: {ex.Message}");
                }
            }

            _continuousServices.Clear();
            UpdateContinuousButtons(false);
            lblContinuousStatus.Text = "";
        }

        private void PauseContinuousMode()
        {
            foreach (var service in _continuousServices.Values)
            {
                service.Pause();
            }
            AppendLog("Mode continu en PAUSE");
            btnPause.Enabled = false;
            btnResume.Enabled = true;
        }

        private void ResumeContinuousMode()
        {
            foreach (var service in _continuousServices.Values)
            {
                service.Resume();
            }
            AppendLog("Mode continu REPRIS");
            btnPause.Enabled = true;
            btnResume.Enabled = false;
        }

        private void UpdateContinuousButtons(bool running)
        {
            btnStartContinuous.Enabled = !running;
            btnStopContinuous.Enabled = running;
            btnPause.Enabled = running;
            btnResume.Enabled = false;
            cmbSyncMode.Enabled = !running;
            btnLoadAgents.Enabled = !running;
        }

        private void UpdateContinuousStatusUI()
        {
            if (!_continuousServices.Any())
            {
                lblContinuousStatus.Text = "";
                return;
            }

            var active = _continuousServices.Values.Count(s => s.IsRunning && !s.IsPaused);
            var paused = _continuousServices.Values.Count(s => s.IsPaused);

            lblContinuousStatus.Text = $"Actifs: {active} | Pause: {paused}";
            lblContinuousStatus.ForeColor = paused > 0 ? ThemeWarning : ThemeSuccess;
        }

        private void ContinuousService_SyncCompleted(object? sender, AgentSyncResult e)
        {
            if (InvokeRequired)
            {
                Invoke(() => ContinuousService_SyncCompleted(sender, e));
                return;
            }

            // Update grid
            var agent = _agents.FirstOrDefault(a => a.AgentId == e.AgentId);
            if (agent != null)
            {
                agent.LastSync = DateTime.Now;
                agent.TotalRowsSynced += e.TotalRows;
                agent.TotalSyncs++;
                dgvAgents.Refresh();
            }
        }

        private void OnFormClosing_Handler(object? sender, FormClosingEventArgs e)
        {
            if (!_forceClose)
            {
                // Intercepter le X : minimiser dans le tray au lieu de fermer
                e.Cancel = true;
                WindowState = FormWindowState.Minimized;
                return;
            }

            // Fermeture definitive (via menu tray "Quitter")
            _trayIcon.Visible = false;
            _trayIcon.Dispose();

            if (_continuousServices.Any())
            {
                // Arreter les services de maniere synchrone
                Task.Run(async () => await StopContinuousModeAsync()).Wait(TimeSpan.FromSeconds(10));
            }

            SyncLogger.Instance.Dispose();
        }

        #endregion

        #region Tache Planifiee

        private const string ScheduledTaskName = "SageETLAgent_AutoStart";

        private void ConfigureScheduledTask()
        {
            bool taskExists = IsScheduledTaskExists();

            if (taskExists)
            {
                var result = MessageBox.Show(
                    "La tache planifiee 'SageETLAgent_AutoStart' existe deja.\n\n" +
                    "Voulez-vous la SUPPRIMER ?\n\n" +
                    "Oui = Supprimer la tache\n" +
                    "Non = Garder la tache",
                    "Tache planifiee",
                    MessageBoxButtons.YesNo,
                    MessageBoxIcon.Question);

                if (result == DialogResult.Yes)
                {
                    RemoveScheduledTask();
                }
            }
            else
            {
                var result = MessageBox.Show(
                    "Creer une tache planifiee pour lancer automatiquement\n" +
                    "SageETLAgent en mode service a chaque demarrage du systeme ?\n\n" +
                    $"Executable: {Application.ExecutablePath} --service",
                    "Tache planifiee",
                    MessageBoxButtons.YesNo,
                    MessageBoxIcon.Question);

                if (result == DialogResult.Yes)
                {
                    CreateScheduledTask();
                }
            }
        }

        private bool IsScheduledTaskExists()
        {
            try
            {
                var psi = new ProcessStartInfo
                {
                    FileName = "schtasks.exe",
                    Arguments = $"/Query /TN \"{ScheduledTaskName}\" /FO CSV /NH",
                    UseShellExecute = false,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    CreateNoWindow = true
                };
                using var process = Process.Start(psi);
                process?.WaitForExit(5000);
                return process?.ExitCode == 0;
            }
            catch
            {
                return false;
            }
        }

        private void CreateScheduledTask()
        {
            try
            {
                var exePath = Application.ExecutablePath;
                var workDir = Path.GetDirectoryName(exePath) ?? "";

                // schtasks /Create : tache au demarrage avec HIGHEST privileges
                var args = $"/Create /TN \"{ScheduledTaskName}\" " +
                           $"/TR \"\\\"{exePath}\\\" --service\" " +
                           $"/SC ONSTART /DELAY 0000:30 " +
                           $"/RL HIGHEST /F";

                var psi = new ProcessStartInfo
                {
                    FileName = "schtasks.exe",
                    Arguments = args,
                    UseShellExecute = true,
                    Verb = "runas", // Elevation admin
                    CreateNoWindow = false
                };

                using var process = Process.Start(psi);
                process?.WaitForExit(15000);

                if (process?.ExitCode == 0)
                {
                    AppendLog("Tache planifiee creee: SageETLAgent_AutoStart (demarrage systeme + 30s)");
                    MessageBox.Show(
                        "Tache planifiee creee avec succes !\n\n" +
                        $"Nom: {ScheduledTaskName}\n" +
                        "Declencheur: Au demarrage du systeme (delai 30s)\n" +
                        $"Action: {exePath} --service\n" +
                        "Privileges: Eleves (administrateur)",
                        "Succes",
                        MessageBoxButtons.OK,
                        MessageBoxIcon.Information);
                }
                else
                {
                    AppendLog($"Erreur creation tache planifiee (code: {process?.ExitCode})");
                    MessageBox.Show(
                        "Erreur lors de la creation de la tache planifiee.\n" +
                        "Verifiez que vous avez les droits administrateur.",
                        "Erreur",
                        MessageBoxButtons.OK,
                        MessageBoxIcon.Error);
                }
            }
            catch (Exception ex)
            {
                AppendLog($"Erreur tache planifiee: {ex.Message}");
                MessageBox.Show(
                    $"Erreur: {ex.Message}\n\n" +
                    "L'elevation administrateur a peut-etre ete refusee.",
                    "Erreur",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error);
            }
        }

        private void RemoveScheduledTask()
        {
            try
            {
                var psi = new ProcessStartInfo
                {
                    FileName = "schtasks.exe",
                    Arguments = $"/Delete /TN \"{ScheduledTaskName}\" /F",
                    UseShellExecute = true,
                    Verb = "runas",
                    CreateNoWindow = false
                };

                using var process = Process.Start(psi);
                process?.WaitForExit(10000);

                if (process?.ExitCode == 0)
                {
                    AppendLog("Tache planifiee supprimee: SageETLAgent_AutoStart");
                    MessageBox.Show(
                        "Tache planifiee supprimee avec succes.",
                        "Succes",
                        MessageBoxButtons.OK,
                        MessageBoxIcon.Information);
                }
                else
                {
                    MessageBox.Show(
                        "Erreur lors de la suppression de la tache planifiee.",
                        "Erreur",
                        MessageBoxButtons.OK,
                        MessageBoxIcon.Error);
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Erreur: {ex.Message}", "Erreur",
                    MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        #endregion

        #region Mode Manuel

        private async Task TestConnectionAsync()
        {
            _serverUrl = txtServerUrl.Text.Trim();
            using var client = new ApiClient(_serverUrl);

            var (success, message) = await client.TestConnectionAsync();
            if (success)
            {
                MessageBox.Show("Connexion reussie!", "Test", MessageBoxButtons.OK, MessageBoxIcon.Information);
                lblStatus.Text = "Connecte";
            }
            else
            {
                MessageBox.Show($"Echec: {message}", "Erreur", MessageBoxButtons.OK, MessageBoxIcon.Error);
                lblStatus.Text = "Deconnecte";
            }
        }

        private async Task LoadAgentsAsync()
        {
            try
            {
                _serverUrl = txtServerUrl.Text.Trim();
                _dwhCode = txtDwhCode.Text.Trim();

                if (string.IsNullOrWhiteSpace(_dwhCode))
                {
                    MessageBox.Show("Le champ 'DWH Code' est obligatoire.\nEntrez le code client (ex: ESSAIDI01) avant de charger les agents.",
                        "DWH Code requis", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                    txtDwhCode.Focus();
                    return;
                }

                lblStatus.Text = "Chargement...";

                using var client = new ApiClient(_serverUrl, _dwhCode);
                _agents = await client.GetAgentsAsync();

                dgvAgents.DataSource = null;
                dgvAgents.DataSource = _agents;

                AppendLog($"Charge {_agents.Count} agent(s)");
                lblStatus.Text = $"{_agents.Count} agent(s)";

                // Setup progress bars
                SetupProgressBars();
                UpdateModeUI();

                // Auto-demarrage mode continu : selectionner tous les agents et lancer
                if (_agents.Any() && !_continuousServices.Any())
                {
                    foreach (var a in _agents) a.IsSelected = true;
                    dgvAgents.Refresh();
                    cmbSyncMode.SelectedIndex = 1; // "Continu"
                    await StartContinuousModeAsync();
                }
            }
            catch (Exception ex)
            {
                AppendLog($"ERREUR chargement: {ex.Message}");
                MessageBox.Show($"Erreur: {ex.Message}", "Erreur", MessageBoxButtons.OK, MessageBoxIcon.Error);
                lblStatus.Text = "Erreur";
            }
        }

        private void SetupProgressBars()
        {
            pnlProgress.Controls.Clear();
            _progressBars.Clear();
            _progressLabels.Clear();

            int y = 2;
            foreach (var agent in _agents)
            {
                var lbl = new Label
                {
                    Text = $"{agent.Name}:",
                    Location = new Point(5, y + 2),
                    Width = 80,
                    AutoSize = false,
                    Font = new Font("Segoe UI", 8F, FontStyle.Bold),
                    ForeColor = ThemeTextDark
                };
                pnlProgress.Controls.Add(lbl);

                var pb = new ProgressBar
                {
                    Location = new Point(90, y),
                    Width = 400,
                    Height = 18,
                    Style = ProgressBarStyle.Continuous
                };
                pnlProgress.Controls.Add(pb);
                _progressBars[agent.AgentId] = pb;

                var lblProgress = new Label
                {
                    Text = "En attente",
                    Location = new Point(500, y + 2),
                    Width = 500,
                    AutoSize = false,
                    ForeColor = ThemeTextMuted,
                    Font = new Font("Segoe UI", 8F)
                };
                pnlProgress.Controls.Add(lblProgress);
                _progressLabels[agent.AgentId] = lblProgress;

                y += 26;
            }
        }

        private async Task SyncSelectedAsync()
        {
            var selected = _agents.Where(a => a.IsSelected).ToList();
            if (!selected.Any())
            {
                MessageBox.Show("Selectionnez au moins un agent", "Info", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }

            await StartSyncAsync(selected);
        }

        private async Task SyncAllAsync()
        {
            foreach (var agent in _agents)
            {
                agent.IsSelected = true;
            }
            dgvAgents.Refresh();
            await StartSyncAsync(_agents);
        }

        private async Task StartSyncAsync(List<AgentProfile> agents)
        {
            SetSyncingState(true);

            // Reset progress bars
            foreach (var agent in agents)
            {
                if (_progressBars.TryGetValue(agent.AgentId, out var pb))
                {
                    pb.Value = 0;
                }
                if (_progressLabels.TryGetValue(agent.AgentId, out var lbl))
                {
                    lbl.Text = "Demarrage...";
                    lbl.ForeColor = ThemePrimary;
                }
            }

            try
            {
                await _syncManager.SyncAllAsync(agents, maxParallelism: 4);
            }
            finally
            {
                SetSyncingState(false);
            }
        }

        private void SetSyncingState(bool syncing)
        {
            btnSyncSelected.Enabled = !syncing;
            btnSyncAll.Enabled = !syncing;
            btnLoadAgents.Enabled = !syncing;
            btnCancel.Enabled = syncing;

            lblStatus.Text = syncing ? "Synchronisation..." : "Pret";
        }

        #endregion

        #region Event Handlers

        private void SyncManager_ProgressChanged(object? sender, SyncProgressEvent e)
        {
            if (InvokeRequired)
            {
                Invoke(() => SyncManager_ProgressChanged(sender, e));
                return;
            }

            if (_progressBars.TryGetValue(e.AgentId, out var pb))
            {
                pb.Value = Math.Min(100, (int)e.ProgressPercent);
            }

            if (_progressLabels.TryGetValue(e.AgentId, out var lbl))
            {
                lbl.Text = $"{e.CurrentTable} ({e.TableIndex}/{e.TotalTables}) - {e.Message}";
                lbl.ForeColor = ThemePrimary;
            }
        }

        private void SyncManager_AgentCompleted(object? sender, AgentSyncResult e)
        {
            if (InvokeRequired)
            {
                Invoke(() => SyncManager_AgentCompleted(sender, e));
                return;
            }

            if (_progressBars.TryGetValue(e.AgentId, out var pb))
            {
                pb.Value = 100;
            }

            if (_progressLabels.TryGetValue(e.AgentId, out var lbl))
            {
                if (e.Success)
                {
                    lbl.Text = $"OK - {e.TablesSuccess}/{e.TablesTotal} tables, {e.TotalRows:N0} lignes";
                    lbl.ForeColor = ThemeSuccess;
                }
                else
                {
                    lbl.Text = $"ERREUR: {e.Error}";
                    lbl.ForeColor = ThemeDanger;
                }
            }

            // Update grid
            var agent = _agents.FirstOrDefault(a => a.AgentId == e.AgentId);
            if (agent != null)
            {
                agent.LastSync = DateTime.Now;
                agent.TotalRowsSynced += e.TotalRows;
                dgvAgents.Refresh();
            }
        }

        private void SyncManager_AllCompleted(object? sender, EventArgs e)
        {
            if (InvokeRequired)
            {
                Invoke(() => SyncManager_AllCompleted(sender, e));
                return;
            }

            MessageBox.Show("Synchronisation terminee!", "Termine", MessageBoxButtons.OK, MessageBoxIcon.Information);
        }

        private void DgvAgents_CellClick(object? sender, DataGridViewCellEventArgs e)
        {
            if (e.RowIndex < 0) return;

            var agent = _agents[e.RowIndex];

            if (e.ColumnIndex == dgvAgents.Columns["colSync"]?.Index)
            {
                // Sync single agent (mode manuel)
                _ = SyncSingleAgentAsync(agent);
            }
            else if (e.ColumnIndex == dgvAgents.Columns["colContinuous"]?.Index)
            {
                // Toggle continuous mode for single agent
                _ = ToggleContinuousForAgentAsync(agent);
            }
            else if (e.ColumnIndex == dgvAgents.Columns["colTestConn"]?.Index)
            {
                _ = TestAgentConnectionAsync(agent);
            }
            else if (e.ColumnIndex == dgvAgents.Columns["colConfig"]?.Index)
            {
                // Show config dialog
                ShowAgentConfig(agent);
            }
            else if (e.ColumnIndex == dgvAgents.Columns["colDelete"]?.Index)
            {
                // Delete agent
                _ = DeleteAgentAsync(agent);
            }
        }

        private void DgvAgents_CellValueChanged(object? sender, DataGridViewCellEventArgs e)
        {
            if (e.RowIndex < 0) return;

            if (e.ColumnIndex == dgvAgents.Columns["colSelected"]?.Index)
            {
                var selected = _agents.Count(a => a.IsSelected);
                lblStatus.Text = $"{selected} agent(s) selectionne(s)";
                UpdateModeUI();
            }
        }

        private async Task TestAgentConnectionAsync(AgentProfile agent)
        {
            lblStatus.Text = $"Test connexion {agent.Name}...";
            var sb = new System.Text.StringBuilder();
            sb.AppendLine($"Test de connexion : {agent.Name}\n");

            static bool IsLocalServer(string server)
            {
                if (string.IsNullOrWhiteSpace(server)) return false;
                var s = server.Trim().ToLowerInvariant();
                return s == "." || s == "localhost" || s == "(local)" || s == "127.0.0.1"
                    || s.StartsWith("tcp:localhost") || s.StartsWith("tcp:127.0.0.1")
                    || s.StartsWith(".\\") || s.StartsWith("localhost\\");
            }

            // ── Source Sage ──────────────────────────────────────
            sb.AppendLine("SOURCE SAGE");
            sb.AppendLine($"  Serveur  : {agent.SageServer}");
            sb.AppendLine($"  Base     : {agent.SageDatabase}");
            bool sageLocal = IsLocalServer(agent.SageServer);
            sb.AppendLine($"  Auth     : {(sageLocal ? "Windows (Integrated Security)" : $"SQL — utilisateur : {agent.SageUsername}")}");
            try
            {
                string sageAuth = sageLocal
                    ? "Integrated Security=True;Trusted_Connection=True"
                    : $"User Id={agent.SageUsername};Password={agent.SagePassword}";
                var sageCsStr = $"Server={agent.SageServer};Database={agent.SageDatabase};{sageAuth};" +
                                "TrustServerCertificate=True;Connection Timeout=15;";
                using var sageCon = new SqlConnection(sageCsStr);
                await sageCon.OpenAsync();
                using var cmd = new SqlCommand("SELECT @@SERVERNAME, DB_NAME()", sageCon);
                cmd.CommandTimeout = 10;
                using var reader = await cmd.ExecuteReaderAsync();
                string srvName = "?", dbName = "?";
                if (await reader.ReadAsync())
                {
                    srvName = reader.IsDBNull(0) ? "?" : reader.GetString(0);
                    dbName  = reader.IsDBNull(1) ? "?" : reader.GetString(1);
                }
                sb.AppendLine($"  Resultat : OK  (instance={srvName}, base={dbName})");
            }
            catch (Exception ex)
            {
                sb.AppendLine($"  Resultat : ECHEC");
                sb.AppendLine($"  Erreur   : {ex.Message}");
            }

            sb.AppendLine();

            // ── Destination DWH ──────────────────────────────────
            sb.AppendLine("DESTINATION DWH");
            sb.AppendLine($"  Serveur  : {agent.DwhServer}");
            sb.AppendLine($"  Base     : {agent.DwhDatabase}");
            bool dwhLocal = IsLocalServer(agent.DwhServer);
            sb.AppendLine($"  Auth     : {(dwhLocal ? "Windows (Integrated Security)" : $"SQL — utilisateur : {agent.DwhUsername}")}");
            try
            {
                string dwhAuth = dwhLocal
                    ? "Integrated Security=True;Trusted_Connection=True"
                    : $"User Id={agent.DwhUsername};Password={agent.DwhPassword}";
                var dwhCsStr = $"Server={agent.DwhServer};Database={agent.DwhDatabase};{dwhAuth};" +
                               "TrustServerCertificate=True;Connection Timeout=15;";
                using var dwhCon = new SqlConnection(dwhCsStr);
                await dwhCon.OpenAsync();
                using var cmd = new SqlCommand("SELECT @@SERVERNAME, DB_NAME()", dwhCon);
                cmd.CommandTimeout = 10;
                using var reader = await cmd.ExecuteReaderAsync();
                string srvName = "?", dbName = "?";
                if (await reader.ReadAsync())
                {
                    srvName = reader.IsDBNull(0) ? "?" : reader.GetString(0);
                    dbName  = reader.IsDBNull(1) ? "?" : reader.GetString(1);
                }
                sb.AppendLine($"  Resultat : OK  (instance={srvName}, base={dbName})");
            }
            catch (Exception ex)
            {
                sb.AppendLine($"  Resultat : ECHEC");
                sb.AppendLine($"  Erreur   : {ex.Message}");
            }

            lblStatus.Text = "Pret";
            AppendLog($"[TEST CONN] {agent.Name} — voir la fenetre de resultat");
            MessageBox.Show(sb.ToString(), $"Test de connexion — {agent.Name}",
                MessageBoxButtons.OK, MessageBoxIcon.Information);
        }

        private async Task SyncSingleAgentAsync(AgentProfile agent)
        {
            agent.IsSelected = true;
            dgvAgents.Refresh();
            await StartSyncAsync(new List<AgentProfile> { agent });
        }

        private async Task ToggleContinuousForAgentAsync(AgentProfile agent)
        {
            if (_continuousServices.TryGetValue(agent.AgentId, out var existingService))
            {
                // Arreter le service existant
                await existingService.StopAsync();
                existingService.Dispose();
                _continuousServices.Remove(agent.AgentId);
                AppendLog($"Mode continu arrete pour {agent.Name}");
            }
            else
            {
                // Demarrer un nouveau service
                var service = new ContinuousSyncService(_serverUrl, agent);
                // LogMessage n'est plus necessaire: les services logguent directement via SyncLogger
                service.ProgressChanged += SyncManager_ProgressChanged;
                service.SyncCompleted += ContinuousService_SyncCompleted;

                _continuousServices[agent.AgentId] = service;

                try
                {
                    await service.StartAsync();
                    AppendLog($"Mode continu demarre pour {agent.Name}");
                }
                catch (Exception ex)
                {
                    AppendLog($"Erreur: {ex.Message}");
                    _continuousServices.Remove(agent.AgentId);
                }
            }

            if (_continuousServices.Any() && !heartbeatTimer.Enabled)
            {
                heartbeatTimer.Start();
            }
            else if (!_continuousServices.Any())
            {
                heartbeatTimer.Stop();
                lblContinuousStatus.Text = "";
            }
        }

        private void ShowAgentConfig(AgentProfile agent)
        {
            var dlg = new Form
            {
                Text = $"Configuration — {agent.Name}",
                Width = 420,
                Height = 440,
                StartPosition = FormStartPosition.CenterParent,
                FormBorderStyle = FormBorderStyle.FixedDialog,
                MaximizeBox = false, MinimizeBox = false,
                BackColor = ThemeBg,
                Font = new Font("Segoe UI", 9F)
            };

            var tbl = new TableLayoutPanel
            {
                Dock = DockStyle.Fill,
                ColumnCount = 2,
                Padding = new Padding(14, 10, 14, 8),
                AutoSize = true
            };
            tbl.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 130));
            tbl.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
            dlg.Controls.Add(tbl);

            Label MkLabel(string text, bool section = false)
            {
                var lbl = new Label { Text = text, AutoSize = true, Dock = DockStyle.Fill, TextAlign = ContentAlignment.MiddleLeft };
                if (section)
                {
                    lbl.Font = new Font("Segoe UI", 8.5F, FontStyle.Bold);
                    lbl.ForeColor = ThemePrimaryDarker;
                    lbl.Margin = new Padding(0, 10, 0, 2);
                }
                else
                {
                    lbl.ForeColor = ThemeTextMuted;
                    lbl.Margin = new Padding(0, 4, 8, 4);
                }
                return lbl;
            }

            TextBox MkField(string value, bool password = false)
            {
                return new TextBox
                {
                    Text = value,
                    Dock = DockStyle.Fill,
                    BorderStyle = BorderStyle.FixedSingle,
                    Margin = new Padding(0, 3, 0, 3),
                    PasswordChar = password ? '●' : '\0'
                };
            }

            // ── Section Source Sage ──
            var lblSrc = MkLabel("▸ Source Sage", section: true);
            tbl.Controls.Add(lblSrc, 0, 0); tbl.SetColumnSpan(lblSrc, 2);

            tbl.Controls.Add(MkLabel("Serveur"), 0, 1);
            var txtSageSrv = MkField(agent.SageServer);
            tbl.Controls.Add(txtSageSrv, 1, 1);

            tbl.Controls.Add(MkLabel("Base de données"), 0, 2);
            var txtSageDb = MkField(agent.SageDatabase);
            tbl.Controls.Add(txtSageDb, 1, 2);

            tbl.Controls.Add(MkLabel("Utilisateur SQL"), 0, 3);
            var txtSageUser = MkField(agent.SageUsername);
            tbl.Controls.Add(txtSageUser, 1, 3);

            tbl.Controls.Add(MkLabel("Mot de passe"), 0, 4);
            var txtSagePwd = MkField(agent.SagePassword, password: true);
            tbl.Controls.Add(txtSagePwd, 1, 4);

            // ── Section DWH ──
            var lblDwh = MkLabel("▸ Destination DWH", section: true);
            tbl.Controls.Add(lblDwh, 0, 5); tbl.SetColumnSpan(lblDwh, 2);

            tbl.Controls.Add(MkLabel("Serveur"), 0, 6);
            var txtDwhSrv = MkField(agent.DwhServer);
            tbl.Controls.Add(txtDwhSrv, 1, 6);

            tbl.Controls.Add(MkLabel("Base de données"), 0, 7);
            var txtDwhDb = MkField(agent.DwhDatabase);
            tbl.Controls.Add(txtDwhDb, 1, 7);

            tbl.Controls.Add(MkLabel("Utilisateur SQL"), 0, 8);
            var txtDwhUser = MkField(agent.DwhUsername);
            tbl.Controls.Add(txtDwhUser, 1, 8);

            tbl.Controls.Add(MkLabel("Mot de passe"), 0, 9);
            var txtDwhPwd = MkField(agent.DwhPassword, password: true);
            tbl.Controls.Add(txtDwhPwd, 1, 9);

            // ── Barre de test connexion ──
            var testBar = new Panel
            {
                Dock = DockStyle.Bottom,
                Height = 38,
                BackColor = ThemeBg,
                Padding = new Padding(14, 5, 14, 5)
            };
            var btnTest = CreateStyledButton("🔌 Tester la connexion", 160, 26,
                Color.FromArgb(8, 145, 178), Color.White);
            btnTest.Dock = DockStyle.Right;
            var lblTestResult = new Label
            {
                AutoSize = false,
                Dock = DockStyle.Fill,
                TextAlign = ContentAlignment.MiddleLeft,
                Font = new Font("Segoe UI", 8.5F, FontStyle.Italic),
                ForeColor = ThemeTextMuted,
                Text = "Tester avant de sauvegarder"
            };
            testBar.Controls.Add(lblTestResult);
            testBar.Controls.Add(btnTest);
            dlg.Controls.Add(testBar);

            btnTest.Click += async (s, e) =>
            {
                btnTest.Enabled = false;
                btnTest.Text = "Connexion...";
                lblTestResult.ForeColor = ThemeTextMuted;
                lblTestResult.Text = "Test en cours...";
                try
                {
                    var cs = $"Server={txtSageSrv.Text.Trim()};" +
                             $"Database={txtSageDb.Text.Trim()};" +
                             $"User Id={txtSageUser.Text.Trim()};" +
                             $"Password={txtSagePwd.Text};" +
                             $"Connect Timeout=8;TrustServerCertificate=True;";
                    using var conn = new SqlConnection(cs);
                    await conn.OpenAsync();
                    lblTestResult.ForeColor = Color.FromArgb(34, 197, 94);   // vert
                    lblTestResult.Text = "✔ Connexion réussie !";
                    lblTestResult.Font = new Font("Segoe UI", 8.5F, FontStyle.Bold);
                }
                catch (Exception ex)
                {
                    lblTestResult.ForeColor = Color.FromArgb(239, 68, 68);   // rouge
                    var msg = ex.Message.Length > 60 ? ex.Message[..57] + "…" : ex.Message;
                    lblTestResult.Text = $"✘ {msg}";
                    lblTestResult.Font = new Font("Segoe UI", 8F, FontStyle.Italic);
                }
                finally
                {
                    btnTest.Enabled = true;
                    btnTest.Text = "🔌 Tester la connexion";
                }
            };

            // ── Boutons Annuler / Enregistrer ──
            var btnPanel = new FlowLayoutPanel
            {
                Dock = DockStyle.Bottom,
                FlowDirection = FlowDirection.RightToLeft,
                Height = 42,
                Padding = new Padding(8, 6, 8, 6),
                BackColor = ThemeBgCard
            };
            var btnSave    = CreateStyledButton("💾 Enregistrer", 120, 28, ThemePrimary, Color.White);
            var btnCancel2 = CreateStyledButton("Annuler", 80, 28, ThemeTextMuted, Color.White, isOutline: true);
            btnPanel.Controls.Add(btnSave);
            btnPanel.Controls.Add(btnCancel2);
            dlg.Controls.Add(btnPanel);

            btnCancel2.Click += (s, e) => dlg.Close();

            btnSave.Click += async (s, e) =>
            {
                btnSave.Enabled = false;
                btnSave.Text = "...";
                try
                {
                    var updates = new
                    {
                        sage_server   = txtSageSrv.Text.Trim(),
                        sage_database = txtSageDb.Text.Trim(),
                        sage_username = txtSageUser.Text.Trim(),
                        sage_password = txtSagePwd.Text,
                        dwh_server    = txtDwhSrv.Text.Trim(),
                        dwh_database  = txtDwhDb.Text.Trim(),
                        dwh_username  = txtDwhUser.Text.Trim(),
                        dwh_password  = txtDwhPwd.Text
                    };

                    using var client = new ApiClient(_serverUrl, _dwhCode);
                    var (ok, msg) = await client.UpdateAgentAsync(agent.AgentId, updates, _dwhCode);

                    if (ok)
                    {
                        // Mettre a jour le profil local
                        agent.SageServer   = updates.sage_server;
                        agent.SageDatabase = updates.sage_database;
                        agent.SageUsername = updates.sage_username;
                        agent.SagePassword = updates.sage_password;
                        agent.DwhServer    = updates.dwh_server;
                        agent.DwhDatabase  = updates.dwh_database;
                        agent.DwhUsername  = updates.dwh_username;
                        agent.DwhPassword  = updates.dwh_password;
                        dgvAgents.Refresh();
                        AppendLog($"[CONFIG] {agent.Name} — parametres de connexion mis a jour");
                        dlg.Close();
                    }
                    else
                    {
                        MessageBox.Show($"Echec de la sauvegarde :\n{msg}", "Erreur",
                            MessageBoxButtons.OK, MessageBoxIcon.Error);
                        btnSave.Enabled = true;
                        btnSave.Text = "Enregistrer";
                    }
                }
                catch (Exception ex)
                {
                    MessageBox.Show(ex.Message, "Erreur", MessageBoxButtons.OK, MessageBoxIcon.Error);
                    btnSave.Enabled = true;
                    btnSave.Text = "Enregistrer";
                }
            };

            dlg.ShowDialog(this);
        }

        private async Task DeleteAgentAsync(AgentProfile agent)
        {
            // Verifier si l'agent est en mode continu
            if (_continuousServices.ContainsKey(agent.AgentId))
            {
                MessageBox.Show(
                    $"L'agent '{agent.Name}' est en mode continu.\nArretez-le d'abord avant de le supprimer.",
                    "Agent actif",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Warning);
                return;
            }

            // Confirmation de suppression
            var result = MessageBox.Show(
                $"Etes-vous sur de vouloir supprimer l'agent '{agent.Name}' ?\n\n" +
                $"Cette action supprimera egalement toutes les tables associees.\n" +
                $"Cette operation est irreversible.",
                "Confirmer la suppression",
                MessageBoxButtons.YesNo,
                MessageBoxIcon.Warning,
                MessageBoxDefaultButton.Button2);

            if (result != DialogResult.Yes)
                return;

            try
            {
                lblStatus.Text = "Suppression...";
                AppendLog($"Suppression de l'agent {agent.Name}...");

                using var client = new ApiClient(_serverUrl);
                var (success, message) = await client.DeleteAgentAsync(agent.AgentId);

                if (success)
                {
                    AppendLog($"Agent {agent.Name} supprime avec succes");

                    // Retirer de la liste locale
                    _agents.Remove(agent);

                    // Retirer les barres de progression
                    if (_progressBars.ContainsKey(agent.AgentId))
                    {
                        _progressBars.Remove(agent.AgentId);
                    }
                    if (_progressLabels.ContainsKey(agent.AgentId))
                    {
                        _progressLabels.Remove(agent.AgentId);
                    }

                    // Rafraichir le DataGridView
                    dgvAgents.DataSource = null;
                    dgvAgents.DataSource = _agents;

                    // Reconfigurer les barres de progression
                    SetupProgressBars();

                    lblStatus.Text = $"{_agents.Count} agent(s)";

                    MessageBox.Show(
                        $"L'agent '{agent.Name}' a ete supprime avec succes.",
                        "Suppression reussie",
                        MessageBoxButtons.OK,
                        MessageBoxIcon.Information);
                }
                else
                {
                    AppendLog($"Erreur suppression: {message}");
                    MessageBox.Show(
                        $"Erreur lors de la suppression:\n{message}",
                        "Erreur",
                        MessageBoxButtons.OK,
                        MessageBoxIcon.Error);
                    lblStatus.Text = "Erreur";
                }
            }
            catch (Exception ex)
            {
                AppendLog($"Erreur suppression: {ex.Message}");
                MessageBox.Show(
                    $"Erreur lors de la suppression:\n{ex.Message}",
                    "Erreur",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error);
                lblStatus.Text = "Erreur";
            }
        }

        #endregion

        /// <summary>
        /// Methode de compatibilite: les services qui n'ont pas encore migre vers SyncLogger
        /// passent encore par cet ancien AppendLog via EventHandler.
        /// Les messages sont relayes au SyncLogger pour affichage colore.
        /// </summary>
        private void AppendLog(string message)
        {
            // Relayer les anciens messages vers le logger centralise
            // qui gere le threading, la couleur et le fichier
            SyncLogger.Instance.Info(LogCategory.GENERAL, message);
        }
    }
}
