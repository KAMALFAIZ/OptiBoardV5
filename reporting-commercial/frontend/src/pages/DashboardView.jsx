import { useState, useEffect, useMemo, useRef, useCallback } from 'react'
import { useParams, Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useIsMobile } from '../hooks/useIsMobile'
import {
  BarChart2, LineChart, PieChart, Activity, Table, Type, Gauge,
  RefreshCw, Edit, AlertCircle, LayoutGrid, X, Download, Search,
  ChevronLeft, ChevronRight, ArrowUpDown, TrendingUp, TrendingDown, Settings2,
  Filter, Layers, Target, Zap, Image, GitBranch, BarChart3, Timer, SlidersHorizontal
} from 'lucide-react'
import {
  BarChart, Bar, LineChart as ReLineChart, Line, PieChart as RePieChart, Pie, Cell,
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  RadialBarChart, RadialBar, ComposedChart, Treemap as ReTreemap,
  FunnelChart, Funnel, LabelList
} from 'recharts'
import GridLayout from 'react-grid-layout'
import 'react-grid-layout/css/styles.css'
import 'react-resizable/css/styles.css'
import Loading from '../components/common/Loading'
import SubscribeButton from '../components/common/SubscribeButton'
import FavoriteButton from '../components/common/FavoriteButton'
import InsightsPanel from '../components/common/InsightsPanel'
import ExecutiveSummaryModal from '../components/common/ExecutiveSummaryModal'
import api, { getBuilderDashboard, previewDataSource, previewUnifiedDataSource, extractErrorMessage } from '../services/api'
import { useTheme } from '../context/ThemeContext'
import { useGlobalFilters } from '../context/GlobalFilterContext'
import GlobalFilterBar from '../components/GlobalFilterBar'

// ─── Widget types ───
const WIDGET_TYPE_MAP = {
  kpi: { icon: Activity, color: 'bg-blue-500' },
  kpi_compare: { icon: TrendingUp, color: 'bg-emerald-500' },
  gauge: { icon: Gauge, color: 'bg-cyan-500' },
  progress: { icon: Target, color: 'bg-lime-500' },
  sparkline: { icon: Zap, color: 'bg-rose-500' },
  chart_bar: { icon: BarChart2, color: 'bg-indigo-500' },
  chart_stacked_bar: { icon: BarChart3, color: 'bg-violet-500' },
  chart_line: { icon: LineChart, color: 'bg-teal-500' },
  chart_combo: { icon: GitBranch, color: 'bg-fuchsia-500' },
  chart_pie: { icon: PieChart, color: 'bg-amber-500' },
  chart_area: { icon: LineChart, color: 'bg-purple-500' },
  chart_funnel: { icon: Filter, color: 'bg-orange-500' },
  chart_treemap: { icon: Layers, color: 'bg-pink-500' },
  table: { icon: Table, color: 'bg-gray-500' },
  text: { icon: Type, color: 'bg-slate-500' },
  image: { icon: Image, color: 'bg-sky-500' },
}

function generateThemeColors(theme) {
  if (!theme?.colors?.primary) {
    return ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#14b8a6']
  }
  const p = theme.colors.primary
  return [p[600], theme.colors.accent, p[400], p[800], '#f59e0b', '#8b5cf6', p[300], '#ec4899', '#f97316', '#14b8a6']
}

const formatNumber = (val) => {
  if (val === null || val === undefined) return '0'
  const n = Number(val)
  if (isNaN(n)) return '0'
  return n.toLocaleString('fr-FR', { minimumFractionDigits: 0, maximumFractionDigits: 2 })
}

// Auto-détecte x_field (catégoriel) et y_field (numérique) à partir des données
function autoDetectFields(data, cfg) {
  const keys = Object.keys(data[0] || {})
  if (keys.length === 0) return { xf: '', yf: '' }

  const xf = cfg.x_field || keys[0]

  if (cfg.y_field) return { xf, yf: cfg.y_field }

  // Chercher le premier champ numérique différent de x_field
  for (const k of keys) {
    if (k === xf) continue
    const sample = data[0][k]
    if (typeof sample === 'number' || (typeof sample === 'string' && !isNaN(Number(sample)) && sample.trim() !== '')) {
      return { xf, yf: k }
    }
  }
  // Fallback: deuxième champ
  return { xf, yf: keys[1] || keys[0] }
}

// ─── Aggregation helper ───
function aggregateData(data, field, func = 'SUM') {
  if (!data?.length || !field) return 0
  const values = data.map(r => Number(r[field]) || 0).filter(v => !isNaN(v))
  if (!values.length) return 0
  switch (func) {
    case 'SUM': return values.reduce((a, b) => a + b, 0)
    case 'AVG': return values.reduce((a, b) => a + b, 0) / values.length
    case 'COUNT': return values.length
    case 'MIN': return Math.min(...values)
    case 'MAX': return Math.max(...values)
    case 'FIRST': return values[0]
    case 'LAST': return values[values.length - 1]
    default: return values.reduce((a, b) => a + b, 0)
  }
}

// ─── Conditional formatting ───
function getConditionalColor(value, thresholds) {
  if (!thresholds?.length) return null
  const sorted = [...thresholds].sort((a, b) => b.value - a.value)
  for (const t of sorted) {
    if (value >= t.value) return t.color
  }
  return sorted[sorted.length - 1]?.color || null
}

// ════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ════════════════════════════════════════════════════════════════════
export default function DashboardView() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const isMobile = useIsMobile()
  const { filters: contextFilters, updateFilter } = useGlobalFilters()
  const [loading, setLoading] = useState(true)
  const [dashboard, setDashboard] = useState(null)
  const [error, setError] = useState(null)
  const [refreshKey, setRefreshKey] = useState(0)
  const [openParamsCount, setOpenParamsCount] = useState(0)
  const [widgetFilters, setWidgetFilters] = useState({})
  const [drillByColumn, setDrillByColumn] = useState({})
  const [detailModal, setDetailModal] = useState({ isOpen: false, title: '', data: [], filterField: null, filterValue: null })
  const [containerWidth, setContainerWidth] = useState(1200)
  // Bloque le chargement des widgets jusqu'à ce que l'utilisateur confirme les paramètres
  const [paramsConfirmed, setParamsConfirmed] = useState(false)
  const containerRef = useRef(null)
  const autoRefreshRef = useRef(null)

  // Cache de deduplication : si plusieurs widgets utilisent la meme DataSource,
  // un seul appel API est fait et les autres attendent le resultat
  const dataSourceCacheRef = useRef(new Map())

  // Vider le cache quand refreshKey change (actualiser)
  useEffect(() => {
    dataSourceCacheRef.current = new Map()
  }, [refreshKey])

  // Données collectées depuis les widgets (pour InsightsPanel)
  const [insightsData, setInsightsData] = useState([])

  const fetchSharedData = useCallback((dsCode, dsId, isTemplate, filters) => {
    const cacheKey = `${dsCode || dsId}::${JSON.stringify(filters || {})}`
    const cache = dataSourceCacheRef.current

    if (cache.has(cacheKey)) {
      return cache.get(cacheKey)
    }

    // Creer la promesse et la stocker immediatement (deduplication)
    const promise = (async () => {
      let res
      if (dsCode && isTemplate) {
        res = await previewUnifiedDataSource(dsCode, filters || {}, null, 0)
      } else {
        res = await previewDataSource(dsId || dsCode, filters || {}, 0)
      }
      // Collecter les données pour InsightsPanel (premier widget avec données)
      const rows = res?.data?.data || []
      if (rows.length > 0) {
        setInsightsData(prev => prev.length === 0 ? rows : prev)
      }
      return res
    })()

    cache.set(cacheKey, promise)
    return promise
  }, [])

  // Combiner les filtres globaux (date, societe) avec les filtres de widgets
  const mergedFilters = useMemo(() => {
    const base = {}
    if (contextFilters?.dateDebut) base.dateDebut = contextFilters.dateDebut
    if (contextFilters?.dateFin) base.dateFin = contextFilters.dateFin
    if (contextFilters?.societe) base.societe = contextFilters.societe
    if (contextFilters?.commercial) base.commercial = contextFilters.commercial
    if (contextFilters?.gamme) base.gamme = contextFilters.gamme
    return { ...base, ...widgetFilters }
  }, [contextFilters, widgetFilters])

  // Re-executer quand les filtres globaux changent
  const prevFiltersRef = useRef(null)
  useEffect(() => {
    if (!dashboard) return
    const currentFilters = JSON.stringify({
      dateDebut: contextFilters?.dateDebut,
      dateFin: contextFilters?.dateFin,
      societe: contextFilters?.societe,
    })
    if (prevFiltersRef.current && prevFiltersRef.current !== currentFilters) {
      setRefreshKey(k => k + 1)
    }
    prevFiltersRef.current = currentFilters
  }, [contextFilters?.dateDebut, contextFilters?.dateFin, contextFilters?.societe, dashboard])

  const widgets = dashboard?.widgets || []
  const autoRefreshInterval = dashboard?.auto_refresh || 0

  const layout = useMemo(() =>
    widgets.map(w => ({ i: w.id, x: w.x || 0, y: w.y || 0, w: w.w || 4, h: w.h || 4, static: true })),
    [widgets]
  )

  useEffect(() => { loadDashboard() }, [id])

  // Appliquer les filtres globaux transmis par le rapport source (une seule fois au montage)
  useEffect(() => {
    const gfDateDebut = searchParams.get('gf_dateDebut')
    const gfDateFin = searchParams.get('gf_dateFin')
    const gfSociete = searchParams.get('gf_societe')
    if (gfDateDebut) updateFilter('dateDebut', gfDateDebut)
    if (gfDateFin) updateFilter('dateFin', gfDateFin)
    if (gfSociete) updateFilter('societe', gfSociete)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!id) return
    api.get(`/drillthrough/rules/by-source?source_type=dashboard&source_id=${id}`)
      .then(res => { if (res.data.success) setDrillByColumn(res.data.by_column || {}) })
      .catch(() => {})
  }, [id])

  useEffect(() => {
    if (!containerRef.current) return
    const ro = new ResizeObserver(entries => { for (const e of entries) setContainerWidth(e.contentRect.width) })
    ro.observe(containerRef.current)
    setContainerWidth(containerRef.current.clientWidth)
    return () => ro.disconnect()
  }, [dashboard])

  // Auto-refresh
  useEffect(() => {
    if (autoRefreshRef.current) clearInterval(autoRefreshRef.current)
    if (autoRefreshInterval > 0) {
      autoRefreshRef.current = setInterval(() => setRefreshKey(k => k + 1), autoRefreshInterval * 1000)
    }
    return () => { if (autoRefreshRef.current) clearInterval(autoRefreshRef.current) }
  }, [autoRefreshInterval])

  const loadDashboard = async () => {
    setLoading(true); setError(null)
    setParamsConfirmed(false)  // Réinitialiser à chaque changement de dashboard
    try {
      const res = await getBuilderDashboard(id)
      setDashboard(res.data.data)
    } catch (e) {
      console.error('Erreur:', e)
      setError('Impossible de charger ce dashboard')
    } finally { setLoading(false) }
  }

  const buildDrillUrl = (rule, value, sourceName) => {
    const params = new URLSearchParams()
    params.set('dt_field', rule.target_filter_field)
    params.set('dt_value', value ?? '')
    params.set('dt_source', sourceName)
    if (contextFilters?.dateDebut) params.set('gf_dateDebut', contextFilters.dateDebut)
    if (contextFilters?.dateFin) params.set('gf_dateFin', contextFilters.dateFin)
    if (contextFilters?.societe) params.set('gf_societe', contextFilters.societe)
    return `${rule.target_url}?${params.toString()}`
  }

  const openDetail = (title, data, filter) => {
    // Si une règle drill-through est configurée pour ce champ, naviguer vers la cible
    if (filter?.field && drillByColumn[filter.field]?.length > 0) {
      const rule = drillByColumn[filter.field][0]
      navigate(buildDrillUrl(rule, filter.value, dashboard?.nom || title))
      return
    }
    // Sinon, comportement modal existant
    setDetailModal({ isOpen: true, title, data, filterField: filter?.field || null, filterValue: filter?.value || null })
  }

  if (loading) return <Loading message="Chargement du dashboard..." />

  if (error || !dashboard) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center p-8">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-2">Erreur</h2>
          <p className="text-gray-500 mb-4">{error || 'Dashboard introuvable'}</p>
          <Link to="/" className="text-primary-500 hover:underline">Retour</Link>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-3 p-3">
      {/* Header */}
      <div className={`flex ${isMobile ? 'flex-col gap-2' : 'items-center justify-between'}`}>
        <div className="flex items-center gap-3 min-w-0">
          <LayoutGrid className="w-5 h-5 text-primary-500 flex-shrink-0" />
          <div className="min-w-0">
            <h1 className="text-base font-bold text-gray-900 dark:text-white truncate">{dashboard.nom}</h1>
            {dashboard.description && <p className="text-xs text-gray-500 truncate">{dashboard.description}</p>}
          </div>
          {autoRefreshInterval > 0 && (
            <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 text-[10px] font-medium flex-shrink-0">
              <Timer className="w-3 h-3" />{autoRefreshInterval}s
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <GlobalFilterBar showSociete={true} openOnMount triggerOpen={openParamsCount} onFilterChange={() => { setParamsConfirmed(true); setRefreshKey(k => k + 1) }} />
          <button onClick={() => setOpenParamsCount(c => c + 1)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600">
            <RefreshCw className="w-4 h-4" />{!isMobile && 'Actualiser'}
          </button>
          {!isMobile && dashboard && insightsData.length > 0 && (
            <>
              <InsightsPanel reportType="dashboard" reportId={parseInt(id)} reportNom={dashboard.nom} data={insightsData} columnsInfo={[]} />
              <ExecutiveSummaryModal reportType="dashboard" reportId={parseInt(id)} reportNom={dashboard.nom} data={insightsData} columnsInfo={[]} />
            </>
          )}
          {dashboard && <FavoriteButton reportType="dashboard" reportId={parseInt(id)} reportNom={dashboard.nom} />}
          {!isMobile && dashboard && <SubscribeButton reportType="dashboard" reportId={parseInt(id)} reportNom={dashboard.nom} />}
        </div>
      </div>

      {/* Widget Filter Bar */}
      {widgets.some(w => w.config?.filter_field) && (
        <WidgetFilterBar widgets={widgets} globalFilters={widgetFilters} setGlobalFilters={setWidgetFilters} />
      )}

      {/* Widgets */}
      {widgets.length === 0 ? (
        <div className="flex items-center justify-center py-20 text-gray-400">
          <div className="text-center">
            <LayoutGrid className="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p>Ce dashboard ne contient aucun widget</p>
          </div>
        </div>
      ) : isMobile ? (
        // Mobile : empilement vertical simple
        <div className="flex flex-col gap-3">
          {widgets.map(widget => (
            <div key={widget.id} style={{ minHeight: 180 }} className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden flex flex-col shadow-sm">
              <WidgetView key={`${widget.id}-${refreshKey}`} widget={widget} onDrillDown={openDetail} globalFilters={mergedFilters} fetchSharedData={fetchSharedData} paramsConfirmed={paramsConfirmed} />
            </div>
          ))}
        </div>
      ) : (
        // Desktop : grid layout
        <div ref={containerRef}>
          <GridLayout
            className="layout"
            layout={layout}
            cols={12}
            rowHeight={60}
            width={containerWidth || 1200}
            isDraggable={false}
            isResizable={false}
            margin={[12, 12]}
            containerPadding={[0, 0]}
          >
            {widgets.map(widget => (
              <div key={widget.id} className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden flex flex-col shadow-sm">
                <WidgetView key={`${widget.id}-${refreshKey}`} widget={widget} onDrillDown={openDetail} globalFilters={mergedFilters} fetchSharedData={fetchSharedData} paramsConfirmed={paramsConfirmed} />
              </div>
            ))}
          </GridLayout>
        </div>
      )}

      {/* Detail Modal */}
      {detailModal.isOpen && (
        <DetailModal
          title={detailModal.title}
          data={detailModal.data}
          filterField={detailModal.filterField}
          filterValue={detailModal.filterValue}
          onClose={() => setDetailModal({ isOpen: false, title: '', data: [], filterField: null, filterValue: null })}
        />
      )}
    </div>
  )
}


// ════════════════════════════════════════════════════════════════════
// WIDGET FILTER BAR (filtres internes par clic sur widget)
// ════════════════════════════════════════════════════════════════════
function WidgetFilterBar({ widgets, globalFilters, setGlobalFilters }) {
  const filterFields = useMemo(() => {
    const fields = new Map()
    widgets.forEach(w => {
      if (w.config?.filter_field) {
        fields.set(w.config.filter_field, w.config._filter_values || [])
      }
    })
    return fields
  }, [widgets])

  if (filterFields.size === 0) return null

  return (
    <div className="flex items-center gap-3 px-4 py-2.5 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl">
      <Filter className="w-4 h-4 text-blue-500 flex-shrink-0" />
      <span className="text-xs font-semibold text-blue-600 dark:text-blue-400 flex-shrink-0">Filtres:</span>
      {[...filterFields.entries()].map(([field, values]) => (
        <div key={field} className="flex items-center gap-1.5">
          <span className="text-[10px] text-blue-500 uppercase font-medium">{field}</span>
          <select
            value={globalFilters[field] || ''}
            onChange={e => setGlobalFilters(prev => ({ ...prev, [field]: e.target.value }))}
            className="px-2 py-1 text-xs border border-blue-200 dark:border-blue-700 rounded-md bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 focus:ring-1 focus:ring-blue-400"
          >
            <option value="">Tous</option>
            {values.map(v => <option key={v} value={v}>{v}</option>)}
          </select>
        </div>
      ))}
      {Object.keys(globalFilters).some(k => globalFilters[k]) && (
        <button onClick={() => setGlobalFilters({})}
          className="text-[10px] text-blue-500 hover:text-blue-700 underline flex-shrink-0">
          Effacer
        </button>
      )}
    </div>
  )
}


// ════════════════════════════════════════════════════════════════════
// WIDGET VIEW (read-only)
// ════════════════════════════════════════════════════════════════════
function WidgetView({ widget, onDrillDown, globalFilters, fetchSharedData, paramsConfirmed = true }) {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const wt = WIDGET_TYPE_MAP[widget.type] || WIDGET_TYPE_MAP.kpi
  const Icon = wt.icon

  useEffect(() => {
    const load = async () => {
      const dsCode = widget.config?.dataSourceCode
      const dsId = widget.config?.dataSourceId
      const isTemplate = widget.config?.dataSourceOrigin === 'template'

      // Attendre que l'utilisateur confirme les paramètres avant de charger
      if (!paramsConfirmed) return

      if (!dsCode && !dsId) { setData([]); return }
      setLoading(true); setError(null)
      try {
        // Utiliser le fetch deduplique si disponible (meme DS = un seul appel API)
        let res
        if (fetchSharedData) {
          res = await fetchSharedData(dsCode, dsId, isTemplate, globalFilters)
        } else if (dsCode && isTemplate) {
          res = await previewUnifiedDataSource(dsCode, globalFilters || {}, null, 0)
        } else {
          res = await previewDataSource(dsId || dsCode, globalFilters || {}, 0)
        }
        let rawData = res.data?.data || []

        // Convertir les valeurs numériques (les API peuvent retourner des strings)
        // Recharts exige des vrais numbers pour le rendu des axes Y
        if (rawData.length > 0) {
          rawData = rawData.map(row => {
            const converted = { ...row }
            for (const key of Object.keys(converted)) {
              const val = converted[key]
              if (val !== null && val !== undefined && val !== '' && typeof val === 'string') {
                // Exclure les dates
                if (/^\d{4}-\d{2}/.test(val)) continue
                // Tester si c'est un nombre (ex: "1210302.03", "-539", "0")
                const num = Number(val)
                if (!isNaN(num) && val.trim() !== '') {
                  converted[key] = num
                } else {
                  // Tenter format français: "1 234 567,89" → 1234567.89
                  const cleaned = val.replace(/\s/g, '').replace(',', '.')
                  const num2 = Number(cleaned)
                  if (!isNaN(num2) && cleaned !== '') {
                    converted[key] = num2
                  }
                }
              }
            }
            return converted
          })
        }

        // Client-side filtering
        if (widget.config?.filter_field && globalFilters?.[widget.config.filter_field]) {
          rawData = rawData.filter(r => String(r[widget.config.filter_field]) === String(globalFilters[widget.config.filter_field]))
        }

        // Client-side sorting
        if (widget.config?.sort_field) {
          const dir = widget.config.sort_direction === 'desc' ? -1 : 1
          rawData.sort((a, b) => {
            const av = a[widget.config.sort_field], bv = b[widget.config.sort_field]
            if (typeof av === 'number' && typeof bv === 'number') return (av - bv) * dir
            return String(av || '').localeCompare(String(bv || '')) * dir
          })
        }

        // Limit rows
        if (widget.config?.limit_rows && widget.config.limit_rows > 0) {
          rawData = rawData.slice(0, widget.config.limit_rows)
        }

        setData(rawData)
      } catch (e) {
        setError(extractErrorMessage(e, 'Erreur'))
        setData([])
      } finally { setLoading(false) }
    }
    load()
  }, [widget.config?.dataSourceCode, widget.config?.dataSourceId, widget.config?.dataSourceOrigin, globalFilters, widget.config?.filter_field, widget.config?.sort_field, widget.config?.sort_direction, widget.config?.limit_rows, paramsConfirmed])

  return (
    <>
      <div className="flex items-center gap-1.5 px-3 py-2 bg-gray-50 dark:bg-gray-700/50 border-b border-gray-200 dark:border-primary-600 flex-shrink-0">
        <div className={`w-5 h-5 rounded flex items-center justify-center ${wt.color}`}>
          <Icon className="w-3 h-3 text-white" />
        </div>
        <span className="text-sm font-semibold text-gray-700 dark:text-gray-300 truncate">{widget.title}</span>
      </div>
      <div className="flex-1 p-3 overflow-hidden" style={{ minHeight: 0 }}>
        {!paramsConfirmed ? (
          <div className="flex flex-col items-center justify-center h-full gap-2 text-gray-400">
            <SlidersHorizontal className="w-5 h-5 opacity-40" />
            <span className="text-xs">Confirmez les paramètres</span>
          </div>
        ) : loading ? (
          <div className="flex items-center justify-center h-full"><RefreshCw className="w-6 h-6 text-gray-400 animate-spin" /></div>
        ) : error ? (
          <div className="flex items-center justify-center h-full text-red-500 text-xs gap-1"><AlertCircle className="w-4 h-4" />{error}</div>
        ) : !widget.config?.dataSourceId && !widget.config?.dataSourceCode && !['text', 'image'].includes(widget.type) ? (
          <div className="flex items-center justify-center h-full text-gray-400 text-xs">Aucune source configuree</div>
        ) : (
          <WidgetContent widget={widget} data={data} onDrillDown={(filter) => onDrillDown(widget.title, data, filter)} />
        )}
      </div>
    </>
  )
}


// ════════════════════════════════════════════════════════════════════
// WIDGET CONTENT (shared renderer)
// ════════════════════════════════════════════════════════════════════
function WidgetContent({ widget, data, onDrillDown }) {
  const { theme } = useTheme()
  const COLORS = generateThemeColors(theme)
  const cfg = widget.config || {}

  switch (widget.type) {
    case 'kpi':
    case 'kpi_compare': {
      const { yf: vf } = autoDetectFields(data, { x_field: cfg.x_field, y_field: cfg.value_field })
      const agg = cfg.aggregation || 'SUM'
      const total = aggregateData(data, vf, agg)
      const baseColor = cfg.kpi_color || '#3b82f6'
      const kpiColor = getConditionalColor(total, cfg.thresholds) || baseColor
      return (
        <div className="flex flex-col items-center justify-center h-full cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/30 rounded-lg transition-colors"
          onClick={() => onDrillDown?.()}>
          <span className="text-3xl font-black tabular-nums" style={{ color: kpiColor }}>
            {cfg.prefix || ''}{formatNumber(total)}{cfg.suffix || ''}
          </span>
          <span className="text-xs text-gray-500 mt-1">{cfg.subtitle || `${vf} (${agg})`}</span>
          {widget.type === 'kpi_compare' && cfg.compare_field && (
            <CompareIndicator data={data} valueField={vf} compareField={cfg.compare_field} aggregation={agg} />
          )}
        </div>
      )
    }

    case 'gauge': {
      const { yf: vf } = autoDetectFields(data, { x_field: cfg.x_field, y_field: cfg.value_field })
      const agg = cfg.aggregation || 'SUM'
      const total = aggregateData(data, vf, agg)
      const maxVal = cfg.max_value || 100
      const pct = Math.min(100, Math.max(0, (total / maxVal) * 100))
      const gaugeColor = getConditionalColor(total, cfg.thresholds) || cfg.kpi_color || '#3b82f6'
      return (
        <div className="flex flex-col items-center justify-center h-full">
          <ResponsiveContainer width="100%" height="80%">
            <RadialBarChart cx="50%" cy="50%" innerRadius="60%" outerRadius="90%" barSize={12} data={[{ value: pct, fill: gaugeColor }]} startAngle={180} endAngle={0}>
              <RadialBar background dataKey="value" cornerRadius={6} fill={gaugeColor} />
            </RadialBarChart>
          </ResponsiveContainer>
          <span className="text-lg font-bold -mt-4" style={{ color: gaugeColor }}>{formatNumber(total)}</span>
          <span className="text-[10px] text-gray-400">{cfg.subtitle || vf} / {formatNumber(maxVal)}</span>
        </div>
      )
    }

    case 'progress': {
      const { yf: vf } = autoDetectFields(data, { x_field: cfg.x_field, y_field: cfg.value_field })
      const agg = cfg.aggregation || 'SUM'
      const total = aggregateData(data, vf, agg)
      const maxVal = cfg.max_value || 100
      const pct = Math.min(100, Math.max(0, (total / maxVal) * 100))
      const barColor = getConditionalColor(pct, cfg.thresholds) || cfg.kpi_color || '#3b82f6'
      return (
        <div className="flex flex-col justify-center h-full px-3 gap-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-700 dark:text-gray-300">{cfg.subtitle || vf}</span>
            <span className="text-sm font-bold" style={{ color: barColor }}>{pct.toFixed(1)}%</span>
          </div>
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-4 overflow-hidden">
            <div className="h-full rounded-full transition-all duration-700 flex items-center justify-end pr-1"
              style={{ width: `${pct}%`, backgroundColor: barColor }}>
              {pct > 15 && <span className="text-[9px] text-white font-bold">{formatNumber(total)}</span>}
            </div>
          </div>
          <div className="flex items-center justify-between text-[10px] text-gray-400">
            <span>0</span>
            <span>Objectif: {formatNumber(maxVal)}</span>
          </div>
        </div>
      )
    }

    case 'sparkline': {
      const { xf, yf: _yf } = autoDetectFields(data, cfg)
      const yf = cfg.value_field || _yf
      const color = cfg.color || '#3b82f6'
      const agg = cfg.aggregation || 'SUM'
      const total = aggregateData(data, yf, agg)
      return (
        <div className="flex items-center h-full gap-3 px-1">
          <div className="flex flex-col flex-shrink-0">
            <span className="text-lg font-black tabular-nums" style={{ color }}>{formatNumber(total)}</span>
            <span className="text-[10px] text-gray-400">{cfg.subtitle || yf}</span>
          </div>
          <div className="flex-1 h-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
                <Area type="monotone" dataKey={yf} stroke={color} fill={color} fillOpacity={0.15} strokeWidth={2} dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )
    }

    case 'chart_bar': {
      const { xf, yf } = autoDetectFields(data, cfg)
      const horizontal = cfg.horizontal || false
      return (
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 10, right: 10, left: 10, bottom: 10 }}
            layout={horizontal ? 'vertical' : 'horizontal'}
            onClick={e => e?.activePayload?.[0] && onDrillDown?.({ field: xf, value: e.activePayload[0].payload[xf] })} style={{ cursor: 'pointer' }}>
            {cfg.show_grid !== false && <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />}
            {horizontal ? (
              <>
                <YAxis dataKey={xf} type="category" tick={{ fontSize: 11 }} width={80} />
                <XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={formatNumber} />
              </>
            ) : (
              <>
                <XAxis dataKey={xf} tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={formatNumber} />
              </>
            )}
            <Tooltip formatter={v => formatNumber(v)} content={<CustomTooltip />} />
            {cfg.show_legend && <Legend wrapperStyle={{ fontSize: 11 }} />}
            <Bar dataKey={yf} fill={cfg.color || COLORS[0]} radius={horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0]} name={cfg.y_label || yf}>
              {cfg.show_labels && <LabelList dataKey={yf} position="top" fontSize={9} formatter={formatNumber} />}
            </Bar>
            {cfg.y_field_2 && <Bar dataKey={cfg.y_field_2} fill={cfg.color_2 || COLORS[1]} radius={horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0]} name={cfg.y_label_2 || cfg.y_field_2} />}
            {cfg.y_field_3 && <Bar dataKey={cfg.y_field_3} fill={cfg.color_3 || COLORS[2]} radius={horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0]} name={cfg.y_label_3 || cfg.y_field_3} />}
          </BarChart>
        </ResponsiveContainer>
      )
    }

    case 'chart_stacked_bar': {
      const { xf, yf } = autoDetectFields(data, cfg)
      const mode = cfg.stack_mode || 'stacked'
      return (
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 10, right: 10, left: 10, bottom: 10 }}>
            {cfg.show_grid !== false && <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />}
            <XAxis dataKey={xf} tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} tickFormatter={formatNumber} />
            <Tooltip formatter={v => formatNumber(v)} content={<CustomTooltip />} />
            {cfg.show_legend && <Legend wrapperStyle={{ fontSize: 11 }} />}
            <Bar dataKey={yf} stackId={mode === 'stacked' || mode === 'percent' ? 'stack' : undefined} fill={cfg.color || COLORS[0]} radius={[4, 4, 0, 0]} name={cfg.y_label || yf}>
              {cfg.show_labels && <LabelList dataKey={yf} position="center" fontSize={9} fill="#fff" formatter={formatNumber} />}
            </Bar>
            {cfg.y_field_2 && <Bar dataKey={cfg.y_field_2} stackId={mode === 'stacked' || mode === 'percent' ? 'stack' : undefined} fill={cfg.color_2 || COLORS[1]} name={cfg.y_label_2 || cfg.y_field_2} />}
            {cfg.y_field_3 && <Bar dataKey={cfg.y_field_3} stackId={mode === 'stacked' || mode === 'percent' ? 'stack' : undefined} fill={cfg.color_3 || COLORS[2]} name={cfg.y_label_3 || cfg.y_field_3} />}
          </BarChart>
        </ResponsiveContainer>
      )
    }

    case 'chart_combo': {
      const { xf, yf } = autoDetectFields(data, cfg)
      return (
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 10, right: 10, left: 10, bottom: 10 }}>
            {cfg.show_grid !== false && <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />}
            <XAxis dataKey={xf} tick={{ fontSize: 11 }} />
            <YAxis yAxisId="left" tick={{ fontSize: 11 }} tickFormatter={formatNumber} />
            {cfg.y_field_2 && <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} tickFormatter={formatNumber} />}
            <Tooltip formatter={v => formatNumber(v)} content={<CustomTooltip />} />
            {cfg.show_legend && <Legend wrapperStyle={{ fontSize: 11 }} />}
            <Bar yAxisId="left" dataKey={yf} fill={cfg.color || COLORS[0]} radius={[4, 4, 0, 0]} name={cfg.y_label || yf}>
              {cfg.show_labels && <LabelList dataKey={yf} position="top" fontSize={9} formatter={formatNumber} />}
            </Bar>
            {cfg.y_field_2 && <Line yAxisId={cfg.combo_same_axis ? 'left' : 'right'} type="monotone" dataKey={cfg.y_field_2} stroke={cfg.color_2 || COLORS[1]} strokeWidth={2} dot={{ r: 3 }} name={cfg.y_label_2 || cfg.y_field_2} />}
            {cfg.y_field_3 && <Line yAxisId="left" type="monotone" dataKey={cfg.y_field_3} stroke={cfg.color_3 || COLORS[2]} strokeWidth={2} dot={{ r: 3 }} name={cfg.y_label_3 || cfg.y_field_3} />}
          </ComposedChart>
        </ResponsiveContainer>
      )
    }

    case 'chart_line': {
      const { xf, yf } = autoDetectFields(data, cfg)
      return (
        <ResponsiveContainer width="100%" height="100%">
          <ReLineChart data={data} margin={{ top: 10, right: 10, left: 10, bottom: 10 }}
            onClick={e => e?.activePayload?.[0] && onDrillDown?.({ field: xf, value: e.activePayload[0].payload[xf] })} style={{ cursor: 'pointer' }}>
            {cfg.show_grid !== false && <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />}
            <XAxis dataKey={xf} tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} tickFormatter={formatNumber} />
            <Tooltip formatter={v => formatNumber(v)} content={<CustomTooltip />} />
            {cfg.show_legend && <Legend wrapperStyle={{ fontSize: 11 }} />}
            <Line type={cfg.curve_type || 'monotone'} dataKey={yf} stroke={cfg.color || COLORS[0]} strokeWidth={2} dot={{ r: 4 }} name={cfg.y_label || yf}>
              {cfg.show_labels && <LabelList dataKey={yf} position="top" fontSize={9} formatter={formatNumber} />}
            </Line>
            {cfg.y_field_2 && <Line type={cfg.curve_type || 'monotone'} dataKey={cfg.y_field_2} stroke={cfg.color_2 || COLORS[1]} strokeWidth={2} dot={{ r: 4 }} name={cfg.y_label_2 || cfg.y_field_2} />}
            {cfg.y_field_3 && <Line type={cfg.curve_type || 'monotone'} dataKey={cfg.y_field_3} stroke={cfg.color_3 || COLORS[2]} strokeWidth={2} dot={{ r: 4 }} name={cfg.y_label_3 || cfg.y_field_3} />}
          </ReLineChart>
        </ResponsiveContainer>
      )
    }

    case 'chart_pie': {
      const { xf: lf, yf: vf } = autoDetectFields(data, { x_field: cfg.label_field, y_field: cfg.value_field })
      return (
        <ResponsiveContainer width="100%" height="100%">
          <RePieChart>
            <Pie data={data} dataKey={vf} nameKey={lf} cx="50%" cy="50%" outerRadius="80%" innerRadius={cfg.donut ? '45%' : '0%'}
              label={cfg.show_labels !== false ? ({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%` : false}
              labelLine={cfg.show_labels !== false}
              onClick={entry => entry?.[lf] && onDrillDown?.({ field: lf, value: entry[lf] })} style={{ cursor: 'pointer' }}>
              {data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
            </Pie>
            <Tooltip formatter={v => formatNumber(v)} content={<CustomTooltip />} />
            {cfg.show_legend && <Legend wrapperStyle={{ fontSize: 11 }} />}
          </RePieChart>
        </ResponsiveContainer>
      )
    }

    case 'chart_area': {
      const { xf, yf } = autoDetectFields(data, cfg)
      const color = cfg.color || COLORS[0]
      return (
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 10, left: 10, bottom: 10 }}
            onClick={e => e?.activePayload?.[0] && onDrillDown?.({ field: xf, value: e.activePayload[0].payload[xf] })} style={{ cursor: 'pointer' }}>
            {cfg.show_grid !== false && <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />}
            <XAxis dataKey={xf} tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} tickFormatter={formatNumber} />
            <Tooltip formatter={v => formatNumber(v)} content={<CustomTooltip />} />
            <Area type="monotone" dataKey={yf} stroke={color} fill={color} fillOpacity={0.2} strokeWidth={2} stackId={cfg.stacked ? 'stack' : undefined} />
            {cfg.y_field_2 && <Area type="monotone" dataKey={cfg.y_field_2} stroke={cfg.color_2 || COLORS[1]} fill={cfg.color_2 || COLORS[1]} fillOpacity={0.15} strokeWidth={2} stackId={cfg.stacked ? 'stack' : undefined} />}
            {cfg.y_field_3 && <Area type="monotone" dataKey={cfg.y_field_3} stroke={cfg.color_3 || COLORS[2]} fill={cfg.color_3 || COLORS[2]} fillOpacity={0.1} strokeWidth={2} stackId={cfg.stacked ? 'stack' : undefined} />}
          </AreaChart>
        </ResponsiveContainer>
      )
    }

    case 'chart_funnel': {
      const { xf: lf, yf: vf } = autoDetectFields(data, { x_field: cfg.label_field, y_field: cfg.value_field })
      const funnelData = data.map((row, i) => ({
        name: row[lf],
        value: Number(row[vf]) || 0,
        fill: COLORS[i % COLORS.length]
      })).sort((a, b) => b.value - a.value)
      return (
        <ResponsiveContainer width="100%" height="100%">
          <FunnelChart>
            <Tooltip formatter={v => formatNumber(v)} />
            <Funnel dataKey="value" data={funnelData} isAnimationActive>
              <LabelList position="right" fill="#374151" fontSize={10} formatter={v => formatNumber(v)} />
              <LabelList position="left" fill="#6b7280" fontSize={10} dataKey="name" />
            </Funnel>
          </FunnelChart>
        </ResponsiveContainer>
      )
    }

    case 'chart_treemap': {
      const { xf: lf, yf: vf } = autoDetectFields(data, { x_field: cfg.label_field, y_field: cfg.value_field })
      const treemapData = data.map((row, i) => ({
        name: String(row[lf] || ''),
        size: Math.abs(Number(row[vf]) || 0),
        fill: COLORS[i % COLORS.length]
      })).filter(d => d.size > 0)

      const TreemapLabel = ({ x, y, width, height, name, size }) => {
        if (width < 40 || height < 25) return null
        return (
          <g>
            <text x={x + width / 2} y={y + height / 2 - 6} textAnchor="middle" fill="#fff" fontSize={10} fontWeight="bold">
              {name?.length > 12 ? name.slice(0, 12) + '..' : name}
            </text>
            <text x={x + width / 2} y={y + height / 2 + 8} textAnchor="middle" fill="rgba(255,255,255,0.8)" fontSize={9}>
              {formatNumber(size)}
            </text>
          </g>
        )
      }
      return (
        <ResponsiveContainer width="100%" height="100%">
          <ReTreemap data={treemapData} dataKey="size" nameKey="name" aspectRatio={4 / 3}
            content={<TreemapLabel />}>
            <Tooltip formatter={v => formatNumber(v)} />
          </ReTreemap>
        </ResponsiveContainer>
      )
    }

    case 'table': {
      if (!data?.length) return <div className="text-center text-gray-400 text-xs py-4">Aucune donnee</div>
      const cols = cfg.visible_columns?.length ? cfg.visible_columns : Object.keys(data[0])
      return (
        <div className="overflow-auto h-full">
          <table className="w-full text-xs">
            <thead className="bg-gray-50 dark:bg-gray-700 sticky top-0">
              <tr>{cols.map(c => <th key={c} className="px-3 py-2 text-left font-semibold text-gray-600 dark:text-gray-300 border-b whitespace-nowrap">{c}</th>)}</tr>
            </thead>
            <tbody>
              {data.slice(0, cfg.max_rows || 100).map((row, i) => (
                <tr key={i} className={i % 2 === 0 ? 'bg-white dark:bg-gray-800' : 'bg-gray-50 dark:bg-gray-750'}>
                  {cols.map(c => {
                    const val = row[c]
                    const isNum = typeof val === 'number'
                    let cellBg = ''
                    if (isNum && cfg.table_thresholds?.[c]) {
                      const cc = getConditionalColor(val, cfg.table_thresholds[c])
                      if (cc) cellBg = cc
                    }
                    return (
                      <td key={c} className="px-3 py-2 text-gray-700 dark:text-gray-300 border-b border-gray-100 dark:border-gray-700 whitespace-nowrap"
                        style={cellBg ? { backgroundColor: cellBg + '30', color: cellBg } : {}}>
                        {isNum ? formatNumber(val) : String(val ?? '')}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
          {data.length > (cfg.max_rows || 100) && <p className="text-center text-gray-400 text-[10px] py-1">{data.length} lignes total</p>}
        </div>
      )
    }

    case 'text': {
      const bgColor = cfg.bg_color || 'transparent'
      const textColor = cfg.text_color || 'inherit'
      const fontSize = cfg.font_size || 14
      return (
        <div className="p-2 overflow-auto h-full whitespace-pre-wrap" style={{ backgroundColor: bgColor, color: textColor, fontSize }}>
          {cfg.content || 'Aucun contenu'}
        </div>
      )
    }

    case 'image': {
      const url = cfg.image_url || ''
      const fit = cfg.image_fit || 'contain'
      if (!url) return <div className="flex items-center justify-center h-full text-gray-400 text-xs"><Image className="w-8 h-8 opacity-30" /></div>
      return (
        <div className="flex items-center justify-center h-full p-1 overflow-hidden">
          <img src={url} alt={widget.title} className="max-w-full max-h-full" style={{ objectFit: fit }} onError={e => { e.target.style.display = 'none' }} />
        </div>
      )
    }

    default:
      return <div className="text-xs text-gray-400 text-center">Widget non supporte</div>
  }
}

function CompareIndicator({ data, valueField, compareField, aggregation = 'SUM' }) {
  const current = aggregateData(data, valueField, aggregation)
  const prev = aggregateData(data, compareField, aggregation)
  if (!prev) return null
  const pct = ((current - prev) / Math.abs(prev)) * 100
  const isUp = pct > 0
  return (
    <span className={`flex items-center gap-0.5 text-xs font-semibold mt-1 ${isUp ? 'text-green-500' : 'text-red-500'}`}>
      {isUp ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
      {isUp ? '+' : ''}{pct.toFixed(1)}%
    </span>
  )
}

// ── Custom Tooltip ──
function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-3">
      <p className="text-sm font-semibold text-gray-900 dark:text-white mb-1">{label}</p>
      {payload.map((entry, i) => (
        <p key={i} className="text-sm" style={{ color: entry.color }}>
          {entry.name}: <span className="font-bold">{formatNumber(entry.value)}</span>
        </p>
      ))}
      <p className="text-[10px] text-primary-500 mt-1.5">Cliquez pour le detail</p>
    </div>
  )
}


// ════════════════════════════════════════════════════════════════════
// DETAIL MODAL (Drill-Down)
// ════════════════════════════════════════════════════════════════════
function DetailModal({ title, data, filterField, filterValue, onClose }) {
  const [searchTerm, setSearchTerm] = useState('')
  const [sortField, setSortField] = useState(null)
  const [sortDirection, setSortDirection] = useState('asc')
  const [currentPage, setCurrentPage] = useState(1)
  const pageSize = 50

  const filteredData = data.filter(row => {
    if (!searchTerm) return true
    const s = searchTerm.toLowerCase()
    return Object.values(row).some(v => String(v).toLowerCase().includes(s))
  })

  const sortedData = [...filteredData].sort((a, b) => {
    if (!sortField) return 0
    const av = a[sortField], bv = b[sortField]
    if (typeof av === 'number' && typeof bv === 'number') return sortDirection === 'asc' ? av - bv : bv - av
    return sortDirection === 'asc' ? String(av || '').localeCompare(String(bv || '')) : String(bv || '').localeCompare(String(av || ''))
  })

  const totalPages = Math.ceil(sortedData.length / pageSize)
  const paginatedData = sortedData.slice((currentPage - 1) * pageSize, currentPage * pageSize)
  const columns = data.length > 0 ? Object.keys(data[0]) : []

  const handleSort = (field) => {
    if (sortField === field) setSortDirection(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortField(field); setSortDirection('asc') }
  }

  const exportCSV = () => {
    if (!sortedData.length) return
    const headers = columns.join(';')
    const rows = sortedData.map(row => columns.map(c => {
      const v = row[c]
      return typeof v === 'number' ? v.toString().replace('.', ',') : `"${String(v || '').replace(/"/g, '""')}"`
    }).join(';'))
    const csv = [headers, ...rows].join('\n')
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `${title.replace(/[^a-zA-Z0-9]/g, '_')}_detail.csv`; a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="relative bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-[95vw] h-[90vh] max-w-6xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
          <div>
            <h2 className="text-lg font-bold text-gray-900 dark:text-white">{title} - Detail</h2>
            {filterField && filterValue && <p className="text-sm text-primary-600 mt-0.5">Filtre: {filterField} = "{filterValue}"</p>}
            <p className="text-sm text-gray-500">{sortedData.length} enregistrement{sortedData.length > 1 ? 's' : ''}</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input type="text" value={searchTerm} onChange={e => { setSearchTerm(e.target.value); setCurrentPage(1) }}
                placeholder="Rechercher..." className="pl-9 pr-4 py-2 text-sm border border-primary-300 dark:border-primary-600 rounded-lg dark:bg-gray-700 w-64" />
            </div>
            <button onClick={exportCSV} className="flex items-center gap-2 px-3 py-2 text-sm bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600">
              <Download className="w-4 h-4" />CSV
            </button>
            <button onClick={onClose} className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"><X className="w-5 h-5" /></button>
          </div>
        </div>

        {/* Table */}
        <div className="flex-1 overflow-auto" style={{ minHeight: 0 }}>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-700 sticky top-0">
              <tr>
                {columns.map(c => (
                  <th key={c} onClick={() => handleSort(c)}
                    className="px-4 py-3 text-left font-semibold text-gray-600 dark:text-gray-300 border-b cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600 whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      {c}
                      {sortField === c && <ArrowUpDown className={`w-3 h-3 ${sortDirection === 'desc' ? 'rotate-180' : ''}`} />}
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {paginatedData.map((row, i) => (
                <tr key={i} className={`${i % 2 === 0 ? 'bg-white dark:bg-gray-800' : 'bg-gray-50 dark:bg-gray-750'} hover:bg-primary-50 dark:hover:bg-primary-900/20`}>
                  {columns.map(c => (
                    <td key={c} className={`px-4 py-3 border-b border-gray-100 dark:border-gray-700 whitespace-nowrap ${
                      filterField === c && String(row[c]) === String(filterValue) ? 'bg-primary-100 dark:bg-primary-900/30 font-medium text-primary-700 dark:text-primary-300' : 'text-gray-700 dark:text-gray-300'
                    }`}>
                      {typeof row[c] === 'number' ? formatNumber(row[c]) : String(row[c] ?? '')}
                    </td>
                  ))}
                </tr>
              ))}
              {!paginatedData.length && <tr><td colSpan={columns.length} className="text-center py-12 text-gray-500">Aucune donnee trouvee</td></tr>}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-6 py-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700 flex-shrink-0">
            <span className="text-sm text-gray-600 dark:text-gray-400">Page {currentPage} / {totalPages}</span>
            <div className="flex items-center gap-2">
              <button onClick={() => setCurrentPage(p => Math.max(1, p - 1))} disabled={currentPage === 1}
                className="p-2 rounded hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50"><ChevronLeft className="w-4 h-4" /></button>
              <button onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))} disabled={currentPage === totalPages}
                className="p-2 rounded hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50"><ChevronRight className="w-4 h-4" /></button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
