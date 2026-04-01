using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.IO;
using System.Linq;
using System.Text;
using System.Windows.Forms;
using SageETLAgent.Models;

namespace SageETLAgent.Forms
{
    /// <summary>
    /// Dialog affichant les resultats du pointage source vs DWH
    /// </summary>
    public class PointageResultForm : Form
    {
        private readonly ReconciliationReport _report;
        private DataGridView _dgv = null!;

        // ── Theme Colors (Professional) ──
        private static readonly Color ThemePrimary      = Color.FromArgb(37, 99, 235);
        private static readonly Color ThemePrimaryDarker = Color.FromArgb(30, 58, 138);
        private static readonly Color ThemePrimary50     = Color.FromArgb(239, 246, 255);
        private static readonly Color ThemePrimaryLight  = Color.FromArgb(219, 234, 254);
        private static readonly Color ThemeSuccess       = Color.FromArgb(22, 163, 74);
        private static readonly Color ThemeSuccessLight  = Color.FromArgb(220, 252, 231);
        private static readonly Color ThemeDanger        = Color.FromArgb(220, 38, 38);
        private static readonly Color ThemeDangerLight   = Color.FromArgb(254, 226, 226);
        private static readonly Color ThemeWarning       = Color.FromArgb(234, 88, 12);
        private static readonly Color ThemeWarningLight  = Color.FromArgb(255, 237, 213);
        private static readonly Color ThemeTextDark      = Color.FromArgb(15, 23, 42);
        private static readonly Color ThemeTextMuted     = Color.FromArgb(100, 116, 139);
        private static readonly Color ThemeBg            = Color.FromArgb(248, 250, 252);
        private static readonly Color ThemeBgCard        = Color.White;
        private static readonly Color ThemeBorder        = Color.FromArgb(226, 232, 240);

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

        public PointageResultForm(ReconciliationReport report)
        {
            _report = report;
            InitializeComponent();
            LoadData();
        }

        private void InitializeComponent()
        {
            this.Text = $"Pointage - {_report.AgentName} ({_report.SageDatabase} → {_report.DwhDatabase})";
            this.Size = new Size(1050, 650);
            this.StartPosition = FormStartPosition.CenterParent;
            this.Font = new Font("Segoe UI", 9F);
            this.MinimizeBox = false;
            this.MaximizeBox = true;
            this.BackColor = ThemeBg;

            // ── Header panel ──
            var headerPanel = new Panel
            {
                Dock = DockStyle.Top,
                Height = 48,
                BackColor = ThemeBgCard
            };
            headerPanel.Paint += (s, e) =>
            {
                var g = e.Graphics;
                g.SmoothingMode = SmoothingMode.AntiAlias;
                using var pen = new Pen(ThemePrimary, 2);
                g.DrawLine(pen, 0, headerPanel.Height - 1, headerPanel.Width, headerPanel.Height - 1);
                using var titleFont = new Font("Segoe UI", 12F, FontStyle.Bold);
                using var titleBrush = new SolidBrush(ThemeTextDark);
                g.DrawString($"Pointage — {_report.AgentName}", titleFont, titleBrush, 16, 13);
            };
            this.Controls.Add(headerPanel);

            var mainLayout = new TableLayoutPanel
            {
                Dock = DockStyle.Fill,
                RowCount = 3,
                ColumnCount = 1,
                Padding = new Padding(12, 56, 12, 8),
                BackColor = ThemeBg
            };
            mainLayout.RowStyles.Add(new RowStyle(SizeType.Absolute, 72));
            mainLayout.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
            mainLayout.RowStyles.Add(new RowStyle(SizeType.Absolute, 50));

            // ── Summary cards row ──
            var summaryPanel = new FlowLayoutPanel
            {
                Dock = DockStyle.Fill,
                FlowDirection = FlowDirection.LeftToRight,
                WrapContents = false,
                BackColor = Color.Transparent
            };

            void AddStatCard(string label, string value, Color color, Color bgColor)
            {
                var card = new Panel
                {
                    Width = 140,
                    Height = 58,
                    Margin = new Padding(0, 0, 8, 0)
                };
                card.Paint += (s, e) =>
                {
                    var g = e.Graphics;
                    g.SmoothingMode = SmoothingMode.AntiAlias;
                    var rect = new Rectangle(0, 0, card.Width - 1, card.Height - 1);
                    using var path = CreateRoundedRect(rect, 6);
                    using var fillBrush = new SolidBrush(bgColor);
                    g.FillPath(fillBrush, path);
                    using var borderPen = new Pen(Color.FromArgb(40, color), 1);
                    g.DrawPath(borderPen, path);
                    // Left accent
                    using var accentBrush = new SolidBrush(color);
                    g.FillRectangle(accentBrush, 0, 8, 3, card.Height - 16);
                    // Value
                    using var valFont = new Font("Segoe UI", 16F, FontStyle.Bold);
                    using var valBrush = new SolidBrush(color);
                    g.DrawString(value, valFont, valBrush, 12, 4);
                    // Label
                    using var lblFont = new Font("Segoe UI", 8F);
                    using var lblBrush = new SolidBrush(ThemeTextMuted);
                    g.DrawString(label, lblFont, lblBrush, 14, 36);
                };
                summaryPanel.Controls.Add(card);
            }

            AddStatCard("Tables", _report.TablesChecked.ToString(), ThemePrimary, ThemePrimary50);
            AddStatCard("OK", _report.TablesOk.ToString(), ThemeSuccess, ThemeSuccessLight);
            AddStatCard("Ecarts", _report.TablesWithDiffs.ToString(), ThemeWarning, ThemeWarningLight);
            AddStatCard("Erreurs", _report.TablesError.ToString(), ThemeDanger, ThemeDangerLight);
            AddStatCard("Duree", $"{_report.DurationSeconds:F1}s", ThemeTextMuted, Color.FromArgb(241, 245, 249));

            mainLayout.Controls.Add(summaryPanel, 0, 0);

            // ── DataGridView (card style) ──
            var gridCard = new Panel
            {
                Dock = DockStyle.Fill,
                BackColor = ThemeBgCard,
                Margin = new Padding(0, 4, 0, 4)
            };
            gridCard.Paint += (s, e) =>
            {
                var g = e.Graphics;
                g.SmoothingMode = SmoothingMode.AntiAlias;
                using var pen = new Pen(ThemeBorder, 1);
                var rect = new Rectangle(0, 0, gridCard.Width - 1, gridCard.Height - 1);
                using var path = CreateRoundedRect(rect, 6);
                g.DrawPath(pen, path);
            };

            _dgv = new DataGridView
            {
                Dock = DockStyle.Fill,
                AutoGenerateColumns = false,
                AllowUserToAddRows = false,
                AllowUserToDeleteRows = false,
                ReadOnly = true,
                SelectionMode = DataGridViewSelectionMode.FullRowSelect,
                RowHeadersVisible = false,
                BackgroundColor = ThemeBgCard,
                GridColor = ThemeBorder,
                BorderStyle = BorderStyle.None,
                CellBorderStyle = DataGridViewCellBorderStyle.SingleHorizontal,
                EnableHeadersVisualStyles = false,
                ColumnHeadersHeight = 36,
                RowTemplate = { Height = 32 }
            };
            _dgv.ColumnHeadersDefaultCellStyle = new DataGridViewCellStyle
            {
                BackColor = ThemePrimary50,
                ForeColor = ThemePrimaryDarker,
                Font = new Font("Segoe UI", 8.5F, FontStyle.Bold),
                Alignment = DataGridViewContentAlignment.MiddleLeft,
                Padding = new Padding(6, 0, 6, 0)
            };
            _dgv.DefaultCellStyle = new DataGridViewCellStyle
            {
                Font = new Font("Segoe UI", 9F),
                ForeColor = ThemeTextDark,
                BackColor = ThemeBgCard,
                SelectionBackColor = ThemePrimaryLight,
                SelectionForeColor = ThemePrimaryDarker,
                Padding = new Padding(4, 0, 4, 0)
            };
            _dgv.AlternatingRowsDefaultCellStyle = new DataGridViewCellStyle
            {
                BackColor = Color.FromArgb(250, 251, 254),
                SelectionBackColor = ThemePrimaryLight,
                SelectionForeColor = ThemePrimaryDarker
            };

            _dgv.Columns.Add(new DataGridViewTextBoxColumn
            {
                Name = "colTable",
                HeaderText = "Table",
                Width = 200
            });
            _dgv.Columns.Add(new DataGridViewTextBoxColumn
            {
                Name = "colSource",
                HeaderText = "Source",
                Width = 90,
                DefaultCellStyle = new DataGridViewCellStyle { Alignment = DataGridViewContentAlignment.MiddleRight }
            });
            _dgv.Columns.Add(new DataGridViewTextBoxColumn
            {
                Name = "colDwh",
                HeaderText = "DWH",
                Width = 90,
                DefaultCellStyle = new DataGridViewCellStyle { Alignment = DataGridViewContentAlignment.MiddleRight }
            });
            _dgv.Columns.Add(new DataGridViewTextBoxColumn
            {
                Name = "colEcart",
                HeaderText = "Ecart",
                Width = 80,
                DefaultCellStyle = new DataGridViewCellStyle { Alignment = DataGridViewContentAlignment.MiddleRight }
            });
            _dgv.Columns.Add(new DataGridViewTextBoxColumn
            {
                Name = "colMissing",
                HeaderText = "Manquantes",
                Width = 100,
                DefaultCellStyle = new DataGridViewCellStyle { Alignment = DataGridViewContentAlignment.MiddleRight }
            });
            _dgv.Columns.Add(new DataGridViewTextBoxColumn
            {
                Name = "colOrphans",
                HeaderText = "Orphelines",
                Width = 100,
                DefaultCellStyle = new DataGridViewCellStyle { Alignment = DataGridViewContentAlignment.MiddleRight }
            });
            _dgv.Columns.Add(new DataGridViewTextBoxColumn
            {
                Name = "colDuration",
                HeaderText = "Duree (s)",
                Width = 80,
                DefaultCellStyle = new DataGridViewCellStyle { Alignment = DataGridViewContentAlignment.MiddleRight }
            });
            _dgv.Columns.Add(new DataGridViewTextBoxColumn
            {
                Name = "colStatus",
                HeaderText = "Statut",
                Width = 80,
                DefaultCellStyle = new DataGridViewCellStyle
                {
                    Alignment = DataGridViewContentAlignment.MiddleCenter,
                    Font = new Font("Segoe UI", 8.5F, FontStyle.Bold)
                }
            });

            var gridInner = new Panel
            {
                Dock = DockStyle.Fill,
                Padding = new Padding(1)
            };
            gridInner.Controls.Add(_dgv);
            gridCard.Controls.Add(gridInner);
            mainLayout.Controls.Add(gridCard, 0, 1);

            // ── Buttons bar ──
            var buttonsPanel = new FlowLayoutPanel
            {
                Dock = DockStyle.Fill,
                FlowDirection = FlowDirection.RightToLeft,
                BackColor = Color.Transparent,
                Padding = new Padding(0, 8, 0, 0)
            };

            var btnClose = new Button
            {
                Text = "Fermer",
                Width = 100,
                Height = 34,
                FlatStyle = FlatStyle.Flat,
                BackColor = ThemeBgCard,
                ForeColor = ThemeTextMuted,
                Cursor = Cursors.Hand,
                Margin = new Padding(0, 0, 0, 0)
            };
            btnClose.FlatAppearance.BorderColor = ThemeBorder;
            btnClose.FlatAppearance.BorderSize = 1;
            btnClose.Click += (s, e) => this.Close();
            buttonsPanel.Controls.Add(btnClose);

            var btnExport = new Button
            {
                Text = "Exporter CSV",
                Width = 130,
                Height = 34,
                BackColor = ThemePrimary,
                ForeColor = Color.White,
                FlatStyle = FlatStyle.Flat,
                Cursor = Cursors.Hand,
                Margin = new Padding(0, 0, 8, 0)
            };
            btnExport.FlatAppearance.BorderSize = 0;
            btnExport.FlatAppearance.MouseOverBackColor = ControlPaint.Dark(ThemePrimary, 0.08f);
            btnExport.Click += BtnExport_Click;
            buttonsPanel.Controls.Add(btnExport);

            mainLayout.Controls.Add(buttonsPanel, 0, 2);

            this.Controls.Add(mainLayout);
        }

        private void LoadData()
        {
            foreach (var t in _report.Tables)
            {
                var rowIndex = _dgv.Rows.Add(
                    t.TableName,
                    t.SourceCount.ToString("N0"),
                    t.DwhCount.ToString("N0"),
                    t.CountDifference != 0 ? t.CountDifference.ToString("+#;-#;0") : "0",
                    t.HasPrimaryKey ? t.MissingInDwh.ToString("N0") : "-",
                    t.HasPrimaryKey ? t.OrphansInDwh.ToString("N0") : "-",
                    t.DurationSeconds.ToString("F1"),
                    t.Status);

                var row = _dgv.Rows[rowIndex];

                // Coloration selon statut
                switch (t.Status)
                {
                    case "OK":
                        row.Cells["colStatus"].Style.ForeColor = ThemeSuccess;
                        row.Cells["colStatus"].Style.BackColor = ThemeSuccessLight;
                        break;
                    case "ECART":
                        row.Cells["colStatus"].Style.ForeColor = ThemeWarning;
                        row.Cells["colStatus"].Style.BackColor = ThemeWarningLight;
                        row.Cells["colEcart"].Style.ForeColor = ThemeDanger;
                        if (t.MissingInDwh > 0)
                            row.Cells["colMissing"].Style.ForeColor = ThemeDanger;
                        if (t.OrphansInDwh > 0)
                            row.Cells["colOrphans"].Style.ForeColor = ThemeDanger;
                        break;
                    case "ERREUR":
                        row.Cells["colStatus"].Style.ForeColor = Color.White;
                        row.Cells["colStatus"].Style.BackColor = ThemeDanger;
                        row.DefaultCellStyle.ForeColor = ThemeTextMuted;
                        break;
                }
            }
        }

        private void BtnExport_Click(object? sender, EventArgs e)
        {
            using var dialog = new SaveFileDialog
            {
                Filter = "CSV|*.csv",
                FileName = $"pointage_{_report.AgentName}_{DateTime.Now:yyyyMMdd_HHmmss}.csv",
                Title = "Exporter le rapport de pointage"
            };

            if (dialog.ShowDialog() != DialogResult.OK)
                return;

            try
            {
                var sb = new StringBuilder();
                sb.AppendLine("Table;Source;DWH;Ecart;Manquantes DWH;Orphelines DWH;Duree (s);Statut;Erreur");

                foreach (var t in _report.Tables)
                {
                    sb.AppendLine(string.Join(";",
                        t.TableName,
                        t.SourceCount,
                        t.DwhCount,
                        t.CountDifference,
                        t.HasPrimaryKey ? t.MissingInDwh.ToString() : "",
                        t.HasPrimaryKey ? t.OrphansInDwh.ToString() : "",
                        t.DurationSeconds.ToString("F1"),
                        t.Status,
                        t.ErrorMessage ?? ""));
                }

                // Resume
                sb.AppendLine();
                sb.AppendLine($"Agent;{_report.AgentName}");
                sb.AppendLine($"Source;{_report.SageDatabase}");
                sb.AppendLine($"DWH;{_report.DwhDatabase}");
                sb.AppendLine($"Date;{_report.StartTime:yyyy-MM-dd HH:mm:ss}");
                sb.AppendLine($"Duree;{_report.DurationSeconds:F1}s");
                sb.AppendLine($"Tables OK;{_report.TablesOk}");
                sb.AppendLine($"Tables Ecarts;{_report.TablesWithDiffs}");
                sb.AppendLine($"Tables Erreurs;{_report.TablesError}");

                File.WriteAllText(dialog.FileName, sb.ToString(), Encoding.UTF8);
                MessageBox.Show($"Rapport exporte:\n{dialog.FileName}", "Export",
                    MessageBoxButtons.OK, MessageBoxIcon.Information);
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Erreur export: {ex.Message}", "Erreur",
                    MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }
    }
}
