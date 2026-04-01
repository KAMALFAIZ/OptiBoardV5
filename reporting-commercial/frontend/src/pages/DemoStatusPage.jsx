import { useState, useEffect, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import axios from 'axios'
import {
  BarChart2, CheckCircle, Clock, AlertCircle, Loader2,
  Database, RefreshCw, ExternalLink, Calendar, User, Building2,
} from 'lucide-react'

const POLL_INTERVAL_MS = 8000

function DemoBanner({ expiresAt }) {
  const expiryDate = expiresAt ? new Date(expiresAt).toLocaleDateString('fr-MA', {
    day: '2-digit', month: 'long', year: 'numeric',
  }) : null

  return (
    <div className="w-full bg-amber-500 text-white text-sm font-medium flex items-center justify-center gap-2 px-4 py-2">
      <Clock className="w-4 h-4 shrink-0" />
      <span>
        Environnement de démonstration
        {expiryDate && <> — expire le <strong>{expiryDate}</strong></>}
      </span>
    </div>
  )
}

function StepItem({ done, active, label, sublabel }) {
  return (
    <div className="flex items-start gap-3">
      <div className={`mt-0.5 w-6 h-6 rounded-full flex items-center justify-center shrink-0 ${
        done  ? 'bg-green-500' :
        active ? 'bg-blue-500 animate-pulse' :
                 'bg-gray-200'
      }`}>
        {done  ? <CheckCircle className="w-4 h-4 text-white" /> :
         active ? <Loader2 className="w-3 h-3 text-white animate-spin" /> :
                  <span className="w-2 h-2 rounded-full bg-gray-400" />}
      </div>
      <div>
        <p className={`text-sm font-medium ${done ? 'text-gray-900' : active ? 'text-blue-700' : 'text-gray-400'}`}>
          {label}
        </p>
        {sublabel && (
          <p className={`text-xs ${done || active ? 'text-gray-500' : 'text-gray-300'}`}>{sublabel}</p>
        )}
      </div>
    </div>
  )
}

function SageConfigForm({ token, onSaved }) {
  const [sageServer,   setSageServer]   = useState('localhost')
  const [sageDatabase, setSageDatabase] = useState('')
  const [sageUser,     setSageUser]     = useState('')
  const [sagePassword, setSagePassword] = useState('')
  const [saving,   setSaving]   = useState(false)
  const [testing,  setTesting]  = useState(false)
  const [msg,      setMsg]      = useState(null)
  const [testMsg,  setTestMsg]  = useState(null)

  const buildPayload = () => ({
    sage_server:   sageServer.trim(),
    sage_database: sageDatabase.trim(),
    sage_username: sageUser.trim(),
    sage_password: sagePassword,
  })

  const handleTest = async () => {
    if (!sageDatabase.trim()) { setTestMsg({ ok: false, txt: 'Renseignez la base Sage avant de tester' }); return }
    setTesting(true)
    setTestMsg(null)
    try {
      const res = await axios.post(`/api/demo/${token}/test-connection`, buildPayload())
      setTestMsg({ ok: res.data.success, txt: res.data.message })
    } catch (e) {
      setTestMsg({ ok: false, txt: e.response?.data?.detail || 'Erreur lors du test' })
    } finally {
      setTesting(false)
    }
  }

  const handleSave = async () => {
    if (!sageDatabase.trim()) { setMsg({ ok: false, txt: 'La base Sage est obligatoire' }); return }
    setSaving(true)
    try {
      await axios.patch(`/api/demo/${token}/configure`, buildPayload())
      setMsg({ ok: true, txt: "✅ Configuration enregistrée — redémarrez l'AgentETL" })
      if (onSaved) onSaved()
    } catch (e) {
      setMsg({ ok: false, txt: e.response?.data?.detail || 'Erreur' })
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="bg-orange-50 border border-orange-200 rounded-2xl p-5 space-y-3">
      <h4 className="font-semibold text-orange-900 text-sm flex items-center gap-2">
        <Database className="w-4 h-4" /> Configuration base Sage 100
      </h4>
      <p className="text-xs text-orange-700">Renseignez les informations de connexion à votre base Sage.</p>
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="text-xs text-gray-600 font-medium">Serveur SQL</label>
          <input value={sageServer} onChange={e => setSageServer(e.target.value)}
            className="w-full mt-1 px-2 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-400"
            placeholder="localhost" />
        </div>
        <div>
          <label className="text-xs text-gray-600 font-medium">Base Sage <span className="text-red-500">*</span></label>
          <input value={sageDatabase} onChange={e => setSageDatabase(e.target.value)}
            className="w-full mt-1 px-2 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-400"
            placeholder="GESCOM2026" />
        </div>
        <div>
          <label className="text-xs text-gray-600 font-medium">Utilisateur SQL</label>
          <input value={sageUser} onChange={e => setSageUser(e.target.value)}
            className="w-full mt-1 px-2 py-1.5 text-sm border border-gray-300 rounded-lg"
            placeholder="sa (laisser vide = auth Windows)" />
        </div>
        <div>
          <label className="text-xs text-gray-600 font-medium">Mot de passe</label>
          <input type="password" value={sagePassword} onChange={e => setSagePassword(e.target.value)}
            className="w-full mt-1 px-2 py-1.5 text-sm border border-gray-300 rounded-lg" />
        </div>
      </div>

      {/* Résultat du test */}
      {testMsg && (
        <div className={`flex items-start gap-2 text-xs font-medium px-3 py-2 rounded-lg ${
          testMsg.ok ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-600 border border-red-200'
        }`}>
          {testMsg.ok
            ? <CheckCircle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
            : <AlertCircle className="w-3.5 h-3.5 mt-0.5 shrink-0" />}
          <span>{testMsg.txt}</span>
        </div>
      )}

      <div className="flex gap-2">
        <button onClick={handleTest} disabled={testing || saving}
          className="flex-1 flex items-center justify-center gap-1.5 bg-white border border-orange-300 text-orange-700 text-sm font-medium py-2 rounded-lg hover:bg-orange-100 disabled:opacity-50 transition-colors">
          {testing
            ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Test en cours…</>
            : <><RefreshCw className="w-3.5 h-3.5" /> Tester la connexion</>}
        </button>
        <button onClick={handleSave} disabled={saving || testing}
          className="flex-1 bg-orange-600 text-white text-sm font-medium py-2 rounded-lg hover:bg-orange-700 disabled:opacity-50 transition-colors">
          {saving ? 'Enregistrement…' : 'Enregistrer'}
        </button>
      </div>

      {msg && (
        <p className={`text-xs font-medium ${msg.ok ? 'text-green-700' : 'text-red-600'}`}>{msg.txt}</p>
      )}
    </div>
  )
}

export default function DemoStatusPage() {
  const { token } = useParams()
  const [session, setSession] = useState(null)
  const [loading, setLoading]  = useState(true)
  const [error, setError]      = useState(null)
  const [lastRefresh, setLastRefresh] = useState(null)
  const [showSageConfig, setShowSageConfig] = useState(false)

  const fetchStatus = useCallback(async () => {
    try {
      const res = await axios.get(`/api/demo/${token}/status`)
      if (res.data.success) {
        setSession(res.data)
        setLastRefresh(new Date())
      } else {
        setError('Session introuvable.')
      }
    } catch (err) {
      if (err.response?.status === 404) {
        setError('Lien de démonstration invalide ou expiré.')
      } else {
        setError('Erreur de connexion au serveur.')
      }
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => {
    fetchStatus()
  }, [fetchStatus])

  // Polling auto tant que la sync n'est pas terminée
  useEffect(() => {
    if (!session) return
    if (session.is_expired || session.revoked) return
    if (session.sync_completed) return

    const interval = setInterval(fetchStatus, POLL_INTERVAL_MS)
    return () => clearInterval(interval)
  }, [session, fetchStatus])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 p-4">
        <div className="w-full max-w-md text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-red-100 rounded-full mb-4">
            <AlertCircle className="w-8 h-8 text-red-500" />
          </div>
          <h1 className="text-xl font-bold text-gray-900 mb-2">Accès impossible</h1>
          <p className="text-gray-500 text-sm">{error}</p>
          <a
            href="/demo"
            className="mt-6 inline-block bg-blue-600 text-white px-6 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            Créer une nouvelle démo
          </a>
        </div>
      </div>
    )
  }

  if (session.revoked || session.is_expired) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 p-4">
        <div className="w-full max-w-md text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gray-100 rounded-full mb-4">
            <Clock className="w-8 h-8 text-gray-400" />
          </div>
          <h1 className="text-xl font-bold text-gray-900 mb-2">Session expirée</h1>
          <p className="text-gray-500 text-sm">
            {session.revoked
              ? 'Cette session de démonstration a été révoquée.'
              : 'Votre accès démo de 7 jours est terminé.'}
          </p>
          <a
            href="/demo"
            className="mt-6 inline-block bg-blue-600 text-white px-6 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            Créer une nouvelle démo
          </a>
        </div>
      </div>
    )
  }

  // Calcul de l'étape courante
  const isCloneKa = session.demo_mode === 'clone_ka'
  const step = !session.confirmed       ? 0
             : !session.sync_started    ? 1
             : !session.sync_completed  ? 2
             :                            3

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <DemoBanner expiresAt={session.expires_at} />

      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center gap-3">
        <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
          <BarChart2 className="w-5 h-5 text-white" />
        </div>
        <span className="font-bold text-gray-900 text-lg">OptiBoard</span>
        <span className="text-xs bg-amber-100 text-amber-700 font-medium px-2 py-0.5 rounded-full ml-1">Démo</span>
      </header>

      <main className="flex-1 flex items-center justify-center p-4">
        <div className="w-full max-w-lg space-y-4">

          {/* Carte info session */}
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
            <h2 className="text-lg font-bold text-gray-900 mb-4">Votre espace démonstration</h2>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="flex items-center gap-2 text-gray-600">
                <User className="w-4 h-4 text-gray-400" />
                <span>{session.prenom} {session.nom}</span>
              </div>
              <div className="flex items-center gap-2 text-gray-600">
                <Building2 className="w-4 h-4 text-gray-400" />
                <span>{session.societe}</span>
              </div>
              <div className="flex items-center gap-2 text-gray-600">
                <Calendar className="w-4 h-4 text-gray-400" />
                <span>Données : Jan – Fév 2026</span>
              </div>
              <div className="flex items-center gap-2 text-gray-600">
                <Clock className="w-4 h-4 text-gray-400" />
                <span>
                  Expire le{' '}
                  {session.expires_at
                    ? new Date(session.expires_at).toLocaleDateString('fr-MA', { day: '2-digit', month: 'short' })
                    : '—'}
                </span>
              </div>
            </div>
          </div>

          {/* Carte progression */}
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
            <div className="flex items-center justify-between mb-5">
              <h3 className="font-semibold text-gray-900">Progression</h3>
              <button
                onClick={fetchStatus}
                className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 transition-colors"
              >
                <RefreshCw className="w-3 h-3" />
                {lastRefresh ? lastRefresh.toLocaleTimeString('fr-MA', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '—'}
              </button>
            </div>

            <div className="space-y-4">
              <StepItem
                done={step > 0} active={step === 0}
                label="Email confirmé"
                sublabel="Vérification de votre adresse email"
              />
              {isCloneKa ? (
                <StepItem
                  done={step > 1} active={step === 1}
                  label="Préparation des données"
                  sublabel="Copie des données de démonstration 2025–2026 en cours"
                />
              ) : (
                <StepItem
                  done={step > 1} active={step === 1}
                  label="AgentETL en attente"
                  sublabel="Téléchargez et lancez l'AgentETL sur votre serveur Sage"
                />
              )}
              <StepItem
                done={step > 2} active={step === 2}
                label={isCloneKa ? 'Copie des données en cours' : 'Synchronisation en cours'}
                sublabel={
                  step === 2 && session.rows_total > 0
                    ? `${session.rows_total.toLocaleString()} lignes reçues — ${session.tables_synced} tables`
                    : isCloneKa ? 'Import des données DWH (2025–2026)' : 'Transfert de vos données Sage (Jan – Fév 2026)'
                }
              />
              <StepItem
                done={step === 3} active={false}
                label="OptiBoard prêt"
                sublabel="Visualisez vos données dans le tableau de bord"
              />
            </div>

            {/* Barre de progression */}
            {step === 2 && (
              <div className="mt-5">
                <div className="w-full bg-gray-100 rounded-full h-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full transition-all duration-500 animate-pulse"
                    style={{ width: '60%' }}
                  />
                </div>
                <p className="text-xs text-gray-400 mt-1 text-center">Synchronisation en cours…</p>
              </div>
            )}
          </div>

          {/* Boutons accès OptiBoard (quand prêt) */}
          {step === 3 && session.optiboard_url && (
            <div className="flex flex-col gap-3">
              {/* Bouton principal : application complète */}
              <a
                href={session.optiboard_url}
                className="flex items-center justify-center gap-2 w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-4 rounded-2xl transition-colors shadow-lg text-base"
              >
                <Database className="w-5 h-5" />
                Accéder à l'application complète
                <ExternalLink className="w-4 h-4" />
              </a>
              {/* Lien secondaire : tableau de bord simplifié */}
              {session.board_url && (
                <a
                  href={session.board_url}
                  className="flex items-center justify-center gap-2 w-full bg-white border border-gray-200 hover:bg-gray-50 text-gray-700 font-medium py-3 rounded-2xl transition-colors text-sm"
                >
                  <BarChart2 className="w-4 h-4 text-gray-500" />
                  Voir le tableau de bord simplifié
                </a>
              )}
            </div>
          )}

          {/* Bloc téléchargement AgentETL (step 1, mode agent_etl seulement) */}
          {step === 1 && !isCloneKa && (
            <div className="bg-blue-50 border border-blue-200 rounded-2xl p-5">
              <h4 className="font-semibold text-blue-900 mb-2 text-sm">Télécharger l'AgentETL</h4>
              <p className="text-xs text-blue-700 leading-relaxed mb-3">
                Installez l'AgentETL sur votre serveur Windows où est installé Sage.
                La configuration est déjà pré-remplie avec votre token.
              </p>
              <a
                href={`/api/demo/${token}/download`}
                className="inline-flex items-center gap-2 bg-blue-600 text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
              >
                Télécharger SageETLAgent.exe
              </a>
            </div>
          )}

          {/* Config base Sage — toujours accessible */}
          <div className="border-t border-gray-100 pt-3">
            <button
              onClick={() => setShowSageConfig(v => !v)}
              className="flex items-center gap-2 text-xs text-gray-500 hover:text-orange-600 transition-colors"
            >
              <Database className="w-3.5 h-3.5" />
              {showSageConfig ? 'Masquer' : 'Modifier la configuration base Sage'}
            </button>
            {showSageConfig && (
              <div className="mt-3">
                <SageConfigForm token={token} onSaved={() => setShowSageConfig(false)} />
              </div>
            )}
          </div>

        </div>
      </main>
    </div>
  )
}
