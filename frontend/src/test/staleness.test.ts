import { freshness, parseUtcIso, STALE_AFTER_MIN, timeAgoShort } from '../lib/staleness'

const NOW = new Date('2026-06-06T12:00:00Z')

describe('freshness', () => {
  it('renvoie unknown pour null ou date invalide', () => {
    expect(freshness(null, NOW)).toBe('unknown')
    expect(freshness('pas-une-date', NOW)).toBe('unknown')
  })

  it('renvoie recent en dessous du seuil', () => {
    const recent = new Date(NOW.getTime() - 60_000).toISOString()  // 1 min
    expect(freshness(recent, NOW)).toBe('recent')
  })

  it('renvoie stale au-delà du seuil', () => {
    const stale = new Date(NOW.getTime() - (STALE_AFTER_MIN + 1) * 60_000).toISOString()
    expect(freshness(stale, NOW)).toBe('stale')
  })
})

describe('timeAgoShort', () => {
  it('formate "à l\'instant", min, h, j', () => {
    expect(timeAgoShort(null, NOW)).toBe('jamais')
    expect(timeAgoShort(new Date(NOW.getTime() - 30_000).toISOString(), NOW)).toBe("à l'instant")
    expect(timeAgoShort(new Date(NOW.getTime() - 5 * 60_000).toISOString(), NOW)).toBe('il y a 5 min')
    expect(timeAgoShort(new Date(NOW.getTime() - 3 * 3600_000).toISOString(), NOW)).toBe('il y a 3 h')
    expect(timeAgoShort(new Date(NOW.getTime() - 5 * 86400_000).toISOString(), NOW)).toBe('il y a 5 j')
  })
})

// === Filet de fuseau (fix 2026-06-07) ======================================

describe('parseUtcIso', () => {
  it('parse une ISO avec Z comme UTC', () => {
    expect(parseUtcIso('2026-06-01T17:01:21Z').toISOString()).toBe('2026-06-01T17:01:21.000Z')
  })

  it('parse une ISO avec offset +HH:MM comme UTC', () => {
    expect(parseUtcIso('2026-06-07T10:36:52+00:00').toISOString()).toBe('2026-06-07T10:36:52.000Z')
  })

  it('traite une ISO sans marqueur comme UTC (sinon JS prendrait LOCAL)', () => {
    const naive = parseUtcIso('2026-06-01T17:01:21.050934')
    const explicit = parseUtcIso('2026-06-01T17:01:21.050934Z')
    expect(naive.getTime()).toBe(explicit.getTime())
  })
})

describe('freshness — filet de fuseau', () => {
  it('un timestamp sans Z il y a 1 min est considéré recent (pas stale)', () => {
    // Reproduit le bug CEST : si on parsait en LOCAL, on aurait +2 h dans le
    // passé et la valeur passerait au-dessus du seuil 10 min -> stale.
    const oneMinAgoNoTz = '2026-06-06T11:59:00'  // 1 min avant NOW (sans Z)
    expect(freshness(oneMinAgoNoTz, NOW)).toBe('recent')
  })

  it('un timestamp avec Z et sans Z à la même heure donnent le même résultat', () => {
    const withZ = '2026-06-06T11:59:00Z'
    const withoutZ = '2026-06-06T11:59:00'
    expect(freshness(withZ, NOW)).toBe(freshness(withoutZ, NOW))
  })
})
