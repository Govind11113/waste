import { describe, expect, it, vi } from 'vitest'
import { loadRuntimeConfig } from './runtimeConfig'

/**
 * @param {unknown} payload
 * @param {{ ok?: boolean, status?: number }} [options]
 */
const response = (payload, { ok = true, status = 200 } = {}) => ({
  ok,
  status,
  json: vi.fn().mockResolvedValue(payload),
})

describe('loadRuntimeConfig', () => {
  it('loads only same-origin public configuration without caching', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(response({
      version: '3.0.0',
      configured: true,
      clerkPublishableKey: 'pk_test_valid-development-key',
      apiBase: '/unexpected',
      backendSecret: 'must-not-be-used',
      errors: [],
    }))

    await expect(loadRuntimeConfig(fetchImpl, '')).resolves.toEqual({
      version: '3.0.0',
      configured: true,
      clerkPublishableKey: 'pk_test_valid-development-key',
      apiBase: '/api/v1',
      errors: [],
    })
    expect(fetchImpl).toHaveBeenCalledWith('/api/runtime-config', {
      cache: 'no-store',
      headers: { Accept: 'application/json' },
    })
  })

  it('uses an explicit development key only when the backend is unavailable', async () => {
    const fetchImpl = vi.fn().mockRejectedValue(new Error('offline'))

    await expect(loadRuntimeConfig(fetchImpl, 'pk_test_local-vite-key')).resolves.toMatchObject({
      configured: true,
      clerkPublishableKey: 'pk_test_local-vite-key',
      version: 'development',
    })
  })

  it('rejects a live Clerk key for localhost even if marked configured', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(response({
      configured: true,
      clerkPublishableKey: 'pk_live_not-for-localhost',
      errors: [],
    }))

    await expect(loadRuntimeConfig(fetchImpl, '')).rejects.toThrow('pk_test_')
  })

  it('rejects placeholder development keys during Vite fallback', async () => {
    const fetchImpl = vi.fn().mockRejectedValue(new Error('offline'))

    await expect(loadRuntimeConfig(fetchImpl, 'pk_test_example')).rejects.toThrow(
      'Could not load application configuration',
    )
  })

  it('surfaces backend configuration guidance', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(response({
      configured: false,
      clerkPublishableKey: null,
      errors: ['EWASTE_CLERK_PUBLISHABLE_KEY is missing'],
    }))

    await expect(loadRuntimeConfig(fetchImpl, '')).rejects.toThrow(
      'EWASTE_CLERK_PUBLISHABLE_KEY is missing',
    )
  })

  it('reports a failed configuration endpoint', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(response({}, { ok: false, status: 503 }))

    await expect(loadRuntimeConfig(fetchImpl, '')).rejects.toThrow(
      'Configuration service returned 503',
    )
  })
})
