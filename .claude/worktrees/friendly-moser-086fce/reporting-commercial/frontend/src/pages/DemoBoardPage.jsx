import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import axios from 'axios'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts'
import {
  TrendingUp, Users, ShoppingBag, FileText,
  AlertCircle, Loader2, RefreshCw, Bell, ChevronRight,
} from 'lucide-react'

const fmt    = (n) => new Intl.NumberFormat('fr-MA', { maximumFractionDigits: 0 }).format(n ?? 0)
const fmtMAD = (n) => {
  const v = n ?? 0
  if (v >= 1_000_000) return (v / 1_000_000).toFixed(2) + ' M'
  if (v >= 1_000)     return (v / 1_000).toFixed(1) + ' K'
  return fmt(v)
}

const COLORS = ['#2563eb','#7c3aed','#059669','#d97706','#dc2626','#0891b2','#65a30d','#9333ea','#e11d48','#0284c7']

// ── KPI Card (style identique au vrai OptiBoard) ─────────────────────────────
function KPICard({ label, value, sub, color, icon: Icon, trend }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-500">{label}</span>
        <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${color}`}>
          <Icon className="w-4 h-4 text-white" />
        </div>
      </div>
      <div>
        <p className="text-2xl font-bold text-gray-900">{value}</p>
        {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
      </div>
      {trend !== undefined && (
        <div className="flex items-center gap-1 text-xs text-emerald-600 font-medium">
          <TrendingUp className="w-3.5 h-3.5" />
          <span>Données Sage synchronisées</span>
        </div>
      )}
    </div>
  )
}

// ── Tooltip chart ─────────────────────────────────────────────────────────────
function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg px-3 py-2 text-sm">
      <p className="font-semibold text-gray-700 mb-1">{label}</p>
      <p className="text-blue-600 font-bold">{fmtMAD(payload[0]?.value)} MAD</p>
    </div>
  )
}

export default function DemoBoardPage() {
  const { token } = useParams()
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)
  const [refreshing, setRefreshing] = useState(false)
  const now = new Date().toLocaleTimeString('fr-MA', { hour: '2-digit', minute: '2-digit' })

  const load = (silent = false) => {
    if (!silent) setLoading(true)
    else setRefreshing(true)
    axios.get(`/api/demo/${token}/dashboard`)
      .then(r => { setData(r.data); setError(null) })
      .catch(e => {
        const s = e.response?.status
        if (s === 425) setError('La synchronisation n\'est pas encore terminée.')
        else if (s === 404) setError('Session de démonstration introuvable.')
        else if (s === 410) setError('Cette session a expiré.')
        else setError(e.response?.data?.detail || 'Erreur de chargement.')
      })
      .finally(() => { setLoading(false); setRefreshing(false) })
  }

  useEffect(() => { load() }, [token])

  // ── Loading ───────────────────────────────────────────────────────────────
  if (loading) return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <Loader2 className="w-10 h-10 text-blue-600 animate-spin mx-auto mb-3" />
        <p className="text-sm text-gray-500">Chargement du tableau de bord…</p>
      </div>
    </div>
  )

  // ── Error ─────────────────────────────────────────────────────────────────
  if (error) return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 gap-4">
      <AlertCircle className="w-12 h-12 text-red-400" />
      <p className="text-gray-700 font-medium">{error}</p>
      <Link to={`/demo/${token}`} className="text-sm text-blue-600 hover:underline">
        ← Retour au suivi de synchronisation
      </Link>
    </div>
  )

  const { kpis, ca_mensuel, top_clients, top_articles, societe } = data
  const moisLabel = { '2026-01': 'Janvier', '2026-02': 'Février' }
  const caChart = ca_mensuel.map(r => ({ ...r, label: moisLabel[r.mois] || r.mois }))
  const pieData = top_clients.slice(0, 6).map(c => ({ name: c.nom, value: c.ca }))

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">

      {/* ── Top Header (style vrai OptiBoard) ──────────────────────────────── */}
      <header className="bg-[#1e3a5f] text-white px-6 py-0 flex items-stretch">
        {/* Logo zone */}
        <div className="flex items-center gap-3 pr-8 border-r border-white/10 py-3">
          <div className="w-9 h-9 bg-white/10 rounded-lg flex items-center justify-center">
            <svg viewBox="0 0 24 24" fill="none" className="w-5 h-5 text-white" stroke="currentColor" strokeWidth={2}>
              <rect x="3" y="12" width="4" height="9" rx="1"/><rect x="10" y="8" width="4" height="13" rx="1"/><rect x="17" y="4" width="4" height="17" rx="1"/>
            </svg>
          </div>
          <div>
            <p className="font-bold text-white leading-none text-base">OptiBoard</p>
            <p className="text-[10px] text-white/50 leading-none mt-0.5">Reporting</p>
          </div>
        </div>

        {/* Breadcrumb */}
        <div className="flex items-center gap-2 px-6 text-sm text-white/60">
          <span className="text-white/40">Ventes</span>
          <ChevronRight className="w-3.5 h-3.5 text-white/30" />
          <span className="text-white font-medium">Chiffre d'Affaires</span>
        </div>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Démo badge + actions */}
        <div className="flex items-center gap-3 py-3">
          <span className="text-xs bg-amber-500/20 text-amber-300 border border-amber-500/30 font-medium px-2.5 py-1 rounded-full">
            Démo · {societe}
          </span>
          <button
            onClick={() => load(true)}
            className="w-8 h-8 rounded-lg bg-white/10 hover:bg-white/20 flex items-center justify-center transition-colors"
            title="Actualiser"
          >
            <RefreshCw className={`w-4 h-4 text-white/70 ${refreshing ? 'animate-spin' : ''}`} />
          </button>
          <button className="w-8 h-8 rounded-lg bg-white/10 flex items-center justify-center">
            <Bell className="w-4 h-4 text-white/70" />
          </button>
          <div className="w-8 h-8 rounded-lg bg-blue-500 flex items-center justify-center text-xs font-bold text-white">
            D
          </div>
        </div>
      </header>

      {/* ── Bandeau démo ───────────────────────────────────────────────────── */}
      <div className="bg-amber-50 border-b border-amber-200 px-6 py-2 flex items-center gap-2 text-xs text-amber-700">
        <span className="font-semibold">Environnement de démonstration</span>
        <span className="text-amber-500">·</span>
        <span>Données Sage extraites automatiquement · Période : Janvier – Février 2026</span>
        <Link to={`/demo/${token}`} className="ml-auto text-amber-600 hover:text-amber-800 font-medium hover:underline">
          ← Suivi synchronisation
        </Link>
      </div>

      {/* ── Contenu principal ──────────────────────────────────────────────── */}
      <main className="flex-1 p-6 space-y-6">

        {/* Titre section */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-gray-900">Chiffre d'Affaires Commercial</h1>
            <p className="text-sm text-gray-400 mt-0.5">Janvier – Février 2026 · Mis à jour à {now}</p>
          </div>
          <span className="text-xs bg-green-100 text-green-700 font-medium px-3 py-1 rounded-full border border-green-200">
            ✓ {fmt(kpis.nb_factures)} factures synchronisées
          </span>
        </div>

        {/* KPIs */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <KPICard label="Chiffre d'Affaires" value={`${fmtMAD(kpis.ca_total)} MAD`}
            sub="Jan – Fév 2026" color="bg-blue-600" icon={TrendingUp} trend={1} />
          <KPICard label="Factures émises" value={fmt(kpis.nb_factures)}
            sub="Tous documents" color="bg-violet-600" icon={FileText} />
          <KPICard label="Clients actifs" value={fmt(kpis.nb_clients)}
            sub="Avec facturation" color="bg-emerald-600" icon={Users} />
          <KPICard label="Références vendues" value={fmt(kpis.nb_articles)}
            sub="Articles distincts" color="bg-orange-500" icon={ShoppingBag} />
        </div>

        {/* Graphiques */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* CA mensuel — 2 colonnes */}
          <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 shadow-sm p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-gray-900">Évolution mensuelle du CA</h2>
              <span className="text-xs text-gray-400">MAD TTC</span>
            </div>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={caChart} barSize={72} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" vertical={false} />
                <XAxis dataKey="label" tick={{ fontSize: 13, fill: '#6b7280' }} axisLine={false} tickLine={false} />
                <YAxis tickFormatter={fmtMAD} tick={{ fontSize: 11, fill: '#9ca3af' }} axisLine={false} tickLine={false} />
                <Tooltip content={<ChartTooltip />} cursor={{ fill: '#f3f4f6' }} />
                <Bar dataKey="ca" fill="#2563eb" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Répartition clients — 1 colonne */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
            <h2 className="font-semibold text-gray-900 mb-4">Répartition par client</h2>
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" innerRadius={55} outerRadius={85}
                  paddingAngle={3} dataKey="value">
                  {pieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip formatter={(v) => [`${fmtMAD(v)} MAD`, 'CA']} />
                <Legend iconType="circle" iconSize={8}
                  formatter={(v) => <span className="text-xs text-gray-600">{v.length > 18 ? v.slice(0,18)+'…' : v}</span>}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Tables */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          {/* Top clients */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
            <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
              <h2 className="font-semibold text-gray-900 flex items-center gap-2">
                <Users className="w-4 h-4 text-violet-500" /> Top clients
              </h2>
              <span className="text-xs text-gray-400">{top_clients.length} clients</span>
            </div>
            <div className="divide-y divide-gray-50">
              {top_clients.map((c, i) => (
                <div key={c.code} className="flex items-center gap-3 px-5 py-3">
                  <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
                    i === 0 ? 'bg-yellow-100 text-yellow-700' :
                    i === 1 ? 'bg-gray-100 text-gray-600' :
                    i === 2 ? 'bg-orange-100 text-orange-600' : 'bg-gray-50 text-gray-400'
                  }`}>{i + 1}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-800 truncate">{c.nom}</p>
                    <div className="w-full bg-gray-100 rounded-full h-1 mt-1.5">
                      <div className="bg-violet-500 h-1 rounded-full transition-all"
                        style={{ width: `${Math.min(100, (c.ca / (top_clients[0]?.ca || 1)) * 100)}%` }} />
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-sm font-bold text-gray-800">{fmtMAD(c.ca)}</p>
                    <p className="text-[10px] text-gray-400">MAD</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Top articles */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
            <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
              <h2 className="font-semibold text-gray-900 flex items-center gap-2">
                <ShoppingBag className="w-4 h-4 text-orange-500" /> Top articles
              </h2>
              <span className="text-xs text-gray-400">{top_articles.length} articles</span>
            </div>
            <div className="divide-y divide-gray-50">
              {top_articles.map((a, i) => (
                <div key={a.ref} className="flex items-center gap-3 px-5 py-3">
                  <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
                    i === 0 ? 'bg-yellow-100 text-yellow-700' :
                    i === 1 ? 'bg-gray-100 text-gray-600' :
                    i === 2 ? 'bg-orange-100 text-orange-600' : 'bg-gray-50 text-gray-400'
                  }`}>{i + 1}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-800 truncate">{a.designation || a.ref}</p>
                    <div className="w-full bg-gray-100 rounded-full h-1 mt-1.5">
                      <div className="bg-orange-500 h-1 rounded-full transition-all"
                        style={{ width: `${Math.min(100, (a.ca / (top_articles[0]?.ca || 1)) * 100)}%` }} />
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-sm font-bold text-gray-800">{fmtMAD(a.ca)}</p>
                    <p className="text-[10px] text-gray-400">{fmt(a.qte)} u.</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between text-xs text-gray-400 pb-2">
          <span>OptiBoard Démo · {societe} · Données Sage Jan – Fév 2026</span>
          <span>© 2026 KASoft</span>
        </div>
      </main>
    </div>
  )
}
