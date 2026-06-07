/**
 * Page Inventaire / licences (chantier N1 étape 4).
 *
 * Source : `GET /api/inventory/overview`. Affiche le parc Mac mini par
 * établissement + agrégats (total sièges, répartition par formule commerciale).
 * Lecture seule.
 */

import { Link } from 'react-router-dom'

import { usePolling } from '../hooks/usePolling'
import type { EstablishmentInventory, InventoryOverview } from '../lib/inventory'
import { timeAgoShort } from '../lib/staleness'

export function Inventory() {
  const { data, loading, error } = usePolling<InventoryOverview>(
    '/api/inventory/overview',
    30_000,
  )

  return (
    <div className="mx-auto max-w-6xl">
      <header>
        <h1 className="text-2xl font-semibold text-slate-800">Inventaire / licences</h1>
        <p className="mt-1 text-sm text-slate-500">
          Parc Mac mini déclaré par établissement et répartition des sièges.
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
  data: InventoryOverview | null
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
  if (!data) return null

  return (
    <>
      <TotalsBand totals={data.totals} />
      <ParkTable items={data.items} />
    </>
  )
}

// ============================================================================
// KPI band
// ============================================================================

function TotalsBand({ totals }: { totals: InventoryOverview['totals'] }) {
  const formulesEntries = Object.entries(totals.par_formule)
  return (
    <section className="mt-6">
      <h2 className="text-sm font-semibold text-slate-800">Synthèse flotte</h2>
      <div className="mt-2 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Kpi label="Établissements" value={String(totals.nb_etablissements)} />
        <Kpi
          label="Inventaire reçu"
          value={`${totals.nb_etablissements_renseignes} / ${totals.nb_etablissements}`}
        />
        <Kpi label="Sièges déclarés" value={String(totals.total_sieges)} />
        <Kpi
          label="Formules distinctes"
          value={String(formulesEntries.length)}
          sub={
            formulesEntries.length === 0
              ? '—'
              : formulesEntries
                  .map(([k, v]) => `${k} : ${v}`)
                  .join(' · ')
          }
        />
      </div>
    </section>
  )
}

function Kpi({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-xs font-medium text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-slate-800">{value}</p>
      {sub && <p className="mt-1 text-[11px] text-slate-400">{sub}</p>}
    </div>
  )
}

// ============================================================================
// Tableau parc
// ============================================================================

function ParkTable({ items }: { items: EstablishmentInventory[] }) {
  return (
    <section className="mt-6 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="text-sm font-semibold text-slate-800">Parc par établissement</h2>
      {items.length === 0 ? (
        <p className="mt-2 text-xs text-slate-500">Aucun établissement enregistré.</p>
      ) : (
        <table className="mt-3 w-full text-xs">
          <thead className="text-left text-slate-500">
            <tr>
              <th className="py-1 font-medium">Établissement</th>
              <th className="py-1 font-medium">Mac mini</th>
              <th className="py-1 font-medium">macOS</th>
              <th className="py-1 font-medium">Sièges</th>
              <th className="py-1 font-medium">Formule</th>
              <th className="py-1 font-medium">Dernier inventaire</th>
            </tr>
          </thead>
          <tbody className="text-slate-700">
            {items.map((it) => (
              <tr key={it.id} className="border-t border-slate-100">
                <td className="py-1">
                  <Link
                    to={`/etablissement/${it.id}`}
                    className="text-craie-600 hover:underline"
                  >
                    {it.name}
                  </Link>
                </td>
                <td className="py-1">{it.mac_mini_model ?? '—'}</td>
                <td className="py-1">{it.macos_version ?? '—'}</td>
                <td className="py-1 font-mono">{it.capacite_declaree_sieges ?? '—'}</td>
                <td className="py-1">{it.formule_commerciale ?? '—'}</td>
                <td className="py-1 text-slate-500">{timeAgoShort(it.last_seen_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}
