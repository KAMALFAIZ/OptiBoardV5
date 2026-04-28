/**
 * AIDeckBuilder — Générateur de présentations interactives basées sur les données DWH.
 * Phase 1 : saisie de la demande libre
 * Phase 2 : révision du plan de slides
 * Phase 3 : éditeur slide par slide (viz recharts + narration IA + chat par slide)
 */
import { useState, useEffect, useRef, useCallback } from 'react'
import {
  Sparkles, ChevronLeft, ChevronRight, ChevronDown, ChevronUp,
  Plus, Trash2, Send, Loader2, RefreshCw, AlertCircle, X,
  MessageSquare, BarChart2, Table2, Eye, Grid3X3, Check,
} from 'lucide-react'
import {
  BarChart, Bar, LineChart, Line, AreaChart, Area,
  PieChart as RechartsPieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer, Legend,
} from 'recharts'
import api from '../services/api'

const COLORS = ['#6366f1', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#3b82f6', '#ef4444', '#06b6d4']

const VIZ_LABEL = { chart: 'Graphique', grid: 'Tableau', pivot: 'Pivot', none: 'Texte' }
const VIZ_COLOR = {
  chart: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  grid:  'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  pivot: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  none:  'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400',
}
const STATUS_DOT = {
  pending:    'bg-gray-300 dark:bg-gray-600',
  generating: 'bg-yellow-400 animate-pulse',
  ready:      'bg-green-500',
  error:      'bg-red-500',
}
const STATUS_LABEL = { pending: 'En attente', generating: 'En cours…', ready: 'Prêt', error: 'Erreur' }
const STATUS_CLASS = {
  ready:      'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  generating: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  error:      'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  pending:    'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400',
}

// ─── SlideViz ────────────────────────────────────────────────────────────────
function SlideViz({ slide }) {
  const { data = [], columns = [], viz_type, chart_type } = slide

  if (viz_type === 'none' || !data.length) {
    return (
      <div className="flex flex-col items-center justify-center h-44 rounded-xl bg-gray-50 dark:bg-gray-800/60 border-2 border-dashed border-gray-200 dark:border-gray-700 text-gray-400">
        <BarChart2 className="w-7 h-7 mb-2 opacity-40" />
        <span className="text-xs">{viz_type === 'none' ? 'Slide texte — aucune visualisation' : 'Données non encore générées'}</span>
      </div>
    )
  }

  if (viz_type === 'grid') {
    return (
      <div className="overflow-auto max-h-52 rounded-lg border border-gray-200 dark:border-gray-700 text-xs">
        <table className="w-full">
          <thead className="bg-gray-100 dark:bg-gray-800 sticky top-0">
            <tr>
              {columns.map(c => (
                <th key={c} className="px-3 py-2 text-left text-gray-600 dark:text-gray-400 font-semibold whitespace-nowrap">
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.slice(0, 15).map((row, i) => (
              <tr key={i} className={i % 2 === 0 ? 'bg-white dark:bg-gray-900' : 'bg-gray-50 dark:bg-gray-800/50'}>
                {columns.map(c => (
                  <td key={c} className="px-3 py-1.5 text-gray-700 dark:text-gray-300 whitespace-nowrap">
                    {row[c] != null ? String(row[c]) : '—'}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }

  // Chart
  const numCols = columns.filter(c => typeof data[0]?.[c] === 'number')
  const textCols = columns.filter(c => !numCols.includes(c))
  const xKey = textCols[0] || columns[0]
  const yKeys = numCols.slice(0, 4)
  const chartData = data.slice(0, 20)
  const fmt = v => (String(v).length > 13 ? String(v).slice(0, 13) + '…' : String(v))

  if (chart_type === 'pie' && yKeys.length > 0) {
    const pieData = chartData.map(d => ({ name: String(d[xKey] ?? ''), value: Number(d[yKeys[0]] ?? 0) }))
    return (
      <ResponsiveContainer width="100%" height={260}>
        <RechartsPieChart>
          <Pie
            data={pieData} dataKey="value" nameKey="name"
            cx="50%" cy="50%" outerRadius={90}
            label={({ name, percent }) => `${String(name).slice(0, 10)} ${(percent * 100).toFixed(0)}%`}
            labelLine={false}
          >
            {pieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
          </Pie>
          <Tooltip formatter={(v) => new Intl.NumberFormat('fr-FR').format(v)} />
        </RechartsPieChart>
      </ResponsiveContainer>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={260}>
      {chart_type === 'line' ? (
        <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 30, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
          <XAxis dataKey={xKey} tickFormatter={fmt} tick={{ fontSize: 10 }} angle={-25} textAnchor="end" interval="preserveStartEnd" />
          <YAxis tick={{ fontSize: 10 }} />
          <Tooltip formatter={(v) => new Intl.NumberFormat('fr-FR').format(v)} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          {yKeys.map((key, i) => (
            <Line key={key} type="monotone" dataKey={key} stroke={COLORS[i]} strokeWidth={2} dot={false} />
          ))}
        </LineChart>
      ) : chart_type === 'area' ? (
        <AreaChart data={chartData} margin={{ top: 5, right: 20, bottom: 30, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
          <XAxis dataKey={xKey} tickFormatter={fmt} tick={{ fontSize: 10 }} angle={-25} textAnchor="end" interval="preserveStartEnd" />
          <YAxis tick={{ fontSize: 10 }} />
          <Tooltip formatter={(v) => new Intl.NumberFormat('fr-FR').format(v)} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          {yKeys.map((key, i) => (
            <Area key={key} type="monotone" dataKey={key} stroke={COLORS[i]} fill={COLORS[i]} fillOpacity={0.18} strokeWidth={2} />
          ))}
        </AreaChart>
      ) : (
        <BarChart data={chartData} margin={{ top: 5, right: 20, bottom: 30, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
          <XAxis dataKey={xKey} tickFormatter={fmt} tick={{ fontSize: 10 }} angle={-25} textAnchor="end" interval="preserveStartEnd" />
          <YAxis tick={{ fontSize: 10 }} />
          <Tooltip formatter={(v) => new Intl.NumberFormat('fr-FR').format(v)} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          {yKeys.map((key, i) => (
            <Bar key={key} dataKey={key} fill={COLORS[i]} radius={[3, 3, 0, 0]} />
          ))}
        </BarChart>
      )}
    </ResponsiveContainer>
  )
}

// ─── Phase 1 : Request input ──────────────────────────────────────────────────
function Phase1({ onPlan, loading, initialRequest }) {
  const [request, setRequest] = useState(initialRequest || '')
  const examples = [
    'Présentation mensuelle des ventes par commercial et par région',
    'Bilan annuel pour le CODIR : CA, marges et recouvrement',
    'Analyse du recouvrement : retards, DSO et balance âgée clients',
    'Revue des stocks : ruptures, dormants et rotations lentes',
  ]

  return (
    <div className="flex flex-col items-center justify-center min-h-[75vh] p-6">
      <div className="w-full max-w-2xl">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 mb-4 shadow-lg">
            <Sparkles className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-1">OptiBoard Deck IA</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Décrivez votre présentation — l'IA crée le plan, charge les données réelles et rédige les analyses
          </p>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg border border-gray-200 dark:border-gray-700 p-5">
          <textarea
            value={request}
            onChange={e => setRequest(e.target.value)}
            placeholder="Ex : Prépare une présentation mensuelle pour la direction avec les ventes par commercial, l'état du recouvrement et les stocks critiques…"
            rows={5}
            className="w-full resize-none rounded-xl border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white p-4 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 placeholder-gray-400 dark:placeholder-gray-600"
          />

          <div className="flex flex-wrap gap-2 mt-3 mb-4">
            <span className="text-xs text-gray-400 self-center mr-1">Exemples :</span>
            {examples.map((ex, i) => (
              <button
                key={i}
                onClick={() => setRequest(ex)}
                className="text-xs px-3 py-1.5 rounded-full bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-100 dark:hover:bg-indigo-900/50 transition-colors border border-indigo-100 dark:border-indigo-800"
              >
                {ex}
              </button>
            ))}
          </div>

          <button
            onClick={() => onPlan(request)}
            disabled={!request.trim() || loading}
            className="w-full flex items-center justify-center gap-2 py-3 px-6 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 text-white font-semibold hover:from-indigo-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-md hover:shadow-lg text-sm"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            {loading ? 'Génération du plan en cours…' : 'Créer la présentation'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Phase 2 : Plan review ────────────────────────────────────────────────────
function Phase2({ plan, onBack, onStart, onChange }) {
  const { deck_title, slides } = plan

  const moveSlide = (idx, dir) => {
    const next = [...slides]
    ;[next[idx], next[idx + dir]] = [next[idx + dir], next[idx]]
    onChange({ ...plan, slides: next })
  }

  const deleteSlide = idx => onChange({ ...plan, slides: slides.filter((_, i) => i !== idx) })

  const addSlide = () =>
    onChange({
      ...plan,
      slides: [
        ...slides,
        {
          title: 'Nouveau slide', description: '', datasource_id: null,
          viz_type: 'none', chart_type: null, focus: '',
          status: 'pending', narration: '', recommendation: '', data: [], columns: [], chat: [], notes: '',
        },
      ],
    })

  return (
    <div className="max-w-2xl mx-auto py-6 px-4">
      <div className="flex items-center gap-3 mb-6">
        <button
          onClick={onBack}
          className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 transition-colors"
        >
          <ChevronLeft className="w-5 h-5" />
        </button>
        <div className="flex-1">
          <h2 className="text-lg font-bold text-gray-900 dark:text-white">{deck_title}</h2>
          <p className="text-xs text-gray-500">{slides.length} slides · Réorganisez et ajustez le plan avant de générer</p>
        </div>
        <button
          onClick={onStart}
          disabled={slides.length === 0}
          className="flex items-center gap-2 px-5 py-2 rounded-xl bg-indigo-600 text-white font-semibold hover:bg-indigo-700 transition-colors shadow-md text-sm disabled:opacity-50"
        >
          Générer <ChevronRight className="w-4 h-4" />
        </button>
      </div>

      <div className="space-y-2">
        {slides.map((slide, idx) => (
          <div
            key={idx}
            className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-3.5 flex items-center gap-3"
          >
            <span className="w-6 h-6 rounded-full bg-indigo-100 dark:bg-indigo-900/50 text-indigo-600 dark:text-indigo-400 flex items-center justify-center text-xs font-bold shrink-0">
              {idx + 1}
            </span>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-gray-900 dark:text-white truncate">{slide.title}</p>
              <p className="text-xs text-gray-500 truncate">{slide.description}</p>
            </div>
            <div className="flex items-center gap-1 shrink-0">
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${VIZ_COLOR[slide.viz_type] || VIZ_COLOR.none}`}>
                {VIZ_LABEL[slide.viz_type] || slide.viz_type}
                {slide.chart_type ? ` · ${slide.chart_type}` : ''}
              </span>
              <button onClick={() => moveSlide(idx, -1)} disabled={idx === 0}
                className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-30 transition-colors">
                <ChevronUp className="w-4 h-4 text-gray-500" />
              </button>
              <button onClick={() => moveSlide(idx, 1)} disabled={idx === slides.length - 1}
                className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-30 transition-colors">
                <ChevronDown className="w-4 h-4 text-gray-500" />
              </button>
              <button onClick={() => deleteSlide(idx)}
                className="p-1 rounded hover:bg-red-50 dark:hover:bg-red-900/20 text-gray-400 hover:text-red-500 transition-colors">
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>
        ))}
      </div>

      <button
        onClick={addSlide}
        className="mt-3 w-full py-2.5 rounded-xl border-2 border-dashed border-gray-300 dark:border-gray-600 text-gray-500 hover:border-indigo-400 hover:text-indigo-500 transition-colors flex items-center justify-center gap-2 text-sm"
      >
        <Plus className="w-4 h-4" /> Ajouter un slide
      </button>
    </div>
  )
}

// ─── SlideEditor (Phase 3 detail view) ───────────────────────────────────────
function SlideEditor({ slide, slideIdx, totalSlides, deckId, onUpdate, onGenerate, onPrev, onNext }) {
  const [chatOpen, setChatOpen] = useState(false)
  const [chatInput, setChatInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const chatEndRef = useRef(null)

  useEffect(() => {
    if (chatOpen && chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [slide.chat, chatOpen])

  const sendChat = async () => {
    if (!chatInput.trim() || !deckId || chatLoading) return
    const msg = chatInput.trim()
    setChatInput('')
    setChatLoading(true)

    const history = slide.chat || []
    const newHistory = [...history, { role: 'user', content: msg }]
    onUpdate({ ...slide, chat: newHistory })

    try {
      const res = await api.post(`/ai/deck/${deckId}/slide/${slideIdx}/chat`, {
        message: msg,
        chat_history: history,
      })
      const updatedSlide = res.data.slide
        ? { ...res.data.slide, chat: [...newHistory, { role: 'assistant', content: res.data.reply }] }
        : { ...slide, chat: [...newHistory, { role: 'assistant', content: res.data.reply }] }
      onUpdate(updatedSlide)
    } catch {
      onUpdate({ ...slide, chat: [...newHistory, { role: 'assistant', content: "Désolé, une erreur s'est produite." }] })
    } finally {
      setChatLoading(false)
    }
  }

  const isGenerating = slide.status === 'generating'
  const isReady = slide.status === 'ready'

  return (
    <div className="space-y-4">
      {/* Slide header */}
      <div className="flex items-start gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-medium text-gray-400 uppercase tracking-wide">
              Slide {slideIdx + 1} / {totalSlides}
            </span>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_CLASS[slide.status] || STATUS_CLASS.pending}`}>
              {isReady && <Check className="w-3 h-3 inline mr-0.5" />}
              {isGenerating && <Loader2 className="w-3 h-3 inline mr-0.5 animate-spin" />}
              {STATUS_LABEL[slide.status] || slide.status}
            </span>
          </div>
          <h2 className="text-xl font-bold text-gray-900 dark:text-white leading-tight">{slide.title}</h2>
          {slide.description && (
            <p className="text-sm text-gray-500 mt-0.5">{slide.description}</p>
          )}
          {slide.focus && (
            <p className="text-xs text-indigo-500 dark:text-indigo-400 mt-1 italic">Angle : {slide.focus}</p>
          )}
        </div>
        <button
          onClick={onGenerate}
          disabled={isGenerating || !deckId}
          className="shrink-0 flex items-center gap-1.5 px-4 py-2 rounded-xl bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isGenerating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
          {isReady ? 'Regénérer' : 'Générer'}
        </button>
      </div>

      {/* Visualization */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <BarChart2 className="w-4 h-4 text-indigo-500" />
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Visualisation</h3>
            <span className={`text-xs px-2 py-0.5 rounded-full ${VIZ_COLOR[slide.viz_type] || VIZ_COLOR.none}`}>
              {VIZ_LABEL[slide.viz_type] || slide.viz_type}
              {slide.chart_type ? ` · ${slide.chart_type}` : ''}
            </span>
          </div>
          {slide.data?.length > 0 && (
            <span className="text-xs text-gray-400">{slide.data.length} lignes · {slide.columns?.length} colonnes</span>
          )}
        </div>
        <SlideViz slide={slide} />
      </div>

      {/* Narration */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">Analyse & Narration</h3>
        <textarea
          value={slide.narration || ''}
          onChange={e => onUpdate({ ...slide, narration: e.target.value })}
          placeholder={isReady ? '' : 'La narration générée par l\'IA apparaîtra ici après la génération. Vous pouvez l\'éditer librement.'}
          rows={4}
          className="w-full resize-none bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-600 p-3 text-sm text-gray-700 dark:text-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 placeholder-gray-400 dark:placeholder-gray-600 leading-relaxed"
        />
      </div>

      {/* Recommendation */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">Recommandation</h3>
        <textarea
          value={slide.recommendation || ''}
          onChange={e => onUpdate({ ...slide, recommendation: e.target.value })}
          placeholder="La recommandation actionnable générée par l'IA…"
          rows={2}
          className="w-full resize-none bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-600 p-3 text-sm text-gray-700 dark:text-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 placeholder-gray-400 dark:placeholder-gray-600"
        />
      </div>

      {/* Chat */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <button
          onClick={() => setChatOpen(o => !o)}
          className="w-full flex items-center justify-between p-4 text-left hover:bg-gray-50 dark:hover:bg-gray-750 transition-colors"
        >
          <div className="flex items-center gap-2">
            <MessageSquare className="w-4 h-4 text-indigo-500" />
            <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">Affiner avec l'IA</span>
            {(slide.chat?.length || 0) > 0 && (
              <span className="text-xs bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 px-2 py-0.5 rounded-full">
                {slide.chat.length}
              </span>
            )}
          </div>
          <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform duration-200 ${chatOpen ? 'rotate-180' : ''}`} />
        </button>

        {chatOpen && (
          <div className="px-4 pb-4 border-t border-gray-100 dark:border-gray-700">
            <div className="max-h-52 overflow-y-auto py-3 space-y-2">
              {(slide.chat || []).length === 0 && (
                <p className="text-xs text-gray-400 text-center py-4 italic">
                  Demandez à l'IA : modifier la narration, changer le type de graphique, simplifier le texte, analyser une tendance…
                </p>
              )}
              {(slide.chat || []).map((msg, i) => (
                <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[80%] text-xs px-3 py-2 rounded-xl leading-relaxed ${
                    msg.role === 'user'
                      ? 'bg-indigo-600 text-white'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
                  }`}>
                    {msg.content}
                  </div>
                </div>
              ))}
              {chatLoading && (
                <div className="flex justify-start">
                  <div className="bg-gray-100 dark:bg-gray-700 text-gray-400 text-xs px-3 py-2 rounded-xl flex items-center gap-1.5">
                    <Loader2 className="w-3 h-3 animate-spin" /> En train de réfléchir…
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            <div className="flex gap-2 mt-1">
              <input
                value={chatInput}
                onChange={e => setChatInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChat() } }}
                placeholder="Ex: Passe en graphique courbes, simplifie la narration…"
                className="flex-1 text-xs px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 placeholder-gray-400 dark:placeholder-gray-600"
              />
              <button
                onClick={sendChat}
                disabled={!chatInput.trim() || chatLoading || !deckId}
                className="p-2 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50 transition-colors"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Navigation */}
      <div className="flex justify-between pt-1 pb-6">
        <button
          onClick={onPrev}
          disabled={slideIdx === 0}
          className="flex items-center gap-1.5 px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-30 transition-colors"
        >
          <ChevronLeft className="w-4 h-4" /> Précédent
        </button>
        <button
          onClick={onNext}
          disabled={slideIdx === totalSlides - 1}
          className="flex items-center gap-1.5 px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-30 transition-colors"
        >
          Suivant <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}

// ─── Phase 3 : Editor ─────────────────────────────────────────────────────────
function Phase3({ deckId, slides, setSlides, deckTitle, userRequest, onBack }) {
  const [activeIdx, setActiveIdx] = useState(0)
  const [overviewMode, setOverviewMode] = useState(false)
  const [generatingAll, setGeneratingAll] = useState(false)
  const saveTimerRef = useRef(null)
  const topRef = useRef(null)

  // Debounced auto-save to DB
  const scheduleAutoSave = useCallback((updatedSlides) => {
    if (!deckId) return
    clearTimeout(saveTimerRef.current)
    saveTimerRef.current = setTimeout(() => {
      api.put(`/ai/deck/${deckId}`, { slides: updatedSlides }).catch(() => {})
    }, 1500)
  }, [deckId])

  const updateSlide = useCallback((idx, updatedSlide) => {
    setSlides(prev => {
      const copy = [...prev]
      copy[idx] = updatedSlide
      scheduleAutoSave(copy)
      return copy
    })
  }, [setSlides, scheduleAutoSave])

  const generateSlide = useCallback(async (idx) => {
    if (!deckId) return
    setSlides(prev => {
      const copy = [...prev]
      copy[idx] = { ...copy[idx], status: 'generating' }
      return copy
    })
    try {
      const res = await api.post(`/ai/deck/${deckId}/slide/${idx}/generate`)
      setSlides(prev => {
        const copy = [...prev]
        copy[idx] = { ...res.data.slide, status: 'ready', chat: copy[idx].chat || [] }
        return copy
      })
    } catch {
      setSlides(prev => {
        const copy = [...prev]
        copy[idx] = { ...copy[idx], status: 'error' }
        return copy
      })
    }
  }, [deckId, setSlides])

  const generateAll = async () => {
    setGeneratingAll(true)
    setOverviewMode(false)
    for (let i = 0; i < slides.length; i++) {
      if (slides[i].status !== 'ready') {
        setActiveIdx(i)
        topRef.current?.scrollIntoView({ behavior: 'smooth' })
        await generateSlide(i)
      }
    }
    setGeneratingAll(false)
  }

  const goTo = (idx) => {
    setActiveIdx(idx)
    setOverviewMode(false)
    setTimeout(() => topRef.current?.scrollIntoView({ behavior: 'smooth' }), 50)
  }

  const readyCount = slides.filter(s => s.status === 'ready').length

  // ── Overview mode ──
  if (overviewMode) {
    return (
      <div className="space-y-5">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-gray-900 dark:text-white">{deckTitle}</h2>
            <p className="text-xs text-gray-500">{readyCount}/{slides.length} slides générés</p>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={generateAll} disabled={generatingAll}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-indigo-600 text-white text-sm hover:bg-indigo-700 disabled:opacity-50 transition-colors">
              {generatingAll ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
              Tout générer
            </button>
            <button onClick={() => setOverviewMode(false)}
              className="px-4 py-2 rounded-xl border border-gray-200 dark:border-gray-700 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
              Éditeur
            </button>
          </div>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
          {slides.map((slide, idx) => (
            <div
              key={idx}
              onClick={() => goTo(idx)}
              className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 cursor-pointer hover:border-indigo-400 dark:hover:border-indigo-500 hover:shadow-md transition-all group"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold text-gray-400">#{idx + 1}</span>
                <span className={`w-2.5 h-2.5 rounded-full ${STATUS_DOT[slide.status] || STATUS_DOT.pending}`} />
              </div>
              <p className="text-sm font-semibold text-gray-900 dark:text-white line-clamp-2 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                {slide.title}
              </p>
              <p className="text-xs text-gray-500 mt-1 line-clamp-2">
                {slide.narration || slide.description || <span className="italic text-gray-400">Non généré</span>}
              </p>
              {slide.status === 'ready' && slide.data?.length > 0 && (
                <div className="mt-2 h-16 pointer-events-none opacity-75">
                  <SlideViz slide={slide} />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    )
  }

  // ── Editor mode ──
  return (
    <div ref={topRef}>
      {/* Top bar */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2 min-w-0">
          <button onClick={onBack} className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 shrink-0">
            <ChevronLeft className="w-4 h-4" />
          </button>
          <div className="min-w-0">
            <h2 className="text-base font-bold text-gray-900 dark:text-white truncate">{deckTitle}</h2>
            <p className="text-xs text-gray-500">{readyCount}/{slides.length} générés</p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() => setOverviewMode(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-200 dark:border-gray-700 text-xs text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <Grid3X3 className="w-3.5 h-3.5" /> Vue d'ensemble
          </button>
          <button
            onClick={generateAll}
            disabled={generatingAll}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 text-white text-xs hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            {generatingAll ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
            Tout générer
          </button>
        </div>
      </div>

      {/* Slide strip */}
      <div className="flex gap-2 overflow-x-auto pb-2 mb-4 scrollbar-thin">
        {slides.map((slide, idx) => (
          <button
            key={idx}
            onClick={() => goTo(idx)}
            className={`shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeIdx === idx
                ? 'bg-indigo-600 text-white shadow-md'
                : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:border-indigo-400 dark:hover:border-indigo-500'
            }`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${activeIdx === idx ? 'bg-white/60' : (STATUS_DOT[slide.status] || STATUS_DOT.pending)}`} />
            <span className="max-w-[120px] truncate">{idx + 1}. {slide.title}</span>
          </button>
        ))}
      </div>

      {/* Active slide editor */}
      {slides[activeIdx] && (
        <div className="max-w-3xl mx-auto">
          <SlideEditor
            slide={slides[activeIdx]}
            slideIdx={activeIdx}
            totalSlides={slides.length}
            deckId={deckId}
            onUpdate={updated => updateSlide(activeIdx, updated)}
            onGenerate={() => generateSlide(activeIdx)}
            onPrev={() => goTo(Math.max(0, activeIdx - 1))}
            onNext={() => goTo(Math.min(slides.length - 1, activeIdx + 1))}
          />
        </div>
      )}
    </div>
  )
}

// ─── Main AIDeckBuilder ───────────────────────────────────────────────────────
export default function AIDeckBuilder() {
  const [phase, setPhase] = useState(1)
  const [planLoading, setPlanLoading] = useState(false)
  const [plan, setPlan] = useState(null)
  const [deckId, setDeckId] = useState(null)
  const [slides, setSlides] = useState([])
  const [deckTitle, setDeckTitle] = useState('')
  const [userRequest, setUserRequest] = useState('')
  const [error, setError] = useState(null)
  const [startLoading, setStartLoading] = useState(false)

  const handlePlan = async (request) => {
    if (!request.trim()) return
    setUserRequest(request)
    setPlanLoading(true)
    setError(null)
    try {
      const res = await api.post('/ai/deck/plan', { user_request: request })
      setPlan(res.data.plan)
      setPhase(2)
    } catch (e) {
      setError(e.response?.data?.detail || 'Erreur lors de la génération du plan. Vérifiez la configuration IA.')
    } finally {
      setPlanLoading(false)
    }
  }

  const handleStart = async () => {
    setStartLoading(true)
    setError(null)
    try {
      const res = await api.post('/ai/deck', {
        title: plan.deck_title,
        user_request: userRequest,
        slides: plan.slides,
      })
      setDeckId(res.data.deck_id)
      setSlides(plan.slides.map(s => ({ ...s, status: 'pending', chat: [], data: [], columns: [] })))
      setDeckTitle(plan.deck_title)
      setPhase(3)
    } catch (e) {
      setError(e.response?.data?.detail || 'Erreur lors de la sauvegarde du deck.')
    } finally {
      setStartLoading(false)
    }
  }

  return (
    <div className="relative">
      {/* Toast error */}
      {error && (
        <div className="fixed top-4 right-4 z-50 flex items-center gap-2 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700 text-red-700 dark:text-red-400 px-4 py-3 rounded-xl shadow-lg text-sm max-w-sm">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span className="flex-1">{error}</span>
          <button onClick={() => setError(null)} className="shrink-0 hover:opacity-70">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {phase === 1 && (
        <Phase1 onPlan={handlePlan} loading={planLoading} initialRequest={userRequest} />
      )}

      {phase === 2 && plan && (
        <Phase2
          plan={plan}
          onBack={() => setPhase(1)}
          onStart={handleStart}
          onChange={setPlan}
        />
      )}

      {phase === 3 && (
        <Phase3
          deckId={deckId}
          slides={slides}
          setSlides={setSlides}
          deckTitle={deckTitle}
          userRequest={userRequest}
          onBack={() => setPhase(2)}
        />
      )}

      {startLoading && (
        <div className="fixed inset-0 z-40 bg-black/20 dark:bg-black/40 flex items-center justify-center">
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-6 flex flex-col items-center gap-3">
            <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
            <p className="text-sm text-gray-600 dark:text-gray-400">Sauvegarde du deck…</p>
          </div>
        </div>
      )}
    </div>
  )
}
