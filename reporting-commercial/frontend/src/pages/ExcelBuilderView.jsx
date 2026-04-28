import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import {
  Download, ArrowLeft, RefreshCw, Loader2, AlertCircle,
  FileSpreadsheet, ChevronDown, ChevronRight, Calendar,
  Settings2
} from 'lucide-react'
import {
  getExcelBuilder,
  executeExcelBuilder,
  exportExcelBuilder,
} from '../services/api'

const MONTHS = ['janv', 'févr', 'mars', 'avr', 'mai', 'juin', 'juil', 'août', 'sept', 'oct', 'nov', 'déc']

function formatNumber(val) {
  if (val === null || val === undefined || val === '') return '-'
  const n = Number(val)
  if (isNaN(n)) return '-'
  return n.toLocaleString('fr-FR', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
}

export default function ExcelBuilderView() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const { darkMode } = useTheme()

  const [builder, setBuilder] = useState(null)
  const [config, setConfig] = useState(null)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [executing, setExecuting] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [error, setError] = useState(null)
  const [year, setYear] = useState(new Date().getFullYear())
  const [collapsedSections, setCollapsedSections] = useState({})

  const YEARS = Array.from({ length: 7 }, (_, i) => 2020 + i)

  const loadBuilder = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const res = await getExcelBuilder(id)
      if (res.data?.success) {
        const b = res.data.data
        setBuilder(b)
        const cfg = typeof b.config === 'string' ? JSON.parse(b.config) : b.config
        setConfig(cfg)
        if (cfg?.year) setYear(cfg.year)
      } else {
        setError('Builder introuvable')
      }
    } catch (e) {
      setError('Erreur de chargement : ' + (e.message || e))
    } finally {
      setLoading(false)
    }
  }, [id])

  const executeBuilder = useCallback(async (selectedYear) => {
    if (!id) return
    try {
      setExecuting(true)
      setError(null)
      const res = await executeExcelBuilder(id, { context: { year: selectedYear } })
      if (res.data?.success) {
        setData(res.data)
      } else {
        setError('Erreur exécution : ' + (res.data?.error || 'inconnu'))
      }
    } catch (e) {
      setError('Erreur exécution : ' + (e.message || e))
    } finally {
      setExecuting(false)
    }
  }, [id])

  useEffect(() => { loadBuilder() }, [loadBuilder])

  useEffect(() => {
    if (config) executeBuilder(year)
  }, [config, year, executeBuilder])

  const handleExport = async () => {
    try {
      setExporting(true)
      const blob = await exportExcelBuilder(id, { context: { year } })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${builder?.name || 'rapport'}_${year}.xlsx`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      setError('Erreur export : ' + (e.message || e))
    } finally {
      setExporting(false)
    }
  }

  const toggleSection = (idx) => {
    setCollapsedSections(prev => ({ ...prev, [idx]: !prev[idx] }))
  }

  const activeMonths = config?.months || MONTHS

  // ── Colonne TOTAL depuis data ou calculée ──
  const getRowTotal = (values) => {
    if (!values) return 0
    return values.reduce((sum, v) => sum + (Number(v) || 0), 0)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full min-h-[400px]">
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    )
  }

  if (error && !builder) {
    return (
      <div className="flex flex-col items-center justify-center h-full min-h-[400px] gap-4">
        <AlertCircle className="w-12 h-12 text-red-500" />
        <p className="text-red-600 dark:text-red-400">{error}</p>
        <button onClick={() => navigate('/excel-builder')}
          className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700">
          Retour
        </button>
      </div>
    )
  }

  const sections = data?.sections || config?.sections || []
  const columns = data?.columns || activeMonths

  return (
    <div className="flex flex-col h-full bg-gray-50 dark:bg-gray-900">
      {/* ── Topbar ── */}
      <div className="flex items-center justify-between px-4 py-3 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 shadow-sm flex-shrink-0">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/excel-builder')}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors">
            <ArrowLeft className="w-4 h-4 text-gray-600 dark:text-gray-400" />
          </button>
          <FileSpreadsheet className="w-5 h-5 text-green-600" />
          <div>
            <h1 className="font-semibold text-gray-900 dark:text-white text-sm leading-tight">
              {builder?.name || 'Excel Builder'}
            </h1>
            {builder?.description && (
              <p className="text-xs text-gray-500 dark:text-gray-400">{builder.description}</p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Sélecteur d'année */}
          <div className="flex items-center gap-1 bg-gray-100 dark:bg-gray-700 rounded-lg px-2 py-1">
            <Calendar className="w-3.5 h-3.5 text-gray-500" />
            <select
              value={year}
              onChange={e => setYear(Number(e.target.value))}
              className="bg-transparent text-sm text-gray-700 dark:text-gray-300 border-none outline-none cursor-pointer"
            >
              {YEARS.map(y => <option key={y} value={y}>{y}</option>)}
            </select>
          </div>

          <button onClick={() => executeBuilder(year)} disabled={executing}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg transition-colors disabled:opacity-50">
            <RefreshCw className={`w-3.5 h-3.5 ${executing ? 'animate-spin' : ''}`} />
            Actualiser
          </button>

          <button onClick={() => navigate(`/excel-builder`)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg transition-colors">
            <Settings2 className="w-3.5 h-3.5" />
            Configurer
          </button>

          <button onClick={handleExport} disabled={exporting}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors disabled:opacity-50">
            {exporting
              ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
              : <Download className="w-3.5 h-3.5" />}
            Exporter Excel
          </button>
        </div>
      </div>

      {/* ── Erreur non bloquante ── */}
      {error && (
        <div className="mx-4 mt-3 flex items-center gap-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg px-4 py-2 text-sm text-red-700 dark:text-red-400">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}

      {/* ── Table principale ── */}
      <div className="flex-1 overflow-auto p-4">
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">

          {/* Titre du rapport */}
          <div className="px-6 py-3 bg-blue-700 text-white text-center font-bold text-base tracking-wide">
            {config?.title || builder?.name || 'RAPPORT ANALYTIQUE'} — {year}
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="bg-gray-800 text-white">
                  <th className="sticky left-0 z-10 bg-gray-800 text-left px-4 py-2 font-semibold min-w-[250px]">
                    Libellé
                  </th>
                  {columns.map(col => (
                    <th key={col} className="px-3 py-2 text-right font-semibold whitespace-nowrap min-w-[80px]">
                      {col}
                    </th>
                  ))}
                  <th className="px-3 py-2 text-right font-bold bg-yellow-600 min-w-[90px]">
                    TOTAL
                  </th>
                </tr>
              </thead>
              <tbody>
                {executing ? (
                  <tr>
                    <td colSpan={columns.length + 2} className="text-center py-10 text-gray-400">
                      <div className="flex items-center justify-center gap-2">
                        <Loader2 className="w-5 h-5 animate-spin" />
                        Chargement des données…
                      </div>
                    </td>
                  </tr>
                ) : sections.length === 0 ? (
                  <tr>
                    <td colSpan={columns.length + 2} className="text-center py-10 text-gray-400">
                      Aucune section configurée
                    </td>
                  </tr>
                ) : sections.map((section, sIdx) => {
                  const isCollapsed = collapsedSections[sIdx]
                  const sectionColor = section.color || '#dbeafe'
                  const rows = section.rows || []

                  return (
                    <>
                      {/* En-tête de section */}
                      <tr
                        key={`section-${sIdx}`}
                        style={{ backgroundColor: sectionColor }}
                        className="cursor-pointer select-none"
                        onClick={() => toggleSection(sIdx)}
                      >
                        <td className="sticky left-0 z-10 px-4 py-1.5 font-bold text-gray-900"
                          style={{ backgroundColor: sectionColor }}>
                          <div className="flex items-center gap-1.5">
                            {isCollapsed
                              ? <ChevronRight className="w-3.5 h-3.5" />
                              : <ChevronDown className="w-3.5 h-3.5" />}
                            {section.label}
                          </div>
                        </td>
                        {columns.map((_, cIdx) => (
                          <td key={cIdx} className="px-3 py-1.5 text-right font-bold text-gray-900">
                            {/* Totaux de section si data disponible */}
                            {data && rows.length > 0
                              ? formatNumber(
                                  rows.filter(r => r.type !== 'total').reduce((sum, r) => {
                                    const v = r.values?.[cIdx]
                                    return sum + (Number(v) || 0)
                                  }, 0)
                                )
                              : ''}
                          </td>
                        ))}
                        <td className="px-3 py-1.5 text-right font-bold text-gray-900">
                          {data && rows.length > 0
                            ? formatNumber(
                                rows.filter(r => r.type !== 'total').reduce((sum, r) =>
                                  sum + getRowTotal(r.values), 0)
                              )
                            : ''}
                        </td>
                      </tr>

                      {/* Lignes de la section */}
                      {!isCollapsed && rows.map((row, rIdx) => {
                        const isTotal = row.type === 'total' || row.type === 'formula'
                        const rowBg = isTotal
                          ? (darkMode ? 'bg-blue-900/40' : 'bg-blue-50')
                          : (rIdx % 2 === 0
                            ? (darkMode ? 'bg-gray-800' : 'bg-white')
                            : (darkMode ? 'bg-gray-750' : 'bg-gray-50'))

                        return (
                          <tr key={`row-${sIdx}-${rIdx}`}
                            className={`${rowBg} hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors border-b border-gray-100 dark:border-gray-700`}>
                            <td className={`sticky left-0 z-10 ${rowBg} px-6 py-1 ${isTotal ? 'font-semibold' : 'font-normal'} text-gray-800 dark:text-gray-200`}>
                              {row.label}
                            </td>
                            {columns.map((_, cIdx) => {
                              const val = row.values?.[cIdx]
                              return (
                                <td key={cIdx}
                                  className={`px-3 py-1 text-right tabular-nums ${isTotal ? 'font-semibold text-blue-700 dark:text-blue-400' : 'text-gray-700 dark:text-gray-300'}`}>
                                  {data ? formatNumber(val) : <span className="text-gray-300">—</span>}
                                </td>
                              )
                            })}
                            <td className={`px-3 py-1 text-right tabular-nums font-semibold ${isTotal ? 'text-blue-700 dark:text-blue-400' : 'text-gray-900 dark:text-gray-100'}`}>
                              {data ? formatNumber(getRowTotal(row.values)) : '—'}
                            </td>
                          </tr>
                        )
                      })}
                    </>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* ── Résumé bas de page ── */}
        {data && (
          <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3">
            {sections.map((section, sIdx) => {
              const rows = section.rows || []
              const total = rows.filter(r => r.type !== 'total').reduce((sum, r) =>
                sum + getRowTotal(r.values), 0)
              return (
                <div key={sIdx}
                  className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-3 shadow-sm">
                  <div className="flex items-center gap-2 mb-1">
                    <div className="w-3 h-3 rounded-sm flex-shrink-0" style={{ backgroundColor: section.color || '#dbeafe' }} />
                    <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{section.label}</p>
                  </div>
                  <p className="text-sm font-bold text-gray-900 dark:text-white tabular-nums">
                    {formatNumber(total)}
                  </p>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
