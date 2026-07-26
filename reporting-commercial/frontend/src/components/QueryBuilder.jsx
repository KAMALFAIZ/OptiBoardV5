import { useState, useEffect, useRef } from 'react'
import {
  X, Database, Table2, Columns, Plus, Trash2, Play, Save, Search,
  Link2, Filter, SortAsc, SortDesc, ChevronRight, ChevronDown, Eye, Code, RefreshCw, Settings2, Layout, Maximize2, Minimize2, AlertTriangle
} from 'lucide-react'
import {
  getQueryBuilderTables, getTableColumns, previewBuilderQuery, createDataSource, getDataSource,
  extractErrorMessage
} from '../services/api'
import JoinDesigner from './JoinDesigner'
import SqlEditor from './SqlEditor'

const AGGREGATES = ['', 'SUM', 'COUNT', 'AVG', 'MIN', 'MAX']
const JOIN_TYPES = ['INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'FULL JOIN']
const OPERATORS = ['=', '!=', '>', '<', '>=', '<=', 'LIKE', 'IN', 'IS NULL', 'IS NOT NULL']
const PARAM_TYPES = ['date', 'text', 'number', 'select', 'multiselect']
const PARAM_SOURCES = ['manual', 'societe', 'annee', 'mois']

export default function QueryBuilder({ isOpen, onClose, onSave, onUseQuery = null, targetType = 'pivot', initialSourceId = null, initialSql = '' }) {
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
  const [sqlFullscreen, setSqlFullscreen] = useState(false)
  // Non-null quand une requete chargee est trop complexe pour l'edition visuelle
  const [sqlOnlyNotice, setSqlOnlyNotice] = useState(null)

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
      setSqlFullscreen(false)
      setSqlOnlyNotice(null)
    } else {
      loadTables()
      // Charger la requete existante (edition d'un template) : on tente une
      // retro-generation vers les onglets visuels pour les requetes SIMPLES ;
      // sinon repli sur l'editeur SQL (aucune corruption d'une requete complexe).
      if (initialSql && !initialSourceId) {
        loadFromSql(initialSql)
      }
    }
  }, [isOpen])

  // Charger automatiquement depuis une source existante
  useEffect(() => {
    if (isOpen && initialSourceId && tables.length > 0 && !initializing && selectedTables.length === 0) {
      loadFromDataSource(initialSourceId)
    }
  }, [isOpen, initialSourceId, tables.length])

  // Preserve le SQL d'origine tant que l'utilisateur n'a pas modifie la config visuelle
  // (evite d'ecraser une requete avancee au simple chargement de l'assistant).
  const preserveOriginalSql = useRef(false)

  useEffect(() => {
    // Ne générer la requête que si on a au moins une table sélectionnée
    if (selectedTables.length > 0) {
      // Sauter la 1ere generation declenchee par un chargement programmatique
      if (preserveOriginalSql.current) {
        preserveOriginalSql.current = false
        return
      }
      // L'utilisateur a modifie la config : la requete est desormais reconstruite
      setSqlOnlyNotice(null)
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

  // Construit un descripteur de parametre a partir de son nom (@xxx), avec
  // devinette du type/source selon des heuristiques sur le nom.
  const buildParamMeta = (paramName) => {
    let type = 'text'
    let source = 'manual'
    const lowerName = paramName.toLowerCase()
    if (lowerName.includes('date') || lowerName.includes('debut') || lowerName.includes('fin') || lowerName.includes('du') || lowerName.includes('au')) {
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
    return {
      name: paramName,
      label: paramName.replace('@', '').replace(/([A-Z])/g, ' $1').trim(),
      type,
      source,
      defaultValue: '',
      required: true,
    }
  }

  // Extraire les paramètres (@param) des conditions WHERE
  const extractParametersFromConditions = (conditions) => {
    const params = []
    const seen = new Set()
    conditions.forEach(cond => {
      if (cond.value && cond.value.startsWith('@') && !seen.has(cond.value)) {
        seen.add(cond.value)
        params.push(buildParamMeta(cond.value))
      }
    })
    return params
  }

  // Extraire TOUS les parametres @xxx presents dans la requete (SELECT, WHERE,
  // GROUP BY, HAVING...), pas seulement dans les filtres. Dedoublonne.
  const extractParamsFromSql = (sql) => {
    if (!sql) return []
    const seen = new Set()
    const out = []
    const re = /@([A-Za-z_][A-Za-z0-9_]*)/g
    let m
    while ((m = re.exec(sql)) !== null) {
      const name = '@' + m[1]
      if (!seen.has(name)) {
        seen.add(name)
        out.push(buildParamMeta(name))
      }
    }
    return out
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

  // ────────────────────────────────────────────────────────────────────────
  // Parseur SQL → visuel (cas SIMPLES uniquement)
  // Retourne une structure exploitable par le builder, ou null si la requete
  // est trop complexe (CTE, sous-requete, CASE, expressions, fonctions non
  // agregees...). En cas de null, on retombe sur l'editeur SQL sans rien casser.
  // ────────────────────────────────────────────────────────────────────────

  // Decoupe une liste en respectant les parentheses (ex: SELECT a, SUM(b), c)
  const splitTopLevel = (str, sep) => {
    const out = []
    let depth = 0
    let cur = ''
    for (const ch of str) {
      if (ch === '(') depth++
      else if (ch === ')') depth--
      if (ch === sep && depth === 0) {
        out.push(cur)
        cur = ''
      } else {
        cur += ch
      }
    }
    if (cur.trim()) out.push(cur)
    return out
  }

  // Parse une reference de table: [Table] AS [t] | [Table] t | Table t | Table
  const parseTableRef = (raw) => {
    const str = raw.trim()
    const m = str.match(/^(?:\[([^\]]+)\]|([A-Za-z0-9_]+))/)
    if (!m) return null
    const name = m[1] || m[2]
    let after = str.slice(m[0].length).trim().replace(/^AS\s+/i, '')
    let alias = name
    const am = after.match(/^(?:\[([^\]]+)\]|([A-Za-z0-9_]+))/)
    if (am) alias = am[1] || am[2]
    return { name, alias }
  }

  // Parse un identifiant colonne: [t].[col] | [col] | t.col | col
  const parseColumnRef = (raw) => {
    const m = raw.trim().match(
      /^(?:\[([^\]]+)\]|([A-Za-z0-9_]+))(?:\.(?:\[([^\]]+)\]|([A-Za-z0-9_]+)))?$/
    )
    if (!m) return null
    if (m[3] !== undefined || m[4] !== undefined) {
      return { tableAlias: m[1] || m[2], name: m[3] || m[4] }
    }
    return { tableAlias: null, name: m[1] || m[2] }
  }

  // Parse un element de SELECT: colonne, colonne AS alias, ou AGG(col) AS alias
  const parseSelectItem = (raw) => {
    let expr = raw.trim()
    let alias = ''
    const asm = expr.match(/\s+AS\s+(?:\[([^\]]+)\]|([A-Za-z0-9_]+))\s*$/i)
    if (asm) {
      alias = asm[1] || asm[2]
      expr = expr.slice(0, expr.length - asm[0].length).trim()
    }
    let aggregate = ''
    const aggm = expr.match(/^(SUM|COUNT|AVG|MIN|MAX)\s*\(\s*(?:DISTINCT\s+)?([\s\S]+?)\s*\)$/i)
    let inner = expr
    if (aggm) {
      aggregate = aggm[1].toUpperCase()
      inner = aggm[2].trim()
    }
    if (inner === '*') return null // COUNT(*) / SELECT * non geres visuellement
    const colRef = parseColumnRef(inner)
    if (!colRef) return null // expression complexe (CASE, +, fonction...) -> abandon
    return { tableAlias: colRef.tableAlias, name: colRef.name, aggregate, alias }
  }

  // Analyse complete d'un SELECT simple -> structure { tables, columns, joins, orderBy }
  const parseSqlToStructure = (rawSql) => {
    if (!rawSql) return null
    let sql = rawSql.trim().replace(/;+\s*$/, '')
    if (sql.includes(';')) return null // multi-instructions
    // Rejeter les constructions complexes
    if (/^\s*WITH\b/i.test(sql)) return null // CTE
    if (/\bUNION\b|\bEXCEPT\b|\bINTERSECT\b/i.test(sql)) return null
    if (/\bCASE\b|\bOVER\s*\(|\bPIVOT\b|\bUNPIVOT\b/i.test(sql)) return null
    if (/\(\s*SELECT\b/i.test(sql)) return null // sous-requete
    if (/\bHAVING\b/i.test(sql)) return null

    const selFrom = sql.match(/^\s*SELECT\s+([\s\S]*?)\sFROM\s+([\s\S]+)$/i)
    if (!selFrom) return null
    let selectPart = selFrom[1].trim()
    let rest = selFrom[2].trim()
    selectPart = selectPart.replace(/^DISTINCT\s+/i, '').replace(/^TOP\s+\d+\s+/i, '')

    // Delimiter FROM/JOIN vs WHERE/GROUP BY/ORDER BY
    const idxs = [/\bWHERE\b/i, /\bGROUP\s+BY\b/i, /\bORDER\s+BY\b/i]
      .map((re) => rest.search(re))
      .filter((i) => i >= 0)
    const fromEnd = idxs.length ? Math.min(...idxs) : rest.length
    const fromPart = rest.slice(0, fromEnd).trim()

    const orderIdx = rest.search(/\bORDER\s+BY\b/i)
    const orderPart =
      orderIdx >= 0 ? rest.slice(orderIdx).replace(/^\s*ORDER\s+BY\s+/i, '').trim() : ''

    // --- Tables + jointures ---
    const firstJoin = fromPart.search(/\b(?:INNER|LEFT|RIGHT|FULL)\s+(?:OUTER\s+)?JOIN\b/i)
    const baseStr = (firstJoin >= 0 ? fromPart.slice(0, firstJoin) : fromPart).trim()
    const baseTable = parseTableRef(baseStr)
    if (!baseTable) return null
    const tables = [baseTable]
    const rawJoins = []
    if (firstJoin >= 0) {
      const joinRe =
        /\b(INNER|LEFT|RIGHT|FULL)\s+(?:OUTER\s+)?JOIN\s+([\s\S]+?)\s+ON\s+([\s\S]+?)(?=\b(?:INNER|LEFT|RIGHT|FULL)\s+(?:OUTER\s+)?JOIN\b|$)/gi
      let jm
      while ((jm = joinRe.exec(fromPart)) !== null) {
        const t = parseTableRef(jm[2].trim())
        if (!t) return null
        const onStr = jm[3].trim()
        if (/\bAND\b|\bOR\b/i.test(onStr)) return null // jointure multi-conditions non geree
        const onm = onStr.match(
          /^(?:\[([^\]]+)\]|([A-Za-z0-9_]+))\.(?:\[([^\]]+)\]|([A-Za-z0-9_]+))\s*=\s*(?:\[([^\]]+)\]|([A-Za-z0-9_]+))\.(?:\[([^\]]+)\]|([A-Za-z0-9_]+))$/
        )
        if (!onm) return null
        tables.push(t)
        rawJoins.push({
          type: `${jm[1].toUpperCase()} JOIN`,
          joinedAlias: t.alias,
          joinedName: t.name,
          leftAlias: onm[1] || onm[2],
          leftCol: onm[3] || onm[4],
          rightAlias: onm[5] || onm[6],
          rightCol: onm[7] || onm[8],
        })
      }
    }

    // Map alias -> nom de table
    const aliasMap = {}
    tables.forEach((t) => {
      aliasMap[t.alias] = t.name
      aliasMap[t.name] = t.name
    })

    // Resoudre les jointures vers le modele builder {type,table1,column1,table2,column2}
    const joins = []
    for (const j of rawJoins) {
      let table1, column1, column2
      if (j.leftAlias === j.joinedAlias) {
        column2 = j.leftCol
        table1 = aliasMap[j.rightAlias]
        column1 = j.rightCol
      } else {
        table1 = aliasMap[j.leftAlias]
        column1 = j.leftCol
        column2 = j.rightCol
      }
      if (!table1) return null
      joins.push({ type: j.type, table1, column1, table2: j.joinedName, column2 })
    }

    // --- Colonnes SELECT ---
    let columns = []
    if (selectPart.trim() !== '*') {
      const items = splitTopLevel(selectPart, ',')
      for (const it of items) {
        const parsed = parseSelectItem(it)
        if (!parsed) return null
        const table = parsed.tableAlias ? aliasMap[parsed.tableAlias] : baseTable.name
        if (!table) return null
        let alias = parsed.alias
        if (alias && alias === parsed.name && !parsed.aggregate) alias = ''
        columns.push({ table, name: parsed.name, aggregate: parsed.aggregate, alias })
      }
    }

    // --- ORDER BY ---
    const orderBy = []
    if (orderPart) {
      for (const tok of splitTopLevel(orderPart, ',')) {
        const om = tok
          .trim()
          .match(/^(?:\[([^\]]+)\]|([A-Za-z0-9_]+))(?:\.(?:\[([^\]]+)\]|([A-Za-z0-9_]+)))?\s*(ASC|DESC)?$/i)
        if (!om) return null
        const col = om[3] || om[4] || om[1] || om[2]
        orderBy.push({ column: col, direction: (om[5] || 'ASC').toUpperCase() })
      }
    }

    return { tables, columns, joins, orderBy }
  }

  // Parse la clause FROM (+ JOINs) -> { tables, joins, aliasMap } ou null.
  // Tolerant : construit TOUJOURS l'aliasMap (indispensable pour resoudre les
  // colonnes prefixees), accepte les ON multi-conditions (prend la 1ere egalite),
  // et n'abandonne pas toute la clause si un seul JOIN n'est pas representable.
  const parseTablesAndJoins = (fromPart) => {
    if (!fromPart || fromPart.includes('(')) return null // sous-requete dans FROM
    const firstJoin = fromPart.search(/\b(?:INNER|LEFT|RIGHT|FULL)\s+(?:OUTER\s+)?JOIN\b/i)
    const baseStr = (firstJoin >= 0 ? fromPart.slice(0, firstJoin) : fromPart).trim()
    const baseTable = parseTableRef(baseStr)
    if (!baseTable) return null
    const tables = [baseTable]
    const rawJoins = []
    if (firstJoin >= 0) {
      const joinRe =
        /\b(INNER|LEFT|RIGHT|FULL)\s+(?:OUTER\s+)?JOIN\s+([\s\S]+?)\s+ON\s+([\s\S]+?)(?=\b(?:INNER|LEFT|RIGHT|FULL)\s+(?:OUTER\s+)?JOIN\b|$)/gi
      let jm
      const eqRe = /(?:\[([^\]]+)\]|([A-Za-z0-9_]+))\.(?:\[([^\]]+)\]|([A-Za-z0-9_]+))\s*=\s*(?:\[([^\]]+)\]|([A-Za-z0-9_]+))\.(?:\[([^\]]+)\]|([A-Za-z0-9_]+))/g
      while ((jm = joinRe.exec(fromPart)) !== null) {
        const t = parseTableRef(jm[2].trim())
        if (!t) continue // table non parsable : on saute ce join (garde les autres)
        tables.push(t)
        const onStr = jm[3].trim()
        // Recuperer TOUTES les egalites [a].[c1] = [b].[c2] du ON (jointure multi-conditions)
        const eqs = []
        let em
        eqRe.lastIndex = 0
        while ((em = eqRe.exec(onStr)) !== null) {
          eqs.push({
            leftAlias: em[1] || em[2],
            leftCol: em[3] || em[4],
            rightAlias: em[5] || em[6],
            rightCol: em[7] || em[8],
          })
        }
        if (eqs.length === 0) continue // ON non representable : table gardee, pas de join
        rawJoins.push({ type: `${jm[1].toUpperCase()} JOIN`, joinedAlias: t.alias, joinedName: t.name, eqs })
      }
    }
    const aliasMap = {}
    tables.forEach((t) => {
      aliasMap[t.alias] = t.name
      aliasMap[t.name] = t.name
    })
    const joins = []
    for (const j of rawJoins) {
      // Resoudre chaque egalite en {column1 (cote table1), column2 (cote table2)}
      let table1 = null
      const pairs = []
      for (const e of j.eqs) {
        let c1, c2
        if (e.leftAlias === j.joinedAlias) { c2 = e.leftCol; table1 = table1 || aliasMap[e.rightAlias]; c1 = e.rightCol }
        else { table1 = table1 || aliasMap[e.leftAlias]; c1 = e.leftCol; c2 = e.rightCol }
        pairs.push({ column1: c1, column2: c2 })
      }
      if (!table1 || pairs.length === 0) continue
      const [primary, ...extra] = pairs
      joins.push({
        type: j.type,
        table1,
        column1: primary.column1,
        table2: j.joinedName,
        column2: primary.column2,
        operator: '=',
        ...(extra.length ? { extraConditions: extra.map((p) => ({ ...p, operator: '=' })) } : {}),
      })
    }
    return { tables, joins, aliasMap }
  }

  // Extrait tous les noms de tables cites apres FROM/JOIN (toute requete, meme complexe).
  // Sert uniquement a l'AFFICHAGE (lecture seule) — ne modifie jamais le SQL.
  const extractTableNames = (sql) => {
    if (!sql) return []
    const names = new Set()
    const re = /\b(?:FROM|JOIN)\s+(?:\[([^\]]+)\]|([A-Za-z0-9_]+))/gi
    let m
    while ((m = re.exec(sql)) !== null) {
      const n = m[1] || m[2]
      if (n) names.add(n)
    }
    return [...names]
  }

  // Charge une requete SQL dans le builder : visuel si simple, sinon editeur SQL.
  const loadFromSql = async (sql) => {
    const struct = parseSqlToStructure(sql)
    if (!struct) {
      // Requete avancee : on charge quand meme les tables detectees comme tables
      // EDITABLES, mais on PRESERVE le SQL d'origine tant que l'utilisateur ne
      // modifie rien (la regeneration -- qui perd les colonnes calculees -- n'a
      // lieu qu'a la 1ere interaction visuelle).
      setInitializing(true)
      try {
        const tableObjs = []
        for (const name of extractTableNames(sql)) {
          const cols = await loadTableColumns(name)
          if (cols && cols.length > 0) {
            tableObjs.push({ name, alias: name, columns: cols, expanded: true })
          }
        }
        setGeneratedQuery(sql)
        // Charger TOUS les parametres @xxx (independant du SQL -> pas de regeneration)
        setParameters(extractParamsFromSql(sql))

        // Parsing PARTIEL (colonnes representables, jointures, filtres) — uniquement
        // pour une requete "plate" (pas de CTE ni sous-requete). Les colonnes calculees
        // (FORMAT, DATENAME, CASE...) sont simplement ignorees ; le reste s'affiche.
        let partialCols = []
        let partialJoins = []
        let partialWhere = []
        const isFlat =
          /^\s*SELECT\b/i.test(sql) &&
          !/^\s*WITH\b/i.test(sql) &&
          !/\(\s*SELECT\b/i.test(sql) &&
          (sql.match(/\bSELECT\b/gi) || []).length === 1
        if (isFlat) {
          // Delimiter la clause FROM/JOIN
          const fromAt = sql.search(/\bFROM\b/i)
          const after = fromAt >= 0 ? sql.slice(fromAt + 4) : ''
          const bnds = [/\bWHERE\b/i, /\bGROUP\s+BY\b/i, /\bORDER\s+BY\b/i]
            .map((re) => after.search(re))
            .filter((i) => i >= 0)
          const fromPart = after.slice(0, bnds.length ? Math.min(...bnds) : after.length).trim()
          const tj = parseTablesAndJoins(fromPart)
          const aliasMap = tj ? tj.aliasMap : {}
          if (tj) partialJoins = tj.joins

          // Colonnes : garder celles qui sont representables (colonne simple ou agregat)
          const selM = sql.match(/^\s*SELECT\s+([\s\S]*?)\sFROM\s/i)
          if (selM) {
            const items = splitTopLevel(
              selM[1].replace(/^DISTINCT\s+/i, '').replace(/^TOP\s+\d+\s+/i, ''),
              ','
            )
            for (const it of items) {
              const p = parseSelectItem(it)
              if (!p) continue // colonne calculee -> ignoree
              let table = p.tableAlias ? aliasMap[p.tableAlias] : null
              if (!table) {
                const owners = tableObjs.filter((t) => t.columns.some((c) => c.name === p.name))
                if (owners.length === 1) table = owners[0].name
              }
              if (!table) continue
              const meta = tableObjs.find((t) => t.name === table)?.columns.find((c) => c.name === p.name)
              if (!meta) continue
              let alias = p.alias
              if (alias && alias === p.name && !p.aggregate) alias = ''
              partialCols.push({
                key: `${table}.${p.name}`,
                table,
                name: p.name,
                type: meta.type || '',
                alias,
                aggregate: p.aggregate || '',
                groupBy: false,
              })
            }
          }
          partialWhere = parseWhereConditions(sql)
        }

        // Identifier ce qui empeche l'edition visuelle (pour un message explicite)
        const blockers = []
        if (/^\s*WITH\b/i.test(sql)) blockers.push('CTE (WITH)')
        if (/\(\s*SELECT\b/i.test(sql)) blockers.push('sous-requête')
        if (/\bCASE\b/i.test(sql)) blockers.push('CASE')
        if (/\bUNION\b|\bEXCEPT\b|\bINTERSECT\b/i.test(sql)) blockers.push('UNION')
        if (blockers.length === 0 && !isFlat) blockers.push('SELECT imbriqué')

        if (tableObjs.length > 0) {
          preserveOriginalSql.current = true
          setSelectedTables(tableObjs)
          if (partialJoins.length) setJoins(partialJoins)
          if (partialCols.length) setSelectedColumns(partialCols)
          if (partialWhere.length) setWhereConditions(partialWhere)
          setActiveTab(partialCols.length ? 'columns' : 'tables')
          if (isFlat) {
            setSqlOnlyNotice(
              'Requête avancée : tables, colonnes simples, jointures et filtres reconnus sont chargés pour édition. Les colonnes calculées (FORMAT, CASE…) et le GROUP BY d\'origine ne sont pas repris et seront perdus dès que vous modifierez la sélection. Le SQL d\'origine reste intact tant que vous ne changez rien.'
            )
          } else {
            setSqlOnlyNotice(
              `Cette requête contient : ${blockers.join(', ')}. Ces constructions n'ont pas d'équivalent dans l'éditeur visuel (jointure sur sous-requête, colonnes/filtres calculés…), donc seules les TABLES sont chargées — colonnes, jointures et filtres ne peuvent pas être reconstitués sans fausser la requête. Modifiez-la dans l'éditeur SQL.`
            )
          }
        } else {
          setActiveTab('query')
          setSqlOnlyNotice(
            'Aucune table de ce DWH n\'a été reconnue dans la requête : éditez-la directement dans l\'éditeur SQL.'
          )
        }
      } finally {
        setInitializing(false)
      }
      return
    }
    setInitializing(true)
    try {
      // Charger les colonnes reelles de chaque table (types + rendu des onglets)
      const tableObjs = []
      for (const t of struct.tables) {
        const cols = await loadTableColumns(t.name)
        if (!cols || cols.length === 0) {
          // Table inconnue du DWH -> on ne risque pas une reconstruction bancale
          setGeneratedQuery(sql)
          setActiveTab('query')
          setSqlOnlyNotice(
            `La table « ${t.name} » est introuvable dans ce DWH : édition visuelle indisponible, utilisez l'éditeur SQL.`
          )
          return
        }
        tableObjs.push({ name: t.name, alias: t.name, columns: cols, expanded: true })
      }
      setSqlOnlyNotice(null)

      const selCols = struct.columns.map((c) => {
        const meta = tableObjs.find((to) => to.name === c.table)?.columns?.find((cc) => cc.name === c.name)
        return {
          key: `${c.table}.${c.name}`,
          table: c.table,
          name: c.name,
          type: meta?.type || '',
          alias: c.alias || '',
          aggregate: c.aggregate || '',
          groupBy: false,
        }
      })

      const parsedConditions = parseWhereConditions(sql)
      // Extraire TOUS les @param de la requete (pas seulement ceux des filtres)
      const extractedParams = extractParamsFromSql(sql)

      preserveOriginalSql.current = true
      setSelectedTables(tableObjs)
      setJoins(struct.joins)
      setSelectedColumns(selCols)
      setOrderByColumns(struct.orderBy)
      setWhereConditions(parsedConditions)
      setParameters(extractedParams)
      setActiveTab(selCols.length ? 'columns' : parsedConditions.length ? 'where' : 'tables')
    } catch (err) {
      console.error('Erreur parse SQL -> visuel:', err)
      setGeneratedQuery(sql)
      setActiveTab('query')
      setSqlOnlyNotice('Impossible de charger la requête en mode visuel : utilisez l\'éditeur SQL.')
    } finally {
      setInitializing(false)
    }
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

  // Jointures multi-conditions : gerer les conditions supplementaires (extraConditions)
  const addJoinCondition = (index) => {
    setJoins(joins.map((j, i) =>
      i === index
        ? { ...j, extraConditions: [...(j.extraConditions || []), { column1: '', column2: '', operator: '=' }] }
        : j
    ))
  }

  const updateJoinCondition = (index, condIndex, field, value) => {
    setJoins(joins.map((j, i) => {
      if (i !== index) return j
      const conds = (j.extraConditions || []).map((c, ci) =>
        ci === condIndex ? { ...c, [field]: value } : c
      )
      return { ...j, extraConditions: conds }
    }))
  }

  const removeJoinCondition = (index, condIndex) => {
    setJoins(joins.map((j, i) =>
      i === index
        ? { ...j, extraConditions: (j.extraConditions || []).filter((_, ci) => ci !== condIndex) }
        : j
    ))
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

    // JOINS (avec conditions multiples : ON c1 = c2 [AND cx = cy ...])
    joins.forEach(join => {
      if (join.column1 && join.column2) {
        let on = `[${join.table1}].[${join.column1}] ${join.operator || '='} [${join.table2}].[${join.column2}]`
        ;(join.extraConditions || []).forEach(c => {
          if (c.column1 && c.column2) {
            on += ` AND [${join.table1}].[${c.column1}] ${c.operator || '='} [${join.table2}].[${c.column2}]`
          }
        })
        query += `\n${join.type} [${join.table2}] ON ${on}`
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
              → {targetType === 'pivot' ? 'Pivot Table' : targetType === 'template' ? 'Template SQL' : 'GridView'}
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
            {onUseQuery ? (
              <button
                onClick={() => { onUseQuery(generatedQuery, parameters); onClose() }}
                disabled={!generatedQuery}
                className="btn-primary flex items-center gap-1 text-sm"
              >
                <Save className="w-4 h-4" />
                Utiliser cette requête
              </button>
            ) : (
              <button
                onClick={() => setShowSaveModal(true)}
                disabled={!generatedQuery}
                className="btn-primary flex items-center gap-1 text-sm"
              >
                <Save className="w-4 h-4" />
                Créer Source
              </button>
            )}
            <button onClick={onClose} className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg">
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Contenu principal */}
        <div className="flex-1 flex overflow-hidden">
          {/* Panneau gauche - Tables */}
          <div className={`${sqlFullscreen ? 'hidden' : 'w-64'} border-r border-gray-200 dark:border-gray-700 flex flex-col`}>
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
          <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
            {/* Tabs */}
            <div className={`${sqlFullscreen ? 'hidden' : 'flex'} border-b border-gray-200 dark:border-gray-700 px-4`}>
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

            {/* Bandeau : requete non editable visuellement */}
            {sqlOnlyNotice && !sqlFullscreen && (
              <div className="mx-4 mt-3 flex items-start gap-2 rounded-lg border border-amber-300 bg-amber-50 dark:border-amber-700 dark:bg-amber-900/20 px-3 py-2 text-sm text-amber-800 dark:text-amber-300">
                <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <div className="flex items-center justify-between gap-3 flex-1">
                  <span>{sqlOnlyNotice}</span>
                  {activeTab !== 'query' && (
                    <button
                      onClick={() => setActiveTab('query')}
                      className="whitespace-nowrap font-medium underline hover:no-underline"
                    >
                      Ouvrir l'éditeur SQL
                    </button>
                  )}
                </div>
              </div>
            )}

            {/* Contenu des tabs */}
            <div className={`${sqlFullscreen ? 'hidden' : activeTab === 'query' ? 'flex-1 min-h-0 flex flex-col' : 'flex-1 overflow-auto p-4'}`}>
              {/* Tab Tables */}
              {activeTab === 'tables' && (
                <div className="space-y-4">
                  <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                    Tables sélectionnées ({selectedTables.length})
                  </h3>
                  {selectedTables.length === 0 ? (
                    (() => {
                      const detected = sqlOnlyNotice
                        ? extractTableNames(generatedQuery).filter(n => tables.some(t => t.name === n))
                        : []
                      if (detected.length > 0) {
                        return (
                          <div className="space-y-2">
                            <p className="text-sm text-gray-500">
                              Tables détectées dans la requête (lecture seule — édition visuelle désactivée) :
                            </p>
                            <div className="flex flex-wrap gap-2">
                              {detected.map(name => (
                                <span
                                  key={name}
                                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700/50 text-sm text-gray-700 dark:text-gray-300"
                                >
                                  <Table2 className="w-3.5 h-3.5 text-primary-500" />
                                  {name}
                                </span>
                              ))}
                            </div>
                          </div>
                        )
                      }
                      return <p className="text-sm text-gray-500">Cliquez sur une table à gauche pour l'ajouter</p>
                    })()
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
                    onTableRemove={(tableName) => removeTable(tableName)}
                    onAllColumnsToggle={(tableName, columns, isSelected) => {
                      if (isSelected) {
                        setSelectedColumns(prev => {
                          const newCols = columns
                            .filter(col => !prev.find(c => c.key === `${tableName}.${col.name}`))
                            .map(col => ({ key: `${tableName}.${col.name}`, table: tableName, name: col.name, type: col.type, alias: '', aggregate: '', groupBy: false }))
                          return [...prev, ...newCols]
                        })
                      } else {
                        setSelectedColumns(prev => prev.filter(c => c.table !== tableName))
                      }
                    }}
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
                        <div key={i} className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg space-y-2">
                          <div className="flex items-center gap-2">
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
                              title="Supprimer la jointure"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>

                          {/* Conditions supplementaires (jointure multi-conditions) */}
                          {(join.extraConditions || []).map((cond, ci) => (
                            <div key={ci} className="flex items-center gap-2 pl-2 ml-1 border-l-2 border-primary-200 dark:border-primary-700">
                              <span className="text-xs font-mono text-gray-400 w-8">AND</span>
                              <select
                                value={cond.column1}
                                onChange={(e) => updateJoinCondition(i, ci, 'column1', e.target.value)}
                                className="px-2 py-1.5 text-sm border border-primary-300 dark:border-primary-600 rounded dark:bg-gray-700"
                              >
                                <option value="">-- {join.table1} --</option>
                                {selectedTables.find(t => t.name === join.table1)?.columns.map(c => (
                                  <option key={c.name} value={c.name}>{c.name}</option>
                                ))}
                              </select>
                              <span className="text-sm font-mono text-gray-500">=</span>
                              <select
                                value={cond.column2}
                                onChange={(e) => updateJoinCondition(i, ci, 'column2', e.target.value)}
                                className="px-2 py-1.5 text-sm border border-primary-300 dark:border-primary-600 rounded dark:bg-gray-700"
                              >
                                <option value="">-- {join.table2} --</option>
                                {selectedTables.find(t => t.name === join.table2)?.columns.map(c => (
                                  <option key={c.name} value={c.name}>{c.name}</option>
                                ))}
                              </select>
                              <button
                                onClick={() => removeJoinCondition(i, ci)}
                                className="p-1.5 hover:bg-red-100 rounded text-red-500"
                                title="Supprimer la condition"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                          ))}

                          <button
                            onClick={() => addJoinCondition(i)}
                            className="text-xs text-primary-600 dark:text-primary-400 hover:underline flex items-center gap-1 ml-1"
                          >
                            <Plus className="w-3 h-3" />
                            Ajouter une condition (ET)
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
                <div className="flex-1 min-h-0 flex flex-col">
                  <div className="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700 flex-shrink-0">
                    <h3 className="text-sm font-semibold text-gray-300">
                      Éditeur SQL
                    </h3>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={generateQuery}
                        className="px-3 py-1 text-xs bg-green-600 hover:bg-green-700 text-white rounded flex items-center gap-1"
                      >
                        <RefreshCw className="w-3 h-3" />
                        Régénérer
                      </button>
                      <button
                        onClick={() => setSqlFullscreen(true)}
                        title="Plein écran"
                        className="px-2 py-1 text-xs bg-gray-600 hover:bg-gray-500 text-white rounded flex items-center gap-1"
                      >
                        <Maximize2 className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                  <div className="flex-1 min-h-0 relative overflow-hidden">
                    <SqlEditor
                      value={generatedQuery}
                      onChange={(val) => setGeneratedQuery(val)}
                      placeholder="-- Sélectionnez des tables et colonnes pour générer la requête, ou écrivez directement votre SQL ici"
                      fill
                      forceDark
                      className="absolute inset-0"
                    />
                  </div>
                  {error && (
                    <div className="p-3 bg-red-900/50 border-t border-red-700 text-red-300 text-sm flex-shrink-0">
                      {error}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* SQL Plein écran */}
            {sqlFullscreen && (
              <div className="flex-1 min-h-0 flex flex-col bg-gray-900">
                <div className="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700 flex-shrink-0">
                  <h3 className="text-sm font-semibold text-gray-300">Éditeur SQL</h3>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={generateQuery}
                      className="px-3 py-1 text-xs bg-green-600 hover:bg-green-700 text-white rounded flex items-center gap-1"
                    >
                      <RefreshCw className="w-3 h-3" />
                      Régénérer
                    </button>
                    <button
                      onClick={() => setSqlFullscreen(false)}
                      title="Réduire"
                      className="px-2 py-1 text-xs bg-gray-600 hover:bg-gray-500 text-white rounded flex items-center gap-1"
                    >
                      <Minimize2 className="w-3 h-3" />
                    </button>
                  </div>
                </div>
                <div className="flex-1 min-h-0 relative overflow-hidden">
                  <SqlEditor
                    value={generatedQuery}
                    onChange={(val) => setGeneratedQuery(val)}
                    placeholder="-- Écrivez votre SQL ici"
                    fill
                    forceDark
                    className="absolute inset-0"
                  />
                </div>
                {error && (
                  <div className="p-3 bg-red-900/50 border-t border-red-700 text-red-300 text-sm flex-shrink-0">
                    {error}
                  </div>
                )}
              </div>
            )}

            {/* Aperçu */}
            {!sqlFullscreen && showPreview && previewData.length > 0 && (
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
