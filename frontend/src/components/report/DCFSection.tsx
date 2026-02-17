import { useState } from 'react';
import type { DCFResult, SensitivityCell } from '../../types';
import { WarningWithSources } from './WarningWithSources';

interface DCFSectionProps {
  result: DCFResult;
}

function fmt(val: number): string {
  if (val >= 1e9) return `$${(val / 1e9).toFixed(2)}B`;
  if (val >= 1e6) return `$${(val / 1e6).toFixed(2)}M`;
  if (val >= 1e3) return `$${(val / 1e3).toFixed(0)}K`;
  return `$${val.toFixed(0)}`;
}

function pct(val: number): string {
  return `${(val * 100).toFixed(1)}%`;
}

function SensitivityTable({ cells, baseWacc, baseTgr }: {
  cells: SensitivityCell[];
  baseWacc: number;
  baseTgr: number;
}) {
  if (cells.length === 0) return null;

  // Extract unique sorted WACC rows and TGR columns
  const waccSet = [...new Set(cells.map(c => c.wacc))].sort((a, b) => a - b);
  const tgrSet = [...new Set(cells.map(c => c.terminal_growth_rate))].sort((a, b) => a - b);

  const lookup = new Map<string, number>();
  for (const c of cells) {
    lookup.set(`${c.wacc.toFixed(4)}_${c.terminal_growth_rate.toFixed(4)}`, c.enterprise_value);
  }

  const isBase = (w: number, t: number) =>
    Math.abs(w - baseWacc) < 0.0001 && Math.abs(t - baseTgr) < 0.0001;

  return (
    <div className="overflow-x-auto">
      <h4 className="text-sm font-medium text-slate-700 mb-2">Sensitivity Analysis (WACC vs Terminal Growth Rate)</h4>
      <table className="text-xs w-full">
        <thead>
          <tr>
            <th className="py-1.5 pr-2 text-left text-slate-500">WACC \ TGR</th>
            {tgrSet.map(t => (
              <th key={t} className={`py-1.5 px-2 text-right ${Math.abs(t - baseTgr) < 0.0001 ? 'text-blue-700 font-bold' : 'text-slate-500'}`}>
                {pct(t)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {waccSet.map(w => (
            <tr key={w} className="border-t border-slate-100">
              <td className={`py-1.5 pr-2 ${Math.abs(w - baseWacc) < 0.0001 ? 'text-blue-700 font-bold' : 'text-slate-600'}`}>
                {pct(w)}
              </td>
              {tgrSet.map(t => {
                const key = `${w.toFixed(4)}_${t.toFixed(4)}`;
                const ev = lookup.get(key);
                const base = isBase(w, t);
                return (
                  <td
                    key={t}
                    className={`py-1.5 px-2 text-right font-mono ${
                      base
                        ? 'bg-blue-100 text-blue-900 font-bold rounded'
                        : 'text-slate-700'
                    }`}
                  >
                    {ev != null ? fmt(ev) : '—'}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function DCFSection({ result }: DCFSectionProps) {
  const [expanded, setExpanded] = useState(false);
  const isEstimated = result.warnings.some(w => w.includes('model-estimated'));

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-6 py-4 flex items-center justify-between text-left"
      >
        <div className="flex items-center gap-2 flex-wrap">
          <h3 className="font-semibold text-slate-800">Discounted Cash Flow</h3>
          {isEstimated && (
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700 border border-amber-200">
              Estimated Inputs
            </span>
          )}
          <p className="w-full text-sm text-slate-500">
            EV: {fmt(result.enterprise_value)} | WACC: {(result.discount_rate * 100).toFixed(1)}% | TGR: {(result.terminal_growth_rate * 100).toFixed(1)}%
          </p>
        </div>
        <span className="text-slate-400">{expanded ? '−' : '+'}</span>
      </button>
      {expanded && (
        <div className="px-6 pb-4 space-y-4">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 border-b border-slate-100">
                <th className="py-2 pr-4">Year</th>
                <th className="py-2">Free Cash Flow</th>
              </tr>
            </thead>
            <tbody>
              {result.projected_fcfs.map((fcf, i) => (
                <tr key={i} className="border-b border-slate-50">
                  <td className="py-2 pr-4">Year {i + 1}</td>
                  <td className="py-2">{fmt(fcf)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="text-sm">
            <span className="text-slate-500">Terminal Value:</span>{' '}
            <span className="font-medium">{fmt(result.terminal_value)}</span>
          </div>

          {result.sensitivity_table && result.sensitivity_table.length > 0 && (
            <SensitivityTable
              cells={result.sensitivity_table}
              baseWacc={result.discount_rate}
              baseTgr={result.terminal_growth_rate}
            />
          )}

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
