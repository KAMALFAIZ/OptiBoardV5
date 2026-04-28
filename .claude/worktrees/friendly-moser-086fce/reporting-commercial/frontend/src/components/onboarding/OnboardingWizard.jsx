import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import api from '../../services/api'
import {
  BarChart2, Users, Briefcase, TrendingUp,
  Bell, ChevronRight, CheckCircle, X, Sparkles
} from 'lucide-react'

// ─── Étape 1 : Choix du rôle ─────────────────────────────────────────────────
const ROLES = [
  {
    id: 'direction',
    label: 'Direction',
    description: 'PDG, DAF, Directeur Général',
    icon: Briefcase,
    color: 'bg-indigo-50 dark:bg-indigo-900/20 border-indigo-200 dark:border-indigo-700 text-indigo-700 dark:text-indigo-300',
    activeColor: 'bg-indigo-600 border-indigo-600 text-white',
    modules: ['Dashboard KPIs exécutifs', 'Résumé IA hebdomadaire', 'Alertes critiques', 'Analyse CA & Créances'],
  },
  {
    id: 'manager',
    label: 'Manager',
    description: 'Resp. Commercial, Resp. Comptabilité',
    icon: Users,
    color: 'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-700 text-emerald-700 dark:text-emerald-300',
    activeColor: 'bg-emerald-600 border-emerald-600 text-white',
    modules: ['Ventes & Stocks', 'Recouvrement', 'Fiches Client 360°', 'Pivot & GridView'],
  },
  {
    id: 'commercial',
    label: 'Commercial / Opérationnel',
    description: 'Commercial, Comptable, Gestionnaire',
    icon: TrendingUp,
    color: 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-700 text-amber-700 dark:text-amber-300',
    activeColor: 'bg-amber-600 border-amber-600 text-white',
    modules: ['Liste Ventes détaillée', 'Fiche Client', 'Documents ventes', 'Assistant IA'],
  },
]

// ─── Étape 2 : Aperçu modules ─────────────────────────────────────────────────
function ModulePreview({ role }) {
  const found = ROLES.find(r => r.id === role)
  if (!found) return null
  return (
    <div className="space-y-3">
      <p className="text-sm text-gray-500 dark:text-gray-400 text-center">
        Voici les modules prioritaires pour votre rôle <strong>{found.label}</strong>
      </p>
      <div className="grid grid-cols-2 gap-3">
        {found.modules.map((mod, i) => (
          <div key={i} className="flex items-center gap-2 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-100 dark:border-gray-700">
            <CheckCircle className="w-4 h-4 text-emerald-500 flex-shrink-0" />
            <span className="text-sm text-gray-700 dark:text-gray-300">{mod}</span>
          </div>
        ))}
      </div>
      <p className="text-xs text-gray-400 dark:text-gray-500 text-center mt-2">
        Tous les modules restent accessibles depuis le menu latéral.
      </p>
    </div>
  )
}

// ─── Étape 3 : Première alerte ────────────────────────────────────────────────
const ALERT_PRESETS = [
  { label: 'CA journalier inférieur à un seuil', key: 'ca_jour', placeholder: 'Ex : 5000' },
  { label: 'Encours client dépasse un montant', key: 'encours', placeholder: 'Ex : 50000' },
  { label: 'Stock critique en dessous du seuil', key: 'stock',   placeholder: 'Ex : 10' },
]

function AlertStep({ onSkip }) {
  const [selected, setSelected] = useState(null)
  const [valeur, setValeur] = useState('')
  const [saved, setSaved] = useState(false)

  const handleSave = () => {
    // L'alerte réelle sera créée via AlertsPage — ici on montre juste la valeur
    setSaved(true)
  }

  if (saved) {
    return (
      <div className="text-center py-6">
        <CheckCircle className="w-12 h-12 text-emerald-500 mx-auto mb-3" />
        <p className="font-semibold text-gray-800 dark:text-white">Alerte enregistrée !</p>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Vous la retrouverez dans <strong>Mes alertes</strong> pour la configurer précisément.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-500 dark:text-gray-400 text-center">
        Choisissez votre première surveillance automatique
      </p>
      <div className="space-y-2">
        {ALERT_PRESETS.map((preset) => (
          <button
            key={preset.key}
            onClick={() => setSelected(preset.key)}
            className={`w-full flex items-center gap-3 p-3 rounded-lg border text-left transition-all text-sm ${
              selected === preset.key
                ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300'
                : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:border-gray-300'
            }`}
          >
            <Bell className={`w-4 h-4 flex-shrink-0 ${selected === preset.key ? 'text-primary-500' : 'text-gray-400'}`} />
            {preset.label}
          </button>
        ))}
      </div>

      {selected && (
        <div className="flex gap-2">
          <input
            type="number"
            value={valeur}
            onChange={e => setValeur(e.target.value)}
            placeholder={ALERT_PRESETS.find(p => p.key === selected)?.placeholder}
            className="flex-1 px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:border-primary-500"
          />
          <button
            onClick={handleSave}
            disabled={!valeur}
            className="px-4 py-2 bg-primary-600 hover:bg-primary-700 disabled:opacity-40 text-white rounded-lg text-sm font-medium transition-colors"
          >
            Créer
          </button>
        </div>
      )}

      <button onClick={onSkip} className="w-full text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors py-1">
        Passer cette étape →
      </button>
    </div>
  )
}


// ─── Wizard principal ─────────────────────────────────────────────────────────
export default function OnboardingWizard({ onClose }) {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [step, setStep] = useState(0)
  const [selectedRole, setSelectedRole] = useState(null)
  const [finishing, setFinishing] = useState(false)

  const steps = [
    { title: 'Quel est votre rôle ?',          subtitle: 'Personnalisez votre expérience OptiBoard' },
    { title: 'Votre tableau de bord',           subtitle: 'Les modules essentiels pour vous' },
    { title: 'Activez votre première alerte',   subtitle: 'Soyez informé automatiquement' },
  ]

  const handleFinish = async () => {
    setFinishing(true)
    try {
      // Récupérer le dwh_code depuis la session
      let dwhCode = null
      try {
        const saved = localStorage.getItem('currentDWH') || sessionStorage.getItem('currentDWH')
        if (saved) dwhCode = JSON.parse(saved)?.code
      } catch { /* ignore */ }

      if (user?.id && dwhCode) {
        await api.patch('/auth/me/onboarding-done', { user_id: user.id, dwh_code: dwhCode })

        // Mettre à jour le user en localStorage pour éviter de revoir le wizard
        const key = localStorage.getItem('user') ? 'localStorage' : 'sessionStorage'
        const storage = key === 'localStorage' ? localStorage : sessionStorage
        try {
          const saved = JSON.parse(storage.getItem('user') || '{}')
          storage.setItem('user', JSON.stringify({ ...saved, onboarding_done: true }))
        } catch { /* ignore */ }
      }
    } catch (e) {
      console.error('onboarding-done error:', e)
    } finally {
      setFinishing(false)
      onClose()
    }
  }

  const canNext = step === 0 ? !!selectedRole : true

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/50 backdrop-blur-sm px-4">
      <div className="w-full max-w-lg bg-white dark:bg-gray-900 rounded-2xl shadow-2xl overflow-hidden">

        {/* Header */}
        <div className="bg-gradient-to-r from-primary-600 to-primary-700 px-6 py-5">
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-2 text-white">
              <Sparkles className="w-5 h-5" />
              <span className="font-bold text-lg">Bienvenue sur OptiBoard</span>
            </div>
            <button onClick={onClose} className="text-white/70 hover:text-white transition-colors">
              <X className="w-5 h-5" />
            </button>
          </div>
          <p className="text-primary-100 text-sm">{steps[step].subtitle}</p>

          {/* Barre de progression */}
          <div className="flex gap-1.5 mt-4">
            {steps.map((_, i) => (
              <div
                key={i}
                className={`h-1 flex-1 rounded-full transition-all ${
                  i <= step ? 'bg-white' : 'bg-white/30'
                }`}
              />
            ))}
          </div>
        </div>

        {/* Corps */}
        <div className="px-6 py-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-5 text-center">
            {steps[step].title}
          </h2>

          {/* Étape 0 — Rôle */}
          {step === 0 && (
            <div className="space-y-3">
              {ROLES.map((role) => {
                const Icon = role.icon
                const isActive = selectedRole === role.id
                return (
                  <button
                    key={role.id}
                    onClick={() => setSelectedRole(role.id)}
                    className={`w-full flex items-center gap-4 p-4 rounded-xl border-2 text-left transition-all ${
                      isActive ? role.activeColor : role.color
                    }`}
                  >
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
                      isActive ? 'bg-white/20' : 'bg-white dark:bg-gray-800'
                    }`}>
                      <Icon className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="font-semibold text-sm">{role.label}</div>
                      <div className={`text-xs mt-0.5 ${isActive ? 'opacity-80' : 'text-gray-500 dark:text-gray-400'}`}>
                        {role.description}
                      </div>
                    </div>
                    {isActive && <CheckCircle className="w-5 h-5 ml-auto opacity-80" />}
                  </button>
                )
              })}
            </div>
          )}

          {/* Étape 1 — Modules */}
          {step === 1 && <ModulePreview role={selectedRole} />}

          {/* Étape 2 — Alerte */}
          {step === 2 && <AlertStep onSkip={handleFinish} />}
        </div>

        {/* Footer */}
        <div className="px-6 pb-6 flex items-center justify-between">
          <button
            onClick={() => step > 0 ? setStep(s => s - 1) : onClose()}
            className="text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
          >
            {step === 0 ? 'Passer' : '← Retour'}
          </button>

          {step < steps.length - 1 ? (
            <button
              onClick={() => setStep(s => s + 1)}
              disabled={!canNext}
              className="flex items-center gap-2 px-5 py-2.5 bg-primary-600 hover:bg-primary-700 disabled:opacity-40 text-white rounded-xl text-sm font-semibold transition-colors shadow"
            >
              Suivant
              <ChevronRight className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={handleFinish}
              disabled={finishing}
              className="flex items-center gap-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-60 text-white rounded-xl text-sm font-semibold transition-colors shadow"
            >
              {finishing ? 'Enregistrement…' : 'Terminer'}
              <CheckCircle className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
