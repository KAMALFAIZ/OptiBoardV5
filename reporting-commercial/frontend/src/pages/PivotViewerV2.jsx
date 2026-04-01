import { useState, useEffect, useCallback, useRef } from 'react'
import { useParams } from 'react-router-dom'
import { useIsMobile } from '../hooks/useIsMobile'
import { useAuth } from '../context/AuthContext'
import { useSettings } from '../context/SettingsContext'
import { useGlobalFilters } from '../context/GlobalFilterContext'
import {
  getPivotV2, executePivotV2, drilldownPivotV2, exportPivotV2,
  getPivotV2Fields, getPivotV2UserPrefs, savePivotV2UserPrefs, resetPivotV2UserPrefs,
  getUnifiedDataSourceFields
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
  ChevronDown
} from 'lucide-react'

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

  const handleApply = () => {
    onApply(config)
    onClose()
  }

  const ZoneBox = ({ zone, title, icon, fields, maxFields, color = 'gray' }) => {
    const colorClasses = {
      blue: 'border-blue-200 dark:border-blue-800 bg-blue-50/50 dark:bg-blue-900/10',
      green: 'border-green-200 dark:border-green-800 bg-green-50/50 dark:bg-green-900/10',
      amber: 'border-amber-200 dark:border-amber-800 bg-amber-50/50 dark:bg-amber-900/10',
      purple: 'border-purple-200 dark:border-purple-800 bg-purple-50/50 dark:bg-purple-900/10',
    }
    const labelColors = {
      blue: 'text-blue-700 dark:text-blue-300',
      green: 'text-green-700 dark:text-green-300',
      amber: 'text-amber-700 dark:text-amber-300',
      purple: 'text-purple-700 dark:text-purple-300',
    }
    return (
      <div
        className={`rounded-lg border-2 border-dashed p-2 min-h-[100px] transition-colors ${colorClasses[color]}`}
        onDragOver={(e) => { e.preventDefault(); e.currentTarget.classList.add('ring-2', 'ring-blue-400') }}
        onDragLeave={(e) => { e.currentTarget.classList.remove('ring-2', 'ring-blue-400') }}
        onDrop={(e) => { e.preventDefault(); e.currentTarget.classList.remove('ring-2', 'ring-blue-400'); handleDrop(zone) }}
      >
        <div className={`text-xs font-bold mb-1.5 ${labelColors[color]} flex items-center gap-1`}>
          {icon} {title}
          {maxFields && <span className="text-[10px] font-normal opacity-60">({maxFields} max)</span>}
        </div>
        <div className="space-y-1">
          {fields.map((f, idx) => (
            <div
              key={f.field}
              draggable
              onDragStart={() => handleDragStart(f, zone)}
              className="flex items-center gap-1 bg-white dark:bg-gray-800 rounded px-2 py-1.5 text-xs border border-gray-200 dark:border-gray-700 shadow-sm cursor-grab active:cursor-grabbing group hover:border-blue-300"
            >
              <GripVertical size={12} className="text-gray-300 flex-shrink-0" />
              <span className="flex-1 truncate font-medium text-gray-700 dark:text-gray-300">
                {f.label || f.field}
              </span>
              {zone === 'values' && (
                <select
                  value={f.aggregation || 'SUM'}
                  onChange={(e) => handleChangeAgg(idx, e.target.value)}
                  onClick={(e) => e.stopPropagation()}
                  className="text-[10px] bg-gray-100 dark:bg-gray-700 border-0 rounded px-1 py-0.5 text-gray-500 dark:text-gray-400 max-w-[70px]"
                >
                  {AGGREGATIONS.map(a => (
                    <option key={a.value} value={a.value}>{a.label}</option>
                  ))}
                </select>
              )}
              <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                <button onClick={() => handleMoveUp(zone, idx)} className="p-0.5 text-gray-400 hover:text-gray-600" title="Monter"><ArrowUp size={10} /></button>
                <button onClick={() => handleMoveDown(zone, idx)} className="p-0.5 text-gray-400 hover:text-gray-600" title="Descendre"><ArrowDown size={10} /></button>
                <button onClick={() => handleRemoveFromZone(zone, f.field)} className="p-0.5 text-red-400 hover:text-red-600" title="Retirer"><X size={10} /></button>
              </div>
            </div>
          ))}
          {fields.length === 0 && (
            <div className="text-[10px] text-gray-400 italic text-center py-3">
              Glisser des champs ici
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-2xl border border-gray-200 dark:border-gray-700 w-[720px] max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-sm font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Settings2 size={16} />
            Configuration des champs
          </h2>
          <button onClick={onClose} className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800">
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-auto p-4">
          <div className="flex gap-4">
            {/* Liste des champs disponibles */}
            <div className="w-48 flex-shrink-0">
              <div className="text-xs font-bold text-gray-700 dark:text-gray-300 mb-2">
                Champs disponibles
              </div>
              <div className="border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-800/50 max-h-[400px] overflow-y-auto">
                {unusedFields.length === 0 && (
                  <div className="text-[10px] text-gray-400 italic text-center py-4">
                    Tous les champs sont utilises
                  </div>
                )}
                {unusedFields.map(f => (
                  <div
                    key={f.name}
                    draggable
                    onDragStart={() => handleDragStart(f, 'available')}
                    className="flex items-center gap-2 px-2.5 py-1.5 text-xs cursor-grab active:cursor-grabbing hover:bg-white dark:hover:bg-gray-700 border-b border-gray-100 dark:border-gray-700/50 last:border-b-0 transition-colors"
                  >
                    <GripVertical size={11} className="text-gray-300 flex-shrink-0" />
                    <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${f.type === 'number' ? 'bg-blue-400' : f.type === 'date' ? 'bg-amber-400' : 'bg-gray-400'}`} />
                    <span className="truncate text-gray-600 dark:text-gray-400">{f.label || f.name}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Zones de drop */}
            <div className="flex-1 grid grid-cols-2 gap-3">
              <ZoneBox zone="filters" title="Zone Filtre" icon="🔍" fields={config.filters} color="amber" />
              <ZoneBox zone="columns" title="Zone Colonne" icon="⬛" fields={config.columns} maxFields={1} color="green" />
              <ZoneBox zone="rows" title="Zone Ligne" icon="☰" fields={config.rows} color="blue" />
              <ZoneBox zone="values" title="Zone Donnees" icon="Σ" fields={config.values} color="purple" />
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
        <div className="flex items-center justify-end gap-2 px-5 py-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 rounded-b-xl">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-medium text-gray-600 dark:text-gray-400 bg-white dark:bg-gray-800 border border-primary-300 dark:border-primary-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          >
            Annuler
          </button>
          <button
            onClick={handleApply}
            className="px-4 py-2 text-xs font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-1.5"
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
  const { user } = useAuth()
  const { formatNumber } = useSettings()
  const { filters: globalFilters } = useGlobalFilters()
  const isMobile = useIsMobile()

  // Config pivot
  const [pivotConfig, setPivotConfig] = useState(null)
  const [loading, setLoading] = useState(true)
  const [executing, setExecuting] = useState(false)
  const [error, setError] = useState(null)

  // Donnees pivotees
  const [pivotResult, setPivotResult] = useState(null)
  const [showDebug, setShowDebug] = useState(false)
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
  const [fieldChooserOpen, setFieldChooserOpen] = useState(false)
  const [exportMenuOpen, setExportMenuOpen] = useState(false)
  const [openParamsCount, setOpenParamsCount] = useState(0)

  // Drill-down
  const [drilldownOpen, setDrilldownOpen] = useState(false)
  const [drilldownCell, setDrilldownCell] = useState(null)

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
  }, [globalFilters?.dateDebut, globalFilters?.dateFin, globalFilters?.societe])

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
    try {
      const res = await getPivotV2(id)
      if (res.data?.success) {
        const data = res.data.data
        setPivotConfig(data)

        // Init live config depuis la config admin
        setLiveConfig({
          rows: data.rows_config || [],
          columns: data.columns_config || [],
          values: data.values_config || [],
          filters: data.filters_config || [],
        })

        // Charger les preferences utilisateur
        if (user?.id) {
          try {
            const prefsRes = await getPivotV2UserPrefs(id, user.id)
            if (prefsRes.data?.has_prefs && prefsRes.data?.data?.custom_config) {
              const cc = prefsRes.data.data.custom_config
              setLiveConfig(prev => ({
                rows: cc.rows || prev.rows,
                columns: cc.columns || prev.columns,
                values: cc.values || prev.values,
                filters: cc.filters || prev.filters,
              }))
            }
          } catch (e) {
            // Ignorer les erreurs de prefs
          }
        }

        // Charger les champs
        const dsIdentifier = data.data_source_code || data.data_source_id
        if (dsIdentifier) {
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

        // Executer automatiquement
        await executePivot(data)
      }
    } catch (err) {
      setError('Erreur de chargement du pivot')
    } finally {
      setLoading(false)
    }
  }

  // Executer le pivot
  const executePivot = async (configOverride) => {
    setExecuting(true)
    setError(null)
    try {
      const ctx = {
        dateDebut: globalFilters?.dateDebut,
        dateFin: globalFilters?.dateFin,
        societe: globalFilters?.societe,
        commercial: globalFilters?.commercial,
        gamme: globalFilters?.gamme,
      }
      const res = await executePivotV2(id, ctx, false, selectedDwhCode)
      if (res.data?.success) {
        setPivotResult(res.data)
      } else {
        setError(res.data?.error || 'Erreur execution')
      }
    } catch (err) {
      setError('Erreur execution du pivot')
    } finally {
      setExecuting(false)
    }
  }

  // Rafraichir
  const handleRefresh = () => {
    executePivot(pivotConfig)
  }

  // Drill-down
  const handleCellClick = (cellInfo) => {
    setDrilldownCell(cellInfo)
    setDrilldownOpen(true)
  }

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
      const isBlob = format === 'excel' || format === 'pdf'
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
          } catch (_) { }
        }
        const ext = format === 'excel' ? 'xlsx' : 'pdf'
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
      rows: pivotConfig.rows_config || [],
      columns: pivotConfig.columns_config || [],
      values: pivotConfig.values_config || [],
      filters: pivotConfig.filters_config || [],
    })
    if (user?.id) {
      try {
        await resetPivotV2UserPrefs(id, user.id)
        localStorage.removeItem(`pivotV2_prefs_${id}_${user.id}`)
      } catch (e) { /* ignore */ }
    }
    handleRefresh()
  }

  // Appliquer la config du field chooser
  const handleApplyFieldChooser = (newConfig) => {
    setLiveConfig(newConfig)
    saveUserPrefs(newConfig)
    // Re-executer
    handleRefresh()
  }

  // Loading screen
  if (loading) {
    return (
      <div className="flex items-center justify-center h-full -m-3 lg:-m-4">
        <Loader2 size={32} className="animate-spin text-blue-500" />
      </div>
    )
  }

  // Error screen
  if (!pivotConfig) {
    return (
      <div className="flex items-center justify-center h-full -m-3 lg:-m-4 text-gray-500">
        Pivot non trouve
      </div>
    )
  }

  const sourceRows = pivotResult?.metadata?.sourceRows || 0
  const pivotRows = pivotResult?.metadata?.totalRows || 0
  const execTime = pivotResult?.metadata?.executionTime || 0

  return (
    <div className={`flex flex-col overflow-hidden ${isMobile ? 'h-[calc(100dvh-112px)]' : 'h-full -m-3 lg:-m-4'}`}>
      {/* TOOLBAR — compact et unifié */}
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 gap-2 flex-shrink-0">
        {/* Gauche: titre + metadata */}
        <div className="flex items-center gap-3 min-w-0">
          <h1 className="text-base font-bold text-gray-900 dark:text-white truncate">{pivotConfig.nom}</h1>
          {pivotResult && !executing && (
            <div className="hidden sm:flex items-center gap-1.5 text-[10px] text-gray-400">
              <span className="bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded">{sourceRows.toLocaleString('fr-FR')} lignes source</span>
              <span className="bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded">{pivotRows.toLocaleString('fr-FR')} lignes pivot</span>
              <span className="bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded">{execTime}ms</span>
            </div>
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
          <GlobalFilterBar showSociete={true} openOnMount triggerOpen={openParamsCount} onFilterChange={handleRefresh} />


          <div className="w-px h-5 bg-gray-200 dark:bg-gray-700 mx-0.5" />

          {/* Bouton Field Chooser — desktop seulement */}
          {!isMobile && (
            <button
              onClick={() => setFieldChooserOpen(true)}
              className="inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
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
                        ? 'bg-white dark:bg-gray-700 text-blue-600 dark:text-blue-400 shadow-sm'
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
                className="text-xs bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-2 py-1.5 text-gray-600 dark:text-gray-400"
              >
                {CHART_TYPES.map(t => (
                  <option key={t.id} value={t.id}>{t.label}</option>
                ))}
              </select>

              {pivotResult?.valueFields?.length > 1 && pivotResult?.columnField && (
                <select
                  value={chartValueIndex ?? ''}
                  onChange={(e) => setChartValueIndex(e.target.value === '' ? null : parseInt(e.target.value))}
                  className="text-xs bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-2 py-1.5 text-gray-600 dark:text-gray-400 max-w-[120px]"
                >
                  <option value="">Toutes mesures</option>
                  {pivotResult.valueFields.map((vf, i) => (
                    <option key={i} value={i}>{vf.label || vf.field}</option>
                  ))}
                </select>
              )}

              <div className="flex items-center gap-1">
                <label className="text-[10px] text-gray-400">Max:</label>
                <input
                  type="number"
                  min={5}
                  max={500}
                  value={maxChartRows}
                  onChange={(e) => setMaxChartRows(Math.max(5, Math.min(500, parseInt(e.target.value) || 50)))}
                  className="w-12 text-xs bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-1.5 py-1.5 text-gray-600 dark:text-gray-400 text-center"
                />
              </div>
            </>
          )}

          <div className="w-px h-5 bg-gray-200 dark:bg-gray-700 mx-0.5" />

          {/* Actions */}
          <button
            onClick={() => setOpenParamsCount(c => c + 1)}
            disabled={executing}
            className="p-1.5 text-gray-500 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors"
            title="Rafraichir"
          >
            <RefreshCw size={15} className={executing ? 'animate-spin' : ''} />
          </button>

          <button
            onClick={handleResetConfig}
            className="p-1.5 text-gray-500 hover:text-amber-600 hover:bg-amber-50 dark:hover:bg-amber-900/20 rounded-lg transition-colors"
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
              className="p-1.5 text-gray-500 hover:text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20 rounded-lg transition-colors inline-flex items-center gap-0.5"
              disabled={exporting}
            >
              {exporting ? <Loader2 size={15} className="animate-spin" /> : <Download size={15} />}
              <ChevronDown size={10} />
            </button>
            {exportMenuOpen && !exporting && (
              <div className="absolute right-0 top-full mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-xl z-30 min-w-[140px] py-1">
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
      <div className="flex-1 flex flex-col overflow-hidden p-3" style={{ minHeight: 0 }}>
        {error && (
          <div className="mb-3 px-4 py-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 rounded-lg text-sm flex-shrink-0 flex items-center justify-between">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="p-0.5 hover:bg-red-100 dark:hover:bg-red-900/40 rounded">
              <X size={14} />
            </button>
          </div>
        )}

        {executing && (
          <div className="flex items-center justify-center flex-1">
            <div className="text-center">
              <Loader2 size={32} className="animate-spin text-blue-500 mx-auto mb-2" />
              <p className="text-xs text-gray-400">Chargement des donnees...</p>
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
                className={`bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-4 ${viewMode === 'both' ? 'mt-3' : ''} flex-shrink-0`}
              />
            )}
          </div>
        )}

        {!executing && !pivotResult && !error && (
          <div className="flex items-center justify-center flex-1 text-gray-400 text-sm">
            Cliquez sur Rafraichir pour charger les donnees
          </div>
        )}
      </div>

      {/* Field Chooser Dialog */}
      <FieldChooserDialog
        open={fieldChooserOpen}
        onClose={() => setFieldChooserOpen(false)}
        availableFields={availableFields}
        liveConfig={liveConfig}
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
      />
    </div>
  )
}
