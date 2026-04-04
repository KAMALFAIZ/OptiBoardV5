import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import Loading from '../components/common/Loading'
import { getBuilderDashboards } from '../services/api'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'
import OnboardingWizard from '../components/onboarding/OnboardingWizard'
import {
  LayoutGrid, Star, Clock, Table, BarChart2, GitBranch,
  ChevronRight, StarOff, Users
} from 'lucide-react'

const REPORT_ICONS = {
  gridview: Table,
  dashboard: BarChart2,
  pivot: GitBranch,
}
const REPORT_LABELS = {
  gridview: 'GridView',
  dashboard: 'Dashboard',
  pivot: 'Pivot',
}
const TYPE_COLORS = {
  gridview: 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 border-blue-100 dark:border-blue-800/30',
  dashboard: 'bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400 border-indigo-100 dark:border-indigo-800/30',
  pivot: 'bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-400 border-purple-100 dark:border-purple-800/30',
}

const TABS = [
  { id: 'role',    label: 'Tableau de bord',    icon: Users },
  { id: 'favs',   label: 'Mes favoris',         icon: Star  },
  { id: 'recents',label: 'Récemment visités',   icon: Clock },
]

function ReportCard({ item, onRemoveFav, isFavorite }) {
  const Icon = REPORT_ICONS[item.report_type] || LayoutGrid
  const colorClass = TYPE_COLORS[item.report_type] || TYPE_COLORS.gridview

  return (
    <div className="group relative bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 hover:border-primary-300 dark:hover:border-primary-600 shadow-sm hover:shadow-md transition-all overflow-hidden">
      <Link to={item.url} className="flex flex-col h-full p-4">
        <div className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-xs font-medium border w-fit mb-3 ${colorClass}`}>
          <Icon className="w-3.5 h-3.5" />
          {REPORT_LABELS[item.report_type] || item.report_type}
        </div>
        <h3 className="font-semibold text-gray-900 dark:text-white text-sm leading-snug line-clamp-2 flex-1">{item.nom}</h3>
        <div className="flex items-center justify-between mt-3">
          <span className="text-xs text-gray-400 dark:text-gray-500">
            {item.visited_at
              ? `Visité ${new Date(item.visited_at).toLocaleDateString('fr-FR')}`
              : item.created_at
                ? `Ajouté ${new Date(item.created_at).toLocaleDateString('fr-FR')}`
                : ''
            }
          </span>
          <ChevronRight className="w-4 h-4 text-primary-400 group-hover:translate-x-0.5 transition-transform" />
        </div>
      </Link>
      {isFavorite && onRemoveFav && (
        <button
          onClick={(e) => { e.preventDefault(); onRemoveFav(item) }}
          className="absolute top-2 right-2 p-1 rounded-md opacity-0 group-hover:opacity-100 transition-opacity text-amber-400 hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20"
          title="Retirer des favoris"
        >
          <StarOff className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  )
}

export default function HomePage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [loading, setLoading] = useState(true)
  const [favorites, setFavorites] = useState([])
  const [recents, setRecents] = useState([])
  const [roleReports, setRoleReports] = useState([])
  const [showPersonal, setShowPersonal] = useState(false)
  const [activeTab, setActiveTab] = useState('role')
  const [showOnboarding, setShowOnboarding] = useState(false)

  // Afficher le wizard si l'utilisateur n'a pas encore fait l'onboarding
  useEffect(() => {
    if (user && user.onboarding_done === false) {
      setShowOnboarding(true)
    }
  }, [user])

  useEffect(() => {
    const init = async () => {
      try {
        if (user?.id) {
          const [favRes, recRes, dashRes, roleRes] = await Promise.all([
            api.get('/favorites', { params: { user_id: user.id } }),
            api.get('/favorites/recents', { params: { user_id: user.id, limit: 8 } }),
            getBuilderDashboards(user.id),
            api.get('/favorites/role-reports', { params: { user_id: user.id } }).catch(() => ({ data: { data: [] } })),
          ])

          const favs = favRes.data.data || []
          const recs = recRes.data.data || []

          // Dashboards du rôle — fallback sur tous les publics si vide
          let roleData = roleRes.data?.data || []
          if (roleData.length === 0) {
            const allDash = dashRes.data?.data || dashRes.data || []
            roleData = allDash
              .filter(d => d.is_public)
              .map(d => ({
                report_type: 'dashboard',
                report_id: d.id,
                nom: d.nom,
                url: `/view/${d.id}`,
              }))
          }

          setFavorites(favs)
          setRecents(recs)
          setRoleReports(roleData)

          if (roleData.length === 0) setActiveTab('favs')

          if (favs.length > 0 || recs.length > 0 || roleData.length > 0) {
            setShowPersonal(true)
            setLoading(false)
            return
          }
        }

        const res = await getBuilderDashboards()
        const dashboards = res.data?.data || res.data || []
        if (dashboards.length > 0) {
          const pub = dashboards.find(d => d.is_public)
          const target = pub || dashboards[0]
          navigate(`/view/${target.id}`, { replace: true })
          return
        }
        setShowPersonal(true)
      } catch (e) {
        console.error('Erreur chargement homepage:', e)
        setShowPersonal(true)
      } finally {
        setLoading(false)
      }
    }
    init()
  }, [navigate, user?.id])

  const removeFavorite = async (item) => {
    try {
      await api.delete('/favorites', {
        params: { user_id: user.id, report_type: item.report_type, report_id: item.report_id }
      })
      setFavorites(prev => prev.filter(f => f.id !== item.id))
    } catch (e) {
      console.error(e)
    }
  }

  if (loading) return <Loading message="Chargement..." />
  if (!showPersonal) return null

  const recentNotInFav = recents.filter(r =>
    !favorites.some(f => f.report_type === r.report_type && f.report_id === r.report_id)
  )

  // Badge counts par onglet
  const counts = {
    role: roleReports.length,
    favs: favorites.length,
    recents: recentNotInFav.length,
  }

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      {/* Onboarding wizard — premier login uniquement */}
      {showOnboarding && (
        <OnboardingWizard onClose={() => setShowOnboarding(false)} />
      )}
      {/* En-tête */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Bonjour{user?.nom ? `, ${user.nom}` : ''} 👋
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">Vos rapports et tableaux de bord</p>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="-mb-px flex gap-1">
          {TABS.map(({ id, label, icon: Icon }) => {
            const isActive = activeTab === id
            return (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                className={`inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap
                  ${isActive
                    ? 'border-primary-500 text-primary-600 dark:text-primary-400'
                    : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:border-gray-300 dark:hover:border-gray-600'
                  }`}
              >
                <Icon className={`w-4 h-4 ${id === 'favs' && isActive ? 'fill-primary-500' : ''}`} />
                {label}
                {counts[id] > 0 && (
                  <span className={`text-xs px-1.5 py-0.5 rounded-full font-medium
                    ${isActive
                      ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400'
                    }`}
                  >
                    {counts[id]}
                  </span>
                )}
              </button>
            )
          })}
        </nav>
      </div>

      {/* Contenu de l'onglet actif */}
      {activeTab === 'role' && (
        roleReports.length > 0 ? (
          <div className="grid grid-cols-4 gap-4">
            {roleReports.map(item => (
              <ReportCard key={`role-${item.report_type}-${item.report_id}`} item={item} />
            ))}
          </div>
        ) : (
          <div className="rounded-xl border-2 border-dashed border-gray-200 dark:border-gray-700 p-10 text-center">
            <Users className="w-10 h-10 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
            <p className="font-medium text-gray-500 dark:text-gray-400">Aucun tableau de bord assigné à votre rôle</p>
          </div>
        )
      )}

      {activeTab === 'favs' && (
        favorites.length > 0 ? (
          <div className="grid grid-cols-4 gap-4">
            {favorites.map(item => (
              <ReportCard key={item.id} item={item} isFavorite onRemoveFav={removeFavorite} />
            ))}
          </div>
        ) : (
          <div className="rounded-xl border-2 border-dashed border-gray-200 dark:border-gray-700 p-10 text-center">
            <Star className="w-10 h-10 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
            <p className="font-medium text-gray-500 dark:text-gray-400">Aucun favori pour l'instant</p>
            <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">Cliquez sur ⭐ dans un rapport pour l'ajouter ici</p>
          </div>
        )
      )}

      {activeTab === 'recents' && (
        recentNotInFav.length > 0 ? (
          <div className="grid grid-cols-4 gap-4">
            {recentNotInFav.map(item => (
              <ReportCard key={`${item.report_type}-${item.report_id}`} item={item} />
            ))}
          </div>
        ) : (
          <div className="rounded-xl border-2 border-dashed border-gray-200 dark:border-gray-700 p-10 text-center">
            <Clock className="w-10 h-10 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
            <p className="font-medium text-gray-500 dark:text-gray-400">Aucune visite récente</p>
          </div>
        )
      )}
    </div>
  )
}
