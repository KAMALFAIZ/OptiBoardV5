/**
 * MobileProfilePage — Page profil complète (mobile)
 * Sections : Profil · Favoris · Préférences · Sécurité · Déconnexion
 */
import { useState, useEffect, useCallback } from 'react'
import {
  User, KeyRound, Eye, EyeOff, CheckCircle2, LogOut,
  Star, Trash2, Bell, BellOff, Moon, Sun,
  DollarSign, Globe, Hash, ChevronRight,
  Database, Shield, Settings2, Loader2, AlertTriangle,
  LayoutDashboard, Table2, PieChart,
} from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { useDWH } from '../../context/DWHContext'
import { useTheme } from '../../context/ThemeContext'
import api from '../../services/api'

// ─── Champs favoris ───────────────────────────────────────────────────────────
const TYPE_ICONS = { dashboard: LayoutDashboard, gridview: Table2, pivot: PieChart, 'pivot-v2': PieChart }
const TYPE_LABELS = { dashboard: 'Dashboard', gridview: 'Grid', pivot: 'Pivot', 'pivot-v2': 'Pivot' }
const TYPE_COLORS = {
  dashboard: 'bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400',
  gridview:  'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400',
  pivot:     'bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-400',
  'pivot-v2':'bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-400',
}

// ─── Préférences (clé localStorage) ──────────────────────────────────────────
const PREFS_KEY_PREFIX = 'user_prefs_'
const DEFAULT_PREFS = { devise: 'MAD', separateur: 'fr', formatDate: 'dmy', }
function loadPrefs(userId) {
  try { return { ...DEFAULT_PREFS, ...JSON.parse(localStorage.getItem(PREFS_KEY_PREFIX + userId)) } }
  catch { return DEFAULT_PREFS }
}
function savePrefs(userId, prefs) {
  localStorage.setItem(PREFS_KEY_PREFIX + userId, JSON.stringify(prefs))
}

// ─── Section wrapper ──────────────────────────────────────────────────────────
function Section({ title, icon: Icon, children }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm overflow-hidden mb-3">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-100 dark:border-gray-700">
        <Icon className="w-4 h-4 text-primary-500" />
        <span className="text-sm font-semibold text-gray-700 dark:text-gray-200">{title}</span>
      </div>
      {children}
    </div>
  )
}

// ─── Row toggle ───────────────────────────────────────────────────────────────
function ToggleRow({ label, sub, checked, onChange, disabled }) {
  return (
    <div className="flex items-center justify-between px-4 py-3">
      <div>
        <p className="text-sm font-medium text-gray-900 dark:text-white">{label}</p>
        {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
      </div>
      <button
        onClick={onChange}
        disabled={disabled}
        className={`relative w-11 h-6 rounded-full transition-colors duration-200 flex-shrink-0 ${
          checked ? 'bg-primary-600' : 'bg-gray-300 dark:bg-gray-600'
        } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        <span className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform duration-200 ${checked ? 'translate-x-5' : ''}`} />
      </button>
    </div>
  )
}

// ─── Row select ───────────────────────────────────────────────────────────────
function SelectRow({ label, value, options, onChange }) {
  return (
    <div className="flex items-center justify-between px-4 py-3">
      <p className="text-sm font-medium text-gray-900 dark:text-white">{label}</p>
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        className="text-sm text-gray-700 dark:text-gray-200 bg-gray-100 dark:bg-gray-700 rounded-lg px-2 py-1 border-none focus:outline-none focus:ring-2 focus:ring-primary-500"
      >
        {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  )
}

// ─── Champ mot de passe ───────────────────────────────────────────────────────
function PasswordField({ label, field, form, setForm, show, setShow }) {
  return (
    <div className="px-4 pb-3">
      <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">{label}</label>
      <div className="relative">
        <input
          type={show[field] ? 'text' : 'password'}
          value={form[field]}
          onChange={e => setForm(f => ({ ...f, [field]: e.target.value }))}
          className="w-full h-11 px-3 pr-11 rounded-xl border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700/50 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          placeholder="••••••••"
          required
        />
        <button type="button" onClick={() => setShow(s => ({ ...s, [field]: !s[field] }))}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">
          {show[field] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
        </button>
      </div>
    </div>
  )
}

// ─── Page principale ──────────────────────────────────────────────────────────
export default function MobileProfilePage() {
  const { user, logout } = useAuth()
  const { currentDWH, dwhList } = useDWH()
  const { darkMode, setDarkMode } = useTheme()

  // ── Favoris ───────────────────────────────────────────────────────────────
  const [favorites, setFavorites] = useState([])
  const [favLoading, setFavLoading] = useState(true)
  const [removingFav, setRemovingFav] = useState(null)

  const loadFavorites = useCallback(async () => {
    if (!user?.id) return
    try {
      const res = await api.get('/favorites', { params: { user_id: user.id } })
      setFavorites(res.data?.data || [])
    } catch { setFavorites([]) }
    finally { setFavLoading(false) }
  }, [user?.id])

  useEffect(() => { loadFavorites() }, [loadFavorites])

  const removeFavorite = async (fav) => {
    const key = `${fav.report_type}_${fav.report_id}`
    setRemovingFav(key)
    try {
      await api.delete('/favorites', { params: { user_id: user.id, report_type: fav.report_type, report_id: fav.report_id } })
      setFavorites(prev => prev.filter(f => !(f.report_type === fav.report_type && f.report_id === fav.report_id)))
    } catch { /* silencieux */ }
    finally { setRemovingFav(null) }
  }

  // ── Préférences ───────────────────────────────────────────────────────────
  const [prefs, setPrefs] = useState(() => loadPrefs(user?.id))
  const updatePref = (key, val) => {
    setPrefs(prev => {
      const updated = { ...prev, [key]: val }
      savePrefs(user?.id, updated)
      return updated
    })
  }

  // ── Notifications push ────────────────────────────────────────────────────
  const [notifPerm, setNotifPerm] = useState('default')
  useEffect(() => {
    if ('Notification' in window) setNotifPerm(Notification.permission)
  }, [])

  const handleToggleNotif = async () => {
    if (!('Notification' in window)) return
    if (notifPerm === 'granted') {
      // On ne peut pas révoquer depuis le code — orienter vers les paramètres navigateur
      alert('Pour désactiver, modifiez les permissions dans les paramètres de votre navigateur.')
      return
    }
    const perm = await Notification.requestPermission()
    setNotifPerm(perm)
    if (perm === 'granted') {
      new Notification('OptiBoard', {
        body: 'Notifications activées ! Vous serez alerté en cas d\'alerte KPI critique.',
        icon: '/favicon.ico',
      })
      localStorage.setItem(`notif_enabled_${user?.id}`, '1')
    }
  }

  // ── Changer mot de passe ──────────────────────────────────────────────────
  const [pwForm, setPwForm] = useState({ current: '', next: '', confirm: '' })
  const [pwShow, setPwShow] = useState({ current: false, next: false, confirm: false })
  const [pwLoading, setPwLoading] = useState(false)
  const [pwError, setPwError] = useState('')
  const [pwSuccess, setPwSuccess] = useState(false)

  const handlePwSubmit = async (e) => {
    e.preventDefault()
    setPwError('')
    if (pwForm.next !== pwForm.confirm) { setPwError('Les mots de passe ne correspondent pas.'); return }
    if (pwForm.next.length < 6) { setPwError('Minimum 6 caractères.'); return }
    setPwLoading(true)
    try {
      await api.post('/auth/change-password', { current_password: pwForm.current, new_password: pwForm.next })
      setPwSuccess(true)
      setPwForm({ current: '', next: '', confirm: '' })
    } catch (err) {
      setPwError(err.response?.data?.detail || 'Erreur lors du changement.')
    } finally { setPwLoading(false) }
  }

  const initials = [user?.prenom?.[0], user?.nom?.[0]].filter(Boolean).join('').toUpperCase() || user?.username?.[0]?.toUpperCase() || '?'
  const fullName = [user?.prenom, user?.nom].filter(Boolean).join(' ') || user?.username

  return (
    <div className="p-3 pb-24 max-w-md mx-auto">

      {/* ── Carte profil ────────────────────────────── */}
      <div className="bg-gradient-to-br from-primary-600 to-primary-700 dark:from-primary-700 dark:to-primary-900 rounded-2xl p-5 mb-3 text-white shadow-md">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-full bg-white/20 flex items-center justify-center flex-shrink-0 text-xl font-bold">
            {initials}
          </div>
          <div className="flex-1 min-w-0">
            <h1 className="font-bold text-lg leading-tight truncate">{fullName}</h1>
            <p className="text-white/70 text-sm truncate">@{user?.username}</p>
            {(user?.role_dwh || user?.role_global || user?.role) && (
              <span className="inline-block mt-1 bg-white/20 text-white text-xs font-semibold px-2 py-0.5 rounded-full capitalize">
                {user?.role_dwh || user?.role_global || user?.role}
              </span>
            )}
          </div>
        </div>
        {currentDWH?.nom && (
          <div className="mt-3 flex items-center gap-2 bg-white/10 rounded-xl px-3 py-2">
            <Database className="w-3.5 h-3.5 text-white/70" />
            <span className="text-sm text-white/90 font-medium truncate">{currentDWH.nom}</span>
            {dwhList.length > 1 && <span className="ml-auto text-white/50 text-xs">{dwhList.length} bases</span>}
          </div>
        )}
      </div>

      {/* ── Favoris ─────────────────────────────────── */}
      <Section title="Mes Favoris" icon={Star}>
        {favLoading ? (
          <div className="flex justify-center py-6">
            <Loader2 className="w-5 h-5 text-primary-400 animate-spin" />
          </div>
        ) : favorites.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-6">Aucun favori enregistré</p>
        ) : (
          <div className="divide-y divide-gray-100 dark:divide-gray-700/50">
            {favorites.map(fav => {
              const IconComp = TYPE_ICONS[fav.report_type] || Star
              const colorClass = TYPE_COLORS[fav.report_type] || TYPE_COLORS.dashboard
              const key = `${fav.report_type}_${fav.report_id}`
              const isRemoving = removingFav === key
              return (
                <div key={key} className="flex items-center gap-3 px-4 py-3">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${colorClass}`}>
                    <IconComp className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{fav.nom || `#${fav.report_id}`}</p>
                    <p className="text-xs text-gray-400">{TYPE_LABELS[fav.report_type] || fav.report_type}</p>
                  </div>
                  <button
                    onClick={() => removeFavorite(fav)}
                    disabled={isRemoving}
                    className="p-2 rounded-lg text-gray-300 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors flex-shrink-0"
                  >
                    {isRemoving
                      ? <Loader2 className="w-4 h-4 animate-spin" />
                      : <Trash2 className="w-4 h-4" />}
                  </button>
                </div>
              )
            })}
          </div>
        )}
      </Section>

      {/* ── Préférences ─────────────────────────────── */}
      <Section title="Préférences" icon={Settings2}>
        <ToggleRow
          label="Mode sombre"
          sub="Thème de l'interface"
          checked={darkMode}
          onChange={() => setDarkMode(!darkMode)}
        />
        <div className="border-t border-gray-100 dark:border-gray-700/50" />
        <ToggleRow
          label="Notifications push"
          sub={notifPerm === 'granted' ? 'Activées' : notifPerm === 'denied' ? 'Bloquées dans le navigateur' : 'Alertes KPI critiques'}
          checked={notifPerm === 'granted'}
          onChange={handleToggleNotif}
          disabled={notifPerm === 'denied'}
        />
        {notifPerm === 'denied' && (
          <div className="px-4 pb-3">
            <p className="text-xs text-amber-600 dark:text-amber-400 flex items-start gap-1.5 bg-amber-50 dark:bg-amber-900/20 p-2 rounded-lg">
              <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
              Notifications bloquées. Activez-les dans les paramètres de votre navigateur.
            </p>
          </div>
        )}
        <div className="border-t border-gray-100 dark:border-gray-700/50" />
        <SelectRow
          label="Devise d'affichage"
          value={prefs.devise}
          onChange={val => updatePref('devise', val)}
          options={[{ value: 'MAD', label: 'MAD (Dirham)' }, { value: 'EUR', label: 'EUR (Euro)' }, { value: 'USD', label: 'USD (Dollar)' }]}
        />
        <div className="border-t border-gray-100 dark:border-gray-700/50" />
        <SelectRow
          label="Format des nombres"
          value={prefs.separateur}
          onChange={val => updatePref('separateur', val)}
          options={[{ value: 'fr', label: '1 234 567,89' }, { value: 'en', label: '1,234,567.89' }]}
        />
        <div className="border-t border-gray-100 dark:border-gray-700/50" />
        <SelectRow
          label="Format de date"
          value={prefs.formatDate}
          onChange={val => updatePref('formatDate', val)}
          options={[{ value: 'dmy', label: 'JJ/MM/AAAA' }, { value: 'mdy', label: 'MM/JJ/AAAA' }, { value: 'ymd', label: 'AAAA-MM-JJ' }]}
        />
      </Section>

      {/* ── Sécurité ─────────────────────────────────── */}
      <Section title="Sécurité" icon={Shield}>
        {pwSuccess ? (
          <div className="flex flex-col items-center py-6 gap-3">
            <CheckCircle2 className="w-10 h-10 text-green-500" />
            <p className="text-green-700 dark:text-green-400 font-medium text-sm">Mot de passe modifié !</p>
            <button onClick={() => setPwSuccess(false)} className="text-xs text-primary-600 underline">Modifier à nouveau</button>
          </div>
        ) : (
          <form onSubmit={handlePwSubmit}>
            <div className="pt-3">
              <PasswordField label="Mot de passe actuel" field="current" form={pwForm} setForm={setPwForm} show={pwShow} setShow={setPwShow} />
              <PasswordField label="Nouveau mot de passe" field="next" form={pwForm} setForm={setPwForm} show={pwShow} setShow={setPwShow} />
              <PasswordField label="Confirmer le nouveau mot de passe" field="confirm" form={pwForm} setForm={setPwForm} show={pwShow} setShow={setPwShow} />
            </div>
            {pwError && (
              <div className="mx-4 mb-3 text-xs text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 p-2.5 rounded-lg">{pwError}</div>
            )}
            <div className="px-4 pb-4">
              <button type="submit" disabled={pwLoading}
                className="w-full h-11 rounded-xl bg-primary-600 hover:bg-primary-700 disabled:opacity-60 text-white font-semibold text-sm transition-colors">
                {pwLoading ? <span className="flex items-center justify-center gap-2"><Loader2 className="w-4 h-4 animate-spin" />Enregistrement...</span> : 'Enregistrer'}
              </button>
            </div>
          </form>
        )}
      </Section>

      {/* ── Déconnexion ──────────────────────────────── */}
      <button
        onClick={() => logout()}
        className="w-full h-12 rounded-2xl border border-red-200 dark:border-red-800/40 text-red-600 dark:text-red-400 font-semibold text-sm flex items-center justify-center gap-2 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
      >
        <LogOut className="w-4 h-4" />
        Déconnexion
      </button>

      <p className="text-center text-xs text-gray-300 dark:text-gray-600 mt-4">
        OptiBoard · v{APP_VERSION || '1.0'}
      </p>
    </div>
  )
}

// Fallback version
const APP_VERSION = typeof __APP_VERSION__ !== 'undefined' ? __APP_VERSION__ : null
