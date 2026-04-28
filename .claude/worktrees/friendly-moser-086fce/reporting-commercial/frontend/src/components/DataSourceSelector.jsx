/**
 * DataSourceSelector - Composant de selection de DataSource Template
 * ===================================================================
 * Affiche une liste groupee par categorie des DataSources disponibles
 * (Templates centraux + Sources locales)
 *
 * Props:
 * - value: ID ou code de la datasource selectionnee
 * - onChange: (datasource) => void - callback quand une selection change
 * - onPreview: (datasource) => void - callback pour previsualiser
 * - showPreview: boolean - afficher le bouton preview
 * - category: string - filtrer par categorie
 * - className: string - classes CSS additionnelles
 */

import { useState, useEffect, useMemo } from 'react'
import {
  Database, ChevronDown, ChevronRight, Search, RefreshCw,
  Eye, Settings2, Layers, FileText, Tag, Loader2, Check
} from 'lucide-react'
import { getUnifiedDataSources } from '../services/api'

// Categories predefinies avec icones et couleurs
const CATEGORY_CONFIG = {
  'Ventes': { icon: FileText, color: 'text-blue-500', bg: 'bg-blue-50 dark:bg-blue-900/20' },
  'Stocks': { icon: Layers, color: 'text-green-500', bg: 'bg-green-50 dark:bg-green-900/20' },
  'Recouvrement': { icon: Tag, color: 'text-orange-500', bg: 'bg-orange-50 dark:bg-orange-900/20' },
  'Dashboard': { icon: Database, color: 'text-purple-500', bg: 'bg-purple-50 dark:bg-purple-900/20' },
  'RH': { icon: FileText, color: 'text-pink-500', bg: 'bg-pink-50 dark:bg-pink-900/20' },
  'Finance': { icon: FileText, color: 'text-emerald-500', bg: 'bg-emerald-50 dark:bg-emerald-900/20' },
  'custom': { icon: Settings2, color: 'text-gray-500', bg: 'bg-gray-50 dark:bg-gray-900/20' },
  'Autre': { icon: Database, color: 'text-slate-500', bg: 'bg-slate-50 dark:bg-slate-900/20' }
}

export default function DataSourceSelector({
  value,
  onChange,
  onPreview,
  showPreview = true,
  category = null,
  className = '',
  placeholder = 'Sélectionner une source de données...'
}) {
  const [loading, setLoading] = useState(true)
  const [dataSources, setDataSources] = useState([])
  const [grouped, setGrouped] = useState({})
  const [searchTerm, setSearchTerm] = useState('')
  const [expandedCategories, setExpandedCategories] = useState({})
  const [isOpen, setIsOpen] = useState(false)
  const [error, setError] = useState(null)

  // Charger les datasources
  useEffect(() => {
    loadDataSources()
  }, [category])

  const loadDataSources = async () => {
    setLoading(true)
    setError(null)
    try {
      const params = {}
      if (category) params.category = category

      const response = await getUnifiedDataSources(params)

      if (response.data.success) {
        setDataSources(response.data.data || [])
        setGrouped(response.data.grouped || {})

        // Ouvrir toutes les categories par defaut
        const cats = {}
        Object.keys(response.data.grouped || {}).forEach(c => { cats[c] = true })
        setExpandedCategories(cats)
      } else {
        setError(response.data.error || 'Erreur de chargement')
      }
    } catch (err) {
      console.error('Erreur chargement datasources:', err)
      setError('Erreur de connexion au serveur')
    } finally {
      setLoading(false)
    }
  }

  // Filtrer par recherche
  const filteredGrouped = useMemo(() => {
    if (!searchTerm) return grouped

    const filtered = {}
    Object.entries(grouped).forEach(([cat, sources]) => {
      const matching = sources.filter(ds =>
        ds.nom?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        ds.code?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        ds.description?.toLowerCase().includes(searchTerm.toLowerCase())
      )
      if (matching.length > 0) {
        filtered[cat] = matching
      }
    })
    return filtered
  }, [grouped, searchTerm])

  // Trouver la datasource selectionnee
  const selectedDataSource = useMemo(() => {
    if (!value) return null
    return dataSources.find(ds =>
      ds.id === value || ds.code === value || ds.id?.toString() === value?.toString()
    )
  }, [value, dataSources])

  const toggleCategory = (cat) => {
    setExpandedCategories(prev => ({ ...prev, [cat]: !prev[cat] }))
  }

  const handleSelect = (datasource) => {
    onChange?.(datasource)
    setIsOpen(false)
    setSearchTerm('')
  }

  const getCategoryConfig = (cat) => {
    return CATEGORY_CONFIG[cat] || CATEGORY_CONFIG['Autre']
  }

  return (
    <div className={`relative ${className}`}>
      {/* Bouton de selection */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={`
          w-full flex items-center justify-between px-4 py-3
          border border-primary-300 dark:border-primary-600 rounded-lg
          bg-white dark:bg-gray-800
          hover:border-primary-400 dark:hover:border-primary-500
          focus:ring-2 focus:ring-primary-500 focus:border-primary-500
          transition-all duration-150
          ${isOpen ? 'ring-2 ring-primary-500 border-primary-500' : ''}
        `}
      >
        <div className="flex items-center gap-3 min-w-0">
          <Database className={`w-5 h-5 flex-shrink-0 ${selectedDataSource ? 'text-primary-500' : 'text-gray-400'}`} />

          {selectedDataSource ? (
            <div className="flex flex-col items-start min-w-0">
              <span className="font-medium text-gray-900 dark:text-white truncate">
                {selectedDataSource.nom}
              </span>
              <span className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-2">
                <code className="bg-gray-100 dark:bg-gray-700 px-1 rounded">{selectedDataSource.code}</code>
                {selectedDataSource.origin === 'template' && (
                  <span className="text-primary-500 flex items-center gap-1">
                    <Settings2 className="w-3 h-3" />
                    Template
                  </span>
                )}
              </span>
            </div>
          ) : (
            <span className="text-gray-500 dark:text-gray-400">{placeholder}</span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {showPreview && selectedDataSource && (
            <span
              role="button"
              tabIndex={0}
              onClick={(e) => {
                e.stopPropagation()
                onPreview?.(selectedDataSource)
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.stopPropagation()
                  onPreview?.(selectedDataSource)
                }
              }}
              className="p-1.5 text-gray-400 hover:text-primary-500 hover:bg-gray-100 dark:hover:bg-gray-700 rounded cursor-pointer"
              title="Prévisualiser"
            >
              <Eye className="w-4 h-4" />
            </span>
          )}
          <ChevronDown className={`w-5 h-5 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        </div>
      </button>

      {/* Dropdown */}
      {isOpen && (
        <>
          {/* Overlay pour fermer */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />

          <div className="absolute top-full left-0 right-0 mt-1 z-50 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-xl max-h-[400px] flex flex-col">
            {/* Barre de recherche */}
            <div className="p-3 border-b border-gray-200 dark:border-gray-700">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Rechercher une source..."
                  className="w-full pl-9 pr-8 py-2 text-sm border border-primary-300 dark:border-primary-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-primary-500"
                  autoFocus
                />
                {loading && (
                  <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 animate-spin" />
                )}
                {!loading && (
                  <button
                    type="button"
                    onClick={loadDataSources}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-primary-500"
                  >
                    <RefreshCw className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>

            {/* Liste des datasources */}
            <div className="flex-1 overflow-y-auto">
              {error ? (
                <div className="p-4 text-center text-red-500">
                  <p>{error}</p>
                  <button
                    onClick={loadDataSources}
                    className="mt-2 text-sm text-primary-500 hover:underline"
                  >
                    Réessayer
                  </button>
                </div>
              ) : loading ? (
                <div className="p-8 text-center">
                  <Loader2 className="w-8 h-8 animate-spin text-primary-500 mx-auto" />
                  <p className="mt-2 text-sm text-gray-500">Chargement...</p>
                </div>
              ) : Object.keys(filteredGrouped).length === 0 ? (
                <div className="p-8 text-center text-gray-500">
                  <Database className="w-12 h-12 mx-auto mb-2 opacity-30" />
                  <p>Aucune source trouvée</p>
                </div>
              ) : (
                Object.entries(filteredGrouped).map(([cat, sources]) => {
                  const config = getCategoryConfig(cat)
                  const CategoryIcon = config.icon

                  return (
                    <div key={cat} className="border-b border-gray-100 dark:border-gray-700 last:border-b-0">
                      {/* Header de categorie */}
                      <button
                        type="button"
                        onClick={() => toggleCategory(cat)}
                        className={`w-full px-4 py-2 flex items-center justify-between text-sm font-medium hover:bg-gray-50 dark:hover:bg-gray-700 ${config.bg}`}
                      >
                        <span className={`flex items-center gap-2 ${config.color}`}>
                          {expandedCategories[cat] ? (
                            <ChevronDown className="w-4 h-4" />
                          ) : (
                            <ChevronRight className="w-4 h-4" />
                          )}
                          <CategoryIcon className="w-4 h-4" />
                          {cat}
                        </span>
                        <span className="text-xs bg-gray-200 dark:bg-gray-600 px-2 py-0.5 rounded-full text-gray-600 dark:text-gray-300">
                          {sources.length}
                        </span>
                      </button>

                      {/* Liste des sources dans la categorie */}
                      {expandedCategories[cat] && (
                        <div className="py-1">
                          {sources.map(ds => {
                            const isSelected = selectedDataSource?.id === ds.id ||
                              selectedDataSource?.code === ds.code

                            return (
                              <button
                                key={ds.id || ds.code}
                                type="button"
                                onClick={() => handleSelect(ds)}
                                className={`
                                  w-full px-4 py-2 flex items-center gap-3 text-left
                                  hover:bg-gray-50 dark:hover:bg-gray-700
                                  ${isSelected ? 'bg-primary-50 dark:bg-primary-900/20' : ''}
                                `}
                              >
                                {/* Indicateur de selection */}
                                <div className={`w-5 h-5 flex items-center justify-center rounded-full border ${
                                  isSelected
                                    ? 'bg-primary-500 border-primary-500 text-white'
                                    : 'border-primary-300 dark:border-primary-600'
                                }`}>
                                  {isSelected && <Check className="w-3 h-3" />}
                                </div>

                                {/* Infos de la source */}
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-2">
                                    <span className={`font-medium truncate ${isSelected ? 'text-primary-700 dark:text-primary-400' : 'text-gray-900 dark:text-white'}`}>
                                      {ds.nom}
                                    </span>
                                    {ds.origin === 'template' && (
                                      <span className="text-xs bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 px-1.5 py-0.5 rounded">
                                        Template
                                      </span>
                                    )}
                                    {ds.is_system && (
                                      <Settings2 className="w-3 h-3 text-amber-500" title="Système" />
                                    )}
                                  </div>
                                  <div className="flex items-center gap-2 mt-0.5">
                                    <code className="text-xs text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 px-1 rounded truncate">
                                      {ds.code}
                                    </code>
                                    {ds.description && (
                                      <span className="text-xs text-gray-400 truncate">
                                        {ds.description.substring(0, 50)}...
                                      </span>
                                    )}
                                  </div>
                                </div>
                              </button>
                            )
                          })}
                        </div>
                      )}
                    </div>
                  )
                })
              )}
            </div>

            {/* Footer avec stats */}
            <div className="px-4 py-2 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50 text-xs text-gray-500">
              <span>{dataSources.length} sources disponibles</span>
              {searchTerm && (
                <span className="ml-2">
                  ({Object.values(filteredGrouped).flat().length} résultats)
                </span>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
