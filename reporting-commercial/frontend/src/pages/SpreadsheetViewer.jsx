import { useState, useEffect, useCallback, useRef } from 'react'
import { useParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useGlobalFilters } from '../context/GlobalFilterContext'
import {
  getSpreadsheet, getSpreadsheetData,
  getSpreadsheetUserState, saveSpreadsheetUserState, resetSpreadsheetUserState,
  exportSpreadsheet, downloadBlob, importSpreadsheetExcel
} from '../services/api'
import {
  RefreshCw, Save, Download, RotateCcw, Loader2, FileSpreadsheet,
  AlertCircle, Upload, BarChart3, Table2, TrendingUp, TrendingDown,
  Hash, ChevronDown
} from 'lucide-react'
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts'
import { Workbook } from '@fortune-sheet/react'
import '@fortune-sheet/react/dist/index.css'

const CHART_COLORS = ['#4472C4', '#ED7D31', '#70AD47', '#FFC000', '#5B9BD5', '#A5A5A5', '#264478', '#9B59B6', '#E74C3C', '#1ABC9C']

function KpiCard({ label, value, icon: Icon, color, subtitle }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-3 flex items-center gap-3 min-w-0">
      <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${color}`}>
        <Icon size={18} className="text-white" />
      </div>
      <div className="min-w-0">
        <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{label}</p>
        <p className="text-base font-bold text-gray-800 dark:text-gray-100 truncate">{value}</p>
        {subtitle && <p className="text-[10px] text-gray-400 truncate">{subtitle}</p>}
      </div>
    </div>
  )
}

function formatNum(n) {
  if (n == null || isNaN(n)) return '—'
  if (Math.abs(n) >= 1_000_000) return (n / 1_000_000).toFixed(1) + ' M'
  if (Math.abs(n) >= 1_000) return (n / 1_000).toFixed(1) + ' K'
  return n.toLocaleString('fr-FR', { maximumFractionDigits: 2 })
}

export default function SpreadsheetViewer() {
  const { id } = useParams()
  const { user } = useAuth()
  const { filters: globalFilters } = useGlobalFilters()

  const [config, setConfig] = useState(null)
  const [sheetData, setSheetData] = useState(null)
  const [sheetsMetadata, setSheetsMetadata] = useState([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [error, setError] = useState(null)
  const [hasUserState, setHasUserState] = useState(false)
  const [workbookKey, setWorkbookKey] = useState(0)
  const [importing, setImporting] = useState(false)
  const [viewMode, setViewMode] = useState('dashboard')
  const [activeChartSheet, setActiveChartSheet] = useState(0)
  const [chartType, setChartType] = useState('bar')

  const saveTimerRef = useRef(null)
  const currentSheetsRef = useRef(null)
  const fileInputRef = useRef(null)

  const buildContext = useCallback(() => ({
    dateDebut: globalFilters?.dateDebut,
    dateFin: globalFilters?.dateFin,
    societe: globalFilters?.societe,
  }), [globalFilters])

  useEffect(() => {
    if (id) loadAll()
    return () => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current)
    }
  }, [id])

  const loadAll = async () => {
    setLoading(true)
    setError(null)
    try {
      const [configRes, dataRes, stateRes] = await Promise.all([
        getSpreadsheet(id),
        getSpreadsheetData(id, buildContext()),
        user?.id ? getSpreadsheetUserState(id, user.id) : Promise.resolve({ data: { data: null } }),
      ])

      if (!configRes.data?.success) throw new Error('Config introuvable')
      setConfig(configRes.data.data)

      const userState = stateRes.data?.data?.sheet_data
      setHasUserState(!!userState)

      if (dataRes.data?.success) {
        const apiSheets = dataRes.data.sheets || []
        setSheetsMetadata(apiSheets)
        if (userState && Array.isArray(userState) && userState.length > 0) {
          setSheetData(userState)
        } else {
          setSheetData(buildFortuneSheets(apiSheets))
        }
      }
    } catch (err) {
      console.error('Erreur chargement:', err)
      setError(err.response?.data?.detail || err.message || 'Erreur de chargement')
    } finally {
      setLoading(false)
    }
  }

  const buildFortuneSheets = (apiSheets) => {
    return apiSheets.map((s, i) => ({
      name: s.name || `Feuille ${i + 1}`,
      celldata: s.celldata || [],
      order: i,
      row: Math.max((s.row_count || 0) + 20, 80),
      column: Math.max((s.column_count || 0) + 10, 26),
      config: s.config || {},
      status: i === 0 ? 1 : 0,
    }))
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    setError(null)
    try {
      const dataRes = await getSpreadsheetData(id, buildContext())
      if (dataRes.data?.success) {
        const apiSheets = dataRes.data.sheets || []
        setSheetsMetadata(apiSheets)
        setSheetData(buildFortuneSheets(apiSheets))
        setWorkbookKey(k => k + 1)
        setHasUserState(false)
      }
    } catch (err) {
      setError('Erreur rafraichissement: ' + (err.message || ''))
    } finally {
      setRefreshing(false)
    }
  }

  const handleSave = async () => {
    if (!user?.id || !currentSheetsRef.current) return
    setSaving(true)
    try {
      await saveSpreadsheetUserState(id, user.id, { sheet_data: currentSheetsRef.current })
      setHasUserState(true)
    } catch (err) {
      setError('Erreur sauvegarde')
    } finally {
      setSaving(false)
    }
  }

  const handleReset = async () => {
    if (!user?.id) return
    if (!window.confirm('Reinitialiser vos modifications ?')) return
    try {
      await resetSpreadsheetUserState(id, user.id)
      setHasUserState(false)
      await handleRefresh()
    } catch (err) {
      setError('Erreur reinitialisation')
    }
  }

  const handleExport = async () => {
    setExporting(true)
    try {
      const res = await exportSpreadsheet(id, buildContext())
      const filename = (config?.nom || 'spreadsheet').replace(/[^\w\s-]/g, '') + '.xlsx'
      downloadBlob(res.data, filename)
    } catch (err) {
      setError('Erreur export')
    } finally {
      setExporting(false)
    }
  }

  const handleChange = useCallback((data) => {
    currentSheetsRef.current = data
  }, [])

  const handleImportExcel = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    e.target.value = ''
    setImporting(true)
    setError(null)
    try {
      const res = await importSpreadsheetExcel(file)
      if (res.data?.success) {
        const fortuneSheets = (res.data.sheets || []).map((s, i) => ({
          name: s.name || `Feuille ${i + 1}`,
          celldata: s.celldata || [],
          order: i,
          row: Math.max((s.row_count || 0) + 20, 80),
          column: Math.max((s.column_count || 0) + 10, 26),
          config: s.config || {},
          status: i === 0 ? 1 : 0,
        }))
        setSheetData(fortuneSheets)
        setWorkbookKey(k => k + 1)
      }
    } catch (err) {
      setError('Erreur import: ' + (err.response?.data?.detail || err.message))
    } finally {
      setImporting(false)
    }
  }

  const currentMeta = sheetsMetadata[activeChartSheet]
  const allStats = sheetsMetadata.flatMap(s => Object.values(s.stats || {}))
  const topKpis = allStats.sort((a, b) => Math.abs(b.sum) - Math.abs(a.sum)).slice(0, 4)

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-50 dark:bg-gray-900">
        <div className="text-center">
          <Loader2 className="w-10 h-10 animate-spin text-primary-500 mx-auto mb-3" />
          <p className="text-sm text-gray-500">Chargement du classeur...</p>
        </div>
      </div>
    )
  }

  if (error && !sheetData) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-50 dark:bg-gray-900">
        <div className="text-center max-w-md">
          <AlertCircle className="w-10 h-10 text-red-400 mx-auto mb-3" />
          <p className="text-sm text-red-600 dark:text-red-400 mb-4">{error}</p>
          <button onClick={loadAll}
            className="px-4 py-2 text-sm bg-primary-600 text-white rounded-xl hover:bg-primary-700 transition-colors">
            Reessayer
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full bg-gray-50 dark:bg-gray-900">
      {/* Toolbar */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-4 py-2 flex items-center gap-3">
        <div className="flex items-center gap-2">
          <FileSpreadsheet size={18} className="text-primary-500" />
          <h1 className="text-sm font-semibold text-gray-800 dark:text-gray-200 truncate max-w-xs">
            {config?.nom || 'Classeur'}
          </h1>
        </div>

        {/* View mode toggle */}
        <div className="flex bg-gray-100 dark:bg-gray-700 rounded-lg p-0.5 ml-2">
          <button onClick={() => setViewMode('dashboard')}
            className={`flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium transition-colors
              ${viewMode === 'dashboard' ? 'bg-white dark:bg-gray-600 text-primary-700 dark:text-primary-300 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}>
            <BarChart3 size={12} /> Dashboard
          </button>
          <button onClick={() => setViewMode('spreadsheet')}
            className={`flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium transition-colors
              ${viewMode === 'spreadsheet' ? 'bg-white dark:bg-gray-600 text-primary-700 dark:text-primary-300 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}>
            <Table2 size={12} /> Tableur
          </button>
        </div>

        <div className="flex-1" />

        {error && <span className="text-xs text-red-500 mr-2">{error}</span>}

        {hasUserState && (
          <span className="text-xs bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400 px-2 py-0.5 rounded-full">
            Modifications sauvegardees
          </span>
        )}

        <button onClick={handleRefresh} disabled={refreshing}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-40 transition-colors">
          <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
          Rafraichir
        </button>

        <button onClick={handleSave} disabled={saving}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300 hover:bg-primary-100 dark:hover:bg-primary-900/40 disabled:opacity-40 transition-colors">
          {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
          Sauvegarder
        </button>

        {hasUserState && (
          <button onClick={handleReset}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            title="Reinitialiser">
            <RotateCcw size={14} />
          </button>
        )}

        <input ref={fileInputRef} type="file" accept=".xlsx,.xls" onChange={handleImportExcel} className="hidden" />
        <button onClick={() => fileInputRef.current?.click()} disabled={importing}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300 hover:bg-amber-100 dark:hover:bg-amber-900/40 disabled:opacity-40 transition-colors">
          {importing ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />}
          Ouvrir Excel
        </button>

        <button onClick={handleExport} disabled={exporting}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300 hover:bg-emerald-100 dark:hover:bg-emerald-900/40 disabled:opacity-40 transition-colors">
          {exporting ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
          Excel
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden flex flex-col">
        {viewMode === 'dashboard' && sheetsMetadata.length > 0 && (
          <div className="overflow-auto p-4 space-y-4" style={{ maxHeight: '100%' }}>
            {/* KPI Cards */}
            {topKpis.length > 0 && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {topKpis.map((kpi, i) => (
                  <KpiCard
                    key={i}
                    label={kpi.label}
                    value={formatNum(kpi.sum)}
                    icon={i === 0 ? TrendingUp : i === 1 ? Hash : i === 2 ? TrendingDown : BarChart3}
                    color={['bg-blue-500', 'bg-emerald-500', 'bg-orange-500', 'bg-violet-500'][i]}
                    subtitle={`Moy: ${formatNum(kpi.avg)} | ${kpi.count} lignes`}
                  />
                ))}
              </div>
            )}

            {/* Sheet selector + chart type */}
            <div className="flex items-center gap-3 flex-wrap">
              <div className="flex bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-0.5 gap-0.5">
                {sheetsMetadata.map((s, i) => (
                  <button key={i} onClick={() => setActiveChartSheet(i)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors
                      ${activeChartSheet === i ? 'bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300' : 'text-gray-500 hover:bg-gray-50 dark:hover:bg-gray-700'}`}>
                    {s.name}
                  </button>
                ))}
              </div>
              <div className="flex bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-0.5 gap-0.5">
                {[
                  { id: 'bar', label: 'Barres' },
                  { id: 'line', label: 'Lignes' },
                  { id: 'pie', label: 'Camembert' },
                ].map(ct => (
                  <button key={ct.id} onClick={() => setChartType(ct.id)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors
                      ${chartType === ct.id ? 'bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300' : 'text-gray-500 hover:bg-gray-50 dark:hover:bg-gray-700'}`}>
                    {ct.label}
                  </button>
                ))}
              </div>
              {currentMeta && (
                <span className="text-xs text-gray-400">
                  {currentMeta.row_count} lignes | {currentMeta.column_count || currentMeta.headers?.length || '?'} colonnes
                </span>
              )}
            </div>

            {/* Chart */}
            {currentMeta?.chart_data?.length > 0 && (
              <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 p-4">
                <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-3">
                  {currentMeta.name}
                </h3>
                <div style={{ height: 340 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    {chartType === 'bar' ? (
                      <BarChart data={currentMeta.chart_data} margin={{ top: 5, right: 20, bottom: 60, left: 20 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
                        <XAxis dataKey="name" angle={-35} textAnchor="end" tick={{ fontSize: 10 }} interval={0} />
                        <YAxis tick={{ fontSize: 10 }} tickFormatter={formatNum} />
                        <Tooltip formatter={(v) => formatNum(v)} />
                        <Legend wrapperStyle={{ fontSize: 11 }} />
                        {(currentMeta.numeric_cols || []).slice(0, 4).map((col, i) => {
                          const label = currentMeta.stats?.[col]?.label || col
                          return <Bar key={col} dataKey={col} name={label} fill={CHART_COLORS[i]} radius={[4, 4, 0, 0]} />
                        })}
                      </BarChart>
                    ) : chartType === 'line' ? (
                      <LineChart data={currentMeta.chart_data} margin={{ top: 5, right: 20, bottom: 60, left: 20 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
                        <XAxis dataKey="name" angle={-35} textAnchor="end" tick={{ fontSize: 10 }} interval={0} />
                        <YAxis tick={{ fontSize: 10 }} tickFormatter={formatNum} />
                        <Tooltip formatter={(v) => formatNum(v)} />
                        <Legend wrapperStyle={{ fontSize: 11 }} />
                        {(currentMeta.numeric_cols || []).slice(0, 4).map((col, i) => {
                          const label = currentMeta.stats?.[col]?.label || col
                          return <Line key={col} type="monotone" dataKey={col} name={label} stroke={CHART_COLORS[i]} strokeWidth={2} dot={{ r: 3 }} />
                        })}
                      </LineChart>
                    ) : (
                      <PieChart>
                        <Pie
                          data={currentMeta.chart_data.slice(0, 10).map((d, i) => ({
                            name: d.name,
                            value: d[currentMeta.numeric_cols?.[0]] || 0,
                          }))}
                          cx="50%" cy="50%"
                          outerRadius={120}
                          innerRadius={50}
                          dataKey="value"
                          label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                          labelLine={{ strokeWidth: 1 }}
                        >
                          {currentMeta.chart_data.slice(0, 10).map((_, i) => (
                            <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip formatter={(v) => formatNum(v)} />
                      </PieChart>
                    )}
                  </ResponsiveContainer>
                </div>
              </div>
            )}

            {/* Stats table per sheet */}
            {currentMeta?.stats && Object.keys(currentMeta.stats).length > 0 && (
              <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 p-4">
                <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-3">
                  Statistiques — {currentMeta.name}
                </h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="bg-gray-50 dark:bg-gray-900">
                        <th className="px-3 py-2 text-left font-medium text-gray-500">Indicateur</th>
                        <th className="px-3 py-2 text-right font-medium text-gray-500">Somme</th>
                        <th className="px-3 py-2 text-right font-medium text-gray-500">Moyenne</th>
                        <th className="px-3 py-2 text-right font-medium text-gray-500">Min</th>
                        <th className="px-3 py-2 text-right font-medium text-gray-500">Max</th>
                        <th className="px-3 py-2 text-right font-medium text-gray-500">Nb</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                      {Object.entries(currentMeta.stats).map(([key, st]) => (
                        <tr key={key} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                          <td className="px-3 py-2 font-medium text-gray-700 dark:text-gray-300">{st.label}</td>
                          <td className="px-3 py-2 text-right font-mono text-gray-800 dark:text-gray-200">{formatNum(st.sum)}</td>
                          <td className="px-3 py-2 text-right font-mono text-gray-600 dark:text-gray-400">{formatNum(st.avg)}</td>
                          <td className="px-3 py-2 text-right font-mono text-gray-600 dark:text-gray-400">{formatNum(st.min)}</td>
                          <td className="px-3 py-2 text-right font-mono text-gray-600 dark:text-gray-400">{formatNum(st.max)}</td>
                          <td className="px-3 py-2 text-right text-gray-500">{st.count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Quick access to spreadsheet */}
            <div className="text-center py-2">
              <button onClick={() => setViewMode('spreadsheet')}
                className="text-xs text-primary-600 dark:text-primary-400 hover:underline flex items-center gap-1 mx-auto">
                <Table2 size={12} /> Voir les donnees dans le tableur
              </button>
            </div>
          </div>
        )}

        {(viewMode === 'spreadsheet' || sheetsMetadata.length === 0) && (
          <div className="flex-1 overflow-hidden">
            {sheetData && sheetData.length > 0 ? (
              <Workbook key={workbookKey} data={sheetData} onChange={handleChange} />
            ) : (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <FileSpreadsheet className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                  <p className="text-sm text-gray-500">Aucune donnee disponible</p>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
