import { useState, useEffect } from 'react'
import { X, ChevronLeft, ChevronRight, ArrowUpDown, FileSpreadsheet, Loader2 } from 'lucide-react'
import { useSettings } from '../../context/SettingsContext'
import { exportDrilldownPivotV2 } from '../../services/api'

export default function DrillDownModal({
  isOpen,
  onClose,
  pivotId,
  cellInfo,
  context,
  fetchDrilldown,
  className = '',
}) {
  const { formatNumber, formatDate } = useSettings()
  const [data, setData] = useState([])
  const [columns, setColumns] = useState([])
  const [totals, setTotals] = useState({})
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(50)
  const [totalPages, setTotalPages] = useState(1)
  const [loading, setLoading] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [error, setError] = useState(null)
  const [sortField, setSortField] = useState(null)
  const [sortDirection, setSortDirection] = useState('asc')

  useEffect(() => {
    if (isOpen && cellInfo && pivotId) {
      setPage(1)
      setSortField(null)
      setSortDirection('asc')
      loadData(1, null, 'asc')
    }
  }, [isOpen, cellInfo, pivotId])

  const loadData = async (newPage, sf, sd) => {
    setLoading(true)
    setError(null)
    try {
      const result = await fetchDrilldown(pivotId, {
        rowValues: cellInfo.rowValues || {},
        columnValue: cellInfo.columnValue || null,
        valueField: cellInfo.valueField,
        context: context || {},
        page: newPage,
        pageSize,
        sortField: sf !== undefined ? sf : sortField,
        sortDirection: sd !== undefined ? sd : sortDirection,
      })

      if (result.success) {
        setData(result.data || [])
        setColumns(result.columns || [])
        setTotals(result.totals || {})
        setTotal(result.total || 0)
        setPage(result.page || newPage)
        setTotalPages(result.totalPages || 1)
      } else {
        setError(result.error || 'Erreur inconnue')
      }
    } catch (err) {
      setError(err.message || 'Erreur de chargement')
    } finally {
      setLoading(false)
    }
  }

  const handleSort = (field) => {
    const newDir = sortField === field && sortDirection === 'asc' ? 'desc' : 'asc'
    setSortField(field)
    setSortDirection(newDir)
    loadData(1, field, newDir)
  }

  const handleExportExcel = async () => {
    setExporting(true)
    try {
      const request = {
        rowValues: cellInfo.rowValues || {},
        columnValue: cellInfo.columnValue || null,
        valueField: cellInfo.valueField,
        context: context || {},
        page: 1,
        pageSize: 999999,
        sortField,
        sortDirection,
      }
      const res = await exportDrilldownPivotV2(pivotId, request)
      const url = URL.createObjectURL(res.data)
      const a = document.createElement('a')
      a.href = url
      a.download = res.headers?.['content-disposition']?.split('filename=')[1] || `drilldown_${pivotId}.xlsx`
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

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-2xl w-[90vw] max-w-5xl max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h3 className="text-lg font-bold text-gray-900 dark:text-white">Detail des donnees</h3>
            <div className="flex items-center gap-1 text-xs text-gray-500 mt-1">
              {breadcrumb.map((item, i) => (
                <span key={i} className="flex items-center gap-1">
                  {i > 0 && <ChevronRight size={12} />}
                  <span className="bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded">{item}</span>
                </span>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500">{total.toLocaleString('fr-FR')} lignes</span>
            {/* Bouton Export Excel */}
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

        {/* Content — scroll vertical + horizontal, thead et tfoot sticky */}
        <div className="flex-1 overflow-auto drilldown-quartz" style={{ position: 'relative' }}>
          {loading ? (
            <div className="flex items-center justify-center h-48">
              <Loader2 size={32} className="animate-spin text-blue-500" />
            </div>
          ) : error ? (
            <div className="flex items-center justify-center h-48 text-red-500 text-sm">{error}</div>
          ) : (
            <table className="w-full border-collapse" style={{ borderSpacing: 0 }}>
              {/* En-tête : sticky en haut */}
              <thead style={{ position: 'sticky', top: 0, zIndex: 10 }}>
                <tr>
                  {columns.map(col => (
                    <th
                      key={col.field}
                      onClick={() => handleSort(col.field)}
                      className="text-left cursor-pointer hover:opacity-80 whitespace-nowrap"
                    >
                      <span className="flex items-center gap-1">
                        {col.header || col.field}
                        {sortField === col.field && (
                          <ArrowUpDown size={12} style={{ color: 'var(--color-primary-500, #3b82f6)' }} />
                        )}
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
                {data.map((row, i) => (
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
              </tbody>
            </table>
          )}
        </div>

        {/* Footer - Pagination */}
        <div className="flex items-center justify-between px-6 py-3 border-t border-gray-200 dark:border-gray-700">
          <span className="text-sm text-gray-500">
            Page {page} sur {totalPages} ({total.toLocaleString('fr-FR')} resultats)
          </span>
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
