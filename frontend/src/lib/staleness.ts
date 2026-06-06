/**
 * Helpers de fraicheur pour les panneaux de telemetrie de la page detail.
 *
 * Decision : la fraicheur est jugee cote UI (le backend renvoie last_seen_at
 * brut, sans seuil dur). Le collecteur M4 emet a 30 s / 2 min selon les flux ;
 * 10 minutes laissent une marge confortable avant de marquer "perime".
 *
 * Aucune dependance sur Date.now() au moment du calcul -> testable avec un
 * `now` injecte.
 */

export const STALE_AFTER_MIN = 10

export type Freshness = 'recent' | 'stale' | 'unknown'

export function freshness(
  lastSeenIso: string | null,
  now: Date = new Date(),
): Freshness {
  if (!lastSeenIso) return 'unknown'
  const last = new Date(lastSeenIso)
  if (Number.isNaN(last.getTime())) return 'unknown'
  const minutes = (now.getTime() - last.getTime()) / 60_000
  return minutes > STALE_AFTER_MIN ? 'stale' : 'recent'
}

export function timeAgoShort(iso: string | null, now: Date = new Date()): string {
  if (!iso) return 'jamais'
  const last = new Date(iso)
  if (Number.isNaN(last.getTime())) return 'jamais'
  const min = Math.max(0, Math.floor((now.getTime() - last.getTime()) / 60_000))
  if (min < 1) return "à l'instant"
  if (min < 60) return `il y a ${min} min`
  const h = Math.floor(min / 60)
  if (h < 24) return `il y a ${h} h`
  const d = Math.floor(h / 24)
  return `il y a ${d} j`
}
