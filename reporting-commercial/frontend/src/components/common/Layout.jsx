import { Link, useLocation, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard,
  ShoppingCart,
  Package,
  CreditCard,
  Sun,
  Moon,
  Menu,
  X,
  Building2,
  RefreshCw,
  Users,
  Settings,
  Cog,
  ChevronDown,
  ChevronRight,
  ChevronLeft,
  LogOut,
  User,
  LayoutGrid,
  PanelTop,
  Table2,
  Table,
  Folder,
  FileSpreadsheet,
  Link as LinkIcon,
  BarChart3,
  Wallet,
  PanelLeftClose,
  PanelLeftOpen,
  Palette,
  Mail,
  Calendar,
  Database,
  ArrowRightLeft,
  // === Icones metier ===
  FileText,
  Truck,
  ClipboardList,
  FileQuestion,
  RotateCcw,
  PackageCheck,
  Receipt,
  TrendingUp,
  TrendingDown,
  PieChart,
  Target,
  MapPin,
  Layers,
  Activity,
  DollarSign,
  Percent,
  ShoppingBag,
  BarChart2,
  LineChart,
  Award,
  AlertTriangle,
  Clock,
  Repeat,
  GitCompare,
  UserCheck,
  UserX,
  Gauge,
  Crosshair,
  Star,
  Zap,
  Filter,
  ArrowUpDown,
  CircleDollarSign,
  BadgePercent,
  Scale,
  FolderOpen,
  Boxes,
  Shield,
  Globe,
  Brain,
  MessageSquare,
  SlidersHorizontal,
  Bell,
  GitBranch,
  ShieldCheck,
  Sparkles,
} from 'lucide-react'
import { useState, useEffect, useRef, useCallback } from 'react'
import { getUserMenus } from '../../services/api'
import { useSettings } from '../../context/SettingsContext'
import { useDataSource } from '../../context/DataSourceContext'
import ChatWidget from '../ai/ChatWidget'
import AlertBell from './AlertBell'
import Watermark from './Watermark'

// Navigation statique supprimée - utilise les menus dynamiques maintenant

// Structure du menu admin avec sous-groupes
// ─── Règle de visibilité ────────────────────────────────────────────────────
// superadminOnly: true  → visible uniquement en base maître (superadmin)
// (rien)               → visible pour tous les admins (superadmin + admin_client)
// ────────────────────────────────────────────────────────────────────────────
// ─── Règles de visibilité ────────────────────────────────────────────────────
// superadminOnly : true  → base maître uniquement (role_global = superadmin)
// adminOnly      : true  → superadmin + admin_client (pas les utilisateurs simples)
// (rien)                 → tous les utilisateurs ayant accès à la page
// ────────────────────────────────────────────────────────────────────────────
const adminNavigation = [
  // ── Navigation ───────────────────────────────────────────────────────────
  {
    name: 'Navigation',
    icon: Layers,
    pageCode: 'admin',
    isFolder: true,
    children: [
      { name: 'Gestion Menus',  href: '/admin/menus',        icon: Settings, pageCode: 'admin' },
      { name: 'Menus Maitre',   href: '/admin/master-menus', icon: Globe,    pageCode: 'admin', superadminOnly: true },
    ]
  },
  // ── Données & ETL ─────────────────────────────────────────────────────────
  {
    name: 'Données & ETL',
    icon: Database,
    pageCode: 'admin',
    isFolder: true,
    children: [
      { name: 'Base de Données', href: '/admin/database', icon: Database,       pageCode: 'admin', superadminOnly: true },
      { name: 'ETL Admin',       href: '/admin/etl',      icon: ArrowRightLeft, pageCode: 'etl_admin' },
      { name: 'Accès Direct Sage', href: '/sage-direct', icon: Database,       pageCode: 'etl_admin', subtitle: 'Live · Sans sync' },
    ]
  },
  // ── Reporting & Alertes ───────────────────────────────────────────────────
  {
    name: 'Reporting',
    icon: BarChart3,
    pageCode: 'admin',
    isFolder: true,
    children: [
      { name: 'Alertes KPI',    href: '/admin/alerts',           icon: Bell,      pageCode: 'admin' },
      { name: 'Abonnements',    href: '/admin/subscriptions',    icon: Activity,  pageCode: 'admin', subtitle: 'Self-service' },
      { name: 'Envois Planifiés', href: '/admin/report-scheduler', icon: Mail,   pageCode: 'report_scheduler', subtitle: 'Push → destinataires' },
      { name: 'Digest IA',      href: '/admin/digest',           icon: Brain,     pageCode: 'admin', subtitle: 'Résumé hebdo direction' },
      { name: 'Drill-through',  href: '/admin/drillthrough',     icon: GitBranch, pageCode: 'admin' },
    ]
  },
  // ── IA Learning ───────────────────────────────────────────────────────────
  {
    name: 'IA Learning',
    icon: Brain,
    pageCode: 'admin',
    superadminOnly: true,
    isFolder: true,
    children: [
      { name: 'Query Library', href: '/admin/ai-library', icon: Brain, pageCode: 'admin', superadminOnly: true },
      { name: 'Gestion Prompts', href: '/admin/ai-prompts', icon: MessageSquare, pageCode: 'admin', superadminOnly: true },
    ]
  },
  {
    name: 'Builders',
    icon: LayoutGrid,
    pageCode: 'admin',
    isFolder: true,
    children: [
      { name: 'Dashboard Builder', href: '/builder', icon: LayoutGrid, pageCode: 'admin' },
      { name: 'Pivot Builder', href: '/pivot-builder-v2', icon: Table2, pageCode: 'admin' },
      { name: 'GridView Builder', href: '/gridview-builder', icon: Table, pageCode: 'admin' },
      { name: 'DataSource Templates', href: '/admin/datasources', icon: Database, pageCode: 'admin' },
      { name: 'Créateur IA', href: '/ai-presentation', icon: Sparkles, pageCode: 'dashboard', subtitle: 'PPTX & Excel par IA' },
      { name: 'Deck IA', href: '/ai-deck', icon: Sparkles, pageCode: 'dashboard', subtitle: 'Présentation interactive' },
    ]
  },
  {
    name: 'Configuration',
    icon: Cog,
    pageCode: 'dashboard',
    isFolder: true,
    children: [
      { name: 'Parametres', href: '/settings', icon: Cog, pageCode: 'admin' },
      { name: 'Themes', href: '/themes', icon: Palette, pageCode: 'dashboard' },
      { name: 'Config Serveur (.env)', href: '/admin/env', icon: SlidersHorizontal, pageCode: 'admin', superadminOnly: true },
    ]
  },
  {
    name: 'Gestion Utilisateurs',
    icon: Users,
    pageCode: 'users',
    isFolder: true,
    children: [
      { name: 'Utilisateurs',        href: '/admin/users',       icon: Users,      pageCode: 'users',      superadminOnly: true },
      { name: 'Utilisateurs Client', href: '/admin/client-users',icon: UserCheck,  pageCode: 'client_users' },
      { name: 'Rôles & Permissions', href: '/admin/roles',       icon: Shield,     pageCode: 'admin' },
      { name: 'Mon DWH',             href: '/admin/client-dwh',  icon: Database,   pageCode: 'client_dwh' },
      { name: 'Gestion DWH',         href: '/admin/dwh',         icon: Building2,  pageCode: 'admin',      superadminOnly: true },
    ]
  },
]

// Map des icones (metier + generiques)
const iconMap = {
  // Generiques
  Folder, FolderOpen, Table2, LayoutDashboard, FileSpreadsheet, LinkIcon,
  ShoppingCart, BarChart3, Wallet, Package, Users, LayoutGrid,
  Table, PanelTop, Settings, Database, Calendar, Mail,
  // Documents
  FileText, Receipt, ClipboardList, FileQuestion, PackageCheck,
  // Logistique
  Truck, Boxes,
  // Mouvements
  RotateCcw, Repeat, ArrowUpDown, ArrowRightLeft,
  // Analyses
  TrendingUp, TrendingDown, PieChart, BarChart2, LineChart, Activity,
  // Finance
  DollarSign, CircleDollarSign, CreditCard, BadgePercent, Percent, Scale,
  // Commercial
  Target, Crosshair, ShoppingBag, Star, Award,
  // Clients
  UserCheck, UserX, User,
  // Geographie
  MapPin, Layers,
  // Alertes
  AlertTriangle, Zap,
  // Temps
  Clock,
  // Comparaison
  GitCompare, Filter, Gauge,
}

const getIconComponent = (iconName) => {
  return iconMap[iconName] || Folder
}

// Composant pour le menu contextuel flottant (mode collapsed)
function CollapsedMenuPopover({ menu, isOpen, onClose, onNavigate, buttonRef }) {
  const popoverRef = useRef(null)
  const hasChildren = menu.children && menu.children.length > 0

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (popoverRef.current && !popoverRef.current.contains(event.target) &&
          buttonRef.current && !buttonRef.current.contains(event.target)) {
        onClose()
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isOpen, onClose, buttonRef])

  if (!isOpen) return null

  // Calculer la position du popover
  const buttonRect = buttonRef.current?.getBoundingClientRect()
  const top = buttonRect ? buttonRect.top : 0

  return (
    <div
      ref={popoverRef}
      className="fixed z-50 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg min-w-[200px] max-w-[280px] py-2"
      style={{ left: '80px', top: Math.max(top, 10) }}
    >
      {/* Titre du menu */}
      <div className="px-3 py-2 border-b border-gray-200 dark:border-gray-700">
        <span className="font-semibold text-gray-900 dark:text-white text-sm">{menu.nom}</span>
      </div>

      {/* Sous-menus */}
      {hasChildren ? (
        <div className="py-1 max-h-[400px] overflow-y-auto">
          {menu.children.map((child) => (
            <CollapsedMenuPopoverItem
              key={child.id}
              menu={child}
              depth={0}
              onNavigate={onNavigate}
              onClose={onClose}
            />
          ))}
        </div>
      ) : (
        <div className="px-3 py-2 text-gray-500 dark:text-gray-400 text-sm">
          Aucun sous-menu
        </div>
      )}
    </div>
  )
}

// Item recursif pour le popover
function CollapsedMenuPopoverItem({ menu, depth, onNavigate, onClose }) {
  const [isExpanded, setIsExpanded] = useState(false)
  const hasChildren = menu.children && menu.children.length > 0
  const IconComp = getIconComponent(menu.icon)
  const isFolder = menu.type === 'folder' || hasChildren

  const handleClick = () => {
    if (isFolder) {
      setIsExpanded(!isExpanded)
    } else {
      onNavigate(menu)
      onClose()
    }
  }

  return (
    <div>
      <button
        onClick={handleClick}
        className={`
          w-full flex items-center gap-2 px-3 py-2 text-sm
          text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700
          transition-colors
        `}
        style={{ paddingLeft: `${12 + depth * 12}px` }}
      >
        <IconComp className="w-4 h-4 flex-shrink-0" style={{ color: 'var(--color-primary-500)' }} />
        <span className="truncate flex-1 text-left">{menu.nom}</span>
        {hasChildren && (
          isExpanded
            ? <ChevronDown className="w-3 h-3 flex-shrink-0" style={{ color: 'var(--color-primary-400)' }} />
            : <ChevronRight className="w-3 h-3 flex-shrink-0" style={{ color: 'var(--color-primary-400)' }} />
        )}
      </button>

      {hasChildren && isExpanded && (
        <div>
          {menu.children.map((child) => (
            <CollapsedMenuPopoverItem
              key={child.id}
              menu={child}
              depth={depth + 1}
              onNavigate={onNavigate}
              onClose={onClose}
            />
          ))}
        </div>
      )}
    </div>
  )
}

// Composant pour un bouton de menu collapsed avec popover
function CollapsedMenuButton({ menu, navigateToMenu }) {
  const [isPopoverOpen, setIsPopoverOpen] = useState(false)
  const buttonRef = useRef(null)
  const IconComp = getIconComponent(menu.icon)
  const hasChildren = menu.children && menu.children.length > 0

  const handleClick = () => {
    if (hasChildren || menu.type === 'folder') {
      setIsPopoverOpen(!isPopoverOpen)
    } else {
      navigateToMenu(menu)
    }
  }

  return (
    <>
      <button
        ref={buttonRef}
        onClick={handleClick}
        className={`
          flex items-center justify-center w-full px-3 py-2.5 rounded-lg
          text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700/50
          transition-colors
          ${isPopoverOpen ? 'bg-gray-100 dark:bg-gray-700/50' : ''}
        `}
        title={menu.nom}
      >
        <IconComp className="w-6 h-6" style={{ color: 'var(--color-primary-500)' }} />
      </button>
      <CollapsedMenuPopover
        menu={menu}
        isOpen={isPopoverOpen}
        onClose={() => setIsPopoverOpen(false)}
        onNavigate={navigateToMenu}
        buttonRef={buttonRef}
      />
    </>
  )
}

// Composant recursif pour afficher les menus dynamiques
function DynamicMenuItem({ menu, depth, openMenuIds, toggleMenuOpen, navigateToMenu, location }) {
  const hasChildren = menu.children && menu.children.length > 0
  const isOpen = openMenuIds[menu.id]
  const IconComp = getIconComponent(menu.icon)
  const isInactive = menu.is_active === false || menu.is_active === 0

  // Determiner si cet element est actif (page courante)
  const isActive = (
    ((menu.type === 'pivot' || menu.type === 'pivot-v2') && location.pathname === `/pivot-v2/${menu.target_id}`) ||
    (menu.type === 'gridview' && location.pathname === `/grid/${menu.target_id}`) ||
    (menu.type === 'dashboard' && location.pathname === `/view/${menu.target_id}`) ||
    (menu.type === 'page' && location.pathname === menu.url)
  )

  const isFolder = menu.type === 'folder' || hasChildren
  const isRootLevel = depth === 0

  return (
    <div>
      <button
        onClick={() => isFolder ? toggleMenuOpen(menu.id) : navigateToMenu(menu)}
        className={`
          w-full flex items-center gap-3 rounded-lg text-sm
          transition-colors duration-200
          ${isRootLevel ? 'px-3 py-2.5' : 'px-3 py-2'}
          ${isInactive ? 'opacity-50' : ''}
          ${isActive
            ? 'menu-item-active'
            : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700/50'
          }
        `}
        style={{
          paddingLeft: isRootLevel ? '12px' : `${12 + depth * 16}px`,
          ...(isActive ? { backgroundColor: 'var(--color-primary-100)', color: 'var(--color-primary-700)' } : {})
        }}
        title={isInactive ? `${menu.nom} (inactif)` : menu.nom}
      >
        <IconComp className={`${isRootLevel ? 'w-5 h-5' : 'w-4 h-4'} flex-shrink-0`} style={{ color: isActive ? 'var(--color-primary-700)' : 'var(--color-primary-500)' }} />
        <span className="truncate font-medium flex-1 text-left">{menu.nom}</span>
        {hasChildren && (
          isOpen
            ? <ChevronDown className="w-4 h-4 flex-shrink-0" style={{ color: isActive ? 'var(--color-primary-700)' : 'var(--color-primary-400)' }} />
            : <ChevronRight className="w-4 h-4 flex-shrink-0" style={{ color: isActive ? 'var(--color-primary-700)' : 'var(--color-primary-400)' }} />
        )}
      </button>

      {hasChildren && isOpen && (
        <div className="mt-1 space-y-1">
          {menu.children.map(child => (
            <DynamicMenuItem
              key={child.id}
              menu={child}
              depth={depth + 1}
              openMenuIds={openMenuIds}
              toggleMenuOpen={toggleMenuOpen}
              navigateToMenu={navigateToMenu}
              location={location}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export default function Layout({ children, darkMode, setDarkMode, onRefresh, refreshing, user, onLogout, appName }) {
  const location = useLocation()
  const navigate = useNavigate()
  const { settings } = useSettings()
  const { dataSource, toggleDataSource, isSageDirect } = useDataSource()
  // Lire le DWH courant depuis localStorage (pas de DWHProvider dans l'arbre)
  const [currentDWH, setCurrentDWH] = useState(() => {
    try { return JSON.parse(localStorage.getItem('currentDWH')) } catch { return null }
  })
  useEffect(() => {
    const handleStorage = () => {
      try { setCurrentDWH(JSON.parse(localStorage.getItem('currentDWH'))) } catch { setCurrentDWH(null) }
    }
    window.addEventListener('storage', handleStorage)
    return () => window.removeEventListener('storage', handleStorage)
  }, [])
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [adminOpen, setAdminOpen] = useState(location.pathname.startsWith('/admin/'))
  const [adminSubMenus, setAdminSubMenus] = useState({})
  const [userMenuOpen, setUserMenuOpen] = useState(false)

  // Menu dynamique
  const [dynamicMenus, setDynamicMenus] = useState([])
  const [openMenuIds, setOpenMenuIds] = useState({})
  const [menusLoading, setMenusLoading] = useState(false)

  // Charger les menus dynamiques selon les droits utilisateur
  const loadUserMenus = useCallback(async () => {
    if (!user) return
    setMenusLoading(true)
    try {
      const response = await getUserMenus(user.id, currentDWH?.code || null)
      const menus = response.data?.data || response.data || []
      setDynamicMenus(Array.isArray(menus) ? menus : [])
    } catch (error) {
      console.error('Erreur chargement menus:', error)
      // Session obsolète (utilisateur supprimé) → forcer reconnexion
      if (error.response?.status === 404) {
        window.dispatchEvent(new CustomEvent('auth:session-expired'))
      }
      setDynamicMenus([])
    } finally {
      setMenusLoading(false)
    }
  }, [user, currentDWH?.code]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    loadUserMenus()
  }, [user, currentDWH?.code]) // eslint-disable-line react-hooks/exhaustive-deps

  // Toggle menu ouvert/ferme
  const toggleMenuOpen = (menuId) => {
    setOpenMenuIds(prev => ({ ...prev, [menuId]: !prev[menuId] }))
  }

  // Navigation vers un element de menu
  const navigateToMenu = (menu) => {
    setSidebarOpen(false)
    if ((menu.type === 'pivot' || menu.type === 'pivot-v2') && menu.target_id) {
      navigate(`/pivot-v2/${menu.target_id}`)
    } else if (menu.type === 'gridview' && menu.target_id) {
      navigate(`/grid/${menu.target_id}`)
    } else if (menu.type === 'dashboard' && menu.target_id) {
      navigate(`/view/${menu.target_id}`)
    } else if (menu.type === 'page' && menu.url) {
      navigate(menu.url)
    }
  }

  // ── Détection du rôle réel ───────────────────────────────────────────────
  // Nouveau format : user.role_global = 'superadmin', user.from_client_db = false
  // Ancien format  : user.role = 'admin' (legacy localStorage)
  const isSuperAdmin = (
    user?.role_global === 'superadmin' ||
    user?.role === 'superadmin' ||
    (user?.from_client_db === false && !user?.role_dwh) ||
    (user?.role === 'admin' && !currentDWH && !user?.from_client_db)
  )
  const isAdminClient = !isSuperAdmin && (
    user?.role_global === 'admin_client' ||
    user?.role_dwh === 'admin_client' ||
    user?.role === 'admin_client'
  )

  // Si superadmin détecté mais currentDWH en mémoire → le vider silencieusement
  if (isSuperAdmin && currentDWH) {
    localStorage.removeItem('currentDWH')
    sessionStorage.removeItem('currentDWH')
  }

  // Fonction pour verifier l'acces a une page
  const hasAccess = (pageCode) => {
    if (!user) return false
    if (isSuperAdmin || isAdminClient || user.role === 'admin') return true
    return user.pages_autorisees?.includes(pageCode)
  }

  // Filtrer la navigation admin selon les droits
  // Les items superadminOnly ne s'affichent qu'en base maître (superadmin)
  const filteredAdminNavigation = adminNavigation
    .filter(item => {
      if (item.superadminOnly && !isSuperAdmin) return false
      if (item.isFolder && item.children) {
        // Le dossier est visible si au moins un enfant autorisé est accessible
        const visibleChildren = item.children.filter(child =>
          !(child.superadminOnly && !isSuperAdmin) && hasAccess(child.pageCode)
        )
        return visibleChildren.length > 0
      }
      return hasAccess(item.pageCode)
    })
    .map(item => {
      // Filtrer les enfants superadminOnly dans les dossiers
      if (item.isFolder && item.children) {
        return {
          ...item,
          children: item.children.filter(child =>
            !(child.superadminOnly && !isSuperAdmin) && hasAccess(child.pageCode)
          )
        }
      }
      return item
    })
  const showAdminSection = filteredAdminNavigation.length > 0

  return (
    <div className="h-screen flex overflow-hidden" style={{ minHeight: 0 }}>
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed lg:static inset-y-0 left-0 z-50
          ${sidebarCollapsed ? 'w-20' : 'w-80'} bg-white dark:bg-gray-800 border-r border-primary-300 dark:border-gray-700
          transform transition-all duration-200 ease-in-out
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        `}
      >
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div
            className={`flex items-center ${sidebarCollapsed ? 'justify-center' : 'gap-3'} px-4 py-4 border-b border-gray-200 dark:border-gray-700 cursor-pointer`}
            style={{ backgroundColor: 'var(--sidebar-bg)' }}
            onClick={() => navigate('/')}
            title="Accueil"
          >
            <div className="w-8 h-8 flex-shrink-0 flex items-center justify-center rounded-md bg-white/20">
              <span className="text-white font-extrabold text-lg leading-none">K</span>
            </div>
            {!sidebarCollapsed && (
              <div className="min-w-0">
                <h1 className="text-white font-bold text-base truncate">{appName ? appName.split(' - ')[0] : 'OptiBoard'}</h1>
                <p className="text-white/70 dark:text-gray-400 text-sm">{appName && appName.includes(' - ') ? appName.split(' - ').slice(1).join(' - ') : 'Reporting'}</p>
                {currentDWH?.nom && (
                  <p className="text-white/90 font-semibold text-xs mt-1 truncate bg-white/10 rounded px-2 py-0.5">
                    {currentDWH.nom}
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Navigation */}
          <nav className={`flex-1 ${sidebarCollapsed ? 'px-2' : 'px-3'} py-3 space-y-1 overflow-y-auto text-sm`}>
            {/* Menu Dynamique en premier */}
            {dynamicMenus.length > 0 && (
              sidebarCollapsed ? (
                // Mode collapsed - afficher uniquement les icones avec popover au clic
                <div className="space-y-1">
                  {dynamicMenus.map((menu) => (
                    <CollapsedMenuButton
                      key={menu.id}
                      menu={menu}
                      navigateToMenu={navigateToMenu}
                    />
                  ))}
                </div>
              ) : (
                // Mode expanded - afficher l'arborescence complete
                <div className="space-y-1">
                  {dynamicMenus.map((menu) => (
                    <DynamicMenuItem
                      key={menu.id}
                      menu={menu}
                      depth={0}
                      openMenuIds={openMenuIds}
                      toggleMenuOpen={toggleMenuOpen}
                      navigateToMenu={navigateToMenu}
                      location={location}
                    />
                  ))}
                </div>
              )
            )}

            {/* Message si pas de menus */}
            {dynamicMenus.length === 0 && !sidebarCollapsed && (
              <div className="text-center py-4 text-gray-400 dark:text-gray-600 text-xs">
                {menusLoading ? (
                  <span className="italic">Chargement...</span>
                ) : (
                  <button
                    onClick={loadUserMenus}
                    className="flex items-center gap-1 mx-auto text-gray-400 hover:text-blue-500 transition-colors"
                    title="Recharger les menus"
                  >
                    <RefreshCw className="w-3 h-3" />
                    <span>Actualiser les menus</span>
                  </button>
                )}
              </div>
            )}

            {/* Admin Section — masqué pour les utilisateurs demo */}
            {showAdminSection && !user?.dwh_code?.startsWith('DEMO_') && (
              <div className="pt-3 mt-3 border-t border-gray-200 dark:border-gray-700">
                {sidebarCollapsed ? (
                  <Link
                    to="/admin/menus"
                    className={`flex items-center justify-center px-3 py-2.5 rounded-lg text-sm transition-colors duration-200
                      ${location.pathname.startsWith('/admin') || location.pathname.startsWith('/builder') || location.pathname.startsWith('/pivot-builder') || location.pathname.startsWith('/gridview-builder') || location.pathname === '/settings' || location.pathname === '/themes'
                        ? 'menu-item-active'
                        : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700/50'
                      }`}
                    style={(location.pathname.startsWith('/admin') || location.pathname.startsWith('/builder') || location.pathname.startsWith('/pivot-builder') || location.pathname.startsWith('/gridview-builder') || location.pathname === '/settings' || location.pathname === '/themes') ? { backgroundColor: 'var(--color-primary-100)', color: 'var(--color-primary-700)' } : {}}
                    title="Admin"
                  >
                    <Settings className="w-6 h-6" style={{ color: (location.pathname.startsWith('/admin') || location.pathname.startsWith('/builder') || location.pathname.startsWith('/pivot-builder') || location.pathname.startsWith('/gridview-builder') || location.pathname === '/settings' || location.pathname === '/themes') ? 'var(--color-primary-700)' : 'var(--color-primary-500)' }} />
                  </Link>
                ) : (
                  <>
                    <button
                      onClick={() => setAdminOpen(!adminOpen)}
                      className="w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700/50"
                    >
                      <div className="flex items-center gap-3">
                        <Settings className="w-5 h-5" style={{ color: 'var(--color-primary-500)' }} />
                        <span className="font-medium">Admin</span>
                      </div>
                      <ChevronDown className={`w-4 h-4 transition-transform ${adminOpen ? 'rotate-180' : ''}`} style={{ color: 'var(--color-primary-400)' }} />
                    </button>

                    {adminOpen && (
                      <div className="ml-4 mt-1 space-y-1">
                        {filteredAdminNavigation.map((item) => {
                          // Si c'est un dossier avec des enfants
                          if (item.isFolder && item.children) {
                            const isSubMenuOpen = adminSubMenus[item.name]
                            const hasActiveChild = item.children.some(child => location.pathname === child.href)
                            return (
                              <div key={item.name}>
                                <button
                                  onClick={() => setAdminSubMenus(prev => ({ ...prev, [item.name]: !prev[item.name] }))}
                                  className={`
                                    w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm
                                    transition-colors duration-200
                                    ${hasActiveChild
                                      ? 'text-primary-600 dark:text-primary-400'
                                      : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700/50'
                                    }
                                  `}
                                >
                                  <div className="flex items-center gap-3">
                                    <item.icon className="w-4 h-4" style={{ color: hasActiveChild ? 'var(--color-primary-600)' : 'var(--color-primary-500)' }} />
                                    <span className="font-medium">{item.name}</span>
                                  </div>
                                  <ChevronDown className={`w-3 h-3 transition-transform ${isSubMenuOpen ? 'rotate-180' : ''}`} style={{ color: 'var(--color-primary-400)' }} />
                                </button>
                                {isSubMenuOpen && (
                                  <div className="ml-4 mt-1 space-y-1">
                                    {item.children.filter(child => hasAccess(child.pageCode)).map((child) => {
                                      const isActive = location.pathname === child.href
                                      return (
                                        <Link
                                          key={child.name}
                                          to={child.href}
                                          onClick={() => setSidebarOpen(false)}
                                          className={`
                                            flex items-center gap-3 px-3 py-1.5 rounded-lg text-sm
                                            transition-colors duration-200
                                            ${isActive
                                              ? 'menu-item-active'
                                              : 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700/50'
                                            }
                                          `}
                                          style={isActive ? { backgroundColor: 'var(--color-primary-100)', color: 'var(--color-primary-700)' } : {}}
                                        >
                                          <child.icon className="w-3.5 h-3.5" style={{ color: isActive ? 'var(--color-primary-700)' : 'var(--color-primary-500)' }} />
                                          <span>{child.name}</span>
                                        </Link>
                                      )
                                    })}
                                  </div>
                                )}
                              </div>
                            )
                          }

                          // Sinon c'est un lien direct
                          const isActive = location.pathname === item.href
                          return (
                            <Link
                              key={item.name}
                              to={item.href}
                              onClick={() => setSidebarOpen(false)}
                              className={`
                                flex items-center gap-3 px-3 py-2 rounded-lg text-sm
                                transition-colors duration-200
                                ${isActive
                                  ? 'menu-item-active'
                                  : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700/50'
                                }
                              `}
                              style={isActive ? { backgroundColor: 'var(--color-primary-100)', color: 'var(--color-primary-700)' } : {}}
                            >
                              <item.icon className="w-4 h-4 shrink-0" style={{ color: isActive ? 'var(--color-primary-700)' : 'var(--color-primary-500)' }} />
                              <span className="flex flex-col min-w-0">
                                <span>{item.name}</span>
                                {item.subtitle && (
                                  <span className="text-[10px] text-gray-400 dark:text-gray-500 leading-none mt-0.5">{item.subtitle}</span>
                                )}
                              </span>
                            </Link>
                          )
                        })}
                      </div>
                    )}
                  </>
                )}
              </div>
            )}
          </nav>

          {/* User info */}
          {user && (
            <div className={`${sidebarCollapsed ? 'px-2' : 'px-3'} py-3 border-t border-gray-200 dark:border-gray-700`}>
              <div className={`flex items-center ${sidebarCollapsed ? 'justify-center' : 'gap-3 px-3'} py-2 rounded-lg bg-gray-50 dark:bg-gray-700/50`} title={sidebarCollapsed ? `${user.nom} ${user.prenom}` : ''}>
                <div
                  className={`${sidebarCollapsed ? 'w-10 h-10' : 'w-9 h-9'} rounded-full flex items-center justify-center`}
                  style={{ backgroundColor: 'var(--color-primary-100)' }}
                >
                  <User className={`${sidebarCollapsed ? 'w-5 h-5' : 'w-5 h-5'}`} style={{ color: 'var(--color-primary-600)' }} />
                </div>
                {!sidebarCollapsed && (
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                      {user.nom} {user.prenom}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                      {isSuperAdmin ? 'Super Administrateur' : isAdminClient ? 'Admin Client' : user.role === 'readonly' ? 'Lecture seule' : 'Utilisateur'}
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Toggle collapse button + Footer */}
          <div className={`${sidebarCollapsed ? 'px-2' : 'px-3'} py-3 border-t border-gray-200 dark:border-gray-700 flex ${sidebarCollapsed ? 'justify-center' : 'justify-between'} items-center`}>
            {!sidebarCollapsed && (
              <p className="text-gray-500 dark:text-gray-400 text-xs">
                © 2026 KAsoft
              </p>
            )}
            <button
              onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
              className="hidden lg:flex p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors text-gray-500 dark:text-gray-400"
              title={sidebarCollapsed ? 'Developper le menu' : 'Reduire le menu'}
            >
              {sidebarCollapsed ? (
                <PanelLeftOpen className="w-5 h-5" style={{ color: 'var(--color-primary-500)' }} />
              ) : (
                <PanelLeftClose className="w-5 h-5" style={{ color: 'var(--color-primary-500)' }} />
              )}
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0 min-h-0">
        {/* Header */}
        <header className="flex-shrink-0 sticky top-0 z-30 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between px-3 lg:px-4 py-2">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700"
            >
              <Menu className="w-5 h-5" style={{ color: 'var(--color-primary-500)' }} />
            </button>

            <div className="flex-1 lg:flex-none">
              <h2 className="text-sm font-semibold text-gray-900 dark:text-white lg:hidden text-center">
                Reporting Commercial
              </h2>
            </div>

            <div className="flex items-center gap-1">
              {/* Toggle DWH / Sage Direct */}
              <button
                onClick={toggleDataSource}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-all duration-200 border ${
                  isSageDirect
                    ? 'bg-orange-100 dark:bg-orange-900/40 text-orange-700 dark:text-orange-300 border-orange-300 dark:border-orange-700'
                    : 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 border-blue-200 dark:border-blue-800'
                }`}
                title={isSageDirect ? 'Mode Sage Direct (live) — cliquer pour DWH' : 'Mode DWH (synchronisé) — cliquer pour Sage Direct'}
              >
                <Database className="w-3.5 h-3.5" />
                <span>{isSageDirect ? 'Sage Live' : 'DWH'}</span>
                <span className={`w-1.5 h-1.5 rounded-full ${isSageDirect ? 'bg-orange-500 animate-pulse' : 'bg-blue-500'}`} />
              </button>

              {/* Cloche alertes KPI */}
              <AlertBell />

              {/* Refresh button */}
              {onRefresh && (
                <button
                  onClick={onRefresh}
                  disabled={refreshing}
                  className="p-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors disabled:opacity-50"
                  title="Actualiser les donnees"
                >
                  <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} style={{ color: 'var(--color-primary-500)' }} />
                </button>
              )}

              {/* Theme toggle */}
              <button
                onClick={() => setDarkMode(!darkMode)}
                className="p-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                title={darkMode ? 'Mode clair' : 'Mode sombre'}
              >
                {darkMode ? (
                  <Sun className="w-4 h-4 text-yellow-500" />
                ) : (
                  <Moon className="w-4 h-4" style={{ color: 'var(--color-primary-500)' }} />
                )}
              </button>

              {/* User menu */}
              {user && (
                <div className="relative">
                  <button
                    onClick={() => setUserMenuOpen(!userMenuOpen)}
                    className="flex items-center gap-2 p-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                  >
                    <div
                      className="w-6 h-6 rounded-full flex items-center justify-center"
                      style={{ backgroundColor: 'var(--color-primary-100)' }}
                    >
                      <User className="w-3 h-3" style={{ color: 'var(--color-primary-600)' }} />
                    </div>
                    <span className="hidden lg:block text-sm text-gray-700 dark:text-gray-300">
                      {user.prenom}
                    </span>
                    <ChevronDown className="w-3 h-3" style={{ color: 'var(--color-primary-400)' }} />
                  </button>

                  {userMenuOpen && (
                    <>
                      <div
                        className="fixed inset-0 z-40"
                        onClick={() => setUserMenuOpen(false)}
                      />
                      <div className="absolute right-0 mt-1 w-48 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-50">
                        <div className="p-3 border-b border-gray-200 dark:border-gray-700">
                          <p className="text-sm font-medium text-gray-900 dark:text-white">
                            {user.nom} {user.prenom}
                          </p>
                          <p className="text-xs text-gray-500">{user.username}</p>
                          <p className="text-xs mt-1" style={{ color: 'var(--color-primary-600)' }}>
                            {isSuperAdmin ? 'Super Administrateur' : isAdminClient ? 'Admin Client' : user.role === 'readonly' ? 'Lecture seule' : 'Utilisateur'}
                          </p>
                        </div>
                        <div className="p-1">
                          <Link
                            to="/mes-abonnements"
                            onClick={() => setUserMenuOpen(false)}
                            className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
                          >
                            <Bell className="w-4 h-4" style={{ color: 'var(--color-primary-500)' }} />
                            Mes Abonnements
                          </Link>
                          {(isSuperAdmin || isAdminClient) && (
                            <Link
                              to="/setup-2fa"
                              onClick={() => setUserMenuOpen(false)}
                              className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
                            >
                              <ShieldCheck className="w-4 h-4 text-indigo-500" />
                              Sécurité (2FA)
                            </Link>
                          )}
                          <div className="my-1 border-t border-gray-100 dark:border-gray-700" />
                          <button
                            onClick={() => {
                              setUserMenuOpen(false)
                              onLogout()
                            }}
                            className="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-md transition-colors"
                          >
                            <LogOut className="w-4 h-4" />
                            Deconnexion
                          </button>
                        </div>
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 flex flex-col min-h-0 p-3 lg:p-4 overflow-auto">
          {children}
        </main>
      </div>

      {/* AI Chat Widget (floating) */}
      <ChatWidget />

      {/* Filigrane dynamique utilisateur (canvas tuilé, anti-copie/impression) */}
      {(settings?.watermarkEnabled ?? true) && <Watermark user={user} darkMode={darkMode} />}
    </div>
  )
}
