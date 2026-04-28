import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ChevronRight, Search, Star, X,
  TrendingUp, TrendingDown, Minus, Clock, History,
  Folder, FolderOpen, Table2, LayoutDashboard, FileSpreadsheet,
  ShoppingCart, BarChart3, Wallet, Package, Users, LayoutGrid,
  Table, Settings, Database, Mail,
  FileText, Receipt, ClipboardList, FileQuestion, PackageCheck,
  Truck, Boxes, RotateCcw, Repeat, ArrowUpDown, ArrowRightLeft,
  TrendingUp as TUp, TrendingDown as TDown, PieChart, BarChart2, LineChart, Activity,
  DollarSign, CircleDollarSign, CreditCard, BadgePercent, Percent, Scale,
  Target, Crosshair, ShoppingBag, Award,
  UserCheck, UserX, User,
  MapPin, Layers, AlertTriangle, Zap, GitCompare, Filter, Gauge,
  Link as LinkIcon, PanelTop,
  Zap as ZapIcon, Pin, PinOff, ChevronDown, Pencil, Check,
} from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { useGlobalFilters } from '../../context/GlobalFilterContext'
import { useDWH } from '../../context/DWHContext'
import { getDashboard, getEvolutionMensuelle, getComparatifAnnuel } from '../../services/api'
import api from '../../services/api'
import { withCache, cacheAge, formatCacheAge } from '../../services/apiCache'
import MobileDWHSheet from '../../components/mobile/MobileDWHSheet'
import { CacheIndicator } from '../../components/mobile/MobileNetworkBanner'

// ─── Filtre date rapide ───────────────────────────────────────────────────────
function DateFilterStrip() {
  const { filters, setCurrentMonth, setCurrentYear, setPreviousYear } = useGlobalFilters()
  const today = new Date()
  const curYear = today.getFullYear()
  const curMonth = String(today.getMonth() + 1).padStart(2, '0')
  const monthStart = `${curYear}-${curMonth}-01`

  const active = (() => {
    const d = filters.dateDebut, f = filters.dateFin
    if (d === monthStart) return 'month'
    if (d === `${curYear}-01-01` && f >= `${curYear}-12-30`) return 'year'
    if (d === `${curYear - 1}-01-01` && f >= `${curYear - 1}-12-30`) return 'prev'
    return null
  })()

  const btn = (label, key, onClick) => (
    <button key={key} onClick={onClick}
      className={`flex-shrink-0 px-3 py-1.5 rounded-full text-xs font-semibold transition-colors ${
        active === key
          ? 'bg-primary-600 text-white'
          : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-gray-700'
      }`}
    >{label}</button>
  )
  return (
    <div className="px-3 pb-2">
      <div className="flex gap-2 overflow-x-auto scrollbar-hide pb-0.5">
        {btn('Ce mois', 'month', setCurrentMonth)}
        {btn('Cette année', 'year', setCurrentYear)}
        {btn('Année préc.', 'prev', setPreviousYear)}
      </div>
    </div>
  )
}

// ─── Icônes ───────────────────────────────────────────────────────────────────
const ICON_MAP = {
  Folder, FolderOpen, Table2, LayoutDashboard, FileSpreadsheet, LinkIcon,
  ShoppingCart, BarChart3, Wallet, Package, Users, LayoutGrid,
  Table, PanelTop, Settings, Database, Mail,
  FileText, Receipt, ClipboardList, FileQuestion, PackageCheck,
  Truck, Boxes, RotateCcw, Repeat, ArrowUpDown, ArrowRightLeft,
  TrendingUp: TUp, TrendingDown: TDown, PieChart, BarChart2, LineChart, Activity,
  DollarSign, CircleDollarSign, CreditCard, BadgePercent, Percent, Scale,
  Target, Crosshair, ShoppingBag, Star, Award,
  UserCheck, UserX, User,
  MapPin, Layers, AlertTriangle, Zap, Clock, GitCompare, Filter, Gauge,
}
const getIcon = (name) => ICON_MAP[name] || Folder

// ─── Types ────────────────────────────────────────────────────────────────────
const TYPE_COLORS = {
  dashboard:  'text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-900/20',
  gridview:   'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20',
  pivot:      'text-purple-600 dark:text-purple-400 bg-purple-50 dark:bg-purple-900/20',
  'pivot-v2': 'text-purple-600 dark:text-purple-400 bg-purple-50 dark:bg-purple-900/20',
  folder:     'text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-800',
  page:       'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20',
}
const TYPE_LABELS = { dashboard: 'Dashboard', gridview: 'Grid', pivot: 'Pivot', 'pivot-v2': 'Pivot', page: 'Page' }
const TYPE_BADGE = {
  dashboard:  'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300',
  gridview:   'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300',
  pivot:      'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300',
  'pivot-v2': 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300',
  page:       'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300',
}

function getUrl(menu) {
  if (menu.type === 'dashboard' && menu.target_id) return `/view/${menu.target_id}`
  if (menu.type === 'gridview' && menu.target_id) return `/grid/${menu.target_id}`
  if ((menu.type === 'pivot' || menu.type === 'pivot-v2') && menu.target_id) return `/pivot-v2/${menu.target_id}`
  if (menu.type === 'page' && menu.url) return menu.url
  return null
}

function flattenMenus(menus, result = []) {
  for (const m of menus) {
    if (m.children?.length) flattenMenus(m.children, result)
    else { const url = getUrl(m); if (url) result.push(m) }
  }
  return result
}

// ─── Highlight ────────────────────────────────────────────────────────────────
function Highlight({ text, query }) {
  if (!query) return <span>{text}</span>
  const idx = text.toLowerCase().indexOf(query.toLowerCase())
  if (idx === -1) return <span>{text}</span>
  return (
    <span>
      {text.slice(0, idx)}
      <mark className="bg-yellow-200 dark:bg-yellow-800/60 text-inherit rounded-sm not-italic">{text.slice(idx, idx + query.length)}</mark>
      {text.slice(idx + query.length)}
    </span>
  )
}

// ─── Sparkline SVG ────────────────────────────────────────────────────────────
function Sparkline({ values, color = '#3b82f6', width = 72, height = 28 }) {
  if (!values || values.length < 2) return null
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1
  const pad = 2
  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * width
    const y = height - pad - ((v - min) / range) * (height - pad * 2)
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
  const lastX = width
  const lastY = height - pad - ((values[values.length - 1] - min) / range) * (height - pad * 2)
  return (
    <svg width={width} height={height} className="overflow-visible flex-shrink-0">
      <polyline fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" points={pts} opacity="0.7" />
      <circle cx={lastX} cy={lastY} r="2.5" fill={color} />
    </svg>
  )
}

// ─── KPI Card avec sparkline ──────────────────────────────────────────────────
function KPICard({ label, value, evolution, tendance, sparkValues, sparkColor }) {
  const isUp = tendance === 'hausse'
  const isDown = tendance === 'baisse'
  const color = sparkColor || (isUp ? '#22c55e' : isDown ? '#ef4444' : '#3b82f6')
  return (
    <div className="flex-shrink-0 bg-white dark:bg-gray-800 rounded-2xl p-3.5 shadow-sm min-w-[150px]">
      <p className="text-xs text-gray-500 dark:text-gray-400 mb-1 truncate">{label}</p>
      <p className="text-base font-bold text-gray-900 dark:text-white truncate">{value || '—'}</p>
      <div className="flex items-end justify-between mt-1.5 gap-2">
        {evolution != null ? (
          <div className={`flex items-center gap-0.5 text-xs font-semibold ${isUp ? 'text-green-500' : isDown ? 'text-red-500' : 'text-gray-400'}`}>
            {isUp ? <TrendingUp className="w-3 h-3" /> : isDown ? <TrendingDown className="w-3 h-3" /> : <Minus className="w-3 h-3" />}
            {isUp ? '+' : ''}{typeof evolution === 'number' ? evolution.toFixed(1) : evolution}%
          </div>
        ) : <span />}
        <Sparkline values={sparkValues} color={color} />
      </div>
    </div>
  )
}

// ─── Widget objectif CA ───────────────────────────────────────────────────────
function ObjectifWidget({ comparatif }) {
  if (!comparatif || comparatif.length < 2) return null
  const n1 = comparatif.find(r => r.annee < new Date().getFullYear())
  const n  = comparatif.find(r => r.annee === new Date().getFullYear())
  if (!n || !n1 || !n1.ca_ht) return null

  const pct = Math.min((n.ca_ht / n1.ca_ht) * 100, 150)
  // % de l'année écoulée
  const today = new Date()
  const yearStart = new Date(today.getFullYear(), 0, 1)
  const yearEnd   = new Date(today.getFullYear(), 11, 31)
  const yearPct   = ((today - yearStart) / (yearEnd - yearStart)) * 100

  const isOnTrack = pct >= yearPct
  const barColor  = isOnTrack ? 'bg-green-500' : pct >= yearPct * 0.85 ? 'bg-amber-400' : 'bg-red-500'

  const fmt = (v) => {
    if (!v && v !== 0) return '—'
    if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(2)}M`
    if (v >= 1_000)     return `${(v / 1_000).toFixed(1)}K`
    return v.toFixed(0)
  }

  return (
    <div className="mx-3 mb-3 bg-white dark:bg-gray-800 rounded-2xl p-4 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Target className="w-4 h-4 text-primary-500" />
          <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Progression vs N-1</p>
        </div>
        <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${isOnTrack ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}`}>
          {isOnTrack ? 'En avance' : 'À surveiller'}
        </span>
      </div>

      {/* Barre */}
      <div className="relative h-3 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden mb-2">
        <div className={`h-full rounded-full transition-all duration-700 ${barColor}`} style={{ width: `${Math.min(pct, 100)}%` }} />
        {/* Marqueur "où on devrait être" */}
        <div
          className="absolute top-0 bottom-0 w-0.5 bg-gray-400 dark:bg-gray-500"
          style={{ left: `${yearPct}%` }}
          title={`Objectif à cette date: ${yearPct.toFixed(0)}%`}
        />
      </div>

      <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
        <span>CA {n.annee}: <strong className="text-gray-900 dark:text-white">{fmt(n.ca_ht)} MAD</strong></span>
        <span className={`font-bold ${isOnTrack ? 'text-green-600' : 'text-amber-600'}`}>{pct.toFixed(0)}% de N-1</span>
        <span>Réf: {fmt(n1.ca_ht)} MAD</span>
      </div>

      {/* Légende */}
      <div className="flex items-center gap-1.5 mt-2 text-[10px] text-gray-400">
        <div className="w-4 h-0.5 bg-gray-400" />
        <span>Attendu à ce jour ({yearPct.toFixed(0)}%)</span>
      </div>
    </div>
  )
}

// ─── Shortcuts grid ───────────────────────────────────────────────────────────
const MAX_SHORTCUTS = 6

function ShortcutGrid({ shortcuts, onNavigate, onRemove, editMode }) {
  if (shortcuts.length === 0 && !editMode) return null
  return (
    <div className="grid grid-cols-3 gap-2">
      {shortcuts.map((m) => {
        const IconComp = getIcon(m.icon)
        const colorClass = TYPE_COLORS[m.type] || TYPE_COLORS.folder
        const url = m.url || getUrl(m)
        return (
          <button
            key={m.url || m.id}
            onClick={() => !editMode && url && onNavigate(url)}
            className="relative flex flex-col items-center gap-1.5 bg-white dark:bg-gray-800 rounded-xl p-3 shadow-sm active:scale-95 transition-transform"
          >
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${colorClass}`}>
              <IconComp className="w-5 h-5" />
            </div>
            <span className="text-[11px] font-medium text-gray-700 dark:text-gray-300 text-center leading-tight line-clamp-2 w-full">
              {m.nom}
            </span>
            {editMode && (
              <button
                onClick={(e) => { e.stopPropagation(); onRemove(m) }}
                className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-red-500 text-white flex items-center justify-center shadow"
              >
                <X className="w-3 h-3" />
              </button>
            )}
          </button>
        )
      })}
    </div>
  )
}

// ─── Row rapport (favori, récent) ─────────────────────────────────────────────
function ReportRow({ menu, onNavigate, sub, pinned, onPin, showPin }) {
  const IconComp = getIcon(menu.icon)
  const colorClass = TYPE_COLORS[menu.type] || TYPE_COLORS.folder
  const url = menu.url || getUrl(menu)
  return (
    <button
      onClick={() => url && onNavigate(url)}
      className="flex items-center gap-3 bg-white dark:bg-gray-800 rounded-xl p-3 shadow-sm active:scale-[0.98] transition-transform w-full text-left"
    >
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${colorClass}`}>
        <IconComp className="w-4 h-4" />
      </div>
      <div className="flex-1 min-w-0">
        <span className="block text-sm font-medium text-gray-900 dark:text-white truncate">{menu.nom}</span>
        {sub && <span className="text-xs text-gray-400 truncate block">{sub}</span>}
      </div>
      {showPin && (
        <button
          onClick={(e) => { e.stopPropagation(); onPin?.(menu) }}
          className={`p-1 rounded-lg flex-shrink-0 transition-colors ${
            pinned
              ? 'text-primary-600 dark:text-primary-400'
              : 'text-gray-300 dark:text-gray-600 hover:text-primary-500'
          }`}
          title={pinned ? 'Retirer des raccourcis' : 'Épingler en raccourci'}
        >
          {pinned ? <Pin className="w-4 h-4" /> : <Pin className="w-4 h-4" />}
        </button>
      )}
    </button>
  )
}

// ─── Résultat de recherche ────────────────────────────────────────────────────
function SearchResult({ menu, onNavigate, query, onSelect }) {
  const IconComp = getIcon(menu.icon)
  const url = getUrl(menu)
  const badge = TYPE_BADGE[menu.type]
  const label = TYPE_LABELS[menu.type]
  return (
    <button
      onClick={() => { if (url) { onSelect?.(); onNavigate(url) } }}
      className="flex items-center gap-3 px-3 py-2.5 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700/50 active:bg-gray-100 w-full text-left transition-colors"
    >
      <IconComp className="w-4 h-4 flex-shrink-0" style={{ color: 'var(--color-primary-500)' }} />
      <span className="flex-1 font-medium truncate"><Highlight text={menu.nom} query={query} /></span>
      {badge && label && (
        <span className={`text-[10px] px-1.5 py-0.5 rounded font-semibold flex-shrink-0 ${badge}`}>{label}</span>
      )}
    </button>
  )
}

// ─── Page principale (Tableau de Bord) ───────────────────────────────────────
export default function MobileHomePage({ menus = [], recents = [] }) {
  const { user } = useAuth()
  const { filters } = useGlobalFilters()
  const { currentDWH, hasMultipleDWH } = useDWH()
  const navigate = useNavigate()
  const searchRef = useRef(null)

  const [favorites, setFavorites] = useState([])
  const [kpis, setKpis] = useState(null)
  const [evolutionData, setEvolutionData] = useState([])
  const [comparatif, setComparatif] = useState([])
  const [loading, setLoading] = useState(true)
  const [fromCache, setFromCache] = useState(false)
  const [dataCacheAge, setDataCacheAge] = useState(null)
  const [search, setSearch] = useState('')
  const [searchFocused, setSearchFocused] = useState(false)
  const [dwhSheetOpen, setDwhSheetOpen] = useState(false)

  // Historique recherche
  const HISTORY_KEY = `search_history_${user?.id}`
  const [searchHistory, setSearchHistory] = useState(() => {
    try { return JSON.parse(localStorage.getItem(HISTORY_KEY)) || [] } catch { return [] }
  })

  // Shortcuts (raccourcis épinglés)
  const SHORTCUTS_KEY = `shortcuts_${user?.id}`
  const [shortcuts, setShortcuts] = useState(() => {
    try { return JSON.parse(localStorage.getItem(`shortcuts_${user?.id}`)) || [] } catch { return [] }
  })
  const [shortcutEditMode, setShortcutEditMode] = useState(false)

  const saveToHistory = useCallback((term) => {
    const t = term.trim()
    if (!t || t.length < 2) return
    setSearchHistory(prev => {
      const updated = [t, ...prev.filter(h => h.toLowerCase() !== t.toLowerCase())].slice(0, 6)
      localStorage.setItem(HISTORY_KEY, JSON.stringify(updated))
      return updated
    })
  }, [HISTORY_KEY])

  const removeFromHistory = useCallback((term) => {
    setSearchHistory(prev => {
      const updated = prev.filter(h => h !== term)
      localStorage.setItem(HISTORY_KEY, JSON.stringify(updated))
      return updated
    })
  }, [HISTORY_KEY])

  const clearHistory = useCallback(() => {
    setSearchHistory([])
    localStorage.removeItem(HISTORY_KEY)
  }, [HISTORY_KEY])

  const toggleShortcut = useCallback((menu) => {
    const url = menu.url || getUrl(menu)
    setShortcuts(prev => {
      const exists = prev.some(s => s.url === url)
      const updated = exists
        ? prev.filter(s => s.url !== url)
        : prev.length >= MAX_SHORTCUTS
          ? prev
          : [...prev, { id: menu.id, nom: menu.nom, type: menu.type, icon: menu.icon, url }]
      localStorage.setItem(SHORTCUTS_KEY, JSON.stringify(updated))
      return updated
    })
  }, [SHORTCUTS_KEY])

  useEffect(() => {
    if (!user?.id) return
    const load = async () => {
      setLoading(true)
      setFromCache(false)
      try {
        const curYear = filters?.annee || new Date().getFullYear()
        const uid = user.id
        const [favResult, kpiResult, evolResult, compResult] = await Promise.all([
          withCache(`fav_${uid}`,         () => api.get('/favorites', { params: { user_id: uid } }), 30 * 60 * 1000),
          withCache(`kpi_${uid}_${curYear}`, () => getDashboard({ annee: curYear }), 60 * 60 * 1000),
          withCache(`evol_${uid}`,        () => getEvolutionMensuelle({ periode: 'annee_courante' }), 60 * 60 * 1000),
          withCache(`comp_${uid}_${curYear}`, () => getComparatifAnnuel(curYear), 60 * 60 * 1000),
        ])

        const anyFromCache = [favResult, kpiResult, evolResult, compResult].some(r => r.fromCache)
        setFromCache(anyFromCache)
        if (anyFromCache) setDataCacheAge(formatCacheAge(cacheAge(`kpi_${uid}_${curYear}`)))

        setFavorites(favResult.data?.data || favResult.data || [])
        const kpiData = kpiResult.data
        if (kpiData?.kpis) setKpis(kpiData.kpis)
        const evolData = evolResult.data
        if (evolData?.data) setEvolutionData(evolData.data)
        const compData = compResult.data
        if (compData?.data) setComparatif(compData.data)
      } catch (e) {
        console.error('Erreur chargement mobile home:', e)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [user?.id, filters?.annee])

  const handleNavigate = (url) => navigate(url)
  const allLeaves = flattenMenus(menus)

  // Recherche
  const searchResults = search.trim().length > 1
    ? allLeaves.filter(m => m.nom?.toLowerCase().includes(search.toLowerCase()))
    : []

  // Favoris
  const favTypeMap = { dashboard: 'dashboard', gridview: 'gridview', 'pivot-v2': 'pivot', pivot: 'pivot' }
  const favLeaves = favorites.length > 0
    ? allLeaves.filter(m => favorites.some(f =>
        f.report_type === (favTypeMap[m.type] || m.type) && f.report_id === m.target_id))
    : []

  // Sparkline values depuis evolution mensuelle
  const caValues    = evolutionData.slice(-6).map(r => r.ca_ht || 0)
  const margeValues = evolutionData.slice(-6).map(r => r.marge_brute || 0)

  // KPI Cards
  const kpiCards = kpis ? [
    { label: 'Chiffre d\'Affaires', value: kpis.ca_ht?.formatted_value, evolution: kpis.ca_ht?.evolution, tendance: kpis.ca_ht?.tendance, sparkValues: caValues },
    { label: 'Marge Brute',         value: kpis.marge_brute?.formatted_value, evolution: kpis.marge_brute?.evolution, tendance: kpis.marge_brute?.tendance, sparkValues: margeValues },
    { label: 'DSO (jours)',         value: kpis.dso?.formatted_value, evolution: kpis.dso?.evolution, tendance: kpis.dso?.tendance },
    { label: 'Rotation Stock',      value: kpis.rotation_stock?.formatted_value, evolution: kpis.rotation_stock?.evolution, tendance: kpis.rotation_stock?.tendance },
  ].filter(k => k.value) : []

  return (
    <div className="flex flex-col min-h-full bg-gray-50 dark:bg-gray-900 relative">

      {/* ── Barre de recherche ────────────────────────── */}
      <div className="px-3 pt-3 pb-2 relative">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            ref={searchRef}
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            onFocus={() => setSearchFocused(true)}
            onBlur={() => setTimeout(() => setSearchFocused(false), 150)}
            onKeyDown={e => { if (e.key === 'Enter' && search.trim().length > 1) saveToHistory(search) }}
            placeholder="Rechercher un rapport..."
            className="w-full h-10 pl-9 pr-9 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
          {search && (
            <button onClick={() => { setSearch(''); searchRef.current?.focus() }} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Historique de recherche */}
        {searchFocused && !search && searchHistory.length > 0 && (
          <div className="absolute left-3 right-3 z-30 mt-1 bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
            <div className="flex items-center justify-between px-3 pt-2 pb-1">
              <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Recherches récentes</span>
              <button onClick={clearHistory} className="text-xs text-primary-500 hover:text-primary-700">Effacer</button>
            </div>
            {searchHistory.map(h => (
              <div key={h} className="flex items-center group">
                <button onMouseDown={() => setSearch(h)}
                  className="flex items-center gap-2.5 flex-1 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700/50 text-left">
                  <History className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
                  <span className="truncate">{h}</span>
                </button>
                <button onMouseDown={() => removeFromHistory(h)} className="pr-3 text-gray-300 hover:text-gray-500">
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Filtre date rapide ────────────────────────── */}
      <DateFilterStrip />

      {/* ── Indicateur données en cache ──────────────── */}
      <CacheIndicator fromCache={fromCache} cacheAge={dataCacheAge} />

      {/* ── Sélecteur DWH ────────────────────────────── */}
      {hasMultipleDWH && (
        <div className="px-3 pb-2">
          <button
            onClick={() => setDwhSheetOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-white dark:bg-gray-800 rounded-full border border-gray-200 dark:border-gray-700 shadow-sm text-xs font-semibold text-gray-700 dark:text-gray-300 active:bg-gray-50"
          >
            <Database className="w-3.5 h-3.5 text-primary-500" />
            <span className="max-w-[140px] truncate">{currentDWH?.nom || 'Base active'}</span>
            <ChevronDown className="w-3 h-3 text-gray-400" />
          </button>
        </div>
      )}

      {/* ── Résultats de recherche ──────────────────── */}
      {search.trim().length > 1 ? (
        <div className="mx-3 bg-white dark:bg-gray-800 rounded-2xl shadow-sm overflow-hidden">
          {searchResults.length === 0 ? (
            <p className="py-8 text-center text-sm text-gray-400">Aucun résultat pour « {search} »</p>
          ) : (
            <>
              <p className="text-xs text-gray-400 px-3 pt-2 pb-1">{searchResults.length} résultat{searchResults.length > 1 ? 's' : ''}</p>
              <div className="divide-y divide-gray-100 dark:divide-gray-700/50">
                {searchResults.map(m => (
                  <SearchResult key={m.id} menu={m} query={search} onNavigate={handleNavigate} onSelect={() => saveToHistory(search)} />
                ))}
              </div>
            </>
          )}
        </div>
      ) : loading ? (
        <div className="flex-1 flex items-center justify-center py-16">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
        </div>
      ) : (
        <>
          {/* ── KPI Cards avec sparklines ───────────────── */}
          {kpiCards.length > 0 && (
            <div className="px-3 pb-2">
              <p className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wide mb-2">Indicateurs clés</p>
              <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
                {kpiCards.map(k => <KPICard key={k.label} {...k} />)}
              </div>
            </div>
          )}

          {/* ── Widget objectif ─────────────────────────── */}
          <ObjectifWidget comparatif={comparatif} />

          {/* ── Accès rapide (Shortcuts) ────────────────── */}
          {(shortcuts.length > 0) && (
            <div className="px-3 pb-3">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-1.5">
                  <ZapIcon className="w-3.5 h-3.5 text-amber-400" />
                  <p className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wide">Accès rapide</p>
                </div>
                <button
                  onClick={() => setShortcutEditMode(e => !e)}
                  className={`flex items-center gap-1 text-xs px-2 py-0.5 rounded-full transition-colors ${
                    shortcutEditMode
                      ? 'bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300'
                      : 'text-gray-400 hover:text-gray-600'
                  }`}
                >
                  {shortcutEditMode ? <><Check className="w-3 h-3" /> Terminer</> : <><Pencil className="w-3 h-3" /> Modifier</>}
                </button>
              </div>
              <ShortcutGrid
                shortcuts={shortcuts}
                onNavigate={handleNavigate}
                onRemove={toggleShortcut}
                editMode={shortcutEditMode}
              />
            </div>
          )}

          {/* ── Favoris ────────────────────────────────── */}
          {favLeaves.length > 0 && (
            <div className="px-3 pb-3">
              <div className="flex items-center gap-1.5 mb-2">
                <Star className="w-3.5 h-3.5 text-amber-500" />
                <p className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wide">Favoris</p>
                {shortcuts.length < MAX_SHORTCUTS && (
                  <span className="ml-auto text-[10px] text-gray-400">Cliquer <Pin className="w-2.5 h-2.5 inline" /> pour épingler</span>
                )}
              </div>
              <div className="flex flex-col gap-2">
                {favLeaves.map(m => {
                  const url = getUrl(m)
                  const isPinned = shortcuts.some(s => s.url === url)
                  return (
                    <ReportRow
                      key={m.id}
                      menu={m}
                      onNavigate={handleNavigate}
                      pinned={isPinned}
                      showPin={shortcuts.length < MAX_SHORTCUTS || isPinned}
                      onPin={toggleShortcut}
                    />
                  )
                })}
              </div>
            </div>
          )}

          {/* ── Récents ────────────────────────────────── */}
          {recents.length > 0 && (
            <div className="px-3 pb-4">
              <div className="flex items-center gap-1.5 mb-2">
                <Clock className="w-3.5 h-3.5 text-blue-400" />
                <p className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wide">Consultés récemment</p>
              </div>
              <div className="flex flex-col gap-2">
                {recents.map((m, i) => {
                  const isPinned = shortcuts.some(s => s.url === m.url)
                  return (
                    <ReportRow
                      key={`${m.url}-${i}`}
                      menu={m}
                      onNavigate={handleNavigate}
                      sub={m.visitedAt ? new Date(m.visitedAt).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : undefined}
                      pinned={isPinned}
                      showPin={shortcuts.length < MAX_SHORTCUTS || isPinned}
                      onPin={toggleShortcut}
                    />
                  )
                })}
              </div>
            </div>
          )}
        </>
      )}

      {/* ── Bottom sheet DWH ─────────────────────────── */}
      <MobileDWHSheet open={dwhSheetOpen} onClose={() => setDwhSheetOpen(false)} />
    </div>
  )
}
