import { createContext, useContext, useState, useEffect } from 'react'

const SettingsContext = createContext(null)

const defaultSettings = {
  // Format des nombres
  numberFormat: 'full', // 'full' = 1 000 000, 'abbreviated' = 1M, 'thousands' = 1 000K
  decimalPlaces: 2,
  thousandSeparator: ' ',
  decimalSeparator: ',',
  currencySymbol: 'DH',
  currencyPosition: 'after', // 'before' ou 'after'

  // Affichage des graphiques
  showLegend: true,
  legendPosition: 'bottom', // 'top', 'bottom', 'left', 'right'
  showGridLines: true,
  showDataLabels: false,
  chartAnimation: true,

  // Couleurs des graphiques
  chartColors: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'],
  positiveColor: '#10b981',
  negativeColor: '#ef4444',

  // Tableaux
  rowsPerPage: 25,
  showRowNumbers: true,
  highlightNegatives: true,
  alternateRowColors: true,
  compactMode: false,

  // KPI Cards
  showEvolution: true,
  showSparkline: true,
  kpiSize: 'medium', // 'small', 'medium', 'large'

  // Dates
  dateFormat: 'DD/MM/YYYY',

  // Exports
  exportFormat: 'xlsx', // 'xlsx', 'csv', 'pdf'
  includeHeaders: true,

  // Interface
  sidebarCollapsed: false,
  defaultPage: '/',
  refreshInterval: 0, // 0 = manuel, sinon en secondes

  // Sécurité
  watermarkEnabled: true, // Filigrane utilisateur (anti-copie/impression)
}

export function SettingsProvider({ children }) {
  const [settings, setSettings] = useState(() => {
    const saved = localStorage.getItem('appSettings')
    if (saved) {
      try {
        return { ...defaultSettings, ...JSON.parse(saved) }
      } catch (e) {
        return defaultSettings
      }
    }
    return defaultSettings
  })

  useEffect(() => {
    localStorage.setItem('appSettings', JSON.stringify(settings))
  }, [settings])

  const updateSettings = (newSettings) => {
    setSettings(prev => ({ ...prev, ...newSettings }))
  }

  const resetSettings = () => {
    setSettings(defaultSettings)
    localStorage.removeItem('appSettings')
  }

  // Fonction pour formater les nombres selon les paramètres
  const formatNumber = (value, options = {}) => {
    if (value === null || value === undefined || isNaN(value)) return '-'

    const num = parseFloat(value)
    const {
      format = settings.numberFormat,
      decimals = settings.decimalPlaces,
      showCurrency = false
    } = options

    let formatted

    if (format === 'abbreviated') {
      if (Math.abs(num) >= 1000000000) {
        formatted = (num / 1000000000).toFixed(decimals) + ' Mrd'
      } else if (Math.abs(num) >= 1000000) {
        formatted = (num / 1000000).toFixed(decimals) + ' M'
      } else if (Math.abs(num) >= 1000) {
        formatted = (num / 1000).toFixed(decimals) + ' K'
      } else {
        formatted = num.toFixed(decimals)
      }
    } else if (format === 'thousands') {
      formatted = (num / 1000).toFixed(decimals) + ' K'
    } else {
      // Format complet avec séparateurs
      const parts = num.toFixed(decimals).split('.')
      parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, settings.thousandSeparator)
      formatted = parts.join(settings.decimalSeparator)
    }

    if (showCurrency) {
      if (settings.currencyPosition === 'before') {
        formatted = settings.currencySymbol + ' ' + formatted
      } else {
        formatted = formatted + ' ' + settings.currencySymbol
      }
    }

    return formatted
  }

  // Fonction pour formater les pourcentages
  const formatPercent = (value, decimals = 1) => {
    if (value === null || value === undefined || isNaN(value)) return '-'
    return parseFloat(value).toFixed(decimals) + '%'
  }

  // Fonction pour formater les dates
  const formatDate = (dateStr) => {
    if (!dateStr) return '-'
    const date = new Date(dateStr)
    const format = settings.dateFormat

    const day = String(date.getDate()).padStart(2, '0')
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const year = date.getFullYear()

    return format
      .replace('DD', day)
      .replace('MM', month)
      .replace('YYYY', year)
  }

  return (
    <SettingsContext.Provider value={{
      settings,
      updateSettings,
      resetSettings,
      formatNumber,
      formatPercent,
      formatDate,
      defaultSettings
    }}>
      {children}
    </SettingsContext.Provider>
  )
}

export function useSettings() {
  const context = useContext(SettingsContext)
  if (!context) {
    throw new Error('useSettings must be used within a SettingsProvider')
  }
  return context
}
