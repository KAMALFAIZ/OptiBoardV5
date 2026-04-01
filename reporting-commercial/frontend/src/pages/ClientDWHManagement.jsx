import { useState, useEffect, useRef } from 'react'
import {
  Database, Server, Mail, Shield, Plus, Trash2, RefreshCw,
  Eye, EyeOff, CheckCircle, XCircle, AlertTriangle, Send, Pencil, Bot,
} from 'lucide-react'
import {
  getClientDwhInfo, getClientDwhSources, createClientDwhSource, updateClientDwhSource, deleteClientDwhSource,
  getClientSmtp, saveClientSmtp, testClientSmtp, getClientLicense,
} from '../services/api'
import { getAgents } from '../services/etlApi'

const TABS = [
  { id: 'dwh', label: 'Mon DWH', icon: Database },
  { id: 'smtp', label: 'Email (SMTP)', icon: Mail },
  { id: 'license', label: 'Ma Licence', icon: Shield },
]

const PLAN_STYLES = {
  trial:      { label: 'Trial',      bg: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300' },
  standard:   { label: 'Standard',   bg: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300' },
  premium:    { label: 'Premium',    bg: 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300' },
  enterprise: { label: 'Enterprise', bg: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300' },
}

// ── Onglet 1 : Mon DWH ────────────────────────────────────────────────────────
function DwhTab() {
  const [dwhInfo, setDwhInfo] = useState(null)
  const [sources, setSources] = useState([])
  const [agents, setAgents] = useState([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editSource, setEditSource] = useState(null) // null = création, objet = édition
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [toast, setToast] = useState(null)

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3000)
  }
  const [form, setForm] = useState({
    code_societe: '', nom_societe: '', serveur_sage: '', base_sage: '',
    user_sage: '', password_sage: '', etl_enabled: true,
    etl_mode: 'incremental', etl_schedule: '*/15 * * * *',
  })

  const load = async () => {
    setLoading(true)
    try {
      const [infoRes, srcRes, agentsRes] = await Promise.all([
        getClientDwhInfo(),
        getClientDwhSources(),
        getAgents().catch(() => ({ data: { agents: [] } })),
      ])
      setDwhInfo(infoRes.data?.data || null)
      setSources(srcRes.data?.data || [])
      setAgents(agentsRes.data?.data || [])
    } catch (e) {
      setError(e.response?.data?.detail || 'Erreur de chargement')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const EMPTY_FORM = { code_societe: '', nom_societe: '', serveur_sage: '', base_sage: '',
    user_sage: '', password_sage: '', etl_enabled: true, etl_mode: 'incremental', etl_schedule: '*/15 * * * *' }

  const openAdd = () => { setEditSource(null); setForm(EMPTY_FORM); setError(''); setShowModal(true) }
  const openEdit = (s) => {
    setEditSource(s)
    setForm({ code_societe: s.code_societe, nom_societe: s.nom_societe,
      serveur_sage: s.serveur_sage || '', base_sage: s.base_sage || '',
      user_sage: s.user_sage || '', password_sage: '',
      etl_enabled: !!s.etl_enabled, etl_mode: s.etl_mode || 'incremental',
      etl_schedule: s.etl_schedule || '*/15 * * * *' })
    setError(''); setShowModal(true)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      if (editSource) {
        await updateClientDwhSource(editSource.code_societe, form)
        showToast(`Source "${editSource.code_societe}" modifiée avec succès`)
      } else {
        await createClientDwhSource(form)
        showToast(`Source "${form.code_societe}" ajoutée avec succès`)
      }
      setShowModal(false)
      setEditSource(null)
      setForm(EMPTY_FORM)
      await load()
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || (editSource ? 'Erreur lors de la modification' : 'Erreur lors de l\'ajout')
      setError(msg)
      showToast(msg, 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (code) => {
    if (!confirm(`Supprimer la source "${code}" ?`)) return
    try {
      await deleteClientDwhSource(code)
      showToast(`Source "${code}" supprimée`)
      await load()
    } catch (e) {
      const msg = e.response?.data?.detail || 'Erreur lors de la suppression'
      setError(msg)
      showToast(msg, 'error')
    }
  }

  // Retrouver l'agent lié à une source (matching par sage_database == base_sage)
  const getLinkedAgent = (source) =>
    agents.find(a => a.sage_database && source.base_sage &&
      a.sage_database.toLowerCase() === source.base_sage.toLowerCase()) || null

  const agentStatusBadge = (agent) => {
    const h = agent.health_status || agent.statut || ''
    const map = {
      'En ligne':        { cls: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',     label: 'En ligne'     },
      'actif':           { cls: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',     label: 'En ligne'     },
      'Hors ligne':      { cls: 'bg-gray-100  text-gray-600  dark:bg-gray-700  dark:text-gray-400',      label: 'Hors ligne'   },
      'Erreur':          { cls: 'bg-red-100   text-red-700   dark:bg-red-900   dark:text-red-300',       label: 'Erreur'       },
      'erreur':          { cls: 'bg-red-100   text-red-700   dark:bg-red-900   dark:text-red-300',       label: 'Erreur'       },
      'Desactive':       { cls: 'bg-gray-100  text-gray-500  dark:bg-gray-700  dark:text-gray-400',      label: 'Désactivé'    },
      'Inactif':         { cls: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300', label: 'Inactif'      },
      'Jamais connecte': { cls: 'bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300', label: 'Jamais conn.' },
    }
    const style = map[h] || { cls: 'bg-gray-100 text-gray-500', label: h || 'Inconnu' }
    return <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${style.cls}`}>{style.label}</span>
  }

  if (loading) return (
    <div className="flex justify-center py-12">
      <RefreshCw className="w-6 h-6 animate-spin text-primary-500" />
    </div>
  )

  return (
    <div className="space-y-6">
      {/* Toast notification */}
      {toast && (
        <div className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-xl shadow-lg text-sm font-medium text-white transition-all ${
          toast.type === 'error' ? 'bg-red-600' : 'bg-green-600'
        }`}>
          {toast.msg}
        </div>
      )}

      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3 text-red-700 dark:text-red-300 text-sm">
          {error}
        </div>
      )}

      {/* Infos DWH */}
      {dwhInfo && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-primary-50 dark:bg-primary-900/20 rounded-lg">
              <Database className="w-5 h-5 text-primary-600 dark:text-primary-400" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 dark:text-white">{dwhInfo.nom}</h3>
              {dwhInfo.raison_sociale && (
                <p className="text-sm text-gray-500 dark:text-gray-400">{dwhInfo.raison_sociale}</p>
              )}
            </div>
            <span className={`ml-auto text-xs px-2 py-1 rounded-full font-medium ${
              dwhInfo.actif
                ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
                : 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
            }`}>
              {dwhInfo.actif ? 'Actif' : 'Inactif'}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm">
            {dwhInfo.adresse && (
              <div>
                <span className="text-gray-500 dark:text-gray-400">Adresse :</span>{' '}
                <span className="text-gray-800 dark:text-gray-200">{dwhInfo.adresse}</span>
              </div>
            )}
            {dwhInfo.ville && (
              <div>
                <span className="text-gray-500 dark:text-gray-400">Ville :</span>{' '}
                <span className="text-gray-800 dark:text-gray-200">{dwhInfo.ville}</span>
              </div>
            )}
            {dwhInfo.email && (
              <div>
                <span className="text-gray-500 dark:text-gray-400">Email :</span>{' '}
                <span className="text-gray-800 dark:text-gray-200">{dwhInfo.email}</span>
              </div>
            )}
            {dwhInfo.telephone && (
              <div>
                <span className="text-gray-500 dark:text-gray-400">Tél :</span>{' '}
                <span className="text-gray-800 dark:text-gray-200">{dwhInfo.telephone}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Sources Sage */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <Server className="w-4 h-4 text-gray-500" />
            Sources Sage ({sources.length})
          </h3>
          <button
            onClick={openAdd}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-primary-600 hover:bg-primary-700 text-white text-sm rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" />
            Ajouter source
          </button>
        </div>
        {sources.length === 0 ? (
          <div className="text-center py-8 text-gray-400 dark:text-gray-500 text-sm">
            Aucune source configurée
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 dark:text-gray-400 border-b border-gray-100 dark:border-gray-700">
                  <th className="px-4 py-2 font-medium">Code</th>
                  <th className="px-4 py-2 font-medium">Nom société</th>
                  <th className="px-4 py-2 font-medium">Serveur Sage</th>
                  <th className="px-4 py-2 font-medium">Base</th>
                  <th className="px-4 py-2 font-medium">ETL</th>
                  <th className="px-4 py-2 font-medium">Agent lié</th>
                  <th className="px-4 py-2 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {sources.map((s) => (
                  <tr key={s.code_societe} className="border-b border-gray-50 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/30">
                    <td className="px-4 py-2 font-mono font-medium text-gray-800 dark:text-gray-200">{s.code_societe}</td>
                    <td className="px-4 py-2 text-gray-700 dark:text-gray-300">{s.nom_societe}</td>
                    <td className="px-4 py-2 text-gray-600 dark:text-gray-400">{s.serveur_sage}</td>
                    <td className="px-4 py-2 text-gray-600 dark:text-gray-400">{s.base_sage}</td>
                    <td className="px-4 py-2">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        s.etl_enabled
                          ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
                          : 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400'
                      }`}>
                        {s.etl_enabled ? 'Actif' : 'Désactivé'}
                      </span>
                    </td>
                    <td className="px-4 py-2">
                      {(() => {
                        const agent = getLinkedAgent(s)
                        if (!agent) return (
                          <span className="text-xs text-gray-400 dark:text-gray-500 italic flex items-center gap-1">
                            <Bot className="w-3.5 h-3.5" /> Aucun
                          </span>
                        )
                        return (
                          <div className="flex items-center gap-1.5">
                            <Bot className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
                            <span className="text-xs text-gray-700 dark:text-gray-300 font-medium truncate max-w-[100px]" title={agent.name}>
                              {agent.name}
                            </span>
                            {agentStatusBadge(agent)}
                          </div>
                        )
                      })()}
                    </td>
                    <td className="px-4 py-2">
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => openEdit(s)}
                          className="p-1.5 text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded transition-colors"
                          title="Modifier"
                        >
                          <Pencil className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(s.code_societe)}
                          className="p-1.5 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors"
                          title="Supprimer"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal ajout / modification source */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-lg mx-4">
            <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
              <h3 className="font-semibold text-gray-900 dark:text-white">
                {editSource ? `Modifier la source "${editSource.code_societe}"` : 'Ajouter une source Sage'}
              </h3>
              <button onClick={() => { setShowModal(false); setEditSource(null) }} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">✕</button>
            </div>
            <form onSubmit={handleSubmit} className="p-4 space-y-3">
              {error && (
                <div className="bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 text-sm p-2 rounded">
                  {error}
                </div>
              )}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Code société *</label>
                  <input
                    required value={form.code_societe}
                    onChange={e => !editSource && setForm(f => ({ ...f, code_societe: e.target.value }))}
                    readOnly={!!editSource}
                    className={`w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white ${editSource ? 'bg-gray-100 dark:bg-gray-600 cursor-not-allowed' : 'bg-white dark:bg-gray-700'}`}
                    placeholder="EX: ALBA01"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Nom société *</label>
                  <input
                    required value={form.nom_societe}
                    onChange={e => setForm(f => ({ ...f, nom_societe: e.target.value }))}
                    className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                    Serveur Sage
                    <span className="ml-1 text-gray-400 font-normal">(par défaut : .)</span>
                  </label>
                  <input
                    value={form.serveur_sage}
                    onChange={e => setForm(f => ({ ...f, serveur_sage: e.target.value }))}
                    placeholder="Ex: . (local) ou SERVEUR\INSTANCE"
                    className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Base Sage *</label>
                  <input
                    required value={form.base_sage}
                    onChange={e => setForm(f => ({ ...f, base_sage: e.target.value }))}
                    className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Utilisateur Sage</label>
                  <input
                    value={form.user_sage}
                    onChange={e => setForm(f => ({ ...f, user_sage: e.target.value }))}
                    className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Mot de passe Sage</label>
                  <input
                    type="password" value={form.password_sage}
                    onChange={e => setForm(f => ({ ...f, password_sage: e.target.value }))}
                    className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                </div>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox" id="etl_enabled" checked={form.etl_enabled}
                  onChange={e => setForm(f => ({ ...f, etl_enabled: e.target.checked }))}
                  className="rounded"
                />
                <label htmlFor="etl_enabled" className="text-sm text-gray-700 dark:text-gray-300">ETL activé</label>
              </div>
              <div className="flex justify-end gap-2 pt-2 border-t border-gray-200 dark:border-gray-700">
                <button type="button" onClick={() => setShowModal(false)}
                  className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg">
                  Annuler
                </button>
                <button type="submit" disabled={saving}
                  className="px-4 py-2 text-sm bg-primary-600 hover:bg-primary-700 text-white rounded-lg disabled:opacity-50 flex items-center gap-2">
                  {saving && <RefreshCw className="w-3 h-3 animate-spin" />}
                  {editSource ? 'Enregistrer' : 'Ajouter'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Onglet 2 : SMTP ──────────────────────────────────────────────────────────
function SmtpTab() {
  const [form, setForm] = useState({
    smtp_server: '', smtp_port: 587, smtp_username: '', smtp_password: '',
    from_email: '', from_name: '', use_tls: true,
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [showPwd, setShowPwd] = useState(false)
  const [testEmail, setTestEmail] = useState('')
  const [showTestModal, setShowTestModal] = useState(false)
  const [message, setMessage] = useState({ type: '', text: '' })

  useEffect(() => {
    getClientSmtp().then(res => {
      if (res.data?.data) setForm(f => ({ ...f, ...res.data.data }))
    }).catch(() => {}).finally(() => setLoading(false))
  }, [])

  const handleSave = async (e) => {
    e.preventDefault()
    setSaving(true)
    setMessage({ type: '', text: '' })
    try {
      await saveClientSmtp(form)
      setMessage({ type: 'success', text: 'Configuration SMTP sauvegardée avec succès' })
    } catch (e) {
      setMessage({ type: 'error', text: e.response?.data?.detail || 'Erreur lors de la sauvegarde' })
    } finally {
      setSaving(false)
    }
  }

  const handleTest = async () => {
    if (!testEmail) return
    setTesting(true)
    setMessage({ type: '', text: '' })
    try {
      await testClientSmtp(testEmail)
      setMessage({ type: 'success', text: `Email de test envoyé à ${testEmail}` })
      setShowTestModal(false)
      setTestEmail('')
    } catch (e) {
      setMessage({ type: 'error', text: e.response?.data?.detail || 'Erreur d\'envoi' })
    } finally {
      setTesting(false)
    }
  }

  if (loading) return (
    <div className="flex justify-center py-12">
      <RefreshCw className="w-6 h-6 animate-spin text-primary-500" />
    </div>
  )

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
      {message.text && (
        <div className={`mb-4 p-3 rounded-lg text-sm flex items-center gap-2 ${
          message.type === 'success'
            ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300'
            : 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300'
        }`}>
          {message.type === 'success' ? <CheckCircle className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
          {message.text}
        </div>
      )}
      <form onSubmit={handleSave} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Serveur SMTP *</label>
            <input required value={form.smtp_server}
              onChange={e => setForm(f => ({ ...f, smtp_server: e.target.value }))}
              placeholder="smtp.gmail.com"
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Port</label>
            <input type="number" value={form.smtp_port}
              onChange={e => setForm(f => ({ ...f, smtp_port: parseInt(e.target.value) || 587 }))}
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Utilisateur</label>
            <input value={form.smtp_username}
              onChange={e => setForm(f => ({ ...f, smtp_username: e.target.value }))}
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Mot de passe</label>
            <div className="relative">
              <input type={showPwd ? 'text' : 'password'} value={form.smtp_password}
                onChange={e => setForm(f => ({ ...f, smtp_password: e.target.value }))}
                className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white pr-9"
              />
              <button type="button" onClick={() => setShowPwd(s => !s)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                {showPwd ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Email expéditeur *</label>
            <input required type="email" value={form.from_email}
              onChange={e => setForm(f => ({ ...f, from_email: e.target.value }))}
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Nom expéditeur</label>
            <input value={form.from_name}
              onChange={e => setForm(f => ({ ...f, from_name: e.target.value }))}
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
          </div>
        </div>
        <div className="flex items-center gap-2">
          <input type="checkbox" id="use_tls" checked={form.use_tls}
            onChange={e => setForm(f => ({ ...f, use_tls: e.target.checked }))}
            className="rounded"
          />
          <label htmlFor="use_tls" className="text-sm text-gray-700 dark:text-gray-300">Utiliser TLS (STARTTLS)</label>
        </div>
        <div className="flex justify-between items-center pt-2 border-t border-gray-200 dark:border-gray-700">
          <button type="button" onClick={() => setShowTestModal(true)}
            className="flex items-center gap-1.5 px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 rounded-lg transition-colors">
            <Send className="w-4 h-4" />
            Envoyer email test
          </button>
          <button type="submit" disabled={saving}
            className="flex items-center gap-1.5 px-4 py-2 text-sm bg-primary-600 hover:bg-primary-700 text-white rounded-lg disabled:opacity-50 transition-colors">
            {saving && <RefreshCw className="w-3 h-3 animate-spin" />}
            Enregistrer
          </button>
        </div>
      </form>

      {/* Modal test email */}
      {showTestModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-sm mx-4 p-5">
            <h3 className="font-semibold text-gray-900 dark:text-white mb-3">Email de test</h3>
            <input type="email" value={testEmail}
              onChange={e => setTestEmail(e.target.value)}
              placeholder="destinataire@example.com"
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white mb-3"
              onKeyDown={e => e.key === 'Enter' && handleTest()}
            />
            <div className="flex justify-end gap-2">
              <button onClick={() => setShowTestModal(false)}
                className="px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg">
                Annuler
              </button>
              <button onClick={handleTest} disabled={testing || !testEmail}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-primary-600 hover:bg-primary-700 text-white rounded-lg disabled:opacity-50">
                {testing && <RefreshCw className="w-3 h-3 animate-spin" />}
                Envoyer
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Onglet 3 : Licence ───────────────────────────────────────────────────────
function LicenseTab() {
  const [license, setLicense] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    getClientLicense()
      .then(res => setLicense(res.data?.data || null))
      .catch(e => setError(e.response?.data?.detail || 'Erreur de chargement'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <div className="flex justify-center py-12">
      <RefreshCw className="w-6 h-6 animate-spin text-primary-500" />
    </div>
  )

  if (error) return (
    <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 text-red-700 dark:text-red-300 text-sm">
      {error}
    </div>
  )

  if (!license) return (
    <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-xl p-6 flex items-start gap-3">
      <AlertTriangle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 mt-0.5 flex-shrink-0" />
      <div>
        <p className="font-medium text-yellow-800 dark:text-yellow-300">Aucune licence assignée</p>
        <p className="text-sm text-yellow-700 dark:text-yellow-400 mt-1">
          Aucune licence n'est associée à votre espace client. Contactez votre administrateur pour l'activation.
        </p>
      </div>
    </div>
  )

  const planStyle = PLAN_STYLES[license.plan] || PLAN_STYLES.standard
  const daysRemaining = license.days_remaining ?? null
  const isExpiringSoon = daysRemaining !== null && daysRemaining <= 30 && daysRemaining > 0
  const isExpired = license.status === 'expired' || (daysRemaining !== null && daysRemaining <= 0)

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{license.organization_name}</h3>
            {!license.is_client_specific && (
              <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">Licence globale (partagée)</p>
            )}
          </div>
          <span className={`px-3 py-1 rounded-full text-sm font-semibold ${planStyle.bg}`}>
            {planStyle.label}
          </span>
        </div>

        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-500 dark:text-gray-400 block mb-0.5">Statut</span>
            <span className={`font-medium ${
              isExpired ? 'text-red-600 dark:text-red-400' :
              license.status === 'valid' ? 'text-green-600 dark:text-green-400' :
              'text-gray-600 dark:text-gray-400'
            }`}>
              {isExpired ? 'Expirée' : license.status === 'valid' ? 'Valide' : license.status}
            </span>
          </div>
          <div>
            <span className="text-gray-500 dark:text-gray-400 block mb-0.5">Expiration</span>
            <span className="font-medium text-gray-800 dark:text-gray-200">
              {license.expiry_date
                ? new Date(license.expiry_date).toLocaleDateString('fr-FR')
                : '—'}
            </span>
          </div>
          <div>
            <span className="text-gray-500 dark:text-gray-400 block mb-0.5">Jours restants</span>
            <span className={`font-medium ${
              isExpired ? 'text-red-600 dark:text-red-400' :
              isExpiringSoon ? 'text-orange-600 dark:text-orange-400' :
              'text-gray-800 dark:text-gray-200'
            }`}>
              {daysRemaining !== null ? `${daysRemaining} j` : '—'}
              {isExpiringSoon && ' ⚠️'}
            </span>
          </div>
          <div>
            <span className="text-gray-500 dark:text-gray-400 block mb-0.5">Utilisateurs max</span>
            <span className="font-medium text-gray-800 dark:text-gray-200">
              {license.max_users === 0 ? 'Illimité' : license.max_users}
            </span>
          </div>
        </div>
      </div>

      {/* Features */}
      {Array.isArray(license.features) && license.features.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
          <h4 className="font-medium text-gray-900 dark:text-white mb-3">Fonctionnalités incluses</h4>
          <div className="flex flex-wrap gap-2">
            {license.features.includes('all') ? (
              <span className="px-3 py-1 bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300 rounded-full text-xs font-medium">
                ✓ Toutes les fonctionnalités
              </span>
            ) : (
              license.features.map(f => (
                <span key={f} className="px-3 py-1 bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300 rounded-full text-xs font-medium border border-green-200 dark:border-green-800">
                  ✓ {f}
                </span>
              ))
            )}
          </div>
        </div>
      )}

      {/* Alerte expiration */}
      {isExpiringSoon && (
        <div className="bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg p-3 flex items-center gap-2 text-orange-700 dark:text-orange-300 text-sm">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          Votre licence expire dans {daysRemaining} jours. Contactez votre administrateur pour le renouvellement.
        </div>
      )}
    </div>
  )
}

// ── Page principale ───────────────────────────────────────────────────────────
export default function ClientDWHManagement() {
  const [activeTab, setActiveTab] = useState('dwh')
  const [dwhList, setDwhList]     = useState([])
  const [selectedDwh, setSelectedDwh] = useState(() => {
    try { return JSON.parse(localStorage.getItem('currentDWH') || 'null') } catch { return null }
  })

  // Charger la liste DWH si superadmin (pas de currentDWH dans localStorage)
  useEffect(() => {
    if (!localStorage.getItem('currentDWH')) {
      import('../services/api').then(({ default: api }) => {
        api.get('/auth/dwh-list').then(res => {
          const list = res.data || []
          setDwhList(list)
          if (list.length > 0 && !selectedDwh) setSelectedDwh(list[0])
        }).catch(() => {})
      })
    }
  }, [])

  // Quand l'admin choisit un DWH → l'écrire temporairement dans localStorage
  const handleSelectDwh = (dwh) => {
    setSelectedDwh(dwh)
    localStorage.setItem('currentDWH', JSON.stringify(dwh))
    window.location.reload()
  }

  const clientName = selectedDwh?.nom || selectedDwh?.code || ''
  const isSuperAdminNoClient = !localStorage.getItem('currentDWH') && dwhList.length > 0

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary-50 dark:bg-primary-900/20 rounded-lg">
              <Database className="w-5 h-5 text-primary-600 dark:text-primary-400" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900 dark:text-white">Mon Espace Client</h1>
              {clientName && (
                <p className="text-sm text-gray-500 dark:text-gray-400">{clientName}</p>
              )}
            </div>
          </div>
          {/* Sélecteur DWH pour superadmin */}
          {dwhList.length > 1 && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500">Client :</span>
              <select
                value={selectedDwh?.code || ''}
                onChange={e => handleSelectDwh(dwhList.find(d => d.code === e.target.value))}
                className="text-sm px-3 py-1.5 border border-blue-300 dark:border-blue-600 rounded-lg bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 font-medium cursor-pointer"
              >
                {dwhList.map(d => (
                  <option key={d.code} value={d.code}>{d.nom || d.code}</option>
                ))}
              </select>
            </div>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-6">
        <div className="flex gap-0">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === id
                  ? 'border-primary-500 text-primary-600 dark:text-primary-400'
                  : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
              }`}
            >
              <Icon className="w-4 h-4" />
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Contenu */}
      <div className="flex-1 overflow-y-auto p-6">
        {activeTab === 'dwh'     && <DwhTab />}
        {activeTab === 'smtp'    && <SmtpTab />}
        {activeTab === 'license' && <LicenseTab />}
      </div>
    </div>
  )
}
