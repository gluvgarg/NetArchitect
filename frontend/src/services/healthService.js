import { apiRequest } from './api'

/**
 * Health check service communicating with the FastAPI backend.
 */
export async function getBackendHealth() {
  return apiRequest('/health')
}

/**
 * Detailed API status check communicating with /api/v1/health.
 */
export async function getApiV1Health() {
  return apiRequest('/api/v1/health')
}
