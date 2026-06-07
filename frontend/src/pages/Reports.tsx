/**
 * Page Rapports (chantier N1 étape 4).
 *
 * Source : `GET /api/reports/overview`. Vue STRICTEMENT anonymisée :
 * aucun contenu utilisateur (questions / réponses / notes enseignants) n'est
 * récupéré du backend ni affiché. Compteurs et métadonnées uniquement.
 *
 * Cette page reste sous réserve de l'arbitrage juridique :
 * - Visualisation du CONTENU des reports (Q/R/notes) → EXCLU tant que le juriste
 *   n'a pas tranché.
 * - Liste anonymisée (date + étab + niveau + mode) → présentée ici, à VALIDER
 *   juriste RGPD (point ouvert noté au JOURNAL).
 */

import { Link } from 'react-router-dom'

import { usePolling } from '../hooks/usePolling'
import type {
  RecentReportSummary,
  ReportsOverview,
  ReportsTotals,
  TopReportingEstablishment,
} from '../lib/reports'
import { timeAgoShort } from '../lib/staleness'

export function Reports() {
  const { data, loading, error } = usePolling<ReportsOverview>(
    '/api/reports/overview',
    30_000,
  )

  return (
    <div className="mx-auto max-w-6xl">
      <header>
        <h1 className="text-2xl font-semibold text-slate-800">Rapports</h1>
        <p className="mt-1 text-sm text-slate-500">
          Aperçu agrégé des reports remontés par les établissements.
        </p>
      </header>

      <RgpdBanner />
      <Body data={data} loading={loading} error={error} />
    </div>
  )
}

function RgpdBanner() {
  return (
    <div
      role="note"
      className="mt-4 rounded-md border border-ambre-500/30 bg-ambre-100 px-3 py-2 text-xs text-ambre-500"
    >
      ⚠️ Le contenu détaillé des reports (questions, réponses, notes
      enseignants) <strong>n'est pas visualisable</strong> dans cette console
      tant que le cadre juridique n'a pas tranché. Cette page affiche
      uniquement des compteurs et la liste anonymisée (date, établissement,
      niveau, mode pédagogique).
    </div>
  )
}

function Body({
  data,
  loading,
  error,
}: {
  data: ReportsOverview | null
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
        Aucun rapport sur les 30 derniers jours.
      </div>
    )
  }

  return (
    <>
      <KpiBand totals_7d={data.totals_7d} totals_30d={data.totals_30d} />
      <BreakdownBand totals_30d={data.totals_30d} />
      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <TopCard items={data.top_establishments} />
        <RecentCard items={data.recent} />
      </div>
    </>
  )
}

// ============================================================================

function KpiBand({
  totals_7d,
  totals_30d,
}: {
  totals_7d: ReportsTotals
  totals_30d: ReportsTotals
}) {
  return (
    <section className="mt-6">
      <h2 className="text-sm font-semibold text-slate-800">Volumétrie 7 j · 30 j</h2>
      <div className="mt-2 grid grid-cols-2 gap-3">
        <Kpi label="Total 30 j" value={String(totals_30d.total)} sub={`${totals_7d.total} sur 7 j`} />
        <Kpi
          label="Établissements émetteurs"
          value="—"
          sub="Cf. tableau « Top établissements » ci-dessous"
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

function BreakdownBand({ totals_30d }: { totals_30d: ReportsTotals }) {
  return (
    <section className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
      <BreakdownCard title="Par niveau scolaire · 30 j" data={totals_30d.by_niveau} />
      <BreakdownCard title="Par mode pédagogique · 30 j" data={totals_30d.by_mode} />
    </section>
  )
}

function BreakdownCard({ title, data }: { title: string; data: Record<string, number> }) {
  const entries = Object.entries(data).sort((a, b) => b[1] - a[1])
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="text-sm font-semibold text-slate-800">{title}</h3>
      {entries.length === 0 ? (
        <p className="mt-2 text-xs text-slate-500">Aucune donnée.</p>
      ) : (
        <ul className="mt-3 space-y-1 text-xs">
          {entries.map(([k, v]) => (
            <li key={k} className="flex items-center justify-between">
              <span className="text-slate-700">{k}</span>
              <span className="font-mono text-slate-500">{v}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function TopCard({ items }: { items: TopReportingEstablishment[] }) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="text-sm font-semibold text-slate-800">Top établissements · 30 j</h2>
      {items.length === 0 ? (
        <p className="mt-2 text-xs text-slate-500">Aucun établissement émetteur.</p>
      ) : (
        <table className="mt-3 w-full text-xs">
          <thead className="text-left text-slate-500">
            <tr>
              <th className="py-1 font-medium">Établissement</th>
              <th className="py-1 text-right font-medium">Reports</th>
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
                <td className="py-1 text-right font-mono font-semibold">{it.nb_reports}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}

function RecentCard({ items }: { items: RecentReportSummary[] }) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="text-sm font-semibold text-slate-800">Derniers reports</h2>
      <p className="mt-1 text-[11px] text-slate-400">
        Métadonnées uniquement — pas de contenu utilisateur.
      </p>
      {items.length === 0 ? (
        <p className="mt-2 text-xs text-slate-500">Aucun report récent.</p>
      ) : (
        <table className="mt-3 w-full text-xs">
          <thead className="text-left text-slate-500">
            <tr>
              <th className="py-1 font-medium">Reçu</th>
              <th className="py-1 font-medium">Jour</th>
              <th className="py-1 font-medium">Établissement</th>
              <th className="py-1 font-medium">Niveaux</th>
              <th className="py-1 font-medium">Mode</th>
            </tr>
          </thead>
          <tbody className="text-slate-700">
            {items.map((it, idx) => (
              <tr key={idx} className="border-t border-slate-100">
                <td className="py-1 text-slate-500">{timeAgoShort(it.received_at)}</td>
                <td className="py-1">{it.date_jour}</td>
                <td className="py-1">
                  <Link
                    to={`/etablissement/${it.etablissement_id}`}
                    className="text-craie-600 hover:underline"
                  >
                    {it.etablissement_name}
                  </Link>
                </td>
                <td className="py-1">{it.niveau_scolaire.join(', ')}</td>
                <td className="py-1">{it.mode_pedagogique}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}
