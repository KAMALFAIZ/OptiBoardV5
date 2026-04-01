import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Settings as SettingsIcon,
  Hash,
  BarChart3,
  Table,
  CreditCard,
  Calendar,
  Download,
  Monitor,
  RotateCcw,
  Save,
  Check,
  Palette,
  Bot,
  Loader2,
  CheckCircle,
  XCircle
} from 'lucide-react'
import { useSettings } from '../context/SettingsContext'
import api from '../services/api'

const tabs = [
  { id: 'numbers', name: 'Nombres', icon: Hash },
  { id: 'charts', name: 'Graphiques', icon: BarChart3 },
  { id: 'tables', name: 'Tableaux', icon: Table },
  { id: 'kpi', name: 'KPI', icon: CreditCard },
  { id: 'dates', name: 'Dates', icon: Calendar },
  { id: 'export', name: 'Export', icon: Download },
  { id: 'interface', name: 'Interface', icon: Monitor },
  { id: 'ai', name: 'Intelligence Artificielle', icon: Bot },
]

export default function Settings() {
  const { settings, updateSettings, resetSettings, formatNumber, defaultSettings } = useSettings()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('numbers')
  const [saved, setSaved] = useState(false)

  // AI Configuration state
  const [aiConfig, setAiConfig] = useState({
    AI_PROVIDER: '',
    AI_MODEL: '',
    AI_API_KEY: '',
    AI_OLLAMA_URL: 'http://localhost:11434',
    AI_MAX_TOKENS: 4096,
    AI_TEMPERATURE: 0.2,
    AI_ENABLED: false,
    AI_RATE_LIMIT_PER_MINUTE: 20,
  })
  const [aiLoading, setAiLoading] = useState(false)
  const [aiSaving, setAiSaving] = useState(false)
  const [aiTestResult, setAiTestResult] = useState(null)
  const [aiTesting, setAiTesting] = useState(false)

  // Load AI config on tab switch
  useEffect(() => {
    if (activeTab === 'ai') {
      setAiLoading(true)
      api.get('/setup/ai-config')
        .then(res => {
          if (res.data.success) setAiConfig(res.data.config)
        })
        .catch(() => {})
        .finally(() => setAiLoading(false))
    }
  }, [activeTab])

  const handleAiChange = (key, value) => {
    setAiConfig(prev => ({ ...prev, [key]: value }))
    setAiTestResult(null)
  }

  const handleAiSave = async () => {
    setAiSaving(true)
    try {
      await api.post('/setup/ai-config', aiConfig)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (e) {
      alert('Erreur lors de la sauvegarde: ' + (e.response?.data?.detail || e.message))
    } finally {
      setAiSaving(false)
    }
  }

  const handleAiTest = async () => {
    setAiTesting(true)
    setAiTestResult(null)
    try {
      // Save first, then test
      await api.post('/setup/ai-config', aiConfig)
      const res = await api.post('/ai/test-provider')
      setAiTestResult(res.data)
    } catch (e) {
      setAiTestResult({ success: false, error: e.response?.data?.detail || e.message })
    } finally {
      setAiTesting(false)
    }
  }

  const providerModels = {
    openai: ['gpt-4o', 'gpt-4-turbo', 'gpt-4o-mini', 'gpt-3.5-turbo'],
    anthropic: ['claude-sonnet-4-5-20250929', 'claude-opus-4-6', 'claude-haiku-4-5-20251001'],
    ollama: ['llama3.2', 'mistral', 'codellama', 'mixtral'],
  }

  const handleChange = (key, value) => {
    updateSettings({ [key]: value })
  }

  const handleSave = () => {
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const handleReset = () => {
    if (confirm('Voulez-vous vraiment reinitialiser tous les parametres ?')) {
      resetSettings()
    }
  }

  const previewNumber = 1234567.89

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <SettingsIcon className="w-8 h-8 text-theme-primary" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Parametres</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">Configurez l'affichage de l'application</p>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleReset}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-primary-300 dark:border-primary-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
          >
            <RotateCcw className="w-4 h-4" />
            Reinitialiser
          </button>
          <button
            onClick={handleSave}
            className="btn-primary flex items-center gap-2"
          >
            {saved ? <Check className="w-4 h-4" /> : <Save className="w-4 h-4" />}
            {saved ? 'Enregistre !' : 'Enregistrer'}
          </button>
        </div>
      </div>

      <div className="flex gap-6">
        {/* Tabs sidebar */}
        <div className="w-56 flex-shrink-0">
          <nav className="space-y-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-lg transition-colors ${
                  activeTab === tab.id
                    ? 'tab-active'
                    : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
                }`}
                style={activeTab === tab.id ? { backgroundColor: 'var(--color-primary-100)', color: 'var(--color-primary-700)' } : {}}
              >
                <tab.icon className="w-5 h-5" />
                {tab.name}
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1 bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          {/* Numbers Tab */}
          {activeTab === 'numbers' && (
            <div className="space-y-6">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                <Hash className="w-5 h-5" />
                Format des nombres
              </h2>

              {/* Preview */}
              <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">Apercu:</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {formatNumber(previewNumber, { showCurrency: true })}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Format d'affichage
                  </label>
                  <select
                    value={settings.numberFormat}
                    onChange={(e) => handleChange('numberFormat', e.target.value)}
                    className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  >
                    <option value="full">Complet (1 234 567,89)</option>
                    <option value="abbreviated">Abrege (1,23 M)</option>
                    <option value="thousands">En milliers (1 234,57 K)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Decimales
                  </label>
                  <select
                    value={settings.decimalPlaces}
                    onChange={(e) => handleChange('decimalPlaces', parseInt(e.target.value))}
                    className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  >
                    <option value={0}>0 decimales</option>
                    <option value={1}>1 decimale</option>
                    <option value={2}>2 decimales</option>
                    <option value={3}>3 decimales</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Separateur des milliers
                  </label>
                  <select
                    value={settings.thousandSeparator}
                    onChange={(e) => handleChange('thousandSeparator', e.target.value)}
                    className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  >
                    <option value=" ">Espace ( )</option>
                    <option value=",">Virgule (,)</option>
                    <option value=".">Point (.)</option>
                    <option value="'">Apostrophe (')</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Separateur decimal
                  </label>
                  <select
                    value={settings.decimalSeparator}
                    onChange={(e) => handleChange('decimalSeparator', e.target.value)}
                    className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  >
                    <option value=",">Virgule (,)</option>
                    <option value=".">Point (.)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Symbole de devise
                  </label>
                  <input
                    type="text"
                    value={settings.currencySymbol}
                    onChange={(e) => handleChange('currencySymbol', e.target.value)}
                    className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Position de la devise
                  </label>
                  <select
                    value={settings.currencyPosition}
                    onChange={(e) => handleChange('currencyPosition', e.target.value)}
                    className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  >
                    <option value="after">Apres (1 234 DH)</option>
                    <option value="before">Avant (DH 1 234)</option>
                  </select>
                </div>
              </div>
            </div>
          )}

          {/* Charts Tab */}
          {activeTab === 'charts' && (
            <div className="space-y-6">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                <BarChart3 className="w-5 h-5" />
                Graphiques
              </h2>

              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                  <div>
                    <p className="font-medium text-gray-900 dark:text-white">Afficher la legende</p>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Affiche les legendes sur les graphiques</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.showLegend}
                      onChange={(e) => handleChange('showLegend', e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-primary-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-primary-600 peer-checked:bg-primary-600"></div>
                  </label>
                </div>

                {settings.showLegend && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Position de la legende
                    </label>
                    <select
                      value={settings.legendPosition}
                      onChange={(e) => handleChange('legendPosition', e.target.value)}
                      className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    >
                      <option value="top">En haut</option>
                      <option value="bottom">En bas</option>
                      <option value="left">A gauche</option>
                      <option value="right">A droite</option>
                    </select>
                  </div>
                )}

                <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                  <div>
                    <p className="font-medium text-gray-900 dark:text-white">Lignes de grille</p>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Affiche les lignes de grille</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.showGridLines}
                      onChange={(e) => handleChange('showGridLines', e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-primary-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-primary-600 peer-checked:bg-primary-600"></div>
                  </label>
                </div>

                <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                  <div>
                    <p className="font-medium text-gray-900 dark:text-white">Etiquettes de donnees</p>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Affiche les valeurs sur les barres/points</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.showDataLabels}
                      onChange={(e) => handleChange('showDataLabels', e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-primary-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-primary-600 peer-checked:bg-primary-600"></div>
                  </label>
                </div>

                <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                  <div>
                    <p className="font-medium text-gray-900 dark:text-white">Animations</p>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Active les animations des graphiques</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.chartAnimation}
                      onChange={(e) => handleChange('chartAnimation', e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-primary-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-primary-600 peer-checked:bg-primary-600"></div>
                  </label>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 flex items-center gap-2">
                    <Palette className="w-4 h-4" />
                    Couleurs des graphiques
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {settings.chartColors.map((color, index) => (
                      <input
                        key={index}
                        type="color"
                        value={color}
                        onChange={(e) => {
                          const newColors = [...settings.chartColors]
                          newColors[index] = e.target.value
                          handleChange('chartColors', newColors)
                        }}
                        className="w-10 h-10 rounded-lg border border-primary-300 dark:border-primary-600 cursor-pointer"
                      />
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Couleur positive
                    </label>
                    <div className="flex items-center gap-2">
                      <input
                        type="color"
                        value={settings.positiveColor}
                        onChange={(e) => handleChange('positiveColor', e.target.value)}
                        className="w-10 h-10 rounded-lg border border-primary-300 dark:border-primary-600 cursor-pointer"
                      />
                      <span className="text-sm text-gray-500">{settings.positiveColor}</span>
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Couleur negative
                    </label>
                    <div className="flex items-center gap-2">
                      <input
                        type="color"
                        value={settings.negativeColor}
                        onChange={(e) => handleChange('negativeColor', e.target.value)}
                        className="w-10 h-10 rounded-lg border border-primary-300 dark:border-primary-600 cursor-pointer"
                      />
                      <span className="text-sm text-gray-500">{settings.negativeColor}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Tables Tab */}
          {activeTab === 'tables' && (
            <div className="space-y-6">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                <Table className="w-5 h-5" />
                Tableaux
              </h2>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Lignes par page
                  </label>
                  <select
                    value={settings.rowsPerPage}
                    onChange={(e) => handleChange('rowsPerPage', parseInt(e.target.value))}
                    className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  >
                    <option value={10}>10 lignes</option>
                    <option value={25}>25 lignes</option>
                    <option value={50}>50 lignes</option>
                    <option value={100}>100 lignes</option>
                  </select>
                </div>

                <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                  <div>
                    <p className="font-medium text-gray-900 dark:text-white">Numeros de ligne</p>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Affiche les numeros de ligne</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.showRowNumbers}
                      onChange={(e) => handleChange('showRowNumbers', e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-primary-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-primary-600 peer-checked:bg-primary-600"></div>
                  </label>
                </div>

                <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                  <div>
                    <p className="font-medium text-gray-900 dark:text-white">Surligner les negatifs</p>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Met en rouge les valeurs negatives</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.highlightNegatives}
                      onChange={(e) => handleChange('highlightNegatives', e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-primary-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-primary-600 peer-checked:bg-primary-600"></div>
                  </label>
                </div>

                <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                  <div>
                    <p className="font-medium text-gray-900 dark:text-white">Lignes alternees</p>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Alterne les couleurs de fond des lignes</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.alternateRowColors}
                      onChange={(e) => handleChange('alternateRowColors', e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-primary-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-primary-600 peer-checked:bg-primary-600"></div>
                  </label>
                </div>

                <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                  <div>
                    <p className="font-medium text-gray-900 dark:text-white">Mode compact</p>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Reduit l'espacement dans les tableaux</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.compactMode}
                      onChange={(e) => handleChange('compactMode', e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-primary-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-primary-600 peer-checked:bg-primary-600"></div>
                  </label>
                </div>
              </div>
            </div>
          )}

          {/* KPI Tab */}
          {activeTab === 'kpi' && (
            <div className="space-y-6">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                <CreditCard className="w-5 h-5" />
                Cartes KPI
              </h2>

              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                  <div>
                    <p className="font-medium text-gray-900 dark:text-white">Afficher l'evolution</p>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Affiche le pourcentage d'evolution</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.showEvolution}
                      onChange={(e) => handleChange('showEvolution', e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-primary-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-primary-600 peer-checked:bg-primary-600"></div>
                  </label>
                </div>

                <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                  <div>
                    <p className="font-medium text-gray-900 dark:text-white">Mini graphique (Sparkline)</p>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Affiche un mini graphique de tendance</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.showSparkline}
                      onChange={(e) => handleChange('showSparkline', e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-primary-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-primary-600 peer-checked:bg-primary-600"></div>
                  </label>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Taille des cartes KPI
                  </label>
                  <select
                    value={settings.kpiSize}
                    onChange={(e) => handleChange('kpiSize', e.target.value)}
                    className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  >
                    <option value="small">Petite</option>
                    <option value="medium">Moyenne</option>
                    <option value="large">Grande</option>
                  </select>
                </div>
              </div>
            </div>
          )}

          {/* Dates Tab */}
          {activeTab === 'dates' && (
            <div className="space-y-6">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                <Calendar className="w-5 h-5" />
                Format des dates
              </h2>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Format de date
                </label>
                <select
                  value={settings.dateFormat}
                  onChange={(e) => handleChange('dateFormat', e.target.value)}
                  className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                >
                  <option value="DD/MM/YYYY">DD/MM/YYYY (31/12/2025)</option>
                  <option value="MM/DD/YYYY">MM/DD/YYYY (12/31/2025)</option>
                  <option value="YYYY-MM-DD">YYYY-MM-DD (2025-12-31)</option>
                  <option value="DD-MM-YYYY">DD-MM-YYYY (31-12-2025)</option>
                </select>
              </div>

              <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">Apercu:</p>
                <p className="text-lg font-medium text-gray-900 dark:text-white">
                  {settings.dateFormat.replace('DD', '31').replace('MM', '12').replace('YYYY', '2025')}
                </p>
              </div>
            </div>
          )}

          {/* Export Tab */}
          {activeTab === 'export' && (
            <div className="space-y-6">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                <Download className="w-5 h-5" />
                Options d'export
              </h2>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Format d'export par defaut
                  </label>
                  <select
                    value={settings.exportFormat}
                    onChange={(e) => handleChange('exportFormat', e.target.value)}
                    className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  >
                    <option value="xlsx">Excel (.xlsx)</option>
                    <option value="csv">CSV (.csv)</option>
                    <option value="pdf">PDF (.pdf)</option>
                  </select>
                </div>

                <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                  <div>
                    <p className="font-medium text-gray-900 dark:text-white">Inclure les en-tetes</p>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Ajoute les noms de colonnes dans l'export</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.includeHeaders}
                      onChange={(e) => handleChange('includeHeaders', e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-primary-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-primary-600 peer-checked:bg-primary-600"></div>
                  </label>
                </div>
              </div>
            </div>
          )}

          {/* Interface Tab */}
          {activeTab === 'interface' && (
            <div className="space-y-6">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                <Monitor className="w-5 h-5" />
                Interface
              </h2>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Page par defaut
                  </label>
                  <select
                    value={settings.defaultPage}
                    onChange={(e) => handleChange('defaultPage', e.target.value)}
                    className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  >
                    <option value="/">Dashboard</option>
                    <option value="/ventes">Ventes</option>
                    <option value="/stocks">Stocks</option>
                    <option value="/recouvrement">Recouvrement</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Rafraichissement automatique
                  </label>
                  <select
                    value={settings.refreshInterval}
                    onChange={(e) => handleChange('refreshInterval', parseInt(e.target.value))}
                    className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  >
                    <option value={0}>Manuel uniquement</option>
                    <option value={30}>Toutes les 30 secondes</option>
                    <option value={60}>Toutes les minutes</option>
                    <option value={300}>Toutes les 5 minutes</option>
                    <option value={600}>Toutes les 10 minutes</option>
                  </select>
                </div>

                <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                  <div>
                    <p className="font-medium text-gray-900 dark:text-white">Menu reduit par defaut</p>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Demarre avec le menu lateral reduit</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.sidebarCollapsed}
                      onChange={(e) => handleChange('sidebarCollapsed', e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-primary-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-primary-600 peer-checked:bg-primary-600"></div>
                  </label>
                </div>

                <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                  <div>
                    <p className="font-medium text-gray-900 dark:text-white">Filigrane de protection</p>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Affiche le nom de l'utilisateur en filigrane (protection contre la copie et l'impression)
                    </p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.watermarkEnabled ?? true}
                      onChange={(e) => handleChange('watermarkEnabled', e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-primary-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-primary-600 peer-checked:bg-primary-600"></div>
                  </label>
                </div>
              </div>
            </div>
          )}

          {/* AI Tab */}
          {activeTab === 'ai' && (
            <div className="space-y-6">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                <Bot className="w-5 h-5" />
                Intelligence Artificielle
              </h2>
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <div className="w-16 h-16 rounded-2xl bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center mb-4">
                  <Bot className="w-8 h-8 text-primary-600 dark:text-primary-400" />
                </div>
                <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-1">
                  Configuration déplacée
                </h3>
                <p className="text-sm text-gray-500 dark:text-gray-400 mb-6 max-w-sm">
                  La configuration de l'API IA (clé, fournisseur, modèle) est désormais
                  gérée depuis la page <strong>IA Learning</strong>.
                </p>
                <button
                  onClick={() => navigate('/admin/ai-library')}
                  className="flex items-center gap-2 px-5 py-2.5 text-sm font-medium bg-primary-600 hover:bg-primary-700 text-white rounded-xl transition-colors shadow-sm"
                >
                  <Bot className="w-4 h-4" />
                  Aller à IA Learning
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
