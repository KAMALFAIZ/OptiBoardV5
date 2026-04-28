import { useState, useEffect } from 'react'
import { Bell, BellOff, Mail, Check, Loader2, X, Plus, Trash2, Clock, Calendar, Users } from 'lucide-react'
import api from '../../services/api'
import { useAuth } from '../../context/AuthContext'

const FREQUENCIES = [
  { key: 'daily',   label: 'Quotidien',    desc: 'Chaque jour' },
  { key: 'weekly',  label: 'Hebdomadaire', desc: 'Chaque semaine' },
  { key: 'monthly', label: 'Mensuel',      desc: 'Chaque mois' },
]

const FORMATS = [
  { key: 'excel', label: 'Excel (.xlsx)' },
  { key: 'pdf',   label: 'PDF' },
]

const CHANNELS = [
  { key: 'email',    label: 'Email',    icon: '✉️', placeholder: 'votre@email.com',       hint: 'Rapport joint en pièce attachée' },
  { key: 'whatsapp', label: 'WhatsApp', icon: '💬', placeholder: '+212600000000',          hint: 'Numéro international (+212…)' },
  { key: 'telegram', label: 'Telegram', icon: '✈️', placeholder: '123456789 ou @username', hint: 'Chat ID ou @username du bot' },
]

const HOURS = [6,7,8,9,10,11,12,14,16,18,20]
const DAYS_FR = ['Lundi','Mardi','Mercredi','Jeudi','Vendredi','Samedi','Dimanche']

export default function SubscribeButton({ reportType, reportId, reportNom }) {
  const { user } = useAuth()
  const [open, setOpen]           = useState(false)
  const [subscribed, setSubscribed] = useState(false)
  const [subId, setSubId]         = useState(null)
  const [loading, setLoading]     = useState(false)
  const [checking, setChecking]   = useState(true)
  const [tab, setTab]             = useState('base')   // base | planning | recipients

  // Champs base
  const [email, setEmail]         = useState('')
  const [frequency, setFrequency] = useState('daily')
  const [format, setFormat]       = useState('excel')
  const [channel, setChannel]     = useState('email')
  const [contactInfo, setContactInfo] = useState('')

  // Planification avancée
  const [heureEnvoi, setHeureEnvoi]     = useState(7)
  const [jourSemaine, setJourSemaine]   = useState(0)    // 0=lundi
  const [jourMois, setJourMois]         = useState(1)    // 1-28
  const [dateDebut, setDateDebut]       = useState('')
  const [dateFin, setDateFin]           = useState('')

  // Destinataires supplémentaires
  const [recipients, setRecipients]     = useState([])   // {channel, contact_info, nom}
  const [newRcpChannel, setNewRcpChannel] = useState('email')
  const [newRcpContact, setNewRcpContact] = useState('')
  const [newRcpNom, setNewRcpNom]       = useState('')

  const [successMsg, setSuccessMsg] = useState('')
  const [errorMsg, setErrorMsg]     = useState('')

  useEffect(() => {
    if (user?.email) { setEmail(user.email); setContactInfo(user.email) }
  }, [user])

  useEffect(() => {
    if (channel === 'email') setContactInfo(email)
  }, [email, channel])

  useEffect(() => {
    if (!reportId || !email) { setChecking(false); return }
    checkSubscription()
  }, [reportId, email])

  async function checkSubscription() {
    setChecking(true)
    try {
      const res = await api.get('/subscriptions/check', {
        params: { email, report_type: reportType, report_id: reportId }
      })
      if (res.data?.success && res.data.subscribed) {
        const s = res.data.subscription
        setSubscribed(true)
        setSubId(s?.id)
        setFrequency(s?.frequency || 'daily')
        setFormat(s?.export_format || 'excel')
        setHeureEnvoi(s?.heure_envoi ?? 7)
        setJourSemaine(s?.jour_semaine ?? 0)
        setJourMois(s?.jour_mois ?? 1)
        setDateDebut(s?.date_debut ? s.date_debut.slice(0,10) : '')
        setDateFin(s?.date_fin   ? s.date_fin.slice(0,10)   : '')
      } else {
        setSubscribed(false); setSubId(null)
      }
    } catch {} finally { setChecking(false) }
  }

  async function subscribe() {
    if (!email || !/\S+@\S+\.\S+/.test(email)) { setErrorMsg('Email invalide'); return }
    if (channel !== 'email' && !contactInfo.trim()) {
      setErrorMsg('Veuillez saisir votre ' + (channel === 'whatsapp' ? 'numéro WhatsApp' : 'Chat ID Telegram'))
      return
    }
    setLoading(true); setErrorMsg('')
    try {
      const res = await api.post('/subscriptions', {
        user_email: email,
        report_type: reportType,
        report_id: reportId,
        report_nom: reportNom,
        frequency,
        export_format: format,
        channel,
        contact_info: contactInfo.trim() || email,
        heure_envoi: heureEnvoi,
        jour_semaine: frequency === 'weekly'  ? jourSemaine : null,
        jour_mois:    frequency === 'monthly' ? jourMois    : null,
        date_debut: dateDebut || null,
        date_fin:   dateFin   || null,
        recipients: recipients.filter(r => r.contact_info),
      })
      if (res.data?.success) {
        setSubscribed(true)
        setSubId(res.data.id)
        setSuccessMsg(`Abonné(e) — première livraison ${res.data.next_send || 'demain'}`)
        setTimeout(() => { setSuccessMsg(''); setOpen(false) }, 2500)
      } else {
        setErrorMsg(res.data?.error || 'Erreur lors de l\'abonnement')
      }
    } catch { setErrorMsg('Erreur réseau') } finally { setLoading(false) }
  }

  async function unsubscribe() {
    if (!subId) return
    setLoading(true)
    try {
      await api.delete(`/subscriptions/${subId}`)
      setSubscribed(false); setSubId(null); setOpen(false)
    } catch { setErrorMsg('Erreur lors du désabonnement') } finally { setLoading(false) }
  }

  function addRecipient() {
    if (!newRcpContact.trim()) return
    setRecipients(p => [...p, { channel: newRcpChannel, contact_info: newRcpContact.trim(), nom: newRcpNom.trim() }])
    setNewRcpContact(''); setNewRcpNom('')
  }

  const freqDesc = () => {
    const h = `${heureEnvoi}h00`
    if (frequency === 'daily')   return `Chaque jour à ${h}`
    if (frequency === 'weekly')  return `Chaque ${DAYS_FR[jourSemaine]} à ${h}`
    if (frequency === 'monthly') return `Le ${jourMois} de chaque mois à ${h}`
    return ''
  }

  const tabCls = (k) => `px-2 py-1 text-xs rounded font-medium transition-colors ${
    tab === k
      ? 'bg-white dark:bg-gray-700 text-gray-800 dark:text-white shadow-sm'
      : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
  }`

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(o => !o)}
        disabled={checking}
        className={`flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-lg transition-colors
          ${subscribed
            ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300 hover:bg-green-100'
            : 'bg-gray-50 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-600'
          } disabled:opacity-50`}
        title={subscribed ? 'Gérer mon abonnement' : 'S\'abonner à ce rapport'}
      >
        {checking ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
          : subscribed ? <><BellOff className="w-3.5 h-3.5" />Abonné</>
          : <><Bell className="w-3.5 h-3.5" />S'abonner</>
        }
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 mt-1 w-96 bg-white dark:bg-gray-800 rounded-xl shadow-2xl border border-gray-200 dark:border-gray-700 z-50 max-h-[90vh] overflow-y-auto">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700 sticky top-0 bg-white dark:bg-gray-800 z-10">
              <div className="flex items-center gap-2">
                <Mail className="w-4 h-4" style={{ color: 'var(--color-primary-500)' }} />
                <span className="text-sm font-semibold text-gray-900 dark:text-white">
                  {subscribed ? 'Mon abonnement' : 'S\'abonner au rapport'}
                </span>
              </div>
              <button onClick={() => setOpen(false)} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Sous-onglets */}
            {!subscribed && (
              <div className="flex gap-1 px-4 pt-3 bg-gray-50 dark:bg-gray-700/50 border-b border-gray-200 dark:border-gray-700 pb-2">
                <button className={tabCls('base')}      onClick={() => setTab('base')}>
                  <Bell className="w-3 h-3 inline mr-1" />Base
                </button>
                <button className={tabCls('planning')}  onClick={() => setTab('planning')}>
                  <Clock className="w-3 h-3 inline mr-1" />Planification
                </button>
                <button className={tabCls('recipients')} onClick={() => setTab('recipients')}>
                  <Users className="w-3 h-3 inline mr-1" />Destinataires
                  {recipients.length > 0 && (
                    <span className="ml-1 text-[9px] px-1 rounded-full bg-indigo-500 text-white">{recipients.length}</span>
                  )}
                </button>
              </div>
            )}

            <div className="p-4 space-y-3">
              <p className="text-xs text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-700 rounded-lg px-3 py-2 truncate">
                {reportNom}
              </p>

              {/* ── TAB BASE ── */}
              {(tab === 'base' || subscribed) && (
                <>
                  {/* Canal */}
                  {!subscribed && (
                    <div>
                      <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1.5">Canal de livraison</label>
                      <div className="flex gap-1.5">
                        {CHANNELS.map(ch => (
                          <button key={ch.key} type="button"
                            onClick={() => { setChannel(ch.key); setErrorMsg('') }}
                            className={`flex-1 flex flex-col items-center gap-0.5 py-2 rounded-lg border text-xs transition-colors ${
                              channel === ch.key
                                ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300 font-medium'
                                : 'border-gray-200 dark:border-gray-600 text-gray-500 dark:text-gray-400 hover:border-gray-300'
                            }`}
                            style={channel === ch.key ? { borderColor: 'var(--color-primary-400)' } : {}}
                          >
                            <span className="text-base leading-none">{ch.icon}</span>
                            <span>{ch.label}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Email */}
                  <div>
                    <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Adresse email <span className="text-gray-400">(identification)</span>
                    </label>
                    <input type="email" value={email}
                      onChange={e => { setEmail(e.target.value); setErrorMsg('') }}
                      disabled={subscribed} placeholder="votre@email.com"
                      className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 disabled:opacity-60 disabled:cursor-not-allowed"
                    />
                  </div>

                  {/* Contact canal */}
                  {!subscribed && channel !== 'email' && (
                    <div>
                      <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                        {channel === 'whatsapp' ? 'Numéro WhatsApp' : 'Chat ID Telegram'}
                      </label>
                      <input type="text" value={contactInfo}
                        onChange={e => { setContactInfo(e.target.value); setErrorMsg('') }}
                        placeholder={CHANNELS.find(c => c.key === channel)?.placeholder}
                        className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2"
                      />
                      <p className="text-[10px] text-gray-400 mt-1">{CHANNELS.find(c => c.key === channel)?.hint}</p>
                    </div>
                  )}

                  {/* Fréquence */}
                  <div>
                    <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Fréquence</label>
                    <div className="grid grid-cols-3 gap-1.5">
                      {FREQUENCIES.map(f => (
                        <button key={f.key} disabled={subscribed} onClick={() => setFrequency(f.key)}
                          className={`p-2 rounded-lg border text-xs text-center transition-colors disabled:opacity-60 disabled:cursor-not-allowed
                            ${frequency === f.key
                              ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300 font-medium'
                              : 'border-gray-200 dark:border-gray-600 hover:border-gray-300 text-gray-600 dark:text-gray-300'
                            }`}
                          style={frequency === f.key ? { borderColor: 'var(--color-primary-400)' } : {}}
                        >
                          <div className="font-medium">{f.label}</div>
                        </button>
                      ))}
                    </div>
                    {!subscribed && (
                      <p className="text-[10px] text-indigo-500 mt-1">📅 {freqDesc()}</p>
                    )}
                  </div>

                  {/* Format */}
                  <div>
                    <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Format</label>
                    <div className="flex gap-2">
                      {FORMATS.map(f => (
                        <button key={f.key} disabled={subscribed} onClick={() => setFormat(f.key)}
                          className={`flex-1 py-1.5 rounded-lg border text-xs transition-colors disabled:opacity-60
                            ${format === f.key
                              ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300 font-medium'
                              : 'border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:border-gray-300'
                            }`}
                          style={format === f.key ? { borderColor: 'var(--color-primary-400)' } : {}}
                        >
                          {f.label}
                        </button>
                      ))}
                    </div>
                  </div>
                </>
              )}

              {/* ── TAB PLANIFICATION ── */}
              {tab === 'planning' && !subscribed && (
                <div className="space-y-3">
                  {/* Heure d'envoi */}
                  <div>
                    <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1 flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5" /> Heure d'envoi
                    </label>
                    <div className="flex flex-wrap gap-1">
                      {HOURS.map(h => (
                        <button key={h} onClick={() => setHeureEnvoi(h)}
                          className={`px-2 py-1 text-xs rounded-lg border transition-colors ${
                            heureEnvoi === h
                              ? 'border-indigo-400 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 font-medium'
                              : 'border-gray-200 dark:border-gray-600 text-gray-500 hover:border-gray-300'
                          }`}
                        >
                          {h}h
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Jour de la semaine (weekly) */}
                  {frequency === 'weekly' && (
                    <div>
                      <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Jour de la semaine</label>
                      <div className="grid grid-cols-7 gap-1">
                        {DAYS_FR.map((d, i) => (
                          <button key={i} onClick={() => setJourSemaine(i)}
                            className={`py-1.5 text-[10px] rounded border transition-colors text-center ${
                              jourSemaine === i
                                ? 'border-indigo-400 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 font-semibold'
                                : 'border-gray-200 dark:border-gray-600 text-gray-500 hover:border-gray-300'
                            }`}
                          >
                            {d.slice(0,3)}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Jour du mois (monthly) */}
                  {frequency === 'monthly' && (
                    <div>
                      <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Jour du mois</label>
                      <div className="flex flex-wrap gap-1">
                        {Array.from({length: 28}, (_,i) => i+1).map(d => (
                          <button key={d} onClick={() => setJourMois(d)}
                            className={`w-8 h-7 text-xs rounded border transition-colors ${
                              jourMois === d
                                ? 'border-indigo-400 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 font-semibold'
                                : 'border-gray-200 dark:border-gray-600 text-gray-500 hover:border-gray-300'
                            }`}
                          >
                            {d}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Période de validité */}
                  <div>
                    <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1 flex items-center gap-1">
                      <Calendar className="w-3.5 h-3.5" /> Période de validité <span className="text-gray-400 font-normal">(optionnel)</span>
                    </label>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <p className="text-[10px] text-gray-400 mb-0.5">À partir du</p>
                        <input type="date" value={dateDebut} onChange={e => setDateDebut(e.target.value)}
                          className="w-full text-xs rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-400"
                        />
                      </div>
                      <div>
                        <p className="text-[10px] text-gray-400 mb-0.5">Jusqu'au</p>
                        <input type="date" value={dateFin} onChange={e => setDateFin(e.target.value)}
                          min={dateDebut}
                          className="w-full text-xs rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-400"
                        />
                      </div>
                    </div>
                    {dateFin && <p className="text-[10px] text-amber-500 mt-1">⚠ L'abonnement se désactivera automatiquement à cette date.</p>}
                  </div>

                  <div className="p-2 bg-indigo-50 dark:bg-indigo-900/20 rounded-lg">
                    <p className="text-[10px] text-indigo-600 dark:text-indigo-400 font-medium">📅 Résumé : {freqDesc()}{dateDebut ? ` · Du ${dateDebut}` : ''}{dateFin ? ` au ${dateFin}` : ''}</p>
                  </div>
                </div>
              )}

              {/* ── TAB DESTINATAIRES ── */}
              {tab === 'recipients' && !subscribed && (
                <div className="space-y-3">
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    Ajoutez d'autres personnes qui recevront ce rapport à chaque livraison.
                  </p>

                  {/* Ajouter un destinataire */}
                  <div className="p-3 border border-dashed border-gray-300 dark:border-gray-600 rounded-lg space-y-2">
                    <div className="flex gap-1.5">
                      {CHANNELS.map(ch => (
                        <button key={ch.key} type="button"
                          onClick={() => setNewRcpChannel(ch.key)}
                          className={`flex-1 py-1 text-xs rounded border transition-colors ${
                            newRcpChannel === ch.key
                              ? 'border-indigo-400 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600'
                              : 'border-gray-200 dark:border-gray-600 text-gray-400 hover:border-gray-300'
                          }`}
                        >
                          {ch.icon} {ch.label}
                        </button>
                      ))}
                    </div>
                    <input type="text" value={newRcpNom} onChange={e => setNewRcpNom(e.target.value)}
                      placeholder="Nom (optionnel)"
                      className="w-full text-xs rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 px-2 py-1.5 focus:outline-none"
                    />
                    <div className="flex gap-1.5">
                      <input type="text" value={newRcpContact} onChange={e => setNewRcpContact(e.target.value)}
                        placeholder={CHANNELS.find(c => c.key === newRcpChannel)?.placeholder}
                        className="flex-1 text-xs rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 px-2 py-1.5 focus:outline-none"
                        onKeyDown={e => e.key === 'Enter' && addRecipient()}
                      />
                      <button onClick={addRecipient}
                        disabled={!newRcpContact.trim()}
                        className="px-2 py-1.5 text-xs rounded bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-40 transition-colors"
                      >
                        <Plus className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  {/* Liste */}
                  {recipients.length === 0 ? (
                    <p className="text-xs text-center text-gray-400 py-2">Aucun destinataire supplémentaire</p>
                  ) : (
                    <div className="space-y-1">
                      {recipients.map((r, i) => {
                        const ch = CHANNELS.find(c => c.key === r.channel)
                        return (
                          <div key={i} className="flex items-center gap-2 text-xs p-2 rounded-lg bg-gray-50 dark:bg-gray-700">
                            <span>{ch?.icon}</span>
                            <span className="flex-1 text-gray-700 dark:text-gray-200 truncate">
                              {r.nom ? <><strong>{r.nom}</strong> · </> : null}{r.contact_info}
                            </span>
                            <button onClick={() => setRecipients(p => p.filter((_, j) => j !== i))}
                              className="text-gray-400 hover:text-red-500 p-0.5">
                              <Trash2 className="w-3 h-3" />
                            </button>
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              )}

              {/* Messages */}
              {successMsg && (
                <div className="flex items-center gap-2 p-2 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg text-xs text-green-700 dark:text-green-300">
                  <Check className="w-3.5 h-3.5 flex-shrink-0" />{successMsg}
                </div>
              )}
              {errorMsg && <p className="text-xs text-red-600 dark:text-red-400">{errorMsg}</p>}

              {/* Actions */}
              <div className="flex gap-2 pt-1">
                {subscribed ? (
                  <>
                    <button onClick={unsubscribe} disabled={loading}
                      className="flex-1 py-2 text-xs font-medium rounded-lg border border-red-300 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors disabled:opacity-50">
                      {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin mx-auto" /> : 'Se désabonner'}
                    </button>
                    <button onClick={() => setOpen(false)}
                      className="flex-1 py-2 text-xs font-medium rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 transition-colors">
                      Fermer
                    </button>
                  </>
                ) : (
                  <>
                    <button onClick={() => setOpen(false)}
                      className="py-2 px-3 text-xs rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
                      Annuler
                    </button>
                    <button onClick={subscribe} disabled={loading || !email}
                      className="flex-1 py-2 text-xs font-medium rounded-lg text-white transition-colors disabled:opacity-50"
                      style={{ backgroundColor: 'var(--color-primary-600)' }}>
                      {loading
                        ? <Loader2 className="w-3.5 h-3.5 animate-spin mx-auto" />
                        : `Confirmer${recipients.length > 0 ? ` (${recipients.length + 1} dest.)` : ''}`
                      }
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
