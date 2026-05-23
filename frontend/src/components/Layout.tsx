import { Outlet } from 'react-router-dom'
import { Breadcrumb } from './Breadcrumb'
import { Sidebar } from './Sidebar'

// Chrome de la console : sidebar fixe + topbar (breadcrumb) + zone de contenu.
export function Layout() {
  return (
    <div className="flex h-screen bg-slate-50">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex h-16 shrink-0 items-center border-b border-slate-200 bg-white px-8">
          <Breadcrumb />
        </header>
        <main className="flex-1 overflow-auto p-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
