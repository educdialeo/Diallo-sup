import { createContext } from 'react'

export interface AuthUser {
  id: number
  email: string
  is_active: boolean
  last_login_at: string | null
}

export type AuthState =
  | { status: 'loading' }
  | { status: 'unauthenticated' }
  | { status: 'authenticated'; user: AuthUser }

export interface AuthContextValue {
  state: AuthState
  /** Re-fetch /api/auth/me (apres login OK ou pour resynchroniser). */
  refresh: () => Promise<void>
  /** POST /api/auth/logout puis purge de l'etat. */
  logout: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)
