import { X, ChevronDown, Settings2 } from 'lucide-react'
import { useState, useRef, useEffect } from 'react'

const AGGREGATIONS = [
  { value: 'SUM', label: 'Somme' },
  { value: 'COUNT', label: 'Comptage' },
  { value: 'AVG', label: 'Moyenne' },
  { value: 'MIN', label: 'Minimum' },
  { value: 'MAX', label: 'Maximum' },
  { value: 'DISTINCTCOUNT', label: 'Nb Distinct' },
]

const FORMATS = [
  { value: 'number', label: 'Nombre' },
  { value: 'currency', label: 'Monnaie (DH)' },
  { value: 'percent', label: 'Pourcentage' },
  { value: 'text', label: 'Texte' },
]

export default function MeasureConfig({
  measure,
  onChange,
  onRemove,
  className = '',
}) {
  const [showPopover, setShowPopover] = useState(false)
  const popoverRef = useRef(null)
  const btnRef = useRef(null)

  const handleChange = (key, value) => {
    onChange?.({ ...measure, [key]: value })
  }

  // Fermer le popover au clic exterieur
  useEffect(() => {
    if (!showPopover) return
    const handleClick = (e) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target) &&
          btnRef.current && !btnRef.current.contains(e.target)) {
        setShowPopover(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [showPopover])

  return (
    <div className={`bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-3 ${className}`}>
      {/* Ligne principale */}
      <div className="flex items-center gap-3">
        {/* Bouton config */}
        <div className="relative">
          <button
            ref={btnRef}
            onClick={() => setShowPopover(!showPopover)}
            className={`p-1 rounded transition-colors ${showPopover ? 'text-blue-500 bg-blue-50 dark:bg-blue-900/30' : 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-300'}`}
            title="Parametres"
          >
            <Settings2 size={16} />
          </button>

          {/* Popover */}
          {showPopover && (
            <div
              ref={popoverRef}
              className="absolute left-0 top-8 z-50 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-3 w-64"
            >
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Format</label>
                  <select
                    value={measure.format || 'number'}
                    onChange={(e) => handleChange('format', e.target.value)}
                    className="w-full text-sm bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded px-2 py-1.5 focus:ring-2 focus:ring-blue-500 outline-none"
                  >
                    {FORMATS.map(f => (
                      <option key={f.value} value={f.value}>{f.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Decimales</label>
                  <input
                    type="number"
                    min={0}
                    max={6}
                    value={measure.decimals ?? 2}
                    onChange={(e) => handleChange('decimals', parseInt(e.target.value) || 0)}
                    className="w-full text-sm bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded px-2 py-1.5 focus:ring-2 focus:ring-blue-500 outline-none"
                  />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Champ */}
        <span className="text-sm font-medium text-purple-700 dark:text-purple-400 bg-purple-50 dark:bg-purple-900/20 px-2 py-0.5 rounded">
          {measure.field}
        </span>

        {/* Agregation */}
        <select
          value={measure.aggregation || 'SUM'}
          onChange={(e) => handleChange('aggregation', e.target.value)}
          className="text-sm bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded px-2 py-1 focus:ring-2 focus:ring-blue-500 outline-none"
        >
          {AGGREGATIONS.map(a => (
            <option key={a.value} value={a.value}>{a.label}</option>
          ))}
        </select>

        {/* Label custom */}
        <input
          type="text"
          value={measure.label || ''}
          onChange={(e) => handleChange('label', e.target.value)}
          placeholder="Label..."
          className="flex-1 text-sm bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded px-2 py-1 focus:ring-2 focus:ring-blue-500 outline-none"
        />

        <button
          onClick={() => onRemove?.(measure.field)}
          className="p-1 text-gray-400 hover:text-red-500 transition-colors"
        >
          <X size={16} />
        </button>
      </div>
    </div>
  )
}
