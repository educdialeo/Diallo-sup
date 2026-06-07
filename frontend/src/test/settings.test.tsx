import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'

import { Settings } from '../pages/Settings'

function mockApi(body: unknown) {
  vi.stubGlobal(
    'fetch',
    vi.fn(() =>
      Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve(body),
      } as Response),
    ),
  )
}

const BASE = {
  app_name: 'Diallo-sup console',
  version: '0.1.0',
  host: '0.0.0.0',
  port: 8000,
  log_level: 'info',
  session_ttl_hours: 12,
  preauth_ttl_minutes: 5,
  session_cookie_secure: false,
  login_max_attempts: 5,
  login_lockout_minutes: 15,
  jwt_secret_configured: true,
  totp_at_rest_key_configured: true,
  generated_at: '2026-06-07T12:00:00Z',
}

describe('Settings', () => {
  it('rend toutes les sections en lecture seule', async () => {
    mockApi(BASE)
    render(
      <MemoryRouter>
        <Settings />
      </MemoryRouter>,
    )
    expect(await screen.findByText('Diallo-sup console')).toBeInTheDocument()
    expect(screen.getByText('Service')).toBeInTheDocument()
    expect(screen.getByText('Auth / session')).toBeInTheDocument()
    expect(screen.getByText('Anti-brute-force')).toBeInTheDocument()
    expect(screen.getByText(/Secrets/i)).toBeInTheDocument()
    // Aucun bouton de modification
    expect(screen.queryAllByRole('button')).toEqual([])
  })

  it('affiche "configuré ✅" quand les secrets sont en place', async () => {
    mockApi(BASE)
    render(
      <MemoryRouter>
        <Settings />
      </MemoryRouter>,
    )
    const ok = await screen.findAllByText(/configuré/)
    expect(ok.length).toBeGreaterThanOrEqual(2)  // JWT_SECRET + TOTP_AT_REST_KEY
  })

  it('affiche "manquant ❌" quand un secret n\'est pas configuré', async () => {
    mockApi({ ...BASE, jwt_secret_configured: false })
    render(
      <MemoryRouter>
        <Settings />
      </MemoryRouter>,
    )
    await waitFor(() =>
      expect(screen.getByText(/manquant/i)).toBeInTheDocument(),
    )
  })
})
