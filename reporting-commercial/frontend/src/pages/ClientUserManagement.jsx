import { useState, useEffect } from 'react'
import {
  Users, Plus, RefreshCw, Edit2, Trash2, Key, X, AlertCircle, CheckCircle,
  Smartphone, Shield, MapPin, Monitor, Clock, ChevronDown, ChevronUp, Calendar,
} from 'lucide-react'
import {
  getClientUsers, createClientUser, updateClientUser,
  deleteClientUser, resetClientUserPassword, extractErrorMessage
} from '../services/api'

const ROLE_LABELS = {
  user:         { label: 'Utilisateur',    color: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300' },
  admin_client: { label: 'Administrateur', color: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300' },
  readonly:     { label: 'Lecture seule',  color: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300' },
}

const JOURS = [
  { val: 1, label: 'Lu' },
  { val: 2, label: 'Ma' },
  { val: 3, label: 'Me' },
  { val: 4, label: 'Je' },
  { val: 5, label: 'Ve' },
  { val: 6, label: 'Sa' },
  { val: 7, label: 'Di' },
]

const HEURES = Array.from({ length: 24 }, (_, i) => i)

const EMPTY_FORM = {
  username: '', password: '', nom: '', prenom: '', email: '',
  role_dwh: 'user', mobile_access: true,
  ip_autorises: '', pc_autorises: '',
  heure_debut: '', heure_fin: '',
  jours_autorises: '',
}

function hasRestrictions(u) {
  return !!(u.ip_autorises || u.pc_autorises || u.heure_debut != null || u.jours_autorises)
}

export default function ClientUserManagement() {
  const [users, setUsers]                   = useState([])
  const [loading, setLoading]               = useState(true)
  const [error, setError]                   = useState(null)
  const [success, setSuccess]               = useState(null)
  const [showModal, setShowModal]           = useState(false)
  const [editUser, setEditUser]             = useState(null)
  const [formData, setFormData]             = useState(EMPTY_FORM)
  const [saving, setSaving]                 = useState(false)
  const [formError, setFormError]           = useState(null)
  const [showRestrictions, setShowRestrictions] = useState(false)

  const currentDWH = (() => {
    try { return JSON.parse(localStorage.getItem('currentDWH') || '{}') } catch { return {} }
  })()

  const load = async () => {
    setLoading(true); setError(null)
    try {
      const res = await getClientUsers()
      setUsers(res.data?.data || res.data || [])
    } catch (e) {
      setError(extractErrorMessage(e, 'Erreur de chargement'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const showSuccess = (msg) => {
    setSuccess(msg)
    setTimeout(() => setSuccess(null), 3000)
  }

  const openCreate = () => {
    setEditUser(null)
    setFormData(EMPTY_FORM)
    setFormError(null)
    setShowRestrictions(false)
    setShowModal(true)
  }

  const openEdit = (u) => {
    setEditUser(u)
    setFormData({
      username: u.username, password: '',
      nom: u.nom || '', prenom: u.prenom || '',
      email: u.email || '', role_dwh: u.role_dwh || 'user',
      mobile_access: u.mobile_access ?? true,
      ip_autorises: u.ip_autorises || '',
      pc_autorises: u.pc_autorises || '',
      heure_debut: u.heure_debut ?? '',
      heure_fin:   u.heure_fin   ?? '',
      jours_autorises: u.jours_autorises || '',
    })
    setFormError(null)
    setShowRestrictions(hasRestrictions(u))
    setShowModal(true)
  }

  const closeModal = () => { setShowModal(false); setEditUser(null) }

  const set = (k, v) => setFormData(prev => ({ ...prev, [k]: v }))

  const toggleJour = (val) => {
    const current = formData.jours_autorises
      ? formData.jours_autorises.split(',').map(Number).filter(Boolean)
      : []
    const updated = current.includes(val)
      ? current.filter(d => d !== val)
      : [...current, val].sort((a, b) => a - b)
    set('jours_autorises', updated.join(','))
  }

  const hasJour = (val) =>
    formData.jours_autorises
      ? formData.jours_autorises.split(',').map(Number).includes(val)
      : false

  const buildPayload = () => ({
    nom: formData.nom, prenom: formData.prenom,
    email: formData.email, role_dwh: formData.role_dwh,
    mobile_access: formData.role_dwh === 'admin_client' ? true : formData.mobile_access,
    ip_autorises:     formData.ip_autorises.trim()     || null,
    pc_autorises:     formData.pc_autorises.trim()     || null,
    heure_debut:      formData.heure_debut !== ''      ? parseInt(formData.heure_debut) : null,
    heure_fin:        formData.heure_fin   !== ''      ? parseInt(formData.heure_fin)   : null,
    jours_autorises:  formData.jours_autorises         || null,
  })

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true); setFormError(null)
    try {
      if (editUser) {
        await updateClientUser(editUser.id, buildPayload())
        showSuccess('Utilisateur modifié')
      } else {
        if (!formData.username || !formData.password) {
          setFormError('Identifiant et mot de passe obligatoires')
          return
        }
        await createClientUser({ ...buildPayload(), username: formData.username, password: formData.password })
        showSuccess('Utilisateur créé')
      }
      closeModal()
      load()
    } catch (e) {
      setFormError(extractErrorMessage(e, 'Erreur lors de la sauvegarde'))
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (u) => {
    if (!window.confirm(`Supprimer l'utilisateur "${u.username}" ?`)) return
    try {
      await deleteClientUser(u.id)
      showSuccess('Utilisateur supprimé')
      load()
    } catch (e) {
      setError(extractErrorMessage(e, 'Erreur de suppression'))
    }
  }

  const handleReset = async (u) => {
    if (!window.confirm(`Réinitialiser le mot de passe de "${u.username}" à son identifiant ?`)) return
    try {
      await resetClientUserPassword(u.id)
      showSuccess(`Mot de passe réinitialisé à "${u.username}"`)
    } catch (e) {
      setError(extractErrorMessage(e, 'Erreur de réinitialisation'))
    }
  }

  const handleToggleActif = async (u) => {
    try {
      await updateClientUser(u.id, { actif: !u.actif })
      showSuccess(u.actif ? 'Utilisateur désactivé' : 'Utilisateur activé')
      load()
    } catch (e) {
      setError(extractErrorMessage(e, 'Erreur'))
    }
  }

  /* ── Restriction badge tooltip ── */
  const restrictionTitle = (u) => {
    const parts = []
    if (u.ip_autorises) parts.push(`IP: ${u.ip_autorises}`)
    if (u.pc_autorises) parts.push(`Postes: ${u.pc_autorises}`)
    if (u.heure_debut != null && u.heure_fin != null)
      parts.push(`Horaire: ${String(u.heure_debut).padStart(2,'0')}h–${String(u.heure_fin).padStart(2,'0')}h`)
    if (u.jours_autorises) {
      const noms = u.jours_autorises.split(',').map(d => JOURS.find(j => j.val === +d)?.label).filter(Boolean)
      parts.push(`Jours: ${noms.join(' ')}`)
    }
    return parts.join('\n')
  }

  return (
    <div className="p-6 space-y-6">
      {/* En-tête */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg" style={{ backgroundColor: 'var(--color-primary-100)' }}>
            <Users className="w-6 h-6" style={{ color: 'var(--color-primary-600)' }} />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">
              Utilisateurs — {currentDWH.nom || currentDWH.code || 'Client'}
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Gérez les comptes de votre espace client
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={load} className="p-2 rounded-lg text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700" title="Actualiser">
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={openCreate}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-white text-sm font-medium"
            style={{ backgroundColor: 'var(--color-primary-600)' }}
          >
            <Plus className="w-4 h-4" />
            Ajouter utilisateur
          </button>
        </div>
      </div>

      {/* Alertes */}
      {error && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 text-sm">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {error}
          <button onClick={() => setError(null)} className="ml-auto"><X className="w-4 h-4" /></button>
        </div>
      )}
      {success && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 text-sm">
          <CheckCircle className="w-4 h-4 shrink-0" />
          {success}
        </div>
      )}

      {/* Tableau */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-40 text-gray-400">
            <RefreshCw className="w-5 h-5 animate-spin mr-2" /> Chargement...
          </div>
        ) : users.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-40 text-gray-400 gap-2">
            <Users className="w-10 h-10 opacity-30" />
            <p>Aucun utilisateur</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-700/50 border-b border-gray-200 dark:border-gray-700">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Identifiant</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Nom</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Email</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Rôle</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Statut</th>
                <th className="px-4 py-3 text-center font-medium text-gray-600 dark:text-gray-300" title="Accès mobile">
                  <Smartphone className="w-4 h-4 inline" />
                </th>
                <th className="px-4 py-3 text-center font-medium text-gray-600 dark:text-gray-300" title="Restrictions d'accès">
                  <Shield className="w-4 h-4 inline" />
                </th>
                <th className="px-4 py-3 text-right font-medium text-gray-600 dark:text-gray-300">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {users.map(u => {
                const role = ROLE_LABELS[u.role_dwh] || ROLE_LABELS.user
                const restricted = hasRestrictions(u)
                return (
                  <tr key={u.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                    <td className="px-4 py-3 font-medium text-gray-900 dark:text-white">{u.username}</td>
                    <td className="px-4 py-3 text-gray-600 dark:text-gray-300">
                      {[u.prenom, u.nom].filter(Boolean).join(' ') || '—'}
                    </td>
                    <td className="px-4 py-3 text-gray-500 dark:text-gray-400">{u.email || '—'}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${role.color}`}>
                        {role.label}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => handleToggleActif(u)}
                        className={`px-2 py-0.5 rounded-full text-xs font-medium cursor-pointer ${
                          u.actif
                            ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                            : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                        }`}
                        title={u.actif ? 'Cliquer pour désactiver' : 'Cliquer pour activer'}
                      >
                        {u.actif ? 'Actif' : 'Inactif'}
                      </button>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <Smartphone
                        className={`w-4 h-4 inline ${u.mobile_access ? 'text-primary-500' : 'text-gray-300 dark:text-gray-600'}`}
                        title={u.mobile_access ? 'Accès mobile activé' : 'Accès mobile désactivé'}
                      />
                    </td>
                    {/* Restrictions column */}
                    <td className="px-4 py-3 text-center">
                      {restricted ? (
                        <div className="flex items-center justify-center gap-1" title={restrictionTitle(u)}>
                          {u.ip_autorises && <MapPin  className="w-3.5 h-3.5 text-orange-500" />}
                          {u.pc_autorises && <Monitor className="w-3.5 h-3.5 text-blue-500"   />}
                          {(u.heure_debut != null || u.heure_fin != null) && <Clock    className="w-3.5 h-3.5 text-purple-500" />}
                          {u.jours_autorises && <Calendar className="w-3.5 h-3.5 text-teal-500"   />}
                        </div>
                      ) : (
                        <span className="text-gray-300 dark:text-gray-600 text-xs">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => openEdit(u)}
                          className="p-1.5 rounded-lg text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20"
                          title="Modifier"
                        ><Edit2 className="w-4 h-4" /></button>
                        <button
                          onClick={() => handleReset(u)}
                          className="p-1.5 rounded-lg text-gray-400 hover:text-orange-600 hover:bg-orange-50 dark:hover:bg-orange-900/20"
                          title="Réinitialiser le mot de passe"
                        ><Key className="w-4 h-4" /></button>
                        <button
                          onClick={() => handleDelete(u)}
                          className="p-1.5 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
                          title="Supprimer"
                        ><Trash2 className="w-4 h-4" /></button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-lg max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700 shrink-0">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                {editUser ? 'Modifier utilisateur' : 'Nouvel utilisateur'}
              </h2>
              <button onClick={closeModal} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-4 overflow-y-auto">
              {formError && (
                <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 text-sm">
                  <AlertCircle className="w-4 h-4 shrink-0" />{formError}
                </div>
              )}

              {/* Identifiant */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Identifiant *</label>
                <input
                  value={formData.username}
                  onChange={e => set('username', e.target.value)}
                  disabled={!!editUser}
                  required={!editUser}
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:opacity-60 disabled:cursor-not-allowed"
                  placeholder="ex: jean.dupont"
                />
              </div>

              {/* Mot de passe */}
              {!editUser && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Mot de passe *</label>
                  <input
                    type="password"
                    value={formData.password}
                    onChange={e => set('password', e.target.value)}
                    required
                    className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    placeholder="••••••••"
                  />
                </div>
              )}

              {/* Prénom / Nom */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Prénom</label>
                  <input value={formData.prenom} onChange={e => set('prenom', e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    placeholder="Prénom" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Nom</label>
                  <input value={formData.nom} onChange={e => set('nom', e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    placeholder="Nom" />
                </div>
              </div>

              {/* Email */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Email</label>
                <input type="email" value={formData.email} onChange={e => set('email', e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  placeholder="email@exemple.com" />
              </div>

              {/* Rôle */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Rôle</label>
                <select
                  value={formData.role_dwh}
                  onChange={e => { set('role_dwh', e.target.value); if (e.target.value === 'admin_client') set('mobile_access', true) }}
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                >
                  <option value="user">Utilisateur</option>
                  <option value="admin_client">Administrateur</option>
                  <option value="readonly">Lecture seule</option>
                </select>
              </div>

              {/* Accès mobile */}
              <div className={`flex items-start gap-3 p-3 rounded-lg border ${
                formData.role_dwh === 'admin_client'
                  ? 'border-purple-200 bg-purple-50 dark:border-purple-800 dark:bg-purple-900/20'
                  : 'border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/30'
              }`}>
                <input type="checkbox" id="mobile_access"
                  checked={formData.role_dwh === 'admin_client' ? true : !!formData.mobile_access}
                  disabled={formData.role_dwh === 'admin_client'}
                  onChange={e => set('mobile_access', e.target.checked)}
                  className="mt-0.5 w-4 h-4 rounded text-primary-600 border-gray-300 focus:ring-primary-500 disabled:opacity-60"
                />
                <div className="flex-1">
                  <label htmlFor="mobile_access" className={`flex items-center gap-1.5 text-sm font-medium cursor-pointer ${
                    formData.role_dwh === 'admin_client' ? 'text-purple-700 dark:text-purple-300' : 'text-gray-700 dark:text-gray-300'
                  }`}>
                    <Smartphone className="w-4 h-4" />
                    Accès application mobile
                  </label>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                    {formData.role_dwh === 'admin_client'
                      ? 'Toujours activé pour les administrateurs'
                      : "Autoriser la connexion depuis l'application mobile"}
                  </p>
                </div>
              </div>

              {/* ── Section Restrictions avancées ── */}
              <div className="border border-gray-200 dark:border-gray-600 rounded-lg overflow-hidden">
                <button
                  type="button"
                  onClick={() => setShowRestrictions(v => !v)}
                  className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 dark:bg-gray-700/50 hover:bg-gray-100 dark:hover:bg-gray-700 text-sm font-medium text-gray-700 dark:text-gray-300"
                >
                  <span className="flex items-center gap-2">
                    <Shield className="w-4 h-4 text-gray-400" />
                    Restrictions avancées
                    {(formData.ip_autorises || formData.pc_autorises || formData.heure_debut !== '' || formData.jours_autorises) && (
                      <span className="px-1.5 py-0.5 text-xs rounded-full bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300">
                        Actives
                      </span>
                    )}
                  </span>
                  {showRestrictions ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>

                {showRestrictions && (
                  <div className="p-4 space-y-4 bg-white dark:bg-gray-800">

                    {/* IPs autorisées */}
                    <div>
                      <label className="flex items-center gap-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        <MapPin className="w-3.5 h-3.5 text-orange-500" />
                        Adresses IP autorisées
                      </label>
                      <input
                        value={formData.ip_autorises}
                        onChange={e => set('ip_autorises', e.target.value)}
                        className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                        placeholder="ex: 192.168.1.10, 10.0.0.0"
                      />
                      <p className="text-xs text-gray-400 mt-1">Séparer par des virgules. Laisser vide = toutes les IP</p>
                    </div>

                    {/* Postes autorisés */}
                    <div>
                      <label className="flex items-center gap-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        <Monitor className="w-3.5 h-3.5 text-blue-500" />
                        Postes autorisés
                      </label>
                      <input
                        value={formData.pc_autorises}
                        onChange={e => set('pc_autorises', e.target.value)}
                        className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                        placeholder="ex: DESKTOP-ABC, LAPTOP-FARID"
                      />
                      <p className="text-xs text-gray-400 mt-1">Noms de machines (envoyés par l'app desktop)</p>
                    </div>

                    {/* Plage horaire */}
                    <div>
                      <label className="flex items-center gap-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        <Clock className="w-3.5 h-3.5 text-purple-500" />
                        Plage horaire autorisée
                      </label>
                      <div className="flex items-center gap-3">
                        <div className="flex-1">
                          <label className="text-xs text-gray-500 dark:text-gray-400 mb-1 block">De</label>
                          <select
                            value={formData.heure_debut}
                            onChange={e => set('heure_debut', e.target.value)}
                            className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                          >
                            <option value="">-- Aucune --</option>
                            {HEURES.map(h => (
                              <option key={h} value={h}>{String(h).padStart(2, '0')}:00</option>
                            ))}
                          </select>
                        </div>
                        <span className="text-gray-400 mt-5">–</span>
                        <div className="flex-1">
                          <label className="text-xs text-gray-500 dark:text-gray-400 mb-1 block">À</label>
                          <select
                            value={formData.heure_fin}
                            onChange={e => set('heure_fin', e.target.value)}
                            className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                          >
                            <option value="">-- Aucune --</option>
                            {HEURES.map(h => (
                              <option key={h} value={h}>{String(h).padStart(2, '0')}:00</option>
                            ))}
                          </select>
                        </div>
                      </div>
                      <p className="text-xs text-gray-400 mt-1">Laisser vide = pas de restriction horaire</p>
                    </div>

                    {/* Jours autorisés */}
                    <div>
                      <label className="flex items-center gap-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        <Calendar className="w-3.5 h-3.5 text-teal-500" />
                        Jours autorisés
                      </label>
                      <div className="flex gap-1.5 flex-wrap">
                        {JOURS.map(j => (
                          <button
                            key={j.val}
                            type="button"
                            onClick={() => toggleJour(j.val)}
                            className={`w-9 h-9 rounded-lg text-xs font-semibold border transition-colors ${
                              hasJour(j.val)
                                ? 'bg-primary-600 border-primary-600 text-white'
                                : 'bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:border-primary-400'
                            }`}
                          >
                            {j.label}
                          </button>
                        ))}
                        {formData.jours_autorises && (
                          <button
                            type="button"
                            onClick={() => set('jours_autorises', '')}
                            className="px-2 h-9 rounded-lg text-xs border border-gray-300 dark:border-gray-600 text-gray-400 hover:text-red-500 hover:border-red-300"
                            title="Effacer"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                      <p className="text-xs text-gray-400 mt-1">Aucun jour coché = tous les jours autorisés</p>
                    </div>

                  </div>
                )}
              </div>

              {/* Boutons */}
              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={closeModal}
                  className="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 text-sm hover:bg-gray-50 dark:hover:bg-gray-700"
                >
                  Annuler
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="px-4 py-2 rounded-lg text-white text-sm font-medium disabled:opacity-60"
                  style={{ backgroundColor: 'var(--color-primary-600)' }}
                >
                  {saving ? 'Enregistrement...' : editUser ? 'Enregistrer' : 'Créer'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
