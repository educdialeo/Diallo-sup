/**
 * Page Modération (chantier N1 étape 3) — vue d'agrégation flotte.
 *
 * Argument de vente clé : aperçu d'ensemble de la modération sur toute la
 * flotte. Sections : KPI 7j/30j par catégorie, tendance 30 j par catégorie,
 * top établissements (drill -> page détail), N derniers incidents.
 *
 * AUCUN contenu utilisateur : compteurs uniquement.
 */

import { Link } from 'react-router-dom'

import { Sparkline } from '../components/Sparkline'
import { usePolling } from '../hooks/usePolling'
import type { IncidentsOverview, RecentIncidentItem } from '../lib/incidents'
import { timeAgoShort } from '../lib/staleness'

export function Moderation() {
  const { data, loading, error } = usePolling<IncidentsOverview>(
    '/api/incidents/overview',
    30_000,
  )

  return (
    <div className="mx-auto max-w-6xl">
      <header>
        <h1 className="text-2xl font-semibold text-slate-800">Modération</h1>
        <p className="mt-1 text-sm text-slate-500">
          Aperçu agrégé des refus de modération sur toute la flotte. Compteurs uniquement
          — aucun contenu utilisateur.
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
  data: IncidentsOverview | null
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
  if (data.totals_30d.total === 0) {
    return (
      <div className="mt-8 rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-slate-500">
        Aucun incident de modération sur les 30 derniers jours.
      </div>
    )
  }

  return (
    <>
      <KpiBand data={data} />
      <TrendBand trend={data.trend_30d} />
      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <TopEstablishmentsCard items={data.top_establishments} />
        <RecentIncidentsCard items={data.recent_incidents} />
      </div>
    </>
  )
}

// ============================================================================
// KPI 7j / 30j
// ============================================================================

function KpiBand({ data }: { data: IncidentsOverview }) {
  return (
    <section className="mt-6">
      <h2 className="text-sm font-semibold text-slate-800">Refus 7 j · 30 j</h2>
      <div className="mt-2 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <KpiCard
          label="Total"
          short={data.totals_7d.total}
          long={data.totals_30d.total}
        />
        <KpiCard
          label="Blacklist"
          short={data.totals_7d.blacklist}
          long={data.totals_30d.blacklist}
        />
        <KpiCard
          label="LlamaGuard"
          short={data.totals_7d.llamaguard}
          long={data.totals_30d.llamaguard}
        />
        <KpiCard
          label="System prompt"
          short={data.totals_7d.systemprompt}
          long={data.totals_30d.systemprompt}
        />
      </div>
    </section>
  )
}

function KpiCard({ label, short, long }: { label: string; short: number; long: number }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-xs font-medium text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-slate-800">{long}</p>
      <p className="text-[11px] text-slate-400">
        <span className="font-medium text-slate-600">{short}</span> sur 7 j
      </p>
    </div>
  )
}

// ============================================================================
// Tendance 30 j par catégorie
// ============================================================================

function TrendBand({ trend }: { trend: IncidentsOverview['trend_30d'] }) {
  return (
    <section className="mt-6 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="text-sm font-semibold text-slate-800">Tendance 30 j · par catégorie</h2>
      <div className="mt-3 space-y-3">
        <TrendRow label="Blacklist" values={trend.blacklist} />
        <TrendRow label="LlamaGuard" values={trend.llamaguard} />
        <TrendRow label="System prompt" values={trend.systemprompt} />
      </div>
    </section>
  )
}

function TrendRow({ label, values }: { label: string; values: number[] }) {
  const total = values.reduce((a, b) => a + b, 0)
  return (
    <div className="flex items-center justify-between gap-3">
      <div className="w-32 shrink-0">
        <p className="text-xs font-medium text-slate-700">{label}</p>
        <p className="text-[11px] text-slate-400">{total} sur la période</p>
      </div>
      <div className="flex-1 text-craie-400">
        <Sparkline values={values} width={520} height={32} />
      </div>
    </div>
  )
}

// ============================================================================
// Top établissements
// ============================================================================

function TopEstablishmentsCard({
  items,
}: {
  items: IncidentsOverview['top_establishments']
}) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="text-sm font-semibold text-slate-800">Top établissements · 30 j</h2>
      {items.length === 0 ? (
        <p className="mt-2 text-xs text-slate-500">Aucun établissement avec incident.</p>
      ) : (
        <table className="mt-3 w-full text-xs">
          <thead className="text-left text-slate-500">
            <tr>
              <th className="py-1 font-medium">Établissement</th>
              <th className="py-1 font-medium">BL</th>
              <th className="py-1 font-medium">LG</th>
              <th className="py-1 font-medium">SP</th>
              <th className="py-1 text-right font-medium">Total</th>
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
                <td className="py-1 font-mono">{it.nb_refus_blacklist}</td>
                <td className="py-1 font-mono">{it.nb_refus_llamaguard}</td>
                <td className="py-1 font-mono">{it.nb_refus_systemprompt}</td>
                <td className="py-1 text-right font-mono font-semibold">{it.total}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}

// ============================================================================
// Derniers incidents (tous étabs)
// ============================================================================

function RecentIncidentsCard({ items }: { items: RecentIncidentItem[] }) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="text-sm font-semibold text-slate-800">Derniers incidents</h2>
      {items.length === 0 ? (
        <p className="mt-2 text-xs text-slate-500">Aucun incident récent.</p>
      ) : (
        <table className="mt-3 w-full text-xs">
          <thead className="text-left text-slate-500">
            <tr>
              <th className="py-1 font-medium">Reçu</th>
              <th className="py-1 font-medium">Établissement</th>
              <th className="py-1 font-medium">BL</th>
              <th className="py-1 font-medium">LG</th>
              <th className="py-1 font-medium">SP</th>
            </tr>
          </thead>
          <tbody className="text-slate-700">
            {items.map((it, idx) => (
              <tr key={idx} className="border-t border-slate-100">
                <td className="py-1 text-slate-500">{timeAgoShort(it.received_at)}</td>
                <td className="py-1">
                  <Link
                    to={`/etablissement/${it.etablissement_id}`}
                    className="text-craie-600 hover:underline"
                  >
                    {it.etablissement_name}
                  </Link>
                </td>
                <td className="py-1 font-mono">{it.nb_refus_blacklist}</td>
                <td className="py-1 font-mono">{it.nb_refus_llamaguard}</td>
                <td className="py-1 font-mono">{it.nb_refus_systemprompt}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}
