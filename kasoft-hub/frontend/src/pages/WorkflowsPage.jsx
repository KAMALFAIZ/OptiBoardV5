import React, { useEffect, useState } from 'react'
import { workflowsApi, templatesApi, productsApi } from '../services/api'

const EVENTS = ['new_prospect', 'new_client', 'demo_requested', 'demo_completed', 'ticket_opened', 'ticket_resolved', 'payment_late', 'subscription_expiring']
const CHANNELS = ['telegram', 'whatsapp', 'email']

export default function WorkflowsPage() {
  const [workflows, setWorkflows] = useState([])
  const [templates, setTemplates] = useState([])
  const [products, setProducts] = useState([])
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({ nom: '', trigger_event: 'new_prospect', product_code: 'ALL', is_active: true, actions: [{ type: 'send_message', channel: 'whatsapp', template_id: '', delay_hours: 0 }] })

  const load = () => workflowsApi.list().then(r => setWorkflows(r.data.data)).catch(() => {})
  useEffect(() => { load() }, [])
  useEffect(() => {
    templatesApi.list().then(r => setTemplates(r.data.data)).catch(() => {})
    productsApi.list().then(r => setProducts(r.data.data)).catch(() => {})
  }, [])

  const toggle = async (wf) => {
    await workflowsApi.update(wf.id, { is_active: !wf.is_active })
    load()
  }

  const del = async (id) => { if (window.confirm('Supprimer ce workflow ?')) { await workflowsApi.delete(id); load() } }

  const create = async () => {
    const payload = {
      ...form,
      actions: form.actions.map(a => ({ ...a, template_id: a.template_id ? +a.template_id : null }))
    }
    await workflowsApi.create(payload)
    setShowCreate(false)
    load()
  }

  const addAction = () => setForm(f => ({ ...f, actions: [...f.actions, { type: 'send_message', channel: 'whatsapp', template_id: '', delay_hours: 0 }] }))
  const updateAction = (i, k, v) => setForm(f => ({ ...f, actions: f.actions.map((a, idx) => idx === i ? { ...a, [k]: v } : a) }))
  const removeAction = (i) => setForm(f => ({ ...f, actions: f.actions.filter((_, idx) => idx !== i) }))

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-800">Workflows Automation</h1>
        <button onClick={() => setShowCreate(true)} className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-indigo-700">+ Nouveau workflow</button>
      </div>

      <div className="space-y-3">
        {workflows.map(wf => (
          <div key={wf.id} className="bg-white border rounded-xl p-4">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${wf.is_active ? 'bg-green-500' : 'bg-gray-300'}`} />
                  <span className="font-medium text-gray-800">{wf.nom}</span>
                  <span className="text-xs bg-indigo-50 text-indigo-600 px-2 py-0.5 rounded">{wf.product_code}</span>
                </div>
                <div className="mt-1 flex items-center gap-2 text-sm text-gray-500">
                  <span className="bg-amber-50 text-amber-700 px-2 py-0.5 rounded text-xs font-medium">⚡ {wf.trigger_event}</span>
                  <span>→</span>
                  <span className="text-xs">{wf.executions_count} exécutions</span>
                </div>
              </div>
              <div className="flex gap-2">
                <button onClick={() => toggle(wf)} className={`text-xs px-3 py-1 rounded ${wf.is_active ? 'bg-amber-100 text-amber-700 hover:bg-amber-200' : 'bg-green-100 text-green-700 hover:bg-green-200'}`}>
                  {wf.is_active ? 'Désactiver' : 'Activer'}
                </button>
                <button onClick={() => del(wf.id)} className="text-xs px-3 py-1 rounded bg-red-50 text-red-600 hover:bg-red-100">Suppr.</button>
              </div>
            </div>
          </div>
        ))}
        {workflows.length === 0 && <div className="text-center py-12 text-gray-400">Aucun workflow — créez votre première automatisation</div>}
      </div>

      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-lg space-y-4 max-h-screen overflow-auto">
            <h2 className="font-bold text-lg">Nouveau workflow</h2>

            <input className="w-full border rounded px-3 py-2 text-sm" placeholder="Nom *" value={form.nom} onChange={e => setForm(f => ({ ...f, nom: e.target.value }))} />

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-gray-500">Produit</label>
                <select className="w-full border rounded px-3 py-2 text-sm mt-1" value={form.product_code} onChange={e => setForm(f => ({ ...f, product_code: e.target.value }))}>
                  <option value="ALL">Tous les produits</option>
                  {products.map(p => <option key={p.code} value={p.code}>{p.nom}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs text-gray-500">Déclencheur</label>
                <select className="w-full border rounded px-3 py-2 text-sm mt-1" value={form.trigger_event} onChange={e => setForm(f => ({ ...f, trigger_event: e.target.value }))}>
                  {EVENTS.map(e => <option key={e} value={e}>{e}</option>)}
                </select>
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs font-medium text-gray-700">Actions ({form.actions.length})</label>
                <button onClick={addAction} className="text-xs text-indigo-600 hover:underline">+ Ajouter action</button>
              </div>
              <div className="space-y-2">
                {form.actions.map((a, i) => (
                  <div key={i} className="bg-gray-50 rounded p-3 space-y-2">
                    <div className="grid grid-cols-3 gap-2">
                      <select className="border rounded px-2 py-1 text-xs" value={a.channel} onChange={e => updateAction(i, 'channel', e.target.value)}>
                        {CHANNELS.map(c => <option key={c} value={c}>{c}</option>)}
                      </select>
                      <select className="border rounded px-2 py-1 text-xs" value={a.template_id} onChange={e => updateAction(i, 'template_id', e.target.value)}>
                        <option value="">-- Template --</option>
                        {templates.filter(t => t.channel === a.channel).map(t => <option key={t.id} value={t.id}>{t.nom}</option>)}
                      </select>
                      <input type="number" className="border rounded px-2 py-1 text-xs" placeholder="Délai (h)" value={a.delay_hours} onChange={e => updateAction(i, 'delay_hours', +e.target.value)} />
                    </div>
                    <button onClick={() => removeAction(i)} className="text-xs text-red-400 hover:text-red-600">Supprimer</button>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex gap-3 justify-end pt-2">
              <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-sm border rounded hover:bg-gray-50">Annuler</button>
              <button onClick={create} disabled={!form.nom} className="px-4 py-2 text-sm bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50">Créer</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
