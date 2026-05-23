import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { App } from '../App'

describe('App', () => {
  it('affiche le wordmark DiALEO et les 6 entrées de navigation', async () => {
    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <App />
      </MemoryRouter>,
    )

    // findBy flush les effets asynchrones (sonde /health du HealthIndicator).
    expect(await screen.findByText('DiALEO')).toBeInTheDocument()

    // Les 6 écrans cibles, dans la navigation principale (scopée pour éviter
    // la collision avec le titre de la page Dashboard rendue).
    const nav = within(screen.getByRole('navigation', { name: 'Navigation principale' }))
    expect(nav.getByText('Dashboard global')).toBeInTheDocument()
    expect(nav.getByText('Vue établissement')).toBeInTheDocument()
    expect(nav.getByText('Reports')).toBeInTheDocument()
    expect(nav.getByText('Déploiements N2')).toBeInTheDocument()
    expect(nav.getByText('Inventaire / licences')).toBeInTheDocument()
    expect(nav.getByText('Réglages console')).toBeInTheDocument()
  })
})
