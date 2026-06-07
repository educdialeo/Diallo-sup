/** Types miroirs de app/schemas/incidents.py (chantier N1 étape 3). */

export interface IncidentTotals {
  blacklist: number
  llamaguard: number
  systemprompt: number
  total: number
}

export interface TrendByCategory {
  blacklist: number[]
  llamaguard: number[]
  systemprompt: number[]
}

export interface EstablishmentIncidentsSummary {
  id: number
  name: string
  nb_refus_blacklist: number
  nb_refus_llamaguard: number
  nb_refus_systemprompt: number
  total: number
}

export interface RecentIncidentItem {
  received_at: string
  window_start: string | null
  window_end: string | null
  etablissement_id: number
  etablissement_name: string
  nb_refus_blacklist: number
  nb_refus_llamaguard: number
  nb_refus_systemprompt: number
}

export interface IncidentsOverview {
  totals_7d: IncidentTotals
  totals_30d: IncidentTotals
  trend_30d: TrendByCategory
  top_establishments: EstablishmentIncidentsSummary[]
  recent_incidents: RecentIncidentItem[]
  generated_at: string
}
