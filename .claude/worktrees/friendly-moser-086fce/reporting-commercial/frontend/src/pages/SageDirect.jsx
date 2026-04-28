import { useState, useEffect, useCallback } from 'react'
import {
  Database, Search, RefreshCw, ChevronDown, ChevronRight,
  FileText, Layers, X, AlertCircle, Info
} from 'lucide-react'
import api from '../services/api'
import { useDWH } from '../context/DWHContext'

// ─── Constantes ───────────────────────────────────────────────────────────────

const TYPE_DOC_OPTIONS = [
  { value: '',  label: 'Tous (Factures + Avoirs)' },
  { value: '6', label: 'Factures (DO_Type 6)' },
  { value: '7', label: 'Avoirs (DO_Type 7)' },
]

const STATUT_LABELS = { 0: 'Brouillon', 1: 'Validé', 2: 'Transféré' }

// ─── Composant principal ───────────────────────────────────────────────────────

export default function SageDirect() {
  const { currentDWH } = useDWH()
  const dwhCode = currentDWH?.code

  // Sources Sage disponibles
  const [societes, setSocietes] = useState([])
  const [loadingSocietes, setLoadingSocietes] = useState(true)
  const [errorSocietes, setErrorSocietes] = useState(null)

  // Filtres
  const [codeSociete, setCodeSociete] = useState('')
  const [dateDebut, setDateDebut]     = useState('')
  const [dateFin, setDateFin]         = useState('')
  const [typeDoc, setTypeDoc]         = useState('')
  const [codeTiers, setCodeTiers]     = useState('')
  const [limit, setLimit]             = useState(200)

  // Résultats entêtes
  const [entetes, setEntetes]       = useState([])
  const [loadingEntetes, setLoadingEntetes] = useState(false)
  const [errorEntetes, setErrorEntetes]     = useState(null)
  const [searched, setSearched]     = useState(false)

  // Lignes (détail d'une pièce)
  const [expandedPiece, setExpandedPiece] = useState(null)
  const [lignes, setLignes]               = useState({})    // { numero_piece: [...] }
  const [loadingLigne, setLoadingLigne]   = useState(null)  // numero_piece en cours

  // ─── Chargement des sociétés disponibles ────────────────────────────────────
  useEffect(() => {
    if (!dwhCode) return
    const fetchSocietes = async () => {
      setLoadingSocietes(true)
      setErrorSocietes(null)
      try {
        const res = await api.get('/sage-direct/societes', {
          headers: { 'X-DWH-Code': dwhCode }
        })
        if (res.data.success) {
          setSocietes(res.data.data)
          if (res.data.data.length > 0) {
            setCodeSociete(res.data.data[0].code_societe)
          }
        }
      } catch (e) {
        setErrorSocietes(e.response?.data?.detail || 'Erreur chargement sources Sage')
      } finally {
        setLoadingSocietes(false)
      }
    }
    fetchSocietes()
  }, [dwhCode])

  // ─── Recherche entêtes ──────────────────────────────────────────────────────
  const handleSearch = useCallback(async () => {
    if (!codeSociete) return
    setLoadingEntetes(true)
    setErrorEntetes(null)
    setEntetes([])
    setExpandedPiece(null)
    setLignes({})
    setSearched(true)

    try {
      const res = await api.post('/sage-direct/entetes', {
        code_societe: codeSociete,
        date_debut:   dateDebut   || null,
        date_fin:     dateFin     || null,
        type_doc:     typeDoc     ? parseInt(typeDoc) : null,
        code_tiers:   codeTiers   || null,
        limit,
      }, { headers: { 'X-DWH-Code': dwhCode } })
      if (res.data.success) {
        setEntetes(res.data.data)
      }
    } catch (e) {
      setErrorEntetes(e.response?.data?.detail || 'Erreur lors de la requête Sage')
    } finally {
      setLoadingEntetes(false)
    }
  }, [codeSociete, dateDebut, dateFin, typeDoc, codeTiers, limit])

  // ─── Chargement lignes d'une pièce ──────────────────────────────────────────
  const handleToggleLignes = useCallback(async (numeroPiece) => {
    if (expandedPiece === numeroPiece) {
      setExpandedPiece(null)
      return
    }
    setExpandedPiece(numeroPiece)
    if (lignes[numeroPiece]) return // déjà chargé

    setLoadingLigne(numeroPiece)
    try {
      const res = await api.post('/sage-direct/lignes', {
        code_societe:  codeSociete,
        numero_piece:  numeroPiece,
      }, { headers: { 'X-DWH-Code': dwhCode } })
      if (res.data.success) {
        setLignes(prev => ({ ...prev, [numeroPiece]: res.data.data }))
      }
    } catch (e) {
      setLignes(prev => ({ ...prev, [numeroPiece]: [] }))
    } finally {
      setLoadingLigne(null)
    }
  }, [expandedPiece, lignes, codeSociete])

  // ─── Helpers UI ─────────────────────────────────────────────────────────────
  const selectedSociete = societes.find(s => s.code_societe === codeSociete)

  const formatMontant = (val) =>
    val == null ? '-' : Number(val).toLocaleString('fr-FR', { minimumFractionDigits: 2 })

  const typeDocLabel = (type) =>
    type === 6 ? 'Facture' : type === 7 ? 'Avoir' : `Type ${type}`

  // ─── Rendu ──────────────────────────────────────────────────────────────────
  return (
    <div className="p-6 space-y-6">

      {/* ── En-tête ── */}
      <div className="flex items-center gap-3">
        <div className="p-2 bg-orange-100 dark:bg-orange-900/30 rounded-lg">
          <Database className="h-6 w-6 text-orange-600 dark:text-orange-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Accès Direct Sage
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Lecture directe sur la base Sage — sans synchronisation ETL
          </p>
        </div>
        {/* Badge info */}
        <span className="ml-auto flex items-center gap-1.5 text-xs bg-blue-50 dark:bg-blue-900/30
                         text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-700
                         px-2.5 py-1 rounded-full">
          <Info className="h-3.5 w-3.5" />
          Lecture seule · Données live Sage
        </span>
      </div>

      {/* ── Erreur sources ── */}
      {errorSocietes && (
        <div className="flex items-center gap-2 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200
                        dark:border-red-700 rounded-lg text-red-700 dark:text-red-300 text-sm">
          <AlertCircle className="h-4 w-4 flex-shrink-0" />
          {errorSocietes}
        </div>
      )}

      {/* ── Panneau de filtres ── */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 shadow-sm">

        {/* Ligne 1 : Société + infos serveur */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div>
            <label className="block text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1 uppercase tracking-wide">
              Société Sage
            </label>
            {loadingSocietes ? (
              <div className="h-9 bg-gray-100 dark:bg-gray-700 rounded-lg animate-pulse" />
            ) : (
              <select
                value={codeSociete}
                onChange={e => setCodeSociete(e.target.value)}
                className="w-full h-9 px-3 rounded-lg border border-gray-300 dark:border-gray-600
                           bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm
                           focus:outline-none focus:ring-2 focus:ring-orange-400"
              >
                {societes.length === 0 && (
                  <option value="">Aucune source disponible</option>
                )}
                {societes.map(s => (
                  <option key={s.code_societe} value={s.code_societe}>
                    {s.nom_societe} ({s.code_societe})
                  </option>
                ))}
              </select>
            )}
          </div>

          {selectedSociete && (
            <div className="md:col-span-2 flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400
                            bg-gray-50 dark:bg-gray-700/50 rounded-lg px-3 py-2 border border-gray-200 dark:border-gray-600">
              <Database className="h-3.5 w-3.5 flex-shrink-0" />
              <span>
                <span className="font-medium">{selectedSociete.serveur_sage}</span>
                {' › '}<span className="font-medium">{selectedSociete.base_sage}</span>
              </span>
              {selectedSociete.etl_enabled && (
                <span className="ml-auto bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300
                                 px-2 py-0.5 rounded-full text-xs">ETL actif</span>
              )}
            </div>
          )}
        </div>

        {/* Ligne 2 : Filtres dates + type + tiers + limit */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
              Date début
            </label>
            <input
              type="date"
              value={dateDebut}
              onChange={e => setDateDebut(e.target.value)}
              className="w-full h-9 px-3 rounded-lg border border-gray-300 dark:border-gray-600
                         bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm
                         focus:outline-none focus:ring-2 focus:ring-orange-400"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
              Date fin
            </label>
            <input
              type="date"
              value={dateFin}
              onChange={e => setDateFin(e.target.value)}
              className="w-full h-9 px-3 rounded-lg border border-gray-300 dark:border-gray-600
                         bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm
                         focus:outline-none focus:ring-2 focus:ring-orange-400"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
              Type document
            </label>
            <select
              value={typeDoc}
              onChange={e => setTypeDoc(e.target.value)}
              className="w-full h-9 px-3 rounded-lg border border-gray-300 dark:border-gray-600
                         bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm
                         focus:outline-none focus:ring-2 focus:ring-orange-400"
            >
              {TYPE_DOC_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
              Code tiers
            </label>
            <div className="relative">
              <input
                type="text"
                value={codeTiers}
                onChange={e => setCodeTiers(e.target.value)}
                placeholder="Rechercher..."
                className="w-full h-9 pl-3 pr-8 rounded-lg border border-gray-300 dark:border-gray-600
                           bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm
                           focus:outline-none focus:ring-2 focus:ring-orange-400"
              />
              {codeTiers && (
                <button
                  onClick={() => setCodeTiers('')}
                  className="absolute right-2 top-2.5 text-gray-400 hover:text-gray-600"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
              Limite lignes
            </label>
            <select
              value={limit}
              onChange={e => setLimit(parseInt(e.target.value))}
              className="w-full h-9 px-3 rounded-lg border border-gray-300 dark:border-gray-600
                         bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm
                         focus:outline-none focus:ring-2 focus:ring-orange-400"
            >
              {[50, 100, 200, 500, 1000].map(n => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Bouton Rechercher */}
        <div className="flex items-center gap-3">
          <button
            onClick={handleSearch}
            disabled={!codeSociete || loadingEntetes}
            className="flex items-center gap-2 px-5 py-2 bg-orange-500 hover:bg-orange-600
                       disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium
                       rounded-lg transition-colors text-sm"
          >
            {loadingEntetes
              ? <RefreshCw className="h-4 w-4 animate-spin" />
              : <Search className="h-4 w-4" />
            }
            {loadingEntetes ? 'Chargement...' : 'Rechercher dans Sage'}
          </button>

          {searched && !loadingEntetes && (
            <span className="text-sm text-gray-500 dark:text-gray-400">
              {entetes.length} document{entetes.length > 1 ? 's' : ''} trouvé{entetes.length > 1 ? 's' : ''}
            </span>
          )}
        </div>
      </div>

      {/* ── Erreur entêtes ── */}
      {errorEntetes && (
        <div className="flex items-center gap-2 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200
                        dark:border-red-700 rounded-lg text-red-700 dark:text-red-300 text-sm">
          <AlertCircle className="h-4 w-4 flex-shrink-0" />
          {errorEntetes}
        </div>
      )}

      {/* ── Tableau des entêtes ── */}
      {searched && !loadingEntetes && !errorEntetes && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">

          {entetes.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-gray-400 dark:text-gray-500">
              <FileText className="h-12 w-12 mb-3 opacity-40" />
              <p className="text-sm">Aucun document trouvé pour ces critères</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 dark:bg-gray-700/60 text-xs font-semibold
                                 text-gray-600 dark:text-gray-300 uppercase tracking-wide">
                    <th className="px-3 py-3 w-8"></th>
                    <th className="px-4 py-3 text-left">N° Pièce</th>
                    <th className="px-4 py-3 text-left">Type</th>
                    <th className="px-4 py-3 text-left">Date</th>
                    <th className="px-4 py-3 text-left">Code Client</th>
                    <th className="px-4 py-3 text-left">Référence</th>
                    <th className="px-4 py-3 text-right">Total HT</th>
                    <th className="px-4 py-3 text-right">Total TTC</th>
                    <th className="px-4 py-3 text-center">Statut</th>
                    <th className="px-4 py-3 text-center">Lignes</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                  {entetes.map((row) => {
                    const isExpanded = expandedPiece === row.Numero_Piece
                    const rowLignes  = lignes[row.Numero_Piece]
                    const isLoading  = loadingLigne === row.Numero_Piece
                    const isAvoir    = row.Type_Doc === 7

                    return (
                      <>
                        {/* Ligne entête */}
                        <tr
                          key={row.Numero_Piece}
                          className={`cursor-pointer transition-colors
                            ${isExpanded
                              ? 'bg-orange-50 dark:bg-orange-900/10'
                              : 'hover:bg-gray-50 dark:hover:bg-gray-700/40'
                            }`}
                          onClick={() => handleToggleLignes(row.Numero_Piece)}
                        >
                          {/* Chevron expand */}
                          <td className="px-3 py-3 text-gray-400">
                            {isLoading
                              ? <RefreshCw className="h-4 w-4 animate-spin" />
                              : isExpanded
                                ? <ChevronDown className="h-4 w-4 text-orange-500" />
                                : <ChevronRight className="h-4 w-4" />
                            }
                          </td>
                          <td className="px-4 py-3 font-mono font-medium text-gray-900 dark:text-white">
                            {row.Numero_Piece}
                          </td>
                          <td className="px-4 py-3">
                            <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium
                              ${isAvoir
                                ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300'
                                : 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                              }`}>
                              {typeDocLabel(row.Type_Doc)}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-gray-700 dark:text-gray-300">
                            {row.Date_Doc ? row.Date_Doc.slice(0, 10) : '-'}
                          </td>
                          <td className="px-4 py-3 font-mono text-xs text-gray-700 dark:text-gray-300">
                            {row.Code_Client || '-'}
                          </td>
                          <td className="px-4 py-3 text-gray-500 dark:text-gray-400 text-xs">
                            {row.Reference || '-'}
                          </td>
                          <td className={`px-4 py-3 text-right font-medium tabular-nums
                            ${isAvoir ? 'text-red-600 dark:text-red-400' : 'text-gray-900 dark:text-white'}`}>
                            {formatMontant(row.Total_HT)}
                          </td>
                          <td className={`px-4 py-3 text-right tabular-nums
                            ${isAvoir ? 'text-red-600 dark:text-red-400' : 'text-gray-700 dark:text-gray-300'}`}>
                            {formatMontant(row.Total_TTC)}
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span className="text-xs text-gray-500 dark:text-gray-400">
                              {STATUT_LABELS[row.Statut] ?? row.Statut}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-center text-xs text-gray-400 dark:text-gray-500">
                            {row.Nb_Lignes ?? '—'}
                          </td>
                        </tr>

                        {/* Lignes détail (expandable) */}
                        {isExpanded && (
                          <tr key={`${row.Numero_Piece}-lignes`}>
                            <td colSpan={10} className="p-0">
                              <div className="bg-orange-50/60 dark:bg-orange-900/5 border-t border-b
                                              border-orange-100 dark:border-orange-800/30 px-8 py-3">
                                {isLoading || !rowLignes ? (
                                  <div className="flex items-center gap-2 text-sm text-gray-400 py-2">
                                    <RefreshCw className="h-4 w-4 animate-spin" />
                                    Chargement des lignes...
                                  </div>
                                ) : rowLignes.length === 0 ? (
                                  <p className="text-sm text-gray-400 py-2">Aucune ligne trouvée.</p>
                                ) : (
                                  <table className="w-full text-xs">
                                    <thead>
                                      <tr className="text-gray-500 dark:text-gray-400 border-b border-orange-100 dark:border-orange-800/30">
                                        <th className="pb-2 text-left font-semibold">#</th>
                                        <th className="pb-2 text-left font-semibold">Réf. Article</th>
                                        <th className="pb-2 text-left font-semibold">Désignation</th>
                                        <th className="pb-2 text-right font-semibold">Qté</th>
                                        <th className="pb-2 text-right font-semibold">PU HT</th>
                                        <th className="pb-2 text-right font-semibold">Remise</th>
                                        <th className="pb-2 text-right font-semibold">Montant HT</th>
                                        <th className="pb-2 text-right font-semibold">Montant TTC</th>
                                        <th className="pb-2 text-left font-semibold">Unité</th>
                                        <th className="pb-2 text-left font-semibold">Famille</th>
                                      </tr>
                                    </thead>
                                    <tbody className="divide-y divide-orange-100/60 dark:divide-orange-800/20">
                                      {rowLignes.map((lg) => (
                                        <tr key={lg.Num_Ligne}
                                            className="hover:bg-orange-100/30 dark:hover:bg-orange-900/10">
                                          <td className="py-1.5 pr-3 text-gray-400">{lg.Num_Ligne}</td>
                                          <td className="py-1.5 pr-3 font-mono text-gray-700 dark:text-gray-300">{lg.Code_Article || '-'}</td>
                                          <td className="py-1.5 pr-3 text-gray-800 dark:text-gray-200 max-w-xs truncate">{lg.Designation || '-'}</td>
                                          <td className="py-1.5 pr-3 text-right tabular-nums text-gray-700 dark:text-gray-300">{lg.Quantite}</td>
                                          <td className="py-1.5 pr-3 text-right tabular-nums text-gray-700 dark:text-gray-300">{formatMontant(lg.Prix_Unitaire)}</td>
                                          <td className="py-1.5 pr-3 text-right tabular-nums text-gray-500">
                                            {lg.Remise ? `${lg.Remise}%` : '-'}
                                          </td>
                                          <td className="py-1.5 pr-3 text-right tabular-nums font-medium text-gray-900 dark:text-white">{formatMontant(lg.Montant_HT)}</td>
                                          <td className="py-1.5 pr-3 text-right tabular-nums text-gray-700 dark:text-gray-300">{formatMontant(lg.Montant_TTC)}</td>
                                          <td className="py-1.5 pr-3 text-gray-500">{lg.Unite || '-'}</td>
                                          <td className="py-1.5 text-gray-500">{lg.Famille || '-'}</td>
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                )}
                              </div>
                            </td>
                          </tr>
                        )}
                      </>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ── Etat initial (avant recherche) ── */}
      {!searched && !loadingSocietes && (
        <div className="flex flex-col items-center justify-center py-20 text-gray-400 dark:text-gray-600">
          <Layers className="h-14 w-14 mb-4 opacity-30" />
          <p className="text-sm font-medium">Sélectionnez une société et lancez la recherche</p>
          <p className="text-xs mt-1 opacity-70">Les données sont lues directement depuis la base Sage</p>
        </div>
      )}
    </div>
  )
}
