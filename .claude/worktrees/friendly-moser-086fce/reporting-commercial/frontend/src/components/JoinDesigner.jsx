import { useState, useRef, useEffect, useCallback } from 'react'
import { X, Table2, GripVertical, Link2, Settings2 } from 'lucide-react'

const JOIN_TYPES = [
  { value: 'INNER JOIN', label: 'Inner', description: 'Retourne les lignes qui ont des correspondances dans les deux tables' },
  { value: 'LEFT JOIN', label: 'Left Outer', description: 'Retourne toutes les lignes de la table de gauche et les correspondances de droite' },
  { value: 'RIGHT JOIN', label: 'Right Outer', description: 'Retourne toutes les lignes de la table de droite et les correspondances de gauche' },
  { value: 'FULL JOIN', label: 'Full Outer', description: 'Retourne toutes les lignes quand il y a une correspondance dans l\'une des tables' }
]

const OPERATORS = [
  { value: '=', label: 'Equal to' },
  { value: '!=', label: 'Not equal to' },
  { value: '>', label: 'Greater than' },
  { value: '<', label: 'Less than' },
  { value: '>=', label: 'Greater than or equal' },
  { value: '<=', label: 'Less than or equal' }
]

export default function JoinDesigner({
  tables,
  joins,
  onJoinsChange,
  onColumnSelect,
  onTableRemove,
  onAllColumnsToggle
}) {
  const containerRef = useRef(null)
  const [tablePositions, setTablePositions] = useState({})
  const [draggingTable, setDraggingTable] = useState(null)
  const [draggingColumn, setDraggingColumn] = useState(null)
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 })
  const [selectedJoin, setSelectedJoin] = useState(null)
  const [showRelationPanel, setShowRelationPanel] = useState(false)
  const [dropTarget, setDropTarget] = useState(null)
  const [connectionLine, setConnectionLine] = useState(null)

  // Initialiser les positions des tables
  useEffect(() => {
    const newPositions = { ...tablePositions }
    let needsUpdate = false

    tables.forEach((table, index) => {
      if (!newPositions[table.name]) {
        needsUpdate = true
        newPositions[table.name] = {
          x: 50 + (index % 3) * 300,
          y: 50 + Math.floor(index / 3) * 350
        }
      }
    })

    // Supprimer les positions des tables qui n'existent plus
    Object.keys(newPositions).forEach(tableName => {
      if (!tables.find(t => t.name === tableName)) {
        delete newPositions[tableName]
        needsUpdate = true
      }
    })

    if (needsUpdate) {
      setTablePositions(newPositions)
    }
  }, [tables])

  // Déplacement de table
  const handleTableMouseDown = (e, tableName) => {
    if (e.target.closest('.column-item')) return

    e.preventDefault()
    const rect = e.currentTarget.getBoundingClientRect()
    setDragOffset({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top
    })
    setDraggingTable(tableName)
  }

  // Déplacement de colonne pour créer une jointure
  const handleColumnMouseDown = (e, table, column) => {
    e.preventDefault()
    e.stopPropagation()

    const rect = e.currentTarget.getBoundingClientRect()
    setDraggingColumn({
      table: table.name,
      column: column.name,
      type: column.type,
      startX: rect.right,
      startY: rect.top + rect.height / 2
    })
  }

  const handleMouseMove = useCallback((e) => {
    if (draggingTable) {
      const container = containerRef.current
      if (!container) return

      const containerRect = container.getBoundingClientRect()
      const newX = e.clientX - containerRect.left - dragOffset.x + container.scrollLeft
      const newY = e.clientY - containerRect.top - dragOffset.y + container.scrollTop

      setTablePositions(prev => ({
        ...prev,
        [draggingTable]: {
          x: Math.max(0, newX),
          y: Math.max(0, newY)
        }
      }))
    }

    if (draggingColumn) {
      const container = containerRef.current
      if (!container) return

      const containerRect = container.getBoundingClientRect()
      setConnectionLine({
        x1: draggingColumn.startX - containerRect.left + container.scrollLeft,
        y1: draggingColumn.startY - containerRect.top + container.scrollTop,
        x2: e.clientX - containerRect.left + container.scrollLeft,
        y2: e.clientY - containerRect.top + container.scrollTop
      })
    }
  }, [draggingTable, draggingColumn, dragOffset])

  const handleMouseUp = useCallback((e) => {
    if (draggingColumn && dropTarget) {
      // Créer une nouvelle jointure
      const existingJoin = joins.find(j =>
        (j.table1 === draggingColumn.table && j.table2 === dropTarget.table) ||
        (j.table2 === draggingColumn.table && j.table1 === dropTarget.table)
      )

      if (!existingJoin && draggingColumn.table !== dropTarget.table) {
        const newJoin = {
          type: 'INNER JOIN',
          table1: draggingColumn.table,
          column1: draggingColumn.column,
          table2: dropTarget.table,
          column2: dropTarget.column,
          operator: '='
        }
        onJoinsChange([...joins, newJoin])
        setSelectedJoin(joins.length)
        setShowRelationPanel(true)
      }
    }

    setDraggingTable(null)
    setDraggingColumn(null)
    setConnectionLine(null)
    setDropTarget(null)
  }, [draggingColumn, dropTarget, joins, onJoinsChange])

  const handleColumnMouseEnter = (table, column) => {
    if (draggingColumn && table.name !== draggingColumn.table) {
      setDropTarget({ table: table.name, column: column.name })
    }
  }

  const handleColumnMouseLeave = () => {
    setDropTarget(null)
  }

  useEffect(() => {
    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [handleMouseMove, handleMouseUp])

  // Calculer les lignes de connexion pour les jointures existantes
  const getJoinLines = () => {
    if (!containerRef.current) return []

    const lines = []
    const container = containerRef.current

    joins.forEach((join, index) => {
      const table1El = container.querySelector(`[data-table="${join.table1}"]`)
      const table2El = container.querySelector(`[data-table="${join.table2}"]`)
      const col1El = container.querySelector(`[data-column="${join.table1}.${join.column1}"]`)
      const col2El = container.querySelector(`[data-column="${join.table2}.${join.column2}"]`)

      if (table1El && table2El && col1El && col2El) {
        const containerRect = container.getBoundingClientRect()
        const col1Rect = col1El.getBoundingClientRect()
        const col2Rect = col2El.getBoundingClientRect()

        // Déterminer quel côté utiliser pour chaque table
        const table1Rect = table1El.getBoundingClientRect()
        const table2Rect = table2El.getBoundingClientRect()

        let x1, x2
        if (table1Rect.right < table2Rect.left) {
          // Table1 à gauche de Table2
          x1 = col1Rect.right - containerRect.left + container.scrollLeft
          x2 = col2Rect.left - containerRect.left + container.scrollLeft
        } else if (table2Rect.right < table1Rect.left) {
          // Table2 à gauche de Table1
          x1 = col1Rect.left - containerRect.left + container.scrollLeft
          x2 = col2Rect.right - containerRect.left + container.scrollLeft
        } else {
          // Tables qui se chevauchent
          x1 = col1Rect.right - containerRect.left + container.scrollLeft
          x2 = col2Rect.left - containerRect.left + container.scrollLeft
        }

        lines.push({
          index,
          x1,
          y1: col1Rect.top + col1Rect.height / 2 - containerRect.top + container.scrollTop,
          x2,
          y2: col2Rect.top + col2Rect.height / 2 - containerRect.top + container.scrollTop,
          join
        })
      }
    })

    return lines
  }

  const updateJoin = (index, field, value) => {
    const newJoins = joins.map((j, i) => i === index ? { ...j, [field]: value } : j)
    onJoinsChange(newJoins)
  }

  const removeJoin = (index) => {
    onJoinsChange(joins.filter((_, i) => i !== index))
    setSelectedJoin(null)
    setShowRelationPanel(false)
  }

  const handleLineClick = (index) => {
    setSelectedJoin(index)
    setShowRelationPanel(true)
  }

  const joinLines = getJoinLines()

  return (
    <div className="h-full flex">
      {/* Zone de design */}
      <div
        ref={containerRef}
        className="flex-1 relative overflow-auto bg-gray-100 dark:bg-gray-900"
        style={{
          backgroundImage: 'radial-gradient(circle, #d1d5db 1px, transparent 1px)',
          backgroundSize: '20px 20px'
        }}
      >
        {/* Instructions si pas de tables */}
        {tables.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center text-gray-500 dark:text-gray-400">
              <Table2 className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p className="text-lg font-medium">Aucune table sélectionnée</p>
              <p className="text-sm mt-1">Cliquez sur une table dans la liste à gauche pour l'ajouter</p>
            </div>
          </div>
        )}

        {/* SVG pour les lignes de connexion */}
        <svg
          className="absolute inset-0 pointer-events-none"
          style={{ width: '100%', height: '100%', minWidth: '2000px', minHeight: '1500px' }}
        >
          <defs>
            <marker
              id="arrowhead"
              markerWidth="10"
              markerHeight="7"
              refX="9"
              refY="3.5"
              orient="auto"
            >
              <polygon points="0 0, 10 3.5, 0 7" fill="#6366f1" />
            </marker>
          </defs>

          {/* Lignes de jointure existantes */}
          {joinLines.map((line, i) => {
            const isSelected = selectedJoin === line.index
            const midX = (line.x1 + line.x2) / 2

            return (
              <g key={i}>
                {/* Ligne invisible plus large pour faciliter le clic */}
                <path
                  d={`M ${line.x1} ${line.y1} C ${midX} ${line.y1}, ${midX} ${line.y2}, ${line.x2} ${line.y2}`}
                  fill="none"
                  stroke="transparent"
                  strokeWidth="20"
                  style={{ cursor: 'pointer', pointerEvents: 'stroke' }}
                  onClick={() => handleLineClick(line.index)}
                />
                {/* Ligne visible */}
                <path
                  d={`M ${line.x1} ${line.y1} C ${midX} ${line.y1}, ${midX} ${line.y2}, ${line.x2} ${line.y2}`}
                  fill="none"
                  stroke={isSelected ? '#6366f1' : '#94a3b8'}
                  strokeWidth={isSelected ? 3 : 2}
                  strokeDasharray={line.join.type.includes('LEFT') || line.join.type.includes('RIGHT') ? '5,5' : 'none'}
                />
                {/* Indicateur de type de jointure */}
                <g
                  transform={`translate(${midX - 20}, ${(line.y1 + line.y2) / 2 - 10})`}
                  style={{ cursor: 'pointer', pointerEvents: 'all' }}
                  onClick={() => handleLineClick(line.index)}
                >
                  <rect
                    x="0"
                    y="0"
                    width="40"
                    height="20"
                    rx="4"
                    fill={isSelected ? '#6366f1' : '#475569'}
                  />
                  <text
                    x="20"
                    y="14"
                    textAnchor="middle"
                    fill="white"
                    fontSize="10"
                    fontWeight="500"
                  >
                    {line.join.operator || '='}
                  </text>
                </g>
              </g>
            )
          })}

          {/* Ligne de connexion en cours de création */}
          {connectionLine && (
            <path
              d={`M ${connectionLine.x1} ${connectionLine.y1} L ${connectionLine.x2} ${connectionLine.y2}`}
              fill="none"
              stroke="#6366f1"
              strokeWidth="2"
              strokeDasharray="5,5"
            />
          )}
        </svg>

        {/* Tables */}
        {tables.map(table => {
          const pos = tablePositions[table.name] || { x: 50, y: 50 }

          return (
            <div
              key={table.name}
              data-table={table.name}
              className={`
                absolute bg-white dark:bg-gray-800 rounded-lg shadow-lg border-2
                ${draggingTable === table.name ? 'border-primary-500 shadow-xl z-50' : 'border-primary-300 dark:border-primary-600'}
                select-none
              `}
              style={{
                left: pos.x,
                top: pos.y,
                minWidth: '200px',
                maxWidth: '280px'
              }}
              onMouseDown={(e) => handleTableMouseDown(e, table.name)}
            >
              {/* Header de la table */}
              <div className="flex items-center gap-2 px-3 py-2 bg-gray-100 dark:bg-gray-700 rounded-t-lg border-b border-gray-200 dark:border-primary-600 cursor-move">
                <GripVertical className="w-4 h-4 text-gray-400 flex-shrink-0" />
                <Table2 className="w-4 h-4 text-primary-500 flex-shrink-0" />
                <span className="font-semibold text-sm text-gray-800 dark:text-white truncate flex-1">
                  {table.name}
                </span>
                {onTableRemove && (
                  <button
                    onMouseDown={(e) => e.stopPropagation()}
                    onClick={(e) => { e.stopPropagation(); onTableRemove(table.name) }}
                    className="flex-shrink-0 p-0.5 rounded hover:bg-red-100 dark:hover:bg-red-900/40 text-gray-400 hover:text-red-500"
                    title="Supprimer la table"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>

              {/* Checkbox * (All Columns) */}
              <div className="px-2 py-1 border-b border-gray-100 dark:border-gray-700">
                <label className="flex items-center gap-2 p-1 hover:bg-gray-50 dark:hover:bg-gray-700/50 rounded cursor-pointer">
                  <input
                    type="checkbox"
                    checked={!!table._selectedAll}
                    onChange={(e) => {
                      if (onAllColumnsToggle) {
                        onAllColumnsToggle(table.name, table.columns, e.target.checked)
                      }
                    }}
                    className="rounded border-primary-300 text-primary-500 focus:ring-primary-500"
                  />
                  <span className="text-xs text-gray-600 dark:text-gray-400 italic">* (All Columns)</span>
                </label>
              </div>

              {/* Liste des colonnes */}
              <div className="max-h-[250px] overflow-y-auto">
                {table.columns.map(col => {
                  const colKey = `${table.name}.${col.name}`
                  const isDropTarget = dropTarget?.table === table.name && dropTarget?.column === col.name
                  const isDragging = draggingColumn?.table === table.name && draggingColumn?.column === col.name
                  const isJoinColumn = joins.some(j =>
                    (j.table1 === table.name && j.column1 === col.name) ||
                    (j.table2 === table.name && j.column2 === col.name)
                  )

                  return (
                    <div
                      key={col.name}
                      data-column={colKey}
                      className={`
                        column-item flex items-center gap-2 px-2 py-1.5 text-sm cursor-grab
                        ${isDragging ? 'bg-primary-100 dark:bg-primary-900/30' : ''}
                        ${isDropTarget ? 'bg-green-100 dark:bg-green-900/30 ring-2 ring-green-500' : ''}
                        ${isJoinColumn ? 'bg-blue-50 dark:bg-blue-900/20' : ''}
                        hover:bg-gray-50 dark:hover:bg-gray-700/50
                      `}
                      onMouseDown={(e) => handleColumnMouseDown(e, table, col)}
                      onMouseEnter={() => handleColumnMouseEnter(table, col)}
                      onMouseLeave={handleColumnMouseLeave}
                    >
                      <input
                        type="checkbox"
                        checked={col._selected || false}
                        onChange={(e) => {
                          e.stopPropagation()
                          if (onColumnSelect) onColumnSelect(table.name, col, e.target.checked)
                        }}
                        onClick={(e) => e.stopPropagation()}
                        className="rounded border-primary-300 text-primary-500 focus:ring-primary-500"
                      />
                      {isJoinColumn && (
                        <Link2 className="w-3 h-3 text-blue-500 flex-shrink-0" />
                      )}
                      <span className={`
                        flex-1 truncate text-xs
                        ${isJoinColumn ? 'text-blue-600 dark:text-blue-400 font-medium' : 'text-gray-700 dark:text-gray-300'}
                      `}>
                        {col.name}
                      </span>
                      <span className="text-[10px] text-gray-400 px-1 py-0.5 bg-gray-100 dark:bg-gray-700 rounded">
                        {col.type?.split('(')[0] || 'var'}
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>
          )
        })}

        {/* Instructions de drag */}
        {tables.length > 0 && joins.length === 0 && (
          <div className="absolute bottom-4 left-4 bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-700 rounded-lg p-3 text-sm text-blue-700 dark:text-blue-300 max-w-xs">
            <p className="font-medium mb-1">Créer une jointure</p>
            <p className="text-xs">Faites glisser une colonne d'une table vers une colonne d'une autre table pour créer une relation.</p>
          </div>
        )}
      </div>

      {/* Panneau Relation Properties */}
      {showRelationPanel && selectedJoin !== null && joins[selectedJoin] && (
        <div className="w-72 border-l border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 flex flex-col">
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center gap-2">
              <Settings2 className="w-4 h-4 text-primary-500" />
              <span className="font-semibold text-sm">Relation Properties</span>
            </div>
            <button
              onClick={() => {
                setShowRelationPanel(false)
                setSelectedJoin(null)
              }}
              className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {/* Tables impliquées */}
            <div className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <Table2 className="w-4 h-4 text-gray-500" />
                  <span className="font-medium">{joins[selectedJoin].table1}</span>
                </div>
                <Link2 className="w-4 h-4 text-primary-500" />
                <div className="flex items-center gap-2">
                  <span className="font-medium">{joins[selectedJoin].table2}</span>
                  <Table2 className="w-4 h-4 text-gray-500" />
                </div>
              </div>
              <div className="flex items-center justify-between text-xs text-gray-500 mt-1">
                <span>{joins[selectedJoin].column1}</span>
                <span>{joins[selectedJoin].operator || '='}</span>
                <span>{joins[selectedJoin].column2}</span>
              </div>
            </div>

            {/* Type de jointure */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Join Type
              </label>
              <div className="space-y-2">
                {JOIN_TYPES.map(jt => (
                  <label
                    key={jt.value}
                    className={`
                      flex items-start gap-3 p-2 rounded-lg cursor-pointer border
                      ${joins[selectedJoin].type === jt.value
                        ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                        : 'border-gray-200 dark:border-primary-600 hover:bg-gray-50 dark:hover:bg-gray-700/50'}
                    `}
                  >
                    <input
                      type="radio"
                      name="joinType"
                      value={jt.value}
                      checked={joins[selectedJoin].type === jt.value}
                      onChange={(e) => updateJoin(selectedJoin, 'type', e.target.value)}
                      className="mt-0.5 text-primary-500 focus:ring-primary-500"
                    />
                    <div>
                      <span className="block text-sm font-medium text-gray-800 dark:text-white">
                        {jt.label}
                      </span>
                      <span className="block text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                        {jt.description}
                      </span>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            {/* Opérateur */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Operator
              </label>
              <select
                value={joins[selectedJoin].operator || '='}
                onChange={(e) => updateJoin(selectedJoin, 'operator', e.target.value)}
                className="w-full px-3 py-2 text-sm border border-primary-300 dark:border-primary-600 rounded-lg dark:bg-gray-700"
              >
                {OPERATORS.map(op => (
                  <option key={op.value} value={op.value}>{op.label}</option>
                ))}
              </select>
            </div>

            {/* Colonnes */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Left Column ({joins[selectedJoin].table1})
              </label>
              <select
                value={joins[selectedJoin].column1}
                onChange={(e) => updateJoin(selectedJoin, 'column1', e.target.value)}
                className="w-full px-3 py-2 text-sm border border-primary-300 dark:border-primary-600 rounded-lg dark:bg-gray-700"
              >
                {tables.find(t => t.name === joins[selectedJoin].table1)?.columns.map(c => (
                  <option key={c.name} value={c.name}>{c.name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Right Column ({joins[selectedJoin].table2})
              </label>
              <select
                value={joins[selectedJoin].column2}
                onChange={(e) => updateJoin(selectedJoin, 'column2', e.target.value)}
                className="w-full px-3 py-2 text-sm border border-primary-300 dark:border-primary-600 rounded-lg dark:bg-gray-700"
              >
                {tables.find(t => t.name === joins[selectedJoin].table2)?.columns.map(c => (
                  <option key={c.name} value={c.name}>{c.name}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Actions */}
          <div className="p-4 border-t border-gray-200 dark:border-gray-700">
            <button
              onClick={() => removeJoin(selectedJoin)}
              className="w-full px-4 py-2 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800"
            >
              Supprimer la relation
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
