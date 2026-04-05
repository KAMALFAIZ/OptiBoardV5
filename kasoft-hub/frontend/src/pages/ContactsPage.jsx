import React, { useEffect, useState } from 'react'
import { contactsApi, productsApi } from '../services/api'

const SEGMENTS = ['', 'prospect', 'lead', 'client', 'churned']
const SEGMENT_COLORS = { prospect: 'bg-blue-100 text-blue-700', lead: 'bg-amber-100 text-amber-700', client: 'bg-green-100 text-green-700', churned: 'bg-gray-100 text-gray-500' }

export default function ContactsPage() {
  const [contacts, setContacts] = useState([])
  const [total, setTotal] = useState(0)
  const [products, setProducts] = useState([])
  const [filters, setFilters] = useState({ product_code: '', segment: '', search: '' })
  const [loading, setLoading] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ product_code: '', nom: '', prenom: '', email: '', telephone: '', whatsapp: '', societe: '', segment: 'prospect', source: 'manual' })

  const load = () => {
    setLoading(true)
    contactsApi.list(filters).then(r => {
      setContacts(r.data.data)
      setTotal(r.data.total)
    }).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [filters])
  useEffect(() => { productsApi.list().then(r => setProducts(r.data.data)).catch(() => {}) }, [])

  const save = async () => {
    await contactsApi.create(form)
    setShowForm(false)
    setForm({ product_code: '', nom: '', prenom: '', email: '', telephone: '', whatsapp: '', societe: '', segment: 'prospect', source: 'manual' })
    load()
  }

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-800">Contacts <span className="text-gray-400 text-lg">({total})</span></h1>
        <button onClick={() => setShowForm(true)} className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-indigo-700">+ Nouveau contact</button>
      </div>

      {/* Filtres */}
      <div className="flex gap-3 flex-wrap">
        <select className="border rounded-lg px-3 py-2 text-sm" value={filters.product_code} onChange={e => setFilters(f => ({ ...f, product_code: e.target.value }))}>
          <option value="">Tous les produits</option>
          {products.map(p => <option key={p.code} value={p.code}>{p.nom}</option>)}
        </select>
        <select className="border rounded-lg px-3 py-2 text-sm" value={filters.segment} onChange={e => setFilters(f => ({ ...f, segment: e.target.value }))}>
          {SEGMENTS.map(s => <option key={s} value={s}>{s || 'Tous segments'}</option>)}
        </select>
        <input className="border rounded-lg px-3 py-2 text-sm flex-1 min-w-48" placeholder="Rechercher nom, email, société..." value={filters.search} onChange={e => setFilters(f => ({ ...f, search: e.target.value }))} />
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              {['Nom', 'Société', 'Email', 'Téléphone', 'Produit', 'Segment', 'Source', 'Date'].map(h => (
                <th key={h} className="text-left px-4 py-3 font-medium text-gray-600">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y">
            {loading ? (
              <tr><td colSpan={8} className="text-center py-8 text-gray-400">Chargement...</td></tr>
            ) : contacts.length === 0 ? (
              <tr><td colSpan={8} className="text-center py-8 text-gray-400">Aucun contact</td></tr>
            ) : contacts.map(c => (
              <tr key={c.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-medium">{c.nom} {c.prenom || ''}</td>
                <td className="px-4 py-3 text-gray-600">{c.societe || '—'}</td>
                <td className="px-4 py-3 text-gray-600">{c.email || '—'}</td>
                <td className="px-4 py-3 text-gray-600">{c.telephone || '—'}</td>
                <td className="px-4 py-3"><span className="text-xs bg-gray-100 px-2 py-1 rounded">{c.product_code}</span></td>
                <td className="px-4 py-3"><span className={`text-xs px-2 py-1 rounded-full font-medium ${SEGMENT_COLORS[c.segment] || ''}`}>{c.segment}</span></td>
                <td className="px-4 py-3 text-gray-500">{c.source}</td>
                <td className="px-4 py-3 text-gray-400">{new Date(c.created_at).toLocaleDateString('fr-FR')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Modal nouveau contact */}
      {showForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-lg space-y-3">
            <h2 className="font-bold text-lg">Nouveau contact</h2>
            <div className="grid grid-cols-2 gap-3">
              <select className="border rounded px-3 py-2 text-sm col-span-2" value={form.product_code} onChange={e => setForm(f => ({ ...f, product_code: e.target.value }))}>
                <option value="">-- Produit --</option>
                {products.map(p => <option key={p.code} value={p.code}>{p.nom}</option>)}
              </select>
              <input className="border rounded px-3 py-2 text-sm" placeholder="Nom *" value={form.nom} onChange={e => setForm(f => ({ ...f, nom: e.target.value }))} />
              <input className="border rounded px-3 py-2 text-sm" placeholder="Prénom" value={form.prenom} onChange={e => setForm(f => ({ ...f, prenom: e.target.value }))} />
              <input className="border rounded px-3 py-2 text-sm" placeholder="Email" value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} />
              <input className="border rounded px-3 py-2 text-sm" placeholder="Téléphone" value={form.telephone} onChange={e => setForm(f => ({ ...f, telephone: e.target.value }))} />
              <input className="border rounded px-3 py-2 text-sm col-span-2" placeholder="Société" value={form.societe} onChange={e => setForm(f => ({ ...f, societe: e.target.value }))} />
              <select className="border rounded px-3 py-2 text-sm" value={form.segment} onChange={e => setForm(f => ({ ...f, segment: e.target.value }))}>
                {['prospect', 'lead', 'client'].map(s => <option key={s} value={s}>{s}</option>)}
              </select>
              <select className="border rounded px-3 py-2 text-sm" value={form.source} onChange={e => setForm(f => ({ ...f, source: e.target.value }))}>
                {['manual', 'website', 'demo', 'referral', 'cold', 'webhook'].map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div className="flex gap-3 justify-end pt-2">
              <button onClick={() => setShowForm(false)} className="px-4 py-2 text-sm border rounded-lg hover:bg-gray-50">Annuler</button>
              <button onClick={save} disabled={!form.nom || !form.product_code} className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50">Créer</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
