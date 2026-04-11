import { useState, useEffect, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  User, Search, TrendingUp, CreditCard, Clock, AlertTriangle,
  CheckCircle, FileText, BarChart2, RefreshCw, ChevronRight,
  Building2, Phone, Mail, MapPin, Shield, Folder, ShoppingCart, ArrowRight
} from 'lucide-react'
import KPICard from '../components/Dashboard/KPICard'
import Loading from '../components/common/Loading'
import { getFicheFournisseurListe, getFicheFournisseur } from '../services/api'
import { useGlobalFilters } from '../context/GlobalFilterContext'
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell
} from 'recharts'

const TABS = [
  { id: 'overview', label: 'Vue générale', icon: BarChart2 },
  { id: 'documents', label: 'Documents achats', icon: Folder },
  { id: 'echeances', label: 'Échéances dues', icon: AlertTriangle },
  { id: 'paiements', label: 'Historique paiements', icon: CheckCircle },
]

const TRANCHE_COLORS = {
  'A echoir': '#3b82f6',
  '0-30j': '#10b981',
  '31-60j': '#84cc16',
  '61-90j': '#f59e0b',
  '91-120j': '#f97316',
  '+120j': '#ef4444',
}

const formatCurrency = (v) =>
  (v || 0).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

const formatDate = (d) => {
  if (!d || d === 'None' || d === 'null') return '-'
  try { return new Date(d).toLocaleDateString('fr-FR') } catch { return d }
}

const TrancheBadge = ({ tranche }) => {
  const colors = {
    'A echoir': 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
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

// ─── Dialog recherche fournisseur ─────────────────────────────────────────────
function FournisseurSearchDialog({ fournisseurs, loading, onSelect, onClose }) {
  const [search, setSearch] = useState('')

  const filtered = useMemo(() =>
    fournisseurs.filter(f =>
      (f.nom_fournisseur || '').toLowerCase().includes(search.toLowerCase()) ||
      (f.acheteur || '').toLowerCase().includes(search.toLowerCase())
    ), [fournisseurs, search])

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
        <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-200 dark:border-gray-700">
          <Search className="w-5 h-5 text-gray-400 flex-shrink-0" />
          <input
            autoFocus
            type="text"
            placeholder="Rechercher un fournisseur par nom ou acheteur..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="flex-1 bg-transparent text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none"
          />
          {search && (
            <button onClick={() => setSearch('')} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 text-xs">✕</button>
          )}
        </div>

        <div className="max-h-96 overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center h-24">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-500" />
            </div>
          ) : filtered.length === 0 ? (
            <p className="text-center text-sm text-gray-500 py-10">Aucun fournisseur trouvé</p>
          ) : (
            <>
              <p className="px-4 py-2 text-xs text-gray-400 border-b border-gray-100 dark:border-gray-700">
                {filtered.length} fournisseur{filtered.length !== 1 ? 's' : ''}
              </p>
              {filtered.map((f, idx) => (
                <button
                  key={`${f.nom_fournisseur}-${idx}`}
                  onClick={() => { onSelect(f); onClose() }}
                  className="w-full text-left px-4 py-3 border-b border-gray-100 dark:border-gray-700/50 hover:bg-primary-50 dark:hover:bg-primary-900/20 transition-colors"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-gray-900 dark:text-white truncate">{f.nom_fournisseur}</p>
                      {f.acheteur && (
                        <p className="text-xs text-gray-500 dark:text-gray-400">{f.acheteur}</p>
                      )}
                    </div>
                    <div className="text-right flex-shrink-0">
                      {f.total_achats > 0 && (
                        <p className="text-xs font-semibold text-blue-600 dark:text-blue-400">{formatCurrency(f.total_achats)}</p>
                      )}
                      {f.solde > 0 && (
                        <p className="text-xs text-amber-600">{formatCurrency(f.solde)} dû</p>
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

// ─── Graphique évolution achats ────────────────────────────────────────────────
function AchatsEvolutionChart({ data }) {
  if (!data || data.length === 0) {
    return <p className="text-sm text-gray-500 text-center py-8">Pas de données pour la période</p>
  }
  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={data} margin={{ top: 4, right: 8, left: 8, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey="mois" tick={{ fontSize: 10 }} />
        <YAxis tick={{ fontSize: 10 }} tickFormatter={v => v >= 1000 ? `${(v / 1000).toFixed(0)}K` : v} />
        <Tooltip formatter={v => formatCurrency(v)} />
        <Line type="monotone" dataKey="montant_ttc" name="Montant TTC" stroke="#f59e0b" strokeWidth={2} dot={{ r: 3 }} />
      </LineChart>
    </ResponsiveContainer>
  )
}

// ─── Onglet documents achats ──────────────────────────────────────────────────
function DocumentsTab({ documents, docsSummary }) {
  const [typeFilter, setTypeFilter] = useState('Tous')

  const filtered = useMemo(() =>
    typeFilter === 'Tous' ? documents : documents.filter(d => d.type_doc === typeFilter),
    [documents, typeFilter]
  )

  return (
    <div className="space-y-4">
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
      <div className="card overflow-hidden">
        {filtered.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 dark:bg-gray-800">
                <tr>
                  {['Société', 'Type', 'N° pièce', 'Date', 'Montant HT', 'Montant TTC', 'Réglé', 'Reste', 'Statut', 'Acheteur'].map(h => (
                    <th key={h} className="px-3 py-2.5 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wide whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                {filtered.map((d, i) => (
                  <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                    <td className="px-3 py-2 text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">{d.societe || '-'}</td>
                    <td className="px-3 py-2 whitespace-nowrap">
                      <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">{d.type_doc || '-'}</span>
                    </td>
                    <td className="px-3 py-2 font-mono text-xs text-gray-700 dark:text-gray-300 whitespace-nowrap">{d.num_piece || '-'}</td>
                    <td className="px-3 py-2 text-gray-600 dark:text-gray-400 whitespace-nowrap">{formatDate(d.date)}</td>
                    <td className="px-3 py-2 text-right text-gray-700 dark:text-gray-300 whitespace-nowrap">{formatCurrency(d.montant_ht)}</td>
                    <td className="px-3 py-2 text-right font-medium text-gray-900 dark:text-white whitespace-nowrap">{formatCurrency(d.montant_ttc)}</td>
                    <td className="px-3 py-2 text-right text-emerald-600 dark:text-emerald-400 whitespace-nowrap">{formatCurrency(d.montant_regle)}</td>
                    <td className="px-3 py-2 text-right font-semibold whitespace-nowrap">
                      <span className={d.reste_a_regler > 0 ? 'text-red-600 dark:text-red-400' : 'text-gray-400'}>{formatCurrency(d.reste_a_regler)}</span>
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap">
                      {d.statut ? (
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                          d.statut === 'Soldé' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300'
                          : d.statut === 'Partiel' ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300'
                          : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
                        }`}>{d.statut}</span>
                      ) : '-'}
                    </td>
                    <td className="px-3 py-2 text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">{d.acheteur || '-'}</td>
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
export default function FicheFournisseur() {
  const [searchParams] = useSearchParams()
  const { updateFilter } = useGlobalFilters()
  const [fournisseurs, setFournisseurs] = useState([])
  const [loadingList, setLoadingList] = useState(false)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [selectedFournisseur, setSelectedFournisseur] = useState(null)
  const [fiche, setFiche] = useState(null)
  const [loadingFiche, setLoadingFiche] = useState(false)
  const [activeTab, setActiveTab] = useState('overview')
  const [periode, setPeriode] = useState('annee_courante')

  useEffect(() => {
    if (selectedFournisseur) loadFiche(selectedFournisseur.nom_fournisseur)
  }, [periode]) // eslint-disable-line react-hooks/exhaustive-deps

  // Drill-through entrant : auto-sélectionner le fournisseur depuis l'URL
  useEffect(() => {
    const dtField = searchParams.get('dt_field')
    const dtValue = searchParams.get('dt_value')
    const gfDateDebut = searchParams.get('gf_dateDebut')
    const gfDateFin = searchParams.get('gf_dateFin')
    const gfSociete = searchParams.get('gf_societe')
    if (gfDateDebut) updateFilter('dateDebut', gfDateDebut)
    if (gfDateFin) updateFilter('dateFin', gfDateFin)
    if (gfSociete) updateFilter('societe', gfSociete)
    if (dtValue && (dtField === 'CT_Num' || dtField === 'code_fournisseur' || dtField === 'fournisseur' || dtField === 'nom_fournisseur')) {
      setFiche(null)
      loadFiche(dtValue)
      setSelectedFournisseur({ nom_fournisseur: dtValue, code_fournisseur: dtValue })
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleOpenDialog = () => {
    setDialogOpen(true)
    if (fournisseurs.length === 0) loadFournisseurs()
  }

  const loadFournisseurs = async () => {
    setLoadingList(true)
    try {
      const res = await getFicheFournisseurListe()
      setFournisseurs(res.data.data || [])
    } catch (e) {
      console.error('Erreur chargement fournisseurs:', e)
    } finally {
      setLoadingList(false)
    }
  }

  const loadFiche = async (nomFournisseur) => {
    setLoadingFiche(true)
    setFiche(null)
    try {
      const res = await getFicheFournisseur(nomFournisseur, { periode })
      setFiche(res.data)
    } catch (e) {
      console.error('Erreur chargement fiche:', e)
    } finally {
      setLoadingFiche(false)
    }
  }

  const handleSelectFournisseur = (f) => {
    setSelectedFournisseur(f)
    setActiveTab('overview')
    loadFiche(f.nom_fournisseur)
  }

  const periodeOptions = [
    { value: 'mois_courant', label: 'Mois courant' },
    { value: 'trimestre_courant', label: 'Trimestre' },
    { value: 'annee_courante', label: 'Année courante' },
    { value: 'annee_precedente', label: 'Année précédente' },
    { value: '12_derniers_mois', label: '12 derniers mois' },
  ]

  const kpis = fiche?.kpis || {}
  const fournisseur = fiche?.fournisseur || {}

  const dtSource = searchParams.get('dt_source')
  const dtField = searchParams.get('dt_field')
  const dtValue = searchParams.get('dt_value')

  return (
    <div className="h-full">
      {dtField && dtValue && selectedFournisseur && (
        <div className="flex items-center gap-2 px-4 py-1.5 bg-blue-50 dark:bg-blue-900/20 border-b border-blue-200 dark:border-blue-800/30 text-xs text-blue-700 dark:text-blue-300">
          <ArrowRight className="w-3.5 h-3.5 flex-shrink-0" />
          <span>Accédé depuis <b>{dtSource || 'rapport source'}</b></span>
        </div>
      )}
      {dialogOpen && (
        <FournisseurSearchDialog
          fournisseurs={fournisseurs}
          loading={loadingList}
          onSelect={handleSelectFournisseur}
          onClose={() => setDialogOpen(false)}
        />
      )}

      <div className="overflow-y-auto bg-gray-50 dark:bg-gray-900 min-h-full">
        {!selectedFournisseur ? (
          <div className="flex flex-col items-center justify-center h-[calc(100vh-120px)] text-gray-400">
            <ShoppingCart className="w-16 h-16 mb-4 opacity-20" />
            <p className="text-lg font-semibold text-gray-600 dark:text-gray-300">Fiche Fournisseur</p>
            <p className="text-sm mt-1 mb-6">Recherchez un fournisseur pour afficher sa fiche 360°</p>
            <button
              onClick={handleOpenDialog}
              className="flex items-center gap-2 px-5 py-2.5 bg-primary-600 hover:bg-primary-700 text-white rounded-xl font-medium text-sm transition-colors shadow"
            >
              <Search className="w-4 h-4" />
              Rechercher un fournisseur
            </button>
          </div>
        ) : loadingFiche ? (
          <div className="flex items-center justify-center h-[calc(100vh-120px)]">
            <Loading message={`Chargement de la fiche ${selectedFournisseur.nom_fournisseur}...`} />
          </div>
        ) : fiche ? (
          <div className="p-6 space-y-5">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-full bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center flex-shrink-0">
                  <ShoppingCart className="w-5 h-5 text-amber-600 dark:text-amber-400" />
                </div>
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <h1 className="text-xl font-bold text-gray-900 dark:text-white">
                      {fournisseur.nom || selectedFournisseur.nom_fournisseur}
                    </h1>
                    {fiche.info_sage?.risque_fournisseur && fiche.info_sage.risque_fournisseur !== '—' && (
                      <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
                        {fiche.info_sage.risque_fournisseur}
                      </span>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-3 mt-1 text-sm text-gray-500 dark:text-gray-400">
                    {fournisseur.acheteur && (
                      <span className="flex items-center gap-1"><User className="w-3.5 h-3.5" />{fournisseur.acheteur}</span>
                    )}
                    {fournisseur.code && (
                      <span className="flex items-center gap-1"><ChevronRight className="w-3.5 h-3.5" />{fournisseur.code}</span>
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
                  Changer de fournisseur
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
                  onClick={() => loadFiche(selectedFournisseur.nom_fournisseur)}
                  className="p-1.5 rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                  title="Rafraîchir"
                >
                  <RefreshCw className="w-4 h-4 text-gray-500" />
                </button>
              </div>
            </div>

            {/* KPIs */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
              <KPICard title="Achats TTC (période)" formattedValue={formatCurrency(kpis.achats_ttc)} icon={TrendingUp} color="primary" />
              <KPICard title="Solde dû" formattedValue={formatCurrency(kpis.solde)} icon={CreditCard} color={kpis.solde > 0 ? 'yellow' : 'green'} />
              <KPICard title="Échéances dues" formattedValue={formatCurrency(kpis.total_echeances_dues)} icon={AlertTriangle} color={kpis.total_echeances_dues > 0 ? 'red' : 'green'} />
              <KPICard title="Paiements" formattedValue={formatCurrency(kpis.total_paiements)} icon={CheckCircle} color="green" />
              <KPICard title="Nb factures dues" formattedValue={String(kpis.nb_echeances || 0)} icon={FileText} color={kpis.nb_echeances > 0 ? 'yellow' : 'green'} />
              <KPICard title="Nb documents" formattedValue={String(kpis.nb_documents || 0)} icon={Folder} color="blue" />
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
                      className={`flex items-center gap-1.5 py-2.5 px-3 text-sm font-medium border-b-2 transition-colors ${
                        activeTab === tab.id
                          ? 'border-primary-500 text-primary-600 dark:text-primary-400'
                          : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400'
                      }`}
                    >
                      <Icon className="w-3.5 h-3.5" />
                      {tab.label}
                      {tab.id === 'echeances' && kpis.nb_echeances > 0 && (
                        <span className="ml-1 px-1.5 py-0.5 rounded-full text-xs bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400">
                          {kpis.nb_echeances}
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
                {/* Évolution achats */}
                <div className="card p-5">
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Évolution achats TTC</h3>
                  <AchatsEvolutionChart data={fiche.achats_evolution} />
                </div>

                {/* Résumé financier */}
                <div className="card p-5">
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Résumé financier</h3>
                  <div className="space-y-2.5">
                    {[
                      { label: 'Achats HT (période)', value: formatCurrency(kpis.achats_ht) },
                      { label: 'Achats TTC (période)', value: formatCurrency(kpis.achats_ttc) },
                      { label: 'Nb documents période', value: kpis.nb_documents || 0 },
                      { label: 'Total achats cumulé', value: formatCurrency(kpis.total_achats), highlight: true },
                      { label: 'Total réglé cumulé', value: formatCurrency(kpis.total_regle_global) },
                      { label: 'Solde dû', value: formatCurrency(kpis.solde), alert: kpis.solde > 0 },
                      { label: 'Échéances dues', value: formatCurrency(kpis.total_echeances_dues), alert: kpis.total_echeances_dues > 0 },
                      { label: 'Dernier paiement', value: formatDate(kpis.dernier_paiement) || '-' },
                    ].map((row, i) => (
                      <div key={i} className="flex justify-between items-center py-1 border-b border-gray-100 dark:border-gray-700/50 last:border-0">
                        <span className="text-sm text-gray-600 dark:text-gray-400">{row.label}</span>
                        <span className={`text-sm font-semibold ${
                          row.alert ? 'text-red-600 dark:text-red-400'
                          : row.highlight ? 'text-blue-600 dark:text-blue-400'
                          : 'text-gray-900 dark:text-white'
                        }`}>{row.value}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Informations fournisseur */}
                <div className="card p-5 lg:col-span-2">
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                    <Building2 className="w-4 h-4 text-primary-500" />
                    Informations fournisseur
                  </h3>
                  <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-x-6 gap-y-4">
                    {[
                      { icon: User,        label: 'Acheteur',              value: fournisseur.acheteur || '—' },
                      { icon: Shield,      label: 'Risque',                value: fiche.info_sage?.risque_fournisseur || '—' },
                      { icon: CreditCard,  label: 'Plafond autorisation',  value: fiche.info_sage?.plafond_autorisation > 0 ? formatCurrency(fiche.info_sage.plafond_autorisation) : '—' },
                      { icon: Shield,      label: 'Assurance',             value: fiche.info_sage?.assurance > 0 ? formatCurrency(fiche.info_sage.assurance) : '—' },
                      { icon: Phone,       label: 'Téléphone',             value: fiche.info_sage?.telephone || '—' },
                      { icon: Phone,       label: 'Fax',                   value: fiche.info_sage?.fax || '—' },
                      { icon: Mail,        label: 'Email',                 value: fiche.info_sage?.email || '—' },
                      { icon: MapPin,      label: 'Adresse',               value: fiche.info_sage?.adresse || '—' },
                      { icon: MapPin,      label: 'Ville',                 value: fiche.info_sage?.ville || '—' },
                      { icon: FileText,    label: 'ICE',                   value: fiche.info_sage?.ice || '—', mono: true },
                      { icon: FileText,    label: 'RC',                    value: fiche.info_sage?.rc || '—', mono: true },
                      { icon: Building2,   label: 'Forme juridique',       value: fiche.info_sage?.forme_juridique || '—' },
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

            {/* Tab: Documents achats */}
            {activeTab === 'documents' && (
              <DocumentsTab documents={fiche.documents || []} docsSummary={fiche.docs_summary || []} />
            )}

            {/* Tab: Échéances dues */}
            {activeTab === 'echeances' && (
              <div className="space-y-3">
                {fiche.echeances?.length > 0 ? (
                  <>
                    <div className="card p-3 bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800">
                      <div className="flex items-center gap-2 text-red-700 dark:text-red-300">
                        <AlertTriangle className="w-4 h-4" />
                        <span className="text-sm font-medium">
                          {fiche.echeances.length} échéance{fiche.echeances.length > 1 ? 's' : ''} due{fiche.echeances.length > 1 ? 's' : ''} — total {formatCurrency(kpis.total_echeances_dues)}
                        </span>
                      </div>
                    </div>
                    <div className="card overflow-hidden">
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead className="bg-gray-50 dark:bg-gray-800">
                            <tr>
                              {['Pièce', 'Date doc.', 'Échéance', 'Montant', 'Réglé', 'Reste', 'Retard', 'Tranche'].map(h => (
                                <th key={h} className="px-3 py-2.5 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wide whitespace-nowrap">{h}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                            {fiche.echeances.map((e, i) => (
                              <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                                <td className="px-3 py-2 font-mono text-xs text-gray-700 dark:text-gray-300 whitespace-nowrap">{e.num_piece || '-'}</td>
                                <td className="px-3 py-2 text-gray-600 dark:text-gray-400 whitespace-nowrap">{formatDate(e.date_document)}</td>
                                <td className="px-3 py-2 text-gray-600 dark:text-gray-400 whitespace-nowrap">{formatDate(e.date_echeance)}</td>
                                <td className="px-3 py-2 text-right font-medium text-gray-900 dark:text-white whitespace-nowrap">{formatCurrency(e.montant_echeance)}</td>
                                <td className="px-3 py-2 text-right text-emerald-600 dark:text-emerald-400 whitespace-nowrap">{formatCurrency(e.montant_regle)}</td>
                                <td className="px-3 py-2 text-right font-semibold text-red-600 dark:text-red-400 whitespace-nowrap">{formatCurrency(e.reste_a_regler)}</td>
                                <td className="px-3 py-2 text-right whitespace-nowrap">
                                  {e.jours_retard > 0 ? (
                                    <span className="text-red-600 dark:text-red-400 font-medium">{e.jours_retard}j</span>
                                  ) : (
                                    <span className="text-blue-500">À venir</span>
                                  )}
                                </td>
                                <td className="px-3 py-2 whitespace-nowrap"><TrancheBadge tranche={e.tranche_age} /></td>
                              </tr>
                            ))}
                          </tbody>
                          <tfoot className="bg-gray-50 dark:bg-gray-800">
                            <tr>
                              <td colSpan={3} className="px-3 py-2 text-xs font-semibold text-gray-600 dark:text-gray-400">Total</td>
                              <td className="px-3 py-2 text-right text-xs font-bold text-gray-900 dark:text-white">{formatCurrency(fiche.echeances.reduce((s, e) => s + e.montant_echeance, 0))}</td>
                              <td className="px-3 py-2 text-right text-xs font-bold text-emerald-600">{formatCurrency(fiche.echeances.reduce((s, e) => s + e.montant_regle, 0))}</td>
                              <td className="px-3 py-2 text-right text-xs font-bold text-red-600">{formatCurrency(kpis.total_echeances_dues)}</td>
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
                    <p className="font-medium text-gray-900 dark:text-white">Aucune échéance en retard</p>
                    <p className="text-sm text-gray-500 mt-1">Ce fournisseur est à jour</p>
                  </div>
                )}
              </div>
            )}

            {/* Tab: Historique paiements */}
            {activeTab === 'paiements' && (
              <div className="card overflow-hidden">
                {fiche.paiements?.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-gray-50 dark:bg-gray-800">
                        <tr>
                          {['Date paiement', 'N° pièce', 'Date échéance', 'Mode règlement', 'Montant'].map(h => (
                            <th key={h} className="px-3 py-2.5 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wide whitespace-nowrap">{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                        {fiche.paiements.map((p, i) => (
                          <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                            <td className="px-3 py-2 font-medium text-gray-900 dark:text-white whitespace-nowrap">{formatDate(p.date_paiement)}</td>
                            <td className="px-3 py-2 font-mono text-xs text-gray-700 dark:text-gray-300 whitespace-nowrap">{p.num_piece || '-'}</td>
                            <td className="px-3 py-2 text-gray-500 dark:text-gray-400 whitespace-nowrap">{formatDate(p.date_echeance)}</td>
                            <td className="px-3 py-2 text-gray-500 dark:text-gray-400 whitespace-nowrap">{p.mode_reglement || '-'}</td>
                            <td className="px-3 py-2 text-right font-semibold text-emerald-600 dark:text-emerald-400 whitespace-nowrap">{formatCurrency(p.montant)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="p-8 text-center">
                    <p className="text-gray-500">Aucun paiement trouvé pour ce fournisseur</p>
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
