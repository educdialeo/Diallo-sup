import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'

import { Reports } from '../pages/Reports'

const _SENSITIVE = 'SHOULD_NEVER_APPEAR_IN_UI'

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

const EMPTY = {
  totals_7d: { total: 0, by_niveau: {}, by_mode: {} },
  totals_30d: { total: 0, by_niveau: {}, by_mode: {} },
  top_establishments: [],
  recent: [],
  generated_at: '2026-06-07T12:00:00Z',
}

const POPULATED = {
  totals_7d: { total: 4, by_niveau: { CM1: 2, '6e': 1 }, by_mode: { dialogue: 3, quiz: 1 } },
  totals_30d: { total: 9, by_niveau: { CM1: 4, CM2: 2, '6e': 2, '5e': 1 }, by_mode: { dialogue: 6, quiz: 2, explication: 1 } },
  top_establishments: [
    { id: 5, name: 'Collège Renoir', nb_reports: 5 },
    { id: 1, name: 'École Saint-Pierre', nb_reports: 3 },
  ],
  recent: [
    {
      received_at: '2026-06-07T11:55:00Z',
      date_jour: '2026-06-07',
      etablissement_id: 5,
      etablissement_name: 'Collège Renoir',
      niveau_scolaire: ['3e'],
      mode_pedagogique: 'dialogue',
    },
  ],
  generated_at: '2026-06-07T12:00:00Z',
}

describe('Reports', () => {
  it('affiche le bandeau RGPD systématiquement', async () => {
    mockApi(EMPTY)
    render(
      <MemoryRouter>
        <Reports />
      </MemoryRouter>,
    )
    // Le texte est cassé par un <strong>, on cherche dans le textContent agrégé.
    const banner = await screen.findByRole('note')
    expect(banner.textContent).toMatch(/contenu détaillé/i)
    expect(banner.textContent).toMatch(/pas visualisable/i)
  })

  it("affiche l'état vide quand 0 report sur 30 j", async () => {
    mockApi(EMPTY)
    render(
      <MemoryRouter>
        <Reports />
      </MemoryRouter>,
    )
    await waitFor(() =>
      expect(screen.getByText(/Aucun rapport sur les 30 derniers jours/i)).toBeInTheDocument(),
    )
  })

  it('affiche KPI, ventilations et top', async () => {
    mockApi(POPULATED)
    render(
      <MemoryRouter>
        <Reports />
      </MemoryRouter>,
    )
    // KPI total 30j
    expect(await screen.findByText('9')).toBeInTheDocument()
    // Niveaux apparaissent dans les ventilations (CM1 unique)
    expect(screen.getByText('CM1')).toBeInTheDocument()
    // "dialogue" et "Collège Renoir" apparaissent plusieurs fois (ventilation +
    // ligne recent / top + recent), donc getAllByText.
    expect(screen.getAllByText('dialogue').length).toBeGreaterThanOrEqual(1)
    const renoirLinks = await screen.findAllByRole('link', { name: 'Collège Renoir' })
    expect(renoirLinks.length).toBeGreaterThanOrEqual(1)
    expect(renoirLinks[0].getAttribute('href')).toBe('/etablissement/5')
  })

  // ⚠️ Défense en profondeur : même si une réponse polluée arrivait, l'UI ne
  // chercherait jamais à afficher question/reponse/note (ces clés ne sont
  // pas typées dans RecentReportSummary). Test : injecter une réponse qui
  // CONTIENT par erreur des champs sensibles, vérifier qu'ils n'apparaissent
  // pas à l'écran.
  it("ne rend jamais de contenu sensible même si l'API en renvoyait par erreur", async () => {
    const polluted = {
      ...POPULATED,
      recent: [
        {
          ...POPULATED.recent[0],
          // Champs sensibles ajoutés "par erreur" -> ne doivent pas être rendus.
          question: _SENSITIVE,
          reponse: _SENSITIVE,
          note_enseignant: _SENSITIVE,
        },
      ],
    }
    mockApi(polluted)
    render(
      <MemoryRouter>
        <Reports />
      </MemoryRouter>,
    )
    // Attente d'un élément populé (peu importe lequel — Collège Renoir apparaît
    // 2x : top + recent — on utilise findAllByText).
    await screen.findAllByText('Collège Renoir')
    expect(screen.queryByText(_SENSITIVE)).not.toBeInTheDocument()
  })
})
