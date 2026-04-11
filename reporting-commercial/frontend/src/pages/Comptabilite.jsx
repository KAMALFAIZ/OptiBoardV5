import { useState, useCallback, useEffect } from 'react'
import {
  BookOpen, FileText, Users, Landmark, TrendingDown, TrendingUp,
  Clock, Building2, Link2, BarChart2, LayoutDashboard, TableProperties,
  RefreshCw, Database, CheckCircle, AlertTriangle, ArrowRight
} from 'lucide-react'
import Loading from '../components/common/Loading'
import { previewUnifiedDataSource, seedComptabiliteDatasources, seedComptabiliteReports } from '../services/api'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useGlobalFilters } from '../context/GlobalFilterContext'

// ── Helpers ───────────────────────────────────────────────────────────────────
const fmt = (v, dec = 2) =>
  (v == null ? '—' : Number(v).toLocaleString('fr-FR', { minimumFractionDigits: dec, maximumFractionDigits: dec }))

const fmtDate = (d) => {
  if (!d || d === 'None' || d === 'null') return '—'
  try { return new Date(d).toLocaleDateString('fr-FR') } catch { return String(d) }
}

// ── Configuration des onglets ─────────────────────────────────────────────────
const TABS = [
  {
    id: 'balance_generale',        label: 'Balance Générale',         icon: BookOpen,
    ds: 'DS_BALANCE_GENERALE',     type: 'balance',
    columns: ['Compte','Intitule','Nature','Societe','A Nouveau','Mvt Debit','Mvt Credit','Total Debit','Total Credit','Solde','Solde Debiteur','Solde Crediteur'],
  },
  {
    id: 'journal_ecritures',       label: 'Journal des Écritures',    icon: FileText,
    ds: 'DS_ECRITURES_DETAIL',     type: 'detail',
    columns: ['Date','Journal','Num Piece','Compte','Intitule Compte','Tiers','Libelle','Débit','Crédit','Lettrage','Societe'],
  },
  {
    id: 'balance_tiers',           label: 'Balance Tiers',            icon: Users,
    ds: 'DS_ECRITURES_PAR_TIERS',  type: 'tiers',
    columns: ['Code Tiers','Tiers','Type','Societe','Total Debit','Total Credit','Solde','Nb Ecritures'],
  },
  {
    id: 'tresorerie',              label: 'Écritures de Trésorerie',  icon: Landmark,
    ds: 'DS_TRESORERIE',           type: 'tresorerie',
    columns: ['Compte','Intitule','Societe','Solde Initial','Encaissements','Decaissements','Solde Final'],
  },
  {
    id: 'charges',                 label: 'Détail des Charges',       icon: TrendingDown,
    ds: 'DS_DETAIL_CHARGES',       type: 'charges',
    columns: ['Compte','Intitule','Societe','Montant N','Montant N1','Evolution %'],
  },
  {
    id: 'produits',                label: 'Détail des Produits',      icon: TrendingUp,
    ds: 'DS_DETAIL_PRODUITS',      type: 'produits',
    columns: ['Compte','Intitule','Societe','Montant N','Montant N1','Evolution %'],
  },
  {
    id: 'echeances_clients',       label: 'Échéances Clients',        icon: Clock,
    ds: 'DS_ECHEANCES_COMPTABLES', type: 'echeances',
    columns: ['Echeance','Compte','Compte Tiers','Tiers','Num Piece','Libelle','Débit','Crédit','Mode Reglement','Jours Avant Echeance','Societe'],
    extraFilter: (r) => (r['Type tiers'] || '').toLowerCase().includes('client'),
  },
  {
    id: 'echeances_fournisseurs',  label: 'Échéances Fournisseurs',   icon: Building2,
    ds: 'DS_ECHEANCES_COMPTABLES', type: 'echeances',
    columns: ['Echeance','Compte','Compte Tiers','Tiers','Num Piece','Libelle','Débit','Crédit','Mode Reglement','Jours Avant Echeance','Societe'],
    extraFilter: (r) => (r['Type tiers'] || '').toLowerCase().includes('fourn'),
  },
  {
    id: 'lettrage',                label: 'Lettrage & Rapprochement', icon: Link2,
    ds: 'DS_LETTRAGE',             type: 'lettrage',
    columns: ['Compte','Intitule','Societe','Nb Lettrees','Nb Non Lettrees','Solde Non Lettre'],
  },
  {
    id: 'analyses',                label: 'Analyses Comptables',      icon: BarChart2,
    ds: 'DS_ECRITURES_PAR_MOIS',   type: 'analyses',
    columns: ['Annee','Mois','Societe','Nb Ecritures','Total Debit','Total Credit','Nb Comptes','Nb Pieces'],
  },
]

// ── Colonnes monétaires ───────────────────────────────────────────────────────
const MONEY_COLS = new Set([
  'Total Debit','Total Credit','Solde','Solde Debiteur','Solde Crediteur',
  'A Nouveau','Mvt Debit','Mvt Credit','Solde Initial','Encaissements',
  'Decaissements','Solde Final','Montant N','Montant N1','Débit','Crédit',
  'Solde Non Lettre',
])

// ── DataTable simple ──────────────────────────────────────────────────────────
function SimpleTable({ rows, columns, pageSize = 25 }) {
  const [page, setPage] = useState(0)
  if (!rows?.length) return <p className="text-sm text-gray-400 py-8 text-center">Aucune donnée</p>

  const pages = Math.ceil(rows.length / pageSize)
  const slice = rows.slice(page * pageSize, (page + 1) * pageSize)

  const renderCell = (val, col) => {
    if (val == null) return '—'
    if (MONEY_COLS.has(col)) return <span className={Number(val) < 0 ? 'text-red-600' : ''}>{fmt(val)}</span>
    if (col === 'Evolution %') return val != null ? (
      <span className={Number(val) > 0 ? 'text-red-500' : 'text-emerald-600'}>
        {Number(val) > 0 ? '+' : ''}{Number(val).toFixed(1)} %
      </span>
    ) : '—'
    if (col.toLowerCase().includes('date') || col === 'Echeance') return fmtDate(val)
    return String(val)
  }

  return (
    <div>
      <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
        <table className="min-w-full text-xs">
          <thead className="bg-gray-50 dark:bg-gray-700/50">
            <tr>
              {columns.map(c => (
                <th key={c} className="px-3 py-2 text-left font-medium text-gray-600 dark:text-gray-300 whitespace-nowrap">
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
            {slice.map((row, i) => (
              <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-700/30 transition">
                {columns.map(c => (
                  <td key={c} className="px-3 py-1.5 text-gray-800 dark:text-gray-200 whitespace-nowrap">
                    {renderCell(row[c], c)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {pages > 1 && (
        <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
          <span>{rows.length} lignes — page {page + 1}/{pages}</span>
          <div className="flex gap-1">
            <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0}
              className="px-2 py-1 rounded border border-gray-300 dark:border-gray-600 disabled:opacity-40 hover:bg-gray-100 dark:hover:bg-gray-700">
              ‹
            </button>
            <button onClick={() => setPage(p => Math.min(pages - 1, p + 1))} disabled={page >= pages - 1}
              className="px-2 py-1 rounded border border-gray-300 dark:border-gray-600 disabled:opacity-40 hover:bg-gray-100 dark:hover:bg-gray-700">
              ›
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Panneau d'un onglet ───────────────────────────────────────────────────────
function TabPanel({ tab, globalFilters, navigate }) {
  const [rows, setRows] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [loaded, setLoaded] = useState(false)

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    previewUnifiedDataSource(tab.ds, globalFilters || {})
      .then(r => {
        let data = r.data?.data ?? r.data ?? []
        if (tab.extraFilter) data = data.filter(tab.extraFilter)
        setRows(data)
        setLoaded(true)
      })
      .catch(e => setError(e.response?.data?.detail || e.message))
      .finally(() => setLoading(false))
  }, [tab.ds, globalFilters, tab.extraFilter])

  if (!loaded && !loading) {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-3">
        <Database className="w-10 h-10 text-gray-300 dark:text-gray-600" />
        <p className="text-sm text-gray-500">Cliquez pour charger les données</p>
        <button onClick={load}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 transition">
          <RefreshCw className="w-4 h-4" />
          Charger
        </button>
      </div>
    )
  }

  if (loading) return <Loading />

  if (error) return (
    <div className="flex flex-col items-center justify-center py-12 gap-2 text-red-600 dark:text-red-400">
      <AlertTriangle className="w-8 h-8" />
      <p className="text-sm font-medium">{error}</p>
      <button onClick={load} className="text-xs underline">Réessayer</button>
    </div>
  )

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-500 dark:text-gray-400">
          {rows?.length ?? 0} lignes — datasource&nbsp;
          <code className="bg-gray-100 dark:bg-gray-700 px-1 rounded text-xs">{tab.ds}</code>
        </span>
        <div className="flex gap-2">
          <button onClick={load}
            className="flex items-center gap-1 px-2.5 py-1 text-xs rounded-lg
              bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 transition">
            <RefreshCw className="w-3 h-3" />
            Actualiser
          </button>
          <button onClick={() => navigate(`/pivot-builder-v2?ds=${tab.ds}`)}
            className="flex items-center gap-1 px-2.5 py-1 text-xs rounded-lg
              bg-indigo-50 text-indigo-700 hover:bg-indigo-100 dark:bg-indigo-900/30 dark:text-indigo-300 transition">
            <TableProperties className="w-3 h-3" />
            PivotGrid
          </button>
          <button onClick={() => navigate(`/gridview-builder?ds=${tab.ds}`)}
            className="flex items-center gap-1 px-2.5 py-1 text-xs rounded-lg
              bg-emerald-50 text-emerald-700 hover:bg-emerald-100 dark:bg-emerald-900/30 dark:text-emerald-300 transition">
            <Database className="w-3 h-3" />
            GridView
          </button>
          <button onClick={() => navigate(`/builder?ds=${tab.ds}`)}
            className="flex items-center gap-1 px-2.5 py-1 text-xs rounded-lg
              bg-purple-50 text-purple-700 hover:bg-purple-100 dark:bg-purple-900/30 dark:text-purple-300 transition">
            <LayoutDashboard className="w-3 h-3" />
            Dashboard
          </button>
        </div>
      </div>
      <SimpleTable rows={rows} columns={tab.columns} />
    </div>
  )
}

// =============================================================================
// PAGE PRINCIPALE
// =============================================================================
export default function Comptabilite() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { filters: globalFilters, updateFilter } = useGlobalFilters?.() ?? { filters: {}, updateFilter: () => {} }

  const [activeTab, setActiveTab] = useState('balance_generale')

  // Drill-through entrant : appliquer les filtres globaux et activer l'onglet selon dt_field
  useEffect(() => {
    const dtField = searchParams.get('dt_field')
    const gfDateDebut = searchParams.get('gf_dateDebut')
    const gfDateFin = searchParams.get('gf_dateFin')
    const gfSociete = searchParams.get('gf_societe')
    if (gfDateDebut) updateFilter('dateDebut', gfDateDebut)
    if (gfDateFin) updateFilter('dateFin', gfDateFin)
    if (gfSociete) updateFilter('societe', gfSociete)
    // Activer l'onglet pertinent selon le champ drill-through
    const tabMap = {
      compte: 'balance_generale', tiers: 'balance_tiers',
      echeance: 'echeances_clients', fournisseur: 'echeances_fournisseurs',
    }
    if (dtField && tabMap[dtField]) setActiveTab(tabMap[dtField])
  }, []) // eslint-disable-line react-hooks/exhaustive-deps
  const [seeding, setSeeding] = useState(false)
  const [seedingReports, setSeedingReports] = useState(false)
  const [seedMsg, setSeedMsg] = useState(null)

  const handleSeed = async () => {
    setSeeding(true)
    setSeedMsg(null)
    try {
      const r = await seedComptabiliteDatasources()
      setSeedMsg({ ok: true, text: r.data.message })
    } catch {
      setSeedMsg({ ok: false, text: 'Erreur lors de l\'initialisation des datasources.' })
    } finally {
      setSeeding(false)
      setTimeout(() => setSeedMsg(null), 6000)
    }
  }

  const handleSeedReports = async () => {
    setSeedingReports(true)
    setSeedMsg(null)
    try {
      const r = await seedComptabiliteReports()
      setSeedMsg({ ok: true, text: r.data.message })
    } catch {
      setSeedMsg({ ok: false, text: 'Erreur lors de la création des rapports.' })
    } finally {
      setSeedingReports(false)
      setTimeout(() => setSeedMsg(null), 8000)
    }
  }

  const tab = TABS.find(t => t.id === activeTab)

  const dtSource = searchParams.get('dt_source')
  const dtField = searchParams.get('dt_field')
  const dtValue = searchParams.get('dt_value')

  return (
    <div className="h-full flex flex-col p-4 gap-4 overflow-auto">

      {/* Bandeau drill-through entrant */}
      {dtField && dtValue && (
        <div className="flex items-center gap-2 px-4 py-1.5 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800/30 rounded-lg text-xs text-blue-700 dark:text-blue-300">
          <ArrowRight className="w-3.5 h-3.5 flex-shrink-0" />
          <span>Filtré depuis <b>{dtSource || 'rapport source'}</b> — {dtField}: <b>{dtValue}</b></span>
        </div>
      )}

      {/* En-tête */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">Comptabilité</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Datasources liées à <code className="bg-gray-100 dark:bg-gray-700 px-1 rounded text-xs">[Ecritures_Comptables]</code>
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={handleSeed} disabled={seeding}
            className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-lg
              bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50 transition">
            <Database className="w-3.5 h-3.5" />
            {seeding ? 'Initialisation…' : '① Datasources'}
          </button>
          <button onClick={handleSeedReports} disabled={seedingReports}
            className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-lg
              bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50 transition">
            <Database className="w-3.5 h-3.5" />
            {seedingReports ? 'Création…' : '② GridViews + Pivots + Dashboards'}
          </button>
        </div>
      </div>

      {/* Message */}
      {seedMsg && (
        <div className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm ${
          seedMsg.ok
            ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300'
            : 'bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300'
        }`}>
          {seedMsg.ok ? <CheckCircle className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
          {seedMsg.text}
        </div>
      )}

      {/* Carte principale */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 flex-1 flex flex-col overflow-hidden">
        {/* Tabs */}
        <div className="border-b border-gray-200 dark:border-gray-700 overflow-x-auto">
          <div className="flex min-w-max">
            {TABS.map(t => {
              const Icon = t.icon
              return (
                <button key={t.id} onClick={() => setActiveTab(t.id)}
                  className={`flex items-center gap-1.5 px-4 py-3 text-xs font-medium whitespace-nowrap border-b-2 transition ${
                    activeTab === t.id
                      ? 'border-primary-600 text-primary-700 dark:text-primary-400'
                      : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:border-gray-300'
                  }`}>
                  <Icon className="w-3.5 h-3.5" />
                  {t.label}
                </button>
              )
            })}
          </div>
        </div>

        {/* Contenu */}
        <div className="flex-1 overflow-auto p-4">
          {tab && <TabPanel key={activeTab} tab={tab} globalFilters={globalFilters} navigate={navigate} />}
        </div>
      </div>
    </div>
  )
}
