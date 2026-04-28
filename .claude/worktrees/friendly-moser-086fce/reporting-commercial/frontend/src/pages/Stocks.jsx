import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Download, Package, AlertTriangle, RotateCcw, Clock } from 'lucide-react'
import KPICard from '../components/Dashboard/KPICard'
import DataTable from '../components/DrillDown/DataTable'
import DetailModal from '../components/DrillDown/DetailModal'
import { TopChart } from '../components/Dashboard/Charts'
import Filters from '../components/common/Filters'
import Loading from '../components/common/Loading'
import api, {
  getStocks,
  getStockDormant,
  getRotationStock,
  getMouvementsArticle,
  getStocksParGamme,
  exportStocksExcel,
  downloadBlob
} from '../services/api'
import { useGlobalFilters } from '../context/GlobalFilterContext'

export default function Stocks() {
  const navigate = useNavigate()
  const { filters: globalFilters } = useGlobalFilters()
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState(null)
  const [stocksGamme, setStocksGamme] = useState([])
  const [filters, setFilters] = useState({ periode: 'annee_courante' })
  const [activeTab, setActiveTab] = useState('overview')
  const [drillByColumn, setDrillByColumn] = useState({})

  // Modal
  const [modalOpen, setModalOpen] = useState(false)
  const [modalData, setModalData] = useState({
    title: '',
    breadcrumb: [],
    data: [],
    columns: [],
    total: 0,
    page: 1,
    loading: false
  })

  useEffect(() => {
    loadData()
  }, [filters])

  useEffect(() => {
    api.get('/drillthrough/rules/by-source?source_type=stocks')
      .then(res => { if (res.data.success) setDrillByColumn(res.data.by_column || {}) })
      .catch(() => {})
  }, [])

  const buildDrillUrl = (rule, value) => {
    const params = new URLSearchParams()
    params.set('dt_field', rule.target_filter_field)
    params.set('dt_value', value ?? '')
    params.set('dt_source', 'Stocks')
    if (globalFilters?.dateDebut) params.set('gf_dateDebut', globalFilters.dateDebut)
    if (globalFilters?.dateFin) params.set('gf_dateFin', globalFilters.dateFin)
    if (globalFilters?.societe) params.set('gf_societe', globalFilters.societe)
    return `${rule.target_url}?${params.toString()}`
  }

  const tryDrillThrough = (fieldName, value, fallback) => {
    const rules = drillByColumn[fieldName]
    if (rules?.length > 0) { navigate(buildDrillUrl(rules[0], value)); return true }
    fallback(); return false
  }

  const loadData = async () => {
    setLoading(true)
    try {
      const [stocksResponse, gammeResponse] = await Promise.all([
        getStocks(filters),
        getStocksParGamme()
      ])
      setData(stocksResponse.data)
      setStocksGamme(gammeResponse.data.data || [])
    } catch (error) {
      console.error('Error loading stocks:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleExport = async () => {
    try {
      const response = await exportStocksExcel()
      downloadBlob(response.data, `stocks_${new Date().toISOString().slice(0, 10)}.xlsx`)
    } catch (error) {
      console.error('Export error:', error)
    }
  }

  // Drill-down handler
  const handleArticleClick = async (row) => {
    if (!row?.code_article) return
    if (tryDrillThrough('code_article', row.code_article, () => {})) return
    setModalData(prev => ({ ...prev, loading: true }))
    setModalOpen(true)

    try {
      const response = await getMouvementsArticle(row.code_article)
      const result = response.data

      setModalData({
        title: `Article: ${row.designation || row.code_article}`,
        breadcrumb: ['Stocks', 'Articles', row.code_article],
        data: result.mouvements || [],
        columns: [
          { key: 'date_mouvement', header: 'Date', format: 'date' },
          { key: 'type_mouvement', header: 'Type' },
          { key: 'numero_piece', header: 'N. Piece' },
          { key: 'sens_mouvement', header: 'Sens', render: (v) => v === 'E' ? 'Entree' : 'Sortie' },
          { key: 'quantite', header: 'Qte', format: 'number' },
          { key: 'cmup', header: 'CMUP', format: 'currency' },
          { key: 'client', header: 'Client' }
        ],
        total: result.nb_mouvements || 0,
        page: 1,
        loading: false
      })
    } catch (error) {
      console.error('Error:', error)
      setModalOpen(false)
    }
  }

  // Handler pour clic sur gamme dans le graphique
  const handleGammeClick = (gammeData) => {
    if (!gammeData?.gamme) return
    if (tryDrillThrough('gamme', gammeData.gamme, () => {})) return
    setModalData({
      title: `Gamme: ${gammeData.gamme}`,
      breadcrumb: ['Stocks', 'Par Gamme', gammeData.gamme],
      data: [gammeData],
      columns: [
        { key: 'gamme', header: 'Gamme' },
        { key: 'quantite_totale', header: 'Quantité', format: 'number' },
        { key: 'valeur_totale', header: 'Valeur', format: 'currency' },
        { key: 'nb_articles', header: 'Nb Articles', format: 'number' }
      ],
      total: 1,
      page: 1,
      loading: false
    })
    setModalOpen(true)
  }

  // Handler pour KPI Valeur Totale Stock
  const handleKPIValeurClick = () => {
    setModalData({
      title: 'Valeur Stock - Par Gamme',
      breadcrumb: ['Stocks', 'Valeur'],
      data: stocksGamme || [],
      columns: [
        { key: 'gamme', header: 'Gamme' },
        { key: 'quantite_totale', header: 'Quantité', format: 'number' },
        { key: 'valeur_totale', header: 'Valeur', format: 'currency' },
        { key: 'nb_articles', header: 'Nb Articles', format: 'number' }
      ],
      total: stocksGamme?.length || 0,
      page: 1,
      loading: false
    })
    setModalOpen(true)
  }

  // Handler pour KPI Nombre d'Articles
  const handleKPIArticlesClick = () => {
    setModalData({
      title: 'Liste des Articles',
      breadcrumb: ['Stocks', 'Articles'],
      data: data?.par_article || [],
      columns: [
        { key: 'code_article', header: 'Code' },
        { key: 'designation', header: 'Désignation' },
        { key: 'gamme', header: 'Gamme' },
        { key: 'stock_actuel', header: 'Stock', format: 'number' },
        { key: 'valeur_stock', header: 'Valeur', format: 'currency' }
      ],
      total: data?.par_article?.length || 0,
      page: 1,
      loading: false
    })
    setModalOpen(true)
  }

  // Handler pour KPI Stock Dormant
  const handleKPIDormantClick = () => {
    setModalData({
      title: 'Stock Dormant (>180 jours)',
      breadcrumb: ['Stocks', 'Dormant'],
      data: data?.articles_dormants || [],
      columns: [
        { key: 'code_article', header: 'Code' },
        { key: 'designation', header: 'Désignation' },
        { key: 'gamme', header: 'Gamme' },
        { key: 'stock_actuel', header: 'Stock', format: 'number' },
        { key: 'valeur_stock', header: 'Valeur', format: 'currency' },
        { key: 'jours_sans_mouvement', header: 'Jours Inactif', format: 'number' }
      ],
      total: data?.articles_dormants?.length || 0,
      page: 1,
      loading: false
    })
    setModalOpen(true)
  }

  if (loading) {
    return <Loading message="Chargement des stocks..." />
  }

  const tabs = [
    { id: 'overview', label: 'Vue d\'ensemble' },
    { id: 'articles', label: 'Par Article' },
    { id: 'dormant', label: 'Stock Dormant' },
    { id: 'rotation', label: 'Rotation' }
  ]

  const formatCurrency = (value) => {
    return (value || 0).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Gestion des Stocks</h1>
          <p className="text-gray-500 dark:text-gray-400">
            Analyse des stocks, rotation et articles dormants
          </p>
        </div>
        <button onClick={handleExport} className="btn-primary flex items-center gap-2">
          <Download className="w-4 h-4" />
          Exporter Excel
        </button>
      </div>

      {/* Filters */}
      <Filters onFilterChange={setFilters} showPeriod={true} />

      {/* KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          title="Valeur Totale Stock"
          formattedValue={formatCurrency(data?.valeur_totale_stock)}
          icon={Package}
          color="primary"
          onClick={handleKPIValeurClick}
          clickable
        />
        <KPICard
          title="Nombre d'Articles"
          formattedValue={String(data?.nb_articles || 0)}
          icon={Package}
          color="blue"
          onClick={handleKPIArticlesClick}
          clickable
        />
        <KPICard
          title="Stock Dormant"
          formattedValue={formatCurrency(data?.stock_dormant_valeur)}
          icon={AlertTriangle}
          color="red"
          onClick={handleKPIDormantClick}
          clickable
        />
        <KPICard
          title="Taux Dormant"
          formattedValue={`${data?.taux_dormant || 0}%`}
          icon={Clock}
          color="yellow"
          onClick={handleKPIDormantClick}
          clickable
        />
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="flex gap-4">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`
                py-3 px-1 border-b-2 font-medium text-sm transition-colors
                ${activeTab === tab.id
                  ? 'border-primary-500 text-primary-600 dark:text-primary-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400'
                }
              `}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <TopChart
            data={stocksGamme.slice(0, 10)}
            dataKey="valeur_totale"
            nameKey="gamme"
            title="Stock par Gamme (Valeur)"
            onBarClick={handleGammeClick}
          />
          <div className="card p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Resume des Stocks
            </h3>
            <div className="space-y-2">
              <div
                className="flex justify-between items-center py-2 px-3 border-b dark:border-gray-700 cursor-pointer rounded hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                onClick={handleKPIValeurClick}
                title="Cliquez pour voir le détail"
              >
                <span className="text-gray-600 dark:text-gray-400">Valeur totale</span>
                <span className="font-semibold">{formatCurrency(data?.valeur_totale_stock)}</span>
              </div>
              <div
                className="flex justify-between items-center py-2 px-3 border-b dark:border-gray-700 cursor-pointer rounded hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                onClick={handleKPIArticlesClick}
                title="Cliquez pour voir le détail"
              >
                <span className="text-gray-600 dark:text-gray-400">Nombre d'articles</span>
                <span className="font-semibold">{data?.nb_articles || 0}</span>
              </div>
              <div
                className="flex justify-between items-center py-2 px-3 border-b dark:border-gray-700 cursor-pointer rounded hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                onClick={handleKPIDormantClick}
                title="Cliquez pour voir le détail"
              >
                <span className="text-gray-600 dark:text-gray-400">Stock dormant (valeur)</span>
                <span className="font-semibold text-red-500">{formatCurrency(data?.stock_dormant_valeur)}</span>
              </div>
              <div
                className="flex justify-between items-center py-2 px-3 border-b dark:border-gray-700 cursor-pointer rounded hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                onClick={handleKPIDormantClick}
                title="Cliquez pour voir le détail"
              >
                <span className="text-gray-600 dark:text-gray-400">Articles dormants</span>
                <span className="font-semibold text-red-500">{data?.stock_dormant_nb_articles || 0}</span>
              </div>
              <div
                className="flex justify-between items-center py-2 px-3 cursor-pointer rounded hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                onClick={handleKPIDormantClick}
                title="Cliquez pour voir le détail"
              >
                <span className="text-gray-600 dark:text-gray-400">Taux de stock dormant</span>
                <span className="font-semibold text-amber-500">{data?.taux_dormant || 0}%</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'articles' && (
        <DataTable
          data={data?.par_article || []}
          columns={[
            { key: 'code_article', header: 'Code' },
            { key: 'designation', header: 'Designation' },
            { key: 'gamme', header: 'Gamme' },
            { key: 'stock_actuel', header: 'Stock', format: 'number', align: 'right' },
            { key: 'cmup_moyen', header: 'CMUP', format: 'currency', align: 'right' },
            { key: 'valeur_stock', header: 'Valeur', format: 'currency', align: 'right' },
            { key: 'dernier_mouvement', header: 'Dernier Mvt', format: 'date' }
          ]}
          onRowClick={handleArticleClick}
          clickable
          pageSize={15}
        />
      )}

      {activeTab === 'dormant' && (
        <>
          <div className="card p-4 mb-4 bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800">
            <div className="flex items-center gap-3">
              <AlertTriangle className="w-5 h-5 text-red-500" />
              <div>
                <p className="font-medium text-red-800 dark:text-red-200">
                  {data?.stock_dormant_nb_articles || 0} articles sans mouvement depuis plus de 180 jours
                </p>
                <p className="text-sm text-red-600 dark:text-red-300">
                  Valeur totale: {formatCurrency(data?.stock_dormant_valeur)}
                </p>
              </div>
            </div>
          </div>
          <DataTable
            data={data?.articles_dormants || []}
            columns={[
              { key: 'code_article', header: 'Code' },
              { key: 'designation', header: 'Designation' },
              { key: 'gamme', header: 'Gamme' },
              { key: 'stock_actuel', header: 'Stock', format: 'number', align: 'right' },
              { key: 'valeur_stock', header: 'Valeur', format: 'currency', align: 'right' },
              { key: 'jours_sans_mouvement', header: 'Jours Inactif', format: 'number', align: 'right' },
              { key: 'dernier_mouvement', header: 'Dernier Mvt', format: 'date' }
            ]}
            onRowClick={handleArticleClick}
            clickable
            pageSize={15}
          />
        </>
      )}

      {activeTab === 'rotation' && (
        <DataTable
          data={data?.rotation_par_gamme || []}
          columns={[
            { key: 'gamme', header: 'Gamme' },
            { key: 'sorties_valeur', header: 'Sorties (Valeur)', format: 'currency', align: 'right' },
            { key: 'stock_moyen_valeur', header: 'Stock Moyen', format: 'currency', align: 'right' },
            { key: 'rotation', header: 'Rotation', format: 'number', align: 'right' }
          ]}
          pageSize={15}
        />
      )}

      {/* Detail Modal */}
      <DetailModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        {...modalData}
      />
    </div>
  )
}
