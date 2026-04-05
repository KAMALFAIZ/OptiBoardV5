import React, { useEffect, useState } from 'react'
import { templatesApi } from '../services/api'

const CHANNELS = ['email', 'whatsapp', 'telegram']
const CHANNEL_ICONS = { email: '📧', whatsapp: '📱', telegram: '✈️' }

export default function TemplatesPage() {
  const [templates, setTemplates] = useState([])
  const [filter, setFilter] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState({ nom: '', channel: 'whatsapp', sujet: '', contenu: '', product_code: 'ALL' })

  const load = () => templatesApi.list({ channel: filter || undefined }).then(r => setTemplates(r.data.data)).catch(() => {})
  useEffect(() => { load() }, [filter])

  const save = async () => {
    if (editing) { await templatesApi.update(editing.id, form) }
    else { await templatesApi.create(form) }
    setShowCreate(false)
    setEditing(null)
    setForm({ nom: '', channel: 'whatsapp', sujet: '', contenu: '', product_code: 'ALL' })
    load()
  }

  const del = async (id) => { if (window.confirm('Supprimer ?')) { await templatesApi.delete(id); load() } }

  const openEdit = (t) => { setForm({ nom: t.nom, channel: t.channel, sujet: t.sujet || '', contenu: t.contenu, product_code: t.product_code }); setEditing(t); setShowCreate(true) }

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-800">Templates Messages</h1>
        <button onClick={() => { setEditing(null); setForm({ nom: '', channel: 'whatsapp', sujet: '', contenu: '', product_code: 'ALL' }); setShowCreate(true) }}
          className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-indigo-700">+ Nouveau template</button>
      </div>

      <div className="flex gap-2">
        <button onClick={() => setFilter('')} className={`px-3 py-1.5 rounded text-sm ${filter === '' ? 'bg-indigo-600 text-white' : 'border hover:bg-gray-50'}`}>Tous</button>
        {CHANNELS.map(c => (
          <button key={c} onClick={() => setFilter(c)} className={`px-3 py-1.5 rounded text-sm ${filter === c ? 'bg-indigo-600 text-white' : 'border hover:bg-gray-50'}`}>
            {CHANNEL_ICONS[c]} {c}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {templates.map(t => (
          <div key={t.id} className="bg-white border rounded-xl p-4 space-y-2">
            <div className="flex items-start justify-between">
              <div>
                <div className="font-medium text-gray-800">{t.nom}</div>
                <div className="text-xs text-gray-400">{t.product_code}</div>
              </div>
              <span className="text-lg">{CHANNEL_ICONS[t.channel]}</span>
            </div>
            {t.sujet && <div className="text-xs font-medium text-gray-600">Sujet: {t.sujet}</div>}
            <div className="text-sm text-gray-600 bg-gray-50 rounded p-2 max-h-24 overflow-auto whitespace-pre-wrap">{t.contenu}</div>
            <div className="flex gap-2 pt-1">
              <button onClick={() => openEdit(t)} className="text-xs text-indigo-600 hover:underline">Modifier</button>
              <button onClick={() => del(t.id)} className="text-xs text-red-400 hover:text-red-600">Supprimer</button>
            </div>
          </div>
        ))}
        {templates.length === 0 && <div className="col-span-3 text-center py-12 text-gray-400">Aucun template</div>}
      </div>

      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-lg space-y-3">
            <h2 className="font-bold text-lg">{editing ? 'Modifier' : 'Nouveau'} template</h2>
            <input className="w-full border rounded px-3 py-2 text-sm" placeholder="Nom *" value={form.nom} onChange={e => setForm(f => ({ ...f, nom: e.target.value }))} />
            <div className="grid grid-cols-2 gap-3">
              <select className="border rounded px-3 py-2 text-sm" value={form.channel} onChange={e => setForm(f => ({ ...f, channel: e.target.value }))}>
                {CHANNELS.map(c => <option key={c} value={c}>{CHANNEL_ICONS[c]} {c}</option>)}
              </select>
              <select className="border rounded px-3 py-2 text-sm" value={form.product_code} onChange={e => setForm(f => ({ ...f, product_code: e.target.value }))}>
                <option value="ALL">Tous produits</option>
                {['OPTIBOARD', 'OPTIBTP', 'OPTICRM', 'OPTIPROMIMMO'].map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            {form.channel === 'email' && (
              <input className="w-full border rounded px-3 py-2 text-sm" placeholder="Sujet email" value={form.sujet} onChange={e => setForm(f => ({ ...f, sujet: e.target.value }))} />
            )}
            <div>
              <textarea className="w-full border rounded px-3 py-2 text-sm h-32 resize-none" placeholder="Contenu du message... Utilisez {nom}, {societe}, {produit}" value={form.contenu} onChange={e => setForm(f => ({ ...f, contenu: e.target.value }))} />
              <div className="text-xs text-gray-400 mt-1">Variables : {'{nom}'} {'{prenom}'} {'{societe}'} {'{email}'} {'{produit}'}</div>
            </div>
            <div className="flex gap-3 justify-end">
              <button onClick={() => { setShowCreate(false); setEditing(null) }} className="px-4 py-2 text-sm border rounded hover:bg-gray-50">Annuler</button>
              <button onClick={save} disabled={!form.nom || !form.contenu} className="px-4 py-2 text-sm bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50">Sauvegarder</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
