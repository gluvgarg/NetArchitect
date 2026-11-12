/**
 * Base API client configuration for NetArchitect.
 * Default points to FastAPI running on port 8000.
 */

export const API_BASE_URL =
  import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

/**
 * Standard fetch wrapper with JSON parsing and error handling.
 */
export async function apiRequest(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`
  const defaultHeaders = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
  }

  const response = await fetch(url, {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  })

  if (!response.ok) {
    throw new Error(`API Error: ${response.status} ${response.statusText}`)
  }

  return response.json()
}
