import { useState, useEffect, useMemo, useCallback } from 'react'
import {
  Link as LinkIcon, X, Loader2, Plus, Search, ChevronRight, Rows3,
  AlertTriangle, ShieldCheck,
} from 'lucide-react'
import {
  getMenusFlat, createMenu, updateMenu, detachMenu as detachMenuApi,
  getReportAccess, setReportAccess,
} from '../services/api'
import { useToast } from './common/Toast'

/**
 * Modale « Attacher au menu dynamique », partagée par PivotBuilderV2,
 * GridViewBuilder et DashboardBuilder (elle y était triplement dupliquée,
 * chaque copie ayant dérivé de son côté).
 *
 * Props :
 *   open        bool
 *   onClose     () => void
 *   menuType    'pivot-v2' | 'gridview' | 'dashboard' | 'pivot'
 *   reportId    id du rapport à attacher
 *   reportName  nom du rapport (pré-remplit nom + code)
 *   icon        icône lucide enregistrée en base pour le menu
 *   notify      (message, 'success'|'error') => void   (optionnel)
 */

const TYPE_LABEL = {
  'pivot-v2':  'Pivot',
  'pivot':     'Pivot',
  'gridview':  'Grille',
  'dashboard': 'Dashboard',
}

const REPORT_TYPE = {
  'pivot-v2':  'pivot',
  'pivot':     'pivot',
  'gridview':  'gridview',
  'dashboard': 'dashboard',
}

/** Même normalisation que `normalize_menu_code()` côté backend. */
export function normalizeMenuCode(raw) {
  if (!raw) return ''
  return String(raw)
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-+|-+$)/g, '')
    .slice(0, 100)
}

/** Les routes menus renvoient 200 + {success:false} au lieu d'une erreur HTTP. */
function unwrap(res) {
  const data = res?.data
  if (data && data.success === false) {
    throw new Error(data.error || 'Opération refusée par le serveur')
  }
  return data || {}
}

function errText(err, fallback) {
  return err?.response?.data?.detail || err?.message || fallback
}

export default function AttachMenuModal({
  open, onClose, menuType, reportId, reportName, icon = 'Rows3', notify,
}) {
  const toast = useToast()
  const say = useCallback((msg, type = 'success') => {
    if (notify) notify(msg, type)
    else if (type === 'error') toast.error(msg)
    else toast.success(msg)
  }, [notify, toast])

  const [menuFlat, setMenuFlat] = useState([])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  const [newMenuNom, setNewMenuNom] = useState('')
  const [newMenuCode, setNewMenuCode] = useState('')
  const [newMenuParentId, setNewMenuParentId] = useState('')
  const [parentPickerOpen, setParentPickerOpen] = useState(false)
  const [parentSearch, setParentSearch] = useState('')

  const [attachExistingId, setAttachExistingId] = useState('')
  const [existingPickerOpen, setExistingPickerOpen] = useState(false)
  const [existingSearch, setExistingSearch] = useState('')

  const [grantAccess, setGrantAccess] = useState(true)
  const [access, setAccess] = useState(null)

  const typeLabel = TYPE_LABEL[menuType] || 'rapport'
  const reportType = REPORT_TYPE[menuType] || menuType

  // ── Chargement ────────────────────────────────────────────────────────
  const loadMenus = useCallback(async (silent = false) => {
    if (!silent) setLoading(true)
    try {
      // include_central : le menu réellement affiché fusionne client + central.
      // Sans cela un rapport déjà attaché côté central paraît « non attaché ».
      const res = await getMenusFlat(true)
      setMenuFlat(unwrap(res).data || [])
    } catch (err) {
      console.error('Erreur chargement menus:', err)
      say(errText(err, 'Erreur lors du chargement des menus'), 'error')
      setMenuFlat([])
    } finally {
      if (!silent) setLoading(false)
    }
  }, [say])

  const loadAccess = useCallback(async () => {
    if (!reportId) return
    try {
      const data = unwrap(await getReportAccess(reportType, reportId))
      setAccess(data)
    } catch (err) {
      console.warn('Droits rapport indisponibles:', err)
      setAccess(null)
    }
  }, [reportType, reportId])

  useEffect(() => {
    if (!open) return
    setNewMenuNom(reportName || '')
    setNewMenuCode(normalizeMenuCode(reportName || ''))
    setNewMenuParentId('')
    setAttachExistingId('')
    setParentPickerOpen(false)
    setParentSearch('')
    setExistingPickerOpen(false)
    setExistingSearch('')
    setGrantAccess(true)
    setAccess(null)
    loadMenus()
    loadAccess()
  }, [open, reportId, reportName, loadMenus, loadAccess])

  // ── Dérivés ───────────────────────────────────────────────────────────
  const sameId = (a, b) => a != null && b != null && Number(a) === Number(b)

  const linkedMenus = useMemo(
    () => menuFlat.filter(m => m.type === menuType && sameId(m.target_id, reportId)),
    [menuFlat, menuType, reportId]
  )

  // Un menu du catalogue central n'est pas modifiable depuis la base client.
  const attachableMenus = useMemo(
    () => menuFlat.filter(m =>
      m.type === menuType && !sameId(m.target_id, reportId) && m.editable !== false
    ),
    [menuFlat, menuType, reportId]
  )

  // Emplacement = dossiers uniquement (on ne range pas un état sous un état).
  const folders = useMemo(
    () => menuFlat.filter(m => !m.target_id && (!m.type || m.type === 'folder')),
    [menuFlat]
  )

  const usedCodes = useMemo(
    () => new Set(menuFlat.map(m => (m.code || '').toLowerCase()).filter(Boolean)),
    [menuFlat]
  )
  const codeTaken = !!newMenuCode && usedCodes.has(newMenuCode.toLowerCase())
  const canCreate = !!newMenuNom.trim() && !!newMenuCode.trim() && !codeTaken && !saving

  const menuLabel = (m) => `${m.parent_name ? m.parent_name + ' > ' : ''}${m.nom}`
  const matches = (m, q) => !q || [m.nom, m.parent_name, m.code]
    .some(v => (v || '').toLowerCase().includes(q))

  // ── Actions ───────────────────────────────────────────────────────────
  const createAndAttach = async () => {
    if (!reportId || !canCreate) return
    setSaving(true)
    try {
      const data = unwrap(await createMenu({
        parent_id: newMenuParentId ? parseInt(newMenuParentId, 10) : null,
        nom: newMenuNom.trim(),
        code: normalizeMenuCode(newMenuCode),
        icon,
        type: menuType,
        target_id: reportId,
        url: '',
        ordre: 0,
        is_active: true,
        grant_all_roles: grantAccess,
      }))
      if (data.ignored_columns?.length) {
        console.warn('Colonnes APP_Menus absentes, ignorées:', data.ignored_columns)
      }
      say('Menu créé et rapport attaché')
      await Promise.all([loadMenus(true), loadAccess()])
      setNewMenuNom('')
      setNewMenuCode('')
      setNewMenuParentId('')
    } catch (err) {
      console.error('Erreur création menu:', err)
      say(errText(err, 'Erreur lors de la création du menu'), 'error')
    } finally {
      setSaving(false)
    }
  }

  const attachToExisting = async () => {
    const menu = attachableMenus.find(m => String(m.id) === String(attachExistingId))
    if (!reportId || !menu) return
    setSaving(true)
    try {
      unwrap(await updateMenu(menu.id, {
        type: menuType,
        target_id: reportId,
        icon: menu.icon || icon,
      }))
      if (grantAccess) {
        try {
          await setReportAccess({
            report_type: reportType, report_id: reportId,
            all_roles: true, menu_id: menu.id,
          })
        } catch (e) {
          console.warn('Droits non appliqués:', e)
        }
      }
      say(`"${menu.nom}" pointe maintenant vers ce rapport`)
      await Promise.all([loadMenus(true), loadAccess()])
      setAttachExistingId('')
    } catch (err) {
      console.error('Erreur attachement menu:', err)
      say(errText(err, "Erreur lors de l'attachement"), 'error')
    } finally {
      setSaving(false)
    }
  }

  const detach = async (menu) => {
    if (!window.confirm(`Détacher "${menu.nom}" du menu ?`)) return
    setSaving(true)
    try {
      const data = unwrap(await detachMenuApi(menu.id))
      say(data.message || 'Menu détaché')
      await loadMenus(true)
    } catch (err) {
      console.error('Erreur détachement menu:', err)
      say(errText(err, 'Erreur lors du détachement'), 'error')
    } finally {
      setSaving(false)
    }
  }

  if (!open) return null

  const inputCls = 'w-full px-2.5 py-1.5 text-sm border border-primary-300 dark:border-primary-600 rounded-lg dark:bg-gray-700 dark:text-white'
  const optionCls = (selected) => `w-full text-left px-3 py-1.5 text-sm truncate ${selected
    ? 'bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300 font-medium'
    : 'text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700'}`

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-white dark:bg-gray-800 rounded-xl shadow-xl p-6 w-[560px] max-w-[92vw] max-h-[85vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <LinkIcon className="w-5 h-5 text-primary-500" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Attacher au menu dynamique</h2>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded">
            <X className="w-5 h-5" />
          </button>
        </div>

        {loading ? (
          <div className="py-10 text-center text-gray-400">
            <Loader2 className="w-5 h-5 animate-spin mx-auto mb-2" />
            Chargement des menus...
          </div>
        ) : (
          <div className="space-y-5">
            {/* Visibilité réelle du rapport */}
            {access?.admin_only && (
              <div className="flex items-start gap-2 px-3 py-2 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800">
                <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
                <p className="text-xs text-amber-800 dark:text-amber-200">
                  Ce rapport n'est visible que des administrateurs : aucun rôle n'y a accès.
                  Laissez l'option « Donner l'accès à tous les rôles » cochée pour le rendre visible.
                </p>
              </div>
            )}
            {access && !access.admin_only && access.roles_granted > 0 && (
              <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0" />
                Visible par {access.roles_granted}/{access.roles_total} rôle(s) non-admin.
              </div>
            )}

            {/* Menus actuellement liés */}
            <div>
              <label className="block text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
                Menus liés à ce rapport
              </label>
              {linkedMenus.length === 0 ? (
                <p className="text-sm text-gray-400">Ce rapport n'est encore attaché à aucun menu.</p>
              ) : (
                <div className="space-y-1.5">
                  {linkedMenus.map(m => (
                    <div key={m.uid || m.id} className="flex items-center justify-between px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg text-sm">
                      <span className="flex items-center gap-2 text-gray-700 dark:text-gray-200 min-w-0 truncate">
                        <Rows3 className="w-3.5 h-3.5 text-primary-500 flex-shrink-0" />
                        <span className="truncate">{menuLabel(m)}</span>
                        {!m.is_active && <span className="text-[10px] text-orange-500 font-semibold flex-shrink-0">masqué</span>}
                      </span>
                      {m.editable !== false ? (
                        <button
                          onClick={() => detach(m)}
                          disabled={saving}
                          className="text-red-500 hover:text-red-700 disabled:opacity-40 text-xs font-medium flex-shrink-0 ml-2"
                        >
                          Détacher
                        </button>
                      ) : (
                        <span className="text-[10px] text-gray-400 flex-shrink-0 ml-2">catalogue central</span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Créer un nouveau menu */}
            <div className="border-t border-gray-100 dark:border-gray-700 pt-4">
              <label className="block text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
                Créer un nouveau menu pour ce rapport
              </label>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-gray-600 dark:text-gray-300 mb-1">Nom</label>
                  <input value={newMenuNom} onChange={e => setNewMenuNom(e.target.value)} className={inputCls} />
                </div>
                <div>
                  <label className="block text-xs text-gray-600 dark:text-gray-300 mb-1">Code</label>
                  <input
                    value={newMenuCode}
                    onChange={e => setNewMenuCode(normalizeMenuCode(e.target.value))}
                    className={`${inputCls} ${codeTaken ? 'border-red-400 dark:border-red-500' : ''}`}
                  />
                </div>
              </div>
              {codeTaken && (
                <p className="text-xs text-red-500 mt-1">
                  Le code « {newMenuCode} » est déjà utilisé par un autre menu — choisissez-en un autre.
                </p>
              )}

              <div className="mt-3 relative">
                <label className="block text-xs text-gray-600 dark:text-gray-300 mb-1">Emplacement (parent)</label>
                <button
                  type="button"
                  onClick={() => setParentPickerOpen(o => !o)}
                  className={`${inputCls} flex items-center justify-between gap-2 text-left`}
                >
                  <span className="truncate">
                    {(() => {
                      const m = folders.find(x => String(x.id) === String(newMenuParentId))
                      return m ? menuLabel(m) : '-- Racine --'
                    })()}
                  </span>
                  <ChevronRight className={`w-3.5 h-3.5 text-gray-400 flex-shrink-0 transition-transform ${parentPickerOpen ? 'rotate-90' : ''}`} />
                </button>
                {parentPickerOpen && (
                  <>
                    <div className="fixed inset-0 z-40" onClick={() => setParentPickerOpen(false)} />
                    <div className="absolute left-0 right-0 top-full mt-1 z-50 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-xl max-h-64 flex flex-col">
                      <div className="p-2 border-b border-gray-100 dark:border-gray-700 flex-shrink-0">
                        <div className="relative">
                          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
                          <input
                            autoFocus
                            value={parentSearch}
                            onChange={e => setParentSearch(e.target.value)}
                            placeholder="Rechercher un dossier..."
                            className="w-full pl-7 pr-2 py-1.5 text-xs bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded outline-none dark:text-white"
                          />
                        </div>
                      </div>
                      <div className="flex-1 overflow-y-auto py-1">
                        <button
                          type="button"
                          onClick={() => { setNewMenuParentId(''); setParentPickerOpen(false); setParentSearch('') }}
                          className={optionCls(!newMenuParentId)}
                        >
                          -- Racine --
                        </button>
                        {folders
                          .filter(m => matches(m, parentSearch.trim().toLowerCase()))
                          .map(m => (
                            <button
                              key={m.uid || m.id}
                              type="button"
                              onClick={() => { setNewMenuParentId(String(m.id)); setParentPickerOpen(false); setParentSearch('') }}
                              className={optionCls(String(newMenuParentId) === String(m.id))}
                            >
                              {menuLabel(m)}
                            </button>
                          ))}
                        {folders.filter(m => matches(m, parentSearch.trim().toLowerCase())).length === 0 && (
                          <p className="px-3 py-2 text-xs text-gray-400">Aucun dossier</p>
                        )}
                      </div>
                    </div>
                  </>
                )}
              </div>

              <label className="flex items-start gap-2 mt-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={grantAccess}
                  onChange={e => setGrantAccess(e.target.checked)}
                  className="mt-0.5"
                />
                <span className="text-xs text-gray-600 dark:text-gray-300">
                  Donner l'accès à tous les rôles
                  <span className="block text-[11px] text-gray-400">
                    Sinon le menu n'est visible que des administrateurs.
                  </span>
                </span>
              </label>

              <button onClick={createAndAttach} disabled={!canCreate} className="btn-primary mt-3 flex items-center gap-2">
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                Créer et attacher
              </button>
            </div>

            {/* Attacher à un menu existant — section toujours rendue :
                masquée quand la liste était vide, elle donnait l'impression
                que la fonction n'existait pas. */}
            <div className="border-t border-gray-100 dark:border-gray-700 pt-4">
              <label className="block text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
                Ou réattacher un menu existant
              </label>
              {attachableMenus.length === 0 ? (
                <p className="text-sm text-gray-400">
                  Aucun autre menu de type « {typeLabel} » n'est modifiable ici.
                  Créez-en un ci-dessus.
                </p>
              ) : (
                <>
                <div className="flex items-center gap-2">
                  <div className="relative flex-1 min-w-0">
                    <button
                      type="button"
                      onClick={() => setExistingPickerOpen(o => !o)}
                      className={`${inputCls} flex items-center justify-between gap-2 text-left`}
                    >
                      <span className="truncate">
                        {(() => {
                          const m = attachableMenus.find(x => String(x.id) === String(attachExistingId))
                          return m ? menuLabel(m) : `-- Sélectionner un menu ${typeLabel} --`
                        })()}
                      </span>
                      <ChevronRight className={`w-3.5 h-3.5 text-gray-400 flex-shrink-0 transition-transform ${existingPickerOpen ? 'rotate-90' : ''}`} />
                    </button>
                    {existingPickerOpen && (
                      <>
                        <div className="fixed inset-0 z-40" onClick={() => setExistingPickerOpen(false)} />
                        <div className="absolute left-0 right-0 top-full mt-1 z-50 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-xl max-h-64 flex flex-col">
                          <div className="p-2 border-b border-gray-100 dark:border-gray-700 flex-shrink-0">
                            <div className="relative">
                              <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
                              <input
                                autoFocus
                                value={existingSearch}
                                onChange={e => setExistingSearch(e.target.value)}
                                placeholder="Rechercher un menu..."
                                className="w-full pl-7 pr-2 py-1.5 text-xs bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded outline-none dark:text-white"
                              />
                            </div>
                          </div>
                          <div className="flex-1 overflow-y-auto py-1">
                            {attachableMenus
                              .filter(m => matches(m, existingSearch.trim().toLowerCase()))
                              .map(m => (
                                <button
                                  key={m.uid || m.id}
                                  type="button"
                                  onClick={() => { setAttachExistingId(String(m.id)); setExistingPickerOpen(false); setExistingSearch('') }}
                                  className={optionCls(String(attachExistingId) === String(m.id))}
                                >
                                  {menuLabel(m)}
                                </button>
                              ))}
                            {attachableMenus.filter(m => matches(m, existingSearch.trim().toLowerCase())).length === 0 && (
                              <p className="px-3 py-2 text-xs text-gray-400">Aucun résultat</p>
                            )}
                          </div>
                        </div>
                      </>
                    )}
                  </div>
                  <button
                    onClick={attachToExisting}
                    disabled={saving || !attachExistingId}
                    className="btn-primary whitespace-nowrap flex-shrink-0"
                  >
                    Attacher
                  </button>
                </div>
                <p className="text-xs text-gray-400 mt-1.5">
                  Le menu sélectionné pointera désormais vers ce rapport à la place du sien.
                  {' '}({attachableMenus.length} menu{attachableMenus.length > 1 ? 'x' : ''} disponible{attachableMenus.length > 1 ? 's' : ''})
                </p>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
