import { NavLink, useLocation } from 'react-router-dom'
import { Menu, User, Home, MessageSquare } from 'lucide-react'

export default function BottomNavBar({ onMenuOpen }) {
  const location = useLocation()
  const isHome = location.pathname === '/'

  return (
    <nav className="flex-shrink-0 bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700 safe-area-pb">
      <div className="flex">
        {/* Accueil */}
        <NavLink
          to="/"
          className="flex-1 flex flex-col items-center justify-center py-2 gap-0.5 transition-colors"
        >
          <Home className={`w-5 h-5 ${isHome ? 'text-primary-600 dark:text-primary-400' : 'text-gray-400 dark:text-gray-500'}`} />
          <span className={`text-xs font-medium ${isHome ? 'text-primary-600 dark:text-primary-400' : 'text-gray-400 dark:text-gray-500'}`}>
            Accueil
          </span>
        </NavLink>

        {/* Menu (drawer gauche) */}
        <button
          onClick={onMenuOpen}
          className="flex-1 flex flex-col items-center justify-center py-2 gap-0.5 transition-colors text-gray-400 dark:text-gray-500 hover:text-primary-600 dark:hover:text-primary-400"
        >
          <Menu className="w-5 h-5" />
          <span className="text-xs font-medium">Menu</span>
        </button>

        {/* Chat IA */}
        <NavLink
          to="/chat"
          className="flex-1 flex flex-col items-center justify-center py-2 gap-0.5 transition-colors"
        >
          {({ isActive }) => (
            <>
              <MessageSquare className={`w-5 h-5 ${isActive ? 'text-primary-600 dark:text-primary-400' : 'text-gray-400 dark:text-gray-500'}`} />
              <span className={`text-xs font-medium ${isActive ? 'text-primary-600 dark:text-primary-400' : 'text-gray-400 dark:text-gray-500'}`}>
                Assistant
              </span>
            </>
          )}
        </NavLink>

        {/* Compte */}
        <NavLink
          to="/profil"
          className="flex-1 flex flex-col items-center justify-center py-2 gap-0.5 transition-colors"
        >
          {({ isActive }) => (
            <>
              <User className={`w-5 h-5 ${isActive ? 'text-primary-600 dark:text-primary-400' : 'text-gray-400 dark:text-gray-500'}`} />
              <span className={`text-xs font-medium ${isActive ? 'text-primary-600 dark:text-primary-400' : 'text-gray-400 dark:text-gray-500'}`}>
                Compte
              </span>
            </>
          )}
        </NavLink>
      </div>
    </nav>
  )
}
