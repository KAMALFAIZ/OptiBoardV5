import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { useIsMobile } from '../hooks/useIsMobile'
import { useAuth } from '../context/AuthContext'
import { useSettings } from '../context/SettingsContext'
import { useGlobalFilters } from '../context/GlobalFilterContext'
import {
  getPivotV2, executePivotV2, drilldownPivotV2, exportPivotV2,
  getPivotV2Fields, getPivotV2UserPrefs, savePivotV2UserPrefs, resetPivotV2UserPrefs,
  getUnifiedDataSourceFields, updatePivotV2, isRequestCanceled, getUnifiedDataSource
} from '../services/api'
import api from '../services/api'
import { PivotTable, PivotChart, DrillDownModal } from '../components/PivotV2'
import GlobalFilterBar from '../components/GlobalFilterBar'
import SubscribeButton from '../components/common/SubscribeButton'
import FavoriteButton from '../components/common/FavoriteButton'
import InsightsPanel from '../components/common/InsightsPanel'
import ExecutiveSummaryModal from '../components/common/ExecutiveSummaryModal'
import {
  Loader2, RefreshCw, Download, Table2, BarChart3, LayoutGrid,
  RotateCcw, FileSpreadsheet, FileText, Settings2, X,
  GripVertical, ArrowRight, ArrowLeft, ArrowUp, ArrowDown, Check,
  ChevronDown, Presentation, ExternalLink, Info,
  Rows3, Columns3, Filter, Hash, Type, Calendar
} from 'lucide-react'
import ReportDocModal, { hasDoc } from '../components/common/ReportDocModal'

const VIEW_MODES = [
  { id: 'table', icon: Table2, label: 'Tableau' },
  { id: 'chart', icon: BarChart3, label: 'Graphique' },
  { id: 'both', icon: LayoutGrid, label: 'Les deux' },
]

const CHART_TYPES = [
  { id: 'bar', label: 'Barres' },
  { id: 'horizontal_bar', label: 'Barres horiz.' },
  { id: 'stacked_bar', label: 'Barres empilees' },
  { id: 'line', label: 'Lignes' },
  { id: 'area', label: 'Aires' },
  { id: 'pie', label: 'Camembert' },
  { id: 'donut', label: 'Anneau' },
]

const AGGREGATIONS = [
  { value: 'SUM', label: 'Somme' },
  { value: 'COUNT', label: 'Comptage' },
  { value: 'AVG', label: 'Moyenne' },
  { value: 'MIN', label: 'Min' },
  { value: 'MAX', label: 'Max' },
  { value: 'DISTINCTCOUNT', label: 'Distinct' },
  { value: 'VAR', label: 'Variance' },
  { value: 'STDEV', label: 'Ecart-type' },
  { value: 'MEDIAN', label: 'Mediane' },
]

// Parse JSON string ou retourne le tableau directement. Les colonnes de configuration sont
// stockees en NVARCHAR(MAX) : selon le chemin de lecture, elles remontent tantot en tableau
// deja parse, tantot en chaine JSON brute. Sans normalisation, une chaine traverse le `|| []`
// (elle est truthy) et casse au premier .map, ou pire fait paraitre les zones remplies alors
// qu'aucun champ n'est exploitable. Meme helper que le concepteur.
const safeArray = (val) => {
  if (Array.isArray(val)) return val
  if (typeof val === 'string') {
    try { const parsed = JSON.parse(val); return Array.isArray(parsed) ? parsed : [] }
    catch { return [] }
  }
  return []
}

// ─── Field Chooser Dialog ────────────────────────────────────────────
function FieldChooserDialog({ open, onClose, availableFields, liveConfig, onApply }) {
  const [config, setConfig] = useState({ rows: [], columns: [], values: [], filters: [] })
  const [dragItem, setDragItem] = useState(null)
  const [dragSource, setDragSource] = useState(null)

  // Sync on open
  useEffect(() => {
    if (open) {
      setConfig({
        rows: [...(liveConfig.rows || [])],
        columns: [...(liveConfig.columns || [])],
        values: [...(liveConfig.values || [])],
        filters: [...(liveConfig.filters || [])],
      })
    }
  }, [open, liveConfig])

  if (!open) return null

  // Champs utilises
  const usedFieldNames = new Set([
    ...config.rows.map(f => f.field),
    ...config.columns.map(f => f.field),
    ...config.values.map(f => f.field),
    ...config.filters.map(f => f.field),
  ])

  // Champs disponibles non utilises
  const unusedFields = availableFields.filter(f => !usedFieldNames.has(f.name))

  // Drag handlers
  const handleDragStart = (field, source) => {
    setDragItem(field)
    setDragSource(source)
  }

  const handleDrop = (targetZone) => {
    if (!dragItem) return

    // Remove from source
    if (dragSource && dragSource !== 'available') {
      setConfig(prev => ({
        ...prev,
        [dragSource]: prev[dragSource].filter(f => f.field !== dragItem.field),
      }))
    }

    // Build field object
    let fieldObj = dragSource === 'available'
      ? { field: dragItem.name || dragItem.field, label: dragItem.label || dragItem.name || dragItem.field, type: dragItem.type }
      : { ...dragItem }

    if (targetZone === 'values' && !fieldObj.aggregation) {
      fieldObj.aggregation = 'SUM'
      fieldObj.format = fieldObj.type === 'number' ? 'number' : 'text'
      fieldObj.decimals = 2
    }

    // Add to target
    setConfig(prev => ({
      ...prev,
      [targetZone]: [...prev[targetZone], fieldObj],
    }))

    setDragItem(null)
    setDragSource(null)
  }

  const handleRemoveFromZone = (zone, fieldName) => {
    setConfig(prev => ({
      ...prev,
      [zone]: prev[zone].filter(f => f.field !== fieldName),
    }))
  }

  const handleMoveUp = (zone, idx) => {
    if (idx === 0) return
    setConfig(prev => {
      const arr = [...prev[zone]]
      ;[arr[idx - 1], arr[idx]] = [arr[idx], arr[idx - 1]]
      return { ...prev, [zone]: arr }
    })
  }

  const handleMoveDown = (zone, idx) => {
    setConfig(prev => {
      if (idx >= prev[zone].length - 1) return prev
      const arr = [...prev[zone]]
      ;[arr[idx], arr[idx + 1]] = [arr[idx + 1], arr[idx]]
      return { ...prev, [zone]: arr }
    })
  }

  const handleChangeAgg = (idx, newAgg) => {
    setConfig(prev => {
      const arr = [...prev.values]
      arr[idx] = { ...arr[idx], aggregation: newAgg }
      return { ...prev, values: arr }
    })
  }

  const DATE_GROUPING_OPTIONS = [
    { value: '', label: 'Brut (date exacte)' },
    { value: 'mois_annee', label: 'Mois-Année' },
    { value: 'trimestre_annee', label: 'Trimestre-Année' },
    { value: 'semestre_annee', label: 'Semestre-Année' },
    { value: 'annee', label: 'Année' },
    { value: 'mois', label: 'Mois' },
    { value: 'trimestre', label: 'Trimestre' },
    { value: 'semestre', label: 'Semestre' },
    { value: 'jour', label: 'Jour' },
    { value: 'semaine', label: 'Semaine' },
  ]

  const handleChangeDateGrouping = (zone, idx, newGrouping) => {
    setConfig(prev => {
      const arr = [...prev[zone]]
      arr[idx] = { ...arr[idx], date_grouping: newGrouping || undefined }
      return { ...prev, [zone]: arr }
    })
  }

  const isEmptyConfig = config.rows.length === 0 && config.values.length === 0

  const handleApply = () => {
    // Refuser une config qui n'affiche rien — elle serait aussi persistee en base
    if (isEmptyConfig) return
    onApply(config)
    onClose()
  }

  // Memes codes couleur que le Pivot Builder
  const TYPE_BADGE = {
    number: { icon: Hash, cls: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300' },
    date: { icon: Calendar, cls: 'bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300' },
    text: { icon: Type, cls: 'bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300' },
  }
  const TypeBadge = ({ type }) => {
    const t = TYPE_BADGE[type] || TYPE_BADGE.text
    const I = t.icon
    return (
      <span className={`flex items-center justify-center w-5 h-5 rounded flex-shrink-0 ${t.cls}`}>
        <I size={11} strokeWidth={2.5} />
      </span>
    )
  }

  const ZoneBox = ({ zone, title, hint, icon: ZIcon, fields, maxFields, color = 'gray' }) => {
    const accents = {
      blue: { bar: 'bg-sky-500', icon: 'bg-sky-50 text-sky-600 dark:bg-sky-900/30 dark:text-sky-300' },
      green: { bar: 'bg-emerald-500', icon: 'bg-emerald-50 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-300' },
      amber: { bar: 'bg-amber-500', icon: 'bg-amber-50 text-amber-600 dark:bg-amber-900/30 dark:text-amber-300' },
      purple: { bar: 'bg-violet-500', icon: 'bg-violet-50 text-violet-600 dark:bg-violet-900/30 dark:text-violet-300' },
    }
    const a = accents[color] || accents.blue
    const overLimit = maxFields && fields.length > maxFields
    return (
      <div
        className="relative flex flex-col rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm overflow-hidden min-h-[120px] transition-shadow"
        onDragOver={(e) => { e.preventDefault(); e.currentTarget.classList.add('ring-2', 'ring-primary-400') }}
        onDragLeave={(e) => { if (!e.currentTarget.contains(e.relatedTarget)) e.currentTarget.classList.remove('ring-2', 'ring-primary-400') }}
        onDrop={(e) => { e.preventDefault(); e.currentTarget.classList.remove('ring-2', 'ring-primary-400'); handleDrop(zone) }}
      >
        <span className={`absolute left-0 top-0 bottom-0 w-[3px] ${a.bar}`} />
        <div className="flex items-center gap-2 px-3 py-2 border-b border-gray-100 dark:border-gray-700">
          <span className={`flex items-center justify-center w-6 h-6 rounded-md ${a.icon}`}>
            <ZIcon size={13} />
          </span>
          <div className="min-w-0">
            <div className="text-xs font-semibold text-gray-800 dark:text-gray-100 leading-tight">{title}</div>
            <div className="text-[10px] text-gray-400 leading-tight truncate">{hint}</div>
          </div>
          <span className={`ml-auto px-1.5 py-0.5 rounded-full text-[10px] font-semibold ${overLimit
            ? 'bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-300'
            : 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-300'}`}>
            {maxFields ? `${fields.length}/${maxFields}` : fields.length}
          </span>
        </div>
        <div className="flex-1 p-2">
        <div className="space-y-1">
          {fields.map((f, idx) => (
            <div
              key={f.field}
              draggable
              onDragStart={() => handleDragStart(f, zone)}
              title={f.label || f.field}
              className="flex items-center gap-1.5 h-8 bg-white dark:bg-gray-800 rounded-md pl-1 pr-1.5 text-xs border border-gray-200 dark:border-gray-700 cursor-grab active:cursor-grabbing group hover:border-primary-300 dark:hover:border-primary-600 hover:shadow-sm transition-all"
            >
              <GripVertical size={12} className="text-gray-300 group-hover:text-gray-400 flex-shrink-0" />
              <TypeBadge type={f.type} />
              <span className="flex-1 truncate font-medium text-gray-700 dark:text-gray-200">
                {f.label || f.field}
              </span>
              {(zone === 'rows' || zone === 'columns') && f.type === 'date' && (
                <select
                  value={f.date_grouping || ''}
                  onChange={(e) => handleChangeDateGrouping(zone, idx, e.target.value)}
                  onClick={(e) => e.stopPropagation()}
                  className="text-[10px] font-semibold bg-gray-100 dark:bg-gray-700 border-0 rounded px-1 py-0.5 text-gray-600 dark:text-gray-300 max-w-[100px] focus:ring-2 focus:ring-primary-500/30 outline-none"
                >
                  {DATE_GROUPING_OPTIONS.map(dg => (
                    <option key={dg.value} value={dg.value}>{dg.label}</option>
                  ))}
                </select>
              )}
              {zone === 'values' && (
                <select
                  value={f.aggregation || 'SUM'}
                  onChange={(e) => handleChangeAgg(idx, e.target.value)}
                  onClick={(e) => e.stopPropagation()}
                  className="text-[10px] font-semibold bg-gray-100 dark:bg-gray-700 border-0 rounded px-1 py-0.5 text-gray-600 dark:text-gray-300 max-w-[80px] focus:ring-2 focus:ring-primary-500/30 outline-none"
                >
                  {AGGREGATIONS.map(a => (
                    <option key={a.value} value={a.value}>{a.label}</option>
                  ))}
                </select>
              )}
              <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                <button onClick={() => handleMoveUp(zone, idx)} className="p-0.5 rounded text-gray-400 hover:text-primary-600 hover:bg-gray-100 dark:hover:bg-gray-700" title="Monter"><ArrowUp size={11} /></button>
                <button onClick={() => handleMoveDown(zone, idx)} className="p-0.5 rounded text-gray-400 hover:text-primary-600 hover:bg-gray-100 dark:hover:bg-gray-700" title="Descendre"><ArrowDown size={11} /></button>
                <button onClick={() => handleRemoveFromZone(zone, f.field)} className="p-0.5 rounded text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20" title="Retirer"><X size={11} /></button>
              </div>
            </div>
          ))}
          {fields.length === 0 && (
            <div className="h-full min-h-[56px] flex items-center justify-center rounded-lg border border-dashed border-gray-200 dark:border-gray-700 bg-gray-50/60 dark:bg-gray-900/20 text-[11px] text-gray-400">
              Glisser des champs ici
            </div>
          )}
        </div>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-2xl border border-gray-200 dark:border-gray-700 w-[780px] max-w-[95vw] max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2.5">
            <span className="flex items-center justify-center w-8 h-8 rounded-lg bg-primary-50 text-primary-600 dark:bg-primary-900/30 dark:text-primary-300">
              <Settings2 size={16} />
            </span>
            <div>
              <h2 className="text-[13px] font-semibold text-gray-900 dark:text-white leading-tight">Configuration des champs</h2>
              <p className="text-[11px] text-gray-400 leading-tight">Glissez les champs vers les zones pour réorganiser le tableau</p>
            </div>
          </div>
          <button onClick={onClose} title="Fermer" className="w-8 h-8 flex items-center justify-center text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800">
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-auto p-4 bg-gray-50/60 dark:bg-gray-900">
          <div className="flex gap-4">
            {/* Liste des champs disponibles */}
            <div className="w-52 flex-shrink-0 flex flex-col rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm overflow-hidden">
              <div className="flex items-center gap-2 px-3 py-2 border-b border-gray-100 dark:border-gray-700">
                <span className="text-xs font-semibold text-gray-800 dark:text-gray-100">Champs disponibles</span>
                <span className="ml-auto px-1.5 py-0.5 rounded-full bg-primary-50 dark:bg-primary-900/30 text-[10px] font-semibold text-primary-600 dark:text-primary-300">
                  {unusedFields.length}
                </span>
              </div>
              <div className="p-2 space-y-1 max-h-[400px] overflow-y-auto">
                {unusedFields.length === 0 && (
                  <div className="text-[11px] text-gray-400 text-center py-6">
                    Tous les champs sont utilisés
                  </div>
                )}
                {unusedFields.map(f => (
                  <div
                    key={f.name}
                    draggable
                    onDragStart={() => handleDragStart(f, 'available')}
                    title={f.label || f.name}
                    className="group flex items-center gap-1.5 h-7 pl-1 pr-2 text-xs rounded-md bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 cursor-grab active:cursor-grabbing hover:border-primary-300 dark:hover:border-primary-600 hover:shadow-sm transition-all"
                  >
                    <GripVertical size={12} className="text-gray-300 group-hover:text-gray-400 flex-shrink-0" />
                    <TypeBadge type={f.type} />
                    <span className="truncate font-medium text-gray-700 dark:text-gray-200">{f.label || f.name}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Zones de drop */}
            <div className="flex-1 grid grid-cols-2 gap-3">
              <ZoneBox zone="filters" title="Filtres" hint="Restreignent les données" icon={Filter} fields={config.filters} color="amber" />
              <ZoneBox zone="columns" title="Colonnes" hint="Axe horizontal" icon={Columns3} fields={config.columns} maxFields={1} color="green" />
              <ZoneBox zone="rows" title="Lignes" hint="Axe vertical" icon={Rows3} fields={config.rows} color="blue" />
              <ZoneBox zone="values" title="Mesures" hint="Indicateurs agrégés" icon={BarChart3} fields={config.values} color="purple" />
            </div>
          </div>

          {/* Checkbox options */}
          <div className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-800 flex items-center gap-4">
            <label className="flex items-center gap-1.5 text-xs text-gray-500">
              <input type="checkbox" defaultChecked className="w-3.5 h-3.5 rounded text-blue-500" />
              Defer Layout Update
            </label>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 px-5 py-3 border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 rounded-b-xl">
          {isEmptyConfig && (
            <span className="mr-auto text-[11px] text-amber-600 dark:text-amber-400">
              Ajoutez au moins un champ en Lignes et en Mesures.
            </span>
          )}
          <button
            onClick={onClose}
            className="h-8 px-4 text-xs font-semibold text-gray-600 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg hover:border-primary-400 hover:text-primary-600 transition-colors"
          >
            Annuler
          </button>
          <button
            onClick={handleApply}
            disabled={isEmptyConfig}
            title={isEmptyConfig ? 'Ajoutez au moins un champ en Lignes et en Mesures' : undefined}
            className="h-8 px-4 text-xs font-semibold text-white bg-primary-600 rounded-lg hover:bg-primary-700 shadow-sm transition-colors flex items-center gap-1.5 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-primary-600"
          >
            <Check size={14} />
            Appliquer
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Main PivotViewerV2 ─────────────────────────────────────────────
export default function PivotViewerV2() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { user } = useAuth()
  const { formatNumber } = useSettings()
  const { filters: globalFilters, updateFilter } = useGlobalFilters()
  const isMobile = useIsMobile()

  // Config pivot
  const [pivotConfig, setPivotConfig] = useState(null)
  const [loading, setLoading] = useState(true)
  const [executing, setExecuting] = useState(false)
  const [error, setError] = useState(null)

  // Donnees pivotees
  const [pivotResult, setPivotResult] = useState(null)
  const [showDebug, setShowDebug] = useState(false)
  const [showDoc, setShowDoc] = useState(false)
  const [dwhList, setDwhList] = useState([])
  const [selectedDwhCode, setSelectedDwhCode] = useState(() => {
    try { return JSON.parse(localStorage.getItem('currentDWH'))?.code || null } catch { return null }
  })

  // Champs disponibles
  const [availableFields, setAvailableFields] = useState([])

  // Config live (modifiable par l'utilisateur)
  const [liveConfig, setLiveConfig] = useState({
    rows: [],
    columns: [],
    values: [],
    filters: [],
  })

  // UI state
  const [viewMode, setViewMode] = useState('table')
  const [chartType, setChartType] = useState('bar')
  const [maxChartRows, setMaxChartRows] = useState(50)
  const [chartValueIndex, setChartValueIndex] = useState(null)
  const [hasCatalogueParam, setHasCatalogueParam] = useState(false)
  const [fieldChooserOpen, setFieldChooserOpen] = useState(false)
  const [exportMenuOpen, setExportMenuOpen] = useState(false)
  const [openParamsCount, setOpenParamsCount] = useState(0)

  // Drill-down (interne — modal détail)
  const [drilldownOpen, setDrilldownOpen] = useState(false)
  const [drilldownCell, setDrilldownCell] = useState(null)

  // Drill-through inter-rapports
  const [drillByColumn, setDrillByColumn] = useState({})
  const [drillMenu, setDrillMenu] = useState(null) // { x, y, rules, value, field }

  // Prefs save debounce
  const saveTimer = useRef(null)
  const exportMenuRef = useRef(null)

  // Fermer export menu au clic extérieur
  useEffect(() => {
    if (!exportMenuOpen) return
    const handleClick = (e) => {
      if (exportMenuRef.current && !exportMenuRef.current.contains(e.target)) {
        setExportMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [exportMenuOpen])

  // Appliquer les filtres globaux transmis par le rapport source (une seule fois au montage)
  useEffect(() => {
    const gfDateDebut = searchParams.get('gf_dateDebut')
    const gfDateFin = searchParams.get('gf_dateFin')
    const gfSociete = searchParams.get('gf_societe')
    if (gfDateDebut) updateFilter('dateDebut', gfDateDebut)
    if (gfDateFin) updateFilter('dateFin', gfDateFin)
    if (gfSociete) updateFilter('societe', gfSociete)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Charger les règles drill-through pour ce Pivot
  useEffect(() => {
    if (!id) return
    api.get(`/drillthrough/rules/by-source?source_type=pivot&source_id=${id}`)
      .then(res => { if (res.data.success) setDrillByColumn(res.data.by_column || {}) })
      .catch(() => {})
  }, [id])

  // Re-executer quand les filtres globaux changent
  const prevFiltersRef = useRef(null)
  useEffect(() => {
    if (!pivotConfig) return
    const currentFilters = JSON.stringify({
      dateDebut: globalFilters?.dateDebut,
      dateFin: globalFilters?.dateFin,
      societe: globalFilters?.societe,
    })
    if (prevFiltersRef.current && prevFiltersRef.current !== currentFilters) {
      executePivot(pivotConfig)
    }
    prevFiltersRef.current = currentFilters
  }, [globalFilters?.dateDebut, globalFilters?.dateFin, globalFilters?.societe, globalFilters?.catalogue])

  // Charger la liste DWH (pour sélecteur superadmin)
  useEffect(() => {
    api.get('/auth/dwh-list').then(res => {
      const list = res.data || []
      setDwhList(list)
      // Si aucun DWH sélectionné → prendre le premier
      if (!selectedDwhCode && list.length > 0) setSelectedDwhCode(list[0].code)
    }).catch(() => {})
  }, [])

  // Charger la config du pivot
  useEffect(() => {
    if (id) {
      loadPivot()
    }
  }, [id])

  const loadPivot = async () => {
    setLoading(true)
    setError(null)
    setPivotResult(null)  // Vider les données stale d'une navigation précédente
    try {
      const res = await getPivotV2(id)
      if (res.data?.success) {
        const data = res.data.data
        setPivotConfig(data)

        // Init live config depuis la config admin
        setLiveConfig({
          rows: safeArray(data.rows_config),
          columns: safeArray(data.columns_config),
          values: safeArray(data.values_config),
          filters: safeArray(data.filters_config),
        })

        // Charger les preferences utilisateur — uniquement si plus récentes que la config builder
        if (user?.id) {
          try {
            const prefsRes = await getPivotV2UserPrefs(id, user.id)
            if (prefsRes.data?.has_prefs && prefsRes.data?.data?.custom_config) {
              const prefsUpdatedAt = new Date(prefsRes.data.data.updated_at || 0)
              const configUpdatedAt = new Date(data.updated_at || 0)
              // Ignorer les prefs si le builder a sauvegardé plus récemment
              const cc = prefsRes.data.data.custom_config
              // Ignorer des prefs degenerees (ni ligne ni valeur) : elles videraient
              // le pivot alors que la config du builder est correcte
              const prefsUsable = (cc?.rows?.length > 0) || (cc?.values?.length > 0)
              if (prefsUpdatedAt >= configUpdatedAt && prefsUsable) {
                setLiveConfig(prev => ({
                  rows: cc.rows?.length ? cc.rows : prev.rows,
                  columns: cc.columns || prev.columns,
                  values: cc.values?.length ? cc.values : prev.values,
                  filters: cc.filters || prev.filters,
                }))
              }
            }
          } catch (e) {
            // Ignorer les erreurs de prefs
          }
        }

        // Charger les champs
        const dsIdentifier = data.data_source_code || data.data_source_id
        if (dsIdentifier) {
          try {
            const dsRes = await getUnifiedDataSource(dsIdentifier)
            const dsParams = dsRes.data?.data?.parameters
            setHasCatalogueParam(Array.isArray(dsParams)
              && dsParams.some(p => (p?.name || '').toLowerCase() === 'catalogue'))
          } catch (e) {
            setHasCatalogueParam(false)
          }
          try {
            const fieldsRes = await getUnifiedDataSourceFields(dsIdentifier)
            setAvailableFields(fieldsRes.data?.fields || [])
          } catch (e) {
            try {
              const fieldsRes2 = await getPivotV2Fields(dsIdentifier)
              setAvailableFields(fieldsRes2.data?.fields || [])
            } catch (e2) {
              // Ignorer
            }
          }
        }

        // Ne pas executer automatiquement — le GlobalFilterBar (openOnMount)
        // ouvrira le dialogue params et l'utilisateur cliquera "Appliquer"
      }
    } catch (err) {
      setError('Erreur de chargement du pivot')
    } finally {
      setLoading(false)
    }
  }

  // Executer le pivot
  const executePivot = async (configOverride, customLiveConfig) => {
    setExecuting(true)
    setError(null)
    // Une execution annulee n'est pas un echec : executePivotV2 passe par
    // cancelableRequest, qui avorte la requete precedente des qu'une nouvelle
    // part sur la meme cle. Changer la periode declenche plusieurs executions
    // successives ; sans ce drapeau, le rejet de l'AbortController tombait dans
    // le catch et affichait "Erreur execution du pivot" alors que la requete
    // suivante aboutissait normalement (d'ou des 200 OK cote serveur pour un
    // ecran en erreur). On laisse alors la main a l'execution qui a pris le
    // relais, sans toucher ni a l'erreur ni au drapeau de chargement.
    let canceled = false
    try {
      const ctx = {
        dateDebut: globalFilters?.dateDebut,
        dateFin: globalFilters?.dateFin,
        societe: globalFilters?.societe,
        commercial: globalFilters?.commercial,
        gamme: globalFilters?.gamme,
        catalogue: globalFilters?.catalogue,
      }
      // Utiliser customLiveConfig si fourni (evite le probleme d'async setState),
      // sinon utiliser liveConfig courant
      let effectiveLiveConfig = customLiveConfig || liveConfig
      // Ne jamais surcharger avec une config vide (config pas encore chargee, prefs
      // corrompues...) : le backend utiliserait alors une definition sans champ
      if (!(effectiveLiveConfig?.rows?.length) && !(effectiveLiveConfig?.values?.length)) {
        effectiveLiveConfig = null
      }
      const res = await executePivotV2(id, ctx, false, selectedDwhCode, effectiveLiveConfig)
      if (res.data?.success) {
        setPivotResult(res.data)
      } else {
        setError(res.data?.error || 'Erreur execution')
      }
    } catch (err) {
      if (isRequestCanceled(err)) {
        canceled = true
        return
      }
      setError('Erreur execution du pivot')
    } finally {
      if (!canceled) setExecuting(false)
    }
  }

  // Rafraichir
  const handleRefresh = () => {
    executePivot(pivotConfig)
  }

  // Construit l'URL de navigation drill-through avec filtres globaux propagés
  const buildDrillUrl = useCallback((rule, value, sourceName) => {
    const params = new URLSearchParams()
    params.set('dt_field', rule.target_filter_field)
    params.set('dt_value', value ?? '')
    params.set('dt_source', sourceName)
    if (globalFilters?.dateDebut) params.set('gf_dateDebut', globalFilters.dateDebut)
    if (globalFilters?.dateFin) params.set('gf_dateFin', globalFilters.dateFin)
    if (globalFilters?.societe) params.set('gf_societe', globalFilters.societe)
    return `${rule.target_url}?${params.toString()}`
  }, [globalFilters])

  // Drill-down / Drill-through
  const handleCellClick = useCallback((cellInfo) => {
    // Rechercher les règles drill-through applicables sur les dimensions de la cellule
    const matchedRules = []
    for (const [field, value] of Object.entries(cellInfo.rowValues || {})) {
      const rules = drillByColumn[field]
      if (rules?.length > 0) {
        rules.forEach(r => matchedRules.push({ rule: r, value, field }))
      }
    }

    if (matchedRules.length === 1) {
      const { rule, value } = matchedRules[0]
      navigate(buildDrillUrl(rule, value, pivotConfig?.nom || ''))
      return
    }

    if (matchedRules.length > 1) {
      const event = cellInfo.event
      setDrillMenu({
        x: event ? event.clientX : window.innerWidth / 2,
        y: event ? event.clientY : window.innerHeight / 2,
        items: matchedRules,
      })
      return
    }

    // Pas de règle drill-through → comportement interne (modal détail)
    setDrilldownCell(cellInfo)
    setDrilldownOpen(true)
  }, [drillByColumn, navigate, buildDrillUrl, pivotConfig?.nom])

  const fetchDrilldown = async (pivotId, request) => {
    try {
      const res = await drilldownPivotV2(pivotId, request)
      return res.data
    } catch (err) {
      return { success: false, error: err.message }
    }
  }

  // Export
  const [exporting, setExporting] = useState(false)
  const handleExport = async (format = 'excel') => {
    setExporting(true)
    setExportMenuOpen(false)
    try {
      const ctx = {
        dateDebut: globalFilters?.dateDebut,
        dateFin: globalFilters?.dateFin,
        societe: globalFilters?.societe,
      }
      const isBlob = format === 'excel' || format === 'pdf' || format === 'pptx'
      const res = await exportPivotV2(id, ctx, format, isBlob)

      if (isBlob && res.data instanceof Blob) {
        if (res.data.type === 'application/json' || res.data.size < 200) {
          try {
            const text = await res.data.text()
            const json = JSON.parse(text)
            if (!json.success) {
              setError(json.error || 'Erreur export')
              return
            }
          } catch (_) {
            // Blob is binary data (not JSON error) — proceed to download
          }
        }
        const ext = format === 'excel' ? 'xlsx' : format === 'pptx' ? 'pptx' : 'pdf'
        const url = URL.createObjectURL(res.data)
        const a = document.createElement('a')
        a.href = url
        a.download = `pivot_${id}.${ext}`
        a.click()
        URL.revokeObjectURL(url)
      } else if (res.data?.success) {
        if (format === 'csv' && res.data.content) {
          const blob = new Blob(['\ufeff' + res.data.content], { type: 'text/csv;charset=utf-8;' })
          const url = URL.createObjectURL(blob)
          const a = document.createElement('a')
          a.href = url
          a.download = res.data.filename || 'pivot.csv'
          a.click()
          URL.revokeObjectURL(url)
        }
      } else if (res.data?.error) {
        setError(res.data.error)
      }
    } catch (err) {
      setError('Erreur export')
    } finally {
      setExporting(false)
    }
  }

  // Sauvegarder les prefs utilisateur (debounce)
  const saveUserPrefs = useCallback((newConfig) => {
    if (!user?.id || !id) return
    if (saveTimer.current) clearTimeout(saveTimer.current)
    saveTimer.current = setTimeout(async () => {
      try {
        await savePivotV2UserPrefs(id, user.id, {
          custom_config: newConfig || liveConfig,
          ui_state: { viewMode, chartType },
        })
        localStorage.setItem(`pivotV2_prefs_${id}_${user.id}`, JSON.stringify(newConfig || liveConfig))
      } catch (e) { }
    }, 2000)
  }, [id, user?.id, liveConfig, viewMode, chartType])

  // Reset prefs
  const handleResetConfig = async () => {
    if (!pivotConfig) return
    setLiveConfig({
      rows: safeArray(pivotConfig.rows_config),
      columns: safeArray(pivotConfig.columns_config),
      values: safeArray(pivotConfig.values_config),
      filters: safeArray(pivotConfig.filters_config),
    })
    if (user?.id) {
      try {
        await resetPivotV2UserPrefs(id, user.id)
        localStorage.removeItem(`pivotV2_prefs_${id}_${user.id}`)
      } catch (e) { /* ignore */ }
    }
    handleRefresh()
  }

  // Appliquer la config du field chooser et sauvegarder en base
  const handleApplyFieldChooser = async (newConfig) => {
    // Une config sans ligne ni valeur n'affiche rien : ne jamais l'appliquer,
    // et surtout ne jamais l'ecrire en base (elle effacerait le pivot pour tous)
    const isEmpty = !(newConfig.rows?.length) && !(newConfig.values?.length)
    if (isEmpty) {
      setError('Configuration vide : ajoutez au moins un champ en Zone Ligne et en Zone Donnees.')
      return
    }
    setLiveConfig(newConfig)
    saveUserPrefs(newConfig)
    // Sauvegarder en base (APP_Pivots_V2) — même logique que le builder
    try {
      const upd = await updatePivotV2(id, {
        rows_config: newConfig.rows || [],
        columns_config: newConfig.columns || [],
        values_config: newConfig.values || [],
        filters_config: newConfig.filters || [],
      })
      if (upd?.data && upd.data.success === false) {
        console.error('Sauvegarde config pivot refusee:', upd.data.error)
      }
    } catch (e) {
      console.error('Erreur sauvegarde config pivot:', e)
    }
    // Passer newConfig directement — setLiveConfig est async, handleRefresh lirait l'ancienne valeur
    executePivot(pivotConfig, newConfig)
  }

  // Config presentee dans le field chooser : la config live, ou a defaut celle
  // enregistree par le concepteur (evite un dialogue avec toutes les zones vides)
  const chooserConfig = useMemo(() => {
    if (liveConfig.rows?.length || liveConfig.values?.length) return liveConfig
    return {
      rows: safeArray(pivotConfig?.rows_config),
      columns: safeArray(pivotConfig?.columns_config),
      values: safeArray(pivotConfig?.values_config),
      filters: safeArray(pivotConfig?.filters_config),
    }
  }, [liveConfig, pivotConfig])

  // Loading screen
  if (loading) {
    return (
      <div className="flex items-center justify-center h-full -m-3 lg:-m-4">
        <Loader2 size={28} className="animate-spin text-primary-500" />
      </div>
    )
  }

  // Error screen
  if (!pivotConfig) {
    return (
      <div className="flex items-center justify-center h-full -m-3 lg:-m-4">
        <div className="flex flex-col items-center text-center px-10 py-8 rounded-xl border border-dashed border-gray-200 dark:border-gray-700">
          <span className="flex items-center justify-center w-12 h-12 rounded-xl bg-gray-100 text-gray-400 dark:bg-gray-800 mb-3">
            <Table2 className="w-6 h-6" />
          </span>
          <p className="text-sm font-semibold text-gray-700 dark:text-gray-200">Pivot introuvable</p>
        </div>
      </div>
    )
  }

  const sourceRows = pivotResult?.metadata?.sourceRows || 0
  const pivotRows = pivotResult?.metadata?.totalRows || 0
  const execTime = pivotResult?.metadata?.executionTime || 0

  return (
    <div className={`flex flex-col overflow-hidden ${isMobile ? 'h-[calc(100dvh-112px)]' : 'h-full -m-3 lg:-m-4'}`}>
      {/* TOOLBAR — compact et unifié */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 gap-2 flex-shrink-0">
        {/* Gauche: titre + metadata */}
        <div className="flex items-center gap-3 min-w-0">
          {hasDoc(pivotConfig) ? (
            <button onClick={() => setShowDoc(true)} className="flex items-center gap-1.5 text-[15px] font-semibold text-gray-900 dark:text-white truncate hover:text-primary-600 dark:hover:text-primary-400 transition-colors">
              {pivotConfig.nom}
              <Info className="w-3.5 h-3.5 text-primary-400 flex-shrink-0" />
            </button>
          ) : (
            <h1 className="text-[15px] font-semibold text-gray-900 dark:text-white truncate">{pivotConfig.nom}</h1>
          )}
          {/* ── DEBUG WHERE : visible uniquement si effective_dwh = null ── */}
          {pivotResult?.debug && !pivotResult.debug.effective_dwh && !executing && (
            <button onClick={() => setShowDebug(v => !v)}
              className="ml-2 flex items-center gap-1 px-2 py-0.5 text-[10px] font-semibold text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/30 border border-amber-300 dark:border-amber-600 rounded hover:bg-amber-100 transition-colors">
              ⚠ Debug SQL
            </button>
          )}
        </div>

        {/* Droite: contrôles */}
        <div className="flex items-center gap-1">
          {/* Paramètres (filtres globaux) */}
          <GlobalFilterBar showSociete={true} showCatalogue={hasCatalogueParam} openOnMount triggerOpen={openParamsCount} onFilterChange={handleRefresh} />


          <div className="w-px h-5 bg-gray-200 dark:bg-gray-700 mx-0.5" />

          {/* Bouton Field Chooser — desktop seulement */}
          {!isMobile && (
            <button
              onClick={() => setFieldChooserOpen(true)}
              className="inline-flex items-center gap-1.5 h-8 px-2.5 text-xs font-semibold text-gray-600 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg hover:border-primary-400 hover:text-primary-600 transition-colors"
            >
              <Settings2 size={14} />
              <span className="hidden sm:inline">Champs</span>
            </button>
          )}

          <div className="w-px h-5 bg-gray-200 dark:bg-gray-700 mx-0.5" />

          {/* Boutons mode vue — desktop seulement */}
          {!isMobile && (
            <div className="flex bg-gray-100 dark:bg-gray-800 rounded-lg p-0.5">
              {VIEW_MODES.map(mode => {
                const ModeIcon = mode.icon
                return (
                  <button
                    key={mode.id}
                    onClick={() => setViewMode(mode.id)}
                    className={`p-1.5 rounded-md transition-colors ${
                      viewMode === mode.id
                        ? 'bg-white dark:bg-gray-700 text-primary-600 dark:text-primary-300 shadow-sm'
                        : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
                    }`}
                    title={mode.label}
                  >
                    <ModeIcon size={15} />
                  </button>
                )
              })}
            </div>
          )}

          {/* Chart controls — desktop seulement */}
          {!isMobile && (viewMode === 'chart' || viewMode === 'both') && (
            <>
              <select
                value={chartType}
                onChange={(e) => setChartType(e.target.value)}
                className="text-xs font-medium bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg h-8 text-gray-700 dark:text-gray-300 focus:ring-2 focus:ring-primary-500/30 focus:border-primary-400 outline-none px-2"
              >
                {CHART_TYPES.map(t => (
                  <option key={t.id} value={t.id}>{t.label}</option>
                ))}
              </select>

              {pivotResult?.valueFields?.length > 1 && pivotResult?.columnField && (
                <select
                  value={chartValueIndex ?? ''}
                  onChange={(e) => setChartValueIndex(e.target.value === '' ? null : parseInt(e.target.value))}
                  className="text-xs font-medium bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg h-8 text-gray-700 dark:text-gray-300 focus:ring-2 focus:ring-primary-500/30 focus:border-primary-400 outline-none px-2 max-w-[120px]"
                >
                  <option value="">Toutes mesures</option>
                  {pivotResult.valueFields.map((vf, i) => (
                    <option key={i} value={i}>{vf.label || vf.field}</option>
                  ))}
                </select>
              )}

              <div className="flex items-center gap-1">
                <label className="text-[11px] font-medium text-gray-400">Max</label>
                <input
                  type="number"
                  min={5}
                  max={500}
                  value={maxChartRows}
                  onChange={(e) => setMaxChartRows(Math.max(5, Math.min(500, parseInt(e.target.value) || 50)))}
                  className="w-14 text-xs font-medium bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg h-8 text-gray-700 dark:text-gray-300 focus:ring-2 focus:ring-primary-500/30 focus:border-primary-400 outline-none px-1.5 text-center"
                />
              </div>
            </>
          )}

          <div className="w-px h-5 bg-gray-200 dark:bg-gray-700 mx-0.5" />

          {/* Actions */}
          <button
            onClick={() => setOpenParamsCount(c => c + 1)}
            disabled={executing}
            className="w-8 h-8 flex items-center justify-center text-gray-500 hover:text-primary-600 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
            title="Rafraichir"
          >
            <RefreshCw size={15} className={executing ? 'animate-spin' : ''} />
          </button>

          <button
            onClick={handleResetConfig}
            className="w-8 h-8 flex items-center justify-center text-gray-500 hover:text-primary-600 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
            title="Reinitialiser la config"
          >
            <RotateCcw size={15} />
          </button>

          {/* Insights IA + Résumé Exécutif — desktop seulement */}
          {!isMobile && pivotConfig && pivotResult?.data?.length > 0 && (
            <>
              <InsightsPanel
                reportType="pivot"
                reportId={parseInt(id)}
                reportNom={pivotConfig.nom}
                data={pivotResult.data}
                columnsInfo={[]}
              />
              <ExecutiveSummaryModal
                reportType="pivot"
                reportId={parseInt(id)}
                reportNom={pivotConfig.nom}
                data={pivotResult.data}
                columnsInfo={[]}
              />
            </>
          )}

          {/* Favoris */}
          {pivotConfig && (
            <FavoriteButton reportType="pivot" reportId={parseInt(id)} reportNom={pivotConfig.nom} />
          )}
          {/* Abonnement email — desktop seulement */}
          {!isMobile && pivotConfig && (
            <SubscribeButton
              reportType="pivot"
              reportId={parseInt(id)}
              reportNom={pivotConfig.nom}
            />
          )}

          {!isMobile && <div className="w-px h-5 bg-gray-200 dark:bg-gray-700 mx-0.5" />}

          {/* Export menu — desktop seulement */}
          {!isMobile && <div className="relative" ref={exportMenuRef}>
            <button
              onClick={() => setExportMenuOpen(!exportMenuOpen)}
              className="h-8 px-2 text-gray-500 hover:text-primary-600 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors inline-flex items-center gap-0.5"
              disabled={exporting}
            >
              {exporting ? <Loader2 size={15} className="animate-spin" /> : <Download size={15} />}
              <ChevronDown size={10} />
            </button>
            {exportMenuOpen && !exporting && (
              <div className="absolute right-0 top-full mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-xl z-30 min-w-[170px] py-1">
                <button
                  onClick={() => handleExport('csv')}
                  className="flex items-center gap-2 w-full px-3 py-1.5 text-xs hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 transition-colors"
                >
                  <FileText size={13} /> Export CSV
                </button>
                <button
                  onClick={() => handleExport('excel')}
                  className="flex items-center gap-2 w-full px-3 py-1.5 text-xs hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 transition-colors"
                >
                  <FileSpreadsheet size={13} /> Export Excel
                </button>
                <button
                  onClick={() => handleExport('pdf')}
                  className="flex items-center gap-2 w-full px-3 py-1.5 text-xs hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 transition-colors"
                >
                  <FileText size={13} /> Export PDF
                </button>
                <div className="my-0.5 border-t border-gray-100 dark:border-gray-700" />
                <button
                  onClick={() => handleExport('pptx')}
                  className="flex items-center gap-2 w-full px-3 py-1.5 text-xs hover:bg-indigo-50 dark:hover:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 transition-colors font-medium"
                >
                  <Presentation size={13} /> PowerPoint (.pptx)
                </button>
              </div>
            )}
          </div>}
        </div>
      </div>

      {/* ── PANNEAU DEBUG WHERE ─────────────────────────────────────────────── */}
      {showDebug && pivotResult?.debug && (
        <div className="flex-shrink-0 bg-gray-950 text-green-300 text-xs font-mono border-b border-gray-700 overflow-auto" style={{ maxHeight: 280 }}>
          <div className="flex items-center justify-between px-4 py-2 bg-gray-900 border-b border-gray-700">
            <span className="text-amber-400 font-bold">⚠ Debug WHERE — Valeurs injectées</span>
            <button onClick={() => setShowDebug(false)} className="text-gray-400 hover:text-white text-base leading-none">✕</button>
          </div>
          <div className="p-4 space-y-3">
            <div>
              <div className="text-yellow-400 mb-1 font-bold">── Contexte passé ──</div>
              {Object.entries(pivotResult.debug.context_passed || {}).map(([k, v]) => (
                <div key={k}><span className="text-blue-300">@{k}</span> = <span className="text-white">{JSON.stringify(v)}</span></div>
              ))}
            </div>
            <div>
              <div className="text-yellow-400 mb-1 font-bold">── DWH utilisé ──</div>
              <div><span className="text-blue-300">datasource</span> = <span className="text-white">{pivotResult.debug.datasource_code}</span></div>
              <div><span className="text-blue-300">origin</span> = <span className="text-white">{pivotResult.debug.datasource_origin}</span></div>
              <div><span className={`text-blue-300`}>effective_dwh</span> = <span className={pivotResult.debug.effective_dwh ? 'text-green-400' : 'text-red-400 font-bold'}>{pivotResult.debug.effective_dwh || '❌ NULL — aucun DWH connecté!'}</span></div>
            </div>
            <div>
              <div className="text-yellow-400 mb-1 font-bold">── Requête SQL injectée ──</div>
              <pre className="text-gray-300 whitespace-pre-wrap leading-relaxed">{pivotResult.debug.query_injected}</pre>
            </div>
          </div>
        </div>
      )}
      {/* ─────────────────────────────────────────────────────────────────────── */}

      {/* CONTENU */}
      <div className="flex-1 flex flex-col overflow-hidden p-3 bg-slate-50 dark:bg-gray-950" style={{ minHeight: 0 }}>
        {error && (
          <div className="mb-3 px-3 py-2.5 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 rounded-lg text-sm flex-shrink-0 flex items-center justify-between">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="p-0.5 hover:bg-red-100 dark:hover:bg-red-900/40 rounded">
              <X size={14} />
            </button>
          </div>
        )}

        {executing && (
          <div className="flex items-center justify-center flex-1">
            <div className="text-center">
              <Loader2 size={28} className="animate-spin text-primary-500 mx-auto mb-2" />
              <p className="text-xs text-gray-400">Chargement des données…</p>
            </div>
          </div>
        )}

        {!executing && pivotResult && (
          <div className="flex-1 flex flex-col" style={{ minHeight: 0 }}>
            {/* Tableau */}
            {(viewMode === 'table' || viewMode === 'both') && (
              <PivotTable
                data={pivotResult.data || []}
                pivotColumns={pivotResult.pivotColumns || []}
                rowFields={pivotResult.rowFields || []}
                columnField={pivotResult.columnField}
                valueFields={pivotResult.valueFields || []}
                formattingRules={pivotResult.formattingRules || []}
                comparison={pivotResult.comparison}
                options={pivotResult.options || {}}
                windowCalculations={pivotResult.windowCalculations || []}
                summaryFunctions={pivotResult.summaryFunctions || []}
                onCellClick={handleCellClick}
                className=""
              />
            )}

            {/* Chart */}
            {(viewMode === 'chart' || viewMode === 'both') && (
              <PivotChart
                data={pivotResult.data || []}
                pivotColumns={pivotResult.pivotColumns || []}
                rowFields={pivotResult.rowFields || []}
                columnField={pivotResult.columnField}
                valueFields={pivotResult.valueFields || []}
                chartType={chartType}
                maxRows={maxChartRows}
                selectedValueIndex={chartValueIndex}
                onCellClick={handleCellClick}
                className={`bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl shadow-sm p-4 ${viewMode === 'both' ? 'mt-3' : ''} flex-shrink-0`}
              />
            )}
          </div>
        )}

        {!executing && !pivotResult && !error && (
          <div className="flex items-center justify-center flex-1">
            <div className="flex flex-col items-center text-center px-10 py-8 rounded-xl border border-dashed border-gray-200 dark:border-gray-700 bg-white/70 dark:bg-gray-900/30">
              <span className="flex items-center justify-center w-12 h-12 rounded-xl bg-primary-50 text-primary-500 dark:bg-primary-900/30 mb-3">
                <Table2 className="w-6 h-6" />
              </span>
              <p className="text-sm font-semibold text-gray-700 dark:text-gray-200">Aucune donnée affichée</p>
              <p className="text-xs text-gray-400 mt-1">Cliquez sur Rafraîchir pour charger les données</p>
            </div>
          </div>
        )}
      </div>

      {/* Field Chooser Dialog */}
      <FieldChooserDialog
        open={fieldChooserOpen}
        onClose={() => setFieldChooserOpen(false)}
        availableFields={availableFields}
        liveConfig={chooserConfig}
        onApply={handleApplyFieldChooser}
      />

      {/* Drill-down Modal */}
      <DrillDownModal
        isOpen={drilldownOpen}
        onClose={() => setDrilldownOpen(false)}
        pivotId={id}
        cellInfo={drilldownCell}
        context={{
          dateDebut: globalFilters?.dateDebut,
          dateFin: globalFilters?.dateFin,
          societe: globalFilters?.societe,
          commercial: globalFilters?.commercial,
          gamme: globalFilters?.gamme,
        }}
        fetchDrilldown={fetchDrilldown}
        drilldownDsCode={pivotConfig?.drilldown_data_source_code}
        mainDsCode={pivotConfig?.data_source_code}
      />

      {/* Menu contextuel drill-through multi-règles (Pivot) */}
      {drillMenu && (
        <>
          <div className="fixed inset-0 z-50" onClick={() => setDrillMenu(null)} />
          <div
            className="fixed z-50 bg-white dark:bg-gray-800 rounded-xl shadow-xl border border-gray-200 dark:border-gray-700 py-1 min-w-[220px]"
            style={{ left: drillMenu.x, top: drillMenu.y }}
          >
            <div className="px-3 py-1.5 text-[10px] font-semibold text-gray-400 uppercase tracking-wide border-b border-gray-100 dark:border-gray-700">
              <ExternalLink className="w-3 h-3 inline mr-1" />Naviguer vers...
            </div>
            {drillMenu.items.map(({ rule, value, field }, i) => (
              <button
                key={i}
                onClick={() => {
                  const url = buildDrillUrl(rule, value, pivotConfig?.nom || '')
                  setDrillMenu(null)
                  navigate(url)
                }}
                className="w-full text-left px-3 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-primary-50 dark:hover:bg-primary-900/20 hover:text-primary-700 dark:hover:text-primary-300 transition-colors"
              >
                <span className="text-xs text-gray-400 mr-1.5">{field}:</span>
                {rule.label || rule.nom}
              </button>
            ))}
          </div>
        </>
      )}

      {showDoc && <ReportDocModal title={pivotConfig.nom} config={pivotConfig} onClose={() => setShowDoc(false)} />}
    </div>
  )
}
