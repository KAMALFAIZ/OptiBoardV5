import { useState, useMemo } from 'react'
import {
  Search, Filter, Download, Plus, Pencil, Trash2, X, ChevronDown,
  AlertCircle, Clock, CheckCircle, Package
} from 'lucide-react'

const STATUTS = ['Planifié', 'Ferme', 'Clôturé', 'En cours']
const ORIGINES = ['MRP', 'Manuel', 'Import']
const SITES = ['–', 'SITE1', 'SITE2']

const initialData = [
  {
    id: 3,
    num_of: 'OF-2026-00003',
    date: '08/05/2026',
    article: 'B10',
    designation: 'B10 V',
    quantite: 10000,
    unite: 'PC',
    realisation: 0,
    priorite: 5,
    origine: 'MRP',
    site: '–',
    debut: '04/01/2026',
    fin: '04/01/2026',
    comp_op: '8/11',
    jalonnement: 'Non jalonné',
    allocation: 'Aucune',
    avancement: 'Non démarré',
    statut: 'Planifié',
  },
  {
    id: 2,
    num_of: 'OF-2026-00002',
    date: '08/05/2026',
    article: 'B10',
    designation: 'B10 V',
    quantite: 55555,
    unite: 'PC',
    realisation: 0,
    priorite: 5,
    origine: 'MRP',
    site: '–',
    debut: '04/01/2026',
    fin: '04/01/2026',
    comp_op: '8/11',
    jalonnement: 'Non jalonné',
    allocation: 'Aucune',
    avancement: 'Non démarré',
    statut: 'Planifié',
  },
  {
    id: 1,
    num_of: 'OF-2026-00001',
    date: '08/05/2026',
    article: 'B10',
    designation: 'B10 V',
    quantite: 15444,
    unite: 'PC',
    realisation: 65,
    priorite: 5,
    origine: 'MRP',
    site: '–',
    debut: '28/12/2025',
    fin: '28/12/2025',
    comp_op: '8/11',
    jalonnement: 'Non jalonné',
    allocation: 'Aucune',
    avancement: 'En cours',
    statut: 'Ferme',
  },
]

const emptyForm = {
  num_of: '',
  date: '',
  article: '',
  designation: '',
  quantite: '',
  unite: 'PC',
  realisation: 0,
  priorite: 5,
  origine: 'MRP',
  site: '–',
  debut: '',
  fin: '',
  comp_op: '',
  jalonnement: 'Non jalonné',
  allocation: 'Aucune',
  avancement: 'Non démarré',
  statut: 'Planifié',
}

function StatutBadge({ statut }) {
  const map = {
    Planifié: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
    Ferme: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
    Clôturé: 'bg-gray-200 text-gray-600 dark:bg-gray-700 dark:text-gray-400',
    'En cours': 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
  }
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${map[statut] || 'bg-gray-100 text-gray-600'}`}>
      {statut}
    </span>
  )
}

function ProgressBar({ value }) {
  const color = value === 0 ? 'bg-gray-200 dark:bg-gray-600' : value >= 100 ? 'bg-emerald-500' : 'bg-teal-500'
  return (
    <div className="flex items-center gap-2">
      <div className="w-20 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${Math.min(value, 100)}%` }} />
      </div>
      <span className="text-xs text-gray-500 dark:text-gray-400 w-7">{value}%</span>
    </div>
  )
}

function isLate(finStr) {
  if (!finStr) return false
  const [d, m, y] = finStr.split('/')
  const fin = new Date(+y, +m - 1, +d)
  return fin < new Date()
}

export default function OrdreFabrication() {
  const [ofs, setOfs] = useState(initialData)
  const [search, setSearch] = useState('')
  const [activeTab, setActiveTab] = useState('Tous')
  const [editOf, setEditOf] = useState(null)   // null = fermé, {} = nouveau, {...} = édition
  const [deleteOf, setDeleteOf] = useState(null)
  const [form, setForm] = useState(emptyForm)
  const [showFilters, setShowFilters] = useState(false)

  const tabs = useMemo(() => {
    const counts = { Tous: ofs.length, Ferme: 0, Planifié: 0, Clôturé: 0 }
    ofs.forEach(o => { if (counts[o.statut] !== undefined) counts[o.statut]++ })
    return [
      { label: 'Tous', count: counts.Tous },
      { label: 'Fermés', count: counts.Ferme },
      { label: 'Planifiés', count: counts.Planifié },
      { label: 'Clôturés', count: counts.Clôturé },
    ]
  }, [ofs])

  const filtered = useMemo(() => {
    let list = ofs
    if (activeTab !== 'Tous') {
      const map = { Fermés: 'Ferme', Planifiés: 'Planifié', Clôturés: 'Clôturé' }
      list = list.filter(o => o.statut === map[activeTab])
    }
    if (search.trim()) {
      const q = search.toLowerCase()
      list = list.filter(o =>
        o.num_of.toLowerCase().includes(q) ||
        o.article.toLowerCase().includes(q) ||
        o.designation.toLowerCase().includes(q)
      )
    }
    return list
  }, [ofs, activeTab, search])

  const stats = useMemo(() => {
    const enCours = ofs.filter(o => o.avancement === 'En cours').length
    const termines = ofs.filter(o => o.statut === 'Clôturé').length
    const avgAv = ofs.length ? Math.round(ofs.reduce((s, o) => s + o.realisation, 0) / ofs.length) : 0
    const qtePlanifiee = ofs.reduce((s, o) => s + o.quantite, 0)
    const qteRealisee = ofs.reduce((s, o) => s + Math.round(o.quantite * o.realisation / 100), 0)
    const enRetard = ofs.filter(o => isLate(o.fin) && o.statut !== 'Clôturé').length
    return { enCours, termines, avgAv, qtePlanifiee, qteRealisee, enRetard }
  }, [ofs])

  function openNew() {
    setForm({ ...emptyForm, num_of: `OF-2026-${String(ofs.length + 1).padStart(5, '0')}` })
    setEditOf('new')
  }

  function openEdit(of) {
    setForm({ ...of })
    setEditOf(of.id)
  }

  function saveForm() {
    if (editOf === 'new') {
      setOfs(prev => [{ ...form, id: Date.now(), quantite: +form.quantite || 0, realisation: +form.realisation || 0, priorite: +form.priorite || 5 }, ...prev])
    } else {
      setOfs(prev => prev.map(o => o.id === editOf ? { ...o, ...form, quantite: +form.quantite || 0, realisation: +form.realisation || 0, priorite: +form.priorite || 5 } : o))
    }
    setEditOf(null)
  }

  function confirmDelete() {
    setOfs(prev => prev.filter(o => o.id !== deleteOf.id))
    setDeleteOf(null)
  }

  return (
    <div className="flex flex-col h-full bg-gray-50 dark:bg-gray-900 min-h-0">
      {/* En-tête */}
      <div className="px-6 pt-5 pb-3 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <p className="text-xs text-gray-400 dark:text-gray-500 mb-1">Production › Planification › Ordres de fabrication</p>
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">Ordres de fabrication</h1>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowFilters(v => !v)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              <Filter size={14} /> Filtres
            </button>
            <button className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700">
              <Download size={14} /> Exporter <ChevronDown size={12} />
            </button>
            <button
              onClick={openNew}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-teal-600 hover:bg-teal-700 text-white rounded-lg font-medium"
            >
              <Plus size={14} /> Nouvel OF
            </button>
          </div>
        </div>

        {/* Barre de stats */}
        <div className="flex items-center gap-4 mt-3 text-xs text-gray-500 dark:text-gray-400 flex-wrap">
          <span className="flex items-center gap-1"><Package size={13} /> Total : <b className="text-gray-700 dark:text-gray-200">{ofs.length}</b></span>
          <span className="flex items-center gap-1 text-amber-600 dark:text-amber-400"><Clock size={13} /> En cours : <b>{stats.enCours}</b></span>
          <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400"><CheckCircle size={13} /> Terminés : <b>{stats.termines}</b></span>
          <span className="flex items-center gap-1">Avancement moyen : <b className="text-teal-600 dark:text-teal-400">{stats.avgAv}%</b></span>
          <span>Qté planifiée : <b>{stats.qtePlanifiee.toLocaleString()}</b> → <b>{stats.qteRealisee.toLocaleString()}</b> réalisée</span>
          {stats.enRetard > 0 && (
            <span className="flex items-center gap-1 text-red-500"><AlertCircle size={13} /> En retard : <b>{stats.enRetard}</b></span>
          )}
        </div>

        {/* Onglets */}
        <div className="flex gap-1 mt-3">
          {tabs.map(t => (
            <button
              key={t.label}
              onClick={() => setActiveTab(t.label)}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                activeTab === t.label
                  ? 'bg-gray-800 dark:bg-gray-200 text-white dark:text-gray-900'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600'
              }`}
            >
              <span className={`w-2 h-2 rounded-full ${
                t.label === 'Fermés' ? 'bg-emerald-400' :
                t.label === 'Planifiés' ? 'bg-blue-400' :
                t.label === 'Clôturés' ? 'bg-red-400' : 'bg-gray-400'
              }`} />
              {t.label} {t.count}
            </button>
          ))}
        </div>
      </div>

      {/* Recherche */}
      <div className="px-6 py-3 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="relative max-w-xs">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Rechercher un OF, article, désignation…"
            className="w-full pl-8 pr-3 py-1.5 text-sm border border-gray-200 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-teal-500"
          />
        </div>
      </div>

      {/* Tableau */}
      <div className="flex-1 overflow-auto px-6 py-4">
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-gray-50 dark:bg-gray-750 border-b border-gray-200 dark:border-gray-700">
                {['ACTIONS','N° OF','DATE','ARTICLE','DÉSIGNATION','QUANTITÉ','RÉALISATION','ORIGINE','SITE','DÉBUT','FIN','COMP/OP','JALONNEMENT','AVANCEMENT','STATUT'].map(h => (
                  <th key={h} className="px-3 py-2.5 text-left font-semibold text-gray-500 dark:text-gray-400 whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {filtered.length === 0 ? (
                <tr><td colSpan={17} className="text-center py-10 text-gray-400">Aucun OF trouvé</td></tr>
              ) : filtered.map(of => (
                <tr key={of.id} className="hover:bg-gray-50 dark:hover:bg-gray-750 transition-colors">
                  <td className="px-3 py-2.5">
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => openEdit(of)}
                        title="Modifier"
                        className="p-1.5 rounded-lg text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 hover:text-blue-700 transition-colors"
                      >
                        <Pencil size={14} />
                      </button>
                      <button
                        onClick={() => setDeleteOf(of)}
                        title="Supprimer"
                        className="p-1.5 rounded-lg text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 hover:text-red-600 transition-colors"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                  <td className="px-3 py-2.5 font-medium text-teal-600 dark:text-teal-400 whitespace-nowrap">{of.num_of}</td>
                  <td className="px-3 py-2.5 text-gray-600 dark:text-gray-400 whitespace-nowrap">{of.date}</td>
                  <td className="px-3 py-2.5 font-semibold text-blue-600 dark:text-blue-400">{of.article}</td>
                  <td className="px-3 py-2.5 text-gray-700 dark:text-gray-300">{of.designation}</td>
                  <td className="px-3 py-2.5 font-semibold text-gray-900 dark:text-white whitespace-nowrap">{of.quantite.toLocaleString()} {of.unite}</td>
                  <td className="px-3 py-2.5"><ProgressBar value={of.realisation} /></td>
                  <td className="px-3 py-2.5 text-purple-600 dark:text-purple-400 font-medium">{of.origine}</td>
                  <td className="px-3 py-2.5 text-gray-500 dark:text-gray-400">{of.site}</td>
                  <td className="px-3 py-2.5 text-gray-600 dark:text-gray-400 whitespace-nowrap">{of.debut}</td>
                  <td className={`px-3 py-2.5 whitespace-nowrap font-medium ${isLate(of.fin) && of.statut !== 'Clôturé' ? 'text-red-500' : 'text-gray-600 dark:text-gray-400'}`}>
                    {of.fin}
                  </td>
                  <td className="px-3 py-2.5 text-gray-600 dark:text-gray-400">{of.comp_op}</td>
                  <td className="px-3 py-2.5 text-gray-500 dark:text-gray-400 whitespace-nowrap">{of.jalonnement}</td>
                  <td className="px-3 py-2.5">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                      of.avancement === 'En cours' ? 'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-300' :
                      of.avancement === 'Terminé' ? 'bg-emerald-100 text-emerald-700' :
                      'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400'
                    }`}>{of.avancement}</span>
                  </td>
                  <td className="px-3 py-2.5"><StatutBadge statut={of.statut} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal Edit / Nouveau */}
      {editOf !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-base font-bold text-gray-900 dark:text-white">
                {editOf === 'new' ? 'Nouvel ordre de fabrication' : `Modifier ${form.num_of}`}
              </h2>
              <button onClick={() => setEditOf(null)} className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-500">
                <X size={16} />
              </button>
            </div>

            <div className="px-6 py-5 grid grid-cols-2 gap-4">
              {[
                { label: 'N° OF', key: 'num_of', readOnly: editOf !== 'new' },
                { label: 'Date', key: 'date', type: 'text', placeholder: 'jj/mm/aaaa' },
                { label: 'Article', key: 'article' },
                { label: 'Désignation', key: 'designation' },
                { label: 'Quantité', key: 'quantite', type: 'number' },
                { label: 'Unité', key: 'unite' },
                { label: 'Début', key: 'debut', placeholder: 'jj/mm/aaaa' },
                { label: 'Fin', key: 'fin', placeholder: 'jj/mm/aaaa' },
                { label: 'Priorité', key: 'priorite', type: 'number' },
                { label: 'COMP/OP', key: 'comp_op' },
              ].map(({ label, key, readOnly, type = 'text', placeholder }) => (
                <div key={key}>
                  <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">{label}</label>
                  <input
                    type={type}
                    value={form[key]}
                    onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                    readOnly={readOnly}
                    placeholder={placeholder}
                    className={`w-full px-3 py-1.5 text-sm border border-gray-200 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-teal-500 ${readOnly ? 'opacity-60 cursor-not-allowed' : ''}`}
                  />
                </div>
              ))}

              {[
                { label: 'Origine', key: 'origine', options: ORIGINES },
                { label: 'Site', key: 'site', options: SITES },
                { label: 'Statut', key: 'statut', options: STATUTS },
                { label: 'Jalonnement', key: 'jalonnement', options: ['Non jalonné', 'Jalonné'] },
                { label: 'Allocation', key: 'allocation', options: ['Aucune', 'Partielle', 'Totale'] },
                { label: 'Avancement', key: 'avancement', options: ['Non démarré', 'En cours', 'Terminé'] },
              ].map(({ label, key, options }) => (
                <div key={key}>
                  <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">{label}</label>
                  <select
                    value={form[key]}
                    onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                    className="w-full px-3 py-1.5 text-sm border border-gray-200 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-teal-500"
                  >
                    {options.map(o => <option key={o} value={o}>{o}</option>)}
                  </select>
                </div>
              ))}

              <div className="col-span-2">
                <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Réalisation (%)</label>
                <input
                  type="range" min="0" max="100"
                  value={form.realisation}
                  onChange={e => setForm(f => ({ ...f, realisation: +e.target.value }))}
                  className="w-full accent-teal-600"
                />
                <span className="text-xs text-teal-600 dark:text-teal-400">{form.realisation}%</span>
              </div>
            </div>

            <div className="flex justify-end gap-2 px-6 py-4 border-t border-gray-200 dark:border-gray-700">
              <button onClick={() => setEditOf(null)} className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700">
                Annuler
              </button>
              <button onClick={saveForm} className="px-4 py-2 text-sm bg-teal-600 hover:bg-teal-700 text-white rounded-lg font-medium">
                {editOf === 'new' ? 'Créer' : 'Enregistrer'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Delete */}
      {deleteOf && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-sm mx-4 p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center">
                <Trash2 size={18} className="text-red-500" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-gray-900 dark:text-white">Supprimer l'OF</h3>
                <p className="text-xs text-gray-500 dark:text-gray-400">{deleteOf.num_of}</p>
              </div>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-5">
              Êtes-vous sûr de vouloir supprimer cet ordre de fabrication ? Cette action est irréversible.
            </p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setDeleteOf(null)} className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700">
                Annuler
              </button>
              <button onClick={confirmDelete} className="px-4 py-2 text-sm bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium">
                Supprimer
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
