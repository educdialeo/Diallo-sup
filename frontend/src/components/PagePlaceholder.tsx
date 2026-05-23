import type { ReactNode } from 'react'

// Gabarit commun des 6 écrans tant qu'ils ne sont pas implémentés (chantier N1).
export function PagePlaceholder({
  title,
  description,
  children,
}: {
  title: string
  description: string
  children?: ReactNode
}) {
  return (
    <div className="mx-auto max-w-5xl">
      <h1 className="text-2xl font-semibold text-slate-800">{title}</h1>
      <p className="mt-1 text-sm text-slate-500">{description}</p>
      <div className="mt-6 rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center">
        <p className="text-sm font-medium text-slate-600">Écran à venir</p>
        <p className="mt-1 text-xs text-slate-400">Implémenté au chantier N1.</p>
        {children}
      </div>
    </div>
  )
}
