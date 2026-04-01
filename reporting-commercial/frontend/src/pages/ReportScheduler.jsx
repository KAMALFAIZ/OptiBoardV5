import { useState, useEffect, useMemo } from 'react'
import {
  Calendar, Clock, Mail, Send, Plus, Edit2, Trash2, Play, Pause,
  FileSpreadsheet, Table2, LayoutDashboard, Download, Settings,
  CheckCircle, XCircle, AlertCircle, RefreshCw, History, Users,
  ChevronDown, ChevronRight, Save, X, TestTube,
  Tag, Copy, Zap, TrendingUp, AlertTriangle, Eye, Filter
} from 'lucide-react'

// API calls
const API_BASE = '/api/report-scheduler'

const api = {
  getSchedules: () => fetch(`${API_BASE}/schedules`).then(r => r.json()),
  getSchedule: (id) => fetch(`${API_BASE}/schedules/${id}`).then(r => r.json()),
  createSchedule: (data) => fetch(`${API_BASE}/schedules`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }).then(r => r.json()),
  updateSchedule: (id, data) => fetch(`${API_BASE}/schedules/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }).then(r => r.json()),
  deleteSchedule: (id) => fetch(`${API_BASE}/schedules/${id}`, { method: 'DELETE' }).then(r => r.json()),
  toggleSchedule: (id) => fetch(`${API_BASE}/schedules/${id}/toggle`, { method: 'POST' }).then(r => r.json()),
  runNow: (id) => fetch(`${API_BASE}/schedules/${id}/run-now`, { method: 'POST' }).then(r => r.json()),
  duplicateSchedule: (id) => fetch(`${API_BASE}/schedules/${id}/duplicate`, { method: 'POST' }).then(r => r.json()),
  getHistory: (limit = 100) => fetch(`${API_BASE}/history?limit=${limit}`).then(r => r.json()),
  getHistoryFiltered: (params) => fetch(`${API_BASE}/history?${new URLSearchParams(params)}`).then(r => r.json()),
  getHistoryStats: () => fetch(`${API_BASE}/history/stats`).then(r => r.json()),
  getAvailableReports: () => fetch(`${API_BASE}/available-reports`).then(r => r.json()),
  getUsersWithEmails: () => fetch(`${API_BASE}/users-with-emails`).then(r => r.json()),
  getEmailConfig: () => fetch(`${API_BASE}/email-config`).then(r => r.json()),
  saveEmailConfig: (data) => fetch(`${API_BASE}/email-config`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }).then(r => r.json()),
  testEmailConfig: (data) => fetch(`${API_BASE}/email-config/test`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }).then(r => r.json()),
  sendTestEmail: (email) => fetch(`${API_BASE}/email-config/send-test?to_email=${encodeURIComponent(email)}`, { method: 'POST' }).then(r => r.json()),
}

const FREQUENCY_OPTIONS = [
  { value: 'daily', label: 'Quotidien', icon: Calendar },
  { value: 'weekly', label: 'Hebdomadaire', icon: Calendar },
  { value: 'monthly', label: 'Mensuel', icon: Calendar },
  { value: 'once', label: 'Une fois', icon: Clock },
]

const DAYS_OF_WEEK = [
  { value: 1, label: 'Lun' },
  { value: 2, label: 'Mar' },
  { value: 3, label: 'Mer' },
  { value: 4, label: 'Jeu' },
  { value: 5, label: 'Ven' },
  { value: 6, label: 'Sam' },
  { value: 7, label: 'Dim' },
]

const DAYS_OF_WEEK_FULL = [
  { value: 1, label: 'Lundi' },
  { value: 2, label: 'Mardi' },
  { value: 3, label: 'Mercredi' },
  { value: 4, label: 'Jeudi' },
  { value: 5, label: 'Vendredi' },
  { value: 6, label: 'Samedi' },
  { value: 7, label: 'Dimanche' },
]

const REPORT_TYPE_ICONS = {
  pivot: Table2,
  gridview: FileSpreadsheet,
  dashboard: LayoutDashboard,
  export: Download,
}

// ==================== TOAST SYSTEM ====================

function Toast({ toasts, remove }) {
  return (
    <div className="fixed bottom-4 right-4 z-[100] space-y-2">
      {toasts.map(t => (
        <div
          key={t.id}
          className={`flex items-center gap-3 px-4 py-3 rounded-xl shadow-lg text-sm font-medium text-white max-w-sm transition-all
            ${t.type === 'success' ? 'bg-green-600' : t.type === 'error' ? 'bg-red-600' : 'bg-gray-800'}`}
        >
          {t.type === 'success'
            ? <CheckCircle className="w-4 h-4 shrink-0" />
            : t.type === 'error'
              ? <XCircle className="w-4 h-4 shrink-0" />
              : <AlertTriangle className="w-4 h-4 shrink-0" />
          }
          <span>{t.message}</span>
          <button onClick={() => remove(t.id)} className="ml-auto opacity-70 hover:opacity-100">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      ))}
    </div>
  )
}

// ==================== MAIN COMPONENT ====================

export default function ReportScheduler() {
  const [activeTab, setActiveTab] = useState('schedules')
  const [schedules, setSchedules] = useState([])
  const [history, setHistory] = useState([])
  const [historyStats, setHistoryStats] = useState({})
  const [availableReports, setAvailableReports] = useState({})
  const [availableUsers, setAvailableUsers] = useState([])
  const [emailConfig, setEmailConfig] = useState(null)
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editingSchedule, setEditingSchedule] = useState(null)
  const [showEmailConfig, setShowEmailConfig] = useState(false)

  // Filtres liste schedules
  const [searchText, setSearchText] = useState('')
  const [filterActiveOnly, setFilterActiveOnly] = useState(false)
  const [sortBy, setSortBy] = useState('nom') // nom | next_run | success_rate

  // Filtres historique
  const [historyFilterSchedule, setHistoryFilterSchedule] = useState('')
  const [historyFilterStatus, setHistoryFilterStatus] = useState('')

  // Toast system
  const [toasts, setToasts] = useState([])
  const toast = (message, type = 'success') => {
    const id = Date.now()
    setToasts(p => [...p, { id, message, type }])
    setTimeout(() => setToasts(p => p.filter(t => t.id !== id)), 4000)
  }
  const removeToast = (id) => setToasts(p => p.filter(t => t.id !== id))

  useEffect(() => { loadData() }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const [schedulesRes, historyRes, statsRes, reportsRes, usersRes, emailRes] = await Promise.all([
        api.getSchedules(),
        api.getHistory(),
        api.getHistoryStats(),
        api.getAvailableReports(),
        api.getUsersWithEmails(),
        api.getEmailConfig(),
      ])
      if (schedulesRes.success) setSchedules(schedulesRes.data || [])
      if (historyRes.success) setHistory(historyRes.data || [])
      if (statsRes.success) setHistoryStats(statsRes.data || {})
      if (reportsRes.success) setAvailableReports(reportsRes.data || {})
      if (usersRes.success) setAvailableUsers(usersRes.data || [])
      if (emailRes.success) setEmailConfig(emailRes.data)
    } catch (error) {
      console.error('Erreur chargement:', error)
    }
    setLoading(false)
  }

  const handleToggle = async (id) => {
    const result = await api.toggleSchedule(id)
    if (result.success) {
      setSchedules(prev => prev.map(s => s.id === id ? { ...s, is_active: result.is_active } : s))
      toast(result.is_active ? 'Schedule activé' : 'Schedule mis en pause')
    } else {
      toast('Erreur lors du changement de statut', 'error')
    }
  }

  const handleRunNow = async (id) => {
    const result = await api.runNow(id)
    if (result.success) {
      toast('Exécution lancée en arrière-plan')
      setTimeout(loadData, 2000)
    } else {
      toast('Erreur : ' + result.error, 'error')
    }
  }

  const handleDelete = async (id, nom) => {
    if (!window.confirm(`Supprimer le rapport planifié "${nom}" ?`)) return
    const result = await api.deleteSchedule(id)
    if (result.success) {
      setSchedules(prev => prev.filter(s => s.id !== id))
      toast('Schedule supprimé')
    } else {
      toast('Erreur lors de la suppression', 'error')
    }
  }

  const handleDuplicate = async (id) => {
    const result = await api.duplicateSchedule(id)
    if (result.success) {
      toast('Schedule dupliqué avec succès')
      loadData()
    } else {
      toast('Erreur lors de la duplication : ' + result.error, 'error')
    }
  }

  const handleEdit = (schedule) => {
    setEditingSchedule(schedule)
    setShowModal(true)
  }

  const handleCreate = () => {
    setEditingSchedule(null)
    setShowModal(true)
  }

  // Schedules filtrés et triés
  const filteredSchedules = useMemo(() => {
    let list = [...schedules]
    if (searchText) {
      const q = searchText.toLowerCase()
      list = list.filter(s => s.nom.toLowerCase().includes(q) || (s.tags || '').toLowerCase().includes(q))
    }
    if (filterActiveOnly) {
      list = list.filter(s => s.is_active)
    }
    list.sort((a, b) => {
      if (sortBy === 'nom') return a.nom.localeCompare(b.nom)
      if (sortBy === 'next_run') {
        if (!a.next_run) return 1
        if (!b.next_run) return -1
        return new Date(a.next_run) - new Date(b.next_run)
      }
      if (sortBy === 'success_rate') {
        const rateA = a.run_count > 0 ? a.success_count / a.run_count : 0
        const rateB = b.run_count > 0 ? b.success_count / b.run_count : 0
        return rateB - rateA
      }
      return 0
    })
    return list
  }, [schedules, searchText, filterActiveOnly, sortBy])

  // Historique filtré
  const filteredHistory = useMemo(() => {
    let list = [...history]
    if (historyFilterSchedule) list = list.filter(h => String(h.schedule_id) === historyFilterSchedule)
    if (historyFilterStatus) list = list.filter(h => h.status === historyFilterStatus)
    return list
  }, [history, historyFilterSchedule, historyFilterStatus])

  // Stats globales
  const globalStats = historyStats.global || {}

  return (
    <div className="space-y-6">
      <Toast toasts={toasts} remove={removeToast} />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
            <Mail className="w-7 h-7" style={{ color: 'var(--color-primary-600)' }} />
            Envois Planifiés
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1 text-sm">
            L'admin crée des envois automatiques vers une liste de destinataires (Push) · Email uniquement · Filtres disponibles
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowEmailConfig(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <Settings className="w-4 h-4" />
            Config Email
          </button>
          <button
            onClick={handleCreate}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-white"
            style={{ backgroundColor: 'var(--color-primary-600)' }}
          >
            <Plus className="w-4 h-4" />
            Nouveau
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <StatCard icon={Calendar} label="Rapports Actifs" value={schedules.filter(s => s.is_active).length} color="primary" />
        <StatCard icon={Send} label="Envoyés (30j)" value={globalStats.total || 0} color="blue" />
        <StatCard icon={CheckCircle} label="Succès" value={globalStats.success || 0} color="green" />
        <StatCard icon={XCircle} label="Erreurs" value={globalStats.errors || 0} color="red" />
        <StatCard
          icon={TrendingUp}
          label="Taux de succès"
          value={globalStats.total > 0 ? `${Math.round((globalStats.success / globalStats.total) * 100)}%` : '—'}
          color="amber"
        />
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="flex gap-4">
          <TabButton active={activeTab === 'schedules'} onClick={() => setActiveTab('schedules')}>
            <Calendar className="w-4 h-4" />
            Programmations
          </TabButton>
          <TabButton active={activeTab === 'history'} onClick={() => setActiveTab('history')}>
            <History className="w-4 h-4" />
            Historique
          </TabButton>
          <TabButton active={activeTab === 'stats'} onClick={() => setActiveTab('stats')}>
            <TrendingUp className="w-4 h-4" />
            Statistiques
          </TabButton>
        </nav>
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="w-8 h-8 animate-spin text-gray-400" />
        </div>
      ) : activeTab === 'schedules' ? (
        <>
          {/* Barre filtres/recherche */}
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex-1 min-w-48 relative">
              <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Rechercher par nom ou tag..."
                value={searchText}
                onChange={e => setSearchText(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
              />
            </div>
            <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={filterActiveOnly}
                onChange={e => setFilterActiveOnly(e.target.checked)}
                className="rounded border-gray-300"
              />
              Actifs seulement
            </label>
            <select
              value={sortBy}
              onChange={e => setSortBy(e.target.value)}
              className="px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
            >
              <option value="nom">Tri : Par nom</option>
              <option value="next_run">Tri : Par prochain envoi</option>
              <option value="success_rate">Tri : Par taux de succès</option>
            </select>
            <span className="text-sm text-gray-500 dark:text-gray-400">{filteredSchedules.length} résultat(s)</span>
          </div>

          <SchedulesList
            schedules={filteredSchedules}
            onToggle={handleToggle}
            onRunNow={handleRunNow}
            onEdit={handleEdit}
            onDelete={handleDelete}
            onDuplicate={handleDuplicate}
          />
        </>
      ) : activeTab === 'history' ? (
        <HistoryList
          history={filteredHistory}
          schedules={schedules}
          filterSchedule={historyFilterSchedule}
          filterStatus={historyFilterStatus}
          onFilterSchedule={setHistoryFilterSchedule}
          onFilterStatus={setHistoryFilterStatus}
          onRefresh={loadData}
        />
      ) : (
        <StatsPanel stats={historyStats} />
      )}

      {/* Modal schedule */}
      {showModal && (
        <ScheduleModal
          schedule={editingSchedule}
          availableReports={availableReports}
          availableUsers={availableUsers}
          onClose={() => setShowModal(false)}
          onSave={async (data) => {
            const result = editingSchedule
              ? await api.updateSchedule(editingSchedule.id, data)
              : await api.createSchedule(data)
            if (result.success) {
              setShowModal(false)
              loadData()
              toast(editingSchedule ? 'Schedule mis à jour' : 'Schedule créé avec succès')
            } else {
              toast('Erreur : ' + result.error, 'error')
            }
          }}
        />
      )}

      {/* Email Config Modal */}
      {showEmailConfig && (
        <EmailConfigModal
          config={emailConfig}
          onClose={() => setShowEmailConfig(false)}
          onSave={async (data) => {
            const result = await api.saveEmailConfig(data)
            if (result.success) {
              setShowEmailConfig(false)
              loadData()
              toast('Configuration email sauvegardée')
            } else {
              toast('Erreur : ' + result.error, 'error')
            }
          }}
          onTest={api.testEmailConfig}
          onSendTest={api.sendTestEmail}
          toast={toast}
        />
      )}
    </div>
  )
}

// ==================== STAT CARD ====================

function StatCard({ icon: Icon, label, value, color }) {
  const colors = {
    primary: 'bg-primary-100 text-primary-600 dark:bg-primary-900/30 dark:text-primary-400',
    blue: 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400',
    green: 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400',
    red: 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400',
    amber: 'bg-amber-100 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400',
  }
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-lg ${colors[color]}`}>
          <Icon className="w-5 h-5" />
        </div>
        <div>
          <p className="text-2xl font-bold text-gray-900 dark:text-white">{value}</p>
          <p className="text-sm text-gray-500 dark:text-gray-400">{label}</p>
        </div>
      </div>
    </div>
  )
}

function TabButton({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-4 py-3 border-b-2 font-medium text-sm transition-colors ${
        active
          ? 'border-primary-600 text-primary-600'
          : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400'
      }`}
    >
      {children}
    </button>
  )
}

// ==================== SCHEDULES LIST ====================

function SchedulesList({ schedules, onToggle, onRunNow, onEdit, onDelete, onDuplicate }) {
  if (schedules.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500 dark:text-gray-400">
        <Mail className="w-12 h-12 mx-auto mb-4 opacity-50" />
        <p>Aucun rapport planifié</p>
        <p className="text-sm mt-1">Cliquez sur "Nouveau" pour créer votre premier rapport automatique</p>
      </div>
    )
  }
  return (
    <div className="space-y-3">
      {schedules.map(schedule => (
        <ScheduleCard
          key={schedule.id}
          schedule={schedule}
          onToggle={() => onToggle(schedule.id)}
          onRunNow={() => onRunNow(schedule.id)}
          onEdit={() => onEdit(schedule)}
          onDelete={() => onDelete(schedule.id, schedule.nom)}
          onDuplicate={() => onDuplicate(schedule.id)}
        />
      ))}
    </div>
  )
}

// ==================== SCHEDULE CARD ====================

function ScheduleCard({ schedule, onToggle, onRunNow, onEdit, onDelete, onDuplicate }) {
  const Icon = REPORT_TYPE_ICONS[schedule.report_type] || FileSpreadsheet
  const now = new Date()

  // Badge statut
  const isExpired = schedule.date_fin && new Date(schedule.date_fin) < now
  const statusBadge = isExpired
    ? <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400">Expiré</span>
    : schedule.is_active
      ? <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">Actif</span>
      : <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400">Pausé</span>

  // Badge fréquence
  const freqLabel = () => {
    const day = schedule.schedule_day
    const time = schedule.schedule_time || '—'
    if (schedule.frequency === 'daily') return `Chaque jour ${time}`
    if (schedule.frequency === 'weekly') {
      const d = DAYS_OF_WEEK_FULL.find(d => d.value === day)
      return `${d ? d.label : 'Hebdo'} ${time}`
    }
    if (schedule.frequency === 'monthly') return `${day || 1}er du mois ${time}`
    if (schedule.frequency === 'once') return `Une fois ${time}`
    return time
  }

  // Badge next_run
  const nextRunBadge = () => {
    if (!schedule.next_run) return null
    const nr = new Date(schedule.next_run)
    const today = new Date(); today.setHours(0,0,0,0)
    const nrDay = new Date(nr); nrDay.setHours(0,0,0,0)
    if (nr < now) {
      return <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400">En retard</span>
    }
    if (nrDay.getTime() === today.getTime()) {
      return <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">Aujourd'hui</span>
    }
    return <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">{nr.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short' })}</span>
  }

  // Mini barre succès
  const successBar = () => {
    const total = schedule.run_count || 0
    if (total === 0) return null
    const rate = Math.round(((schedule.success_count || 0) / total) * 100)
    return (
      <div className="flex items-center gap-2 mt-1">
        <div className="w-20 h-1.5 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full ${rate >= 80 ? 'bg-green-500' : rate >= 50 ? 'bg-amber-500' : 'bg-red-500'}`}
            style={{ width: `${rate}%` }}
          />
        </div>
        <span className="text-xs text-gray-500 dark:text-gray-400">{rate}% succès ({total} envois)</span>
      </div>
    )
  }

  // Chips destinataires
  const recipientsChips = () => {
    const list = schedule.recipients || []
    const shown = list.slice(0, 3)
    const rest = list.length - 3
    return (
      <div className="flex flex-wrap gap-1 mt-1">
        {shown.map(e => (
          <span key={e} className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded text-xs">• {e}</span>
        ))}
        {rest > 0 && (
          <span className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 rounded text-xs">+{rest}</span>
        )}
      </div>
    )
  }

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-lg border ${
      isExpired ? 'border-red-200 dark:border-red-800 opacity-70'
      : schedule.is_active ? 'border-gray-200 dark:border-gray-700'
      : 'border-gray-300 dark:border-gray-600 opacity-60'
    } p-4`}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-4 flex-1 min-w-0">
          <div className={`p-3 rounded-lg shrink-0 ${schedule.is_active && !isExpired ? 'bg-primary-100 dark:bg-primary-900/30' : 'bg-gray-100 dark:bg-gray-700'}`}>
            <Icon className={`w-6 h-6 ${schedule.is_active && !isExpired ? 'text-primary-600 dark:text-primary-400' : 'text-gray-400'}`} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="font-semibold text-gray-900 dark:text-white truncate">{schedule.nom}</h3>
              {statusBadge}
              <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300">
                {freqLabel()}
              </span>
              {nextRunBadge()}
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
              {schedule.report_name || `${schedule.report_type} #${schedule.report_id}`}
            </p>
            {/* Tags */}
            {schedule.tags && (
              <div className="flex flex-wrap gap-1 mt-1">
                {schedule.tags.split(',').map(t => t.trim()).filter(Boolean).map(t => (
                  <span key={t} className="flex items-center gap-1 px-1.5 py-0.5 bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300 rounded text-xs">
                    <Tag className="w-2.5 h-2.5" />{t}
                  </span>
                ))}
              </div>
            )}
            {successBar()}
            {recipientsChips()}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1 shrink-0">
          <button
            onClick={onToggle}
            className={`p-2 rounded-lg transition-colors ${
              schedule.is_active
                ? 'bg-green-100 text-green-600 hover:bg-green-200 dark:bg-green-900/30 dark:text-green-400'
                : 'bg-gray-100 text-gray-400 hover:bg-gray-200 dark:bg-gray-700'
            }`}
            title={schedule.is_active ? 'Désactiver' : 'Activer'}
          >
            {schedule.is_active ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
          </button>
          <button
            onClick={onRunNow}
            className="p-2 rounded-lg bg-blue-100 text-blue-600 hover:bg-blue-200 dark:bg-blue-900/30 dark:text-blue-400"
            title="Exécuter maintenant"
          >
            <Send className="w-4 h-4" />
          </button>
          <button
            onClick={onEdit}
            className="p-2 rounded-lg bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-400"
            title="Modifier"
          >
            <Edit2 className="w-4 h-4" />
          </button>
          <button
            onClick={onDuplicate}
            className="p-2 rounded-lg bg-amber-100 text-amber-600 hover:bg-amber-200 dark:bg-amber-900/30 dark:text-amber-400"
            title="Dupliquer"
          >
            <Copy className="w-4 h-4" />
          </button>
          <button
            onClick={onDelete}
            className="p-2 rounded-lg bg-red-100 text-red-600 hover:bg-red-200 dark:bg-red-900/30 dark:text-red-400"
            title="Supprimer"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}

// ==================== HISTORY LIST ====================

function HistoryList({ history, schedules, filterSchedule, filterStatus, onFilterSchedule, onFilterStatus, onRefresh }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700 flex-wrap gap-3">
        <h3 className="font-semibold text-gray-900 dark:text-white">Historique des envois</h3>
        <div className="flex items-center gap-2 flex-wrap">
          {/* Filtre schedule */}
          <select
            value={filterSchedule}
            onChange={e => onFilterSchedule(e.target.value)}
            className="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option value="">Tous les schedules</option>
            {schedules.map(s => (
              <option key={s.id} value={String(s.id)}>{s.nom}</option>
            ))}
          </select>
          {/* Filtre statut */}
          <select
            value={filterStatus}
            onChange={e => onFilterStatus(e.target.value)}
            className="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option value="">Tous statuts</option>
            <option value="success">Succès</option>
            <option value="error">Erreurs</option>
          </select>
          <button onClick={onRefresh} className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg" title="Actualiser">
            <RefreshCw className="w-4 h-4 text-gray-500" />
          </button>
        </div>
      </div>
      {history.length === 0 ? (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">Aucun envoi enregistré</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-700/50 text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">
              <tr>
                <th className="px-4 py-2 text-left">Statut</th>
                <th className="px-4 py-2 text-left">Schedule</th>
                <th className="px-4 py-2 text-left">Destinataires</th>
                <th className="px-4 py-2 text-left">Taille</th>
                <th className="px-4 py-2 text-left">Date</th>
                <th className="px-4 py-2 text-left">Erreur</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {history.map(item => (
                <tr key={item.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                  <td className="px-4 py-2">
                    {item.status === 'success'
                      ? <CheckCircle className="w-5 h-5 text-green-500" />
                      : <XCircle className="w-5 h-5 text-red-500" />
                    }
                  </td>
                  <td className="px-4 py-2 text-gray-900 dark:text-white font-medium">
                    {item.report_name || item.schedule_name || '—'}
                  </td>
                  <td className="px-4 py-2 text-gray-500 dark:text-gray-400">
                    {item.recipients?.length || 0} dest.
                  </td>
                  <td className="px-4 py-2 text-gray-500 dark:text-gray-400">
                    {item.file_size ? `${Math.round(item.file_size / 1024)} Ko` : '—'}
                  </td>
                  <td className="px-4 py-2 text-gray-500 dark:text-gray-400 whitespace-nowrap">
                    {new Date(item.sent_at).toLocaleString('fr-FR')}
                  </td>
                  <td className="px-4 py-2">
                    {item.error_message && (
                      <span className="text-red-500 text-xs truncate max-w-xs block" title={item.error_message}>
                        {item.error_message.slice(0, 60)}{item.error_message.length > 60 ? '…' : ''}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

// ==================== STATS PANEL ====================

function StatsPanel({ stats }) {
  const perSchedule = stats.per_schedule || []
  const trend = stats.trend || []
  const maxTotal = trend.reduce((m, d) => Math.max(m, d.total), 1)

  return (
    <div className="space-y-6">
      {/* Tableau par schedule */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
          <h3 className="font-semibold text-gray-900 dark:text-white">Performances par schedule (30 derniers jours)</h3>
        </div>
        {perSchedule.length === 0 ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">Pas encore de données</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-700/50 text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">
              <tr>
                <th className="px-4 py-2 text-left">Nom</th>
                <th className="px-4 py-2 text-right">Total envois</th>
                <th className="px-4 py-2 text-right">Succès</th>
                <th className="px-4 py-2 text-right">Taux</th>
                <th className="px-4 py-2 text-left">Progression</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {perSchedule.map(row => {
                const rate = row.total > 0 ? Math.round((row.success / row.total) * 100) : 0
                return (
                  <tr key={row.schedule_id} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                    <td className="px-4 py-2 text-gray-900 dark:text-white font-medium">{row.nom}</td>
                    <td className="px-4 py-2 text-gray-500 dark:text-gray-400 text-right">{row.total}</td>
                    <td className="px-4 py-2 text-green-600 dark:text-green-400 text-right">{row.success}</td>
                    <td className="px-4 py-2 text-right">
                      <span className={`font-semibold ${rate >= 80 ? 'text-green-600 dark:text-green-400' : rate >= 50 ? 'text-amber-600 dark:text-amber-400' : 'text-red-600 dark:text-red-400'}`}>
                        {rate}%
                      </span>
                    </td>
                    <td className="px-4 py-2">
                      <div className="w-32 h-2 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${rate >= 80 ? 'bg-green-500' : rate >= 50 ? 'bg-amber-500' : 'bg-red-500'}`}
                          style={{ width: `${rate}%` }}
                        />
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Tendance 7 jours */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
        <h3 className="font-semibold text-gray-900 dark:text-white mb-4">Tendance 7 derniers jours</h3>
        {trend.length === 0 ? (
          <div className="text-center py-6 text-gray-500 dark:text-gray-400 text-sm">Pas encore de données</div>
        ) : (
          <div className="flex items-end gap-3 h-24">
            {trend.map(d => {
              const heightPct = Math.max(4, Math.round((d.total / maxTotal) * 100))
              const successPct = d.total > 0 ? Math.round((d.success / d.total) * 100) : 0
              const dateStr = new Date(d.day).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short' })
              return (
                <div key={d.day} className="flex flex-col items-center gap-1 flex-1" title={`${dateStr} : ${d.total} envois, ${successPct}% succès`}>
                  <span className="text-xs text-gray-500 dark:text-gray-400">{d.total}</span>
                  <div className="w-full flex flex-col justify-end" style={{ height: '60px' }}>
                    <div
                      className={`w-full rounded-t ${successPct >= 80 ? 'bg-green-500' : successPct >= 50 ? 'bg-amber-500' : 'bg-red-500'}`}
                      style={{ height: `${heightPct}%` }}
                    />
                  </div>
                  <span className="text-xs text-gray-400 dark:text-gray-500 truncate w-full text-center">{dateStr}</span>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

// ==================== SCHEDULE MODAL (onglets) ====================

function ScheduleModal({ schedule, availableReports, availableUsers, onClose, onSave }) {
  const [activeTab, setActiveTab] = useState('base')
  const [form, setForm] = useState({
    nom: schedule?.nom || '',
    description: schedule?.description || '',
    tags: schedule?.tags || '',
    report_type: schedule?.report_type || 'export',
    report_id: schedule?.report_id || null,
    export_format: schedule?.export_format || 'excel',
    frequency: schedule?.frequency || 'daily',
    schedule_time: schedule?.schedule_time || '08:00',
    schedule_day: schedule?.schedule_day || 1,
    date_debut: schedule?.date_debut ? String(schedule.date_debut).slice(0,10) : '',
    date_fin: schedule?.date_fin ? String(schedule.date_fin).slice(0,10) : '',
    objet_email: schedule?.objet_email || '',
    message_email: schedule?.message_email || '',
    recipients: schedule?.recipients || [],
    cc_recipients: schedule?.cc_recipients || [],
    is_active: schedule?.is_active !== false,
  })
  const [saving, setSaving] = useState(false)
  const [manualTo, setManualTo] = useState('')
  const [manualCc, setManualCc] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.nom.trim()) { setActiveTab('base'); return }
    if (form.recipients.length === 0) { setActiveTab('destinataires'); return }
    setSaving(true)
    const data = {
      ...form,
      recipients: form.recipients,
      cc_recipients: form.cc_recipients.length > 0 ? form.cc_recipients : null,
      report_id: form.report_id || null,
      date_debut: form.date_debut || null,
      date_fin: form.date_fin || null,
      tags: form.tags || null,
      objet_email: form.objet_email || null,
      message_email: form.message_email || null,
    }
    await onSave(data)
    setSaving(false)
  }

  const toggleEmail = (field, email) => {
    setForm(prev => ({
      ...prev,
      [field]: prev[field].includes(email)
        ? prev[field].filter(e => e !== email)
        : [...prev[field], email]
    }))
  }

  const addManual = (field, val, setter) => {
    const email = val.trim()
    if (!email || !email.includes('@')) return
    setForm(prev => ({ ...prev, [field]: prev[field].includes(email) ? prev[field] : [...prev[field], email] }))
    setter('')
  }

  const removeEmail = (field, email) => {
    setForm(prev => ({ ...prev, [field]: prev[field].filter(e => e !== email) }))
  }

  const getReportOptions = () => {
    switch (form.report_type) {
      case 'pivot': return availableReports.pivots || []
      case 'gridview': return availableReports.gridviews || []
      case 'dashboard': return availableReports.dashboards || []
      case 'export': return availableReports.exports || []
      default: return []
    }
  }

  // Preview prochain envoi
  const previewNextRun = () => {
    const now = new Date()
    const [h, m] = (form.schedule_time || '08:00').split(':').map(Number)
    let label = ''
    if (form.frequency === 'daily') {
      const d = new Date(now)
      d.setHours(h, m, 0, 0)
      if (d <= now) d.setDate(d.getDate() + 1)
      label = d.toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' }) + ` à ${form.schedule_time}`
    } else if (form.frequency === 'weekly') {
      const day = form.schedule_day || 1
      const diff = (day - now.getDay() + 6) % 7 || 7
      const d = new Date(now)
      d.setDate(d.getDate() + diff)
      d.setHours(h, m, 0, 0)
      label = d.toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' }) + ` à ${form.schedule_time}`
    } else if (form.frequency === 'monthly') {
      label = `Le ${form.schedule_day || 1} du prochain mois à ${form.schedule_time}`
    } else {
      label = `Demain à ${form.schedule_time}`
    }
    return label
  }

  const TABS = [
    { id: 'base', label: 'Base' },
    { id: 'planification', label: 'Planification' },
    { id: 'destinataires', label: 'Destinataires' },
  ]

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-2xl max-h-[92vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700 shrink-0">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            {schedule ? "Modifier l'envoi planifié" : 'Nouvel envoi planifié'}
          </h2>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Onglets */}
        <div className="flex border-b border-gray-200 dark:border-gray-700 shrink-0 px-6">
          {TABS.map(t => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === t.id
                  ? 'border-primary-600 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400'
              }`}
            >
              {t.label}
              {t.id === 'destinataires' && form.recipients.length > 0 && (
                <span className="ml-1.5 px-1.5 py-0.5 bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 rounded-full text-xs">
                  {form.recipients.length}
                </span>
              )}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col flex-1 overflow-hidden">
          <div className="flex-1 overflow-y-auto p-6 space-y-5">

            {/* ===== ONGLET BASE ===== */}
            {activeTab === 'base' && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Nom *</label>
                  <input
                    type="text"
                    value={form.nom}
                    onChange={e => setForm({ ...form, nom: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Description</label>
                  <textarea
                    rows={2}
                    value={form.description}
                    onChange={e => setForm({ ...form, description: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white resize-none"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    <span className="flex items-center gap-1"><Tag className="w-3.5 h-3.5" /> Tags (séparés par virgule)</span>
                  </label>
                  <input
                    type="text"
                    value={form.tags}
                    onChange={e => setForm({ ...form, tags: e.target.value })}
                    placeholder="Ex : ventes, mensuel, direction"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                </div>

                {/* Type de rapport */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Type de rapport</label>
                  <div className="grid grid-cols-4 gap-2">
                    {[
                      { value: 'export', label: 'Export', Icon: Download },
                      { value: 'pivot', label: 'Pivot', Icon: Table2 },
                      { value: 'gridview', label: 'GridView', Icon: FileSpreadsheet },
                      { value: 'dashboard', label: 'Dashboard', Icon: LayoutDashboard },
                    ].map(opt => (
                      <button
                        key={opt.value}
                        type="button"
                        onClick={() => setForm({ ...form, report_type: opt.value, report_id: null })}
                        className={`flex flex-col items-center gap-1 p-3 rounded-lg border-2 text-xs font-medium transition-colors ${
                          form.report_type === opt.value
                            ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300'
                            : 'border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:border-gray-300'
                        }`}
                      >
                        <opt.Icon className="w-5 h-5" />
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Rapport</label>
                  <select
                    value={form.report_id || ''}
                    onChange={e => setForm({ ...form, report_id: e.target.value || null })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  >
                    <option value="">Sélectionner...</option>
                    {getReportOptions().map(r => (
                      <option key={r.id} value={r.id}>{r.nom}</option>
                    ))}
                  </select>
                </div>

                {/* Format */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Format d'export</label>
                  <div className="flex gap-2">
                    {['excel', 'pdf', 'csv'].map(fmt => (
                      <button
                        key={fmt}
                        type="button"
                        onClick={() => setForm({ ...form, export_format: fmt })}
                        className={`px-4 py-2 rounded-lg text-sm font-medium border-2 transition-colors ${
                          form.export_format === fmt
                            ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300'
                            : 'border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:border-gray-300'
                        }`}
                      >
                        {fmt.toUpperCase()}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Statut actif */}
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() => setForm({ ...form, is_active: !form.is_active })}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${form.is_active ? 'bg-green-500' : 'bg-gray-300 dark:bg-gray-600'}`}
                  >
                    <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${form.is_active ? 'translate-x-6' : 'translate-x-1'}`} />
                  </button>
                  <span className="text-sm text-gray-700 dark:text-gray-300">
                    {form.is_active ? 'Actif — sera exécuté automatiquement' : 'Inactif — ne sera pas exécuté'}
                  </span>
                </div>
              </>
            )}

            {/* ===== ONGLET PLANIFICATION ===== */}
            {activeTab === 'planification' && (
              <>
                {/* Fréquence */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Fréquence</label>
                  <div className="grid grid-cols-4 gap-2">
                    {FREQUENCY_OPTIONS.map(f => (
                      <button
                        key={f.value}
                        type="button"
                        onClick={() => setForm({ ...form, frequency: f.value })}
                        className={`py-2 px-3 rounded-lg text-sm font-medium border-2 transition-colors ${
                          form.frequency === f.value
                            ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300'
                            : 'border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:border-gray-300'
                        }`}
                      >
                        {f.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Heure */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Heure d'envoi</label>
                  <input
                    type="time"
                    value={form.schedule_time}
                    onChange={e => setForm({ ...form, schedule_time: e.target.value })}
                    className="w-40 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                </div>

                {/* Jour semaine (weekly) */}
                {form.frequency === 'weekly' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Jour de la semaine</label>
                    <div className="flex gap-1.5 flex-wrap">
                      {DAYS_OF_WEEK.map(d => (
                        <button
                          key={d.value}
                          type="button"
                          onClick={() => setForm({ ...form, schedule_day: d.value })}
                          className={`px-3 py-2 rounded-lg text-sm font-medium border-2 transition-colors ${
                            form.schedule_day === d.value
                              ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300'
                              : 'border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:border-gray-300'
                          }`}
                        >
                          {d.label}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Jour mois (monthly) */}
                {form.frequency === 'monthly' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Jour du mois</label>
                    <div className="grid grid-cols-7 gap-1">
                      {Array.from({ length: 28 }, (_, i) => i + 1).map(d => (
                        <button
                          key={d}
                          type="button"
                          onClick={() => setForm({ ...form, schedule_day: d })}
                          className={`py-1.5 rounded text-sm font-medium border transition-colors ${
                            form.schedule_day === d
                              ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300'
                              : 'border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:border-gray-300'
                          }`}
                        >
                          {d}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Période */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Période de validité</label>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">Le schedule ne sera exécuté que pendant cette période. Laissez vide pour une durée illimitée.</p>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-xs text-gray-500 dark:text-gray-400 mb-1 block">Date début</label>
                      <input
                        type="date"
                        value={form.date_debut}
                        onChange={e => setForm({ ...form, date_debut: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-gray-500 dark:text-gray-400 mb-1 block">Date fin</label>
                      <input
                        type="date"
                        value={form.date_fin}
                        onChange={e => setForm({ ...form, date_fin: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
                      />
                    </div>
                  </div>
                </div>

                {/* Objet & message email */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Sujet de l'email (personnalisé)</label>
                  <input
                    type="text"
                    value={form.objet_email}
                    onChange={e => setForm({ ...form, objet_email: e.target.value })}
                    placeholder="Laissez vide pour le sujet automatique"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Message additionnel</label>
                  <textarea
                    rows={3}
                    value={form.message_email}
                    onChange={e => setForm({ ...form, message_email: e.target.value })}
                    placeholder="Message qui sera inclus dans le corps de l'email..."
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white resize-none"
                  />
                </div>

                {/* Preview */}
                <div className="p-3 bg-primary-50 dark:bg-primary-900/20 rounded-lg border border-primary-200 dark:border-primary-800">
                  <p className="text-sm text-primary-700 dark:text-primary-300">
                    <span className="font-semibold">Prochain envoi estimé :</span> {previewNextRun()}
                  </p>
                </div>
              </>
            )}

            {/* ===== ONGLET DESTINATAIRES ===== */}
            {activeTab === 'destinataires' && (
              <>
                {/* Section TO */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Destinataires (À) *
                    <span className="ml-2 text-xs font-normal text-gray-500">({form.recipients.length} sélectionné(s))</span>
                  </label>
                  {/* Chips sélectionnés */}
                  {form.recipients.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mb-2">
                      {form.recipients.map(e => (
                        <span key={e} className="flex items-center gap-1 px-2 py-1 bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 rounded-lg text-xs">
                          {e}
                          <button type="button" onClick={() => removeEmail('recipients', e)}><X className="w-3 h-3" /></button>
                        </span>
                      ))}
                    </div>
                  )}
                  {/* Liste utilisateurs */}
                  <div className="border border-gray-200 dark:border-gray-600 rounded-lg max-h-36 overflow-y-auto">
                    {availableUsers.length === 0 ? (
                      <div className="px-3 py-2 text-gray-500 text-sm">Aucun utilisateur disponible</div>
                    ) : availableUsers.map(user => (
                      <label key={user.id} className="flex items-center gap-2 px-3 py-2 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer border-b border-gray-100 dark:border-gray-700 last:border-0">
                        <input
                          type="checkbox"
                          checked={form.recipients.includes(user.email)}
                          onChange={() => toggleEmail('recipients', user.email)}
                          className="rounded border-gray-300"
                        />
                        <span className="text-sm text-gray-900 dark:text-white">{user.nom} {user.prenom}</span>
                        <span className="text-xs text-gray-500 ml-auto">{user.email}</span>
                      </label>
                    ))}
                  </div>
                  {/* Saisie manuelle */}
                  <div className="flex gap-2 mt-2">
                    <input
                      type="email"
                      value={manualTo}
                      onChange={e => setManualTo(e.target.value)}
                      onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), addManual('recipients', manualTo, setManualTo))}
                      placeholder="Ou saisir un email manuellement..."
                      className="flex-1 px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    />
                    <button
                      type="button"
                      onClick={() => addManual('recipients', manualTo, setManualTo)}
                      className="px-3 py-2 text-sm bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 rounded-lg hover:bg-primary-200"
                    >
                      Ajouter
                    </button>
                  </div>
                </div>

                {/* Section CC */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Copie (CC) — optionnel
                    <span className="ml-2 text-xs font-normal text-gray-500">({form.cc_recipients.length} sélectionné(s))</span>
                  </label>
                  {form.cc_recipients.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mb-2">
                      {form.cc_recipients.map(e => (
                        <span key={e} className="flex items-center gap-1 px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg text-xs">
                          {e}
                          <button type="button" onClick={() => removeEmail('cc_recipients', e)}><X className="w-3 h-3" /></button>
                        </span>
                      ))}
                    </div>
                  )}
                  <div className="border border-gray-200 dark:border-gray-600 rounded-lg max-h-28 overflow-y-auto">
                    {availableUsers.map(user => (
                      <label key={user.id} className="flex items-center gap-2 px-3 py-2 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer border-b border-gray-100 dark:border-gray-700 last:border-0">
                        <input
                          type="checkbox"
                          checked={form.cc_recipients.includes(user.email)}
                          onChange={() => toggleEmail('cc_recipients', user.email)}
                          className="rounded border-gray-300"
                        />
                        <span className="text-sm text-gray-900 dark:text-white">{user.nom} {user.prenom}</span>
                        <span className="text-xs text-gray-500 ml-auto">{user.email}</span>
                      </label>
                    ))}
                  </div>
                  <div className="flex gap-2 mt-2">
                    <input
                      type="email"
                      value={manualCc}
                      onChange={e => setManualCc(e.target.value)}
                      onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), addManual('cc_recipients', manualCc, setManualCc))}
                      placeholder="Ou saisir un email CC manuellement..."
                      className="flex-1 px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    />
                    <button
                      type="button"
                      onClick={() => addManual('cc_recipients', manualCc, setManualCc)}
                      className="px-3 py-2 text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200"
                    >
                      Ajouter
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 dark:border-gray-700 shrink-0">
            <div className="flex gap-1">
              {TABS.map((t, i) => (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => setActiveTab(t.id)}
                  className={`w-2 h-2 rounded-full transition-colors ${activeTab === t.id ? 'bg-primary-600' : 'bg-gray-300 dark:bg-gray-600'}`}
                />
              ))}
            </div>
            <div className="flex gap-3">
              {activeTab !== 'base' && (
                <button
                  type="button"
                  onClick={() => setActiveTab(activeTab === 'planification' ? 'base' : 'planification')}
                  className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg text-sm"
                >
                  Précédent
                </button>
              )}
              {activeTab !== 'destinataires' ? (
                <button
                  type="button"
                  onClick={() => setActiveTab(activeTab === 'base' ? 'planification' : 'destinataires')}
                  className="px-4 py-2 text-white rounded-lg text-sm"
                  style={{ backgroundColor: 'var(--color-primary-600)' }}
                >
                  Suivant
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={saving}
                  className="flex items-center gap-2 px-4 py-2 text-white rounded-lg text-sm"
                  style={{ backgroundColor: 'var(--color-primary-600)' }}
                >
                  {saving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                  {schedule ? 'Enregistrer' : 'Créer'}
                </button>
              )}
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}

// ==================== EMAIL CONFIG MODAL ====================

function EmailConfigModal({ config, onClose, onSave, onTest, onSendTest, toast }) {
  const [form, setForm] = useState({
    smtp_host: config?.smtp_host || '',
    smtp_port: config?.smtp_port || 587,
    smtp_user: config?.smtp_user || '',
    smtp_password: '',
    sender_name: config?.sender_name || 'Reporting KAsoft',
    use_ssl: config?.use_ssl !== false,
    use_tls: config?.use_tls || false,
  })
  const [testing, setTesting] = useState(false)
  const [testEmail, setTestEmail] = useState('')
  const [saving, setSaving] = useState(false)

  const handleTest = async () => {
    setTesting(true)
    const result = await onTest(form)
    toast(result.success ? 'Connexion SMTP réussie !' : 'Erreur : ' + result.error, result.success ? 'success' : 'error')
    setTesting(false)
  }

  const handleSendTest = async () => {
    if (!testEmail) {
      toast('Entrez une adresse email', 'warn')
      return
    }
    setTesting(true)
    const result = await onSendTest(testEmail)
    toast(result.success ? 'Email de test envoyé !' : 'Erreur : ' + result.error, result.success ? 'success' : 'error')
    setTesting(false)
  }

  const handleSave = async () => {
    setSaving(true)
    await onSave({ ...form, is_active: true })
    setSaving(false)
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-lg">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Configuration Email</h2>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        <div className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Serveur SMTP</label>
              <input
                type="text"
                value={form.smtp_host}
                onChange={e => setForm({ ...form, smtp_host: e.target.value })}
                placeholder="smtp.gmail.com"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Port</label>
              <input
                type="number"
                value={form.smtp_port}
                onChange={e => setForm({ ...form, smtp_port: parseInt(e.target.value) })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Email (identifiant)</label>
            <input
              type="email"
              value={form.smtp_user}
              onChange={e => setForm({ ...form, smtp_user: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Mot de passe</label>
            <input
              type="password"
              value={form.smtp_password}
              onChange={e => setForm({ ...form, smtp_password: e.target.value })}
              placeholder={config ? '••••••••' : ''}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Nom expéditeur</label>
            <input
              type="text"
              value={form.sender_name}
              onChange={e => setForm({ ...form, sender_name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
          </div>

          <div className="flex items-center gap-6">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={form.use_ssl}
                onChange={e => setForm({ ...form, use_ssl: e.target.checked })}
                className="rounded border-gray-300"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">SSL</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={form.use_tls}
                onChange={e => setForm({ ...form, use_tls: e.target.checked })}
                className="rounded border-gray-300"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">STARTTLS</span>
            </label>
          </div>

          {/* Test */}
          <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg space-y-3">
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Tester la configuration</p>
            <div className="flex gap-2">
              <input
                type="email"
                value={testEmail}
                onChange={e => setTestEmail(e.target.value)}
                placeholder="Email de test"
                className="flex-1 px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
              <button
                onClick={handleTest}
                disabled={testing}
                className="px-3 py-2 text-sm bg-blue-100 text-blue-600 rounded-lg hover:bg-blue-200 dark:bg-blue-900/30 dark:text-blue-400 whitespace-nowrap"
              >
                {testing ? <RefreshCw className="w-4 h-4 animate-spin" /> : 'Tester connexion'}
              </button>
              <button
                onClick={handleSendTest}
                disabled={testing || !testEmail}
                className="px-3 py-2 text-sm bg-green-100 text-green-600 rounded-lg hover:bg-green-200 dark:bg-green-900/30 dark:text-green-400 whitespace-nowrap"
              >
                Envoyer test
              </button>
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
          >
            Annuler
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2 px-4 py-2 text-white rounded-lg"
            style={{ backgroundColor: 'var(--color-primary-600)' }}
          >
            {saving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Enregistrer
          </button>
        </div>
      </div>
    </div>
  )
}
