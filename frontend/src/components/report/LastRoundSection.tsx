import { useState } from 'react';
import type { LastRoundResult } from '../../types';
import { WarningWithSources } from './WarningWithSources';

interface LastRoundSectionProps {
  result: LastRoundResult;
}

function fmt(val: number): string {
  if (val >= 1e9) return `$${(val / 1e9).toFixed(2)}B`;
  if (val >= 1e6) return `$${(val / 1e6).toFixed(2)}M`;
  return `$${val.toLocaleString()}`;
}

export function LastRoundSection({ result }: LastRoundSectionProps) {
  const [expanded, setExpanded] = useState(false);
  const isEstimated = result.warnings.some(w => w.toLowerCase().includes('model-estimated'));

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-6 py-4 flex items-center justify-between text-left"
      >
        <div className="flex items-center gap-2 flex-wrap">
          <h3 className="font-semibold text-slate-800">Last Round Market-Adjusted</h3>
          {isEstimated && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700 border border-amber-200">
              &#9888; Estimated Inputs
            </span>
          )}
          <p className="w-full text-sm text-slate-500">
            EV: {fmt(result.enterprise_value)} | Adjustment: {(result.adjustment_factor * 100 - 100).toFixed(1)}%
            {result.months_since_round != null && ` | ${result.months_since_round}mo ago`}
          </p>
        </div>
        <span className="text-slate-400">{expanded ? '−' : '+'}</span>
      </button>
      {expanded && (
        <div className="px-6 pb-4 space-y-3 text-sm">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <span className="text-slate-500">Last Round Valuation:</span>{' '}
              <span className="font-medium">{fmt(result.last_round_valuation)}</span>
            </div>
            <div>
              <span className="text-slate-500">Index Return:</span>{' '}
              <span className="font-medium">
                {result.index_return != null ? `${(result.index_return * 100).toFixed(1)}%` : '—'}
              </span>
            </div>
            <div>
              <span className="text-slate-500">Adjustment Factor:</span>{' '}
              <span className="font-medium">{result.adjustment_factor.toFixed(3)}</span>
            </div>
            <div>
              <span className="text-slate-500">Months Since Round:</span>{' '}
              <span className="font-medium">{result.months_since_round ?? '—'}</span>
            </div>
          </div>
          {result.warnings.length > 0 && (
            <div className="space-y-1">
              {result.warnings.map((w, i) => (
                <WarningWithSources key={i} text={w} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
