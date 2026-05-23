import { useEffect, useState } from 'react'

export type HealthState = 'loading' | 'ok' | 'offline'

interface HealthResponse {
  status: string
  service: string
}

// Sonde l'endpoint /health du backend (preuve d'integration front <-> back).
// Une seule verification au montage : le rafraichissement temps reel (SSE) est
// hors scope de ce chantier.
export function useHealth(): { state: HealthState; service: string | null } {
  const [state, setState] = useState<HealthState>('loading')
  const [service, setService] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function check() {
      try {
        const res = await fetch('/health')
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = (await res.json()) as HealthResponse
        if (!cancelled) {
          setState(data.status === 'ok' ? 'ok' : 'offline')
          setService(data.service ?? null)
        }
      } catch {
        if (!cancelled) {
          setState('offline')
          setService(null)
        }
      }
    }

    void check()
    return () => {
      cancelled = true
    }
  }, [])

  return { state, service }
}
