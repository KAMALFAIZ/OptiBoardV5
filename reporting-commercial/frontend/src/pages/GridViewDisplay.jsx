import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react'
import { useParams, Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useIsMobile } from '../hooks/useIsMobile'
import { AgGridReact } from 'ag-grid-react'
import {
  Table, RefreshCw, Edit, AlertCircle, Download, Settings2, Eye, Search, X, Filter,
  Columns, Layers, RotateCcw, ArrowRight, TrendingUp, Presentation
} from 'lucide-react'
import Loading from '../components/common/Loading'
import CheckboxListFilter from '../components/common/CheckboxListFilter'
import api, { getGridView, getDataSource, previewDataSource, executeQuery, getUnifiedDataSource, previewUnifiedDataSource, getUserGridPrefs, saveUserGridPrefs, resetUserGridPrefs, getUserEffectivePermissions, getDwhFilterOptions, exportGridPptx } from '../services/api'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import { mapColumnsToColDefs, buildTotalsRow, columnStateToPrefs, prefsToColumnState } from '../utils/agGridColumnMapper'
import { AG_GRID_LOCALE_FR } from '../utils/agGridLocaleFr'
import GlobalFilterBar from '../components/GlobalFilterBar'
import { useGlobalFilters } from '../context/GlobalFilterContext'
import SubscribeButton from '../components/common/SubscribeButton'
import FavoriteButton from '../components/common/FavoriteButton'
import InsightsPanel from '../components/common/InsightsPanel'
import ExecutiveSummaryModal from '../components/common/ExecutiveSummaryModal'
import AnomalyBadge from '../components/common/AnomalyBadge'
import ForecastModal from '../components/common/ForecastModal'

// Résoudre les macros de dates en valeurs réelles (format YYYY-MM-DD)
function resolveDateMacro(macroOrValue) {
  if (!macroOrValue || typeof macroOrValue !== 'string') return macroOrValue
  const today = new Date()
  const year = today.getFullYear()
  const month = today.getMonth() // 0-indexed
  const pad = (n) => String(n).padStart(2, '0')

  switch (macroOrValue.toUpperCase().trim()) {
    case 'TODAY':
      return today.toISOString().split('T')[0]
    case 'YESTERDAY': {
      const d = new Date(today); d.setDate(d.getDate() - 1)
      return d.toISOString().split('T')[0]
    }
    case 'FIRST_DAY_MONTH':
      return `${year}-${pad(month + 1)}-01`
    case 'LAST_DAY_MONTH': {
      const last = new Date(year, month + 1, 0)
      return `${year}-${pad(month + 1)}-${pad(last.getDate())}`
    }
    case 'FIRST_DAY_YEAR':
      return `${year}-01-01`
    case 'LAST_DAY_YEAR':
      return `${year}-12-31`
    case 'FIRST_DAY_LAST_MONTH': {
      const d = new Date(year, month - 1, 1)
      return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-01`
    }
    case 'LAST_DAY_LAST_MONTH': {
      const d = new Date(year, month, 0)
      return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
    }
    case 'FIRST_DAY_LAST_YEAR':
      return `${year - 1}-01-01`
    case 'LAST_DAY_LAST_YEAR':
      return `${year - 1}-12-31`
    default:
      return macroOrValue
  }
}

// ═══════════════════════════════════════════════════════════════════════
// GROUPEMENT MULTI-CHAMPS — Couleurs par niveau
// ═══════════════════════════════════════════════════════════════════════
const GROUP_LEVEL_STYLES = [
  { bg: 'var(--color-primary-50)', border: 'var(--color-primary-300)', text: 'var(--color-primary-900)' },
  { bg: '#f0fdf4', border: '#86efac', text: '#14532d' },
  { bg: '#fefce8', border: '#fde047', text: '#713f12' },
  { bg: '#fdf2f8', border: '#f9a8d4', text: '#831843' },
]

export default function GridViewDisplay() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { isEditor, user } = useAuth()
  const { darkMode } = useTheme()
  const { filters: globalFilters } = useGlobalFilters()
  const isMobile = useIsMobile()
  const gridRef = useRef(null)

  const [loading, setLoading] = useState(true)
  const [grid, setGrid] = useState(null)
  const [allData, setAllData] = useState([])
  const [columns, setColumns] = useState([])
  const [error, setError] = useState(null)
  const [refreshing, setRefreshing] = useState(false)
  const [debugInfo, setDebugInfo] = useState(null)
  const [showDebug, setShowDebug] = useState(true)

  // Recherche globale
  const [globalSearch, setGlobalSearch] = useState('')

  // Floating filters toggle
  const [showFilters, setShowFilters] = useState(false)

  // Groupement multi-champs
  const [groupByFields, setGroupByFields] = useState([])
  const [showGroupPanel, setShowGroupPanel] = useState(false)

  // Colonnes panel
  const [showColumnPanel, setShowColumnPanel] = useState(false)


  // Menu contextuel colonne
  const [contextMenu, setContextMenu] = useState(null) // { x, y, colId, field }
  // Menu contextuel titre
  const [titleContextMenu, setTitleContextMenu] = useState(null) // { x, y }

  // Gestion des paramètres
  const [sourceParams, setSourceParams] = useState([])
  const [paramValues, setParamValues] = useState({})
  const [showParamsModal, setShowParamsModal] = useState(false)
  const [openParamsCount, setOpenParamsCount] = useState(0)
  const [pendingSourceId, setPendingSourceId] = useState(null)
  const [pendingPageSize, setPendingPageSize] = useState(25)
  const [pendingTotalColumns, setPendingTotalColumns] = useState([])
  const [selectOptions, setSelectOptions] = useState({})
  const [loadingOptions, setLoadingOptions] = useState({})

  // Drill-through rules (field → list of rules)
  const [drillByColumn, setDrillByColumn] = useState({})

  // Indices de lignes anormales (pour highlight AG Grid)
  const [anomalyRowIndices, setAnomalyRowIndices] = useState(new Set())

  // Forecast modal
  const [forecastOpen, setForecastOpen] = useState(false)

  // Drill-through filter applied from URL params
  const dtField = searchParams.get('dt_field')
  const dtValue = searchParams.get('dt_value')
  const dtSource = searchParams.get('dt_source')

  // Debounce timer for saving prefs
  const saveTimerRef = useRef(null)

  useEffect(() => {
    loadGrid()
  }, [id])

  // Charger les règles drill-through pour ce GridView
  useEffect(() => {
    if (!id) return
    api.get(`/drillthrough/rules/by-source?source_type=gridview&source_id=${id}`)
      .then(res => {
        if (res.data.success) setDrillByColumn(res.data.by_column || {})
      })
      .catch(() => {})
  }, [id])

  // Charger les options pour les paramètres de type select/multiselect
  useEffect(() => {
    const loadSelectOptions = async () => {
      const selectParams = sourceParams.filter(p =>
        (p.type === 'select' || p.type === 'multiselect') && p.source === 'query' && p.query
      )

      // Champs DWH connus — charger via l'endpoint dédié (X-DWH-Code) plutôt que executeQuery (central DB)
      const DWH_FILTER_FIELDS = ['societe', 'commercial', 'gamme', 'zone']

      for (const param of selectParams) {
        if (selectOptions[param.name]) continue

        setLoadingOptions(prev => ({ ...prev, [param.name]: true }))
        try {
          let options = []
          if (DWH_FILTER_FIELDS.includes(param.name)) {
            const res = await getDwhFilterOptions(param.name)
            if (res.data?.success && res.data?.data) {
              options = res.data.data.map(row => ({ value: row.value, label: row.label }))
            }
          } else {
            const res = await executeQuery(param.query, 500)
            if (res.data.success && res.data.data) {
              options = res.data.data.map(row => ({
                value: row.value || row[Object.keys(row)[0]],
                label: row.label || row.value || row[Object.keys(row)[0]]
              }))
            }
          }
          if (param.allow_null) {
            options.unshift({ value: '', label: param.null_label || '(Tous)' })
          }
          setSelectOptions(prev => ({ ...prev, [param.name]: options }))
        } catch (err) {
          console.error(`Erreur chargement options ${param.name}:`, err)
        } finally {
          setLoadingOptions(prev => ({ ...prev, [param.name]: false }))
        }
      }
    }

    if (sourceParams.length > 0) {
      loadSelectOptions()
    }
  }, [sourceParams])

  const loadGrid = async () => {
    setLoading(true)
    setError(null)
    try {
      const gridRes = await getGridView(id)
      const gridData = gridRes.data.data
      setGrid(gridData)

      // Charger les prefs utilisateur (colonnes personnalisees)
      let finalColumns = gridData.columns || []
      if (user?.id) {
        try {
          const prefsRes = await getUserGridPrefs(gridData.id, user.id)
          if (prefsRes.data.has_prefs && prefsRes.data.data?.length > 0) {
            finalColumns = prefsRes.data.data
          }
        } catch (e) {
          console.warn('Pas de prefs utilisateur, utilisation config par defaut')
        }
      }

      // Appliquer les masques de colonnes du rôle de l'utilisateur
      if (user?.id) {
        try {
          const permRes = await getUserEffectivePermissions(user.id)
          const permsData = permRes.data?.data || {}
          const hiddenByType = permsData.hidden_columns?.gridview || {}
          // Chercher par l'id de la grille (en string ou number)
          const hiddenCols = hiddenByType[String(gridData.id)] || hiddenByType[Number(gridData.id)] || []
          if (hiddenCols.length > 0) {
            const hiddenSet = new Set(hiddenCols.map(c => c.toLowerCase()))
            // Supprimer complètement les colonnes masquées par rôle (grille + panneau)
            finalColumns = finalColumns.filter(col =>
              !hiddenSet.has((col.field || '').toLowerCase())
            )
          }
        } catch (e) {
          console.warn('Impossible de charger les permissions de colonnes:', e)
        }
      }

      setColumns(finalColumns)

      // Initialiser le groupement par défaut
      const defaultGroupBy = gridData.default_group_by
        || finalColumns.filter(c => c.groupBy).map(c => c.field)
      if (defaultGroupBy && defaultGroupBy.length > 0) {
        setGroupByFields(defaultGroupBy)
      }

      // Supporter data_source_code (templates) OU data_source_id (legacy)
      const hasSourceCode = gridData.data_source_code && gridData.data_source_code.trim() !== ''
      const hasSourceId = gridData.data_source_id && gridData.data_source_id > 0

      if (hasSourceCode || hasSourceId) {
        let sourceRes
        let sourceIdentifier

        if (hasSourceCode) {
          sourceIdentifier = gridData.data_source_code
          sourceRes = await getUnifiedDataSource(sourceIdentifier)
        } else {
          sourceIdentifier = gridData.data_source_id
          sourceRes = await getDataSource(sourceIdentifier)
        }

        if (sourceRes.data.success && sourceRes.data.data) {
          const params = sourceRes.data.data.parameters || []
          let paramList = []

          if (Array.isArray(params)) {
            paramList = params.map(p => ({
              name: p.name,
              label: p.label || p.name.replace('@', ''),
              type: p.type || 'text',
              default: p.default || p.defaultValue || '',
              required: p.required !== false,
              source: p.source,
              query: p.query,
              allow_null: p.allow_null,
              null_label: p.null_label
            }))
          } else if (typeof params === 'object' && Object.keys(params).length > 0) {
            paramList = Object.entries(params).map(([name, cfg]) => ({
              name,
              label: cfg.label || name.replace('@', ''),
              type: cfg.type || 'text',
              default: cfg.default || cfg.defaultValue || '',
              required: cfg.required !== false,
              source: cfg.source,
              query: cfg.query,
              allow_null: cfg.allow_null,
              null_label: cfg.null_label
            }))
          }

          setSourceParams(paramList)

          if (paramList.length > 0) {
            const defaults = {}
            paramList.forEach(p => {
              const key = p.name.replace('@', '')
              // Priorité : valeur par défaut définie → globalFilters → vide
              const globalVal = globalFilters?.[key]
              if (p.type === 'multiselect') {
                defaults[p.name] = []
              } else if (p.type === 'date') {
                defaults[p.name] = resolveDateMacro(p.default) || (globalVal ? String(globalVal) : '')
              } else {
                defaults[p.name] = p.default || (globalVal != null ? String(globalVal) : '')
              }
            })
            setParamValues(defaults)
            setPendingSourceId(sourceIdentifier)
            setPendingPageSize(gridData.page_size || 25)
            setPendingTotalColumns(gridData.total_columns || [])

            // Auto-execute si tous les params requis ont des valeurs (défaut ou globalFilters)
            const allRequiredHaveDefaults = paramList
              .filter(p => p.required)
              .every(p => {
                const val = defaults[p.name]
                return val && val !== '' && (!Array.isArray(val) || val.length > 0)
              })

            if (allRequiredHaveDefaults) {
              // Construire le contexte et charger directement
              const autoContext = {}
              paramList.forEach(p => {
                const key = p.name.replace('@', '')
                const value = defaults[p.name]
                if (Array.isArray(value)) {
                  if (value.length > 0) autoContext[key] = value
                } else if (value && typeof value === 'string' && value.trim() !== '') {
                  autoContext[key] = value
                } else if (value && typeof value === 'number') {
                  autoContext[key] = value
                }
              })
              await loadDataFromSource(sourceIdentifier, gridData.page_size || 25, gridData.total_columns || [], autoContext, hasSourceCode)
            } else {
              setShowParamsModal(true)
              setLoading(false)
              return
            }
          }
        }

        await loadDataFromSource(sourceIdentifier, gridData.page_size || 25, gridData.total_columns || [], {}, hasSourceCode)
      }
    } catch (err) {
      console.error('Erreur:', err)
      setError('Impossible de charger cette grille')
    } finally {
      setLoading(false)
    }
  }

  const executeWithParams = async () => {
    setShowParamsModal(false)
    setLoading(true)

    const context = {}
    sourceParams.forEach(p => {
      const key = p.name.replace('@', '')
      const value = paramValues[p.name]

      if (Array.isArray(value)) {
        if (value.length > 0) {
          context[key] = value
        }
      } else if (value && value.trim && value.trim() !== '') {
        context[key] = value
      } else if (value && typeof value === 'number') {
        context[key] = value
      }
    })

    const isCode = typeof pendingSourceId === 'string' && isNaN(Number(pendingSourceId))
    await loadDataFromSource(pendingSourceId, pendingPageSize, pendingTotalColumns, context, isCode)
    setLoading(false)
  }

  const loadDataFromSource = async (sourceIdentifier, pageSize, totalColumns, context = {}, useUnifiedApi = false) => {
    setRefreshing(true)
    const dbg = {
      sourceIdentifier,
      useUnifiedApi,
      globalFilters: { ...globalFilters },
      context: { ...context },
      mergedContext: null,
      endpoint: null,
      responseTotal: null,
      rowsReceived: null,
      error: null,
      ts: new Date().toISOString(),
    }
    try {
      const isCode = typeof sourceIdentifier === 'string' && isNaN(Number(sourceIdentifier))
      const shouldUseUnified = useUnifiedApi || isCode

      // Fusionner les filtres globaux (dates, societe) avec les paramètres spécifiques
      const mergedContext = { ...globalFilters, ...context }
      dbg.mergedContext = mergedContext
      dbg.shouldUseUnified = shouldUseUnified

      let response
      if (shouldUseUnified) {
        dbg.endpoint = `POST /api/datasources/unified/${sourceIdentifier}/preview`
        response = await previewUnifiedDataSource(sourceIdentifier, mergedContext, null, 0)
      } else {
        dbg.endpoint = `POST /api/builder/datasources/${sourceIdentifier}/preview`
        response = await previewDataSource(sourceIdentifier, mergedContext, 0)
      }

      const sourceData = response.data.data || []
      dbg.responseTotal = response.data.total ?? response.data.count ?? sourceData.length
      dbg.rowsReceived = sourceData.length
      dbg.responseKeys = response.data ? Object.keys(response.data) : []
      setAllData(sourceData)
    } catch (err) {
      console.error('Erreur chargement source:', err)
      dbg.error = err?.response?.data?.detail || err?.message || String(err)
      setError('Erreur lors du chargement des données')
    } finally {
      setRefreshing(false)
      setDebugInfo(dbg)
    }
  }

  // Features de la grille (avec valeurs par défaut)
  const features = useMemo(() => ({
    show_search: true,
    show_column_filters: true,
    show_grouping: true,
    show_column_toggle: true,
    show_export: true,
    show_pagination: true,
    show_page_size: true,
    allow_sorting: true,
    display_full_height: true,
    ...(grid?.features || {})
  }), [grid?.features])

  // Composant cellRenderer pour la première colonne (affiche le label de groupe)
  const GroupCellRenderer = useCallback((params) => {
    if (params.data?.__isGroupRow) {
      const d = params.data
      const icon = d.__expanded ? '▾' : '▸'
      const indent = (d.__level || 0) * 18
      return (
        <span style={{ paddingLeft: indent, cursor: 'pointer', fontWeight: 700, fontSize: '9pt', display: 'inline-block', width: '100%' }}>
          <span style={{ fontSize: 12, marginRight: 6 }}>{icon}</span>
          {d.__groupLabel}: <b>{d.__groupValue}</b>{' '}
          <span style={{ opacity: 0.5, fontWeight: 400, fontSize: '8pt' }}>({d.__groupCount})</span>
        </span>
      )
    }
    // Ligne normale → afficher la valeur formatée
    if (params.valueFormatted != null && params.valueFormatted !== '') return params.valueFormatted
    return params.value != null ? params.value : ''
  }, [])

  // AG Grid Column Defs — avec cellRenderer pour lignes de groupe
  const agColumnDefs = useMemo(() => {
    const baseCols = mapColumnsToColDefs(columns, features)
    if (!baseCols.length) return baseCols

    // La première colonne visible reçoit le cellRenderer de groupe (composant React)
    baseCols[0].cellRenderer = GroupCellRenderer

    // Marquer visuellement les colonnes avec des règles drill-through
    if (Object.keys(drillByColumn).length > 0) {
      baseCols.forEach(col => {
        if (drillByColumn[col.field]?.length > 0) {
          col.cellStyle = (params) => {
            if (params.data?.__isGroupRow) return undefined
            return { cursor: 'pointer', color: 'var(--color-primary-600)', textDecoration: 'underline dotted' }
          }
          col.headerTooltip = `Drill-through disponible → ${drillByColumn[col.field].map(r => r.label || r.nom).join(', ')}`
        }
      })
    }

    return baseCols
  }, [columns, features, GroupCellRenderer, drillByColumn])

  // ═══════════════════════════════════════════════════════════════════
  // GROUPEMENT MULTI-NIVEAUX HIÉRARCHIQUE
  // ═══════════════════════════════════════════════════════════════════
  const [expandedGroups, setExpandedGroups] = useState({})

  // Déterminer le champ de la première colonne visible (pour y injecter le label de groupe)
  const firstVisibleField = useMemo(() => {
    const col = columns.find(c => c.field && c.field.toLowerCase() !== 'societe' && c.visible !== false)
    return col?.field || null
  }, [columns])

  const groupedData = useMemo(() => {
    if (!groupByFields.length || !allData.length) return allData

    const totalColumns = grid?.total_columns || []

    // Fonction récursive pour grouper à chaque niveau
    const buildGroupRows = (rows, level, parentPath) => {
      if (level >= groupByFields.length) return rows // plus de niveaux → lignes détail

      const field = groupByFields[level]
      const label = columns.find(c => c.field === field)?.header || field
      const groups = {}
      const order = []

      rows.forEach(row => {
        const key = row[field] != null ? String(row[field]) : '(vide)'
        if (!groups[key]) { groups[key] = []; order.push(key) }
        groups[key].push(row)
      })

      const result = []
      order.forEach(key => {
        const groupRows = groups[key]
        const path = parentPath ? `${parentPath}|||${key}` : key
        const isExpanded = expandedGroups[path] !== false

        // Ligne de groupe — on met une valeur dans la 1ère colonne visible
        // pour forcer AG Grid à appeler le cellRenderer
        const groupRow = {
          __isGroupRow: true,
          __groupPath: path,
          __groupValue: key,
          __groupLabel: label,
          __groupCount: groupRows.length,
          __expanded: isExpanded,
          __level: level
        }
        // Injecter le label dans le champ de la première colonne visible
        if (firstVisibleField) {
          groupRow[firstVisibleField] = `${label}: ${key} (${groupRows.length})`
        }
        // Sous-totaux
        totalColumns.forEach(tc => {
          groupRow[tc] = groupRows.reduce((sum, r) => sum + (typeof r[tc] === 'number' ? r[tc] : 0), 0)
        })
        result.push(groupRow)

        // Enfants (récursif)
        if (isExpanded) {
          const children = buildGroupRows(groupRows, level + 1, path)
          children.forEach(r => result.push(r))
        }
      })
      return result
    }

    return buildGroupRows(allData, 0, '')
  }, [allData, groupByFields, expandedGroups, grid?.total_columns, columns, firstVisibleField])

  // Totals row (pinned bottom)
  const totalsRowData = useMemo(() => {
    const totalColumns = grid?.total_columns || []
    if (!totalColumns.length || !allData.length || !grid?.show_totals) return undefined
    return buildTotalsRow(totalColumns, allData, columns)
  }, [allData, grid?.total_columns, grid?.show_totals, columns])

  // Default column def
  const defaultColDef = useMemo(() => ({
    sortable: features.allow_sorting !== false,
    resizable: true,
    floatingFilter: features.show_column_filters && showFilters,
    filterParams: { buttons: ['reset'] },
    suppressHeaderMenuButton: true,
    suppressHeaderFilterButton: false,
    suppressHeaderContextMenu: true, // on gère le clic droit nous-mêmes
    // Sur mobile : largeur minimale lisible pour éviter le squeezing
    minWidth: isMobile ? 90 : 50,
  }), [features.allow_sorting, features.show_column_filters, showFilters, isMobile])

  // Quick filter (global search)
  useEffect(() => {
    if (gridRef.current?.api) {
      gridRef.current.api.setGridOption('quickFilterText', globalSearch || '')
    }
  }, [globalSearch])

  // Groupement : reset expanded quand on change de champs
  useEffect(() => {
    setExpandedGroups({})
  }, [groupByFields])

  // Toggle un groupe ouvert/fermé (par path)
  const toggleGroup = useCallback((groupPath) => {
    setExpandedGroups(prev => ({
      ...prev,
      [groupPath]: prev[groupPath] === false ? true : false
    }))
  }, [])

  // Ajouter / supprimer un champ de groupement
  const addGroupField = useCallback((field) => {
    if (field && !groupByFields.includes(field)) {
      setGroupByFields(prev => [...prev, field])
    }
  }, [groupByFields])

  const removeGroupField = useCallback((field) => {
    setGroupByFields(prev => prev.filter(f => f !== field))
  }, [])

  const moveGroupField = useCallback((index, direction) => {
    setGroupByFields(prev => {
      const arr = [...prev]
      const newIdx = index + direction
      if (newIdx < 0 || newIdx >= arr.length) return arr
      ;[arr[index], arr[newIdx]] = [arr[newIdx], arr[index]]
      return arr
    })
  }, [])

  // Save column state to prefs (debounced)
  const saveColumnPrefs = useCallback(() => {
    if (!gridRef.current?.api || !user?.id || !grid?.id) return

    if (saveTimerRef.current) clearTimeout(saveTimerRef.current)

    saveTimerRef.current = setTimeout(() => {
      const agState = gridRef.current.api.getColumnState()
      const updatedColumns = columnStateToPrefs(agState, columns)
      saveUserGridPrefs(grid.id, user.id, updatedColumns).catch(e =>
        console.warn('Erreur sauvegarde prefs:', e)
      )
    }, 1500)
  }, [user?.id, grid?.id, columns])

  // ═══════════════════════════════════════════════════════════════════
  // MENU CONTEXTUEL COLONNE
  // ═══════════════════════════════════════════════════════════════════
  const closeContextMenu = useCallback(() => setContextMenu(null), [])
  const closeTitleContextMenu = useCallback(() => setTitleContextMenu(null), [])

  // Fermer le menu contextuel quand on clique ailleurs
  useEffect(() => {
    if (contextMenu) {
      const handleClick = () => setContextMenu(null)
      window.addEventListener('click', handleClick)
      return () => window.removeEventListener('click', handleClick)
    }
  }, [contextMenu])

  const handleColumnContextMenu = useCallback((e) => {
    // e = { column, event } via onColumnHeaderContextMenu OU cellContextMenu
    const event = e.event || e
    const colId = e.column?.getColId?.() || e.column?.colId || null
    if (!colId) return
    event.preventDefault()
    event.stopPropagation()
    setContextMenu({
      x: event.clientX,
      y: event.clientY,
      colId,
      field: colId
    })
  }, [])

  const ctxSortAsc = useCallback(() => {
    if (!gridRef.current?.api || !contextMenu) return
    gridRef.current.api.applyColumnState({ state: [{ colId: contextMenu.colId, sort: 'asc' }], defaultState: { sort: null } })
    closeContextMenu()
  }, [contextMenu, closeContextMenu])

  const ctxSortDesc = useCallback(() => {
    if (!gridRef.current?.api || !contextMenu) return
    gridRef.current.api.applyColumnState({ state: [{ colId: contextMenu.colId, sort: 'desc' }], defaultState: { sort: null } })
    closeContextMenu()
  }, [contextMenu, closeContextMenu])

  const ctxClearSort = useCallback(() => {
    if (!gridRef.current?.api) return
    gridRef.current.api.applyColumnState({ defaultState: { sort: null } })
    closeContextMenu()
  }, [closeContextMenu])

  const ctxGroupByColumn = useCallback(() => {
    if (!contextMenu) return
    addGroupField(contextMenu.field)
    closeContextMenu()
  }, [contextMenu, addGroupField, closeContextMenu])

  const ctxUngroupAll = useCallback(() => {
    setGroupByFields([])
    closeContextMenu()
  }, [closeContextMenu])

  const ctxMoveLeft = useCallback(() => {
    if (!gridRef.current?.api || !contextMenu) return
    const allCols = gridRef.current.api.getAllDisplayedColumns()
    const idx = allCols.findIndex(c => c.getColId() === contextMenu.colId)
    if (idx > 0) {
      gridRef.current.api.moveColumnByIndex(idx, idx - 1)
      saveColumnPrefs()
    }
    closeContextMenu()
  }, [contextMenu, closeContextMenu, saveColumnPrefs])

  const ctxMoveRight = useCallback(() => {
    if (!gridRef.current?.api || !contextMenu) return
    const allCols = gridRef.current.api.getAllDisplayedColumns()
    const idx = allCols.findIndex(c => c.getColId() === contextMenu.colId)
    if (idx < allCols.length - 1) {
      gridRef.current.api.moveColumnByIndex(idx, idx + 1)
      saveColumnPrefs()
    }
    closeContextMenu()
  }, [contextMenu, closeContextMenu, saveColumnPrefs])

  const ctxHideColumn = useCallback(() => {
    if (!gridRef.current?.api || !contextMenu) return
    gridRef.current.api.setColumnsVisible([contextMenu.colId], false)
    saveColumnPrefs()
    closeContextMenu()
  }, [contextMenu, closeContextMenu, saveColumnPrefs])

  // Ref sur le container du grid pour attacher le clic droit sur les headers
  const gridContainerRef = useRef(null)
  // Ref sur la barre titre pour le menu contextuel titre
  const titleBarRef = useRef(null)

  // On grid ready - restore saved state
  const onGridReady = useCallback((params) => {
    const savedState = prefsToColumnState(columns)
    if (savedState) {
      params.api.applyColumnState({ state: savedState, applyOrder: true })
    }
    // Sur mobile : toujours auto-size (jamais sizeColumnsToFit qui écrase les colonnes)
    if (isMobile) {
      setTimeout(() => params.api.autoSizeAllColumns(), 100)
      return
    }
    // Tableau 100% : colonnes remplissent toute la largeur
    if (features.display_full_height) {
      setTimeout(() => params.api.sizeColumnsToFit(), 100)
    } else {
      // Auto-size columns if no saved widths
      const hasWidths = columns.some(c => c.width)
      if (!hasWidths) {
        setTimeout(() => params.api.autoSizeAllColumns(), 100)
      }
    }
  }, [columns, features.display_full_height, isMobile])

  // Quand display_full_height est actif, re-fit les colonnes au resize de la fenêtre (desktop uniquement)
  useEffect(() => {
    if (!features.display_full_height || isMobile) return
    const handleResize = () => {
      if (gridRef.current?.api) {
        gridRef.current.api.sizeColumnsToFit()
      }
    }
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [features.display_full_height, isMobile])

  // Attacher le clic droit sur les headers — via capture phase pour intercepter avant AG Grid
  useEffect(() => {
    const container = gridContainerRef.current
    if (!container) return

    const handleHeaderContextMenu = (event) => {
      // Vérifier si le clic est sur un header OU une cellule de données
      const headerCell = event.target.closest('.ag-header-cell')
      const bodyCell = event.target.closest('.ag-cell')
      const target = headerCell || bodyCell
      if (!target) return

      const colId = target.getAttribute('col-id')
      if (!colId || colId.startsWith('ag-Grid-')) return

      event.preventDefault()
      event.stopPropagation()
      setContextMenu({
        x: event.clientX,
        y: event.clientY,
        colId,
        field: colId
      })
    }

    // capture: true → intercepte AVANT que AG Grid ne consomme l'événement
    container.addEventListener('contextmenu', handleHeaderContextMenu, true)
    return () => container.removeEventListener('contextmenu', handleHeaderContextMenu, true)
  }, [])

  // Attacher le clic droit sur la barre titre via DOM natif (meme pattern que les colonnes)
  useEffect(() => {
    const el = titleBarRef.current
    if (!el) return

    const handleTitleContextMenu = (event) => {
      // Ne pas intercepter le clic droit sur les inputs
      if (event.target.tagName === 'INPUT' || event.target.tagName === 'SELECT') return
      event.preventDefault()
      event.stopPropagation()
      setTitleContextMenu({ x: event.clientX, y: event.clientY })
    }

    el.addEventListener('contextmenu', handleTitleContextMenu, true)
    return () => el.removeEventListener('contextmenu', handleTitleContextMenu, true)
  }, [])

  // Export CSV
  const exportCSV = useCallback(() => {
    if (!gridRef.current?.api) return
    gridRef.current.api.exportDataAsCsv({
      fileName: `${grid?.nom || 'grille'}.csv`,
      columnSeparator: ';',
      processCellCallback: (params) => {
        if (params.value == null) return ''
        return params.value
      }
    })
  }, [grid?.nom])

  // Export PowerPoint
  const [exportingPptx, setExportingPptx] = useState(false)
  const exportPptx = useCallback(async () => {
    if (!grid?.id) return
    setExportingPptx(true)
    try {
      const res = await exportGridPptx(grid.id)
      const url = URL.createObjectURL(res.data)
      const a = document.createElement('a')
      a.href = url
      a.download = `${grid.nom || 'grille'}.pptx`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Erreur export PPTX:', err)
    } finally {
      setExportingPptx(false)
    }
  }, [grid?.id, grid?.nom])

  // Écouter l'événement export depuis le FAB mobile
  useEffect(() => {
    if (!isMobile) return
    const handler = () => exportCSV()
    window.addEventListener('mobile:export:csv', handler)
    return () => window.removeEventListener('mobile:export:csv', handler)
  }, [isMobile, exportCSV])

  // Reset prefs
  const handleResetPrefs = useCallback(async () => {
    if (!user?.id || !grid?.id) return
    await resetUserGridPrefs(grid.id, user.id)
    const gridRes = await getGridView(id)
    const defaultCols = gridRes.data.data.columns || []
    setColumns(defaultCols)
    setGroupByFields([])
    setGlobalSearch('')
  }, [user?.id, grid?.id, id])

  // Toggle column visibility from panel
  const toggleColumnVisibility = useCallback((field) => {
    if (!gridRef.current?.api) return
    const col = gridRef.current.api.getColumn(field)
    if (col) {
      const isVisible = gridRef.current.api.getColumnState().find(c => c.colId === field)
      gridRef.current.api.setColumnsVisible([field], isVisible?.hide !== false ? true : !isVisible?.hide === false)
      // Simpler: toggle
      const currentState = gridRef.current.api.getColumnState()
      const colState = currentState.find(c => c.colId === field)
      if (colState) {
        gridRef.current.api.setColumnsVisible([field], colState.hide === true)
        saveColumnPrefs()
      }
    }
  }, [saveColumnPrefs])

  // Get column visibility state
  const getColumnVisibility = useCallback(() => {
    if (!gridRef.current?.api) {
      // Fallback: use columns config
      const vis = {}
      columns.forEach(c => { vis[c.field] = c.visible !== false })
      return vis
    }
    const vis = {}
    gridRef.current.api.getColumnState().forEach(c => {
      vis[c.colId] = !c.hide
    })
    return vis
  }, [columns])

  // Status bar (row count)
  const statusBar = useMemo(() => ({
    statusPanels: [
      { statusPanel: 'agTotalAndFilteredRowCountComponent', align: 'left' },
      { statusPanel: 'agSelectedRowCountComponent', align: 'center' }
    ]
  }), [])

  // Filtrage drill-through : si URL contient dt_field/dt_value, filtrer les données
  const displayData = useMemo(() => {
    if (!dtField || !dtValue) return groupedData
    return groupedData.filter(row => {
      if (row.__isGroupRow) return true
      return String(row[dtField] ?? '') === String(dtValue)
    })
  }, [groupedData, dtField, dtValue])

  // Gestion du clic sur une cellule drill-through
  const onCellClicked = useCallback((params) => {
    if (params.data?.__isGroupRow) return
    const field = params.column.getColId()
    const rules = drillByColumn[field]
    if (!rules || rules.length === 0) return
    const rule = rules[0]
    const value = params.value
    const url = `${rule.target_url}?dt_field=${encodeURIComponent(rule.target_filter_field)}&dt_value=${encodeURIComponent(value ?? '')}&dt_source=${encodeURIComponent(grid?.nom || '')}`
    navigate(url)
  }, [drillByColumn, navigate, grid?.nom])

  if (loading) {
    return <Loading message="Chargement de la grille..." />
  }

  if (error || !grid) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center p-8">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-2">Erreur</h2>
          <p className="text-gray-500 mb-4">{error || 'Grille introuvable'}</p>
          <Link to="/" className="btn-primary">Retour</Link>
        </div>
      </div>
    )
  }

  const columnVisibility = getColumnVisibility()

  return (
    <div className={`flex flex-col bg-slate-50 dark:bg-gray-900 ${isMobile ? 'h-[calc(100dvh-56px)]' : 'h-[calc(100vh-64px)] -m-3 lg:-m-4'}`}>
      {/* Header fixe — masqué sur mobile */}
      {!isMobile && <div className="flex-none bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 z-20">
        {/* Ligne 1 : titre + actions */}
        <div ref={titleBarRef} className="flex items-center justify-between px-4 py-2">
          <div className="flex items-center gap-3 min-w-0 cursor-context-menu">
            <Table className="w-5 h-5 text-primary-500 flex-shrink-0" />
            <h1 className="text-base font-bold text-gray-900 dark:text-white truncate">{grid.nom}</h1>
            {grid.description && (
              <span className="hidden lg:inline text-xs text-gray-400 truncate max-w-[200px]">{grid.description}</span>
            )}
            {/* Badge nb lignes */}
            <span className="flex-shrink-0 px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-xs font-medium text-gray-600 dark:text-gray-300 tabular-nums">
              {dtField && dtValue
                ? `${displayData.filter(r => !r.__isGroupRow).length.toLocaleString('fr-FR')} / ${allData.length.toLocaleString('fr-FR')} lignes`
                : `${allData.length.toLocaleString('fr-FR')} lignes`
              }
            </span>
            {refreshing && <RefreshCw className="w-3.5 h-3.5 text-primary-500 animate-spin flex-shrink-0" />}
          </div>

          <div className="flex items-center gap-1.5">
            {/* Paramètres globaux — masqué si le datasource a ses propres params */}
            {sourceParams.length === 0 && (
              <GlobalFilterBar showSociete={true} triggerOpen={openParamsCount} onFilterChange={() => {
                if (!grid) return
                const hasSourceCode = grid.data_source_code && grid.data_source_code.trim() !== ''
                const sourceIdentifier = hasSourceCode ? grid.data_source_code : grid.data_source_id
                if (!sourceIdentifier) return
                loadDataFromSource(sourceIdentifier, grid.page_size || 25, grid.total_columns || [], {}, hasSourceCode)
              }} />
            )}

            <div className="w-px h-6 bg-gray-200 dark:bg-gray-600 mx-0.5" />

            {/* Recherche globale */}
            {features.show_search && (
              <div className="relative">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
                <input
                  type="text"
                  value={globalSearch}
                  onChange={(e) => setGlobalSearch(e.target.value)}
                  placeholder="Rechercher..."
                  className="pl-8 pr-7 py-1.5 text-xs border border-primary-300 dark:border-primary-600 rounded-lg w-44 focus:ring-2 focus:ring-primary-500 focus:w-56 transition-all dark:bg-gray-700 dark:text-white"
                />
                {globalSearch && (
                  <button
                    onClick={() => setGlobalSearch('')}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            )}

            <div className="w-px h-6 bg-gray-200 dark:bg-gray-600 mx-0.5" />

            {/* Toggle Filtres */}
            {features.show_column_filters && (
              <button
                onClick={() => setShowFilters(!showFilters)}
                className={`p-1.5 rounded-lg transition-colors ${showFilters ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-600' : 'text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700'}`}
                title="Filtres par colonne"
              >
                <Filter className="w-4 h-4" />
              </button>
            )}

            {/* Groupement multi-champs */}
            {features.show_grouping && (
              <div className="relative">
                <button
                  onClick={() => setShowGroupPanel(!showGroupPanel)}
                  className={`p-1.5 rounded-lg transition-colors relative ${groupByFields.length ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-600' : 'text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700'}`}
                  title="Grouper par"
                >
                  <Layers className="w-4 h-4" />
                  {groupByFields.length > 0 && (
                    <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-primary-500 text-white text-[10px] flex items-center justify-center font-bold">{groupByFields.length}</span>
                  )}
                </button>
                {showGroupPanel && (
                  <>
                    <div className="fixed inset-0 z-30" onClick={() => setShowGroupPanel(false)} />
                    <div className="absolute right-0 mt-1 w-80 bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 z-40 p-3">
                      <div className="flex items-center justify-between mb-2">
                        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Grouper par</h3>
                        {groupByFields.length > 0 && (
                          <button onClick={() => setGroupByFields([])} className="text-xs text-red-500 hover:text-red-700">Tout retirer</button>
                        )}
                      </div>

                      {/* Champs sélectionnés — ordonnés */}
                      {groupByFields.length > 0 && (
                        <div className="flex flex-col gap-1 mb-2">
                          {groupByFields.map((field, i) => {
                            const col = columns.find(c => c.field === field)
                            return (
                              <div key={field} className="flex items-center gap-1 px-2 py-1 rounded bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-700">
                                <span className="text-xs font-bold text-primary-400 w-4">{i + 1}</span>
                                <span className="flex-1 text-xs font-medium text-primary-800 dark:text-primary-200">{col?.header || field}</span>
                                <button onClick={() => moveGroupField(i, -1)} disabled={i === 0} className="text-gray-400 hover:text-gray-600 disabled:opacity-30 text-xs px-0.5">▲</button>
                                <button onClick={() => moveGroupField(i, 1)} disabled={i === groupByFields.length - 1} className="text-gray-400 hover:text-gray-600 disabled:opacity-30 text-xs px-0.5">▼</button>
                                <button onClick={() => removeGroupField(field)} className="text-red-400 hover:text-red-600 text-xs px-0.5">✕</button>
                              </div>
                            )
                          })}
                        </div>
                      )}

                      {/* Ajouter un champ */}
                      <select
                        value=""
                        onChange={(e) => { addGroupField(e.target.value); e.target.value = '' }}
                        className="w-full px-2 py-1.5 text-sm border border-primary-300 dark:border-primary-600 rounded dark:bg-gray-700"
                      >
                        <option value="">+ Ajouter un niveau...</option>
                        {columns.filter(c => c.visible !== false && !groupByFields.includes(c.field)).map(col => (
                          <option key={col.field} value={col.field}>{col.header}</option>
                        ))}
                      </select>
                    </div>
                  </>
                )}
              </div>
            )}

            {/* Colonnes */}
            {features.show_column_toggle && (
              <div className="relative">
                <button
                  onClick={() => setShowColumnPanel(!showColumnPanel)}
                  className="p-1.5 rounded-lg text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                  title="Colonnes visibles"
                >
                  <Columns className="w-4 h-4" />
                </button>
                {showColumnPanel && (
                  <>
                    <div className="fixed inset-0 z-30" onClick={() => setShowColumnPanel(false)} />
                    <div className="absolute right-0 mt-1 w-64 bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 z-40 p-3 max-h-80 overflow-auto">
                      <div className="flex items-center justify-between mb-2">
                        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Colonnes visibles</h3>
                        {user?.id && (
                          <button
                            onClick={handleResetPrefs}
                            className="text-xs text-blue-600 hover:text-blue-800 dark:text-blue-400"
                            title="Réinitialiser la configuration des colonnes"
                          >
                            Réinitialiser
                          </button>
                        )}
                      </div>
                      <div className="space-y-0.5">
                        {columns.map(col => (
                          <label key={col.field} className="flex items-center gap-2 text-xs cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 px-1.5 py-1 rounded">
                            <input
                              type="checkbox"
                              checked={columnVisibility[col.field] !== false}
                              onChange={() => toggleColumnVisibility(col.field)}
                              className="rounded border-primary-300 w-3.5 h-3.5"
                            />
                            <span className="text-gray-700 dark:text-gray-300">{col.header}</span>
                          </label>
                        ))}
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}

            <div className="w-px h-6 bg-gray-200 dark:bg-gray-600 mx-0.5" />

            {/* Export */}
            {features.show_export && (
              <>
                <button
                  onClick={exportCSV}
                  disabled={!allData.length}
                  className="p-1.5 rounded-lg text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors disabled:opacity-40"
                  title="Exporter CSV"
                >
                  <Download className="w-4 h-4" />
                </button>
                <button
                  onClick={exportPptx}
                  disabled={exportingPptx}
                  className="p-1.5 rounded-lg text-indigo-500 hover:bg-indigo-50 dark:hover:bg-indigo-900/30 transition-colors disabled:opacity-40"
                  title="Exporter PowerPoint (.pptx)"
                >
                  {exportingPptx
                    ? <RefreshCw className="w-4 h-4 animate-spin" />
                    : <Presentation className="w-4 h-4" />}
                </button>
              </>
            )}

            {/* Auto-size */}
            <button
              onClick={() => gridRef.current?.api?.autoSizeAllColumns()}
              className="p-1.5 rounded-lg text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              title="Ajuster la largeur des colonnes"
            >
              <RotateCcw className="w-4 h-4" />
            </button>

            {/* Actualiser — ouvre le bon dialog selon le type de params */}
            <button
              onClick={() => {
                if (sourceParams.length > 0) {
                  setShowParamsModal(true)
                } else {
                  setOpenParamsCount(c => c + 1)
                }
              }}
              disabled={refreshing}
              className="p-1.5 rounded-lg text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors disabled:opacity-40"
              title="Actualiser les données"
            >
              <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            </button>

            {/* Bouton Forecast — desktop seulement */}
            {!isMobile && allData.length > 0 && (
              <button
                onClick={() => setForecastOpen(true)}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium border border-indigo-200 dark:border-indigo-700 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-300 hover:bg-indigo-100 dark:hover:bg-indigo-900/40 transition-colors"
                title="Prévision (Forecasting)"
              >
                <TrendingUp className="w-3.5 h-3.5" />
                Prévision
              </button>
            )}

            {/* Détection anomalies — desktop seulement */}
            {!isMobile && allData.length > 0 && (
              <AnomalyBadge
                data={allData}
                columnsInfo={columns}
                onAnomaliesLoaded={(indices) => {
                  setAnomalyRowIndices(indices)
                  gridRef.current?.api?.refreshCells({ force: true })
                  gridRef.current?.api?.redrawRows()
                }}
              />
            )}

            {/* Insights IA + Résumé Exécutif — desktop seulement */}
            {!isMobile && allData.length > 0 && grid && (
              <>
                <InsightsPanel
                  reportType="gridview"
                  reportId={parseInt(id)}
                  reportNom={grid.nom}
                  data={allData}
                  columnsInfo={columns}
                />
                <ExecutiveSummaryModal
                  reportType="gridview"
                  reportId={parseInt(id)}
                  reportNom={grid.nom}
                  data={allData}
                  columnsInfo={columns}
                />
              </>
            )}

            {/* Favoris + Abonnement email */}
            <div className="w-px h-6 bg-gray-200 dark:bg-gray-600 mx-0.5" />
            {grid && (
              <FavoriteButton reportType="gridview" reportId={parseInt(id)} reportNom={grid.nom} />
            )}
            {!isMobile && grid && (
              <SubscribeButton
                reportType="gridview"
                reportId={parseInt(id)}
                reportNom={grid.nom}
              />
            )}

            {!isMobile && isEditor() && (
              <>
                <div className="w-px h-6 bg-gray-200 dark:bg-gray-600 mx-0.5" />
                <Link
                  to="/gridview-builder"
                  className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-lg bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300 hover:bg-primary-100 dark:hover:bg-primary-900/40 transition-colors"
                >
                  <Edit className="w-3.5 h-3.5" />
                  Builder
                </Link>
              </>
            )}
          </div>
        </div>

        {/* Bandeau drill-through (visible si navigation depuis un rapport source) */}
        {dtField && dtValue && (
          <div className="flex items-center gap-2 px-4 py-1.5 bg-blue-50 dark:bg-blue-900/20 border-t border-blue-200 dark:border-blue-800/30 text-xs text-blue-700 dark:text-blue-300">
            <ArrowRight className="w-3.5 h-3.5 flex-shrink-0" />
            <span>
              Filtré depuis <b>{dtSource || 'rapport source'}</b> — {dtField}: <b>{dtValue}</b>
            </span>
            <button
              onClick={() => navigate(`/grid/${id}`)}
              className="ml-auto flex items-center gap-1 px-2 py-0.5 rounded bg-blue-100 dark:bg-blue-800/30 hover:bg-blue-200 dark:hover:bg-blue-700/40 transition-colors"
              title="Voir toutes les données"
            >
              <X className="w-3 h-3" /> Effacer le filtre
            </button>
          </div>
        )}

        {/* Barre chips groupement (visible seulement si groupement actif) */}
        {groupByFields.length > 0 && (
          <div className="flex items-center gap-1.5 px-4 py-1 bg-primary-50/50 dark:bg-primary-900/10 border-t border-primary-100 dark:border-primary-800/30 text-xs">
            <Layers className="w-3 h-3 text-primary-400 flex-shrink-0" />
            {groupByFields.map((field, i) => {
              const col = columns.find(c => c.field === field)
              return (
                <React.Fragment key={field}>
                  {i > 0 && <span className="text-primary-300 dark:text-primary-600">→</span>}
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-white dark:bg-gray-800 border border-primary-200 dark:border-primary-700 text-primary-700 dark:text-primary-300 font-medium shadow-sm">
                    {col?.header || field}
                    <button
                      onClick={() => removeGroupField(field)}
                      className="text-primary-300 hover:text-red-500 transition-colors"
                      title="Retirer"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                </React.Fragment>
              )
            })}
            <button
              onClick={() => setGroupByFields([])}
              className="ml-1 text-red-400 hover:text-red-600 text-xs transition-colors"
              title="Dégrouper tout"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>}

      {/* 🐛 DEBUG PANEL — affiche les infos de chargement des données */}
      {showDebug && debugInfo && (
        <div className="flex-none bg-yellow-50 border-b-2 border-yellow-400 px-4 py-2 text-xs font-mono z-10">
          <div className="flex items-center justify-between mb-1">
            <span className="font-bold text-yellow-800 text-sm">🐛 DEBUG — Chargement des données</span>
            <button onClick={() => setShowDebug(false)} className="text-yellow-600 hover:text-yellow-900 font-bold text-base leading-none">✕</button>
          </div>
          <div className="grid grid-cols-2 gap-x-6 gap-y-0.5 text-yellow-900">
            <div><b>Endpoint:</b> <span className="text-blue-700">{debugInfo.endpoint}</span></div>
            <div><b>Lignes reçues:</b> <span className={debugInfo.rowsReceived === 0 ? 'text-red-700 font-bold' : 'text-green-700 font-bold'}>{debugInfo.rowsReceived}</span> / total serveur: <b>{debugInfo.responseTotal}</b></div>
            <div><b>globalFilters.dateDebut:</b> <span className="text-orange-700">{String(debugInfo.globalFilters?.dateDebut ?? 'undefined')}</span></div>
            <div><b>globalFilters.dateFin:</b> <span className="text-orange-700">{String(debugInfo.globalFilters?.dateFin ?? 'undefined')}</span></div>
            <div><b>globalFilters.societe:</b> <span className="text-orange-700">{String(debugInfo.globalFilters?.societe ?? 'undefined')}</span></div>
            <div><b>shouldUseUnified:</b> {String(debugInfo.shouldUseUnified)}</div>
            <div className="col-span-2"><b>mergedContext envoyé:</b> <span className="text-purple-700">{JSON.stringify(debugInfo.mergedContext)}</span></div>
            <div className="col-span-2"><b>Clés réponse API:</b> {JSON.stringify(debugInfo.responseKeys)}</div>
            {debugInfo.error && <div className="col-span-2 text-red-700 font-bold"><b>❌ Erreur:</b> {debugInfo.error}</div>}
          </div>
        </div>
      )}

      {/* AG Grid */}
      <div ref={gridContainerRef} className={`flex-1 overflow-x-auto ${darkMode ? 'ag-theme-quartz-dark' : 'ag-theme-quartz'}`}>
        <AgGridReact
          ref={gridRef}
          theme="legacy"
          rowData={displayData}
          columnDefs={agColumnDefs}
          defaultColDef={defaultColDef}
          localeText={AG_GRID_LOCALE_FR}
          animateRows={true}
          enableCellTextSelection={true}
          ensureDomOrder={true}
          // Quand le groupement est actif, on empêche AG Grid de re-trier les lignes
          // car notre groupedData est déjà dans l'ordre hiérarchique correct
          postSortRows={groupByFields.length > 0 ? (params) => {
            // Restaurer l'ordre original de groupedData (ignorer le tri AG Grid)
            const indexMap = new Map()
            groupedData.forEach((row, i) => indexMap.set(row, i))
            params.nodes.sort((a, b) => (indexMap.get(a.data) ?? 0) - (indexMap.get(b.data) ?? 0))
          } : undefined}
          // Pagination
          pagination={features.show_pagination}
          paginationPageSize={grid?.page_size || 25}
          paginationPageSizeSelector={features.show_page_size ? [10, 25, 50, 100, 200, 500] : false}
          // Totals row
          pinnedBottomRowData={totalsRowData}
          // Column menu — menu contextuel custom
          suppressMenuHide={true}
          preventDefaultOnContextMenu={true}
          onCellContextMenu={handleColumnContextMenu}
          // Style lignes de groupe
          getRowStyle={(params) => {
            if (params.data?.__isGroupRow) {
              const level = params.data.__level || 0
              const s = GROUP_LEVEL_STYLES[level % GROUP_LEVEL_STYLES.length]
              return {
                backgroundColor: s.bg,
                borderLeft: `4px solid ${s.border}`,
                borderTop: level === 0 ? `2px solid ${s.border}` : `1px solid ${s.border}`,
                fontWeight: 700,
                cursor: 'pointer',
                color: s.text
              }
            }
            // Highlight lignes anormales
            if (params.node?.rowIndex != null && anomalyRowIndices.has(params.node.rowIndex)) {
              return { backgroundColor: 'rgba(251,191,36,0.12)', borderLeft: '3px solid #f59e0b' }
            }
            return undefined
          }}
          onRowClicked={(params) => {
            if (params.data?.__isGroupRow) {
              toggleGroup(params.data.__groupPath)
            }
          }}
          onCellClicked={onCellClicked}
          // Events
          onGridReady={onGridReady}
          onColumnResized={saveColumnPrefs}
          onColumnMoved={saveColumnPrefs}
          onColumnVisible={saveColumnPrefs}
          onColumnPinned={saveColumnPrefs}
          onSortChanged={saveColumnPrefs}
          // Size
          domLayout="normal"
        />
      </div>

      {/* Menu contextuel colonne */}
      {contextMenu && (
        <>
          <div className="fixed inset-0 z-50" onClick={closeContextMenu} onContextMenu={(e) => { e.preventDefault(); closeContextMenu() }} />
          <div
            className="fixed z-50 bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 py-1 min-w-[220px]"
            style={{ left: contextMenu.x, top: contextMenu.y }}
          >
            {/* Tri */}
            <button onClick={ctxSortAsc} className="ctx-menu-item">
              <span className="ctx-menu-icon">↑↓</span> Tri croissant
            </button>
            <button onClick={ctxSortDesc} className="ctx-menu-item">
              <span className="ctx-menu-icon">↓↑</span> Tri décroissant
            </button>
            <button onClick={ctxClearSort} className="ctx-menu-item text-gray-400 dark:text-gray-500">
              <span className="ctx-menu-icon">⊘</span> Effacer le tri
            </button>

            <div className="border-t border-gray-200 dark:border-gray-700 my-1" />

            {/* Groupement */}
            <button onClick={ctxGroupByColumn} className="ctx-menu-item">
              <span className="ctx-menu-icon">▦</span> Grouper par cette colonne
            </button>
            {groupByFields.length > 0 && (
              <button onClick={ctxUngroupAll} className="ctx-menu-item">
                <span className="ctx-menu-icon">⊟</span> Dégrouper tout
              </button>
            )}

            <div className="border-t border-gray-200 dark:border-gray-700 my-1" />

            {/* Déplacer */}
            <button onClick={ctxMoveLeft} className="ctx-menu-item">
              <span className="ctx-menu-icon">←</span> Déplacer à gauche
            </button>
            <button onClick={ctxMoveRight} className="ctx-menu-item">
              <span className="ctx-menu-icon">→</span> Déplacer à droite
            </button>

            <div className="border-t border-gray-200 dark:border-gray-700 my-1" />

            {/* Masquer */}
            <button onClick={ctxHideColumn} className="ctx-menu-item text-red-500 dark:text-red-400">
              <span className="ctx-menu-icon">👁</span> Masquer la colonne
            </button>
          </div>
        </>
      )}

      {/* Menu contextuel titre */}
      {titleContextMenu && (
        <>
          <div className="fixed inset-0 z-50" onClick={closeTitleContextMenu} onContextMenu={(e) => { e.preventDefault(); closeTitleContextMenu() }} />
          <div
            className="fixed z-50 bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 py-1 min-w-[220px]"
            style={{ left: titleContextMenu.x, top: titleContextMenu.y }}
          >
            {/* Actualiser */}
            <button onClick={() => {
              closeTitleContextMenu()
              if (sourceParams.length > 0) {
                setShowParamsModal(true)
              } else {
                setOpenParamsCount(c => c + 1)
              }
            }} className="ctx-menu-item">
              <span className="ctx-menu-icon"><RefreshCw className="w-3.5 h-3.5" /></span> Actualiser les données
            </button>

            <div className="border-t border-gray-200 dark:border-gray-700 my-1" />

            {/* Recherche */}
            {features.show_search && (
              <button onClick={() => {
                closeTitleContextMenu()
                setGlobalSearch('')
                // Focus sur le champ recherche apres fermeture
                setTimeout(() => {
                  const input = document.querySelector('input[placeholder="Rechercher..."]')
                  if (input) input.focus()
                }, 100)
              }} className="ctx-menu-item">
                <span className="ctx-menu-icon"><Search className="w-3.5 h-3.5" /></span> Rechercher
              </button>
            )}

            {/* Filtres colonnes */}
            {features.show_column_filters && (
              <button onClick={() => { closeTitleContextMenu(); setShowFilters(!showFilters) }} className="ctx-menu-item">
                <span className="ctx-menu-icon"><Filter className="w-3.5 h-3.5" /></span> {showFilters ? 'Masquer les filtres' : 'Afficher les filtres'}
              </button>
            )}

            <div className="border-t border-gray-200 dark:border-gray-700 my-1" />

            {/* Groupement */}
            {features.show_grouping && (
              <button onClick={() => { closeTitleContextMenu(); setShowGroupPanel(!showGroupPanel) }} className="ctx-menu-item">
                <span className="ctx-menu-icon"><Layers className="w-3.5 h-3.5" /></span> {showGroupPanel ? 'Fermer groupement' : 'Panneau groupement'}
              </button>
            )}
            {groupByFields.length > 0 && (
              <button onClick={() => { closeTitleContextMenu(); setGroupByFields([]) }} className="ctx-menu-item">
                <span className="ctx-menu-icon">⊟</span> Dégrouper tout
              </button>
            )}

            <div className="border-t border-gray-200 dark:border-gray-700 my-1" />

            {/* Colonnes */}
            {features.show_column_toggle && (
              <button onClick={() => { closeTitleContextMenu(); setShowColumnPanel(!showColumnPanel) }} className="ctx-menu-item">
                <span className="ctx-menu-icon"><Columns className="w-3.5 h-3.5" /></span> {showColumnPanel ? 'Fermer colonnes' : 'Colonnes visibles'}
              </button>
            )}

            {/* Ajuster largeur */}
            <button onClick={() => {
              closeTitleContextMenu()
              if (!isMobile && features.display_full_height) {
                gridRef.current?.api?.sizeColumnsToFit()
              } else {
                gridRef.current?.api?.autoSizeAllColumns()
              }
            }} className="ctx-menu-item">
              <span className="ctx-menu-icon"><RotateCcw className="w-3.5 h-3.5" /></span> Ajuster largeur colonnes
            </button>

            {/* Export */}
            {features.show_export && allData.length > 0 && (
              <>
                <div className="border-t border-gray-200 dark:border-gray-700 my-1" />
                <button onClick={() => { closeTitleContextMenu(); exportCSV() }} className="ctx-menu-item">
                  <span className="ctx-menu-icon"><Download className="w-3.5 h-3.5" /></span> Exporter CSV
                </button>
              </>
            )}

            {/* Builder (editeurs uniquement) */}
            {isEditor() && (
              <>
                <div className="border-t border-gray-200 dark:border-gray-700 my-1" />
                <button onClick={() => { closeTitleContextMenu(); navigate('/gridview-builder') }} className="ctx-menu-item">
                  <span className="ctx-menu-icon"><Edit className="w-3.5 h-3.5" /></span> Ouvrir dans le Builder
                </button>
              </>
            )}
          </div>
        </>
      )}

      {/* Modal Paramètres */}
      {showParamsModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/50" />
          <div className="relative bg-white dark:bg-gray-800 rounded-xl shadow-xl p-6 w-[500px] max-w-[90vw]">
            <div className="flex items-center gap-2 mb-4">
              <Settings2 className="w-5 h-5 text-primary-500" />
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Paramètres du rapport
              </h2>
            </div>

            <p className="text-sm text-gray-500 mb-4">
              Veuillez saisir les paramètres pour afficher les données du rapport.
            </p>

            <div className="space-y-4 mb-6">
              {sourceParams.map((param, i) => (
                <div key={i}>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    {param.label || param.name.replace('@', '')}
                    {param.required && <span className="text-red-500 ml-1">*</span>}
                  </label>

                  {param.type === 'select' ? (
                    <select
                      value={paramValues[param.name] || ''}
                      onChange={(e) => setParamValues({ ...paramValues, [param.name]: e.target.value || null })}
                      disabled={loadingOptions[param.name]}
                      className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-700 dark:text-white"
                    >
                      {loadingOptions[param.name] ? (
                        <option>Chargement...</option>
                      ) : (
                        selectOptions[param.name]?.map((opt, j) => (
                          <option key={j} value={opt.value}>{opt.label}</option>
                        )) || <option value="">-- Sélectionner --</option>
                      )}
                    </select>
                  ) : param.type === 'multiselect' ? (
                    <CheckboxListFilter
                      options={selectOptions[param.name] || []}
                      value={Array.isArray(paramValues[param.name]) ? paramValues[param.name] : []}
                      onChange={(selected) => setParamValues({ ...paramValues, [param.name]: selected })}
                      loading={loadingOptions[param.name]}
                      allowNull={param.allow_null !== false}
                      nullLabel={param.null_label || '(Toutes)'}
                      label={param.label || param.name}
                      searchable={true}
                      maxHeight={180}
                    />
                  ) : (
                    <input
                      type={param.type === 'date' ? 'date' : (param.type === 'number' || param.type === 'float') ? 'number' : 'text'}
                      step={param.type === 'float' ? '0.01' : undefined}
                      value={paramValues[param.name] || ''}
                      onChange={(e) => setParamValues({ ...paramValues, [param.name]: e.target.value })}
                      placeholder={param.label || param.name}
                      className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-700 dark:text-white"
                    />
                  )}
                </div>
              ))}
            </div>

            <div className="flex justify-end gap-2">
              <Link to="/" className="btn-secondary">
                Annuler
              </Link>
              <button
                onClick={executeWithParams}
                className="btn-primary flex items-center gap-1"
              >
                <Eye className="w-4 h-4" />
                Afficher le rapport
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Forecast Modal */}
      <ForecastModal
        isOpen={forecastOpen}
        onClose={() => setForecastOpen(false)}
        data={allData}
        columns={columns}
        reportName={grid?.nom || 'Rapport'}
      />
    </div>
  )
}
