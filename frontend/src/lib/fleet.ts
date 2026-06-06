/** Types miroirs de app/schemas/fleet.py (chantier N1 fleet view). */

export type Health = 'online' | 'degraded' | 'silent'

export interface FleetItem {
  id: number
  name: string
  status: string
  health: Health
  last_heartbeat_at: string | null
  nb_eleves_connected: number | null
  nb_classes_active: number | null
  sessions_total: number
  sessions_7j: number
  nb_eleves: number
  duree_moyenne_min: number | null
  trend_14d: number[]
  incidents_recent: number
  is_dormant: boolean
}

export interface FleetResponse {
  items: FleetItem[]
  generated_at: string
}

// ============================================================================
// Detail — GET /api/fleet/{id}
// ============================================================================

export interface MachineHealth {
  last_seen_at: string | null
  status_global: string | null
  uptime_seconds: number | null
  last_boot: string | null
  cpu_percent: number | null
  ram_used_mb: number | null
  ram_total_mb: number | null
  disk_used_gb: number | null
  disk_total_gb: number | null
  temperature_celsius: number | null
  mac_serial: string | null
}

export interface OllamaSnapshot {
  last_seen_at: string | null
  models_loaded: string[]
  ping_latency_ms: number | null
  ram_used_mb: number | null
  last_inference_at: string | null
}

export interface DialeoSnapshot {
  last_seen_at: string | null
  version: string | null
  uvicorn_status: string | null
  last_deploy_at: string | null
  modes_active: string[]
}

export interface DaemonSnapshot {
  last_seen_at: string | null
  uvicorn_status: string | null
  response_time_ms: number | null
  http_status: number | null
  consecutive_failures: number | null
  daemon_uptime_seconds: number | null
  last_success_iso: string | null
}

export interface IncidentDetail {
  received_at: string
  window_start: string | null
  window_end: string | null
  nb_refus_blacklist: number
  nb_refus_llamaguard: number
  nb_refus_systemprompt: number
}

export interface UsageDay {
  date: string  // YYYY-MM-DD
  nb_sessions: number
  nb_eleves: number
  duree_moyenne_min: number | null
}

export interface EstablishmentDetail {
  id: number
  name: string
  status: string
  created_at: string
  health: Health
  last_heartbeat_at: string | null
  nb_eleves_connected: number | null
  nb_classes_active: number | null
  machine: MachineHealth
  ollama: OllamaSnapshot
  dialeo: DialeoSnapshot
  daemon: DaemonSnapshot
  incidents_recent: IncidentDetail[]
  usage_history: UsageDay[]
  generated_at: string
}
