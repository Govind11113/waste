/**
 * API utilities with idempotent retry logic, rate-limit tracking, image
 * validation, and cancellable upload progress.
 */

const MAX_FILE_SIZE_MB = 10
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
const SUPPORTED_IMAGE_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp'])
const MIN_DIMENSION_PX = 160
const MAX_ASPECT_RATIO = 10
const IDEMPOTENT_METHODS = new Set(['GET', 'HEAD', 'OPTIONS', 'PUT', 'DELETE'])

/**
 * @typedef {{ width: number, height: number }} ImageDimensions
 * @typedef {{ valid: boolean, error?: string, dimensions?: ImageDimensions }} ImageValidation
 */

/**
 * Validate an image file before upload.
 * @param {File | null | undefined} file
 * @returns {Promise<ImageValidation>}
 */
export async function validateImageFile(file) {
  if (!file) return { valid: false, error: 'No file selected' }
  if (!SUPPORTED_IMAGE_TYPES.has(file.type.toLowerCase())) {
    return { valid: false, error: 'Unsupported image format. Use JPEG, PNG, or WebP.' }
  }
  if (file.size > MAX_FILE_SIZE_BYTES) {
    return { valid: false, error: `File too large. Maximum size is ${MAX_FILE_SIZE_MB}MB` }
  }

  try {
    const dimensions = await getImageDimensions(file)
    const { width, height } = dimensions
    if (Math.min(width, height) < MIN_DIMENSION_PX) {
      return { valid: false, error: `Image too small. Minimum dimension is ${MIN_DIMENSION_PX}px` }
    }
    const aspectRatio = Math.max(width, height) / Math.min(width, height)
    if (aspectRatio > MAX_ASPECT_RATIO) {
      return { valid: false, error: 'Image aspect ratio too extreme. Please crop to a more standard ratio' }
    }
    return { valid: true, dimensions }
  } catch {
    return { valid: false, error: 'Could not read image file' }
  }
}

/**
 * @param {File} file
 * @returns {Promise<ImageDimensions>}
 */
function getImageDimensions(file) {
  return new Promise((resolve, reject) => {
    const image = new Image()
    const objectUrl = URL.createObjectURL(file)
    const cleanup = () => URL.revokeObjectURL(objectUrl)

    image.onload = () => {
      cleanup()
      resolve({ width: image.width, height: image.height })
    }
    image.onerror = () => {
      cleanup()
      reject(new Error('Failed to load image'))
    }
    image.src = objectUrl
  })
}

/** @param {number} delayMs @param {AbortSignal | null | undefined} signal */
function wait(delayMs, signal) {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(signal.reason ?? new DOMException('Request aborted', 'AbortError'))
      return
    }
    const timer = window.setTimeout(() => {
      signal?.removeEventListener('abort', onAbort)
      resolve(undefined)
    }, delayMs)
    const onAbort = () => {
      window.clearTimeout(timer)
      reject(signal?.reason ?? new DOMException('Request aborted', 'AbortError'))
    }
    signal?.addEventListener('abort', onAbort, { once: true })
  })
}

/**
 * Fetch with bounded exponential backoff. Non-idempotent methods such as POST
 * and PATCH are attempted once unless the caller explicitly opts in.
 *
 * @param {RequestInfo | URL} input
 * @param {RequestInit} [options]
 * @param {number} [maxAttempts]
 * @param {boolean} [retryNonIdempotent]
 * @returns {Promise<Response>}
 */
export async function retryFetch(input, options = {}, maxAttempts = 3, retryNonIdempotent = false) {
  const requestMethod = input instanceof Request ? input.method : 'GET'
  const method = (options.method || requestMethod).toUpperCase()
  const attempts = IDEMPOTENT_METHODS.has(method) || retryNonIdempotent
    ? Math.max(1, maxAttempts)
    : 1
  let lastError

  for (let attempt = 0; attempt < attempts; attempt += 1) {
    if (options.signal?.aborted) {
      throw options.signal.reason ?? new DOMException('Request aborted', 'AbortError')
    }

    try {
      const response = await fetch(input, options)
      const retryableStatus = response.status === 429 || response.status === 503
      if (!retryableStatus || attempt === attempts - 1) return response

      await response.body?.cancel().catch(() => undefined)
      await wait(Math.min(1000 * (2 ** attempt), 5000), options.signal)
    } catch (error) {
      if (options.signal?.aborted || (error instanceof DOMException && error.name === 'AbortError')) {
        throw error
      }
      lastError = error
      if (attempt === attempts - 1) break
      await wait(Math.min(1000 * (2 ** attempt), 5000), options.signal)
    }
  }

  throw lastError instanceof Error ? lastError : new Error('Request failed after retries')
}

/**
 * @param {Response} response
 * @returns {{ remaining: number | null, reset: number | null }}
 */
export function getRateLimitInfo(response) {
  const remaining = response.headers.get('X-RateLimit-Remaining')
  const reset = response.headers.get('X-RateLimit-Reset')
  return {
    remaining: remaining === null ? null : Number.parseInt(remaining, 10),
    reset: reset === null ? null : Number.parseInt(reset, 10),
  }
}

/** @param {string} rawHeaders */
function parseXhrHeaders(rawHeaders) {
  const headers = new Headers()
  rawHeaders.trim().split(/[\r\n]+/).forEach((line) => {
    const separator = line.indexOf(':')
    if (separator <= 0) return
    headers.append(line.slice(0, separator).trim(), line.slice(separator + 1).trim())
  })
  return headers
}

/**
 * Upload a file with progress tracking, a hard timeout, and caller-controlled
 * cancellation. The resolved value is a real Response-like browser object.
 *
 * @param {string} url
 * @param {FormData} formData
 * @param {string | null | undefined} token
 * @param {(progress: number) => void} [onProgress]
 * @param {{ signal?: AbortSignal, timeoutMs?: number }} [config]
 * @returns {Promise<Response>}
 */
export function uploadWithProgress(url, formData, token, onProgress, config = {}) {
  const { signal, timeoutMs = 180_000 } = config

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    let settled = false

    const cleanup = () => signal?.removeEventListener('abort', abortUpload)
    /** @param {Response} response */
    const finish = (response) => {
      if (settled) return
      settled = true
      cleanup()
      resolve(response)
    }
    /** @param {unknown} reason */
    const fail = (reason) => {
      if (settled) return
      settled = true
      cleanup()
      reject(reason instanceof Error || reason instanceof DOMException ? reason : new Error(String(reason)))
    }
    const abortUpload = () => xhr.abort()

    xhr.upload.addEventListener('progress', (event) => {
      if (event.lengthComputable) {
        onProgress?.(Math.round((event.loaded / event.total) * 100))
      }
    })

    xhr.addEventListener('load', () => {
      finish(new Response(xhr.responseText, {
        status: xhr.status,
        statusText: xhr.statusText,
        headers: parseXhrHeaders(xhr.getAllResponseHeaders()),
      }))
    })
    xhr.addEventListener('error', () => fail(new Error('Network error during upload')))
    xhr.addEventListener('timeout', () => fail(new Error('Upload timed out. Please try again.')))
    xhr.addEventListener('abort', () => fail(signal?.reason ?? new DOMException('Upload aborted', 'AbortError')))

    if (signal?.aborted) {
      fail(signal.reason ?? new DOMException('Upload aborted', 'AbortError'))
      return
    }

    xhr.open('POST', url)
    xhr.timeout = timeoutMs
    if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`)
    signal?.addEventListener('abort', abortUpload, { once: true })
    xhr.send(formData)
  })
}
