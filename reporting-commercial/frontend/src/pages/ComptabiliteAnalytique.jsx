import { useState, useCallback, useEffect } from 'react'
import {
  GitBranch, BarChart2, TrendingDown, TrendingUp,
  Target, RefreshCw, Download, AlertTriangle, CheckCircle
} from 'lucide-react'
import Loading from '../components/common/Loading'
import { useGlobalFilters } from '../context/GlobalFilterContext'
import { useDWH } from '../context/DWHContext'
import api from '../services/api'
import * as XLSX from 'xlsx'

// ── Helpers ───────────────────────────────────────────────────────────────────
const fmt = (v, dec = 2) =>
  v == null ? '—' : Number(v).toLocaleString('fr-FR', { minimumFractionDigits: dec, maximumFractionDigits: dec })

const fmtPct = (v) => v == null ? '—' : `${Number(v).toFixed(1)} %`

const COLORS = {
  primary: '#2563eb',
  success: '#16a34a',
  danger:  '#dc2626',
  warning: '#ea580c',
  neutral: '#6b7280',
}

// ── Onglets ───────────────────────────────────────────────────────────────────
const TABS = [
  { id: 'centres',    label: 'Centres de coûts',      icon: GitBranch },
  { id: 'evolution',  label: 'Ventilation mensuelle',  icon: BarChart2 },
  { id: 'pl',         label: 'Résultat par activité',  icon: TrendingUp },
  { id: 'budget',     label: 'Budget vs Réalisé',      icon: Target },
]

// ── Composant principal ───────────────────────────────────────────────────────
export default function ComptabiliteAnalytique() {
  const { filters } = useGlobalFilters()
  const { activeDWH } = useDWH()
  const [activeTab, setActiveTab] = useState('centres')
  const [data, setData] = useState({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const dwhCode = activeDWH?.code || filters.societe

  const load = useCallback(async () => {
    if (!dwhCode) return
    setLoading(true)
    setError(null)
    const base = { dwh_code: dwhCode, date_debut: filters.dateDebut, date_fin: filters.dateFin }
    const year = filters.annee || new Date().getFullYear()
    try {
      const [centres, evolution, pl, budget] = await Promise.all([
        api.get('/analytique/centres', { params: base }),
        api.get('/analytique/evolution', { params: base }),
        api.get('/analytique/pl-activite', { params: base }),
        api.get('/analytique/budget-vs-realise', { params: { ...base, exercice: year } }),
      ])
      setData({
        centres:   centres.data?.data  || [],
        evolution: evolution.data?.data || [],
        pl:        pl.data?.data        || [],
        budget:    budget.data?.data    || [],
      })
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Erreur de chargement')
    } finally {
      setLoading(false)
    }
  }, [dwhCode, filters.dateDebut, filters.dateFin, filters.annee])

  useEffect(() => { load() }, [load])

  const exportExcel = () => {
    const rows = data[activeTab] || []
    if (!rows.length) return
    const ws = XLSX.utils.json_to_sheet(rows)
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, activeTab)
    XLSX.writeFile(wb, `analytique_${activeTab}_${filters.dateDebut}_${filters.dateFin}.xlsx`)
  }

  const tab = TABS.find(t => t.id === activeTab)

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <GitBranch size={24} className="text-blue-600" />
            Comptabilité Analytique
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            {filters.dateDebut} → {filters.dateFin}
            {dwhCode && <span className="ml-2 font-medium text-blue-600">· {dwhCode}</span>}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={exportExcel}
            className="flex items-center gap-1 px-3 py-2 text-sm bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-40"
            disabled={!(data[activeTab]?.length)}
          >
            <Download size={14} /> Excel
          </button>
          <button
            onClick={load}
            className="flex items-center gap-1 px-3 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
            disabled={loading}
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Actualiser
          </button>
        </div>
      </div>

      {/* Alerte si pas de DWH */}
      {!dwhCode && (
        <div className="flex items-center gap-2 p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 rounded-lg text-yellow-800 dark:text-yellow-300">
          <AlertTriangle size={18} />
          <span className="text-sm">Sélectionnez un DWH pour afficher les données analytiques.</span>
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 rounded-lg text-red-700 dark:text-red-300">
          <AlertTriangle size={18} />
          <span className="text-sm">{error}</span>
        </div>
      )}

      {/* Onglets */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="-mb-px flex space-x-6 overflow-x-auto">
          {TABS.map(t => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={`flex items-center gap-1.5 py-3 px-1 text-sm font-medium border-b-2 whitespace-nowrap transition-colors ${
                activeTab === t.id
                  ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
              }`}
            >
              <t.icon size={15} />
              {t.label}
            </button>
          ))}
        </nav>
      </div>

      {loading ? (
        <Loading message="Chargement des données analytiques…" />
      ) : (
        <>
          {activeTab === 'centres'   && <TabCentres   data={data.centres   || []} />}
          {activeTab === 'evolution' && <TabEvolution data={data.evolution || []} />}
          {activeTab === 'pl'        && <TabPL        data={data.pl        || []} />}
          {activeTab === 'budget'    && <TabBudget    data={data.budget    || []} />}
        </>
      )}
    </div>
  )
}

// ── Onglet : Centres de coûts ─────────────────────────────────────────────────
function TabCentres({ data }) {
  if (!data.length) return <EmptyState />
  const totalDebit  = data.reduce((s, r) => s + (Number(r.Debit)  || 0), 0)
  const totalCredit = data.reduce((s, r) => s + (Number(r.Credit) || 0), 0)
  const totalSolde  = data.reduce((s, r) => s + (Number(r.Solde)  || 0), 0)

  return (
    <div className="space-y-4">
      {/* KPIs */}
      <div className="grid grid-cols-3 gap-4">
        <KpiCard label="Total Débit"  value={fmt(totalDebit)}  color="text-red-600" />
        <KpiCard label="Total Crédit" value={fmt(totalCredit)} color="text-green-600" />
        <KpiCard label="Solde Net"    value={fmt(totalSolde)}  color={totalSolde >= 0 ? 'text-green-600' : 'text-red-600'} />
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 dark:bg-gray-700/50">
            <tr>
              {['Code', 'Centre', 'Débit', 'Crédit', 'Solde'].map(h => (
                <th key={h} className="px-4 py-3 text-left font-semibold text-gray-600 dark:text-gray-300">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
            {data.map((r, i) => (
              <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                <td className="px-4 py-2 font-mono text-xs text-gray-500">{r.Code_Centre}</td>
                <td className="px-4 py-2 font-medium text-gray-800 dark:text-gray-200">{r.Centre}</td>
                <td className="px-4 py-2 text-right text-red-600">{fmt(r.Debit)}</td>
                <td className="px-4 py-2 text-right text-green-600">{fmt(r.Credit)}</td>
                <td className={`px-4 py-2 text-right font-semibold ${Number(r.Solde) >= 0 ? 'text-green-700' : 'text-red-700'}`}>
                  {fmt(r.Solde)}
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot className="bg-gray-100 dark:bg-gray-700 font-semibold">
            <tr>
              <td colSpan={2} className="px-4 py-2 text-gray-700 dark:text-gray-200">TOTAL</td>
              <td className="px-4 py-2 text-right text-red-700">{fmt(totalDebit)}</td>
              <td className="px-4 py-2 text-right text-green-700">{fmt(totalCredit)}</td>
              <td className={`px-4 py-2 text-right ${totalSolde >= 0 ? 'text-green-800' : 'text-red-800'}`}>{fmt(totalSolde)}</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  )
}

// ── Onglet : Ventilation mensuelle ────────────────────────────────────────────
function TabEvolution({ data }) {
  if (!data.length) return <EmptyState />

  // Pivoter : periodes en colonnes, centres en lignes
  const periodes = [...new Set(data.map(r => r.Periode))].sort()
  const centres  = [...new Set(data.map(r => r.Centre))]
  const byKey    = {}
  data.forEach(r => { byKey[`${r.Centre}|${r.Periode}`] = r.Solde })

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-auto">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 dark:bg-gray-700/50">
          <tr>
            <th className="px-4 py-3 text-left font-semibold text-gray-600 dark:text-gray-300 sticky left-0 bg-gray-50 dark:bg-gray-700/50">Centre</th>
            {periodes.map(p => (
              <th key={p} className="px-3 py-3 text-right font-semibold text-gray-600 dark:text-gray-300 whitespace-nowrap">{p}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
          {centres.map((c, i) => (
            <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
              <td className="px-4 py-2 font-medium text-gray-800 dark:text-gray-200 sticky left-0 bg-white dark:bg-gray-800">{c}</td>
              {periodes.map(p => {
                const v = byKey[`${c}|${p}`]
                return (
                  <td key={p} className={`px-3 py-2 text-right ${Number(v) >= 0 ? 'text-green-700' : 'text-red-600'}`}>
                    {fmt(v)}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── Onglet : P&L par activité ─────────────────────────────────────────────────
function TabPL({ data }) {
  if (!data.length) return <EmptyState />
  const totProduits = data.reduce((s, r) => s + (Number(r.Produits) || 0), 0)
  const totCharges  = data.reduce((s, r) => s + (Number(r.Charges)  || 0), 0)
  const totResultat = totProduits - totCharges

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-4">
        <KpiCard label="Produits"  value={fmt(totProduits)} color="text-green-600" />
        <KpiCard label="Charges"   value={fmt(totCharges)}  color="text-red-600" />
        <KpiCard label="Résultat Net" value={fmt(totResultat)} color={totResultat >= 0 ? 'text-green-700 font-bold' : 'text-red-700 font-bold'} />
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 dark:bg-gray-700/50">
            <tr>
              {['Centre', 'Produits', 'Charges', 'Résultat'].map(h => (
                <th key={h} className="px-4 py-3 text-left font-semibold text-gray-600 dark:text-gray-300">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
            {data.map((r, i) => (
              <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                <td className="px-4 py-2 font-medium text-gray-800 dark:text-gray-200">{r.Centre}</td>
                <td className="px-4 py-2 text-right text-green-600">{fmt(r.Produits)}</td>
                <td className="px-4 py-2 text-right text-red-600">{fmt(r.Charges)}</td>
                <td className={`px-4 py-2 text-right font-semibold ${Number(r.Resultat) >= 0 ? 'text-green-700' : 'text-red-700'}`}>
                  {fmt(r.Resultat)}
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot className="bg-gray-100 dark:bg-gray-700 font-bold">
            <tr>
              <td className="px-4 py-2 text-gray-700 dark:text-gray-200">TOTAL</td>
              <td className="px-4 py-2 text-right text-green-700">{fmt(totProduits)}</td>
              <td className="px-4 py-2 text-right text-red-700">{fmt(totCharges)}</td>
              <td className={`px-4 py-2 text-right ${totResultat >= 0 ? 'text-green-800' : 'text-red-800'}`}>{fmt(totResultat)}</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  )
}

// ── Onglet : Budget vs Réalisé ────────────────────────────────────────────────
function TabBudget({ data }) {
  if (!data.length) return <EmptyState message="Aucun budget saisi pour cet exercice. Saisissez un budget dans Paramètres → Budgets." />

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-auto">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 dark:bg-gray-700/50">
          <tr>
            {['Centre', 'Budget', 'Réalisé', 'Écart', 'Taux réal.'].map(h => (
              <th key={h} className="px-4 py-3 text-left font-semibold text-gray-600 dark:text-gray-300">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
          {data.map((r, i) => {
            const taux = r.Taux_Realisation
            const ecart = Number(r.Ecart) || 0
            return (
              <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                <td className="px-4 py-2 font-medium text-gray-800 dark:text-gray-200">{r.Centre}</td>
                <td className="px-4 py-2 text-right">{fmt(r.Budget)}</td>
                <td className="px-4 py-2 text-right">{fmt(r.Realise)}</td>
                <td className={`px-4 py-2 text-right font-medium ${ecart >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {ecart >= 0 ? '+' : ''}{fmt(ecart)}
                </td>
                <td className="px-4 py-2 text-right">
                  {taux != null ? (
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                      taux >= 100 ? 'bg-green-100 text-green-800' :
                      taux >= 80  ? 'bg-yellow-100 text-yellow-800' :
                                    'bg-red-100 text-red-800'
                    }`}>
                      {taux >= 100 ? <CheckCircle size={10} className="mr-1" /> : <AlertTriangle size={10} className="mr-1" />}
                      {fmtPct(taux)}
                    </span>
                  ) : '—'}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ── Composants utilitaires ────────────────────────────────────────────────────
function KpiCard({ label, value, color = 'text-gray-800' }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
      <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">{label}</p>
      <p className={`text-xl font-bold ${color} dark:text-white`}>{value}</p>
    </div>
  )
}

function EmptyState({ message = 'Aucune donnée analytique pour cette période.' }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-gray-400">
      <GitBranch size={48} className="mb-3 opacity-30" />
      <p className="text-lg font-medium">Aucune donnée</p>
      <p className="text-sm mt-1 text-center max-w-sm">{message}</p>
    </div>
  )
}
