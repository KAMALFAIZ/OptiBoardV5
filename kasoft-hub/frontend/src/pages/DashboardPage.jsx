import React, { useEffect, useState } from 'react'
import { analyticsApi, productsApi } from '../services/api'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'

const KPICard = ({ label, value, sub, color = 'indigo' }) => {
  const colors = {
    indigo: 'bg-indigo-50 border-indigo-200 text-indigo-700',
    green:  'bg-green-50  border-green-200  text-green-700',
    red:    'bg-red-50    border-red-200    text-red-700',
    amber:  'bg-amber-50  border-amber-200  text-amber-700',
  }
  return (
    <div className={`rounded-xl border p-4 ${colors[color]}`}>
      <div className="text-2xl font-bold">{value ?? '—'}</div>
      <div className="text-sm font-medium">{label}</div>
      {sub && <div className="text-xs opacity-70 mt-1">{sub}</div>}
    </div>
  )
}

const PRODUCT_COLORS = ['#059669', '#F59E0B', '#3B82F6', '#8B5CF6']

export default function DashboardPage() {
  const [kpis, setKpis] = useState(null)
  const [byProduct, setByProduct] = useState([])
  const [ticketsByProduct, setTicketsByProduct] = useState([])
  const [evolution, setEvolution] = useState([])

  useEffect(() => {
    analyticsApi.dashboard().then(r => setKpis(r.data.data)).catch(() => {})
    analyticsApi.contactsByProduct().then(r => setByProduct(r.data.data)).catch(() => {})
    analyticsApi.ticketsByProduct().then(r => setTicketsByProduct(r.data.data)).catch(() => {})
    analyticsApi.contactsEvolution().then(r => setEvolution(r.data.data)).catch(() => {})
  }, [])

  const c = kpis?.contacts || {}
  const t = kpis?.tickets  || {}
  const d = kpis?.deliveries || {}

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold text-gray-800">Dashboard</h1>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPICard label="Contacts total" value={c.total} sub={`+${c.today || 0} aujourd'hui`} color="indigo" />
        <KPICard label="Tickets ouverts" value={t.open_count} sub={`${t.overdue_count || 0} en retard`} color={t.overdue_count > 0 ? 'red' : 'green'} />
        <KPICard label="Campagnes actives" value={kpis?.campaigns?.active_count} color="amber" />
        <KPICard label="Messages envoyés" value={d.sent_count} sub={`${d.today_count || 0} aujourd'hui`} color="green" />
      </div>

      {/* Funnel contacts */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border p-4">
          <div className="text-xs text-gray-500 mb-2">Prospects</div>
          <div className="text-3xl font-bold text-indigo-600">{c.prospects || 0}</div>
        </div>
        <div className="bg-white rounded-xl border p-4">
          <div className="text-xs text-gray-500 mb-2">Leads</div>
          <div className="text-3xl font-bold text-amber-600">{c.leads || 0}</div>
        </div>
        <div className="bg-white rounded-xl border p-4">
          <div className="text-xs text-gray-500 mb-2">Clients</div>
          <div className="text-3xl font-bold text-green-600">{c.clients || 0}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Évolution contacts */}
        <div className="bg-white rounded-xl border p-4">
          <h2 className="font-semibold mb-3 text-gray-700">Contacts — 30 derniers jours</h2>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={evolution}>
              <XAxis dataKey="date" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Bar dataKey="count" fill="#6366f1" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Par produit */}
        <div className="bg-white rounded-xl border p-4">
          <h2 className="font-semibold mb-3 text-gray-700">Contacts par produit</h2>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={byProduct} dataKey="total" nameKey="product_nom" cx="50%" cy="50%" outerRadius={80} label={({ product_nom, percent }) => `${product_nom} ${(percent * 100).toFixed(0)}%`}>
                {byProduct.map((_, i) => <Cell key={i} fill={PRODUCT_COLORS[i % PRODUCT_COLORS.length]} />)}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Tickets par produit */}
      <div className="bg-white rounded-xl border p-4">
        <h2 className="font-semibold mb-3 text-gray-700">Tickets SAV par produit</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {ticketsByProduct.map((p, i) => (
            <div key={p.product_code} className="text-center p-3 rounded-lg" style={{ background: PRODUCT_COLORS[i % 4] + '20', borderLeft: `4px solid ${PRODUCT_COLORS[i % 4]}` }}>
              <div className="font-bold text-xl">{p.open_count || 0}</div>
              <div className="text-sm">{p.product_nom}</div>
              {p.overdue_count > 0 && <div className="text-xs text-red-600">{p.overdue_count} en retard</div>}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
