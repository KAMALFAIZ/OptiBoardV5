import { useState, useEffect } from 'react'
import {
  Database, Server, User, Lock, CheckCircle, XCircle, AlertCircle,
  Settings, Loader2, RefreshCw, Save, TestTube, HardDrive, Activity
} from 'lucide-react'
import api, { extractErrorMessage } from '../services/api'

export default function DatabaseManagement() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [savingAppName, setSavingAppName] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState(null)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)
  const [databases, setDatabases] = useState([])
  const [loadingDatabases, setLoadingDatabases] = useState(false)
  const [dbStats, setDbStats] = useState(null)
  const [tablesStatus, setTablesStatus] = useState(null)

  const [config, setConfig] = useState({
    server: '',
    database: '',
    username: '',
    password: '',
    app_name: ''
  })

  // Charger la configuration actuelle
  useEffect(() => {
    loadCurrentConfig()
  }, [])

  const loadCurrentConfig = async () => {
    setLoading(true)
    try {
      // Charger le statut de setup avec les infos completes
      const statusResponse = await api.get('/setup/status')
      if (statusResponse.data.configured) {
        // Recuperer le nom de l'app depuis la base de donnees (prioritaire)
        let appName = statusResponse.data.app_name || ''
        try {
          const nameRes = await api.get('/setup/app-name')
          if (nameRes.data.success && nameRes.data.app_name) {
            appName = nameRes.data.app_name
          }
        } catch (e) { /* fallback */ }
        setConfig(prev => ({
          ...prev,
          server: statusResponse.data.server || '',
          database: statusResponse.data.database || '',
          username: statusResponse.data.username || prev.username || '',
          password: statusResponse.data.password || prev.password || '',
          app_name: appName
        }))
      }

      // Charger les stats de la base
      await loadDbStats()

      // Charger le statut des tables
      await loadTablesStatus()

    } catch (err) {
      console.error('Erreur chargement config:', err)
      setError('Erreur lors du chargement de la configuration')
    } finally {
      setLoading(false)
    }
  }

  const loadDbStats = async () => {
    try {
      const healthResponse = await api.get('/health')
      setDbStats({
        status: healthResponse.data.status,
        database: healthResponse.data.database,
        cache: healthResponse.data.cache
      })
    } catch (err) {
      console.error('Erreur stats DB:', err)
    }
  }

  const loadTablesStatus = async () => {
    try {
      const tablesResponse = await api.get('/setup/check-tables')
      setTablesStatus(tablesResponse.data)
    } catch (err) {
      console.error('Erreur check tables:', err)
    }
  }

  // Charger la liste des bases de donnees
  const handleLoadDatabases = async () => {
    if (!config.server || !config.username || !config.password) {
      setError('Veuillez remplir le serveur, utilisateur et mot de passe')
      return
    }

    setLoadingDatabases(true)
    setError(null)
    try {
      const response = await api.get('/setup/databases', {
        params: {
          server: config.server,
          username: config.username,
          password: config.password
        }
      })

      if (response.data.success) {
        setDatabases(response.data.databases)
      } else {
        setError(response.data.error || 'Erreur lors du chargement des bases')
      }
    } catch (err) {
      setError(extractErrorMessage(err, 'Erreur de connexion'))
    } finally {
      setLoadingDatabases(false)
    }
  }

  // Tester la connexion
  const handleTestConnection = async () => {
    if (!config.server || !config.database || !config.username || !config.password) {
      setError('Veuillez remplir tous les champs de connexion')
      return
    }

    setTesting(true)
    setError(null)
    setTestResult(null)

    try {
      const response = await api.post('/setup/test-connection', {
        server: config.server,
        database: config.database,
        username: config.username,
        password: config.password
      })

      if (response.data.success) {
        setTestResult({
          success: true,
          message: response.data.message,
          serverInfo: response.data.server_info,
          databaseExists: response.data.database_exists,
          warning: response.data.warning
        })
      } else {
        setTestResult({
          success: false,
          message: response.data.error
        })
      }
    } catch (err) {
      setTestResult({
        success: false,
        message: extractErrorMessage(err, 'Erreur de connexion')
      })
    } finally {
      setTesting(false)
    }
  }

  // Sauvegarder la configuration
  const handleSaveConfig = async () => {
    if (!config.server || !config.database || !config.username || !config.password) {
      setError('Veuillez remplir tous les champs de connexion')
      return
    }

    setSaving(true)
    setError(null)
    setSuccess(null)

    try {
      const response = await api.post('/setup/configure', {
        server: config.server,
        database: config.database,
        username: config.username,
        password: config.password,
        app_name: config.app_name || 'OptiBoard - Reporting Commercial'
      })

      if (response.data.success) {
        setSuccess('Configuration sauvegardee avec succes. Les tables ont ete initialisees. Redemarrez le backend pour appliquer les nouveaux parametres.')
        // Recharger les stats apres un petit delai
        setTimeout(async () => {
          await loadDbStats()
          await loadTablesStatus()
          // Recharger la config depuis le serveur
          await loadCurrentConfig()
        }, 1000)
      } else {
        setError(response.data.error || 'Erreur lors de la sauvegarde')
      }
    } catch (err) {
      setError(extractErrorMessage(err, 'Erreur lors de la sauvegarde'))
    } finally {
      setSaving(false)
    }
  }

  // Sauvegarder uniquement le nom de l'application (en base de donnees)
  const handleSaveAppName = async () => {
    setSavingAppName(true)
    setError(null)
    setSuccess(null)
    try {
      const response = await api.put('/setup/app-name', {
        app_name: config.app_name || 'OptiBoard - Reporting Commercial'
      })
      if (response.data.success) {
        setSuccess('Nom de l\'application sauvegarde. La page va se recharger...')
        setTimeout(() => window.location.reload(), 1500)
      }
    } catch (err) {
      setError(extractErrorMessage(err, 'Erreur lors de la sauvegarde du nom'))
    } finally {
      setSavingAppName(false)
    }
  }

  // Reinitialiser les tables
  const handleInitTables = async () => {
    if (!confirm('Voulez-vous reinitialiser toutes les tables APP? Les donnees existantes ne seront pas supprimees.')) {
      return
    }

    setLoading(true)
    setError(null)
    setSuccess(null)

    try {
      const response = await api.post('/setup/init-all-tables')
      if (response.data.success) {
        setSuccess(`Tables initialisees: ${response.data.created_tables?.join(', ')}`)
        await loadTablesStatus()
      } else {
        setError(response.data.error || 'Erreur lors de l\'initialisation')
      }
    } catch (err) {
      setError(extractErrorMessage(err, 'Erreur lors de l\'initialisation'))
    } finally {
      setLoading(false)
    }
  }

  // Vider le cache
  const handleClearCache = async () => {
    try {
      const response = await api.post('/cache/clear')
      setSuccess(response.data.message)
      await loadDbStats()
    } catch (err) {
      setError('Erreur lors du vidage du cache')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    )
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
          <Database className="w-7 h-7" />
          Gestion Base de Donnees
        </h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          Configuration de la connexion a la base OptiBoard_SaaS
        </p>
      </div>

      {/* Messages */}
      {error && (
        <div className="mb-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center gap-2 text-red-600 dark:text-red-400">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span>{error}</span>
          <button onClick={() => setError(null)} className="ml-auto text-red-400 hover:text-red-600">×</button>
        </div>
      )}

      {success && (
        <div className="mb-4 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg flex items-center gap-2 text-green-600 dark:text-green-400">
          <CheckCircle className="w-5 h-5 flex-shrink-0" />
          <span>{success}</span>
          <button onClick={() => setSuccess(null)} className="ml-auto text-green-400 hover:text-green-600">×</button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Colonne Configuration */}
        <div className="lg:col-span-2 space-y-6">
          {/* Configuration de connexion */}
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
              <Settings className="w-5 h-5" />
              Configuration de Connexion
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Serveur */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                  <Server className="w-4 h-4 inline mr-1" />
                  Serveur SQL
                </label>
                <input
                  type="text"
                  value={config.server}
                  onChange={(e) => setConfig({ ...config, server: e.target.value })}
                  placeholder="ex: localhost, 192.168.1.100"
                  className="w-full px-4 py-2.5 border border-primary-300 dark:border-primary-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              {/* Username */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                  <User className="w-4 h-4 inline mr-1" />
                  Utilisateur SQL
                </label>
                <input
                  type="text"
                  value={config.username}
                  onChange={(e) => setConfig({ ...config, username: e.target.value })}
                  placeholder="ex: sa"
                  className="w-full px-4 py-2.5 border border-primary-300 dark:border-primary-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              {/* Password */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                  <Lock className="w-4 h-4 inline mr-1" />
                  Mot de passe SQL
                </label>
                <input
                  type="password"
                  value={config.password}
                  onChange={(e) => setConfig({ ...config, password: e.target.value })}
                  placeholder="Mot de passe"
                  className="w-full px-4 py-2.5 border border-primary-300 dark:border-primary-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              {/* Database */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                  <Database className="w-4 h-4 inline mr-1" />
                  Base de donnees
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={config.database}
                    onChange={(e) => setConfig({ ...config, database: e.target.value })}
                    placeholder="ex: OptiBoard_SaaS"
                    list="database-list"
                    className="flex-1 px-4 py-2.5 border border-primary-300 dark:border-primary-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                  <button
                    type="button"
                    onClick={handleLoadDatabases}
                    disabled={loadingDatabases}
                    className="px-4 py-2.5 bg-gray-100 dark:bg-gray-600 hover:bg-gray-200 dark:hover:bg-gray-500 text-gray-700 dark:text-gray-200 rounded-lg transition-colors"
                    title="Charger les bases disponibles"
                  >
                    {loadingDatabases ? <Loader2 className="w-5 h-5 animate-spin" /> : <RefreshCw className="w-5 h-5" />}
                  </button>
                </div>
                <datalist id="database-list">
                  {databases.map(db => (
                    <option key={db} value={db} />
                  ))}
                </datalist>
              </div>

              {/* App Name */}
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                  Nom de l'application
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={config.app_name}
                    onChange={(e) => setConfig({ ...config, app_name: e.target.value })}
                    placeholder="OptiBoard - Reporting Commercial"
                    className="flex-1 px-4 py-2.5 border border-primary-300 dark:border-primary-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                  <button
                    onClick={handleSaveAppName}
                    disabled={savingAppName}
                    className="px-4 py-2.5 bg-green-600 hover:bg-green-700 disabled:bg-green-300 text-white font-medium rounded-lg transition-colors flex items-center gap-2 flex-shrink-0"
                  >
                    {savingAppName ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Save className="w-4 h-4" />
                    )}
                    Appliquer
                  </button>
                </div>
                <p className="text-xs text-gray-400 mt-1">Format: Titre - Sous-titre (ex: MonEntreprise - Reporting)</p>
              </div>
            </div>

            {/* Resultat du test */}
            {testResult && (
              <div className={`mt-4 p-4 rounded-lg ${testResult.success ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800' : 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800'}`}>
                <div className="flex items-center gap-2">
                  {testResult.success ? (
                    <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
                  ) : (
                    <XCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
                  )}
                  <span className={`font-medium ${testResult.success ? 'text-green-700 dark:text-green-300' : 'text-red-700 dark:text-red-300'}`}>
                    {testResult.message}
                  </span>
                </div>
                {testResult.success && testResult.serverInfo && (
                  <div className="text-sm text-green-600 dark:text-green-400 mt-2">
                    {testResult.databaseExists === false ? (
                      <p className="text-amber-600 dark:text-amber-400">Base inexistante - sera creee automatiquement</p>
                    ) : (
                      <p>Tables existantes: {testResult.serverInfo.table_count}</p>
                    )}
                  </div>
                )}
                {testResult.warning && (
                  <div className="mt-2 p-2 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded text-sm text-amber-700 dark:text-amber-300">
                    <AlertCircle className="w-4 h-4 inline mr-1" />
                    {testResult.warning}
                  </div>
                )}
              </div>
            )}

            {/* Boutons d'action */}
            <div className="mt-6 flex flex-wrap gap-3">
              <button
                onClick={handleTestConnection}
                disabled={testing}
                className="px-4 py-2.5 bg-gray-600 hover:bg-gray-700 disabled:bg-gray-400 text-white font-medium rounded-lg transition-colors flex items-center gap-2"
              >
                {testing ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <TestTube className="w-5 h-5" />
                )}
                Tester la connexion
              </button>
              <button
                onClick={handleSaveConfig}
                disabled={saving || !testResult?.success}
                className="px-4 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-medium rounded-lg transition-colors flex items-center gap-2"
              >
                {saving ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Save className="w-5 h-5" />
                )}
                Sauvegarder
              </button>
            </div>
          </div>

          {/* Gestion des tables */}
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
              <HardDrive className="w-5 h-5" />
              Tables Systeme
            </h2>

            {tablesStatus?.tables && (
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2 mb-4">
                {Object.entries(tablesStatus.tables).map(([table, exists]) => (
                  <div
                    key={table}
                    className={`p-2 rounded-lg text-sm flex items-center gap-2 ${
                      exists
                        ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300'
                        : 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300'
                    }`}
                  >
                    {exists ? (
                      <CheckCircle className="w-4 h-4 flex-shrink-0" />
                    ) : (
                      <XCircle className="w-4 h-4 flex-shrink-0" />
                    )}
                    <span className="truncate">{table.replace('APP_', '')}</span>
                  </div>
                ))}
              </div>
            )}

            <button
              onClick={handleInitTables}
              disabled={loading}
              className="px-4 py-2.5 bg-amber-600 hover:bg-amber-700 disabled:bg-amber-400 text-white font-medium rounded-lg transition-colors flex items-center gap-2"
            >
              <RefreshCw className="w-5 h-5" />
              Reinitialiser les tables
            </button>
          </div>
        </div>

        {/* Colonne Stats */}
        <div className="space-y-6">
          {/* Statut de connexion */}
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
              <Activity className="w-5 h-5" />
              Statut
            </h2>

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-gray-600 dark:text-gray-400">Base de donnees</span>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                  dbStats?.database === 'connected'
                    ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300'
                    : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300'
                }`}>
                  {dbStats?.database === 'connected' ? 'Connecte' : 'Deconnecte'}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-gray-600 dark:text-gray-400">Serveur</span>
                <span className="text-sm font-medium text-gray-900 dark:text-white truncate max-w-32" title={config.server}>
                  {config.server || '-'}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-gray-600 dark:text-gray-400">Base</span>
                <span className="text-sm font-medium text-gray-900 dark:text-white truncate max-w-32" title={config.database}>
                  {config.database || '-'}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-gray-600 dark:text-gray-400">Tables APP</span>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                  tablesStatus?.all_tables_exist
                    ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300'
                    : 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300'
                }`}>
                  {tablesStatus?.all_tables_exist ? 'Toutes presentes' : 'Incompletes'}
                </span>
              </div>
            </div>
          </div>

          {/* Cache */}
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
              <HardDrive className="w-5 h-5" />
              Cache
            </h2>

            {dbStats?.cache && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Entrees</span>
                  <span className="font-medium text-gray-900 dark:text-white">{dbStats.cache.entries}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Hits</span>
                  <span className="font-medium text-gray-900 dark:text-white">{dbStats.cache.hits}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Misses</span>
                  <span className="font-medium text-gray-900 dark:text-white">{dbStats.cache.misses}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Hit Rate</span>
                  <span className="font-medium text-gray-900 dark:text-white">{(dbStats.cache.hit_rate * 100).toFixed(1)}%</span>
                </div>
              </div>
            )}

            <button
              onClick={handleClearCache}
              className="mt-4 w-full px-4 py-2 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              Vider le cache
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
