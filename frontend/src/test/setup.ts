import '@testing-library/jest-dom'
import { vi } from 'vitest'

// Stub de fetch : evite tout appel reseau reel dans les tests (la sonde /health
// du HealthIndicator est ainsi neutralisee proprement).
vi.stubGlobal(
  'fetch',
  vi.fn(() =>
    Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ status: 'ok', service: 'Diallo-sup console' }),
    } as Response),
  ),
)
