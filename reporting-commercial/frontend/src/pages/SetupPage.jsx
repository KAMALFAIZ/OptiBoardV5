import { useState, useEffect } from 'react'
import { Database, Server, User, Lock, CheckCircle, XCircle, AlertCircle, Settings, Loader2 } from 'lucide-react'
import api, { extractErrorMessage } from '../services/api'

export default function SetupPage({ onConfigured }) {
  const [step, setStep] = useState(1)
  const [loading, setLoading] = useState(false)
  const [testing, setTesting] = useState(false)
  const [error, setError] = useState(null)
  const [testResult, setTestResult] = useState(null)
  const [databases, setDatabases] = useState([])
  const [loadingDatabases, setLoadingDatabases] = useState(false)

  const [config, setConfig] = useState({
    server: '',
    database: '',
    username: '',
    password: '',
    app_name: 'OptiBoard - Reporting Commercial'
  })

  // Tester la connexion
  const handleTestConnection = async () => {
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

  // Charger la liste des bases de donnees
  const handleLoadDatabases = async () => {
    if (!config.server || !config.username || !config.password) return

    setLoadingDatabases(true)
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
      }
    } catch (err) {
      console.error('Erreur chargement bases:', err)
    } finally {
      setLoadingDatabases(false)
    }
  }

  // Sauvegarder la configuration
  const handleSaveConfig = async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await api.post('/setup/configure', config)

      if (response.data.success) {
        setStep(3)
        // Notifier le parent que la configuration est terminee
        if (onConfigured) {
          setTimeout(() => onConfigured(), 2000)
        }
      } else {
        setError(response.data.error || 'Erreur lors de la configuration')
      }
    } catch (err) {
      setError(extractErrorMessage(err, 'Erreur lors de la sauvegarde'))
    } finally {
      setLoading(false)
    }
  }

  const canProceed = config.server && config.database && config.username && config.password

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-600 via-blue-700 to-indigo-800 p-4">
      <div className="w-full max-w-2xl">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-white rounded-full shadow-lg mb-4">
            <Settings className="w-10 h-10 text-blue-600" />
          </div>
          <h1 className="text-3xl font-bold text-white">Configuration Initiale</h1>
          <p className="text-blue-200 mt-2">Configurez la connexion a votre base de donnees OptiBoard_SaaS</p>
        </div>

        {/* Progress Steps */}
        <div className="flex justify-center mb-8">
          <div className="flex items-center">
            <div className={`w-10 h-10 rounded-full flex items-center justify-center ${step >= 1 ? 'bg-white text-blue-600' : 'bg-blue-400 text-white'}`}>
              1
            </div>
            <div className={`w-20 h-1 ${step >= 2 ? 'bg-white' : 'bg-blue-400'}`}></div>
            <div className={`w-10 h-10 rounded-full flex items-center justify-center ${step >= 2 ? 'bg-white text-blue-600' : 'bg-blue-400 text-white'}`}>
              2
            </div>
            <div className={`w-20 h-1 ${step >= 3 ? 'bg-white' : 'bg-blue-400'}`}></div>
            <div className={`w-10 h-10 rounded-full flex items-center justify-center ${step >= 3 ? 'bg-white text-blue-600' : 'bg-blue-400 text-white'}`}>
              3
            </div>
          </div>
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl shadow-xl p-8">
          {step === 1 && (
            <>
              <h2 className="text-xl font-semibold text-gray-900 mb-6">
                Connexion au serveur SQL
              </h2>

              {error && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-600">
                  <AlertCircle className="w-5 h-5 flex-shrink-0" />
                  <span className="text-sm">{error}</span>
                </div>
              )}

              <div className="space-y-5">
                {/* Serveur */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    <Server className="w-4 h-4 inline mr-1" />
                    Serveur SQL
                  </label>
                  <input
                    type="text"
                    value={config.server}
                    onChange={(e) => setConfig({ ...config, server: e.target.value })}
                    placeholder="ex: localhost, 192.168.1.100, server.domain.com"
                    className="w-full px-4 py-2.5 border border-primary-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>

                {/* Username */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    <User className="w-4 h-4 inline mr-1" />
                    Utilisateur SQL
                  </label>
                  <input
                    type="text"
                    value={config.username}
                    onChange={(e) => setConfig({ ...config, username: e.target.value })}
                    placeholder="ex: sa"
                    className="w-full px-4 py-2.5 border border-primary-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>

                {/* Password */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    <Lock className="w-4 h-4 inline mr-1" />
                    Mot de passe SQL
                  </label>
                  <input
                    type="password"
                    value={config.password}
                    onChange={(e) => setConfig({ ...config, password: e.target.value })}
                    placeholder="Mot de passe"
                    className="w-full px-4 py-2.5 border border-primary-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>

                {/* Database avec liste deroulante */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
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
                      className="flex-1 px-4 py-2.5 border border-primary-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                    <button
                      type="button"
                      onClick={handleLoadDatabases}
                      disabled={!config.server || !config.username || !config.password || loadingDatabases}
                      className="px-4 py-2.5 bg-gray-100 hover:bg-gray-200 disabled:bg-gray-50 text-gray-700 rounded-lg transition-colors"
                    >
                      {loadingDatabases ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Charger'}
                    </button>
                  </div>
                  <datalist id="database-list">
                    {databases.map(db => (
                      <option key={db} value={db} />
                    ))}
                  </datalist>
                </div>

                {/* App Name */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    Nom de l'application
                  </label>
                  <input
                    type="text"
                    value={config.app_name}
                    onChange={(e) => setConfig({ ...config, app_name: e.target.value })}
                    placeholder="OptiBoard - Reporting Commercial"
                    className="w-full px-4 py-2.5 border border-primary-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>

              <div className="mt-6 flex justify-end">
                <button
                  onClick={() => setStep(2)}
                  disabled={!canProceed}
                  className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-medium rounded-lg transition-colors"
                >
                  Suivant
                </button>
              </div>
            </>
          )}

          {step === 2 && (
            <>
              <h2 className="text-xl font-semibold text-gray-900 mb-6">
                Test de connexion
              </h2>

              {/* Resume de la config */}
              <div className="bg-gray-50 rounded-lg p-4 mb-6">
                <h3 className="text-sm font-medium text-gray-700 mb-3">Configuration:</h3>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <span className="text-gray-500">Serveur:</span>
                  <span className="font-medium">{config.server}</span>
                  <span className="text-gray-500">Base:</span>
                  <span className="font-medium">{config.database}</span>
                  <span className="text-gray-500">Utilisateur:</span>
                  <span className="font-medium">{config.username}</span>
                </div>
              </div>

              {/* Resultat du test */}
              {testResult && (
                <div className={`mb-6 p-4 rounded-lg ${testResult.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
                  <div className="flex items-center gap-2 mb-2">
                    {testResult.success ? (
                      <CheckCircle className="w-5 h-5 text-green-600" />
                    ) : (
                      <XCircle className="w-5 h-5 text-red-600" />
                    )}
                    <span className={`font-medium ${testResult.success ? 'text-green-700' : 'text-red-700'}`}>
                      {testResult.message}
                    </span>
                  </div>
                  {testResult.success && testResult.serverInfo && (
                    <div className="text-sm text-green-600 mt-2">
                      {testResult.databaseExists === false ? (
                        <p className="text-amber-600">Base inexistante - sera creee automatiquement</p>
                      ) : (
                        <p>Tables existantes: {testResult.serverInfo.table_count}</p>
                      )}
                    </div>
                  )}
                  {testResult.warning && (
                    <div className="mt-2 p-2 bg-amber-50 border border-amber-200 rounded text-sm text-amber-700">
                      <AlertCircle className="w-4 h-4 inline mr-1" />
                      {testResult.warning}
                    </div>
                  )}
                </div>
              )}

              {error && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-600">
                  <AlertCircle className="w-5 h-5 flex-shrink-0" />
                  <span className="text-sm">{error}</span>
                </div>
              )}

              <div className="flex justify-between">
                <button
                  onClick={() => setStep(1)}
                  className="px-6 py-2.5 bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium rounded-lg transition-colors"
                >
                  Retour
                </button>
                <div className="flex gap-3">
                  <button
                    onClick={handleTestConnection}
                    disabled={testing}
                    className="px-6 py-2.5 bg-gray-600 hover:bg-gray-700 disabled:bg-gray-400 text-white font-medium rounded-lg transition-colors flex items-center gap-2"
                  >
                    {testing ? (
                      <>
                        <Loader2 className="w-5 h-5 animate-spin" />
                        Test...
                      </>
                    ) : (
                      'Tester la connexion'
                    )}
                  </button>
                  <button
                    onClick={handleSaveConfig}
                    disabled={loading || !testResult?.success}
                    className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-medium rounded-lg transition-colors flex items-center gap-2"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="w-5 h-5 animate-spin" />
                        Configuration...
                      </>
                    ) : (
                      'Configurer'
                    )}
                  </button>
                </div>
              </div>
            </>
          )}

          {step === 3 && (
            <div className="text-center py-8">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-green-100 rounded-full mb-4">
                <CheckCircle className="w-8 h-8 text-green-600" />
              </div>
              <h2 className="text-xl font-semibold text-gray-900 mb-2">
                Configuration terminee!
              </h2>
              <p className="text-gray-500 mb-6">
                L'application est maintenant configuree. Vous allez etre redirige vers la page de connexion.
              </p>
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
            </div>
          )}
        </div>

        {/* Footer */}
        <p className="text-center text-blue-200 text-sm mt-6">
          OptiBoard - Configuration initiale
        </p>
      </div>
    </div>
  )
}
