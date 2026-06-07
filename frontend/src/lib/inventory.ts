/** Types miroirs de app/schemas/inventory.py (chantier N1 étape 4). */

export interface EstablishmentInventory {
  id: number
  name: string
  status: string
  last_seen_at: string | null
  mac_mini_model: string | null
  macos_version: string | null
  capacite_declaree_sieges: number | null
  formule_commerciale: string | null
  last_changed_at: string | null
}

export interface InventoryTotals {
  nb_etablissements: number
  nb_etablissements_renseignes: number
  total_sieges: number
  par_formule: Record<string, number>
}

export interface InventoryOverview {
  items: EstablishmentInventory[]
  totals: InventoryTotals
  generated_at: string
}
