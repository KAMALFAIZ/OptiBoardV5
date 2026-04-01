import { useState, useRef, useEffect } from 'react'
import FieldPill from './FieldPill'
import { Calendar } from 'lucide-react'

const DATE_GROUPINGS = [
  { value: '', label: 'Brut' },
  { value: 'jour', label: 'Jour' },
  { value: 'semaine', label: 'Semaine' },
  { value: 'mois', label: 'Mois' },
  { value: 'mois_annee', label: 'Mois-Annee' },
  { value: 'trimestre', label: 'Trimestre' },
  { value: 'trimestre_annee', label: 'Trim-Annee' },
  { value: 'semestre', label: 'Semestre' },
  { value: 'semestre_annee', label: 'Sem-Annee' },
  { value: 'annee', label: 'Annee' },
]

const AGGREGATIONS = [
  { value: 'SUM', label: 'Somme' },
  { value: 'COUNT', label: 'Comptage' },
  { value: 'AVG', label: 'Moyenne' },
  { value: 'MIN', label: 'Minimum' },
  { value: 'MAX', label: 'Maximum' },
  { value: 'DISTINCTCOUNT', label: 'Nb Distinct' },
  { value: 'VAR', label: 'Variance' },
  { value: 'STDEV', label: 'Ecart-type' },
  { value: 'MEDIAN', label: 'Mediane' },
]

const NUMERIC_GROUPINGS = [
  { value: '', label: 'Aucun' },
  { value: 'interval', label: 'Intervalle fixe' },
  { value: 'ranges', label: 'Plages personnalisees' },
]

const FORMATS = [
  { value: 'number', label: 'Nombre' },
  { value: 'currency', label: 'Monnaie (DH)' },
  { value: 'percent', label: 'Pourcentage' },
  { value: 'text', label: 'Texte' },
]

const zoneStyles = {
  rows: {
    border: 'border-blue-300 dark:border-blue-700',
    bg: 'bg-blue-50/50 dark:bg-blue-900/10',
    activeBg: 'bg-blue-100 dark:bg-blue-900/30',
    label: 'text-blue-700 dark:text-blue-400',
  },
  columns: {
    border: 'border-green-300 dark:border-green-700',
    bg: 'bg-green-50/50 dark:bg-green-900/10',
    activeBg: 'bg-green-100 dark:bg-green-900/30',
    label: 'text-green-700 dark:text-green-400',
  },
  values: {
    border: 'border-purple-300 dark:border-purple-700',
    bg: 'bg-purple-50/50 dark:bg-purple-900/10',
    activeBg: 'bg-purple-100 dark:bg-purple-900/30',
    label: 'text-purple-700 dark:text-purple-400',
  },
  filters: {
    border: 'border-amber-300 dark:border-amber-700',
    bg: 'bg-amber-50/50 dark:bg-amber-900/10',
    activeBg: 'bg-amber-100 dark:bg-amber-900/30',
    label: 'text-amber-700 dark:text-amber-400',
  },
}

export default function DropZone({
  zone = 'rows',
  title,
  icon: Icon,
  fields = [],
  onDrop,
  onRemove,
  onReorder,
  onFieldChange,
  placeholder = 'Glisser des champs ici',
  maxFields,
  className = '',
}) {
  const [dragOver, setDragOver] = useState(false)
  const [dragIndex, setDragIndex] = useState(null)
  const [contextMenu, setContextMenu] = useState(null) // { x, y, field, index }
  const contextRef = useRef(null)
  const style = zoneStyles[zone] || zoneStyles.rows

  const showDateGrouping = true // Regroupement temporel disponible pour les champs date dans toutes les zones

  // Fermer le menu contextuel au clic exterieur
  useEffect(() => {
    if (!contextMenu) return
    const handleClick = (e) => {
      if (contextRef.current && !contextRef.current.contains(e.target)) {
        setContextMenu(null)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [contextMenu])

  const handleDragOver = (e) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
    setDragOver(true)
  }

  const handleDragLeave = (e) => {
    if (!e.currentTarget.contains(e.relatedTarget)) {
      setDragOver(false)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    setDragIndex(null)

    try {
      const data = JSON.parse(e.dataTransfer.getData('text/plain'))
      if (data && data.field) {
        if (maxFields && fields.length >= maxFields) {
          return
        }
        // Autoriser le meme champ plusieurs fois dans les valeurs (ex: SUM + AVG)
        // Pour les autres zones, bloquer les doublons
        if (zone !== 'values' && fields.some(f => f.field === data.field)) {
          return
        }
        onDrop?.(data, zone)
      }
    } catch (err) {
      // Ignore invalid drag data
    }
  }

  const handleInternalDragStart = (e, index) => {
    setDragIndex(index)
    e.dataTransfer.setData('text/plain', JSON.stringify({ ...fields[index], __reorder: true, __fromZone: zone, __fromIndex: index }))
  }

  const handleInternalDrop = (e, targetIndex) => {
    e.preventDefault()
    e.stopPropagation()

    try {
      const data = JSON.parse(e.dataTransfer.getData('text/plain'))
      if (data.__reorder && data.__fromZone === zone) {
        onReorder?.(data.__fromIndex, targetIndex)
      }
    } catch (err) {
      // Ignore
    }
    setDragIndex(null)
  }

  const handleContextMenu = (e, field, index) => {
    e.preventDefault()
    setContextMenu({ x: e.clientX, y: e.clientY, field, index })
  }

  const handleContextChange = (key, value) => {
    if (!contextMenu) return
    // Mettre a jour le menu contextuel localement pour reflet immediat
    setContextMenu(prev => prev ? { ...prev, field: { ...prev.field, [key]: value } } : null)
    onFieldChange?.(contextMenu.field._uid, zone, { [key]: value })
  }

  return (
    <div className={`${className}`}>
      {title && (
        <div className={`flex items-center gap-1.5 mb-1.5 text-xs font-semibold uppercase tracking-wide ${style.label}`}>
          {Icon && <Icon size={14} />}
          <span>{title}</span>
          {maxFields && (
            <span className="text-gray-400 font-normal">({fields.length}/{maxFields})</span>
          )}
        </div>
      )}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`
          min-h-[48px] rounded-lg border-2 border-dashed p-2
          transition-all duration-200
          ${dragOver ? `${style.activeBg} ${style.border} scale-[1.01]` : `${style.bg} ${style.border} border-opacity-50`}
          ${fields.length === 0 ? 'flex items-center justify-center' : ''}
        `}
      >
        {fields.length === 0 ? (
          <span className="text-xs text-gray-400 dark:text-gray-500 italic">{placeholder}</span>
        ) : (
          <div className="flex flex-wrap gap-1.5">
            {fields.map((f, i) => (
              <div
                key={f._uid || `${f.field}_${i}`}
                onDragOver={(e) => { e.preventDefault(); e.stopPropagation() }}
                onDrop={(e) => handleInternalDrop(e, i)}
                onContextMenu={(e) => handleContextMenu(e, f, i)}
                className={`flex items-center gap-1 ${dragIndex === i ? 'opacity-30' : ''} transition-opacity`}
              >
                <FieldPill
                  field={f.field}
                  type={f.type}
                  label={zone === 'values' ? `${f.label || f.field} (${(AGGREGATIONS.find(a => a.value === f.aggregation) || AGGREGATIONS[0]).label})` : (f.label || f.field)}
                  removable
                  onRemove={() => onRemove?.(f._uid, zone)}
                  onDragStart={(e) => handleInternalDragStart(e, i)}
                  compact
                />
                {/* Indicateur de regroupement temporel pour les champs date */}
                {f.type === 'date' && f.date_grouping && (
                  <span
                    className="text-[10px] px-1 py-0.5 rounded bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-300 cursor-pointer"
                    title="Regroupement temporel (clic droit pour modifier)"
                  >
                    {(DATE_GROUPINGS.find(dg => dg.value === f.date_grouping) || {}).label || f.date_grouping}
                  </span>
                )}
                {/* Indicateur regroupement numerique */}
                {f.numeric_grouping?.type && (
                  <span
                    className="text-[10px] px-1 py-0.5 rounded bg-cyan-100 dark:bg-cyan-900/30 text-cyan-600 dark:text-cyan-300 cursor-pointer"
                    title="Regroupement numerique (clic droit pour modifier)"
                  >
                    {f.numeric_grouping.type === 'interval' ? `Pas: ${f.numeric_grouping.step}` : 'Plages'}
                  </span>
                )}
                {/* Indicateur regroupement texte */}
                {f.text_grouping?.type && (
                  <span
                    className="text-[10px] px-1 py-0.5 rounded bg-teal-100 dark:bg-teal-900/30 text-teal-600 dark:text-teal-300 cursor-pointer"
                    title="Regroupement texte (clic droit pour modifier)"
                  >
                    {f.text_grouping.type === 'first_letter' ? '1re lettre' : 'Groupes'}
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Menu contextuel (clic droit) */}
      {contextMenu && (
        <div
          ref={contextRef}
          className="fixed z-[100] bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-xl py-1 min-w-[220px]"
          style={{ left: contextMenu.x, top: contextMenu.y }}
        >
          {/* Nom du champ */}
          <div className="px-3 py-1.5 text-xs font-semibold text-gray-500 dark:text-gray-400 border-b border-gray-100 dark:border-gray-700">
            {contextMenu.field.field}
          </div>

          {/* Label personnalise */}
          <div className="px-3 py-2 border-b border-gray-100 dark:border-gray-700">
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Label</label>
            <input
              type="text"
              value={contextMenu.field.label || ''}
              onChange={(e) => handleContextChange('label', e.target.value)}
              placeholder={contextMenu.field.field}
              className="w-full text-sm bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded px-2 py-1 focus:ring-2 focus:ring-blue-500 outline-none"
            />
          </div>

          {/* Regroupement temporel pour les dates en lignes/colonnes */}
          {showDateGrouping && contextMenu.field.type === 'date' && (
            <div className="px-3 py-2 border-b border-gray-100 dark:border-gray-700">
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Regroupement</label>
              <select
                value={contextMenu.field.date_grouping || ''}
                onChange={(e) => handleContextChange('date_grouping', e.target.value)}
                className="w-full text-sm bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded px-2 py-1 focus:ring-2 focus:ring-blue-500 outline-none"
              >
                {DATE_GROUPINGS.map(dg => (
                  <option key={dg.value} value={dg.value}>{dg.label}</option>
                ))}
              </select>
            </div>
          )}

          {/* Options pour les mesures (valeurs) */}
          {zone === 'values' && (
            <div className="px-3 py-2 space-y-2 border-b border-gray-100 dark:border-gray-700">
              <div>
                <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Agregation</label>
                <select
                  value={contextMenu.field.aggregation || 'SUM'}
                  onChange={(e) => handleContextChange('aggregation', e.target.value)}
                  className="w-full text-sm bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded px-2 py-1 focus:ring-2 focus:ring-blue-500 outline-none"
                >
                  {AGGREGATIONS.map(a => (
                    <option key={a.value} value={a.value}>{a.label}</option>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Format</label>
                  <select
                    value={contextMenu.field.format || 'number'}
                    onChange={(e) => handleContextChange('format', e.target.value)}
                    className="w-full text-sm bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded px-2 py-1 focus:ring-2 focus:ring-blue-500 outline-none"
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
                    value={contextMenu.field.decimals ?? 2}
                    onChange={(e) => handleContextChange('decimals', parseInt(e.target.value) || 0)}
                    className="w-full text-sm bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded px-2 py-1 focus:ring-2 focus:ring-blue-500 outline-none"
                  />
                </div>
              </div>
              {/* Fonction dans les totaux */}
              <div>
                <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Fonction dans les totaux</label>
                <select
                  value={contextMenu.field.summary_aggregation || ''}
                  onChange={(e) => handleContextChange('summary_aggregation', e.target.value || null)}
                  className="w-full text-sm bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded px-2 py-1 focus:ring-2 focus:ring-blue-500 outline-none"
                >
                  <option value="">Identique</option>
                  {AGGREGATIONS.map(a => (
                    <option key={a.value} value={a.value}>{a.label}</option>
                  ))}
                </select>
              </div>
              <label className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400">
                <input
                  type="checkbox"
                  checked={contextMenu.field.show_in_totals !== false}
                  onChange={(e) => handleContextChange('show_in_totals', e.target.checked)}
                  className="rounded"
                />
                Afficher dans les totaux
              </label>
            </div>
          )}

          {/* Regroupement numerique (pour champs number en lignes/colonnes) */}
          {(zone === 'rows' || zone === 'columns') && contextMenu.field.type === 'number' && (
            <div className="px-3 py-2 border-b border-gray-100 dark:border-gray-700 space-y-2">
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400">Regroupement numerique</label>
              <select
                value={contextMenu.field.numeric_grouping?.type || ''}
                onChange={(e) => {
                  const t = e.target.value
                  if (!t) handleContextChange('numeric_grouping', null)
                  else if (t === 'interval') handleContextChange('numeric_grouping', { type: 'interval', step: 100 })
                  else if (t === 'ranges') handleContextChange('numeric_grouping', { type: 'ranges', ranges: [{ label: 'Bas', min: 0, max: 100 }, { label: 'Moyen', min: 100, max: 500 }, { label: 'Haut', min: 500, max: 999999 }] })
                }}
                className="w-full text-sm bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded px-2 py-1 focus:ring-2 focus:ring-blue-500 outline-none"
              >
                {NUMERIC_GROUPINGS.map(ng => (
                  <option key={ng.value} value={ng.value}>{ng.label}</option>
                ))}
              </select>
              {contextMenu.field.numeric_grouping?.type === 'interval' && (
                <div>
                  <label className="text-xs text-gray-500 dark:text-gray-400">Pas:</label>
                  <input
                    type="number"
                    min={1}
                    value={contextMenu.field.numeric_grouping.step || 100}
                    onChange={(e) => handleContextChange('numeric_grouping', { ...contextMenu.field.numeric_grouping, step: parseInt(e.target.value) || 100 })}
                    className="w-full text-sm bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded px-2 py-1 focus:ring-2 focus:ring-blue-500 outline-none mt-1"
                  />
                </div>
              )}
            </div>
          )}

          {/* Regroupement texte (pour champs text en lignes/colonnes) */}
          {(zone === 'rows' || zone === 'columns') && contextMenu.field.type === 'text' && !contextMenu.field.date_grouping && (
            <div className="px-3 py-2 border-b border-gray-100 dark:border-gray-700">
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Regroupement texte</label>
              <select
                value={contextMenu.field.text_grouping?.type || ''}
                onChange={(e) => {
                  const t = e.target.value
                  if (!t) handleContextChange('text_grouping', null)
                  else if (t === 'first_letter') handleContextChange('text_grouping', { type: 'first_letter' })
                }}
                className="w-full text-sm bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded px-2 py-1 focus:ring-2 focus:ring-blue-500 outline-none"
              >
                <option value="">Aucun</option>
                <option value="first_letter">Premiere lettre</option>
              </select>
            </div>
          )}

          {/* Supprimer */}
          <button
            onClick={() => {
              onRemove?.(contextMenu.field._uid, zone)
              setContextMenu(null)
            }}
            className="w-full text-left px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
          >
            Supprimer
          </button>
        </div>
      )}
    </div>
  )
}
