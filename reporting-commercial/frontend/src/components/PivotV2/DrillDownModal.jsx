import { useState, useEffect, useMemo, useRef, useCallback } from 'react'
import { X, ChevronLeft, ChevronRight, ArrowUpDown, FileSpreadsheet, Loader2, Database, Search, Filter, ChevronDown } from 'lucide-react'
import { useSettings } from '../../context/SettingsContext'
import { exportDrilldownPivotV2 } from '../../services/api'

function ColumnFilterDropdown({ column, data, activeFilter, onFilter, formatCellValue }) {
  const [open, setOpen] = useState(false)
  const [filterSearch, setFilterSearch] = useState('')
  const ref = useRef(null)

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    if (open) document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  const uniqueValues = useMemo(() => {
    const vals = new Map()
    data.forEach(row => {
      const v = row[column.field]
      const key = v === null || v === undefined ? '__null__' : String(v)
      if (!vals.has(key)) vals.set(key, { raw: v, display: formatCellValue(v, column.format), count: 1 })
      else vals.get(key).count++
    })
    return Array.from(vals.values()).sort((a, b) => a.display.localeCompare(b.display, 'fr'))
  }, [data, column.field])

  const filtered = filterSearch
    ? uniqueValues.filter(v => v.display.toLowerCase().includes(filterSearch.toLowerCase()))
    : uniqueValues

  const isActive = activeFilter !== undefined

  return (
    <div ref={ref} className="relative inline-block">
      <button
        onClick={(e) => { e.stopPropagation(); setOpen(!open); setFilterSearch('') }}
        className={`p-0.5 rounded transition-colors ${isActive ? 'text-blue-600 dark:text-blue-400' : 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 opacity-0 group-hover:opacity-100'}`}
      >
        <Filter size={10} />
      </button>
      {open && (
        <div className="absolute top-full left-0 mt-1 w-56 bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 z-50" onClick={e => e.stopPropagation()}>
          <div className="p-2 border-b border-gray-100 dark:border-gray-700">
            <input
              value={filterSearch}
              onChange={e => setFilterSearch(e.target.value)}
              placeholder="Filtrer..."
              className="w-full px-2 py-1.5 text-xs border border-gray-200 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
              autoFocus
            />
          </div>
          <div className="max-h-48 overflow-y-auto">
            {isActive && (
              <button
                onClick={() => { onFilter(column.field, undefined); setOpen(false) }}
                className="w-full px-3 py-1.5 text-xs text-left text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20"
              >
                Effacer le filtre
              </button>
            )}
            {filtered.map((v, i) => (
              <button
                key={i}
                onClick={() => { onFilter(column.field, v.raw); setOpen(false) }}
                className={`w-full px-3 py-1.5 text-xs text-left hover:bg-gray-50 dark:hover:bg-gray-700 flex justify-between items-center ${
                  isActive && String(activeFilter) === String(v.raw) ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-600' : 'text-gray-700 dark:text-gray-300'
                }`}
              >
                <span className="truncate mr-2">{v.display === '-' ? '(vide)' : v.display}</span>
                <span className="text-gray-400 text-[10px] flex-shrink-0">{v.count}</span>
              </button>
            ))}
            {filtered.length === 0 && (
              <div className="px-3 py-2 text-xs text-gray-400 text-center">Aucun resultat</div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

const PAGE_SIZES = [25, 50, 100, 200]

export default function DrillDownModal({
  isOpen,
  onClose,
  pivotId,
  cellInfo,
  context,
  fetchDrilldown,
  exportDrilldown,
  drilldownDsCode = null,
  mainDsCode = null,
  title = null,
  className = '',
}) {
  const { formatNumber, formatDate } = useSettings()
  const [data, setData] = useState([])
  const [columns, setColumns] = useState([])
  const [totals, setTotals] = useState({})
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(50)
  const [totalPages, setTotalPages] = useState(1)
  const [loading, setLoading] = useState(false)
  const [loadingSeconds, setLoadingSeconds] = useState(0)
  const [exporting, setExporting] = useState(false)
  const [error, setError] = useState(null)
  const [sortField, setSortField] = useState(null)
  const [sortDirection, setSortDirection] = useState('asc')
  const [search, setSearch] = useState('')
  const [columnFilters, setColumnFilters] = useState({})

  // Escape key
  useEffect(() => {
    if (!isOpen) return
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [isOpen, onClose])

  useEffect(() => {
    if (isOpen && fetchDrilldown) {
      // Reset complet avant chaque chargement (évite d'afficher l'ancien état)
      setPage(1)
      setTotal(0)
      setTotalPages(1)
      setData([])
      setColumns([])
      setTotals({})
      setSortField(null)
      setSortDirection('asc')
      setSearch('')
      setColumnFilters({})
      setError(null)
      loadData(1, null, 'asc', pageSize)
    }
  }, [isOpen, cellInfo, pivotId])

  const loadData = async (newPage, sf, sd, ps) => {
    if (!fetchDrilldown) return
    setLoading(true)
    setLoadingSeconds(0)
    setError(null)
    // Timer visuel — incrémente chaque seconde pendant le chargement
    const timerRef = { id: null }
    const startTime = Date.now()
    timerRef.id = setInterval(() => {
      setLoadingSeconds(Math.floor((Date.now() - startTime) / 1000))
    }, 1000)
    try {
      const result = await fetchDrilldown(pivotId, {
        rowValues: cellInfo?.rowValues || {},
        columnValue: cellInfo?.columnValue || null,
        valueField: cellInfo?.valueField,
        context: context || {},
        page: newPage,
        pageSize: ps !== undefined ? ps : pageSize,
        sortField: sf !== undefined ? sf : sortField,
        sortDirection: sd !== undefined ? sd : sortDirection,
      })

      if (result.success) {
        // Normalise les colonnes : le backend peut retourner {name,type} ou {field,header,format,...}
        // DrillDownModal utilise col.field partout → s'assurer que field, header, format existent.
        const rawCols = result.columns || []
        const normCols = rawCols.map(c => ({
          ...c,
          field:  c.field  ?? c.name  ?? '',
          header: c.header ?? c.label ?? c.field ?? c.name ?? '',
          format: c.format ?? (c.type === 'number' ? 'number' : c.type === 'date' ? 'date' : ''),
        }))
        // Normalise les totaux : si indexés par name, les réindexer par field
        const rawTotals = result.totals || {}
        const normTotals = {}
        normCols.forEach(c => {
          if (rawTotals[c.field] !== undefined) normTotals[c.field] = rawTotals[c.field]
          else if (rawTotals[c.name] !== undefined) normTotals[c.field] = rawTotals[c.name]
        })
        setData(result.data || [])
        setColumns(normCols)
        setTotals(normTotals)
        setTotal(result.total || 0)
        setPage(result.page || newPage)
        setTotalPages(result.totalPages || 1)
      } else {
        setError(result.error || 'Erreur inconnue')
      }
    } catch (err) {
      setError(err.message || 'Erreur de chargement')
    } finally {
      clearInterval(timerRef.id)
      setLoading(false)
      setLoadingSeconds(0)
    }
  }

  const handleSort = (field) => {
    const newDir = sortField === field && sortDirection === 'asc' ? 'desc' : 'asc'
    setSortField(field)
    setSortDirection(newDir)
    loadData(1, field, newDir, pageSize)
  }

  const handlePageSizeChange = (newSize) => {
    setPageSize(newSize)
    setPage(1)
    loadData(1, sortField, sortDirection, newSize)
  }

  const handleExportExcel = async () => {
    setExporting(true)
    try {
      const request = {
        rowValues: cellInfo?.rowValues || {},
        columnValue: cellInfo?.columnValue || null,
        valueField: cellInfo?.valueField,
        context: context || {},
        page: 1,
        pageSize: 999999,
        sortField,
        sortDirection,
      }

      let res
      if (exportDrilldown) {
        res = await exportDrilldown(request)
      } else if (pivotId) {
        res = await exportDrilldownPivotV2(pivotId, request)
      } else {
        return
      }

      const url = URL.createObjectURL(res.data)
      const a = document.createElement('a')
      a.href = url
      a.download = res.headers?.['content-disposition']?.split('filename=')[1] || `drilldown.xlsx`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      console.error('Export error:', e)
    } finally {
      setExporting(false)
    }
  }

  const formatCellValue = (value, format) => {
    if (value === null || value === undefined) return '-'
    if (format === 'currency') return formatNumber(value, { showCurrency: true })
    if (format === 'number') return formatNumber(value)
    if (format === 'date') return formatDate(value)
    return String(value)
  }

  const filteredData = useMemo(() => {
    let result = data
    if (search) {
      const q = search.toLowerCase()
      result = result.filter(r => Object.values(r).some(v => String(v ?? '').toLowerCase().includes(q)))
    }
    const activeFilters = Object.entries(columnFilters).filter(([, v]) => v !== undefined)
    if (activeFilters.length > 0) {
      result = result.filter(r =>
        activeFilters.every(([field, val]) => {
          const rv = r[field]
          if (val === null || val === undefined) return rv === null || rv === undefined
          return String(rv ?? '') === String(val)
        })
      )
    }
    return result
  }, [data, search, columnFilters])

  const handleColumnFilter = (field, value) => {
    setColumnFilters(prev => {
      if (value === undefined) {
        const next = { ...prev }
        delete next[field]
        return next
      }
      return { ...prev, [field]: value }
    })
  }

  const activeFilterCount = Object.keys(columnFilters).length

  // Breadcrumb
  const breadcrumb = []
  if (cellInfo?.rowValues) {
    for (const [key, val] of Object.entries(cellInfo.rowValues)) {
      if (val !== 'TOTAL' && !String(val).startsWith('Sous-total')) {
        const display = (!val || val === 'None') ? '(vide)' : val
        breadcrumb.push(`${key}: ${display}`)
      }
    }
  }
  if (cellInfo?.columnValue) breadcrumb.push(cellInfo.columnValue)
  if (cellInfo?.valueField) breadcrumb.push(cellInfo.valueField)

  const hasTotals = Object.keys(totals).length > 0
  const modalTitle = title || 'Detail des donnees'

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-2xl w-[90vw] max-w-5xl max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-lg font-bold text-gray-900 dark:text-white">{modalTitle}</h3>
            </div>
            {breadcrumb.length > 0 && (
              <div className="flex items-center gap-1 text-xs text-gray-500 mt-1 flex-wrap">
                {breadcrumb.map((item, i) => (
                  <span key={i} className="flex items-center gap-1">
                    {i > 0 && <ChevronRight size={12} />}
                    <span className="bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded">{item}</span>
                  </span>
                ))}
              </div>
            )}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500">
              {filteredData.length !== data.length
                ? `${filteredData.length.toLocaleString('fr-FR')} / ${total.toLocaleString('fr-FR')}`
                : total.toLocaleString('fr-FR')
              } lignes
            </span>
            <button
              onClick={handleExportExcel}
              disabled={exporting || loading || total === 0}
              title="Exporter vers Excel"
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-green-600 hover:bg-green-700 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {exporting
                ? <Loader2 size={14} className="animate-spin" />
                : <FileSpreadsheet size={14} />
              }
              {exporting ? 'Export...' : 'Excel'}
            </button>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Search + Filter chips */}
        <div className="px-6 py-3 border-b border-gray-100 dark:border-gray-800 space-y-2">
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Rechercher dans la page courante…"
              className="w-full pl-9 pr-4 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          {activeFilterCount > 0 && (
            <div className="flex items-center gap-1.5 flex-wrap">
              <Filter size={12} className="text-blue-500" />
              {Object.entries(columnFilters).map(([field, val]) => {
                const col = columns.find(c => c.field === field)
                return (
                  <span key={field} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-700">
                    {col?.header || field}: {val === null || val === undefined ? '(vide)' : formatCellValue(val, col?.format)}
                    <button onClick={() => handleColumnFilter(field, undefined)} className="hover:text-red-500 ml-0.5">
                      <X size={10} />
                    </button>
                  </span>
                )
              })}
              <button onClick={() => setColumnFilters({})} className="text-[10px] text-red-500 hover:text-red-700 ml-1">
                Tout effacer
              </button>
            </div>
          )}
        </div>

        {/* Content — scroll vertical + horizontal, thead et tfoot sticky */}
        <div className="flex-1 overflow-auto drilldown-quartz" style={{ position: 'relative' }}>
          {loading ? (
            <div className="flex flex-col items-center justify-center h-48 gap-3">
              <Loader2 size={32} className="animate-spin text-blue-500" />
              <div className="text-sm text-gray-500 dark:text-gray-400">
                Chargement des données…
                {loadingSeconds >= 3 && (
                  <span className="ml-2 font-mono text-blue-600 dark:text-blue-400">{loadingSeconds}s</span>
                )}
              </div>
              {loadingSeconds >= 10 && (
                <div className="text-xs text-amber-600 dark:text-amber-400 max-w-xs text-center px-4">
                  Requête volumineuse en cours. Merci de patienter…
                </div>
              )}
            </div>
          ) : error ? (
            <div className="flex items-center justify-center h-48 text-red-500 text-sm">{error}</div>
          ) : (
            <table className="w-full border-collapse" style={{ borderSpacing: 0 }}>
              {/* En-tete : sticky en haut */}
              <thead style={{ position: 'sticky', top: 0, zIndex: 10 }}>
                <tr>
                  {columns.map(col => (
                    <th
                      key={col.field}
                      className="text-left whitespace-nowrap group"
                    >
                      <span className="flex items-center gap-1">
                        <span className="cursor-pointer hover:opacity-80" onClick={() => handleSort(col.field)}>
                          {col.header || col.field}
                        </span>
                        {sortField === col.field && (
                          <ArrowUpDown size={12} style={{ color: 'var(--color-primary-500, #3b82f6)' }} />
                        )}
                        <ColumnFilterDropdown
                          column={col}
                          data={data}
                          activeFilter={columnFilters[col.field]}
                          onFilter={handleColumnFilter}
                          formatCellValue={formatCellValue}
                        />
                      </span>
                    </th>
                  ))}
                </tr>
              </thead>

              {/* Total : sticky en bas */}
              {hasTotals && data.length > 0 && (
                <tfoot style={{ position: 'sticky', bottom: 0, zIndex: 10 }}>
                  <tr style={{
                    background: 'var(--color-primary-50, #EEF2FF)',
                    borderTop: '2px solid var(--color-primary-400, #60A5FA)',
                  }}>
                    {columns.map((col, idx) => {
                      const val = totals[col.field]
                      return (
                        <td
                          key={col.field}
                          className={`whitespace-nowrap ${['number', 'currency'].includes(col.format) ? 'text-right' : ''}`}
                          style={{
                            fontWeight: 700,
                            color: 'var(--color-primary-800, #1e3a5f)',
                            fontVariantNumeric: 'tabular-nums',
                            background: 'var(--color-primary-50, #EEF2FF)',
                          }}
                        >
                          {idx === 0
                            ? 'TOTAL'
                            : val !== undefined
                              ? formatCellValue(val, col.format)
                              : ''}
                        </td>
                      )
                    })}
                  </tr>
                </tfoot>
              )}

              <tbody>
                {filteredData.map((row, i) => (
                  <tr key={i}>
                    {columns.map(col => (
                      <td
                        key={col.field}
                        className={`whitespace-nowrap ${['number', 'currency'].includes(col.format) ? 'text-right' : ''}`}
                        style={['number', 'currency'].includes(col.format) ? { fontVariantNumeric: 'tabular-nums' } : undefined}
                      >
                        {formatCellValue(row[col.field], col.format)}
                      </td>
                    ))}
                  </tr>
                ))}
                {filteredData.length === 0 && !loading && (
                  <tr><td colSpan={columns.length || 1} className="text-center py-8 text-gray-400 text-sm">Aucun resultat</td></tr>
                )}
              </tbody>
            </table>
          )}
        </div>

        {/* Footer - Pagination + Page size */}
        <div className="flex items-center justify-between px-6 py-3 border-t border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-500">
              Page {page} sur {totalPages} — {filteredData.length !== data.length ? `${filteredData.length} affiche(s) / ` : ''}{total.toLocaleString('fr-FR')} resultats
            </span>
            <select
              value={pageSize}
              onChange={e => handlePageSizeChange(Number(e.target.value))}
              className="text-xs border border-gray-200 dark:border-gray-700 rounded-md bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              {PAGE_SIZES.map(s => (
                <option key={s} value={s}>{s} / page</option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => { const p = page - 1; setPage(p); loadData(p) }}
              disabled={page <= 1 || loading}
              className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronLeft size={18} style={{ color: 'var(--color-primary-500)' }} />
            </button>
            <button
              onClick={() => { const p = page + 1; setPage(p); loadData(p) }}
              disabled={page >= totalPages || loading}
              className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronRight size={18} style={{ color: 'var(--color-primary-500)' }} />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
