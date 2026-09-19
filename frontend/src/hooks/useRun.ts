import { useCallback, useEffect, useState } from 'react';
import { RunHeader, RunStatus, Verdict } from '../types';

export function useRun(initialRunId?: string | null) {
  const [runId, setRunId] = useState<string | null>(() => {
    if (initialRunId) return initialRunId;
    // Check URL parameters
    const params = new URLSearchParams(window.location.search);
    return params.get('runId') || params.get('run') || null;
  });

  const [header, setHeader] = useState<RunHeader | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch header info for current runId
  const fetchRunHeader = useCallback(async (id: string) => {
    try {
      const res = await fetch(`/api/runs/${encodeURIComponent(id)}`);
      if (!res.ok) {
        if (res.status === 404) {
          setError(`Run ${id} not found`);
          return null;
        }
        throw new Error(`Failed to fetch run: ${res.statusText}`);
      }
      const data: RunHeader = await res.json();
      setHeader(data);
      setError(null);
      return data;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setError(msg);
      return null;
    }
  }, []);

  // Fetch latest active or recent run if no runId is provided
  const findOrSelectRun = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await fetch('/api/runs');
      if (!res.ok) throw new Error('Failed to list runs');
      const runs: RunHeader[] = await res.json();
      if (runs.length > 0) {
        // Prefer currently running run, otherwise most recent
        const activeRun = runs.find((r) => r.status === 'running' || r.status === 'pending');
        const target = activeRun || runs[0];
        setRunId(target.run_id);
        setHeader(target);
      }
    } catch (err: unknown) {
      console.warn('Could not fetch existing runs:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (runId) {
      fetchRunHeader(runId);
    } else {
      findOrSelectRun();
    }
  }, [runId, fetchRunHeader, findOrSelectRun]);

  // Keep URL query param in sync
  useEffect(() => {
    if (runId) {
      const url = new URL(window.location.href);
      if (url.searchParams.get('runId') !== runId) {
        url.searchParams.set('runId', runId);
        window.history.replaceState({}, '', url.toString());
      }
    }
  }, [runId]);

  // Start a new run
  const startRun = async (params: {
    ticker: string;
    tradeDate?: string;
    useStub?: boolean;
    stepDelay?: number;
    provider?: string;
    quickModel?: string;
    deepModel?: string;
    depth?: number;
    analysts?: string[];
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    config?: Record<string, any>;
  }) => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/runs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ticker: params.ticker,
          trade_date: params.tradeDate || new Date().toISOString().split('T')[0],
          use_stub: params.useStub !== undefined ? params.useStub : false,
          step_delay: params.stepDelay !== undefined ? params.stepDelay : 0.0,
          provider: params.provider,
          quick_model: params.quickModel,
          deep_model: params.deepModel,
          depth: params.depth,
          analysts: params.analysts,
          config: params.config || {},
        }),
      });

      if (res.status === 409) {
        // Conflict - another run active
        const data = await res.json();
        const activeId = data.detail?.active_run_id;
        if (activeId) {
          setRunId(activeId);
          await fetchRunHeader(activeId);
          return { run_id: activeId, status: 'running' };
        }
        throw new Error(data.detail?.message || 'A run is already active');
      }

      if (!res.ok) {
        throw new Error(`Failed to start run: ${res.statusText}`);
      }

      const result = await res.json();
      setRunId(result.run_id);
      await fetchRunHeader(result.run_id);
      return result;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setError(msg);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  // Cancel current run
  const cancelRun = async () => {
    if (!runId) return;
    try {
      const res = await fetch(`/api/runs/${encodeURIComponent(runId)}/cancel`, {
        method: 'POST',
      });
      if (res.ok) {
        setHeader((prev) => (prev ? { ...prev, status: 'cancelled' } : null));
      } else {
        const data = await res.json();
        console.warn('Cancel returned status:', res.status, data);
      }
    } catch (err) {
      console.error('Failed to cancel run:', err);
    }
  };

  // Update header dynamically from incoming event
  const applyHeaderUpdate = useCallback((partial: {
    status?: RunStatus;
    verdict?: Verdict;
    stats?: Record<string, any>;
  }) => {
    setHeader((prev) => {
      if (!prev) return null;
      return {
        ...prev,
        status: partial.status || prev.status,
        verdict: partial.verdict || prev.verdict,
        stats: partial.stats || prev.stats,
      };
    });
  }, []);

  return {
    runId,
    setRunId,
    header,
    isLoading,
    error,
    startRun,
    cancelRun,
    refreshHeader: () => (runId ? fetchRunHeader(runId) : Promise.resolve(null)),
    applyHeaderUpdate,
  };
}
