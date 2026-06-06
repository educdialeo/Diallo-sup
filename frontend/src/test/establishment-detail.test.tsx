import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { vi } from 'vitest'

import { EstablishmentDetail } from '../pages/EstablishmentDetail'

function mockFetch(status: number, body: unknown) {
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

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/etablissement/:id" element={<EstablishmentDetail />} />
      </Routes>
    </MemoryRouter>,
  )
}

const recent = new Date(Date.now() - 60_000).toISOString()
const veryOld = new Date(Date.now() - 7 * 86400_000).toISOString()

const baseDetail = {
  id: 1,
  name: 'École Saint-Pierre',
  status: 'active',
  created_at: '2026-05-23T16:27:14Z',
  health: 'online',
  last_heartbeat_at: recent,
  nb_eleves_connected: 42,
  nb_classes_active: 3,
  machine: {
    last_seen_at: recent,
    status_global: 'up', uptime_seconds: 952247, last_boot: null,
    cpu_percent: 12.5, ram_used_mb: 8000, ram_total_mb: 24576,
    disk_used_gb: 120.0, disk_total_gb: 460.43,
    temperature_celsius: null, mac_serial: 'C02XYZSEED',
  },
  ollama: {
    last_seen_at: null, models_loaded: [],
    ping_latency_ms: null, ram_used_mb: null, last_inference_at: null,
  },
  dialeo: {
    last_seen_at: recent, version: 'v0.10.1-test',
    uvicorn_status: 'up', last_deploy_at: null,
    modes_active: ['aide_redaction'],
  },
  daemon: {
    last_seen_at: veryOld,  // périmé -> doit afficher le badge
    uvicorn_status: 'ok', response_time_ms: 6, http_status: 200,
    consecutive_failures: 0, daemon_uptime_seconds: 695690,
    last_success_iso: veryOld,
  },
  incidents_recent: [
    {
      received_at: '2026-06-05T08:00:00Z',
      window_start: null, window_end: null,
      nb_refus_blacklist: 3, nb_refus_llamaguard: 1, nb_refus_systemprompt: 0,
    },
  ],
  usage_history: Array.from({ length: 30 }, (_, i) => ({
    date: `2026-06-${String(i + 1).padStart(2, '0')}`,
    nb_sessions: i % 5,
    nb_eleves: i * 3,
    duree_moyenne_min: i ? 28 + (i % 4) : null,
  })),
  generated_at: new Date().toISOString(),
}

describe('EstablishmentDetail', () => {
  it('affiche le nom, le CPU, la version Dialeo et un incident', async () => {
    mockFetch(200, baseDetail)
    renderAt('/etablissement/1')

    expect(await screen.findByText('École Saint-Pierre')).toBeInTheDocument()
    expect(screen.getByText('12.5 %')).toBeInTheDocument()
    expect(screen.getByText('v0.10.1-test')).toBeInTheDocument()
    // L'incident apparait dans le tableau
    expect(screen.getByText(/Incidents modération/i)).toBeInTheDocument()
  })

  it('marque visuellement le panneau périmé (daemon vu il y a 7 jours)', async () => {
    mockFetch(200, baseDetail)
    renderAt('/etablissement/1')
    // Au moins un badge "périmé" doit apparaitre (pour le panneau daemon)
    const stale = await screen.findAllByText(/périmé/i)
    expect(stale.length).toBeGreaterThanOrEqual(1)
  })

  it('affiche "Non rapporté" pour le panneau ollama (last_seen_at null)', async () => {
    mockFetch(200, baseDetail)
    renderAt('/etablissement/1')
    expect(await screen.findByText('Non rapporté.')).toBeInTheDocument()
  })

  it('affiche "Établissement introuvable" sur 404', async () => {
    mockFetch(404, { detail: 'Établissement introuvable.' })
    renderAt('/etablissement/9999')
    await waitFor(() =>
      expect(screen.getByText(/introuvable/i)).toBeInTheDocument(),
    )
  })
})
