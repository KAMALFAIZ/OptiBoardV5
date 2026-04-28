import { useState, useEffect, useMemo } from 'react'
import {
  Bell, Plus, Trash2, Edit2, ToggleLeft, ToggleRight,
  AlertTriangle, AlertCircle, Info, CheckCheck, Play,
  Clock, History, Settings, X, Check, Filter,
  TrendingUp, TrendingDown, Activity, ShieldAlert,
  Mail, RefreshCw, ChevronRight, Send, Globe,
  Database, Layers, Users,
} from 'lucide-react'
import api from '../services/api'

// ────────────────────────────────────────────────
// Config niveaux
// ────────────────────────────────────────────────
const NIVEAU_CONFIG = {
  critical: {
    label: 'Critique',
    color: 'text-red-600 dark:text-red-400',
    bg: 'bg-red-50 dark:bg-red-900/20',
    border: 'border-red-200 dark:border-red-800',
    badge: 'bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300',
    dot: 'bg-red-500',
    icon: (sz = 'w-4 h-4') => <AlertTriangle className={`${sz} text-red-500`} />,
  },
  warning: {
    label: 'Attention',
    color: 'text-amber-600 dark:text-amber-400',
    bg: 'bg-amber-50 dark:bg-amber-900/20',
    border: 'border-amber-200 dark:border-amber-800',
    badge: 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300',
    dot: 'bg-amber-500',
    icon: (sz = 'w-4 h-4') => <AlertCircle className={`${sz} text-amber-500`} />,
  },
  info: {
    label: 'Info',
    color: 'text-blue-600 dark:text-blue-400',
    bg: 'bg-blue-50 dark:bg-blue-900/20',
    border: 'border-blue-200 dark:border-blue-800',
    badge: 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300',
    dot: 'bg-blue-500',
    icon: (sz = 'w-4 h-4') => <Info className={`${sz} text-blue-500`} />,
  },
}

const EMPTY_RULE = {
  nom: '', description: '', metric_type: 'dso', operator: 'gt',
  threshold_value: '', niveau: 'warning', notify_emails: [],
  cooldown_hours: 4, is_active: true,
}

function fmt(n, unit = '') {
  if (n === null || n === undefined) return '—'
  if (unit === 'MAD') return new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 0 }).format(n) + ' MAD'
  if (unit === '%') return n.toFixed(1) + '%'
  if (unit === 'jours') return n.toFixed(1) + ' j'
  if (unit === 'x') return n.toFixed(1) + 'x'
  return String(n)
}

function timeAgo(dt) {
  if (!dt) return '—'
  const diff = Date.now() - new Date(dt).getTime()
  const m = Math.floor(diff / 60000)
  if (m < 1) return 'À l\'instant'
  if (m < 60) return `Il y a ${m} min`
  const h = Math.floor(m / 60)
  if (h < 24) return `Il y a ${h}h`
  const d = Math.floor(h / 24)
  return `Il y a ${d} jour${d > 1 ? 's' : ''}`
}

// ────────────────────────────────────────────────
// Composant principal
// ────────────────────────────────────────────────
export default function AlertsPage() {
  const [tab, setTab]             = useState('rules')
  const [rules, setRules]         = useState([])
  const [history, setHistory]     = useState([])
  const [metrics, setMetrics]     = useState([])
  const [operators, setOperators] = useState([])
  const [loading, setLoading]     = useState(true)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [showForm, setShowForm]   = useState(false)
  const [editRule, setEditRule]   = useState(null)
  const [form, setForm]           = useState(EMPTY_RULE)
  const [emailInput, setEmailInput] = useState('')
  const [saving, setSaving]       = useState(false)
  const [evaluating, setEvaluating] = useState(false)
  const [successMsg, setSuccessMsg] = useState('')
  const [errorMsg, setErrorMsg]   = useState('')
  const [filterNiveau, setFilterNiveau] = useState('all')
  const [filterStatus, setFilterStatus] = useState('all')

  // Templates (base maître)
  const [templates, setTemplates]         = useState([])
  const [templatesLoading, setTemplatesLoading] = useState(false)
  const [publishing, setPublishing]       = useState(false)
  const [publishResult, setPublishResult] = useState(null)

  useEffect(() => { fetchAll() }, [])

  async function fetchAll() {
    setLoading(true)
    try {
      const [rulesRes, metaRes] = await Promise.all([
        api.get('/alerts/rules'),
        api.get('/alerts/metrics'),
      ])
      if (rulesRes.data?.success) setRules(rulesRes.data.data || [])
      if (metaRes.data?.success) {
        setMetrics(metaRes.data.metrics || [])
        setOperators(metaRes.data.operators || [])
      }
    } catch { setErrorMsg('Impossible de charger les règles') }
    finally { setLoading(false) }
  }

  async function fetchHistory() {
    setHistoryLoading(true)
    try {
      const res = await api.get('/alerts/history?limit=100')
      if (res.data?.success) setHistory(res.data.data || [])
    } catch { } finally { setHistoryLoading(false) }
  }

  // Stats calculées
  const stats = useMemo(() => {
    const active    = rules.filter(r => r.is_active).length
    const criticals = rules.filter(r => r.niveau === 'critical' && r.is_active).length
    const unread    = rules.reduce((s, r) => s + (r.unread_count || 0), 0)
    const lastEval  = rules.reduce((latest, r) => {
      if (!r.last_checked) return latest
      const d = new Date(r.last_checked)
      return d > latest ? d : latest
    }, new Date(0))
    return { total: rules.length, active, criticals, unread, lastEval }
  }, [rules])

  // Règles filtrées
  const filteredRules = useMemo(() => {
    return rules.filter(r => {
      if (filterNiveau !== 'all' && r.niveau !== filterNiveau) return false
      if (filterStatus === 'active'   && !r.is_active) return false
      if (filterStatus === 'inactive' &&  r.is_active) return false
      return true
    })
  }, [rules, filterNiveau, filterStatus])

  function openCreate() { setEditRule(null); setForm(EMPTY_RULE); setEmailInput(''); setShowForm(true) }
  function openEdit(rule) {
    setEditRule(rule)
    setForm({
      nom: rule.nom || '', description: rule.description || '',
      metric_type: rule.metric_type || 'dso', operator: rule.operator || 'gt',
      threshold_value: rule.threshold_value ?? '', niveau: rule.niveau || 'warning',
      notify_emails: rule.notify_emails || [], cooldown_hours: rule.cooldown_hours ?? 4,
      is_active: rule.is_active ?? true,
    })
    setEmailInput(''); setShowForm(true)
  }

  function addEmail() {
    const e = emailInput.trim()
    if (e && /\S+@\S+\.\S+/.test(e) && !form.notify_emails.includes(e)) {
      setForm(f => ({ ...f, notify_emails: [...f.notify_emails, e] }))
      setEmailInput('')
    }
  }

  async function saveRule() {
    if (!form.nom || !form.metric_type || form.threshold_value === '') {
      setErrorMsg('Nom, métrique et seuil sont obligatoires'); return
    }
    setSaving(true)
    try {
      const payload = { ...form, threshold_value: parseFloat(form.threshold_value) }
      if (editRule) await api.put(`/alerts/rules/${editRule.id}`, payload)
      else          await api.post('/alerts/rules', payload)
      flash('success', editRule ? 'Règle mise à jour' : 'Règle créée')
      setShowForm(false); fetchAll()
    } catch { setErrorMsg('Erreur lors de la sauvegarde') }
    finally { setSaving(false) }
  }

  async function deleteRule(id) {
    if (!confirm('Supprimer cette règle et tout son historique ?')) return
    try { await api.delete(`/alerts/rules/${id}`); flash('success', 'Règle supprimée'); fetchAll() }
    catch { setErrorMsg('Erreur suppression') }
  }

  async function toggleRule(id) {
    try { await api.post(`/alerts/rules/${id}/toggle`); fetchAll() }
    catch { setErrorMsg('Erreur toggle') }
  }

  async function runEvaluation() {
    setEvaluating(true)
    try {
      await api.post('/alerts/evaluate')
      flash('success', 'Évaluation lancée — résultats dans quelques secondes')
      setTimeout(() => { fetchAll(); if (tab === 'history') fetchHistory() }, 3000)
    } catch { setErrorMsg('Erreur évaluation') }
    finally { setEvaluating(false) }
  }

  async function acknowledgeOne(id) {
    try { await api.post(`/alerts/history/${id}/acknowledge`); fetchHistory() }
    catch { }
  }

  async function acknowledgeAll() {
    try { await api.post('/alerts/history/acknowledge-all'); flash('success', 'Tout marqué comme lu'); fetchHistory() }
    catch { }
  }

  // ── Templates ─────────────────────────────────────
  async function fetchTemplates() {
    setTemplatesLoading(true)
    try {
      const res = await api.get('/alerts/templates')
      if (res.data?.success) setTemplates(res.data.data || [])
    } catch { } finally { setTemplatesLoading(false) }
  }

  async function deleteTemplate(id) {
    if (!confirm('Supprimer ce template ?')) return
    try { await api.delete(`/alerts/templates/${id}`); flash('success', 'Template supprimé'); fetchTemplates() }
    catch { setErrorMsg('Erreur suppression') }
  }

  async function publishAll(templateIds = null) {
    setPublishing(true)
    setPublishResult(null)
    try {
      const payload = {}
      if (templateIds) payload.template_ids = templateIds
      const res = await api.post('/alerts/templates/publish', payload)
      if (res.data?.success) {
        setPublishResult(res.data)
        flash('success', res.data.message)
        fetchTemplates()
      } else {
        setErrorMsg(res.data?.error || 'Erreur publication')
      }
    } catch { setErrorMsg('Erreur publication') }
    finally { setPublishing(false) }
  }

  async function seedDemoTemplates() {
    try {
      const res = await api.post('/alerts/templates/seed-demo')
      if (res.data?.success) { flash('success', res.data.message); fetchTemplates() }
      else setErrorMsg(res.data?.error || 'Erreur')
    } catch { setErrorMsg('Erreur chargement templates demo') }
  }

  function flash(type, msg) {
    if (type === 'success') { setSuccessMsg(msg); setTimeout(() => setSuccessMsg(''), 3000) }
    else { setErrorMsg(msg); setTimeout(() => setErrorMsg(''), 4000) }
  }

  const getMetric  = key => metrics.find(m => m.key === key)
  const getOpLabel = key => operators.find(o => o.key === key)?.label || key

  return (
    <div className="space-y-5">

      {/* ── En-tête ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Bell className="w-5 h-5" style={{ color: 'var(--color-primary-600)' }} />
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">Alertes KPI</h1>
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 ml-7">
            Surveillance automatique des indicateurs clés de performance
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={runEvaluation} disabled={evaluating}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${evaluating ? 'animate-spin' : ''}`} />
            {evaluating ? 'En cours…' : 'Évaluer maintenant'}
          </button>
          <button
            onClick={openCreate}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg text-white transition-colors"
            style={{ backgroundColor: 'var(--color-primary-600)' }}
          >
            <Plus className="w-3.5 h-3.5" /> Nouvelle règle
          </button>
        </div>
      </div>

      {/* ── Messages flash ── */}
      {successMsg && (
        <div className="flex items-center gap-2 p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg text-sm text-green-700 dark:text-green-300">
          <Check className="w-4 h-4 flex-shrink-0" /> {successMsg}
        </div>
      )}
      {errorMsg && (
        <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-700 dark:text-red-300">
          <X className="w-4 h-4 flex-shrink-0" /> {errorMsg}
        </div>
      )}

      {/* ── Cartes stats ── */}
      {!loading && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            {
              label: 'Règles actives',
              value: stats.active,
              sub: `${stats.total} au total`,
              icon: <Activity className="w-5 h-5" />,
              color: 'text-blue-600 dark:text-blue-400',
              bg: 'bg-blue-50 dark:bg-blue-900/20',
            },
            {
              label: 'Critiques actives',
              value: stats.criticals,
              sub: 'niveau critique',
              icon: <ShieldAlert className="w-5 h-5" />,
              color: 'text-red-600 dark:text-red-400',
              bg: 'bg-red-50 dark:bg-red-900/20',
            },
            {
              label: 'Non lues (24h)',
              value: stats.unread,
              sub: 'à traiter',
              icon: <Bell className="w-5 h-5" />,
              color: stats.unread > 0 ? 'text-amber-600 dark:text-amber-400' : 'text-gray-500',
              bg: stats.unread > 0 ? 'bg-amber-50 dark:bg-amber-900/20' : 'bg-gray-50 dark:bg-gray-800',
            },
            {
              label: 'Dernière éval.',
              value: stats.lastEval.getFullYear() > 2000 ? timeAgo(stats.lastEval) : '—',
              sub: 'surveillance continue',
              icon: <Clock className="w-5 h-5" />,
              color: 'text-green-600 dark:text-green-400',
              bg: 'bg-green-50 dark:bg-green-900/20',
              small: true,
            },
          ].map((s, i) => (
            <div key={i} className="card p-4 flex items-center gap-3">
              <div className={`p-2 rounded-lg ${s.bg} ${s.color} flex-shrink-0`}>
                {s.icon}
              </div>
              <div className="min-w-0">
                <p className={`font-bold ${s.small ? 'text-base' : 'text-2xl'} ${s.color} leading-tight`}>
                  {s.value}
                </p>
                <p className="text-xs font-medium text-gray-700 dark:text-gray-300">{s.label}</p>
                <p className="text-[10px] text-gray-400">{s.sub}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── Onglets ── */}
      <div className="flex gap-4 border-b border-gray-200 dark:border-gray-700">
        {[
          { key: 'rules',     label: 'Règles d\'alerte', icon: <Settings className="w-4 h-4" />, count: rules.length },
          { key: 'history',   label: 'Historique',        icon: <History className="w-4 h-4" />,  count: history.length || null },
          { key: 'templates', label: 'Modèles Maître',    icon: <Layers className="w-4 h-4" />,   count: templates.length || null },
        ].map(t => (
          <button
            key={t.key}
            onClick={() => {
              setTab(t.key)
              if (t.key === 'history') fetchHistory()
              if (t.key === 'templates') fetchTemplates()
            }}
            className={`flex items-center gap-1.5 pb-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t.key
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
            style={tab === t.key ? { borderColor: 'var(--color-primary-500)', color: 'var(--color-primary-600)' } : {}}
          >
            {t.icon}
            {t.label}
            {t.count != null && (
              <span className="ml-1 px-1.5 py-0.5 text-[10px] font-bold rounded-full bg-gray-100 dark:bg-gray-700 text-gray-500">
                {t.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* ══════════════════════════════════════
          ONGLET RÈGLES
      ══════════════════════════════════════ */}
      {tab === 'rules' && (
        <div className="space-y-4">
          {/* Filtres */}
          {!loading && rules.length > 0 && (
            <div className="flex flex-wrap items-center gap-2">
              <span className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
                <Filter className="w-3 h-3" /> Filtrer :
              </span>
              {/* Niveau */}
              {[
                { key: 'all',      label: `Toutes (${rules.length})` },
                { key: 'critical', label: `Critiques (${rules.filter(r=>r.niveau==='critical').length})` },
                { key: 'warning',  label: `Attention (${rules.filter(r=>r.niveau==='warning').length})` },
              ].map(f => (
                <button
                  key={f.key}
                  onClick={() => setFilterNiveau(f.key)}
                  className={`px-3 py-1 text-xs rounded-full border transition-colors ${
                    filterNiveau === f.key
                      ? 'text-white border-transparent'
                      : 'border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700'
                  }`}
                  style={filterNiveau === f.key ? { backgroundColor: 'var(--color-primary-600)' } : {}}
                >
                  {f.label}
                </button>
              ))}
              <div className="w-px h-4 bg-gray-200 dark:bg-gray-700 mx-1" />
              {[
                { key: 'all',      label: 'Tous statuts' },
                { key: 'active',   label: 'Actives' },
                { key: 'inactive', label: 'Inactives' },
              ].map(f => (
                <button
                  key={f.key}
                  onClick={() => setFilterStatus(f.key)}
                  className={`px-3 py-1 text-xs rounded-full border transition-colors ${
                    filterStatus === f.key
                      ? 'bg-gray-700 dark:bg-gray-300 text-white dark:text-gray-900 border-transparent'
                      : 'border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700'
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>
          )}

          {/* Liste */}
          {loading ? (
            <div className="flex justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2" style={{ borderColor: 'var(--color-primary-600)' }} />
            </div>
          ) : rules.length === 0 ? (
            <div className="text-center py-16 text-gray-500 dark:text-gray-400">
              <Bell className="w-12 h-12 mx-auto mb-3 opacity-20" />
              <p className="font-medium text-base">Aucune règle d'alerte configurée</p>
              <p className="text-sm mt-1">Créez votre première règle pour surveiller vos KPIs automatiquement.</p>
              <button
                onClick={openCreate}
                className="mt-4 px-5 py-2 text-sm rounded-lg text-white"
                style={{ backgroundColor: 'var(--color-primary-600)' }}
              >
                Créer une règle
              </button>
            </div>
          ) : filteredRules.length === 0 ? (
            <div className="text-center py-10 text-gray-400 text-sm">
              Aucune règle ne correspond aux filtres sélectionnés.
            </div>
          ) : (
            <div className="space-y-2">
              {filteredRules.map(rule => {
                const nConf  = NIVEAU_CONFIG[rule.niveau] || NIVEAU_CONFIG.info
                const metric = getMetric(rule.metric_type)
                const unit   = metric?.unit || ''
                const hasTrigger = !!rule.last_triggered

                return (
                  <div
                    key={rule.id}
                    className={`card p-4 transition-all ${
                      !rule.is_active ? 'opacity-50' : ''
                    } ${
                      rule.unread_count > 0
                        ? `border-l-4 ${rule.niveau === 'critical' ? 'border-l-red-500' : 'border-l-amber-500'}`
                        : ''
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      {/* Icône niveau */}
                      <div className={`p-2 rounded-lg ${nConf.bg} flex-shrink-0 mt-0.5`}>
                        {nConf.icon('w-4 h-4')}
                      </div>

                      {/* Infos principales */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-semibold text-gray-900 dark:text-white text-sm">
                            {rule.nom}
                          </span>
                          <span className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${nConf.badge}`}>
                            {nConf.label}
                          </span>
                          {!rule.is_active && (
                            <span className="text-[11px] px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-400">
                              Inactif
                            </span>
                          )}
                          {rule.unread_count > 0 && (
                            <span className="flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-red-500 text-white font-bold">
                              <Bell className="w-2.5 h-2.5" />
                              {rule.unread_count} non lue{rule.unread_count > 1 ? 's' : ''}
                            </span>
                          )}
                        </div>

                        {/* Condition */}
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                          <span className="font-medium text-gray-700 dark:text-gray-300">
                            {metric?.label || rule.metric_type}
                          </span>
                          {' '}<span className="font-mono">{getOpLabel(rule.operator)}</span>{' '}
                          <strong className={nConf.color}>{fmt(rule.threshold_value, unit)}</strong>
                          {metric?.unit && <span className="text-gray-400 ml-1">({unit})</span>}
                          <span className="ml-2 text-gray-400">• Cooldown {rule.cooldown_hours}h</span>
                          {rule.notify_emails?.length > 0 && (
                            <span className="ml-2 inline-flex items-center gap-0.5 text-gray-400">
                              <Mail className="w-3 h-3" /> {rule.notify_emails.length}
                            </span>
                          )}
                        </p>

                        {/* Dernière activité */}
                        {hasTrigger ? (
                          <p className="text-[11px] text-gray-400 mt-1 flex items-center gap-1">
                            <Clock className="w-3 h-3 flex-shrink-0" />
                            Dernier déclenchement : {new Date(rule.last_triggered).toLocaleString('fr-FR')}
                            {rule.trigger_count > 0 && (
                              <span className="ml-1 text-gray-500">• {rule.trigger_count} fois au total</span>
                            )}
                          </p>
                        ) : (
                          <p className="text-[11px] text-gray-400 mt-1">Jamais déclenchée</p>
                        )}
                      </div>

                      {/* Actions */}
                      <div className="flex items-center gap-0.5 flex-shrink-0">
                        <button
                          onClick={() => toggleRule(rule.id)}
                          className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                          title={rule.is_active ? 'Désactiver' : 'Activer'}
                        >
                          {rule.is_active
                            ? <ToggleRight className="w-5 h-5" style={{ color: 'var(--color-primary-500)' }} />
                            : <ToggleLeft  className="w-5 h-5 text-gray-400" />
                          }
                        </button>
                        <button
                          onClick={() => openEdit(rule)}
                          className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                          title="Modifier"
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => deleteRule(rule.id)}
                          className="p-1.5 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors text-gray-400 hover:text-red-500"
                          title="Supprimer"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* ══════════════════════════════════════
          ONGLET HISTORIQUE
      ══════════════════════════════════════ */}
      {tab === 'history' && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {history.length > 0
                ? `${history.length} entrée${history.length > 1 ? 's' : ''} — ${history.filter(h => !h.is_acknowledged).length} non lue${history.filter(h => !h.is_acknowledged).length > 1 ? 's' : ''}`
                : 'Aucun historique'
              }
            </p>
            {history.some(h => !h.is_acknowledged) && (
              <button
                onClick={acknowledgeAll}
                className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors text-gray-600 dark:text-gray-400"
              >
                <CheckCheck className="w-3.5 h-3.5" />
                Tout marquer comme lu
              </button>
            )}
          </div>

          {historyLoading ? (
            <div className="flex justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2" style={{ borderColor: 'var(--color-primary-600)' }} />
            </div>
          ) : history.length === 0 ? (
            <div className="text-center py-16 text-gray-500 dark:text-gray-400">
              <History className="w-12 h-12 mx-auto mb-3 opacity-20" />
              <p className="font-medium">Aucun historique d'alerte</p>
              <p className="text-sm mt-1">Les alertes déclenchées apparaîtront ici.</p>
              <button
                onClick={runEvaluation}
                className="mt-4 flex items-center gap-2 mx-auto px-4 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              >
                <Play className="w-3.5 h-3.5" /> Lancer une évaluation
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              {history.map(entry => {
                const nConf  = NIVEAU_CONFIG[entry.niveau] || NIVEAU_CONFIG.info
                const metric = getMetric(entry.metric_type)
                const isRead = !!entry.is_acknowledged
                return (
                  <div
                    key={entry.id}
                    className={`flex items-start gap-3 p-3.5 rounded-xl border text-sm transition-all ${
                      isRead
                        ? 'bg-gray-50 dark:bg-gray-800/40 border-gray-200 dark:border-gray-700/50 opacity-60'
                        : `${nConf.bg} ${nConf.border} border`
                    }`}
                  >
                    <div className={`mt-0.5 flex-shrink-0 ${isRead ? 'opacity-50' : ''}`}>
                      {nConf.icon('w-4 h-4')}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className={`font-semibold ${isRead ? 'text-gray-500 dark:text-gray-400' : 'text-gray-900 dark:text-white'}`}>
                          {entry.rule_nom || 'Alerte'}
                        </span>
                        <span className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${nConf.badge}`}>
                          {nConf.label}
                        </span>
                        {isRead && <span className="text-[11px] text-gray-400 flex items-center gap-0.5"><Check className="w-3 h-3" /> Lu</span>}
                      </div>
                      <p className={`mt-0.5 ${isRead ? 'text-gray-400' : 'text-gray-600 dark:text-gray-300'}`}>
                        {entry.message}
                      </p>
                      <div className="flex items-center gap-3 mt-1 text-[11px] text-gray-400">
                        <span className="flex items-center gap-0.5">
                          <Clock className="w-3 h-3" />
                          {new Date(entry.triggered_at).toLocaleString('fr-FR')}
                        </span>
                        {entry.acknowledged_by && (
                          <span>Lu par {entry.acknowledged_by}</span>
                        )}
                      </div>
                    </div>
                    {!isRead && (
                      <button
                        onClick={() => acknowledgeOne(entry.id)}
                        className="flex-shrink-0 p-1.5 rounded-lg hover:bg-white/60 dark:hover:bg-gray-700/60 transition-colors text-gray-400 hover:text-green-600"
                        title="Marquer comme lu"
                      >
                        <Check className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* ══════════════════════════════════════
          ONGLET MODÈLES MAÎTRE
      ══════════════════════════════════════ */}
      {tab === 'templates' && (
        <div className="space-y-4">
          {/* Toolbar templates */}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
              <Database className="w-4 h-4" />
              <span>Base maître <code className="text-xs bg-gray-100 dark:bg-gray-700 px-1 rounded">OptiBoard_SaaS</code></span>
              <span className="text-gray-300 dark:text-gray-600">•</span>
              <span>{templates.length} modèle{templates.length !== 1 ? 's' : ''}</span>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={seedDemoTemplates}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              >
                <RefreshCw className="w-3.5 h-3.5" /> Charger standards
              </button>
              <button
                onClick={() => publishAll()}
                disabled={publishing || templates.filter(t => t.is_active).length === 0}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg text-white transition-colors disabled:opacity-50"
                style={{ backgroundColor: 'var(--color-primary-600)' }}
              >
                <Globe className={`w-3.5 h-3.5 ${publishing ? 'animate-spin' : ''}`} />
                {publishing ? 'Publication…' : 'Publier à tous les clients'}
              </button>
            </div>
          </div>

          {/* Résultat publication */}
          {publishResult && (
            <div className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-xl">
              <div className="flex items-center gap-2 text-green-700 dark:text-green-300 font-semibold text-sm mb-2">
                <Check className="w-4 h-4" /> Publication terminée
              </div>
              <div className="grid grid-cols-3 gap-3 text-center">
                {[
                  { label: 'Règles créées', val: publishResult.total_created, color: 'text-green-600' },
                  { label: 'Clients touchés', val: publishResult.clients_count, color: 'text-blue-600' },
                  { label: 'Ignorées (existent)', val: publishResult.total_skipped, color: 'text-gray-500' },
                ].map((s, i) => (
                  <div key={i} className="bg-white dark:bg-gray-800 rounded-lg p-2">
                    <p className={`text-lg font-bold ${s.color}`}>{s.val}</p>
                    <p className="text-[10px] text-gray-500">{s.label}</p>
                  </div>
                ))}
              </div>
              {publishResult.details?.some(d => d.errors?.length) && (
                <div className="mt-2 text-xs text-red-600 dark:text-red-400">
                  {publishResult.details.filter(d => d.errors?.length).map(d => (
                    <div key={d.client}>{d.nom}: {d.errors[0]}</div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Loading / empty */}
          {templatesLoading ? (
            <div className="flex items-center justify-center py-12">
              <RefreshCw className="w-6 h-6 animate-spin text-gray-400" />
            </div>
          ) : templates.length === 0 ? (
            <div className="text-center py-14">
              <Layers className="w-10 h-10 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
              <p className="text-gray-500 dark:text-gray-400 font-medium">Aucun modèle en base maître</p>
              <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">
                Cliquez "Charger standards" pour injecter les modèles financiers prédéfinis
              </p>
              <button
                onClick={seedDemoTemplates}
                className="mt-4 px-4 py-2 text-sm rounded-lg text-white transition-colors"
                style={{ backgroundColor: 'var(--color-primary-600)' }}
              >
                Charger les modèles standards
              </button>
            </div>
          ) : (
            <>
              {/* Regroupement par catégorie */}
              {Object.entries(
                templates.reduce((acc, t) => {
                  const cat = t.categorie || 'Autre'
                  if (!acc[cat]) acc[cat] = []
                  acc[cat].push(t)
                  return acc
                }, {})
              ).map(([cat, items]) => (
                <div key={cat} className="space-y-2">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400 dark:text-gray-500 flex items-center gap-2">
                    <span className="h-px flex-1 bg-gray-200 dark:bg-gray-700" />
                    {cat}
                    <span className="h-px flex-1 bg-gray-200 dark:bg-gray-700" />
                  </h3>
                  {items.map(tmpl => {
                    const cfg = NIVEAU_CONFIG[tmpl.niveau] || NIVEAU_CONFIG.warning
                    return (
                      <div
                        key={tmpl.id}
                        className={`card p-4 border-l-4 ${cfg.border} flex items-start gap-4`}
                      >
                        {/* Niveau icon */}
                        <div className={`mt-0.5 ${cfg.color}`}>
                          {cfg.icon('w-5 h-5')}
                        </div>
                        {/* Contenu */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-semibold text-sm text-gray-900 dark:text-white">{tmpl.nom}</span>
                            <span className={`px-1.5 py-0.5 text-[10px] font-bold rounded-full ${cfg.badge}`}>
                              {cfg.label}
                            </span>
                            {tmpl.published_count > 0 && (
                              <span className="flex items-center gap-1 px-1.5 py-0.5 text-[10px] rounded-full bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300">
                                <Users className="w-2.5 h-2.5" />
                                Publié {tmpl.published_count}×
                              </span>
                            )}
                          </div>
                          {tmpl.description && (
                            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 truncate">{tmpl.description}</p>
                          )}
                          <div className="flex items-center gap-3 mt-1.5 text-[11px] text-gray-400">
                            <span>Seuil : <strong className="text-gray-600 dark:text-gray-300">{tmpl.threshold_value}</strong></span>
                            <span>Cooldown : <strong className="text-gray-600 dark:text-gray-300">{tmpl.cooldown_hours}h</strong></span>
                            {tmpl.last_published && (
                              <span>Dernier envoi : {timeAgo(tmpl.last_published)}</span>
                            )}
                          </div>
                        </div>
                        {/* Actions */}
                        <div className="flex items-center gap-1 flex-shrink-0">
                          <button
                            onClick={() => publishAll([tmpl.id])}
                            disabled={publishing}
                            className="flex items-center gap-1 px-2.5 py-1.5 text-xs rounded-lg bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 hover:bg-blue-100 dark:hover:bg-blue-900/50 transition-colors disabled:opacity-50"
                            title="Publier à tous les clients"
                          >
                            <Send className="w-3 h-3" />
                            Publier
                          </button>
                          <button
                            onClick={() => deleteTemplate(tmpl.id)}
                            className="p-1.5 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                            title="Supprimer"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    )
                  })}
                </div>
              ))}
            </>
          )}
        </div>
      )}

      {/* ══════════════════════════════════════
          MODAL FORMULAIRE
      ══════════════════════════════════════ */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-lg max-h-[92vh] overflow-y-auto">

            {/* Header */}
            <div className="flex items-center justify-between p-5 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-2">
                <Bell className="w-4 h-4" style={{ color: 'var(--color-primary-600)' }} />
                <h2 className="font-semibold text-gray-900 dark:text-white">
                  {editRule ? 'Modifier la règle' : 'Nouvelle règle d\'alerte'}
                </h2>
              </div>
              <button
                onClick={() => setShowForm(false)}
                className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Corps */}
            <div className="p-5 space-y-4">

              {/* Nom */}
              <div>
                <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
                  Nom de la règle <span className="text-red-500">*</span>
                </label>
                <input
                  type="text" value={form.nom}
                  onChange={e => setForm(f => ({ ...f, nom: e.target.value }))}
                  placeholder="Ex: DSO critique > 90 jours"
                  className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-400"
                />
              </div>

              {/* Description */}
              <div>
                <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
                  Description <span className="text-gray-400 font-normal">(optionnel)</span>
                </label>
                <input
                  type="text" value={form.description}
                  onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                  placeholder="Contexte et action recommandée…"
                  className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none"
                />
              </div>

              {/* Condition */}
              <div>
                <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
                  Condition de déclenchement <span className="text-red-500">*</span>
                </label>
                <div className="grid grid-cols-3 gap-2">
                  <select
                    value={form.metric_type}
                    onChange={e => setForm(f => ({ ...f, metric_type: e.target.value }))}
                    className="col-span-1 px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none"
                  >
                    {metrics.map(m => <option key={m.key} value={m.key}>{m.label}</option>)}
                  </select>
                  <select
                    value={form.operator}
                    onChange={e => setForm(f => ({ ...f, operator: e.target.value }))}
                    className="px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none"
                  >
                    {operators.map(o => <option key={o.key} value={o.key}>{o.label}</option>)}
                  </select>
                  <input
                    type="number" value={form.threshold_value}
                    onChange={e => setForm(f => ({ ...f, threshold_value: e.target.value }))}
                    placeholder="Seuil"
                    className="px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none"
                  />
                </div>
                {form.metric_type && (
                  <p className="text-xs text-gray-400 mt-1 flex items-center gap-1">
                    <Info className="w-3 h-3" />
                    Unité : <strong>{getMetric(form.metric_type)?.unit || '—'}</strong>
                    {getMetric(form.metric_type)?.higher_is_worse
                      ? ' — une valeur élevée est défavorable'
                      : ' — une valeur élevée est favorable'
                    }
                  </p>
                )}
              </div>

              {/* Niveau & cooldown */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
                    Niveau d'alerte
                  </label>
                  <select
                    value={form.niveau}
                    onChange={e => setForm(f => ({ ...f, niveau: e.target.value }))}
                    className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none"
                  >
                    <option value="info">ℹ️ Info</option>
                    <option value="warning">⚠️ Attention</option>
                    <option value="critical">🔴 Critique</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
                    Cooldown (heures)
                  </label>
                  <input
                    type="number" min="1" value={form.cooldown_hours}
                    onChange={e => setForm(f => ({ ...f, cooldown_hours: parseInt(e.target.value) || 4 }))}
                    className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none"
                  />
                </div>
              </div>

              {/* Emails */}
              <div>
                <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
                  Notifications email <span className="text-gray-400 font-normal">(optionnel)</span>
                </label>
                <div className="flex gap-2">
                  <input
                    type="email" value={emailInput}
                    onChange={e => setEmailInput(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), addEmail())}
                    placeholder="email@exemple.com"
                    className="flex-1 px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none"
                  />
                  <button
                    type="button" onClick={addEmail}
                    className="px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                  >
                    <Plus className="w-4 h-4" />
                  </button>
                </div>
                {form.notify_emails.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {form.notify_emails.map(email => (
                      <span
                        key={email}
                        className="flex items-center gap-1 px-2.5 py-1 text-xs bg-gray-100 dark:bg-gray-700 rounded-full text-gray-700 dark:text-gray-300"
                      >
                        <Mail className="w-3 h-3" />
                        {email}
                        <button
                          onClick={() => setForm(f => ({ ...f, notify_emails: f.notify_emails.filter(e => e !== email) }))}
                          className="text-gray-400 hover:text-red-500 ml-0.5"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Actif */}
              <label className="flex items-center gap-3 cursor-pointer p-3 rounded-lg bg-gray-50 dark:bg-gray-700/50 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">
                <input
                  type="checkbox" id="is_active" checked={form.is_active}
                  onChange={e => setForm(f => ({ ...f, is_active: e.target.checked }))}
                  className="w-4 h-4 rounded accent-primary-600"
                />
                <div>
                  <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Règle active</p>
                  <p className="text-xs text-gray-400">La règle sera évaluée lors des prochains cycles de surveillance.</p>
                </div>
              </label>
            </div>

            {/* Footer */}
            <div className="flex justify-end gap-2 p-5 border-t border-gray-200 dark:border-gray-700">
              <button
                onClick={() => setShowForm(false)}
                className="px-4 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors text-gray-700 dark:text-gray-300"
              >
                Annuler
              </button>
              <button
                onClick={saveRule} disabled={saving}
                className="px-5 py-2 text-sm rounded-lg text-white font-medium transition-colors disabled:opacity-50 flex items-center gap-1.5"
                style={{ backgroundColor: 'var(--color-primary-600)' }}
              >
                {saving ? (
                  <><RefreshCw className="w-3.5 h-3.5 animate-spin" /> Enregistrement…</>
                ) : editRule ? (
                  <><Check className="w-3.5 h-3.5" /> Mettre à jour</>
                ) : (
                  <><Plus className="w-3.5 h-3.5" /> Créer la règle</>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
