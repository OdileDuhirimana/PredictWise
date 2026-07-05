import { useCallback, useEffect, useState } from 'react'
import api from '../api'

/**
 * Fetches a single GET endpoint and exposes { data, loading, error, reload }.
 *
 * Why this exists: every page that loads dashboard-style data (Dashboard.jsx
 * has five independent calls) needs the exact same three states — "still
 * loading" (show a skeleton), "failed" (show a retryable error, not an
 * infinite skeleton), and "loaded" (show the data). Before this hook,
 * Dashboard.jsx called `.then()` on each request with no `.catch()`, so any
 * single failed request (expired token, network blip, backend 500) left
 * that card's skeleton loader spinning forever with no way for the user to
 * recover short of a full page reload. Centralizing the fetch/error/retry
 * logic here means every consumer gets a real error state and a `reload()`
 * escape hatch for free, and a fix to the pattern only has to happen once.
 *
 * @param {string} endpoint - path passed to the shared `api` axios instance.
 * @returns {{data: any, loading: boolean, error: string|null, reload: () => void}}
 */
export default function useApiResource(endpoint) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    return api
      .get(endpoint)
      .then((response) => {
        setData(response.data)
      })
      .catch((err) => {
        const message = err?.response?.data?.error?.message || 'Failed to load data. Please try again.'
        setError(message)
      })
      .finally(() => {
        setLoading(false)
      })
  }, [endpoint])

  useEffect(() => {
    load()
  }, [load])

  return { data, loading, error, reload: load }
}
