import { LogOut } from 'lucide-react'
import { NavLink, useNavigate } from 'react-router-dom'

import { useAuth } from '../auth/useAuth'
import { NAV_ITEMS } from '../lib/nav'
import { HealthIndicator } from './HealthIndicator'

// Sidebar verticale fixe : wordmark DiALEO + navigation + santé + déconnexion.
export function Sidebar() {
  const { state, logout } = useAuth()
  const navigate = useNavigate()
  const email = state.status === 'authenticated' ? state.user.email : null

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <aside className="flex h-full w-64 flex-col border-r border-slate-200 bg-white">
      <div className="flex h-16 items-center gap-2 px-6">
        <span className="flex h-7 w-7 items-center justify-center rounded-md bg-craie-400 text-sm font-bold text-white">
          D
        </span>
        <span className="text-lg font-bold tracking-tight text-slate-800">DiALEO</span>
        <span className="ml-1 text-xs font-medium text-slate-400">supervision</span>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-2" aria-label="Navigation principale">
        {NAV_ITEMS.map(({ path, label, icon: Icon }) => (
          <NavLink
            key={path}
            to={path}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-craie-50 text-craie-600'
                  : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
              }`
            }
          >
            <Icon className="h-4 w-4" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="space-y-3 border-t border-slate-200 px-6 py-4">
        <HealthIndicator />
        {email && (
          <div className="flex items-center justify-between gap-2 text-xs">
            <span className="truncate text-slate-500" title={email}>
              {email}
            </span>
            <button
              type="button"
              onClick={handleLogout}
              className="flex items-center gap-1 rounded px-2 py-1 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800"
              aria-label="Se déconnecter"
              title="Se déconnecter"
            >
              <LogOut className="h-3.5 w-3.5" />
              Déconnexion
            </button>
          </div>
        )}
      </div>
    </aside>
  )
}
