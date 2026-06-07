/** Types miroirs de app/schemas/reports.py (chantier N1 étape 4).
 *
 * ⚠️ AUCUN champ ne porte de contenu utilisateur (question/reponse/note) —
 * la défense en profondeur est faite côté backend (cf service reports).
 */

export interface ReportsTotals {
  total: number
  by_niveau: Record<string, number>
  by_mode: Record<string, number>
}

export interface TopReportingEstablishment {
  id: number
  name: string
  nb_reports: number
}

export interface RecentReportSummary {
  received_at: string
  date_jour: string  // YYYY-MM-DD
  etablissement_id: number
  etablissement_name: string
  niveau_scolaire: string[]
  mode_pedagogique: string
  // PAS de question, PAS de reponse, PAS de note_enseignant.
}

export interface ReportsOverview {
  totals_7d: ReportsTotals
  totals_30d: ReportsTotals
  top_establishments: TopReportingEstablishment[]
  recent: RecentReportSummary[]
  generated_at: string
}
