import { useState, useEffect, useCallback } from 'react'
import {
  TrendingUp,
  TrendingDown,
  Users,
  FileText,
  DollarSign,
  AlertTriangle,
  Calendar,
  RefreshCw,
  Filter,
  BarChart3,
  PieChart,
  Layers
} from 'lucide-react'
import Loading from '../components/common/Loading'
import {
  getAnalyseKpis,
  getAnalyseTopClientsCA,
  getAnalyseTopClientsCreances,
  getAnalyseCAParMois,
  getAnalyseCAParCommercial,
  getAnalyseFiltres,
  getAnalyseBalanceAgeeTranche,
  getAnalyseBalanceAgeeDetail
} from '../services/api'

// Definition des onglets
const TABS = [
  { id: 'synthese', label: 'Synthese', icon: Layers },
  { id: 'ca', label: 'Chiffre d\'Affaires', icon: BarChart3 },
  { id: 'creances', label: 'Creances', icon: AlertTriangle },
  { id: 'balance', label: 'Balance Agee', icon: PieChart }
]

export default function AnalyseCACreances() {
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('synthese')
  const [kpis, setKpis] = useState(null)
  const [topClientsCA, setTopClientsCA] = useState([])
  const [topClientsCreances, setTopClientsCreances] = useState([])
  const [caParMois, setCaParMois] = useState([])
  const [caParCommercial, setCaParCommercial] = useState([])
  const [balanceAgeeTranche, setBalanceAgeeTranche] = useState(null)
  const [balanceAgeeDetail, setBalanceAgeeDetail] = useState([])
  const [filtres, setFiltres] = useState({ societes: [], representants: [], regions: [], groupes: [] })

  const [selectedSociete, setSelectedSociete] = useState('')
  const [selectedRepresentant, setSelectedRepresentant] = useState('')
  const [selectedRegion, setSelectedRegion] = useState('')
  const [selectedGroupe, setSelectedGroupe] = useState('')

  // Format en millions
  const formatMillions = (value) => {
    const millions = (value || 0) / 1000000
    return new Intl.NumberFormat('fr-FR', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(millions) + ' M'
  }

  // Format nombre
  const formatNumber = (value) => {
    return new Intl.NumberFormat('fr-FR').format(value || 0)
  }

  // Format pourcentage
  const formatPercent = (value) => {
    return new Intl.NumberFormat('fr-FR', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value || 0) + ' %'
  }

  // Charger les filtres
  const loadFiltres = useCallback(async () => {
    try {
      const response = await getAnalyseFiltres()
      if (response.data.success) {
        setFiltres({
          societes: response.data.societes || [],
          representants: response.data.representants || [],
          regions: response.data.regions || [],
          groupes: response.data.groupes || []
        })
      }
    } catch (error) {
      console.error('Erreur chargement filtres:', error)
    }
  }, [])

  // Charger les donnees
  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const params = {}
      if (selectedSociete) params.societe = selectedSociete
      if (selectedRepresentant) params.representant = selectedRepresentant
      if (selectedRegion) params.region = selectedRegion
      if (selectedGroupe) params.groupe = selectedGroupe

      const [kpisRes, topCARes, topCreancesRes, caParMoisRes, caParCommercialRes, balanceAgeeRes, balanceDetailRes] = await Promise.all([
        getAnalyseKpis(params),
        getAnalyseTopClientsCA({ ...params, limit: 10 }),
        getAnalyseTopClientsCreances({ ...params, limit: 10 }),
        getAnalyseCAParMois(params),
        getAnalyseCAParCommercial(params),
        getAnalyseBalanceAgeeTranche(params),
        getAnalyseBalanceAgeeDetail({ ...params, limit: 100 })
      ])

      if (kpisRes.data.success) setKpis(kpisRes.data.kpis)
      if (topCARes.data.success) setTopClientsCA(topCARes.data.data)
      if (topCreancesRes.data.success) setTopClientsCreances(topCreancesRes.data.data)
      if (caParMoisRes.data.success) setCaParMois(caParMoisRes.data.data)
      if (caParCommercialRes.data.success) setCaParCommercial(caParCommercialRes.data.data)
      if (balanceAgeeRes.data.success) setBalanceAgeeTranche(balanceAgeeRes.data.data)
      if (balanceDetailRes.data.success) setBalanceAgeeDetail(balanceDetailRes.data.data)

    } catch (error) {
      console.error('Erreur chargement donnees:', error)
    } finally {
      setLoading(false)
    }
  }, [selectedSociete, selectedRepresentant, selectedRegion, selectedGroupe])

  useEffect(() => {
    loadFiltres()
  }, [loadFiltres])

  useEffect(() => {
    loadData()
  }, [loadData])

  if (loading) {
    return <Loading />
  }

  // Composant Tab pour la navigation
  const TabButton = ({ tab }) => {
    const Icon = tab.icon
    const isActive = activeTab === tab.id
    return (
      <button
        onClick={() => setActiveTab(tab.id)}
        className={`
          flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-t-lg border-b-2 transition-all
          ${isActive
            ? 'border-primary-500 text-primary-600 dark:text-primary-400 bg-white dark:bg-gray-800'
            : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700/50'
          }
        `}
      >
        <Icon className="w-4 h-4" />
        <span className="hidden sm:inline">{tab.label}</span>
      </button>
    )
  }

  // Contenu de l'onglet Synthese
  const TabSynthese = () => (
    <div className="space-y-6">
      {/* KPIs Principaux - CA */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-green-500" />
          Chiffre d'Affaires
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          <div className="card p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
            <div className="flex items-center gap-2 text-xs text-blue-600 dark:text-blue-400">
              <Users className="w-3 h-3" />
              <span>Clients</span>
            </div>
            <div className="text-xl font-bold text-blue-700 dark:text-blue-300">
              {formatNumber(kpis?.ca?.nb_clients)}
            </div>
          </div>
          <div className="card p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
            <div className="flex items-center gap-2 text-xs text-green-600 dark:text-green-400">
              <FileText className="w-3 h-3" />
              <span>Factures</span>
            </div>
            <div className="text-xl font-bold text-green-700 dark:text-green-300">
              {formatNumber(kpis?.ca?.nb_factures)}
            </div>
          </div>
          <div className="card p-3 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg">
            <div className="flex items-center gap-2 text-xs text-purple-600 dark:text-purple-400">
              <DollarSign className="w-3 h-3" />
              <span>CA HT</span>
            </div>
            <div className="text-xl font-bold text-purple-700 dark:text-purple-300">
              {formatMillions(kpis?.ca?.ca_ht)}
            </div>
          </div>
          <div className="card p-3 bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800 rounded-lg">
            <div className="flex items-center gap-2 text-xs text-indigo-600 dark:text-indigo-400">
              <DollarSign className="w-3 h-3" />
              <span>CA TTC</span>
            </div>
            <div className="text-xl font-bold text-indigo-700 dark:text-indigo-300">
              {formatMillions(kpis?.ca?.ca_ttc)}
            </div>
          </div>
          <div className="card p-3 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-lg">
            <div className="flex items-center gap-2 text-xs text-emerald-600 dark:text-emerald-400">
              <TrendingUp className="w-3 h-3" />
              <span>Marge</span>
            </div>
            <div className="text-xl font-bold text-emerald-700 dark:text-emerald-300">
              {formatMillions(kpis?.ca?.marge_brute)}
            </div>
          </div>
          <div className="card p-3 bg-teal-50 dark:bg-teal-900/20 border border-teal-200 dark:border-teal-800 rounded-lg">
            <div className="flex items-center gap-2 text-xs text-teal-600 dark:text-teal-400">
              <TrendingUp className="w-3 h-3" />
              <span>Taux Marge</span>
            </div>
            <div className="text-xl font-bold text-teal-700 dark:text-teal-300">
              {formatPercent(kpis?.ca?.taux_marge)}
            </div>
          </div>
        </div>
      </div>

      {/* KPIs Creances */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-orange-500" />
          Creances Clients
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="card p-3 bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg">
            <div className="flex items-center gap-2 text-xs text-orange-600 dark:text-orange-400">
              <AlertTriangle className="w-3 h-3" />
              <span>Solde Creances</span>
            </div>
            <div className="text-xl font-bold text-orange-700 dark:text-orange-300">
              {formatMillions(kpis?.creances?.total_solde)}
            </div>
          </div>
          <div className="card p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <div className="flex items-center gap-2 text-xs text-red-600 dark:text-red-400">
              <AlertTriangle className="w-3 h-3" />
              <span>Impayes</span>
            </div>
            <div className="text-xl font-bold text-red-700 dark:text-red-300">
              {formatMillions(kpis?.creances?.total_impayes)}
            </div>
          </div>
          <div className="card p-3 bg-cyan-50 dark:bg-cyan-900/20 border border-cyan-200 dark:border-cyan-800 rounded-lg">
            <div className="flex items-center gap-2 text-xs text-cyan-600 dark:text-cyan-400">
              <TrendingUp className="w-3 h-3" />
              <span>Taux Recouvrement</span>
            </div>
            <div className="text-xl font-bold text-cyan-700 dark:text-cyan-300">
              {formatPercent(kpis?.creances?.taux_recouvrement)}
            </div>
          </div>
          <div className="card p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
            <div className="flex items-center gap-2 text-xs text-amber-600 dark:text-amber-400">
              <Calendar className="w-3 h-3" />
              <span>DSO (jours)</span>
            </div>
            <div className="text-xl font-bold text-amber-700 dark:text-amber-300">
              {formatNumber(kpis?.creances?.dso)}
            </div>
          </div>
        </div>
      </div>

      {/* Top Clients en cote a cote */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top 10 Clients CA */}
        <div className="card bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
            <h3 className="font-semibold text-gray-900 dark:text-white text-sm flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-green-500" />
              Top 10 Clients par CA
            </h3>
          </div>
          <div className="overflow-x-auto max-h-[400px]">
            <table className="w-full">
              <thead className="bg-gray-100 dark:bg-gray-700 sticky top-0">
                <tr>
                  <th className="px-3 py-2 text-left text-xs font-semibold text-gray-600 dark:text-gray-300">Client</th>
                  <th className="px-3 py-2 text-right text-xs font-semibold text-gray-600 dark:text-gray-300">CA HT</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {topClientsCA.slice(0, 10).map((client, idx) => (
                  <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                    <td className="px-3 py-2 text-sm text-gray-900 dark:text-gray-100 truncate max-w-[250px]" title={client.client}>
                      {client.client}
                    </td>
                    <td className="px-3 py-2 text-sm text-right text-gray-900 dark:text-gray-100 whitespace-nowrap font-semibold">
                      {formatMillions(client.ca_ht)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Top 10 Clients Creances */}
        <div className="card bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
            <h3 className="font-semibold text-gray-900 dark:text-white text-sm flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-orange-500" />
              Top 10 Clients par Creances
            </h3>
          </div>
          <div className="overflow-x-auto max-h-[400px]">
            <table className="w-full">
              <thead className="bg-gray-100 dark:bg-gray-700 sticky top-0">
                <tr>
                  <th className="px-3 py-2 text-left text-xs font-semibold text-gray-600 dark:text-gray-300">Client</th>
                  <th className="px-3 py-2 text-right text-xs font-semibold text-gray-600 dark:text-gray-300">Solde</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {topClientsCreances.slice(0, 10).map((client, idx) => (
                  <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                    <td className="px-3 py-2 text-sm text-gray-900 dark:text-gray-100 truncate max-w-[250px]" title={client.client}>
                      {client.client}
                    </td>
                    <td className="px-3 py-2 text-sm text-right text-orange-600 dark:text-orange-400 whitespace-nowrap font-semibold">
                      {formatMillions(client.solde_cloture)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )

  // Contenu de l'onglet Chiffre d'Affaires
  const TabCA = () => (
    <div className="space-y-6">
      {/* Top Clients CA */}
      <div className="card bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
          <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-green-500" />
            Top 10 Clients par CA
          </h3>
        </div>
        <div className="overflow-x-auto max-h-[400px]">
          <table className="w-full">
            <thead className="bg-gray-100 dark:bg-gray-700 sticky top-0">
              <tr>
                <th className="px-3 py-2 text-left text-xs font-semibold text-gray-600 dark:text-gray-300">Client</th>
                <th className="px-3 py-2 text-right text-xs font-semibold text-gray-600 dark:text-gray-300">CA HT</th>
                <th className="px-3 py-2 text-right text-xs font-semibold text-gray-600 dark:text-gray-300">Marge</th>
                <th className="px-3 py-2 text-right text-xs font-semibold text-gray-600 dark:text-gray-300">%</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {topClientsCA.map((client, idx) => (
                <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td className="px-3 py-2 text-sm text-gray-900 dark:text-gray-100">
                    <div className="font-medium truncate max-w-[250px]" title={client.client}>
                      {client.client}
                    </div>
                  </td>
                  <td className="px-3 py-2 text-sm text-right text-gray-900 dark:text-gray-100 whitespace-nowrap">
                    {formatMillions(client.ca_ht)}
                  </td>
                  <td className="px-3 py-2 text-sm text-right text-gray-900 dark:text-gray-100 whitespace-nowrap">
                    {formatMillions(client.marge)}
                  </td>
                  <td className="px-3 py-2 text-sm text-right whitespace-nowrap">
                    <span className={`${client.taux_marge >= 20 ? 'text-green-600' : client.taux_marge >= 10 ? 'text-yellow-600' : 'text-red-600'}`}>
                      {formatPercent(client.taux_marge)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Evolution CA par Mois */}
      <div className="card bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
          <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <Calendar className="w-5 h-5 text-purple-500" />
            Evolution CA par Mois - 2025
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-100 dark:bg-gray-700">
              <tr>
                <th className="px-3 py-2 text-left text-xs font-semibold text-gray-600 dark:text-gray-300">Mois</th>
                <th className="px-3 py-2 text-right text-xs font-semibold text-gray-600 dark:text-gray-300">CA HT</th>
                <th className="px-3 py-2 text-right text-xs font-semibold text-gray-600 dark:text-gray-300">Marge</th>
                <th className="px-3 py-2 text-right text-xs font-semibold text-gray-600 dark:text-gray-300">Clients</th>
                <th className="px-3 py-2 text-right text-xs font-semibold text-gray-600 dark:text-gray-300">Factures</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {caParMois.map((mois, idx) => (
                <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td className="px-3 py-2 text-sm font-medium text-gray-900 dark:text-gray-100">
                    {mois.mois_nom}
                  </td>
                  <td className="px-3 py-2 text-sm text-right text-gray-900 dark:text-gray-100">
                    {formatMillions(mois.ca_ht)}
                  </td>
                  <td className="px-3 py-2 text-sm text-right text-emerald-600 dark:text-emerald-400">
                    {formatMillions(mois.marge)}
                  </td>
                  <td className="px-3 py-2 text-sm text-right text-gray-600 dark:text-gray-400">
                    {formatNumber(mois.nb_clients)}
                  </td>
                  <td className="px-3 py-2 text-sm text-right text-gray-600 dark:text-gray-400">
                    {formatNumber(mois.nb_factures)}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot className="bg-gray-100 dark:bg-gray-700 font-semibold">
              <tr>
                <td className="px-3 py-2 text-sm text-gray-900 dark:text-gray-100">Total</td>
                <td className="px-3 py-2 text-sm text-right text-gray-900 dark:text-gray-100">
                  {formatMillions(caParMois.reduce((sum, m) => sum + (m.ca_ht || 0), 0))}
                </td>
                <td className="px-3 py-2 text-sm text-right text-emerald-600 dark:text-emerald-400">
                  {formatMillions(caParMois.reduce((sum, m) => sum + (m.marge || 0), 0))}
                </td>
                <td className="px-3 py-2 text-sm text-right text-gray-600 dark:text-gray-400">-</td>
                <td className="px-3 py-2 text-sm text-right text-gray-600 dark:text-gray-400">
                  {formatNumber(caParMois.reduce((sum, m) => sum + (m.nb_factures || 0), 0))}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {/* CA par Commercial */}
      <div className="card bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
          <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <Users className="w-5 h-5 text-blue-500" />
            CA par Commercial
          </h3>
        </div>
        <div className="overflow-x-auto max-h-[400px]">
          <table className="w-full">
            <thead className="bg-gray-100 dark:bg-gray-700 sticky top-0">
              <tr>
                <th className="px-3 py-2 text-left text-xs font-semibold text-gray-600 dark:text-gray-300">Commercial</th>
                <th className="px-3 py-2 text-right text-xs font-semibold text-gray-600 dark:text-gray-300">Clients</th>
                <th className="px-3 py-2 text-right text-xs font-semibold text-gray-600 dark:text-gray-300">Factures</th>
                <th className="px-3 py-2 text-right text-xs font-semibold text-gray-600 dark:text-gray-300">CA HT</th>
                <th className="px-3 py-2 text-right text-xs font-semibold text-gray-600 dark:text-gray-300">Marge</th>
                <th className="px-3 py-2 text-right text-xs font-semibold text-gray-600 dark:text-gray-300">Taux</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {caParCommercial.map((com, idx) => (
                <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td className="px-3 py-2 text-sm font-medium text-gray-900 dark:text-gray-100">
                    {com.commercial}
                  </td>
                  <td className="px-3 py-2 text-sm text-right text-gray-600 dark:text-gray-400">
                    {formatNumber(com.nb_clients)}
                  </td>
                  <td className="px-3 py-2 text-sm text-right text-gray-600 dark:text-gray-400">
                    {formatNumber(com.nb_factures)}
                  </td>
                  <td className="px-3 py-2 text-sm text-right text-gray-900 dark:text-gray-100 font-semibold">
                    {formatMillions(com.ca_ht)}
                  </td>
                  <td className="px-3 py-2 text-sm text-right text-emerald-600 dark:text-emerald-400">
                    {formatMillions(com.marge)}
                  </td>
                  <td className="px-3 py-2 text-sm text-right whitespace-nowrap">
                    <span className={`${com.taux_marge >= 20 ? 'text-green-600' : com.taux_marge >= 10 ? 'text-yellow-600' : 'text-red-600'}`}>
                      {formatPercent(com.taux_marge)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )

  // Contenu de l'onglet Creances
  const TabCreances = () => (
    <div className="space-y-6">
      {/* Top Clients Creances */}
      <div className="card bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
          <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-orange-500" />
            Top 10 Clients par Creances
          </h3>
        </div>
        <div className="overflow-x-auto max-h-[400px]">
          <table className="w-full">
            <thead className="bg-gray-100 dark:bg-gray-700 sticky top-0">
              <tr>
                <th className="px-3 py-2 text-left text-xs font-semibold text-gray-600 dark:text-gray-300">Client</th>
                <th className="px-3 py-2 text-left text-xs font-semibold text-gray-600 dark:text-gray-300">Commercial</th>
                <th className="px-3 py-2 text-right text-xs font-semibold text-gray-600 dark:text-gray-300">Solde</th>
                <th className="px-3 py-2 text-right text-xs font-semibold text-gray-600 dark:text-gray-300">Impayes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {topClientsCreances.map((client, idx) => (
                <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td className="px-3 py-2 text-sm text-gray-900 dark:text-gray-100">
                    <div className="font-medium truncate max-w-[250px]" title={client.client}>
                      {client.client}
                    </div>
                  </td>
                  <td className="px-3 py-2 text-sm text-gray-600 dark:text-gray-400">
                    {client.representant}
                  </td>
                  <td className="px-3 py-2 text-sm text-right text-orange-600 dark:text-orange-400 font-semibold whitespace-nowrap">
                    {formatMillions(client.solde_cloture)}
                  </td>
                  <td className="px-3 py-2 text-sm text-right text-red-600 dark:text-red-400 whitespace-nowrap">
                    {formatMillions(client.impayes)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Evolution Creances par Mois */}
      <div className="card bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
          <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <Calendar className="w-5 h-5 text-orange-500" />
            Creances par Mois (Echeances)
          </h3>
        </div>
        <div className="overflow-x-auto">
          <div className="grid grid-cols-4 md:grid-cols-6 lg:grid-cols-12 gap-2 p-4">
            {[
              { label: 'Janv', value: kpis?.mensuel?.janv_25 },
              { label: 'Fevr', value: kpis?.mensuel?.fevr_25 },
              { label: 'Mars', value: kpis?.mensuel?.mars_25 },
              { label: 'Avr', value: kpis?.mensuel?.avr_25 },
              { label: 'Mai', value: kpis?.mensuel?.mai_25 },
              { label: 'Juin', value: kpis?.mensuel?.juin_25 },
              { label: 'Juil', value: kpis?.mensuel?.juil_25 },
              { label: 'Aout', value: kpis?.mensuel?.aout_25 },
              { label: 'Sept', value: kpis?.mensuel?.sept_25 },
              { label: 'Oct', value: kpis?.mensuel?.oct_25 },
              { label: 'Nov', value: kpis?.mensuel?.nov_25 },
              { label: 'Dec', value: kpis?.mensuel?.dec_25 }
            ].map((mois, idx) => (
              <div
                key={idx}
                className={`p-3 rounded-lg text-center ${
                  (mois.value || 0) > 0
                    ? 'bg-orange-100 dark:bg-orange-900/30 border border-orange-200 dark:border-orange-800'
                    : 'bg-gray-100 dark:bg-gray-700'
                }`}
              >
                <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">{mois.label}</div>
                <div className={`text-sm font-semibold ${(mois.value || 0) > 0 ? 'text-orange-600 dark:text-orange-400' : 'text-gray-400'}`}>
                  {(mois.value || 0) > 0 ? formatMillions(mois.value) : '-'}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )

  // Contenu de l'onglet Balance Agee
  const TabBalance = () => (
    <div className="space-y-6">
      {balanceAgeeTranche && (
        <>
          {/* Barre de progression horizontale */}
          <div className="card bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <h3 className="font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
              <PieChart className="w-5 h-5 text-blue-500" />
              Repartition par Tranche d'Anciennete
            </h3>
            <div className="flex h-10 rounded-lg overflow-hidden mb-2">
              {balanceAgeeTranche.tranches?.map((tranche, idx) => {
                const colorMap = {
                  green: 'bg-green-500',
                  yellow: 'bg-yellow-500',
                  orange: 'bg-orange-500',
                  red: 'bg-red-500',
                  darkred: 'bg-red-700'
                }
                return tranche.pourcentage > 0 ? (
                  <div
                    key={idx}
                    className={`${colorMap[tranche.color]} flex items-center justify-center text-white text-xs font-semibold transition-all`}
                    style={{ width: `${Math.max(tranche.pourcentage, 2)}%` }}
                    title={`${tranche.tranche}: ${formatMillions(tranche.montant)} (${tranche.pourcentage}%)`}
                  >
                    {tranche.pourcentage >= 10 && `${tranche.pourcentage}%`}
                  </div>
                ) : null
              })}
            </div>
            <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
              <span>Courant</span>
              <span>+6 mois</span>
            </div>
          </div>

          {/* Details par tranche */}
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            {balanceAgeeTranche.tranches?.map((tranche, idx) => {
              const colorMapBg = {
                green: 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800',
                yellow: 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800',
                orange: 'bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800',
                red: 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800',
                darkred: 'bg-red-100 dark:bg-red-900/30 border-red-300 dark:border-red-700'
              }
              const colorMapText = {
                green: 'text-green-600 dark:text-green-400',
                yellow: 'text-yellow-600 dark:text-yellow-400',
                orange: 'text-orange-600 dark:text-orange-400',
                red: 'text-red-600 dark:text-red-400',
                darkred: 'text-red-700 dark:text-red-300'
              }
              return (
                <div
                  key={idx}
                  className={`p-4 rounded-lg border ${colorMapBg[tranche.color]}`}
                >
                  <div className={`text-sm font-medium ${colorMapText[tranche.color]} mb-1`}>
                    {tranche.tranche}
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 mb-3">
                    {tranche.label}
                  </div>
                  <div className={`text-2xl font-bold ${colorMapText[tranche.color]} mb-1`}>
                    {formatMillions(tranche.montant)}
                  </div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    {tranche.pourcentage}% du total
                  </div>
                </div>
              )
            })}
          </div>

          {/* Resume */}
          <div className="card bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="text-center p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Total Creances</div>
                <div className="text-2xl font-bold text-gray-900 dark:text-white">
                  {formatMillions(balanceAgeeTranche.total_solde)}
                </div>
              </div>
              <div className="text-center p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Total Impayes</div>
                <div className="text-2xl font-bold text-red-600 dark:text-red-400">
                  {formatMillions(balanceAgeeTranche.total_impayes)}
                </div>
              </div>
              <div className="text-center p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Nombre de Clients</div>
                <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                  {formatNumber(balanceAgeeTranche.nb_clients)}
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Tableau Detail par Client */}
      <div className="card bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
          <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <Users className="w-5 h-5 text-blue-500" />
            Balance Agee par Client
          </h3>
        </div>
        <div className="overflow-x-auto max-h-[500px]">
          <table className="w-full">
            <thead className="bg-gray-100 dark:bg-gray-700 sticky top-0">
              <tr>
                <th className="px-3 py-2 text-left text-xs font-semibold text-gray-600 dark:text-gray-300 whitespace-nowrap">Client</th>
                <th className="px-3 py-2 text-left text-xs font-semibold text-gray-600 dark:text-gray-300 whitespace-nowrap">Commercial</th>
                <th className="px-3 py-2 text-left text-xs font-semibold text-gray-600 dark:text-gray-300 whitespace-nowrap">Societe</th>
                <th className="px-3 py-2 text-right text-xs font-semibold text-gray-600 dark:text-gray-300 whitespace-nowrap">Solde Total</th>
                <th className="px-3 py-2 text-right text-xs font-semibold text-purple-600 dark:text-purple-400 whitespace-nowrap bg-purple-50 dark:bg-purple-900/20">DSO</th>
                <th className="px-3 py-2 text-right text-xs font-semibold text-green-600 dark:text-green-400 whitespace-nowrap bg-green-50 dark:bg-green-900/20">0-30j</th>
                <th className="px-3 py-2 text-right text-xs font-semibold text-yellow-600 dark:text-yellow-400 whitespace-nowrap bg-yellow-50 dark:bg-yellow-900/20">30-60j</th>
                <th className="px-3 py-2 text-right text-xs font-semibold text-orange-600 dark:text-orange-400 whitespace-nowrap bg-orange-50 dark:bg-orange-900/20">60-90j</th>
                <th className="px-3 py-2 text-right text-xs font-semibold text-red-600 dark:text-red-400 whitespace-nowrap bg-red-50 dark:bg-red-900/20">90-180j</th>
                <th className="px-3 py-2 text-right text-xs font-semibold text-red-700 dark:text-red-300 whitespace-nowrap bg-red-100 dark:bg-red-900/30">&gt;180j</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {balanceAgeeDetail.map((client, idx) => (
                <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td className="px-3 py-2 text-sm text-gray-900 dark:text-gray-100">
                    <div className="font-medium truncate max-w-[200px]" title={client.client}>
                      {client.client}
                    </div>
                  </td>
                  <td className="px-3 py-2 text-sm text-gray-600 dark:text-gray-400 whitespace-nowrap">
                    {client.representant}
                  </td>
                  <td className="px-3 py-2 text-sm text-gray-600 dark:text-gray-400 whitespace-nowrap">
                    {client.societe}
                  </td>
                  <td className="px-3 py-2 text-sm text-right font-semibold text-gray-900 dark:text-gray-100 whitespace-nowrap">
                    {formatMillions(client.solde_cloture)}
                  </td>
                  <td className="px-3 py-2 text-sm text-right whitespace-nowrap bg-purple-50 dark:bg-purple-900/10 text-purple-600 dark:text-purple-400 font-medium">
                    {Math.round(client.dso || 0)}j
                  </td>
                  <td className={`px-3 py-2 text-sm text-right whitespace-nowrap bg-green-50 dark:bg-green-900/10 ${client.tranche_0_30 > 0 ? 'text-green-600 dark:text-green-400 font-medium' : 'text-gray-400'}`}>
                    {client.tranche_0_30 > 0 ? formatMillions(client.tranche_0_30) : '-'}
                  </td>
                  <td className={`px-3 py-2 text-sm text-right whitespace-nowrap bg-yellow-50 dark:bg-yellow-900/10 ${client.tranche_30_60 > 0 ? 'text-yellow-600 dark:text-yellow-400 font-medium' : 'text-gray-400'}`}>
                    {client.tranche_30_60 > 0 ? formatMillions(client.tranche_30_60) : '-'}
                  </td>
                  <td className={`px-3 py-2 text-sm text-right whitespace-nowrap bg-orange-50 dark:bg-orange-900/10 ${client.tranche_60_90 > 0 ? 'text-orange-600 dark:text-orange-400 font-medium' : 'text-gray-400'}`}>
                    {client.tranche_60_90 > 0 ? formatMillions(client.tranche_60_90) : '-'}
                  </td>
                  <td className={`px-3 py-2 text-sm text-right whitespace-nowrap bg-red-50 dark:bg-red-900/10 ${client.tranche_90_180 > 0 ? 'text-red-600 dark:text-red-400 font-medium' : 'text-gray-400'}`}>
                    {client.tranche_90_180 > 0 ? formatMillions(client.tranche_90_180) : '-'}
                  </td>
                  <td className={`px-3 py-2 text-sm text-right whitespace-nowrap bg-red-100 dark:bg-red-900/20 ${client.tranche_plus_180 > 0 ? 'text-red-700 dark:text-red-300 font-bold' : 'text-gray-400'}`}>
                    {client.tranche_plus_180 > 0 ? formatMillions(client.tranche_plus_180) : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot className="bg-gray-100 dark:bg-gray-700 font-semibold sticky bottom-0">
              <tr>
                <td colSpan="3" className="px-3 py-2 text-sm text-gray-900 dark:text-gray-100">
                  Total ({balanceAgeeDetail.length} clients)
                </td>
                <td className="px-3 py-2 text-sm text-right text-gray-900 dark:text-gray-100 whitespace-nowrap">
                  {formatMillions(balanceAgeeDetail.reduce((sum, c) => sum + (c.solde_cloture || 0), 0))}
                </td>
                <td className="px-3 py-2 text-sm text-right text-purple-600 dark:text-purple-400 whitespace-nowrap bg-purple-50 dark:bg-purple-900/20">
                  {Math.round(balanceAgeeDetail.length > 0 ? balanceAgeeDetail.reduce((sum, c) => sum + (c.dso || 0), 0) / balanceAgeeDetail.length : 0)}j
                </td>
                <td className="px-3 py-2 text-sm text-right text-green-600 dark:text-green-400 whitespace-nowrap bg-green-50 dark:bg-green-900/20">
                  {formatMillions(balanceAgeeDetail.reduce((sum, c) => sum + (c.tranche_0_30 || 0), 0))}
                </td>
                <td className="px-3 py-2 text-sm text-right text-yellow-600 dark:text-yellow-400 whitespace-nowrap bg-yellow-50 dark:bg-yellow-900/20">
                  {formatMillions(balanceAgeeDetail.reduce((sum, c) => sum + (c.tranche_30_60 || 0), 0))}
                </td>
                <td className="px-3 py-2 text-sm text-right text-orange-600 dark:text-orange-400 whitespace-nowrap bg-orange-50 dark:bg-orange-900/20">
                  {formatMillions(balanceAgeeDetail.reduce((sum, c) => sum + (c.tranche_60_90 || 0), 0))}
                </td>
                <td className="px-3 py-2 text-sm text-right text-red-600 dark:text-red-400 whitespace-nowrap bg-red-50 dark:bg-red-900/20">
                  {formatMillions(balanceAgeeDetail.reduce((sum, c) => sum + (c.tranche_90_180 || 0), 0))}
                </td>
                <td className="px-3 py-2 text-sm text-right text-red-700 dark:text-red-300 whitespace-nowrap bg-red-100 dark:bg-red-900/30">
                  {formatMillions(balanceAgeeDetail.reduce((sum, c) => sum + (c.tranche_plus_180 || 0), 0))}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    </div>
  )

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Analyse CA & Creances Clients
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Vue consolidee du chiffre d'affaires et des creances - Annee 2025
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Filtre Societe */}
          <select
            value={selectedSociete}
            onChange={(e) => setSelectedSociete(e.target.value)}
            className="input min-w-[160px]"
          >
            <option value="">Toutes societes</option>
            {filtres.societes.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>

          {/* Filtre Representant */}
          <select
            value={selectedRepresentant}
            onChange={(e) => setSelectedRepresentant(e.target.value)}
            className="input min-w-[160px]"
          >
            <option value="">Tous commerciaux</option>
            {filtres.representants.map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>

          {/* Filtre Region */}
          <select
            value={selectedRegion}
            onChange={(e) => setSelectedRegion(e.target.value)}
            className="input min-w-[140px]"
          >
            <option value="">Toutes regions</option>
            {filtres.regions.map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>

          {/* Filtre Groupe */}
          <select
            value={selectedGroupe}
            onChange={(e) => setSelectedGroupe(e.target.value)}
            className="input min-w-[140px]"
          >
            <option value="">Tous groupes</option>
            {filtres.groupes.map((g) => (
              <option key={g} value={g}>{g}</option>
            ))}
          </select>

          <button
            onClick={loadData}
            disabled={loading}
            className="btn btn-secondary flex items-center gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Actualiser
          </button>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <div className="flex gap-1 overflow-x-auto">
          {TABS.map((tab) => (
            <TabButton key={tab.id} tab={tab} />
          ))}
        </div>
      </div>

      {/* Tab Content */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
        {activeTab === 'synthese' && <TabSynthese />}
        {activeTab === 'ca' && <TabCA />}
        {activeTab === 'creances' && <TabCreances />}
        {activeTab === 'balance' && <TabBalance />}
      </div>
    </div>
  )
}
