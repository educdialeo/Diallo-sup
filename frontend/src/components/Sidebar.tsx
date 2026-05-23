import { NavLink } from 'react-router-dom'
import { NAV_ITEMS } from '../lib/nav'
import { HealthIndicator } from './HealthIndicator'

// Sidebar verticale fixe : wordmark DiALEO + navigation + état console.
export function Sidebar() {
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

      <div className="border-t border-slate-200 px-6 py-4">
        <HealthIndicator />
      </div>
    </aside>
  )
}
