import { useRef, useState, useMemo, useCallback } from 'react'
import { AgGridReact } from 'ag-grid-react'
import { X, Download, Code, ChevronDown, ChevronUp, Table2 } from 'lucide-react'
import { AG_GRID_LOCALE_FR } from '../../utils/agGridLocaleFr'

// ─── Formatters ──────────────────────────────────────────────────────────────

const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}(T|\s|$)/

function fmtNumber(params) {
  if (params.value == null || params.value === '') return ''
  const n = typeof params.value === 'number' ? params.value : parseFloat(params.value)
  if (isNaN(n)) return params.value
  const hasDecimals = n % 1 !== 0
  return n.toLocaleString('fr-FR', {
    minimumFractionDigits: hasDecimals ? 2 : 0,
    maximumFractionDigits: 2
  })
}

function fmtDate(params) {
  if (params.value == null || params.value === '') return ''
  try {
    const d = new Date(params.value)
    if (isNaN(d.getTime())) return params.value
    return `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}/${d.getFullYear()}`
  } catch {
    return params.value
  }
}

// ─── Construction des ColDefs depuis données brutes ───────────────────────────

function buildColDefs(columns, firstRow) {
  return columns.map(col => {
    const val = firstRow?.[col]
    const isNum = typeof val === 'number'
    const isDate = typeof val === 'string' && ISO_DATE_RE.test(val)

    return {
      field: col,
      headerName: col,
      sortable: true,
      resizable: true,
      filter: isNum ? 'agNumberColumnFilter' : isDate ? 'agDateColumnFilter' : 'agTextColumnFilter',
      floatingFilter: true,
      valueFormatter: isNum ? fmtNumber : isDate ? fmtDate : undefined,
      cellStyle: isNum ? { textAlign: 'right' } : undefined,
      flex: 1,
      minWidth: 90,
    }
  })
}

// ─── Composant principal ──────────────────────────────────────────────────────

export default function AIGridViewModal({ sql, results, columns, onClose }) {
  const gridRef = useRef(null)
  const [showSQL, setShowSQL] = useState(false)

  const colDefs = useMemo(() => {
    if (!columns?.length) return []
    return buildColDefs(columns, results?.[0])
  }, [columns, results])

  const defaultColDef = useMemo(() => ({
    sortable: true,
    resizable: true,
    filter: true,
    floatingFilter: true,
    suppressMovable: false,
  }), [])

  const exportCSV = useCallback(() => {
    if (!gridRef.current?.api) return
    gridRef.current.api.exportDataAsCsv({
      fileName: `resultats-ia-${new Date().toISOString().slice(0, 10)}.csv`,
      columnSeparator: ';',
      processCellCallback: (params) => {
        if (params.value == null) return ''
        return params.value
      }
    })
  }, [])

  // Fermeture sur Escape
  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Escape') onClose()
  }, [onClose])

  return (
    <div
      className="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
      onKeyDown={handleKeyDown}
      tabIndex={-1}
    >
      <div className="w-full max-w-[95vw] h-[90vh] flex flex-col
                      bg-white dark:bg-gray-900 rounded-2xl shadow-2xl
                      border border-gray-200 dark:border-gray-700 overflow-hidden">

        {/* ── En-tête ── */}
        <div className="flex items-center justify-between px-5 py-3
                        bg-primary-600 dark:bg-primary-700 text-white flex-shrink-0">
          <div className="flex items-center gap-2">
            <Table2 className="w-5 h-5" />
            <span className="font-semibold text-sm">Résultats SQL</span>
            <span className="px-2 py-0.5 text-xs bg-white/20 rounded-full">
              {results?.length ?? 0} ligne{results?.length !== 1 ? 's' : ''}
            </span>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={exportCSV}
              className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium
                         bg-white/15 hover:bg-white/25 rounded-lg transition-colors"
              title="Exporter en CSV"
            >
              <Download className="w-3.5 h-3.5" />
              Export CSV
            </button>
            <button
              onClick={() => setShowSQL(v => !v)}
              className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium
                         bg-white/15 hover:bg-white/25 rounded-lg transition-colors ml-1"
              title="Voir la requête SQL"
            >
              <Code className="w-3.5 h-3.5" />
              SQL
              {showSQL ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            </button>
            <button
              onClick={onClose}
              className="p-1.5 hover:bg-white/20 rounded-lg transition-colors ml-1"
              title="Fermer (Echap)"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* ── Bloc SQL (collapsible) ── */}
        {showSQL && sql && (
          <div className="flex-shrink-0 border-b border-gray-200 dark:border-gray-700
                          bg-gray-50 dark:bg-gray-950 px-4 py-3 max-h-40 overflow-auto">
            <pre className="text-xs font-mono text-gray-700 dark:text-gray-300 whitespace-pre-wrap break-all">
              {sql}
            </pre>
          </div>
        )}

        {/* ── AG Grid ── */}
        <div className="flex-1 min-h-0 ag-theme-alpine dark:ag-theme-alpine-dark">
          {colDefs.length > 0 ? (
            <AgGridReact
              ref={gridRef}
              rowData={results}
              columnDefs={colDefs}
              defaultColDef={defaultColDef}
              theme="legacy"
              localeText={AG_GRID_LOCALE_FR}
              pagination={true}
              paginationPageSize={50}
              paginationPageSizeSelector={[25, 50, 100, 200, 500]}
              enableCellTextSelection={true}
              ensureDomOrder={true}
              animateRows={true}
              suppressMenuHide={true}
              domLayout="normal"
              style={{ height: '100%', width: '100%' }}
            />
          ) : (
            <div className="flex items-center justify-center h-full text-gray-400 dark:text-gray-500 text-sm">
              Aucune donnée à afficher
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
