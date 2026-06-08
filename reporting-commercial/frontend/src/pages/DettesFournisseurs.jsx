import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { AlertTriangle, CreditCard, Users, Database, TrendingDown } from 'lucide-react'
import KPICard from '../components/Dashboard/KPICard'
import DataTable from '../components/DrillDown/DataTable'
import DetailModal from '../components/DrillDown/DetailModal'
import { BalanceAgeeChart, TopChart } from '../components/Dashboard/Charts'
import Loading from '../components/common/Loading'
import api from '../services/api'

export default function DettesFournisseurs() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState(null)
  const [activeTab, setActiveTab] = useState('overview')
  const [drillByColumn, setDrillByColumn] = useState({})

  const [modalOpen, setModalOpen] = useState(false)
  const [modalData, setModalData] = useState({
    title: '', breadcrumb: [], data: [], columns: [], total: 0, page: 1, loading: false
  })

  useEffect(() => {
    loadData()
    api.get('/drillthrough/rules/by-source?source_type=dettes_fournisseurs')
      .then(res => { if (res.data.success) setDrillByColumn(res.data.by_column || {}) })
      .catch(() => {})
  }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const res = await api.get('/dettes-fournisseurs')
      setData(res.data)
    } catch (err) {
      console.error('Erreur chargement dettes fournisseurs:', err)
    } finally {
      setLoading(false)
    }
  }

  const tryDrill = (field, value, fallback) => {
    const rules = drillByColumn[field]
    if (rules?.length > 0) { navigate(`${rules[0].target_url}?dt_field=${rules[0].target_filter_field}&dt_value=${value ?? ''}`); return true }
    fallback(); return false
  }

  const handleFournisseurClick = async (row) => {
    if (!row?.code) return
    if (tryDrill('fournisseur', row.fournisseur, () => {})) return
    setModalData(prev => ({ ...prev, loading: true }))
    setModalOpen(true)
    try {
      const res = await api.get(`/dettes-fournisseurs/fournisseur/${encodeURIComponent(row.code)}`)
      const r = res.data
      setModalData({
        title: `Fournisseur : ${r.fournisseur}`,
        breadcrumb: ['Dettes Fournisseurs', r.fournisseur],
        data: [
          { tranche: '0-30 jours', montant: r.repartition?.['0_30'] || 0 },
          { tranche: '31-60 jours', montant: r.repartition?.['31_60'] || 0 },
          { tranche: '61-90 jours', montant: r.repartition?.['61_90'] || 0 },
          { tranche: '91-120 jours', montant: r.repartition?.['91_120'] || 0 },
          { tranche: '+120 jours', montant: r.repartition?.plus_120 || 0 },
        ],
        columns: [
          { key: 'tranche', header: 'Tranche' },
          { key: 'montant', header: 'Montant', format: 'currency', align: 'right' },
        ],
        total: 5, page: 1, loading: false,
      })
    } catch {
      setModalOpen(false)
    }
  }

  const handleTrancheClick = async (trancheData) => {
    if (!trancheData?.tranche) return
    const tranche = trancheData.tranche.replace('j', '')
    if (tryDrill('tranche', trancheData.tranche, () => {})) return
    setModalData(prev => ({ ...prev, loading: true }))
    setModalOpen(true)
    try {
      const res = await api.get(`/dettes-fournisseurs/tranche/${encodeURIComponent(tranche)}`)
      const r = res.data
      setModalData({
        title: `Tranche : ${trancheData.tranche}`,
        breadcrumb: ['Dettes Fournisseurs', 'Balance Agée', trancheData.tranche],
        data: r.data || [],
        columns: [
          { key: 'fournisseur', header: 'Fournisseur' },
          { key: 'societe', header: 'Société' },
          { key: 'montant_tranche', header: 'Montant', format: 'currency', align: 'right' },
          { key: 'dettes_total', header: 'Dettes Total', format: 'currency', align: 'right' },
        ],
        total: r.total || 0, page: 1, loading: false,
      })
    } catch {
      setModalOpen(false)
    }
  }

  const handleKPITotalClick = () => {
    setModalData({
      title: 'Top Fournisseurs — Dettes',
      breadcrumb: ['Dettes Fournisseurs', 'Top 10'],
      data: data?.top_dettes || [],
      columns: [
        { key: 'fournisseur', header: 'Fournisseur' },
        { key: 'societe', header: 'Société' },
        { key: 'dettes', header: 'Dettes', format: 'currency', align: 'right' },
        { key: 'tranche_0_30', header: '0-30j', format: 'currency', align: 'right' },
        { key: 'tranche_plus_120', header: '+120j', format: 'currency', align: 'right' },
      ],
      total: data?.top_dettes?.length || 0, page: 1, loading: false,
    })
    setModalOpen(true)
  }

  const handleKPICritiquesClick = () => {
    setModalData({
      title: 'Dettes Critiques (+120j)',
      breadcrumb: ['Dettes Fournisseurs', 'Critiques'],
      data: data?.dettes_critiques || [],
      columns: [
        { key: 'fournisseur', header: 'Fournisseur' },
        { key: 'societe', header: 'Société' },
        { key: 'dettes_plus_120', header: '+120j', format: 'currency', align: 'right' },
        { key: 'dettes_total', header: 'Dettes Total', format: 'currency', align: 'right' },
      ],
      total: data?.dettes_critiques?.length || 0, page: 1, loading: false,
    })
    setModalOpen(true)
  }

  const handleKPINbClick = () => {
    setModalData({
      title: 'Liste des Fournisseurs',
      breadcrumb: ['Dettes Fournisseurs', 'Fournisseurs'],
      data: data?.top_dettes || [],
      columns: [
        { key: 'fournisseur', header: 'Fournisseur' },
        { key: 'societe', header: 'Société' },
        { key: 'dettes', header: 'Dettes', format: 'currency', align: 'right' },
        { key: 'tranche_0_30', header: '0-30j', format: 'currency', align: 'right' },
        { key: 'tranche_31_60', header: '31-60j', format: 'currency', align: 'right' },
        { key: 'tranche_plus_120', header: '+120j', format: 'currency', align: 'right' },
      ],
      total: data?.top_dettes?.length || 0, page: 1, loading: false,
    })
    setModalOpen(true)
  }

  const tabs = [
    { id: 'overview', label: 'Vue d\'ensemble' },
    { id: 'balance', label: 'Balance Agée' },
    { id: 'critiques', label: 'Dettes Critiques' },
  ]

  const formatCurrency = (v) => (v || 0).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Dettes Fournisseurs</h1>
          <p className="text-gray-500 dark:text-gray-400">
            Analyse des échéances fournisseurs et balance âgée
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            to="/admin/datasources?category=dettes_fournisseurs"
            className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-600 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-xl transition-colors"
            title="Voir les datasources dettes fournisseurs"
          >
            <Database className="w-4 h-4" />
            DataSources
          </Link>
        </div>
      </div>

      {loading ? (
        <Loading message="Chargement des dettes fournisseurs..." />
      ) : (
        <>
          {/* KPIs */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <KPICard
              title="Dettes Total"
              formattedValue={formatCurrency(data?.dettes_total)}
              icon={CreditCard}
              color="primary"
              onClick={handleKPITotalClick}
              clickable
            />
            <KPICard
              title="Dettes Critiques +120j"
              formattedValue={formatCurrency(data?.dettes_critiques_montant)}
              icon={AlertTriangle}
              color="red"
              onClick={handleKPICritiquesClick}
              clickable
            />
            <KPICard
              title="Taux Dettes Critiques"
              formattedValue={`${data?.taux_dettes_critiques || 0}%`}
              icon={TrendingDown}
              color="yellow"
              onClick={handleKPICritiquesClick}
              clickable
            />
            <KPICard
              title="Nombre de Fournisseurs"
              formattedValue={String(data?.nb_fournisseurs || 0)}
              icon={Users}
              color="blue"
              onClick={handleKPINbClick}
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
                data={data?.top_dettes || []}
                dataKey="dettes"
                nameKey="fournisseur"
                title="Top 10 Dettes Fournisseurs"
                onBarClick={handleFournisseurClick}
              />

              {/* Répartition pourcentages */}
              <div className="card p-6 lg:col-span-2">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  Répartition des Dettes
                </h3>
                <div className="grid grid-cols-5 gap-4">
                  {[
                    { label: '0-30j', key: '0_30', color: 'bg-emerald-500', tranche: '0-30j' },
                    { label: '31-60j', key: '31_60', color: 'bg-green-500', tranche: '31-60j' },
                    { label: '61-90j', key: '61_90', color: 'bg-amber-500', tranche: '61-90j' },
                    { label: '91-120j', key: '91_120', color: 'bg-orange-500', tranche: '91-120j' },
                    { label: '+120j', key: 'plus_120', color: 'bg-red-500', tranche: '+120j' },
                  ].map((t) => (
                    <div
                      key={t.key}
                      className="text-center cursor-pointer p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                      onClick={() => handleTrancheClick({ tranche: t.tranche })}
                      title="Cliquez pour voir le détail"
                    >
                      <div className={`h-2 ${t.color} rounded-full mb-2`} style={{
                        width: `${data?.repartition_pct?.[t.key] || 0}%`,
                        minWidth: '10%'
                      }} />
                      <p className="text-sm font-medium text-gray-900 dark:text-white">{t.label}</p>
                      <p className="text-lg font-bold text-gray-900 dark:text-white">
                        {data?.repartition_pct?.[t.key] || 0}%
                      </p>
                      <p className="text-xs text-gray-500">
                        {formatCurrency(data?.repartition_tranches?.[t.key])}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'balance' && (
            <DataTable
              data={data?.top_dettes || []}
              columns={[
                { key: 'fournisseur', header: 'Fournisseur' },
                { key: 'societe', header: 'Société' },
                { key: 'dettes', header: 'Dettes', format: 'currency', align: 'right' },
                { key: 'tranche_0_30', header: '0-30j', format: 'currency', align: 'right' },
                { key: 'tranche_31_60', header: '31-60j', format: 'currency', align: 'right' },
                { key: 'tranche_61_90', header: '61-90j', format: 'currency', align: 'right' },
                { key: 'tranche_91_120', header: '91-120j', format: 'currency', align: 'right' },
                { key: 'tranche_plus_120', header: '+120j', format: 'currency', align: 'right' },
              ]}
              onRowClick={handleFournisseurClick}
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
                      {data?.dettes_critiques?.length || 0} fournisseurs avec dettes critiques
                    </p>
                    <p className="text-sm text-red-600 dark:text-red-300">
                      Dettes +120 jours de retard
                    </p>
                  </div>
                </div>
              </div>
              <DataTable
                data={data?.dettes_critiques || []}
                columns={[
                  { key: 'fournisseur', header: 'Fournisseur' },
                  { key: 'societe', header: 'Société' },
                  { key: 'dettes_plus_120', header: '+120j', format: 'currency', align: 'right' },
                  { key: 'dettes_total', header: 'Dettes Total', format: 'currency', align: 'right' },
                ]}
                onRowClick={handleFournisseurClick}
                clickable
                pageSize={15}
              />
            </>
          )}
        </>
      )}

      <DetailModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        {...modalData}
      />
    </div>
  )
}
