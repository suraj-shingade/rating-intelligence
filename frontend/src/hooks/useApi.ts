/* ============================================================
   useApi -- Generic hook for API calls with loading, data,
   and error state management.
   ============================================================ */

import { useState, useCallback, useRef } from 'react';

interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

interface UseApiReturn<T, A extends unknown[]> {
  data: T | null;
  loading: boolean;
  error: string | null;
  execute: (...args: A) => Promise<T | null>;
  reset: () => void;
}

/**
 * Custom hook that wraps an async API function with loading/error handling.
 *
 * @param apiFn  The async function to wrap (e.g. apiClient.getHealth)
 * @returns      Object with { data, loading, error, execute, reset }
 */
export function useApi<T, A extends unknown[] = []>(
  apiFn: (...args: A) => Promise<T>
): UseApiReturn<T, A> {
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    loading: false,
    error: null,
  });

  const callIdRef = useRef(0);

  const execute = useCallback(
    async (...args: A): Promise<T | null> => {
      const callId = ++callIdRef.current;
      setState({ data: null, loading: true, error: null });

      try {
        const result = await apiFn(...args);
        if (callId === callIdRef.current) {
          setState({ data: result, loading: false, error: null });
        }
        return result;
      } catch (err: unknown) {
        const message =
          err instanceof Error ? err.message : 'An unexpected error occurred';
        if (callId === callIdRef.current) {
          setState({ data: null, loading: false, error: message });
        }
        return null;
      }
    },
    [apiFn]
  );

  const reset = useCallback(() => {
    setState({ data: null, loading: false, error: null });
  }, []);

  return { ...state, execute, reset };
}
