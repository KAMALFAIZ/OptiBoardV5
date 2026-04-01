import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Users, Plus, Search, Mail, Phone, Key, ArrowRight, X } from 'lucide-react'
import api from '../services/api'

export default function Clients() {
  const [clients, setClients] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [form, setForm] = useState({ code: '', name: '', email: '', phone: '', contact_name: '', address: '', notes: '' })
  const [saving, setSaving] = useState(false)

  const load = async () => {
    try {
      const res = await api.get('/clients')
      setClients(res.data.data)
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const filtered = clients.filter(c =>
    c.name?.toLowerCase().includes(search.toLowerCase()) ||
    c.code?.toLowerCase().includes(search.toLowerCase()) ||
    c.email?.toLowerCase().includes(search.toLowerCase())
  )

  const handleCreate = async () => {
    if (!form.code || !form.name) return
    setSaving(true)
    try {
      await api.post('/clients', form)
      setShowModal(false)
      setForm({ code: '', name: '', email: '', phone: '', contact_name: '', address: '', notes: '' })
      load()
    } catch (e) {
      alert(e.response?.data?.detail || 'Erreur')
    } finally { setSaving(false) }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500" />
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Users className="w-6 h-6 text-blue-400" /> Clients
          </h1>
          <p className="text-gray-500 text-sm mt-1">{clients.length} clients enregistres</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium transition-colors"
        >
          <Plus className="w-4 h-4" /> Nouveau client
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Rechercher un client..."
          className="w-full pl-10 pr-4 py-2.5 bg-gray-900 border border-gray-800 rounded-lg text-sm text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500/50"
        />
      </div>

      {/* Client Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {filtered.map(client => (
          <Link
            key={client.id}
            to={`/clients/${client.id}`}
            className="bg-gray-900 border border-gray-800 rounded-xl p-5 hover:border-blue-500/30 transition-colors group"
          >
            <div className="flex items-start justify-between mb-3">
              <div>
                <h3 className="font-semibold text-white group-hover:text-blue-400 transition-colors">{client.name}</h3>
                <p className="text-xs text-gray-500 font-mono mt-0.5">{client.code}</p>
              </div>
              <div className="flex items-center gap-1.5 px-2 py-1 bg-blue-500/10 text-blue-400 rounded-lg text-xs">
                <Key className="w-3 h-3" />
                {client.license_count || 0}
              </div>
            </div>
            {client.email && (
              <div className="flex items-center gap-2 text-xs text-gray-500 mt-2">
                <Mail className="w-3.5 h-3.5" /> {client.email}
              </div>
            )}
            {client.phone && (
              <div className="flex items-center gap-2 text-xs text-gray-500 mt-1">
                <Phone className="w-3.5 h-3.5" /> {client.phone}
              </div>
            )}
            <div className="flex items-center justify-end mt-3 text-xs text-gray-600 group-hover:text-blue-400">
              Voir details <ArrowRight className="w-3.5 h-3.5 ml-1" />
            </div>
          </Link>
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="text-center py-12 text-gray-600">
          {search ? 'Aucun client correspondant' : 'Aucun client enregistre'}
        </div>
      )}

      {/* Modal Nouveau Client */}
      {showModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-lg">
            <div className="flex items-center justify-between p-5 border-b border-gray-800">
              <h2 className="text-lg font-semibold">Nouveau client</h2>
              <button onClick={() => setShowModal(false)} className="p-1 hover:bg-gray-800 rounded-lg">
                <X className="w-5 h-5 text-gray-400" />
              </button>
            </div>
            <div className="p-5 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs text-gray-400 mb-1.5">Code *</label>
                  <input value={form.code} onChange={e => setForm({ ...form, code: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500/30"
                    placeholder="CLI001" />
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1.5">Nom *</label>
                  <input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500/30"
                    placeholder="Entreprise SARL" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs text-gray-400 mb-1.5">Email</label>
                  <input value={form.email} onChange={e => setForm({ ...form, email: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500/30"
                    placeholder="contact@entreprise.com" />
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1.5">Telephone</label>
                  <input value={form.phone} onChange={e => setForm({ ...form, phone: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500/30"
                    placeholder="+213 555 123 456" />
                </div>
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1.5">Contact</label>
                <input value={form.contact_name} onChange={e => setForm({ ...form, contact_name: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500/30"
                  placeholder="M. Ahmed" />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1.5">Adresse</label>
                <input value={form.address} onChange={e => setForm({ ...form, address: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500/30"
                  placeholder="Alger, Algerie" />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1.5">Notes</label>
                <textarea value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} rows={2}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500/30 resize-none"
                  placeholder="Notes optionnelles..." />
              </div>
            </div>
            <div className="flex justify-end gap-3 p-5 border-t border-gray-800">
              <button onClick={() => setShowModal(false)}
                className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors">
                Annuler
              </button>
              <button onClick={handleCreate} disabled={saving || !form.code || !form.name}
                className="px-5 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-600/30 disabled:cursor-not-allowed rounded-lg text-sm font-medium transition-colors">
                {saving ? 'Creation...' : 'Creer le client'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
