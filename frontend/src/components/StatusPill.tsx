type Status = 'ok' | 'warning' | 'critical'

const STYLES: Record<Status, { label: string; className: string }> = {
  ok: { label: 'OK', className: 'bg-sauge-100 text-sauge-500' },
  warning: { label: 'Warning', className: 'bg-chaleur-100 text-chaleur-500' },
  critical: { label: 'Critique', className: 'bg-brique-100 text-brique-500' },
}

// Matérialise les 3 couleurs fonctionnelles de la charte Dialeo.
export function StatusPill({ status, label }: { status: Status; label?: string }) {
  const style = STYLES[status]
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${style.className}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {label ?? style.label}
    </span>
  )
}
