/**
 * Gestion des DWH Clients - Architecture Multi-Tenant
 * ====================================================
 * Shell principal : état + handlers uniquement.
 * Le JSX des onglets est délégué aux sous-composants dans components/dwh/.
 */

import { useState, useEffect } from 'react'
import {
  Building2, Plus, RefreshCw, HardDrive, Upload, AlertCircle, X,
  LayoutGrid, PieChart, BarChart3, Database, Menu as MenuIcon
} from 'lucide-react'
import api, { extractErrorMessage } from '../services/api'
import PublishModal from '../components/PublishModal'
import DWHClientsTab from '../components/dwh/DWHClientsTab'
import ClientDBDetailModal from '../components/dwh/ClientDBDetailModal'
import MasterPublishTab from '../components/dwh/MasterPublishTab'
import ETLTablesAdmin from '../components/dwh/ETLTablesAdmin'
import DWHFormModal from '../components/dwh/DWHFormModal'

// Tables synchronisables depuis la base master vers les bases client
const SYNCABLE_TABLES = [
  'APP_Menus', 'APP_GridViews', 'APP_Pivots_V2', 'APP_Dashboards',
  'APP_DataSources', 'APP_EmailConfig', 'APP_Settings',
  'APP_ReportSchedules', 'APP_UserPages', 'APP_UserMenus'
]

// Icones et couleurs par type d'entite master
const ENTITY_TYPE_ICONS = {
  gridviews:   { icon: LayoutGrid, color: 'text-blue-600',   bg: 'bg-blue-100 dark:bg-blue-900/30' },
  pivots:      { icon: PieChart,   color: 'text-purple-600', bg: 'bg-purple-100 dark:bg-purple-900/30' },
  dashboards:  { icon: BarChart3,  color: 'text-green-600',  bg: 'bg-green-100 dark:bg-green-900/30' },
  datasources: { icon: Database,   color: 'text-orange-600', bg: 'bg-orange-100 dark:bg-orange-900/30' },
  menus:       { icon: MenuIcon,   color: 'text-indigo-600', bg: 'bg-indigo-100 dark:bg-indigo-900/30' }
}

export default function DWHManagement() {
  // ── État DWH Clients ──────────────────────────────────────────────────────
  const [dwhList, setDwhList] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedDWH, setSelectedDWH] = useState(null)
  const [showModal, setShowModal] = useState(false)
  const [modalMode, setModalMode] = useState('create') // create | edit | sources | smtp
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [expandedDWH, setExpandedDWH] = useState(null)
  const [connectionStatus, setConnectionStatus] = useState(null)

  // Formulaire DWH
  const [formData, setFormData] = useState({
    code: '', nom: '', raison_sociale: '', adresse: '', ville: '',
    pays: 'Maroc', telephone: '', email: '', logo_url: '',
    serveur_dwh: '', base_dwh: '', user_dwh: '', password_dwh: '',
    serveur_optiboard: '', base_optiboard: '', user_optiboard: '', password_optiboard: '',
    actif: true
  })

  // Formulaire SMTP
  const [smtpData, setSmtpData] = useState({
    smtp_server: '', smtp_port: 587, smtp_username: '', smtp_password: '',
    from_email: '', from_name: '', use_tls: true
  })

  // Sources Sage
  const [sources, setSources] = useState([])
  const [sourceForm, setSourceForm] = useState({
    code_societe: '', nom_societe: '', serveur_sage: '', base_sage: '',
    user_sage: '', password_sage: '', etl_enabled: true,
    etl_mode: 'incremental', etl_schedule: '*/15 * * * *'
  })

  // ── État Bases Client ─────────────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState('dwh')
  const [clientDBs, setClientDBs] = useState([])
  const [clientDBLoading, setClientDBLoading] = useState(false)
  const [clientDBStats, setClientDBStats] = useState({ total: 0, healthy: 0, unhealthy: 0, pending: 0 })
  const [showDetailModal, setShowDetailModal] = useState(false)
  const [detailData, setDetailData] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [syncing, setSyncing] = useState({})
  const [syncingAll, setSyncingAll] = useState(false)
  const [resetting, setResetting] = useState(false)

  // ── État Publication Master ───────────────────────────────────────────────
  const [masterEntities, setMasterEntities] = useState({})
  const [masterLoading, setMasterLoading] = useState(false)
  const [masterStats, setMasterStats] = useState({ total: 0, with_code: 0 })
  const [masterFilter, setMasterFilter] = useState('all')
  const [masterSearch, setMasterSearch] = useState('')
  const [masterSelected, setMasterSelected] = useState([])
  const [publishingAll, setPublishingAll] = useState(false)
  const [showPublishModal, setShowPublishModal] = useState(false)
  const [publishTarget, setPublishTarget] = useState({ type: '', code: '', name: '' })

  // ── Confirmation suppression DWH ─────────────────────────────────────────
  const [deleteConfirm, setDeleteConfirm] = useState(null)  // { dwh, dropDatabases }
  const [deleting, setDeleting] = useState(false)
  const [deleteResult, setDeleteResult] = useState(null)    // résultat drop bases

  useEffect(() => { loadDWHList() }, [])

  // ── Handlers DWH Clients ──────────────────────────────────────────────────
  const loadDWHList = async () => {
    setLoading(true)
    try {
      const res = await api.get('/dwh-admin/list')
      setDwhList(res.data.data || [])
      setError(null)
    } catch (err) {
      setError(extractErrorMessage(err, 'Erreur lors du chargement'))
      setDwhList([])
    } finally {
      setLoading(false)
    }
  }

  const openCreateModal = () => {
    setFormData({
      code: '', nom: '', raison_sociale: '', adresse: '', ville: '',
      pays: 'Maroc', telephone: '', email: '', logo_url: '',
      serveur_dwh: '', base_dwh: '', user_dwh: '', password_dwh: '',
      serveur_optiboard: '', base_optiboard: '', user_optiboard: '', password_optiboard: '',
      actif: true
    })
    setModalMode('create')
    setConnectionStatus(null)
    setShowModal(true)
  }

  const openEditModal = (dwh) => {
    setFormData({
      code: dwh.code, nom: dwh.nom,
      raison_sociale: dwh.raison_sociale || '',
      adresse: dwh.adresse || '', ville: dwh.ville || '',
      pays: dwh.pays || 'Maroc', telephone: dwh.telephone || '',
      email: dwh.email || '', logo_url: dwh.logo_url || '',
      serveur_dwh: dwh.serveur_dwh, base_dwh: dwh.base_dwh,
      user_dwh: dwh.user_dwh, password_dwh: '',
      // OptiBoard : valeur enregistrée ou héritage DWH (vraie valeur dans le state)
      serveur_optiboard: dwh.serveur_optiboard || dwh.serveur_dwh || '',
      base_optiboard:    dwh.base_optiboard    || `OptiBoard_clt${dwh.code}`,
      user_optiboard:    dwh.user_optiboard    || dwh.user_dwh || '',
      password_optiboard: '',
      actif: dwh.actif
    })
    setSelectedDWH(dwh)
    setModalMode('edit')
    setConnectionStatus(null)
    setShowModal(true)
  }

  const openSMTPModal = async (dwh) => {
    setSelectedDWH(dwh)
    try {
      const res = await api.get(`/dwh-admin/${dwh.code}/smtp`)
      setSmtpData(res.data.data || {
        smtp_server: '', smtp_port: 587, smtp_username: '', smtp_password: '',
        from_email: dwh.email || '', from_name: dwh.nom || '', use_tls: true
      })
    } catch {
      setSmtpData({
        smtp_server: '', smtp_port: 587, smtp_username: '', smtp_password: '',
        from_email: dwh.email || '', from_name: dwh.nom || '', use_tls: true
      })
    }
    setModalMode('smtp')
    setShowModal(true)
  }

  const openSourcesModal = async (dwh) => {
    setSelectedDWH(dwh)
    try {
      const res = await api.get(`/dwh-admin/${dwh.code}/sources`)
      setSources(res.data.data || [])
    } catch {
      setSources([])
    }
    setSourceForm({
      code_societe: '', nom_societe: '', serveur_sage: '', base_sage: '',
      user_sage: '', password_sage: '', etl_enabled: true,
      etl_mode: 'incremental', etl_schedule: '*/15 * * * *'
    })
    setModalMode('sources')
    setShowModal(true)
  }

  const handleSaveDWH = async () => {
    setSaving(true)
    try {
      if (modalMode === 'create') {
        const res = await api.post('/dwh-admin', formData)
        const d = res.data
        if (d.db_created) {
          alert(`DWH cree avec succes!\n\nBase '${formData.base_dwh}' initialisee avec ${d.tables_count || 0} tables.`)
        } else {
          alert(d.message || 'DWH cree avec succes!')
        }
      } else {
        await api.put(`/dwh-admin/${formData.code}`, formData)
      }
      setShowModal(false)
      setConnectionStatus(null)
      loadDWHList()
    } catch (err) {
      setError(extractErrorMessage(err, 'Erreur lors de la sauvegarde'))
    } finally {
      setSaving(false)
    }
  }

  const handleSaveSMTP = async () => {
    setSaving(true)
    try {
      await api.post(`/dwh-admin/${selectedDWH.code}/smtp`, smtpData)
      setShowModal(false)
    } catch (err) {
      setError(extractErrorMessage(err, 'Erreur lors de la sauvegarde SMTP'))
    } finally {
      setSaving(false)
    }
  }

  const handleTestConnection = async () => {
    setTesting(true)
    setConnectionStatus(null)
    try {
      const res = await api.post('/dwh-admin/test-connection', {
        serveur: formData.serveur_dwh, base: formData.base_dwh,
        user: formData.user_dwh, password: formData.password_dwh
      })
      if (res.data.success) {
        setConnectionStatus(res.data.db_exists === false
          ? { type: 'warning', message: `Serveur accessible mais la base '${formData.base_dwh}' n'existe pas. Elle sera creee automatiquement.` }
          : { type: 'success', message: res.data.message || 'Connexion reussie!' }
        )
      } else {
        setConnectionStatus({ type: 'error', message: res.data.message || 'Echec de la connexion' })
      }
    } catch (err) {
      setConnectionStatus({ type: 'error', message: extractErrorMessage(err) })
    } finally {
      setTesting(false)
    }
  }

  const handleTestSMTP = async () => {
    setTesting(true)
    try {
      const res = await api.post(`/dwh-admin/${selectedDWH.code}/smtp/test`, smtpData)
      alert(res.data.success ? 'Email de test envoye!' : 'Echec: ' + res.data.error)
    } catch (err) {
      alert('Erreur: ' + extractErrorMessage(err))
    } finally {
      setTesting(false)
    }
  }

  const handleAddSource = async () => {
    setSaving(true)
    try {
      await api.post(`/dwh-admin/${selectedDWH.code}/sources`, sourceForm)
      const res = await api.get(`/dwh-admin/${selectedDWH.code}/sources`)
      setSources(res.data.data || [])
      setSourceForm({
        code_societe: '', nom_societe: '', serveur_sage: '', base_sage: '',
        user_sage: '', password_sage: '', etl_enabled: true,
        etl_mode: 'incremental', etl_schedule: '*/15 * * * *'
      })
    } catch (err) {
      setError(extractErrorMessage(err, "Erreur lors de l'ajout"))
    } finally {
      setSaving(false)
    }
  }

  const handleDeleteSource = async (sourceCode) => {
    if (!confirm('Supprimer cette source Sage?')) return
    try {
      await api.delete(`/dwh-admin/${selectedDWH.code}/sources/${sourceCode}`)
      setSources(sources.filter(s => s.code_societe !== sourceCode))
    } catch (err) {
      setError(extractErrorMessage(err, 'Erreur lors de la suppression'))
    }
  }

  const handleDeleteDWH = (dwh) => {
    if (dwh.is_demo || dwh.code === 'KA') {
      alert('Le client Kasoft-Démo est protégé et ne peut pas être supprimé.')
      return
    }
    // Ouvre le modal de confirmation personnalisé
    setDeleteConfirm({ dwh, dropDatabases: false })
    setDeleteResult(null)
  }

  const confirmDeleteDWH = async () => {
    if (!deleteConfirm) return
    const { dwh, dropDatabases } = deleteConfirm
    setDeleting(true)
    try {
      const params = `force=true&drop_databases=true`
      const res = await api.delete(`/dwh-admin/${dwh.code}?${params}`)
      setDeleteResult(res.data)
      // Fermer le panneau si le DWH supprimé était sélectionné
      if (selectedDWH?.code === dwh.code) {
        setSelectedDWH(null)
        setShowModal(false)
      }
      if (expandedDWH === dwh.code) setExpandedDWH(null)
      // Rafraîchir la liste
      await loadDWHList()
      // Fermer le modal après 2s si tout s'est bien passé
      setTimeout(() => { setDeleteConfirm(null); setDeleteResult(null) }, 2000)
    } catch (err) {
      setError(extractErrorMessage(err, 'Erreur lors de la suppression'))
      setDeleteConfirm(null)
    } finally {
      setDeleting(false)
    }
  }

  const toggleExpand = (code) => setExpandedDWH(expandedDWH === code ? null : code)

  // ── Handlers Bases Client ─────────────────────────────────────────────────
  const loadClientDatabases = async () => {
    setClientDBLoading(true)
    try {
      const res = await api.get('/dwh-admin/client-databases')
      setClientDBs(res.data.data || [])
      setClientDBStats({
        total: res.data.total || 0,
        healthy: res.data.healthy || 0,
        unhealthy: res.data.unhealthy || 0,
        pending: res.data.pending_migration || 0
      })
    } catch (err) {
      setError(extractErrorMessage(err, 'Erreur chargement bases client'))
    } finally {
      setClientDBLoading(false)
    }
  }

  const loadClientDBDetail = async (code) => {
    setDetailLoading(true)
    try {
      const res = await api.get(`/dwh-admin/${code}/client-db-status`)
      setDetailData(res.data)
      setShowDetailModal(true)
    } catch (err) {
      setError(extractErrorMessage(err, 'Erreur chargement detail'))
    } finally {
      setDetailLoading(false)
    }
  }

  const handleSyncClient = async (code, tables = null) => {
    setSyncing(prev => ({ ...prev, [code]: true }))
    try {
      await api.post(`/dwh-admin/${code}/sync-data`, { tables, mode: 'replace' })
      await loadClientDatabases()
      if (showDetailModal && detailData?.dwh_code === code) {
        await loadClientDBDetail(code)
      }
    } catch (err) {
      setError(extractErrorMessage(err, 'Erreur synchronisation'))
    } finally {
      setSyncing(prev => ({ ...prev, [code]: false }))
    }
  }

  const handleSyncAllClients = async () => {
    if (!confirm('Synchroniser les donnees vers toutes les bases client?')) return
    setSyncingAll(true)
    try {
      for (const db of clientDBs.filter(d => d.connection_status === 'ok')) {
        await api.post(`/dwh-admin/${db.dwh_code}/sync-data`, { mode: 'replace' })
      }
      await loadClientDatabases()
    } catch (err) {
      setError(extractErrorMessage(err, 'Erreur synchronisation globale'))
    } finally {
      setSyncingAll(false)
    }
  }

  const handleResetClient = async (code) => {
    if (!confirm(`ATTENTION: Reinitialiser la base OptiBoard_${code}? Les donnees seront recrees depuis MASTER.`)) return
    if (!confirm('Etes-vous VRAIMENT sur? Cette action est irreversible.')) return
    setResetting(true)
    try {
      await api.post(`/dwh-admin/${code}/reset-client-db`, { confirm: true, keep_user_data: true })
      await loadClientDatabases()
      setShowDetailModal(false)
    } catch (err) {
      setError(extractErrorMessage(err, 'Erreur reinitialisation'))
    } finally {
      setResetting(false)
    }
  }

  const handleMigrateAll = async () => {
    if (!confirm('Creer les bases OptiBoard_XXX pour tous les clients sans base?')) return
    try {
      const res = await api.post('/dwh-admin/migrate-all')
      alert(res.data.message || 'Migration terminee')
      await loadClientDatabases()
    } catch (err) {
      setError(extractErrorMessage(err, 'Erreur migration'))
    }
  }

  const handleCreateSingleClientDB = async (code) => {
    try {
      const res = await api.post(`/dwh-admin/${code}/create-client-db`)
      alert(res.data.already_exists
        ? `OptiBoard_${code} existe deja`
        : `Base OptiBoard_${code} creee avec succes!`
      )
      await loadClientDatabases()
    } catch (err) {
      setError(extractErrorMessage(err, 'Erreur creation base client'))
    }
  }

  // ── Handlers Publication Master ───────────────────────────────────────────
  const loadMasterEntities = async () => {
    setMasterLoading(true)
    try {
      const res = await api.get('/master/entities')
      if (res.data.success) {
        setMasterEntities(res.data.data || {})
        setMasterStats({ total: res.data.total || 0, with_code: res.data.with_code || 0 })
      }
    } catch (err) {
      setError(extractErrorMessage(err, 'Erreur chargement entites Master'))
    } finally {
      setMasterLoading(false)
    }
  }

  const openPublishModal = (entityType, code, name) => {
    setPublishTarget({ type: entityType, code, name })
    setShowPublishModal(true)
  }

  const handlePublishAll = async () => {
    if (!confirm('Publier TOUTES les entites Master vers TOUS les clients ?')) return
    setPublishingAll(true)
    try {
      const res = await api.post('/master/publish-all', {})
      const d = res.data
      alert(`Publication terminee!\n${d.total_published} publiee(s), ${d.total_updated} mise(s) a jour, ${d.total_failed} echec(s)`)
      await loadMasterEntities()
    } catch (err) {
      setError(extractErrorMessage(err, 'Erreur publication globale'))
    } finally {
      setPublishingAll(false)
    }
  }

  const handlePublishSelected = async () => {
    if (masterSelected.length === 0) return
    const grouped = {}
    masterSelected.forEach(item => {
      const [type, code] = item.split('::')
      if (!grouped[type]) grouped[type] = []
      grouped[type].push(code)
    })
    try {
      const clientsRes = await api.get('/master/clients')
      const clientCodes = (clientsRes.data.data || []).filter(c => c.connected).map(c => c.code)
      if (clientCodes.length === 0) { setError('Aucun client connecte disponible'); return }
      const entities = Object.entries(grouped).map(([type, codes]) => ({ type, codes }))
      const res = await api.post('/master/publish', { entities, clients: clientCodes, mode: 'upsert' })
      const d = res.data
      alert(`Publication terminee!\n${d.total_published} publiee(s), ${d.total_updated} mise(s) a jour, ${d.total_failed} echec(s)`)
      setMasterSelected([])
      await loadMasterEntities()
    } catch (err) {
      setError(extractErrorMessage(err, 'Erreur publication selection'))
    }
  }

  const handleGenerateCodes = async () => {
    try {
      const res = await api.post('/master/generate-codes')
      alert(`Codes generes: ${res.data.total_updated} entite(s) mises a jour`)
      await loadMasterEntities()
    } catch (err) {
      setError(extractErrorMessage(err, 'Erreur generation codes'))
    }
  }

  const selectAllMasterEntities = () => {
    const all = []
    Object.entries(masterEntities).forEach(([type, data]) => {
      ;(data.items || []).forEach(item => { if (item.code) all.push(`${type}::${item.code}`) })
    })
    setMasterSelected(all)
  }

  const getFilteredMasterEntities = () => {
    const items = []
    const types = masterFilter === 'all' ? Object.keys(masterEntities) : [masterFilter]
    types.forEach(type => {
      const data = masterEntities[type]
      if (!data?.items) return
      data.items.forEach(item => {
        if (masterSearch && !item.nom?.toLowerCase().includes(masterSearch.toLowerCase()) &&
            !item.code?.toLowerCase().includes(masterSearch.toLowerCase())) return
        items.push({ ...item, entity_type: type, entity_label: data.label })
      })
    })
    return items
  }

  // ── Rendu ─────────────────────────────────────────────────────────────────
  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Building2 className="text-primary-600" />
            Gestion des DWH Clients
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            Architecture multi-tenant - Gestion des bases clients et sources Sage
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={loadDWHList}
            className="px-4 py-2 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 rounded-lg flex items-center gap-2"
          >
            <RefreshCw size={18} />
            Actualiser
          </button>
          <button
            onClick={openCreateModal}
            className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg flex items-center gap-2"
          >
            <Plus size={18} />
            Nouveau DWH
          </button>
        </div>
      </div>

      {/* Tab Bar — Central uniquement : pas de données clients */}
      <div className="flex border-b border-gray-200 dark:border-gray-700 mb-6">
        {[
          { id: 'dwh',    icon: Building2,  label: 'Registre Clients',    onClick: () => setActiveTab('dwh') },
          { id: 'master', icon: Upload,     label: 'Publication Templates', onClick: () => { setActiveTab('master'); loadMasterEntities() } },
          { id: 'etl',    icon: Database,   label: 'ETL Tables',           onClick: () => setActiveTab('etl') },
        ].map(tab => {
          const Icon = tab.icon
          return (
            <button
              key={tab.id}
              onClick={tab.onClick}
              className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-primary-600 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
              }`}
            >
              <Icon size={16} className="inline mr-2 -mt-0.5" />
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* Error banner */}
      {error && (
        <div className="mb-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center gap-2 text-red-600 dark:text-red-400">
          <AlertCircle size={20} />
          {error}
          <button onClick={() => setError(null)} className="ml-auto"><X size={18} /></button>
        </div>
      )}

      {/* Onglets */}
      {activeTab === 'dwh' && (
        <DWHClientsTab
          loading={loading}
          dwhList={dwhList}
          expandedDWH={expandedDWH}
          toggleExpand={toggleExpand}
          openCreateModal={openCreateModal}
          openEditModal={openEditModal}
          openSMTPModal={openSMTPModal}
          openSourcesModal={openSourcesModal}
          handleDeleteDWH={handleDeleteDWH}
        />
      )}

      {activeTab === 'master' && (
        <MasterPublishTab
          masterEntities={masterEntities}
          masterLoading={masterLoading}
          masterStats={masterStats}
          masterFilter={masterFilter}
          setMasterFilter={setMasterFilter}
          masterSearch={masterSearch}
          setMasterSearch={setMasterSearch}
          masterSelected={masterSelected}
          setMasterSelected={setMasterSelected}
          publishingAll={publishingAll}
          handlePublishAll={handlePublishAll}
          handlePublishSelected={handlePublishSelected}
          loadMasterEntities={loadMasterEntities}
          handleGenerateCodes={handleGenerateCodes}
          selectAllMasterEntities={selectAllMasterEntities}
          getFilteredMasterEntities={getFilteredMasterEntities}
          openPublishModal={openPublishModal}
          ENTITY_TYPE_ICONS={ENTITY_TYPE_ICONS}
        />
      )}

      {/* Onglet ETL Tables — publication + propositions */}
      {activeTab === 'etl' && (
        <ETLTablesAdmin />
      )}

      {/* Modals */}
      <ClientDBDetailModal
        show={showDetailModal}
        onClose={() => setShowDetailModal(false)}
        detailData={detailData}
        syncing={syncing}
        resetting={resetting}
        handleSyncClient={handleSyncClient}
        handleResetClient={handleResetClient}
        SYNCABLE_TABLES={SYNCABLE_TABLES}
      />

      <DWHFormModal
        show={showModal}
        onClose={() => setShowModal(false)}
        modalMode={modalMode}
        formData={formData}
        setFormData={setFormData}
        smtpData={smtpData}
        setSmtpData={setSmtpData}
        sourceForm={sourceForm}
        setSourceForm={setSourceForm}
        sources={sources}
        saving={saving}
        testing={testing}
        connectionStatus={connectionStatus}
        selectedDWH={selectedDWH}
        handleSaveDWH={handleSaveDWH}
        handleSaveSMTP={handleSaveSMTP}
        handleTestConnection={handleTestConnection}
        handleTestSMTP={handleTestSMTP}
        handleAddSource={handleAddSource}
        handleDeleteSource={handleDeleteSource}
      />

      <PublishModal
        isOpen={showPublishModal}
        onClose={() => setShowPublishModal(false)}
        entityType={publishTarget.type}
        entityCode={publishTarget.code}
        entityName={publishTarget.name}
      />

      {/* ── Modal confirmation suppression DWH ──────────────────────────── */}
      {deleteConfirm && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-md">
            {/* Header */}
            <div className="p-5 border-b border-red-100 dark:border-red-900/30 flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-red-100 dark:bg-red-900/40 flex items-center justify-center shrink-0">
                <AlertCircle size={20} className="text-red-600 dark:text-red-400" />
              </div>
              <div>
                <h3 className="font-semibold text-gray-900 dark:text-white">
                  Supprimer le DWH "{deleteConfirm.dwh.nom}"&nbsp;?
                </h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Code : <span className="font-mono font-bold">{deleteConfirm.dwh.code}</span>
                </p>
              </div>
            </div>

            {/* Body */}
            <div className="p-5 space-y-4">
              {!deleteResult ? (
                <>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Tous les enregistrements liés seront supprimés (sources, ETL, historique…).
                    <strong className="text-red-600"> Cette action est irréversible.</strong>
                  </p>

                  {/* Avertissement DROP automatique des bases */}
                  <div className="flex items-start gap-3 p-3 bg-red-50 dark:bg-red-900/20
                                  border border-red-200 dark:border-red-800 rounded-xl text-sm text-red-700 dark:text-red-300">
                    <span className="mt-0.5">⚠️</span>
                    <div>
                      <p className="font-medium">Les bases SQL Server seront supprimées :</p>
                      <p className="font-mono mt-1">DWH_{deleteConfirm.dwh.code} &nbsp;&amp;&amp;&nbsp; OptiBoard_clt{deleteConfirm.dwh.code}</p>
                    </div>
                  </div>
                </>
              ) : (
                /* Résultat après suppression */
                <div className="space-y-2">
                  <p className="text-sm font-medium text-green-700 dark:text-green-400 flex items-center gap-2">
                    <span className="inline-block w-5 h-5 rounded-full bg-green-100 text-green-600 text-center leading-5">✓</span>
                    DWH supprimé avec succès
                  </p>
                  {(deleteResult.drop_results || []).map((r, i) => (
                    <div key={i} className={`text-xs px-3 py-2 rounded-lg font-mono ${
                      r.dropped
                        ? 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-300'
                        : 'bg-gray-50 text-gray-500 dark:bg-gray-700 dark:text-gray-400'
                    }`}>
                      {r.dropped ? '✅' : '⚠️'} &nbsp;{r.db}
                      {!r.dropped && r.reason && ` — ${r.reason}`}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="p-5 border-t border-gray-100 dark:border-gray-700 flex justify-end gap-3">
              {!deleteResult ? (
                <>
                  <button
                    onClick={() => setDeleteConfirm(null)}
                    disabled={deleting}
                    className="px-4 py-2 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700
                               dark:hover:bg-gray-600 rounded-lg text-sm"
                  >
                    Annuler
                  </button>
                  <button
                    onClick={confirmDeleteDWH}
                    disabled={deleting}
                    className="px-4 py-2 bg-red-600 hover:bg-red-700 disabled:bg-red-300
                               text-white rounded-lg text-sm flex items-center gap-2"
                  >
                    {deleting
                      ? <><span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                          Suppression…</>
                      : '🗑 Supprimer définitivement'}
                  </button>
                </>
              ) : (
                <button
                  onClick={() => { setDeleteConfirm(null); setDeleteResult(null) }}
                  className="px-4 py-2 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 rounded-lg text-sm"
                >
                  Fermer
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
