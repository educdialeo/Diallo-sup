import { EstablishmentTile } from '../components/EstablishmentTile'
import { usePolling } from '../hooks/usePolling'
import type { FleetResponse } from '../lib/fleet'

export function Dashboard() {
  const { data, loading, error } = usePolling<FleetResponse>('/api/fleet', 30_000)

  return (
    <div className="mx-auto max-w-6xl">
      <header>
        <h1 className="text-2xl font-semibold text-slate-800">Dashboard</h1>
        <p className="mt-1 text-sm text-slate-500">
          Vue d&apos;ensemble de la flotte d&apos;établissements supervisés.
        </p>
      </header>

      <Body data={data} loading={loading} error={error} />
    </div>
  )
}

function Body({
  data,
  loading,
  error,
}: {
  data: FleetResponse | null
  loading: boolean
  error: string | null
}) {
  if (loading && !data) {
    return (
      <div className="mt-8 text-center text-sm text-slate-500" role="status">
        Chargement…
      </div>
    )
  }
  if (error) {
    return (
      <div
        role="alert"
        className="mt-8 rounded-md border border-brique-500/30 bg-brique-100 px-3 py-2 text-sm text-brique-500"
      >
        Erreur de chargement ({error}).
      </div>
    )
  }
  const items = data?.items ?? []
  const allSilent = items.length > 0 && items.every((i) => i.health === 'silent')
  if (items.length === 0) {
    return (
      <div className="mt-8 rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-slate-500">
        Aucun établissement enregistré pour le moment.
      </div>
    )
  }
  return (
    <>
      {allSilent && (
        <div className="mt-4 rounded-md border border-slate-300 bg-slate-50 px-3 py-2 text-xs text-slate-500">
          Tous les établissements sont silencieux pour l&apos;instant — vérifiez le collecteur côté Mac mini.
        </div>
      )}
      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((it) => (
          <EstablishmentTile key={it.id} item={it} />
        ))}
      </div>
    </>
  )
}
