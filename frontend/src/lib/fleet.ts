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
