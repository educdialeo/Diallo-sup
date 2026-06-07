import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'

import { Inventory } from '../pages/Inventory'

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

const POPULATED = {
  items: [
    {
      id: 1,
      name: 'École Saint-Pierre',
      status: 'active',
      last_seen_at: '2026-06-07T12:00:00Z',
      mac_mini_model: 'Mac mini M4',
      macos_version: '15.5',
      capacite_declaree_sieges: 30,
      formule_commerciale: 'Essentiel',
      last_changed_at: '2026-05-23T16:00:00Z',
    },
    {
      id: 2,
      name: 'École sans inventaire',
      status: 'active',
      last_seen_at: null,
      mac_mini_model: null,
      macos_version: null,
      capacite_declaree_sieges: null,
      formule_commerciale: null,
      last_changed_at: null,
    },
  ],
  totals: {
    nb_etablissements: 2,
    nb_etablissements_renseignes: 1,
    total_sieges: 30,
    par_formule: { Essentiel: 1 },
  },
  generated_at: '2026-06-07T12:00:00Z',
}

describe('Inventory', () => {
  it('affiche les totaux et le tableau parc', async () => {
    mockApi(POPULATED)
    render(
      <MemoryRouter>
        <Inventory />
      </MemoryRouter>,
    )
    expect(await screen.findByText('École Saint-Pierre')).toBeInTheDocument()
    expect(screen.getByText('Mac mini M4')).toBeInTheDocument()
    expect(screen.getByText('Essentiel')).toBeInTheDocument()
    // "30" apparaît dans le KPI (total sièges) ET dans la ligne du tableau (capacite).
    expect(screen.getAllByText('30').length).toBeGreaterThanOrEqual(1)
  })

  it('affiche un tiret pour les étabs sans inventaire reçu', async () => {
    mockApi(POPULATED)
    render(
      <MemoryRouter>
        <Inventory />
      </MemoryRouter>,
    )
    expect(await screen.findByText('École sans inventaire')).toBeInTheDocument()
    // L'établissement sans inventaire doit avoir au moins un "—" (plusieurs colonnes vides)
    expect(screen.getAllByText('—').length).toBeGreaterThanOrEqual(4)
  })

  it('rend les noms étabs comme liens vers la page détail', async () => {
    mockApi(POPULATED)
    render(
      <MemoryRouter>
        <Inventory />
      </MemoryRouter>,
    )
    const link = await screen.findByRole('link', { name: 'École Saint-Pierre' })
    expect(link.getAttribute('href')).toBe('/etablissement/1')
  })

  it("état vide quand aucun établissement", async () => {
    mockApi({
      items: [],
      totals: {
        nb_etablissements: 0,
        nb_etablissements_renseignes: 0,
        total_sieges: 0,
        par_formule: {},
      },
      generated_at: '2026-06-07T12:00:00Z',
    })
    render(
      <MemoryRouter>
        <Inventory />
      </MemoryRouter>,
    )
    await waitFor(() =>
      expect(screen.getByText(/Aucun établissement enregistré/i)).toBeInTheDocument(),
    )
  })
})
