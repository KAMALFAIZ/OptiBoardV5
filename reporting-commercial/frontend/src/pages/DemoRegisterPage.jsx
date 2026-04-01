import { useState } from 'react'
import axios from 'axios'
import { CheckCircle, Loader2, AlertCircle, BarChart2, ArrowRight, XCircle, Database, Upload } from 'lucide-react'

const SECTEURS = [
  'Commerce de gros',
  'Commerce de détail',
  'Import / Export',
  'Distribution',
  'Industrie',
  'Agroalimentaire',
  'BTP',
  'Services',
  'Autre',
]

export default function DemoRegisterPage() {
  const [demoMode, setDemoMode] = useState(null)   // null = pas encore choisi
  const [form, setForm] = useState({
    nom: '', prenom: '', societe: '', email: '', secteur: '', telephone: '',
  })
  const [loading, setLoading]   = useState(false)
  const [success, setSuccess]   = useState(false)
  const [rejected, setRejected] = useState(false)
  const [error, setError]       = useState(null)

  const handleChange = (e) => {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }))
    setError(null)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.nom || !form.prenom || !form.societe || !form.email) {
      setError('Veuillez remplir tous les champs obligatoires.')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const res = await axios.post('/api/demo/register', { ...form, demo_mode: demoMode })
      if (res.data.already_active || res.data.message?.includes('toujours active')) {
        setRejected(true)
      } else if (res.data.success) {
        setSuccess(true)
      } else {
        setError(res.data.message || 'Une erreur est survenue.')
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Erreur de connexion au serveur.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-600 via-blue-700 to-blue-900 flex flex-col items-center justify-center p-4">

      {/* Header */}
      <div className="mb-8 text-center">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-white/20 rounded-2xl mb-4">
          <BarChart2 className="w-9 h-9 text-white" />
        </div>
        <h1 className="text-3xl font-bold text-white">OptiBoard</h1>
        <p className="text-blue-200 mt-1">Essayez gratuitement avec vos propres données Sage</p>
      </div>

      <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl overflow-hidden">

        {/* ── Étape 1 : Choix du mode ─────────────────────────── */}
        {!demoMode && !success && !rejected && (
          <div className="p-8">
            <h2 className="text-xl font-bold text-gray-900 mb-1 text-center">Choisissez votre mode de démo</h2>
            <p className="text-sm text-gray-500 text-center mb-6">Comment souhaitez-vous alimenter votre démo ?</p>
            <div className="space-y-3">
              <button
                onClick={() => setDemoMode('clone_ka')}
                className="w-full flex items-start gap-4 p-4 border-2 border-blue-500 bg-blue-50 rounded-xl hover:bg-blue-100 transition-colors text-left"
              >
                <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center shrink-0 mt-0.5">
                  <Database className="w-5 h-5 text-white" />
                </div>
                <div>
                  <p className="font-semibold text-gray-900 text-sm">Données de démonstration</p>
                  <p className="text-xs text-gray-500 mt-0.5">Accès immédiat avec des données réelles 2025–2026. Aucune installation requise.</p>
                  <span className="inline-block mt-1.5 text-xs bg-blue-600 text-white px-2 py-0.5 rounded-full">Recommandé</span>
                </div>
              </button>
              <button
                onClick={() => setDemoMode('agent_etl')}
                className="w-full flex items-start gap-4 p-4 border-2 border-gray-200 rounded-xl hover:border-gray-400 hover:bg-gray-50 transition-colors text-left"
              >
                <div className="w-10 h-10 bg-gray-600 rounded-lg flex items-center justify-center shrink-0 mt-0.5">
                  <Upload className="w-5 h-5 text-white" />
                </div>
                <div>
                  <p className="font-semibold text-gray-900 text-sm">Mes données Sage</p>
                  <p className="text-xs text-gray-500 mt-0.5">Synchronisez vos propres données via l'AgentETL. Nécessite une installation sur votre serveur.</p>
                </div>
              </button>
            </div>
          </div>
        )}

        {/* ── Rejet (email déjà inscrit) ──────────────────────── */}
        {rejected && (
          <div className="p-8 text-center">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-orange-100 rounded-full mb-4">
              <XCircle className="w-9 h-9 text-orange-500" />
            </div>
            <h2 className="text-xl font-bold text-gray-900 mb-2">Adresse déjà enregistrée</h2>
            <p className="text-gray-600 text-sm leading-relaxed mb-1">
              Nous sommes désolés, mais l'adresse <strong>{form.email}</strong> est déjà associée à une session démo active.
            </p>
            <p className="text-gray-500 text-sm leading-relaxed mb-6">
              Veuillez vérifier votre boîte mail (y compris les spams) pour retrouver votre lien d'accès,
              ou utilisez une autre adresse email pour créer une nouvelle démo.
            </p>
            <button
              onClick={() => { setRejected(false); setDemoMode(null); setForm({ nom:'', prenom:'', societe:'', email:'', secteur:'', telephone:'' }) }}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 rounded-xl transition-colors text-sm"
            >
              Utiliser une autre adresse
            </button>
          </div>
        )}

        {/* ── Succès ──────────────────────────────────────────── */}
        {success && !rejected && (
          <div className="p-8 text-center">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-green-100 rounded-full mb-4">
              <CheckCircle className="w-9 h-9 text-green-600" />
            </div>
            <h2 className="text-xl font-bold text-gray-900 mb-2">Inscription réussie !</h2>
            <p className="text-gray-600 text-sm leading-relaxed">
              Un email de confirmation vient d'être envoyé à <strong>{form.email}</strong>.
            </p>
            {demoMode === 'clone_ka' ? (
              <div className="mt-6 p-4 bg-blue-50 rounded-xl text-left">
                <p className="text-xs font-semibold text-blue-700 mb-2">Étapes suivantes :</p>
                <ol className="text-xs text-blue-600 space-y-1 list-decimal list-inside">
                  <li>Confirmez votre email</li>
                  <li>Accédez à OptiBoard avec des données 2025–2026</li>
                </ol>
              </div>
            ) : (
              <div className="mt-6 p-4 bg-blue-50 rounded-xl text-left">
                <p className="text-xs font-semibold text-blue-700 mb-2">Étapes suivantes :</p>
                <ol className="text-xs text-blue-600 space-y-1 list-decimal list-inside">
                  <li>Confirmez votre email</li>
                  <li>Téléchargez et lancez l'AgentETL</li>
                  <li>Configurez votre connexion Sage</li>
                  <li>Accédez à OptiBoard avec vos données</li>
                </ol>
              </div>
            )}
          </div>
        )}

        {/* ── Étape 2 : Formulaire (après choix du mode) ──────── */}
        {demoMode && !success && !rejected && (
          <>
            <div className="px-8 pt-8 pb-2 flex items-center gap-2">
              <button onClick={() => setDemoMode(null)} className="text-gray-400 hover:text-gray-600 text-xs underline">← Retour</button>
              <span className="text-xs text-gray-400">|</span>
              <span className="text-xs text-gray-500">
                {demoMode === 'clone_ka' ? '🗄 Données de démonstration' : '⬆ Mes données Sage'}
              </span>
            </div>
            <div className="px-8 pb-2">
              <h2 className="text-xl font-bold text-gray-900">Démarrer ma démo gratuite</h2>
              <p className="text-sm text-gray-500 mt-1">Accès pendant 7 jours</p>
            </div>

            {error && (
              <div className="mx-8 mt-4 flex items-start gap-2 bg-red-50 border border-red-200 rounded-lg p-3">
                <AlertCircle className="w-4 h-4 text-red-500 mt-0.5 shrink-0" />
                <p className="text-sm text-red-700">{error}</p>
              </div>
            )}

            <form onSubmit={handleSubmit} className="px-8 py-6 space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Prénom <span className="text-red-500">*</span></label>
                  <input type="text" name="prenom" value={form.prenom} onChange={handleChange} required placeholder="Mohammed"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Nom <span className="text-red-500">*</span></label>
                  <input type="text" name="nom" value={form.nom} onChange={handleChange} required placeholder="Alami"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none" />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Société <span className="text-red-500">*</span></label>
                <input type="text" name="societe" value={form.societe} onChange={handleChange} required placeholder="SARL Alami & Fils"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Email professionnel <span className="text-red-500">*</span></label>
                <input type="email" name="email" value={form.email} onChange={handleChange} required placeholder="m.alami@societe.ma"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Secteur d'activité</label>
                <select name="secteur" value={form.secteur} onChange={handleChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none bg-white">
                  <option value="">— Sélectionner —</option>
                  {SECTEURS.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Téléphone</label>
                <input type="tel" name="telephone" value={form.telephone} onChange={handleChange} placeholder="+212 6XX XXX XXX"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none" />
              </div>
              <button type="submit" disabled={loading}
                className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-semibold py-3 rounded-xl transition-colors text-sm">
                {loading
                  ? <><Loader2 className="w-4 h-4 animate-spin" /> Création en cours...</>
                  : <>Démarrer ma démo gratuite <ArrowRight className="w-4 h-4" /></>}
              </button>
              <p className="text-xs text-center text-gray-400">Aucune carte bancaire requise. Vos données restent confidentielles.</p>
            </form>
          </>
        )}
      </div>

      {/* Footer */}
      <p className="mt-6 text-blue-300 text-xs text-center">
        Powered by OptiBoard — Reporting Sage pour PME marocaines
      </p>
    </div>
  )
}
