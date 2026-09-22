import { useState, useRef, useEffect } from 'react'
import FieldPill from './FieldPill'
import { Filter, Plus } from 'lucide-react'

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
    accent: 'bg-sky-500',
    iconBg: 'bg-sky-50 text-sky-600 dark:bg-sky-900/30 dark:text-sky-300',
    activeBg: 'bg-sky-50 dark:bg-sky-900/20 border-sky-400 dark:border-sky-600',
    hint: 'Axe vertical du tableau',
  },
  columns: {
    accent: 'bg-emerald-500',
    iconBg: 'bg-emerald-50 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-300',
    activeBg: 'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-400 dark:border-emerald-600',
    hint: 'Axe horizontal du tableau',
  },
  values: {
    accent: 'bg-violet-500',
    iconBg: 'bg-violet-50 text-violet-600 dark:bg-violet-900/30 dark:text-violet-300',
    activeBg: 'bg-violet-50 dark:bg-violet-900/20 border-violet-400 dark:border-violet-600',
    hint: 'Indicateurs agrégés',
  },
  filters: {
    accent: 'bg-amber-500',
    iconBg: 'bg-amber-50 text-amber-600 dark:bg-amber-900/30 dark:text-amber-300',
    activeBg: 'bg-amber-50 dark:bg-amber-900/20 border-amber-400 dark:border-amber-600',
    hint: "Restreignent les données à l'affichage",
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

  const overLimit = maxFields && fields.length > maxFields
  const ZoneIcon = Icon || Filter

  return (
    <div className={`relative flex flex-col rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm overflow-hidden ${className}`}>
      <span className={`absolute left-0 top-0 bottom-0 w-[3px] ${style.accent}`} />
      {title && (
        <div className="flex items-center gap-2.5 px-4 py-2.5 border-b border-gray-100 dark:border-gray-700">
          <span className={`flex items-center justify-center w-7 h-7 rounded-lg ${style.iconBg}`}>
            <ZoneIcon size={15} />
          </span>
          <div className="min-w-0">
            <div className="text-[13px] font-semibold text-gray-800 dark:text-gray-100 leading-tight">{title}</div>
            <div className="text-[11px] text-gray-400 leading-tight truncate">{style.hint}</div>
          </div>
          <span
            className={`ml-auto px-2 py-0.5 rounded-full text-[11px] font-semibold ${overLimit
              ? 'bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-300'
              : 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-300'}`}
            title={overLimit ? `Maximum ${maxFields} champ(s) — le surplus est ignoré` : undefined}
          >
            {maxFields ? `${fields.length}/${maxFields}` : fields.length}
          </span>
        </div>
      )}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`
          flex-1 min-h-[76px] m-2 rounded-lg border border-dashed p-2
          transition-colors duration-150
          ${dragOver ? style.activeBg : 'border-transparent'}
          ${fields.length === 0 && !dragOver ? 'border-gray-200 dark:border-gray-700 bg-gray-50/60 dark:bg-gray-900/20' : ''}
          ${fields.length === 0 ? 'flex items-center justify-center' : ''}
        `}
      >
        {fields.length === 0 ? (
          <span className="flex items-center gap-1.5 text-xs text-gray-400 dark:text-gray-500">
            <Plus size={13} />
            {placeholder}
          </span>
        ) : (
          <div className="flex flex-wrap gap-1.5 content-start">
            {fields.map((f, i) => {
              const agg = zone === 'values' ? (AGGREGATIONS.find(a => a.value === f.aggregation) || AGGREGATIONS[0]).label : null
              const dateGrp = f.type === 'date' && f.date_grouping
                ? ((DATE_GROUPINGS.find(dg => dg.value === f.date_grouping) || {}).label || f.date_grouping) : null
              const numGrp = f.numeric_grouping?.type
                ? (f.numeric_grouping.type === 'interval' ? `Pas ${f.numeric_grouping.step}` : 'Plages') : null
              const txtGrp = f.text_grouping?.type
                ? (f.text_grouping.type === 'first_letter' ? '1re lettre' : 'Groupes') : null
              return (
                <div
                  key={f._uid || `${f.field}_${i}`}
                  onDragOver={(e) => { e.preventDefault(); e.stopPropagation() }}
                  onDrop={(e) => handleInternalDrop(e, i)}
                  onContextMenu={(e) => handleContextMenu(e, f, i)}
                  className={`max-w-full ${dragIndex === i ? 'opacity-30' : ''} transition-opacity`}
                >
                  <FieldPill
                    field={f.field}
                    type={f.type}
                    label={f.label || f.field}
                    badge={agg || dateGrp || numGrp || txtGrp}
                    removable
                    onRemove={() => onRemove?.(f._uid, zone)}
                    onSettings={onFieldChange ? (e) => {
                      const r = e.currentTarget.getBoundingClientRect()
                      setContextMenu({ x: Math.min(r.left, window.innerWidth - 240), y: r.bottom + 4, field: f, index: i })
                    } : undefined}
                    onDragStart={(e) => handleInternalDragStart(e, i)}
                    compact
                  />
                </div>
              )
            })}
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
