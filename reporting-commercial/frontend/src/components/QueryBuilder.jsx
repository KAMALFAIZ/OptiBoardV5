import { useState, useEffect } from 'react'
import {
  X, Database, Table2, Columns, Plus, Trash2, Play, Save, Search,
  Link2, Filter, SortAsc, SortDesc, ChevronRight, ChevronDown, Eye, Code, RefreshCw, Settings2, Layout
} from 'lucide-react'
import {
  getQueryBuilderTables, getTableColumns, previewBuilderQuery, createDataSource, getDataSource,
  extractErrorMessage
} from '../services/api'
import JoinDesigner from './JoinDesigner'

const AGGREGATES = ['', 'SUM', 'COUNT', 'AVG', 'MIN', 'MAX']
const JOIN_TYPES = ['INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'FULL JOIN']
const OPERATORS = ['=', '!=', '>', '<', '>=', '<=', 'LIKE', 'IN', 'IS NULL', 'IS NOT NULL']
const PARAM_TYPES = ['date', 'text', 'number', 'select', 'multiselect']
const PARAM_SOURCES = ['manual', 'societe', 'annee', 'mois']

export default function QueryBuilder({ isOpen, onClose, onSave, targetType = 'pivot', initialSourceId = null }) {
  const [tables, setTables] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [initializing, setInitializing] = useState(false)

  // Configuration de la requête
  const [selectedTables, setSelectedTables] = useState([])
  const [joins, setJoins] = useState([])
  const [selectedColumns, setSelectedColumns] = useState([])
  const [whereConditions, setWhereConditions] = useState([])
  const [groupByColumns, setGroupByColumns] = useState([])
  const [orderByColumns, setOrderByColumns] = useState([])
  const [parameters, setParameters] = useState([]) // Paramètres personnalisés

  // Résultats
  const [generatedQuery, setGeneratedQuery] = useState('')
  const [previewData, setPreviewData] = useState([])
  const [previewColumns, setPreviewColumns] = useState([])
  const [showPreview, setShowPreview] = useState(false)
  const [executing, setExecuting] = useState(false)
  const [error, setError] = useState('')

  // Modal pour sauvegarder
  const [showSaveModal, setShowSaveModal] = useState(false)
  const [sourceName, setSourceName] = useState('')
  const [sourceDescription, setSourceDescription] = useState('')
  const [saving, setSaving] = useState(false)

  // Vue active
  const [activeTab, setActiveTab] = useState('tables') // tables, columns, joins, where, query

  // Reset l'état quand le modal se ferme
  useEffect(() => {
    if (!isOpen) {
      // Réinitialiser l'état quand le modal se ferme
      setSelectedTables([])
      setSelectedColumns([])
      setJoins([])
      setWhereConditions([])
      setOrderByColumns([])
      setParameters([])
      setGeneratedQuery('')
      setPreviewData([])
      setPreviewColumns([])
      setShowPreview(false)
      setError('')
      setSourceName('')
      setSourceDescription('')
      setActiveTab('tables')
      setInitializing(false)
    } else {
      loadTables()
    }
  }, [isOpen])

  // Charger automatiquement depuis une source existante
  useEffect(() => {
    if (isOpen && initialSourceId && tables.length > 0 && !initializing && selectedTables.length === 0) {
      loadFromDataSource(initialSourceId)
    }
  }, [isOpen, initialSourceId, tables.length])

  useEffect(() => {
    // Ne générer la requête que si on a au moins une table sélectionnée
    if (selectedTables.length > 0) {
      generateQuery()
    }
  }, [selectedTables, selectedColumns, joins, whereConditions, groupByColumns, orderByColumns])

  const loadTables = async () => {
    setLoading(true)
    try {
      const response = await getQueryBuilderTables()
      setTables(response.data.tables || [])
    } catch (err) {
      console.error('Erreur chargement tables:', err)
    } finally {
      setLoading(false)
    }
  }

  const loadTableColumns = async (tableName) => {
    try {
      const response = await getTableColumns(tableName)
      return response.data.columns || []
    } catch (err) {
      console.error('Erreur chargement colonnes:', err)
      return []
    }
  }

  // Charger depuis une source de données existante - approche simplifiée
  const loadFromDataSource = async (sourceId) => {
    setInitializing(true)
    try {
      const response = await getDataSource(sourceId)
      if (response.data.success && response.data.data) {
        const source = response.data.data
        const query = source.query_template || ''

        // Extraire uniquement le nom de la table principale depuis FROM
        const tableMatch = query.match(/FROM\s+\[?(\w+)\]?/i)
        if (tableMatch) {
          const tableName = tableMatch[1]

          // Charger les colonnes de la table
          const columns = await loadTableColumns(tableName)

          if (columns.length > 0) {
            // Ajouter la table
            const loadedTable = {
              name: tableName,
              alias: tableName,
              columns: columns,
              expanded: true
            }
            setSelectedTables([loadedTable])

            // Sélectionner toutes les colonnes automatiquement
            const allCols = columns.map(col => ({
              key: `${tableName}.${col.name}`,
              table: tableName,
              name: col.name,
              type: col.type,
              alias: '',
              aggregate: '',
              groupBy: false
            }))
            setSelectedColumns(allCols)

            // Parser les conditions WHERE
            const parsedConditions = parseWhereConditions(query)

            // Extraire les paramètres des conditions WHERE
            const extractedParams = extractParametersFromConditions(parsedConditions)

            // Utiliser un setTimeout pour s'assurer que React a fini de batching les états
            setTimeout(() => {
              if (parsedConditions.length > 0) {
                setWhereConditions(parsedConditions)
                setParameters(extractedParams)
                setActiveTab('where')
              } else {
                setActiveTab('columns')
              }
            }, 100)
          }
        }

        // Pré-remplir le nom de la source
        setSourceName(source.nom || '')
        setSourceDescription(source.description || '')

        // Charger les paramètres existants de la source
        if (source.parameters) {
          let loadedParams = []
          // Le backend stocke les paramètres comme une liste
          if (Array.isArray(source.parameters)) {
            loadedParams = source.parameters.map(p => ({
              name: p.name,
              label: p.label || p.name.replace('@', ''),
              type: p.type || 'text',
              source: p.source || 'manual',
              defaultValue: p.default || p.defaultValue || '',
              required: p.required !== false
            }))
          } else if (typeof source.parameters === 'object') {
            // Compatibilité avec l'ancien format objet
            loadedParams = Object.entries(source.parameters).map(([name, config]) => ({
              name,
              label: config.label || name.replace('@', ''),
              type: config.type || 'text',
              source: config.source || 'manual',
              defaultValue: config.default || config.defaultValue || '',
              required: config.required !== false
            }))
          }
          if (loadedParams.length > 0) {
            setTimeout(() => setParameters(loadedParams), 150)
          }
        }
      }
    } catch (err) {
      console.error('Erreur chargement source:', err)
    } finally {
      setInitializing(false)
    }
  }

  // Extraire les paramètres (@param) des conditions WHERE
  const extractParametersFromConditions = (conditions) => {
    const params = []
    const seen = new Set()

    conditions.forEach(cond => {
      if (cond.value && cond.value.startsWith('@')) {
        const paramName = cond.value
        if (!seen.has(paramName)) {
          seen.add(paramName)
          // Deviner le type en fonction du nom
          let type = 'text'
          let source = 'manual'
          const lowerName = paramName.toLowerCase()
          if (lowerName.includes('date') || lowerName.includes('du') || lowerName.includes('au')) {
            type = 'date'
          } else if (lowerName.includes('annee') || lowerName.includes('year')) {
            type = 'number'
            source = 'annee'
          } else if (lowerName.includes('mois') || lowerName.includes('month')) {
            type = 'number'
            source = 'mois'
          } else if (lowerName.includes('societe') || lowerName.includes('soc')) {
            type = 'text'
            source = 'societe'
          }

          params.push({
            name: paramName,
            label: paramName.replace('@', '').replace(/([A-Z])/g, ' $1').trim(),
            type,
            source,
            defaultValue: '',
            required: true
          })
        }
      }
    })

    return params
  }

  // Parser les conditions WHERE d'une requête SQL
  const parseWhereConditions = (query) => {
    const conditions = []

    // Extraire la partie WHERE
    const whereMatch = query.match(/WHERE\s+(.+?)(?:GROUP BY|ORDER BY|$)/is)
    if (!whereMatch) return conditions

    let wherePart = whereMatch[1].trim()

    // Gérer BETWEEN en le convertissant en deux conditions >= et <=
    // [col] BETWEEN @val1 AND @val2 => [col] >= @val1 AND [col] <= @val2
    const betweenRegex = /\[([^\]]+)\]\s+BETWEEN\s+(@?\w+)\s+AND\s+(@?\w+)/gi
    let betweenMatch
    while ((betweenMatch = betweenRegex.exec(wherePart)) !== null) {
      const colName = betweenMatch[1]
      const val1 = betweenMatch[2]
      const val2 = betweenMatch[3]
      // Remplacer BETWEEN par deux conditions
      wherePart = wherePart.replace(
        betweenMatch[0],
        `[${colName}] >= ${val1} AND [${colName}] <= ${val2}`
      )
    }

    // Séparer par AND/OR (en gardant le connecteur)
    const parts = wherePart.split(/\s+(AND|OR)\s+/i)

    let currentConnector = 'AND'
    for (let i = 0; i < parts.length; i++) {
      const part = parts[i].trim()

      // Si c'est un connecteur (AND/OR), le sauvegarder pour la prochaine condition
      if (part.toUpperCase() === 'AND' || part.toUpperCase() === 'OR') {
        currentConnector = part.toUpperCase()
        continue
      }

      if (!part) continue

      // Parser la condition: [colonne] opérateur valeur
      // Patterns supportés: >=, <=, !=, =, >, <, LIKE, IN, IS NULL, IS NOT NULL
      // Note: les noms de colonnes peuvent contenir des espaces et être entre crochets [Col Name]

      // IS NULL / IS NOT NULL
      const isNullMatch = part.match(/\[([^\]]+)\]\s+(IS\s+(?:NOT\s+)?NULL)/i) || part.match(/(\w+)\s+(IS\s+(?:NOT\s+)?NULL)/i)
      if (isNullMatch) {
        conditions.push({
          column: isNullMatch[1],
          operator: isNullMatch[2].toUpperCase().replace(/\s+/g, ' '),
          value: '',
          connector: conditions.length === 0 ? 'AND' : currentConnector
        })
        continue
      }

      // LIKE - avec support des noms entre crochets
      const likeMatch = part.match(/\[([^\]]+)\]\s+LIKE\s+[%']*([@\w]+)[%']*/i) || part.match(/(\w+)\s+LIKE\s+[%']*([@\w]+)[%']*/i)
      if (likeMatch) {
        conditions.push({
          column: likeMatch[1],
          operator: 'LIKE',
          value: likeMatch[2],
          connector: conditions.length === 0 ? 'AND' : currentConnector
        })
        continue
      }

      // IN - avec support des noms entre crochets
      const inMatch = part.match(/\[([^\]]+)\]\s+IN\s*\((.+)\)/i) || part.match(/(\w+)\s+IN\s*\((.+)\)/i)
      if (inMatch) {
        conditions.push({
          column: inMatch[1],
          operator: 'IN',
          value: inMatch[2],
          connector: conditions.length === 0 ? 'AND' : currentConnector
        })
        continue
      }

      // Opérateurs de comparaison: >=, <=, !=, =, >, <
      // Avec support des noms entre crochets, préfixes de table, et des valeurs de paramètres @xxx
      // Format: [table].[colonne] ou [colonne] ou colonne
      const compMatch =
        // Format [table].[colonne] >= @value
        part.match(/(?:\[[^\]]+\]\.)?\[([^\]]+)\]\s*(>=|<=|!=|=|>|<)\s*'?(@[\w]+|\d+|[\w]+)'?/i) ||
        // Format table.colonne >= @value
        part.match(/(?:\w+\.)?(\w+)\s*(>=|<=|!=|=|>|<)\s*'?(@[\w]+|\d+|[\w]+)'?/i)
      if (compMatch) {
        conditions.push({
          column: compMatch[1],
          operator: compMatch[2],
          value: compMatch[3],
          connector: conditions.length === 0 ? 'AND' : currentConnector
        })
        continue
      }
    }

    return conditions
  }

  const addTable = async (tableName) => {
    if (selectedTables.find(t => t.name === tableName)) return

    const columns = await loadTableColumns(tableName)
    const newTable = {
      name: tableName,
      alias: tableName,
      columns: columns,
      expanded: true
    }
    setSelectedTables([...selectedTables, newTable])
  }

  const removeTable = (tableName) => {
    setSelectedTables(selectedTables.filter(t => t.name !== tableName))
    setSelectedColumns(selectedColumns.filter(c => c.table !== tableName))
    setJoins(joins.filter(j => j.table1 !== tableName && j.table2 !== tableName))
  }

  const toggleColumn = (table, column) => {
    const key = `${table}.${column.name}`
    const existing = selectedColumns.find(c => c.key === key)

    if (existing) {
      setSelectedColumns(selectedColumns.filter(c => c.key !== key))
    } else {
      setSelectedColumns([...selectedColumns, {
        key,
        table,
        name: column.name,
        type: column.type,
        alias: '',
        aggregate: '',
        groupBy: false
      }])
    }
  }

  const updateColumn = (key, field, value) => {
    setSelectedColumns(selectedColumns.map(c =>
      c.key === key ? { ...c, [field]: value } : c
    ))
  }

  const addJoin = () => {
    if (selectedTables.length < 2) return
    setJoins([...joins, {
      type: 'INNER JOIN',
      table1: selectedTables[0].name,
      column1: '',
      table2: selectedTables[1]?.name || '',
      column2: ''
    }])
  }

  const updateJoin = (index, field, value) => {
    setJoins(joins.map((j, i) => i === index ? { ...j, [field]: value } : j))
  }

  const removeJoin = (index) => {
    setJoins(joins.filter((_, i) => i !== index))
  }

  const addWhereCondition = () => {
    setWhereConditions([...whereConditions, {
      column: '',
      operator: '=',
      value: '',
      connector: 'AND'
    }])
  }

  const updateWhere = (index, field, value) => {
    setWhereConditions(whereConditions.map((w, i) => i === index ? { ...w, [field]: value } : w))
  }

  const removeWhere = (index) => {
    setWhereConditions(whereConditions.filter((_, i) => i !== index))
  }

  const addParameter = () => {
    setParameters([...parameters, {
      name: '@param' + (parameters.length + 1),
      label: 'Paramètre ' + (parameters.length + 1),
      type: 'text',
      source: 'manual',
      defaultValue: '',
      required: true
    }])
  }

  const updateParameter = (index, field, value) => {
    setParameters(parameters.map((p, i) => i === index ? { ...p, [field]: value } : p))
  }

  const removeParameter = (index) => {
    setParameters(parameters.filter((_, i) => i !== index))
  }

  const toggleOrderBy = (column, direction) => {
    const existing = orderByColumns.find(o => o.column === column)
    if (existing) {
      if (existing.direction === direction) {
        setOrderByColumns(orderByColumns.filter(o => o.column !== column))
      } else {
        setOrderByColumns(orderByColumns.map(o =>
          o.column === column ? { ...o, direction } : o
        ))
      }
    } else {
      setOrderByColumns([...orderByColumns, { column, direction }])
    }
  }

  const generateQuery = () => {
    if (selectedTables.length === 0) {
      setGeneratedQuery('')
      return
    }

    // SELECT
    let selectParts = []
    const hasAggregates = selectedColumns.some(c => c.aggregate)
    const groupByCols = []

    if (selectedColumns.length === 0) {
      selectParts.push('*')
    } else {
      selectedColumns.forEach(col => {
        const colRef = `[${col.table}].[${col.name}]`
        if (col.aggregate) {
          const alias = col.alias || `${col.aggregate}_${col.name}`
          selectParts.push(`${col.aggregate}(${colRef}) AS [${alias}]`)
        } else {
          if (col.alias) {
            selectParts.push(`${colRef} AS [${col.alias}]`)
          } else {
            selectParts.push(colRef)
          }
          if (hasAggregates) {
            groupByCols.push(colRef)
          }
        }
      })
    }

    // FROM
    const fromTable = selectedTables[0]
    let query = `SELECT TOP 1000 ${selectParts.join(',\n       ')}\nFROM [${fromTable.name}] AS [${fromTable.alias}]`

    // JOINS
    joins.forEach(join => {
      if (join.column1 && join.column2) {
        query += `\n${join.type} [${join.table2}] ON [${join.table1}].[${join.column1}] = [${join.table2}].[${join.column2}]`
      }
    })

    // WHERE
    if (whereConditions.length > 0) {
      const whereParts = whereConditions.map((w, i) => {
        if (!w.column) return ''
        let clause = ''
        if (w.operator === 'IS NULL' || w.operator === 'IS NOT NULL') {
          clause = `[${w.column}] ${w.operator}`
        } else if (w.operator === 'LIKE') {
          // Si la valeur est un paramètre (@xxx), ne pas ajouter les %
          if (w.value.startsWith('@')) {
            clause = `[${w.column}] LIKE ${w.value}`
          } else {
            clause = `[${w.column}] LIKE '%${w.value}%'`
          }
        } else if (w.operator === 'IN') {
          clause = `[${w.column}] IN (${w.value})`
        } else {
          // Si la valeur est un paramètre (@xxx), ne pas ajouter de guillemets
          let val
          if (w.value.startsWith('@')) {
            val = w.value  // Paramètre SQL, garder tel quel
          } else if (!isNaN(w.value) && w.value.trim() !== '') {
            val = w.value  // Nombre
          } else {
            val = `'${w.value}'`  // Chaîne de caractères
          }
          clause = `[${w.column}] ${w.operator} ${val}`
        }
        return i === 0 ? clause : `${w.connector} ${clause}`
      }).filter(Boolean)

      if (whereParts.length > 0) {
        query += `\nWHERE ${whereParts.join('\n      ')}`
      }
    }

    // GROUP BY
    if (groupByCols.length > 0) {
      query += `\nGROUP BY ${groupByCols.join(', ')}`
    }

    // ORDER BY
    if (orderByColumns.length > 0) {
      const orderParts = orderByColumns.map(o => `[${o.column}] ${o.direction}`)
      query += `\nORDER BY ${orderParts.join(', ')}`
    }

    setGeneratedQuery(query)
  }

  const executePreview = async () => {
    if (!generatedQuery) return

    setExecuting(true)
    setError('')
    try {
      const response = await previewBuilderQuery(generatedQuery)
      if (response.data.success) {
        setPreviewData(response.data.data || [])
        setPreviewColumns(response.data.columns || [])
        setShowPreview(true)
      } else {
        setError(response.data.error || 'Erreur lors de l\'exécution')
      }
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setExecuting(false)
    }
  }

  const handleSave = async () => {
    if (!sourceName.trim() || !generatedQuery) return

    setSaving(true)
    try {
      // Construire la liste des parameters (le backend attend une liste)
      const paramsList = parameters.map(p => ({
        name: p.name,
        label: p.label,
        type: p.type,
        source: p.source,
        default: p.defaultValue,
        required: p.required
      }))

      const response = await createDataSource({
        nom: sourceName,
        type: 'query',
        description: sourceDescription,
        query_template: generatedQuery,
        parameters: paramsList
      })

      if (response.data.success) {
        const newSourceId = response.data.id
        setShowSaveModal(false)
        onSave && onSave(newSourceId, sourceName)
        onClose()
      }
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  const filteredTables = tables.filter(t =>
    t.name.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const allColumns = selectedTables.flatMap(t =>
    t.columns.map(c => ({ ...c, table: t.name, fullName: `${t.name}.${c.name}` }))
  )

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />

      <div className="relative bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-[95vw] h-[90vh] max-w-7xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <Database className="w-5 h-5 text-primary-500" />
            <h2 className="text-lg font-bold text-gray-900 dark:text-white">
              Query Builder
            </h2>
            <span className="text-sm text-gray-500">
              → {targetType === 'pivot' ? 'Pivot Table' : 'GridView'}
            </span>
            {initializing && (
              <span className="flex items-center gap-1 text-sm text-primary-500">
                <RefreshCw className="w-4 h-4 animate-spin" />
                Chargement de la source...
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={executePreview}
              disabled={!generatedQuery || executing}
              className="btn-secondary flex items-center gap-1 text-sm"
            >
              <Play className="w-4 h-4" />
              {executing ? 'Exécution...' : 'Aperçu'}
            </button>
            <button
              onClick={() => setShowSaveModal(true)}
              disabled={!generatedQuery}
              className="btn-primary flex items-center gap-1 text-sm"
            >
              <Save className="w-4 h-4" />
              Créer Source
            </button>
            <button onClick={onClose} className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg">
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Contenu principal */}
        <div className="flex-1 flex overflow-hidden">
          {/* Panneau gauche - Tables */}
          <div className="w-64 border-r border-gray-200 dark:border-gray-700 flex flex-col">
            <div className="p-2 border-b border-gray-200 dark:border-gray-700">
              <div className="relative">
                <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Rechercher table..."
                  className="w-full pl-8 pr-3 py-1.5 text-sm border border-primary-300 dark:border-primary-600 rounded-md dark:bg-gray-700"
                />
              </div>
            </div>
            <div className="flex-1 overflow-y-auto p-2">
              {loading ? (
                <p className="text-sm text-gray-500 text-center py-4">Chargement...</p>
              ) : (
                <div className="space-y-1">
                  {filteredTables.map(table => (
                    <div
                      key={table.name}
                      onClick={() => addTable(table.name)}
                      className={`
                        flex items-center gap-2 p-2 rounded-lg cursor-pointer text-sm
                        ${selectedTables.find(t => t.name === table.name)
                          ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700'
                          : 'hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300'
                        }
                      `}
                    >
                      <Table2 className="w-4 h-4 flex-shrink-0" />
                      <span className="truncate">{table.name}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Zone centrale - Configuration */}
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Tabs */}
            <div className="flex border-b border-gray-200 dark:border-gray-700 px-4">
              {[
                { id: 'tables', label: 'Tables', icon: Table2 },
                { id: 'visual', label: 'Visuel', icon: Layout },
                { id: 'columns', label: 'Colonnes', icon: Columns },
                { id: 'joins', label: 'Jointures', icon: Link2 },
                { id: 'where', label: 'Filtres', icon: Filter },
                { id: 'params', label: 'Paramètres', icon: Settings2, badge: parameters.length },
                { id: 'query', label: 'SQL', icon: Code }
              ].map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`
                    flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 -mb-px
                    ${activeTab === tab.id
                      ? 'border-primary-500 text-primary-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                    }
                  `}
                >
                  <tab.icon className="w-4 h-4" />
                  {tab.label}
                  {tab.badge > 0 && (
                    <span className="ml-1 px-1.5 py-0.5 text-[10px] bg-primary-100 text-primary-600 rounded-full">
                      {tab.badge}
                    </span>
                  )}
                </button>
              ))}
            </div>

            {/* Contenu des tabs */}
            <div className="flex-1 overflow-auto p-4">
              {/* Tab Tables */}
              {activeTab === 'tables' && (
                <div className="space-y-4">
                  <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                    Tables sélectionnées ({selectedTables.length})
                  </h3>
                  {selectedTables.length === 0 ? (
                    <p className="text-sm text-gray-500">Cliquez sur une table à gauche pour l'ajouter</p>
                  ) : (
                    <div className="space-y-2">
                      {selectedTables.map(table => (
                        <div key={table.name} className="border border-gray-200 dark:border-gray-700 rounded-lg">
                          <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/50">
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => setSelectedTables(selectedTables.map(t =>
                                  t.name === table.name ? { ...t, expanded: !t.expanded } : t
                                ))}
                              >
                                {table.expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                              </button>
                              <Table2 className="w-4 h-4 text-primary-500" />
                              <span className="font-medium">{table.name}</span>
                              <span className="text-xs text-gray-500">({table.columns.length} colonnes)</span>
                            </div>
                            <button
                              onClick={() => removeTable(table.name)}
                              className="p-1 hover:bg-red-100 dark:hover:bg-red-900/30 rounded text-red-500"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                          {table.expanded && (
                            <div className="p-2 grid grid-cols-3 gap-1 max-h-48 overflow-y-auto">
                              {table.columns.map(col => {
                                const isSelected = selectedColumns.find(c => c.key === `${table.name}.${col.name}`)
                                return (
                                  <div
                                    key={col.name}
                                    onClick={() => toggleColumn(table.name, col)}
                                    className={`
                                      flex items-center gap-1.5 p-1.5 rounded text-xs cursor-pointer
                                      ${isSelected
                                        ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700'
                                        : 'hover:bg-gray-100 dark:hover:bg-gray-700'
                                      }
                                    `}
                                  >
                                    <span className={`w-4 h-4 rounded flex items-center justify-center text-[9px] font-bold
                                      ${['int', 'bigint', 'decimal', 'float', 'money', 'numeric'].includes(col.type)
                                        ? 'bg-purple-100 text-purple-600' : 'bg-blue-100 text-blue-600'}`}>
                                      {['int', 'bigint', 'decimal', 'float', 'money', 'numeric'].includes(col.type) ? '#' : 'T'}
                                    </span>
                                    <span className="truncate">{col.name}</span>
                                  </div>
                                )
                              })}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Tab Visuel - Designer de jointures */}
              {activeTab === 'visual' && (
                <div className="h-full -m-4">
                  <JoinDesigner
                    tables={selectedTables.map(table => ({
                      ...table,
                      columns: table.columns.map(col => ({
                        ...col,
                        _selected: selectedColumns.some(sc => sc.key === `${table.name}.${col.name}`)
                      })),
                      _selectedAll: table.columns.every(col =>
                        selectedColumns.some(sc => sc.key === `${table.name}.${col.name}`)
                      )
                    }))}
                    joins={joins}
                    onJoinsChange={setJoins}
                    onColumnSelect={(tableName, column, isSelected) => {
                      const key = `${tableName}.${column.name}`
                      if (isSelected) {
                        if (!selectedColumns.find(c => c.key === key)) {
                          setSelectedColumns([...selectedColumns, {
                            key,
                            table: tableName,
                            name: column.name,
                            type: column.type,
                            alias: '',
                            aggregate: '',
                            groupBy: false
                          }])
                        }
                      } else {
                        setSelectedColumns(selectedColumns.filter(c => c.key !== key))
                      }
                    }}
                  />
                </div>
              )}

              {/* Tab Colonnes */}
              {activeTab === 'columns' && (
                <div className="space-y-4">
                  <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                    Colonnes de sortie ({selectedColumns.length})
                  </h3>
                  {selectedColumns.length === 0 ? (
                    <p className="text-sm text-gray-500">Sélectionnez des colonnes dans l'onglet Tables</p>
                  ) : (
                    <table className="w-full text-sm">
                      <thead className="bg-gray-50 dark:bg-gray-700">
                        <tr>
                          <th className="px-3 py-2 text-left">Colonne</th>
                          <th className="px-3 py-2 text-left">Alias</th>
                          <th className="px-3 py-2 text-left">Agrégation</th>
                          <th className="px-3 py-2 text-left">Tri</th>
                          <th className="px-3 py-2 w-10"></th>
                        </tr>
                      </thead>
                      <tbody>
                        {selectedColumns.map(col => (
                          <tr key={col.key} className="border-b border-gray-100 dark:border-gray-700">
                            <td className="px-3 py-2">
                              <span className="font-mono text-xs">{col.table}.{col.name}</span>
                            </td>
                            <td className="px-3 py-2">
                              <input
                                type="text"
                                value={col.alias}
                                onChange={(e) => updateColumn(col.key, 'alias', e.target.value)}
                                placeholder="Alias..."
                                className="w-full px-2 py-1 text-xs border border-primary-300 dark:border-primary-600 rounded dark:bg-gray-700"
                              />
                            </td>
                            <td className="px-3 py-2">
                              <select
                                value={col.aggregate}
                                onChange={(e) => updateColumn(col.key, 'aggregate', e.target.value)}
                                className="px-2 py-1 text-xs border border-primary-300 dark:border-primary-600 rounded dark:bg-gray-700"
                              >
                                {AGGREGATES.map(agg => (
                                  <option key={agg} value={agg}>{agg || '(aucune)'}</option>
                                ))}
                              </select>
                            </td>
                            <td className="px-3 py-2">
                              <div className="flex gap-1">
                                <button
                                  onClick={() => toggleOrderBy(col.name, 'ASC')}
                                  className={`p-1 rounded ${orderByColumns.find(o => o.column === col.name && o.direction === 'ASC')
                                    ? 'bg-primary-100 text-primary-600' : 'hover:bg-gray-100'}`}
                                >
                                  <SortAsc className="w-4 h-4" />
                                </button>
                                <button
                                  onClick={() => toggleOrderBy(col.name, 'DESC')}
                                  className={`p-1 rounded ${orderByColumns.find(o => o.column === col.name && o.direction === 'DESC')
                                    ? 'bg-primary-100 text-primary-600' : 'hover:bg-gray-100'}`}
                                >
                                  <SortDesc className="w-4 h-4" />
                                </button>
                              </div>
                            </td>
                            <td className="px-3 py-2">
                              <button
                                onClick={() => setSelectedColumns(selectedColumns.filter(c => c.key !== col.key))}
                                className="p-1 hover:bg-red-100 rounded text-red-500"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              )}

              {/* Tab Jointures */}
              {activeTab === 'joins' && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                      Jointures ({joins.length})
                    </h3>
                    <button
                      onClick={addJoin}
                      disabled={selectedTables.length < 2}
                      className="btn-secondary text-xs flex items-center gap-1"
                    >
                      <Plus className="w-3 h-3" />
                      Ajouter jointure
                    </button>
                  </div>
                  {joins.length === 0 ? (
                    <p className="text-sm text-gray-500">
                      {selectedTables.length < 2
                        ? 'Sélectionnez au moins 2 tables pour créer une jointure'
                        : 'Cliquez sur "Ajouter jointure" pour lier les tables'}
                    </p>
                  ) : (
                    <div className="space-y-3">
                      {joins.map((join, i) => (
                        <div key={i} className="flex items-center gap-2 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                          <select
                            value={join.table1}
                            onChange={(e) => updateJoin(i, 'table1', e.target.value)}
                            className="px-2 py-1.5 text-sm border border-primary-300 dark:border-primary-600 rounded dark:bg-gray-700"
                          >
                            {selectedTables.map(t => (
                              <option key={t.name} value={t.name}>{t.name}</option>
                            ))}
                          </select>
                          <select
                            value={join.column1}
                            onChange={(e) => updateJoin(i, 'column1', e.target.value)}
                            className="px-2 py-1.5 text-sm border border-primary-300 dark:border-primary-600 rounded dark:bg-gray-700"
                          >
                            <option value="">-- Colonne --</option>
                            {selectedTables.find(t => t.name === join.table1)?.columns.map(c => (
                              <option key={c.name} value={c.name}>{c.name}</option>
                            ))}
                          </select>
                          <select
                            value={join.type}
                            onChange={(e) => updateJoin(i, 'type', e.target.value)}
                            className="px-2 py-1.5 text-sm border border-primary-300 dark:border-primary-600 rounded dark:bg-gray-700 font-mono"
                          >
                            {JOIN_TYPES.map(jt => (
                              <option key={jt} value={jt}>{jt}</option>
                            ))}
                          </select>
                          <select
                            value={join.table2}
                            onChange={(e) => updateJoin(i, 'table2', e.target.value)}
                            className="px-2 py-1.5 text-sm border border-primary-300 dark:border-primary-600 rounded dark:bg-gray-700"
                          >
                            {selectedTables.filter(t => t.name !== join.table1).map(t => (
                              <option key={t.name} value={t.name}>{t.name}</option>
                            ))}
                          </select>
                          <select
                            value={join.column2}
                            onChange={(e) => updateJoin(i, 'column2', e.target.value)}
                            className="px-2 py-1.5 text-sm border border-primary-300 dark:border-primary-600 rounded dark:bg-gray-700"
                          >
                            <option value="">-- Colonne --</option>
                            {selectedTables.find(t => t.name === join.table2)?.columns.map(c => (
                              <option key={c.name} value={c.name}>{c.name}</option>
                            ))}
                          </select>
                          <button
                            onClick={() => removeJoin(i)}
                            className="p-1.5 hover:bg-red-100 rounded text-red-500"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Tab Filtres */}
              {activeTab === 'where' && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                      Conditions WHERE ({whereConditions.length})
                    </h3>
                    <button onClick={addWhereCondition} className="btn-secondary text-xs flex items-center gap-1">
                      <Plus className="w-3 h-3" />
                      Ajouter condition
                    </button>
                  </div>
                  {whereConditions.length === 0 ? (
                    <p className="text-sm text-gray-500">Aucun filtre défini</p>
                  ) : (
                    <div className="space-y-2">
                      {whereConditions.map((cond, i) => (
                        <div key={i} className="flex items-center gap-2 p-2 bg-gray-50 dark:bg-gray-700/50 rounded">
                          {i > 0 && (
                            <select
                              value={cond.connector}
                              onChange={(e) => updateWhere(i, 'connector', e.target.value)}
                              className="px-2 py-1 text-xs border border-primary-300 dark:border-primary-600 rounded dark:bg-gray-700"
                            >
                              <option value="AND">AND</option>
                              <option value="OR">OR</option>
                            </select>
                          )}
                          <select
                            value={cond.column}
                            onChange={(e) => updateWhere(i, 'column', e.target.value)}
                            className="flex-1 px-2 py-1 text-sm border border-primary-300 dark:border-primary-600 rounded dark:bg-gray-700"
                          >
                            <option value="">-- Colonne --</option>
                            {allColumns.map(c => (
                              <option key={c.fullName} value={c.name}>{c.fullName}</option>
                            ))}
                          </select>
                          <select
                            value={cond.operator}
                            onChange={(e) => updateWhere(i, 'operator', e.target.value)}
                            className="px-2 py-1 text-sm border border-primary-300 dark:border-primary-600 rounded dark:bg-gray-700"
                          >
                            {OPERATORS.map(op => (
                              <option key={op} value={op}>{op}</option>
                            ))}
                          </select>
                          {!['IS NULL', 'IS NOT NULL'].includes(cond.operator) && (
                            <input
                              type="text"
                              value={cond.value}
                              onChange={(e) => updateWhere(i, 'value', e.target.value)}
                              placeholder="Valeur..."
                              className="flex-1 px-2 py-1 text-sm border border-primary-300 dark:border-primary-600 rounded dark:bg-gray-700"
                            />
                          )}
                          <button onClick={() => removeWhere(i)} className="p-1 hover:bg-red-100 rounded text-red-500">
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Tab Paramètres */}
              {activeTab === 'params' && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                      Paramètres de la requête ({parameters.length})
                    </h3>
                    <button onClick={addParameter} className="btn-secondary text-xs flex items-center gap-1">
                      <Plus className="w-3 h-3" />
                      Ajouter paramètre
                    </button>
                  </div>

                  <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg text-sm text-blue-700 dark:text-blue-300">
                    <p className="font-medium mb-1">💡 Paramètres détectés automatiquement</p>
                    <p>Les paramètres (@param) utilisés dans les filtres sont extraits automatiquement. Configurez leur type et source ici.</p>
                  </div>

                  {parameters.length === 0 ? (
                    <p className="text-sm text-gray-500">Aucun paramètre défini. Ajoutez des valeurs @param dans vos filtres WHERE.</p>
                  ) : (
                    <div className="space-y-3">
                      {parameters.map((param, i) => (
                        <div key={i} className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-gray-200 dark:border-primary-600">
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                            <div>
                              <label className="block text-xs font-medium text-gray-600 mb-1">Nom du paramètre</label>
                              <input
                                type="text"
                                value={param.name}
                                onChange={(e) => updateParameter(i, 'name', e.target.value)}
                                placeholder="@param"
                                className="w-full px-2 py-1.5 text-sm border border-primary-300 dark:border-primary-600 rounded dark:bg-gray-700 font-mono"
                              />
                            </div>
                            <div>
                              <label className="block text-xs font-medium text-gray-600 mb-1">Libellé affiché</label>
                              <input
                                type="text"
                                value={param.label}
                                onChange={(e) => updateParameter(i, 'label', e.target.value)}
                                placeholder="Label..."
                                className="w-full px-2 py-1.5 text-sm border border-primary-300 dark:border-primary-600 rounded dark:bg-gray-700"
                              />
                            </div>
                            <div>
                              <label className="block text-xs font-medium text-gray-600 mb-1">Type</label>
                              <select
                                value={param.type}
                                onChange={(e) => updateParameter(i, 'type', e.target.value)}
                                className="w-full px-2 py-1.5 text-sm border border-primary-300 dark:border-primary-600 rounded dark:bg-gray-700"
                              >
                                {PARAM_TYPES.map(t => (
                                  <option key={t} value={t}>
                                    {t === 'date' ? '📅 Date' : t === 'number' ? '🔢 Nombre' : t === 'select' ? '📋 Liste' : t === 'multiselect' ? '☑️ Liste coche' : '📝 Texte'}
                                  </option>
                                ))}
                              </select>
                            </div>
                            <div>
                              <label className="block text-xs font-medium text-gray-600 mb-1">Source</label>
                              <select
                                value={param.source}
                                onChange={(e) => updateParameter(i, 'source', e.target.value)}
                                className="w-full px-2 py-1.5 text-sm border border-primary-300 dark:border-primary-600 rounded dark:bg-gray-700"
                              >
                                {PARAM_SOURCES.map(s => (
                                  <option key={s} value={s}>
                                    {s === 'manual' ? 'Saisie manuelle' : s === 'societe' ? 'Filtre société' : s === 'annee' ? 'Filtre année' : 'Filtre mois'}
                                  </option>
                                ))}
                              </select>
                            </div>
                          </div>
                          <div className="flex items-center gap-4 mt-3">
                            <div className="flex-1">
                              <label className="block text-xs font-medium text-gray-600 mb-1">
                                {(param.type === 'select' || param.type === 'multiselect') ? 'Requête SQL pour les options' : 'Valeur par défaut'}
                              </label>
                              {(param.type === 'select' || param.type === 'multiselect') ? (
                                <textarea
                                  value={param.defaultValue}
                                  onChange={(e) => updateParameter(i, 'defaultValue', e.target.value)}
                                  placeholder="SELECT code AS value, libelle AS label FROM MaTable ORDER BY libelle"
                                  rows={2}
                                  className="w-full px-2 py-1.5 text-sm border border-primary-300 dark:border-primary-600 rounded dark:bg-gray-700 font-mono"
                                />
                              ) : (
                                <input
                                  type={param.type === 'date' ? 'date' : param.type === 'number' ? 'number' : 'text'}
                                  value={param.defaultValue}
                                  onChange={(e) => updateParameter(i, 'defaultValue', e.target.value)}
                                  placeholder="Valeur par défaut..."
                                  className="w-full px-2 py-1.5 text-sm border border-primary-300 dark:border-primary-600 rounded dark:bg-gray-700"
                                />
                              )}
                            </div>
                            <label className="flex items-center gap-2 mt-4">
                              <input
                                type="checkbox"
                                checked={param.required}
                                onChange={(e) => updateParameter(i, 'required', e.target.checked)}
                                className="rounded border-primary-300"
                              />
                              <span className="text-sm text-gray-600">Requis</span>
                            </label>
                            <button
                              onClick={() => removeParameter(i)}
                              className="mt-4 p-1.5 hover:bg-red-100 rounded text-red-500"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Tab SQL */}
              {activeTab === 'query' && (
                <div className="h-full flex flex-col -m-4">
                  <div className="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700">
                    <h3 className="text-sm font-semibold text-gray-300">
                      Éditeur SQL
                    </h3>
                    <button
                      onClick={generateQuery}
                      className="px-3 py-1 text-xs bg-green-600 hover:bg-green-700 text-white rounded flex items-center gap-1"
                    >
                      <RefreshCw className="w-3 h-3" />
                      Régénérer
                    </button>
                  </div>
                  <div className="flex-1 relative">
                    <textarea
                      value={generatedQuery}
                      onChange={(e) => setGeneratedQuery(e.target.value)}
                      placeholder="-- Sélectionnez des tables et colonnes pour générer la requête, ou écrivez directement votre SQL ici"
                      className="absolute inset-0 w-full h-full p-4 bg-gray-900 text-green-400 font-mono text-sm resize-none border-0 focus:outline-none focus:ring-0"
                      spellCheck={false}
                    />
                  </div>
                  {error && (
                    <div className="p-3 bg-red-900/50 border-t border-red-700 text-red-300 text-sm">
                      {error}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Aperçu */}
            {showPreview && previewData.length > 0 && (
              <div className="border-t border-gray-200 dark:border-gray-700 max-h-64 overflow-auto">
                <div className="sticky top-0 bg-gray-100 dark:bg-gray-700 px-4 py-2 flex items-center justify-between">
                  <span className="text-sm font-medium">Aperçu ({previewData.length} lignes)</span>
                  <button onClick={() => setShowPreview(false)} className="p-1 hover:bg-gray-200 dark:hover:bg-gray-600 rounded">
                    <X className="w-4 h-4" />
                  </button>
                </div>
                <table className="w-full text-xs">
                  <thead className="bg-gray-50 dark:bg-gray-700 sticky top-8">
                    <tr>
                      {previewColumns.map(col => (
                        <th key={col} className="px-2 py-1.5 text-left font-medium border-b">{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {previewData.slice(0, 20).map((row, i) => (
                      <tr key={i} className={i % 2 === 0 ? 'bg-white dark:bg-gray-800' : 'bg-gray-50 dark:bg-gray-750'}>
                        {previewColumns.map(col => (
                          <td key={col} className="px-2 py-1 border-b border-gray-100 dark:border-gray-700 truncate max-w-[200px]">
                            {row[col]?.toString() || ''}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Modal Sauvegarde */}
      {showSaveModal && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center">
          <div className="absolute inset-0 bg-black/50" onClick={() => setShowSaveModal(false)} />
          <div className="relative bg-white dark:bg-gray-800 rounded-xl shadow-xl p-6 w-96">
            <h3 className="text-lg font-semibold mb-4">Créer une source de données</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Nom de la source *</label>
                <input
                  type="text"
                  value={sourceName}
                  onChange={(e) => setSourceName(e.target.value)}
                  placeholder="Ex: Ventes par commercial"
                  className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg dark:bg-gray-700"
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Description</label>
                <textarea
                  value={sourceDescription}
                  onChange={(e) => setSourceDescription(e.target.value)}
                  placeholder="Description optionnelle..."
                  rows={2}
                  className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg dark:bg-gray-700"
                />
              </div>
              {error && (
                <div className="p-2 bg-red-50 dark:bg-red-900/20 text-red-600 text-sm rounded">
                  {error}
                </div>
              )}
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button onClick={() => setShowSaveModal(false)} className="btn-secondary">
                Annuler
              </button>
              <button
                onClick={handleSave}
                disabled={!sourceName.trim() || saving}
                className="btn-primary"
              >
                {saving ? 'Création...' : 'Créer et utiliser'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
