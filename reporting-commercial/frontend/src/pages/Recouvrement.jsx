import { useState, useEffect } from 'react'
import { Download, CreditCard, Clock, AlertTriangle, Users } from 'lucide-react'
import KPICard from '../components/Dashboard/KPICard'
import DataTable from '../components/DrillDown/DataTable'
import DetailModal from '../components/DrillDown/DetailModal'
import { BalanceAgeeChart, TopChart } from '../components/Dashboard/Charts'
import Filters from '../components/common/Filters'
import Loading from '../components/common/Loading'
import {
  getRecouvrement,
  getBalanceAgee,
  getClientEncours,
  getCommercialEncours,
  getClientsParTranche,
  exportRecouvrementExcel,
  downloadBlob
} from '../services/api'

export default function Recouvrement() {
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
      const response = await getRecouvrement(filters)
      setData(response.data)
    } catch (error) {
      console.error('Error loading recouvrement:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleExport = async () => {
    try {
      const response = await exportRecouvrementExcel()
      downloadBlob(response.data, `recouvrement_${new Date().toISOString().slice(0, 10)}.xlsx`)
    } catch (error) {
      console.error('Export error:', error)
    }
  }

  // Drill-down handlers
  const handleClientClick = async (row) => {
    if (!row?.client) return
    setModalData(prev => ({ ...prev, loading: true }))
    setModalOpen(true)

    try {
      const response = await getClientEncours(row.client)
      const result = response.data

      setModalData({
        title: `Client: ${row.client}`,
        breadcrumb: ['Recouvrement', 'Clients', row.client],
        data: [
          { tranche: '0-30 jours', montant: result.repartition?.['0_30'] || 0 },
          { tranche: '31-60 jours', montant: result.repartition?.['31_60'] || 0 },
          { tranche: '61-90 jours', montant: result.repartition?.['61_90'] || 0 },
          { tranche: '91-120 jours', montant: result.repartition?.['91_120'] || 0 },
          { tranche: '+120 jours', montant: result.repartition?.plus_120 || 0 }
        ],
        columns: [
          { key: 'tranche', header: 'Tranche' },
          { key: 'montant', header: 'Montant', format: 'currency', align: 'right' }
        ],
        total: 5,
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
      const response = await getCommercialEncours(row.commercial)
      const result = response.data

      setModalData({
        title: `Commercial: ${row.commercial}`,
        breadcrumb: ['Recouvrement', 'Commerciaux', row.commercial],
        data: result.clients || [],
        columns: [
          { key: 'client', header: 'Client' },
          { key: 'societe', header: 'Societe' },
          { key: 'encours', header: 'Encours', format: 'currency', align: 'right' },
          { key: 'impayes', header: 'Impayes', format: 'currency', align: 'right' },
          { key: 'plus_120', header: '+120j', format: 'currency', align: 'right' }
        ],
        total: result.nb_clients || 0,
        page: 1,
        loading: false
      })
    } catch (error) {
      console.error('Error:', error)
      setModalOpen(false)
    }
  }

  const handleTrancheClick = async (trancheData) => {
    if (!trancheData?.tranche) return
    const tranche = trancheData.tranche.replace('j', '')
    setModalData(prev => ({ ...prev, loading: true }))
    setModalOpen(true)

    try {
      const response = await getClientsParTranche(tranche)
      const result = response.data

      setModalData({
        title: `Tranche: ${trancheData.tranche}`,
        breadcrumb: ['Recouvrement', 'Balance Agee', trancheData.tranche],
        data: result.data || [],
        columns: [
          { key: 'client', header: 'Client' },
          { key: 'commercial', header: 'Commercial' },
          { key: 'montant_tranche', header: 'Montant', format: 'currency', align: 'right' },
          { key: 'encours_total', header: 'Encours Total', format: 'currency', align: 'right' }
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

  // Handler pour KPI DSO
  const handleKPIDSOClick = () => {
    setModalData({
      title: 'DSO - Détail par Commercial',
      breadcrumb: ['Recouvrement', 'DSO'],
      data: data?.par_commercial || [],
      columns: [
        { key: 'commercial', header: 'Commercial' },
        { key: 'nb_clients', header: 'Nb Clients', format: 'number' },
        { key: 'encours_total', header: 'Encours Total', format: 'currency' },
        { key: 'total_impayes', header: 'Impayés', format: 'currency' }
      ],
      total: data?.par_commercial?.length || 0,
      page: 1,
      loading: false
    })
    setModalOpen(true)
  }

  // Handler pour KPI Encours Total
  const handleKPIEncoursClick = () => {
    setModalData({
      title: 'Encours Total - Top Clients',
      breadcrumb: ['Recouvrement', 'Encours'],
      data: data?.top_encours || [],
      columns: [
        { key: 'client', header: 'Client' },
        { key: 'commercial', header: 'Commercial' },
        { key: 'encours', header: 'Encours', format: 'currency' },
        { key: 'tranche_0_30', header: '0-30j', format: 'currency' },
        { key: 'tranche_plus_120', header: '+120j', format: 'currency' }
      ],
      total: data?.top_encours?.length || 0,
      page: 1,
      loading: false
    })
    setModalOpen(true)
  }

  // Handler pour KPI Créances Douteuses
  const handleKPICreancesClick = () => {
    setModalData({
      title: 'Créances Douteuses (+120j)',
      breadcrumb: ['Recouvrement', 'Créances Douteuses'],
      data: data?.creances_critiques || [],
      columns: [
        { key: 'client', header: 'Client' },
        { key: 'commercial', header: 'Commercial' },
        { key: 'societe', header: 'Société' },
        { key: 'creances_plus_120', header: '+120j', format: 'currency' },
        { key: 'impayes', header: 'Impayés', format: 'currency' }
      ],
      total: data?.creances_critiques?.length || 0,
      page: 1,
      loading: false
    })
    setModalOpen(true)
  }

  // Handler pour KPI Nombre de Clients
  const handleKPINbClientsClick = () => {
    setModalData({
      title: 'Liste des Clients',
      breadcrumb: ['Recouvrement', 'Clients'],
      data: data?.top_encours || [],
      columns: [
        { key: 'client', header: 'Client' },
        { key: 'commercial', header: 'Commercial' },
        { key: 'encours', header: 'Encours', format: 'currency' },
        { key: 'tranche_0_30', header: '0-30j', format: 'currency' },
        { key: 'tranche_31_60', header: '31-60j', format: 'currency' },
        { key: 'tranche_plus_120', header: '+120j', format: 'currency' }
      ],
      total: data?.top_encours?.length || 0,
      page: 1,
      loading: false
    })
    setModalOpen(true)
  }

  const tabs = [
    { id: 'overview', label: 'Vue d\'ensemble' },
    { id: 'balance', label: 'Balance Agee' },
    { id: 'commerciaux', label: 'Par Commercial' },
    { id: 'critiques', label: 'Creances Critiques' }
  ]

  const formatCurrency = (value) => {
    return (value || 0).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }

  const getDSOColor = (dso) => {
    if (dso < 30) return 'green'
    if (dso < 60) return 'yellow'
    return 'red'
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Recouvrement & DSO</h1>
          <p className="text-gray-500 dark:text-gray-400">
            Analyse des encours clients et indicateurs de recouvrement
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
        <Loading message="Chargement du recouvrement..." />
      ) : (
        <>
      {/* KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        <KPICard
          title="DSO"
          formattedValue={`${data?.dso || 0} jours`}
          icon={Clock}
          color={getDSOColor(data?.dso)}
          onClick={handleKPIDSOClick}
          clickable
        />
        <KPICard
          title="Encours Total"
          formattedValue={formatCurrency(data?.encours_total)}
          icon={CreditCard}
          color="primary"
          onClick={handleKPIEncoursClick}
          clickable
        />
        <KPICard
          title="Creances Douteuses"
          formattedValue={formatCurrency(data?.creances_douteuses)}
          icon={AlertTriangle}
          color="red"
          onClick={handleKPICreancesClick}
          clickable
        />
        <KPICard
          title="Taux Creances Douteuses"
          formattedValue={`${data?.taux_creances_douteuses || 0}%`}
          icon={AlertTriangle}
          color="yellow"
          onClick={handleKPICreancesClick}
          clickable
        />
        <KPICard
          title="Nombre de Clients"
          formattedValue={String(data?.nb_clients || 0)}
          icon={Users}
          color="blue"
          onClick={handleKPINbClientsClick}
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
          <BalanceAgeeChart
            data={data?.repartition_tranches || {}}
            onBarClick={handleTrancheClick}
          />
          <TopChart
            data={data?.top_encours || []}
            dataKey="encours"
            nameKey="client"
            title="Top 10 Encours Clients"
            onBarClick={handleClientClick}
          />

          {/* Repartition percentages */}
          <div className="card p-6 lg:col-span-2">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Repartition des Encours
            </h3>
            <div className="grid grid-cols-5 gap-4">
              {[
                { label: '0-30j', key: '0_30', color: 'bg-emerald-500', tranche: '0-30j' },
                { label: '31-60j', key: '31_60', color: 'bg-green-500', tranche: '31-60j' },
                { label: '61-90j', key: '61_90', color: 'bg-amber-500', tranche: '61-90j' },
                { label: '91-120j', key: '91_120', color: 'bg-orange-500', tranche: '91-120j' },
                { label: '+120j', key: 'plus_120', color: 'bg-red-500', tranche: '+120j' }
              ].map((tranche) => (
                <div
                  key={tranche.key}
                  className="text-center cursor-pointer p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                  onClick={() => handleTrancheClick({ tranche: tranche.tranche })}
                  title="Cliquez pour voir le détail"
                >
                  <div className={`h-2 ${tranche.color} rounded-full mb-2`} style={{
                    width: `${data?.repartition_pct?.[tranche.key] || 0}%`,
                    minWidth: '10%'
                  }} />
                  <p className="text-sm font-medium text-gray-900 dark:text-white">{tranche.label}</p>
                  <p className="text-lg font-bold text-gray-900 dark:text-white">
                    {data?.repartition_pct?.[tranche.key] || 0}%
                  </p>
                  <p className="text-xs text-gray-500">
                    {formatCurrency(data?.repartition_tranches?.[tranche.key])}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'balance' && (
        <DataTable
          data={data?.top_encours || []}
          columns={[
            { key: 'client', header: 'Client' },
            { key: 'commercial', header: 'Commercial' },
            { key: 'encours', header: 'Encours', format: 'currency', align: 'right' },
            { key: 'tranche_0_30', header: '0-30j', format: 'currency', align: 'right' },
            { key: 'tranche_31_60', header: '31-60j', format: 'currency', align: 'right' },
            { key: 'tranche_61_90', header: '61-90j', format: 'currency', align: 'right' },
            { key: 'tranche_91_120', header: '91-120j', format: 'currency', align: 'right' },
            { key: 'tranche_plus_120', header: '+120j', format: 'currency', align: 'right' }
          ]}
          onRowClick={handleClientClick}
          clickable
          pageSize={15}
        />
      )}

      {activeTab === 'commerciaux' && (
        <DataTable
          data={data?.par_commercial || []}
          columns={[
            { key: 'commercial', header: 'Commercial' },
            { key: 'nb_clients', header: 'Nb Clients', format: 'number', align: 'right' },
            { key: 'encours_total', header: 'Encours Total', format: 'currency', align: 'right' },
            { key: 'tranche_0_30', header: '0-30j', format: 'currency', align: 'right' },
            { key: 'tranche_plus_120', header: '+120j', format: 'currency', align: 'right' },
            { key: 'total_impayes', header: 'Impayes', format: 'currency', align: 'right' }
          ]}
          onRowClick={handleCommercialClick}
          clickable
          pageSize={15}
        />
      )}

      {activeTab === 'critiques' && (
        <>
          <div className="card p-4 mb-4 bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800">
            <div className="flex items-center gap-3">
              <AlertTriangle className="w-5 h-5 text-red-500" />
              <div>
                <p className="font-medium text-red-800 dark:text-red-200">
                  {data?.creances_critiques?.length || 0} clients avec creances critiques
                </p>
                <p className="text-sm text-red-600 dark:text-red-300">
                  Creances +120 jours ou impayes
                </p>
              </div>
            </div>
          </div>
          <DataTable
            data={data?.creances_critiques || []}
            columns={[
              { key: 'client', header: 'Client' },
              { key: 'commercial', header: 'Commercial' },
              { key: 'societe', header: 'Societe' },
              { key: 'creances_plus_120', header: '+120j', format: 'currency', align: 'right' },
              { key: 'impayes', header: 'Impayes', format: 'currency', align: 'right' },
              { key: 'encours_total', header: 'Encours Total', format: 'currency', align: 'right' }
            ]}
            onRowClick={handleClientClick}
            clickable
            pageSize={15}
          />
        </>
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
