/**
 * Page Réglages (chantier N1 étape 4).
 *
 * Source : `GET /api/settings/overview`. Lecture seule. Aucune valeur de
 * secret n'est exposée — uniquement des booléens `*_configured`.
 *
 * Modification : passe par `.env` sur DialSup + redémarrage launchd (cf
 * docs/RESILIENCE.md). Aucune mutation depuis cette UI en v1.
 */

import { usePolling } from '../hooks/usePolling'
import type { SettingsOverview } from '../lib/settings'
import { timeAgoShort } from '../lib/staleness'

export function Settings() {
  const { data, loading, error } = usePolling<SettingsOverview>(
    '/api/settings/overview',
    30_000,
  )

  return (
    <div className="mx-auto max-w-4xl">
      <header>
        <h1 className="text-2xl font-semibold text-slate-800">Réglages console</h1>
        <p className="mt-1 text-sm text-slate-500">
          Configuration runtime — lecture seule. Toute modification passe par le
          fichier <code className="rounded bg-slate-100 px-1">.env</code> sur DialSup
          puis un redémarrage du service launchd.
        </p>
      </header>

      <Body data={data} loading={loading} error={error} />
    </div>
  )
}

function Body({
  data,
  loading,
  error,
}: {
  data: SettingsOverview | null
  loading: boolean
  error: string | null
}) {
  if (loading && !data) {
    return (
      <div className="mt-8 text-center text-sm text-slate-500" role="status">
        Chargement…
      </div>
    )
  }
  if (error) {
    return (
      <div
        role="alert"
        className="mt-8 rounded-md border border-brique-500/30 bg-brique-100 px-3 py-2 text-sm text-brique-500"
      >
        Erreur de chargement ({error}).
      </div>
    )
  }
  if (!data) return null

  return (
    <div className="mt-6 space-y-4">
      <Section title="Service">
        <Row label="Application" value={data.app_name} />
        <Row label="Version package" value={data.version} />
        <Row label="Hôte d'écoute" value={`${data.host} : ${data.port}`} />
        <Row label="Niveau de log" value={data.log_level} />
      </Section>

      <Section title="Auth / session">
        <Row label="Durée de session" value={`${data.session_ttl_hours} h`} />
        <Row label="TTL pre_auth (étape mdp)" value={`${data.preauth_ttl_minutes} min`} />
        <Row
          label="Cookie Secure"
          value={data.session_cookie_secure ? 'oui (HTTPS)' : 'non (HTTP local)'}
        />
      </Section>

      <Section title="Anti-brute-force">
        <Row label="Échecs max avant verrouillage" value={String(data.login_max_attempts)} />
        <Row label="Durée du verrouillage" value={`${data.login_lockout_minutes} min`} />
      </Section>

      <Section title="Secrets (statut uniquement, jamais la valeur)">
        <Row
          label="JWT_SECRET"
          value={data.jwt_secret_configured ? 'configuré ✅' : 'manquant ❌'}
        />
        <Row
          label="TOTP_AT_REST_KEY"
          value={data.totp_at_rest_key_configured ? 'configuré ✅' : 'manquant ❌'}
        />
      </Section>

      <p className="text-right text-[11px] text-slate-400">
        Snapshot pris {timeAgoShort(data.generated_at)}
      </p>
    </div>
  )
}

function Section({
  title,
  children,
}: {
  title: string
  children: React.ReactNode
}) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="text-sm font-semibold text-slate-800">{title}</h2>
      <dl className="mt-3 space-y-1.5 text-xs">{children}</dl>
    </section>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <dt className="text-slate-500">{label}</dt>
      <dd className="font-medium text-slate-800">{value}</dd>
    </div>
  )
}
