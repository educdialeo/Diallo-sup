import { render, screen } from '@testing-library/react'
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

function renderLogin() {
  return render(
    <AuthContext.Provider value={unauthCtx}>
      <MemoryRouter initialEntries={['/login']}>
        <Login />
      </MemoryRouter>
    </AuthContext.Provider>,
  )
}

/**
 * Fabrique un mock fetch qui réagit en fonction de l'URL et du body
 * (pour les flux multi-appels comme login -> enroll).
 */
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

describe('Login flow', () => {
  it('aiguille vers VERIFY_TOTP quand /login renvoie totp_requis', async () => {
    mockFetchByUrl({
      '/api/auth/login': () => ({ status: 200, body: { status: 'totp_requis' } }),
    })
    const user = userEvent.setup()
    renderLogin()
    await user.type(screen.getByLabelText('Email'), 'admin@example.com')
    await user.type(screen.getByLabelText('Mot de passe'), 'passphrase-longue-ok')
    await user.click(screen.getByRole('button', { name: /se connecter/i }))
    expect(
      await screen.findByText(/Saisissez le code à 6 chiffres/i),
    ).toBeInTheDocument()
  })

  it("aiguille vers ENROLL_QR quand /login renvoie enrolement_requis", async () => {
    mockFetchByUrl({
      '/api/auth/login': () => ({ status: 200, body: { status: 'enrolement_requis' } }),
      '/api/auth/totp/enroll': () => ({
        status: 200,
        body: { otpauth_uri: 'otpauth://totp/DialSup:admin@example.com?secret=ABCDEFGHIJKLMNOP&issuer=DialSup' },
      }),
    })
    const user = userEvent.setup()
    renderLogin()
    await user.type(screen.getByLabelText('Email'), 'admin@example.com')
    await user.type(screen.getByLabelText('Mot de passe'), 'passphrase-longue-ok')
    await user.click(screen.getByRole('button', { name: /se connecter/i }))
    expect(
      await screen.findByText(/Scannez ce QR code/i),
    ).toBeInTheDocument()
    // Lien "saisie manuelle" présent.
    expect(screen.getByText(/Saisie manuelle/i)).toBeInTheDocument()
  })

  it('affiche "Identifiants invalides." sur 401 de /login', async () => {
    mockFetchByUrl({
      '/api/auth/login': () => ({ status: 401, body: { detail: 'Identifiants invalides.' } }),
    })
    const user = userEvent.setup()
    renderLogin()
    await user.type(screen.getByLabelText('Email'), 'admin@example.com')
    await user.type(screen.getByLabelText('Mot de passe'), 'mauvais')
    await user.click(screen.getByRole('button', { name: /se connecter/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Identifiants invalides.')
  })

  it('affiche un message dédié sur 423 (compte verrouillé)', async () => {
    mockFetchByUrl({
      '/api/auth/login': () => ({ status: 423, body: { detail: 'Compte temporairement verrouillé.' } }),
    })
    const user = userEvent.setup()
    renderLogin()
    await user.type(screen.getByLabelText('Email'), 'admin@example.com')
    await user.type(screen.getByLabelText('Mot de passe'), 'mauvais')
    await user.click(screen.getByRole('button', { name: /se connecter/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/verrouillé/i)
  })

  it('VERIFY_TOTP : 401 "Code invalide." reste sur l’écran TOTP avec message "Code incorrect."', async () => {
    let loginDone = false
    mockFetchByUrl({
      '/api/auth/login': () => {
        loginDone = true
        return { status: 200, body: { status: 'totp_requis' } }
      },
      '/api/auth/verify-totp': () => ({ status: 401, body: { detail: 'Code invalide.' } }),
    })
    const user = userEvent.setup()
    renderLogin()
    await user.type(screen.getByLabelText('Email'), 'a@b.c')
    await user.type(screen.getByLabelText('Mot de passe'), 'xxxxxxxxxxxx')
    await user.click(screen.getByRole('button', { name: /se connecter/i }))
    await screen.findByText(/Saisissez le code à 6 chiffres/i)
    expect(loginDone).toBe(true)

    await user.type(screen.getByLabelText(/Code à 6 chiffres/i), '000000')
    await user.click(screen.getByRole('button', { name: /vérifier/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Code incorrect.')
    // On est resté sur l'écran TOTP, pas un retour à PASSWORD.
    expect(screen.getByText(/Saisissez le code à 6 chiffres/i)).toBeInTheDocument()
  })
})
