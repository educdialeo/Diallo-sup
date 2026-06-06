/**
 * Page detail d'un etablissement (chantier N1 etape 2, drill-down).
 *
 * Atteinte en cliquant une tuile de la fleet view. Reutilise usePolling 30 s,
 * StatusDot, Sparkline, charte chalkboard. Chaque panneau marque visuellement
 * sa propre fraicheur (cf lib/staleness) — un CPU% d'il y a 5 jours ne doit
 * pas passer pour du temps reel.
 */

import { Link, useParams } from 'react-router-dom'

import { Sparkline } from '../components/Sparkline'
import { StatusDot } from '../components/StatusDot'
import { usePolling } from '../hooks/usePolling'
import type {
  DaemonSnapshot,
  DialeoSnapshot,
  EstablishmentDetail as Detail,
  IncidentDetail,
  MachineHealth,
  OllamaSnapshot,
  UsageDay,
} from '../lib/fleet'
import { freshness, timeAgoShort } from '../lib/staleness'

export function EstablishmentDetail() {
  const { id } = useParams<{ id: string }>()
  const { data, loading, error } = usePolling<Detail>(`/api/fleet/${id}`, 30_000)

  return (
    <div className="mx-auto max-w-6xl">
      <Link
        to="/dashboard"
        className="inline-flex items-center text-xs text-craie-600 hover:underline"
      >
        ← Dashboard
      </Link>

      <Body data={data} loading={loading} error={error} />
    </div>
  )
}

function Body({
  data,
  loading,
  error,
}: {
  data: Detail | null
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
  // 404 -> error sera "HTTP 404"
  if (error?.includes('404')) {
    return (
      <div
        role="alert"
        className="mt-8 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-500"
      >
        Établissement introuvable.
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
      <Header detail={data} />
      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <SessionsLiveCard detail={data} />
        <MachineCard machine={data.machine} />
        <DialeoCard dialeo={data.dialeo} />
        <DaemonCard daemon={data.daemon} />
        <OllamaCard ollama={data.ollama} />
        <UsageHistoryCard history={data.usage_history} />
      </div>
      <IncidentsCard incidents={data.incidents_recent} />
    </>
  )
}

// ============================================================================
// En-tête
// ============================================================================

function Header({ detail }: { detail: Detail }) {
  return (
    <header className="mt-2 flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h1 className="text-2xl font-semibold text-slate-800">{detail.name}</h1>
        <p className="mt-1 text-xs text-slate-500">
          Statut : <span className="font-medium text-slate-700">{detail.status}</span>
          {' · '}
          Dernier signal : <span className="font-medium text-slate-700">{timeAgoShort(detail.last_heartbeat_at)}</span>
        </p>
      </div>
      <StatusDot health={detail.health} />
    </header>
  )
}

// ============================================================================
// Cartes
// ============================================================================

function Card({
  title,
  lastSeenAt,
  children,
}: {
  title: string
  lastSeenAt: string | null
  children: React.ReactNode
}) {
  const f = freshness(lastSeenAt)
  return (
    <section className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-baseline justify-between">
        <h2 className="text-sm font-semibold text-slate-800">{title}</h2>
        <FreshnessBadge lastSeenAt={lastSeenAt} freshness={f} />
      </div>
      {f === 'unknown' ? (
        <p className="text-xs text-slate-400">Non rapporté.</p>
      ) : (
        children
      )}
    </section>
  )
}

function FreshnessBadge({
  lastSeenAt,
  freshness: f,
}: {
  lastSeenAt: string | null
  freshness: 'recent' | 'stale' | 'unknown'
}) {
  if (f === 'unknown') {
    return <span className="text-[11px] text-slate-400">jamais reçu</span>
  }
  if (f === 'stale') {
    return (
      <span
        className="rounded-full bg-ambre-100 px-2 py-0.5 text-[11px] font-medium text-ambre-500"
        title={lastSeenAt ?? undefined}
      >
        périmé · {timeAgoShort(lastSeenAt)}
      </span>
    )
  }
  return (
    <span className="text-[11px] text-slate-500" title={lastSeenAt ?? undefined}>
      mis à jour {timeAgoShort(lastSeenAt)}
    </span>
  )
}

function SessionsLiveCard({ detail }: { detail: Detail }) {
  // Pas de last_seen_at dedie : on raccroche a celui du heartbeat (proxy).
  return (
    <Card title="Sessions live" lastSeenAt={detail.last_heartbeat_at}>
      <Kv label="Élèves connectés" value={detail.nb_eleves_connected ?? '—'} />
      <Kv label="Classes actives" value={detail.nb_classes_active ?? '—'} />
    </Card>
  )
}

function MachineCard({ machine }: { machine: MachineHealth }) {
  const ramPct =
    machine.ram_used_mb != null && machine.ram_total_mb
      ? Math.round((machine.ram_used_mb / machine.ram_total_mb) * 100)
      : null
  const diskPct =
    machine.disk_used_gb != null && machine.disk_total_gb
      ? Math.round((machine.disk_used_gb / machine.disk_total_gb) * 100)
      : null
  return (
    <Card title="Machine" lastSeenAt={machine.last_seen_at}>
      <Kv label="Statut global" value={machine.status_global ?? '—'} />
      <Kv
        label="CPU"
        value={machine.cpu_percent != null ? `${machine.cpu_percent} %` : '—'}
      />
      <Kv
        label="RAM"
        value={
          machine.ram_used_mb != null && machine.ram_total_mb
            ? `${(machine.ram_used_mb / 1024).toFixed(1)} / ${(machine.ram_total_mb / 1024).toFixed(0)} Go (${ramPct} %)`
            : '—'
        }
      />
      <Kv
        label="Disque"
        value={
          machine.disk_used_gb != null && machine.disk_total_gb
            ? `${machine.disk_used_gb.toFixed(0)} / ${machine.disk_total_gb.toFixed(0)} Go (${diskPct} %)`
            : '—'
        }
      />
      <Kv label="Uptime" value={uptimeShort(machine.uptime_seconds)} />
      <Kv label="Mac serial" value={machine.mac_serial ?? '—'} />
    </Card>
  )
}

function OllamaCard({ ollama }: { ollama: OllamaSnapshot }) {
  return (
    <Card title="Ollama" lastSeenAt={ollama.last_seen_at}>
      <Kv label="Modèles chargés" value={ollama.models_loaded.join(', ') || '—'} />
      <Kv label="Latence ping" value={ollama.ping_latency_ms != null ? `${ollama.ping_latency_ms} ms` : '—'} />
      <Kv label="RAM utilisée" value={ollama.ram_used_mb != null ? `${ollama.ram_used_mb} Mo` : '—'} />
      <Kv label="Dernière inférence" value={timeAgoShort(ollama.last_inference_at)} />
    </Card>
  )
}

function DialeoCard({ dialeo }: { dialeo: DialeoSnapshot }) {
  return (
    <Card title="Dialeo" lastSeenAt={dialeo.last_seen_at}>
      <Kv label="Version" value={dialeo.version ?? '—'} />
      <Kv label="Uvicorn" value={dialeo.uvicorn_status ?? '—'} />
      <Kv label="Dernier déploiement" value={timeAgoShort(dialeo.last_deploy_at)} />
      <Kv label="Modes actifs" value={dialeo.modes_active.join(', ') || '—'} />
    </Card>
  )
}

function DaemonCard({ daemon }: { daemon: DaemonSnapshot }) {
  return (
    <Card title="Daemon de surveillance" lastSeenAt={daemon.last_seen_at}>
      <Kv label="Uvicorn vu par le daemon" value={daemon.uvicorn_status ?? '—'} />
      <Kv
        label="Temps de réponse"
        value={daemon.response_time_ms != null ? `${daemon.response_time_ms} ms` : '—'}
      />
      <Kv
        label="Échecs consécutifs"
        value={daemon.consecutive_failures != null ? String(daemon.consecutive_failures) : '—'}
      />
      <Kv label="Dernière réussite" value={timeAgoShort(daemon.last_success_iso)} />
      <Kv label="Uptime daemon" value={uptimeShort(daemon.daemon_uptime_seconds)} />
    </Card>
  )
}

function UsageHistoryCard({ history }: { history: UsageDay[] }) {
  const sessions = history.map((d) => d.nb_sessions)
  const total30 = sessions.reduce((a, b) => a + b, 0)
  return (
    <section className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm lg:col-span-2">
      <div className="flex items-baseline justify-between">
        <h2 className="text-sm font-semibold text-slate-800">Historique d&apos;usage · 30 j</h2>
        <span className="text-[11px] text-slate-500">{total30} sessions sur la période</span>
      </div>
      <div className="text-craie-400">
        <Sparkline values={sessions} width={520} height={48} />
      </div>
    </section>
  )
}

function IncidentsCard({ incidents }: { incidents: IncidentDetail[] }) {
  if (incidents.length === 0) {
    return (
      <section className="mt-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-800">Incidents modération · 30 j</h2>
        <p className="mt-2 text-xs text-slate-500">Aucun incident sur la période.</p>
      </section>
    )
  }
  return (
    <section className="mt-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="text-sm font-semibold text-slate-800">
        Incidents modération · 30 j
      </h2>
      <p className="mt-1 text-[11px] text-slate-400">
        Compteurs anonymisés — aucun contenu utilisateur n&apos;est stocké.
      </p>
      <table className="mt-3 w-full text-xs">
        <thead className="text-left text-slate-500">
          <tr>
            <th className="py-1 font-medium">Reçu</th>
            <th className="py-1 font-medium">Blacklist</th>
            <th className="py-1 font-medium">LlamaGuard</th>
            <th className="py-1 font-medium">System prompt</th>
          </tr>
        </thead>
        <tbody className="text-slate-700">
          {incidents.map((it, idx) => (
            <tr key={idx} className="border-t border-slate-100">
              <td className="py-1 text-slate-500">{timeAgoShort(it.received_at)}</td>
              <td className="py-1 font-mono">{it.nb_refus_blacklist}</td>
              <td className="py-1 font-mono">{it.nb_refus_llamaguard}</td>
              <td className="py-1 font-mono">{it.nb_refus_systemprompt}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}

// ============================================================================
// Helpers d'affichage
// ============================================================================

function Kv({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-2 text-xs">
      <dt className="text-slate-500">{label}</dt>
      <dd className="font-medium text-slate-800">{value}</dd>
    </div>
  )
}

function uptimeShort(seconds: number | null | undefined): string {
  if (seconds == null) return '—'
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  if (days > 0) return `${days} j ${hours} h`
  return `${hours} h`
}
