/**
 * Mapping columns_config (OptiBoard DB) → AG Grid ColDef[]
 */

const frNumber = (value, minFrac, maxFrac) => {
  if (value == null) return ''
  const n = typeof value === 'number' ? value : parseFloat(value)
  if (isNaN(n)) return ''
  return n.toLocaleString('fr-FR', {
    minimumFractionDigits: minFrac,
    maximumFractionDigits: maxFrac
  })
}

// Détecte si une string ressemble à une date ISO (2026-02-09T00:00:00)
const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}(T|\s)/

// Formate une date en jj/mm/aaaa
const formatDateFR = (value) => {
  if (value == null || value === '') return ''
  try {
    const d = new Date(value)
    if (isNaN(d.getTime())) return value
    const day = String(d.getDate()).padStart(2, '0')
    const month = String(d.getMonth() + 1).padStart(2, '0')
    const year = d.getFullYear()
    return `${day}/${month}/${year}`
  } catch {
    return value
  }
}

// Formate un nombre décimal/float en format FR (1 234,56)
const formatNumberFR = (value) => {
  if (value == null || value === '') return ''
  const n = typeof value === 'number' ? value : parseFloat(value)
  if (isNaN(n)) return value
  // Si entier → pas de décimales, sinon 2 décimales
  const hasDecimals = n % 1 !== 0
  return n.toLocaleString('fr-FR', {
    minimumFractionDigits: hasDecimals ? 2 : 0,
    maximumFractionDigits: 2
  })
}

const VALUE_FORMATTERS = {
  number: (params) => formatNumberFR(params.value),
  currency: (params) => {
    if (params.value == null) return ''
    return frNumber(params.value, 2, 2)
  },
  percent: (params) => {
    if (params.value == null) return ''
    if (typeof params.value === 'number') {
      return (params.value * 100).toFixed(2).replace('.', ',') + ' %'
    }
    return params.value
  },
  date: (params) => formatDateFR(params.value)
}

// Auto-formatter : détecte le type et applique le bon format
const autoValueFormatter = (params) => {
  const val = params.value
  if (val == null || val === '') return ''
  // Date ISO
  if (typeof val === 'string' && ISO_DATE_RE.test(val)) {
    return formatDateFR(val)
  }
  // Nombre (type number)
  if (typeof val === 'number') {
    return formatNumberFR(val)
  }
  // String numérique (décimal arrivant comme string, ex: "1234.56")
  if (typeof val === 'string' && val.trim() !== '' && !isNaN(Number(val))) {
    return formatNumberFR(Number(val))
  }
  return val
}

const ALIGN_STYLE = {
  left: { textAlign: 'left' },
  center: { textAlign: 'center' },
  right: { textAlign: 'right' }
}

function mapOneColumn(col, features) {
  const colDef = {
    field: col.field,
    headerName: col.header || col.field,
    hide: col.visible === false,
    sortable: features.allow_sorting !== false && col.sortable !== false,
    filter: col.filterable !== false,
    resizable: true,
    filterParams: { buttons: ['reset', 'apply'], closeOnApply: true }
  }

  // Width
  if (col.width) {
    colDef.width = col.width
  } else {
    colDef.flex = 1
    colDef.minWidth = 100
  }

  // Format → valueFormatter + filter type
  const fmt = col.format || ''
  const isNumericFormat = fmt === 'number' || fmt === 'currency' || fmt === 'percent'

  if (VALUE_FORMATTERS[fmt]) {
    colDef.valueFormatter = VALUE_FORMATTERS[fmt]
  } else {
    // Auto-détection : applique le formateur automatique (date ISO → jj/mm/aaaa, float → FR)
    colDef.valueFormatter = autoValueFormatter
  }

  if (isNumericFormat) {
    colDef.filter = 'agNumberColumnFilter'
  } else if (fmt === 'date') {
    colDef.filter = 'agDateColumnFilter'
  } else {
    colDef.filter = 'agTextColumnFilter'
  }

  // Alignment — les nombres toujours à droite
  if (col.align) {
    colDef.cellStyle = ALIGN_STYLE[col.align] || ALIGN_STYLE.left
    if (col.align === 'right') colDef.headerClass = 'ag-right-aligned-header'
    else if (col.align === 'center') colDef.headerClass = 'ag-center-aligned-header'
  } else if (isNumericFormat) {
    colDef.cellStyle = ALIGN_STYLE.right
    colDef.headerClass = 'ag-right-aligned-header'
  } else {
    // Auto-détection : aligner à droite si la valeur est un nombre ou un décimal (string numérique)
    colDef.cellStyle = (params) => {
      const v = params.value
      if (v == null || v === '') return { textAlign: 'left' }
      if (typeof v === 'number') return { textAlign: 'right' }
      if (typeof v === 'string' && v.trim() !== '' && !isNaN(Number(v))) return { textAlign: 'right' }
      return { textAlign: 'left' }
    }
  }

  // Pinned (if saved in prefs)
  if (col.pinned) colDef.pinned = col.pinned

  // AG state restoration (sort, sortIndex)
  if (col._agState) {
    if (col._agState.pinned) colDef.pinned = col._agState.pinned
    if (col._agState.sort) colDef.sort = col._agState.sort
    if (col._agState.sortIndex != null) colDef.sortIndex = col._agState.sortIndex
  }

  return colDef
}

/**
 * Convert columns_config array to AG Grid ColDef[]
 */
export function mapColumnsToColDefs(columns, features = {}) {
  if (!columns || !columns.length) return []
  return columns
    .filter(col => col.field && col.field.toLowerCase() !== 'societe')
    .map(col => mapOneColumn(col, features))
}

/**
 * Build pinned bottom row data for totals display
 */
export function buildTotalsRow(totalColumns, data, columns) {
  if (!totalColumns || !totalColumns.length || !data.length) return undefined

  const row = {}
  const firstVisible = columns.find(c => c.visible !== false && c.field.toLowerCase() !== 'societe')
  if (firstVisible) row[firstVisible.field] = 'TOTAL'

  totalColumns.forEach(field => {
    row[field] = data.reduce((sum, r) => {
      const v = r[field]
      return sum + (typeof v === 'number' ? v : 0)
    }, 0)
  })

  return [row]
}

/**
 * Convert AG Grid column state to app prefs format
 * Filtre les colonnes internes AG Grid (selection, auto-group, etc.)
 */
export function columnStateToPrefs(agColumnState, originalColumns) {
  return agColumnState
    .filter(agCol => {
      // Exclure les colonnes internes d'AG Grid
      if (!agCol.colId) return false
      if (agCol.colId.startsWith('ag-Grid-')) return false
      if (agCol.colId.startsWith('ag-grid-')) return false
      // Vérifier que la colonne existe dans la config originale
      return originalColumns.some(c => c.field === agCol.colId)
    })
    .map(agCol => {
      const orig = originalColumns.find(c => c.field === agCol.colId) || {}
      return {
        ...orig,
        field: agCol.colId,
        header: orig.header || agCol.colId,
        width: agCol.width || orig.width || null,
        visible: !agCol.hide,
        sortable: orig.sortable !== undefined ? orig.sortable : true,
        filterable: orig.filterable !== undefined ? orig.filterable : true,
        format: orig.format || '',
        align: orig.align || 'left',
        pinned: agCol.pinned || null,
        _agState: {
          pinned: agCol.pinned || null,
          sort: agCol.sort || null,
          sortIndex: agCol.sortIndex != null ? agCol.sortIndex : null
        }
      }
    })
}

/**
 * Convert app prefs to AG Grid column state for restore
 */
export function prefsToColumnState(columns) {
  const hasState = columns.some(c => c._agState || c.pinned)
  if (!hasState) return null

  return columns.map(col => ({
    colId: col.field,
    width: col.width || undefined,
    hide: col.visible === false,
    pinned: col._agState?.pinned || col.pinned || null,
    sort: col._agState?.sort || null,
    sortIndex: col._agState?.sortIndex != null ? col._agState.sortIndex : null
  }))
}
