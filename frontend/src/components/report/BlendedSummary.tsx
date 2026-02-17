import type { BlendedValuation } from '../../types';

interface BlendedSummaryProps {
  valuation: BlendedValuation;
}

function formatCurrency(value: number): string {
  if (value >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
  if (value >= 1e6) return `$${(value / 1e6).toFixed(2)}M`;
  if (value >= 1e3) return `$${(value / 1e3).toFixed(0)}K`;
  return `$${value.toFixed(0)}`;
}

export function BlendedSummary({ valuation }: BlendedSummaryProps) {
  const { fair_value, fair_value_range } = valuation;
  const [low, high] = fair_value_range;
  const rangeWidth = high - low;
  const fairPct = rangeWidth > 0 ? ((fair_value - low) / rangeWidth) * 100 : 50;

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
      <div className="text-sm text-slate-500 uppercase tracking-wider mb-1">
        Blended Fair Value
      </div>
      <div className="text-4xl font-bold text-slate-900 mb-4">
        {formatCurrency(fair_value)}
      </div>

      {/* Range bar */}
      <div className="mb-2">
        <div className="relative h-3 bg-gradient-to-r from-blue-100 via-blue-300 to-blue-100 rounded-full">
          <div
            className="absolute top-1/2 -translate-y-1/2 w-4 h-4 bg-blue-600 rounded-full border-2 border-white shadow"
            style={{ left: `calc(${fairPct}% - 8px)` }}
          />
        </div>
        <div className="flex justify-between text-xs text-slate-400 mt-1">
          <span>{formatCurrency(low)}</span>
          <span>{formatCurrency(high)}</span>
        </div>
      </div>

      {/* Method breakdown */}
      <div className="mt-4 space-y-2">
        {valuation.methodology_weights.map((w) => (
          <div key={w.method} className="flex items-center gap-2">
            <div className="w-20 text-xs text-slate-500 capitalize">{w.method.replace('_', ' ')}</div>
            <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-500 rounded-full"
                style={{ width: `${w.weight * 100}%` }}
              />
            </div>
            <span className="text-xs text-slate-600 w-12 text-right">
              {(w.weight * 100).toFixed(0)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
