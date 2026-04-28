/**
 * UpdateManagerPage — Module MAJ
 * ================================
 * Permet aux clients de verifier et appliquer les mises a jour
 * publiees par KASOFT depuis le catalogue central.
 *
 * Clients autonomes : connexion ponctuelle pour tirer les MAJ ici.
 * Clients connectes : MAJ automatiques + this page pour forcer.
 */
import { useState, useEffect, useCallback } from 'react'
import {
  RefreshCw, Download, CheckCircle, Clock, AlertTriangle,
  Database, LayoutDashboard, Grid3x3, BarChart3, Menu,
  ChevronDown, ChevronUp, History, Wifi, WifiOff
} from 'lucide-react'
import api from '../services/api'

// ── API helpers ──────────────────────────────────────────────
const checkUpdates  = ()           => api.get('/updates/check')
const pullETL       = ()           => api.post('/updates/pull/etl')
const pullBuilder   = ()           => api.post('/updates/pull/builder')
const pullAll       = ()           => api.post('/updates/pull/all')
const getHistory    = (params={})  => api.get('/updates/history', { params })

// ── Catégorie config ─────────────────────────────────────────
const CATEGORIES = [
  { key: 'etl_tables', label: 'Tables ETL',   icon: Database,       color: 'blue',   type: 'etl_table'  },
  { key: 'dashboards', label: 'Dashboards',   icon: LayoutDashboard, color: 'purple', type: 'dashboard'  },
  { key: 'gridviews',  label: 'Grilles',      icon: Grid3x3,        color: 'indigo', type: 'gridview'   },
  { key: 'menus',      label: 'Menus',        icon: Menu,           color: 'orange', type: 'menu'       },
]

const COLOR_CLASSES = {
  blue:   { bg: 'bg-blue-50 dark:bg-blue-900/20',   text: 'text-blue-700 dark:text-blue-400',   border: 'border-blue-200 dark:border-blue-700',   badge: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300' },
  purple: { bg: 'bg-purple-50 dark:bg-purple-900/20', text: 'text-purple-700 dark:text-purple-400', border: 'border-purple-200 dark:border-purple-700', badge: 'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300' },
  indigo: { bg: 'bg-indigo-50 dark:bg-indigo-900/20', text: 'text-indigo-700 dark:text-indigo-400', border: 'border-indigo-200 dark:border-indigo-700', badge: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300' },
  orange: { bg: 'bg-orange-50 dark:bg-orange-900/20', text: 'text-orange-700 dark:text-orange-400', border: 'border-orange-200 dark:border-orange-700', badge: 'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300' },
}

// ── Composant CategoryCard ────────────────────────────────────
function CategoryCard({ cat, data, onPull, pulling }) {
  const [expanded, setExpanded] = useState(false)
  const c      = COLOR_CLASSES[cat.color]
  const Icon   = cat.icon
  const count  = data?.pending ?? 0
  const items  = data?.items   ?? []
  const lastApplied = data?.last_applied

  return (
    <div className={`rounded-xl border ${c.border} ${c.bg} overflow-hidden`}>
      {/* Header */}
      <div className="flex items-center justify-between p-4">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg bg-white dark:bg-gray-800 shadow-sm`}>
            <Icon className={`w-5 h-5 ${c.text}`} />
          </div>
          <div>
            <p className="font-semibold text-gray-900 dark:text-white">{cat.label}</p>
            {lastApplied
              ? <p className="text-xs text-gray-500 dark:text-gray-400">
                  Derniere MAJ : {new Date(lastApplied).toLocaleDateString('fr-FR', { day:'2-digit', month:'short', year:'numeric', hour:'2-digit', minute:'2-digit' })}
                </p>
              : <p className="text-xs text-gray-400 italic">Jamais installe</p>
            }
          </div>
        </div>

        <div className="flex items-center gap-2">
          {count > 0 && (
            <span className={`text-xs font-bold px-2 py-1 rounded-full ${c.badge}`}>
              {count} en attente
            </span>
          )}
          {count === 0 && (
            <span className="text-xs font-medium px-2 py-1 rounded-full bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 flex items-center gap-1">
              <CheckCircle className="w-3.5 h-3.5" /> A jour
            </span>
          )}
          {count > 0 && (
            <button
              onClick={() => onPull(cat.key)}
              disabled={pulling}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 transition-colors`}
            >
              {pulling ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
              Appliquer
            </button>
          )}
          {items.length > 0 && (
            <button
              onClick={() => setExpanded(v => !v)}
              className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
            >
              {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
          )}
        </div>
      </div>

      {/* Items liste */}
      {expanded && items.length > 0 && (
        <div className="border-t border-gray-200 dark:border-gray-700 divide-y divide-gray-100 dark:divide-gray-700">
          {items.map(item => (
            <div key={item.code} className="flex items-center justify-between px-4 py-2 text-sm">
              <span className="text-gray-700 dark:text-gray-300">
                <span className="font-mono text-xs text-gray-400 mr-2">{item.code}</span>
                {item.nom}
              </span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                {item.statut === 'non_installe' ? 'Nouveau' : 'Mise a jour'}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Composant HistoryTable ────────────────────────────────────
function HistoryTable({ history }) {
  if (!history.length) {
    return (
      <div className="text-center py-12 text-gray-400 dark:text-gray-500">
        <History className="w-10 h-10 mx-auto mb-3 opacity-40" />
        <p className="text-sm">Aucun historique de mise a jour</p>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700">
            <th className="pb-2 pr-4 font-medium">Date</th>
            <th className="pb-2 pr-4 font-medium">Type</th>
            <th className="pb-2 pr-4 font-medium">Element</th>
            <th className="pb-2 pr-4 font-medium">Version</th>
            <th className="pb-2 font-medium">Statut</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 dark:divide-gray-700/50">
          {history.map(row => (
            <tr key={row.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
              <td className="py-2 pr-4 text-gray-500 dark:text-gray-400 whitespace-nowrap">
                {new Date(row.date_installation).toLocaleString('fr-FR')}
              </td>
              <td className="py-2 pr-4">
                <span className="font-mono text-xs px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
                  {row.type_entite}
                </span>
              </td>
              <td className="py-2 pr-4 text-gray-700 dark:text-gray-300">
                <span className="text-gray-400 text-xs mr-1">{row.code_entite}</span>
                {row.nom_entite}
              </td>
              <td className="py-2 pr-4 text-gray-500 dark:text-gray-400 text-xs">
                {row.version_precedente != null ? `v${row.version_precedente} → ` : ''}v{row.version_installee}
              </td>
              <td className="py-2">
                {row.statut === 'succes'   && <span className="inline-flex items-center gap-1 text-xs text-green-600 dark:text-green-400"><CheckCircle className="w-3.5 h-3.5" /> Succes</span>}
                {row.statut === 'echec'    && <span className="inline-flex items-center gap-1 text-xs text-red-600 dark:text-red-400"><AlertTriangle className="w-3.5 h-3.5" /> Echec</span>}
                {row.statut === 'rollback' && <span className="inline-flex items-center gap-1 text-xs text-orange-600 dark:text-orange-400"><Clock className="w-3.5 h-3.5" /> Rollback</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── Page principale ───────────────────────────────────────────
export default function UpdateManagerPage() {
  const [tab, setTab]           = useState('updates')   // 'updates' | 'history'
  const [checking, setChecking] = useState(false)
  const [pulling, setPulling]   = useState(null)        // key de la categorie en cours
  const [updateData, setUpdateData] = useState(null)
  const [history, setHistory]   = useState([])
  const [loadingHistory, setLoadingHistory] = useState(false)
  const [toast, setToast]       = useState(null)

  const showToast = (msg, type='success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 4000)
  }

  // Verifier les MAJ
  const handleCheck = useCallback(async () => {
    setChecking(true)
    try {
      const res = await checkUpdates()
      setUpdateData(res.data)
    } catch (e) {
      showToast('Impossible de joindre le serveur central', 'error')
    } finally {
      setChecking(false)
    }
  }, [])

  // Appliquer les MAJ d'une categorie
  const handlePull = async (catKey) => {
    setPulling(catKey)
    try {
      let res
      if (catKey === 'etl_tables') res = await pullETL()
      else                         res = await pullBuilder()

      const d = res.data
      showToast(d.message || `${d.applied || d.total_applied} element(s) mis a jour`)
      await handleCheck()   // rafraichir le statut
    } catch (e) {
      showToast('Erreur lors de la mise a jour', 'error')
    } finally {
      setPulling(null)
    }
  }

  // Appliquer tout
  const handlePullAll = async () => {
    setPulling('all')
    try {
      const res = await pullAll()
      const d   = res.data
      showToast(d.message || `${d.total_applied} element(s) mis a jour`)
      await handleCheck()
    } catch (e) {
      showToast('Erreur lors de la mise a jour globale', 'error')
    } finally {
      setPulling(null)
    }
  }

  // Charger l'historique
  const loadHistory = useCallback(async () => {
    setLoadingHistory(true)
    try {
      const res = await getHistory({ limit: 200 })
      setHistory(res.data?.data || [])
    } catch (e) {
      showToast('Erreur chargement historique', 'error')
    } finally {
      setLoadingHistory(false)
    }
  }, [])

  useEffect(() => {
    handleCheck()
  }, [handleCheck])

  useEffect(() => {
    if (tab === 'history') loadHistory()
  }, [tab, loadHistory])

  const totalPending = updateData?.total_pending ?? 0
  const categories   = updateData?.categories ?? {}

  return (
    <div className="p-6 max-w-4xl mx-auto">

      {/* Toast */}
      {toast && (
        <div className={`fixed top-4 right-4 z-50 flex items-center gap-2 px-4 py-3 rounded-xl shadow-lg text-sm font-medium transition-all
          ${toast.type === 'error'
            ? 'bg-red-600 text-white'
            : 'bg-green-600 text-white'}`}>
          {toast.type === 'error' ? <AlertTriangle className="w-4 h-4" /> : <CheckCircle className="w-4 h-4" />}
          {toast.msg}
        </div>
      )}

      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <RefreshCw className="w-6 h-6 text-blue-600" />
            Gestionnaire de mises a jour
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Synchronisez votre installation avec le catalogue KASOFT
          </p>
        </div>

        <div className="flex items-center gap-2">
          {totalPending > 0 && (
            <button
              onClick={handlePullAll}
              disabled={pulling === 'all'}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-xl text-sm font-semibold hover:bg-blue-700 disabled:opacity-50 transition-colors shadow"
            >
              {pulling === 'all'
                ? <RefreshCw className="w-4 h-4 animate-spin" />
                : <Download className="w-4 h-4" />}
              Tout mettre a jour ({totalPending})
            </button>
          )}
          <button
            onClick={handleCheck}
            disabled={checking}
            className="flex items-center gap-2 px-4 py-2 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 rounded-xl text-sm font-medium hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${checking ? 'animate-spin' : ''}`} />
            Verifier
          </button>
        </div>
      </div>

      {/* Statut connexion */}
      {updateData && (
        <div className={`flex items-center gap-2 mb-6 px-4 py-2.5 rounded-xl text-sm font-medium
          ${totalPending === 0
            ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 border border-green-200 dark:border-green-700'
            : 'bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-700'}`}>
          {totalPending === 0
            ? <><CheckCircle className="w-4 h-4" /> Votre installation est a jour — verifie le {new Date(updateData.checked_at).toLocaleTimeString('fr-FR')}</>
            : <><AlertTriangle className="w-4 h-4" /> {totalPending} mise(s) a jour disponible(s)</>
          }
        </div>
      )}

      {/* Onglets */}
      <div className="flex border-b border-gray-200 dark:border-gray-700 mb-6 gap-1">
        {[
          { id: 'updates', label: 'Mises a jour', icon: Download },
          { id: 'history', label: 'Historique',   icon: History  },
        ].map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors
              ${tab === t.id
                ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}`}
          >
            <t.icon className="w-4 h-4" />
            {t.label}
          </button>
        ))}
      </div>

      {/* Onglet Mises a jour */}
      {tab === 'updates' && (
        <div className="space-y-4">
          {checking && !updateData && (
            <div className="flex items-center justify-center py-16 text-gray-400">
              <RefreshCw className="w-6 h-6 animate-spin mr-2" />
              <span>Connexion au serveur central...</span>
            </div>
          )}
          {!checking && !updateData && (
            <div className="text-center py-16 text-gray-400">
              <WifiOff className="w-10 h-10 mx-auto mb-3 opacity-40" />
              <p className="text-sm">Impossible de contacter le serveur central</p>
              <button onClick={handleCheck} className="mt-3 text-sm text-blue-600 hover:underline">Reessayer</button>
            </div>
          )}
          {CATEGORIES.map(cat => (
            <CategoryCard
              key={cat.key}
              cat={cat}
              data={categories[cat.key]}
              onPull={handlePull}
              pulling={pulling === cat.key || pulling === 'all'}
            />
          ))}
        </div>
      )}

      {/* Onglet Historique */}
      {tab === 'history' && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          {loadingHistory
            ? <div className="flex items-center justify-center py-10 text-gray-400">
                <RefreshCw className="w-5 h-5 animate-spin mr-2" /> Chargement...
              </div>
            : <HistoryTable history={history} />
          }
        </div>
      )}
    </div>
  )
}
