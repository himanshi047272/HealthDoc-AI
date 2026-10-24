import { useCallback, useEffect, useRef, useState } from 'react'

export function useAsync<T>(fn: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const fnRef = useRef(fn)
  fnRef.current = fn
  const run = useCallback(async (silent = false) => {
    if (!silent) setLoading(true)
    try { setData(await fnRef.current()); setError(null) }
    catch (e) { setError(e instanceof Error ? e.message : 'Something went wrong.') }
    finally { setLoading(false) }
  }, [])
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { void run() }, deps)
  return { data, error, loading, reload: run }
}
