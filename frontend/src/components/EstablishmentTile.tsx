import { Link } from 'react-router-dom'

import type { FleetItem } from '../lib/fleet'
import { timeAgoShort } from '../lib/staleness'
import { Sparkline } from './Sparkline'
import { StatusDot } from './StatusDot'

// Adapte timeAgoShort en variante "Il y a X" (majuscule, "Jamais" capitalisé)
// pour rester cohérent avec le style "Dernier signal : ..." de la tuile.
function timeAgo(iso: string | null): string {
  if (!iso) return 'Jamais'
  const s = timeAgoShort(iso)
  return s.charAt(0).toUpperCase() + s.slice(1)
}

export function EstablishmentTile({ item }: { item: FleetItem }) {
  return (
    <Link
      to={`/etablissement/${item.id}`}
      aria-label={`Voir le détail de ${item.name}`}
      className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition-colors hover:border-craie-300 hover:shadow"
    >
      {/* Haut : nom + pastille de santé */}
      <header className="flex items-start justify-between gap-2">
        <h3 className="text-sm font-semibold text-slate-800">{item.name}</h3>
        <StatusDot health={item.health} />
      </header>

      {/* Milieu : live + usage + sparkline */}
      <dl className="space-y-1.5 text-xs text-slate-600">
        <Row label="Élèves connectés">
          <span className="font-medium text-slate-800">
            {item.nb_eleves_connected ?? '—'}
          </span>
          {item.nb_classes_active != null && (
            <span className="ml-1 text-slate-400">
              ({item.nb_classes_active} classe{item.nb_classes_active > 1 ? 's' : ''})
            </span>
          )}
        </Row>
        <Row label="Sessions 7 j">
          <span className="font-medium text-slate-800">{item.sessions_7j}</span>
        </Row>
        <Row label="Durée moyenne">
          <span className="font-medium text-slate-800">
            {item.duree_moyenne_min != null ? `${item.duree_moyenne_min.toFixed(0)} min` : '—'}
          </span>
        </Row>
        <Row label="Tendance 14 j">
          <span className="text-craie-400">
            <Sparkline values={item.trend_14d} />
          </span>
        </Row>
      </dl>
      <p className="text-[11px] text-slate-400">Dernier signal : {timeAgo(item.last_heartbeat_at)}</p>

      {/* Bas : badges alertes / dormant */}
      {(item.incidents_recent > 0 || item.is_dormant) && (
        <footer className="flex flex-wrap gap-2">
          {item.incidents_recent > 0 && (
            <span className="rounded-full bg-chaleur-100 px-2 py-0.5 text-xs font-medium text-chaleur-500">
              {item.incidents_recent} refus modération (7 j)
            </span>
          )}
          {item.is_dormant && (
            <span className="rounded-full bg-ambre-100 px-2 py-0.5 text-xs font-medium text-ambre-500">
              Dormant
            </span>
          )}
        </footer>
      )}
    </Link>
  )
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <dt>{label}</dt>
      <dd>{children}</dd>
    </div>
  )
}
