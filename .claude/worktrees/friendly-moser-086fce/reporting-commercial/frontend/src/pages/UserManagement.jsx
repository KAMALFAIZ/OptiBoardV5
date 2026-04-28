import { useState, useEffect } from 'react'
import { Users, Building2, Plus, Edit2, Trash2, RefreshCw, Eye, EyeOff, Check, X, Shield, Database } from 'lucide-react'
import Loading from '../components/common/Loading'
import api, {
  getUsers,
  createUser,
  updateUser,
  deleteUser,
  resetUserPassword,
  getAvailablePages,
  extractErrorMessage
} from '../services/api'

export default function UserManagement() {
  const [loading, setLoading] = useState(true)
  const [users, setUsers] = useState([])
  const [dwhList, setDwhList] = useState([])
  const [pages, setPages] = useState([])
  const [showModal, setShowModal] = useState(false)
  const [editingUser, setEditingUser] = useState(null)
  const [showPassword, setShowPassword] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  // Sources Sage par DWH (pour les societes)
  const [sourcesByDwh, setSourcesByDwh] = useState({})
  const [loadingSources, setLoadingSources] = useState(false)

  const [formData, setFormData] = useState({
    username: '',
    password: '',
    nom: '',
    prenom: '',
    email: '',
    role: 'user',
    dwh_autorises: [],
    societes: [],
    pages_autorisees: []
  })

  useEffect(() => {
    loadData()
  }, [])

  // Charger les sources quand les DWH autorises changent
  useEffect(() => {
    loadSourcesForDwh()
  }, [formData.dwh_autorises])

  const loadData = async () => {
    setLoading(true)
    try {
      const [usersRes, dwhRes, pagesRes] = await Promise.all([
        getUsers(),
        api.get('/dwh-admin/list'),
        getAvailablePages()
      ])
      setUsers(usersRes.data.data || [])
      setDwhList(dwhRes.data.data || [])
      setPages(pagesRes.data.data || [])
    } catch (error) {
      console.error('Erreur chargement:', error)
      setError('Erreur lors du chargement des donnees')
    } finally {
      setLoading(false)
    }
  }

  const loadSourcesForDwh = async () => {
    if (formData.dwh_autorises.length === 0) {
      setSourcesByDwh({})
      return
    }

    setLoadingSources(true)
    const sources = {}

    for (const dwhCode of formData.dwh_autorises) {
      try {
        const res = await api.get(`/dwh-admin/${dwhCode}/sources`)
        sources[dwhCode] = res.data.data || []
      } catch (error) {
        console.error(`Erreur chargement sources ${dwhCode}:`, error)
        sources[dwhCode] = []
      }
    }

    setSourcesByDwh(sources)
    setLoadingSources(false)
  }

  const handleCreate = () => {
    setEditingUser(null)
    setFormData({
      username: '',
      password: '',
      nom: '',
      prenom: '',
      email: '',
      role: 'user',
      dwh_autorises: [],
      societes: [],
      pages_autorisees: []
    })
    setSourcesByDwh({})
    setShowModal(true)
    setError(null)
  }

  const handleEdit = (user) => {
    setEditingUser(user)
    setFormData({
      username: user.username,
      password: '',
      nom: user.nom || '',
      prenom: user.prenom || '',
      email: user.email || '',
      role: user.role || 'user',
      dwh_autorises: user.dwh_autorises || [],
      societes: user.societes || [],
      pages_autorisees: user.pages_autorisees || []
    })
    setShowModal(true)
    setError(null)
  }

  const handleDelete = async (user) => {
    if (!confirm(`Supprimer l'utilisateur ${user.nom} ${user.prenom} ?`)) return

    try {
      await deleteUser(user.id)
      loadData()
    } catch (error) {
      console.error('Erreur suppression:', error)
      setError('Erreur lors de la suppression')
    }
  }

  const handleResetPassword = async (user) => {
    if (!confirm(`Reinitialiser le mot de passe de ${user.nom} ${user.prenom} ? Le nouveau mot de passe sera: ${user.username}`)) return

    try {
      await resetUserPassword(user.id)
      alert(`Mot de passe reinitialise: ${user.username}`)
    } catch (error) {
      console.error('Erreur reset:', error)
      setError('Erreur lors de la reinitialisation')
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError(null)

    try {
      if (editingUser) {
        await updateUser(editingUser.id, {
          nom: formData.nom,
          prenom: formData.prenom,
          email: formData.email,
          role: formData.role,
          dwh_autorises: formData.dwh_autorises,
          societes: formData.societes,
          pages_autorisees: formData.pages_autorisees
        })
      } else {
        await createUser(formData)
      }
      setShowModal(false)
      loadData()
    } catch (error) {
      console.error('Erreur sauvegarde:', error)
      setError(extractErrorMessage(error, 'Erreur lors de la sauvegarde'))
    } finally {
      setSaving(false)
    }
  }

  const toggleDwh = (code) => {
    setFormData(prev => {
      const newDwh = prev.dwh_autorises.includes(code)
        ? prev.dwh_autorises.filter(d => d !== code)
        : [...prev.dwh_autorises, code]

      // Nettoyer les societes qui n'appartiennent plus aux DWH selectionnes
      const validSocietes = prev.societes.filter(s => {
        const [dwhCode] = s.split(':')
        return newDwh.includes(dwhCode)
      })

      return {
        ...prev,
        dwh_autorises: newDwh,
        societes: validSocietes
      }
    })
  }

  const toggleSociete = (dwhCode, societeCode) => {
    const fullCode = `${dwhCode}:${societeCode}`
    setFormData(prev => ({
      ...prev,
      societes: prev.societes.includes(fullCode)
        ? prev.societes.filter(s => s !== fullCode)
        : [...prev.societes, fullCode]
    }))
  }

  const togglePage = (code) => {
    setFormData(prev => ({
      ...prev,
      pages_autorisees: prev.pages_autorisees.includes(code)
        ? prev.pages_autorisees.filter(p => p !== code)
        : [...prev.pages_autorisees, code]
    }))
  }

  const getRoleBadge = (role) => {
    const styles = {
      superadmin: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
      admin: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
      user: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
      readonly: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-400'
    }
    return styles[role] || styles.user
  }

  const getDwhName = (code) => {
    const dwh = dwhList.find(d => d.code === code)
    return dwh ? dwh.nom : code
  }

  if (loading) {
    return <Loading message="Chargement des utilisateurs..." />
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Gestion des Utilisateurs</h1>
          <p className="text-gray-500 dark:text-gray-400">
            Gerez les utilisateurs et leurs permissions multi-tenant
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={loadData} className="btn-secondary flex items-center gap-2">
            <RefreshCw className="w-4 h-4" />
            Actualiser
          </button>
          <button onClick={handleCreate} className="btn-primary flex items-center gap-2">
            <Plus className="w-4 h-4" />
            Nouvel Utilisateur
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <Users className="w-8 h-8 text-primary-500" />
            <div>
              <p className="text-sm text-gray-500">Total Utilisateurs</p>
              <p className="text-2xl font-bold">{users.length}</p>
            </div>
          </div>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <Shield className="w-8 h-8 text-red-500" />
            <div>
              <p className="text-sm text-gray-500">Administrateurs</p>
              <p className="text-2xl font-bold">{users.filter(u => u.role === 'admin' || u.role === 'superadmin').length}</p>
            </div>
          </div>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <Database className="w-8 h-8 text-blue-500" />
            <div>
              <p className="text-sm text-gray-500">Clients DWH</p>
              <p className="text-2xl font-bold">{dwhList.length}</p>
            </div>
          </div>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <Check className="w-8 h-8 text-green-500" />
            <div>
              <p className="text-sm text-gray-500">Utilisateurs Actifs</p>
              <p className="text-2xl font-bold">{users.filter(u => u.actif).length}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Users Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto border table-theme rounded">
          <table className="w-full text-sm">
            <thead>
              <tr className="table-theme-header border-b">
                <th className="px-3 py-2 text-left text-xs font-semibold border-r">Utilisateur</th>
                <th className="px-3 py-2 text-left text-xs font-semibold border-r">Role</th>
                <th className="px-3 py-2 text-left text-xs font-semibold border-r">DWH Autorises</th>
                <th className="px-3 py-2 text-left text-xs font-semibold border-r">Societes</th>
                <th className="px-3 py-2 text-left text-xs font-semibold border-r">Statut</th>
                <th className="px-3 py-2 text-center text-xs font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-3 py-8 text-center text-gray-500">
                    Aucun utilisateur configure
                  </td>
                </tr>
              ) : (
                users.map((user) => (
                  <tr
                    key={user.id}
                    className="table-theme-row border-b last:border-b-0 transition-colors"
                  >
                    <td className="px-3 py-2 border-r table-theme-cell">
                      <div>
                        <p className="font-medium text-gray-900 dark:text-white">{user.nom} {user.prenom}</p>
                        <p className="text-xs text-gray-500">{user.username}</p>
                        {user.email && <p className="text-xs text-gray-400">{user.email}</p>}
                      </div>
                    </td>
                    <td className="px-3 py-2 border-r table-theme-cell">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getRoleBadge(user.role)}`}>
                        {user.role}
                      </span>
                    </td>
                    <td className="px-3 py-2 border-r table-theme-cell">
                      <div className="flex flex-wrap gap-1">
                        {user.dwh_autorises?.length > 0 ? (
                          user.dwh_autorises.map(d => (
                            <span key={d} className="px-2 py-0.5 bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 rounded text-xs">
                              {getDwhName(d)}
                            </span>
                          ))
                        ) : (
                          <span className="text-gray-400 text-xs">Tous</span>
                        )}
                      </div>
                    </td>
                    <td className="px-3 py-2 border-r table-theme-cell">
                      <div className="flex flex-wrap gap-1 max-w-xs">
                        {user.societes?.length > 0 ? (
                          user.societes.slice(0, 3).map(s => (
                            <span key={s} className="px-2 py-0.5 bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 rounded text-xs">
                              {s.split(':')[1] || s}
                            </span>
                          ))
                        ) : (
                          <span className="text-gray-400 text-xs">Toutes</span>
                        )}
                        {user.societes?.length > 3 && (
                          <span className="text-gray-500 text-xs">+{user.societes.length - 3}</span>
                        )}
                      </div>
                    </td>
                    <td className="px-3 py-2 border-r table-theme-cell">
                      {user.actif ? (
                        <span className="flex items-center gap-1 text-green-600 text-xs">
                          <Check className="w-3 h-3" /> Actif
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-red-600 text-xs">
                          <X className="w-3 h-3" /> Inactif
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex items-center justify-center gap-1">
                        <button
                          onClick={() => handleEdit(user)}
                          className="p-1.5 rounded hover:bg-blue-100 dark:hover:bg-blue-900/30 text-blue-600"
                          title="Modifier"
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleResetPassword(user)}
                          className="p-1.5 rounded hover:bg-amber-100 dark:hover:bg-amber-900/30 text-amber-600"
                          title="Reinitialiser mot de passe"
                        >
                          <RefreshCw className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(user)}
                          className="p-1.5 rounded hover:bg-red-100 dark:hover:bg-red-900/30 text-red-600"
                          title="Supprimer"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal Create/Edit */}
      {showModal && (
        <div className="fixed inset-0 z-50 overflow-hidden">
          <div className="absolute inset-0 bg-black/50" onClick={() => setShowModal(false)} />
          <div className="absolute inset-4 lg:inset-y-6 lg:inset-x-1/4 bg-white dark:bg-gray-800 rounded-xl shadow-xl flex flex-col">
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                {editingUser ? 'Modifier Utilisateur' : 'Nouvel Utilisateur'}
              </h2>
              <button onClick={() => setShowModal(false)} className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-4 space-y-4">
              {error && (
                <div className="p-3 bg-red-50 dark:bg-red-900/20 text-red-600 rounded-lg text-sm">
                  {error}
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Email (identifiant de connexion)
                  </label>
                  <input
                    type="email"
                    value={formData.username}
                    onChange={(e) => setFormData({ ...formData, username: e.target.value, email: e.target.value })}
                    disabled={!!editingUser}
                    required
                    placeholder="exemple@email.com"
                    className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-700 disabled:opacity-50"
                  />
                </div>
                {!editingUser && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Mot de passe
                    </label>
                    <div className="relative">
                      <input
                        type={showPassword ? 'text' : 'password'}
                        value={formData.password}
                        onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                        required
                        className="w-full px-3 py-2 pr-10 border border-primary-300 dark:border-primary-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-700"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400"
                      >
                        {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>
                )}
                {editingUser && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Email
                    </label>
                    <input
                      type="email"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-700"
                    />
                  </div>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Nom
                  </label>
                  <input
                    type="text"
                    value={formData.nom}
                    onChange={(e) => setFormData({ ...formData, nom: e.target.value })}
                    required
                    className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-700"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Prenom
                  </label>
                  <input
                    type="text"
                    value={formData.prenom}
                    onChange={(e) => setFormData({ ...formData, prenom: e.target.value })}
                    required
                    className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-700"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Role
                </label>
                <select
                  value={formData.role}
                  onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                  className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-700"
                >
                  <option value="user">Utilisateur</option>
                  <option value="admin">Administrateur</option>
                  <option value="superadmin">Super Admin</option>
                  <option value="readonly">Lecture seule</option>
                </select>
              </div>

              {/* DWH Autorises */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  <Database className="w-4 h-4 inline mr-1" />
                  Clients DWH autorises
                </label>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-2 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg max-h-32 overflow-y-auto">
                  {dwhList.length === 0 ? (
                    <p className="text-gray-500 text-sm col-span-full">Aucun client DWH configure</p>
                  ) : (
                    dwhList.map(dwh => (
                      <label key={dwh.code} className="flex items-center gap-2 cursor-pointer p-1 hover:bg-gray-100 dark:hover:bg-gray-600 rounded">
                        <input
                          type="checkbox"
                          checked={formData.dwh_autorises.includes(dwh.code)}
                          onChange={() => toggleDwh(dwh.code)}
                          className="rounded border-primary-300 text-primary-600 focus:ring-primary-500"
                        />
                        <div className="flex-1 min-w-0">
                          <span className="text-sm text-gray-700 dark:text-gray-300 truncate block">{dwh.nom}</span>
                          <span className="text-xs text-gray-500">{dwh.code}</span>
                        </div>
                      </label>
                    ))
                  )}
                </div>
                <p className="text-xs text-gray-500 mt-1">Laisser vide pour autoriser tous les DWH</p>
              </div>

              {/* Societes par DWH */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  <Building2 className="w-4 h-4 inline mr-1" />
                  Societes autorisees par DWH
                </label>
                <div className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg max-h-48 overflow-y-auto">
                  {formData.dwh_autorises.length === 0 ? (
                    <p className="text-gray-500 text-sm">Selectionnez d'abord des clients DWH</p>
                  ) : loadingSources ? (
                    <div className="flex items-center gap-2 text-gray-500">
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      Chargement des societes...
                    </div>
                  ) : (
                    formData.dwh_autorises.map(dwhCode => (
                      <div key={dwhCode} className="mb-3 last:mb-0">
                        <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1 flex items-center gap-1">
                          <Database className="w-3 h-3" />
                          {getDwhName(dwhCode)}
                        </p>
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-1 pl-4">
                          {(sourcesByDwh[dwhCode] || []).length === 0 ? (
                            <p className="text-xs text-gray-400 col-span-full">Aucune societe configuree</p>
                          ) : (
                            sourcesByDwh[dwhCode].map(source => (
                              <label key={source.code} className="flex items-center gap-2 cursor-pointer p-1 hover:bg-gray-100 dark:hover:bg-gray-600 rounded">
                                <input
                                  type="checkbox"
                                  checked={formData.societes.includes(`${dwhCode}:${source.code}`)}
                                  onChange={() => toggleSociete(dwhCode, source.code)}
                                  className="rounded border-primary-300 text-green-600 focus:ring-green-500"
                                />
                                <span className="text-sm text-gray-700 dark:text-gray-300 truncate">{source.nom_societe}</span>
                              </label>
                            ))
                          )}
                        </div>
                      </div>
                    ))
                  )}
                </div>
                <p className="text-xs text-gray-500 mt-1">Laisser vide pour autoriser toutes les societes</p>
              </div>

              {/* Pages */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Pages autorisees
                </label>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-2 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                  {pages.map(page => (
                    <label key={page.code} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formData.pages_autorisees.includes(page.code)}
                        onChange={() => togglePage(page.code)}
                        className="rounded border-primary-300 text-primary-600 focus:ring-primary-500"
                      />
                      <div>
                        <span className="text-sm text-gray-700 dark:text-gray-300">{page.nom}</span>
                        <p className="text-xs text-gray-500">{page.description}</p>
                      </div>
                    </label>
                  ))}
                </div>
              </div>
            </form>

            <div className="flex items-center justify-end gap-2 px-4 py-3 border-t border-gray-200 dark:border-gray-700">
              <button
                type="button"
                onClick={() => setShowModal(false)}
                className="btn-secondary"
              >
                Annuler
              </button>
              <button
                onClick={handleSubmit}
                disabled={saving}
                className="btn-primary flex items-center gap-2"
              >
                {saving ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Enregistrement...
                  </>
                ) : (
                  <>
                    <Check className="w-4 h-4" />
                    {editingUser ? 'Modifier' : 'Creer'}
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
