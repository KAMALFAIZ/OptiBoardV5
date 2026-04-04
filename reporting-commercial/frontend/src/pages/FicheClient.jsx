import { useState, useEffect, useMemo } from 'react'
import {
  User, Search, TrendingUp, CreditCard, Clock, AlertTriangle,
  CheckCircle, ShoppingBag, FileText, BarChart2, ArrowLeft,
  RefreshCw, ChevronRight, Building2, Phone, Mail, MapPin,
  Shield, Folder
} from 'lucide-react'
import KPICard from '../components/Dashboard/KPICard'
import DataTable from '../components/DrillDown/DataTable'
import Loading from '../components/common/Loading'
import { getFicheClientListe, getFicheClient } from '../services/api'
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell
} from 'recharts'

const TABS = [
  { id: 'overview', label: 'Vue générale', icon: BarChart2 },
  { id: 'documents', label: 'Documents ventes', icon: Folder },
  { id: 'echeances', label: 'Factures impayées', icon: FileText },
  { id: 'reglements', label: 'Historique règlements', icon: CheckCircle },
  { id: 'produits', label: 'Top produits', icon: ShoppingBag },
]

const TRANCHE_COLORS = {
  '0-30j': '#10b981',
  '31-60j': '#84cc16',
  '61-90j': '#f59e0b',
  '91-120j': '#f97316',
  '+120j': '#ef4444',
}

// ─── Score de Santé Client ────────────────────────────────────────────────────
function computeHealthScore(kpis) {
  let score = 100
  const flags = []

  const dso           = parseFloat(kpis.dso_client || 0)
  const encours       = parseFloat(kpis.encours || 0)
  const plafond       = parseFloat(kpis.plafond || 0)
  const tranche120    = parseFloat(kpis.tranche_plus_120 || 0)
  const nbImpayes     = parseInt(kpis.nb_factures_impayees || 0)
  const tauxReglement = parseFloat(kpis.taux_reglement || 100)

  if (dso > 90)      { score -= 35; flags.push(`DSO critique : ${Math.round(dso)}j`) }
  else if (dso > 60) { score -= 25; flags.push(`DSO élevé : ${Math.round(dso)}j`) }
  else if (dso > 30) { score -= 12; flags.push(`DSO modéré : ${Math.round(dso)}j`) }

  if (plafond > 0) {
    const ratio = encours / plafond
    if (ratio > 1.0)      { score -= 25; flags.push(`Encours dépasse le plafond (${Math.round(ratio * 100)}%)`) }
    else if (ratio > 0.85){ score -= 15; flags.push(`Encours à ${Math.round(ratio * 100)}% du plafond`) }
  }

  if (tranche120 > 10000) { score -= 20; flags.push(`Retard >120j : ${tranche120.toLocaleString('fr-FR')} €`) }
  else if (tranche120 > 0){ score -= 10; flags.push(`Retard >120j : ${tranche120.toLocaleString('fr-FR')} €`) }

  if (nbImpayes > 10)     { score -= Math.min(nbImpayes * 2, 15); flags.push(`${nbImpayes} factures impayées`) }
  else if (nbImpayes > 3) { score -= 5;  flags.push(`${nbImpayes} factures impayées`) }

  if (tauxReglement < 50)      { score -= 15; flags.push(`Taux règlement faible : ${Math.round(tauxReglement)}%`) }
  else if (tauxReglement < 75) { score -= 7;  flags.push(`Taux règlement : ${Math.round(tauxReglement)}%`) }

  score = Math.max(0, Math.min(100, score))

  let niveau, couleur, libelle
  if (score >= 70)      { niveau = 'Vert';   couleur = '#10b981'; libelle = 'Bon payeur' }
  else if (score >= 40) { niveau = 'Orange'; couleur = '#f59e0b'; libelle = 'À surveiller' }
  else                  { niveau = 'Rouge';  couleur = '#ef4444'; libelle = 'Risque élevé' }

  return { score, niveau, couleur, libelle, flags }
}

function HealthScoreBadge({ kpis }) {
  const [expanded, setExpanded] = useState(false)
  if (!kpis || Object.keys(kpis).length === 0) return null

  const { score, couleur, libelle, flags } = computeHealthScore(kpis)

  const bgClass =
    score >= 70 ? 'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800/40' :
    score >= 40 ? 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800/40' :
                  'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800/40'

  const textClass =
    score >= 70 ? 'text-emerald-700 dark:text-emerald-400' :
    score >= 40 ? 'text-amber-700 dark:text-amber-400' :
                  'text-red-700 dark:text-red-400'

  return (
    <div className={`relative inline-block`}>
      <button
        onClick={() => setExpanded(v => !v)}
        className={`flex items-center gap-2 px-3 py-1.5 rounded-xl border text-sm font-semibold transition-all hover:shadow-sm ${bgClass} ${textClass}`}
      >
        {/* Arc de cercle SVG */}
        <svg width="32" height="32" viewBox="0 0 36 36">
          <circle cx="18" cy="18" r="15" fill="none" stroke="#e5e7eb" strokeWidth="3" />
          <circle
            cx="18" cy="18" r="15" fill="none"
            stroke={couleur} strokeWidth="3"
            strokeDasharray={`${(score / 100) * 94.2} 94.2`}
            strokeLinecap="round"
            transform="rotate(-90 18 18)"
          />
          <text x="18" y="22" textAnchor="middle" fontSize="10" fontWeight="700" fill={couleur}>{score}</text>
        </svg>
        <span>{libelle}</span>
        <Shield className="w-3.5 h-3.5 opacity-60" />
      </button>

      {expanded && flags.length > 0 && (
        <div className="absolute right-0 top-full mt-2 z-20 w-72 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-xl p-3">
          <div className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-2 uppercase tracking-wide">Points de vigilance</div>
          <ul className="space-y-1.5">
            {flags.map((f, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-gray-700 dark:text-gray-300">
                <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5 text-amber-500" />
                {f}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

const formatCurrency = (v) =>
  (v || 0).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

const formatDate = (d) => {
  if (!d || d === 'None' || d === 'null') return '-'
  try {
    return new Date(d).toLocaleDateString('fr-FR')
  } catch {
    return d
  }
}

const TrancheBadge = ({ tranche }) => {
  const colors = {
    'A échoir': 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
    '0-30 jours': 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
    '31-60 jours': 'bg-lime-100 text-lime-700 dark:bg-lime-900/30 dark:text-lime-300',
    '61-90 jours': 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
    '91-120 jours': 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
    '+120 jours': 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
  }
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${colors[tranche] || 'bg-gray-100 text-gray-600'}`}>
      {tranche}
    </span>
  )
}

// ─── Dialog recherche client ──────────────────────────────────────────────────
function ClientSearchDialog({ clients, loading, onSelect, onClose }) {
  const [search, setSearch] = useState('')
  const inputRef = useState(null)

  const filtered = useMemo(() =>
    clients.filter(c =>
      (c.nom_client || '').toLowerCase().includes(search.toLowerCase()) ||
      (c.commercial || '').toLowerCase().includes(search.toLowerCase())
    ), [clients, search])

  // Fermer sur Escape
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4" onClick={onClose}>
      <div
        className="w-full max-w-lg bg-white dark:bg-gray-800 rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-700 overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        {/* Barre de recherche */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-200 dark:border-gray-700">
          <Search className="w-5 h-5 text-gray-400 flex-shrink-0" />
          <input
            autoFocus
            type="text"
            placeholder="Rechercher un client par nom ou commercial..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="flex-1 bg-transparent text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none"
          />
          {search && (
            <button onClick={() => setSearch('')} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 text-xs">
              ✕
            </button>
          )}
        </div>

        {/* Résultats */}
        <div className="max-h-96 overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center h-24">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-500" />
            </div>
          ) : filtered.length === 0 ? (
            <p className="text-center text-sm text-gray-500 py-10">Aucun client trouvé</p>
          ) : (
            <>
              <p className="px-4 py-2 text-xs text-gray-400 border-b border-gray-100 dark:border-gray-700">
                {filtered.length} client{filtered.length !== 1 ? 's' : ''}
              </p>
              {filtered.map((c, idx) => (
                <button
                  key={`${c.code_client}-${idx}`}
                  onClick={() => { onSelect(c); onClose() }}
                  className="w-full text-left px-4 py-3 border-b border-gray-100 dark:border-gray-700/50 hover:bg-primary-50 dark:hover:bg-primary-900/20 transition-colors"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-gray-900 dark:text-white truncate">{c.nom_client}</p>
                      {c.commercial && (
                        <p className="text-xs text-gray-500 dark:text-gray-400">{c.commercial}</p>
                      )}
                    </div>
                    <div className="text-right flex-shrink-0">
                      {c.encours > 0 && (
                        <p className="text-xs font-semibold text-blue-600 dark:text-blue-400">{formatCurrency(c.encours)}</p>
                      )}
                      {c.impayes > 0 && (
                        <p className="text-xs text-red-500">{formatCurrency(c.impayes)} impayés</p>
                      )}
                    </div>
                  </div>
                </button>
              ))}
            </>
          )}
        </div>

        <div className="px-4 py-2 border-t border-gray-100 dark:border-gray-700 text-xs text-gray-400 flex justify-between">
          <span>↵ Sélectionner</span>
          <span>Esc Fermer</span>
        </div>
      </div>
    </div>
  )
}

// ─── Balance âgée graphique ───────────────────────────────────────────────────
function BalanceAgeeBar({ balance }) {
  const data = [
    { label: '0-30j', value: balance.tranche_0_30, color: TRANCHE_COLORS['0-30j'] },
    { label: '31-60j', value: balance.tranche_31_60, color: TRANCHE_COLORS['31-60j'] },
    { label: '61-90j', value: balance.tranche_61_90, color: TRANCHE_COLORS['61-90j'] },
    { label: '91-120j', value: balance.tranche_91_120, color: TRANCHE_COLORS['91-120j'] },
    { label: '+120j', value: balance.tranche_plus_120, color: TRANCHE_COLORS['+120j'] },
  ].filter(d => d.value > 0)

  if (data.length === 0) {
    return <p className="text-sm text-gray-500 text-center py-4">Aucun encours</p>
  }

  return (
    <ResponsiveContainer width="100%" height={160}>
      <BarChart data={data} margin={{ top: 4, right: 8, left: 8, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey="label" tick={{ fontSize: 11 }} />
        <YAxis tick={{ fontSize: 10 }} tickFormatter={v => v >= 1000 ? `${(v / 1000).toFixed(0)}K` : v} />
        <Tooltip formatter={v => formatCurrency(v)} />
        <Bar dataKey="value" radius={[3, 3, 0, 0]}>
          {data.map((entry, i) => (
            <Cell key={i} fill={entry.color} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

// ─── Évolution CA client ──────────────────────────────────────────────────────
function CAEvolutionChart({ data }) {
  if (!data || data.length === 0) {
    return <p className="text-sm text-gray-500 text-center py-8">Pas de données CA pour la période</p>
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={data} margin={{ top: 4, right: 8, left: 8, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey="mois" tick={{ fontSize: 10 }} />
        <YAxis tick={{ fontSize: 10 }} tickFormatter={v => v >= 1000 ? `${(v / 1000).toFixed(0)}K` : v} />
        <Tooltip formatter={v => formatCurrency(v)} />
        <Line
          type="monotone"
          dataKey="ca_ht"
          name="CA HT"
          stroke="var(--color-primary-500, #6366f1)"
          strokeWidth={2}
          dot={{ r: 3 }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}

// ─── Onglet documents ventes ──────────────────────────────────────────────────
const DOC_TYPE_FILTERS = ['Tous', 'Bon de livraison', 'Facture', 'Commande', 'Devis']

function DocumentsTab({ documents, docsSummary }) {
  const [typeFilter, setTypeFilter] = useState('Tous')

  const filtered = useMemo(() =>
    typeFilter === 'Tous' ? documents : documents.filter(d => d.type_doc === typeFilter),
    [documents, typeFilter]
  )

  // Types réellement présents dans les données
  const availableTypes = useMemo(() => {
    const types = new Set(documents.map(d => d.type_doc).filter(Boolean))
    return ['Tous', ...Array.from(types)]
  }, [documents])

  return (
    <div className="space-y-4">
      {/* Résumé par type */}
      {docsSummary.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {docsSummary.map((s, i) => (
            <button
              key={i}
              onClick={() => setTypeFilter(s.type_doc === typeFilter ? 'Tous' : s.type_doc)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm border transition-colors ${
                typeFilter === s.type_doc
                  ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300'
                  : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:border-gray-300'
              }`}
            >
              <Folder className="w-3.5 h-3.5" />
              <span className="font-medium">{s.type_doc}</span>
              <span className="px-1.5 py-0.5 rounded-full text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400">{s.count}</span>
              <span className="text-xs text-gray-500 dark:text-gray-400">{formatCurrency(s.montant_ttc)}</span>
            </button>
          ))}
        </div>
      )}

      {/* Table */}
      <div className="card overflow-hidden">
        {filtered.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 dark:bg-gray-800">
                <tr>
                  {['Société', 'Type', 'N° pièce', 'Date', 'Montant HT', 'Montant TTC', 'Réglé', 'Reste', 'Statut', 'Commercial'].map(h => (
                    <th key={h} className="px-3 py-2.5 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wide whitespace-nowrap">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                {filtered.map((d, i) => (
                  <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                    <td className="px-3 py-2 text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">{d.societe || '-'}</td>
                    <td className="px-3 py-2 whitespace-nowrap">
                      <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
                        {d.type_doc || '-'}
                      </span>
                    </td>
                    <td className="px-3 py-2 font-mono text-xs text-gray-700 dark:text-gray-300 whitespace-nowrap">{d.num_piece || '-'}</td>
                    <td className="px-3 py-2 text-gray-600 dark:text-gray-400 whitespace-nowrap">{formatDate(d.date)}</td>
                    <td className="px-3 py-2 text-right text-gray-700 dark:text-gray-300 whitespace-nowrap">{formatCurrency(d.montant_ht)}</td>
                    <td className="px-3 py-2 text-right font-medium text-gray-900 dark:text-white whitespace-nowrap">{formatCurrency(d.montant_ttc)}</td>
                    <td className="px-3 py-2 text-right text-emerald-600 dark:text-emerald-400 whitespace-nowrap">{formatCurrency(d.montant_regle)}</td>
                    <td className="px-3 py-2 text-right font-semibold whitespace-nowrap">
                      <span className={d.reste_a_regler > 0 ? 'text-red-600 dark:text-red-400' : 'text-gray-400'}>
                        {formatCurrency(d.reste_a_regler)}
                      </span>
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap">
                      {d.statut ? (
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                          d.statut === 'Soldé' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300'
                          : d.statut === 'Partiel' ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300'
                          : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
                        }`}>
                          {d.statut}
                        </span>
                      ) : '-'}
                    </td>
                    <td className="px-3 py-2 text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">{d.commercial || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-8 text-center">
            <Folder className="w-10 h-10 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
            <p className="text-gray-500">Aucun document pour la période sélectionnée</p>
          </div>
        )}
      </div>
      <p className="text-xs text-gray-400 text-right">{filtered.length} document{filtered.length !== 1 ? 's' : ''}</p>
    </div>
  )
}

// ─── Page principale ──────────────────────────────────────────────────────────
export default function FicheClient() {
  const [clients, setClients] = useState([])
  const [loadingList, setLoadingList] = useState(false)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [selectedClient, setSelectedClient] = useState(null)
  const [fiche, setFiche] = useState(null)
  const [loadingFiche, setLoadingFiche] = useState(false)
  const [activeTab, setActiveTab] = useState('overview')
  const [periode, setPeriode] = useState('annee_courante')

  // Charger la liste des clients à la première ouverture du dialog
  const handleOpenDialog = () => {
    setDialogOpen(true)
    if (clients.length === 0) loadClients()
  }

  // Recharger la fiche quand periode change
  useEffect(() => {
    if (selectedClient) loadFiche(selectedClient.code_client)
  }, [periode]) // eslint-disable-line react-hooks/exhaustive-deps

  const loadClients = async () => {
    setLoadingList(true)
    try {
      const res = await getFicheClientListe()
      setClients(res.data.data || [])
    } catch (e) {
      console.error('Erreur chargement clients:', e)
    } finally {
      setLoadingList(false)
    }
  }

  const loadFiche = async (codeClient) => {
    setLoadingFiche(true)
    setFiche(null)
    try {
      const res = await getFicheClient(codeClient, { periode })
      setFiche(res.data)
    } catch (e) {
      console.error('Erreur chargement fiche:', e)
    } finally {
      setLoadingFiche(false)
    }
  }

  const handleSelectClient = (client) => {
    setSelectedClient(client)
    setActiveTab('overview')
    loadFiche(client.code_client)
  }

  const periodeOptions = [
    { value: 'mois_courant', label: 'Mois courant' },
    { value: 'trimestre_courant', label: 'Trimestre' },
    { value: 'annee_courante', label: 'Année courante' },
    { value: 'annee_precedente', label: 'Année précédente' },
    { value: '12_derniers_mois', label: '12 derniers mois' },
  ]

  const kpis = fiche?.kpis || {}
  const balance = fiche?.balance_agee || {}
  const client = fiche?.client || {}

  const getDSOColor = (dso) => dso < 30 ? 'green' : dso < 60 ? 'yellow' : 'red'
  const getRiskLevel = () => {
    if (!fiche) return null
    if (kpis.tranche_plus_120 > 0) return { label: 'Risque élevé', color: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300' }
    if (kpis.impayes > 0) return { label: 'À surveiller', color: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300' }
    return { label: 'Bon payeur', color: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300' }
  }
  const risk = getRiskLevel()

  return (
    <div className="h-full">
      {/* ── Dialog recherche ── */}
      {dialogOpen && (
        <ClientSearchDialog
          clients={clients}
          loading={loadingList}
          onSelect={handleSelectClient}
          onClose={() => setDialogOpen(false)}
        />
      )}

      {/* ── Contenu principal pleine largeur ── */}
      <div className="overflow-y-auto bg-gray-50 dark:bg-gray-900 min-h-full">
        {!selectedClient ? (
          <div className="flex flex-col items-center justify-center h-[calc(100vh-120px)] text-gray-400">
            <User className="w-16 h-16 mb-4 opacity-20" />
            <p className="text-lg font-semibold text-gray-600 dark:text-gray-300">Fiche Client</p>
            <p className="text-sm mt-1 mb-6">Recherchez un client pour afficher sa fiche 360°</p>
            <button
              onClick={handleOpenDialog}
              className="flex items-center gap-2 px-5 py-2.5 bg-primary-600 hover:bg-primary-700 text-white rounded-xl font-medium text-sm transition-colors shadow"
            >
              <Search className="w-4 h-4" />
              Rechercher un client
            </button>
          </div>
        ) : loadingFiche ? (
          <div className="flex items-center justify-center h-[calc(100vh-120px)]">
            <Loading message={`Chargement de la fiche ${selectedClient.nom_client}...`} />
          </div>
        ) : fiche ? (
          <div className="p-6 space-y-5">
            {/* Header client */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-full bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center flex-shrink-0">
                  <User className="w-5 h-5 text-primary-600 dark:text-primary-400" />
                </div>
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <h1 className="text-xl font-bold text-gray-900 dark:text-white">
                      {client.nom || selectedClient.nom_client}
                    </h1>
                    {risk && (
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${risk.color}`}>
                        {risk.label}
                      </span>
                    )}
                    <HealthScoreBadge kpis={kpis} />
                  </div>
                  <div className="flex flex-wrap gap-3 mt-1 text-sm text-gray-500 dark:text-gray-400">
                    {client.commercial && (
                      <span className="flex items-center gap-1">
                        <User className="w-3.5 h-3.5" />
                        {client.commercial}
                      </span>
                    )}
                    {client.societe && (
                      <span className="flex items-center gap-1">
                        <ChevronRight className="w-3.5 h-3.5" />
                        {client.societe}
                      </span>
                    )}
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={handleOpenDialog}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                >
                  <Search className="w-3.5 h-3.5" />
                  Changer de client
                </button>
                <select
                  value={periode}
                  onChange={e => setPeriode(e.target.value)}
                  className="text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-primary-500"
                >
                  {periodeOptions.map(o => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
                <button
                  onClick={() => loadFiche(selectedClient.code_client)}
                  className="p-1.5 rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                  title="Rafraîchir"
                >
                  <RefreshCw className="w-4 h-4 text-gray-500" />
                </button>
              </div>
            </div>

            {/* KPIs */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
              <KPICard
                title="CA HT"
                formattedValue={formatCurrency(kpis.ca_ht)}
                icon={TrendingUp}
                color="primary"
              />
              <KPICard
                title="Encours"
                formattedValue={formatCurrency(kpis.encours)}
                icon={CreditCard}
                color="blue"
              />
              <KPICard
                title="Impayés"
                formattedValue={formatCurrency(kpis.impayes)}
                icon={AlertTriangle}
                color={kpis.impayes > 0 ? 'red' : 'green'}
              />
              <KPICard
                title="DSO Client"
                formattedValue={`${kpis.dso_client || 0} j`}
                icon={Clock}
                color={getDSOColor(kpis.dso_client)}
              />
              <KPICard
                title="Taux règlement"
                formattedValue={`${kpis.taux_reglement || 0}%`}
                icon={CheckCircle}
                color={kpis.taux_reglement >= 80 ? 'green' : kpis.taux_reglement >= 50 ? 'yellow' : 'red'}
              />
              <KPICard
                title="Factures impayées"
                formattedValue={String(kpis.nb_factures_impayees || 0)}
                icon={FileText}
                color={kpis.nb_factures_impayees > 0 ? 'yellow' : 'green'}
              />
            </div>

            {/* Tabs */}
            <div className="border-b border-gray-200 dark:border-gray-700">
              <nav className="flex gap-1">
                {TABS.map(tab => {
                  const Icon = tab.icon
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`
                        flex items-center gap-1.5 py-2.5 px-3 text-sm font-medium border-b-2 transition-colors
                        ${activeTab === tab.id
                          ? 'border-primary-500 text-primary-600 dark:text-primary-400'
                          : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400'
                        }
                      `}
                    >
                      <Icon className="w-3.5 h-3.5" />
                      {tab.label}
                      {tab.id === 'echeances' && kpis.nb_factures_impayees > 0 && (
                        <span className="ml-1 px-1.5 py-0.5 rounded-full text-xs bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400">
                          {kpis.nb_factures_impayees}
                        </span>
                      )}
                    </button>
                  )
                })}
              </nav>
            </div>

            {/* Tab: Vue générale */}
            {activeTab === 'overview' && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                {/* Balance âgée */}
                <div className="card p-5">
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Balance âgée</h3>
                  <BalanceAgeeBar balance={balance} />
                  <div className="grid grid-cols-5 gap-1 mt-3">
                    {[
                      { label: '0-30j', key: 'tranche_0_30', color: 'bg-emerald-500' },
                      { label: '31-60j', key: 'tranche_31_60', color: 'bg-lime-500' },
                      { label: '61-90j', key: 'tranche_61_90', color: 'bg-amber-500' },
                      { label: '91-120j', key: 'tranche_91_120', color: 'bg-orange-500' },
                      { label: '+120j', key: 'tranche_plus_120', color: 'bg-red-500' },
                    ].map(t => (
                      <div key={t.key} className="text-center">
                        <div className={`h-1 ${t.color} rounded-full mb-1`} />
                        <p className="text-xs text-gray-500 dark:text-gray-400">{t.label}</p>
                        <p className="text-xs font-semibold text-gray-800 dark:text-gray-200">
                          {formatCurrency(balance[t.key] || 0)}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Évolution CA */}
                <div className="card p-5">
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Évolution CA HT</h3>
                  <CAEvolutionChart data={fiche.ca_evolution} />
                </div>

                {/* Résumé financier */}
                <div className="card p-5">
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Résumé financier</h3>
                  <div className="space-y-2.5">
                    {[
                      { label: 'CA HT (période)', value: formatCurrency(kpis.ca_ht) },
                      { label: 'CA TTC (période)', value: formatCurrency(kpis.ca_ttc) },
                      { label: 'Nb transactions', value: kpis.nb_transactions || 0 },
                      { label: 'Nb produits distincts', value: kpis.nb_produits || 0 },
                      { label: 'Encours total', value: formatCurrency(kpis.encours), highlight: kpis.encours > 0 },
                      { label: 'Dont impayés', value: formatCurrency(kpis.impayes), alert: kpis.impayes > 0 },
                      { label: 'Créances +120j', value: formatCurrency(kpis.tranche_plus_120), alert: kpis.tranche_plus_120 > 0 },
                      { label: 'Dernier règlement', value: formatDate(kpis.dernier_reglement) || '-' },
                    ].map((row, i) => (
                      <div key={i} className="flex justify-between items-center py-1 border-b border-gray-100 dark:border-gray-700/50 last:border-0">
                        <span className="text-sm text-gray-600 dark:text-gray-400">{row.label}</span>
                        <span className={`text-sm font-semibold ${
                          row.alert ? 'text-red-600 dark:text-red-400'
                          : row.highlight ? 'text-blue-600 dark:text-blue-400'
                          : 'text-gray-900 dark:text-white'
                        }`}>
                          {row.value}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Répartition par tranche - détail */}
                <div className="card p-5">
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Répartition encours</h3>
                  {kpis.encours > 0 ? (
                    <div className="space-y-3">
                      {[
                        { label: '0 - 30 jours', key: 'tranche_0_30', color: 'bg-emerald-500' },
                        { label: '31 - 60 jours', key: 'tranche_31_60', color: 'bg-lime-500' },
                        { label: '61 - 90 jours', key: 'tranche_61_90', color: 'bg-amber-500' },
                        { label: '91 - 120 jours', key: 'tranche_91_120', color: 'bg-orange-500' },
                        { label: '+120 jours', key: 'tranche_plus_120', color: 'bg-red-500' },
                      ].map(t => {
                        const val = balance[t.key] || 0
                        const pct = kpis.encours > 0 ? Math.round(val / kpis.encours * 100) : 0
                        return (
                          <div key={t.key}>
                            <div className="flex justify-between text-xs mb-1">
                              <span className="text-gray-600 dark:text-gray-400">{t.label}</span>
                              <span className="font-medium text-gray-900 dark:text-white">
                                {formatCurrency(val)} ({pct}%)
                              </span>
                            </div>
                            <div className="w-full bg-gray-100 dark:bg-gray-700 rounded-full h-2">
                              <div
                                className={`${t.color} h-2 rounded-full transition-all`}
                                style={{ width: `${pct}%` }}
                              />
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  ) : (
                    <p className="text-sm text-gray-500 text-center py-4">Aucun encours</p>
                  )}
                </div>
              {/* Informations client Sage */}
              <div className="card p-5 lg:col-span-2">
                <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                  <Building2 className="w-4 h-4 text-primary-500" />
                  Informations client
                </h3>
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-x-6 gap-y-4">
                  {[
                    { icon: User,        label: 'Représentant',         value: client.commercial || fiche.info_sage?.commercial || '—' },
                    { icon: Shield,      label: 'Risque',                value: fiche.info_sage?.risque_client || '—' },
                    { icon: CreditCard,  label: 'Plafond autorisation',  value: fiche.info_sage?.plafond_autorisation > 0 ? formatCurrency(fiche.info_sage.plafond_autorisation) : '—' },
                    { icon: Shield,      label: 'Assurance',             value: fiche.info_sage?.assurance > 0 ? formatCurrency(fiche.info_sage.assurance) : '—' },
                    { icon: Phone,       label: 'Téléphone',             value: fiche.info_sage?.telephone || '—' },
                    { icon: Mail,        label: 'Email',                 value: fiche.info_sage?.email || '—' },
                    { icon: MapPin,      label: 'Adresse',               value: fiche.info_sage?.adresse || '—' },
                    { icon: MapPin,      label: 'Ville',                 value: fiche.info_sage?.ville || '—' },
                    { icon: FileText,    label: 'ICE',                   value: fiche.info_sage?.ice || '—', mono: true },
                    { icon: FileText,    label: 'RC',                    value: fiche.info_sage?.rc || '—', mono: true },
                    { icon: Building2,   label: 'Forme juridique',       value: fiche.info_sage?.forme_juridique || '—' },
                    { icon: TrendingUp,  label: 'Capital',               value: fiche.info_sage?.capital > 0 ? formatCurrency(fiche.info_sage.capital) : '—' },
                  ].map(({ icon: Icon, label, value, mono }) => (
                    <div key={label} className="flex items-start gap-2 min-w-0">
                      <Icon className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
                      <div className="min-w-0">
                        <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
                        <p className={`text-sm font-medium truncate ${mono ? 'font-mono' : ''} ${value === '—' ? 'text-gray-400 dark:text-gray-500' : 'text-gray-900 dark:text-white'}`}>
                          {value}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            )}

            {/* Tab: Documents ventes */}
            {activeTab === 'documents' && (
              <DocumentsTab documents={fiche.documents || []} docsSummary={fiche.docs_summary || []} />
            )}

            {/* Tab: Factures impayées */}
            {activeTab === 'echeances' && (
              <div className="space-y-3">
                {fiche.echeances?.length > 0 ? (
                  <>
                    <div className="card p-3 bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800">
                      <div className="flex items-center gap-2 text-amber-700 dark:text-amber-300">
                        <AlertTriangle className="w-4 h-4" />
                        <span className="text-sm font-medium">
                          {fiche.echeances.length} facture{fiche.echeances.length > 1 ? 's' : ''} non réglée{fiche.echeances.length > 1 ? 's' : ''} — total {formatCurrency(kpis.total_factures_impayees)}
                        </span>
                      </div>
                    </div>
                    <div className="card overflow-hidden">
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead className="bg-gray-50 dark:bg-gray-800">
                            <tr>
                              {['Pièce', 'Date doc.', 'Échéance', 'Montant', 'Réglé', 'Reste', 'Retard', 'Tranche'].map(h => (
                                <th key={h} className="px-3 py-2.5 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wide whitespace-nowrap">
                                  {h}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                            {fiche.echeances.map((e, i) => (
                              <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                                <td className="px-3 py-2 font-mono text-xs text-gray-700 dark:text-gray-300 whitespace-nowrap">
                                  {e.num_piece || '-'}
                                </td>
                                <td className="px-3 py-2 text-gray-600 dark:text-gray-400 whitespace-nowrap">
                                  {formatDate(e.date_document)}
                                </td>
                                <td className="px-3 py-2 text-gray-600 dark:text-gray-400 whitespace-nowrap">
                                  {formatDate(e.date_echeance)}
                                </td>
                                <td className="px-3 py-2 text-right font-medium text-gray-900 dark:text-white whitespace-nowrap">
                                  {formatCurrency(e.montant_echeance)}
                                </td>
                                <td className="px-3 py-2 text-right text-emerald-600 dark:text-emerald-400 whitespace-nowrap">
                                  {formatCurrency(e.montant_regle)}
                                </td>
                                <td className="px-3 py-2 text-right font-semibold text-red-600 dark:text-red-400 whitespace-nowrap">
                                  {formatCurrency(e.reste_a_regler)}
                                </td>
                                <td className="px-3 py-2 text-right whitespace-nowrap">
                                  {e.jours_retard > 0 ? (
                                    <span className="text-red-600 dark:text-red-400 font-medium">{e.jours_retard}j</span>
                                  ) : (
                                    <span className="text-blue-500">À venir</span>
                                  )}
                                </td>
                                <td className="px-3 py-2 whitespace-nowrap">
                                  <TrancheBadge tranche={e.tranche_age} />
                                </td>
                              </tr>
                            ))}
                          </tbody>
                          <tfoot className="bg-gray-50 dark:bg-gray-800">
                            <tr>
                              <td colSpan={3} className="px-3 py-2 text-xs font-semibold text-gray-600 dark:text-gray-400">Total</td>
                              <td className="px-3 py-2 text-right text-xs font-bold text-gray-900 dark:text-white">
                                {formatCurrency(fiche.echeances.reduce((s, e) => s + e.montant_echeance, 0))}
                              </td>
                              <td className="px-3 py-2 text-right text-xs font-bold text-emerald-600">
                                {formatCurrency(fiche.echeances.reduce((s, e) => s + e.montant_regle, 0))}
                              </td>
                              <td className="px-3 py-2 text-right text-xs font-bold text-red-600">
                                {formatCurrency(kpis.total_factures_impayees)}
                              </td>
                              <td colSpan={2} />
                            </tr>
                          </tfoot>
                        </table>
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="card p-8 text-center">
                    <CheckCircle className="w-10 h-10 text-emerald-500 mx-auto mb-3" />
                    <p className="font-medium text-gray-900 dark:text-white">Aucune facture impayée</p>
                    <p className="text-sm text-gray-500 mt-1">Ce client est à jour dans ses paiements</p>
                  </div>
                )}
              </div>
            )}

            {/* Tab: Historique règlements */}
            {activeTab === 'reglements' && (
              <div className="card overflow-hidden">
                {fiche.reglements?.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-gray-50 dark:bg-gray-800">
                        <tr>
                          {['Date règlement', 'Pièce', 'Date document', 'Montant facture', 'Montant réglé', 'Mode', 'Délai (j)'].map(h => (
                            <th key={h} className="px-3 py-2.5 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wide whitespace-nowrap">
                              {h}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                        {fiche.reglements.map((r, i) => (
                          <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                            <td className="px-3 py-2 font-medium text-gray-900 dark:text-white whitespace-nowrap">
                              {formatDate(r.date_reglement)}
                            </td>
                            <td className="px-3 py-2 font-mono text-xs text-gray-700 dark:text-gray-300 whitespace-nowrap">
                              {r.num_piece || '-'}
                            </td>
                            <td className="px-3 py-2 text-gray-500 dark:text-gray-400 whitespace-nowrap">
                              {formatDate(r.date_document)}
                            </td>
                            <td className="px-3 py-2 text-right text-gray-700 dark:text-gray-300 whitespace-nowrap">
                              {formatCurrency(r.montant_facture)}
                            </td>
                            <td className="px-3 py-2 text-right font-semibold text-emerald-600 dark:text-emerald-400 whitespace-nowrap">
                              {formatCurrency(r.montant_reglement)}
                            </td>
                            <td className="px-3 py-2 text-gray-500 dark:text-gray-400 whitespace-nowrap">
                              {r.mode_reglement || '-'}
                            </td>
                            <td className="px-3 py-2 text-right whitespace-nowrap">
                              {r.delai_jours > 0 ? (
                                <span className={r.delai_jours > 60 ? 'text-red-500' : r.delai_jours > 30 ? 'text-amber-500' : 'text-emerald-500'}>
                                  {r.delai_jours}j
                                </span>
                              ) : '-'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="p-8 text-center">
                    <p className="text-gray-500">Aucun règlement trouvé pour ce client</p>
                  </div>
                )}
              </div>
            )}

            {/* Tab: Top produits */}
            {activeTab === 'produits' && (
              <div className="card overflow-hidden">
                {fiche.top_produits?.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-gray-50 dark:bg-gray-800">
                        <tr>
                          {['Code', 'Désignation', 'Gamme', 'Qté vendue', 'CA HT', '% CA'].map(h => (
                            <th key={h} className="px-3 py-2.5 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wide whitespace-nowrap">
                              {h}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                        {fiche.top_produits.map((p, i) => {
                          const pct = kpis.ca_ht > 0 ? Math.round(p.ca_ht / kpis.ca_ht * 100) : 0
                          return (
                            <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                              <td className="px-3 py-2 font-mono text-xs text-gray-500 dark:text-gray-400">{p.code_article}</td>
                              <td className="px-3 py-2 text-gray-900 dark:text-white font-medium">{p.designation}</td>
                              <td className="px-3 py-2 text-gray-500 dark:text-gray-400">{p.gamme || '-'}</td>
                              <td className="px-3 py-2 text-right text-gray-700 dark:text-gray-300">
                                {(p.quantite || 0).toLocaleString('fr-FR', { maximumFractionDigits: 0 })}
                              </td>
                              <td className="px-3 py-2 text-right font-semibold text-gray-900 dark:text-white">
                                {formatCurrency(p.ca_ht)}
                              </td>
                              <td className="px-3 py-2 text-right">
                                <div className="flex items-center justify-end gap-2">
                                  <div className="w-16 bg-gray-100 dark:bg-gray-700 rounded-full h-1.5">
                                    <div
                                      className="bg-primary-500 h-1.5 rounded-full"
                                      style={{ width: `${pct}%` }}
                                    />
                                  </div>
                                  <span className="text-xs text-gray-500 w-8 text-right">{pct}%</span>
                                </div>
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="p-8 text-center">
                    <p className="text-gray-500">Aucune donnée produit pour la période sélectionnée</p>
                  </div>
                )}
              </div>
            )}
          </div>
        ) : null}
      </div>
    </div>
  )
}
