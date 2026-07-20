import { useCallback } from 'react'
import { useAuth } from '@clerk/clerk-react'
import { retryFetch } from './apiUtils'

/**
 * Returns an authenticated `fetch` bound to the current Clerk session.
 *
 * Every request to `/api/v1/*` now carries `Authorization: Bearer <jwt>`,
 * which the backend validates against Clerk's JWKS. If the session token
 * can't be obtained (signed out), requests are sent unauthenticated and the
 * backend will respond 401 — callers should handle that like any network error.
 *
 * Usage:
 *   const apiFetch = useApiFetch()
 *   const res = await apiFetch('/api/v1/classifier/scan', { method: 'POST', body })
 *
 * Accepts the same arguments as `window.fetch`. Also accepts a `URL` object
 * as the first argument (History.jsx builds query-string URLs that way) — it
 * is stringified before the call.
 */
export function useApiFetch() {
  const { getToken } = useAuth()

  return useCallback(
    /**
     * @param {RequestInfo | URL} input
     * @param {RequestInit} [init]
     * @returns {Promise<Response>}
     */
    async (input, init = {}) => {
      const token = await getToken()
      const headers = new Headers(init.headers)
      if (token) headers.set('Authorization', `Bearer ${token}`)
      return retryFetch(input, { ...init, headers })
    },
    [getToken]
  )
}
