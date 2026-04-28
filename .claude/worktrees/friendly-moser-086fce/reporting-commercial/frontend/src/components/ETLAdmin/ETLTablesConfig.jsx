import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import {
  Database, RefreshCw, CheckCircle, XCircle, Clock, Info,
  Zap, Layers, Plus, Edit2, Trash2, Save, X, Upload, Download,
  FlaskConical, BarChart3, Eye, EyeOff, Search
} from 'lucide-react'
import {
  getETLTables, getAgents, triggerTableSync,
  createETLTable, updateETLTable, deleteETLTable, toggleETLTable,
  migrateETLFromYaml, deleteAllETLTables, importETLFromOptiBoard,
  testBulkInsert
} from '../../services/etlApi'
import { extractErrorMessage } from '../../services/api'

// Styles par type de synchronisation
const SYNC_TYPES = [
  { value: 'incremental', label: 'Incremental', color: 'text-blue-600', bg: 'bg-blue-100' },
  { value: 'full',        label: 'Full Sync',   color: 'text-green-600', bg: 'bg-green-100' },
]

const PRIORITY_TYPES = [
  { value: 'high',   label: 'Prioritaire', color: 'text-orange-700', bg: 'bg-orange-100' },
  { value: 'normal', label: 'Normal',      color: 'text-gray-600',   bg: 'bg-gray-100'   },
  { value: 'low',    label: 'Basse',       color: 'text-gray-500',   bg: 'bg-gray-50'    },
]

const getSyncStyle    = (v) => SYNC_TYPES.find(t => t.value === v)    || SYNC_TYPES[0]
const getPriorityStyle = (v) => PRIORITY_TYPES.find(t => t.value === v) || PRIORITY_TYPES[1]

export default function ETLTablesConfig() {
  /* ── State ── */
  const [tables,  setTables]  = useState([])
  const [agents,  setAgents]  = useState([])
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)
  const [success, setSuccess] = useState(null)

  // Filtres
  const [searchTerm,   setSearchTerm]   = useState('')
  const [filterMode,   setFilterMode]   = useState('all') // all | incremental | full | high | normal | low
  const [showDisabled, setShowDisabled] = useState(true)

  // Highlight & scroll (comme MenuMasterManagement)
  const [highlightedTable, setHighlightedTable] = useState(null)
  const tableRefs = useRef({})

  // Modals
  const [showModal,       setShowModal]       = useState(false)
  const [editingTable,    setEditingTable]    = useState(null)
  const [deleteConfirm,   setDeleteConfirm]   = useState(null)
  const [deleteAllConfirm,setDeleteAllConfirm]= useState(false)
  const [saving,          setSaving]          = useState(false)

  // Bulk Insert Test
  const [showBulkTestModal, setShowBulkTestModal] = useState(false)
  const [bulkTestRunning,   setBulkTestRunning]   = useState(false)
  const [bulkTestResults,   setBulkTestResults]   = useState(null)
  const [bulkTestParams,    setBulkTestParams]    = useState({ table_name: '', row_limit: 10000 })

  // Formulaire
  const [formData, setFormData] = useState({
    name: '', source_table: '', target_table: '',
    sync_type: 'incremental', priority: 'normal',
    description: '', primary_key: '', incremental_column: '',
    batch_size: 1000, enabled: true, delete_detection: false, query: ''
  })

  useEffect(() => { loadData() }, [])

  /* ── Data ── */
  const loadData = async () => {
    setLoading(true)
    try {
      const [tablesRes, agentsRes] = await Promise.all([getETLTables(), getAgents()])
      const tablesData = tablesRes.data?.tables || tablesRes.data?.data || tablesRes.data || []
      const agentsData = agentsRes.data?.data  || agentsRes.data || []
      setTables(Array.isArray(tablesData) ? tablesData : [])
      setAgents(Array.isArray(agentsData) ? agentsData : [])
      setError(null)
    } catch (err) {
      console.error('Erreur chargement:', err)
      setError('Erreur lors du chargement des tables ETL')
    } finally {
      setLoading(false)
    }
  }

  /* ── Highlight / scroll (pattern MenuMasterManagement) ── */
  const scrollToAndHighlight = useCallback((tableName) => {
    setHighlightedTable(tableName)
    setTimeout(() => {
      const el = tableRefs.current[tableName]
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
      setTimeout(() => setHighlightedTable(null), 3000)
    }, 200)
  }, [])

  /* ── Handlers ── */
  const showMsg = (msg, type = 'success', delay = 3000) => {
    if (type === 'success') { setSuccess(msg); setTimeout(() => setSuccess(null), delay) }
    else                    { setError(msg);   setTimeout(() => setError(null),   delay) }
  }

  const handleSyncTable = async (tableName, agentId = null) => {
    try {
      if (agentId) {
        await triggerTableSync(agentId, tableName)
        showMsg(`Synchronisation de ${tableName} declenchee pour l'agent`)
      } else {
        const activeAgents = agents.filter(a => a.status === 'active')
        for (const agent of activeAgents) await triggerTableSync(agent.agent_id, tableName)
        showMsg(`Synchronisation de ${tableName} declenchee sur ${activeAgents.length} agents`)
      }
    } catch (err) {
      showMsg(extractErrorMessage(err, 'Erreur lors de la synchronisation'), 'error', 5000)
    }
  }

  const handleAddTable = () => {
    setEditingTable(null)
    setFormData({
      name: '', source_table: '', target_table: '',
      sync_type: 'incremental', priority: 'normal',
      description: '', primary_key: '', incremental_column: '',
      batch_size: 1000, enabled: true, delete_detection: false, query: ''
    })
    setShowModal(true)
  }

  const handleEditTable = (table) => {
    setEditingTable(table)
    const source     = table.source || {}
    const target     = table.target || {}
    const sourceTable = source.table || table.source_table || table.name || ''
    const sourceQuery = source.query || table.source_query || table.query || ''
    const targetTable = target.table || table.target_table || ''
    const primaryKey  = target.primary_key || table.primary_key || []
    const tsCol       = table.timestamp_column || table.incremental_column || ''
    setFormData({
      name:               table.name || '',
      source_table:       sourceTable,
      target_table:       targetTable,
      sync_type:          table.sync_type || 'incremental',
      priority:           table.priority  || 'normal',
      description:        table.description || '',
      primary_key:        Array.isArray(primaryKey) ? primaryKey.join(', ') : (primaryKey || ''),
      incremental_column: tsCol,
      batch_size:         table.batch_size || 1000,
      enabled:            table.enabled !== false,
      delete_detection:   table.delete_detection === true,
      query:              sourceQuery
    })
    setShowModal(true)
  }

  const handleSaveTable = async () => {
    if (!formData.name.trim() || !formData.target_table.trim()) {
      showMsg('Le nom et la table cible sont obligatoires', 'error', 5000)
      return
    }
    setSaving(true)
    const savedName = formData.name
    try {
      const tableData = {
        ...formData,
        source_table: formData.source_table || formData.name,
        primary_key: formData.primary_key
          ? formData.primary_key.split(',').map(k => k.trim()).filter(k => k)
          : []
      }
      if (editingTable) {
        await updateETLTable(editingTable.name, tableData)
        showMsg(`Table "${savedName}" modifiee avec succes`)
      } else {
        await createETLTable(tableData)
        showMsg(`Table "${savedName}" creee avec succes`)
      }
      setShowModal(false)
      await loadData()
      scrollToAndHighlight(savedName)
    } catch (err) {
      console.error('Erreur sauvegarde:', err)
      showMsg(extractErrorMessage(err, 'Erreur lors de la sauvegarde'), 'error', 5000)
    } finally {
      setSaving(false)
    }
  }

  const handleDeleteTable = async (tableName) => {
    try {
      await deleteETLTable(tableName)
      showMsg(`Table "${tableName}" supprimee avec succes`)
      setDeleteConfirm(null)
      loadData()
    } catch (err) {
      showMsg(extractErrorMessage(err, 'Erreur lors de la suppression'), 'error', 5000)
    }
  }

  const handleToggleTable = async (tableName) => {
    try {
      await toggleETLTable(tableName)
      loadData()
      showMsg(`Statut de "${tableName}" modifie`)
    } catch (err) {
      showMsg(extractErrorMessage(err, 'Erreur lors du changement de statut'), 'error', 5000)
    }
  }

  const handleMigrateYaml = async () => {
    try {
      setSaving(true)
      await migrateETLFromYaml()
      showMsg('Migration YAML vers SQL terminee avec succes')
      loadData()
    } catch (err) {
      showMsg(extractErrorMessage(err, 'Erreur lors de la migration'), 'error', 5000)
    } finally {
      setSaving(false)
    }
  }

  const handleDeleteAllTables = async () => {
    try {
      setSaving(true)
      const res = await deleteAllETLTables()
      const cnt = res.data.deleted_total || res.data.deleted_config || 0
      showMsg(`${cnt} tables supprimees avec succes`)
      setDeleteAllConfirm(false)
      loadData()
    } catch (err) {
      showMsg(extractErrorMessage(err, 'Erreur lors de la suppression'), 'error', 5000)
    } finally {
      setSaving(false)
    }
  }

  const handleImportFromOptiBoard = async () => {
    try {
      setSaving(true)
      const res = await importETLFromOptiBoard()
      showMsg(`Import OptiBoard: ${res.data.imported} importees, ${res.data.skipped} ignorees`, 'success', 5000)
      loadData()
    } catch (err) {
      showMsg(extractErrorMessage(err, "Erreur lors de l'import depuis OptiBoard"), 'error', 5000)
    } finally {
      setSaving(false)
    }
  }

  const handleRunBulkTest = async () => {
    if (!bulkTestParams.table_name) {
      setBulkTestResults({ success: false, error: 'Veuillez selectionner une table' })
      return
    }
    setBulkTestRunning(true)
    setBulkTestResults(null)
    try {
      const res = await testBulkInsert({ table_name: bulkTestParams.table_name, row_limit: bulkTestParams.row_limit })
      setBulkTestResults(res.data)
    } catch (err) {
      setBulkTestResults({ success: false, error: extractErrorMessage(err, 'Erreur lors du test') })
    } finally {
      setBulkTestRunning(false)
    }
  }

  const openBulkTestModal = () => {
    if (tables.length > 0 && !bulkTestParams.table_name)
      setBulkTestParams(prev => ({ ...prev, table_name: tables[0].name }))
    setShowBulkTestModal(true)
  }

  /* ── Computed ── */
  const tableCounts = useMemo(() => ({
    all:         tables.length,
    incremental: tables.filter(t => t.sync_type === 'incremental').length,
    full:        tables.filter(t => t.sync_type === 'full').length,
    high:        tables.filter(t => t.priority  === 'high').length,
    normal:      tables.filter(t => t.priority  === 'normal').length,
    low:         tables.filter(t => t.priority  === 'low').length,
  }), [tables])

  const filteredTables = useMemo(() => {
    return tables.filter(table => {
      const matchSearch = !searchTerm ||
        table.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        table.description?.toLowerCase().includes(searchTerm.toLowerCase())
      let matchFilter = true
      if      (filterMode === 'incremental') matchFilter = table.sync_type === 'incremental'
      else if (filterMode === 'full')        matchFilter = table.sync_type === 'full'
      else if (filterMode === 'high')        matchFilter = table.priority  === 'high'
      else if (filterMode === 'normal')      matchFilter = table.priority  === 'normal'
      else if (filterMode === 'low')         matchFilter = table.priority  === 'low'
      const matchEnabled = showDisabled || table.enabled !== false
      return matchSearch && matchFilter && matchEnabled
    })
  }, [tables, searchTerm, filterMode, showDisabled])

  /* ── Row renderer (pattern renderMenuItem) ── */
  const renderTableRow = (table) => {
    const syncStyle     = getSyncStyle(table.sync_type)
    const priorityStyle = getPriorityStyle(table.priority)
    const isEnabled     = table.enabled !== false
    const isHighlighted = highlightedTable === table.name
    const sourceTable   = table.source?.table || table.source_table || table.name
    const targetTable   = table.target?.table || table.target_table || '—'
    const pk            = table.target?.primary_key || table.primary_key
    const pkStr         = Array.isArray(pk) ? pk.join(', ') : (pk || '')

    return (
      <div
        key={table.name}
        ref={(el) => { tableRefs.current[table.name] = el }}
        className={`
          group/item flex items-center gap-3 py-2.5 px-3 rounded-lg
          transition-all duration-200 border border-transparent
          ${isHighlighted
            ? 'bg-green-100 dark:bg-green-900/30 ring-2 ring-green-500 ring-opacity-50 border-green-300'
            : 'hover:bg-gray-50 dark:hover:bg-gray-700/50 hover:border-gray-200 dark:hover:border-gray-600'
          }
          ${!isEnabled ? 'opacity-60' : ''}
        `}
      >
        {/* Point de statut */}
        <div className={`w-2 h-2 rounded-full flex-shrink-0 ${isEnabled ? 'bg-green-500' : 'bg-gray-400'}`} />

        {/* Icone avec couleur selon type de sync */}
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${syncStyle.bg} dark:bg-opacity-20`}>
          {table.sync_type === 'incremental'
            ? <Zap       className={`w-4 h-4 ${syncStyle.color}`} />
            : <RefreshCw className={`w-4 h-4 ${syncStyle.color}`} />
          }
        </div>

        {/* Nom + meta */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className={`text-sm font-medium truncate ${!isEnabled ? 'text-gray-400 dark:text-gray-500' : 'text-gray-900 dark:text-white'}`}>
              {table.name}
            </span>
          </div>
          <div className="text-xs text-gray-400 truncate mt-0.5">
            {table.description
              ? table.description
              : <span className="font-mono">{sourceTable} → {targetTable}{pkStr ? ` · PK: ${pkStr}` : ''}</span>
            }
          </div>
        </div>

        {/* Badges type + priorite */}
        <div className="flex items-center gap-1.5 flex-shrink-0">
          <span className={`text-xs px-2 py-1 rounded-md font-medium ${syncStyle.bg} ${syncStyle.color} dark:bg-opacity-20`}>
            {syncStyle.label}
          </span>
          <span className={`text-xs px-2 py-1 rounded-md font-medium ${priorityStyle.bg} ${priorityStyle.color} dark:bg-opacity-20`}>
            {priorityStyle.label}
          </span>
          {!isEnabled && (
            <span className="text-xs text-orange-600 dark:text-orange-400 px-2 py-1 bg-orange-100 dark:bg-orange-900/30 rounded-md flex items-center gap-1">
              <EyeOff className="w-3 h-3" />
              Inactif
            </span>
          )}
        </div>

        {/* Actions (visibles au hover comme dans menu) */}
        <div className="flex items-center gap-0.5 opacity-0 group-hover/item:opacity-100 transition-opacity flex-shrink-0">
          <button
            onClick={() => handleToggleTable(table.name)}
            className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-md transition-colors"
            title={isEnabled ? 'Desactiver' : 'Activer'}
          >
            {isEnabled
              ? <EyeOff className="w-4 h-4 text-gray-500" />
              : <Eye    className="w-4 h-4 text-green-500" />
            }
          </button>
          <button
            onClick={() => handleSyncTable(table.name)}
            className="p-1.5 hover:bg-blue-100 dark:hover:bg-blue-900/30 rounded-md transition-colors"
            title="Synchroniser sur tous les agents"
          >
            <RefreshCw className="w-4 h-4 text-blue-500" />
          </button>
          <button
            onClick={() => handleEditTable(table)}
            className="p-1.5 hover:bg-blue-100 dark:hover:bg-blue-900/30 rounded-md transition-colors"
            title="Modifier"
          >
            <Edit2 className="w-4 h-4 text-blue-500" />
          </button>
          <button
            onClick={() => setDeleteConfirm(table.name)}
            className="p-1.5 hover:bg-red-100 dark:hover:bg-red-900/30 rounded-md transition-colors"
            title="Supprimer"
          >
            <Trash2 className="w-4 h-4 text-red-500" />
          </button>
        </div>
      </div>
    )
  }

  /* ── Loading ── */
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500" />
      </div>
    )
  }

  /* ── Render ── */
  return (
    <div className="h-full flex flex-col bg-slate-50 dark:bg-gray-900">

      {/* ═══ HEADER ═══ */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between">

          {/* Titre */}
          <div className="flex items-center gap-3">
            <Database className="w-6 h-6 text-primary-500" />
            <div>
              <h1 className="text-xl font-bold text-gray-900 dark:text-white">Tables ETL</h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Configuration des tables partagees entre tous les agents
              </p>
            </div>
          </div>

          {/* Notifications + Boutons utilitaires */}
          <div className="flex items-center gap-2">
            {success && (
              <span className="flex items-center gap-1.5 text-sm text-green-700 dark:text-green-300 bg-green-50 dark:bg-green-900/20 px-3 py-1.5 rounded-lg">
                <CheckCircle className="w-4 h-4" /> {success}
              </span>
            )}
            {error && (
              <span className="flex items-center gap-1.5 text-sm text-red-700 dark:text-red-300 bg-red-50 dark:bg-red-900/20 px-3 py-1.5 rounded-lg">
                <XCircle className="w-4 h-4" /> {error}
              </span>
            )}
            <button
              onClick={handleMigrateYaml}
              disabled={saving}
              className="px-3 py-2 text-sm bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 rounded-lg hover:bg-amber-200 dark:hover:bg-amber-900/50 flex items-center gap-2 disabled:opacity-50 transition-colors"
              title="Importer depuis le fichier YAML existant"
            >
              <Upload className="w-4 h-4" />
              YAML
            </button>
            <button
              onClick={handleImportFromOptiBoard}
              disabled={saving}
              className="px-3 py-2 text-sm bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded-lg hover:bg-green-200 dark:hover:bg-green-900/50 flex items-center gap-2 disabled:opacity-50 transition-colors"
              title="Importer depuis OptiBoard.SyncQuery"
            >
              <Download className="w-4 h-4" />
              OptiBoard
            </button>
            <button
              onClick={openBulkTestModal}
              disabled={saving || tables.length === 0}
              className="px-3 py-2 text-sm bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 rounded-lg hover:bg-primary-200 dark:hover:bg-primary-900/50 flex items-center gap-2 disabled:opacity-50 transition-colors"
              title="Tester les performances BULK INSERT"
            >
              <FlaskConical className="w-4 h-4" />
              Test
            </button>
          </div>
        </div>
      </div>

      {/* ═══ CONTENU ═══ */}
      <div className="flex-1 p-6 overflow-auto">
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm">

          {/* Barre d'outils */}
          <div className="p-4 border-b border-gray-200 dark:border-gray-700 space-y-3">

            {/* Ligne 1: Titre + bouton Nouvelle Table */}
            <div className="flex items-center justify-between">
              <h2 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                <Layers className="w-5 h-5 text-primary-500" />
                Configuration Tables ETL
                <span className="text-sm font-normal text-gray-400">({tableCounts.all} tables)</span>
              </h2>
              <button
                onClick={handleAddTable}
                className="btn-primary flex items-center gap-2"
              >
                <Plus className="w-4 h-4" />
                Nouvelle Table
              </button>
            </div>

            {/* Ligne 2: Recherche + onglets filtres + options */}
            <div className="flex items-center gap-3 flex-wrap">

              {/* Recherche */}
              <div className="relative flex-1 min-w-[180px] max-w-sm">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Rechercher une table..."
                  className="w-full pl-10 pr-8 py-2 text-sm border border-primary-300 dark:border-primary-600 rounded-lg
                             bg-white dark:bg-gray-700 focus:ring-2 focus:ring-primary-500 focus:border-transparent
                             text-gray-900 dark:text-white"
                />
                {searchTerm && (
                  <button
                    onClick={() => setSearchTerm('')}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>

              {/* Onglets filtres (comme menu) */}
              <div className="flex items-center gap-1 bg-gray-100 dark:bg-gray-700 rounded-lg p-1">
                {[
                  { key: 'all',         label: 'Tous',        count: tableCounts.all         },
                  { key: 'incremental', label: 'Incremental', count: tableCounts.incremental  },
                  { key: 'full',        label: 'Full Sync',   count: tableCounts.full         },
                  { key: 'high',        label: 'Prioritaire', count: tableCounts.high         },
                  { key: 'normal',      label: 'Normal',      count: tableCounts.normal       },
                  { key: 'low',         label: 'Basse',       count: tableCounts.low          },
                ].map(tab => (
                  <button
                    key={tab.key}
                    onClick={() => setFilterMode(tab.key)}
                    className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                      filterMode === tab.key
                        ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm'
                        : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
                    }`}
                  >
                    {tab.label} ({tab.count})
                  </button>
                ))}
              </div>

              {/* Toggle inactives */}
              <button
                onClick={() => setShowDisabled(!showDisabled)}
                className={`flex items-center gap-2 px-3 py-2 text-xs font-medium rounded-lg border transition-colors ${
                  showDisabled
                    ? 'bg-gray-100 dark:bg-gray-700 border-primary-300 dark:border-primary-600 text-gray-700 dark:text-gray-300'
                    : 'bg-orange-100 border-orange-300 text-orange-700'
                }`}
              >
                {showDisabled ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                {showDisabled ? 'Inactives visibles' : 'Inactives masquees'}
              </button>

              {/* Boutons utilitaires (actualiser + tout supprimer) */}
              <div className="flex items-center gap-1 border-l border-primary-300 dark:border-primary-600 pl-3">
                <button
                  onClick={loadData}
                  className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                  title="Actualiser"
                >
                  <RefreshCw className="w-4 h-4 text-gray-500" />
                </button>
                {tables.length > 0 && (
                  <button
                    onClick={() => setDeleteAllConfirm(true)}
                    disabled={saving}
                    className="p-2 hover:bg-red-100 dark:hover:bg-red-900/30 rounded-lg transition-colors disabled:opacity-50"
                    title="Supprimer toutes les tables ETL"
                  >
                    <Trash2 className="w-4 h-4 text-red-500" />
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Liste des tables */}
          <div className="p-4">
            {tables.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                <Database className="w-12 h-12 mx-auto mb-3 opacity-30" />
                <p className="font-medium">Aucune table ETL configuree</p>
                <button
                  onClick={handleAddTable}
                  className="mt-4 text-primary-600 hover:underline text-sm"
                >
                  Configurer la premiere table ETL
                </button>
              </div>
            ) : filteredTables.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                <Search className="w-12 h-12 mx-auto mb-3 opacity-30" />
                <p>Aucune table ne correspond aux filtres</p>
                <button
                  onClick={() => { setSearchTerm(''); setFilterMode('all') }}
                  className="mt-4 text-primary-600 hover:underline text-sm"
                >
                  Reinitialiser les filtres
                </button>
              </div>
            ) : (
              <div className="space-y-0.5">
                {filteredTables.map(table => renderTableRow(table))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ═══ MODAL : Confirmation suppression totale ═══ */}
      {deleteAllConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4 shadow-xl">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Supprimer toutes les tables ETL ?
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              Cette action va supprimer les <strong>{tables.length} tables</strong> configurees.
              Cette action est irreversible.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setDeleteAllConfirm(false)}
                className="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600"
              >
                Annuler
              </button>
              <button
                onClick={handleDeleteAllTables}
                disabled={saving}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 flex items-center gap-2"
              >
                {saving ? <RefreshCw size={16} className="animate-spin" /> : <Trash2 size={16} />}
                Supprimer tout
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ═══ MODAL : Confirmation suppression individuelle ═══ */}
      {deleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-3 bg-red-100 dark:bg-red-900/30 rounded-full">
                <Trash2 className="text-red-600 dark:text-red-400" size={24} />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Confirmer la suppression</h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">Cette action est irreversible</p>
              </div>
            </div>
            <p className="text-gray-700 dark:text-gray-300 mb-6">
              Etes-vous sur de vouloir supprimer la table <strong>"{deleteConfirm}"</strong> ?
              Cette action supprimera la configuration pour tous les agents.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setDeleteConfirm(null)}
                className="px-4 py-2 text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600"
              >
                Annuler
              </button>
              <button
                onClick={() => handleDeleteTable(deleteConfirm)}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
              >
                Supprimer
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ═══ MODAL : Création / Édition ═══ */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-start justify-center z-50 overflow-y-auto py-8">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full mx-4 my-auto">

            {/* Header modal */}
            <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                <Database size={20} />
                {editingTable ? 'Modifier la Table' : 'Nouvelle Table ETL'}
              </h2>
              <button
                onClick={() => setShowModal(false)}
                className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg"
              >
                <X size={20} />
              </button>
            </div>

            {/* Body modal */}
            <div className="p-6 space-y-6">

              {/* Nom + Description */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Nom de la table *
                  </label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    disabled={!!editingTable}
                    placeholder="F_DOCENTETE"
                    className="w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded-lg text-gray-900 dark:text-white disabled:opacity-50"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Description
                  </label>
                  <input
                    type="text"
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    placeholder="En-tetes documents"
                    className="w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded-lg text-gray-900 dark:text-white"
                  />
                </div>
              </div>

              {/* Source + Target */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Table source (Sage)
                  </label>
                  <input
                    type="text"
                    value={formData.source_table}
                    onChange={(e) => setFormData({ ...formData, source_table: e.target.value })}
                    placeholder="Meme que nom si vide"
                    className="w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded-lg text-gray-900 dark:text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Table cible (DWH) *
                  </label>
                  <input
                    type="text"
                    value={formData.target_table}
                    onChange={(e) => setFormData({ ...formData, target_table: e.target.value })}
                    placeholder="DWH_F_DOCENTETE"
                    className="w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded-lg text-gray-900 dark:text-white"
                  />
                </div>
              </div>

              {/* Type + Priorité */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Type de synchronisation
                  </label>
                  <select
                    value={formData.sync_type}
                    onChange={(e) => setFormData({ ...formData, sync_type: e.target.value })}
                    className="w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded-lg text-gray-900 dark:text-white"
                  >
                    <option value="incremental">Incremental</option>
                    <option value="full">Full Sync</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Priorite
                  </label>
                  <select
                    value={formData.priority}
                    onChange={(e) => setFormData({ ...formData, priority: e.target.value })}
                    className="w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded-lg text-gray-900 dark:text-white"
                  >
                    <option value="high">Haute</option>
                    <option value="normal">Normal</option>
                    <option value="low">Basse</option>
                  </select>
                </div>
              </div>

              {/* Clé primaire + Colonne incrémentale */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Cle primaire (separer par virgule)
                  </label>
                  <input
                    type="text"
                    value={formData.primary_key}
                    onChange={(e) => setFormData({ ...formData, primary_key: e.target.value })}
                    placeholder="DO_Piece, cbMarq"
                    className="w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded-lg text-gray-900 dark:text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Colonne incrementale
                  </label>
                  <input
                    type="text"
                    value={formData.incremental_column}
                    onChange={(e) => setFormData({ ...formData, incremental_column: e.target.value })}
                    placeholder="cbModification"
                    className="w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded-lg text-gray-900 dark:text-white"
                  />
                </div>
              </div>

              {/* Batch size + Actif */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Taille du batch
                  </label>
                  <input
                    type="number"
                    value={formData.batch_size}
                    onChange={(e) => setFormData({ ...formData, batch_size: parseInt(e.target.value) || 1000 })}
                    min="100" max="50000"
                    className="w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded-lg text-gray-900 dark:text-white"
                  />
                </div>
                <div className="flex items-end">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formData.enabled}
                      onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
                      className="w-5 h-5 text-primary-600 bg-gray-100 border-primary-300 rounded focus:ring-primary-500"
                    />
                    <span className="text-gray-700 dark:text-gray-300">Table active</span>
                  </label>
                </div>
              </div>

              {/* Détection des suppressions */}
              <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4">
                <label className="flex items-start gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.delete_detection}
                    onChange={(e) => setFormData({ ...formData, delete_detection: e.target.checked })}
                    className="w-5 h-5 mt-0.5 text-amber-600 bg-gray-100 border-primary-300 rounded focus:ring-amber-500"
                  />
                  <div>
                    <span className="font-medium text-amber-800 dark:text-amber-300">
                      Detection des suppressions
                    </span>
                    <p className="text-xs text-amber-700 dark:text-amber-400 mt-1">
                      Detecte et supprime du DWH les enregistrements qui n'existent plus dans la source Sage.<br />
                      <strong>Attention:</strong> Cette option peut impacter les performances sur les grosses tables (&gt;100k lignes).
                    </p>
                  </div>
                </label>
              </div>

              {/* Query SQL */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Query SQL a executer
                </label>
                <textarea
                  value={formData.query}
                  onChange={(e) => setFormData({ ...formData, query: e.target.value })}
                  placeholder="SELECT * FROM F_DOCENTETE WHERE DO_Type = 6"
                  rows={4}
                  className="w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded-lg text-gray-900 dark:text-white font-mono text-sm"
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Laissez vide pour synchroniser toute la table. Sinon, specifiez une requete SELECT personnalisee.
                </p>
              </div>
            </div>

            {/* Footer modal */}
            <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200 dark:border-gray-700">
              <button
                onClick={() => setShowModal(false)}
                className="px-4 py-2 text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600"
              >
                Annuler
              </button>
              <button
                onClick={handleSaveTable}
                disabled={saving}
                className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 flex items-center gap-2 disabled:opacity-50"
              >
                {saving ? <RefreshCw size={16} className="animate-spin" /> : <Save size={16} />}
                {editingTable ? 'Modifier' : 'Creer'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ═══ MODAL : Test BULK INSERT ═══ */}
      {showBulkTestModal && (
        <div className="fixed inset-0 bg-black/50 flex items-start justify-center z-50 overflow-y-auto py-8">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-3xl w-full mx-4 my-auto">

            <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                <FlaskConical size={20} className="text-primary-600" />
                Test Performance BULK INSERT
              </h2>
              <button
                onClick={() => { setShowBulkTestModal(false); setBulkTestResults(null) }}
                className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg"
              >
                <X size={20} />
              </button>
            </div>

            <div className="p-6 space-y-6">
              {/* Info */}
              <div className="bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <Info className="text-primary-600 dark:text-primary-400 flex-shrink-0 mt-0.5" size={18} />
                  <div className="text-sm text-primary-700 dark:text-primary-300">
                    <p className="font-medium mb-1">Ce test compare 3 methodes d'insertion:</p>
                    <ul className="list-disc list-inside space-y-1 text-primary-600 dark:text-primary-400">
                      <li><strong>fast_executemany</strong> — Methode actuelle (pyodbc optimise)</li>
                      <li><strong>INSERT VALUES multiples</strong> — Batch de 1000 valeurs par INSERT</li>
                      <li><strong>executemany standard</strong> — Version non-optimisee (reference)</li>
                    </ul>
                  </div>
                </div>
              </div>

              {/* Paramètres */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Table ETL a tester
                  </label>
                  <select
                    value={bulkTestParams.table_name}
                    onChange={(e) => setBulkTestParams({ ...bulkTestParams, table_name: e.target.value })}
                    className="w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded-lg text-gray-900 dark:text-white"
                  >
                    {tables.map(table => (
                      <option key={table.name} value={table.name}>
                        {table.name}{table.description ? ` — ${table.description}` : ''}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Nombre de lignes de test
                  </label>
                  <input
                    type="number"
                    value={bulkTestParams.row_limit}
                    onChange={(e) => setBulkTestParams({ ...bulkTestParams, row_limit: parseInt(e.target.value) || 10000 })}
                    min="1000" max="100000" step="1000"
                    className="w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded-lg text-gray-900 dark:text-white"
                  />
                </div>
              </div>

              {/* Bouton lancer */}
              <div className="flex justify-center">
                <button
                  onClick={handleRunBulkTest}
                  disabled={bulkTestRunning}
                  className="px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 flex items-center gap-2 disabled:opacity-50 font-medium"
                >
                  {bulkTestRunning
                    ? <><RefreshCw size={18} className="animate-spin" /> Test en cours...</>
                    : <><Zap size={18} /> Lancer le test</>
                  }
                </button>
              </div>

              {/* Résultats */}
              {bulkTestResults && (
                <div className="space-y-4">
                  {bulkTestResults.success ? (
                    <>
                      <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
                        <div className="flex items-center gap-2 text-green-700 dark:text-green-300 font-medium mb-2">
                          <CheckCircle size={18} />
                          Test termine avec succes
                        </div>
                        <div className="text-sm text-green-600 dark:text-green-400 space-y-1">
                          <p>Meilleure methode: <strong>{bulkTestResults.best_method}</strong></p>
                          <p>Duree totale: {(bulkTestResults.total_duration_ms / 1000).toFixed(1)}s</p>
                        </div>
                      </div>

                      <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                        <table className="w-full text-sm">
                          <thead className="bg-gray-50 dark:bg-gray-800">
                            <tr>
                              <th className="px-4 py-3 text-left font-medium text-gray-700 dark:text-gray-300">#</th>
                              <th className="px-4 py-3 text-left font-medium text-gray-700 dark:text-gray-300">Methode</th>
                              <th className="px-4 py-3 text-right font-medium text-gray-700 dark:text-gray-300">Lignes</th>
                              <th className="px-4 py-3 text-right font-medium text-gray-700 dark:text-gray-300">Duree</th>
                              <th className="px-4 py-3 text-right font-medium text-gray-700 dark:text-gray-300">Performance</th>
                              <th className="px-4 py-3 text-center font-medium text-gray-700 dark:text-gray-300">Status</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                            {bulkTestResults.results?.map((result, index) => (
                              <tr key={result.method} className={index === 0 ? 'bg-green-50 dark:bg-green-900/10' : ''}>
                                <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
                                  {index === 0 ? '🏆' : index + 1}
                                </td>
                                <td className="px-4 py-3">
                                  <span className="font-medium text-gray-900 dark:text-white">{result.method}</span>
                                  {result.note && <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{result.note}</p>}
                                </td>
                                <td className="px-4 py-3 text-right text-gray-600 dark:text-gray-400">
                                  {result.rows.toLocaleString()}
                                </td>
                                <td className="px-4 py-3 text-right text-gray-600 dark:text-gray-400">
                                  {result.duration_ms}ms
                                </td>
                                <td className="px-4 py-3 text-right">
                                  <span className={`font-medium ${index === 0 ? 'text-green-600 dark:text-green-400' : 'text-gray-900 dark:text-white'}`}>
                                    {result.rows_per_sec.toLocaleString()} rows/sec
                                  </span>
                                </td>
                                <td className="px-4 py-3 text-center">
                                  {result.status === 'success'
                                    ? <CheckCircle size={16} className="text-green-500 mx-auto" />
                                    : <XCircle    size={16} className="text-red-500 mx-auto"   />
                                  }
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>

                      <div className="bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800 rounded-lg p-4">
                        <div className="flex items-start gap-3">
                          <BarChart3 className="text-primary-600 dark:text-primary-400 flex-shrink-0 mt-0.5" size={18} />
                          <div>
                            <p className="text-sm font-medium text-primary-800 dark:text-primary-300 mb-1">Recommandation</p>
                            <p className="text-sm text-primary-700 dark:text-primary-400">{bulkTestResults.recommendation}</p>
                          </div>
                        </div>
                      </div>
                    </>
                  ) : (
                    <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
                      <div className="flex items-center gap-2 text-red-700 dark:text-red-300">
                        <XCircle size={18} />
                        <span className="font-medium">Erreur: {bulkTestResults.error}</span>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200 dark:border-gray-700">
              <button
                onClick={() => { setShowBulkTestModal(false); setBulkTestResults(null) }}
                className="px-4 py-2 text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600"
              >
                Fermer
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
