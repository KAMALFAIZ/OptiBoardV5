import { useState, useEffect, useCallback } from 'react'
import {
  Bell, Mail, MessageSquare, Send, Users, CheckCircle2, XCircle,
  ToggleLeft, ToggleRight, Trash2, Calendar, RefreshCw, Play,
  ChevronLeft, ChevronRight, Search, Filter, Clock, Activity,
  TrendingUp, AlertTriangle, Zap, Edit2, X, Save
} from 'lucide-react'
import api from '../services/api'

// ─── Constantes ───────────────────────────────────────────────────────────────

const CHANNEL_CFG = {
  email:    { icon: '✉️', label: 'Email',    color: 'text-blue-500',   bg: 'bg-blue-50 dark:bg-blue-900/20' },
  telegram: { icon: '✈️', label: 'Telegram', color: 'text-sky-500',    bg: 'bg-sky-50 dark:bg-sky-900/20' },
  whatsapp: { icon: '💬', label: 'WhatsApp', color: 'text-green-500',  bg: 'bg-green-50 dark:bg-green-900/20' },
}
const FREQ_LABEL  = { daily: 'Quotidien', weekly: 'Hebdomadaire', monthly: 'Mensuel' }
const DAYS_FR     = ['Lun','Mar','Mer','Jeu','Ven','Sam','Dim']
const HOURS       = [6,7,8,9,10,11,12,14,16,18,20]
const FORMATS     = [{ key:'excel', label:'Excel' }, { key:'pdf', label:'PDF' }]
const CHANNELS_OPT = [{ key:'email', label:'✉️ Email' }, { key:'whatsapp', label:'💬 WhatsApp' }, { key:'telegram', label:'✈️ Telegram' }]

function fmt(dt) {
  if (!dt) return '—'
  return new Date(dt).toLocaleString('fr-FR', { day:'2-digit', month:'2-digit', year:'numeric', hour:'2-digit', minute:'2-digit' })
}
function fmtDate(dt) {
  if (!dt) return '—'
  return new Date(dt).toLocaleDateString('fr-FR')
}

// ─── Composant principal ───────────────────────────────────────────────────────

export default function AdminSubscriptionsPage() {
  const [tab, setTab] = useState('overview')

  // Stats
  const [stats, setStats] = useState(null)
  const [statsLoading, setStatsLoading] = useState(true)

  // Abonnements
  const [subs, setSubs] = useState([])
  const [subsLoading, setSubsLoading] = useState(false)
  const [subsTotal, setSubsTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState({ channel: '', frequency: '', is_active: '', search: '' })

  // Logs
  const [logs, setLogs] = useState([])
  const [logsLoading, setLogsLoading] = useState(false)
  const [logsTotal, setLogsTotal] = useState(0)
  const [logsPage, setLogsPage] = useState(1)
  const [logsFilters, setLogsFilters] = useState({ channel: '', status: '', days: 7 })
  const [logsSummary, setLogsSummary] = useState([])

  // UI
  const [flash, setFlash] = useState(null)
  const [delivering, setDelivering] = useState({})
  const [rescheduling, setRescheduling] = useState(null)
  const [rescheduleVal, setRescheduleVal] = useState('')
  const [editSub, setEditSub] = useState(null)   // sub en cours d'édition

  useEffect(() => { loadStats() }, [])
  useEffect(() => { if (tab === 'subs') loadSubs() }, [tab, page, filters])
  useEffect(() => { if (tab === 'logs') { loadLogs(); loadLogsSummary() } }, [tab, logsPage, logsFilters])

  async function loadStats() {
    setStatsLoading(true)
    try {
      const r = await api.get('/admin/subscriptions/stats')
      if (r.data?.success) setStats(r.data.data)
    } catch {} finally { setStatsLoading(false) }
  }

  async function loadSubs() {
    setSubsLoading(true)
    try {
      const r = await api.get('/admin/subscriptions', {
        params: { page, page_size: 20, ...filters, is_active: filters.is_active === '' ? undefined : filters.is_active }
      })
      if (r.data?.success) { setSubs(r.data.data); setSubsTotal(r.data.total) }
    } catch {} finally { setSubsLoading(false) }
  }

  async function loadLogs() {
    setLogsLoading(true)
    try {
      const r = await api.get('/admin/subscriptions/logs', {
        params: { page: logsPage, page_size: 30, ...logsFilters }
      })
      if (r.data?.success) { setLogs(r.data.data); setLogsTotal(r.data.total) }
    } catch {} finally { setLogsLoading(false) }
  }

  async function loadLogsSummary() {
    try {
      const r = await api.get('/admin/subscriptions/logs/summary', { params: { days: 30 } })
      if (r.data?.success) setLogsSummary(r.data.data)
    } catch {}
  }

  function showFlash(type, msg) {
    setFlash({ type, msg })
    setTimeout(() => setFlash(null), 4000)
  }

  async function deliverNow(subId) {
    setDelivering(p => ({ ...p, [subId]: true }))
    try {
      const r = await api.post(`/admin/subscriptions/${subId}/deliver-now`)
      if (r.data?.success) showFlash('success', r.data.message)
      else showFlash('error', r.data?.error || 'Erreur')
    } catch { showFlash('error', 'Erreur réseau') } finally {
      setDelivering(p => ({ ...p, [subId]: false }))
    }
  }

  async function deliverAll() {
    try {
      const r = await api.post('/admin/subscriptions/deliver-all')
      if (r.data?.success) showFlash('success', r.data.message)
    } catch { showFlash('error', 'Erreur réseau') }
  }

  async function toggleSub(id) {
    try {
      await api.put(`/admin/subscriptions/${id}/toggle`)
      setSubs(prev => prev.map(s => s.id === id ? { ...s, is_active: s.is_active ? 0 : 1 } : s))
    } catch { showFlash('error', 'Erreur toggle') }
  }

  async function deleteSub(id, nom) {
    if (!confirm(`Supprimer l'abonnement "${nom}" ?`)) return
    try {
      await api.delete(`/admin/subscriptions/${id}`)
      setSubs(prev => prev.filter(s => s.id !== id))
      setSubsTotal(p => p - 1)
      showFlash('success', 'Abonnement supprimé')
    } catch { showFlash('error', 'Erreur suppression') }
  }

  async function confirmReschedule(id) {
    if (!rescheduleVal) return
    try {
      const r = await api.put(`/admin/subscriptions/${id}/reschedule`, { next_send: rescheduleVal })
      if (r.data?.success) {
        setSubs(prev => prev.map(s => s.id === id ? { ...s, next_send: rescheduleVal } : s))
        showFlash('success', `Reprogrammé → ${r.data.next_send}`)
        setRescheduling(null)
      }
    } catch { showFlash('error', 'Erreur reprogrammation') }
  }

  async function saveSub(id, patch) {
    try {
      const r = await api.put(`/subscriptions/${id}`, patch)
      if (r.data?.success) {
        const updated = r.data.data
        if (updated) setSubs(prev => prev.map(s => s.id === id ? { ...s, ...updated } : s))
        showFlash('success', 'Abonnement mis à jour')
        setEditSub(null)
      } else {
        showFlash('error', r.data?.error || 'Erreur')
      }
    } catch { showFlash('error', 'Erreur réseau') }
  }

  const totalPages = Math.ceil(subsTotal / 20)
  const logsTotalPages = Math.ceil(logsTotal / 30)

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Bell className="w-5 h-5" style={{ color: 'var(--color-primary-600)' }} />
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">Abonnements Utilisateurs</h1>
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 ml-7">
            Abonnements créés par les utilisateurs depuis les pages de rapports · Email, WhatsApp, Telegram
          </p>
        </div>
        <button
          onClick={deliverAll}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900 font-medium hover:bg-gray-700 transition-colors"
        >
          <Zap className="w-3.5 h-3.5" />
          Livrer maintenant (tous)
        </button>
      </div>

      {/* Flash */}
      {flash && (
        <div className={`p-3 rounded-lg text-sm font-medium ${
          flash.type === 'success'
            ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300 border border-green-200 dark:border-green-800'
            : 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800'
        }`}>
          {flash.msg}
        </div>
      )}

      {/* Onglets */}
      <div className="flex gap-4 border-b border-gray-200 dark:border-gray-700">
        {[
          { key: 'overview', label: 'Vue d\'ensemble',  icon: <Activity className="w-4 h-4" /> },
          { key: 'subs',     label: 'Abonnements',      icon: <Users className="w-4 h-4" /> },
          { key: 'logs',     label: 'Historique',       icon: <Clock className="w-4 h-4" /> },
        ].map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`flex items-center gap-1.5 pb-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t.key ? 'border-primary-500 text-primary-600' : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
            style={tab === t.key ? { borderColor: 'var(--color-primary-500)', color: 'var(--color-primary-600)' } : {}}
          >
            {t.icon}{t.label}
          </button>
        ))}
      </div>

      {/* ── OVERVIEW ── */}
      {tab === 'overview' && (
        <div className="space-y-4">
          {statsLoading ? (
            <div className="flex justify-center py-12"><RefreshCw className="w-6 h-6 animate-spin text-gray-400" /></div>
          ) : stats ? (
            <>
              {/* KPI Cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <KpiCard icon={<Users className="w-5 h-5 text-indigo-500" />}
                  label="Total abonnés" value={stats.total} sub={`${stats.actifs} actifs`} color="indigo" />
                <KpiCard icon={<CheckCircle2 className="w-5 h-5 text-green-500" />}
                  label="Livrés aujourd'hui" value={stats.today_ok} sub={`${stats.total_sent} total`} color="green" />
                <KpiCard icon={<XCircle className="w-5 h-5 text-red-500" />}
                  label="Erreurs aujourd'hui" value={stats.today_err}
                  sub={stats.today_err > 0 ? 'Voir historique' : 'Tout est OK'} color="red" />
                <KpiCard icon={<Bell className="w-5 h-5 text-amber-500" />}
                  label="En pause" value={stats.pauses} sub="abonnements" color="amber" />
              </div>

              {/* Distribution par canal + fréquence */}
              <div className="grid grid-cols-2 gap-4">
                <div className="card p-4">
                  <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
                    <MessageSquare className="w-4 h-4 text-indigo-400" /> Par canal
                  </h3>
                  <div className="space-y-2">
                    {Object.entries(CHANNEL_CFG).map(([key, cfg]) => {
                      const n = stats.by_channel?.[key] || 0
                      const max = Math.max(...Object.values(stats.by_channel || {}), 1)
                      return (
                        <div key={key}>
                          <div className="flex items-center justify-between text-xs mb-1">
                            <span className="flex items-center gap-1"><span>{cfg.icon}</span>{cfg.label}</span>
                            <span className="font-semibold">{n}</span>
                          </div>
                          <div className="h-1.5 bg-gray-100 dark:bg-gray-700 rounded-full">
                            <div className="h-1.5 rounded-full transition-all" style={{
                              width: `${(n / max) * 100}%`,
                              backgroundColor: key === 'email' ? '#3b82f6' : key === 'telegram' ? '#0ea5e9' : '#22c55e'
                            }} />
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>

                <div className="card p-4">
                  <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
                    <Calendar className="w-4 h-4 text-indigo-400" /> Par fréquence
                  </h3>
                  <div className="space-y-2">
                    {Object.entries(FREQ_LABEL).map(([key, label]) => {
                      const n = stats.by_freq?.[key] || 0
                      const max = Math.max(...Object.values(stats.by_freq || {}), 1)
                      return (
                        <div key={key}>
                          <div className="flex items-center justify-between text-xs mb-1">
                            <span>{label}</span>
                            <span className="font-semibold">{n}</span>
                          </div>
                          <div className="h-1.5 bg-gray-100 dark:bg-gray-700 rounded-full">
                            <div className="h-1.5 rounded-full bg-indigo-400 transition-all" style={{ width: `${(n / max) * 100}%` }} />
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              </div>

              {/* Prochaines livraisons */}
              {stats.next_due?.length > 0 && (
                <div className="card p-4">
                  <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
                    <Clock className="w-4 h-4 text-indigo-400" /> Prochaines livraisons planifiées
                  </h3>
                  <div className="space-y-2">
                    {stats.next_due.map((s, i) => {
                      const ch = CHANNEL_CFG[s.channel || 'email'] || CHANNEL_CFG.email
                      return (
                        <div key={i} className="flex items-center gap-3 text-sm">
                          <span className="text-base">{ch.icon}</span>
                          <span className="flex-1 text-gray-700 dark:text-gray-300 truncate">{s.report_nom}</span>
                          <span className="text-xs text-gray-400 truncate">{s.user_email}</span>
                          <span className="text-xs font-mono text-indigo-500 whitespace-nowrap">{fmt(s.next_send)}</span>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}
            </>
          ) : (
            <p className="text-center text-gray-400 py-8">Impossible de charger les statistiques</p>
          )}
        </div>
      )}

      {/* ── ABONNEMENTS ── */}
      {tab === 'subs' && (
        <div className="space-y-3">
          {/* Filtres */}
          <div className="card p-3 flex flex-wrap gap-2 items-center">
            <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-gray-100 dark:bg-gray-700">
              <Search className="w-3.5 h-3.5 text-gray-400" />
              <input
                type="text"
                value={filters.search}
                onChange={e => { setFilters(p => ({ ...p, search: e.target.value })); setPage(1) }}
                placeholder="Email ou rapport…"
                className="text-xs bg-transparent outline-none text-gray-700 dark:text-gray-200 w-40"
              />
            </div>
            <select value={filters.channel} onChange={e => { setFilters(p => ({ ...p, channel: e.target.value })); setPage(1) }}
              className="text-xs rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 px-2 py-1.5">
              <option value="">Tous les canaux</option>
              <option value="email">✉️ Email</option>
              <option value="telegram">✈️ Telegram</option>
              <option value="whatsapp">💬 WhatsApp</option>
            </select>
            <select value={filters.frequency} onChange={e => { setFilters(p => ({ ...p, frequency: e.target.value })); setPage(1) }}
              className="text-xs rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 px-2 py-1.5">
              <option value="">Toutes fréquences</option>
              <option value="daily">Quotidien</option>
              <option value="weekly">Hebdomadaire</option>
              <option value="monthly">Mensuel</option>
            </select>
            <select value={filters.is_active} onChange={e => { setFilters(p => ({ ...p, is_active: e.target.value })); setPage(1) }}
              className="text-xs rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 px-2 py-1.5">
              <option value="">Tous statuts</option>
              <option value="1">Actifs</option>
              <option value="0">En pause</option>
            </select>
            <button onClick={loadSubs} className="ml-auto flex items-center gap-1 px-2 py-1.5 text-xs rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700">
              <RefreshCw className="w-3 h-3" /> Actualiser
            </button>
            <span className="text-xs text-gray-400">{subsTotal} résultat{subsTotal > 1 ? 's' : ''}</span>
          </div>

          {/* Table */}
          {subsLoading ? (
            <div className="flex justify-center py-8"><RefreshCw className="w-5 h-5 animate-spin text-gray-400" /></div>
          ) : (
            <div className="card overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 dark:bg-gray-700/50 text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                  <tr>
                    <th className="text-left px-4 py-2.5">Utilisateur</th>
                    <th className="text-left px-4 py-2.5">Rapport</th>
                    <th className="text-left px-3 py-2.5">Canal</th>
                    <th className="text-left px-3 py-2.5">Fréquence</th>
                    <th className="text-left px-3 py-2.5">Prochaine livraison</th>
                    <th className="text-left px-3 py-2.5">Statut</th>
                    <th className="text-right px-3 py-2.5">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                  {subs.length === 0 ? (
                    <tr><td colSpan={7} className="text-center py-8 text-gray-400">Aucun abonnement</td></tr>
                  ) : subs.map(sub => {
                    const ch = CHANNEL_CFG[sub.channel || 'email'] || CHANNEL_CFG.email
                    return (
                      <tr key={sub.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors">
                        <td className="px-4 py-3">
                          <span className="text-xs text-gray-600 dark:text-gray-300 font-mono">{sub.user_email}</span>
                        </td>
                        <td className="px-4 py-3">
                          <span className="font-medium text-gray-800 dark:text-gray-200 text-xs">{sub.report_nom}</span>
                          <span className="ml-1.5 text-[10px] text-gray-400">{sub.report_type}</span>
                        </td>
                        <td className="px-3 py-3">
                          <span className={`flex items-center gap-1 text-xs font-medium ${ch.color}`}>
                            {ch.icon} {ch.label}
                          </span>
                        </td>
                        <td className="px-3 py-3">
                          <div className="text-xs text-gray-600 dark:text-gray-300 font-medium">{FREQ_LABEL[sub.frequency] || sub.frequency}</div>
                          <div className="text-[10px] text-gray-400 mt-0.5">
                            {sub.frequency === 'daily'   && `${sub.heure_envoi ?? 7}h00`}
                            {sub.frequency === 'weekly'  && `${DAYS_FR[sub.jour_semaine ?? 0]} ${sub.heure_envoi ?? 7}h`}
                            {sub.frequency === 'monthly' && `J${sub.jour_mois ?? 1} · ${sub.heure_envoi ?? 7}h`}
                          </div>
                        </td>
                        <td className="px-3 py-3">
                          {rescheduling === sub.id ? (
                            <div className="flex items-center gap-1">
                              <input type="datetime-local" value={rescheduleVal}
                                onChange={e => setRescheduleVal(e.target.value)}
                                className="text-xs rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 px-1.5 py-0.5"
                              />
                              <button onClick={() => confirmReschedule(sub.id)}
                                className="text-green-600 hover:text-green-700 p-0.5"><CheckCircle2 className="w-3.5 h-3.5" /></button>
                              <button onClick={() => setRescheduling(null)}
                                className="text-gray-400 hover:text-gray-600 p-0.5"><XCircle className="w-3.5 h-3.5" /></button>
                            </div>
                          ) : (
                            <button
                              onClick={() => { setRescheduling(sub.id); setRescheduleVal(sub.next_send?.slice(0,16) || '') }}
                              className="text-xs text-gray-500 hover:text-indigo-500 font-mono"
                            >
                              {fmt(sub.next_send)}
                            </button>
                          )}
                        </td>
                        <td className="px-3 py-3">
                          <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${
                            sub.is_active
                              ? 'bg-green-100 dark:bg-green-900/40 text-green-600 dark:text-green-400'
                              : 'bg-gray-100 dark:bg-gray-700 text-gray-500'
                          }`}>
                            {sub.is_active ? 'Actif' : 'En pause'}
                          </span>
                        </td>
                        <td className="px-3 py-3">
                          <div className="flex items-center gap-1 justify-end">
                            <button
                              onClick={() => deliverNow(sub.id)}
                              disabled={delivering[sub.id]}
                              title="Livrer maintenant"
                              className="p-1.5 rounded hover:bg-indigo-50 dark:hover:bg-indigo-900/20 text-gray-400 hover:text-indigo-500 disabled:opacity-40 transition-colors"
                            >
                              {delivering[sub.id] ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
                            </button>
                            <button
                              onClick={() => setEditSub(sub)}
                              title="Modifier la planification"
                              className="p-1.5 rounded hover:bg-amber-50 dark:hover:bg-amber-900/20 text-gray-400 hover:text-amber-500 transition-colors"
                            >
                              <Edit2 className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => toggleSub(sub.id)}
                              title={sub.is_active ? 'Mettre en pause' : 'Réactiver'}
                              className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 hover:text-gray-600 transition-colors"
                            >
                              {sub.is_active
                                ? <ToggleRight className="w-4 h-4" style={{ color: 'var(--color-primary-500)' }} />
                                : <ToggleLeft className="w-4 h-4" />
                              }
                            </button>
                            <button
                              onClick={() => deleteSub(sub.id, sub.report_nom)}
                              title="Supprimer"
                              className="p-1.5 rounded hover:bg-red-50 dark:hover:bg-red-900/20 text-gray-400 hover:text-red-500 transition-colors"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between text-xs text-gray-500">
              <span>Page {page} / {totalPages} — {subsTotal} abonnement{subsTotal > 1 ? 's' : ''}</span>
              <div className="flex gap-1">
                <button disabled={page === 1} onClick={() => setPage(p => p - 1)}
                  className="p-1 rounded border border-gray-300 dark:border-gray-600 disabled:opacity-40 hover:bg-gray-50 dark:hover:bg-gray-700">
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}
                  className="p-1 rounded border border-gray-300 dark:border-gray-600 disabled:opacity-40 hover:bg-gray-50 dark:hover:bg-gray-700">
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── HISTORIQUE ── */}
      {tab === 'logs' && (
        <div className="space-y-3">
          {/* Mini graphique résumé */}
          {logsSummary.length > 0 && (
            <div className="card p-4">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-indigo-400" /> Livraisons — 30 derniers jours
              </h3>
              <div className="flex items-end gap-1 h-16">
                {logsSummary.map((d, i) => {
                  const maxN = Math.max(...logsSummary.map(x => x.success + x.errors), 1)
                  const total = d.success + d.errors
                  return (
                    <div key={i} className="flex-1 flex flex-col items-center gap-0.5" title={`${fmtDate(d.day)}: ${d.success} ok, ${d.errors} erreurs`}>
                      <div className="w-full flex flex-col-reverse gap-px" style={{ height: 52 }}>
                        {d.errors > 0 && (
                          <div className="w-full bg-red-400 rounded-sm" style={{ height: `${(d.errors / maxN) * 52}px` }} />
                        )}
                        {d.success > 0 && (
                          <div className="w-full bg-green-400 rounded-sm" style={{ height: `${(d.success / maxN) * 52}px` }} />
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
              <div className="flex gap-3 mt-2 text-[10px] text-gray-400">
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-green-400 inline-block" /> Succès</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-red-400 inline-block" /> Erreurs</span>
              </div>
            </div>
          )}

          {/* Filtres logs */}
          <div className="card p-3 flex flex-wrap gap-2 items-center">
            <select value={logsFilters.days} onChange={e => { setLogsFilters(p => ({ ...p, days: +e.target.value })); setLogsPage(1) }}
              className="text-xs rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 px-2 py-1.5">
              <option value={1}>Aujourd'hui</option>
              <option value={7}>7 derniers jours</option>
              <option value={30}>30 derniers jours</option>
              <option value={90}>90 derniers jours</option>
            </select>
            <select value={logsFilters.channel} onChange={e => { setLogsFilters(p => ({ ...p, channel: e.target.value })); setLogsPage(1) }}
              className="text-xs rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 px-2 py-1.5">
              <option value="">Tous les canaux</option>
              <option value="email">✉️ Email</option>
              <option value="telegram">✈️ Telegram</option>
              <option value="whatsapp">💬 WhatsApp</option>
            </select>
            <select value={logsFilters.status} onChange={e => { setLogsFilters(p => ({ ...p, status: e.target.value })); setLogsPage(1) }}
              className="text-xs rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 px-2 py-1.5">
              <option value="">Tous statuts</option>
              <option value="success">✅ Succès</option>
              <option value="error">❌ Erreurs</option>
            </select>
            <button onClick={loadLogs} className="ml-auto flex items-center gap-1 px-2 py-1.5 text-xs rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700">
              <RefreshCw className="w-3 h-3" /> Actualiser
            </button>
            <span className="text-xs text-gray-400">{logsTotal} entrée{logsTotal > 1 ? 's' : ''}</span>
          </div>

          {/* Table logs */}
          {logsLoading ? (
            <div className="flex justify-center py-8"><RefreshCw className="w-5 h-5 animate-spin text-gray-400" /></div>
          ) : (
            <div className="card overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 dark:bg-gray-700/50 text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                  <tr>
                    <th className="text-left px-4 py-2.5">Date</th>
                    <th className="text-left px-4 py-2.5">Utilisateur</th>
                    <th className="text-left px-4 py-2.5">Rapport</th>
                    <th className="text-left px-3 py-2.5">Canal</th>
                    <th className="text-left px-3 py-2.5">Statut</th>
                    <th className="text-left px-3 py-2.5">Détail</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                  {logs.length === 0 ? (
                    <tr><td colSpan={6} className="text-center py-8 text-gray-400">Aucun log</td></tr>
                  ) : logs.map(log => {
                    const ch = CHANNEL_CFG[log.channel || 'email'] || CHANNEL_CFG.email
                    return (
                      <tr key={log.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors">
                        <td className="px-4 py-2.5 text-xs font-mono text-gray-500 whitespace-nowrap">{fmt(log.sent_at)}</td>
                        <td className="px-4 py-2.5 text-xs text-gray-600 dark:text-gray-300">{log.user_email}</td>
                        <td className="px-4 py-2.5 text-xs text-gray-700 dark:text-gray-200 max-w-[200px] truncate">{log.report_nom}</td>
                        <td className="px-3 py-2.5">
                          <span className={`text-xs font-medium ${ch.color}`}>{ch.icon} {ch.label}</span>
                        </td>
                        <td className="px-3 py-2.5">
                          <span className={`flex items-center gap-1 text-xs font-medium ${
                            log.status === 'success' ? 'text-green-600 dark:text-green-400' : 'text-red-500 dark:text-red-400'
                          }`}>
                            {log.status === 'success' ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                            {log.status === 'success' ? 'Succès' : 'Erreur'}
                          </span>
                        </td>
                        <td className="px-3 py-2.5 text-xs text-gray-400 max-w-[220px] truncate">{log.error_msg || '—'}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination logs */}
          {logsTotalPages > 1 && (
            <div className="flex items-center justify-between text-xs text-gray-500">
              <span>Page {logsPage} / {logsTotalPages}</span>
              <div className="flex gap-1">
                <button disabled={logsPage === 1} onClick={() => setLogsPage(p => p - 1)}
                  className="p-1 rounded border border-gray-300 dark:border-gray-600 disabled:opacity-40 hover:bg-gray-50 dark:hover:bg-gray-700">
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <button disabled={logsPage >= logsTotalPages} onClick={() => setLogsPage(p => p + 1)}
                  className="p-1 rounded border border-gray-300 dark:border-gray-600 disabled:opacity-40 hover:bg-gray-50 dark:hover:bg-gray-700">
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── MODAL EDIT ── */}
      {editSub && (
        <EditSubModal
          sub={editSub}
          onClose={() => setEditSub(null)}
          onSave={saveSub}
        />
      )}
    </div>
  )
}

// ─── Edit Modal ────────────────────────────────────────────────────────────────

function EditSubModal({ sub, onClose, onSave }) {
  const [form, setForm] = useState({
    frequency:    sub.frequency    || 'daily',
    heure_envoi:  sub.heure_envoi  ?? 7,
    jour_semaine: sub.jour_semaine ?? 0,
    jour_mois:    sub.jour_mois    ?? 1,
    export_format: sub.export_format || 'excel',
    channel:      sub.channel      || 'email',
    contact_info: sub.contact_info || '',
    date_debut:   sub.date_debut   ? sub.date_debut.slice(0, 10) : '',
    date_fin:     sub.date_fin     ? sub.date_fin.slice(0, 10)   : '',
  })
  const [saving, setSaving] = useState(false)

  const f = (k, v) => setForm(p => ({ ...p, [k]: v }))

  async function handleSave() {
    setSaving(true)
    await onSave(sub.id, {
      ...form,
      jour_semaine: form.frequency === 'weekly'  ? form.jour_semaine : null,
      jour_mois:    form.frequency === 'monthly' ? form.jour_mois    : null,
      date_debut:   form.date_debut || null,
      date_fin:     form.date_fin   || null,
    })
    setSaving(false)
  }

  const freqDesc = () => {
    const h = `${form.heure_envoi}h00`
    if (form.frequency === 'daily')   return `Chaque jour à ${h}`
    if (form.frequency === 'weekly')  return `${DAYS_FR[form.jour_semaine]} à ${h}`
    if (form.frequency === 'monthly') return `Le ${form.jour_mois} du mois à ${h}`
    return ''
  }

  const inCls = 'w-full text-xs rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-100 px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-amber-400'
  const btnCls = (active) => `px-2.5 py-1.5 text-xs rounded-lg border transition-colors ${active ? 'border-amber-400 bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 font-semibold' : 'border-gray-200 dark:border-gray-600 text-gray-500 hover:border-gray-300'}`

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-md" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200 dark:border-gray-700">
          <div>
            <div className="flex items-center gap-2">
              <Edit2 className="w-4 h-4 text-amber-500" />
              <h2 className="text-sm font-bold text-gray-900 dark:text-white">Modifier l'abonnement</h2>
            </div>
            <p className="text-xs text-gray-400 mt-0.5 truncate max-w-xs">{sub.report_nom} · {sub.user_email}</p>
          </div>
          <button onClick={onClose} className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg">
            <X className="w-4 h-4 text-gray-500" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          {/* Fréquence */}
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1.5">Fréquence</label>
            <div className="grid grid-cols-3 gap-1.5">
              {Object.entries(FREQ_LABEL).map(([k, l]) => (
                <button key={k} onClick={() => f('frequency', k)} className={btnCls(form.frequency === k)}>{l}</button>
              ))}
            </div>
          </div>

          {/* Heure */}
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1.5">Heure d'envoi</label>
            <div className="flex flex-wrap gap-1">
              {HOURS.map(h => (
                <button key={h} onClick={() => f('heure_envoi', h)} className={btnCls(form.heure_envoi === h)}>{h}h</button>
              ))}
            </div>
          </div>

          {/* Jour semaine */}
          {form.frequency === 'weekly' && (
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1.5">Jour de la semaine</label>
              <div className="grid grid-cols-7 gap-1">
                {DAYS_FR.map((d, i) => (
                  <button key={i} onClick={() => f('jour_semaine', i)} className={btnCls(form.jour_semaine === i)}>{d}</button>
                ))}
              </div>
            </div>
          )}

          {/* Jour mois */}
          {form.frequency === 'monthly' && (
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1.5">Jour du mois</label>
              <div className="flex flex-wrap gap-1">
                {Array.from({ length: 28 }, (_, i) => i + 1).map(d => (
                  <button key={d} onClick={() => f('jour_mois', d)} className={`w-8 h-7 text-xs rounded border transition-colors ${form.jour_mois === d ? 'border-amber-400 bg-amber-50 dark:bg-amber-900/30 text-amber-700 font-semibold' : 'border-gray-200 dark:border-gray-600 text-gray-500 hover:border-gray-300'}`}>{d}</button>
                ))}
              </div>
            </div>
          )}

          {/* Résumé planification */}
          <div className="px-3 py-2 bg-amber-50 dark:bg-amber-900/20 rounded-lg">
            <p className="text-xs text-amber-600 dark:text-amber-400 font-medium">📅 {freqDesc()}</p>
          </div>

          {/* Format + Canal */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1.5">Format</label>
              <div className="flex gap-1">
                {FORMATS.map(ft => (
                  <button key={ft.key} onClick={() => f('export_format', ft.key)} className={`flex-1 ${btnCls(form.export_format === ft.key)}`}>{ft.label}</button>
                ))}
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1.5">Canal</label>
              <select value={form.channel} onChange={e => f('channel', e.target.value)} className={inCls}>
                {CHANNELS_OPT.map(c => <option key={c.key} value={c.key}>{c.label}</option>)}
              </select>
            </div>
          </div>

          {/* Contact (si non-email) */}
          {form.channel !== 'email' && (
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1.5">
                {form.channel === 'whatsapp' ? 'Numéro WhatsApp' : 'Chat ID Telegram'}
              </label>
              <input type="text" value={form.contact_info} onChange={e => f('contact_info', e.target.value)}
                placeholder={form.channel === 'whatsapp' ? '+212600000000' : '123456789'}
                className={inCls}
              />
            </div>
          )}

          {/* Période */}
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1.5">Période de validité <span className="font-normal text-gray-400">(optionnel)</span></label>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <p className="text-[10px] text-gray-400 mb-0.5">À partir du</p>
                <input type="date" value={form.date_debut} onChange={e => f('date_debut', e.target.value)} className={inCls} />
              </div>
              <div>
                <p className="text-[10px] text-gray-400 mb-0.5">Jusqu'au</p>
                <input type="date" value={form.date_fin} min={form.date_debut} onChange={e => f('date_fin', e.target.value)} className={inCls} />
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 px-5 py-4 border-t border-gray-200 dark:border-gray-700">
          <button onClick={onClose} className="px-3 py-2 text-xs rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300">
            Annuler
          </button>
          <button onClick={handleSave} disabled={saving}
            className="flex items-center gap-1.5 px-4 py-2 text-xs rounded-lg text-white font-medium disabled:opacity-50"
            style={{ backgroundColor: 'var(--color-primary-600)' }}>
            {saving ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
            Enregistrer
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── KPI Card ─────────────────────────────────────────────────────────────────

function KpiCard({ icon, label, value, sub, color }) {
  const colors = {
    indigo: 'bg-indigo-50 dark:bg-indigo-900/20 border-indigo-100 dark:border-indigo-800',
    green:  'bg-green-50  dark:bg-green-900/20  border-green-100  dark:border-green-800',
    red:    'bg-red-50    dark:bg-red-900/20    border-red-100    dark:border-red-800',
    amber:  'bg-amber-50  dark:bg-amber-900/20  border-amber-100  dark:border-amber-800',
  }
  return (
    <div className={`card p-4 border ${colors[color] || colors.indigo}`}>
      <div className="flex items-center justify-between mb-2">
        {icon}
        <span className="text-2xl font-bold text-gray-900 dark:text-white">{value ?? '—'}</span>
      </div>
      <p className="text-xs font-medium text-gray-600 dark:text-gray-400">{label}</p>
      <p className="text-[10px] text-gray-400 mt-0.5">{sub}</p>
    </div>
  )
}
