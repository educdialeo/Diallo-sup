import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { ReactNode } from 'react'

import { api, setUnauthorizedHandler } from '../lib/api'
import { AuthContext } from './context'
import type { AuthContextValue, AuthState, AuthUser } from './context'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ status: 'loading' })
  // Ref vers setState pour le handler 401 (eviter une closure perimee).
  const setStateRef = useRef(setState)
  setStateRef.current = setState

  const refresh = useCallback(async () => {
    const res = await api<AuthUser>('/api/auth/me', { skipUnauthHandler: true })
    if (res.ok && res.data) {
      setState({ status: 'authenticated', user: res.data })
    } else {
      setState({ status: 'unauthenticated' })
    }
  }, [])

  const logout = useCallback(async () => {
    await api('/api/auth/logout', { method: 'POST', skipUnauthHandler: true })
    setState({ status: 'unauthenticated' })
  }, [])

  // Branche l'intercepteur global 401 sur la purge d'etat.
  useEffect(() => {
    setUnauthorizedHandler(() => {
      setStateRef.current({ status: 'unauthenticated' })
    })
  }, [])

  // Verifie la session au montage.
  useEffect(() => {
    void refresh()
  }, [refresh])

  const value = useMemo<AuthContextValue>(
    () => ({ state, refresh, logout }),
    [state, refresh, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
