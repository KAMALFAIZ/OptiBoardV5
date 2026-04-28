import { useState } from 'react'
import { KeyRound, Eye, EyeOff, CheckCircle2, LogOut } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import api from '../../services/api'

export default function ChangePasswordPage() {
  const { user, logout } = useAuth()
  const [form, setForm] = useState({ current: '', next: '', confirm: '' })
  const [show, setShow] = useState({ current: false, next: false, confirm: false })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)

  const toggle = (field) => setShow(s => ({ ...s, [field]: !s[field] }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    if (form.next !== form.confirm) {
      setError('Les nouveaux mots de passe ne correspondent pas.')
      return
    }
    if (form.next.length < 6) {
      setError('Le nouveau mot de passe doit contenir au moins 6 caractères.')
      return
    }

    setLoading(true)
    try {
      await api.post('/auth/change-password', {
        current_password: form.current,
        new_password: form.next,
      })
      setSuccess(true)
      setForm({ current: '', next: '', confirm: '' })
    } catch (err) {
      setError(err.response?.data?.detail || 'Erreur lors du changement de mot de passe.')
    } finally {
      setLoading(false)
    }
  }

  const PasswordField = ({ label, field }) => (
    <div>
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
        {label}
      </label>
      <div className="relative">
        <input
          type={show[field] ? 'text' : 'password'}
          value={form[field]}
          onChange={e => setForm(f => ({ ...f, [field]: e.target.value }))}
          className="w-full h-12 px-4 pr-12 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-base focus:outline-none focus:ring-2 focus:ring-primary-500"
          placeholder="••••••••"
          required
        />
        <button
          type="button"
          onClick={() => toggle(field)}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 p-1"
        >
          {show[field] ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
        </button>
      </div>
    </div>
  )

  return (
    <div className="p-4 max-w-md mx-auto">
      {/* Info utilisateur */}
      <div className="bg-white dark:bg-gray-800 rounded-2xl p-4 mb-4 flex items-center gap-3 shadow-sm">
        <div className="w-10 h-10 rounded-full bg-primary-100 dark:bg-primary-900 flex items-center justify-center">
          <span className="text-primary-700 dark:text-primary-300 font-bold text-sm">
            {user?.prenom?.[0]}{user?.nom?.[0]}
          </span>
        </div>
        <div className="min-w-0">
          <p className="font-semibold text-gray-900 dark:text-white text-sm truncate">
            {user?.prenom} {user?.nom}
          </p>
          <p className="text-gray-500 dark:text-gray-400 text-xs truncate">{user?.username}</p>
        </div>
      </div>

      {/* Formulaire */}
      <div className="bg-white dark:bg-gray-800 rounded-2xl p-5 shadow-sm">
        <div className="flex items-center gap-2 mb-5">
          <KeyRound className="w-5 h-5 text-primary-600" />
          <h2 className="font-bold text-gray-900 dark:text-white">Changer le mot de passe</h2>
        </div>

        {success ? (
          <div className="flex flex-col items-center py-6 gap-3">
            <CheckCircle2 className="w-12 h-12 text-green-500" />
            <p className="text-green-700 dark:text-green-400 font-medium text-center">
              Mot de passe modifié avec succès !
            </p>
            <button
              onClick={() => setSuccess(false)}
              className="mt-2 text-sm text-primary-600 underline"
            >
              Modifier à nouveau
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <PasswordField label="Mot de passe actuel" field="current" />
            <PasswordField label="Nouveau mot de passe" field="next" />
            <PasswordField label="Confirmer le nouveau mot de passe" field="confirm" />

            {error && (
              <p className="text-red-600 dark:text-red-400 text-sm bg-red-50 dark:bg-red-900/20 p-3 rounded-lg">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full h-12 rounded-xl bg-primary-600 hover:bg-primary-700 disabled:opacity-60 text-white font-semibold text-sm transition-colors mt-1"
            >
              {loading ? 'Enregistrement...' : 'Enregistrer'}
            </button>
          </form>
        )}
      </div>

      {/* Déconnexion */}
      <button
        onClick={() => logout()}
        className="w-full mt-4 h-12 rounded-xl border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 font-medium text-sm flex items-center justify-center gap-2 transition-colors hover:bg-gray-50 dark:hover:bg-gray-800"
      >
        <LogOut className="w-4 h-4" />
        Déconnexion
      </button>
    </div>
  )
}
