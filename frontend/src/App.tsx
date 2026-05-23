import { Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { Dashboard } from './pages/Dashboard'
import { Etablissement } from './pages/Etablissement'
import { Reports } from './pages/Reports'
import { Deployments } from './pages/Deployments'
import { Inventory } from './pages/Inventory'
import { Settings } from './pages/Settings'

// Ossature de navigation. La page d'accueil par defaut est le Dashboard global.
// Les ecrans reels sont implementes feature par feature au chantier N1.
export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/etablissement" element={<Etablissement />} />
        <Route path="/reports" element={<Reports />} />
        <Route path="/deploiements" element={<Deployments />} />
        <Route path="/inventaire" element={<Inventory />} />
        <Route path="/reglages" element={<Settings />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Route>
    </Routes>
  )
}
