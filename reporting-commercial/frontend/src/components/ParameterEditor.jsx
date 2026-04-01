import { useState, useEffect } from 'react'
import {
  X, Plus, Trash2, Save, Wand2, RefreshCw, Settings2,
  Calendar, Hash, Type, ToggleLeft, Globe, User, Lock
} from 'lucide-react'
import { getParameterConfig, extractParamsFromQuery, updateDataSource } from '../services/api'

const TYPE_ICONS = {
  string: Type,
  number: Hash,
  float: Hash,
  date: Calendar,
  boolean: ToggleLeft
}

const SOURCE_ICONS = {
  global: Globe,
  user: User,
  fixed: Lock
}

export default function ParameterEditor({ isOpen, onClose, dataSource, onSave }) {
  const [parameters, setParameters] = useState([])
  const [config, setConfig] = useState({
    macros: [],
    global_keys: [],
    types: [],
    sources: []
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [extracting, setExtracting] = useState(false)

  useEffect(() => {
    if (isOpen) {
      loadConfig()
      if (dataSource?.parameters) {
        setParameters(
          Array.isArray(dataSource.parameters)
            ? dataSource.parameters
            : []
        )
      } else {
        setParameters([])
      }
    }
  }, [isOpen, dataSource])

  const loadConfig = async () => {
    setLoading(true)
    try {
      const response = await getParameterConfig()
      if (response.data.success) {
        setConfig({
          macros: response.data.macros || [],
          global_keys: response.data.global_keys || [],
          types: response.data.types || [],
          sources: response.data.sources || []
        })
      }
    } catch (err) {
      console.error('Erreur chargement config:', err)
    } finally {
      setLoading(false)
    }
  }

  const extractParameters = async () => {
    if (!dataSource?.query_template) return

    setExtracting(true)
    try {
      const response = await extractParamsFromQuery(dataSource.query_template)
      if (response.data.success && response.data.parameters) {
        // Fusionner avec les paramètres existants
        const existing = new Set(parameters.map(p => p.name))
        const newParams = response.data.parameters.filter(p => !existing.has(p.name))
        setParameters([...parameters, ...newParams])
      }
    } catch (err) {
      console.error('Erreur extraction:', err)
    } finally {
      setExtracting(false)
    }
  }

  const addParameter = () => {
    setParameters([
      ...parameters,
      {
        name: '',
        type: 'string',
        label: '',
        required: false,
        source: 'user',
        global_key: null,
        default: null
      }
    ])
  }

  const updateParameter = (index, field, value) => {
    setParameters(parameters.map((p, i) => {
      if (i !== index) return p

      const updated = { ...p, [field]: value }

      // Auto-set global_key quand on passe en source global
      if (field === 'source' && value === 'global' && !updated.global_key) {
        // Chercher une correspondance dans les global_keys
        const match = config.global_keys.find(g =>
          updated.name.toLowerCase().includes(g.value.toLowerCase())
        )
        if (match) {
          updated.global_key = match.value
        }
      }

      // Auto-generate label from name
      if (field === 'name' && !updated.label) {
        updated.label = value.replace(/([A-Z])/g, ' $1').replace(/_/g, ' ').trim()
        updated.label = updated.label.charAt(0).toUpperCase() + updated.label.slice(1)
      }

      return updated
    }))
  }

  const removeParameter = (index) => {
    setParameters(parameters.filter((_, i) => i !== index))
  }

  const handleSave = async () => {
    if (!dataSource?.id) return

    setSaving(true)
    try {
      await updateDataSource(dataSource.id, {
        parameters: parameters
      })
      onSave && onSave(parameters)
      onClose()
    } catch (err) {
      console.error('Erreur sauvegarde:', err)
      alert('Erreur lors de la sauvegarde')
    } finally {
      setSaving(false)
    }
  }

  if (!isOpen) return null

  const SourceIcon = ({ source }) => {
    const Icon = SOURCE_ICONS[source] || User
    return <Icon className="w-4 h-4" />
  }

  const TypeIcon = ({ type }) => {
    const Icon = TYPE_ICONS[type] || Type
    return <Icon className="w-4 h-4" />
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />

      <div className="relative bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-[90vw] max-w-4xl max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <Settings2 className="w-5 h-5 text-primary-500" />
            <div>
              <h2 className="text-lg font-bold text-gray-900 dark:text-white">
                Configuration des Parametres
              </h2>
              <p className="text-sm text-gray-500">
                {dataSource?.nom || 'Source de donnees'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={extractParameters}
              disabled={extracting || !dataSource?.query_template}
              className="btn-secondary flex items-center gap-1 text-sm"
              title="Detecter automatiquement les @params dans la requete"
            >
              {extracting ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <Wand2 className="w-4 h-4" />
              )}
              Auto-detecter
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="btn-primary flex items-center gap-1 text-sm"
            >
              {saving ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <Save className="w-4 h-4" />
              )}
              Sauvegarder
            </button>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-4">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <RefreshCw className="w-8 h-8 animate-spin text-primary-500" />
            </div>
          ) : (
            <div className="space-y-4">
              {/* Info */}
              <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-sm text-blue-700 dark:text-blue-300">
                <p className="font-medium mb-1">Comment ca marche :</p>
                <ul className="list-disc list-inside space-y-1 text-xs">
                  <li><strong>Source Global</strong> : Le parametre est automatiquement rempli par les filtres globaux de l'application</li>
                  <li><strong>Source Utilisateur</strong> : L'utilisateur doit saisir la valeur</li>
                  <li><strong>Source Fixe</strong> : Valeur constante definie ici</li>
                  <li>Utilisez <code className="bg-blue-100 dark:bg-blue-800 px-1 rounded">@nomParametre</code> dans votre requete SQL</li>
                </ul>
              </div>

              {/* Parameters list */}
              {parameters.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <Settings2 className="w-12 h-12 mx-auto mb-3 opacity-30" />
                  <p>Aucun parametre configure</p>
                  <p className="text-sm mt-1">
                    Cliquez sur "Auto-detecter" ou "Ajouter" pour commencer
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {parameters.map((param, index) => (
                    <div
                      key={index}
                      className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-gray-200 dark:border-primary-600"
                    >
                      <div className="grid grid-cols-12 gap-3">
                        {/* Nom */}
                        <div className="col-span-2">
                          <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                            Nom (@param)
                          </label>
                          <input
                            type="text"
                            value={param.name}
                            onChange={(e) => updateParameter(index, 'name', e.target.value)}
                            placeholder="dateDebut"
                            className="w-full px-2 py-1.5 text-sm border border-primary-300 dark:border-primary-600 rounded dark:bg-gray-700 font-mono"
                          />
                        </div>

                        {/* Label */}
                        <div className="col-span-2">
                          <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                            Label
                          </label>
                          <input
                            type="text"
                            value={param.label}
                            onChange={(e) => updateParameter(index, 'label', e.target.value)}
                            placeholder="Date de debut"
                            className="w-full px-2 py-1.5 text-sm border border-primary-300 dark:border-primary-600 rounded dark:bg-gray-700"
                          />
                        </div>

                        {/* Type */}
                        <div className="col-span-2">
                          <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                            Type
                          </label>
                          <div className="relative">
                            <select
                              value={param.type}
                              onChange={(e) => updateParameter(index, 'type', e.target.value)}
                              className="w-full px-2 py-1.5 text-sm border border-primary-300 dark:border-primary-600 rounded dark:bg-gray-700 pl-8"
                            >
                              {config.types.map(t => (
                                <option key={t.value} value={t.value}>{t.label}</option>
                              ))}
                            </select>
                            <div className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-400">
                              <TypeIcon type={param.type} />
                            </div>
                          </div>
                        </div>

                        {/* Source */}
                        <div className="col-span-2">
                          <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                            Source
                          </label>
                          <div className="relative">
                            <select
                              value={param.source}
                              onChange={(e) => updateParameter(index, 'source', e.target.value)}
                              className="w-full px-2 py-1.5 text-sm border border-primary-300 dark:border-primary-600 rounded dark:bg-gray-700 pl-8"
                            >
                              {config.sources.map(s => (
                                <option key={s.value} value={s.value}>{s.label}</option>
                              ))}
                            </select>
                            <div className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-400">
                              <SourceIcon source={param.source} />
                            </div>
                          </div>
                        </div>

                        {/* Global Key (si source = global) */}
                        {param.source === 'global' && (
                          <div className="col-span-2">
                            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                              Cle globale
                            </label>
                            <select
                              value={param.global_key || ''}
                              onChange={(e) => updateParameter(index, 'global_key', e.target.value || null)}
                              className="w-full px-2 py-1.5 text-sm border border-primary-300 dark:border-primary-600 rounded dark:bg-gray-700"
                            >
                              <option value="">-- Choisir --</option>
                              {config.global_keys.map(g => (
                                <option key={g.value} value={g.value}>{g.label}</option>
                              ))}
                            </select>
                          </div>
                        )}

                        {/* Default (si source = fixed ou user) */}
                        {(param.source === 'fixed' || param.source === 'user') && (
                          <div className="col-span-2">
                            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                              {param.source === 'fixed' ? 'Valeur' : 'Defaut'}
                            </label>
                            {param.type === 'date' ? (
                              <select
                                value={param.default || ''}
                                onChange={(e) => updateParameter(index, 'default', e.target.value || null)}
                                className="w-full px-2 py-1.5 text-sm border border-primary-300 dark:border-primary-600 rounded dark:bg-gray-700"
                              >
                                <option value="">-- Aucun --</option>
                                {config.macros.map(m => (
                                  <option key={m.value} value={m.value}>{m.label}</option>
                                ))}
                              </select>
                            ) : (
                              <input
                                type={param.type === 'number' || param.type === 'float' ? 'number' : 'text'}
                                value={param.default || ''}
                                onChange={(e) => updateParameter(index, 'default', e.target.value || null)}
                                placeholder="Valeur..."
                                className="w-full px-2 py-1.5 text-sm border border-primary-300 dark:border-primary-600 rounded dark:bg-gray-700"
                              />
                            )}
                          </div>
                        )}

                        {/* Required + Delete */}
                        <div className="col-span-2 flex items-end gap-2">
                          <label className="flex items-center gap-1.5 text-sm cursor-pointer">
                            <input
                              type="checkbox"
                              checked={param.required}
                              onChange={(e) => updateParameter(index, 'required', e.target.checked)}
                              className="rounded border-primary-300 text-primary-600 focus:ring-primary-500"
                            />
                            <span className="text-gray-600 dark:text-gray-400">Requis</span>
                          </label>
                          <button
                            onClick={() => removeParameter(index)}
                            className="p-1.5 hover:bg-red-100 dark:hover:bg-red-900/30 rounded text-red-500"
                            title="Supprimer"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Add button */}
              <button
                onClick={addParameter}
                className="w-full py-2 border-2 border-dashed border-primary-300 dark:border-primary-600 rounded-lg text-gray-500 hover:border-primary-500 hover:text-primary-500 transition-colors flex items-center justify-center gap-2"
              >
                <Plus className="w-4 h-4" />
                Ajouter un parametre
              </button>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
          <div className="flex items-center justify-between text-xs text-gray-500">
            <span>{parameters.length} parametre(s) configure(s)</span>
            <span>Les parametres @global sont automatiquement remplis par les filtres</span>
          </div>
        </div>
      </div>
    </div>
  )
}
