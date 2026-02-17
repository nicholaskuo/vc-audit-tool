import { useState, useCallback, useRef } from 'react';
import type { ValuationRequest, ValuationReport, PipelineStep } from '../types';
import { api } from '../api/client';

export function useValuation() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<ValuationReport | null>(null);
  const [pipelineEvents, setPipelineEvents] = useState<PipelineStep[]>([]);
  const eventSourceRef = useRef<EventSource | null>(null);

  const submit = useCallback(async (data: ValuationRequest) => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.createValuation(data);
      setReport(result);
      return result;
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setError(msg);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const submitAsync = useCallback(async (data: ValuationRequest) => {
    setLoading(true);
    setError(null);
    setPipelineEvents([]);

    try {
      const res = await fetch('/api/valuations/async', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!res.ok) {
        throw new Error(`API error ${res.status}: ${await res.text()}`);
      }
      const { report_id, stream_url } = await res.json();

      return new Promise<ValuationReport | null>((resolve) => {
        const es = new EventSource(stream_url);
        eventSourceRef.current = es;

        es.onmessage = async (event) => {
          const parsed = JSON.parse(event.data);

          if (parsed.type === 'step') {
            setPipelineEvents((prev) => {
              const existing = prev.findIndex(
                (s) => s.step_name === parsed.step_name
              );
              const step: PipelineStep = {
                step_name: parsed.step_name,
                status: parsed.status === 'started' ? 'running' : parsed.status,
                duration_ms: parsed.duration_ms,
                error: parsed.error,
              };
              if (existing >= 0) {
                const updated = [...prev];
                updated[existing] = step;
                return updated;
              }
              return [...prev, step];
            });
          }

          if (parsed.type === 'complete') {
            es.close();
            eventSourceRef.current = null;
            try {
              const result = await api.getValuation(report_id);
              setReport(result);
              setLoading(false);
              resolve(result);
            } catch (err) {
              const msg = err instanceof Error ? err.message : 'Unknown error';
              setError(msg);
              setLoading(false);
              resolve(null);
            }
          }
        };

        es.onerror = () => {
          es.close();
          eventSourceRef.current = null;
          setError('Lost connection to pipeline stream');
          setLoading(false);
          resolve(null);
        };
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setError(msg);
      setLoading(false);
      return null;
    }
  }, []);

  const reweight = useCallback(async (id: string, weights: Record<string, number>) => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.reweightValuation(id, weights);
      setReport(result);
      return result;
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setError(msg);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const loadReport = useCallback(async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.getValuation(id);
      setReport(result);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  return { loading, error, report, pipelineEvents, submit, submitAsync, reweight, loadReport };
}
