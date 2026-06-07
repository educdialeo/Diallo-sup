import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'

import { Dashboard } from '../pages/Dashboard'

function mockFleet(items: unknown[]) {
  vi.stubGlobal(
    'fetch',
    vi.fn(() =>
      Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ items, generated_at: '2026-06-06T12:00:00Z' }),
      } as Response),
    ),
  )
}

const baseItem = {
  id: 1,
  name: 'École Saint-Pierre',
  status: 'active',
  health: 'online' as const,
  last_heartbeat_at: '2026-06-06T11:59:00Z',
  nb_eleves_connected: 42,
  nb_classes_active: 3,
  sessions_total: 100,
  sessions_7j: 30,
  nb_eleves: 200,
  duree_moyenne_min: 28.5,
  trend_14d: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14],
  incidents_recent: 0,
  is_dormant: false,
}

describe('Dashboard', () => {
  it('affiche l’état vide quand 0 établissement', async () => {
    mockFleet([])
    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>,
    )
    await waitFor(() =>
      expect(screen.getByText(/Aucun établissement enregistré/i)).toBeInTheDocument(),
    )
  })

  it('rend une tuile par établissement avec le nom et les chiffres usage', async () => {
    mockFleet([
      baseItem,
      {
        ...baseItem,
        id: 2,
        name: 'Lycée Démo',
        health: 'online',
        nb_eleves_connected: null,
        nb_classes_active: null,
        sessions_total: 0,
        sessions_7j: 0,
        nb_eleves: 0,
        duree_moyenne_min: null,
        trend_14d: Array(14).fill(0),
        is_dormant: true,
      },
    ])
    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>,
    )
    expect(await screen.findByText('École Saint-Pierre')).toBeInTheDocument()
    expect(screen.getByText('Lycée Démo')).toBeInTheDocument()
    // Le badge "Dormant" n'apparait QUE pour le second
    expect(screen.getByText('Dormant')).toBeInTheDocument()
  })

  it('affiche le badge incident quand incidents_recent > 0', async () => {
    mockFleet([{ ...baseItem, incidents_recent: 7 }])
    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>,
    )
    expect(await screen.findByText(/7 refus modération/i)).toBeInTheDocument()
  })

  it('affiche un bandeau quand tous les établissements sont silencieux', async () => {
    mockFleet([
      { ...baseItem, health: 'silent', is_dormant: false },
      { ...baseItem, id: 2, name: 'Autre', health: 'silent', is_dormant: false },
    ])
    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>,
    )
    expect(
      await screen.findByText(/Tous les établissements sont silencieux/i),
    ).toBeInTheDocument()
  })

  // Filet permanent : ce payload est la réponse RÉELLE de prod 2026-06-07
  // (établissement unique, idle/silencieux, plein de null). À ne JAMAIS retirer.
  it('rend la grille pour le payload prod réel éparse (1 étab silent, nulls)', async () => {
    mockFleet([
      {
        id: 1,
        name: 'Dialeo Pilote 001',
        status: 'active',
        health: 'silent',
        last_heartbeat_at: '2026-06-01T17:01:21.050934', // sans Z (SQLite)
        nb_eleves_connected: null,
        nb_classes_active: null,
        sessions_total: 0,
        sessions_7j: 0,
        nb_eleves: 0,
        duree_moyenne_min: null,
        trend_14d: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        incidents_recent: 0,
        is_dormant: false,
      },
    ])
    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>,
    )
    expect(await screen.findByText('Dialeo Pilote 001')).toBeInTheDocument()
    expect(screen.queryByText(/Erreur de chargement/i)).not.toBeInTheDocument()
  })
})
