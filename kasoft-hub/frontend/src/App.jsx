import React from 'react'
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import DashboardPage from './pages/DashboardPage'
import ContactsPage from './pages/ContactsPage'
import TicketsPage from './pages/TicketsPage'
import CampaignsPage from './pages/CampaignsPage'
import WorkflowsPage from './pages/WorkflowsPage'
import TemplatesPage from './pages/TemplatesPage'
import SettingsPage from './pages/SettingsPage'

const navItems = [
  { to: '/',           label: 'Dashboard',   icon: '📊' },
  { to: '/contacts',   label: 'Contacts',    icon: '👥' },
  { to: '/tickets',    label: 'SAV',         icon: '🎫' },
  { to: '/campaigns',  label: 'Campagnes',   icon: '📣' },
  { to: '/workflows',  label: 'Workflows',   icon: '⚡' },
  { to: '/templates',  label: 'Templates',   icon: '📝' },
  { to: '/settings',   label: 'Paramètres',  icon: '⚙️' },
]

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen bg-gray-50">
        {/* Sidebar */}
        <aside className="w-56 bg-gray-900 text-white flex flex-col shrink-0">
          <div className="p-4 border-b border-gray-700">
            <div className="text-lg font-bold text-white">KAsoft Hub</div>
            <div className="text-xs text-gray-400">Automation Centre</div>
          </div>
          <nav className="flex-1 p-3 space-y-1">
            {navItems.map(({ to, label, icon }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  `flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                    isActive
                      ? 'bg-indigo-600 text-white'
                      : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                  }`
                }
              >
                <span>{icon}</span>
                <span>{label}</span>
              </NavLink>
            ))}
          </nav>
          <div className="p-3 border-t border-gray-700 text-xs text-gray-500">
            v1.0.0 — OptiBoard, OptiBTP,<br />OptiCRM, OptiPromImmo
          </div>
        </aside>

        {/* Main content */}
        <main className="flex-1 overflow-auto">
          <Routes>
            <Route path="/"          element={<DashboardPage />} />
            <Route path="/contacts"  element={<ContactsPage />} />
            <Route path="/tickets"   element={<TicketsPage />} />
            <Route path="/campaigns" element={<CampaignsPage />} />
            <Route path="/workflows" element={<WorkflowsPage />} />
            <Route path="/templates" element={<TemplatesPage />} />
            <Route path="/settings"  element={<SettingsPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
