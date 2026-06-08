/**
 * Palette de couleurs harmonisée OptiBoard (Phase 3 — U-01)
 * Importer et utiliser dans tous les composants graphiques.
 */
export const COLORS = {
  primary: '#2563eb',
  success: '#16a34a',
  danger:  '#dc2626',
  warning: '#ea580c',
  neutral: '#6b7280',
}

/** Couleurs ordonnées pour les graphiques multi-séries */
export const CHART_PALETTE = [
  '#2563eb', // primary blue
  '#16a34a', // success green
  '#ea580c', // warning orange
  '#8b5cf6', // purple
  '#06b6d4', // cyan
  '#f59e0b', // amber
  '#ec4899', // pink
  '#10b981', // emerald
]

/** Couleurs pour les tranches d'âge de créances */
export const AGE_COLORS = {
  'A échoir':   '#16a34a',
  '0-30 jours': '#2563eb',
  '31-60 jours':'#f59e0b',
  '61-90 jours':'#ea580c',
  '+90 jours':  '#dc2626',
}

/** Classes Tailwind par niveau de performance */
export const perfClass = (value, good = 80, warn = 50) => {
  if (value == null) return 'text-gray-400'
  if (value >= good)  return 'text-green-600 dark:text-green-400'
  if (value >= warn)  return 'text-orange-500 dark:text-orange-400'
  return 'text-red-600 dark:text-red-400'
}
