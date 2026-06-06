import { freshness, STALE_AFTER_MIN, timeAgoShort } from '../lib/staleness'

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
