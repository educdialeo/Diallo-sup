/** Types miroirs de app/schemas/settings.py (chantier N1 étape 4).
 *
 * Lecture seule — aucune valeur secrète, seuls des booléens `*_configured`.
 */

export interface SettingsOverview {
  app_name: string
  version: string
  host: string
  port: number
  log_level: string

  session_ttl_hours: number
  preauth_ttl_minutes: number
  session_cookie_secure: boolean

  login_max_attempts: number
  login_lockout_minutes: number

  jwt_secret_configured: boolean
  totp_at_rest_key_configured: boolean

  generated_at: string
}
