/**
 * DemoLaunchPage — Portail de demarrage demo OptiBoard
 *
 * Appele depuis DemoStatusPage quand sync_completed=1.
 * 1. POST /api/demo/:token/provision  → cree user + DWH si besoin
 * 2. POST /api/demo/:token/auto-login → retourne session compatible localStorage
 * 3. Stocke user / token / currentDWH dans localStorage
 * 4. Hard-redirect vers "/" → l'app charge avec la session demo
 */
import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import axios from 'axios'
import { Loader2, AlertCircle, Rocket } from 'lucide-react'

export default function DemoLaunchPage() {
  const { token } = useParams()
  const [phase, setPhase] = useState('init')   // init | provisioning | logging | redirecting | error
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!token) {
      setError('Token manquant')
      setPhase('error')
      return
    }
    launch()
  }, [token]) // eslint-disable-line react-hooks/exhaustive-deps

  const launch = async () => {
    try {
      // 1. Provisionnement du compte demo (idempotent)
      setPhase('provisioning')
      await axios.post(`/api/demo/${token}/provision`)

      // 2. Auto-login — recuperer les credentials de session
      setPhase('logging')
      const res = await axios.post(`/api/demo/${token}/auto-login`)

      if (!res.data.success) {
        throw new Error(res.data.detail || 'Echec de connexion automatique')
      }

      // 3. Nettoyer l'ancienne session, puis stocker la nouvelle
      localStorage.removeItem('user'); sessionStorage.removeItem('user')
      localStorage.removeItem('token'); sessionStorage.removeItem('token')
      localStorage.removeItem('currentDWH'); sessionStorage.removeItem('currentDWH')

      localStorage.setItem('user',       JSON.stringify(res.data.user))
      localStorage.setItem('token',      res.data.token)
      if (res.data.current_dwh?.code) {
        localStorage.setItem('currentDWH', JSON.stringify(res.data.current_dwh))
      }

      // 4. Redirection vers l'application
      setPhase('redirecting')
      setTimeout(() => {
        window.location.href = '/'
      }, 600)

    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Erreur lors du demarrage de la demo'
      setError(msg)
      setPhase('error')
    }
  }

  const phaseLabel = {
    init:         'Initialisation...',
    provisioning: 'Preparation de votre espace demo...',
    logging:      'Connexion en cours...',
    redirecting:  'Redirection vers OptiBoard...',
  }

  /* ── Erreur ─────────────────────────────────────────────────────────────── */
  if (phase === 'error') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-[#1e3a5f] to-[#0f2040] flex items-center justify-center p-6">
        <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full text-center">
          <div className="w-14 h-14 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <AlertCircle className="w-7 h-7 text-red-600" />
          </div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">Impossible de demarrer la demo</h2>
          <p className="text-gray-500 text-sm mb-6">{error}</p>
          <button
            onClick={() => { setPhase('init'); setError(null); launch() }}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2.5 rounded-xl transition-colors text-sm"
          >
            Reessayer
          </button>
          <a
            href={`/demo/${token}`}
            className="block mt-3 text-sm text-gray-400 hover:text-gray-600 transition-colors"
          >
            Retourner a la page de suivi
          </a>
        </div>
      </div>
    )
  }

  /* ── Chargement / Redirection ───────────────────────────────────────────── */
  return (
    <div className="min-h-screen bg-gradient-to-br from-[#1e3a5f] to-[#0f2040] flex items-center justify-center p-6">
      <div className="text-center text-white">
        {/* Logo / icone */}
        <div className="w-20 h-20 bg-white/10 rounded-full flex items-center justify-center mx-auto mb-6 backdrop-blur-sm">
          {phase === 'redirecting'
            ? <Rocket className="w-10 h-10 text-white" />
            : <Loader2 className="w-10 h-10 text-white animate-spin" />
          }
        </div>

        {/* Titre */}
        <h1 className="text-2xl font-bold mb-2">Demarrage de votre demo OptiBoard</h1>
        <p className="text-blue-200 text-sm mb-8">
          Preparation de votre environnement personnalise avec vos donnees Sage
        </p>

        {/* Etapes */}
        <div className="bg-white/10 rounded-xl p-5 backdrop-blur-sm max-w-xs mx-auto text-left space-y-3">
          {[
            { id: 'provisioning', label: 'Creation du compte demo' },
            { id: 'logging',      label: 'Connexion automatique' },
            { id: 'redirecting',  label: 'Ouverture de l\'application' },
          ].map((step) => {
            const phases = ['provisioning', 'logging', 'redirecting']
            const currentIdx = phases.indexOf(phase)
            const stepIdx    = phases.indexOf(step.id)
            const isDone     = stepIdx < currentIdx
            const isActive   = stepIdx === currentIdx

            return (
              <div key={step.id} className="flex items-center gap-3">
                <div className={`w-5 h-5 rounded-full flex items-center justify-center shrink-0 ${
                  isDone   ? 'bg-green-400' :
                  isActive ? 'bg-white/90 ring-2 ring-blue-300' :
                             'bg-white/20'
                }`}>
                  {isDone
                    ? <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>
                    : isActive
                      ? <Loader2 className="w-3 h-3 text-blue-600 animate-spin" />
                      : null
                  }
                </div>
                <span className={`text-sm ${isDone ? 'text-green-300' : isActive ? 'text-white font-medium' : 'text-white/40'}`}>
                  {step.label}
                </span>
              </div>
            )
          })}
        </div>

        {/* Message de phase */}
        <p className="mt-6 text-blue-200 text-xs animate-pulse">
          {phaseLabel[phase] || '...'}
        </p>
      </div>
    </div>
  )
}
