import { vi } from 'vitest'

import { api, setUnauthorizedHandler } from '../lib/api'

function mockFetchOnce(status: number, body: unknown) {
  vi.stubGlobal(
    'fetch',
    vi.fn(() =>
      Promise.resolve({
        ok: status >= 200 && status < 300,
        status,
        json: () => Promise.resolve(body),
      } as Response),
    ),
  )
}

describe('api wrapper', () => {
  it('inclut credentials: include et Content-Type quand body fourni', async () => {
    const calls: Array<{ url: string; init: RequestInit }> = []
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string, init: RequestInit) => {
        calls.push({ url, init })
        return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({}) } as Response)
      }),
    )
    await api('/api/whatever', { method: 'POST', body: JSON.stringify({ a: 1 }) })
    expect(calls[0].init.credentials).toBe('include')
    const headers = new Headers(calls[0].init.headers)
    expect(headers.get('Content-Type')).toBe('application/json')
  })

  it('déclenche onUnauthorized sur 401 hors /api/auth/*', async () => {
    const handler = vi.fn()
    setUnauthorizedHandler(handler)
    mockFetchOnce(401, { detail: 'nope' })
    const res = await api('/api/establishments')
    expect(res.status).toBe(401)
    expect(handler).toHaveBeenCalledOnce()
  })

  it('ne déclenche PAS onUnauthorized sur 401 d’un endpoint /api/auth/*', async () => {
    const handler = vi.fn()
    setUnauthorizedHandler(handler)
    mockFetchOnce(401, { detail: 'Code invalide.' })
    const res = await api('/api/auth/verify-totp', {
      method: 'POST',
      body: JSON.stringify({ code: '000000' }),
    })
    expect(res.status).toBe(401)
    expect(handler).not.toHaveBeenCalled()
  })

  it('respecte skipUnauthHandler pour les check-ins /me', async () => {
    const handler = vi.fn()
    setUnauthorizedHandler(handler)
    mockFetchOnce(401, { detail: 'Authentification requise.' })
    await api('/api/auth/me', { skipUnauthHandler: true })
    expect(handler).not.toHaveBeenCalled()
  })
})
