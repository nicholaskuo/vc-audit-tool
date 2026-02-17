import { useState, useCallback, useEffect } from 'react';
import type { ValuationSummary } from '../types';
import { api } from '../api/client';

export function useHistory() {
  const [history, setHistory] = useState<ValuationSummary[]>([]);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const list = await api.listValuations();
      setHistory(list);
    } catch {
      // silently fail — sidebar is non-critical
    } finally {
      setLoading(false);
    }
  }, []);

  const remove = useCallback(async (id: string) => {
    try {
      await api.deleteValuation(id);
      setHistory(prev => prev.filter(v => v.id !== id));
    } catch {
      // silently fail
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { history, loading, refresh, remove };
}
