import type { ValuationRequest, ValuationReport, ValuationSummary } from '../types';

const BASE = '/api/valuations';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }
  return res.json();
}

export const api = {
  createValuation(data: ValuationRequest): Promise<ValuationReport> {
    return request<ValuationReport>(BASE, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  reweightValuation(id: string, weights: Record<string, number>): Promise<ValuationReport> {
    return request<ValuationReport>(`${BASE}/${id}/reweight`, {
      method: 'POST',
      body: JSON.stringify({ weights }),
    });
  },

  listValuations(): Promise<ValuationSummary[]> {
    return request<ValuationSummary[]>(BASE);
  },

  getValuation(id: string): Promise<ValuationReport> {
    return request<ValuationReport>(`${BASE}/${id}`);
  },

  deleteValuation(id: string): Promise<void> {
    return request<void>(`${BASE}/${id}`, { method: 'DELETE' });
  },

  getAuditLog(id: string): Promise<Record<string, unknown>> {
    return request<Record<string, unknown>>(`${BASE}/${id}/audit-log`);
  },

  async uploadProjections(file: File): Promise<import('../types').FinancialProjections> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${BASE}/upload-projections`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const body = await res.text();
      throw new Error(`Upload error ${res.status}: ${body}`);
    }
    return res.json();
  },
};
