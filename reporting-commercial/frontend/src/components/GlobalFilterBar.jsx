import { useState, useEffect } from 'react'
import { Calendar, Building2, Users, Package, MapPin, X, SlidersHorizontal, Eye } from 'lucide-react'
import { useGlobalFilters } from '../context/GlobalFilterContext'
import { getDwhFilterOptions } from '../services/api'

// Helper: formater date YYYY-MM-DD → DD/MM/YYYY
function fmtDate(d) {
  if (!d) return ''
  const [y, m, day] = d.split('-')
  return `${day}/${m}/${y}`
}

/**
 * Bouton compact + Modal de paramètres globaux
 * Même principe que le modal paramètres de GridViewDisplay
 */
export default function GlobalFilterBar({ showSociete = true, showCommercial = false, showGamme = false, showZone = false, onFilterChange = null, openOnMount = false, triggerOpen = 0 }) {
  const {
    filters,
    updateFilter,
    resetFilters,
    setCurrentYear,
    setPreviousYear,
    setCurrentMonth,
    setCurrentQuarter,
    hasActiveFilters
  } = useGlobalFilters()

  const [open, setOpen] = useState(false)
  const [societeOptions, setSocieteOptions] = useState([])
  const [hasAutoOpened, setHasAutoOpened] = useState(false)

  // Ouvrir automatiquement au chargement si demandé
  useEffect(() => {
    if (openOnMount && !hasAutoOpened) {
      setOpen(true)
      setHasAutoOpened(true)
    }
  }, [openOnMount, hasAutoOpened])

  // Ouvrir quand triggerOpen change (depuis un bouton externe comme Rafraîchir)
  useEffect(() => {
    if (triggerOpen > 0) setOpen(true)
  }, [triggerOpen])

  useEffect(() => {
    if (showSociete) loadSocieteOptions()
  }, [showSociete])

  const loadSocieteOptions = async () => {
    try {
      const res = await getDwhFilterOptions('societe')
      if (res.data?.success && res.data?.data) setSocieteOptions(res.data.data)
    } catch (e) {
      console.warn('Erreur chargement sociétés:', e)
    }
  }

  const handleFilterChange = (key, value) => {
    updateFilter(key, value)
    if (onFilterChange) setTimeout(() => onFilterChange(), 100)
  }

  const handlePeriodPreset = (action) => {
    action()
    if (onFilterChange) setTimeout(() => onFilterChange(), 100)
  }

  const handleReset = () => {
    resetFilters()
    if (onFilterChange) setTimeout(() => onFilterChange(), 100)
  }

  const handleApply = () => {
    setOpen(false)
    if (onFilterChange) setTimeout(() => onFilterChange(), 100)
  }

  // Libellé société
  const societeLabel = filters.societe
    ? societeOptions.find(o => o.value === filters.societe)?.label || filters.societe
    : null

  // Compteur filtres actifs (hors dates)
  const extraFiltersCount = [filters.societe, filters.commercial, filters.gamme, filters.zone].filter(Boolean).length

  const periodPresets = [
    { label: "Année en cours", action: setCurrentYear },
    { label: "Année précédente", action: setPreviousYear },
    { label: "Mois en cours", action: setCurrentMonth },
    { label: "Trimestre en cours", action: setCurrentQuarter },
  ]

  return (
    <>
      {/* ─── Bouton Toolbar ─── */}
      <button
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
        title="Paramètres de filtre"
      >
        <SlidersHorizontal className="w-4 h-4" style={{ color: 'var(--color-primary-500)' }} />
        <span className="hidden sm:inline">{fmtDate(filters.dateDebut)} - {fmtDate(filters.dateFin)}</span>
        {extraFiltersCount > 0 && (
          <span className="w-4.5 h-4.5 flex items-center justify-center rounded-full text-[9px] font-bold text-white" style={{ backgroundColor: 'var(--color-primary-500)', minWidth: '18px', height: '18px' }}>
            {extraFiltersCount}
          </span>
        )}
      </button>

      {/* ─── Modal Paramètres (même style que GridViewDisplay) ─── */}
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/50" onClick={() => setOpen(false)} />
          <div className="relative bg-white dark:bg-gray-800 rounded-xl shadow-xl p-6 w-[500px] max-w-[90vw]">
            {/* Header */}
            <div className="flex items-center gap-2 mb-4">
              <SlidersHorizontal className="w-5 h-5" style={{ color: 'var(--color-primary-500)' }} />
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Paramètres
              </h2>
            </div>

            <div className="space-y-4 mb-6">
              {/* Période rapide */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                  Période rapide
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {periodPresets.map((preset, i) => (
                    <button
                      key={i}
                      onClick={() => handlePeriodPreset(preset.action)}
                      className="px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-primary-600 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors text-gray-700 dark:text-gray-300 text-left"
                    >
                      {preset.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Date Début */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Date début
                </label>
                <input
                  type="date"
                  value={filters.dateDebut}
                  onChange={(e) => handleFilterChange('dateDebut', e.target.value)}
                  className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-700 dark:text-white"
                />
              </div>

              {/* Date Fin */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Date fin
                </label>
                <input
                  type="date"
                  value={filters.dateFin}
                  onChange={(e) => handleFilterChange('dateFin', e.target.value)}
                  className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-700 dark:text-white"
                />
              </div>

              {/* Société */}
              {showSociete && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Société
                  </label>
                  <select
                    value={filters.societe || ''}
                    onChange={(e) => handleFilterChange('societe', e.target.value || null)}
                    className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-700 dark:text-white"
                  >
                    <option value="">Toutes les sociétés</option>
                    {societeOptions.map((opt, i) => (
                      <option key={i} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>
              )}

              {/* Commercial */}
              {showCommercial && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Commercial
                  </label>
                  <select
                    value={filters.commercial || ''}
                    onChange={(e) => handleFilterChange('commercial', e.target.value || null)}
                    className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-700 dark:text-white"
                  >
                    <option value="">Tous les commerciaux</option>
                  </select>
                </div>
              )}

              {/* Gamme */}
              {showGamme && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Gamme
                  </label>
                  <select
                    value={filters.gamme || ''}
                    onChange={(e) => handleFilterChange('gamme', e.target.value || null)}
                    className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-700 dark:text-white"
                  >
                    <option value="">Toutes les gammes</option>
                  </select>
                </div>
              )}

              {/* Zone */}
              {showZone && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Zone
                  </label>
                  <select
                    value={filters.zone || ''}
                    onChange={(e) => handleFilterChange('zone', e.target.value || null)}
                    className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-700 dark:text-white"
                  >
                    <option value="">Toutes les zones</option>
                  </select>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="flex justify-between">
              <button
                onClick={handleReset}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-500 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
              >
                <X className="w-4 h-4" />
                Réinitialiser
              </button>
              <div className="flex gap-2">
                <button
                  onClick={() => setOpen(false)}
                  className="btn-secondary"
                >
                  Annuler
                </button>
                <button
                  onClick={handleApply}
                  className="btn-primary flex items-center gap-1"
                >
                  <Eye className="w-4 h-4" />
                  Appliquer
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
