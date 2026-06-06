/**
 * Hook de polling simple : fetch immediat au montage, puis a intervalle regulier.
 * Cleanup correct au demontage (annulation des callbacks en vol via un flag).
 */

import { useEffect, useState } from 'react'

import { api } from '../lib/api'

export interface PollingState<T> {
  data: T | null
  loading: boolean
  error: string | null
}

export function usePolling<T>(url: string, intervalMs = 30_000): PollingState<T> {
  const [state, setState] = useState<PollingState<T>>({
    data: null,
    loading: true,
    error: null,
  })

  useEffect(() => {
    let cancelled = false

    const run = async () => {
      const res = await api<T>(url)
      if (cancelled) return
      if (res.ok && res.data !== null) {
        setState({ data: res.data, loading: false, error: null })
      } else {
        setState((s) => ({ ...s, loading: false, error: `HTTP ${res.status}` }))
      }
    }

    void run()
    const timer = setInterval(() => {
      void run()
    }, intervalMs)
    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [url, intervalMs])

  return state
}
