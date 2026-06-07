import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'

import { Moderation } from '../pages/Moderation'

function mockOverview(body: unknown) {
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

const EMPTY = {
  totals_7d: { blacklist: 0, llamaguard: 0, systemprompt: 0, total: 0 },
  totals_30d: { blacklist: 0, llamaguard: 0, systemprompt: 0, total: 0 },
  trend_30d: {
    blacklist: Array(30).fill(0),
    llamaguard: Array(30).fill(0),
    systemprompt: Array(30).fill(0),
  },
  top_establishments: [],
  recent_incidents: [],
  generated_at: '2026-06-07T12:00:00Z',
}

const POPULATED = {
  ...EMPTY,
  totals_7d: { blacklist: 5, llamaguard: 2, systemprompt: 1, total: 8 },
  totals_30d: { blacklist: 12, llamaguard: 7, systemprompt: 3, total: 22 },
  trend_30d: {
    blacklist: [...Array(29).fill(0), 5],
    llamaguard: [...Array(25).fill(0), 1, 2, 0, 3, 1],
    systemprompt: Array(30).fill(0),
  },
  top_establishments: [
    {
      id: 5,
      name: 'Collège Renoir',
      nb_refus_blacklist: 8,
      nb_refus_llamaguard: 3,
      nb_refus_systemprompt: 1,
      total: 12,
    },
    {
      id: 2,
      name: 'Collège Voltaire',
      nb_refus_blacklist: 1,
      nb_refus_llamaguard: 3,
      nb_refus_systemprompt: 2,
      total: 6,
    },
  ],
  recent_incidents: [
    {
      received_at: '2026-06-07T11:55:00Z',
      window_start: null,
      window_end: null,
      etablissement_id: 5,
      etablissement_name: 'Collège Renoir',
      nb_refus_blacklist: 3,
      nb_refus_llamaguard: 1,
      nb_refus_systemprompt: 0,
    },
  ],
}

describe('Moderation', () => {
  it('affiche l’état vide quand totals_30d.total === 0', async () => {
    mockOverview(EMPTY)
    render(
      <MemoryRouter>
        <Moderation />
      </MemoryRouter>,
    )
    await waitFor(() =>
      expect(screen.getByText(/Aucun incident de modération/i)).toBeInTheDocument(),
    )
  })

  it("affiche les KPI 7j/30j et les rubriques quand populé", async () => {
    mockOverview(POPULATED)
    render(
      <MemoryRouter>
        <Moderation />
      </MemoryRouter>,
    )
    // KPI principal (total 30j)
    expect(await screen.findByText('22')).toBeInTheDocument()
    // Catégories : chaque label apparaît 2× (KPI + tendance), donc getAllByText.
    expect(screen.getAllByText('Blacklist').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('LlamaGuard').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('System prompt').length).toBeGreaterThanOrEqual(1)
    // Tableaux
    expect(screen.getByText('Top établissements · 30 j')).toBeInTheDocument()
    expect(screen.getByText('Derniers incidents')).toBeInTheDocument()
  })

  it('rend des liens cliquables vers les pages détail établissement', async () => {
    mockOverview(POPULATED)
    render(
      <MemoryRouter>
        <Moderation />
      </MemoryRouter>,
    )
    // "Collège Renoir" apparaît 2 fois (top + recent), chacun en <a href="/etablissement/5">
    const links = await screen.findAllByRole('link', { name: 'Collège Renoir' })
    expect(links.length).toBeGreaterThanOrEqual(2)
    for (const link of links) {
      expect(link.getAttribute('href')).toBe('/etablissement/5')
    }
  })
})
