import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'

import { AuthContext } from '../auth/context'
import type { AuthContextValue } from '../auth/context'
import { Login } from '../pages/auth/Login'

const unauthCtx: AuthContextValue = {
  state: { status: 'unauthenticated' },
  refresh: async () => undefined,
  logout: async () => undefined,
}

function mockFetchByUrl(handlers: Record<string, () => { status: number; body: unknown }>) {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string) => {
      const handler = handlers[url]
      if (!handler) {
        return Promise.reject(new Error(`fetch non mocké pour ${url}`))
      }
      const { status, body } = handler()
      return Promise.resolve({
        ok: status >= 200 && status < 300,
        status,
        json: () => Promise.resolve(body),
      } as Response)
    }),
  )
}

async function walkToRecoveryCodes() {
  mockFetchByUrl({
    '/api/auth/login': () => ({ status: 200, body: { status: 'enrolement_requis' } }),
    '/api/auth/totp/enroll': () => ({
      status: 200,
      body: { otpauth_uri: 'otpauth://totp/DialSup:a@b.c?secret=ABCDEFGHIJKLMNOP&issuer=DialSup' },
    }),
    '/api/auth/totp/confirm': () => ({
      status: 200,
      body: {
        recovery_codes: [
          'A1B2-C3D4', 'E5F6-7890', 'AAAA-BBBB', 'CCCC-DDDD', 'EEEE-FFFF',
          '1111-2222', '3333-4444', '5555-6666', '7777-8888', '9999-0000',
        ],
      },
    }),
  })
  const user = userEvent.setup()
  render(
    <AuthContext.Provider value={unauthCtx}>
      <MemoryRouter initialEntries={['/login']}>
        <Login />
      </MemoryRouter>
    </AuthContext.Provider>,
  )
  await user.type(screen.getByLabelText('Email'), 'a@b.c')
  await user.type(screen.getByLabelText('Mot de passe'), 'passphrase-longue-ok')
  await user.click(screen.getByRole('button', { name: /se connecter/i }))
  await screen.findByText(/Scannez ce QR code/i)
  await user.type(screen.getByLabelText(/Code à 6 chiffres/i), '123456')
  await user.click(screen.getByRole('button', { name: /confirmer l.enrôlement/i }))
  return user
}

describe('Recovery codes gate', () => {
  it('affiche les 10 codes et l’avertissement', async () => {
    await walkToRecoveryCodes()
    await waitFor(() => expect(screen.getByText('A1B2-C3D4')).toBeInTheDocument())
    expect(screen.getByText(/Notez ces codes maintenant/i)).toBeInTheDocument()
    // Les 10 codes doivent être présents.
    expect(screen.getByText('9999-0000')).toBeInTheDocument()
  })

  it("'Accéder à la console' est désactivé tant que la case n'est pas cochée", async () => {
    const user = await walkToRecoveryCodes()
    await screen.findByText('A1B2-C3D4')
    const button = screen.getByRole('button', { name: /accéder à la console/i })
    expect(button).toBeDisabled()
    const checkbox = screen.getByRole('checkbox')
    await user.click(checkbox)
    expect(button).toBeEnabled()
  })
})
