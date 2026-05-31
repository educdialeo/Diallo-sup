/**
 * Wrapper fetch unifie : credentials inclus, gestion 401 centralisee.
 *
 * Sur 401 hors `/api/auth/*`, declenche `onUnauthorized` (positionne par
 * AuthProvider) -> purge de l'etat + redirection /login. Les 401 *sur*
 * `/api/auth/*` (mauvais code TOTP, login KO) ne purgent rien : la page
 * de login les traite localement.
 */

export type ApiResult<T = unknown> = {
  ok: boolean
  status: number
  data: T | null
}

let _onUnauthorized: () => void = () => {}

export function setUnauthorizedHandler(fn: () => void): void {
  _onUnauthorized = fn
}

export type ApiInit = Omit<RequestInit, 'credentials'> & {
  /** Si true, ne declenche pas onUnauthorized sur 401. */
  skipUnauthHandler?: boolean
}

function isAuthEndpoint(url: string): boolean {
  return url.startsWith('/api/auth/') || url === '/api/auth/me'
}

export async function api<T = unknown>(url: string, init?: ApiInit): Promise<ApiResult<T>> {
  const { skipUnauthHandler, headers, ...rest } = init ?? {}
  const finalHeaders = new Headers(headers)
  // JSON par defaut quand on envoie un body.
  if (rest.body !== undefined && !finalHeaders.has('Content-Type')) {
    finalHeaders.set('Content-Type', 'application/json')
  }
  const resp = await fetch(url, {
    ...rest,
    credentials: 'include',
    headers: finalHeaders,
  })

  let data: T | null = null
  if (resp.status !== 204) {
    try {
      data = (await resp.json()) as T
    } catch {
      data = null
    }
  }

  if (resp.status === 401 && !skipUnauthHandler && !isAuthEndpoint(url)) {
    _onUnauthorized()
  }

  return { ok: resp.ok, status: resp.status, data }
}
