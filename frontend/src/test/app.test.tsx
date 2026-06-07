import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import { App } from '../App'
import { AuthContext } from '../auth/context'
import type { AuthContextValue } from '../auth/context'

const authenticatedCtx: AuthContextValue = {
  state: {
    status: 'authenticated',
    user: { id: 1, email: 'admin@example.com', is_active: true, last_login_at: null },
  },
  refresh: async () => undefined,
  logout: async () => undefined,
}

describe('App', () => {
  it("rend le chrome de la console quand l'admin est authentifié", async () => {
    render(
      <AuthContext.Provider value={authenticatedCtx}>
        <MemoryRouter initialEntries={['/dashboard']}>
          <App />
        </MemoryRouter>
      </AuthContext.Provider>,
    )

    // Wordmark de la sidebar (rendu sous RequireAuth car authentifié).
    expect(await screen.findByText('DiALEO')).toBeInTheDocument()

    // Les 7 entrées de la navigation principale (Modération ajoutée en étape 3 N1).
    const nav = within(screen.getByRole('navigation', { name: 'Navigation principale' }))
    expect(nav.getByText('Dashboard global')).toBeInTheDocument()
    expect(nav.getByText('Vue établissement')).toBeInTheDocument()
    expect(nav.getByText('Reports')).toBeInTheDocument()
    expect(nav.getByText('Modération')).toBeInTheDocument()
    expect(nav.getByText('Déploiements N2')).toBeInTheDocument()
    expect(nav.getByText('Inventaire / licences')).toBeInTheDocument()
    expect(nav.getByText('Réglages console')).toBeInTheDocument()
  })
})
