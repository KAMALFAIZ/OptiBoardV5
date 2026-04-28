import { useState, useEffect } from 'react'
import { X, Server, Copy, Check, AlertTriangle, Database, ChevronDown, ChevronUp } from 'lucide-react'
import { createAgent } from '../../services/etlApi'
import { extractErrorMessage, getClientDwhSources } from '../../services/api'

export default function CreateAgentModal({ dwhList, isClientPortal = false, clientDwhCode = '', clientDwhNom = '', onClose, onCreated }) {
  const [formData, setFormData] = useState({
    dwh_code: isClientPortal ? clientDwhCode : '',
    name: '',
    description: '',
    sync_interval_seconds: 300,
    batch_size: 5000,
    is_enabled: true,
    auto_start: true,
    // Connexion Sage
    sage_server: '',
    sage_database: '',
    sage_username: 'sa',
    sage_password: ''
  })
  const [showSageConfig, setShowSageConfig] = useState(true)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [sources, setSources] = useState([])

  useEffect(() => {
    getClientDwhSources().then(r => setSources(r.data?.data || [])).catch(() => {})
  }, [])

  const handleSourceSelect = (source) => {
    if (!source) return
    setFormData(f => ({
      ...f,
      name: f.name || source.nom_societe || source.code_societe,
      sage_server:   source.serveur_sage   || f.sage_server,
      sage_database: source.base_sage      || f.sage_database,
      sage_username: source.user_sage      || f.sage_username,
      sage_password: source.password_sage  || f.sage_password,
    }))
  }
  const [createdAgent, setCreatedAgent] = useState(null)
  const [copied, setCopied] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      console.log('Envoi formData:', formData)
      const response = await createAgent(formData)
      console.log('Reponse API:', response.data)

      // L'API retourne {agent: {...}, api_key: "..."}
      if (response.data.agent) {
        setCreatedAgent({
          agent_id: response.data.agent.agent_id,
          api_key: response.data.api_key,
          name: response.data.agent.name
        })
      } else if (response.data.success && response.data.data) {
        // Format alternatif {success: true, data: {...}}
        setCreatedAgent(response.data.data)
      } else {
        console.error('Format reponse inattendu:', response.data)
        setError(response.data.error || response.data.detail || 'Erreur lors de la creation')
      }
    } catch (err) {
      console.error('Erreur creation agent:', err)
      console.error('Response data:', err.response?.data)
      setError(extractErrorMessage(err, 'Erreur lors de la creation'))
    } finally {
      setLoading(false)
    }
  }

  const handleCopyConfig = () => {
    const config = `# Configuration Agent ETL
agent:
  id: "${createdAgent.agent_id}"
  api_key: "${createdAgent.api_key}"
  name: "${createdAgent.name}"

central_server:
  url: "${window.location.origin}/api"
  timeout: 60
  retry_count: 3

sage_database:
  server: "localhost"
  database: "VOTRE_BASE_SAGE"
  username: "sa"
  password: "VOTRE_MOT_DE_PASSE"
  societe_code: "VOTRE_CODE_SOCIETE"

sync:
  interval_seconds: ${formData.sync_interval_seconds}
  batch_size: ${formData.batch_size}
`
    navigator.clipboard.writeText(config)
    setCopied(true)
    setTimeout(() => setCopied(false), 3000)
  }

  const handleClose = () => {
    if (createdAgent) {
      onCreated()
    }
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <Server size={20} />
            {createdAgent ? 'Agent Cree!' : 'Nouvel Agent ETL'}
          </h2>
          <button
            onClick={handleClose}
            className="p-1 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="p-4">
          {createdAgent ? (
            // Affichage apres creation
            <div className="space-y-4">
              <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <Check className="text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" size={20} />
                  <div>
                    <h3 className="font-medium text-green-800 dark:text-green-300">
                      Agent cree avec succes!
                    </h3>
                    <p className="text-sm text-green-600 dark:text-green-400 mt-1">
                      Sauvegardez les informations ci-dessous, la cle API ne sera plus affichee.
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 space-y-3">
                <div>
                  <label className="text-xs text-gray-500 dark:text-gray-400">Agent ID</label>
                  <p className="font-mono text-sm text-gray-900 dark:text-white break-all">
                    {createdAgent.agent_id}
                  </p>
                </div>
                <div>
                  <label className="text-xs text-gray-500 dark:text-gray-400">Cle API (CONFIDENTIEL)</label>
                  <p className="font-mono text-sm text-gray-900 dark:text-white break-all bg-yellow-50 dark:bg-yellow-900/20 p-2 rounded border border-yellow-200 dark:border-yellow-800">
                    {createdAgent.api_key}
                  </p>
                </div>
              </div>

              <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" size={20} />
                  <div className="text-sm text-amber-800 dark:text-amber-300">
                    <p className="font-medium">Important:</p>
                    <ul className="list-disc list-inside mt-1 space-y-1">
                      <li>Copiez la cle API maintenant</li>
                      <li>Elle ne sera plus accessible apres fermeture</li>
                      <li>Configurez votre agent avec ces informations</li>
                    </ul>
                  </div>
                </div>
              </div>

              <button
                onClick={handleCopyConfig}
                className="w-full px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 flex items-center justify-center gap-2 transition-colors"
              >
                {copied ? <Check size={16} /> : <Copy size={16} />}
                {copied ? 'Configuration copiee!' : 'Copier la configuration YAML'}
              </button>
            </div>
          ) : (
            // Formulaire de creation
            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300 text-sm">
                  {error}
                </div>
              )}

              {/* Sélecteur DWH : visible uniquement pour superadmin */}
              {!isClientPortal ? (
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Data Warehouse *
                  </label>
                  <select
                    className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
                    value={formData.dwh_code}
                    onChange={(e) => setFormData({ ...formData, dwh_code: e.target.value })}
                    required
                  >
                    <option value="">Selectionnez un DWH</option>
                    {dwhList.map(dwh => (
                      <option key={dwh.code} value={dwh.code}>
                        {dwh.nom || dwh.code}
                      </option>
                    ))}
                  </select>
                </div>
              ) : (
                /* Portail client : DWH fixé, affiché en lecture seule */
                <div className="flex items-center gap-2 px-3 py-2 bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-700 rounded-lg">
                  <Database size={16} className="text-primary-500 flex-shrink-0" />
                  <div>
                    <p className="text-xs text-primary-500 dark:text-primary-400">Base client</p>
                    <p className="text-sm font-semibold text-primary-700 dark:text-primary-300">
                      {clientDwhNom || clientDwhCode}
                    </p>
                  </div>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Nom de l'agent *
                </label>
                <input
                  type="text"
                  className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="Ex: Agent Site Principal"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Description
                </label>
                <textarea
                  className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Description optionnelle..."
                  rows={2}
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Intervalle sync (s)
                  </label>
                  <input
                    type="number"
                    className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
                    value={formData.sync_interval_seconds}
                    onChange={(e) => setFormData({ ...formData, sync_interval_seconds: parseInt(e.target.value) })}
                    min={60}
                    max={86400}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Batch size
                  </label>
                  <input
                    type="number"
                    className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
                    value={formData.batch_size}
                    onChange={(e) => setFormData({ ...formData, batch_size: parseInt(e.target.value) })}
                    min={100}
                    max={100000}
                  />
                </div>
              </div>

              {/* Combo Sources Sage */}
              {sources.length > 0 && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Source Sage <span className="text-gray-400 font-normal">({sources.length})</span>
                  </label>
                  <select
                    className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
                    defaultValue=""
                    onChange={e => {
                      const src = sources.find(s => s.code_societe === e.target.value)
                      handleSourceSelect(src)
                    }}
                  >
                    <option value="">— Sélectionner une source pour auto-remplir —</option>
                    {sources.map(s => (
                      <option key={s.code_societe} value={s.code_societe}>
                        {s.nom_societe || s.code_societe} — {s.base_sage}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Section Connexion Sage */}
              <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
                <button
                  type="button"
                  onClick={() => setShowSageConfig(!showSageConfig)}
                  className="w-full px-4 py-3 bg-gray-50 dark:bg-gray-700/50 flex items-center justify-between text-left hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                >
                  <span className="flex items-center gap-2 font-medium text-gray-700 dark:text-gray-300">
                    <Database size={18} />
                    Connexion Base Sage
                  </span>
                  {showSageConfig ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                </button>

                {showSageConfig && (
                  <div className="p-4 space-y-3 border-t border-gray-200 dark:border-gray-700">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                          Serveur SQL
                        </label>
                        <input
                          type="text"
                          className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
                          value={formData.sage_server}
                          onChange={(e) => setFormData({ ...formData, sage_server: e.target.value })}
                          placeholder="localhost ou IP"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                          Base de donnees
                        </label>
                        <input
                          type="text"
                          className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
                          value={formData.sage_database}
                          onChange={(e) => setFormData({ ...formData, sage_database: e.target.value })}
                          placeholder="NomBaseSage"
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                          Utilisateur SQL
                        </label>
                        <input
                          type="text"
                          className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
                          value={formData.sage_username}
                          onChange={(e) => setFormData({ ...formData, sage_username: e.target.value })}
                          placeholder="sa"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                          Mot de passe SQL
                        </label>
                        <input
                          type="password"
                          className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
                          value={formData.sage_password}
                          onChange={(e) => setFormData({ ...formData, sage_password: e.target.value })}
                          placeholder="Mot de passe"
                        />
                      </div>
                    </div>

                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      Ces informations permettent a l'agent de se connecter a la base Sage pour synchroniser les donnees.
                    </p>
                  </div>
                )}
              </div>

              <div className="flex gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
                <button
                  type="button"
                  className="flex-1 px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                  onClick={onClose}
                >
                  Annuler
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50"
                  disabled={loading}
                >
                  {loading ? 'Creation...' : 'Creer l\'agent'}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}
