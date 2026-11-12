import { useState, useEffect, useCallback } from 'react'
import { getBackendHealth } from '../services/healthService'

/**
 * Custom React hook to query and track FastAPI backend health.
 */
export function useBackendHealth() {
  const [status, setStatus] = useState('checking') // 'checking' | 'connected' | 'disconnected'
  const [details, setDetails] = useState(null)
  const [lastChecked, setLastChecked] = useState(null)
  const [latencyMs, setLatencyMs] = useState(null)
  const [error, setError] = useState(null)

  const performCheck = useCallback(async () => {
    const startTime = performance.now()
    try {
      const data = await getBackendHealth()
      const elapsed = Math.round(performance.now() - startTime)
      setLatencyMs(elapsed)
      setDetails(data)
      setStatus(data?.status === 'healthy' ? 'connected' : 'disconnected')
      setError(null)
      setLastChecked(new Date().toLocaleTimeString())
    } catch (err) {
      setStatus('disconnected')
      setError(err?.message || 'Unable to connect to backend')
      setDetails(null)
      setLastChecked(new Date().toLocaleTimeString())
    }
  }, [])

  const recheck = useCallback(() => {
    setStatus('checking')
    performCheck()
  }, [performCheck])

  useEffect(() => {
    let ignore = false

    const execute = async () => {
      const startTime = performance.now()
      try {
        const data = await getBackendHealth()
        if (!ignore) {
          const elapsed = Math.round(performance.now() - startTime)
          setLatencyMs(elapsed)
          setDetails(data)
          setStatus(data?.status === 'healthy' ? 'connected' : 'disconnected')
          setError(null)
          setLastChecked(new Date().toLocaleTimeString())
        }
      } catch (err) {
        if (!ignore) {
          setStatus('disconnected')
          setError(err?.message || 'Unable to connect to backend')
          setDetails(null)
          setLastChecked(new Date().toLocaleTimeString())
        }
      }
    }

    execute()

    return () => {
      ignore = true
    }
  }, [])

  return {
    status,
    details,
    lastChecked,
    latencyMs,
    error,
    recheck,
  }
}
