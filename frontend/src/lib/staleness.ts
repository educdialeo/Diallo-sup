/**
 * Helpers de fraicheur pour les panneaux de telemetrie de la page detail.
 *
 * Decision : la fraicheur est jugee cote UI (le backend renvoie last_seen_at
 * brut, sans seuil dur). Le collecteur M4 emet a 30 s / 2 min selon les flux ;
 * 10 minutes laissent une marge confortable avant de marquer "perime".
 *
 * Aucune dependance sur Date.now() au moment du calcul -> testable avec un
 * `now` injecte.
 *
 * Filet de fuseau : `parseUtcIso` traite TOUT timestamp sans marqueur comme
 * UTC. Cela aligne le frontend sur le contrat backend (fix 2026-06-07,
 * cf `app/schemas/_utc.py`) ET protege contre les timestamps issus du payload
 * (chaines brutes que UtcDatetime backend ne touche pas).
 */

export const STALE_AFTER_MIN = 10

export type Freshness = 'recent' | 'stale' | 'unknown'

/**
 * Parse un ISO 8601 en `Date`. Si la string n'a pas de marqueur de fuseau
 * (`Z`, `+HH:MM`, `-HH:MM`), on l'interprete comme UTC (cohérent avec le
 * contrat backend ; sinon JS la parserait en heure LOCALE et introduirait
 * un decalage selon le fuseau du serveur).
 */
export function parseUtcIso(iso: string): Date {
  if (/[Zz]$|[+-]\d\d:?\d\d$/.test(iso)) return new Date(iso)
  return new Date(iso + 'Z')
}

export function freshness(
  lastSeenIso: string | null,
  now: Date = new Date(),
): Freshness {
  if (!lastSeenIso) return 'unknown'
  const last = parseUtcIso(lastSeenIso)
  if (Number.isNaN(last.getTime())) return 'unknown'
  const minutes = (now.getTime() - last.getTime()) / 60_000
  return minutes > STALE_AFTER_MIN ? 'stale' : 'recent'
}

export function timeAgoShort(iso: string | null, now: Date = new Date()): string {
  if (!iso) return 'jamais'
  const last = parseUtcIso(iso)
  if (Number.isNaN(last.getTime())) return 'jamais'
  const min = Math.max(0, Math.floor((now.getTime() - last.getTime()) / 60_000))
  if (min < 1) return "à l'instant"
  if (min < 60) return `il y a ${min} min`
  const h = Math.floor(min / 60)
  if (h < 24) return `il y a ${h} h`
  const d = Math.floor(h / 24)
  return `il y a ${d} j`
}
