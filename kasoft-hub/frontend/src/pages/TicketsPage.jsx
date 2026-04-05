import React, { useEffect, useState } from 'react'
import { ticketsApi, productsApi } from '../services/api'

const STATUT_COLORS = {
  open:        'bg-blue-100 text-blue-700',
  in_progress: 'bg-amber-100 text-amber-700',
  pending:     'bg-purple-100 text-purple-700',
  resolved:    'bg-green-100 text-green-700',
  closed:      'bg-gray-100 text-gray-500',
  overdue:     'bg-red-100 text-red-700',
}
const PRIORITE_COLORS = {
  low: 'text-gray-400', medium: 'text-amber-500', high: 'text-orange-500', critical: 'text-red-600 font-bold',
}

export default function TicketsPage() {
  const [tickets, setTickets] = useState([])
  const [total, setTotal] = useState(0)
  const [stats, setStats] = useState({})
  const [products, setProducts] = useState([])
  const [filters, setFilters] = useState({ product_code: '', statut: '', search: '' })
  const [selected, setSelected] = useState(null)
  const [reply, setReply] = useState({ contenu: '', channel: 'email' })
  const [showCreate, setShowCreate] = useState(false)
  const [newTicket, setNewTicket] = useState({ product_code: '', sujet: '', description: '', priorite: 'medium' })

  const load = () => {
    ticketsApi.list(filters).then(r => { setTickets(r.data.data); setTotal(r.data.total) })
    ticketsApi.stats().then(r => setStats(r.data.data))
  }
  useEffect(() => { load() }, [filters])
  useEffect(() => { productsApi.list().then(r => setProducts(r.data.data)).catch(() => {}) }, [])

  const sendReply = async () => {
    if (!reply.contenu.trim()) return
    await ticketsApi.reply(selected.id, reply)
    setReply({ contenu: '', channel: 'email' })
    ticketsApi.get(selected.id).then(r => setSelected(r.data.data))
    load()
  }

  const changeStatus = async (id, statut) => {
    await ticketsApi.updateStatus(id, { statut })
    load()
    if (selected?.id === id) ticketsApi.get(id).then(r => setSelected(r.data.data))
  }

  const createTicket = async () => {
    await ticketsApi.create(newTicket)
    setShowCreate(false)
    setNewTicket({ product_code: '', sujet: '', description: '', priorite: 'medium' })
    load()
  }

  return (
    <div className="p-6 flex gap-4 h-full">
      {/* Liste tickets */}
      <div className="flex-1 space-y-4 overflow-auto">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-800">SAV <span className="text-gray-400 text-lg">({total})</span></h1>
          <button onClick={() => setShowCreate(true)} className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-indigo-700">+ Nouveau ticket</button>
        </div>

        {/* Stats bar */}
        <div className="grid grid-cols-5 gap-2 text-center">
          {[
            { label: 'Ouverts', val: stats.open_count, color: 'text-blue-600' },
            { label: 'En cours', val: stats.inprog_count, color: 'text-amber-600' },
            { label: 'En retard', val: stats.overdue_count, color: 'text-red-600' },
            { label: 'Résolus', val: stats.resolved_count, color: 'text-green-600' },
            { label: 'Moy résol.', val: stats.avg_resolution_hours ? `${Math.round(stats.avg_resolution_hours)}h` : '—', color: 'text-gray-600' },
          ].map(s => (
            <div key={s.label} className="bg-white rounded-lg border p-2">
              <div className={`text-xl font-bold ${s.color}`}>{s.val ?? '—'}</div>
              <div className="text-xs text-gray-500">{s.label}</div>
            </div>
          ))}
        </div>

        {/* Filtres */}
        <div className="flex gap-2">
          <select className="border rounded px-3 py-2 text-sm" value={filters.product_code} onChange={e => setFilters(f => ({ ...f, product_code: e.target.value }))}>
            <option value="">Tous produits</option>
            {products.map(p => <option key={p.code} value={p.code}>{p.nom}</option>)}
          </select>
          <select className="border rounded px-3 py-2 text-sm" value={filters.statut} onChange={e => setFilters(f => ({ ...f, statut: e.target.value }))}>
            <option value="">Tous statuts</option>
            {Object.keys(STATUT_COLORS).map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <input className="border rounded px-3 py-2 text-sm flex-1" placeholder="Rechercher..." value={filters.search} onChange={e => setFilters(f => ({ ...f, search: e.target.value }))} />
        </div>

        <div className="space-y-2">
          {tickets.map(t => (
            <div key={t.id} onClick={() => ticketsApi.get(t.id).then(r => setSelected(r.data.data))}
              className={`bg-white border rounded-xl p-4 cursor-pointer hover:border-indigo-300 transition-colors ${selected?.id === t.id ? 'border-indigo-400 shadow-sm' : ''}`}>
              <div className="flex items-start justify-between">
                <div>
                  <div className="font-medium text-gray-800">{t.sujet}</div>
                  <div className="text-xs text-gray-500 mt-1">{t.numero} · {t.product_code} · {t.contact_nom || 'Sans contact'}</div>
                </div>
                <div className="flex gap-2 items-center">
                  <span className={`text-xs font-medium ${PRIORITE_COLORS[t.priorite]}`}>{t.priorite}</span>
                  <span className={`text-xs px-2 py-1 rounded-full font-medium ${STATUT_COLORS[t.statut]}`}>{t.statut}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Panel ticket sélectionné */}
      {selected && (
        <div className="w-96 bg-white border rounded-xl p-4 flex flex-col overflow-auto shrink-0">
          <div className="flex justify-between items-start mb-3">
            <div>
              <div className="font-bold text-gray-800">{selected.sujet}</div>
              <div className="text-xs text-gray-400">{selected.numero}</div>
            </div>
            <button onClick={() => setSelected(null)} className="text-gray-400 hover:text-gray-700">✕</button>
          </div>

          {selected.description && <p className="text-sm text-gray-600 mb-3 border-b pb-3">{selected.description}</p>}

          {/* Actions statut */}
          <div className="flex gap-1 flex-wrap mb-3">
            {['open', 'in_progress', 'resolved', 'closed'].map(s => (
              <button key={s} onClick={() => changeStatus(selected.id, s)}
                className={`text-xs px-2 py-1 rounded border transition-colors ${selected.statut === s ? 'bg-indigo-600 text-white border-indigo-600' : 'hover:bg-gray-50'}`}>
                {s}
              </button>
            ))}
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-auto space-y-2 mb-3 max-h-60">
            {(selected.messages || []).map(m => (
              <div key={m.id} className={`rounded-lg p-2 text-sm ${m.direction === 'out' ? 'bg-indigo-50 ml-4' : 'bg-gray-50 mr-4'}`}>
                <div>{m.contenu}</div>
                <div className="text-xs text-gray-400 mt-1">{m.sent_by} · {new Date(m.sent_at).toLocaleString('fr-FR')}</div>
              </div>
            ))}
          </div>

          {/* Répondre */}
          <div className="border-t pt-3 space-y-2">
            <select className="w-full border rounded px-2 py-1 text-sm" value={reply.channel} onChange={e => setReply(r => ({ ...r, channel: e.target.value }))}>
              <option value="email">Email</option>
              <option value="whatsapp">WhatsApp</option>
              <option value="telegram">Telegram</option>
            </select>
            <textarea className="w-full border rounded px-2 py-1 text-sm h-20 resize-none" placeholder="Votre réponse..." value={reply.contenu} onChange={e => setReply(r => ({ ...r, contenu: e.target.value }))} />
            <button onClick={sendReply} className="w-full bg-indigo-600 text-white rounded py-2 text-sm hover:bg-indigo-700">Envoyer</button>
          </div>
        </div>
      )}

      {/* Modal nouveau ticket */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md space-y-3">
            <h2 className="font-bold text-lg">Nouveau ticket SAV</h2>
            <select className="w-full border rounded px-3 py-2 text-sm" value={newTicket.product_code} onChange={e => setNewTicket(t => ({ ...t, product_code: e.target.value }))}>
              <option value="">-- Produit --</option>
              {products.map(p => <option key={p.code} value={p.code}>{p.nom}</option>)}
            </select>
            <input className="w-full border rounded px-3 py-2 text-sm" placeholder="Sujet *" value={newTicket.sujet} onChange={e => setNewTicket(t => ({ ...t, sujet: e.target.value }))} />
            <textarea className="w-full border rounded px-3 py-2 text-sm h-24 resize-none" placeholder="Description..." value={newTicket.description} onChange={e => setNewTicket(t => ({ ...t, description: e.target.value }))} />
            <select className="w-full border rounded px-3 py-2 text-sm" value={newTicket.priorite} onChange={e => setNewTicket(t => ({ ...t, priorite: e.target.value }))}>
              {['low', 'medium', 'high', 'critical'].map(p => <option key={p} value={p}>{p}</option>)}
            </select>
            <div className="flex gap-3 justify-end">
              <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-sm border rounded hover:bg-gray-50">Annuler</button>
              <button onClick={createTicket} disabled={!newTicket.sujet || !newTicket.product_code} className="px-4 py-2 text-sm bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50">Créer</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
