import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import {
  Plus, Save, Eye, Trash2, GripVertical,
  BarChart2, LineChart, PieChart, Activity, Table, Type, Gauge,
  X, RefreshCw, LayoutGrid, AlertCircle, Settings2,
  BookOpen, Users, Landmark,
  Copy, ChevronDown, Palette, Hash, TrendingUp, TrendingDown,
  ArrowUp, ArrowDown, Maximize2, Minimize2, Filter, Layers,
  Target, Zap, Image, GitBranch, BarChart3, Timer, Check, Search, Sparkles
} from 'lucide-react'
import {
  BarChart, Bar, LineChart as ReLineChart, Line, PieChart as RePieChart, Pie, Cell,
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  RadialBarChart, RadialBar, ComposedChart, Treemap as ReTreemap,
  FunnelChart, Funnel, LabelList, ScatterChart, Scatter, ZAxis
} from 'recharts'
import GridLayout from 'react-grid-layout'
import 'react-grid-layout/css/styles.css'
import 'react-resizable/css/styles.css'
import Loading from '../components/common/Loading'
import DataSourceSelector from '../components/DataSourceSelector'
import AIDashboardGenerator from '../components/ai/AIDashboardGenerator'
import {
  getBuilderDashboards,
  getBuilderDashboard,
  createBuilderDashboard,
  updateBuilderDashboard,
  deleteBuilderDashboard,
  getWidgetTemplates,
  getDataSources,
  getDataSource,
  previewDataSource,
  extractErrorMessage
} from '../services/api'
import { useTheme } from '../context/ThemeContext'

// ─── Widget type definitions ───
const WIDGET_TYPES = [
  { type: 'kpi', name: 'KPI', icon: Activity, color: 'bg-blue-500', defaultW: 3, defaultH: 3, description: 'Indicateur chiffre cle', category: 'Indicateurs' },
  { type: 'kpi_compare', name: 'KPI Compare', icon: TrendingUp, color: 'bg-emerald-500', defaultW: 3, defaultH: 3, description: 'KPI avec comparaison', category: 'Indicateurs' },
  { type: 'gauge', name: 'Jauge', icon: Gauge, color: 'bg-cyan-500', defaultW: 3, defaultH: 4, description: 'Jauge circulaire', category: 'Indicateurs' },
  { type: 'progress', name: 'Progression', icon: Target, color: 'bg-lime-500', defaultW: 3, defaultH: 2, description: 'Barre de progression', category: 'Indicateurs' },
  { type: 'sparkline', name: 'Sparkline', icon: Zap, color: 'bg-rose-500', defaultW: 3, defaultH: 2, description: 'Mini-graphique inline', category: 'Indicateurs' },
  { type: 'chart_bar', name: 'Barres', icon: BarChart2, color: 'bg-indigo-500', defaultW: 6, defaultH: 5, description: 'Graphique en barres', category: 'Graphiques' },
  { type: 'chart_stacked_bar', name: 'Barres empilees', icon: BarChart3, color: 'bg-violet-500', defaultW: 6, defaultH: 5, description: 'Barres empilees / groupees', category: 'Graphiques' },
  { type: 'chart_line', name: 'Lignes', icon: LineChart, color: 'bg-teal-500', defaultW: 6, defaultH: 5, description: 'Graphique en lignes', category: 'Graphiques' },
  { type: 'chart_combo', name: 'Combo', icon: GitBranch, color: 'bg-fuchsia-500', defaultW: 6, defaultH: 5, description: 'Barres + Lignes combine', category: 'Graphiques' },
  { type: 'chart_pie', name: 'Camembert', icon: PieChart, color: 'bg-amber-500', defaultW: 4, defaultH: 5, description: 'Graphique circulaire', category: 'Graphiques' },
  { type: 'chart_area', name: 'Aire', icon: LineChart, color: 'bg-purple-500', defaultW: 6, defaultH: 5, description: 'Graphique en aire', category: 'Graphiques' },
  { type: 'chart_funnel', name: 'Entonnoir', icon: Filter, color: 'bg-orange-500', defaultW: 4, defaultH: 5, description: 'Entonnoir de conversion', category: 'Graphiques' },
  { type: 'chart_treemap', name: 'Treemap', icon: Layers, color: 'bg-pink-500', defaultW: 6, defaultH: 5, description: 'Arborescence proportionnelle', category: 'Graphiques' },
  { type: 'table', name: 'Tableau', icon: Table, color: 'bg-gray-500', defaultW: 12, defaultH: 6, description: 'Tableau de donnees', category: 'Donnees' },
  { type: 'text', name: 'Texte', icon: Type, color: 'bg-slate-500', defaultW: 4, defaultH: 3, description: 'Zone de texte libre', category: 'Divers' },
  { type: 'image', name: 'Image', icon: Image, color: 'bg-sky-500', defaultW: 3, defaultH: 3, description: 'Image / Logo URL', category: 'Divers' },
]

const WIDGET_TYPE_MAP = Object.fromEntries(WIDGET_TYPES.map(t => [t.type, t]))
const WIDGET_CATEGORIES = [...new Set(WIDGET_TYPES.map(t => t.category))]

// ─── Aggregation functions ───
const AGGREGATION_FUNCTIONS = [
  { value: 'SUM', label: 'Somme (SUM)' },
  { value: 'AVG', label: 'Moyenne (AVG)' },
  { value: 'COUNT', label: 'Nombre (COUNT)' },
  { value: 'MIN', label: 'Minimum (MIN)' },
  { value: 'MAX', label: 'Maximum (MAX)' },
  { value: 'FIRST', label: 'Premier' },
  { value: 'LAST', label: 'Dernier' },
]

// ─── Theme colors ───
function generateThemeColors(theme) {
  if (!theme?.colors?.primary) {
    return ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#14b8a6']
  }
  const p = theme.colors.primary
  return [p[600], theme.colors.accent, p[400], p[800], '#f59e0b', '#8b5cf6', p[300], '#ec4899', '#f97316', '#14b8a6']
}

const formatNumber = (val) => {
  if (val === null || val === undefined) return '0'
  return Number(val).toLocaleString('fr-FR', { minimumFractionDigits: 0, maximumFractionDigits: 2 })
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
  // Sort thresholds by value descending
  const sorted = [...thresholds].sort((a, b) => b.value - a.value)
  for (const t of sorted) {
    if (value >= t.value) return t.color
  }
  return sorted[sorted.length - 1]?.color || null
}

const APP_DOT = {
  commercial:   'bg-blue-500',
  comptabilite: 'bg-emerald-500',
  paie:         'bg-orange-400',
  tresorerie:   'bg-violet-500',
}
const APP_TEXT = {
  commercial:   'text-blue-600 dark:text-blue-400',
  comptabilite: 'text-emerald-600 dark:text-emerald-400',
  paie:         'text-orange-500 dark:text-orange-400',
  tresorerie:   'text-violet-600 dark:text-violet-400',
}
const APP_BG = {
  commercial:   'bg-blue-100 dark:bg-blue-900/30',
  comptabilite: 'bg-emerald-100 dark:bg-emerald-900/30',
  paie:         'bg-orange-100 dark:bg-orange-900/30',
  tresorerie:   'bg-violet-100 dark:bg-violet-900/30',
}

// ════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ════════════════════════════════════════════════════════════════════
export default function DashboardBuilder() {
  const [loading, setLoading] = useState(true)
  const [dashboards, setDashboards] = useState([])
  const [currentDashboard, setCurrentDashboard] = useState(null)
  const [widgets, setWidgets] = useState([])
  const [selectedWidgetId, setSelectedWidgetId] = useState(null)
  const [saving, setSaving] = useState(false)
  const [previewMode, setPreviewMode] = useState(false)
  const [showNewModal, setShowNewModal] = useState(false)
  const [newDashboardName, setNewDashboardName] = useState('')
  const [newDashApp, setNewDashApp] = useState('')
  const [showAIGenerator, setShowAIGenerator] = useState(false)
  const [toast, setToast] = useState(null)
  const [gridWidth, setGridWidth] = useState(1200)
  const [showWidgetPicker, setShowWidgetPicker] = useState(false)
  const [globalFilters, setGlobalFilters] = useState({})
  const [autoRefreshInterval, setAutoRefreshInterval] = useState(0)
  const [refreshKey, setRefreshKey] = useState(0)
  const [searchQuery, setSearchQuery] = useState('')
  const [sidebarAppFilter, setSidebarAppFilter] = useState('')

  const [sidebarWidth, setSidebarWidth] = useState(192)
  const sidebarDragging = useRef(false)
  const [dashboardApplication, setDashboardApplication] = useState('')

  const APPLICATION_OPTIONS = [
    { value: '', label: '-- Aucune --' },
    { value: 'commercial', label: 'Gestion Commerciale' },
    { value: 'comptabilite', label: 'Comptabilité' },
    { value: 'paie', label: 'Paie' },
    { value: 'tresorerie', label: 'Gestion Trésorerie' },
  ]
  const gridContainerRef = useRef(null)
  const autoRefreshRef = useRef(null)

  const selectedWidget = useMemo(() => widgets.find(w => w.id === selectedWidgetId), [widgets, selectedWidgetId])

  // Layout for react-grid-layout
  const layout = useMemo(() =>
    widgets.map(w => ({ i: w.id, x: w.x || 0, y: w.y || 0, w: w.w || 4, h: w.h || 4, minW: 2, minH: 2 })),
    [widgets]
  )

  // Sidebar resize handlers
  const handleSidebarResizeStart = useCallback((e) => {
    e.preventDefault()
    sidebarDragging.current = true
    const startX = e.clientX
    const startWidth = sidebarWidth
    const onMouseMove = (e) => {
      if (!sidebarDragging.current) return
      const newWidth = Math.min(Math.max(startWidth + (e.clientX - startX), 140), 480)
      setSidebarWidth(newWidth)
    }
    const onMouseUp = () => {
      sidebarDragging.current = false
      document.removeEventListener('mousemove', onMouseMove)
      document.removeEventListener('mouseup', onMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
    document.addEventListener('mousemove', onMouseMove)
    document.addEventListener('mouseup', onMouseUp)
  }, [sidebarWidth])

  // Track container width for GridLayout
  useEffect(() => {
    if (!gridContainerRef.current) return
    const ro = new ResizeObserver(entries => { for (const e of entries) setGridWidth(e.contentRect.width) })
    ro.observe(gridContainerRef.current)
    setGridWidth(gridContainerRef.current.clientWidth)
    return () => ro.disconnect()
  }, [currentDashboard])

  useEffect(() => { loadData() }, [])

  // Auto-refresh
  useEffect(() => {
    if (autoRefreshRef.current) clearInterval(autoRefreshRef.current)
    if (autoRefreshInterval > 0) {
      autoRefreshRef.current = setInterval(() => setRefreshKey(k => k + 1), autoRefreshInterval * 1000)
    }
    return () => { if (autoRefreshRef.current) clearInterval(autoRefreshRef.current) }
  }, [autoRefreshInterval])

  // Load dashboard config including global filters and auto-refresh
  useEffect(() => {
    if (currentDashboard) {
      setGlobalFilters(currentDashboard.global_filters || {})
      setAutoRefreshInterval(currentDashboard.auto_refresh || 0)
    }
  }, [currentDashboard])

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3000)
  }

  const loadData = async () => {
    setLoading(true)
    try {
      const [res] = await Promise.all([getBuilderDashboards()])
      setDashboards(res.data.data || [])
    } catch (e) {
      console.error('Erreur chargement:', e)
    } finally {
      setLoading(false)
    }
  }

  const loadDashboard = async (id) => {
    try {
      const res = await getBuilderDashboard(id)
      const db = res.data.data
      setCurrentDashboard(db)
      setWidgets(db.widgets || [])
      setDashboardApplication(db.application || '')
      setSelectedWidgetId(null)
      setPreviewMode(false)
    } catch (e) {
      console.error('Erreur chargement dashboard:', e)
    }
  }

  const createNewDashboard = async () => {
    if (!newDashboardName.trim()) return
    try {
      const res = await createBuilderDashboard({ nom: newDashboardName, description: '', widgets: [], is_public: false, ...(newDashApp && { application: newDashApp }) })
      setShowNewModal(false)
      setNewDashboardName('')
      setNewDashApp('')
      await loadData()
      await loadDashboard(res.data.id)
      showToast('Dashboard cree')
    } catch (e) {
      console.error('Erreur creation:', e)
    }
  }

  const handleAIImport = async (generatedDashboard) => {
    try {
      // Créer le dashboard dans la base avec les widgets générés
      const widgets = (generatedDashboard.widgets || []).map((w, i) => ({
        ...w,
        id: w.id || `w_${Date.now()}_${i}`,
        x: Math.round(w.x || 0),
        y: Math.round(w.y || 0),
        w: Math.round(w.w || 4),
        h: Math.round(w.h || 4),
      }))
      const res = await createBuilderDashboard({
        nom: generatedDashboard.nom || 'Dashboard IA',
        description: generatedDashboard.description || '',
        widgets,
        is_public: false
      })
      setShowAIGenerator(false)
      await loadData()
      await loadDashboard(res.data.id)
      showToast(`Dashboard "${generatedDashboard.nom}" créé avec ${widgets.length} widgets !`)
    } catch (e) {
      console.error('Erreur import AI dashboard:', e)
      showToast('Erreur lors de l\'import', 'error')
    }
  }

  const saveDashboard = async () => {
    if (!currentDashboard) return
    setSaving(true)
    try {
      // Sanitize widget positions to integers for clean storage
      const cleanWidgets = widgets.map(w => ({
        ...w,
        x: Math.round(w.x || 0),
        y: Math.round(w.y || 0),
        w: Math.round(w.w || 4),
        h: Math.round(w.h || 4),
      }))
      await updateBuilderDashboard(currentDashboard.id, {
        widgets: cleanWidgets,
        application: dashboardApplication || null,
      })
      showToast('Dashboard sauvegarde !')
    } catch (e) {
      console.error('Erreur sauvegarde:', e)
      showToast('Erreur sauvegarde', 'error')
    } finally {
      setSaving(false)
    }
  }

  const deleteDashboard = async (id) => {
    if (!confirm('Supprimer ce dashboard ?')) return
    try {
      await deleteBuilderDashboard(id)
      if (currentDashboard?.id === id) { setCurrentDashboard(null); setWidgets([]) }
      loadData()
      showToast('Dashboard supprime')
    } catch (e) { console.error(e) }
  }

  const handleQuickSetAppDB = async (e, dashId, appValue) => {
    e.stopPropagation()
    try {
      await updateBuilderDashboard(dashId, { application: appValue })
      setDashboards(prev => prev.map(d => d.id === dashId ? { ...d, application: appValue } : d))
      if (currentDashboard?.id === dashId) {
        setCurrentDashboard(prev => ({ ...prev, application: appValue }))
        setDashboardApplication(appValue)
      }
    } catch (err) {
      console.error('Erreur affectation application:', err)
    }
  }

  // ── Widget CRUD ──
  const addWidget = (type) => {
    if (!currentDashboard) return
    const def = WIDGET_TYPE_MAP[type] || WIDGET_TYPES[0]
    const maxY = widgets.reduce((max, w) => Math.max(max, (w.y || 0) + (w.h || 4)), 0)
    const newW = {
      id: `w_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
      type,
      title: def.name,
      x: 0, y: maxY,
      w: def.defaultW, h: def.defaultH,
      config: {}
    }
    setWidgets(prev => [...prev, newW])
    setSelectedWidgetId(newW.id)
    setShowWidgetPicker(false)
  }

  const duplicateWidget = (wid) => {
    const src = widgets.find(w => w.id === wid)
    if (!src) return
    const maxY = widgets.reduce((max, w) => Math.max(max, (w.y || 0) + (w.h || 4)), 0)
    const dup = { ...src, id: `w_${Date.now()}_dup`, title: src.title + ' (copie)', y: maxY, config: { ...src.config } }
    setWidgets(prev => [...prev, dup])
    setSelectedWidgetId(dup.id)
  }

  const deleteWidget = (wid) => {
    setWidgets(prev => prev.filter(w => w.id !== wid))
    if (selectedWidgetId === wid) setSelectedWidgetId(null)
  }

  const updateWidget = (wid, updates) => {
    setWidgets(prev => prev.map(w => {
      if (w.id !== wid) return w
      if (updates.config) return { ...w, ...updates, config: { ...w.config, ...updates.config } }
      return { ...w, ...updates }
    }))
  }

  // ── react-grid-layout handlers ──
  const onLayoutChange = useCallback((newLayout) => {
    setWidgets(prev => {
      const layoutMap = Object.fromEntries(newLayout.map(l => [l.i, l]))
      return prev.map(w => {
        const l = layoutMap[w.id]
        if (!l) return w
        return { ...w, x: l.x, y: l.y, w: l.w, h: l.h }
      })
    })
  }, [])

  if (loading) return <Loading message="Chargement du Dashboard Builder..." />

  return (
    <div className="h-full flex flex-col -m-3 lg:-m-4 overflow-hidden">
      {/* ── HEADER ── */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 flex-shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-8 h-8 rounded-xl bg-primary-50 dark:bg-primary-900/30 flex items-center justify-center flex-shrink-0">
            <LayoutGrid size={15} className="text-primary-600 dark:text-primary-400" />
          </div>
          <div className="min-w-0">
            <h1 className="text-sm font-bold text-gray-900 dark:text-white truncate leading-tight">
              {currentDashboard ? currentDashboard.nom : 'Dashboard Builder'}
            </h1>
            {currentDashboard && (
              <div className="flex items-center gap-2 mt-0.5">
                <select
                  value={dashboardApplication}
                  onChange={(e) => setDashboardApplication(e.target.value)}
                  className={`text-[10px] bg-transparent border-0 p-0 cursor-pointer outline-none font-medium leading-none ${APP_TEXT[dashboardApplication] || 'text-gray-400 dark:text-gray-500'}`}
                >
                  <option value="">Affecter une application...</option>
                  {APPLICATION_OPTIONS.filter(a => a.value).map(a => (
                    <option key={a.value} value={a.value}>{a.label}</option>
                  ))}
                </select>
              </div>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {currentDashboard && (
            <>
              {autoRefreshInterval > 0 && (
                <span className="flex items-center gap-1 px-2 py-1 rounded-xl bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 text-[10px] font-medium">
                  <Timer className="w-3 h-3" />
                  {autoRefreshInterval}s
                </span>
              )}
              <button onClick={() => setRefreshKey(k => k + 1)}
                className="p-1.5 rounded-xl bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors" title="Actualiser">
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
              <button onClick={() => setPreviewMode(!previewMode)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium transition-colors ${previewMode ? 'bg-primary-100 text-primary-700 dark:bg-primary-900/40 dark:text-primary-300' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200'}`}>
                <Eye className="w-3.5 h-3.5" />{previewMode ? 'Éditer' : 'Aperçu'}
              </button>
              <button onClick={saveDashboard} disabled={saving}
                className="flex items-center gap-1.5 px-4 py-1.5 rounded-xl text-xs font-semibold bg-primary-600 text-white hover:bg-primary-700 disabled:opacity-50 transition-colors shadow-sm">
                {saving ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                Sauvegarder
              </button>
            </>
          )}
          <button onClick={() => setShowAIGenerator(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium bg-gradient-to-r from-violet-600 to-purple-600 text-white hover:from-violet-700 hover:to-purple-700 transition-all shadow-sm">
            <Sparkles className="w-3.5 h-3.5" />IA
          </button>
          <button onClick={() => setShowNewModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium bg-primary-600 text-white hover:bg-primary-700 transition-colors">
            <Plus className="w-3.5 h-3.5" />Nouveau
          </button>
        </div>
      </div>

      {/* ── BODY ── */}
      <div className="flex-1 flex overflow-hidden" style={{ minHeight: 0 }}>
        {/* ── LEFT SIDEBAR ── */}
        <div className="bg-white dark:bg-gray-900 border-r border-gray-100 dark:border-gray-800 flex flex-col flex-shrink-0 relative" style={{ width: sidebarWidth }}>
          <div className="px-4 pt-4 pb-3 border-b border-gray-100 dark:border-gray-800">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-[11px] font-bold text-gray-400 dark:text-gray-500 uppercase tracking-widest">Dashboards</h2>
            </div>
            <div className="relative mb-2">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
              <input type="text" value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
                placeholder="Rechercher..."
                className="w-full pl-8 pr-7 py-2 text-xs bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl focus:ring-2 focus:ring-primary-400 focus:border-transparent dark:text-white placeholder-gray-400 outline-none transition-all" />
              {searchQuery && (
                <button onClick={() => setSearchQuery('')} className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
            <select value={sidebarAppFilter} onChange={e => setSidebarAppFilter(e.target.value)}
              className="w-full px-2.5 py-2 text-xs bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl dark:text-white focus:ring-2 focus:ring-primary-400 focus:border-transparent outline-none transition-all">
              <option value="">Toutes les applications</option>
              {APPLICATION_OPTIONS.filter(a => a.value).map(a => (
                <option key={a.value} value={a.value}>{a.label}</option>
              ))}
            </select>
          </div>
          <div className="flex-1 overflow-y-auto py-2 px-2">
            {dashboards.length === 0 ? (
              <p className="text-xs text-gray-400 text-center py-6">Aucun dashboard</p>
            ) : (() => {
              const filtered = dashboards.filter(d =>
                d.nom.toLowerCase().includes(searchQuery.toLowerCase()) &&
                (!sidebarAppFilter || d.application === sidebarAppFilter)
              )
              return filtered.length === 0 ? (
                <p className="text-xs text-gray-400 text-center py-4">Aucun résultat</p>
              ) : filtered.map(d => (
                <div key={d.id} onClick={() => loadDashboard(d.id)}
                  className={`group flex items-center gap-2 px-2 py-1.5 rounded-xl cursor-pointer transition-all duration-150 mb-0.5
                    ${currentDashboard?.id === d.id
                      ? 'bg-primary-50 dark:bg-primary-900/20 shadow-sm ring-1 ring-primary-200 dark:ring-primary-800'
                      : 'hover:bg-gray-50 dark:hover:bg-gray-800/60'}`}>
                  <div className={`w-1 h-7 rounded-full flex-shrink-0 ${APP_DOT[d.application] || 'bg-gray-200 dark:bg-gray-700'}`} />
                  <div className={`flex-shrink-0 w-6 h-6 rounded-lg flex items-center justify-center ${APP_BG[d.application] || 'bg-gray-100 dark:bg-gray-800'}`} title={d.application || ''}>
                    {d.application === 'commercial'   && <TrendingUp className="w-3 h-3 text-blue-600 dark:text-blue-400" strokeWidth={2.5} />}
                    {d.application === 'comptabilite' && <BookOpen   className="w-3 h-3 text-emerald-600 dark:text-emerald-400" strokeWidth={2.5} />}
                    {d.application === 'paie'         && <Users      className="w-3 h-3 text-orange-500 dark:text-orange-400" strokeWidth={2.5} />}
                    {d.application === 'tresorerie'   && <Landmark   className="w-3 h-3 text-violet-600 dark:text-violet-400" strokeWidth={2.5} />}
                    {!d.application                   && <LayoutGrid className="w-3 h-3 text-gray-300 dark:text-gray-600" strokeWidth={2} />}
                  </div>
                  <span className={`flex-1 truncate text-[11px] font-semibold ${currentDashboard?.id === d.id ? 'text-primary-700 dark:text-primary-400' : 'text-gray-800 dark:text-gray-200'}`}>
                    {d.nom}
                  </span>
                  {!d.is_public && (
                    <button onClick={(e) => { e.stopPropagation(); deleteDashboard(d.id) }}
                      className="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-all flex-shrink-0">
                      <Trash2 className="w-3 h-3 text-red-400" />
                    </button>
                  )}
                </div>
              ))
            })()}
          </div>
          {/* Resize handle */}
          <div
            onMouseDown={handleSidebarResizeStart}
            className="absolute top-0 right-0 w-1.5 h-full cursor-col-resize hover:bg-primary-400/40 active:bg-primary-500/50 transition-colors z-10"
          />
        </div>

        {/* ── MAIN CANVAS ── */}
        {currentDashboard ? (
          <div className="flex-1 flex flex-col overflow-hidden" style={{ minHeight: 0 }}>
            {/* Widget toolbar */}
            {!previewMode && (
              <div className="flex items-center gap-1.5 px-3 py-2 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 overflow-x-auto flex-shrink-0">
                <button onClick={() => setShowWidgetPicker(true)}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400 rounded-lg hover:bg-primary-100 dark:hover:bg-primary-900/50 transition-colors flex-shrink-0 border border-primary-200 dark:border-primary-700 font-medium text-xs">
                  <Plus className="w-3.5 h-3.5" />Ajouter Widget
                </button>
                <div className="w-px h-6 bg-gray-200 dark:bg-gray-700 mx-1" />
                {/* Quick add: most common types */}
                {WIDGET_TYPES.slice(0, 8).map(wt => {
                  const Icon = wt.icon
                  return (
                    <button key={wt.type} onClick={() => addWidget(wt.type)} title={wt.description}
                      className="flex items-center gap-1 px-2 py-1.5 bg-gray-50 dark:bg-gray-700 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors flex-shrink-0 border border-gray-200 dark:border-primary-600">
                      <div className={`w-4 h-4 rounded flex items-center justify-center ${wt.color}`}>
                        <Icon className="w-2.5 h-2.5 text-white" />
                      </div>
                      <span className="text-[10px] font-medium text-gray-600 dark:text-gray-300 whitespace-nowrap">{wt.name}</span>
                    </button>
                  )
                })}
              </div>
            )}

            {/* Global Filter Bar */}
            {widgets.some(w => w.config?.filter_field) && (
              <GlobalFilterBar widgets={widgets} globalFilters={globalFilters} setGlobalFilters={setGlobalFilters} />
            )}

            {/* Grid */}
            <div ref={gridContainerRef} className="flex-1 overflow-auto bg-slate-50 dark:bg-gray-950 p-4" style={{ minHeight: 0 }}>
              {widgets.length === 0 ? (
                <div className="flex items-center justify-center h-full text-gray-400">
                  <div className="text-center">
                    <LayoutGrid className="w-12 h-12 mx-auto mb-3 opacity-40" />
                    <p className="text-sm font-medium">Cliquez sur "Ajouter Widget" pour commencer</p>
                    <p className="text-xs text-gray-400 mt-1">ou utilisez les raccourcis dans la barre d'outils</p>
                  </div>
                </div>
              ) : (
                <GridLayout
                  className="layout"
                  layout={layout}
                  cols={12}
                  rowHeight={60}
                  width={gridWidth - 32 || 1200}
                  isDraggable={!previewMode}
                  isResizable={!previewMode}
                  draggableHandle=".widget-drag-handle"
                  onLayoutChange={onLayoutChange}
                  compactType="vertical"
                  margin={[12, 12]}
                  containerPadding={[0, 0]}
                >
                  {widgets.map(widget => (
                    <div key={widget.id}
                      className={`rounded-xl border-2 overflow-hidden flex flex-col bg-white dark:bg-gray-800 shadow-sm transition-shadow hover:shadow-md
                        ${selectedWidgetId === widget.id && !previewMode ? 'border-primary-500 ring-2 ring-primary-200 dark:ring-primary-800' : 'border-gray-200 dark:border-gray-700'}`}
                      onClick={() => !previewMode && setSelectedWidgetId(widget.id)}>
                      <WidgetCard
                        key={`${widget.id}-${refreshKey}`}
                        widget={widget}
                        previewMode={previewMode}
                        onDelete={() => deleteWidget(widget.id)}
                        onDuplicate={() => duplicateWidget(widget.id)}
                        globalFilters={globalFilters}
                      />
                    </div>
                  ))}
                </GridLayout>
              )}
            </div>
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center bg-slate-50 dark:bg-gray-950">
            <div className="text-center">
              <LayoutGrid className="w-16 h-16 mx-auto mb-4 opacity-20 text-gray-400" />
              <p className="text-lg font-semibold text-gray-600 dark:text-gray-300 mb-1">Dashboard Builder</p>
              <p className="text-sm text-gray-400 mb-6">Selectionnez un dashboard ou creez-en un nouveau</p>
              <button onClick={() => setShowNewModal(true)}
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 font-medium transition-colors">
                <Plus className="w-4 h-4" />Creer un Dashboard
              </button>
            </div>
          </div>
        )}

        {/* ── RIGHT CONFIG PANEL ── */}
        {selectedWidget && !previewMode && (
          <div className="w-80 bg-white dark:bg-gray-800 border-l border-gray-200 dark:border-gray-700 flex flex-col flex-shrink-0">
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
              <h3 className="text-sm font-bold text-gray-900 dark:text-white">Configuration</h3>
              <button onClick={() => setSelectedWidgetId(null)} className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded">
                <X className="w-4 h-4 text-gray-400" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              <WidgetConfigPanel
                widget={selectedWidget}
                onUpdate={(updates) => updateWidget(selectedWidget.id, updates)}
              />
            </div>
          </div>
        )}
      </div>

      {/* ── AI GENERATOR MODAL ── */}
      {showAIGenerator && (
        <AIDashboardGenerator
          onImport={handleAIImport}
          onClose={() => setShowAIGenerator(false)}
        />
      )}

      {/* ── MODALS ── */}
      {showNewModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/50" onClick={() => setShowNewModal(false)} />
          <div className="relative bg-white dark:bg-gray-800 rounded-xl shadow-2xl p-6 w-96">
            <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-4">Nouveau Dashboard</h2>
            <input type="text" value={newDashboardName} onChange={e => setNewDashboardName(e.target.value)}
              placeholder="Nom du dashboard" autoFocus onKeyDown={e => e.key === 'Enter' && createNewDashboard()}
              className="w-full px-3 py-2.5 border border-primary-300 dark:border-primary-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-700 dark:text-white mb-3" />
            <select value={newDashApp} onChange={e => setNewDashApp(e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-700 dark:text-white mb-4 focus:ring-2 focus:ring-primary-400 outline-none">
              <option value="">-- Application (optionnel) --</option>
              {APPLICATION_OPTIONS.filter(a => a.value).map(a => (
                <option key={a.value} value={a.value}>{a.label}</option>
              ))}
            </select>
            <div className="flex justify-end gap-2">
              <button onClick={() => setShowNewModal(false)} className="px-4 py-2 text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg">Annuler</button>
              <button onClick={createNewDashboard} disabled={!newDashboardName.trim()}
                className="px-4 py-2 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50">Creer</button>
            </div>
          </div>
        </div>
      )}

      {/* Widget Picker Modal */}
      {showWidgetPicker && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/50" onClick={() => setShowWidgetPicker(false)} />
          <div className="relative bg-white dark:bg-gray-800 rounded-xl shadow-2xl p-6 w-[600px] max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-bold text-gray-900 dark:text-white">Ajouter un Widget</h2>
              <button onClick={() => setShowWidgetPicker(false)} className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg">
                <X className="w-5 h-5 text-gray-400" />
              </button>
            </div>
            {WIDGET_CATEGORIES.map(cat => (
              <div key={cat} className="mb-5">
                <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">{cat}</h3>
                <div className="grid grid-cols-3 gap-2">
                  {WIDGET_TYPES.filter(wt => wt.category === cat).map(wt => {
                    const Icon = wt.icon
                    return (
                      <button key={wt.type} onClick={() => addWidget(wt.type)}
                        className="flex flex-col items-center gap-2 p-3 rounded-xl border border-gray-200 dark:border-gray-700 hover:border-primary-300 dark:hover:border-primary-600 hover:bg-primary-50 dark:hover:bg-primary-900/20 transition-all group">
                        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${wt.color} group-hover:scale-110 transition-transform`}>
                          <Icon className="w-5 h-5 text-white" />
                        </div>
                        <span className="text-xs font-semibold text-gray-700 dark:text-gray-300">{wt.name}</span>
                        <span className="text-[10px] text-gray-400 text-center leading-tight">{wt.description}</span>
                      </button>
                    )
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div className={`fixed bottom-4 right-4 z-50 px-4 py-2.5 rounded-lg shadow-lg text-sm font-medium text-white transition-all ${toast.type === 'error' ? 'bg-red-500' : 'bg-green-500'}`}>
          {toast.msg}
        </div>
      )}
    </div>
  )
}


// ════════════════════════════════════════════════════════════════════
// GLOBAL FILTER BAR
// ════════════════════════════════════════════════════════════════════
function GlobalFilterBar({ widgets, globalFilters, setGlobalFilters }) {
  // Collect unique filter fields from all widgets
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
    <div className="flex items-center gap-3 px-4 py-2 bg-blue-50 dark:bg-blue-900/20 border-b border-blue-200 dark:border-blue-800 flex-shrink-0">
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
// WIDGET CARD (inside grid)
// ════════════════════════════════════════════════════════════════════
function WidgetCard({ widget, previewMode, onDelete, onDuplicate, globalFilters }) {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const wt = WIDGET_TYPE_MAP[widget.type] || WIDGET_TYPES[0]
  const Icon = wt.icon

  useEffect(() => {
    const load = async () => {
      const dsId = widget.config?.dataSourceId
      if (!dsId) { setData([]); return }
      setLoading(true); setError(null)
      try {
        const res = await previewDataSource(dsId, globalFilters || {})
        let rawData = res.data?.data || []

        // Convertir les valeurs numériques (les API SQL retournent parfois des strings)
        if (rawData.length > 0) {
          rawData = rawData.map(row => {
            const converted = { ...row }
            for (const key of Object.keys(converted)) {
              const val = converted[key]
              if (val !== null && val !== undefined && val !== '' && typeof val === 'string') {
                if (/^\d{4}-\d{2}/.test(val)) continue // Exclure les dates
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

        // Client-side filtering if filter_field is set
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
  }, [widget.config?.dataSourceId, globalFilters, widget.config?.filter_field, widget.config?.sort_field, widget.config?.sort_direction, widget.config?.limit_rows])

  return (
    <>
      {/* Header */}
      <div className="flex items-center justify-between px-2.5 py-1.5 bg-gray-50 dark:bg-gray-700/50 border-b border-gray-200 dark:border-primary-600 flex-shrink-0">
        <div className="flex items-center gap-1.5 min-w-0 flex-1">
          {!previewMode && <GripVertical className="w-3.5 h-3.5 text-gray-400 cursor-grab widget-drag-handle flex-shrink-0" />}
          <div className={`w-5 h-5 rounded flex items-center justify-center flex-shrink-0 ${wt.color}`}>
            <Icon className="w-3 h-3 text-white" />
          </div>
          <span className="text-xs font-semibold text-gray-700 dark:text-gray-300 truncate">{widget.title}</span>
        </div>
        {!previewMode && (
          <div className="flex items-center gap-0.5 flex-shrink-0">
            <button onClick={e => { e.stopPropagation(); onDuplicate() }} className="p-1 hover:bg-gray-200 dark:hover:bg-gray-600 rounded" title="Dupliquer">
              <Copy className="w-3 h-3 text-gray-400" />
            </button>
            <button onClick={e => { e.stopPropagation(); onDelete() }} className="p-1 hover:bg-red-100 dark:hover:bg-red-900/30 rounded" title="Supprimer">
              <X className="w-3 h-3 text-red-400" />
            </button>
          </div>
        )}
      </div>
      {/* Content */}
      <div className="flex-1 p-2 overflow-hidden" style={{ minHeight: 0 }}>
        {loading ? (
          <div className="flex items-center justify-center h-full"><RefreshCw className="w-5 h-5 text-gray-400 animate-spin" /></div>
        ) : error ? (
          <div className="flex items-center justify-center h-full text-red-500 text-xs gap-1"><AlertCircle className="w-4 h-4" />{error}</div>
        ) : !widget.config?.dataSourceId && !['text', 'image'].includes(widget.type) ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-400 text-xs gap-1">
            <Settings2 className="w-6 h-6 opacity-40" />
            <span>Configurez une source</span>
          </div>
        ) : (
          <WidgetContent widget={widget} data={data} />
        )}
      </div>
    </>
  )
}


// ════════════════════════════════════════════════════════════════════
// WIDGET CONTENT (renders all widget types)
// ════════════════════════════════════════════════════════════════════
function WidgetContent({ widget, data, onDrillDown }) {
  const { theme } = useTheme()
  const COLORS = generateThemeColors(theme)
  const cfg = widget.config || {}

  switch (widget.type) {
    case 'kpi':
    case 'kpi_compare': {
      const vf = cfg.value_field || Object.keys(data[0] || {})[1] || 'value'
      const agg = cfg.aggregation || 'SUM'
      const total = aggregateData(data, vf, agg)
      const baseColor = cfg.kpi_color || '#3b82f6'
      const kpiColor = getConditionalColor(total, cfg.thresholds) || baseColor
      const prefix = cfg.prefix || ''
      const suffix = cfg.suffix || ''
      const subtitle = cfg.subtitle || `${vf} (${agg})`
      return (
        <div className="flex flex-col items-center justify-center h-full cursor-pointer" onClick={() => onDrillDown?.({ field: vf, value: null })}>
          <span className="text-3xl font-black tabular-nums" style={{ color: kpiColor }}>
            {prefix}{formatNumber(total)}{suffix}
          </span>
          <span className="text-xs text-gray-500 mt-1">{subtitle}</span>
          {widget.type === 'kpi_compare' && cfg.compare_field && (
            <CompareIndicator data={data} valueField={vf} compareField={cfg.compare_field} aggregation={agg} />
          )}
        </div>
      )
    }

    case 'gauge': {
      const vf = cfg.value_field || Object.keys(data[0] || {})[1] || 'value'
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
      const vf = cfg.value_field || Object.keys(data[0] || {})[1] || 'value'
      const agg = cfg.aggregation || 'SUM'
      const total = aggregateData(data, vf, agg)
      const maxVal = cfg.max_value || 100
      const pct = Math.min(100, Math.max(0, (total / maxVal) * 100))
      const barColor = getConditionalColor(pct, cfg.thresholds) || cfg.kpi_color || '#3b82f6'
      return (
        <div className="flex flex-col justify-center h-full px-2 gap-2">
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
      const xf = cfg.x_field || Object.keys(data[0] || {})[0]
      const yf = cfg.y_field || cfg.value_field || Object.keys(data[0] || {})[1]
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
      const xf = cfg.x_field || Object.keys(data[0] || {})[0]
      const yf = cfg.y_field || Object.keys(data[0] || {})[1]
      const color = cfg.color || COLORS[0]
      const horizontal = cfg.horizontal || false
      return (
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 5, right: 10, left: 5, bottom: 5 }}
            layout={horizontal ? 'vertical' : 'horizontal'}
            onClick={e => e?.activePayload?.[0] && onDrillDown?.({ field: xf, value: e.activePayload[0].payload[xf] })}>
            {cfg.show_grid !== false && <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />}
            {horizontal ? (
              <>
                <YAxis dataKey={xf} type="category" tick={{ fontSize: 10 }} width={80} />
                <XAxis type="number" tick={{ fontSize: 10 }} tickFormatter={formatNumber} />
              </>
            ) : (
              <>
                <XAxis dataKey={xf} tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} tickFormatter={formatNumber} />
              </>
            )}
            <Tooltip formatter={v => formatNumber(v)} />
            {cfg.show_legend && <Legend wrapperStyle={{ fontSize: 10 }} />}
            <Bar dataKey={yf} fill={color} radius={horizontal ? [0, 3, 3, 0] : [3, 3, 0, 0]} name={cfg.y_label || yf}>
              {cfg.show_labels && <LabelList dataKey={yf} position="top" fontSize={9} formatter={formatNumber} />}
            </Bar>
            {cfg.y_field_2 && <Bar dataKey={cfg.y_field_2} fill={cfg.color_2 || COLORS[1]} radius={horizontal ? [0, 3, 3, 0] : [3, 3, 0, 0]} name={cfg.y_label_2 || cfg.y_field_2} />}
            {cfg.y_field_3 && <Bar dataKey={cfg.y_field_3} fill={cfg.color_3 || COLORS[2]} radius={horizontal ? [0, 3, 3, 0] : [3, 3, 0, 0]} name={cfg.y_label_3 || cfg.y_field_3} />}
          </BarChart>
        </ResponsiveContainer>
      )
    }

    case 'chart_stacked_bar': {
      const xf = cfg.x_field || Object.keys(data[0] || {})[0]
      const yf = cfg.y_field || Object.keys(data[0] || {})[1]
      const mode = cfg.stack_mode || 'stacked' // stacked | grouped | percent
      return (
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 5, right: 10, left: 5, bottom: 5 }}>
            {cfg.show_grid !== false && <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />}
            <XAxis dataKey={xf} tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} tickFormatter={formatNumber} />
            <Tooltip formatter={v => formatNumber(v)} />
            {cfg.show_legend && <Legend wrapperStyle={{ fontSize: 10 }} />}
            <Bar dataKey={yf} stackId={mode === 'stacked' || mode === 'percent' ? 'stack' : undefined} fill={cfg.color || COLORS[0]} radius={[3, 3, 0, 0]} name={cfg.y_label || yf}>
              {cfg.show_labels && <LabelList dataKey={yf} position="center" fontSize={9} fill="#fff" formatter={formatNumber} />}
            </Bar>
            {cfg.y_field_2 && <Bar dataKey={cfg.y_field_2} stackId={mode === 'stacked' || mode === 'percent' ? 'stack' : undefined} fill={cfg.color_2 || COLORS[1]} name={cfg.y_label_2 || cfg.y_field_2} />}
            {cfg.y_field_3 && <Bar dataKey={cfg.y_field_3} stackId={mode === 'stacked' || mode === 'percent' ? 'stack' : undefined} fill={cfg.color_3 || COLORS[2]} name={cfg.y_label_3 || cfg.y_field_3} />}
          </BarChart>
        </ResponsiveContainer>
      )
    }

    case 'chart_combo': {
      const xf = cfg.x_field || Object.keys(data[0] || {})[0]
      const yf = cfg.y_field || Object.keys(data[0] || {})[1]
      return (
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 5, right: 10, left: 5, bottom: 5 }}>
            {cfg.show_grid !== false && <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />}
            <XAxis dataKey={xf} tick={{ fontSize: 10 }} />
            <YAxis yAxisId="left" tick={{ fontSize: 10 }} tickFormatter={formatNumber} />
            {cfg.y_field_2 && <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 10 }} tickFormatter={formatNumber} />}
            <Tooltip formatter={v => formatNumber(v)} />
            {cfg.show_legend && <Legend wrapperStyle={{ fontSize: 10 }} />}
            <Bar yAxisId="left" dataKey={yf} fill={cfg.color || COLORS[0]} radius={[3, 3, 0, 0]} name={cfg.y_label || yf}>
              {cfg.show_labels && <LabelList dataKey={yf} position="top" fontSize={9} formatter={formatNumber} />}
            </Bar>
            {cfg.y_field_2 && <Line yAxisId={cfg.combo_same_axis ? 'left' : 'right'} type="monotone" dataKey={cfg.y_field_2} stroke={cfg.color_2 || COLORS[1]} strokeWidth={2} dot={{ r: 3 }} name={cfg.y_label_2 || cfg.y_field_2} />}
            {cfg.y_field_3 && <Line yAxisId="left" type="monotone" dataKey={cfg.y_field_3} stroke={cfg.color_3 || COLORS[2]} strokeWidth={2} dot={{ r: 3 }} name={cfg.y_label_3 || cfg.y_field_3} />}
          </ComposedChart>
        </ResponsiveContainer>
      )
    }

    case 'chart_line': {
      const xf = cfg.x_field || Object.keys(data[0] || {})[0]
      const yf = cfg.y_field || Object.keys(data[0] || {})[1]
      const color = cfg.color || COLORS[0]
      return (
        <ResponsiveContainer width="100%" height="100%">
          <ReLineChart data={data} margin={{ top: 5, right: 10, left: 5, bottom: 5 }}
            onClick={e => e?.activePayload?.[0] && onDrillDown?.({ field: xf, value: e.activePayload[0].payload[xf] })}>
            {cfg.show_grid !== false && <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />}
            <XAxis dataKey={xf} tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} tickFormatter={formatNumber} />
            <Tooltip formatter={v => formatNumber(v)} />
            {cfg.show_legend && <Legend wrapperStyle={{ fontSize: 10 }} />}
            <Line type={cfg.curve_type || 'monotone'} dataKey={yf} stroke={color} strokeWidth={2} dot={{ r: 3 }} name={cfg.y_label || yf}>
              {cfg.show_labels && <LabelList dataKey={yf} position="top" fontSize={9} formatter={formatNumber} />}
            </Line>
            {cfg.y_field_2 && <Line type={cfg.curve_type || 'monotone'} dataKey={cfg.y_field_2} stroke={cfg.color_2 || COLORS[1]} strokeWidth={2} dot={{ r: 3 }} name={cfg.y_label_2 || cfg.y_field_2} />}
            {cfg.y_field_3 && <Line type={cfg.curve_type || 'monotone'} dataKey={cfg.y_field_3} stroke={cfg.color_3 || COLORS[2]} strokeWidth={2} dot={{ r: 3 }} name={cfg.y_label_3 || cfg.y_field_3} />}
          </ReLineChart>
        </ResponsiveContainer>
      )
    }

    case 'chart_pie': {
      const lf = cfg.label_field || Object.keys(data[0] || {})[0]
      const vf = cfg.value_field || Object.keys(data[0] || {})[1]
      return (
        <ResponsiveContainer width="100%" height="100%">
          <RePieChart>
            <Pie data={data} dataKey={vf} nameKey={lf} cx="50%" cy="50%" outerRadius="75%" innerRadius={cfg.donut ? '45%' : '0%'}
              label={cfg.show_labels !== false ? ({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%` : false}
              labelLine={cfg.show_labels !== false}
              onClick={entry => entry?.[lf] && onDrillDown?.({ field: lf, value: entry[lf] })}>
              {data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
            </Pie>
            <Tooltip formatter={v => formatNumber(v)} />
            {cfg.show_legend && <Legend wrapperStyle={{ fontSize: 10 }} />}
          </RePieChart>
        </ResponsiveContainer>
      )
    }

    case 'chart_area': {
      const xf = cfg.x_field || Object.keys(data[0] || {})[0]
      const yf = cfg.y_field || Object.keys(data[0] || {})[1]
      const color = cfg.color || COLORS[0]
      return (
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 5, right: 10, left: 5, bottom: 5 }}>
            {cfg.show_grid !== false && <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />}
            <XAxis dataKey={xf} tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} tickFormatter={formatNumber} />
            <Tooltip formatter={v => formatNumber(v)} />
            <Area type="monotone" dataKey={yf} stroke={color} fill={color} fillOpacity={0.2} strokeWidth={2} stackId={cfg.stacked ? 'stack' : undefined} />
            {cfg.y_field_2 && <Area type="monotone" dataKey={cfg.y_field_2} stroke={cfg.color_2 || COLORS[1]} fill={cfg.color_2 || COLORS[1]} fillOpacity={0.15} strokeWidth={2} stackId={cfg.stacked ? 'stack' : undefined} />}
            {cfg.y_field_3 && <Area type="monotone" dataKey={cfg.y_field_3} stroke={cfg.color_3 || COLORS[2]} fill={cfg.color_3 || COLORS[2]} fillOpacity={0.1} strokeWidth={2} stackId={cfg.stacked ? 'stack' : undefined} />}
          </AreaChart>
        </ResponsiveContainer>
      )
    }

    case 'chart_funnel': {
      const lf = cfg.label_field || Object.keys(data[0] || {})[0]
      const vf = cfg.value_field || Object.keys(data[0] || {})[1]
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
      const lf = cfg.label_field || Object.keys(data[0] || {})[0]
      const vf = cfg.value_field || Object.keys(data[0] || {})[1]
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
        <div className="overflow-auto h-full text-xs">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-700 sticky top-0">
              <tr>{cols.map(c => <th key={c} className="px-2 py-1.5 text-left font-semibold text-gray-600 dark:text-gray-300 border-b whitespace-nowrap">{c}</th>)}</tr>
            </thead>
            <tbody>
              {data.slice(0, cfg.max_rows || 100).map((row, i) => (
                <tr key={i} className={i % 2 === 0 ? 'bg-white dark:bg-gray-800' : 'bg-gray-50/50 dark:bg-gray-800/50'}>
                  {cols.map(c => {
                    const val = row[c]
                    const isNum = typeof val === 'number'
                    // Conditional formatting for table cells
                    let cellBg = ''
                    if (isNum && cfg.table_thresholds?.[c]) {
                      const cc = getConditionalColor(val, cfg.table_thresholds[c])
                      if (cc) cellBg = cc
                    }
                    return (
                      <td key={c} className="px-2 py-1 text-gray-700 dark:text-gray-300 border-b border-gray-100 dark:border-gray-700 whitespace-nowrap"
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
          {cfg.content || 'Texte...'}
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

// ── Compare indicator for KPI ──
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


// ════════════════════════════════════════════════════════════════════
// WIDGET CONFIG PANEL
// ════════════════════════════════════════════════════════════════════
function WidgetConfigPanel({ widget, onUpdate }) {
  const cfg = widget.config || {}
  const [availableFields, setAvailableFields] = useState([])
  const [configTab, setConfigTab] = useState('general')

  // Load available fields when datasource changes
  useEffect(() => {
    const loadFields = async () => {
      if (!cfg.dataSourceId) { setAvailableFields([]); return }
      try {
        const res = await previewDataSource(cfg.dataSourceId, {})
        // Try columns array first (always present even if data is empty)
        const cols = res.data?.columns || []
        if (cols.length > 0) {
          setAvailableFields(cols)
          return
        }
        // Fallback: extract from first data row
        const data = res.data?.data || []
        if (data.length > 0) {
          setAvailableFields(Object.keys(data[0]))
          return
        }
        // If preview failed but returned error, try to get columns from datasource metadata
        if (!res.data?.success) {
          try {
            const dsRes = await getDataSource(cfg.dataSourceId)
            const query = dsRes.data?.data?.query_template || ''
            // Parse SELECT column names from query
            const selectMatch = query.match(/SELECT\s+(?:TOP\s+\d+\s+)?([\s\S]*?)\s+FROM/i)
            if (selectMatch) {
              const selectPart = selectMatch[1]
              const fieldNames = selectPart.split(',').map(col => {
                col = col.trim()
                // Extract alias: "... AS [alias]" or "... AS alias"
                const asMatch = col.match(/\bAS\s+\[?([^\]]+)\]?\s*$/i)
                if (asMatch) return asMatch[1].trim()
                // Extract [table].[column] pattern
                const bracketMatch = col.match(/\[([^\]]+)\]\s*$/)
                if (bracketMatch) return bracketMatch[1].trim()
                // Last segment after dot
                const dotParts = col.split('.')
                return dotParts[dotParts.length - 1].replace(/[\[\]]/g, '').trim()
              }).filter(f => f && f !== '*')
              if (fieldNames.length > 0) {
                setAvailableFields(fieldNames)
                return
              }
            }
          } catch { /* ignore fallback error */ }
        }
        setAvailableFields([])
      } catch (e) {
        console.warn('Impossible de charger les champs de la source:', e)
        setAvailableFields([])
      }
    }
    loadFields()
  }, [cfg.dataSourceId])

  const updateCfg = (key, val) => onUpdate({ config: { ...cfg, [key]: val } })

  const FieldSelect = ({ label, cfgKey, placeholder }) => (
    <div>
      <label className="block text-[11px] font-semibold text-gray-500 dark:text-gray-400 mb-1 uppercase tracking-wider">{label}</label>
      <select value={cfg[cfgKey] || ''} onChange={e => updateCfg(cfgKey, e.target.value)}
        className="w-full px-2.5 py-2 text-sm border border-primary-300 dark:border-primary-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-700 dark:text-white">
        <option value="">{placeholder || '-- Selectionner --'}</option>
        {availableFields.map(f => <option key={f} value={f}>{f}</option>)}
      </select>
    </div>
  )

  const ColorInput = ({ label, cfgKey, defaultVal }) => (
    <div>
      <label className="block text-[11px] font-semibold text-gray-500 dark:text-gray-400 mb-1 uppercase tracking-wider">{label}</label>
      <div className="flex items-center gap-2">
        <input type="color" value={cfg[cfgKey] || defaultVal || '#3b82f6'} onChange={e => updateCfg(cfgKey, e.target.value)}
          className="w-8 h-8 rounded cursor-pointer border border-primary-300 dark:border-primary-600" />
        <input type="text" value={cfg[cfgKey] || defaultVal || '#3b82f6'} onChange={e => updateCfg(cfgKey, e.target.value)}
          className="flex-1 px-2.5 py-1.5 text-sm border border-primary-300 dark:border-primary-600 rounded-lg dark:bg-gray-700 dark:text-white font-mono" />
      </div>
    </div>
  )

  const TextInput = ({ label, cfgKey, placeholder, type = 'text' }) => (
    <div>
      <label className="block text-[11px] font-semibold text-gray-500 dark:text-gray-400 mb-1 uppercase tracking-wider">{label}</label>
      <input type={type} value={cfg[cfgKey] || ''} onChange={e => updateCfg(cfgKey, type === 'number' ? Number(e.target.value) : e.target.value)}
        placeholder={placeholder}
        className="w-full px-2.5 py-2 text-sm border border-primary-300 dark:border-primary-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-700 dark:text-white" />
    </div>
  )

  const CheckInput = ({ label, cfgKey }) => (
    <label className="flex items-center gap-2 cursor-pointer">
      <input type="checkbox" checked={!!cfg[cfgKey]} onChange={e => updateCfg(cfgKey, e.target.checked)}
        className="rounded text-primary-500 focus:ring-primary-500" />
      <span className="text-sm text-gray-700 dark:text-gray-300">{label}</span>
    </label>
  )

  const SelectInput = ({ label, cfgKey, options, placeholder }) => (
    <div>
      <label className="block text-[11px] font-semibold text-gray-500 dark:text-gray-400 mb-1 uppercase tracking-wider">{label}</label>
      <select value={cfg[cfgKey] || ''} onChange={e => updateCfg(cfgKey, e.target.value)}
        className="w-full px-2.5 py-2 text-sm border border-primary-300 dark:border-primary-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-700 dark:text-white">
        {placeholder && <option value="">{placeholder}</option>}
        {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  )

  // Config tabs for complex widgets
  const showTabs = !['text', 'image'].includes(widget.type)
  const tabs = [
    { key: 'general', label: 'General' },
    { key: 'data', label: 'Donnees' },
    { key: 'style', label: 'Style' },
  ]

  return (
    <div className="space-y-4">
      {/* Title */}
      <div>
        <label className="block text-[11px] font-semibold text-gray-500 dark:text-gray-400 mb-1 uppercase tracking-wider">Titre</label>
        <input type="text" value={widget.title} onChange={e => onUpdate({ title: e.target.value })}
          className="w-full px-2.5 py-2 text-sm border border-primary-300 dark:border-primary-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-700 dark:text-white font-medium" />
      </div>

      {/* DataSource */}
      {!['text', 'image'].includes(widget.type) && (
        <div>
          <label className="block text-[11px] font-semibold text-gray-500 dark:text-gray-400 mb-1 uppercase tracking-wider">Source de donnees</label>
          <DataSourceSelector
            value={cfg.dataSourceCode || cfg.dataSourceId}
            onChange={(ds) => onUpdate({
              config: { ...cfg, dataSourceId: ds?.id || null, dataSourceCode: ds?.code || null, dataSourceOrigin: ds?.origin || null }
            })}
            showPreview={false}
            placeholder="Selectionner une source..."
          />
          {cfg.dataSourceCode && (
            <div className="mt-1.5 text-[10px] text-primary-600 flex items-center gap-1">
              <Settings2 className="w-3 h-3" />{cfg.dataSourceCode}
            </div>
          )}
        </div>
      )}

      {/* Tabs */}
      {showTabs && (
        <>
          <div className="flex items-center gap-1 border-b border-gray-200 dark:border-gray-700">
            {tabs.map(tab => (
              <button key={tab.key} onClick={() => setConfigTab(tab.key)}
                className={`px-3 py-1.5 text-xs font-medium border-b-2 transition-colors ${
                  configTab === tab.key
                    ? 'border-primary-500 text-primary-600 dark:text-primary-400'
                    : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
                }`}>
                {tab.label}
              </button>
            ))}
          </div>

          {/* ── GENERAL TAB ── */}
          {configTab === 'general' && (
            <div className="space-y-4">
              {/* KPI */}
              {(widget.type === 'kpi' || widget.type === 'kpi_compare') && (
                <>
                  <FieldSelect label="Champ valeur" cfgKey="value_field" placeholder="Champ numerique" />
                  <SelectInput label="Agregation" cfgKey="aggregation" options={AGGREGATION_FUNCTIONS} />
                  <TextInput label="Sous-titre" cfgKey="subtitle" placeholder="Ex: CA Total, Marge..." />
                  <div className="grid grid-cols-2 gap-3">
                    <TextInput label="Prefixe" cfgKey="prefix" placeholder="Ex: MAD " />
                    <TextInput label="Suffixe" cfgKey="suffix" placeholder="Ex: DH, %, ..." />
                  </div>
                  {widget.type === 'kpi_compare' && (
                    <FieldSelect label="Champ comparaison (N-1)" cfgKey="compare_field" placeholder="Champ a comparer" />
                  )}
                </>
              )}

              {/* Gauge / Progress */}
              {(widget.type === 'gauge' || widget.type === 'progress') && (
                <>
                  <FieldSelect label="Champ valeur" cfgKey="value_field" placeholder="Champ numerique" />
                  <SelectInput label="Agregation" cfgKey="aggregation" options={AGGREGATION_FUNCTIONS} />
                  <TextInput label="Valeur max (objectif)" cfgKey="max_value" placeholder="100" type="number" />
                  <TextInput label="Sous-titre" cfgKey="subtitle" placeholder="Ex: Objectif" />
                </>
              )}

              {/* Sparkline */}
              {widget.type === 'sparkline' && (
                <>
                  <FieldSelect label="Axe X" cfgKey="x_field" />
                  <FieldSelect label="Valeur" cfgKey="value_field" placeholder="Champ numerique" />
                  <SelectInput label="Agregation" cfgKey="aggregation" options={AGGREGATION_FUNCTIONS} />
                  <TextInput label="Sous-titre" cfgKey="subtitle" placeholder="Label" />
                </>
              )}

              {/* Bar / Line / Area */}
              {['chart_bar', 'chart_line', 'chart_area', 'chart_stacked_bar', 'chart_combo'].includes(widget.type) && (
                <>
                  <FieldSelect label="Axe X (categories)" cfgKey="x_field" />
                  <FieldSelect label="Axe Y (valeurs)" cfgKey="y_field" />
                  <TextInput label="Nom serie 1" cfgKey="y_label" placeholder="Label..." />
                  <hr className="border-gray-200 dark:border-gray-700" />
                  <p className="text-[10px] text-gray-400 uppercase tracking-wider font-semibold">2eme Serie (optionnel)</p>
                  <FieldSelect label="Axe Y 2" cfgKey="y_field_2" />
                  {cfg.y_field_2 && <TextInput label="Nom serie 2" cfgKey="y_label_2" placeholder="Label 2..." />}
                  <p className="text-[10px] text-gray-400 uppercase tracking-wider font-semibold">3eme Serie (optionnel)</p>
                  <FieldSelect label="Axe Y 3" cfgKey="y_field_3" />
                  {cfg.y_field_3 && <TextInput label="Nom serie 3" cfgKey="y_label_3" placeholder="Label 3..." />}
                </>
              )}

              {/* Pie / Funnel / Treemap */}
              {['chart_pie', 'chart_funnel', 'chart_treemap'].includes(widget.type) && (
                <>
                  <FieldSelect label="Champ labels" cfgKey="label_field" />
                  <FieldSelect label="Champ valeurs" cfgKey="value_field" />
                </>
              )}

              {/* Table */}
              {widget.type === 'table' && (
                <TextInput label="Nombre max de lignes" cfgKey="max_rows" placeholder="100" type="number" />
              )}
            </div>
          )}

          {/* ── DATA TAB ── */}
          {configTab === 'data' && (
            <div className="space-y-4">
              <p className="text-[10px] text-gray-400 uppercase tracking-wider font-semibold">Tri des donnees</p>
              <FieldSelect label="Trier par" cfgKey="sort_field" placeholder="Pas de tri" />
              {cfg.sort_field && (
                <SelectInput label="Direction" cfgKey="sort_direction" options={[
                  { value: 'asc', label: 'Croissant (A-Z, 0-9)' },
                  { value: 'desc', label: 'Decroissant (Z-A, 9-0)' },
                ]} />
              )}
              <TextInput label="Limiter a N lignes" cfgKey="limit_rows" placeholder="Toutes" type="number" />

              <hr className="border-gray-200 dark:border-gray-700" />
              <p className="text-[10px] text-gray-400 uppercase tracking-wider font-semibold">Filtre global</p>
              <FieldSelect label="Champ filtre" cfgKey="filter_field" placeholder="Aucun filtre" />
              <p className="text-[10px] text-gray-400 leading-tight">
                Ce champ sera expose comme filtre global. Les utilisateurs pourront filtrer par valeur.
              </p>
            </div>
          )}

          {/* ── STYLE TAB ── */}
          {configTab === 'style' && (
            <div className="space-y-4">
              {/* KPI / Gauge / Progress / Sparkline colors */}
              {['kpi', 'kpi_compare', 'gauge', 'progress', 'sparkline'].includes(widget.type) && (
                <ColorInput label="Couleur principale" cfgKey="kpi_color" defaultVal="#3b82f6" />
              )}

              {/* Chart colors */}
              {['chart_bar', 'chart_line', 'chart_area', 'chart_stacked_bar', 'chart_combo'].includes(widget.type) && (
                <>
                  <ColorInput label="Couleur serie 1" cfgKey="color" defaultVal="#3b82f6" />
                  {cfg.y_field_2 && <ColorInput label="Couleur serie 2" cfgKey="color_2" defaultVal="#10b981" />}
                  {cfg.y_field_3 && <ColorInput label="Couleur serie 3" cfgKey="color_3" defaultVal="#f59e0b" />}
                </>
              )}

              {/* Sparkline color */}
              {widget.type === 'sparkline' && (
                <ColorInput label="Couleur courbe" cfgKey="color" defaultVal="#3b82f6" />
              )}

              {/* Chart options */}
              {['chart_bar', 'chart_line', 'chart_area', 'chart_stacked_bar', 'chart_combo', 'chart_pie'].includes(widget.type) && (
                <>
                  <hr className="border-gray-200 dark:border-gray-700" />
                  <p className="text-[10px] text-gray-400 uppercase tracking-wider font-semibold">Options graphique</p>
                  <CheckInput label="Afficher la legende" cfgKey="show_legend" />
                  <CheckInput label="Afficher les etiquettes" cfgKey="show_labels" />
                  {!['chart_pie'].includes(widget.type) && (
                    <CheckInput label="Grille de fond" cfgKey="show_grid" />
                  )}
                </>
              )}

              {/* Type-specific options */}
              {widget.type === 'chart_bar' && <CheckInput label="Barres horizontales" cfgKey="horizontal" />}
              {widget.type === 'chart_pie' && <CheckInput label="Mode donut (creux)" cfgKey="donut" />}
              {widget.type === 'chart_area' && <CheckInput label="Aires empilees" cfgKey="stacked" />}
              {widget.type === 'chart_stacked_bar' && (
                <SelectInput label="Mode empilement" cfgKey="stack_mode" options={[
                  { value: 'stacked', label: 'Empile' },
                  { value: 'grouped', label: 'Groupe cote a cote' },
                ]} />
              )}
              {widget.type === 'chart_combo' && (
                <CheckInput label="Meme axe Y pour les 2 series" cfgKey="combo_same_axis" />
              )}
              {widget.type === 'chart_line' && (
                <SelectInput label="Type de courbe" cfgKey="curve_type" options={[
                  { value: 'monotone', label: 'Lisse' },
                  { value: 'linear', label: 'Lineaire' },
                  { value: 'step', label: 'Escalier' },
                ]} />
              )}

              {/* Conditional formatting (for KPI / Gauge / Progress) */}
              {['kpi', 'kpi_compare', 'gauge', 'progress'].includes(widget.type) && (
                <>
                  <hr className="border-gray-200 dark:border-gray-700" />
                  <ThresholdEditor
                    thresholds={cfg.thresholds || []}
                    onChange={t => updateCfg('thresholds', t)}
                  />
                </>
              )}
            </div>
          )}
        </>
      )}

      {/* Non-tabbed: text and image */}
      {widget.type === 'text' && (
        <>
          <div>
            <label className="block text-[11px] font-semibold text-gray-500 dark:text-gray-400 mb-1 uppercase tracking-wider">Contenu</label>
            <textarea value={cfg.content || ''} onChange={e => updateCfg('content', e.target.value)} rows={5}
              className="w-full px-2.5 py-2 text-sm border border-primary-300 dark:border-primary-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-700 dark:text-white" />
          </div>
          <ColorInput label="Couleur de fond" cfgKey="bg_color" defaultVal="transparent" />
          <ColorInput label="Couleur texte" cfgKey="text_color" defaultVal="#374151" />
          <TextInput label="Taille police (px)" cfgKey="font_size" placeholder="14" type="number" />
        </>
      )}

      {widget.type === 'image' && (
        <>
          <TextInput label="URL de l'image" cfgKey="image_url" placeholder="https://..." />
          <SelectInput label="Ajustement" cfgKey="image_fit" options={[
            { value: 'contain', label: 'Contenir (entier)' },
            { value: 'cover', label: 'Couvrir (remplir)' },
            { value: 'fill', label: 'Etirer' },
          ]} />
        </>
      )}
    </div>
  )
}


// ════════════════════════════════════════════════════════════════════
// THRESHOLD EDITOR (Conditional formatting)
// ════════════════════════════════════════════════════════════════════
function ThresholdEditor({ thresholds, onChange }) {
  const addThreshold = () => {
    onChange([...thresholds, { value: 0, color: '#ef4444' }])
  }

  const updateThreshold = (idx, key, val) => {
    const t = [...thresholds]
    t[idx] = { ...t[idx], [key]: key === 'value' ? Number(val) : val }
    onChange(t)
  }

  const removeThreshold = (idx) => {
    onChange(thresholds.filter((_, i) => i !== idx))
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] text-gray-400 uppercase tracking-wider font-semibold">Seuils conditionnels</span>
        <button onClick={addThreshold}
          className="text-[10px] text-primary-500 hover:text-primary-700 font-medium flex items-center gap-0.5">
          <Plus className="w-3 h-3" />Ajouter
        </button>
      </div>
      {thresholds.length === 0 && (
        <p className="text-[10px] text-gray-400 italic">Aucun seuil. La couleur par defaut sera utilisee.</p>
      )}
      <div className="space-y-2">
        {thresholds.map((t, i) => (
          <div key={i} className="flex items-center gap-2">
            <span className="text-[10px] text-gray-500 w-6">{'>='}</span>
            <input type="number" value={t.value} onChange={e => updateThreshold(i, 'value', e.target.value)}
              className="w-20 px-2 py-1 text-xs border border-primary-300 dark:border-primary-600 rounded dark:bg-gray-700 dark:text-white" />
            <input type="color" value={t.color} onChange={e => updateThreshold(i, 'color', e.target.value)}
              className="w-7 h-7 rounded cursor-pointer border border-primary-300 dark:border-primary-600" />
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: t.color }} />
            <button onClick={() => removeThreshold(i)} className="p-0.5 hover:bg-red-100 dark:hover:bg-red-900/30 rounded">
              <X className="w-3 h-3 text-red-400" />
            </button>
          </div>
        ))}
      </div>
      {thresholds.length > 0 && (
        <p className="text-[10px] text-gray-400 mt-1 leading-tight">
          Ex: {'>='} 80 = vert, {'>='} 50 = orange, {'>='} 0 = rouge
        </p>
      )}
    </div>
  )
}
