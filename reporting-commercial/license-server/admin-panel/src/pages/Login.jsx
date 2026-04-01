import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Shield, Eye, EyeOff, AlertCircle } from 'lucide-react'
import api, { setStoredKey } from '../services/api'

export default function Login() {
  const [key, setKey] = useState('')
  const [show, setShow] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!key.trim()) return

    setLoading(true)
    setError('')

    try {
      // Tester la cle en appelant /api/dashboard
      const response = await api.get('/dashboard', {
        headers: { 'X-Admin-Key': key.trim() }
      })
      if (response.data.success) {
        setStoredKey(key.trim())
        navigate('/')
      }
    } catch (err) {
      if (err.response?.status === 401) {
        setError('Clé admin incorrecte. Vérifiez la valeur de ADMIN_API_KEY dans le .env du serveur.')
      } else {
        setError('Erreur de connexion au serveur : ' + (err.message || 'inconnue'))
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md">

        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-blue-600 mb-4">
            <Shield className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">OptiBoard License Server</h1>
          <p className="text-gray-400 text-sm mt-1">Panneau d'administration</p>
        </div>

        {/* Formulaire */}
        <form onSubmit={handleSubmit} className="bg-gray-900 rounded-2xl p-6 border border-gray-800">
          <h2 className="text-lg font-semibold text-white mb-1">Connexion</h2>
          <p className="text-gray-400 text-sm mb-6">
            Entrez la clé admin configurée dans le fichier <code className="text-blue-400">.env</code> du serveur.
          </p>

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Clé admin (ADMIN_API_KEY)
            </label>
            <div className="relative">
              <input
                type={show ? 'text' : 'password'}
                value={key}
                onChange={(e) => setKey(e.target.value)}
                placeholder="kasoft-ls-admin-..."
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 pr-12
                           text-white placeholder-gray-500 focus:outline-none focus:border-blue-500
                           focus:ring-1 focus:ring-blue-500 font-mono text-sm"
                autoFocus
              />
              <button
                type="button"
                onClick={() => setShow(!show)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-200"
              >
                {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {error && (
            <div className="mb-4 flex items-start gap-2 bg-red-500/10 border border-red-500/30
                            rounded-lg p-3 text-red-400 text-sm">
              <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={loading || !key.trim()}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed
                       text-white font-medium py-3 rounded-lg transition-colors"
          >
            {loading ? 'Vérification...' : 'Accéder au panneau'}
          </button>
        </form>

        <p className="text-center text-gray-600 text-xs mt-6">
          La clé est stockée localement dans votre navigateur.
        </p>
      </div>
    </div>
  )
}
