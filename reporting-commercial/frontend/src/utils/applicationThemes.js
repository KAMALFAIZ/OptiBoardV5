// ════════════════════════════════════════════════════════════════════
// Thèmes par application métier (commercial, comptabilite, paie, tresorerie)
// Module partagé par les 4 builders : DashboardBuilder, GridViewBuilder,
// PivotBuilderV2, SpreadsheetBuilder.
//
// Fusion des constantes locales dupliquées (2026-06) :
// - APP_DOT / APP_TEXT / APP_BG étaient identiques dans DashboardBuilder,
//   GridViewBuilder et PivotBuilderV2 (aucune divergence de valeur).
// - APP_LABEL provient de PivotBuilderV2 / SpreadsheetBuilder (identiques).
// - SpreadsheetBuilder ne définissait que APP_DOT + APP_LABEL (mêmes valeurs).
// ════════════════════════════════════════════════════════════════════

// Pastille de couleur (liste sidebar, badges)
export const APP_DOT = {
  commercial:   'bg-blue-500',
  comptabilite: 'bg-emerald-500',
  paie:         'bg-orange-400',
  tresorerie:   'bg-violet-500',
}

// Couleur de texte (light + dark)
export const APP_TEXT = {
  commercial:   'text-blue-600 dark:text-blue-400',
  comptabilite: 'text-emerald-600 dark:text-emerald-400',
  paie:         'text-orange-500 dark:text-orange-400',
  tresorerie:   'text-violet-600 dark:text-violet-400',
}

// Fond coloré (light + dark)
export const APP_BG = {
  commercial:   'bg-blue-100 dark:bg-blue-900/30',
  comptabilite: 'bg-emerald-100 dark:bg-emerald-900/30',
  paie:         'bg-orange-100 dark:bg-orange-900/30',
  tresorerie:   'bg-violet-100 dark:bg-violet-900/30',
}

// Libellé court affiché dans l'UI
export const APP_LABEL = {
  commercial:   'Commerciale',
  comptabilite: 'Comptabilité',
  paie:         'Paie',
  tresorerie:   'Trésorerie',
}
