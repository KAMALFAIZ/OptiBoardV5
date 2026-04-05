import React, { useEffect, useState } from 'react'
import { campaignsApi, productsApi, templatesApi } from '../services/api'

const STATUT_COLORS = { draft: 'bg-gray-100 text-gray-600', active: 'bg-green-100 text-green-700', paused: 'bg-amber-100 text-amber-700', completed: 'bg-blue-100 text-blue-700' }

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState([])
  const [products, setProducts] = useState([])
  const [templates, setTemplates] = useState([])
  const [selected, setSelected] = useState(null)
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({ nom: '', type_camp: 'nurturing', channel: 'multi', product_code: 'ALL', description: '' })
  const [newStep, setNewStep] = useState({ step_order: 1, delay_days: 0, channel: 'email', template_id: '', condition_type: 'always' })

  const load = () => campaignsApi.list().then(r => setCampaigns(r.data.data)).catch(() => {})

  useEffect(() => { load() }, [])
  useEffect(() => {
    productsApi.list().then(r => setProducts(r.data.data)).catch(() => {})
    templatesApi.list().then(r => setTemplates(r.data.data)).catch(() => {})
  }, [])

  const openCampaign = (id) => campaignsApi.get(id).then(r => setSelected(r.data.data))

  const createCampaign = async () => {
    await campaignsApi.create(form)
    setShowCreate(false)
    setForm({ nom: '', type_camp: 'nurturing', channel: 'multi', product_code: 'ALL', description: '' })
    load()
  }

  const addStep = async () => {
    if (!selected) return
    await campaignsApi.addStep(selected.id, { ...newStep, template_id: newStep.template_id || null })
    setNewStep({ step_order: (selected.steps?.length || 0) + 2, delay_days: 0, channel: 'email', template_id: '', condition_type: 'always' })
    openCampaign(selected.id)
  }

  const startCampaign = async (id) => { await campaignsApi.start(id); load(); if (selected?.id === id) openCampaign(id) }
  const pauseCampaign = async (id) => { await campaignsApi.pause(id); load(); if (selected?.id === id) openCampaign(id) }

  return (
    <div className="p-6 flex gap-4">
      <div className="flex-1 space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-800">Campagnes Marketing</h1>
          <button onClick={() => setShowCreate(true)} className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-indigo-700">+ Nouvelle campagne</button>
        </div>

        <div className="space-y-3">
          {campaigns.map(c => (
            <div key={c.id} onClick={() => openCampaign(c.id)}
              className={`bg-white border rounded-xl p-4 cursor-pointer hover:border-indigo-300 ${selected?.id === c.id ? 'border-indigo-400' : ''}`}>
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium text-gray-800">{c.nom}</div>
                  <div className="text-xs text-gray-400 mt-1">{c.product_code} · {c.type_camp} · {c.steps_count} étapes · {c.enrolled_count} inscrits</div>
                </div>
                <div className="flex gap-2 items-center">
                  <span className={`text-xs px-2 py-1 rounded-full font-medium ${STATUT_COLORS[c.statut]}`}>{c.statut}</span>
                  {c.statut === 'draft' && <button onClick={e => { e.stopPropagation(); startCampaign(c.id) }} className="text-xs bg-green-600 text-white px-2 py-1 rounded hover:bg-green-700">Activer</button>}
                  {c.statut === 'active' && <button onClick={e => { e.stopPropagation(); pauseCampaign(c.id) }} className="text-xs bg-amber-500 text-white px-2 py-1 rounded hover:bg-amber-600">Pause</button>}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Détail campagne */}
      {selected && (
        <div className="w-96 bg-white border rounded-xl p-4 space-y-4 overflow-auto shrink-0">
          <div className="flex justify-between">
            <div className="font-bold text-gray-800">{selected.nom}</div>
            <button onClick={() => setSelected(null)} className="text-gray-400 hover:text-gray-700">✕</button>
          </div>

          <div className="text-sm text-gray-500">{selected.description || 'Aucune description'}</div>

          <div>
            <div className="font-medium text-sm mb-2">Étapes ({selected.steps?.length || 0})</div>
            <div className="space-y-2">
              {(selected.steps || []).map(s => (
                <div key={s.id} className="flex items-center gap-2 text-sm bg-gray-50 rounded p-2">
                  <span className="w-6 h-6 rounded-full bg-indigo-100 text-indigo-700 text-xs flex items-center justify-center font-bold">{s.step_order}</span>
                  <span className="flex-1">J+{s.delay_days} · {s.channel}</span>
                  <span className="text-xs text-gray-400">Template #{s.template_id || '—'}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Ajouter étape */}
          <div className="border-t pt-3 space-y-2">
            <div className="font-medium text-sm">Ajouter une étape</div>
            <div className="grid grid-cols-2 gap-2">
              <input type="number" className="border rounded px-2 py-1 text-sm" placeholder="Ordre" value={newStep.step_order} onChange={e => setNewStep(s => ({ ...s, step_order: +e.target.value }))} />
              <input type="number" className="border rounded px-2 py-1 text-sm" placeholder="Délai (jours)" value={newStep.delay_days} onChange={e => setNewStep(s => ({ ...s, delay_days: +e.target.value }))} />
              <select className="border rounded px-2 py-1 text-sm" value={newStep.channel} onChange={e => setNewStep(s => ({ ...s, channel: e.target.value }))}>
                {['email', 'whatsapp', 'telegram'].map(c => <option key={c} value={c}>{c}</option>)}
              </select>
              <select className="border rounded px-2 py-1 text-sm" value={newStep.template_id} onChange={e => setNewStep(s => ({ ...s, template_id: e.target.value }))}>
                <option value="">-- Template --</option>
                {templates.filter(t => t.channel === newStep.channel).map(t => <option key={t.id} value={t.id}>{t.nom}</option>)}
              </select>
            </div>
            <button onClick={addStep} className="w-full bg-indigo-600 text-white rounded py-2 text-sm hover:bg-indigo-700">+ Ajouter étape</button>
          </div>
        </div>
      )}

      {/* Modal créer campagne */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md space-y-3">
            <h2 className="font-bold text-lg">Nouvelle campagne</h2>
            <input className="w-full border rounded px-3 py-2 text-sm" placeholder="Nom *" value={form.nom} onChange={e => setForm(f => ({ ...f, nom: e.target.value }))} />
            <select className="w-full border rounded px-3 py-2 text-sm" value={form.product_code} onChange={e => setForm(f => ({ ...f, product_code: e.target.value }))}>
              <option value="ALL">Tous les produits</option>
              {products.map(p => <option key={p.code} value={p.code}>{p.nom}</option>)}
            </select>
            <select className="w-full border rounded px-3 py-2 text-sm" value={form.type_camp} onChange={e => setForm(f => ({ ...f, type_camp: e.target.value }))}>
              {['onboarding', 'nurturing', 'promo', 'reactivation'].map(t => <option key={t} value={t}>{t}</option>)}
            </select>
            <textarea className="w-full border rounded px-3 py-2 text-sm h-20 resize-none" placeholder="Description..." value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
            <div className="flex gap-3 justify-end">
              <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-sm border rounded hover:bg-gray-50">Annuler</button>
              <button onClick={createCampaign} disabled={!form.nom} className="px-4 py-2 text-sm bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50">Créer</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
