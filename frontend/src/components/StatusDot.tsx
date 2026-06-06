import type { Health } from '../lib/fleet'

const PRESENT: Record<Health, { cls: string; label: string }> = {
  online: { cls: 'bg-sauge-500', label: 'En ligne' },
  degraded: { cls: 'bg-chaleur-500', label: 'Dégradée' },
  silent: { cls: 'bg-brique-500', label: 'Silencieuse' },
}

export function StatusDot({ health }: { health: Health }) {
  const s = PRESENT[health]
  return (
    <span
      className="inline-flex items-center gap-1.5 text-xs text-slate-600"
      title={`Santé : ${s.label}`}
    >
      <span className={`h-2 w-2 rounded-full ${s.cls}`} aria-hidden="true" />
      <span>{s.label}</span>
    </span>
  )
}
