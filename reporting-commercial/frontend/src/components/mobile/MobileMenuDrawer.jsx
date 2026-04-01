import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { X, ChevronDown, ChevronRight, Folder } from 'lucide-react'
import {
  Folder as FolderIcon, FolderOpen, Table2, LayoutDashboard, FileSpreadsheet,
  ShoppingCart, BarChart3, Wallet, Package, Users, LayoutGrid,
  Table, PanelTop, Settings, Database, Mail,
  FileText, Receipt, ClipboardList, FileQuestion, PackageCheck,
  Truck, Boxes, RotateCcw, Repeat, ArrowUpDown, ArrowRightLeft,
  TrendingUp, TrendingDown, PieChart, BarChart2, LineChart, Activity,
  DollarSign, CircleDollarSign, CreditCard, BadgePercent, Percent, Scale,
  Target, Crosshair, ShoppingBag, Star, Award,
  UserCheck, UserX, User,
  MapPin, Layers, AlertTriangle, Zap, Clock, GitCompare, Filter, Gauge,
  Link as LinkIcon,
} from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { useDWH } from '../../context/DWHContext'

const ICON_MAP = {
  Folder: FolderIcon, FolderOpen, Table2, LayoutDashboard, FileSpreadsheet, LinkIcon,
  ShoppingCart, BarChart3, Wallet, Package, Users, LayoutGrid,
  Table, PanelTop, Settings, Database, Mail,
  FileText, Receipt, ClipboardList, FileQuestion, PackageCheck,
  Truck, Boxes, RotateCcw, Repeat, ArrowUpDown, ArrowRightLeft,
  TrendingUp, TrendingDown, PieChart, BarChart2, LineChart, Activity,
  DollarSign, CircleDollarSign, CreditCard, BadgePercent, Percent, Scale,
  Target, Crosshair, ShoppingBag, Star, Award,
  UserCheck, UserX, User,
  MapPin, Layers, AlertTriangle, Zap, Clock, GitCompare, Filter, Gauge,
}
const getIcon = (name) => ICON_MAP[name] || FolderIcon

function getUrl(menu) {
  if (menu.type === 'dashboard' && menu.target_id) return `/view/${menu.target_id}`
  if (menu.type === 'gridview' && menu.target_id) return `/grid/${menu.target_id}`
  if ((menu.type === 'pivot' || menu.type === 'pivot-v2') && menu.target_id) return `/pivot-v2/${menu.target_id}`
  if (menu.type === 'page' && menu.url) return menu.url
  return null
}

// ─── Item récursif style sidebar ─────────────────────────────────────────────
function MenuItem({ menu, depth = 0, onNavigate, location }) {
  const [open, setOpen] = useState(false)
  const hasChildren = menu.children && menu.children.length > 0
  const IconComp = getIcon(menu.icon)
  const url = getUrl(menu)
  const isActive = !!(url && location?.pathname === url)

  const handleClick = () => {
    if (hasChildren) setOpen(o => !o)
    else if (url) onNavigate(url)
  }

  return (
    <div>
      <button
        onClick={handleClick}
        className={`w-full flex items-center gap-3 rounded-lg text-sm transition-colors duration-150 pr-3
          ${depth === 0 ? 'py-2.5' : 'py-2'}
          ${isActive ? '' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700/50 active:bg-gray-100'}
        `}
        style={{
          paddingLeft: depth === 0 ? '12px' : `${12 + depth * 16}px`,
          ...(isActive ? { backgroundColor: 'var(--color-primary-100)', color: 'var(--color-primary-700)' } : {})
        }}
      >
        <IconComp
          className={`${depth === 0 ? 'w-5 h-5' : 'w-4 h-4'} flex-shrink-0`}
          style={{ color: isActive ? 'var(--color-primary-700)' : 'var(--color-primary-500)' }}
        />
        <span className="truncate font-medium flex-1 text-left">{menu.nom}</span>
        {hasChildren && (
          open
            ? <ChevronDown className="w-4 h-4 flex-shrink-0" style={{ color: 'var(--color-primary-400)' }} />
            : <ChevronRight className="w-4 h-4 flex-shrink-0" style={{ color: 'var(--color-primary-400)' }} />
        )}
      </button>
      {hasChildren && open && (
        <div className="mt-0.5 space-y-0.5">
          {menu.children.map(child => (
            <MenuItem key={child.id} menu={child} depth={depth + 1} onNavigate={onNavigate} location={location} />
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Drawer ───────────────────────────────────────────────────────────────────
export default function MobileMenuDrawer({ open, onClose, menus, appName }) {
  const navigate = useNavigate()
  const location = useLocation()
  const { user } = useAuth()
  const { currentDWH } = useDWH()

  const handleNavigate = (url) => {
    navigate(url)
    onClose()
  }

  return (
    <>
      {/* Overlay */}
      {open && (
        <div
          className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm"
          onClick={onClose}
        />
      )}

      {/* Panneau gauche */}
      <div
        className={`fixed inset-y-0 left-0 z-50 flex flex-col bg-white dark:bg-gray-800 shadow-2xl transition-transform duration-300 ease-out`}
        style={{ width: '80vw', maxWidth: 320, transform: open ? 'translateX(0)' : 'translateX(-100%)' }}
      >
        {/* Header du drawer */}
        <div
          className="flex items-center gap-3 px-4 py-4 flex-shrink-0"
          style={{ backgroundColor: 'var(--sidebar-bg, #1e40af)' }}
        >
          <div className="w-8 h-8 flex-shrink-0 flex items-center justify-center rounded-md bg-white/20">
            <span className="text-white font-extrabold text-lg leading-none">K</span>
          </div>
          <div className="flex-1 min-w-0">
            <h1 className="text-white font-bold text-base truncate">
              {appName ? appName.split(' - ')[0] : 'OptiBoard'}
            </h1>
            <p className="text-white/70 text-xs truncate">
              {appName?.includes(' - ') ? appName.split(' - ').slice(1).join(' - ') : 'Reporting'}
            </p>
            {currentDWH?.nom && (
              <p className="text-white/90 font-semibold text-xs mt-1 truncate bg-white/10 rounded px-2 py-0.5 inline-block">
                {currentDWH.nom}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-white/70 hover:text-white hover:bg-white/10 flex-shrink-0"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Menu scrollable */}
        <nav className="flex-1 overflow-y-auto px-2 py-2 space-y-0.5">
          {menus.length === 0 ? (
            <p className="text-center py-8 text-sm text-gray-400">Chargement...</p>
          ) : (
            menus.map(menu => (
              <MenuItem key={menu.id} menu={menu} depth={0} onNavigate={handleNavigate} location={location} />
            ))
          )}
        </nav>

        {/* Pied : info utilisateur */}
        {user && (
          <div className="flex-shrink-0 border-t border-gray-200 dark:border-gray-700 px-4 py-3 flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center flex-shrink-0">
              <span className="text-primary-700 dark:text-primary-300 font-bold text-sm">
                {(user.prenom?.[0] || user.username?.[0] || '?').toUpperCase()}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-gray-900 dark:text-white truncate">
                {user.prenom && user.nom ? `${user.prenom} ${user.nom}` : user.username}
              </p>
              <p className="text-xs text-gray-400 truncate">{user.role_dwh || user.role_global || user.role}</p>
            </div>
          </div>
        )}

        {/* Safe area */}
        <div className="safe-area-pb" />
      </div>
    </>
  )
}
