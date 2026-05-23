import { useLocation } from 'react-router-dom'
import { NAV_ITEMS } from '../lib/nav'

// Fil d'Ariane contextuel : Console / <écran courant>.
export function Breadcrumb() {
  const { pathname } = useLocation()
  const current = NAV_ITEMS.find((item) => pathname.startsWith(item.path))
  return (
    <nav className="text-sm" aria-label="Fil d'Ariane">
      <span className="text-slate-400">Console</span>
      <span className="mx-2 text-slate-300">/</span>
      <span className="font-medium text-slate-700">{current?.label ?? '—'}</span>
    </nav>
  )
}
