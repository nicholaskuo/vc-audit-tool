import { useState } from 'react';
import { SourceLinks } from './WarningWithSources';

interface AssumptionsTableProps {
  assumptions: Record<string, unknown>;
}

const ESTIMATED_KEYS = new Set([
  'estimated_revenue', 'estimated_ebitda', 'revenue_confidence', 'revenue_reasoning',
  'estimated_growth_rates', 'estimated_ebitda_margins', 'estimated_wacc',
  'estimated_terminal_growth_rate', 'projections_source', 'projections_confidence', 'projections_reasoning',
  'estimated_last_round_valuation', 'estimated_last_round_date',
  'last_round_source', 'last_round_confidence', 'last_round_reasoning',
  'research_sources',
]);

const REASONING_KEYS = new Set([
  'revenue_reasoning', 'projections_reasoning', 'last_round_reasoning',
]);

function formatValue(val: unknown): string {
  if (val == null) return '—';
  if (Array.isArray(val)) {
    return val.map(v => typeof v === 'number' && v < 1 && v > -1 ? `${(v * 100).toFixed(1)}%` : String(v)).join(', ');
  }
  if (typeof val === 'number') {
    if (Math.abs(val) >= 1e9) return `$${(val / 1e9).toFixed(2)}B`;
    if (Math.abs(val) >= 1e6) return `$${(val / 1e6).toFixed(2)}M`;
    if (Math.abs(val) < 1 && val !== 0) return `${(val * 100).toFixed(1)}%`;
    return val.toLocaleString();
  }
  return String(val);
}

function formatLabel(key: string): string {
  return key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function ConfidenceBadge({ level }: { level: string }) {
  const colors: Record<string, string> = {
    high: 'bg-green-100 text-green-700 border-green-200',
    medium: 'bg-amber-100 text-amber-700 border-amber-200',
    low: 'bg-red-100 text-red-600 border-red-200',
  };
  const color = colors[level] || 'bg-slate-100 text-slate-600 border-slate-200';
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${color}`}>
      {level}
    </span>
  );
}

function EstimatedSection({ title, entries }: { title: string; entries: [string, unknown][] }) {
  const [showReasoning, setShowReasoning] = useState(false);
  const reasoningEntries = entries.filter(([k]) => REASONING_KEYS.has(k));
  const displayEntries = entries.filter(([k]) => !REASONING_KEYS.has(k));

  return (
    <div className="space-y-2">
      <h4 className="text-xs font-semibold text-amber-800 uppercase tracking-wider">{title}</h4>
      <table className="w-full text-sm">
        <tbody>
          {displayEntries.map(([key, val]) => (
            <tr key={key} className="border-b border-amber-100/50">
              <td className="py-1.5 pr-4 text-amber-700 whitespace-nowrap">
                {formatLabel(key)}
              </td>
              <td className="py-1.5 font-medium text-amber-900">
                {key.endsWith('confidence') ? (
                  <ConfidenceBadge level={String(val)} />
                ) : (
                  formatValue(val)
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {reasoningEntries.length > 0 && (
        <div>
          <button
            onClick={() => setShowReasoning(!showReasoning)}
            className="text-xs text-amber-600 hover:text-amber-800 font-medium flex items-center gap-1"
          >
            <span>{showReasoning ? '−' : '+'}</span>
            {showReasoning ? 'Hide' : 'Show'} reasoning
          </button>
          {showReasoning && (
            <div className="mt-1.5 text-xs text-amber-700 bg-amber-50 rounded p-2.5 whitespace-pre-line">
              {reasoningEntries.map(([key, val]) => (
                <div key={key}>
                  <span className="font-medium">{formatLabel(key.replace('_reasoning', ''))}:</span>{' '}
                  {String(val)}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function AssumptionsTable({ assumptions }: AssumptionsTableProps) {
  const entries = Object.entries(assumptions).filter(([, v]) => v != null);
  if (entries.length === 0) return null;

  const estimatedEntries = entries.filter(([k]) => ESTIMATED_KEYS.has(k) && k !== 'research_sources');
  const userEntries = entries.filter(([k]) => !ESTIMATED_KEYS.has(k));

  // Group estimated entries by category
  const revenueEstimates = estimatedEntries.filter(([k]) =>
    k.startsWith('estimated_revenue') || k.startsWith('estimated_ebitda') || k === 'revenue_confidence' || k === 'revenue_reasoning'
  );
  const projectionEstimates = estimatedEntries.filter(([k]) =>
    k.startsWith('estimated_growth') || k.startsWith('estimated_ebitda_margin') || k === 'estimated_wacc'
    || k === 'estimated_terminal_growth_rate' || k.startsWith('projections_')
  );
  const lastRoundEstimates = estimatedEntries.filter(([k]) =>
    k.startsWith('estimated_last_round') || k.startsWith('last_round_source') || k.startsWith('last_round_confidence') || k.startsWith('last_round_reasoning')
  );

  const hasEstimates = estimatedEntries.length > 0;

  // Extract research sources (structured array, not a flat key-value)
  const researchSources = (assumptions.research_sources as { title: string; url: string }[] | undefined) ?? [];

  return (
    <div className="space-y-4">
      {hasEstimates && (
        <div className="bg-amber-50 rounded-xl border border-amber-200 p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <span className="text-amber-500 text-lg">&#9888;</span>
            <h3 className="text-sm font-semibold text-amber-800 uppercase tracking-wider">
              Model-Estimated Values
            </h3>
          </div>
          <p className="text-xs text-amber-700 mb-4">
            The following values were estimated by the AI model from web research. They were not provided by the user
            and should be reviewed carefully.
          </p>

          {researchSources.length > 0 && (
            <div className="mb-4 p-3 bg-white/60 rounded-lg border border-amber-200/50">
              <h4 className="text-xs font-semibold text-amber-800 uppercase tracking-wider mb-2">
                Primary Sources
              </h4>
              <SourceLinks sources={researchSources} />
            </div>
          )}

          <div className="space-y-4">
            {revenueEstimates.length > 0 && (
              <EstimatedSection title="Revenue & EBITDA" entries={revenueEstimates} />
            )}
            {projectionEstimates.length > 0 && (
              <EstimatedSection title="DCF Projections" entries={projectionEstimates} />
            )}
            {lastRoundEstimates.length > 0 && (
              <EstimatedSection title="Last Funding Round" entries={lastRoundEstimates} />
            )}
          </div>
        </div>
      )}

      {userEntries.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
          <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-3">
            {hasEstimates ? 'User-Provided Values' : 'Key Assumptions'}
          </h3>
          <table className="w-full text-sm">
            <tbody>
              {userEntries.map(([key, val]) => (
                <tr key={key} className="border-b border-slate-50">
                  <td className="py-2 pr-4 text-slate-500">
                    {formatLabel(key)}
                  </td>
                  <td className="py-2 font-medium text-slate-800">
                    {formatValue(val)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export function hasModelEstimates(assumptions: Record<string, unknown>): boolean {
  return Object.keys(assumptions).some(k => ESTIMATED_KEYS.has(k) && assumptions[k] != null);
}
