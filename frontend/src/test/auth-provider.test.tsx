import { render, screen, waitFor } from '@testing-library/react'
import { vi } from 'vitest'

import { AuthProvider } from '../auth/AuthProvider'
import { useAuth } from '../auth/useAuth'

function Probe() {
  const { state } = useAuth()
  return <div data-testid="status">{state.status}</div>
}

function mockMe(status: number, body: unknown = {}) {
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

describe('AuthProvider', () => {
  it('passe à authenticated quand /api/auth/me répond 200', async () => {
    mockMe(200, { id: 1, email: 'admin@example.com', is_active: true, last_login_at: null })
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    )
    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('authenticated'))
  })

  it('passe à unauthenticated quand /api/auth/me répond 401', async () => {
    mockMe(401, { detail: 'Authentification requise.' })
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    )
    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('unauthenticated'))
  })
})
