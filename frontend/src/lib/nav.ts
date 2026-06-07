import {
  Boxes,
  Building2,
  FileWarning,
  LayoutDashboard,
  Rocket,
  Settings,
  ShieldAlert,
  type LucideIcon,
} from 'lucide-react'

export interface NavItem {
  path: string
  label: string
  icon: LucideIcon
}

// 7 ecrans N1, dans l'ordre de la sidebar (Moderation en cluster supervision
// avec Dashboard / Vue etablissement, AVANT Reports).
export const NAV_ITEMS: NavItem[] = [
  { path: '/dashboard', label: 'Dashboard global', icon: LayoutDashboard },
  { path: '/etablissement', label: 'Vue établissement', icon: Building2 },
  { path: '/moderation', label: 'Modération', icon: ShieldAlert },
  { path: '/reports', label: 'Reports', icon: FileWarning },
  { path: '/deploiements', label: 'Déploiements N2', icon: Rocket },
  { path: '/inventaire', label: 'Inventaire / licences', icon: Boxes },
  { path: '/reglages', label: 'Réglages console', icon: Settings },
]
