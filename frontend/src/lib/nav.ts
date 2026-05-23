import {
  Boxes,
  Building2,
  FileWarning,
  LayoutDashboard,
  Rocket,
  Settings,
  type LucideIcon,
} from 'lucide-react'

export interface NavItem {
  path: string
  label: string
  icon: LucideIcon
}

// Les 6 ecrans cibles N1, dans l'ordre de la sidebar.
export const NAV_ITEMS: NavItem[] = [
  { path: '/dashboard', label: 'Dashboard global', icon: LayoutDashboard },
  { path: '/etablissement', label: 'Vue établissement', icon: Building2 },
  { path: '/reports', label: 'Reports', icon: FileWarning },
  { path: '/deploiements', label: 'Déploiements N2', icon: Rocket },
  { path: '/inventaire', label: 'Inventaire / licences', icon: Boxes },
  { path: '/reglages', label: 'Réglages console', icon: Settings },
]
