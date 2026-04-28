import { useState, useEffect, useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Download, Filter, RefreshCw, ChevronLeft, ChevronRight, ChevronUp, ChevronDown, ChevronsUpDown, Search, X, ArrowRight } from 'lucide-react'
import Loading from '../components/common/Loading'
import { getListeVentes, getListeVentesFiltres, exportListeVentes, downloadBlob } from '../services/api'
import { useGlobalFilters } from '../context/GlobalFilterContext'

export default function ListeVentes() {
  const [searchParams] = useSearchParams()
  const { updateFilter } = useGlobalFilters()
  const [loading, setLoading] = useState(true)
  const [exporting, setExporting] = useState(false)
  const [data, setData] = useState([])
  const [totaux, setTotaux] = useState({})
  const [pagination, setPagination] = useState({
    page: 1,
    page_size: 50,
    total_records: 0,
    total_pages: 0
  })
  const [filtresDisponibles, setFiltresDisponibles] = useState({
    gammes: [],
    catalogue2: [],
    catalogue3: [],
    commerciaux: [],
    canaux: [],
    zones: [],
    regions: [],
    villes: [],
    groupes: [],
    societes: []
  })

  // Filtres (annee 2025 fixee cote backend)
  const [filters, setFilters] = useState({
    societe: '',
    gamme: '',
    catalogue2: '',
    catalogue3: '',
    commercial: '',
    canal: '',
    zone: '',
    region: '',
    ville: '',
    groupe: ''
  })

  const [showFilters, setShowFilters] = useState(false)

  // Etat pour le tri
  const [sortConfig, setSortConfig] = useState({ key: 'montant_ht', direction: 'desc' })

  // Recherche sur designation
  const [searchDesignation, setSearchDesignation] = useState('')

  // Filtres par colonne (filtrage local sur les donnees affichees)
  const [columnFilters, setColumnFilters] = useState({
    gamme: '',
    catalogue2: '',
    catalogue3: '',
    designation: '',
    intitule_client: '',
    commercial: '',
    region: ''
  })

  // Charger les filtres disponibles (annee 2025 fixee cote backend)
  const loadFiltres = useCallback(async () => {
    try {
      const response = await getListeVentesFiltres()
      if (response.data.success) {
        setFiltresDisponibles({
          gammes: response.data.gammes || [],
          catalogue2: response.data.catalogue2 || [],
          catalogue3: response.data.catalogue3 || [],
          commerciaux: response.data.commerciaux || [],
          canaux: response.data.canaux || [],
          zones: response.data.zones || [],
          regions: response.data.regions || [],
          villes: response.data.villes || [],
          groupes: response.data.groupes || [],
          societes: response.data.societes || []
        })
      }
    } catch (error) {
      console.error('Erreur chargement filtres:', error)
    }
  }, [])

  // Charger les donnees
  const loadData = useCallback(async (page = 1) => {
    setLoading(true)
    try {
      const params = {
        ...filters,
        page,
        page_size: pagination.page_size
      }
      // Nettoyer les params vides
      Object.keys(params).forEach(key => {
        if (params[key] === '' || params[key] === null) {
          delete params[key]
        }
      })

      const response = await getListeVentes(params)
      if (response.data.success) {
        setData(response.data.data || [])
        setTotaux(response.data.totaux || {})
        setPagination(response.data.pagination || {
          page: 1,
          page_size: 50,
          total_records: 0,
          total_pages: 0
        })
      }
    } catch (error) {
      console.error('Erreur chargement donnees:', error)
    } finally {
      setLoading(false)
    }
  }, [filters, pagination.page_size])

  // Charger au montage et quand les filtres changent
  useEffect(() => {
    loadFiltres()
  }, [loadFiltres])

  // Appliquer les paramètres drill-through entrants (une seule fois au montage)
  useEffect(() => {
    const dtField = searchParams.get('dt_field')
    const dtValue = searchParams.get('dt_value')
    const gfDateDebut = searchParams.get('gf_dateDebut')
    const gfDateFin = searchParams.get('gf_dateFin')
    const gfSociete = searchParams.get('gf_societe')
    if (gfDateDebut) updateFilter('dateDebut', gfDateDebut)
    if (gfDateFin) updateFilter('dateFin', gfDateFin)
    if (gfSociete) updateFilter('societe', gfSociete)
    if (dtField && dtValue) {
      // Mapper dt_field vers le filtre ListeVentes correspondant
      const fieldMap = {
        gamme: 'gamme', commercial: 'commercial', code_client: 'code_client',
        societe: 'societe', zone: 'zone', region: 'region',
        code_article: 'code_article',
      }
      const key = fieldMap[dtField] || dtField
      if (key in filters) {
        setFilters(prev => ({ ...prev, [key]: dtValue }))
      }
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    loadData(1)
  }, [filters])

  // Export Excel
  const handleExport = async () => {
    setExporting(true)
    try {
      const params = { ...filters }
      Object.keys(params).forEach(key => {
        if (params[key] === '' || params[key] === null) {
          delete params[key]
        }
      })

      const response = await exportListeVentes(params)
      if (response.data.success) {
        // Creer un fichier Excel a partir des donnees
        const exportData = response.data.data
        const csvContent = generateCSV(exportData)
        const blob = new Blob(["\ufeff" + csvContent], { type: 'text/csv;charset=utf-8;' })
        downloadBlob(blob, `liste_ventes_${new Date().toISOString().split('T')[0]}.csv`)
      }
    } catch (error) {
      console.error('Erreur export:', error)
    } finally {
      setExporting(false)
    }
  }

  // Generer CSV (sans Zone, Ville, Societe, Canal, Groupe, Premiere/Derniere Vente)
  const generateCSV = (data) => {
    const headers = [
      'Gamme', 'Catalogue 2', 'Catalogue 3', 'Designation', 'Client',
      'Commercial', 'Region',
      'Quantite', 'Montant HT', 'Montant TTC',
      'Marge Brute', 'Taux Marge %',
      'Prix Unit Min', 'Prix Unit Max', 'Prix Unit Moyen',
      'Nb Transactions', 'Nb Factures'
    ]

    const rows = data.map(row => [
      row.gamme,
      row.catalogue2,
      row.catalogue3,
      row.designation,
      row.intitule_client,
      row.commercial,
      row.region,
      row.quantite_totale,
      row.montant_ht,
      row.montant_ttc,
      row.marge_brute,
      row.taux_marge,
      row.prix_unit_min,
      row.prix_unit_max,
      row.prix_unit_moyen,
      row.nb_transactions,
      row.nb_factures
    ])

    return [headers.join(';'), ...rows.map(r => r.join(';'))].join('\n')
  }

  // Gestion pagination
  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= pagination.total_pages) {
      loadData(newPage)
    }
  }

  // Reset filtres
  const resetFilters = () => {
    setFilters({
      societe: '',
      gamme: '',
      catalogue2: '',
      catalogue3: '',
      commercial: '',
      canal: '',
      zone: '',
      region: '',
      ville: '',
      groupe: ''
    })
  }

  // Format monnaie
  const formatCurrency = (value) => {
    return new Intl.NumberFormat('fr-FR', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value || 0)
  }

  // Format en millions
  const formatMillions = (value) => {
    const millions = (value || 0) / 1000000
    return new Intl.NumberFormat('fr-FR', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(millions) + ' M'
  }

  // Gestion du tri
  const handleSort = (key) => {
    setSortConfig(prev => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc'
    }))
  }

  // Donnees filtrees par recherche designation, filtres colonnes puis triees
  const sortedData = useMemo(() => {
    // Filtrer par recherche designation
    let filteredData = data
    if (searchDesignation.trim()) {
      const searchLower = searchDesignation.toLowerCase().trim()
      filteredData = filteredData.filter(row =>
        row.designation && row.designation.toLowerCase().includes(searchLower)
      )
    }

    // Appliquer les filtres par colonne
    Object.keys(columnFilters).forEach(key => {
      const filterValue = columnFilters[key]
      if (filterValue && filterValue.trim()) {
        const filterLower = filterValue.toLowerCase().trim()
        filteredData = filteredData.filter(row => {
          const cellValue = row[key]
          if (cellValue === null || cellValue === undefined) return false
          return String(cellValue).toLowerCase().includes(filterLower)
        })
      }
    })

    // Trier
    if (!sortConfig.key) return filteredData

    return [...filteredData].sort((a, b) => {
      const aVal = a[sortConfig.key]
      const bVal = b[sortConfig.key]

      // Gestion des valeurs nulles
      if (aVal === null || aVal === undefined) return 1
      if (bVal === null || bVal === undefined) return -1

      // Tri numerique ou alphabetique
      let comparison = 0
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        comparison = aVal - bVal
      } else {
        comparison = String(aVal).localeCompare(String(bVal), 'fr-FR', { sensitivity: 'base' })
      }

      return sortConfig.direction === 'asc' ? comparison : -comparison
    })
  }, [data, sortConfig, searchDesignation, columnFilters])

  // Reset filtres colonnes
  const resetColumnFilters = () => {
    setColumnFilters({
      gamme: '',
      catalogue2: '',
      catalogue3: '',
      designation: '',
      intitule_client: '',
      commercial: '',
      region: ''
    })
  }

  // Verifier si des filtres colonnes sont actifs
  const hasActiveColumnFilters = Object.values(columnFilters).some(v => v && v.trim())

  // Icone de tri pour une colonne
  const getSortIcon = (key) => {
    if (sortConfig.key !== key) {
      return <ChevronsUpDown className="w-3 h-3 opacity-40" />
    }
    return sortConfig.direction === 'asc'
      ? <ChevronUp className="w-3 h-3" />
      : <ChevronDown className="w-3 h-3" />
  }

  // Colonnes du tableau (sans Zone, Ville, Societe, Canal, Groupe, Premiere/Derniere Vente)
  const columns = [
    { key: 'gamme', header: 'Gamme' },
    { key: 'catalogue2', header: 'Cat. 2' },
    { key: 'catalogue3', header: 'Cat. 3' },
    { key: 'designation', header: 'Designation' },
    { key: 'intitule_client', header: 'Client' },
    { key: 'commercial', header: 'Commercial' },
    { key: 'region', header: 'Region' },
    { key: 'quantite_totale', header: 'Quantite', format: 'number', align: 'right' },
    { key: 'montant_ht', header: 'Montant HT', format: 'currency', align: 'right' },
    { key: 'montant_ttc', header: 'Montant TTC', format: 'currency', align: 'right' },
    { key: 'marge_brute', header: 'Marge Brute', format: 'currency', align: 'right' },
    { key: 'taux_marge', header: 'Taux Marge %', format: 'percent', align: 'right' },
    { key: 'prix_unit_min', header: 'Prix Min', format: 'currency', align: 'right' },
    { key: 'prix_unit_max', header: 'Prix Max', format: 'currency', align: 'right' },
    { key: 'prix_unit_moyen', header: 'Prix Moyen', format: 'currency', align: 'right' },
    { key: 'nb_transactions', header: 'Nb Trans.', format: 'number', align: 'right' },
    { key: 'nb_factures', header: 'Nb Fact.', format: 'number', align: 'right' }
  ]

  const dtField = searchParams.get('dt_field')
  const dtValue = searchParams.get('dt_value')
  const dtSource = searchParams.get('dt_source')

  return (
    <div className="space-y-4">
      {/* Bandeau drill-through entrant */}
      {dtField && dtValue && (
        <div className="flex items-center gap-2 px-4 py-1.5 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800/30 rounded-lg text-xs text-blue-700 dark:text-blue-300">
          <ArrowRight className="w-3.5 h-3.5 flex-shrink-0" />
          <span>Filtré depuis <b>{dtSource || 'rapport source'}</b> — {dtField}: <b>{dtValue}</b></span>
          <button
            onClick={() => setFilters(prev => { const f = { ...prev }; delete f[dtField]; return f })}
            className="ml-auto flex items-center gap-1 px-2 py-0.5 rounded bg-blue-100 dark:bg-blue-800/30 hover:bg-blue-200 transition-colors"
          >
            <X className="w-3 h-3" /> Effacer
          </button>
        </div>
      )}
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Liste des Ventes Agregees - Annee 2025
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Agregation des ventes par dimensions avec statistiques de prix - Table: Chiffre_Affaires_Groupe_Bis
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Filtre Societe principal - toujours visible */}
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300 whitespace-nowrap">
              Societe:
            </label>
            <select
              value={filters.societe}
              onChange={(e) => setFilters({ ...filters, societe: e.target.value })}
              className="input min-w-[200px]"
            >
              <option value="">Toutes les societes</option>
              {filtresDisponibles.societes.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          {/* Recherche Designation */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={searchDesignation}
              onChange={(e) => setSearchDesignation(e.target.value)}
              placeholder="Rechercher designation..."
              className="input pl-9 pr-8 min-w-[200px]"
            />
            {searchDesignation && (
              <button
                onClick={() => setSearchDesignation('')}
                className="absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`btn ${showFilters ? 'btn-primary' : 'btn-secondary'} flex items-center gap-2`}
          >
            <Filter className="w-4 h-4" />
            Plus de filtres
          </button>

          <button
            onClick={() => loadData(pagination.page)}
            disabled={loading}
            className="btn btn-secondary flex items-center gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Actualiser
          </button>

          <button
            onClick={handleExport}
            disabled={exporting || loading}
            className="btn btn-primary flex items-center gap-2"
          >
            <Download className="w-4 h-4" />
            {exporting ? 'Export...' : 'Exporter CSV'}
          </button>
        </div>
      </div>

      {/* Indicateur de filtre actif */}
      {(filters.societe || searchDesignation || hasActiveColumnFilters) && (
        <div className="flex items-center gap-2 text-sm flex-wrap">
          <span className="text-gray-600 dark:text-gray-400">Filtres actifs:</span>
          {filters.societe && (
            <>
              <span className="px-2 py-1 bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 rounded-full font-medium">
                Societe: {filters.societe}
              </span>
              <button
                onClick={() => setFilters({ ...filters, societe: '' })}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                &times;
              </button>
            </>
          )}
          {searchDesignation && (
            <>
              <span className="px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full font-medium">
                Designation: "{searchDesignation}"
              </span>
              <button
                onClick={() => setSearchDesignation('')}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                &times;
              </button>
            </>
          )}
          {hasActiveColumnFilters && (
            <>
              <span className="px-2 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded-full font-medium">
                Filtres colonnes actifs ({sortedData.length} resultat{sortedData.length > 1 ? 's' : ''})
              </span>
              <button
                onClick={resetColumnFilters}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                title="Effacer les filtres de colonnes"
              >
                &times;
              </button>
            </>
          )}
        </div>
      )}

      {/* Panneau de filtres */}
      {showFilters && (
        <div className="card p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-900 dark:text-white">Filtres</h3>
            <button onClick={resetFilters} className="text-sm text-primary-600 hover:underline">
              Reinitialiser
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5 gap-4">
            {/* Societe */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Societe
              </label>
              <select
                value={filters.societe}
                onChange={(e) => setFilters({ ...filters, societe: e.target.value })}
                className="input w-full"
              >
                <option value="">Toutes les societes</option>
                {filtresDisponibles.societes.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>

            {/* Gamme (Catalogue 1) */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Gamme (Cat. 1)
              </label>
              <select
                value={filters.gamme}
                onChange={(e) => setFilters({ ...filters, gamme: e.target.value })}
                className="input w-full"
              >
                <option value="">Toutes les gammes</option>
                {filtresDisponibles.gammes.map((g) => (
                  <option key={g} value={g}>{g}</option>
                ))}
              </select>
            </div>

            {/* Catalogue 2 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Catalogue 2
              </label>
              <select
                value={filters.catalogue2}
                onChange={(e) => setFilters({ ...filters, catalogue2: e.target.value })}
                className="input w-full"
              >
                <option value="">Tous</option>
                {filtresDisponibles.catalogue2.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>

            {/* Catalogue 3 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Catalogue 3
              </label>
              <select
                value={filters.catalogue3}
                onChange={(e) => setFilters({ ...filters, catalogue3: e.target.value })}
                className="input w-full"
              >
                <option value="">Tous</option>
                {filtresDisponibles.catalogue3.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>

            {/* Commercial */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Commercial
              </label>
              <select
                value={filters.commercial}
                onChange={(e) => setFilters({ ...filters, commercial: e.target.value })}
                className="input w-full"
              >
                <option value="">Tous les commerciaux</option>
                {filtresDisponibles.commerciaux.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>

            {/* Canal */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Canal
              </label>
              <select
                value={filters.canal}
                onChange={(e) => setFilters({ ...filters, canal: e.target.value })}
                className="input w-full"
              >
                <option value="">Tous les canaux</option>
                {filtresDisponibles.canaux.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>

            {/* Zone */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Zone (Souche)
              </label>
              <select
                value={filters.zone}
                onChange={(e) => setFilters({ ...filters, zone: e.target.value })}
                className="input w-full"
              >
                <option value="">Toutes les zones</option>
                {filtresDisponibles.zones.map((z) => (
                  <option key={z} value={z}>{z}</option>
                ))}
              </select>
            </div>

            {/* Region */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Region
              </label>
              <select
                value={filters.region}
                onChange={(e) => setFilters({ ...filters, region: e.target.value })}
                className="input w-full"
              >
                <option value="">Toutes les regions</option>
                {filtresDisponibles.regions.map((r) => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </select>
            </div>

            {/* Ville */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Ville
              </label>
              <select
                value={filters.ville}
                onChange={(e) => setFilters({ ...filters, ville: e.target.value })}
                className="input w-full"
              >
                <option value="">Toutes les villes</option>
                {filtresDisponibles.villes.map((v) => (
                  <option key={v} value={v}>{v}</option>
                ))}
              </select>
            </div>

            {/* Groupe Client */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Groupe Client
              </label>
              <select
                value={filters.groupe}
                onChange={(e) => setFilters({ ...filters, groupe: e.target.value })}
                className="input w-full"
              >
                <option value="">Tous les groupes</option>
                {filtresDisponibles.groupes.map((g) => (
                  <option key={g} value={g}>{g}</option>
                ))}
              </select>
            </div>
          </div>
        </div>
      )}

      {/* KPIs Totaux */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="card p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
          <div className="text-sm text-blue-600 dark:text-blue-400">Quantite Totale</div>
          <div className="text-xl font-bold text-blue-700 dark:text-blue-300">
            {formatCurrency(totaux.quantite_totale).split(',')[0]}
          </div>
        </div>
        <div className="card p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
          <div className="text-sm text-green-600 dark:text-green-400">Montant HT</div>
          <div className="text-xl font-bold text-green-700 dark:text-green-300">
            {formatMillions(totaux.montant_ht)}
          </div>
        </div>
        <div className="card p-4 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg">
          <div className="text-sm text-purple-600 dark:text-purple-400">Montant TTC</div>
          <div className="text-xl font-bold text-purple-700 dark:text-purple-300">
            {formatMillions(totaux.montant_ttc)}
          </div>
        </div>
        <div className="card p-4 bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg">
          <div className="text-sm text-orange-600 dark:text-orange-400">Marge Brute</div>
          <div className="text-xl font-bold text-orange-700 dark:text-orange-300">
            {formatMillions(totaux.marge_brute)}
          </div>
        </div>
        <div className="card p-4 bg-teal-50 dark:bg-teal-900/20 border border-teal-200 dark:border-teal-800 rounded-lg">
          <div className="text-sm text-teal-600 dark:text-teal-400">Taux Marge Global</div>
          <div className="text-xl font-bold text-teal-700 dark:text-teal-300">
            {totaux.taux_marge_global?.toFixed(2) || '0.00'} %
          </div>
        </div>
      </div>

      {/* Tableau de donnees avec header et footer fixes */}
      {loading ? (
        <Loading />
      ) : (
        <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden" style={{ height: 'calc(100vh - 420px)', minHeight: '400px' }}>
          <div className="h-full overflow-auto">
            <table className="w-full border-collapse" style={{ tableLayout: 'auto' }}>
              {/* Header fixe avec sticky */}
              <thead className="bg-gray-100 dark:bg-gray-800 sticky top-0 z-10">
                <tr>
                  {columns.map((col) => (
                    <th
                      key={col.key}
                      onClick={() => handleSort(col.key)}
                      className={`px-3 py-2 text-xs font-semibold text-gray-600 dark:text-gray-300 uppercase tracking-wider border-b border-gray-200 dark:border-gray-700 bg-gray-100 dark:bg-gray-800 cursor-pointer hover:bg-gray-200 dark:hover:bg-gray-700 select-none transition-colors ${col.align === 'right' ? 'text-right' : 'text-left'}`}
                    >
                      <div className={`flex items-center gap-1 ${col.align === 'right' ? 'justify-end' : ''}`}>
                        <span>{col.header}</span>
                        {getSortIcon(col.key)}
                      </div>
                    </th>
                  ))}
                </tr>
                {/* Ligne de filtres par colonne */}
                <tr className="bg-gray-50 dark:bg-gray-700/50">
                  {columns.map((col) => (
                    <th key={`filter-${col.key}`} className="px-1 py-1 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/50">
                      {columnFilters.hasOwnProperty(col.key) ? (
                        <input
                          type="text"
                          value={columnFilters[col.key] || ''}
                          onChange={(e) => setColumnFilters(prev => ({ ...prev, [col.key]: e.target.value }))}
                          placeholder="Filtrer..."
                          className="w-full px-2 py-1 text-xs border border-primary-300 dark:border-primary-600 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500"
                          onClick={(e) => e.stopPropagation()}
                        />
                      ) : (
                        <span className="text-xs text-gray-400">-</span>
                      )}
                    </th>
                  ))}
                </tr>
              </thead>

              {/* Body */}
              <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
                {sortedData.map((row, idx) => (
                  <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                    {columns.map((col) => (
                      <td
                        key={col.key}
                        className={`px-3 py-2 text-sm text-gray-900 dark:text-gray-100 whitespace-nowrap ${col.align === 'right' ? 'text-right' : 'text-left'}`}
                      >
                        {col.format === 'currency' ? formatCurrency(row[col.key]) :
                         col.format === 'number' ? (row[col.key] || 0).toLocaleString('fr-FR') :
                         col.format === 'percent' ? `${(row[col.key] || 0).toFixed(2)} %` :
                         row[col.key] || '-'}
                      </td>
                    ))}
                  </tr>
                ))}
                {sortedData.length === 0 && (
                  <tr>
                    <td colSpan={columns.length} className="px-3 py-8 text-center text-gray-500 dark:text-gray-400">
                      Aucune donnee trouvee
                    </td>
                  </tr>
                )}
              </tbody>

              {/* Footer fixe avec sticky */}
              <tfoot className="bg-gray-100 dark:bg-gray-800 sticky bottom-0 z-10">
                <tr className="font-semibold border-t-2 border-primary-300 dark:border-primary-600">
                  {columns.map((col, idx) => (
                    <td
                      key={col.key}
                      className={`px-3 py-3 text-sm text-gray-900 dark:text-gray-100 bg-gray-100 dark:bg-gray-800 whitespace-nowrap ${col.align === 'right' ? 'text-right' : 'text-left'}`}
                    >
                      {idx === 0 ? `Total (${pagination.total_records.toLocaleString('fr-FR')} lignes)` :
                       col.key === 'quantite_totale' ? (totaux.quantite_totale || 0).toLocaleString('fr-FR') :
                       col.key === 'montant_ht' ? formatCurrency(totaux.montant_ht) :
                       col.key === 'montant_ttc' ? formatCurrency(totaux.montant_ttc) :
                       col.key === 'marge_brute' ? formatCurrency(totaux.marge_brute) :
                       col.key === 'taux_marge' ? `${(totaux.taux_marge_global || 0).toFixed(2)} %` :
                       ''}
                    </td>
                  ))}
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      )}

      {/* Pagination */}
      {!loading && pagination.total_pages > 1 && (
        <div className="flex items-center justify-between px-4 py-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Page {pagination.page} sur {pagination.total_pages}
            {' | '}
            {((pagination.page - 1) * pagination.page_size + 1).toLocaleString('fr-FR')}
            {' - '}
            {Math.min(pagination.page * pagination.page_size, pagination.total_records).toLocaleString('fr-FR')}
            {' sur '}
            {pagination.total_records.toLocaleString('fr-FR')}
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => handlePageChange(1)}
              disabled={pagination.page === 1}
              className="btn btn-secondary px-3 py-1 disabled:opacity-50"
            >
              Debut
            </button>
            <button
              onClick={() => handlePageChange(pagination.page - 1)}
              disabled={pagination.page === 1}
              className="btn btn-secondary p-1 disabled:opacity-50"
            >
              <ChevronLeft className="w-5 h-5" style={{ color: 'var(--color-primary-500)' }} />
            </button>

            {/* Numeros de page */}
            <div className="flex items-center gap-1">
              {[...Array(Math.min(5, pagination.total_pages))].map((_, idx) => {
                let pageNum
                if (pagination.total_pages <= 5) {
                  pageNum = idx + 1
                } else if (pagination.page <= 3) {
                  pageNum = idx + 1
                } else if (pagination.page >= pagination.total_pages - 2) {
                  pageNum = pagination.total_pages - 4 + idx
                } else {
                  pageNum = pagination.page - 2 + idx
                }

                return (
                  <button
                    key={pageNum}
                    onClick={() => handlePageChange(pageNum)}
                    className={`px-3 py-1 rounded ${
                      pagination.page === pageNum
                        ? 'bg-primary-600 text-white'
                        : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                    }`}
                  >
                    {pageNum}
                  </button>
                )
              })}
            </div>

            <button
              onClick={() => handlePageChange(pagination.page + 1)}
              disabled={pagination.page === pagination.total_pages}
              className="btn btn-secondary p-1 disabled:opacity-50"
            >
              <ChevronRight className="w-5 h-5" style={{ color: 'var(--color-primary-500)' }} />
            </button>
            <button
              onClick={() => handlePageChange(pagination.total_pages)}
              disabled={pagination.page === pagination.total_pages}
              className="btn btn-secondary px-3 py-1 disabled:opacity-50"
            >
              Fin
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
