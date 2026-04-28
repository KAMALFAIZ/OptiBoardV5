/**
 * API Service pour la gestion des agents ETL
 * Routes backend: /api/admin/etl/agents
 */
import axios from 'axios'

const API_BASE = '/api'

// Instance axios configuree
const api = axios.create({
  baseURL: API_BASE,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Intercepteur : ajouter X-DWH-Code + Authorization
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token') || sessionStorage.getItem('token')
  if (token && !config.headers['Authorization']) {
    config.headers['Authorization'] = `Bearer ${token}`
  }
  if (!config.headers['X-DWH-Code']) {
    try {
      const savedDWH = localStorage.getItem('currentDWH') || sessionStorage.getItem('currentDWH')
      if (savedDWH) {
        const parsed = JSON.parse(savedDWH)
        if (parsed?.code) config.headers['X-DWH-Code'] = parsed.code
      }
    } catch (e) { /* ignore */ }
  }
  return config
})

// ============================================================
// Gestion des Agents
// ============================================================

/**
 * Liste tous les agents ETL
 * @param {Object} params - Filtres optionnels (dwh_code, status)
 * @param {boolean} centralMode - Si true (superadmin), envoie X-DWH-Code: CENTRAL
 *   pour lire APP_ETL_Agents_Monitoring au lieu d'une base client
 */
export const getAgents = (params = {}, centralMode = false) => {
  const config = { params }
  if (centralMode) {
    // Forcer X-DWH-Code = 'CENTRAL' pour court-circuiter l'intercepteur
    config.headers = { 'X-DWH-Code': 'CENTRAL' }
  }
  return api.get('/admin/etl/agents', config)
}

/**
 * Recupere les details d'un agent
 * @param {string} agentId - ID de l'agent
 */
export const getAgent = (agentId) => {
  return api.get(`/admin/etl/agents/${agentId}`)
}

/**
 * Cree un nouvel agent
 * @param {Object} data - Donnees de l'agent
 */
export const createAgent = (data) => {
  const config = data.dwh_code ? { headers: { 'X-DWH-Code': data.dwh_code } } : {}
  return api.post('/admin/etl/agents', data, config)
}

/**
 * Met a jour un agent
 * @param {string} agentId - ID de l'agent
 * @param {Object} data - Donnees a mettre a jour
 */
export const updateAgent = (agentId, data) => {
  return api.put(`/admin/etl/agents/${agentId}`, data)
}

/**
 * Supprime un agent
 * @param {string} agentId - ID de l'agent
 */
export const deleteAgent = (agentId) => {
  return api.delete(`/admin/etl/agents/${agentId}`)
}

/**
 * Active/Desactive un agent
 * @param {string} agentId - ID de l'agent
 */
export const toggleAgent = (agentId) => {
  return api.post(`/admin/etl/agents/${agentId}/toggle`)
}

/**
 * Regenere la cle API d'un agent
 * @param {string} agentId - ID de l'agent
 */
export const regenerateApiKey = (agentId) => {
  return api.post(`/admin/etl/agents/${agentId}/regenerate-key`)
}

// ============================================================
// Commandes Agent
// ============================================================

/**
 * Declenche une synchronisation
 * @param {string} agentId - ID de l'agent
 */
export const triggerSync = (agentId) => {
  return api.post(`/admin/etl/agents/${agentId}/commands`, {
    command_type: 'sync_now',
    priority: 1
  })
}

/**
 * Synchronise une table specifique
 * @param {string} agentId - ID de l'agent
 * @param {string} tableName - Nom de la table
 */
export const triggerTableSync = (agentId, tableName) => {
  return api.post(`/admin/etl/agents/${agentId}/commands`, {
    command_type: 'sync_table',
    command_data: { table_name: tableName },
    priority: 1
  })
}

/**
 * Met un agent en pause
 * @param {string} agentId - ID de l'agent
 */
export const pauseAgent = (agentId) => {
  return api.post(`/admin/etl/agents/${agentId}/commands`, {
    command_type: 'pause',
    priority: 1
  })
}

/**
 * Reprend un agent en pause
 * @param {string} agentId - ID de l'agent
 */
export const resumeAgent = (agentId) => {
  return api.post(`/admin/etl/agents/${agentId}/commands`, {
    command_type: 'resume',
    priority: 1
  })
}

/**
 * Liste les commandes d'un agent
 * @param {string} agentId - ID de l'agent
 * @param {Object} params - Filtres optionnels
 */
export const getAgentCommands = (agentId, params = {}) => {
  return api.get(`/admin/etl/agents/${agentId}/commands`, { params })
}

// ============================================================
// Configuration Tables
// ============================================================

/**
 * Liste les tables configurees pour un agent
 * @param {string} agentId - ID de l'agent
 */
export const getAgentTables = (agentId) => {
  return api.get(`/admin/etl/agents/${agentId}/tables`)
}

/**
 * Ajoute une table a un agent
 * @param {string} agentId - ID de l'agent
 * @param {Object} tableConfig - Configuration de la table
 */
export const addAgentTable = (agentId, tableConfig) => {
  return api.post(`/admin/etl/agents/${agentId}/tables`, tableConfig)
}

/**
 * Met a jour une table
 * @param {string} agentId - ID de l'agent
 * @param {string} tableId - ID de la table
 * @param {Object} data - Donnees a mettre a jour
 */
export const updateAgentTable = (agentId, tableId, data) => {
  return api.put(`/admin/etl/agents/${agentId}/tables/${tableId}`, data)
}

/**
 * Supprime une table
 * @param {string} agentId - ID de l'agent
 * @param {string} tableId - ID de la table
 */
export const deleteAgentTable = (agentId, tableId) => {
  return api.delete(`/admin/etl/agents/${agentId}/tables/${tableId}`)
}

/**
 * Active/Desactive une table
 * @param {string} agentId - ID de l'agent
 * @param {string} tableId - ID de la table
 */
export const toggleAgentTable = (agentId, tableId) => {
  return api.post(`/admin/etl/agents/${agentId}/tables/${tableId}/toggle`)
}

/**
 * Importe les tables ETL disponibles
 * @param {string} agentId - ID de l'agent
 */
export const importTablesFromYaml = (agentId) => {
  return api.post(`/admin/etl/agents/${agentId}/import-tables`)
}

// ============================================================
// Logs et Monitoring
// ============================================================

/**
 * Liste les logs de synchronisation d'un agent
 * @param {string} agentId - ID de l'agent
 * @param {Object} params - Filtres optionnels
 */
export const getAgentLogs = (agentId, params = {}) => {
  return api.get(`/admin/etl/agents/${agentId}/logs`, { params })
}

/**
 * Liste les heartbeats d'un agent
 * @param {string} agentId - ID de l'agent
 * @param {number} limit - Nombre max de resultats
 */
export const getAgentHeartbeats = (agentId, limit = 50) => {
  return api.get(`/admin/etl/agents/${agentId}/heartbeats`, { params: { limit } })
}

/**
 * Recupere les statistiques d'un agent
 * @param {string} agentId - ID de l'agent
 */
export const getAgentStats = (agentId) => {
  return api.get(`/admin/etl/agents/${agentId}/stats`)
}

/**
 * Recupere les statistiques globales ETL
 */
export const getETLStats = () => {
  return api.get('/admin/etl/stats')
}

/**
 * Dashboard de monitoring sync - taille DB, lignes, inserts, updates par DWH
 */
export const getSyncDashboard = () => {
  return api.get('/admin/etl/sync-dashboard')
}

// ============================================================
// DWH
// ============================================================

/**
 * Liste les DWH disponibles
 */
export const getDWHList = () => {
  return api.get('/admin/dwh')
}

/**
 * Telecharge le package agent
 */
export const downloadAgentPackage = () => {
  return api.get('/admin/etl/agents/download/package', { responseType: 'blob' })
}

/**
 * Recupere le fichier de configuration d'un agent
 * @param {string} agentId - ID de l'agent
 */
export const getAgentConfigFile = (agentId) => {
  return api.get(`/admin/etl/agents/${agentId}/config-file`)
}

/**
 * Liste les tables ETL disponibles (configuration globale partagee)
 */
export const getAvailableETLTables = () => {
  return api.get('/admin/etl/tables/available')
}

/**
 * Recupere le statut de sync des tables pour un agent
 * @param {string} agentId - ID de l'agent
 */
export const getAgentSyncStatus = (agentId) => {
  return api.get(`/admin/etl/agents/${agentId}/sync-status`)
}

// ============================================================
// Configuration Tables ETL Globales
// ============================================================

/**
 * Liste toutes les tables ETL configurees
 */
export const getETLTables = () => {
  return api.get('/etl/config/tables')
}

/**
 * Cree une nouvelle table ETL
 * @param {Object} tableConfig - Configuration de la table
 */
export const createETLTable = (tableConfig) => {
  return api.post('/etl/config/tables', tableConfig)
}

/**
 * Met a jour une table ETL
 * @param {string} tableName - Nom de la table
 * @param {Object} data - Donnees a mettre a jour
 */
export const updateETLTable = (tableName, data) => {
  return api.put(`/etl/config/tables/${tableName}`, data)
}

/**
 * Supprime une table ETL
 * @param {string} tableName - Nom de la table
 */
export const deleteETLTable = (tableName) => {
  return api.delete(`/etl/config/tables/${tableName}`)
}

/**
 * Active/Desactive une table ETL
 * @param {string} tableName - Nom de la table
 */
export const toggleETLTable = (code, is_enabled) => {
  return api.patch(`/etl-tables/client/${code}/toggle`, { is_enabled })
}

/**
 * Recupere la configuration globale ETL
 */
export const getETLGlobalConfig = () => {
  return api.get('/etl/config/global')
}

/**
 * Migre les tables ETL du fichier YAML vers SQL
 */
export const migrateETLFromYaml = () => {
  return api.post('/etl/config/migrate')
}

/**
 * Supprime toutes les tables ETL
 */
export const deleteAllETLTables = () => {
  return api.delete('/etl/config/tables')
}

/**
 * Importe les tables ETL depuis OptiBoard (SyncQuery)
 */
export const importETLFromOptiBoard = () => {
  return api.post('/etl/config/import-from-optiboard')
}

/**
 * Supprime toutes les tables d'un agent
 * @param {string} agentId - ID de l'agent
 */
export const deleteAllAgentTables = (agentId) => {
  return api.delete(`/admin/etl/agents/${agentId}/tables`)
}

/**
 * Synchronise les tables d'un agent avec la config globale ETL
 * @param {string} agentId - ID de l'agent
 */
export const syncAgentTablesWithConfig = (agentId) => {
  return api.post(`/admin/etl/agents/${agentId}/sync-tables`)
}

/**
 * Re-synchronise le catalogue ETL central vers APP_ETL_Tables_Published du client
 * Ajoute les nouvelles tables sans écraser les choix existants (is_enabled)
 * @param {string} agentId - ID de l'agent
 */
export const syncPublishedTables = (agentId) => {
  return api.post(`/admin/etl/agents/${agentId}/sync-published-tables`)
}

/**
 * Récupère le statut d'héritage des tables d'un agent
 * (inherited | customized | custom | not_deployed)
 */
export const getAgentTablesStatus = (agentId) => {
  return api.get(`/admin/etl/agents/${agentId}/tables-status`)
}

/**
 * Marque une table héritée comme personnalisée (protégée des syncs futurs)
 */
export const markAgentTableCustomized = (agentId, tableId) => {
  return api.post(`/admin/etl/agents/${agentId}/tables/${tableId}/mark-customized`)
}

/**
 * Réinitialise une table personnalisée vers les valeurs du maître
 */
export const resetAgentTableToMaster = (agentId, tableId) => {
  return api.post(`/admin/etl/agents/${agentId}/tables/${tableId}/reset-to-master`)
}

/**
 * Déploie une table du catalogue maître vers un agent spécifique
 */
export const deployMasterTableToAgent = (agentId, tableName) => {
  return api.post(`/admin/etl/agents/${agentId}/deploy-master-table`, { table_name: tableName })
}

/**
 * Test de performance BULK INSERT
 * Compare differentes methodes d'insertion pour optimiser les performances
 * @param {Object} params - Parametres du test
 * @param {string} params.table_name - Nom de la table a tester
 * @param {number} params.row_limit - Nombre max de lignes (defaut: 10000)
 * @param {string} params.agent_id - ID de l'agent (optionnel)
 */
export const testBulkInsert = (params) => {
  return api.post('/etl/test/bulk-insert', params, { timeout: 120000 })
}

// ============================================================
// Tables ETL publiees par le central (lecture cote client)
// ============================================================

/**
 * Liste les tables ETL publiees par KASOFT (APP_ETL_Tables_Published)
 */
export const getPublishedETLTables = () => api.get('/etl-tables/client')

// ============================================================
// Tables ETL personnalisees du client (APP_ETL_Tables_Config client)
// ============================================================

/**
 * Liste les tables ETL propres au client
 */
export const getClientCustomETLTables = () => api.get('/etl-tables/client/custom')

/**
 * Cree une table ETL personnalisee
 * @param {Object} data - Configuration de la table
 */
export const createClientCustomETLTable = (data) => api.post('/etl-tables/client/custom', data)

/**
 * Met a jour une table ETL personnalisee
 * @param {string} code - Code de la table
 * @param {Object} data - Donnees a mettre a jour
 */
export const updateClientCustomETLTable = (code, data) => api.put(`/etl-tables/client/custom/${code}`, data)

/**
 * Supprime une table ETL personnalisee
 * @param {string} code - Code de la table
 */
export const deleteClientCustomETLTable = (code) => api.delete(`/etl-tables/client/custom/${code}`)

/**
 * Publie les tables ETL personnalisees vers l'agent ETL du client
 */
export const publishClientCustomETLTables = () => api.post('/etl-tables/client/custom/publish')

// ============================================================
// Export par defaut
// ============================================================

export default {
  // Agents
  getAgents,
  getAgent,
  createAgent,
  updateAgent,
  deleteAgent,
  toggleAgent,
  regenerateApiKey,

  // Commandes
  triggerSync,
  triggerTableSync,
  pauseAgent,
  resumeAgent,
  getAgentCommands,

  // Tables
  getAgentTables,
  addAgentTable,
  updateAgentTable,
  deleteAgentTable,
  toggleAgentTable,
  importTablesFromYaml,

  // Monitoring
  getAgentLogs,
  getAgentHeartbeats,
  getAgentStats,
  getETLStats,
  getSyncDashboard,

  // DWH
  getDWHList,

  // Package
  downloadAgentPackage,
  getAgentConfigFile,
  getAvailableETLTables,
  getAgentSyncStatus,

  // Tables publiees KASOFT (client)
  getPublishedETLTables,

  // Tables personnalisees client
  getClientCustomETLTables,
  createClientCustomETLTable,
  updateClientCustomETLTable,
  deleteClientCustomETLTable,
  publishClientCustomETLTables,
}
