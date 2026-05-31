import { useContext } from 'react'

import { AuthContext } from './context'
import type { AuthContextValue } from './context'

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (ctx === null) {
    throw new Error('useAuth doit être utilisé à l’intérieur d’un <AuthProvider>.')
  }
  return ctx
}
