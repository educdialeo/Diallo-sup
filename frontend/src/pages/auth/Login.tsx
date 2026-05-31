/**
 * Page d'authentification — state machine interne (1 seule route /login).
 *
 *   PASSWORD                       (email + mot de passe)
 *     │ POST /api/auth/login
 *     │  200 status="totp_requis"        ──> VERIFY_TOTP
 *     │  200 status="enrolement_requis"  ──> ENROLL_QR
 *     │  401 / 423 / 503                  ──> message d'erreur
 *     ▼
 *   ENROLL_QR  (1er enrolement)
 *     │ POST /api/auth/totp/confirm
 *     ▼
 *   SHOW_RECOVERY_CODES (gate "j'ai sauvegardé")
 *     ▼
 *   /dashboard
 *
 *   VERIFY_TOTP (re-login d'un user deja enrole)
 *     │ POST /api/auth/verify-totp
 *     ▼
 *   /dashboard
 *
 * Si le cookie pre_auth expire (5 min) ou disparait en cours de flux,
 * un 401 "Authentification requise." ramene proprement a PASSWORD.
 *
 * Registre : vouvoiement partout.
 */

import { useCallback, useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import QRCode from 'react-qr-code'

import { useAuth } from '../../auth/useAuth'
import { api } from '../../lib/api'

type Step = 'PASSWORD' | 'VERIFY_TOTP' | 'ENROLL_QR' | 'SHOW_RECOVERY_CODES'

interface LocationState {
  from?: { pathname?: string }
}

function extractSecret(otpauthUri: string): string {
  const m = otpauthUri.match(/[?&]secret=([A-Z2-7]+)/)
  return m ? m[1] : ''
}

function isPreauthExpired(detail: unknown): boolean {
  // /verify-totp et /confirm renvoient :
  //   - "Code invalide." si le code est faux
  //   - "Authentification requise." / "Session invalide ou expirée." sinon
  return typeof detail === 'string' && !detail.toLowerCase().includes('code')
}

// =============================================================================

export function Login() {
  const { state: authState, refresh } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as LocationState | null)?.from?.pathname ?? '/dashboard'

  // Deja authentifie ? On bascule vers la console.
  useEffect(() => {
    if (authState.status === 'authenticated') {
      navigate(from, { replace: true })
    }
  }, [authState.status, from, navigate])

  const [step, setStep] = useState<Step>('PASSWORD')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  // Inputs.
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [code, setCode] = useState('')
  const [useRecovery, setUseRecovery] = useState(false)

  // Enroll.
  const [otpauthUri, setOtpauthUri] = useState<string | null>(null)
  const [manualVisible, setManualVisible] = useState(false)

  // Recovery codes.
  const [recoveryCodes, setRecoveryCodes] = useState<string[]>([])
  const [codesAcked, setCodesAcked] = useState(false)

  const resetToPassword = useCallback((msg: string | null = null) => {
    setStep('PASSWORD')
    setError(msg)
    setCode('')
    setUseRecovery(false)
    setOtpauthUri(null)
    setRecoveryCodes([])
    setCodesAcked(false)
  }, [])

  // --- Étape 1 : mot de passe ---------------------------------------------
  const submitPassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setBusy(true)
    const r = await api<{ status: string }>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
    setBusy(false)
    if (r.status === 200 && r.data?.status === 'totp_requis') {
      setStep('VERIFY_TOTP')
      return
    }
    if (r.status === 200 && r.data?.status === 'enrolement_requis') {
      // Lance immediatement /enroll pour recuperer l'URI.
      const e2 = await api<{ otpauth_uri: string }>('/api/auth/totp/enroll', {
        method: 'POST',
      })
      if (e2.status === 200 && e2.data?.otpauth_uri) {
        setOtpauthUri(e2.data.otpauth_uri)
        setStep('ENROLL_QR')
      } else {
        setError("Échec de l’initialisation de l’enrôlement. Veuillez réessayer.")
      }
      return
    }
    if (r.status === 423) {
      setError('Compte temporairement verrouillé. Veuillez réessayer plus tard.')
      return
    }
    if (r.status === 503) {
      setError("Service d’authentification indisponible.")
      return
    }
    setError('Identifiants invalides.')
  }

  // --- Étape 2a : verify-totp ---------------------------------------------
  const submitVerifyTotp = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setBusy(true)
    const r = await api<{ status: string }>('/api/auth/verify-totp', {
      method: 'POST',
      body: JSON.stringify({ code }),
    })
    setBusy(false)
    if (r.status === 200) {
      await refresh()
      navigate(from, { replace: true })
      return
    }
    if (r.status === 423) {
      setError('Compte temporairement verrouillé. Veuillez réessayer plus tard.')
      return
    }
    if (r.status === 401) {
      const detail = (r.data as { detail?: unknown } | null)?.detail
      if (isPreauthExpired(detail)) {
        resetToPassword('Session expirée. Veuillez recommencer.')
      } else {
        setError('Code incorrect.')
      }
      return
    }
    setError("Erreur. Veuillez réessayer.")
  }

  // --- Étape 2b : confirm (enrôlement) ------------------------------------
  const submitConfirm = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setBusy(true)
    const r = await api<{ recovery_codes: string[] }>('/api/auth/totp/confirm', {
      method: 'POST',
      body: JSON.stringify({ code }),
    })
    setBusy(false)
    if (r.status === 200 && r.data?.recovery_codes?.length) {
      setRecoveryCodes(r.data.recovery_codes)
      setStep('SHOW_RECOVERY_CODES')
      setCode('')
      return
    }
    if (r.status === 423) {
      setError('Compte temporairement verrouillé. Veuillez réessayer plus tard.')
      return
    }
    if (r.status === 401) {
      const detail = (r.data as { detail?: unknown } | null)?.detail
      if (isPreauthExpired(detail)) {
        resetToPassword('Session expirée. Veuillez recommencer.')
      } else {
        setError('Code incorrect.')
      }
      return
    }
    setError("Erreur. Veuillez réessayer.")
  }

  // --- Gate codes de recup ------------------------------------------------
  const enterConsole = async () => {
    await refresh()
    navigate(from, { replace: true })
  }
  const copyCodes = async () => {
    await navigator.clipboard.writeText(recoveryCodes.join('\n'))
  }
  const downloadCodes = () => {
    const blob = new Blob(
      [
        'Codes de récupération Diallo-sup\n',
        'À conserver hors-ligne. Chacun utilisable UNE seule fois.\n\n',
        recoveryCodes.join('\n') + '\n',
      ],
      { type: 'text/plain' },
    )
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'diallosup-recovery-codes.txt'
    a.click()
    URL.revokeObjectURL(url)
  }

  // =========================================================================
  // Rendu
  // =========================================================================
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-12">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <Header />

        {error && (
          <div
            role="alert"
            className="mb-4 rounded-md border border-brique-500/30 bg-brique-100 px-3 py-2 text-sm text-brique-500"
          >
            {error}
          </div>
        )}

        {step === 'PASSWORD' && (
          <form onSubmit={submitPassword} className="space-y-4">
            <Field label="Email">
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className={inputClass}
                autoComplete="username"
              />
            </Field>
            <Field label="Mot de passe">
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className={inputClass}
                autoComplete="current-password"
              />
            </Field>
            <PrimaryButton disabled={busy || !email || !password}>
              {busy ? 'Connexion…' : 'Se connecter'}
            </PrimaryButton>
          </form>
        )}

        {step === 'VERIFY_TOTP' && (
          <form onSubmit={submitVerifyTotp} className="space-y-4">
            <p className="text-sm text-slate-600">
              Saisissez le code à 6 chiffres de votre application d’authentification.
            </p>
            <Field label={useRecovery ? 'Code de récupération' : 'Code à 6 chiffres'}>
              <input
                type="text"
                required
                inputMode={useRecovery ? 'text' : 'numeric'}
                autoComplete="one-time-code"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                className={`${inputClass} ${useRecovery ? '' : 'tracking-[0.5em] text-center font-mono text-lg'}`}
                placeholder={useRecovery ? 'XXXX-XXXX' : '••••••'}
                maxLength={useRecovery ? 9 : 6}
              />
            </Field>
            <PrimaryButton disabled={busy || !code}>
              {busy ? 'Vérification…' : 'Vérifier'}
            </PrimaryButton>
            <button
              type="button"
              onClick={() => {
                setUseRecovery((v) => !v)
                setCode('')
              }}
              className="block w-full text-center text-xs text-craie-600 underline-offset-2 hover:underline"
            >
              {useRecovery
                ? '← Utiliser le code de l’application'
                : 'Utiliser un code de récupération à la place'}
            </button>
          </form>
        )}

        {step === 'ENROLL_QR' && otpauthUri && (
          <form onSubmit={submitConfirm} className="space-y-4">
            <p className="text-sm text-slate-600">
              Scannez ce QR code avec votre application d’authentification (Google
              Authenticator, Microsoft Authenticator, Authy…), puis saisissez le code
              à 6 chiffres qu’elle affiche.
            </p>
            <div className="mx-auto flex h-48 w-48 items-center justify-center rounded-md border border-slate-200 bg-white p-3">
              <QRCode value={otpauthUri} size={168} />
            </div>
            <button
              type="button"
              onClick={() => setManualVisible((v) => !v)}
              className="block w-full text-center text-xs text-craie-600 hover:underline"
            >
              {manualVisible ? '← Cacher la saisie manuelle' : 'Impossible de scanner ? Saisie manuelle'}
            </button>
            {manualVisible && (
              <div className="rounded-md bg-slate-50 p-3 text-xs text-slate-600">
                <p className="mb-1 font-medium text-slate-700">Saisie manuelle :</p>
                <dl className="space-y-1">
                  <Row k="Compte">{decodeURIComponent(otpauthUri.split('/totp/')[1].split('?')[0])}</Row>
                  <Row k="Émetteur">DialSup</Row>
                  <Row k="Type">TOTP</Row>
                  <Row k="Algorithme">SHA-1</Row>
                  <Row k="Chiffres">6</Row>
                  <Row k="Période">30 s</Row>
                  <Row k="Clé">
                    <code className="break-all font-mono">{extractSecret(otpauthUri)}</code>
                  </Row>
                </dl>
              </div>
            )}
            <Field label="Code à 6 chiffres">
              <input
                type="text"
                required
                inputMode="numeric"
                autoComplete="one-time-code"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                className={`${inputClass} tracking-[0.5em] text-center font-mono text-lg`}
                placeholder="••••••"
                maxLength={6}
              />
            </Field>
            <PrimaryButton disabled={busy || code.length < 6}>
              {busy ? 'Confirmation…' : 'Confirmer l’enrôlement'}
            </PrimaryButton>
          </form>
        )}

        {step === 'SHOW_RECOVERY_CODES' && (
          <div className="space-y-4">
            <div className="rounded-md border-2 border-chaleur-500/40 bg-chaleur-100 p-3 text-sm text-chaleur-500">
              <p className="font-semibold">⚠️ Notez ces codes maintenant.</p>
              <p className="mt-1 text-chaleur-500/90">
                Ils ne seront <strong>plus jamais</strong> affichés. En cas de perte du
                téléphone <em>et</em> de tous les codes, le ré-enrôlement TOTP devra être
                fait en ligne de commande sur le serveur.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-2 rounded-md bg-slate-50 p-3 text-center font-mono text-sm text-slate-800">
              {recoveryCodes.map((c) => (
                <code key={c}>{c}</code>
              ))}
            </div>
            <div className="flex gap-2">
              <SecondaryButton onClick={copyCodes}>Copier</SecondaryButton>
              <SecondaryButton onClick={downloadCodes}>Télécharger .txt</SecondaryButton>
            </div>
            <label className="flex items-start gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={codesAcked}
                onChange={(e) => setCodesAcked(e.target.checked)}
                className="mt-0.5 h-4 w-4 accent-craie-400"
              />
              <span>J’ai sauvegardé mes codes de récupération en lieu sûr.</span>
            </label>
            <PrimaryButton onClick={enterConsole} disabled={!codesAcked}>
              Accéder à la console
            </PrimaryButton>
          </div>
        )}
      </div>
    </div>
  )
}

// =============================================================================
// Petits primitives charte Dialeo (inlined pour ne pas exploser le nb de fichiers)
// =============================================================================

function Header() {
  return (
    <div className="mb-6 flex items-center gap-2">
      <span className="flex h-8 w-8 items-center justify-center rounded-md bg-craie-400 text-base font-bold text-white">
        D
      </span>
      <span className="text-lg font-bold tracking-tight text-slate-800">DiALEO</span>
      <span className="ml-1 text-xs font-medium text-slate-400">supervision</span>
    </div>
  )
}

const inputClass =
  'block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 ' +
  'placeholder-slate-400 focus:border-craie-400 focus:outline-none focus:ring-2 focus:ring-craie-400/40'

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-slate-600">{label}</span>
      {children}
    </label>
  )
}

function PrimaryButton({
  children,
  disabled,
  onClick,
}: {
  children: React.ReactNode
  disabled?: boolean
  onClick?: () => void
}) {
  return (
    <button
      type={onClick ? 'button' : 'submit'}
      disabled={disabled}
      onClick={onClick}
      className="w-full rounded-md bg-craie-400 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-craie-500 disabled:cursor-not-allowed disabled:opacity-50"
    >
      {children}
    </button>
  )
}

function SecondaryButton({
  children,
  onClick,
}: {
  children: React.ReactNode
  onClick?: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex-1 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
    >
      {children}
    </button>
  )
}

function Row({ k, children }: { k: string; children: React.ReactNode }) {
  return (
    <div className="flex gap-2">
      <dt className="w-20 shrink-0 text-slate-500">{k}</dt>
      <dd className="flex-1 text-slate-700">{children}</dd>
    </div>
  )
}
