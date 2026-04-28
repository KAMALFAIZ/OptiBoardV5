import { useState, useEffect, useRef } from 'react'
import { Calendar, Building2, X } from 'lucide-react'
import { getSocietes } from '../../services/api'

export default function Filters({
  onFilterChange,
  showPeriod = true,
  showSociete = true,
  showGamme = false,
  showCommercial = false,
  showCanal = false,
  gammes = [],
  commerciaux = [],
  canaux = []
}) {
  const [filters, setFilters] = useState({
    periode: 'annee_courante',
    date_debut: '',
    date_fin: '',
    societe: '',
    gamme: '',
    commercial: '',
    canal: ''
  })

  const [showCustomDates, setShowCustomDates] = useState(false)
  const [societes, setSocietes] = useState([])
  const isFirstRender = useRef(true)

  useEffect(() => {
    if (showSociete) {
      getSocietes().then(res => {
        if (res.data.success) {
          setSocietes(res.data.data || [])
        }
      }).catch(err => console.error('Erreur chargement societes:', err))
    }
  }, [showSociete])

  // Envoyer les filtres initiaux au premier rendu
  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false
      onFilterChange && onFilterChange(filters)
    }
  }, [])

  const periodes = [
    { value: 'annee_courante', label: 'Annee 2025' },
    { value: 'annee_precedente', label: 'Annee 2024' },
    { value: 'trimestre_courant', label: 'Trimestre en cours' },
    { value: 'mois_courant', label: 'Mois en cours' },
    { value: '12_derniers_mois', label: '12 derniers mois' },
    { value: 'custom', label: 'Personnalise' }
  ]

  const handleChange = (key, value) => {
    const newFilters = { ...filters, [key]: value }

    if (key === 'periode' && value === 'custom') {
      setShowCustomDates(true)
      // Ne pas déclencher onFilterChange tant que les dates ne sont pas renseignées
      setFilters(newFilters)
      return
    } else if (key === 'periode') {
      setShowCustomDates(false)
      newFilters.date_debut = ''
      newFilters.date_fin = ''
    }

    // Pour les dates personnalisées, attendre que les deux soient renseignées
    if (showCustomDates && (key === 'date_debut' || key === 'date_fin')) {
      setFilters(newFilters)
      if (newFilters.date_debut && newFilters.date_fin) {
        onFilterChange && onFilterChange(newFilters)
      }
      return
    }

    setFilters(newFilters)
    onFilterChange && onFilterChange(newFilters)
  }

  const clearFilters = () => {
    const defaultFilters = {
      periode: 'annee_courante',
      date_debut: '',
      date_fin: '',
      societe: '',
      gamme: '',
      commercial: '',
      canal: ''
    }
    setFilters(defaultFilters)
    setShowCustomDates(false)
    onFilterChange && onFilterChange(defaultFilters)
  }

  const hasActiveFilters = filters.gamme || filters.commercial || filters.canal || filters.societe

  return (
    <div className="card p-2 mb-4">
      <div className="flex flex-wrap items-center gap-2">
        {/* Periode */}
        {showPeriod && (
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-gray-500" />
            <select
              value={filters.periode}
              onChange={(e) => handleChange('periode', e.target.value)}
              className="input w-auto"
            >
              {periodes.map((p) => (
                <option key={p.value} value={p.value}>{p.label}</option>
              ))}
            </select>
          </div>
        )}

        {/* Custom dates */}
        {showCustomDates && (
          <>
            <input
              type="date"
              value={filters.date_debut}
              onChange={(e) => handleChange('date_debut', e.target.value)}
              className="input w-auto"
            />
            <span className="text-gray-500 text-sm">au</span>
            <input
              type="date"
              value={filters.date_fin}
              onChange={(e) => handleChange('date_fin', e.target.value)}
              className="input w-auto"
            />
          </>
        )}

        {/* Societe filter */}
        {showSociete && societes.length > 0 && (
          <div className="flex items-center gap-1">
            <Building2 className="w-4 h-4 text-gray-500" />
            <select
              value={filters.societe}
              onChange={(e) => handleChange('societe', e.target.value)}
              className="input w-auto"
            >
              <option value="">Toutes societes</option>
              {societes.map((s, i) => (
                <option key={i} value={s}>{s}</option>
              ))}
            </select>
          </div>
        )}

        {/* Gamme filter */}
        {showGamme && gammes.length > 0 && (
          <select
            value={filters.gamme}
            onChange={(e) => handleChange('gamme', e.target.value)}
            className="input w-auto"
          >
            <option value="">Toutes les gammes</option>
            {gammes.map((g, i) => (
              <option key={i} value={g}>{g}</option>
            ))}
          </select>
        )}

        {/* Commercial filter */}
        {showCommercial && commerciaux.length > 0 && (
          <select
            value={filters.commercial}
            onChange={(e) => handleChange('commercial', e.target.value)}
            className="input w-auto"
          >
            <option value="">Tous les commerciaux</option>
            {commerciaux.map((c, i) => (
              <option key={i} value={c}>{c}</option>
            ))}
          </select>
        )}

        {/* Canal filter */}
        {showCanal && canaux.length > 0 && (
          <select
            value={filters.canal}
            onChange={(e) => handleChange('canal', e.target.value)}
            className="input w-auto"
          >
            <option value="">Tous les canaux</option>
            {canaux.map((c, i) => (
              <option key={i} value={c}>{c}</option>
            ))}
          </select>
        )}

        {/* Clear filters */}
        {hasActiveFilters && (
          <button
            onClick={clearFilters}
            className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
          >
            <X className="w-4 h-4" />
            Effacer les filtres
          </button>
        )}
      </div>
    </div>
  )
}
