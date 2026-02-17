import { useState, useEffect } from 'react';
import type { MethodologyWeight } from '../../types';

interface WeightSlidersProps {
  weights: MethodologyWeight[];
  onApply: (weights: Record<string, number>) => void;
  loading: boolean;
}

export function WeightSliders({ weights, onApply, loading }: WeightSlidersProps) {
  const [local, setLocal] = useState<Record<string, number>>({});

  useEffect(() => {
    const init: Record<string, number> = {};
    weights.forEach((w) => {
      init[w.method] = Math.round(w.weight * 100);
    });
    setLocal(init);
  }, [weights]);

  const methods = Object.keys(local);
  const total = Object.values(local).reduce((s, v) => s + v, 0);

  const handleChange = (method: string, val: number) => {
    setLocal((prev) => ({ ...prev, [method]: val }));
  };

  const handleApply = () => {
    const normalized: Record<string, number> = {};
    const t = Object.values(local).reduce((s, v) => s + v, 0);
    methods.forEach((m) => {
      normalized[m] = t > 0 ? local[m] / t : 0;
    });
    onApply(normalized);
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
      <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-4">
        Adjust Weights
      </h3>
      <div className="space-y-4">
        {methods.map((method) => (
          <div key={method}>
            <div className="flex justify-between text-sm mb-1">
              <span className="text-slate-700 capitalize">{method.replace('_', ' ')}</span>
              <span className="text-slate-500">{local[method]}%</span>
            </div>
            <input
              type="range"
              min={0}
              max={100}
              value={local[method]}
              onChange={(e) => handleChange(method, parseInt(e.target.value))}
              className="w-full"
            />
          </div>
        ))}
      </div>
      <div className="mt-3 flex items-center justify-between">
        <span className={`text-xs ${total === 100 ? 'text-green-600' : 'text-amber-600'}`}>
          Total: {total}% {total !== 100 && '(will be normalized)'}
        </span>
        <button
          onClick={handleApply}
          disabled={loading || total === 0}
          className="px-4 py-1.5 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Applying...' : 'Apply Weights'}
        </button>
      </div>
    </div>
  );
}
