import { Navigate, Route, Routes } from 'react-router-dom'

import { RequireAuth } from './auth/RequireAuth'
import { Layout } from './components/Layout'
import { Dashboard } from './pages/Dashboard'
import { Deployments } from './pages/Deployments'
import { EstablishmentDetail } from './pages/EstablishmentDetail'
import { Etablissement } from './pages/Etablissement'
import { Inventory } from './pages/Inventory'
import { Moderation } from './pages/Moderation'
import { Reports } from './pages/Reports'
import { Settings } from './pages/Settings'
import { Login } from './pages/auth/Login'

// La page d'accueil par defaut est le Dashboard global. Les 7 ecrans sont
// derriere RequireAuth (session admin requise) ; /login est public.
export function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<RequireAuth />}>
        <Route element={<Layout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/etablissement" element={<Etablissement />} />
          <Route path="/etablissement/:id" element={<EstablishmentDetail />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/moderation" element={<Moderation />} />
          <Route path="/deploiements" element={<Deployments />} />
          <Route path="/inventaire" element={<Inventory />} />
          <Route path="/reglages" element={<Settings />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Route>
      </Route>
    </Routes>
  )
}
