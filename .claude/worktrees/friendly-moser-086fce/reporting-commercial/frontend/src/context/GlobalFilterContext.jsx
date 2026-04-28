import { createContext, useContext, useState, useEffect, useCallback } from 'react'

/**
 * Contexte global pour les filtres partagés entre tous les composants
 * Ces filtres sont automatiquement injectés dans les datasources
 */
const GlobalFilterContext = createContext()

// Clés des filtres stockées dans localStorage
const STORAGE_KEY = 'reporting_global_filters'

// Valeurs par défaut des filtres
const getDefaultFilters = () => {
  const today = new Date()
  const year = today.getFullYear()

  return {
    dateDebut: `${year - 2}-01-01`,
    dateFin: today.toISOString().split('T')[0],
    annee: year,
    societe: null,
    commercial: null,
    gamme: null,
    zone: null,
    client: null
  }
}

export function GlobalFilterProvider({ children }) {
  // Charger les filtres depuis localStorage ou utiliser les valeurs par défaut
  const [filters, setFilters] = useState(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored) {
        const parsed = JSON.parse(stored)
        const defaults = getDefaultFilters()
        const merged = { ...defaults, ...parsed }
        // Si dateDebut est dans l'annee courante seulement, etendre a 2 ans en arriere
        const currentYear = new Date().getFullYear()
        const storedYear = merged.dateDebut ? parseInt(merged.dateDebut.slice(0, 4)) : 0
        if (storedYear >= currentYear) {
          merged.dateDebut = defaults.dateDebut
        }
        return merged
      }
    } catch (e) {
      console.warn('Erreur lecture filtres localStorage:', e)
    }
    return getDefaultFilters()
  })

  // Sauvegarder dans localStorage à chaque changement
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(filters))
    } catch (e) {
      console.warn('Erreur sauvegarde filtres localStorage:', e)
    }
  }, [filters])

  /**
   * Met à jour un seul filtre
   */
  const updateFilter = useCallback((key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }))
  }, [])

  /**
   * Met à jour plusieurs filtres à la fois
   */
  const updateFilters = useCallback((newFilters) => {
    setFilters(prev => ({ ...prev, ...newFilters }))
  }, [])

  /**
   * Réinitialise tous les filtres aux valeurs par défaut
   */
  const resetFilters = useCallback(() => {
    setFilters(getDefaultFilters())
  }, [])

  /**
   * Définit la période à l'année courante
   */
  const setCurrentYear = useCallback(() => {
    const year = new Date().getFullYear()
    setFilters(prev => ({
      ...prev,
      dateDebut: `${year}-01-01`,
      dateFin: `${year}-12-31`,
      annee: year
    }))
  }, [])

  /**
   * Définit la période à l'année précédente
   */
  const setPreviousYear = useCallback(() => {
    const year = new Date().getFullYear() - 1
    setFilters(prev => ({
      ...prev,
      dateDebut: `${year}-01-01`,
      dateFin: `${year}-12-31`,
      annee: year
    }))
  }, [])

  /**
   * Définit la période au mois courant
   */
  const setCurrentMonth = useCallback(() => {
    const today = new Date()
    const year = today.getFullYear()
    const month = String(today.getMonth() + 1).padStart(2, '0')
    const lastDay = new Date(year, today.getMonth() + 1, 0).getDate()

    setFilters(prev => ({
      ...prev,
      dateDebut: `${year}-${month}-01`,
      dateFin: `${year}-${month}-${String(lastDay).padStart(2, '0')}`,
      annee: year
    }))
  }, [])

  /**
   * Définit la période au trimestre courant
   */
  const setCurrentQuarter = useCallback(() => {
    const today = new Date()
    const year = today.getFullYear()
    const quarter = Math.floor(today.getMonth() / 3)
    const startMonth = quarter * 3 + 1
    const endMonth = startMonth + 2
    const lastDay = new Date(year, endMonth, 0).getDate()

    setFilters(prev => ({
      ...prev,
      dateDebut: `${year}-${String(startMonth).padStart(2, '0')}-01`,
      dateFin: `${year}-${String(endMonth).padStart(2, '0')}-${String(lastDay).padStart(2, '0')}`,
      annee: year
    }))
  }, [])

  /**
   * Retourne les filtres non-null pour les requêtes API
   */
  const getActiveFilters = useCallback(() => {
    const active = {}
    for (const [key, value] of Object.entries(filters)) {
      if (value !== null && value !== undefined && value !== '') {
        active[key] = value
      }
    }
    return active
  }, [filters])

  /**
   * Vérifie si des filtres sont actifs (autres que les dates par défaut)
   */
  const hasActiveFilters = useCallback(() => {
    const defaults = getDefaultFilters()
    return Object.keys(filters).some(key => {
      if (key === 'dateDebut' || key === 'dateFin' || key === 'annee') return false
      return filters[key] !== null && filters[key] !== defaults[key]
    })
  }, [filters])

  const value = {
    // État
    filters,

    // Actions simples
    updateFilter,
    updateFilters,
    resetFilters,

    // Raccourcis période
    setCurrentYear,
    setPreviousYear,
    setCurrentMonth,
    setCurrentQuarter,

    // Helpers
    getActiveFilters,
    hasActiveFilters
  }

  return (
    <GlobalFilterContext.Provider value={value}>
      {children}
    </GlobalFilterContext.Provider>
  )
}

/**
 * Hook pour utiliser les filtres globaux
 */
export function useGlobalFilters() {
  const context = useContext(GlobalFilterContext)
  if (!context) {
    throw new Error('useGlobalFilters doit être utilisé dans un GlobalFilterProvider')
  }
  return context
}

export default GlobalFilterContext
