const BUILD_TIME_DEVELOPMENT_KEY = import.meta.env.DEV
  ? String(import.meta.env.VITE_CLERK_PUBLISHABLE_KEY || '').trim()
  : ''

/** @param {string} key */
function isLocalhostDevelopmentKey(key) {
  const normalized = key.toLowerCase()
  return key.startsWith('pk_test_')
    && !['example', 'your-clerk', 'replace-with'].some((token) => normalized.includes(token))
}

/**
 * @typedef {{
 *   version: string,
 *   configured: boolean,
 *   clerkPublishableKey: string | null,
 *   apiBase: string,
 *   errors: string[],
 * }} RuntimeConfig
 */

/**
 * Load safe browser configuration from the same-origin backend.
 * Production never falls back to Vite build-time values, so one Windows build
 * can be configured after extraction without exposing backend secrets.
 *
 * @param {typeof fetch} [fetchImpl]
 * @param {string} [developmentKey]
 * @returns {Promise<RuntimeConfig>}
 */
export async function loadRuntimeConfig(fetchImpl = fetch, developmentKey = BUILD_TIME_DEVELOPMENT_KEY) {
  /** @type {Partial<RuntimeConfig> | null} */
  let payload = null
  try {
    const response = await fetchImpl('/api/runtime-config', {
      cache: 'no-store',
      headers: { Accept: 'application/json' },
    })
    if (!response.ok) {
      throw new Error(`Configuration service returned ${response.status}`)
    }
    payload = await response.json()
  } catch (error) {
    if (isLocalhostDevelopmentKey(developmentKey)) {
      return {
        version: 'development',
        configured: true,
        clerkPublishableKey: developmentKey,
        apiBase: '/api/v1',
        errors: [],
      }
    }
    const message = error instanceof Error ? error.message : 'Configuration service is unavailable'
    throw new Error(`Could not load application configuration: ${message}`)
  }

  const errors = Array.isArray(payload?.errors)
    ? payload.errors.filter((value) => typeof value === 'string')
    : []
  const runtimeKey = typeof payload?.clerkPublishableKey === 'string'
    ? payload.clerkPublishableKey.trim()
    : ''
  const key = runtimeKey || developmentKey
  const configured = Boolean(payload?.configured && isLocalhostDevelopmentKey(key))

  if (!configured) {
    const reasons = errors.length
      ? errors.join('; ')
      : 'A valid Clerk development publishable key (pk_test_) is required.'
    throw new Error(reasons)
  }

  return {
    version: typeof payload?.version === 'string' ? payload.version : 'unknown',
    configured: true,
    clerkPublishableKey: key,
    apiBase: '/api/v1',
    errors: [],
  }
}
