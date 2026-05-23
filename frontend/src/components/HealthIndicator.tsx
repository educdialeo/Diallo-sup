import { useHealth, type HealthState } from '../hooks/useHealth'

const DOT: Record<HealthState, string> = {
  loading: 'bg-slate-300',
  ok: 'bg-sauge-500',
  offline: 'bg-brique-500',
}

const TEXT: Record<HealthState, string> = {
  loading: 'vérification…',
  ok: 'console : ok',
  offline: 'hors-ligne',
}

// Affiche l'état de la liaison avec le backend (GET /health).
export function HealthIndicator() {
  const { state } = useHealth()
  return (
    <div className="flex items-center gap-2 text-xs text-slate-500">
      <span className={`h-2 w-2 rounded-full ${DOT[state]}`} />
      <span>{TEXT[state]}</span>
    </div>
  )
}
