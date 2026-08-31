import { useState, useEffect, useCallback } from 'react'
import {
  Server, Database, RefreshCw, Plus, Settings, Activity,
  CheckCircle, XCircle, AlertTriangle, Clock, Pause, Play,
  Trash2, Eye, Download, Upload, Zap, Layers, BarChart3
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import Loading from '../components/common/Loading'
import AgentList from '../components/ETLAdmin/AgentList'
import AgentDetailModal from '../components/ETLAdmin/AgentDetailModal'
import CreateAgentModal from '../components/ETLAdmin/CreateAgentModal'
import SyncLogViewer from '../components/ETLAdmin/SyncLogViewer'
import ETLTablesAdmin from '../components/dwh/ETLTablesAdmin'
import ETLClientTablesConfig from '../components/ETLAdmin/ETLClientTablesConfig'
import SyncMonitoringDashboard from '../components/ETLAdmin/SyncMonitoringDashboard'
import { useAuth } from '../context/AuthContext'
import {
  getAgents,
  getETLStats,
  getDWHList,
  triggerSync,
  pauseAgent,
  resumeAgent,
  deleteAgent,
  syncPublishedTables,
  downloadSageAgent
} from '../services/etlApi'

// Onglets de l'administration ETL
const ETL_TABS_CLIENT = [
  { id: 'agents',     label: 'Agents',      icon: Server   },
  { id: 'monitoring', label: 'Monitoring',  icon: BarChart3 },
]
const ETL_TABS_EDITOR = [
  { id: 'agents',     label: 'Agents',      icon: Server   },
  { id: 'monitoring', label: 'Monitoring',  icon: BarChart3 },
  { id: 'tables',     label: 'Tables ETL',  icon: Database  },
]

export default function ETLAdmin() {
  const { user } = useAuth()
  const currentDWH = (() => { try { return JSON.parse(localStorage.getItem('currentDWH') || sessionStorage.getItem('currentDWH')) } catch { return null } })()

  // Détection portail client — multi-critères pour couvrir anciennes sessions et nouvelles :
  // 1. from_client_db=true   → nouveau flag backend (sessions récentes)
  // 2. role_global=admin_client → rôle exclusivement client (toutes sessions)
  // 3. Superadmin central KASOFT → jamais isClientPortal
  const isSuperAdmin   = user?.role_global === 'superadmin' || user?.role === 'superadmin'
  const isClientPortal = !isSuperAdmin && (
    user?.from_client_db === true ||
    user?.role_global === 'admin_client' ||
    user?.role === 'admin_client' ||
    user?.dwh_code != null          // dwh_code présent → user issu d'une base client
  )

  const [loading, setLoading] = useState(true)
  const [agents, setAgents] = useState([])
  const [dwhList, setDwhList] = useState([])
  const [selectedAgent, setSelectedAgent] = useState(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showDownloadPicker, setShowDownloadPicker] = useState(false)
  const [showDetailModal, setShowDetailModal] = useState(false)
  const [showLogsModal, setShowLogsModal] = useState(false)
  const [error, setError] = useState(null)
  const [successMsg, setSuccessMsg] = useState(null)
  const [refreshing, setRefreshing] = useState(false)
  const [downloadingAgent, setDownloadingAgent] = useState(false)

  // Onglet actif
  const [activeTab, setActiveTab] = useState('agents')

  // Filtres
  const [filterDwh, setFilterDwh] = useState('')
  const [filterStatus, setFilterStatus] = useState('')

  // Stats globales
  const [globalStats, setGlobalStats] = useState({
    total: 0,
    active: 0,
    syncing: 0,
    error: 0,
    inactive: 0
  })

  const loadData = useCallback(async () => {
    try {
      const params = {}
      if (filterStatus) params.status = filterStatus
      if (!isClientPortal && filterDwh) params.dwh_code = filterDwh

      const [agentsRes, dwhRes] = await Promise.all([
        // Superadmin → header 'CENTRAL' pour bypass X-DWH-Code auto
        getAgents(params, isSuperAdmin),
        isClientPortal
          ? Promise.resolve({ data: { data: [] } })
          : getDWHList().catch(() => ({ data: { data: [] } }))
      ])

      // Support both formats: {data: [...]} and {success: true, data: [...]}
      const agentsData = agentsRes.data
      const agentsList = Array.isArray(agentsData) ? agentsData : (agentsData?.data || [])
      setAgents(agentsList)

      const dwhData = dwhRes.data
      setDwhList(Array.isArray(dwhData) ? dwhData : (dwhData?.data || []))

      // Calculer les stats
      const stats = {
        total: agentsList.length,
        active: agentsList.filter(a => a.status === 'active').length,
        syncing: agentsList.filter(a => a.status === 'syncing').length,
        error: agentsList.filter(a => a.status === 'error').length,
        inactive: agentsList.filter(a => a.status === 'inactive').length
      }
      setGlobalStats(stats)

    } catch (error) {
      console.error('Erreur chargement agents:', error)
      setError('Erreur lors du chargement des agents')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [filterDwh, filterStatus])

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 30000)
    return () => clearInterval(interval)
  }, [loadData])

  // Auto-dismiss toasts
  useEffect(() => {
    if (successMsg) {
      const t = setTimeout(() => setSuccessMsg(null), 5000)
      return () => clearTimeout(t)
    }
  }, [successMsg])
  useEffect(() => {
    if (error) {
      const t = setTimeout(() => setError(null), 8000)
      return () => clearTimeout(t)
    }
  }, [error])

  const handleRefresh = () => {
    setRefreshing(true)
    loadData()
  }

  // Telecharge l'agent Sage ETL (.NET) a installer sur le serveur Sage du client
  // Telechargement du zip agent. Avec un agentId, le zip embarque la config
  // (jeton d'enrolement) : rien a saisir chez le client. Sans, zip nu.
  const runDownloadAgent = async (agent = null) => {
    setShowDownloadPicker(false)
    setDownloadingAgent(true)
    try {
      const res = await downloadSageAgent(agent?.agent_id)
      const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/zip' }))
      const a = document.createElement('a')
      a.href = url
      a.download = agent
        ? `SageETLAgent_${agent.dwh_code || agent.name || 'config'}.zip`
        : 'SageETLAgent.zip'
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)
      if (agent) {
        setSuccessMsg(`Agent pret a l'emploi telecharge pour ${agent.name} — le jeton d'enrolement expire dans 24 h`)
      }
    } catch (err) {
      console.error('Erreur telechargement agent Sage:', err)
      setError("Erreur lors du telechargement de l'agent Sage")
    } finally {
      setDownloadingAgent(false)
    }
  }

  const handleDownloadAgent = () => {
    // Sans agent enregistre, rien a pre-configurer : telechargement direct.
    if (!agents.length) return runDownloadAgent()
    setShowDownloadPicker(true)
  }

  const handleAgentClick = (agent) => {
    setSelectedAgent(agent)
    setShowDetailModal(true)
  }

  const handleViewLogs = (agent) => {
    setSelectedAgent(agent)
    setShowLogsModal(true)
  }

  const handleTriggerSync = async (agent) => {
    try {
      await triggerSync(agent.agent_id)
      setSuccessMsg(`Synchronisation declenchee pour ${agent.name}`)
      setTimeout(loadData, 1000)
    } catch (error) {
      console.error('Erreur sync:', error)
      setError('Erreur lors du declenchement de la synchronisation')
    }
  }

  const handlePauseResume = async (agent) => {
    try {
      const isPausing = agent.status === 'active' || agent.status === 'syncing'
      if (isPausing) {
        await pauseAgent(agent.agent_id)
      } else {
        await resumeAgent(agent.agent_id)
      }
      setSuccessMsg(`Agent ${agent.name} ${isPausing ? 'mis en pause' : 'repris'}`)
      setTimeout(loadData, 1000)
    } catch (error) {
      console.error('Erreur pause/resume:', error)
      setError('Erreur lors du changement de statut de l\'agent')
    }
  }

  const handleSyncTables = async (agent) => {
    try {
      const res = await syncPublishedTables(agent.agent_id)
      const { added, updated } = res.data
      setSuccessMsg(`Tables recuperees depuis OptiBoard : ${added} nouvelle(s) ajoutee(s), ${updated} mise(s) a jour`)
      await loadData()
    } catch (error) {
      console.error('Erreur récupération tables OptiBoard:', error)
      setError('Erreur lors de la récupération des tables depuis OptiBoard')
    }
  }

  const handleDeleteAgent = async (agent) => {
    try {
      await deleteAgent(agent.agent_id)
      setSuccessMsg(`Agent ${agent.name} supprime`)
      await loadData()
    } catch (error) {
      console.error('Erreur suppression agent:', error)
      setError('Erreur lors de la suppression de l\'agent')
    }
  }

  const handleAgentCreated = async () => {
    console.log('handleAgentCreated: Fermeture modal et rechargement...')
    setShowCreateModal(false)
    try {
      await loadData()
      console.log('handleAgentCreated: Donnees rechargees')
    } catch (err) {
      console.error('handleAgentCreated: Erreur rechargement:', err)
    }
  }

  const handleAgentUpdated = () => {
    setShowDetailModal(false)
    loadData()
  }

  if (loading) {
    return <Loading message="Chargement des agents ETL..." />
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Server size={28} />
            Administration ETL
          </h1>
          <p className="text-gray-500 dark:text-gray-400">
            Gestion des agents de synchronisation Sage 100
          </p>
        </div>
        <div className="flex gap-2">
          <button
            className="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 flex items-center gap-2 transition-colors"
            onClick={handleRefresh}
            disabled={refreshing}
          >
            <RefreshCw size={16} className={refreshing ? 'animate-spin' : ''} />
            Actualiser
          </button>
          <button
            className="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 flex items-center gap-2 transition-colors disabled:opacity-50"
            onClick={handleDownloadAgent}
            disabled={downloadingAgent}
            title="Télécharger l'agent Sage ETL, pré-configuré pour un agent (aucun identifiant à saisir)"
          >
            <Download size={16} className={downloadingAgent ? 'animate-pulse' : ''} />
            {downloadingAgent ? 'Préparation…' : 'Agent Sage'}
          </button>
          {activeTab === 'agents' && (
            <button
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 flex items-center gap-2 transition-colors"
              onClick={() => setShowCreateModal(true)}
            >
              <Plus size={16} />
              Nouvel Agent
            </button>
          )}
        </div>
      </div>

      {/* Onglets — Tables ETL et Colonnes réservés aux éditeurs KASOFT (non client) */}
      <div className="flex gap-1 mb-6 bg-gray-100 dark:bg-gray-800 p-1 rounded-lg w-fit">
        {(isClientPortal ? ETL_TABS_CLIENT : ETL_TABS_EDITOR).map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 rounded-md text-sm font-medium flex items-center gap-2 transition-colors ${
              activeTab === tab.id
                ? 'bg-white dark:bg-gray-700 text-primary-600 dark:text-primary-400 shadow-sm'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
            }`}
          >
            <tab.icon size={16} />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Toast notifications (fixed bottom-right) */}
      <div className="fixed bottom-4 right-4 z-50 space-y-2 max-w-md">
        {error && (
          <div className="p-4 bg-red-100 dark:bg-red-900/80 text-red-700 dark:text-red-300 rounded-lg shadow-lg flex items-center justify-between animate-slide-in border border-red-200 dark:border-red-700">
            <div className="flex items-center gap-2">
              <XCircle size={16} className="flex-shrink-0" />
              <span className="text-sm">{error}</span>
            </div>
            <button onClick={() => setError(null)} className="text-red-500 hover:text-red-700 ml-3 flex-shrink-0">
              <XCircle size={16} />
            </button>
          </div>
        )}
        {successMsg && (
          <div className="p-4 bg-green-100 dark:bg-green-900/80 text-green-700 dark:text-green-300 rounded-lg shadow-lg flex items-center justify-between animate-slide-in border border-green-200 dark:border-green-700">
            <div className="flex items-center gap-2">
              <CheckCircle size={16} className="flex-shrink-0" />
              <span className="text-sm">{successMsg}</span>
            </div>
            <button onClick={() => setSuccessMsg(null)} className="text-green-500 hover:text-green-700 ml-3 flex-shrink-0">
              <XCircle size={16} />
            </button>
          </div>
        )}
      </div>

      {/* Contenu selon l'onglet actif */}
      {activeTab === 'agents' && (
        <>
          {/* Stats Cards — admin central uniquement */}
          {!isClientPortal && <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
            <div className="bg-primary-500 text-white rounded-lg p-4">
              <div className="flex items-center gap-3">
                <Server size={32} className="opacity-75" />
                <div>
                  <div className="text-2xl font-bold">{globalStats.total}</div>
                  <div className="text-sm opacity-90">Total Agents</div>
                </div>
              </div>
            </div>
            <div className="bg-green-500 text-white rounded-lg p-4">
              <div className="flex items-center gap-3">
                <CheckCircle size={32} className="opacity-75" />
                <div>
                  <div className="text-2xl font-bold">{globalStats.active}</div>
                  <div className="text-sm opacity-90">Actifs</div>
                </div>
              </div>
            </div>
            <div className="bg-primary-400 text-white rounded-lg p-4">
              <div className="flex items-center gap-3">
                <RefreshCw size={32} className="opacity-75" />
                <div>
                  <div className="text-2xl font-bold">{globalStats.syncing}</div>
                  <div className="text-sm opacity-90">En cours</div>
                </div>
              </div>
            </div>
            <div className="bg-red-500 text-white rounded-lg p-4">
              <div className="flex items-center gap-3">
                <XCircle size={32} className="opacity-75" />
                <div>
                  <div className="text-2xl font-bold">{globalStats.error}</div>
                  <div className="text-sm opacity-90">En erreur</div>
                </div>
              </div>
            </div>
            <div className="bg-gray-500 text-white rounded-lg p-4">
              <div className="flex items-center gap-3">
                <Pause size={32} className="opacity-75" />
                <div>
                  <div className="text-2xl font-bold">{globalStats.inactive}</div>
                  <div className="text-sm opacity-90">Inactifs</div>
                </div>
              </div>
            </div>
          </div>}

          {/* Filtres — admin central uniquement */}
          {!isClientPortal && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 mb-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Filtrer par DWH
                </label>
                <select
                  className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
                  value={filterDwh}
                  onChange={(e) => setFilterDwh(e.target.value)}
                >
                  <option value="">Tous les DWH</option>
                  {dwhList.map(dwh => (
                    <option key={dwh.code} value={dwh.code}>
                      {dwh.nom || dwh.code}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Filtrer par Status
                </label>
                <select
                  className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
                  value={filterStatus}
                  onChange={(e) => setFilterStatus(e.target.value)}
                >
                  <option value="">Tous les status</option>
                  <option value="active">Actif</option>
                  <option value="syncing">En synchronisation</option>
                  <option value="error">En erreur</option>
                  <option value="inactive">Inactif</option>
                  <option value="paused">En pause</option>
                </select>
              </div>
              <div className="text-right text-sm text-gray-500 dark:text-gray-400 flex items-center justify-end gap-1">
                <Clock size={14} />
                Actualisation automatique toutes les 30s
              </div>
            </div>
          </div>
          )}

          {/* Liste des agents */}
          <AgentList
            agents={agents}
            onAgentClick={handleAgentClick}
            onViewLogs={handleViewLogs}
            onTriggerSync={handleTriggerSync}
            onPauseResume={handlePauseResume}
            onSyncTables={handleSyncTables}
            onDelete={handleDeleteAgent}
          />
        </>
      )}

      {/* Onglet Monitoring */}
      {activeTab === 'monitoring' && (
        <SyncMonitoringDashboard />
      )}

      {/* Onglet Tables ETL — vue selon le contexte */}
      {activeTab === 'tables' && (
        isClientPortal
          ? <ETLClientTablesConfig
              agents={agents}
              onSyncFromOptiBoard={handleSyncTables}
            />
          : <ETLTablesAdmin />
      )}


      {/* Modals */}
      {showCreateModal && (
        <CreateAgentModal
          dwhList={dwhList}
          isClientPortal={isClientPortal}
          clientDwhCode={currentDWH?.code}
          clientDwhNom={currentDWH?.nom}
          onClose={() => setShowCreateModal(false)}
          onCreated={handleAgentCreated}
        />
      )}

      {showDetailModal && selectedAgent && (
        <AgentDetailModal
          agent={selectedAgent}
          onClose={() => setShowDetailModal(false)}
          onUpdated={handleAgentUpdated}
        />
      )}

      {showLogsModal && selectedAgent && (
        <SyncLogViewer
          agent={selectedAgent}
          onClose={() => setShowLogsModal(false)}
        />
      )}

      {/* Choix de l'agent a pre-configurer dans le zip telecharge */}
      {showDownloadPicker && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
          onClick={() => setShowDownloadPicker(false)}
        >
          <div
            className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-md max-h-[80vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-4 border-b border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                <Download size={18} />
                Telecharger l'agent Sage
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                Choisissez l'agent : le zip embarquera sa configuration et un jeton
                d'enrolement valable 24 h. Chez le client, il suffit de dezipper, lancer,
                puis importer le fichier de config — aucun identifiant a saisir.
              </p>
            </div>

            <div className="p-2 overflow-y-auto">
              {agents.map((agent) => (
                <button
                  key={agent.agent_id}
                  onClick={() => runDownloadAgent(agent)}
                  className="w-full text-left px-3 py-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                >
                  <div className="font-medium text-gray-900 dark:text-white">{agent.name}</div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">
                    {agent.dwh_name || agent.dwh_code}
                    {agent.sage_database ? ` - ${agent.sage_database}` : ''}
                  </div>
                </button>
              ))}
            </div>

            <div className="p-3 border-t border-gray-200 dark:border-gray-700 flex justify-between gap-2">
              <button
                onClick={() => runDownloadAgent()}
                className="px-3 py-2 text-sm text-gray-600 dark:text-gray-300 hover:underline"
                title="Zip nu : identifiants a saisir manuellement dans l'agent"
              >
                Sans configuration
              </button>
              <button
                onClick={() => setShowDownloadPicker(false)}
                className="px-4 py-2 text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600"
              >
                Annuler
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
