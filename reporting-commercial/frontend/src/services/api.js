import axios from 'axios'

const API_BASE_URL = '/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // 60 secondes timeout pour les requêtes lentes
  headers: {
    'Content-Type': 'application/json'
  }
})

// Intercepteur global : ajouter X-DWH-Code + Authorization a chaque requete
api.interceptors.request.use((config) => {
  // Token d'authentification
  const token = localStorage.getItem('token') || sessionStorage.getItem('token')
  if (token && !config.headers['Authorization']) {
    config.headers['Authorization'] = `Bearer ${token}`
  }
  // DWH Code
  if (!config.headers['X-DWH-Code']) {
    try {
      const savedDWH = localStorage.getItem('currentDWH') || sessionStorage.getItem('currentDWH')
      if (savedDWH) {
        const parsedDWH = JSON.parse(savedDWH)
        if (parsedDWH?.code) {
          config.headers['X-DWH-Code'] = parsedDWH.code
        }
      }
    } catch (e) { /* ignore */ }
  }
  // Data Source — bascule DWH / Sage Direct
  if (!config.headers['X-Data-Source']) {
    try {
      const ds = localStorage.getItem('dataSource')
      if (ds === 'sage') {
        config.headers['X-Data-Source'] = 'sage'
      }
    } catch (e) { /* ignore */ }
  }
  // User ID — pour la vérification des permissions côté backend
  if (!config.headers['X-User-Id']) {
    try {
      const savedUser = localStorage.getItem('user') || sessionStorage.getItem('user')
      if (savedUser) {
        const parsedUser = JSON.parse(savedUser)
        if (parsedUser?.id) {
          config.headers['X-User-Id'] = String(parsedUser.id)
        }
      }
    } catch (e) { /* ignore */ }
  }
  return config
})

// Intercepteur de réponse : déconnexion auto si token expiré (401)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Vider la session et notifier l'app
      localStorage.removeItem('user')
      localStorage.removeItem('token')
      sessionStorage.removeItem('user')
      sessionStorage.removeItem('token')
      window.dispatchEvent(new CustomEvent('auth:session-expired'))
    }
    return Promise.reject(error)
  }
)

// Dashboard APIs
export const getDashboard = (params = {}) => api.get('/dashboard', { params })
export const getEvolutionMensuelle = (params = {}) => api.get('/dashboard/evolution-mensuelle', { params })
export const getComparatifAnnuel = (annee) => api.get('/dashboard/comparatif-annuel', { params: { annee } })

// Ventes APIs
export const getVentes = (params = {}) => api.get('/ventes', { params })
export const getVentesParGamme = (params = {}) => api.get('/ventes/par-gamme', { params })
export const getVentesParCommercial = (params = {}) => api.get('/ventes/par-commercial', { params })
export const getTopClients = (params = {}) => api.get('/ventes/top-clients', { params })
export const getTopProduits = (params = {}) => api.get('/ventes/top-produits', { params })

// Ventes Detail APIs (Drill-Down)
export const getDetailGamme = (gamme, params = {}) => api.get(`/ventes/detail/gamme/${encodeURIComponent(gamme)}`, { params })
export const getDetailClient = (codeClient, params = {}) => api.get(`/ventes/detail/client/${encodeURIComponent(codeClient)}`, { params })
export const getDetailProduit = (codeArticle, params = {}) => api.get(`/ventes/detail/produit/${encodeURIComponent(codeArticle)}`, { params })
export const getDetailCommercial = (commercial, params = {}) => api.get(`/ventes/detail/commercial/${encodeURIComponent(commercial)}`, { params })
export const getDetailMois = (annee, mois, params = {}) => api.get(`/ventes/detail/mois/${annee}/${mois}`, { params })

// Stocks APIs
export const getStocks = (params = {}) => api.get('/stocks', { params })
export const getStockDormant = (params = {}) => api.get('/stocks/dormant', { params })
export const getRotationStock = (params = {}) => api.get('/stocks/rotation', { params })
export const getMouvementsArticle = (codeArticle, params = {}) => api.get(`/stocks/article/${encodeURIComponent(codeArticle)}`, { params })
export const getStocksParGamme = () => api.get('/stocks/par-gamme')

// Fiche Client APIs
export const getFicheClientListe = () => api.get('/fiche-client/liste')
export const getFicheClient = (codeClient, params = {}) => api.get(`/fiche-client/${encodeURIComponent(codeClient)}`, { params })
export const getFicheClientHealthScore = (codeClient, params = {}) => api.get(`/fiche-client/${encodeURIComponent(codeClient)}/health-score`, { params })

// Fiche Fournisseur APIs
export const getFicheFournisseurListe = () => api.get('/fiche-fournisseur/liste')
export const getFicheFournisseur = (nomFournisseur, params = {}) => api.get(`/fiche-fournisseur/${encodeURIComponent(nomFournisseur)}`, { params })

// Recouvrement APIs
export const getRecouvrement = (params = {}) => api.get('/recouvrement', { params })
export const getDSO = (params = {}) => api.get('/recouvrement/dso', { params })
export const getBalanceAgee = (params = {}) => api.get('/recouvrement/balance-agee', { params })
export const getClientEncours = (clientId) => api.get(`/recouvrement/client/${encodeURIComponent(clientId)}`)
export const getCommercialEncours = (commercialId) => api.get(`/recouvrement/commercial/${encodeURIComponent(commercialId)}`)
export const getClientsParTranche = (tranche, params = {}) => api.get(`/recouvrement/tranche/${encodeURIComponent(tranche)}`, { params })

// Admin SQL APIs
export const getQueries = (params = {}) => api.get('/admin/queries', { params })
export const getQueryDetail = (queryId) => api.get(`/admin/queries/${queryId}`)
export const executeQuery = (query, limit = 100) => api.post('/admin/queries/execute', null, { params: { query, limit } })
export const getQueryHistory = (params = {}) => api.get('/admin/queries/history', { params })
export const getQueryStats = () => api.get('/admin/queries/stats')
export const previewQuery = (queryId, params = {}) => api.post(`/admin/queries/preview/${queryId}`, null, { params })

// Export APIs
export const exportVentesExcel = (params = {}) => {
  return api.get('/export/excel/ventes', { params, responseType: 'blob' })
}
export const exportStocksExcel = () => {
  return api.get('/export/excel/stocks', { responseType: 'blob' })
}
export const exportRecouvrementExcel = () => {
  return api.get('/export/excel/recouvrement', { responseType: 'blob' })
}
export const exportRapportComplet = (params = {}) => {
  return api.get('/export/excel/complet', { params, responseType: 'blob' })
}
export const exportDashboardPDF = (params = {}) => {
  return api.get('/export/pdf/dashboard', { params, responseType: 'blob' })
}
export const exportDashboardPptx = (params = {}) => {
  return api.get('/export/pptx/dashboard', { params, responseType: 'blob' })
}

// AI Presentation Builder
export const aiGenerateDocument = (templateId, formData, docType) =>
  api.post('/ai/presentation/generate', { template_id: templateId, form_data: formData, doc_type: docType },
    { responseType: 'blob', timeout: 90000 })

// AI Deck Builder
export const aiDeckPlan = (userRequest) =>
  api.post('/ai/deck/plan', { user_request: userRequest }, { timeout: 90000 })
export const aiDeckCreate = (title, userRequest, slides) =>
  api.post('/ai/deck', { title, user_request: userRequest, slides })
export const aiDeckList = () => api.get('/ai/deck')
export const aiDeckGet = (id) => api.get(`/ai/deck/${id}`)
export const aiDeckUpdate = (id, data) => api.put(`/ai/deck/${id}`, data)
export const aiDeckDelete = (id) => api.delete(`/ai/deck/${id}`)
export const aiDeckGenerateSlide = (deckId, slideIdx) =>
  api.post(`/ai/deck/${deckId}/slide/${slideIdx}/generate`, {}, { timeout: 120000 })
export const aiDeckSlideChat = (deckId, slideIdx, message, chatHistory) =>
  api.post(`/ai/deck/${deckId}/slide/${slideIdx}/chat`, { message, chat_history: chatHistory }, { timeout: 60000 })
export const exportCSV = (table, params = {}) => {
  return api.get(`/export/csv/${table}`, { params, responseType: 'blob' })
}

// Health check
export const healthCheck = () => api.get('/health')

// Societes API
export const getSocietes = () => api.get('/societes')

// Admin Users & Societes (DWH Clients) APIs
export const getAdminSocietes = () => api.get('/admin/societes')
export const getSocieteByCode = (code) => api.get(`/admin/societes/${code}`)
export const createSociete = (data) => api.post('/admin/societes', data)
export const updateSociete = (code, data) => api.put(`/admin/societes/${code}`, data)
export const deleteSociete = (code) => api.delete(`/admin/societes/${code}`)
export const testSocieteConnection = (code) => api.post(`/admin/societes/${code}/test`)
export const getSocieteTables = (code) => api.get(`/admin/societes/${code}/tables`)
export const executeSocieteQuery = (code, query, params = []) => api.post(`/admin/societes/${code}/query`, { query, params })
export const getSocietesSchema = () => api.get('/admin/societes/schema')
export const migrateSocietesTable = () => api.post('/admin/societes/migrate')

export const getUsers = () => api.get('/admin/users')
export const createUser = (data) => api.post('/admin/users', data)
export const updateUser = (id, data) => api.put(`/admin/users/${id}`, data)
export const deleteUser = (id) => api.delete(`/admin/users/${id}`)
export const resetUserPassword = (id) => api.post(`/admin/users/${id}/reset-password`)

export const getAvailablePages = () => api.get('/admin/pages')
export const login = (credentials) => api.post('/admin/login', credentials)
export const getClientInfo = (code) => api.get('/auth/client-info', { params: { code } })
export const getDwhList = (userId) =>
  api.get('/auth/dwh-list', { headers: { 'X-User-Id': String(userId) } })

// Client User Management APIs (admin_client — OptiBoard_XXX.APP_Users)
export const getClientUsers = () => api.get('/auth/client-users')
export const createClientUser = (data) => api.post('/auth/client-users', data)
export const updateClientUser = (id, data) => api.put(`/auth/client-users/${id}`, data)
export const deleteClientUser = (id) => api.delete(`/auth/client-users/${id}`)
export const resetClientUserPassword = (id) => api.post(`/auth/client-users/${id}/reset-password`)

// Client Portal : DWH & Licence (admin_client — gestion de leur propre DWH)
export const getClientDwhInfo = () => api.get('/client/dwh-info')
export const getClientDwhSources = () => api.get('/client/dwh-sources')
export const createClientDwhSource = (data) => api.post('/client/dwh-sources', data)
export const updateClientDwhSource = (code, data) => api.put(`/client/dwh-sources/${code}`, data)
export const deleteClientDwhSource = (code) => api.delete(`/client/dwh-sources/${code}`)
export const getClientSmtp = () => api.get('/client/smtp')
export const saveClientSmtp = (data) => api.post('/client/smtp', data)
export const testClientSmtp = (email) => api.post('/client/smtp/test', { test_email: email })
export const getClientLicense = () => api.get('/client/license')

// Dashboard Builder APIs
export const getBuilderDashboards = (userId) => api.get('/builder/dashboards', { params: { user_id: userId } })
export const getBuilderDashboard = (id) => api.get(`/builder/dashboards/${id}`)
export const createBuilderDashboard = (data) => api.post('/builder/dashboards', data)
export const updateBuilderDashboard = (id, data) => api.put(`/builder/dashboards/${id}`, data)
export const deleteBuilderDashboard = (id) => api.delete(`/builder/dashboards/${id}`)
export const getWidgetTemplates = () => api.get('/builder/templates')

// Helper: recuperer le DWH code depuis localStorage ou fallback API
let _cachedDefaultDWH = null
const getDwhCode = () => {
  try {
    const savedDWH = localStorage.getItem('currentDWH')
    if (savedDWH) {
      const parsedDWH = JSON.parse(savedDWH)
      if (parsedDWH?.code) return parsedDWH.code
    }
  } catch (e) { /* ignore */ }
  return _cachedDefaultDWH
}
// Charger le DWH par defaut au demarrage si rien dans localStorage
;(async () => {
  try {
    if (!localStorage.getItem('currentDWH')) {
      const userStr = localStorage.getItem('user')
      const userId = userStr ? JSON.parse(userStr)?.id : null
      if (userId) {
        const res = await api.get('/auth/dwh-list', { headers: { 'X-User-Id': userId } })
        const list = res.data || []
        if (list.length > 0) {
          _cachedDefaultDWH = list[0].code
        }
      }
    }
  } catch (e) { /* ignore */ }
})()

// DataSources APIs (Legacy - sources locales uniquement)
export const getDataSources = () => api.get('/builder/datasources')
export const getDataSource = (id) => api.get(`/builder/datasources/${id}`)
export const updateDataSource = (id, data) => api.put(`/builder/datasources/${id}`, data)
export const deleteDataSource = (id) => api.delete(`/builder/datasources/${id}`)
export const extractDataSourceParams = (id) => api.post(`/builder/datasources/${id}/extract-params`)
export const previewDataSource = (id, context = {}, limit = null) => {
  const headers = {}
  const dwh = getDwhCode()
  if (dwh) headers['X-DWH-Code'] = dwh
  // Si limit est specifie, l'ajouter au context via __limit (0 = pas de limite)
  const ctx = limit !== null ? { ...context, __limit: limit } : context
  return api.post(`/builder/datasources/${id}/preview`, ctx, { headers })
}
export const executeBuilderQuery = (query, params) => api.post('/builder/execute-query', null, { params: { query, ...params } })

// DataSources Templates APIs (Nouveau - unifié templates + sources)
export const getDataSourceTemplates = (params = {}) => api.get('/datasources/templates', { params })
export const getDataSourceTemplate = (id) => api.get(`/datasources/templates/${id}`)
export const getDataSourceTemplateByCode = (code) => api.get(`/datasources/templates/code/${code}`)
export const createDataSourceTemplate = (data) => api.post('/datasources/templates', data)
export const updateDataSourceTemplate = (id, data) => api.put(`/datasources/templates/${id}`, data)
export const deleteDataSourceTemplate = (id) => api.delete(`/datasources/templates/id/${id}`)
export const testDataSourceQuery = (data) => api.post('/datasources/execute/test', data)

// DataSources Unifiées (Templates + Sources locales) - Pour les Builders
export const getUnifiedDataSources = (params = {}) => api.get('/datasources/unified', { params })
export const getUnifiedDataSource = (identifier) => api.get(`/datasources/unified/${identifier}`)
export const previewUnifiedDataSource = (identifier, context = {}, dwhCode = null, limit = null) => {
  const headers = {}
  const dwh = dwhCode || getDwhCode()
  if (dwh) headers['X-DWH-Code'] = dwh
  // limit=0 => pas de limite (viewer mode), limit=100 defaut (builder)
  const body = { context }
  if (limit !== null) body.limit = limit
  return api.post(`/datasources/unified/${identifier}/preview`, body, { headers, timeout: 120000 })
}
export const getDwhFilterOptions = (field, dwhCode = null) => {
  const headers = {}
  const dwh = dwhCode || getDwhCode()
  if (dwh) headers['X-DWH-Code'] = dwh
  return api.get('/datasources/dwh-filter-options', { params: { field }, headers })
}

export const getUnifiedDataSourceFields = (identifier) => {
  const headers = {}
  const dwh = getDwhCode()
  if (dwh) headers['X-DWH-Code'] = dwh
  return api.get(`/datasources/unified/${identifier}/fields`, { headers, timeout: 120000 })
}

// Parameter Resolver APIs
export const getParameterConfig = () => api.get('/builder/parameters/config')
export const extractParamsFromQuery = (query) => api.post('/builder/parameters/extract', { query })


// GridView Builder APIs
export const getGridViews = (userId) => api.get('/gridview/grids', { params: { user_id: userId } })
export const getGridView = (id) => api.get(`/gridview/grids/${id}`)
export const createGridView = (data) => api.post('/gridview/grids', data)
export const updateGridView = (id, data) => api.put(`/gridview/grids/${id}`, data)
export const deleteGridView = (id) => api.delete(`/gridview/grids/${id}`)
export const getGridData = (id, request = {}) => api.post(`/gridview/grids/${id}/data`, request)
export const exportGridData = (id, format) => api.post(`/gridview/grids/${id}/export`, { format })
export const exportGridPptx = (id) =>
  api.get(`/gridview/grids/${id}/export/pptx`,
    { headers: getDWHHeaders(), responseType: 'blob', timeout: 120000 })
export const getUserGridPrefs = (gridId, userId) => api.get(`/gridview/grids/${gridId}/user-prefs/${userId}`)
export const saveUserGridPrefs = (gridId, userId, columns) => api.put(`/gridview/grids/${gridId}/user-prefs/${userId}`, { columns })
export const resetUserGridPrefs = (gridId, userId) => api.delete(`/gridview/grids/${gridId}/user-prefs/${userId}`)
export const getUserEffectivePermissions = (userId) => api.get(`/users/${userId}/effective-permissions`)

// Query Builder APIs
export const getQueryBuilderTables = () => api.get('/builder/query-builder/tables')
export const getTableColumns = (tableName) => api.get(`/builder/query-builder/tables/${tableName}/columns`)
export const getTableRelations = (tableName) => api.get(`/builder/query-builder/tables/${tableName}/relations`)
export const buildQuery = (config) => api.post('/builder/query-builder/build', config)
export const previewBuilderQuery = (query) => api.post('/builder/query-builder/preview', { query })
export const createDataSource = (data) => api.post('/builder/datasources', data)
export const generateDashboardFromAI = (description, dwh_code) =>
  api.post('/builder/ai/generate', { description, dwh_code }, { timeout: 120000 })
export const generatePivotFromAI = (description, dwh_code) =>
  api.post('/builder/ai/generate/pivot', { description, dwh_code }, { timeout: 120000 })
export const generateGridViewFromAI = (description, dwh_code) =>
  api.post('/builder/ai/generate/gridview', { description, dwh_code }, { timeout: 120000 })

// Menu APIs
export const getAllMenus = () => api.get('/menus/')
export const getMenusFlat = () => api.get('/menus/flat')
export const getUserMenus = (userId, dwhCode = null) => {
  const headers = {}
  const dwh = dwhCode || getDwhCode()
  if (dwh) headers['X-DWH-Code'] = dwh
  return api.get(`/menus/user/${userId}`, { headers })
}
export const createMenu = (data) => api.post('/menus/', data)
export const updateMenu = (id, data) => api.put(`/menus/${id}`, data)
export const deleteMenu = (id) => api.delete(`/menus/${id}`)
export const getUserMenuAccess = (userId) => api.get(`/menus/access/${userId}`)
export const setUserMenuAccess = (data) => api.post('/menus/access', data)
export const setBulkUserMenuAccess = (data) => api.post('/menus/access/bulk', data)
export const removeUserMenuAccess = (userId, menuId) => api.delete(`/menus/access/${userId}/${menuId}`)
export const getMenuTargets = (type) => api.get(`/menus/targets/${type}`)
export const initSampleMenus = () => api.post('/menus/init-sample')

// Master Menu APIs (base centrale)
export const getMasterMenus = () => api.get('/menus/master')
export const getMasterMenusFlat = () => api.get('/menus/master/flat')
export const createMasterMenu = (data) => api.post('/menus/master', data)
export const updateMasterMenu = (id, data) => api.put(`/menus/master/${id}`, data)
export const deleteMasterMenu = (id) => api.delete(`/menus/master/${id}`)
export const getMasterMenuTargets = (type) => api.get(`/menus/master/targets/${type}`)

// Master Publish APIs
export const getMasterEntities = () => api.get('/master/entities')
export const getMasterClients = () => api.get('/master/clients')
export const publishEntities = (data) => api.post('/master/publish', data, { timeout: 300000 })
export const publishAllEntities = (data) => api.post('/master/publish-all', data, { timeout: 300000 })
export const getMenusSyncStatus = () => api.get('/master/menus-sync-status', { timeout: 120000 })
export const cleanupClientMenus = (clientCode) => api.post(`/master/cleanup-menus/${clientCode}`, {}, { timeout: 60000 })

// Update Manager — Pull menus depuis base maître (portail client)
export const pullBuilderMenus = () => api.post('/updates/pull/builder', {}, { timeout: 60000 })

// Liste Ventes APIs
export const getListeVentes = (params = {}) => api.get('/liste-ventes', { params })
export const getListeVentesFiltres = (params = {}) => api.get('/liste-ventes/filtres', { params })
export const exportListeVentes = (params = {}) => api.get('/liste-ventes/export', { params })


// Analyse CA et Creances APIs
export const getAnalyseKpis = (params = {}) => api.get('/analyse-ca-creances/kpis', { params })
export const getAnalyseTopClientsCA = (params = {}) => api.get('/analyse-ca-creances/top-clients-ca', { params })
export const getAnalyseTopClientsCreances = (params = {}) => api.get('/analyse-ca-creances/top-clients-creances', { params })
export const getAnalyseCAParMois = (params = {}) => api.get('/analyse-ca-creances/ca-par-mois', { params })
export const getAnalyseCAParCommercial = (params = {}) => api.get('/analyse-ca-creances/ca-par-commercial', { params })
export const getAnalyseFiltres = () => api.get('/analyse-ca-creances/filtres')
export const getAnalyseBalanceAgeeTranche = (params = {}) => api.get('/analyse-ca-creances/balance-agee-tranche', { params })
export const getAnalyseBalanceAgeeDetail = (params = {}) => api.get('/analyse-ca-creances/balance-agee-detail', { params })

// Pivot V2 APIs
const getDWHHeaders = () => {
  const headers = {}
  try {
    const savedDWH = localStorage.getItem('currentDWH')
    if (savedDWH) {
      const parsedDWH = JSON.parse(savedDWH)
      if (parsedDWH?.code) headers['X-DWH-Code'] = parsedDWH.code
    }
  } catch (e) { /* ignore */ }
  return headers
}

export const getPivotsV2 = (userId) => api.get('/v2/pivots', { params: { user_id: userId } })
export const getPivotV2 = (id) => api.get(`/v2/pivots/${id}`)
export const createPivotV2 = (data) => api.post('/v2/pivots', data)
export const updatePivotV2 = (id, data) => api.put(`/v2/pivots/${id}`, data)
export const deletePivotV2 = (id) => api.delete(`/v2/pivots/${id}`)
export const executePivotV2 = (id, context = {}, raw = false, dwhCode = null) => {
  const headers = dwhCode ? { 'X-DWH-Code': dwhCode } : getDWHHeaders()
  return api.post(`/v2/pivots/${id}/execute`, { context, raw }, { headers })
}
export const previewPivotV2 = (id, context = {}) => {
  return api.post(`/v2/pivots/${id}/preview`, { context }, { headers: getDWHHeaders() })
}
export const drilldownPivotV2 = (id, request) => {
  return api.post(`/v2/pivots/${id}/drilldown`, request, { headers: getDWHHeaders() })
}
export const exportDrilldownPivotV2 = (id, request) => {
  return api.post(`/v2/pivots/${id}/drilldown/export`, request, {
    headers: getDWHHeaders(),
    responseType: 'blob',
    timeout: 120000,
  })
}
export const getPivotV2Fields = (identifier) => {
  return api.get(`/v2/pivots/fields/${identifier}`, { headers: getDWHHeaders(), timeout: 120000 })
}
export const getPivotV2UserPrefs = (pivotId, userId) => api.get(`/v2/pivots/${pivotId}/prefs/${userId}`)
export const savePivotV2UserPrefs = (pivotId, userId, data) => api.put(`/v2/pivots/${pivotId}/prefs/${userId}`, data)
export const resetPivotV2UserPrefs = (pivotId, userId) => api.delete(`/v2/pivots/${pivotId}/prefs/${userId}`)
export const exportPivotV2 = (id, context = {}, format = 'excel', asBlob = false) => {
  const config = { headers: getDWHHeaders(), timeout: 120000 }
  if (asBlob) config.responseType = 'blob'
  return api.post(`/v2/pivots/${id}/export?format=${format}`, { context }, config)
}

// Helper to extract error message from API responses (handles FastAPI validation errors)
export const extractErrorMessage = (err, fallback = 'Erreur inconnue') => {
  const detail = err.response?.data?.detail
  if (!detail) return err.message || fallback
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map(d => typeof d === 'object' ? (d.msg || JSON.stringify(d)) : String(d)).join(', ')
  }
  if (typeof detail === 'object') return detail.msg || JSON.stringify(detail)
  return String(detail)
}

// Helper to download blob
export const downloadBlob = (blob, filename) => {
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  window.URL.revokeObjectURL(url)
  document.body.removeChild(a)
}

// Premier login — définir le mot de passe
export const setFirstPassword = (userId, dwhCode, newPassword) =>
  api.post('/auth/set-first-password', { user_id: userId, dwh_code: dwhCode, new_password: newPassword })

// =============================================================================
// COMPTABILITÉ
// =============================================================================
export const getComptabiliteKpis = (exercice) =>
  api.get('/comptabilite/kpis', { params: exercice ? { exercice } : {} })

export const getBalanceGenerale = (exercice) =>
  api.get('/comptabilite/balance-generale', { params: exercice ? { exercice } : {} })

export const getJournalEcritures = (params = {}) =>
  api.get('/comptabilite/journal-ecritures', { params })

export const getBalanceTiers = (type_tiers = 'all') =>
  api.get('/comptabilite/balance-tiers', { params: { type_tiers } })

export const getTresorerie = (params = {}) =>
  api.get('/comptabilite/tresorerie', { params })

export const getDetailCharges = (exercice) =>
  api.get('/comptabilite/charges', { params: exercice ? { exercice } : {} })

export const getDetailProduits = (exercice) =>
  api.get('/comptabilite/produits', { params: exercice ? { exercice } : {} })

export const getEcheancesClientsCompta = (params = {}) =>
  api.get('/comptabilite/echeances-clients', { params })

export const getEcheancesFournisseurs = () =>
  api.get('/comptabilite/echeances-fournisseurs')

export const getLettrage = (params = {}) =>
  api.get('/comptabilite/lettrage', { params })

export const getAnalysesComptables = (exercice) =>
  api.get('/comptabilite/analyses', { params: exercice ? { exercice } : {} })

export const seedComptabiliteDatasources = () =>
  api.post('/comptabilite/seed-datasources')

export const seedComptabiliteReports = () =>
  api.post('/comptabilite/seed-reports')

// AI Presentation Builder
export const aiPresentationChat = (message, type = 'pptx') =>
  api.post('/ai/presentation/chat', { message, type })

export const aiPresentationGenerate = (slides, type = 'pptx') =>
  api.post('/ai/presentation/generate', { slides, type }, { responseType: 'blob' })

// Sage Direct Config Admin
export const getSageConfigMappings = (includeInactive = true) =>
  api.get('/admin/sage-config', { params: { include_inactive: includeInactive } })

export const getSageConfigMapping = (id) =>
  api.get(`/admin/sage-config/${id}`)

export const createSageMapping = (payload) =>
  api.post('/admin/sage-config', payload)

export const updateSageMapping = (id, payload) =>
  api.put(`/admin/sage-config/${id}`, payload)

export const deleteSageMapping = (id) =>
  api.delete(`/admin/sage-config/${id}`)

export const resetSageMappings = () =>
  api.post('/admin/sage-config/reset')

export const invalidateSageCache = () =>
  api.post('/admin/sage-config/invalidate-cache')

export const testSageSql = (sageSql, dbName = 'bijou', societeCode = 'TEST') =>
  api.post('/admin/sage-config/test-sql', { sage_sql: sageSql, db_name: dbName, societe_code: societeCode })

export default api
