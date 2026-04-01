import { useState, useEffect } from 'react'
import {
  X, Server, Settings, Database, RefreshCw, Trash2, Key,
  CheckCircle, XCircle, Clock, Save, Power, PowerOff, Edit3, Plus
} from 'lucide-react'
import {
  getAgent, updateAgent, deleteAgent, regenerateApiKey,
  getAgentTables, triggerTableSync, getAvailableETLTables,
  deleteETLTable, toggleETLTable, syncAgentTablesWithConfig, deleteAllAgentTables,
  updateETLTable, createETLTable
} from '../../services/etlApi'
import { extractErrorMessage } from '../../services/api'

const tabs = [
  { id: 'info', label: 'Informations', icon: Server },
  { id: 'tables', label: 'Tables', icon: Database },
  { id: 'settings', label: 'Parametres', icon: Settings }
]

export default function AgentDetailModal({ agent: initialAgent, onClose, onUpdated }) {
  const [activeTab, setActiveTab] = useState('info')
  const [agent, setAgent] = useState(initialAgent)
  const [tables, setTables] = useState([])  // Tables configurees pour cet agent
  const [availableTables, setAvailableTables] = useState([])  // Tables ETL disponibles (partagees)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)

  // Edition
  const [editMode, setEditMode] = useState(false)
  const [editData, setEditData] = useState({})

  // Edition table ETL
  const [editingTable, setEditingTable] = useState(null)
  const [tableEditData, setTableEditData] = useState({})
  const [showAddTable, setShowAddTable] = useState(false)

  useEffect(() => {
    loadData()
  }, [initialAgent.agent_id])

  const loadData = async () => {
    try {
      const [agentRes, tablesRes, availableRes] = await Promise.all([
        getAgent(initialAgent.agent_id),
        getAgentTables(initialAgent.agent_id),
        getAvailableETLTables()
      ])
      // Support both formats: direct object or {data: {...}} or {tables: [...]}
      const agentData = agentRes.data?.data || agentRes.data
      const tablesData = tablesRes.data?.data || tablesRes.data || []
      // Format pour available: {success: true, tables: [...]}
      const availableData = availableRes.data?.tables || availableRes.data?.data || availableRes.data || []

      setAgent(agentData)
      setTables(Array.isArray(tablesData) ? tablesData : [])
      setAvailableTables(Array.isArray(availableData) ? availableData : [])
      setEditData({
        name: agentData.name || agentData.nom || '',
        description: agentData.description || '',
        sync_interval_seconds: agentData.sync_interval_seconds || agentData.sync_interval_secondes || 300,
        heartbeat_interval_seconds: agentData.heartbeat_interval_seconds || agentData.heartbeat_interval_secondes || 30,
        batch_size: agentData.batch_size || 10000,
        is_active: agentData.is_active ?? 1,
        sage_server: agentData.sage_server || '',
        sage_database: agentData.sage_database || '',
        sage_username: agentData.sage_username || '',
        sage_password: ''
      })
    } catch (err) {
      console.error('Erreur chargement:', err)
      setError('Erreur lors du chargement')
    }
  }

  const handleSave = async () => {
    setLoading(true)
    setError(null)
    try {
      // Ne pas envoyer sage_password si vide (pour ne pas ecraser l'existant)
      const dataToSend = { ...editData }
      if (!dataToSend.sage_password) {
        delete dataToSend.sage_password
      }
      await updateAgent(agent.agent_id, dataToSend)
      setSuccess('Agent mis a jour')
      setEditMode(false)
      loadData()
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(extractErrorMessage(err, 'Erreur lors de la mise a jour'))
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async () => {
    if (!confirm('Supprimer cet agent ? Cette action est irreversible.')) return

    setLoading(true)
    try {
      await deleteAgent(agent.agent_id)
      onUpdated()
    } catch (err) {
      setError(extractErrorMessage(err, 'Erreur lors de la suppression'))
      setLoading(false)
    }
  }

  const handleRegenerateKey = async () => {
    if (!confirm('Regenerer la cle API ? L\'agent devra etre reconfigure.')) return

    setLoading(true)
    try {
      const res = await regenerateApiKey(agent.agent_id)
      if (res.data.success) {
        const newKey = res.data.data.api_key
        // Copier automatiquement dans le presse-papiers
        try {
          await navigator.clipboard.writeText(newKey)
          alert(`Nouvelle cle API:\n\n${newKey}\n\n✓ La cle a ete copiee dans le presse-papiers!`)
        } catch (clipboardErr) {
          // Si le clipboard echoue, afficher quand meme la cle
          alert(`Nouvelle cle API:\n\n${newKey}\n\nSauvegardez-la maintenant!`)
        }
      }
    } catch (err) {
      setError(extractErrorMessage(err, 'Erreur lors de la regeneration'))
    } finally {
      setLoading(false)
    }
  }

  const handleSyncTable = async (tableName) => {
    try {
      await triggerTableSync(agent.agent_id, tableName)
      setSuccess(`Synchronisation de ${tableName} declenchee`)
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(extractErrorMessage(err, 'Erreur sync'))
    }
  }

  const handleToggleTable = async (tableName) => {
    try {
      await toggleETLTable(tableName)
      setSuccess(`Table ${tableName} mise a jour`)
      loadData()
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(extractErrorMessage(err, 'Erreur lors de la mise a jour'))
    }
  }

  const handleDeleteTable = async (tableName) => {
    if (!confirm(`Supprimer la table "${tableName}" ? Cette action est irreversible.`)) return

    try {
      await deleteETLTable(tableName)
      setSuccess(`Table ${tableName} supprimee`)
      loadData()
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(extractErrorMessage(err, 'Erreur lors de la suppression'))
    }
  }

  const handleSyncTablesWithConfig = async () => {
    if (!confirm('Resynchroniser les tables de cet agent avec la configuration globale ETL ?\nCela supprimera les anciennes tables et importera celles de la config.')) return

    setLoading(true)
    try {
      const res = await syncAgentTablesWithConfig(agent.agent_id)
      setSuccess(`Synchronisation terminee: ${res.data.deleted} supprimees, ${res.data.added} importees`)
      loadData()
      setTimeout(() => setSuccess(null), 5000)
    } catch (err) {
      setError(extractErrorMessage(err, 'Erreur lors de la synchronisation'))
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteAllAgentTables = async () => {
    if (!confirm('Supprimer toutes les tables de cet agent ? Cette action est irreversible.')) return

    setLoading(true)
    try {
      const res = await deleteAllAgentTables(agent.agent_id)
      setSuccess(`${res.data.deleted} tables supprimees`)
      loadData()
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(extractErrorMessage(err, 'Erreur lors de la suppression'))
    } finally {
      setLoading(false)
    }
  }

  // Ouvrir le modal d'edition de table
  const handleEditTable = (table) => {
    setEditingTable(table)
    setTableEditData({
      name: table.name,
      target_table: table.target_table,
      sync_type: table.sync_type || 'full',
      priority: table.priority || 'normal',
      timestamp_column: table.timestamp_column || '',
      description: table.description || '',
      interval_minutes: table.interval_minutes || 5,
      delete_detection: table.delete_detection || false
    })
  }

  // Sauvegarder les modifications de table
  const handleSaveTable = async () => {
    if (!editingTable) return

    setLoading(true)
    try {
      await updateETLTable(editingTable.name, tableEditData)
      setSuccess(`Table "${editingTable.name}" mise a jour`)
      setEditingTable(null)
      loadData()
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(extractErrorMessage(err, 'Erreur lors de la mise a jour'))
    } finally {
      setLoading(false)
    }
  }

  // Creer une nouvelle table
  const handleCreateTable = async () => {
    if (!tableEditData.name || !tableEditData.target_table) {
      setError('Nom et table cible requis')
      return
    }

    setLoading(true)
    try {
      await createETLTable(tableEditData)
      setSuccess(`Table "${tableEditData.name}" creee`)
      setShowAddTable(false)
      setTableEditData({})
      loadData()
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(extractErrorMessage(err, 'Erreur lors de la creation'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-3xl mx-4 max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <Server size={24} className="text-primary-600" />
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">{agent.name || agent.nom}</h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">{agent.dwh_code}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1 text-gray-500 hover:text-gray-700">
            <X size={20} />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-200 dark:border-gray-700">
          {tabs.map(tab => (
            <button
              key={tab.id}
              className={`flex-1 px-4 py-3 text-sm font-medium flex items-center justify-center gap-2 transition-colors ${
                activeTab === tab.id
                  ? 'text-primary-600 border-b-2 border-primary-600'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
              onClick={() => setActiveTab(tab.id)}
            >
              <tab.icon size={16} />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Messages */}
        {error && (
          <div className="mx-4 mt-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 rounded-lg text-sm">
            {error}
          </div>
        )}
        {success && (
          <div className="mx-4 mt-4 p-3 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300 rounded-lg text-sm">
            {success}
          </div>
        )}

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {activeTab === 'info' && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <InfoItem label="ID Agent" value={agent.agent_id} mono />
                <InfoItem label="Status" value={agent.status || agent.statut} />
                <InfoItem label="Sante" value={agent.health_status} />
                <InfoItem label="Hostname" value={agent.hostname || '-'} />
                <InfoItem label="IP" value={agent.ip_address || '-'} />
                <InfoItem label="Version" value={agent.agent_version || '-'} />
                <InfoItem label="Dernier heartbeat" value={formatDate(agent.last_heartbeat)} />
                <InfoItem label="Derniere sync" value={formatDate(agent.last_sync)} />
                <InfoItem label="Total syncs" value={agent.total_syncs} />
                <InfoItem label="Lignes synchronisees" value={agent.total_rows_synced?.toLocaleString()} />
                <InfoItem label="Echecs consecutifs" value={agent.consecutive_failures} />
                <InfoItem label="Tables actives" value={agent.tables_count} />
              </div>

              {agent.last_error && (
                <div className="bg-red-50 dark:bg-red-900/20 p-3 rounded-lg">
                  <h4 className="text-sm font-medium text-red-800 dark:text-red-300 mb-1">Derniere erreur</h4>
                  <p className="text-sm text-red-600 dark:text-red-400">{agent.last_error}</p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'tables' && (
            <div className="space-y-4">
              {/* En-tete avec info */}
              <div className="bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800 rounded-lg p-3">
                <p className="text-sm text-primary-700 dark:text-primary-300">
                  <strong>Tables ETL partagees</strong> - Ces tables sont synchronisees par tous les agents.
                  Le statut ci-dessous indique l'etat de synchronisation pour cet agent.
                </p>
              </div>

              {/* Stats resumees */}
              <div className="grid grid-cols-4 gap-3">
                <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">{availableTables.length}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Tables disponibles</p>
                </div>
                <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-green-600 dark:text-green-400">
                    {tables.filter(t => t.last_sync_status === 'success').length}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Sync OK</p>
                </div>
                <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-red-600 dark:text-red-400">
                    {tables.filter(t => t.last_sync_status === 'error').length}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">En erreur</p>
                </div>
                <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-gray-600 dark:text-gray-400">
                    {availableTables.length - tables.length}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Non sync</p>
                </div>
              </div>

              {/* Boutons de gestion */}
              <div className="flex gap-2 flex-wrap">
                <button
                  onClick={() => {
                    setShowAddTable(true)
                    setTableEditData({
                      name: '',
                      target_table: '',
                      sync_type: 'full',
                      priority: 'normal',
                      timestamp_column: '',
                      description: '',
                      interval_minutes: 5,
                      delete_detection: false
                    })
                  }}
                  disabled={loading}
                  className="px-3 py-1.5 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded hover:bg-green-200 dark:hover:bg-green-900/50 text-sm flex items-center gap-1 disabled:opacity-50"
                  title="Ajouter une nouvelle table ETL"
                >
                  <Plus size={14} />
                  Ajouter table
                </button>
                <button
                  onClick={handleSyncTablesWithConfig}
                  disabled={loading}
                  className="px-3 py-1.5 bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 rounded hover:bg-primary-200 dark:hover:bg-primary-900/50 text-sm flex items-center gap-1 disabled:opacity-50"
                  title="Resynchroniser les tables avec la config globale ETL"
                >
                  <RefreshCw size={14} />
                  Sync avec config
                </button>
                <button
                  onClick={handleDeleteAllAgentTables}
                  disabled={loading}
                  className="px-3 py-1.5 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded hover:bg-red-200 dark:hover:bg-red-900/50 text-sm flex items-center gap-1 disabled:opacity-50"
                  title="Supprimer toutes les tables de cet agent"
                >
                  <Trash2 size={14} />
                  Vider tables
                </button>
              </div>

              {/* Liste des tables ETL disponibles */}
              <div className="space-y-2">
                <h4 className="font-medium text-gray-900 dark:text-white flex items-center gap-2">
                  <Database size={16} />
                  Tables ETL ({availableTables.length})
                </h4>

                <div className="space-y-2">
                  {availableTables.map(availTable => {
                    // Trouver le statut de sync pour cet agent
                    const agentTableStatus = tables.find(t => t.table_name === availTable.name)

                    return (
                      <div
                        key={availTable.name}
                        className="rounded-lg border bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 overflow-hidden"
                      >
                        <div className="px-4 py-3 flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <Database
                              size={18}
                              className={agentTableStatus ? 'text-primary-600' : 'text-gray-400'}
                            />
                            <div>
                              <h4 className="font-semibold text-gray-900 dark:text-white">
                                {availTable.name}
                              </h4>
                              <p className="text-xs text-gray-500 dark:text-gray-400">
                                {availTable.description || `→ ${availTable.target_table}`}
                              </p>
                            </div>
                          </div>

                          <div className="flex items-center gap-2">
                            {/* Badge type sync */}
                            <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                              availTable.sync_type === 'incremental'
                                ? 'bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400'
                                : 'bg-primary-200 text-primary-800 dark:bg-primary-900/40 dark:text-primary-300'
                            }`}>
                              {availTable.sync_type === 'incremental' ? 'Incr.' : 'Full'}
                            </span>

                            {/* Badge priorite */}
                            <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                              availTable.priority === 'high'
                                ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400'
                                : availTable.priority === 'low'
                                ? 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
                                : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
                            }`}>
                              {availTable.priority === 'high' ? 'Prioritaire' : availTable.priority === 'low' ? 'Basse' : 'Normal'}
                            </span>

                            {/* Badge statut sync agent */}
                            {agentTableStatus ? (
                              <span className={`px-2 py-0.5 text-xs font-medium rounded-full flex items-center gap-1 ${
                                agentTableStatus.last_sync_status === 'success'
                                  ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                                  : agentTableStatus.last_sync_status === 'error'
                                  ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                                  : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                              }`}>
                                {agentTableStatus.last_sync_status === 'success' ? (
                                  <><CheckCircle size={12} /> OK</>
                                ) : agentTableStatus.last_sync_status === 'error' ? (
                                  <><XCircle size={12} /> Erreur</>
                                ) : (
                                  <><Clock size={12} /> En attente</>
                                )}
                              </span>
                            ) : (
                              <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400">
                                Non sync
                              </span>
                            )}

                            {/* Bouton Editer */}
                            <button
                              className="px-2 py-1 text-xs bg-yellow-50 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400 rounded hover:bg-yellow-100 dark:hover:bg-yellow-900/50 flex items-center gap-1"
                              onClick={() => handleEditTable(availTable)}
                              title="Editer la table"
                            >
                              <Edit3 size={12} />
                            </button>

                            {/* Bouton Activer/Desactiver */}
                            <button
                              className={`px-2 py-1 text-xs rounded flex items-center gap-1 ${
                                availTable.is_enabled !== false
                                  ? 'bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400 hover:bg-green-100 dark:hover:bg-green-900/50'
                                  : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600'
                              }`}
                              onClick={() => handleToggleTable(availTable.name)}
                              title={availTable.is_enabled !== false ? 'Desactiver la table' : 'Activer la table'}
                            >
                              {availTable.is_enabled !== false ? <Power size={12} /> : <PowerOff size={12} />}
                            </button>

                            {/* Bouton sync */}
                            <button
                              className="px-2 py-1 text-xs bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400 rounded hover:bg-primary-100 dark:hover:bg-primary-900/50 flex items-center gap-1"
                              onClick={() => handleSyncTable(availTable.name)}
                              title="Synchroniser maintenant"
                            >
                              <RefreshCw size={12} />
                            </button>

                            {/* Bouton supprimer */}
                            <button
                              className="px-2 py-1 text-xs bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-400 rounded hover:bg-red-100 dark:hover:bg-red-900/50 flex items-center gap-1"
                              onClick={() => handleDeleteTable(availTable.name)}
                              title="Supprimer la table"
                            >
                              <Trash2 size={12} />
                            </button>
                          </div>
                        </div>

                        {/* Details si synchro existe */}
                        {agentTableStatus && (
                          <div className="px-4 py-2 bg-gray-50 dark:bg-gray-900/50 border-t border-gray-100 dark:border-gray-700">
                            <div className="flex items-center gap-6 text-xs text-gray-500 dark:text-gray-400">
                              <span>
                                <Clock size={12} className="inline mr-1" />
                                Derniere sync: <strong className="text-gray-700 dark:text-gray-300">
                                  {agentTableStatus.last_sync ? formatDate(agentTableStatus.last_sync) : 'Jamais'}
                                </strong>
                              </span>
                              {agentTableStatus.last_sync_rows > 0 && (
                                <span>
                                  Lignes: <strong className="text-gray-700 dark:text-gray-300">
                                    {agentTableStatus.last_sync_rows?.toLocaleString()}
                                  </strong>
                                </span>
                              )}
                              {agentTableStatus.societe_code && (
                                <span>
                                  Societe: <strong className="text-gray-700 dark:text-gray-300">
                                    {agentTableStatus.societe_code}
                                  </strong>
                                </span>
                              )}
                            </div>
                            {agentTableStatus.last_error && (
                              <p className="text-xs text-red-600 dark:text-red-400 mt-1 truncate">
                                Erreur: {agentTableStatus.last_error}
                              </p>
                            )}
                          </div>
                        )}
                      </div>
                    )
                  })}

                  {availableTables.length === 0 && (
                    <div className="text-center py-8 bg-gray-50 dark:bg-gray-900 rounded-lg">
                      <Database size={40} className="mx-auto text-gray-300 dark:text-gray-600 mb-3" />
                      <p className="text-gray-500 dark:text-gray-400">Aucune table ETL configuree</p>
                      <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">
                        Configurez les tables ETL dans le fichier de configuration
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'settings' && (
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <h3 className="font-medium text-gray-900 dark:text-white">Parametres</h3>
                {!editMode ? (
                  <button
                    className="px-3 py-1.5 text-sm bg-primary-600 text-white rounded hover:bg-primary-700"
                    onClick={() => setEditMode(true)}
                  >
                    Modifier
                  </button>
                ) : (
                  <div className="flex gap-2">
                    <button
                      className="px-3 py-1.5 text-sm bg-gray-200 dark:bg-gray-700 rounded"
                      onClick={() => setEditMode(false)}
                    >
                      Annuler
                    </button>
                    <button
                      className="px-3 py-1.5 text-sm bg-primary-600 text-white rounded flex items-center gap-1"
                      onClick={handleSave}
                      disabled={loading}
                    >
                      <Save size={14} />
                      Sauvegarder
                    </button>
                  </div>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">Nom</label>
                  <input
                    type="text"
                    className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded"
                    value={editData.name || ''}
                    onChange={(e) => setEditData({ ...editData, name: e.target.value })}
                    disabled={!editMode}
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">Actif</label>
                  <select
                    className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded"
                    value={editData.is_active ? '1' : '0'}
                    onChange={(e) => setEditData({ ...editData, is_active: e.target.value === '1' })}
                    disabled={!editMode}
                  >
                    <option value="1">Oui</option>
                    <option value="0">Non</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">Intervalle sync (s)</label>
                  <input
                    type="number"
                    className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded"
                    value={editData.sync_interval_seconds || 300}
                    onChange={(e) => setEditData({ ...editData, sync_interval_seconds: parseInt(e.target.value) })}
                    disabled={!editMode}
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">Heartbeat (s)</label>
                  <input
                    type="number"
                    className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded"
                    value={editData.heartbeat_interval_seconds || 30}
                    onChange={(e) => setEditData({ ...editData, heartbeat_interval_seconds: parseInt(e.target.value) })}
                    disabled={!editMode}
                  />
                </div>
                <div className="col-span-2">
                  <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">Description</label>
                  <textarea
                    className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded"
                    value={editData.description || ''}
                    onChange={(e) => setEditData({ ...editData, description: e.target.value })}
                    disabled={!editMode}
                    rows={2}
                  />
                </div>
              </div>

              {/* Section Connexion Sage */}
              <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
                <h4 className="font-medium text-gray-900 dark:text-white mb-3 flex items-center gap-2">
                  <Database size={16} />
                  Connexion Base Sage
                </h4>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">Serveur SQL</label>
                    <input
                      type="text"
                      className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded"
                      value={editData.sage_server || ''}
                      onChange={(e) => setEditData({ ...editData, sage_server: e.target.value })}
                      disabled={!editMode}
                      placeholder="localhost ou IP"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">Base de donnees</label>
                    <input
                      type="text"
                      className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded"
                      value={editData.sage_database || ''}
                      onChange={(e) => setEditData({ ...editData, sage_database: e.target.value })}
                      disabled={!editMode}
                      placeholder="NomBaseSage"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">Utilisateur SQL</label>
                    <input
                      type="text"
                      className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded"
                      value={editData.sage_username || ''}
                      onChange={(e) => setEditData({ ...editData, sage_username: e.target.value })}
                      disabled={!editMode}
                      placeholder="sa"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">Mot de passe SQL</label>
                    <input
                      type="password"
                      className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded"
                      value={editData.sage_password || ''}
                      onChange={(e) => setEditData({ ...editData, sage_password: e.target.value })}
                      disabled={!editMode}
                      placeholder="Laisser vide pour ne pas changer"
                    />
                  </div>
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                  Ces informations permettent a l'agent de se connecter a la base Sage pour synchroniser les donnees.
                </p>
              </div>

              <div className="pt-4 border-t border-gray-200 dark:border-gray-700 space-y-3">
                <h4 className="font-medium text-gray-900 dark:text-white">Actions dangereuses</h4>
                <div className="flex gap-3">
                  <button
                    className="px-4 py-2 bg-yellow-100 text-yellow-700 rounded hover:bg-yellow-200 flex items-center gap-2"
                    onClick={handleRegenerateKey}
                    disabled={loading}
                  >
                    <Key size={16} />
                    Regenerer cle API
                  </button>
                  <button
                    className="px-4 py-2 bg-red-100 text-red-700 rounded hover:bg-red-200 flex items-center gap-2"
                    onClick={handleDelete}
                    disabled={loading}
                  >
                    <Trash2 size={16} />
                    Supprimer agent
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Modal Edition Table ETL */}
        {(editingTable || showAddTable) && (
          <div className="fixed inset-0 z-60 flex items-center justify-center bg-black/50">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-2xl mx-4 max-h-[80vh] overflow-hidden flex flex-col">
              {/* Header */}
              <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
                <div className="flex items-center gap-3">
                  <Database size={20} className="text-primary-600" />
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                    {showAddTable ? 'Nouvelle table ETL' : `Editer: ${editingTable?.name}`}
                  </h3>
                </div>
                <button
                  onClick={() => { setEditingTable(null); setShowAddTable(false); }}
                  className="p-1 text-gray-500 hover:text-gray-700"
                >
                  <X size={20} />
                </button>
              </div>

              {/* Form */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Nom de la table *
                    </label>
                    <input
                      type="text"
                      className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded focus:ring-2 focus:ring-primary-500"
                      value={tableEditData.name || ''}
                      onChange={(e) => setTableEditData({ ...tableEditData, name: e.target.value })}
                      disabled={!!editingTable}
                      placeholder="Ex: Liste des clients"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Table cible (DWH) *
                    </label>
                    <input
                      type="text"
                      className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded focus:ring-2 focus:ring-primary-500"
                      value={tableEditData.target_table || ''}
                      onChange={(e) => setTableEditData({ ...tableEditData, target_table: e.target.value })}
                      placeholder="Ex: Clients"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Type de sync
                    </label>
                    <select
                      className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded"
                      value={tableEditData.sync_type || 'full'}
                      onChange={(e) => setTableEditData({ ...tableEditData, sync_type: e.target.value })}
                    >
                      <option value="full">Full (complet)</option>
                      <option value="incremental">Incremental</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Priorite
                    </label>
                    <select
                      className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded"
                      value={tableEditData.priority || 'normal'}
                      onChange={(e) => setTableEditData({ ...tableEditData, priority: e.target.value })}
                    >
                      <option value="high">Haute</option>
                      <option value="normal">Normale</option>
                      <option value="low">Basse</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Intervalle (min)
                    </label>
                    <input
                      type="number"
                      min="1"
                      className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded"
                      value={tableEditData.interval_minutes || 5}
                      onChange={(e) => setTableEditData({ ...tableEditData, interval_minutes: parseInt(e.target.value) || 5 })}
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Colonne timestamp (pour sync incremental)
                  </label>
                  <input
                    type="text"
                    className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded"
                    value={tableEditData.timestamp_column || ''}
                    onChange={(e) => setTableEditData({ ...tableEditData, timestamp_column: e.target.value })}
                    placeholder="Ex: cbModification, DO_Date"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Description
                  </label>
                  <textarea
                    className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded"
                    value={tableEditData.description || ''}
                    onChange={(e) => setTableEditData({ ...tableEditData, description: e.target.value })}
                    rows={2}
                    placeholder="Description de la table..."
                  />
                </div>

                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="delete_detection"
                    checked={tableEditData.delete_detection || false}
                    onChange={(e) => setTableEditData({ ...tableEditData, delete_detection: e.target.checked })}
                    className="w-4 h-4 text-primary-600 rounded"
                  />
                  <label htmlFor="delete_detection" className="text-sm text-gray-700 dark:text-gray-300">
                    Detection des suppressions (compare source/destination)
                  </label>
                </div>
              </div>

              {/* Footer */}
              <div className="flex justify-end gap-3 p-4 border-t border-gray-200 dark:border-gray-700">
                <button
                  onClick={() => { setEditingTable(null); setShowAddTable(false); }}
                  className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-300 dark:hover:bg-gray-600"
                >
                  Annuler
                </button>
                <button
                  onClick={showAddTable ? handleCreateTable : handleSaveTable}
                  disabled={loading}
                  className="px-4 py-2 bg-primary-600 text-white rounded hover:bg-primary-700 flex items-center gap-2 disabled:opacity-50"
                >
                  <Save size={16} />
                  {showAddTable ? 'Creer' : 'Sauvegarder'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function InfoItem({ label, value, mono }) {
  return (
    <div>
      <span className="text-sm text-gray-500 dark:text-gray-400">{label}</span>
      <p className={`text-gray-900 dark:text-white ${mono ? 'font-mono text-xs break-all' : ''}`}>
        {value || '-'}
      </p>
    </div>
  )
}

function formatDate(dateStr) {
  if (!dateStr) return 'Jamais'
  return new Date(dateStr).toLocaleString('fr-FR')
}
