import { useState, useMemo, useCallback, useRef, useEffect } from 'react'
import { ChevronDown, ChevronRight, ArrowUp, ArrowDown, TrendingUp, TrendingDown, Minus, Filter, Search, ChevronsDownUp, ChevronsUpDown } from 'lucide-react'
import { useSettings } from '../../context/SettingsContext'

// Utilitaires formatage conditionnel
function getHeatmapColor(value, min, max, colorMin, colorMax) {
  if (max === min) return null
  const ratio = Math.max(0, Math.min(1, (value - min) / (max - min)))
  const r1 = parseInt(colorMin.slice(1, 3), 16)
  const g1 = parseInt(colorMin.slice(3, 5), 16)
  const b1 = parseInt(colorMin.slice(5, 7), 16)
  const r2 = parseInt(colorMax.slice(1, 3), 16)
  const g2 = parseInt(colorMax.slice(3, 5), 16)
  const b2 = parseInt(colorMax.slice(5, 7), 16)
  const r = Math.round(r1 + (r2 - r1) * ratio)
  const g = Math.round(g1 + (g2 - g1) * ratio)
  const b = Math.round(b1 + (b2 - b1) * ratio)
  return `rgb(${r}, ${g}, ${b})`
}

function getThresholdColor(value, levels) {
  if (!levels || levels.length === 0) return null
  for (const level of levels) {
    if (value <= (level.max ?? Infinity)) {
      return level.color
    }
  }
  return null
}

function ColumnFilterDropdown({ values, selected, onChange, onClose }) {
  const [search, setSearch] = useState('')
  const filtered = search ? values.filter(v => v.toLowerCase().includes(search.toLowerCase())) : values
  const activeSet = selected || new Set()
  const allShown = activeSet.size === 0

  const toggle = (val) => {
    const next = new Set(activeSet)
    if (allShown) {
      // Passer de "tous" a "tous sauf celui-ci"
      values.forEach(v => { if (v !== val) next.add(v) })
    } else if (next.has(val)) {
      next.delete(val)
    } else {
      next.add(val)
    }
    // Si tout est selectionne, revenir a vide (= pas de filtre)
    if (next.size === values.length) {
      onChange(new Set())
    } else {
      onChange(next)
    }
  }

  return (
    <>
      <div className="p-2 border-b border-gray-200 dark:border-gray-700">
        <div className="relative">
          <Search size={12} className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text" value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Rechercher..."
            className="w-full text-xs pl-7 pr-2 py-1.5 border border-primary-300 dark:border-primary-600 rounded bg-white dark:bg-gray-700 focus:ring-1 focus:ring-blue-500 outline-none"
          />
        </div>
      </div>
      <div className="px-2 py-1 border-b border-gray-100 dark:border-gray-700 flex gap-3 text-[10px]">
        <button onClick={() => onChange(new Set())} className="text-blue-500 hover:underline">Tous</button>
        <button onClick={() => onChange(new Set(['__NONE__']))} className="text-blue-500 hover:underline">Aucun</button>
      </div>
      <div className="max-h-[220px] overflow-y-auto p-1">
        {filtered.map(val => (
          <label key={val} className="flex items-center gap-2 px-2 py-1 text-xs hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer rounded">
            <input
              type="checkbox"
              checked={allShown || activeSet.has(val)}
              onChange={() => toggle(val)}
              className="rounded text-blue-500"
            />
            <span className="truncate">{val}</span>
          </label>
        ))}
        {filtered.length === 0 && <div className="px-2 py-2 text-xs text-gray-400">Aucun resultat</div>}
      </div>
      <div className="p-1.5 border-t border-gray-200 dark:border-gray-700 text-right">
        <button onClick={onClose} className="text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 px-2 py-1">Fermer</button>
      </div>
    </>
  )
}

export default function PivotTable({
  data = [],
  pivotColumns = [],
  rowFields = [],
  columnField,
  valueFields = [],
  formattingRules = [],
  comparison,
  options = {},
  onCellClick,
  windowCalculations = [],
  summaryFunctions = [],
  className = '',
}) {
  const { formatNumber } = useSettings()
  const [expandedGroups, setExpandedGroups] = useState(new Set())
  const [allExpanded, setAllExpanded] = useState(true)
  const [sortConfig, setSortConfig] = useState(null)
  const [columnFilters, setColumnFilters] = useState({})
  const [filterDropdown, setFilterDropdown] = useState(null)
  const filterRef = useRef(null)

  // Fermer le dropdown filtre au clic exterieur
  useEffect(() => {
    if (!filterDropdown) return
    const handleClick = (e) => {
      if (filterRef.current && !filterRef.current.contains(e.target)) {
        setFilterDropdown(null)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [filterDropdown])

  const rowFieldNames = useMemo(() => rowFields.map(rf => rf.field || rf), [rowFields])

  // Window calculation columns: detect __WC_ keys from data
  const wcColumns = useMemo(() => {
    if (!data || data.length === 0) return []
    const wcKeys = new Set()
    for (const row of data) {
      for (const key of Object.keys(row)) {
        if (key.startsWith('__WC_') && key.endsWith('__')) wcKeys.add(key)
      }
    }
    // Map to label from windowCalculations prop or derive from key
    return Array.from(wcKeys).map(key => {
      const wcId = key.slice(4, -2) // strip __WC_ and __
      const wcDef = windowCalculations.find(w => w.id === wcId)
      return { key, label: wcDef?.label || wcId, format: wcDef?.format || 'number', decimals: wcDef?.decimals ?? 2 }
    })
  }, [data, windowCalculations])

  // Calculer min/max par champ pour le formatage conditionnel
  const fieldMinMax = useMemo(() => {
    const result = {}
    for (const rule of formattingRules) {
      if (rule.type === 'heatmap' || rule.type === 'data_bars') {
        let min = Infinity, max = -Infinity
        for (const row of data) {
          if (row.__isSubtotal__ || row.__isGrandTotal__ || row.__isSummary__) continue
          for (const key of Object.keys(row)) {
            if (key.includes(`_${rule.field}`) || key === rule.field) {
              const val = parseFloat(row[key])
              if (!isNaN(val)) {
                min = Math.min(min, val)
                max = Math.max(max, val)
              }
            }
          }
        }
        result[rule.field] = { min, max }
      }
    }
    return result
  }, [data, formattingRules])

  // Formatter une cellule — retourne un objet {text, suffix} pour séparer le suffixe DH
  const formatCell = useCallback((value, vf) => {
    if (value === null || value === undefined) return '-'
    const num = parseFloat(value)
    if (isNaN(num)) return value

    if (vf?.format === 'currency') {
      const formatted = formatNumber(num, { showCurrency: true, decimals: vf.decimals ?? 2 })
      // Séparer le suffixe monétaire (DH, €, $, etc.) pour un affichage plus propre
      const match = String(formatted).match(/^(.+?)\s+(DH|€|\$|MAD|EUR|USD)$/i)
      if (match) {
        return <>{match[1]} <span className="text-gray-400 dark:text-gray-500 text-[0.85em]">{match[2]}</span></>
      }
      return formatted
    }
    if (vf?.format === 'percent') {
      return <>{formatNumber(num, { decimals: vf.decimals ?? 1 })}<span className="text-gray-400 dark:text-gray-500 text-[0.85em]">%</span></>
    }
    return formatNumber(num, { decimals: vf?.decimals ?? 2 })
  }, [formatNumber])

  // Afficher les pourcentages sous une valeur
  const renderPct = useCallback((row, key) => {
    const parts = []
    if (options.showRowPercent && row[`${key}__pct_row`] != null) {
      parts.push(<span key="r" title="% ligne">{row[`${key}__pct_row`]}%L</span>)
    }
    if (options.showColPercent && row[`${key}__pct_col`] != null) {
      parts.push(<span key="c" title="% colonne" className="ml-1">{row[`${key}__pct_col`]}%C</span>)
    }
    if (options.showTotalPercent && row[`${key}__pct_total`] != null) {
      parts.push(<span key="t" title="% total" className="ml-1">{row[`${key}__pct_total`]}%T</span>)
    }
    if (parts.length === 0) return null
    return <div className="text-[9px] text-gray-400 dark:text-gray-500 mt-0.5 leading-tight">{parts}</div>
  }, [options.showRowPercent, options.showColPercent, options.showTotalPercent])

  // Appliquer le formatage conditionnel
  const getCellStyle = useCallback((value, fieldName) => {
    const style = {}
    for (const rule of formattingRules) {
      if (rule.field !== fieldName) continue
      const num = parseFloat(value)
      if (isNaN(num)) continue

      switch (rule.type) {
        case 'heatmap': {
          const mm = fieldMinMax[fieldName]
          if (mm) {
            const bg = getHeatmapColor(num, mm.min, mm.max, rule.config?.colorMin || '#ef4444', rule.config?.colorMax || '#22c55e')
            if (bg) {
              style.backgroundColor = bg
              style.color = '#fff'
            }
          }
          break
        }
        case 'thresholds': {
          const color = getThresholdColor(num, rule.config?.levels)
          if (color) {
            style.backgroundColor = color + '22'
            style.color = color
          }
          break
        }
        case 'negative_red': {
          if (num < 0) {
            style.color = rule.config?.color || '#ef4444'
            style.fontWeight = 600
          }
          break
        }
        default:
          break
      }
    }
    return style
  }, [formattingRules, fieldMinMax])

  // Data bar inline
  const getDataBar = useCallback((value, fieldName) => {
    const rule = formattingRules.find(r => r.field === fieldName && r.type === 'data_bars')
    if (!rule) return null
    const mm = fieldMinMax[fieldName]
    if (!mm || mm.max === mm.min) return null
    const num = parseFloat(value)
    if (isNaN(num)) return null
    const pct = Math.max(0, Math.min(100, ((num - mm.min) / (mm.max - mm.min)) * 100))
    return { width: `${pct}%`, color: rule.config?.color || '#3b82f6' }
  }, [formattingRules, fieldMinMax])

  // Collecter toutes les cles de groupe
  const allGroupKeys = useMemo(() => {
    const keys = new Set()
    for (const row of data) {
      if (!row.__isSubtotal__ && !row.__isGrandTotal__ && !row.__isSummary__ && rowFieldNames.length > 1) {
        keys.add(row[rowFieldNames[0]])
      }
    }
    return keys
  }, [data, rowFieldNames])

  // Expand/collapse un seul groupe
  const toggleGroup = (groupKey) => {
    if (allExpanded) {
      // Passer de "tout deplie" a "tout sauf ce groupe"
      const next = new Set(allGroupKeys)
      next.delete(groupKey)
      setExpandedGroups(next)
      setAllExpanded(false)
    } else {
      setExpandedGroups(prev => {
        const next = new Set(prev)
        if (next.has(groupKey)) {
          next.delete(groupKey)
        } else {
          next.add(groupKey)
        }
        // Si tous les groupes sont maintenant ouverts, revenir a allExpanded
        if (next.size === allGroupKeys.size) {
          setAllExpanded(true)
        }
        return next
      })
    }
  }

  const toggleAll = () => {
    if (allExpanded) {
      setExpandedGroups(new Set())
      setAllExpanded(false)
    } else {
      setExpandedGroups(new Set(allGroupKeys))
      setAllExpanded(true)
    }
  }

  // Tri
  const handleSort = (key) => {
    setSortConfig(prev => {
      if (prev?.key === key) {
        return prev.direction === 'asc' ? { key, direction: 'desc' } : null
      }
      return { key, direction: 'asc' }
    })
  }

  // Filtrer les lignes visibles (expand/collapse)
  // Valeurs uniques par champ ligne pour les filtres
  const uniqueValuesPerField = useMemo(() => {
    const result = {}
    for (const fname of rowFieldNames) {
      const vals = new Set()
      for (const row of data) {
        if (!row.__isSubtotal__ && !row.__isGrandTotal__ && !row.__isSummary__) {
          const v = row[fname]
          if (v !== undefined && v !== null && v !== '') vals.add(String(v))
        }
      }
      result[fname] = Array.from(vals).sort()
    }
    return result
  }, [data, rowFieldNames])

  // Appliquer les filtres colonnes
  const filteredData = useMemo(() => {
    const activeFilters = Object.entries(columnFilters).filter(([, s]) => s.size > 0)
    if (activeFilters.length === 0) return data
    return data.filter(row => {
      if (row.__isGrandTotal__ || row.__isSubtotal__ || row.__isSummary__) return true
      for (const [field, allowed] of activeFilters) {
        if (!allowed.has(String(row[field] || ''))) return false
      }
      return true
    })
  }, [data, columnFilters])

  const visibleRows = useMemo(() => {
    if (rowFieldNames.length <= 1) return filteredData

    return filteredData.filter(row => {
      if (row.__isGrandTotal__ || row.__isSummary__) return true

      const groupVal = row[rowFieldNames[0]]
      const isExpanded = allExpanded || expandedGroups.has(groupVal)

      if (row.__isSubtotal__) {
        return true // Toujours afficher les sous-totaux (sert de header quand replie)
      }

      // Si le groupe n'est pas expanded, masquer TOUTES les lignes detail
      // Le sous-total sert de ligne resumee pour le groupe
      if (!isExpanded) {
        return false
      }

      return true
    })
  }, [filteredData, rowFieldNames, expandedGroups, allExpanded])

  // Appliquer le tri
  const sortedRows = useMemo(() => {
    if (!sortConfig) return visibleRows
    const { key, direction } = sortConfig
    return [...visibleRows].sort((a, b) => {
      if (a.__isSummary__) return 1
      if (b.__isSummary__) return -1
      if (a.__isGrandTotal__) return 1
      if (b.__isGrandTotal__) return -1
      if (a.__isSubtotal__ && !b.__isSubtotal__) return 1
      if (!a.__isSubtotal__ && b.__isSubtotal__) return -1

      const aVal = a[key] ?? ''
      const bVal = b[key] ?? ''
      const aNum = parseFloat(aVal)
      const bNum = parseFloat(bVal)

      if (!isNaN(aNum) && !isNaN(bNum)) {
        return direction === 'asc' ? aNum - bNum : bNum - aNum
      }
      return direction === 'asc'
        ? String(aVal).localeCompare(String(bVal))
        : String(bVal).localeCompare(String(aVal))
    })
  }, [visibleRows, sortConfig])

  // Calculer l'info de groupe pour chaque ligne (pour eviter de repeter la 1ere colonne)
  const rowGroupInfo = useMemo(() => {
    if (rowFieldNames.length <= 1) return new Map()
    const info = new Map()
    let lastGroupVal = null
    for (let i = 0; i < sortedRows.length; i++) {
      const row = sortedRows[i]
      if (row.__isSubtotal__ || row.__isGrandTotal__ || row.__isSummary__) continue
      const groupVal = row[rowFieldNames[0]]
      if (groupVal !== lastGroupVal) {
        info.set(i, true) // premiere ligne du groupe
        lastGroupVal = groupVal
      } else {
        info.set(i, false) // ligne suivante dans le meme groupe
      }
    }
    return info
  }, [sortedRows, rowFieldNames])

  // Separer les lignes normales et les lignes sticky (grand total + summary)
  const { bodyRows, footerRows } = useMemo(() => {
    const body = []
    const footer = []
    for (const row of sortedRows) {
      if (row.__isGrandTotal__ || row.__isSummary__) {
        footer.push(row)
      } else {
        body.push(row)
      }
    }
    return { bodyRows: body, footerRows: footer }
  }, [sortedRows])

  // Pas de donnees
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-400 dark:text-gray-500 text-sm">
        Aucune donnee a afficher. Executez le pivot pour voir les resultats.
      </div>
    )
  }

  // Icone comparaison
  const ComparisonIcon = ({ value }) => {
    const num = parseFloat(value)
    if (isNaN(num)) return null
    if (num > 0) return <TrendingUp size={14} className="text-green-500 inline ml-1" />
    if (num < 0) return <TrendingDown size={14} className="text-red-500 inline ml-1" />
    return <Minus size={14} className="text-gray-400 inline ml-1" />
  }

  return (
    <div className={`flex flex-col pivot-quartz ${className}`} style={{ minHeight: 0, flex: '1 1 0%' }}>
      {/* Toolbar — afficher seulement s'il y a des sous-totaux */}
      {rowFieldNames.length > 1 && data.some(r => r.__isSubtotal__) && (
        <div className="flex items-center gap-2 mb-2 flex-shrink-0">
          <button
            onClick={toggleAll}
            className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors font-medium"
          >
            {allExpanded ? (
              <>
                <ChevronsDownUp size={14} />
                Tout replier
              </>
            ) : (
              <>
                <ChevronsUpDown size={14} />
                Tout deplier
              </>
            )}
          </button>
        </div>
      )}

      {/* Tableau */}
      <div className="overflow-auto flex-1" style={{ minHeight: 0 }}>
        <table className="w-full border-collapse">
          <thead className="sticky top-0 z-10">
            {/* En-tete colonnes pivot */}
            {columnField && pivotColumns.length > 0 && (
              <tr>
                {/* Espace pour les colonnes de lignes */}
                <th
                  colSpan={rowFieldNames.length}
                  className="pivot-col-header"
                />
                {pivotColumns.map(col => (
                  <th
                    key={col}
                    colSpan={valueFields.length}
                    className="pivot-col-header text-center"
                  >
                    {col}
                  </th>
                ))}
                {/* Totaux */}
                {options.showGrandTotals !== false && (
                  <th
                    colSpan={valueFields.length}
                    className="pivot-total-header text-center"
                  >
                    Total
                  </th>
                )}
              </tr>
            )}

            {/* En-tete mesures */}
            <tr>
              {/* Colonnes de lignes */}
              {rowFields.map(rf => {
                const fname = rf.field || rf
                const label = rf.label || fname
                const hasFilter = columnFilters[fname]?.size > 0
                return (
                  <th
                    key={fname}
                    className="text-left sticky left-0 z-20 relative pivot-row-cell"
                  >
                    <span className="flex items-center gap-1">
                      <span className="cursor-pointer hover:text-gray-900 dark:hover:text-gray-100" onClick={() => handleSort(fname)}>
                        {label}
                      </span>
                      {sortConfig?.key === fname && (
                        sortConfig.direction === 'asc' ? <ArrowUp size={12} className="pivot-sort-icon" /> : <ArrowDown size={12} className="pivot-sort-icon" />
                      )}
                      <button
                        onClick={(e) => { e.stopPropagation(); setFilterDropdown(filterDropdown === fname ? null : fname) }}
                        className={`p-0.5 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors ${hasFilter ? 'text-blue-500' : 'text-gray-400'}`}
                        title="Filtrer"
                      >
                        <Filter size={11} />
                      </button>
                    </span>
                    {filterDropdown === fname && (
                      <div ref={filterRef} className="absolute left-0 top-full mt-1 z-50 bg-white dark:bg-gray-800 pivot-filter-dropdown min-w-[200px]" onClick={(e) => e.stopPropagation()}>
                        <ColumnFilterDropdown
                          values={uniqueValuesPerField[fname] || []}
                          selected={columnFilters[fname]}
                          onChange={(newSet) => setColumnFilters(prev => ({ ...prev, [fname]: newSet }))}
                          onClose={() => setFilterDropdown(null)}
                        />
                      </div>
                    )}
                  </th>
                )
              })}

              {/* Colonnes de valeurs */}
              {columnField && pivotColumns.length > 0 ? (
                <>
                  {pivotColumns.map(col =>
                    valueFields.map(vf => {
                      const key = `${col}__${vf.alias}`
                      return (
                        <th
                          key={key}
                          onClick={() => handleSort(key)}
                          className="text-right cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700"
                        >
                          <span className="flex items-center justify-end gap-1">
                            {vf.label || vf.field}
                            {sortConfig?.key === key && (
                              sortConfig.direction === 'asc' ? <ArrowUp size={12} className="pivot-sort-icon" /> : <ArrowDown size={12} className="pivot-sort-icon" />
                            )}
                          </span>
                        </th>
                      )
                    })
                  )}
                  {/* Total columns */}
                  {options.showGrandTotals !== false && valueFields.map(vf => (
                    <th
                      key={`total_${vf.alias}`}
                      onClick={() => handleSort(`__TOTAL__${vf.alias}`)}
                      className="pivot-total-header text-right cursor-pointer hover:opacity-80"
                    >
                      <span className="flex items-center justify-end gap-1">
                        Total {vf.label || vf.field}
                        {sortConfig?.key === `__TOTAL__${vf.alias}` && (
                          sortConfig.direction === 'asc' ? <ArrowUp size={12} className="pivot-sort-icon" /> : <ArrowDown size={12} className="pivot-sort-icon" />
                        )}
                      </span>
                    </th>
                  ))}
                </>
              ) : (
                // Pas de colonne pivot
                <>
                  {valueFields.map(vf => (
                    <th
                      key={vf.alias}
                      onClick={() => handleSort(vf.alias)}
                      className="text-right cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700"
                    >
                      <span className="flex items-center justify-end gap-1">
                        {vf.label || vf.field}
                        {sortConfig?.key === vf.alias && (
                          sortConfig.direction === 'asc' ? <ArrowUp size={12} className="pivot-sort-icon" /> : <ArrowDown size={12} className="pivot-sort-icon" />
                        )}
                      </span>
                    </th>
                  ))}
                  {/* Colonnes calculs avances */}
                  {wcColumns.map(wc => (
                    <th
                      key={wc.key}
                      onClick={() => handleSort(wc.key)}
                      className="text-right cursor-pointer pivot-wc-cell hover:opacity-80"
                      style={{ color: 'var(--color-primary-600, #2563eb)' }}
                    >
                      <span className="flex items-center justify-end gap-1">
                        {wc.label}
                        {sortConfig?.key === wc.key && (
                          sortConfig.direction === 'asc' ? <ArrowUp size={12} className="pivot-sort-icon" /> : <ArrowDown size={12} className="pivot-sort-icon" />
                        )}
                      </span>
                    </th>
                  ))}
                </>
              )}
            </tr>
          </thead>

          <tbody>
            {bodyRows.map((row, rowIdx) => {
              const isSubtotal = row.__isSubtotal__
              const isGrandTotal = false
              const isSummary = false

              // Determiner si ce sous-total est dans un groupe replie
              const rawSubtotalVal = isSubtotal ? (row[rowFieldNames[0]] || '') : ''
              const subtotalGroupVal = isSubtotal
                ? (typeof rawSubtotalVal === 'string' && rawSubtotalVal.startsWith('Sous-total ')
                    ? rawSubtotalVal.slice('Sous-total '.length)
                    : rawSubtotalVal)
                : null
              const isCollapsedSubtotal = isSubtotal && rowFieldNames.length > 1 &&
                !allExpanded && !expandedGroups.has(subtotalGroupVal)

              const rowClass = isSubtotal
                ? isCollapsedSubtotal
                  ? 'pivot-collapsed-row'
                  : 'pivot-subtotal-row'
                : ''

              // Trouver l'index original dans sortedRows pour rowGroupInfo
              const origIdx = sortedRows.indexOf(row)

              return (
                <tr
                  key={row.__rowKey__ || rowIdx}
                  className={`${rowClass} transition-colors`}
                >
                  {/* Cellules de lignes */}
                  {rowFieldNames.map((fname, colIdx) => {
                    const cellVal = row[fname] || ''
                    const isGroupCol = colIdx === 0 && rowFieldNames.length > 1
                    const isFirstOfGroup = rowGroupInfo.get(origIdx) === true
                    const isDetailRow = rowGroupInfo.has(origIdx) && !rowGroupInfo.get(origIdx)

                    const showChevronOnSubtotal = isGroupCol && isCollapsedSubtotal
                    const showChevronOnDetail = isGroupCol && isFirstOfGroup && !isSubtotal
                    const showChevron = showChevronOnSubtotal || showChevronOnDetail

                    const groupKeyForChevron = showChevronOnSubtotal ? subtotalGroupVal : cellVal
                    const isExpanded = expandedGroups.has(groupKeyForChevron) || allExpanded
                    const hideGroupVal = isGroupCol && isDetailRow && !isSubtotal

                    let displayVal = cellVal
                    if (isCollapsedSubtotal && isGroupCol) {
                      displayVal = subtotalGroupVal || cellVal
                    }

                    return (
                      <td
                        key={fname}
                        className="text-left whitespace-nowrap sticky left-0 bg-inherit z-[5] pivot-row-cell"
                      >
                        <span className="flex items-center gap-1">
                          {showChevron && (
                            <button
                              onClick={() => toggleGroup(groupKeyForChevron)}
                              className="p-0.5 rounded hover:bg-gray-200 dark:hover:bg-gray-700"
                            >
                              {isExpanded
                                ? <ChevronDown size={14} className="text-gray-500" />
                                : <ChevronRight size={14} className="text-gray-500" />
                              }
                            </button>
                          )}
                          {!hideGroupVal && (
                            <span className={`${isCollapsedSubtotal ? 'font-semibold' : isSubtotal ? 'text-gray-500 dark:text-gray-400' : ''} ${showChevronOnDetail ? 'font-semibold' : ''}`}>
                              {isCollapsedSubtotal && colIdx > 0 ? '' : displayVal}
                            </span>
                          )}
                        </span>
                      </td>
                    )
                  })}

                  {/* Cellules de valeurs */}
                  {columnField && pivotColumns.length > 0 ? (
                    <>
                      {pivotColumns.map(col =>
                        valueFields.map(vf => {
                          const key = `${col}__${vf.alias}`
                          const val = row[key]
                          const cellStyle = getCellStyle(val, vf.field)
                          const dataBar = getDataBar(val, vf.field)
                          const drillRowValues = isSubtotal
                            ? { [rowFieldNames[0]]: subtotalGroupVal }
                            : Object.fromEntries(rowFieldNames.map(f => [f, row[f]]))
                          return (
                            <td
                              key={key}
                              onClick={(e) => onCellClick?.({
                                rowValues: drillRowValues,
                                columnValue: col,
                                valueField: vf.field,
                                event: e,
                              })}
                              style={cellStyle}
                              className="pivot-value-cell whitespace-nowrap pivot-clickable"
                            >
                              <div className="relative">
                                {dataBar && (
                                  <div className="absolute left-0 top-0 bottom-0 rounded opacity-20" style={{ width: dataBar.width, backgroundColor: dataBar.color }} />
                                )}
                                <span className="relative z-[1]">{formatCell(val, vf)}</span>
                                {renderPct(row, key)}
                              </div>
                            </td>
                          )
                        })
                      )}
                      {options.showGrandTotals !== false && valueFields.map(vf => {
                        const key = `__TOTAL__${vf.alias}`
                        const val = row[key]
                        return (
                          <td key={key} className="pivot-value-cell pivot-total-cell whitespace-nowrap">
                            {formatCell(val, vf)}
                            {renderPct(row, key)}
                          </td>
                        )
                      })}
                    </>
                  ) : (
                    <>
                      {valueFields.map(vf => {
                        const val = row[vf.alias]
                        const cellStyle = getCellStyle(val, vf.field)
                        const dataBar = getDataBar(val, vf.field)
                        const drillRowValues = isSubtotal
                          ? { [rowFieldNames[0]]: subtotalGroupVal }
                          : Object.fromEntries(rowFieldNames.map(f => [f, row[f]]))
                        return (
                          <td
                            key={vf.alias}
                            onClick={(e) => onCellClick?.({
                              rowValues: drillRowValues,
                              valueField: vf.field,
                              event: e,
                            })}
                            style={cellStyle}
                            className="pivot-value-cell whitespace-nowrap pivot-clickable"
                          >
                            <div className="relative">
                              {dataBar && (
                                <div className="absolute left-0 top-0 bottom-0 rounded opacity-20" style={{ width: dataBar.width, backgroundColor: dataBar.color }} />
                              )}
                              <span className="relative z-[1]">{formatCell(val, vf)}</span>
                              {renderPct(row, vf.alias)}
                            </div>
                          </td>
                        )
                      })}
                      {wcColumns.map(wc => {
                        const val = row[wc.key]
                        return (
                          <td key={wc.key} className="pivot-value-cell pivot-wc-cell whitespace-nowrap">
                            {val != null ? formatCell(val, { format: wc.format, decimals: wc.decimals }) : '-'}
                          </td>
                        )
                      })}
                    </>
                  )}
                </tr>
              )
            })}
          </tbody>

          {/* Grand Total + Summary : sticky en bas */}
          {footerRows.length > 0 && (
            <tfoot className="sticky bottom-0 z-10">
              {footerRows.map((row, fIdx) => {
                const isGrandTotal = row.__isGrandTotal__
                const isSummary = row.__isSummary__

                const rowClass = isSummary
                  ? 'pivot-summary-row'
                  : 'pivot-grandtotal-row'

                return (
                  <tr key={row.__rowKey__ || `footer_${fIdx}`} className={rowClass}>
                    {/* Cellules de lignes */}
                    {rowFieldNames.map((fname) => {
                      const cellVal = row[fname] || ''
                      return (
                        <td
                          key={fname}
                          className="text-left whitespace-nowrap sticky left-0 z-[5] pivot-row-cell"
                        >
                          <span className="font-bold">
                            {cellVal}
                          </span>
                        </td>
                      )
                    })}

                    {/* Cellules de valeurs */}
                    {columnField && pivotColumns.length > 0 ? (
                      <>
                        {pivotColumns.map(col =>
                          valueFields.map(vf => {
                            const key = `${col}__${vf.alias}`
                            const val = row[key]
                            return (
                              <td
                                key={key}
                                onClick={() => isGrandTotal && onCellClick?.({ rowValues: {}, columnValue: col, valueField: vf.field })}
                                className={`pivot-value-cell whitespace-nowrap ${isGrandTotal ? 'pivot-clickable' : ''}`}
                              >
                                <span className="relative z-[1]">
                                  {isSummary && row[`${key}__fn`] ? (
                                    <>
                                      <span className="text-[10px] font-medium mr-1">{row[`${key}__fn`]}</span>
                                      {formatCell(val, vf)}
                                    </>
                                  ) : formatCell(val, vf)}
                                </span>
                              </td>
                            )
                          })
                        )}
                        {options.showGrandTotals !== false && valueFields.map(vf => {
                          const key = `__TOTAL__${vf.alias}`
                          const val = row[key]
                          return (
                            <td
                              key={key}
                              onClick={() => isGrandTotal && onCellClick?.({ rowValues: {}, valueField: vf.field })}
                              className={`pivot-value-cell pivot-total-cell font-bold whitespace-nowrap ${isGrandTotal ? 'pivot-clickable' : ''}`}
                            >
                              {formatCell(val, vf)}
                            </td>
                          )
                        })}
                      </>
                    ) : (
                      <>
                        {valueFields.map(vf => {
                          const val = row[vf.alias]
                          return (
                            <td
                              key={vf.alias}
                              onClick={() => isGrandTotal && onCellClick?.({ rowValues: {}, valueField: vf.field })}
                              className={`pivot-value-cell whitespace-nowrap ${isGrandTotal ? 'pivot-clickable' : ''}`}
                            >
                              <span className="relative z-[1]">
                                {isSummary && row[`${vf.alias}__fn`] ? (
                                  <>
                                    <span className="text-[10px] font-medium mr-1">{row[`${vf.alias}__fn`]}</span>
                                    {formatCell(val, vf)}
                                  </>
                                ) : formatCell(val, vf)}
                              </span>
                            </td>
                          )
                        })}
                        {wcColumns.map(wc => {
                          const val = row[wc.key]
                          return (
                            <td key={wc.key} className="pivot-value-cell pivot-wc-cell whitespace-nowrap">
                              {val != null ? formatCell(val, { format: wc.format, decimals: wc.decimals }) : '-'}
                            </td>
                          )
                        })}
                      </>
                    )}
                  </tr>
                )
              })}
            </tfoot>
          )}
        </table>
      </div>
    </div>
  )
}
