import { useState, useRef, useCallback } from 'react'
import {
  FileText, X, RefreshCw, Copy, Printer, Sparkles,
  CheckCircle, AlertCircle, ChevronDown, ChevronUp, Loader2
} from 'lucide-react'
import api from '../../services/api'

/**
 * Modal de Résumé Exécutif IA.
 * Props:
 *   reportType, reportId, reportNom  — identification du rapport
 *   data                             — données brutes (array)
 *   columnsInfo                      — config colonnes
 *   period, entity                   — contexte optionnel
 */
export default function ExecutiveSummaryModal({ reportType, reportId, reportNom, data, columnsInfo, period, entity }) {
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState(null)
  const [copied, setCopied] = useState(false)
  const [expandedSections, setExpandedSections] = useState({})
  const printRef = useRef(null)

  const generate = useCallback(async (forceRefresh = false) => {
    if (!data || data.length === 0) {
      setError('Aucune donnée disponible')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const res = await api.post('/ai-summary/generate', {
        report_type: reportType,
        report_id: reportId,
        report_nom: reportNom,
        data: data.slice(0, 500),
        columns_info: columnsInfo || [],
        period: period || null,
        entity: entity || null,
        force_refresh: forceRefresh
      })
      if (res.data.success) {
        setSummary(res.data)
        // Tout déplier par défaut
        const expanded = {}
        res.data.sections?.forEach(s => { expanded[s.id] = true })
        setExpandedSections(expanded)
      } else {
        setError(res.data.error || 'Erreur de génération')
      }
    } catch (e) {
      setError(e.response?.data?.detail || 'Erreur de connexion')
    } finally {
      setLoading(false)
    }
  }, [reportType, reportId, reportNom, data, columnsInfo, period, entity])

  const handleOpen = () => {
    setOpen(true)
    if (!summary && !loading) generate()
  }

  const handleCopy = () => {
    if (!summary) return
    let text = `${summary.titre}\nGénéré le ${summary.date_generation}\n\n`
    summary.sections?.forEach(s => {
      text += `${s.titre}\n${'─'.repeat(40)}\n${s.contenu}\n\n`
    })
    if (summary.kpis_cles?.length > 0) {
      text += `KPIs Clés\n${'─'.repeat(40)}\n`
      summary.kpis_cles.forEach(k => {
        text += `• ${k.label} : ${k.valeur} — ${k.interpretation}\n`
      })
    }
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  const handlePrint = () => {
    if (!printRef.current) return
    const printContent = printRef.current.innerHTML
    const win = window.open('', '_blank')
    win.document.write(`
      <html><head>
        <title>${summary?.titre || 'Résumé Exécutif'}</title>
        <style>
          body { font-family: Georgia, serif; max-width: 800px; margin: 40px auto; color: #1a1a1a; line-height: 1.7; }
          h1 { font-size: 22px; border-bottom: 2px solid #4f46e5; padding-bottom: 8px; color: #4f46e5; }
          .meta { color: #666; font-size: 13px; margin-bottom: 24px; }
          .section { margin: 20px 0; }
          .section-title { font-size: 16px; font-weight: bold; color: #1e293b; margin-bottom: 8px; }
          .section-body { font-size: 14px; color: #374151; }
          .kpis { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin-top: 24px; }
          .kpi { display: flex; gap: 12px; margin: 8px 0; font-size: 13px; }
          .kpi-label { font-weight: bold; min-width: 140px; }
          .kpi-value { color: #4f46e5; font-weight: bold; }
          .kpi-interp { color: #64748b; }
          @media print { body { margin: 20px; } }
        </style>
      </head><body>
        <h1>${summary?.titre || 'Résumé Exécutif'}</h1>
        <div class="meta">Généré le ${summary?.date_generation} · ${summary?.nb_lignes_analysees} lignes analysées · ${summary?.provider}</div>
        ${summary?.sections?.map(s => `
          <div class="section">
            <div class="section-title">${s.titre}</div>
            <div class="section-body">${s.contenu}</div>
          </div>
        `).join('') || ''}
        ${summary?.kpis_cles?.length > 0 ? `
          <div class="kpis">
            <div class="section-title">📊 KPIs Clés</div>
            ${summary.kpis_cles.map(k => `
              <div class="kpi">
                <span class="kpi-label">${k.label}</span>
                <span class="kpi-value">${k.valeur}</span>
                <span class="kpi-interp">${k.interpretation}</span>
              </div>
            `).join('')}
          </div>
        ` : ''}
      </body></html>
    `)
    win.document.close()
    win.focus()
    setTimeout(() => { win.print(); win.close() }, 300)
  }

  const toggleSection = (id) => {
    setExpandedSections(prev => ({ ...prev, [id]: !prev[id] }))
  }

  return (
    <>
      {/* Bouton déclencheur */}
      <button
        onClick={handleOpen}
        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
        title="Générer un résumé exécutif IA"
      >
        <FileText className="w-3.5 h-3.5" />
        <span className="hidden sm:inline">Résumé IA</span>
      </button>

      {/* Modal */}
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setOpen(false)} />
          <div className="relative bg-white dark:bg-gray-900 rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] flex flex-col overflow-hidden">

            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-900/20 dark:to-purple-900/20">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-indigo-100 dark:bg-indigo-900/40">
                  <Sparkles className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
                </div>
                <div>
                  <h2 className="font-bold text-gray-900 dark:text-white text-base">Résumé Exécutif IA</h2>
                  <p className="text-xs text-gray-500 dark:text-gray-400">{reportNom}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {summary && (
                  <>
                    <button
                      onClick={handleCopy}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-50 transition-colors"
                      title="Copier le texte"
                    >
                      {copied ? <CheckCircle className="w-3.5 h-3.5 text-green-500" /> : <Copy className="w-3.5 h-3.5" />}
                      {copied ? 'Copié !' : 'Copier'}
                    </button>
                    <button
                      onClick={handlePrint}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-indigo-600 text-white hover:bg-indigo-700 transition-colors"
                      title="Imprimer / Exporter PDF"
                    >
                      <Printer className="w-3.5 h-3.5" />
                      PDF
                    </button>
                    <button
                      onClick={() => generate(true)}
                      disabled={loading}
                      className="p-1.5 rounded-lg text-gray-400 hover:text-indigo-500 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition-colors disabled:opacity-40"
                      title="Regénérer"
                    >
                      <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                    </button>
                  </>
                )}
                <button onClick={() => setOpen(false)} className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Body */}
            <div className="flex-1 overflow-y-auto p-6" ref={printRef}>
              {loading ? (
                <div className="flex flex-col items-center justify-center py-16 gap-4">
                  <div className="relative">
                    <Loader2 className="w-12 h-12 text-indigo-500 animate-spin" />
                    <Sparkles className="w-5 h-5 text-purple-400 absolute -top-1 -right-1 animate-pulse" />
                  </div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">L'IA rédige votre résumé exécutif...</p>
                  <p className="text-xs text-gray-400">Analyse des données en cours</p>
                </div>
              ) : error ? (
                <div className="flex flex-col items-center justify-center py-12 gap-3">
                  <AlertCircle className="w-10 h-10 text-red-400" />
                  <p className="text-sm text-red-500">{error}</p>
                  <button onClick={() => generate()} className="text-sm text-indigo-600 hover:underline">Réessayer</button>
                </div>
              ) : summary ? (
                <div className="space-y-4">
                  {/* Titre + méta */}
                  <div className="pb-4 border-b border-gray-200 dark:border-gray-700">
                    <h1 className="text-xl font-bold text-gray-900 dark:text-white">{summary.titre}</h1>
                    <div className="flex flex-wrap gap-3 mt-2 text-xs text-gray-400">
                      <span>Généré le {summary.date_generation}</span>
                      {summary.nb_lignes_analysees && <span>· {summary.nb_lignes_analysees} lignes analysées</span>}
                      {summary.from_cache && <span>· Depuis cache ({summary.cache_age_minutes} min)</span>}
                      <span>· {summary.provider}</span>
                    </div>
                  </div>

                  {/* KPIs clés */}
                  {summary.kpis_cles?.length > 0 && (
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      {summary.kpis_cles.map((kpi, i) => (
                        <div key={i} className="bg-indigo-50 dark:bg-indigo-900/20 rounded-xl p-3 border border-indigo-100 dark:border-indigo-800/30">
                          <div className="text-xs text-indigo-500 dark:text-indigo-400 font-medium mb-1">{kpi.label}</div>
                          <div className="text-lg font-bold text-indigo-700 dark:text-indigo-300">{kpi.valeur}</div>
                          <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{kpi.interpretation}</div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Sections narratives */}
                  {summary.sections?.map((section) => (
                    <div key={section.id} className="rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
                      <button
                        onClick={() => toggleSection(section.id)}
                        className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-750 transition-colors text-left"
                      >
                        <h3 className="font-semibold text-gray-800 dark:text-white text-sm">{section.titre}</h3>
                        {expandedSections[section.id]
                          ? <ChevronUp className="w-4 h-4 text-gray-400 flex-shrink-0" />
                          : <ChevronDown className="w-4 h-4 text-gray-400 flex-shrink-0" />
                        }
                      </button>
                      {expandedSections[section.id] && (
                        <div className="px-4 py-3">
                          <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">{section.contenu}</p>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          </div>
        </div>
      )}
    </>
  )
}
