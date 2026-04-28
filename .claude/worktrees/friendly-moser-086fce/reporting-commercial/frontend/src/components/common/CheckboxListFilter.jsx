import React, { useState, useMemo } from 'react'
import { Search, Check, CheckSquare, Square, Loader2 } from 'lucide-react'

/**
 * Composant de filtre avec liste de cases à cocher
 * Similaire au design "Liste à cocher" avec options avancées
 *
 * Props:
 * - options: Array<{value, label}> - Liste des options
 * - value: Array<string> - Valeurs sélectionnées
 * - onChange: (values: string[]) => void - Callback de changement
 * - loading: boolean - État de chargement
 * - allowNull: boolean - Autoriser la valeur nulle (tous)
 * - nullLabel: string - Label pour l'option "tous"
 * - label: string - Label du filtre
 * - searchable: boolean - Activer la recherche
 * - maxHeight: number - Hauteur max de la liste (px)
 */
export default function CheckboxListFilter({
  options = [],
  value = [],
  onChange,
  loading = false,
  allowNull = true,
  nullLabel = '(Toutes)',
  label = 'Filtre',
  searchable = true,
  maxHeight = 200
}) {
  const [searchTerm, setSearchTerm] = useState('')

  // Filtrer les options selon la recherche
  const filteredOptions = useMemo(() => {
    if (!searchTerm.trim()) return options
    const search = searchTerm.toLowerCase()
    return options.filter(opt =>
      opt.label?.toLowerCase().includes(search) ||
      opt.value?.toLowerCase().includes(search)
    )
  }, [options, searchTerm])

  // Vérifier si tout est sélectionné
  const allSelected = useMemo(() => {
    if (!options.length) return false
    const nonNullOptions = options.filter(o => o.value)
    return nonNullOptions.every(opt => value.includes(opt.value))
  }, [options, value])

  // Vérifier si rien n'est sélectionné (= tous)
  const noneSelected = value.length === 0

  // Sélectionner/Désélectionner tout
  const toggleAll = () => {
    if (allSelected) {
      onChange([]) // Désélectionner tout = Tous
    } else {
      const allValues = options.filter(o => o.value).map(o => o.value)
      onChange(allValues)
    }
  }

  // Sélectionner "Tous" (valeur nulle)
  const selectAll = () => {
    onChange([])
  }

  // Toggle une option
  const toggleOption = (optValue) => {
    if (!optValue) {
      // Option "Tous" cliquée
      selectAll()
      return
    }

    const newValue = value.includes(optValue)
      ? value.filter(v => v !== optValue)
      : [...value, optValue]

    onChange(newValue)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-4 text-gray-500">
        <Loader2 className="w-5 h-5 animate-spin mr-2" />
        <span className="text-sm">Chargement...</span>
      </div>
    )
  }

  return (
    <div className="w-full">
      {/* Barre de recherche */}
      {searchable && options.length > 5 && (
        <div className="relative mb-2">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Rechercher..."
            className="w-full pl-8 pr-3 py-1.5 text-sm border border-primary-300 dark:border-primary-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-700 dark:text-white"
          />
        </div>
      )}

      {/* Options rapides */}
      <div className="flex items-center gap-3 mb-2 text-xs">
        <button
          type="button"
          onClick={toggleAll}
          className="text-primary-600 hover:text-primary-700 dark:text-primary-400 hover:underline flex items-center gap-1"
        >
          <CheckSquare className="w-3 h-3" />
          {allSelected ? 'Désélectionner tout' : 'Sélectionner tout'}
        </button>
        {value.length > 0 && (
          <span className="text-gray-500">
            ({value.length} sélectionné{value.length > 1 ? 's' : ''})
          </span>
        )}
      </div>

      {/* Liste des options avec cases à cocher */}
      <div
        className="border border-primary-300 dark:border-primary-600 rounded-lg overflow-hidden bg-white dark:bg-gray-800"
        style={{ maxHeight: `${maxHeight}px`, overflowY: 'auto' }}
      >
        {/* Option "Tous" (valeur nulle) */}
        {allowNull && (
          <label
            className={`flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 border-b border-gray-200 dark:border-gray-700 ${noneSelected ? 'bg-primary-50 dark:bg-primary-900/30' : ''}`}
          >
            <div className={`w-4 h-4 rounded border flex items-center justify-center ${noneSelected ? 'bg-primary-500 border-primary-500' : 'border-gray-400 dark:border-gray-500'}`}>
              {noneSelected && <Check className="w-3 h-3 text-white" />}
            </div>
            <span className={`text-sm ${noneSelected ? 'font-medium text-primary-700 dark:text-primary-300' : 'text-gray-700 dark:text-gray-300'}`}>
              {nullLabel}
            </span>
          </label>
        )}

        {/* Options filtrées */}
        {filteredOptions.length === 0 ? (
          <div className="px-3 py-4 text-center text-sm text-gray-500">
            {searchTerm ? 'Aucun résultat' : 'Aucune option disponible'}
          </div>
        ) : (
          filteredOptions.filter(opt => opt.value).map((opt, i) => {
            const isChecked = value.includes(opt.value)
            return (
              <label
                key={opt.value || i}
                className={`flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 ${i < filteredOptions.filter(o => o.value).length - 1 ? 'border-b border-gray-100 dark:border-gray-700' : ''} ${isChecked ? 'bg-primary-50/50 dark:bg-primary-900/20' : ''}`}
              >
                <div className={`w-4 h-4 rounded border flex items-center justify-center transition-colors ${isChecked ? 'bg-primary-500 border-primary-500' : 'border-gray-400 dark:border-gray-500'}`}>
                  {isChecked && <Check className="w-3 h-3 text-white" />}
                </div>
                <span className={`text-sm ${isChecked ? 'font-medium text-gray-900 dark:text-white' : 'text-gray-700 dark:text-gray-300'}`}>
                  {opt.label}
                </span>
                <input
                  type="checkbox"
                  checked={isChecked}
                  onChange={() => toggleOption(opt.value)}
                  className="sr-only"
                />
              </label>
            )
          })
        )}
      </div>

      {/* Résumé de la sélection */}
      {value.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {value.slice(0, 3).map(v => {
            const opt = options.find(o => o.value === v)
            return (
              <span
                key={v}
                className="inline-flex items-center gap-1 px-2 py-0.5 bg-primary-100 dark:bg-primary-900/40 text-primary-700 dark:text-primary-300 rounded text-xs"
              >
                {opt?.label || v}
              </span>
            )
          })}
          {value.length > 3 && (
            <span className="inline-flex items-center px-2 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded text-xs">
              +{value.length - 3} autres
            </span>
          )}
        </div>
      )}
    </div>
  )
}
