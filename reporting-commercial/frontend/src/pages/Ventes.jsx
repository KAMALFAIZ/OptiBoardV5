import { useState, useEffect } from 'react'
import { Download, TrendingUp, Users, ShoppingCart, Package } from 'lucide-react'
import KPICard from '../components/Dashboard/KPICard'
import DataTable from '../components/DrillDown/DataTable'
import DetailModal from '../components/DrillDown/DetailModal'
import { CAEvolutionChart, CAParGammeChart, TopChart } from '../components/Dashboard/Charts'
import Filters from '../components/common/Filters'
import Loading from '../components/common/Loading'
import {
  getVentes,
  getDetailGamme,
  getDetailClient,
  getDetailCommercial,
  getDetailProduit,
  exportVentesExcel,
  downloadBlob
} from '../services/api'

export default function Ventes() {
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState(null)
  const [filters, setFilters] = useState({ periode: 'annee_courante' })
  const [activeTab, setActiveTab] = useState('overview')

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

  const loadData = async () => {
    setLoading(true)
    try {
      const response = await getVentes(filters)
      setData(response.data)
    } catch (error) {
      console.error('Error loading ventes:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleExport = async () => {
    try {
      const response = await exportVentesExcel(filters)
      downloadBlob(response.data, `ventes_${new Date().toISOString().slice(0, 10)}.xlsx`)
    } catch (error) {
      console.error('Export error:', error)
    }
  }

  // Drill-down handlers
  const handleGammeClick = async (row) => {
    if (!row?.gamme) return
    setModalData(prev => ({ ...prev, loading: true }))
    setModalOpen(true)

    try {
      const response = await getDetailGamme(row.gamme, filters)
      const result = response.data

      setModalData({
        title: `Gamme: ${row.gamme}`,
        breadcrumb: ['Ventes', 'Par Gamme', row.gamme],
        data: result.data || [],
        columns: [
          { key: 'code_article', header: 'Code Article' },
          { key: 'designation', header: 'Designation' },
          { key: 'quantite_vendue', header: 'Quantite', format: 'number' },
          { key: 'ca_ht', header: 'CA HT', format: 'currency' },
          { key: 'marge_brute', header: 'Marge', format: 'currency' },
          { key: 'nb_clients', header: 'Nb Clients', format: 'number' }
        ],
        total: result.total || 0,
        page: 1,
        loading: false
      })
    } catch (error) {
      console.error('Error:', error)
      setModalOpen(false)
    }
  }

  const handleClientClick = async (row) => {
    if (!row?.code_client) return
    setModalData(prev => ({ ...prev, loading: true }))
    setModalOpen(true)

    try {
      const response = await getDetailClient(row.code_client, filters)
      const result = response.data

      setModalData({
        title: `Client: ${row.nom_client}`,
        breadcrumb: ['Ventes', 'Top Clients', row.nom_client],
        data: result.achats || [],
        columns: [
          { key: 'date', header: 'Date', format: 'date' },
          { key: 'numero_piece', header: 'N. Piece' },
          { key: 'code_article', header: 'Article' },
          { key: 'designation', header: 'Designation' },
          { key: 'quantite', header: 'Qte', format: 'number' },
          { key: 'montant_ht', header: 'Montant HT', format: 'currency' }
        ],
        total: result.total || 0,
        page: 1,
        loading: false
      })
    } catch (error) {
      console.error('Error:', error)
      setModalOpen(false)
    }
  }

  const handleCommercialClick = async (row) => {
    if (!row?.commercial) return
    setModalData(prev => ({ ...prev, loading: true }))
    setModalOpen(true)

    try {
      const response = await getDetailCommercial(row.commercial, filters)
      const result = response.data

      setModalData({
        title: `Commercial: ${row.commercial}`,
        breadcrumb: ['Ventes', 'Par Commercial', row.commercial],
        data: result.top_clients || [],
        columns: [
          { key: 'code_client', header: 'Code' },
          { key: 'nom_client', header: 'Client' },
          { key: 'ca_ht', header: 'CA HT', format: 'currency' },
          { key: 'nb_transactions', header: 'Nb Transactions', format: 'number' }
        ],
        total: result.top_clients?.length || 0,
        page: 1,
        loading: false
      })
    } catch (error) {
      console.error('Error:', error)
      setModalOpen(false)
    }
  }

  const handleProduitClick = async (row) => {
    if (!row?.code_article) return
    setModalData(prev => ({ ...prev, loading: true }))
    setModalOpen(true)

    try {
      const response = await getDetailProduit(row.code_article, filters)
      const result = response.data

      setModalData({
        title: `Produit: ${row.designation}`,
        breadcrumb: ['Ventes', 'Top Produits', row.designation],
        data: result.ventes || [],
        columns: [
          { key: 'date', header: 'Date', format: 'date' },
          { key: 'nom_client', header: 'Client' },
          { key: 'commercial', header: 'Commercial' },
          { key: 'quantite', header: 'Qte', format: 'number' },
          { key: 'montant_ht', header: 'Montant HT', format: 'currency' }
        ],
        total: result.total || 0,
        page: 1,
        loading: false
      })
    } catch (error) {
      console.error('Error:', error)
      setModalOpen(false)
    }
  }

  // Handler pour clic sur période (Evolution CA)
  const handlePeriodeClick = (periodeData) => {
    if (!periodeData?.periode) return
    const periode = periodeData.periode
    setModalData({
      title: `Période: ${periode}`,
      breadcrumb: ['Ventes', 'Evolution CA', periode],
      data: [periodeData],
      columns: [
        { key: 'periode', header: 'Période' },
        { key: 'ca_ht', header: 'CA HT', format: 'currency' },
        { key: 'marge_brute', header: 'Marge Brute', format: 'currency' },
        { key: 'nb_ventes', header: 'Nb Ventes', format: 'number' }
      ],
      total: 1,
      page: 1,
      loading: false
    })
    setModalOpen(true)
  }

  // Handler pour KPI CA Total HT - affiche toutes les ventes par gamme
  const handleKPICAClick = () => {
    setModalData({
      title: 'CA Total HT - Détail par Gamme',
      breadcrumb: ['Ventes', 'CA Total HT'],
      data: data?.par_gamme || [],
      columns: [
        { key: 'gamme', header: 'Gamme' },
        { key: 'ca_ht', header: 'CA HT', format: 'currency' },
        { key: 'marge_brute', header: 'Marge Brute', format: 'currency' },
        { key: 'taux_marge', header: 'Taux Marge', format: 'percent' },
        { key: 'nb_ventes', header: 'Nb Ventes', format: 'number' }
      ],
      total: data?.par_gamme?.length || 0,
      page: 1,
      loading: false
    })
    setModalOpen(true)
  }

  // Handler pour KPI Clients - affiche tous les clients
  const handleKPIClientsClick = () => {
    setModalData({
      title: 'Liste des Clients',
      breadcrumb: ['Ventes', 'Clients'],
      data: data?.top_clients || [],
      columns: [
        { key: 'code_client', header: 'Code' },
        { key: 'nom_client', header: 'Client' },
        { key: 'commercial', header: 'Commercial' },
        { key: 'ca_ht', header: 'CA HT', format: 'currency' },
        { key: 'nb_transactions', header: 'Transactions', format: 'number' }
      ],
      total: data?.top_clients?.length || 0,
      page: 1,
      loading: false
    })
    setModalOpen(true)
  }

  // Handler pour KPI Gammes - affiche toutes les gammes
  const handleKPIGammesClick = () => {
    setModalData({
      title: 'Liste des Gammes',
      breadcrumb: ['Ventes', 'Gammes'],
      data: data?.par_gamme || [],
      columns: [
        { key: 'gamme', header: 'Gamme' },
        { key: 'ca_ht', header: 'CA HT', format: 'currency' },
        { key: 'marge_brute', header: 'Marge Brute', format: 'currency' },
        { key: 'taux_marge', header: 'Taux Marge', format: 'percent' },
        { key: 'pourcentage_ca', header: '% CA', format: 'percent' }
      ],
      total: data?.par_gamme?.length || 0,
      page: 1,
      loading: false
    })
    setModalOpen(true)
  }

  const tabs = [
    { id: 'overview', label: 'Vue d\'ensemble' },
    { id: 'gammes', label: 'Par Gamme' },
    { id: 'commerciaux', label: 'Par Commercial' },
    { id: 'clients', label: 'Top Clients' },
    { id: 'produits', label: 'Top Produits' }
  ]

  const formatCurrency = (value) => {
    return (value || 0).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Analyse des Ventes</h1>
          <p className="text-gray-500 dark:text-gray-400">
            Performance commerciale et analyse detaillee
          </p>
        </div>
        <button onClick={handleExport} className="btn-primary flex items-center gap-2">
          <Download className="w-4 h-4" />
          Exporter Excel
        </button>
      </div>

      {/* Filters - toujours visible */}
      <Filters onFilterChange={setFilters} showPeriod={true} />

      {/* Loading state */}
      {loading ? (
        <Loading message="Chargement des ventes..." />
      ) : (
        <>
      {/* KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          title="CA Total HT"
          formattedValue={formatCurrency(data?.ca_total_ht)}
          icon={TrendingUp}
          color="primary"
          onClick={handleKPICAClick}
          clickable
        />
        <KPICard
          title="CA Total TTC"
          formattedValue={formatCurrency(data?.ca_total_ttc)}
          icon={TrendingUp}
          color="blue"
          onClick={handleKPICAClick}
          clickable
        />
        <KPICard
          title="Nombre de Gammes"
          formattedValue={String(data?.par_gamme?.length || 0)}
          icon={Package}
          color="purple"
          onClick={handleKPIGammesClick}
          clickable
        />
        <KPICard
          title="Nombre de Clients"
          formattedValue={String(data?.top_clients?.length || 0)}
          icon={Users}
          color="green"
          onClick={handleKPIClientsClick}
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
          <CAEvolutionChart data={data?.par_periode || []} onBarClick={handlePeriodeClick} />
          <CAParGammeChart data={data?.par_gamme || []} onSliceClick={handleGammeClick} />
        </div>
      )}

      {activeTab === 'gammes' && (
        <DataTable
          data={data?.par_gamme || []}
          columns={[
            { key: 'gamme', header: 'Gamme' },
            { key: 'ca_ht', header: 'CA HT', format: 'currency', align: 'right' },
            { key: 'marge_brute', header: 'Marge Brute', format: 'currency', align: 'right' },
            { key: 'taux_marge', header: 'Taux Marge', format: 'percent', align: 'right' },
            { key: 'nb_ventes', header: 'Nb Ventes', format: 'number', align: 'right' },
            { key: 'pourcentage_ca', header: '% CA', format: 'percent', align: 'right' }
          ]}
          onRowClick={handleGammeClick}
          clickable
          pageSize={15}
        />
      )}

      {activeTab === 'commerciaux' && (
        <DataTable
          data={data?.par_commercial || []}
          columns={[
            { key: 'commercial', header: 'Commercial' },
            { key: 'ca_ht', header: 'CA HT', format: 'currency', align: 'right' },
            { key: 'marge_brute', header: 'Marge Brute', format: 'currency', align: 'right' },
            { key: 'nb_clients', header: 'Nb Clients', format: 'number', align: 'right' },
            { key: 'nb_ventes', header: 'Nb Ventes', format: 'number', align: 'right' }
          ]}
          onRowClick={handleCommercialClick}
          clickable
          pageSize={15}
        />
      )}

      {activeTab === 'clients' && (
        <DataTable
          data={data?.top_clients || []}
          columns={[
            { key: 'code_client', header: 'Code' },
            { key: 'nom_client', header: 'Client' },
            { key: 'commercial', header: 'Commercial' },
            { key: 'ca_ht', header: 'CA HT', format: 'currency', align: 'right' },
            { key: 'nb_transactions', header: 'Transactions', format: 'number', align: 'right' }
          ]}
          onRowClick={handleClientClick}
          clickable
          pageSize={15}
        />
      )}

      {activeTab === 'produits' && (
        <DataTable
          data={data?.top_produits || []}
          columns={[
            { key: 'code_article', header: 'Code' },
            { key: 'designation', header: 'Designation' },
            { key: 'gamme', header: 'Gamme' },
            { key: 'quantite_vendue', header: 'Qte Vendue', format: 'number', align: 'right' },
            { key: 'ca_ht', header: 'CA HT', format: 'currency', align: 'right' }
          ]}
          onRowClick={handleProduitClick}
          clickable
          pageSize={15}
        />
      )}
        </>
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
