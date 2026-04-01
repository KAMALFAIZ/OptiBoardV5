import { useState, useEffect, useRef } from 'react'
import { Bell, Trash2, ToggleLeft, ToggleRight, Mail, Calendar, FileText,
         LayoutGrid, Table2, ExternalLink, Eye, Palette, X, RefreshCw,
         Settings, Save, Check, Plus, Edit2, Star, MessageSquare } from 'lucide-react'
import { Link } from 'react-router-dom'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'

const FREQ_LABEL = { daily: 'Quotidien', weekly: 'Hebdomadaire', monthly: 'Mensuel' }
const DAYS_FR    = ['Lun','Mar','Mer','Jeu','Ven','Sam','Dim']

function freqDetail(sub) {
  const h = sub.heure_envoi ?? 7
  if (sub.frequency === 'daily')   return `Chaque jour à ${h}h`
  if (sub.frequency === 'weekly')  return `${DAYS_FR[sub.jour_semaine ?? 0]} à ${h}h`
  if (sub.frequency === 'monthly') return `Le ${sub.jour_mois ?? 1} du mois à ${h}h`
  return ''
}
const FORMAT_LABEL = { excel: 'Excel', pdf: 'PDF' }

const REPORT_TYPE_CONFIG = {
  gridview:  { label: 'GridView',   icon: <Table2 className="w-4 h-4 text-blue-500" />,   href: id => `/grid/${id}` },
  dashboard: { label: 'Dashboard',  icon: <LayoutGrid className="w-4 h-4 text-emerald-500" />, href: id => `/view/${id}` },
  pivot:     { label: 'Pivot',      icon: <FileText className="w-4 h-4 text-violet-500" />, href: id => `/pivot-v2/${id}` },
}

const DEFAULT_CONTENT = {
  telegram: `📊 *{nom_app}* — Rapport Automatique\n\nBonjour 👋\n\nVotre rapport *{rapport}* est prêt.\n\n📅 Généré le {date}\n🔄 Fréquence : {frequence}\n\n_Message automatique — {nom_app}_`,
  whatsapp: `📊 *{nom_app}* — Rapport Automatique\n\nBonjour 👋\n\nVotre rapport *{rapport}* est prêt.\n\n📅 Généré le {date}\n🔄 Fréquence : {frequence}\n\n_Message automatique — {nom_app}_`,
  email: `<!DOCTYPE html>\n<html>\n<head><meta charset="utf-8"></head>\n<body style="font-family:Arial,sans-serif;color:#333;max-width:600px;margin:0 auto;padding:20px">\n  <h2 style="color:#6366f1">{nom_app} — Rapport {frequence}</h2>\n  <p>Bonjour,</p>\n  <p>Votre rapport <strong>{rapport}</strong> a été généré le {date}.</p>\n  <p style="color:#888;font-size:12px">Message automatique — {nom_app}</p>\n</body>\n</html>`,
}

const TEMPLATES_META = [
  { key: 'moderne',       label: 'Moderne',       desc: 'Design épuré avec dégradé coloré',         color: '#6366f1' },
  { key: 'professionnel', label: 'Professionnel',  desc: 'Style corporate classique, sobre et fiable', color: '#1e40af' },
  { key: 'minimaliste',   label: 'Minimaliste',    desc: 'Simple, lisible, focus sur le contenu',    color: '#374151' },
  { key: 'alerte',        label: 'Rapport Alerte', desc: 'Pour les rapports urgents avec KPIs',      color: '#dc2626' },
]

export default function MySubscriptionsPage() {
  const { user } = useAuth()
  const [tab, setTab]     = useState('subs')
  const [subs, setSubs]   = useState([])
  const [loading, setLoading] = useState(true)
  const [email, setEmail] = useState('')
  const [successMsg, setSuccessMsg] = useState('')
  const [errorMsg, setErrorMsg]     = useState('')

  // Templates email
  const [selectedTpl, setSelectedTpl]     = useState(null)
  const [previewHtml, setPreviewHtml]     = useState('')
  const [previewLoading, setPreviewLoading] = useState(false)

  // Templates personnalisés (messaging)
  const [msgTemplates, setMsgTemplates]   = useState([])
  const [tplTab, setTplTab]               = useState('email')  // email|telegram|whatsapp
  const [editingTpl, setEditingTpl]       = useState(null)     // null | {id?, nom, channel, contenu, is_default}
  const [tplPreview, setTplPreview]       = useState('')
  const [tplPreviewType, setTplPreviewType] = useState('text')
  const [tplSaving, setTplSaving]         = useState(false)

  // Paramétrage templates
  const [showConfig, setShowConfig]   = useState(false)
  const [config, setConfig]           = useState(null)
  const [configDraft, setConfigDraft] = useState(null)
  const [configSaving, setConfigSaving] = useState(false)
  const [configSaved, setConfigSaved]   = useState(false)
  const previewDebounce = useRef(null)

  useEffect(() => {
    if (user?.email) {
      setEmail(user.email)
      fetchSubscriptions(user.email)
    } else {
      setLoading(false)
    }
  }, [user])

  async function fetchSubscriptions(userEmail) {
    setLoading(true)
    try {
      const res = await api.get('/subscriptions', { params: { email: userEmail } })
      if (res.data?.success) setSubs(res.data.data || [])
    } catch { setErrorMsg('Impossible de charger les abonnements') } finally {
      setLoading(false)
    }
  }

  async function toggleSub(id) {
    try {
      await api.post(`/subscriptions/${id}/toggle`)
      setSubs(prev => prev.map(s => s.id === id ? { ...s, is_active: s.is_active ? 0 : 1 } : s))
    } catch { setErrorMsg('Erreur toggle') }
  }

  async function deleteSub(id, nom) {
    if (!confirm(`Se désabonner de "${nom}" ?`)) return
    try {
      await api.delete(`/subscriptions/${id}`)
      setSubs(prev => prev.filter(s => s.id !== id))
      flash('success', 'Désabonnement effectué')
    } catch { setErrorMsg('Erreur désabonnement') }
  }

  async function deliverNow() {
    try {
      await api.post('/subscriptions/deliver-now')
      flash('success', 'Livraison manuelle lancée — vous recevrez les rapports dans quelques instants')
    } catch { setErrorMsg('Erreur livraison') }
  }

  // Charger la config + templates au montage des onglets
  useEffect(() => {
    if (tab === 'templates' && !config) loadConfig()
    if (tab === 'msg-templates') loadMsgTemplates()
  }, [tab])

  async function loadMsgTemplates() {
    try {
      const res = await api.get('/subscriptions/message-templates')
      if (res.data?.success) setMsgTemplates(res.data.data || [])
    } catch {}
  }

  async function saveMsgTemplate() {
    if (!editingTpl?.nom?.trim() || !editingTpl?.contenu?.trim()) return
    setTplSaving(true)
    try {
      let res
      if (editingTpl.id) {
        res = await api.put(`/subscriptions/message-templates/${editingTpl.id}`, {
          nom: editingTpl.nom, contenu: editingTpl.contenu, is_default: editingTpl.is_default
        })
      } else {
        res = await api.post('/subscriptions/message-templates', editingTpl)
      }
      if (res.data?.success) {
        await loadMsgTemplates()
        setEditingTpl(null)
        setTplPreview('')
      } else {
        flash('error', res.data?.error || 'Erreur sauvegarde')
      }
    } catch { flash('error', 'Erreur réseau') } finally { setTplSaving(false) }
  }

  async function deleteMsgTemplate(id, nom) {
    if (!confirm(`Supprimer le template "${nom}" ?`)) return
    try {
      await api.delete(`/subscriptions/message-templates/${id}`)
      setMsgTemplates(prev => prev.filter(t => t.id !== id))
    } catch { flash('error', 'Erreur suppression') }
  }

  async function setDefaultMsgTemplate(id) {
    try {
      await api.post(`/subscriptions/message-templates/${id}/set-default`)
      await loadMsgTemplates()
    } catch { flash('error', 'Erreur') }
  }

  async function previewMsgTemplate(channel, contenu) {
    try {
      const res = await api.post('/subscriptions/message-templates/preview', { channel, contenu })
      if (res.data?.success) {
        setTplPreview(res.data.rendered)
        setTplPreviewType(res.data.type)
      }
    } catch {}
  }

  async function loadConfig() {
    try {
      const res = await api.get('/subscriptions/email-templates/config')
      if (res.data?.success) {
        setConfig(res.data.data)
        setConfigDraft(res.data.data)
      }
    } catch {}
  }

  async function loadTemplatePreview(key, draft) {
    setSelectedTpl(key)
    setPreviewLoading(true)
    const params = draft || configDraft || {}
    try {
      const res = await api.get(`/subscriptions/email-templates/${key}/preview`, {
        params: {
          nom_entreprise: params.nom_entreprise || undefined,
          couleur_principale: params.couleur_principale || undefined,
          texte_accueil: params.texte_accueil || undefined,
          texte_footer: params.texte_footer || undefined,
        }
      })
      if (res.data?.success) setPreviewHtml(res.data.html)
    } catch { setPreviewHtml('') } finally { setPreviewLoading(false) }
  }

  function onDraftChange(field, value) {
    const next = { ...configDraft, [field]: value }
    setConfigDraft(next)
    if (selectedTpl) {
      clearTimeout(previewDebounce.current)
      previewDebounce.current = setTimeout(() => loadTemplatePreview(selectedTpl, next), 600)
    }
  }

  async function saveConfig() {
    setConfigSaving(true)
    try {
      const res = await api.post('/subscriptions/email-templates/config', configDraft)
      if (res.data?.success) {
        setConfig(res.data.data)
        setConfigSaved(true)
        setTimeout(() => setConfigSaved(false), 2500)
      }
    } catch { flash('error', 'Erreur sauvegarde') } finally { setConfigSaving(false) }
  }

  function flash(type, msg) {
    if (type === 'success') { setSuccessMsg(msg); setTimeout(() => setSuccessMsg(''), 4000) }
    else { setErrorMsg(msg); setTimeout(() => setErrorMsg(''), 4000) }
  }

  const active = subs.filter(s => s.is_active)
  const inactive = subs.filter(s => !s.is_active)

  return (
    <div className="max-w-3xl mx-auto space-y-4">
      {/* Titre */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Bell className="w-5 h-5" style={{ color: 'var(--color-primary-600)' }} />
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">Mes Abonnements</h1>
        </div>
        {tab === 'subs' && subs.length > 0 && (
          <button
            onClick={deliverNow}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          >
            <Mail className="w-3.5 h-3.5" />
            Recevoir maintenant
          </button>
        )}
      </div>

      {/* Onglets */}
      <div className="flex gap-4 border-b border-gray-200 dark:border-gray-700">
        {[
          { key: 'subs',          label: 'Mes Abonnements',  icon: <Bell className="w-4 h-4" /> },
          { key: 'templates',     label: 'Templates Email',  icon: <Palette className="w-4 h-4" /> },
          { key: 'msg-templates', label: 'Mes Templates',    icon: <MessageSquare className="w-4 h-4" /> },
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

      {/* ── ONGLET TEMPLATES ── */}
      {tab === 'templates' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              4 styles de templates pour la livraison automatique par email.
            </p>
            <button
              onClick={() => setShowConfig(v => !v)}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border transition-colors ${
                showConfig
                  ? 'bg-indigo-50 dark:bg-indigo-900/20 border-indigo-300 dark:border-indigo-700 text-indigo-700 dark:text-indigo-300'
                  : 'border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
              }`}
            >
              <Settings className="w-3.5 h-3.5" />
              Paramétrage
            </button>
          </div>

          {/* ── Panneau Paramétrage ── */}
          {showConfig && configDraft && (
            <div className="card p-4 border border-indigo-200 dark:border-indigo-800 bg-indigo-50/40 dark:bg-indigo-900/10 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-200 flex items-center gap-1.5">
                  <Settings className="w-4 h-4 text-indigo-500" />
                  Personnalisation des emails
                </h3>
                <button
                  onClick={saveConfig}
                  disabled={configSaving}
                  className={`flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg font-medium transition-colors ${
                    configSaved
                      ? 'bg-green-100 text-green-700 border border-green-300'
                      : 'bg-indigo-600 hover:bg-indigo-700 text-white disabled:opacity-50'
                  }`}
                >
                  {configSaved ? <><Check className="w-3.5 h-3.5" />Sauvegardé</> : configSaving ? <><RefreshCw className="w-3.5 h-3.5 animate-spin" />…</> : <><Save className="w-3.5 h-3.5" />Enregistrer</>}
                </button>
              </div>

              <div className="grid grid-cols-2 gap-3">
                {/* Nom entreprise */}
                <div>
                  <label className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-1 block">
                    Nom affiché dans l'email
                  </label>
                  <input
                    type="text"
                    value={configDraft.nom_entreprise || ''}
                    onChange={e => onDraftChange('nom_entreprise', e.target.value)}
                    placeholder="OptiBoard"
                    className="w-full text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-400"
                  />
                </div>

                {/* Couleur principale */}
                <div>
                  <label className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-1 block">
                    Couleur principale
                  </label>
                  <div className="flex items-center gap-2">
                    <input
                      type="color"
                      value={configDraft.couleur_principale || '#6366f1'}
                      onChange={e => onDraftChange('couleur_principale', e.target.value)}
                      className="w-9 h-8 rounded border border-gray-300 dark:border-gray-600 cursor-pointer p-0.5"
                    />
                    <input
                      type="text"
                      value={configDraft.couleur_principale || '#6366f1'}
                      onChange={e => onDraftChange('couleur_principale', e.target.value)}
                      className="flex-1 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-400 font-mono"
                    />
                  </div>
                </div>

                {/* Template par défaut */}
                <div>
                  <label className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-1 block">
                    Template par défaut
                  </label>
                  <select
                    value={configDraft.template_defaut || 'moderne'}
                    onChange={e => onDraftChange('template_defaut', e.target.value)}
                    className="w-full text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-400"
                  >
                    {TEMPLATES_META.map(t => (
                      <option key={t.key} value={t.key}>{t.label}</option>
                    ))}
                  </select>
                </div>

                {/* Message d'accueil */}
                <div>
                  <label className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-1 block">
                    Message d'accueil
                  </label>
                  <input
                    type="text"
                    value={configDraft.texte_accueil || ''}
                    onChange={e => onDraftChange('texte_accueil', e.target.value)}
                    placeholder="Bonjour,"
                    className="w-full text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-400"
                  />
                </div>

                {/* Texte footer */}
                <div className="col-span-2">
                  <label className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-1 block">
                    Texte pied de page
                  </label>
                  <input
                    type="text"
                    value={configDraft.texte_footer || ''}
                    onChange={e => onDraftChange('texte_footer', e.target.value)}
                    placeholder="Ce message est généré automatiquement par OptiBoard."
                    className="w-full text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-400"
                  />
                </div>
              </div>

              <p className="text-xs text-indigo-500 dark:text-indigo-400">
                💡 Modifiez les champs pour voir l'aperçu se mettre à jour en temps réel.
              </p>

              {/* ── Section Telegram ── */}
              <div className="border-t border-indigo-200 dark:border-indigo-800 pt-3">
                <p className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2 flex items-center gap-1.5">
                  ✈️ Telegram
                  {configDraft.telegram_bot_token
                    ? <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-green-100 dark:bg-green-900/40 text-green-600">Configuré</span>
                    : <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-400">Non configuré</span>}
                </p>
                <div className="space-y-2">
                  <div>
                    <label className="text-xs text-gray-500 mb-1 block">Token Bot Telegram</label>
                    <input
                      type="password"
                      value={configDraft.telegram_bot_token || ''}
                      onChange={e => onDraftChange('telegram_bot_token', e.target.value)}
                      placeholder="123456789:AAF..."
                      className="w-full text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-400 font-mono"
                    />
                    <p className="text-[10px] text-gray-400 mt-1">Obtenez un token via @BotFather sur Telegram</p>
                  </div>
                  <ChannelTestButton channel="telegram" cfg={configDraft} onError={msg => flash('error', msg)} />
                </div>
              </div>

              {/* ── Section WhatsApp ── */}
              <div className="border-t border-indigo-200 dark:border-indigo-800 pt-3">
                <p className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2 flex items-center gap-1.5">
                  💬 WhatsApp (Twilio)
                  {configDraft.twilio_account_sid
                    ? <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-green-100 dark:bg-green-900/40 text-green-600">Configuré</span>
                    : <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-400">Non configuré</span>}
                </p>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-xs text-gray-500 mb-1 block">Account SID</label>
                    <input
                      type="text"
                      value={configDraft.twilio_account_sid || ''}
                      onChange={e => onDraftChange('twilio_account_sid', e.target.value)}
                      placeholder="ACxxxxxxxxxxxxxxxx"
                      className="w-full text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-400 font-mono"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-gray-500 mb-1 block">Auth Token</label>
                    <input
                      type="password"
                      value={configDraft.twilio_auth_token || ''}
                      onChange={e => onDraftChange('twilio_auth_token', e.target.value)}
                      placeholder="••••••••••••••••••"
                      className="w-full text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-400 font-mono"
                    />
                  </div>
                  <div className="col-span-2">
                    <label className="text-xs text-gray-500 mb-1 block">Numéro expéditeur WhatsApp</label>
                    <input
                      type="text"
                      value={configDraft.twilio_whatsapp_from || ''}
                      onChange={e => onDraftChange('twilio_whatsapp_from', e.target.value)}
                      placeholder="+14155238886 (Sandbox Twilio)"
                      className="w-full text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-400 font-mono"
                    />
                    <p className="text-[10px] text-gray-400 mt-1">Sandbox Twilio : +14155238886 · console.twilio.com</p>
                  </div>
                  <div className="col-span-2">
                    <ChannelTestButton channel="whatsapp" cfg={configDraft} onError={msg => flash('error', msg)} />
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Cartes templates */}
          <div className="grid grid-cols-2 gap-3">
            {TEMPLATES_META.map(tpl => (
              <button
                key={tpl.key}
                onClick={() => loadTemplatePreview(tpl.key)}
                className={`card p-4 text-left hover:shadow-md transition-all border-2 ${
                  selectedTpl === tpl.key ? 'border-primary-400' : 'border-transparent'
                }`}
              >
                <div className="flex items-center gap-3 mb-2">
                  <div
                    className="w-8 h-8 rounded-full flex-shrink-0"
                    style={{ background: tpl.key === 'moderne' && configDraft?.couleur_principale
                      ? configDraft.couleur_principale : tpl.color }}
                  />
                  <div>
                    <div className="flex items-center gap-1.5">
                      <p className="font-semibold text-sm text-gray-900 dark:text-white">{tpl.label}</p>
                      {configDraft?.template_defaut === tpl.key && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-indigo-100 dark:bg-indigo-900/40 text-indigo-600 dark:text-indigo-400 font-medium">Défaut</span>
                      )}
                    </div>
                    <p className="text-xs text-gray-400">{tpl.desc}</p>
                  </div>
                </div>
                <div className="flex items-center gap-1 text-xs mt-2"
                     style={{ color: 'var(--color-primary-600)' }}>
                  <Eye className="w-3 h-3" /> Aperçu
                </div>
              </button>
            ))}
          </div>

          {/* Preview iframe */}
          {selectedTpl && (
            <div className="card overflow-hidden">
              <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Aperçu — {TEMPLATES_META.find(t => t.key === selectedTpl)?.label}
                  {showConfig && <span className="ml-2 text-xs text-indigo-500">(avec votre personnalisation)</span>}
                </span>
                <button onClick={() => { setSelectedTpl(null); setPreviewHtml('') }}
                  className="p-1 rounded text-gray-400 hover:text-gray-600">
                  <X className="w-4 h-4" />
                </button>
              </div>
              <div className="p-2 bg-gray-100 dark:bg-gray-800">
                {previewLoading ? (
                  <div className="flex items-center justify-center py-16">
                    <RefreshCw className="w-6 h-6 animate-spin text-gray-400" />
                  </div>
                ) : previewHtml ? (
                  <iframe
                    srcDoc={previewHtml}
                    className="w-full rounded border border-gray-200 dark:border-gray-700"
                    style={{ height: '480px', background: '#fff' }}
                    title={`Aperçu template ${selectedTpl}`}
                  />
                ) : (
                  <div className="text-center py-10 text-sm text-gray-400">
                    Impossible de charger l'aperçu — redémarrez le backend
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── ONGLET ABONNEMENTS ── */}
      {tab === 'subs' && <>
      {/* Email badge */}
      {email && (
        <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
          <Mail className="w-4 h-4" />
          Abonnements pour <strong className="text-gray-700 dark:text-gray-300">{email}</strong>
        </div>
      )}

      {/* Messages */}
      {successMsg && (
        <div className="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg text-sm text-green-700 dark:text-green-300">
          {successMsg}
        </div>
      )}
      {errorMsg && (
        <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-700 dark:text-red-300">
          {errorMsg}
        </div>
      )}

      {/* Contenu */}
      {loading ? (
        <div className="flex justify-center py-16">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
        </div>
      ) : subs.length === 0 ? (
        <div className="text-center py-16 text-gray-400 dark:text-gray-500">
          <Bell className="w-12 h-12 mx-auto mb-4 opacity-30" />
          <p className="font-medium text-gray-600 dark:text-gray-400">Aucun abonnement actif</p>
          <p className="text-sm mt-2">
            Ouvrez un rapport (GridView, Dashboard ou Pivot) et cliquez sur{' '}
            <span className="font-medium text-gray-600 dark:text-gray-300">S'abonner</span>{' '}
            pour recevoir des rapports automatiquement.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Actifs */}
          {active.length > 0 && (
            <section>
              <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-2">
                Actifs ({active.length})
              </h2>
              <div className="space-y-2">
                {active.map(sub => <SubCard key={sub.id} sub={sub} onToggle={toggleSub} onDelete={deleteSub} />)}
              </div>
            </section>
          )}

          {/* Inactifs */}
          {inactive.length > 0 && (
            <section>
              <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-2">
                En pause ({inactive.length})
              </h2>
              <div className="space-y-2 opacity-60">
                {inactive.map(sub => <SubCard key={sub.id} sub={sub} onToggle={toggleSub} onDelete={deleteSub} />)}
              </div>
            </section>
          )}
        </div>
      )}

      {/* Lien vers les rapports */}
      {subs.length > 0 && (
        <p className="text-xs text-gray-400 text-center">
          Pour s'abonner à d'autres rapports, ouvrez-les depuis le menu et cliquez sur "S'abonner".
        </p>
      )}
      </>}

      {/* ── ONGLET MES TEMPLATES ── */}
      {tab === 'msg-templates' && (
        <div className="space-y-4">
          {/* Sub-tabs canal */}
          <div className="flex gap-2">
            {[
              { key: 'email',    icon: '✉️', label: 'Email' },
              { key: 'telegram', icon: '✈️', label: 'Telegram' },
              { key: 'whatsapp', icon: '💬', label: 'WhatsApp' },
            ].map(ch => (
              <button
                key={ch.key}
                onClick={() => { setTplTab(ch.key); setEditingTpl(null); setTplPreview('') }}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border font-medium transition-colors ${
                  tplTab === ch.key
                    ? 'bg-indigo-600 text-white border-indigo-600'
                    : 'border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
                }`}
              >
                <span>{ch.icon}</span>{ch.label}
                <span className="ml-1 text-[10px] opacity-70">
                  ({msgTemplates.filter(t => t.channel === ch.key).length})
                </span>
              </button>
            ))}
            <button
              onClick={() => setEditingTpl({ nom: '', channel: tplTab, contenu: DEFAULT_CONTENT[tplTab] || '', is_default: false })}
              className="ml-auto flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900 font-medium hover:bg-gray-700 dark:hover:bg-gray-200 transition-colors"
            >
              <Plus className="w-3.5 h-3.5" />
              Nouveau template
            </button>
          </div>

          {/* Formulaire création/édition */}
          {editingTpl && (
            <div className="card p-4 border border-indigo-200 dark:border-indigo-800 bg-indigo-50/30 dark:bg-indigo-900/10 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-200">
                  {editingTpl.id ? 'Modifier le template' : 'Nouveau template'} — {tplTab}
                </h3>
                <button onClick={() => { setEditingTpl(null); setTplPreview('') }} className="text-gray-400 hover:text-gray-600">
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="col-span-2">
                  <label className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-1 block">Nom du template</label>
                  <input
                    type="text"
                    value={editingTpl.nom}
                    onChange={e => setEditingTpl(p => ({ ...p, nom: e.target.value }))}
                    placeholder="Ex: Template Standard, Alerte Ventes…"
                    className="w-full text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-400"
                  />
                </div>

                <div className="col-span-2">
                  <div className="flex items-center justify-between mb-1">
                    <label className="text-xs font-medium text-gray-600 dark:text-gray-400">
                      Contenu {tplTab === 'email' ? '(HTML)' : '(texte — supports *gras*, _italique_)'}
                    </label>
                    <div className="flex gap-1">
                      {['{nom_app}','{rapport}','{frequence}','{date}'].map(v => (
                        <button
                          key={v}
                          type="button"
                          onClick={() => setEditingTpl(p => ({ ...p, contenu: (p.contenu || '') + v }))}
                          className="text-[10px] px-1.5 py-0.5 rounded bg-indigo-100 dark:bg-indigo-900/40 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-200 font-mono"
                        >
                          {v}
                        </button>
                      ))}
                    </div>
                  </div>
                  <textarea
                    value={editingTpl.contenu}
                    onChange={e => setEditingTpl(p => ({ ...p, contenu: e.target.value }))}
                    rows={tplTab === 'email' ? 10 : 6}
                    className="w-full text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-400 font-mono resize-y"
                    placeholder={tplTab === 'email' ? '<!DOCTYPE html>…' : 'Bonjour 👋\n\nVotre rapport *{rapport}* est prêt…'}
                  />
                </div>

                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="tpl-default"
                    checked={!!editingTpl.is_default}
                    onChange={e => setEditingTpl(p => ({ ...p, is_default: e.target.checked }))}
                    className="rounded border-gray-300"
                  />
                  <label htmlFor="tpl-default" className="text-xs text-gray-600 dark:text-gray-400">
                    Définir comme template par défaut pour {tplTab}
                  </label>
                </div>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() => previewMsgTemplate(tplTab, editingTpl.contenu)}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                >
                  <Eye className="w-3.5 h-3.5" />
                  Aperçu
                </button>
                <button
                  onClick={saveMsgTemplate}
                  disabled={tplSaving || !editingTpl.nom.trim() || !editingTpl.contenu.trim()}
                  className="flex items-center gap-1.5 px-4 py-1.5 text-xs rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-medium disabled:opacity-40 transition-colors ml-auto"
                >
                  {tplSaving ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                  {editingTpl.id ? 'Mettre à jour' : 'Créer'}
                </button>
              </div>

              {/* Aperçu */}
              {tplPreview && (
                <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
                  <div className="px-3 py-2 bg-gray-100 dark:bg-gray-700 text-xs font-medium text-gray-600 dark:text-gray-300 flex items-center gap-1.5">
                    <Eye className="w-3 h-3" /> Aperçu avec données d'exemple
                  </div>
                  {tplPreviewType === 'html' ? (
                    <iframe srcDoc={tplPreview} className="w-full" style={{ height: 400, background: '#fff' }} title="preview" />
                  ) : (
                    <pre className="p-4 text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap bg-white dark:bg-gray-800 font-sans">
                      {tplPreview}
                    </pre>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Liste des templates existants */}
          {msgTemplates.filter(t => t.channel === tplTab).length === 0 && !editingTpl ? (
            <div className="text-center py-12 text-gray-400 dark:text-gray-500">
              <MessageSquare className="w-10 h-10 mx-auto mb-3 opacity-30" />
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Aucun template {tplTab}</p>
              <p className="text-xs mt-1">Cliquez sur "Nouveau template" pour en créer un.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {msgTemplates.filter(t => t.channel === tplTab).map(tpl => (
                <div key={tpl.id} className="card p-4 flex items-start gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-semibold text-sm text-gray-900 dark:text-white">{tpl.nom}</span>
                      {tpl.is_default ? (
                        <span className="flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900/40 text-amber-600 dark:text-amber-400 font-medium">
                          <Star className="w-2.5 h-2.5 fill-current" /> Défaut
                        </span>
                      ) : null}
                    </div>
                    <pre className="text-xs text-gray-400 mt-1 truncate font-sans" style={{ maxWidth: '40ch' }}>
                      {tpl.contenu?.slice(0, 80)}{tpl.contenu?.length > 80 ? '…' : ''}
                    </pre>
                    <p className="text-[10px] text-gray-400 mt-1">
                      Créé le {new Date(tpl.created_at).toLocaleDateString('fr-FR')}
                    </p>
                  </div>
                  <div className="flex items-center gap-1 flex-shrink-0">
                    {!tpl.is_default && (
                      <button
                        onClick={() => setDefaultMsgTemplate(tpl.id)}
                        title="Définir par défaut"
                        className="p-1.5 rounded hover:bg-amber-50 dark:hover:bg-amber-900/20 text-gray-400 hover:text-amber-500 transition-colors"
                      >
                        <Star className="w-3.5 h-3.5" />
                      </button>
                    )}
                    <button
                      onClick={() => { setEditingTpl({ ...tpl, is_default: !!tpl.is_default }); setTplPreview('') }}
                      title="Modifier"
                      className="p-1.5 rounded hover:bg-indigo-50 dark:hover:bg-indigo-900/20 text-gray-400 hover:text-indigo-500 transition-colors"
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => deleteMsgTemplate(tpl.id, tpl.nom)}
                      title="Supprimer"
                      className="p-1.5 rounded hover:bg-red-50 dark:hover:bg-red-900/20 text-gray-400 hover:text-red-500 transition-colors"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

const CHANNEL_CONFIG = {
  email:    { icon: '✉️', label: 'Email',     color: 'text-blue-500' },
  whatsapp: { icon: '💬', label: 'WhatsApp',  color: 'text-green-500' },
  telegram: { icon: '✈️', label: 'Telegram',  color: 'text-sky-500' },
}

function ChannelTestButton({ channel, cfg, onError }) {
  const [testPhone, setTestPhone] = useState('')
  const [testing, setTesting]     = useState(false)
  const [testResult, setTestResult] = useState(null)

  async function runTest() {
    if (!testPhone.trim()) return
    setTesting(true); setTestResult(null)
    try {
      // Save config first so backend has latest tokens
      await api.post('/subscriptions/email-templates/config', cfg)
      const res = await api.post('/subscriptions/channels/test', {
        channel, contact_info: testPhone.trim()
      })
      setTestResult(res.data?.success ? 'ok' : res.data?.error || 'Échec')
    } catch (e) {
      setTestResult(e?.response?.data?.detail || 'Erreur réseau')
    } finally {
      setTesting(false)
      setTimeout(() => setTestResult(null), 5000)
    }
  }

  const placeholder = channel === 'telegram' ? 'Chat ID ex: 123456789' : 'Numéro ex: +212600...'

  return (
    <div className="flex items-center gap-2">
      <input
        type="text"
        value={testPhone}
        onChange={e => setTestPhone(e.target.value)}
        placeholder={placeholder}
        className="flex-1 text-xs rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-indigo-400"
      />
      <button
        onClick={runTest}
        disabled={testing || !testPhone.trim()}
        className="flex items-center gap-1 px-2.5 py-1.5 text-xs rounded-lg bg-gray-800 dark:bg-gray-600 text-white hover:bg-gray-700 disabled:opacity-40 transition-colors whitespace-nowrap"
      >
        {testing ? <RefreshCw className="w-3 h-3 animate-spin" /> : null}
        Tester
      </button>
      {testResult && (
        <span className={`text-[10px] font-medium ${testResult === 'ok' ? 'text-green-600' : 'text-red-500'}`}>
          {testResult === 'ok' ? '✓ Envoyé' : `✗ ${testResult}`}
        </span>
      )}
    </div>
  )
}

function SubCard({ sub, onToggle, onDelete }) {
  const typeConf = REPORT_TYPE_CONFIG[sub.report_type] || REPORT_TYPE_CONFIG.gridview
  const href = typeConf.href(sub.report_id)
  const chanConf = CHANNEL_CONFIG[sub.channel || 'email'] || CHANNEL_CONFIG.email

  return (
    <div className={`card p-4 flex items-center gap-4`}>
      {/* Icône type */}
      <div className="p-2 rounded-lg bg-gray-100 dark:bg-gray-700 flex-shrink-0">
        {typeConf.icon}
      </div>

      {/* Infos */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <Link
            to={href}
            className="font-semibold text-gray-900 dark:text-white text-sm hover:underline flex items-center gap-1"
          >
            {sub.report_nom}
            <ExternalLink className="w-3 h-3 opacity-50" />
          </Link>
          <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-500">
            {typeConf.label}
          </span>
        </div>
        <div className="flex items-center gap-3 mt-1 text-xs text-gray-500 dark:text-gray-400 flex-wrap">
          <span className={`flex items-center gap-1 font-medium ${chanConf.color}`}>
            <span>{chanConf.icon}</span>
            {chanConf.label}
            {sub.contact_info && sub.channel !== 'email' && (
              <span className="text-gray-400 font-normal">· {sub.contact_info}</span>
            )}
          </span>
          <span className="flex items-center gap-1">
            <Calendar className="w-3 h-3" />
            {FREQ_LABEL[sub.frequency] || sub.frequency} — {freqDetail(sub)}
          </span>
          <span className="flex items-center gap-1">
            <FileText className="w-3 h-3" />
            {FORMAT_LABEL[sub.export_format] || sub.export_format}
          </span>
          {(sub.date_debut || sub.date_fin) && (
            <span className="flex items-center gap-1 text-amber-500">
              📅 {sub.date_debut ? new Date(sub.date_debut).toLocaleDateString('fr-FR') : '…'}
              {' → '}
              {sub.date_fin ? new Date(sub.date_fin).toLocaleDateString('fr-FR') : '∞'}
            </span>
          )}
          {sub.last_sent && (
            <span className="text-gray-400">
              Dernière : {new Date(sub.last_sent).toLocaleDateString('fr-FR')}
            </span>
          )}
          {sub.next_send && sub.is_active && (
            <span className="text-gray-400">
              Prochaine : {new Date(sub.next_send).toLocaleDateString('fr-FR')}
            </span>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-1 flex-shrink-0">
        <button
          onClick={() => onToggle(sub.id)}
          className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          title={sub.is_active ? 'Mettre en pause' : 'Réactiver'}
        >
          {sub.is_active
            ? <ToggleRight className="w-4 h-4" style={{ color: 'var(--color-primary-500)' }} />
            : <ToggleLeft className="w-4 h-4 text-gray-400" />
          }
        </button>
        <button
          onClick={() => onDelete(sub.id, sub.report_nom)}
          className="p-1.5 rounded hover:bg-red-50 dark:hover:bg-red-900/20 text-gray-400 hover:text-red-500 transition-colors"
          title="Se désabonner"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}
